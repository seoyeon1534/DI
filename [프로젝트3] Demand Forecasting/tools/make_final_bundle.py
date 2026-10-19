"""전 과정 비교용 데이터 5개 → data/

    python tools/make_final_bundle.py

1. backtests.parquet   모든 방식 × 시드 × 확정 시점 × 원점 × 개소 × 날짜 (예측 · 분위수 · 인력 · 비용 · 날짜/주 범주)
2. metrics.csv         방식 × 축(전체 · 무료 O/X · 주범주 · 교안 구분 · 날짜유형 · 개소유형 · 개소 · 반기 · 공개일) 지표 + FVA(앞 행 대비)
3. scenarios.csv       가정 바꾸기 4개 × 방식 3개 × (23개소 합계 + 개소별)
4. recommend_2026.csv  2026-01-01 ~ 01-28 개소 × 날짜 권고 (소수 · 정수, 가정별)
5. top10_shortage.csv  인력이 가장 많이 모자란 10건 + 원인 · 출처

입력: outputs/run_v2/(MLP), outputs/run_v3/(Chronos-2), appendix/report_addons/(chronos_free_lead8, recommend_2026_4w, top10_shortage).
MASE 분모는 모든 행에 원점 전날 기준(lead 1)을 쓴다 — 확정 시점끼리 같은 잣대로 비교.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import dl  # noqa: E402
import hv  # noqa: E402
from paths import ADD, DATA, RUN_V2, RUN_V3  # noqa: E402

RUN = RUN_V2
OUT = DATA
OUT.mkdir(parents=True, exist_ok=True)

v, w, c, s = hv.load()
assert hv.check_anchors(v, w, c)["일치"].all()
cal = hv.add_free_rule(hv.make_calendar())
panel = hv.build_panel(v, cal, s)
qden = hv.mase_denominators(panel)
wt = hv.week_table()
wt["무료"] = np.where(wt["무료 개방 주"], "무료 O", "무료 X")

# ════════════════════════════════════════════════════════════
# 0. 모든 방식 모으기: 이름 → (종류, 확정, {시드: 백테스트})
# ════════════════════════════════════════════════════════════
m7 = hv.backtest(panel, hv.fc_mean7, name="1 직전 7일 평균")
m7_8 = hv.backtest(panel, hv.fc_mean7, lead=8, name="1 직전 7일 평균")
MODELS = {
    "0a 나이브": ("기준선", "전날", {0: hv.backtest(panel, hv.fc_naive, name="0a 나이브")}),
    "0b 계절 나이브": ("기준선", "전날", {0: hv.backtest(panel, hv.fc_snaive7, name="0b 계절 나이브")}),
    "1 직전 7일 평균": ("기준선", "전날", {0: m7}),
    "2 + 서비스 수준 보정": ("기준선", "전날", {0: hv.apply_multiplier(
        m7, hv.service_level_multiplier(panel, weeks=26, by="site"), by="site", name="2 + 서비스 수준 보정")}),
}
FVA_LABEL = {
    "past": "3 MLP: 과거 관람객만", "+dow": "4 MLP + 요일·정기 휴관", "+holiday_nf": "5 MLP + 공휴일(명절 아님)",
    "+myeongjeol": "6 MLP + 명절 연휴 (FVA 1차)", "+lastwed": "7 MLP + 마지막 수요일 (FVA 2차)",
    "+rain_prev": "8 MLP + 전날 큰비", "[완벽예보]+rain": "9 MLP [완벽한 예보 가정] + 당일 비",
    "(선택)+neighbor": "(선택) MLP + 이웃 궁 휴관",
}
raw = pd.read_parquet(RUN / "mlp_raw.parquet")
for vk, lab in FVA_LABEL.items():
    g = raw[raw["variant"] == vk]
    MODELS[lab] = ("MLP", "전날", {sd: hv.attach(panel, x.drop(columns=["variant", "seed"]), lab) for sd, x in g.groupby("seed")})
# Chronos-2: v3 실행(outputs/run_v3) — FVA 한 칸씩 + 보정 규칙. C1·C2·C3 는 run_v2 실행과 설정이 같다
V3 = RUN_V3
C3 = "C3 Chronos-2 + 공휴일·무료 개방"
for job, lab in [("c1_zs", "C1 Chronos-2 제로샷"), ("k1_closed", "K1 Chronos-2 + 정기 휴관"), ("c2_hol", "C2 Chronos-2 + 공휴일"),
                 ("k3_myeong", "K3 Chronos-2 + 공휴일·명절 연휴"), ("c3_free", C3),
                 ("ruleA_pos", "C3 + 보정 A 명절 연휴 안 위치"), ("ruleB_notice", "C3 + 보정 B 공지된 무료·행사 (상한)"),
                 ("ruleAB", "C3 + 보정 A + B")]:
    MODELS[lab] = ("Chronos-2", "전날", {0: pd.read_parquet(V3 / f"{job}.parquet").assign(model=lab)})
# 확정 시점: 1 · 2 · 3주 전 (lead 8 · 15 · 22) = 4주 예측의 2 · 3 · 4주차
for lead, lab in [(8, "1주 전"), (15, "2주 전"), (22, "3주 전")]:
    b7 = m7_8 if lead == 8 else hv.backtest(panel, hv.fc_mean7, lead=lead, name="1 직전 7일 평균")
    MODELS[f"1 직전 7일 평균 · {lab}"] = ("기준선", lab, {0: b7.assign(model=f"1 직전 7일 평균 · {lab}")})
    MODELS[f"2 + 서비스 수준 보정 · {lab}"] = ("기준선", lab, {0: hv.apply_multiplier(
        b7, hv.service_level_multiplier(panel, weeks=26, by="site", lead=lead), by="site", name=f"2 + 서비스 수준 보정 · {lab}")})
    src = ADD / "chronos_free_lead8.parquet" if lead == 8 else V3 / f"c3_lead{lead}.parquet"
    MODELS[f"{C3} · {lab}"] = ("Chronos-2", lab, {0: pd.read_parquet(src).assign(model=f"{C3} · {lab}")})
ORDER = list(MODELS)
MIN_STAFF = {"왕릉": 1.0}   # 팀 결정 10/15: 왕릉은 문 여는 날 하루 1명 이상 — 기준선·모형에 똑같이


def with_min(bt):
    bt = bt.copy()
    bt["qstaff"] = np.maximum(bt["qstaff"], bt["group"].map(MIN_STAFF).fillna(0) * hv.PER_STAFF)
    return bt

# ── 행마다 붙일 범주 ──
DAY = ["명절 연휴(무료)", "마지막 수요일(무료)", "공휴일(무료 아님)", "주말", "평일"]
info = panel.set_index(["site", "date"])[["is_myeongjeol", "is_last_wednesday", "is_holiday"]]


def tag(bt):
    x = bt.drop(columns=[c for c in ["is_myeongjeol", "is_last_wednesday"] if c in bt]).join(
        info.drop(columns="is_holiday"), on=["site", "date"])
    x = x.merge(wt[["origin", "무료", "주범주", "교안 구분"]], on="origin", how="left")
    x["날짜유형"] = np.select([x["is_myeongjeol"] == 1, x["is_last_wednesday"] == 1, x["is_holiday"] == 1,
                           x["weekday"].isin(["토", "일"])], DAY[:4], DAY[4])
    x["반기"] = hv.half(x)
    x["공개일"] = np.where(x["origin"] + pd.Timedelta(days=6) < dl.CHRONOS_RELEASE, "공개일 전", "공개일 후")
    x["전체"] = "전체"
    return x


# ════════════════════════════════════════════════════════════
# 1. backtests.parquet
# ════════════════════════════════════════════════════════════
KEEP = ["방식", "종류", "확정", "seed", "origin", "site", "group", "date", "weekday", "status", "y", "yhat",
        "q10", "q50", "q80", "q90", "qstaff", "staff", "need", "short", "over", "cost", "hit",
        "무료", "주범주", "교안 구분", "날짜유형", "반기", "공개일", "is_holiday", "is_free_rule", "is_myeongjeol", "is_last_wednesday"]
TAGGED = {}
frames = []
for name, (kind, lead, runs) in MODELS.items():
    TAGGED[name] = {}
    for sd, bt in runs.items():
        x = tag(bt)
        TAGGED[name][sd] = x
        o = hv.add_cost(x[x["status"] == "open"])
        x = x.join(o[["staff", "need", "short", "over", "cost", "hit"]])
        frames.append(x.assign(방식=name, 종류=kind, 확정=lead, seed=sd).reindex(columns=KEEP))
BT = pd.concat(frames, ignore_index=True)
BT.to_parquet(OUT / "backtests.parquet", index=False)
print("backtests:", BT.shape, "| 방식", BT["방식"].nunique())

# ════════════════════════════════════════════════════════════
# 2. metrics.csv (시드 평균 + 시드 범위 + FVA)
# ════════════════════════════════════════════════════════════
AXES = ["전체", "무료", "주범주", "교안 구분", "날짜유형", "group", "site", "반기", "공개일"]
AXIS_NAME = {"group": "개소유형", "site": "개소"}
COLS = ["n", "WAPE", "MASE", "포함률(80%)", "평균 구간 길이", "q0.9 초과", "적중률", "부족비용", "잉여비용", "비용"]
rows, per_seed = [], {}
for name, (kind, lead, _) in MODELS.items():
    for ax in AXES:
        per = []
        for sd, x in TAGGED[name].items():
            r = hv.summarize(x, by=ax, qden=qden).droplevel("model").reindex(columns=COLS)
            o = hv.add_cost(x[x["status"] == "open"])
            r["배치 인력(명·일)"] = o.groupby(ax)["staff"].sum()
            om = hv.add_cost(with_min(x[x["status"] == "open"]))
            r["비용 (왕릉 최소 1명)"] = om.groupby(ax)["cost"].sum()
            r["배치 인력 (왕릉 최소 1명)"] = om.groupby(ax)["staff"].sum()
            per.append(r.assign(seed=sd))
        P = pd.concat(per)
        per_seed[(name, ax)] = P
        m = P.drop(columns="seed").groupby(level=0).mean()
        if len(per) > 1:
            m["MASE 시드 범위"] = P.groupby(level=0)["MASE"].agg(lambda q: q.max() - q.min())
            m["비용 시드 범위"] = P.groupby(level=0)["비용"].agg(lambda q: q.max() - q.min())
        m = m.reset_index().rename(columns={ax: "값"})
        rows.append(m.assign(방식=name, 종류=kind, 확정=lead, 축=AXIS_NAME.get(ax, ax), 시드수=len(per)))
M = pd.concat(rows, ignore_index=True)

# FVA: 체인 안에서 앞 행 대비 비용, 5시드 모두 ↓
CHAINS = [["1 직전 7일 평균", "2 + 서비스 수준 보정", *[l for k, l in FVA_LABEL.items() if not k.startswith("(선택)")]],
          ["C1 Chronos-2 제로샷", "K1 Chronos-2 + 정기 휴관", "C2 Chronos-2 + 공휴일", "K3 Chronos-2 + 공휴일·명절 연휴", C3]]
PREV = {b: a for ch in CHAINS for a, b in zip(ch, ch[1:])}
PREV["(선택) MLP + 이웃 궁 휴관"] = "7 MLP + 마지막 수요일 (FVA 2차)"
for r_ in ["C3 + 보정 A 명절 연휴 안 위치", "C3 + 보정 B 공지된 무료·행사 (상한)", "C3 + 보정 A + B"]:
    PREV[r_] = C3          # 보정 규칙은 적용 전(C3) 대비
M["FVA 앞 행"] = M["방식"].map(PREV)
for col in ["비용", "비용 (왕릉 최소 1명)"]:
    key = M.set_index(["방식", "축", "값"])[col]
    base = M[M["방식"] == "1 직전 7일 평균"].set_index(["축", "값"])[col]
    prev = [key.get((p, a, v_)) if isinstance(p, str) else np.nan for p, a, v_ in zip(M["FVA 앞 행"], M["축"], M["값"])]
    sfx = "" if col == "비용" else " (왕릉 최소 1명)"
    M["앞 행 대비 비용" + sfx] = M[col] - pd.Series(prev, index=M.index, dtype=float)
    M["직전 7일 평균 대비 비용" + sfx] = M[col] - [base.get((a, v_), np.nan) for a, v_ in zip(M["축"], M["값"])]
down = {}
for (name, ax), P in per_seed.items():
    p = PREV.get(name)
    if p and P["seed"].nunique() > 1 and per_seed[(p, ax)]["seed"].nunique() > 1:
        a = P.set_index("seed", append=True)["비용"]
        b = per_seed[(p, ax)].set_index("seed", append=True)["비용"]
        for val, ok in (a < b.reindex(a.index)).groupby(level=0).all().items():
            down[(name, AXIS_NAME.get(ax, ax), val)] = bool(ok)
M["5시드 모두 ↓"] = [down.get(k) for k in zip(M["방식"], M["축"], M["값"])]
M["방식 순서"] = M["방식"].map({k: i for i, k in enumerate(ORDER)})
front = ["축", "값", "방식 순서", "방식", "종류", "확정", "시드수"]
M = M[front + [c for c in M.columns if c not in front]].sort_values(["축", "값", "방식 순서"])
M.to_csv(OUT / "metrics.csv", index=False, encoding="utf-8-sig", float_format="%.6g")
print("metrics:", M.shape)

# ════════════════════════════════════════════════════════════
# 3. scenarios.csv — 가정 바꾸기 (원점 전날 확정)
# ════════════════════════════════════════════════════════════
FREE_CU = 1_200_000
m7b = TAGGED["1 직전 7일 평균"][0]
C3 = TAGGED["C3 Chronos-2 + 공휴일·무료 개방"][0].copy()
C3["q_mix"] = np.where(C3["is_free_rule"] == 1, C3["q90"], C3["q80"])
mult8 = hv.service_level_multiplier(panel, weeks=26, by="site")
mult9 = hv.service_level_multiplier(panel, weeks=26, by="site", tau=0.9)
sl8 = hv.apply_multiplier(m7b, mult8, by="site")["qstaff"].to_numpy()
sl9 = hv.apply_multiplier(m7b, mult9, by="site")["qstaff"].to_numpy()
m7b = m7b.assign(sl8=sl8, sl9=sl9, sl_mix=np.where(m7b["is_free_rule"] == 1, sl9, sl8))


def scen_cost(bt, col, per=hv.PER_STAFF, cu_free=hv.C_U):
    d = bt[bt["status"] == "open"].copy()
    staff, need = d[col] / per, d["y"] / per
    cu = np.where(d["is_free_rule"] == 1, cu_free, hv.C_U)
    d["비용"] = cu * (need - staff).clip(lower=0) + hv.C_O * (staff - need).clip(lower=0)
    d["적중"] = (need <= staff).astype(float)
    d["배치 인력(명·일)"] = staff
    d["무료일 적중"] = np.where(d["is_free_rule"] == 1, d["적중"], np.nan)
    agg = lambda g: pd.Series({"비용": g["비용"].sum(), "적중률": g["적중"].mean(), "배치 인력(명·일)": g["배치 인력(명·일)"].sum(),
                               "무료 개방일 적중률": g["무료일 적중"].mean()})
    out = d.groupby("site").apply(agg, include_groups=False)
    out.loc["합계"] = agg(d)
    return out


SCEN = {  # 가정: {방식: (백테스트, 인력 열, 1명당, 무료일 C_u)}
    "기본 (τ 0.8, C_u 60만, 2,000명)": {"1 직전 7일 평균": (m7b, "yhat", 2000, hv.C_U), "2 + 서비스 수준 보정": (m7b, "sl8", 2000, hv.C_U),
                                     "C3 Chronos-2 + 공휴일·무료 개방": (C3, "q80", 2000, hv.C_U)},
    "① 서비스 수준 0.9": {"1 직전 7일 평균": (m7b, "yhat", 2000, hv.C_U), "2 + 서비스 수준 보정": (m7b, "sl9", 2000, hv.C_U),
                       "C3 Chronos-2 + 공휴일·무료 개방": (C3, "q90", 2000, hv.C_U)},
    "② 무료 개방일만 C_u 120만 (무료일 τ 0.9)": {"1 직전 7일 평균": (m7b, "yhat", 2000, FREE_CU), "2 + 서비스 수준 보정": (m7b, "sl_mix", 2000, FREE_CU),
                                           "C3 Chronos-2 + 공휴일·무료 개방": (C3, "q_mix", 2000, FREE_CU)},
    "③ 1명당 1,500명": {"1 직전 7일 평균": (m7b, "yhat", 1500, hv.C_U), "2 + 서비스 수준 보정": (m7b, "sl8", 1500, hv.C_U),
                      "C3 Chronos-2 + 공휴일·무료 개방": (C3, "q80", 1500, hv.C_U)},
}
srows = []
for sc, meth in SCEN.items():
    res = {k: scen_cost(bt, col, per, cu) for k, (bt, col, per, cu) in meth.items()}
    for k, r in res.items():
        r = r.assign(직전_7일_평균_대비_절감=res["1 직전 7일 평균"]["비용"] - r["비용"])
        srows.append(r.reset_index().rename(columns={"site": "개소", "직전_7일_평균_대비_절감": "직전 7일 평균 대비 절감"}).assign(가정=sc, 방식=k))
S = pd.concat(srows, ignore_index=True)[["가정", "방식", "개소", "비용", "직전 7일 평균 대비 절감", "적중률", "배치 인력(명·일)", "무료 개방일 적중률"]]
S.to_csv(OUT / "scenarios.csv", index=False, encoding="utf-8-sig", float_format="%.6g")
tot = S[S["개소"] == "합계"].pivot(index="가정", columns="방식", values="비용") / 1e8
print("scenarios (합계, 억):\n", tot.round(2).to_string())

# ════════════════════════════════════════════════════════════
# 4. recommend_2026.csv — 4주판 + 가정별
# ════════════════════════════════════════════════════════════
R = pd.read_csv(ADD / "recommend_2026_4w.csv", parse_dates=["date"])
op = ~R["휴관"].astype(bool)
R["① 서비스 수준 0.9 (소수)"] = np.where(op, R["q90"] / 2000, 0.0)
R["③ 1명당 1,500명 (소수)"] = np.where(op, R["q80"] / 1500, 0.0)
for c_ in ["① 서비스 수준 0.9", "③ 1명당 1,500명"]:
    R[f"{c_} (정수)"] = np.ceil(R[f"{c_} (소수)"]).astype(int)
R = R.rename(columns={"인력(소수)": "기본 (소수)", "인력(정수, 올림)": "기본 (정수)",
                      "② 무료일 q0.9 (소수)": "② 무료 개방일 C_u 120만 (소수)", "② 무료일 q0.9 (정수)": "② 무료 개방일 C_u 120만 (정수)"})
# 최종 권고 = 기본 + 왕릉 최소 1명 (정수는 날마다 올림이라 이미 1 이상 — 소수 열만 하한을 올린다)
R["최종 권고 (소수)"] = np.where(op, np.maximum(R["기본 (소수)"], R["group"].map(MIN_STAFF).fillna(0)), 0.0)
R["최종 권고 (정수)"] = np.ceil(R["최종 권고 (소수)"]).astype(int)
assert (R["최종 권고 (정수)"] == R["기본 (정수)"]).all()
R.to_csv(OUT / "recommend_2026.csv", index=False, encoding="utf-8-sig", float_format="%.4f")
print("recommend:", R.shape)

# ════════════════════════════════════════════════════════════
# 5. top10_shortage.csv — 원인 · 출처
# ════════════════════════════════════════════════════════════
CAUSE = {
    "2025-10-08": ("명절 연휴 후반", "추석 연휴 끝(당일 +2일, 대체 휴일) — 「명절 연휴 0/1」로는 연휴 안의 위치를 모름. 가을 궁중문화축전(10-08~12) 첫날과 겹침",
                   "https://v.daum.net/v/20250924090201523 ; https://www.newsis.com/view/NISX20250910_0003322928"),
    "2025-10-09": ("명절 연휴 후반", "추석 연휴 마지막 날(한글날) + 궁중문화축전 둘째 날",
                   "https://v.daum.net/v/20250924090201523 ; https://www.newsis.com/view/NISX20250910_0003322928"),
    "2025-05-04": ("행사일", "종묘대제(5월 첫째 일요일) — 정전 보수(2020~2025-04) 뒤 6년 만에 정전에서 봉행. 달력에 없음",
                   "https://mediahub.seoul.go.kr/archives/2014363"),
    "2025-11-04": ("규칙 밖 무료 개방", "2025-10-29~11-09 4대 궁·종묘·조선왕릉·세종대왕유적 무료 개방(코리아 그랜드 페스티벌) — 달력 규칙에 없음",
                   "https://v.daum.net/v/20251029122516924 ; https://mediahub.seoul.go.kr/archives/2016050"),
    "2025-11-08": ("규칙 밖 무료 개방", "2025-10-29~11-09 4대 궁·종묘·조선왕릉·세종대왕유적 무료 개방(코리아 그랜드 페스티벌) — 달력 규칙에 없음",
                   "https://v.daum.net/v/20251029122516924 ; https://mediahub.seoul.go.kr/archives/2016050"),
}
T10 = pd.read_csv(ADD / "top10_shortage.csv")
T10.insert(0, "순위", range(1, len(T10) + 1))
T10["원인 분류"] = T10["date"].map(lambda d: CAUSE[d][0])
T10["원인"] = T10["date"].map(lambda d: CAUSE[d][1])
T10["출처"] = T10["date"].map(lambda d: CAUSE[d][2])
T10.to_csv(OUT / "top10_shortage.csv", index=False, encoding="utf-8-sig", float_format="%.4f")
print(T10[["순위", "date", "site", "원인 분류"]].to_string(index=False))
