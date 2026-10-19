"""Colab T4 실행 세트 v3 → outputs/heritage_colab_v3.zip (+ outputs/colab_run_v3.ipynb) — 로컬 CPU 대신 Colab 으로 돌릴 때만

zip 안: src/ · tools/run_colab_v3.py · 데이터 5개 · colab_run_v3.ipynb · README_colab_v3.md
실행 내용: Chronos-2 10회 (FVA 한 칸씩 5 · 보정 규칙 A/B/A+B 3 · 3·4주 전 확정 2) — tools/run_colab_v3.py 참고
"""
import zipfile
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s.strip()))
code = lambda s: cells.append(nbf.v4.new_code_cell(s.strip()))

md("""
# 궁·능 관람객 — Chronos-2 추가 실행 v3 (Colab T4)

최종 모형 **C3 (Chronos-2 + 공휴일·무료 개방)** 기준으로 남은 계산 10회:

| 묶음 | 작업 | 보고서에서 쓰는 곳 |
|---|---|---|
| FVA 한 칸씩 (가이드 요구사항 6) | C1 제로샷 → K1 + 정기 휴관 → C2 + 공휴일 → K3 + 명절 연휴 → C3 + 마지막 수요일 | ④ FVA 표 (최종 모형) |
| 보정 규칙 (요구사항 7) | C3 + A 명절 연휴 안 위치 · C3 + B 공지된 무료·행사 · C3 + A + B | ⑤ 보정 규칙 전후 비용 |
| 확정 시점 (요구사항 8, 4주 권고) | C3 2주 일찍 · 3주 일찍 확정 (4주 예측의 3·4주차) | ④ 확정 시점별 비용 |

**사용법**
1. 메뉴 **런타임 → 런타임 유형 변경 → T4 GPU**
2. `heritage_colab_v3.zip` 을 구글 드라이브 **`내 드라이브/heritage_colab/`** 에 올린다 (안 올리면 3번 셀에서 업로드 창이 뜬다)
3. **런타임 → 모두 실행** — 드라이브 접근 허용

- 결과는 드라이브 `heritage_colab/run_v3/` 에 작업마다 파일 하나. 끊기면 **모두 실행을 다시** 누르면 끝난 작업은 건너뛴다.
- 마지막 셀이 `run_v3_results.zip` 을 내려받는다 → 원래 PC 의 `outputs/run_v3/` 에 풀기.
""")
code("""
# 1. T4 GPU 확인 — 없으면 멈춘다
import torch
assert torch.cuda.is_available(), 'GPU 가 없습니다. 런타임 → 런타임 유형 변경 → T4 GPU 로 바꾼 뒤 다시 「모두 실행」.'
print('GPU:', torch.cuda.get_device_name(0))
if 'T4' not in torch.cuda.get_device_name(0):
    print('※ T4 가 아닌 GPU 입니다. 결과는 같지만 시간이 다를 수 있습니다.')
""")
code("""
# 2. 드라이브 연결
from google.colab import drive
drive.mount('/content/drive')
import os
WORK = '/content/drive/MyDrive/heritage_colab'
os.makedirs(WORK, exist_ok=True)
print('작업 폴더:', WORK)
""")
code("""
# 3. zip 찾기 → 없으면 업로드 → /content/heritage 에 풀기
import glob, shutil, zipfile
zips = sorted(glob.glob(f'{WORK}/heritage_colab_v3*.zip'))
if not zips:
    from google.colab import files
    up = files.upload()                       # heritage_colab_v3.zip 선택
    name = next(iter(up))
    shutil.copy(name, f'{WORK}/{name}')
    zips = [f'{WORK}/{name}']
shutil.rmtree('/content/heritage', ignore_errors=True)
zipfile.ZipFile(zips[-1]).extractall('/content/heritage')
os.chdir('/content/heritage')
print('사용한 zip:', zips[-1]); print(sorted(os.listdir('.')))
""")
code("""
# 4. 패키지 (로컬과 같은 판: chronos-forecasting 2.3.2, holidays 0.103)
!pip -q install "chronos-forecasting==2.3.2" "holidays==0.103"
import pandas, numpy, holidays, importlib.metadata as im
print('pandas', pandas.__version__, '| numpy', numpy.__version__, '| torch', torch.__version__,
      '| holidays', holidays.__version__, '| chronos', im.version('chronos-forecasting'))
""")
code("""
# 5. 시험 — 원점 1개로 10개 작업이 도는지 (1~2분). 결과는 run_v3/_test/ (본 결과와 섞이지 않음)
!python tools/run_colab_v3.py --device cuda --limit 1 --out "{WORK}/run_v3"
""")
code("""
# 6. 본 실행 — 원점 52개 × 10개 작업. 끊기면 이 셀부터 다시 실행해도 이어서 돈다
!python tools/run_colab_v3.py --device cuda --out "{WORK}/run_v3"
""")
code("""
# 7. 확인 + 실행 환경 기록 + 결과 zip 내려받기
import pandas as pd, platform, subprocess
R = f'{WORK}/run_v3'
done = sorted(f for f in os.listdir(R) if f.endswith('.parquet'))
print(len(done), '개:', done)
assert len(done) == 10, '10개가 아닙니다 — 6번 셀을 다시 실행하세요'
for f in done:
    d = pd.read_parquet(f'{R}/{f}'); print(f'{f:22s} 원점 {d.origin.nunique():2d}개 · 행 {len(d):,}')
env = (f"python {platform.python_version()}\\n"
       + subprocess.run(['pip', 'show', 'torch', 'chronos-forecasting', 'pandas', 'numpy', 'holidays'],
                        capture_output=True, text=True).stdout
       + subprocess.run(['nvidia-smi', '-L'], capture_output=True, text=True).stdout)
open(f'{R}/env.txt', 'w').write(env)
shutil.rmtree(f'{R}/_test', ignore_errors=True)
out = shutil.make_archive('/content/run_v3_results', 'zip', R)
from google.colab import files
files.download(out)
""")

