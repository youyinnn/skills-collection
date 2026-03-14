# Skills Collection — Medical AI PhD Research Workflows

A curated collection of **50 Claude Code skills** organized by research workflow stage, tailored for AI and Medical AI PhD researchers.

## Documentation

| File | Description |
|---|---|
| [PLATFORM_GUIDE.en.md](PLATFORM_GUIDE.en.md) | Which skills work in Claude Code vs Claude.ai |
| [PLATFORM_GUIDE.zh.md](PLATFORM_GUIDE.zh.md) | 平台兼容性指南（中文） |
| [recommended_skills_for_medical_ai_phd.en.md](recommended_skills_for_medical_ai_phd.en.md) | Recommended skills by research stage (English) |
| [recommended_skills_for_medical_ai_phd.zh.md](recommended_skills_for_medical_ai_phd.zh.md) | 按研究阶段推荐的 skills（中文） |

## Plugins

| Plugin | Skills | Description |
|---|---|---|
| `literature-and-topic-selection` | 12 | Topic ideation, literature review, academic databases |
| `data-preparation-and-processing` | 12 | Medical imaging, EHR, physiological signals, data processing |
| `model-development-and-experiments` | 11 | Deep learning, GNNs, explainability, time series |
| `results-analysis-and-visualization` | 6 | Plotting, statistical analysis, interactive visualization |
| `paper-writing-and-submission` | 10 | Academic writing, slides, posters, peer review |

## Installation

### Step 1 — Add this repository as a marketplace

```
/plugin marketplace add youyinnn/skills-collection
```

### Step 2 — Install the plugins you need

```
/plugin install literature-and-topic-selection@skills-collection
/plugin install data-preparation-and-processing@skills-collection
/plugin install model-development-and-experiments@skills-collection
/plugin install results-analysis-and-visualization@skills-collection
/plugin install paper-writing-and-submission@skills-collection
```

You can install only the plugins relevant to your current work.

### Recommended minimal install for Medical AI PhD

```
/plugin install literature-and-topic-selection@skills-collection
/plugin install data-preparation-and-processing@skills-collection
/plugin install model-development-and-experiments@skills-collection
/plugin install results-analysis-and-visualization@skills-collection
/plugin install paper-writing-and-submission@skills-collection
```

## Skills by Stage

### Stage 1 — Literature & Topic Selection

| Skill | Purpose |
|---|---|
| `scientific-brainstorming` | Research ideation, finding gaps, cross-disciplinary exploration |
| `hypothesis-generation` | Derive testable hypotheses from data or literature |
| `literature-review` | Systematic review across PubMed / arXiv / bioRxiv |
| `scientific-critical-thinking` | Evaluate study design, identify bias, evidence grading (GRADE) |
| `citation-management` | Reference management workflows |
| `pyzotero` | Programmatic Zotero library management |
| `arxiv-database` | Search arXiv preprints (CS / AI / Statistics) |
| `pubmed-database` | PubMed REST API with Boolean / MeSH queries |
| `biorxiv-database` | Search bioRxiv life science preprints |
| `openalex-database` | Query 240M+ scholarly works, citation analysis |
| `bgpt-paper-search` | Extract structured experiment data from full-text papers |
| `research-grants` | NSF / NIH / DARPA grant writing |

### Stage 2 — Data Preparation & Processing

| Skill | Purpose |
|---|---|
| `pydicom` | Read/write DICOM files (CT / MRI / X-Ray / Ultrasound) |
| `pathml` | Computational pathology WSI analysis, 160+ formats |
| `histolab` | Lightweight H&E tile extraction |
| `imaging-data-commons` | Access NIH public medical imaging datasets |
| `pyhealth` | Medical AI toolkit: MIMIC-III/IV, eICU, OMOP |
| `clinicaltrials-database` | Query ClinicalTrials.gov |
| `clinvar-database` | Query ClinVar genetic variants database |
| `neurokit2` | Physiological signal processing: ECG / EEG / EDA / PPG |
| `polars` | Fast in-memory dataframe processing |
| `dask` | Distributed computing for larger-than-RAM workflows |
| `exploratory-data-analysis` | EDA reports for scientific data formats |
| `statistical-analysis` | Statistical testing and modeling |

### Stage 3 — Model Development & Experiments

| Skill | Purpose |
|---|---|
| `pytorch-lightning` | Structured PyTorch training with logging and checkpointing |
| `transformers` | HuggingFace transformers for NLP and vision tasks |
| `torch-geometric` | Graph neural networks for molecular / biomedical data |
| `scikit-learn` | Classical ML: classification, regression, clustering |
| `pymc` | Bayesian statistical modeling |
| `shap` | Model explainability via Shapley values |
| `umap-learn` | Dimensionality reduction and embedding visualization |
| `aeon` | Time series classification and regression |
| `networkx` | Graph analysis and network science |
| `primekg` | Biomedical knowledge graph for drug discovery |
| `stable-baselines3` | Reinforcement learning algorithms |

### Stage 4 — Results Analysis & Visualization

| Skill | Purpose |
|---|---|
| `matplotlib` | Publication-quality static figures |
| `seaborn` | Statistical data visualization |
| `plotly` | Interactive plots and dashboards |
| `scientific-visualization` | Publication-ready multi-panel figures (Nature / Cell / IEEE style) |
| `statistical-analysis` | Statistical tests, power analysis, reporting |
| `statsmodels` | Regression, time series, and econometric models |

### Stage 5 — Paper Writing & Submission

| Skill | Purpose |
|---|---|
| `scientific-writing` | Academic paper drafting and revision |
| `venue-templates` | NeurIPS / ICML / MICCAI / Nature formatting |
| `latex-posters` | Conference poster design in LaTeX |
| `pptx-posters` | Conference poster design in PowerPoint |
| `scientific-slides` | Presentation slides for research talks |
| `infographics` | Visual abstract and graphical summary creation |
| `markdown-mermaid-writing` | Diagrams and flowcharts in Markdown |
| `paper-2-web` | Convert papers to web-friendly formats |
| `peer-review` | Structured peer review writing |
| `scholar-evaluation` | Evaluate research quality and impact |

## Repository Structure

```
skills-collection/
├── .claude-plugin/
│   └── marketplace.json               # Marketplace definition
├── registry.json                      # Plugin registry index
├── PLATFORM_GUIDE.en.md               # Platform compatibility guide (English)
├── PLATFORM_GUIDE.zh.md               # Platform compatibility guide (Chinese)
├── recommended_skills_for_medical_ai_phd.en.md
├── recommended_skills_for_medical_ai_phd.zh.md
└── plugins/
    ├── literature-and-topic-selection/
    │   ├── .claude-plugin/plugin.json
    │   └── skills/<skill-name>/
    │       ├── SKILL.md               # Skill definition and usage
    │       └── references/            # Reference documentation
    ├── data-preparation-and-processing/
    ├── model-development-and-experiments/
    ├── results-analysis-and-visualization/
    └── paper-writing-and-submission/
```
