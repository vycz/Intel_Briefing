<div align="center">

# 🕵️ Intel Briefing - AI 情报聚合系统

**每天 5 分钟，掌握全球科技圈正在发生什么。**

用 AI 自动从 10+ 数据源抓取、翻译、分析情报，生成一份中文日报。

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Powered by Antigravity](https://img.shields.io/badge/Powered%20by-Antigravity-8A2BE2)](https://github.com/google-gemini)
[![GitHub Stars](https://img.shields.io/github/stars/77AutumN/Intel_Briefing?style=social)](https://github.com/77AutumN/Intel_Briefing)
[![G-Star](https://gitcode.com/c30c30cc/intel-briefing/star/badge.svg)](https://gitcode.com/c30c30cc/intel-briefing)
[![AtomGit](https://img.shields.io/badge/Platform-AtomGit-blue?logo=git)](#)

</div>

---

## 🤔 这是什么？

一个**开箱即用的情报采集+分析引擎**。你可以把它理解为：一个帮你自动"刷"全网科技新闻的 AI 助手，不过它刷完以后还会帮你整理成中文报告。

**适合谁用？**
- 想每天快速了解科技圈动态的开发者
- 做竞品分析、行业研究的产品经理
- 想找灵感和机会的独立开发者 / 创业者
- 任何对"信息不对称套利"感兴趣的人

## ✨ 它能干什么？

### 📊 情报日报 (`run_mission.py`)
从 10+ 数据源抓取最新信息，生成一份包含 8 大板块的中文日报：

| 板块 | 数据源 | 你能看到什么 |
|:--|:--|:--|
| 🛠️ 技术趋势 | Hacker News, GitHub Trending | 今天程序员们在聊什么 |
| 💰 资本动向 | 36Kr, WallStreetCN | 谁在融资、谁在并购 |
| 📚 学术前沿 | ArXiv AI/ML | 最新 AI 论文，自动翻译摘要 |
| 🚀 产品精选 | Product Hunt | 今天发布了什么新产品 |
| 💬 社区热议 | V2EX | 中文开发者社区在讨论什么 |
| 🐦 社交舆情 | X (Twitter) via Grok | Twitter 上的技术热话题 |
| 📖 深度洞察 | HN Top Blogs | 热门技术博客全文分析 |
| 🔗 链接验证 | 自动核查 | 每个链接都经过有效性检测 |

### 💰 赏金猎人 (`run_bounty_hunter.py`)
自动扫描 V2EX 和 Chrome 扩展商店，寻找：
- **V2EX 急单** — 筛选"有偿"、"求助"等关键词，按紧急程度打分
- **Chrome 扩展机会** — 找到"用户多但评分差"的扩展（适合重写竞品）

### ⛏️ Alpha 雷达 (`run_alpha_radar.py`)
通过 Grok 搜索 X/Twitter 上最新的开源项目，专注于：
- Solana / Web3 领域的 CLI 工具
- 有"包装变现"潜力的开源代码
- 自动验证 GitHub 链接是否有效（防 AI 幻觉）

### 🏗️ 营收分析师 (`run_revenue_architect.py`)
读取日报内容，用 LLM 自动分析出 5 类机会：

| 类别 | 说明 |
|:--|:--|
| 💰 变现机会 | 能直接赚钱的项目/需求 |
| 🧠 学习机会 | 值得深入研究的技术 |
| ✍️ 创作机会 | 高互动潜力的内容选题 |
| 📈 涨粉机会 | 可以蹭热度的趋势话题 |
| 🤝 背书机会 | 参与贡献能建立信誉的开源项目 |

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/77AutumN/Intel_Briefing.git
cd Intel_Briefing
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API 密钥

```bash
cp .env.example .env
# 编辑 .env，填入你自己的 API Key
```

### 4. 运行！

```bash
# 📊 生成情报日报（核心功能，推荐先试这个）
python run_mission.py

# 💰 寻找赏金机会
python run_bounty_hunter.py

# ⛏️ 扫描 Web3 开源工具
python run_alpha_radar.py

# 🏗️ 分析机会并生成行动计划
python run_revenue_architect.py
```

报告会保存在 `reports/` 目录下。

### 5. 代理 / VPN 配置（可选）

如果你需要通过代理访问外部 API，设置环境变量时请使用 **HTTP 代理地址**（不是 SOCKS）：

```bash
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
```

> [!IMPORTANT]
> `httpx` 默认不支持 SOCKS 代理（`socks5://`）。如果你的代理客户端只提供 SOCKS 端口，需要额外安装：
> ```bash
> pip install httpx[socks]
> ```

| 客户端 | HTTP 端口 | SOCKS 端口 |
|:--|:--|:--|
| Clash | 7890 | 7891 |
| V2RayN | 10809 | 10808 |

---

## 🔑 API 密钥说明

| 密钥 | 用途 | 是否必需 | 费用 |
|:--|:--|:--|:--|
| `GITHUB_TOKEN` | GitHub Trending (GraphQL API) | **必需** | ✅ [免费申请 PAT](https://github.com/settings/tokens) |
| `XAI_API_KEY` | Grok API (X/Twitter 舆情 + 营收分析) | 推荐 | 每月 $25 免费额度 ([申请](https://console.x.ai/)) |
| `PRODUCTHUNT_TOKEN` | Product Hunt 数据 | 可选 | ✅ [免费申请](https://www.producthunt.com/v2/oauth/applications) |
| `GEMINI_API_KEY` | Google Gemini (中文翻译) | 可选 | ✅ 免费额度充足 ([申请](https://aistudio.google.com/apikey)) |

> ⚠️ **最低要求：拿到 `GITHUB_TOKEN` 就能跑基础日报**（HN、GitHub Trending、ArXiv、V2EX、36Kr 等）。没有 `XAI_API_KEY` 会跳过 Twitter 舆情和营收分析。没有 `GEMINI_API_KEY` 会跳过中文翻译。
>
> 💡 **你需要用自己的 Key** — 本项目不内置任何 API 密钥，所有密钥都需要你自己申请。

---

## 📁 项目结构

```
Intel_Briefing/
├── run_mission.py              # 🎯 主入口：情报日报
├── run_bounty_hunter.py        # 💰 赏金猎人
├── run_alpha_radar.py          # ⛏️ Alpha 雷达
├── run_revenue_architect.py    # 🏗️ 营收分析师
├── cli.py                      # 命令行工具
├── fetch_unified_intel.py      # 统一情报采集器
├── prompts/
│   └── commercial_logic.md     # 营收分析 LLM Prompt（可自定义）
├── src/
│   ├── sensors/                # 数据源传感器
│   │   ├── arxiv_ai.py         # ArXiv 论文
│   │   ├── chrome_radar.py     # Chrome 扩展商店
│   │   ├── github_trending.py  # GitHub 热门项目
│   │   ├── hacker_news.py      # Hacker News
│   │   ├── hn_blogs.py         # HN 热门博客 (全文)
│   │   ├── product_hunt.py     # Product Hunt
│   │   ├── v2ex_radar.py       # V2EX 社区
│   │   ├── x_grok_sensor.py    # X/Twitter (Grok)
│   │   └── x_twitter.py        # X/Twitter (备用)
│   ├── generators/
│   │   └── curator.py          # 策展分析器
│   ├── utils/
│   │   ├── gemini_translator.py # Gemini 中文翻译
│   │   ├── jina_reader.py      # 网页全文提取
│   │   └── verifier.py         # 链接有效性验证
│   └── external/
│       └── fetch_news.py       # 新闻聚合核心模块
├── reports/                    # 📄 生成的报告目录
│   ├── daily_briefings/        # 情报日报
│   ├── tactical/               # 赏金猎人报告
│   ├── web3/                   # Alpha 雷达报告
│   └── opportunities/          # 营收分析报告
└── .env.example                # API 密钥模板
```

---

## 🎨 自定义

### 修改营收分析逻辑
编辑 `prompts/commercial_logic.md`，可以自定义 LLM 分析机会的维度和输出格式。

### 添加新的数据源
在 `src/sensors/` 下新建一个传感器文件，然后在 `fetch_unified_intel.py` 中导入即可。每个传感器只需要实现一个返回列表的函数。

### GitHub Actions 自动化
项目自带 `.github/workflows/daily-report.yml`，配置好 Secrets 后可以每天自动生成日报。

---

## 📄 License

MIT — 随便用，改了也不用告诉我。

---

<div align="center">

**如果觉得有用，给个 ⭐ 就是最大的支持。**

</div>
