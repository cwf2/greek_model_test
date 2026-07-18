---
title: δέ POS tagging — gold-treebank divergence and a training-schema attribution
description: The three official grc UD treebanks genuinely disagree on how to tag δέ; PART turns out to be a document-provenance artifact confined to Perseus's Homer-heavy train split and invisible to any of the three treebanks' benchmarks; and the specific ADV-vs-CCONJ direction each of this project's models drifts toward on stylistic outliers (Nonnus, Tryphiodorus) tracks which treebanks fed its training.
tags: [pos-tagging, particles, ud-treebanks, latincy-dev]
date: 2026-07-18
script: experiments/de_pos_tagging.py
---

# δέ POS tagging — gold-treebank divergence and a training-schema attribution

Started from a simple question — why does δέ get different UPOS tags across
models? — and traced it to root causes across the gold treebanks themselves, not
just this project's three models. Reproduce everything below with
`python3 experiments/de_pos_tagging.py` (clones `UD_Ancient_Greek-{Perseus,PROIEL,PTNK}`
at pinned commits into `data/ud_treebanks/`, then reads this project's own
`data/tokens/*.csv` and the installed models' `meta.json`).

## 1. The three official grc UD treebanks disagree with each other on δέ

| treebank | δέ tags |
|---|---|
| PROIEL (NT Gospels + Herodotus *Histories*) | **100% ADV**, every split |
| PTNK (Septuagint, Codex Alexandrinus) | **100% CCONJ**, every split |
| Perseus | dev/test: ADV/CCONJ only. **train: majority PART** (see §3) |

This isn't noise — it's a real theoretical split. Checking where δέ's clause
attaches (its head token's own deprel: `root` = independent/paratactic, `conj` =
syntactically coordinated):

| treebank | root% | conj% |
|---|---|---|
| PROIEL | 86–88% | 7–9% |
| Perseus | 91–92% | ~0% |
| PTNK | 63–68% | 27–35% |

PROIEL treats δέ as a discourse particle that essentially never syntactically
coordinates two clauses (consistent with the older Denniston/Bakker view of
postpositive particles as discourse-organizers, not conjunctions). PTNK is
3–4× more willing to attach the clause via `conj` (the traditional
grammar-book view: δέ is a coordinator). Perseus sits in between structurally
but tags almost none of it CCONJ regardless.

## 2. All three of this project's models default overwhelmingly to PART for δέ

70–100% PART across every model/author combination (see `data/tokens/*.csv`) —
which is striking given **PART barely exists in any of the three treebanks'
dev/test splits** (never in PROIEL or PTNK at all; only in Perseus's train). Don't
treat these models' PART output on δέ as implementing a deliberate UD-standard
convention — it isn't one any of the three treebanks' benchmarks would recognize.

## 3. Where PART actually comes from: a single-document artifact in Perseus's train split

Per-document breakdown of `{δέ,τε,γάρ,μέν,ἄν,ἄρα,γε}` tags in `grc_perseus-ud-train.conllu`:

| document | genre | PART% |
|---|---|---|
| Homer, *Iliad* (`tlg0012`) | verse | **100.0%** (8,629/8,630 — 63% of ALL train PART) |
| Sophocles (`tlg0011`) | verse | **99.9%** |
| Hesiod (`tlg0020`) | verse | **100.0%** |
| Aeschylus (`tlg0085`) | verse | **100.0%** |
| Athenaeus (`tlg0008`) | prose | 0.0% |
| Herodotus (`tlg0016`) | prose | 0.0% |
| Diodorus Siculus (`tlg0060`) | prose | 0.0% |
| Homeric Hymns (`tlg0013`) | **verse** | **0.0%** |

Not a verse-vs-prose pattern — Homeric Hymns is verse and 0% PART, ruling that
out. It's a clean, binary, per-document artifact: each work is either ~100% or
~0% PART, no middle ground, consistent with an annotation-history split (Homer,
Sophocles, Hesiod, Aeschylus were annotated earliest in the source AGDT project
and apparently never reconverted when the newer ADV/CCONJ convention was
adopted). Confirmed via git history: `git log -S PART` on
`grc_perseus-ud-dev.conllu` and `grc_perseus-ud-test.conllu` returns **zero
commits** for either — PART hasn't just been fixed there at some point, it has
never existed in either file at any point in this repo's history.

Since Homer's *Iliad* alone accounts for 63% of all train PART instances, a
tagger trained on this data learns an unusually strong, Homer-anchored
"this context → PART" rule (§5).

## 4. None of the three treebanks' benchmarks touch epic verse at all

| treebank | dev/test genre |
|---|---|
| Perseus | Athenaeus (dev also: Thucydides, Plutarch) — all prose |
| PROIEL | New Testament Gospels + Herodotus *Histories* — all prose |
| PTNK | Septuagint (Genesis, ...) — prose/narrative translation-Greek |

Every PART-affected document (Homer, Sophocles, Hesiod, Aeschylus) sits only in
Perseus's train split and is completely absent from any of the three treebanks'
evaluation data. This isn't a magnitude-too-small-to-notice problem — it's that
the specific texts where the PART artifact lives were never sampled into any
benchmark at all. **Whatever accuracy number any of these three models publish,
none of it reflects performance on epic hexameter verse** — the entire genre this
project's corpus (Iliad, Odyssey, Argonautica, Posthomerica, Sack of Troy,
Dionysiaca) is built from has zero representation in held-out evaluation data
anywhere in this ecosystem.

One caveat found while checking this: Perseus's Athenaeus test data isn't purely
prose narration either — Athenaeus quotes extensively from lost comedy (its
Book 13, on courtesans, especially), and at least one such quotation is included,
untagged as such, as an ordinary sentence in the treebank:

> Attribution: *"Ἄλεξις δ̓ ἐν τῷ ἐπιγραφομένῳ δράματι Ἰσοστάσιον ... οὕτως ἐκτίθεται·"*
> ("Alexis, in the play titled Isostasion, sets it out as follows:")
> Next sentence: *"πρῶτα μὲν γὰρ πρὸς τὸ κέρδος καὶ τὸ συλᾶν τοὺς πέλας..."* — the
> quoted Middle Comedy fragment itself.

So "no verse at all" is too strong for Perseus's test split specifically — it's
more precisely "no *dactylic hexameter* verse," since comic trimeter is
metrically, syntactically, and register-wise quite different from the epic verse
this project's corpus uses. The general point (no benchmark here reflects epic
performance) still holds.

