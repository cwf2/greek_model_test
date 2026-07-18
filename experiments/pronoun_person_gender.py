"""Reproduces the pronoun person/gender findings in reports/pronoun_person_gender.md:
1st/2nd-person pronouns are reliably findable by lemma (modulo elision), but the
`person` and `gender` morphological features on them are not trustworthy search
targets, and tracing why leads into the three treebanks' own gold conventions and,
for Perseus specifically, into the original (pre-UD-conversion) AGDT source XML.

Clones the three UD treebanks (data/ud_treebanks/, shared with de_pos_tagging.py)
and the original AGDT treebank source (data/agdt_source/) at pinned commits. Also
reads data/comparison/aligned_tokens.csv (run compare_models.py first).

    python3 experiments/pronoun_person_gender.py
"""

import re
import subprocess
from collections import defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parent.parent
UD_DIR = REPO_ROOT / "data" / "ud_treebanks"
ALIGNED = REPO_ROOT / "data" / "comparison" / "aligned_tokens.csv"
AGDT_DIR = REPO_ROOT / "data" / "agdt_source" / "treebank_data"

MODELS = ["lg", "trf", "odycy"]
PERSON1 = ["ἐγώ", "ἡμεῖς"]
PERSON2 = ["σύ", "ὑμεῖς"]
APOSTROPHES = {"ʼ", "'", "’"}

# Same pins as de_pos_tagging.py (shared clones).
TREEBANKS = {
    "grc_perseus": ("UD_Ancient_Greek-Perseus", "331ddef91411d0e6549744ee889e05549e6da77d"),
    "grc_proiel": ("UD_Ancient_Greek-PROIEL", "a4ab8d436de97d4598d410d91ea20b4127d04a5f"),
    "grc_ptnk": ("UD_Ancient_Greek-PTNK", "818fb315ff1f6cd95b6e7fa90f3707488d2b010d"),
}
PERSEUS_TRAIN = UD_DIR / "UD_Ancient_Greek-Perseus" / "grc_perseus-ud-train.conllu"

# Pinned so re-running later reproduces the same document/annotator counts even if
# upstream adds more annotation. Sparse + blob-filtered: this repo also contains
# Latin and non-v2.1 material we don't need.
AGDT_COMMIT = "bf4334f0af5e13d16b04c1cccd6237e683ac6f5f"
AGDT_SPARSE_PATH = "v2.1/Greek"


def ensure_treebanks():
    UD_DIR.mkdir(parents=True, exist_ok=True)
    for name, (repo, commit) in TREEBANKS.items():
        path = UD_DIR / repo
        if not path.exists():
            subprocess.run(
                ["git", "clone", "--quiet", f"https://github.com/UniversalDependencies/{repo}.git", str(path)],
                check=True,
            )
        subprocess.run(["git", "-C", str(path), "checkout", "--quiet", commit], check=True)


def ensure_agdt_source():
    AGDT_DIR.parent.mkdir(parents=True, exist_ok=True)
    if not AGDT_DIR.exists():
        subprocess.run(
            ["git", "clone", "--quiet", "--filter=blob:none", "--sparse",
             "https://github.com/PerseusDL/treebank_data.git", str(AGDT_DIR)],
            check=True,
        )
        subprocess.run(["git", "-C", str(AGDT_DIR), "sparse-checkout", "set", AGDT_SPARSE_PATH], check=True)
    subprocess.run(["git", "-C", str(AGDT_DIR), "checkout", "--quiet", AGDT_COMMIT], check=True)


def has_apostrophe(s):
    return any(ch in APOSTROPHES for ch in str(s))


def conllu_sentences(path: Path):
    """Yield (sent_id, doc_id, [cols, ...]) per sentence."""
    for block in path.read_text(encoding="utf-8").split("\n\n"):
        lines = block.splitlines()
        sent_id = None
        for l in lines:
            if l.startswith("# sent_id"):
                sent_id = l.split("=", 1)[1].strip()
        if sent_id is None:
            continue
        doc_id = sent_id.split(".tb.xml")[0] if ".tb.xml" in sent_id else sent_id.rsplit("@", 1)[0]
        rows = []
        for l in lines:
            if l.startswith("#") or not l.strip():
                continue
            cols = l.split("\t")
            if len(cols) != 10 or "-" in cols[0] or "." in cols[0]:
                continue
            rows.append(cols)
        yield sent_id, doc_id, rows


