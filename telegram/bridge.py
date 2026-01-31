import os
import requests
from flask import Flask, request
import threading
import time

app = Flask(__name__)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN','8271199766:AAGXTUl_JgEAvA9IFp2OV5Oh1oozvGATg6c')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID','8390029327')
BROKER_AGENT_URL = os.environ.get('SENTINEL_AGENT_URL','http://localhost:9000/agent')
LAST_UPDATE_ID_FILE = 'last_update_id.txt'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    # Basic handling: forward text to agent via broker
    text = data.get('message',{}).get('text')
    if not text:
        return {'status':'no text'}
    # Send to local agent runtime
    r = requests.post(BROKER_AGENT_URL, json={'prompt': text}, timeout=30)
    if r.status_code==200:
        out = r.json()
        send_telegram(out.get('output','No response'))
    return {'ok':True}

@app.route('/send', methods=['POST'])
def send_endpoint():
    data = request.get_json()
    text = data.get('text')
    send_telegram(text)
    return {'ok':True}

@app.route('/resend_last', methods=['POST'])
def resend_last():
    # Read last agent memory event and resend its output
    try:
        mpath = 'C:/Users/Roger/clawd/projects/sentinel-mvp/agent/agent_memory.json'
        import json
        with open(mpath,'r',encoding='utf-8') as f:
            j = json.load(f)
        last = j.get('events',[])[-1]
        out = last.get('response',{}).get('output')
        if out:
            send_telegram(out)
            return {'ok':True,'sent':out}
    except Exception as e:
        return {'ok':False,'error':str(e)}
    return {'ok':False,'error':'no output found'}

def send_telegram(msg):
    # Always prefer env, fall back to TOOLS.md
    token = TELEGRAM_TOKEN
    chat = CHAT_ID
    if (not token) or (not chat):
        try:
            tools = open('C:/Users/Roger/clawd/TOOLS.md','r',encoding='utf-8').read()
            import re
            m = re.search(r'Bot Token:\s*(\S+)', tools)
            if m and not token:
                token = m.group(1)
            m2 = re.search(r'Your Telegram User ID:\s*(\d+)', tools)
            if m2 and not chat:
                chat = m2.group(1)
        except Exception:
            pass
    if not token or not chat:
        print('Telegram not configured; token/chat missing')
        return
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        r = requests.post(url, data={'chat_id': chat, 'text': msg}, timeout=15)
        print('send_telegram status', r.status_code, r.text)
    except Exception as e:
        print('send_telegram error', e)

# Poll getUpdates to receive messages (since webhook isn't public)
def poll_updates():
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates'
    last_id = None
    if os.path.exists(LAST_UPDATE_ID_FILE):
        try:
            last_id = int(open(LAST_UPDATE_ID_FILE).read().strip())
        except Exception:
            last_id = None
    while True:
        try:
            params = {'timeout':10}
            if last_id:
                params['offset'] = last_id + 1
            r = requests.get(url, params=params, timeout=30)
            j = r.json()
            if j.get('ok'):
                for u in j.get('result',[]):
                    upd_id = u['update_id']
                    msg = u.get('message',{})
                    text = msg.get('text')
                    if text:
                        # forward
                        print('Received msg:', text)
                        resp = requests.post(BROKER_AGENT_URL, json={'prompt': text}, timeout=30)
                        if resp.status_code==200:
                            out = resp.json()
                            send_telegram(out.get('output','No response'))
                    last_id = upd_id
                if last_id:
                    open(LAST_UPDATE_ID_FILE,'w').write(str(last_id))
        except Exception as e:
            print('poll error', e)
        time.sleep(1)

if __name__=='__main__':
    t = threading.Thread(target=poll_updates, daemon=True)
    t.start()
    app.run(port=8080)
