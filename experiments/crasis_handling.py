"""Reproduces the crasis-handling findings in reports/crasis_handling.md:
does any model ever split a genuine crasis token at the internal breathing mark
(coronis), or fail to keep elided/punctuated forms separate?

Detection signature for genuine crasis: a token starting with a consonant that
also contains a character whose *fully recursive* NFD decomposition includes
psili (U+0313) or dasia (U+0314) -- i.e. an internal breathing mark, which is
what a crasis coronis is. (A single-level unicodedata.decomposition() call is
NOT enough -- e.g. 'ἆ' decomposes to alpha+circumflex first, and only the
*alpha*'s own decomposition contains the psili. Must use NFD.)

This also catches a known source-text encoding issue (accent mis-encoded as
breathing -- see PREPROCESSING.md) and an unrelated trf/odyCy tokenizer bug
(under/over-splitting) as false positives/side effects; the report separates
these three categories by hand since there's no automatic way to tell them
apart from the signature alone.

Prerequisite: `python3 modeltest.py <model>` for each of grc_dep_web_lg,
grc_dep_web_trf, grc_odycy_joint_trf (populates data/tokens/).

    python3 experiments/crasis_handling.py
"""

import glob
import unicodedata
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parent.parent
TOKENS_DIR = REPO_ROOT / "data" / "tokens"
CONSONANTS = set("βγδζθκλμνξπρστφχψ")

# Already root-caused in PREPROCESSING.md as an accent-mis-encoded-as-breathing
# source-text issue (Dionysiaca/Posthomerica), not crasis and not a tokenizer bug.
KNOWN_SOURCE_TEXT_CORRUPTION = {
    "καἰ", "δἐ", "βέλἐ", "σἐο", "μένἐ", "θυμήρἐ", "δένδρἐ", "τὀν", "δαλὀν",
    "χθονἰ", "κρυφἱῳ", "πἁλιν", "σὐτίκα", "σὐν", "δάκρὐ", "Ζεὐς", "κὐδιόωσαν",
    "φἐρτατος", "Λἰσονίδης", "Λἰσήποιο", "Λἰνήιος", "Λἰακίδαο", "Λὐτίκα",
    "νἱὸς", "νἱέος",
}


def has_internal_breathing(text: str) -> bool:
    if len(text) < 2 or not text[0].isalpha() or text[0].lower() not in CONSONANTS:
        return False
    for ch in text[1:]:
        if any(0x0313 <= ord(c) <= 0x0314 for c in unicodedata.normalize("NFD", ch)):
            return True
    return False


def load_model_tokens(model: str) -> set[str]:
    forms = set()
    for f in glob.glob(str(TOKENS_DIR / f"*.{model}.csv")):
        df = pd.read_csv(f, dtype=str, keep_default_na=False, usecols=["text"])
        forms |= set(df["text"].unique())
    return forms


def main():
    models = ["grc_dep_web_lg", "grc_dep_web_trf", "grc_odycy_joint_trf"]
    per_model = {m: load_model_tokens(m) for m in models}

    # lg/trf share a tokenizer -- use lg as the reference for "what whole tokens exist".
    lg_candidates = sorted(t for t in per_model["grc_dep_web_lg"] if has_internal_breathing(t))
    print(f"{len(lg_candidates)} candidate tokens in grc_dep_web_lg's own token list "
          f"match the internal-breathing-after-consonant signature:")
    for t in lg_candidates:
        print(f"  {t}")
    print()

    known_corrupt = [t for t in lg_candidates if t in KNOWN_SOURCE_TEXT_CORRUPTION]
    genuine_or_new = [t for t in lg_candidates if t not in KNOWN_SOURCE_TEXT_CORRUPTION]
    print(f"{len(known_corrupt)} match the already-documented source-text encoding "
          f"corruption list (PREPROCESSING.md) -- excluded from crasis analysis below.")
    print()

    print(f"Remaining {len(genuine_or_new)} candidates: checking whether each survives "
          f"as a single token in grc_dep_web_trf and grc_odycy_joint_trf too.")
    trf_missing = [t for t in genuine_or_new if t not in per_model["grc_dep_web_trf"]]
    odycy_missing = [t for t in genuine_or_new if t not in per_model["grc_odycy_joint_trf"]]

    print(f"\nMissing whole from grc_dep_web_trf's token list: {len(trf_missing)}")
    for t in trf_missing:
        print(f"  {t}")

    print(f"\nMissing whole from grc_odycy_joint_trf's token list "
          f"(candidate crasis-splitting cases): {len(odycy_missing)}")
    for t in odycy_missing:
        print(f"  {t}")

    # Known blind spot: the consonant-initial requirement above misses crasis forms
    # that happen to start with a vowel, e.g. οὑμὸς (< ὁ + ἐμός) -- 'ὁ' is itself
    # vowel-initial, so the breathing on the second letter looks like ordinary
    # word-initial diphthong breathing (as in οὐρανός) rather than an internal
    # marker. No general fix without a lexicon; spot-checking known cases instead.
    print("\nManual check (vowel-initial crasis, outside the automated signature):")
    for form in ["οὑμὸς", "οὑμὸν"]:
        in_lg = form in per_model["grc_dep_web_lg"]
        in_odycy = form in per_model["grc_odycy_joint_trf"]
        print(f"  {form}: whole in lg={in_lg}, whole in odyCy={in_odycy}")

    print("\nCross-check: are the 5 known 'under-split' glued tokens present in ALL "
          "three models' own tokenizers, or trf-specific?")
    glued = ["γαμοστόλον·οὐρανόθεν", "δ̓ἀλεγεινός", "δ̓ἐν", "κρᾶτ̓ἀπέκοψε", "ποίησʼ—ὡς"]
    for g in glued:
        present = [m for m in models if g in per_model[m]]
        print(f"  {g!r}: present whole in {present}")


if __name__ == "__main__":
    main()
