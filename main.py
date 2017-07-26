#!/usr/local/bin/python
# -*- coding: UTF-8 -*-

import argparse
import json
import logging
from datetime import date, datetime

import apache_beam as beam
import en_depent_web_md
# import en_core_web_md
import spacy
import textblob
from textblob.download_corpora import download_lite as textblob_download_lite_corpora

from modules.BioentityTagger import BioEntityTagger
from apache_beam.coders import coders
# from apache_beam.examples.complete.game.user_score import WriteToBigQuery
from apache_beam.io import Read, iobase, WriteToText, ReadFromText
from apache_beam.io.filesystem import CompressionTypes
# from beam2_1 import WriteToBigQuery
# from schemas.table_schema_parsers import parse_bq_json_schema
from apache_beam.io.gcp.internal.clients import bigquery
from apache_beam.io.textio import _TextSource
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import SetupOptions
from dateutil.parser import parse
from lxml import etree, objectify
from spacy.language_data import TOKENIZER_INFIXES
from spacy.tokenizer import Tokenizer

from modules.NLP import NounChuncker, DocumentAnalysisSpacy

MEDLINE_BASE_PATH = 'pubmed/baseline'
MEDLINE_UPDATE_PATH = 'pubmed/updatefiles'
EXPECTED_ENTRIES_IN_MEDLINE_BASELINE_FILE = 30000

BQ_SCHEMA = '''{"fields":[{"mode":"NULLABLE","name":"_text_analyzers","type":"STRING"},{"fields":[{"mode":"NULLABLE","name":"label","type":"STRING"},{"mode":"NULLABLE","name":"id","type":"STRING"}],"mode":"REPEATED","name":"mesh_headings","type":"RECORD"},{"fields":[{"fields":[{"mode":"REPEATED","name":"chunks","type":"STRING"},{"fields":[{"mode":"NULLABLE","name":"term","type":"STRING"},{"mode":"NULLABLE","name":"score","type":"FLOAT"}],"mode":"REPEATED","name":"key_chunks","type":"RECORD"},{"fields":[{"mode":"NULLABLE","name":"short","type":"STRING"},{"mode":"NULLABLE","name":"long","type":"STRING"}],"mode":"REPEATED","name":"abbreviations","type":"RECORD"},{"mode":"REPEATED","name":"named_entities","type":"STRING"},{"fields":[{"mode":"NULLABLE","name":"short","type":"STRING"},{"mode":"NULLABLE","name":"long","type":"STRING"}],"mode":"REPEATED","name":"acronyms","type":"RECORD"},{"mode":"REPEATED","name":"recurring_chunks","type":"STRING"},{"mode":"REPEATED","name":"top_chunks","type":"STRING"}],"mode":"NULLABLE","name":"nlp","type":"RECORD"},{"fields":[{"mode":"REPEATED","name":"chunks","type":"STRING"},{"mode":"REPEATED","name":"recurring_chunks","type":"STRING"},{"mode":"REPEATED","name":"top_chunks","type":"STRING"},{"fields":[{"mode":"NULLABLE","name":"short","type":"STRING"},{"mode":"NULLABLE","name":"long","type":"STRING"}],"mode":"REPEATED","name":"abbreviations","type":"RECORD"}],"mode":"NULLABLE","name":"noun_phrases","type":"RECORD"}],"mode":"NULLABLE","name":"text_mined_entities","type":"RECORD"},{"fields":[{"mode":"NULLABLE","name":"registryNumber","type":"STRING"},{"mode":"NULLABLE","name":"name_id","type":"STRING"},{"mode":"NULLABLE","name":"name","type":"STRING"}],"mode":"REPEATED","name":"chemicals","type":"RECORD"},{"mode":"NULLABLE","name":"filename","type":"STRING"},{"mode":"REPEATED","name":"full_text_url","type":"STRING"},{"mode":"NULLABLE","name":"full_text","type":"STRING"},{"mode":"NULLABLE","name":"is_open_access","type":"STRING"},{"mode":"REPEATED","name":"references","type":"STRING"},{"fields":[{"mode":"NULLABLE","name":"issue","type":"STRING"},{"mode":"NULLABLE","name":"pgn","type":"STRING"},{"mode":"NULLABLE","name":"volume","type":"STRING"}],"mode":"NULLABLE","name":"journal_reference","type":"RECORD"},{"fields":[{"mode":"NULLABLE","name":"medlineAbbreviation","type":"STRING"},{"mode":"NULLABLE","name":"title","type":"STRING"}],"mode":"NULLABLE","name":"journal","type":"RECORD"},{"mode":"NULLABLE","name":"date_of_revision","type":"STRING"},{"mode":"REPEATED","name":"keywords","type":"STRING"},{"mode":"NULLABLE","name":"doi","type":"STRING"},{"mode":"NULLABLE","name":"id","type":"INTEGER"},{"mode":"REPEATED","name":"pub_type","type":"STRING"},{"mode":"NULLABLE","name":"title","type":"STRING"},{"mode":"NULLABLE","name":"cited_by","type":"STRING"},{"mode":"NULLABLE","name":"has_references","type":"STRING"},{"mode":"NULLABLE","name":"_delete_pmids","type":"STRING"},{"fields":[{"mode":"NULLABLE","name":"Identifier","type":"STRING"},{"mode":"NULLABLE","name":"CollectiveName","type":"STRING"},{"mode":"NULLABLE","name":"Suffix","type":"STRING"},{"mode":"NULLABLE","name":"affiliation","type":"STRING"},{"mode":"NULLABLE","name":"full_name","type":"STRING"},{"mode":"NULLABLE","name":"last_name","type":"STRING"},{"mode":"NULLABLE","name":"short_name","type":"STRING"}],"mode":"REPEATED","name":"authors","type":"RECORD"},{"mode":"NULLABLE","name":"pub_date","type":"DATE"},{"mode":"NULLABLE","name":"has_text_mined_entities","type":"STRING"},{"mode":"NULLABLE","name":"date","type":"DATE"},{"mode":"NULLABLE","name":"abstract","type":"STRING"},{"mode":"NULLABLE","name":"data_release","type":"FLOAT"}]}'''





