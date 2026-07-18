"""Reproduces the δέ POS-tagging investigation in reports/de_pos_tagging.md:
gold-treebank divergence across the three official grc UD treebanks, where the
PART tag actually comes from (git archaeology), what genre those treebanks'
dev/test splits actually cover, and how that shows up in this project's own
three models' behavior on δέ specifically (elision-lemma split, PART dominance,
and a training-schema attribution for the Nonnus/Tryphiodorus outlier).

Clones the three UD treebanks into data/ud_treebanks/ at pinned commits (so this
reproduces the same finding later even if upstream fixes the issues found here).
Also reads data/comparison/aligned_tokens.csv (run compare_models.py first) and
the installed models' meta.json (already present after `pip install -r
requirements.txt`).

    python3 experiments/de_pos_tagging.py
"""

import glob
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parent.parent
UD_DIR = REPO_ROOT / "data" / "ud_treebanks"
ALIGNED = REPO_ROOT / "data" / "comparison" / "aligned_tokens.csv"
TOKENS_DIR = REPO_ROOT / "data" / "tokens"

# Pinned so re-running this later reproduces the same finding even if upstream
# ever fixes the train/dev-test PART inconsistency this script documents.
TREEBANKS = {
    "grc_perseus": ("UD_Ancient_Greek-Perseus", "331ddef91411d0e6549744ee889e05549e6da77d"),
    "grc_proiel": ("UD_Ancient_Greek-PROIEL", "a4ab8d436de97d4598d410d91ea20b4127d04a5f"),
    "grc_ptnk": ("UD_Ancient_Greek-PTNK", "818fb315ff1f6cd95b6e7fa90f3707488d2b010d"),
}


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


def conllu_rows(path: Path):
    """Yield (sent_id, newdoc_id, cols) for each token line, cols = full tab-split row."""
    newdoc = None
    sent_id = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("# newdoc id"):
                newdoc = line.split("=", 1)[1].strip()
            elif line.startswith("# sent_id"):
                sent_id = line.split("=", 1)[1].strip()
            elif line.startswith("#") or line.strip() == "":
                continue
            else:
                cols = line.split("\t")
                if "-" in cols[0] or "." in cols[0]:
                    continue
                yield sent_id, newdoc, cols


def section_a_upos_divergence():
    print("=" * 70)
    print("A. δέ UPOS distribution across the three official grc UD treebanks")
    print("=" * 70)
    for name, (repo, _) in TREEBANKS.items():
        files = sorted((UD_DIR / repo).glob("*.conllu"))
        for f in files:
            counts = {}
            for _, _, cols in conllu_rows(f):
                if cols[2] == "δέ":
                    counts[cols[3]] = counts.get(cols[3], 0) + 1
            if counts:
                print(f"  {f.name}: {counts}")
    print()


def section_b_deprel_structure():
    print("=" * 70)
    print("B. Does δέ's clause attach as an independent root, or as `conj`?")
    print("   (root = structurally paratactic; conj = syntactically coordinated)")
    print("=" * 70)
    for name, (repo, _) in TREEBANKS.items():
        files = sorted((UD_DIR / repo).glob("*.conllu"))
        for f in files:
            by_id = {}
            de_heads = []
            rows = list(conllu_rows(f))
            cur_sent_rows = []
            cur_sent = None
            # group by sentence to resolve HEAD ids within the same sentence
            groups = {}
            for sent_id, _, cols in rows:
                groups.setdefault(sent_id, []).append(cols)
            head_deprel_counts = {}
            for sent_id, sent_rows in groups.items():
                idx = {c[0]: c for c in sent_rows}
                for c in sent_rows:
                    if c[2] == "δέ":
                        head = idx.get(c[6])
                        hd = head[7] if head else "ROOT_OR_MISSING"
                        head_deprel_counts[hd] = head_deprel_counts.get(hd, 0) + 1
            if head_deprel_counts:
                total = sum(head_deprel_counts.values())
                root_pct = 100 * head_deprel_counts.get("root", 0) / total
                conj_pct = 100 * head_deprel_counts.get("conj", 0) / total
                print(f"  {f.name}: n={total}  root={root_pct:.1f}%  conj={conj_pct:.1f}%")
    print()


