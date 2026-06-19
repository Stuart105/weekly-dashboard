"""
DeepSeek AI 实时分析注入脚本
读取已构建的 weekly-dashboard.html，注入 DeepSeek API 调用 JS 代码

用法: python3 deepseek_inject.py
"""
import base64, os, re
from pathlib import Path

BASE = Path(__file__).parent
HTML_FILE = BASE / 'weekly-dashboard.html'

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

# Read HTML
html = open(HTML_FILE, encoding='utf-8').read()

# Build the JS code to inject (NOT f-string - regular string, so braces are fine)
inject_js = f'''
// DeepSeek AI integration (injected by deepseek_inject.py)
const DEEPSEEK_KEY_ENC='{key_b64}';
const DEEPSEEK_MODEL='deepseek-v4-flash';

function callDeepSeek(prompt,callback){{
  if(!DEEPSEEK_KEY_ENC){{ callback(null,'未配置API密钥'); return; }}
  const key=atob(DEEPSEEK_KEY_ENC);
  fetch('https://api.deepseek.com/v1/chat/completions',{{
    method:'POST',
    headers:{{'Authorization':'Bearer '+key,'Content-Type':'application/json'}},
    body:JSON.stringify({{
      model:DEEPSEEK_MODEL,
      messages:[
        {{role:'system',content:'你是一个零售数据分析专家，用专业简洁的中文分析门店数据。'}},
        {{role:'user',content:prompt}}
      ],
      temperature:0.7,
      max_tokens:2048
    }})
  }})
  .then(r=>r.json()).then(d=>{{
    if(d.choices&&d.choices[0]) callback(d.choices[0].message.content);
    else callback(null,'API返回异常: '+JSON.stringify(d));
  }})
  .catch(e=>callback(null,'网络错误: '+e.message));
}}

function renderAnalysis(el){{
  const btn=el||document.querySelector('button[onclick*="renderAnalysis"]');
  if(btn){{ btn.classList.add('loading'); btn.disabled=true; }}
  showToast('🔄 AI正在分析数据...','info');
  const D=DATA;
  var p='请分析以下奥莱门店本周经营数据，给出核心发现（3条）和改善建议（2条）：';
  p+='\\n\\n【经营数据】';
  p+='\\n- 门店：'+D.store;
  p+='\\n- 周期：'+D.period+'（'+D.week_range+'）';
  p+='\\n- 目标流水：¥'+(D.target/10000).toFixed(1)+'万';
  p+='\\n- 实际流水：¥'+(D.actual/10000).toFixed(1)+'万';
  p+='\\n- 达成率：'+D.achieve.toFixed(1)+'%';
  p+='\\n- 同比：'+(D.yoy>0?'+':'')+D.yoy.toFixed(1)+'%';
  p+='\\n- 环比：'+(D.mom>0?'+':'')+D.mom.toFixed(1)+'%';
  p+='\\n- 成交率：'+D.conv.toFixed(1)+'%';
  p+='\\n- 日均客流：'+D.flow.toFixed(0)+'人';
  p+='\\n- 客单价：¥'+D.avg_t.toFixed(0);
  p+='\\n- 连带率：'+D.attach_r.toFixed(2)+'件';
  p+='\\n- 件单价：¥'+D.unit_p.toFixed(0);
  p+='\\n- 折扣率：'+D.disc.toFixed(1)+'%';
  p+='\\n- O2O流水：¥'+(D.o2o/10000).toFixed(2)+'万';
  p+='\\n- SSSG：'+(D.sssg>0?'+':'')+D.sssg.toFixed(1)+'%';
  var c=D.category;
  if(c){{
    p+='\\n\\n【品类分析】';
    p+='\\n- 鞋：¥'+(c['鞋']?((c['鞋'].flow/10000).toFixed(1)):'0')+'万（同比'+(c['鞋']?((c['鞋'].yoy>0?'+':'')+c['鞋'].yoy.toFixed(1)+'%'):'--')+'）';
    p+='\\n- 服：¥'+(c['服']?((c['服'].flow/10000).toFixed(1)):'0')+'万（同比'+(c['服']?((c['服'].yoy>0?'+':'')+c['服'].yoy.toFixed(1)+'%'):'--')+'）';
  }}
  p+='\\n\\n【日别达成】';
  var days=['周一','周二','周三','周四','周五','周六','周日'];
  for(var i=0;i<7&&i<D.daily.length;i++){{
    p+='\\n- '+days[i]+'：'+D.daily[i].a.toFixed(1)+'%';
  }}
  p+='\\n\\n请用以下格式回复：【核心发现】1. 2. 3. 【改善建议】1. 2.';

  callDeepSeek(p,function(result,err){{
    if(err){{
      var idx=Math.floor(Math.random()*FULL_TEXTS.length);
      document.getElementById('fullTextContent').innerHTML=
        '<div style="color:#94a3b8;font-size:12px;margin-bottom:8px">⚠️ AI离线，使用预制分析</div>'+FULL_TEXTS[idx];
      showToast('⚠️ AI离线','info');
    }}else{{
      var html=result.replace(/\\n/g,'<br>').replace(/【([^】]+)】/g,'<br><b>【$1】</b>');
      document.getElementById('fullTextContent').innerHTML=
        '<div style="font-size:12px;color:#6366f1;margin-bottom:8px">🤖 DeepSeek AI 实时生成</div>'+html;
      showToast('✅ AI分析完成','success');
    }}
    if(btn){{ btn.classList.remove('loading'); btn.disabled=false; }}
  }});
}}
'''

# Inject the JS code: replace old renderAnalysis with new one
# Use brace counting to find function boundaries
old_render_start = html.find('\nfunction renderAnalysis(el){')
new_render_start = html.find('\n// ─── INIT')

if old_render_start > 0 and new_render_start > old_render_start:
    old_render_end = new_render_start
    # Build the complete new JS: preserve code before + inject new code + preserve code after INIT
    before = html[:old_render_start]
    after = html[old_render_start:]  # includes old function + everything after
    
    # Remove old function by finding the next top-level function declaration or comment
    # after the function's closing brace
    search_start = after.find('function renderAnalysis(el){')  # start of the func body
    if search_start >= 0:
        # Count braces to find the matching closing brace
        depth = 0
        func_end = search_start
        for i in range(search_start, len(after)):
            c = after[i]
            if c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    func_end = i + 1  # include the closing brace
                    break
        
        if func_end > search_start:
            after = after[:search_start] + inject_js + after[func_end:]
            html = before + after
        else:
            # fallback: just append
            html = html + '\n' + inject_js
    else:
        html = html + '\n' + inject_js
else:
    # No old renderAnalysis found, just append
    html = html + '\n' + inject_js

with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ DeepSeek JS 注入成功")
print(f"   API Key: {api_key[:12]}...")
