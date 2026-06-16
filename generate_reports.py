#!/usr/bin/env python
"""Generate dynamic weekly analysis reports from extracted data."""
import json, sys

_base = sys.argv[1] if len(sys.argv) > 1 else '.'
with open(f'{_base}/extracted_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

r7 = d['r7_kpi']; r15 = d['r15_price']; daily = d['daily']; cate = d['category']
store = "奥莱店华南区城市"
rc = d.get('report_config', {}); period = rc.get('_version', 'W24')

target = r7['14']; actual = r7['17']; achieve = r7['20']*100
conv_rate = r7['5']*100; daily_flow = r7['8']; yoy = r7['22']*100; sssg = r7['24']*100; mom = r7['28']*100
o2o = r7['33'] or 0; o2o_pct = r7['35']*100 if r7['35'] else 0; o2o_online = r7['39'] or 0; pad = r7['37'] or 0
unit_price = r15['4']; avg_ticket = r15['10']; attach_rate = r15['16']; discount = r15['28']*100; ticket_cnt = r15['22']
unit_yoy = r15['6']*100; ticket_yoy = r15['12']*100; attach_yoy = r15['18']*100
discount_yoy = r15['30']*100; discount_mom = r15['32']*100 if r15.get('32') else 0

day_keys = ['4','6','8','10','12','14','16']; day_names = ['周一','周二','周三','周四','周五','周六','周日']
daily_data = []
for i, dk in enumerate(day_keys):
    daily_data.append({'name':day_names[i],'target':float(daily['21']['data'][dk]),'flow':float(daily['22']['data'][dk]),
        'achieve':float(daily['23']['data'][dk])*100,'yoy':float(daily['24']['data'][dk])*100,
        'mom':float(daily['25']['data'][dk])*100,'conv':float(daily['27']['data'][dk])*100,
        'visitors':int(round(float(daily['28']['data'][dk]))),'ticket':float(daily['29']['data'][dk]),'attach':float(daily['30']['data'][dk])})

cat_labels = {'4':'男装','6':'女装','14':'鞋','16':'配件'}
cat_data = {}
for ck, cn in cat_labels.items():
    cat_data[cn] = {'flow':float(cate['36']['data'].get(ck,0)),'qty':int(float(cate['37']['data'].get(ck,0))),
        'disc':float(cate['38']['data'].get(ck,0))*100,'yoy':float(cate['42']['data'].get(ck,0))*100,
        'mom':float(cate['40']['data'].get(ck,0))*100,'flow_share':float(cate['44']['data'].get(ck,0))*100,
        'sku_sell':int(float(cate['47']['data'].get(ck,0))),'sku_usage':float(cate['50']['data'].get(ck,0))*100 if cate['50']['data'].get(ck) else 0,
        'stock_qty':int(float(cate['52']['data'].get(ck,0)))}
tsq = sum(cat_data[c]['stock_qty'] for c in cat_data)
for cn in cat_data:
    sqs = cat_data[cn]['stock_qty']/tsq*100; fs = cat_data[cn]['flow_share']; g = fs-sqs
    cat_data[cn]['stock_qty_share'] = sqs
    cat_data[cn]['match'] = '匹配' if abs(g)<=5 else f'销>库 +{g:.1f}pp' if g>0 else f'库>销 {abs(g):.1f}pp'

shoe_share = cat_data['鞋']['flow_share']
shoe_per_sku = cat_data['鞋']['flow']/max(cat_data['鞋']['sku_sell'],1)
acc_per_sku = cat_data['配件']['flow']/max(cat_data['配件']['sku_sell'],1)
conv_yoy_pp = float(r7['6'])*100
worst_day = min(daily_data, key=lambda d:d['achieve'])
best_day = max(daily_data, key=lambda d:d['achieve'])
wc = min(cat_data.items(), key=lambda x:x[1]['yoy'])
bc = max(cat_data.items(), key=lambda x:x[1]['yoy'])
yoy_sev = '暴增' if yoy>=20 else '大幅增长' if yoy>=10 else '增长' if yoy>=3 else '微增' if yoy>0 else '暴跌' if yoy<=-20 else '大幅下滑' if yoy<=-10 else '下滑' if yoy<=-3 else '微降'
tl = actual/(1+yoy/100) if abs(yoy)>0.01 else actual; dvl = abs(actual-tl)

seas = d['seasonal']; npd = {}
if '5' in seas:
    r5,r7s,r6s = seas['5'],seas.get('7'),seas.get('6')
    fk = [('4','2025Q4及以前(服)'),('6','2026Q1(服)'),('8','2026Q2(服)'),('10','2026Q3+(服)'),('13','26年常青(服)'),
          ('15','2025Q4及以前(鞋)'),('18','2026Q1(鞋)'),('20','2026Q2(鞋)'),('22','2026Q3+(鞋)'),('25','26年常青(鞋)')]
    for ck,lb in fk:
        if ck in r5:
            npd[lb] = {'flow':float(r5[ck]),'disc':float(r7s[ck])*100 if r7s and ck in r7s else 0,
                'qty':int(float(r6s[ck])) if r6s and ck in r6s else 0}
dr_data = d.get('discount_range',{}).get('211',{}).get('data',{})

def p(v,d=2): return f"{v:+.{d}f}%" if v is not None else '--'
def pa(v,d=2): return f"{v:.{d}f}%" if v is not None else '--'
def m(v): return f"¥{v:,.0f}" if v is not None else '--'
def dw(v,u='增长',w='下降'): return u if v>0 else w if v<0 else '持平'

# ──── REPORT 1 ────
def r1():
    p2l = worst_day['target']-worst_day['flow']
    npec = npd.get('26年常青(服)',{}); npes = npd.get('26年常青(鞋)',{}); npq2 = npd.get('2026Q2(服)',{})

    drs = ''
    for d in daily_data:
        bg = ' style="background:#fef2f2;"' if d['achieve']<100 else (' style="background:#f0fdf4;"' if d['achieve']>150 else '')
        ac = 'td-red' if d['achieve']<100 else 'td-green'
        yc = 'td-green' if d['yoy']<0 else 'td-red'
        drs += f'<tr{bg}><td>{d["name"]}</td><td>{m(d["target"])}</td><td>{m(d["flow"])}</td><td class="{ac}">{pa(d["achieve"],1)}</td><td class="{yc}">{p(d["yoy"],1)}</td><td>{pa(d["conv"])}</td><td>{d["visitors"]}</td><td>{m(d["ticket"])}</td></tr>'

    ctr = ''
    for cn in ['男装','女装','鞋','配件']:
        c = cat_data[cn]; yc = 'td-green' if c['yoy']<0 else 'td-red'
        ctr += f'<tr><td>{cn}</td><td>{m(c["flow"])}</td><td>{pa(c["flow_share"])}</td><td>{c["qty"]}</td><td>{pa(c["disc"])}</td><td class="{yc}">{p(c["yoy"])}</td><td>{c["stock_qty"]}</td><td>{pa(c["stock_qty_share"])}</td><td>{c["match"]}</td></tr>'

    mr = f'''<tr><td>流水达成率</td><td>{pa(achieve)}</td><td class="td-green">{p(yoy)}</td><td class="td-green">{p(mom)}</td><td><span class="tag tag-{'up' if yoy>0 else 'down'}">{"🔥" if yoy>0 else "⚠️"}</span></td></tr>
<tr><td>成交率</td><td>{pa(conv_rate)}</td><td class="td-green">{p(conv_yoy_pp)}pp</td><td class="{'td-red' if float(r7['7'])*100>0 else 'td-green'}">{p(float(r7['7'])*100)}pp</td><td><span class="tag tag-{'up' if conv_yoy_pp>0 else 'down'}">{"🔥" if conv_yoy_pp>0 else "⚠️"}</span></td></tr>
<tr><td>日均客流</td><td>{daily_flow:.0f}人</td><td class="td-red">{p(float(r7['10'])*100)}</td><td class="td-green">{p(float(r7['12'])*100)}</td><td><span class="tag tag-{'up' if float(r7['10'])*100>0 else 'down'}">{"🔥" if float(r7['10'])*100>0 else "⚠️"}</span></td></tr>
<tr><td>客单价</td><td>{m(avg_ticket)}</td><td class="td-red">{p(ticket_yoy)}</td><td class="{'td-red' if float(r15['14'])*100>0 else 'td-green'}">{p(float(r15['14'])*100)}</td><td><span class="tag tag-{'up' if ticket_yoy>0 else 'down'}">{"🔥" if ticket_yoy>0 else "⚠️"}</span></td></tr>
<tr><td>连带率</td><td>{attach_rate:.2f}件</td><td class="td-red">{p(attach_yoy)}</td><td class="{'td-red' if float(r15['20'])*100>0 else 'td-green'}">{p(float(r15['20'])*100)}</td><td><span class="tag tag-{'up' if attach_yoy>0 else 'down'}">{"🔥" if attach_yoy>0 else "⚠️"}</span></td></tr>
<tr><td>件单价</td><td>{m(unit_price)}</td><td class="{'td-red' if unit_yoy>0 else 'td-green'}">{p(unit_yoy)}</td><td class="{'td-red' if float(r15['8'])*100>0 else 'td-green'}">{p(float(r15['8'])*100)}</td><td><span class="tag tag-{'up' if unit_yoy>0 else 'down'}">{"🔥" if unit_yoy>0 else "⚠️"}</span></td></tr>
<tr><td>折扣率</td><td>{pa(discount)}</td><td class="td-green">{p(discount_yoy)}pp</td><td class="td-green">{p(discount_mom)}pp</td><td><span class="tag tag-{'down' if discount_yoy<0 else 'up'}">{"🔥" if discount_yoy<0 else "⚠️"}</span></td></tr>
<tr><td>SSSG</td><td>{p(sssg)}</td><td class="td-red">{p(sssg)}</td><td class="td-green">{p(mom)}</td><td><span class="tag tag-{'up' if sssg>0 else 'down'}">{"🔥" if sssg>0 else "⚠️"}</span></td></tr>'''

    tm = float(r7['7'])*100
    prob = f'''<div class="problem-card"><span class="pnum">1</span><h3>整体流水{yoy_sev}：达成{pa(achieve)}，同比{dw(yoy)}{p(yoy)}</h3>
<div class="loss-tag">周流水同比{dw(yoy)} ≈ {m(dvl)}</div><div class="data-box"><table><tr><td>本周流水 <b>{m(actual)}</b></td><td>同比 <b style="color:{"#27ae60" if yoy>0 else "#ef4444"};">{p(yoy)}</b></td><td>达成率 <b style="color:{"#27ae60" if achieve>=100 else "#ef4444"};">{pa(achieve)}</b></td><td>（{"超目标"+m(actual-target) if achieve>=100 else "缺口"+m(target-actual)}）</td></tr><tr><td>成交率 <b>{pa(conv_rate)}</b>（同比{p(conv_yoy_pp)}pp）</td><td>客单价 <b>{m(avg_ticket)}</b>（同比{p(ticket_yoy)}）</td><td>连带率 <b>{attach_rate:.2f}</b>（同比{p(attach_yoy)}）</td><td>三项核心指标{dw(ticket_yoy)}/{dw(attach_yoy)}</td></tr></table><div style="margin-top:6px;font-size:12px;color:#5a5a7a;">若恢复到去年同期水平：周流水应达 {m(tl)}，差距 <b>{m(dvl)}</b></div></div>
<div class="cause"><b>产生原因：</b><br>1. 折扣率{pa(discount)}（同比{p(discount_yoy)}pp），{"折扣持续加深但流水未同步增长" if discount>40 else "折扣在可控范围内"}；<br>2. 成交率{pa(conv_rate)}（同比{p(conv_yoy_pp)}pp），{"转化效率在改善" if conv_yoy_pp>0 else "转化效率在恶化"}；<br>3. 日均客流{daily_flow:.0f}人（同比{p(float(r7['10'])*100)}），{"客流增长带动了进店量" if float(r7['10'])*100>0 else "客流量有所下降"}；<br>4. 客单价{m(avg_ticket)}（同比{p(ticket_yoy)}），{dw(ticket_yoy,"提升带动了流水增长","下降对流水形成拖累")}。</div></div>

<div class="problem-card"><span class="pnum">2</span><h3>{worst_day["name"]}崩盘 — 达成率仅{pa(worst_day["achieve"],1)}{", 单日损失"+m(abs(p2l)) if p2l>0 else ""}</h3>
<div class="loss-tag">预计损失 ≈ {m(abs(p2l))}（{worst_day["name"]}达成率仅{pa(worst_day["achieve"],1)}）</div><div class="data-box"><table><tr><td>{worst_day["name"]}目标 <b>{m(worst_day["target"])}</b></td><td>实际 <b style="color:#ef4444;">{m(worst_day["flow"])}</b></td><td>达成率 <b style="color:#ef4444;">{pa(worst_day["achieve"],1)}</b></td><td>同比 <b style="color:#ef4444;">{p(worst_day["yoy"],1)}</b></td></tr><tr><td>{worst_day["name"]}客流 <b>{worst_day["visitors"]}</b>人</td><td>成交率 <b>{pa(worst_day["conv"])}</b></td><td>客单价 <b>{m(worst_day["ticket"])}</b></td><td>（{("全周唯一达成率低于60%的日" if worst_day["achieve"]<60 else "全周达成率最弱日")}）</td></tr></table></div>
<div class="cause"><b>产生原因：</b><br>1. {worst_day["name"]}目标{m(worst_day["target"])}{"，目标设定可能偏高" if worst_day["target"]>sum(d["target"] for d in daily_data)/7*1.5 else "，与平日相当"}；<br>2. {worst_day["name"]}客流{worst_day["visitors"]}人{"（显著低于其他日）" if worst_day["visitors"]<sum(d["visitors"] for d in daily_data)/7*0.7 else "，与平日基本持平"}；<br>3. {worst_day["name"]}客单价{m(worst_day["ticket"])}、连带率{worst_day["attach"]:.2f}{"，均低于全周均值" if worst_day["ticket"]<sum(d["ticket"] for d in daily_data)/7*0.85 else "，处于正常水平"}；<br>4. 可能受商场活动/竞品促销/天气等外部因素影响。</div></div>

<div class="problem-card"><span class="pnum">3</span><h3>品类表现：{dw(bc[1]["yoy"])} vs {dw(wc[1]["yoy"])}</h3>
<div class="data-box"><table><tr><th>品类</th><th>流水</th><th>同比</th><th>环比</th><th>折扣率</th><th>每SKU产出</th></tr>{ctr}</table></div>
<div class="cause"><b>产生原因：</b><br>1. {wc[0]}同比{p(wc[1]["yoy"])}{"，作为核心品类失速最严重" if wc[0] in ["鞋","男装"] else "，表现弱于其他品类"}；<br>2. {"部分品类环比增长，趋势向好" if any(cat_data[c]["mom"]>0 for c in cat_data) else "各品类环比均下滑，趋势需关注"}。</div></div>

<div class="problem-card"><span class="pnum">4</span><h3>客单价与连带率{dw(ticket_yoy,"双升","双降")}</h3>
<div class="loss-tag">客单价同比{p(ticket_yoy)}，连带率同比{p(attach_yoy)}</div>
<div class="data-box"><table><tr><th>指标</th><th>本周</th><th>同比</th><th>环比</th><th>解读</th></tr>
<tr><td>客单价</td><td>{m(avg_ticket)}</td><td class="{'td-red' if ticket_yoy>0 else 'td-green'}">{p(ticket_yoy)}</td><td class="{'td-red' if float(r15['14'])*100>0 else 'td-green'}">{p(float(r15['14'])*100)}</td><td>{dw(ticket_yoy,"持续上行","持续下行")}</td></tr>
<tr><td>连带率</td><td>{attach_rate:.2f}件</td><td class="{'td-red' if attach_yoy>0 else 'td-green'}">{p(attach_yoy)}</td><td class="{'td-red' if float(r15['20'])*100>0 else 'td-green'}">{p(float(r15['20'])*100)}</td><td>{dw(attach_yoy,"明显提升","大幅下滑")}</td></tr>
<tr><td>件单价</td><td>{m(unit_price)}</td><td class="{'td-red' if unit_yoy>0 else 'td-green'}">{p(unit_yoy)}</td><td>{p(float(r15['8'])*100)}</td><td>{dw(unit_yoy,"提升","基本持平")}</td></tr></table></div></div>

<div class="problem-card"><span class="pnum">5</span><h3>折扣率{dw(discount_yoy,"持续走高","有所回落")}：{pa(discount)}</h3>
<div class="loss-tag">折扣率同比{p(discount_yoy)}pp、环比{p(discount_mom)}pp</div><div class="data-box"><table><tr><th>折扣区间</th><th>数量</th><th>占比</th></tr>
<tr style="background:#fee2e2;"><td>5折以下</td><td>{dr_data.get("1","--")}</td><td>{dr_data.get("2","--")}</td></tr>
<tr><td>5-6折</td><td>{dr_data.get("4","--")}</td><td>{dr_data.get("5","--")}</td></tr>
<tr><td>6-7折</td><td>{dr_data.get("7","--")}</td><td>{dr_data.get("8","--")}</td></tr>
<tr><td>7-8折</td><td>{dr_data.get("10","--")}</td><td>{dr_data.get("11","--")}</td></tr>
<tr><td>8折以上</td><td>{dr_data.get("13","--")}</td><td>{dr_data.get("14","--")}</td></tr></table></div>
<div class="cause"><b>产生原因：</b><br>1. 折扣率{pa(discount)}意味着平均约{(100-discount)/10:.1f}折出售；<br>2. {"顾客对常年打折形成预期" if discount>40 else "当前折扣水平在奥莱正常范围内"}。</div></div>

<div class="problem-card"><span class="pnum">6</span><h3>新品表现分析</h3>
<div class="data-box"><table><tr><th>季节</th><th>流水</th><th>折扣率</th><th>数量</th></tr>
<tr><td>26年常青(服)</td><td>{m(npec.get("flow",0))}</td><td>{pa(npec.get("disc",0))}</td><td>{npec.get("qty",0)}</td></tr>
<tr><td>26年常青(鞋)</td><td>{m(npes.get("flow",0))}</td><td>{pa(npes.get("disc",0))}</td><td>{npes.get("qty",0)}</td></tr>
<tr><td>2026Q2(服)</td><td>{m(npq2.get("flow",0))}</td><td>{pa(npq2.get("disc",0))}</td><td>{npq2.get("qty",0)}</td></tr></table></div></div>'''

    opp = f'''<div class="opp-card"><span class="onum">1</span><h3>{worst_day["name"]}复苏攻坚 — 夺回单日{m(abs(p2l))}增量</h3>
<div class="action"><b>目标：</b>{worst_day["name"]}达成率从{pa(worst_day["achieve"],1)}恢复至80%+。<br>
<b>方案A：</b>提前推送专属券+短信触达30天未到店会员；<br>
<b>方案B：</b>"带朋友到店各减20元"裂变活动；<br>
<b>方案C：</b>最强导购值守高价值区域，设单日PK奖。</div></div>
<div class="opp-card"><span class="onum">2</span><h3>流量激活：成交率从{pa(conv_rate)}提升至{pa(min(conv_rate+4,30))}</h3>
<div class="action"><b>目标：</b>提升成交率4pp，周增流水≈{m((conv_rate/100+0.04-conv_rate/100)*(daily_flow*7)*avg_ticket) if conv_rate>0 else m(0)}。<br>
<b>方案A：</b>进店三句话标准话术；<br>
<b>方案B：</b>"试穿三件即送"降低门槛；<br>
<b>方案C：</b>收银台"加价购"转化增量。</div></div>
<div class="opp-card"><span class="onum">3</span><h3>品类深耕：聚焦{bc[0] if bc[1]["yoy"]>0 else wc[0]}的{dw(bc[1]["yoy"],"优势放大","改善提升")}</h3>
<div class="action"><b>方案A：</b>分析{wc[0]}同比{p(wc[1]["yoy"])}根因；<br>
<b>方案B：</b>{bc[0]}同比{p(bc[1]["yoy"])}，提炼经验复制；<br>
<b>方案C：</b>清理连续2周0动销SKU。</div></div>
<div class="opp-card"><span class="onum">4</span><h3>连带攻坚：{attach_rate:.2f}件{("→保持高位" if attach_yoy>0 else "→"+str(round(attach_rate+0.6,2))+"件")}</h3>
<div class="action"><b>方案A：</b>"1+1+1"搭配法；<br>
<b>方案B：</b>衣鞋跨界连带；<br>
<b>方案C：</b>连带即时激励。</div></div>
<div class="opp-card"><span class="onum">5</span><h3>折扣管控：从"全打折"转向"选择性折扣"</h3>
<div class="action"><b>目标：</b>综合折扣率{"控制在"+str(round(discount-2,1))+"%以内" if discount>40 else "保持在"+str(round(discount,1))+"%左右"}。<br>
<b>方案A：</b>新品首2周正价保护；<br>
<b>方案B：</b>分品类差异化折扣；<br>
<b>方案C：</b>满减替代直降。</div></div>
<div class="opp-card"><span class="onum">6</span><h3>O2O渠道发力 + {best_day["name"]}巩固</h3>
<div class="action"><b>目标：</b>O2O从{m(o2o)}提升至{m(o2o*1.3)}+。<br>
<b>方案A：</b>{best_day["name"]}模式复制（达成{pa(best_day["achieve"],1)}/客单价{m(best_day["ticket"])}）；<br>
<b>方案B：</b>PAD+官网O2O同步推；<br>
<b>方案C：</b>会员精准触达。</div></div>'''

    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{period} 周报深度分析 | 6大问题点 + 机会点</title><style>
:root{{--bg:#f5f6f8;--card:#fff;--t:#1a1a2e;--t2:#5a5a7a;--b:#e8ecf1;--r:#e74c3c;--g:#27ae60;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--t);line-height:1.7;}}
.rp{{max-width:1150px;margin:0 auto;padding:24px 20px 60px;}}
.hd{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:32px 36px;border-radius:16px;margin-bottom:24px;}}
.hd h1{{font-size:26px;font-weight:700;}}
.hd .m{{font-size:14px;opacity:.85;margin-top:6px;}}
.sc{{background:var(--card);border-radius:14px;padding:28px 32px;margin-bottom:18px;box-shadow:0 1px 3px rgba(0,0,0,.04);border:1px solid var(--b);}}
.sc h2{{font-size:18px;font-weight:700;margin-bottom:20px;}}
table{{width:100%;border-collapse:collapse;font-size:13px;}}
th{{background:#f1f5f9;padding:9px 10px;text-align:center;font-weight:600;color:var(--t2);font-size:12px;border-bottom:2px solid var(--b);}}
td{{padding:9px 10px;text-align:center;border-bottom:1px solid var(--b);}}
tr:nth-child(even){{background:#fafbfc;}}
td:first-child,th:first-child{{text-align:left;font-weight:600;}}
.td-red{{color:var(--r);font-weight:700;}}
.td-green{{color:var(--g);font-weight:700;}}
.tag{{display:inline-block;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600;}}
.tag-up{{background:#fee2e2;color:#991b1b;}}
.tag-down{{background:#d1fae5;color:#065f46;}}
.pc{{background:#fef2f2;border-left:5px solid #ef4444;border-radius:10px;padding:18px 22px;margin-bottom:16px;}}
.pc .pn{{display:inline-block;background:#ef4444;color:#fff;width:28px;height:28px;border-radius:50%;text-align:center;line-height:28px;font-weight:800;font-size:14px;margin-right:10px;vertical-align:middle;}}
.pc h3{{display:inline;font-size:16px;color:#991b1b;}}
.pc .lt{{background:#fecaca;display:inline-block;padding:2px 10px;border-radius:4px;font-weight:700;color:#7f1d1d;font-size:13px;margin:8px 0;}}
.pc .db{{background:#fff;border-radius:8px;padding:12px 16px;margin:10px 0;font-size:13px;}}
.pc .cs{{margin-top:8px;font-size:13.5px;line-height:1.8;}}
.oc{{background:#f0fdf4;border-left:5px solid #22c55e;border-radius:10px;padding:18px 22px;margin-bottom:16px;}}
.oc .on{{display:inline-block;background:#22c55e;color:#fff;width:28px;height:28px;border-radius:50%;text-align:center;line-height:28px;font-weight:800;font-size:14px;margin-right:10px;vertical-align:middle;}}
.oc h3{{display:inline;font-size:16px;color:#065f46;}}
.oc .ac{{font-size:13.5px;line-height:1.8;margin-top:8px;}}
.ftr{{text-align:center;padding:20px;color:var(--t2);font-size:12px;}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px;}}
.hbx{{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-radius:12px;padding:16px 20px;margin:14px 0;font-size:14px;}}
hr{{border:none;border-top:1px solid var(--b);margin:16px 0;}}
</style></head><body><div class="rp">
<div class="hd"><h1>{period} 周报深度分析报告</h1><div class="m">{store} | {period} | 本周流水{m(actual)} | 达成率{pa(achieve)}</div></div>
<div class="sc"><h2>一、本周核心KPI全貌</h2>
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px;">
<div style="background:#f9fafb;border-radius:10px;padding:16px;border:1px solid var(--b);"><div style="font-size:12px;color:var(--t2);">流水</div><div style="font-size:22px;font-weight:700;">{m(actual)}</div><div style="font-size:13px;color:{"#27ae60" if achieve>=100 else "#e74c3c"};font-weight:600;">达成率{pa(achieve)}</div></div>
<div style="background:#f9fafb;border-radius:10px;padding:16px;border:1px solid var(--b);"><div style="font-size:12px;color:var(--t2);">同比/环比</div><div style="font-size:22px;font-weight:700;color:{"#e74c3c" if yoy>0 else "#27ae60"};">{p(yoy)}</div><div style="font-size:13px;color:var(--t2);">环比{p(mom)}</div></div>
<div style="background:#f9fafb;border-radius:10px;padding:16px;border:1px solid var(--b);"><div style="font-size:12px;color:var(--t2);">成交率</div><div style="font-size:22px;font-weight:700;">{pa(conv_rate)}</div><div style="font-size:13px;color:{"#e74c3c" if conv_yoy_pp>0 else "#27ae60"};font-weight:600;">同比{p(conv_yoy_pp)}pp</div></div>
<div style="background:#f9fafb;border-radius:10px;padding:16px;border:1px solid var(--b);"><div style="font-size:12px;color:var(--t2);">客单价</div><div style="font-size:22px;font-weight:700;">{m(avg_ticket)}</div><div style="font-size:13px;color:{"#e74c3c" if ticket_yoy>0 else "#27ae60"};font-weight:600;">同比{p(ticket_yoy)}</div></div>
<div style="background:#f9fafb;border-radius:10px;padding:16px;border:1px solid var(--b);"><div style="font-size:12px;color:var(--t2);">日均客流</div><div style="font-size:22px;font-weight:700;">{daily_flow:.0f}人</div><div style="font-size:13px;color:{"#e74c3c" if float(r7['10'])*100>0 else "#27ae60"};font-weight:600;">同比{p(float(r7['10'])*100)}</div></div>
<div style="background:#f9fafb;border-radius:10px;padding:16px;border:1px solid var(--b);"><div style="font-size:12px;color:var(--t2);">连带率</div><div style="font-size:22px;font-weight:700;">{attach_rate:.2f}</div><div style="font-size:13px;color:{"#e74c3c" if attach_yoy>0 else "#27ae60"};font-weight:600;">同比{p(attach_yoy)}</div></div>
<div style="background:#f9fafb;border-radius:10px;padding:16px;border:1px solid var(--b);"><div style="font-size:12px;color:var(--t2);">折扣率</div><div style="font-size:22px;font-weight:700;">{pa(discount)}</div><div style="font-size:13px;color:{"#e74c3c" if discount_yoy<0 else "#27ae60"};font-weight:600;">同比{p(discount_yoy)}pp</div></div>
<div style="background:#f9fafb;border-radius:10px;padding:16px;border:1px solid var(--b);"><div style="font-size:12px;color:var(--t2);">鞋占比</div><div style="font-size:22px;font-weight:700;">{pa(shoe_share,1)}</div><div style="font-size:13px;color:var(--t2);">O2O {pa(o2o_pct,1)}</div></div>
</div></div>
<div class="sc"><h2>KPI同比/环比对比矩阵</h2><table><thead><tr><th>指标</th><th>本周值</th><th>同比</th><th>环比</th><th>趋势</th></tr></thead><tbody>{mr}</tbody></table></div>
<div class="sc"><h2>日别销售趋势</h2><table><thead><tr><th>日期</th><th>目标</th><th>流水</th><th>达成率</th><th>同比</th><th>成交率</th><th>客流</th><th>客单价</th></tr></thead><tbody>{drs}<tr style="font-weight:700;background:#f1f5f9;"><td>合计</td><td>{m(target)}</td><td>{m(actual)}</td><td>{pa(achieve,1)}</td><td>{p(yoy,1)}</td><td>{pa(conv_rate)}</td><td>{daily_flow:.0f}</td><td>{m(avg_ticket)}</td></tr></tbody></table></div>
<hr><div class="sc" style="border-top:3px solid #ef4444;"><h2>二、六大关键问题点</h2></div>{prob}
<div class="sc"><h2>品类结构速览</h2><div class="grid2"><div><table><thead><tr><th>品类</th><th>流水</th><th>占比</th><th>销量</th><th>折扣</th><th>同比</th><th>库存</th><th>库占</th><th>匹配</th></tr></thead><tbody>{ctr}</tbody></table></div><div class="hbx"><strong>鞋每SKU产出 {m(shoe_per_sku)} vs 配件 {m(acc_per_sku)}</strong><br>鞋占比{pa(shoe_share,1)}，库存数{cat_data["鞋"]["stock_qty"]}件（{pa(cat_data["鞋"]["stock_qty_share"],1)}）</div></div></div>
<hr><div class="sc" style="border-top:3px solid #22c55e;"><h2>三、六大机会点 & 可落地方案</h2></div>{opp}
<div class="sc" style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;border:none;"><h2 style="color:#fbbf24;">总结</h2>
<p style="font-size:15px;line-height:1.9;margin-top:16px;">流水达成{pa(achieve)}，同比{dw(yoy)}{p(yoy)}。{"主要矛盾在于客流转化效率+连带率" if conv_yoy_pp<0 and attach_yoy<0 else "成交率是主要瓶颈" if conv_yoy_pp<0 else "关键指标全面向好"}。<br>六项措施联动落地，预计释放 <strong style="color:#fbbf24;">¥{int(actual*0.08):,}/周</strong> 增量空间（按8%改善估算）。</p></div>
<div class="ftr">{period}周报深度分析 | {store} | AI店长出品</div></div></body></html>'''

# ──── REPORT 2 ────
def r2():
    da = '→'.join(f'{d["name"]}<span class="{"red" if d["achieve"]<80 else "green"}">{d["achieve"]:.0f}%</span>' for d in daily_data)
    ct = ''
    for cn in ['男装','女装','鞋','配件']:
        c = cat_data[cn]; ct += f'<tr><td>{cn}</td><td>{m(c["flow"])}</td><td class="red">{p(c["yoy"],1)}</td><td class="green">{p(c["mom"],1)}</td><td>{pa(c["disc"],1)}</td><td>{pa(c["sku_usage"],1) if cn in ("鞋","配件") else "--"}</td></tr>'

    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{period} 周分析 & 重点改善策略</title><style>
:root{{--bg:#f2f3f5;--card:#fff;--t:#1a1a2e;--s:#6b7280;--r:#dc2626;--g:#16a34a;--b:#2563eb;--o:#f59e0b;--bd:#e5e7eb;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--t);font-size:14px;line-height:1.65;}}
.pg{{max-width:1200px;margin:0 auto;padding:20px 24px;}}
.mg{{display:grid;grid-template-columns:1.15fr 1fr;gap:20px;}}
@media(max-width:900px){{.mg{{grid-template-columns:1fr;}}}}
.ct{{font-size:17px;font-weight:800;padding:6px 0 14px;display:flex;align-items:center;gap:8px;border-bottom:2px solid var(--bd);margin-bottom:14px;}}
.bl{{background:var(--card);border-radius:10px;padding:18px 20px;margin-bottom:14px;border:1px solid var(--bd);}}
.bl h3{{font-size:15px;font-weight:700;margin-bottom:10px;}}
.up{{color:var(--r);font-weight:600;}}.down{{color:var(--g);font-weight:600;}}
.red{{color:var(--r);font-weight:700;}}.green{{color:var(--g);font-weight:700;}}
.dl{{font-size:13.5px;line-height:1.8;}}
.tag{{display:inline-block;padding:1px 8px;border-radius:12px;font-size:11px;font-weight:600;margin:0 2px;}}
.tag-r{{background:#fee2e2;color:#991b1b;}}
.tag-g{{background:#d1fae5;color:#065f46;}}
.tag-o{{background:#fef3c7;color:#92400e;}}
.hl{{background:#fffbeb;border-radius:6px;padding:10px 14px;margin:8px 0;font-size:13px;border-left:3px solid var(--o);}}
.si{{padding:12px 0;border-bottom:1px solid var(--bd);}}
.si:last-child{{border-bottom:none;}}
.si .sn{{display:inline-flex;width:26px;height:26px;border-radius:50%;font-weight:800;font-size:13px;margin-right:8px;justify-content:center;align-items:center;}}
.si .st{{font-weight:700;font-size:14px;display:flex;align-items:center;margin-bottom:4px;}}
.si .sb{{font-size:13px;color:#4b5563;line-height:1.7;padding-left:34px;}}
.s1{{background:#eff6ff;color:#2563eb;}}.s2{{background:#fef3c7;color:#d97706;}}
.s3{{background:#f0fdf4;color:#16a34a;}}.s4{{background:#fef2f2;color:#dc2626;}}.s5{{background:#f5f3ff;color:#7c3aed;}}
.dv{{border:none;border-top:1px dashed var(--bd);margin:10px 0;}}
.fn{{font-size:11px;color:#9ca3af;text-align:right;margin-top:12px;}}
.tm{{width:100%;font-size:12.5px;border-collapse:collapse;margin:8px 0;}}
.tm th{{background:#f1f5f9;padding:6px 8px;text-align:center;font-weight:600;color:var(--s);border-bottom:1px solid var(--bd);}}
.tm td{{padding:6px 8px;text-align:center;border-bottom:1px solid var(--bd);}}
</style></head><body><div class="pg"><div class="mg">
<div><div class="ct"><span class="dot" style="width:8px;height:8px;border-radius:50%;display:inline-block;background:#dc2626;"></span> 周分析 — {period}</div>
<div class="bl"><h3>达成：{pa(achieve,1)} | 同比 <span class="{'down' if yoy<0 else 'up'}">{p(yoy)}</span></h3>
<div class="dl">周目标达成{pa(achieve,1)}，{"超目标"+m(actual-target) if achieve>=100 else "缺口"+m(target-actual)}。<br>同比{dw(yoy)}{p(yoy)}，同店同比{p(sssg)}。<br>日别: {da}<br><span class="tag {'tag-r' if worst_day['achieve']<80 else 'tag-o'}">{worst_day["name"]}达成{pa(worst_day["achieve"],1)}</span></div></div>
<div class="bl"><h3>成交率：{pa(conv_rate)} | 同比{p(conv_yoy_pp)}pp</h3><div class="dl">日均客流{daily_flow:.0f}人/天（同比{p(float(r7['10'])*100)}）。<br>
<div class="hl">客流同比{p(float(r7['10'])*100)}，成交率同比{p(conv_yoy_pp)}pp。{"客流增长但成交率下降——进店转化效率在恶化" if float(r7['10'])*100>0 and conv_yoy_pp<0 else "客流下降但成交率提升——进店质量在改善" if float(r7['10'])*100<0 and conv_yoy_pp>0 else "两项指标同步变化"}</div></div></div>
<div class="bl"><h3>品类：鞋同比{p(cat_data["鞋"]["yoy"])}</h3><div class="dl"><table class="tm"><tr><th>品类</th><th>流水</th><th>同比</th><th>环比</th><th>折扣</th><th>动销率</th></tr>{ct}</table><div class="hl"><b>鞋占比{pa(shoe_share,1)} | </b>鞋SKU动销率{pa(cat_data["鞋"]["sku_usage"])} | 配件每SKU产出{m(acc_per_sku)} vs 鞋{m(shoe_per_sku)}</div></div></div>
<div class="bl"><h3>客单价{m(avg_ticket)} | 连带{attach_rate:.2f}</h3><div class="dl">客单价{m(avg_ticket)}（同比{p(ticket_yoy)}），拆解：{m(unit_price)}×{attach_rate:.2f}≈{m(round(unit_price*attach_rate))}<br>折扣率{pa(discount)}，同比{p(discount_yoy)}pp，环比{p(discount_mom)}pp。</div></div></div>
<div><div class="ct"><span class="dot" style="width:8px;height:8px;border-radius:50%;display:inline-block;background:#2563eb;"></span> 本周重点改善策略</div>
<div class="bl">
<div class="si"><div class="st"><span class="sn s1">1</span>{worst_day["name"]}复苏攻坚</div><div class="sb"><b>执行人：</b>店长+全体导购　<b>时间：</b>{"周五下午~周日全天" if worst_day["name"]=="周六" else worst_day["name"]+"全天"}<br><b>动作：</b>1.提前推送专属券+短信触达；2."老带新"裂变；3.排班优化设PK奖。目标达成率从{pa(worst_day["achieve"],1)}→80%+</div></div>
<div class="si"><div class="st"><span class="sn s2">2</span>成交率抢救：{pa(conv_rate)}→{pa(min(conv_rate+4,30))}</div><div class="sb"><b>执行人：</b>全体导购　<b>时间：</b>全周<br><b>动作：</b>进店三句话+试穿有礼+加价购。周流水约增{m((conv_rate/100+0.04-conv_rate/100)*(daily_flow*7)*avg_ticket) if conv_rate>0 else m(0)}</div></div>
<div class="si"><div class="st"><span class="sn s3">3</span>SKU效率+爆款深耕</div><div class="sb"><b>执行人：</b>店长+商品专员　<b>时间：</b>周三前<br><b>动作：</b>清理0动销SKU+锁定爆款加深库存。</div></div>
<div class="si"><div class="st"><span class="sn s4">4</span>连带攻坚：{attach_rate:.2f}→{round(attach_rate+0.6,2)}</div><div class="sb"><b>执行人：</b>全体导购　<b>时间：</b>全周<br><b>动作：</b>"1+1+1"搭配+跨界连带+即时激励。</div></div>
<div class="si"><div class="st"><span class="sn s5">5</span>折扣管控+新品策略</div><div class="sb"><b>执行人：</b>店长　<b>时间：</b>周二前<br><b>动作：</b>新品首2周正价保护+满减免替代直降。目标折扣率{"控制在"+str(round(discount-2,1))+"%以内" if discount>40 else "保持"+str(round(discount,1))+"%左右"}</div></div>
</div></div></div><div class="fn">{period}周分析 & 改善策略 | {store} | AI店长分析</div></div></body></html>'''

# ──── REPORT 3 ────
def r3():
    txt = f'''{period}周报分析稿
店铺：{store}
周期：{period}
报告日期：动态生成

===============================
一、周分析
===============================

1、达成：本周目标{m(target)}，实际流水{m(actual)}，达成率{pa(achieve)}，{"超目标"+m(actual-target) if actual>=target else "缺口"+m(target-actual)}。同比{dw(yoy)}{p(yoy)}，同店同比{p(sssg)}，环比{p(mom)}。

2、成交率与客流：成交率{pa(conv_rate)}（同比{p(conv_yoy_pp)}pp），日均客流{daily_flow:.0f}人/天（同比{p(float(r7['10'])*100)}），周客单量{ticket_cnt:.0f}笔。{"客流增长但成交率下降" if float(r7['10'])*100>0 and conv_yoy_pp<0 else "客流下降但成交率提升" if float(r7['10'])*100<0 and conv_yoy_pp>0 else "两项指标同步变化"}。

3、客单价与连带：客单价{m(avg_ticket)}（同比{p(ticket_yoy)}），连带率{attach_rate:.2f}件（同比{p(attach_yoy)}），件单价{m(unit_price)}（同比{p(unit_yoy)}）。

4、鞋类：鞋流水{m(cat_data["鞋"]["flow"])}，占比{pa(shoe_share,1)}，同比{p(cat_data["鞋"]["yoy"])}、环比{p(cat_data["鞋"]["mom"])}。每SKU产出{m(shoe_per_sku)}。

5、品类：男装{m(cat_data["男装"]["flow"])}（同比{p(cat_data["男装"]["yoy"])}），女装{m(cat_data["女装"]["flow"])}（同比{p(cat_data["女装"]["yoy"])}），配件{m(cat_data["配件"]["flow"])}（同比{p(cat_data["配件"]["yoy"])}）。

6、日别结构：'''
    for d in daily_data:
        txt += f'{d["name"]}{m(d["flow"])}（达成{pa(d["achieve"],1)}，同比{p(d["yoy"],1)}）→ '
    txt = txt.rstrip('→ ')

    txt += f'''

7、折扣率：综合折扣率{pa(discount)}（同比{p(discount_yoy)}pp、环比{p(discount_mom)}pp），约{round((100-discount)/10,1)}折出售。

8、O2O：O2O流水{m(o2o)}（占比{pa(o2o_pct)}），PAD{m(pad)}，官网O2O{m(o2o_online)}。

===============================
二、本周重点改善策略
===============================

1、{worst_day["name"]}复苏：提前推送专属券+老带新裂变+排班优化，目标达成率从{pa(worst_day["achieve"],1)}提升至80%+。

2、成交率抢救（{pa(conv_rate)}→{pa(min(conv_rate+4,30))}）：进店三句话话术+试穿三件有礼+加价购，目标周流水约增{m((conv_rate/100+0.04-conv_rate/100)*(daily_flow*7)*avg_ticket) if conv_rate>0 else m(0)}。

3、SKU效率：清理0动销SKU，锁定爆款加深库存。

4、连带攻坚（{attach_rate:.2f}→{round(attach_rate+0.6,2)}）：1+1+1搭配法+跨界连带+即时激励。

5、折扣管控+新品正价保护：满减免替代直降，目标综合折扣率{"控制在"+str(round(discount-2,1))+"%以内" if discount>40 else "保持"+str(round(discount,1))+"%左右"}。

===============================
报告完毕 | {store} | {period}周分析
===============================
'''
    return txt

# ══════ WRITE ══════
with open(f'{_base}/{period}周报深度分析报告.html','w',encoding='utf-8') as f: f.write(r1())
print(f"Report 1: {period}周报深度分析报告.html")
with open(f'{_base}/{period}周分析_改善策略.html','w',encoding='utf-8') as f: f.write(r2())
print(f"Report 2: {period}周分析_改善策略.html")
with open(f'{_base}/{period}周报分析稿.txt','w',encoding='utf-8') as f: f.write(r3())
print(f"Report 3: {period}周报分析稿.txt")
print("\nAll reports generated successfully!")
