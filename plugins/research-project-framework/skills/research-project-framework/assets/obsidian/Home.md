# <项目名>

**<论文标题>** · <目标场地> · 截稿 <日期>

[[tracking/Index|任务表]] · [[tracking/Board|看板]] · [[records/Decisions|决定]] · [[tracking/Risks|风险]] · [[tracking/Writing-workflow|写作流程]] · [[tracking/File-map|目录分类]] · [[tracking/Setup|一次性设置]]

```dataviewjs
// Home 的 dashboard。每个数字都是算出来的,没有一处是抄的。
// 来源一:tracking/tasks 的卡片 frontmatter。来源二:derived/repo_state.md,
// 由 scripts/repo_check.py 在每次编辑后重写,装 git 与 CSV 行数这些 Obsidian 算不出的东西。
// 会写文件的只有一处:状态下拉框,它同时改卡片 frontmatter 和看板里那一行。
try {
  const A = (typeof app !== "undefined") ? app : dv.app;
  const DT = dv.luxon.DateTime;
  const today = DT.now().startOf("day");
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const iso = d => d && d.toISODate ? d.toISODate() : (d ? String(d) : null);
  const daysTo = v => Math.round(DT.fromISO(iso(v)).diff(today, "days").days);
  const cut = (s, n) => { s = String(s ?? ""); return s.length > n ? s.slice(0, n) + "…" : s; };

  const S = dv.page("derived/repo_state.md") ?? {};
  const cards = Array.from(dv.pages('"tracking/tasks"').where(p => p.id));
  const st = {};
  for (const c of cards) st[c.id] = c.status;
  const deps = c => !c.depends ? [] : (Array.isArray(c.depends) ? c.depends : [c.depends]);
  const isReady = c => c.status === "todo"
      && deps(c).every(d => st[String(d)] === "done");

  // 筛选与搜索的状态挂在 window 上,Dataview 重跑这一块时不丢
  const UI = (window.__dashUI ??= { chip: "ready", phase: null, q: "" });

  const STATUSES = ["todo", "doing", "blocked", "paused", "done", "cancelled"];
  // 栏名要和 tracking/Board.md、scripts/config.py 的 LANES 一致(英文见 references/glossary-zh-en.md)
  const LANE = { todo: "待办", doing: "进行中", blocked: "阻塞 / 暂缓",
                 paused: "阻塞 / 暂缓", cancelled: "取消", done: "完成" };
  // 卡片 phase 字段的显示名,按项目填,例如 { "A-setup": "开张", "B-writing": "写作" };没列的照原样显示
  const PH = {};
  const phaseName = k => PH[k] ?? k;

  const groups = () => {
    const live = cards.filter(c => c.status !== "cancelled");
    return {
      all: cards, live,
      done: live.filter(c => c.status === "done"),
      doing: cards.filter(c => c.status === "doing"),
      ready: cards.filter(isReady),
      waiting: live.filter(c => c.decision_by && c.status !== "done"),
      due: cards.filter(c => c.due && c.status !== "done" && c.status !== "cancelled")
               .sort((a, b) => String(iso(a.due)).localeCompare(String(iso(b.due)))),
    };
  };

  const CHIPS = [["ready", "能动手"], ["waiting", "等我定"], ["doing", "进行中"],
                 ["due", "有期限"], ["all", "全部"]];

  const rows = () => {
    const g = groups();
    let r = g[UI.chip] ?? g.all;
    if (UI.phase) r = r.filter(c => c.phase === UI.phase);
    if (UI.q) {
      const q = UI.q.toLowerCase();
      r = r.filter(c => (c.id + " " + c.title).toLowerCase().includes(q));
    }
    return r;
  };

  // ---------- 画 ----------
  const idCell = id => `<span class="dash-open" data-id="${esc(id)}">${esc(id)}</span>`;
  const selCell = c => `<select class="dash-sel" data-id="${esc(c.id)}">` +
    STATUSES.map(s => `<option value="${s}"${s === c.status ? " selected" : ""}>${s}</option>`).join("") +
    `</select>`;
  const dueCell = c => {
    if (!c.due) return "";
    const n = daysTo(iso(c.due));
    return n < 0 ? `<span class="dash-late">逾期 ${-n} 天</span>` : `${n} 天`;
  };

  const taskTable = () => {
    const r = rows();
    if (!r.length) return `<div class="dash-note">这个条件下没有卡。</div>`;
    return `<table class="dash-table"><thead><tr><th>卡</th><th>做什么</th><th>阶段</th>` +
      `<th>状态</th><th>还剩</th></tr></thead><tbody>` +
      r.map(c => `<tr><td>${idCell(c.id)}</td><td>${esc(cut(c.title, 52))}</td>` +
        `<td class="m">${esc(phaseName(c.phase ?? ""))}</td>` +
        `<td>${selCell(c)}</td><td class="m">${dueCell(c)}</td></tr>`).join("") +
      `</tbody></table>`;
  };

  const phaseBars = () => {
    let out = "";
    for (const k of [...new Set(cards.map(c => c.phase).filter(Boolean))].sort()) {
      const a = cards.filter(c => c.phase === k && c.status !== "cancelled");
      if (!a.length) continue;   // 整个阶段都取消了就不画,否则显示成 0/0
      const d = a.filter(c => c.status === "done");
      const pct = Math.round(100 * d.length / a.length);
      out += `<div class="dash-clickrow${UI.phase === k ? " on" : ""}" data-phase="${k}">` +
        `<div class="dash-row"><span>${esc(phaseName(k))}</span><span class="m">${d.length}/${a.length}</span></div>` +
        `<div class="dash-bar"><i style="width:${pct}%"></i></div></div>`;
    }
    return out + `<div class="dash-note">点一行只看那个阶段,再点一次取消。</div>`;
  };

  const tiles = () => {
    const g = groups();
    const t = (n, k, s, cls, chip) =>
      `<div class="dash-tile ${cls ?? ""}${chip ? " click" : ""}"${chip ? ` data-chip="${chip}"` : ""}>` +
      `<div class="n">${esc(n)}</div><div class="k">${esc(k)}</div><div class="s">${esc(s)}</div></div>`;
    return [
      t(`${g.done.length}/${g.live.length}`, "任务完成", `进行中 ${g.doing.length} · 取消 ${cards.length - g.live.length}`, "", "all"),
      t(g.ready.length, "现在能动手", "待办且前置齐了", g.ready.length ? "ok" : "", "ready"),
      t(g.waiting.length, "等你一句话", "卡在决定上", g.waiting.length ? "warn" : "ok", "waiting"),
      t(S.proposal_version ?? "?", "当前提案", `${iso(S.proposal_date) ?? ""} · ${S.proposal_chars ?? 0} 字符`),
      t(S.draft_chars ?? 0, "初稿字符", (S.draft_chars ?? 0) === 0 ? "还没开工" : "论文仓 section/ 的 .tex"),
      t(S.uncommitted ?? 0, "未提交文件", `分支 ${S.branch ?? "?"}`, (S.uncommitted ?? 0) > 0 ? "warn" : "ok"),
      t(`${S.risks_open ?? 0}/${S.risks_total ?? 0}`, "风险开着", `已关 ${S.risks_closed ?? 0} · 已删 ${S.risks_deleted ?? 0}`),
    ].join("");
  };

  const waitList = () => {
    const w = groups().waiting;
    if (!w.length) return `<div class="dash-note">没有等你的。</div>`;
    return `<table class="dash-table"><tbody>` + w.map(c =>
      `<tr><td>${idCell(c.id)}</td><td>${esc(cut(c.title, 34))}</td><td>${selCell(c)}</td></tr>`
    ).join("") + `</tbody></table>`;
  };

  // ---------- 组装 ----------
  const root = dv.container.createDiv("dash-root");
  let dec = [];
  try {
    const t = await dv.io.load("records/Decisions.md");
    dec = t.split("\n").filter(l => /^\|\s*20\d\d-\d\d-\d\d/.test(l))
      .slice(-5).reverse().map(l => l.split("|").slice(1, -1).map(x => x.trim()));
  } catch (e) { /* 文件不在就不显示 */ }
  const logs = Array.from(dv.pages('"records/log"')
    .where(p => /^\d{4}-\d{2}-\d{2}/.test(p.file.name))   // 日志名以日期开头:<日期>_<会话短名>
    .sort(p => p.file.name, "desc").limit(3));

  const panel = (title, body, cls) =>
    `<div class="dash-panel ${cls ?? ""}"><div class="h">${title}</div>${body}</div>`;

  const paint = () => {
    root.innerHTML =
      `<div class="dash-tiles">${tiles()}</div>` +
      panel(`任务 <input class="dash-q" type="text" placeholder="搜卡号或标题">` +
        `<span class="dash-chips">` +
        CHIPS.map(([k, label]) => `<span class="dash-chip${UI.chip === k ? " on" : ""}" data-chip="${k}">${label}</span>`).join("") +
        (UI.phase ? `<span class="dash-chip on" data-phase="${UI.phase}">${esc(phaseName(UI.phase))} ×</span>` : "") +
        `</span>`, taskTable(), "wide") +
      `<div class="dash-grid">` +
        panel("阶段进度", phaseBars()) +
        panel("等你一句话", waitList()) +
        panel("产物", [
          ["分析输出", `${S.analysis_files ?? "?"} 份(derived/analysis/)`],
          ["初稿", `${S.draft_chars ?? 0} 字符(论文仓 section/)`],
        ].map(([k, v]) => `<div class="dash-row"><span>${esc(k)}</span><span class="m">${esc(v)}</span></div>`).join("")) +
        panel("最近发生了什么",
          `<div class="dash-note">日志 ` +
          (logs.length ? logs.map(p => `<span class="dash-open" data-id="${esc(p.file.name)}">${esc(p.file.name)}</span>`).join(" · ") : "无") +
          `</div><table class="dash-table"><tbody>` +
          dec.map(r => `<tr><td class="m">${esc(r[0] ?? "")}</td><td class="m">${esc(r[1] ?? "")}</td><td>${esc(cut(r[2] ?? "", 60))}</td></tr>`).join("") +
          `</tbody></table><div class="dash-note">最近提交 ${esc(S.last_commit ?? "?")}(${esc(iso(S.last_commit_date) ?? "?")})</div>`) +
      `</div>`;
    wire();
  };

  // 只重画任务表,不动搜索框,免得每敲一个字焦点就跑掉
  const repaintTable = () => {
    const host = root.querySelector(".dash-panel.wide");
    const old = host && host.querySelector(".dash-table, .dash-note");
    if (!old) return paint();
    old.outerHTML = taskTable();
    wire();
  };

  async function setStatus(id, value) {
    const f = A.vault.getAbstractFileByPath("tracking/tasks/" + id + ".md");
    if (!f) return;
    await A.fileManager.processFrontMatter(f, fm => { fm.status = value; });
    const c = cards.find(x => x.id === id);
    if (c) c.status = value;
    st[id] = value;
    await syncBoard(id, value);   // 看板是手写清单,不同步就会当场变成过时记录
    paint();
  }

  async function syncBoard(id, status) {
    const f = A.vault.getAbstractFileByPath("tracking/Board.md");
    if (!f || !LANE[status]) return;
    const edit = text => {
      const lines = text.split("\n");
      const i = lines.findIndex(l => l.includes("[" + "[" + id + "]]"));
      if (i < 0) return text;
      const row = lines.splice(i, 1)[0].replace(/^- \[[ x]\]/, status === "done" ? "- [x]" : "- [ ]");
      const h = lines.findIndex(l => l.trim() === "## " + LANE[status]);
      if (h < 0) return text;
      let j = h + 1;
      while (j < lines.length && !lines[j].startsWith("## ")) j++;
      while (j > h + 1 && lines[j - 1].trim() === "") j--;
      lines.splice(j, 0, row);
      return lines.join("\n");
    };
    if (A.vault.process) await A.vault.process(f, edit);
    else await A.vault.modify(f, edit(await A.vault.read(f)));
  }

  function wire() {
    root.querySelectorAll(".dash-open").forEach(e =>
      e.addEventListener("click", () => A.workspace.openLinkText(e.dataset.id, "", false)));
    root.querySelectorAll(".dash-sel").forEach(e =>
      e.addEventListener("change", () => setStatus(e.dataset.id, e.value)));
    root.querySelectorAll("[data-chip]").forEach(e =>
      e.addEventListener("click", () => { UI.chip = e.dataset.chip; UI.phase = null; paint(); }));
    root.querySelectorAll("[data-phase]").forEach(e =>
      e.addEventListener("click", () => {
        UI.phase = UI.phase === e.dataset.phase ? null : e.dataset.phase; paint();
      }));
    const q = root.querySelector(".dash-q");
    if (q) {
      q.value = UI.q;
      q.addEventListener("input", () => { UI.q = q.value; repaintTable(); });
    }
  }

  paint();
  if (!S.branch) {
    dv.paragraph("**derived/repo_state.md 还没生成。** 跑一次 `python3 scripts/repo_check.py`,带问号的格子就有数了。");
  }
} catch (e) {
  dv.paragraph("**dashboard 出错了:** " + e.message + "。出现这一行说明插件已在运行,不是限制模式的问题;把这行错误原样告诉助手。");
}
```

**上面一片空白,或只有一行 Dataview JS queries are disabled?** 见 [[Setup]] 第 2 步:装好并启用两个插件、关掉限制模式、打开 Dataview 的 JavaScript 查询。

**这一页会写文件的只有状态下拉框。** 改一个值,它同时写卡片 frontmatter 和 [[Board]] 里对应那一行,两处不会分家。别的都是只读。页面里的数字不要手工改,全部由卡片与 `derived/repo_state.md` 算出。

**工作方式:** 任务卡在 `tracking/tasks/`;决定只记字面做过的并注明谁;新会话仍先读 `CLAUDE.md`。带 `decision_by` 的卡是等你一句话的。

**新文件放哪:** 目录表在 [[File-map]]。硬规矩只有两条:`inputs/` 不改,`derived/` 由脚本生成。仓库自己算得出来的事实不要手写,`scripts/repo_check.py` 每次编辑后自动核对。
