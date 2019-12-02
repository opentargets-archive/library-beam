gcloud compute instances create es5-node-$1  \
       --image-project debian-cloud \
       --image-family debian-10 \
       --machine-type n1-highmem-8 \
       --zone europe-west1-d \
       --metadata-from-file startup-script=startup.sh \
       --boot-disk-size "1024" \
       --boot-disk-type "pd-ssd" --boot-disk-device-name "es5-node-ssd-$1" \
       --project open-targets-library \
       --scopes default,storage-rw
