"""03_scoring.ipynb 생성 — 교안 양식 채점표 + 무료 개방 O/X 채점 + FVA. 계산 결과는 outputs/run_v2/ (tools/run_day2.py)."""
import nbformat as nbf
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s.strip()))
code = lambda s: cells.append(nbf.v4.new_code_cell(s.strip()))

md("""
# 채점표 — 무료 개방 O / X 와 FVA

설계는 `분석설계.md`. 원점 2025-01-01(수)부터 7일 간격 52개, 7일을 원점 전날 한 번에 예측, 확장 윈도우(2023-01-01~).

| 채점 축 | 원점 수 |
|---|---|
| **무료 O** — 7일 안에 무료 개방일(명절 연휴 · 마지막 수요일) | 14 |
| **무료 X** | 38 |
| 2단: A 명절 연휴 주 · B 마지막 수요일 주 / C 평일 공휴일 주 · D 특별일 직후 주 · E 평소 주 | 4 · 10 / 4 · 13 · 21 |

지표: MASE(모델 비교, 같은 주의 계절 나이브와 비교) · WAPE(1순위) · 비용(최종 결정) · 적중률 · 80% 포함률 · 평균 구간 길이.
학습형 모델(MLP)은 시드 0~4 다섯 번의 평균이고, 차이가 시드 범위보다 작으면 「차이 없음」.
""")
code("""
import sys; sys.path.insert(0, 'src')
import pandas as pd, numpy as np
import hv, dl
from pathlib import Path
pd.set_option('display.width', 240); pd.set_option('display.max_columns', 40)
pd.set_option('display.float_format', '{:,.3f}'.format)
RUN = Path('outputs/run_v2')

v, w, c, s = hv.load()
assert hv.check_anchors(v, w, c)['일치'].all()
cal = hv.add_free_rule(hv.make_calendar())
panel = hv.build_panel(v, cal, s)
qden = hv.mase_denominators(panel)
wt = hv.week_table()
wt['무료'] = np.where(wt['무료 개방 주'], '무료 O', '무료 X')
print(wt['무료'].value_counts().to_dict(), wt['주범주'].value_counts().sort_index().to_dict())
""")

md("## 0. 예측 모으기")
code("""
m7 = hv.backtest(panel, hv.fc_mean7, name='mean7')
mult = hv.service_level_multiplier(panel, weeks=26, by='site')      # 2024 하반기 검증 원점에서 고른 설정
BASE = {
    '계절 나이브': hv.backtest(panel, hv.fc_snaive7, name='계절 나이브'),
    '나이브': hv.backtest(panel, hv.fc_naive, name='나이브'),
    '1 직전 7일 평균': m7.assign(model='1 직전 7일 평균'),
    '2 + 서비스 수준 보정': hv.apply_multiplier(m7, mult, by='site', name='2 + 서비스 수준 보정'),
}
FVA_LABEL = {
    'past': '3 MLP: 과거 관람객만',
    '+dow': '4 + 요일·정기 휴관',
    '+holiday_nf': '5 + 공휴일(명절 아님)',
    '+myeongjeol': '6 FVA 1차: + 명절 연휴',
    '+lastwed': '7 FVA 2차: + 마지막 수요일',
    '+rain_prev': '8 + 전날 큰비',
    '[완벽예보]+rain': '9 [완벽한 예보 가정] + 당일 비',
    '(선택)+neighbor': '(선택) + 이웃 궁 휴관',
}
raw = pd.read_parquet(RUN / 'mlp_raw.parquet')
MLP = {lab: {sd: hv.attach(panel, g.drop(columns=['variant', 'seed']), lab)
             for sd, g in raw[raw['variant'] == vk].groupby('seed')}
       for vk, lab in FVA_LABEL.items() if (raw['variant'] == vk).any()}
CH = {lab: pd.read_parquet(RUN / f'chronos_{tag}.parquet').assign(model=lab)
      for tag, lab in [('zs', 'Chronos-2 제로샷'), ('hol', 'Chronos-2 + 공휴일'), ('free', 'Chronos-2 + 공휴일·무료 개방')]}
print('MLP 변형:', list(MLP), '| 시드:', sorted(raw['seed'].unique()), '| 원점:', raw['origin'].nunique())
""")
code("""
def tag(bt):
    return bt.merge(wt[['origin', '무료', '주범주', '교안 구분']], on='origin', how='left')

def score(bt, by):
    \"\"\"by 범주별 지표. 비용은 주당(원점당) 백만 원으로도.\"\"\"
    bt = tag(bt)
    r = hv.summarize(bt, by=by, qden=qden)
    n = bt.groupby(by)['origin'].nunique()
    r['주당 비용(백만)'] = r['비용'].to_numpy() / 1e6 / n.reindex(r.index.get_level_values(0)).to_numpy()
    return r

def score_seeds(runs, by):
    \"\"\"MLP: 시드별로 채점해 평균, MASE·비용의 시드 범위.\"\"\"
    per = pd.concat([score(bt, by).assign(seed=sd) for sd, bt in runs.items()]).reset_index()
    keys = [by, 'model']
    m = per.groupby(keys).mean(numeric_only=True).drop(columns='seed')
    m['MASE 시드 범위'] = per.groupby(keys)['MASE'].agg(lambda x: x.max() - x.min())
    return m, per

FINAL_MLP = '7 FVA 2차: + 마지막 수요일'   # 최종 후보(무료 정보까지 넣은 행)
""")

