#!/usr/bin/env python3
"""
飞书多维表格 → 仪表板 DATA 全量解析器
解析所有区段: KPI汇总 / 日别 / 品类 / 系列 / 季节 / TOP商品 / 折扣区间
"""
import json, os, re, sys
from pathlib import Path
import requests

BASE = Path(__file__).parent.parent

# ── 环境变量 ──
APP_ID = os.environ.get("FEISHU_APP_ID", "cli_a931cdfb8bf89bb5")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
BASE_ID = os.environ.get("FEISHU_BASE_ID", "XJAZbw1rqaWHMnsVAJIci7ttnJd")
TABLE_ID = "tblmGijNaVv80ogT"

if not APP_SECRET:
    env_file = BASE / '.env'
    if env_file.exists():
        for line in open(env_file):
            line = line.strip()
            if line.startswith("FEISHU_APP_SECRET="):
                APP_SECRET = line.split("=", 1)[1].strip().strip('"').strip("'")

if not APP_SECRET:
    print("❌ FEISHU_APP_SECRET 未配置"); sys.exit(1)

# ── 工具函数 ──
def auth():
    r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
    return "Bearer " + r.json()["tenant_access_token"]

TOKEN = auth()

def _num(s):
    if s is None: return None
    if isinstance(s, (int, float)): return float(s)
    s = str(s).replace(",", "").replace("¥", "").strip()
    if s in ("/", "-", ""): return None
    try:
        if s.endswith("%"): return float(s[:-1])
        return float(s)
    except ValueError: return None

def _pct(s):
    """百分比值保留原始数字（如 109.4% → 109.4）"""
    v = _num(s)
    return v  # feishu_build already stores raw values

# ── 读取所有行 ──
print("📡 正在从飞书获取数据...")
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

def get(row, key): return row.get(key)
def getn(row, key): return _num(row.get(key))

# ── 1. 提取周期和门店 ──
week_period, week_range = "W??", ""
for row in rows:
    for v in row.values():
        if isinstance(v, str) and "W" in v and "周累计" in v:
            m = re.search(r'(W\d+)', v)
            week_period = m.group(1) if m else week_period
            week_range = v.replace(f"{week_period}周累计：", "").replace("至", "-")

# ── 2. 区段1+2: 总体KPI + KPI细分 ──
# 查找汇总区的周合计行 (按 RGHW 值区分)
sec1_row = sec2_row = None
first_weekly = False
for row in rows:
    if get(row, "奥莱店华南区城市") == "周合计":
        if not first_weekly:
            sec1_row = row; first_weekly = True
        else:
            sec2_row = row; break

SECTION1_MAP = {
    "字段 9": "target", "字段 11": "actual", "字段 13": "achieve",
    "字段 15": "sssg", "字段 16": "yoy", "字段 20": "mom",
    "字段 25": "o2o", "字段 27": "o2o_pct", "字段 28": "o2o_mom",
    "字段 29": "pad", "字段 31": "o2o_online",
    "RGHW": "daily_flow", "广州一区(奥莱店华南区)": "conv_rate",
    "字段 4": "conv_yoy", "字段 6": "flow_yoy",
    "字段 5": "conv_mom", "字段 18": "sssg_adj",
}
SECTION2_MAP = {
    # Row 12 标签: 字段3=当期, 字段4=同比, 字段10=当期, 字段13=环比, 字段15=当期, 字段16=同比
    "字段 3":             "unit_price",      # 件单价 当期 = 113
    "字段 4":             "unit_yoy",        # 件单价 同比 = -14.4%
    "字段 9":             "unit_mom",        # 件单价环比 = -15.0%
    "字段 10":            "attach_rate",     # 连带率 当期 = 4.08
    "字段 13":            "attach_yoy",      # 连带率 同比 = -9.0%
    "字段 15":            "tkt_cnt",         # 交易次数 当期 = 276
    "字段 16":            "tkt_c_yoy",       # 交易次数 同比 = -10.7%
    "字段 20":            "discount",        # 折扣率 = 42.2%
    "字段 24":            "discount_yoy",    # 折扣率同比 = -0.9%
    "字段 26":            "disc_adj",        # 折扣率(剔团购) = 42.2%
    "字段 30":            "discount_mom",    # 折扣率环比 = -0.9%
    "字段 6":             "avg_ticket_sec2", # 客单价(从细分区段) = 463
    "字段 22":            "avg_ticket_yoy",  # 客单价同比 = -1.3%
    "字段 28":            "avg_ticket_mom",  # 客单价环比 = -1.3%
    "RGHW":               "attach_mom",      # 连带率环比 = -6.6%
}

