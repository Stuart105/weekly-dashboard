# weekly-dashboard

安踏零售店铺周报仪表板 —— 从飞书云盘自动拉取最新周报数据，生成可视化仪表板。

## 核心流程

```
飞书云盘（每周上传周报电子表格）
        ↓  自动扫描最新文件
  feishu_build_v2.py（动态表头解析 + 数据提取）
        ↓  生成 JSON 注入 HTML
  weekly-dashboard.html（单页仪表板，可直接部署）
```

## 项目结构

```
weekly-dashboard/
├── feishu/
│   └── feishu_build_v2.py        ← 核心：数据提取 + 动态表头解析
├── weekly-dashboard.html         ← 仪表板前端（自包含，含 Chart.js）
├── index.html                    ← 入口镜像（部署用）
├── .github/workflows/
│   └── update-dashboard.yml      ← 每周一自动更新
├── .env.example                  ← 环境变量模板
├── .env                          ← 实际凭证（不提交 Git）
├── requirements.txt              ← Python 依赖
└── favicon.ico                   ← 图标
```

## 使用方式

### 自动模式（推荐）

```bash
# 自动扫描云盘，匹配最新周报
python3 feishu/feishu_build_v2.py
```

### 手动指定周报

```bash
python3 feishu/feishu_build_v2.py W25
```

### 列出云盘文件

```bash
python3 feishu/feishu_build_v2.py --list
```

### 启动本地预览

```bash
python3 -m http.server 8000
# 浏览器打开 http://localhost:8000/weekly-dashboard.html
```

## 环境变量

在项目根目录创建 `.env`：

```
FEISHU_APP_ID=cli_xxxxxxxx
FEISHU_APP_SECRET=xxxxxxxx
FEISHU_BASE_ID=XJAZbw1rqaWHMnsVAJIci7ttnJd
FEISHU_FOLDER_TOKEN=O7etfItlNl7CLedE04kc2ZHUncM
```

## 功能亮点

- **10个KPI指标带**：达成率 / 流水 / 同比 / 成交率 / 客单价 / 连带率 / 鞋占比 / O2O / 折扣率 / 客流
- **7个数据维度**：日别 / 品类 / 服装子品类 / 鞋系列 / TOP商品 / 新品季节 / 折扣区间
- **3个分析Tab**：问题诊断 / 改善策略 / 全文分析稿
- **Chart.js 图表**：日别流水 / 品类占比 / TOP商品 / 新品折扣率
- **问题诊断引擎**：自动识别同比暴跌 / 周六崩盘 / 品类下滑 / 客单连带双降 / 折扣恶性循环
- **动态表头解析**：W26/W27 等未来周报无需修改代码，自动适配
- **云盘自动匹配**：上传新周报到云盘后，自动识别并提取最新数据

## 依赖

```bash
pip install requests
```

## 自动化部署

GitHub Actions 每周一自动从飞书云盘拉取最新周报数据，更新仪表板并推送。

## 作者

Stuart — 安踏零售数据分析工具链