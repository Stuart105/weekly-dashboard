"""
全量构建脚本 — 构建dashboard + DeepSeek AI增强分析

用法: python3 build_all.py
"""
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent

# Step 1: 正常构建
print("=" * 50)
print("Step 1: 构建 dashboard...")
print("=" * 50)
ret = subprocess.run([sys.executable, 'build_dashboard.py'], cwd=BASE, capture_output=True, text=True)
if ret.returncode != 0:
    print(f"❌ 构建失败:\n{ret.stderr}")
    sys.exit(1)
print(ret.stdout.strip())

# Step 2: DeepSeek AI 分析
print("=" * 50)
print("Step 2: 调用 DeepSeek AI 分析...")
print("=" * 50)
try:
    ret = subprocess.run([sys.executable, 'deepseek_client.py'], cwd=BASE, capture_output=True, text=True, timeout=60)
    print(ret.stdout.strip())
    if ret.returncode != 0:
        print(f"⚠️  AI 分析异常: {ret.stderr}")
except Exception as e:
    print(f"⚠️  AI 分析超时或失败: {e}")

# Step 3: 注入 AI 分析
print("=" * 50)
print("Step 3: 注入 AI 分析到页面...")
print("=" * 50)
html_file = BASE / 'weekly-dashboard.html'
ai_file = BASE / 'ai_analysis.json'

if html_file.exists() and ai_file.exists():
    with open(ai_file, encoding='utf-8') as f:
        ai_data = json.load(f)
    
    with open(html_file, encoding='utf-8') as f:
        html = f.read()
    
    analysis_text = ai_data['ai_analysis'].strip().replace('\n', '<br>')
    
    ai_section = f'''
  <!-- AI ANALYSIS TAB -->
  <div id="tab-ai" class="analysis-tab" style="display:none">
    <div class="section" style="margin-top:0">
      <div style="background:linear-gradient(135deg,#667eea22,#764ba222);border-radius:12px;padding:16px;line-height:1.8;font-size:14px">
        <div style="font-size:12px;color:#94a3b8;margin-bottom:8px">🤖 DeepSeek {ai_data.get("model","")} 生成</div>
        {analysis_text}
      </div>
    </div>
  </div>'''
    
    # Inject AI tab button after fulltext button
    html = html.replace(
        "onclick=\"switchAnalysisTab('fulltext',this)",
        "onclick=\"switchAnalysisTab('ai',this)\">🤖 AI 分析</button>\n    <button class=\"tab\" onclick=\"switchAnalysisTab('fulltext',this)"
    )
    
    # Inject AI tab content after the LAST </script> (main script, not CDN scripts)
    last_script = html.rfind('</script>')
    if last_script != -1:
        html = html[:last_script] + '</script>' + f'\n\n{ai_section}' + html[last_script + len('</script>'):]
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ AI 分析注入成功")
    print(f"   模型: {ai_data.get('model', '?')}")
    print(f"   推理 tokens: {ai_data.get('usage',{}).get('prompt_tokens','?')}")
else:
    print("⚠️  未找到 AI 分析结果，跳过注入")
    print("   可单独运行: python3 deepseek_client.py")

print("=" * 50)
print("✅ 构建完成")
print("=" * 50)
