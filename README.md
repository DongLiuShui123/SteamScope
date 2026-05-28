# SteamScope - AI 游戏评论洞察系统

SteamScope 是一个面向游戏产品运营场景的 Steam 玩家评论分析工具。用户输入任意 Steam 游戏 AppID 后，系统会自动获取玩家评论，并输出情绪分布、高频关键词、评论时间趋势和产品运营分析报告，帮助快速识别玩家满意点、负反馈问题和潜在口碑风险。

## 项目定位

游戏产品运营需要持续关注玩家评论，但人工阅读大量评论效率低，也不容易快速发现集中问题。SteamScope 将评论采集、数据清洗、情感分析、关键词提取和报告生成整合到一个网页工具中，让用户可以用更低成本完成一次基础的玩家反馈分析。

## 核心功能

- **Steam 评论采集**：输入 Steam AppID，自动获取玩家评论数据。
- **数据清洗**：使用 pandas 清洗重复、空值和疑似广告/导流评论。
- **情感分析**：结合 Steam 推荐字段、SnowNLP 情感分数和游戏评论语境词典，判断正向、中性、负向评论。
- **关键词提取**：使用 jieba 提取玩家高频讨论关键词。
- **趋势分析**：按全部、最近 7 天、最近 30 天或自定义日期查看评论情绪趋势。
- **产品运营报告**：自动生成简洁的玩家情绪分析报告，包含总览、核心发现、问题优先级、运营建议和典型评论。
- **结果下载**：支持下载清洗后的 CSV 数据和 Markdown 分析报告。

## 适用场景

- 游戏产品运营：跟踪玩家口碑，识别版本问题和社区风险。
- 产品经理作品集：展示数据分析、AI 工具应用和产品化表达能力。
- 玩家反馈研究：快速了解某款 Steam 游戏的好评点、差评点和讨论热点。

## 页面预览

运行后可以在浏览器中打开本地页面：

```text
http://localhost:8501
```

页面支持输入 Steam AppID，例如：

```text
1245620  # Elden Ring / 艾尔登法环
730      # Counter-Strike 2
570      # Dota 2
```

## 本地运行

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/SteamScope.git
cd SteamScope
```

如果你是直接下载 ZIP，也可以解压后进入项目文件夹。

### 2. 创建虚拟环境

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

macOS / Linux：

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 启动应用

```bash
streamlit run app.py
```

启动成功后，浏览器打开：

```text
http://localhost:8501
```

## 使用方法

1. 在左侧输入 Steam 游戏 AppID。
2. 选择评论数量、评论语言和评论类型。
3. 点击“开始分析”。
4. 查看情绪分布、高频关键词、评论时间趋势和分析报告。
5. 根据需要下载 CSV 数据或 Markdown 报告。

## 技术实现

| 模块 | 技术 |
|---|---|
| 网页界面 | Streamlit |
| 数据采集 | Steam Review API / Steam AppDetails API |
| 数据处理 | pandas |
| 中文分词 | jieba |
| 情感分析 | SnowNLP + Steam 推荐字段 + 规则词典 |
| 可视化 | Plotly |
| 报告生成 | Python 模板生成 Markdown |

## 项目结构

```text
SteamScope/
├── app.py                 # Streamlit 网页入口
├── requirements.txt       # Python 依赖
├── README.md              # 项目说明
├── .gitignore
└── src/
    ├── steam_api.py       # Steam API 请求
    ├── analysis.py        # 数据清洗、情感分析、关键词和问题识别
    ├── report.py          # 产品运营报告生成
    ├── sample_data.py     # 示例数据
    └── __init__.py
```

## 情感分析说明

项目不是只依赖 SnowNLP 单一模型，而是使用混合判断：

- Steam `voted_up=True` 代表玩家主动推荐。
- SnowNLP 给出文本情感分数。
- 游戏评论语境词典用于修正玩梗、安利、强情绪表达造成的误判。

例如部分玩家会用“卧槽”“不萌”“毒舌”等词表达强烈喜欢，单纯情感模型可能误判为负向。项目会结合 Steam 推荐字段和正向语境词，将这类评论识别为“高强度安利”。


## 注意事项

- Steam 在部分网络环境下访问可能较慢或超时。
- SnowNLP 不是专门针对游戏评论训练的模型，项目通过 Steam 推荐字段和规则词典进行补充修正。
- 分析结果适合作为产品运营判断的辅助依据，不应替代人工复核。
