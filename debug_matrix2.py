#!/usr/bin/env python3
"""检查飞书表中KPI区段的所有字段"""
import os, sys
sys.path.insert(0, '/workspace/feishu')
from feishu_build import rows, get, _num

print("=" * 80)
print("KPI汇总区段（周合计）所有字段")
print("=" * 80)

# 找到第一个周合计行
for i, row in enumerate(rows):
    city = get(row, "奥莱店华南区城市") or ""
    if city == "周合计":
        print(f"行 {i}: 周合计")
        print("\n所有字段:")
        for k in sorted(row.keys()):
            v = row[k]
            if v is not None and v != "":
                print(f"  {k}: {v}")
        break

print("\n" + "=" * 80)
print("KPI细分区段（第二个周合计）所有字段")
print("=" * 80)

# 找到第二个周合计行
count = 0
for i, row in enumerate(rows):
    city = get(row, "奥莱店华南区城市") or ""
    if city == "周合计":
        count += 1
        if count == 2:
            print(f"行 {i}: 周合计")
            print("\n所有字段:")
            for k in sorted(row.keys()):
                v = row[k]
                if v is not None and v != "":
                    print(f"  {k}: {v}")
            break

print("\n" + "=" * 80)
print("日别区段 - 连带率行")
print("=" * 80)

for i, row in enumerate(rows):
    city = get(row, "奥莱店华南区城市") or ""
    if city == "连带率":
        print(f"行 {i}: 连带率")
        print("\n所有字段:")
        for k in sorted(row.keys()):
            v = row[k]
            if v is not None and v != "":
                print(f"  {k}: {v}")
        break

print("\n" + "=" * 80)
print("日别区段 - 客流数量行")
print("=" * 80)

for i, row in enumerate(rows):
    city = get(row, "奥莱店华南区城市") or ""
    if city == "客流数量":
        print(f"行 {i}: 客流数量")
        print("\n所有字段:")
        for k in sorted(row.keys()):
            v = row[k]
            if v is not None and v != "":
                print(f"  {k}: {v}")
        break
