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
* run NLP analytical pipeline
  ```
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
* OPTIONAL run job to split Enriched JSONs in smaller pieces
  ```
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

* run job load JSONs in Elasticsearch (TODO)
