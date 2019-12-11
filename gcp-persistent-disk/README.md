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

In order to create a new version the user must change the parameter "cluster.name" (ES cluster) and if the number of VMs (run.sh) changes the parameter "minimum_master_nodes" must be number_of_total_vm/2+1. (The number of VMs should be odd)

discovery:
  zen:
    hosts_provider: gce
    minimum_master_nodes: 2
indices.store.throttle.max_bytes_per_sec: "200mb"
cluster.name: library201911v7


## Load the data in ES
The infrastructure scripts generates a DNS name.
In google cloud these info are stored under  Network services > Load balancing

Eg
[SERVICE_LABEL].[FORWARDING_RULE_NAME].il4.[REGION].lb.[PROJECT_ID].internal

To test if the cluster is available and correct:

> export $HOST= _[SERVICE_LABEL]_
> curl http://$HOST.$HOST.il4.europe-west1.lb.open-targets-af.internal:9200
>
> curl -X GET "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-af.internal:9200/_cat/nodes?v&s=name"
> curl -X GET "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-af.internal:9200/_cluster/health?pretty"

The script "steps.sh" contains the steps to load the data into the ES.

This is a prototype of infrastructure and the aim is builing a list of commands to run.

In future, we aim to create an automatic script.

