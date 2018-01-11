import ahocorasick
import logging
import string
import sys
import time
import unicodedata

import requests
from fuzzywuzzy import fuzz
from rope.base.codeanalyze import ChangeCollector

from BioStopWords import DOMAIN_STOP_WORDS
from modules.vocabulary import vocabulary_urls

unicode_punctation_table = dict.fromkeys(i for i in xrange(sys.maxunicode)
                                         if unicodedata.category(unichr(i)).startswith('P'))


class BioEntityTagger(object):
    separators_all = [' ', '.', ',', ';', ':', ')', ']', '(', '[', '{', '}', '/', '\\', '"', "'", '?', '!', '<', '>',
                      '+', '-']

    def __init__(self,
                 partial_match=False,
                 ignorecase=True,
                 stopwords=None):
        '''

        :param partial_match:  allow for matching a non clomplete word
        :param ignorecase: case sensitive or not
        :param stopwords: stopwords to skip, defaults to a very broad list
        '''
        self.A = ahocorasick.Automaton()
        self.partial_match = partial_match
        self.ignorecase = ignorecase
        if stopwords is None:
            stopwords = DOMAIN_STOP_WORDS
        idx = 0
        s = requests.Session()
        '''get the dictionaries from remote files'''
        for dictionary_url in vocabulary_urls:
            max_retry = 3
            retry = 0
            while retry < max_retry:
                dictionary_request = s.get(dictionary_url)
                if not dictionary_request.ok:
                    time.sleep(1)
                    retry += 1
                else:
                    break
            if not dictionary_request.ok:
                logging.error('cannot download dictionary %s, skipped' % dictionary_url)
                continue
            dictionary = dictionary_request.json()
            category, reference_db = dictionary_url.split('/')[-1].split('.')[0].split('_')[0].split('-')
            '''load the elements in the Automation if they are not too short or are stopwords'''
            for element, element_data in dictionary.items():
                ids = element_data['ids']
                pref_name = element_data['pref_name']
                if len(element) > 2:
                    element_str = element.encode('utf-8')
                    if ((len(element_str) < 5) and (element_str not in stopwords) or \
                                    (len(element_str) >= 5) and (element_str.lower() not in stopwords)):
                        idx += 1
                        if self.ignorecase:
                            element_match = element_str.lower()
                        else:
                            element_match = element_str
                        self.add_tag(element_match,
                                     idx,
                                     category,
                                     reference_db,
                                     [i.encode('utf-8') for i in ids],
                                     element,
                                     element_match,
                                     pref_name)
                        '''handle elements with dashes by also creating a copy without'''
                        if '-' in element_match:
                            element_match_without_dash = element_match.replace('-', '')
                            if len(element_match_without_dash) > 2:
                                self.add_tag(element_match_without_dash,
                                             idx,
                                             category,
                                             reference_db,
                                             [i.encode('utf-8') for i in ids],
                                             element,
                                             element_match_without_dash,
                                             pref_name)
                        '''if supporting partial match'''
                        if self.partial_match:
                            for longest_token in element.split():
                                if longest_token != element and len(
                                        longest_token) > 5 and longest_token.lower() not in stopwords:
                                    self.add_tag(longest_token,
                                                 idx,
                                                 category + '-TOKEN',
                                                 reference_db,
                                                 [i.encode('utf-8') for i in ids],
                                                 element,
                                                 longest_token,
                                                 pref_name)

        s.close()
        self.A.make_automaton()

    def add_tag(self, element_text, idx, category, reference_db, ids, element, match, pref_name):
        unique_resource_key = category + '|' + reference_db
        category_insert = [category]
        reference_db_insert = [reference_db]
        ids_insert = [[i.encode('utf-8') for i in ids]]
        previous_annotation = self.A.get(element_text, None)

        if previous_annotation is None:
            annotation = [idx,
                          category_insert,
                          reference_db_insert,
                          ids_insert,
                          element,
                          match,
                          pref_name]

            self.A.add_word(element_text,
                            annotation)
        else:
            previous_keys = []
            for j in range(len(previous_annotation[1])):
                previous_keys.append(previous_annotation[1][j] + '|' + previous_annotation[2][j])
            if unique_resource_key not in previous_keys:
                previous_annotation[1].extend(category_insert)
                previous_annotation[2].extend(reference_db_insert)
                previous_annotation[3].extend(ids_insert)  # TODO: might need to merge addidional ids if the
                # uniquekey is passed before
                self.A.add_word(element_text, previous_annotation)

    def tag(self, text):
        return self._tag(text, self.A, self.ignorecase)

    @staticmethod
    def _tag(text, automation, ignorecase=True):
        '''
        finds tags in a text
        :param text: text to tag
        :param automation: automation to use
        :param ignorecase: deafault to True
        :return:
        '''
        if isinstance(text, unicode):
            text_to_tag = text.encode('utf-8')
        else:
            text_to_tag = text
        if ignorecase:
            text_to_tag = text_to_tag.lower()
        matches = []
        for i in automation.iter(text_to_tag.lower()):
            if len(i[1]) < 7:
                print i
        for end_index, (insert_order, category_list, reference_db_list, entity_id_list, original_value, match,
                        pref_name) in automation.iter(text_to_tag.lower()):
            start_index = end_index - len(match) + 1
            end_index += 1

            if (start_index == 0 or text_to_tag[start_index - 1] in BioEntityTagger.separators_all) and \
                    (end_index == len(text_to_tag) or text_to_tag[end_index] in BioEntityTagger.separators_all):
                for j in range(len(category_list)):
                    category = category_list[j]
                    reference_db = reference_db_list[j]
                    entity_id = entity_id_list[j]
                    if isinstance(entity_id, list):
                        entity_id = entity_id[0]
                    if category.endswith('-TOKEN'):
                        pre, post = original_value.split(match)[:2]
                        potential_match = text_to_tag[start_index:end_index + len(post)]
                        score = fuzz.token_sort_ratio(original_value, potential_match)
                        if score > 90:
                            tag = MatchedTag(match, start_index, end_index, category.replace('-TOKEN', ''),
                                             reference_db,
                                             entity_id, original_value, pref_name)
                            matches.append(tag.__dict__)
                    else:
                        tag = MatchedTag(match, start_index, end_index, category, reference_db, entity_id,
                                         original_value, pref_name)
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
    def group_matches_by_category_and_reference(matches):
        grouped_by_category_type = {}
        for match in matches:
            key = match['category'] + '|' + match['reference_db']
            if key not in grouped_by_category_type:
                grouped_by_category_type[key] = []
            grouped_by_category_type[key].append(match)

        return grouped_by_category_type

    @staticmethod
    def remove_nested_matches(matches):
        filtered_matches = []
        sorted_matches = sorted(matches, key=lambda x: (x['start'], -x['end']))
        for i, tag_i in enumerate(sorted_matches):
            keep = True
            for j, tag_j in enumerate(sorted_matches):
                if i != j:
                    if tag_j['start'] <= tag_i['start'] <= tag_j['end'] and \
                                            tag_j['start'] <= tag_i['end'] <= tag_j['end']:
                        keep = False
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
        '''
        produce a text with the tags written as markup
        :param text: text to tags
        :param matches: tags to encode
        :return:
        '''
        text_to_tag = text
        tagged_abstract = ''
        if isinstance(text, unicode):
            text_to_tag = text.encode('utf-8')
        try:
            tagged_abstract = ChangeCollector(text_to_tag)
            for i, tag in enumerate(
                    sorted(matches, key=lambda x: (x['start'], -x['end']))):
                if isinstance(tag['reference'], (list, tuple)):
                    tag_reference = '|'.join(tag['reference'])
                else:
                    tag_reference = tag['reference']
                tagged_abstract.add_change(tag['start'], tag['start'],
                                           '<mark-%s data-entity="%s" reference-db="%s"  reference="%s">' % (
                                               str(i), tag['category'], tag['reference_db'], tag_reference))
                tagged_abstract.add_change(tag['end'], tag['end'], '</mark-%s>' % str(i))
            tagged_abstract = '<div  class="entities">%s</div></br>' % tagged_abstract.get_changed()
        except UnicodeDecodeError:
            logging.error('cannot generate maked text for unicode decode error')
        return tagged_abstract

    @staticmethod
    def get_tags_in_range(matches, start, end):
        filtered_tag = []
        for t in matches:
            if start <= t['start'] <= end and \
                                    start <= t['end'] <= end:
                filtered_tag.append(t)
            elif t['end'] > end:
                break

        return filtered_tag

    @staticmethod
    def get_tag_by_match(tags, match):
        matched_tags = []
        for tag in tags:
            if tag['match'].lower() == match.lower():
                matched_tags.append(match)
        return []

    @staticmethod
    def extend_tags_to_alternative_forms(text, extended_forms):
        A = ahocorasick.Automaton()
        for text_to_match, payload in extended_forms.items():
            A.add_word(text_to_match.lower(),
                       [0, [payload['category']], [payload['reference_db']], [payload['reference']],
                        payload['original_value'],
                        text_to_match.lower(), payload['label']])
        A.make_automaton()

        return BioEntityTagger._tag(text, A, )


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
                 sentence=None
                 ):
        self.match = match
        self.start = start
        self.end = end
        self.category = category
        self.reference_db = reference_db
        self.reference = reference
        self.original_value = original_value
        self.label = label
        self.sentence = sentence

    @staticmethod
    def sanitize_string(s):
        if isinstance(s, unicode):
            return s.translate(unicode_punctation_table)
        elif isinstance(s, str):
            return unicode(s.translate(string.maketrans(' ', '_'), string.punctuation))
        else:
            return u''

# TODO: use inflection.table.ascii from SPECIALIST lexicon to enhance matching forms
