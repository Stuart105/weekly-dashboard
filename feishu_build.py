#!/usr/bin/env python3
"""
飞书多维表格 → 仪表板 DATA 全量解析器
解析所有区段: KPI汇总 / 日别 / 品类 / 系列 / 季节 / TOP商品 / 折扣区间
"""
import json, os, re, sys
from pathlib import Path
import requests

BASE = Path(__file__).parent

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
    "RGHW": "flow", "广州一区(奥莱店华南区)": "conv",
    "字段 4": "conv_yoy", "字段 6": "flow_yoy",
    "字段 5": "conv_mom", "字段 18": "sssg_adj",
}
SECTION2_MAP = {
    "字段 10": "attach_r", "字段 15": "tkt_cnt", "字段 20": "disc",
    "字段 26": "disc_adj", "RGHW": "shoe_share", "字段 6": "unit_p",
    "字段 4": "unit_yoy", "字段 13": "attach_yoy", "字段 16": "avg_t_yoy",
}

kpi_updates = {"period": week_period, "week_range": week_range}
def apply_map(row, mapping, label):
    if not row: return
    for fid, dkey in mapping.items():
        v = _num(row.get(fid))
        if v is not None: kpi_updates[dkey] = v

apply_map(sec1_row, SECTION1_MAP, "总体KPI")
apply_map(sec2_row, SECTION2_MAP, "KPI细分")
if "actual" in kpi_updates and "tkt_cnt" in kpi_updates and kpi_updates["tkt_cnt"] > 0:
    kpi_updates["avg_t"] = round(kpi_updates["actual"] / kpi_updates["tkt_cnt"], 2)

# ── 3. 日别数据 ──
# 日别列映射: 字段ID → 星期
DAY_COLS = {"字段 3": "周一", "字段 4": "周二", "RGHW": "周三",
            "字段 6": "周四", "线下折扣店": "周五", "字段 9": "周六", "字段 10": "周日"}

daily_raw = {}
for row in rows:
    city = get(row, "奥莱店华南区城市") or ""
    if city in ("流水目标", "EPOS流水", "EPOS达成率", "同比", "环比",
                 "成交率", "客流数量", "客单价", "连带率", "同店同比\n(剔除团购)"):
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
# Category columns: 字段 9=鞋, 字段 13=服, 字段 15=器配, 字段 3=男, 字段 4=女, 字段 6=童
CATE_COLS = {"字段 9": "鞋", "字段 13": "服", "字段 15": "器配",
             "字段 3": "男", "字段 4": "女", "字段 6": "童"}
category = {}

# 品类指标映射: feishu行类型 → (DATA字段名, 默认值)
CATE_METRICS = {
    "流水": ("flow", 0), "数量": ("qty", 0),
    "折扣": ("disc", 0), "流水占比": ("f_share", 0),
    "同比": ("yoy", 0), "环比": ("mom", 0),
    "SKU(个数)": ("sku_s", 0), "SKU动销率": ("sku_u", 0),
    "库存数量": ("s_qty", 0), "库存占比": ("s_q_share", 0),
}

# 为每个品类初始化默认值
for cname in CATE_COLS.values():
    category[cname] = {dk: dv for _, (dk, dv) in CATE_METRICS.items()}

for row in rows:
    city = get(row, "奥莱店华南区城市") or ""
    if city in CATE_METRICS:
        dkey, _ = CATE_METRICS[city]
        for fid, cname in CATE_COLS.items():
            v = getn(row, fid)
            if v is not None:
                category[cname][dkey] = v

# 品类补充字段: match_lbl (基于yoy方向)
for cname, cd in category.items():
    cd["match_lbl"] = "增长" if cd.get("yoy", 0) > 0 else ("下降" if cd.get("yoy", 0) < 0 else "持平")

# ── 5. 服装品类(子品类 sub_ps) ──
sub_ps = []
in_apparel = False
for row in rows:
    city = get(row, "奥莱店华南区城市") or ""
    if city == "服装-PS中类":
        in_apparel = True; continue
    if city == "合计" and in_apparel:
        in_apparel = False; continue
    if not in_apparel: continue
    if not city or city in ("服装-PS中类", "裙类", "编织衫", "其他中类"): continue

    name = city
    flow_val = getn(row, "RGHW") or 0
    disc_val = getn(row, "字段 9") or 0  # 占比 → 改为用占比字段
    qty_val = getn(row, "字段 13") or 0   # 同比
    yoy_val = getn(row, "字段 15") or 0   # 环比

    if name and flow_val:
        sub_ps.append({"n": name, "f": flow_val, "d": disc_val, "q": int(qty_val) if qty_val else 0,
                        "isAcc": False, "yoy": yoy_val})

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

# ── 8. 折扣区间 ──
disc_range = {}
for row in rows:
    city = get(row, "奥莱店华南区城市") or ""
    if city == "单件订单" or city == "数量":
        continue
    if get(row, "销售订单数据"):
        continue
    # 折扣区间行: city 是一个数字 (折扣率)
    try:
        disc_key = int(float(city))
    except (ValueError, TypeError):
        continue
    cols = {}
    for fid in ("字段 3", "字段 4", "字段 6", "RGHW", "字段 9", "字段 10", "字段 13", "字段 15"):
        v = get(row, fid)
        if v is not None:
            cols[fid] = str(v)
    label = get(row, "RGHW") or ""
    if not label and not cols:
        continue
    disc_range[str(disc_key)] = {"label": str(label), "cols": cols}

# ── 构建最终 DATA 更新 ──
all_updates = dict(kpi_updates)
all_updates["daily"] = daily
all_updates["category"] = category
all_updates["sub_ps"] = sub_ps
all_updates["shoe"] = shoes
all_updates["top"] = top
if disc_range:
    all_updates["disc_range"] = disc_range

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
    html_path.write_text(html, encoding='utf-8')
    print(f"  ✅ {html_name}")

# ── 摘要 ──
print(f"\n📊 更新完成！共更新 {updated_count} 个字段")
print(f"   周期: {week_period} | {week_range}")
print(f"   daily: {len(daily)} 天 | category: {len(category)} 类 | sub_ps: {len(sub_ps)} 个")
print(f"   shoes: {len(shoes)} 个 | TOP: {len(top)} 组 | disc_range: {len(disc_range)} 档")
