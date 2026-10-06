# 进度索引(Dataview)

导航:[[Home]] · [[Board]] · [[Decisions]] · [[Risks]] · [[File-map]] · [[Writing-workflow]] · 日志在 `records/log/`

任务卡在 `tracking/tasks/`,每张卡的 frontmatter 是唯一数据源;改一次 `status`,下面所有表同步。

改状态有三种方式:直接编辑卡片、在 [[Board]] 里拖动、或在 [[Home]] 的任务表里用下拉框选(第三种会同时写卡片和看板那一行)。
「能动手」只看状态与前置;要看哪张卡在通往投稿的路上,从 `depends` 追。

字段:`phase`(阶段,显示名在 [[Home]] 的 PH 表里改)· `effort` low/medium/high · `status` todo/doing/blocked/paused/done/cancelled · `window` 计划里的时段 · `due` 有明确日期时才填 · `depends` 前置任务 id · `decision_by` 只有等人拍板的卡才填,填谁的名字。

带 `decision_by` 的卡会出现在 [[Home]] 的「等你一句话」那一格里。它和 `status` 是两回事:一张卡可以是 blocked 而不等任何人(等算力、等前置),也可以是 paused 而在等用户一句话。

## 现在能动手的:待办且前置全部完成
```dataviewjs
const cards = dv.pages('"tracking/tasks"').where(p => p.id);
const st = {}; for (const c of cards) st[c.id] = c.status;
const deps = c => !c.depends ? [] : (Array.isArray(c.depends) ? c.depends : [c.depends]);
const ready = cards.where(c => c.status === "todo" && deps(c).every(d => st[String(d)] === "done"));
dv.table(["卡", "做什么", "阶段", "effort", "depends"],
  ready.sort(c => c.id).map(c => [c.file.link, c.title, c.phase, c.effort, deps(c).join(", ")]));
```

## 全部任务
```dataview
TABLE phase, effort, status, window, due, depends
FROM "tracking/tasks"
SORT phase ASC, id ASC
```

## 按阶段
```dataview
TABLE rows.id AS ids, length(rows) AS n, length(filter(rows, (r) => r.status = "done")) AS done
FROM "tracking/tasks"
GROUP BY phase
SORT phase ASC
```

## 状态汇总
```dataview
TABLE length(rows) AS n, rows.id AS ids
FROM "tracking/tasks"
GROUP BY status
```

## 有到期日的
```dataview
TABLE status, due
FROM "tracking/tasks"
WHERE due
SORT due ASC
```

## 等人拍板
```dataview
TABLE phase, status, decision_by
FROM "tracking/tasks"
WHERE decision_by
SORT id ASC
```

## 暂缓与阻塞
```dataview
TABLE phase, window
FROM "tracking/tasks"
WHERE status = "paused" OR status = "blocked"
```
