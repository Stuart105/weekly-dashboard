#!/usr/bin/env python
"""Build single-page weekly report dashboard HTML."""
import json, os, sys
from datetime import datetime

# Usage: python build_dashboard.py [data_directory]
# If no argument, looks for extracted_data.json in current directory
BASE = sys.argv[1] if len(sys.argv) > 1 else '.'
with open(f'{BASE}/extracted_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

r7 = d['r7_kpi']; r15 = d['r15_price']; daily = d['daily']; cate = d['category']
top = d['top_goods']; seas = d['seasonal']; member = d['member']

store = "奥莱店华南区城市"
rc = d.get('report_config', {})
period = rc.get('_version', 'W24')
week_range = "2026.06.08-06.14"

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

# Helper for safe extraction with fallback
def cval(row_label, col_key, default=0):
    for rk, rd in cate.items():
        if rd.get('label') == row_label:
            v = rd.get('data', {}).get(col_key, None)
            return float(v) if v is not None else default
    return default

# Group 1: Product categories (鞋服器配) — full metrics including stock
for ck, cn in [('14','鞋'),('16','服'),('18','器配')]:
    f_c = float(cate['36']['data'].get(ck,0))
    cat_data[cn] = {
        'flow': f_c,
        'qty': int(cval('数量', ck)),
        'disc': cval('折扣', ck)*100,
        'yoy': cval('同比', ck)*100,
        'mom': cval('环比', ck)*100,
        'f_share': cval('流水占比', ck)*100,
        'sku_s': int(cval('SKU(个数)', ck)),
        's_qty': int(cval('库存数量', ck)),
        's_sku': int(cval('库存SKU(个数)', ck)),
        'sku_u': cval('SKU动销率', ck)*100,
        'sat': cval('无可补断码率', ck)*100,
        'st': cval('实际断码率', ck)*100,
        'group': 'product',
    }

# Group 2: Customer gender (男女童, 童装=J-K合并列C10)
for ck, cn in [('4','男'),('6','女'),('10','童')]:
    f_c = float(cate['36']['data'].get(ck,0))
    entry = {
        'flow': f_c,
        'qty': int(cval('数量', ck)),
        'disc': cval('折扣', ck)*100,
        'yoy': cval('同比', ck)*100,
        'mom': cval('环比', ck)*100,
        'f_share': cval('流水占比', ck)*100,
        'group': 'gender',
    }
    # Add stock data where available (cval returns 0 for missing)
    entry['sku_s'] = int(cval('SKU(个数)', ck))
    entry['s_qty'] = int(cval('库存数量', ck))
    entry['s_sku'] = int(cval('库存SKU(个数)', ck))
    entry['sku_u'] = cval('SKU动销率', ck)*100
    entry['sat'] = cval('无可补断码率', ck)*100
    entry['st'] = cval('实际断码率', ck)*100
    cat_data[cn] = entry

# Category match (only for product group)
product_cats = [cn for cn, cd in cat_data.items() if cd.get('group') == 'product']
total_sq = sum(cat_data[c]['s_qty'] for c in product_cats) if product_cats else 0
for cn in product_cats:
    cd = cat_data[cn]
    sqs = cd['s_qty']/total_sq*100 if total_sq > 0 else 0
    fs = cd['f_share']
    cd['s_q_share'] = sqs
    cd['gap'] = fs - sqs
    cd['match_lbl'] = '匹配' if abs(fs-sqs)<=5 else (f'销>库+{fs-sqs:.1f}pp' if fs>sqs else f'库>销{sqs-fs:.1f}pp')

# TOP
top_labels = {'125':'TOP10','126':'TOP20','127':'TOP40','128':'TOP60','129':'TOP100'}
top_data = {}
for rk, lbl in top_labels.items():
    if rk in top:
        td = top[rk]['data']
        filtered = {k: float(td.get(k,0))*100 for k in ['4','6','8','10','13'] if k in td}
        if filtered:  # skip empty entries (e.g. TOP100 with no 4/6/8/10/13 cols)
            top_data[lbl] = filtered

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
sub_ps_rows.sort(key=lambda x: x['f'], reverse=True)  # 流水倒序

# Shoe series  
shoe_rows = []
for rk in ['76','77','78','79','80','85','87']:
    if rk in d['shoe_series']:
        rd = d['shoe_series'][rk]; data = rd['data']
        label = rd['label']
        if label and data.get('8'):
            shoe_rows.append({'n':label,'f':float(data['8']),'q':int(float(data['4'])),'d':float(data['10'])*100})
shoe_rows.sort(key=lambda x: x['f'], reverse=True)  # 流水倒序

# Acc sub-PS (uses accessory_sub section, rows 115-120)
acc_rows = []
for rk in ['115','116','117','120']:
    if rk in d['accessory_sub']:
        rd = d['accessory_sub'][rk]; data = rd['data']
        label = rd['label']
        if label and data.get('8'):
            sub_ps_rows.append({'n':label,'f':float(data['8']),'d':float(data['10'])*100,'q':int(float(data['4'])),'isAcc':True})

# Seasonal new product
seas_data = {}
seas_meta = {}  # overall metrics (yoy etc)
if '5' in seas:
    r5d = seas['5'].get('data', {})
    r7d = seas.get('7', {}).get('data', {}) if isinstance(seas.get('7'), dict) else {}
    r6d = seas.get('6', {}).get('data', {}) if isinstance(seas.get('6'), dict) else {}
    r19d = seas.get('19', {}).get('data', {}) if isinstance(seas.get('19'), dict) else {}
    r25d = seas.get('25', {}).get('data', {}) if isinstance(seas.get('25'), dict) else {}
    # NEW: extract 环比(row9), SKU个数(row16), 库存数量(row21), 同比(row11)
    r9d = seas.get('9', {}).get('data', {}) if isinstance(seas.get('9'), dict) else {}
    r16d = seas.get('16', {}).get('data', {}) if isinstance(seas.get('16'), dict) else {}
    r21d = seas.get('21', {}).get('data', {}) if isinstance(seas.get('21'), dict) else {}
    r11d = seas.get('11', {}).get('data', {}) if isinstance(seas.get('11'), dict) else {}
    r13d = seas.get('13', {}).get('data', {}) if isinstance(seas.get('13'), dict) else {}  # 流水占比
    r23d = seas.get('23', {}).get('data', {}) if isinstance(seas.get('23'), dict) else {}  # 库存占比
    # Overall YoY for 服 and 鞋 (row 11 col 4=服, col 15=鞋)
    seas_meta['cloth_yoy'] = float(r11d.get('4', 0))*100 if '4' in r11d else 0
    seas_meta['shoe_yoy'] = float(r11d.get('15', 0))*100 if '15' in r11d else 0
    for ck, lbl in [('4','2025Q4及以前(服)'),('6','2026Q1(服)'),('8','2026Q2(服)'),('10','2026Q3+(服)'),('13','26年常青(服)'),
                     ('15','2025Q4及以前(鞋)'),('18','2026Q1(鞋)'),('20','2026Q2(鞋)'),('22','2026Q3+(鞋)'),('25','26年常青(鞋)')]:
        if ck in r5d:
            seas_data[lbl] = {
                'f': float(r5d.get(ck,0)),
                'd': float(r7d.get(ck,0))*100 if ck in r7d else 0,
                'q': int(float(r6d.get(ck,0))) if ck in r6d else 0,
                'su': float(r19d.get(ck,0))*100 if ck in r19d else 0,
                'sat': float(r25d.get(ck,0))*100 if ck in r25d else 0,
                # NEW fields for season comparison
                'mom': float(r9d.get(ck,0))*100 if ck in r9d else 0,
                'sku': int(float(r16d.get(ck,0))) if ck in r16d else 0,
                'stock_qty': int(float(r21d.get(ck,0))) if ck in r21d else 0,
                'fs': float(r13d.get(ck,0))*100 if ck in r13d else 0,  # 流水占比%
                'stk_share': float(r23d.get(ck,0))*100 if ck in r23d else 0,  # 库存占比%
            }

# Build season comparison HTML tables (服 vs 鞋, seasons as columns)
# type: 'money' → ¥前缀 | 'pct' → %后缀+红绿色 | 'num' → 纯数字
_seas_metrics = [('流水','f','money'),('销量','q','num'),('环比','mom','pct'),('SKU数','sku','num'),('库存量','stock_qty','num'),('折扣率','d','pct_abs'),('动销率','su','pct_abs')]
_seas_keys = [('2025Q4及以前(服)','2025Q4及以前(鞋)'),('2026Q1(服)','2026Q1(鞋)'),('2026Q2(服)','2026Q2(鞋)'),('2026Q3+(服)','2026Q3+(鞋)'),('26年常青(服)','26年常青(鞋)')]
def _sfmt(v, typ):
    if v is None: return '—', ''
    if typ == 'pct': return f'{v:+.1f}%' if v>0 else f'{v:.1f}%', f' class="{"hi" if v>0 else "lo"}"'
    if typ == 'pct_abs': return f'{v:.1f}%', ''  # absolute % no sign
    if typ == 'money': return f'¥{v:,.0f}', ''
    return f'{v:,.0f}', ''  # num type: plain number
clothing_seas_html = ''
shoe_seas_html = ''
for nm, fk, typ in _seas_metrics:
    c_row = f'<tr><td>{nm}</td>'
    s_row = f'<tr><td>{nm}</td>'
    for ck, sk in _seas_keys:
        cv = seas_data.get(ck, {}).get(fk) if ck in seas_data else None
        sv = seas_data.get(sk, {}).get(fk) if sk in seas_data else None
        ctxt, ccls = _sfmt(cv, typ)
        stxt, scls = _sfmt(sv, typ)
        c_row += f'<td{ccls}>{ctxt}</td>'
        s_row += f'<td{scls}>{stxt}</td>'
    clothing_seas_html += c_row + '</tr>'
    shoe_seas_html += s_row + '</tr>'

# ───────── Mid-category data (男服/女服/男鞋/女鞋) ─────────
# Each: {name, section_start_row, col_map: {season_label: col_key}}
_mid_cats = [
    ('男服', 28, [('25Q4','4'),('26Q1','6'),('26Q2','8'),('26Q3+','10'),('常青','13')]),
    ('女服', 28, [('25Q4','15'),('26Q1','18'),('26Q2','20'),('26Q3+','22'),('常青','25')]),
    ('男鞋', 55, [('25Q4','4'),('26Q1','6'),('26Q2','8'),('26Q3+','10'),('常青','13')]),
    ('女鞋', 55, [('25Q4','15'),('26Q1','18'),('26Q2','20'),('26Q3+','22'),('常青','25')]),
]
_mid_metrics = [('流水','f','money'),('销量','qty','num'),('环比','mom','pct'),('SKU数','sku','num'),('库存量','stock_qty','num'),('折扣率','d','pct_abs'),('动销率','su','pct_abs')]
# Metric row mapping: {field: (section2_row, section3_row)}
_mid_row_map = {'f':(32,59), 'qty':(33,60), 'mom':(36,63), 'sku':(43,70), 'stock_qty':(48,75), 'd':(34,61), 'su':(46,73)}

mid_data = {}  # {name: {season_label: {f, mom, sku, stock_qty, d, su}}}
mid_agg = {}   # {name: {f, mom, sku, stock_qty, d, su}} — aggregate totals
_mid_names = ['男服','女服','男鞋','女鞋']
for mname, base_row, season_cols in _mid_cats:
    is_shoe = base_row >= 55
    mcat_data = {}
    for slab, ck in season_cols:
        mentry = {}
        for field, (r2, r3) in _mid_row_map.items():
            rk = str(r3 if is_shoe else r2)
            if rk in seas:
                v = seas[rk].get('data', {}).get(ck)
                if v is not None:
                    if field in ('mom', 'd', 'su'):
                        mentry[field] = float(v) * 100
                    elif field in ('sku', 'stock_qty', 'qty'):
                        mentry[field] = int(float(v))
                    else:
                        mentry[field] = float(v)
        if mentry.get('f', 0) > 0:
            mcat_data[slab] = mentry
    mid_data[mname] = mcat_data
    entries = [e for e in mcat_data.values() if e.get('f', 0) > 0]
    agg = {}
    if entries:
        for fk in ['f', 'sku', 'stock_qty', 'qty']:
            agg[fk] = sum(e.get(fk, 0) for e in entries)
        for fk in ['mom', 'd', 'su']:
            vals = [e.get(fk, 0) for e in entries if e.get(fk) is not None]
            agg[fk] = sum(vals) / len(vals) if vals else 0
    else:
        agg = {fk: 0 for fk in ['f','sku','stock_qty','qty','mom','d','su']}
    mid_agg[mname] = agg

# Build compact single table: 指标 | 男服 | 女服 | 男鞋 | 女鞋
_mid_table_html = '<thead><tr><th>指标</th><th>男服</th><th>女服</th><th>男鞋</th><th>女鞋</th></tr></thead><tbody>'
for nm, fk, typ in _mid_metrics:
    _mid_table_html += f'<tr><td>{nm}</td>'
    for mn in _mid_names:
        v = mid_agg[mn].get(fk, 0)
        if typ == 'money':
            _mid_table_html += f'<td>¥{v:,.0f}</td>'
        elif typ == 'pct':
            cls = ' class="hi"' if v > 0 else ' class="lo"'
            _mid_table_html += f'<td{cls}>{v:+.1f}%</td>'
        elif typ == 'pct_abs':
            _mid_table_html += f'<td>{v:.1f}%</td>'
        else:
            _mid_table_html += f'<td>{v:,.0f}</td>'
    _mid_table_html += '</tr>'
_mid_table_html += '</tbody>'

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
        'conv_rate': to_num(row_data.get('5', 0))*100,
        'daily_flow': to_num(row_data.get('8', 0)),
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
    'mom': mom_v, 'sssg': sssg_v,
    'conv_rate': conv_v, 'daily_flow': flow_v,
    'avg_ticket': avg_t, 'unit_price': unit_p, 'attach_rate': attach_r, 'discount': disc_v,
    'o2o': o2o_v, 'o2o_pct': o2o_pct, 'tkt_cnt': tkt_cnt, 'pad': pad_v, 'o2o_online': o2o_online,
    'conv_yoy': conv_yoy, 'flow_yoy': flow_yoy, 'avg_ticket_yoy': avg_t_yoy,
    'attach_yoy': attach_yoy, 'unit_yoy': unit_yoy,
    'discount_yoy': disc_yoy_p, 'discount_mom': disc_mom,
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
    'acc_per_sku': cat_data['器配']['flow'] / cat_data['器配']['sku_s'] if cat_data['器配']['sku_s'] else 0,
    'total_stock_qty': total_sq,
    'shoe_s_qty': cat_data['鞋']['s_qty'],
    'shoe_s_sku': cat_data['鞋']['s_sku'],
    'mtd': mtd_data, 'ytd': ytd_data, 'reg': reg_data,
    'mid_agg': mid_agg,
}

