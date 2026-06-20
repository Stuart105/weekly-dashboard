// DeepSeek AI 实时分析 v2 — 人货场框架 + 大厂级分析深度
const DEEPSEEK_MODEL = 'deepseek-v4-pro';
// Worker 代理地址（部署 Cloudflare Worker 后替换）
const API_PROXY = 'https://YOUR_WORKER.workers.dev';
const SYSTEM_PROMPT = '你是一个在中国奥特莱斯零售行业有10年经验的门店运营专家。你精通：门店KPI诊断、品类管理、库存优化、导购绩效提升、折扣策略制定。分析时请遵循"人-货-场"三维框架：人（客流转化漏斗、人员效率）、货（品类健康度、SKU效率、新品表现、库存匹配）、场（日别节奏、折扣环境、对标差距）。请用专业但易懂的中文写作，直接给出数据和判断，不写客套话。每条分析控制在80-150字，必须包含具体数字支撑而非模糊描述。改善建议必须包含量化目标和可执行动作。';

function callDeepSeek(prompt, callback) {
  fetch(API_PROXY, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: DEEPSEEK_MODEL,
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: prompt }
      ],
      temperature: 0.6,
      max_tokens: 8192
    })
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    if (d.choices && d.choices[0]) {
      var msg = d.choices[0].message;
      var content = msg.content || '';
      // If content is empty but reasoning is available, use reasoning as fallback
      if (!content && msg.reasoning_content) {
        content = msg.reasoning_content;
      }
      callback(content || null, content ? null : 'API返回空内容');
    } else {
      callback(null, 'API返回异常: ' + JSON.stringify(d));
    }
  })
  .catch(function(e) { callback(null, '网络错误: ' + e.message); });
}

