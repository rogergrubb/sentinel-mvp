from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, json, glob, time
from datetime import datetime, timedelta

app = FastAPI()
# Add CORS to allow Vercel (or any origin) to fetch data
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RAW_ROOT = r'C:/Users/Roger/clawd/sentinel/raw'

# Start/stop kept for compatibility
@app.post('/start')
def start_agent():
    return {'status':'manual-start-not-implemented'}

@app.post('/stop')
def stop_agent():
    return {'status':'manual-stop-not-implemented'}

@app.get('/logs')
def logs():
    p = 'C:/Users/Roger/clawd/projects/sentinel-mvp/agent/agent_memory.json'
    if os.path.exists(p):
        return {'memory': open(p,'r',encoding='utf-8').read()}
    return {'memory':None}

# Utility: get latest JSON file
def latest_json_for_submolt(submolt='general'):
    files = glob.glob(os.path.join(RAW_ROOT, '*', f'moltbook_{submolt}_*.json'))
    if not files:
        return None
    files.sort()
    return files[-1]

# A) API endpoint: latest scrape
@app.get('/data/latest')
def data_latest(submolt: str = 'general'):
    f = latest_json_for_submolt(submolt)
    if not f:
        return JSONResponse({'error':'no_data'}, status_code=404)
    try:
        with open(f,'r',encoding='utf-8') as fh:
            j = json.load(fh)
        return j
    except Exception as e:
        return JSONResponse({'error':'read_failed','detail':str(e)}, status_code=500)

# A2) Summary endpoint
@app.get('/data/summary')
def data_summary(hours: int = 24, submolt: str = 'general'):
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    files = glob.glob(os.path.join(RAW_ROOT, '*', f'moltbook_{submolt}_*.json'))
    total_posts = 0
    flagged_counts = {}
    submolt_counts = {}
    authors = {}
    for f in files:
        try:
            with open(f,'r',encoding='utf-8') as fh:
                j = json.load(fh)
            scraped = datetime.fromisoformat(j.get('scraped_at').replace('Z',''))
            if scraped < cutoff:
                continue
            for p in j.get('posts',[]):
                total_posts += 1
                for kw in p.get('flagged_keywords',[]):
                    flagged_counts[kw] = flagged_counts.get(kw,0)+1
                sub = j.get('submolt')
                submolt_counts[sub] = submolt_counts.get(sub,0)+1
                a = p.get('author') or 'unknown'
                authors[a] = authors.get(a,0)+1
        except Exception:
            continue
    top_authors = sorted(authors.items(), key=lambda x:-x[1])[:10]
    top_flags = sorted(flagged_counts.items(), key=lambda x:-x[1])[:10]
    return {'total_posts': total_posts, 'top_flags': top_flags, 'top_authors': top_authors, 'submolts': submolt_counts}

# B) SSE stream for flagged signals
def event_stream(submolt='general'):
    seen = set()
    while True:
        f = latest_json_for_submolt(submolt)
        if f:
            try:
                with open(f,'r',encoding='utf-8') as fh:
                    j = json.load(fh)
                for p in j.get('posts', []):
                    pid = p.get('id')
                    if pid in seen:
                        continue
                    seen.add(pid)
                    if p.get('flagged_keywords'):
                        data = {'ts': j.get('scraped_at'), 'post': p}
                        yield f'data: {json.dumps(data)}\n\n'
            except Exception:
                pass
        time.sleep(5)

@app.get('/stream/signals')
def stream_signals(submolt: str = 'general'):
    return StreamingResponse(event_stream(submolt), media_type='text/event-stream')

# C) Export sample data (last N files)
@app.get('/data/export')
def data_export(submolt: str = 'general', last: int = 24):
    files = glob.glob(os.path.join(RAW_ROOT, '*', f'moltbook_{submolt}_*.json'))
    files.sort(reverse=True)
    out = []
    for f in files[:last]:
        try:
            with open(f,'r',encoding='utf-8') as fh:
                out.append(json.load(fh))
        except Exception:
            continue
    return {'count': len(out), 'files': out}

@app.post('/morning-brief')
def morning_brief():
    # Trigger agent to generate a morning brief and send via Telegram using bridge
    import requests
    r = requests.post('http://localhost:9000/agent', json={'prompt':'Generate a concise morning brief from SOUL.md and memory'})
    if r.status_code==200:
        out = r.json()
        try:
            requests.post('http://localhost:8080/send', json={'text': out.get('output','')})
        except Exception as e:
            print('Failed to send telegram', e)
    return {'ok':True}
