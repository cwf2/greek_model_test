---
title: Pronoun+τε univerbation has no correct single-token POS tag
description: The ὅστε "generalizing relative" family (relative pronoun + enclitic τε fused into one word) can't be represented by a single POS tag, and all three models split on how to be wrong about it.
tags: [pos-tagging, multi-word-token, sack-of-troy]
date: 2026-07-16
script: experiments/pronoun_te_univerbation.py
---

# Pronoun+τε univerbation has no correct single-token POS tag

Found while spot-checking `αἵτʼ` (Sack of Troy / Triphiodorus 535, part of a bee
simile: `ἥτε πολυξείνοιο ... αἵτʼ ἐπεὶ οὖν ἔκαμον πολυχανδέος ἔνδοθι σίμβλου`):
`grc_dep_web_lg` tags it ADJ, `grc_dep_web_trf` tags it PRON, and odyCy independently
tags it CCONJ. All three keep it as a single token — this genuinely is one word in the
source XML, not a tokenization split issue.

## Why no tag is fully correct

`αἵτʼ` (= `αἵ` + `τε`, elided) is the standard Homeric-epic univerbation of a relative
pronoun with the enclitic connective particle τε — the ὅστε/οἵτε/ἥτε "generalizing
relative" family (LSJ lists these under the pronoun entries, not as independently
lexicalized words). The token does two grammatical jobs at once: `αἵ` is the syntactic
head (nominative plural feminine relative pronoun), `τε` is a semantically bleached
connective riding along. No single part-of-speech tag covers both.

Universal Dependencies has a mechanism for exactly this: multi-word tokens (MWT),
where one orthographic form splits into multiple syntactic words each with its own
tag (the canonical example is French `du` → `de` + `le`). None of these three models
implement MWT splitting — they're all constrained to one POS per orthographic token —
so `trf`'s PRON (favoring the syntactic head) is the least-wrong option among the
three, not a genuinely correct one.

## Scope: how often does this actually happen?

Checked the whole corpus for the rest of the ὅστε family (`ὅστε`, `ἥτε`, `οἵτε`,
`αἵτε`, `αἵτʼ`, `ἥντε`, and their elided variants). 6 instances total, **all in Sack
of Troy** — this author/edition favors the construction; it doesn't appear anywhere
else in the six-text corpus.

| text | 3-way POS agreement | lemma resolves to ὅστε on all 3 |
|---|---|---|
| `ἥτε` (×2), `ὅστε` | yes (PRON) | yes |
| `οἵτε` | no (`lg`→ADJ, others→PRON) | yes |
| `ἥντε` | no (`lg`/`trf`→VERB, odyCy→PRON; also the only one that resolves to a *different* lemma family, odyCy→`ἥς`) | no |
| `αἵτʼ` | no (`lg`→ADJ, `trf`→PRON, odyCy→CCONJ) | no |

So 3 of 6 resolve cleanly to PRON/ὅστε on all three models — the construction usually
isn't a problem in practice. The two outliers that fail worst (`ἥντε`, `αἵτʼ`) share a
trait: they're the two *rarer* inflected forms, and `αἵτʼ` additionally stacks the
elision mark on top. That combination looks underrepresented in training data — lemma
resolution fails outright (stays as/near the raw surface form instead of resolving to
`ὅστε`) and POS diverges across models as a result, rather than the models
implementing three different *principled* readings of the construction.

## Not proposing a fix

This is a training-data-coverage question (rare inflected forms of a fused
function-word construction), not a lookup-table gap like the
[elision-apostrophe bug](elision_apostrophe_bug.md) — flagging in case it's useful
signal for what to oversample, or just interesting independent of any specific fix.