def _get_field_schema(**kwargs):
    field_schema = bigquery.TableFieldSchema()
    field_schema.name = kwargs['name']
    field_schema.type = kwargs.get('type', 'STRING')
    field_schema.mode = kwargs.get('mode', 'NULLABLE')
    fields = kwargs.get('fields')
    if fields:
        for field in fields:
            field_schema.fields.append(_get_field_schema(**field))
    return field_schema


def _inject_fields(fields, table_schema):
    for field in fields:
        table_schema.fields.append(_get_field_schema(**field))

def parse_bq_json_schema(schema):
    table_schema = bigquery.TableSchema()
    _inject_fields(schema['fields'], table_schema)
    # table_schema = pickler.loads(pickler.dumps(table_schema))
    return table_schema

def json_serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat(' ')
    elif isinstance(obj, date):
        return obj.isoformat()
    else:
        try:
            return obj.__dict__
        except AttributeError:
            raise TypeError('Type not serializable')

class _MedlineTextSource(_TextSource):
    def read_records(self, file_path, range_tracker):
        logging.info(file_path)
        file_name = file_path.split('/')[-1]
        record = []
        skip = True
        for line in self.read_record_by_line(file_path, range_tracker):
            line = line.strip()
            if line.startswith("<MedlineCitation ") or line.startswith("<DeleteCitation>"):
                skip = False
            if not skip:
                record.append(line)
            if line.startswith("</MedlineCitation>") or line.startswith("</DeleteCitation>"):
                rec = ''.join(record).strip()
                skip = True
                record = []
                yield rec, file_name

    def read_record_by_line(self, file_name, range_tracker):
        start_offset = range_tracker.start_position()
        read_buffer = _MedlineTextSource.ReadBuffer('', 0)

        next_record_start_position = -1

        def split_points_unclaimed(stop_position):
            return (0 if stop_position <= next_record_start_position
                    else iobase.RangeTracker.SPLIT_POINTS_UNKNOWN)

        range_tracker.set_split_points_unclaimed_callback(split_points_unclaimed)

        with self.open_file(file_name) as file_to_read:
            position_after_skipping_header_lines = self._skip_lines(
                file_to_read, read_buffer,
                self._skip_header_lines) if self._skip_header_lines else 0
            start_offset = max(start_offset, position_after_skipping_header_lines)
            if start_offset > position_after_skipping_header_lines:
                # Seeking to one position before the start index and ignoring the
                # current line. If start_position is at beginning if the line, that line
                # belongs to the current bundle, hence ignoring that is incorrect.
                # Seeking to one byte before prevents that.

                file_to_read.seek(start_offset - 1)
                read_buffer = _TextSource.ReadBuffer('', 0)
                sep_bounds = self._find_separator_bounds(file_to_read, read_buffer)
                if not sep_bounds:
                    # Could not find a separator after (start_offset - 1). This means that
                    # none of the records within the file belongs to the current source.
                    return

                _, sep_end = sep_bounds
                read_buffer.data = read_buffer.data[sep_end:]
                next_record_start_position = start_offset - 1 + sep_end
            else:
                next_record_start_position = position_after_skipping_header_lines

            while range_tracker.try_claim(next_record_start_position):
                record, num_bytes_to_next_record = self._read_record(file_to_read,
                                                                     read_buffer)
                # For compressed text files that use an unsplittable OffsetRangeTracker
                # with infinity as the end position, above 'try_claim()' invocation
                # would pass for an empty record at the end of file that is not
                # followed by a new line character. Since such a record is at the last
                # position of a file, it should not be a part of the considered range.
                # We do this check to ignore such records.
                if len(record) == 0 and num_bytes_to_next_record < 0:  # pylint: disable=len-as-condition
                    break

                # Record separator must be larger than zero bytes.
                assert num_bytes_to_next_record != 0
                if num_bytes_to_next_record > 0:
                    next_record_start_position += num_bytes_to_next_record
                yield self._coder.decode(record)
                if num_bytes_to_next_record < 0:
                    break


