import os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'report', 'figs')
os.makedirs(OUT, exist_ok=True)

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 8
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False
plt.rcParams['axes.titlesize'] = 9
plt.rcParams['legend.fontsize'] = 7.5
W, H = 6.7, 2.5  # inches; about 170 mm wide at A4 text width
C_GREY, C_GREEN, C_BLUE, C_ORANGE, C_PURPLE = '#8a8a84', '#1fae78', '#2a7ad8', '#e96a35', '#5b4fd6'


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=220, bbox_inches='tight', pad_inches=0.08)
    plt.close(fig)
    print('saved', name)


bt = pd.read_parquet(os.path.join(BASE, 'data', 'backtests.parquet'))
bt['date'] = pd.to_datetime(bt['date'])
bt['origin'] = pd.to_datetime(bt['origin'])
fin = bt[(bt['확정'] == '전날')]
m_last = fin[fin['방식'] == '7 MLP + 마지막 수요일 (FVA 2차)']
m_c3 = fin[(fin['방식'] == 'C3 Chronos-2 + 공휴일·무료 개방') & (fin['seed'] == 0)]
m_base = fin[(fin['방식'] == '1 직전 7일 평균') & (fin['seed'] == 0)]

# ---------- fig1: weekly cost by week category ----------
t2 = pd.read_csv(os.path.join(BASE, 'appendix', 'run_v2', 'table2_week_cats.csv'), encoding='utf-8-sig')
cats = ['A 명절 연휴 주', 'B 마지막 수요일 주', 'C 평일 공휴일 주(무료 없음)', 'D 특별일 직후 주', 'E 평소 주']
cat_lab = ['A 명절 연휴\n(4주)', 'B 마지막 수요일\n(10주)', 'C 평일 공휴일\n(4주)', 'D 특별일 직후\n(13주)', 'E 평소\n(21주)']
meth = [('1 직전 7일 평균', '직전 7일 평균', C_GREY), ('2 + 서비스 수준 보정', '+ 서비스 수준 보정', C_GREEN),
        ('7 FVA 2차: + 마지막 수요일', 'MLP', C_BLUE), ('Chronos-2 + 공휴일·무료 개방', 'Chronos-2 + 공휴일·무료 개방', C_ORANGE)]
fig, ax = plt.subplots(figsize=(W, H))
x = np.arange(len(cats)); bw = 0.2
for k, (key, lab, col) in enumerate(meth):
    vals = [t2[(t2['주범주'] == c) & (t2['model'].str.contains(key, regex=False))]['주당 비용(백만)'].iloc[0] for c in cats]
    ax.bar(x + (k - 1.5) * bw, vals, bw, color=col, label=lab)
    for xi, v in zip(x + (k - 1.5) * bw, vals):
        ax.text(xi, v + 1.5, f'{v:.0f}', ha='center', va='bottom', fontsize=6)
ax.set_xticks(x); ax.set_xticklabels(cat_lab, fontsize=7)
for lbl in ax.get_xticklabels()[:2]:
    lbl.set_color(C_PURPLE); lbl.set_fontweight('bold')
ax.set_ylabel('주당 비용 (백만 원)')
ax.legend(ncol=4, frameon=False, loc='upper right')
ax.set_ylim(0, 125)
save(fig, 'fig1.png')

# ---------- fig2: MASE free O/X ----------
t1 = pd.read_csv(os.path.join(BASE, 'appendix', 'run_v2', 'table1_free_ox.csv'), encoding='utf-8-sig')
rows = [('직전 7일 평균', '1 직전 7일 평균', C_GREY), ('MLP', '7 FVA 2차', C_BLUE),
        ('Chronos-2 제로샷', 'Chronos-2 제로샷', C_GREEN), ('Chronos-2 + 공휴일·무료 개방', 'Chronos-2 + 공휴일·무료 개방', C_ORANGE)]
def mase(free, key):
    r = t1[(t1['무료'] == free) & (t1['model'].str.contains(key, regex=False))]
    return float(r['MASE'].iloc[0])
