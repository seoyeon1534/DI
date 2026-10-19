"""노트북 5개 생성 + 실행 → notebooks/ (입력: data/, 먼저 tools/make_final_bundle.py)

    python tools/make_final_notebooks.py               # 5개 모두
    python tools/make_final_notebooks.py 01 05         # 일부만 (파일 이름 앞 두 자리)
"""
import sys
from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from paths import NB  # noqa: E402
NB.mkdir(parents=True, exist_ok=True)
ONLY = set(sys.argv[1:])

SETUP = """
import sys
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib import font_manager

# 묶음 폴더(real_final 또는 final) 찾기 — notebooks/ 에서 열든, 묶음 폴더나 그 위(Colab 의 /content)에서 열든 된다
HERE = Path.cwd()
CANDIDATES = [p / sub for p in [HERE, *HERE.parents] for sub in ('data', 'real_final/data', 'final/data')]
DATA = next((c for c in CANDIDATES if (c / 'metrics.csv').exists()), None)
if DATA is None:
    raise FileNotFoundError(f'data/metrics.csv 를 찾지 못했습니다 (지금 위치: {HERE}). '
                            '묶음 폴더 전체(data · notebooks ...)를 받았는지, 노트북을 notebooks/ 에서 열었는지 확인하세요.')
BASE = DATA.parent                              # 묶음 폴더
# 01 노트북만 쓰는 src/ 와 원본 데이터: 묶음 폴더 안(real_final: src/ · raw/)이 먼저, 없으면 저장소 최상위
SRC = next((p for p in [BASE / 'src', BASE.parent / 'src'] if (p / 'hv.py').exists()), None)
RAW = next((p for p in [BASE / 'raw', BASE.parent] if (p / 'anchors.json').exists()), None)
if SRC is not None:
    sys.path.insert(0, str(SRC))
print('데이터:', DATA)

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 80)
HAVE = {f.name for f in font_manager.fontManager.ttflist}
KFONT = next((f for f in ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'Noto Sans CJK KR', 'Noto Sans KR'] if f in HAVE), None)
if KFONT is None:
    print('※ 한글 폰트가 없어 그림의 한글이 네모로 보일 수 있습니다 (Colab: !apt -qq install fonts-nanum 후 런타임 다시 시작)')
plt.rcParams.update({'font.family': KFONT or 'sans-serif', 'axes.unicode_minus': False, 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False})
SITES = ['경복궁', '창덕궁', '창경궁', '덕수궁', '종묘', '동구릉', '광릉', '홍유릉', '사릉', '태릉', '정릉', '헌릉', '선릉', '의릉',
         '영휘원', '서오릉', '서삼릉', '융릉', '파주삼릉', '파주장릉', '김포장릉', '양주온릉', '세종대왕유적']   # 궁 → 종묘 → 왕릉
BLUE, ORANGE, AQUA, GRAY, VIOLET = '#2a78d6', '#eb6834', '#1baf7a', '#898781', '#6250d6'

M = pd.read_csv(DATA / 'metrics.csv')
ORDER = M.drop_duplicates('방식').sort_values('방식 순서')['방식'].tolist()

def table(axis, metric, conf='전날', models=None, scale=1):
    \"\"\"축(axis)의 값별로 방식 × 값 표. scale=1e8 이면 억 원.\"\"\"
    x = M[(M['축'] == axis) & (M['확정'] == conf)]
    t = x.pivot(index='방식', columns='값', values=metric) / scale
    idx = [m for m in ORDER if m in t.index and (models is None or m in models)]
    return t.reindex(idx)

KEY = ['1 직전 7일 평균', '2 + 서비스 수준 보정', '7 MLP + 마지막 수요일 (FVA 2차)', 'C3 Chronos-2 + 공휴일·무료 개방']
"""


