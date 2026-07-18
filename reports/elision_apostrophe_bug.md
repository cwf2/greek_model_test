---
title: Elision-apostrophe lemmatization gap
description: U+02BC vs U+0027 codepoint mismatch breaks lemma resolution on 6.33% of the corpus across all three models (not just LatinCy), degrading POS/morph too.
tags: [lemmatization, elision, tokenizer-bug, latincy-dev]
date: 2026-07-16
script: experiments/elision_apostrophe_bug.py
---

# Elision-apostrophe lemmatization gap

**For:** the LatinCy developer's Claude, next round of `grc_dep_web_*` improvement
**From:** an inter-model comparison run on an epic-poetry corpus (external user, not the LatinCy team)
**Date:** 2026-07-16 (revised 2026-07-18: moved to the `reports/`+`experiments/` convention,
morph-agreement numbers below corrected to match `compare_models.py`'s own methodology —
see note at §6)

This report is self-contained; the author has no access to LatinCy training internals.
Everything below is **observed input→output behavior** of the released models, not a
reading of the tokenizer exception lists or lemma tables. Treat the mechanism claims
(marked *inferred*) as hypotheses to verify against the actual model source.

---

## TL;DR

Across a 496k-token Greek epic corpus, **6.33% of tokens (31,398) carry an elision
mark and are almost never lemmatized correctly** by any of the three models tested
(both LatinCy Greek models and odyCy). Root cause appears to be a **character-encoding
mismatch**: the source texts mark elision with **U+02BC ʼ (MODIFIER LETTER
APOSTROPHE)**, but lemma resolution is keyed to **U+0027 ' (ASCII APOSTROPHE)**. The
tokenizer handles U+02BC fine (keeps elided forms whole); the *lemmatizer* does not.

Two compounding problems on top of the base miss:

1. **`grc_dep_web_lg`'s neural lemmatizer actively hallucinates** corrupted lemmas on
   these tokens (e.g. `ὧδʼ` → `ὧδʼῖς`, `ἄρʼ` → `ἄρʼς`, `ἀλλʼ` → `̔ἀλλʼ`), whereas
   `grc_dep_web_trf` mostly leaves them as the raw surface form. The `trf` failure is
   recoverable/greppable; the `lg` failure is not.
2. **POS and morphology also degrade sharply on elided tokens**, not just lemma — so
   these tokens are unreliable across every column, and a naive downstream "just fix
   the lemma" won't rescue them.

**Do NOT fix this by normalizing U+02BC→U+0027 before the tokenizer** — that re-breaks
tokenization (details in §5). The correct layer is lemma lookup.

Reproduce everything below with `python3 compare_models.py` (writes the alignment
this report reads) then `python3 experiments/elision_apostrophe_bug.py`.

---

## 1. Environment

| item | value |
|---|---|
| Models | `grc_dep_web_lg` 3.8.2, `grc_dep_web_trf` 3.8.2, `grc_odycy_joint_trf` 0.7.0 |
| spaCy | 3.8.14 |
| `lg` pipeline | senter, tok2vec, tagger, morphologizer, **trainable_lemmatizer**, **lookup_lemmatizer**, parser |
| `trf` pipeline | senter, transformer, tagger, morphologizer, **trainable_lemmatizer**, **lookup_lemmatizer**, parser |

