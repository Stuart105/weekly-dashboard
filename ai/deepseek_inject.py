"""
DeepSeek AI 注入脚本 v2 — 读取独立JS文件，替换占位符后注入HTML
完全避免f-string转义问题
"""
import base64, os
from pathlib import Path

BASE = Path(__file__).parent.parent
HTML_FILE = BASE / 'weekly-dashboard.html'
JS_FILE = BASE / 'ai' / 'deepseek_analyzer.js'

# Read API key
api_key = os.environ.get('DEEPSEEK_API_KEY', '')
env_file = BASE / '.env'
if not api_key and env_file.exists():
    for line in open(env_file):
        line = line.strip()
        if line.startswith('DEEPSEEK_API_KEY='):
            api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
            break

if not api_key:
    print("⚠️  未找到 DeepSeek API Key，跳过注入")
    exit(0)

key_b64 = base64.b64encode(api_key.encode()).decode()
print(f"✅ API Key 已加载 ({api_key[:12]}...)")

# Read JS file (plain text, no f-string issues)
js_code = open(JS_FILE, encoding='utf-8').read()
# Replace placeholder with actual key
js_code = js_code.replace('__DEEPSEEK_KEY_B64__', key_b64)

# Read HTML
html = open(HTML_FILE, encoding='utf-8').read()

# Find and replace the old renderAnalysis function
# Use brace counting to find function boundaries
old_start = html.find('\nfunction renderAnalysis(el){')
if old_start < 0:
    old_start = html.find('function renderAnalysis(el){')

if old_start >= 0:
    # Find the matching closing brace
    search_from = html.find('{', old_start)
    depth = 0
    func_end = search_from
    for i in range(search_from, len(html)):
        ch = html[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                func_end = i + 1
                break
    
    # Replace old function with new JS code
    html = html[:old_start] + '\n' + js_code + '\n' + html[func_end:]
    
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ DeepSeek JS 注入成功")
    print(f"   原函数位置: {old_start}")
    print(f"   新代码大小: {len(js_code)} bytes")
else:
    print("⚠️  未找到 renderAnalysis 函数")
