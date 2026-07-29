---
title: A Claude-assisted first-pass treebank prototype for Quintus (Posthomerica 1.1-30)
description: The three existing parsers already produce full dependency trees that the pipeline discards; capturing them and using their disagreements to scaffold a hand-adjudicated silver CoNLL-U file gets less than half the tokens right by unanimous 3-way agreement, but the disagreements are cheap to spot and the resulting silver file is a real, usable first pass.
tags: [treebank, dependency-parsing, quintus, posthomerica, model-comparison, latincy-dev]
date: 2026-07-18
script: treebank_base.py, experiments/treebank_agreement.py
---

# A Claude-assisted first-pass treebank prototype for Quintus (Posthomerica 1.1-30)

Prototype for building real dependency treebanks for authors with no existing
gold treebank — starting with Quintus Smyrnaeus (Posthomerica), confirmed
absent from both `data/agdt_source/` and the UD-converted treebanks in
`data/ud_treebanks/` (those cover Iliad/Odyssey/Argonautica-adjacent texts,
not `tlg2046`/`tlg2045`). Nonnus (Dionysiaca) is the intended second pass,
deferred until this procedure is validated.

## The base layer was already there

`uva_common.nlp.line_array_to_token_table` (what `modeltest.py` calls) reads
`token.pos_`/`token.morph` but never `token.dep_`/`token.head`/sentence
boundaries — even though all three models (`grc_dep_web_lg`, `grc_dep_web_trf`,
`grc_odycy_joint_trf`) ship a `parser` + `senter` component and already emit
standard UD deprel labels (`nsubj`, `obj`, `nmod`, `parataxis`, ...), confirmed
by direct inspection rather than assumed. [treebank_base.py](../treebank_base.py)
re-extracts a bounded line range straight from the source XML (mirroring, not
editing, `uva_common`'s private book/line helpers, since that package is
shared with the DICES project) and runs the pipeline directly so this
structure survives, writing one CSV per model to `data/treebanks_base/`.

## How much do three Homer-trained parsers agree on Quintus's syntax?

[experiments/treebank_agreement.py](../experiments/treebank_agreement.py)
aligns the three models' output for Posthomerica 1.1-31 (220 tokens, 9
complete sentences — book 1 line 30 cuts a sentence in half, so the bound
was extended one line to `ἄφραστοι·` rather than ship a truncated final
sentence) and compares head+deprel per token:

| | agree across all 3 |
|---|---|
| head | 122/220 (55%) |
| deprel | 149/220 (68%) |
| both | 99/220 (45%) |

Substantially lower than this corpus's POS-tagging agreement (see
[model_comparison_report.md](model_comparison_report.md)) — unsurprising,
since syntax is a harder transfer target than tagging, and confirms the
premise that these parsers' *dependency* output needs the same
disagreement-driven adjudication treatment already used for POS, not blind
trust. `grc_dep_web_lg` (the non-transformer tagger) is disproportionately
the odd one out in 3-way splits, consistent with its existing reputation in
this repo ([MODELS.md](../MODELS.md)) as the weaker of the two LatinCy models.

Per-sentence, agreement ranged from "majority" (6/8 to 17/28 tokens) to
"split" (as low as 2/7): the long, syntactically dense sentences (a
51-token and a 42-token sentence built from chains of coordinated relative
and content clauses) are exactly where the parsers diverge most, and where
adjudication time actually needs to go — a concrete instance of the "flag
hard cases for review" value this whole approach is supposed to deliver.

## The silver file: [data/treebanks/tlg2046.tlg001.perseus-grc2.1.1-30.silver.conllu](../data/treebanks/tlg2046.tlg001.perseus-grc2.1.1-30.silver.conllu)

Hand-adjudicated (by Claude, this session) from the three candidate parses
plus close reading of the Greek, cross-checked against how
`UD_Ancient_Greek-Perseus`/`PROIEL` handle structurally similar
constructions. Structurally validated: exactly one root per sentence, no
cycles, no out-of-range HEAD indices. Each sentence carries a
`# claude_agreement` comment (unanimous/majority/split) so a human reviewer
can prioritize the split sentences first rather than re-checking everything
uniformly — the same triage principle as `data/spotchecks/`.

### Recurring corrections applied across (not spot-fixed once)

