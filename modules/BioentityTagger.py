import ahocorasick

import logging
import string

import requests
import time
from fuzzywuzzy import fuzz
from rope.base.codeanalyze import ChangeCollector

from BioStopWords import DOMAIN_STOP_WORDS

dictionary_urls= [
  "https://storage.googleapis.com/opentargets-bioentity-dictionary/ANATOMY-MESH.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/ANTROPOLOGY-MESH.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/CHEMICAL-MESH.json",
  "https://storage.googleapis.com/opentargets-bioentity-dictionary/DIAGNOSTICS-MESH.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/DISCIPLINE-MESH.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/DISEASE-EPMC.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/DISEASE-MESH.json",
  "https://storage.googleapis.com/opentargets-bioentity-dictionary/DISEASE-OPENTARGETS.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/GENE-EPMC.json",
  "https://storage.googleapis.com/opentargets-bioentity-dictionary/HEALTHCARE-MESH.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/HUMANITIES-MESH.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/INFORMATIONSCIENCE-MESH.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/LOC-MESH.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/NAMEDGROUP-MESH.json",
  "https://storage.googleapis.com/opentargets-bioentity-dictionary/ORGANISM-MESH.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/PATHWAY-OPENTARGETS.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/PHENOTYPE-EPMC.json",
  "https://storage.googleapis.com/opentargets-bioentity-dictionary/PROCESS-MESH.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/PROTEINCOMPLEX-CHEMBL.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/PROTEINCOMPLEX-COMPLEXPORTAL.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/PROTEINCOMPLEX-CORUM.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/PROTEINCOMPLEX-GO.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/PSICHIATRY-MESH.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/PUBLICATION-MESH.json",
  "https://storage.googleapis.com/opentargets-bioentity-dictionary/TARGET-OPENTARGETS.json",
  # "https://storage.googleapis.com/opentargets-bioentity-dictionary/TECHNOLOGY-MESH.json"
]