md("""
## 1. 교안 양식 채점표 — 무료 O / X

교안 평가표(방식 × 공휴일 없는 주 / 있는 주)와 같은 모양으로, 축만 **무료 개방 O / X** 로 바꿨습니다.
""")
code("""
rows = [score(BASE[k], '무료') for k in ['계절 나이브', '나이브', '1 직전 7일 평균', '2 + 서비스 수준 보정']]
mlp_m, _ = score_seeds(MLP[FINAL_MLP], '무료'); rows.append(mlp_m.assign(**{'MASE 시드 범위': mlp_m['MASE 시드 범위']}))
rows += [score(bt, '무료') for bt in CH.values()]
T1 = pd.concat(rows)
order = ['계절 나이브', '나이브', '1 직전 7일 평균', '2 + 서비스 수준 보정', FINAL_MLP] + list(CH)
def wide(T, cols):
    out = T[cols].unstack(0)
    return out.reindex(order)
print('■ MASE (같은 주의 계절 나이브와 비교)'); display(wide(T1, ['MASE']))
print('■ 80% 포함률 · 평균 구간 길이(명) · q0.9 초과 비율'); display(wide(T1, ['포함률(80%)', '평균 구간 길이', 'q0.9 초과']))
print('■ 적중률(목표 0.8) · WAPE · 주당 비용(백만 원)'); display(wide(T1, ['적중률', 'WAPE', '주당 비용(백만)']))
T1.to_csv(RUN / 'table1_free_ox.csv', encoding='utf-8-sig')
""")

md("## 2. 2단 범주 — A~E (주제 답변 · 진단)")
code("""
rows = [score(BASE[k], '주범주') for k in ['계절 나이브', '1 직전 7일 평균', '2 + 서비스 수준 보정']]
m2, _ = score_seeds(MLP[FINAL_MLP], '주범주'); rows.append(m2)
rows += [score(bt, '주범주') for bt in CH.values()]
T2 = pd.concat(rows)
order2 = ['계절 나이브', '1 직전 7일 평균', '2 + 서비스 수준 보정', FINAL_MLP] + list(CH)
for col in ['MASE', '적중률', '주당 비용(백만)']:
    print('■', col); display(T2[col].unstack(0).reindex(order2))
T2.to_csv(RUN / 'table2_week_cats.csv', encoding='utf-8-sig')
""")

md("## 3. 교안 호환 — 공휴일 있는 주(11) / 없는 주(41)")
code("""
rows = [score(BASE[k], '교안 구분') for k in ['계절 나이브', '나이브', '1 직전 7일 평균']]
m3, _ = score_seeds(MLP[FINAL_MLP], '교안 구분'); rows.append(m3)
rows += [score(bt, '교안 구분') for bt in CH.values()]
T3 = pd.concat(rows)
display(T3[['MASE', '포함률(80%)', '평균 구간 길이']].unstack(0).reindex(['계절 나이브', '나이브', '1 직전 7일 평균', FINAL_MLP] + list(CH)))
""")

