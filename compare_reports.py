#!/usr/bin/env python3
"""
对比 W24 和 W25 周报的结构差异，找出切换数据出错的根因
"""
import json, os
from pathlib import Path

BASE = Path('/workspace')

# 加载两份数据
with open(BASE / 'W24_raw.json') as f:
    w24 = json.load(f)
with open(BASE / 'W25_raw.json') as f:
    w25 = json.load(f)

print("=" * 100)
print("📊 W24 vs W25 周报结构对比分析")
print("=" * 100)

# 1. 对比 header 行（行1）
print("\n" + "=" * 80)
print("1. 列头对比 (row 1)")
print("=" * 80)
w24_header = w24[1] if len(w24) > 1 else []
w25_header = w25[1] if len(w25) > 1 else []

# 检查列数差异
max_cols = max(len(w24_header), len(w25_header))
print(f"W24 列数: {len(w24_header)}, W25 列数: {len(w25_header)}")

# 找出不同的列
for i in range(max_cols):
    v24 = w24_header[i] if i < len(w24_header) else None
    v25 = w25_header[i] if i < len(w25_header) else None
    if v24 != v25:
        print(f"  列{i}: W24='{v24}' → W25='{v25}'")

# 2. 对比行标签（列0的值）
print("\n" + "=" * 80)
print("2. 行标签对比 (col 0)")
print("=" * 80)

def get_labels(data):
    """获取所有非空行标签（列0的值）"""
    labels = []
    for i, row in enumerate(data):
        if row and row[0]:
            labels.append((i, str(row[0]).replace('\n', '\\n')))
    return labels

w24_labels = get_labels(w24)
w25_labels = get_labels(w25)

print(f"W24 标签行数: {len(w24_labels)}, W25 标签行数: {len(w25_labels)}")

# 逐行对比
max_label_rows = max(len(w24_labels), len(w25_labels))
mismatches = []
for i in range(max_label_rows):
    ri24, l24 = w24_labels[i] if i < len(w24_labels) else (-1, 'MISSING')
    ri25, l25 = w25_labels[i] if i < len(w25_labels) else (-1, 'MISSING')
    if l24 != l25:
        mismatches.append((i, ri24, l24, ri25, l25))
    elif ri24 != ri25:
        mismatches.append((i, ri24, l24, ri25, l25))

if mismatches:
    print(f"差异行数: {len(mismatches)}")
    for i, ri24, l24, ri25, l25 in mismatches[:20]:
        print(f"  序号{i}: W24[行{ri24}]='{l24}' vs W25[行{ri25}]='{l25}'")
else:
    print("✅ 所有行标签完全一致！")

# 3. 对比关键区段的数据
print("\n" + "=" * 80)
print("3. 关键区段数据对比")
print("=" * 80)

# 找出特定标签的行号
def find_row(data, label):
    for i, row in enumerate(data):
        if row and row[0] and str(row[0]).strip() == label:
            return i, row
    return -1, None

# 对比 KPI 行
print("\n--- KPI 周合计行 ---")
for label in ['周合计']:
    ri24, r24 = find_row(w24, label)
    ri25, r25 = find_row(w25, label)
    if ri24 >= 0 and ri25 >= 0:
        print(f"  W24[行{ri24}]: {[(i,v) for i,v in enumerate(r24[:20]) if v is not None]}")
        print(f"  W25[行{ri25}]: {[(i,v) for i,v in enumerate(r25[:20]) if v is not None]}")

# 对比第二个周合计行
print("\n--- KPI 细分 周合计行 ---")
# 找到第二个周合计
w24_zhou2 = [(i, row) for i, row in enumerate(w24) if row and row[0] and str(row[0]).strip() == '周合计']
w25_zhou2 = [(i, row) for i, row in enumerate(w25) if row and row[0] and str(row[0]).strip() == '周合计']
print(f"  W24 周合计行: {[i for i,_ in w24_zhou2]}")
print(f"  W25 周合计行: {[i for i,_ in w25_zhou2]}")
if len(w24_zhou2) >= 2:
    _, r24 = w24_zhou2[1]
    print(f"  W24 第二个周合计[行{w24_zhou2[1][0]}]: {[(i,v) for i,v in enumerate(r24[:20]) if v is not None]}")
