#!/usr/local/bin/python
# -*- coding: UTF-8 -*-
import codecs
import json
import os
import unittest

from modules.BioentityTagger import BioEntityTagger
from modules.NLP import init_spacy_english_language, SentenceAnalysisSpacy, DocumentAnalysisSpacy

chromosome8p_text = u'Chromosome 8p as a potential hub for developmental neuropsychiatric disorders: implications for ' \
               u'schizophrenia, autism and cancer. Defects in genetic and developmental processes are thought to ' \
               u'contribute susceptibility to autism and schizophrenia. Presumably, owing to etiological complexity ' \
               u'identifying susceptibility genes and abnormalities in the development has been difficult. However, ' \
               u'the importance of genes within chromosomal 8p region for neuropsychiatric disorders and cancer is ' \
               u'well established. There are 484 annotated genes located on 8p; many are most likely oncogenes and ' \
               u'tumor-suppressor genes.   Molecular      genetics and developmental studies have identified 21 genes in ' \
               u'this region (ADRA1A, ARHGEF10, CHRNA2, CHRNA6, CHRNB3, DKK4, DPYSL2, EGR3, FGF17, FGF20, FGFR1, ' \
               u'FZD3, LDL, NAT2, NEF3, NRG1, PCM1, PLAT, PPP3CC, SFRP1 and VMAT1/SLC18A1) that are most likely to ' \
               u'contribute to neuropsychiatric disorders (schizophrenia, autism, bipolar disorder and depression), ' \
               u'neurodegenerative disorders (Parkinson\'s and Alzheimer\'s disease) and cancer. Furthermore, ' \
               u'at least seven nonprotein-coding RNAs (microRNAs) are located at 8p. Structural variants on 8p, ' \
               u'such as copy number variants, microdeletions or microduplications, might also contribute to autism, ' \
               u'schizophrenia and other human diseases including cancer. In this review, we consider the current ' \
               u'state of evidence from cytogenetic, linkage, association, gene expression and endophenotyping ' \
               u'studies for the role of these 8p genes in neuropsychiatric disease. We also describe how a mutation ' \
               u'in an 8p gene (Fgf17) results in a mouse with deficits in specific components of social behavior and ' \
               u'a reduction in its dorsomedial prefrontal cortex. We finish by discussing the biological connections ' \
               u'of 8p with respect to neuropsychiatric disorders and cancer, despite the shortcomings of this ' \
               u'evidence.'


def _concept_exists(
        subject,
        verb,
        object,
        concept_list,
        ignore_case=False):
    for c in concept_list:
        if ignore_case:
            if c['subject'].lower() == subject.lower() and \
                            c['verb'].lower() == verb.lower() and \
                            c['object'].lower() == object.lower():
                return True
        else:
            if c['subject'] == subject and \
                            c['verb'] == verb and \
                            c['object'] == object:
                return True
    return False

class SpacySentenceNLPTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nlp = init_spacy_english_language()


    def test_doc(self):
        text = u'Asthma is a chronic disease characterized by airway inflammation, obstruction and hyperresponsiveness.'

        doc = self.nlp(text)
        sentence = SentenceAnalysisSpacy(doc, self.nlp)
        sentence.analyse()
        self.assertTrue(_concept_exists(subject=u'Asthma',
                                             verb=u'be',
                                             object=u'chronic disease',
                                             concept_list=sentence.concepts))

    def test_span(self):
        text = u'Asthma is a chronic disease characterized by airway inflammation, obstruction and ' \
               u'hyperresponsiveness. ' \
               u'Severe asthma affects a small proportion of subjects but results in most of the morbidity, ' \
               u'costs and mortality ' \
               u'associated with the disease.'

        doc = self.nlp(text)
        for span in doc.sents:
            sentence = SentenceAnalysisSpacy(span, self.nlp)
            sentence.analyse()
            self.assertTrue(_concept_exists(subject=u'Asthma',
                                                 verb=u'be',
                                                 object=u'chronic disease',
                                                 concept_list=sentence.concepts))
            break

    def test_asthma(self):
        text = u'Asthma is a chronic disease characterized by airway inflammation, obstruction and hyperresponsiveness.'
        expected_noun_phrases = set(
            ['chronic disease', 'airway inflammation', 'obstruction', 'Asthma', 'hyperresponsiveness'])

        sentence = SentenceAnalysisSpacy(text, self.nlp)
        sentence.analyse()
        noun_phrases = set([i.text for i in sentence.noun_phrases])

        self.assertTrue(_concept_exists(subject=u'Asthma',
                                             verb=u'be',
                                             object=u'chronic disease',
                                             concept_list=sentence.concepts))
        self.assertTrue(_concept_exists(subject=u'Asthma',
                                             verb=u'be characterized by',
                                             object=u'hyperresponsiveness',
                                             concept_list=sentence.concepts))
        self.assertTrue(_concept_exists(subject=u'Asthma',
                                             verb=u'be characterized by',
                                             object=u'airway inflammation',
                                             concept_list=sentence.concepts))
        self.assertTrue(_concept_exists(subject=u'Asthma',
                                             verb=u'be characterized by',
                                             object=u'obstruction',
                                             concept_list=sentence.concepts))

        self.assertEqual(noun_phrases, expected_noun_phrases)

    def test_clinical_trials_and_il5_antiodies(self):
        text = u'Recently,  more and more clinical trials have been performed to evaluate the effects of ' \
               u'anti-interleukin (IL)-5 antibodies in eosinophilic asthma.'

        # TODO: should be this:
        # expected_noun_phrases = set(
        #     ['anti-interleukin (IL)-5 antibodies', 'effects', 'clinical trials', 'eosinophilic asthma'])
        expected_noun_phrases = set(
            ['anti-interleukin', 'effects', 'clinical trials', 'eosinophilic asthma'])
        sentence = SentenceAnalysisSpacy(text, self.nlp)
        sentence.analyse()
        noun_phrases = set([i.text for i in sentence.noun_phrases])

        self.assertTrue(_concept_exists(subject=u'clinical trials',
                                             verb=u'perform evaluate',
                                             object=u'effects',
                                             concept_list=sentence.concepts))
        self.assertTrue(_concept_exists(subject=u'clinical trials',
                                             verb=u'perform evaluate',
                                             object=u'eosinophilic asthma',
                                             concept_list=sentence.concepts))
        self.assertTrue(_concept_exists(subject=u'clinical trials',
                                             verb=u'perform evaluate',
                                             object=u'anti-interleukin',
                                             concept_list=sentence.concepts))

        self.assertEqual(noun_phrases, expected_noun_phrases)

    def test_serum_level(self):
        '''test verb descriptor to be collected'''
        text = u'The serum levels of CA125, CA15.3, and HE4 were significantly higher in the TTF-1-positive group ' \
               u'than in the TTF-1-negative group (p<0.05).'
        expected_noun_phrases = set(['TTF-1-negative group', 'serum levels', 'TTF-1-positive group'])
        sentence = SentenceAnalysisSpacy(text, self.nlp)
        sentence.analyse()
        noun_phrases = set([i.text for i in sentence.noun_phrases])
        self.assertEqual(noun_phrases, expected_noun_phrases)
        self.assertTrue(_concept_exists(subject=u'serum levels',
                                             verb=u'be higher',
                                             object=u'TTF-1-positive group',
                                             concept_list=sentence.concepts))
        self.assertTrue(_concept_exists(subject=u'serum levels',
                                             verb=u'be higher than',
                                             object=u'TTF-1-negative group',
                                             concept_list=sentence.concepts))

    def test_hyphen_token(self):
        text = u'Here we report that the Polo-like kinase PLK1, an essential mitotic kinase regulator, ' \
               u'is an important downstream effector of c-ABL in regulating the growth of cervical cancer.'

        sentence = SentenceAnalysisSpacy(text, self.nlp)
        sentence.analyse()
        noun_phrases = set([i.text for i in sentence.noun_phrases])
        self.assertIn(u'Polo-like kinase PLK1', noun_phrases)
        self.assertIn(u'c-ABL', noun_phrases)

        self.assertTrue(_concept_exists(subject=u'Polo-like kinase PLK1',
                                             verb=u'report is',
                                             object=u'important downstream effector',
                                             concept_list=sentence.concepts)
                        )
        self.assertTrue(_concept_exists(subject=u'Polo-like kinase PLK1',
                                             verb=u'report is',
                                             object=u'c-ABL',
                                             concept_list=sentence.concepts)
                        )

        self.assertTrue(_concept_exists(subject=u'Polo-like kinase PLK1',
                                             verb=u'report regulating',
                                             object=u'cervical cancer',
                                             concept_list=sentence.concepts)
                        )
        self.assertTrue(_concept_exists(subject=u'Polo-like kinase PLK1',
                                             verb=u'report regulating',
                                             object=u'growth',
                                             concept_list=sentence.concepts)
                        )

    def test_Schistosoma(self):
        text = u'Studies have suggested that Schistosoma mansoni infection reduces the severity of asthma and prevent ' \
               u'' \
               u'' \
               u'' \
               u'' \
               u'' \
               u'atopy.'

        sentence = SentenceAnalysisSpacy(text, self.nlp)
        sentence.analyse()
        noun_phrases = set([i.text for i in sentence.noun_phrases])
        self.assertIn(u'Schistosoma mansoni infection', noun_phrases)

        self.assertTrue(_concept_exists(subject=u'Schistosoma mansoni infection',
                                             verb=u'suggest reduces',
                                             object=u'asthma',
                                             concept_list=sentence.concepts)
                        )

        self.assertTrue(_concept_exists(subject=u'Schistosoma mansoni infection',
                                             verb=u'suggest prevent',
                                             object=u'atopy',
                                             concept_list=sentence.concepts)
                        )

    def test_Fanconi(self):
        text = u'Fanconi anemia (FA) is a genetic disease characterized by bone marrow failure and increased cancer ' \
               u'risk.'
        expected_noun_phrases = set(['bone marrow failure', 'Fanconi anemia', 'cancer risk', 'genetic disease', ])
        sentence = SentenceAnalysisSpacy(text, self.nlp)
        self.assertIn(u'FA', sentence.abbreviations)
        self.assertEqual(u'Fanconi anemia', sentence.abbreviations[u'FA'])
        sentence.analyse()
        noun_phrases = set([i.text for i in sentence.noun_phrases])
        self.assertEqual(noun_phrases, expected_noun_phrases)

        self.assertTrue(_concept_exists(subject=u'Fanconi anemia',
                                             verb=u'be characterized by',
                                             object=u'cancer risk',
                                             concept_list=sentence.concepts)
                        )
        self.assertTrue(_concept_exists(subject=u'genetic disease',
                                             verb=u'be characterized by',
                                             object=u'cancer risk',
                                             concept_list=sentence.concepts)
                        )

        self.assertTrue(_concept_exists(subject=u'Fanconi anemia',
                                             verb=u'be characterized by',
                                             object=u'bone marrow failure',
                                             concept_list=sentence.concepts)
                        )
        self.assertTrue(_concept_exists(subject=u'genetic disease',
                                             verb=u'be characterized by',
                                             object=u'bone marrow failure',
                                             concept_list=sentence.concepts)
                        )

    def alpha_syn(self):
        text = u'Deubiquitinase Usp8 regulates α-synuclein clearance and modifies its toxicity in Lewy body disease.'
        expected_noun_phrases = set(['Usp8', 'Lewy body disease', 'alpha-synuclein clearance', 'toxicity'])
        sentence = SentenceAnalysisSpacy(text, self.nlp)
        sentence.analyse()
        noun_phrases = set([i.text for i in sentence.noun_phrases])
        self.assertEqual(noun_phrases, expected_noun_phrases)

        self.assertTrue(_concept_exists(subject=u'Usp8',
                                             verb=u'regulate',
                                             object=u'alpha-synuclein clearance',
                                             concept_list=sentence.concepts)
                        )
        self.assertTrue(_concept_exists(subject=u'Usp8',
                                             verb=u'regulate modifies',
                                             object=u'Lewy body disease',
                                             concept_list=sentence.concepts)
                        )
        self.assertTrue(_concept_exists(subject=u'Usp8',
                                             verb=u'regulate modifies',
                                             object=u'toxicity',
                                             concept_list=sentence.concepts)
                        )

    # TODO: "The results show that ERK2 phosphorylated p53 at Thr55"
    # Watson example: http://www.sciencedirect.com/science/article/pii/S0149291815013168  pmid: 11409876

    def test_multi_gene_and_disease(self):
        text = u' Molecular genetics and developmental studies have identified 21 genes in this region (ADRA1A, ' \
               u'ARHGEF10, CHRNA2, CHRNA6, CHRNB3, DKK4, DPYSL2, EGR3, FGF17, FGF20, ' \
               u'FGFR1, FZD3, LDL, NAT2, NEF3, NRG1, PCM1, PLAT, ' \
               u'PPP3CC, SFRP1 and VMAT1/SLC18A1) that are most likely to contribute to neuropsychiatric disorders ' \
               u'(schizophrenia, autism, bipolar disorder and depression), neurodegenerative disorders (Parkinson\'s' \
               u' and Alzheimer\'s disease) and cancer.'

        minimal_expected_noun_phrases = ['autism', 'ARHGEF10', 'NEF3', 'genes', 'depression', 'CHRNA6', 'PCM1', 'DKK4',
                                         'PPP3CC', 'EGR3', 'VMAT1/SLC18A1', 'FGF20', 'bipolar disorder', 'CHRNA2',
                                         'FZD3', 'Molecular genetics', 'CHRNB3', 'NAT2', 'DPYSL2', 'NRG1', 'cancer',
                                         'FGF17', 'PLAT', 'FGFR1', 'SFRP1', 'neuropsychiatric disorders', 'region',
                                         'LDL', 'schizophrenia', 'depression', 'Parkinson\'s', 'Alzheimer\'s disease'
                                         ]
        sentence = SentenceAnalysisSpacy(text, self.nlp)
        sentence.analyse()
        noun_phrases = set([i.text for i in sentence.noun_phrases])
        self.assertTrue(_concept_exists(subject=u' Molecular genetics',
                                             verb=u'identify',
                                             object=u'FZD3',
                                             concept_list=sentence.concepts)
                        )
        for i in minimal_expected_noun_phrases:
            self.assertIn(i, noun_phrases)

    def testManyPunctations(self):
        text = u'In ' \
               u'addition, the antagonistic action of propranolol (1 X 10(-7) M) in a Ca++-containing or ' \
               u'Sr++-containing medium was determined. '

        sentence = SentenceAnalysisSpacy(text, self.nlp)
        sentence.analyse()

    def test_custom_tokenizer(self):
        text = u'the antagonistic action of propranolol (1 X 10(-7) M) in a Ca++-containing or. Cell growth and ' \
               u'quabain-sensitive 86Rg+ uptake and (Na++K+)-ATPase activity in 3T3 and SV40 transformed 3T3 ' \
               u'fibroblasts. The uptake of ouabain-sensitive 86Rb+ uptake measured at 5 min and the uptake measured ' \
               u'at 60 min was 4.5- and 2.7-fold greater respectively for SV40 transformed 3T3 cells compared to 3T3 ' \
               u'cells during the late log phase of growth. This uptake, however, varied markedly with cell growth. ' \
               u'Ouabain-sensitive 86Rb+ uptake was found to be a sensitive indicator of protein synthesis as ' \
               u'measured by total protein content. Cessation of cell growth as measured by total protein content was ' \
               u'' \
               u'' \
               u'' \
               u'associated with a decline in ouabain-sensitive 86Rb+ uptake in both cell types. This increase ' \
               u'ouabain-sensitive cation transport was reflected in increased levels of (Na++K)-ATPase activity for ' \
               u'SV40 3T3 cells, which showed a 2.5-fold increase V but the same Km as 3T3 cells. These results are ' \
               u'compared with the results of related work. Possible mechanisms for these effects are discussed and ' \
               u'how changes in cation transport might be related to alterations in cell growth. This is a test, ' \
               u'for a complex entity name: th:is.{e}nt/ity-is,ver-y/co_m[p]lex(to)par;se . '

        # u'Derivatives of 1,2,3,11a-tetrahydro-5H-pyrrolo[2,1-c][1,4]benzodiazepine-5,11(10H)-dione as ' \
        # u'anxiolytic agents. A study of the pharmacological properties of pyrrolo[2,1-c][1,4]benzodiazepine ' \
        # u'derivatives led to the choice of (+)-1,2,3,11a-tetrahydro-10-methyl-5H-pyrrolol[2,1-c][1,' \
        # u'4]benzodiazepine-5,11)10H)-dione as a candidate for anxiolytic evaluation in a limited clinical ' \
        # u'trial in man. Metabolism studies in laboratory animals have pointed to rapid hydroxylation, ' \
        # u'possibly in the 3 and 11a positions. A series of compouds containing methyl groups in one or more of ' \
        # u'these positions has been prepared in an effort to block metabolism and thereby obtain more active or ' \
        # u'longer acting compounds. All of these derivatives were less active than the parent compound.'

        # u'Inversion of optical configuration of alpha-methylfluorene-2-acetic acid (cicloprofen) in rats and
        # monkeys. A simple and sensitive radiometric method to determine the individual enantiomers of cicloprofen
        # has been developed. 14C-Cicloprofen was converted to its L-leucine diastereoisomers, which were separated
        # by thin-layer chromatography and quantified by measuring the radioactivity in the area corresponding to
        # each individual diastereoisomer. This technique has also been used to measure the enantiomers of unlabeled
        # cicloprofen by condensing with 14C-labeled L-leucine. By using the radiometric method,
        # a unique biotransformation process, the inversion of the (-)-enantiomer of alpha-methylfluorene-2-acetic
        # acid to its (+)-enantiomer, has been demonstrated in the rat and monkey. The rate of (-)- to (+)-inversion
        # was found to be faster in the rat than in the monkey. After single or repeated oral adminstration of the
        # racemic modification or the (-)-enantiomer of cicloprofen to both species, the ratio of (+)- to (
        # -)-enantiomers of cicloprofen in plasma, urine, or bile increased with time. At 5, 22, and 48 hr after oral
        #  administration of a single 50-mg/kg dose of the (-)-enantiomer, 14C-cicloprofen in rat plasma contained
        # 20, 50, and 79%, respectively, of the (+)-enantiomer. After receiving the same dose of (-)-enantiomer,
        # monkey plasma contained 16.5% and 32% of (+)-enantiomer at 8 and 24 hr, respectively. After oral
        # administration of a single 50-mg/kg dose of the (+)-enantiomer of 14C-cicloprofen to rats and monkeys,
        # the percentage of (-)-enantiomer in plasma varied from 2 to 15%. Since the administered (+)-enantiomer
        # contained 4% of (-)-enantiomer and the (+)-enantiomer was excreted at a faster rate than its (-)-antipode
        # by rats or monkeys, it is not known whether an occasional small percentage increase of (-)-enantiomer in
        # plasma resulted from the (+)-to-(-) inversion, or from faster elimination of the (+)-enantiomer.
        # Nevertheless, if (+)-to-(-) inversion does occur in these two species, the rate is much slower than for the
        #  (-)-to-(+) inversion.'


        # u' Properties of common wheat ferredoxin, and a comparison with ferredoxins from related species of
        # triticum and aegilops. Wheat ferredoxin was purified from the leaves of common wheat (Triticum aestivum).
        # The absorption spectrum showed maxima at 465, 425, 332, and 278 nm. The absorbance ratio, A425 nm/A278 nm
        # was 0.49, and the millimolar extinction coefficient at 425 nm was 10.8 mM-1. cm-1. The amino acid
        # composition was determined to be Lys5, His2, Arg1, Asp11, Thr5, Ser7, Glu18, Pro5, Gly6, Ala7, Cys5, Val7,
        # Met1, Ile4, Leu7, Tyr4, Phe1, and Trp1. The total number of amino acid residues was 97. The molecular
        # weight was calculated from the amino acid composition to be 10,829, including iron and sulfur atoms. This
        # value was confirmed by other methods, which were based on the contents of non-heme iron and of terminal
        # amino acid. The N-terminal amino acid was alanine, and the C-terminal amino acid sequence was
        # -Glu-Leu-Thr-AlaCOOH. Comparative studies were performed between T. aestivum ferredoxin and ferredoxins
        # isolated from closely related species; these were T. aegilopoides, T. durum, Ae. squarrosa, and Ae. ovata.
        # No significant differences in the properties of these ferredoxins were detected. It was also shown that
        # these ferredoxins are immunologically homologous. It is, therefore, likely that one molecular species of
        # ferredoxin is distributed through two genera of Triticum and Aegilops.'
        sentence = SentenceAnalysisSpacy(text, self.nlp)
        sentence.analyse(merge_with_syntax=False)
        tokens = [i.text for i in sentence.doc]
        self.assertIn(u'10(-7)', tokens)
        self.assertIn(u'(Na++K+)-ATPase', tokens)
        self.assertIn(u'2.7-fold', tokens)
        self.assertIn(u'4.5-', tokens)
        self.assertIn(u'86Rb+', tokens)
        self.assertIn(u'Ca++-containing', tokens)
        self.assertIn(u'(Na++K)-ATPase', tokens)
        self.assertIn(u'Ouabain-sensitive', tokens)
        self.assertIn(u'th:is.{e}nt/ity-is,ver-y/co_m[p]lex(to)par;se', tokens)
        self.assertNotIn(u'cells,', tokens)
        self.assertNotIn(u'(1', tokens)
        self.assertNotIn(u'fibroblasts.', tokens)

    def test_to_text(self):
        text = u'Molecular genetics and developmental studies have identified 21 genes in this region (ADRA1A, ' \
               u'ARHGEF10, CHRNA2, CHRNA6, CHRNB3, DKK4, DPYSL2, EGR3, FGF17, FGF20, ' \
               u'FGFR1, FZD3, LDL, NAT2, NEF3, NRG1, PCM1, PLAT, ' \
               u'PPP3CC, SFRP1 and VMAT1/SLC18A1) that are most likely to contribute to neuropsychiatric disorders ' \
               u'(schizophrenia, autism, bipolar disorder and depression), neurodegenerative disorders (Parkinson\'s' \
               u' and Alzheimer\'s disease) and cancer.'

        sentence = SentenceAnalysisSpacy(text, self.nlp)
        sentence.analyse(verbose=True, )
        print sentence.to_text()
        print sentence.to_pos_tagged_text()