class ReadMedlineFiles(beam.PTransform):
    """A PTransform for reading text files.
  
    Parses a text file as newline-delimited elements, by default assuming
    UTF-8 encoding. Supports newline delimiters '\\n' and '\\r\\n'.
  
    This implementation only supports reading text encoded using UTF-8 or ASCII.
    This does not support other encodings such as UTF-16 or UTF-32.
    """

    def __init__(
            self,
            file_pattern=None,
            min_bundle_size=0,
            compression_type=CompressionTypes.AUTO,
            strip_trailing_newlines=True,
            coder=coders.StrUtf8Coder(),
            validate=True,
            skip_header_lines=0,
            **kwargs):
        """Initialize the ReadFromText transform.
    
        Args:
          file_pattern: The file path to read from as a local file path or a GCS
            ``gs://`` path. The path can contain glob characters
            ``(*, ?, and [...] sets)``.
          min_bundle_size: Minimum size of bundles that should be generated when
            splitting this source into bundles. See ``FileBasedSource`` for more
            details.
          compression_type: Used to handle compressed input files. Typical value
            is CompressionTypes.AUTO, in which case the underlying file_path's
            extension will be used to detect the compression.
          strip_trailing_newlines: Indicates whether this source should remove
            the newline char in each line it reads before decoding that line.
          validate: flag to verify that the files exist during the pipeline
            creation time.
          skip_header_lines: Number of header lines to skip. Same number is skipped
            from each source file. Must be 0 or higher. Large number of skipped
            lines might impact performance.
          coder: Coder used to decode each line.
        """
        super(ReadMedlineFiles, self).__init__(**kwargs)
        self._source = _MedlineTextSource(
            file_pattern, min_bundle_size, compression_type,
            strip_trailing_newlines, coder
            , validate=validate,
            skip_header_lines=skip_header_lines)

    def expand(self, pvalue):
        return pvalue.pipeline | Read(self._source)


