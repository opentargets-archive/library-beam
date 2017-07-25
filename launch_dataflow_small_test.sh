#!/usr/bin/env bash
python -m main \
  --project open-targets \
  --job_name open-targets-medline-process-test \
  --runner DataflowRunner \
  --temp_location gs://opentargets-library-tmp/temp \
  --setup_file ./setup.py \
  --worker_machine_type n1-highmem-8 \
  --input_baseline gs://pubmed-medline/baseline/medline17n08*.xml.gz \
  --output gs://medline-json/test/parsed/medline-base17 \
  --output_enriched gs://medline-json/test/analyzed/medline-base17 \
  --zone europe-west1-d

#  --requirements_file requirements.txt \


