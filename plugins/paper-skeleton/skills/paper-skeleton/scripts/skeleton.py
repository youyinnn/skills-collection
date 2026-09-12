#!/usr/bin/env python3
"""Paper skeleton: one load-bearing sentence per paragraph of a LaTeX manuscript, kept in an Obsidian vault.

    skeleton.py init <main.tex> [--vault DIR]   read the manuscript, write skeleton.json, report what was found
    skeleton.py bootstrap [--write]              one card per paragraph in sections/, one \\label{sk|id} per card in the tex
    skeleton.py build                            rebuild Skeleton-graph.canvas, Skeleton-argument.canvas, Skeleton.md
    skeleton.py sync                             relocate every card in the tex by its label, take over changed sentences, rebuild
    skeleton.py check                            self-test on a synthetic manuscript in a temp dir

The vault is the current directory unless --vault is given. sections/*.md are the source of truth: one heading per
card with a header line (number, file:line, role), the sentence carrying a block id, "What rests on it", and the
optional "Relations." and "Left out." lines. The canvases and Skeleton.md are generated and never edited by hand.
The manuscript is edited in exactly one way: bootstrap inserts \\label{sk|<id>} right after each card's element.
"""
import collections
import datetime
import difflib
import json
import os
import pathlib
import re
import subprocess
import sys
import textwrap

# --------------------------------------------------------------------------- defaults
SKIP_ENVS = ['figure', 'figure*', 'table', 'table*', 'tabular', 'tabular*', 'tabularx', 'longtable', 'equation', 'equation*',
             'align', 'align*', 'gather', 'gather*', 'multline', 'multline*', 'eqnarray', 'eqnarray*', 'tikzpicture',
             'algorithm', 'algorithmic', 'algorithm2e', 'lstlisting', 'verbatim', 'minted', 'comment', 'thebibliography',
             'IEEEkeywords', 'IEEEbiography', 'IEEEbiographynophoto', 'keywords', 'CCSXML']
STRUCTURAL = ('\\section', '\\subsection', '\\subsubsection', '\\paragraph', '\\chapter', '\\label', '\\input', '\\include',
              '\\centering', '\\vspace', '\\hspace', '\\newpage', '\\clearpage', '\\bibliography', '\\bibliographystyle',
              '\\maketitle', '\\title', '\\author', '\\markboth', '\\IEEEpeerreviewmaketitle', '\\appendix', '\\noindent',
              '\\newcommand', '\\renewcommand', '\\providecommand', '\\DeclareRobustCommand', '\\DeclareMathOperator', '\\def', '\\let',
              '\\usepackage', '\\RequirePackage', '\\documentclass', '\\setlength', '\\addtolength', '\\newlength', '\\newtcolorbox',
              '\\newtcbtheorem', '\\newmdenv', '\\newenvironment', '\\renewenvironment', '\\newtheorem', '\\definecolor', '\\hypersetup',
              '\\graphicspath', '\\newcounter', '\\setcounter', '\\pagestyle', '\\thispagestyle', '\\makeatletter', '\\makeatother',
              '\\tikzset', '\\pgfplotsset', '\\sisetup', '\\lstset', '\\captionsetup', '\\usetikzlibrary', '\\newif', '\\if', '\\fi', '\\else')
ROLE_META = {  # role -> (canvas color, legend text); Okabe-Ito, colorblind-safe
    'claim': ('#D55E00', 'Claim. What the article proposes, contributes, or establishes.'),
    'question': ('#E69F00', 'Question and motivation. The need, the research questions, the positioning against prior work.'),
    'method': ('#0072B2', 'Method and design. How the study is built and the rules it judges by.'),
    'finding': ('#009E73', 'Finding and evidence. What the results show.'),
    'boundary': ('#CC79A7', 'Boundary and qualifier. What limits or scopes the findings.'),
    'nav': ('#999999', 'Navigation. Roadmap and pointers.'),
    'unset': (None, 'Unset. Bootstrapped and not yet judged: the sentence is the paragraph opener, the role is not chosen.'),
}
GREEN, BLUE, PURPLE, GRAY = '#009E73', '#0072B2', '#CC79A7', '#999999'
ARG_VERBS = {'supports': GREEN, 'licenses': BLUE, 'qualifies': PURPLE, 'same claim as': GRAY}
VERB_COLOR = {'delivered by': BLUE, 'delivers': BLUE, 'anchors': GREEN, 'anchored by': GREEN, 'restated in': GRAY,
              'restates': GRAY, 'cited in': GRAY, 'cites': GRAY, **ARG_VERBS}
LABEL_ANY = re.compile(r'\\label\{[^}]*\}')
LABEL_SK = re.compile(r'\\label\{sk\|([a-z0-9-]+)\}')
STOP = ('%', '\\begin', '\\end') + STRUCTURAL + ('\\item',)
CARD_RE = re.compile(r'^### (?P<num>.+)\n\*\*(?P<star>★ )?(?P=num)\*\* · `(?P<where>[^`]+)` · (?P<role>[a-z]+)\n'
                     r'(?P<sentence>.+?) \^(?P<bid>[a-z0-9-]+)\n\n\*\*What rests on it\.\*\* (?P<rest>.+?)$'
                     r'(?:\n\*\*Relations\.\*\* (?P<relations>.+?)$)?(?:\n\*\*Left out\.\*\* (?P<leftout>.+?)$)?', re.M)
WHERE_RE = re.compile(r'\*\*(?:★ )?(?P<num>[^*\n]+)\*\* · `(?P<where>[^`]+)` · [a-z]+\n(?P<sentence>[^\n]+?) \^(?P<bid>[a-z0-9-]+)$', re.M)
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX']


def die(msg):
    sys.exit(f'skeleton: {msg}')


