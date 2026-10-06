"""Tests for the draft-side measurement: comments and structure lines dropped, citations numbered
per file, display math counted as a formula without splitting its block, one sentence per line."""
import measure_tex_section as mt

TEX = r"""\section{Background}
\label{sec:background}

%% header comment with words that must not count

\textbf{The step.}
The step takes candidates~\citep{a2020, b2021} and Section~\ref{sec:x} defines $\mathcal{C}$.
XYZ is \emph{Made Up Score}~\citep{a2020}; the score is
\begin{equation}
  r = \frac{1}{j} \sum_k m_k
\end{equation}
and it is read per image.

\textbf{The rule.}
The rule picks the highest test score. It never looks at the map.
"""


def test_normalize_and_measure():
    m = mt.measure(TEX)
    assert len(m["blocks"]) == 2 and m["formulas"] == 1
    assert m["blocks"] == [25, 15]                    # label 2 + 9 + 8 + 6; label 2 + 13
    assert m["cite_groups"] == 2 and m["cite_refs"] == 3 and m["keys"] == 2
    assert m["sentences"] == 6 and m["max"] == 13
    assert len(m["two_sentence_lines"]) == 1 and m["two_sentence_lines"][0].startswith("The rule picks")


def test_abbreviations_are_not_sentence_breaks():
    m = mt.measure("Methods such as RISE, i.e. deletion curves, are common.\n")
    assert m["two_sentence_lines"] == [] and m["words"] == 10   # i.e. counts as two tokens


def test_citation_forms_and_floats():
    t = r"""Text before~\citep[Section 4]{a2020} and \citeauthor{b2021} say so~\citep{c,} more.
A row ends with \\[4pt] here.
\begin{figure}
  \includegraphics[width=\linewidth]{fig.pdf}
  \caption{A caption sentence.}
\end{figure}
Display \[ x = 1 \] follows.
"""
    m = mt.measure(t)
    assert (m["cite_groups"], m["keys"]) == (3, 3)          # optional argument, \citeauthor, empty key
    assert m["floats"] == 1 and m["formulas"] == 1           # figure removed whole; \[ \] is math, \\[4pt] is not
    assert m["sentences"] == 3 and m["words"] == 6 + 5 + 2   # "4pt" and the caption are gone, the placeholder is no word
