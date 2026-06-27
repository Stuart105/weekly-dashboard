#!/usr/bin/env python3
"""
feishu_build_v2.py — 直接读取飞书电子表格，跳过 bitable 中间层

核心原理：
- 飞书 Sheet 的列顺序由 Excel 模板决定，但可能随周报版本变化
- 通过解析表头行动态定位列位置，而非硬编码列索引
- 行标签用于定位数据区段（跨周报稳定）
- 列标签用于定位数据列（从表头行动态解析）

用法：
  python3 feishu/feishu_build_v2.py              # 使用 .env 中的默认配置
  python3 feishu/feishu_build_v2.py W24          # 切换到 W24 周报
  python3 feishu/feishu_build_v2.py W25          # 切换到 W25 周报
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

def _clean(s):
    """清理标签文本"""
    if s is None: return ""
    return str(s).strip().replace("\n", "").replace(" ", "")

def parse_col_map(header_row, label_map):
    """
    动态解析表头行，构建 列索引 → key 映射。
    header_row: 表头行（list）
    label_map: {匹配关键词: 映射key}，按优先级排序
    返回: {col_index: key}
    """
    result = {}
    for col_idx, val in enumerate(header_row):
        if val is None:
            continue
        label = _clean(val)
        for pattern, key in label_map.items():
            if pattern in label:
                result[col_idx] = key
                break
    return result

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
max_cols = len(raw[0]) if raw else 0
print(f"   读取 {len(raw)} 行 x {max_cols} 列")

# ── 2. 构建行标签索引 ──
row_labels = {}
for i, row in enumerate(raw):
    if row and row[0]:
        label = _clean(row[0])
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

# ═══════════════════════════════════════════════════════════════
# 核心：动态列解析策略
# 每个数据区段都通过解析其表头行来确定列位置，而非硬编码列索引
# 这样即使 W26/W27 的列结构变化，也能自动适应
# ═══════════════════════════════════════════════════════════════

kpi = {"period": week_period, "week_range": week_display}

# ── 4a. KPI 总体（sec1：第一个"周合计"行）──
# sec1 结构稳定（Excel 模板顶部固定区域），但为防万一也做动态解析
print("📊 提取 KPI 数据...")

sec1_ri, sec1 = find_row("周合计", 1)
if sec1_ri >= 0:
    # 解析 sec1 表头 (rows 3-5) 构建列映射
    # Row 3: 分组标签 (店铺数量, 成交率, 日均客流量, 销售)
    # Row 4: 子标签 (当期, 同比, 环比, 流水目标, 流水达成率, 同店同比, ...)
    # Row 5: O2O 子标签 (流水, 占比, PAD流水, 官网O2O流水)
    row3 = raw[sec1_ri - 3] if sec1_ri >= 3 else []
    row4 = raw[sec1_ri - 2] if sec1_ri >= 2 else []
    row5 = raw[sec1_ri - 1] if sec1_ri >= 1 else []

    # 从 row4 主标签定位
    sec1_map = {}
    for ci, v in enumerate(row4):
        if v is None: continue
        lbl = _clean(v)
        if '流水目标' in lbl: sec1_map[ci] = ('target', False)
        elif '流水达成率' in lbl: sec1_map[ci] = ('achieve', True)
        elif '流水同比' in lbl: sec1_map[ci] = ('sssg', True)
        elif '同店同比' in lbl and '剔除' in lbl: sec1_map[ci] = ('sssg_adj', True)
        elif '同店同比' in lbl: sec1_map[ci] = ('yoy', True)
        elif '流水环比' in lbl: sec1_map[ci] = ('mom', True)
        elif '流水' == lbl: sec1_map[ci] = ('actual', False)
        elif '客流量' in lbl: sec1_map[ci] = ('daily_flow', False)

    # 从 row3 + row4 定位成交率
    for ci, v in enumerate(row3):
        if v is None: continue
        lbl = _clean(v)
        if '成交率' in lbl:
            # 成交率: 当期=col4, 同比=col5, 环比=col6
            sec1_map[ci] = ('conv_rate', True)
            sec1_map[ci+1] = ('conv_yoy', True)
            sec1_map[ci+2] = ('conv_mom', True)
            break

    # 从 row4 定位 客流量同比 (col 9)
    for ci, v in enumerate(row4):
        if v is None: continue
        lbl = _clean(v)
        if lbl == '同比' and ci > 7:
            # 客流量同比在 col 9
            if ci == 9:
                sec1_map[ci] = ('flow_yoy', True)

    # 从 row5 定位 O2O 相关
    for ci, v in enumerate(row5):
        if v is None: continue
        lbl = _clean(v)
        if '流水' == lbl and ci >= 32: sec1_map[ci] = ('o2o', False)
        elif 'PAD流水' in lbl: sec1_map[ci] = ('pad', False)
        elif '官网O2O流水' in lbl: sec1_map[ci] = ('o2o_online', False)

    # 从 row5 定位 O2O占比和环比
    for ci, v in enumerate(row5):
        if v is None: continue
        lbl = _clean(v)
        if '占比' == lbl and ci >= 34: sec1_map[ci] = ('o2o_pct', True)
        elif '环比' == lbl and ci >= 35: sec1_map[ci] = ('o2o_mom', True)

    SEC1_PCT_KEYS = {"achieve", "sssg", "yoy", "sssg_adj", "mom",
                     "o2o_pct", "o2o_mom", "conv_rate", "conv_yoy", "conv_mom", "flow_yoy"}
    for col_idx, (dkey, is_pct) in sec1_map.items():
        if col_idx < len(sec1):
            v = _num(sec1[col_idx])
            if v is not None:
                if is_pct:
                    v = v * 100
                kpi[dkey] = v

# ── 4b. KPI细分（sec2：第二个"周合计"行）──
# 使用固定子节起始列 (3,9,15,21,27,33)，每子节 3 列 (当期/同比/环比)
sec2_ri, sec2 = find_row("周合计", 2)
if sec2_ri >= 0:
    SEC2_SECTIONS = {
        3:  ("unit_price", "unit_yoy", "unit_mom"),
        9:  ("avg_ticket_sec2", "avg_ticket_yoy", "avg_ticket_mom"),
        15: ("attach_rate", "attach_yoy", "attach_mom"),
        21: ("tkt_cnt", "tkt_c_yoy", "tkt_c_mom"),
        27: ("discount", "discount_yoy", "discount_mom"),
        33: ("disc_adj", "disc_adj_yoy", "disc_adj_mom"),
    }
    PCT_KEYS = {"discount", "disc_adj", "discount_yoy", "discount_mom",
                "disc_adj_yoy", "disc_adj_mom",
                "unit_yoy", "unit_mom", "avg_ticket_yoy", "avg_ticket_mom",
                "attach_yoy", "attach_mom", "tkt_c_yoy", "tkt_c_mom"}
    for start_col, (k0, k1, k2) in SEC2_SECTIONS.items():
        for offset, key in enumerate([k0, k1, k2]):
            ci = start_col + offset * 2
            if ci < len(sec2):
                v = _num(sec2[ci])
                if v is not None:
                    if key in PCT_KEYS:
                        v = v * 100
                    kpi[key] = v

# 客单价：从日别区"客单价"行的"周合计"列获取
ri_kj, row_kj = find_row("客单价", 1)
if ri_kj >= 0:
    # 找"周合计"列（col 17 在日别区）
    daily_header = raw[ri_kj - 9] if ri_kj >= 9 else []  # row 19 (日别)
    week_col = 17  # 默认
    for ci, v in enumerate(daily_header):
        if v and '周合计' in _clean(v):
            week_col = ci
            break
    if week_col < len(row_kj):
        v = _num(row_kj[week_col])
        if v: kpi["avg_ticket"] = v

print(f"   KPI字段: {len(kpi)} 个")

# ── 5. 日别数据（动态解析列映射）──
print("📊 提取日别数据...")

daily_start = row_labels.get("日别", [None])[0]
daily_end = row_labels.get("大类别", [None])[0]

# 动态解析日别列的星期映射
daily = []
if daily_start is not None:
    day_header = raw[daily_start]  # Row 19: 日别 | 周一 | 周二 | ...
    DAY_COLS = {}
    for ci, v in enumerate(day_header):
        if v is None: continue
        lbl = _clean(v)
        for day_name in ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]:
            if lbl == day_name:
                DAY_COLS[ci] = day_name
                break

    # 收集指标行
    daily_metrics = {}
    for i in range(daily_start + 1, daily_end):
        row = raw[i]
        if row and row[0]:
            label = _clean(row[0])
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
            entry["a"] = (v or 0) * 100
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

print(f"   日别: {len(daily)} 天 (动态解析列: {list(DAY_COLS.keys())})")

# ── 6. 品类数据（动态解析列映射）──
print("📊 提取品类数据...")

cate_start = row_labels.get("大类别", [None])[0]
cate_end = None
for end_label in ["服装-系列", "服装-PS中类", "鞋-系列"]:
    if end_label in row_labels:
        cate_end = row_labels[end_label][0]
        break

# 动态解析品类列：从 Row 32 (品类区段第二行) 找品类名
CATE_COLS = {}
if cate_start is not None and cate_start + 1 < len(raw):
    cate_header = raw[cate_start + 1]  # Row 32
    for ci, v in enumerate(cate_header):
        if v is None: continue
        lbl = _clean(v)
        for cname in ["男", "女", "童", "鞋", "服", "器配"]:
            if cname in lbl:
                CATE_COLS[ci] = cname
                break

CATE_METRICS = {
    "流水": "flow", "数量": "qty", "折扣": "disc",
    "流水占比": "f_share", "同比": "yoy", "环比": "mom",
    "SKU(个数)": "sku_s", "SKU动销率": "sku_u",
    "库存数量": "s_qty", "库存占比": "s_q_share",
}

category = {}
if cate_start is not None and cate_end is not None:
    for i in range(cate_start + 1, cate_end):
        row = raw[i]
        if row and row[0]:
            label = _clean(row[0])
            if label in CATE_METRICS:
                dkey = CATE_METRICS[label]
                for col_idx, cname in CATE_COLS.items():
                    if col_idx < len(row):
                        v = _num(row[col_idx])
                        if v is not None:
                            if dkey in ("disc", "f_share", "s_q_share", "sku_u", "yoy", "mom"):
                                v = v * 100
                            category.setdefault(cname, {})[dkey] = v

# 补充元数据和默认值
defaults = {"qty": 0, "disc": 0, "yoy": 0, "mom": 0, "f_share": 0,
            "sku_s": 0, "sku_u": 0, "s_qty": 0, "s_q_share": 0}
for cname in ["鞋", "服", "器配"]:
    if cname not in category: category[cname] = {}
    for k, v in defaults.items():
        category[cname].setdefault(k, v)
    category[cname]["group"] = "product"
for cname in ["男", "女", "童"]:
    if cname not in category: category[cname] = {}
    for k, v in defaults.items():
        category[cname].setdefault(k, v)
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

if "鞋" in category and category["鞋"].get("f_share"):
    kpi["shoe_share"] = category["鞋"]["f_share"]

print(f"   品类: {len(category)} 类 (动态解析列: {CATE_COLS})")

# ── 7. 子品类（动态解析列映射）──
print("📊 提取子品类...")

sub_ps = []
ACC_NAMES = {"包类", "袜类", "帽类", "内裤类", "球", "其他中类"}

# 子品类列映射：从表头行 (Row 90 或 Row 113) 动态解析
# 表头结构: 数量(col3), 吊牌价(col5), 流水(col7), 折扣(col9), 占比(col13), 同比(col17), 环比(col21)
# 由于 PS中类 和 器配中类 使用相同的列结构，解析一次即可

def parse_sub_ps_cols(header_row):
    """从子品类表头行解析列映射（仅解析销售数据区，cols 3-25）"""
    col_map = {}
    for ci, v in enumerate(header_row):
        if v is None or ci > 25:  # 仅解析左侧销售数据区
            continue
        lbl = _clean(v)
        if '流水' == lbl: col_map['flow'] = ci
        elif '占比' == lbl: col_map['share'] = ci
        elif '同比' == lbl: col_map['yoy'] = ci
        elif '环比' == lbl: col_map['mom'] = ci
        elif '数量' == lbl: col_map['qty'] = ci
        elif '折扣' == lbl: col_map['disc'] = ci
    return col_map

# 尝试从服装-PS中类表头解析
sub_ps_cols = None
if "服装-PS中类" in row_labels:
    ps_start = row_labels["服装-PS中类"][0]
    if ps_start + 1 < len(raw):
        sub_ps_cols = parse_sub_ps_cols(raw[ps_start + 1])  # Row 90

if sub_ps_cols is None:
    # fallback: 硬编码
    sub_ps_cols = {'flow': 7, 'share': 13, 'yoy': 17, 'mom': 21, 'qty': 3, 'disc': 9}

for sec_start in ["服装-PS中类", "器配中类"]:
    if sec_start not in row_labels:
        continue
    start_idx = row_labels[sec_start][0]
    end_idx = None
    for i in range(start_idx + 1, len(raw)):
        row = raw[i]
        if row and row[0] and _clean(row[0]) == "合计":
            end_idx = i
            break
    if not end_idx:
        continue

    for i in range(start_idx + 1, end_idx):
        row = raw[i]
        if row and row[0]:
            name = _clean(row[0])
            if name in (sec_start, "合计"):
                continue
            flow_val = _num(row[sub_ps_cols['flow']]) if sub_ps_cols['flow'] < len(row) else 0
            share_val = (_num(row[sub_ps_cols['share']]) or 0) * 100 if sub_ps_cols['share'] < len(row) else 0
            yoy_val = _num(row[sub_ps_cols['yoy']]) if sub_ps_cols['yoy'] < len(row) else 0  # 已是百分比
            mom_val = (_num(row[sub_ps_cols['mom']]) or 0) * 100 if sub_ps_cols['mom'] < len(row) else 0
            sub_ps.append({
                "n": name, "f": flow_val or 0, "d": share_val or 0,
                "q": 0, "isAcc": name in ACC_NAMES,
                "yoy": yoy_val or 0, "mom": mom_val or 0
            })

print(f"   子品类: {len(sub_ps)} 个 (列映射: {sub_ps_cols})")

# ── 8. 鞋系列（复用子品类列映射）──
print("📊 提取鞋系列...")

shoes = []
if "鞋-系列" in row_labels:
    start_idx = row_labels["鞋-系列"][0]
    end_idx = None
    for i in range(start_idx + 1, len(raw)):
        row = raw[i]
        if row and row[0] and _clean(row[0]) == "合计":
            end_idx = i
            break
    if end_idx:
        for i in range(start_idx + 1, end_idx):
            row = raw[i]
            if row and row[0]:
                name = _clean(row[0])
                if name in ("滑板系列", "极限运动", "健身"):
                    continue
                flow_val = _num(row[sub_ps_cols['flow']]) if sub_ps_cols['flow'] < len(row) else 0
                qty_val = _num(row[sub_ps_cols['qty']]) if sub_ps_cols['qty'] < len(row) else 0
                disc_val = (_num(row[sub_ps_cols['disc']]) or 0) * 100 if sub_ps_cols['disc'] < len(row) else 0
                if name and flow_val:
                    shoes.append({"n": name, "f": flow_val, "q": int(qty_val) if qty_val else 0, "d": disc_val})

print(f"   鞋系列: {len(shoes)} 个")

# ── 9. TOP商品（动态解析列映射）──
print("📊 提取TOP商品...")

# 解析 TOP 表头 (Row 123)
top_cols = {}
if "TOP商品" in row_labels:
    top_header_idx = row_labels["TOP商品"][0]
    if top_header_idx + 1 < len(raw):
        top_header = raw[top_header_idx + 1]  # Row 123
        for ci, v in enumerate(top_header):
            if v is None: continue
            lbl = _clean(v)
            if '销量占比' in lbl:
                # 判断是鞋还是服：鞋在 col 3-15, 服在 col 17-27
                if ci <= 15:
                    top_cols['shoe_sales_share'] = ci
                else:
                    top_cols['cloth_sales_share'] = ci
            elif '无可补断码率' in lbl:
                if ci <= 15:
                    top_cols['shoe_noreplen'] = ci
                else:
                    top_cols['cloth_noreplen'] = ci

# fallback
if not top_cols:
    top_cols = {'cloth_sales_share': 17, 'shoe_sales_share': 3, 'cloth_noreplen': 23, 'shoe_noreplen': 9}

top = {}
for label in ["TOP10", "TOP20", "TOP40", "TOP60", "TOP100"]:
    ri, row = find_row(label, 1)
    if ri >= 0:
        # 前端: "4"=服, "6"=鞋, "8"=服无可补断码率, "10"=鞋无可补断码率
        mapping = [
            ("4", top_cols.get('cloth_sales_share', 17)),
            ("6", top_cols.get('shoe_sales_share', 3)),
            ("8", top_cols.get('cloth_noreplen', 23)),
            ("10", top_cols.get('shoe_noreplen', 9)),
        ]
        top[label] = {}
        for sub_key, col_idx in mapping:
            if col_idx < len(row):
                v = _num(row[col_idx])
                if v is not None:
                    top[label][sub_key] = v * 100

print(f"   TOP商品: {len(top)} 组 (列映射: {top_cols})")

# ── 10. 季节数据（从 bitable 季节表读取）──
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

# SKU动销率
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

# ── 11. 品类聚合 ──
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
    "shoe": shoes,
    "matrix": [
        ["流水", f"¥{kpi.get('actual', 0):,.0f}", f"{kpi.get('yoy', 0):+.1f}%", f"{kpi.get('mom', 0):+.1f}%"],
        ["达成率", f"{kpi.get('achieve', 0):.1f}%", f"{kpi.get('sssg', 0):+.1f}%", f"{kpi.get('mom', 0):+.1f}%"],
        ["折扣率", f"{kpi.get('discount', 0):.1f}%", f"{kpi.get('discount_yoy', 0):+.1f}%", f"{kpi.get('discount_mom', 0):+.1f}%"],
        ["件单价", f"¥{kpi.get('unit_price', 0):.0f}", f"{kpi.get('unit_yoy', 0):+.1f}%", f"{kpi.get('unit_mom', 0):+.1f}%"],
        ["客单价", f"¥{kpi.get('avg_ticket', kpi.get('avg_ticket_sec2', 0)):.0f}", f"{kpi.get('avg_ticket_yoy', 0):+.1f}%", f"{kpi.get('avg_ticket_mom', 0):+.1f}%"],
        ["连带率", f"{kpi.get('attach_rate', 0):.2f}件", f"{kpi.get('attach_yoy', 0):+.1f}%", f"{kpi.get('attach_mom', 0):+.1f}%"],
    ],
    "mtd": {}, "ytd": {}, "reg": {},
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