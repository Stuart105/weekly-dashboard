#!/usr/bin/env python3
"""
feishu_build_v2.py — 直接读取飞书电子表格，跳过 bitable 中间层

核心原理：
- 飞书 Sheet 的列顺序是固定的（由 Excel 模板决定），不会因周报切换而改变
- bitable 的字段顺序可能和 Sheet 不同，导致数据错位
- 直接用 Sheet 列索引提取数据，消除中间层错位风险

用法：
  python3 feishu_build_v2.py              # 使用 .env 中的默认配置
  python3 feishu_build_v2.py W24          # 切换到 W24 周报
  python3 feishu_build_v2.py W25          # 切换到 W25 周报
"""

import json, os, re, sys
from pathlib import Path
import requests

BASE = Path(__file__).parent.parent

# ── 配置 ──
APP_ID = os.environ.get("FEISHU_APP_ID", "cli_a931cdfb8bf89bb5")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
BASE_ID = os.environ.get("FEISHU_BASE_ID", "XJAZbw1rqaWHMnsVAJIci7ttnJd")

# 周报配置（Sheet Token → Sheet ID）
WEEK_CONFIG = {
    "W24": ("JKjNsGqhfhmhG1tbijocjHAUnMd", "0jrzud"),
    "W25": ("BReJss39ah5PfytirOfcDThansj", "0kOHQv"),
}

# 从命令行参数或环境变量获取周报选择
week_choice = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FEISHU_WEEK", "W25")
if week_choice not in WEEK_CONFIG:
    print(f"❌ 未知周报: {week_choice}，可选: {list(WEEK_CONFIG.keys())}")
    sys.exit(1)

SHEET_TOKEN, SHEET_ID = WEEK_CONFIG[week_choice]

if not APP_SECRET:
    env_file = BASE / '.env'
    if env_file.exists():
        for line in open(env_file):
            line = line.strip()
            if line.startswith("FEISHU_APP_SECRET="):
                APP_SECRET = line.split("=", 1)[1].strip().strip('"').strip("'")

if not APP_SECRET:
    print("❌ FEISHU_APP_SECRET 未配置"); sys.exit(1)

# ── 认证 ──
def auth():
    r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
    return "Bearer " + r.json()["tenant_access_token"]

TOKEN = auth()

# ── 工具函数 ──
def _num(s):
    if s is None: return None
    if isinstance(s, (int, float)): return float(s)
    s = str(s).replace(",", "").replace("¥", "").replace(" ", "").strip()
    if s in ("/", "-", ""): return None
    try:
        if s.endswith("%"): return float(s[:-1])
        return float(s)
    except ValueError: return None

# ── 1. 从 Sheet 读取原始数据 ──
print(f"📡 正在从飞书电子表格获取 {week_choice} 数据...")
print(f"   Sheet: {SHEET_TOKEN} / {SHEET_ID}")

r = requests.get(
    f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SHEET_TOKEN}/values/{SHEET_ID}",
    headers={"Authorization": TOKEN},
    params={"range": "A1:AN250"},
    timeout=15)
data = r.json()
raw = data.get("data", {}).get("valueRange", {}).get("values", [])
print(f"   读取 {len(raw)} 行 x {len(raw[0]) if raw else 0} 列")

# ── 2. 构建行标签索引（col0 的值 → 行号） ──
row_labels = {}
for i, row in enumerate(raw):
    if row and row[0]:
        label = str(row[0]).strip().replace("\n", "")
        if label not in row_labels:
            row_labels[label] = []
        row_labels[label].append(i)

def find_row(label, nth=1):
    indices = row_labels.get(label, [])
    if len(indices) >= nth:
        return indices[nth - 1], raw[indices[nth - 1]]
    return -1, None

# ── 3. 提取周期 ──
week_period, week_display = "W??", ""
for row in raw:
    for v in row:
        if isinstance(v, str) and "W" in v and "周累计" in v:
            m = re.search(r'(W\d+)', v)
            week_period = m.group(1) if m else week_period
            week_display = v.replace(f"{week_period}周累计：", "").replace("至", "→")
            break

