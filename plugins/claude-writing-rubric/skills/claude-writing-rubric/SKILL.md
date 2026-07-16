---
name: claude-writing-rubric
description: Bilingual (EN/ZH) rubric for scientific paper writing sessions covering workflow/communication rules, LaTeX editing conventions, and prose style. These rules were accumulated from user feedback in prior sessions and apply to all work in the repository unless the user overrides them explicitly. Use when editing LaTeX manuscript files, writing or translating paper sections, or any interaction in a scientific writing project.
license: MIT license
metadata:
    skill-author: Jun
---

# Claude Writing Rubric

These rules were accumulated from user feedback in prior sessions on this project. 这些规则是在本项目此前的多次会话中，根据用户反馈逐步积累形成的。They apply to all work in this repository unless the user overrides them explicitly. 除非用户明确另行说明，否则这些规则适用于本仓库的所有工作。

## Workflow and Communication

- Confirm before editing: before editing any file, state which file, what will change, and why. 编辑前确认：在编辑任何文件之前，先说明是哪个文件、要改什么、为什么改。Only proceed after the user approves. 只有在用户同意之后才能继续操作。Do not batch-announce multiple edits and then proceed without waiting for confirmation on each batch. 不要一次性宣布多处编辑后就直接执行，每一批修改都要等待用户确认。
- Language: reply only in English and Chinese. 语言：只用英文和中文回复。Never use Korean under any circumstances. 任何情况下都不能使用韩文。
- Token efficiency: do not re-read a file immediately after editing it (Edit/Write confirms success, file state is tracked). token 效率：编辑完文件后不要立即重新读取（Edit/Write 工具已确认成功，文件状态是被跟踪的）。Read only the relevant offset/section of large files, not the whole file. 对于大文件，只读取相关的片段或区间，不要通读全文。Keep analysis responses direct, lead with the conclusion, skip context recaps and background the user already knows. 分析类回复要直接，先给结论，省略用户已经知道的背景铺垫和上下文回顾。
- Never compile LaTeX: never run pdflatex, latexmk, or any LaTeX compilation command. 永远不编译 LaTeX：不要运行 pdflatex、latexmk 或任何 LaTeX 编译命令。The sandbox is missing packages (e.g. algorithm.sty) and compilation always fails misleadingly. 沙盒环境缺少部分宏包（例如 algorithm.sty），编译总会失败并给出误导性的错误信息。LaTeX edits do not need compilation to verify; check structure/braces via Python if needed. LaTeX 的修改不需要通过编译来验证，如有需要可用 Python 检查括号配对等结构问题。
- Tex is the source of truth: for any discussion or analysis of the method, ground every claim in the latest manuscript `sections/*.tex`. Tex 是唯一权威来源：对方法的任何讨论或分析，都要以最新的正文 `sections/*.tex` 为依据。Code may only corroborate, never serve as the basis for a conclusion. 代码只能作为佐证，不能作为下结论的依据。If code and text diverge, the text wins for any stated conclusion, and the divergence should be flagged rather than reasoned from code. 如果代码和正文不一致，任何结论都以正文为准，并应指出这一分歧，而不是依据代码推理。

## LaTeX Editing Rules

