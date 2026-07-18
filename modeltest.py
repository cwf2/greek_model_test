import os
import argparse
import uva_common
import spacy
import pandas as pd
from dicesapi import DicesAPI

# Perseus marks elision with U+02BC (MODIFIER LETTER APOSTROPHE). Do NOT
# normalize this to ASCII "'" before tokenization — tested in an earlier
# round (see reports/latincy_handoff.md §5) and rejected: the tokenizer's
# ASCII-apostrophe exception list is incomplete, so normalizing introduces
# spurious token splits (+246 stray tokens on Iliad book 1 alone). The
# elision-lemma gap this was trying to work around is a real bug, but the
# fix belongs in lemma lookup, not text preprocessing.

# global values
DATA_DIR = "data"
TEXTS = [
    ("Iliad", "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2"),
    ("Odyssey", "urn:cts:greekLit:tlg0012.tlg002.perseus-grc2"),
    ("Argonautica", "urn:cts:greekLit:tlg0001.tlg001.perseus-grc2"),
    ("Posthomerica", "urn:cts:greekLit:tlg2046.tlg001.perseus-grc2"),
    ("Sack of Troy", "urn:cts:greekLit:tlg0647.tlg001.perseus-grc2"),
    ("Dionysiaca", "urn:cts:greekLit:tlg2045.tlg001.perseus-grc2"),
]

# get command-line options
parser = argparse.ArgumentParser(
    prog = "modeltest.py",
    description = "uses a spacy model to tokenize and tag a corpus of texts",
)
parser.add_argument("model", help="model to use")
args = parser.parse_args()

# download texts from Perseus
print("Checking local text repository")
uva_common.clone_repo("greek")

# prepare output directory
tokens_dir = os.path.join(DATA_DIR, "tokens")
os.makedirs(tokens_dir, exist_ok=True)

# read XML from local directory
print("Loading XML...")

corpus = []
for name, urn in TEXTS:
    text = uva_common.Text(urn)
    text.name = name
    corpus.append(text)
print(f"Corpus contains {len(corpus)} texts")

# load model
print(f"Loading model {args.model}")
nlp = spacy.load(args.model)

# parse all texts
print("Running NLP...")
for i, text in enumerate(corpus):
    print(f"[{i+1}/{len(corpus)}]", text.title, end="...")
    text.tokens = text.parse(nlp_pipeline=nlp)
    print(len(text.tokens), "tokens")

# get speech data from DICES
api = DicesAPI()
all_speeches = api.getSpeeches()

# manual speech corrections
for s in all_speeches:
    # missing line number in Apollonius
    if s.work.urn=="urn:cts:greekLit:tlg0001.tlg001.perseus-grc2" and s.l_la=="3.739":
        s.l_la = "3.738"

    # missing line number in Odyssey
    if s.work.urn=="urn:cts:greekLit:tlg0012.tlg002.perseus-grc2" and s.l_fi=="10.456":
        s.l_fi = "10.45"

# create token table
for text in corpus:
    print(text.author, text.title, "...", end=" ")

    # ordered sequence of line URNs taken directly from the token table
    line_table = pd.DataFrame({
        "urn": text.tokens["urn"].drop_duplicates()
    }).reset_index(drop=True)
    line_table = line_table.assign(
        speech_id=None, speaker=None, addressee=None,
        level=0, type=None, cluster=None, turn=None, tags=None,
    )

    # annotate lines that fall inside speeches
    for speech in all_speeches:
        if speech.work.urn != text.urn:
            continue

        first_urn = f"{text.urn}:{speech.l_fi}"
        last_urn = f"{text.urn}:{speech.l_la}"

        matches_first = line_table.index[line_table["urn"] == first_urn]
        matches_last  = line_table.index[line_table["urn"] == last_urn]

        if len(matches_first) == 0 or len(matches_last) == 0:
            print(f"\n  warning: could not locate speech {speech._attributes['public_id']} "
                  f"({speech.l_fi}–{speech.l_la})")
            continue

        i_first = matches_first[0]
        i_last  = matches_last[0]

        line_table.loc[i_first:i_last, "speech_id"]  = speech._attributes["public_id"]
        line_table.loc[i_first:i_last, "speaker"]    = speech.getSpkrString()
        line_table.loc[i_first:i_last, "addressee"]  = speech.getAddrString()
        line_table.loc[i_first:i_last, "level"]      = speech.level + 1
        line_table.loc[i_first:i_last, "type"]       = speech.type
        line_table.loc[i_first:i_last, "cluster"]    = speech.cluster.id
        line_table.loc[i_first:i_last, "turn"]       = speech.part
        line_table.loc[i_first:i_last, "tags"]       = ";".join(
            tag["type"] for tag in speech._attributes["tags"]
        )

    # distinguish Odysseus' apologue from his other speeches
    apologue_ids = ["3F63", "A2AB"]
    line_table.loc[line_table["speech_id"].isin(apologue_ids), "speaker"] = "Odysseus-Apologue"

    # merge speech annotation into token table
    text.tokens = pd.merge(text.tokens, line_table, on="urn")

    # attach the English work name as its own column
    text.tokens.insert(2, "work", text.name)

    # export — filename built from CTS components (colon-free, OS-independent),
    # not the URN string itself
    outfile = os.path.join(tokens_dir, f"{text.workgroup}.{text.work}.{text.edition}.{args.model}.csv")
    text.tokens.to_csv(outfile, index=False)
    print(f"{len(text.tokens)} tokens → {outfile}")
        
