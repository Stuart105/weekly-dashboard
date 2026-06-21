# weekly-dashboard

周报分析工具链 —— 每周从公司报表自动筛选关键数据，生成可视化仪表板并调用大模型进行 AI 分析。

## 核心流程

```
每周数据（飞书多维表格 或 Excel）
        ↓
   数据提取/清洗
        ↓
   build_dashboard.py  → weekly-dashboard.html（可视化仪表板）
        ↓
   AI 分析（DeepSeek 大模型） → 自动解读指标变化
        ↓
   浏览器打开 / 推送至 GitHub Pages
```

## 三种使用方式

### 方式 A：飞书自动同步（推荐，每周一自动更新）

已配置 GitHub Actions 定时任务，每周一 00:00（UTC）自动从飞书多维表格拉取最新数据，刷新仪表板。

手动触发：在 GitHub 仓库 → Actions → 「更新周报数据」 → Run workflow

### 方式 B：命令行手动生成（数据在本地 Excel 时）

```bash
# 1. 从 Excel 提取数据
python3 extract_data.py 你的周报文件.xlsx

# 2. 生成仪表板（含图表、KPI、品类分析）
python3 build_dashboard.py

# 3. 注入 AI 分析（需要 DeepSeek API Key）
python3 ai/deepseek_inject.py

# 4. 用浏览器打开
open weekly-dashboard.html
```

一键执行上述所有步骤：

```bash
python3 scripts/build_all.py
```

### 方式 C：本地 HTTP 服务（上传 Excel 自动构建）

```bash
# 启动服务，支持 Excel 上传 → 自动解析 → 生成仪表板
python3 server.py

# 浏览器访问 http://localhost:8000
```

## 项目结构

```
weekly-dashboard/
├── build_dashboard.py      ← 主脚本：生成 HTML 仪表板
├── generate_reports.py     ← 生成三份文字报告（深度分析/策略/分析稿）
├── extract_data.py         ← 从 Excel 提取 JSON 数据
│
├── feishu/                 ← 飞书数据源模块
│   ├── feishu_fetch.py     ← 从多维表格读取 KPI 数据
│   └── feishu_build.py     ← 飞书全流程 → 仪表板
│
├── ai/                     ← AI 分析模块
│   ├── deepseek_client.py  ← DeepSeek API 客户端
│   ├── deepseek_inject.py  ← 将 AI 分析注入 HTML 仪表板
│   └── deepseek_analyzer.js ← 浏览器端 AI 交互代码
│
├── scripts/                ← 辅助脚本
│   ├── build_all.py        ← 一键生成 + AI 注入
│   └── build_and_deploy.py ← 一键生成 + Git 提交部署
│
├── data/                   ← 本地周报数据（不提交到 Git）
├── reports/                ← 本地历史报告（不提交到 Git）
│
├── server.py               ← 本地 HTTP 服务（支持 Excel 上传）
├── Procfile                ← 服务部署配置
│
├── .github/workflows/
│   └── update-dashboard.yml ← 每周一自动从飞书更新
│
├── .env.example            ← 环境变量模板
├── requirements.txt        ← Python 依赖
├── favicon.ico             ← 仪表板图标
│
├── weekly-dashboard.html   ← 主仪表板（构建产物，保留在 Git）
└── index.html              ← EdgeOne Pages 入口（与 weekly-dashboard 同步）
```

## 功能亮点

- 📊 **10个KPI指标带**：达成率 / 流水 / 同比 / 成交率 / 客单价 / 连带率 / 鞋占比 / O2O / 折扣率 / 客流
- 📅 **7个数据维度**：日别 / 品类 / 服装子品类 / 鞋系列 / TOP商品 / 新品季节 / 折扣区间
- 🔍 **3个分析Tab**：问题诊断 / 改善策略 / 全文分析稿
- 📈 **Chart.js 图表**：日别流水 / 品类占比 / TOP商品 / 新品折扣率
- 📥 **Excel 直接导入**：前端 JS 解析，无需重新构建
- 🤖 **问题诊断引擎**：自动识别同比暴跌 / 周六崩盘 / 品类全面下滑 / 客单连带双降 / 折扣恶性循环
- 🤖 **AI 分析**：DeepSeek 大模型解读指标变化与趋势

## 依赖安装

```bash
pip install requests openpyxl
```

## 环境变量（可选）

在项目根目录创建 `.env` 文件（参考 `.env.example`）：

```
# 飞书 API（用于飞书自动同步）
FEISHU_APP_ID=你的飞书AppID
FEISHU_APP_SECRET=你的飞书AppSecret
FEISHU_BASE_ID=你的飞书多维表格BaseID

# DeepSeek API（用于AI分析）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

## 注意事项

- `data/`、`reports/`、`extracted_data.json` 和 `.env` 均在 `.gitignore` 中，不会提交到 Git
- `weekly-dashboard.html` 和 `index.html` 是仪表板输出文件，保留在 Git 以便 GitHub Pages / EdgeOne 部署
- 每周新生成的报告和数据文件都在本地 `data/` 和 `reports/` 目录，不会污染仓库

## 作者

Stuart — 