print(f"   周期: {week_period} | {week_display}")

# ── 4. KPI 数据提取 ──
# 列索引映射（基于 Sheet 实际列位置，跨周报稳定）
# 参考: Row 1(列头) + Row 3-5(分组头) 确定列含义

print("📊 提取 KPI 数据...")

kpi = {"period": week_period, "week_range": week_display}

# ── 4a. 总体KPI（第一个"周合计"行，row 6）──
sec1_ri, sec1 = find_row("周合计", 1)
if sec1_ri >= 0:
    # 列映射: 通过对比 bitable 字段名和 Sheet 列值验证
    # col3="店铺数量", col4="成交率当期", col5="成交率同比", col6="成交率环比"
    # col7="日均客流量", col9="日均客流量同比", col11="日均客流量环比"
    # col13="流水目标", col16="流水", col19="流水达成率"
    # col21="流水同比(SSSG)", col23="同店同比", col25="同店同比(剔团购)", col27="流水环比"
    # col32="O2O流水", col34="O2O占比", col35="O2O环比", col36="PAD流水", col38="官网O2O流水"
    sec1_map = {
        13: "target",       # 流水目标
        16: "actual",       # 流水
        19: "achieve",      # 流水达成率
        21: "sssg",         # SSSG (流水同比)
        23: "yoy",          # 同店同比
        25: "sssg_adj",     # 同店同比(剔除团购)
        27: "mom",          # 流水环比
        32: "o2o",          # O2O流水
        34: "o2o_pct",      # O2O占比
        35: "o2o_mom",      # O2O环比
        36: "pad",          # PAD流水
        38: "o2o_online",   # 官网O2O流水
        7:  "daily_flow",   # 日均客流量
        4:  "conv_rate",    # 成交率
        5:  "conv_yoy",     # 成交率同比
        6:  "conv_mom",     # 成交率环比
        9:  "flow_yoy",     # 日均客流量同比
    }
    # Sheet 存小数（如 0.738），前端期望百分比（如 73.8）
    SEC1_PCT_KEYS = {"achieve", "sssg", "yoy", "sssg_adj", "mom",
                     "o2o_pct", "o2o_mom", "conv_rate", "conv_yoy", "conv_mom", "flow_yoy"}
    for col_idx, dkey in sec1_map.items():
        if col_idx < len(sec1):
            v = _num(sec1[col_idx])
            if v is not None:
                if dkey in SEC1_PCT_KEYS:
                    v = v * 100
                kpi[dkey] = v

# ── 4b. KPI细分（第二个"周合计"行，row 14，动态解析表头）──
# W24和W25的sec2列结构不同：W24 col21=客单量, W25 col21=交易次数
# 但折扣率始终在 col 27-37 区域
sec2_ri, sec2 = find_row("周合计", 2)
if sec2_ri >= 0:
    # 读取表头行: row 12 (子节标签), row 13 (当期/同比/环比)
    sec2_header = raw[sec2_ri - 2] if sec2_ri >= 2 else []  # row 12
    sec2_sub = raw[sec2_ri - 1] if sec2_ri >= 1 else []      # row 13

    # 子节固定起始列: col 3,9,15,21,27,33
    # 每个子节占 3 列 (当期/同比/环比)，间隔 2 列
    SEC2_SECTIONS = {
        3:  ("unit_price", "unit_yoy", "unit_mom"),           # 件单价
        9:  ("avg_ticket_sec2", "avg_ticket_yoy", "avg_ticket_mom"),  # 客单价
        15: ("attach_rate", "attach_yoy", "attach_mom"),      # 连带率
        21: ("tkt_cnt", "tkt_c_yoy", "tkt_c_mom"),            # 客单量/交易次数
        27: ("discount", "discount_yoy", "discount_mom"),     # 折扣率
        33: ("disc_adj", "disc_adj_yoy", "disc_adj_mom"),     # 折扣率(剔团购)
    }
    DISC_PCT_KEYS = {"discount", "disc_adj", "discount_yoy", "discount_mom",
                     "disc_adj_yoy", "disc_adj_mom"}
    # 同比/环比字段：Sheet 存小数，前端期望百分比
    SEC2_YOY_MOM_KEYS = {"unit_yoy", "unit_mom", "avg_ticket_yoy", "avg_ticket_mom",
                         "attach_yoy", "attach_mom", "tkt_c_yoy", "tkt_c_mom"}
    for start_col, (key0, key1, key2) in SEC2_SECTIONS.items():
        for offset, key in enumerate([key0, key1, key2]):
            col_idx = start_col + offset * 2
            if col_idx < len(sec2):
                v = _num(sec2[col_idx])
                if v is not None:
                    if key in DISC_PCT_KEYS or key in SEC2_YOY_MOM_KEYS:
                        v = v * 100
                    kpi[key] = v

