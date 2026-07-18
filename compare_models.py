"""Compare tagging output of three spaCy models across the epic corpus.

Reads the per-model token tables in data/tokens/ (produced by modeltest.py),
aligns tokens across models, and writes:

  data/comparison/aligned_tokens.csv      every token comparable across all 3 models
  data/comparison/tokenization_mismatches.csv   lines where odyCy segments differently
  data/comparison/summary_by_text.csv     agreement rates per text
  data/comparison/summary_overall.csv     agreement rates over the whole corpus
  data/comparison/pos_confusion_*.csv     POS confusion matrices, pairwise
"""

import difflib
import os
import unicodedata
from collections import Counter

import pandas as pd

DATA_DIR = "data/tokens"
OUT_DIR = "data/comparison"
os.makedirs(OUT_DIR, exist_ok=True)

MODELS = ["grc_odycy_joint_trf", "grc_dep_web_lg", "grc_dep_web_trf"]
PIVOT = "grc_dep_web_lg"          # lg & trf always tokenize identically
OTHER_LATINCY = "grc_dep_web_trf"
ODYCY = "grc_odycy_joint_trf"

TEXTS = [
    ("tlg0001.tlg001.perseus-grc2", "Argonautica"),
    ("tlg0012.tlg001.perseus-grc2", "Iliad"),
    ("tlg0012.tlg002.perseus-grc2", "Odyssey"),
    ("tlg0647.tlg001.perseus-grc2", "Sack of Troy"),
    ("tlg2045.tlg001.perseus-grc2", "Dionysiaca"),
    ("tlg2046.tlg001.perseus-grc2", "Posthomerica"),
]

MORPH_FIELDS = ["verbform", "mood", "tense", "voice", "person", "number", "case", "gender"]
ALL_FIELDS = ["pos", "lemma"] + MORPH_FIELDS


def strip_accents(s):
    if not s:
        return s
    decomp = unicodedata.normalize("NFD", s)
    return "".join(c for c in decomp if not unicodedata.combining(c))


def load(stem, model):
    df = pd.read_csv(os.path.join(DATA_DIR, f"{stem}.{model}.csv"), keep_default_na=False)
    return df


def align_text(stem, work_name):
    lg = load(stem, "grc_dep_web_lg")
    trf = load(stem, "grc_dep_web_trf")
    ody = load(stem, ODYCY)

    assert len(lg) == len(trf) and (lg["text"].values == trf["text"].values).all(), \
        f"{stem}: lg/trf tokenization mismatch, alignment assumption violated"

    # group each df's row-indices by line_id, preserving first-seen order
    def line_groups(df):
        groups = {}
        order = []
        for idx, lid in enumerate(df["line_id"].values):
            if lid not in groups:
                groups[lid] = []
                order.append(lid)
            groups[lid].append(idx)
        return groups, order

    lg_groups, lg_order = line_groups(lg)
    ody_groups, _ = line_groups(ody)

    lg_text = lg["text"].values
    ody_text = ody["text"].values

    aligned_rows = []
    mismatch_rows = []

    for lid in lg_order:
        lg_idx = lg_groups[lid]
        ody_idx = ody_groups.get(lid, [])

        lg_toks = [lg_text[i] for i in lg_idx]
        ody_toks = [ody_text[i] for i in ody_idx]

        if lg_toks == ody_toks:
            # trivial 1:1 alignment, no need for difflib
            pairs = list(zip(lg_idx, ody_idx))
            exact = True
        else:
            sm = difflib.SequenceMatcher(None, lg_toks, ody_toks, autojunk=False)
            pairs = []
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == "equal":
                    pairs.extend(zip(lg_idx[i1:i2], ody_idx[j1:j2]))
            exact = False

        if not exact:
            mismatch_rows.append(dict(
                stem=stem, work=work_name, urn=lg.at[lg_idx[0], "urn"], line_id=lid,
                lg_trf_tokens=" ".join(lg_toks), odycy_tokens=" ".join(ody_toks),
                n_aligned=len(pairs), n_lg=len(lg_toks), n_odycy=len(ody_toks),
            ))

        for li, oi in pairs:
            row = dict(
                work=work_name, urn=lg.at[li, "urn"], line_id=lid, text=lg_text[li],
                speaker=lg.at[li, "speaker"], level=lg.at[li, "level"],
            )
            for f in ALL_FIELDS:
                row[f"lg_{f}"] = lg.at[li, f]
                row[f"trf_{f}"] = trf.at[li, f]
                row[f"odycy_{f}"] = ody.at[oi, f]
            aligned_rows.append(row)

    return pd.DataFrame(aligned_rows), pd.DataFrame(mismatch_rows)


