#!/usr/bin/env bash
python -m main \
  --project open-targets \
  --job_name open-targets-medline-process-split \
  --runner DataflowRunner \
  --temp_location gs://opentargets-library-tmp/temp \
  --setup_file ./setup.py \
  --worker_machine_type custom-16-106496 \
  --input_enriched gs://medline-json/analyzed/pubmed18*_enriched.json \
  --output_splitted gs://medline-json/splitted/pubmed18 \
  --zone europe-west1-d

#  --requirements_file requirements.txt \


