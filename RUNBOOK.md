RUNBOOK - Sentinel MVP

Overview
--------
Sentinel is a minimal hosted agent platform (single-user demo). Components run locally in this workspace under C:\Users\Roger\clawd\projects\sentinel-mvp.

Services and ports
------------------
- Broker (FastAPI): http://localhost:8000
- Agent (FastAPI): http://localhost:9000
- Telegram bridge (Flask): http://127.0.0.1:8080 (polls Telegram getUpdates)
- Web dashboard (FastAPI): http://localhost:7000

Starting services (manual)
--------------------------
Open PowerShell and run each in its own terminal (do NOT run multiple bridge instances):

# Broker (local python)
cd broker
python -m uvicorn app:app --host 0.0.0.0 --port 8000

# Agent (local python)
cd agent
python agent.py
# or: python -m uvicorn app:app --host 0.0.0.0 --port 9000 --app-dir agent

# Telegram bridge (local python)
cd telegram
python bridge.py

# Web dashboard
cd web
python -m uvicorn app:app --host 0.0.0.0 --port 7000

Docker Compose (one-command deploy)
-----------------------------------
# On the target VPS (install Docker and Docker Compose v2)
# Create an env file with secrets: .env
# Contents example:
# ANTHROPIC_API_KEY=sk-...
# SENTINEL_TELEGRAM_TOKEN=8271199766:...
# SENTINEL_TELEGRAM_CHAT_ID=8390029327
# OPENAI_API_KEY=sk-...

# Then run:
cd /home/ubuntu/sentinel-mvp
docker compose up -d

Systemd (bare metal / production)
--------------------------------
# Copy systemd unit files from deploy/systemd to /etc/systemd/system on the VPS.
# Example (as root or via sudo):
cp deploy/systemd/sentinel-broker.service /etc/systemd/system/
cp deploy/systemd/sentinel-agent.service /etc/systemd/system/
cp deploy/systemd/sentinel-bridge.service /etc/systemd/system/
cp deploy/systemd/sentinel-web.service /etc/systemd/system/

# Reload systemd and start services
systemctl daemon-reload
systemctl enable --now sentinel-broker.service
systemctl enable --now sentinel-agent.service
systemctl enable --now sentinel-bridge.service
systemctl enable --now sentinel-web.service

How to check logs
-----------------
# Docker compose logs
docker compose logs -f

# Systemd logs
journalctl -u sentinel-broker.service -f
journalctl -u sentinel-agent.service -f
journalctl -u sentinel-bridge.service -f
journalctl -u sentinel-web.service -f

How to restart services
-----------------------
# Docker compose
docker compose restart

# Systemd
systemctl restart sentinel-agent.service
systemctl restart sentinel-broker.service
systemctl restart sentinel-bridge.service
systemctl restart sentinel-web.service

How to update code
------------------
# On the VPS
cd /home/ubuntu/sentinel-mvp
git pull origin master
# Then restart services (choose systemd or docker compose method above)

Manual troubleshooting
---------------------
- If bridge fails to send messages, check the SENTINEL_TELEGRAM_TOKEN and run:
  curl "https://api.telegram.org/bot${SENTINEL_TELEGRAM_TOKEN}/getUpdates"
- If agent is down, check systemd or docker logs and restart accordingly.

Safety
------
- Do not run multiple processes polling the same Telegram bot token. Use separate bot tokens per product.
- Keep TOOLS.md out of the repo and rotate secrets regularly.

