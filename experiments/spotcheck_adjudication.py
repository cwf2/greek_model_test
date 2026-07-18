"""Tallies the human-adjudicated spot-check sample for reports/spotcheck_adjudication.md.

This does NOT reproduce the human judgments themselves -- those are recorded by
hand in data/spotchecks/spotcheck_sample.csv via spotcheck_review.py's browser
interface, and can't be regenerated. This script only computes summary statistics
over already-adjudicated data.

Prerequisite: data/spotchecks/spotcheck_sample.csv fully adjudicated (every row's
human_judgement column filled in).

    python3 experiments/spotcheck_adjudication.py
"""

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parent.parent
SAMPLE = REPO_ROOT / "data" / "spotchecks" / "spotcheck_sample.csv"

# categories where exactly one model disagrees with the other two on POS
ODD_ONE_OUT = {"trf": "pos_2v1_trf_odd", "lg": "pos_2v1_lg_odd", "odycy": "pos_2v1_odycy_odd"}


def credits_model_on_pos(judgement: str, model: str) -> bool:
    """True only if `judgement` cleanly credits `model` for the POS call
    specifically -- excludes mixed POS/lemma verdicts where the model won on
    lemma but not POS (e.g. "trf+odycy (POS) / lg+trf (lemma)" should NOT
    credit lg), and excludes "ambiguous"/"none" verdicts."""
    j = judgement.strip().lower()
    if j.startswith("ambiguous") or j.startswith("none") or j == "":
        return False
    if "(pos)" in j or "(lemma)" in j:
        # mixed verdict -- only the clause before "(POS)" counts for POS credit
        pos_clause = j.split("(pos)")[0] if "(pos)" in j else ""
        return model in pos_clause
    return model in j


def main():
    df = pd.read_csv(SAMPLE, dtype=str, keep_default_na=False)

    print("Category breakdown:")
    print(df["category"].value_counts().to_string())
    print()

    print("Odd-one-out accuracy (was the minority model actually right?):")
    for model, category in ODD_ONE_OUT.items():
        sub = df[df["category"] == category]
        right = sub["human_judgement"].apply(lambda j: credits_model_on_pos(j, model))
        print(f"  {model}: {right.sum()}/{len(sub)}")
        for _, row in sub[right].iterrows():
            print(f"    {row['text']!r}: {row['human_judgement']}")
    print()

    unresolved = df[df["notes"].str.contains("REVIEW", na=False)]
    print(f"{len(unresolved)} rows still flagged REVIEW (unresolved / needs second pass):")
    for _, row in unresolved.iterrows():
        print(f"  {row['text']!r} ({row['work']}): {row['notes'][:100]}")


if __name__ == "__main__":
    main()