def parse_medline_xml(record, filename):
    publication = dict()
    try:
        medline = objectify.fromstring(record)
        if medline.tag == 'MedlineCitation':

            publication['pmid'] = medline.PMID.text
            for child in medline.getchildren():
                if child.tag == 'DateCreated':
                    first_publication_date = []
                    first_publication_date.append(child.Year.text)
                    first_publication_date.append(child.Month.text)
                    if child.Day.text:
                        first_publication_date.append(child.Day.text)
                    else:
                        first_publication_date.append('1')

                    publication['first_publication_date'] = parse(' '.join(first_publication_date)).date().isoformat()

                if child.tag == 'Article':
                    publication['journal_reference'] = {}
                    publication = parse_article_info(child, publication)

                if child.tag == 'ChemicalList':
                    publication['chemicals'] = []
                    for chemical in child.getchildren():
                        chemical_dict = dict()
                        chemical_dict['name'] = chemical.NameOfSubstance.text
                        chemical_dict['name_id'] = chemical.NameOfSubstance.attrib['UI']
                        chemical_dict['registryNumber'] = chemical.RegistryNumber.text
                        publication['chemicals'].append(chemical_dict)

                if child.tag == 'KeywordList':
                    publication['keywords'] = []
                    for keyword in child.getchildren():
                        publication['keywords'].append(keyword.text)

                if child.tag == 'MeshHeadingList':
                    publication['mesh_terms'] = list()
                    for meshheading in child.getchildren():
                        mesh_heading = dict()
                        for label in meshheading.getchildren():
                            if label.tag == 'DescriptorName':
                                mesh_heading['id'] = label.attrib['UI']
                                mesh_heading['label'] = label.text
                                # if label.tag == 'QualifierName':
                                #     if 'qualifier' not in mesh_heading.keys():
                                #         mesh_heading['qualifier'] = list()
                                #     qualifier = dict()
                                #     qualifier['label'] = label.text
                                #     qualifier['id'] = label.attrib['UI']
                                #     mesh_heading['qualifier'].append(qualifier)

                        publication['mesh_terms'].append(mesh_heading)

        elif medline.tag == 'DeleteCitation':
            publication['delete_pmids'] = list()
            for deleted_pmid in medline.getchildren():
                publication['delete_pmids'].append(deleted_pmid.text)

        publication['filename'] = filename

        # publication['text_analyzers'] = self.analyzers
        if 'delete_pmids' in publication and publication['delete_pmids']:
            for pmid in publication['delete_pmids']:
                '''update parent and analyzed child publication with empty values'''
                yield dict(pub_id=pmid,
                           filename=publication.get('filename'),
                           )
        else:
            yield dict(pub_id=publication['pmid'],
                        title=publication.get('title'),
                        abstract=publication.get('abstract'),
                        authors=publication.get('authors'),
                        pub_date=publication.get('pub_date'),
                        date=publication.get("first_publication_date"),
                        journal=publication.get('journal'),
                        journal_reference=publication.get("journal_reference"),
                        full_text=u"",
                        # full_text_url=publication['fullTextUrlList']['fullTextUrl'],
                        keywords=publication.get('keywords'),
                        doi=publication.get('doi'),
                        # cited_by=publication['citedByCount'],
                        # has_text_mined_terms=publication['hasTextMinedTerms'] == u'Y',
                        # has_references=publication['hasReferences'] == u'Y',
                        # is_open_access=publication['isOpenAccess'] == u'Y',
                        pub_type=publication.get('pub_types'),
                        filename=publication.get('filename'),
                        mesh_headings=publication.get('mesh_terms'),
                        chemicals=publication.get('chemicals'),
                        # text_analyzers=self.analyzers,
                        )

    except etree.XMLSyntaxError as e:
        pmid = 'n/a'
        try:
            pmid_end = record.index('</PMID>')
            if pmid_end:
                pmid = record[pmid_end-8:pmid_end]
        except:
            pass
        logging.error("Error parsing XML file {} - medline record {}".format(filename, pmid), e.message)