# --------------------------------------------------------------------------- the manuscript
class Tex:
    """The manuscript as the skeleton sees it: the \\input chain of main.tex, its macros, its .aux numbers, its environments."""

    def __init__(self, main, cfg=None):
        self.main = pathlib.Path(main).resolve()
        self.root = self.main.parent
        cfg = cfg or {}
        self.boxes = set(cfg.get('boxes', []))
        self.skip = set(SKIP_ENVS) | set(cfg.get('skip_envs', []))
        self.macros = {}        # name -> (arity, body)
        self.override = dict(cfg.get('macros', {}))
        self.warnings = collections.Counter()
        self.chain = []         # files in reading order (relative to root)
        self.lines = {}
        self._walk(self.main)
        self.numbers = self._aux(cfg.get('aux'))

    def _walk(self, path, seen=None):
        seen = seen or set()
        rel = str(path.resolve().relative_to(self.root))
        if rel in seen or not path.exists():
            return
        seen.add(rel)
        text = path.read_text()
        self.chain.append(rel)
        self.lines[rel] = text.split('\n')
        self._scan_defs(text)
        for m in re.finditer(r'^[^%\n]*?\\(?:input|include|subfile)\{([^}]+)\}', text, re.M):
            name = m.group(1)
            for cand in (self.root / name, self.root / (name + '.tex'), path.parent / name, path.parent / (name + '.tex')):
                if cand.exists() and cand.is_file():
                    self._walk(cand, seen)
                    break

    def _scan_defs(self, text):
        for m in re.finditer(r'\\newtcolorbox(?:\[[^\]]*\])?\{(\w+)\}', text):
            self.boxes.add(m.group(1))
        for m in re.finditer(r'\\newtcbtheorem(?:\[[^\]]*\])?\{(\w+)\}', text):
            self.boxes.add(m.group(1))
        for m in re.finditer(r'\\newmdenv(?:\[[^\]]*\])?\{(\w+)\}', text):
            self.boxes.add(m.group(1))
        for m in re.finditer(r'\\(?:new|renew|provide)command\*?\s*\{?\\(\w+)\}?\s*(?:\[(\d)\])?(?:\[[^\]]*\])?\s*\{', text):
            name, arity, start = m.group(1), int(m.group(2) or 0), m.end()
            depth, i = 1, start
            while i < len(text) and depth:
                c = text[i]
                if c == '\\':
                    i += 2
                    continue
                depth += (c == '{') - (c == '}')
                i += 1
            self.macros.setdefault(name, (arity, text[start:i - 1]))

    def _aux(self, aux):
        cands = [self.root / aux] if aux else []
        cands += [self.root / 'output' / (self.main.stem + '.aux'), self.root / (self.main.stem + '.aux'), self.root / 'build' / (self.main.stem + '.aux')]
        for p in cands:
            if p.exists():
                out = {}
                for m in re.finditer(r'\\newlabel\{([^}]+)\}\{\{(.*?)\}\{', p.read_text()):
                    out[m.group(1)] = self.plain(m.group(2), quiet=True)
                self.aux_path = p
                return out
        self.aux_path = None
        return {}

    # -- LaTeX to text
    def expand(self, name, args):
        """Expand a user macro when its body renders to clean text; otherwise keep the last argument, or the name."""
        if name in self.override:
            return self.override[name]
        if name in self.macros:
            arity, body = self.macros[name]
            for k, a in enumerate(args[:arity], 1):
                body = body.replace(f'#{k}', a)
            before = sum(self.warnings.values())
            out = self._plain(body, depth=1)
            if '\\' not in out and '#' not in out and sum(self.warnings.values()) == before:
                return out
            self.warnings = self._warnings_snapshot(before)   # the body was not clean: forget the warnings its expansion raised
            if len(args) > 1:
                m = re.search(r'\\(?:textbf|textit|textsc|emph|text|mbox|hyperref\[[^\]]*\]|href\{[^}]*\}|textcolor\{[^}]*\})\s*\{\s*(?:\\\w+\s*)*#(\d)', body)
                k = int(m.group(1)) if m else 1
                return args[k - 1] if k <= len(args) else args[0]
        if args:
            return args[0] if len(args) == 1 else args[-1]
        self.warnings[name] += 1
        return name

    def _warnings_snapshot(self, before):
        # drop the most recent warnings until the total is back at `before`
        total = sum(self.warnings.values())
        for n in reversed(list(self.warnings)):
            while total > before and self.warnings[n] > 0:
                self.warnings[n] -= 1
                total -= 1
        return collections.Counter({n: k for n, k in self.warnings.items() if k > 0})

    def _plain(self, s, depth=0):
        if depth > 4:
            return s
        s = LABEL_ANY.sub('', s)
        s = re.sub(r'\\item(?:\[[^\]]*\])?\s*', '', s)
        s = re.sub(r'(?<!\\)%.*$', '', s, flags=re.M)
        s = re.sub(r'\s*~?\\(?:cite[tp]?|citeauthor|citeyear|nocite)\*?\s*(?:\[[^\]]*\])*\s*\{[^}]*\}', '', s)
        s = re.sub(r'\\footnote\{(?:[^{}]|\{[^{}]*\})*\}', '', s)
        s = re.sub(r'\\(?:ref|eqref|pageref|cref|Cref|autoref)\*?\{([^}]*)\}', lambda m: self.numbers.get(m.group(1), '[' + m.group(1) + ']'), s)
        s = re.sub(r'\\(?:hyperref)\[[^\]]*\]\{([^}]*)\}', r'\1', s)
        s = re.sub(r'\\(?:href)\{[^}]*\}\{([^}]*)\}', r'\1', s)
        s = re.sub(r'\\(?:url|texttt|path)\{([^}]*)\}', r'\1', s)
        s = re.sub(r'\\textcolor\{[^}]*\}\{([^}]*)\}', r'\1', s)
        s = re.sub(r'\$([^$]*)\$', lambda m: math_plain(m.group(1)), s)
        s = re.sub(r'\\\((.*?)\\\)', lambda m: math_plain(m.group(1)), s)
        for _ in range(3):
            s = re.sub(r'\\(?:textit|textbf|textsc|textrm|textsf|textup|textnormal|emph|underline|mbox|hbox|text|mathrm|uppercase|MakeUppercase)\s*\{([^{}]*)\}', r'\1', s)
        s = re.sub(r'\\(?:scriptscriptstyle|scriptstyle|textstyle|displaystyle|small|footnotesize|scriptsize|tiny|large|Large|LARGE|huge|Huge|'
                   r'bfseries|itshape|scshape|rmfamily|sffamily|ttfamily|normalfont|xspace|noindent|indent|centering|raggedright|raggedleft|relax|hfill|vfill|par|newline|linebreak|-)\b\s*', '', s)
        s = s.replace('\\%', '%').replace('\\&', '&').replace('\\_', '_').replace('\\#', '#').replace('\\$', '$').replace('\\{', '{').replace('\\}', '}')
        s = s.replace('~', ' ').replace('\\,', ' ').replace('\\;', ' ').replace('\\ ', ' ').replace('\\\\', ' ').replace('``', '"').replace("''", '"').replace('`', "'")
        # user macros, with or without brace arguments
        def user(m):
            name = m.group(1)
            rest, args, i = m.group(2), [], 0
            while rest[i:i + 1] == '{':
                depth, j = 1, i + 1
                while j < len(rest) and depth:
                    depth += (rest[j] == '{') - (rest[j] == '}')
                    j += 1
                args.append(self._plain(rest[i + 1:j - 1], depth + 1) if False else rest[i + 1:j - 1])
                i = j
            return self.expand(name, [self._plain(a, depth + 1) for a in args]) + rest[i:]
        s = re.sub(r'\\([A-Za-z]+)\*?((?:\{(?:[^{}]|\{[^{}]*\})*\})*)', user, s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    def plain(self, s, quiet=False):
        out = self._plain(s.strip())
        out = out.replace('{', '').replace('}', '')
        return out

    # -- structure
    def paragraphs(self, rel):
        """Prose paragraphs and boxes of one file: dicts with kind (para / item / box), start, end (1-based, inclusive)."""
        out, cur, skip = [], None, 0

        def close():
            nonlocal cur
            if cur:
                out.append(cur)
            cur = None

        lines = self.lines[rel]
        body = [i for i, l in enumerate(lines, 1) if l.strip().startswith('\\begin{document}')]
        first = body[0] + 1 if body else 1   # the preamble is not prose
        open_braces, after_structural = 0, False   # a structural command's continuation lines (open braces, or a `{` argument on the next line) stay structural
        for i, raw in enumerate(lines, 1):
            s = raw.strip()
            if i < first:
                continue
            if s.startswith('\\end{document}'):
                break
            if open_braces > 0 or (after_structural and s.startswith('{')):
                open_braces = max(0, open_braces + s.count('{') - s.count('}'))
                close()
                continue
            after_structural = False
            b = re.match(r'\\begin\{(\w+\*?)\}', s)
            e = re.match(r'\\end\{(\w+\*?)\}', s)
            if b and b.group(1) in self.skip:
                close()
                skip += 1
                continue
            if e and e.group(1) in self.skip:
                skip = max(0, skip - 1)
                continue
            if skip:
                continue
            if b and b.group(1) in self.boxes:
                close()
                cur = dict(kind='box', start=i, end=i, env=b.group(1))
                continue
            if e and e.group(1) in self.boxes:
                if cur:
                    cur['end'] = i
                close()
                continue
            if cur and cur['kind'] == 'box':
                cur['end'] = i
                continue
            if b or e:
                close()
                continue
            if not s or s.startswith(STRUCTURAL) or s.startswith('\\end') or s == '\\\\':
                if s.startswith(STRUCTURAL):
                    open_braces, after_structural = max(0, s.count('{') - s.count('}')), True
                close()
                continue
            if s.startswith('%'):
                continue
            if s.startswith('\\item'):
                close()
                cur = dict(kind='item', start=i, end=i)
                if not re.sub(r'^\\item(\[[^\]]*\])?\s*', '', s):
                    continue
            if cur is None:
                cur = dict(kind='para', start=i, end=i)
            cur['end'] = i
        close()
        return out

    def sections(self):
        """Files of the chain that hold prose, with a title, a number prefix, and their subsection headings."""
        out, sec_n = [], 0
        for rel in self.chain:
            paras = self.paragraphs(rel)
            if not paras:
                continue
            text = '\n'.join(self.lines[rel])
            heads = [(m.start(), m.group(1), m.group(2), m.group(3)) for m in re.finditer(r'^\\(section|subsection|subsubsection)(\*?)\{((?:[^{}]|\{[^{}]*\})*)\}', text, re.M)]
            secs = [h for h in heads if h[1] == 'section']
            if secs:
                title = self.plain(secs[0][3])
                if secs[0][2] == '*':
                    num = ''.join(w[0] for w in title.split() if w[0].isupper()) or title[:3]
                else:
                    sec_n += 1
                    num = ROMAN[sec_n - 1] if sec_n <= len(ROMAN) else str(sec_n)
            else:  # no \section: name the file after the environment holding its first paragraph (abstract, IEEEImpStatement)
                before = self.lines[rel][:paras[0]['start']]
                envs = [m.group(1) for l in before for m in re.finditer(r'\\begin\{(\w+)\}', l) if m.group(1) != 'document']
                title = re.sub(r'^IEEE', '', envs[-1]) if envs else pathlib.Path(rel).stem
                title = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', title).capitalize()
                num = title[:3]
            out.append(dict(tex=rel, title=title, num=num, short=pathlib.Path(rel).stem, paragraphs=len(paras)))
        shorts = collections.Counter(s['short'] for s in out)
        for s in out:
            if shorts[s['short']] > 1:
                s['short'] = s['tex'].replace('.tex', '').replace('/', '-')
        return out

    def git_state(self, files):
        try:
            sha = subprocess.run(['git', '-C', str(self.root), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
            dirty = subprocess.run(['git', '-C', str(self.root), 'status', '--porcelain', '--'] + [str(self.root / f) for f in files], capture_output=True, text=True).stdout.split('\n')
            dirty = [d.split()[-1] for d in dirty if d.strip()]
            return f"{sha} ({'clean' if not dirty else 'uncommitted changes in ' + ', '.join(pathlib.Path(d).stem for d in dirty)})"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return 'not a git repository'


MATH_SUBS = [('\\bar{\\delta}', 'δ̄'), ('\\geq', '≥'), ('\\leq', '≤'), ('\\ge', '≥'), ('\\le', '≤'), ('\\neq', '≠'), ('\\ne', '≠'),
             ('\\times', '×'), ('\\alpha', 'α'), ('\\beta', 'β'), ('\\gamma', 'γ'), ('\\delta', 'δ'), ('\\epsilon', 'ε'), ('\\lambda', 'λ'),
             ('\\mu', 'μ'), ('\\pi', 'π'), ('\\rho', 'ρ'), ('\\sigma', 'σ'), ('\\tau', 'τ'), ('\\phi', 'φ'), ('\\chi', 'χ'), ('\\omega', 'ω'),
             ('\\Delta', 'Δ'), ('\\Sigma', 'Σ'), ('\\Omega', 'Ω'), ('\\infty', '∞'), ('\\pm', '±'), ('\\cdot', '·'), ('\\ldots', '...'),
             ('\\dagger', '†'), ('\\sim', '-'), ('\\approx', '≈'), ('\\circ', '°'), ('\\%', '%'), ('\\,', ' '), ('\\;', ' '), ('\\!', ''), ('~', ' ')]


def math_plain(s):
    s = re.sub(r'_\{(\d+)\\sim\s*(\d+)\}', r'\1-\2', s)
    s = re.sub(r'\\(?:text|mathrm|mathbf|mathit|textrm|mathcal|operatorname)\{([^}]*)\}', r'\1', s)
    s = re.sub(r'\\(?:scriptscriptstyle|scriptstyle|textstyle|displaystyle|left|right|,|;|!)\b\s*', '', s)
    for a, b in MATH_SUBS:
        s = s.replace(a, b)
    s = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'\1/\2', s)
    s = re.sub(r'\^\{?2\}?', '²', s)
    s = re.sub(r'\^\{([^}]*)\}', r'^\1', s)
    s = re.sub(r'_\{?(\d+)\}?', r'\1', s)
    s = re.sub(r'_\{([^}]*)\}', r'_\1', s)
    s = re.sub(r'\\([A-Za-z]+)', r'\1', s)
    s = s.replace('{', '').replace('}', '').replace('Δ R', 'ΔR')
    return s


ABBREV = re.compile(r'\b(e\.g|i\.e|et al|vs|cf|Fig|Figs|Eq|Eqs|Sec|Secs|Tab|Ref|Refs|No|Dr|Mr|Ms|Prof|approx|resp)\.\s')
BOUNDARY = re.compile(r'(?<=[.!?])\s+(?=[A-Z(\\])')


def protect(t):
    """Same length as t, with the space after a common abbreviation replaced so BOUNDARY does not split there."""
    return ABBREV.sub(lambda m: m.group(0)[:-1] + '\x00', t)


def boundaries(t):
    """Start offsets of the whitespace runs that end a sentence in t (labels are not removed: offsets are into t)."""
    return [m.start() for m in BOUNDARY.finditer(protect(t))]


def sentences(line):
    """Sentences of a raw tex line (labels ignored). A period followed by a space and a capital, a parenthesis, or a
    command ends a sentence; common abbreviations do not."""
    t = protect(LABEL_ANY.sub('', line).strip())
    return [x.replace('\x00', ' ') for x in BOUNDARY.split(t) if x]


# --------------------------------------------------------------------------- the vault
class Vault:
    def __init__(self, root):
        self.root = pathlib.Path(root).resolve()
        self.cfg_path = self.root / 'skeleton.json'
        self.sec_dir = self.root / 'sections'

    def load(self):
        if not self.cfg_path.exists():
            die(f'no skeleton.json in {self.root}; run: skeleton.py init <main.tex> --vault {self.root}')
        self.cfg = json.loads(self.cfg_path.read_text())
        main = pathlib.Path(self.cfg['main_tex'])
        self.tex = Tex(main if main.is_absolute() else self.root / main, self.cfg)
        self.sections = self.cfg['sections']
        self.short_of = {s['tex']: s['short'] for s in self.sections}
        self.tex_of = {s['short']: s['tex'] for s in self.sections}
        self.file_of = {s['tex']: s['file'] for s in self.sections}
        return self

    def save_cfg(self):
        self.cfg_path.write_text(json.dumps(self.cfg, indent=2, ensure_ascii=False) + '\n')

    def where(self, tex, line, to=None):
        return f'{self.short_of[tex]}:{line}' + (f'-{to}' if to else '')

    def parse_where(self, w):
        f, _, rng = w.partition(':')
        a, _, b = rng.partition('-')
        return self.tex_of[f], int(a), (int(b) if b else None)

    def frontmatter(self):
        state = self.tex.git_state([s['tex'] for s in self.sections])
        return [f'source: {self.tex.root}', f'source_commit: {state}', f'updated: {datetime.date.today().isoformat()}']

    # -- cards
    def load_cards(self):
        """Chapters in reading order, each with its subsections and cards, parsed from sections/*.md."""
        chapters, cards = [], {}
        for s in self.sections:
            path = self.sec_dir / (s['file'] + '.md')
            if not path.exists():
                continue
            text = path.read_text()
            subs, cur = [], ['', '', []]
            subs.append(cur)
            pos = 0
            for m in re.finditer(r'^## (.+)$', text, re.M):
                for c in CARD_RE.finditer(text, pos, m.start()):
                    cur[2].append(self._card(c, s))
                cur = [f"{s['file']}#{m.group(1)}", m.group(1), []]
                subs.append(cur)
                pos = m.end()
            for c in CARD_RE.finditer(text, pos):
                cur[2].append(self._card(c, s))
            subs = [x for x in subs if x[2]]
            chapters.append((s, subs))
            for _, _, cs in subs:
                for c in cs:
                    assert c['bid'] not in cards, f"duplicate block id ^{c['bid']}"
                    cards[c['bid']] = c
        by_num = {c['num']: b for b, c in cards.items()}
        for c in cards.values():
            c['edges'] = []
            for verb, targets in c['relations']:
                for t in targets:
                    if t not in by_num:
                        c['problems'].append(f"relation target '{t}' is not a card")
                    else:
                        c['edges'].append((verb, by_num[t]))
        return chapters, cards

    def _card(self, m, s):
        rel = []
        if m['relations']:
            for part in m['relations'].split(';'):
                verb, sep, rest = part.strip().rstrip('.').partition(':')
                if not sep:
                    verb, rest = 'relates to', verb
                rel.append((verb.strip(), [t.strip() for t in rest.split(',') if t.strip()]))
        role = m['role']
        return dict(num=m['num'], where=m['where'], role=role if role in ROLE_META else 'unset', chapter=bool(m['star']),
                    sentence=m['sentence'], rest=m['rest'], relations=rel, leftout=m['leftout'], file=s['file'], heading=m['num'],
                    bid=m['bid'], problems=[] if role in ROLE_META else [f"unknown role '{role}'"])

    # -- labels
    def labels(self):
        found = collections.defaultdict(list)
        for s in self.sections:
            for i, l in enumerate(self.tex.lines[s['tex']], 1):
                for m in LABEL_SK.finditer(l):
                    found[m.group(1)].append((s['tex'], i))
        return found

    def element_at(self, tex, i):
        """(plain text, first line) of the sentence or run-in heading that ends at the sk| label on line i."""
        lines, raw = self.tex.lines[tex], self.tex.lines[tex][i - 1]
        pos, start = LABEL_SK.search(raw).start(), i
        while start > 1:
            prev = lines[start - 2].strip()
            if not prev or prev.startswith(STOP) or re.search(r'[.!?][)}]*$', LABEL_ANY.sub('', prev).rstrip()):
                break
            start -= 1
        joined = ' '.join(lines[start - 1:i - 1] + [raw[:pos]])
        joined = re.sub(r'^\s*\\item(?:\[[^\]]*\])?\s*', '', joined)
        sents = sentences(self.tex.plain(joined))
        return (sents[-1] if sents else ''), start

    def candidates(self, tex, span):
        lines, out = self.tex.lines[tex], []
        for i in range(len(lines) - span + 1):
            chunk = lines[i:i + span]
            if any(not l.strip() or (l.strip().startswith(STOP) and not l.strip().startswith('\\item')) for l in chunk):
                continue
            for t in sentences(' '.join(chunk)):
                out.append((self.tex.plain(t), i + 1, i + span if span > 1 else None))
        return out

    # -- sync
    def sync(self):
        moved, updated, missing = [], [], []
        lab = self.labels()
        fm = self.frontmatter()
        for s in self.sections:
            path = self.sec_dir / (s['file'] + '.md')
            if not path.exists():
                continue
            text, edits = path.read_text(), []
            for m in WHERE_RE.finditer(text):
                tex, line, to = self.parse_where(m['where'])
                hits = lab.get(m['bid'], [])
                if len(hits) == 1:
                    tex, i = hits[0]
                    sentence, start = self.element_at(tex, i)
                    best = (sentence, start, i if start != i else None)
                else:
                    cands = self.candidates(tex, (to - line + 1) if to else 1)
                    exact = [c for c in cands if c[0] == m['sentence']]
                    if exact:
                        best = min(exact, key=lambda c: abs(c[1] - line))
                    else:
                        best = max(cands, key=lambda c: difflib.SequenceMatcher(None, m['sentence'], c[0]).ratio(), default=None)
                        if not best or difflib.SequenceMatcher(None, m['sentence'], best[0]).ratio() < 0.8:
                            missing.append(f"{m['num']} {m['where']}")
                            continue
                new_where = self.where(tex, best[1], best[2])
                if new_where != m['where']:
                    moved.append(f"{m['num']} {m['where']} -> {new_where}")
                    edits.append((m.span('where'), new_where))
                if best[0] != m['sentence']:
                    tag = '' if difflib.SequenceMatcher(None, m['sentence'], best[0]).ratio() >= 0.8 else '  (rewrite, re-judge the card)'
                    updated.append(f"{m['num']} {new_where}{tag}\n    - {m['sentence']}\n    + {best[0]}")
                    edits.append((m.span('sentence'), best[0]))
            if edits:
                for (a, b), rep in sorted(edits, reverse=True):
                    text = text[:a] + rep + text[b:]
                text = re.sub(r'^source_commit: .*$', fm[1], text, count=1, flags=re.M)
                text = re.sub(r'^updated: .*$', fm[2], text, count=1, flags=re.M)
                path.write_text(text)
        return moved, updated, missing

    # -- census
    def census(self, cards):
        problems, lab = [], self.labels()
        by_tex = collections.defaultdict(list)
        for c in cards.values():
            tex, line, to = self.parse_where(c['where'])
            c['tex'], c['line'], c['to'] = tex, line, to
            by_tex[tex].append(c)
            problems += [f"{c['num']}: {p}" for p in c['problems']]
        for s in self.sections:
            tex = s['tex']
            paras = self.tex.paragraphs(tex)
            for p in paras:
                hits = [c for c in by_tex[tex] if p['start'] <= c['line'] <= p['end']]
                if len(hits) != 1:
                    problems.append(f"{tex}:{p['start']}-{p['end']} ({p['kind']}) has {len(hits)} cards: {[h['num'] for h in hits]}")
                labs = [b for b, hs in lab.items() for ff, ln in hs if ff == tex and p['start'] <= ln <= p['end']]
                if len(labs) > 1:
                    problems.append(f"{tex}:{p['start']}-{p['end']} holds {len(labs)} labels: {labs}")
            covered = {c['bid'] for p in paras for c in by_tex[tex] if p['start'] <= c['line'] <= p['end']}
            for c in by_tex[tex]:
                if c['bid'] not in covered:
                    problems.append(f"{c['num']} at {tex}:{c['line']} is outside every paragraph")
        for b, hits in lab.items():
            if b not in cards:
                problems.append(f'label sk|{b} at {hits} has no card')
            elif len(hits) > 1:
                problems.append(f'label sk|{b} appears {len(hits)} times: {hits}')
        for c in cards.values():
            if c['bid'] not in lab:
                problems.append(f"{c['num']} has no \\label{{sk|{c['bid']}}} in the tex")
        return problems


# --------------------------------------------------------------------------- init
def cmd_init(main, vault_dir):
    tex = Tex(main)
    v = Vault(vault_dir)
    v.root.mkdir(parents=True, exist_ok=True)
    if v.cfg_path.exists():
        die(f'{v.cfg_path} exists; edit it or delete it to re-init')
    secs = tex.sections()
    used = {s for s in {m.group(1) for rel in tex.chain for m in re.finditer(r'\\begin\{(\w+\*?)\}', '\n'.join(tex.lines[rel]))}}
    for k, s in enumerate(secs):
        s['file'] = f"{k:02d} {s['num']} {s['title']}".replace('/', '-')
    cfg = dict(main_tex=str(tex.main), aux=str(tex.aux_path.relative_to(tex.root)) if tex.aux_path else None,
               sections=[{k: s[k] for k in ('tex', 'file', 'title', 'num', 'short')} for s in secs],
               boxes=sorted(tex.boxes & used), skip_envs=[], macros={})
    v.cfg = cfg
    v.save_cfg()
    print(f'wrote {v.cfg_path}')
    print(f'manuscript: {tex.main}  ({len(tex.chain)} files in the \\input chain, {len(secs)} hold prose)')
    aux_note = tex.aux_path or 'not found (ref numbers will show as [label])'
    print(f'.aux: {aux_note}')
    for s in secs:
        print(f"  {s['num']:5s} {s['tex']:32s} {s['paragraphs']:3d} paragraphs   -> sections/{s['file']}.md")
    envs = sorted(used)
    print('environments:', ', '.join(f"{e} ({'skip' if e in tex.skip else 'box' if e in tex.boxes else 'prose'})" for e in envs))
    textual = {n for n, (a, b) in tex.macros.items() if a == 0 and '\\' not in tex.plain(b)}
    print(f'macros: {len(tex.macros)} defined, {len(textual)} expand to text; set "macros": {{"name": "text"}} in skeleton.json to override any rendering')
    print('next: review skeleton.json (order, titles, boxes), then: skeleton.py bootstrap --vault', v.root)


# --------------------------------------------------------------------------- bootstrap
def bid_of(num):
    return re.sub(r'[^a-z0-9]', '', num.lower())


def cmd_bootstrap(v, write):
    if any((v.sec_dir / (s['file'] + '.md')).exists() for s in v.sections):
        die('sections/ already has chapter files; bootstrap only starts a vault (delete them to start over)')
    tex, lab = v.tex, v.labels()
    existing = {b: hits[0] for b, hits in lab.items() if len(hits) == 1}
    inserts, files_out, total, box_n, seen = {}, {}, 0, collections.Counter(), set()
    fm = v.frontmatter()
    for s in v.sections:
        rel, lines = s['tex'], tex.lines[s['tex']]
        text = '\n'.join(lines)
        heads = sorted([(m.start(), m.group(1), m.group(2)) for m in re.finditer(r'^\\(subsection|subsubsection)\*?\{((?:[^{}]|\{[^{}]*\})*)\}', text, re.M)])
        offsets = [0] + [i + 1 for i, c in enumerate(text) if c == '\n']
        out = ['---', f"section: {s['num']}", f"title: {s['title']}", f"tex: {rel}"] + fm[1:] + ['---', '', f"# {s['title']}", '',
               'The load-bearing sentence of each paragraph and box of this section, in reading order, with its source line, its role '
               'in the argument, and what rests on it. This file is the source; [[Skeleton]], [[Skeleton-graph.canvas]], and '
               '[[Skeleton-argument.canvas]] only reference it. Criterion in [[Skeleton]].']
        sub_i, sub_num, k = 0, '', 0
        for p in tex.paragraphs(rel):
            while sub_i < len(heads) and offsets[p['start'] - 1] > heads[sub_i][0]:
                kind, title = heads[sub_i][1], tex.plain(heads[sub_i][2])
                letters = [h for h in heads[:sub_i + 1] if h[1] == 'subsection']
                sub_num = f"{s['num']}-{chr(64 + len(letters))}" if kind == 'subsection' else sub_num + f".{sum(1 for h in heads[:sub_i + 1] if h[1] == 'subsubsection')}"
                out += ['', f'## {sub_num} {title}']
                k = 0
                sub_i += 1
            if p['kind'] == 'box':
                box_n[p['env']] += 1
                num = f"{p['env'].capitalize()}-{box_n[p['env']]}"
            else:
                k += 1
                num = f"{sub_num or s['num']}.{k}"
            b = bid_of(num)
            while b in seen:
                b += 'x'
            seen.add(b)
            # provisional element: the run-in heading if the paragraph opens with one alone on its line, else the first sentence
            first = lines[p['start'] - 1]
            body_start = p['start']
            if p['kind'] == 'box':
                body_start = next((i for i in range(p['start'] + 1, p['end'] + 1) if lines[i - 1].strip() and not lines[i - 1].strip().startswith(('\\begin', '\\end', '%'))), p['start'])
                first = lines[body_start - 1]
            m = re.match(r'(\s*(?:\\item(?:\[[^\]]*\])?\s*)?)(\\textbf\{[^}]*\})\s*$', first)
            if m:
                pos, line_no, sent = m.end(2), body_start, tex.plain(m.group(2))
                to = None
            else:
                line_no, acc = body_start, ''
                while True:
                    raw = lines[line_no - 1]
                    seg = re.sub(r'^\s*\\item(\[[^\]]*\])?\s*|^\s*\\textbf\{[^}]*\}\s*', '', raw) if line_no == body_start else raw
                    bounds = boundaries(LABEL_ANY.sub(lambda m: ' ' * len(m.group(0)), seg))
                    if bounds:
                        pos, acc = len(raw) - len(seg) + bounds[0], acc + ' ' + seg[:bounds[0]]
                        break
                    if line_no >= p['end'] or re.search(r'[.!?][)}]*\s*$', LABEL_ANY.sub('', raw)):
                        pos, acc = len(raw.rstrip()), acc + ' ' + seg
                        break
                    acc += ' ' + seg
                    line_no += 1
                sent, to = tex.plain(acc), (line_no if line_no != body_start else None)
                if to:
                    body_start, line_no = body_start, line_no
            if b in existing:
                pass  # a label already present for this id is kept where it is
            else:
                inserts[(rel, line_no)] = (pos, f'\\label{{sk|{b}}}')
            where = v.where(rel, body_start, to)
            out += ['', f'### {num}', f'**{num}** · `{where}` · unset', f'{sent} ^{b}', '', '**What rests on it.** TODO']
            total += 1
        out.append('')
        files_out[s['file']] = '\n'.join(out)
    print(f'{total} cards over {len(files_out)} chapter files; {len(inserts)} labels to insert into the tex')
    for (rel, i), (pos, lab_) in sorted(inserts.items()):
        raw = tex.lines[rel][i - 1]
        print(f"  {rel}:{i}  ...{raw[max(0, pos - 40):pos]}[{lab_}]{raw[pos:pos + 20]}")
    if not write:
        print('dry run: pass --write to write sections/ and insert the labels')
        return
    for (rel, i), (pos, lab_) in inserts.items():
        raw = tex.lines[rel][i - 1]
        tex.lines[rel][i - 1] = raw[:pos] + lab_ + raw[pos:]
    for rel in {r for r, _ in inserts}:
        (tex.root / rel).write_text('\n'.join(tex.lines[rel]))
    v.sec_dir.mkdir(exist_ok=True)
    for name, content in files_out.items():
        (v.sec_dir / (name + '.md')).write_text(content)
    print(f'wrote sections/ ({len(files_out)} files) and {len(inserts)} labels in {len({r for r, _ in inserts})} tex files')


# --------------------------------------------------------------------------- build
W, GAPX, GAPY, PAD, LABEL_H = 480, 240, 28, 40, 44
LINE_H, CARD_PAD = 27, 48


def nlines(t, cpl):
    return max(1, len(textwrap.wrap(t, cpl, break_on_hyphens=False)))


def fnode(c, x, y, width, full):
    cpl = int(width / 9.2)
    extra = (nlines('Relations. ' + '; '.join(v + ': ' + ', '.join(t) for v, t in c['relations']), cpl) if c['relations'] else 0) + (nlines(c['leftout'], cpl) if c['leftout'] else 0)
    if full:
        ln = 1 + nlines(c['sentence'], cpl) + 1 + nlines(c['rest'], cpl) + extra
        h = CARD_PAD + 44 + ln * LINE_H
    else:
        ln = 1 + nlines(c['sentence'], cpl)
        h = CARD_PAD + 16 + ln * LINE_H
    d = dict(id=c['bid'], type='file', file=f"sections/{c['file']}.md", subpath=f"#{c['heading']}" if full else f"#^{c['bid']}",
             x=int(x), y=int(y), width=width, height=int(h))
    col = ROLE_META[c['role']][0]
    if col:
        d['color'] = col
    return d


def legend(prefix, x, y, title, edge_text):
    LW, LH, LG = 300, 190, 20
    out = [dict(id=f'{prefix}_TITLE', type='text', x=x, y=y, width=W + 2 * PAD, height=LABEL_H + PAD + LH, text=title)]
    gx = x + W + 2 * PAD + GAPX // 2
    roles = [(r, m) for r, m in ROLE_META.items() if m[0]]
    for k, (role, (col, text)) in enumerate(roles):
        out.append(dict(id=f'{prefix}_L_{role}', type='text', x=gx + PAD + k * (LW + LG), y=y + LABEL_H + PAD // 2, width=LW, height=LH, text=f"**{role}**\n\n{text}", color=col))
    ex = gx + PAD + len(roles) * (LW + LG)
    out.append(dict(id=f'{prefix}_L_edges', type='text', x=ex, y=y + LABEL_H + PAD // 2, width=2 * LW + LG, height=LH, text=edge_text))
    out.append(dict(id=f'{prefix}_LEGEND', type='group', x=gx, y=y, width=ex + 2 * LW + LG + PAD - gx, height=LABEL_H + PAD + LH, label='Legend'))
    return out


GRAPH_TITLE = ("# Paper skeleton, reading order\n\nOne load-bearing sentence per paragraph, first section to last. One group per section, "
               "left to right; inside a section, the lead paragraphs and each subsection are side-by-side columns. Every card is a live view "
               "of its section file in `sections/`; edit there. Card color = role of the sentence in the argument (legend to the right). "
               "★ = the section's load-bearing sentence.\n\nArgument map: [[Skeleton-argument.canvas]] · Criterion and reverse outline: [[Skeleton]]")
GRAPH_EDGES = ("**Arrows**\n\nBlue: a promise and where the paper delivers it (delivered by, delivers).\n\nGreen: evidence and where "
               "the abstract or conclusion restates it (anchors).\n\nGray: any other cross-reference the text itself states.")
ARG_TITLE = ("# Paper skeleton, argument map\n\nThe contention on top, the claims that support it beneath, each finding under the claim it "
             "holds up, the rules the findings are judged by along the bottom, and the boundaries that qualify the claims on the right. "
             "Every card is a live view of its section file in `sections/`; same colors as [[Skeleton-graph.canvas]]. Cards with no "
             "supports / licenses / qualifies / same-claim relation are left out (list in [[Skeleton]]).\n\nCriterion and reverse outline: [[Skeleton]]")
ARG_EDGES = ("**Arrows**\n\nGreen, supports: evidence drawn upward into the claim it holds up.\n\nBlue, licenses: the rule or design a "
             "finding is judged by.\n\nPurple, qualifies: a boundary on the claim it points at.\n\nGray, same claim: one claim at two ends of the paper.")


def build_graph(v, chapters, cards):
    nodes, edges, x0 = [], [], 0
    for s, subs in chapters:
        bottom = 0
        for j, (ssid, stitle, members) in enumerate(subs):
            xj = x0 + PAD + j * (W + 2 * PAD)
            y = LABEL_H + PAD
            if ssid:
                gy = y
                y += LABEL_H
            for c in members:
                d = fnode(c, xj, y, W, full=True)
                nodes.append(d)
                y += d['height'] + GAPY
            y -= GAPY
            if ssid:
                y += PAD // 2
                nodes.append(dict(id=re.sub(r'\W', '_', ssid), type='group', x=xj - PAD // 2, y=gy, width=W + PAD, height=y - gy, label=stitle))
            bottom = max(bottom, y)
        width = max(1, len(subs)) * (W + 2 * PAD)
        nodes.append(dict(id='S_' + re.sub(r'\W', '_', s['file']), type='group', x=x0, y=0, width=width, height=bottom + PAD, label=f"{s['num']} {s['title']}"))
        x0 += width + GAPX
    nodes = legend('G', 0, -(LABEL_H + PAD + 190 + 80), GRAPH_TITLE, GRAPH_EDGES) + nodes
    k = 0
    for c in cards.values():
        for verb, t in c['edges']:
            if verb in ('supports', 'licenses', 'qualifies'):
                continue
            edges.append(dict(id=f'e{k}', fromNode=c['bid'], fromSide='right', toNode=t, toSide='left', label=verb.replace(' as', ''), color=VERB_COLOR.get(verb, GRAY)))
            k += 1
    (v.root / 'Skeleton-graph.canvas').write_text(json.dumps(dict(nodes=nodes, edges=edges), indent='\t', ensure_ascii=False) + '\n')
    return len(nodes), len(edges)


def build_argument(v, cards):
    sup = collections.defaultdict(list)     # parent -> children (child supports parent)
    parent, lic, qual, same = {}, collections.defaultdict(list), {}, []
    for c in cards.values():
        for verb, t in c['edges']:
            if verb == 'supports':
                if c['bid'] not in parent:
                    parent[c['bid']] = t
                    sup[t].append(c['bid'])
                else:
                    sup.setdefault(t, [])
                    same.append((c['bid'], t, 'supports'))
            elif verb == 'licenses':
                lic[c['bid']].append(t)
            elif verb == 'qualifies':
                qual[c['bid']] = t
            elif verb == 'same claim as':
                same.append((c['bid'], t, 'same claim'))
    in_tree = set(parent) | set(sup)
    if not in_tree and not lic and not qual and not same:
        (v.root / 'Skeleton-argument.canvas').write_text(json.dumps(dict(nodes=legend('A', 0, 0, ARG_TITLE, ARG_EDGES), edges=[]), indent='\t', ensure_ascii=False) + '\n')
        return 0, 0
    roots = [b for b in in_tree if b not in parent]
    AW, APITCH, AGAP = 400, 460, 90
    depth_of, x_of = {}, {}

    def place(i, d, x_left):
        depth_of[i] = d
        kids = sup.get(i, [])
        if not kids:
            cx, span = x_left + APITCH / 2, APITCH
        else:
            x, centers = x_left, []
            for k in kids:
                c, sp = place(k, d + 1, x)
                centers.append(c)
                x += sp
            span, cx = x - x_left, (centers[0] + centers[-1]) / 2
        x_of[i] = cx - AW / 2
        return cx, span

    x = APITCH
    for r in roots:
        _, w = place(r, 0, x)
        x += w + APITCH // 2
    side = x + 40
    for a, t, kind in same:   # a same-claim pair sits beside the tree when one end (or both) is not in it
        for end, other in ((a, t), (t, a)):
            if end not in depth_of:
                depth_of[end], x_of[end] = depth_of.get(other, 0), side
                side += APITCH
    max_d = max(depth_of.values()) if depth_of else 0
    for w_ in lic:
        if w_ not in depth_of:
            depth_of[w_] = max_d + 1

    def ah(i):
        return fnode(cards[i], 0, 0, AW, full=False)['height']

    rows = collections.defaultdict(list)
    for i, d in depth_of.items():
        rows[d].append(i)
    row_y, yy = {}, 0
    for d in sorted(rows):
        row_y[d] = yy
        yy += max(ah(i) for i in rows[d]) + AGAP
    warrants = [w_ for w_ in lic if w_ not in x_of]
    order = sorted(warrants, key=lambda w_: sum(x_of.get(t, 0) for t in lic[w_]) / max(1, len(lic[w_])))
    last = -1e9
    for w_ in order:
        want = sum(x_of.get(t, 0) for t in lic[w_]) / max(1, len(lic[w_]))
        x_of[w_] = max(want, last + APITCH)
        last = x_of[w_]
    bx = (max(x_of.values()) if x_of else 0) + AW + 260
    bo = sorted([b for b in qual if b not in x_of], key=lambda b: (row_y.get(depth_of.get(qual[b], 0), 0), qual[b]))
    by, last = {}, -1e9
    for b in bo:
        by[b] = max(row_y.get(depth_of.get(qual[b], 0), 0), last)
        last = by[b] + ah(b) + AGAP // 2
    nodes, edges = [], []
    for i in depth_of:
        nodes.append(fnode(cards[i], x_of[i], row_y[depth_of[i]], AW, full=False))
    for b in bo:
        nodes.append(fnode(cards[b], bx, by[b], AW, full=False))
    nodes = legend('A', 0, -(LABEL_H + PAD + 190 + 120), ARG_TITLE, ARG_EDGES) + nodes
    placed = set(depth_of) | set(bo)
    k = 0

    def edge(a, b, fs, ts, col, lab):
        nonlocal k
        if a in placed and b in placed:
            edges.append(dict(id=f'a{k}', fromNode=a, fromSide=fs, toNode=b, toSide=ts, color=col, label=lab))
            k += 1

    for child, p in parent.items():
        edge(child, p, 'top', 'bottom', GREEN, 'supports')
    for a, t, kind in same:
        if kind == 'supports':
            edge(a, t, 'top', 'bottom', GREEN, 'supports')
        else:
            edge(a, t, 'right', 'left', GRAY, 'same claim')
    for w_, targets in lic.items():
        for t in targets:
            edge(w_, t, 'top', 'bottom', BLUE, 'licenses')
    for b, t in qual.items():
        edge(b, t, 'left', 'right', PURPLE, 'qualifies')
    (v.root / 'Skeleton-argument.canvas').write_text(json.dumps(dict(nodes=nodes, edges=edges), indent='\t', ensure_ascii=False) + '\n')
    return len(placed), len(edges)


def build_md(v, chapters, cards, arg_ids, fm):
    def emb(c):
        return f"![[{c['file']}#^{c['bid']}]]"

    def link(c):
        return f"[[{c['file']}#{c['heading']}|{c['num']}]]"

    stars = [c for c in cards.values() if c['chapter']]
    thesis = [c for c in stars if c['file'] == chapters[-1][0]['file']] + [c for c in stars if c['file'] == chapters[0][0]['file']]
    md = ['---', 'title: Paper skeleton'] + fm + ['---', '', '# Paper skeleton', '']
    md.append(f'One load-bearing sentence per paragraph of the main text, numbered straight through in reading order: the paper read in '
              f'{len(cards)} sentences. A paragraph\'s load-bearing sentence is the sentence the paragraph exists to deliver: remove it and the '
              'paragraph has no claim; the other sentences either lead up to it (background, evidence, numbers) or hang from it (refer back to '
              'it, parallel it, point to it). When two sentences qualify, the one later text depends on wins: the antecedent of a back-reference, '
              'the opener of a parallel structure, or the anchor of a summary box, abstract, or conclusion sentence. For a procedure or definition '
              'block whose sentences are parallel details that no later text cites, the run-in heading is the load-bearing element. One sentence '
              'per section is the chapter\'s load-bearing sentence (★), the one its other paragraphs serve. Boxes contribute the sentence other '
              'sections cite.')
    md.append('')
    md.append(f'The sentences live in the section files under `sections/`, one heading per paragraph with the sentence, its `file:line` in the '
              f'manuscript, its role, and what rests on it; this list and both canvases only reference them, so an edit in a section file shows '
              f'up everywhere. Each sentence carries `\\label{{sk|<block id>}}` in the tex, which is how `sync` finds it again after every edit. '
              'The sentences were extracted verbatim from the `.tex` (LaTeX rendered to plain text) at the commit in the frontmatter; the '
              'manuscript is the source of truth.')
    md.append('')
    md.append('Two drawings of the same cards: [[Skeleton-graph.canvas]] keeps reading order, one group per section, with arrows for the '
              'promises, evidence, and cross-references the text itself states. [[Skeleton-argument.canvas]] is the argument map: contention '
              'on top, findings under the claim they hold up, judging rules along the bottom, boundaries on the right. The role tag on each card '
              '(claim, question, method, finding, boundary, nav) is its color on both canvases; the legends are on the canvases.')
    if thesis:
        md += ['', '**Thesis to read every line against**', '']
        for c in thesis:
            md += [emb(c), '']
    md += ['**Three checks** (the writing-center reverse-outline procedure)', '',
           '1. Relation: does the sentence relate back to the thesis, directly or through the sentence it supports?',
           '2. Transition: does the sentence follow from the one before it without a step the reader has to supply?',
           '3. Repetition: where two sentences say the same thing, is the second one doing a job the first cannot?']
    k = 0
    for s, subs in chapters:
        md += ['', f"## {s['title']}", '', f"Section file: [[{s['file']}]]", '']
        for _, _, members in subs:
            for c in members:
                k += 1
                md.append(f'{k}. {emb(c)}')
    omitted = [c for c in cards.values() if c['bid'] not in arg_ids]
    if arg_ids:
        md += ['', '## Cards left out of the argument map', '']
        for reason, role in [('Questions and motivation are not nodes of an argument map', 'question'), ('Procedure without an inferential role', 'method'),
                             ('Navigation', 'nav'), ('Not yet judged', 'unset')]:
            ns = [c for c in omitted if c['role'] == role and not c['leftout']]
            if ns:
                md.append(f"- {reason}: " + ', '.join(link(c) for c in ns) + '.')
        cases = [c for c in omitted if c['leftout']]
        if cases:
            md.append('- Case by case: ' + '; '.join(f"{link(c)} {c['leftout']}" for c in cases) + '.')
        rest = [c for c in omitted if c['role'] not in ('question', 'method', 'nav', 'unset') and not c['leftout']]
        if rest:
            md.append('- No reason recorded (add a **Left out.** line or a relation): ' + ', '.join(link(c) for c in rest) + '.')
    md.append('')
    (v.root / 'Skeleton.md').write_text('\n'.join(md))


def cmd_build(v, after_sync=None):
    chapters, cards = v.load_cards()
    if not cards:
        die('no cards in sections/; run bootstrap first')
    problems = v.census(cards)
    fm = v.frontmatter()
    gn, ge = build_graph(v, chapters, cards)
    an, ae = build_argument(v, cards)
    arg = json.loads((v.root / 'Skeleton-argument.canvas').read_text())
    arg_ids = {n['id'] for n in arg['nodes'] if n['type'] == 'file'}
    build_md(v, chapters, cards, arg_ids, fm)
    if after_sync:
        for label, items in zip(('moved', 'updated', 'missing'), after_sync):
            print(f'sync {label} {len(items)}' + (':\n  ' + '\n  '.join(items) if items else ''))
    print(f"cards {len(cards)} (chapter {sum(c['chapter'] for c in cards.values())}); roles {dict(collections.Counter(c['role'] for c in cards.values()))}")
    print(f'graph canvas: {gn} nodes incl. groups/legend, {ge} edges; argument canvas: {an} cards, {ae} edges; omitted {len(cards) - an}')
    print(f'source {fm[1].split(": ", 1)[1]}')
    if v.tex.warnings:
        print('unrendered macros (set "macros" in skeleton.json):', ', '.join(f'\\{n} x{k}' for n, k in v.tex.warnings.most_common()))
    print('paragraph census:', 'OK' if not problems else '')
    for p in problems:
        print('  PROBLEM', p)
    return problems


# --------------------------------------------------------------------------- check: a synthetic manuscript
SYNTH_MAIN = r"""\documentclass{article}
\newcommand{\symfoo}{\textsc{Foo$_{\mathrm{X}}$}\xspace}
\newcommand{\refa}[1]{\textbf{#1}}
\newtcolorbox{rqbox}{}
\begin{document}
\begin{abstract}
This paper proposes a thing.\label{sk|abs1}
It also measures the thing on \symfoo twice.
\end{abstract}
\input{sections/intro}
\input{sections/method.tex}
\input{sections/tables/t1}
\end{document}
"""
SYNTH_INTRO = r"""\section{Introduction}
\label{sec|intro}
Long-tailed data degrades models, e.g. Fig. 3 shows it. This is the second sentence.
Therefore the study is needed.

\begin{rqbox}
How does \symfoo change under mixing?
\end{rqbox}

\textbf{Contributions.}
The contributions of this paper are:
\begin{enumerate}
\item A framework is proposed (see Section~\ref{sec|method}).
\item A finding is reported at \refa{A1}.
\end{enumerate}
"""
SYNTH_METHOD = r"""\section{Method}
\subsection{Design}
\label{sec|method}
The pipeline has two tasks: training and evaluation.
\begin{figure}
\centering
\caption{A figure.}
\end{figure}
For each dataset, configurations are defined:
(1) six baselines, and
(2) ninety-six mixes.
The rest of the paragraph explains why.
"""
SYNTH_TABLE = r"""\begin{table}
\begin{tabular}{ll}
a & b \\
\end{tabular}
\end{table}
"""


def cmd_check():
    import shutil, tempfile
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='skel_check_'))
    paper, vault = tmp / 'paper', tmp / 'vault'
    (paper / 'sections' / 'tables').mkdir(parents=True)
    (paper / 'main.tex').write_text(SYNTH_MAIN)
    (paper / 'sections' / 'intro.tex').write_text(SYNTH_INTRO)
    (paper / 'sections' / 'method.tex').write_text(SYNTH_METHOD)
    (paper / 'sections' / 'tables' / 't1.tex').write_text(SYNTH_TABLE)
    (paper / 'output').mkdir()
    (paper / 'output' / 'main.aux').write_text('\\newlabel{sec|intro}{{1}{1}}\n\\newlabel{sec|method}{{2.1}{2}}\n')
    me = pathlib.Path(__file__).resolve()

    def run(*args, ok=True):
        r = subprocess.run([sys.executable, str(me), *args, '--vault', str(vault)], capture_output=True, text=True)
        assert (r.returncode == 0) == ok, r.stdout + r.stderr
        return r.stdout + r.stderr

    out = run('init', str(paper / 'main.tex'))
    cfg = json.loads((vault / 'skeleton.json').read_text())
    assert [s['tex'] for s in cfg['sections']] == ['main.tex', 'sections/intro.tex', 'sections/method.tex'], cfg
    assert cfg['boxes'] == ['rqbox'] and [s['num'] for s in cfg['sections']] == ['Abs', 'I', 'II'], cfg
    out = run('bootstrap')
    assert '8 cards' in out and '7 labels' in out and 'dry run' in out and not (vault / 'sections').exists(), out
    out = run('bootstrap', '--write')
    intro = (paper / 'sections' / 'intro.tex').read_text()
    assert intro.count('\\label{sk|') == 5 and 'shows it.\\label{sk|i1} This is' in intro and '\\textbf{Contributions.}\\label{sk|i2}' in intro, intro
    assert 'mixing?\\label{sk|rqbox1}' in intro and 'Section~\\ref{sec|method}).\\label{sk|i3}' in intro, intro
    method = (paper / 'sections' / 'method.tex').read_text()
    assert 'evaluation.\\label{sk|iia1}' in method and 'ninety-six mixes.\\label{sk|iia2}' in method, method
    assert SYNTH_MAIN.count('\\label{sk|abs1}') == 1 and (paper / 'main.tex').read_text().count('\\label{sk|') == 1  # existing label kept, not duplicated
    card = (vault / 'sections' / '01 I Introduction.md').read_text()
    assert 'Long-tailed data degrades models, e.g. Fig. 3 shows it. ^i1' in card and 'How does Foo_X change under mixing? ^rqbox1' in card, card
    assert 'A finding is reported at A1. ^i4' in card and '(see Section 2.1). ^i3' in card, card
    m = (vault / 'sections' / '02 II Method.md').read_text()
    assert '## II-A Design' in m and '`method:9-11`' in m and 'six baselines, and (2) ninety-six mixes. ^iia2' in m, m
    out = run('build')
    assert 'paragraph census: OK' in out and 'cards 8' in out, out
    # edits: small change with label, rewrite with label, rewrite without label, insert a line, add a paragraph
    lines = (paper / 'sections' / 'intro.tex').read_text().split('\n')
    lines[2] = lines[2].replace('degrades models', 'hurts models')                  # small edit, label kept -> updated
    lines[6] = 'Is anything different now?\\label{sk|rqbox1}'                       # rewrite, label kept -> updated, flagged
    lines.insert(1, 'An inserted line before everything.')                          # -> every card after it moves
    lines += ['', 'A brand new paragraph with no card.']
    (paper / 'sections' / 'intro.tex').write_text('\n'.join(lines))
    lines = (paper / 'sections' / 'method.tex').read_text().split('\n')
    lines[3] = 'The pipeline has been rewritten entirely without its label.'
    (paper / 'sections' / 'method.tex').write_text('\n'.join(lines))
    out = run('sync')
    counts = dict(re.findall(r'^sync (\w+) (\d+)', out, re.M))
    assert counts == {'moved': '5', 'updated': '2', 'missing': '1'}, out
    assert '+ Long-tailed data hurts models, e.g. Fig. 3 shows it.' in out and 'II-A.1 method:4' in out.split('missing')[1], out
    assert 'Rqbox-1 intro:8  (rewrite, re-judge the card)' in out and 'II-A.2 method:9-11' not in out, out
    assert 'intro.tex:2-2 (para) has 0 cards' in out and 'II-A.1 has no \\label{sk|iia1}' in out and 'intro.tex:19-19 (para) has 0 cards' in out, out
    assert 'unrendered macros' not in out, out
    assert out.count('PROBLEM') == 3, out
    out2 = run('sync')
    assert dict(re.findall(r'^sync (\w+) (\d+)', out2, re.M)) == {'moved': '0', 'updated': '0', 'missing': '1'}, out2
    shutil.rmtree(tmp)
    print('check: ok (init 3 sections + 1 box env, bootstrap 8 cards + 7 labels with 1 kept, build clean, sync 5 moved / 2 updated / 1 missing, census 3 problems, idempotent)')


# --------------------------------------------------------------------------- main
def main():
    args = sys.argv[1:]
    vault_dir = '.'
    if '--vault' in args:
        i = args.index('--vault')
        vault_dir = args[i + 1]
        del args[i:i + 2]
    if not args or args[0] not in ('init', 'bootstrap', 'build', 'sync', 'check'):
        print(__doc__)
        sys.exit(2)
    cmd = args[0]
    if cmd == 'check':
        return cmd_check()
    if cmd == 'init':
        if len(args) < 2:
            die('init needs the path to main.tex')
        return cmd_init(args[1], vault_dir)
    v = Vault(vault_dir).load()
    if cmd == 'bootstrap':
        return cmd_bootstrap(v, '--write' in args)
    if cmd == 'sync':
        result = v.sync()
        return cmd_build(v, after_sync=result)
    return cmd_build(v)


if __name__ == '__main__':
    main()
