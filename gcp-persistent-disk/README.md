== README ==
This directory contains the scripts to generate LINK infrastructure and the instructions about how to load the data into ES.


=== Infrastructure ===

The file run.sh creates the infrastructure and the number of VM is hardcoded.

*) 3 Vms: 8cpu and 52 GB
*) Elasticsearch 5.6 and 24 shards

gcloud beta compute --project=$PROJECT \
  instance-groups managed create $NAME \
    --size=3 \
    ...
    
The file startup.sh is used by run.sh for creating the instance template.