**Corpus** (Perseus TEI, CTS `perseus-grc2` editions): Iliad (`tlg0012.tlg001`),
Odyssey (`tlg0012.tlg002`), Argonautica (`tlg0001.tlg001`), Posthomerica
(`tlg2046.tlg001`), Quintus/*Sack of Troy* (`tlg0647.tlg001`), Nonnus *Dionysiaca*
(`tlg2045.tlg001`). 496,403 tokens aligned across all three models. `lg` and `trf`
tokenize **byte-for-byte identically** on all six texts (shared tokenizer), so any
lemma/POS/morph difference between them is purely downstream of tokenization.

---

## 2. The core finding

Elided token = surface form containing U+02BC ʼ (or, rarely, U+0027/U+2019). There
are 31,398 in the aligned set. A lemma is "unresolved" when it **still carries an
elision mark** — this is a stricter and more accurate test than "lemma != surface
form," because `lg`'s hallucinated lemmas (§4) differ from the surface form while
still being garbage, not a correct resolution.

| model | elided tokens | unresolved lemma |
|---|---|---|
| `grc_dep_web_lg` | 31,398 | **99.99%** |
| `grc_dep_web_trf` | 31,398 | **99.99%** |
| `grc_odycy_joint_trf` | 31,398 | **99.99%** |

**U+02BC-spelled elisions essentially never resolve**; the 3 stray U+0027-spelled
tokens in the corpus mostly do (2/3 resolve on `trf`) — the strongest evidence the
resolution path keys on U+0027, not U+02BC.

Codepoint census among elided tokens: U+02BC = 31,394; U+0027 = 3; U+2019 = 1. In the
raw source XML the U+0027 occurrences are overwhelmingly in XPath/markup and English
notes, **not** in the Greek text — Greek elision is essentially 100% U+02BC.

Most frequent affected forms (all indeclinable function words at the top — high
value, low ambiguity to fix):

| form | count | correct lemma |
|---|---|---|
| `δʼ` | 11,526 | δέ |
| `τʼ` | 1,536 | τε |
| `ἀλλʼ` | 1,395 | ἀλλά |
| `ἄρʼ` | 1,006 | ἄρα |
| `ἐπʼ` | 774 | ἐπί |
| `οὐδʼ` | 710 | οὐδέ |
| `γʼ` | 480 | γε |
| `ῥʼ` | 427 | ῥα |
| `μʼ` | 335 | με/μοι (ambiguous) |
| `ὑπʼ` | 327 | ὑπό |
| `κατʼ` | 284 | κατά |
| `θʼ` | 284 | τε (aspirated) |

`δʼ` alone is 36.7% of all elided tokens and 2.32% of the whole corpus — see
[reports/de_pos_tagging.md](de_pos_tagging.md) for what this specific bug does to δέ
frequency/POS analysis downstream.

---

## 3. Distribution across texts

Elision rate tracks metrical style, so the payoff is concentrated in Homeric-style
hexameter:

| text | elided tokens | % of text |
|---|---|---|
| Iliad | 11,157 | 8.76% |
| Odyssey | 8,942 | 8.74% |
| Posthomerica | 5,774 | 8.45% |
| Argonautica | 3,342 | 7.38% |
| Sack of Troy | 203 | 4.22% |
| Dionysiaca (Nonnus) | 1,978 | 1.33% |

(Dionysiaca's low elision rate here is corpus-wide across all elidable words, not
specific to δέ — see [de_pos_tagging.md](de_pos_tagging.md) for the δέ-specific
version of this same pattern, which is even more pronounced: 27.1% vs. 54–68% for
the other four texts.)

---

## 4. `lg`-specific: neural lemmatizer hallucination

*(inferred: this is the `trainable_lemmatizer` firing where the `lookup_lemmatizer`
has no U+0027 key to hit, and producing character-level garbage on the OOV-shaped
apostrophe-terminated string.)*

`trf` mostly copies the raw form through. `lg` instead emits corrupted strings on
1,145/31,398 elided tokens (3.6%) — cases where its lemma both still carries an
elision mark *and* doesn't match `trf`'s pass-through failure, i.e. it's not just
unresolved, it's actively different garbage:

| surface | `lg` lemma | `trf` lemma | note |
|---|---|---|---|
| `ῥʼ` | `ἄρʼ` | `ῥʼ` | wrong word entirely (ῥα ≠ ἄρα) |
| `ὧδʼ` | `ὧδʼῖς` | `ὧδʼ` | hallucinated suffix |
| `ἄρʼ` | `ἄρʼς` | `ἄρʼ` | hallucinated `ς` |
| `νῆʼ` | `νῆʼ` | `νʼῦς` | (here `trf` is the one that mutates) |
| `ἄλλοθʼ` | `ἄλλοθʼς` | `ἄλλοθʼ` | hallucinated `ς` |
| `ἀλλʼ` | `̔ἀλλʼ` | `ἀλλʼ` | breathing mark prepended |

Implication: for `lg`, elided-token lemmas are worse than useless — they can't even be
recovered by stripping the apostrophe, because the stem itself is altered. Worth a look
at whether the trainable lemmatizer should defer to (rather than override) the lookup
lemmatizer on tokens ending in an elision mark.

---

## 5. Why the "obvious" preprocessing fix is wrong

Normalizing U+02BC→U+0027 in the text **before** `nlp()` looked tempting and was
tested. It partially fixes lemmas for forms already in the tokenizer's U+0027
exception list — but the tokenizer's exception coverage for U+0027 is **incomplete**,
so many forms then get split into `stem + '` (a spurious lone-apostrophe token with a
garbage POS tag). On Iliad book 1 alone this introduced **+246 stray tokens**.

Tokenizer behavior on elided forms, by codepoint (verified against `grc_dep_web_lg`):

| form | U+02BC (source) | U+0027 (normalized) |
|---|---|---|
| `δʼ`, `τʼ`, `ἀλλʼ`, `ἐπʼ`, `μʼ`, `ὑπʼ`, `κατʼ`, `διʼ`, `παρʼ`, `μετʼ` | whole | whole ✓ (in exception list) |
| `ἄρʼ`, `οὐδʼ`, `γʼ`, `θʼ`, `ἀπʼ`, `μάλʼ`, `ἔνθʼ`, `ἀμφʼ`, `ἠδʼ` | whole | **SPLIT(2)** ✗ |

Key takeaways for the fix:

- The **tokenizer already keeps every elided form whole under U+02BC** — tokenization
  is *not* broken and should not be touched.
- The U+0027 tokenizer exception list is a **partial** subset of elided forms; relying
  on it (via preprocessing) trades a lemma bug for a tokenization bug.
- Therefore the fix belongs at **lemma lookup**: normalize the apostrophe (or add
  U+02BC-keyed entries) *inside* the lemmatizer lookup, after tokenization. That
  resolves lemmas without perturbing token boundaries, POS, or morph.

Suggested minimal change (to verify against actual internals): make the
`lookup_lemmatizer` key lookups run on an apostrophe-normalized form (`str.translate`
U+02BC/U+2019 → U+0027), and/or extend the lookup table with the U+02BC-spelled
indeclinables in §2. For `lg`, additionally gate the `trainable_lemmatizer` so it
doesn't overwrite a successful lookup hit on elided tokens (§4).

---

## 6. This is bigger than lemma — POS/morph degrade too

The elision mark degrades the whole analysis, likely because the apostrophe-terminated
token yields an embedding the models weren't trained to handle. Restricting to elided
tokens, using the same straight 3-way-equality methodology `compare_models.py` uses
for its corpus-wide numbers (so these are directly comparable, not a different metric):

| feature | elided | corpus-wide |
|---|---|---|
| POS | **44.9%** | 87.8% |
| gender | 73.8% | 90.4% |
| case | 73.9% | 93.0% |
| voice | 85.4% | 96.8% |
| tense | 85.7% | 95.9% |

> **Correction (2026-07-18):** the original version of this report cited much lower
> morph-agreement figures (gender 39.5%, voice 40.0%, case 53.1%, tense 59.8%) from an
> ad hoc, non-reproducible filtering pass. Rebuilding this analysis as
> `experiments/elision_apostrophe_bug.py` against `compare_models.py`'s own aligned
> output — the methodology used everywhere else in this project — gives the numbers
> above instead. The direction of the finding (morph collapses substantially on elided
> tokens, even accounting for how much these numbers dip corpus-wide too) is unchanged;
> only the magnitude was wrong.

Concrete: `ἀλλʼ` (= conjunction ἀλλά) gets tagged ADJ/Nom/Masc by `lg`, CCONJ by `trf`,
PART by odyCy — three different word classes, none right.

So even a perfect lemma fix leaves POS/morph on these 31k tokens meaningfully less
reliable than the rest of the corpus. If elided forms can be surfaced to the
tagger/morphologizer in a training-consistent way (e.g. consistent apostrophe
normalization applied uniformly in **training and inference**, or adding elided
function-word forms to training data), that would likely lift all four columns
together — a larger but higher-value fix than the lemma table alone.

---

## 7. Prioritized recommendations

1. **Lemma lookup normalization (cheap, safe, high coverage).** Apostrophe-normalize
   at lookup time and/or add U+02BC-keyed entries for the elided indeclinables in §2.
   Fixes the bulk of the 31k tokens (δʼ/τʼ/ἀλλʼ/ἄρʼ/... are the long tail's head). No
   tokenization impact.
2. **`lg` trainable-lemmatizer guard (targeted).** Stop it from overwriting/hallucinating
   on elision-terminated tokens; prefer the lookup result. Removes the §4 corruption.
3. **Uniform apostrophe handling in training + inference (larger, lifts POS/morph).**
   Address §6 so these tokens stop being an across-the-board weak point.
4. **Ambiguous elisions stay model's job.** Pronoun/verb elisions like `μʼ` (με vs μοι)
   or ambiguous stems are genuinely context-dependent — don't force these into a static
   table; they're the legitimate residual after 1–3.

Related findings: the pronoun+τε univerbation issue
([pronoun_te_univerbation.md](pronoun_te_univerbation.md)) and the `lg`
possessive-adjective instability ([possessive_adjective_pos_instability.md](possessive_adjective_pos_instability.md))
were both found while investigating this bug but are independent issues, not part of
the elision mechanism — split into their own reports rather than kept as asides here.
