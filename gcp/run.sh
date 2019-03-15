#
# This script will create a new elasticsearch cluster
# It is configures as a GCP Instance Group with an Instance Template
# and sets up a Load Balancer in front of it
#


NOW=`date +'%y%m%d-%H%M%S'`
NAME=es-$NOW
PROJECT=open-targets-library

gcloud --project=$PROJECT \
  compute instance-templates create $NAME \
    --custom-cpu 2 \
    --custom-memory 12 \
    --local-ssd="" \
    --image-project debian-cloud \
    --image-family debian-9 \
    --scopes=compute-rw \
    --metadata-from-file startup-script=startup.sh

#if trying to do containers, use this
#    --image-project cos-cloud \
#    --image-family cos-stable \

#NOTE this is a BETA command and liable to change in future!
gcloud beta compute --project=$PROJECT \
  instance-groups managed create $NAME \
    --size=11 \
    --template=$NAME \
    --zone=europe-west1-d 

#create a healthcheck
#used by autohealing and load balancing
#check for 10s every 10s each 6 times for 1m total
gcloud beta compute --project=$PROJECT \
  health-checks create http $NAME \
    --request-path="/_nodes/_local" \
    --port=9200 \
    --check-interval=10s \
    --timeout=10s \
    --unhealthy-threshold=3 \
    --healthy-threshold=3

#configure healthcheck for autohealing
gcloud beta compute --project=$PROJECT \
  instance-groups managed update $NAME \
    --health-check=$NAME \
    --zone=europe-west1-d 

#configure a load balancer
#create the load balancer backend service
gcloud compute --project=$PROJECT \
  backend-services create $NAME \
    --health-checks=$NAME \
    --load-balancing-scheme=internal \
    --protocol=tcp \
    --region=europe-west1
#add the instance group to the backend service
gcloud compute --project=$PROJECT \
  backend-services add-backend $NAME \
    --instance-group=$NAME \
    --region=europe-west1 \
    --instance-group-zone=europe-west1-d

#create a forwarding rule for the actual load balancing
#must use a service label to get dns!
gcloud compute --project=$PROJECT \
  forwarding-rules create $NAME \
    --service-label $NAME \
    --region=europe-west1 \
    --address-region=europe-west1 \
    --load-balancing-scheme=internal \
    --ip-protocol=TCP \
    --ports=all \
    --backend-service=$NAME

# [SERVICE_LABEL].[FORWARDING_RULE_NAME].il4.[REGION].lb.[PROJECT_ID].internal

#curl http://$NAME.$NAME.il4.europe-west1.lb.open-targets-af.internal:9200

#configure firewall to allow healthchecks - manual

#sudo journalctl -n 500 -f -u google-startup-scripts.service

#time curl "localhost:9200/_cat/nodes?v&s=name"
#time curl localhost:9200/_cluster/health?pretty
#time curl localhost:9200/_cluster/state?pretty
#time curl localhost:9200/_cat/master?v
#time curl "localhost:9200/_cat/shards?v&s=index,shard,prirep"