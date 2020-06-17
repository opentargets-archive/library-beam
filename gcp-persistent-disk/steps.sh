# DNS name 
# Eg.  http://es-201206-133204.es-201206-133204.il4.europe-west1.lb.open-targets-library.internal:9200
# HOST=es-200617-101804
# curl -X GET http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200

export HOST=es-200617-101804

# the number of shard is related with CPU and VMS. Eg. 3VMsx8cpu=24
curl -XPUT "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/_template/default" -H 'Content-Type: application/json' \
-d'{"template":"*","settings":{"number_of_shards":24}}' 

mkdir loader
cd loader

# Settings for the different indices
curl  -X GET https://raw.githubusercontent.com/opentargets/library-beam/master/es-mapping-index/concept.json > concept.json
curl  -X GET https://raw.githubusercontent.com/opentargets/library-beam/master/es-mapping-index/publication.json > publication.json
curl  -X GET https://raw.githubusercontent.com/opentargets/library-beam/master/es-mapping-index/settings.json > settings.json

curl -XPUT "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/pubmed-20-taggedtext?pretty" -H 'Content-Type: application/json' -d@"settings.json"
curl -XPUT "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/pubmed-20-bioentity?pretty" -H 'Content-Type: application/json' -d@"settings.json"
curl -XPUT "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/pubmed-20?pretty" -H 'Content-Type: application/json' -d@"publication.json"
curl -XPUT "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/pubmed-20-concept?pretty" -H 'Content-Type: application/json' -d@"concept.json"

#Adam suggested to add this. Change the HOST
curl -XPUT 'http://$s-200617-101804.es-200617-101804.il4.europe-west1.lb.open-targets-library.internal:9200/pubmed-20-concept/_settings' -H 'Content-Type: application/json' -d'{"index" : {"max_adjacency_matrix_filters" : 500}}'

curl -X GET http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/_cat/indices

# list of files stored in Google Storage
gsutil ls gs://medline_2020_06/splitted/pubmed\*_bioentities\*.json.gz > bioentities_files.txt
gsutil ls gs://medline_2020_06/splitted/pubmed\*_taggedtext\*.json.gz > taggedtext_files.txt
gsutil ls gs://medline_2020_06/splitted/pubmed\*_small\*.json.gz > publication_files.txt
gsutil ls gs://medline_2020_06/splitted/pubmed\*_concepts\*.json.gz > concepts_files.txt


# Taggedtext index // BEGIN FOR EVERY INDEX

#split the file for running 10 processes
wc -l taggedtext_files.txt
split -l 1180 taggedtext_files.txt taggedtext_split_


#_index_name_tmux.sh
# HOST=dns_name_hardcode (todo: change YOUR_PATH and HOST.)
#!/bin/bash
FILES=$YOUR_PATH/loader/taggedtext_split_*
tmux start-server
for f in $FILES
do
   windowName="tagg-${f: -2}"
   # take action on each file. $f store current file name
   #cat $f
   echo $windowName
   tmux new-session -d -s ${windowName}
   tmux send-keys -t ${windowName} "source ~/library-beam/venv_elastic/bin/activate" Enter
   tmux send-keys -t ${windowName} "export HOST=es-191209-112649" Enter
   tmux send-keys -t ${windowName} "export input=${f}; ./es_tag.sh" Enter
done

# es_tag.sh
time for file in $(cat ${input}); do gsutil cat $file | gunzip | elasticsearch_loader --es-host "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.int
ernal:9200" --with-retry --bulk-size 10000 --index pubmed-19-taggedtext --type taggedtext --id-field pub_id json --json-lines - ; done

#Kill the list of tmux opened
#!/bin/bash
FILES=$YOUR_PATH/loader/taggedtext_split_*
tmux start-server
for f in $FILES
do
   windowName="tagg-${f: -2}"
   echo $windowName
   tmux kill-session -t ${windowName}
done

# Changed the refresh interval
export HOST=dns_name_param
curl -XPUT 'http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/pubmed-19-taggedtex/_settings' -d '{"index":{"refresh_interval":"1s”}}'


#### IMPORTANT 
The index es_concept.sh is slightly different due the id-field value

time for file in $(cat ${input}); do gsutil cat $file | gunzip | elasticsearch_loader --es-host "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.int
ernal:9200" --with-retry --bulk-size 10000 --index pubmed-19-concept --type concept json --json-lines - ; done

There are some examples under "tmux_example"
