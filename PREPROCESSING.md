# Perseus source-text notes

Data-quality issues found in the Perseus `canonical-greekLit` source texts
themselves — as opposed to model/tokenizer behavior, which belongs in
[reports/](reports/INDEX.md) and [MODELS.md](MODELS.md). Nothing here
should be fixed by changing model choice; it needs to be handled (or at least
accounted for) in preprocessing before texts reach any model.

## Accent/breathing mis-encoding (Dionysiaca, Posthomerica)

Found 2026-07-16 while auditing crasis handling in `grc_dep_web_trf` (see
[reports/crasis_handling.md](reports/crasis_handling.md)). A search for tokens
with an internal breathing mark (the real crasis signature) turned up ~110
false positives concentrated in Dionysiaca and Posthomerica, where an accent
character appears to have been mis-encoded as a breathing mark:

- `καἰ` for `καί` (72 occurrences, almost all in Dionysiaca)
- `τεύχἐ`, `δἐ`, `βέλἐ`, `σἐο`, `μένἐ`, `θυμήρἐ`, `δένδρἐ` (accent → breathing
  substitution, mostly Posthomerica)
- `τὀν`, `δαλὀν`, `χθονἰ`, `κρυφἱῳ`, `πἁλιν`, `σὐτίκα`, `σὐν`, `δάκρὐ`,
  `Ζεὐς`, `κὐδιόωσαν`, `φἐρτατος` — same pattern, scattered
- Separately, apparent letter substitution `Α`→`Λ` at word start produces
  the same false-positive signature once the true initial vowel's breathing
  mark ends up on the second letter: `Λἰσονίδης` for `Αἰσονίδης`,
  `Λἰσήποιο`, `Λἰνήιος`, `Λἰακίδαο`, `Λὐτίκα` (all Argonautica) —
  `νἱὸς`/`νἱέος` for `υἱός`/`υἱέος` (Ν/Υ confusion) is likely the same class
  of error.

Not yet root-caused (unclear whether it's upstream in Perseus's XML or
introduced somewhere in this repo's text extraction). Every one of these was
confirmed to be a spurious token, not genuine crasis — none of them
correspond to real crasis forms in the underlying poem. Detection method: a
token starting with a consonant that also contains a Unicode character whose
fully recursive NFD decomposition includes psili (U+0313) or dasia (U+0314)
— now checked in as
[experiments/crasis_handling.py](experiments/crasis_handling.py) (that script
also excludes this list by name so it doesn't contaminate the crasis findings
in [reports/crasis_handling.md](reports/crasis_handling.md)).

**Not yet handled**: no normalization/correction pass exists for this. If it
matters for a given analysis, filter or hand-correct affected tokens rather
than trusting POS/lemma output on them, since the corrupted spelling itself
also degrades model output on top of the encoding issue.

## Candidate: missing word-boundary in 5 locations (unconfirmed)

Found 2026-07-18 as a side effect of [reports/crasis_handling.md](reports/crasis_handling.md)
— 5 tokens where two words appear glued together with no space or punctuation
between them at all: `κρᾶτ̓ἀπέκοψε` (Posthomerica 1.261), `δ̓ἐν` (8.492),
`δ̓ἀλεγεινός` (14.193), `ποίησʼ—ὡς` (Odyssey 14.274), `γαμοστόλον·οὐρανόθεν`
(Dionysiaca 43.374). All 5 are glued identically in all three models, including
odyCy's independent tokenizer — three unrelated tokenizers failing at the exact
same character position is strong evidence this is a missing boundary in the
source XML rather than any model's tokenizer bug, but **not yet confirmed
against the raw XML**.

## Other single-character transcription errors (spot-checked, not systematically searched)

Found by hand during spot-check review, not via the corpus-wide scan above —
likely more of these exist but haven't been searched for systematically.

- **`ὅπων` for `ὅπως`** (Dionysiaca 31.272, ν/ς confusion). User confirmed
  against the Loeb text. `ὅπως` here governs a purpose clause with `θέλξω`;
  worth noting that `grc_dep_web_trf` independently tagged `θέλξω` as aorist
  subjunctive 1st sg — the mood/person a correct `ὅπως`-purpose-clause
  reading requires — even though it never saw the corrected spelling. See
  [reports/spotcheck_adjudication.md](reports/spotcheck_adjudication.md) and
  spot-check row 22 for detail.

If a systematic sweep for this error class is ever done, ν/ς and Α/Λ and
Ν/Υ confusion (per the section above) all look like the same underlying
phenomenon — single visually/phonetically adjacent character substitutions —
and a spell-check-style pass against a Greek epic lexicon might catch more of
these than the breathing-mark heuristic used above, which only catches the
subset that happens to produce an internal breathing-marked vowel.

- **`ὄβριμου` for `ὄβριμον`** (Posthomerica 1.8, ν/υ confusion). Found while
  hand-treebanking this passage (see
  [reports/treebank_agreement.md](reports/treebank_agreement.md)): the word
  is grammatically required to agree with the accusative `ἄνδρα` it
  modifies, but `-ου` is unambiguously a genitive ending — same error class
  as the ν/υ confusion already noted above (`νἱὸς`/`υἱός`), not yet
  confirmed against a critical edition.

- **`ἐλάθοιο` for `ἐλάφοιο`** (Posthomerica 1.25, θ/φ confusion — a letter
  pair not yet seen in the other cases here). `ἐλάθοιο` doesn't lemmatize to
  any attested word and stalled the treebank adjudication (see
  [reports/treebank_agreement.md](reports/treebank_agreement.md), sentence
  7) until cross-checking Way's 1913 translation ("'twas at a stag she
  hurled") pointed at `ἔλαφος` "stag/deer" — genitive `ἐλάφοιο` is exactly
  the epic form `τιτυσκομένη` ("aiming at") would govern, and fits the
  context perfectly. Not yet confirmed against a critical edition, but
  high-confidence.
