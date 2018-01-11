curl -XPOST 'http://esurl:9200/_aliases?pretty' -H 'Content-Type: application/json' -d '
    {
        "actions": [
            {"add": {"index": "pubmed-18", "alias": "!publication-data"}}
        ]
    } '
