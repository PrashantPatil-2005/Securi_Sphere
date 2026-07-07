# Database encryption at rest

Securi stores security events, credentials hashes, audit trails, and configuration in external data stores. **Encryption at rest is an infrastructure responsibility** — the application does not implement transparent database encryption (TDE). This guide maps what to protect, how each layer works, and how to verify production posture.

## What Securi stores

| Store | Default path | Sensitive data |
|-------|----------------|----------------|
| **PostgreSQL** | `securi_pg_data` Docker volume or managed RDS/Cloud SQL | Users, JWT refresh metadata, events, alerts, offenses, audit logs, MFA secrets |
| **Redis** | In-memory / optional persistence | Job queue payloads, rate-limit counters, WS pub/sub (ephemeral) |
| **OpenSearch** | `securi_os_data` volume (when `SEARCH_BACKEND=opensearch`) | Indexed events for search |

PostgreSQL is the **primary compliance boundary**. Redis and OpenSearch should follow the same host/volume encryption standards when they hold production data.

## Responsibility model

```
┌─────────────────────────────────────────────────────────┐
│  Application (FastAPI)                                   │
│  • bcrypt password hashes, hashed API keys               │
│  • Immutable audit hash chain (tamper detection)         │
│  • No column-level encryption in app code                │
└──────────────────────────┬──────────────────────────────┘
                           │ TLS recommended in transit
┌──────────────────────────▼──────────────────────────────┐
│  PostgreSQL / Redis / OpenSearch                         │
│  • Files on disk = your encryption layer                 │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  Infrastructure                                          │
│  • Volume/disk encryption, KMS, managed DB encryption    │
└─────────────────────────────────────────────────────────┘
```

## Layer 1 — Volume and disk encryption (required)

Protect the filesystem where database files live.

### Bare metal / VPS

- **Linux:** LUKS full-disk or encrypted LVM for `/var/lib/docker` (or wherever Docker stores volumes).
- Mount encrypted volumes before starting `docker compose`.
- Restrict host SSH and disable direct exposure of Postgres port `5432` (use `docker-compose.prod.yml`, which clears published ports).

### Cloud block storage

| Provider | Approach |
|----------|----------|
| **AWS** | EBS volumes encrypted with AWS KMS; EC2 instance store not recommended for DB |
| **Azure** | Azure Disk Encryption or encrypted managed disks |
| **GCP** | Persistent disks with Google-managed or CMEK keys |
| **DigitalOcean** | Encrypted volumes (enabled by default on block storage) |

### Docker Compose

The default `docker-compose.yml` uses named volumes (`securi_pg_data`). Encryption applies to the **underlying host path**, not inside the container:

```bash
docker volume inspect securi_pg_data
# Mountpoint → must reside on an encrypted filesystem
```

For production, prefer **managed PostgreSQL** over self-hosted Compose Postgres when encryption and HA are required.

## Layer 2 — Managed PostgreSQL (recommended)

Managed services encrypt storage at rest by default and simplify key rotation.

| Service | Setting |
|---------|---------|
| **Amazon RDS / Aurora** | `StorageEncrypted=true`, choose KMS key at create time (cannot enable later without snapshot restore) |
| **Azure Database for PostgreSQL** | Infrastructure encryption on by default; optional customer-managed keys |
| **Google Cloud SQL** | Disk encryption enabled by default; CMEK optional |
| **Neon / Supabase / Railway** | Platform-managed encryption — confirm in vendor SOC 2 / security whitepaper |

**Connection string** (example for RDS):

```env
DATABASE_URL=postgresql+asyncpg://securi:PASSWORD@db.example.us-east-1.rds.amazonaws.com:5432/securi
```

Use a private subnet security group — do not expose Postgres to the public internet.

## Layer 3 — Encryption in transit (complementary)

In-transit TLS does **not** replace at-rest encryption but is required on untrusted networks.

For managed Postgres with `sslmode=require`:

```env
# asyncpg accepts ssl via query string on many deployments
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/securi?ssl=require
```

If your provider issues a custom CA, mount the cert and configure the client trust store on the backend host/container.

Verify from the backend container:

```bash
psql "$DATABASE_URL_SYNC" -c "SHOW ssl;"
# ssl | on
```

(`DATABASE_URL_SYNC` = same URL with `postgresql://` driver for `psql`.)

## Redis and OpenSearch

