# 中英对照表

工作语言不是中文时用。第 1 节的词有脚本在认,改了要同步改代码和模板;第 2、3 节的词在几份文件之间互相引用,换的话所有出现处一起换。

## 1. 脚本会去认的词

| 中文 | 英文 | 要同时改的地方 |
|---|---|---|
| 待办 | To do | `scripts/config.py` 的 `LANES`、`tracking/Board.md` 的栏名、`Home.md` 的 `LANE` 表 |
| 进行中 | Doing | 同上 |
| 阻塞 / 暂缓 | Blocked / Paused | 同上 |
| 取消 | Cancelled | 同上 |
| 完成 | Done | 同上 |
| 关闭 | Closed | `scripts/config.py` 的 `RISK_CLOSED`;风险表「状态 / 对策」一栏里写这个词的行算关闭 |
| 已删 | Deleted | `scripts/config.py` 的 `RISK_DELETED`;风险一栏以删除线开头、并写这个词的行算删除 |

## 2. 记录里的固定说法

| 中文 | 英文 | 出现在 |
|---|---|---|
| 本次判断标准出自 | Criterion source | `references/research-workflow.md` 第 2 节;`assets/log.md` |
| 我自立 | Self-set | 同上 |
| 推测/无证据 | Conjecture, no evidence | `references/research-workflow.md` 第 2 节;CLAUDE.md 铁律 |
| 助手提议 | Assistant's proposal | `assets/task-card.md`;`assets/Decisions.md` |
| 已确立的事实 | Settled facts | CLAUDE.md;`references/research-workflow.md` 第 1 节 |
| 当前状态 | Current state | CLAUDE.md;`references/project-management.md` 第 2 节 |
| 项目类型 | Project type | CLAUDE.md(开张六问的答案) |

## 3. 触发词

用户说这些词时,助手按对应的规则做。英文用户的说法写进 CLAUDE.md 的工作规则,不靠助手猜。

| 中文 | 英文 | 助手做什么 |
|---|---|---|
| 开始 | go / start | 点名的那件工作就此批准,做完再报(`references/collaboration.md` 第 1 节) |
| 提交 | commit | 提交一次,只交本会话的行,不推送(`references/project-management.md` 第 5 节) |
| 检查 | check / review | 只报告问题、出处与建议改法,不改(`references/collaboration.md` 第 1 节) |
| 优化某节 | optimize <section> | 按优化清单逐项走(`references/writing-workflow.md` 第 3 节) |

## 4. 换成英文时还是中文的地方

- 五份正文、补充文件、模板:要整体翻译。
- 脚本的报告输出(`by_type.py`、`abstract_stats.py`、`agent_runs_ledger.py` 等)与 `repo_check.py` 的提示:是中文;要英文,得改各脚本里的字符串。