def line_iterator(f):

    for line in file(f):
        yield unicode(line, encoding='utf-8')


class SpacyDocumentNLPTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nlp = init_spacy_english_language()
        cls.tagger = BioEntityTagger(partial_match=False)

    def test_analyse_all_abstracts(self):
        file_path = 'resources/test_abstract_nlp.txt'
        filedir = os.path.dirname(__file__)
        abstracts_analyzer = DocumentAnalysisSpacy(nlp=self.nlp, tagger=self.tagger)
        for abstract in file(os.path.join(filedir, file_path)):
            digested_abstract = abstracts_analyzer.digest(unicode(abstract, encoding='UTF-8'))
            # pprint(digested_abstract)
            # print parsed_abstract.noun_phrase_counter
            # print 'Top Noun Phrases:', len(digested_abstract['top_chunks']), digested_abstract['top_chunks']
            # print 'Noun Phrases:', len(digested_abstract['chunks'])
            # print 'Concepts:', len(digested_abstract['concepts'])
            # print 'Tagged:'
            print digested_abstract['tagged_text']
            # print '='*60
            self.assertLess(len(digested_abstract['top_chunks']), len(digested_abstract['chunks']))

    def test_custom_tokenizer(self):
        text = u'This is a test, for a complex entity name: th:is.{e}nt/ity-is,ver-y/co_m[p]lex(to)par;se ' \
               u'this_is-simpler. but this is an other sentence\nand this is after a new line'

        doc_analysis = DocumentAnalysisSpacy(self.nlp,
                                             tagger=self.tagger)
        doc, digest = doc_analysis.process(text)
        sentences = list(doc.sents)
        self.assertEqual(len(sentences), 2)
        tokens = [i.text for i in sentences[0]]
        self.assertIn(u'th:is.{e}nt/ity-is,ver-y/co_m[p]lex(to)par;se', tokens)
        self.assertIn(u'this_is-simpler', tokens)
        self.assertNotIn(u'sentence\nand', tokens)
        self.assertNotIn(u'name:', tokens)
        self.assertNotIn(u'this_is-simpler.', tokens)
        self.assertNotIn(u'sentence', tokens)
        self.assertNotIn(u'line', tokens)

    def test_tags_in_concepts(self):
        abstracts_analyzer = DocumentAnalysisSpacy(nlp=self.nlp,
                                                   tagger=self.tagger)
        digested_abstract = abstracts_analyzer.digest(chromosome8p_text)
        concepts = [concept for concept in digested_abstract['concepts'] if 'PPP3CC' in concept['object']]
        self.assertNotEquals(concepts,[])
        for concept in concepts:
            tags_types = concept['object_tags'].keys()
            self.assertIn('GENE',tags_types)
            for tag in concept['object_tags']['GENE']:

                matched_text = tag['match'].lower()
                positions_text = concept['sentence_text'][tag['start']:tag['end']].lower()
                self.assertEqual(matched_text, positions_text)

    def test_obama(self):
        '''compare with https://github.com/GoogleCloudPlatform/python-docs-samples/tree/master/language
        /syntax_triples'''

        text = u'In 2004, Obama received national attention during his campaign to represent Illinois in the United ' \
               u'States Senate with his victory in the March Democratic Party primary, his keynote address at the ' \
               u'Democratic National Convention in July, and his election to the Senate in November. He began his ' \
               u'presidential campaign in 2007 and, after a close primary campaign against Hillary Clinton in 2008, ' \
               u'he won sufficient delegates in the Democratic Party primaries to receive the presidential ' \
               u'nomination. He then defeated Republican nominee John McCain in the general election, ' \
               u'and was inaugurated as president on January 20, 2009. Nine months after his inauguration, ' \
               u'Obama was named the 2009 Nobel Peace Prize laureate.'
        abstracts_analyzer = DocumentAnalysisSpacy(nlp=self.nlp,
                                                   tagger=self.tagger)
        digested_abstract = abstracts_analyzer.digest(text)
        print 'Top Noun Phrases:', len(digested_abstract['top_chunks']), digested_abstract['top_chunks']
        print 'Noun Phrases:', len(digested_abstract['chunks'])
        print 'Concepts:', len(digested_abstract['concepts'])

    def test_to_text(self):
        text = chromosome8p_text


        abstracts_analyzer = DocumentAnalysisSpacy(nlp=self.nlp,
                                                   tagger=self.tagger)
        digested_abstract = abstracts_analyzer.digest(text)
        clean_abstract = abstracts_analyzer.to_text()
        self.assertNotIn(',', clean_abstract )
        self.assertIn('molecular_genetics', clean_abstract)
        pos_tagged_abstract = abstracts_analyzer.to_pos_tagged_text()
        self.assertIn('molecular_genetics|NOUN', pos_tagged_abstract)
        ent_and_pos_tagged_abstract =  abstracts_analyzer.to_entity_tagged_text()
        self.assertIn('ensg00000120907|GENE|ADRA1D', ent_and_pos_tagged_abstract)


    def testEbmeddingTrainingSave(self):
        file_path = 'resources/pubmed_result.abstract.txt'
        filedir = os.path.dirname(__file__)
        clean_file = codecs.open('embedding_training_clean.txt','w',encoding="utf-8")
        clean_file_lower =codecs. open('embedding_training_lower.txt','w',encoding="utf-8")
        pos_file = codecs.open('embedding_training_pos.txt','w',encoding="utf-8")
        ent_and_pos_file = codecs.open('embedding_training_end_and_pos.txt','w', encoding="utf-8")
        abstracts_analyzer = DocumentAnalysisSpacy(nlp=self.nlp,
                                                   tagger=self.tagger)
        # for i, doc in enumerate(abstrac  n_threads=8)):

        for i,abstract in enumerate(file(os.path.join(filedir, file_path))):
            if i%1000 == 0:
                print i
            # try:
            if 1:
                digested_abstract = abstracts_analyzer.digest(unicode(abstract, encoding='utf-8'))
                text = abstracts_analyzer.to_text(lower = False)
                json.dumps(text)
                clean_file.write(text+'\n')
                text = abstracts_analyzer.to_text(lower = True)
                json.dumps(text)
                clean_file_lower.write(text+'\n')
                text = abstracts_analyzer.to_pos_tagged_text(lower=True)
                json.dumps(text)
                pos_file.write(text+'\n')
                text = abstracts_analyzer.to_entity_tagged_text(lower=True, use_pos=False)
                json.dumps(text)
                ent_and_pos_file.write(text+'\n')
            # except Exception as e:
            #     print 'error converting to w2v input',e




if __name__ == '__main__':
    unittest.main()
