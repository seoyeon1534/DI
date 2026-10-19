"""final/report/ — 보고서 · AI 맥락 사본 + 그림 8장을 PDF 하나로

    python tools/make_final_report.py

원본은 루트의 report_draft.md, AI_CONTEXT.md, outputs/figures/. 원본을 고친 뒤 다시 실행하면 사본이 갱신된다.
"""
import shutil
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "final" / "report"
OUT.mkdir(parents=True, exist_ok=True)

# 보고서: 그림 · 파일 경로를 final/report/ 기준으로
txt = (ROOT / "report_draft.md").read_text(encoding="utf-8")
txt = txt.replace("](outputs/", "](../../outputs/")
head = "> 사본 — 원본은 저장소 최상위 `report_draft.md`. 본문의 `outputs/...` 경로는 저장소 최상위 기준이다.\n\n"
(OUT / "report.md").write_text(head + txt, encoding="utf-8")
shutil.copy(ROOT / "AI_CONTEXT.md", OUT / "AI_CONTEXT.md")

figs = sorted((ROOT / "outputs" / "figures").glob("fig*.png"))
with PdfPages(OUT / "figures.pdf") as pdf:
    for f in figs:
        img = plt.imread(f)
        h, w = img.shape[:2]
        fig = plt.figure(figsize=(11.69, 11.69 * h / w))
        ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(img); ax.axis("off")
        pdf.savefig(fig, dpi=200); plt.close(fig)
print("report.md, AI_CONTEXT.md, figures.pdf (", len(figs), "장 )")
