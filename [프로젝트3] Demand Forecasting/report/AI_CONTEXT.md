> real_final 판 — 이 문서의 경로는 **원래 저장소** 기준이다. real_final 안에서는 `final/data` → `data/`, `outputs/report_addons` → `appendix/report_addons`, `outputs/figures` → `report/figures` 로 읽는다.

# AI_CONTEXT — 궁·능 관람객 예측 프로젝트 인수인계 (AI용)

> **쓰는 법**: 이 파일 전체를 Claude·ChatGPT 등에 붙여 넣거나, Claude Code 로 이 폴더를 연 뒤 "AI_CONTEXT.md 먼저 읽어" 라고 하면 됩니다.
> 기준 시점 2026-10-15. 숫자는 모두 `outputs/run_v2/`, `outputs/report_addons/` 에서 나온 값입니다.

---

## 0. AI 에게 주는 지시 (이 블록을 그대로 프롬프트로 사용)

```
너는 "궁·능 23개소 관람객 예측과 인력 배치" 팀 프로젝트(딥러닝 시계열 수업)의 분석 보조다.
아래 문서(AI_CONTEXT.md)가 지금까지의 결정·정의·결과·파일 위치의 기준이다.

규칙
1. 문서의 "확정 결정"(§2)은 팀이 여러 번 논의해 정한 것이다. 바꾸자고 제안할 수는 있지만,
   묻지 않고 옛 설정(원점 2025-07-01 26개, 비 5mm, MASE 1순위, 범주별 따로 학습)으로 되돌리지 마라.
2. 숫자를 말할 때는 어느 파일에서 나왔는지 밝혀라. 파일에 없는 숫자는 "계산 안 함"이라고 말하고 지어내지 마라.
3. **예측 입력 · 채점 축 · 효과 크기**의 무료 개방 여부는 `is_free_rule`(달력 규칙)만 쓴다. 예측할 날의 `paid` 는 확정 시점에 알 수 없다.
   **지난 날짜가 실제로 무료였는지**는 교안 정의(유료 비중 `paid ÷ total` < 15%)로 판정한다 — 달력 규칙 검증 · 규칙 밖 무료 개방 찾기 · 보정 B 의 과거 표시에만.
   `paid == 0` 으로 판정하지 마라(창덕궁 · 경복궁 무료일을 놓침). 15% 정의는 덕수궁 · 저유료 왕릉 5곳(양주온릉 · 정릉 · 영휘원 · 의릉 · 홍유릉)에서 맞지 않는다.
4. 보고 형식은 수업 교안(`배운거/` 폴더)과 같게 유지한다: 직전 7일 평균 → + 서비스 수준 보정 → MLP → Chronos-2 순서,
   표는 무료 개방 O/X 로 나눠 채점.
5. 지표 역할: WAPE = 정확도 1순위 / MASE = 딥러닝 모형끼리 비교 / 비용(원) = 최종 결정.
6. 그림 제목은 "발견한 내용"을 문장으로 쓰고, 그 문장이 데이터와 맞는지 숫자로 확인한 뒤에 쓴다.
7. 코드 수정은 `src/hv.py`(공통), `src/dl.py`(딥러닝)에 하고, 노트북은 직접 고치지 말고 `tools/make_*_nb.py` 를 고쳐 다시 만든다.
8. 답은 한국어, 체크리스트·표 위주, 근거를 붙여서.
```

---

## 1. 프로젝트 한 장 요약

| 항목 | 내용 |
|---|---|
| 과제 | 궁·능 23개소 일별 관람객 예측 → 개소별 인력 배치 권고 |
| 핵심 질문 | **무료 개방일·명절에 개소마다 인력을 평소의 몇 배로 늘려야 하는가** |
| 마감 | 발표 2026-10-19(월) 14:30, 제출 23:59 — 공개 GitHub 저장소에 `report.pdf`, `slides.pdf` |
| 데이터 | `heritage_visitors_daily.parquet`(일별 total/free/paid), `weather_daily.parquet`, `calendar_kr_2015_2025.csv`, `sites.csv`, `anchors.json`(검산용 기준값) |
| 개소 | 궁 4(경복궁·창덕궁·창경궁·덕수궁) + 종묘 + 왕릉 18 = 23 |
| 결론(가안) | **Chronos-2 + 공휴일·무료 개방 공변량**, 분위수 q0.8 기준 배치. 직전 7일 평균 대비 비용 14.86억 → 8.46억 (−6.40억) |

