"""
Telegram Webhook Bridge — يستقبل إشارات ويحولها تلغرام فوراً
______________________________________________________________
يشغل كخدمة systemd على port 7890
"""

import json, os
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.parse

# Read token from Hermes .env (live token)
_env_path = "/root/.hermes/.env"
BOT_TOKEN = "8474030966:***"
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                t = line.split("=", 1)[1].strip().strip('"').strip("'")
                if t:
                    BOT_TOKEN = t
                    break
CHAT_ID = "15036469"


def send_telegram(text: str) -> bool:
    """إرسال رسالة تلغرام"""
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }).encode()
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def format_signal(sig: dict) -> str:
    """تنسيق الإشارة لرسالة تلغرام"""
    t = sig.get("type", "")

    if t == "entry":
        msg = f'🚨 *{sig.get("symbol", "SPX")} — {sig.get("direction", "PUT").upper()}*\n'
        msg += f'{sig.get("signal_type", "مضاربة سريعة")}\n\n'
        msg += f'💰 الدخول: ${sig.get("entry", "?")}\n'
        msg += f'🎯 الهدف 1: ${sig.get("target1", "?")}\n'
        if sig.get("target2"):
            msg += f'🎯 الهدف 2: ${sig["target2"]}\n'
        msg += f'🛑 الوقف: ${sig.get("stop", "?")}\n\n'
        if sig.get("delta"):
            msg += f'📐 Delta: {sig["delta"]}\n'
        if sig.get("ror"):
            msg += f'📊 R:R: {sig["ror"]}\n'
        if sig.get("greeks"):
            msg += f'📊 {sig["greeks"]}\n'
        msg += f'\n{sig.get("note", "للتحليل فقط")}'
        return msg

    elif t == "update":
        msg = f'📊 *{sig.get("symbol", "")} — تحديث*\n\n'
        msg += f'💰 P&L: {sig.get("pnl", "?")}\n'
        if sig.get("suggestion"):
            msg += f'💡 اقتراح: {sig["suggestion"]}\n'
        return msg

    elif t == "close":
        msg = f'✅ *صفقة مقفلة*\n\n'
        msg += f'🪙 {sig.get("symbol", "")} {sig.get("direction", "")}\n'
        msg += f'💰 الدخول: ${sig.get("entry", "?")} ← الخروج: ${sig.get("exit", "?")}\n'
        msg += f'📈 P&L: {sig.get("pnl", "?")}\n'
        if sig.get("duration"):
            msg += f'⏱ المدة: {sig["duration"]}\n'
        msg += f'\n{sig.get("reason", "انتهت")}'
        return msg

    else:
        return f'ℹ️ *إشارة*\n{json.dumps(sig, ensure_ascii=False)}'


class SignalHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            sig = json.loads(body)
            text = format_signal(sig)
            ok = send_telegram(text)
            status = "sent" if ok else "failed"
            self.send_response(200)
        except Exception as e:
            status = f"error: {e}"
            self.send_response(400)

        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": status}).encode())

    def log_message(self, format, *args):
        if len(args) >= 3: print(f"[Webhook] {args[0]} {args[1]} {args[2]}")


if __name__ == "__main__":
    port = 7890
    server = HTTPServer(("0.0.0.0", port), SignalHandler)
    print(f"🚀 Telegram Webhook Bridge on port {port}")
    print(f"   POST http://localhost:{port}  ← البوت يسوي POST هنا")
    server.serve_forever()
