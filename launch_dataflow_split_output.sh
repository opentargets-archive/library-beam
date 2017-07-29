#!/usr/bin/env bash
python -m main \
  --project open-targets \
  --job_name open-targets-medline-process-split\
  --runner DataflowRunner \
  --temp_location gs://opentargets-library-tmp/temp \
  --setup_file ./setup.py \
  --worker_machine_type n1-highmem-16 \
  --input_enriched gs://medline-json/analyzed/beam-temp-medline-base17-fb6b74da72de11e7aeed42010a840003/*_enriched.json.gz \
  --output_splitted gs://medline-json/splitted/medline-base17 \
  --max_num_workers 10 \
  --zone europe-west1-d

#  --requirements_file requirements.txt \


