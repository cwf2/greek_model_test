"""Reproduces the ὅστε/generalizing-relative univerbation findings in
reports/pronoun_te_univerbation.md.

Prerequisite: `python3 compare_models.py` (writes data/comparison/aligned_tokens.csv).

    python3 experiments/pronoun_te_univerbation.py
"""

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parent.parent
ALIGNED = REPO_ROOT / "data" / "comparison" / "aligned_tokens.csv"

# The ὅστε "generalizing relative" family: relative pronoun (ὅς/ἥ/οἵ/αἵ) + enclitic
# connective τε, univerbated into one orthographic word (elided to -τʼ before a vowel).
FORMS = ["ὅστε", "ἥτε", "οἵτε", "αἵτε", "αἵτʼ", "ἥντε", "οἵτʼ", "ἥτʼ"]
MODELS = ["lg", "trf", "odycy"]


def main():
    df = pd.read_csv(ALIGNED, dtype=str, keep_default_na=False)
    sub = df[df["text"].isin(FORMS)].copy()

    print(f"Found {len(sub)} instances of the ὅστε family across the corpus:")
    print(sub[["work", "line_id", "text"] + [f"{m}_pos" for m in MODELS] + [f"{m}_lemma" for m in MODELS]]
          .to_string(index=False))
    print()

    by_work = sub["work"].value_counts()
    print("By text:")
    for work, n in by_work.items():
        print(f"  {work}: {n}")
    if len(by_work) == 1:
        print(f"  -> concentrated entirely in {by_work.index[0]}, not spread across the corpus.")
    print()

    pos_cols = [f"{m}_pos" for m in MODELS]
    all_agree = sub[pos_cols].nunique(axis=1) == 1
    print(f"3-way POS agreement: {all_agree.sum()}/{len(sub)}")
    disagreements = sub[~all_agree]
    if len(disagreements):
        print("Disagreements:")
        print(disagreements[["work", "line_id", "text"] + pos_cols].to_string(index=False))
    print()

    lemma_cols = [f"{m}_lemma" for m in MODELS]
    resolved_to_hoste = sub[lemma_cols].apply(lambda row: (row == "ὅστε").all(), axis=1)
    print(f"Lemma correctly resolved to ὅστε on all 3 models: {resolved_to_hoste.sum()}/{len(sub)}")
    unresolved = sub[~resolved_to_hoste]
    if len(unresolved):
        print("Not resolved on all three:")
        print(unresolved[["text"] + lemma_cols].to_string(index=False))


if __name__ == "__main__":
    main()
