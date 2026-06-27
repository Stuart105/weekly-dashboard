#!/usr/bin/env python3
"""查找缺失的KPI字段"""
import os, sys
sys.path.insert(0, '/workspace/feishu')
from feishu_build import rows, get, _num

print("=" * 80)
print("查找缺失的KPI字段")
print("=" * 80)

# 查找包含"环比"的行
print("\n包含'环比'的行:")
for i, row in enumerate(rows):
    city = get(row, "奥莱店华南区城市") or ""
    if "环比" in city:
        print(f"\n行 {i}: {city}")
        for k, v in sorted(row.items()):
            if v is not None and v != "" and k != "奥莱店华南区城市":
                print(f"  {k}: {v}")

# 查找客单价相关的行
print("\n\n" + "=" * 80)
print("客单价相关行:")
for i, row in enumerate(rows):
    city = get(row, "奥莱店华南区城市") or ""
    if "客单价" in city:
        print(f"\n行 {i}: {city}")
        for k, v in sorted(row.items()):
            if v is not None and v != "" and k != "奥莱店华南区城市":
                print(f"  {k}: {v}")

# 查找日均客流相关的行
print("\n\n" + "=" * 80)
print("日均客流相关行:")
for i, row in enumerate(rows):
    city = get(row, "奥莱店华南区城市") or ""
    if "客流" in city or "日均" in city:
        print(f"\n行 {i}: {city}")
        for k, v in sorted(row.items()):
            if v is not None and v != "" and k != "奥莱店华南区城市":
                print(f"  {k}: {v}")
