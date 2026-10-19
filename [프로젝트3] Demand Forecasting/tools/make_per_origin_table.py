"""원점별 학습 구간 · 지표 표 (가이드 요구사항 2: 원점별 학습 구간을 날짜로, 베이스라인 3개 + 최종 모형의 원점별 지표)

    python tools/make_per_origin_table.py      # 입력: data/backtests.parquet

→ appendix/report_addons/per_origin_table.csv, per_origin_table.md (보고서 ④에 붙이는 표)
"""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from paths import ADD, DATA  # noqa: E402
OUT = ADD
M = {"0a 나이브": "나이브", "0b 계절 나이브": "계절 나이브", "1 직전 7일 평균": "직전 7일 평균", "C3 Chronos-2 + 공휴일·무료 개방": "C3"}
BT = pd.read_parquet(DATA / "backtests.parquet",
                     filters=[("방식", "in", list(M)), ("확정", "==", "전날")])
d = BT[BT["status"] == "open"].assign(ae=lambda x: (x["y"] - x["yhat"]).abs(), 방식=lambda x: x["방식"].map(M))
g = d.groupby(["origin", "방식"])
W = (g["ae"].sum() / g["y"].sum()).unstack()[list(M.values())]
C = (g["cost"].sum() / 1e6).unstack()[["직전 7일 평균", "C3"]]
info = d.drop_duplicates("origin").set_index("origin")[["무료", "주범주"]]

D = lambda t: t.strftime("%Y-%m-%d")
rows = []
for o in W.index:
    rows.append({
        "원점": D(o), "주범주": info.loc[o, "주범주"].split(" ")[0], "무료": info.loc[o, "무료"],
        "MLP 학습": f"2023-01-01 ~ {D(o - pd.Timedelta(days=57))}",
        "MLP 검증(조기 종료)": f"{D(o - pd.Timedelta(days=56))} ~ {D(o - pd.Timedelta(days=1))}",
        "Chronos-2 입력": f"2023-01-01 ~ {D(o - pd.Timedelta(days=1))}",
        "예측(평가)": f"{D(o)} ~ {D(o + pd.Timedelta(days=6))}",
        **{f"WAPE {k}": W.loc[o, k] for k in W.columns},
        "비용 직전 7일 평균(백만)": C.loc[o, "직전 7일 평균"], "비용 C3(백만)": C.loc[o, "C3"],
        "WAPE 1위": W.loc[o].idxmin(),
    })
T = pd.DataFrame(rows)
T.to_csv(OUT / "per_origin_table.csv", index=False, encoding="utf-8-sig", float_format="%.4f")

# ── 보고서용 마크다운 ──
lines = ["| 원점 | 범주 | MLP 학습 | MLP 검증 | 예측(평가) | WAPE 나이브 | 계절 나이브 | 직전 7일 평균 | **C3** | 비용 직전 7일 평균 → C3 (백만 원) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
for r in T.itertuples(index=False):
    w = [getattr(r, f"_{i}") for i in range(7, 11)]
    best = min(w)
    cells = [f"**{x:.3f}**" if x == best else f"{x:.3f}" for x in w]
    lines.append(f"| {r.원점} | {r.주범주}{' (무료)' if r.무료 == '무료 O' else ''} | ~{r[3][-10:]} | {r[4][:10][5:]} ~ {r[4][-5:]} | "
                 f"{r[6][5:10]} ~ {r[6][-5:]} | " + " | ".join(cells) + f" | {r[11]:,.1f} → {r[12]:,.1f} |")
tot = d.groupby("방식").apply(lambda x: x["ae"].sum() / x["y"].sum(), include_groups=False)
lines.append(f"| **52개 전체** | | | | | {tot['나이브']:.3f} | {tot['계절 나이브']:.3f} | {tot['직전 7일 평균']:.3f} | **{tot['C3']:.3f}** | "
             f"{C['직전 7일 평균'].sum():,.1f} → {C['C3'].sum():,.1f} |")
(OUT / "per_origin_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[:4])); print("...")
print("WAPE 1위 횟수:", T["WAPE 1위"].value_counts().to_dict())
print("C3 가 직전 7일 평균보다 WAPE 낮은 원점:", int((T["WAPE C3"] < T["WAPE 직전 7일 평균"]).sum()))
print("C3 가 직전 7일 평균보다 비용 낮은 원점:", int((T["비용 C3(백만)"] < T["비용 직전 7일 평균(백만)"]).sum()))
