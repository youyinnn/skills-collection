---
name: research-project-framework
description: Working framework for a user and an AI assistant running a paper-type research project together, with templates and scripts. Covers project setup (folders, records, task cards, Obsidian dashboard, edit-time checks), collaboration rules, the research workflow (setting the direction, literature, experiments, annotation, replication package) and the writing workflow (measuring sample papers of the target venue, drafting, optimizing, simulated review, checks before submission). Use it whenever the user starts a new research or paper project, sets up a project folder or vault, asks how to organize logs, decisions or tasks, asks how to draft, optimize, check or submit a section, or the project turns out to have human participants, a parent project, co-authors or Overleaf, a journal target, a tool to evaluate, or less than a month to the deadline, even if the framework is not named. 开新研究项目、搭项目库、开张、写某节、优化某节、检查、提交、投稿前检查时用。
license: MIT license
metadata:
    skill-author: Jun
---

# 研究项目框架

一套给「用户 + AI 助手」合作做论文型研究项目的做法,管三件事:项目怎么管、研究怎么做、论文怎么写。本文件是入口:开新项目的六个问题和开张清单写在这里,其余做法在 `references/` 里,用到哪份读哪份。

**路径约定:** 本 skill 里写的 `references/`、`assets/` 开头的路径都相对于本 skill 的根目录;`scripts/` 既指本 skill 的脚本,也指开张时拷进项目的同名目录;`tracking/`、`records/` 等指项目里的目录。

**角色:** 用户(项目负责人,论文作者,决定由他做);导师;合作者(有的话,分工写进 CLAUDE.md,见 `references/project-types/collaborators-overleaf.md`);助手(AI 编码与写作助手,在用户的电脑上读写文件、跑脚本、提交代码)。

## 每轮都要守的规则放在项目的 CLAUDE.md

本 skill 只在用到时才读进来,会话被压缩以后它就不一定还在上下文里。所以每轮都要守的规则(回复用什么语言、什么时候先问、只在用户说「提交」时提交、「检查」只报告不改)不能只靠本 skill:开张时它们随 `assets/CLAUDE.template.md` 拷成项目的 `CLAUDE.md`,每个会话开头都会读到。项目里要改这类规则,改项目的 `CLAUDE.md`。

## 什么情况读哪份

| 情况 | 读 |
|---|---|
| 开新项目 | 本文件下面的「先答六个问题」与「开张清单」 |
| 项目有人类参与者、从已有项目派生、有合作者或在 Overleaf、投期刊、是工具论文、离截稿不到一个月 | `references/project-types/` 里对应的那一份 |
| 记录各管什么、状态怎么记、目录、几个会话并行、提交、与导师 | `references/project-management.md` |
| 什么时候先问、什么时候直接改、什么时候只报告;东西怎么给用户看;回答的分寸;边界 | `references/collaboration.md` |
| 定方向的顺序、八种判断错误、文献、实验与算力、标注、复现包 | `references/research-workflow.md` |
| 量范文、起稿一节、优化一节、压尾巴、逐句要理由、模拟评审、引用核查、图表、投稿前检查 | `references/writing-workflow.md`;开张后读项目里按项目改过的 `tracking/Writing-workflow.md` |
| 出了错,想找管它的规则 | `references/lessons-index.md` |
| 工作语言不是中文 | `references/glossary-zh-en.md` |
| 在对话里展示改动 | `assets/change-widget.html` 的样式,规则见 `references/collaboration.md` 第 2 节 |

`references/` 里前五份(project-management、collaboration、research-workflow、writing-workflow、lessons-index)是核心五份,所有项目都适用。`references/project-types/` 里的六份补充只在对应的问题答「是」时用,冲突处优先于核心五份。

## 先答六个问题

开张时先答这六个问题,答案写进 CLAUDE.md 的「项目类型」。答「是」的,开张前先读对应的补充文件,它会改开张清单里的几步。