class BioEntityTagger(object):
    separators_all = [' ', '.', ',', ';', ':', ')', ']', '(', '[', '{', '}', '/', '\\','"',"'", '?', '!', '<', '>', '+', '-']


    def __init__(self, partial_match = False, ignorecase = True):
        self.A = ahocorasick.Automaton()
        self.partial_match = partial_match
        self.ignorecase = ignorecase
        self.tag_labels = {}

        idx = 0
        s = requests.Session()
        for dictionary_url in dictionary_urls:
            max_retry = 3
            retry = 0
            while retry < max_retry:
                dictionary_request = s.get(dictionary_url)
                if not dictionary_request.ok:
                    time.sleep(1)
                    retry+=1
                else:
                    break
            if not dictionary_request.ok:
                logging.error('cannot download dictionary %s, skipped'%dictionary_url)
                continue
            dictionary = dictionary_request.json()
            category, reference_db = dictionary_url.split('/')[-1].split('.')[0].split('_')[0].split('-')
            for element, ids in dictionary.items():
                if len(element) > 2:
                    idx += 1
                    element_str = element.encode('utf-8')
                    if self.ignorecase:
                        element_match = element_str.lower()
                    else:
                        element_match = element_str
                    self.add_tag(element_match, idx, category, reference_db, [i.encode('utf-8') for i in ids], element, element_match)
                    if '-' in element_match:
                        element_match_without_dash =element_match.replace('-', '')
                        self.add_tag(element_match_without_dash, idx, category, reference_db, [i.encode('utf-8') for i in ids], element, element_match_without_dash)
                        element_match_without_dash = element_match.replace('-', ' ')
                        self.add_tag(element_match_without_dash, idx, category, reference_db,
                                     [i.encode('utf-8') for i in ids], element, element_match_without_dash)
                    if self.partial_match:
                        for longest_token in element.split():
                            if longest_token != element  and len(longest_token) >5 and longest_token.lower() not in DOMAIN_STOP_WORDS:
                                self.add_tag(longest_token, idx, category+'-TOKEN', reference_db, [i.encode('utf-8') for i in ids], element,
                                                 longest_token)

        s.close()
        self.A.make_automaton()

    def add_tag(self,element_text,  idx, category, reference_db, ids, element, match):
        unique_resource_key = category + '|' + reference_db
        category_insert = [category]
        reference_db_insert = [reference_db]
        ids_insert = [[i.encode('utf-8') for i in ids]]
        previous_annotation =  self.A.get(element_text, None)
        for id_insert in ids_insert[0]:
            unique_id = id_insert+'|'+ unique_resource_key
            if unique_id not in self.tag_labels:
                self.tag_labels[unique_id] = self.sanitize_string(element_text)

        if previous_annotation is None:
            self.A.add_word(element_text,
                            [idx, category_insert, reference_db_insert, ids_insert, element, match])
        else:
            previous_keys = []
            for j in range(len(previous_annotation[1])):
                previous_keys.append(previous_annotation[1][j] + '|' + previous_annotation[2][j])
            if unique_resource_key not in previous_keys:
                previous_annotation[1].extend(category_insert)
                previous_annotation[2].extend(reference_db_insert)
                previous_annotation[3].extend(ids_insert)#TODO: might need to merge addidional ids if the uniquekey is passed before
                self.A.add_word(element_text,previous_annotation)

    def tag(self, text):
        return self._tag(text, self.A, self.ignorecase, self.tag_labels)

    @staticmethod
    def sanitize_string(s):
        return s.translate(string.maketrans(' ','_'),string.punctuation)

    @staticmethod
    def _tag(text, automation, ignorecase = True, labels ={}):
        if isinstance(text, unicode):
            text_to_tag = text.encode('utf-8')
        else:
            text_to_tag = text
        if ignorecase:
            text_to_tag = text_to_tag.lower()
        matches = []
        for end_index, (insert_order, category_list, reference_db_list, entity_id_list, original_value, match) in automation.iter(text_to_tag.lower()):
            start_index = end_index - len(match) + 1
            end_index+=1

            if (start_index == 0 or text_to_tag[start_index - 1] in BioEntityTagger.separators_all) and \
                    (end_index == len(text_to_tag) or text_to_tag[end_index] in BioEntityTagger.separators_all):
                for j in range(len(category_list)):
                    category=category_list[j]
                    reference_db = reference_db_list[j]
                    entity_id = entity_id_list[j]
                    if isinstance(entity_id, list):
                        entity_id = entity_id[0]
                    unique_entity_id = '|'.join([entity_id,category, reference_db])
                    entity_label = ''
                    if unique_entity_id in labels:
                        entity_label = labels[unique_entity_id]
                    if category.endswith('-TOKEN'):
                        pre, post = original_value.split(match)[:2]
                        potential_match = text_to_tag[start_index:end_index + len(post)]
                        score = fuzz.token_sort_ratio(original_value, potential_match)
                        if score > 90:
                            tag = MatchedTag(match, start_index, end_index, category.replace('-TOKEN', ''), reference_db,
                                             entity_id, original_value, entity_label)
                            matches.append(tag.__dict__)
                    else:
                        tag = MatchedTag(match, start_index, end_index, category, reference_db, entity_id, original_value, entity_label)
                        matches.append(tag.__dict__)
            else:
                pass

        grouped_matches = BioEntityTagger.group_matches_by_category_and_reference(matches)
        filtered_matches = []
        for group, matches_in_group in grouped_matches.items():
            non_nested_matches = BioEntityTagger.remove_nested_matches(matches_in_group)
            filtered_matches.extend(non_nested_matches)


        return filtered_matches

    @staticmethod
    def group_matches_by_category_and_reference( matches):
        grouped_by_category_type = {}
        for match in matches:
            key = match['category'] + '|' + match['reference_db']
            if key not in grouped_by_category_type:
                grouped_by_category_type[key]=[]
            grouped_by_category_type[key].append(match)

        return grouped_by_category_type

    @staticmethod
    def remove_nested_matches( matches):
        filtered_matches = []
        sorted_matches =  sorted(matches, key=lambda x: (x['start'], -x['end']))
        for i, tag_i in enumerate(sorted_matches ):
            keep = True
            for j, tag_j in enumerate(sorted_matches):
                if i!= j:
                    if tag_j['start']<=tag_i['start']<=tag_j['end'] and \
                        tag_j['start'] <= tag_i['end'] <= tag_j['end']:
                        keep=False
                        break
                    elif tag_j['start'] > tag_i['start']:
                        break
                    else:
                        pass
            if keep:
                filtered_matches.append(tag_i)
        return filtered_matches

    @staticmethod
    def mark_tags_in_text(text, matches):
        text_to_tag = text
        tagged_abstract = ''
        if isinstance(text, unicode):
            text_to_tag = text.encode('utf-8')
        try:
            tagged_abstract = ChangeCollector(text_to_tag)
            for i, tag in enumerate(
                    sorted(matches, key=lambda x: (x['start'], -x['end']))):
                tagged_abstract.add_change(tag['start'], tag['start'],
                                           '<mark-%s data-entity="%s" reference-db="%s"  reference="%s">' % (
                                           str(i), tag['category'],tag['reference_db'], '|'.join(tag['reference'])))
                tagged_abstract.add_change(tag['end'], tag['end'], '</mark-%s>' % str(i))
            tagged_abstract = '<div  class="entities">%s</div></br>' % tagged_abstract.get_changed()
        except UnicodeDecodeError:
            logging.error('cannot generate maked text for unicode decode error')
        return tagged_abstract

    @staticmethod
    def get_tags_in_range(matches, start, end):
        filtered_tag = []
        for t in matches:
            if start<=t['start']<=end and \
                start <= t['end'] <= end:
                filtered_tag.append(t)
            elif t['end']> end:
                break

        return filtered_tag

    @staticmethod
    def get_tag_by_match(tags, match):
        matched_tags = []
        for tag in tags:
            if tag['match'].lower()==match.lower():
                matched_tags.append(match)
        return []

    @staticmethod
    def extend_tags_to_alternative_forms(text, extended_forms, labels = {}):
        A = ahocorasick.Automaton()
        for text_to_match, payload in extended_forms.items():
            A.add_word(text_to_match.lower(),
                           [0, [payload['category']], [payload['reference_db']], [payload['reference']], payload['label'], text_to_match.lower()])
        A.make_automaton()

        return BioEntityTagger._tag(text, A, labels = labels)



class MatchedTag(object):
    def __init__(self,
                 match,
                 start,
                 end,
                 category,
                 reference_db,
                 reference,
                 original_value,
                 label,
                 sentence = None
                 ):
        self.match = match
        self.start = start
        self.end = end
        self.category = category
        self.reference_db = reference_db
        self.reference = reference
        self.original_value = original_value
        self.label = label
        self.sentence = None


# TODO: use inflection.table.ascii from SPECIALIST lexicon to enhance matching forms