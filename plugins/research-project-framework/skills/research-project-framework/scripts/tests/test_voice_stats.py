"""One check per feature family on a fixed text, and the draft-side line reader."""
import voice_stats as V

SENTS = [
    "We measure the cost of the rule.",                       # we, short, opener not The
    "The step trains nothing and never looks at the map.",   # The opener, two negations
    "However, the same rule can fail: it ignores the property; nobody checks it.",  # disc, same, hedge, colon, semi
    "Our benchmark covers sixteen datasets, and for example the medical ones were evaluated first by us.",
]


def test_feats_counts():
    f = V.feats(SENTS)
    assert f["sents"] == 4 and f["words"] == 46
    assert f["we100"] == round(100 * 3 / 46, 2)       # We, Our, us
    assert f["neg100"] == round(100 * 2 / 46, 2)      # nothing, never
    assert f["same100"] == round(100 * 1 / 46, 2)
    assert f["disc100"] == round(100 * 3 / 46, 2)     # However, for example, first
    assert f["hedge100"] == round(100 * 1 / 46, 2)    # can
    assert f["start_the"] == 25.0 and f["colon"] == 25.0 and f["semi"] == 25.0
    assert f["short"] == 50.0                         # 7 and 10 words


def test_draft_sentences_drop_labels_and_comments():
    tex = "%% header\n\\textbf{The step.}\nThe step takes candidates~\\citep{a2020}.\n\nWe count this line too.\n"
    s = V.draft_sentences(tex)
    assert s == ["The step takes candidates [1].", "We count this line too."]
