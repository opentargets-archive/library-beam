#!/usr/local/bin/python
# -*- coding: UTF-8 -*-
import os
import unittest
from lxml import etree
from tqdm import tqdm

from main import parse_medline_xml
from modules.BioentityTagger import BioEntityTagger
from modules.NLP import init_spacy_english_language, SentenceAnalysisSpacy, DocumentAnalysisSpacy

class MedlineParser(unittest.TestCase):

    def testParsing(self):
        file_name = 'resources/cancer_small.xml'
        tree = etree.parse(file_name)
        out = open('resources/pubmed_result.abstract.txt','w')
        for element in tqdm(tree.iter('MedlineCitation')):
            parsed = next(parse_medline_xml(etree.tostring(element),file_name))
            if parsed['abstract']:
                try:
                    out.write(parsed['abstract'].encode('utf-8').replace('\n','')+'\n')
                except Exception as e:
                    print 'could not parse', e



if __name__ == '__main__':
    unittest.main()
