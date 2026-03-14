# Recommended Skills — AI / Medical AI PhD Research Workflow

> Selected from 175 skills, curated for AI and Medical AI research, organized by research workflow stage.

---

## 📚 Stage 1: Topic Selection & Literature Research

| Skill | Purpose |
|---|---|
| `scientific-brainstorming` | Creative research ideation, identifying research gaps, exploring interdisciplinary connections |
| `hypothesis-generation` | Formulate testable scientific hypotheses from data or literature |
| `literature-review` | Systematic literature review across PubMed / arXiv / bioRxiv and more; outputs cited Markdown/PDF documents |
| `scientific-critical-thinking` | Evaluate experimental design validity, identify biases and confounders, evidence grading (GRADE/Cochrane) |
| `citation-management` | Reference management — search, validate, and generate BibTeX entries |
| `pyzotero` | Programmatic Zotero integration — manage libraries, export citations, upload PDF attachments |
| `arxiv-database` | Search arXiv preprints (CS / AI / Statistics) |
| `pubmed-database` | Direct PubMed REST API access with advanced Boolean/MeSH queries |
| `biorxiv-database` | Search bioRxiv life sciences preprints |
| `openalex-database` | Query 240M+ scholarly works; citation analysis and research trend tracking |
| `bgpt-paper-search` | Extract structured experimental data from full-text papers (methods, results, sample sizes) |
| `research-grants` | Write competitive grant proposals for NSF / NIH / DARPA / NSTC |

---

## 🗄️ Stage 2: Data Preparation & Processing

### Medical Imaging
| Skill | Purpose |
|---|---|
| `pydicom` | Read/write DICOM files (CT / MRI / X-ray / Ultrasound); extract pixel data and metadata |
| `pathml` | Computational pathology WSI analysis; multiplexed immunofluorescence, tissue segmentation, 160+ formats |
| `histolab` | Lightweight H&E tile extraction for simple WSI preprocessing pipelines |
| `imaging-data-commons` | Access NCI public cancer imaging datasets (radiology + pathology) |

### Clinical & EHR Data
| Skill | Purpose |
|---|---|
| `pyhealth` | Comprehensive healthcare AI toolkit; MIMIC-III/IV, eICU, OMOP; clinical prediction tasks (mortality, readmission, drug recommendation) |
| `clinicaltrials-database` | Query ClinicalTrials.gov API v2 for trial data |
| `clinvar-database` | Query NCBI ClinVar for variant clinical significance and pathogenicity |

### Physiological Signals
| Skill | Purpose |
|---|---|
| `neurokit2` | Biosignal processing: ECG / EEG / EDA / PPG / EMG; HRV analysis, event-related potentials |

### General Data Processing
| Skill | Purpose |
|---|---|
| `polars` | Fast in-memory DataFrame processing (high-speed pandas alternative, suited for 1–100GB) |
| `exploratory-data-analysis` | Automated EDA across 200+ scientific file formats; data quality and distribution reports |
| `statistical-analysis` | Statistical tests, regression analysis, APA-formatted reporting |
| `dask` | Out-of-core parallel computation for datasets exceeding RAM |

---

## 🤖 Stage 3: Model Development & Experiments

### Core Deep Learning
| Skill | Purpose |
|---|---|
| `transformers` | HuggingFace Transformers; text / image / audio / multimodal tasks; fine-tuning pre-trained models |
| `pytorch-lightning` | Structured PyTorch training; multi-GPU / TPU, distributed training (DDP / FSDP / DeepSpeed), W&B logging |
| `scikit-learn` | Classical ML — classification, regression, clustering, model evaluation, pipelines |

### Graph Neural Networks
| Skill | Purpose |
|---|---|
| `torch-geometric` | GNNs: node/graph classification, link prediction, GCN / GAT / GraphSAGE; suited for medical knowledge graphs |
| `networkx` | Complex network analysis — biological networks, citation networks, graph algorithms |
| `primekg` | Query PrimeKG precision medicine knowledge graph (gene-drug-disease-phenotype associations) |

### Explainability & Uncertainty
| Skill | Purpose |
|---|---|
| `shap` | Model interpretability (XAI); feature importance analysis — essential for medical AI papers |
| `pymc` | Bayesian modeling, uncertainty quantification, hierarchical models |

### Time Series & Reinforcement Learning
| Skill | Purpose |
|---|---|
| `aeon` | Time series ML: classification, forecasting, anomaly detection (suited for physiological signals, ICU data) |
| `stable-baselines3` | Production-ready RL algorithms (PPO, SAC, DQN) with scikit-learn-like API |

### Dimensionality Reduction & Clustering
| Skill | Purpose |
|---|---|
| `umap-learn` | High-dimensional data dimensionality reduction for 2D/3D visualization; integrates with HDBSCAN clustering |

---

## 📊 Stage 4: Results Analysis & Visualization

| Skill | Purpose |
|---|---|
| `scientific-visualization` | Publication-ready multi-panel figures; Nature / Science / Cell / IEEE formatting; colorblind-safe palettes |
| `matplotlib` | Fully customizable static figures; export to PNG / PDF / SVG |
| `seaborn` | Quick statistical plots — distributions, heatmaps, regression plots |
| `plotly` | Interactive visualizations for EDA and presentations |
| `statistical-analysis` | Significance testing, effect sizes, multiple comparison corrections |
| `statsmodels` | Statistical modeling — OLS, GLM, ARIMA; detailed diagnostics and inference tables |

---

## ✍️ Stage 5: Paper Writing & Submission

| Skill | Purpose |
|---|---|
| `scientific-writing` | Core writing tool; IMRAD structure; APA/AMA/Vancouver citations; CONSORT/STROBE/PRISMA compliance |
| `venue-templates` | LaTeX templates and formatting requirements for NeurIPS / ICML / CVPR / MICCAI / Nature / IEEE / ACM |
| `peer-review` | Structured manuscript review; also useful for pre-submission self-assessment |
| `scholar-evaluation` | Systematic scoring framework for evaluating paper quality across multiple dimensions |
| `markdown-mermaid-writing` | Technical documentation with 24 Mermaid diagram types and 9 document templates |
| `latex-posters` | Academic conference posters in LaTeX (beamerposter / tikzposter) |
| `scientific-slides` | Research talk slides for conferences, seminars, and thesis defense; PowerPoint and LaTeX Beamer |
| `paper-2-web` | Convert papers to interactive websites, video abstracts, or conference posters |
| `pptx-posters` | HTML/CSS-based posters exportable to PDF or PPTX |
| `infographics` | Create infographics for science communication and social media dissemination |

---

## 🔁 Recommended Core Combination (Install First)

Minimal viable workflow for AI + Medical AI PhD:

```
Literature:    literature-review  +  citation-management  +  arxiv-database  +  pubmed-database
Data:          pyhealth  +  pydicom  +  pathml
Modeling:      transformers  +  pytorch-lightning  +  shap
Analysis:      scientific-visualization  +  statistical-analysis
Writing:       scientific-writing  +  venue-templates  +  scientific-slides
```

---

## 📌 Notes

- Skills listed here are selected from `skills_summary.md` (175 skills total)
- Some skills require API keys (e.g., `rowan`, `perplexity-search`, `research-lookup`)
- `pyhealth` supports MIMIC-III/IV datasets — requires separate data access application via PhysioNet
- `pathml` supports 160+ pathology slide formats; GPU acceleration recommended

---

*Last updated: 2026-03-12*