---

## 2. 확정 결정 (바꾸려면 팀 합의)

| # | 결정 | 내용 / 이유 |
|---|---|---|
| 1 | 예측 단위 | 7일 직접 예측(horizon 7), 매주 수요일 원점 |
| 2 | 시험 원점 | **2025-01-01 부터 52개**(1년 전체, 설·추석·마지막 수요일 모두 포함) |
| 3 | 학습 구간 | **2023-01-01 부터, 확장 윈도우**(원점마다 원점 전날까지 늘려 감) |
| 4 | 검증 원점 | 서비스 수준 배수 선택 = 2024-07-03 부터 26개 / 교안 재현 = 2025-07-01 부터 26개 |
| 5 | 규칙 밖 0 | **A안**: 정기 휴관일이 아닌데 0 인 날은 학습·평가에서 제외 |
| 6 | 휴관일 | `closed_weekday` 기준. 휴관일 값은 NaN, 빠진 날짜는 격자로 채운 뒤 결측 |
| 7 | 비 | 10mm 이상 = 비(0/1) |
| 8 | 지표 | WAPE 1순위, MASE 딥러닝 비교, 비용 최종 결정 |
| 9 | 채점 축 | **무료 개방 O / X** (O 14주, X 38주). 교안 호환 분할 11/41 도 같이 냄 |
| 10 | FVA | 1차 = 무료 공휴일(명절 연휴) 피처, 2차 = 마지막 수요일 피처 |
| 11 | 학습 방식 | 범주별로 따로 학습하지 않음 — 하나로 학습, 채점만 나눔 |
| 12 | 근무표 확정 | 원점 전날 확정(기본). 1주 전 확정은 비교용 |
| 13 | 실행 환경 | 로컬 CPU 또는 Colab T4 |
| 14 | 최종 모형 (10/15) | **C3 Chronos-2 + 공휴일·무료 개방** |
| 15 | 권고 기간 (10/15) | **4주 (2026-01-01 ~ 01-28)** |
| 16 | 정수 · 최소 인원 (10/15) | 날마다 q0.8 ÷ 2,000 올림, **왕릉은 문 여는 날 하루 1명 이상**, 관리소 공유 안 함. 비용 계산(소수)에서도 왕릉 하한 1명을 기준선·모형에 똑같이 적용 (`tools/make_v3_results.py`) |

---

## 3. 정의 (코드와 같은 이름)

**무료 개방 규칙 `is_free_rule`** (2023년 이후에만 유효)
- 명절 연휴 = 설·추석 당일을 포함해 이어지는 쉬는 날 전체 (`is_myeongjeol`)
- 매월 마지막 수요일 (`is_last_wednesday`)
- 과거는 다름: 2015–16 은 명절 당일만, 2021 은 무료 없음 → 그래서 학습을 2023 부터 시작

**상태 `status`**: open / closed_regular / closed_substitute / closed_temp / missing

**주 범주 (원점 52주 분류)**

| 범주 | 주 수 | 무료 개방 |
|---|---|---|
| A 명절 연휴 주 | 4 | O |
| B 마지막 수요일 주 | 10 | O |
| C 평일 공휴일 주(무료 없음) | 4 | X |
| D 특별일 직후 주 | 13 | X |
| E 평소 주 | 21 | X |

**비용 가정**
- 부족 1명·일 C_u = 60만 원, 남음 1명·일 C_o = 15만 원 → 목표 분위수 τ* = C_u/(C_u+C_o) = 0.8
- 관람객 2,000명당 1명 → 배치 인력 = q0.8 / 2000
- 비용 = C_u × max(필요−배치, 0) + C_o × max(배치−필요, 0), 개방일만 합산

