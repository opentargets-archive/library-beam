#!/usr/bin/env bash
python -m main \
  --project open-targets \
  --job_name open-targets-medline-process-test \
  --runner DirectRunner \
  --setup_file ./setup.py \
  --input_baseline gs://pubmed-medline/baseline/pubmed18n082*.xml.gz \
  --output_enriched gs://medline-json/test/analyzed/pubmed18 \

#  --requirements_file requirements.txt \


