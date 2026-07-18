---
title: 1st/2nd-person pronouns are reliable by lemma, not by morph tag
description: Personal pronouns can be found reliably by matching lemma + POS (elision aside), but the `person` feature is almost never populated and `gender`, where populated, isn't tracking anything real — traced through both this project's models and the three treebanks' own gold conventions, down to an individual-annotator effect in the original AGDT source XML.
tags: [pos-tagging, morphology, pronouns, ud-treebanks, latincy-dev]
date: 2026-07-18
script: experiments/pronoun_person_gender.py
---

# 1st/2nd-person pronouns are reliable by lemma, not by morph tag

Started from a practical question: if you want to find 1st/2nd-person personal
pronouns (ἐγώ/σύ and their forms) in this corpus, should you match on `pos=PRON` +
`person∈{1,2}`, or on `pos=PRON` + a fixed lemma list? Reproduce everything below
with `python3 experiments/pronoun_person_gender.py` (clones the three UD treebanks,
shared with [de_pos_tagging.py](de_pos_tagging.py), and the original pre-UD-conversion
AGDT treebank source at a pinned commit; also reads this project's own
`data/comparison/aligned_tokens.csv`).

## 1. The apparent cross-model disagreement is about `person`, not identification

Naively comparing which tokens each model tags as a 1st/2nd-person pronoun looks
like near-total disagreement: on unelided tokens where *any* model flags
`PRON`+`person∈{1,2}`, `lg` finds 118+75, `odycy` 30+54, `trf` only 7+4 — almost no
three-way overlap. But checking what POS each model actually assigns on that same
set shows they agree almost completely: `lg` 279/279 PRON, `trf` 274/279, `odycy`
275/279. The three models aren't disagreeing about which words are pronouns — they're
disagreeing about whether to bother populating the `person` feature once they've
correctly identified one.

## 2. `person` is blank for every grammatical person, not just 1st/2nd

Broadening from ἐγώ/σύ specifically to 3rd-person pronouns (ὁ, ὅς, ἕ/μιν/σφεῖς,
αὐτός) shows the same near-total blank rate across the board:

| lemma class | `lg` blank | `trf` blank | `odycy` blank |
|---|---|---|---|
| 1st (ἐγώ) | 97.1% | 99.8% | 99.2% |
| 2nd (σύ) | 97.6% | 99.9% | 98.3% |
| 3rd (ὁ) | 99.5% | 100.0% | 100.0% |
| 3rd (ὅς) | 100.0% | 100.0% | 100.0% |
| 3rd (ἕ/μιν/σφεῖς) | 98.4% | 100.0% | 100.0% |
| 3rd (αὐτός) | 89.2% | 100.0% | 100.0% |

`trf`/`odycy` leave `person` blank on essentially every pronoun regardless of which
person it grammatically is; `lg` is the only one that ever fills it in at a
non-trivial rate, and even it stays under 11% everywhere.

## 3. Traced to the gold treebanks' own training conventions

Checking `Person` marking directly in each treebank's train split:

| treebank | 1st person marked | 2nd person marked |
|---|---|---|
| Perseus | 9.0% | 4.9% |
| PROIEL | 100.0% | 100.0% |
| PTNK | 100.0% | 100.0% |

Model behavior tracks Perseus's rare-marking convention, not an average across
training sources — `grc_odycy_joint_trf` trains on Perseus *and* PROIEL, and PROIEL
alone contributes more raw ἐγώ/σύ tokens than Perseus (5,457 vs. 2,802), yet its
output looks like Perseus's minority convention won anyway. That's confirmed as a
fact about the training data; *why* Perseus's convention dominates despite
contributing fewer tokens isn't something this investigation pins down.

## 4. `Gender` on pronouns is a genuine three-way schema conflict, not noise