**지표**: WAPE, MASE(분모 = 2023~cutoff 의 lag-7 MAE), 적중률(실제 ≤ q0.8), 80% 포함률, 평균 구간 길이, q0.9 초과 비율, 부족/잉여/총 비용

---

## 4. 모형

| 모형 | 설정 |
|---|---|
| 직전 7일 평균 | 기준선 (`hv.fc_mean7`) |
| + 서비스 수준 보정 | 개소별 배수를 검증 원점 26개에서 골라 곱함 (`hv.service_level_multiplier`) |
| 글로벌 MLP | 입력 28일 log1p(개소별 표준화) + 개방 마스크 + 개소 원핫 + 달력 공변량 → 64 → 64 → 7×4 분위수(0.1/0.5/0.8/0.9). pinball loss, Adam 1e-3, batch 512, patience 5, 시드 0–4. 학습 2023-01-01~원점−57일, 직전 56일로 조기 종료 |
| Chronos-2 | `amazon/chronos-2`, chronos-forecasting 2.3.2. 맥락 2023-01-01~원점 전날. 공변량은 `df`·`future_df` 둘 다에 넣음. 3종: 제로샷 / + 공휴일 [is_holiday, is_closed_weekday] / + 공휴일·무료 개방 (+ is_myeongjeol, is_last_wednesday) |

주의: Chronos-2 공개일(2025-10-17) 이전 원점은 사전학습 데이터와 겹칠 수 있어 따로 표시함.

MLP FVA 변형(`dl.FEATURE_SETS`): past → +dow → +holiday_nf → +myeongjeol → +lastwed → +rain_prev → [완벽예보]+rain → (선택)+neighbor

---

## 5. 주요 결과 (원점 52개, 23개소)

| 방식 | WAPE | MASE | 적중률 | 비용 |
|---|---|---|---|---|
| 직전 7일 평균 | 0.444 | 1.224 | 0.58 | 14.86억 |
| + 서비스 수준 보정 | 0.444 | 1.224 | 0.80 | 13.20억 |
| MLP (FVA 2차까지) | 0.339 | 0.912 | — | 9.66억 |
| Chronos-2 제로샷 | 0.318 | — | — | 10.04억 |
| Chronos-2 + 공휴일 | — | — | — | 9.04억 |
| **Chronos-2 + 공휴일·무료 개방** | **0.293** | **0.822** | **0.804** | **8.46억** |

- 절감 −6.40억 = 보정 −1.66억 + 모형 −4.74억. 원점 52개 중 36개에서 WAPE 1위.
- FVA 1차(명절) −1.83억(그중 무료 O 주 −1.66억, 시드 5개 모두 개선). FVA 2차(마지막 수요일) 차이 없음. 비·이웃 휴관 피처는 비용 증가.
- 효과 크기: 궁 마지막 수요일 1.8배, 명절 당일 이후 4.0배 / 왕릉 마지막 수요일 1.5배, 평일 공휴일 2.5배 / 종묘 마지막 수요일 4.3배.
- 확정 시점: Chronos 1주 전 확정 9.22억(+0.76억), 직전 7일 평균 1주 전 17.33억.
- 개소 유형별 비용: 궁 10.96 → 6.21억. 절감 상위: 경복궁 −214M, 창덕궁 −96M, 창경궁 −88M, 덕수궁 −77M, 종묘 −52M.
- 부족 상위 10건 = 부족 비용의 21.5%(0.996억): 추석 후반(10-08, 10-09 궁 4곳) 7건(가을 궁중문화축전 10-08~12 와 겹침), 종묘대제(05-04, 정전 재개방 직후) 1건, 규칙 밖 무료 개방(11-04 창덕궁, 11-08 덕수궁) 2건 — 2025-10-29~11-09 4대궁·종묘·왕릉 무료(코리아 그랜드 페스티벌). (이전 문서의 6/3건 집계는 오류)
- 가정 바꾸기(23개소 합 절감, 백만 원): 기본 639.6 / τ 0.9 597.8 / 무료일 C_u 120만 1013.9 / 1명당 1,500명 852.8. **모든 개소·모든 가정에서 절감 양수.**
- 2026 권고 4주(01-01~01-28): 정수 합 883명·일(1~4주차 231·215·215·222, 소수 449.6). 왕릉은 하루 최소 1명(각 24명·일).

