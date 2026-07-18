---
title: grc_dep_web_lg is internally inconsistent on possessive-adjective POS
description: lg's occasional DET tag on possessive adjectives isn't a principled tagset-convention difference from trf/odyCy -- the identical surface form gets 2-3 different tags from lg across occurrences.
tags: [pos-tagging, model-instability]
date: 2026-07-17
script: experiments/possessive_adjective_pos_instability.py
---

# grc_dep_web_lg is internally inconsistent on possessive-adjective POS

Small, low-severity, but concrete. Spot-checking `ἐμὰ` (Odyssey 15.505,
`ἑσπέριος δʼ εἰς ἄστυ ἰδὼν ἐμὰ ἔργα κάτειμι`) showed `grc_dep_web_lg` tagging it DET
while `grc_dep_web_trf` and odyCy both tag ADJ. The initial guess was a principled
tagset-convention difference (DET under a UD-style scheme vs. ADJ under an
AGDT-style one) — checking the full corpus disproves that.

## Corpus-wide check

1,643 tokens where at least one of the three models resolved the lemma to the
possessive-adjective family (`ἐμός`, `σός`, `ἡμέτερος`, `ὑμέτερος`, `σφέτερος`):

| model | ADJ | PRON | DET | other |
|---|---|---|---|---|
| `lg` | 1,571 (95.6%) | 37 | **14 (0.85%)** | 21 (NOUN/ADV/VERB/X) |
| `trf` | 1,619 (98.5%) | 20 | 0 | 4 (PUNCT/PART/ADV) |
| `odyCy` | 1,622 (98.7%) | 21 | 0 | 0 |

`trf` and odyCy never produce DET for this family at all. `lg` does, but only 0.85%
of the time — not a rule it applies consistently, an occasional deviation. 3-way POS
agreement across the family is 94.0%.

The clearest evidence it's instability rather than convention: **the identical
surface form gets different tags from `lg` across different occurrences**, with
`trf`/odyCy's tag on the same tokens staying constant:

| surface form | occurrences | `lg` tags seen |
|---|---|---|
| `ἐμὰ` | 24 | ADJ, DET, **PRON** — three different tags |
| `ἐμὸν` | 199 | ADJ, DET |
| `ἐμὸς` | 87 | ADJ, DET |
| `ἐμοῦ` | 28 | ADJ, PRON |
| `ἡμετέρης` | 28 | ADJ, NOUN |

Since `lg`/`trf` share a tokenizer and the surface string is identical token-for-token,
this isn't a tokenization artifact — it's the tagger itself being unstable on this
closed word class, context-dependent rather than principled.

## Not proposing a specific fix

This reads like a calibration/training-data issue on a narrow closed class rather than
something with an obvious lookup-table remedy, and it's infrequent enough (0.85%
lg-DET-vs-ADJ) that it may not be worth prioritizing. Noting it mainly because
"`lg` systematically uses a different POS convention than `trf`" would be the wrong
takeaway if someone else runs into this same single-token disagreement and assumes
it's principled the way the ὅς DET-vs-PRON split sometimes legitimately is elsewhere
in Greek treebanks (compare
[pronoun_te_univerbation.md](pronoun_te_univerbation.md), where the disagreement
*is* a genuine no-correct-answer case rather than instability).

## Note on scope of the corpus-wide count

The 1,643-token count above matches a token if *any* of the three models resolved its
lemma to the family — lemma resolution on inflected/elided forms in this family isn't
fully reliable either (e.g. `ἐμῇς`, `ἐμῷ`, `ἡμέτερʼ` show up as distinct unresolved
lemmas rather than folding into `ἐμός`/`ἡμέτερος`), so anchoring to a single model's
lemma column would undercount.
