"""MoltBook public collector
Behavior: Try authenticated requests using MOLTBOOK_API_KEY from TOOLS.md (if present).
If auth fails, fall back to unauthenticated discovery. Run for a specified duration (default 60s*60).
Stores posts into SQLite at moltbook_data.db and writes a sample brief at moltbook_sample_brief.txt
"""
import os, time, requests, sqlite3, json
from datetime import datetime, timedelta

BASE_URL = 'https://www.moltbook.com/api/v1'
DURATION_SECONDS = int(os.environ.get('MOLT_COLLECT_DURATION', '3600'))
POLL_INTERVAL = int(os.environ.get('MOLT_POLL_INTERVAL', '30'))
DB_PATH = os.path.join(os.path.dirname(__file__), 'moltbook_data.db')
SAMPLE_PATH = os.path.join(os.path.dirname(__file__), 'moltbook_sample_brief.txt')
USER_AGENT = 'SentinelRecon/1.0 (+https://sentinel-landing-blue.vercel.app)'

schema = '''
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    author TEXT,
    text TEXT,
    url TEXT,
    submolt TEXT,
    created_at TEXT,
    fetched_at TEXT
);
'''

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript(schema)
    conn.commit()
    return conn

def read_molt_api_key():
    # try env first
    key = os.environ.get('MOLTBOOK_API_KEY')
    if key:
        return key
    # try TOOLS.md
    try:
        tools = open('C:/Users/Roger/clawd/TOOLS.md','r',encoding='utf-8').read()
        import re
        m = re.search(r'MOLTBOOK\s*API\s*-?\s*API Key:\s*(\S+)', tools)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None

def fetch_feed(auth_key=None, params=None):
    headers = {'User-Agent': USER_AGENT}
    if auth_key:
        headers['Authorization'] = f'Bearer {auth_key}'
    url = f"{BASE_URL}/posts"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        return r.status_code, r
    except Exception as e:
        return None, e

def normalize_and_store(conn, items):
    c = conn.cursor()
    added = 0
    for item in items:
        try:
            pid = str(item.get('id') or item.get('post_id'))
            author = item.get('author', {}).get('name') if isinstance(item.get('author'), dict) else item.get('author')
            text = item.get('content') or item.get('text') or item.get('body')
            # prefer API-provided URL fields, otherwise construct a permalink by id
            url = item.get('url') or item.get('permalink') or item.get('link')
            if not url and pid:
                url = f'https://www.moltbook.com/posts/{pid}'
            submolt = item.get('submolt') or (item.get('submolt',{}) .get('name') if isinstance(item.get('submolt'), dict) else None)
            created = item.get('created_at')
            fetched = datetime.utcnow().isoformat()
            if not pid or not text:
                continue
            c.execute('INSERT OR IGNORE INTO posts (id,author,text,url,submolt,created_at,fetched_at) VALUES (?,?,?,?,?,?,?)',
                      (pid, author, text, url, submolt, created, fetched))
            if c.rowcount:
                added += 1
        except Exception:
            continue
    conn.commit()
    return added

def classify_and_summarize(conn):
    # simple summarization: top submolts, top authors, sample posts
    c = conn.cursor()
    rows = c.execute('SELECT submolt, COUNT(*) as cnt FROM posts GROUP BY submolt ORDER BY cnt DESC LIMIT 5').fetchall()
    top_submolts = rows
    rows = c.execute('SELECT author, COUNT(*) as cnt FROM posts GROUP BY author ORDER BY cnt DESC LIMIT 5').fetchall()
    top_authors = rows
    samples = c.execute('SELECT id, author, text, url FROM posts ORDER BY fetched_at DESC LIMIT 10').fetchall()
    return top_submolts, top_authors, samples

def write_sample(top_submolts, top_authors, samples):
    with open(SAMPLE_PATH,'w',encoding='utf-8') as f:
        f.write(f'Recon Sample - {datetime.utcnow().isoformat()}\n\n')
        f.write('Top submolts:\n')
        for s in top_submolts:
            f.write(f' - {s[0]} ({s[1]})\n')
        f.write('\nTop authors:\n')
        for a in top_authors:
            f.write(f' - {a[0]} ({a[1]})\n')
        f.write('\nSample posts:\n')
        for s in samples:
            f.write(f'-- {s[0]} by {s[1]}\n')
            f.write(s[2][:1000].replace('\n',' ') + '\n')
            if s[3]: f.write(f'Link: {s[3]}\n')
            f.write('\n')
    print('WROTE SAMPLE', SAMPLE_PATH)


def main():
    conn = init_db()
    key = read_molt_api_key()
    start = datetime.utcnow()
    end = start + timedelta(seconds=DURATION_SECONDS)
    print('Starting MoltBook collector for', DURATION_SECONDS, 'seconds. Using auth key:', bool(key))
    params = {'sort':'hot','limit':25}
    while datetime.utcnow() < end:
        status, resp = fetch_feed(auth_key=key, params=params)
        if status == 200:
            try:
                data = resp.json()
                items = data.get('posts') if isinstance(data, dict) and 'posts' in data else (data if isinstance(data, list) else [])
                added = normalize_and_store(conn, items)
                print(datetime.utcnow().isoformat(), 'Fetched', len(items), 'items (added', added, ')')
            except Exception as e:
                print('parse error', e)
        else:
            # if auth used and got 401/403, try unauthenticated once
            if key and (status in (401,403)):
                print('Auth failed (', status, '), attempting unauthenticated discovery')
                key = None
                status2, resp2 = fetch_feed(auth_key=None, params=params)
                if status2 == 200:
                    try:
                        data = resp2.json()
                        items = data.get('posts') if isinstance(data, dict) and 'posts' in data else (data if isinstance(data, list) else [])
                        added = normalize_and_store(conn, items)
                        print(datetime.utcnow().isoformat(), 'Unauth fetched', len(items), 'items (added', added, ')')
                    except Exception as e:
                        print('parse error2', e)
                else:
                    print('No public feed available or rate limited; status', status, 'resp', resp)
            else:
                print('Fetch status', status, 'resp', resp)
        time.sleep(POLL_INTERVAL)
    # finished run
    top_submolts, top_authors, samples = classify_and_summarize(conn)
    write_sample(top_submolts, top_authors, samples)

if __name__ == '__main__':
    main()