# ───────── Dynamic analysis text variables ─────────
# Severity/direction helpers
def dw(v, up='增长', down='下降'): return up if v>0 else down if v<0 else '持平'

# Revenue YoY severity
if yoy_v >= 20: p1_sev = '暴增'
elif yoy_v >= 10: p1_sev = '大幅增长'
elif yoy_v >= 3: p1_sev = '增长'
elif yoy_v > 0: p1_sev = '微增'
elif yoy_v <= -20: p1_sev = '暴跌'
elif yoy_v <= -10: p1_sev = '大幅下滑'
elif yoy_v <= -3: p1_sev = '下滑'
else: p1_sev = '微降'

# Prior period values
conv_prev = conv_v - conv_yoy
attach_prev = attach_r / (1 + attach_yoy/100) if abs(1 + attach_yoy/100) > 0.01 else attach_r
attach_gap = abs(attach_r - attach_prev)
avg_t_prev = avg_t / (1 + avg_t_yoy/100) if abs(1 + avg_t_yoy/100) > 0.01 else avg_t
avg_t_gap = abs(avg_t - avg_t_prev)

# YoY revenue loss
ly_revenue = actual_v / (1 + yoy_v/100) if abs(1 + yoy_v/100) > 0.01 else actual_v
loss_vs_ly = abs(actual_v - ly_revenue)

# Worst/best day
worst_day_idx = min(range(7), key=lambda i: daily_rows[i]['a'])
best_day_idx = max(range(7), key=lambda i: daily_rows[i]['a'])
worst_day = daily_rows[worst_day_idx]
best_day = daily_rows[best_day_idx]

# Category extremes
worst_cat = min(cat_data.keys(), key=lambda c: cat_data[c]['yoy'])
best_cat = max(cat_data.keys(), key=lambda c: cat_data[c]['yoy'])
worst_cat_yoy = cat_data[worst_cat]['yoy']
best_cat_yoy = cat_data[best_cat]['yoy']
shoe_zero_pct = 100 - cat_data['鞋']['sku_u']
all_cats_down = all(cat_data[c]['yoy'] < -5 for c in cat_data)

# Discount
disc_zhe = (100 - disc_v) / 10  # e.g. 44.1% → ~5.6折
concat_disc_sev = '持续走高' if disc_yoy_p > 0 else '有所改善'
disc_cycle = '越打折越卖不动' if disc_yoy_p > 0 and mom_v < -5 else '虽有下降但折扣率高'

# Sat loss / opportunity
sat_loss = worst_day['t'] - worst_day['f']
conv_lift_amt = (0.22 - conv_v/100) * (flow_v * 7) * avg_t
attach_lift_amt = (4.5 - attach_r) * tkt_cnt * unit_p
ticket_to_600 = (600 - avg_t) * tkt_cnt
first_cat_name = worst_cat
first_cat_yoy = worst_cat_yoy

# P1 title and detail
p1_title = f'整体流水同比{p1_sev}{abs(yoy_v):.1f}%'
if achieve_v < 100:
    p1_title += ' — 业绩未达标需重点关注'
elif yoy_v < -10:
    p1_title += ' — 同比大幅下滑需紧急干预'
else:
    p1_title += ' — 需关注增长质量'

p1_loss = f'周流水同比流失 ≈ ¥{loss_vs_ly:,.0f}' if yoy_v < 0 else f'周流水同比增量 ≈ ¥{loss_vs_ly:,.0f}'

conv_pp = f'（{pct(conv_yoy,1)}pp）'
p1_detail = f'成交率 {pa(conv_v,2)}{conv_pp}'
p1_detail += f' | 客单价 ¥{avg_t:,.0f}（同比{pct(avg_t_yoy,1)}）'
p1_detail += f' | 连带率 {f2(attach_r)}（同比{pct(attach_yoy,1)}）'

p1_root_cause_parts = []
if disc_yoy_p > 0:
    p1_root_cause_parts.append(f'折扣持续加深（{pa(disc_v,1)}/同比{disc_yoy_p:+.1f}pp）')
if conv_yoy < -5:
    p1_root_cause_parts.append(f'成交率从{pa(conv_prev,1)}降至{pa(conv_v,1)}，转化效率恶化')
if attach_yoy < -5:
    p1_root_cause_parts.append(f'连带率从{f2(attach_prev)}降至{f2(attach_r)}，每笔少卖约{attach_gap:.2f}件')
p1_root_cause = '；'.join(p1_root_cause_parts) if p1_root_cause_parts else '多指标综合影响'

# P2 - worst day
p2_title = f'{worst_day["n"]}崩盘 — 达成率仅{pa(worst_day["a"],1)}，单日损失 ¥{sat_loss:,.0f}'
# Find the weekday with max target multiple
other_targets = [daily_rows[i]['t'] for i in range(7) if i != worst_day_idx]
avg_other_target = sum(other_targets) / len(other_targets) if other_targets else worst_day['t']
target_multiple = worst_day['t'] / avg_other_target if avg_other_target > 0 else 1
best_day_achieve = best_day['a']

p2_cause = f'目标设定过高（工作日均目标的{target_multiple:.1f}倍）；'
if worst_day['v'] < best_day['v'] * 0.7:
    p2_cause += f'客流仅{worst_day["v"]}人（不及{best_day["n"]}{best_day["v"]}人的{worst_day["v"]/best_day["v"]*100:.0f}%）；'
p2_cause += f'客单价¥{worst_day["tk"]:,.0f}、连带率{worst_day["at"]:.2f}均低于{best_day["n"]}峰值'

# P3 - Category
p3_title = f'所有品类同比全面下挫 — {worst_cat}{pct(worst_cat_yoy,1)}最严重'
p3_loss = '四品类无一幸免'
if worst_cat_yoy < best_cat_yoy:
    p3_loss += f'，{worst_cat}环比{pct(cat_data[worst_cat]["mom"],1)}加速恶化'

cat_yoy_parts = []
for cn in ['鞋','服','器配']:
    if cn in cat_data:
        cat_yoy_parts.append(f'{cn}{pct(cat_data[cn]["yoy"],1)}')
p3_detail_cats = ' | '.join(cat_yoy_parts)

p3_cause_parts = []
if cat_data['鞋']['sku_u'] < 50:
    p3_cause_parts.append(f'鞋SKU动销率仅{pa(cat_data["鞋"]["sku_u"],1)}，{shoe_zero_pct:.0f}%鞋SKU一周0动销')
p3_disc_range = [cat_data[c]['disc'] for c in cat_data]
p3_cause_parts.append(f'四品类折扣率均在{min(p3_disc_range):.0f}-{max(p3_disc_range):.0f}%区间，同质化打折无法形成差异化')
p3_cause = '；'.join(p3_cause_parts)

# P4 - Ticket/attach
p4_title = f'客单价与连带率双降 — 低客单、低效率交易驱动'
p4_loss = f'若客单价恢复至¥600，周增量 ≈ ¥{ticket_to_600:,.0f}'
p4_detail = f'客单价 ¥{avg_t:,.0f}（同比{pct(avg_t_yoy,1)}） | 连带率 {f2(attach_r)}件（同比{pct(attach_yoy,1)}） | 件单价 ¥{unit_p:,.0f}（同比{pct(unit_yoy,1)}）'
if abs(attach_yoy) > abs(avg_t_yoy):
    p4_detail += ' → 连带效率下降是主因'
p4_cause = f'每笔少卖约{attach_gap:.2f}件，导购推荐和搭配销售能力下降；'
if worst_day['at'] < best_day['at']:
    p4_cause += f'周末客流多但连带反而差（{worst_day["n"]}{worst_day["at"]:.2f}/{best_day["n"]}{best_day["at"]:.2f}）；'
p4_cause += '折扣环境导致顾客倾向买单件折扣品而非多件搭配'