# 客单价：从日别区"客单价"行的"周报（单位：元）"列获取
# 周报（单位：元）列在 col 17
ri_kj, row_kj = find_row("客单价", 1)
if ri_kj >= 0 and len(row_kj) > 17:
    v = _num(row_kj[17])
    if v: kpi["avg_ticket"] = v

# 鞋流水占比（从品类数据中获取）
# 先放在这里，后面品类数据提取后会覆盖

print(f"   KPI字段: {len(kpi)} 个")

# ── 5. 日别数据 ──
print("📊 提取日别数据...")

# 日别区段: "日别"行 → 下一个"大类别"行
daily_start = row_labels.get("日别", [None])[0]
daily_end = row_labels.get("大类别", [None])[0]

# 星期列映射（Sheet 列索引 → 星期名）
DAY_COLS = {3: "周一", 5: "周二", 7: "周三", 9: "周四", 11: "周五", 13: "周六", 15: "周日"}

daily = []
if daily_start and daily_end:
    # 收集日别区段内的指标行
    daily_metrics = {}
    for i in range(daily_start + 1, daily_end):
        row = raw[i]
        if row and row[0]:
            label = str(row[0]).strip().replace("\n", "")
            if label in ["流水目标", "EPOS流水", "EPOS达成率", "同比", "环比",
                         "成交率", "客流数量", "客单价", "连带率", "同店同比(剔除团购)"]:
                daily_metrics[label] = row

    for col_idx, day_name in DAY_COLS.items():
        entry = {"n": day_name}
        if "流水目标" in daily_metrics:
            entry["t"] = _num(daily_metrics["流水目标"][col_idx]) if col_idx < len(daily_metrics["流水目标"]) else 0 or 0
        if "EPOS流水" in daily_metrics:
            entry["f"] = _num(daily_metrics["EPOS流水"][col_idx]) if col_idx < len(daily_metrics["EPOS流水"]) else 0 or 0
        if "EPOS达成率" in daily_metrics:
            v = _num(daily_metrics["EPOS达成率"][col_idx]) if col_idx < len(daily_metrics["EPOS达成率"]) else 0
            entry["a"] = (v or 0) * 100  # Sheet 存小数，前端期望百分比
        if "同比" in daily_metrics:
            v = _num(daily_metrics["同比"][col_idx]) if col_idx < len(daily_metrics["同比"]) else 0
            entry["y"] = (v or 0) * 100
        if "成交率" in daily_metrics:
            v = _num(daily_metrics["成交率"][col_idx]) if col_idx < len(daily_metrics["成交率"]) else 0
            entry["c"] = (v or 0) * 100
        if "客流数量" in daily_metrics:
            entry["v"] = _num(daily_metrics["客流数量"][col_idx]) if col_idx < len(daily_metrics["客流数量"]) else 0 or 0
        if "客单价" in daily_metrics:
            entry["tk"] = _num(daily_metrics["客单价"][col_idx]) if col_idx < len(daily_metrics["客单价"]) else 0 or 0
        if "连带率" in daily_metrics:
            entry["at"] = _num(daily_metrics["连带率"][col_idx]) if col_idx < len(daily_metrics["连带率"]) else 0 or 0
        daily.append(entry)

