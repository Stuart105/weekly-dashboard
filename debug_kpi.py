#!/usr/bin/env python3
"""调试KPI区段结构"""
import os, sys
sys.path.insert(0, '/workspace/feishu')
from feishu_build import rows, get

print("=" * 80)
print("KPI区段完整结构")
print("=" * 80)

in_kpi = False
for i, row in enumerate(rows):
    city = get(row, "奥莱店华南区城市") or ""
    if city == "周合计":
        in_kpi = True
        print(f"行 {i}: 周合计 (KPI区段开始)")
        continue
    if in_kpi:
        if city == "日别":
            print(f"行 {i}: 日别 (KPI区段结束)")
            break
        if city:
            # Print all non-empty fields
            fields = {k: v for k, v in row.items() if v is not None and v != ""}
            print(f"\n行 {i}: '{city}'")
            for k, v in sorted(fields.items()):
                print(f"  {k}: {v}")
