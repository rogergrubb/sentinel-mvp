"""OpenClaw public collector (safe, public-only)

Usage: edit CONFIG at top with base_url or run with env OPENCLAW_BASE_URL.
This script polls the OpenClaw public feed, stores posts into SQLite, and
writes a minimal log. It is intentionally conservative: rate-limited and
respects terms of service (set delay accordingly).
"""
import os
import time
import requests
import sqlite3
from datetime import datetime

BASE_URL = os.environ.get('OPENCLAW_BASE_URL', 'https://openclaw.example/api')
POLL_INTERVAL = int(os.environ.get('OPENCLAW_POLL_INTERVAL', '30'))  # seconds
DB_PATH = os.environ.get('OPENCLAW_DB','openclaw_data.db')
USER_AGENT = 'SentinelRecon/1.0 (+https://sentinel-landing-blue.vercel.app)'

# Minimal schema: posts table
schema = '''
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    author TEXT,
    text TEXT,
    url TEXT,
    created_at TEXT,
    fetched_at TEXT
);
'''

def init_db(path=DB_PATH):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.executescript(schema)
    conn.commit()
    return conn

def fetch_public_feed(base_url=BASE_URL):
    # expected: GET {base_url}/public/posts or similar
    # This is a conservative attempt: try common endpoints
    candidates = [
        f"{base_url}/posts",
        f"{base_url}/public/posts",
        f"{base_url}/v1/posts",
        f"{base_url}/feed",
        base_url
    ]
    headers = {'User-Agent': USER_AGENT}
    for url in candidates:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                try:
                    j = r.json()
                    return j, url
                except Exception:
                    # not JSON
                    continue
        except Exception:
            continue
    return None, None

def normalize_and_store(conn, data):
    # Expect data to be a list of posts or dict with 'posts' key
    if isinstance(data, dict) and 'posts' in data:
        items = data['posts']
    elif isinstance(data, list):
        items = data
    else:
        # unknown shape
        return 0
    c = conn.cursor()
    added = 0
    for item in items:
        try:
            pid = str(item.get('id') or item.get('post_id') or item.get('uuid'))
            author = item.get('author') or item.get('user') or item.get('handle')
            text = item.get('text') or item.get('body') or item.get('content')
            url = item.get('url') or item.get('link')
            created = item.get('created_at') or item.get('timestamp')
            fetched = datetime.utcnow().isoformat()
            if not pid or not text:
                continue
            c.execute('INSERT OR IGNORE INTO posts (id,author,text,url,created_at,fetched_at) VALUES (?,?,?,?,?,?)',
                      (pid, author, text, url, created, fetched))
            if c.rowcount:
                added += 1
        except Exception:
            continue
    conn.commit()
    return added

def main_loop():
    conn = init_db()
    print('OpenClaw collector started. Base URL:', BASE_URL)
    while True:
        data, url = fetch_public_feed()
        if data is None:
            print(datetime.utcnow().isoformat(), 'No public feed found at candidates; sleeping')
        else:
            added = normalize_and_store(conn, data)
            print(datetime.utcnow().isoformat(), f'Fetched from {url}; new posts added: {added}')
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main_loop()
