#!/usr/bin/env python
"""Build single-page weekly report dashboard HTML."""
import json, os

BASE = 'D:/workbuddykongjian/2026-06-11-10-36-28'
with open(f'{BASE}/extracted_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

r7 = d['r7_kpi']; r15 = d['r15_price']; daily = d['daily']; cate = d['category']
top = d['top_goods']; seas = d['seasonal']; member = d['member']

store = "奥莱店华南区城市"
period = "W23"  
week_range = "2026.06.01-06.07"

# ───────── helpers ─────────
def pct(v, d=2): return f"{v:+.{d}f}%" if v is not None else '--'
def pa(v, d=2): return f"{v:.{d}f}%" if v is not None else '--'
def money(v): return f"{(v/10000):.1f}万" if v is not None and abs(v)>=10000 else (f"¥{v:,.0f}" if v is not None else '--')
def num(v): return f"{v:,.0f}" if v is not None else '--'
def f2(v): return f"{v:.2f}" if v is not None else '--'
def tag(v, up=True):
    if v is None or v == 0: return 'tag-neutral'
    return 'tag-up' if (v>0) == up else 'tag-down'

# ───────── extract all metrics ─────────
day_keys = ['4','6','8','10','12','14','16']
day_names = ['周一','周二','周三','周四','周五','周六','周日']

daily_rows = []
for i, dk in enumerate(day_keys):
    daily_rows.append({
        'n': day_names[i],
        't': float(daily['21']['data'][dk]),
        'f': float(daily['22']['data'][dk]),
        'a': float(daily['23']['data'][dk])*100,
        'y': float(daily['24']['data'][dk])*100,
        'c': float(daily['27']['data'][dk])*100,
        'v': int(round(float(daily['28']['data'][dk]))),
        'tk': float(daily['29']['data'][dk]),
        'at': float(daily['30']['data'][dk]),
    })

cat_data = {}
for ck, cn in [('4','男装'),('6','女装'),('14','鞋'),('16','配件')]:
    f_c = float(cate['36']['data'].get(ck,0))
    qty = int(float(cate['37']['data'].get(ck,0)))
    cat_data[cn] = {
        'flow': f_c, 'qty': qty,
        'disc': float(cate['38']['data'].get(ck,0))*100,
        'yoy': float(cate['42']['data'].get(ck,0))*100,
        'mom': float(cate['40']['data'].get(ck,0))*100,
        'f_share': float(cate['44']['data'].get(ck,0))*100,
        'sku_s': int(float(cate['47']['data'].get(ck,0))),
        's_qty': int(float(cate['52']['data'].get(ck,0))),
        's_sku': int(float(cate['53']['data'].get(ck,0))),
        'sku_u': (float(cate['50']['data'].get(ck,0))*100) if cate['50']['data'].get(ck) is not None else 0,
        'sat': float(cate['56']['data'].get(ck,0))*100,
        'st': float(cate['57']['data'].get(ck,0))*100,
    }

# Category match
total_sq = sum(cat_data[c]['s_qty'] for c in cat_data)
for cn in cat_data:
    sqs = cat_data[cn]['s_qty']/total_sq*100
    fs = cat_data[cn]['f_share']
    cat_data[cn]['s_q_share'] = sqs
    cat_data[cn]['gap'] = fs - sqs
    cat_data[cn]['match_lbl'] = '匹配' if abs(fs-sqs)<=5 else (f'销>库+{fs-sqs:.1f}pp' if fs>sqs else f'库>销{sqs-fs:.1f}pp')

# TOP
top_labels = {'125':'TOP10','126':'TOP20','127':'TOP40','128':'TOP60','129':'TOP100'}
top_data = {}
for rk, lbl in top_labels.items():
    if rk in top:
        td = top[rk]['data']
        top_data[lbl] = {k: float(td.get(k,0))*100 for k in ['4','6','8','10','13'] if k in td}

# KPI matrix for table
target_v = r7['14']; actual_v = r7['17']; achieve_v = r7['20']*100
yoy_v = r7['22']*100; mom_v = r7['28']*100; sssg_v = r7['24']*100
conv_v = r7['5']*100; flow_v = r7['8']; o2o_v = r7['33']; o2o_pct = r7['35']*100
avg_t = r15['10']; unit_p = r15['4']; attach_r = r15['16']; disc_v = r15['28']*100
tkt_cnt = r15['22']; pad_v = r7['37']; o2o_online = r7['39']
conv_yoy = float(r7['6'])*100; flow_yoy = float(r7['10'])*100
avg_t_yoy = r15['12']*100; attach_yoy = r15['18']*100; unit_yoy = r15['6']*100
disc_yoy_p = r15['30']*100; avg_t_mom = r15['14']*100; attach_mom = r15['20']*100
unit_mom = r15['8']*100; disc_mom = r15['32']*100; o2o_mom = float(r7['36'])*100
conv_mom = float(r7['7'])*100; flow_mom = float(r7['12'])*100

matrix = [
    ('流水达成率', pa(achieve_v), pct(yoy_v), pct(mom_v)),
    ('成交率', pa(conv_v), f'{pct(conv_yoy)}pp', f'{pct(conv_mom)}pp'),
    ('日均客流', flow_v, pct(flow_yoy), pct(flow_mom)),
    ('客单价', money(avg_t), pct(avg_t_yoy), pct(avg_t_mom)),
    ('连带率', f'{attach_r:.2f}件', pct(attach_yoy), pct(attach_mom)),
    ('件单价', money(unit_p), pct(unit_yoy), pct(unit_mom)),
    ('折扣率', pa(disc_v), f'{pct(disc_yoy_p)}pp', f'{pct(disc_mom)}pp'),
    ('O2O流水', money(o2o_v), '--', pct(o2o_mom)),
    ('SSSG', pct(sssg_v), pct(sssg_v), pct(mom_v)),
]

# Sub-PS for 服装子品类
sub_ps_rows = []
for rk in ['92','94','95','96','99','100','102','103','104']:
    if rk in d['sub_ps']:
        rd = d['sub_ps'][rk]; data = rd['data']
        label = rd['label']
        if label and data.get('8'):
            sub_ps_rows.append({'n':label,'f':float(data['8']),'d':float(data['10'])*100,'q':int(float(data['4'])),'isAcc':False})

# Shoe series  
shoe_rows = []
for rk in ['76','77','78','79','80','85','87']:
    if rk in d['shoe_series']:
        rd = d['shoe_series'][rk]; data = rd['data']
        label = rd['label']
        if label and data.get('8'):
            shoe_rows.append({'n':label,'f':float(data['8']),'q':int(float(data['4'])),'d':float(data['10'])*100})

# Acc sub-PS
acc_rows = []
for rk in ['115','116','117','120']:
    if rk in d['sub_ps']:
        rd = d['sub_ps'][rk]; data = rd['data']
        label = rd['label']
        if label and data.get('8'):
            sub_ps_rows.append({'n':label,'f':float(data['8']),'d':float(data['10'])*100,'q':int(float(data['4'])),'isAcc':True})

# Seasonal new product
seas_data = {}
if '5' in seas:
    r5 = seas['5']; r7s = seas.get('7',{}); r6s = seas.get('6',{})
    r19s = seas.get('19',{}); r25s = seas.get('25',{})
    for ck, lbl in [('4','2025Q4及以前(服)'),('6','2026Q1(服)'),('8','2026Q2(服)'),('10','2026Q3+(服)'),('13','26年常青(服)'),
                     ('15','2025Q4及以前(鞋)'),('18','2026Q1(鞋)'),('20','2026Q2(鞋)'),('22','2026Q3+(鞋)'),('25','26年常青(鞋)')]:
        if ck in r5:
            seas_data[lbl] = {
                'f': float(r5.get(ck,0)),
                'd': float(r7s.get(ck,0))*100 if ck in r7s else 0,
                'q': int(float(r6s.get(ck,0))) if ck in r6s else 0,
                'su': float(r19s.get(ck,0))*100 if ck in r19s else 0,
                'sat': float(r25s.get(ck,0))*100 if ck in r25s else 0,
            }

# Member extraction
member_rows = []
mem = d.get('member', {})
for rk, rd in mem.items():
    if rk in ['2','4','5','6']: continue
    data = rd
    name = data.get('3','')
    sales = data.get('9', 0)
    if name and sales and float(sales) > 0:
        member_rows.append({
            'id': str(data.get('1','')),
            'name': str(name),
            'sales': float(sales),
            'qty': int(float(data.get('10', 0))),
            'unitPrice': float(data.get('11', 0)),
            'avgTicket': float(data.get('12', 0)),
            'attach': float(data.get('13', 0)),
            'shoePct': float(data.get('15', 0))*100 if data.get('15') else 0,
            'clothPct': float(data.get('16', 0))*100 if data.get('16') else 0,
            'o2o': float(data.get('17', 0)) if data.get('17') else 0,
        })

# ───────── build JSON payload for HTML ─────────
# Extract MTD/YTD/Regional from JSON with named keys matching DATA object
def to_num(v):
    """Safely convert to float, returns 0 for '/' or other non-numeric values"""
    if v is None or str(v).strip() in ('','/','-','N/A'):
        return 0
    return float(v)

def bench_row(row_data):
    return {
        'conv': to_num(row_data.get('5', 0))*100,
        'flow': to_num(row_data.get('8', 0)),
        'target': to_num(row_data.get('14', 0)),
        'actual': to_num(row_data.get('17', 0)),
        'achieve': to_num(row_data.get('20', 0))*100,
        'sssg': to_num(row_data.get('24', 0))*100 if '24' in row_data else to_num(row_data.get('22', 0))*100,
        'mom': to_num(row_data.get('28', 0))*100,
    }
mtd_data = bench_row(d.get('r8_month', {}))
ytd_data = bench_row(d.get('r9_year', {}))
reg_data = bench_row(d.get('r10_week', {}))

# Extract discount/order range from extracted_data
disc_range_data = {}
if 'discount_range' in d:
    for rk, row in d['discount_range'].items():
        label = str(row.get('label', ''))
        cols = {}
        raw = row.get('data', {})
        for ck, cv in raw.items():
            try: cols[ck] = float(cv)
            except (ValueError, TypeError): cols[ck] = cv
        disc_range_data[rk] = {'label': label, 'cols': cols}

payload = {
    'store': store, 'period': period, 'week_range': week_range,
    'target': target_v, 'actual': actual_v, 'achieve': achieve_v, 'yoy': yoy_v,
    'mom': mom_v, 'sssg': sssg_v, 'conv': conv_v, 'flow': flow_v,
    'avg_t': avg_t, 'unit_p': unit_p, 'attach_r': attach_r, 'disc': disc_v,
    'o2o': o2o_v, 'o2o_pct': o2o_pct, 'tkt_cnt': tkt_cnt, 'pad': pad_v, 'o2o_online': o2o_online,
    'conv_yoy': conv_yoy, 'flow_yoy': flow_yoy, 'avg_t_yoy': avg_t_yoy,
    'attach_yoy': attach_yoy, 'unit_yoy': unit_yoy, 'disc_yoy_p': disc_yoy_p, 'disc_mom': disc_mom,
    'o2o_mom': o2o_mom, 'conv_mom': conv_mom, 'flow_mom': flow_mom,
    'daily': daily_rows,
    'category': cat_data,
    'matrix': matrix,
    'top': top_data,
    'sub_ps': sub_ps_rows, 'shoe': shoe_rows,
    'seas': seas_data, 'disc_range': disc_range_data, 'member': member_rows,
    'shoe_share': cat_data['鞋']['f_share'],
    'shoe_sku_u': cat_data['鞋']['sku_u'],
    'shoe_per_sku': cat_data['鞋']['flow'] / cat_data['鞋']['sku_s'] if cat_data['鞋']['sku_s'] else 0,
    'acc_per_sku': cat_data['配件']['flow'] / cat_data['配件']['sku_s'] if cat_data['配件']['sku_s'] else 0,
    'total_stock_qty': total_sq,
    'shoe_s_qty': cat_data['鞋']['s_qty'],
    'shoe_s_sku': cat_data['鞋']['s_sku'],
    'mtd': mtd_data, 'ytd': ytd_data, 'reg': reg_data,
}

# ───────── HTML generation ─────────
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>W23 周报分析仪表板 | {store}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
<style>
:root{{--bg:#f0f2f5;--card:#fff;--text:#1e293b;--sub:#64748b;--border:#e2e8f0;
--red:#ef4444;--green:#22c55e;--blue:#3b82f6;--amber:#f59e0b;--purple:#8b5cf6;
--red-bg:#fef2f2;--green-bg:#f0fdf4;--blue-bg:#eff6ff;--amber-bg:#fffbeb;}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--text);font-size:14px;line-height:1.6}}
.app{{max-width:1300px;margin:0 auto;padding:0 16px 40px}}

/* Header */
.header{{background:linear-gradient(135deg,#0f172a,#1e293b);color:white;padding:18px 28px;border-radius:0 0 14px 14px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;position:sticky;top:0;z-index:100;margin-bottom:12px;}}
.header h1{{font-size:20px;font-weight:700}}
.header .meta{{font-size:12px;opacity:.75}}
.header .actions{{display:flex;gap:8px}}
.header .btn{{padding:6px 14px;border-radius:6px;border:none;cursor:pointer;font-size:12px;font-weight:600;transition:.2s}}
.btn-outline{{background:transparent;border:1px solid rgba(255,255,255,.3);color:white}}
.btn-outline:hover{{background:rgba(255,255,255,.1)}}
.btn-primary{{background:var(--blue);color:white}}
.btn-primary:hover{{background:#2563eb}}

/* Sticky KPI */
.kpi-strip{{position:sticky;top:72px;z-index:99;background:var(--card);border-radius:12px;padding:12px 20px;display:flex;gap:12px;flex-wrap:wrap;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:16px;border:1px solid var(--border)}}
.kpi-strip .ki{{flex:1;min-width:100px;text-align:center;padding:8px 6px;border-radius:8px;background:#f8fafc}}
.kpi-strip .ki .kv{{font-size:22px;font-weight:800}}
.kpi-strip .ki .kl{{font-size:11px;color:var(--sub);margin-top:2px}}
.kpi-strip .ki .kc{{font-size:12px;font-weight:600;margin-top:1px}}
.up{{color:var(--red)}}.down{{color:var(--green)}}.neutral{{color:var(--sub)}}
.tag-up{{background:var(--red-bg);color:#991b1b;padding:1px 8px;border-radius:12px;font-size:11px}}
.tag-down{{background:var(--green-bg);color:#065f46;padding:1px 8px;border-radius:12px;font-size:11px}}
.tag-neutral{{background:#f1f5f9;color:#475569;padding:1px 8px;border-radius:12px;font-size:11px}}

/* Tabs */
.tabs{{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:12px}}
.tab{{padding:8px 18px;border-radius:8px 8px 0 0;cursor:pointer;font-size:13px;font-weight:600;color:var(--sub);background:transparent;border:none;border-bottom:2px solid transparent;transition:.2s}}
.tab.active{{color:var(--blue);border-bottom-color:var(--blue);background:var(--blue-bg)}}
.tab:hover:not(.active){{color:var(--text);background:#f8fafc}}

/* Cards */
.section{{background:var(--card);border-radius:12px;padding:22px 26px;margin-bottom:14px;border:1px solid var(--border);box-shadow:0 1px 3px rgba(0,0,0,.04)}}
.section h3{{font-size:16px;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px}}
.chart-wrap{{position:relative;width:100%;max-height:350px}}
.chart-wrap canvas{{width:100%!important}}

/* Grids */
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}
@media(max-width:900px){{.grid2,.grid3{{grid-template-columns:1fr}}}}

/* Table */
.tbl{{width:100%;border-collapse:collapse;font-size:12.5px}}
.tbl th{{background:#f1f5f9;padding:8px 10px;text-align:center;font-weight:600;color:var(--sub);border-bottom:2px solid var(--border);font-size:11px}}
.tbl td{{padding:7px 10px;text-align:center;border-bottom:1px solid var(--border)}}
.tbl tr:nth-child(even){{background:#fafbfc}}
.tbl td:first-child,.tbl th:first-child{{text-align:left;font-weight:600}}
.tbl .hi{{color:var(--red);font-weight:700}}
.tbl .lo{{color:var(--green);font-weight:700}}

/* Filters */
.filters{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px;padding:10px 14px;background:#f8fafc;border-radius:8px}}
.filters select{{padding:6px 12px;border-radius:6px;border:1px solid var(--border);background:white;font-size:13px;cursor:pointer}}
.filters label{{font-size:12px;color:var(--sub);font-weight:600}}

/* Problem/Opp cards */
.pc{{border-left:4px solid var(--red);background:var(--red-bg);border-radius:8px;padding:14px 18px;margin-bottom:10px;transition:.2s}}
.oc{{border-left:4px solid var(--green);background:var(--green-bg);border-radius:8px;padding:14px 18px;margin-bottom:10px;transition:.2s}}
.pc:hover,.oc:hover{{box-shadow:0 2px 8px rgba(0,0,0,.08)}}
.pc .phead,.oc .ohead{{display:flex;align-items:center;gap:10px;cursor:pointer}}
.pc .pnum,.oc .onum{{width:26px;height:26px;border-radius:50%;color:white;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:13px;flex-shrink:0}}
.pc .pnum{{background:var(--red)}}.oc .onum{{background:var(--green)}}
.pc h4,.oc h4{{font-size:15px;margin:0}}
.pbody,.obody{{margin-top:10px;padding-top:10px;border-top:1px solid rgba(0,0,0,.1);line-height:1.7;font-size:13px}}
.pbody .loss-tag{{display:inline-block;background:#fecaca;padding:2px 8px;border-radius:4px;font-weight:700;color:#7f1d1d;font-size:12px;margin-bottom:8px}}
.dbox{{background:white;border-radius:6px;padding:10px 14px;margin:8px 0;font-size:12px}}
.dbox td{{padding:2px 10px 2px 0}}

/* Toggle */
.toggle-icon{{transition:transform .2s;font-size:12px}}
.pc.open .toggle-icon,.oc.open .toggle-icon{{transform:rotate(90deg)}}
.pc:not(.open) .pbody,.oc:not(.open) .obody{{display:none}}

/* Highlight box */
.highlight{{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-radius:8px;padding:12px 16px;margin:10px 0;font-size:13px}}
.summary-box{{background:linear-gradient(135deg,#0f172a,#1e293b);color:white;border-radius:12px;padding:20px 26px;margin-top:16px}}

/* Full text */
.full-text{{background:#fafbfc;border-radius:8px;padding:18px 22px;font-size:13px;line-height:1.9;white-space:pre-wrap;max-height:60vh;overflow-y:auto}}

.footer{{text-align:center;padding:20px;color:var(--sub);font-size:11px}}

/* Toast & Import */
.toast{{position:fixed;top:20px;right:20px;z-index:9999;padding:12px 20px;border-radius:8px;color:white;font-weight:600;font-size:13px;box-shadow:0 4px 12px rgba(0,0,0,.15);animation:slideIn .3s ease;display:none}}
.toast.success{{background:var(--green)}}.toast.error{{background:var(--red)}}.toast.info{{background:var(--blue)}}
.toast.show{{display:block}}
@keyframes slideIn{{from{{transform:translateX(100%);opacity:0}}to{{transform:translateX(0);opacity:1}}}}
.btn-primary.loading{{opacity:.7;pointer-events:none}}
.btn-primary.loading::after{{content:'...';animation:dots 1s infinite}}
@keyframes dots{{0%,20%{{content:'.'}}40%{{content:'..'}}60%{{content:'...'}}80%,100%{{content:''}}}}
</style>
</head>
<body>
<div class="app" id="app">

<div class="toast" id="toast"></div>

<div class="header">
  <div><h1>📊 W23 周报分析仪表板</h1><div class="meta">{store} | {week_range}</div></div>
  <div class="actions">
    <button class="btn btn-primary" id="btnImport" onclick="triggerImport()">📥 导入周报</button>
    <button class="btn btn-outline" onclick="refreshAllCharts()">🔄 刷新图表</button>
    <input type="file" id="fileInput" accept=".xlsx,.xls" style="display:none" onchange="handleFileImport(event)">
  </div>
</div>

<!-- STICKY KPI STRIP -->
<div class="kpi-strip" id="kpiStrip">
  <div class="ki"><div class="kv" style="color:{'#22c55e' if achieve_v>=100 else '#ef4444'}">{pa(achieve_v,1)}</div><div class="kl">达成率</div><div class="kc {'up' if achieve_v>=100 else 'down'}">{'超目标' if achieve_v>=100 else '未达标'}</div></div>
  <div class="ki"><div class="kv">{actual_v/10000:.1f}万</div><div class="kl">周流水</div><div class="kc down">{pct(yoy_v,1)}</div></div>
  <div class="ki"><div class="kv" style="color:{'#ef4444' if yoy_v<0 else '#22c55e'}">{pct(yoy_v,1)}</div><div class="kl">SSSG</div><div class="kc {'up' if yoy_v>0 else 'down'}">同比</div></div>
  <div class="ki"><div class="kv">{pa(conv_v,1)}</div><div class="kl">成交率</div><div class="kc {'up' if conv_yoy>0 else 'down'}">{pct(conv_yoy,1)}pp</div></div>
  <div class="ki"><div class="kv">{money(avg_t)}</div><div class="kl">客单价</div><div class="kc {'up' if avg_t_yoy>0 else 'down'}">{pct(avg_t_yoy,1)}</div></div>
  <div class="ki"><div class="kv">{f2(attach_r)}件</div><div class="kl">连带率</div><div class="kc {'up' if attach_yoy>0 else 'down'}">{pct(attach_yoy,1)}</div></div>
  <div class="ki"><div class="kv">{pa(cat_data['鞋']['f_share'],1)}</div><div class="kl">鞋占比</div><div class="kc down">{pct(cat_data['鞋']['yoy'],1)}</div></div>
  <div class="ki"><div class="kv">{money(o2o_v)}</div><div class="kl">O2O</div><div class="kc {'up' if o2o_mom>0 else 'down'}">{pct(o2o_mom,1)}</div></div>
  <div class="ki"><div class="kv">{pa(disc_v,1)}</div><div class="kl">折扣率</div><div class="kc {'up' if disc_yoy_p>0 else 'down'}">{pct(disc_yoy_p,1)}pp</div></div>
  <div class="ki"><div class="kv">{num(flow_v)}人</div><div class="kl">日均客流</div><div class="kc {'up' if flow_yoy>0 else 'down'}">{pct(flow_yoy,1)}</div></div>
</div>

<!-- ─── SECTION 2: DATA FILTERING ─── -->
<div class="section">
  <h3>📊 数据筛选展示</h3>
  <div class="tabs">
    <button class="tab active" onclick="switchDataTab('daily')">日别趋势</button>
    <button class="tab" onclick="switchDataTab('matrix')">KPI矩阵</button>
    <button class="tab" onclick="switchDataTab('cate')">品类分析</button>
    <button class="tab" onclick="switchDataTab('top')">TOP集中度</button>
    <button class="tab" onclick="switchDataTab('seas')">新品季节</button>
    <button class="tab" onclick="switchDataTab('sub')">子品类</button>
  </div>

  <!-- DATA TAB CONTENTS -->
  <div id="tab-daily" class="data-tab">
    <div class="grid2">
      <div class="chart-wrap"><canvas id="chartDailyFlow"></canvas></div>
      <div class="chart-wrap"><canvas id="chartDailyRate"></canvas></div>
    </div>
    <div class="grid2" style="margin-top:14px">
      <div class="chart-wrap"><canvas id="chartDailyTicket"></canvas></div>
      <div class="chart-wrap"><canvas id="chartDailyAttach"></canvas></div>
    </div>
    <table class="tbl" style="margin-top:14px">
      <thead><tr><th>日期</th><th>目标</th><th>实际流水</th><th>达成率</th><th>同比</th><th>成交率</th><th>客流</th><th>客单价</th><th>连带率</th></tr></thead>
      <tbody id="dailyTable"></tbody>
    </table>
  </div>

  <div id="tab-matrix" class="data-tab" style="display:none">
    <table class="tbl">
      <thead><tr><th>指标</th><th>本周值</th><th>同比</th><th>环比</th><th>趋势</th></tr></thead>
      <tbody id="matrixTable"></tbody>
    </table>
  </div>

  <div id="tab-cate" class="data-tab" style="display:none">
    <div class="grid2">
      <div class="chart-wrap"><canvas id="chartCateFlow"></canvas></div>
      <div class="chart-wrap"><canvas id="chartCateMatch"></canvas></div>
    </div>
    <table class="tbl" style="margin-top:14px">
      <thead><tr><th>品类</th><th>流水</th><th>销售占比</th><th>同比</th><th>环比</th><th>折扣率</th><th>SKU在售</th><th>SKU动销率</th><th>库存数量</th><th>库存占比</th><th>匹配分析</th></tr></thead>
      <tbody id="cateTable"></tbody>
    </table>
  </div>

  <div id="tab-top" class="data-tab" style="display:none">
    <div class="chart-wrap" style="max-height:300px"><canvas id="chartTop"></canvas></div>
    <table class="tbl" style="margin-top:14px">
      <thead><tr><th>层级</th><th>销量占比</th><th>流水占比</th><th>库存金额占比</th><th>可满足率</th></tr></thead>
      <tbody id="topTable"></tbody>
    </table>
  </div>

  <div id="tab-seas" class="data-tab" style="display:none">
    <div class="grid2">
      <div class="chart-wrap"><canvas id="chartSeasFlow"></canvas></div>
      <div class="chart-wrap"><canvas id="chartSeasRate"></canvas></div>
    </div>
    <table class="tbl" style="margin-top:14px">
      <thead><tr><th>季节</th><th>流水</th><th>数量</th><th>折扣率</th><th>SKU动销率</th><th>可满足率</th></tr></thead>
      <tbody id="seasTable"></tbody>
    </table>
  </div>

  <div id="tab-sub" class="data-tab" style="display:none">
    <div class="grid3">
      <div>
        <h4 style="font-size:13px;margin-bottom:8px;color:var(--sub)">服装子品类</h4>
        <table class="tbl"><thead><tr><th>品类</th><th>流水</th><th>折扣</th></tr></thead><tbody id="subCloth"></tbody></table>
      </div>
      <div>
        <h4 style="font-size:13px;margin-bottom:8px;color:var(--sub)">鞋系列</h4>
        <table class="tbl"><thead><tr><th>系列</th><th>流水</th><th>销量</th><th>折扣</th></tr></thead><tbody id="subShoe"></tbody></table>
      </div>
      <div>
        <h4 style="font-size:13px;margin-bottom:8px;color:var(--sub)">配件子品类</h4>
        <table class="tbl"><thead><tr><th>品类</th><th>流水</th><th>折扣</th></tr></thead><tbody id="subAcc"></tbody></table>
      </div>
    </div>
  </div>

  <div id="tab-bench" class="data-tab" style="display:none">
    <table class="tbl">
      <thead><tr><th>指标</th><th>本周</th><th>月累计(06月)</th><th>vs本周</th><th>年累计(YTD)</th><th>vs本周</th><th>区域均值(19店)</th><th>vs本周</th></tr></thead>
      <tbody id="benchTable"></tbody>
    </table>
  </div>
</div>

<!-- ─── SECTION 3: SMART ANALYSIS ─── -->
<div class="section">
  <h3>🤖 智能分析</h3>
  <div class="tabs">
    <button class="tab active" onclick="switchAnalysisTab('problems')">🔴 关键问题 (6)</button>
    <button class="tab" onclick="switchAnalysisTab('opps')">🟢 改善机会 (6)</button>
    <button class="tab" onclick="switchAnalysisTab('fulltext')">📝 完整分析稿</button>
  </div>

  <div id="tab-problems" class="analysis-tab" style="display:block">
    <div class="pc open" onclick="toggleCard(this)">
      <div class="phead"><span class="pnum">1</span><h4>整体流水同比暴跌-31.62% — 业绩断崖式下滑</h4><span class="toggle-icon">▶</span></div>
      <div class="pbody">
        <span class="loss-tag">周流水同比流失 ≈ ¥50,198</span>
        <div class="dbox">
          本周流水 <b>¥{actual_v:,.0f}</b> | 同比 <b style="color:var(--red)">{pct(yoy_v,2)}</b> | 达成率 <b>{pa(achieve_v,2)}</b><br>
          成交率 <b>{pa(conv_v,2)}</b>（同比-8.37pp） | 客单价 <b>¥{avg_t:,.0f}</b>（同比-14.1%） | 连带率 <b>{f2(attach_r)}</b>（同比-14.4%）<br>
          <span style="color:var(--sub);font-size:11px">若恢复去年同期：周流水应达 ¥{actual_v/(1+yoy_v/100):,.0f}</span>
        </div>
        <b>根因：</b>折扣持续加深（44.1%/+2.8pp）但流水反降，说明不是价格问题而是客流质量和产品吸引力下降；成交率从26.5%降至18.1%，每100人进店少成交8人。
      </div>
    </div>

    <div class="pc open" onclick="toggleCard(this)">
      <div class="phead"><span class="pnum">2</span><h4>周六崩盘 — 达成率仅51.69%，单日损失 ¥{26280.1-13584.82:,.0f}</h4><span class="toggle-icon">▶</span></div>
      <div class="pbody">
        <span class="loss-tag">预估损失 ≈ ¥{26280.10-13584.82:,.0f}</span>
        <div class="dbox">
          周六目标 ¥{daily_rows[5]['t']:,.0f} → 实际 <b style="color:var(--red)">¥{daily_rows[5]['f']:,.0f}</b> | 达成 <b style="color:var(--red)">{pa(daily_rows[5]['a'],1)}</b> | 同比 <b style="color:var(--red)">{pct(daily_rows[5]['y'],1)}</b><br>
          客流量 {daily_rows[5]['v']}人 | 成交率 {pa(daily_rows[5]['c'],1)} | 客单价 ¥{daily_rows[5]['tk']:,.0f}
        </div>
        <b>根因：</b>周六目标设定过高（工作日目标的2.5倍）；客流仅198人（不及周日343人的60%）；客单价¥{daily_rows[5]['tk']:,.0f}、连带率{daily_rows[5]['at']:.2f}均低于周四峰值。
      </div>
    </div>

    <div class="pc open" onclick="toggleCard(this)">
      <div class="phead"><span class="pnum">3</span><h4>所有品类同比全面下挫 — 鞋类{pct(cat_data['鞋']['yoy'],1)}最严重</h4><span class="toggle-icon">▶</span></div>
      <div class="pbody">
        <span class="loss-tag">四品类无一幸免，鞋类环比{pct(cat_data['鞋']['mom'],1)}加速恶化</span>
        <div class="dbox">
          男装{pct(cat_data['男装']['yoy'],1)} | 女装{pct(cat_data['女装']['yoy'],1)} | 鞋{pct(cat_data['鞋']['yoy'],1)} | 配件{pct(cat_data['配件']['yoy'],1)}<br>
          鞋SKU动销率仅{pa(cat_data['鞋']['sku_u'],1)}，64%鞋SKU一周0动销；配件每SKU产出{money(cat_data['配件']['flow']/cat_data['配件']['sku_s'])}
        </div>
        <b>根因：</b>鞋类作为核心品类失速最严重，124个在售SKU中大量躺平；四品类折扣率均在43-45%区间，同质化打折无法形成差异化。
      </div>
    </div>

    <div class="pc" onclick="toggleCard(this)">
      <div class="phead"><span class="pnum">4</span><h4>客单价与连带率双降 — 低客单、低效率交易驱动</h4><span class="toggle-icon">▶</span></div>
      <div class="pbody">
        <span class="loss-tag">若客单价恢复至¥600，周增量 ≈ ¥{600*tkt_cnt-actual_v:,.0f}</span>
        <div class="dbox">
          客单价 ¥{avg_t:,.0f}（同比-14.1%） | 连带率 {f2(attach_r)}件（同比-14.4%） | 件单价 ¥{unit_p:,.0f}（基本持平）<br>
          客单价下降 = 连带率从4.57降至3.91（-14.4%）× 件单价持平 → <b>连带效率下降是主因</b>
        </div>
        <b>根因：</b>每笔少卖0.66件，导购推荐和搭配销售能力下降；周末客流多但连带反而差（周六3.54/周日3.39）；折扣环境导致顾客倾向买单件折扣品而非多件搭配。
      </div>
    </div>

    <div class="pc" onclick="toggleCard(this)">
      <div class="phead"><span class="pnum">5</span><h4>折扣率{pa(disc_v,1)}持续走高 — 越打折越卖不动</h4><span class="toggle-icon">▶</span></div>
      <div class="pbody">
        <span class="loss-tag">折扣率环比{pct(disc_mom,1)}pp但流水环比{pct(mom_v,1)}</span>
        <div class="dbox">
          综合折扣{pa(disc_v,1)}（约5.6折）| 同比{disc_yoy_p:+.2f}pp | 环比{disc_mom:+.2f}pp<br>
          折扣加深→流水反降→继续加深折扣的恶性循环正在形成
        </div>
        <b>根因：</b>44.1%折扣在奥莱体系中也属偏高；顾客对"奥莱=常年打折"形成预期，非打折商品难以动销；同行竞争压力迫使持续让利但效果递减。
      </div>
    </div>

    <div class="pc" onclick="toggleCard(this)">
      <div class="phead"><span class="pnum">6</span><h4>新品表现乏力 — 26年常青款折扣率{pa(seas_data.get('26年常青(服)',{}).get('d',0),1)}、动销率低</h4><span class="toggle-icon">▶</span></div>
      <div class="pbody">
        <span class="loss-tag">26年常青(服)折扣{pa(seas_data.get('26年常青(服)',{}).get('d',0),1)}，动销率{pa(seas_data.get('26年常青(服)',{}).get('su',0),1)}</span>
        <div class="dbox">
          2026Q2(服)折扣{pa(seas_data.get('2026Q2(服)',{}).get('d',0),1)}（约4折），当季新品也需大幅让利<br>
          新品可满足率仅2-6%，新品备货极度保守
        </div>
        <b>根因：</b>新品即打折→新品价值感知弱→不敢深库存→不敢推→卖不动→继续打折的恶性循环。
      </div>
    </div>
  </div>

  <div id="tab-opps" class="analysis-tab" style="display:none">
    <div class="oc" onclick="toggleCard(this)">
      <div class="ohead"><span class="onum">1</span><h4>周六复苏攻坚 — 夺回单日 ¥{26280.1-13584.82:,.0f} 增量</h4><span class="toggle-icon">▶</span></div>
      <div class="obody">
        <b>目标：</b>周六达成率从51.69%恢复至80%+<br>
        <b>方案A — 周五预锁定：</b>周五晚场推"周六专属券：满399-30（限前30单）"，企微+短信推送近30天消费会员<br>
        <b>方案B — 周六社交引流：</b>"带朋友到店各减¥20"裂变活动<br>
        <b>方案C — 排班优化：</b>周六14-18点最强导购值守高价值区域，设单日客单价PK奖
      </div>
    </div>

    <div class="oc" onclick="toggleCard(this)">
      <div class="ohead"><span class="onum">2</span><h4>流量激活：成交率从18.1%提升至22%</h4><span class="toggle-icon">▶</span></div>
      <div class="obody">
        <b>目标：</b>提升成交率4pp，周增流水≈¥{((0.22-0.1812)*(flow_v*7)*avg_t):,.0f}<br>
        <b>方案A — 进店话术：</b>"欢迎光临，今天鞋/服装新品到店，您可以先看看"<br>
        <b>方案B — 试穿激励：</b>"试穿3件以上送品牌袜子一双"<br>
        <b>方案C — 加价购：</b>结账时推"加¥59换购指定T恤"
      </div>
    </div>

    <div class="oc" onclick="toggleCard(this)">
      <div class="ohead"><span class="onum">3</span><h4>鞋类SKU瘦身+爆款深耕 — 动销率{pa(cat_data['鞋']['sku_u'],1)}→50%+</h4><span class="toggle-icon">▶</span></div>
      <div class="obody">
        <b>目标：</b>鞋SKU动销率从{pa(cat_data['鞋']['sku_u'],1)}提升至50%+<br>
        <b>方案A — 断舍离：</b>筛查连续2周0动销鞋SKU申请调出<br>
        <b>方案B — TOP20深耕：</b>锁定TOP20鞋款加库存深度（满足率36.5%→50%+）<br>
        <b>方案C — 配件同步：</b>{cat_data['配件']['sku_s']}个配件SKU清理0动销，每SKU产出{money(cat_data['配件']['flow']/cat_data['配件']['sku_s'])}→¥200+
      </div>
    </div>

    <div class="oc" onclick="toggleCard(this)">
      <div class="ohead"><span class="onum">4</span><h4>连带攻坚：从{f2(attach_r)}件拉升至4.5件</h4><span class="toggle-icon">▶</span></div>
      <div class="obody">
        <b>目标：</b>连带率提升0.6件，周流水增量≈¥{((4.5-attach_r)*tkt_cnt*unit_p):,.0f}<br>
        <b>方案A — "1+1+1"搭配法：</b>主推品+搭配品+连带品的完整Look推荐<br>
        <b>方案B — 鞋区旁陈列：</b>"买鞋+¥99换购指定短裤"跨界连带<br>
        <b>方案C — "连带王"奖：</b>单笔超4件¥10，超6件¥20，下班即兑现
      </div>
    </div>

    <div class="oc" onclick="toggleCard(this)">
      <div class="ohead"><span class="onum">5</span><h4>折扣管控：从{pa(disc_v,1)}控制到42%以内</h4><span class="toggle-icon">▶</span></div>
      <div class="obody">
        <b>目标：</b>综合折扣率控制在42%以内<br>
        <b>方案A — 新品保护期：</b>26年常青款前2周正价销售<br>
        <b>方案B — 满减替代直降：</b>"满599减60、满999减150"替代全场X折<br>
        <b>方案C — 品折扣中折：</b>鞋类保持折扣力度，服装适度收紧折扣
      </div>
    </div>

    <div class="oc" onclick="toggleCard(this)">
      <div class="ohead"><span class="onum">6</span><h4>O2O渠道发力 + 周日巩固</h4><span class="toggle-icon">▶</span></div>
      <div class="obody">
        <b>目标：</b>O2O从{money(o2o_v)}提升至¥8,000+（占比7%+）<br>
        <b>方案A — 周日会员维护：</b>周日流水¥{daily_rows[6]['f']:,.0f}是全周最强，保持不丢失<br>
        <b>方案B — PAD+官网同步推：</b>线下畅销款标注"线上同款可购"<br>
        <b>方案C — 周四模式复制：</b>周四达成127%/客单价¥{daily_rows[3]['tk']:,.0f}/连带{daily_rows[3]['at']:.2f}，分析成功因素复制到其他工作日
      </div>
    </div>
  </div>

  <div id="tab-fulltext" class="analysis-tab" style="display:none">
    <div class="full-text" id="fullTextContent"></div>
  </div>
</div>

<!-- Summary -->
<div class="summary-box">
  <h3 style="color:#fbbf24;margin-bottom:12px;">总结：六大问题的逻辑关系</h3>
  <p style="font-size:13px;line-height:2;opacity:.9">
    <span style="background:var(--red);padding:3px 12px;border-radius:20px;font-size:11px">P1 同比大跌</span> + 
    <span style="background:var(--red);padding:3px 12px;border-radius:20px;font-size:11px">P2 周六崩盘</span> → 客流端失血<br>
    <span style="background:var(--red);padding:3px 12px;border-radius:20px;font-size:11px">P3 品类全跌</span> + 
    <span style="background:var(--red);padding:3px 12px;border-radius:20px;font-size:11px">P5 折扣失控</span> → 品类端失血<br>
    <span style="background:var(--red);padding:3px 12px;border-radius:20px;font-size:11px">P4 客单/连带双降</span> + 
    <span style="background:var(--red);padding:3px 12px;border-radius:20px;font-size:11px">P6 新品乏力</span> → 效率端失血
  </p>
  <p style="font-size:14px;line-height:1.9;margin-top:12px;padding-top:12px;border-top:1px solid rgba(255,255,255,.2)">
    <strong style="color:#fca5a5;">三大失血点（客流 → 品类 → 效率）</strong>互为因果。<br>
    破解之道：<strong style="color:#86efac;">周六引流（P1/2）→ SKU瘦身+深耕（P3）→ 连带攻坚（P4）→ 折扣优化（P5）→ 新品策略+O2O（P6）</strong><br>
    六项措施联动落地，预计释放 <strong style="color:#fbbf24;">¥15,000-20,000/周</strong> 增量空间。
  </p>
</div>

<div class="footer">{store} | W23 周报分析仪表板 | EdgeOne Pages 部署 | AI店长出品</div>

</div>

<!-- ─── DATA PAYLOAD ─── -->
<script>
const DATA = {json.dumps(payload, ensure_ascii=False, default=str)};

// ─── TAB SWITCHING ───
function switchDataTab(name) {{
  document.querySelectorAll('.data-tab').forEach(e=>e.style.display='none');
  document.getElementById('tab-'+name).style.display='block';
  document.querySelectorAll('.section:first-of-type .tab').forEach(t=>t.classList.remove('active'));
  event.target.classList.add('active');
  if(name==='daily'){{ drawDailyCharts(); }}
  if(name==='cate'){{ drawCateCharts(); }}
  if(name==='top'){{ drawTopChart(); }}
  if(name==='seas'){{ drawSeasCharts(); }}
}}

function switchAnalysisTab(name) {{
  document.querySelectorAll('.analysis-tab').forEach(e=>e.style.display='none');
  document.getElementById('tab-'+name).style.display='block';
  document.querySelectorAll('.section:last-of-type .tab').forEach(t=>t.classList.remove('active'));
  event.target.classList.add('active');
}}

function toggleCard(el) {{
  if(window.event&&window.event.target){{var tg=window.event.target;if(tg.tagName==='BUTTON'||tg.tagName==='A')return;}}
  el.classList.toggle('open');
}}

// ─── RENDER TABLES ───
function initTables() {{
  const D=DATA;
  // Daily table
  let dt='';
  D.daily.forEach((r,i)=>{{
    const ach=r.a; const acls=ach<100?'hi':(ach>150?'hi':'');
    const ycls=r.y<0?'lo':'hi';
    dt+=`<tr><td>${{r.n}}</td><td>¥${{r.t.toLocaleString()}}</td><td>¥${{r.f.toLocaleString()}}</td>
    <td class="${{acls}}">${{ach.toFixed(1)}}%</td><td class="${{ycls}}">${{(r.y>0?'+':'')+r.y.toFixed(1)}}%</td>
    <td>${{r.c.toFixed(2)}}%</td><td>${{r.v}}</td><td>¥${{r.tk.toFixed(0)}}</td><td>${{r.at.toFixed(2)}}</td></tr>`;
  }});
  dt+=`<tr style="font-weight:700;background:#f1f5f9"><td>合计</td><td>¥${{D.target.toLocaleString()}}</td>
  <td>¥${{D.actual.toLocaleString()}}</td><td>${{D.achieve.toFixed(1)}}%</td>
  <td class="lo">${{D.yoy.toFixed(1)}}%</td><td>${{D.conv.toFixed(2)}}%</td>
  <td>${{D.flow.toFixed(0)}}</td><td>¥${{D.avg_t.toFixed(0)}}</td><td>${{D.attach_r.toFixed(2)}}</td></tr>`;
  document.getElementById('dailyTable').innerHTML=dt;

  // Matrix table
  let mt='';
  D.matrix.forEach(r=>{{
    mt+=`<tr><td>${{r[0]}}</td><td>${{r[1]}}</td><td class="${{r[2].includes('-')?'lo':'hi'}}">${{r[2]}}</td><td class="${{r[3].includes('-')?'lo':'hi'}}">${{r[3]}}</td><td><span class="${{r[2].includes('-')?'tag-down':'tag-up'}}">${{r[2].includes('-')?'⬇️':'⬆️'}}</span></td></tr>`;
  }});
  document.getElementById('matrixTable').innerHTML=mt;

  // Category table
  let ct='';
  for(const[cn,cd]of Object.entries(D.category)){{
    const mcls=cd.gap>5?'hi':(cd.gap<-5?'lo':'');
    ct+=`<tr><td>${{cn}}</td><td>¥${{cd.flow.toLocaleString()}}</td><td>${{cd.f_share.toFixed(2)}}%</td>
    <td class="lo">${{(cd.yoy>0?'+':'')+cd.yoy.toFixed(2)}}%</td><td class="lo">${{(cd.mom>0?'+':'')+cd.mom.toFixed(2)}}%</td>
    <td>${{cd.disc.toFixed(2)}}%</td><td>${{cd.sku_s}}</td><td>${{cd.sku_u.toFixed(2)}}%</td>
    <td>${{cd.s_qty.toLocaleString()}}</td><td>${{cd.s_q_share.toFixed(2)}}%</td><td class="${{mcls}}">${{cd.match_lbl}}</td></tr>`;
  }}
  document.getElementById('cateTable').innerHTML=ct;

  // TOP table
  let tt='';
  for(const[tn,td]of Object.entries(D.top)){{
    tt+=`<tr><td>${{tn}}</td><td>${{td['4'].toFixed(2)}}%</td><td>${{td['6'].toFixed(2)}}%</td><td>${{td['8'].toFixed(2)}}%</td><td>${{td['10'].toFixed(2)}}%</td></tr>`;
  }}
  document.getElementById('topTable').innerHTML=tt;

  // Season table
  let st='';
  for(const[sn,sd]of Object.entries(D.seas)){{
    st+=`<tr><td>${{sn}}</td><td>¥${{sd.f.toLocaleString()}}</td><td>${{sd.q}}</td><td>${{sd.d.toFixed(2)}}%</td><td>${{sd.su.toFixed(2)}}%</td><td>${{sd.sat.toFixed(2)}}%</td></tr>`;
  }}
  document.getElementById('seasTable').innerHTML=st;

  // Sub tables
  let sc=''; D.sub_ps.filter(r=>!r.isAcc).forEach(r=>{{ sc+='<tr><td>'+r.n+'</td><td>¥'+r.f.toLocaleString()+'</td><td>'+(r.d||0).toFixed(2)+'%</td></tr>'; }});
  document.getElementById('subCloth').innerHTML=sc;
  let ss=''; D.shoe.forEach(r=>{{ ss+='<tr><td>'+r.n+'</td><td>¥'+r.f.toLocaleString()+'</td><td>'+r.q+'</td><td>'+(r.d||0).toFixed(2)+'%</td></tr>'; }});
  document.getElementById('subShoe').innerHTML=ss||'<tr><td colspan="4">导入后解析</td></tr>';
  let sa=''; D.sub_ps.filter(r=>r.isAcc).forEach(r=>{{ sa+='<tr><td>'+r.n+'</td><td>¥'+r.f.toLocaleString()+'</td><td>'+(r.d||0).toFixed(2)+'%</td></tr>'; }});
  document.getElementById('subAcc').innerHTML=sa;

  // Bench table
  var bt='';
  var kmap=[{{k:'conv','n':'成交率','pct':1}},{{k:'flow','n':'日均客流'}},{{k:'target','n':'流水目标'}},{{k:'actual','n':'流水实际'}},{{k:'achieve','n':'达成率','pct':1}},{{k:'sssg','n':'同比%','pct':1}},{{k:'mom','n':'环比%','pct':1}}];
  kmap.forEach(function(item){{
    var w=D[item.k]!=null?D[item.k]:0;
    var m=D.mtd&&D.mtd[item.k]!=null?D.mtd[item.k]:0;
    var y=D.ytd&&D.ytd[item.k]!=null?D.ytd[item.k]:0;
    var r=D.reg&&D.reg[item.k]!=null?D.reg[item.k]:0;
    var fw=item.pct?w.toFixed(1)+'%':(w>=10000?'¥'+w.toLocaleString():'¥'+w.toFixed(0));
    var fm=item.pct?m.toFixed(1)+'%':(m>=10000?'¥'+m.toLocaleString():'¥'+m.toFixed(0));
    var fy=item.pct?y.toFixed(1)+'%':(y>=10000?'¥'+y.toLocaleString():'¥'+y.toFixed(0));
    var fr=item.pct?r.toFixed(1)+'%':(r>=10000?'¥'+r.toLocaleString():'¥'+r.toFixed(0));
    var dw=item.pct?(m-w).toFixed(1)+'pp':((m-w)>=0?'+':'')+(m-w).toFixed(0);
    var dy=item.pct?(y-w).toFixed(1)+'pp':((y-w)>=0?'+':'')+(y-w).toFixed(0);
    var dr=item.pct?(r-w).toFixed(1)+'pp':((r-w)>=0?'+':'')+(r-w).toFixed(0);
    bt+='<tr><td>'+item.n+'</td><td>'+fw+'</td><td>'+fm+'</td><td>'+dw+'</td><td>'+fy+'</td><td>'+dy+'</td><td>'+fr+'</td><td>'+dr+'</td></tr>';
  }});
  document.getElementById('benchTable').innerHTML=bt||'<tr><td colspan="8">导入后解析</td></tr>';

  // Full text
  document.getElementById('fullTextContent').innerHTML=`${{FULL_TEXT}}`;
}}

// ─── CHARTS ───
let chartInstances={{}};
function destroyChart(id){{ if(chartInstances[id]){{chartInstances[id].destroy();delete chartInstances[id];}} }}

const colors={{red:'#ef4444',green:'#22c55e',blue:'#3b82f6',amber:'#f59e0b',purple:'#8b5cf6',
  gray:'#94a3b8',redBg:'rgba(239,68,68,0.15)',greenBg:'rgba(34,197,94,0.15)',blueBg:'rgba(59,130,246,0.15)'}};

function drawDailyCharts() {{
  const D=DATA, labels=D.daily.map(r=>r.n);
  
  destroyChart('chartDailyFlow');
  chartInstances.chartDailyFlow = new Chart(document.getElementById('chartDailyFlow'),{{
    type:'bar', data:{{ labels, datasets:[
      {{ label:'目标', data:D.daily.map(r=>r.t), backgroundColor:colors.greenBg, borderColor:colors.green, borderWidth:1.5, borderRadius:4 }},
      {{ label:'实际流水', data:D.daily.map(r=>r.f), backgroundColor:colors.blueBg, borderColor:colors.blue, borderWidth:1.5, borderRadius:4 }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{display:true,text:'日别流水 (目标 vs 实际)',font:{{size:14}}}}, legend:{{position:'bottom'}} }},
      scales:{{ y:{{ ticks:{{ callback:v=>'¥'+v.toLocaleString()}} }} }}
    }}
  }});

  destroyChart('chartDailyRate');
  chartInstances.chartDailyRate = new Chart(document.getElementById('chartDailyRate'),{{
    type:'line', data:{{ labels, datasets:[
      {{ label:'达成率', data:D.daily.map(r=>r.a), borderColor:colors.blue, backgroundColor:'transparent', tension:0.3, pointRadius:4, pointBackgroundColor:colors.blue }},
      {{ label:'成交率', data:D.daily.map(r=>r.c), borderColor:colors.green, backgroundColor:'transparent', tension:0.3, pointRadius:4, pointBackgroundColor:colors.green, yAxisID:'y1' }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{display:true,text:'日别达成率 & 成交率',font:{{size:14}}}}, legend:{{position:'bottom'}} }},
      scales:{{ y:{{ position:'left',ticks:{{ callback:v=>v.toFixed(0)+'%'}},max:250 }}, y1:{{ position:'right',ticks:{{ callback:v=>v.toFixed(1)+'%'}},max:30,grid:{{drawOnChartArea:false}} }} }}
    }}
  }});

  destroyChart('chartDailyTicket');
  chartInstances.chartDailyTicket = new Chart(document.getElementById('chartDailyTicket'),{{
    type:'bar', data:{{ labels, datasets:[
      {{ label:'客单价 (¥)', data:D.daily.map(r=>r.tk), backgroundColor:[colors.amber+'40',colors.amber+'40',colors.amber+'40',colors.amber+'40',colors.amber+'40',colors.amber+'40',colors.amber+'40'], borderColor:colors.amber, borderWidth:1.5, borderRadius:4 }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{display:true,text:'日别客单价',font:{{size:14}}}}, legend:{{display:false}} }},
      scales:{{ y:{{ ticks:{{ callback:v=>'¥'+v.toLocaleString()}} }} }}
    }}
  }});

  destroyChart('chartDailyAttach');
  chartInstances.chartDailyAttach = new Chart(document.getElementById('chartDailyAttach'),{{
    type:'line', data:{{ labels, datasets:[
      {{ label:'连带率 (件)', data:D.daily.map(r=>r.at), borderColor:colors.red, backgroundColor:'transparent', tension:0.3, pointRadius:5, pointBackgroundColor:colors.red, fill:false }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{display:true,text:'日别连带率',font:{{size:14}}}}, legend:{{display:false}} }},
      scales:{{ y:{{ ticks:{{ callback:v=>v.toFixed(2)+'件'}}, min:Math.max(0,Math.min(...D.daily.map(r=>r.at))-1) }} }}
    }}
  }});
}}

function drawCateCharts() {{
  const D=DATA, cats=Object.keys(D.category);
  const flows=cats.map(c=>D.category[c].flow), yoys=cats.map(c=>D.category[c].yoy);
  const sShares=cats.map(c=>D.category[c].s_q_share), fShares=cats.map(c=>D.category[c].f_share);

  destroyChart('chartCateFlow');
  chartInstances.chartCateFlow = new Chart(document.getElementById('chartCateFlow'),{{
    type:'bar', data:{{ labels:cats, datasets:[
      {{ label:'流水', data:flows, backgroundColor:[colors.blueBg,colors.purple+'40',colors.redBg,colors.amber+'40'], borderColor:[colors.blue,colors.purple,colors.red,colors.amber], borderWidth:1.5, borderRadius:6, yAxisID:'y' }},
      {{ label:'同比%', data:yoys, type:'line', borderColor:colors.red, backgroundColor:'transparent', pointRadius:5, pointBackgroundColor:colors.red, yAxisID:'y1' }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{display:true,text:'品类流水 & 同比',font:{{size:14}}}}, legend:{{position:'bottom'}} }},
      scales:{{ y:{{ position:'left',ticks:{{ callback:v=>'¥'+v.toLocaleString()}} }}, y1:{{ position:'right',ticks:{{ callback:v=>v.toFixed(0)+'%'}},grid:{{drawOnChartArea:false}} }} }}
    }}
  }});

  destroyChart('chartCateMatch');
  chartInstances.chartCateMatch = new Chart(document.getElementById('chartCateMatch'),{{
    type:'bar', data:{{ labels:cats, datasets:[
      {{ label:'销售占比', data:fShares, backgroundColor:colors.blueBg, borderColor:colors.blue, borderWidth:1.5, borderRadius:4 }},
      {{ label:'库存占比(数量)', data:sShares, backgroundColor:colors.gray+'40', borderColor:colors.gray, borderWidth:1.5, borderRadius:4 }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{display:true,text:'品类销售占比 vs 库存数量占比',font:{{size:14}}}}, legend:{{position:'bottom'}} }},
      scales:{{ y:{{ ticks:{{ callback:v=>v.toFixed(0)+'%'}} }} }}
    }}
  }});
}}

function drawTopChart() {{
  const D=DATA, labels=Object.keys(D.top);
  const fShares=labels.map(l=>D.top[l]['6']), vShares=labels.map(l=>D.top[l]['4']);

  destroyChart('chartTop');
  chartInstances.chartTop = new Chart(document.getElementById('chartTop'),{{
    type:'bar', data:{{ labels, datasets:[
      {{ label:'流水占比', data:fShares, backgroundColor:colors.blueBg, borderColor:colors.blue, borderWidth:1.5, borderRadius:4 }},
      {{ label:'销量占比', data:vShares, backgroundColor:colors.greenBg, borderColor:colors.green, borderWidth:1.5, borderRadius:4 }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{display:true,text:'TOP商品集中度',font:{{size:14}}}}, legend:{{position:'bottom'}} }},
      scales:{{ y:{{ ticks:{{ callback:v=>v.toFixed(0)+'%'}},max:110 }} }}
    }}
  }});
}}

function drawSeasCharts() {{
  const D=DATA, labels=Object.keys(D.seas).slice(0,5); // clothing only
  const sLabels=Object.keys(D.seas);
  const flows=sLabels.map(s=>D.seas[s].f);

  destroyChart('chartSeasFlow');
  chartInstances.chartSeasFlow = new Chart(document.getElementById('chartSeasFlow'),{{
    type:'bar', data:{{ labels:sLabels, datasets:[
      {{ label:'流水', data:flows, backgroundColor:sLabels.map((_,i)=>i<5?colors.blueBg:colors.redBg), borderColor:sLabels.map((_,i)=>i<5?colors.blue:colors.red), borderWidth:1.5, borderRadius:4 }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false, indexAxis:'y',
      plugins:{{ title:{{display:true,text:'新品季节流水分布',font:{{size:14}}}} }},
      scales:{{ x:{{ ticks:{{ callback:v=>'¥'+v.toLocaleString()}} }} }}
    }}
  }});

  const discRates=sLabels.map(s=>D.seas[s].d);
  destroyChart('chartSeasRate');
  chartInstances.chartSeasRate = new Chart(document.getElementById('chartSeasRate'),{{
    type:'bar', data:{{ labels:sLabels, datasets:[
      {{ label:'折扣率%', data:discRates, backgroundColor:discRates.map(d=>d>50?colors.redBg:colors.amber+'40'), borderColor:discRates.map(d=>d>50?colors.red:colors.amber), borderWidth:1.5, borderRadius:4 }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false, indexAxis:'y',
      plugins:{{ title:{{display:true,text:'新品季节折扣率 (越低越健康)',font:{{size:14}}}} }},
      scales:{{ x:{{ ticks:{{ callback:v=>v.toFixed(0)+'%'}},max:120 }} }}
    }}
  }});
}}

function refreshAllCharts() {{
  Object.keys(chartInstances).forEach(k=>{{chartInstances[k].destroy();delete chartInstances[k];}});
  drawDailyCharts();
  const activeTab=document.querySelector('.data-tab[style*="block"]');
  if(activeTab&&activeTab.id==='tab-cate')drawCateCharts();
  if(activeTab&&activeTab.id==='tab-top')drawTopChart();
  if(activeTab&&activeTab.id==='tab-seas')drawSeasCharts();
}}

// Full text content
const FULL_TEXT=`<b>W23周报分析稿</b> | {store} | {week_range}

<b>一、周分析</b>

1、达成：本周目标¥{target_v/10000:.1f}万，实际¥{actual_v/10000:.1f}万，达成率{pa(achieve_v,2)}，超目标¥{(actual_v-target_v)/10000:.1f}万。但同比{pct(yoy_v,2)}，同店同比{pct(sssg_v,2)}，环比{pct(mom_v,2)}。达成率表面达标但增长质量堪忧。

2、成交率与客流：成交率{pa(conv_v,2)}（同比{pct(conv_yoy)}pp），日均客流{flow_v:.0f}人/天（同比{pct(flow_yoy)}），周客单量{tkt_cnt:.0f}笔。客流增长但成交率下降——"进店不买"问题突出。

3、客单价与连带：客单价¥{avg_t:,.0f}（同比{pct(avg_t_yoy,1)}），连带率{f2(attach_r)}件（同比{pct(attach_yoy,1)}），件单价¥{unit_p:,.0f}（同比{pct(unit_yoy,1)}）。客单价下降主要拖累是连带率下滑，每笔交易少卖约0.66件。

4、鞋类：流水¥{cat_data["鞋"]["flow"]/10000:.1f}万，占比{pa(cat_data["鞋"]["f_share"],1)}，同比{pct(cat_data["鞋"]["yoy"],1)}。SKU动销率仅{pa(cat_data["鞋"]["sku_u"],1)}，{cat_data["鞋"]["sku_s"]}个在售SKU中约64%一周0动销。

5、服装品类：男装¥{cat_data["男装"]["flow"]/10000:.1f}万（同比{pct(cat_data["男装"]["yoy"],1)}），女装¥{cat_data["女装"]["flow"]/10000:.1f}万（同比{pct(cat_data["女装"]["yoy"],1)}）。

6、配件：¥{cat_data["配件"]["flow"]/10000:.1f}万（同比{pct(cat_data["配件"]["yoy"],1)}，唯一环比微增{pct(cat_data["配件"]["mom"],1)}），但{cat_data["配件"]["sku_s"]}个在售SKU中动销率仅{pa(cat_data["配件"]["sku_u"],1)}，每SKU产出{money(cat_data["配件"]["flow"]/cat_data["配件"]["sku_s"])}。

7、日别结构：周一¥{daily_rows[0]["f"]/10000:.1f}万（达成{pa(daily_rows[0]["a"],1)}）→ 周二¥{daily_rows[1]["f"]/10000:.1f}万 → 周三¥{daily_rows[2]["f"]/10000:.1f}万 → 周四¥{daily_rows[3]["f"]/10000:.1f}万 → 周五¥{daily_rows[4]["f"]/10000:.1f}万（唯一同比正增{pct(daily_rows[4]["y"],1)}）→ <b>周六¥{daily_rows[5]["f"]/10000:.1f}万（达成{pa(daily_rows[5]["a"],1)}，全周最低）</b>→ 周日¥{daily_rows[6]["f"]/10000:.1f}万（达成{pa(daily_rows[6]["a"],1)}，全周最高）。

8、折扣率：{pa(disc_v,1)}（同比{disc_yoy_p:+.2f}pp、环比{disc_mom:+.2f}pp），约5.6折。折扣加深但流水下降，"打折拉销售"策略已失效。

9、线上O2O：¥{o2o_v/10000:.2f}万（占比{pa(o2o_pct,1)}，环比{pct(o2o_mom,1)}），O2O是少数增长亮点。

<b>二、本周重点改善策略</b>

1、周六复苏：周五企微推送"周六满399-30"券，设"老带新"裂变，周六14-18点最强导购值守。目标周六达成80%+。

2、成交率抢救（18%→22%）：进店三句话话术，试穿送袜子，收银台加价购。目标周增约¥12,000。

3、SKU瘦身+爆款深耕：筛查2周0动销SKU申请调出，锁定TOP20鞋款加库存深度。目标鞋动销率→50%+。

4、连带攻坚（3.91→4.5件）："1+1+1"搭配法，跨界连带陈列，"连带王"即时奖。目标周增约¥{(4.5-attach_r)*tkt_cnt*unit_p:,.0f}。

5、折扣管控（44%→42%）：新品首2周正价保护，满减替代直降，品类折扣分治。`;

// ─── IMPORT & PARSE EXCEL ───
function showToast(msg,type){{
  const t=document.getElementById('toast');
  t.textContent=msg; t.className='toast '+type+' show';
  setTimeout(()=>{{t.classList.remove('show');}},3000);
}}
function triggerImport(){{ document.getElementById('fileInput').click(); }}
function handleFileImport(e){{
  const file=e.target.files[0];
  if(!file) return;
  const btn=document.getElementById('btnImport');
  btn.classList.add('loading'); btn.disabled=true;
  showToast('正在解析 '+file.name+'...','info');
  const reader=new FileReader();
  reader.onload=function(ev){{
    try{{
      const wb=XLSX.read(ev.target.result,{{type:'array'}});
      const newData=parseExcelWorkbook(wb);
      if(!newData) throw new Error('无法识别周报格式');
      Object.assign(DATA,newData);
      document.querySelector('.header .meta').textContent=DATA.store+' | '+DATA.week_range;
      document.querySelector('.header h1').textContent='📊 '+DATA.period+' 周报分析仪表板';
      document.title=DATA.period+' 周报分析仪表板 | '+DATA.store;
      buildKpiStrip(); initTables(); refreshAllCharts(); renderAnalysis();
      document.querySelectorAll('.data-tab').forEach(e=>e.style.display='none');
      document.getElementById('tab-daily').style.display='block';
      const tabs=document.querySelectorAll('.section:first-of-type .tab');
      tabs.forEach(t=>t.classList.remove('active'));
      if(tabs[0]) tabs[0].classList.add('active');
      showToast('✅ 导入成功! '+DATA.store+' | '+DATA.week_range,'success');
    }}catch(err){{
      showToast('❌ 解析失败: '+err.message,'error');
      console.error(err);
    }}finally{{
      btn.classList.remove('loading'); btn.disabled=false;
      e.target.value='';
    }}
  }};
  reader.readAsArrayBuffer(file);
}}

function findRow(sheet,keyword,col){{
  col=col||1;
  for(let r=1;r<=250;r++){{
    const cell=sheet[XLSX.utils.encode_cell({{r:r-1,c:col-1}})];
    const v=cell&&cell.v!==undefined&&cell.v!==null?String(cell.v):'';
    if(v.includes(keyword)) return r;
  }}
  return 0;
}}

function parseExcelWorkbook(wb){{
  const sNames=wb.SheetNames;
  if(!sNames||sNames.length<1) throw new Error('工作薄为空');
  let wsMain=null, wsSeas=null, wsMember=null;
  for(let i=0;i<sNames.length;i++){{
    const s=wb.Sheets[sNames[i]], a4=s['A4']?s['A4'].v:null;
    if(a4==='KPI') wsMain=s;
    else if(wsMain&&!wsSeas&&findRow(s,'产品季',4)) wsSeas=s;
    else if(!wsMember&&findRow(s,'工号',1)>0) wsMember=s;
  }}
  if(!wsMain){{ for(let i=0;i<sNames.length;i++){{ if(!wsMain&&findRow(wb.Sheets[sNames[i]],'KPI',1)>0) wsMain=wb.Sheets[sNames[i]]; }} }}
  if(!wsMain) throw new Error('未找到周报数据表(KPI行)');
  function cv(s,r,c){{ const cell=s[XLSX.utils.encode_cell({{r:r-1,c:c-1}})]; if(!cell||cell.v===undefined||cell.v===null) return null; if(String(cell.v)==='#DIV/0!'||String(cell.v)==='/'||String(cell.v).includes('DIV')) return null; return cell.v; }}
  const kpiRow=findRow(wsMain,'KPI')||7;
  const priceRow=findRow(wsMain,'件单价')||(kpiRow+8);
  const dailyStart=kpiRow+14;
  const cateStart=findRow(wsMain,'吊牌价')||35;
  const clothStart=findRow(wsMain,'服装系列')||62;
  const shoeStart=findRow(wsMain,'鞋系列')||76;
  const subPsStart=findRow(wsMain,'裙类')||findRow(wsMain,'器配',4)||91;
  const topStart=findRow(wsMain,'TOP')||findRow(wsMain,'TOP商品')||123;
  const discStart=findRow(wsMain,'单件')||208;
  const store=cv(wsMain,2,1)||'未知店铺';
  const rawP=cv(wsMain,2,23)||''; const pM=rawP.match(/W(\\d+)/);
  const period=pM?pM[0]:'W??', weekRange=rawP.replace(/W\\d+周累计[：:]\\s*/,'').replace(/至/g,'-')||'';
  const r7={{}}; [4,5,6,7,8,10,12,14,17,20,22,24,28,33,35,36,37,39].forEach(c=>r7[c]=cv(wsMain,kpiRow,c));
  const r15={{}}; [4,6,8,10,12,14,16,18,20,22,24,28,30,32].forEach(c=>r15[c]=cv(wsMain,priceRow,c));
  const dayC=[4,6,8,10,12,14,16,18], dn=['周一','周二','周三','周四','周五','周六','周日'];
  const daily=[]; for(let i=0;i<7;i++) daily.push({{n:dn[i],t:cv(wsMain,dailyStart+0,dayC[i])||0,f:cv(wsMain,dailyStart+1,dayC[i])||0,a:(cv(wsMain,dailyStart+2,dayC[i])||0)*100,y:(cv(wsMain,dailyStart+3,dayC[i])||0)*100,c:(cv(wsMain,dailyStart+6,dayC[i])||0)*100,v:Math.round(cv(wsMain,dailyStart+7,dayC[i])||0),tk:cv(wsMain,dailyStart+8,dayC[i])||0,at:cv(wsMain,dailyStart+9,dayC[i])||0}});
  const catC={{'4':'男装','6':'女装','14':'鞋','16':'配件'}}; const catData={{}};
  for(const[col,nm]of Object.entries(catC)){{ const cn=parseInt(col); const f=cv(wsMain,cateStart+1,cn)||0; const ss=cv(wsMain,cateStart+12,cn)||0; catData[nm]={{flow:f,qty:cv(wsMain,cateStart+2,cn)||0,disc:(cv(wsMain,cateStart+3,cn)||0)*100,yoy:(cv(wsMain,cateStart+7,cn)||0)*100,mom:(cv(wsMain,cateStart+5,cn)||0)*100,f_share:(cv(wsMain,cateStart+9,cn)||0)*100,sku_s:ss,s_qty:cv(wsMain,cateStart+17,cn)||0,s_sku:cv(wsMain,cateStart+18,cn)||0,sku_u:(cv(wsMain,cateStart+15,cn)||0)*100,sat:(cv(wsMain,cateStart+21,cn)||0)*100,st:(cv(wsMain,cateStart+22,cn)||0)*100}}; }}
  const tsq=Object.values(catData).reduce((s,c)=>s+(c.s_qty||0),0);
  for(const[nm,cd]of Object.entries(catData)){{ const sqs=tsq>0?(cd.s_qty/tsq*100):0,fs=cd.f_share; cd.s_q_share=sqs; cd.gap=fs-sqs; cd.match_lbl=Math.abs(fs-sqs)<=5?'匹配':(fs>sqs?'销>库+'+((fs-sqs).toFixed(1))+'pp':'库>销'+((sqs-fs).toFixed(1))+'pp'); }}
  const topData={{}}; const tl={{'0':'TOP10','1':'TOP20','2':'TOP40','3':'TOP60','4':'TOP100'}};
  for(let i=0;i<5;i++){{ const r=topStart+i,d4=cv(wsMain,r,4),d6=cv(wsMain,r,6); if(d4!==null||d6!==null) topData[tl[String(i)]]={{'4':(d4||0)*100,'6':(d6||0)*100,'8':(cv(wsMain,r,8)||0)*100,'10':(cv(wsMain,r,10)||0)*100,'13':(cv(wsMain,r,13)||0)*100}}; }}
  const subPs=[]; let inSubPs=false, inAcc=false;
  for(let r=subPsStart;r<=subPsStart+40&&r<=180;r++){{
    const label=cv(wsMain,r,1); const flow=cv(wsMain,r,8);
    if(label==='合计'&&inSubPs&&!inAcc){{ inAcc=true; continue; }}
    if(label==='合计'&&inAcc) break;
    if(label&&flow&&Number(flow)&&!String(label).includes('器配')&&!String(label).includes('奥莱')&&!String(label).includes('销售')){{
      if(!inSubPs) inSubPs=true;
      const disc=cv(wsMain,r,10);
      if(inAcc) subPs.push({{isAcc:true,n:String(label),f:Number(flow),d:disc?Number(disc)*100:0,q:cv(wsMain,r,4)?Math.round(Number(cv(wsMain,r,4))):0}});
      else subPs.push({{isAcc:false,n:String(label),f:Number(flow),d:disc?Number(disc)*100:0,q:cv(wsMain,r,4)?Math.round(Number(cv(wsMain,r,4))):0}});
    }}
  }}
  const shoeSeries=[];
  for(let r=shoeStart+1;r<=shoeStart+20&&r<=120;r++){{
    const label=cv(wsMain,r,1); if(label==='合计') break;
    const flow=cv(wsMain,r,8);
    if(label&&flow&&Number(flow)) shoeSeries.push({{n:String(label),f:Number(flow),q:cv(wsMain,r,4)?Math.round(Number(cv(wsMain,r,4))):0,d:(cv(wsMain,r,10)||0)*100}});
  }}
  const seasData={{}};
  if(wsSeas){{
    const sHdr=findRow(wsSeas,'产品季',4)||3;
    const seasFlowRow=findRow(wsSeas,'流水',1)||sHdr+2;
    const seasDiscRow=seasFlowRow+2; const seasQtyRow=seasFlowRow+1;
    const seasSkuURow=findRow(wsSeas,'SKU动销',1)||16;
    const seasSatRow=findRow(wsSeas,'无可补',1)||25;
    const seasKeys=[['4','2025Q4及以前(服)'],['6','2026Q1(服)'],['8','2026Q2(服)'],['10','2026Q3+(服)'],['13','26年常青(服)'],['15','2025Q4及以前(鞋)'],['18','2026Q1(鞋)'],['20','2026Q2(鞋)'],['22','2026Q3+(鞋)'],['25','26年常青(鞋)']];
    for(const[ck,lb]of seasKeys){{ const cn=parseInt(ck); const f=cv(wsSeas,seasFlowRow,cn); if(f!==null) seasData[lb]={{f:Number(f),d:(cv(wsSeas,seasDiscRow,cn)||0)*100,q:Math.round(cv(wsSeas,seasQtyRow,cn)||0),su:(cv(wsSeas,seasSkuURow,cn)||0)*100,sat:(cv(wsSeas,seasSatRow,cn)||0)*100}}; }}
  }}
  const discRange={{}};
  for(let r=discStart;r<=discStart+3&&r<=220;r++){{ const label=cv(wsMain,r,1); if(!label) continue; discRange[String(r)]={{label:String(label),cols:{{}}}}; for(let c=1;c<=15;c++){{ const v=cv(wsMain,r,c); if(v!==null&&v!==undefined) discRange[String(r)].cols[String(c)]=v; }} }}
  const memberData=[];
  if(wsMember){{ const memStart=findRow(wsMember,'销售')-1||7; for(let r=memStart;r<=memStart+15&&r<=30;r++){{ const id=cv(wsMember,r,1); const name=cv(wsMember,r,3); const sales=cv(wsMember,r,9); if(name&&sales&&Number(sales)>0) memberData.push({{id:String(id||''),name:String(name),sales:Number(sales),qty:Math.round(cv(wsMember,r,10)||0),unitPrice:Number(cv(wsMember,r,11)||0),avgTicket:Number(cv(wsMember,r,12)||0),attach:Number(cv(wsMember,r,13)||0),shoePct:(cv(wsMember,r,15)||0)*100,clothPct:(cv(wsMember,r,16)||0)*100,o2o:cv(wsMember,r,17)||0}}); }} }}
  const t=r7[14]||0,act=r7[17]||0,ach=(r7[20]||0)*100,co=(r7[5]||0)*100,fl=r7[8]||0,ss=(r7[24]||0)*100,yo=(r7[22]||0)*100,mo=(r7[28]||0)*100;
  const oo=r7[33]||0,op=(r7[35]||0)*100,pd=r7[37]||0,ol=r7[39]||0;
  const at=r15[10]||0,up=r15[4]||0,ar=r15[16]||0,di=(r15[28]||0)*100,tc=r15[22]||0;
  const cy=(r7[6]||0)*100,fy=(r7[10]||0)*100,ay=(r15[12]||0)*100,ayy=(r15[18]||0)*100,uy=(r15[6]||0)*100,dy=(r15[30]||0)*100,om=(r7[36]||0)*100,cm=(r7[7]||0)*100,fm=(r7[12]||0)*100;
  const mfmt=v=>v>=10000?((v/10000).toFixed(1)+'万'):('¥'+v.toFixed(0));
  const mat=[['流水达成率',ach.toFixed(2)+'%',(yo>0?'+':'')+yo.toFixed(2)+'%',(mo>0?'+':'')+mo.toFixed(2)+'%'],['成交率',co.toFixed(2)+'%',(cy>0?'+':'')+cy.toFixed(2)+'%pp',(cm>0?'+':'')+cm.toFixed(2)+'%pp'],['日均客流',fl.toFixed(0)+'人',(fy>0?'+':'')+fy.toFixed(2)+'%',(fm>0?'+':'')+fm.toFixed(2)+'%'],['客单价',(at>=10000?((at/10000).toFixed(1)+'万'):('¥'+at.toFixed(0))),(ay>0?'+':'')+ay.toFixed(2)+'%',(ay>0?'+':'')+ay.toFixed(2)+'%'],['连带率',ar.toFixed(2)+'件',(ayy>0?'+':'')+ayy.toFixed(2)+'%',(ayy>0?'+':'')+ayy.toFixed(2)+'%'],['件单价',(up>=10000?((up/10000).toFixed(1)+'万'):('¥'+up.toFixed(0))),(uy>0?'+':'')+uy.toFixed(2)+'%',(uy>0?'+':'')+uy.toFixed(2)+'%'],['折扣率',di.toFixed(2)+'%',(dy>0?'+':'')+dy.toFixed(2)+'%pp',(dy>0?'+':'')+dy.toFixed(2)+'%pp'],['O2O流水',(oo>=10000?((oo/10000).toFixed(1)+'万'):('¥'+oo.toFixed(0))),'--',(om>0?'+':'')+om.toFixed(2)+'%'],['SSSG',(ss>0?'+':'')+ss.toFixed(2)+'%',(ss>0?'+':'')+ss.toFixed(2)+'%',(mo>0?'+':'')+mo.toFixed(2)+'%']];
  const sh=catData['鞋']?catData['鞋'].f_share:0,su=catData['鞋']?catData['鞋'].sku_u:0;
  return {{store,period,week_range:weekRange,target:t,actual:act,achieve:ach,yoy:yo,mom:mo,sssg:ss,conv:co,flow:fl,avg_t:at,unit_p:up,attach_r:ar,disc:di,o2o:oo,o2o_pct:op,tkt_cnt:tc,pad:pd,o2o_online:ol,conv_yoy:cy,flow_yoy:fy,avg_t_yoy:ay,attach_yoy:ayy,unit_yoy:uy,disc_yoy_p:dy,o2o_mom:om,conv_mom:cm,flow_mom:fm,daily,category:catData,matrix:mat,top:topData,sub_ps:subPs,shoe:shoeSeries,seas:seasData,disc_range:discRange,member:memberData,shoe_share:sh,shoe_sku_u:su,total_stock_qty:tsq,shoe_s_qty:catData['鞋']?catData['鞋'].s_qty:0,shoe_s_sku:catData['鞋']?catData['鞋'].s_sku:0}};
}}

// ─── P1-1: computeDerivedMetrics ───
function computeDerivedMetrics(d){{
  const w=(d.category['鞋']?d.category['鞋'].flow:0);
  const shoePS=w/(d.category['鞋']?d.category['鞋'].sku_s:1);
  const accPS=(d.category['配件']?d.category['配件'].flow:0)/(d.category['配件']?d.category['配件'].sku_s:1);
  const cs=Object.entries(d.category).sort((a,b)=>a[1].yoy-b[1].yoy);
  const wc=cs[0]?cs[0][0]:'--',wy=cs[0]?cs[0][1].yoy:0;
  const sat=d.daily[5];
  return{{shoePerSku:shoePS,accPerSku:accPS,worstCat:wc,worstCatYoy:wy,
    yoyGap:d.actual/(1+d.yoy/100)-d.actual,satGap:sat.t-sat.f,
    ticketGap:(600-d.avg_t)*d.tkt_cnt,attachGap:(4.5-d.attach_r)*d.tkt_cnt*d.unit_p,
    satAchieve:sat.a,satFlow:sat.f,satTarget:sat.t,satVisitors:sat.v,satTicket:sat.tk,satAttach:sat.at,
    sunFlow:d.daily[6].f,thuAchive:d.daily[3].a,thuTicket:d.daily[3].tk,thuAttach:d.daily[3].at,
    allCatsDown:Object.values(d.category).every(c=>c.yoy<-15),
    discountSpiral:d.disc>40&&d.mom<-10&&d.disc_mom>0,
    lowConvHighFlow:d.conv<20&&d.flow_yoy>0,
    ticketAttachBothDown:d.avg_t_yoy<-10&&d.attach_yoy<-10}};
}}

// ─── P0-3: analysisRules ───
function analyzeProblems(d,m){{
  const fm=v=>v>=10000?((v/10000).toFixed(1)+'万'):('¥'+v.toFixed(0));
  const ps=[];
  if(d.yoy<-20) ps.push({{id:'yoy_crash',severity:'high',title:'整体流水同比暴跌'+d.yoy.toFixed(1)+'% — 业绩断崖式下滑',loss:'周流水同比流失 ≈ '+fm(Math.abs(m.yoyGap)),data:'本周流水 <b>'+fm(d.actual)+'</b> | 同比 <b style="color:#ef4444">'+(d.yoy>0?'+':'')+d.yoy.toFixed(1)+'%</b> | 达成率 <b>'+d.achieve.toFixed(1)+'%</b><br>成交率 <b>'+d.conv.toFixed(1)+'%</b>（同比'+(d.conv_yoy>0?'+':'')+d.conv_yoy.toFixed(1)+'pp）| 客单价 '+fm(d.avg_t)+'<br>若恢复去年同期周流水应达 '+fm(d.actual/(1+d.yoy/100)),cause:[d.conv_yoy<-3?'成交率同比'+d.conv_yoy.toFixed(1)+'pp转化效率恶化':'',d.disc_yoy_p>0&&d.yoy<0?'折扣率'+(d.disc_yoy_p>0?'+':'')+d.disc_yoy_p.toFixed(1)+'pp但流水同步下降':'',d.attach_yoy<-8?'连带率'+d.attach_yoy.toFixed(1)+'%每笔少卖约'+(d.attach_r*(1-Math.abs(d.attach_yoy/100))-d.attach_r).toFixed(1)+'件':''].filter(Boolean).join('；')}});
  if(m.satAchieve<60) ps.push({{id:'sat_crash',severity:'high',title:'周六崩盘 — 达成率仅'+m.satAchieve.toFixed(1)+'%，单日损失 '+fm(m.satGap),loss:'预估损失 ≈ '+fm(m.satGap),data:'周六目标 '+fm(m.satTarget)+' → 实际 <b style="color:#ef4444">'+fm(m.satFlow)+'</b> | 达成 <b style="color:#ef4444">'+m.satAchieve.toFixed(1)+'%</b><br>客流量 '+m.satVisitors+'人（不及周日'+d.daily[6].v+'人的'+(m.satVisitors/d.daily[6].v*100).toFixed(0)+'%）| 客单价 '+fm(m.satTicket)+' | 连带率 '+m.satAttach.toFixed(2),cause:'目标'+m.satTarget/m.satTarget.toFixed(1)+'倍于平日目标过高；客流仅'+m.satVisitors+'人不足；客单价/连带率均低于周四峰值'}});
  if(m.allCatsDown) ps.push({{id:'category_all_down',severity:'high',title:'所有品类同比全面下挫 — '+m.worstCat+' '+m.worstCatYoy.toFixed(1)+'%最严重',loss:'四品类无一幸免',data:Object.entries(d.category).map(([n,cd])=>n+' '+(cd.yoy>0?'+':'')+cd.yoy.toFixed(1)+'%（折扣'+cd.disc.toFixed(1)+'%）').join(' | '),cause:(d.category['鞋']?d.category['鞋'].sku_u:0)<40?'鞋SKU动销率仅'+(d.category['鞋']?d.category['鞋'].sku_u.toFixed(1):'--')+'%大量SKU躺平':''}});
  if(m.ticketAttachBothDown) ps.push({{id:'ticket_attach_down',severity:'medium',title:'客单价与连带率双降 — 低客单低效率驱动',loss:'若客单价恢复至¥600周增量≈'+fm(m.ticketGap),data:'客单价 '+(d.avg_t_yoy>0?'+':'')+d.avg_t_yoy.toFixed(1)+'% | 连带率 '+(d.attach_yoy>0?'+':'')+d.attach_yoy.toFixed(1)+'% | 件单价 '+(d.unit_yoy>0?'+':'')+d.unit_yoy.toFixed(1)+'% → 客单价下降主因是连带效率下降',cause:'每笔少卖约'+(d.attach_r*(1-Math.abs(d.attach_yoy/100))-d.attach_r).toFixed(1)+'件导购推荐能力下降'}});
  if(m.discountSpiral) ps.push({{id:'discount_spiral',severity:'medium',title:'折扣率'+d.disc.toFixed(1)+'%持续走高 — 越打折越卖不动',loss:'折扣率环比'+(d.disc_mom>0?'+':'')+d.disc_mom.toFixed(1)+'pp但流水环比'+(d.mom>0?'+':'')+d.mom.toFixed(1)+'%',data:'综合折扣'+d.disc.toFixed(1)+'%（约'+d.disc/10+(d.disc/10).toFixed(1)+'折）| 同比'+(d.disc_yoy_p>0?'+':'')+d.disc_yoy_p.toFixed(1)+'pp | 环比'+(d.disc_mom>0?'+':'')+d.disc_mom.toFixed(1)+'pp',cause:'折扣加深→流水反降→继续加深折扣的恶性循环'}});
  if(ps.length===0) ps.push({{id:'no_issue',severity:'low',title:'未检测到严重问题',loss:'',data:'本周各项指标均在合理范围内',cause:''}});
  return ps;
}}

function analyzeOpportunities(d,m){{
  const fm=v=>v>=10000?((v/10000).toFixed(1)+'万'):('¥'+v.toFixed(0));
  return[{{id:'sat_recovery',title:'周六复苏攻坚 — 夺回单日 '+fm(m.satGap)+' 增量',body:'<b>目标：</b>周六达成率从'+m.satAchieve.toFixed(1)+'%恢复至80%+<br><b>A — 周五预锁定：</b>推"周六专属券满399-30"<br><b>B — 社交裂变：</b>"带朋友到店各减¥20"<br><b>C — 排班优化：</b>周六14-18点最强导购值守'}},
  {{id:'conversion',title:'流量激活：成交率从'+d.conv.toFixed(1)+'%提升至'+(d.conv+4).toFixed(1)+'%',body:'<b>目标：</b>提升成交率4pp<br><b>A — 进店话术：</b>"欢迎光临今天新品到店"<br><b>B — 试穿激励：</b>"试穿3件以上送袜子"<br><b>C — 加价购：</b>"加¥59换购指定T恤"'}},
  {{id:'sku_slim',title:'SKU瘦身+爆款深耕',body:'<b>目标：</b>鞋SKU动销率提升至50%+<br><b>A — 断舍离：</b>筛查2周0动销SKU调出<br><b>B — TOP20深耕：</b>锁定TOP20鞋款加库存深度<br><b>C — 配件同步：</b>清理0动销配件SKU'}},
  {{id:'attach_up',title:'连带攻坚：从'+d.attach_r.toFixed(1)+'件拉升至4.5件',body:'<b>目标：</b>连带率+0.6件周增≈'+fm(m.attachGap)+'<br><b>A — "1+1+1"搭配法：</b>主推+搭配+连带<br><b>B — 鞋区旁陈列：</b>"买鞋+¥99换购短裤"<br><b>C — "连带王"奖：</b>超4件¥10超6件¥20'}},
  {{id:'disc_control',title:'折扣管控：从'+d.disc.toFixed(1)+'%控制到'+(d.disc-2).toFixed(1)+'%以内',body:'<b>目标：</b>综合折扣率'+(d.disc-2).toFixed(1)+'%以内<br><b>A — 新品保护：</b>常青款首2周正价销售<br><b>B — 满减替代直降：</b>"满599减60/满999减150"<br><b>C — 品折扣中折：</b>鞋保持折扣服装收紧'}},
  {{id:'o2o_boost',title:'O2O渠道发力 + 周日巩固',body:'<b>目标：</b>O2O从'+fm(d.o2o)+'提升至'+fm(8000)+'+<br><b>A — 周日维护：</b>周日流水'+fm(m.sunFlow)+'全周最强<br><b>B — PAD+官网同步：</b>线下畅销款标注线上同款<br><b>C — 周四模式复制：</b>周四达成'+m.thuAchive.toFixed(1)+'%复制到其他日'}}];
}}

function renderAnalysis(){{
  const D=DATA,m=computeDerivedMetrics(D),ps=analyzeProblems(D,m),os=analyzeOpportunities(D,m);
  let ph=''; ps.forEach((p,i)=>{{ph+='<div class="pc'+(i<2?' open':'')+'" onclick="toggleCard(this)"><div class="phead"><span class="pnum">'+(i+1)+'</span><h4>'+p.title+'</h4><span class="toggle-icon">▶</span></div>'+(p.loss?'<div class="pbody"><span class="loss-tag">'+p.loss+'</span>':'<div class="pbody">')+(p.data?'<div class="dbox">'+p.data+'</div>':'')+(p.cause?'<b>根因：</b>'+p.cause:'')+'</div></div>';}});
  document.getElementById('tab-problems').innerHTML=ph;
  let oh=''; os.forEach((o,i)=>{{oh+='<div class="oc" onclick="toggleCard(this)"><div class="ohead"><span class="onum">'+(i+1)+'</span><h4>'+o.title+'</h4><span class="toggle-icon">▶</span></div><div class="obody">'+o.body+'</div></div>';}});
  document.getElementById('tab-opps').innerHTML=oh;
  document.querySelector('.summary-box').innerHTML='<h3 style="color:#fbbf24;margin-bottom:12px;">总结：核心问题逻辑关系</h3><p style="font-size:13px;line-height:2;opacity:.9"><span style="background:var(--red);padding:3px 12px;border-radius:20px;font-size:11px">同比'+D.yoy.toFixed(1)+'%</span>+<span style="background:var(--red);padding:3px 12px;border-radius:20px;font-size:11px">周六达成'+m.satAchieve.toFixed(1)+'%</span>→客流端失血<br><span style="background:var(--red);padding:3px 12px;border-radius:20px;font-size:11px">'+m.worstCat+' '+m.worstCatYoy.toFixed(1)+'%</span>+<span style="background:var(--red);padding:3px 12px;border-radius:20px;font-size:11px">折扣'+D.disc.toFixed(1)+'%</span>→品类端失血<br><span style="background:var(--red);padding:3px 12px;border-radius:20px;font-size:11px">客单'+D.avg_t_yoy.toFixed(1)+'%</span>+<span style="background:var(--red);padding:3px 12px;border-radius:20px;font-size:11px">连带'+D.attach_yoy.toFixed(1)+'%</span>→效率端失血</p>';
}}

function buildKpiStrip(){{
  const D=DATA,fmt=v=>v>=10000?((v/10000).toFixed(1)+'万'):('¥'+v.toFixed(0)),pc=v=>(v>0?'+':'')+v.toFixed(1)+'%',pa=v=>v.toFixed(1)+'%',cl=v=>v>=0?'up':'down';
  const h=[]; h.push('<div class="ki"><div class="kv" style="color:'+(D.achieve>=100?'#22c55e':'#ef4444')+'">'+D.achieve.toFixed(1)+'%</div><div class="kl">达成率</div><div class="kc '+cl(D.achieve>=100)+'">'+(D.achieve>=100?'超目标':'未达标')+'</div></div>');
  h.push('<div class="ki"><div class="kv">'+fmt(D.actual)+'</div><div class="kl">周流水</div><div class="kc down">'+pc(D.yoy)+'</div></div>');
  h.push('<div class="ki"><div class="kv" style="color:'+(D.yoy<0?'#ef4444':'#22c55e')+'">'+pc(D.yoy)+'</div><div class="kl">SSSG</div><div class="kc '+cl(D.yoy)+'">同比</div></div>');
  h.push('<div class="ki"><div class="kv">'+D.conv.toFixed(1)+'%</div><div class="kl">成交率</div><div class="kc '+cl(D.conv_yoy)+'">'+pa(D.conv_yoy)+'pp</div></div>');
  h.push('<div class="ki"><div class="kv">'+fmt(D.avg_t)+'</div><div class="kl">客单价</div><div class="kc '+cl(D.avg_t_yoy)+'">'+pc(D.avg_t_yoy)+'</div></div>');
  h.push('<div class="ki"><div class="kv">'+D.attach_r.toFixed(2)+'件</div><div class="kl">连带率</div><div class="kc '+cl(D.attach_yoy)+'">'+pc(D.attach_yoy)+'</div></div>');
  h.push('<div class="ki"><div class="kv">'+D.shoe_share.toFixed(1)+'%</div><div class="kl">鞋占比</div><div class="kc down">'+pc(D.category['鞋']?D.category['鞋'].yoy:0)+'</div></div>');
  h.push('<div class="ki"><div class="kv">'+fmt(D.o2o)+'</div><div class="kl">O2O</div><div class="kc '+cl(D.o2o_mom)+'">'+pc(D.o2o_mom)+'</div></div>');
  h.push('<div class="ki"><div class="kv">'+D.disc.toFixed(1)+'%</div><div class="kl">折扣率</div><div class="kc '+cl(D.disc_yoy_p)+'">'+pa(D.disc_yoy_p)+'pp</div></div>');
  h.push('<div class="ki"><div class="kv">'+D.flow.toFixed(0)+'人</div><div class="kl">日均客流</div><div class="kc '+cl(D.flow_yoy)+'">'+pc(D.flow_yoy)+'</div></div>');
  document.getElementById('kpiStrip').innerHTML=h.join('');
}}

// ─── INIT ───
window.addEventListener('DOMContentLoaded',()=>{{
  initTables();
  drawDailyCharts();
}});
</script>
</body>
</html>'''

with open(f'{BASE}/weekly-dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Dashboard built: {BASE}/weekly-dashboard.html ({len(html):,} bytes)")
