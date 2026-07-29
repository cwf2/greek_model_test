"""How well do the three existing parsers' dependency structure transfer to
Quintus (Posthomerica), a text none of them were trained on?

Reads the three per-model CSVs treebank_base.py wrote for Posthomerica book 1,
lines 1-30, aligns them token-by-token (all three happen to tokenize this
passage identically -- 212 tokens, 9 sentences each -- so no difflib alignment
is needed here, unlike compare_models.py's odyCy handling), and reports
per-sentence agreement on head+deprel.

    python3 experiments/treebank_agreement.py

See reports/treebank_agreement.md for the writeup.
"""
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parent.parent
IN_DIR = REPO_ROOT / "data" / "treebanks_base"
STEM = "tlg2046.tlg001.perseus-grc2.1.1-31"
MODELS = ["grc_dep_web_lg", "grc_dep_web_trf", "grc_odycy_joint_trf"]


def load(model):
    return pd.read_csv(IN_DIR / f"{STEM}.{model}.csv", keep_default_na=False)


def main():
    frames = {m: load(m) for m in MODELS}

    lengths = {m: len(df) for m, df in frames.items()}
    if len(set(lengths.values())) != 1:
        raise SystemExit(f"token count mismatch, alignment assumption broken: {lengths}")

    base = frames[MODELS[0]][["sent_id", "sent_token_id", "urn", "text"]].copy()
    for m in MODELS:
        mismatches = (frames[m]["text"].values != base["text"].values).sum()
        if mismatches:
            raise SystemExit(f"{m}: {mismatches} token-text mismatches vs {MODELS[0]}, alignment assumption broken")
        base[f"{m}_head"] = frames[m]["head"].values
        base[f"{m}_deprel"] = frames[m]["deprel"].values

    head_cols = [f"{m}_head" for m in MODELS]
    deprel_cols = [f"{m}_deprel" for m in MODELS]

    base["heads_agree"] = base[head_cols].nunique(axis=1) == 1
    base["deprels_agree"] = base[deprel_cols].nunique(axis=1) == 1
    base["fully_agree"] = base["heads_agree"] & base["deprels_agree"]

    print(f"{len(base)} tokens across {base['sent_id'].nunique()} sentences\n")
    print("Token-level agreement:")
    print(f"  head agrees (all 3):    {base['heads_agree'].sum()}/{len(base)}")
    print(f"  deprel agrees (all 3):  {base['deprels_agree'].sum()}/{len(base)}")
    print(f"  both agree (all 3):     {base['fully_agree'].sum()}/{len(base)}")
    print()

    print("Per-sentence classification:")
    per_sent = base.groupby("sent_id")["fully_agree"].agg(["sum", "count"])
    for sent_id, row in per_sent.iterrows():
        if row["sum"] == row["count"]:
            label = "unanimous"
        elif row["sum"] >= row["count"] / 2:
            label = "majority"
        else:
            label = "split"
        print(f"  sentence {sent_id}: {int(row['sum'])}/{int(row['count'])} tokens fully agree -> {label}")

    print()
    print("Disagreeing tokens (head and/or deprel):")
    disagree = base[~base["fully_agree"]]
    for _, r in disagree.iterrows():
        print(f"  {r['urn']} sent {r['sent_id']} tok {r['sent_token_id']} {r['text']!r}: "
              + " / ".join(f"{m}={r[f'{m}_head']}:{r[f'{m}_deprel']}" for m in MODELS))


if __name__ == "__main__":
    main()
