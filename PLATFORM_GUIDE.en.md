# Skills Platform Compatibility Guide

This guide clarifies which skills are best used in **Claude Code** vs **Claude.ai**, helping you choose the right tool for each research task.

## Classification Criteria

| Category | Reason |
|---|---|
| **Claude Code only** | Requires code execution, local file I/O, HTTP API calls, or Python libraries |
| **Both platforms** | Writing, analysis, or discussion tasks — Claude Code adds file management; Claude.ai offers fluid conversation |
| **Claude.ai preferred** | Primarily conversational — no file operations needed; Claude.ai's interface is more natural |

---

## Plugin: literature-and-topic-selection

| Skill | Platform | Reason |
|---|---|---|
| `arxiv-database` | **Claude Code only** | Calls arXiv Atom API via HTTP requests |
| `biorxiv-database` | **Claude Code only** | Calls bioRxiv API via HTTP requests |
| `pubmed-database` | **Claude Code only** | Calls NCBI E-utilities REST API via HTTP |
| `openalex-database` | **Claude Code only** | Queries OpenAlex API programmatically |
| `bgpt-paper-search` | **Claude Code only** | Requires `Bash` tool (BGPT MCP server) |
| `pyzotero` | **Claude Code only** | Runs Python `pyzotero` client; reads/writes Zotero library |
| `literature-review` | **Both** | Claude Code: automated multi-database search (PubMed, arXiv, bioRxiv, etc.) + output Markdown/PDF files; Claude.ai: synthesis and drafting only if papers are manually provided — cannot execute database queries |
| `citation-management` | **Both** | Claude Code: generate BibTeX files, batch validation; Claude.ai: verify and discuss specific citations |
| `hypothesis-generation` | **Both** | Claude Code: write hypothesis files, link to data; Claude.ai: conversational hypothesis discussion from observations |
| `research-grants` | **Both** | Claude Code: write and manage grant documents locally; Claude.ai: draft and iterate on proposal text |
| `scientific-critical-thinking` | **Both** | Claude Code: structured evaluation with file output; Claude.ai: real-time discussion of paper methodology |
| `scientific-brainstorming` | **Claude.ai preferred** | Purely conversational — open-ended ideation flows more naturally in chat; Claude Code works but offers no added value |

---

## Plugin: data-preparation-and-processing

| Skill | Platform | Reason |
|---|---|---|
| `pydicom` | **Claude Code only** | Reads/writes DICOM files using Python `pydicom` |
| `histolab` | **Claude Code only** | Processes WSI slide files; runs tile extraction pipelines |
| `pathml` | **Claude Code only** | Full computational pathology toolkit; requires GPU/file access |
| `imaging-data-commons` | **Claude Code only** | Downloads cancer imaging datasets via `idc-index` |
| `neurokit2` | **Claude Code only** | Processes ECG/EEG/EDA signal files with Python |
| `pyhealth` | **Claude Code only** | Trains ML models on EHR datasets (MIMIC, eICU); needs local data |
| `clinicaltrials-database` | **Claude Code only** | Queries ClinicalTrials.gov API v2 |
| `clinvar-database` | **Claude Code only** | Queries NCBI ClinVar via E-utilities API |
| `dask` | **Claude Code only** | Distributed/out-of-core computation; requires Python execution |
| `polars` | **Claude Code only** | In-memory DataFrame processing; requires Python execution |
| `exploratory-data-analysis` | **Claude Code only** | Reads local data files (200+ formats); generates EDA reports |
| `statistical-analysis` | **Both** | Claude Code: run tests on local data files; Claude.ai: guidance on test selection and interpreting results without data |

---

## Plugin: model-development-and-experiments

> All skills in this plugin are **Claude Code only** — they all require running Python code.

