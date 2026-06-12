import re

PATH = 'D:/workbuddykongjian/2026-06-11-10-36-28/weekly-dashboard.html'
with open(PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# === 1: Tab buttons -- onclick uses 'this', functions use 'el' directly ===
html = html.replace("switchDataTab('daily',event)", "switchDataTab('daily',this)")
html = html.replace("switchDataTab('matrix',event)", "switchDataTab('matrix',this)")
html = html.replace("switchDataTab('cate',event)", "switchDataTab('cate',this)")
html = html.replace("switchDataTab('seas',event)", "switchDataTab('seas',this)")
html = html.replace("switchDataTab('sub',event)", "switchDataTab('sub',this)")
html = html.replace("switchDataTab('bench',event)", "switchDataTab('bench',this)")
html = html.replace("switchAnalysisTab('problems',event)", "switchAnalysisTab('problems',this)")
html = html.replace("switchAnalysisTab('opps',event)", "switchAnalysisTab('opps',this)")
html = html.replace("switchAnalysisTab('fulltext',event)", "switchAnalysisTab('fulltext',this)")

# Fix switchDataTab function
html = html.replace(
    'function switchDataTab(name,ev) {ev=ev||window.event;',
    'function switchDataTab(name,el) {')
html = html.replace(
    "  if(ev&&ev.target)ev.target.classList.add('active');\n  if(name==='daily')",
    "  if(el)el.classList.add('active');\n  if(name==='daily')")
html = html.replace(
    "  if(name==='seas'){ drawSeasCharts(); }\n}",
    "  if(name==='seas'){ drawSeasCharts(); }\n  if(name==='order'){ drawOrderCharts(); }\n}")

# Fix switchAnalysisTab function
html = html.replace(
    'function switchAnalysisTab(name,ev) {ev=ev||window.event;',
    'function switchAnalysisTab(name,el) {')
html = html.replace(
    "if(ev&&ev.target)ev.target.classList.add('active');\n}",
    "if(el)el.classList.add('active');\n}")

print("1. Tab buttons fixed")

# === 2: TOP集中度 -> 订单件数分布 (rename button + replace tab-top content + rename in JS) ===
html = html.replace(
    "onclick=\"switchDataTab('top')\">TOP集中度",
    "onclick=\"switchDataTab('order',this)\">订单分布")

# Replace tab-top div content (the charts + table)
html = html.replace('id="chartTopCon"', 'id="chartOrderPieces"')
html = html.replace('id="chartTopFlow"', 'id="chartOrderFlow"')
html = html.replace('id="topTable"', 'id="orderTable"')

# Replace TOP section header in the tab-top
html = html.replace(
    '<h4 style="font-size:13px;margin-bottom:8px;color:var(--sub)">TOP商品集中度</h4>',
    '')

# Now rewrite drawTopChart to drawOrderCharts and rename initTables TOP section
# Replace drawTopChart function call
html = html.replace('function drawTopChart()', 'function drawOrderCharts()')
html = html.replace('if(name===\'top\'){ drawTopChart(); }', 'if(name===\'order\'){ drawOrderCharts(); }')
html = html.replace('if(activeTab&&activeTab.id===\'tab-top\')drawTopChart();', 'if(activeTab&&activeTab.id===\'tab-order\')drawOrderCharts();')

print("2. TOP -> Order distribution renamed")

with open(PATH, 'w', encoding='utf-8') as f:
    f.write(html)
print("Done, size:", len(html))
