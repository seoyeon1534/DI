"""Colab 실행용 zip 만들기 → outputs/heritage_colab.zip

zip 안: src/ · tools/ · 데이터 5개 · colab_run.ipynb · README_colab.md
"""
import zipfile
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s.strip()))
code = lambda s: cells.append(nbf.v4.new_code_cell(s.strip()))

md("""
# 궁·능 관람객 — MLP · Chronos-2 백테스트 (Colab T4)

**사용법**
1. 메뉴 **런타임 → 런타임 유형 변경 → T4 GPU**
2. `heritage_colab.zip` 을 구글 드라이브 **`내 드라이브/heritage_colab/`** 폴더에 올린다 (없으면 4번 셀에서 직접 업로드)
3. **런타임 → 모두 실행**

- 결과는 드라이브 `heritage_colab/run_v2/` 에 저장된다. 세션이 끊기면 **모두 실행을 다시 누르면 이어서** 돈다(끝난 부분은 건너뜀).
- 끝나면 마지막 셀이 `run_v2_results.zip` 을 내려받는다 → 원래 PC 의 `outputs/run_v2/` 에 풀면 된다.
""")
code("""
# T4 GPU 확인 — 없으면 여기서 멈춘다(런타임 → 런타임 유형 변경 → T4 GPU 후 다시 「모두 실행」)
import torch
assert torch.cuda.is_available(), 'GPU 가 없습니다. 런타임 → 런타임 유형 변경 → T4 GPU 로 바꾼 뒤 다시 실행하세요.'
print('GPU:', torch.cuda.get_device_name(0))
if 'T4' not in torch.cuda.get_device_name(0):
    print('※ T4 가 아닌 GPU 입니다. 돌아가긴 하지만 시간 예상이 달라집니다.')
""")
code("""
from google.colab import drive
drive.mount('/content/drive')
import os
WORK = '/content/drive/MyDrive/heritage_colab'
os.makedirs(WORK, exist_ok=True)
print('작업 폴더:', WORK)
""")
code("""
# zip 찾기 → 없으면 업로드 → /content/heritage 에 풀기
import glob, shutil, zipfile
zips = sorted(glob.glob(f'{WORK}/heritage_colab*.zip'))
if not zips:
    from google.colab import files
    up = files.upload()                       # heritage_colab.zip 선택
    name = next(iter(up))
    shutil.copy(name, f'{WORK}/{name}')
    zips = [f'{WORK}/{name}']
shutil.rmtree('/content/heritage', ignore_errors=True)
zipfile.ZipFile(zips[-1]).extractall('/content/heritage')
os.chdir('/content/heritage')
print('사용한 zip:', zips[-1]); print(sorted(os.listdir('.')))
""")
code("""
!pip -q install chronos-forecasting "holidays==0.103"
import pandas, numpy, torch, holidays, chronos
print('pandas', pandas.__version__, '| numpy', numpy.__version__, '| torch', torch.__version__,
      '| cuda', torch.cuda.is_available(), '| holidays', holidays.__version__, '| chronos', getattr(chronos, '__version__', '?'))
""")
code("""
# 검산 7개 — 하나라도 False 면 멈춘다
import sys; sys.path.insert(0, 'src')
import hv
v, w, c, s = hv.load()
chk = hv.check_anchors(v, w, c); print(chk)
assert chk['일치'].all()
""")
code("""
# GPU 한 번 학습 시간 확인 (참고)
import time, dl
cal = hv.add_free_rule(hv.make_calendar()); p = hv.build_panel(v, cal, s); A = dl.Arrays(p, cal, w, s)
dl.fit_predict_mlp(A, hv.ORIGINS[0], feats=dl.FEATURE_SETS['past'], seed=0, device='cuda')   # GPU 예열
t = time.time(); dl.fit_predict_mlp(A, hv.ORIGINS[0], feats=dl.FEATURE_SETS['+lastwed'], seed=0, device='cuda')
sec = time.time() - t
print(f'GPU({torch.cuda.get_device_name(0)}) 한 번 {sec:.1f}초 → MLP 2,080회 약 {sec * 2080 / 60:.0f}분 예상 (+ Chronos-2 3종 몇 분)')
""")
code("""
# 본 실행 — 끊기면 이 셀부터 다시 실행해도 이어서 돈다
!python tools/run_day2.py --device cuda --out "{WORK}/run_v2"
""")
code("""
# 실행 환경 기록(보고서 재현 조건용) + 결과 zip 내려받기
import platform, subprocess
env = (f"python {platform.python_version()}\\n"
       + subprocess.run(['pip', 'show', 'torch', 'chronos-forecasting', 'pandas', 'numpy', 'holidays'],
                        capture_output=True, text=True).stdout
       + subprocess.run(['nvidia-smi', '-L'], capture_output=True, text=True).stdout)
open(f'{WORK}/run_v2/env.txt', 'w').write(env)
out = shutil.make_archive('/content/run_v2_results', 'zip', f'{WORK}/run_v2')
from google.colab import files
files.download(out)
""")

nb = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"name": "python3", "display_name": "Python 3"},
    "accelerator": "GPU", "colab": {"gpuType": "T4", "provenance": []}})

readme = """# Colab 실행 안내

1. Colab(https://colab.research.google.com) → 파일 → 노트북 업로드 → zip 안의 `colab_run.ipynb`
   (또는 zip 을 풀지 말고 드라이브에 올린 뒤, 노트북만 따로 열어도 됨)
2. 런타임 → 런타임 유형 변경 → **T4 GPU** (안 바꾸면 첫 셀에서 멈춤)
3. `heritage_colab.zip` 을 구글 드라이브 `내 드라이브/heritage_colab/` 에 올림 (안 올리면 실행 중에 업로드 창이 뜸)
4. 런타임 → 모두 실행. 드라이브 접근 허용 창이 뜨면 허용
5. 끝나면 `run_v2_results.zip` 이 내려받아짐 → 원래 PC 의 `outputs/run_v2/` 에 풀기 → `python tools/make_scoring_nb.py`

- 세션이 끊겨도 「모두 실행」 을 다시 누르면 끝난 부분은 건너뛰고 이어서 돈다 (결과는 드라이브 `heritage_colab/run_v2/`)
- 계산량: MLP 8변형 × 시드 5 × 원점 52 = 2,080회 + Chronos-2 3종. 예상 시간은 6번 셀이 알려 줌
- GPU 는 결과 숫자를 CPU 와 소수점 아래에서 조금 다르게 낼 수 있음 → `run_v2/env.txt` 를 보고서 재현 조건에 적기
"""

files = ["src/hv.py", "src/dl.py", "tools/run_day2.py", "tools/make_scoring_nb.py",
         "heritage_visitors_daily.parquet", "weather_daily.parquet", "calendar_kr_2015_2025.csv",
         "sites.csv", "anchors.json"]
dst = ROOT / "outputs" / "heritage_colab.zip"
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(ROOT / f, f)
    z.writestr("colab_run.ipynb", nbf.writes(nb))
    z.writestr("README_colab.md", readme)
nbf.write(nb, ROOT / "colab_run.ipynb")
print(dst, round(dst.stat().st_size / 1e6, 2), "MB")
for i in zipfile.ZipFile(dst).infolist():
    print(f"  {i.filename:40s} {i.file_size:>10,}")
