#!/usr/bin/env python3
"""读取飞书云盘文件夹中的文件"""
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

# 从URL提取folder_token
# URL: https://ncnefidnowjl.feishu.cn/drive/folder/O7etfItlNl7CLedE04kc2ZHUncM
FOLDER_TOKEN = "O7etfItlNl7CLedE04kc2ZHUncM"

print("=" * 80)
print("读取飞书云盘文件夹")
print("=" * 80)

# 1. 列出文件夹中的文件
print("\n--- 文件夹内容 ---")
r = requests.get(
    f"https://open.feishu.cn/open-apis/drive/v1/files",
    headers={"Authorization": TOKEN},
    params={"folder_token": FOLDER_TOKEN, "page_size": 50},
    timeout=15
)
print(f"Status: {r.status_code}")
data = r.json()
print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:3000]}")

# 2. 如果有文件，尝试下载
files = data.get("data", {}).get("files", [])
for f in files:
    print(f"\n--- 文件: {f.get('name')} (token: {f.get('token')}) ---")
    file_token = f.get("token")
    if file_token:
        # 下载文件
        r2 = requests.get(
            f"https://open.feishu.cn/open-apis/drive/v1/files/{file_token}/download",
            headers={"Authorization": TOKEN},
            timeout=30
        )
        print(f"Download status: {r2.status_code}")
        if r2.status_code == 200:
            content_type = r2.headers.get("Content-Type", "")
            print(f"Content-Type: {content_type}")
            # 保存文件
            fname = f.get("name", "unknown")
            save_path = BASE / fname
            with open(save_path, "wb") as fout:
                fout.write(r2.content)
            print(f"Saved to: {save_path} ({len(r2.content)} bytes)")
        else:
            print(f"Response: {r2.text[:500]}")