print(f"   日别: {len(daily)} 天")

# ── 6. 品类数据 ──
print("📊 提取品类数据...")

# 品类区段: "大类别"行 → "服装-系列"/"服装-PS中类"/"鞋-系列"行
cate_start = row_labels.get("大类别", [None])[0]
cate_end = None
for end_label in ["服装-系列", "服装-PS中类", "鞋-系列"]:
    if end_label in row_labels:
        cate_end = row_labels[end_label][0]
        break

# 品类列映射: 列索引 → 品类名
# 基于 Sheet 行32 的品类区段头: 男(3), 女(5), 童(7), 鞋(13), 服(15), 器配(17)
CATE_COLS = {3: "男", 5: "女", 7: "童", 13: "鞋", 15: "服", 17: "器配"}

# 品类指标行名 → DATA字段名
CATE_METRICS = {
    "流水": "flow", "数量": "qty", "折扣": "disc",
    "流水占比": "f_share", "同比": "yoy", "环比": "mom",
    "SKU(个数)": "sku_s", "SKU动销率": "sku_u",
    "库存数量": "s_qty", "库存占比": "s_q_share",
}

category = {}
if cate_start and cate_end:
    for i in range(cate_start + 1, cate_end):
        row = raw[i]
        if row and row[0]:
            label = str(row[0]).strip().replace("\n", "")
            if label in CATE_METRICS:
                dkey = CATE_METRICS[label]
                for col_idx, cname in CATE_COLS.items():
                    if col_idx < len(row):
                        v = _num(row[col_idx])
                        if v is not None:
                            # Sheet 存小数（如 0.427），前端期望百分比（如 42.7）
                            if dkey in ("disc", "f_share", "s_q_share", "sku_u", "yoy", "mom"):
                                v = v * 100
                            category.setdefault(cname, {})[dkey] = v

# 补充元数据
for cname in ["鞋", "服", "器配"]:
    if cname not in category: category[cname] = {}
    category[cname]["group"] = "product"
for cname in ["男", "女", "童"]:
    if cname not in category: category[cname] = {}
    category[cname]["group"] = "gender"

# 计算 match_lbl
prod_cats = ["鞋", "服", "器配"]
total_sq = sum(category.get(c, {}).get("s_qty", 0) for c in prod_cats)
for cname in prod_cats:
    cd = category.get(cname, {})
    sqs = cd.get("s_q_share", 0)
    if not sqs and total_sq > 0 and cd.get("s_qty", 0) > 0:
        sqs = cd["s_qty"] / total_sq * 100
        cd["s_q_share"] = sqs
    fs = cd.get("f_share", 0)
    cd["gap"] = fs - sqs
    if abs(fs - sqs) <= 5:
        cd["match_lbl"] = "匹配"
    elif fs > sqs:
        cd["match_lbl"] = f"销>库+{fs - sqs:.1f}pp"
    else:
        cd["match_lbl"] = f"库>销{sqs - fs:.1f}pp"

for cname in ["男", "女", "童"]:
    if cname in category:
        category[cname]["match_lbl"] = "（匹配分析仅产品维度）"

# 鞋流水占比
if "鞋" in category and category["鞋"].get("f_share"):
    kpi["shoe_share"] = category["鞋"]["f_share"]

print(f"   品类: {len(category)} 类")

# ── 7. 子品类 ──
print("📊 提取子品类...")

sub_ps = []
ACC_NAMES = {"包类", "袜类", "帽类", "内裤类", "球", "其他中类"}

