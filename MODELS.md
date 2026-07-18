# Model registry

Every model tested against the corpus, so a new session doesn't have to 
reconstruct this from `data/` (gitignored) or old chat history.

| model | version | source | tokenizer family | notes |
|---|---|---|---|---|
| `grc_dep_web_lg` | 3.8.2 | [latincy/grc_dep_web_lg](https://huggingface.co/latincy/grc_dep_web_lg) | LatinCy (shared w/ `grc_dep_web_trf`) | non-transformer tagger; see [reports/](reports/INDEX.md) for behavior notes |
| `grc_dep_web_trf` | 3.8.2 | [latincy/grc_dep_web_trf](https://huggingface.co/latincy/grc_dep_web_trf) | LatinCy (shared w/ `grc_dep_web_lg`) | transformer tagger; tokenizes byte-for-byte identically to `grc_dep_web_lg` on all six corpus texts |
| `grc_odycy_joint_trf` | 0.7.0 | [chcaa/grc_odycy_joint_trf](https://huggingface.co/chcaa/grc_odycy_joint_trf) | odyCy (own tokenizer) | Homeric-specific training; only model with its own tokenizer, so alignment against it requires `difflib` diffing per line in `compare_models.py` |

## Adding a model

1. `pip install <model-wheel-url>` into `venv`, then re-freeze: `pip freeze > requirements.txt`.
2. Add a row above (version, source, tokenizer family — check whether it shares a
   tokenizer with an existing model, the way `lg`/`trf` do, since that changes how
   cheaply `compare_models.py` can align it).
3. `python modeltest.py <model_name>` to populate `data/tokens/`.
4. **`compare_models.py` currently assumes exactly 3 models with one pivot pair
   sharing a tokenizer** (`PIVOT`/`OTHER_LATINCY` vs `ODYCY` in the script). Adding a
   4th model means generalizing that alignment logic — don't try to bolt a 4th model
   onto the current pairwise-diff approach without revisiting it.
5. If the addition changes or corrects an existing report's findings, note it there
   (see [reports/](reports/INDEX.md)).
