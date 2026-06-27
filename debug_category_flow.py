#!/usr/bin/env python3
"""调试品类数据提取"""
import os, sys
sys.path.insert(0, '/workspace/feishu')

# 重新运行品类数据提取逻辑
from feishu_build import rows, get, getn, CATE_METRICS, category

print("=" * 80)
print("品类数据提取检查")
print("=" * 80)

# 检查大类别区段的原始数据
print("\n大类别区段原始数据:")
in_category = False
for i, row in enumerate(rows):
    city = get(row, "奥莱店华南区城市") or ""
    if city == "大类别":
        in_category = True
        print(f"\n行 {i}: 大类别 (开始)")
        continue
    if city in ("服装-PS中类", "鞋-系列", "器配中类"):
        if in_category:
            print(f"\n行 {i}: {city} (结束)")
            break
    if in_category and city in CATE_METRICS:
        print(f"\n行 {i}: {city}")
        for k, v in sorted(row.items()):
            if v is not None and v != "" and k != "奥莱店华南区城市":
                print(f"  {k}: {v}")

# 检查品类初始化后的值
print("\n" + "=" * 80)
print("品类初始化后的值 (器配和性别组提取后):")
for cname in ["鞋", "服", "器配", "男", "女", "童"]:
    print(f"  {cname}: flow={category[cname].get('flow', 0)}, qty={category[cname].get('qty', 0)}")

# 检查季节数据提取后的值
from feishu_build import seas, mid_agg
print("\n" + "=" * 80)
print("季节数据中的服和鞋数据:")
for key in sorted(seas.keys()):
    if '(服)' in key or '(鞋)' in key:
        print(f"  {key}: f={seas[key].get('f', 0)}")

print("\n" + "=" * 80)
print("mid_agg 数据:")
for k, v in mid_agg.items():
    print(f"  {k}: {v}")

# 手动计算品类聚合
print("\n" + "=" * 80)
print("手动计算品类聚合:")
服_total = 0
for mid_cat in ["男服", "女服"]:
    for season_key, season_data in seas.items():
        if f"({mid_cat})" in season_key:
            服_total += season_data.get("f", 0)
print(f"  服 (男服+女服): {服_total}")

鞋_total = 0
for mid_cat in ["男鞋", "女鞋"]:
    for season_key, season_data in seas.items():
        if f"({mid_cat})" in season_key:
            鞋_total += season_data.get("f", 0)
print(f"  鞋 (男鞋+女鞋): {鞋_total}")

# 检查最终的品类数据
print("\n" + "=" * 80)
print("最终的品类数据 (从 feishu_build 导入):")
from feishu_build import category as final_category
for cname in ["鞋", "服", "器配"]:
    print(f"  {cname}: flow={final_category[cname].get('flow', 0)}, qty={final_category[cname].get('qty', 0)}")
