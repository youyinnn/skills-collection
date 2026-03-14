# Skills 平台兼容性指南

本指南说明各 skill 适合在 **Claude Code** 还是 **Claude.ai** 中使用，帮助你针对每项科研任务选择合适的工具。

## 分类标准

| 类别 | 说明 |
|---|---|
| **Claude Code 专属** | 需要执行代码、本地文件读写、HTTP API 调用或 Python 库 |
| **两者均适合** | 写作、分析或讨论类任务 — Claude Code 额外提供文件管理能力；Claude.ai 对话更流畅 |
| **Claude.ai 更适合** | 主要为对话场景 — 无需文件操作；Claude.ai 界面更自然 |

---

## 插件：literature-and-topic-selection

| Skill | 平台 | 原因 |
|---|---|---|
| `arxiv-database` | **Claude Code 专属** | 通过 HTTP 调用 arXiv Atom API |
| `biorxiv-database` | **Claude Code 专属** | 通过 HTTP 调用 bioRxiv API |
| `pubmed-database` | **Claude Code 专属** | 通过 HTTP 调用 NCBI E-utilities REST API |
| `openalex-database` | **Claude Code 专属** | 以编程方式查询 OpenAlex API |
| `bgpt-paper-search` | **Claude Code 专属** | 需要 `Bash` 工具（BGPT MCP 服务器） |
| `pyzotero` | **Claude Code 专属** | 运行 Python `pyzotero` 客户端；读写 Zotero 文献库 |
| `literature-review` | **两者均适合** | Claude Code：通过结构化 API 自动化多数据库检索 + 输出 Markdown/PDF 文件；Claude.ai：可通过联网搜索查找文献，但无法调用结构化 API，结果不够系统、无法批量导出 |
| `citation-management` | **两者均适合** | Claude Code：批量生成 BibTeX 文件、批量验证引用；Claude.ai：针对具体引用进行核查和讨论 |
| `hypothesis-generation` | **两者均适合** | Claude Code：写入假设文件并关联数据；Claude.ai：基于观测进行对话式假设讨论 |
| `research-grants` | **两者均适合** | Claude Code：本地撰写和管理基金文档；Claude.ai：起草并迭代申请文本 |
| `scientific-critical-thinking` | **两者均适合** | Claude Code：结构化评估并输出文件；Claude.ai：实时讨论论文方法论 |
| `scientific-brainstorming` | **Claude.ai 更适合** | 纯对话场景 — 开放式头脑风暴在聊天界面更自然；Claude Code 可用但无附加价值 |

---

## 插件：data-preparation-and-processing

| Skill | 平台 | 原因 |
|---|---|---|
| `pydicom` | **Claude Code 专属** | 使用 Python `pydicom` 读写 DICOM 文件 |
| `histolab` | **Claude Code 专属** | 处理 WSI 切片文件；运行 tile 提取流水线 |
| `pathml` | **Claude Code 专属** | 完整计算病理学工具包；需要 GPU/文件访问 |
| `imaging-data-commons` | **Claude Code 专属** | 通过 `idc-index` 下载癌症影像数据集 |
| `neurokit2` | **Claude Code 专属** | 用 Python 处理 ECG/EEG/EDA 等生理信号文件 |
| `pyhealth` | **Claude Code 专属** | 在 EHR 数据集（MIMIC、eICU）上训练 ML 模型；需要本地数据 |
| `clinicaltrials-database` | **Claude Code 专属** | 查询 ClinicalTrials.gov API v2 |
| `clinvar-database` | **Claude Code 专属** | 通过 E-utilities API 查询 NCBI ClinVar |
| `dask` | **Claude Code 专属** | 分布式/超内存计算；需要 Python 执行环境 |
| `polars` | **Claude Code 专属** | 内存 DataFrame 处理；需要 Python 执行环境 |
| `exploratory-data-analysis` | **Claude Code 专属** | 读取本地数据文件（200+ 格式）；生成 EDA 报告 |
| `statistical-analysis` | **两者均适合** | Claude Code：对本地数据文件运行统计检验；Claude.ai：无需数据时，提供检验选择建议和结果解读 |

---

## 插件：model-development-and-experiments

> 本插件中所有 skills 均为 **Claude Code 专属** — 全部需要运行 Python 代码。

