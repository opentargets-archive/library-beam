import argparse
import codecs
import gzip
import json
import logging
import time
from tempfile import NamedTemporaryFile

from elasticsearch import Elasticsearch
from elasticsearch.helpers import parallel_bulk
from google.cloud import storage
from tqdm import tqdm


'''
tmux new-session "python load2es.py publication --es http://myes:9200"
'''

NODES = 37
INDEX_NAME = 'pubmed-19'
DOC_TYPE = 'publication'

index_config = {
    'bioentity':
        dict(suffix='_bioentities.json.gz',
             index='pubmed-19-bioentity',
             doc_type='bioentity',
             mappings=None,
             pub_id=True),
    'taggedtext':
        dict(suffix='_taggedtext.json.gz',
             index='pubmed-19-taggedtext',
             doc_type='taggedtext',
             mappings=None,
             pub_id=True),
    'publication':
        dict(suffix='_small.json.gz',
             index='pubmed-19',
             doc_type='publication',
             mappings='publication.json',
             pub_id=True
             ),
    'concept':
        dict(suffix='_concepts.json.gz',
             index='pubmed-19-concept',
             doc_type='concept',
             mappings='concept.json',
             pub_id=False),

}


def read_remote_files(bucket, filenames, index_, doc_type, use_pub_id):
    for file_name in filenames:
        for line in read_remote_file(
                bucket, file_name, index_, doc_type, use_pub_id):
            yield line


def read_remote_file(bucket, file_name, index_, doc_type, use_pub_id):
    counter = 0
    while counter <= 3:  # retry 3 times
        counter += 1
        try:
            with NamedTemporaryFile() as cache_file:
                # download the file to a temporary location
                blob = bucket.get_blob(file_name)
                blob.download_to_file(cache_file, )
                # flush the file to make sure it is written to disk
                cache_file.flush()
                # re-open the cache file to decompress it
                zf = gzip.open(cache_file.name, 'rb')

                reader = codecs.getreader("utf-8")
                new_line = []
                for line in reader(zf):
                    new_line.append(line)
                    if line[-1] == '\n':
                        counter += 1
                        if len(new_line) > 1:
                            line_to_yield = ''.join(new_line)
                        else:
                            line_to_yield = line
                        new_line = []
                        if line_to_yield:
                            pub_id = line_to_yield.partition('"pub_id": "')[2].partition('"')[0]
                            if not pub_id:
                                logging.error('no pubmedid parsed for line %s' % line)
                            else:
                                _id = None
                                if use_pub_id and pub_id:
                                    _id = pub_id
                                    yield {
                                        '_index': index_,
                                        '_type': doc_type,
                                        '_id': _id,
                                        '_source': line_to_yield
                                    }
                                else:
                                    yield {
                                        '_index': index_,
                                        '_type': doc_type,
                                        '_source': line_to_yield
                                    }
                break
        except Exception as e:
            logging.exception('could not get file %s: %s' % (file_name, e))
            pass
        if counter == 3:
            logging.error(' file %s skipped', file_name)


def get_file_names(suffix):
    client = storage.Client(project='open-targets-library')
    bucket = client.get_bucket('medline_2019_11')

    for i in bucket.list_blobs(prefix='splitted/'):
        if i.name.endswith(suffix):
            yield i.name


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Load LINK data into Elasticsearch')
    parser.add_argument('indices', nargs='+',
                        help='one or more elasticsearch indexes to load')
    parser.add_argument('--es', dest='es', action='append',
                        default=[],
                        help='elasticsearch url(s)')
    args = parser.parse_args()

    # setup the google cloud storage bucket reading stuff
    client = storage.Client(project='open-targets-library')
    bucket = client.get_bucket('medline_2019_11')

    # prepate elasticsearch for loading
    valid_indices = list(set(args.indices) & set(index_config.keys()))
    logging.info('loading data for indices: ' + ', '.join(valid_indices))
    es = Elasticsearch(
        hosts=args.es,
        max_retry=10,
        retry_on_timeout=True,
    )
    for idx in valid_indices:
        index_data = index_config[idx]

        # delete any old index
        tqdm.write('deleting %s %s' % (
            index_data['index'], es.indices.delete(
                index=index_data['index'], 
                ignore=404, 
                timeout='300s'
            )
        ))
        if index_data['mappings']:
            tqdm.write('creating %s %s' % (
                index_data['index'], es.indices.create(
                    index=index_data['index'], 
                    ignore=400,
                    body=json.load(open('es-mapping/' + index_data['mappings'])),
                    timeout='30s'
                )
            ))
        else:
            tqdm.write('creating %s %s' % (
                index_data['index'], es.indices.create(
                    index=index_data['index'], 
                    ignore=400,
                    timeout='30s'
                )
            ))

        # wait a while for index to stabilize
        time.sleep(15)

        # prepare elasticserach for bulk loading
        temp_index_settings = {
            "index": {
                "refresh_interval": "-1",
                "number_of_replicas": 0,
                "translog.durability": 'async',
            }
        }
        es.indices.put_settings(index=index_data['index'],
                                body=temp_index_settings)

        # get filenames from the bucket for this index
        file_names = tuple(get_file_names(suffix=index_data['suffix']))

        # make a generator of all the rows in all the files
        loaded_rows = read_remote_files(
                bucket,
                file_names,
                index_data['index'],
                index_data['doc_type'],
                index_data['pub_id']
            )

        success, failed = 0, 0
        with tqdm(loaded_rows,
                desc='loading json for index %s' % index_data['index'],
                unit=' docs',
                unit_scale=True,
                total=30000000 if 'concept' not in index_data['index'] else 570000000) as p_loaded_rows:


            # configure how many threads to load in
            # this should be less than 1 per elasticsearch node CPU
            threads = NODES * 2
            counter = 0

            # do the actual loading now
            for ok, item in parallel_bulk(
                    es, p_loaded_rows,
                    raise_on_error=True,
                    chunk_size=1000,
                    thread_count=threads,
                    request_timeout=300
                    ):

                if not ok:
                    failed += 1
                else:
                    success += 1
                counter += 1

        tqdm.write("uploaded %i success, %i failed\n" % (success, failed))

        # return elasticsearch to non-bulk settings
        # this will make it start to reiplicate if applicable
        restore_index_settings = {
            "index": {
                "refresh_interval": "1s",
                "number_of_replicas": 1,
                "translog.durability": 'request',
            }
        }
        es.indices.put_settings(index=index_data['index'],
                                body=restore_index_settings)

