import json

from elasticsearch import Elasticsearch
from elasticsearch.helpers import parallel_bulk
from tqdm import tqdm


def delete_all_output():
    from google.cloud import storage

    client = storage.Client(project='open-targets')
    bucket = client.get_bucket('medline-json')
    for i, blob_ref in enumerate(bucket.list_blobs()):
        if blob_ref.name.endswith('.json') and (blob_ref.name.startswith('parsed/medline-base17')  or blob_ref.name.startswith('analyzed/medline-base17')) :
            blob = bucket.get_blob(blob_ref.name)
            blob.delete()
            print 'deleted', i, blob_ref.name

if __name__ == '__main__':
    delete_all_output()