if len(w25_zhou2) >= 2:
    _, r25 = w25_zhou2[1]
    print(f"  W25 第二个周合计[行{w25_zhou2[1][0]}]: {[(i,v) for i,v in enumerate(r25[:20]) if v is not None]}")

# 4. 对比列头结构（所有非空列）
print("\n" + "=" * 80)
print("4. 列头完整结构对比")
print("=" * 80)

def get_col_structure(row):
    """获取列头结构: {列索引: 列名}"""
    return {i: str(v).strip() for i, v in enumerate(row) if v is not None}

w24_struct = get_col_structure(w24_header)
w25_struct = get_col_structure(w25_header)

# 新增的列
new_cols = {k: v for k, v in w25_struct.items() if k not in w24_struct}
if new_cols:
    print("W25 新增列:")
    for k, v in sorted(new_cols.items()):
        print(f"  列{k}: '{v}'")

# 删除的列
removed_cols = {k: v for k, v in w24_struct.items() if k not in w25_struct}
if removed_cols:
    print("W25 删除列:")
    for k, v in sorted(removed_cols.items()):
        print(f"  列{k}: '{v}'")

# 5. 对比品类数据区段
print("\n" + "=" * 80)
print("5. 品类区段数据对比（大类别部分）")
print("=" * 80)

for label in ['大类别', '流水', '数量', '折扣', '环比', '同比', '流水占比']:
    ri24, r24 = find_row(w24, label)
    ri25, r25 = find_row(w25, label)
    if ri24 >= 0 and ri25 >= 0:
        v24 = {i: v for i, v in enumerate(r24[:40]) if v is not None}
        v25 = {i: v for i, v in enumerate(r25[:40]) if v is not None}
        if v24 != v25:
            print(f"  '{label}' 数据不同:")
            # 找出具体差异
            all_keys = set(v24.keys()) | set(v25.keys())
            for k in sorted(all_keys):
                if v24.get(k) != v25.get(k):
                    print(f"    列{k}: W24='{v24.get(k)}' vs W25='{v25.get(k)}'")

# 6. 对比日别数据
print("\n" + "=" * 80)
print("6. 日别数据对比")
print("=" * 80)

for label in ['日别', '流水目标', 'EPOS流水', 'EPOS达成率', '同比', '环比', '成交率', '客流数量', '客单价', '连带率']:
    ri24, r24 = find_row(w24, label)
    ri25, r25 = find_row(w25, label)
    if ri24 >= 0 and ri25 >= 0:
        v24 = {i: v for i, v in enumerate(r24[:40]) if v is not None}
        v25 = {i: v for i, v in enumerate(r25[:40]) if v is not None}
        if v24 != v25:
            print(f"  '{label}':")
            all_keys = set(v24.keys()) | set(v25.keys())
            for k in sorted(all_keys):
                if v24.get(k) != v25.get(k):
                    print(f"    列{k}: W24='{v24.get(k)}' vs W25='{v25.get(k)}'")

# 7. 总结
print("\n" + "=" * 80)
print("7. 结构差异总结")
print("=" * 80)
print(f"W24 总行数: {len(w24)}")
print(f"W25 总行数: {len(w25)}")
print(f"W24 列数: {len(w24_header)}")
print(f"W25 列数: {len(w25_header)}")

# 检查是否所有行标签相同
if not mismatches:
    print("✅ 行标签结构完全一致，数据切换应该是平滑的")
else:
    print(f"⚠️ 有 {len(mismatches)} 处行标签差异")