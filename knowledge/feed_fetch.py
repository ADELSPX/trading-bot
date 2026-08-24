#!/usr/bin/env python3
"""تغذية المعرفة التداولية — فهد (تلجرام) + محمد مطر (X)"""
import urllib.request, re, html, json, os, subprocess
from datetime import datetime

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8', errors='ignore')

today = datetime.now().strftime('%Y-%m-%d')
output = []

# 1. فهد — تلجرام (القناة الرئيسية)
try:
    content = fetch('https://t.me/s/FAHAD_GAMMA1')
    msgs = re.findall(r'data-post="([^"]+)"[^>]*>.*?<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL)
    output.append(f"=== فهد (تلجرام) — آخر {len(msgs)} رسالة ===")
    for post_id, t in msgs[:8]:
        clean = re.sub(r'<[^>]+>', ' ', t)
        clean = html.unescape(clean).strip()
        clean = re.sub(r'\s+', ' ', clean)
        if clean and clean not in ('QQQ','NDX','SPX','CRWV','TSLA','MSTR'):
            output.append(f"[{post_id}] {clean[:200]}")
except Exception as e:
    output.append(f"فهد: {e}")

# 2. محمد مطر — X (عبر xurl CLI)
try:
    r = subprocess.run(['tw', 'user-posts', 'ArabicWallSt', '-n', '3', '--json'],
                       capture_output=True, text=True, timeout=30)
    content = r.stdout
    idx = content.find('{')
    if idx > -1:
        d = json.loads(content[idx:])
        posts = d.get('data', [])
        output.append(f"\n=== محمد مطر (X) — آخر {len(posts)} بوست ===")
        for p in posts[:3]:
            text = (p.get('text') or '')[:200].replace('\n', ' ')
            created = (p.get('createdAtLocal') or '')[:16]
            output.append(f"[{created}] {text}")
except Exception as e:
    output.append(f"محمد مطر: {e}")

result = "\n".join(output)
print(result)

# Save to knowledge feed
os.makedirs('/root/trading-bot/knowledge/feed', exist_ok=True)
path = f'/root/trading-bot/knowledge/feed/feed-{today}.md'
with open(path, 'w', encoding='utf-8') as f:
    f.write(f"# تغذية المعرفة {today}\n\n{result}\n")
print(f"\n💾 حفظت في: {path}")
