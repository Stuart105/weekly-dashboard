#!/usr/bin/env python3
"""
从飞书多维表格获取最新数据，完整更新 weekly-dashboard.html 的页头和 KPI 指标。
飞书表格结构：
  第 2-4 行: 标签行（说明每列含义）
  第 5 行:   周合计（总体KPI数据）
  第 10 行:  第二组标签行
  第 13 行:  周合计（细分KPI数据：连带率/折扣率/鞋占比等）
"""
import json, os, re, sys
from pathlib import Path

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
            elif line.startswith("FEISHU_APP_ID="):
                APP_ID = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("FEISHU_BASE_ID="):
                BASE_ID = line.split("=", 1)[1].strip().strip('"').strip("'")

if not APP_SECRET:
    print("❌ FEISHU_APP_SECRET 未配置")
    sys.exit(1)

import requests

# ── 认证 ──
def auth():
    r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
    return "Bearer " + r.json()["tenant_access_token"]

TOKEN = auth()

def _num(s):
    """字符串转数值"""
    if s is None: return None
    if isinstance(s, (int, float)): return float(s)
    s = str(s).replace(",", "").replace("¥", "").strip()
    if s in ("/", "-", ""): return None
    try:
        if s.endswith("%"):
            return float(s[:-1])
        return float(s)
    except ValueError:
        return None

# ── 读取所有行 ──
print("📡 正在从飞书获取数据...")
items, pt = [], None
while True:
    p = {"page_size": 200}
    if pt: p["page_token"] = pt
    r = requests.get(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{TABLE_ID}/records",
        headers={"Authorization": TOKEN}, params=p, timeout=15)
    d = r.json()
    items += d["data"].get("items", [])
    if not d["data"].get("has_more"): break
    pt = d["data"].get("page_token")

# ── 解析行数据 ──
rows = [item.get("fields", {}) for item in items]

# ── 定义字段映射：区1(总体KPI)的 周合计 行 → DATA key ──
SECTION1_MAP = {
    # 飞书字段ID          → Dashboard DATA key
    "字段 9":             "target",      # 流水目标
    "字段 11":            "actual",      # 流水
    "字段 13":            "achieve",     # 流水达成率
    "字段 15":            "sssg",        # 流水同比(同店同比)
    "字段 16":            "yoy",         # 同店同比
    "字段 20":            "mom",         # 流水环比
    "字段 25":            "o2o",         # O2O流水
    "字段 27":            "o2o_pct",     # O2O占比
    "字段 28":            "o2o_mom",     # O2O环比
    "字段 29":            "pad",         # PAD流水
    "字段 31":            "o2o_online",  # 官网O2O
    "RGHW":               "flow",        # 客流量
    "广州一区(奥莱店华南区)": "conv",      # 成交率
    "字段 4":             "conv_yoy",    # 成交率同比
    "字段 6":             "flow_yoy",    # 客流同比
    "字段 5":             "conv_mom",    # 成交率环比
    "字段 18":            "sssg_adj",    # 同店同比(剔团购)
}

# ── 定义字段映射：区2(KPI细分)的 周合计 行 → DATA key ──
SECTION2_MAP = {
    "字段 10":            "attach_r",    # 连带率
    "字段 15":            "tkt_cnt",     # 交易次数
    "字段 20":            "disc",        # 折扣率
    "字段 26":            "disc_adj",    # 折扣率(剔团购)
    "RGHW":               "shoe_share",  # 鞋占比
    "字段 6":             "unit_p",      # 件单价
    "字段 4":             "unit_yoy",    # 件单价同比
    "字段 13":            "attach_yoy",  # 连带率同比
    "字段 16":            "avg_t_yoy",   # 客单价同比
}

# ── 查找 周合计 行 ──
sec1_row, sec2_row = None, None
week_period, week_range = "W??", ""
first_weekly_found = False

for i, row in enumerate(rows):
    city = row.get("奥莱店华南区城市", "")
    if city == "周合计":
        # 检查 RGHW 值来区分 section 1 和 2
        rghw = str(row.get("RGHW", ""))
        if not first_weekly_found:
            sec1_row = row
            first_weekly_found = True
        else:
            sec2_row = row

    # 提取周期信息
    for v in row.values():
        if isinstance(v, str) and "W" in v and "周累计" in v:
            m = re.search(r'(W\d+)', v)
            if m:
                week_period = m.group(1)
                week_range = v.replace(f"{week_period}周累计：", "").replace("至", "-")

# ── 应用映射 ──
updates = {
    "period": week_period,
    "week_range": week_range,
}

def apply_section(row, mapping, label):
    """将飞书行数据按映射写入 updates 字典"""
    if not row:
        print(f"  ⚠️ 未找到 {label} 行")
        return
    count = 0
    for field_id, data_key in mapping.items():
        raw = row.get(field_id)
        val = _num(raw)
        if val is not None:
            updates[data_key] = val
            count += 1
    print(f"  ✅ {label}: 映射了 {count} 个指标")

apply_section(sec1_row, SECTION1_MAP, "总体KPI(区1)")
apply_section(sec2_row, SECTION2_MAP, "KPI细分(区2)")

# ── 计算衍生指标 ──
if "actual" in updates and "tkt_cnt" in updates and updates["tkt_cnt"] > 0:
    updates["avg_t"] = round(updates["actual"] / updates["tkt_cnt"], 2)

# ── 更新 HTML ──
print("\n📝 更新 HTML...")
updated_count = 0
for html_name in ('weekly-dashboard.html', 'index.html'):
    html_path = BASE / html_name
    if not html_path.exists():
        continue

    html = html_path.read_text(encoding='utf-8')

    for key, val in updates.items():
        if isinstance(val, str):
            pattern = rf'"{re.escape(key)}":\s*"[^"]*"'
            replacement = f'"{key}": "{val}"'
        else:
            pattern = rf'"{re.escape(key)}":\s*[\d.]+(?:e[+-]?\d+)?'
            replacement = f'"{key}": {val}'
        new_html = re.sub(pattern, replacement, html)
        if new_html != html:
            updated_count += 1
            html = new_html

    html_path.write_text(html, encoding='utf-8')
    print(f"  ✅ {html_name}")

# ── 摘要 ──
print(f"\n📊 更新完成！共更新 {updated_count} 个字段")
print(f"   周期: {week_period}")
print(f"   日期: {week_range}")
for k, v in sorted(updates.items()):
    if k not in ("period", "week_range"):
        print(f"   {k}: {v}")