kpi_updates = {"period": week_period, "week_range": week_range}
def apply_map(row, mapping, label):
    if not row: return
    for fid, dkey in mapping.items():
        v = _num(row.get(fid))
        if v is not None: kpi_updates[dkey] = v

apply_map(sec1_row, SECTION1_MAP, "总体KPI")
apply_map(sec2_row, SECTION2_MAP, "KPI细分")

# avg_ticket: 从日别区客单价行取 周报（单位：元）字段
for row in rows:
    if get(row, "奥莱店华南区城市") == "客单价":
        v = _num(row.get("周报（单位：元）"))
        if v: kpi_updates["avg_ticket"] = v
        break

# ── 3. 日别数据 ──
# ⚠️ 限定在日别区段内(品类区也有同比/环比行导致覆盖)
# 日别列映射: 字段ID → 星期
DAY_COLS = {"字段 3": "周一", "字段 4": "周二", "RGHW": "周三",
            "字段 6": "周四", "线下折扣店": "周五", "字段 9": "周六", "字段 10": "周日"}
DAILY_METRICS = ("流水目标", "EPOS流水", "EPOS达成率", "同比", "环比",
                 "成交率", "客流数量", "客单价", "连带率", "同店同比\n(剔除团购)")

daily_raw = {}
in_daily_section = False
for row in rows:
    city = get(row, "奥莱店华南区城市") or ""
    if city == "日别":
        in_daily_section = True; continue
    if city == "大类别":
        break  # 日别区结束
    if in_daily_section and city in DAILY_METRICS:
        metric = city.replace("\n", "")
        daily_raw[metric] = row

daily = []
for i, (fid, day_name) in enumerate(DAY_COLS.items()):
    entry = {"n": day_name}
    if "流水目标" in daily_raw: entry["t"] = getn(daily_raw["流水目标"], fid) or 0
    if "EPOS流水" in daily_raw: entry["f"] = getn(daily_raw["EPOS流水"], fid) or 0
    if "EPOS达成率" in daily_raw: entry["a"] = getn(daily_raw["EPOS达成率"], fid) or 0
    if "同比" in daily_raw: entry["y"] = getn(daily_raw["同比"], fid) or 0
    if "成交率" in daily_raw: entry["c"] = getn(daily_raw["成交率"], fid) or 0
    if "客流数量" in daily_raw: entry["v"] = getn(daily_raw["客流数量"], fid) or 0
    if "客单价" in daily_raw: entry["tk"] = getn(daily_raw["客单价"], fid) or 0
    if "连带率" in daily_raw: entry["at"] = getn(daily_raw["连带率"], fid) or 0
    daily.append(entry)

# ── 4. 品类数据 ──
# 品类数据从季节表的中类数据聚合得到（男服+女服=服，男鞋+女鞋=鞋）
# 器配数据仍从大类别表提取
# 注意：此部分依赖第9部分的季节数据提取，因此品类聚合逻辑移至季节数据提取之后

