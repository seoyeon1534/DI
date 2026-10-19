"""보고서 가안 보충 계산 → appendix/report_addons/*.csv (입력: outputs/run_v2/chronos_free.parquet)

1. 2026 권고표(Chronos-2 + 공휴일·무료 개방, 2026-01-01 ~ 01-07)
2. 근무표 확정 시점: 원점 전날(lead=1) vs 1주 전(lead=8)
3. 가정 바꾸기: 서비스 수준 0.9 / 무료 개방일 C_u 120만 / 1명당 1,500명
4. 개소 유형별 표 · 개소별 절감액
5. 인력이 가장 많이 모자란 10건
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from paths import ADD, RUN_V2  # noqa: E402
import dl  # noqa: E402
import hv  # noqa: E402

RUN = RUN_V2
OUT = ADD
OUT.mkdir(parents=True, exist_ok=True)
pd.set_option("display.width", 250)

v, w, c, s = hv.load()
cal = hv.add_free_rule(hv.make_calendar())
panel = hv.build_panel(v, cal, s)
qden = hv.mase_denominators(panel)
wt = hv.week_table()
wt["무료"] = np.where(wt["무료 개방 주"], "무료 O", "무료 X")
FINAL = pd.read_parquet(RUN / "chronos_free.parquet").assign(model="Chronos-2 + 공휴일·무료 개방")
m7 = hv.backtest(panel, hv.fc_mean7, name="직전 7일 평균")
SL = hv.apply_multiplier(m7, hv.service_level_multiplier(panel, weeks=26, by="site"), by="site", name="+ 서비스 수준 보정")
COV = dl.COV_SETS["+ 공휴일·무료 개방"]


def cost_frame(bt, staff_col="qstaff", cu=hv.C_U, co=hv.C_O, per=hv.PER_STAFF):
    d = bt[bt["status"] == "open"].copy()
    d["staff"] = d[staff_col] / per
    d["need"] = d["y"] / per
    d["short"] = (d["need"] - d["staff"]).clip(lower=0)
    d["over"] = (d["staff"] - d["need"]).clip(lower=0)
    cu = cu(d) if callable(cu) else cu
    d["cost"] = cu * d["short"] + co * d["over"]
    d["hit"] = (d["need"] <= d["staff"]).astype(int)
    return d


# ════════════════════════════════════════════════════════════
# 1. 2026 권고표
# ════════════════════════════════════════════════════════════
origin26 = pd.Timestamp("2026-01-01")
days26 = pd.date_range(origin26, periods=hv.HORIZON)
past = panel[(panel["date"] >= dl.TRAIN_START) & (panel["date"] <= "2025-12-31")]
df = past[["site", "date", "y"] + COV].rename(columns={"site": "item_id", "date": "timestamp", "y": "target"})
c26 = cal[cal["date"].isin(days26)]
fut = pd.concat([c26.assign(item_id=r.site, is_closed_weekday=(c26["weekday"] == r.closed_weekday).astype(int))
                 for r in s.itertuples()])[["item_id", "date"] + COV].rename(columns={"date": "timestamp"})
pipe = dl.chronos_pipe()
fc = pipe.predict_df(df, future_df=fut, prediction_length=hv.HORIZON, quantile_levels=[0.1, 0.5, 0.8, 0.9],
                     id_column="item_id", timestamp_column="timestamp", target="target")
fc = fc.rename(columns={"item_id": "site", "timestamp": "date"})
rec = fc[["site", "date"]].copy()
for q in ["0.1", "0.5", "0.8", "0.9"]:
    rec[f"q{int(float(q) * 100)}"] = fc[q].clip(lower=0).to_numpy()
rec = rec.merge(c26[["date", "weekday", "holiday_name", "is_free_rule"]], on="date")
rec = rec.merge(s[["site", "group", "closed_weekday"]], on="site")
rec["휴관"] = rec["weekday"] == rec["closed_weekday"]          # 1/1~1/7 에 공휴일이 휴관 요일과 겹치지 않음 → 대체 휴관 없음
rec["인력(소수)"] = np.where(rec["휴관"], 0.0, rec["q80"] / hv.PER_STAFF)
rec["인력(정수, 올림)"] = np.ceil(rec["인력(소수)"]).astype(int)
# 비교: 직전 7일 평균(2025-12-25 ~ 31 개방일 평균)
last7 = panel[(panel["date"] >= "2025-12-25") & (panel["date"] <= "2025-12-31")].groupby("site")["y"].mean()
rec["직전 7일 평균 인력"] = np.where(rec["휴관"], 0.0, rec["site"].map(last7) / hv.PER_STAFF)
rec.to_csv(OUT / "recommend_2026.csv", index=False, encoding="utf-8-sig")
tab = rec.pivot(index="site", columns="date", values="인력(정수, 올림)")
tab.columns = [d.strftime("%m-%d") + "(" + "월화수목금토일"[d.dayofweek] + ")" for d in tab.columns]
tab = tab.reindex(s["site"])
tab["7일 합"] = tab.sum(axis=1)
tab.loc["합계"] = tab.sum()
tab.to_csv(OUT / "recommend_2026_table.csv", encoding="utf-8-sig")
print("\n[1] 2026 권고표 (정수, 올림)\n", tab.to_string())
print("소수 합", round(rec["인력(소수)"].sum(), 1), "| 직전 7일 평균 방식 소수 합", round(rec["직전 7일 평균 인력"].sum(), 1))

# ════════════════════════════════════════════════════════════
# 2. 근무표 확정 시점: lead 1 vs 8
# ════════════════════════════════════════════════════════════
ch8 = dl.run_chronos(panel, covariates=COV, lead=8, name="Chronos-2 (1주 전 확정)")
ch8.to_parquet(OUT / "chronos_free_lead8.parquet")
m7_8 = hv.backtest(panel, hv.fc_mean7, lead=8, name="직전 7일 평균 (1주 전 확정)")
SL8 = hv.apply_multiplier(m7_8, hv.service_level_multiplier(panel, weeks=26, by="site", lead=8), by="site",
                          name="+ 서비스 수준 보정 (1주 전 확정)")
rows = []
for lab, bt in [("직전 7일 평균 · 전날", m7), ("직전 7일 평균 · 1주 전", m7_8), ("+ 보정 · 전날", SL), ("+ 보정 · 1주 전", SL8),
                ("Chronos-2 + 무료 개방 · 전날", FINAL), ("Chronos-2 + 무료 개방 · 1주 전", ch8)]:
    r = hv.summarize(bt, qden=qden).iloc[0]
    d = cost_frame(bt).merge(wt[["origin", "무료"]], on="origin")
    rows.append({"방식 · 확정": lab, "WAPE": r["WAPE"], "MASE": r["MASE"], "적중률": r["적중률"], "비용(억)": r["비용"] / 1e8,
                 "무료 O 비용(억)": d.loc[d["무료"] == "무료 O", "cost"].sum() / 1e8})
lead_tab = pd.DataFrame(rows)
lead_tab.to_csv(OUT / "lead_compare.csv", index=False, encoding="utf-8-sig")
print("\n[2] 확정 시점\n", lead_tab.round(3).to_string(index=False))

# ════════════════════════════════════════════════════════════
# 3. 가정 바꾸기
# ════════════════════════════════════════════════════════════
SL9 = hv.apply_multiplier(m7, hv.service_level_multiplier(panel, weeks=26, by="site", tau=0.9), by="site", name="+ 보정(0.9)")
free_cu = lambda d: np.where(d["is_free_rule"] == 1, 1_200_000, hv.C_U)    # 무료 개방일만 C_u 120만
FINAL_mix = FINAL.assign(q_mix=np.where(FINAL["is_free_rule"] == 1, FINAL["q90"], FINAL["q80"]))  # τ*=120/(120+15)=0.89 → q0.9
SL_mix = SL.merge(SL9[["origin", "site", "date", "qstaff"]].rename(columns={"qstaff": "q9"}), on=["origin", "site", "date"])
SL_mix["q_mix"] = np.where(SL_mix["is_free_rule"] == 1, SL_mix["q9"], SL_mix["qstaff"])
scen = []
def add(scn, lab, d):
    scen.append({"가정": scn, "방식": lab, "비용(억)": d["cost"].sum() / 1e8, "적중률": d["hit"].mean(),
                 "배치 인력(명·일)": d["staff"].sum(), "무료 개방일 적중률": d.loc[d["is_free_rule"] == 1, "hit"].mean()})
for lab, bt, col in [("직전 7일 평균", m7, "qstaff"), ("+ 서비스 수준 보정", SL, "qstaff"), ("Chronos-2 + 무료 개방", FINAL, "q80")]:
    add("기본 (τ 0.8, C_u 60만, 2,000명)", lab, cost_frame(bt, col))
for lab, bt, col in [("직전 7일 평균", m7, "qstaff"), ("+ 서비스 수준 보정(0.9 배수)", SL9, "qstaff"), ("Chronos-2 + 무료 개방 (q0.9)", FINAL, "q90")]:
    add("① 서비스 수준 0.9 (비용 가정은 기본)", lab, cost_frame(bt, col))
for lab, bt, col in [("직전 7일 평균", m7, "qstaff"), ("+ 서비스 수준 보정 (무료일 0.9)", SL_mix, "q_mix"),
                     ("Chronos-2 + 무료 개방 (무료일 q0.9)", FINAL_mix, "q_mix")]:
    add("② 무료 개방일만 C_u 120만 (τ* 0.89)", lab, cost_frame(bt, col, cu=free_cu))
for lab, bt, col in [("직전 7일 평균", m7, "qstaff"), ("+ 서비스 수준 보정", SL, "qstaff"), ("Chronos-2 + 무료 개방", FINAL, "q80")]:
    add("③ (예비) 1명당 1,500명", lab, cost_frame(bt, col, per=1500))
scen = pd.DataFrame(scen)
base = scen.groupby("가정")["비용(억)"].transform("first")
scen["직전 7일 평균 대비 절감(억)"] = base - scen["비용(억)"]
scen.to_csv(OUT / "assumption_scenarios.csv", index=False, encoding="utf-8-sig")
print("\n[3] 가정 바꾸기\n", scen.round(3).to_string(index=False))
# 2026 권고표가 가정에 따라 얼마나 바뀌나
print("2026 권고 소수 합: 기본 q0.8", round((rec["q80"] / 2000 * ~rec["휴관"]).sum(), 1),
      "| q0.9", round((rec["q90"] / 2000 * ~rec["휴관"]).sum(), 1), "| 1,500명", round((rec["q80"] / 1500 * ~rec["휴관"]).sum(), 1))

# ════════════════════════════════════════════════════════════
# 4. 개소 유형별 · 개소별 절감
# ════════════════════════════════════════════════════════════
g = []
for lab, bt in [("직전 7일 평균", m7), ("Chronos-2 + 무료 개방", FINAL)]:
    r = hv.summarize(bt, by="group", qden=qden)
    r["비용(억)"] = r["비용"] / 1e8
    g.append(r[["WAPE", "MASE", "적중률", "비용(억)"]])
grp = pd.concat(g).unstack("model")
grp.to_csv(OUT / "by_group.csv", encoding="utf-8-sig")
print("\n[4] 개소 유형별\n", grp.round(3).to_string())
site_cost = pd.DataFrame({lab: cost_frame(bt).groupby("site")["cost"].sum() / 1e6
                          for lab, bt in [("직전 7일 평균", m7), ("Chronos-2 + 무료 개방", FINAL)]})
site_cost["절감(백만)"] = site_cost["직전 7일 평균"] - site_cost["Chronos-2 + 무료 개방"]
site_cost["절감률"] = site_cost["절감(백만)"] / site_cost["직전 7일 평균"]
site_cost = site_cost.sort_values("절감(백만)", ascending=False)
site_cost.to_csv(OUT / "by_site_saving.csv", encoding="utf-8-sig")
print("\n개소별 절감 상위\n", site_cost.head(8).round(2).to_string())

# ════════════════════════════════════════════════════════════
# 5. 인력이 가장 많이 모자란 10건 (최종 모형)
# ════════════════════════════════════════════════════════════
d = cost_frame(FINAL, "q80").merge(wt[["origin", "주범주"]], on="origin")
d = d.merge(panel[["site", "date", "paid", "holiday_name", "is_myeongjeol", "is_last_wednesday", "seollal_offset",
                   "chuseok_offset"]], on=["site", "date"])
d["유료 비중"] = d["paid"] / d["y"]
top = d.sort_values("short", ascending=False).head(10)
# 같은 날 다른 개소도 무료였나(규칙 밖 무료 개방 단서, 사후 분석용)
pp = panel[panel["status"] == "open"].assign(ps=lambda x: x["paid"] / x["y"])
cnt = pp[(pp["ps"] < 0.15) & (pp["group"] != "왕릉") & (pp["is_free_rule"] == 0)].groupby("date")["site"].count()
top["같은 날 규칙 밖 무료(궁·종묘 수)"] = top["date"].map(cnt).fillna(0).astype(int)
cols = ["date", "weekday", "site", "y", "q80", "short", "cost", "주범주", "holiday_name", "is_myeongjeol",
        "seollal_offset", "chuseok_offset", "is_last_wednesday", "is_free_rule", "유료 비중", "같은 날 규칙 밖 무료(궁·종묘 수)"]
top[cols].to_csv(OUT / "top10_shortage.csv", index=False, encoding="utf-8-sig")
print("\n[5] 부족 상위 10건\n", top[cols].round(2).to_string(index=False))
print("10건 비용 합(억)", round(top["cost"].sum() / 1e8, 3), "/ 전체 부족 비용(억)", round((d["short"] * hv.C_U).sum() / 1e8, 3))
