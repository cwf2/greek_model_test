"""Renders a CoNLL-U treebank as dependency-arc diagrams for manual review.

Read-only: this only visualizes data/treebanks/*.conllu, it doesn't edit it
(unlike spotcheck_review.py, which saves human judgments back to its CSV --
correcting dependency trees needs its own editor, deliberately out of scope
here). Reuses spaCy's own conllu_to_docs converter (see the "can spacy read
the conllu file" check this session) and displacy for the arcs, so there's no
new rendering code to get wrong.

    python3 treebank_visualize.py [path/to/file.conllu]

Writes an HTML file next to the input (in data/treebank_review/, gitignored
like the rest of data/) and opens it in a browser.
"""
import argparse
import os
import webbrowser
from pathlib import Path

from spacy import displacy
from spacy.training.converters import conllu_to_docs

DEFAULT_CONLLU = "data/treebanks/tlg2046.tlg001.perseus-grc2.1.1-30.silver.conllu"
OUT_DIR = os.path.join("data", "treebank_review")

AGREEMENT_COLOR = {"unanimous": "#2e7d32", "majority": "#f9a825", "split": "#c62828"}


def parse_comments(conllu_text):
    """Pull sent_id/agreement/note comments per sentence, in file order --
    conllu_to_docs discards non-standard comments, so read them separately
    and zip by position (safe since n_sents=1 gives one Doc per sentence)."""
    sentences = []
    cur = {"sent_id": None, "agreement": None, "notes": []}
    for line in conllu_text.splitlines():
        if line.startswith("# sent_id"):
            cur["sent_id"] = line.split("=", 1)[1].strip()
        elif line.startswith("# claude_agreement"):
            cur["agreement"] = line.split("=", 1)[1].strip()
        elif line.startswith("# claude_note"):
            cur["notes"].append(line.split("=", 1)[1].strip())
        elif line.strip() == "":
            if cur["sent_id"] is not None:
                sentences.append(cur)
            cur = {"sent_id": None, "agreement": None, "notes": []}
    if cur["sent_id"] is not None:
        sentences.append(cur)
    return sentences


def build_html(conllu_path):
    text = Path(conllu_path).read_text(encoding="utf-8")
    docs = list(conllu_to_docs(text, n_sents=1, no_print=True))
    comments = parse_comments(text)
    if len(docs) != len(comments):
        raise SystemExit(f"parsed {len(docs)} docs but {len(comments)} sentence comment blocks -- "
                          "file may not be one complete sentence per blank-line block")

    blocks = []
    for doc, c in zip(docs, comments):
        badge_html = ""
        if c["agreement"]:
            color = AGREEMENT_COLOR.get(c["agreement"], "#666")
            badge_html = f'<span class="badge" style="background:{color}">{c["agreement"]}</span>'
        notes_html = "".join(f'<div class="note">{n}</div>' for n in c["notes"])
        svg = displacy.render(doc, style="dep", page=False, options={"compact": True})
        blocks.append(f'''
<section>
  <h3>{c["sent_id"]} {badge_html}</h3>
  {notes_html}
  <div class="tree">{svg}</div>
</section>''')

    return f'''<!doctype html>
<html><head><meta charset="utf-8"><title>Treebank review: {Path(conllu_path).name}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 2em; }}
  h3 {{ display: flex; align-items: center; gap: 0.75em; }}
  .badge {{ color: white; padding: 0.15em 0.6em; border-radius: 1em; font-size: 0.7em; }}
  .note {{ background: #fff3cd; border-left: 4px solid #f9a825; padding: 0.5em 1em; margin: 0.5em 0; font-size: 0.9em; }}
  .tree {{ overflow-x: auto; }}
  section {{ border-bottom: 1px solid #ddd; padding-bottom: 1em; margin-bottom: 1em; }}
</style></head>
<body>
<h1>{Path(conllu_path).name}</h1>
{"".join(blocks)}
</body></html>'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("conllu", nargs="?", default=DEFAULT_CONLLU)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    html = build_html(args.conllu)
    out_path = os.path.join(OUT_DIR, Path(args.conllu).stem + ".html")
    Path(out_path).write_text(html, encoding="utf-8")
    print(f"wrote {out_path}")
    if not args.no_browser:
        webbrowser.open(f"file://{os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