# 品类指标映射: feishu行类型 → (DATA字段名, 默认值)
CATE_METRICS = {
    "流水": ("flow", 0), "数量": ("qty", 0),
    "折扣": ("disc", 0), "流水占比": ("f_share", 0),
    "同比": ("yoy", 0), "环比": ("mom", 0),
    "SKU(个数)": ("sku_s", 0), "SKU动销率": ("sku_u", 0),
    "库存数量": ("s_qty", 0), "库存占比": ("s_q_share", 0),
}
PRODUCT_CATS = {"鞋", "服", "器配"}

# 初始化品类数据结构（器配和性别组数据在此提取，鞋服数据在季节数据提取后聚合）
category = {}
for cname in ["鞋", "服", "器配", "男", "女", "童"]:
    entry = {dk: dv for _, (dk, dv) in CATE_METRICS.items()}
    entry["group"] = "product" if cname in PRODUCT_CATS else "gender"
    category[cname] = entry

# 器配数据从大类别表提取
in_category = False
for row in rows:
    city = get(row, "奥莱店华南区城市") or ""
    if city == "大类别":
        in_category = True; continue
    if city in ("服装-PS中类", "鞋-系列", "器配中类"):
        if in_category: break  # 品类区结束
    if in_category and city in CATE_METRICS:
        dkey, _ = CATE_METRICS[city]
        # 只提取器配数据（字段 15）
        v = getn(row, "字段 15")
        if v is not None:
            category["器配"][dkey] = v

# 性别组数据从大类别表提取
in_category = False
for row in rows:
    city = get(row, "奥莱店华南区城市") or ""
    if city == "大类别":
        in_category = True; continue
    if city in ("服装-PS中类", "鞋-系列", "器配中类"):
        if in_category: break
    if in_category and city in CATE_METRICS:
        dkey, _ = CATE_METRICS[city]
        # 男=字段3, 女=字段4, 童=字段6
        for fid, cname in [("字段 3", "男"), ("字段 4", "女"), ("字段 6", "童")]:
            v = getn(row, fid)
            if v is not None:
                category[cname][dkey] = v

# 品类补充字段: 计算 match_lbl 和 gap（仅产品组）
# 库存占比优先用飞书原始数据，若缺失则用库存数量计算
prod_cats = [c for c, cd in category.items() if cd.get("group") == "product"]
total_sq = sum(category[c].get("s_qty", 0) for c in prod_cats)
for cname in prod_cats:
    cd = category[cname]
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

# 性别组: match_lbl 标记为仅产品维度
for cname, cd in category.items():
    if cd.get("group") == "gender":
        cd["match_lbl"] = "（匹配分析仅产品维度）"

# shoe_share: 从品类数据取鞋的流水占比
if "鞋" in category and category["鞋"].get("f_share"):
    kpi_updates["shoe_share"] = category["鞋"]["f_share"]

# ── 5. 子品类 (sub_ps = 服装PS中类 + 器配中类) ──
sub_ps = []
sub_sections = [("服装-PS中类", "器配中类"), ("器配中类", "TOP商品")]  # (start, end)

# 配件类名称列表（用于区分子品类是服装还是配件）
ACC_NAMES = {"包类", "袜类", "帽类", "内裤类", "球", "其他中类"}

for sec_start, sec_end in sub_sections:
    in_section = False
    for row in rows:
        city = get(row, "奥莱店华南区城市") or ""
        if city == sec_start:
            in_section = True; continue
        if city == sec_end or (city == "合计" and in_section):
            break
        if not in_section: continue
        # 跳过标签行和无数据行
        if city in (sec_start, "") and get(row, "RGHW") is None:
            continue
        if not city: continue

        name = city
        flow_val = getn(row, "RGHW") or 0
        share_val = getn(row, "字段 9") or 0    # 占比
        yoy_val = getn(row, "字段 13") or 0     # 同比(剔除团购)
        mom_val = getn(row, "字段 15") or 0     # 环比

        # 判断是否为配件类
        is_accessory = name in ACC_NAMES

        # 所有中类都包含(含无数据项)
        sub_ps.append({
            "n": name, "f": flow_val, "d": share_val,
            "q": 0, "isAcc": is_accessory,  # q=数量(飞书无此数据)
            "yoy": yoy_val, "mom": mom_val
        })