# P5 - Discount
p5_title = f'折扣率{pa(disc_v,1)}{concat_disc_sev} — {disc_cycle}'
p5_loss = f'折扣率环比{pct(disc_mom,1)}pp但流水环比{pct(mom_v,1)}'
p5_detail = f'综合折扣{pa(disc_v,1)}（约{disc_zhe:.1f}折）| 同比{disc_yoy_p:+.2f}pp | 环比{disc_mom:+.2f}pp'
p5_detail += '<br>折扣加深→流水反降→继续加深折扣的恶性循环正在形成'
p5_cause = f'{pa(disc_v,1)}折扣在奥莱体系中也属偏高；顾客对"奥莱=常年打折"形成预期，非打折商品难以动销；同行竞争压力迫使持续让利但效果递减'

# P6 - Seasonal
p6_lbl_cloth_evergreen = '26年常青(服)'
p6_f_cloth = seas_data.get(p6_lbl_cloth_evergreen, {}).get('f', 0)
p6_d_cloth = seas_data.get(p6_lbl_cloth_evergreen, {}).get('d', 0)
p6_su_cloth = seas_data.get(p6_lbl_cloth_evergreen, {}).get('su', 0)
p6_q2_cloth_d = seas_data.get('2026Q2(服)', {}).get('d', 0)
p6_title = f'新品表现乏力 — {p6_lbl_cloth_evergreen}折扣率{pa(p6_d_cloth,1)}、动销率低'
p6_tag = f'{p6_lbl_cloth_evergreen}折扣{pa(p6_d_cloth,1)}，动销率{pa(p6_su_cloth,1)}'
p6_detail = f'2026Q2(服)折扣{pa(p6_q2_cloth_d,1)}（约{max(1, (100-p6_q2_cloth_d)/10):.0f}折），当季新品也需大幅让利'
# Get min/max sat among clothing items
cloth_sats = [seas_data[k]['sat'] for k in seas_data if '(服)' in k and seas_data[k].get('sat', 0) > 0]
if cloth_sats:
    p6_detail += f'<br>新品可满足率仅{min(cloth_sats):.0f}-{max(cloth_sats):.0f}%，新品备货极度保守'

# Opps text
opp1_title = f'{worst_day["n"]}复苏攻坚 — 夺回单日 ¥{sat_loss:,.0f} 增量'
opp2_title = f'流量激活：成交率从{pa(conv_v,1)}提升至{pa(conv_v+4,1)}'
opp3_title = f'鞋类SKU瘦身+爆款深耕 — 动销率{pa(cat_data["鞋"]["sku_u"],1)}→50%+'
opp4_title = f'连带攻坚：从{f2(attach_r)}件拉升至4.5件'
opp5_title = f'折扣管控：从{pa(disc_v,1)}控制到{pa(disc_v-2,1)}以内'
opp6_title = f'O2O渠道发力 + 周日巩固'

# FULL_TEXT pre-computed strings
avg_t_dir = '增长' if avg_t_yoy > 0 else '下降'
attach_dir = '增长' if attach_yoy > 0 else '下滑'
disc_str = "折扣加深但流水下降，'打折拉销售'策略已失效" if disc_yoy_p > 0 and mom_v < 0 else "折扣控制较好"
avg_t_analysis = f"客单价{avg_t_dir}主要受连带率{attach_dir}影响" if abs(avg_t_yoy) > 0 else "客单价基本持平"
achieve_assessment = "达成率表面达标但增长质量堪忧" if achieve_v >= 100 else "达成率偏低需重点关注"
flow_conv_analysis = "客流增长但成交率下降—'进店不买'问题突出" if flow_yoy > 0 and conv_yoy < 0 else "客流与成交率同步波动"

# ───────── 4× Analysis Variants ─────────
# Different analytical angles for key assessment phrases
_achieve_variants = [
    f"达成率{pa(achieve_v,2)}，{'超目标' if achieve_v>=100 else '未达标'}¥{abs(actual_v-target_v)/10000:.1f}万。同比{pct(yoy_v,2)}，{'增长质量尚可' if yoy_v>10 else '增长乏力需关注' if yoy_v>0 else '下滑需警惕'}",
    f"目标¥{target_v/10000:.1f}万，实绩¥{actual_v/10000:.1f}万，缺口¥{abs(actual_v-target_v)/10000:.1f}万。{achieve_assessment}。同比{pct(yoy_v,2)}、同店同比{pct(sssg_v,2)}",
    f"本周流水¥{actual_v/10000:.1f}万（目标¥{target_v/10000:.1f}万），达成率{pa(achieve_v,2)}。同比{pct(yoy_v,2)}，{'跑赢去年' if yoy_v>5 else '跑输去年' if yoy_v<-5 else '与去年持平'}",
    f"核心指标：达成率{pa(achieve_v,2)}（目标¥{target_v/10000:.1f}万 → 实际¥{actual_v/10000:.1f}万），同比{pct(yoy_v,2)}，{'表现优于大盘' if yoy_v>15 else '跑输大盘' if yoy_v<0 else '基本持平'}",
]
_conv_variants = [
    f"成交率{pa(conv_v,2)}（同比{pct(conv_yoy,1)}pp），日均客流{flow_v:.0f}人（同比{pct(flow_yoy,1)}）{flow_conv_analysis}",
    f"客流{flow_v:.0f}人/天，成交率{pa(conv_v,2)}，{flow_conv_analysis}。周成交{tkt_cnt:.0f}笔",
    f"进店转化率{pa(conv_v,2)}（同比{pct(conv_yoy,1)}pp），日均客流{flow_v:.0f}人、同比{pct(flow_yoy,1)}。{flow_conv_analysis}",
    f"流量端：日均{flow_v:.0f}人（同比{pct(flow_yoy,1)}），成交率{pa(conv_v,2)}（同比{pct(conv_yoy,1)}pp），{'客流增长但转化不足' if flow_yoy>0 and conv_yoy<0 else '流量与转化同步波动'}",
]
_ticket_variants = [
    f"客单价¥{avg_t:,.0f}（同比{pct(avg_t_yoy,1)}），连带率{f2(attach_r)}件（同比{pct(attach_yoy,1)}），件单价¥{unit_p:,.0f}（同比{pct(unit_yoy,1)}）。{avg_t_analysis}",
    f"客单价¥{avg_t:,.0f}同比{pct(avg_t_yoy,1)}，连带率{f2(attach_r)}同比{pct(attach_yoy,1)}，件单价¥{unit_p:,.0f}同比{pct(unit_yoy,1)}。{avg_t_analysis}",
    f"客单¥{avg_t:,.0f}（{pct(avg_t_yoy,1)}），连带{f2(attach_r)}（{pct(attach_yoy,1)}），件单¥{unit_p:,.0f}（{pct(unit_yoy,1)}）。{'连带驱动客单' if abs(attach_yoy) > abs(avg_t_yoy) else '件单价驱动客单'}为主因",
    f"价格效率：客单价¥{avg_t:,.0f}（同比{pct(avg_t_yoy,1)}），连带率{f2(attach_r)}件（同比{pct(attach_yoy,1)}），件单价¥{unit_p:,.0f}（同比{pct(unit_yoy,1)}）。{avg_t_analysis}。提升连带是提高客单的关键抓手",
]
_shoe_variants = [
    f"鞋类流水¥{cat_data['鞋']['flow']/10000:.1f}万，占比{pa(cat_data['鞋']['f_share'],1)}，同比{pct(cat_data['鞋']['yoy'],1)}。SKU动销率仅{pa(cat_data['鞋']['sku_u'],1)}，{cat_data['鞋']['sku_s']}个SKU中约{shoe_zero_pct:.0f}%一周0动销",
    f"鞋类：¥{cat_data['鞋']['flow']/10000:.1f}万（占比{pa(cat_data['鞋']['f_share'],1)}，同比{pct(cat_data['鞋']['yoy'],1)}）。动销率{pa(cat_data['鞋']['sku_u'],1)}偏低，{'多款商品滞销需调整' if cat_data['鞋']['sku_u']<40 else '库存结构尚可'}",
    f"鞋品类流水¥{cat_data['鞋']['flow']/10000:.1f}万、占比{pa(cat_data['鞋']['f_share'],1)}，同比增长{pct(cat_data['鞋']['yoy'],1)}。动销率仅{pa(cat_data['鞋']['sku_u'],1)}，大量SKU滞销亟待优化",
    f"鞋业绩：¥{cat_data['鞋']['flow']/10000:.1f}万（+{cat_data['鞋']['yoy']:.1f}%），占比{pa(cat_data['鞋']['f_share'],1)}。问题在于动销率{pa(cat_data['鞋']['sku_u'],1)}过低，TOP款集中度过高",
]
_strategy_variants = [
    f"""<b>二、本周重点改善策略</b>

1、{worst_day["n"]}复苏：周五企微推送满399-30券，{worst_day["n"]}14-18点最强导购值守。目标达成80%+。

2、成交率抢救（{conv_v:.0f}%→{conv_v+4:.0f}%）：进店话术"欢迎光临今天新品到店"，试穿激励，收银台加价购。周增约¥{conv_lift_amt:,.0f}。

3、SKU瘦身+爆款深耕：筛查2周0动销SKU调出，锁定TOP20鞋款加库存。目标动销率50%+。

4、连带攻坚（{attach_r:.2f}→4.5件）："主推+搭配+连带"1+1+1法。周增约¥{(4.5-attach_r)*tkt_cnt*unit_p:,.0f}。

5、折扣管控（{disc_v:.0f}%→{disc_v-2:.0f}%）：新品首2周正价保护，满减替代直降，鞋服折扣分治。""",
    f"""<b>二、改善建议</b>

❶ 周六定位：{worst_day["n"]}复苏攻坚，目标{pa(worst_day["a"],1)}→80%+，抢回¥{sat_loss:,.0f}损失。

❷ 转化突围：成交率{conv_v:.0f}%→{conv_v+4:.0f}%，重点提升试穿率，预计周增量¥{conv_lift_amt:,.0f}。

❸ 商品瘦身：鞋SKU动销率{cat_data['鞋']['sku_u']:.0f}%→50%+，0动销SKU果断清退。

❹ 连带拉升：{attach_r:.2f}件→4.5件，推"1+1+1"搭配。增量¥{(4.5-attach_r)*tkt_cnt*unit_p:,.0f}。

❺ 折扣优化：{disc_v:.0f}%→{disc_v-2:.0f}%，新品保护+满减替代直降。""",
    f"""<b>二、三大攻坚方向</b>

<u>方向一：流量转化</u>
成交率{conv_v:.0f}%→{conv_v+4:.0f}%，导购进店三句话话术+试穿赠品。目标增量¥{conv_lift_amt:,.0f}。

<u>方向二：商品效率</u>
鞋SKU动销率{cat_data['鞋']['sku_u']:.0f}%→50%，TOP款加库存+动销款补货+滞销款清退。

<u>方向三：客单提升</u>
连带率{attach_r:.2f}件→4.5件，月增¥{(4.5-attach_r)*tkt_cnt*unit_p*4:,.0f}。折扣{pa(disc_v,1)}→{pa(disc_v-2,1)}控毛利。""",
    f"""<b>二、关键战役</b>

🎯 战役1 — {worst_day["n"]}逆袭
{worst_day["n"]}达成率仅{pa(worst_day["a"],1)}，目标拉升到80%+。提前周五发券预热，当日14-18点王牌导购压阵。

🎯 战役2 — 成交率攻坚
{conv_v:.0f}%→{conv_v+4:.0f}%，进店率→试穿率→成交率三步漏斗优化。预计周增量¥{conv_lift_amt:,.0f}。

🎯 战役3 — 商品结构革命
鞋库存{cat_data['鞋']['s_qty']}件，动销率仅{cat_data['鞋']['sku_u']:.0f}%。清退0动销SKU，集中资源打TOP20爆款。""",
]

