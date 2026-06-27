#!/usr/bin/env python3
"""调试日别区段结构"""
import os, sys
sys.path.insert(0, '/workspace/feishu')
from feishu_build import rows, get

print("=" * 80)
print("日别区段完整结构")
print("=" * 80)

in_daily = False
for i, row in enumerate(rows):
    city = get(row, "奥莱店华南区城市") or ""
    if city == "日别":
        in_daily = True
        print(f"行 {i}: 日别 (区段开始)")
        continue
    if in_daily:
        if city == "大类别":
            print(f"行 {i}: 大类别 (日别区段结束)")
            break
        if city:
            # Print all non-empty fields
            fields = {k: v for k, v in row.items() if v is not None and v != ""}
            print(f"\n行 {i}: '{city}'")
            for k, v in sorted(fields.items()):
                print(f"  {k}: {v}")
