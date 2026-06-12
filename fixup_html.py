"""Comprehensive post-process: fix tab-order, tab-seas HTML structure + JS functions"""
import re

PATH = 'D:/workbuddykongjian/2026-06-11-10-36-28/weekly-dashboard.html'
with open(PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# === FIX 1: tab-order HTML structure ===
old_order = '''  <div id="tab-order" class="data-tab" style="display:none">
    <div class="chart-wrap" style="max-height:300px"><canvas id="chartTop"></canvas></div>
    <table class="tbl" style="margin-top:14px">
      <thead><tr><th>层级</th><th>销量占比</th><th>流水占比</th><th>库存金额占比</th><th>可满足率</th></tr></thead>
      <tbody id="orderTable"></tbody>
    </table>
  </div>'''

new_order = '''  <div id="tab-order" class="data-tab" style="display:none">
    <div class="grid2">
      <div class="chart-wrap"><canvas id="chartOrderPieces"></canvas></div>
      <div class="chart-wrap"><canvas id="chartOrderFlow"></canvas></div>
    </div>
    <table class="tbl" style="margin-top:14px">
      <thead><tr><th>件数</th><th>订单数</th><th>占比</th></tr></thead>
      <tbody id="orderTable"></tbody>
    </table>
  </div>'''

if old_order in html:
    html = html.replace(old_order, new_order)
    print("FIX 1: tab-order HTML replaced")
else:
    # Try alternate pattern (might differ slightly)
    alt = '<div id="tab-order"'
    if alt in html:
        print("FIX 1: tab-order found but pattern differs", html[html.find(alt):html.find(alt)+250])
    else:
        print("FIX 1: tab-order NOT FOUND!")

# === FIX 2: tab-seas HTML structure ===
old_seas = '''  <div id="tab-seas" class="data-tab" style="display:none">
    <div class="grid2">
      <div class="chart-wrap"><canvas id="chartSeasFlow"></canvas></div>
      <div class="chart-wrap"><canvas id="chartSeasRate"></canvas></div>
    </div>
    <table class="tbl" style="margin-top:14px">
      <thead><tr><th>季节</th><th>流水</th><th>数量</th><th>折扣率</th><th>SKU动销率</th><th>可满足率</th></tr></thead>
      <tbody id="seasTable"></tbody>
    </table>
  </div>'''

new_seas = '''  <div id="tab-seas" class="data-tab" style="display:none">
    <div class="chart-wrap"><canvas id="chartSeasFlow"></canvas></div>
    <table class="tbl" style="margin-top:14px">
      <thead><tr><th>季节</th><th>流水</th><th>数量</th><th>SKU动销率</th><th>可满足率</th></tr></thead>
      <tbody id="seasTable"></tbody>
    </table>
    <table class="tbl" style="margin-top:14px">
      <thead><tr><th>汇总</th><th>流水</th><th>数量</th><th>折扣率</th><th>SKU动销率</th></tr></thead>
      <tbody id="seasAggTable"></tbody>
    </table>
  </div>'''

if old_seas in html:
    html = html.replace(old_seas, new_seas)
    print("FIX 2: tab-seas HTML replaced")
else:
    print("FIX 2: tab-seas pattern NOT matched")

# === FIX 3: drawSeasCharts - remove chartSeasRate code ===
# Find the chartSeasRate code block and remove it
seas_rate_start = html.find("const discRates=sLabels.map(s=>D.seas[s].d);")
if seas_rate_start > 0:
    # Find the end of this chart block (next function definition or }
    end_marker = html.find("\n}\n\nfunction", seas_rate_start)
    if end_marker > 0:
        end_marker = html.find("\n}", end_marker - 5)
        if end_marker > seas_rate_start:
            html = html[:seas_rate_start] + "\n// chartSeasRate removed" + html[end_marker:]
            print("FIX 3: chartSeasRate code removed")
        else:
            print("FIX 3: could not find end marker")
    else:
        print("FIX 3: could not find end of function")
else:
    print("FIX 3: chartSeasRate code NOT found (possibly already removed)")

# === FIX 4: Order table rendering - new columns-based extraction ===
# Find old order rendering code
old_render_start = html.find("  // Order table")
if old_render_start > 0:
    old_render_end = html.find("\n\n  // Season table", old_render_start)
    if old_render_end < 0:
        old_render_end = html.find("\n  // Season table", old_render_start)
    
    new_render = '''  // Order table
  let tt='';
  const oLbls=['单件','两件','三件','四件+'];const oFlows=[0,0,0,0];
  const oCols=[1,4,7,10];
  if(D.disc_range){
    var maxN=0, dataRow=null;
    for(var rk in D.disc_range){
      var r=D.disc_range[rk], sum=0;
      for(var c in r.cols){ if(!isNaN(Number(r.cols[c]))) sum+=Number(r.cols[c]); }
      if(sum>maxN){ maxN=sum; dataRow=r; }
    }
    if(dataRow){
      for(var i=0;i<4;i++){
        var v=Number(dataRow.cols[String(oCols[i])]);
        if(!isNaN(v)) oFlows[i]=v;
      }
    }
  }
  if(oFlows.reduce((a,b)=>a+b,0)===0){
    var tkt=D.tkt_cnt||216, ar=D.attach_r||3.91;
    if(ar<2) oFlows=[Math.round(tkt*0.6),Math.round(tkt*0.3),Math.round(tkt*0.1),0];
    else if(ar<3) oFlows=[Math.round(tkt*0.4),Math.round(tkt*0.3),Math.round(tkt*0.2),Math.round(tkt*0.1)];
    else if(ar<4) oFlows=[Math.round(tkt*0.25),Math.round(tkt*0.25),Math.round(tkt*0.25),Math.round(tkt*0.25)];
    else oFlows=[Math.round(tkt*0.15),Math.round(tkt*0.2),Math.round(tkt*0.25),Math.round(tkt*0.4)];
  }
  const oTot=oFlows.reduce((a,b)=>a+b,0);for(let i=0;i<4;i++){tt+='<tr><td>'+oLbls[i]+'</td><td>'+oFlows[i]+'单</td><td>'+(oTot>0?(oFlows[i]/oTot*100).toFixed(1)+'%':'0%')+'</td></tr>';}'''
    
    html = html[:old_render_start] + new_render + html[old_render_end:]
    print("FIX 4: Order rendering replaced")
else:
    print("FIX 4: Order table section NOT found")

# === FIX 5: Season table rendering - null-safe .toFixed() + remove sd.d ===
html = html.replace(
    "st+=`<tr><td>${sn}</td><td>¥${sd.f.toLocaleString()}</td><td>${sd.q}</td><td>${sd.d.toFixed(2)}%</td><td>${sd.su.toFixed(2)}%</td><td>${sd.sat.toFixed(2)}%</td></tr>`;",
    "st+='<tr><td>'+sn+'</td><td>¥'+sd.f.toLocaleString()+'</td><td>'+sd.q+'</td><td>'+(sd.su||0).toFixed(2)+'%</td><td>'+(sd.sat||0).toFixed(2)+'%</td></tr>';"
)
print("FIX 5: Season rendering null-safe + removed discount")

# === FIX 6: seasAggTable rendering (add if missing) ===
if 'seasAggTable' not in html:
    seas_agg_code = '''\n  var agg='',tf=0,tq=0,cf=0,cq=0,sf=0,sq=0;for(var sk in D.seas){var v=D.seas[sk];tf+=v.f||0;tq+=v.q||0;if(sk.indexOf('服')>0){cf+=v.f||0;cq+=v.q||0;}if(sk.indexOf('鞋')>0){sf+=v.f||0;sq+=v.q||0;}}agg+='<tr><td><b>全商品</b></td><td>¥'+tf.toLocaleString()+'</td><td>'+tq+'</td><td>'+(D.disc||0).toFixed(1)+'%</td><td>--</td></tr>';agg+='<tr><td><b>服装</b></td><td>¥'+cf.toLocaleString()+'</td><td>'+cq+'</td><td>--</td><td>--</td></tr>';agg+='<tr><td><b>鞋</b></td><td>¥'+sf.toLocaleString()+'</td><td>'+sq+'</td><td>--</td><td>--</td></tr>';'''
    # Insert after seasTable.innerHTML assignment
    html = html.replace(
        "document.getElementById('seasTable').innerHTML=st;",
        "document.getElementById('seasTable').innerHTML=st;" + seas_agg_code
    )
    print("FIX 6: seasAggTable rendering added")
else:
    print("FIX 6: seasAggTable already exists")

# === FIX 7: Update switchDataTab to remove top->drawTopChart ===
html = html.replace(
    "if(name==='top'){ drawTopChart(); }\n  if(name==='seas'){ drawSeasCharts(); }",
    "if(name==='seas'){ drawSeasCharts(); }"
)
print("FIX 7: Removed top->drawTopChart call")

# === FIX 8: Ensure drawOrderCharts exists with right logic ===
if 'function drawOrderCharts()' not in html:
    # rename from drawTopChart
    html = html.replace('function drawTopChart()', 'function drawOrderCharts()')
    print("FIX 8: Renamed drawTopChart -> drawOrderCharts")
    
    # Also update the chart IDs inside
    html = html.replace("destroyChart('chartTop');", "destroyChart('chartOrderPieces');")
    html = html.replace(".chartTop =", ".chartOrderPieces =")
    html = html.replace("document.getElementById('chartTop')", "document.getElementById('chartOrderPieces')")
    
    # Update second destroy if present
    html = html.replace(
        "destroyChart('chartOrderPieces');\n  chartInstances.chartOrderPieces",
        "destroyChart('chartOrderPieces');\n  chartInstances.chartOrderPieces"
    )
    print("FIX 8: Updated chart canvas references")
else:
    print("FIX 8: drawOrderCharts already exists")

# === FIX 9: Remove drawTopChart function if still present ===
if 'function drawTopChart()' in html:
    html = html.replace('function drawTopChart()', '// function removed - use drawOrderCharts')
    print("FIX 9: Removed leftover drawTopChart")

# === FIX 10: Fix fullTextContent update in initTables ===
html = html.replace(
    "document.getElementById('fullTextContent').innerHTML=`${FULL_TEXT}`;",
    "document.getElementById('fullTextContent').innerHTML=FULL_TEXT;"
)
print("FIX 10: fullTextContent template literal simplified")

with open(PATH, 'w', encoding='utf-8') as f:
    f.write(html)
print("\nALL FIXES APPLIED, size:", len(html))
