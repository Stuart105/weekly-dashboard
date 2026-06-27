#!/usr/bin/env python3
"""调试KPI矩阵字段提取"""
import os, sys
sys.path.insert(0, '/workspace/feishu')
from feishu_build import rows, get, _num, kpi_updates, SECTION1_MAP, SECTION2_MAP, sec1_row, sec2_row

print("=" * 80)
print("KPI矩阵缺失字段检查")
print("=" * 80)

# 检查kpi_updates中的字段
fields_to_check = [
    'avg_ticket_yoy', 'avg_ticket_mom',  # 客单价同比/环比
    'attach_mom',  # 连带率环比
    'flow_mom',  # 日均客流环比
    'discount_yoy',  # 折扣率同比
]

print("\n当前kpi_updates中的字段值：")
for field in fields_to_check:
    val = kpi_updates.get(field, 'NOT FOUND')
    print(f"  {field}: {val}")

# 检查日别区客单价行的详细数据
print("\n" + "=" * 80)
print("日别区客单价行详细数据")
print("=" * 80)
for i, row in enumerate(rows):
    city = get(row, "奥莱店华南区城市") or ""
    if city == "客单价":
        print(f"行 {i}: 客单价")
        for k, v in sorted(row.items()):
            if v is not None and v != "":
                print(f"  {k}: {v}")
        break

# 检查KPI细分区段（sec2_row）的原始数据
print("\n" + "=" * 80)
print("KPI细分区段（sec2_row）原始数据")
print("=" * 80)
if sec2_row:
    for k, v in sorted(sec2_row.items()):
        if v is not None and v != "":
            print(f"  {k}: {v}")
else:
    print("sec2_row 未找到")

# 检查KPI汇总区段（sec1_row）的原始数据
print("\n" + "=" * 80)
print("KPI汇总区段（sec1_row）原始数据")
print("=" * 80)
if sec1_row:
    for k, v in sorted(sec1_row.items()):
        if v is not None and v != "":
            print(f"  {k}: {v}")
else:
    print("sec1_row 未找到")