fig, ax = plt.subplots(figsize=(W, H))
groups = ['무료 개방 주 (14주)', '무료 없는 주 (38주)']
x = np.arange(2); bw = 0.19
for k, (lab, key, col) in enumerate(rows):
    vals = [mase('무료 O', key), mase('무료 X', key)]
    ax.bar(x + (k - 1.5) * bw, vals, bw, color=col, label=lab)
    for xi, v in zip(x + (k - 1.5) * bw, vals):
        ax.text(xi, v + 0.02, f'{v:.2f}', ha='center', va='bottom', fontsize=6.5)
ax.set_xticks(x); ax.set_xticklabels(groups)
from matplotlib.font_manager import FontProperties
KR = FontProperties(fname=r'C:\Windows\Fonts\malgun.ttf', size=8)
ax.set_ylabel('MASE (낮을수록 좋음)', fontproperties=KR, rotation=0, ha='left'); ax.yaxis.set_label_coords(-0.02, 1.06); ax.set_ylim(0, 2.1)
for t in ax.get_yticklabels(): t.set_fontproperties(KR)
ax.legend(ncol=4, frameon=False, loc='upper right')
save(fig, 'fig2.png')

# ---------- fig3: FVA stacked bars (억 원), 신경망과 Chronos-2를 나눠 표시 ----------
m = pd.read_csv(os.path.join(BASE, 'data', 'metrics.csv'), encoding='utf-8-sig')
fr = m[(m['축'] == '무료') & (m['확정'] == '전날')]
def _cost(key, val):
    r = fr[(fr['방식'] == key) & (fr['값'] == val)]
    return float(r['비용'].iloc[0]) / 1e8
MINUS = '-'
rows = [
    ('신경망 MLP', None, None, None, None),
    ('직전 7일 평균 (운영팀 방식)', '1 직전 7일 평균', None, False, C_GREY),
    ('+ 0.8 분위수 보정', '2 + 서비스 수준 보정', None, False, C_GREEN),
    ('+ 과거 관람객만 (달력 없음)', '3 MLP: 과거 관람객만', None, False, C_BLUE),
    ('+ 공휴일 (명절 아님)', '5 MLP + 공휴일(명절 아님)', None, False, C_BLUE),
    ('+ 명절 연휴 정보 (강조)', '6 MLP + 명절 연휴 (FVA 1차)', None, True, C_BLUE),
    ('+ 마지막 수요일 정보', '7 MLP + 마지막 수요일 (FVA 2차)', None, False, C_BLUE),
    ('Chronos-2', None, None, None, None),
    ('제로샷 (달력 정보 없음)', 'C1 Chronos-2 제로샷', None, False, C_ORANGE),
    ('+ 정기 휴관 요일', 'K1 Chronos-2 + 정기 휴관', None, False, C_ORANGE),
    ('+ 공휴일', 'C2 Chronos-2 + 공휴일', None, False, C_ORANGE),
    ('+ 명절 연휴 정보', 'K3 Chronos-2 + 공휴일·명절 연휴', None, False, C_ORANGE),
    ('+ 마지막 수요일 정보 (최종)', 'C3 Chronos-2 + 공휴일·무료 개방', None, True, C_ORANGE),
]
fig, ax = plt.subplots(figsize=(W, 3.1))
ys, labs, prev = [], [], None
y = len(rows)
for label, key, _, hl, col in rows:
    y -= 1
    if key is None:
        prev = None
        ax.text(-0.05, y, label, ha='right', va='center', fontsize=8, fontweight='bold', color='#0b2a4a', transform=ax.get_yaxis_transform())
        continue
    o = _cost(key, '무료 O'); x = _cost(key, '무료 X'); tot = o + x
    ax.barh(y, o, color=C_PURPLE, edgecolor='black' if hl else 'none', linewidth=1.2)
    ax.barh(y, x, left=o, color='#c2c1b6', edgecolor='black' if hl else 'none', linewidth=1.2)
    d = '' if prev is None else f"  ({'+' if tot - prev >= 0 else MINUS}{abs(tot - prev):.2f})"
    ax.text(tot + 0.15, y, f"{tot:.2f}억{d}", va='center', fontsize=7.5, fontweight='bold' if hl else 'normal')
    labs.append((y, label, hl)); prev = tot
