Sentinel MVP - Repo

Overview
--------
This repository contains the Sentinel MVP: a minimal hosted agent platform implementing:
- Credential Broker (Anthropic proxy)
- Agent runtime (MiniMe)
- Telegram bridge (owner <-> agent)
- Simple web dashboard (start/stop agent, view logs, "Morning Brief" trigger)

Structure
---------
- broker/        FastAPI credential broker service
- agent/         Agent runtime (async loop)
- web/           Dashboard (FastAPI) + simple UI
- telegram/      Telegram bridge service
- docker/        Docker Compose and deployment files

Goals
-----
Phase 0 (Day 0): repo skeleton and stubs
Phase 1 (Day 1-3): broker + agent + telegram glue
Phase 2 (Day 4-10): persistence, dashboard, deployment

Security
--------
- Broker holds Anthropic key and mediates all LLM calls
- Agent never sees raw API keys
- Audit logs for all brokered calls

