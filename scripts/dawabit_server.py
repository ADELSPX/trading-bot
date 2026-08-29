#!/usr/bin/env python3
"""خادم بوت ضوابط المؤتمرات — واجهة HTTP بسيطة (JSON)
التشغيل: python3 dawabit_server.py
الاستخدام: POST /ask  {"question": "..."}  →  {"answer": "..."}
أو GET  /ask?q=...
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import sys
sys.path.insert(0, '/root/trading-bot/scripts')
from dawabit_bot import ask

PORT = 8797

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        q = parse_qs(urlparse(self.path).query).get('q', [''])[0]
        if not q:
            self._send(400, {"error": "اكتب q="})
            return
        self._send(200, {"answer": ask(q)})

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length else '{}'
        try:
            q = json.loads(body).get('question', '')
        except:
            q = ''
        if not q:
            self._send(400, {"error": "اكتب question"})
            return
        self._send(200, {"answer": ask(q)})

    def log_message(self, *a):
        pass

if __name__ == '__main__':
    print(f"🚀 خادم ضوابط المؤتمرات على http://0.0.0.0:{PORT}")
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
