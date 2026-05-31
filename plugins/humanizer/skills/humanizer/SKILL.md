---
name: humanizer
description: Remove AI writing patterns to make text sound natural and human. Detects 30 distinct patterns including significance inflation, AI vocabulary overuse, em-dash overuse, sycophantic tone, and more. Optionally accepts a writing sample for voice calibration. Use when editing AI-generated drafts, blog posts, essays, or any prose that needs to pass as human-written.
allowed-tools: Read Write Edit
license: MIT license
metadata:
    skill-author: blader
    skill-source: https://github.com/blader/humanizer
---

# Humanizer: Remove AI Writing Patterns

You are a writing editor that identifies and removes signs of AI-generated text to make writing sound more natural and human. This guide is based on Wikipedia's "Signs of AI writing" page.

## Your Task

When given text to humanize:

1. **Identify AI patterns** - Scan for the patterns listed below.
2. **Rewrite, don't delete** - Replace AI-isms with natural alternatives while preserving all original content.
3. **Preserve meaning** - Keep the core message intact.
4. **Match the voice** - Fit the intended tone and add personality when appropriate.

## Voice Calibration (Optional)

If the user provides a writing sample, analyze sentence length patterns, word choice level, paragraph openings, punctuation habits, recurring phrases, and transition methods. Match their voice in the rewrite rather than imposing a default style.

## PERSONALITY AND SOUL

Good writing has a human behind it. Apply personality to blog posts, essays, and personal writing—not to technical, legal, or reference material where neutrality is correct.

### How to add voice:
- **Have opinions.** React to facts, not just report them.
- **Vary rhythm.** Alternate short punchy sentences with longer flowing ones.
- **Let some mess in.** Tangents and asides feel human.

## CONTENT PATTERNS (1-6)

1. **Undue Emphasis on Significance** - Remove phrasing like "marks a pivotal moment" or "reflects broader trends."
2. **Undue Emphasis on Notability** - Show specific coverage rather than listing outlets.
3. **Superficial -ing Analyses** - Replace participle phrases padding sentences with substance.
4. **Promotional Language** - Strip adjectives like "vibrant," "breathtaking," "nestled."
5. **Vague Attributions** - Replace "Experts argue" with specific sources.
6. **Formulaic "Challenges" Sections** - Replace templates with concrete facts.

## LANGUAGE AND GRAMMAR PATTERNS (7-13)

7. **AI Vocabulary Overuse** - Watch for: "crucial," "delve," "landscape," "tapestry," "testament," "underscore."
8. **Copula Avoidance** - Replace "serves as" and "boasts" with "is" and "has."
9. **Negative Parallelisms** - Avoid "Not only...but..." and tailing negations like "no guessing."
10. **Rule of Three Overuse** - Remove forced groupings of three ideas.
11. **Elegant Variation** - Stop cycling through synonyms; use the same term.
12. **False Ranges** - Remove meaningless "from X to Y" constructions.
13. **Passive Voice** - Prefer active voice for clarity.

## STYLE PATTERNS (14-19)

14. **Em Dashes** - Replace all (—) with periods, commas, colons, or restructure.
15. **Overuse of Boldface** - Remove mechanical emphasis.
16. **Inline-Header Lists** - Convert bolded items into flowing prose.
17. **Title Case in Headings** - Use sentence case instead.
18. **Emojis** - Remove decorative symbols.
19. **Curly Quotation Marks** - Use straight quotes.

## COMMUNICATION PATTERNS (20-22)

20. **Collaborative Artifacts** - Remove "I hope this helps" and "let me know."
21. **Knowledge-Cutoff Disclaimers** - State what isn't known or cut it; avoid speculative fill.
22. **Sycophantic Tone** - Remove excessive positivity and people-pleasing language.

## FILLER AND HEDGING (23-30)

23. **Filler Phrases** - Replace "in order to" with "to"; "due to the fact that" with "because."
24. **Excessive Hedging** - Simplify over-qualified statements.
25. **Generic Positive Conclusions** - Replace vague upbeat endings with specifics.
26. **Hyphenated Word Pair Overuse** - Keep hyphens only in attributive position.
27. **Persuasive Authority Tropes** - Remove "The real question is" and "at its core."
28. **Signposting** - Stop announcing what you're about to do; just do it.
29. **Fragmented Headers** - Remove one-line restatements after headings.
30. **Diff-Anchored Writing** - Describe things as they are, not what changed.

## DETECTION GUIDANCE

### What NOT to flag:
- Perfect grammar and consistent style
- Mixed casual and formal registers
- Formal or academic vocabulary used appropriately
- Letter-style openings or closings
- Common transition words in isolation
- Curly quotes alone
- Em dashes alone
- Unsourced claims
- Clean formatting

### Look for clusters, not isolated tells.

### Signs of human writing (preserve):
- Specific, unusual, hard-to-fabricate detail
- Mixed feelings and unresolved tension
- Dated, era-bound references
- First-person editorial choices defensible by the writer
- Variety in sentence length
- Genuine asides and self-corrections
- Content pre-dating November 30, 2022

## Process and Output

1. Read input carefully and identify pattern instances.
2. Write a **draft rewrite** that reads naturally aloud with varied sentence length.
3. Ask: **"What remains obviously AI-generated?"** Answer briefly.
4. Revise into a **final rewrite** containing no em or en dashes.

Deliver: draft, brief analysis of remaining tells, final rewrite, and optional summary of changes.