def agreement_stats(df, work_name=None):
    n = len(df)
    stats = {"work": work_name or "ALL", "n_tokens": n}
    for f in ALL_FIELDS:
        lg_v, trf_v, ody_v = df[f"lg_{f}"], df[f"trf_{f}"], df[f"odycy_{f}"]
        stats[f"{f}_lg_trf"] = (lg_v == trf_v).mean()
        stats[f"{f}_lg_odycy"] = (lg_v == ody_v).mean()
        stats[f"{f}_trf_odycy"] = (trf_v == ody_v).mean()
        stats[f"{f}_all3"] = ((lg_v == trf_v) & (trf_v == ody_v)).mean()
    # lemma ignoring accents/diacritics
    lg_l = df["lg_lemma"].map(strip_accents)
    trf_l = df["trf_lemma"].map(strip_accents)
    ody_l = df["odycy_lemma"].map(strip_accents)
    stats["lemma_noaccent_lg_trf"] = (lg_l == trf_l).mean()
    stats["lemma_noaccent_lg_odycy"] = (lg_l == ody_l).mean()
    stats["lemma_noaccent_trf_odycy"] = (trf_l == ody_l).mean()
    stats["lemma_noaccent_all3"] = ((lg_l == trf_l) & (trf_l == ody_l)).mean()
    return stats


def pos_confusion(df, col_a, col_b, topn=20):
    c = Counter(zip(df[col_a], df[col_b]))
    rows = [{"a": a, "b": b, "count": n} for (a, b), n in c.items() if a != b]
    rows.sort(key=lambda r: -r["count"])
    return pd.DataFrame(rows[:topn])


def main():
    all_aligned = []
    all_mismatch = []
    per_text_stats = []

    for stem, work in TEXTS:
        print(f"Aligning {work} ({stem})...")
        aligned, mismatch = align_text(stem, work)
        print(f"  {len(aligned)} tokens aligned across all 3 models, "
              f"{len(mismatch)} lines with tokenization mismatch")
        all_aligned.append(aligned)
        all_mismatch.append(mismatch)
        per_text_stats.append(agreement_stats(aligned, work))

    aligned_all = pd.concat(all_aligned, ignore_index=True)
    mismatch_all = pd.concat(all_mismatch, ignore_index=True)

    aligned_all.to_csv(os.path.join(OUT_DIR, "aligned_tokens.csv"), index=False)
    mismatch_all.to_csv(os.path.join(OUT_DIR, "tokenization_mismatches.csv"), index=False)

    summary_by_text = pd.DataFrame(per_text_stats)
    summary_by_text.to_csv(os.path.join(OUT_DIR, "summary_by_text.csv"), index=False)

    summary_overall = pd.DataFrame([agreement_stats(aligned_all)])
    summary_overall.to_csv(os.path.join(OUT_DIR, "summary_overall.csv"), index=False)

    pos_confusion(aligned_all, "lg_pos", "trf_pos").to_csv(
        os.path.join(OUT_DIR, "pos_confusion_lg_vs_trf.csv"), index=False)
    pos_confusion(aligned_all, "lg_pos", "odycy_pos").to_csv(
        os.path.join(OUT_DIR, "pos_confusion_lg_vs_odycy.csv"), index=False)
    pos_confusion(aligned_all, "trf_pos", "odycy_pos").to_csv(
        os.path.join(OUT_DIR, "pos_confusion_trf_vs_odycy.csv"), index=False)

    print("\nDone. Outputs written to", OUT_DIR)


if __name__ == "__main__":
    main()
