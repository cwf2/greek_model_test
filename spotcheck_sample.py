"""Build a stratified human spot-check sample from the model comparison data.

Reads data/comparison/aligned_tokens.csv and tokenization_mismatches.csv
(produced by compare_models.py) and writes data/spotchecks/spotcheck_sample.csv:
a curated, reproducible sample of tokens/lines to manually adjudicate, designed
to maximize information gained per item reviewed rather than sample uniformly.
Spot-check output lives under data/spotchecks/ rather than data/comparison/
because your filled-in judgments are hand-produced and not regenerable, unlike
everything else under data/ — keep that distinction if data/ ever stops being
gitignored wholesale.

Strata (see reports/model_comparison_report.md for rationale):
  tokenization_mismatch   every line where odyCy segments differently (n=12)
  pos_all3_different      all three models disagree on POS               (30)
  pos_2v1_lg_odd          lg is the outlier vs a trf/odycy consensus       (30)
  pos_2v1_odycy_odd       odycy is the outlier vs an lg/trf consensus      (20)
  pos_2v1_trf_odd         trf is the outlier vs an lg/odycy consensus      (10)
  morph_gender_disagree   POS agrees, gender doesn't                      (15)
  morph_case_disagree     POS agrees, case doesn't                        (15)
  morph_tense_disagree    POS agrees, tense doesn't (verbs only)          (15)
  control_all_agree       all three agree, hard categories (control)      (15)
"""

import os
import random

import pandas as pd

IN_DIR = "data/comparison"
OUT_DIR = "data/spotchecks"
SEED = 20260716
N_PER_TEXT_FLOOR = 2  # try to keep every text represented in each stratum

random.seed(SEED)

os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(os.path.join(IN_DIR, "aligned_tokens.csv"), keep_default_na=False)
mismatch = pd.read_csv(os.path.join(IN_DIR, "tokenization_mismatches.csv"), keep_default_na=False)

# --- build line-context lookup (full line text) from the pivot model's tokens ---
line_text = {}
for stem_dir_file in os.listdir("data/tokens"):
    if not stem_dir_file.endswith(".grc_dep_web_lg.csv"):
        continue
    t = pd.read_csv(os.path.join("data/tokens", stem_dir_file), keep_default_na=False)
    for urn, grp in t.groupby("urn", sort=False):
        line_text[urn] = " ".join(grp["text"])


def context(urn, token_text):
    line = line_text.get(urn, "")
    return line.replace(token_text, f"[[{token_text}]]", 1) if token_text in line else line


