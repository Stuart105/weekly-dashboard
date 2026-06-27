#!/usr/bin/env python3
"""检查季节数据表结构"""
import os, sys, requests
sys.path.insert(0, '/workspace/feishu')
from feishu_build import BASE_ID, TOKEN

SEAS_TABLE = "tblhxVtkScorpwxQ"

print("=" * 80)
print("季节数据表结构检查")
print("=" * 80)

r = requests.get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{SEAS_TABLE}/records",
    headers={"Authorization": TOKEN},
    params={"page_size": 100},
    timeout=15
)

data = r.json()
items = data.get("data", {}).get("items", [])

print(f"共获取 {len(items)} 行数据\n")

# 检查前3行的所有字段
for i in range(min(3, len(items))):
    fields = items[i].get("fields", {})
    print(f"行 {i}:")
    for k in sorted(fields.keys()):
        v = fields[k]
        if v is not None and v != "":
            print(f"  {k}: {v}")
    print()

# 检查段2（男服+女服）
print("=" * 80)
print("段2（男服+女服）数据结构")
print("=" * 80)

# 找到第二个"大类别"行
sections = []
for i, item in enumerate(items):
    fields = item.get("fields", {})
    category = fields.get("大类别", "")
    if category == "大类别":
        sections.append(i)

if len(sections) >= 2:
    print(f"段2从行 {sections[1]} 开始\n")
    # 显示段2的前几行
    for i in range(sections[1], min(sections[1] + 5, len(items))):
        fields = items[i].get("fields", {})
        category = fields.get("大类别", "")
        print(f"行 {i}: 大类别='{category}'")
        for k in sorted(fields.keys()):
            v = fields[k]
            if v is not None and v != "":
                print(f"  {k}: {v}")
        print()
