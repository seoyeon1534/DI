"""2026 권고표 4주판 (Chronos-2 + 공휴일·무료 개방, 2026-01-01 ~ 01-28) → appendix/report_addons/recommend_2026_4w*.csv

    python tools/make_recommend_4w.py

- 2025-12-31 까지의 기록으로 28일을 한 번에 예측(prediction_length=28). 공변량은 달력이라 28일 모두 미리 안다.
- 인력(소수) = q0.8 / 2,000, 휴관일 0. 인력(정수) = 날마다 올림 후 합산 (1주판과 같은 규칙).
- k주차는 (k − 1)주 일찍 확정한 백테스트(lead 1 · 8 · 15 · 22)로 검증했다 — C3 비용 8.46 · 9.22 · 9.44 · 9.30억, 적중률 0.80 유지 (tools/run_colab_v3.py).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from paths import ADD  # noqa: E402
import dl  # noqa: E402
import hv  # noqa: E402

OUT = ADD
WEEKS = 4
v, w, c, s = hv.load()
cal = hv.add_free_rule(hv.make_calendar())
panel = hv.build_panel(v, cal, s)
COV = dl.COV_SETS["+ 공휴일·무료 개방"]

origin = pd.Timestamp("2026-01-01")
days = pd.date_range(origin, periods=7 * WEEKS)
past = panel[(panel["date"] >= dl.TRAIN_START) & (panel["date"] <= "2025-12-31")]
df = past[["site", "date", "y"] + COV].rename(columns={"site": "item_id", "date": "timestamp", "y": "target"})
cf = cal[cal["date"].isin(days)]
assert len(cf) == len(days), "2026 달력이 28일을 다 덮지 못함"
fut = pd.concat([cf.assign(item_id=r.site, is_closed_weekday=(cf["weekday"] == r.closed_weekday).astype(int))
                 for r in s.itertuples()])[["item_id", "date"] + COV].rename(columns={"date": "timestamp"})
fc = dl.chronos_pipe().predict_df(df, future_df=fut, prediction_length=len(days), quantile_levels=[0.1, 0.5, 0.8, 0.9],
                                  id_column="item_id", timestamp_column="timestamp", target="target")
fc = fc.rename(columns={"item_id": "site", "timestamp": "date"})
rec = fc[["site", "date"]].copy()
for q in ["0.1", "0.5", "0.8", "0.9"]:
    rec[f"q{int(float(q) * 100)}"] = fc[q].clip(lower=0).to_numpy()
rec = rec.merge(cf[["date", "weekday", "holiday_name", "is_holiday", "is_free_rule", "is_last_wednesday"]], on="date")
rec = rec.merge(s[["site", "group", "closed_weekday"]], on="site")
# 공휴일이 정기 휴관 요일과 겹치면 다음 날로 대체 휴관 — 1/1~1/28 의 공휴일은 1/1(목)뿐이라 겹치지 않음
assert not ((rec["is_holiday"] == 1) & (rec["weekday"] == rec["closed_weekday"])).any()
rec["휴관"] = rec["weekday"] == rec["closed_weekday"]
rec["주차"] = (rec["date"] - origin).dt.days // 7 + 1
rec["인력(소수)"] = np.where(rec["휴관"], 0.0, rec["q80"] / hv.PER_STAFF)
rec["인력(정수, 올림)"] = np.ceil(rec["인력(소수)"]).astype(int)
# 가정 ②: 무료 개방일만 C_u 120만 → τ* 0.89 → 무료일은 q0.9
rec["② 무료일 q0.9 (소수)"] = np.where(rec["휴관"], 0.0, np.where(rec["is_free_rule"] == 1, rec["q90"], rec["q80"]) / hv.PER_STAFF)
rec["② 무료일 q0.9 (정수)"] = np.ceil(rec["② 무료일 q0.9 (소수)"]).astype(int)
rec.to_csv(OUT / "recommend_2026_4w.csv", index=False, encoding="utf-8-sig")

order = list(s["site"])
# 일별 정수표 (개소 × 28일)
daily = rec.pivot(index="site", columns="date", values="인력(정수, 올림)").reindex(order)
daily.columns = [d.strftime("%m-%d") + "(" + "월화수목금토일"[d.dayofweek] + ")" for d in daily.columns]
daily["28일 합"] = daily.sum(axis=1)
daily.loc["합계"] = daily.sum()
daily.to_csv(OUT / "recommend_2026_4w_daily.csv", encoding="utf-8-sig")

# 주차별 합 (소수 / 정수 / 가정 ②)
wk = rec.groupby(["site", "주차"])[["인력(소수)", "인력(정수, 올림)", "② 무료일 q0.9 (소수)", "② 무료일 q0.9 (정수)"]].sum()
wk = wk.unstack("주차").reindex(order)
wk.columns = [f"{a} {b}주차" for a, b in wk.columns]
for a in ["인력(소수)", "인력(정수, 올림)", "② 무료일 q0.9 (소수)", "② 무료일 q0.9 (정수)"]:
    wk[f"{a} 4주 합"] = wk[[f"{a} {i}주차" for i in range(1, WEEKS + 1)]].sum(axis=1)
wk.loc["합계"] = wk.sum()
wk.round(1).to_csv(OUT / "recommend_2026_4w_weekly.csv", encoding="utf-8-sig")

# ── 화면 요약 ──
pd.set_option("display.width", 250)
print("주차:", {i: f"{days[7*(i-1)]:%m-%d} ~ {days[7*i-1]:%m-%d}" for i in range(1, WEEKS + 1)})
print("무료 개방일:", sorted(rec.loc[rec["is_free_rule"] == 1, "date"].dt.strftime("%m-%d(%a)").unique()))
show = wk[[f"인력(소수) {i}주차" for i in range(1, 5)] + ["인력(소수) 4주 합", "인력(정수, 올림) 4주 합", "② 무료일 q0.9 (소수) 4주 합"]]
print("\n■ 주차별 권고 인력 (명·일)\n", show.round(1).to_string())
lw = rec[rec["date"] == "2026-01-28"].set_index("site").reindex(order)
prev = rec[rec["date"] == "2026-01-21"].set_index("site").reindex(order)
print("\n■ 1/28(마지막 수요일) vs 1/21(평소 수요일) q0.8 배수\n", (lw["q80"] / prev["q80"]).round(2).to_string())