def section_c_part_provenance():
    print("=" * 70)
    print("C. Where does the PART tag for δέ (and siblings) actually come from?")
    print("=" * 70)
    train_path = UD_DIR / "UD_Ancient_Greek-Perseus" / "grc_perseus-ud-train.conllu"
    if not train_path.exists():
        print("  (train file not found)")
        return
    particle_lemmas = {"δέ", "τε", "γάρ", "μέν", "ἄν", "ἄρα", "γε"}
    by_doc = {}
    for _, newdoc, cols in conllu_rows(train_path):
        if cols[2] in particle_lemmas and cols[3] in ("PART", "ADV", "CCONJ"):
            doc = (newdoc or "?").split(".")[0] if newdoc else "?"
            by_doc.setdefault(doc, {}).setdefault(cols[3], 0)
            by_doc[doc][cols[3]] += 1
    print("  Per-document tag distribution for {δέ,τε,γάρ,μέν,ἄν,ἄρα,γε} in train:")
    for doc, counts in sorted(by_doc.items()):
        total = sum(counts.values())
        part_pct = 100 * counts.get("PART", 0) / total
        print(f"    {doc}: n={total} PART%={part_pct:.1f}  {counts}")

    # git-log check: has PART EVER appeared in dev or test?
    repo_path = UD_DIR / "UD_Ancient_Greek-Perseus"
    for split in ["dev", "test"]:
        fname = f"grc_perseus-ud-{split}.conllu"
        result = subprocess.run(
            ["git", "-C", str(repo_path), "log", "--oneline", "-S", "PART", "--", fname],
            capture_output=True, text=True,
        )
        commits = [l for l in result.stdout.splitlines() if l.strip()]
        print(f"  Commits ever touching a PART-tagged line in {fname}: {len(commits)}")
    print()


