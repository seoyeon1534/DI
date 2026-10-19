"""v3 결과 정리 → appendix/report_addons/v3_*.csv

    python tools/make_v3_results.py

1. v3_min_staff.csv      최소 인원 규칙(왕릉 개방일 하루 1명 이상)을 기준선과 모형에 똑같이 적용한 비용 · 절감 (run_v3 없이도 계산)
2. v3_fva_chronos.csv    최종 모형 FVA: C1 → + 정기 휴관 → + 공휴일 → + 명절 연휴 → + 마지막 수요일
3. v3_rules.csv          보정 규칙 A · B · A+B 적용 전후 (전체 · 무료 O/X · 날짜 유형 적중률 · 부족 10건 날짜 비용)
4. v3_lead.csv           확정 시점: 전날 · 1 · 2 · 3주 일찍 (lead 1 · 8 · 15 · 22) = 4주 예측의 1~4주차, 같은 평가 날짜
비용은 기본 가정(C_u 60만, C_o 15만, 2,000명) + 최소 인원 규칙 두 가지로 낸다. 인력은 소수(가이드).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from paths import ADD, RUN_V2, RUN_V3  # noqa: E402
import hv  # noqa: E402

V2, V3, OUT = RUN_V2, RUN_V3, ADD
MIN_STAFF = {"왕릉": 1.0}          # 팀 결정 2026-10-15: 왕릉은 문 여는 날 하루 1명 이상, 궁·종묘는 최소 없음
v, w, c, s = hv.load()
cal = hv.add_free_rule(hv.make_calendar())
panel = hv.build_panel(v, cal, s)
qden = hv.mase_denominators(panel)
wt = hv.week_table()
wt["무료"] = np.where(wt["무료 개방 주"], "무료 O", "무료 X")
DAY = ["명절 연휴(무료)", "마지막 수요일(무료)", "공휴일(무료 아님)", "주말", "평일"]
info = panel.set_index(["site", "date"])[["is_myeongjeol", "is_last_wednesday"]]


def with_min(bt):
    """최소 인원: 해당 유형 개방일의 배치 인력을 하한까지 올린다(qstaff = 인력 × 2,000)."""
    bt = bt.copy()
    floor = bt["group"].map(MIN_STAFF).fillna(0) * hv.PER_STAFF
    bt["qstaff"] = np.maximum(bt["qstaff"], floor)
    return bt


def tag(bt):
    x = bt.drop(columns=[k for k in ["is_myeongjeol", "is_last_wednesday"] if k in bt]).join(info, on=["site", "date"])
    x = x.merge(wt[["origin", "무료"]], on="origin", how="left")
    x["날짜유형"] = np.select([x["is_myeongjeol"] == 1, x["is_last_wednesday"] == 1, x["is_holiday"] == 1,
                           x["weekday"].isin(["토", "일"])], DAY[:4], DAY[4])
    return x


def row(bt):
    """전체 지표 + 무료 O/X 비용 + 날짜 유형 적중률, 비용은 기본 · 최소 인원 둘 다 (억 원)."""
    bt = tag(bt)
    r = hv.summarize(bt, qden=qden).iloc[0]
    out = {"WAPE": r["WAPE"], "MASE": r["MASE"], "적중률": r["적중률"]}
    for lab, b in [("", bt), (" (최소 인원)", with_min(bt))]:
        d = hv.add_cost(b[b["status"] == "open"])
        out["비용" + lab] = d["cost"].sum() / 1e8
        for k in ["무료 O", "무료 X"]:
            out[f"비용 {k}{lab}"] = d.loc[d["무료"] == k, "cost"].sum() / 1e8
        out["배치 인력" + lab] = d["staff"].sum()
    d = hv.add_cost(bt[bt["status"] == "open"])
    for k in DAY[:2]:
        out[f"적중률 {k}"] = d.loc[d["날짜유형"] == k, "hit"].mean()
    return pd.Series(out)


m7 = hv.backtest(panel, hv.fc_mean7, name="직전 7일 평균")
SL = hv.apply_multiplier(m7, hv.service_level_multiplier(panel, weeks=26, by="site"), by="site", name="+ 서비스 수준 보정")
C3_v2 = pd.read_parquet(V2 / "chronos_free.parquet")

# ── 1. 최소 인원 규칙 ──
T = pd.DataFrame({"직전 7일 평균": row(m7), "+ 서비스 수준 보정": row(SL), "C3 Chronos-2 + 공휴일·무료 개방": row(C3_v2)}).T
for lab in ["", " (최소 인원)"]:
    T["직전 7일 평균 대비 절감" + lab] = T.loc["직전 7일 평균", "비용" + lab] - T["비용" + lab]
T.to_csv(OUT / "v3_min_staff.csv", encoding="utf-8-sig", float_format="%.4f")
print("■ 최소 인원 규칙 (왕릉 하루 1명) — 비용 억 원\n",
      T[["비용", "비용 (최소 인원)", "직전 7일 평균 대비 절감", "직전 7일 평균 대비 절감 (최소 인원)", "배치 인력", "배치 인력 (최소 인원)"]].round(3).to_string())
a, b, c_ = (T.loc[k, "비용 (최소 인원)"] for k in ["직전 7일 평균", "+ 서비스 수준 보정", "C3 Chronos-2 + 공휴일·무료 개방"])
print(f"절감 나누기(최소 인원): 보정만 {a - b:.3f}억 + 모형 {b - c_:.3f}억 = {a - c_:.3f}억")

if not V3.exists() or not any(V3.glob("*.parquet")):
    print("\noutputs/run_v3/ 결과가 없어 1번만 계산했습니다 — tools/run_colab_v3.py 를 먼저 실행하세요.")
    sys.exit(0)
J = {f.stem: pd.read_parquet(f) for f in V3.glob("*.parquet")}
need = ["c1_zs", "k1_closed", "c2_hol", "k3_myeong", "c3_free", "ruleA_pos", "ruleB_notice", "ruleAB", "c3_lead15", "c3_lead22"]
miss = [k for k in need if k not in J]
assert not miss, f"빠진 작업: {miss}"
assert all(J[k]["origin"].nunique() == len(hv.ORIGINS) for k in need), "원점 52개가 아닌 작업이 있음"

# ── 2. FVA (최종 모형) ──
chain = [("1 직전 7일 평균", m7), ("2 + 서비스 수준 보정", SL), ("C1 Chronos-2 과거 관람객만(제로샷)", J["c1_zs"]),
         ("+ 정기 휴관 요일", J["k1_closed"]), ("+ 공휴일", J["c2_hol"]), ("+ 명절 연휴 (FVA 1차)", J["k3_myeong"]),
         ("+ 마지막 수요일 (FVA 2차) = C3", J["c3_free"])]
F = pd.DataFrame({k: row(bt) for k, bt in chain}).T
for col in ["비용", "비용 무료 O", "비용 무료 X", "비용 (최소 인원)"]:
    F[f"앞 행 대비 {col}"] = F[col].diff()
F.to_csv(OUT / "v3_fva_chronos.csv", encoding="utf-8-sig", float_format="%.4f")
print("\n■ FVA — 최종 모형 Chronos-2 (억 원)\n",
      F[["WAPE", "MASE", "적중률", "비용", "비용 무료 O", "비용 무료 X", "앞 행 대비 비용", "앞 행 대비 비용 무료 O"]].round(3).to_string())

# ── 3. 보정 규칙 전후 ──
top = pd.read_csv(OUT / "top10_shortage.csv", parse_dates=["date"])[["date", "site"]]
R = {}
for k, lab in [("c3_free", "C3 (적용 전)"), ("ruleA_pos", "C3 + 규칙 A 명절 연휴 안 위치"),
               ("ruleB_notice", "C3 + 규칙 B 공지된 무료·행사 (상한)"), ("ruleAB", "C3 + 규칙 A + B")]:
    r = row(J[k])
    d = hv.add_cost(J[k][J[k]["status"] == "open"]).merge(top, on=["date", "site"])
    r["부족 10건 비용"] = d["cost"].sum() / 1e8
    R[lab] = r
R = pd.DataFrame(R).T
for col in ["비용", "비용 무료 O", "비용 (최소 인원)", "부족 10건 비용"]:
    R[f"전후 차이 {col}"] = R[col] - R.loc["C3 (적용 전)", col]
R.to_csv(OUT / "v3_rules.csv", encoding="utf-8-sig", float_format="%.4f")
print("\n■ 보정 규칙 전후 (억 원)\n", R[["WAPE", "비용", "전후 차이 비용", "비용 무료 O", "부족 10건 비용", "전후 차이 부족 10건 비용",
                                   "적중률 명절 연휴(무료)", "적중률 마지막 수요일(무료)"]].round(3).to_string())

# ── 4. 확정 시점 ──
L = {}
for lead in [1, 8, 15, 22]:
    b7 = hv.backtest(panel, hv.fc_mean7, lead=lead, name="직전 7일 평균")
    L[("직전 7일 평균", lead)] = row(b7)
    L[("+ 서비스 수준 보정", lead)] = row(hv.apply_multiplier(b7, hv.service_level_multiplier(panel, weeks=26, by="site", lead=lead), by="site"))
L[("C3", 1)] = row(J["c3_free"])
L[("C3", 8)] = row(pd.read_parquet(OUT / "chronos_free_lead8.parquet"))
L[("C3", 15)] = row(J["c3_lead15"])
L[("C3", 22)] = row(J["c3_lead22"])
L = pd.DataFrame(L).T
LEAD_LAB = {1: "전날 확정 (lead 1) = 4주 예측의 1주차", 8: "1주 일찍 (lead 8) = 2주차",
            15: "2주 일찍 (lead 15) = 3주차", 22: "3주 일찍 (lead 22) = 4주차"}
L.index = pd.MultiIndex.from_tuples([(m, LEAD_LAB[ld]) for m, ld in L.index], names=["방식", "확정"])
L.to_csv(OUT / "v3_lead.csv", encoding="utf-8-sig", float_format="%.4f")
print("\n■ 확정 시점 (억 원)\n", L[["WAPE", "적중률", "비용", "비용 (최소 인원)"]].round(3).to_string())
