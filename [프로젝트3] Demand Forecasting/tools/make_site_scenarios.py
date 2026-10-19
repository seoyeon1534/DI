"""가정 바꾸기를 개소별로 → appendix/report_addons/site_scenarios_cost.csv, site_scenarios_2026.csv"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from paths import ADD, RUN_V2  # noqa: E402
import hv  # noqa: E402

OUT = ADD
v, w, c, s = hv.load()
cal = hv.add_free_rule(hv.make_calendar())
panel = hv.build_panel(v, cal, s)
m7 = hv.backtest(panel, hv.fc_mean7, name="직전 7일 평균")
F = pd.read_parquet(RUN_V2 / "chronos_free.parquet")
FREE_CU = 1_200_000

def cost(bt, col, per=hv.PER_STAFF, cu_free=hv.C_U):
    d = bt[bt["status"] == "open"].copy()
    staff, need = d[col] / per, d["y"] / per
    cu = np.where(d["is_free_rule"] == 1, cu_free, hv.C_U)
    d["cost"] = cu * (need - staff).clip(lower=0) + hv.C_O * (staff - need).clip(lower=0)
    return d.groupby("site")["cost"].sum() / 1e6          # 백만 원

F["q_mix"] = np.where(F["is_free_rule"] == 1, F["q90"], F["q80"])
SCEN = {   # 가정: (직전 7일 평균 비용, 모형 비용)
    "기본": (cost(m7, "qstaff"), cost(F, "q80")),
    "① 서비스 수준 0.9": (cost(m7, "qstaff"), cost(F, "q90")),
    "② 무료 개방일 C_u 120만": (cost(m7, "qstaff", cu_free=FREE_CU), cost(F, "q_mix", cu_free=FREE_CU)),
    "③ 1명당 1,500명": (cost(m7, "qstaff", per=1500), cost(F, "q80", per=1500)),
}
order = list(s["site"])
cols = {}
for k, (b, m) in SCEN.items():
    cols[(k, "직전 7일 평균")] = b
    cols[(k, "모형")] = m
    cols[(k, "절감")] = b - m
T = pd.DataFrame(cols).reindex(order)
T.loc["합계"] = T.sum()
T.round(1).to_csv(OUT / "site_scenarios_cost.csv", encoding="utf-8-sig")
print("■ 개소별 백테스트 비용 (백만 원, 원점 52개)"); print(T.xs("절감", axis=1, level=1).round(1).to_string())

# 2026 권고 인력 (1/1~1/7 합, 명·일) — 가정별
r = pd.read_csv(OUT / "recommend_2026.csv", parse_dates=["date"])
op = ~r["휴관"].astype(bool)
r["기본"] = np.where(op, r["q80"] / 2000, 0)
r["① 서비스 수준 0.9"] = np.where(op, r["q90"] / 2000, 0)
r["② 무료 개방일 C_u 120만"] = np.where(op, np.where(r["is_free_rule"] == 1, r["q90"], r["q80"]) / 2000, 0)  # 1/1~7 엔 무료 개방일 없음 → 기본과 같음
r["③ 1명당 1,500명"] = np.where(op, r["q80"] / 1500, 0)
ks = ["기본", "① 서비스 수준 0.9", "② 무료 개방일 C_u 120만", "③ 1명당 1,500명"]
dec = r.groupby("site")[ks].sum().reindex(order)
ceil = r.assign(**{k: np.ceil(r[k]) for k in ks}).groupby("site")[ks].sum().reindex(order)
R = pd.concat({"소수": dec, "정수(올림)": ceil}, axis=1)
R.loc["합계"] = R.sum()
R.round(1).to_csv(OUT / "site_scenarios_2026.csv", encoding="utf-8-sig")
print("\n■ 2026-01-01~07 권고 인력 합 (명·일)"); print(R.round(1).to_string())
