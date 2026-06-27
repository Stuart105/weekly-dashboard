#!/usr/bin/env python3
"""
深度分析 feishu_build.py 的所有硬编码假设，诊断切换周报数据出错的根因
"""
import json, os, sys, re
from pathlib import Path
import requests

BASE = Path(__file__).parent.parent

APP_ID = os.environ.get("FEISHU_APP_ID", "cli_a931cdfb8bf89bb5")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
if not APP_SECRET:
    env_file = BASE / '.env'
    if env_file.exists():
        for line in open(env_file):
            line = line.strip()
            if line.startswith("FEISHU_APP_SECRET="):
                APP_SECRET = line.split("=", 1)[1].strip().strip('"').strip("'")

def auth():
    r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
    return "Bearer " + r.json()["tenant_access_token"]

TOKEN = auth()
BASE_ID = os.environ.get("FEISHU_BASE_ID", "XJAZbw1rqaWHMnsVAJIci7ttnJd")
TABLE_ID = "tblmGijNaVv80ogT"

# ── 1. 获取表格字段列表（元数据） ──
print("=" * 80)
print("🔍 1. 表格字段元数据（检查实际字段ID vs 代码硬编码）")
print("=" * 80)
r = requests.get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{TABLE_ID}/fields",
    headers={"Authorization": TOKEN}, timeout=15)
fields = r.json().get("data", {}).get("items", [])
print(f"字段总数: {len(fields)}")

# 构建字段ID → 名称映射
field_map = {}
for f in fields:
    fid = f.get("field_id", "")
    fname = f.get("field_name", "")
    ftype = f.get("type", "")
    field_map[fid] = (fname, ftype)

# 检查代码中使用的所有字段ID是否真实存在
CODE_FIELD_IDS = set()
for mapping in [
    {"字段 9", "字段 11", "字段 13", "字段 15", "字段 16", "字段 20", "字段 25", "字段 27", "字段 28", "字段 29", "字段 31",
     "RGHW", "广州一区(奥莱店华南区)", "字段 4", "字段 6", "字段 5", "字段 18"},  # SECTION1_MAP keys
    {"字段 3", "字段 4", "字段 9", "字段 10", "字段 13", "字段 15", "字段 16", "字段 20", "字段 24", "字段 26", "字段 30", "字段 6", "字段 22", "字段 28", "RGHW"},  # SECTION2_MAP keys
    {"字段 3", "字段 4", "RGHW", "字段 6", "线下折扣店", "字段 9", "字段 10"},  # DAY_COLS
]:
    CODE_FIELD_IDS.update(mapping)

print("\n代码中使用的字段ID验证:")
for fid in sorted(CODE_FIELD_IDS):
    if fid in field_map:
        name, ftype = field_map[fid]
        print(f"  ✅ {fid} → {name} (type={ftype})")
    else:
        print(f"  ❌ {fid} → NOT FOUND in table!")

# ── 2. 获取所有行，分析区段结构 ──
print("\n" + "=" * 80)
print("🔍 2. 区段边界检测（通过文本匹配）")
print("=" * 80)

items, pt = [], None
while True:
    p = {"page_size": 200}
    if pt: p["page_token"] = pt
    r = requests.get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{TABLE_ID}/records",
        headers={"Authorization": TOKEN}, params=p, timeout=15)
    d = r.json()
    items += d["data"].get("items", [])
    if not d["data"].get("has_more"): break
    pt = d["data"].get("page_token")

rows = [item.get("fields", {}) for item in items]
print(f"总行数: {len(rows)}")

# 分析"奥莱店华南区城市"列的所有唯一值
city_col = "奥莱店华南区城市"
city_values = []
for i, row in enumerate(rows):
    v = row.get(city_col, "")
    if v:
        city_values.append((i, str(v).replace("\n", "\\n")))

print(f"\n{city_col} 列的所有非空值 (共 {len(city_values)} 个):")
for i, v in city_values:
    print(f"  行{i}: '{v}'")

# 标记关键区段边界
SECTION_MARKERS = {
    "周合计": "KPI汇总",
    "日别": "日别数据开始",
    "大类别": "品类数据开始",
    "服装-PS中类": "服装子品类开始",
    "器配中类": "器配子品类开始",
    "鞋-系列": "鞋系列开始",
    "TOP": "TOP商品开始",
    "合计": "区段结束",
}