def parse_article_info(article, publication):
    for e in article.iterchildren():
        if e.tag == 'ArticleTitle':
            publication['title'] = e.text

        if e.tag == 'Abstract':
            abstracts = []
            for abstractText in e.findall('AbstractText'):
                if abstractText.text:
                    abstracts.append(abstractText.text)
            publication['abstract'] = ' '.join(abstracts)


        if e.tag == 'Journal':
            publication['journal'] = {}
            for child in e.getchildren():
                if child.tag == 'Title':
                    publication['journal']['title'] = child.text
                if child.tag == 'ISOAbbreviation':
                    publication['journal']['medlineAbbreviation'] = child.text
                else:
                    publication['journal']['medlineAbbreviation'] = ''

            for el in e.JournalIssue.getchildren():
                if el.tag == 'PubDate':
                    year, month, day = '1800', 'Jan', '1'
                    for pubdate in el.getchildren():
                        if pubdate.tag == 'Year':
                            year = pubdate.text
                        elif pubdate.tag == 'Month':
                            month = pubdate.text
                        elif pubdate.tag == 'Day':
                            day = pubdate.text

                    try:
                        publication['pub_date'] = parse(' '.join((year, month, day))).date().isoformat()
                    except ValueError:
                        pass
                if el.tag == 'Volume':
                    publication['journal_reference']['volume'] = el.text
                if el.tag == 'Issue':
                    publication['journal_reference']['issue'] = el.text

        if e.tag == 'PublicationTypeList':
            pub_types = []
            for pub_type in e.PublicationType:
                pub_types.append(pub_type.text)
            publication['pub_types'] = pub_types

        if e.tag == 'ELocationID' and e.attrib['EIdType'] == 'doi':
            publication['doi'] = e.text

        if e.tag == 'AuthorList':
            publication['authors'] = list()
            for author in e.Author:
                author_dict = dict()
                for e in author.getchildren():
                    if e.tag != 'AffiliationInfo':
                        author_dict[e.tag] = e.text

                publication['authors'].append(author_dict)

        if e.tag == 'Pagination':
            publication['journal_reference']['pgn'] = e.MedlinePgn.text

    return publication


def get_text_to_analyze(publication):
    try:
        if publication['title'] and publication['abstract']:
            return unicode(publication['title'] + ' ' + publication['abstract'])
        elif publication['title']:
            return unicode(publication['title'])
    except KeyError:
        pass
    return u''


class MedlineXMLParser(beam.DoFn):
    def process(self, element, *args, **kwargs):
        rec, file_name = element
        for parsed_record in parse_medline_xml(rec, file_name):
            yield parsed_record


class TagBioEntity(beam.DoFn):

    def process(self, element, *args, **kwargs):
        if element:
            text_to_match = get_text_to_analyze(element)
            if text_to_match:
                if isinstance(text_to_match, unicode):
                    text_to_match = text_to_match.encode('utf-8')
                matches = self.tagger.tag(text_to_match)
                element['bioentity'] = matches

            yield element


    def start_bundle(self):
        """Called before a bundle of elements is processed on a worker.
    
        Elements to be processed are split into bundles and distributed
        to workers. Before a worker calls process() on the first element
        of its bundle, it calls this method.
        """
        if not hasattr(self, 'tagger'):
            self.init_tagger()

    def init_tagger(self):
        self.tagger = BioEntityTagger()



