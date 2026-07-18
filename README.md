# greek_models

Comparing spaCy models for Ancient Greek NLP on a corpus of epic poetry (Iliad,
Odyssey, Argonautica, Posthomerica, *Sack of Troy*, Dionysiaca), with speech
annotation merged in from [DICES](https://github.com/cwf2/dices-client).

See [MODELS.md](MODELS.md) for which models have been tested,
[reports/](reports/INDEX.md) for the findings themselves, and
[PREPROCESSING.md](PREPROCESSING.md) for data-quality issues found in the
Perseus source texts themselves (as opposed to model/tokenizer behavior).

## What's tracked vs. not

- **`data/` is gitignored entirely** — fully regenerable from the scripts below
  plus the source models (see `MODELS.md`).
- **`reports/` and `experiments/` are tracked.** Every finding worth keeping is a
  matched pair: `experiments/<topic>.py` regenerates the underlying data (no
  dead ends, just the reproducible path to the result), and
  `reports/<topic>.md` is the human-readable writeup, with a YAML frontmatter
  block (title/description/tags/date/script) that [build_report_index.py](build_report_index.py)
  reads to regenerate [reports/INDEX.md](reports/INDEX.md) — run it after
  adding or editing a report. Tags are free-form keywords, not a fixed taxonomy;
  `latincy-dev` marks a report as relevant to the LatinCy maintainer specifically,
  since some findings here are pure corpus/methodology notes with nothing
  actionable for a model developer.
- Some early reports predate the `experiments/` convention and point at one of
  the general-purpose scripts below (`compare_models.py` etc.) instead of a
  dedicated topic script — that's fine, the pairing just needs to be
  reproducible, not necessarily 1:1.

## Setup

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` is a full `pip freeze`, including the model wheels themselves
(pinned to exact HuggingFace URLs) — see [MODELS.md](MODELS.md) for what's in there.

## Pipeline

1. **Tag the corpus with one model:**
   ```
   python3 modeltest.py <model_name>   # e.g. grc_dep_web_lg
   ```
   Clones the Perseus `canonical-greekLit` texts into `data/canonical-greekLit/` if
   not already present, runs the model over all six texts, merges in DICES speech
   annotation, and writes one CSV per text to `data/tokens/`. Repeat per model.

2. **Compare models against each other:**
   ```
   python3 compare_models.py
   ```
   Aligns tokens across models (see caveat in `MODELS.md` — currently assumes 3
   models with one tokenizer-sharing pivot pair) and writes agreement stats,
   confusion matrices, and a full aligned-token table to `data/comparison/`.

3. **Build a human spot-check sample:**
   ```
   python3 spotcheck_sample.py
   ```
   Stratified, reproducible (fixed seed) sample of disagreements to manually
   adjudicate, written to `data/spotchecks/`. Review it with `python3 spotcheck_review.py`
   (local browser UI, saves straight back to the CSV). `data/spotchecks/` is the one
   tracked exception inside the otherwise-gitignored `data/` — your filled-in
   judgments are hand-produced, not regenerable.

## Reports

Free-form exploration (one-off shell/Python, dead ends included) happens
outside version control. Once a finding is solid enough to keep:

1. Write `experiments/<topic>.py` — a clean script that reproduces the
   relevant data, leaving out the exploratory dead ends.
2. Write `reports/<topic>.md` — the human-readable writeup, frontmatter
   included, citing `experiments/<topic>.py` as the reproduction path.
3. Run `python3 build_report_index.py` to refresh [reports/INDEX.md](reports/INDEX.md).
