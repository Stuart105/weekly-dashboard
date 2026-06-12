# weekly-dashboard

安踏零售店铺周报分析仪表板 — 从 Excel 周报自动生成单页 HTML 分析仪表板 + 三份分析报告。

## 快速开始

### 方式一：直接用 HTML 导入 Excel（推荐）

1. 运行 `python build_dashboard.py`（无需参数，会生成一个含默认数据的 HTML）
2. 用浏览器打开 `weekly-dashboard.html`
3. 点击右上角 **「导入 Excel」** 按钮，上传新一周的 Excel 周报
4. 仪表板自动刷新，所有图表和分析同步更新
5. 浏览器「另存为」即可保存最新版本

> HTML 内置 SheetJS 库，可直接解析 Excel，**无需每次重新运行 Python 脚本**。

### 方式二：命令行生成（适合自动化）

```bash
# 1. 准备 extracted_data.json（首次需要，后续可直接用方式一）
python extract_data.py 周报打印.xlsx

# 2. 生成仪表板 HTML
python build_dashboard.py [数据目录]

# 3. 生成三份分析报告
python generate_reports.py [数据目录]
```

- 不传参数：在当前目录找 `extracted_data.json`
- 传参数：指定包含 `extracted_data.json` 的目录

## 项目结构

```
weekly-dashboard/
├── build_dashboard.py   ← 生成 weekly-dashboard.html（主仪表板）
├── generate_reports.py   ← 生成三份报告（深度分析/策略/文字稿）
├── extract_data.py       ← （脚手架）从 Excel 提取 JSON
├── weekly-dashboard.html ← 输出：主仪表板（单文件，含 Chart.js）
├── W23周报深度分析报告.html
├── W23周分析_改善策略.html
└── W23周报分析稿.txt
```

## 功能亮点

- 📊 **10个KPI指标带**：达成率/流水/同比/成交率/客单价/连带率/鞋占比/O2O/折扣率/客流
- 📅 **7个数据Tab**：日别/品类/服装子品类/鞋系列/TOP商品/新品季节/折扣区间
- 🔍 **3个分析Tab**：问题诊断（自动识别）/改善策略/全文分析稿
- 📈 **Chart.js图表**：日别流水/品类占比/TOP商品/新品折扣率
- 📥 **Excel直接导入**：前端JS解析，无需重新构建
- 🤖 **问题诊断引擎**：自动识别同比暴跌/周六崩盘/品类全面下滑/客单连带双降/折扣恶性循环

## 依赖

```bash
pip install openpyxl  # 仅 extract_data.py 需要
```

## 工作流程

```
Excel 周报 (.xlsx)
    ↓（方式一：直接用 HTML 导入，无需此步骤）
    ↓（方式二：extract_data.py）
extracted_data.json
    ↓
build_dashboard.py / generate_reports.py
    ↓
weekly-dashboard.html + 三份报告
```

## 注意事项

- `extracted_data.json` 在 `.gitignore` 中，不会提交到 Git
- 首次使用需要准备 `extracted_data.json`，后续直接用 HTML 导入更方便
- 如需适配新的 Excel 周报格式，修改 `build_dashboard.py` 中的数据解析逻辑

## 作者

Stuart — 安踏零售数据分析工具链