## 5. Training-schema attribution for the Nonnus/Tryphiodorus outlier

This project's own models (`data/tokens/*.csv`) show Nonnus and Tryphiodorus
consistently drifting away from PART toward ADV/CCONJ, more than the other three
authors (Homer, Apollonius, Quintus) — and this holds even restricted to
unelided "proper" δέ tokens, so it isn't just an elision-rate artifact (see
[elision_apostrophe_bug.md](elision_apostrophe_bug.md) for that separate,
already-documented bug; δέ's own elision rate is a further, independent data
point: Nonnus is 27.1% vs. 54–68% for the other four authors, a genuine textual
outlier).

Checked which treebanks actually fed each model, via the installed `meta.json`
(not guessed from the web): `grc_dep_web_lg`/`grc_dep_web_trf` trained on
**PTNK+PROIEL+Perseus combined**; `grc_odycy_joint_trf` on **Perseus+PROIEL only**
(no PTNK). Since PROIEL is the only source that's 100% ADV and PTNK the only one
that's 100% CCONJ (§1), this is testable — Δ vs. Homer's own PART% baseline:

| model | Nonnus ΔADV | Nonnus ΔCCONJ | Tryphiodorus ΔADV | Tryphiodorus ΔCCONJ |
|---|---|---|---|---|
| odyCy (no PTNK) | +10.3 | +5.3 | +10.4 | +6.3 |
| dep_web_trf (has PTNK) | +3.2 | +10.8 | +1.6 | +4.4 |
| dep_web_lg (has PTNK) | +2.7 | +2.1 | +7.3 | +2.3 |

odyCy shifts almost entirely toward ADV — the only schema in its training data
that tags δέ that way. `dep_web_trf` shifts predominantly toward CCONJ, at a
magnitude PROIEL alone can't produce (PROIEL never outputs CCONJ for δέ) —
attributable to PTNK. `dep_web_lg` shows a smaller, more balanced nudge in both
directions (weaker/non-transformer tagger, less decisively pulled either way).

**Caveat on mechanism**: PTNK (Septuagint) and Nonnus's *Dionysiaca* aren't
stylistically close at all despite both being loosely "late Greek" — LXX is
plain, paratactic translation-Greek; Nonnus is maximally ornate literary verse.
The more likely explanation isn't genuine register-detection but PTNK being a
*totally uniform* 100%-CCONJ signal that the tagger regresses toward as a
low-confidence default when it hits Nonnus's unusual vocabulary/syntax — not
because it recognizes Nonnus as LXX-like.

## Scope note

This investigation used δέ as a case study, but the underlying problems — the
elision-lemma split, PART as an unreliable/non-standard default, and
training-schema drift on stylistic outliers — plausibly generalize to other
high-frequency particles (γάρ, μέν, οὖν, δή, τε, ἀλλά, μή, οὐ, ἄν all showed the
same lemma-frequency-dominance pattern when checked). Not yet verified per-particle;
worth checking if this becomes a recurring question.
