// DeepSeek AI 实时分析 - 独立JS文件，避免f-string转义问题
// 通过本地代理服务器调用API，避免浏览器CORS/网络限制
const DEEPSEEK_MODEL = 'deepseek-v4-flash';

function callDeepSeek(prompt, callback) {
  fetch('/api/deepseek', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: DEEPSEEK_MODEL,
      messages: [
        { role: 'system', content: '你是一个零售数据分析专家，用专业简洁的中文分析门店数据。' },
        { role: 'user', content: prompt }
      ],
      temperature: 0.7,
      max_tokens: 2048
    })
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    if (d.choices && d.choices[0]) callback(d.choices[0].message.content);
    else callback(null, 'API返回异常: ' + JSON.stringify(d));
  })
  .catch(function(e) { callback(null, '网络错误: ' + e.message); });
}

function renderAnalysis(el) {
  var btn = el || document.querySelector('button[onclick*="renderAnalysis"]');
  if (btn) { btn.classList.add('loading'); btn.disabled = true; }
  showToast('🔄 AI正在深度分析...', 'info');
  var D = DATA;
  var p = '你是一个零售数据分析专家。请根据以下奥莱门店的完整数据，按照指定模板生成周报分析。\n\n';
  p += '【门店信息】\n';
  p += '店铺：' + D.store + ' | 周期：' + D.period + '（' + D.week_range + '）\n';
  p += '本周目标：¥' + (D.target / 10000).toFixed(1) + '万\n';
  p += '本周实际：¥' + (D.actual / 10000).toFixed(1) + '万\n';
  p += '达成率：' + D.achieve.toFixed(1) + '%\n';
  p += '同比：' + (D.yoy > 0 ? '+' : '') + D.yoy.toFixed(1) + '%\n';
  p += '环比：' + (D.mom > 0 ? '+' : '') + D.mom.toFixed(1) + '%\n';
  p += '\n【运营指标】\n';
  p += '成交率：' + D.conv.toFixed(1) + '%（同比' + (D.conv_yoy > 0 ? '+' : '') + D.conv_yoy.toFixed(1) + 'pp）\n';
  p += '日均客流：' + D.flow.toFixed(0) + '人（同比' + (D.flow_yoy > 0 ? '+' : '') + D.flow_yoy.toFixed(1) + '%）\n';
  p += '周客单量：' + D.tkt_cnt.toFixed(0) + '笔\n';
  p += '客单价：¥' + D.avg_t.toFixed(0) + '（同比' + (D.avg_t_yoy > 0 ? '+' : '') + D.avg_t_yoy.toFixed(1) + '%）\n';
  p += '连带率：' + D.attach_r.toFixed(2) + '件（同比' + (D.attach_yoy > 0 ? '+' : '') + D.attach_yoy.toFixed(1) + '%）\n';
  p += '件单价：¥' + D.unit_p.toFixed(0) + '（同比' + (D.unit_yoy > 0 ? '+' : '') + D.unit_yoy.toFixed(1) + '%）\n';
  p += '折扣率：' + D.disc.toFixed(1) + '%（同比' + (D.disc_yoy_p > 0 ? '+' : '') + D.disc_yoy_p.toFixed(1) + 'pp）\n';
  p += 'SSSG(同店同比)：' + (D.sssg > 0 ? '+' : '') + D.sssg.toFixed(1) + '%\n';
  p += 'O2O流水：¥' + (D.o2o / 10000).toFixed(2) + '万（占比' + (D.o2o_pct ? D.o2o_pct.toFixed(1) : '0') + '%，环比' + (D.o2o_mom > 0 ? '+' : '') + D.o2o_mom.toFixed(1) + '%）\n';
  p += '\n【品类数据】\n';
  var cats = D.category;
  if (cats) {
    var cnames = Object.keys(cats);
    for (var i = 0; i < cnames.length; i++) {
      var c = cats[cnames[i]], cn = cnames[i];
      p += cn + '：流水¥' + (c.flow / 10000).toFixed(1) + '万 | 占比' + (c.f_share ? c.f_share.toFixed(1) : '0') + '% | 同比' + (c.yoy > 0 ? '+' : '') + (c.yoy ? c.yoy.toFixed(1) : '0') + '% | 折扣' + (c.disc ? c.disc.toFixed(1) : '0') + '%\n';
      if (c.group === 'product') {
        p += '  SKU在售：' + c.sku_s + ' | 库存：' + (c.s_qty ? c.s_qty : '0') + ' | 动销率：' + (c.sku_u ? c.sku_u.toFixed(1) : '0') + '% | 匹配：' + (c.match_lbl || '') + '\n';
      }
    }
  }
  p += '\n【日别数据】\n';
  var days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  for (var i = 0; i < 7 && i < D.daily.length; i++) {
    var d = D.daily[i];
    p += days[i] + '：流水¥' + (d.f / 10000).toFixed(1) + '万 | 达成' + d.a.toFixed(1) + '% | 同比' + (d.y > 0 ? '+' : '') + d.y.toFixed(1) + '% | 客流' + d.v + '人 | 客单价¥' + d.tk.toFixed(0) + ' | 连带率' + d.at.toFixed(2) + '\n';
  }
  p += '\n【新品季节数据】\n';
  var seas = D.seas;
  if (seas) {
    for (var sk in seas) {
      var s = seas[sk];
      p += sk + '：流水¥' + (s.f / 10000).toFixed(1) + '万 | 折扣' + s.d.toFixed(1) + '% | SKU' + s.sku + '个 | 库存' + s.stock_qty + '件 | 动销率' + s.su.toFixed(1) + '%\n';
    }
  }
  p += '\n【中类汇总】\n';
  var ma = D.mid_agg;
  if (ma) {
    p += '男服：流水¥' + (ma['男服'] ? (ma['男服'].f / 10000).toFixed(1) : '0') + '万 | SKU' + (ma['男服'] ? ma['男服'].sku : '0') + ' | 库存' + (ma['男服'] ? ma['男服'].stock_qty : '0') + '\n';
    p += '女服：流水¥' + (ma['女服'] ? (ma['女服'].f / 10000).toFixed(1) : '0') + '万 | SKU' + (ma['女服'] ? ma['女服'].sku : '0') + ' | 库存' + (ma['女服'] ? ma['女服'].stock_qty : '0') + '\n';
    p += '男鞋：流水¥' + (ma['男鞋'] ? (ma['男鞋'].f / 10000).toFixed(1) : '0') + '万 | SKU' + (ma['男鞋'] ? ma['男鞋'].sku : '0') + ' | 库存' + (ma['男鞋'] ? ma['男鞋'].stock_qty : '0') + '\n';
    p += '女鞋：流水¥' + (ma['女鞋'] ? (ma['女鞋'].f / 10000).toFixed(1) : '0') + '万 | SKU' + (ma['女鞋'] ? ma['女鞋'].sku : '0') + ' | 库存' + (ma['女鞋'] ? ma['女鞋'].stock_qty : '0') + '\n';
  }
  p += '\n【衍生指标】\n';
  var wi = 0, bi = 0;
  for (var i = 0; i < 7 && i < D.daily.length; i++) {
    if (D.daily[i].a < D.daily[wi].a) wi = i;
    if (D.daily[i].a > D.daily[bi].a) bi = i;
  }
  p += '达成最低日：' + D.daily[wi].n + '（' + D.daily[wi].a.toFixed(1) + '%）\n';
  p += '达成最高日：' + D.daily[bi].n + '（' + D.daily[bi].a.toFixed(1) + '%）\n';
  p += '客流+成交率双降：' + (D.flow_yoy > 0 && D.conv_yoy < 0 ? '是' : '否') + '\n';
  p += '折扣螺旋：' + (D.disc > 40 && D.mom < -10 ? '是' : '否') + '\n';
  p += '\n========================================\n';
  p += '请严格按照以下模板格式输出分析报告，用自然语言填充内容，不要输出Markdown格式，用【】标记段落标题：\n\n';
  p += '1、【达成分析】分析本周目标达成情况，说明达成率高低的原因（结合客流、客单、品类结构），判断增长质量。\n\n';
  p += '2、【转化分析】分析成交率与客流的组合关系，判断是"进店不买"还是"不来人"问题。\n\n';
  p += '3、【客单分析】分析客单价、连带率、件单价的变化趋势，判断驱动客单价的核心因素。\n\n';
  p += '4、【品类分析】分析鞋、服、配三大品类的表现，重点说明鞋类SKU效率问题和库存匹配情况。\n\n';
  p += '5、【服装性别分析】按男、女、童分析服装销售结构，说明性别维度的差异。\n\n';
  p += '6、【日别结构】分析一周的销售节奏，找出最差日和最佳日的特征，说明周末vs工作日的差异。\n\n';
  p += '7、【折扣分析】分析折扣率趋势和合理性，判断是否存在"越打折越卖不动"的风险。\n\n';
  p += '8、【改善建议】基于以上分析，给出3条具体可执行的改善建议，每条需包含具体目标和执行动作。\n\n';
  p += '请用专业客观的语言，直接分析数据，不要评价数据本身的好坏。每条分析控制在100-150字。';

  callDeepSeek(p, function(result, err) {
    if (err) {
      var idx = Math.floor(Math.random() * FULL_TEXTS.length);
      document.getElementById('fullTextContent').innerHTML =
        '<div style="color:#94a3b8;font-size:12px;margin-bottom:8px">⚠️ AI离线，使用预制分析</div>' + FULL_TEXTS[idx];
      showToast('⚠️ AI离线', 'info');
    } else {
      var html = result.replace(/\n/g, '<br>').replace(/【([^】]+)】/g, '<br><br><b>【$1】</b>');
      document.getElementById('fullTextContent').innerHTML =
        '<div style="font-size:12px;color:#6366f1;margin-bottom:8px">🤖 DeepSeek AI 实时生成</div>' + html;
      showToast('✅ AI分析完成', 'success');
    }
    if (btn) { btn.classList.remove('loading'); btn.disabled = false; }
  });
}