# ── 6. 鞋系列 ──
shoes = []
in_shoe = False
for row in rows:
    city = get(row, "奥莱店华南区城市") or ""
    if city == "鞋-系列":
        in_shoe = True; continue
    if city == "合计" and in_shoe:
        in_shoe = False; continue
    if not in_shoe: continue
    if not city or city in ("滑板系列", "极限运动", "健身"): continue

    name = city
    flow_val = getn(row, "RGHW") or 0
    qty_val = getn(row, "字段 9") or 0
    disc_val = getn(row, "字段 13") or 0

    if name and flow_val:
        shoes.append({"n": name, "f": flow_val, "q": int(qty_val) if qty_val else 0, "d": disc_val})

# ── 7. TOP商品 ──
top = {}
for row in rows:
    city = get(row, "奥莱店华南区城市") or ""
    if city and city.startswith("TOP"):
        key = city
        for sub_key, col in [("4", "字段 3"), ("6", "字段 4"), ("8", "字段 6"), ("10", "RGHW")]:
            v = getn(row, col)
            if v is not None:
                top.setdefault(key, {})[sub_key] = v

# ── 8. 折扣区间 (暂用旧数据, 飞书表格格式不同) ──
# 飞书表格中折扣区间数据与TOP商品混排, 暂不覆盖
disc_range = None  # 保留 DATA 中已有的 disc_range

# ── 9. 季节数据 (从 tblhxVtkScorpwxQ 产品季节表, 3段) ──
SEAS_TABLE = "tblhxVtkScorpwxQ"
# 段1列映射: 总服 + 总鞋 → 使用 (服)/(鞋) 命名，与前端渲染一致
SEC1_COLS = {
    "服": "2025Q4及以前(服)", "字段 4": "2026Q1(服)", "字段 6": "2026Q2(服)",
    "字段 8": "2026Q3+(服)", "字段 11": "26年常青(服)",
    "鞋": "2025Q4及以前(鞋)", "字段 15": "2026Q1(鞋)", "字段 17": "2026Q2(鞋)",
    "字段 19": "2026Q3+(鞋)", "字段 22": "26年常青(鞋)",
}
# 段2(男服/女服): 服=男服, 鞋=女服 → 字段4/6/8/11=男服各季, 15/17/19/22=女服各季
SEC2_COLS_MALE = {
    "服": "2025Q4及以前(男服)", "字段 4": "2026Q1(男服)", "字段 6": "2026Q2(男服)",
    "字段 8": "2026Q3+(男服)", "字段 11": "26年常青(男服)",
}
SEC2_COLS_FEMALE = {
    "鞋": "2025Q4及以前(女服)", "字段 15": "2026Q1(女服)", "字段 17": "2026Q2(女服)",
    "字段 19": "2026Q3+(女服)", "字段 22": "26年常青(女服)",
}
# 段3(男鞋/女鞋): 服=男鞋, 鞋=女鞋 → 字段4/6/8/11=男鞋各季, 15/17/19/22=女鞋各季
SEC3_COLS_MALE = {
    "服": "2025Q4及以前(男鞋)", "字段 4": "2026Q1(男鞋)", "字段 6": "2026Q2(男鞋)",
    "字段 8": "2026Q3+(男鞋)", "字段 11": "26年常青(男鞋)",
}
SEC3_COLS_FEMALE = {
    "鞋": "2025Q4及以前(女鞋)", "字段 15": "2026Q1(女鞋)", "字段 17": "2026Q2(女鞋)",
    "字段 19": "2026Q3+(女鞋)", "字段 22": "26年常青(女鞋)",
}

SEAS_METRICS = {
    "流水": ("f", 0), "数量": ("q", 0), "折扣": ("d", 0),
    "流水占比": ("fs", 0), "环比": ("mom", 0), "SKU(个数)": ("sku", 0),
    "库存数量": ("stock_qty", 0), "库存金额": ("stock_amt", 0),
    "吊牌价": ("tag_price", 0), "同比": ("yoy", 0),
}

