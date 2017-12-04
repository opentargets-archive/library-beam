#!/usr/local/bin/python
# -*- coding: UTF-8 -*-
import logging
import re
import string
from collections import Counter
from copy import copy, deepcopy

import nltk
from sklearn.feature_extraction.stop_words import ENGLISH_STOP_WORDS
from spacy.en import English
from spacy.symbols import *
from spacy.tokens import Span
from spacy.tokens.doc import Doc

try:
    from nltk.corpus import stopwords as nltk_stopwords
except ImportError:
    nltk.download(['punkt', 'averaged_perceptron_tagger', 'stopwords'])  # 'brown' corpora might be needed
    from nltk.corpus import stopwords as nltk_stopwords

from textblob import TextBlob
from textblob.base import BaseNPExtractor
from textblob.decorators import requires_nltk_corpus
from textblob.en.np_extractors import _normalize_tags
from textblob.download_corpora import download_lite
from unidecode import unidecode

import spacy
from spacy.language_data import TOKENIZER_INFIXES
from spacy.tokenizer import Tokenizer
# import en_core_web_md
import en_depent_web_md


from AbbreviationFinder import AbbreviationsParser
from BioStopWords import DOMAIN_STOP_WORDS, COMMON_WORDS_CORPUS
from modules.BioentityTagger import MatchedTag
spacy.tokens.token.Token


