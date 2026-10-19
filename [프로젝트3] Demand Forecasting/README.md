# 궁·능 관람객 예측과 인력 배치 — real_final

> **이 폴더 하나로 전부 볼 수 있다.** 보고서 · 제언 · 그림 · 표 · 노트북(실행 결과 포함) · 원본 데이터 · 코드.
> **주제**: 무료 개방일·명절에 개소마다 인력을 평소의 몇 배로 늘려야 하는가
> **결론**: Chronos-2 + 공휴일·무료 개방(C3)의 0.8 분위수 ÷ 2,000명으로 배치하면 2025년 백테스트 비용이 직전 7일 평균보다 **14.86억 → 8.46억(−6.40억)**, 팀 규칙(왕릉 하루 최소 1명)을 양쪽에 넣으면 **19.55억 → 14.05억(−5.50억)**.
> 확정(2026-10-15): 최종 모형 C3 · 권고 4주(2026-01-01 ~ 01-28) · 왕릉 최소 1명 · 매주 화요일 다음 1주 재확정.

## 어디부터 볼까

| 순서 | 파일 | 내용 |
|---|---|---|
| 1 | `report/report.md` | **보고서** (가이드 ①~⑥ + 부록, 의사결정 기록 28개). 그림은 `report/figures/` |
| 2 | `report/제언_가안.md` | 운영팀 제언 9개 (가안) · 출처 밝히며 해석하는 법 · 무료 개방·행사 외부 출처 |
| 3 | `notebooks/02 ~ 05` | 표 · 그림을 `data/` 에서 다시 만든다 (실행 결과가 이미 들어 있어 열기만 해도 보임) |
| 4 | `report/figures.pdf` | 그림 8장 모음 |
| — | `report/AI_CONTEXT.md` | AI 에게 붙여 넣는 프로젝트 맥락 (지시 프롬프트 + 파일 목록) |
| — | `report/검토_무료개방일과_피처정의.md` | 10/15 검토 기록 — 무료 개방일 정의의 쓰임, 보정 A · B, 피처 · 공변량 전체 정의와 이유 |

## 폴더

```
real_final/
├── README.md            이 파일
├── report/              report.md · 제언_가안.md · AI_CONTEXT.md · 검토_무료개방일과_피처정의.md · figures.pdf · figures/ (그림 8장)
├── data/                분석 결과 5개 — backtests.parquet · metrics.csv · scenarios.csv · recommend_2026.csv · top10_shortage.csv
├── notebooks/           01 데이터·베이스라인 · 02 모형 비교·FVA·원점별 표 · 03 범주별·오차 · 04 비용·가정·확정 시점 · 05 2026 권고표
├── appendix/            보고서 부록이 가리키는 표 (report_addons/ · run_v2/ · run_v3/env.txt · run_o1/ 보정 B 변형 17곳)
├── raw/                 원본 데이터 5개 + README_데이터.md (출처 · 주의 사항)
├── src/                 hv.py (전처리·백테스트·비용) · dl.py (MLP · Chronos-2) · paths.py (폴더 경로)
├── tools/               결과를 만드는 스크립트 — 이 폴더 안에서 돈다 (`run_all.py` 가 전체 순서, `legacy/` 는 옛 스크립트 보관)
└── outputs/             (다시 돌리면 생김) 모형 원시 예측 run_v2/ · run_v3/ 와 실행 로그 logs/
```

## 노트북 실행

| 노트북 | 필요한 것 |
|---|---|
| 02 ~ 05 | `data/` · 패키지 `pandas` `pyarrow` `matplotlib` |
| 01 | 위 + `src/` · `raw/` (모두 이 폴더에 있음) + `holidays==0.103` |

