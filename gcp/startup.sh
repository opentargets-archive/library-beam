#initial setup
#-------------

#update packages, and install prerequisites for elasticsearch
#use the non-interactive frontend for apt so we don't get any prompts
export DEBIAN_FRONTEND=noninteractive
#install with apt-get and autoconfirm
apt-get update
apt-get -yq install \
  openjdk-8-jdk-headless \
  net-tools \
  wget \
  uuid-runtime \
  python-pip \
  python-dev \
  python-urllib3 \
  libyaml-dev \
  less \
  apt-transport-https

#ensure pip is the latest version, more than the debian package
pip install --upgrade pip


#install elasticsearch
#---------------------
ES_VERSION=5.6.15
#download the elasticsearch package
wget --quiet --no-check-certificate \
  --output-document=/tmp/elasticsearch-$ES_VERSION.deb \
  https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-$ES_VERSION.deb
#install the elasticsearch package
#use the non-interactive frontend for dpkg so we don't get any prompts
export DEBIAN_FRONTEND=noninteractive
dpkg -i /tmp/elasticsearch-$ES_VERSION.deb
#post-install cleanup
rm /tmp/elasticsearch-$ES_VERSION.deb

#install elasticsearch google compute engine discovery plugin
#note this requires scopes=compute-rw on the VM
/usr/share/elasticsearch/bin/elasticsearch-plugin -s install discovery-gce

#install elasticsearch google storage plugin
#used to save snapshots into a google cloud bucket
/usr/share/elasticsearch/bin/elasticsearch-plugin -s install repository-gcs

#International Components for Unicode support plugin
/usr/share/elasticsearch/bin/elasticsearch-plugin -s install analysis-icu

#configure elasticsearch
#-----------------------

#configure elasticseach
#  cluster.name            must be unique on network for udp broadcast
#  network.host            allow connections on any network device, not just localhost
#  http.port               use only 9200 nothing else
#  bootstrap.memory_lock   disable swap
#  xpack.security.enabled  turn off xpack extras
cat > /etc/elasticsearch/elasticsearch.yml <<EOF_C 
cloud:
  gce:
    project_id: open-targets-library
    zone: europe-west1-d
discovery:
  zen:
    hosts_provider: gce
    minimum_master_nodes: 3
indices.store.throttle.max_bytes_per_sec: "200mb"
cluster.name: library201911v5
node.name: ${HOSTNAME}
network.host: 0.0.0.0
http.port: 9200
bootstrap.memory_lock: true
EOF_C

#configure elasticseach JVM
cat > /etc/elasticsearch/jvm.options <<EOF_C 
-Xms31g
-Xmx31g
#default elasticsearch settings
-XX:+UseConcMarkSweepGC
-XX:CMSInitiatingOccupancyFraction=75
-XX:+UseCMSInitiatingOccupancyOnly
-XX:+AlwaysPreTouch
-server
-Xss1m
-Djava.awt.headless=true
-Dfile.encoding=UTF-8
-Djna.nosys=true
-Djdk.io.permissionsUseCanonicalPath=true
-Dio.netty.noUnsafe=true
-Dio.netty.noKeySetOptimization=true
-Dio.netty.recycler.maxCapacityPerThread=0
-Dlog4j.shutdownHookEnabled=false
-Dlog4j2.disable.jmx=true
-Dlog4j.skipJansi=true
#-XX:+HeapDumpOnOutOfMemoryError
#rotate gc logfiles
-XX:+UseGCLogFileRotation
-XX:NumberOfGCLogFiles=32
-XX:GCLogFileSize=128M
EOF_C

#configure kernel
#  raise number of open files
#  allow locking an unlimited amount of memory
cat <<EOF_C > /etc/security/limits.conf
* soft nofile 65536
* hard nofile 65536
* soft memlock unlimited
* hard memlock unlimited
EOF_C

# set all sysctl configurations
sysctl -p

# disable swap another way
swapoff -a

#more kernel changes to ensure we get best performance
#more disabling of swap, locking of memory, and reducing unnecessary disk IO
echo "block/sda/queue/scheduler = noop" >> /etc/sysfs.conf
echo noop > /sys/block/sda/queue/scheduler
sed -i 's/\#LimitMEMLOCK=infinity/LimitMEMLOCK=infinity/g' /usr/lib/systemd/system/elasticsearch.service
sed -i '46iLimitMEMLOCK=infinity' /usr/lib/systemd/system/elasticsearch.service
systemctl daemon-reload

#actually start the elasticseach server now everything is ready!
service elasticsearch start
