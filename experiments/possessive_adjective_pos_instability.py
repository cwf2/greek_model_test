"""Reproduces the grc_dep_web_lg possessive-adjective POS instability findings in
reports/possessive_adjective_pos_instability.md.

Prerequisite: `python3 compare_models.py` (writes data/comparison/aligned_tokens.csv).

    python3 experiments/possessive_adjective_pos_instability.py
"""

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parent.parent
ALIGNED = REPO_ROOT / "data" / "comparison" / "aligned_tokens.csv"

FAMILY = ["ἐμός", "σός", "ἡμέτερος", "ὑμέτερος", "σφέτερος"]
MODELS = ["lg", "trf", "odycy"]


def main():
    df = pd.read_csv(ALIGNED, dtype=str, keep_default_na=False)
    # A token counts if *any* model resolved its lemma to one of the family --
    # lemma resolution itself is unreliable on inflected/elided forms here (a
    # separate finding), so anchoring to one model's lemma alone would undercount.
    mask = False
    for m in MODELS:
        mask = mask | df[f"{m}_lemma"].isin(FAMILY)
    sub = df[mask]

    print(f"{len(sub)} tokens where at least one model resolved the lemma to the "
          f"possessive-adjective family {FAMILY}.")
    print()

    for m in MODELS:
        print(f"{m} POS distribution:")
        print(sub[f"{m}_pos"].value_counts().to_string())
        print()

    agree = sub[[f"{m}_pos" for m in MODELS]].nunique(axis=1) == 1
    print(f"3-way POS agreement: {100*agree.mean():.1f}% ({agree.sum()}/{len(sub)})")

    lg_det_rate = (sub["lg_pos"] == "DET").mean()
    print(f"lg tags DET: {100*lg_det_rate:.2f}% of the time")
    disagree_det = sub[(sub["lg_pos"] == "DET") & (sub["trf_pos"] == "ADJ") & (sub["odycy_pos"] == "ADJ")]
    print(f"  of which lg=DET vs trf=odycy=ADJ specifically: {len(disagree_det)}")
    print()

    # The single most telling data point: does the identical surface form get
    # different tags from lg across different occurrences?
    for form in sub["text"].value_counts().head(20).index:
        form_rows = sub[sub["text"] == form]
        lg_tags = form_rows["lg_pos"].unique()
        if len(lg_tags) > 1:
            print(f"'{form}' gets {len(lg_tags)} different lg tags across its "
                  f"{len(form_rows)} occurrences: {sorted(lg_tags)}")


if __name__ == "__main__":
    main()