class NLPAnalysis(beam.DoFn):

    def process(self, element, *args, **kwargs):
        element['text_mined_entities'] = {}
        for analyzer in self.analyzers:
            try:
                element['text_mined_entities'][str(analyzer)]=analyzer.digest(get_text_to_analyze(element))
            except:
                logging.exception("error in nlp analysis with %s analyser for text: %s"%(str(analyzer), get_text_to_analyze(element)))
                element['text_mined_entities'][str(analyzer)] = {}
                raise
        yield element

    def start_bundle(self):
        """Called before a bundle of elements is processed on a worker.

        Elements to be processed are split into bundles and distributed
        to workers. Before a worker calls process() on the first element
        of its bundle, it calls this method.
        """
        if not hasattr(self, 'nlp'):
            try:
                self.init_nlp()
                logging.info('INIT NLP MODEL')
            except:
                logging.exception('NLP MODEL INIT FAILED MISERABLY')
        else:
            logging.debug('NLP MODEL already initialized')



    @staticmethod
    def _create_tokenizer(nlp):
        infix_re = spacy.util.compile_infix_regex(TOKENIZER_INFIXES + [  # u'\w*[,-.–_—:;\(\)\[\]\{\}/]{1,3}\S\w*',
            # r'\w*[,\-.\-_:;\(\)\[\]\{\}\/]{1,3}\S\w*',
            # r'((?P<start_with_non_whitespace_and_one_or_more_punctation>\b\S+|[,.-_:;\(\)\[\]\{\}/\+])(?P<has_1_or_more_punctation>[,.-_:;\(\)\[\]\{\}/\+])+(?P<ends_with_non_whitespace_or_non_terminating_punctation>\S+\b[,.-_:;\(\)\[\]\{\}/\+]|[,.-_:;\(\)\[\]\{\}/\+|\-]|\S+\b))',
            # r'\w*\S-\S*\w',
            # u'\w*\S–\S*\w',
            # u'\w*\S—\S*\w',
            # u'\w*[,-.–_—:;\(\)\[\]\{\}/]{1,3}\S\w*'
            ur'(?P<start_with_non_whitespace_and_one_or_more_punctation>\b\S*|[,.-_-:–;—\(\[\{/\+]?)(?P<has_1_or_more_punctation>[,.-_-:–;—\(\)\[\]\{\}/\+])+(?P<ends_with_non_whitespace_or_non_terminating_punctation>\S+\b[,.-_-:–;—\)\]\}/\+]|[,.-_-:–;—\)\]\}/\+}]|\S+\b)'
        ])
        # TODO: prefix and suffix raise TypeError: '_regex.Pattern' object is not callable
        # prefix_boundaries_to_keep =  ur'\) \] \} \> , . - _ - : – ; — \+ -'.split()
        # suffix_boundaries_to_keep = ur'\( \[ \{ \< , . - _ - : – ; — \+ -'.split()
        # prefixe_re = spacy.util.compile_prefix_regex([i for i in TOKENIZER_PREFIXES if i not in
        # prefix_boundaries_to_keep])
        # suffixe_re = spacy.util.compile_suffix_regex([i for i in TOKENIZER_SUFFIXES if i not in
        # suffix_boundaries_to_keep])
        #
        # return Tokenizer(nlp.vocab, {}, prefixe_re.search, suffixe_re.search,
        #                  infix_re.finditer)
        return Tokenizer(nlp.vocab, {}, nlp.tokenizer.prefix_search, nlp.tokenizer.suffix_search,
                         infix_re.finditer)
    @staticmethod
    def _init_spacy_english_language():
        # nlp = en_core_web_md.load(create_make_doc=NLPAnalysis._create_tokenizer)
        nlp = en_depent_web_md.load(create_make_doc=NLPAnalysis._create_tokenizer)
        # nlp.vocab.strings.set_frozen(True)
        return nlp

    def init_nlp(self):
        try:
            logging.debug('DOWNLOADING TEXTBLOB LITE CORPORA')
            textblob_download_lite_corpora()
            logging.debug('STARTING NLPAnalysis')
            self.nlp = NLPAnalysis._init_spacy_english_language()
            logging.debug('STARTING STARTING')
            self._tagger =  BioEntityTagger(partial_match=False)
            self.analyzers = [NounChuncker(), DocumentAnalysisSpacy(self.nlp, tagger=self._tagger)]
        except:
            logging.exception('IT IS A BIG MESS HERE')


