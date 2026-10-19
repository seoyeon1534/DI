"""O1 — 보정 B 변형 재실행 (덕수궁 · 저유료 왕릉 5곳을 입력과 채점에서 모두 뺀 17곳)

    python tools/run_o1_ruleB_variants.py --device cpu
    python tools/run_o1_ruleB_variants.py --device cpu --limit 2      # 시험(원점 2개, 결과는 OUT/_test/)

검토 문서(report/검토_무료개방일과_피처정의.md) 2.6 · O1:
- 기존 보정 B 의 15% 판정 125 개소·일 중 96건이 덕수궁의 원인 모를 저유료 날이었다.
- 저유료 왕릉 5곳은 평소에도 유료 비중이 15% 미만이라 교안 정의로 무료일을 구분할 수 없다.

작업 (모두 17곳, 원점 52개, 전날 확정):
- c3_17     : C3 (기준)
- ruleB1_17 : C3 + extra_free B′ = 궁·종묘(덕수궁 제외)의 규칙 밖 개방일 중 유료 비중 < 15%  + 공지 기간(개방일만)
- ruleB2_17 : C3 + extra_free C  = B′ 중 같은 날 궁·종묘 3곳 이상이 함께 < 15% 인 날만  + 공지 기간(개방일만)
공지 기간 2025-10-30 ~ 11-09 은 기존 B 와 같고, 휴관일 표시 모순(기존 23건)을 없애려 개방일에만 붙인다.
기존 B 처럼 시험 구간(2025)에도 실제 paid 로 표시하므로 결과는 「공지를 모두 미리 알았다」는 상한이다.
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

EXCLUDE = ["덕수궁", "양주온릉", "정릉", "영휘원", "의릉", "홍유릉"]
NOTICE = ("2025-10-30", "2025-11-09")
BASE = ["is_holiday", "is_closed_weekday", "is_myeongjeol", "is_last_wednesday"]
JOBS = {  # 이름: (공변량, 설명)
    "c3_17": (BASE, "C3 (17곳)"),
    "ruleB1_17": (BASE + ["extra_free"], "C3 + 보정 B′ 덕수궁 제외 (17곳, 상한)"),
    "ruleB2_17": (BASE + ["extra_free"], "C3 + 보정 C 같은 날 3곳 이상 (17곳, 상한)"),
}


def build(hv):
    """17곳 패널과 변형별 extra_free 열(extra_free_b1, extra_free_b2)."""
    v, w, c, s = hv.load(ROOT / "raw")
    cal = hv.add_free_rule(hv.make_calendar())
    p = hv.build_panel(v, cal, s)
    p = p[~p["site"].isin(EXCLUDE)].reset_index(drop=True)
    is_open = p["status"] == "open"
    observed = (p["group"].isin(["궁", "종묘"]) & is_open & (p["is_free_rule"] == 0)
                & (p["date"] >= "2023-01-01") & (p["paid"] / p["total"] < 0.15))
    same_day = observed.groupby(p["date"]).transform("sum")
    notice = p["date"].between(*NOTICE) & is_open
    p["extra_free_b1"] = (observed | notice).astype(int)
    p["extra_free_b2"] = ((observed & (same_day >= 3)) | notice).astype(int)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--out", default=str(ROOT / "appendix" / "run_o1"))
    ap.add_argument("--jobs", nargs="*", default=None, help=f"일부만: {list(JOBS)}")
    ap.add_argument("--limit", type=int, default=None, help="원점 앞에서 N개만 (시험용)")
    args = ap.parse_args()

    import hv
    import dl
    out = Path(args.out) / ("_test" if args.limit else "")
    out.mkdir(parents=True, exist_ok=True)
    origins = hv.ORIGINS[: args.limit] if args.limit else hv.ORIGINS

    p = build(hv)
    print(f"개소 {p['site'].nunique()}곳 | 원점 {len(origins)}개 | 저장 {out}")
    for k in ["extra_free_b1", "extra_free_b2"]:
        print(f"{k}: {int(p[k].sum())} 개소·일 (공지 기간 제외 {int(p.loc[~p['date'].between(*NOTICE), k].sum())})", flush=True)

    t0 = time.time()
    for name in args.jobs or list(JOBS):
        covs, desc = JOBS[name]
        f = out / f"{name}.parquet"
        if f.exists():
            print(f"{name:10s} 있음 — 건너뜀", flush=True)
            continue
        col = {"ruleB1_17": "extra_free_b1", "ruleB2_17": "extra_free_b2"}.get(name)
        panel = p.assign(extra_free=p[col]) if col else p
        t = time.time()
        bt = dl.run_chronos(panel, origins=origins, covariates=covs, lead=1, name=desc, device=args.device)
        bt.assign(job=name).to_parquet(f)
        print(f"{name:10s} {time.time() - t:6.0f}s  ({desc})", flush=True)
    print(f"ALL DONE {(time.time() - t0) / 60:.1f}분", flush=True)


if __name__ == "__main__":
    main()
