# Production security checklist

Set these before internet-facing deployment:

```env
ENVIRONMENT=production
DEBUG=false
ALLOW_REGISTRATION=false
ENABLE_SIMULATION=false
EXCLUDE_SIMULATED_FROM_DASHBOARD=true

# JWT — prefer RS256 in production
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY_PATH=/run/secrets/jwt-private.pem
JWT_PUBLIC_KEY_PATH=/run/secrets/jwt-public.pem

# Or HS256 with a strong random secret (min 32 chars)
# JWT_ALGORITHM=HS256
# JWT_SECRET=

REDIS_URL=redis://redis:6379/0
JOB_QUEUE_BACKEND=redis
JOB_QUEUE_RUN_WORKERS=false
WS_PUBSUB_BACKEND=redis

# Optional scale
EVENT_PARTITIONING_ENABLED=true
SEARCH_BACKEND=opensearch
OPENSEARCH_URL=http://opensearch:9200

# Optional IOC enrichment
VIRUSTOTAL_API_KEY=

# Agent transport
AGENT_MTLS_ENABLED=true
AGENT_MTLS_CA_CERT_PATH=/etc/securi/certs/agent-ca.pem
TRUSTED_PROXY=true
```

Generate RS256 keys:

```bash
openssl genrsa -out jwt-private.pem 2048
openssl rsa -in jwt-private.pem -pubout -out jwt-public.pem
```
