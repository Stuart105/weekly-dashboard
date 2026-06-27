#!/usr/bin/env python3
"""Debug: dump raw seasonal table structure to diagnose W25 data missing issue"""
import json, os, sys
from pathlib import Path
import requests

BASE = Path(__file__).parent
APP_ID = "cli_a931cdfb8bf89bb5"
APP_SECRET = ""
BASE_ID = "XJAZbw1rqaWHMnsVAJIci7ttnJd"
SEAS_TABLE = "tblhxVtkScorpwxQ"

env_file = BASE / '.env'
if env_file.exists():
    for line in open(env_file):
        line = line.strip()
        if line.startswith("FEISHU_APP_SECRET="):
            APP_SECRET = line.split("=", 1)[1].strip().strip('"').strip("'")

if not APP_SECRET:
    print("❌ FEISHU_APP_SECRET not found"); sys.exit(1)

r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
token = "Bearer " + r.json()["tenant_access_token"]

r2 = requests.get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{SEAS_TABLE}/records",
    headers={"Authorization": token}, params={"page_size": 100}, timeout=15)
items = r2.json().get("data", {}).get("items", [])

print(f"Total rows: {len(items)}")
print("=" * 100)

# Dump all rows with key fields
for i, item in enumerate(items):
    fields = item.get("fields", {})
    category = (fields.get("大类别") or "").replace("\n", "")
    # Show all non-None fields
    non_null = {k: v for k, v in fields.items() if v is not None and v != "" and v != 0}
    print(f"\n--- Row {i} ---")
    print(f"  大类别: '{category}'")
    # Show key columns
    for fid in ["服", "鞋", "字段 3", "字段 4", "字段 6", "字段 8", "字段 9", "字段 10", "字段 11",
                "字段 13", "字段 15", "字段 17", "字段 19", "字段 20", "字段 22"]:
        v = fields.get(fid)
        if v is not None:
            print(f"  {fid}: {v}")

# Also check section boundaries
print("\n\n" + "=" * 100)
print("SECTION BOUNDARIES (rows where 大类别 == '大类别'):")
for i, item in enumerate(items):
    fields = item.get("fields", {})
    category = (fields.get("大类别") or "").replace("\n", "")
    if category == "大类别":
        print(f"  Row {i}: section header")
