#!/usr/bin/env python3
"""尝试多种方式访问飞书云盘"""
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

# 尝试方法1: 使用 root 文件夹下的子文件列表
print("=== 方法1: 列出 root 下文件 ===")
r = requests.get("https://open.feishu.cn/open-apis/drive/v1/files",
    headers={"Authorization": TOKEN},
    params={"page_size": 50},
    timeout=15)
print(f"Status: {r.status_code}")
print(r.text[:2000])

# 尝试方法2: 使用 explorer 列出子节点
print("\n=== 方法2: explorer ===")
r = requests.get("https://open.feishu.cn/open-apis/drive/v1/files",
    headers={"Authorization": TOKEN},
    params={"folder_token": FOLDER_TOKEN, "page_size": 50, "direction": "DESC"},
    timeout=15)
print(f"Status: {r.status_code}")
print(r.text[:2000])

# 尝试方法3: 检查 app 权限范围
print("\n=== 方法3: 检查权限 ===")
# 获取 bitable 的 files 权限
r = requests.get("https://open.feishu.cn/open-apis/drive/v1/permissions",
    headers={"Authorization": TOKEN},
    params={"token": FOLDER_TOKEN, "type": "folder"},
    timeout=15)
print(f"Status: {r.status_code}")
print(r.text[:2000])

# 方法4: 尝试通过 bitable 的 attachment 下载
# 先看看周报表的附件字段
print("\n=== 方法4: 检查 bitable 附件字段 ===")
BASE_ID = os.environ.get("FEISHU_BASE_ID", "XJAZbw1rqaWHMnsVAJIci7ttnJd")
TABLE_ID = "tblmGijNaVv80ogT"
r = requests.get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{TABLE_ID}/fields",
    headers={"Authorization": TOKEN},
    timeout=15)
print(f"Status: {r.status_code}")
resp = r.json()
if resp.get("data", {}).get("items"):
    for item in resp["data"]["items"][:30]:
        fn = item.get("field_name", "")
        ft = item.get("type", "")
        if "attachment" in str(ft).lower() or "file" in str(fn).lower() or "附件" in str(fn):
            print(f"  字段: {fn} (type={ft})")