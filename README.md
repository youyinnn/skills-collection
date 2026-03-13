# Skills Collection — Medical AI PhD Research Workflows

A curated collection of **51 Claude Code skills** organized by research workflow stage, tailored for AI and Medical AI PhD researchers.

## Plugins

| Plugin | Skills | Description |
|---|---|---|
| `literature-and-topic-selection` | 12 | Topic ideation, literature review, academic databases |
| `data-preparation-and-processing` | 12 | Medical imaging, EHR, physiological signals, data processing |
| `model-development-and-experiments` | 11 | Deep learning, GNNs, explainability, time series |
| `results-analysis-and-visualization` | 6 | Plotting, statistical analysis, interactive visualization |
| `paper-writing-and-submission` | 10 | Academic writing, slides, posters, peer review |

## Installation

Add a plugin to your Claude Code project by referencing its path in `.claude/settings.json`:

```json
{
  "plugins": [
    "github:youyinnn/skills-collection/literature-and-topic-selection",
    "github:youyinnn/skills-collection/data-preparation-and-processing",
    "github:youyinnn/skills-collection/model-development-and-experiments",
    "github:youyinnn/skills-collection/results-analysis-and-visualization",
    "github:youyinnn/skills-collection/paper-writing-and-submission"
  ]
}
```

Or install a single plugin if you only need one stage:

```json
{
  "plugins": [
    "github:youyinnn/skills-collection/model-development-and-experiments"
  ]
}
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
| `scientific-visualization` | Domain-specific scientific plots |
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
├── registry.json                          # Plugin registry index
├── literature-and-topic-selection/
│   ├── .claude-plugin/plugin.json
│   └── skills/<skill-name>/
│       ├── SKILL.md                       # Skill definition and usage
│       └── references/                    # Reference documentation
├── data-preparation-and-processing/
├── model-development-and-experiments/
├── results-analysis-and-visualization/
└── paper-writing-and-submission/
```
