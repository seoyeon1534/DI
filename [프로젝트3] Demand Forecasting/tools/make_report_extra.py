"""보고서 보충 2 → appendix/report_addons/
   daytype_metrics.csv     날짜 유형(명절 연휴 · 마지막 수요일 · 공휴일 · 주말 · 평일)별 WAPE · MASE · 적중률 · 비용 (가이드 요구사항 7)
   daytype_group_final.csv 최종 후보의 날짜 유형 × 개소 유형(궁 · 종묘 · 왕릉)
   mistake4_aggregate.csv  자주 하는 실수 4: 합계로 평가하면 WAPE 가 얼마나 좋아 보이나
   mistake5_paid_flag.csv  자주 하는 실수 5: paid == 0 표시와 달력 규칙의 어긋남

    python tools/make_report_extra.py
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
OUT = ADD
v, w, c, s = hv.load()
cal = hv.add_free_rule(hv.make_calendar())
panel = hv.build_panel(v, cal, s)
qden = hv.mase_denominators(panel)

m7 = hv.backtest(panel, hv.fc_mean7, name="직전 7일 평균")
MODELS = {
    "직전 7일 평균": {0: m7},
    "+ 서비스 수준 보정": {0: hv.apply_multiplier(m7, hv.service_level_multiplier(panel, weeks=26, by="site"), by="site",
                                            name="+ 서비스 수준 보정")},
}
raw = pd.read_parquet(RUN / "mlp_raw.parquet")
g = raw[raw["variant"] == "+lastwed"]
MODELS["MLP FVA 2차 (시드 평균)"] = {sd: hv.attach(panel, x.drop(columns=["variant", "seed"]), "MLP") for sd, x in g.groupby("seed")}
MODELS["Chronos-2 + 공휴일·무료 개방"] = {0: pd.read_parquet(RUN / "chronos_free.parquet")}
FINAL = "Chronos-2 + 공휴일·무료 개방"

DAY = ["명절 연휴(무료)", "마지막 수요일(무료)", "공휴일(무료 아님)", "주말", "평일"]
info = panel.set_index(["site", "date"])[["is_myeongjeol", "is_last_wednesday", "is_holiday", "weekday"]]


def daytype(bt):
    x = bt.join(info, on=["site", "date"], rsuffix="_c")
    wk = x["weekday"].isin(["토", "일"])
    return bt.assign(날짜유형=np.select([x["is_myeongjeol"] == 1, x["is_last_wednesday"] == 1, x["is_holiday"] == 1, wk],
                                    DAY[:4], DAY[4]))


def score(runs, by):
    per = [hv.summarize(daytype(bt), by=by, qden=qden).droplevel("model") for bt in runs.values()]
    r = sum(per) / len(per)
    return r[["n", "WAPE", "MASE", "적중률", "비용"]]


# ── 1. 날짜 유형별 ──
T = pd.concat({k: score(r, "날짜유형") for k, r in MODELS.items()}, names=["방식", "날짜유형"])
T["비용"] = T["비용"] / 1e8
T = T.unstack("방식").reindex(DAY)
T.to_csv(OUT / "daytype_metrics.csv", encoding="utf-8-sig", float_format="%.4f")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print("■ 날짜 유형별 (비용 억 원)")
for m in ["n", "WAPE", "적중률", "비용"]:
    print(f"\n[{m}]\n", T[m].round(3).to_string())

G = score(MODELS[FINAL], ["날짜유형", "group"])
G["비용"] = G["비용"] / 1e6
G = G[["WAPE", "적중률", "비용"]].unstack("group").reindex(DAY)
G.to_csv(OUT / "daytype_group_final.csv", encoding="utf-8-sig", float_format="%.4f")
print("\n■ 최종 후보: 날짜 유형 × 개소 유형 (비용 백만 원)\n", G.round(3).to_string())


# ── 2. 실수 4: 합계로 평가 ──
def wapes(bt):
    d = bt[bt["status"] == "open"]
    site_day = (d["y"] - d["yhat"]).abs().sum() / d["y"].sum()
    tot = d.groupby("date")[["y", "yhat"]].sum()
    total = (tot["y"] - tot["yhat"]).abs().sum() / tot["y"].sum()
    grp = d.groupby(["date", "group"])[["y", "yhat"]].sum()
    group = (grp["y"] - grp["yhat"]).abs().sum() / grp["y"].sum()
    dc = hv.add_cost(d)
    tc = hv.add_cost(tot.reset_index().assign(qstaff=d.groupby("date")["qstaff"].sum().to_numpy()))
    return {"WAPE 개소×날짜(우리 방식)": site_day, "WAPE 개소 유형 합계×날짜": group, "WAPE 23개소 합계×날짜": total,
            "비용 개소×날짜(억)": dc["cost"].sum() / 1e8, "비용 합계×날짜(억)": tc["cost"].sum() / 1e8}


M4 = pd.DataFrame({k: wapes(MODELS[k][0]) for k in ["직전 7일 평균", FINAL]}).T
M4.to_csv(OUT / "mistake4_aggregate.csv", encoding="utf-8-sig", float_format="%.4f")
print("\n■ 실수 4: 합계로 평가\n", M4.round(3).to_string())

# ── 3. 실수 5: paid == 0 을 무료 개방일로 보면 ──
d = panel[(panel["date"] >= "2023-01-01") & (panel["status"] == "open")].copy()
d["paid0"] = (d["paid"] == 0).astype(int)
rows = []
for grp, x in [("전체", d), *d.groupby("group")]:
    cal1, p1 = x["is_free_rule"] == 1, x["paid0"] == 1
    rows.append({"개소 유형": grp, "개방일 수": len(x), "달력 무료일": int(cal1.sum()), "paid==0 인 날": int(p1.sum()),
                 "일치율": (cal1 == p1).mean(),
                 "달력 무료일 중 paid==0 비율": p1[cal1].mean(),
                 "달력 무료 아닌 날 중 paid==0 비율": p1[~cal1].mean()})
M5 = pd.DataFrame(rows)
# 달력 무료일인데 유료가 기록된 개소 (기록 방식 차이)
bys = d[d["is_free_rule"] == 1].groupby("site").agg(무료일=("paid0", "size"), paid0=("paid0", "sum"),
                                                  유료비중_중앙값=("paid", lambda p: np.nan))
bys["유료비중_중앙값"] = d[d["is_free_rule"] == 1].assign(r=lambda x: x["paid"] / x["total"]).groupby("site")["r"].median()
bys["paid==0 비율"] = bys["paid0"] / bys["무료일"]
M5.to_csv(OUT / "mistake5_paid_flag.csv", index=False, encoding="utf-8-sig", float_format="%.4f")
bys.reindex(s["site"]).to_csv(OUT / "mistake5_paid_flag_by_site.csv", encoding="utf-8-sig", float_format="%.4f")
print("\n■ 실수 5: paid == 0 vs 달력 규칙 (2023~2025 개방일)\n", M5.round(3).to_string(index=False))
print("\n달력 무료일의 개소별 paid==0 비율 · 유료 비중 중앙값\n", bys.reindex(s["site"])[["무료일", "paid==0 비율", "유료비중_중앙값"]].round(2).to_string())
