"""OpenSearch index mappings and templates."""

from app.brand import PRODUCT_NAME
from app.search.index_names import ALERTS_INDEX, EVENTS_INDEX_PREFIX, HOSTS_INDEX

TEXT_WITH_KEYWORD = {
    "type": "text",
    "fields": {"keyword": {"type": "keyword", "ignore_above": 8192}},
}

EVENT_PROPERTIES = {
    "id": {"type": "keyword"},
    "host_id": {"type": "keyword"},
    "host_name": {"type": "keyword"},
    "event_type": {"type": "keyword"},
    "severity": {"type": "keyword"},
    "description": TEXT_WITH_KEYWORD,
    "raw_log": TEXT_WITH_KEYWORD,
    "username": {"type": "keyword"},
    "source_ip": {"type": "keyword"},
    "timestamp": {"type": "date"},
}

ALERT_PROPERTIES = {
    "id": {"type": "keyword"},
    "host_id": {"type": "keyword"},
    "host_name": {"type": "keyword"},
    "title": TEXT_WITH_KEYWORD,
    "description": TEXT_WITH_KEYWORD,
    "severity": {"type": "keyword"},
    "status": {"type": "keyword"},
    "created_at": {"type": "date"},
}

HOST_PROPERTIES = {
    "id": {"type": "keyword"},
    "name": TEXT_WITH_KEYWORD,
    "hostname": {"type": "keyword"},
    "status": {"type": "keyword"},
    "ip": {"type": "keyword"},
}

# Legacy flat index (spike) — still created for dev simplicity.
LEGACY_EVENTS_INDEX = "securi-events"

INDEX_MAPPINGS = {
    LEGACY_EVENTS_INDEX: {"mappings": {"properties": EVENT_PROPERTIES}},
    ALERTS_INDEX: {"mappings": {"properties": ALERT_PROPERTIES}},
    HOSTS_INDEX: {"mappings": {"properties": HOST_PROPERTIES}},
}

EVENTS_INDEX_TEMPLATE = {
    "index_patterns": [f"{EVENTS_INDEX_PREFIX}*"],
    "template": {
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
        "mappings": {"properties": EVENT_PROPERTIES},
    },
    "priority": 200,
}


def ism_retention_policy(retention_days: int) -> dict:
    """ISM policy: delete monthly event indices after retention window."""
    return {
        "policy": {
            "description": f"Delete {PRODUCT_NAME} event indices after {retention_days} days",
            "default_state": "hot",
            "states": [
                {
                    "name": "hot",
                    "actions": [],
                    "transitions": [
                        {
                            "state_name": "delete",
                            "conditions": {"min_index_age": f"{retention_days}d"},
                        }
                    ],
                },
                {"name": "delete", "actions": [{"delete": {}}]},
            ],
            "ism_template": [
                {
                    "index_patterns": [f"{EVENTS_INDEX_PREFIX}*"],
                    "priority": 100,
                }
            ],
        }
    }
