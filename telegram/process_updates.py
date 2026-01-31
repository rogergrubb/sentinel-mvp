import requests, json
token='8271199766:AAGXTUl_JgEAvA9IFp2OV5Oh1oozvGATg6c'
uri=f'https://api.telegram.org/bot{token}/getUpdates?limit=10'
resp=requests.get(uri, timeout=30).json()
print(json.dumps(resp, indent=2))
res=resp.get('result',[])
if not res:
    print('no updates')
else:
    msg=res[-1].get('message',{})
    text=msg.get('text')
    chat_id=msg.get('chat',{}).get('id')
    print('latest:', text, 'chat_id:', chat_id)
    agent_resp=requests.post('http://localhost:9000/agent', json={'prompt': text}, timeout=60)
    print('agent status', agent_resp.status_code)
    try:
        out=agent_resp.json()
    except Exception:
        out={'output': str(agent_resp.text)}
    print('agent returned', out)
    out_text = out.get('output') if isinstance(out, dict) else str(out)
    send = requests.post(f'https://api.telegram.org/bot{token}/sendMessage', data={'chat_id':chat_id,'text': out_text}, timeout=30).json()
    print('send result', json.dumps(send, indent=2))
