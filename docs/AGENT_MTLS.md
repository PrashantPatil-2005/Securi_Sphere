# Agent mTLS (optional)

Securi agents use **API keys** over HTTPS by default. For production, enable **mutual TLS** so only enrolled agents with valid client certificates can call `/api/v1/agent/*`.

## Enable

```env
AGENT_MTLS_ENABLED=true
AGENT_MTLS_CA_CERT_PATH=/etc/securi/certs/agent-ca.pem
```

Terminate TLS at your reverse proxy (Caddy/nginx) with:

- Server certificate for API hostname  
- Client certificate verification against your agent CA  
- Forward `X-Forwarded-Proto: https` and set `TRUSTED_PROXY=true`

## Agent enrollment flow

1. Add host in dashboard → generate enrollment token  
2. Generate per-host client cert signed by your CA  
3. Register cert fingerprint:

```bash
curl -X POST http://localhost:8000/api/v1/hosts/HOST_ID/agent-cert \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cert_fingerprint":"SHA256_HEX_OF_AGENT_CERT"}'
```

4. Install cert + key on host (`/etc/securi/agent.crt`, `agent.key`)  
5. Configure agent to present cert on ingest requests  

When `AGENT_MTLS_ENABLED=true`, the enrollment token response includes an `mtls_note` with the fingerprint registration URL.

## Uvicorn direct TLS (dev only)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile=./certs/server.key \
  --ssl-certfile=./certs/server.crt \
  --ssl-ca-certs=./certs/agent-ca.pem \
  --ssl-cert-reqs=2
```

## Status

| Feature | Status |
|---------|--------|
| Config flags | ✅ |
| Reverse-proxy mTLS docs | ✅ |
| Cert fingerprint enrollment API | ✅ `POST /api/v1/hosts/{id}/agent-cert` |
| Alembic `agent_cert_fingerprint` column | ✅ migration `005_agent_cert` |

See `docs/DEPLOYMENT.md` for production TLS with Caddy.
