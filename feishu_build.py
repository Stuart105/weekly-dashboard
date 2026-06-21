#!/usr/bin/env python3
"""从飞书获取最新数据，更新 weekly-dashboard.html 和 index.html 中的页头信息"""
import json, os, re, sys
from pathlib import Path

BASE = Path(__file__).parent

# ── 设置环境变量 ──
for key in ('FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_BASE_ID'):
    val = os.environ.get(key, '')
    if val:
        os.environ[key] = val

# ── 读取飞书数据 ──
sys.path.insert(0, str(BASE))
from feishu_fetch import fetch

print('📡 正在从飞书获取最新数据...')
data = fetch()
print(f'✅ 获取成功: {data["period"]} | {data["week_range"]} | {data["store"]}')

# ── 更新两个 HTML 文件 ──
for html_name in ('weekly-dashboard.html', 'index.html'):
    html_path = BASE / html_name
    if not html_path.exists():
        print(f'⚠️ 跳过不存在的文件: {html_name}')
        continue

    html = html_path.read_text(encoding='utf-8')

    # 更新 DATA 对象中的字段
    replacements = {
        r'"period":\s*"[^"]*"': f'"period": "{data["period"]}"',
        r'"week_range":\s*"[^"]*"': f'"week_range": "{data["week_range"]}"',
        r'"store":\s*"[^"]*"': f'"store": "{data["store"]}"',
    }

    for pattern, replacement in replacements.items():
        html = re.sub(pattern, replacement, html)

    html_path.write_text(html, encoding='utf-8')
    print(f'✅ 已更新: {html_name}')

# ── 输出数据摘要 ──
print(f'\n📊 更新摘要:')
print(f'   周期: {data["period"]}')
print(f'   日期: {data["week_range"]}')
print(f'   门店: {data["store"]}')
print(f'   KPI 指标: {len(data["total_nums"])} 个')