function renderAnalysis(el) {
  var btn = el || document.querySelector('button[onclick*="renderAnalysis"]');
  if (btn) { btn.classList.add('loading'); btn.disabled = true; }
  showToast('AI正在深度分析...', 'info');
  var D = DATA;
  var p = '';

  // ═══════════════════════════════════════════
  // 1. 门店概览
  // ═══════════════════════════════════════════
  p += '═══ 门店概览 ═══\n';
  p += D.store + ' | ' + D.period + ' | ' + D.week_range + '\n';
  p += '目标：¥' + (D.target / 10000).toFixed(1) + '万 → 实际：¥' + (D.actual / 10000).toFixed(1) + '万 → 达成：' + D.achieve.toFixed(1) + '%\n';
  p += '同比：' + (D.yoy > 0 ? '+' : '') + D.yoy.toFixed(1) + '% | 环比：' + (D.mom > 0 ? '+' : '') + D.mom.toFixed(1) + '% | SSSG：' + (D.sssg > 0 ? '+' : '') + D.sssg.toFixed(1) + '%\n';

  // ═══════════════════════════════════════════
  // 2. 人 — 客流转化漏斗
  // ═══════════════════════════════════════════
  p += '\n═══ 人：客流转化 ═══\n';
  p += '日均客流：' + D.flow.toFixed(0) + '人（同比' + (D.flow_yoy > 0 ? '+' : '') + D.flow_yoy.toFixed(1) + '%）\n';
  p += '成交率：' + D.conv.toFixed(1) + '%（同比' + (D.conv_yoy > 0 ? '+' : '') + D.conv_yoy.toFixed(1) + 'pp）\n';
  p += '周客单量：' + D.tkt_cnt.toFixed(0) + '笔\n';
  p += '客单价：¥' + D.avg_t.toFixed(0) + '（同比' + (D.avg_t_yoy > 0 ? '+' : '') + D.avg_t_yoy.toFixed(1) + '%）\n';
  p += '连带率：' + D.attach_r.toFixed(2) + '件（同比' + (D.attach_yoy > 0 ? '+' : '') + D.attach_yoy.toFixed(1) + '%）\n';
  p += '件单价：¥' + D.unit_p.toFixed(0) + '（同比' + (D.unit_yoy > 0 ? '+' : '') + D.unit_yoy.toFixed(1) + '%）\n';
  // 判断漏斗问题
  if (D.flow_yoy > 0 && D.conv_yoy < 0) {
    p += '⚠️  客流↑但成交率↓ — "进店不买"问题突出\n';
  }
  if (D.flow_yoy < -10) {
    p += '⚠️  客流大幅下降 — "不来人"是首要问题\n';
  }

  // ═══════════════════════════════════════════
  // 3. 货 — 品类 | TOP | 子品类 | 新品 | 库存
  // ═══════════════════════════════════════════
  p += '\n═══ 货：品类健康度 ═══\n';
  var cats = D.category;
  if (cats) {
    var cnames = Object.keys(cats);
    for (var i = 0; i < cnames.length; i++) {
      var c = cats[cnames[i]], cn = cnames[i];
      p += cn + '：¥' + (c.flow / 10000).toFixed(1) + '万 | 占比' + (c.f_share ? c.f_share.toFixed(1) : '0') + '% | 同比' + (c.yoy > 0 ? '+' : '') + (c.yoy ? c.yoy.toFixed(1) : '0') + '% | 折扣' + (c.disc ? c.disc.toFixed(1) : '0') + '%\n';
      if (c.group === 'product') {
        p += '  SKU：' + c.sku_s + ' | 库存：' + (c.s_qty ? c.s_qty : '0') + ' | 动销率：' + (c.sku_u ? c.sku_u.toFixed(1) : '0') + '% | ' + (c.match_lbl || '') + '\n';
      }
    }
  }

  // TOP 集中度
  var top = D.top;
  if (top) {
    p += '\n--- TOP商品集中度 ---\n';
    for (var tk in top) {
      var tv = top[tk];
      if (tv) {
        var t4 = tv['4'] || 0, t6 = tv['6'] || 0;
        p += tk + '：服' + (t4 ? t4.toFixed(1) + '%' : '--') + ' | 鞋' + (t6 ? t6.toFixed(1) + '%' : '--') + '\n';
      }
    }
  }

  // 子品类下钻
  p += '\n--- 子品类下钻 ---\n';
  var subPs = D.sub_ps;
  if (subPs && subPs.length) {
    var clothTops = subPs.filter(function(r) { return !r.isAcc; }).slice(0, 5);
    var accTops = subPs.filter(function(r) { return r.isAcc; }).slice(0, 3);
    p += '服装子品类TOP5：';
    for (var i = 0; i < clothTops.length; i++) {
      p += clothTops[i].n + ' ¥' + (clothTops[i].f / 10000).toFixed(2) + '万' + (i < clothTops.length - 1 ? ' | ' : '');
    }
    p += '\n配件子品类：';
    for (var i = 0; i < accTops.length; i++) {
      p += accTops[i].n + ' ¥' + (accTops[i].f / 10000).toFixed(2) + '万' + (i < accTops.length - 1 ? ' | ' : '');
    }
    p += '\n';
  }
  var shoe = D.shoe;
  if (shoe && shoe.length) {
    p += '鞋系列：';
    for (var i = 0; i < shoe.length && i < 5; i++) {
      p += shoe[i].n + ' ¥' + (shoe[i].f / 10000).toFixed(2) + '万' + (i < 4 && i < shoe.length - 1 ? ' | ' : '');
    }
    p += '\n';
  }

  // 新品季节
  p += '\n--- 新品季节 ---\n';
  var seas = D.seas;
  if (seas) {
    for (var sk in seas) {
      var s = seas[sk];
      p += sk + '：¥' + (s.f / 10000).toFixed(1) + '万 | 折扣' + s.d.toFixed(1) + '% | SKU' + s.sku + ' | 库存' + s.stock_qty + ' | 动销率' + s.su.toFixed(1) + '%\n';
    }
  }

  // 中类对比
  p += '\n--- 中类对比 ---\n';
  var ma = D.mid_agg;
  if (ma) {
    var mn = ['男服', '女服', '男鞋', '女鞋'];
    for (var i = 0; i < mn.length; i++) {
      var m = ma[mn[i]];
      if (m) {
        p += mn[i] + '：¥' + (m.f / 10000).toFixed(1) + '万 | SKU' + (m.sku || 0) + ' | 库存' + (m.stock_qty || 0) + ' | 折扣' + (m.d ? m.d.toFixed(1) : '--') + '% | 动销率' + (m.su ? m.su.toFixed(1) : '--') + '%\n';
      }
    }
  }

  // ═══════════════════════════════════════════
  // 4. 场 — 日别节奏 | 折扣环境 | 对标
  // ═══════════════════════════════════════════
  p += '\n═══ 场：日别节奏 ═══\n';
  var wi = 0, bi = 0;
  var days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  for (var i = 0; i < 7 && i < D.daily.length; i++) {
    var d = D.daily[i];
    p += days[i] + '：¥' + (d.f / 10000).toFixed(1) + '万 | 达成' + d.a.toFixed(1) + '% | 客流' + d.v + '人 | 客单¥' + d.tk.toFixed(0) + ' | 连带' + d.at.toFixed(2) + '\n';
    if (d.a < D.daily[wi].a) wi = i;
    if (d.a > D.daily[bi].a) bi = i;
  }
  p += '低谷日：' + D.daily[wi].n + '(' + D.daily[wi].a.toFixed(1) + '%) | 高峰日：' + D.daily[bi].n + '(' + D.daily[bi].a.toFixed(1) + '%)\n';
  // 周末day 5=周六,6=周日
  if (D.daily.length >= 7) {
    var wkdaySum = 0, wkendSum = 0, wkCnt = 0, weCnt = 0;
    for (var i = 0; i < 5; i++) { if (D.daily[i]) { wkdaySum += D.daily[i].f; wkCnt++; } }
    for (var i = 5; i < 7; i++) { if (D.daily[i]) { wkendSum += D.daily[i].f; weCnt++; } }
    p += '工作日日均：¥' + (wkCnt > 0 ? (wkdaySum / wkCnt / 10000).toFixed(1) : '--') + '万 | 周末日均：¥' + (weCnt > 0 ? (wkendSum / weCnt / 10000).toFixed(1) : '--') + '万\n';
  }

  p += '\n═══ 场：折扣与对标 ═══\n';
  p += '折扣率：' + D.disc.toFixed(1) + '%（同比' + (D.disc_yoy_p > 0 ? '+' : '') + D.disc_yoy_p.toFixed(1) + 'pp，约' + ((100 - D.disc) / 10).toFixed(1) + '折）\n';
  p += '折扣螺旋：' + (D.disc > 40 && D.mom < -10 ? '⚠️ 是（高折扣+流水下滑）' : '否') + '\n';
  p += 'O2O：¥' + (D.o2o / 10000).toFixed(2) + '万（占比' + (D.o2o_pct ? D.o2o_pct.toFixed(1) : '0') + '%，环比' + (D.o2o_mom > 0 ? '+' : '') + D.o2o_mom.toFixed(1) + '%）\n';

  // 对标（如果有数据）
  var reg = D.reg;
  if (reg && reg.achieve && reg.achieve > 1) {
    p += '区域达成率均值：' + reg.achieve.toFixed(1) + '%（本店' + (D.achieve - reg.achieve > 0 ? '高于' : '低于') + (Math.abs(D.achieve - reg.achieve)).toFixed(1) + 'pp）\n';
  }

  // ═══════════════════════════════════════════
  // 5. 量化机会
  // ═══════════════════════════════════════════
  p += '\n═══ 量化改善机会 ═══\n';
  var tktCnt = D.tkt_cnt || 0;
  var unitP = D.unit_p || 0;
  // 成交率提升 4pp → 增量
  var convLift = (D.conv + 4 - D.conv) / 100 * D.flow * 7 * D.avg_t;
  p += '成交率+' + 4 + 'pp → 周增量约 ¥' + (convLift / 10000).toFixed(1) + '万\n';
  // 连带率 → 4.5 件
  var attachLift = (4.5 - D.attach_r) * tktCnt * unitP;
  p += '连带率→4.5件 → 周增量约 ¥' + (attachLift / 10000).toFixed(1) + '万\n';
  // 客单价 → ¥600
  var ticketLift = (600 - D.avg_t) * tktCnt;
  p += '客单价→¥600 → 周增量约 ¥' + (ticketLift / 10000).toFixed(1) + '万\n';
  // 最差日复苏
  if (D.daily && D.daily[wi]) {
    var worstGap = D.daily[wi].t - D.daily[wi].f;
    p += D.daily[wi].n + '复苏（达到目标）→ 增量约 ¥' + (Math.max(0, worstGap) / 10000).toFixed(1) + '万\n';
  }

  // ═══════════════════════════════════════════
  // 6. 输出模板（人货场 + 量化）
  // ═══════════════════════════════════════════
  p += '\n═══════════════════════════════════════\n';
  p += '请按照"人货场"三维框架输出分析报告，每段100-150字，必须引用具体数字。格式：\n\n';
  p += '【达成总览】目标达成率分析+同比/环比/SSSG增长质量判断\n';
  p += '【人—转化漏斗】客流×成交率的组合关系，诊断"进店不买"还是"不来人"\n';
  p += '【人—客单效率】客单价/连带率/件单价趋势，识别提升客单的关键杠杆\n';
  p += '【货—品类健康度】鞋服配三大品类表现+TOP集中度+SKU效率问题\n';
  p += '【货—商品深度】子品类下钻、新品季节表现、中类对比\n';
  p += '【货—库存匹配】库销匹配分析、动销率与库存积压\n';
  p += '【场—日别节奏】工作日vs周末对比、低谷日特征、高峰日可复制经验\n';
  p += '【场—折扣诊断】折扣率合理性、"越打折越卖不动"风险评估\n';
  p += '【机会量化】基于数据的可计算改善空间（引用上面的量化数据）\n';
  p += '【改善建议】3条可执行策略（每条含：目标数字+执行动作+预期效果）\n';
  p += '\n要求：专业客观，不写"表现良好/有待提升"等空话，每段必须有数据支撑。';

  callDeepSeek(p, function(result, err) {
    if (err) {
      var idx = Math.floor(Math.random() * FULL_TEXTS.length);
      document.getElementById('fullTextContent').innerHTML =
        '<div style="color:#666;font-size:12px;margin-bottom:8px">AI离线，使用预制分析</div>' + FULL_TEXTS[idx];
      showToast('AI离线', 'info');
    } else {
      // 分段展示 — 统一易读字体，带段落间距
      var html = result
        .replace(/\n/g, '<br>')
        .replace(/═══/g, '')
        .replace(/【人—/g, '<div style="margin-top:18px;margin-bottom:6px;padding-top:12px;border-top:1px solid #eee"><b style="font-size:14px">【人—')
        .replace(/【货—/g, '<div style="margin-top:18px;margin-bottom:6px;padding-top:12px;border-top:1px solid #eee"><b style="font-size:14px">【货—')
        .replace(/【场—/g, '<div style="margin-top:18px;margin-bottom:6px;padding-top:12px;border-top:1px solid #eee"><b style="font-size:14px">【场—')
        .replace(/【达成总览】/g, '<b style="font-size:14px">【达成总览】</b>')
        .replace(/【机会量化】/g, '<div style="margin-top:18px;margin-bottom:6px;padding-top:12px;border-top:1px solid #eee"><b style="font-size:14px">【机会量化】</b></div>')
        .replace(/【改善建议】/g, '<div style="margin-top:18px;margin-bottom:6px;padding-top:12px;border-top:1px solid #eee"><b style="font-size:14px">【改善建议】</b></div>');

      document.getElementById('fullTextContent').innerHTML =
        '<div style="font-size:12px;color:#333;margin-bottom:12px;padding:8px 12px;background:#f5f5f5;border-radius:6px;font-family:system-ui,sans-serif">AI 实时生成 | 人货场框架 | ' + D.period + ' 周报分析</div>' + html;
      showToast('AI分析完成', 'success');
    }
    if (btn) { btn.classList.remove('loading'); btn.disabled = false; }
  });
}