| 问题 | 答「是」时读 | 开张时要多做的事(例子) |
|---|---|---|
| 1. 有没有人类参与者(访谈、问卷、用户研究、请人标注)? | `references/project-types/human-participants.md` | 先查伦理审批来不来得及;身份数据放项目库外 |
| 2. 是不是从已有项目派生,或把已有论文扩展成新稿? | `references/project-types/derived-project.md` | 沿用母项目的代码仓;CLAUDE.md 登记母项目、母论文状态和锁定的提交 |
| 3. 有没有合作者直接改论文,或论文在 Overleaf 上编译? | `references/project-types/collaborators-overleaf.md` | 论文仓改为克隆;定好谁推送、编译结果放哪 |
| 4. 投的是期刊吗? | `references/project-types/journal-revision.md` | 「已确立的事实」写审稿方式与扩展稿政策,不写截稿日 |
| 5. 是不是提出工具或方法、要和基线比较的论文? | `references/project-types/tool-paper.md` | 写下基线、被测对象和测量规程;准备 artifact evaluation |
| 6. 离截稿不到一个月吗? | `references/project-types/tight-deadline.md` | 按剩余天数定下做哪些步、省哪些步 |

工作环境不是 macOS 加本地 LaTeX 加 Obsidian,或者工作语言不是中文的,另看本文件末尾「换环境」一节。

## 开张清单

按顺序做,每一步用到的文件前面都已备好。

1. 答上面的六个问题,答案先记在对话里,第 5 步写进 CLAUDE.md;答「是」的补充文件先读,它们会改下面几步的做法。
2. 建项目文件夹与目录:`inputs/`(`papers/`)、`derived/`(`papers_marker/`)、`records/`(`log/`、`protocols/`、`findings/`、`plans/`、`supervisor/`,导师意见逐字放 `supervisor/`)、`tracking/`(`tasks/`、`templates/`)、`work/`(`proposals/`)、`archive/`、`scripts/`。每个目录里放一个空的 `.gitkeep`:git 不记空目录,不放的话换一台电脑克隆下来这些目录就没了,检查会报一串路径不存在。为什么这样分见 `references/project-management.md` 第 3 节。有人类参与者的,身份数据不放进这里任何一个目录。
3. 建 `.gitignore`,至少写上 `derived/repo_state.md`、`__pycache__/`、`.pytest_cache/`;用 Obsidian 的,再写上 `.obsidian/workspace.json`、`.obsidian/workspace-mobile.json`(每台电脑自己的窗口与标签页状态,一点就变)和 `.obsidian/plugins/`(插件代码与插件设置,换电脑时按 `assets/obsidian/Setup.md` 第 2 步重装)。要收范文 PDF 的,再写上 `inputs/papers/**/*.pdf`:只排除 PDF 文件,目录和里面的 `.gitkeep` 照样进库;训练日志、身份数据这类整个目录都不进库的,写目录名。
4. 把本 skill 的 `scripts/` 整个拷成项目的 `scripts/`。`scripts/config.py` 开张时只填 `VENUE`:目标场地定了就填它的简称(例如 ICSE),范文 PDF 以后放进 `inputs/papers/<VENUE>/`;没定就留空;`PAPER_SECTION_DIR` 等建了论文仓再填,`AGENT_RUNS_DIR` 等有了运行日志再填,`GROUP_ORDER` 等写完论文类型编码本再填,其余用默认值。用你跑脚本的那个 Python 装 pytest(`python -m pip install pytest`),跑一遍测试:`python -m pytest scripts/tests -q`。这时风险表还没拷进来,风险表那一条测试会跳过,这是正常的;第 5 步拷进来以后全部通过。
5. 照下面「要拷进项目的文件」表把文件拷进项目,把六问答案写进 `CLAUDE.md` 的「项目类型」,再填项目自己的信息,`CLAUDE.md`、`Home.md`、`tracking/File-map.md` 里都有:项目名、论文标题、目标场地与截稿、工作规则第 7 条的仓库路径与环境名、已确立的事实。还不知道的写成 `___`,不要编。只有两类不填:铁律 3 的「本次判断标准出自:___」是规则原文;`<年月>`、`<日期>_<会话短名>` 是文件名格式。六问答「否」的,删掉那一行后面括号里的说明;投会议的删掉期刊那半句,投期刊的删掉会议那半句。两个钩子只用 Python 自带的库,`.claude/settings.json` 里的 `python3` 指向哪个 Python 都行。
6. 跑 `python scripts/repo_check.py --fix` 生成文件表的数量块,再跑 `python scripts/repo_check.py`,应当零问题。之后每加一张卡、一篇日志,数量块都会变,检查会提示再跑 `--fix`。
7. 钩子自检:`.claude/settings.json` 里的两个编辑后检查,只在以新项目为根目录启动的会话里生效,开张这个会话里不会自动跑。在项目里开第一个会话时自检一次:在 CLAUDE.md 里写一个不存在的反引号路径(如 `records/no-such-file.md`;检查只认由英文字母、数字与 `_.-/` 组成、第一层目录写在 `config.py` 的 `TOPDIRS` 里的路径),确认 repo_check 报出来;在 `work/proposals/` 下建一个英文的 `.md` 文件(它只扫 `.md`),写一句带 delve 的话,确认 humanizer_scan 报出来;再把两处删掉。
8. 用 Obsidian 的,照 `assets/obsidian/Setup.md` 做,其中拷配置、生成派生数据两步前面已经做过,`.obsidian/app.json` 的 `userIgnoreFilters` 按项目的大目录改(Setup 第 1 步后半);不用的见「换环境」。
9. 建仓库:项目库 `git init -b main`;论文仓按目标场地的模板新建(主文件在根目录,章节、表、图各一个文件夹,用 `\input` 引入),有合作者或在 Overleaf 上的改为克隆;代码仓只在有代码时建,派生项目沿用母项目的代码仓、开新分支。本机多个会话同时编译时,论文仓要有编译锁,锁文件不进仓。提交只在用户说时做。
10. 开张会话照常写会话日志(格式照 `tracking/templates/log.md`),写完再跑一次 `python scripts/repo_check.py --fix`。六问答案是项目的事实,只写在 CLAUDE.md 的「项目类型」。开张时用户说定的事(目标场地、用不用 Obsidian、建哪几个仓库)是决定,照决定表的规则各记一行(谁、哪天、原话);其中目标场地的结论同时写进 CLAUDE.md「已确立的事实」,那里只写结论。
11. 写第一节之前,先在目标场地的论文上量这一节(`references/writing-workflow.md` 第 1 节)。目标场地不是 FSE 时(现有切法按 FSE 定),量之前先按那一节第 2 步改切法、对齐;开张时范文还没收,先记成一张任务卡。
12. 方向没定的话,先按 `references/research-workflow.md` 第 1 节的顺序定,把定下的写进 CLAUDE.md 的「已确立的事实」。