nb = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"name": "python3", "display_name": "Python 3"},
    "accelerator": "GPU", "colab": {"gpuType": "T4", "provenance": []}})

readme = """# Colab T4 실행 안내 (v3)

1. https://colab.research.google.com → 파일 → 노트북 업로드 → zip 안의 `colab_run_v3.ipynb`
2. 런타임 → 런타임 유형 변경 → **T4 GPU** (안 바꾸면 1번 셀에서 멈춤)
3. `heritage_colab_v3.zip` 을 구글 드라이브 `내 드라이브/heritage_colab/` 에 올림 (안 올리면 실행 중 업로드 창)
4. 런타임 → 모두 실행 → 드라이브 접근 허용
5. 끝나면 `run_v3_results.zip` 이 내려받아짐 → 원래 PC 의 `outputs/run_v3/` 에 풀기 → `python tools/make_v3_results.py`

- 계산량: Chronos-2 10회 × 원점 52개 (학습 없음). 5번 셀(원점 1개 시험)이 CPU 에서 2.6분 — T4 는 더 빠르다
- 끊겨도 「모두 실행」 을 다시 누르면 끝난 작업은 건너뜀 (결과: 드라이브 `heritage_colab/run_v3/`)
- 보정 규칙 B 는 「공지가 근무표 확정 전에 나왔다」고 가정한 결과(상한)
"""

files = ["src/hv.py", "src/dl.py", "src/paths.py", "tools/run_colab_v3.py",   # hv.load() 기본 경로 = raw/
         "raw/heritage_visitors_daily.parquet", "raw/weather_daily.parquet", "raw/calendar_kr_2015_2025.csv",
         "raw/sites.csv", "raw/anchors.json"]
dst = ROOT / "outputs" / "heritage_colab_v3.zip"
dst.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(ROOT / f, f)
    z.writestr("colab_run_v3.ipynb", nbf.writes(nb))
    z.writestr("README_colab_v3.md", readme)
nbf.write(nb, ROOT / "outputs" / "colab_run_v3.ipynb")
print(dst, round(dst.stat().st_size / 1e6, 2), "MB")
for i in zipfile.ZipFile(dst).infolist():
    print(f"  {i.filename:40s} {i.file_size:>10,}")
