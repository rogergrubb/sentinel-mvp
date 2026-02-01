"""Meme coin early warning PoC
- Scans sentinel/raw for $TICKER mentions every 5 minutes
- Checks DexScreener prices every 10 minutes
- Enriches queued tokens via Helius (one call per interval, conservative)
- Writes alerts to sentinel/alerts/YYYYMMDD_HHMMSS_token.json
"""
import re, os, json, time, requests, glob
from collections import defaultdict, deque
from datetime import datetime, timedelta

# Config (from Roger)
HELius_MIN_INTERVAL = 300
HELIUS_API_KEY = "4e0c3be1-0fe6-4a35-8cba-923f54f896a9"
HELIUS_BASE_URL = "https://mainnet.helius-rpc.com"

DATA_ROOT = r'C:/Users/Roger/clawd/sentinel/raw'
ALERT_DIR = r'C:/Users/Roger/clawd/sentinel/alerts'
os.makedirs(ALERT_DIR, exist_ok=True)

DEXScreener_SEARCH = 'https://api.dexscreener.com/latest/dex/search?q='

# state
last_scan = None
last_price_check = None
last_helius = None
queue = deque()
seen_tokens = set()

TOKEN_RE = re.compile(r"\$([A-Za-z]{2,8})")

def load_recent_posts(hours=24):
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    posts = []
    for f in sorted(glob.glob(os.path.join(DATA_ROOT,'*','moltbook_general_*.json')), reverse=True):
        try:
            j = json.load(open(f,'r',encoding='utf-8'))
            scraped = datetime.fromisoformat(j.get('scraped_at').replace('Z',''))
            if scraped < cutoff:
                continue
            posts.extend(j.get('posts',[]))
        except Exception:
            continue
    return posts

def scan_moltbook_for_tokens():
    posts = load_recent_posts(24)
    counts = defaultdict(int)
    sample_post = {}
    for p in posts:
        text = (p.get('title','') + '\n' + p.get('content','') )
        for m in TOKEN_RE.findall(text):
            t = m.upper()
            counts[t]+=1
            if t not in sample_post:
                sample_post[t] = p
    return counts, sample_post

def dexscreener_get_price(token):
    try:
        r = requests.get(DEXScreener_SEARCH + token, timeout=10)
        if r.status_code!=200:
            return None
        d = r.json()
        # pick first result if exists
        if 'pairs' in d and d['pairs']:
            p = d['pairs'][0]
            return {'price': p.get('priceUsd'), 'change': p.get('priceChange')}
        # older responses use 'pairs' or 'pairs' nested
        return None
    except Exception:
        return None

def helius_enrich_solana(mint):
    # Conservative single call: try tokenMeta via RPC if available; fallback to None
    url = HELIUS_BASE_URL
    headers = {'Content-Type':'application/json'}
    payload = {
        'jsonrpc':'2.0','id':1,'method':'getTokenAccountsByOwner','params':[]
    }
    # Placeholder: we'll attempt a basic RPC info call (may not return token metadata on free plan)
    try:
        r = requests.post(url, json={'jsonrpc':'2.0','id':1,'method':'getTokenLargestAccounts','params':[mint]}, headers={'Authorization': 'Bearer '+HELIUS_API_KEY}, timeout=15)
        if r.status_code==200:
            return r.json()
    except Exception:
        pass
    return None

def send_telegram_alert(text):
    # read bot token from TOOLS.md
    try:
        tools = open(r'C:/Users/Roger/clawd/TOOLS.md','r',encoding='utf-8').read()
        import re
        m = re.search(r'Bot Token:\s*(\S+)', tools)
        token = m.group(1) if m else None
    except Exception:
        token = None
    if not token:
        print('No Telegram token found; skipping send')
        return False
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = {'chat_id':'8390029327','text':text}
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.status_code==200
    except Exception:
        return False


def write_alert(token, mentions, price_info, minted_ago=None):
    out = {
        'token': token,
        'mentions': mentions,
        'price': price_info,
        'minted_ago': minted_ago,
        'ts': datetime.utcnow().isoformat()+'Z'
    }
    fname = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ') + f'_{token}.json'
    path = os.path.join(ALERT_DIR, fname)
    with open(path,'w',encoding='utf-8') as f:
        json.dump(out,f,indent=2)
    print('WROTE ALERT', path)
    # send via Telegram
    text = f"🚨 {token} - Early Signal Detected\n{mentions} MoltBook mentions (24h)\nPrice: {price_info} \nDetected: {out['ts']}"
    ok = send_telegram_alert(text)
    print('Telegram sent?', ok)
    return path

if __name__=='__main__':
    print('Starting Meme PoC scanner')
    # simple loop: run scan every 5 min, price every 10, helius one token per 5-10 min
    while True:
        now = time.time()
        try:
            # scan MoltBook every 5 minutes
            if not last_scan or now - (last_scan or 0) > 300:
                counts, samples = scan_moltbook_for_tokens()
                print('Scan found', len(counts), 'tokens with mentions')
                # queue tokens with mentions >= threshold and not seen before
                for t,c in counts.items():
                    if c>=5 and t not in seen_tokens:
                        queue.append(t)
                        seen_tokens.add(t)
                last_scan = now

            # price check every 10 minutes
            if not last_price_check or now - (last_price_check or 0) > 600:
                # check all queued/seen tokens
                tokens_to_check = list(seen_tokens)
                prices = {}
                for t in tokens_to_check:
                    pi = dexscreener_get_price(t)
                    prices[t]=pi
                    time.sleep(1)
                last_price_check = now
                # generate alerts for tokens with price and mentions
                for t in list(seen_tokens):
                    mentions = counts.get(t,0)
                    pi = prices.get(t)
                    if mentions>=5 and pi:
                        write_alert(t, mentions, pi)

            # Helius enrichment: process one queued token every HELIUS_MIN_INTERVAL
            if queue and (not last_helius or now - (last_helius or 0) > HELius_MIN_INTERVAL):
                t = queue.popleft()
                print('Helius enrich for', t)
                # we don't have mint address mapping from symbol; placeholder: try using t as mint
                heli = helius_enrich_solana(t)
                print('Helius result for', t, '->', bool(heli))
                last_helius = now

        except Exception as e:
            print('Loop error', e)
        time.sleep(5)