- **`amod` vs `nmod` for attributive adjectives.** All three models tag a
  plain adjective-agreeing-with-its-noun (`θεοείκελος Ἕκτωρ`, `πυκνά
  [ῥωπήια]`, etc.) as `nmod` rather than `amod`, consistently. Checked
  against `UD_Ancient_Greek-Perseus`'s training data directly: `amod` is a
  real label there (931 instances) but heavily outnumbered by `nmod` on
  ADJ-tagged tokens (9984) — this looks like a known inconsistency in the
  AGDT-to-UD conversion these models trained on, not a deliberate
  convention, so the silver file uses `amod` per strict UD guidelines rather
  than reproducing the training-data noise.
- **Tmesis** (`ἀπὸ ... ἴαψεν`, a detached verbal preverb, common in this
  epic register): tagged `ADV`+`advmod` on the verb rather than `ADP`+`case`
  on a noun it doesn't actually govern. Worth deciding once and applying
  consistently, since epic tmesis will recur constantly in Nonnus too.
- **Lemma normalization on elided/crasis forms** (`δʼ`→`δέ`, `ἀπʼ`→`ἀπό`,
  `διʼ`→`διά`, `τοὔνεκʼ`→`τοὔνεκα`, `αὐτίχʼ`→`αὐτίκα`) and a couple of
  outright lemma misses (`ἐπιειμένη` lemmatized as if from `ἐφέζομαι`
  "sit upon" rather than `ἕννυμι` "clothe"; `ἀλευαμένη` left unlemmatized).
  Same lemmatizer gap already documented in
  [elision_apostrophe_bug.md](elision_apostrophe_bug.md), now confirmed to
  extend past elision proper to crasis and other apostrophized forms.

### The one flagged sentence, resolved by a translation lookup

`τὴν γάρ ῥα κατέκτανε δουρὶ κραταιῷ, οὐ μὲν δή τι ἑκοῦσα, τιτυσκομένη δʼ
ἐλάθοιο·` — the subject reference of the two feminine participles
(`ἑκοῦσα`, `τιτυσκομένη`) and the sense of `ἐλάθοιο` (which doesn't
lemmatize to anything attested) weren't resolvable from grammar alone.
Rather than guess, the sentence was flagged `# claude_note = REVIEW` and
left with a best-effort structural analysis, which is exactly the failure
mode this whole approach is supposed to have: cheap coverage everywhere,
explicit flags where a human (or a commentary) is actually needed.

It turned out a single lookup resolved it: Way's 1913 translation (public
domain; see `data/translations/`) makes clear the subject throughout is
Penthesileia, not Achilles — she accidentally killed her own sister
Hippolyta while aiming at a stag. That also explains `ἐλάθοιο`: almost
certainly a θ/φ transcription error for `ἐλάφοιο` (genitive of `ἔλαφος`
"stag/deer" — logged in [PREPROCESSING.md](../PREPROCESSING.md)), the
genitive object `τιτυσκομένη` ("aiming at") would govern. The silver file
now reflects this (still flagged for a critical-edition check on the
`ἐλάθοιο`/`ἐλάφοιο` question, but no longer blocking on subject reference).

This is the concrete answer to "would translation access help": yes, this
specific crux was a lexical/referential gap no amount of re-reading the
Greek alone was going to close, and a 1913 public-domain translation closed
it in one lookup. Worth doing routinely for hard-flagged sentences going
forward, especially for Nonnus, where familiarity is thinner still.

### Also found in passing: a likely transcription error

`ὄβριμου` (book 1 line 8) is grammatically required to agree with `ἄνδρα`
(accusative), but `-ου` is a genitive ending — looks like the same ν/υ
letter-confusion class already logged in
[PREPROCESSING.md](../PREPROCESSING.md) for Dionysiaca/Posthomerica, just
not yet in that doc's spot-checked list. FORM is kept as printed in the
silver file (that's what's actually in the source), with the correction
noted in a `# claude_note` comment and the intended case annotated in FEATS.

## Known limitations of this pass (not fixed, by design — see deferred scope)

- FEATS wasn't independently re-derived for every token — where I didn't
  have a specific reason to override, it's carried through from
  `grc_dep_web_trf`'s output as-is, including at least one known-unreliable
  category (gender on 2-termination adjectives, e.g. `θεοείκελος` tagged
  Fem agreeing with a masculine noun).
- MISC/`SpaceAfter` wasn't populated (all `_`).
- This is 30 lines. It validates the procedure and surfaces the issues
  above; it says nothing yet about whether accuracy holds up at book scale
  or on Nonnus, whose syntax is expected to diverge from these Homer-trained
  parsers considerably more than Quintus's does.
- **This pass is not finished.** The silver file reflects one round of
  adjudication on a small, deliberately-scoped prototype passage — treat it
  as a first-pass sample of the procedure, not a reviewed or stable dataset.
