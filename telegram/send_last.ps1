$j = Get-Content 'C:\Users\Roger\clawd\projects\sentinel-mvp\agent\agent_memory.json' -Raw | ConvertFrom-Json
$last = $j.events[-1].response.output
$body = @{ chat_id = '8390029327'; text = $last }
Invoke-RestMethod -Method Post -Uri 'https://api.telegram.org/bot8592923136:AAFJfOb8I5R9Zt-dGQSORf0IuWfDSyJAtcQ/sendMessage' -Body $body -TimeoutSec 30
Write-Host 'sent'