class ToJSON(beam.DoFn):
    def process(self, element, *args, **kwargs):
        yield json.dumps(element,
                         default=json_serialize,
                         sort_keys=True,
                         ensure_ascii=False,
                         indent=None,
                         )

class ExtractConcepts(beam.DoFn):
    def process(self, element, *args, **kwargs):
        parsed_element = json.loads(element)
        if 'concepts' in parsed_element['text_mined_entities']['nlp']:
            for concept in parsed_element['text_mined_entities']['nlp']['concepts']:
                yield json.dumps(dict(concept = concept,
                                      pub_id = parsed_element['pub_id']),
                                 default=json_serialize,
                                 sort_keys=True,
                                 ensure_ascii=False,
                                 indent=None,
                                 )

class ExtractBioentities(beam.DoFn):
    def process(self, element, *args, **kwargs):
        parsed_element = json.loads(element)
        if 'tagged_entities' in parsed_element['text_mined_entities']['nlp']:
            yield json.dumps(dict(entities = parsed_element['text_mined_entities']['nlp']['tagged_entities'],
                                      pub_id = parsed_element['pub_id']),
                             default=json_serialize,
                             sort_keys=True,
                             ensure_ascii=False,
                             indent=None,
                             )

class ExtractTaggedText(beam.DoFn):
    def process(self, element, *args, **kwargs):
        parsed_element = json.loads(element)
        if 'tagged_text' in parsed_element['text_mined_entities']['nlp']:
            tagged_text = parsed_element['text_mined_entities']['nlp']['tagged_text']
            try:
                partitioned_text = title= tagged_text.partition('. ')
                tagged_text_obj = dict(title= partitioned_text[0],
                                       abstract = partitioned_text[2],
                                       pub_id=parsed_element['pub_id'])
            except:
                tagged_text_obj = dict(title='',
                                       abstract=tagged_text,
                                       pub_id=parsed_element['pub_id']
                                       )
            yield json.dumps(tagged_text_obj,
                             default=json_serialize,
                             sort_keys=True,
                             ensure_ascii=False,
                             indent=None,
                             )

class CleanPublication(beam.DoFn):
    def process(self, element, *args, **kwargs):
        parsed_element = json.loads(element)
        try:
            del parsed_element['text_mined_entities']['nlp']['tagged_text']
        except KeyError:
            pass
        try:
            del parsed_element['text_mined_entities']['nlp']['tagged_entities']
        except KeyError:
            pass
        try:
            del parsed_element['text_mined_entities']['nlp']['concepts']
        except KeyError:
            pass
        yield json.dumps(parsed_element,
                         default=json_serialize,
                         sort_keys=True,
                         ensure_ascii=False,
                         indent=None,
                         )


class Print(beam.DoFn):
    def process(self, element, *args, **kwargs):
        print element


class Consume(beam.DoFn):
    def process(self, element, *args, **kwargs):
        pass





