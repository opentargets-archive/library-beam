

Below are a series of commands useful for doing things with elasticsearch

Setup a local environment variable for convienience
```sh
HOST=es-190313-102133
```

Increase the threshold for "breakers" to help prevent false triggers
```sh
time curl -XPUT "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/_cluster/settings" -H 'Content-Type: application/json' -d'
   {
      "transient" : {
          "indices.breaker.request.limit" : "90%",
          "network.breaker.inflight_requests.limit": "100%"
          }
   }'
```

Below are a series of commands useful for finding out the status of elasticsearch
```sh
curl "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/_cat/nodes?v&s=name"
curl "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/_cat/indices?v&s=index"
curl "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/_cat/shards?v&s=index,shard,prirep"
curl "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/_cat/allocation?v&s=node"
curl "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/_cluster/health?pretty"
curl "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/_cluster/state?pretty"
```

To set a default number of shards create a "template" for future indexes before creating any
```sh
curl -XPUT "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/_template/default" -H 'Content-Type: application/json' \
-d'{"template":"*","settings":{"number_of_shards":37}}'
```

To actually do the loading
```
time python load2es.py bioentity taggedtext publication concept --es "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200"
```

Required for LINK to work properly
```sh
time curl -XPUT "http://$HOST.$HOST.il4.europe-west1.lb.open-targets-library.internal:9200/pubmed-19-concept/_settings" -H 'Content-Type: application/json' -d'
   {
      "index" : {
          "max_adjacency_matrix_filters" : 500
          }
   }'
```