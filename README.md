# Open Targets Library - NLP Pipeline

## NLP Analysis of MedLine/PubMed Running in Apache Beam

This pipeline is designed to run with Apache Beam using the dataflow runner.
It has not been tested with other Beam backends, but it should work there as well pending minimal modifications.
Please see the [Apache Beam SDK](https://beam.apache.org/documentation/sdks/python/) for more info.

## Steps to reproduce a full run
Use python2 with pip and virtualenv

* Generate a mirror of MEDLINE FTP to a Google Storage Bucket (any other storage provider supported by Python Beam SDK should work). E.g. using [rclone](https://rclone.org/)
   
   - Download [pre-built rclone binaries](https://rclone.org/install/#linux-installation-from-precompiled-binary) rather than platform packaged ones as they tend to be more up-to-date 
   - configure rclone with MEDLINE FTP [ftp.ncbi.nlm.nih.gov](ftp://ftp.ncbi.nlm.nih.gov) and your target gcp project
     (my-gcp-project-buckets)  `rclone config`. Medline must have username `anonymous` and password `anonymous`.
   - Generate a full mirror:
     `rclone sync -v medline-ftp:pubmed/baseline my-gcp-project-buckets:my-medline-bucket/baseline`
   - Update new files:
     `rclone sync -v medline-ftp:pubmed/updatefiles my-gcp-project-buckets:my-medline-bucket/updatefiles`
  - Note: you can use `--dry-run` argument to test 
* install tooling
    ```sh
    sudo apt-get install python-dev virtualenv build-essential git libxml2-dev libxslt-dev zlib1g-dev tmux
    ``` 
* Download the pipeline 
    ```sh
    git clone https://github.com/opentargets/library-beam
    cd library-beam
    ```
* Create a virtual environment to manage dependencies in
    ```sh
    virtualenv venv --python=python2
    source venv/bin/activate
    ```
* Install the pipeline into the virtual environment   
    ```sh 
    python setup.py install
    #note this needs between 3.75GB and 7.5GB RAM
    pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-2.2.0/en_core_web_lg-2.2.0.tar.gz
    ```
* Run pipeline
  ```sH
  python -m main \
    --project open-targets-library \
    --job_name medline201911 \
    --runner DataflowRunner \
    --temp_location gs://medline_2019_11/temp \
    --setup_file ./setup.py \
    --worker_machine_type n1-highmem-32 \
    --input_baseline gs://medline_2019_11/baseline/pubmed19n*.xml.gz \
    --input_updates gs://medline_2019_11/updatefiles/pubmed19n*.xml.gz \
    --output_enriched gs://medline_2019_11/analyzed/pubmed19 \
    --output_splitted gs://medline_2019_11/splitted/pubmed19 \
    --max_num_workers 32 \
    --region europe-west1 \
    --zone europe-west1-d
  ```
  
  This can be monitored via [Google Dataflow](https://console.cloud.google.com/dataflow). Note that "wall time" displayed is not the [usual definition](https://en.wikipedia.org/wiki/Elapsed_real_time) but is per thread and worker. 
  
  In total it takes approximately 4h.
  
  ![image](https://user-images.githubusercontent.com/148221/35000427-4e11b818-fadc-11e7-9c2f-08a68eaed37e.png)
    
  ![image](https://user-images.githubusercontent.com/148221/35000458-6108bb24-fadc-11e7-8a84-452f7b3816f6.png)
  
## Steps to load the JSONs dump into ElasticSearch
  
  The directory gcp contains the infrastructure scripts to generate the Elasticsearch cluster.
    
  * Create a virtual environment to manage dependencies in
    ```sh
    virtualenv venv_elasticsearch --python=python2
    source venv_elasticsearch/bin/activate
    pip install -r venv_elasticsearch.txt
    ```
  * Run job load JSONs in Elasticsearch
  ```sh
  python load2es.py publication --es http://myesnode1:9200  --es http://myesnode2:9200
  python load2es.py bioentity --es http://myesnode1:9200  --es http://myesnode2:9200
  python load2es.py taggedtext --es http://myesnode1:9200  --es http://myesnode2:9200
  python load2es.py concept --es http://myesnode1:9200  --es http://myesnode2:9200
  ```
  
  Note: Elasticsearch must have the International Components for Unicode support plugin installed.i.e. `/usr/share/elasticsearch/bin/elasticsearch-plugin -s install analysis-icu`
  
  WARNING: the loading scripts takes a lot of time currently, particurlarly the concept one (24h+). It is good to use `screen` or `tmux` or similar, so it will keep going after disconect and can be recovered.  E.g. 
  ```sh
  tmux
  tmux new-session "time -p python load2es.py publication --es http://be-es-debian-3n-node01:39200 --es http://be-es-debian-3n-node02:39200 --es http://be-es-debian-3n-node03:39200 "
  tmux new-session "time -p python load2es.py bioentity --es http://be-es-debian-3n-node01:39200 --es http://be-es-debian-3n-node02:39200 --es http://be-es-debian-3n-node03:39200 "
  tmux new-session "time -p python load2es.py taggedtext --es http://be-es-debian-3n-node01:39200 --es http://be-es-debian-3n-node02:39200 --es http://be-es-debian-3n-node03:39200 "
  tmux new-session "time -p python load2es.py concept --es http://be-es-debian-3n-node01:39200 --es http://be-es-debian-3n-node02:39200 --es http://be-es-debian-3n-node03:39200 "
  ```
* OPTIONAL: If needed create appropriate aliases in elasticsearch
  ```sh
  curl -XPOST 'http://myesnode1:9200/_aliases' -H 'Content-Type: application/json' -d '
    {
        "actions": [
            {"add": {"index": "pubmed-18", "alias": "!publication-data"}}
        ]
    } '
  ```
* OPTIONAL: Increase elasticsearch capacity for the adjancency matrix aggregation (used by LINK tool)
  ```sh
  curl -XPUT 'http://myesnode1:9200/pubmed-18-concept/_settings' -H 'Content-Type: application/json' -d'
     {
        "index" : {
            "max_adjacency_matrix_filters" : 500
            }
     }'
  ```

## Google Cloud Platform

When controlling this process from a Google cloud machine, make sure it has sufficient scopes enabled.
