
from modules.BioentityTagger import BioEntityTagger


tagger = BioEntityTagger()

for i, text in enumerate(file('resources/test_abstract_nlp.txt')):
    print i
    for tag in tagger.tag(text.lower()):
        print tag, text[tag['start']:tag['end']]
