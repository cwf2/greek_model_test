"""Reproduces the elision-apostrophe lemmatization gap in reports/elision_apostrophe_bug.md.

Prerequisite: `python3 compare_models.py` (writes data/comparison/aligned_tokens.csv
and data/comparison/elision_lemma_comparison.csv, which this script reads).

    python3 experiments/elision_apostrophe_bug.py
"""

import unicodedata
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parent.parent
COMPARISON_DIR = REPO_ROOT / "data" / "comparison"

APOSTROPHES = {
    "ʼ": "U+02BC (MODIFIER LETTER APOSTROPHE)",
    "'": "U+0027 (ASCII APOSTROPHE)",
    "’": "U+2019 (RIGHT SINGLE QUOTATION MARK)",
}
MODELS = ["lg", "trf", "odycy"]


def apostrophe_codepoint(text: str) -> str | None:
    for ch in text:
        if ch in APOSTROPHES:
            return ch
    return None


def main():
    df = pd.read_csv(COMPARISON_DIR / "aligned_tokens.csv", dtype=str, keep_default_na=False)
    df["apostrophe"] = df["text"].map(apostrophe_codepoint)
    elided = df[df["apostrophe"].notna()].copy()

    print(f"Corpus: {len(df):,} tokens; elided: {len(elided):,} ({100*len(elided)/len(df):.2f}%)")
    print()
    print("Codepoint census among elided tokens:")
    for cp, name in APOSTROPHES.items():
        n = (elided["apostrophe"] == cp).sum()
        if n:
            print(f"  {name}: {n}")
    print()

    # "Resolved" = lemma no longer carries an elision mark at all. Testing lemma
    # != raw surface form is NOT enough: grc_dep_web_lg's hallucinated lemmas
    # (e.g. 'ὧδʼ' -> 'ὧδʼῖς') differ from the surface form but are still garbage,
    # not a correct dictionary lemma -- and they still carry the apostrophe.
    def has_apostrophe(s: str) -> bool:
        return apostrophe_codepoint(s) is not None

    print("Unresolved-lemma rate per model (lemma still carries an elision mark):")
    for m in MODELS:
        unresolved = elided[f"{m}_lemma"].map(has_apostrophe).mean()
        print(f"  {m}: {100*unresolved:.2f}%")
    print()

    # The U+0027 contrast: does it resolve where U+02BC doesn't?
    for cp, name in APOSTROPHES.items():
        subset = elided[elided["apostrophe"] == cp]
        if len(subset) == 0:
            continue
        resolved_trf = (~subset["trf_lemma"].map(has_apostrophe)).sum()
        print(f"{name}: {len(subset)} tokens, {resolved_trf} resolve on trf")
    print()

    print("Top 12 elided forms by frequency:")
    top = elided["text"].value_counts().head(12)
    for form, n in top.items():
        print(f"  {form}: {n}")
    print(f"  (single most frequent form is {100*top.iloc[0]/len(elided):.1f}% of all elided tokens,"
          f" {100*top.iloc[0]/len(df):.2f}% of the whole corpus)")
    print()

    # Cross-model 3-way agreement, elided subset vs whole corpus
    def agree3(frame, col):
        cols = [f"{m}_{col}" for m in MODELS]
        return (frame[cols[0]] == frame[cols[1]]) & (frame[cols[1]] == frame[cols[2]])

    print("3-way agreement, elided subset vs. corpus-wide:")
    for col in ["pos", "gender", "voice", "case", "tense"]:
        whole = agree3(df, col).mean()
        el = agree3(elided, col).mean()
        print(f"  {col}: elided {100*el:.1f}%  |  corpus-wide {100*whole:.1f}%")
    print()

    # lg hallucination check: elided tokens where lg's lemma still carries the
    # elision mark (i.e. didn't resolve) AND doesn't match trf's pass-through-raw-form
    # failure mode either -- so it's not just "unresolved", it's actively different
    # garbage.
    def looks_hallucinated(row):
        lem = row["lg_lemma"]
        if not has_apostrophe(lem):
            return False  # actually resolved
        if lem == row["trf_lemma"]:
            return False  # same pass-through-raw-form failure as trf, not hallucination
        return True

    lg_bad = elided[elided.apply(looks_hallucinated, axis=1)]
    print(f"lg lemma diverges from both the raw surface form AND trf's output on "
          f"{len(lg_bad)}/{len(elided)} elided tokens ({100*len(lg_bad)/len(elided):.1f}%) "
          f"-- candidates for hallucination, not just pass-through failure.")
    sample = lg_bad[["text", "lg_lemma", "trf_lemma"]].drop_duplicates().head(8)
    for _, r in sample.iterrows():
        print(f"    {r['text']!r} -> lg={r['lg_lemma']!r}  trf={r['trf_lemma']!r}")


if __name__ == "__main__":
    main()
