
basename = 'pubmed18'

def delete_all_output():
    from google.cloud import storage

    client = storage.Client(project='open-targets')
    bucket = client.get_bucket('medline-json')
    names = list(bucket.list_blobs())
    for i, blob_ref in enumerate(names):
        # print blob_ref.name
        if blob_ref.name.endswith('.json.gz') and \
                (blob_ref.name.startswith('parsed/'+basename)  or
                blob_ref.name.startswith('analyzed/'+basename) or
                blob_ref.name.startswith('splitted/'+basename) or
                blob_ref.name.startswith('test/analyzed/'+basename) or
                blob_ref.name.startswith('test/splitted/'+basename)or
                blob_ref.name.startswith('test/parsed/'+basename)) :
            blob = bucket.get_blob(blob_ref.name)
            blob.delete()
            print 'deleted', i, blob_ref.name, 'of', len(names)

if __name__ == '__main__':
    delete_all_output()