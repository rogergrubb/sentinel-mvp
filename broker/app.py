from fastapi import FastAPI, HTTPException, Request
import os
import json

import httpx

app = FastAPI()

# Read Anthropic key from TOOLS.md fallback or environment
ANTHROPIC_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not ANTHROPIC_KEY:
    try:
        tools = open('C:/Users/Roger/clawd/TOOLS.md','r',encoding='utf-8').read()
        import re
        m = re.search(r'Anthropic\s*API\s*-\s*API Key:\s*(\S+)', tools)
        if m:
            ANTHROPIC_KEY = m.group(1)
    except Exception:
        ANTHROPIC_KEY = None

if not ANTHROPIC_KEY:
    print('WARNING: Anthropic key not found in env or TOOLS.md')

# Simple health endpoint
@app.get('/health')
def health():
    return {'status':'ok'}

# Exact async Anthropic caller as requested
async def call_anthropic(prompt: str, api_key: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30.0,
        )
        data = response.json()
        return data["content"][0]["text"]

# Minimal broker endpoint: POST /call with JSON {prompt}
@app.post('/call')
async def broker_call(req: Request):
    data = await req.json()
    prompt = data.get('prompt')
    if not prompt:
        raise HTTPException(status_code=400, detail='prompt required')
    # Real Anthropic only; no fallbacks
    if not ANTHROPIC_KEY:
        raise HTTPException(status_code=500, detail='Anthropic key not configured')
    try:
        out_text = await call_anthropic(prompt, ANTHROPIC_KEY)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f'Anthropic request failed: {e}')
    # Log minimal audit
    try:
        with open('broker_audit.log','a',encoding='utf-8') as f:
            f.write(json.dumps({'prompt': prompt, 'response_snippet': out_text[:200]}) + '\n')
    except Exception:
        pass
    return {'output': out_text}
