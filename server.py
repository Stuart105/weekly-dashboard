#!/usr/bin/env python3
"""
带 DeepSeek API 代理的 HTTP 服务器
解决浏览器无法直接访问外部API的问题

用法: python3 server.py
"""
import http.server
import json
import os
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent
PORT = 8000

# Read API key
API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
env_file = BASE / '.env'
if not API_KEY and env_file.exists():
    for line in open(env_file):
        line = line.strip()
        if line.startswith('DEEPSEEK_API_KEY='):
            API_KEY = line.split('=', 1)[1].strip().strip('"').strip("'")
            break


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE), **kwargs)

    def do_POST(self):
        """Handle DeepSeek API proxy"""
        if self.path == '/api/deepseek':
            self._proxy_deepseek()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _proxy_deepseek(self):
        """Proxy request to DeepSeek API"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            # Forward to DeepSeek
            req = urllib.request.Request(
                'https://api.deepseek.com/v1/chat/completions',
                data=body,
                headers={
                    'Authorization': f'Bearer {API_KEY}',
                    'Content-Type': 'application/json'
                },
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                result = resp.read().decode('utf-8')

            self.send_response(200)
            self._set_cors_headers()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(result.encode('utf-8'))

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            print(f"DeepSeek API error: {e.code} {error_body[:200]}")
            self.send_response(e.code)
            self._set_cors_headers()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'error': error_body}).encode('utf-8'))

        except Exception as e:
            print(f"Proxy error: {e}")
            self.send_response(500)
            self._set_cors_headers()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

    def end_headers(self):
        # Add CORS headers to all responses
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def log_message(self, format, *args):
        # Only log API calls, not static files
        if '/api/' in (args[0] if args else ''):
            super().log_message(format, *args)


if __name__ == '__main__':
    if not API_KEY:
        print("⚠️  未找到 DEEPSEEK_API_KEY，AI分析将不可用")
        print("   请创建 .env 文件: DEEPSEEK_API_KEY=sk-xxx")
    else:
        print(f"✅ DeepSeek API Key 已加载 ({API_KEY[:12]}...)")

    print(f"🚀 服务器启动: http://localhost:{PORT}")
    print(f"   静态文件: http://localhost:{PORT}/weekly-dashboard.html")
    print(f"   AI代理: http://localhost:{PORT}/api/deepseek")

    with http.server.HTTPServer(('0.0.0.0', PORT), DashboardHandler) as httpd:
        httpd.serve_forever()