def section_a_identification_agreement():
    print("=" * 70)
    print("A. Cross-model agreement on 1st/2nd-person pronoun IDENTIFICATION")
    print("   (contrast: POS agreement vs. `person` feature agreement)")
    print("=" * 70)
    df = pd.read_csv(ALIGNED, dtype=str, keep_default_na=False)
    df["elided"] = df["text"].map(has_apostrophe)
    for m in MODELS:
        person = pd.to_numeric(df[f"{m}_person"], errors="coerce")
        df[f"{m}_is12"] = (df[f"{m}_pos"] == "PRON") & person.isin([1.0, 2.0])

    unelided = df[~df["elided"]]
    flags = unelided[[f"{m}_is12" for m in MODELS]]
    union = unelided[flags.any(axis=1)]
    print(f"Unelided tokens where ANY model flags PRON+person(1|2): {len(union)}")
    print("Of those, each model's actual POS value:")
    for m in MODELS:
        print(f"  {m}: {union[f'{m}_pos'].value_counts().to_dict()}")
    print("-> POS=PRON agreement is near-total (~98-100%) on this set. The near-zero")
    print("   3-way overlap on the is12 flag itself is about `person`, not POS.")
    print()


def section_b_person_blank_by_class():
    print("=" * 70)
    print("B. `person` blank rate is near-universal for ALL persons, not just 1st/2nd")
    print("=" * 70)
    df = pd.read_csv(ALIGNED, dtype=str, keep_default_na=False)
    groups = {
        "1st (ἐγώ)": ["ἐγώ"],
        "2nd (σύ)": ["σύ"],
        "3rd (ὁ)": ["ὁ"],
        "3rd (ὅς)": ["ὅς"],
        "3rd (ἕ/μιν/σφεῖς)": ["ἕ", "μιν", "σφεῖς"],
        "3rd (αὐτός)": ["αὐτός"],
    }
    for m in MODELS:
        pron = df[df[f"{m}_pos"] == "PRON"]
        for label, lemmas in groups.items():
            sub = pron[pron[f"{m}_lemma"].isin(lemmas)]
            if len(sub) == 0:
                continue
            blank = (sub[f"{m}_person"] == "").mean()
            print(f"  {m:6s} {label:20s} n={len(sub):5d}  person blank: {100*blank:5.1f}%")
    print()


def section_c_person_training_provenance():
    print("=" * 70)
    print("C. `Person` marking rate in the three treebanks' TRAIN splits")
    print("=" * 70)
    for name, (repo, _) in TREEBANKS.items():
        files = sorted((UD_DIR / repo).glob("*-train.conllu"))
        for f in files:
            for label, lemmas in [("1st (ἐγώ/ἡμεῖς)", PERSON1), ("2nd (σύ/ὑμεῖς)", PERSON2)]:
                total = has_person = 0
                for _, _, rows in conllu_sentences(f):
                    for cols in rows:
                        if cols[3] == "PRON" and cols[2] in lemmas:
                            total += 1
                            if "Person=" in cols[5]:
                                has_person += 1
                if total:
                    print(f"  {repo:28s} {label:18s} n={total:5d}  Person marked: {100*has_person/total:5.1f}%")
    print()


def section_d_gender_training_provenance():
    print("=" * 70)
    print("D. `Gender` marking rate on pronouns vs. nouns, by treebank")
    print("=" * 70)
    for name, (repo, _) in TREEBANKS.items():
        files = sorted((UD_DIR / repo).glob("*-train.conllu"))
        for f in files:
            noun_total = noun_gender = 0
            pron_stats = defaultdict(lambda: defaultdict(int))
            for _, _, rows in conllu_sentences(f):
                for cols in rows:
                    upos, lemma, feats = cols[3], cols[2], cols[5]
                    if upos == "NOUN":
                        noun_total += 1
                        if "Gender=" in feats:
                            noun_gender += 1
                    if upos == "PRON" and lemma in PERSON1 + PERSON2:
                        label = "1st" if lemma in PERSON1 else "2nd"
                        m = re.search(r"Gender=([^|]+)", feats)
                        pron_stats[label][m.group(1) if m else "(blank)"] += 1
            if noun_total:
                print(f"  {repo}: NOUN Gender marked {100*noun_gender/noun_total:.1f}% (n={noun_total}) -- sanity check")
            for label in ("1st", "2nd"):
                vals = pron_stats.get(label)
                if vals:
                    total = sum(vals.values())
                    print(f"    pronoun {label}: n={total}  " +
                          ", ".join(f"{v}={n} ({100*n/total:.1f}%)" for v, n in sorted(vals.items(), key=lambda x: -x[1])))
    print()


