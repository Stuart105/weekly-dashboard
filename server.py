#!/usr/bin/env python3
"""
带 DeepSeek API 代理 + Excel上传接口 的 HTTP 服务器

用法: python3 server.py
POST /api/deepseek  → DeepSeek API 代理
POST /upload        → 上传 Excel → 自动构建部署
GET  /upload        → 上传页面
"""
import http.server
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
UPLOAD_DIR = BASE / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)
PORT = int(os.environ.get('PORT', '8000'))

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
        """Handle API endpoints"""
        if self.path == '/api/deepseek':
            self._proxy_deepseek()
        elif self.path == '/upload':
            self._handle_upload()
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path == '/upload':
            self._upload_page()
        elif self.path == '/feishu/fetch':
            self._handle_feishu()
        else:
            super().do_GET()

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _handle_feishu(self):
        """Fetch data from Feishu Bitable and return as DATA JSON"""
        try:
            sys.path.insert(0, str(BASE))
            from feishu.feishu_fetch import fetch
            data = fetch()
            self.send_response(200)
            self._json_headers()
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self._json_error(500, f'飞书获取失败: {e}')

    def _handle_upload(self):
        """Handle Excel upload → auto build + deploy"""
        try:
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self._json_error(400, '需要 multipart/form-data')
                return

            # Parse multipart boundary
            boundary = content_type.split('boundary=')[1].strip()
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            # Extract file content from multipart
            file_data = self._parse_multipart(body, boundary)
            if not file_data:
                self._json_error(400, '未找到文件')
                return

            filename = file_data.get('filename', f'upload_{datetime.now().strftime("%m%d_%H%M")}.xlsx')
            filepath = UPLOAD_DIR / filename
            filepath.write_bytes(file_data['content'])

            print(f"📥 收到上传: {filename} ({len(file_data['content'])} bytes)")

            # Run build pipeline
            result = self._run_build(str(filepath))

            self.send_response(200)
            self._json_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            print(f"Upload error: {e}")
            self._json_error(500, str(e))

    def _parse_multipart(self, body, boundary):
        """Simple multipart parser"""
        boundary_bytes = boundary.encode()
        parts = body.split(b'--' + boundary_bytes)
        for part in parts:
            if b'Content-Disposition' not in part or b'filename' not in part:
                continue
            # Split headers and content
            header_end = part.find(b'\r\n\r\n')
            if header_end < 0:
                continue
            headers = part[:header_end].decode('utf-8', errors='ignore')
            content = part[header_end + 4:]
            # Remove trailing \r\n and boundary
            content = content.rstrip(b'\r\n').rstrip(b'--').rstrip(b'\r\n')

            # Extract filename
            filename = 'upload.xlsx'
            for h in headers.split('\r\n'):
                if 'filename=' in h:
                    fname = h.split('filename=')[1].strip('"')
                    if fname:
                        filename = fname
                    break

            return {'filename': filename, 'content': content}
        return None

    def _run_build(self, excel_path):
        """Run extract + build pipeline"""
        try:
            # Step 1: Extract data
            ret = subprocess.run(
                [sys.executable, 'extract_data.py', excel_path],
                cwd=str(BASE), capture_output=True, text=True, timeout=60
            )
            if ret.returncode != 0:
                return {'status': 'error', 'step': 'extract', 'message': ret.stderr[:500]}

            # Step 2: Build dashboard
            ret = subprocess.run(
                [sys.executable, 'build_dashboard.py'],
                cwd=str(BASE), capture_output=True, text=True, timeout=60
            )
            if ret.returncode != 0:
                return {'status': 'error', 'step': 'build', 'message': ret.stderr[:500]}

            # Step 3: Inject AI
            subprocess.run(
                [sys.executable, 'ai/deepseek_inject.py'],
                cwd=str(BASE), capture_output=True, text=True, timeout=30
            )

            # Step 4: Read period info
            import re
            with open(BASE / 'weekly-dashboard.html', 'r', encoding='utf-8') as f:
                html = f.read()
            m = re.search(r'"period":\s*"([^"]+)"', html)
            period = m.group(1) if m else '??'

            return {
                'status': 'ok',
                'period': period,
                'message': f'{period} 周报数据已更新',
                'url': 'https://stuart105.github.io/weekly-dashboard/'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _upload_page(self):
        """Simple upload form"""
        html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>周报上传</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,sans-serif;background:#f0f2f5;display:flex;justify-content:center;align-items:center;min-height:100vh}}
.card{{background:white;border-radius:12px;padding:40px;box-shadow:0 4px 20px rgba(0,0,0,.08);max-width:420px;width:90%;text-align:center}}
h2{{margin-bottom:8px;font-size:22px}}
p{{color:#64748b;margin-bottom:24px;font-size:14px}}
.zone{{border:2px dashed #cbd5e1;border-radius:10px;padding:40px 20px;cursor:pointer;transition:.2s;margin-bottom:16px}}
.zone:hover,.zone.drag{{border-color:#3b82f6;background:#eff6ff}}
.zone p{{font-size:16px;color:#94a3b8;margin:0}}
input{{display:none}}
.btn{{background:#3b82f6;color:white;border:none;padding:10px 28px;border-radius:8px;font-size:15px;cursor:pointer;font-weight:600}}
.btn:disabled{{opacity:.5;cursor:not-allowed}}
.btn-upload{{background:#22c55e;display:none}}
.result{{margin-top:16px;padding:12px;border-radius:8px;font-size:14px;display:none}}
.result.ok{{background:#f0fdf4;color:#065f46;display:block}}
.result.error{{background:#fef2f2;color:#991b1b;display:block}}
</style></head>
<body>
<div class="card">
<h2>📊 周报上传</h2>
<p>上传 Excel 周报文件，自动构建并部署</p>
<div class="zone" id="zone" onclick="document.getElementById('file').click()">
  <p id="zoneText">📁 点击选择文件 或拖拽到此处</p>
</div>
<input type="file" id="file" accept=".xlsx,.xls" onchange="onFileSelected()">
<button class="btn" id="btnSelect" onclick="document.getElementById('file').click()">选择文件</button>
<button class="btn btn-upload" id="btnUpload" onclick="doUpload()">🚀 上传并构建</button>
<div class="result" id="result"></div>
</div>
<script>
var selectedFile = null;
var zone = document.getElementById('zone');
zone.ondragover = function(e){{ e.preventDefault(); zone.classList.add('drag'); }};
zone.ondragleave = function(){{ zone.classList.remove('drag'); }};
zone.ondrop = function(e){{ e.preventDefault(); zone.classList.remove('drag');
  var f = e.dataTransfer.files[0]; if(f) setFile(f); }};
document.getElementById('file').onchange = function(){{ if(this.files[0]) setFile(this.files[0]); }};
function onFileSelected(){{ if(document.getElementById('file').files[0]) setFile(document.getElementById('file').files[0]); }}
function setFile(f){{
  selectedFile = f;
  document.getElementById('zoneText').textContent = '✅ 已选择: ' + f.name + ' (' + (f.size/1024).toFixed(1) + ' KB)';
  document.getElementById('btnUpload').style.display = 'inline-block';
  document.getElementById('result').className = 'result';
}}
function doUpload(){{
  if(!selectedFile) return;
  var fd = new FormData(); fd.append('file', selectedFile);
  var r = document.getElementById('result'); r.className = 'result';
  r.textContent = '⏳ 正在解析构建...'; r.style.display = 'block';
  var bu = document.getElementById('btnUpload'); bu.disabled = true; bu.textContent = '处理中...';
  fetch('/upload', {{method:'POST',body:fd}}).then(function(resp){{ return resp.json(); }})
  .then(function(d){{
    if(d.status==='ok'){{ r.className = 'result ok';
      r.innerHTML = '✅ '+d.message+'<br><small>访问: <a href="'+d.url+'" target="_blank">'+d.url+'</a></small>'; }}
    else{{ r.className = 'result error'; r.textContent = '❌ '+d.message; }}
    bu.disabled = false; bu.textContent = '🚀 上传并构建';
  }}).catch(function(e){{ r.className = 'result error'; r.textContent = '❌ '+e.message; bu.disabled = false; bu.textContent = '🚀 上传并构建'; }});
}}
</script>
</body></html>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _json_headers(self):
        self._set_cors_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')

    def _json_error(self, code, msg):
        self.send_response(code)
        self._json_headers()
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'error', 'message': msg}, ensure_ascii=False).encode('utf-8'))

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
    print(f"   仪表板:  http://localhost:{PORT}/weekly-dashboard.html")
    print(f"   上传:    http://localhost:{PORT}/upload")
    print(f"   AI代理:  http://localhost:{PORT}/api/deepseek")

    with http.server.HTTPServer(('0.0.0.0', PORT), DashboardHandler) as httpd:
        httpd.serve_forever()
