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
async def call_anthropic(prompt: str, api_key: str, model: str = 'claude-sonnet-4-20250514') -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30.0,
        )
        data = response.json()
        # flexible return depending on provider shape
        try:
            return data["content"][0]["text"]
        except Exception:
            return data.get('completion') or str(data)

# Optional OpenAI/GPT-4o-mini caller (best-effort if key present)
async def call_gpt4o(prompt: str, api_key: str) -> str:
    async with httpx.AsyncClient() as client:
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type':'application/json'}
        payload = {
            'model': 'gpt-4o-mini',
            'messages': [{'role':'user','content':prompt}],
            'max_tokens': 1024,
            'temperature': 0.2
        }
        r = await client.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload, timeout=30.0)
        j = r.json()
        try:
            return j['choices'][0]['message']['content']
        except Exception:
            return str(j)

# routing decision helper
def route_decision(prompt: str, hint: str = None) -> str:
    # hint may be 'gpt' or 'sonnet'
    if hint == 'gpt':
        return 'gpt4o'
    if hint == 'sonnet':
        return 'sonnet'
    # simple heuristic: short prompts -> gpt; long/complex -> sonnet
    if len(prompt) < 120 and '\n' not in prompt:
        return 'gpt4o'
    return 'sonnet'

# Minimal broker endpoint: POST /call with JSON {prompt}
@app.post('/call')
async def broker_call(req: Request):
    data = await req.json()
    prompt = data.get('prompt')
    if not prompt:
        raise HTTPException(status_code=400, detail='prompt required')
    hint = data.get('model_hint')
    provider = route_decision(prompt, hint)
    # Real provider calls
    if provider == 'gpt4o':
        OPENAI_KEY = os.environ.get('OPENAI_API_KEY')
        if not OPENAI_KEY:
            # try TOOLS.md
            try:
                tools = open('C:/Users/Roger/clawd/TOOLS.md','r',encoding='utf-8').read()
                import re
                m = re.search(r'OPENAI\s*API\s*-\s*API Key:\s*(\S+)', tools)
                if m:
                    OPENAI_KEY = m.group(1)
            except Exception:
                OPENAI_KEY = None
        if not OPENAI_KEY:
            # fallback to Anthropic sonnet if OpenAI key missing
            out_text = await call_anthropic(prompt, ANTHROPIC_KEY, model='claude-sonnet-4-20250514')
        else:
            out_text = await call_gpt4o(prompt, OPENAI_KEY)
    else:
        out_text = await call_anthropic(prompt, ANTHROPIC_KEY, model='claude-sonnet-4-20250514')

    # Log minimal audit
    try:
        with open('broker_audit.log','a',encoding='utf-8') as f:
            f.write(json.dumps({'prompt': prompt, 'provider': provider, 'response_snippet': (out_text or '')[:200]}) + '\n')
    except Exception:
        pass
    return {'output': out_text, 'provider': provider}
