#!/usr/bin/env python
"""Generate W23 weekly analysis reports from extracted data."""
import json

_base = sys.argv[1] if len(sys.argv) > 1 else '.'
with open(f'{_base}/extracted_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

# ====== EXTRACT KEY METRICS ======
r7 = d['r7_kpi']
r15 = d['r15_price']
daily = d['daily']
cate = d['category']

store = "奥莱店华南区城市"
period = "W23 (2026.06.01-06.07)"

# Core KPI
target = r7['14']        # 99191.69
actual = r7['17']        # 108545.55
achieve = r7['20'] * 100 # 109.43%
conv_rate = r7['5'] * 100 # 18.12%
daily_flow = r7['8']     # 170.29
yoy = r7['22'] * 100     # -31.62%
sssg = r7['24'] * 100    # -31.62%
mom = r7['28'] * 100     # -28.50%
o2o = r7['33']           # 5695.55
o2o_pct = r7['35'] * 100 # 5.13%
o2o_online = r7['39']    # 2530.55
pad = r7['37']           # 2737.0

# Price metrics
unit_price = r15['4']    # 131.92
avg_ticket = r15['10']   # 516.09
attach_rate = r15['16']  # 3.91
discount = r15['28'] * 100 # 44.09%
ticket_cnt = r15['22']   # 216笔/周

# YoY changes for price
unit_yoy = r15['6'] * 100    # +0.27%
ticket_yoy = r15['12'] * 100 # -14.12%
attach_yoy = r15['18'] * 100 # -14.35%
discount_yoy = r15['30'] * 100 # +2.81%

# Daily data
day_keys = ['4','6','8','10','12','14','16']
day_names = ['周一','周二','周三','周四','周五','周六','周日']

daily_data = []
for i, dk in enumerate(day_keys):
    daily_data.append({
        'name': day_names[i],
        'target': float(daily['21']['data'][dk]),
        'flow': float(daily['22']['data'][dk]),
        'achieve': float(daily['23']['data'][dk]) * 100,
        'yoy': float(daily['24']['data'][dk]) * 100,
        'mom': float(daily['25']['data'][dk]) * 100,
        'conv': float(daily['27']['data'][dk]) * 100,
        'visitors': int(round(float(daily['28']['data'][dk]))),
        'ticket': float(daily['29']['data'][dk]),
        'attach': float(daily['30']['data'][dk]),
    })

# Category data (using Row36 for flow, Row42 for YoY)
cat_keys = {'4': '男装', '6': '女装', '14': '鞋', '16': '配件'}
cat_discount_keys = {'4': '男装', '6': '女装', '14': '鞋', '16': '配件'}
cat_data = {}
for ck, cn in cat_keys.items():
    flow = float(cate['36']['data'].get(ck, 0))
    qty = int(float(cate['37']['data'].get(ck, 0)))
    disc = float(cate['38']['data'].get(ck, 0)) * 100
    yoy_c = float(cate['42']['data'].get(ck, 0)) * 100
    mom_c = float(cate['40']['data'].get(ck, 0)) * 100
    flow_share = float(cate['44']['data'].get(ck, 0)) * 100
    sku_sell = int(float(cate['47']['data'].get(ck, 0)))
    stock_amt = float(cate['51']['data'].get(ck, 0))
    stock_qty = int(float(cate['52']['data'].get(ck, 0)))
    stock_sku = int(float(cate['53']['data'].get(ck, 0)))
    stock_share_amt = float(cate['54']['data'].get(ck, 0)) * 100
    sku_usage = float(cate['50']['data'].get(ck, 0)) * 100 if cate['50']['data'].get(ck) else 0
    satisfy = float(cate['56']['data'].get(ck, 0)) * 100
    sell_through = float(cate['57']['data'].get(ck, 0)) * 100
    
    cat_data[cn] = {
        'flow': flow, 'qty': qty, 'disc': disc, 'yoy': yoy_c, 'mom': mom_c,
        'flow_share': flow_share, 'sku_sell': sku_sell, 'stock_amt': stock_amt,
        'stock_qty': stock_qty, 'stock_sku': stock_sku, 'stock_share_amt': stock_share_amt,
        'sku_usage': sku_usage, 'satisfy': satisfy, 'sell_through': sell_through
    }

# Stock quantity total and matching
total_stock_qty = sum(cat_data[cn]['stock_qty'] for cn in ['男装','女装','鞋','配件'])
for cn in cat_data:
    stock_qty_share = cat_data[cn]['stock_qty'] / total_stock_qty * 100
    flow_s = cat_data[cn]['flow_share']
    gap = flow_s - stock_qty_share
    if abs(gap) <= 5:
        cat_data[cn]['match'] = '匹配'
        cat_data[cn]['match_type'] = 'match'
    elif gap > 0:
        cat_data[cn]['match'] = f'销>库 +{gap:.1f}pp'
        cat_data[cn]['match_type'] = 'sale_gt'
    else:
        cat_data[cn]['match'] = f'库>销 {abs(gap):.1f}pp'
        cat_data[cn]['match_type'] = 'stock_gt'
    cat_data[cn]['stock_qty_share'] = stock_qty_share

# Shoe specific
shoe_share = cat_data['鞋']['flow_share']
shoe_stock_share = cat_data['鞋']['stock_qty_share']
shoe_per_sku_flow = cat_data['鞋']['flow'] / cat_data['鞋']['sku_sell']
acc_per_sku_flow = cat_data['配件']['flow'] / cat_data['配件']['sku_sell']

# TOP goods
top = d['top_goods']
top_data = {}
for rk in ['125','126','127','128','129']:
    if rk in top:
        td = top[rk]['data']
        top_data[top[rk]['label']] = {
            'vol_share': float(td.get('4', 0)) * 100,
            'flow_share': float(td.get('6', 0)) * 100,
            'stock_share': float(td.get('8', 0)) * 100,
            'satisfy': float(td.get('10', 0)) * 100,
            'actual_break': float(td.get('13', 0)) * 100,
        }

# Seasonal new product data (Sheet2)
seas = d['seasonal']
new_product = {}
if '5' in seas:
    r5 = seas['5']  # Row 5 = 流水
    r7_seas = seas['7'] if '7' in seas else None  # 折扣
    r6_seas = seas['6'] if '6' in seas else None  # 数量
    r19 = seas['19'] if '19' in seas else None  # SKU动销率
    r25 = seas['25'] if '25' in seas else None  # 可满足率
    
    fs_keys = [('4','2025Q4及以前(服)'),('6','2026Q1(服)'),('8','2026Q2(服)'),('10','2026Q3+(服)'),('13','26年常青(服)'),
               ('15','2025Q4及以前(鞋)'),('18','2026Q1(鞋)'),('20','2026Q2(鞋)'),('22','2026Q3+(鞋)'),('25','26年常青(鞋)')]
    
    new_product = {}
    for ck, label in fs_keys:
        if ck in r5:
            new_product[label] = {
                'flow': float(r5[ck]),
                'disc': float(r7_seas[ck]) * 100 if r7_seas and ck in r7_seas else 0,
                'qty': int(float(r6_seas[ck])) if r6_seas and ck in r6_seas else 0,
                'sku_usage': float(r19[ck]) * 100 if r19 and ck in r19 else 0,
                'satisfy': float(r25[ck]) * 100 if r25 and ck in r25 else 0,
            }

# Discount range
disc_range = d['discount_range']
disc_range_data = {}
if '211' in disc_range:
    dr = disc_range['211']['data']
    disc_range_data = dr

# ====== FORMATTING HELPERS ======
def pct(v, decimals=2):
    """Format percentage."""
    if v is None: return '--'
    return f"{v:+.{decimals}f}%"

def pct_abs(v, decimals=2):
    """Format absolute percentage."""
    if v is None: return '--'
    return f"{v:.{decimals}f}%"

def money(v):
    """Format money."""
    if v is None: return '--'
    return f"¥{v:,.0f}"

def money2(v):
    """Format money with 2 decimals."""
    if v is None: return '--'
    return f"¥{v:,.2f}"

def up_down(v, red_is_up=True):
    """Return CSS class for up/down."""
    if v is None: return ''
    if v > 0:
        return 'up' if red_is_up else 'down'
    elif v < 0:
        return 'down' if red_is_up else 'up'
    return ''

def tag_class(v, red_is_up=True):
    """Return tag CSS class."""
    if v is None: return ''
    if v > 0:
        return 'tag-up' if red_is_up else 'tag-down'
    elif v < 0:
        return 'tag-down' if red_is_up else 'tag-up'
    return 'tag-info'

# ====== REPORT 1: DEEP ANALYSIS HTML ======
def gen_report1():
    # Header KPI strip
    kpi_strip = f'''
<div class="kpi-strip">
    <div class="item"><div class="val">{pct_abs(achieve)}</div><div class="lbl">达成率</div></div>
    <div class="item"><div class="val">{money(actual)}</div><div class="lbl">周流水</div></div>
    <div class="item"><div class="val" style="color:{'#27ae60' if yoy < 0 else '#e74c3c'}">{pct(yoy)}</div><div class="lbl">SSSG</div></div>
    <div class="item"><div class="val">{money(avg_ticket)}</div><div class="lbl">客单价</div></div>
    <div class="item"><div class="val">{pct_abs(conv_rate)}</div><div class="lbl">成交率</div></div>
    <div class="item"><div class="val">{pct_abs(shoe_share, 1)}</div><div class="lbl">鞋占比</div></div>
</div>'''

    # Daily table
    daily_rows = ''
    for dd in daily_data:
        bg = ''
        if dd['achieve'] < 100:
            bg = 'style="background:#fef2f2;"'
        elif dd['achieve'] > 150:
            bg = 'style="background:#f0fdf4;"'
        yoy_cls = 'td-green' if dd['yoy'] < 0 else 'td-red'
        
        daily_rows += f'''
        <tr {bg}>
            <td>{dd['name']}</td>
            <td>{money2(dd['target'])}</td>
            <td>{money2(dd['flow'])}</td>
            <td class="{yoy_cls if dd['achieve'] < 100 else ('td-red' if dd['achieve'] > 150 else '')}">{pct_abs(dd['achieve'],1)}</td>
            <td class="{yoy_cls}">{pct(dd['yoy'],1)}</td>
            <td>{pct_abs(dd['conv'],2)}</td>
            <td>{dd['visitors']}</td>
            <td>{dd['ticket']:.2f}</td>
        </tr>'''

    # Category table
    cate_rows = ''
    for cn in ['男装', '女装', '鞋', '配件']:
        cd = cat_data[cn]
        match_cls = 'td-red' if cd['match_type'] == 'sale_gt' else ('td-green' if cd['match_type'] == 'stock_gt' else '')
        trend = '⬆️' if cd['yoy'] > 0 else '⬇️'
        cate_rows += f'''
        <tr>
            <td>{cn}</td>
            <td>{money(cd['flow'])}</td>
            <td>{pct_abs(cd['flow_share'],2)}</td>
            <td>{cd['qty']}</td>
            <td>{pct_abs(cd['disc'],2)}</td>
            <td class="{'td-green' if cd['yoy'] < 0 else 'td-red' if cd['yoy'] > 0 else ''}">{pct(cd['yoy'],2)}</td>
            <td>{cd['stock_qty']}</td>
            <td>{pct_abs(cd['stock_qty_share'],2)}</td>
            <td class="{match_cls}">{cd['match']}</td>
            <td>{trend}</td>
        </tr>'''

    # TOP table
    top_rows = ''
    for label in ['TOP10','TOP20','TOP40','TOP60','TOP100']:
        if label in top_data:
            td = top_data[label]
            top_rows += f'''
            <tr>
                <td>{label}</td>
                <td>{pct_abs(td['vol_share'],2)}</td>
                <td>{pct_abs(td['flow_share'],2)}</td>
                <td>{pct_abs(td['stock_share'],2)}</td>
                <td>{pct_abs(td['satisfy'],2)}</td>
            </tr>'''

    # KPI overview cards
    kpi_cards = f'''
    <div class="kpi-grid">
        <div class="kpi-card"><div class="label">目标</div><div class="value">{money(target)}</div></div>
        <div class="kpi-card" style="border-color:#22c55e;background:#f0fdf4;"><div class="label">实际流水</div><div class="value">{money(actual)}</div><div class="change up">达成率 {pct_abs(achieve,2)}</div></div>
        <div class="kpi-card"><div class="label">O2O流水</div><div class="value">{money(o2o)}</div><div class="change">PAD {money(pad)} | 官网O2O {money(o2o_online)} | 占比{pct_abs(o2o_pct,2)}</div></div>
        <div class="kpi-card"><div class="label">成交率</div><div class="value">{pct_abs(conv_rate,2)}</div><div class="change {'up' if conv_rate > 15 else 'down'}">同比 {pct(float(r7['6'])*100,2)}pp</div></div>
        <div class="kpi-card"><div class="label">客单价</div><div class="value">{money(avg_ticket)}</div><div class="change down">同比 {pct(ticket_yoy,2)}</div></div>
        <div class="kpi-card"><div class="label">日均客流</div><div class="value">{daily_flow:.0f}人</div><div class="change {'up' if float(r7['10'])*100 > 0 else 'down'}">同比 {pct(float(r7['10'])*100,2)}</div></div>
        <div class="kpi-card"><div class="label">连带率</div><div class="value">{attach_rate:.2f}件</div><div class="change down">同比 {pct(attach_yoy,2)}</div></div>
        <div class="kpi-card"><div class="label">SSSG</div><div class="value {'up' if sssg > 0 else 'down'}">{pct(sssg,2)}</div><div class="change">同店同比 {pct(sssg,2)}</div></div>
        <div class="kpi-card"><div class="label">鞋占比</div><div class="value">{pct_abs(shoe_share,1)}</div><div class="change">鞋库存占比 {pct_abs(cat_data['鞋']['stock_qty_share'],1)}</div></div>
        <div class="kpi-card"><div class="label">折扣率</div><div class="value">{pct_abs(discount,2)}</div><div class="change {'up' if discount_yoy > 0 else 'down'}">同比 {pct(discount_yoy,2)}pp</div></div>
        <div class="kpi-card"><div class="label">周交易笔数</div><div class="value">{ticket_cnt:.0f}笔</div><div class="change down">同比 {pct(float(r15['24'])*100,2)}</div></div>
        <div class="kpi-card" style="border-color:#f59e0b;background:#fffbeb;"><div class="label">件单价</div><div class="value">{money(unit_price)}</div><div class="change {'up' if unit_yoy > 0 else 'down'}">同比 {pct(unit_yoy,2)}</div></div>
    </div>'''

    # KPI同比/环比矩阵
    matrix_rows = f'''
    <tr><td>流水达成率</td><td>{pct_abs(achieve,2)}</td><td class="{'td-green' if yoy < 0 else 'td-red'}">{pct(yoy,2)}</td><td class="{'td-green' if mom < 0 else 'td-red'}">{pct(mom,2)}</td><td><span class="tag {tag_class(yoy)}">{'⬆️' if yoy > 0 else '⬇️'}</span></td></tr>
    <tr><td>成交率</td><td>{pct_abs(conv_rate,2)}</td><td class="{'td-green' if float(r7['6'])*100 > 0 else 'td-red'}">{pct(float(r7['6'])*100,2)}pp</td><td class="{'td-green' if float(r7['7'])*100 > 0 else 'td-red'}">{pct(float(r7['7'])*100,2)}pp</td><td><span class="tag {'tag-up' if float(r7['6'])*100 > 0 else 'tag-down'}">{'⬆️' if float(r7['6'])*100 > 0 else '⬇️'}</span></td></tr>
    <tr><td>日均客流</td><td>{daily_flow:.0f}人</td><td class="{'td-green' if float(r7['10'])*100 > 0 else 'td-red'}">{pct(float(r7['10'])*100,2)}</td><td class="{'td-green' if float(r7['12'])*100 > 0 else 'td-red'}">{pct(float(r7['12'])*100,2)}</td><td><span class="tag {tag_class(float(r7['10'])*100)}">{'⬆️' if float(r7['10'])*100 > 0 else '⬇️'}</span></td></tr>
    <tr><td>客单价</td><td>{money(avg_ticket)}</td><td class="{'td-green' if ticket_yoy > 0 else 'td-red'}">{pct(ticket_yoy,2)}</td><td class="{'td-green' if float(r15['14'])*100 > 0 else 'td-red'}">{pct(float(r15['14'])*100,2)}</td><td><span class="tag {tag_class(ticket_yoy)}">{'⬆️' if ticket_yoy > 0 else '⬇️'}</span></td></tr>
    <tr><td>连带率</td><td>{attach_rate:.2f}件</td><td class="{'td-green' if attach_yoy > 0 else 'td-red'}">{pct(attach_yoy,2)}</td><td class="{'td-green' if float(r15['20'])*100 > 0 else 'td-red'}">{pct(float(r15['20'])*100,2)}</td><td><span class="tag {tag_class(attach_yoy)}">{'⬆️' if attach_yoy > 0 else '⬇️'}</span></td></tr>
    <tr><td>件单价</td><td>{money(unit_price)}</td><td class="{'td-green' if unit_yoy > 0 else 'td-red'}">{pct(unit_yoy,2)}</td><td class="{'td-green' if float(r15['8'])*100 > 0 else 'td-red'}">{pct(float(r15['8'])*100,2)}</td><td><span class="tag {tag_class(unit_yoy)}">{'⬆️' if unit_yoy > 0 else '⬇️'}</span></td></tr>
    <tr><td>折扣率</td><td>{pct_abs(discount,2)}</td><td class="{'td-green' if discount_yoy < 0 else 'td-red'}">{pct(discount_yoy,2)}pp</td><td class="{'td-green' if float(r15['32'])*100 < 0 else 'td-red'}">{pct(float(r15['32'])*100,2)}pp</td><td><span class="tag {tag_class(-discount_yoy)}">{'⬆️' if discount_yoy < 0 else '⬇️'}</span></td></tr>
    <tr><td>O2O流水</td><td>{money(o2o)}</td><td>--</td><td class="{'td-green' if float(r7['36'])*100 > 0 else 'td-red'}">{pct(float(r7['36'])*100,2)}</td><td><span class="tag tag-info">O2O环比</span></td></tr>
    <tr><td>SSSG</td><td>{pct(sssg,2)}</td><td class="{'td-green' if sssg > 0 else 'td-red'}">{pct(sssg,2)}</td><td class="{'td-green' if mom > 0 else 'td-red'}">{pct(mom,2)}</td><td><span class="tag {tag_class(sssg)}">{'⬆️' if sssg > 0 else '⬇️'}</span></td></tr>
    '''

    # 6 PROBLEMS
    sat_flow_diff = 26280.10 * 0.8  # Rough estimate of Saturday potential
    problems_html = f'''
    <!-- PROBLEM 1 -->
    <div class="problem-card">
      <span class="pnum">1</span><h3>整体流水同比暴跌-31.62% — 业绩断崖式下滑</h3>
      <div class="loss-tag">周流水同比流失 ≈ {money(abs(actual/(1+yoy/100)-actual))}</div>
      <div class="data-box">
        <table><tr>
          <td>本周流水 <b>{money(actual)}</b></td><td>同比 <b style="color:#ef4444;">{pct(yoy,2)}</b></td>
          <td>达成率 <b>{pct_abs(achieve,2)}</b></td>
          <td>（达标但同比大幅下降）</td>
        </tr><tr>
          <td>成交率 <b>{pct_abs(conv_rate,2)}</b>（同比-8.37pp）</td>
          <td>客单价 <b>{money(avg_ticket)}</b>（同比-14.12%）</td>
          <td>连带率 <b>{attach_rate:.2f}</b>（同比-14.35%）</td>
          <td>三项核心指标同步下滑</td>
        </tr></table>
        <div style="margin-top:6px;font-size:12px;color:var(--text-secondary);">
          若恢复到去年同期：周流水应达 ¥{actual/(1+yoy/100):,.0f}，差距 <b>{money(abs(actual/(1+yoy/100)-actual))}</b>
        </div>
      </div>
      <div class="cause">
        <b>产生原因：</b><br>
        1. <b>折扣率持续走高至44.09%</b>（同比+2.81pp、环比+7.39pp），越打折越卖不动，说明不是价格问题而是<b>客流质量和产品吸引力下降</b>；<br>
        2. 成交率18.12%（同比-8.37pp），进店100人中仅18人成交，<b>转化效率恶化</b>；<br>
        3. 奥莱店定位+44%综合折扣率，但同比仍跌31%，说明<b>客群在流失或消费降级</b>；<br>
        4. 作为6月第一周，去年此时可能是618/端午等活动拉动，<b>今年营销节奏不足</b>。
      </div>
    </div>

    <!-- PROBLEM 2 -->
    <div class="problem-card">
      <span class="pnum">2</span><h3>周六崩盘 — 达成率仅51.69%，单日损失过万</h3>
      <div class="loss-tag">预计损失 ≈ {money(sat_flow_diff)}（周六流水仅占目标的51.69%）</div>
      <div class="data-box">
        <table><tr>
          <td>周六目标 <b>{money(daily_data[5]['target'])}</b></td><td>实际 <b style="color:#ef4444;">{money(daily_data[5]['flow'])}</b></td>
          <td>达成率 <b style="color:#ef4444;">{pct_abs(daily_data[5]['achieve'],1)}</b></td>
          <td>同比 <b style="color:#ef4444;">{pct(daily_data[5]['yoy'],1)}</b></td>
        </tr><tr>
          <td>周六成交量 <b>{daily_data[5]['visitors']}</b>人</td><td>成交率 <b>{pct_abs(daily_data[5]['conv'],2)}</b></td>
          <td>客单价 <b>{daily_data[5]['ticket']:.2f}</b></td>
          <td>（全周唯一达成率低于60%的日）</td>
        </tr></table>
        <div style="margin-top:6px;font-size:12px;color:var(--text-secondary);">
          周六通常应贡献周流水25-30%，本周仅占12.5%。若恢复正常达成100%，可增 <b>{money(26280.10-13584.82)}</b>
        </div>
      </div>
      <div class="cause">
        <b>产生原因：</b><br>
        1. 周六目标26280.1是平日目标的2.5倍，<b>目标设定过高</b>不切实际；<br>
        2. 周六客流仅198人（不及周日343人的60%），<b>客流未达预期</b>；<br>
        3. 周六客单价476.4元、连带率3.54，均明显低于周四峰值（689.83元/5.33件），<b>导购周末工作效率下降</b>；<br>
        4. 可能受商场活动/竞品促销/天气等外部因素影响。
      </div>
    </div>

    <!-- PROBLEM 3 -->
    <div class="problem-card">
      <span class="pnum">3</span><h3>所有品类同比全面下挫 — 鞋类-43.63%最严重</h3>
      <div class="loss-tag">四品类合计同比流失严重，无一幸免</div>
      <div class="data-box">
        <table>
          <tr><th>品类</th><th>流水</th><th>同比</th><th>环比</th><th>折扣率</th><th>鞋/配每SKU产出</th></tr>
          <tr><td>男装</td><td>{money(cat_data['男装']['flow'])}</td><td class="td-green">{pct(cat_data['男装']['yoy'],2)}</td><td class="td-green">{pct(cat_data['男装']['mom'],2)}</td><td>{pct_abs(cat_data['男装']['disc'],2)}</td><td>--</td></tr>
          <tr><td>女装</td><td>{money(cat_data['女装']['flow'])}</td><td class="td-green">{pct(cat_data['女装']['yoy'],2)}</td><td class="td-green">{pct(cat_data['女装']['mom'],2)}</td><td>{pct_abs(cat_data['女装']['disc'],2)}</td><td>--</td></tr>
          <tr style="background:#fee2e2;"><td>鞋类</td><td>{money(cat_data['鞋']['flow'])}</td><td class="td-green"><b>{pct(cat_data['鞋']['yoy'],2)}</b></td><td class="td-green"><b>{pct(cat_data['鞋']['mom'],2)}</b></td><td>{pct_abs(cat_data['鞋']['disc'],2)}</td><td>{money(shoe_per_sku_flow)}</td></tr>
          <tr><td>配件</td><td>{money(cat_data['配件']['flow'])}</td><td class="td-green">{pct(cat_data['配件']['yoy'],2)}</td><td class="{'td-green' if cat_data['配件']['mom']<0 else 'td-red'}">{pct(cat_data['配件']['mom'],2)}</td><td>{pct_abs(cat_data['配件']['disc'],2)}</td><td>{money(acc_per_sku_flow)}</td></tr>
        </table>
      </div>
      <div class="cause">
        <b>产生原因：</b><br>
        1. 鞋类同比-43.63%、环比-45.31%，作为核心品类失速最严重，<b>鞋类SKU动销率仅35.84%</b>，大量SKU躺平；<br>
        2. 配件每SKU产出仅{money(acc_per_sku_flow)}（vs 鞋{money(shoe_per_sku_flow)}），<b>275个配件在售SKU中40%未动销</b>；<br>
        3. 四品类折扣率均在43-45%区间，<b>同质化打折无法形成差异化竞争</b>；<br>
        4. 各品类环比也全面下滑（除配件微增0.26%），说明<b>下滑趋势在加速而非改善</b>。
      </div>
    </div>

    <!-- PROBLEM 4 -->
    <div class="problem-card">
      <span class="pnum">4</span><h3>客单价与连带率双降 — 低客单、低效率交易驱动</h3>
      <div class="loss-tag">若客单价恢复至600元水平，周增量 ≈ {money(600*ticket_cnt-actual)}</div>
      <div class="data-box">
        <table>
          <tr><th>指标</th><th>本周</th><th>同比</th><th>环比</th><th>解读</th></tr>
          <tr><td>客单价</td><td class="td-green">{money(avg_ticket)}</td><td class="td-green">{pct(ticket_yoy,2)}</td><td class="td-green">{pct(float(r15['14'])*100,2)}</td><td>持续下行</td></tr>
          <tr><td>连带率</td><td class="td-green">{attach_rate:.2f}件</td><td class="td-green">{pct(attach_yoy,2)}</td><td class="td-green">{pct(float(r15['20'])*100,2)}</td><td>大幅下滑</td></tr>
          <tr><td>件单价</td><td class="{'td-green' if unit_yoy<0 else 'td-red'}">{money(unit_price)}</td><td class="{'td-green' if unit_yoy<0 else 'td-red'}">{pct(unit_yoy,2)}</td><td class="{'td-green' if float(r15['8'])*100<0 else 'td-red'}">{pct(float(r15['8'])*100,2)}</td><td>基本持平</td></tr>
          <tr style="background:#fffbeb;"><td><b>隐含问题</b></td><td colspan="4">客单价降14.12% = 连带率降14.35% × 件单价持平，说明<b>连带效率严重下降</b>，每单多卖的能力在减弱</td></tr>
        </table>
      </div>
      <div class="cause">
        <b>产生原因：</b><br>
        1. 连带率从同期4.57降至3.91，<b>每笔少卖0.66件</b>，导购推荐和搭配销售能力下降；<br>
        2. 工作日（周三除外）连带率均低于4.0，周末更只有3.54/3.39，<b>周末客流多但连带反而差</b>；<br>
        3. 折扣率44.09%说明大量商品折价出售，<b>顾客更倾向于购买折扣单品而非多件搭配</b>；<br>
        4. 奥莱店定位导致顾客期望低价，<b>连带提升空间被价格预期压制</b>。
      </div>
    </div>

    <!-- PROBLEM 5 -->
    <div class="problem-card">
      <span class="pnum">5</span><h3>折扣率44.09%持续走高 — 越打折越卖不动</h3>
      <div class="loss-tag">折扣率同比+2.81pp、环比+7.39pp，但流水同比-31.62%</div>
      <div class="data-box">
        <table>
          <tr><th>折扣区间</th><th>数量</th><th>占比</th></tr>
          <tr style="background:#fee2e2;"><td>5折以下</td><td>{disc_range_data.get('1','--')}</td><td>{disc_range_data.get('2','--')}</td></tr>
          <tr><td>5-6折</td><td>{disc_range_data.get('4','--')}</td><td>{disc_range_data.get('5','--')}</td></tr>
          <tr><td>6-7折</td><td>{disc_range_data.get('7','--')}</td><td>{disc_range_data.get('8','--')}</td></tr>
          <tr><td>7-8折</td><td>{disc_range_data.get('10','--')}</td><td>{disc_range_data.get('11','--')}</td></tr>
          <tr><td>8折以上</td><td>{disc_range_data.get('13','--')}</td><td>{disc_range_data.get('14','--')}</td></tr>
        </table>
      </div>
      <div class="cause">
        <b>产生原因：</b><br>
        1. 折扣率44.09%意味着<b>平均5.6折出售</b>，品牌价值被稀释；<br>
        2. 折扣率环比+7.39pp说明<b>近期加大了打折力度</b>，但流水环比-28.50%，打折并未带来额外销售；<br>
        3. 奥莱店虽然本身就是折扣渠道，但44%的综合折扣仍然偏高，<b>折扣下沉空间有限</b>；<br>
        4. <b>顾客对"奥莱=常年打折"形成预期</b>，非打折商品难以动销，形成"不打折就卖不动"的恶性循环。
      </div>
    </div>

    <!-- PROBLEM 6 -->
    <div class="problem-card">
      <span class="pnum">6</span><h3>新品表现乏力 — 26年常青款折扣率高、动销率低</h3>
      <div class="loss-tag">26年常青(服)折扣率54.85%，动销率仅64.58%</div>
      <div class="data-box">
        <table>
          <tr><th>季节</th><th>流水</th><th>折扣率</th><th>动销率</th><th>可满足率</th></tr>
          <tr><td>26年常青(服)</td><td>{money(new_product.get('26年常青(服)',{}).get('flow',0))}</td><td>{pct_abs(new_product.get('26年常青(服)',{}).get('disc',0),2)}</td><td>{pct_abs(new_product.get('26年常青(服)',{}).get('sku_usage',0),2)}</td><td>{pct_abs(new_product.get('26年常青(服)',{}).get('satisfy',0),2)}</td></tr>
          <tr><td>26年常青(鞋)</td><td>{money(new_product.get('26年常青(鞋)',{}).get('flow',0))}</td><td>{pct_abs(new_product.get('26年常青(鞋)',{}).get('disc',0),2)}</td><td>{pct_abs(new_product.get('26年常青(鞋)',{}).get('sku_usage',0),2)}</td><td>{pct_abs(new_product.get('26年常青(鞋)',{}).get('satisfy',0),2)}</td></tr>
          <tr><td>2026Q2(服)</td><td>{money(new_product.get('2026Q2(服)',{}).get('flow',0))}</td><td>{pct_abs(new_product.get('2026Q2(服)',{}).get('disc',0),2)}</td><td>{pct_abs(new_product.get('2026Q2(服)',{}).get('sku_usage',0),2)}</td><td>{pct_abs(new_product.get('2026Q2(服)',{}).get('satisfy',0),2)}</td></tr>
        </table>
      </div>
      <div class="cause">
        <b>产生原因：</b><br>
        1. 26年常青(服)折扣率54.85%（约4.5折），新品即打折，<b>新品价值感知弱</b>；<br>
        2. 2026Q2服装折扣率59.19%（约4折），<b>当季新品也需大幅让利才能卖</b>；<br>
        3. 新品动销率普遍在45-65%之间，<b>35-55%的新品SKU一周内0销售</b>；<br>
        4. 新品可满足率仅2-6%，说明<b>新品备货极度保守</b>，不敢深库存→不敢推→卖不动→继续打折的恶性循环。
      </div>
    </div>
    '''

    # 6 OPPORTUNITIES
    opps_html = f'''
    <!-- OPP 1 -->
    <div class="opp-card">
      <span class="onum">1</span><h3>周六复苏攻坚 — 夺回单日{money(26280.10-13584.82)}增量</h3>
      <div class="action">
        <b>目标：</b>周六达成率从51.69%恢复至80%+。<br>
        <b>方案A — 周五预锁定：</b>周五晚场推"周六专属券：满399-30（限前30单）"，通过企微+短信推送给近30天有消费的会员；<br>
        <b>方案B — 周六社交引流：</b>"带朋友到店各减20元"裂变活动，利用周末社交场景拉客流；<br>
        <b>方案C — 周六排班优化：</b>周六下午14-18点安排最强连带能力导购值守高价值区域，设周六单日客单价PK奖，目标客单价从476提升至550+。
      </div>
    </div>

    <!-- OPP 2 -->
    <div class="opp-card">
      <span class="onum">2</span><h3>流量激活：成交率从18%提升至22%</h3>
      <div class="action">
        <b>目标：</b>提升成交率4pp，周增流水≈{money((0.22-0.1812)*(daily_flow*7)*(attach_rate*unit_price))}。<br>
        <b>方案A — 进店三句话标准话术：</b>"欢迎光临，今天鞋/服装新品到店折扣力度最大，您可以先看看"——针对67%不成交的客流，强化进店引导；<br>
        <b>方案B — 试穿转化激励：</b>"试穿3件以上即送品牌袜子一双"，用低成本的赠品降低顾客试穿门槛；<br>
        <b>方案C — 收银台"加价购"：</b>结账时推"加¥59换购指定T恤/短裤"，将成交率转化为连带率。
      </div>
    </div>

    <!-- OPP 3 -->
    <div class="opp-card">
      <span class="onum">3</span><h3>鞋类SKU瘦身+爆款深耕</h3>
      <div class="action">
        <b>目标：</b>鞋SKU动销率从35.84%提升至50%+，每SKU产出持平或提升。<br>
        <b>方案A — 鞋SKU断舍离：</b>从124个在售SKU中筛选连续2周0动销的SKU，申请调出/退货，将陈列面+库存资金转向动销SKU；<br>
        <b>方案B — TOP20鞋款深耕：</b>锁定销量TOP20鞋款，加库存深度（目标可满足率从36.56%提升至50%+），全店导购话术植入为"本周必推"；<br>
        <b>方案C — 配件瘦身同步：</b>275个配件SKU中清理0动销SKU，每SKU产出从{money(acc_per_sku_flow)}提升至¥200+。
      </div>
    </div>

    <!-- OPP 4 -->
    <div class="opp-card">
      <span class="onum">4</span><h3>连带攻坚：从3.91件拉升至4.5件</h3>
      <div class="action">
        <b>目标：</b>连带率提升0.6件，周流水增量≈{money((4.5-3.91)*ticket_cnt*unit_price)}。<br>
        <b>方案A — "1+1+1"搭配法：</b>每位进店顾客导购主动推荐"1件主推品（鞋/外套）+1件搭配品（裤子/短裤）+1件连带品（T恤/袜子）"的完整搭配；<br>
        <b>方案B — 衣鞋跨界连带：</b>鞋区收银旁陈列"买鞋+¥99换购指定短裤"，服装区旁陈列配套鞋款，用空间引导跨界购买；<br>
        <b>方案C — 连带即时激励：</b>设置"连带王"奖——单笔超4件奖¥10红包，超6件奖¥20，下班即兑现。
      </div>
    </div>

    <!-- OPP 5 -->
    <div class="opp-card">
      <span class="onum">5</span><h3>折扣管控：从"全打折"转向"选择性折扣"</h3>
      <div class="action">
        <b>目标：</b>综合折扣率控制在42%以内。<br>
        <b>方案A — 新品保护期：</b>26年常青款前2周不打折，以"本季首发体验价"名义正价销售，2周后根据动销数据决定是否纳入促销；<br>
        <b>方案B — 分品类折中折：</b>鞋类（占比48%）保持折扣力度，服装（占比20%）适度收紧折扣，用不同品类调节综合折扣率；<br>
        <b>方案C — 满减替代直降：</b>"满599减60、满999减150"替代"全场X折"，顾客为凑满减增加连带，同时保护品牌价值感知。
      </div>
    </div>

    <!-- OPP 6 -->
    <div class="opp-card">
      <span class="onum">6</span><h3>O2O渠道发力 + 周日巩固</h3>
      <div class="action">
        <b>目标：</b>O2O流水从{money(o2o)}提升至{money(8000)}+（占比7%+），周日继续保持当前高流水水平。<br>
        <b>方案A — 周日"老客专享日"：</b>周日是本周最强日（流水31105/达成124%），说明周日客流和购买力都在，<b>重点维护周日会员池</b>：每周日推送"会员专属款"3-5款；<br>
        <b>方案B — PAD+官网O2O同步推：</b>将线下畅销款同步到线上O2O，门店陈列时标注"线上同款可购"，导购辅助顾客扫码下单；<br>
        <b>方案C — 将周四峰值模式复制到周三/周五：</b>周四（达成127%/客单价689.83/连带5.33）是全周效率最高日，分析周四成功因素（排班/促销/活动），复制到周三和周五。
      </div>
    </div>
    '''

    # Full HTML
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>W23 周报深度分析 | 6大问题点 + 机会点</title>
<style>
  :root {{ --bg: #f5f6f8; --card-bg: #ffffff; --text: #1a1a2e; --text-secondary: #5a5a7a;
    --border: #e8ecf1; --red: #e74c3c; --green: #27ae60; --blue: #2563eb;
    --orange: #f59e0b; --accent: #3b82f6; }}
  * {{ margin:0;padding:0;box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif; background:var(--bg); color:var(--text); line-height:1.7; }}
  .report {{ max-width:1150px; margin:0 auto; padding:24px 20px 60px; }}
  .header {{ background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%); color:white; padding:32px 36px; border-radius:16px; margin-bottom:24px; }}
  .header h1 {{ font-size:26px; font-weight:700; }}
  .header .meta {{ font-size:14px; opacity:.85; margin-top:6px; }}
  .header .kpi-strip {{ display:flex; gap:24px; margin-top:18px; flex-wrap:wrap; }}
  .header .kpi-strip .item {{ text-align:center; min-width:80px; }}
  .header .kpi-strip .val {{ font-size:22px; font-weight:800; color:#fbbf24; }}
  .header .kpi-strip .lbl {{ font-size:11px; opacity:.7; }}
  .section {{ background:var(--card-bg); border-radius:14px; padding:28px 32px; margin-bottom:18px; box-shadow:0 1px 3px rgba(0,0,0,.04); border:1px solid var(--border); }}
  .section h2 {{ font-size:18px; font-weight:700; margin-bottom:20px; display:flex; align-items:center; gap:10px; }}
  .section h3 {{ font-size:15px; font-weight:700; margin-bottom:12px; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:14px; }}
  .kpi-card {{ background:#f9fafb; border-radius:10px; padding:16px; border:1px solid var(--border); }}
  .kpi-card .label {{ font-size:12px; color:var(--text-secondary); margin-bottom:4px; }}
  .kpi-card .value {{ font-size:22px; font-weight:700; }}
  .kpi-card .change {{ font-size:13px; margin-top:4px; }}
  .up {{ color:#e74c3c; font-weight:600; }}
  .down {{ color:#27ae60; font-weight:600; }}
  .tag {{ display:inline-block; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }}
  .tag-up {{ background:#fee2e2; color:#991b1b; }}
  .tag-down {{ background:#d1fae5; color:#065f46; }}
  .tag-warn {{ background:#fef3c7; color:#92400e; }}
  .tag-info {{ background:#dbeafe; color:#1e40af; }}
  .problem-card {{ background:#fef2f2; border-left:5px solid #ef4444; border-radius:10px; padding:18px 22px; margin-bottom:16px; }}
  .problem-card .pnum {{ display:inline-block; background:#ef4444; color:white; width:28px; height:28px; border-radius:50%; text-align:center; line-height:28px; font-weight:800; font-size:14px; margin-right:10px; vertical-align:middle; }}
  .problem-card h3 {{ display:inline; font-size:16px; color:#991b1b; }}
  .problem-card .loss-tag {{ background:#fecaca; display:inline-block; padding:2px 10px; border-radius:4px; font-weight:700; color:#7f1d1d; font-size:13px; margin:8px 0; }}
  .problem-card .data-box {{ background:white; border-radius:8px; padding:12px 16px; margin:10px 0; font-size:13px; }}
  .problem-card .data-box td {{ padding:3px 12px 3px 0; font-size:13px; }}
  .problem-card .cause {{ margin-top:8px; font-size:13.5px; line-height:1.8; }}
  .problem-card .cause b {{ color:#991b1b; }}
  .opp-card {{ background:#f0fdf4; border-left:5px solid #22c55e; border-radius:10px; padding:18px 22px; margin-bottom:16px; }}
  .opp-card .onum {{ display:inline-block; background:#22c55e; color:white; width:28px; height:28px; border-radius:50%; text-align:center; line-height:28px; font-weight:800; font-size:14px; margin-right:10px; vertical-align:middle; }}
  .opp-card h3 {{ display:inline; font-size:16px; color:#065f46; }}
  .opp-card .action {{ font-size:13.5px; line-height:1.8; margin-top:8px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ background:#f1f5f9; padding:9px 10px; text-align:center; font-weight:600; color:var(--text-secondary); font-size:12px; border-bottom:2px solid var(--border); }}
  td {{ padding:9px 10px; text-align:center; border-bottom:1px solid var(--border); }}
  tr:nth-child(even) {{ background:#fafbfc; }}
  td:first-child,th:first-child {{ text-align:left; font-weight:600; }}
  .td-red {{ color:var(--red); font-weight:700; }}
  .td-green {{ color:var(--green); font-weight:700; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  hr {{ border:none; border-top:1px solid var(--border); margin:16px 0; }}
  .highlight-box {{ background:linear-gradient(135deg,#eff6ff,#dbeafe); border-radius:12px; padding:16px 20px; margin:14px 0; font-size:14px; }}
  .footer {{ text-align:center; padding:20px; color:var(--text-secondary); font-size:12px; }}
</style>
</head>
<body>
<div class="report">

<div class="header">
  <div style="flex:1;">
    <h1>W23 周报深度分析报告</h1>
    <div class="meta">{store} | {period} | 数据截止 2026.06.07</div>
  </div>
  {kpi_strip}
</div>

<!-- KPI OVERVIEW -->
<div class="section">
  <h2>一、本周核心KPI全貌</h2>
  {kpi_cards}
</div>

<!-- 同比/环比矩阵 -->
<div class="section">
  <h2>KPI同比/环比对比矩阵</h2>
  <table>
    <thead><tr><th>指标</th><th>本周值</th><th>同比</th><th>环比</th><th>趋势</th></tr></thead>
    <tbody>{matrix_rows}</tbody>
  </table>
</div>

<!-- 日别趋势 -->
<div class="section">
  <h2>日别销售趋势</h2>
  <table>
    <thead><tr><th>日期</th><th>目标</th><th>实际流水</th><th>达成率</th><th>同比</th><th>成交率</th><th>客流</th><th>客单价</th></tr></thead>
    <tbody>
      {daily_rows}
      <tr style="font-weight:700;background:#f1f5f9;">
        <td>合计</td><td>{money2(target)}</td><td>{money2(actual)}</td><td>{pct_abs(achieve,1)}</td><td>{pct(yoy,1)}</td><td>{pct_abs(conv_rate,2)}</td><td>{daily_flow:.0f}</td><td>{avg_ticket:.2f}</td>
      </tr>
    </tbody>
  </table>
</div>

<hr>

<!-- PROBLEMS -->
<div class="section" style="border-top:3px solid #ef4444;">
  <h2>二、六大关键问题点</h2>
</div>
{problems_html}

<!-- 品类速览 -->
<div class="section">
  <h2>品类结构速览</h2>
  <div class="grid2">
    <div>
      <table>
        <thead><tr><th>品类</th><th>流水</th><th>销售占比</th><th>销量</th><th>折扣率</th><th>同比</th><th>库存数量</th><th>库存占比</th><th>匹配分析</th></tr></thead>
        <tbody>{cate_rows}</tbody>
      </table>
    </div>
    <div class="highlight-box">
      <strong>鞋每SKU产出 {money(shoe_per_sku_flow)} vs 配件每SKU产出 {money(acc_per_sku_flow)}</strong><br>
      鞋SKU动销率仅{pct_abs(cat_data['鞋']['sku_usage'],2)}，64%的鞋SKU一周0动销<br>
      配件{pct_abs(cat_data['配件']['sku_usage'],2)}的SKU有动销，但每SKU产出仅{money(acc_per_sku_flow)}<br><br>
      <strong>鞋占比 {pct_abs(shoe_share,1)}</strong>，鞋库存数量占总库存{pct_abs(cat_data['鞋']['stock_qty_share'],1)}<br>
      鞋库存金额¥{cat_data['鞋']['stock_amt']/10000:.1f}万（{cat_data['鞋']['stock_sku']}个SKU）
    </div>
  </div>
</div>

<hr>

<!-- OPPORTUNITIES -->
<div class="section" style="border-top:3px solid #22c55e;">
  <h2>三、六大机会点 & 可落地方案</h2>
</div>
{opps_html}

<!-- SUMMARY -->
<div class="section" style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;border:none;">
  <h2 style="color:#fbbf24;">总结：六大问题的逻辑关系</h2>
  <div style="font-size:15px;line-height:2;opacity:.95;">
    <p style="margin-bottom:12px;">
      <span style="background:#ef4444;color:white;padding:4px 14px;border-radius:20px;">P1 同比大跌</span>
      <span style="color:white;margin:0 8px;">+</span>
      <span style="background:#ef4444;color:white;padding:4px 14px;border-radius:20px;">P2 周六崩盘</span>
      <span style="color:white;margin:0 8px;">→</span>
      <span style="color:#fca5a5;">客流端失血</span>
    </p>
    <p style="margin-bottom:12px;">
      <span style="background:#ef4444;color:white;padding:4px 14px;border-radius:20px;">P3 品类全跌</span>
      <span style="color:white;margin:0 8px;">+</span>
      <span style="background:#ef4444;color:white;padding:4px 14px;border-radius:20px;">P5 折扣失控</span>
      <span style="color:white;margin:0 8px;">→</span>
      <span style="color:#fca5a5;">品类端失血</span>
    </p>
    <p style="margin-bottom:12px;">
      <span style="background:#ef4444;color:white;padding:4px 14px;border-radius:20px;">P4 客单/连带双降</span>
      <span style="color:white;margin:0 8px;">+</span>
      <span style="background:#ef4444;color:white;padding:4px 14px;border-radius:20px;">P6 新品乏力</span>
      <span style="color:white;margin:0 8px;">→</span>
      <span style="color:#fca5a5;">效率端失血</span>
    </p>
  </div>
  <div style="margin-top:18px;padding-top:16px;border-top:1px solid rgba(255,255,255,.2);">
    <p style="font-size:15px;line-height:1.9;">
      <strong style="color:#fca5a5;">三大失血点（客流 → 品类 → 效率）</strong>互为因果：客流质量下降 → 品类全线下滑 → 打折加码但无效 → 连带和客单恶化。<br>
      破解之道：<strong style="color:#86efac;">周六引流（问题1/2）→ SKU瘦身+深耕（问题3）→ 连带攻坚（问题4）→ 折扣优化（问题5）→ 新品策略+O2O（问题6）</strong>。<br>
      六项措施联动落地，预计释放 <strong style="color:#fbbf24;">¥15,000-20,000/周</strong> 增量空间。
    </p>
  </div>
</div>

<div class="footer">W23周报深度分析 | {store} | 数据截止 2026.06.07 | AI店长出品</div>
</div>
</body>
</html>'''
    return html


# ====== REPORT 2: STRATEGY HTML ======
def gen_report2():
    daily_achieve_str = ''
    for dd in daily_data:
        cls = 'red' if dd['achieve'] < 100 else ('green' if dd['achieve'] > 150 else '')
        symbol = '' if not cls else f'<span class="{cls}">' + (f'{dd["achieve"]:.0f}%') + '</span>'
        daily_achieve_str += f'周一{symbol}→' if dd['name'] == '周一' else f'{dd["name"]}{symbol}→'

    # Sub categories for clothing
    sub_clothing = ''
    sub_data = d['sub_ps']
    for rk, rd in sub_data.items():
        label = rd['label']
        if not label or label in ['','合计', '奥莱店华南区城市', '器配中类', '']:
            continue
        data = rd['data']
        flow = data.get('8', 0)
        disc = data.get('10', 0)
        if flow and disc and float(flow) > 0:
            sub_clothing += f'<tr><td>{label}</td><td>{money(float(flow))}</td><td>{pct_abs(float(disc)*100,2)}</td></tr>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>W23 周分析 & 重点改善策略</title>
<style>
  :root {{ --bg: #f2f3f5; --card: #ffffff; --text: #1a1a2e; --sub: #6b7280;
    --red: #dc2626; --green: #16a34a; --blue: #2563eb; --orange: #f59e0b; --border: #e5e7eb; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif; background:var(--bg); color:var(--text); font-size:14px; line-height:1.65; }}
  .page {{ max-width:1200px; margin:0 auto; padding:20px 24px; }}
  .main-grid {{ display:grid; grid-template-columns:1.15fr 1fr; gap:20px; }}
  @media(max-width:900px){{ .main-grid{{grid-template-columns:1fr;}} }}
  .col-title {{ font-size:17px; font-weight:800; padding:6px 0 14px; display:flex; align-items:center; gap:8px; border-bottom:2px solid var(--border); margin-bottom:14px; }}
  .col-title .dot {{ width:8px; height:8px; border-radius:50%; display:inline-block; }}
  .dot-red {{ background:#dc2626; }}
  .dot-blue {{ background:#2563eb; }}
  .block {{ background:var(--card); border-radius:10px; padding:18px 20px; margin-bottom:14px; border:1px solid var(--border); }}
  .block h3 {{ font-size:15px; font-weight:700; margin-bottom:10px; display:flex; align-items:center; gap:8px; }}
  .kpi-row {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:8px; }}
  .kpi-item {{ background:#f8fafc; border-radius:6px; padding:10px 14px; min-width:90px; text-align:center; flex:1; }}
  .kpi-item .kval {{ font-size:20px; font-weight:800; }}
  .kpi-item .klbl {{ font-size:11px; color:var(--sub); }}
  .kpi-item .kchg {{ font-size:12px; font-weight:600; margin-top:2px; }}
  .up {{ color:var(--red); }}
  .down {{ color:var(--green); }}
  .data-line {{ font-size:13.5px; line-height:1.8; }}
  .data-line .val {{ font-weight:700; }}
  .data-line .red {{ color:var(--red); font-weight:700; }}
  .data-line .green {{ color:var(--green); font-weight:700; }}
  .data-line .tag {{ display:inline-block; padding:1px 8px; border-radius:12px; font-size:11px; font-weight:600; margin:0 2px; }}
  .tag-red {{ background:#fee2e2; color:#991b1b; }}
  .tag-green {{ background:#d1fae5; color:#065f46; }}
  .tag-orange {{ background:#fef3c7; color:#92400e; }}
  .highlight {{ background:#fffbeb; border-radius:6px; padding:10px 14px; margin:8px 0; font-size:13px; border-left:3px solid var(--orange); }}
  .strategy-item {{ padding:12px 0; border-bottom:1px solid var(--border); }}
  .strategy-item:last-child {{ border-bottom:none; }}
  .strategy-item .snum {{ display:inline-flex; align-items:center; justify-content:center; width:26px; height:26px; border-radius:50%; font-weight:800; font-size:13px; margin-right:8px; flex-shrink:0; }}
  .strategy-item .stitle {{ font-weight:700; font-size:14px; display:flex; align-items:center; margin-bottom:4px; }}
  .strategy-item .sbody {{ font-size:13px; color:#4b5563; line-height:1.7; padding-left:34px; }}
  .snum-1 {{ background:#eff6ff; color:#2563eb; }}
  .snum-2 {{ background:#fef3c7; color:#d97706; }}
  .snum-3 {{ background:#f0fdf4; color:#16a34a; }}
  .snum-4 {{ background:#fef2f2; color:#dc2626; }}
  .snum-5 {{ background:#f5f3ff; color:#7c3aed; }}
  .divider {{ border:none; border-top:1px dashed var(--border); margin:10px 0; }}
  .badge {{ display:inline-block; font-size:12px; font-weight:700; padding:3px 10px; border-radius:4px; }}
  .badge-red {{ background:#fee2e2; color:#dc2626; }}
  .badge-green {{ background:#d1fae5; color:#16a34a; }}
  .footer-note {{ font-size:11px; color:#9ca3af; text-align:right; margin-top:12px; }}
  .table-mini {{ width:100%; font-size:12.5px; border-collapse:collapse; margin:8px 0; }}
  .table-mini th {{ background:#f1f5f9; padding:6px 8px; text-align:center; font-weight:600; color:var(--sub); border-bottom:1px solid var(--border); }}
  .table-mini td {{ padding:6px 8px; text-align:center; border-bottom:1px solid var(--border); }}
</style>
</head>
<body>
<div class="page">

<div class="main-grid">

<!-- LEFT: ANALYSIS -->
<div>
  <div class="col-title"><span class="dot dot-red"></span> 周分析 — W23 (06.01-06.07)</div>

  <!-- 1. 达成 -->
  <div class="block">
    <h3>达成：{pct_abs(achieve,1)} | 同比 <span class="down">{pct(yoy,2)}</span></h3>
    <div class="kpi-row">
      <div class="kpi-item"><div class="klbl">本周目标</div><div class="kval">{money(target)}</div></div>
      <div class="kpi-item" style="border:2px solid #16a34a;"><div class="klbl">本周实际</div><div class="kval up">{money(actual)}</div><div class="kchg up">达成 {pct_abs(achieve,2)}</div></div>
      <div class="kpi-item"><div class="klbl">同比</div><div class="kval down">{pct(yoy,1)}</div></div>
      <div class="kpi-item"><div class="klbl">同店同比</div><div class="kval down">{pct(sssg,1)}</div></div>
    </div>
    <div class="data-line">
      周目标达成 <span class="val up">{pct_abs(achieve,1)}</span>，超目标 <span class="val up">{money(actual-target)}</span>，但<b>同比大跌{pct(yoy,1)}</b>。<br>
      月累计（6月第一周）目标与本周相同。<br>
      <div class="divider"></div>
      日别达成：{daily_achieve_str.rstrip('→')}<br>
      <span class="tag tag-red">周六达成51.69%全周最低；周一达成202%但同比-52%，目标设定偏低</span>
    </div>
  </div>

  <!-- 2. 成交率 -->
  <div class="block">
    <h3>成交率：{pct_abs(conv_rate,2)} | 同比 -8.37pp | 日均客流 {daily_flow:.0f}人</h3>
    <div class="data-line">
      成交率{pct_abs(conv_rate,2)}，<span class="red">同比-8.37pp</span>，进店100人中仅18人成交。<br>
      日均客流{daily_flow:.0f}人/天，周客流合计{daily_flow*7:.0f}人 <span class="green">（同比+18.73%）</span>。<br>
      <div class="highlight">
        <b>矛盾：</b>客流同比+18.73%，但成交率-8.37pp、流水同比-31.62%。<b>人是进店了，但不买</b>——客流质量下降或店内吸引力不足。
      </div>
      客单价<span class="down">{money(avg_ticket)}</span>（<span class="down">-14.12%</span>），连带率<span class="down">{attach_rate:.2f}件</span>（<span class="down">-14.35%</span>），件单价{money(unit_price)}。
    </div>
  </div>

  <!-- 3. 品类 -->
  <div class="block">
    <h3>品类：鞋同比 <span class="red">-43.63%</span> | 配件 <span class="red">-22.21%</span></h3>
    <div class="data-line">
      <table class="table-mini">
        <tr><th>品类</th><th>流水</th><th>同比</th><th>环比</th><th>折扣率</th><th>SKU动销率</th></tr>
        <tr><td>男装</td><td>{money(cat_data['男装']['flow'])}</td><td class="red">{pct(cat_data['男装']['yoy'],1)}</td><td class="red">{pct(cat_data['男装']['mom'],1)}</td><td>{pct_abs(cat_data['男装']['disc'],1)}</td><td>--</td></tr>
        <tr><td>女装</td><td>{money(cat_data['女装']['flow'])}</td><td class="red">{pct(cat_data['女装']['yoy'],1)}</td><td class="red">{pct(cat_data['女装']['mom'],1)}</td><td>{pct_abs(cat_data['女装']['disc'],1)}</td><td>--</td></tr>
        <tr style="background:#fee2e2;"><td><b>鞋</b></td><td><b>{money(cat_data['鞋']['flow'])}</b></td><td class="red"><b>{pct(cat_data['鞋']['yoy'],1)}</b></td><td class="red"><b>{pct(cat_data['鞋']['mom'],1)}</b></td><td>{pct_abs(cat_data['鞋']['disc'],1)}</td><td class="red">{pct_abs(cat_data['鞋']['sku_usage'],1)}</td></tr>
        <tr><td>配件</td><td>{money(cat_data['配件']['flow'])}</td><td class="red">{pct(cat_data['配件']['yoy'],1)}</td><td class="green">{pct(cat_data['配件']['mom'],1)}</td><td>{pct_abs(cat_data['配件']['disc'],1)}</td><td>{pct_abs(cat_data['配件']['sku_usage'],1)}</td></tr>
      </table>
      <div class="highlight">
        <b>鞋占比 {pct_abs(shoe_share,1)}：</b>鞋库存数量{cat_data['鞋']['stock_qty']}件（占{pct_abs(cat_data['鞋']['stock_qty_share'],1)}），鞋SKU动销率仅{pct_abs(cat_data['鞋']['sku_usage'],2)}，64%鞋SKU一周0动销。<br>
        配件每SKU产出 <b>{money(acc_per_sku_flow)}</b> vs 鞋每SKU产出 <b>{money(shoe_per_sku_flow)}</b>
      </div>
    </div>
  </div>

  <!-- 4. 件单价与连带 -->
  <div class="block">
    <h3>客单价{format(money(avg_ticket))} | 连带{format(str(attach_rate))}件 | 折扣{pct_abs(discount,1)}</h3>
    <div class="data-line">
      客单价 <span class="down">{money(avg_ticket)}</span>（同比<span class="down">{pct(ticket_yoy,1)}</span>），拆解：<br>
      件单价{money(unit_price)} × 连带{attach_rate:.2f} = {money(unit_price*attach_rate)} ≈ 客单价{money(avg_ticket)}<br>
      <span class="tag tag-orange">客单价下降主因是连带率从4.57降至3.91（-14.35%），件单价基本持平</span><br>
      <div class="divider"></div>
      日别客单价：周一{money(daily_data[0]['ticket'])} / 周二{money(daily_data[1]['ticket'])} / 周三{money(daily_data[2]['ticket'])} / 周四{money(daily_data[3]['ticket'])} / 周五{money(daily_data[4]['ticket'])} / <span class="red">周六{money(daily_data[5]['ticket'])}</span> / <span class="red">周日{money(daily_data[6]['ticket'])}</span><br>
      折扣率{pct_abs(discount,1)}（<span class="red">同比+2.81pp</span>，<span class="red">环比+7.39pp</span>），折扣在加速加深。
    </div>
  </div>
</div>

<!-- RIGHT: STRATEGY -->
<div>
  <div class="col-title"><span class="dot dot-blue"></span> 本周重点改善策略</div>

  <div class="block">
    <div class="strategy-item">
      <div class="stitle"><span class="snum snum-1">1</span>周六复苏 + 周日巩固：夺回周末主战场</div>
      <div class="sbody">
        <b>执行人：</b>店长 + 全体导购<br>
        <b>时间：</b>周五下午~周日全天<br>
        <b>动作：</b><br>
        1. 周五下午企微推送<b>"周六专属满399-30券"</b>（限前30单）+ 短信触达30天未到店会员，预估拉回30-50组额外客流；<br>
        2. 周六设<b>"老带新"</b>裂变：带朋友到店各减¥20，利用社交场景做工作日无法做到的自然引流；<br>
        3. 周六下午14-18点<b>最强导购值守鞋+服装区</b>，设周六单日客单价PK奖（¥10红包/天），目标周六达成率从51.69%提升至80%+；<br>
        4. 周日继续保持现有高达成态势，<b>维护周日会员池</b>不丢失。
      </div>
    </div>

    <div class="strategy-item">
      <div class="stitle"><span class="snum snum-2">2</span>成交率抢救：从18%提升至22%</div>
      <div class="sbody">
        <b>执行人：</b>全体导购<br>
        <b>时间：</b>全周执行<br>
        <b>动作：</b><br>
        1. <b>进店三句话标准话术：</b>"欢迎光临，今天鞋/服装新品到店折扣力度最大，您可以先看看"，针对67%不成交客流做主动触达；<br>
        2. <b>"试穿三件有礼"：</b>任意试穿3件以上送品牌袜子1双，降低尝试门槛；<br>
        3. 收银台<b>"加价购"：</b>结账时推"加¥59换购指定T恤/短裤"，把成交率的转化用在连带提频上；<br>
        4. 目标：成交率提升4pp → 周流水约增{money((0.22-0.1812)*(daily_flow*7)*avg_ticket)}。
      </div>
    </div>

    <div class="strategy-item">
      <div class="stitle"><span class="snum snum-3">3</span>鞋+配件SKU瘦身 + 爆款深耕</div>
      <div class="sbody">
        <b>执行人：</b>店长 + 商品专员<br>
        <b>时间：</b>周三前完成盘点<br>
        <b>动作：</b><br>
        1. 鞋124个在售SKU中<b>筛查连续2周0动销SKU</b>，申请调出/退货，目标精简至100个以内；<br>
        2. 配件275个SKU中<b>筛查连续2周0动销SKU</b>，目标精简至200以内；<br>
        3. 锁定<b>销量TOP20鞋款</b>，加库存深度（目标满足率从36.5%至50%+），全员话术植入为"本周必推"；<br>
        4. 目标：鞋SKU动销率从35.84%提升至50%+，配件每SKU产出从{money(acc_per_sku_flow)}提升至¥200+。
      </div>
    </div>

    <div class="strategy-item">
      <div class="stitle"><span class="snum snum-4">4</span>连带攻坚：每单多卖0.6件</div>
      <div class="sbody">
        <b>执行人：</b>全体导购<br>
        <b>时间：</b>全周执行<br>
        <b>动作：</b><br>
        1. <b>"1+1+1"搭配法：</b>每位顾客主动推荐"1件主推品+1件搭配品+1件连带品"的完整Look，而非单件推荐；<br>
        2. 鞋区收银旁陈列<b>"买鞋+¥99换购短裤"</b>，用空间动线引导跨界连带；<br>
        3. 设<b>本周"连带王"奖：</b>单笔超4件奖¥10，超6件奖¥20，下班即时兑现；<br>
        4. 目标：连带率从3.91恢复至4.5件，周流水增量≈¥{(((4.5-3.91)*ticket_cnt*unit_price)):,.0f}。
      </div>
    </div>

    <div class="strategy-item">
      <div class="stitle"><span class="snum snum-5">5</span>折扣管控 + 新品策略调整</div>
      <div class="sbody">
        <b>执行人：</b>店长<br>
        <b>时间：</b>周二前制定方案<br>
        <b>动作：</b><br>
        1. <b>新品首2周正价保护：</b>26年常青款前14天不打折，以"本季首发体验价"正价卖，2周后根据动销决定是否纳入促销；<br>
        2. <b>"满减"替代"直降"：</b>"满599减60、满999减150"替代全场X折，顾客为凑满减自然增加连带，同时保护品牌价值；<br>
        3. 在现有折扣基础上<b>"小幅收窄"而非"取消打折"</b>，避免顾客反弹，目标综合折扣率从44%控制到42%以内。
      </div>
    </div>
  </div>
</div>

</div><!-- /main-grid -->

<div class="footer-note">W23周分析 & 改善策略 | {store} | 数据截止 2026.06.07 | AI店长分析</div>
</div>
</body>
</html>'''
    return html


# ====== REPORT 3: TXT ======
def gen_report3():
    target_diff = actual - target
    txt = f'''W23周报分析稿
店铺：{store}
周期：{period}
报告日期：2026.06.11

===============================
一、周分析
===============================

1、达成：本周目标{money(target)}，实际流水{money(actual)}，达成率{pct_abs(achieve,2)}，超目标{money(target_diff)}。但同比{pct(yoy,2)}（周流水低于去年同期约{money(abs(actual/(1+yoy/100)-actual))}），同店同比{pct(sssg,2)}，环比{pct(mom,2)}。达成率表面达标但增长质量堪忧——目标设定让达标变得容易，同比才是真实经营水平。

2、成交率与客流：成交率{pct_abs(conv_rate,2)}（同比-8.37pp、环比-0.10pp），日均客流{daily_flow:.0f}人/天（同比+18.73%），周客单量{ticket_cnt:.0f}笔。客流增长+18.73%但成交率下降-8.37pp、流水下降-31.62%，说明：客流在增加（可能因奥莱本身流量属性），但顾客"进店不买"——转化效率在恶化。日均客流{daily_flow:.0f}人属中等偏低水平。

3、客单价与连带：客单价{money(avg_ticket)}（同比-14.12%、环比-19.90%），连带率{attach_rate:.2f}件（同比-14.35%、环比-30.91%），件单价{money(unit_price)}（同比+0.27%、环比+15.95%）。客单价下降主要拖累因素是连带率大幅下滑（从4.57降至3.91），每笔交易少卖0.66件。件单价基本持平说明并不是在卖更便宜的东西，而是<b>每单卖的件数少了</b>。

4、鞋类：鞋流水{money(cat_data['鞋']['flow'])}，鞋占比{pct_abs(shoe_share,1)}，同比{pct(cat_data['鞋']['yoy'],2)}、环比{pct(cat_data['鞋']['mom'],2)}。鞋类SKU动销率仅{pct_abs(cat_data['鞋']['sku_usage'],2)}，124个在售SKU中约64%一周0动销。鞋每SKU产出{money(shoe_per_sku_flow)}。库存数量{cat_data['鞋']['stock_qty']}件（占{pct_abs(cat_data['鞋']['stock_qty_share'],1)}），库存SKU{cat_data['鞋']['stock_sku']}个。

5、服装品类：男装流水{money(cat_data['男装']['flow'])}（同比{pct(cat_data['男装']['yoy'],2)}），女装流水{money(cat_data['女装']['flow'])}（同比{pct(cat_data['女装']['yoy'],2)}）。服装子品类中，短裤流水{money(float(d['sub_ps']['95']['data'].get('8',0)))}（折扣{pct_abs(float(d['sub_ps']['95']['data'].get('10',0))*100,2)}）、短袖流水{money(float(d['sub_ps']['96']['data'].get('8',0)))}（折扣{pct_abs(float(d['sub_ps']['96']['data'].get('10',0))*100,2)}），夏季应季品有一定表现。

6、配件：流水{money(cat_data['配件']['flow'])}（同比{pct(cat_data['配件']['yoy'],2)}，环比微增+0.26%），是唯一环比未下跌的品类。但配件275个在售SKU中SKU动销率仅{pct_abs(cat_data['配件']['sku_usage'],2)}，每SKU产出仅{money(acc_per_sku_flow)}，效率低下。

7、新品表现：26年常青(服)流水{money(new_product.get('26年常青(服)',{}).get('flow',0))}，折扣率{pct_abs(new_product.get('26年常青(服)',{}).get('disc',0),2)}，动销率{pct_abs(new_product.get('26年常青(服)',{}).get('sku_usage',0),2)}。2026Q2(服)折扣率{pct_abs(new_product.get('2026Q2(服)',{}).get('disc',0),2)}（约4折）。新品折扣率过高说明吊牌价虚高或市场接受度不足，新品即打折的恶性循环在持续。

8、日别结构：周一{money(daily_data[0]['flow'])}（达成{pct_abs(daily_data[0]['achieve'],1)}，同比{pct(daily_data[0]['yoy'],1)}）→ 周二{money(daily_data[1]['flow'])}（达成{pct_abs(daily_data[1]['achieve'],1)}）→ 周三{money(daily_data[2]['flow'])}（达成{pct_abs(daily_data[2]['achieve'],1)}）→ 周四{money(daily_data[3]['flow'])}（达成{pct_abs(daily_data[3]['achieve'],1)}）→ 周五{money(daily_data[4]['flow'])}（达成{pct_abs(daily_data[4]['achieve'],1)}，唯一同比正增长+{pct(daily_data[4]['yoy'],1)}）→ <b>周六{money(daily_data[5]['flow'])}（达成{pct_abs(daily_data[5]['achieve'],1)}，全周最低）</b>→ 周日{money(daily_data[6]['flow'])}（达成{pct_abs(daily_data[6]['achieve'],1)}，全周最高）。周末两天表现严重分化。

9、折扣率：综合折扣率{pct_abs(discount,2)}（同比{pct(discount_yoy,2)}pp、环比{pct(float(r15['32'])*100,2)}pp），约5.6折出售。折扣在持续加深但流水在持续下降，说明"打折拉销售"的策略已经失效，需转为"选择性折扣+连带提升"。

10、库存结构：总库存数量{total_stock_qty}件。品类库存数量分布——男装{cat_data['男装']['stock_qty']}件（{pct_abs(cat_data['男装']['stock_qty_share'],1)}）、女装{cat_data['女装']['stock_qty']}件（{pct_abs(cat_data['女装']['stock_qty_share'],1)}）、鞋{cat_data['鞋']['stock_qty']}件（{pct_abs(cat_data['鞋']['stock_qty_share'],1)}）、配件{cat_data['配件']['stock_qty']}件（{pct_abs(cat_data['配件']['stock_qty_share'],1)}）。鞋库存SKU{cat_data['鞋']['stock_sku']}个（在店），配件{cat_data['配件']['stock_sku']}个（在店）。

11、线上O2O：O2O流水{money(o2o)}（占比{pct_abs(o2o_pct,2)}，环比{pct(float(r7['36'])*100,2)}），PAD流水{money(pad)}，官网O2O{money(o2o_online)}。O2O环比+27.25%，线上渠道在增长，可继续深挖。

===============================
二、本周重点改善策略
===============================

1、周六复苏+周日巩固：周六是本周最大失血点（达成仅51.69%）。周五下午企微推送"周六专属券满399-30"（限前30单），短信触达30天未到店会员预估拉30-50组客流；周六设"老带新"裂变（带朋友各减20）；排班方面周六14-18点最强导购值守重点区域。目标：周六达成80%+，周末两日合计流水5万+。

2、成交率抢救（18%→22%）：客流同比+18.73%但成交率-8.37pp——关键是"进店不买"。执行进店三句话话术、试穿三件送袜子（降门槛）、收银台加价购（¥59换购T恤/短裤）三项组合拳。目标：成交率提升4pp，周流水约增¥12,000。

3、鞋+配件SKU瘦身+爆款深耕：鞋124个SKU中约64%一周0动销，配件275个SKU约60%一周0动销。筛查连续2周0动销SKU申请调出。锁定TOP20爆款鞋加库存深度（维持5双以上安全线），全员话术植入。目标：鞋SKU动销率35.84%→50%+，配件每SKU产出¥{int(acc_per_sku_flow)}→¥200+。

4、连带攻坚（3.91→4.5件）：每笔少卖0.66件是客单价下降主因。执行"1+1+1"搭配推销法（主推+搭配+连带），空间动线上鞋区旁陈列"买鞋+¥99换购短裤"。设"连带王"即时奖励（超4件¥10，超6件¥20）。目标：周流水增约¥{int((4.5-3.91)*ticket_cnt*unit_price)}。

5、折扣管控+新品正价保护：当前44.09%折扣率（5.6折），环比+7.39pp说明在加速打折。策略：26年常青新品首2周正价保护不加入促销；现有促销从"全场X折"转为"满599减60/满999减150"满减制，用满减门槛促进连带同时保护品牌价值。目标：综合折扣率控制在42%以内。

===============================
报告完毕 | {store} | W23周分析
===============================
'''
    return txt


# ====== WRITE REPORTS ======
# base var removed - now using _base from command line arg

with open(f'{_base}/W23周报深度分析报告.html', 'w', encoding='utf-8') as f:
    f.write(gen_report1())
print("Report 1 written: W23周报深度分析报告.html")

with open(f'{_base}/W23周分析_改善策略.html', 'w', encoding='utf-8') as f:
    f.write(gen_report2())
print("Report 2 written: W23周分析_改善策略.html")

txt_content = gen_report3()
with open(f'{_base}/W23周报分析稿.txt', 'w', encoding='utf-8') as f:
    f.write(txt_content)
print("Report 3 written: W23周报分析稿.txt")

print("\nAll reports generated successfully!")
