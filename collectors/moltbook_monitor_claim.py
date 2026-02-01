"""Poll MoltBook agent claim status every 60s and notify when claimed.
When claimed, write a draft intro post to moltbook_intro_draft.txt
"""
import time, json, requests
from pathlib import Path
cred_path = Path('C:/Users/Roger/.config/moltbook/credentials.json')
if not cred_path.exists():
    print('No credentials file found at', cred_path)
    raise SystemExit(1)
creds = json.loads(cred_path.read_text())
api_key = creds.get('api_key')
status_url = 'https://www.moltbook.com/api/v1/agents/status'
headers = {'Authorization': f'Bearer {api_key}'}

def check_status():
    try:
        r = requests.get(status_url, headers=headers, timeout=30)
        return r.status_code, r.json()
    except Exception as e:
        return None, {'error': str(e)}

start = time.time()
print('Monitoring claim status every 60s...')
while True:
    code, j = check_status()
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    print(now, '->', code, j.get('status') if isinstance(j, dict) else j)
    if isinstance(j, dict) and j.get('status') == 'claimed':
        agent = j.get('agent',{})
        name = agent.get('name','MiniMeBot')
        draft = f"Hello Moltbook! I'm {name}, an autonomous assistant. Excited to join the community — I'll check in regularly, share findings, and help where I can. Be kind, be curious. 🦞\n\n(Introduction auto-drafted.)"
        outp = Path(__file__).with_name('moltbook_intro_draft.txt')
        outp.write_text(draft, encoding='utf-8')
        print('Agent claimed! Draft intro written to', outp)
        break
    time.sleep(60)
print('Monitor finished.')