r2 = requests.get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{SEAS_TABLE}/records",
    headers={"Authorization": TOKEN}, params={"page_size": 100}, timeout=15)
seas_items = r2.json().get("data", {}).get("items", [])
seas_rows = [item.get("fields", {}) for item in seas_items]

seas = {}; mid_agg = {"男服": {}, "女服": {}, "男鞋": {}, "女鞋": {}}

# 段1: 行3-25 (总服+总鞋)
for row in seas_rows:
    mn = (row.get("大类别") or "").replace("\n", "")
    if mn == "大类别": break  # 段1结束
    if mn in SEAS_METRICS:
        dkey, _ = SEAS_METRICS[mn]
        for fid, sk in SEC1_COLS.items():
            v = _num(row.get(fid))
            if v is not None: seas.setdefault(sk, {})[dkey] = v

# 段2: 行27-52 (男服+女服) — 从第二个"大类别"行之后开始
sec2_start = next((i for i,r in enumerate(seas_rows) if r.get("大类别","") == "大类别" and i > 0), None)
if sec2_start:
    # 段2 - 男服数据(服列) + 女服数据(鞋列)
    for row in seas_rows[sec2_start+3:]:  # 跳过 header 行
        mn = (row.get("大类别") or "").replace("\n", "")
        if mn == "大类别": break  # 段2结束
        if mn in SEAS_METRICS:
            dkey, _ = SEAS_METRICS[mn]
            # 男服 - 聚合所有指标到 mid_agg
            for fid, sk in SEC2_COLS_MALE.items():
                v = _num(row.get(fid))
                if v is not None:
                    seas.setdefault(sk, {})[dkey] = v
                    # 聚合到 mid_agg["男服"]
                    mid_agg.setdefault("男服", {}).setdefault(dkey, 0)
                    mid_agg["男服"][dkey] += v
            # 女服 - 聚合所有指标到 mid_agg
            for fid, sk in SEC2_COLS_FEMALE.items():
                v = _num(row.get(fid))
                if v is not None:
                    seas.setdefault(sk, {})[dkey] = v
                    # 聚合到 mid_agg["女服"]
                    mid_agg.setdefault("女服", {}).setdefault(dkey, 0)
                    mid_agg["女服"][dkey] += v

# 段3: 行54-79 (男鞋+女鞋) — 从第三个"大类别"行之后
sec3_start = next((i for i,r in enumerate(seas_rows) if r.get("大类别","") == "大类别" and i > sec2_start), None) if sec2_start else None
if sec3_start:
    for row in seas_rows[sec3_start+3:]:
        mn = (row.get("大类别") or "").replace("\n", "")
        if mn == "大类别": break
        if mn in SEAS_METRICS:
            dkey, _ = SEAS_METRICS[mn]
            # 男鞋 - 聚合所有指标到 mid_agg
            for fid, sk in SEC3_COLS_MALE.items():
                v = _num(row.get(fid))
                if v is not None:
                    seas.setdefault(sk, {})[dkey] = v
                    # 聚合到 mid_agg["男鞋"]
                    mid_agg.setdefault("男鞋", {}).setdefault(dkey, 0)
                    mid_agg["男鞋"][dkey] += v
            # 女鞋 - 聚合所有指标到 mid_agg
            for fid, sk in SEC3_COLS_FEMALE.items():
                v = _num(row.get(fid))
                if v is not None:
                    seas.setdefault(sk, {})[dkey] = v
                    # 聚合到 mid_agg["女鞋"]
                    mid_agg.setdefault("女鞋", {}).setdefault(dkey, 0)
                    mid_agg["女鞋"][dkey] += v