### Redis

- Default Compose Redis has **no persistence** — data is ephemeral. Still run Redis on an encrypted host and keep it off public ports (`docker-compose.prod.yml`).
- If you enable RDB/AOF persistence, the `.rdb` / `appendonly.aof` files need the same disk encryption as Postgres.

### OpenSearch

- Enable the security plugin and TLS in production (`docs/PRODUCTION_SECURITY.md`, `docs/OPENSEARCH_AT_SCALE.md`).
- Encrypt the `securi_os_data` volume at the hypervisor/block-storage layer.
- For AWS OpenSearch Service, enable encryption at rest and node-to-node encryption in the domain policy.

## Key management

| Practice | Notes |
|----------|-------|
| **Separate secrets from data** | `JWT_SECRET`, `POSTGRES_PASSWORD`, OIDC client secret in a secrets manager — not in git |
| **KMS / CMK** | Use customer-managed keys for regulated workloads; document key custodian and rotation |
| **Rotation** | Rotating storage encryption keys is provider-specific; plan snapshot → restore for self-hosted LUKS key rotation |
| **Backups** | Encrypted backups — see `docs/BACKUP_AUTOMATION.md`; PITR — `docs/PITR_RUNBOOK.md` |

## Application-level controls (already in Securi)

These complement but do **not** replace disk encryption:

| Control | Doc |
|---------|-----|
| Password hashing (bcrypt) | `backend/docs/02-security-audit-report.md` |
| Immutable audit hash chain | `docs/IMMUTABLE_AUDIT_STORE.md` |
| MFA (TOTP) | `docs/MFA.md` |
| CSP nonces | `docs/CSP_NONCES.md` |
| Agent mTLS (optional) | `docs/AGENT_MTLS.md` |

Column-level encryption (e.g. PostgreSQL `pgcrypto`) is **not** used. If regulators require field-level encryption for specific columns, implement via migration + application crypto — that is out of scope for the default deployment.

## Production checklist

- [ ] PostgreSQL data directory on encrypted storage (LUKS, EBS, or managed DB)
- [ ] `docker-compose.prod.yml` — no public Postgres/Redis ports
- [ ] Strong `POSTGRES_PASSWORD` and `JWT_SECRET` / RS256 keys in secrets manager
- [ ] TLS between app and database where traffic crosses a network (`sslmode=require`)
- [ ] OpenSearch volume encrypted + security plugin when `SEARCH_BACKEND=opensearch`
- [ ] Host filesystem permissions restrict access to `.env` and JWT key files
- [ ] Audit log integrity verified periodically (`GET /api/v1/audit/integrity`)
- [ ] Vendor documentation archived for managed DB encryption (SOC 2, ISO 27001 evidence)

## Verify encryption (examples)

### AWS RDS

```bash
aws rds describe-db-instances --db-instance-identifier securi-prod \
  --query 'DBInstances[0].StorageEncrypted'
# true
```

### Linux LUKS

```bash
lsblk -o NAME,FSTYPE,SIZE,MOUNTPOINT
cryptsetup status /dev/mapper/securi-data  # if using LUKS
```

### Docker volume on encrypted mount

```bash
findmnt -T "$(docker volume inspect -f '{{ .Mountpoint }}' securi_pg_data)"
```

## Compliance mapping

| Framework | Typical control | How this doc helps |
|-----------|-----------------|-------------------|
| **SOC 2 CC6.1** | Logical and physical access | Volume encryption + network isolation |
| **ISO 27001 A.8.24** | Use of cryptography | Documented at-rest and in-transit strategy |
| **GDPR Art. 32** | Security of processing | Encryption as appropriate technical measure |
| **PCI DSS 3.4** | Render PAN unreadable | N/A unless storing card data (Securi does not) |

## Related docs

- `docs/PRODUCTION_SECURITY.md` — production env checklist
- `docs/DEPLOYMENT.md` — Compose, Caddy TLS, network layout
- `docs/IMMUTABLE_AUDIT_STORE.md` — tamper-evident audit logs
- `docs/SCHEMA.md` — tables and retention

## PostgreSQL TDE note

PostgreSQL does **not** ship native transparent data encryption inside the database engine (unlike SQL Server TDE). Industry practice is **filesystem or managed-service storage encryption** plus **TLS in transit**. Do not wait for an in-app TDE feature — implement infrastructure encryption before production go-live.
