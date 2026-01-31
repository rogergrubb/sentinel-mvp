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

# Broker
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --app-dir broker

# Agent
python agent.py (from agent/ directory)
# or: python -m uvicorn app:app --host 0.0.0.0 --port 9000 --app-dir agent

# Telegram bridge
python bridge.py (from telegram/ directory)

# Web dashboard
python -m uvicorn app:app --host 0.0.0.0 --port 7000 --app-dir web

Stopping services
-----------------
- Use Ctrl+C in each terminal to stop services gracefully.
- Or use Task Manager / Stop-Process for 'python' processes carefully.

Key files
---------
- broker/app.py - credential broker + LLM routing
- agent/agent.py - agent runtime (MiniMe)
- telegram/bridge.py - bridge polling and send logic
- agent/agent_memory.json - agent memory (events)
- broker/broker_audit.log - minimal audit log

Secrets
-------
- TOOLS.md holds local credentials (Anthropic key, Telegram tokens). Do not commit TOOLS.md.
- To change the Sentinel bot token, edit telegram/bridge.py or set TELEGRAM_TOKEN env var.

Manual troubleshooting
---------------------
- If bridge fails to send messages, check Telegram token and getUpdates via:
  https://api.telegram.org/bot<token>/getUpdates
- If agent is down, start agent and reprocess pending updates using telegram/process_updates.py

Deploy notes
------------
- For VPS deployment use Docker Compose (docker/docker-compose.yml) and set env vars for keys.
- Run the services under a process supervisor (systemd) for production.

Safety
------
- Do not run multiple processes polling the same Telegram bot token. Use separate bot tokens per product.

