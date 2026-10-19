"""real_final 폴더 안의 경로 — 모든 스크립트가 이 폴더 하나로 돌도록 한곳에서 정한다.

raw/                     원본 데이터 (읽기 전용)
outputs/run_v2/          모형 원시 예측: MLP 전 변형 × 시드, Chronos-2 3종 (tools/run_day2.py)
outputs/run_v3/          모형 원시 예측: Chronos-2 FVA 한 칸씩 · 보정 A/B · 2·3주 전 확정 (tools/run_colab_v3.py)
appendix/report_addons/  보고서 보충 표 (make_report_addons · make_recommend_4w · make_report_extra · make_model_compare ·
                         make_site_scenarios · make_v3_results · make_per_origin_table)
appendix/run_v2/         교안 형식 채점표 (make_scoring_tables)
appendix/run_v3/         Chronos-2 v3 실행 환경 기록
appendix/run_o1/         보정 B 변형 17곳 (run_o1_ruleB_variants · score_o1)
report/figures/          그림 8장 · report/figures.pdf (make_figures)
data/                    분석 결과 5개 (make_final_bundle)
notebooks/               노트북 01~05 (make_final_notebooks)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
WORK = ROOT / "outputs"
RUN_V2 = WORK / "run_v2"
RUN_V3 = WORK / "run_v3"
APPX = ROOT / "appendix"
ADD = APPX / "report_addons"
TAB_V2 = APPX / "run_v2"
ENV_V3 = APPX / "run_v3"
RUN_O1 = APPX / "run_o1"
REPORT = ROOT / "report"
FIG = REPORT / "figures"
DATA = ROOT / "data"
NB = ROOT / "notebooks"
