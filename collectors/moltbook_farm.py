"""MoltBook continuous farm
- Writes JSON per scrape to C:/Users/Roger/clawd/sentinel/raw/YYYY-MM-DD/
- Runs every 30 minutes (respects rate limits)
- Sends a Telegram confirmation after the first successful scrape
"""
import os, time, requests, json
from datetime import datetime

# Config
BASE_URL = 'https://www.moltbook.com/api/v1'
SUBMOLT = 'general'
POLL_INTERVAL = 30 * 60  # 30 minutes
OUT_ROOT = r'C:\Users\Roger\clawd\sentinel\raw'
TOOLS_PATH = r'C:\Users\Roger\clawd\TOOLS.md'
TELE_CHAT = '8390029327'

# helpers
def read_tools_key():
    key = None
    tel = None
    try:
        s = open(TOOLS_PATH,'r',encoding='utf-8').read()
        import re
        m = re.search(r'MOLTBOOK\s*-?.*API Key:\s*(moltbook_\S+)', s)
        if m:
            key = m.group(1)
        m2 = re.search(r'Bot Token:\s*(\S+)', s)
        if m2:
            tel = m2.group(1)
    except Exception:
        pass
    return key, tel

def fetch_posts(api_key=None):
    headers = {'User-Agent':'SentinelRecon/1.0'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    url = f'{BASE_URL}/posts?submolt={SUBMOLT}&sort=new&limit=100'
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code == 200:
        try:
            return r.json()
        except Exception:
            return None
    else:
        return None

def normalize_items(data):
    items = []
    if isinstance(data, dict) and 'posts' in data:
        raw = data['posts']
    elif isinstance(data, list):
        raw = data
    else:
        raw = []
    keywords = ['token','launch','coin','$','coordinate','together','join','DAO','viral','trending','spreading','AGI','superintelligence','alignment']
    for it in raw:
        pid = it.get('id') or it.get('post_id')
        title = it.get('title') or ''
        content = it.get('content') or it.get('text') or ''
        upvotes = it.get('upvotes') or it.get('score') or 0
        comments = it.get('comments') or it.get('comment_count') or 0
        author = it.get('author',{}) if isinstance(it.get('author'), dict) else it.get('author')
        # prefer API-provided URL fields, otherwise construct a permalink by id
        url = it.get('url') or it.get('permalink') or it.get('link')
        if not url and pid:
            url = f'https://www.moltbook.com/posts/{pid}'
        created = it.get('created_at')
        flagged = [kw for kw in keywords if kw.lower() in (title+content).lower()]
        items.append({'id':pid,'title':title,'content':content,'author':author,'upvotes':upvotes,'comments':comments,'created_at':created,'url':url,'flagged_keywords':flagged})
    return items

def write_json(items):
    now = datetime.utcnow()
    day = now.strftime('%Y-%m-%d')
    outdir = os.path.join(OUT_ROOT, day)
    os.makedirs(outdir, exist_ok=True)
    fname = now.strftime('moltbook_general_%Y%m%dT%H%M%SZ.json')
    path = os.path.join(outdir, fname)
    payload = {'scraped_at': now.isoformat()+'Z', 'submolt': SUBMOLT, 'posts': items}
    with open(path,'w',encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    return path, len(items)

def send_telegram(token, text):
    if not token:
        return False
    try:
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        r = requests.post(url, data={'chat_id': TELE_CHAT, 'text': text}, timeout=15)
        return r.status_code == 200
    except Exception:
        return False

def main():
    api_key, tel_token = read_tools_key()
    first = True
    print('Starting MoltBook farm, output ->', OUT_ROOT)
    while True:
        data = None
        if api_key:
            try:
                data = fetch_posts(api_key=api_key)
            except Exception:
                data = None
        if data is None:
            # try unauthenticated
            try:
                data = fetch_posts(api_key=None)
            except Exception:
                data = None
        if data is None:
            print('Fetch failed or no data returned; will retry after interval')
        else:
            items = normalize_items(data)
            path, count = write_json(items)
            print(datetime.utcnow().isoformat(), 'WROTE', path, 'items', count)
            if first:
                # notify via Telegram once
                txt = f'SENTINEL data farm online. First scrape complete. {count} posts captured. Saved to {path}'
                ok = send_telegram(tel_token, txt)
                print('Telegram sent?', ok)
                first = False
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