for yy, label, hl in labs:
    ax.text(-0.25, yy, label, ha='right', va='center', fontsize=7.5, fontweight='bold' if hl else 'normal')
ax.set_yticks([]); ax.set_xlim(0, 15.5)
ax.set_xlabel('백테스트 비용 (억 원, 52개 원점). 괄호 = 바로 위 행과의 차이 (정보 추가 효과)', fontsize=7.5)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=C_PURPLE, label='무료 개방 주 비용'), Patch(color='#c2c1b6', label='무료 없는 주 비용')],
          frameon=False, loc='lower right', fontsize=7.5)
save(fig, 'fig3.png')

# ---------- fig4: per-origin cost ----------
def per_origin(df):
    return df.groupby('origin')['cost'].sum() / 1e8
mlp_seeds = fin[fin['방식'] == '7 MLP + 마지막 수요일 (FVA 2차)']
s_mlp = mlp_seeds.groupby(['origin', 'seed'])['cost'].sum().groupby('origin').mean() / 1e8
s_base = per_origin(fin[(fin['방식'] == '1 직전 7일 평균') & (fin['seed'] == 0)])
s_c3 = per_origin(m_c3)
fig, ax = plt.subplots(figsize=(W, H))
ax.plot(s_base.index, s_base.values, color=C_GREY, lw=1.6, marker='o', ms=2.5, label='직전 7일 평균')
ax.plot(s_mlp.index, s_mlp.values, color=C_BLUE, lw=1.6, marker='o', ms=2.5, label='MLP (5개 시드 평균)')
ax.plot(s_c3.index, s_c3.values, color=C_ORANGE, lw=1.8, marker='o', ms=2.5, label='Chronos-2 + 공휴일·무료 개방')
ax.set_ylabel('원점 주 비용 (억 원)'); ax.set_yticks(np.arange(0, 1.81, 0.4))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m월'))
ax.legend(frameon=False, ncol=3, loc='upper right')
ax.set_ylim(0, 1.9)
save(fig, 'fig4.png')

# ---------- fig5: effect size by day type ----------
groups = ['궁', '왕릉', '종묘']
types = ['명절 연휴 · 당일과 이후', '명절 연휴 · 당일 전', '마지막 수요일', '평일 공휴일 (명절 아님)', '정기 휴관 요일인데 연 공휴일', '주말', '평일']
vals = {'궁': [4.0, 2.1, 1.8, 1.6, 3.0, 0.9, 1.0], '왕릉': [2.5, 1.4, 1.5, 2.5, 4.0, 1.0, 0.9], '종묘': [9.3, 2.5, 4.3, 3.7, 2.6, 0.9, 0.9]}
fig, axes = plt.subplots(1, 3, figsize=(W, H), sharey=True)
for ax, g in zip(axes, groups):
    v = vals[g]
    cols = [C_PURPLE if i < 3 else '#c2c1b6' for i in range(len(v))]
    yy = np.arange(len(v))[::-1]
    ax.barh(yy, v, color=cols)
    for yi, vi in zip(yy, v):
        ax.text(vi + 0.1, yi, f'{vi:.1f}배', va='center', fontsize=6.5)
    ax.axvline(1, color='k', ls='--', lw=0.8)
    ax.set_title(g, fontsize=8.5, fontweight='bold')
    ax.set_xlim(0, max(v) * 1.3)
axes[0].set_yticks(np.arange(len(types))[::-1]); axes[0].set_yticklabels(types, fontsize=6.5)
save(fig, 'fig5.png')