def run(argv=None):
    """Main entry point; defines and runs the tfidf pipeline."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_baseline',
                        required=False,
                        help='baseline URIs to process.')
    parser.add_argument('--input_updates',
                        required=False,
                        help='updates URIs to process.')
    parser.add_argument('--input_enriched',
                        required=False,
                        help='updates URIs to process.')
    parser.add_argument('--output',
                        required=False,
                        help='Output file to write results to.')
    parser.add_argument('--output_enriched',
                        required=False,
                        help='Output file to write results to.')
    parser.add_argument('--output_splitted',
                        required=False,
                        help='Output file to write results to.')
    known_args, pipeline_args = parser.parse_known_args(argv)
    # bq_table_schema = parse_bq_json_schema(json.load(open('schemas/medline.papers.json')))
    bq_table_schema = parse_bq_json_schema(json.loads(BQ_SCHEMA))
    # We use the save_main_session option because one or more DoFn's in this
    # workflow rely on global context (e.g., a module imported at module level).
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(SetupOptions).save_main_session = True
    with beam.Pipeline(options=pipeline_options) as p:

        if known_args.input_baseline or known_args.input_updates:

            if known_args.input_baseline and known_args.input_updates:
                medline_articles_base = p | 'BaselineEmitXML' >> ReadMedlineFiles(known_args.input_baseline)
                medline_articles_updates = p | 'UpdatesEmitXML' >> ReadMedlineFiles(known_args.input_updates)

                medline_articles = (
                    (medline_articles_base, medline_articles_updates)
                    | beam.Flatten())
            elif known_args.input_baseline:
                medline_articles = p | 'BaselineEmitXML' >> ReadMedlineFiles(known_args.input_baseline)
            elif known_args.input_updates:
                medline_articles = p | 'UpdatesEmitXML' >> ReadMedlineFiles(known_args.input_updates)
            else:
                raise AttributeError('at least an XML input is required')




            parsed_medline_articles = medline_articles | 'ParseXMLtoDict' >> beam.ParDo(MedlineXMLParser())
            # parsed_medline_articles | 'ConsumeJSON' >> beam.ParDo(Consume())


            json_medline_articles = parsed_medline_articles | 'MedlineToJSON' >> beam.ParDo(ToJSON())

            #
            json_medline_articles | 'WriteJSONToGS' >> WriteToText(known_args.output, file_name_suffix='.json.gz')
            #
            # json_medline_articles |  'WriteMedlneJSONToBQ' >> beam.io.Write(
            #                                                         beam.io.BigQuerySink(
            #                                                             "open-targets:medline.papers",
            #                                                             schema=bq_table_schema,
            #                                                             create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            #                                                             write_disposition=beam.io.BigQueryDisposition.WRITE_TRUNCATE))


            enriched_articles = parsed_medline_articles | 'NLPAnalysis' >> beam.ParDo(NLPAnalysis())

            json_enriched_medline_articles = enriched_articles | 'EnrichedMedlineToJSON' >> beam.ParDo(ToJSON())

            json_enriched_medline_articles | 'WriteEnrichedJSONToGS' >> WriteToText(known_args.output_enriched, file_name_suffix='_enriched.json.gz')

            # medline_articles | WriteToBigQuery(
            #                                 "open-targets:medline.papers",  # known_args.output_table,
            #                                 schema=bq_table_schema,
            #                                 create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            #                                 write_disposition=beam.io.BigQueryDisposition.WRITE_TRUNCATE)
            #
        elif known_args.input_enriched:

            json_enriched_medline_articles = p | 'GetEnrichedArticles' >> ReadFromText(known_args.input_enriched)

        else:
            raise AttributeError('missing json enriched data  input')

        if known_args.output_splitted:

            concepts = json_enriched_medline_articles | 'ArticleToConcepts' >> beam.ParDo(ExtractConcepts())
            concepts | 'WriteConceptJSONToGS' >> WriteToText(known_args.output_splitted,
                                                              file_name_suffix='_concepts.json.gz')

            bioentities = json_enriched_medline_articles | 'ArticleToBioentities' >> beam.ParDo(ExtractBioentities())
            bioentities | 'WriteBioentityJSONToGS' >> WriteToText(known_args.output_splitted,
                                                              file_name_suffix='_bioentities.json.gz')

            taggedtext = json_enriched_medline_articles | 'ArticleToTaggedText' >> beam.ParDo(ExtractTaggedText())
            taggedtext | 'WriteTaggedTextJSONToGS' >> WriteToText(known_args.output_splitted,
                                                                 file_name_suffix='_taggedtext.json.gz')

            smallarticles = json_enriched_medline_articles | 'ArticleToSmallArticles' >> beam.ParDo(CleanPublication())
            smallarticles | 'WriteSmallArticleJSONToGS' >> WriteToText(known_args.output_splitted,
                                                                     file_name_suffix='_small.json.gz')



if __name__ == '__main__':
    run()