FULL_TEXT_VARIANTS = [
    f'''<b>{period}周报分析（标准版）</b> | {store} | {week_range}

<b>一、周分析</b>

1、达成：{_achieve_variants[0]}。

2、成交率与客流：{_conv_variants[0]}。

3、客单价与连带：{_ticket_variants[0]}。

4、{_shoe_variants[0]}。

5、服装（按性别）：男¥{cat_data["男"]["flow"]/10000:.1f}万（同比{pct(cat_data["男"]["yoy"],1)}），女¥{cat_data["女"]["flow"]/10000:.1f}万（同比{pct(cat_data["女"]["yoy"],1)}），童装¥{cat_data["童"]["flow"]/10000:.1f}万。

6、器配：¥{cat_data["器配"]["flow"]/10000:.1f}万（同比{pct(cat_data["器配"]["yoy"],1)}），{cat_data["器配"]["sku_s"]}个SKU中动销率{pa(cat_data["器配"]["sku_u"],1)}，每SKU产出{money(cat_data["器配"]["flow"]/cat_data["器配"]["sku_s"])}。

7、日别：{daily_rows[0]["n"]}¥{daily_rows[0]["f"]/10000:.1f}万（达成{pa(daily_rows[0]["a"],1)}）→ {daily_rows[1]["n"]}¥{daily_rows[1]["f"]/10000:.1f}万 → {daily_rows[2]["n"]}¥{daily_rows[2]["f"]/10000:.1f}万 → {daily_rows[3]["n"]}¥{daily_rows[3]["f"]/10000:.1f}万 → {daily_rows[4]["n"]}¥{daily_rows[4]["f"]/10000:.1f}万 → <b>{worst_day["n"]}¥{worst_day["f"]/10000:.1f}万（达成率最低）</b>→ {best_day["n"]}¥{best_day["f"]/10000:.1f}万（达成率最高）。

8、折扣：{pa(disc_v,1)}（同比{disc_yoy_p:+.2f}pp），约{disc_zhe:.1f}折。{disc_str}。

9、O2O：¥{o2o_v/10000:.2f}万（占比{pa(o2o_pct,1)}，环比{pct(o2o_mom,1)}），O2O持续增长。

{_strategy_variants[0]}''',
    f'''<b>{period}周报分析（问题导向版）</b> | {store} | {week_range}

<b>一、核心指标</b>

📌 达成：{_achieve_variants[1]}。

📌 客流与成交：{_conv_variants[1]}。

📌 价格效率：{_ticket_variants[1]}。

📌 鞋类：{_shoe_variants[1]}。

📌 服装分性别：男¥{cat_data["男"]["flow"]/10000:.1f}万（同比{pct(cat_data["男"]["yoy"],1)}）| 女¥{cat_data["女"]["flow"]/10000:.1f}万（同比{pct(cat_data["女"]["yoy"],1)}）| 童¥{cat_data["童"]["flow"]/10000:.1f}万。

📌 器配流水¥{cat_data["器配"]["flow"]/10000:.1f}万（同比{pct(cat_data["器配"]["yoy"],1)}），动销率{pa(cat_data["器配"]["sku_u"],1)}。

📌 周走势：{daily_rows[0]["n"]}¥{daily_rows[0]["f"]/10000:.1f}万 → {daily_rows[1]["n"]}¥{daily_rows[1]["f"]/10000:.1f}万 → {daily_rows[2]["n"]}¥{daily_rows[2]["f"]/10000:.1f}万 → {daily_rows[3]["n"]}¥{daily_rows[3]["f"]/10000:.1f}万 → {daily_rows[4]["n"]}¥{daily_rows[4]["f"]/10000:.1f}万 → ⚠️{worst_day["n"]}¥{worst_day["f"]/10000:.1f}万 → ✅{best_day["n"]}¥{best_day["f"]/10000:.1f}万。

📌 折扣率{pa(disc_v,1)}（同比{disc_yoy_p:+.2f}pp），约{disc_zhe:.1f}折。{disc_str}。

📌 O2O流水¥{o2o_v/10000:.2f}万（环比{pct(o2o_mom,1)}）。

{_strategy_variants[1]}''',
    f'''<b>{period}周报分析（机会导向版）</b> | {store} | {week_range}

<b>一、数据透视</b>

💡 目标达成：{_achieve_variants[2]}。

💡 流量转化：{_conv_variants[2]}。

💡 客单效率：{_ticket_variants[2]}。

💡 鞋类表现：{_shoe_variants[2]}。

💡 服装：男¥{cat_data["男"]["flow"]/10000:.1f}万（同比{pct(cat_data["男"]["yoy"],1)}）| 女¥{cat_data["女"]["flow"]/10000:.1f}万（同比{pct(cat_data["女"]["yoy"],1)}）| 童¥{cat_data["童"]["flow"]/10000:.1f}万。

💡 器配：¥{cat_data["器配"]["flow"]/10000:.1f}万（同比{pct(cat_data["器配"]["yoy"],1)}），{cat_data["器配"]["sku_s"]}个SKU。

💡 日别节奏：{daily_rows[0]["n"]}{pa(daily_rows[0]["a"],1)} → {daily_rows[1]["n"]}{pa(daily_rows[1]["a"],1)} → {daily_rows[3]["n"]}{pa(daily_rows[3]["a"],1)} ← 峰值。{worst_day["n"]}{pa(worst_day["a"],1)} ← 洼地。

💡 折扣：{pa(disc_v,1)}→{disc_zhe:.1f}折，同比{disc_yoy_p:+.2f}pp，环比{disc_mom:+.2f}pp。

💡 O2O：¥{o2o_v/10000:.2f}万（环比{pct(o2o_mom,1)}），{'占比持续提升' if o2o_pct>3 else '占比较低有提升空间'}。

{_strategy_variants[2]}''',
    f'''<b>{period}周报分析（数据深度版）</b> | {store} | {week_range}

<b>一、经营诊断</b>

📊 达成诊断：{_achieve_variants[3]}。

📊 流量分析：{_conv_variants[3]}。

📊 价格分析：{_ticket_variants[3]}。

📊 鞋品类：{_shoe_variants[3]}。

📊 服装：男¥{cat_data["男"]["flow"]/10000:.1f}万（同比{pct(cat_data["男"]["yoy"],1)}）| 女¥{cat_data["女"]["flow"]/10000:.1f}万（同比{pct(cat_data["女"]["yoy"],1)}）| 童¥{cat_data["童"]["flow"]/10000:.1f}万。

📊 器配：¥{cat_data["器配"]["flow"]/10000:.1f}万（同比{pct(cat_data["器配"]["yoy"],1)}），每SKU产出{money(cat_data["器配"]["flow"]/cat_data["器配"]["sku_s"])}。

📊 周走势：周一¥{daily_rows[0]["f"]/10000:.1f}万 → 周五¥{daily_rows[4]["f"]/10000:.1f}万 → <b>{worst_day["n"]}¥{worst_day["f"]/10000:.1f}万</b> → {best_day["n"]}¥{best_day["f"]/10000:.1f}万。周末客流集中但成交率偏低。

📊 折扣策略：{pa(disc_v,1)}（同比{disc_yoy_p:+.2f}pp），约{disc_zhe:.1f}折。{disc_str}。

📊 O2O：¥{o2o_v/10000:.2f}万（环比{pct(o2o_mom,1)}），{'可作为增长第二曲线' if o2o_mom>10 else '需加大推广力度'}。

{_strategy_variants[3]}''',
]

# Embed as JS array
FULL_TEXT_VARIANTS_JS = ',\n'.join(f'`{v}`' for v in FULL_TEXT_VARIANTS)

# ───────── HTML generation ─────────
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="favicon.ico" type="image/x-icon">
<title>{period} 周报分析仪表板 | {store} | v{datetime.now().strftime('%m%d-%H%M')}</title>
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

