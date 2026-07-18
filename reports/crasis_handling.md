---
title: Crasis handling across the three models
description: lg/trf never split a genuine crasis form; odyCy splits at least 4 forms at the internal breathing mark, but not universally. A previously-reported "trf under-splitting bug" turns out to be a source-text issue, not a tokenizer bug.
tags: [tokenizer-bug, crasis]
date: 2026-07-16
script: experiments/crasis_handling.py
---

# Crasis handling across the three models

Follow-up to a tokenization-mismatch pattern noticed while comparing odyCy against
`lg`/`trf`: does any model ever split a genuine crasis form (two words fused with a
coronis, e.g. `τἆλλα` = `τὰ` + `ἄλλα`) at the internal breathing mark?

## Detection method

A token starting with a consonant that also contains a character whose **fully
recursive** NFD decomposition includes psili (U+0313) or dasia (U+0314) — i.e. an
internal breathing mark not in word-initial position, which is what a crasis coronis
is. (A single-level `unicodedata.decomposition()` call isn't enough — `ἆ` decomposes
to alpha+circumflex first, and only *that* alpha's own decomposition contains the
psili — see the script for the fix.)

This signature also catches two unrelated things as false positives / side effects,
handled separately below: a known source-text encoding issue, and (see the
correction at the end) what looked like a tokenizer bug but wasn't.

## Result: lg/trf never split; odyCy splits selectively

101 candidate tokens matched the signature in `grc_dep_web_lg`'s token list. 25 are
already-documented source-text corruption (PREPROCESSING.md — an accent mis-encoded
as a breathing mark, e.g. `καἰ` for `καί`), leaving 76 real candidates.

- **0 of the 76 are missing from `grc_dep_web_trf`'s token list** — confirms `lg` and
  `trf` (shared tokenizer) never split a crasis form, no exceptions found.
- **3 of the 76 are missing from `grc_odycy_joint_trf`'s token list**: `καὐτὸς`,
  `προὔχοντα`, `τἆλλα` — these get split (`τἆλλα` → `τἆ` + `λλα`, etc.).

A 4th case doesn't fit the automated signature (it starts with a vowel: `οὑμὸς` <
`ὁ` + `ἐμός` — the breathing on the second letter looks like ordinary word-initial
diphthong breathing, the same shape as `οὐρανός`, so the consonant-initial filter
above misses it by design; there's no general fix without a lexicon). Checked by
hand: whole in `lg`, split in odyCy — so **4 confirmed crasis forms split by odyCy**:
`τἆλλα`, `καὐτός`, `οὑμός`, `προὔχοντα`.

odyCy's crasis-splitting is **selective, not universal** — plenty of other crasis
forms in the 76-candidate list (`κἀκεῖνος` and its inflected family, `τἀμὰ`,
`χἠμεῖς`, `καὐτή`, `χἀζοντʼ`) aren't in the missing list, i.e. odyCy handles those
correctly. Worth knowing if odyCy is ever preferred for other reasons — this bug
doesn't disqualify it wholesale, it's narrow.

## Correction: the "trf under-splitting bug" is a source-text issue, not a tokenizer bug

The 2026-07-16 investigation that first found this also flagged 5 tokens where two
words appear glued together with no token boundary at all — `κρᾶτ̓ἀπέκοψε`
(Posthomerica 1.261), `δ̓ἐν` (8.492), `δ̓ἀλεγεινός` (14.193), `ποίησʼ—ὡς` (Odyssey
14.274), `γαμοστόλον·οὐρανόθεν` (Dionysiaca 43.374) — and attributed it to `trf`
specifically, as "the opposite failure mode from odyCy's crasis-splitting bug."

Rebuilding this check found **all 5 are present, whole and identically glued, in all
three models** — including odyCy, which has a completely independent tokenizer. Three
unrelated tokenizer implementations failing at exactly the same character position is
strong evidence this isn't any one tokenizer's bug at all: it's much more likely a
missing space/punctuation-boundary in the Perseus source XML itself, which no
whitespace/punctuation-driven tokenizer would ever be able to split correctly. This
belongs in [PREPROCESSING.md](../PREPROCESSING.md) as a source-text issue, not here as
a model-behavior one — flagging the correction rather than re-filing it, since
confirming against the raw XML for all 5 locations hasn't been done yet.
