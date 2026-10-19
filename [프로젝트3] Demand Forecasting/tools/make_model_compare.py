"""모든 방식(기준선 · MLP FVA 8행 · Chronos-2 3종)을 한 표에서 비교 → appendix/report_addons/compare_all.zip (model_compare_*.csv)

    python tools/make_model_compare.py

- 원점 52개, 원점 전날 확정(lead 1), 문을 연 날만. 비용 가정은 기본(τ 0.8, C_u 60만, C_o 15만, 2,000명당 1명).
- MLP 행은 시드 0~4 를 따로 채점해 평균. `5시드 ↓` = 같은 시드끼리 앞 행과 비교해 다섯 번 모두 비용이 줄었는지.
- 앞 행 대비: 기준선 → MLP FVA 체인(3~9행), Chronos 체인(제로샷 → + 공휴일 → + 공휴일·무료 개방)은 체인 안에서만.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from paths import ADD, RUN_V2  # noqa: E402
import hv  # noqa: E402

RUN = RUN_V2
OUT = ADD / "compare_all"   # 표 6개를 여기 쓰고 끝에 compare_all.zip 으로 묶는다
OUT.mkdir(parents=True, exist_ok=True)

v, w, c, s = hv.load()
assert hv.check_anchors(v, w, c)["일치"].all()
cal = hv.add_free_rule(hv.make_calendar())
panel = hv.build_panel(v, cal, s)
qden = hv.mase_denominators(panel)
wt = hv.week_table()
wt["무료"] = np.where(wt["무료 개방 주"], "무료 O", "무료 X")

# ── 예측 모으기 (03_scoring 과 같은 이름·순서) ──
m7 = hv.backtest(panel, hv.fc_mean7, name="mean7")
mult = hv.service_level_multiplier(panel, weeks=26, by="site")
MODELS = {   # 이름: (종류, {시드: 백테스트})
    "0 계절 나이브": ("기준선", {0: hv.backtest(panel, hv.fc_snaive7, name="0 계절 나이브")}),
    "1 직전 7일 평균": ("기준선", {0: m7.assign(model="1 직전 7일 평균")}),
    "2 + 서비스 수준 보정": ("기준선", {0: hv.apply_multiplier(m7, mult, by="site", name="2 + 서비스 수준 보정")}),
}
FVA_LABEL = {
    "past": "3 MLP: 과거 관람객만",
    "+dow": "4 MLP + 요일·정기 휴관",
    "+holiday_nf": "5 MLP + 공휴일(명절 아님)",
    "+myeongjeol": "6 MLP + 명절 연휴 (FVA 1차)",
    "+lastwed": "7 MLP + 마지막 수요일 (FVA 2차)",
    "+rain_prev": "8 MLP + 전날 큰비",
    "[완벽예보]+rain": "9 MLP [완벽한 예보 가정] + 당일 비",
    "(선택)+neighbor": "(선택) MLP + 이웃 궁 휴관",
}
raw = pd.read_parquet(RUN / "mlp_raw.parquet")
for vk, lab in FVA_LABEL.items():
    g = raw[raw["variant"] == vk]
    if len(g):
        MODELS[lab] = ("MLP", {sd: hv.attach(panel, x.drop(columns=["variant", "seed"]), lab) for sd, x in g.groupby("seed")})
for tag, lab in [("zs", "C1 Chronos-2 제로샷"), ("hol", "C2 Chronos-2 + 공휴일"), ("free", "C3 Chronos-2 + 공휴일·무료 개방")]:
    MODELS[lab] = ("Chronos-2", {0: pd.read_parquet(RUN / f"chronos_{tag}.parquet").assign(model=lab)})

CHAINS = [["1 직전 7일 평균", "2 + 서비스 수준 보정", *[l for k, l in FVA_LABEL.items() if not k.startswith("(선택)")]],
          ["C1 Chronos-2 제로샷", "C2 Chronos-2 + 공휴일", "C3 Chronos-2 + 공휴일·무료 개방"]]
PREV = {b: a for ch in CHAINS for a, b in zip(ch, ch[1:]) if a in MODELS and b in MODELS}
PREV["(선택) MLP + 이웃 궁 휴관"] = "7 MLP + 마지막 수요일 (FVA 2차)"
METRICS = ["WAPE", "MASE", "적중률", "포함률(80%)", "평균 구간 길이", "q0.9 초과", "배치 인력(명·일)", "부족비용", "잉여비용", "비용"]


def tag(bt):
    return bt.merge(wt[["origin", "무료", "주범주"]], on="origin", how="left")


def score(bt, by=None):
    """by 별 지표 한 벌 (시드 하나)."""
    bt = tag(bt)
    r = hv.summarize(bt, by=by, qden=qden)
    r = r.droplevel("model") if by else r.reset_index(drop=True)
    d = hv.add_cost(bt[bt["status"] == "open"])
    r["배치 인력(명·일)"] = d.groupby(by)["staff"].sum() if by else d["staff"].sum()
    return r.reindex(columns=METRICS)


def score_model(runs, by=None):
    """시드 평균 + 시드별 표(5시드 비교용)."""
    per = {sd: score(bt, by) for sd, bt in runs.items()}
    mean = sum(per.values()) / len(per)
    return mean, per


# ── 1. 전체 + 무료 O/X 비용 (FVA 형식) ──
rows, per_seed = {}, {}
for name, (kind, runs) in MODELS.items():
    tot, per = score_model(runs)
    ox, per_ox = score_model(runs, "무료")
    r = tot.iloc[0].copy()
    r["종류"] = kind
    r["비용 무료 O"], r["비용 무료 X"] = ox.loc["무료 O", "비용"], ox.loc["무료 X", "비용"]
    r["MASE 시드 범위"] = (max(p.iloc[0]["MASE"] for p in per.values()) - min(p.iloc[0]["MASE"] for p in per.values())) if len(per) > 1 else np.nan
    rows[name] = r
    per_seed[name] = pd.DataFrame({sd: {"비용": per[sd].iloc[0]["비용"], "비용 무료 O": per_ox[sd].loc["무료 O", "비용"],
                                        "비용 무료 X": per_ox[sd].loc["무료 X", "비용"]} for sd in per}).T
T = pd.DataFrame(rows).T
base = T.loc["1 직전 7일 평균"]
for col in ["비용", "비용 무료 O", "비용 무료 X"]:
    T[f"직전 7일 평균 대비 {col}"] = T[col] - base[col]
    T[f"앞 행 대비 {col}"] = pd.Series({b: T.loc[b, col] - T.loc[a, col] for b, a in PREV.items()})
for col in ["비용", "비용 무료 O"]:   # 학습형끼리만 (기준선 → MLP 는 시드 대응이 없음)
    T[f"5시드 ↓ {col}"] = pd.Series({b: bool((per_seed[b][col] < per_seed[a][col]).all())
                                     for b, a in PREV.items() if len(per_seed[b]) > 1 and len(per_seed[a]) > 1})
T["WAPE 순위"] = T["WAPE"].astype(float).rank().astype(int)
T["비용 순위"] = T["비용"].astype(float).rank().astype(int)
won = [c for c in T.columns if "비용" in c and "↓" not in c and "순위" not in c]
T[won] = T[won].astype(float) / 1e8   # 억 원
cols = ["종류", "WAPE", "MASE", "MASE 시드 범위", "적중률", "포함률(80%)", "평균 구간 길이", "q0.9 초과", "배치 인력(명·일)",
        "부족비용", "잉여비용", "비용", "비용 무료 O", "비용 무료 X",
        "앞 행 대비 비용", "앞 행 대비 비용 무료 O", "앞 행 대비 비용 무료 X", "5시드 ↓ 비용", "5시드 ↓ 비용 무료 O",
        "직전 7일 평균 대비 비용", "직전 7일 평균 대비 비용 무료 O", "직전 7일 평균 대비 비용 무료 X", "WAPE 순위", "비용 순위"]
T = T[cols]
T.index.name = "방식"
T.to_csv(OUT / "model_compare_overall.csv", encoding="utf-8-sig", float_format="%.4f")


# ── 2. 범주별: 무료 O/X · 주범주 A~E · 개소 유형 · 개소 ──
def by_table(by, metrics, scale=None):
    parts = {}
    for name, (_, runs) in MODELS.items():
        m, _ = score_model(runs, by)
        parts[name] = m[metrics]
    out = pd.concat(parts, names=["방식", by]).unstack(by)
    if scale:
        for col in [c for c in out.columns if c[0] == "비용"]:
            out[col] = out[col] / scale
    return out.reindex(list(MODELS))


KEEP = ["WAPE", "MASE", "적중률", "포함률(80%)", "비용"]
by_table("무료", KEEP, 1e8).to_csv(OUT / "model_compare_free_ox.csv", encoding="utf-8-sig", float_format="%.4f")
by_table("주범주", KEEP, 1e8).to_csv(OUT / "model_compare_week_cats.csv", encoding="utf-8-sig", float_format="%.4f")
by_table("group", KEEP, 1e8).to_csv(OUT / "model_compare_group.csv", encoding="utf-8-sig", float_format="%.4f")
site = by_table("site", ["WAPE", "비용"], 1e6)
site = site.reindex(columns=pd.MultiIndex.from_product([["WAPE", "비용"], list(s["site"])]))
site["비용"].T.round(1).to_csv(OUT / "model_compare_site_cost.csv", encoding="utf-8-sig")      # 개소 × 방식, 백만 원
site["WAPE"].T.round(3).to_csv(OUT / "model_compare_site_wape.csv", encoding="utf-8-sig")

# ── 화면 요약 ──
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
show = T[["종류", "WAPE", "MASE", "적중률", "비용", "비용 무료 O", "비용 무료 X", "앞 행 대비 비용", "앞 행 대비 비용 무료 O",
          "5시드 ↓ 비용", "직전 7일 평균 대비 비용"]]
print("■ 전체 (비용 단위 억 원)\n", show.to_string(float_format=lambda x: f"{x:,.3f}"))
print("\n■ 개소별 비용 (백만 원) 앞부분\n", site["비용"].T.head(6).round(1).to_string())

import shutil  # noqa: E402
shutil.make_archive(str(ADD / "compare_all"), "zip", ADD, "compare_all")
shutil.rmtree(OUT)
print("→", ADD / "compare_all.zip")
