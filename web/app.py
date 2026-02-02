from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, json, glob, time
from datetime import datetime, timedelta, timezone

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
        # Build standardized response expected by dashboard
        resp = {}
        # pumps: load active pumps file if present
        pumps = {}
        pumps_path = r'C:/Users/Roger/clawd/sentinel/alerts/active_pumps.json'
        try:
            if os.path.exists(pumps_path):
                with open(pumps_path,'r',encoding='utf-8') as pf:
                    pumps = json.load(pf)
        except Exception:
            pumps = {}
        resp['pumps'] = pumps
        # stats: basic stats from the latest scrape
        posts = j.get('posts', []) if isinstance(j, dict) else []
        total_posts = len(posts)
        flagged = sum(1 for p in posts if p.get('flagged_keywords'))
        resp['stats'] = {
            'total_posts': total_posts,
            'signals_detected': flagged,
            'scraped_at': j.get('scraped_at')
        }
        # signals: list of flagged posts (IDs)
        signals = []
        for p in posts:
            if p.get('flagged_keywords'):
                signals.append({'id': p.get('id'), 'title': p.get('title'), 'flags': p.get('flagged_keywords')})
        resp['signals'] = signals
        # include raw posts for drilldown if needed
        resp['posts'] = posts
        return resp
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


# New: expose active pumps
@app.get('/pumps/active')
def pumps_active():
    path = r'C:/Users/Roger/clawd/sentinel/alerts/active_pumps.json'
    if not os.path.exists(path):
        return JSONResponse({'count':0,'pumps':{}}, status_code=200)
    try:
        with open(path,'r',encoding='utf-8') as f:
            j = json.load(f)
        return j
    except Exception as e:
        return JSONResponse({'error':'read_failed','detail':str(e)}, status_code=500)


# New: chart endpoint for symbols (reads daily JSONL files)
@app.get('/chart/{symbol}')
def chart_symbol(symbol: str, timeframe: str = '24h'):
    """Return candle list + simple indicators for symbol and timeframe.
    timeframe: 1h,4h,24h,7d,30d,all
    """
    # normalize symbol
    sym = symbol.upper().lstrip('$')
    # compute timeframe cutoff
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    tf = timeframe.lower()
    if tf == '1h': cutoff = now - timedelta(hours=1)
    elif tf == '4h': cutoff = now - timedelta(hours=4)
    elif tf == '24h': cutoff = now - timedelta(hours=24)
    elif tf in ('7d','1w'): cutoff = now - timedelta(days=7)
    elif tf in ('30d','1m'): cutoff = now - timedelta(days=30)
    else: cutoff = datetime.min.replace(tzinfo=timezone.utc)

    prices_root = os.path.join(r'C:\Users\Roger\clawd','sentinel','metrics','prices', sym)
    candles = []
    if os.path.isdir(prices_root):
        for fname in sorted(os.listdir(prices_root)):
            if not fname.endswith('.jsonl'): continue
            fpath = os.path.join(prices_root, fname)
            try:
                with open(fpath,'r',encoding='utf-8') as fh:
                    for line in fh:
                        try:
                            obj = json.loads(line)
                            # parse candle_time
                            ct = None
                            if 'candle_time' in obj:
                                try:
                                    ct = datetime.fromisoformat(obj['candle_time'].replace('Z','+00:00'))
                                except Exception:
                                    ct = None
                            if ct and ct < cutoff:
                                continue
                            candles.append(obj)
                        except Exception:
                            continue
            except Exception:
                continue
    # compute simple indicators using technical module if available
    indicators = {}
    try:
        import sys as _sys, os as _os
        collectors_path = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'collectors'))
        if collectors_path not in _sys.path:
            _sys.path.insert(0, collectors_path)
        from technical import sma, rsi, price_velocity
        closes = [ (c['candle_time'], float(c.get('close') or c.get('price') or 0)) for c in candles if (c.get('close') or c.get('price')) ]
        prices_only = [p for t,p in closes]
        indicators['sma_10'] = sma(prices_only,10)
        indicators['sma_30'] = sma(prices_only,30)
        indicators['rsi'] = rsi(prices_only,14)
        vel = price_velocity(closes,10)
        indicators['velocity_pct'] = vel.get('price_pct_per_min')
        if prices_only:
            indicators['support'] = min(prices_only)
            indicators['resistance'] = max(prices_only)
    except Exception as e:
        print('indicator calc failed', e)

    return {'symbol': sym, 'timeframe': timeframe, 'candles': candles, 'indicators': indicators, 'signals': []}