md("""
## 4. FVA 표 — 전체 · 무료 O · 무료 X

행마다 앞 행에 정보를 하나 더했습니다. **6행(FVA 1차 명절 연휴)·7행(FVA 2차 마지막 수요일)의 비용 감소가 무료 O 열에 몰리면** 모델이 무료 정보를 제대로 쓴 것입니다. MLP 행은 시드 5개 평균, `5시드 ↓` 는 같은 시드끼리 앞 행과 비교해 다섯 번 모두 비용이 줄었는지입니다.
""")
code("""
def cost_cols(bt):
    d = hv.add_cost(tag(bt)[lambda x: x['status'] == 'open'])
    return pd.Series({'비용 전체': d['cost'].sum(), '비용 무료 O': d.loc[d['무료'] == '무료 O', 'cost'].sum(),
                      '비용 무료 X': d.loc[d['무료'] == '무료 X', 'cost'].sum()})

fva_rows, seed_costs = {}, {}
for k in ['1 직전 7일 평균', '2 + 서비스 수준 보정']:
    r = hv.summarize(BASE[k], qden=qden).iloc[0]
    fva_rows[k] = pd.concat([r[['WAPE', 'MASE']], cost_cols(BASE[k])])
for lab, runs in MLP.items():
    per = pd.DataFrame({sd: pd.concat([hv.summarize(bt, qden=qden).iloc[0][['WAPE', 'MASE']], cost_cols(bt)])
                        for sd, bt in runs.items()}).T
    seed_costs[lab] = per
    row = per.mean(); row['MASE 시드 범위'] = per['MASE'].max() - per['MASE'].min()
    fva_rows[lab] = row
FVA = pd.DataFrame(fva_rows).T
chain = [k for k in FVA.index if not k.startswith('(선택)')]
for col in ['비용 전체', '비용 무료 O', '비용 무료 X']:
    FVA[f'앞 행 대비 {col[3:]}'] = FVA.loc[chain, col].diff()
# (선택) 행은 7행과 비교
if '(선택) + 이웃 궁 휴관' in FVA.index:
    for col in ['비용 전체', '비용 무료 O', '비용 무료 X']:
        FVA.loc['(선택) + 이웃 궁 휴관', f'앞 행 대비 {col[3:]}'] = FVA.loc['(선택) + 이웃 궁 휴관', col] - FVA.loc[FINAL_MLP, col]
labs = [l for l in chain if l in seed_costs]
prev = {labs[i]: labs[i - 1] for i in range(1, len(labs))}
prev['(선택) + 이웃 궁 휴관'] = FINAL_MLP
for col in ['비용 전체', '비용 무료 O', '비용 무료 X']:
    FVA[f'5시드 ↓ {col[3:]}'] = pd.Series({l: bool((seed_costs[l][col] < seed_costs[p][col]).all())
                                          for l, p in prev.items() if l in seed_costs})
won = [c for c in FVA.columns if c.startswith('비용') or c.startswith('앞 행')]
FVA_show = FVA.copy(); FVA_show[won] = (FVA_show[won] / 1e6).round(1)
FVA_show.to_csv(RUN / 'fva_v2.csv', encoding='utf-8-sig')
print('비용 단위: 백만 원'); FVA_show
""")
code("""
# 참고: Chronos-2 세 행 (FVA 체인 밖) — + 공휴일 → + 공휴일·무료 개방 의 차이가 Chronos 쪽 무료 정보 가치
ch = pd.DataFrame({k: pd.concat([hv.summarize(bt, qden=qden).iloc[0][['WAPE', 'MASE']], cost_cols(bt) / 1e6]) for k, bt in CH.items()}).T
ch
""")

md("""
## 5. Chronos-2 공개일(2025-10-17) 전 / 후

채점 7일이 공개일 전에 끝나는 원점은 사전학습 자료와 겹쳤을 수 있습니다(교안). 공개일 후 원점만으로 따로 봅니다.
""")
code("""
def rel(bt):
    return bt.assign(공개일=np.where(bt['origin'] + pd.Timedelta(days=6) < dl.CHRONOS_RELEASE, '공개일 전', '공개일 후'))
rows = [hv.summarize(rel(bt), by='공개일', qden=qden) for bt in CH.values()]
rows += [hv.summarize(rel(BASE['계절 나이브']), by='공개일', qden=qden)]
mm = pd.concat([hv.summarize(rel(bt), by='공개일', qden=qden).assign(seed=sd) for sd, bt in MLP[FINAL_MLP].items()])
rows.append(mm.reset_index().groupby(['공개일', 'model']).mean(numeric_only=True).drop(columns='seed'))
print('원점 수:', rel(BASE['나이브']).groupby('공개일')['origin'].nunique().to_dict())
pd.concat(rows)[['MASE', 'WAPE', '적중률', '비용']].unstack(0)
""")

md("""
## 6. 원점별 — 원점이 적은 범주(A·C)와 계절 나이브보다 MASE 가 낮은 개소 비율

교안 규칙: 평균으로 정할 수 없을 때 원점마다 「계절 나이브보다 MASE 가 낮은 개소 비율」을 함께 적습니다.
""")
code("""
def site_mae(bt):
    x = bt[bt['status'] == 'open'].assign(ae=lambda d: (d['y'] - d['yhat']).abs())
    return x.groupby(['origin', 'site'])['ae'].mean()
sn = site_mae(BASE['계절 나이브'])
cand = {'1 직전 7일 평균': BASE['1 직전 7일 평균'], FINAL_MLP + ' (시드 0)': MLP[FINAL_MLP][0], **CH}
beat = pd.DataFrame({k: (site_mae(bt) < sn.reindex(site_mae(bt).index)).groupby('origin').mean() for k, bt in cand.items()})
beat = beat.join(wt.set_index('origin')[['무료', '주범주']])
display(beat[beat['주범주'].str[0].isin(['A', 'C'])].round(2))
beat.groupby('무료').mean(numeric_only=True).round(2)
""")

md("## 7. 상반기 / 하반기 원점 (상반기는 학습 1.8년)")
code("""
rows = [hv.summarize(bt.assign(반기=hv.half(bt)), by='반기', qden=qden) for bt in [BASE['계절 나이브'], BASE['1 직전 7일 평균'], *CH.values()]]
mm = pd.concat([hv.summarize(bt.assign(반기=hv.half(bt)), by='반기', qden=qden).assign(seed=sd) for sd, bt in MLP[FINAL_MLP].items()])
rows.append(mm.reset_index().groupby(['반기', 'model']).mean(numeric_only=True).drop(columns='seed'))
pd.concat(rows)[['MASE', 'WAPE', '적중률', '비용']].unstack(0)
""")

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
nbf.write(nb, ROOT / "03_scoring.ipynb")
print("written")