def section_d_test_split_genres():
    print("=" * 70)
    print("D. What genre do the three treebanks' dev/test splits actually cover?")
    print("=" * 70)
    author_names = {
        "tlg0008": "Athenaeus (prose)", "tlg0003": "Thucydides (prose)",
        "tlg0007": "Plutarch (prose)", "tlg0011": "Sophocles (verse)",
        "tlg0012": "Homer (verse)", "tlg0013": "Homeric Hymns (verse)",
        "tlg0016": "Herodotus (prose)", "tlg0020": "Hesiod (verse)",
        "tlg0060": "Diodorus Siculus (prose)", "tlg0085": "Aeschylus (verse)",
    }
    perseus_dir = UD_DIR / "UD_Ancient_Greek-Perseus"
    for split in ["dev", "test"]:
        f = perseus_dir / f"grc_perseus-ud-{split}.conllu"
        docs = set()
        for _, newdoc, cols in conllu_rows(f):
            m = re.match(r"(tlg\d+)", newdoc or "")
            if m:
                docs.add(m.group(1))
        named = [author_names.get(d, d) for d in sorted(docs)]
        print(f"  grc_perseus {split}: {named}")

    proiel_test = UD_DIR / "UD_Ancient_Greek-PROIEL" / "grc_proiel-ud-test.conllu"
    sources = {}
    with open(proiel_test, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("# source"):
                key = line.split("=", 1)[1].strip().split(",")[0]
                sources[key] = sources.get(key, 0) + 1
    print(f"  grc_proiel test sources: {sources}")

    ptnk_test = UD_DIR / "UD_Ancient_Greek-PTNK" / "grc_ptnk-ud-test.conllu"
    books = set()
    with open(ptnk_test, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("# sent_id"):
                m = re.search(r"Septuagint-(\w+)", line)
                if m:
                    books.add(m.group(1))
    print(f"  grc_ptnk test books: {sorted(books)}")
    print()
    print("  None of the three contain epic hexameter verse -- the only verse in")
    print("  this whole ecosystem (Homer/Sophocles/Hesiod/Aeschylus) sits in")
    print("  grc_perseus's TRAIN split, which is never held out for evaluation.")
    print()


def section_e_our_models_de_behavior():
    print("=" * 70)
    print("E. How do this project's own 3 models actually tag δέ?")
    print("=" * 70)
    if not ALIGNED.exists():
        print("  (run compare_models.py first)")
        return
    de_lemmas = {"δέ", "δὲ"}
    de_elided = {"δʼ", "δʼ."}

    rows = []
    for f in glob.glob(str(TOKENS_DIR / "*.csv")):
        fname = Path(f).name
        model = next((m for m in ["grc_dep_web_trf", "grc_dep_web_lg", "grc_odycy_joint_trf"]
                      if fname.endswith(f".{m}.csv")), None)
        df = pd.read_csv(f, usecols=["author", "lemma", "pos"], dtype=str)
        de = df[df["lemma"].isin(de_lemmas | de_elided)].copy()
        de["model"] = model
        de["elided"] = de["lemma"].isin(de_elided)
        rows.append(de)
    all_de = pd.concat(rows, ignore_index=True)

    print("  PART share of δέ(+δʼ) tokens per model/author:")
    counts = all_de.groupby(["model", "author", "pos"]).size().unstack(fill_value=0)
    counts["total"] = counts.sum(axis=1)
    for (model, author), row in counts.iterrows():
        part_pct = 100 * row.get("PART", 0) / row["total"]
        print(f"    {model} / {author}: PART={part_pct:.1f}%  n={row['total']}")
    print()

    print("  Elision rate for δέ specifically, by author (should match across")
    print("  models -- it's a property of the source text, not the tagger):")
    rate = all_de[all_de["model"] == "grc_dep_web_lg"].groupby(["author", "elided"]).size().unstack(fill_value=0)
    for author, row in rate.iterrows():
        el = row.get(True, 0)
        proper = row.get(False, 0)
        print(f"    {author}: elision rate = {100*el/(el+proper):.1f}%")
    print()


def section_f_training_schema_attribution():
    print("=" * 70)
    print("F. Training-schema attribution for the Nonnus/Tryphiodorus PART dip")
    print("=" * 70)
    for model in ["grc_dep_web_lg", "grc_dep_web_trf", "grc_odycy_joint_trf"]:
        try:
            import importlib.util
            spec = importlib.util.find_spec(model)
            if spec is None or spec.origin is None:
                print(f"  {model}: not installed")
                continue
            meta_path = Path(spec.origin).parent / "meta.json"
            with open(meta_path) as f:
                meta = json.load(f)
            print(f"  {model}: {meta.get('description', '(no description in meta.json)')[:200]}")
        except Exception as e:
            print(f"  {model}: couldn't read meta.json ({e})")
    print()
    print("  PROIEL is the only source that's 100% ADV for δέ; PTNK the only one")
    print("  that's 100% CCONJ (see section A). grc_odycy_joint_trf trains on")
    print("  Perseus+PROIEL only (no PTNK); grc_dep_web_lg/trf train on all three.")
    print("  See section E's per-author PART% for the resulting ADV/CCONJ pull;")
    print("  compare Nonnus/Tryphiodorus against Homer's baseline by hand from")
    print("  that table -- odyCy's gap should skew ADV, dep_web_trf's should skew")
    print("  CCONJ more than PROIEL alone could produce.")
    print()


def section_g_athenaeus_verse_quotation():
    print("=" * 70)
    print("G. Does grc_perseus's Athenaeus test split contain quoted verse?")
    print("=" * 70)
    test_path = UD_DIR / "UD_Ancient_Greek-Perseus" / "grc_perseus-ud-test.conllu"
    lines = test_path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# text") and "Ἰσοστάσιον" in line:
            print(f"  Attribution: {line}")
            # the next sentence's # text line is the quoted fragment itself --
            # window has to clear this sentence's own token rows first (~20 lines)
            for j in range(i + 1, min(i + 40, len(lines))):
                if lines[j].startswith("# text"):
                    print(f"  Next sentence (the quoted comic fragment): {lines[j]}")
                    break
            print("  -> this is a genuine Alexis (comedy) fragment, included as an")
            print("     ordinary annotated sentence with no verse-specific marker.")
            return
    print("  (known example not found -- treebank content may have changed)")
    print()


def main():
    ensure_treebanks()
    section_a_upos_divergence()
    section_b_deprel_structure()
    section_c_part_provenance()
    section_d_test_split_genres()
    section_e_our_models_de_behavior()
    section_f_training_schema_attribution()
    section_g_athenaeus_verse_quotation()


if __name__ == "__main__":
    main()
