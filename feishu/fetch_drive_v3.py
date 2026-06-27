#!/usr/bin/env python3
"""尝试更多方式访问飞书云盘特定文件夹"""
import json, os, sys
from pathlib import Path
import requests

BASE = Path(__file__).parent.parent

APP_ID = os.environ.get("FEISHU_APP_ID", "cli_a931cdfb8bf89bb5")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
if not APP_SECRET:
    env_file = BASE / '.env'
    if env_file.exists():
        for line in open(env_file):
            line = line.strip()
            if line.startswith("FEISHU_APP_SECRET="):
                APP_SECRET = line.split("=", 1)[1].strip().strip('"').strip("'")

def auth():
    r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
    return "Bearer " + r.json()["tenant_access_token"]

TOKEN = auth()
FOLDER_TOKEN = "O7etfItlNl7CLedE04kc2ZHUncM"

# 方法A: 列出 root 所有文件，看看有哪些
print("=== 方法A: 列出 root 所有文件 ===")
all_files = []
pt = None
while True:
    params = {"page_size": 50}
    if pt: params["page_token"] = pt
    r = requests.get("https://open.feishu.cn/open-apis/drive/v1/files",
        headers={"Authorization": TOKEN}, params=params, timeout=15)
    resp = r.json()
    files = resp.get("data", {}).get("files", [])
    all_files.extend(files)
    if not resp.get("data", {}).get("has_more"): break
    pt = resp.get("data", {}).get("page_token")

print(f"总文件数: {len(all_files)}")
for f in all_files:
    print(f"  [{f.get('type')}] {f.get('name')} (token={f.get('token')})")

# 方法B: 尝试用 batch_query 获取文件夹信息
print("\n=== 方法B: batch_query metas ===")
r = requests.post("https://open.feishu.cn/open-apis/drive/v1/metas/batch_query",
    headers={"Authorization": TOKEN, "Content-Type": "application/json"},
    json={
        "request_docs": [{"doc_token": FOLDER_TOKEN, "doc_type": "folder"}],
        "with_url": True
    },
    timeout=15)
print(f"Status: {r.status_code}")
print(r.text[:2000])

# 方法C: 尝试获取文件夹下的子文件（使用正确的参数）
print("\n=== 方法C: 列出文件夹子文件 (多种参数) ===")
for params_set in [
    {"folder_token": FOLDER_TOKEN, "page_size": 50},
    {"folder_token": FOLDER_TOKEN, "page_size": 50, "order_by": "EditedTime", "direction": "DESC"},
]:
    r = requests.get("https://open.feishu.cn/open-apis/drive/v1/files",
        headers={"Authorization": TOKEN}, params=params_set, timeout=15)
    print(f"Params: {params_set}")
    print(f"Status: {r.status_code}")
    print(r.text[:500])

# 方法D: 尝试用 /drive/v1/files/{folder_token}/children
print("\n=== 方法D: children API ===")
r = requests.get(f"https://open.feishu.cn/open-apis/drive/v1/files/{FOLDER_TOKEN}/children",
    headers={"Authorization": TOKEN}, params={"page_size": 50},
    timeout=15)
print(f"Status: {r.status_code}")
print(r.text[:500])