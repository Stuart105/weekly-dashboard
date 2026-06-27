#!/usr/bin/env python3
"""调试品类数据提取"""
import os, sys
sys.path.insert(0, '/workspace/feishu')
from feishu_build import rows, get

print("=" * 80)
print("品类区段原始数据检查")
print("=" * 80)

# 找到品类区段
in_category = False
category_rows = []
for i, row in enumerate(rows):
    city = get(row, "奥莱店华南区城市") or ""
    if city == "大类别":
        in_category = True
        print(f"\n行 {i}: 大类别 (品类区段开始)")
        continue
    if in_category:
        if city in ("服装-PS中类", "鞋-系列", "器配中类"):
            print(f"行 {i}: {city} (品类区段结束)")
            break
        if city in ("流水", "数量", "折扣", "流水占比", "同比", "环比", "SKU(个数)", "SKU动销率", "库存数量", "库存占比"):
            category_rows.append((i, city, row))
            print(f"\n行 {i}: {city}")
            print(f"  字段 9 (鞋): {row.get('字段 9')}")
            print(f"  字段 13 (服): {row.get('字段 13')}")
            print(f"  字段 15 (器配): {row.get('字段 15')}")
            print(f"  字段 3 (男): {row.get('字段 3')}")
            print(f"  字段 4 (女): {row.get('字段 4')}")
            print(f"  字段 6 (童): {row.get('字段 6')}")

print("\n" + "=" * 80)
print("服装流水汇总")
print("=" * 80)

# 计算服装流水
cloth_flow = 0
for i, metric, row in category_rows:
    if metric == "流水":
        cloth_val = row.get('字段 13')
        print(f"服装流水 (字段13): {cloth_val}")
        if cloth_val:
            try:
                cloth_flow = float(str(cloth_val).replace(",", "").replace("¥", "").strip())
                print(f"解析后: {cloth_flow}")
            except:
                pass

print(f"\n最终服装流水: {cloth_flow}")
print(f"用户期望值: 51115")
print(f"差异: {cloth_flow - 51115}")
