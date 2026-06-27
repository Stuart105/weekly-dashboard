#!/usr/bin/env python3
"""检查新品季节数据表"""
import os, sys, requests
sys.path.insert(0, '/workspace/feishu')
from feishu_build import BASE_ID, TOKEN

SEAS_TABLE = "tblhxVtkScorpwxQ"

print("=" * 80)
print("获取季节数据表")
print("=" * 80)

r = requests.get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{SEAS_TABLE}/records",
    headers={"Authorization": TOKEN},
    params={"page_size": 100},
    timeout=15
)

data = r.json()
items = data.get("data", {}).get("items", [])

print(f"共获取 {len(items)} 行数据")

# 显示前30行的结构
print("\n前30行数据结构：")
for i, item in enumerate(items[:30]):
    fields = item.get("fields", {})
    category = fields.get("大类别", "")
    print(f"行 {i}: 大类别='{category}'")
    if i < 5:  # 显示前5行的详细字段
        for k, v in sorted(fields.items()):
            if v is not None and v != "":
                print(f"  {k}: {v}")

# 查找"大类别"分隔行
print("\n" + "=" * 80)
print("查找数据段分隔")
print("=" * 80)

sections = []
for i, item in enumerate(items):
    fields = item.get("fields", {})
    category = fields.get("大类别", "")
    if category == "大类别":
        sections.append(i)
        print(f"段分隔在行 {i}")

print(f"\n共找到 {len(sections)} 个段分隔")

# 检查每个段的数据
if len(sections) >= 1:
    print("\n" + "=" * 80)
    print("段1: 总服+总鞋数据")
    print("=" * 80)
    for i in range(sections[0] + 1, min(sections[0] + 10, len(items))):
        fields = items[i].get("fields", {})
        category = fields.get("大类别", "")
        print(f"行 {i}: {category}")
        # 检查服/鞋列
        fu_val = fields.get("服")
        xie_val = fields.get("鞋")
        if fu_val or xie_val:
            print(f"  服={fu_val}, 鞋={xie_val}")

if len(sections) >= 2:
    print("\n" + "=" * 80)
    print("段2: 男服+女服数据")
    print("=" * 80)
    for i in range(sections[1] + 1, min(sections[1] + 10, len(items))):
        fields = items[i].get("fields", {})
        category = fields.get("大类别", "")
        print(f"行 {i}: {category}")
        fu_val = fields.get("服")
        xie_val = fields.get("鞋")
        if fu_val or xie_val:
            print(f"  服(男服)={fu_val}, 鞋(女服)={xie_val}")

if len(sections) >= 3:
    print("\n" + "=" * 80)
    print("段3: 男鞋+女鞋数据")
    print("=" * 80)
    for i in range(sections[2] + 1, min(sections[2] + 10, len(items))):
        fields = items[i].get("fields", {})
        category = fields.get("大类别", "")
        print(f"行 {i}: {category}")
        fu_val = fields.get("服")
        xie_val = fields.get("鞋")
        if fu_val or xie_val:
            print(f"  服(男鞋)={fu_val}, 鞋(女鞋)={xie_val}")
