FROM python:3.11-slim AS builder

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 securi
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini .
COPY agent ./agent
# Bundle must contain agent/main.py + requirements.txt (see app.utils.agent_bundle)
RUN python -c "import sys; sys.path.insert(0, '/app'); from pathlib import Path; from app.utils.agent_bundle import build_agent_bundle; build_agent_bundle(Path('/app/agent/agent-bundle.tar.gz'))"

USER securi
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "30"]
