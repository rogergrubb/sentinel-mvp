import requests, json, os
BASE='https://www.moltbook.com/api/v1'
url=BASE+'/agents/register'
agent_name = os.environ.get('MOLT_AGENT_NAME','MiniMeBot')
payload={'name':agent_name,'description':'Autonomous assistant and intelligence collector for SellFast.Now'}
try:
    r=requests.post(url,json=payload,timeout=30)
    print('HTTP', r.status_code)
    j=r.json()
    print(json.dumps(j, indent=2))
    if r.status_code in (200,201):
        agent=j.get('agent',{})
        api_key=agent.get('api_key')
        claim_url=agent.get('claim_url')
        code=agent.get('verification_code')
        cfg_path='C:/Users/Roger/.config/moltbook'
        os.makedirs(cfg_path, exist_ok=True)
        cred_file=os.path.join(cfg_path,'credentials.json')
        json.dump({'api_key':api_key,'agent_name':agent.get('name'),'claim_url':claim_url,'verification_code':code}, open(cred_file,'w'), indent=2)
        tools_path='C:/Users/Roger/clawd/TOOLS.md'
        tools=''
        if os.path.exists(tools_path):
            tools=open(tools_path,'r',encoding='utf-8').read()
        block=f"\n## MOLTBOOK\n- Agent: MiniMeBot\n- API Key: {api_key}\n- Claim URL: {claim_url}\n- Verification Code: {code}\n- Profile: https://moltbook.com/u/MiniMeBot\n\n"
        if '## MOLTBOOK' in tools:
            import re
            tools=re.sub(r'## MOLTBOOK[\s\S]*?\n\n', block, tools)
        else:
            tools=tools+block
        open(tools_path,'w',encoding='utf-8').write(tools)
        print('Saved credentials to', cred_file)
    else:
        print('Registration failed or returned non-success status')
except Exception as e:
    print('ERR', e)