for sec_start in ["服装-PS中类", "器配中类"]:
    if sec_start not in row_labels:
        continue
    start_idx = row_labels[sec_start][0]
    # 找到下一个"合计"行
    end_idx = None
    for i in range(start_idx + 1, len(raw)):
        row = raw[i]
        if row and row[0] and str(row[0]).strip() == "合计":
            end_idx = i
            break
    if not end_idx:
        continue

    for i in range(start_idx + 1, end_idx):
        row = raw[i]
        if row and row[0]:
            name = str(row[0]).strip()
            if name in (sec_start, "合计"):
                continue
            # 子品类列: col7=流水, col13=占比, col17=同比, col21=环比
            # Sheet存小数（如 0.0213），前端期望百分比（如 2.13）
            # 注意: 同比(5.71) 已是百分比，环比(0.374) 是小数需 *100
            flow_val = _num(row[7]) if len(row) > 7 else 0
            share_val = (_num(row[13]) or 0) * 100 if len(row) > 13 else 0
            yoy_val = _num(row[17]) if len(row) > 17 else 0  # 已是百分比
            mom_val = (_num(row[21]) or 0) * 100 if len(row) > 21 else 0  # 小数需 *100
            sub_ps.append({
                "n": name, "f": flow_val or 0, "d": share_val or 0,
                "q": 0, "isAcc": name in ACC_NAMES,
                "yoy": yoy_val or 0, "mom": mom_val or 0
            })

print(f"   子品类: {len(sub_ps)} 个")

# ── 8. 鞋系列 ──
print("📊 提取鞋系列...")

shoes = []
if "鞋-系列" in row_labels:
    start_idx = row_labels["鞋-系列"][0]
    end_idx = None
    for i in range(start_idx + 1, len(raw)):
        row = raw[i]
        if row and row[0] and str(row[0]).strip() == "合计":
            end_idx = i
            break
    if end_idx:
        for i in range(start_idx + 1, end_idx):
            row = raw[i]
            if row and row[0]:
                name = str(row[0]).strip()
                if name in ("滑板系列", "极限运动", "健身"):
                    continue
                flow_val = _num(row[7]) if len(row) > 7 else 0    # col 7 = 流水
                qty_val = _num(row[3]) if len(row) > 3 else 0     # col 3 = 数量
                # Sheet存小数（如 0.426），前端期望百分比（如 42.6）
                disc_val = (_num(row[9]) or 0) * 100 if len(row) > 9 else 0
                if name and flow_val:
                    shoes.append({"n": name, "f": flow_val, "q": int(qty_val) if qty_val else 0, "d": disc_val})

print(f"   鞋系列: {len(shoes)} 个")

# ── 9. TOP商品 ──
print("📊 提取TOP商品...")

top = {}
for label in ["TOP10", "TOP20", "TOP40", "TOP60", "TOP100"]:
    ri, row = find_row(label, 1)
    if ri >= 0:
        top[label] = {}
        # 前端: "4"=服, "6"=鞋, "8"=服无可补断码率, "10"=鞋无可补断码率
        # Sheet: col17=服销量占比, col3=鞋销量占比, col23=服无可补断码率, col9=鞋无可补断码率
        # Sheet存小数（如 0.137），前端期望百分比（如 13.7）
        for sub_key, col_idx in [("4", 17), ("6", 3), ("8", 23), ("10", 9)]:
            if col_idx < len(row):
                v = _num(row[col_idx])
                if v is not None:
                    top[label][sub_key] = v * 100

print(f"   TOP商品: {len(top)} 组")

# ── 10. 季节数据（从 bitable 季节表读取，因为季节表结构不同） ──
print("📊 提取季节数据...")