### 要拷进项目的文件

| 文件 | 拷到 |
|---|---|
| `assets/CLAUDE.template.md` | 项目根目录,改名为 `CLAUDE.md`(模板不叫 CLAUDE.md,免得在本 skill 的文件夹里被当成指令读进去) |
| `assets/task-card.md` | `tracking/templates/task-card.md`;每有一项任务,从它复制一张到 `tracking/tasks/<卡号>.md`;卡号是大写字母加数字(A1);同时在看板对应栏加一行 `- [ ] [[A1]] 一句话标题`,否则编辑后检查会报卡片不在看板上 |
| `assets/log.md` | `tracking/templates/log.md`;每个会话照它写自己的日志 |
| `assets/change-widget.html` | `tracking/templates/change-widget.html`;助手在对话里展示改动时照它的样式画 |
| `assets/Decisions.md` | `records/Decisions.md` |
| `assets/Risks.md` | `tracking/Risks.md` |
| `assets/Board.md` | `tracking/Board.md`(Obsidian 看板插件的格式) |
| `assets/File-map.md` | `tracking/File-map.md`;数量块在第 6 步生成 |
| `references/writing-workflow.md` | `tracking/Writing-workflow.md`,原样拷;以后项目里的写作做法有变,改这份副本。离截稿不到一个月的,省哪些步按 `references/project-types/tight-deadline.md` 和用户定下,写进 CLAUDE.md「当前状态」,副本不删步 |
| `assets/obsidian/Home.md` | 项目根目录 `Home.md`(仪表盘);阶段的显示名填在里面的 `PH` 表 |
| `assets/obsidian/Index.md`、`assets/obsidian/Setup.md` | `tracking/` |
| `assets/obsidian/obsidian-config/` | 项目根目录 `.obsidian/` |
| `assets/settings.json` | `.claude/settings.json`;钩子命令用 `${CLAUDE_PROJECT_DIR}` 指项目根目录,不用改,克隆到别的位置也能用 |

## scripts/

拷进项目后,两个钩子、PDF 转换、量草稿的 `measure_tex_section.py`、运行台账,填好 `config.py` 就能用。