| treebank | `Gender` marked (pronouns) | what it actually looks like |
|---|---|---|
| PTNK | **0.0%** | deliberate — same treebank marks `Gender` on 100.0% of NOUN tokens |
| PROIEL | ~100% | mostly `Masc` (89%/51%) plus an explicit `Fem,Masc` ambiguity value (9%/48%) — a default-plus-ambiguity-flag pattern, not referential tracking |
| Perseus | 100% (1st) / 67% (2nd) | single-valued Masc/Fem splits (81%/19% and 54%/13%), with a genuine 33% blank rate for 2nd person specifically (see §5) |

PTNK's 0% isn't FEATS sparsity — it's a real, specific policy (confirmed against
its own 100% NOUN rate). PROIEL's near-100% looked like principled marking from a
distance but turns out to be mostly a default value plus an explicit
"don't know" flag.

Independent of the gold data, this project's own models show the same
non-referential pattern directly: `lg` tags `ἐμοί` as `Gender=Fem` identically in
two near-identical formulaic Odyssey lines (10.406, spoken by Circe; 4.481, spoken
by Menelaus) — same formula ("ὣς ἔφατ᾽, αὐτὰρ ἐμοί γ(ε) ..."), same tag, opposite
real speaker, no feminine word anywhere nearby in either line to explain it as local
agreement. Whatever produces that tag isn't tracking who's actually speaking.

## 5. Perseus's 2nd-person blank rate is an annotator-count effect

Section 4's 33% blank rate for 2nd person turns out to average over two very
different populations. Breaking it down by source document (and, since the
UD-converted CoNLL-U carries no annotator metadata at all, going back to the
original pre-conversion AGDT XML for annotator counts):

| document | total | `Gender` blank | annotators |
|---|---|---|---|
| Iliad | 615 | 43.1% | 22 |
| Sophocles (5 plays) | 48–95 each | 0–9.5% | 1 each |
| Herodotus | 94 | 33.0% | 2 |
| Hesiod, *Works and Days* | 35 | 97.1% | 6 |
| Aeschylus | 18 | 94.4% | 1 |
| Homeric Hymns | 15 | 100.0% | 1 |

Every single-annotator document sits at an extreme — near-0% or near-100% blank,
because it really is one person's judgment call applied consistently throughout.
Every multi-annotator document sits in the middle. That's a real, checkable pattern
(not proof of causation for any individual sentence — no per-sentence annotator
attribution survives in either the UD conversion or the original XML, only a
`subdoc` line-range with no key back to a person, so the Iliad's internal 43% can't
be attributed to specific annotators).

This also rules out two earlier, wrong explanations worth naming so they don't get
re-investigated: it isn't Morpheus (the deterministic morphological analyzer used
for the underlying lemmatization) producing these values, since Morpheus operates
context-free on the wordform alone and σύ/ἐγώ carry no gender morphology to
generate a candidate from in the first place — whatever fills in `Masc`/`Fem` has
to come from the disambiguation step downstream of Morpheus, i.e. a human call. And
it isn't that the blanks cluster on generic/gnomic "you" address (a plausible guess
that a manual sample of 20 blank tokens disconfirmed — they're ordinary
specific-addressee dialogue, same as the tokens that do get marked).

## Bottom line

| model | `person∈{1,2}` + `PRON` search | lemma-list + `PRON` search |
|---|---|---|
| `lg` | 194 | 6,478 |
| `trf` | 12 | 6,755 |
| `odycy` | 84 | 6,872 |

If you want to find 1st/2nd-person pronouns in this corpus (or any corpus tagged by
one of these three models), match on a fixed lemma list (ἐγώ, σύ, ἡμεῖς, ὑμεῖς) +
`pos=PRON` — reliable except for elided forms, which is a separate, already-documented
problem (see [elision_apostrophe_bug.md](elision_apostrophe_bug.md)). Don't search on
`person`; it's populated on roughly 1 in 50 to 1 in 800 true instances depending on
model, and the rate difference between models reflects training-data provenance, not
relative model quality. And don't treat a populated `gender` value on these words as
meaningful at all — the feature has no morphological basis for this word class in the
first place, and where it's filled, both the gold data and this project's own models
show it isn't reliably tracking anything true about who's speaking or being addressed.
