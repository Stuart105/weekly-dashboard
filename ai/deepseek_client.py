"""
DeepSeek AI 分析客户端 — 集成到 weekly-dashboard 构建流程

用法:
    python3 deepseek_client.py [--mode auto|enhance|full]
    
    --mode auto:    自动增强分析文本（默认）
    --mode enhance: 仅增强已有FULL_TEXT
    --mode full:    完全用AI重写分析内容
"""

import json
import os
import sys
import requests
from pathlib import Path

# ─── 配置 ───
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / 'deepseek_config.json'
ENV_FILE = BASE_DIR / '.env'

def load_config():
    """加载配置: 优先环境变量，其次.env文件，最后config.json"""
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    
    # 从 .env 读取
    if not api_key and ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith('DEEPSEEK_API_KEY='):
                    api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
    
    # 从 config.json 读取
    if not api_key and CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
            api_key = cfg.get('api_key', '').replace('${DEEPSEEK_API_KEY}', '')
            if api_key.startswith('sk-'):
                pass  # valid key
            else:
                api_key = os.environ.get('DEEPSEEK_API_KEY', api_key)
    
    if not api_key or api_key.startswith('${'):
        print("❌ 未找到有效的 DeepSeek API Key")
        print("   请设置环境变量: export DEEPSEEK_API_KEY=sk-xxx")
        print("   或创建 .env 文件: DEEPSEEK_API_KEY=sk-xxx")
        sys.exit(1)
    
    return {
        'api_key': api_key,
        'model': 'deepseek-v4-flash',
        'api_base': 'https://api.deepseek.com/v1'
    }


def call_deepseek(messages, system_prompt=None, temperature=0.7, max_tokens=2048):
    """调用 DeepSeek API"""
    cfg = load_config()
    
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)
    
    try:
        resp = requests.post(
            f"{cfg['api_base']}/chat/completions",
            headers={
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json"
            },
            json={
                "model": cfg['model'],
                "messages": full_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=60
        )
        resp.raise_for_status()
        result = resp.json()
        
        content = result['choices'][0]['message']['content']
        reasoning = result['choices'][0]['message'].get('reasoning_content', '')
        
        return {
            'content': content,
            'reasoning': reasoning,
            'model': result['model'],
            'usage': result.get('usage', {})
        }
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   响应: {e.response.text[:500]}")
        return None


def enhance_analysis(data_file=None, mode='auto'):
    """增强分析文本"""
    if data_file is None:
        data_file = BASE_DIR / 'extracted_data.json'
    
    with open(data_file) as f:
        raw = json.load(f)
    
    # 提取关键指标用于 prompt
    kpi = raw.get('r7_kpi', {})
    price = raw.get('r15_price', {})
    daily = raw.get('daily', {})
    
    # 构建数据摘要
    summary = {
        '流水': kpi.get('17', 0),
        '目标': kpi.get('14', 0),
        '达成率': round(float(kpi.get('20', 0) or 0) * 100, 1),
        '同比': round(float(kpi.get('22', 0) or 0) * 100, 1),
        '成交率': round(float(kpi.get('5', 0) or 0) * 100, 1),
        '日均客流': kpi.get('8', 0),
        '客单价': price.get('10', 0),
        '连带率': price.get('16', 0),
        '折扣率': round(float(price.get('28', 0) or 0) * 100, 1),
    }
    
    system_prompt = """你是一个专业的零售数据分析师，擅长从门店数据中提取洞察。
请用简洁专业的中文分析，结构清晰，重点突出。不需要客套话。"""

    user_prompt = f"""分析这家奥莱门店本周的经营数据，给出 3 个核心发现和 2 个改善建议。

本周数据：
- 目标: ¥{summary['目标']:,.0f}
- 实际流水: ¥{summary['流水']:,.0f}
- 达成率: {summary['达成率']}%
- 同比: {summary['同比']:+.1f}%
- 成交率: {summary['成交率']}%
- 日均客流: {summary['日均客流']:.0f}人
- 客单价: ¥{summary['客单价']:,.0f}
- 连带率: {summary['连带率']}件
- 折扣率: {summary['折扣率']}%

请用以下格式回复：
【核心发现】
1. ...
2. ...
3. ...

【改善建议】
1. ...
2. ..."""

    print("🤖 正在调用 DeepSeek 分析...")
    result = call_deepseek(
        messages=[{"role": "user", "content": user_prompt}],
        system_prompt=system_prompt,
        temperature=0.5,
        max_tokens=1024
    )
    
    if result:
        print(f"\n✅ DeepSeek ({result['model']}) 分析完成")
        print(f"   输入 tokens: {result['usage'].get('prompt_tokens', '?')}")
        print(f"   输出 tokens: {result['usage'].get('completion_tokens', '?')}")
        
        if result['reasoning']:
            print(f"\n--- 推理过程 ---\n{result['reasoning']}")
        
        print(f"\n--- AI 分析结果 ---\n{result['content']}")
        
        # 保存结果
        output = {
            'ai_analysis': result['content'],
            'ai_reasoning': result['reasoning'],
            'model': result['model'],
        }
        output_file = BASE_DIR / 'ai_analysis.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n  结果已保存到: {output_file}")
        return output
    
    return None


if __name__ == '__main__':
    mode = 'auto'
    if len(sys.argv) > 1:
        if sys.argv[1] in ('--mode', '-m'):
            mode = sys.argv[2] if len(sys.argv) > 2 else 'auto'
    
    enhance_analysis(mode=mode)