SEAS_TABLE = "tblhxVtkScorpwxQ"
SEC1_COLS = {
    "服": "2025Q4及以前(服)", "字段 4": "2026Q1(服)", "字段 6": "2026Q2(服)",
    "字段 8": "2026Q3+(服)", "字段 11": "26年常青(服)",
    "鞋": "2025Q4及以前(鞋)", "字段 15": "2026Q1(鞋)", "字段 17": "2026Q2(鞋)",
    "字段 19": "2026Q3+(鞋)", "字段 22": "26年常青(鞋)",
}
SEC2_COLS_MALE = {
    "服": "2025Q4及以前(男服)", "字段 4": "2026Q1(男服)", "字段 6": "2026Q2(男服)",
    "字段 8": "2026Q3+(男服)", "字段 11": "26年常青(男服)",
}
SEC2_COLS_FEMALE = {
    "鞋": "2025Q4及以前(女服)", "字段 15": "2026Q1(女服)", "字段 17": "2026Q2(女服)",
    "字段 19": "2026Q3+(女服)", "字段 22": "26年常青(女服)",
}
SEC3_COLS_MALE = {
    "服": "2025Q4及以前(男鞋)", "字段 4": "2026Q1(男鞋)", "字段 6": "2026Q2(男鞋)",
    "字段 8": "2026Q3+(男鞋)", "字段 11": "26年常青(男鞋)",
}
SEC3_COLS_FEMALE = {
    "鞋": "2025Q4及以前(女鞋)", "字段 15": "2026Q1(女鞋)", "字段 17": "2026Q2(女鞋)",
    "字段 19": "2026Q3+(女鞋)", "字段 22": "26年常青(女鞋)",
}

SEAS_METRICS = {
    "流水": "f", "数量": "q", "折扣": "d",
    "流水占比": "fs", "环比": "mom", "SKU(个数)": "sku",
    "库存数量": "stock_qty", "库存金额": "stock_amt",
    "吊牌价": "tag_price", "同比": "yoy",
}

r2 = requests.get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{SEAS_TABLE}/records",
    headers={"Authorization": TOKEN}, params={"page_size": 100}, timeout=15)
seas_items = r2.json().get("data", {}).get("items", [])
seas_rows = [item.get("fields", {}) for item in seas_items]

seas = {}
mid_agg = {"男服": {}, "女服": {}, "男鞋": {}, "女鞋": {}}

# 段1: 总服+总鞋
for row in seas_rows:
    mn = (row.get("大类别") or "").replace("\n", "")
    if mn == "大类别": break
    if mn in SEAS_METRICS:
        dkey = SEAS_METRICS[mn]
        for fid, sk in SEC1_COLS.items():
            v = _num(row.get(fid))
            if v is not None:
                seas.setdefault(sk, {})[dkey] = v

# 段2: 男服+女服
sec2_start = next((i for i, r in enumerate(seas_rows) if r.get("大类别", "") == "大类别" and i > 0), None)
if sec2_start:
    for row in seas_rows[sec2_start + 3:]:
        mn = (row.get("大类别") or "").replace("\n", "")
        if mn == "大类别": break
        if mn in SEAS_METRICS:
            dkey = SEAS_METRICS[mn]
            for fid, sk in SEC2_COLS_MALE.items():
                v = _num(row.get(fid))
                if v is not None:
                    seas.setdefault(sk, {})[dkey] = v
                    mid_agg.setdefault("男服", {}).setdefault(dkey, 0)
                    mid_agg["男服"][dkey] += v
            for fid, sk in SEC2_COLS_FEMALE.items():
                v = _num(row.get(fid))
                if v is not None:
                    seas.setdefault(sk, {})[dkey] = v
                    mid_agg.setdefault("女服", {}).setdefault(dkey, 0)
                    mid_agg["女服"][dkey] += v

# 段3: 男鞋+女鞋
sec3_start = next((i for i, r in enumerate(seas_rows) if r.get("大类别", "") == "大类别" and i > sec2_start), None) if sec2_start else None
if sec3_start:
    for row in seas_rows[sec3_start + 3:]:
        mn = (row.get("大类别") or "").replace("\n", "")
        if mn == "大类别": break
        if mn in SEAS_METRICS:
            dkey = SEAS_METRICS[mn]
            for fid, sk in SEC3_COLS_MALE.items():
                v = _num(row.get(fid))
                if v is not None:
                    seas.setdefault(sk, {})[dkey] = v
                    mid_agg.setdefault("男鞋", {}).setdefault(dkey, 0)
                    mid_agg["男鞋"][dkey] += v
            for fid, sk in SEC3_COLS_FEMALE.items():
                v = _num(row.get(fid))
                if v is not None:
                    seas.setdefault(sk, {})[dkey] = v
                    mid_agg.setdefault("女鞋", {}).setdefault(dkey, 0)
                    mid_agg["女鞋"][dkey] += v

