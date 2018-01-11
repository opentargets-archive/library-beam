#!/usr/bin/env bash
python -m main \
  --project open-targets \
  --job_name open-targets-medline-process-full\
  --runner DataflowRunner \
  --temp_location gs://opentargets-library-tmp/temp \
  --setup_file ./setup.py \
  --worker_machine_type n1-highmem-16 \
  --input_baseline gs://pubmed-medline/baseline/pubmed18n*.xml.gz \
  --input_updates gs://pubmed-medline/updatefiles/pubmed18n*.xml.gz \
  --output_enriched gs://medline-json/analyzed/pubmed18 \
  --max_num_workers 32 \
  --zone europe-west1-d

#  --requirements_file requirements.txt \
#  --output_splitted gs://medline-json/splitted/pubmed18 \


