#!/usr/bin/env python3
"""检查KPI细分区段的完整结构"""
import os, sys
sys.path.insert(0, '/workspace/feishu')
from feishu_build import rows, get, _num

print("=" * 80)
print("KPI细分区段结构分析")
print("=" * 80)

# 查找所有"周合计"行
weekly_rows = []
for i, row in enumerate(rows):
    city = get(row, "奥莱店华南区城市") or ""
    if city == "周合计":
        weekly_rows.append((i, row))
        print(f"\n行 {i}: 周合计")
        for k, v in sorted(row.items()):
            if v is not None and v != "" and k != "奥莱店华南区城市":
                print(f"  {k}: {v}")

# 查找环比行附近的行
print("\n\n" + "=" * 80)
print("环比行附近的结构")
print("=" * 80)
for i in range(20, 30):
    if i < len(rows):
        row = rows[i]
        city = get(row, "奥莱店华南区城市") or ""
        print(f"\n行 {i}: {city}")
        for k, v in sorted(row.items()):
            if v is not None and v != "" and k != "奥莱店华南区城市":
                print(f"  {k}: {v}")