# SKU动销率（硬编码行索引，因为季节表结构固定）
if len(seas_rows) > 17:
    sku_row = seas_rows[17]
    for fid, sk in [("服", "25Q4旧品(服)"), ("鞋", "25Q4旧品(鞋)")]:
        v = _num(sku_row.get(fid))
        if v is not None:
            seas.setdefault(sk, {})["su"] = v
if len(seas_rows) > 44:
    sku_row = seas_rows[44]
    for fid, sk in [("服", "25Q4旧品(男服)"), ("鞋", "25Q4旧品(女服)")]:
        v = _num(sku_row.get(fid))
        if v is not None:
            seas.setdefault(sk, {})["su"] = v

print(f"   季节: {len(seas)} 季, 中类汇总: {len(mid_agg)} 组")

# ── 11. 品类聚合（从季节中类数据计算服/鞋的 flow/qty/sku/stock_qty）──
# 注意：不覆盖 sheet 已提取的 disc 值（bitable 季节表字段映射不可靠）
for mid_cat, parent_cat in [("男服", "服"), ("女服", "服"), ("男鞋", "鞋"), ("女鞋", "鞋")]:
    for season_key, season_data in seas.items():
        if f"({mid_cat})" in season_key:
            for dkey in ["f", "q", "sku", "stock_qty"]:
                v = season_data.get(dkey, 0)
                if v:
                    category.setdefault(parent_cat, {}).setdefault(dkey, 0)
                    category[parent_cat][dkey] += v

print(f"   品类聚合: 服={category.get('服', {}).get('flow', 0):.0f}, 鞋={category.get('鞋', {}).get('flow', 0):.0f}")

# ── 12. 生成 DATA JSON ──
all_updates = {
    "store": "奥莱店华南区城市",
    "period": week_period,
    "week_range": week_display,
    **kpi,
    "daily": daily,
    "category": category,
    "sub_ps": sub_ps,
    "shoes": shoes,
    "seas": seas,
    "mid_agg": mid_agg,
    "top": top,
}

# ── 13. 更新 HTML ──
print("\n📝 更新 HTML...")
html_path = BASE / "weekly-dashboard.html"
with open(html_path, "r") as f:
    html = f.read()

data_json = json.dumps(all_updates, ensure_ascii=False)
new_data = f"const DATA = {data_json};"
html = re.sub(r'const DATA\s*=\s*\{.*?\};', new_data, html, flags=re.DOTALL)

with open(html_path, "w") as f:
    f.write(html)

idx_path = BASE / "index.html"
if idx_path.exists():
    with open(idx_path, "r") as f:
        idx_html = f.read()
    idx_html = re.sub(r'const DATA\s*=\s*\{.*?\};', new_data, idx_html, flags=re.DOTALL)
    with open(idx_path, "w") as f:
        f.write(idx_html)

print(f"  ✅ weekly-dashboard.html")
print(f"  ✅ index.html")

print(f"\n📊 {week_choice} 周报更新完成！")
print(f"   周期: {week_period} | {week_display}")
print(f"   KPI: {len(kpi)} 字段 | daily: {len(daily)} 天 | category: {len(category)} 类")
print(f"   sub_ps: {len(sub_ps)} 个 | shoes: {len(shoes)} 个 | TOP: {len(top)} 组")
print(f"   seas: {len(seas)} 季 | mid_agg: {len(mid_agg)} 组")
print(f"\n💡 切换周报: python3 feishu/feishu_build_v2.py W24 或 W25")