def section_e_formulaic_artifact():
    print("=" * 70)
    print("E. Formulaic minimal pair: identical Homeric formula, opposite true speaker")
    print("=" * 70)
    df = pd.read_csv(ALIGNED, dtype=str, keep_default_na=False)
    pairs = [
        ("Odyssey", "10_0406", "ἐμοί", "Circe (female)"),
        ("Odyssey", "04_0481", "ἐμοί", "Menelaus (male)"),
    ]
    for work, line_id, text, who in pairs:
        row = df[(df["work"] == work) & (df["line_id"] == line_id) & (df["text"] == text)]
        if len(row):
            r = row.iloc[0]
            print(f"  {work} {line_id} ({who}): text={r['text']!r} speaker={r['speaker']!r} lg_gender={r['lg_gender']!r}")
    print("  -> same formula (\"ὣς ἔφατ', αὐτὰρ ἐμοί γ(ε) ...\"), same lg_gender=Fem tag,")
    print("     regardless of the real speaker's sex, and no feminine word nearby in")
    print("     either line -- not evidence of referential inference.")
    print()


def section_f_annotator_clustering():
    print("=" * 70)
    print("F. Perseus 2nd-person Gender blank rate, by document and by annotator count")
    print("=" * 70)
    doc_gender = defaultdict(lambda: {"blank": 0, "filled": 0})
    for _, doc_id, rows in conllu_sentences(PERSEUS_TRAIN):
        for cols in rows:
            if cols[3] == "PRON" and cols[2] in PERSON2:
                if "Gender=" in cols[5]:
                    doc_gender[doc_id]["filled"] += 1
                else:
                    doc_gender[doc_id]["blank"] += 1

    xml_dir = AGDT_DIR / AGDT_SPARSE_PATH / "texts"
    doc_annotators = {}
    for xml_path in xml_dir.glob("*.tb.xml"):
        doc_id = xml_path.name.removesuffix(".tb.xml")
        text = xml_path.read_text(encoding="utf-8")
        doc_annotators[doc_id] = text.count("<resp>annotator of the text</resp>")

    print(f"  {'document':45s} {'total':>6s} {'blank%':>7s} {'annotators':>10s}")
    rows_out = []
    for doc, c in doc_gender.items():
        total = c["blank"] + c["filled"]
        if total < 5:
            continue
        n_annot = doc_annotators.get(doc, doc_annotators.get(doc + ".1"))
        rows_out.append((doc, total, 100 * c["blank"] / total, n_annot))
    for doc, total, pct, n_annot in sorted(rows_out, key=lambda x: -x[1]):
        print(f"  {doc:45s} {total:6d} {pct:6.1f}% {str(n_annot):>10s}")
    print("  -> single-annotator documents sit at extremes (near-0% or near-100%);")
    print("     multi-annotator documents (Iliad: 22, Herodotus: 2) sit in the middle.")
    print("     No per-sentence annotator attribution exists in the source XML (only")
    print("     a `subdoc` line-range with no key to a person) -- can't go further.")
    print()


def section_g_practical_recommendation():
    print("=" * 70)
    print("G. Practical comparison: lemma-list search vs. person+PRON search")
    print("=" * 70)
    df = pd.read_csv(ALIGNED, dtype=str, keep_default_na=False)
    for m in MODELS:
        person = pd.to_numeric(df[f"{m}_person"], errors="coerce")
        morph_search = ((df[f"{m}_pos"] == "PRON") & person.isin([1.0, 2.0])).sum()
        lemma_search = ((df[f"{m}_pos"] == "PRON") & df[f"{m}_lemma"].isin(PERSON1 + PERSON2)).sum()
        print(f"  {m:6s} person+PRON search: {morph_search:5d}   lemma-list+PRON search: {lemma_search:5d}")
    print()


if __name__ == "__main__":
    ensure_treebanks()
    ensure_agdt_source()
    section_a_identification_agreement()
    section_b_person_blank_by_class()
    section_c_person_training_provenance()
    section_d_gender_training_provenance()
    section_e_formulaic_artifact()
    section_f_annotator_clustering()
    section_g_practical_recommendation()