---

## 6. 파일 목록

> **기준 폴더: `real_final/`** (10/15 부터) — 이 폴더 하나로 보고서 · 제언 · 그림 · 표 · 노트북을 보고, **원본 데이터부터 전부 다시 만들 수 있다**: `python tools/run_all.py`(경로는 `src/paths.py`). 문서 원본도 이 폴더의 `report/` 다. 아래 목록 중 `final/` · `outputs/day*` · 최상위 `report_draft.md` 등은 옛 저장소 구조이고, 그 구조용 스크립트는 `tools/legacy/` 에 보관했다.
>
> **(옛 구조) `final/`** — 전 과정을 한 번에 비교하는 정리 폴더. `final/report/README.md`(구성 + 한 장 비교), `final/data/`(backtests.parquet · metrics.csv · scenarios.csv · recommend_2026.csv · top10_shortage.csv), `final/notebooks/` 01~05. 다시 만들기: `tools/make_final_bundle.py` → `make_final_notebooks.py` → `make_final_report.py`.

### 문서 (사람이 읽는 것)
| 파일 | 내용 |
|---|---|
| `AI_CONTEXT.md` | 이 파일 |
| `real_final/report/검토_무료개방일과_피처정의.md` | 10/15 검토: 무료일 정의(달력 규칙 vs 15%)의 쓰임, 보정 A · B, 피처 · 공변량 전체 정의와 이유 |
| `README.md` | 데이터 설명(원본 제공) |
| `프로젝트 가이드.ipynb` | 과제 가이드·채점 기준 (원본) |
| `PLAN.md` | 전체 체크리스트(0~16절) + 결정 표 |
| `전처리.md` | 전처리 규칙과 코드(팀 공유용, 복사 가능) |
| `분석설계.md` | 채점 범주·FVA 1차/2차·Chronos 3종 설계 |
| `정리_1013.md` | 10/13 까지 진행 정리 |
| `report_draft.md` | 보고서 초안(가이드 ①~⑥ 구성). `⬜ [미완]` = 아직 안 한 항목 |
| `배운거/*.ipynb` | 수업 교안 5개 (형식·방법의 기준) |

### 원본 데이터
`heritage_visitors_daily.parquet`, `weather_daily.parquet`, `calendar_kr_2015_2025.csv`, `sites.csv`, `anchors.json`, `랭글용)*.csv`(같은 데이터의 CSV 판)

### 코드
| 파일 | 역할 |
|---|---|
| `src/hv.py` | 공통: 원점(ORIGINS·VAL_ORIGINS·GUIDE_ORIGINS), 로드·검산, 달력·무료 규칙, 패널, 기준선, 백테스트, 서비스 수준 보정, 비용, 주 범주(`week_table`), `summarize` |
| `src/dl.py` | 딥러닝: `FEATURE_SETS`, `Arrays`, `fit_predict_mlp`, `run_mlp`, `chronos_frames`, `run_chronos`, `COV_SETS` |
| `tools/run_day2.py` | MLP(변형×시드) + Chronos 3종 전체 실행. 이어서 돌리기 지원. `--device cpu/cuda`, `--out` |
| `tools/make_day1_nb.py` | → `01_day1_baseline.ipynb` (기준선·서비스 수준 보정·주 범주) |
| `tools/make_day2_nb.py` | → `02_day2_models.ipynb` (**옛 설정, 갱신 필요**) |
| `tools/make_scoring_nb.py` | → `03_scoring.ipynb` (교안 형식 채점표, FVA, 원점별). real_final 에서는 `tools/legacy/`, 표는 `tools/make_scoring_tables.py` |
| `tools/make_figures.py` | → `outputs/figures/fig1~8.png` |
| `tools/make_preprocessed.py` | → `outputs/preprocessed_panel.csv` (전처리.md 코드 실행) |
| `tools/make_colab_bundle.py` | → `outputs/heritage_colab.zip` + `colab_run.ipynb` (Colab T4 실행용) |
| `tools/make_report_addons.py` | → `outputs/report_addons/` (권고표, 확정 시점, 가정 바꾸기, 유형별, 부족 10건) |
| `tools/make_site_scenarios.py` | → 개소별 가정 바꾸기 비용·2026 권고 인력 |