- 로컬: `notebooks/` 에서 열고 「모두 실행」. 첫 셀이 `데이터: …/real_final/data` 를 출력하면 정상.
- Colab: real_final 폴더를 통째로 올린 뒤(예: `/content/real_final`) 노트북을 열고 실행. 01 은 먼저 `!pip -q install "holidays==0.103"`. 그림 한글이 네모면 `!apt -qq install fonts-nanum` 후 런타임 다시 시작.
- 모델 재학습(MLP · Chronos-2)은 노트북에 없다 — 결과는 `data/backtests.parquet` 에 들어 있다. 다시 만들려면 아래 「전체 다시 만들기」.

## 전체 다시 만들기 (이 폴더만으로)

```
pip install pandas pyarrow matplotlib "holidays==0.103" torch chronos-forecasting nbformat nbclient ipykernel
python tools/run_all.py                  # raw/ → 모형 예측 → 표 · 그림 · data/ · 노트북 (로컬 CPU 약 5 ~ 6시간)
python tools/run_all.py --skip-models    # outputs/ 에 모형 예측이 있으면 표부터 (약 40분)
python tools/run_all.py --from make_figures
```

| 단계 | 스크립트 | 만드는 것 | CPU 시간(18코어) |
|---|---|---|---|
| 모형 | `run_day2` | MLP 8변형 × 시드 5 + Chronos-2 3종 → `outputs/run_v2/` | 약 80분 |
| 모형 | `run_colab_v3` | Chronos-2 FVA 한 칸씩 · 보정 A/B · 2·3주 전 확정 → `outputs/run_v3/` | 약 150분 |
| 모형 | `run_o1_ruleB_variants` | 보정 B 변형 17곳 → `appendix/run_o1/` | 약 40분 |
| 표 | `make_report_addons` ~ `make_scoring_tables` (7개) | `appendix/report_addons/` · `appendix/run_v2/` | 약 30분 (Chronos 2회 포함) |
| 그림 | `make_figures` | `report/figures/` 8장 · `report/figures.pdf` | 2분 |
| 결과 | `make_final_bundle` · `make_per_origin_table` · `score_o1` | `data/` 5개 · 원점별 표 · 보정 B 변형 표 | 약 10분 |
| 노트북 | `make_final_notebooks` | `notebooks/` 01 ~ 05 (실행 결과 포함) | 약 3분 |

- 모형 단계는 결과 파일이 있으면 건너뛴다 — 중간에 끊겨도 같은 명령으로 이어서 돈다. 로그는 `outputs/logs/`.
- 2026-10-15 이 순서로 전부 다시 돌려 기존 결과와 같은 숫자를 확인했다(Chronos-2 는 Colab T4 결과와 소수 넷째 자리까지 같음).
- GPU 로 모형만 돌리려면 `python tools/make_colab_bundle_v3.py` → `outputs/heritage_colab_v3.zip` 을 Colab T4 에서 실행하고 결과를 `outputs/run_v3/` 에 푼다.

## 데이터 출처

> 본 저작물은 '국가유산청 궁능유적본부'에서 '2020～2026년' 작성하여 공공누리 제1유형으로 개방한 '국가유산청 궁능유적본부_4대궁 관람객 수 현황(작성자: 국가유산청 궁능유적본부 서비스기획과)'과 '국가유산청 궁능유적본부_조선왕릉 관람객 수 현황(작성자: 국가유산청 궁능유적본부 서비스기획과)'을 이용하였으며, 해당 저작물은 '공공데이터포털, https://www.data.go.kr/data/15040885/fileData.do · https://www.data.go.kr/data/15064582/fileData.do'에서 무료로 다운받으실 수 있습니다.

> The data was obtained from National Aeronautics and Space Administration (NASA) Langley Research Center's Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth Science Division. The data was obtained from the POWER Project's Daily 2.10.0 version on 2026/10/10.

개소 좌표 = 국가유산청 국가유산 검색 오픈API(조회 2026-10-10), 2026 공휴일 = Python `holidays` 0.103. 자세한 내용은 `raw/README_데이터.md`.
