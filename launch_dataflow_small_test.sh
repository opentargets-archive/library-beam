#!/usr/bin/env bash
python -m main \
  --project open-targets \
  --job_name open-targets-medline-process-test-nolabel\
  --runner DataflowRunner \
  --temp_location gs://opentargets-library-tmp/temp-new \
  --setup_file ./setup.py \
  --worker_machine_type n1-highmem-4 \
  --input_baseline gs://pubmed-medline/baseline/medline17n082*.xml.gz \
  --output gs://medline-json/test/parsed/medline-base17 \
  --output_enriched gs://medline-json/test/analyzed/medline-base17 \
  --max_num_workers 3 \
  --zone europe-west1-d

#  --requirements_file requirements.txt \


