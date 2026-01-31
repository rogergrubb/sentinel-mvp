from fastapi import FastAPI, Request
import asyncio
import requests
import os
import json

BROKER_URL = os.environ.get('SENTINEL_BROKER_URL','http://localhost:8000/call')

class MiniMeAgent:
    def __init__(self, soul_path='C:/Users/Roger/clawd/SOUL.md', memory_db='agent_memory.json'):
        self.soul_path = soul_path
        self.memory_db = memory_db
        self.load_soul()
        self.load_memory()

    def load_soul(self):
        try:
            with open(self.soul_path,'r',encoding='utf-8') as f:
                self.soul = f.read()
        except Exception:
            self.soul = ''

    def load_memory(self):
        if os.path.exists(self.memory_db):
            self.memory = json.load(open(self.memory_db,'r',encoding='utf-8'))
        else:
            self.memory = {'events':[]}

    def save_memory(self):
        json.dump(self.memory, open(self.memory_db,'w',encoding='utf-8'), indent=2)

    def call_broker(self, prompt):
        # Send to broker
        payload = {'prompt': prompt}
        r = requests.post(BROKER_URL, json=payload, timeout=60)
        r.raise_for_status()
        out = r.json()
        return out

    def handle_prompt(self, prompt):
        out = self.call_broker(prompt)
        # store in memory
        self.memory['events'].append({'prompt':prompt,'response':out})
        self.save_memory()
        return out

app = FastAPI()
agent = MiniMeAgent()

@app.post('/agent')
async def agent_endpoint(req: Request):
    data = await req.json()
    prompt = data.get('prompt')
    if not prompt:
        return {'error':'prompt required'}
    out = agent.handle_prompt(prompt)
    return out

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=9000)