# ---------- fig6: daily share of sites inside 80% interval ----------
d6 = m_c3[(m_c3['status'] == 'open') & (m_c3['date'] >= '2025-01-01')].copy()
d6['inside'] = (d6['y'] >= d6['q10']) & (d6['y'] <= d6['q90'])
day = d6.groupby('date').agg(share=('inside', 'mean'), free=('is_free_rule', 'max'))
fig, ax = plt.subplots(figsize=(W, H))
nf = day[day['free'] == 0]; f = day[day['free'] == 1]
ax.scatter(nf.index, nf['share'], s=7, color='#c2c1b6', label=f'무료 아닌 날 (평균 {nf["share"].mean():.0%})')
ax.scatter(f.index, f['share'], s=9, color=C_PURPLE, label=f'무료 개방일 (평균 {f["share"].mean():.0%})')
ax.axhline(0.8, color='k', ls='--', lw=0.8); ax.text(day.index[-1], 0.82, '목표 80%', ha='right', fontsize=6.5)
ax.set_ylabel('80% 구간 안 개소 비율'); ax.set_ylim(0, 1.05)
ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m월'))
ax.legend(frameon=False, ncol=2, loc='lower left')
save(fig, 'fig6.png')

# ---------- fig7: hit rate by week category ----------
fig, ax = plt.subplots(figsize=(W, H))
yy = np.arange(len(cats))[::-1]
for k, (key, lab, col) in enumerate(meth):
    vals = [t2[(t2['주범주'] == c) & (t2['model'].str.contains(key, regex=False))]['적중률'].iloc[0] for c in cats]
    ax.scatter(vals, yy + (k - 1.5) * 0.14, s=22, color=col, label=lab, zorder=3)
ax.axvline(0.8, color='k', ls='--', lw=0.8); ax.text(0.805, -0.55, '목표 0.8', fontsize=6.5)
ax.set_yticks(yy); ax.set_yticklabels(['A 명절 연휴 주', 'B 마지막 수요일 주', 'C 평일 공휴일 주', 'D 특별일 직후 주', 'E 평소 주'], fontsize=7)
ax.set_xlim(0.3, 1.0); ax.set_xlabel('적중률 (필요 인력 ≤ 배치 인력인 개소·일 비율)')
ax.legend(frameon=False, ncol=4, loc='upper center', bbox_to_anchor=(0.5, 1.2))
save(fig, 'fig7.png')

# ---------- fig8: Gyeongbokgung Chuseok 2025 ----------
g = fin[(fin['site'] == '경복궁') & (fin['date'] >= '2025-10-01') & (fin['date'] <= '2025-10-14')]
c3 = g[(g['방식'] == 'C3 Chronos-2 + 공휴일·무료 개방') & (g['seed'] == 0)].groupby('date').first()
mlp = g[(g['방식'] == '7 MLP + 마지막 수요일 (FVA 2차)')].groupby('date')['q80'].mean()
base = g[(g['방식'] == '1 직전 7일 평균') & (g['seed'] == 0)].groupby('date')['yhat'].first()
actual = c3['y']
fig, ax = plt.subplots(figsize=(W, H))
ax.fill_between(c3.index, c3['q10'] / 1e3, c3['q90'] / 1e3, color=C_ORANGE, alpha=0.15, label='Chronos-2 80% 구간')
ax.plot(c3.index, c3['q80'] / 1e3, color=C_ORANGE, lw=1.6, label='Chronos-2 0.8 분위수 (인력 기준)')
ax.plot(mlp.index, mlp.values / 1e3, color=C_BLUE, lw=1.4, label='MLP 0.8 분위수')
ax.step(base.index, base.values / 1e3, where='mid', color=C_GREY, lw=1.6, label='직전 7일 평균 (운영팀)')
ax.scatter(actual.index, actual.values / 1e3, s=12, color='k', label='경복궁 실제 관람객', zorder=4)
ax.axvspan(pd.Timestamp('2025-10-02 12:00'), pd.Timestamp('2025-10-09 12:00'), color=C_PURPLE, alpha=0.08)
ax.set_ylabel('관람객 (천 명)')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax.legend(frameon=False, ncol=3, fontsize=6.3, loc='upper right')
ax.set_ylim(0, 150)
save(fig, 'fig8.png')
print('done')