def stratified_sample(sub, n, text_col="work"):
    """Sample n rows from sub, keeping a floor per text where possible."""
    if len(sub) <= n:
        return sub
    texts = sub[text_col].unique().tolist()
    floor_n = min(N_PER_TEXT_FLOOR, n // max(len(texts), 1))
    picked_idx = []
    for t in texts:
        idx = sub.index[sub[text_col] == t].tolist()
        k = min(floor_n, len(idx))
        picked_idx += random.sample(idx, k)
    remaining_pool = [i for i in sub.index if i not in picked_idx]
    remaining_n = max(n - len(picked_idx), 0)
    remaining_n = min(remaining_n, len(remaining_pool))
    picked_idx += random.sample(remaining_pool, remaining_n)
    return sub.loc[picked_idx]


def add_rows(rows, sub, category, fields):
    for _, r in sub.iterrows():
        row = dict(
            category=category, work=r["work"], urn=r["urn"], text=r["text"],
            context=context(r["urn"], r["text"]),
        )
        for f in fields:
            row[f"lg_{f}"] = r[f"lg_{f}"]
            row[f"trf_{f}"] = r[f"trf_{f}"]
            row[f"odycy_{f}"] = r[f"odycy_{f}"]
        row["human_judgement"] = ""
        row["notes"] = ""
        rows.append(row)


rows = []

# 1. tokenization mismatches — review all, they're few and high-value
for _, r in mismatch.iterrows():
    rows.append(dict(
        category="tokenization_mismatch", work=r["work"], urn=r["urn"],
        text="", context=f"lg/trf: {r['lg_trf_tokens']}  |  odycy: {r['odycy_tokens']}",
        lg_pos="", trf_pos="", odycy_pos="", human_judgement="", notes="",
    ))

# 2. POS: all three different
all3_diff = df[(df.lg_pos != df.trf_pos) & (df.trf_pos != df.odycy_pos) & (df.lg_pos != df.odycy_pos)]
add_rows(rows, stratified_sample(all3_diff, 30), "pos_all3_different", ["pos", "lemma"])

# 3. POS: exactly one model differs (2v1), split by odd-one-out
two_v_one = df[~((df.lg_pos == df.trf_pos) & (df.trf_pos == df.odycy_pos))]
two_v_one = two_v_one[~two_v_one.index.isin(all3_diff.index)]

lg_odd = two_v_one[two_v_one.trf_pos == two_v_one.odycy_pos]
odycy_odd = two_v_one[two_v_one.lg_pos == two_v_one.trf_pos]
trf_odd = two_v_one[two_v_one.lg_pos == two_v_one.odycy_pos]

add_rows(rows, stratified_sample(lg_odd, 30), "pos_2v1_lg_odd", ["pos", "lemma"])
add_rows(rows, stratified_sample(odycy_odd, 20), "pos_2v1_odycy_odd", ["pos", "lemma"])
add_rows(rows, stratified_sample(trf_odd, 10), "pos_2v1_trf_odd", ["pos", "lemma"])

# 4. morph disagreement conditioned on POS agreement (worst-agreeing fields)
pos_agree = df[(df.lg_pos == df.trf_pos) & (df.trf_pos == df.odycy_pos)]

gender_dis = pos_agree[
    (pos_agree.lg_gender != "") | (pos_agree.trf_gender != "") | (pos_agree.odycy_gender != "")
]
gender_dis = gender_dis[~((gender_dis.lg_gender == gender_dis.trf_gender) & (gender_dis.trf_gender == gender_dis.odycy_gender))]
add_rows(rows, stratified_sample(gender_dis, 15), "morph_gender_disagree", ["pos", "gender"])

case_dis = pos_agree[(pos_agree.lg_case != "") | (pos_agree.trf_case != "") | (pos_agree.odycy_case != "")]
case_dis = case_dis[~((case_dis.lg_case == case_dis.trf_case) & (case_dis.trf_case == case_dis.odycy_case))]
add_rows(rows, stratified_sample(case_dis, 15), "morph_case_disagree", ["pos", "case"])

tense_dis = pos_agree[(pos_agree.lg_tense != "") | (pos_agree.trf_tense != "") | (pos_agree.odycy_tense != "")]
tense_dis = tense_dis[~((tense_dis.lg_tense == tense_dis.trf_tense) & (tense_dis.trf_tense == tense_dis.odycy_tense))]
add_rows(rows, stratified_sample(tense_dis, 15), "morph_tense_disagree", ["pos", "tense", "mood", "voice"])

# 5. control: all three agree, restricted to notoriously hard categories
hard_all_agree = pos_agree[
    (pos_agree.lg_mood == "Opt") | (pos_agree.lg_number == "Dual")
    | (pos_agree.lg_pos == "PRON")
]
hard_all_agree = hard_all_agree[
    (hard_all_agree.lg_pos == hard_all_agree.trf_pos) & (hard_all_agree.trf_pos == hard_all_agree.odycy_pos)
]
add_rows(rows, stratified_sample(hard_all_agree, 15), "control_all_agree",
         ["pos", "lemma", "mood", "number", "case", "gender"])

sample = pd.DataFrame(rows)
sample.to_csv(os.path.join(OUT_DIR, "spotcheck_sample.csv"), index=False)

print("Spot-check sample written:", os.path.join(OUT_DIR, "spotcheck_sample.csv"))
print(sample["category"].value_counts())
print("Total items:", len(sample))
