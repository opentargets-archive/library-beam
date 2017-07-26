#!/usr/bin/env bash
python -m main \
  --project open-targets \
  --job_name open-targets-medline-process-test \
  --runner DirectRunner \
  --setup_file ./setup.py \
  --input_baseline gs://pubmed-medline/baseline/medline17n08*.xml.gz \
  --output gs://medline-json/test/parsed/medline-base17 \
  --output_enriched gs://medline-json/test/analyzed/medline-base17 \

#  --requirements_file requirements.txt \


