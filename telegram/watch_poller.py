import requests, time, json

token='8271199766:AAGXTUl_JgEAvA9IFp2OV5Oh1oozvGATg6c'
uri=f'https://api.telegram.org/bot{token}/getUpdates'
seen_ids=set()
start=time.time()
print('Watching for 60s...')
while time.time()-start<60:
    try:
        r=requests.get(uri, params={'timeout':10,'limit':20}, timeout=20).json()
        res=r.get('result',[])
        for u in res:
            uid=u['update_id']
            if uid in seen_ids: continue
            seen_ids.add(uid)
            msg=u.get('message',{})
            text=msg.get('text')
            chat=msg.get('chat',{}).get('id')
            print('Got update:', uid, text)
            # forward to agent
            agent_resp=requests.post('http://localhost:9000/agent', json={'prompt': text}, timeout=60)
            try:
                out=agent_resp.json()
            except Exception:
                out={'output': agent_resp.text}
            out_text = out.get('output') if isinstance(out, dict) else str(out)
            send = requests.post(f'https://api.telegram.org/bot{token}/sendMessage', data={'chat_id':chat,'text': out_text}, timeout=30).json()
            print('Replied with:', out_text)
        time.sleep(0.5)
    except Exception as e:
        print('poll error', e)
        time.sleep(1)
print('Done')
