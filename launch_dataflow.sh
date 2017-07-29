#!/usr/bin/env bash
python -m main \
  --project open-targets \
  --job_name open-targets-medline-process-full\
  --runner DataflowRunner \
  --temp_location gs://opentargets-library-tmp/temp \
  --setup_file ./setup.py \
  --worker_machine_type n1-highmem-32 \
  --input_baseline gs://pubmed-medline/baseline/medline17n*.xml.gz \
  --input_updates gs://pubmed-medline/updatefiles/medline17n*.xml.gz \
  --output gs://medline-json/parsed/medline-base17 \
  --output_enriched gs://medline-json/analyzed/medline-base17 \
  --max_num_workers 12 \
  --zone europe-west1-d

#  --requirements_file requirements.txt \
#  --output_splitted gs://medline-json/splitted/medline-base17 \


