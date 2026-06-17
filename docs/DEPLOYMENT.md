# Deployment Guide

## Phase 1: Local Development

See [README.md](../README.md).

## Phase 2: LAN Deployment

1. Set `SERVER_URL=http://YOUR_LAN_IP:8000` in backend `.env`
2. Set `FRONTEND_URL=http://YOUR_LAN_IP:3000` in backend `.env`
3. Run backend: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. Run frontend: `npm run dev` or build with `npm run build && npm start`
5. Allow Windows Firewall ports 8000 and 3000
6. On Ubuntu VMs, use LAN IP in install command

## Phase 3: Internet Deployment (HTTPS)

Use a reverse proxy (Caddy or nginx):

```nginx
server {
    listen 443 ssl;
    server_name securi.example.com;

    location / {
        proxy_pass http://localhost:3000;
    }
    location /api/ {
        proxy_pass http://localhost:8000;
    }
}
```

Update `SERVER_URL` and `FRONTEND_URL` to HTTPS URLs.

## Environment Variables

| Variable | Description |
|----------|-------------|
| DATABASE_URL | PostgreSQL connection string |
| JWT_SECRET | Secret for JWT signing |
| SERVER_URL | Public backend URL (for agent install) |
| FRONTEND_URL | Dashboard URL (for CORS and reset links) |
| SMTP_* | Email notification settings |
| TELEGRAM_BOT_TOKEN | Telegram bot for alerts |
