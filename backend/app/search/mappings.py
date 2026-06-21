EVENTS_INDEX = "securi-events"
ALERTS_INDEX = "securi-alerts"
HOSTS_INDEX = "securi-hosts"

INDEX_MAPPINGS = {
    EVENTS_INDEX: {
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "host_id": {"type": "keyword"},
                "host_name": {"type": "keyword"},
                "event_type": {"type": "keyword"},
                "severity": {"type": "keyword"},
                "description": {"type": "text"},
                "raw_log": {"type": "text"},
                "username": {"type": "keyword"},
                "source_ip": {"type": "keyword"},
                "timestamp": {"type": "date"},
            }
        }
    },
    ALERTS_INDEX: {
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "title": {"type": "text"},
                "description": {"type": "text"},
                "severity": {"type": "keyword"},
                "status": {"type": "keyword"},
                "created_at": {"type": "date"},
            }
        }
    },
    HOSTS_INDEX: {
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "name": {"type": "text"},
                "hostname": {"type": "keyword"},
                "status": {"type": "keyword"},
                "ip": {"type": "keyword"},
            }
        }
    },
}