# su(售罄率)计算
for key, sd in seas.items():
    if sd.get("tag_price", 0) > 0:
        sd["su"] = round(sd.get("f", 0) / sd["tag_price"] * 100, 2)
    else: sd["su"] = 0
    sd.setdefault("sat", 0); sd.setdefault("stock_qty", sd.get("stock_qty", 0))

# ── 4.1 品类数据聚合（从季节表中类数据） ──
# 服 = 男服 + 女服
for mid_cat in ["男服", "女服"]:
    for season_key, season_data in seas.items():
        if f"({mid_cat})" in season_key:
            category["服"]["flow"] += season_data.get("f", 0)
            category["服"]["qty"] += season_data.get("q", 0)
            category["服"]["sku_s"] += season_data.get("sku", 0)
            category["服"]["s_qty"] += season_data.get("stock_qty", 0)
            # 折扣率加权平均
            if season_data.get("f", 0) > 0:
                category["服"]["disc"] += season_data.get("d", 0) * season_data.get("f", 0)

# 鞋 = 男鞋 + 女鞋
for mid_cat in ["男鞋", "女鞋"]:
    for season_key, season_data in seas.items():
        if f"({mid_cat})" in season_key:
            category["鞋"]["flow"] += season_data.get("f", 0)
            category["鞋"]["qty"] += season_data.get("q", 0)
            category["鞋"]["sku_s"] += season_data.get("sku", 0)
            category["鞋"]["s_qty"] += season_data.get("stock_qty", 0)
            # 折扣率加权平均
            if season_data.get("f", 0) > 0:
                category["鞋"]["disc"] += season_data.get("d", 0) * season_data.get("f", 0)

# 计算加权平均折扣率
for cat in ["服", "鞋"]:
    if category[cat]["flow"] > 0:
        category[cat]["disc"] = category[cat]["disc"] / category[cat]["flow"]
    else:
        category[cat]["disc"] = 0

# sku_u 补充: 从季节表 SKU动销率行取总服/总鞋/男/女
# 行18(总段) → 服/鞋; 行45(男服/女服) → 男/女
for fid, cname in [("服", "服"), ("鞋", "鞋")]:
    v = _num(seas_rows[17].get(fid)) if len(seas_rows) > 17 else None
    if v and cname in category:
        if category[cname].get("sku_u", 0) == 0: category[cname]["sku_u"] = v
for fid, cname in [("服", "男"), ("鞋", "女")]:
    v = _num(seas_rows[44].get(fid)) if len(seas_rows) > 44 else None
    if v and cname in category:
        if category[cname].get("sku_u", 0) == 0: category[cname]["sku_u"] = v

# ── 10. 生成 KPI Matrix ──
def _pct(v): return f"{v:.1f}%" if v >= 0 else f"{v:.1f}%"
def _pp(v): return f"{v:.2f}pp" if v >= 0 else f"{v:.2f}pp"
def _money(v): return f"¥{v:,.0f}"

ach_v = kpi_updates.get("achieve", 0)
yoy_v = kpi_updates.get("yoy", 0)
mom_v = kpi_updates.get("mom", 0)
conv_v = kpi_updates.get("conv_rate", 0)
conv_yoy = kpi_updates.get("conv_yoy", 0)
conv_mom = kpi_updates.get("conv_mom", 0)
flow_v = kpi_updates.get("daily_flow", 0)
flow_yoy = kpi_updates.get("flow_yoy", 0)
flow_mom = kpi_updates.get("flow_mom", 0)
avg_t = kpi_updates.get("avg_ticket", 0)
avg_t_yoy = kpi_updates.get("avg_ticket_yoy", 0)
avg_t_mom = kpi_updates.get("avg_ticket_mom", 0)
attach_r = kpi_updates.get("attach_rate", 0)
attach_yoy = kpi_updates.get("attach_yoy", 0)
attach_mom = kpi_updates.get("attach_mom", 0)
unit_p = kpi_updates.get("unit_price", 0)
unit_yoy = kpi_updates.get("unit_yoy", 0)
unit_mom = kpi_updates.get("unit_mom", 0)
disc_v = kpi_updates.get("discount", 0)
disc_yoy_p = kpi_updates.get("discount_yoy", 0)
disc_mom_p = kpi_updates.get("discount_mom", 0)
o2o_v = kpi_updates.get("o2o", 0)
o2o_yoy = 0  # not available from feishu
o2o_mom = kpi_updates.get("o2o_mom", 0)
sssg_v = kpi_updates.get("sssg", 0)

