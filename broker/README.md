Broker service

Purpose: secure credential broker that accepts requests from agent runtime and executes Anthropic API calls on behalf of the agent owner.

Files:
- app.py - FastAPI broker
- Dockerfile

Security:
- Reads Anthropic API key from TOOLS.md or environment
- Logs requests and responses (audit)
- Exposes authenticated endpoint for agent runtime
