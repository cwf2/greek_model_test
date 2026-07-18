---
title: Inter-model comparison on the Greek epic corpus
description: Corpus-wide POS/lemma agreement and disagreement patterns across grc_odycy_joint_trf, grc_dep_web_lg, and grc_dep_web_trf; no gold treebank, so this maps disagreement rather than accuracy.
tags: [model-comparison, pos-tagging, lemmatization]
date: 2026-07-16
script: compare_models.py
---

# Inter-model comparison: three spaCy models on the Greek epic corpus

Compares tagging output from `grc_odycy_joint_trf` (odyCy), `grc_dep_web_lg`, and
`grc_dep_web_trf` (LatinCy) across six epic texts (Iliad, Odyssey, Argonautica,
Posthomerica, Sack of Troy, Dionysiaca — 496k tokens total), based purely on
where the three models agree and disagree with each other. There is no gold
treebank for this specific corpus, so this is not an accuracy measurement —
it's a map of where the models diverge, meant to target the human review in
[Spot-check plan](#spot-check-plan) at the highest-information disagreements.

Method and code: [compare_models.py](../compare_models.py). Raw outputs:
`data/comparison/*.csv` (see [Data files](#data-files) below).

## Method

`grc_dep_web_lg` and `grc_dep_web_trf` share a tokenizer and produced
**byte-for-byte identical token sequences on every one of the six texts** — they
only differ in tagging weights. odyCy uses a different tokenizer and
occasionally segments differently, so tokens were aligned per verse line via
`difflib.SequenceMatcher`, falling back to exact match when sequences already
agreed (the common case). Only tokens with a 1:1 match across all three models
count toward the field-agreement statistics below; the 12 lines where odyCy's
segmentation doesn't align are analyzed separately.

## Headline numbers (496,403 aligned tokens)

| pair | POS agreement | lemma agreement |
|---|---|---|
| lg vs trf | 91.7% | 97.4% |
| lg vs odyCy | 89.5% | 83.1% |
| trf vs odyCy | 93.0% | 83.3% |
| **all three** | **87.8%** | **82.1%** |

Two things jump out immediately:

1. **trf agrees with odyCy more than lg does** — on every single field checked
   (POS, lemma, and all eight morph features), not just on average. lg and trf
   share a tokenizer and are both LatinCy models, so you'd expect them to
   cluster together against odyCy; instead trf consistently sits closer to
   odyCy than to its own sibling model.
2. **Lemma agreement is much lower than POS agreement**, and normalizing away
   accents/diacritics only recovers ~1 point (82.1% → 83.4% three-way) — so
   this isn't an orthographic-convention artifact, it's real disagreement
   about which dictionary form a token belongs to.

## Who's the odd one out?

Restricting to POS tags, of the 496k tokens: **87.8% all agree**, **10.7% are a
2-vs-1 split**, and **1.4% (7,091 tokens) have all three models disagreeing**.
Within the 2-vs-1 splits, the outlier is:

| odd one out | share of 2-vs-1 splits |
|---|---|
| `grc_dep_web_lg` | 48.3% |
| `grc_odycy_joint_trf` | 36.3% |
| `grc_dep_web_trf` | 15.4% |

`grc_dep_web_trf` is rarely the outlier — it's the most "central" model of the
three. `grc_dep_web_lg`, despite being the larger non-transformer LatinCy
model, breaks from a trf/odyCy consensus most often. This is a genuinely
useful prioritization signal: cases where **lg** or **odyCy** breaks from a
two-model consensus are the most likely to contain a real tagging error worth
checking, and the rare cases where **trf** is the outlier are worth checking
precisely *because* they're rare.

## Where the disagreement concentrates

**POS confusions** (all three pairs) are dominated by three known-hard
boundaries in Greek grammar, not random noise:

- **NOUN ↔ ADJ** (substantivized adjectives — e.g. `Κυανέας`, `Πελασγίδος`,
  `τοίην` all get NOUN from one model, ADJ from another)
- **DET ↔ PRON** (`ὁ`, `οἱ` as demonstrative/article vs. pronoun)
- **ADV ↔ PART ↔ CCONJ** (Greek particles — `μέν`, `δέ`, `τε`, `οὐδέ` — where
  the three tagsets appear to draw the ADV/PART/CCONJ line differently; this
  looks like an annotation-scheme difference more than an error)

**Elided and crasis forms are disproportionately represented** in the
disagreement sample: `ἔσσυτʼ`, `ἤμαθʼ`, `πάροιθʼ`, `βάσκʼ` all show up in the
all-three-disagree bucket. This also explains all 12 tokenization mismatches —
every one is a crasis word (`τἆλλα`→`τὰ ἄλλα`, `καὐτός`→`καὶ αὐτός`,
`οὑμός`→`ὁ ἐμός`, `προὔχοντα`→`προ-έχοντα`) where odyCy splits the crasis into
two tokens and LatinCy either keeps it whole or splits at a different point.

**Morph features**, conditioned on all three models agreeing on POS (so the
feature is at least comparable), from worst to best three-way agreement:

| field | all-3 agreement | dominant confusion |
|---|---|---|
| gender | 89.0% | spread across Masc/Fem/Neut, no single dominant pair — looks like genuine ambiguity (proper nouns, epithets), not a fixable bug |
| tense | 91.8% | — |
| case | 92.9% | **Acc ↔ Nom** is ~34% of all case disagreements — consistent with real neuter (and some other) case syncretism in Greek, not necessarily an error |
| number | 95.0% | — |
| voice | 96.8% | — |
| person | 97.5% | — |
| mood | 97.5% | — |
| verbform | 97.1% | — |

**Text-level pattern**: Iliad has the highest agreement of any text on every
single metric (POS, lemma, every morph field). Dionysiaca (Nonnus, 5th c. AD)
has the lowest lemma agreement (76–78%) of any text. This lines up with what
you'd expect from the models' training data — odyCy is Homer-specific, and the
LatinCy grc models are trained on treebanks weighted toward Classical/Homeric
material — so all three are more confident and more mutually consistent on
Homer than on the more linguistically idiosyncratic post-Homeric epic,
especially Nonnus's dense, neologism-heavy style.

| work | n tokens | POS all-3 | lemma all-3 |
|---|---|---|---|
| Iliad | 127,303 | 91.9% | 87.6% |
| Sack of Troy | 4,807 | 86.8% | 78.6% |
| Odyssey | 102,283 | 87.8% | 86.6% |
| Posthomerica | 68,311 | 87.8% | 82.4% |
| Argonautica | 45,305 | 85.0% | 80.9% |
| Dionysiaca | 148,394 | 85.3% | 74.8% |

## Data files

- `data/comparison/aligned_tokens.csv` — every token comparable across all
  three models, with each model's pos/lemma/morph and text/urn/speaker context.
- `data/comparison/tokenization_mismatches.csv` — the 12 lines with a
  segmentation mismatch.
- `data/comparison/summary_by_text.csv` / `summary_overall.csv` — agreement
  rates behind the tables above.
- `data/comparison/pos_confusion_*.csv` — full pairwise POS confusion counts.
- `data/comparison/spotcheck_sample.csv` — the human review sample, below.

## Spot-check plan

Goal: maximize what you learn per item reviewed, not sample uniformly — most
of the corpus already agrees, so a random sample would mostly show you
agreement. Instead the sample in `data/comparison/spotcheck_sample.csv`
(162 items, reproducible via `spotcheck_sample.py`, seed fixed) is stratified
into the categories the analysis above flagged as most informative:

| category | n | why |
|---|---|---|
| `tokenization_mismatch` | 12 | all of them — small, cheap, and all appear to be the same crasis-splitting issue; confirming that closes out a whole error class at once |
| `pos_all3_different` | 30 | the rarest, most severe disagreement (1.4% of tokens) — highest chance of a genuine tagging error rather than a scheme boundary |
| `pos_2v1_lg_odd` | 30 | lg is the outlier most often (48% of 2v1 splits) — worth confirming whether that reflects real lg weaknesses |
| `pos_2v1_odycy_odd` | 20 | odyCy as outlier (36% of splits) — tests whether its Homer-specific training helps or hurts outside Homer |
| `pos_2v1_trf_odd` | 10 | trf is rarely the outlier (15%) — when it is, worth knowing why |
| `morph_gender_disagree` | 15 | worst-agreeing morph field (89%), conditioned on POS already agreeing |
| `morph_case_disagree` | 15 | second-worst (93%), includes the Acc/Nom syncretism cases |
| `morph_tense_disagree` | 15 | third-worst (92%), verbs only |
| `control_all_agree` | 15 | **all three agree**, restricted to notoriously hard categories (optative mood, dual number, pronouns) — agreement isn't correctness, and this checks for a shared blind spot across all three models |

Every stratum keeps at least 2 examples per text where available, so no single
epic dominates the sample. Each row has the target token bracketed in its
verse-line context (`context` column), the relevant fields from all three
models, and blank `human_judgement` / `notes` columns to fill in (e.g. record
which model got it right, or "none of them" / "scheme difference, not an
error").

**Suggested order**: tokenization mismatches first (fastest, and likely to
resolve as one pattern), then `pos_all3_different` (most likely real errors),
then the 2-vs-1 POS strata, then the morph strata, and the control sample last
as a gut-check. At roughly a minute or two per item, the full 162-item sample
is a 2–4 hour task; if you want to cut it down, drop `control_all_agree` first
(lowest yield) and cap the 2v1 strata rather than skipping `pos_all3_different`
or the tokenization mismatches.

## Limits of this analysis

Agreement is a proxy, not ground truth — a category where all three models
agree could still reflect a shared training bias (e.g. all three under-trained
on Nonnus's vocabulary) rather than correctness, which is exactly why the
control stratum exists. Likewise, low agreement in a category like ADV/PART
may reflect an annotation-scheme boundary rather than any model being "wrong,"
so the spot-check should record scheme differences separately from actual
errors rather than forcing every disagreement into a right/wrong verdict.
