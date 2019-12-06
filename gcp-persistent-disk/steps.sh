# LOAD BALANCE address
# Eg.  http://es-191206-133204.es-191206-133204.il4.europe-west1.lb.open-targets-library.internal:9200
# HOST=es-191206-133204
# curl -X GET http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200

export HOST=es-191206-133204

curl -XPUT "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/_template/default" -H 'Content-Type: application/json' \
-d'{"template":"*","settings":{"number_of_shards":40}}' 

mkdir loader
cd loader

# Settings for the different indices
curl  -X GET https://raw.githubusercontent.com/opentargets/library-beam/master/es-mapping-index/concept.json > concept.json
curl  -X GET https://raw.githubusercontent.com/opentargets/library-beam/master/es-mapping-index/publication.json > publication.json
curl  -X GET https://raw.githubusercontent.com/opentargets/library-beam/master/es-mapping-index/settings.json > settings.json

curl -XPUT "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/pubmed-19-taggedtext?pretty" -H 'Content-Type: application/json' -d@"settings.json"
curl -XPUT "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/pubmed-19-bioentity?pretty" -H 'Content-Type: application/json' -d@"settings.json"
curl -XPUT "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/pubmed-19?pretty" -H 'Content-Type: application/json' -d@"publication.json"
curl -XPUT "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/pubmed-19-concept?pretty" -H 'Content-Type: application/json' -d@"concept.json"

curl -X GET http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/_cat/indices

# list of files stored in Google Storage
gsutil ls gs://medline_2019_11/splitted/pubmed\*_bioentities\*.json.gz > bioentities_files.txt
gsutil ls gs://medline_2019_11/splitted/pubmed\*_taggedtext\*.json.gz > taggedtext_files.txt
gsutil ls gs://medline_2019_11/splitted/pubmed\*_small\*.json.gz > publication_files.txt
gsutil ls gs://medline_2019_11/splitted/pubmed\*_concepts\*.json.gz > concepts_files.txt

#split the file for running 10 processes
wc -l taggedtext_files.txt
split -l 1180 taggedtext_files.txt taggedtext_split_

time 
for file in $(cat test.txt); 
 do 
 gsutil cat $file | gunzip | elasticsearch_loader --es-host "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200" --with-retry --bulk-size 10000 --index pubmed-19-taggedtext --type taggedtext --id-field pub_id json --json-lines - ; 
done


# to complete....
wc -l bioentities_files.txt
wc -l publication_files.txt
wc -l concepts_files.txt