**量范文的那一套(`*_stats.py`、`by_type.py`,以及量草稿时拿范文作对照的 `voice_stats.py`)每换一个目标场地,都要先改切法、再对齐,对齐通过才能拿来量。** 原因:脚本靠章节标题把每篇论文切成引言、相关工作等各节,再按节名判断这一节算哪类,而各场地的写法不同。现有的规则是按 FSE 的写法定的(章节标题写成「1 Introduction」);在另外 21 个场地的 37 篇论文上试过,标题写成「1. INTRODUCTION」「I. INTRODUCTION」「Introduction」或没有引言标题的 13 篇都切不出(脚本会列出并跳过),切得出的也有认错节的。怎么改、怎么对齐见 `references/writing-workflow.md` 第 1 节第 2 步。

| 脚本 | 做什么 | 怎么跑 |
|---|---|---|
| `config.py` | 所有随项目变的设置,包括看板栏名与风险表的关键词 | 拷进来先填 |
| `repo_check.py` | 编辑后钩子:核记录与磁盘(反引号里的路径在不在、wikilink 有没有目标、看板与卡片状态、Obsidian 配置、风险表、文件表的数量块),生成仪表盘读的 `derived/repo_state.md`;只报不改。路径与 wikilink 只核 CLAUDE.md、Home.md 与 `tracking/`、`scripts/`、`derived/` 下的文件;`records/`、`archive/` 是历史,里面的旧路径不核也不改 | 钩子自动跑;`--fix` 重写数量块 |
| `humanizer_scan.py` | 编辑后钩子:扫提案等英文文档里的 AI 腔词表命中,只报不改;引用块(以 `>` 开头的行)不扫 | 钩子自动跑 |
| `convert_pdfs_marker.py` | 把 `inputs/papers/<场地>/` 的 PDF 转成 `derived/papers_marker/<场地>/` 的 markdown,已转的跳过 | `python scripts/convert_pdfs_marker.py <场地>`(要装 marker;macOS 上还要 llama.cpp) |
| `abstract_stats.py`、`intro_stats.py`、`relwork_stats.py`、`background_stats.py`、`methodology_stats.py`、`results_stats.py`、`threats_stats.py`、`discussion_stats.py`、`conclusion_stats.py` | 在范文上量各节:有没有、放哪、长度、段数、句长、引用密度、公式与图表、单元主题、标记句;输出到 `derived/analysis/writing_patterns/` | `python scripts/<节>_stats.py`;除结论节外都有 `--dump`,打印切出来的文本供核对与人工标注 |
| `by_type.py` | 按论文类型分组重算上面各表的中位数与计数 | 先有标签文件(每篇一行:`paper`、`group`),各节都跑过 |
| `voice_stats.py` | 草稿某一节的十项声音特征,对照范文同节的中位与四分位 | `python scripts/voice_stats.py --section intro <草稿.tex>` |
| `measure_tex_section.py` | 草稿某一节的词数、句数、句长、40 词以上的句子、引用密度、公式、图表 | `python scripts/measure_tex_section.py <草稿.tex> [--long]` |
| `check_template_quotes.py` | 模板文件里的每条范文例句,逐字对照范文 markdown 核对 | `python scripts/check_template_quotes.py <模板.md>` |
| `agent_runs_ledger.py` | LLM 调用实验的运行台账,每份 JSONL 日志一行(日志字段要求写在文件开头) | `python scripts/agent_runs_ledger.py` |
| `tests/` | 以上脚本的测试 | `python -m pytest scripts/tests -q` |

## 换环境

- **Windows:** 钩子命令(`.claude/settings.json`)和文中的 `python3` 换成 `python` 或 `py -3`;`config.py` 里的绝对路径用正斜杠(`C:/Users/...`)或原始字符串(`r"C:\Users\..."`);脚本已改为按 UTF-8 读写文件和输出。这套脚本只在 macOS 上实跑过,Windows 上的写法是照代码推断的;第一次用,先故意造一处不符,确认两个钩子都会报出来。
- **本机不编译(论文在 Overleaf):** 见 `references/project-types/collaborators-overleaf.md` 第 2 节。
- **不用 Obsidian:** 仪表盘、看板、`.obsidian` 配置不用拷。任务状态改记在一张 markdown 表或 GitHub Issues 里时,「任务状态只记在卡片」这条要一起改的有:`references/project-management.md` 第 1 节的表与第 2 节第一条、CLAUDE.md 工作规则第 2 条、`assets/task-card.md` 末尾的说明;只留一个状态源。Issues 是协作者看得见的,写明助手只在用户点名时才改。
- **工作语言不是中文:** 见 `references/glossary-zh-en.md`。