### 노트북
`01_day1_baseline.ipynb`, `02_day2_models.ipynb`(옛 설정), `03_scoring.ipynb`, `colab_run.ipynb`

### 결과물 `outputs/`
| 경로 | 내용 |
|---|---|
| `day1/` | 기준선 백테스트, 규칙 붙인 달력(2015~2026) |
| `day2/` | **옛 설정(원점 26개) 결과 — 쓰지 말 것** |
| `run_v2/mlp_raw.parquet` | MLP 전 변형·시드 예측 |
| `run_v2/chronos_{zs,hol,free}.parquet` | Chronos-2 3종 예측 |
| `run_v2/overall_table.csv`, `table1_free_ox.csv`, `table2_week_cats.csv`, `fva_v2.csv`, `per_origin_wape.csv` | 채점표 |
| `figures/fig1~fig8` | 범주별 비용, MASE O/X, FVA, 원점별 비용, 효과 크기, 일별 포함률, 적중률, 경복궁 추석 사례 |
| `report_addons/recommend_2026*.csv` | 2026-01-01~07 개소별 권고 인력 |
| `report_addons/lead_compare.csv` | 전날 vs 1주 전 확정 |
| `report_addons/assumption_scenarios.csv` | 가정 바꾸기 (**23개소 합계**) |
| `report_addons/site_scenarios_cost.csv`, `site_scenarios_2026.csv` | 가정 바꾸기 **개소별** |
| `report_addons/by_group.csv`, `by_site_saving.csv`, `top10_shortage.csv` | 유형별·개소별 절감·부족 10건 |
| `report_addons/recommend_2026_4w*.csv` | 2026-01-01~01-28 4주 권고(일별 정수 · 주차별 합 · 가정 ②), `tools/make_recommend_4w.py` |
| `report_addons/daytype_*.csv`, `mistake4_*.csv`, `mistake5_*.csv` | 날짜 유형별 지표, 자주 하는 실수 4·5 측정 (`tools/make_report_extra.py`). `mistake5_*` 는 `paid == 0` 기준 기록 — 15% 기준은 01 노트북 5절 |
| `real_final/appendix/run_o1/` | 보정 B 변형 17곳 예측 3개(`c3_17` · `ruleB1_17` · `ruleB2_17`.parquet) + `o1_compare.csv` (`tools/run_o1_ruleB_variants.py` → `tools/score_o1.py`) |
| `report_addons/compare_all.zip` 안의 `model_compare_*.csv` | **전 방식 비교**(기준선 3 · MLP FVA 8행 · Chronos 3종): overall / free_ox / week_cats / group / site_cost / site_wape (`tools/make_model_compare.py`) |
| `preprocessed_panel.csv` | 전처리 완료 패널 (63,194행 × 25열) |

---

## 7. 재현 방법

```bash
# real_final/ 안에서
pip install pandas pyarrow "holidays==0.103" torch chronos-forecasting matplotlib nbformat nbclient ipykernel
python tools/run_all.py                  # 전부 (로컬 CPU 약 5 ~ 6시간, 이어서 돌리기 지원)
python tools/run_all.py --skip-models    # 모형 예측(outputs/)이 있으면 표 · 그림 · data · 노트북만 (약 40분)
```
- 단계 목록과 시간은 `README.md` 「전체 다시 만들기」. 10/15 에 전부 다시 돌려 기존 숫자와 같음을 확인(Chronos-2 CPU = T4).
- Colab(GPU)으로 Chronos-2 만: `python tools/make_colab_bundle_v3.py` → `outputs/heritage_colab_v3.zip`.
- CPU 병렬 시 스레드를 2개로 묶어야 함(안 묶으면 10배 느려짐) — `run_day2.py` 가 자동 처리.
- 실행 전 `hv.check_anchors()` 로 데이터 검산.

