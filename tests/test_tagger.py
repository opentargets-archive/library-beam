import unittest, json

from modules.BioentityTagger import BioEntityTagger


class TaggerTestCase(unittest.TestCase):

    def setUp(self):
        self.tagger = BioEntityTagger()

    def testTaggerNLP(self):

        for i, text in enumerate(file('resources/test_abstract_nlp.txt')):
            print i
            for tag in self.tagger.tag(text.lower()):
               print tag, text[tag['start']:tag['end']]

    def testTaggerLexebi(self):
        for i, text in enumerate(file('resources/test_abstract_lexebi.txt')):

            print i
            # for tag in tagger.tag(text.lower()):
            #     print tag, text[tag['start']:tag['end']]
            old_tags = set()
            lexebi_tags = set()
            tags = self.tagger.tag(text.lower())
            for tag in tags:
                matched_text = text[tag['start']:tag['end']]
                print tag, matched_text
                if tag['reference_db'] == 'LEXEBI':
                    lexebi_tags.add(matched_text)
                else:
                    old_tags.add(matched_text)
            new_tags = lexebi_tags.difference(old_tags)
            print 'New tags identified : {}'.format(new_tags)


if __name__ == "__main__":
     unittest.main()