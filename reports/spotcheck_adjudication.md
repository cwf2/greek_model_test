---
title: Spot-check adjudication summary
description: Human-adjudicated 162-row stratified sample of model disagreements. trf is right about half the time it's the outlier; lg and odyCy are right much less often when they are.
tags: [pos-tagging, lemmatization, human-adjudication]
date: 2026-07-17
script: experiments/spotcheck_adjudication.py
---

# Spot-check adjudication summary

All 162 rows of `data/spotchecks/spotcheck_sample.csv` — a stratified, reproducible
sample (fixed seed, `spotcheck_sample.py`) of disagreements between `grc_dep_web_lg`,
`grc_dep_web_trf`, and `grc_odycy_joint_trf` — have been hand-adjudicated via the
`spotcheck_review.py` browser tool. That tool and the adjudicated CSV are both
tracked in this repo (`data/spotchecks/` is the one tracked exception inside the
otherwise-gitignored `data/`, since the filled-in judgments are hand-produced and
not regenerable).

`human_judgement` records which model(s) got it right; `notes` has the reasoning.
`experiments/spotcheck_adjudication.py` computes the tallies below directly from
that column — it doesn't re-derive the judgments, only the arithmetic over them.

## Category breakdown

| category | n | what it samples |
|---|---|---|
| `pos_all3_different` | 30 | all three models disagree |
| `pos_2v1_lg_odd` | 30 | lg is the outlier, trf+odyCy agree |
| `pos_2v1_odycy_odd` | 20 | odyCy is the outlier, lg+trf agree |
| `pos_2v1_trf_odd` | 10 | trf is the outlier, lg+odyCy agree |
| `morph_gender_disagree` | 15 | |
| `morph_case_disagree` | 15 | |
| `morph_tense_disagree` | 15 | |
| `tokenization_mismatch` | 12 | (all traced to the crasis-splitting bug — see [crasis_handling.md](crasis_handling.md)) |
| `control_all_agree` | 15 | sanity check — all 15 confirmed correct |

## When a model is the odd one out, is it actually right?

| model | right when outlier | which ones |
|---|---|---|
| `trf` | **5/10 (50%)** | `μʼ`, `πείθοντʼ`, `βατὸν`, `ἐϋμμελίην`, `Τηλέμαχʼ` |
| `lg` | 2/30 (6.7%) | `ἀκμῆτες`, `ἀργῆτι` |
| `odyCy` | 3/20 (15%) | `χρεὼ`, `οἷα`, `καὶ` (scalar "even") |

**Correction:** this previously circulated as "trf right 6 of 10" — re-tallying
directly from the adjudicated CSV (excluding one row recorded as `none` and one
recorded as `ambiguous`, which don't cleanly credit any model) gives 5/10, not 6/10.
The direction of the finding is unchanged (trf is right about half the time it
disagrees with the other two; lg almost never is) — only the exact count was wrong.

In `lg`'s 30-row sample, both of its 2 wins are the same shape: `ἀκμῆτες` and
`ἀργῆτι` are directly-attributive adjectives that `trf`/odyCy misread as
substantivized nouns. See [possessive_adjective_pos_instability.md](possessive_adjective_pos_instability.md)
for a related but separate `lg` instability finding from this same review pass
(originally logged as row 64 here, `ἐμὰ`, before the corpus-wide check showed it
wasn't a principled tagset difference).

## Lemma resolution fails per-wordform, not per-lexeme

Three rows show the same pattern: a model gets the POS right but fails to resolve
the lemma to its citation form, specifically on an irregular inflected form whose
sibling forms resolve fine elsewhere in the corpus.

- `θάμβευς` → correct lemma `θάμβος`: odyCy right on POS, lg+trf right on lemma.
- `ἠχοῦς` → correct lemma `ἠχώ` (contract ω-stem noun): trf+odyCy right on POS
  (NOUN; lg says ADJ), lg+trf right on lemma — odyCy's "lemma" here is just the
  unresolved raw genitive, not a real resolution. Same failure shape as `θάμβευς`.
- `πουλὺς` → correct lemma `πολύς`: **all three models fail**, but the accusative
  sibling `πουλὺν` (same Ionic πουλ- spelling) resolves correctly to `πολύς` in all
  three, every time — including the *harder* transformation (inflectional reduction
  + dialect regularization together) — while the nominative `πουλὺς`, which needs
  only the smaller dialect swap, never does.

This rules out "models are deliberately treating these as distinct lemmas" — it's
sparse, uneven per-surface-form training coverage, not a semantic/lexical decision.
None of these three tokens are elided, so it's independent of the
[elision-apostrophe bug](elision_apostrophe_bug.md).

## Same lemma, unstable POS even when the tag is usually right

`ἀλλά`/`οὐδέ` as CCONJ is correct and is what all three models produce most of the
time — but in 2 sampled instances (both `οὐδέ`, both in the `pos_2v1_trf_odd`
category — see rows for `οὐδὲ`), none of the three models chose CCONJ. Model
instability on an otherwise-reliable call, not a systematic rule violation.

## Still open: 5 rows flagged REVIEW

`experiments/spotcheck_adjudication.py` lists these directly from the `notes`
column; they need a second adjudication pass rather than a fix:

- `συμπαθέων` (Sack of Troy) — participle vs. substantivized-adjective reading,
  both defensible.
- `ἵππου` (Sack of Troy) — deliberate feminine ("mare") imagery for the Trojan
  Horse; lg/odyCy default to masculine.
- `γναμπτὸν` (Iliad) — context fragment too short to confirm case role.
- `ἐσχαρόφιν` (Posthomerica) — Dat vs. Gen, idiomaticity judgment call.
- `ἄμφω` (Sack of Troy) — all three tag it Fem despite being gender-indeclinable;
  possibly a shared spurious default rather than genuine agreement.

Two rows that were originally flagged REVIEW are no longer open: `ὅπων` resolved as
a source-text transcription error (see [PREPROCESSING.md](../PREPROCESSING.md)) with
the POS question itself judged genuinely undecidable rather than left pending; and
`ἠῷος` was resolved in an earlier pass not detailed here.
