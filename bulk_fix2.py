import re

PATH = 'D:/workbuddykongjian/2026-06-11-10-36-28/weekly-dashboard.html'
with open(PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# === 2: Replace TOP tab content with Order Distribution ===
# Remove chart canvases from tab-top, replace with order table
html = html.replace(
    '<div id="tab-top" class="data-tab" style="display:none">',
    '<div id="tab-order" class="data-tab" style="display:none">')

# Replace the grid2 chart section with a single order chart
html = html.replace(
    '<div class="grid2">\n      <div class="chart-wrap"><canvas id="chartOrderPieces"></canvas></div>\n      <div class="chart-wrap"><canvas id="chartOrderFlow"></canvas></div>\n    </div>',
    '<div class="grid2">\n      <div class="chart-wrap"><canvas id="chartOrderPieces"></canvas></div>\n      <div class="chart-wrap"><canvas id="chartOrderFlow"></canvas></div>\n    </div>')

# The chart IDs are already renamed. Now rewrite the drawOrderCharts function content
# Replace the old drawTopChart body with order chart logic
old_draw_top = '''function drawOrderCharts(){
  const D=DATA;
  const colors={blue:'#3b82f6',blueBg:'#dbeafe',green:'#22c55e',greenBg:'#dcfce7',red:'#ef4444',redBg:'#fecaca',amber:'#f59e0b',purple:'#8b5cf6',orange:'#f97316'};
  const tks=Object.keys(D.top);
  const fShares=tks.map(k=>D.top[k]['4']);
  const vShares=tks.map(k=>D.top[k]['6']);'''
new_draw_order = '''function drawOrderCharts(){
  const D=DATA;
  const colors={blue:'#3b82f6',blueBg:'#dbeafe',green:'#22c55e',greenBg:'#dcfce7',red:'#ef4444',redBg:'#fecaca',amber:'#f59e0b',purple:'#8b5cf6',orange:'#f97316'};
  // Order distribution - use disc_range data or fallback
  const orderLabels=['单件','两件','三件','四件+'];
  const orderFlows=[0,0,0,0];
  if(D.disc_range){
    const dr=D.disc_range;
    for(let k in dr){
      const row=dr[k]; const lbl=row.label||'';
      if(lbl.includes('单件')) orderFlows[0]=(row.cols['4']||0)+(row.cols['5']||0);
      if(lbl.includes('两件')) orderFlows[1]=(row.cols['4']||0)+(row.cols['5']||0);
      if(lbl.includes('三件')) orderFlows[2]=(row.cols['4']||0)+(row.cols['5']||0);
      if(lbl.includes('四件')) orderFlows[3]=(row.cols['4']||0)+(row.cols['5']||0);
    }
  }'''

html = html.replace(old_draw_top, new_draw_order)

# Replace the old chart drawing with order chart
old_chart_render = '''  destroyChart('chartOrderPieces');
  chartInstances.chartOrderPieces = new Chart(document.getElementById('chartOrderPieces'),{
    type:'bar', data:{ labels:tks, datasets:[
      { label:'流水占比', data:fShares, backgroundColor:colors.blueBg, borderColor:colors.blue, borderWidth:1.5, borderRadius:4 }
    ]},
    options:{ responsive:true, maintainAspectRatio:false,
      plugins:{ title:{display:true,text:'TOP商品集中度',font:{size:14}} },
      scales:{ y:{ ticks:{ callback:v=>v.toFixed(0)+'%'},max:110 } }
    }
  });

  destroyChart('chartOrderFlow');
  chartInstances.chartOrderFlow = new Chart(document.getElementById('chartOrderFlow'),{
    type:'bar', data:{ labels:tks, datasets:[
      { label:'流水占比', data:fShares, backgroundColor:colors.blueBg, borderColor:colors.blue, borderWidth:1.5, borderRadius:4 },
      { label:'销量占比', data:vShares, backgroundColor:colors.greenBg, borderColor:colors.green, borderWidth:1.5, borderRadius:4 }
    ]},
    options:{ responsive:true, maintainAspectRatio:false,
      plugins:{ title:{display:true,text:'TOP商品集中度',font:{size:14}}, legend:{position:'bottom'} },
      scales:{ y:{ ticks:{ callback:v=>v.toFixed(0)+'%'},max:110 } }
    }
  });
}'''

new_chart_render = '''  destroyChart('chartOrderPieces');
  chartInstances.chartOrderPieces = new Chart(document.getElementById('chartOrderPieces'),{
    type:'bar', data:{ labels:orderLabels, datasets:[
      { label:'订单量', data:orderFlows, backgroundColor:[colors.blueBg,colors.greenBg,colors.amber+'40',colors.redBg], borderColor:[colors.blue,colors.green,colors.amber,colors.red], borderWidth:1.5, borderRadius:4 }
    ]},
    options:{ responsive:true, maintainAspectRatio:false,
      plugins:{ title:{display:true,text:'订单件数分布',font:{size:14}} },
      scales:{ y:{ ticks:{ callback:v=>v.toFixed(0)+'单'} } }
    }
  });

  // Pie chart for order share
  const totalOrders=orderFlows.reduce((a,b)=>a+b,0);
  const orderShares=totalOrders>0?orderFlows.map(v=>(v/totalOrders*100)):[0,0,0,0];
  destroyChart('chartOrderFlow');
  chartInstances.chartOrderFlow = new Chart(document.getElementById('chartOrderFlow'),{
    type:'doughnut', data:{ labels:orderLabels, datasets:[
      { label:'占比%', data:orderShares, backgroundColor:[colors.blueBg,colors.greenBg,colors.amber+'40',colors.redBg], borderColor:[colors.blue,colors.green,colors.amber,colors.red], borderWidth:1 }
    ]},
    options:{ responsive:true, maintainAspectRatio:false,
      plugins:{ title:{display:true,text:'订单件数占比',font:{size:14}}, legend:{position:'bottom'} }
    }
  });
}'''

html = html.replace(old_chart_render, new_chart_render)

# Update the order table rendering in initTables
html = html.replace(
    "// TOP table\n  let tt='';",
    "// Order table\n  let tt='';")
html = html.replace(
    "for(const[tn,td]of Object.entries(D.top))",
    "// Order distribution from disc_range\n  const orderLabels=['单件','两件','三件','四件+'];\n  const orderFlows=[0,0,0,0];\n  if(D.disc_range){for(let k in D.disc_range){const r=D.disc_range[k];const l=r.label||'';if(l.includes('单件'))orderFlows[0]=(r.cols['4']||0)+(r.cols['5']||0);if(l.includes('两件'))orderFlows[1]=(r.cols['4']||0)+(r.cols['5']||0);if(l.includes('三件'))orderFlows[2]=(r.cols['4']||0)+(r.cols['5']||0);if(l.includes('四件'))orderFlows[3]=(r.cols['4']||0)+(r.cols['5']||0);}}\n  const ototal=orderFlows.reduce((a,b)=>a+b,0);\n  for(let i=0;i<4;i++){tt+='<tr><td>'+orderLabels[i]+'</td><td>'+(ototal>0?(orderFlows[i]/ototal*100).toFixed(1)+'%':'0%')+'</td><td>'+orderFlows[i]+'单</td></tr>';}")
html = html.replace(
    "tt+=`<tr><td>${tn}</td><td>${td['4'].toFixed(2)}%</td><td>${td['6'].toFixed(2)}%</td><td>${td['8'].toFixed(2)}%</td><td>${td['10'].toFixed(2)}%</td></tr>`;",
    "// replaced")
html = html.replace(
    "document.getElementById('orderTable').innerHTML=tt;",
    "document.getElementById('orderTable').innerHTML=tt;")
# Fix the table header
html = html.replace(
    "<thead><tr><th>层级</th><th>流水占比</th><th>SKU数占比</th></tr></thead>\n      <tbody id=\"orderTable\"></tbody>",
    "<thead><tr><th>订单件数</th><th>占比</th><th>订单量</th></tr></thead>\n      <tbody id=\"orderTable\"></tbody>")

print("2. Order distribution done")

# === 3: 新品季节 - add aggregate + remove discount chart ===
# After drawing seas flow chart, add totals computation. Find the seas chart section.

# === 4: 子品类按流水倒序 ===
# Find initTables sub_ps rendering and add sort
html = html.replace(
    "D.sub_ps.filter(r=>!r.isAcc).forEach",
    "D.sub_ps.filter(r=>!r.isAcc).sort((a,b)=>b.f-a.f).forEach")
html = html.replace(
    "D.sub_ps.filter(r=>r.isAcc).forEach",
    "D.sub_ps.filter(r=>r.isAcc).sort((a,b)=>b.f-a.f).forEach")
# Also sort shoe series
html = html.replace(
    "D.shoe.forEach",
    "D.shoe.sort((a,b)=>b.f-a.f).forEach")

print("4. Sub_ps sorted descending")

# === 5: 对标分析 - remove MTD/YTD, only week vs region ===
html = html.replace(
    "<thead><tr><th>指标</th><th>本周</th><th>月累计(06月)</th><th>vs本周</th><th>年累计(YTD)</th><th>vs本周</th><th>区域均值(19店)</th><th>vs本周</th></tr></thead>",
    "<thead><tr><th>指标</th><th>本周</th><th>区域均值(19店)</th><th>vs本周</th></tr></thead>")

# Simplify bench rendering to only compare week vs region
old_bench_render = '''  var bt='';
  var kmap=[{k:'conv','n':'成交率','pct':1},{k:'flow','n':'日均客流'},{k:'target','n':'流水目标'},{k:'actual','n':'流水实际'},{k:'achieve','n':'达成率','pct':1},{k:'sssg','n':'同比%','pct':1},{k:'mom','n':'环比%','pct':1}];
  kmap.forEach(function(item){
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
  });'''

new_bench_render = '''  var bt='';
  var kmap=[{k:'conv','n':'成交率','pct':1},{k:'flow','n':'日均客流'},{k:'target','n':'流水目标'},{k:'actual','n':'流水实际'},{k:'achieve','n':'达成率','pct':1},{k:'sssg','n':'同比%','pct':1},{k:'mom','n':'环比%','pct':1}];
  kmap.forEach(function(item){
    var w=D[item.k]!=null?D[item.k]:0;
    var r=D.reg&&D.reg[item.k]!=null?D.reg[item.k]:0;
    var fw=item.pct?w.toFixed(1)+'%':(w>=10000?'¥'+w.toLocaleString():'¥'+w.toFixed(0));
    var fr=item.pct?r.toFixed(1)+'%':(r>=10000?'¥'+r.toLocaleString():'¥'+r.toFixed(0));
    var dr=item.pct?(r-w).toFixed(1)+'pp':((r-w)>=0?'+':'')+(r-w).toFixed(0);
    bt+='<tr><td>'+item.n+'</td><td>'+fw+'</td><td>'+fr+'</td><td>'+dr+'</td></tr>';
  });'''

html = html.replace(old_bench_render, new_bench_render)

# Fix colspan from 8 to 4
html = html.replace("colspan=\"8\"\u003e导入后解析", "colspan=\"4\"\u003e导入后解析")

print("5. Bench simplified to week vs region")

# === Also need to fix the seas tab to add aggregates ===
# Find chartSeasRate and replace with aggregate table
# The seas chart section has two charts. Keep chartSeasFlow, remove chartSeasRate.
seas_rate_html = '''  <div class="chart-wrap"><canvas id="chartSeasRate"></canvas></div>'''
seas_agg_html = '''  <table class="tbl" style="margin-top:14px">
      <thead><tr><th>汇总</th><th>流水</th><th>数量</th><th>折扣率</th><th>SKU动销率</th></tr></thead>
      <tbody id="seasAggTable"></tbody>
    </table>'''
html = html.replace(seas_rate_html, seas_agg_html)

# Remove chartSeasRate drawing
html = re.sub(
    r"destroyChart\('chartSeasRate'\)[\s\S]*?\);\n  }",
    "// chartSeasRate removed; }\n  }",
    html)
# Cleaner approach: just remove the whole chartSeasRate block
# Let me find and remove it more precisely
html = re.sub(
    r"\n\n  destroyChart\('chartSeasRate'\);\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n  \}\);",
    "",
    html)

# Add seas aggregate rendering
html = html.replace(
    "document.getElementById('seasTable').innerHTML=st;",
    "document.getElementById('seasTable').innerHTML=st;\n  // Season aggregates\n  var agg='',totFlow=0,totQty=0,totSu=0,clothFlow=0,clothQty=0,shoeFlow=0,shoeQty=0;\n  for(var sk in D.seas){var d=D.seas[sk];totFlow+=d.f||0;totQty+=d.q||0;totSu=(totSu&&d.su||totSu);if(sk.includes('服')){clothFlow+=d.f||0;clothQty+=d.q||0;}if(sk.includes('鞋')){shoeFlow+=d.f||0;shoeQty+=d.q||0;}}\n  var catAgg=D.category;var shoeAgg=catAgg['鞋'];var clothAgg=[catAgg['男装'],catAgg['女装']];var clothTFlow=(clothAgg[0]?clothAgg[0].flow:0)+(clothAgg[1]?clothAgg[1].flow:0);\n  agg+='<tr><td><b>全商品</b></td><td>¥'+totFlow.toLocaleString()+'</td><td>'+totQty+'</td><td>'+(D.disc||0).toFixed(1)+'%</td><td>--</td></tr>';\n  agg+='<tr><td><b>服装</b></td><td>¥'+clothFlow.toLocaleString()+'</td><td>'+clothQty+'</td><td>--</td><td>--</td></tr>';\n  agg+='<tr><td><b>鞋</b></td><td>¥'+shoeFlow.toLocaleString()+'</td><td>'+shoeQty+'</td><td>--</td><td>--</td></tr>';\n  document.getElementById('seasAggTable').innerHTML=agg;")

print("3. Season aggregate added, discount chart removed")

with open(PATH, 'w', encoding='utf-8') as f:
    f.write(html)
print("ALL DONE, size:", len(html))
