# tools/legacy — 이 폴더 기준으로는 돌지 않는 옛 스크립트

원래 저장소 구조(`outputs/day1` · `outputs/day2` · `final/` · 최상위 `report_draft.md` · `전처리.md` 등)를 전제로 한 스크립트다. 기록용으로만 남긴다.

| 파일 | 하던 일 | 지금 대신하는 것 |
|---|---|---|
| `make_day1_nb.py` | 01_day1_baseline.ipynb (기준선 · 서비스 수준 보정 설정 고르기 · 규칙 검증) | `notebooks/01` · `tools/make_final_notebooks.py` |
| `make_day2_nb.py` | 02_day2_models.ipynb (옛 설정: 원점 26개, 비 5mm) | 쓰지 않음 |
| `make_scoring_nb.py` | 03_scoring.ipynb + `run_v2` 채점표 | `tools/make_scoring_tables.py` (표만) |
| `make_colab_bundle.py` | Colab v1 실행 세트 (run_day2) | 로컬 CPU 실행 (`tools/run_day2.py`) |
| `make_preprocessed.py` | `전처리.md` 코드 실행 → 전처리 패널 CSV | `src/hv.py` `build_panel` |
| `make_real_final.py` | 원래 저장소에서 real_final 폴더를 복사해 만듦 | 이 폴더가 원본 (`tools/run_all.py`) |
| `make_final_report.py` | report_draft.md · AI_CONTEXT.md 사본 + figures.pdf | 문서는 `report/` 가 원본, figures.pdf 는 `tools/make_figures.py` |