matrix = [
    ['流水达成率', _pct(ach_v), _pct(yoy_v), _pct(mom_v)],
    ['成交率', f"{conv_v:.2f}%", f"{conv_yoy:.2f}pp", f"{conv_mom:.2f}pp"],
    ['日均客流', f"{flow_v:,.0f}人", _pct(flow_yoy), _pct(flow_mom)],
    ['客单价', _money(avg_t), _pct(avg_t_yoy), _pct(avg_t_mom)],
    ['连带率', f"{attach_r:.2f}件", _pct(attach_yoy), _pct(attach_mom)],
    ['件单价', _money(unit_p), _pct(unit_yoy), _pct(unit_mom)],
    ['折扣率', f"{disc_v:.2f}%", f"{disc_yoy_p:.2f}pp", f"{disc_mom_p:.2f}pp"],
    ['O2O流水', _money(o2o_v), '--', _pct(o2o_mom)],
    ['SSSG', _pct(sssg_v), '--', _pct(mom_v)],
]

# ── 构建最终 DATA 更新 ──
all_updates = dict(kpi_updates)
all_updates["daily"] = daily
all_updates["category"] = category
all_updates["sub_ps"] = sub_ps
all_updates["shoe"] = shoes
all_updates["top"] = top
all_updates["seas"] = seas
all_updates["mid_agg"] = mid_agg
all_updates["matrix"] = matrix
# disc_range 暂不更新

# ── 更新 HTML ──
print("📝 更新 HTML...")
updated_count = 0
for html_name in ('weekly-dashboard.html', 'index.html'):
    html_path = BASE / html_name
    if not html_path.exists(): continue

    html = html_path.read_text(encoding='utf-8')
    m = re.search(r'const DATA = ({.*?});', html, re.DOTALL)
    if not m:
        print(f"  ⚠️ {html_name}: 未找到 DATA"); continue

    try:
        data_obj = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        print(f"  ❌ {html_name}: JSON解析失败: {e}"); continue

    # 递归更新 (浅层 + 嵌套对象)
    for key, val in all_updates.items():
        if key == "store": continue
        if key in data_obj:
            old = data_obj[key]
            if old != val:
                data_obj[key] = val
                updated_count += 1
                if not isinstance(val, (list, dict)):
                    print(f"  📊 {key}: {old} → {val}")

    new_data = json.dumps(data_obj, ensure_ascii=False, default=str)
    html = html[:m.start(1)] + new_data + html[m.end(1):]

    # 确保 init 中包含 buildKpiStrip()
    old_i = "window.addEventListener('DOMContentLoaded',()=>{\n  initTables();\n  drawDailyCharts();\n});"
    new_i = "window.addEventListener('DOMContentLoaded',()=>{\n  buildKpiStrip();\n  initTables();\n  drawDailyCharts();\n});"
    html = html.replace(old_i, new_i)

    html_path.write_text(html, encoding='utf-8')
    print(f"  ✅ {html_name}")

# ── 摘要 ──
print(f"\n📊 更新完成！共更新 {updated_count} 个字段")
print(f"   周期: {week_period} | {week_range}")
print(f"   daily: {len(daily)} 天 | category: {len(category)} 类 | sub_ps: {len(sub_ps)} 个")
print(f"   shoes: {len(shoes)} 个 | TOP: {len(top)} 组 | seas: {len(seas)} 季 | mid_agg: {len(mid_agg)} 组")