---

## 8. 남은 일 (2026-10-15 오후 기준)

완료(10/15): 개소별 가정 바꾸기 · 최소 인원(왕릉 1명) · 권고 4주 · 최종 모형 C3 · Colab v3(Chronos FVA 한 칸씩, 보정 규칙 A/B/A+B, 2·3주 전 확정) · 2026 설 공지 · 10/29~11/9 무료 공지 · `final/` 갱신.

v3 결과 요약 (`outputs/report_addons/v3_*.csv`, Chronos 는 `outputs/run_v3/` Colab T4):
- Chronos FVA: C1 10.04 → +정기 휴관 10.08(+0.04) → +공휴일 9.04(−1.04) → +명절 8.63(−0.41) → +마지막 수요일 8.46(−0.17)억
- 보정 규칙: A −0.01억(부족 10건 −0.21, 명절 적중률 0.69→0.57) · B −0.39억(공지가 확정 전이라는 상한) · A+B −0.43억 → 모형은 C3 유지, B 는 운영 규칙으로 권고
- 보정 B 변형(10/15, 로컬 CPU, `appendix/run_o1/`): 덕수궁 · 저유료 왕릉 5곳을 입력 · 채점에서 뺀 17곳. C3 6.733억 → B′(개소별 15%) 6.335(−0.398) · C(같은 날 3곳 이상) 6.393(−0.340). B′ 효과의 86% 가 공지 기간(10-30 ~ 11-09). Chronos-2 는 개소마다 따로 예측(23곳 · 17곳 입력 C3 의 q0.8 차이 최대 0.08명)
- 마지막 수요일 적중률(C3): 전날 0.485 · 1주 전 0.537 · 2주 전 0.515 · 3주 전 0.607 — 지평이 아니라 무료 효과 과소 추정(실제 ≈ 중앙값의 1.5배)
- 확정 시점 C3: 전날 8.46 · 1주 전 9.22 · 2주 전 9.44 · 3주 전 9.30억 (적중률 0.80 유지) = 4주 권고의 1~4주차 검증
- 왕릉 최소 1명: 직전 7일 평균 19.55 → C3 14.05억 (−5.50 = 보정 1.36 + 모형 4.13)

- [ ] 공지 확인: 2026-01-01 무료 여부, 궁능유적본부 공지 원문 URL
- [ ] `report.pdf` (report_draft.md 변환), `slides.pdf` (20분, 처음 3분에 권고 인원·절감액·가정 민감도)
- [ ] GitHub 공개 저장소 커밋·푸시 (API 키 없음, 데이터 출처 문장)
- [ ] 옛 설정 정리: `02_day2_models.ipynb`, `outputs/day2/` (옛 원점 26개)

---

## 9. 지난 실수·주의 (같은 실수 반복 금지)

- 예측 입력에 `paid` 기반 무료일 표시 금지(미래 `paid` 는 모름). 지난 날짜의 실제 무료 판정은 교안의 유료 비중 15% 미만 — `paid == 0` 아님(10/15 실수 5 셀이 `paid == 0` 으로 잘못 논증했다가 정정, `report/검토_무료개방일과_피처정의.md`). 설 전날처럼 `is_free_rule=1` 인데 유료가 많은 날이 있음 → 규칙이 실제 운영과 어긋나는 사례로 보고서에 기록.
- 교안 채점표는 "공휴일 없는 주 **2개**, 있는 주 **3개**" (반대로 말한 적 있음).
- H2 마지막 수요일은 5번(6번 아님). 종묘는 기간이 짧은 개소가 아님(잘못 말했다가 정정).
- 그림 제목 정정 사례: fig4 "절반 이하" 틀림, fig5 왕릉 주장 틀림, fig2 "가장 낮음"은 무료 O 주에서만 성립. → 제목은 항상 숫자로 확인.
- `outputs/day2/` 와 `02_day2_models.ipynb` 는 옛 설정(원점 26개, 비 5mm) 결과임.
- `summarize(by='origin')` 등 키 중복 시 단위 dedupe 가 필요 (이미 반영됨).
