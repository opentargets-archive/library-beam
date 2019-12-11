# README

This directory contains the scripts to generate LINK infrastructure and the instructions about how to load the data into ES.


## Infrastructure 

The file run.sh creates the infrastructure. In this first release the number of VM is hardcoded. (3)

*) 3 Vms: 8cpu and 52 GB <br>
*) Elasticsearch 5.6 and 24 shards <br>

gcloud beta compute --project=$PROJECT \
  instance-groups managed create $NAME \
    --size=3 \
    ...

The file startup.sh is used by run.sh for creating the instance template.

In order to create a new version the user must change the parameter "cluster.name" and if the number of VMs changes the parameter "minimum_master_nodes" must be number_of_total_vm/2+1. (The number of VMs should be odd)

discovery:
  zen:
    hosts_provider: gce
    minimum_master_nodes: 2
indices.store.throttle.max_bytes_per_sec: "200mb"
cluster.name: library201911v7