def create_tokenizer(nlp):
    infix_re = spacy.util.compile_infix_regex(TOKENIZER_INFIXES + [  # u'\w*[,-.–_—:;\(\)\[\]\{\}/]{1,3}\S\w*',
        # r'\w*[,\-.\-_:;\(\)\[\]\{\}\/]{1,3}\S\w*',
        # r'((?P<start_with_non_whitespace_and_one_or_more_punctation>\b\S+|[,.-_:;\(\)\[\]\{\}/\+])(
        # ?P<has_1_or_more_punctation>[,.-_:;\(\)\[\]\{\}/\+])+(
        # ?P<ends_with_non_whitespace_or_non_terminating_punctation>\S+\b[,.-_:;\(\)\[\]\{\}/\+]|[,.-_:;\(\)\[\]\{
        # \}/\+|\-]|\S+\b))',
        # r'\w*\S-\S*\w',
        # u'\w*\S–\S*\w',
        # u'\w*\S—\S*\w',
        # u'\w*[,-.–_—:;\(\)\[\]\{\}/]{1,3}\S\w*'
        ur'(?P<start_with_non_whitespace_and_one_or_more_punctation>\b\S*|[,.-_-:–;—\(\[\{/\+]?)('
        ur'?P<has_1_or_more_punctation>[,.-_-:–;—\(\)\[\]\{\}/\+])+('
        ur'?P<ends_with_non_whitespace_or_non_terminating_punctation>\S+\b[,.-_-:–;—\)\]\}/\+]|[,'
        ur'.-_-:–;—\)\]\}/\+}]|\S+\b)'
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


def init_spacy_english_language():
    # nlp = en_core_web_md.load(create_make_doc=create_tokenizer)
    nlp = en_depent_web_md.load(create_make_doc=create_tokenizer)

    # nlp.vocab.strings.set_frozen(True)
    return nlp


import spacy.util

SUBJECTS = ["nsubj", "nsubjpass", "csubj", "csubjpass", "agent", "expl", "meta"]
OBJECTS = ["dobj", "dative", "attr", "oprd", "pobj", "attr", "conj", "compound"]

ANY_NOUN = SUBJECTS + OBJECTS + ['compound']
SHORT_MATCH_CASE_SENSITIVE_CATEGORIES = ['TARGET', 'DRUG' 'CHEMICAL', 'GENE', 'PROTEINCOMPLEX']
NOISY_CATEGORIES = []#['DISEASE',]


# List of symbols we don't care about
SYMBOLS = " ".join(string.punctuation).split(" ") + ["-----", "---", "...", "â", "â", "'ve"]

LABELS = {
    u'ENT': u'ENT',
    u'PERSON': u'ENT',
    u'NORP': u'ENT',
    u'FAC': u'ENT',
    u'ORG': u'ENT',
    u'GPE': u'ENT',
    u'LOC': u'ENT',
    u'LAW': u'ENT',
    u'PRODUCT': u'ENT',
    u'EVENT': u'ENT',
    u'WORK_OF_ART': u'ENT',
    u'LANGUAGE': u'ENT',
    u'DATE': u'DATE',
    u'TIME': u'TIME',
    u'PERCENT': u'PERCENT',
    u'MONEY': u'MONEY',
    u'QUANTITY': u'QUANTITY',
    u'ORDINAL': u'ORDINAL',
    u'CARDINAL': u'CARDINAL'
}
MAX_CHUNKS = 100
MAX_TERM_FREQ = 200000


class AbstractNormalizer(object):
    greek_alphabet = {
        u'\u0391': 'Alpha',
        u'\u0392': 'Beta',
        u'\u0393': 'Gamma',
        u'\u0394': 'Delta',
        u'\u0395': 'Epsilon',
        u'\u0396': 'Zeta',
        u'\u0397': 'Eta',
        u'\u0398': 'Theta',
        u'\u0399': 'Iota',
        u'\u039A': 'Kappa',
        u'\u039B': 'Lamda',
        u'\u039C': 'Mu',
        u'\u039D': 'Nu',
        u'\u039E': 'Xi',
        u'\u039F': 'Omicron',
        u'\u03A0': 'Pi',
        u'\u03A1': 'Rho',
        u'\u03A3': 'Sigma',
        u'\u03A4': 'Tau',
        u'\u03A5': 'Upsilon',
        u'\u03A6': 'Phi',
        u'\u03A7': 'Chi',
        u'\u03A8': 'Psi',
        u'\u03A9': 'Omega',
        u'\u03B1': 'alpha',
        u'\u03B2': 'beta',
        u'\u03B3': 'gamma',
        u'\u03B4': 'delta',
        u'\u03B5': 'epsilon',
        u'\u03B6': 'zeta',
        u'\u03B7': 'eta',
        u'\u03B8': 'theta',
        u'\u03B9': 'iota',
        u'\u03BA': 'kappa',
        u'\u03BB': 'lamda',
        u'\u03BC': 'mu',
        u'\u03BD': 'nu',
        u'\u03BE': 'xi',
        u'\u03BF': 'omicron',
        u'\u03C0': 'pi',
        u'\u03C1': 'rho',
        u'\u03C3': 'sigma',
        u'\u03C4': 'tau',
        u'\u03C5': 'upsilon',
        u'\u03C6': 'phi',
        u'\u03C7': 'chi',
        u'\u03C8': 'psi',
        u'\u03C9': 'omega',
    }

    def normalize(self, text):
        '''transform greek letters'''
        for key in self.greek_alphabet:
            text = text.replace(key, self.greek_alphabet[key])

        '''remove multiple spaces'''
        text = re.sub("\s\s+", " ", text)
        return unidecode(text)


class PerceptronNPExtractor(BaseNPExtractor):
    '''modified from

    http://thetokenizer.com/2013/05/09/efficient-way-to-extract-the-main-topics-of-a-sentence/

    To use Perceptron POS Tagger (more accurate)
    '''

    CFG = {
        ('NNP', 'NNP'): 'NNP',
        ('NNP', 'NN'): 'NNP',
        ('NN', 'NNS'): 'NNP',
        ('NNP', 'PO'): 'NNP',
        ('NN', 'IN'): 'NN',
        ('IN', 'JJ'): 'NN',
        # ('PO', 'NN'): 'NNP',
        ('NN', 'NN'): 'NNI',
        ('NNI', 'NN'): 'NNI',
        ('JJ', 'JJ'): 'JJ',
        ('JJ', 'NN'): 'NNI',
        ('NN', 'JJ'): 'NNI',

    }

    def __init__(self):
        self._trained = False

    @requires_nltk_corpus
    def train(self):
        # train_data = nltk.corpus.brown.tagged_sents(categories=['news','science_fiction'])
        self.tagger = nltk.PerceptronTagger()
        self._trained = True
        return None

    def _tokenize_sentence(self, sentence):
        '''Split the sentence into single words/tokens'''
        tokens = nltk.word_tokenize(sentence)
        return tokens

    def extract(self, sentence):
        '''Return a list of noun phrases (strings) for body of text.'''
        if not self._trained:
            self.train()
        tokens = self._tokenize_sentence(sentence)
        tagged = self.tagger.tag(tokens)
        # print tagged
        tags = _normalize_tags(tagged)
        # print tags
        merge = True
        while merge:
            merge = False
            for x in range(0, len(tags) - 1):
                t1 = tags[x]
                t2 = tags[x + 1]
                key = t1[1], t2[1]
                # print t1, t2, key
                value = self.CFG.get(key, '')
                if value:
                    merge = True
                    tags.pop(x)
                    tags.pop(x)
                    if t2[0][0].isalnum():
                        match = '%s %s' % (t1[0], t2[0])
                    else:
                        match = '%s%s' % (t1[0], t2[0])
                    pos = value
                    tags.insert(x, (match, pos))
                    break

        matches = [t[0] for t in tags if t[1] in ['NNP', 'NNI', 'NN']]
        # print matches
        return matches


class NounChuncker(object):
    def __init__(self):
        self.np_ex = PerceptronNPExtractor()
        self.normalizer = AbstractNormalizer()
        self.abbreviations_finder = AbbreviationsParser()

    def digest(self, text):
        normalized = self.normalizer.normalize(text)
        parsed = TextBlob(normalized, np_extractor=self.np_ex)
        counted_noun_phrases = parsed.noun_phrases
        abbreviations = self.abbreviations_finder.digest(parsed)
        '''make sure defined acronym are used as noun phrases '''
        for abbr in abbreviations:
            if abbr['long'].lower() not in counted_noun_phrases:
                counted_noun_phrases.append(abbr['long'].lower())
        '''improved singularisation still needs refinement'''
        # singular_counted_noun_phrases = []
        # for np in counted_noun_phrases:
        #     if not (np.endswith('sis') or np.endswith('ess')):
        #         singular_counted_noun_phrases.append(singularize(np))
        #     else:
        #         singular_counted_noun_phrases.append(np)
        # singular_counted_noun_phrases = Counter(singular_counted_noun_phrases)
        counted_noun_phrases = Counter(counted_noun_phrases)
        base_noun_phrases = counted_noun_phrases.keys()
        '''remove plurals with appended s'''
        for np in counted_noun_phrases.keys():
            if np + 's' in counted_noun_phrases:
                counted_noun_phrases[np] += counted_noun_phrases[np + 's']
                del counted_noun_phrases[np + 's']
        '''increase count of shorter form with longer form'''
        for abbr in abbreviations:
            short = abbr['short'].lower()
            if short in counted_noun_phrases:
                counted_noun_phrases[abbr['long'].lower()] += counted_noun_phrases[short]
                del counted_noun_phrases[short]

        # count substrings occurrences as well
        for k in counted_noun_phrases:
            for s in counted_noun_phrases:
                if k != s and k in s:
                    counted_noun_phrases[k] += 1
        return dict(chunks=base_noun_phrases,
                    recurring_chunks=[i for i, k in counted_noun_phrases.items() if k > 1],
                    top_chunks=[i[0] for i in counted_noun_phrases.most_common(5) if i[1] > 1],
                    abbreviations=abbreviations)

    def __str__(self):
        return 'noun_phrases'


class PublicationAnalysisSpacy(object):
    def __init__(self, fetcher, dry_run=False):

        self.fetcher = fetcher
        self.logger = logging.getLogger(__name__)
        self.parser = English()
        # A custom stoplist
        STOPLIST = set(nltk_stopwords.words('english') + ["n't", "'s", "'m", "ca", "p", "t"] + list(ENGLISH_STOP_WORDS))
        ALLOWED_STOPLIST = set(('non'))
        self.STOPLIST = STOPLIST - ALLOWED_STOPLIST

    def analyse_publication(self, pub_id, pub=None):

        if pub is None:
            pub = self.fetcher.get_publication(pub_ids=pub_id)
        analysed_pub = None
        if pub.title or pub.abstract:
            text_to_parse = pub.get_text_to_analyze()
            lemmas, noun_chunks, analysed_sentences_count = self._spacy_analyser(text_to_parse)
            lemmas = tuple({'value': k, "count": v} for k, v in lemmas.items())
            noun_chunks = tuple({'value': k, "count": v} for k, v in noun_chunks.items())
            analysed_pub = PublicationAnalysisSpacy(pub_id=pub_id,
                                                    lemmas=lemmas,
                                                    noun_chunks=noun_chunks,
                                                    analysed_sentences_count=analysed_sentences_count)

        return analysed_pub

    def _spacy_analyser(self, abstract):

        lemmas, tokens, parsedEx = self.tokenizeText(abstract)
        parsed_vector = self.transform_doc(parsedEx)
        tl = abstract.lower()
        sents_count = len(list(parsedEx.sents))
        ec = Counter()

        for e in parsedEx.ents:
            e_str = u' '.join(t.orth_ for t in e).encode('utf-8').lower()
            if ((not e.label_) or (e.label_ == u'ENT')) and not (e_str in self.STOPLIST) and not (e_str in SYMBOLS):
                if e_str not in ec:
                    try:
                        ec[e_str] += tl.count(e_str)
                    except:
                        self.logger.info(e_str)
                        #            print( e_str, e_str in STOPLIST)
                        #        print (e.label, repr(e.label_),  ' '.join(t.orth_ for t in e))
        # print('FILTERED NOUN CHUNKS:')
        # for k, v in ec.most_common(5):
        #     print k, round(float(v) / sents_count, 3)

        return lemmas, ec, sents_count

    # A custom function to tokenize the text using spaCy
    # and convert to lemmas
    def tokenizeText(self, sample):
        # get the tokens using spaCy
        tokens_all = self.parser(unicode(sample))
        #    for t in tokens_all.noun_chunks:
        #        print(t, list(t.subtree))
        # lemmatize
        lemmas = []
        for tok in tokens_all:
            lemmas.append(tok.lemma_.lower().strip() if tok.lemma_ != "-PRON-" else tok.lower_)
        tokens = lemmas

        # stoplist the tokens
        tokens = [tok for tok in tokens if tok.encode('utf-8') not in self.STOPLIST]

        # stoplist symbols
        tokens = [tok for tok in tokens if tok.encode('utf-8') not in SYMBOLS]

        # remove large strings of whitespace
        while "" in tokens:
            tokens.remove("")
        while " " in tokens:
            tokens.remove(" ")
        while "\n" in tokens:
            tokens.remove("\n")
        while "\n\n" in tokens:
            tokens.remove("\n\n")
        filtered = []
        for tok in tokens_all:
            if tok.lemma_.lower().strip() in tokens and tok.pos_ in ['PROP', 'PROPN', 'NOUN', 'ORG', 'FCA', 'PERSON', ]:
                filtered.append(tok)
        c = Counter([tok.lemma_.lower().strip() for tok in filtered])
        sents_count = len(list(tokens_all.sents))
        # print 'COMMON LEMMAS'
        # for i in c.most_common(5):
        #     if i[1] > 1:
        #         print i[0], round(float(i[1]) / sents_count, 3)
        return c, tokens, tokens_all

    def represent_word(self, word):
        if word.like_url:
            return '%%URL|X'
        text = re.sub(r'\s', '_', word.text)
        tag = LABELS.get(word.ent_type_, word.pos_)
        if not tag:
            tag = '?'
        return text + '|' + tag

    def transform_doc(self, doc):

        for ent in doc.ents:

            ent.merge(ent.root.tag_, ent.text, LABELS[ent.label_])

        for np in list(doc.noun_chunks):
            #        print (np, np.root.tag_, np.text, np.root.ent_type_)
            while len(np) > 1 and np[0].dep_ not in ('advmod', 'amod', 'compound'):
                np = np[1:]
            # print (np, np.root.tag_, np.text, np.root.ent_type_)

            np.merge(np.root.tag_, np.text, np.root.ent_type_)
        strings = []
        for sent in doc.sents:
            if sent.text.strip():
                strings.append(' '.join(self.represent_word(w) for w in sent if not w.is_space))
        if strings:
            return '\n'.join(strings) + '\n'
        else:
            return ''


class PublicationAnalysis():
    """
    Base class for all publication analysis
    """

    def __init__(self,
                 pub_id):
        self.pub_id = pub_id

    def get_type(self):
        '''Define the type for elasticsearch here'''
        return NotImplementedError()


class DocumentAnalysisSpacy(object):
    def __init__(self,
                 nlp,
                 normalize=True,
                 stopwords=None,
                 tagger=None
                 ):

        self.logger = logging.getLogger(__name__)
        self._normalizer = AbstractNormalizer()
        self._abbreviations_finder = AbbreviationsParser()

        self.normalize = normalize
        if self.normalize:
            self._normalizer = AbstractNormalizer()
        if stopwords is None:
            self.stopwords = set(nltk_stopwords.words('english') + ["n't", "'s", "'m", "ca", "p", "t"] + list(
                ENGLISH_STOP_WORDS) + DOMAIN_STOP_WORDS + list(string.punctuation))

        self.nlp = nlp
        self.processed_counter = 0
        self._tagger = tagger

    def process(self, document):
        tags = []
        if isinstance(document, Doc):
            self.doc = document
            abbreviations = self._abbreviations_finder.digest_as_dict(self.doc.text)
            if self._tagger is not None:
                tags = self._tagger.tag(self.doc.text)

        elif isinstance(document, unicode):
            if self.normalize:
                document = u'' + self._normalizer.normalize(document)
            abbreviations = self._abbreviations_finder.digest_as_dict(document)
            if self._tagger is not None:
                tags = self._tagger.tag(document)

            # self.logger.debug('abbreviations: ' + str(abbreviations))

            if abbreviations:
                for short, long in abbreviations.items():
                    if short in document and not long in document:
                        document = document.replace(short, long)
            try:
                self.doc = self.nlp(document)
            except:
                self.logger.exception('Error parsing the document: %s' % document)
                return [None, {}]
        else:
            raise AttributeError('document needs to be unicode or Doc not %s' % document.__class__)

        allowed_tag_pos = set(('NOUN', 'PROPN', 'ADJ', u'PROPN', u'NOUN', u'ADJ'))

        concepts = []
        noun_phrases = []
        self.analysed_sentences = []
        for si,sentence in enumerate(self.doc.sents):
            try:
                analysed_sentence = SentenceAnalysisSpacy(sentence.text, self.nlp, stopwords=self.stopwords)
                analysed_sentence.analyse()
                self.analysed_sentences.append(analysed_sentence)
                for concept in analysed_sentence.concepts:
                    concept['sentence']=si
                    concepts.append(concept)
                noun_phrases.extend(analysed_sentence.noun_phrases)
            except:
                self.logger.exception('Error parsing the sentence: %s' % sentence.text)

        # print self.noun_phrases
        noun_phrases = list(set([i.text for i in noun_phrases if i.text.lower() not in self.stopwords]))

        # clustered_np = self.cluster_np(noun_phrases)
        noun_phrase_counter = Counter()
        lowered_text = self.doc.text.lower()
        for i in noun_phrases:
            lowered_np = i.lower()
            noun_phrase_counter[lowered_np] = lowered_text.count(lowered_np)
        '''remove plurals with appended s'''
        for np in noun_phrase_counter.keys():
            if np + 's' in noun_phrase_counter:
                noun_phrase_counter[np] += noun_phrase_counter[np + 's']
                del noun_phrase_counter[np + 's']
        '''increase count of shorter form with longer form'''
        for short, long in abbreviations.items():
            if short.lower() in noun_phrase_counter:
                noun_phrase_counter[long.lower()] += noun_phrase_counter[short.lower()]
                del noun_phrase_counter[short.lower()]
        noun_phrases_top = [i[0] for i in noun_phrase_counter.most_common(5) if i[1] > 1]
        noun_phrases_recurring = [i for i, k in noun_phrase_counter.items() if k > 1]

        # bug https://github.com/explosion/spaCy/issues/589
        # self.processed_counter+=1
        # if self.processed_counter%100 == 0:
        # self.nlp.vocab.strings.flush_oov()

        '''bioentity tags'''

        '''filter tags by POS'''
        self.filtered_tags = []
        for tag in tags:
            tokens = self.get_tokens_in_range(self.doc, tag['start'], tag['end'])
            token_pos = set([i.pos_ for i in tokens])
            if token_pos & allowed_tag_pos:
                # if tag['match'] in noun_phrases:
                # print '%s >>>>> %s|%s  <<<<< %s'%(self.doc.text[(t['start'] - 10): t['start']], t['match'],
                # t['category'], self.doc.text[t['end']:t['end'] +10])
                self.filtered_tags.append(tag)
                # else:
                #     print tag['label'], tokens, token_pos
        '''filter out defined acronyms that don't agree'''
        #TODO: if the long form is tagged, search for the short form as well
        acronym_filtered_tags = []
        acronyms_to_extend = {}
        lowered_abbreviations = {i.lower(): i for i in abbreviations}
        lowered_long_forms = {i.lower(): i for i in abbreviations.values()}
        inverted_abbreviations = {v.lower(): k for k, v in abbreviations.items()}
        for tag in self.filtered_tags:
            matched_text = tag['match'].lower()
            if matched_text in lowered_abbreviations:
                long_description = abbreviations[lowered_abbreviations[matched_text]]
                if self._tagger.get_tag_by_match(self.filtered_tags, long_description.lower()):
                    acronym_filtered_tags.append(tag)
            else:
                acronym_filtered_tags.append(tag)
            if matched_text in lowered_long_forms:
                acronyms_to_extend[inverted_abbreviations[matched_text]] = tag
        if acronyms_to_extend:  # extend matches of long form to the short version if needed
            acronym_tags = self._tagger.extend_tags_to_alternative_forms(document, acronyms_to_extend)
            acronym_filtered_tags.extend(acronym_tags)
        acronyms_to_extend_lowered = [i.lower() for i in acronyms_to_extend]
        self.filtered_tags = sorted(acronym_filtered_tags, key=lambda x: (x['start'], -x['end']))

        '''remove tag matching common words'''
        tags_to_remove = []
        for i, tag in enumerate(self.filtered_tags):
            if tag['category'] in SHORT_MATCH_CASE_SENSITIVE_CATEGORIES:
                ''' use case sensive matching for short strings if the word is common'''
                if (len(tag['match']) < 4) or \
                        (len(tag['match']) < 7  and tag['match'] in COMMON_WORDS_CORPUS["brown_corpus"]):
                    original_case = document[tag['start']:  tag['end']]
                    original_case_no_dash = original_case.replace('-', '')
                    original_case_dash_to_space = original_case.replace('-', ' ')
                    if not ((original_case == tag['label'])
                            or (original_case_no_dash == tag['label'])
                            or (original_case_dash_to_space == tag['label'])):
                        tags_to_remove.append(i)
            elif tag['category'] in NOISY_CATEGORIES:
                '''remove common words from matches'''
                if tag['match'] in COMMON_WORDS_CORPUS["brown_corpus"] and  (tag['match'] not in acronyms_to_extend_lowered):
                    tags_to_remove.append(i)

        self.filtered_tags = [i for j, i in enumerate(self.filtered_tags) if j not in tags_to_remove]

        '''Tag TARGET&DISEASE sentences for open targets'''
        for i, sentence in enumerate(self.doc.sents):
            tag_in_sentence = self._tagger.get_tags_in_range(self.filtered_tags, sentence.start_char, sentence.end_char)
            tag_types = set([i['category'] for i in tag_in_sentence])
            if ('GENE' in tag_types) and ('DISEASE' in tag_types):
                self.filtered_tags.append(
                    MatchedTag('target-disease', sentence.start_char, sentence.end_char, 'TARGET&DISEASE',
                               'OPENTARGETS', [''], '', '').__dict__)

        '''store tags for subjects and objects in concepts grouped by their category'''
        sentences_start_chars = [sent.start_char for sent in self.doc.sents]
        for concept in concepts:
            sbj_start = sentences_start_chars[concept['sentence']] + concept['subject_range']['start']
            sbj_end = sentences_start_chars[concept['sentence']] + concept['subject_range']['end']
            sbj_tags = self._tagger.get_tags_in_range(self.filtered_tags,
                                                          sbj_start,
                                                          sbj_end)
            if sbj_tags:
                concept['subject_tags']={}
                sbj_tags_sent_idx = [deepcopy(tag) for tag in sbj_tags]
                for tag in sbj_tags_sent_idx:
                    tag['start']-=sentences_start_chars[concept['sentence']]
                    tag['end'] -= sentences_start_chars[concept['sentence']]
                    tag_class = tag['category']
                    if tag_class not in concept['subject_tags']:
                        concept['subject_tags'][tag_class]=[]
                    concept['subject_tags'][tag_class].append(tag)


            obj_start = sentences_start_chars[concept['sentence']] + concept['object_range']['start']
            obj_end = sentences_start_chars[concept['sentence']] + concept['object_range']['end']
            obj_tags = self._tagger.get_tags_in_range(self.filtered_tags,
                                                          obj_start,
                                                          obj_end)
            if obj_tags:
                concept['object_tags']={}
                obj_tags_sent_idx = [deepcopy(tag) for tag in obj_tags]
                for tag in obj_tags_sent_idx:
                    tag['start'] -= sentences_start_chars[concept['sentence']]
                    tag['end'] -= sentences_start_chars[concept['sentence']]
                    tag_class = tag['category']
                    if tag_class not in concept['object_tags']:
                        concept['object_tags'][tag_class] = []
                    concept['object_tags'][tag_class].append(tag)

        embedding_text = {u'plain': self.to_text(),
                          u'pos_tag': self.to_pos_tagged_text(),
                          u'ent_tag': self.to_entity_tagged_text()}
        return self.doc, \
               dict(chunks=noun_phrases,
                    recurring_chunks=noun_phrases_recurring,
                    top_chunks=noun_phrases_top,
                    abbreviations=[dict(short=k, long=v) for k, v in abbreviations.items()],
                    concepts=concepts,
                    tagged_entities=self.filtered_tags,
                    tagged_entities_grouped=self._tagger.group_matches_by_category_and_reference(self.filtered_tags),
                    tagged_text=self._tagger.mark_tags_in_text(self.doc.text, self.filtered_tags),
                    embedding_text=embedding_text)

    @staticmethod
    def get_tokens_in_range(doc, start, end):
        tokens = []
        for t in doc:
            if start <= t.idx <= end and \
                                    start <= (t.idx + len(t.text)) <= end + 1:
                tokens.append(t)
            elif t.idx > end:
                break
        return tokens

    def digest(self, document):
        return self.process(document)[1]

    def __str__(self):
        return 'nlp'

    def cluster_np(self, noun_phrases):
        '''todo: optimise for speed'''

        clusters = {i: [i] for i in noun_phrases}
        for i in noun_phrases:
            for j in noun_phrases:
                if i != j and i in j.split(' '):
                    # print '%s -> %s'%(i,j)
                    clusters[j].extend(clusters[i])
                    del clusters[i]
                    # elif i != j and j in i:
                    #     print '%s <- %s'%(j,i)
        # pprint(clusters)
        filtered_noun_phrases = []
        for k, v in clusters.items():
            if len(v) > 1:
                longest = sorted(v, key=lambda x: len(x), reverse=True)[0]
                filtered_noun_phrases.append(longest)
            else:
                filtered_noun_phrases.append(v[0])
        # print filtered_noun_phrases
        return filtered_noun_phrases

    def to_pos_tagged_text(self, lower = True):
        text = []
        for sent in self.analysed_sentences:
            text.append(sent.to_pos_tagged_text(lower = lower))
        return u'\n'.join(text)

    def to_text(self, lower = True):
        text = []
        for sent in self.analysed_sentences:
            text.append(sent.to_text(lower = lower))
        return u'\n'.join(text)

    def to_entity_tagged_text(self,
                              tags2skip = ['TARGET&DISEASE'],
                              lower=True,
                              use_pos = False):
        token_tags = {}
        token_refid = {}
        token_labels = {}
        for s_i, s in enumerate(self.doc.sents):
            token_tags[s_i] = {}
            token_refid[s_i] = {}
            token_labels[s_i] = {}
        for tag in self.filtered_tags:
            for s_i, s in enumerate(self.doc.sents):
                if tag['start']>= s.start_char and \
                    tag['end'] <= s.end_char:
                    tag['sentence'] = s_i
                    analyzed_sentence_doc = self.analysed_sentences[s_i].doc
                    tokens = self.get_tokens_in_range(analyzed_sentence_doc, tag['start'] - s.start_char, tag['end'] - s.start_char)
                    if tag['category'] not in tags2skip:
                        for token in tokens:
                            if token.i  not in token_tags[s_i]:
                                token_tags[s_i][token.i] = []
                            token_tags[s_i][token.i].append(tag['category'])
                            if token.i not in token_refid[s_i]:
                                ref = tag['reference']
                                if '/' in ref:#workaround for uris
                                    ref=ref.split('/')[-1]
                                token_refid[s_i][token.i] = ref
                            if token.i  not in token_labels[s_i]:
                                token_labels[s_i][token.i] = MatchedTag.sanitize_string(tag['label'])
                    break
        # for s_i, s in enumerate(self.doc.sents):
        #     analyzed_sentence_doc = self.analysed_sentences[s_i].doc
        #     for token in analyzed_sentence_doc:
        #         if token.i not in token_tags[s_i]:
        #             token_tags[s_i][token.i] = [token.pos_]

        text = []
        for s_i, sent in enumerate(self.analysed_sentences):
            sent_text = sent.to_ent_and_pos_tagged_text(ents = token_tags[s_i],
                                                        ref_ids = token_refid[s_i],
                                                        labels = token_labels[s_i],
                                                        lower=lower,
                                                        use_pos=use_pos)
            text.append(sent_text.encode('ascii',errors='ignore'))
        return u'\n'.join(text)




class SentenceAnalysisSpacy(object):
    def __init__(self,
                 sentence,
                 nlp,
                 abbreviations=None,
                 normalize=True,
                 tagger=None,
                 stopwords = set()):
        self.logger = logging.getLogger(__name__)
        self._normalizer = AbstractNormalizer()
        self._abbreviations_finder = AbbreviationsParser()
        self._tagger = tagger
        self.stopwords = stopwords

        self.tags = []
        self.abbreviations = {}
        if isinstance(sentence, Doc):
            self.sentence = sentence
            self.doc = sentence
            if self._tagger is not None:
                self.tags = self._tagger.tag(self.doc.text)
        elif isinstance(sentence, Span):
            self.sentence = sentence
            self.doc = sentence.doc
            if self._tagger is not None:
                self.tags = self._tagger.tag(self.doc.text)
        elif isinstance(sentence, unicode):
            if not sentence.replace('\n', '').strip():
                raise AttributeError('sentence cannot be empty')
            if normalize:
                sentence = u'' + self._normalizer.normalize(sentence)
            if abbreviations is None:
                self.abbreviations = self._abbreviations_finder.digest_as_dict(sentence)
                # self.logger.info('abbreviations: ' + str(self.abbreviations))

            if abbreviations:
                for short, long in abbreviations:
                    if short in sentence and not long in sentence:
                        sentence = sentence.replace(short, long)
            if self._tagger is not None:
                self.tags = self._tagger.tag(sentence)
            self.sentence = nlp(sentence)
            self.doc = self.sentence
        else:
            raise AttributeError('sentence needs to be unicode or Doc or Span not %s' % sentence.__class__)
            # self.logger.debug(u'Sentence to analyse: '+self.sentence.text)

    def isNegated(self, tok):
        negations = {"no", "not", "n't", "never", "none", "false"}
        for dep in list(tok.lefts) + list(tok.rights):
            if dep.lower_ in negations:
                return True

        # alternatively look for
        #     for child in predicate.children:
        #       if child.dep_ == 'neg':
        #            context = 'Negative'
        return False

    def get_alternative_subjects(self, tok):
        '''given a token, that is a subject of a verb, extends to other possible subjects in the left part of the
        relation'''

        '''get objects in subtree of the subject to be related to objects in the right side of the verb #risk'''
        alt_subjects = [tok]
        allowed_pos = [NOUN, PROPN]
        for sibling in tok.head.children:
            # print sibling, sibling.pos_, sibling.dep_
            if sibling.pos == allowed_pos:
                for sub_subj in sibling.subtree:
                    if sub_subj.dep_ in ANY_NOUN and sub_subj.pos in allowed_pos:  # should check here that there is
                        # an association betweej the subj and these
                        # objects
                        alt_subjects.append(sub_subj)
                        # alt_subjects.append(parsed[sub_subj.left_edge.i : sub_subj.right_edge.i + 1].text.lower())
                '''get other subjects conjuncted to main on to be related to objects in the right side of the verb 
                #risk'''
                for sub_subj in sibling.conjuncts:
                    # print sub_subj, sub_subj.pos_, sub_subj.dep_
                    if sub_subj.dep_ in SUBJECTS and sub_subj.pos in allowed_pos:  # should check here that there is
                        # an association betweej the
                        # subj and these objects
                        alt_subjects.append(sub_subj)
        # print alt_subjects

        # sys.exit()
        return alt_subjects

    def get_extended_verb(self, v):
        '''
        given a verb build a representative chain of verbs for the sintax tree
        :param v:
        :return:
        '''
        verb_modifiers = [prep, agent]
        verb_path = [v]
        verb_text = v.lemma_.lower()
        allowed_lefts_pos = [NOUN, PROPN]
        lefts = list([i for i in v.lefts if i.pos in allowed_lefts_pos and i.dep_ in SUBJECTS])
        '''get anchestor verbs if any'''
        if not v.dep_ == 'ROOT':
            for av in [i for i in v.ancestors if i.pos == VERB and i.dep not in (aux, auxpass)]:
                verb_text = av.lemma_.lower() + ' ' + v.text.lower()
                verb_path.append(av)
                lefts.extend([i for i in av.lefts if i.pos in allowed_lefts_pos and i.dep_ in SUBJECTS])
        for vchild in v.children:
            if vchild.dep in verb_modifiers:
                verb_text += ' ' + vchild.text.lower()
        return verb_text, verb_path, lefts

    def get_verb_path_from_ancestors(self, tok):
        '''
        given a token return the chain of verbs of his ancestors
        :param tok:
        :return:
        '''
        return [i for i in tok.ancestors if i.pos == VERB and i.dep != aux]

    def get_extended_token(self, tok):
        '''
        given a token find a more descriptive string extending it with its chindren
        :param tok:
        :param doc:
        :return:
        '''
        allowed_pos = [NOUN, ADJ, PUNCT, PROPN]
        if 'Parkinson' in tok.text:
            pass
        allowed_dep = ["nsubj", "nsubjpass", "csubj", "csubjpass", "agent", "expl", "dobj", "attr", "oprd", "pobj",
                       # "conj",
                       "compound", "amod", "meta", "npadvmod", "nmod",
                       "amod"]  # , add "prep" to extend for "of and "in"
        extended_tokens = [i for i in tok.subtree if (i.dep_ in allowed_dep and i in tok.children) or (i == tok)]
        # just get continous tokens
        span_range = [tok.i, tok.i]
        ext_tokens_i = [i.i for i in extended_tokens]
        max_bound = max(ext_tokens_i)
        min_bound = min(ext_tokens_i)
        curr_pos = tok.i
        for cursor in range(tok.i, max_bound + 1):
            if cursor in ext_tokens_i:
                if cursor == curr_pos + 1:
                    span_range[1] = cursor
                    curr_pos = cursor

        curr_pos = tok.i
        for cursor in range(tok.i, min_bound - 1, -1):
            if cursor in ext_tokens_i:
                if cursor == curr_pos - 1:
                    span_range[0] = cursor
                    curr_pos = cursor
        span = Span(self.doc, span_range[0], span_range[1] + 1)
        return span

    def traverse_obj_children(self, tok, verb_path):
        '''
        iterate over all the children and the conjuncts to return objects within the same chain of verbs
        :param tok:
        :param verb_path:
        :return:
        '''
        for i in tok.children:
            # print i, verb_path, get_verb_path_from_ancestors(i), get_verb_path_from_ancestors(i) ==verb_path
            if i.dep_ in OBJECTS and (self.get_verb_path_from_ancestors(i) == verb_path):
                yield i
            else:
                self.traverse_obj_children(i, verb_path)
        for i in tok.conjuncts:
            # print i, verb_path, get_verb_path_from_ancestors(i), get_verb_path_from_ancestors(i) ==verb_path
            if i.dep_ in OBJECTS and (self.get_verb_path_from_ancestors(i) == verb_path):
                yield i
            else:
                self.traverse_obj_children(i, verb_path)

    def to_nltk_tree(self, node):
        def tok_format(tok):
            return " ".join(['"%s"' % tok.orth_, tok.tag_, tok.pos_, tok.dep_])

        if node.n_lefts + node.n_rights > 0:
            return nltk.Tree(tok_format(node), [self.to_nltk_tree(child) for child in node.children])
        else:
            return tok_format(node)

    def print_syntax_tree(self):
        for t in self.sentence:
            if t.dep_ == 'ROOT':
                tree = self.to_nltk_tree(t)
                if isinstance(tree, nltk.Tree):
                    tree.pretty_print(stream=self)

    def get_dependent_obj(self, tok, verb_path):
        '''
        given a token find related objects for the sape chain of verbs (verb_path
        :param tok:
        :param verb_path:
        :return:
        '''
        all_descendants = []
        if tok.dep_ in OBJECTS and (self.get_verb_path_from_ancestors(tok) == verb_path):
            all_descendants.append(tok)
        for i in tok.subtree:
            all_descendants.extend(list(self.traverse_obj_children(i, verb_path)))
        descendants = list(set(all_descendants))
        return_obj = [i for i in descendants]
        return return_obj

    def print_syntax_list(self):
        output = [''
                  ]
        output.append(' | '.join(('i', 'text', 'pos', 'dep', 'head')))
        for k, t in enumerate(self.sentence):
            output.append(' | '.join((str(t.i), '"' + t.text + '"', t.pos_, t.dep_, t.head.text)))
        self.logger.debug('\n'.join(output))

    def collapse_noun_phrases_by_punctation(self):
        '''
        this collapse needs tobe used on a single sentence, otherwise it will ocncatenate different sentences
        :param sentence:
        :return:
        '''
        prev_span = ''
        open_brackets = u'( { [ <'.split()
        closed_brackets = u') } ] >'.split()
        for token in self.sentence:
            try:
                if token.text in open_brackets and token.whitespace_ == u'':
                    next_token = token.nbor(1)
                    if any([i in next_token.text for i in closed_brackets]):
                        span = Span(self.doc, token.i, next_token.i + 1)
                        # prev_span = span.text
                        yield span
                elif any([i in token.text for i in open_brackets]):
                    next_token = token.nbor(1)
                    if next_token.text in closed_brackets:
                        span = Span(self.doc, token.i, next_token.i + 1)
                        # prev_span = span.text
                        yield span

            except IndexError:  # skip end of sentence
                pass

    def collapse_noun_phrases_by_syntax(self):
        not_allowed_conjunction_dep = [prep]
        for token in self.sentence:
            if token.pos in [NOUN, PROPN]:
                extended = self.get_extended_token(token)
                if extended.text != token.text:
                    yield extended
                siblings = list(token.head.children)
                span_range = [token.i, token.i]
                for sibling in siblings:
                    if sibling.dep == token.dep  and sibling.dep_ in not_allowed_conjunction_dep:
                        if sibling.i > token.i:
                            span_range[1] = sibling.i
                        elif sibling.i < token.i:
                            span_range[0] = sibling.i

                if span_range != [token.i, token.i]:
                    span = Span(self.doc, span_range[0], span_range[1] + 1)
                    yield span

    def analyse(self, merge_with_syntax=True, verbose=False):
        '''extract concepts'''

        '''collapse noun phrases based on syntax tree'''
        noun_phrases = list(self.collapse_noun_phrases_by_punctation())
        for np in noun_phrases:
            np.merge()
        noun_phrases = list(self.collapse_noun_phrases_by_syntax())
        if merge_with_syntax:
            for np in noun_phrases:
                np.merge()
        if verbose:
            self.print_syntax_list()
            self.print_syntax_tree()

        self.concepts = []
        noun_phrases = []
        verbs = [tok for tok in self.sentence if tok.pos == VERB and tok.dep not in (aux, auxpass)]
        for v in verbs:
            verb_text, verb_path, subjects = self.get_extended_verb(v)
            rights = list([i for i in v.rights if i.pos != VERB])
            # print v, subjects, rights
            for subject in subjects:
                for any_subject in self.get_alternative_subjects(subject):
                    noun_phrases.append(any_subject)
                    for r in rights:
                        dependend_objects = self.get_dependent_obj(r, verb_path)
                        for do in dependend_objects:
                            noun_phrases.append(do)
                            verb_subtree =self.doc[v.left_edge.i: v.right_edge.i + 1].text
                            concept =dict(
                                subject=any_subject.text,
                                subject_range = dict(start=any_subject.idx,
                                                     end=any_subject.idx + len(any_subject.text)),
                                object=do.text,
                                object_range = dict(start=do.idx,
                                                    end=do.idx + len(do.text)),
                                verb=verb_text,
                                verb_path=[i.text for i in verb_path],
                                # subj_ver='%s -> %s' % (any_subject.text, verb_text),
                                # ver_obj='%s -> %s' % (verb_text, do.text),
                                # concept='%s -> %s -> %s' % (any_subject.text, verb_text, do.text),
                                negated=self.isNegated(v) or self.isNegated(any_subject) or \
                                        self.isNegated(do),
                                sentence_text = self.doc.text
                            )
                            if verb_subtree != self.doc.text:
                                concept['verb_subtree'] = verb_subtree
                            self.concepts.append(concept)
        self.noun_phrases = list(set(noun_phrases))
        # self.logger.info(self.noun_phrases)
        # for c in self.concepts:
        #     self.logger.info(c['concept'])

        # for tag in self.tags:
        #     print tag, self.doc[tag['start'], tag['end']]

    def __str__(self):
        return self.sentence.text

    def write(self, message):
        '''needed to print nltk graph to logging'''
        if message != '\n':
            self.logger.debug(message)

    def to_pos_tagged_text(self, lower = True):
        text = []
        for token in self.doc:
            if token.text and (token.pos != PUNCT and token.text.lower() not in self.stopwords):
                if lower:
                    text.append(token.text.strip().replace(u' ', u'_').lower()+u'|'+token.pos_)
                else:
                    text.append(token.text.strip().replace(u' ', u'_')+u'|'+token.pos_)
        return u' '.join(text)

    def to_text(self, lower = True):
        text = []
        for token in self.doc:
            if token.text and (token.pos != PUNCT and token.text.lower() not in self.stopwords):
                text_to_append =  token.text.strip().replace(u' ', u'_')
                if lower:
                    text_to_append = text_to_append.lower()
                text.append(text_to_append)
        return u' '.join(text)

    def to_ent_and_pos_tagged_text(self,
                                   ents,
                                   ref_ids,
                                   labels,
                                   lower=True,
                                   use_pos = False):
        text = []
        for token in self.doc:
            if token.text and (token.pos != PUNCT and token.text.lower() not in self.stopwords):
                pos = token.pos_
                if token.i in ref_ids:
                    token_text = ref_ids[token.i]
                else:
                    token_text = token.text.strip()
                if lower:
                    token_text = token_text.lower()
                token_text= token_text.replace(u' ', u'_')
                if use_pos:
                    token_text+=u'|'+pos
                if token.i in ents:
                    ent = u'_'.join(ents[token.i])
                    token_text+=u'|'+ent
                if token.i in labels:
                    # try:
                        token_text+=u'|'+labels[token.i]
                    # except UnicodeDecodeError:
                    #     pass#TODO: handle non ascii labels
                text.append(token_text)
        return u' '.join(text)
