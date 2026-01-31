from fastapi import FastAPI
import subprocess
import os
app = FastAPI()

# Simple endpoints: start/stop agent (docker compose control assumed)
@app.post('/start')
def start_agent():
    # For prototype we run a background process
    os.system('start cmd /k python C:\\Users\\Roger\\clawd\\projects\\sentinel-mvp\\agent\\agent.py')
    return {'status':'started'}

@app.post('/stop')
def stop_agent():
    # crude stop: user will kill process manually in prototype
    return {'status':'ok'}

@app.get('/logs')
def logs():
    p = 'C:/Users/Roger/clawd/projects/sentinel-mvp/agent/agent_memory.json'
    if os.path.exists(p):
        return {'memory': open(p,'r',encoding='utf-8').read()}
    return {'memory':None}

@app.post('/morning-brief')
def morning_brief():
    # Trigger agent to generate a morning brief and send via Telegram using bridge
    import requests
    r = requests.post('http://localhost:9000/agent', json={'prompt':'Generate a concise morning brief from SOUL.md and memory'})
    if r.status_code==200:
        out = r.json()
        # call telegram bridge send endpoint
        try:
            requests.post('http://localhost:8080/send', json={'text': out.get('output','')})
        except Exception as e:
            print('Failed to send telegram', e)
    return {'ok':True}
