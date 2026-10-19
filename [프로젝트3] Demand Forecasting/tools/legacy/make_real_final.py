"""real_final/ — 이 폴더 하나만 있으면 보고서 · 제언 · 표 · 그림 · 노트북을 모두 보고 실행할 수 있게 묶는다

    python tools/make_real_final.py

먼저 돌려 둘 것: make_final_bundle.py (final/data) · make_final_report.py (figures.pdf) · make_per_origin_table.py
원본(저장소 최상위의 report_draft.md, AI_CONTEXT.md, final/report/제언_가안.md)을 고친 뒤 다시 실행하면 real_final 이 새로 만들어진다.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RF = ROOT / "real_final"
if RF.exists():
    shutil.rmtree(RF)
for d in ["data", "raw", "src", "tools", "notebooks", "report/figures", "appendix/report_addons", "appendix/run_v2", "appendix/run_v3"]:
    (RF / d).mkdir(parents=True, exist_ok=True)


def cp(src, dst):
    shutil.copy2(ROOT / src, RF / dst)


# 1. 분석 데이터 · 원본 데이터 · 코드
for f in (ROOT / "final" / "data").iterdir():
    cp(f.relative_to(ROOT), f"data/{f.name}")
for f in ["heritage_visitors_daily.parquet", "weather_daily.parquet", "calendar_kr_2015_2025.csv", "sites.csv", "anchors.json"]:
    cp(f, f"raw/{f}")
cp("README.md", "raw/README_데이터.md")
for f in ["hv.py", "dl.py"]:
    cp(f"src/{f}", f"src/{f}")
for f in sorted((ROOT / "tools").glob("*.py")):
    cp(f.relative_to(ROOT), f"tools/{f.name}")

# 2. 부록 표 (보고서가 가리키는 파일)
for f in sorted((ROOT / "outputs" / "report_addons").iterdir()):
    if f.suffix in (".csv", ".md", ".zip"):
        cp(f.relative_to(ROOT), f"appendix/report_addons/{f.name}")
for f in sorted((ROOT / "outputs" / "run_v2").glob("*.csv")):
    cp(f.relative_to(ROOT), f"appendix/run_v2/{f.name}")
cp("outputs/run_v3/env.txt", "appendix/run_v3/env.txt")

# 3. 그림
for f in sorted((ROOT / "outputs" / "figures").glob("*.png")):
    cp(f.relative_to(ROOT), f"report/figures/{f.name}")
cp("final/report/figures.pdf", "report/figures.pdf")

# 4. 문서 — 경로를 real_final 기준으로
REPL = [("](outputs/figures/", "](figures/"), ("](../../outputs/figures/", "](figures/"),
        ("final/data/", "data/"), ("final/notebooks/", "notebooks/"), ("final/report/", "report/"),
        ("outputs/report_addons/", "appendix/report_addons/"), ("outputs/run_v2/", "appendix/run_v2/"),
        ("outputs/run_v3/", "appendix/run_v3/"), ("outputs/figures/", "report/figures/"), ("`final/data`", "`data/`")]
NOTE = "> real_final 판 — 본문의 파일 경로는 `real_final/` 기준이다(그림은 `report/figures/`).\n\n"


def doc(src, dst, note=True):
    t = (ROOT / src).read_text(encoding="utf-8")
    for a, b in REPL:
        t = t.replace(a, b)
    (RF / dst).write_text((NOTE if note else "") + t, encoding="utf-8")


doc("report_draft.md", "report/report.md")
doc("final/report/제언_가안.md", "report/제언_가안.md")
doc("AI_CONTEXT.md", "report/AI_CONTEXT.md")

(RF / "README.md").write_text("""# 궁·능 관람객 예측과 인력 배치 — real_final

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

## 폴더

```
real_final/
├── README.md            이 파일
├── report/              report.md · 제언_가안.md · AI_CONTEXT.md · figures.pdf · figures/ (그림 8장)
├── data/                분석 결과 5개 — backtests.parquet · metrics.csv · scenarios.csv · recommend_2026.csv · top10_shortage.csv
├── notebooks/           01 데이터·베이스라인 · 02 모형 비교·FVA·원점별 표 · 03 범주별·오차 · 04 비용·가정·확정 시점 · 05 2026 권고표
├── appendix/            보고서 부록이 가리키는 표 (report_addons/ · run_v2/ · run_v3/env.txt)
├── raw/                 원본 데이터 5개 + README_데이터.md (출처 · 주의 사항)
├── src/                 hv.py (전처리·백테스트·비용) · dl.py (MLP · Chronos-2)
└── tools/               결과를 만든 스크립트 (참고용 — 저장소 원래 구조에서 실행)
```

## 노트북 실행

| 노트북 | 필요한 것 |
|---|---|
| 02 ~ 05 | `data/` · 패키지 `pandas` `pyarrow` `matplotlib` |
| 01 | 위 + `src/` · `raw/` (모두 이 폴더에 있음) + `holidays==0.103` |

- 로컬: `notebooks/` 에서 열고 「모두 실행」. 첫 셀이 `데이터: …/real_final/data` 를 출력하면 정상.
- Colab: real_final 폴더를 통째로 올린 뒤(예: `/content/real_final`) 노트북을 열고 실행. 01 은 먼저 `!pip -q install "holidays==0.103"`. 그림 한글이 네모면 `!apt -qq install fonts-nanum` 후 런타임 다시 시작.
- 모델 재학습(MLP · Chronos-2)은 노트북에 없다 — 결과는 `data/backtests.parquet` 에 들어 있다. 다시 돌리려면 저장소 원래 구조에서 `tools/run_day2.py`(MLP) · `tools/run_colab_v3.py`(Chronos-2, Colab T4).

## 데이터 출처

> 본 저작물은 '국가유산청 궁능유적본부'에서 '2020～2026년' 작성하여 공공누리 제1유형으로 개방한 '국가유산청 궁능유적본부_4대궁 관람객 수 현황(작성자: 국가유산청 궁능유적본부 서비스기획과)'과 '국가유산청 궁능유적본부_조선왕릉 관람객 수 현황(작성자: 국가유산청 궁능유적본부 서비스기획과)'을 이용하였으며, 해당 저작물은 '공공데이터포털, https://www.data.go.kr/data/15040885/fileData.do · https://www.data.go.kr/data/15064582/fileData.do'에서 무료로 다운받으실 수 있습니다.

> The data was obtained from National Aeronautics and Space Administration (NASA) Langley Research Center's Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth Science Division. The data was obtained from the POWER Project's Daily 2.10.0 version on 2026/10/10.

개소 좌표 = 국가유산청 국가유산 검색 오픈API(조회 2026-10-10), 2026 공휴일 = Python `holidays` 0.103. 자세한 내용은 `raw/README_데이터.md`.
""", encoding="utf-8")

# 5. 노트북 생성 + 실행 (real_final/notebooks)
subprocess.run([sys.executable, str(ROOT / "tools" / "make_final_notebooks.py"), "real_final"], check=True)

size = sum(f.stat().st_size for f in RF.rglob("*") if f.is_file())
print(f"real_final: 파일 {sum(1 for f in RF.rglob('*') if f.is_file())}개 · {size / 1e6:.1f} MB")
