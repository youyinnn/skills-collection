# 推荐 Skills 整理 — AI / Medical AI 博士研究工作流

> 共 175 个 skill 中，针对 AI + Medical AI 研究方向筛选出的最相关 skills，按研究工作流阶段分类。

---

## 📚 阶段一：选题 & 文献调研

| Skill | 用途 |
|---|---|
| `scientific-brainstorming` | 创意研究选题、发现 research gap、探索跨学科联系 |
| `hypothesis-generation` | 从数据或文献中提炼可检验的科学假设 |
| `literature-review` | 系统性文献综述，整合 PubMed / arXiv / bioRxiv 等多数据库，输出带引用的 Markdown/PDF |
| `scientific-critical-thinking` | 评估实验设计有效性、识别偏差与混杂因素、证据质量分级（GRADE/Cochrane） |
| `citation-management` | 参考文献管理 |
| `pyzotero` | 与 Zotero 联动，程序化管理文献库、导出引用、上传 PDF 附件 |
| `arxiv-database` | 搜索 arXiv 预印本（CS/AI/统计方向） |
| `pubmed-database` | 直接访问 PubMed REST API，高级 Boolean/MeSH 查询 |
| `biorxiv-database` | 搜索 bioRxiv 生命科学预印本 |
| `openalex-database` | 查询 240M+ 学术文献，支持引用分析、研究趋势分析 |
| `bgpt-paper-search` | 从全文中提取结构化实验数据（方法、结果、样本量），适合深度文献分析 |
| `research-grants` | 撰写 NSF / NIH / DARPA 等基金申请 |

---

## 🗄️ 阶段二：数据准备 & 处理

### 医学影像
| Skill | 用途 |
|---|---|
| `pydicom` | 读写医学 DICOM 文件（CT / MRI / X-Ray / 超声），提取像素数据与元数据 |
| `pathml` | 计算病理学全切片图像（WSI）分析，支持多重免疫荧光、组织分割、160+ 格式 |
| `histolab` | 轻量级 H&E 切片 tile 提取，适合简单 WSI 预处理 |
| `imaging-data-commons` | 访问 NIH 医学影像公开数据集 |

### 临床 & EHR 数据
| Skill | 用途 |
|---|---|
| `pyhealth` | 综合医疗 AI 工具包，支持 MIMIC-III/IV、eICU、OMOP，临床预测任务（死亡率、再入院、药物推荐） |
| `clinicaltrials-database` | 查询 ClinicalTrials.gov，获取临床试验数据 |
| `clinvar-database` | 查询 ClinVar 遗传变异与临床意义数据库 |

### 生理信号
| Skill | 用途 |
|---|---|
| `neurokit2` | 生理信号处理：ECG / EEG / EDA / PPG / EMG，支持 HRV 分析、事件相关电位 |

### 通用数据处理
| Skill | 用途 |
|---|---|
| `polars` | 快速 in-memory DataFrame 处理（pandas 的高速替代，适合 1–100GB） |
| `exploratory-data-analysis` | 自动化 EDA，快速了解数据分布与质量 |
| `statistical-analysis` | 统计检验、回归分析 |
| `dask` | 超出内存的大规模数据并行处理 |

---

## 🤖 阶段三：模型开发 & 实验

### 核心深度学习
| Skill | 用途 |
|---|---|
| `transformers` | HuggingFace Transformers，支持文本/图像/音频/多模态，fine-tuning 预训练模型 |
| `pytorch-lightning` | 组织 PyTorch 训练代码，支持多 GPU / TPU、分布式训练（DDP / FSDP / DeepSpeed）、W&B 日志 |
| `scikit-learn` | 经典 ML，分类 / 回归 / 聚类 / 模型评估 |

### 图神经网络
| Skill | 用途 |
|---|---|
| `torch-geometric` | GNN：节点/图分类、链接预测、GCN / GAT / GraphSAGE，适合医学知识图谱 |
| `networkx` | 复杂网络分析，生物网络、引用网络、图算法 |
| `primekg` | 查询精准医疗知识图谱（基因-药物-疾病-表型多尺度关联） |

### 可解释性 & 不确定性
| Skill | 用途 |
|---|---|
| `shap` | 模型可解释性（XAI），特征重要性分析（医疗 AI 论文必备） |
| `pymc` | 贝叶斯建模，不确定性量化，层次模型 |

### 时间序列 & 强化学习
| Skill | 用途 |
|---|---|
| `aeon` | 时间序列 ML：分类、预测、异常检测（适合生理信号、ICU 数据） |
| `stable-baselines3` | 强化学习标准算法快速实现 |

### 降维 & 聚类
| Skill | 用途 |
|---|---|
| `umap-learn` | 高维数据降维可视化（2D/3D），可与 HDBSCAN 聚类结合 |

---

## 📊 阶段四：结果分析 & 可视化

| Skill | 用途 |
|---|---|
| `scientific-visualization` | 发表级多面板图表，支持 Nature / Science / Cell / IEEE 格式规范，色盲友好配色 |
| `matplotlib` | 完全自定义静态图，导出 PNG / PDF / SVG |
| `seaborn` | 统计图表快速出图（分布、热图、回归） |
| `plotly` | 交互式可视化，适合 EDA 和展示 |
| `statistical-analysis` | 显著性检验、效应量、多重比较校正 |
| `statsmodels` | 统计建模，线性/广义线性模型，时间序列统计 |

---

## ✍️ 阶段五：论文撰写 & 投稿

| Skill | 用途 |
|---|---|
| `scientific-writing` | 核心写作工具，IMRAD 结构，APA/AMA/Vancouver 引用，CONSORT/STROBE/PRISMA 规范 |
| `venue-templates` | NeurIPS / ICML / CVPR / MICCAI / Nature / IEEE / ACM 投稿 LaTeX 模板与格式要求 |
| `peer-review` | 结构化审稿，也可用于投稿前自查稿件 |
| `scholar-evaluation` | 系统性评分框架，评估论文各维度质量 |
| `markdown-mermaid-writing` | 技术文档写作，含 24 种 Mermaid 图表类型和 9 种文档模板 |
| `latex-posters` | 学术海报（LaTeX，适合会议） |
| `scientific-slides` | 学术报告 / 会议 / 答辩 PPT，支持 PowerPoint 和 LaTeX Beamer |
| `paper-2-web` | 将论文转成交互式网页、视频摘要或会议海报 |
| `pptx-posters` | 基于 HTML/CSS 的海报，可导出为 PDF 或 PPTX |
| `infographics` | 制作信息图，适合科普或社交媒体传播 |

---

## 🔁 推荐核心组合（优先安装）

针对 AI + Medical AI 博士的最小可用工作流：

```
文献端：  literature-review  +  citation-management  +  arxiv-database  +  pubmed-database
数据端：  pyhealth  +  pydicom  +  pathml
模型端：  transformers  +  pytorch-lightning  +  shap
分析端：  scientific-visualization  +  statistical-analysis
写作端：  scientific-writing  +  venue-templates  +  scientific-slides
```

---

## 📌 备注

- 以上 skills 来源于上传的 `skills_summary.md`（共 175 个 skill）
- 部分 skills 需要 API key（如 `rowan`、`perplexity-search`、`research-lookup`）
- `pyhealth` 支持 MIMIC-III/IV 数据集，需要单独申请数据访问权限（PhysioNet）
- `pathml` 支持 160+ 病理切片格式，GPU 加速推荐

---

*整理日期：2026-03-12*
