# 一次性设置(Obsidian)

换机器或第一次打开项目库时做一遍。做完之后 [[Home]] 的面板才会出数。

## 1. 拷配置

把 skill research-project-framework 的 `assets/obsidian/obsidian-config/` 拷成项目根目录的 `.obsidian/`(注意前面的点)。`app.json` 的 `userIgnoreFilters` 写上项目里不该被索引的大目录(语料、论文 PDF、训练日志),不排除的话 Obsidian 会去索引它们。

## 2. 装两个社区插件

设置 → 社区插件 → 关掉「限制模式(Restricted mode)」→ 浏览,装并启用 **Dataview** 与 **Kanban**。

限制模式开着时社区插件一律不加载:[[Home]] 的面板变成一段空白代码块,[[Index]] 的表变成空代码块,[[Board]] 变成普通 md 文档。[[Board]] 第一次还要在标签页上右键选「以看板形式打开」。

装好后打开 Dataview 的 JavaScript 查询:设置 → 社区插件(左栏最下面那一组)→ Dataview → 打开「Enable JavaScript queries」。[[Home]] 的面板和 [[Index]] 的表都是 JavaScript 查询,这个开关装好时默认关着;关着时面板位置只有一行 Dataview JS queries are disabled。

## 3. 打开两个 CSS 片段

设置 → 外观 → CSS 片段,确认 `line-width` 与 `dashboard` 都开着(配置文件里已经写成开启,列表里看不到就点刷新)。

- `line-width`:正文行宽放宽到 1100px,多列表格才放得下。前提是 设置 → 编辑器 → 显示 →「可读行长度」打开。
- `dashboard`:Home 的磁贴与分栏排版。关掉的话内容还在,只是变成一长条竖排。

## 4. 让派生数据先生成一次

Home 面板里有一部分数字(git 状态、当前提案、初稿字数)Obsidian 自己算不出来,由 `scripts/repo_check.py` 写进 `derived/repo_state.md`,面板读那一页。脚本在每次编辑后自动跑;新项目里那个文件还不存在,手动跑一次:

```
python3 scripts/repo_check.py
```

`derived/repo_state.md` 不进版本库(写进 `.gitignore`)。

## 5. 日志模板

`.obsidian/daily-notes.json` 已把日志目录设成 `records/log`、模板设成 `tracking/templates/log.md`(配置里不写扩展名)。每个会话的日志由助手按 `<日期>_<会话短名>.md` 命名,不用 Obsidian 的按日新建。
