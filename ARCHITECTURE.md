Sentinel / ClawdBot Two-Bot Architecture

Overview
--------
We operate two separate Telegram bots to avoid polling/webhook conflicts and maintain clear ownership:

1) @MiniMeeeeeeeBot (ClawdBot/MiniMe)
   - Owner: ClawdBot primary processes and gateway
   - Purpose: Personal assistant, always-on MiniMe controlled by ClawdBot gateway
   - Managed by: ClawdBot infrastructure; DO NOT run another poller against this token

2) @SentinelAgent007Bot (Sentinel product)
   - Owner: Sentinel MVP in this repo (manual start)
   - Purpose: Hosted Sentinel agent product for demos and product development
   - Managed by: Sentinel bridge service when started manually

Rules
-----
- Never run two pollers (getUpdates) or webhooks for the same bot token concurrently.
- For demos, keep Sentinel bot dormant until explicitly started (manual run or container start).
- Use separate tokens (stored in TOOLS.md or as env vars) and rotate as needed.

Operational flow (when Sentinel is running)
------------------------------------------
1. Telegram getUpdates -> Sentinel bridge polls the Sentinel bot token
2. Bridge forwards message to Agent (HTTP POST /agent)
3. Agent calls Broker (HTTP POST /call) for LLM response
4. Broker routes to the configured provider (Anthropic/OpenAI) and returns text
5. Bridge sends reply back to Telegram via sendMessage

ClawdBot integration
--------------------
- ClawdBot should continue to own @MiniMeeeeeeeBot. If you want to merge in future, implement routing inside ClawdBot and run a single poller that dispatches to Sentinel runtime as an internal service.

Security
--------
- Broker holds API keys and must be the only service that can use those keys to call external LLMs.
- Keep TOOLS.md private and never commit it. Use environment variables or a secure secrets store in production.

