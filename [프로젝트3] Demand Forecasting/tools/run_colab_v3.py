"""Chronos-2 추가 실행 (v3) — 최종 모형 C3 기준: FVA 한 칸씩 · 보정 규칙 A/B · 3·4주차 확정 시점

    python tools/run_colab_v3.py --device cuda --out /content/drive/MyDrive/heritage_colab/run_v3   # Colab T4
    python tools/run_colab_v3.py --device cpu --limit 1                                            # 로컬 시험(원점 1개)

작업마다 `OUT/<이름>.parquet` 하나. 있으면 건너뛰므로 끊겨도 다시 실행하면 이어서 돈다.
같은 장치에서 비교하려고 C1·C2·C3 도 다시 돌린다(GPU 는 CPU 와 소수점 아래가 조금 다를 수 있음).

공변량 (모두 확정일에 미리 아는 값 — df·future_df 양쪽에 넣는다)
- 보정 규칙 A: 명절 연휴 안의 위치 — `myeong_before`(당일 전) · `myeong_mid`(당일·다음날) · `myeong_late`(당일 +2일 이후).
  세 열의 합 = is_myeongjeol 이라 C3 의 is_myeongjeol 을 이 세 열로 바꾼다. 달력으로 미리 안다.
- 보정 규칙 B: `extra_free` 공지된 규칙 밖 무료 개방·행사일.
  과거 = 궁·종묘에서 실제로 무료였던 규칙 밖 개방일(유료 비중 < 15%, 지난 날이라 확정일에 앎),
  2025-10-30 ~ 11-09 = 궁능유적본부 무료 개방 공지(4대 궁·종묘·조선왕릉·세종대왕유적).
  ※ 「공지가 근무표 확정 전에 나왔다」고 가정한 결과 — 공지를 모으면 얻을 수 있는 효과의 상한.
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

BASE = ["is_holiday", "is_closed_weekday"]
POS = ["myeong_before", "myeong_mid", "myeong_late"]
JOBS = {  # 이름: (공변량, lead, 설명)
    "c1_zs": ([], 1, "C1 Chronos-2 제로샷"),
    "k1_closed": (["is_closed_weekday"], 1, "K1 + 정기 휴관"),
    "c2_hol": (BASE, 1, "C2 + 공휴일"),
    "k3_myeong": (BASE + ["is_myeongjeol"], 1, "K3 + 명절 연휴"),
    "c3_free": (BASE + ["is_myeongjeol", "is_last_wednesday"], 1, "C3 + 마지막 수요일 (최종 모형)"),
    "ruleA_pos": (BASE + POS + ["is_last_wednesday"], 1, "C3 + 보정 A: 명절 연휴 안 위치"),
    "ruleB_notice": (BASE + ["is_myeongjeol", "is_last_wednesday", "extra_free"], 1, "C3 + 보정 B: 공지된 무료·행사"),
    "ruleAB": (BASE + POS + ["is_last_wednesday", "extra_free"], 1, "C3 + 보정 A + B"),
    "c3_lead15": (BASE + ["is_myeongjeol", "is_last_wednesday"], 15, "C3 · 2주 일찍 확정 (3주차)"),
    "c3_lead22": (BASE + ["is_myeongjeol", "is_last_wednesday"], 22, "C3 · 3주 일찍 확정 (4주차)"),
}
NOTICE = ("2025-10-30", "2025-11-09")


def add_v3_covariates(panel, cal):
    """보정 규칙 A·B 공변량을 panel 에 붙인다."""
    import numpy as np
    import pandas as pd
    c = cal.set_index("date")
    off = c["seollal_offset"].fillna(c["chuseok_offset"])
    m = c["is_myeongjeol"] == 1
    pos = pd.DataFrame({"myeong_before": (m & (off < 0)), "myeong_mid": (m & off.between(0, 1)),
                        "myeong_late": (m & (off >= 2))}).astype(int)
    assert (pos.sum(axis=1) == c["is_myeongjeol"]).all(), "명절 위치 세 열의 합이 is_myeongjeol 과 다름"
    p = panel.drop(columns=[k for k in POS + ["extra_free"] if k in panel]).join(pos, on="date")
    observed = ((p["group"].isin(["궁", "종묘"])) & (p["status"] == "open") & (p["is_free_rule"] == 0)
                & (p["date"] >= "2023-01-01") & (p["paid"] / p["total"] < 0.15))
    notice = p["date"].between(*NOTICE)
    p["extra_free"] = (observed | notice).astype(int)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    ap.add_argument("--out", default=str(ROOT / "outputs" / "run_v3"))   # real_final/outputs/run_v3
    ap.add_argument("--jobs", nargs="*", default=None, help=f"일부만: {list(JOBS)}")
    ap.add_argument("--limit", type=int, default=None, help="원점 앞에서 N개만 (시험용, 결과는 OUT/_test/)")
    args = ap.parse_args()

    import torch
    import hv
    import dl
    device = ("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    if device == "cuda" and not torch.cuda.is_available():
        sys.exit("--device cuda 인데 GPU 가 없습니다 (Colab: 런타임 → 런타임 유형 변경 → T4 GPU)")
    out = Path(args.out) / ("_test" if args.limit else "")
    out.mkdir(parents=True, exist_ok=True)
    origins = hv.ORIGINS[: args.limit] if args.limit else hv.ORIGINS

    v, w, c, s = hv.load()
    assert hv.check_anchors(v, w, c)["일치"].all()
    cal = hv.add_free_rule(hv.make_calendar())
    panel = add_v3_covariates(hv.build_panel(v, cal, s), cal)
    print(f"device={device} | 원점 {len(origins)}개 | 저장 {out}")
    print("extra_free 개소·일:", int(panel["extra_free"].sum()), "| 명절 위치(전/당일·다음날/후반):",
          [int(panel.drop_duplicates('date')[k].sum()) for k in POS], flush=True)

    t0 = time.time()
    for name in args.jobs or list(JOBS):
        covs, lead, desc = JOBS[name]
        f = out / f"{name}.parquet"
        if f.exists():
            print(f"{name:14s} 있음 — 건너뜀", flush=True)
            continue
        t = time.time()
        bt = dl.run_chronos(panel, origins=origins, covariates=covs or False, lead=lead, name=desc, device=device)
        bt = bt.assign(job=name, lead=lead)
        bt.to_parquet(f)
        print(f"{name:14s} {time.time() - t:6.0f}s  ({desc})", flush=True)
    print(f"ALL DONE {(time.time() - t0) / 60:.1f}분", flush=True)


if __name__ == "__main__":
    main()