/* KPI — fixed square blocks, two rows */
.kpi-strip{{border-radius:12px;padding:8px 10px;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:10px;border:1px solid var(--border);display:flex;flex-wrap:wrap;gap:8px;justify-content:center}}
.kpi-strip .ki{{flex:0 0 106px;height:106px;text-align:center;padding:6px 4px;border-radius:8px;background:#f8fafc;display:flex;flex-direction:column;justify-content:center;align-items:center;overflow:hidden}}
.kpi-strip .ki .kv{{font-size:18px;font-weight:800;line-height:1.2}}
.kpi-strip .ki .kl{{font-size:10px;color:var(--sub);margin-top:2px;line-height:1.2}}
.kpi-strip .ki .kc{{font-size:11px;font-weight:600;margin-top:1px;line-height:1.2}}
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
/* (summary-box removed) */

/* Full text */
.full-text{{background:#fafbfc;border-radius:8px;padding:18px 22px;font-size:13px;line-height:1.9;white-space:pre-wrap;max-height:60vh;overflow-y:auto}}

.footer{{text-align:center;padding:20px;color:var(--sub);font-size:11px}}

/* Toast & Import */
.toast{{position:fixed;top:20px;right:20px;z-index:9999;padding:12px 20px;border-radius:8px;color:white;font-weight:600;font-size:13px;box-shadow:0 4px 12px rgba(0,0,0,.15);animation:slideIn .3s ease;display:none}}
.toast.success{{background:var(--green)}}.toast.error{{background:var(--red)}}.toast.info{{background:var(--blue)}}
.toast.show{{display:block}}
@keyframes slideIn{{from{{transform:translateX(100%);opacity:0}}to{{transform:translateX(0);opacity:1}}}}
.btn-primary.loading{{opacity:.7;pointer-events:none;position:relative;padding-left:36px}}
.btn-primary.loading::before{{content:'';position:absolute;left:12px;top:50%;margin-top:-7px;width:14px;height:14px;border:2px solid rgba(255,255,255,.3);border-top-color:white;border-radius:50%;animation:spin .6s linear infinite}}
.btn-primary.loading::after{{content:'分析中...';position:relative}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
@keyframes dots{{0%,20%{{content:'.'}}40%{{content:'..'}}60%{{content:'...'}}80%,100%{{content:''}}}}
</style>
</head>
<body>
<div class="app" id="app">

<div class="toast" id="toast"></div>

<div class="header">
  <div><h1>📊 {period} 周报分析仪表板 <span style="background:#ef4444;color:white;font-size:11px;padding:2px 8px;border-radius:4px;vertical-align:middle">v{datetime.now().strftime('%m%d.%H%M')}</span></h1><div class="meta">{store} | {week_range}</div></div>
  <div class="actions">
    <button class="btn btn-primary" id="btnImport" onclick="triggerImport()">📥 导入周报</button>
    <button class="btn btn-outline" onclick="refreshAllCharts()">🔄 刷新图表</button>
    <input type="file" id="fileInput" accept=".xlsx,.xls" style="display:none" onchange="handleFileImport(event)">
  </div>
</div>

<!-- KPI STRIP - ROW 1 (10 cards) -->
<div class="kpi-strip" id="kpiStrip1">
  <div class="ki"><div class="kv">¥{target_v:,.0f}</div><div class="kl">周目标</div><div class="kc neutral">周度目标</div></div>
  <div class="ki"><div class="kv">¥{actual_v:,.0f}</div><div class="kl">达成金额</div><div class="kc {'up' if yoy_v>0 else 'down'}">较去年同期 {pct(yoy_v,1)}</div></div>
  <div class="ki"><div class="kv" style="color:{'#22c55e' if achieve_v>=100 else '#ef4444'}">{pa(achieve_v,1)}</div><div class="kl">达成率</div><div class="kc" style="color:{'#22c55e' if achieve_v>=100 else '#ef4444'}">{'超目标' if achieve_v>=100 else '未达标'}</div></div>
  <div class="ki"><div class="kv" style="color:{'#ef4444' if yoy_v<0 else '#22c55e'}">{pct(yoy_v,1)}</div><div class="kl">流水同比</div><div class="kc {'up' if yoy_v>0 else 'down'}">同比去年</div></div>
  <div class="ki"><div class="kv" style="color:{'#ef4444' if sssg_v<0 else '#22c55e'}">{pct(sssg_v,1)}</div><div class="kl">SSSG</div><div class="kc {'up' if sssg_v>0 else 'down'}">同店同比</div></div>
  <div class="ki"><div class="kv" style="color:{'#ef4444' if mom_v<0 else '#22c55e'}">{pct(mom_v,1)}</div><div class="kl">环比</div><div class="kc {'up' if mom_v>0 else 'down'}">较上周</div></div>
  <div class="ki"><div class="kv">{money(avg_t)}</div><div class="kl">客单价</div><div class="kc {'up' if avg_t_yoy>0 else 'down'}">{pct(avg_t_yoy,1)}</div></div>
  <div class="ki"><div class="kv">{money(unit_p)}</div><div class="kl">件单价</div><div class="kc {'up' if unit_yoy>0 else 'down'}">{pct(unit_yoy,1)}</div></div>
  <div class="ki"><div class="kv">{f2(attach_r)}件</div><div class="kl">连带率</div><div class="kc {'up' if attach_yoy>0 else 'down'}">{pct(attach_yoy,1)}</div></div>
  <div class="ki"><div class="kv">{pa(conv_v,1)}</div><div class="kl">成交率</div><div class="kc {'up' if conv_yoy>0 else 'down'}">{pct(conv_yoy,1)}pp</div></div>
</div>
<!-- STICKY KPI STRIP - ROW 2 (remaining) -->
<div class="kpi-strip" id="kpiStrip2">
  <div class="ki"><div class="kv">{num(flow_v)}人</div><div class="kl">日均客流</div><div class="kc {'up' if flow_yoy>0 else 'down'}">{pct(flow_yoy,1)}</div></div>
  <div class="ki"><div class="kv">{pa(disc_v,1)}</div><div class="kl">折扣率</div><div class="kc {'up' if disc_yoy_p>0 else 'down'}">{pct(disc_yoy_p,1)}pp</div></div>
  <div class="ki"><div class="kv">{money(o2o_v)}</div><div class="kl">O2O</div><div class="kc {'up' if o2o_mom>0 else 'down'}">{pct(o2o_mom,1)}</div></div>
  <div class="ki"><div class="kv">{pa(cat_data['鞋']['f_share'],1)}</div><div class="kl">鞋占比</div><div class="kc {'up' if cat_data['鞋']['yoy']>0 else 'down'}">{pct(cat_data['鞋']['yoy'],1)}</div></div>
</div>

<!-- ─── SECTION 2: DATA FILTERING ─── -->
<div class="section">
  <h3>📊 数据筛选展示</h3>
  <div class="tabs">
    <button class="tab active" onclick="switchDataTab('daily',this)">日别趋势</button>
    <button class="tab" onclick="switchDataTab('matrix',this)">KPI矩阵</button>
    <button class="tab" onclick="switchDataTab('cate',this)">品类分析</button>
    <button class="tab" onclick="switchDataTab('seas',this)">新品季节</button>
    <button class="tab" onclick="switchDataTab('mid',this)">中类分析</button>
    <button class="tab" onclick="switchDataTab('sub',this)">子品类</button>
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
      <thead><tr><th>品类</th><th>流水</th><th>销量</th><th>销售占比</th><th>同比</th><th>环比</th><th>折扣率</th><th>SKU在售</th><th>SKU动销率</th><th>库存数量</th><th>库存占比</th><th>匹配分析</th></tr></thead>
      <tbody id="cateTable"></tbody>
    </table>
  </div>

  <div id="tab-seas" class="data-tab" style="display:none">
    <div class="grid2">
      <div class="chart-wrap"><canvas id="chartSeasFlow"></canvas></div>
      <div class="chart-wrap"><canvas id="chartSeasRate"></canvas></div>
    </div>
    <div class="grid2" style="margin-top:14px;gap:16px">
      <div>
        <h4 style="font-size:14px;margin-bottom:8px;color:var(--blue)">👕 服 季节对比</h4>
        <table class="tbl" style="width:100%">
          <thead><tr><th>指标</th><th>25Q4旧品</th><th>26Q1</th><th>26Q2</th><th>26Q3+</th><th>26常青</th></tr></thead>
          <tbody id="seasClothTable"></tbody>
        </table>
      </div>
      <div>
        <h4 style="font-size:14px;margin-bottom:8px;color:var(--red)">👟 鞋 季节对比</h4>
        <table class="tbl" style="width:100%">
          <thead><tr><th>指标</th><th>25Q4旧品</th><th>26Q1</th><th>26Q2</th><th>26Q3+</th><th>26常青</th></tr></thead>
          <tbody id="seasShoeTable"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ─── MID-CATEGORY TAB ─── -->
  <div id="tab-mid" class="data-tab" style="display:none">
    <div class="chart-wrap" style="margin-bottom:12px"><canvas id="chartMidCloth"></canvas></div>
    <table class="tbl" style="width:100%">
      {_mid_table_html}
    </table>
  </div>

  <div id="tab-sub" class="data-tab" style="display:none">
    <div class="grid3">
      <div>
        <h4 style="font-size:13px;margin-bottom:8px;color:var(--sub)">服装子品类</h4>
        <table class="tbl"><thead><tr><th>品类</th><th>流水</th><th>销量</th><th>折扣</th></tr></thead><tbody id="subCloth"></tbody></table>
      </div>
      <div>
        <h4 style="font-size:13px;margin-bottom:8px;color:var(--sub)">鞋系列</h4>
        <table class="tbl"><thead><tr><th>系列</th><th>流水</th><th>销量</th><th>折扣</th></tr></thead><tbody id="subShoe"></tbody></table>
      </div>
      <div>
        <h4 style="font-size:13px;margin-bottom:8px;color:var(--sub)">配件子品类</h4>
        <table class="tbl"><thead><tr><th>品类</th><th>流水</th><th>销量</th><th>折扣</th></tr></thead><tbody id="subAcc"></tbody></table>
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
  <button class="btn btn-primary" onclick="renderAnalysis(this)" style="margin-bottom:12px">📊 开始分析</button>
  <button class="btn btn-outline" onclick="refreshFromFeishu()" style="margin-bottom:12px;margin-left:6px;background:#22c55e;color:white;border:none">🔄 刷新飞书数据</button>
  <div id="feishuStatus" style="display:none;margin-bottom:8px;padding:6px 12px;border-radius:6px;font-size:12px"></div>
  <div id="tab-fulltext">
    <div class="full-text" id="fullTextContent" style="color:var(--sub);font-size:13px">点击「开始分析」按钮生成分析报告。</div>
  </div>
</div>

<div class="footer">{store} | {period} 周报分析仪表板 | EdgeOne Pages 部署 | 构建: {datetime.now().strftime('%m-%d %H:%M')} | AI店长出品</div>

</div>

<!-- ─── DATA PAYLOAD ─── -->
<script>
const DATA = {json.dumps(payload, ensure_ascii=False, default=str)};

// ─── TAB SWITCHING ───
function switchDataTab(name, el) {{
  document.querySelectorAll('.data-tab').forEach(e=>e.style.display='none');
  document.getElementById('tab-'+name).style.display='block';
  document.querySelectorAll('.section:first-of-type .tab').forEach(t=>t.classList.remove('active'));
  if(el) el.classList.add('active');
  if(name==='daily'){{ drawDailyCharts(); }}
  if(name==='cate'){{ drawCateCharts(); }}
  if(name==='seas'){{ drawSeasCharts(); }}
  if(name==='mid'){{ drawMidCharts(); }}
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
  <td class="${{D.yoy>0?'hi':'lo'}}">${{D.yoy.toFixed(1)}}%</td><td>${{D.conv.toFixed(2)}}%</td>
  <td>${{D.flow.toFixed(0)}}</td><td>¥${{D.avg_t.toFixed(0)}}</td><td>${{D.attach_r.toFixed(2)}}</td></tr>`;
  document.getElementById('dailyTable').innerHTML=dt;

  // Matrix table
  let mt='';
  D.matrix.forEach(r=>{{
    mt+=`<tr><td>${{r[0]}}</td><td>${{r[1]}}</td><td class="${{r[2].includes('-')?'lo':'hi'}}">${{r[2]}}</td><td class="${{r[3].includes('-')?'lo':'hi'}}">${{r[3]}}</td><td><span class="${{r[2].includes('-')?'tag-down':'tag-up'}}">${{r[2].includes('-')?'⬇️':'⬆️'}}</span></td></tr>`;
  }});
  document.getElementById('matrixTable').innerHTML=mt;

  // Category table (two groups: product + gender)
  let ct='';
  let lastGroup='';
  for(const[cn,cd]of Object.entries(D.category)){{
    if(cd.group&&cd.group!==lastGroup){{
      const gname=cd.group==='product'?'📦 产品类别 (鞋/服/器配)':'👥 顾客性别 (男/女/童)';
      ct+='<tr style="background:#e8edf3;font-weight:700"><td colspan="12" style="text-align:left;padding:7px 10px;font-size:13px">'+gname+'</td></tr>';
      lastGroup=cd.group;
    }}
    if(cd.group==='product'){{
      const mcls=cd.gap>5?'hi':(cd.gap<-5?'lo':'');
      ct+='<tr><td>'+cn+'</td><td>¥'+cd.flow.toLocaleString()+'</td><td>'+(cd.qty?cd.qty.toLocaleString():'—')+'</td><td>'+cd.f_share.toFixed(2)+'%</td>'
        +'<td class="'+(cd.yoy>0?'hi':'lo')+'">'+(cd.yoy>0?'+':'')+cd.yoy.toFixed(2)+'%</td><td class="'+(cd.mom>0?'hi':'lo')+'">'+(cd.mom>0?'+':'')+cd.mom.toFixed(2)+'%</td>'
        +'<td>'+cd.disc.toFixed(2)+'%</td><td>'+cd.sku_s+'</td><td>'+(cd.sku_u&&cd.sku_u>0?cd.sku_u.toFixed(2)+'%':'—')+'</td>'
        +'<td>'+cd.s_qty.toLocaleString()+'</td><td>'+cd.s_q_share.toFixed(2)+'%</td><td class="'+mcls+'">'+cd.match_lbl+'</td></tr>';
    }}else{{
      const ycls=cd.yoy>0?'hi':'lo', mcls=cd.mom>0?'hi':'lo';
      ct+='<tr><td>'+cn+'</td><td>¥'+cd.flow.toLocaleString()+'</td><td>'+(cd.qty?cd.qty.toLocaleString():'—')+'</td><td>'+cd.f_share.toFixed(2)+'%</td>'
        +'<td class="'+ycls+'">'+(cd.yoy>0?'+':'')+cd.yoy.toFixed(2)+'%</td><td class="'+mcls+'">'+(cd.mom>0?'+':'')+cd.mom.toFixed(2)+'%</td>'
        +'<td>'+(cd.disc?cd.disc.toFixed(2)+'%':'—')+'</td><td>'+(cd.sku_s?cd.sku_s:'—')+'</td><td>'+(cd.sku_u&&cd.sku_u>0?cd.sku_u.toFixed(2)+'%':'—')+'</td>'
        +'<td>'+(cd.s_qty?cd.s_qty.toLocaleString():'—')+'</td><td>'+(cd.s_q_share?cd.s_q_share.toFixed(2)+'%':'—')+'</td><td style="color:#94a3b8;font-size:11px">（匹配分析仅产品维度）</td></tr>';
    }}
  }}
  document.getElementById('cateTable').innerHTML=ct;

  // Season tables — two modules: 服 seasons / 鞋 seasons (built in Python to avoid f-string brace issues)
  document.getElementById('seasClothTable').innerHTML='{clothing_seas_html}';
  document.getElementById('seasShoeTable').innerHTML='{shoe_seas_html}';

  // Sub tables
  let sc=''; D.sub_ps.filter(r=>!r.isAcc).forEach(r=>{{ sc+='<tr><td>'+r.n+'</td><td>¥'+r.f.toLocaleString()+'</td><td>'+(r.q?r.q.toLocaleString():'—')+'</td><td>'+(r.d||0).toFixed(2)+'%</td></tr>'; }});
  document.getElementById('subCloth').innerHTML=sc;
  let ss=''; D.shoe.forEach(r=>{{ ss+='<tr><td>'+r.n+'</td><td>¥'+r.f.toLocaleString()+'</td><td>'+r.q+'</td><td>'+(r.d||0).toFixed(2)+'%</td></tr>'; }});
  document.getElementById('subShoe').innerHTML=ss||'<tr><td colspan="4">导入后解析</td></tr>';
  let sa=''; D.sub_ps.filter(r=>r.isAcc).forEach(r=>{{ sa+='<tr><td>'+r.n+'</td><td>¥'+r.f.toLocaleString()+'</td><td>'+(r.q?r.q.toLocaleString():'—')+'</td><td>'+(r.d||0).toFixed(2)+'%</td></tr>'; }});
  document.getElementById('subAcc').innerHTML=sa;

  // Bench table
  var bt='';
  var kmap=[{{k:'conv_rate','n':'成交率','pct':1}},{{k:'daily_flow','n':'日均客流'}},{{k:'target','n':'流水目标'}},{{k:'actual','n':'流水实际'}},{{k:'achieve','n':'达成率','pct':1}},{{k:'sssg','n':'同比%','pct':1}},{{k:'mom','n':'环比%','pct':1}}];
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
  const D=DATA;
  // Chart 1: Product categories (鞋/服/器配)
  const prodCats=['鞋','服','器配'];
  const pFlows=prodCats.map(c=>D.category[c]?.flow||0);
  const pYoys=prodCats.map(c=>D.category[c]?.yoy||0);
  const pDiscs=prodCats.map(c=>D.category[c]?.disc||0);
  destroyChart('chartCateFlow');
  chartInstances.chartCateFlow = new Chart(document.getElementById('chartCateFlow'),{{
    type:'bar', data:{{ labels:prodCats, datasets:[
      {{ label:'流水', data:pFlows, backgroundColor:[colors.redBg,colors.blueBg,colors.amber+'40'], borderColor:[colors.red,colors.blue,colors.amber], borderWidth:1.5, borderRadius:6, yAxisID:'y' }},
      {{ label:'同比%', data:pYoys, type:'line', borderColor:colors.purple, backgroundColor:'transparent', pointRadius:5, pointBackgroundColor:colors.purple, yAxisID:'y1' }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{display:true,text:'产品类别 — 鞋 / 服 / 器配',font:{{size:14}}}}, legend:{{position:'bottom'}} }},
      scales:{{ y:{{ position:'left',ticks:{{ callback:v=>'¥'+v.toLocaleString()}} }}, y1:{{ position:'right',ticks:{{ callback:v=>v.toFixed(0)+'%'}},grid:{{drawOnChartArea:false}} }} }}
    }}
  }});
  // Chart 2: Gender categories (男/女/童)
  const genCats=['男','女','童'];
  const gFlows=genCats.map(c=>D.category[c]?.flow||0);
  const gYoys=genCats.map(c=>D.category[c]?.yoy||0);
  destroyChart('chartCateMatch');
  chartInstances.chartCateMatch = new Chart(document.getElementById('chartCateMatch'),{{
    type:'bar', data:{{ labels:genCats, datasets:[
      {{ label:'流水', data:gFlows, backgroundColor:[colors.blueBg,colors.purple+'40',colors.amber+'40'], borderColor:[colors.blue,colors.purple,colors.amber], borderWidth:1.5, borderRadius:6, yAxisID:'y' }},
      {{ label:'同比%', data:gYoys, type:'line', borderColor:colors.red, backgroundColor:'transparent', pointRadius:5, pointBackgroundColor:colors.red, yAxisID:'y1' }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{display:true,text:'顾客性别 — 男 / 女 / 童',font:{{size:14}}}}, legend:{{position:'bottom'}} }},
      scales:{{ y:{{ position:'left',ticks:{{ callback:v=>'¥'+v.toLocaleString()}} }}, y1:{{ position:'right',ticks:{{ callback:v=>v.toFixed(0)+'%'}},grid:{{drawOnChartArea:false}} }} }}
    }}
  }});
}}


function drawSeasCharts() {{
  const D=DATA;
  // Seasons for comparison (服 & 鞋 share the same season labels)
  const seasLabels=['25Q4旧品','26Q1','26Q2','26Q3+','常青'];
  const cKeys=['2025Q4及以前(服)','2026Q1(服)','2026Q2(服)','2026Q3+(服)','26年常青(服)'];
  const sKeys=['2025Q4及以前(鞋)','2026Q1(鞋)','2026Q2(鞋)','2026Q3+(鞋)','26年常青(鞋)'];
  // Flow + 环比 trend comparison
  const cFlows=cKeys.map(k=>D.seas[k]?D.seas[k].f:0);
  const sFlows=sKeys.map(k=>D.seas[k]?D.seas[k].f:0);
  const cMoms=cKeys.map(k=>D.seas[k]?D.seas[k].mom:null);
  const sMoms=sKeys.map(k=>D.seas[k]?D.seas[k].mom:null);
  destroyChart('chartSeasFlow');
  chartInstances.chartSeasFlow = new Chart(document.getElementById('chartSeasFlow'),{{
    type:'bar', data:{{ labels:seasLabels, datasets:[
      {{ label:'服流水', data:cFlows, backgroundColor:colors.blueBg, borderColor:colors.blue, borderWidth:1.5, borderRadius:4, yAxisID:'y' }},
      {{ label:'鞋流水', data:sFlows, backgroundColor:colors.redBg, borderColor:colors.red, borderWidth:1.5, borderRadius:4, yAxisID:'y' }},
      {{ label:'服环比', data:cMoms, type:'line', borderColor:colors.blue, backgroundColor:'transparent', pointRadius:5, pointBackgroundColor:colors.blue, borderDash:[5,3], yAxisID:'y1', tension:0.3 }},
      {{ label:'鞋环比', data:sMoms, type:'line', borderColor:colors.red, backgroundColor:'transparent', pointRadius:5, pointBackgroundColor:colors.red, borderDash:[5,3], yAxisID:'y1', tension:0.3 }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{display:true,text:'各季节流水 & 环比趋势',font:{{size:14}}}}, legend:{{position:'bottom'}} }},
      scales:{{ y:{{ position:'left',ticks:{{ callback:v=>'¥'+v.toLocaleString()}} }}, y1:{{ position:'right',ticks:{{ callback:v=>v.toFixed(0)+'%'}},grid:{{drawOnChartArea:false}} }} }}
    }}
  }});
  // 流水占比(柱状) vs 库存占比(实线) comparison
  const cFShares=cKeys.map(k=>D.seas[k]?D.seas[k].fs:0);
  const sFShares=sKeys.map(k=>D.seas[k]?D.seas[k].fs:0);
  const cStkShares=cKeys.map(k=>D.seas[k]?D.seas[k].stk_share:0);
  const sStkShares=sKeys.map(k=>D.seas[k]?D.seas[k].stk_share:0);
  destroyChart('chartSeasRate');
  chartInstances.chartSeasRate = new Chart(document.getElementById('chartSeasRate'),{{
    type:'bar', data:{{ labels:seasLabels, datasets:[
      {{ label:'服流水占比', data:cFShares, backgroundColor:colors.blueBg, borderColor:colors.blue, borderWidth:1.5, borderRadius:4 }},
      {{ label:'鞋流水占比', data:sFShares, backgroundColor:colors.redBg, borderColor:colors.red, borderWidth:1.5, borderRadius:4 }},
      {{ label:'服库存占比', data:cStkShares, type:'line', borderColor:colors.blue, backgroundColor:'transparent', pointRadius:5, pointBackgroundColor:colors.blue, tension:0.3, borderWidth:2.5 }},
      {{ label:'鞋库存占比', data:sStkShares, type:'line', borderColor:colors.red, backgroundColor:'transparent', pointRadius:5, pointBackgroundColor:colors.red, tension:0.3, borderWidth:2.5 }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{display:true,text:'流水占比(柱) vs 库存占比(线)',font:{{size:14}}}}, legend:{{position:'bottom'}} }},
      scales:{{ y:{{ ticks:{{ callback:v=>v.toFixed(1)+'%'}}, max:80 }} }}
    }}
  }});
}}

function drawMidCharts() {{
  const D=DATA, ma=D.mid_agg;
  if(!ma) return;
  const colors=window.chartColors||{{blue:'#3b82f6',blueBg:'#dbeafe',red:'#ef4444',redBg:'#fee2e2',purple:'#8b5cf6',purpleBg:'#ede9fe',amber:'#f59e0b',gray:'#94a3b8'}};
  // 四中类 流水占比 vs 库存占比
  const cats=['男服','女服','男鞋','女鞋'];
  const flows=cats.map(n=>ma[n]?.f||0);
  const stocks=cats.map(n=>ma[n]?.stock_qty||0);
  const totalFlow=flows.reduce((a,b)=>a+b,0);
  const totalStock=stocks.reduce((a,b)=>a+b,0);
  const flowShares=flows.map(f=>totalFlow?f/totalFlow*100:0);
  const stockShares=stocks.map(s=>totalStock?s/totalStock*100:0);
  const barColors=[colors.blueBg,colors.purpleBg,colors.redBg,colors.amber+'40'];
  const borderColors=[colors.blue,colors.purple,colors.red,colors.amber];
  destroyChart('chartMidCloth'); // reuse first canvas
  chartInstances.chartMidCloth = new Chart(document.getElementById('chartMidCloth'),{{
    type:'bar', data:{{ labels:cats, datasets:[
      {{ label:'流水占比', data:flowShares, backgroundColor:barColors, borderColor:borderColors, borderWidth:1.5, borderRadius:4 }},
      {{ label:'库存占比', data:stockShares, type:'line', borderColor:'#059669', backgroundColor:'transparent', pointRadius:6, pointBackgroundColor:'#059669', tension:0.3, borderWidth:3 }}
    ]}},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{display:true,text:'四中类 流水占比 vs 库存占比',font:{{size:14}}}}, legend:{{position:'bottom'}} }},
      scales:{{ y:{{ ticks:{{ callback:v=>v.toFixed(1)+'%'}}, max:60 }} }}
    }}
  }});
  // Hide second canvas (no longer needed)
  const c2=document.getElementById('chartMidShoe');
  if(c2) c2.style.display='none';
}}

function refreshAllCharts() {{
  Object.keys(chartInstances).forEach(k=>{{chartInstances[k].destroy();delete chartInstances[k];}});
  drawDailyCharts();
  const activeTab=document.querySelector('.data-tab[style*="block"]');
  if(activeTab&&activeTab.id==='tab-cate')drawCateCharts();
  if(activeTab&&activeTab.id==='tab-seas')drawSeasCharts();
  if(activeTab&&activeTab.id==='tab-mid')drawMidCharts();
}}

function refreshFromFeishu(){{
  var st=document.getElementById('feishuStatus');
  st.style.display='block'; st.style.background='#eff6ff'; st.style.color='#3b82f6';
  st.textContent='🔄 正在从飞书获取最新数据...';
  fetch('/feishu/fetch').then(r=>r.json()).then(function(d){{
    if(d.period&&d.period!=='W??'){{
      DATA.store=d.store||DATA.store;
      DATA.period=d.period;
      DATA.week_range=d.week_range||DATA.week_range;
      document.querySelector('.header .meta').textContent=DATA.store+' | '+DATA.week_range;
      document.querySelector('.header h1').innerHTML='📊 '+DATA.period+' 周报分析仪表板 <span style=\"background:#ef4444;color:white;font-size:11px;padding:2px 8px;border-radius:4px;vertical-align:middle\">飞书</span>';
      buildKpiStrip(); initTables(); refreshAllCharts();
      st.style.background='#f0fdf4'; st.style.color='#065f46';
      st.innerHTML='✅ '+DATA.period+' 数据已刷新 | <a href=\"https://stuart105.github.io/weekly-dashboard/\" target=\"_blank\">GitHub Pages</a>';
    }}else{{
      st.style.background='#fef2f2'; st.style.color='#991b1b';
      st.textContent='⚠️ 未获取到数据，请确认飞书表格已填入最新周报';
    }}
  }}).catch(function(e){{
    st.style.background='#fef2f2'; st.style.color='#991b1b';
    st.textContent='⚠️ 刷新失败: 请通过CodeBuddy预览链接访问 (GitHub Pages不支持此功能)';
    console.error(e);
  }});
}}

// Full text content
const FULL_TEXTS=[{FULL_TEXT_VARIANTS_JS}];

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
      buildKpiStrip(); initTables(); refreshAllCharts();
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
  // 核心改进: sheet→二维数组，O(1)取值，消除xlsx类型不确定性
  const Am=XLSX.utils.sheet_to_json(wsMain,{{header:1,defval:null}});
  const As=wsSeas?XLSX.utils.sheet_to_json(wsSeas,{{header:1,defval:null}}):null;
  const Au=wsMember?XLSX.utils.sheet_to_json(wsMember,{{header:1,defval:null}}):null;
  function get(arr,r,c){{ if(!arr)return null;var row=arr[r-1];if(!row)return null;return row[c-1]!==null&&row[c-1]!==undefined?row[c-1]:null; }}
  function gn(arr,r,c){{ var v=get(arr,r,c); if(v===null||v===undefined||v==='') return 0; var n=Number(v); return isNaN(n)?0:n; }}
  function gs(arr,r,c){{ var v=get(arr,r,c); return v!==null&&v!==undefined?String(v):''; }}
  const kpiRow=findRow(wsMain,'KPI')||7;
  const priceRow=findRow(wsMain,'件单价')||(kpiRow+8);
  const dailyStart=kpiRow+14;
  const cateStart=findRow(wsMain,'吊牌价')||35;
  const clothStart=findRow(wsMain,'服装系列')||62;
  const shoeStart=findRow(wsMain,'鞋系列')||76;
  const subPsStart=findRow(wsMain,'裙类')||findRow(wsMain,'器配',4)||91;
  const topStart=findRow(wsMain,'TOP')||findRow(wsMain,'TOP商品')||123;
  const discStart=findRow(wsMain,'单件')||208;
  const store=gs(Am,2,1)||'未知店铺';
  const rawP=gs(Am,2,23); const pM=rawP.match(/W(\\d+)/);
  const period=pM?pM[0]:'W??', weekRange=rawP.replace(/W\\d+周累计[：:]\\s*/,'').replace(/至/g,'-')||'';
  const r7={{}}; [4,5,6,7,8,10,12,14,17,20,22,24,28,33,35,36,37,39].forEach(c=>r7[c]=gn(Am,kpiRow,c));
  const r15={{}}; [4,6,8,10,12,14,16,18,20,22,24,28,30,32].forEach(c=>r15[c]=gn(Am,priceRow,c));
  const dayC=[4,6,8,10,12,14,16,18], dn=['周一','周二','周三','周四','周五','周六','周日'];
  const daily=[]; for(let i=0;i<7;i++) daily.push({{n:dn[i],t:gn(Am,dailyStart+0,dayC[i]),f:gn(Am,dailyStart+1,dayC[i]),a:gn(Am,dailyStart+2,dayC[i])*100,y:gn(Am,dailyStart+3,dayC[i])*100,c:gn(Am,dailyStart+6,dayC[i])*100,v:Math.round(gn(Am,dailyStart+7,dayC[i])),tk:gn(Am,dailyStart+8,dayC[i]),at:gn(Am,dailyStart+9,dayC[i])}});
  const catC={{'14':'鞋','16':'服','18':'器配','4':'男','6':'女','10':'童'}}; const catData={{}};
  for(const[col,nm]of Object.entries(catC)){{ 
    const cn=parseInt(col); 
    const isProduct=cn>=14;
    const f=gn(Am,cateStart+1,cn), ss=gn(Am,cateStart+12,cn);
    catData[nm]={{flow:f,qty:gn(Am,cateStart+2,cn),disc:gn(Am,cateStart+3,cn)*100,yoy:gn(Am,cateStart+7,cn)*100,mom:gn(Am,cateStart+5,cn)*100,f_share:gn(Am,cateStart+9,cn)*100,group:isProduct?'product':'gender',sku_s:ss,s_qty:gn(Am,cateStart+17,cn),s_sku:gn(Am,cateStart+18,cn),sku_u:gn(Am,cateStart+15,cn)*100,sat:gn(Am,cateStart+21,cn)*100,st:gn(Am,cateStart+22,cn)*100}};
  }}
  const tsq=Object.values(catData).filter(c=>c.group==='product').reduce((s,c)=>s+(c.s_qty||0),0);
  for(const[nm,cd]of Object.entries(catData)){{ if(cd.group!=='product') continue; const sqs=tsq>0?(cd.s_qty/tsq*100):0,fs=cd.f_share; cd.s_q_share=sqs; cd.gap=fs-sqs; cd.match_lbl=Math.abs(fs-sqs)<=5?'匹配':(fs>sqs?'销>库+'+((fs-sqs).toFixed(1))+'pp':'库>销'+((sqs-fs).toFixed(1))+'pp'); }}
  const topData={{}}; const tl={{'0':'TOP10','1':'TOP20','2':'TOP40','3':'TOP60','4':'TOP100'}};
  for(let i=0;i<5;i++){{ const r=topStart+i,d4=get(Am,r,4),d6=get(Am,r,6); if(d4!==null||d6!==null) topData[tl[String(i)]]={{'4':(Number(d4)||0)*100,'6':(Number(d6)||0)*100,'8':gn(Am,r,8)*100,'10':gn(Am,r,10)*100,'13':gn(Am,r,13)*100}}; }}
  const subPs=[]; let inSubPs=false, inAcc=false;
  for(let r=subPsStart;r<=subPsStart+40&&r<=180;r++){{
    const label=gs(Am,r,1); const flow=gn(Am,r,8);
    if(label==='合计'&&inSubPs&&!inAcc){{ inAcc=true; continue; }}
    if(label==='合计'&&inAcc) break;
    if(label&&flow&&!label.includes('器配')&&!label.includes('奥莱')&&!label.includes('销售')){{
      if(!inSubPs) inSubPs=true;
      const disc=gn(Am,r,10), qty=gn(Am,r,4);
      const entry={{isAcc:!!inAcc,n:label,f:flow,d:disc?disc*100:0,q:qty?Math.round(qty):0}};
      subPs.push(entry);
    }}
  }}
  const shoeSeries=[];
  for(let r=shoeStart+1;r<=shoeStart+20&&r<=120;r++){{
    const label=gs(Am,r,1); if(label==='合计') break;
    const flow=gn(Am,r,8);
    if(label&&flow) shoeSeries.push({{n:label,f:flow,q:gn(Am,r,4)?Math.round(gn(Am,r,4)):0,d:gn(Am,r,10)*100}});
  }}
  const seasData={{}};
  if(As){{
    const sHdr=findRow(wsSeas,'产品季',4)||3;
    const seasFlowRow=findRow(wsSeas,'流水',1)||sHdr+2;
    const seasDiscRow=seasFlowRow+2; const seasQtyRow=seasFlowRow+1;
    const seasSkuURow=findRow(wsSeas,'SKU动销',1)||16;
    const seasSatRow=findRow(wsSeas,'无可补',1)||25;
    const seasKeys=[['4','2025Q4及以前(服)'],['6','2026Q1(服)'],['8','2026Q2(服)'],['10','2026Q3+(服)'],['13','26年常青(服)'],['15','2025Q4及以前(鞋)'],['18','2026Q1(鞋)'],['20','2026Q2(鞋)'],['22','2026Q3+(鞋)'],['25','26年常青(鞋)']];
    for(const[ck,lb]of seasKeys){{ const cn=parseInt(ck); const f=get(As,seasFlowRow,cn); if(f!==null) seasData[lb]={{f:Number(f),d:gn(As,seasDiscRow,cn)*100,q:Math.round(gn(As,seasQtyRow,cn)),su:gn(As,seasSkuURow,cn)*100,sat:gn(As,seasSatRow,cn)*100}}; }}
  }}
  const discRange={{}};
  for(let r=discStart;r<=discStart+3&&r<=220;r++){{ const label=gs(Am,r,1); if(!label) continue; discRange[String(r)]={{label:label,cols:{{}}}}; for(let c=1;c<=15;c++){{ var v=get(Am,r,c); if(v!==null&&v!==undefined) discRange[String(r)].cols[String(c)]=v; }} }}
  const memberData=[];
  if(Au){{ const memStart=findRow(wsMember,'销售')-1||7; for(let r=memStart;r<=memStart+15&&r<=30;r++){{ const id=gs(Au,r,1); const name=gs(Au,r,3); const sales=gn(Au,r,9); if(name&&sales>0) memberData.push({{id:id,name:name,sales:sales,qty:Math.round(gn(Au,r,10)),unitPrice:gn(Au,r,11),avgTicket:gn(Au,r,12),attach:gn(Au,r,13),shoePct:gn(Au,r,15)*100,clothPct:gn(Au,r,16)*100,o2o:gn(Au,r,17)}}); }} }}
  const t=r7[14],act=r7[17],ach=r7[20]*100,co=r7[5]*100,fl=r7[8],ss=r7[24]*100,yo=r7[22]*100,mo=r7[28]*100;
  const oo=r7[33],op=r7[35]*100,pd=r7[37],ol=r7[39];
  const at=r15[10],up=r15[4],ar=r15[16],di=r15[28]*100,tc=r15[22];
  const cy=r7[6]*100,fy=r7[10]*100,ay=r15[12]*100,ayy=r15[18]*100,uy=r15[6]*100,dy=r15[30]*100,om=r7[36]*100,cm=r7[7]*100,fm=r7[12]*100;
  const mfmt=v=>v>=10000?((v/10000).toFixed(1)+'万'):('¥'+v.toFixed(0));
  const mat=[['流水达成率',ach.toFixed(2)+'%',(yo>0?'+':'')+yo.toFixed(2)+'%',(mo>0?'+':'')+mo.toFixed(2)+'%'],['成交率',co.toFixed(2)+'%',(cy>0?'+':'')+cy.toFixed(2)+'%pp',(cm>0?'+':'')+cm.toFixed(2)+'%pp'],['日均客流',fl.toFixed(0)+'人',(fy>0?'+':'')+fy.toFixed(2)+'%',(fm>0?'+':'')+fm.toFixed(2)+'%'],['客单价',(at>=10000?((at/10000).toFixed(1)+'万'):('¥'+at.toFixed(0))),(ay>0?'+':'')+ay.toFixed(2)+'%',(ay>0?'+':'')+ay.toFixed(2)+'%'],['连带率',ar.toFixed(2)+'件',(ayy>0?'+':'')+ayy.toFixed(2)+'%',(ayy>0?'+':'')+ayy.toFixed(2)+'%'],['件单价',(up>=10000?((up/10000).toFixed(1)+'万'):('¥'+up.toFixed(0))),(uy>0?'+':'')+uy.toFixed(2)+'%',(uy>0?'+':'')+uy.toFixed(2)+'%'],['折扣率',di.toFixed(2)+'%',(dy>0?'+':'')+dy.toFixed(2)+'%pp',(dy>0?'+':'')+dy.toFixed(2)+'%pp'],['O2O流水',(oo>=10000?((oo/10000).toFixed(1)+'万'):('¥'+oo.toFixed(0))),'--',(om>0?'+':'')+om.toFixed(2)+'%'],['SSSG',(ss>0?'+':'')+ss.toFixed(2)+'%',(ss>0?'+':'')+ss.toFixed(2)+'%',(mo>0?'+':'')+mo.toFixed(2)+'%']];
  const sh=catData['鞋']?catData['鞋'].f_share:0,su=catData['鞋']?catData['鞋'].sku_u:0;
  return {{store,period,week_range:weekRange,target:t,actual:act,achieve:ach,yoy:yo,mom:mo,sssg:ss,conv:co,flow:fl,avg_t:at,unit_p:up,attach_r:ar,disc:di,o2o:oo,o2o_pct:op,tkt_cnt:tc,pad:pd,o2o_online:ol,conv_yoy:cy,flow_yoy:fy,avg_t_yoy:ay,attach_yoy:ayy,unit_yoy:uy,disc_yoy_p:dy,o2o_mom:om,conv_mom:cm,flow_mom:fm,daily,category:catData,matrix:mat,top:topData,sub_ps:subPs,shoe:shoeSeries,seas:seasData,disc_range:discRange,member:memberData,shoe_share:sh,shoe_sku_u:su,total_stock_qty:tsq,shoe_s_qty:catData['鞋']?catData['鞋'].s_qty:0,shoe_s_sku:catData['鞋']?catData['鞋'].s_sku:0}};
}}

// ─── P1-1: computeDerivedMetrics ───
function computeDerivedMetrics(d){{
  const w=(d.category['鞋']?d.category['鞋'].flow:0);
  const shoePS=w/(d.category['鞋']?d.category['鞋'].sku_s:1);
  const accPS=(d.category['器配']?d.category['器配'].flow:0)/(d.category['器配']?d.category['器配'].sku_s:1);
  const cs=Object.entries(d.category).filter(([n,c])=>c.group==='product').sort((a,b)=>a[1].yoy-b[1].yoy);
  const wc=cs[0]?cs[0][0]:'--',wy=cs[0]?cs[0][1].yoy:0;
  const sat=d.daily[5];
  return{{shoePerSku:shoePS,accPerSku:accPS,worstCat:wc,worstCatYoy:wy,
    yoyGap:d.actual/(1+d.yoy/100)-d.actual,satGap:sat.t-sat.f,
    ticketGap:(600-d.avg_t)*d.tkt_cnt,attachGap:(4.5-d.attach_r)*d.tkt_cnt*d.unit_p,
    satAchieve:sat.a,satFlow:sat.f,satTarget:sat.t,satVisitors:sat.v,satTicket:sat.tk,satAttach:sat.at,
    sunFlow:d.daily[6].f,thuAchive:d.daily[3].a,thuTicket:d.daily[3].tk,thuAttach:d.daily[3].at,
    allCatsDown:Object.values(d.category).filter(c=>c.group==='product').every(c=>c.yoy<-15),
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
  if(m.discountSpiral) ps.push({{id:'discount_spiral',severity:'medium',title:'折扣率'+d.disc.toFixed(1)+'%持续走高 — 越打折越卖不动',loss:'折扣率环比'+(d.disc_mom>0?'+':'')+d.disc_mom.toFixed(1)+'pp但流水环比'+(d.mom>0?'+':'')+d.mom.toFixed(1)+'%',data:'综合折扣'+d.disc.toFixed(1)+'%（约'+((100-d.disc)/10).toFixed(1)+'折）| 同比'+(d.disc_yoy_p>0?'+':'')+d.disc_yoy_p.toFixed(1)+'pp | 环比'+(d.disc_mom>0?'+':'')+d.disc_mom.toFixed(1)+'pp',cause:'折扣加深→流水反降→继续加深折扣的恶性循环'}});
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

function renderAnalysis(el){{
  const btn=el||document.querySelector('button[onclick*=\"renderAnalysis\"]');
  if(btn){{ btn.classList.add('loading'); btn.disabled=true; }}
  showToast('🔄 正在生成分析报告...','info');
  setTimeout(()=>{{
    // Pick a random variant each time
    const idx=Math.floor(Math.random()*FULL_TEXTS.length);
    document.getElementById('fullTextContent').innerHTML=FULL_TEXTS[idx];
    if(btn){{ btn.classList.remove('loading'); btn.disabled=false; }}
    showToast('✅ 分析完成（风格'+idx+')','success');
  }},500);
}}

function buildKpiStrip(){{
  const D=DATA, fmt=v=>v>=10000?((v/10000).toFixed(1)+'万'):('¥'+v.toFixed(0)), pc=v=>(v>0?'+':'')+v.toFixed(1)+'%', pa=v=>v.toFixed(1)+'%', cl=v=>v>=0?'up':'down';
  // Row 1
  const h1=[];
  h1.push('<div class="ki"><div class="kv">¥'+D.target.toLocaleString()+'</div><div class="kl">周目标</div><div class="kc neutral">周度目标</div></div>');
  h1.push('<div class="ki"><div class="kv">¥'+D.actual.toLocaleString()+'</div><div class="kl">达成金额</div><div class="kc '+cl(D.yoy)+'">较去年同期 '+pc(D.yoy)+'</div></div>');
  h1.push('<div class="ki"><div class="kv" style="color:'+(D.achieve>=100?'#22c55e':'#ef4444')+'">'+D.achieve.toFixed(1)+'%</div><div class="kl">达成率</div><div class="kc" style="color:'+(D.achieve>=100?'#22c55e':'#ef4444')+'">'+(D.achieve>=100?'超目标':'未达标')+'</div></div>');
  h1.push('<div class="ki"><div class="kv" style="color:'+(D.yoy<0?'#ef4444':'#22c55e')+'">'+pc(D.yoy)+'</div><div class="kl">流水同比</div><div class="kc '+cl(D.yoy)+'">同比去年</div></div>');
  h1.push('<div class="ki"><div class="kv" style="color:'+(D.sssg<0?'#ef4444':'#22c55e')+'">'+pc(D.sssg)+'</div><div class="kl">SSSG</div><div class="kc '+cl(D.sssg)+'">同店同比</div></div>');
  h1.push('<div class="ki"><div class="kv" style="color:'+(D.mom<0?'#ef4444':'#22c55e')+'">'+pc(D.mom)+'</div><div class="kl">环比</div><div class="kc '+cl(D.mom)+'">较上周</div></div>');
  h1.push('<div class="ki"><div class="kv">'+fmt(D.avg_t)+'</div><div class="kl">客单价</div><div class="kc '+cl(D.avg_t_yoy)+'">'+pc(D.avg_t_yoy)+'</div></div>');
  h1.push('<div class="ki"><div class="kv">'+fmt(D.unit_p)+'</div><div class="kl">件单价</div><div class="kc '+cl(D.unit_yoy)+'">'+pc(D.unit_yoy)+'</div></div>');
  h1.push('<div class="ki"><div class="kv">'+D.attach_r.toFixed(2)+'件</div><div class="kl">连带率</div><div class="kc '+cl(D.attach_yoy)+'">'+pc(D.attach_yoy)+'</div></div>');
  h1.push('<div class="ki"><div class="kv">'+D.conv.toFixed(1)+'%</div><div class="kl">成交率</div><div class="kc '+cl(D.conv_yoy)+'">'+pa(D.conv_yoy)+'pp</div></div>');
  document.getElementById('kpiStrip1').innerHTML=h1.join('');
  // Row 2
  const h2=[];
  h2.push('<div class="ki"><div class="kv">'+D.flow.toFixed(0)+'人</div><div class="kl">日均客流</div><div class="kc '+cl(D.flow_yoy)+'">'+pc(D.flow_yoy)+'</div></div>');
  h2.push('<div class="ki"><div class="kv">'+D.disc.toFixed(1)+'%</div><div class="kl">折扣率</div><div class="kc '+cl(D.disc_yoy_p)+'">'+pa(D.disc_yoy_p)+'pp</div></div>');
  h2.push('<div class="ki"><div class="kv">'+fmt(D.o2o)+'</div><div class="kl">O2O</div><div class="kc '+cl(D.o2o_mom)+'">'+pc(D.o2o_mom)+'</div></div>');
  let shoeYoy = D.category&&D.category['鞋']?D.category['鞋'].yoy:0;
  h2.push('<div class="ki"><div class="kv">'+D.shoe_share.toFixed(1)+'%</div><div class="kl">鞋占比</div><div class="kc '+cl(shoeYoy)+'">'+pc(shoeYoy)+'</div></div>');
  document.getElementById('kpiStrip2').innerHTML=h2.join('');
}}

// ─── INIT ───
window.addEventListener('DOMContentLoaded',()=>{{
  buildKpiStrip();
  initTables();
  drawDailyCharts();
}});
</script>
</body>
</html>'''

with open(f'{BASE}/weekly-dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)
with open(f'{BASE}/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Dashboard built: {BASE}/weekly-dashboard.html ({len(html):,} bytes)")