| Skill | Reason |
|---|---|
| `pytorch-lightning` | Trains neural networks; requires GPU, local data, file checkpoints |
| `transformers` | Fine-tunes pre-trained models; requires Hugging Face token and compute |
| `torch-geometric` | Trains graph neural networks on graph data |
| `scikit-learn` | Runs ML pipelines on local datasets |
| `shap` | Computes SHAP values from trained models |
| `aeon` | Time series ML on local temporal data |
| `umap-learn` | Dimensionality reduction on local high-dimensional data |
| `pymc` | Bayesian inference with MCMC; computationally intensive |
| `networkx` | Constructs and analyzes graph structures from data |
| `primekg` | Queries PrimeKG knowledge graph programmatically |
| `stable-baselines3` | Trains RL agents in Gymnasium environments |

---

## Plugin: results-analysis-and-visualization

> All visualization skills are **Claude Code only** — they generate figures from local data.

| Skill | Reason |
|---|---|
| `matplotlib` | Generates static figures saved as PNG/PDF/SVG |
| `seaborn` | Statistical plots from pandas DataFrames |
| `plotly` | Interactive visualizations from local data |
| `scientific-visualization` | Publication-ready multi-panel figures (Nature/Cell style) |
| `statsmodels` | Fits statistical models (OLS, GLM, ARIMA) on local data |
| `statistical-analysis` | **Both** — see data-preparation section above |

---

## Plugin: paper-writing-and-submission

| Skill | Platform | Reason |
|---|---|---|
| `latex-posters` | **Claude Code only** | Writes and compiles `.tex` poster files locally |
| `pptx-posters` | **Claude Code only** | Generates HTML/CSS files for export to PPTX/PDF |
| `paper-2-web` | **Claude Code only** | Converts local LaTeX/PDF to web/video/poster formats |
| `infographics` | **Claude Code only** | Generates infographic files via Bash tools |
| `scientific-writing` | **Both** | Claude Code: write/manage full manuscript `.tex`/`.md` files with citations; Claude.ai: draft sections, polish prose, discuss argument structure |
| `venue-templates` | **Both** | Claude Code: apply templates to local manuscript files; Claude.ai: discuss formatting requirements from training knowledge (no web access — may not reflect latest submission guidelines) |
| `peer-review` | **Both** | Claude Code: structured review output to file; Claude.ai: excellent for iterative rebuttal drafting and reviewer comment analysis |
| `scholar-evaluation` | **Both** | Claude Code: structured scoring report to file; Claude.ai: real-time discussion of paper strengths/weaknesses |
| `scientific-slides` | **Both** | Claude Code: generate `.pptx`/`.tex` slide files; Claude.ai: plan structure and content of talks |
| `markdown-mermaid-writing` | **Both** | Claude Code: write and manage local `.md` document files; Claude.ai: draft content and create diagrams in chat |

---

## Summary

| Platform | Skills Count | Typical Tasks |
|---|---|---|
| **Claude Code only** | 37 | Data processing, model training, visualization, database queries, file generation |
| **Both platforms** | 12 | Writing, literature review, statistical guidance, peer review, presentation planning |
| **Claude.ai preferred** | 1 | Open-ended research brainstorming |

> Note: `statistical-analysis` appears in both `data-preparation-and-processing` and `results-analysis-and-visualization` plugins — counted once in the totals above.

### Quick Decision Rule

- **Does the task touch local files, run code, or call an API?** → Claude Code
- **Is it a writing, reviewing, or discussing task?** → Either works; Claude Code if you need file output
- **Is it pure open-ended conversation?** → Claude.ai

---

## Note on Skills in Claude.ai

The skills defined in this repository are loaded only by **Claude Code**. Claude.ai does not read these SKILL.md files.

Two important clarifications:

**For Claude Code only tasks**, the gap is not about precision — it is about what is physically possible. Claude.ai cannot read local DICOM files, cannot execute a real PubMed API call, and cannot run a PyTorch training loop. These are hard environment limitations, not skill-file limitations.

**For Both platforms tasks**, this guide compares "Claude Code with skills loaded" against "Claude.ai without any skill context". If you manually provide the relevant content to Claude.ai (e.g., paste a paper, paste reviewer comments, paste a data summary), the underlying model is identical — output quality will be equivalent. The real difference is **automation and file system access**, not model capability.

In short: use Claude Code when the task touches your local environment; use either platform when the task is analysis, writing, or discussion.
