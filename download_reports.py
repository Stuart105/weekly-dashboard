#!/usr/bin/env python3
"""下载 W24 和 W25 周报数据并保存为 JSON"""
import os, requests, json
from pathlib import Path

BASE = Path('/workspace')
APP_ID = 'cli_a931cdfb8bf89bb5'
APP_SECRET = ''
env_file = BASE / '.env'
if env_file.exists():
    for line in open(env_file):
        line = line.strip()
        if line.startswith('FEISHU_APP_SECRET='):
            APP_SECRET = line.split('=', 1)[1].strip().strip('"').strip("'")
            break

r = requests.post('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    json={'app_id': APP_ID, 'app_secret': APP_SECRET}, timeout=10)
TOKEN = 'Bearer ' + r.json()['tenant_access_token']

# 表配置
reports = [
    ('W24', 'JKjNsGqhfhmhG1tbijocjHAUnMd', '0jrzud'),
    ('W25', 'BReJss39ah5PfytirOfcDThansj', '0kOHQv'),
]

for name, token, sheet_id in reports:
    print(f'=== 下载 {name}周报 ===')
    r = requests.get(
        f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{token}/values/{sheet_id}',
        headers={'Authorization': TOKEN},
        params={'range': 'A1:AN250'},
        timeout=15)
    data = r.json()
    values = data.get('data', {}).get('valueRange', {}).get('values', [])
    print(f'  行数: {len(values)}')
    
    # 保存原始数据
    save_path = BASE / f'{name}_raw.json'
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(values, f, ensure_ascii=False, indent=2)
    print(f'  已保存: {save_path}')
    
    # 打印前几行和关键行
    print(f'  --- 前5行 ---')
    for i, row in enumerate(values[:5]):
        # 只显示非null值
        non_null = {j: v for j, v in enumerate(row) if v is not None}
        print(f'    row{i}: {list(non_null.items())[:8]}')
    
    print(f'  --- 行数: {len(values)} ---')
    print()