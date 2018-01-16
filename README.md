# library-beam
MedLine NLP Analysis Running in Apache Beam
--------------------------------------------

* generate a mirror of MEDLINE FTP to a Google Storage Bucket (any other storage provider supported by Python Beam SDK
should work). E.g. using [rclone](https://rclone.org/)
  - configure rclone with MEDLINE FTP [ftp.ncbi.nlm.nih.gov](ftp://ftp.ncbi.nlm.nih.gov) and your target gcp project (my-gcp-project-buckets)
    `rclone config`
  - Generate a full mirror:
    `rclone sync medline-ftp:pubmed my-gcp-project-buckets:my-medline-bucket`
  - Update new files:
    `rclone sync medline-ftp:pubmed/updatefiles my-gcp-project-buckets:my-medline-bucket/updatefiles`


Use python 2

Starting from scratch:
* install locally
    ```sh
    git clone https://github.com/opentargets/library-beam
    cd library-beam
    (sudo) pip install virtualenv
    virtualenv venv
    source venv/bin/activate
    pip install https://github.com/explosion/spacy-models/releases/download/en_depent_web_md-1.2.1/en_depent_web_md-1.2.1.tar.gz
    python setup.py install
    ```

* run NLP analytical pipeline
  ```sh
  python -m main \
  --project your-project \
  --job_name medline-nlp\
  --runner DataflowRunner \
  --temp_location gs://my-tmp-bucket/temp \
  --setup_file ./setup.py \
  --worker_machine_type n1-highmem-32 \
  --input_baseline gs://my-medline-bucket/baseline/medline17n*.xml.gz \
  --input_updates gs://my-medline-bucket/updatefiles/medline17n*.xml.gz \
  --output_enriched gs://my-medline-bucket-output/analyzed/medline-base17 \
  --max_num_workers 32 \
  --zone europe-west1-d
  ```

  ![image](https://user-images.githubusercontent.com/148221/35000427-4e11b818-fadc-11e7-9c2f-08a68eaed37e.png)

* run job to split Enriched JSONs in smaller pieces
  ```sh
  python -m main \
  --project your-project \
  --job_name medline-nlp-split\
  --runner DataflowRunner \
  --temp_location gs://my-tmp-bucket/temp \
  --setup_file ./setup.py \
  --worker_machine_type n1-highmem-16 \
  --input_enriched gs://my-medline-bucket-output/analyzed/medline-base17*_enriched.json.gz \
  --output_enriched gs://my-medline-bucket-output/analyzed/medline-base17 \
  --max_num_workers 16 \
  --zone europe-west1-d
  ```

  ![image](https://user-images.githubusercontent.com/148221/35000458-6108bb24-fadc-11e7-8a84-452f7b3816f6.png)

* run job load JSONs in Elasticsearch
  ```sh
  python load2es.py publication --es http://myesnode1:9200  --es http://myesnode2:9200
  python load2es.py bioentity --es http://myesnode1:9200  --es http://myesnode2:9200
  python load2es.py bioentity --es http://myesnode1:9200  --es http://myesnode2:9200
  python load2es.py concept --es http://myesnode1:9200  --es http://myesnode2:9200
  ```

  WARNING: the loading scripts takes a lot of time currently, particurlarly the concept one (16h in our system). It
  might be a good idea to use tmux to load the data, so it will keep going while you are not there looking at it.
  E.g. after installing tmux
  ```sh
  tmux new-session "python load2es.py publication --es http://myesnode1:9200  --es http://myesnode2:9200"
  tmux new-session "python load2es.py bioentity --es http://myesnode1:9200  --es http://myesnode2:9200"
  tmux new-session "python load2es.py bioentity --es http://myesnode1:9200  --es http://myesnode2:9200"
  tmux new-session "python load2es.py concept --es http://myesnode1:9200  --es http://myesnode2:9200"
  ```

* OPTIONAL: if needed create appropriate aliases in elasticsearch

  ```sh
  curl -XPOST 'http://myesnode1:9200/_aliases' -H 'Content-Type: application/json' -d '
    {
        "actions": [
            {"add": {"index": "pubmed-18", "alias": "!publication-data"}}
        ]
    } '
  ```

* OPTIONAL: encrease elasticsearch capacity for the adjancency matrix aggregation (used by LINK tool)

  ```sh
  curl -XPUT 'http://myesnode1:9200/pubmed-18-concept/_settings' -H 'Content-Type: application/json' -d'
     {
        "index" : {
            "max_adjacency_matrix_filters" : 500
            }
     }'
  ```