- Line breaks: break a line only after a sentence's period. 断行规则：只能在一句话的句号之后换行。A complete sentence stays on one line, never wrapped mid-sentence. 一个完整的句子要保持在同一行，绝不能在句子中间换行。One sentence per line, no hard-wrapping to a column width. 一行一句，不要按固定列宽强制换行。
- Sentence splitting: split a connective-joined sentence (but, so, and, though, or an appositive) at the connective only when the sentence is too long to read cleanly. 拆句规则：只有当一个由连接词（but、so、and、though）或同位语连接的句子过长、不便阅读时，才在连接处拆分。Keep it inline when the sentence is already short. 如果句子本身已经够短，就保持连接词在句内，不拆分。When a split is warranted, convert the inner connective into a sentence-initial transition (", but" to "However,", ", so" to "Hence,") with an explicit subject for the new sentence, and preserve the original meaning and contrast/causal logic. 需要拆分时，把句内连接词转成句首过渡词（", but" 改为 "However,"，", so" 改为 "Hence,"），给新句子一个明确的主语，并保持原有的转折或因果逻辑不变。
- Cross-references: use manual prefix plus `\ref`, i.e. `Section~\ref{}`, `Table~\ref{}`, `Figure~\ref{}`, `Algorithm~\ref{}`. 交叉引用：使用手动前缀加 `\ref` 的形式，即 `Section~\ref{}`、`Table~\ref{}`、`Figure~\ref{}`、`Algorithm~\ref{}`。Never use `\cref{}`, cleveref is not loaded and it breaks compilation. 绝不使用 `\cref{}`，因为没有加载 cleveref 宏包，用了会导致编译失败。
- Deliberate formatting exception: this paper's existing `\item` lists (contributions enumerate, experiment overview itemize) and run-in bold headers (related work topic headers, method phase headers, inline term emphasis) are intentional authorial choices already reviewed and confirmed by the user. 有意保留的格式例外：本文中已有的 `\item` 列表（贡献点的 enumerate、实验概览的 itemize）以及行内加粗小标题（相关工作的主题标题、方法阶段标题、行内术语强调）都是作者刻意为之，已经过用户审阅确认。Do not flag them as style violations. 不要把这些标记为风格违规。This exception does not extend to new content, which should still follow the general "avoid \item, avoid bold" guidance below. 这一例外不适用于新增内容，新内容仍应遵循下面"尽量不用 \item、尽量不加粗"的一般原则。

## Writing Style Rules

- Punctuation: a colon in prose is allowed only when it introduces an enumeration or list. 标点规则：正文中的冒号只有在引出列举或清单时才允许使用。A colon introducing an explanation, elaboration, or result is not allowed, use a comma plus a relative clause (meaning/where/which) or a new sentence instead. 不允许用冒号引出解释、阐述或结果，应改用逗号加从句（meaning/where/which）或另起一句。Never use semicolons in running prose, only inside LaTeX list environments. 正文中绝不使用分号，分号只能出现在 LaTeX 的列表环境中。
- Visual and typesetting: avoid bold, italics, or quotation marks for emphasis. 视觉与排版：避免使用加粗、斜体或引号来强调。Avoid em dashes, use a subordinate clause or appositive instead. 避免使用破折号，改用从句或同位语替代。Keep LaTeX source clean with no meaningless formatting decoration. 保持 LaTeX 源码干净，不加无意义的格式修饰。Default to continuous prose over `\item` lists for new content. 新内容默认使用连贯段落，而不是 `\item` 列表。
- Logic and diction: rigorous logic, precise and common wording, avoid obscure vocabulary. 逻辑与用词：逻辑要严谨，用词要准确且常见，避免生僻词汇。Prose should be concise and coherent, free of "AI flavor" and mechanical stacking of connective phrases. 行文要凝练连贯，去除"AI 味"，不要机械堆砌连接词。
- Tense: use simple present tense uniformly to describe methods, architecture, and experimental conclusions. 时态：统一用一般现在时描述方法、架构和实验结论。Use past tense only when explicitly referring to a specific historical event. 只有在明确提及某个具体历史事件时才使用过去时。

## Output Format for New Paper Sections

When producing or translating a paper section, output exactly two parts and nothing else: 在撰写或翻译论文章节时，只输出以下两部分，不输出其他任何内容。

Part 1 [LaTeX]: the section in English LaTeX. Must be fully English, with special characters escaped (`95\%`, `model\_v1`, `R\&D`), math kept in `$` delimiters. Part 1【LaTeX】：全英文的 LaTeX 正文，特殊字符必须转义（如 `95\%`、`model\_v1`、`R\&D`），数学公式保留 `$` 符号。

Part 2 [Translation]: the corresponding literal Chinese translation, used to verify the logic matches the original intent. Part 2【中文直译】：对应的中文逐字翻译，用来核对逻辑是否符合原意。

Before finalizing, self-review as a critical peer reviewer: check for over-formatting, logical gaps, and untranslated Chinese, then correct immediately. 定稿前，以挑剔的审稿人视角自我审查：检查是否存在过度排版、逻辑跳跃、未翻译的中文，发现问题立即修正。