def build(name, cells):
    if ONLY and name[:2] not in ONLY:
        return
    nb = nbf.v4.new_notebook(metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
    for kind, src in cells:
        nb.cells.append(nbf.v4.new_markdown_cell(src.strip()) if kind == "md" else nbf.v4.new_code_cell(src.strip()))
    NotebookClient(nb, timeout=1200, kernel_name="python3", resources={"metadata": {"path": str(NB)}}).execute()
    nbf.write(nb, NB / name)
    print("written", name)


md = lambda s: ("md", s)
code = lambda s: ("code", s)

# 01 「실수 5」 — 교안의 분석용 무료일 정의(유료 비중 15% 미만) 기준 (검토 문서 R1)
MISTAKE5_MD = """
**실수 5** — 무료 개방일을 `paid` 로 정해 예측에 쓰는 것 (2023~2025 개방일).

교안의 분석용 정의는 **유료 비중(`paid ÷ total`) 15% 미만 = 무료 개방일**이다. `paid == 0` 으로 정하면 무료일에도 후원 관람이 유료로 남는 창덕궁, 일부 무료일에 유료가 있는 경복궁에서 무료일을 놓친다. 유료 비중으로 보면 이런 날도 대부분 잡힌다.

지난 날짜를 이렇게 표시하는 것은 누수가 아니다. 다만 **예측할 날의 `paid` 는 근무표를 확정할 때 알 수 없으므로 예측 입력에는 달력 규칙(명절 연휴 · 마지막 수요일)만 쓴다.** 15% 정의는 달력 규칙 검증, 규칙 밖 무료 개방 찾기, 보정 B 의 과거 표시에 쓴다.
"""
MISTAKE5_CODE1 = """
LOW = ['양주온릉', '정릉', '영휘원', '의릉', '홍유릉']   # 평소에도 유료 비중이 낮은 왕릉
d = panel[(panel['date'] >= '2023-01-01') & (panel['status'] == 'open')].copy()
d['ps'] = d['paid'] / d['total']
d['obs15'] = d['ps'] < 0.15
d['paid0'] = d['paid'] == 0
d['구분'] = d['group'].where(~d['site'].isin(LOW), '왕릉 저유료 5곳')
rule = d['is_free_rule'] == 1
pd.DataFrame({
    '달력 무료일': d[rule].groupby('구분').size(),
    '15% 무료일': d[d['obs15']].groupby('구분').size(),
    '달력 무료일 중 paid==0': d[rule].groupby('구분')['paid0'].mean(),
    '달력 무료일 중 15% 미만': d[rule].groupby('구분')['obs15'].mean(),
    '무료 아닌 날 중 15% 미만': d[~rule].groupby('구분')['obs15'].mean(),
}).loc[['궁', '종묘', '왕릉', '왕릉 저유료 5곳']].round(3)
"""
MISTAKE5_CODE2 = """
# 궁 · 종묘: 무료일과 평소의 유료 비중 — paid==0 은 창덕궁 · 경복궁에서 무료일을 놓치지만 15% 기준은 대부분 잡는다
x = d[d['group'].isin(['궁', '종묘'])]
pd.DataFrame({
    '무료일 중 paid==0': x[x['is_free_rule'] == 1].groupby('site')['paid0'].mean(),
    '무료일 중 15% 미만': x[x['is_free_rule'] == 1].groupby('site')['obs15'].mean(),
    '무료일 유료 비중(중앙값)': x[x['is_free_rule'] == 1].groupby('site')['ps'].median(),
    '평소 유료 비중(중앙값)': x[x['is_free_rule'] == 0].groupby('site')['ps'].median(),
    '규칙 밖 15% 미만 일수': x[(x['is_free_rule'] == 0) & x['obs15']].groupby('site').size(),
}).loc[['경복궁', '창덕궁', '창경궁', '덕수궁', '종묘']].round(3)
"""
MISTAKE5_NOTE = """
- 달력 무료일은 15% 정의로도 거의 다 무료로 잡힌다. 놓치는 날은 대부분 창덕궁(무료일 유료 비중 15 ~ 19%)이다.
- **15% 정의의 한계** — ① 저유료 왕릉 5곳(양주온릉은 유료 기록이 아예 없음)은 평소에도 15% 미만이라 무료일을 구분하지 못한다. ② 덕수궁은 2023년 1 ~ 3월 등 원인 모를 저유료 날이 많아 「규칙 밖 15% 미만」의 대부분을 차지한다.
- 그 밖의 규칙 밖 15% 미만은 2024-05-15 ~ 19, 2025-10-30 ~ 11-09 처럼 **여러 개소에 같은 날 함께 나타나는 실제 무료 개방**이다. 미리 알 수 없어 C3 에는 넣지 않았고, 공지를 미리 안다고 가정한 보정 B(상한)로 따로 본다.
- `paid == 0` 기준으로 보면 「왕릉은 무료가 아닌 날에도 0 이 많다(7.9%)」처럼 보이지만, 이는 양주온릉(매일 0) 때문이다. 양주온릉을 빼면 2.5% 로 궁 · 종묘와 비슷하다.
"""

# ════════════════════════════════════════════════════════════
build("01_데이터와_베이스라인.ipynb", [
    md("""
# 01 데이터 · 전처리 · 베이스라인

궁·능 23개소 일별 관람객. 이 노트북: 검산 → 전처리 상태 → 무료 개방 규칙 → 베이스라인 3개 + 서비스 수준 보정 → 자주 하는 실수 1·5 측정.

결정 근거는 `report/report.md` 부록 A11(의사결정 기록).
"""),
    code(SETUP),
    md("## 1. 검산값 7개 (`anchors.json`)\n\n**이 노트북만** 원본 데이터(`raw/`)와 `src/` 가 필요하다(real_final 에 들어 있음). 패키지: `pip install pandas pyarrow matplotlib \"holidays==0.103\"`. 02~05 는 `data/` 만 있으면 된다."),
    code("""
if SRC is None or RAW is None:
    raise FileNotFoundError(f'01 노트북은 src/hv.py 와 원본 데이터(raw/ 의 heritage_visitors_daily.parquet · anchors.json 등)가 필요합니다 '
                            f'(찾은 위치 src={SRC}, raw={RAW}). 02~05 노트북은 data/ 만으로 실행됩니다.')
try:
    import holidays
except ImportError:
    raise ImportError('01 노트북은 holidays 패키지가 필요합니다: pip install "holidays==0.103" 후 커널 다시 시작') from None
if holidays.__version__ != '0.103':
    print(f'※ holidays {holidays.__version__} — 분석은 0.103 으로 했습니다. 2026 공휴일 표시가 다를 수 있습니다.')
import hv
v, w, c, s = hv.load(RAW)
chk = hv.check_anchors(v, w, c, data_dir=RAW)
assert chk['일치'].all()
chk
"""),
    md("## 2. 전처리 결과 — 상태 분류 (2023년 이후)\n\n휴관·결측은 `y = NaN` 으로 학습·평가에서 뺀다. 규칙 밖의 0(대체 휴관·임시 휴관)도 뺀다(**A안**)."),
    code("""
cal = hv.add_free_rule(hv.make_calendar())
panel = hv.build_panel(v, cal, s)
p23 = panel[panel['date'] >= '2023-01-01']
print(p23['status'].value_counts().to_string())
print('\\n개소 수:', p23['site'].nunique(), '| 기간:', p23['date'].min().date(), '~', p23['date'].max().date())
"""),
    md("## 3. 무료 개방 규칙 (`is_free_rule` = 명절 연휴 + 매월 마지막 수요일, 2023년 이후)"),
    code("""
fr = cal[cal['date'] >= '2023-01-01'].assign(연=lambda d: d['date'].dt.year)
fr.groupby('연')[['is_myeongjeol', 'is_last_wednesday', 'is_free_rule']].sum().rename(
    columns={'is_myeongjeol': '명절 연휴 일수', 'is_last_wednesday': '마지막 수요일', 'is_free_rule': '무료 개방일 합'})
"""),
    md("## 4. 베이스라인 3개 + 서비스 수준 보정 (원점 2025-01-01 부터 52개, 원점 전날 확정)\n\n보정은 예측값을 바꾸지 않고 인력만 늘린다 → WAPE·MASE 는 같고 적중률·비용만 바뀐다."),
    code("""
base = ['0a 나이브', '0b 계절 나이브', '1 직전 7일 평균', '2 + 서비스 수준 보정']
t = M[(M['축'] == '전체') & M['방식'].isin(base)].set_index('방식').reindex(base)
t = t[['WAPE', 'MASE', '적중률', '배치 인력(명·일)', '부족비용', '잉여비용', '비용']]
t[['부족비용', '잉여비용', '비용']] /= 1e8
t.round(3)
"""),
    md("## 5. 자주 하는 실수 1 · 5\n\n**실수 1** — 휴관일의 0 을 실제값으로 넣고 채점하면 (원점 52개). 보고서의 0.600 vs 0.480 은 가이드 수치 재현용 원점(2025-07-01 부터 26개) 값이다."),
    code("""
m7 = hv.backtest(panel, hv.fc_mean7, name='직전 7일 평균')
pd.DataFrame({'개방일만 (우리 방식)': hv.summarize(m7).iloc[0][['WAPE']],
              '휴관일 0 포함': hv.summarize(m7, open_only=False).iloc[0][['WAPE']]}).T.round(3)
"""),
    md(MISTAKE5_MD),
    code(MISTAKE5_CODE1),
    code(MISTAKE5_CODE2),
    md(MISTAKE5_NOTE),
])

# ════════════════════════════════════════════════════════════
build("02_모형비교_FVA.ipynb", [
    md("""
# 02 모형 비교와 FVA

방식 18개(기준선 4 · 글로벌 MLP FVA 8행 · Chronos-2 3종 · 1주 전 확정 3개)를 같은 원점 52개 × 23개소 × 7일로 채점.
MLP 는 시드 0~4 평균. 비용 단위 억 원. 지표 역할: WAPE 1순위 · MASE 모형 비교 · 비용 최종 결정.
"""),
    code(SETUP),
    md("## 1. 전체 비교표 (원점 전날 확정)"),
    code("""
x = M[(M['축'] == '전체') & (M['확정'] == '전날')].set_index('방식')
x = x.reindex([m for m in ORDER if m in x.index])
t = x[['종류', 'WAPE', 'MASE', 'MASE 시드 범위', '적중률', '포함률(80%)', '배치 인력(명·일)', '비용', '비용 (왕릉 최소 1명)', '직전 7일 평균 대비 비용']].copy()
t[['비용', '비용 (왕릉 최소 1명)', '직전 7일 평균 대비 비용']] /= 1e8
t['WAPE 순위'] = t['WAPE'].rank().astype(int); t['비용 순위'] = t['비용'].rank().astype(int)
t.round(3)
"""),
    md("## 2. FVA — 글로벌 MLP (정보를 하나씩 더함)\n\n행마다 앞 행 대비 비용. `5시드 모두 ↓` 가 True 여야 시드 운이 아닌 개선으로 본다."),
    code("""
mlp = ['1 직전 7일 평균', '2 + 서비스 수준 보정'] + [m for m in ORDER if 'MLP' in m]
rows = []
for ax_val in [('전체', '전체'), ('무료', '무료 O'), ('무료', '무료 X')]:
    y = M[(M['축'] == ax_val[0]) & (M['값'] == ax_val[1])].set_index('방식').reindex(mlp)
    rows.append(pd.DataFrame({f'비용 {ax_val[1]}': y['비용'] / 1e8, f'앞 행 대비 {ax_val[1]}': y['앞 행 대비 비용'] / 1e8,
                              f'5시드↓ {ax_val[1]}': y['5시드 모두 ↓']}))
fva = pd.concat(rows, axis=1)
fva.insert(0, 'WAPE', M[(M['축'] == '전체')].set_index('방식').reindex(mlp)['WAPE'])
fva.round(3)
"""),
    md("## 3. FVA — 최종 모형 Chronos-2 (정보를 한 칸씩, 가이드 요구사항 6)\n\nC1 과거만(제로샷) → K1 + 정기 휴관 → C2 + 공휴일 → K3 + 명절 연휴 (FVA 1차) → C3 + 마지막 수요일 (FVA 2차). Colab T4 실행. 시드가 없는 모형이라 `5시드 ↓` 대신 무료 O/X 로 어디서 줄었는지 본다."),
    code("""
ch = ['1 직전 7일 평균', '2 + 서비스 수준 보정', 'C1 Chronos-2 제로샷', 'K1 Chronos-2 + 정기 휴관', 'C2 Chronos-2 + 공휴일',
      'K3 Chronos-2 + 공휴일·명절 연휴', 'C3 Chronos-2 + 공휴일·무료 개방']
y = M[(M['축'] == '전체') & (M['확정'] == '전날')].set_index('방식').reindex(ch)
f = pd.concat([y[['WAPE', 'MASE', '적중률']], (y[['비용', '앞 행 대비 비용']] / 1e8),
               table('무료', '비용', models=ch, scale=1e8).add_prefix('비용 '),
               table('무료', '앞 행 대비 비용', models=ch, scale=1e8).add_prefix('앞 행 대비 ')], axis=1)
f.round(3)
"""),
    md("## 4. 보정 규칙 전후 (가이드 요구사항 7)\n\nA = 명절 연휴 안 위치(당일 전 / 당일·다음날 / 당일 +2일 이후), B = 공지된 규칙 밖 무료·행사(공지가 확정 전에 나왔다고 가정한 **상한**). 부족 10건 날짜의 비용도 같이 본다."),
    code("""
rules = ['C3 Chronos-2 + 공휴일·무료 개방', 'C3 + 보정 A 명절 연휴 안 위치', 'C3 + 보정 B 공지된 무료·행사 (상한)', 'C3 + 보정 A + B']
y = M[(M['축'] == '전체')].set_index('방식').reindex(rules)
DAY2 = ['명절 연휴(무료)', '마지막 수요일(무료)']
BT = pd.read_parquet(DATA / 'backtests.parquet', filters=[('방식', 'in', rules)])
T10 = pd.read_csv(DATA / 'top10_shortage.csv', parse_dates=['date'])[['date', 'site']]
top = BT.merge(T10, on=['date', 'site']).groupby('방식')['cost'].sum() / 1e8
pd.concat([y[['WAPE']], y[['비용', '앞 행 대비 비용', '비용 (왕릉 최소 1명)']] / 1e8,
           table('무료', '비용', models=rules, scale=1e8).add_prefix('비용 '),
           table('날짜유형', '적중률', models=rules)[DAY2].add_prefix('적중률 '),
           top.rename('부족 10건 비용')], axis=1).round(3)
"""),
    md("## 5. 그림 — 방식별 비용 (무료 O / X 로 나눔, 원점 전날 확정)"),
    code("""
o = table('무료', '비용', scale=1e8)
o = o.loc[[m for m in o.index if '보정 A' not in m and '보정 B' not in m]].iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 6.5))
ax.barh(o.index, o['무료 O'], color=VIOLET, label='무료 개방 주 (14주)')
ax.barh(o.index, o['무료 X'], left=o['무료 O'], color='#c3c2b7', label='무료 없는 주 (38주)')
for i, (a, b) in enumerate(zip(o['무료 O'], o['무료 X'])):
    ax.text(a + b + 0.15, i, f'{a + b:.2f}', va='center', fontsize=8.5)
ax.set_xlabel('백테스트 비용 (억 원)'); ax.legend(loc='lower right', frameon=False)
ax.set_title('C3 가 가장 싸고, 줄어든 비용은 주로 무료 개방 주에서 나온다', loc='left', fontweight='bold')
plt.tight_layout(); plt.show()
"""),
    md("## 6. 원점별 학습 구간 · 지표 값 (가이드 요구사항 2)\n\n원점 52개마다 학습 구간 날짜와 베이스라인 3개 + 최종 모형 C3 의 WAPE · 비용. 보고서 ④ 「원점별 학습 구간 · 지표 값」과 같은 표다."),
    code("""
NAMES = {'0a 나이브': '나이브', '0b 계절 나이브': '계절 나이브', '1 직전 7일 평균': '직전 7일 평균', 'C3 Chronos-2 + 공휴일·무료 개방': 'C3'}
B = pd.read_parquet(DATA / 'backtests.parquet', filters=[('방식', 'in', list(NAMES)), ('확정', '==', '전날')])
B = B[B['status'] == 'open'].assign(ae=lambda x: (x['y'] - x['yhat']).abs(), 방식=lambda x: x['방식'].map(NAMES))
g = B.groupby(['origin', '방식'])
W = (g['ae'].sum() / g['y'].sum()).unstack()[list(NAMES.values())].add_prefix('WAPE ')
C = (g['cost'].sum() / 1e6).unstack()[['직전 7일 평균', 'C3']].add_prefix('비용(백만) ')
o = W.index.to_series()
P = pd.DataFrame({'주범주': B.drop_duplicates('origin').set_index('origin')['주범주'].str[0],
                  'MLP 학습': '2023-01-01 ~ ' + (o - pd.Timedelta(days=57)).dt.strftime('%Y-%m-%d'),
                  'MLP 검증': (o - pd.Timedelta(days=56)).dt.strftime('%m-%d') + ' ~ ' + (o - pd.Timedelta(days=1)).dt.strftime('%m-%d'),
                  'Chronos-2 입력': '2023-01-01 ~ ' + (o - pd.Timedelta(days=1)).dt.strftime('%Y-%m-%d'),
                  '예측(평가)': o.dt.strftime('%m-%d') + ' ~ ' + (o + pd.Timedelta(days=6)).dt.strftime('%m-%d')}).join(W).join(C)
P['WAPE 1위'] = W.idxmin(axis=1).str.replace('WAPE ', '')
P.index = P.index.strftime('%Y-%m-%d')
print('WAPE 1위 횟수:', P['WAPE 1위'].value_counts().to_dict(),
      '| C3 < 직전 7일 평균 (WAPE · 비용):', int((P['WAPE C3'] < P['WAPE 직전 7일 평균']).sum()), '·',
      int((P['비용(백만) C3'] < P['비용(백만) 직전 7일 평균']).sum()), '/ 52')
P.round(3)
"""),
])

# ════════════════════════════════════════════════════════════
build("03_범주별_오차분석.ipynb", [
    md("""
# 03 범주별 지표와 오차 분석

주 범주(A~E) · 날짜 유형 · 개소 유형 · 개소 · 교안 구분 · 상·하반기 · Chronos-2 공개일 전/후. 그리고 인력이 가장 많이 모자란 10건과 실수 4(합계로 평가).
"""),
    code(SETUP),
    md("## 1. 주 범주 A~E (채점 축: 원점 주)"),
    code("pd.concat({k: table('주범주', k, models=KEY, scale=1e8 if k == '비용' else 1) for k in ['WAPE', '적중률', '비용']}, axis=1).round(3)"),
    md("## 2. 날짜 유형 (가이드 요구사항 7)\n\nC3 의 약점: 마지막 수요일 적중률 0.49 — 무료 개방일에 모자라는 날이 절반."),
    code("""
DAY = ['명절 연휴(무료)', '마지막 수요일(무료)', '공휴일(무료 아님)', '주말', '평일']
pd.concat({k: table('날짜유형', k, models=KEY, scale=1e8 if k == '비용' else 1)[DAY] for k in ['WAPE', '적중률', '비용']}, axis=1).round(3)
"""),
    md("## 3. 개소 유형 · 개소"),
    code("pd.concat({k: table('개소유형', k, models=KEY, scale=1e8 if k == '비용' else 1) for k in ['WAPE', 'MASE', '적중률', '비용']}, axis=1).round(3)"),
    code("""
st = table('개소', '비용', models=['1 직전 7일 평균', 'C3 Chronos-2 + 공휴일·무료 개방'], scale=1e6).T
st['절감'] = st.iloc[:, 0] - st.iloc[:, 1]; st['절감률'] = st['절감'] / st.iloc[:, 0]
st.sort_values('절감', ascending=False).round(2)
"""),
    md("## 4. 교안 구분 · 상·하반기 · Chronos-2 공개일(2025-10-17) 전/후\n\n공개일 전 원점은 사전학습 자료와 겹쳤을 수 있다. 공개일 후 원점에서도 C3 가 이기는지 본다."),
    code("""
for ax_ in ['교안 구분', '반기', '공개일']:
    print('■', ax_); display(pd.concat({k: table(ax_, k, models=KEY, scale=1e8 if k == '비용' else 1) for k in ['WAPE', 'MASE', '비용']}, axis=1).round(3))
"""),
    md("## 5. 인력이 가장 많이 모자란 10건 (C3)\n\n원인 셋: 명절 연휴 후반 7건(가을 궁중문화축전과 겹침) · 규칙 밖 무료 개방 2건(10-29~11-09) · 행사일 1건(종묘대제)."),
    code("""
T10 = pd.read_csv(DATA / 'top10_shortage.csv')
display(T10[['순위', 'date', 'weekday', 'site', 'y', 'q80', 'short', 'cost', '원인 분류', '원인']].round(1))
print('10건 비용 합', round(T10['cost'].sum() / 1e8, 3), '억')
T10.groupby('원인 분류')['cost'].agg(['size', 'sum']).assign(sum=lambda d: (d['sum'] / 1e8).round(3))
"""),
    md("## 6. 자주 하는 실수 4 — 합계로 평가하면\n\n23개소를 날짜별로 합쳐 채점하면 개소 간 +·− 오차가 상쇄돼 좋아 보인다."),
    code("""
BT = pd.read_parquet(DATA / 'backtests.parquet', filters=[('seed', '==', 0), ('확정', '==', '전날')])
BT = BT[BT['방식'].isin(['1 직전 7일 평균', 'C3 Chronos-2 + 공휴일·무료 개방']) & (BT['status'] == 'open')]
def wape(d): return (d['y'] - d['yhat']).abs().sum() / d['y'].sum()
out = {}
for m, d in BT.groupby('방식'):
    tot = d.groupby('date')[['y', 'yhat']].sum()
    grp = d.groupby(['date', 'group'])[['y', 'yhat']].sum()
    out[m] = {'개소×날짜 (우리 방식)': wape(d), '개소 유형 합계×날짜': wape(grp), '23개소 합계×날짜': wape(tot)}
pd.DataFrame(out).T.round(3)
"""),
])

# ════════════════════════════════════════════════════════════
build("04_비용_가정_확정시점.ipynb", [
    md("""
# 04 비용 · 절감액 · 가정 바꾸기 · 근무표 확정 시점

기본 가정: 부족 1명·일 60만 원(C_u), 남음 15만 원(C_o), 1명당 2,000명 → τ* = 0.8. 인력은 소수로 계산(가이드).
"""),
    code(SETUP),
    md("## 1. 절감액을 둘로 나누기 (가이드 요구사항 4)\n\n팀 규칙 「왕릉은 문 여는 날 하루 1명 이상」을 직전 7일 평균에도 똑같이 적용한 값을 함께 낸다(가이드: 팀이 더한 규칙은 직전 7일 평균에도)."),
    code("""
e = M[(M['축'] == '전체')].set_index('방식')
out = {}
for col in ['비용', '비용 (왕릉 최소 1명)']:
    x = e[col] / 1e8
    a, b, c_ = x['1 직전 7일 평균'], x['2 + 서비스 수준 보정'], x['C3 Chronos-2 + 공휴일·무료 개방']
    out[col] = {'직전 7일 평균 비용': a, '서비스 수준 보정만으로 줄어든 금액': a - b, '모형으로 더 줄어든 금액': b - c_,
                '전체 절감액': a - c_, '모형 비용': c_}
pd.DataFrame(out).rename(columns={'비용': '기본 (억 원)', '비용 (왕릉 최소 1명)': '왕릉 최소 1명 (억 원)'}).round(3)
"""),
    md("## 2. 근무표 확정 시점 — 전날 · 1 · 2 · 3주 전 (같은 평가 날짜)\n\n4주 권고의 k주차는 (k − 1)주 일찍 확정한 것과 같다. 3·4주차는 Colab T4 v3 실행."),
    code("""
LEADS = ['전날', '1주 전', '2주 전', '3주 전']
rows = []
for base in ['1 직전 7일 평균', '2 + 서비스 수준 보정', 'C3 Chronos-2 + 공휴일·무료 개방']:
    for lab in LEADS:
        m = base if lab == '전날' else f'{base} · {lab}'
        r = e.loc[m]
        rows.append({'방식': base, '확정': lab, '권고 주차': f'{LEADS.index(lab) + 1}주차', 'WAPE': r['WAPE'], 'MASE': r['MASE'],
                     '적중률': r['적중률'], '비용(억)': r['비용'] / 1e8, '비용 왕릉 최소 1명(억)': r['비용 (왕릉 최소 1명)'] / 1e8})
lt = pd.DataFrame(rows)
lt['전날 대비(억)'] = lt['비용(억)'] - lt.groupby('방식')['비용(억)'].transform('first')
lt.round(3)
"""),
    code("""
fig, ax = plt.subplots(figsize=(7.5, 4))
for (m, d), col in zip(lt.groupby('방식', sort=False), [GRAY, AQUA, ORANGE]):
    ax.plot(range(4), d['비용(억)'], marker='o', color=col, lw=2, label=m)
    ax.text(3.08, d['비용(억)'].iloc[-1], f"{d['비용(억)'].iloc[-1]:.2f}", va='center', fontsize=8.5)
ax.set_xticks(range(4), [f'{l}\\n({i + 1}주차)' for i, l in enumerate(LEADS)]); ax.set_ylabel('비용 (억 원)')
ax.set_ylim(0, None); ax.legend(frameon=False, fontsize=8.5, loc='lower left')
ax.set_title('3주 일찍 확정해도 C3 는 전날 확정한 직전 7일 평균보다 5.6억 싸다', loc='left', fontweight='bold', fontsize=10.5)
plt.tight_layout(); plt.show()
"""),
    md("## 3. 가정 바꾸기 — 23개소 합계\n\n① q0.9 로 배치 ② 무료 개방일만 부족 손해 120만(→ 무료일 τ 0.89, q0.9) ③ 1명당 1,500명."),
    code("""
S = pd.read_csv(DATA / 'scenarios.csv')
tot = S[S['개소'] == '합계']
pd.concat({'비용(억)': tot.pivot(index='가정', columns='방식', values='비용') / 1e8,
           '절감(억)': tot.pivot(index='가정', columns='방식', values='직전 7일 평균 대비 절감') / 1e8,
           '적중률': tot.pivot(index='가정', columns='방식', values='적중률')}, axis=1).round(3)
"""),
    md("## 4. 가정 바꾸기 — 개소별 절감 (C3 vs 직전 7일 평균, 백만 원)\n\n23개소 × 4가정 모두 양수면 결론이 가정에 흔들리지 않는다."),
    code("""
ss = S[(S['방식'] == 'C3 Chronos-2 + 공휴일·무료 개방')].pivot(index='개소', columns='가정', values='직전 7일 평균 대비 절감') / 1e6
order = ['경복궁', '창덕궁', '창경궁', '덕수궁', '종묘'] + [i for i in ss.index if i not in ('경복궁', '창덕궁', '창경궁', '덕수궁', '종묘', '합계')] + ['합계']
ss = ss.reindex(order)
print('모두 양수:', bool((ss > 0).all().all()))
ss.round(1)
"""),
])

# ════════════════════════════════════════════════════════════
build("05_권고표_2026.ipynb", [
    md("""
# 05 2026 인력 배치 권고표 (2026-01-01 ~ 01-28, 4주)

C3(Chronos-2 + 공휴일·무료 개방)로 2025-12-31 까지의 기록에서 28일을 한 번에 예측. 인력(소수) = q0.8 ÷ 2,000, 휴관일 0.
**정수 = 날마다 올림** — 예측이 불확실할 때 「충분할 확률 ≥ 0.8 인 가장 작은 정수」가 q0.8 의 올림이다.
k주차는 (k − 1)주 일찍 확정한 백테스트(lead 1 · 8 · 15 · 22, 04 노트북 2절)로 검증했다 — C3 비용 8.46 · 9.22 · 9.44 · 9.30억, 적중률 0.80 유지.
"""),
    code(SETUP),
    code("""
R = pd.read_csv(DATA / 'recommend_2026.csv', parse_dates=['date'])
print('무료 개방일:', list(R.loc[R['is_free_rule'] == 1, 'date'].dt.strftime('%m-%d').unique()))
"""),
    md("## 1. 주차별 합 (명·일)"),
    code("""
cols = ['기본 (소수)', '기본 (정수)', '① 서비스 수준 0.9 (소수)', '② 무료 개방일 C_u 120만 (소수)', '③ 1명당 1,500명 (소수)']
wk = R.groupby(['site', '주차'])[['기본 (소수)', '기본 (정수)']].sum().unstack('주차').reindex(SITES)
wk.loc['합계'] = wk.sum()
display(wk.round(1))
sm = R.groupby('site')[cols].sum().reindex(SITES); sm.loc['합계'] = sm.sum()
sm.round(1)
"""),
    md("## 2. 일별 정수 권고표 — 주차별"),
    code("""
for k in range(1, 5):
    d = R[R['주차'] == k].pivot(index='site', columns='date', values='기본 (정수)').reindex(SITES)
    d.columns = [c.strftime('%m-%d') + '(' + '월화수목금토일'[c.dayofweek] + ')' for c in d.columns]
    d['합'] = d.sum(axis=1); d.loc['합계'] = d.sum()
    print(f'■ {k}주차'); display(d)
"""),
    md("## 3. 1/28 마지막 수요일(무료) vs 1/21 평소 수요일\n\n모형이 올린 배수는 과거 효과 크기(궁 마지막 수요일 약 1.8배)보다 작다. 백테스트에서 C3 의 마지막 수요일 적중률은 확정 시점별로 0.49(전날) · 0.54(1주 전) · 0.52(2주 전) · 0.61(3주 전)으로, **4주차라서 낮은 것이 아니라** 어느 시점이든 실제가 중앙값의 약 1.5배인 **무료 효과 과소 추정** 때문이다. 1/28 은 권고보다 더 필요할 수 있다."),
    code("""
a = R[R['date'] == '2026-01-28'].set_index('site')['q80']; b = R[R['date'] == '2026-01-21'].set_index('site')['q80']
(a / b).reindex(SITES).round(2).rename('q0.8 배수 (1/28 ÷ 1/21)').to_frame().T
"""),
    md("## 4. 올림과 최소 인원이 만드는 차이\n\n팀 결정(10/15): 날마다 올림 + **왕릉은 문 여는 날 하루 1명 이상**, 관리소 공유 없음. 왕릉은 필요 인원이 하루 0.0~0.4명이라 올림만으로도 하루 1명이 되므로 정수 권고표는 같고, 소수 열(`최종 권고 (소수)`)만 하한 1명이 반영된다."),
    code("""
g = R.groupby('group')[['기본 (소수)', '최종 권고 (소수)', '기본 (정수)']].sum()
g['정수 ÷ 소수'] = g['기본 (정수)'] / g['기본 (소수)']
g.round(2)
"""),
])
