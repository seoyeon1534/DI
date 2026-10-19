"""교안 형식 채점표 → appendix/run_v2/ (입력: outputs/run_v2/ — tools/run_day2.py)

    python tools/make_scoring_tables.py

- overall_table.csv     전체 지표 (기준선 4 · MLP FVA 2차 시드 평균 · Chronos-2 3종)
- table1_free_ox.csv    무료 개방 O / X 채점표
- table2_week_cats.csv  주 범주 A ~ E
- fva_v2.csv            MLP FVA 표 (전체 · 무료 O · 무료 X, 시드 평균 · 5시드 모두 ↓)
- per_origin_wape.csv   원점별 WAPE

옛 tools/legacy/make_scoring_nb.py(03_scoring.ipynb 생성)의 계산을 노트북 없이 옮긴 것이다.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from paths import RUN_V2, TAB_V2  # noqa: E402
import hv  # noqa: E402

RUN, OUT = RUN_V2, TAB_V2
OUT.mkdir(parents=True, exist_ok=True)

v, w, c, s = hv.load()
assert hv.check_anchors(v, w, c)["일치"].all()
cal = hv.add_free_rule(hv.make_calendar())
panel = hv.build_panel(v, cal, s)
qden = hv.mase_denominators(panel)
wt = hv.week_table()
wt["무료"] = np.where(wt["무료 개방 주"], "무료 O", "무료 X")

# ── 예측 모으기 ──
m7 = hv.backtest(panel, hv.fc_mean7, name="mean7")
mult = hv.service_level_multiplier(panel, weeks=26, by="site")      # 2024 하반기 검증 원점에서 고른 설정
BASE = {
    "계절 나이브": hv.backtest(panel, hv.fc_snaive7, name="계절 나이브"),
    "나이브": hv.backtest(panel, hv.fc_naive, name="나이브"),
    "1 직전 7일 평균": m7.assign(model="1 직전 7일 평균"),
    "2 + 서비스 수준 보정": hv.apply_multiplier(m7, mult, by="site", name="2 + 서비스 수준 보정"),
}
FVA_LABEL = {
    "past": "3 MLP: 과거 관람객만",
    "+dow": "4 + 요일·정기 휴관",
    "+holiday_nf": "5 + 공휴일(명절 아님)",
    "+myeongjeol": "6 FVA 1차: + 명절 연휴",
    "+lastwed": "7 FVA 2차: + 마지막 수요일",
    "+rain_prev": "8 + 전날 큰비",
    "[완벽예보]+rain": "9 [완벽한 예보 가정] + 당일 비",
    "(선택)+neighbor": "(선택) + 이웃 궁 휴관",
}
raw = pd.read_parquet(RUN / "mlp_raw.parquet")
MLP = {lab: {sd: hv.attach(panel, g.drop(columns=["variant", "seed"]), lab)
             for sd, g in raw[raw["variant"] == vk].groupby("seed")}
       for vk, lab in FVA_LABEL.items() if (raw["variant"] == vk).any()}
CH = {lab: pd.read_parquet(RUN / f"chronos_{tag}.parquet").assign(model=lab)
      for tag, lab in [("zs", "Chronos-2 제로샷"), ("hol", "Chronos-2 + 공휴일"), ("free", "Chronos-2 + 공휴일·무료 개방")]}
FINAL_MLP = "7 FVA 2차: + 마지막 수요일"


def tag(bt):
    return bt.merge(wt[["origin", "무료", "주범주", "교안 구분"]], on="origin", how="left")


def score(bt, by):
    """by 범주별 지표. 비용은 주당(원점당) 백만 원으로도."""
    bt = tag(bt)
    r = hv.summarize(bt, by=by, qden=qden)
    n = bt.groupby(by)["origin"].nunique()
    r["주당 비용(백만)"] = r["비용"].to_numpy() / 1e6 / n.reindex(r.index.get_level_values(0)).to_numpy()
    return r


def score_seeds(runs, by):
    """MLP: 시드별로 채점해 평균, MASE 의 시드 범위."""
    per = pd.concat([score(bt, by).assign(seed=sd) for sd, bt in runs.items()]).reset_index()
    keys = [by, "model"]
    m = per.groupby(keys).mean(numeric_only=True).drop(columns="seed")
    m["MASE 시드 범위"] = per.groupby(keys)["MASE"].agg(lambda x: x.max() - x.min())
    return m


# ── 1. 무료 O / X ──
rows = [score(BASE[k], "무료") for k in ["계절 나이브", "나이브", "1 직전 7일 평균", "2 + 서비스 수준 보정"]]
rows.append(score_seeds(MLP[FINAL_MLP], "무료"))
rows += [score(bt, "무료") for bt in CH.values()]
pd.concat(rows).to_csv(OUT / "table1_free_ox.csv", encoding="utf-8-sig")

# ── 2. 주 범주 A ~ E ──
rows = [score(BASE[k], "주범주") for k in ["계절 나이브", "1 직전 7일 평균", "2 + 서비스 수준 보정"]]
rows.append(score_seeds(MLP[FINAL_MLP], "주범주"))
rows += [score(bt, "주범주") for bt in CH.values()]
pd.concat(rows).to_csv(OUT / "table2_week_cats.csv", encoding="utf-8-sig")


# ── 3. FVA ──
def cost_cols(bt):
    d = hv.add_cost(tag(bt)[lambda x: x["status"] == "open"])
    return pd.Series({"비용 전체": d["cost"].sum(), "비용 무료 O": d.loc[d["무료"] == "무료 O", "cost"].sum(),
                      "비용 무료 X": d.loc[d["무료"] == "무료 X", "cost"].sum()})


fva_rows, seed_costs = {}, {}
for k in ["1 직전 7일 평균", "2 + 서비스 수준 보정"]:
    r = hv.summarize(BASE[k], qden=qden).iloc[0]
    fva_rows[k] = pd.concat([r[["WAPE", "MASE"]], cost_cols(BASE[k])])
for lab, runs in MLP.items():
    per = pd.DataFrame({sd: pd.concat([hv.summarize(bt, qden=qden).iloc[0][["WAPE", "MASE"]], cost_cols(bt)])
                        for sd, bt in runs.items()}).T
    seed_costs[lab] = per
    row = per.mean(); row["MASE 시드 범위"] = per["MASE"].max() - per["MASE"].min()
    fva_rows[lab] = row
FVA = pd.DataFrame(fva_rows).T
chain = [k for k in FVA.index if not k.startswith("(선택)")]
for col in ["비용 전체", "비용 무료 O", "비용 무료 X"]:
    FVA[f"앞 행 대비 {col[3:]}"] = FVA.loc[chain, col].diff()
if "(선택) + 이웃 궁 휴관" in FVA.index:
    for col in ["비용 전체", "비용 무료 O", "비용 무료 X"]:
        FVA.loc["(선택) + 이웃 궁 휴관", f"앞 행 대비 {col[3:]}"] = FVA.loc["(선택) + 이웃 궁 휴관", col] - FVA.loc[FINAL_MLP, col]
labs = [lab for lab in chain if lab in seed_costs]
prev = {labs[i]: labs[i - 1] for i in range(1, len(labs))}
prev["(선택) + 이웃 궁 휴관"] = FINAL_MLP
for col in ["비용 전체", "비용 무료 O", "비용 무료 X"]:
    FVA[f"5시드 ↓ {col[3:]}"] = pd.Series({lab: bool((seed_costs[lab][col] < seed_costs[p][col]).all())
                                          for lab, p in prev.items() if lab in seed_costs})
won = [c_ for c_ in FVA.columns if c_.startswith("비용") or c_.startswith("앞 행")]
FVA[won] = (FVA[won] / 1e6).round(1)
FVA.to_csv(OUT / "fva_v2.csv", encoding="utf-8-sig")

# ── 4. 전체 지표 ──
OV = {"나이브": BASE["나이브"], "계절 나이브": BASE["계절 나이브"], "직전 7일 평균": BASE["1 직전 7일 평균"],
      "+ 서비스 수준 보정": BASE["2 + 서비스 수준 보정"]}
rows = [hv.summarize(bt, qden=qden).reset_index(drop=True).assign(model=k) for k, bt in OV.items()]
mlp = pd.concat([hv.summarize(bt, qden=qden).reset_index(drop=True) for bt in MLP[FINAL_MLP].values()])
rows.append(mlp.mean(numeric_only=True).to_frame().T.assign(model="MLP"))
rows += [hv.summarize(bt, qden=qden).reset_index(drop=True).assign(model=k) for k, bt in CH.items()]
T = pd.concat(rows, ignore_index=True).set_index("model")
T = T[["n", "MASE", "WAPE", "적중률", "부족비용", "잉여비용", "비용", "포함률(80%)", "평균 구간 길이", "q0.9 초과"]]
T["비용(억)"], T["부족(억)"], T["잉여(억)"] = T["비용"] / 1e8, T["부족비용"] / 1e8, T["잉여비용"] / 1e8
T.to_csv(OUT / "overall_table.csv", encoding="utf-8-sig")


# ── 5. 원점별 WAPE ──
def wape_by_origin(bt):
    d = bt[bt["status"] == "open"]
    g = d.assign(ae=(d["y"] - d["yhat"]).abs()).groupby("origin")
    return g["ae"].sum() / g["y"].sum()


PO = pd.DataFrame({"나이브": wape_by_origin(BASE["나이브"]), "계절 나이브": wape_by_origin(BASE["계절 나이브"]),
                   "직전 7일 평균": wape_by_origin(BASE["1 직전 7일 평균"]),
                   "MLP(시드 평균)": pd.concat([wape_by_origin(bt) for bt in MLP[FINAL_MLP].values()], axis=1).mean(axis=1),
                   "Chronos-2 + 공휴일·무료 개방": wape_by_origin(CH["Chronos-2 + 공휴일·무료 개방"])})
PO = PO.join(wt.set_index("origin")["주범주"])
PO.index = PO.index.strftime("%Y-%m-%d")
PO.index.name = "origin"
PO.to_csv(OUT / "per_origin_wape.csv", encoding="utf-8-sig")
print("→", OUT, "| overall\n", T[["MASE", "WAPE", "적중률", "비용(억)"]].round(3).to_string())