print(f"\n区段边界检测:")
for i, v in city_values:
    marker = "→ "
    for key, label in SECTION_MARKERS.items():
        if key in v:
            marker += f"[{label}] "
    if marker != "→ ":
        print(f"  行{i}: {marker}")

# ── 3. 检查"行索引硬编码" ──
print("\n" + "=" * 80)
print("🔍 3. 行索引硬编码检查")
print("=" * 80)
print("代码中硬编码访问:")
print("  seas_rows[17] → SKU动销率(总段) 服/鞋")
print("  seas_rows[44] → SKU动销率(中段) 男/女")
print(f"  实际 seas_rows 总数: (需要从季节表获取)")

# ── 4. 检查季节表结构 ──
SEAS_TABLE = "tblhxVtkScorpwxQ"
print("\n" + "=" * 80)
print("🔍 4. 季节表结构和列映射")
print("=" * 80)

r = requests.get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{SEAS_TABLE}/fields",
    headers={"Authorization": TOKEN}, timeout=15)
seas_fields = r.json().get("data", {}).get("items", [])
print(f"季节表字段总数: {len(seas_fields)}")
for f in seas_fields:
    print(f"  {f.get('field_id'):20s} → {f.get('field_name')} (type={f.get('type')})")

# 获取季节表实际行数
r = requests.get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{SEAS_TABLE}/records",
    headers={"Authorization": TOKEN}, params={"page_size": 200}, timeout=15)
seas_items = r.json().get("data", {}).get("items", [])
print(f"\n季节表实际行数: {len(seas_items)}")

# 检查"大类别"行位置
seas_rows = [item.get("fields", {}) for item in seas_items]
print("\n季节表 '大类别' 行位置:")
for i, row in enumerate(seas_rows):
    v = row.get("大类别", "")
    if v == "大类别" or (isinstance(v, str) and "大类别" in v):
        print(f"  行{i}: '大类别'")

# ── 5. 检查周报列名变化 ──
print("\n" + "=" * 80)
print("🔍 5. 周报列名硬编码检查")
print("=" * 80)
print("代码硬编码的列名:")
print("  '奥莱店华南区城市' → 用于区段识别和行标签匹配")
print("  '周报（单位：元）' → 用于获取客单价")
print("  'RGHW' → 用于多种KPI和流水数据")
print("  '广州一区(奥莱店华南区)' → 用于成交率")
print("  '线下折扣店' → 用于周五数据")

# 检查这些列名是否在当前表中
table_columns = {f.get("field_name", ""): f.get("field_id", "") for f in fields}
for col_name in ["奥莱店华南区城市", "周报（单位：元）", "RGHW", "广州一区(奥莱店华南区)", "线下折扣店"]:
    if col_name in table_columns:
        print(f"  ✅ '{col_name}' → field_id={table_columns[col_name]}")
    else:
        print(f"  ❌ '{col_name}' → NOT FOUND in table!")

# ── 6. 总结硬编码风险 ──
print("\n" + "=" * 80)
print("🔍 6. 硬编码风险总结")
print("=" * 80)
risks = [
    ("SECTION1_MAP/SECTION2_MAP", "硬编码字段ID (如'字段 9', '字段 11')", "如果列顺序变化，数据会错位"),
    ("DAY_COLS", "硬编码星期→字段ID映射", "如果列顺序变化，日别数据错位"),
    ("区段边界检测", "通过文本匹配 '日别'/'大类别'/'周合计'", "如果飞书表格中这些标签文本变化，区段识别失败"),
    ("行索引访问", "硬编码 seas_rows[17] seas_rows[44]", "如果季节表行数变化，数据错位或崩溃"),
    ("列名硬编码", "'奥莱店华南区城市' '周报（单位：元）'", "如果列名在不同周报中不同，数据获取失败"),
    ("季节列映射", "硬编码季度名 '2025Q4' '2026Q1'等", "换年后季度名变化，季节数据全部丢失"),
    ("子品类识别", "硬编码 ACC_NAMES 集合", "如果新增配件品类，分类错误"),
    ("鞋系列过滤", "硬编码排除 '滑板系列' '极限运动' '健身'", "如果新增系列，可能被错误排除"),
]

for name, desc, risk in risks:
    print(f"  ⚠️ {name}: {desc}")
    print(f"     → 风险: {risk}")