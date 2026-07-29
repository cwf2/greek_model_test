"""Captures the dependency base layer modeltest.py's pipeline discards.

uva_common.nlp.line_array_to_token_table (what modeltest.py calls) reads
token.pos_/token.morph but never token.dep_/token.head/sentence boundaries --
even though grc_dep_web_lg/trf and grc_odycy_joint_trf all ship a parser +
senter component and already emit standard UD deprel labels. This script
re-extracts a bounded line range straight from the source XML (mirroring, not
importing, uva_common.text's private book/line helpers -- see
reports/treebank_agreement.md for why this stays local rather than editing
the shared uva-common package) and runs the pipeline directly so head/deprel/
sentence boundaries survive.

    python3 treebank_base.py <urn> <book_n> <first_line> <last_line> <model> [<model> ...]

    python3 treebank_base.py urn:cts:greekLit:tlg2046.tlg001.perseus-grc2 1 1 30 \\
        grc_dep_web_lg grc_dep_web_trf grc_odycy_joint_trf

Writes one CSV per model to data/treebanks_base/.
"""
import argparse
import bisect
import os
import re

import pandas as pd
import spacy
from uva_common.text import Text

DATA_DIR = "data"
OUT_DIR = os.path.join(DATA_DIR, "treebanks_base")
NSMAP = {"tei": "http://www.tei-c.org/ns/1.0"}


def _book_xml(xml, edition_urn, book_n):
    editions = xml.xpath(f'.//tei:div[@type="edition" and @n="{edition_urn}"]', namespaces=NSMAP)
    if len(editions) != 1:
        raise ValueError(f"expected exactly one edition div for {edition_urn}, found {len(editions)}")
    books = xml.xpath(
        f'.//tei:div[(@subtype="book" or @subtype="Book") and @n="{book_n}"]',
        namespaces=NSMAP,
    )
    if not books:
        raise ValueError(f"book {book_n!r} not found in {edition_urn}")
    return books[0]


def _lines_in_range(book_xml, edition_urn, book_n, first_line, last_line):
    """Extract <l> elements with first_line <= n <= last_line, in document order."""
    lines = []
    cumsum = 0
    for l in book_xml.findall(".//tei:l", namespaces=NSMAP):
        n = l.get("n")
        if n is None:
            continue
        m = re.match(r"(\d+)", n)
        if m is None or not (first_line <= int(m.group(1)) <= last_line):
            continue
        text = re.sub(r"\s+", " ", "".join(l.itertext())).strip()
        lines.append(dict(urn=f"{edition_urn}:{book_n}.{n}", n=n, text=text, cumsum=cumsum))
        cumsum += len(text) + 1  # +1 for the space joining lines before parsing
    return lines


def extract(urn, book_n, first_line, last_line, model_name):
    """Run one model over a bounded line range; return a token DataFrame with
    sentence-local head/deprel alongside the usual POS/morph/lemma fields."""
    text = Text(urn)  # public API: loads + cleans (notes/dels stripped) XML, author/title metadata
    book_xml = _book_xml(text._xml, urn, book_n)
    lines = _lines_in_range(book_xml, urn, book_n, first_line, last_line)
    if not lines:
        raise ValueError(f"no lines found in book {book_n} range {first_line}-{last_line}")

    nlp = spacy.load(model_name)
    doc = nlp(" ".join(l["text"] for l in lines))

    line_offsets = [l["cumsum"] for l in lines]

    # doc-global token.i -> (sent_id, sent_token_id), built per sentence so
    # head lookups can be resolved to a sentence-local index below.
    local_pos = {}
    sent_of = {}
    for sent_id, sent in enumerate(doc.sents, start=1):
        for sent_token_id, token in enumerate(sent, start=1):
            local_pos[token.i] = sent_token_id
            sent_of[token.i] = sent_id

    rows = []
    for token in doc:
        i = bisect.bisect_right(line_offsets, token.idx) - 1
        is_root = token.head.i == token.i
        rows.append(dict(
            model=model_name,
            sent_id=sent_of[token.i],
            sent_token_id=local_pos[token.i],
            urn=lines[i]["urn"],
            line_n=lines[i]["n"],
            text=token.text,
            lemma=token.lemma_,
            pos=token.pos_,
            head=0 if is_root else local_pos[token.head.i],
            deprel="root" if is_root else token.dep_,
            verbform=";".join(token.morph.get("VerbForm")),
            mood=";".join(token.morph.get("Mood")),
            tense=";".join(token.morph.get("Tense")),
            voice=";".join(token.morph.get("Voice")),
            person=";".join(token.morph.get("Person")),
            number=";".join(token.morph.get("Number")),
            case=";".join(token.morph.get("Case")),
            gender=";".join(token.morph.get("Gender")),
        ))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urn")
    ap.add_argument("book_n")
    ap.add_argument("first_line", type=int)
    ap.add_argument("last_line", type=int)
    ap.add_argument("models", nargs="+")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    for model_name in args.models:
        print(f"Running {model_name}...")
        df = extract(args.urn, args.book_n, args.first_line, args.last_line, model_name)
        rec = args.urn.split(":")[-1]  # e.g. tlg2046.tlg001.perseus-grc2
        outfile = os.path.join(OUT_DIR, f"{rec}.{args.book_n}.{args.first_line}-{args.last_line}.{model_name}.csv")
        df.to_csv(outfile, index=False)
        print(f"  {len(df)} tokens, {df['sent_id'].nunique()} sentences -> {outfile}")


if __name__ == "__main__":
    main()