| Skill | 原因 |
|---|---|
| `pytorch-lightning` | 训练神经网络；需要 GPU、本地数据和 checkpoint 文件 |
| `transformers` | 微调预训练模型；需要 HuggingFace token 和算力 |
| `torch-geometric` | 在图数据上训练图神经网络 |
| `scikit-learn` | 在本地数据集上运行 ML 流水线 |
| `shap` | 从已训练模型计算 SHAP 值 |
| `aeon` | 在本地时序数据上进行时间序列 ML |
| `umap-learn` | 对本地高维数据做降维 |
| `pymc` | 贝叶斯推断与 MCMC；计算密集型 |
| `networkx` | 从数据构建和分析图结构 |
| `primekg` | 以编程方式查询 PrimeKG 知识图谱 |
| `stable-baselines3` | 在 Gymnasium 环境中训练 RL 智能体 |

---

## 插件：results-analysis-and-visualization

> 所有可视化 skills 均为 **Claude Code 专属** — 均需从本地数据生成图表。

| Skill | 原因 |
|---|---|
| `matplotlib` | 生成静态图表并保存为 PNG/PDF/SVG |
| `seaborn` | 基于 pandas DataFrame 的统计图表 |
| `plotly` | 基于本地数据的交互式可视化 |
| `scientific-visualization` | 发表级多面板图表（Nature/Cell 格式） |
| `statsmodels` | 拟合统计模型（OLS、GLM、ARIMA）于本地数据 |
| `statistical-analysis` | **两者均适合** — 详见数据处理部分 |

---

## 插件：paper-writing-and-submission

| Skill | 平台 | 原因 |
|---|---|---|
| `latex-posters` | **Claude Code 专属** | 在本地写入并编译 `.tex` 海报文件 |
| `pptx-posters` | **Claude Code 专属** | 生成 HTML/CSS 文件并导出为 PPTX/PDF |
| `paper-2-web` | **Claude Code 专属** | 将本地 LaTeX/PDF 转换为网页/视频/海报格式 |
| `infographics` | **Claude Code 专属** | 通过 Bash 工具生成信息图文件 |
| `scientific-writing` | **两者均适合** | Claude Code：撰写和管理完整的 `.tex`/`.md` 稿件及引用；Claude.ai：起草段落、润色文字、讨论论证结构 |
| `venue-templates` | **两者均适合** | Claude Code：将模板应用于本地稿件文件；Claude.ai：通过联网搜索查询并讨论最新投稿格式要求 |
| `peer-review` | **两者均适合** | Claude Code：结构化审稿意见输出至文件；Claude.ai：非常适合迭代式 rebuttal 撰写和评审意见分析 |
| `scholar-evaluation` | **两者均适合** | Claude Code：结构化评分报告输出至文件；Claude.ai：实时讨论论文优缺点 |
| `scientific-slides` | **两者均适合** | Claude Code：生成 `.pptx`/`.tex` 幻灯片文件；Claude.ai：规划报告结构和内容 |
| `markdown-mermaid-writing` | **两者均适合** | Claude Code：写入和管理本地 `.md` 文档；Claude.ai：在对话中起草内容和创建图表 |

---

## 汇总

| 平台 | Skills 数量 | 典型任务 |
|---|---|---|
| **Claude Code 专属** | 37 | 数据处理、模型训练、可视化、数据库查询、文件生成 |
| **两者均适合** | 12 | 写作、文献综述、统计指导、同行评审、演讲规划 |
| **Claude.ai 更适合** | 1 | 开放式科研头脑风暴 |

> 注：`statistical-analysis` 同时出现在 `data-preparation-and-processing` 和 `results-analysis-and-visualization` 两个插件中，以上计数仅统计一次。

### 快速决策规则

- **任务涉及本地文件、运行代码或调用 API？** → Claude Code
- **任务是写作、评审或讨论？** → 两者均可；需要文件输出时选 Claude Code
- **纯粹的开放式对话？** → Claude.ai

---

## 关于 Claude.ai 中的 Skills

本仓库定义的 skills 仅由 **Claude Code** 加载，Claude.ai 不会读取这些 SKILL.md 文件。

两点重要说明：

**对于 Claude Code 专属任务**，差距不在于精确度，而在于**能与不能**。Claude.ai 无法读取本地 DICOM 文件，无法真正调用 PubMed API，也无法运行 PyTorch 训练循环——这些是执行环境的硬性限制，与 skill 文件无关。

**对于两者均适合的任务**，本指南比较的是"加载了 skills 的 Claude Code"与"未加载任何 skill 上下文的 Claude.ai"。如果你手动向 Claude.ai 提供相关内容（如粘贴论文、粘贴评审意见、粘贴数据摘要），底层模型完全相同——输出质量不会有差异。真正的区别在于**自动化程度和文件系统访问**，而非模型能力本身。

简言之：任务涉及本地环境时用 Claude Code；分析、写作或讨论类任务两者均可。
