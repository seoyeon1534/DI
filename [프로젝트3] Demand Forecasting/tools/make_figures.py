"""보고서·발표용 그림 → report/figures/*.png + report/figures.pdf (outputs/run_v2 결과 사용)

python tools/make_figures.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import dl  # noqa: E402
import hv  # noqa: E402
from paths import FIG, RUN_V2  # noqa: E402

RUN = RUN_V2
FIG.mkdir(parents=True, exist_ok=True)

# ── 색: 기본 팔레트 슬롯 1~3(전쌍 검증) + 기준선 회색, 무료 O/X 는 보라/중립 ──────────
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURF = "#e1e0d9", "#c3c2b7", "#fcfcfb"
C = {
    "1 직전 7일 평균": "#898781",           # 운영팀 기준선 — 중립
    "2 + 서비스 수준 보정": "#1baf7a",      # 슬롯 3
    "MLP": "#2a78d6",                       # 슬롯 1
    "Chronos-2 + 공휴일·무료 개방": "#eb6834",  # 슬롯 2
    "Chronos-2 제로샷": "#1baf7a",          # 슬롯 3 (SL 과 같은 그림에 나오지 않게)
}
FREE_O, FREE_X = "#6250d6", "#c3c2b7"       # 무료 개방 O(강조) / X(배경)

plt.rcParams.update({
    "font.family": "Malgun Gothic", "axes.unicode_minus": False, "font.size": 10,
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
    "legend.frameon": False, "legend.fontsize": 9,
})


def save(fig, name, note=None, note_y=-0.03):
    if note:
        fig.text(0.01, note_y, note, fontsize=8, color=MUTED, ha="left", va="top")
    fig.savefig(FIG / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("saved", FIG / name)


# ════════════════════════════════════════════════════════════
# 데이터
# ════════════════════════════════════════════════════════════
v, w, c, s = hv.load()
cal = hv.add_free_rule(hv.make_calendar())
panel = hv.build_panel(v, cal, s)
qden = hv.mase_denominators(panel)
wt = hv.week_table()
wt["무료"] = np.where(wt["무료 개방 주"], "무료 O", "무료 X")
WEEK_SHORT = {k: k.split(" ", 1)[1].replace("(무료 없음)", "\n(무료 없음)") for k in hv.WEEK_CATS}
WEEK_SHORT = {k: f"{k[0]} {v_}" for k, v_ in WEEK_SHORT.items()}

m7 = hv.backtest(panel, hv.fc_mean7, name="1 직전 7일 평균")
SL = hv.apply_multiplier(m7, hv.service_level_multiplier(panel, weeks=26, by="site"), by="site",
                         name="2 + 서비스 수준 보정")
SN = hv.backtest(panel, hv.fc_snaive7, name="계절 나이브")
raw = pd.read_parquet(RUN / "mlp_raw.parquet")
FVA_LABEL = {
    "past": "3 MLP: 과거 관람객만", "+dow": "4 + 요일·정기 휴관", "+holiday_nf": "5 + 공휴일(명절 아님)",
    "+myeongjeol": "6 FVA 1차: + 명절 연휴", "+lastwed": "7 FVA 2차: + 마지막 수요일",
    "+rain_prev": "8 + 전날 큰비", "[완벽예보]+rain": "9 [완벽한 예보 가정] + 당일 비",
}
MLP = {lab: {sd: hv.attach(panel, g.drop(columns=["variant", "seed"]), "MLP")
             for sd, g in raw[raw["variant"] == vk].groupby("seed")} for vk, lab in FVA_LABEL.items()}
FINAL = "7 FVA 2차: + 마지막 수요일"
CH = {lab: pd.read_parquet(RUN / f"chronos_{t}.parquet").assign(model=lab)
      for t, lab in [("zs", "Chronos-2 제로샷"), ("hol", "Chronos-2 + 공휴일"), ("free", "Chronos-2 + 공휴일·무료 개방")]}


def tag(bt):
    return bt.merge(wt[["origin", "무료", "주범주"]], on="origin", how="left")


def cost_by(bt, key):
    d = hv.add_cost(tag(bt)[lambda x: x["status"] == "open"])
    n = d.groupby(key)["origin"].nunique()
    return d.groupby(key)["cost"].sum() / n / 1e6        # 주당 백만 원


def seed_mean(runs, fn):
    return pd.concat([fn(bt) for bt in runs.values()], axis=1).mean(axis=1)


# ════════════════════════════════════════════════════════════
# 그림 1 — 주 범주별 주당 비용
# ════════════════════════════════════════════════════════════
series = {
    "1 직전 7일 평균": cost_by(m7, "주범주"),
    "2 + 서비스 수준 보정": cost_by(SL, "주범주"),
    "MLP": seed_mean(MLP[FINAL], lambda b: cost_by(b, "주범주")),
    "Chronos-2 + 공휴일·무료 개방": cost_by(CH["Chronos-2 + 공휴일·무료 개방"], "주범주"),
}
n_w = wt["주범주"].value_counts()
fig, ax = plt.subplots(figsize=(10, 4.8))
x = np.arange(len(hv.WEEK_CATS)); bw = 0.2
for i, (k, ser) in enumerate(series.items()):
    vals = ser.reindex(hv.WEEK_CATS).to_numpy()
    bars = ax.bar(x + (i - 1.5) * bw, vals, bw * 0.9, color=C[k], label=k.split(" ", 1)[-1] if k[0].isdigit() else k)
    for b, val in zip(bars, vals):
        if i in (0, 3) or vals.max() == val:
            ax.text(b.get_x() + b.get_width() / 2, val + 1.5, f"{val:.0f}", ha="center", fontsize=7.5, color=INK2)
ax.set_xticks(x, [f"{WEEK_SHORT[k]}\n({n_w[k]}주)" for k in hv.WEEK_CATS])
for lab in ax.get_xticklabels()[:2]:
    lab.set_color(FREE_O); lab.set_fontweight("bold")
ax.set_ylabel("주당 비용 (백만 원, 23개소 × 7일)")
ax.set_title("비용은 무료 개방 주(A·B)에 몰리고, 모델이 가장 크게 줄이는 곳도 그곳이다")
ax.legend(ncol=4, loc="upper right")
save(fig, "fig1_cost_by_week_category.png",
     "원점 2025-01-01부터 52개. 보라색 라벨 = 무료 개방 주. MLP 는 시드 0~4 평균. 비용 = 60만 원 × 모자란 명 + 15만 원 × 남는 명.")

# ════════════════════════════════════════════════════════════
# 그림 2 — 교안 평가표: 무료 O / X 별 MASE (계절 나이브 기준선)
# ════════════════════════════════════════════════════════════
def mase_by(bt):
    return hv.summarize(tag(bt), by="무료", qden=qden)["MASE"].droplevel("model")

ms = {
    "1 직전 7일 평균": mase_by(m7),
    "MLP": None,
    "Chronos-2 제로샷": mase_by(CH["Chronos-2 제로샷"]),
    "Chronos-2 + 공휴일·무료 개방": mase_by(CH["Chronos-2 + 공휴일·무료 개방"]),
}
per = pd.concat([mase_by(bt) for bt in MLP[FINAL].values()], axis=1)
ms["MLP"] = per.mean(axis=1)
rng = per.max(axis=1) - per.min(axis=1)
sn = mase_by(SN)
groups = ["무료 O", "무료 X"]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
x = np.arange(2); bw = 0.19
for i, (k, ser) in enumerate(ms.items()):
    vals = ser.reindex(groups).to_numpy()
    bars = ax.bar(x + (i - 1.5) * bw, vals, bw * 0.9, color=C[k], label=k.split(" ", 1)[-1] if k[0].isdigit() else k)
    if k == "MLP":
        ax.errorbar(x + (i - 1.5) * bw, vals, yerr=rng.reindex(groups).to_numpy() / 2, fmt="none", ecolor=INK, lw=1, capsize=3)
    for b, val in zip(bars, vals):
        lift = rng.reindex(groups).to_numpy()[list(vals).index(val)] / 2 if k == "MLP" else 0
        ax.text(b.get_x() + b.get_width() / 2, val + lift + 0.03, f"{val:.2f}", ha="center", fontsize=7.5, color=INK2)
for xi, g in enumerate(groups):
    ax.hlines(sn[g], xi - 2.1 * bw, xi + 2.1 * bw, colors=INK, linestyles="--", lw=1.2)
    ax.text(xi + 2.1 * bw, sn[g] + 0.04, f"계절 나이브 {sn[g]:.2f}", va="bottom", ha="right", fontsize=8, color=INK)
ax.set_xticks(x, [f"무료 개방 주 (14주)", f"무료 없는 주 (38주)"])
ax.set_ylabel("MASE (낮을수록 좋음)")
ax.set_title("무료 개방 주에는 모든 방식의 MASE 가 크게 오르고, 그 주에서는 무료 정보를 넣은 Chronos-2 가 가장 낮다")
ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
save(fig, "fig2_mase_free_ox.png", "점선 = 같은 주의 계절 나이브(교안 기준선). MLP 의 오차 막대 = 시드 0~4 범위.", note_y=-0.08)

# ════════════════════════════════════════════════════════════
# 그림 3 — FVA: 행마다 비용, 무료 O / X 로 나눠 쌓기
# ════════════════════════════════════════════════════════════
def ox_cost(bt):
    d = hv.add_cost(tag(bt)[lambda x: x["status"] == "open"])
    return d.groupby("무료")["cost"].sum() / 1e8          # 억 원

rows = {"1 직전 7일 평균": ox_cost(m7), "2 + 서비스 수준 보정": ox_cost(SL)}
for lab, runs in MLP.items():
    rows[lab] = seed_mean(runs, ox_cost)
rows["Chronos-2 제로샷"] = ox_cost(CH["Chronos-2 제로샷"])
rows["Chronos-2 + 공휴일"] = ox_cost(CH["Chronos-2 + 공휴일"])
rows["Chronos-2 + 공휴일·무료 개방"] = ox_cost(CH["Chronos-2 + 공휴일·무료 개방"])
F = pd.DataFrame(rows).T[["무료 O", "무료 X"]]
F["합"] = F.sum(axis=1)
labels = list(F.index)
ypos = np.arange(len(labels))[::-1].astype(float)
ypos[-3:] -= 0.6                                          # Chronos 묶음 띄우기
fig, ax = plt.subplots(figsize=(10, 6.2))
ax.barh(ypos, F["무료 O"], 0.72, color=FREE_O, label="무료 개방 주")
ax.barh(ypos, F["무료 X"], 0.72, left=F["무료 O"] + 0.04, color=FREE_X, label="무료 없는 주")
prev = None
for y, lab in zip(ypos, labels):
    tot = F.loc[lab, "합"]
    txt = f"{tot:.2f}억"
    if prev is not None and not lab.startswith("Chronos-2 제로샷"):
        d_all = tot - F.loc[prev, "합"]; d_o = F.loc[lab, "무료 O"] - F.loc[prev, "무료 O"]
        txt += f"   ({d_all:+.2f} · 무료 주 {d_o:+.2f})"
    ax.text(tot + 0.12, y, txt, va="center", fontsize=8.5,
            color=INK if lab.startswith("6") or lab.endswith("무료 개방") else INK2,
            fontweight="bold" if lab.startswith("6") or lab.endswith("무료 개방") else "normal")
    prev = lab
ax.set_yticks(ypos, labels)
for t in ax.get_yticklabels():
    if t.get_text().startswith("6") or t.get_text().startswith("7") or t.get_text().endswith("무료 개방"):
        t.set_color(FREE_O); t.set_fontweight("bold")
ax.set_xlim(0, F["합"].max() * 1.45)
ax.set_xlabel("백테스트 비용 (억 원, 원점 52개 × 23개소 × 7일)")
ax.grid(axis="y", visible=False)
ax.set_title("FVA 1차(명절 연휴)가 비용을 가장 크게 줄였고, 줄어든 몫은 거의 다 무료 개방 주에서 나왔다")
ax.legend(loc="lower right")
save(fig, "fig3_fva_cost_free_ox.png",
     "괄호 = 앞 행 대비 (전체 · 무료 개방 주). MLP 행은 시드 0~4 평균. Chronos-2 세 행은 따로 묶은 참고 행(앞 행 = 바로 위 Chronos 행).")

# ════════════════════════════════════════════════════════════
# 그림 4 — 원점별 주당 비용 (무료 개방 주 음영)
# ════════════════════════════════════════════════════════════
def per_origin(bt):
    d = hv.add_cost(bt[bt["status"] == "open"])
    return d.groupby("origin")["cost"].sum() / 1e6

po = {
    "1 직전 7일 평균": per_origin(m7),
    "MLP": seed_mean(MLP[FINAL], per_origin),
    "Chronos-2 + 공휴일·무료 개방": per_origin(CH["Chronos-2 + 공휴일·무료 개방"]),
}
fig, ax = plt.subplots(figsize=(11, 4.4))
for o in wt.loc[wt["무료"] == "무료 O", "origin"]:
    ax.axvspan(o, o + pd.Timedelta(days=7), color=FREE_O, alpha=0.10, lw=0)
for k, ser in po.items():
    ax.plot(ser.index + pd.Timedelta(days=3), ser.values, color=C[k], lw=2, marker="o", ms=3.5,
            label=k.split(" ", 1)[-1] if k[0].isdigit() else k)
for d_, t_ in [("2025-01-22", "설"), ("2025-10-01", "추석"), ("2025-10-29", "규칙 밖\n무료 개방"), ("2025-04-30", "5월 연휴")]:
    ax.annotate(t_, (pd.Timestamp(d_) + pd.Timedelta(days=3), po["1 직전 7일 평균"].get(pd.Timestamp(d_), 0)),
                xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8, color=INK2)
ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%m월"))
ax.set_ylabel("원점 주 비용 (백만 원)")
ax.set_title("두 모델은 설·추석 첫 주의 급등을 크게 줄이지만, 추석 둘째 주와 규칙 밖 무료 개방은 여전히 비싸다")
ax.legend(loc="upper left")
save(fig, "fig4_cost_per_origin.png", "보라 음영 = 무료 개방 주(14주). 점 = 원점 주(7일) 비용. MLP 는 시드 0~4 평균.")

# ════════════════════════════════════════════════════════════
# 그림 5 — 효과 크기: 날짜 유형별 배수 (분석용, 2023~2025)
# ════════════════════════════════════════════════════════════
pp = panel[panel["date"] >= "2022-12-01"].copy()
pp["normal"] = (pp["status"] == "open") & (pp["is_holiday"] == 0) & (pp["is_myeongjeol"] == 0) & (pp["is_last_wednesday"] == 0)
refs = []
for site, g in pp.groupby("site"):
    g = g.set_index("date"); yn = g["y"].where(g["normal"])
    for d_ in g.index[(g["status"] == "open") & (g.index >= "2023-01-01")]:
        win = yn.loc[d_ - pd.Timedelta(days=28):d_ + pd.Timedelta(days=28)]
        win = win[win.index.dayofweek == d_.dayofweek].drop(d_, errors="ignore")
        refs.append((site, d_, g.at[d_, "y"] / win.mean()))
R = pd.DataFrame(refs, columns=["site", "date", "mult"]).merge(
    pp[["site", "date", "group", "weekday", "is_holiday", "is_myeongjeol", "is_last_wednesday",
        "is_closed_weekday", "seollal_offset", "chuseok_offset"]], on=["site", "date"])
wkday = ~R["weekday"].isin(["토", "일"])
off = R["seollal_offset"].fillna(R["chuseok_offset"])
CATS = [("명절 연휴 · 당일과 이후", True), ("명절 연휴 · 당일 전", True), ("마지막 수요일", True),
        ("평일 공휴일 (명절 아님)", False), ("정기 휴관 요일인데 연 공휴일", False), ("주말", False), ("평일", False)]
R["cat"] = np.select([
    (R["is_myeongjeol"] == 1) & (off >= 0), (R["is_myeongjeol"] == 1) & (off < 0),
    (R["is_last_wednesday"] == 1) & (R["is_holiday"] == 0),
    (R["is_holiday"] == 1) & wkday & (R["is_closed_weekday"] == 1),
    (R["is_holiday"] == 1) & wkday, ~wkday], [CATS[0][0], CATS[1][0], CATS[2][0], CATS[4][0], CATS[3][0], "주말"], "평일")
M = R.groupby(["group", "cat"])["mult"].median().unstack("group")
N = R.groupby(["group", "cat"]).size().unstack("group")
fig, axes = plt.subplots(1, 3, figsize=(12, 4.4), sharey=True)
names = [c_[0] for c_ in CATS][::-1]; free = {c_[0]: c_[1] for c_ in CATS}
for ax, grp in zip(axes, ["궁", "왕릉", "종묘"]):
    vals = M[grp].reindex(names)
    ax.barh(names, vals, 0.7, color=[FREE_O if free[n] else FREE_X for n in names])
    for n, val in zip(names, vals):
        ax.text(val + 0.08, n, f"{val:.1f}배", va="center", fontsize=8.5, color=INK if free[n] else INK2)
    ax.axvline(1, color=INK, lw=1, ls="--")
    ax.set_title(f"{grp}", loc="center"); ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(6, vals.max() * 1.25))
axes[0].set_ylabel("")
fig.suptitle("궁은 무료 개방만으로 1.8배, 명절 당일·이후 4배 — 왕릉은 무료보다 공휴일 효과가 더 크다",
             x=0.01, ha="left", fontsize=12.5, fontweight="bold", color=INK)
fig.supxlabel("그날 관람객 ÷ 앞뒤 28일 평소 같은 요일 평균 (중앙값)", fontsize=9, color=INK2)
fig.tight_layout(rect=(0, 0.02, 1, 0.95))
save(fig, "fig5_effect_size_by_daytype.png",
     "2023~2025 개방일, 분석용(미래 28일 사용). 보라 = 무료 개방일. 점선 = 평소(1배). 종묘는 표본이 적어 변동이 큼.", note_y=-0.04)

# ════════════════════════════════════════════════════════════
# 그림 6 — 교안 포함률 그림: 날마다 80% 구간 안 개소 비율
# ════════════════════════════════════════════════════════════
d = CH["Chronos-2 + 공휴일·무료 개방"]
d = d[d["status"] == "open"].assign(inside=lambda x: (x["y"] >= x["q10"]) & (x["y"] <= x["q90"]))
daily = d.groupby("date").agg(inside=("inside", "mean"), free=("is_free_rule", "max"))
fig, ax = plt.subplots(figsize=(11, 4))
nf = daily[daily["free"] == 0]; fr = daily[daily["free"] == 1]
ax.scatter(nf.index, nf["inside"], s=9, color=FREE_X, label=f"무료 아닌 날 (평균 {nf['inside'].mean():.0%})", zorder=2)
ax.scatter(fr.index, fr["inside"], s=26, color=FREE_O, label=f"무료 개방일 (평균 {fr['inside'].mean():.0%})", zorder=3,
           edgecolors=SURF, linewidths=1.2)
ax.axhline(0.8, color=INK, lw=1, ls="--"); ax.text(daily.index.max(), 0.81, "명목 80%", ha="right", fontsize=8, color=INK)
ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%m월"))
ax.set_ylim(0, 1.02); ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v_, _: f"{v_:.0%}"))
ax.set_ylabel("80% 구간 안이던 개소 비율")
ax.set_title("Chronos-2 + 공휴일·무료 개방: 무료 개방일에는 80% 구간 밖으로 벗어나는 개소가 많다")
ax.legend(loc="lower left")
save(fig, "fig6_daily_coverage.png", "점 하나 = 하루(문을 연 개소 중 실제가 q0.1~q0.9 안이던 비율). 교안 「분위수와 포함률」 그림과 같은 방식.")

# ════════════════════════════════════════════════════════════
# 그림 7 — 주 범주별 적중률 vs 목표 0.8
# ════════════════════════════════════════════════════════════
def hit_by(bt):
    return hv.summarize(tag(bt), by="주범주")["적중률"].droplevel("model")

hs = {
    "1 직전 7일 평균": hit_by(m7), "2 + 서비스 수준 보정": hit_by(SL),
    "MLP": seed_mean(MLP[FINAL], hit_by), "Chronos-2 + 공휴일·무료 개방": hit_by(CH["Chronos-2 + 공휴일·무료 개방"]),
}
fig, ax = plt.subplots(figsize=(9, 4.4))
yy = np.arange(len(hv.WEEK_CATS))[::-1]
for i, (k, ser) in enumerate(hs.items()):
    vals = ser.reindex(hv.WEEK_CATS).to_numpy()
    ax.scatter(vals, yy + (i - 1.5) * 0.14, s=70, color=C[k], edgecolors=SURF, linewidths=1.5, zorder=3,
               label=k.split(" ", 1)[-1] if k[0].isdigit() else k)
ax.axvline(0.8, color=INK, lw=1, ls="--"); ax.text(0.805, yy[-1] - 0.45, "목표 0.8 (임계비율)", fontsize=8, color=INK)
ax.set_ylim(yy[-1] - 0.6, yy[0] + 0.5)
ax.set_yticks(yy, [WEEK_SHORT[k].replace("\n", " ") for k in hv.WEEK_CATS])
for lab in ax.get_yticklabels()[:2]:
    lab.set_color(FREE_O); lab.set_fontweight("bold")
ax.set_xlim(0.3, 1.0); ax.set_xlabel("적중률 (필요 인력 ≤ 배치 인력인 개소·일 비율)")
ax.grid(axis="y", visible=False)
ax.set_title("직전 7일 평균은 무료 개방 주 적중률이 0.4대 — 두 모델은 0.73~0.80 으로 목표에 다가간다")
ax.legend(loc="upper center", ncol=4, bbox_to_anchor=(0.5, -0.13))
save(fig, "fig7_hit_rate_by_week_category.png", "적중률 = 인력이 모자라지 않은 비율. 목표는 임계비율 0.8.", note_y=-0.1)

# ════════════════════════════════════════════════════════════
# 그림 8 — 사례: 경복궁 2025 추석 (원점 10-01, 10-08)
# ════════════════════════════════════════════════════════════
site = "경복궁"; lo, hi = pd.Timestamp("2025-10-01"), pd.Timestamp("2025-10-14")
act = panel[(panel["site"] == site) & panel["date"].between(lo, hi)].set_index("date")
ch = CH["Chronos-2 + 공휴일·무료 개방"]; ch = ch[(ch["site"] == site) & ch["date"].between(lo, hi)].set_index("date")
mm = pd.concat([bt[(bt["site"] == site) & bt["date"].between(lo, hi)] for bt in MLP[FINAL].values()]).groupby("date")["q80"].mean()
mv = m7[(m7["site"] == site) & m7["date"].between(lo, hi)].set_index("date")["yhat"]
fig, ax = plt.subplots(figsize=(10, 4.4))
fr_days = act.index[act["is_free_rule"] == 1]
for d_ in fr_days:
    ax.axvspan(d_ - pd.Timedelta(hours=12), d_ + pd.Timedelta(hours=12), color=FREE_O, alpha=0.10, lw=0)
ax.fill_between(ch.index, ch["q10"], ch["q90"], color=C["Chronos-2 + 공휴일·무료 개방"], alpha=0.15, lw=0,
                label="Chronos-2 + 무료 개방 80% 구간")
ax.plot(ch.index, ch["q80"], color=C["Chronos-2 + 공휴일·무료 개방"], lw=2, label="Chronos-2 + 무료 개방 q0.8 (인력 기준)")
ax.plot(mm.index, mm.values, color=C["MLP"], lw=2, label="MLP q0.8 (시드 평균)")
ax.step(mv.index, mv.values, where="mid", color=C["1 직전 7일 평균"], lw=2, label="직전 7일 평균 (운영팀)")
ax.scatter(act.index, act["y"], color=INK, s=28, zorder=5, label="실제 (휴관일 없음)")
ax.axvline(pd.Timestamp("2025-10-07 12:00"), color=AXIS, lw=1)
ax.text(pd.Timestamp("2025-10-07 14:00"), ax.get_ylim()[1] * 0.97, "원점 10-08", fontsize=8, color=INK2, va="top")
ax.xaxis.set_major_locator(mdates.DayLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v_, _: f"{v_/1000:.0f}천"))
ax.set_ylabel("관람객 (명)")
ax.set_title("경복궁 2025 추석: 직전 7일 평균은 연휴 급증을 못 따라가고, 연휴 뒤에는 거꾸로 남는다")
ax.legend(loc="upper right", fontsize=8)
save(fig, "fig8_case_gyeongbokgung_chuseok.png",
     "보라 음영 = 무료 개방일(추석 연휴 10-03~10-09). 원점 10-01·10-08 두 주를 이어 붙임. 화요일(10-14)은 정기 휴관.")

# ════════════════════════════════════════════════════════════
# 그림 8장을 PDF 하나로 → report/figures.pdf (옛 tools/legacy/make_final_report.py 에서 옮김)
# ════════════════════════════════════════════════════════════
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

figs = sorted(FIG.glob("fig*.png"))
with PdfPages(FIG.parent / "figures.pdf") as pdf:
    for f in figs:
        img = plt.imread(f)
        h, w_ = img.shape[:2]
        fig = plt.figure(figsize=(11.69, 11.69 * h / w_))
        ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(img); ax.axis("off")
        pdf.savefig(fig, dpi=200); plt.close(fig)
print("figures.pdf (", len(figs), "장 )")
