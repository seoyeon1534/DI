"""real_final 전체를 이 폴더 안에서 다시 만든다 — 원본 데이터(raw/) → 모형 예측 → 표 · 그림 · data/ · 노트북

    python tools/run_all.py                    # 전부 (CPU 약 5 ~ 6시간, 대부분 모형)
    python tools/run_all.py --skip-models      # 모형 예측(outputs/)이 있으면 표부터 (약 40분 — Chronos 2회 포함)
    python tools/run_all.py --from make_figures
    python tools/run_all.py --only make_final_bundle make_final_notebooks

모형 단계는 결과 파일이 있으면 건너뛴다(이어서 돌리기). 처음부터 다시 돌리려면 outputs/ 를 지운다.
로그: outputs/logs/<단계>.log
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = [  # (이름, 인자, 모형 단계인가, 하는 일)
    ("run_day2", ["--device", "cpu", "--workers", "8"], True, "MLP 전 변형 × 시드 0~4 + Chronos-2 3종 → outputs/run_v2/"),
    ("run_colab_v3", ["--device", "cpu"], True, "Chronos-2 FVA 한 칸씩 · 보정 A/B · 2·3주 전 확정 → outputs/run_v3/"),
    ("run_o1_ruleB_variants", [], True, "보정 B 변형 17곳 → appendix/run_o1/"),
    ("make_report_addons", [], False, "2026 1주 권고 · 1주 전 확정(Chronos) · 가정 바꾸기 · 유형별 · 부족 10건"),
    ("make_recommend_4w", [], False, "2026 4주 권고 (Chronos 28일)"),
    ("make_report_extra", [], False, "날짜 유형별 · 실수 4 · 5"),
    ("make_model_compare", [], False, "전 방식 비교 → compare_all.zip"),
    ("make_site_scenarios", [], False, "가정 바꾸기 개소별"),
    ("make_v3_results", [], False, "v3 결과 표 (FVA · 보정 · 확정 시점 · 최소 인원)"),
    ("make_scoring_tables", [], False, "교안 형식 채점표 → appendix/run_v2/"),
    ("make_figures", [], False, "그림 8장 + figures.pdf → report/"),
    ("make_final_bundle", [], False, "data/ 5개"),
    ("make_per_origin_table", [], False, "원점별 표"),
    ("score_o1", [], False, "보정 B 변형 채점"),
    ("make_final_notebooks", [], False, "notebooks/ 01 ~ 05 생성 · 실행"),
]
NAMES = [s[0] for s in STEPS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-models", action="store_true", help="모형 단계(run_*)를 건너뜀")
    ap.add_argument("--from", dest="start", choices=NAMES, help="이 단계부터")
    ap.add_argument("--only", nargs="+", choices=NAMES, help="이 단계들만")
    args = ap.parse_args()

    steps = STEPS
    if args.start:
        steps = steps[NAMES.index(args.start):]
    if args.only:
        steps = [s for s in steps if s[0] in args.only]
    if args.skip_models:
        steps = [s for s in steps if not s[2]]
    logs = ROOT / "outputs" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for name, extra, _, what in steps:
        t = time.time()
        print(f"▶ {name:24s} {what}", flush=True)
        with open(logs / f"{name}.log", "w", encoding="utf-8") as log:
            r = subprocess.run([sys.executable, str(ROOT / "tools" / f"{name}.py"), *extra], cwd=ROOT,
                               stdout=log, stderr=subprocess.STDOUT, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
        print(f"  {'완료' if r.returncode == 0 else '실패'} {(time.time() - t) / 60:.1f}분", flush=True)
        if r.returncode != 0:
            sys.exit(f"{name} 실패 — outputs/logs/{name}.log 확인")
    print(f"전체 {(time.time() - t0) / 60:.1f}분", flush=True)


if __name__ == "__main__":
    main()
