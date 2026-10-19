"""O1 채점 — 17곳(덕수궁 · 저유료 왕릉 5곳 제외), 원점 52개, 전날 확정

    python tools/score_o1.py        # 먼저 tools/run_o1_ruleB_variants.py

비교: 기준선 2개 · 기존 C3 / 기존 B(23곳 입력, 17곳만 채점) · 17곳 입력 C3 / B′ / C.
출력: appendix/run_o1/o1_compare.csv
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import hv  # noqa: E402
from run_o1_ruleB_variants import EXCLUDE, NOTICE, JOBS, build  # noqa: E402

OUT = ROOT / "appendix" / "run_o1"
p = build(hv)
sites = sorted(p["site"].unique())

# 기존 백테스트(23곳 입력) — 17곳만
B = pd.read_parquet(ROOT / "data" / "backtests.parquet", filters=[("확정", "==", "전날"), ("seed", "==", 0)])
B = B[B["site"].isin(sites)]
OLD = {"1 직전 7일 평균": "1 직전 7일 평균", "2 + 서비스 수준 보정": "2 + 서비스 수준 보정",
       "C3 Chronos-2 + 공휴일·무료 개방": "C3 (23곳 입력)", "C3 + 보정 B 공지된 무료·행사 (상한)": "C3 + 보정 B 기존 (23곳 입력)"}
runs = [B[B["방식"] == k].assign(model=v) for k, v in OLD.items()]
assert all(len(r) for r in runs), [k for k, r in zip(OLD, runs) if not len(r)]
for name, (_, desc) in JOBS.items():
    runs.append(pd.read_parquet(OUT / f"{name}.parquet").assign(model=desc))
cols = ["origin", "site", "date", "model", "y", "yhat", "qstaff", "status", "is_free_rule"]
bt = pd.concat([r[cols] for r in runs], ignore_index=True)
for r in runs[4:]:
    assert len(r[r["status"] == "open"]) == len(runs[2][runs[2]["status"] == "open"]), "채점 행 수가 다름"

# 축: 무료 O/X 주 · 날짜 표시
wt = hv.week_table(hv.ORIGINS)
bt = bt.merge(wt[["origin", "무료 개방 주"]], on="origin")
flags = p[["site", "date", "is_myeongjeol", "is_last_wednesday", "extra_free_b1", "extra_free_b2"]]
bt = bt.merge(flags, on=["site", "date"], how="left")
bt["notice"] = bt["date"].between(*NOTICE)

qden = hv.mase_denominators(p)
order = list(dict.fromkeys(bt["model"]))
S = hv.summarize(bt, qden=qden).reset_index().set_index("model").reindex(order)


def sub(mask, col="비용"):
    return hv.summarize(bt[mask], by=None).reset_index().set_index("model")[col].reindex(order)


T = pd.DataFrame({
    "WAPE": S["WAPE"], "MASE": S["MASE"], "적중률": S["적중률"], "비용(억)": S["비용"] / 1e8,
    "무료 O 주 비용(억)": sub(bt["무료 개방 주"]) / 1e8,
    "무료 X 주 비용(억)": sub(~bt["무료 개방 주"]) / 1e8,
    "명절 연휴 적중률": sub(bt["is_myeongjeol"] == 1, "적중률"),
    "마지막 수요일 적중률": sub((bt["is_last_wednesday"] == 1) & (bt["is_myeongjeol"] == 0), "적중률"),
    "공지 기간 비용(억)": sub(bt["notice"]) / 1e8,
    "규칙 밖 15% 날 비용(억, 공지 기간 밖)": sub((bt["extra_free_b1"] == 1) & ~bt["notice"]) / 1e8,
})
base = T.loc["C3 (17곳)", "비용(억)"]
T["C3 (17곳) 대비(억)"] = T["비용(억)"] - base
T.index.name = "방식 (17곳 채점)"
OUT.mkdir(parents=True, exist_ok=True)
T.round(4).to_csv(OUT / "o1_compare.csv", encoding="utf-8-sig")
pd.set_option("display.width", 250)
print(f"채점 {len(sites)}곳 (제외: {', '.join(EXCLUDE)})")
print(T.round(3).to_string())
