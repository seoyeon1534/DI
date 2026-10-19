"""글로벌 MLP(FVA 변형 × 시드 0~4 × 원점 hv.ORIGINS) + Chronos-2 3종(제로샷 / + 공휴일 / + 공휴일·무료 개방)

    python tools/run_day2.py                       # GPU 가 있으면 GPU 로 한 프로세스, 없으면 CPU 8 프로세스
    python tools/run_day2.py --device cpu --workers 8
    python tools/run_day2.py --out /content/drive/MyDrive/heritage_run   # Colab: 드라이브에 저장(끊겨도 이어서)

- 이어서 돌리기: (변형, 시드) 하나(원점 52개)가 끝날 때마다 `OUT/parts/` 에 저장하고, 다시 실행하면 있는 것은 건너뛴다.
  Chronos-2 도 파일이 있으면 건너뛴다. 끝나면 `OUT/mlp_raw.parquet` 로 합친다.
- CPU 병렬: 워커마다 numpy·MKL·torch 스레드를 2개로 묶는다. 묶지 않으면 프로세스마다 모든 코어를 쓰려다
  서로 뺏어 한 번 학습이 3~5초 → 약 47초로 느려진다(10/13 실행). 18코어 PC 에서 8 × 2 로 2,080회 약 35분.
"""
import os

THREADS = 2
for _k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_k, str(THREADS))   # numpy 를 import 하기 전에 정해야 한다

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_A = None


def _load_arrays():
    import hv, dl
    v, w, c, s = hv.load()
    cal = hv.add_free_rule(hv.make_calendar())
    p = hv.build_panel(v, cal, s)
    return p, dl.Arrays(p, cal, w, s)


def _init():
    global _A
    import torch
    torch.set_num_threads(THREADS)
    _, _A = _load_arrays()


def _unit(args):
    """(변형, 시드) 하나 = 원점 52개 학습·예측."""
    import pandas as pd
    import hv, dl
    variant, seed, device = args
    out = []
    for o in hv.ORIGINS:
        f = dl.fit_predict_mlp(_A, o, feats=dl.FEATURE_SETS[variant], seed=seed, device=device)
        f["seed"], f["variant"] = seed, variant
        out.append(f)
    return variant, seed, pd.concat(out, ignore_index=True)


def _part_path(parts, variant, seed):
    safe = "".join(ch if ch.isalnum() else "_" for ch in variant)
    return parts / f"{safe}__seed{seed}.parquet"


def main():
    global _A
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    ap.add_argument("--workers", type=int, default=8, help="CPU 일 때 프로세스 수(코어 수 ÷ 2 권장). GPU 면 1 로 고정")
    ap.add_argument("--out", default=str(ROOT / "outputs" / "run_v2"))   # real_final/outputs/run_v2
    ap.add_argument("--variants", nargs="*", default=None, help="일부 FVA 변형만 (기본: 전부)")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--skip-chronos", action="store_true")
    args = ap.parse_args()

    import pandas as pd
    import torch
    import hv, dl

    device = ("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    if device == "cuda":
        if not torch.cuda.is_available():
            sys.exit("--device cuda 인데 GPU 가 없습니다 (Colab: 런타임 → 런타임 유형 변경 → T4 GPU)")
        print("GPU:", torch.cuda.get_device_name(0), flush=True)
    out = Path(args.out); parts = out / "parts"; parts.mkdir(parents=True, exist_ok=True)
    variants = args.variants or list(dl.FEATURE_SETS)
    units = [(vn, sd) for vn in variants for sd in range(args.seeds)]
    todo = [(vn, sd) for vn, sd in units if not _part_path(parts, vn, sd).exists()]
    print(f"device={device} | 원점 {len(hv.ORIGINS)}개 | (변형, 시드) {len(units)}개 중 남은 것 {len(todo)}개 | 저장 {out}", flush=True)

    t = time.time()
    done = 0

    def save(vn, sd, df):
        nonlocal done
        df.to_parquet(_part_path(parts, vn, sd))
        done += 1
        el = time.time() - t
        print(f"MLP {done}/{len(todo)}  {vn} seed{sd}  {el / 60:.1f}분 경과, 남은 예상 {el / done * (len(todo) - done) / 60:.0f}분", flush=True)

    if todo:
        if device == "cuda" or args.workers <= 1:
            torch.set_num_threads(max(1, os.cpu_count() or 1))
            _, _A = _load_arrays()
            for vn, sd in todo:
                save(*_unit((vn, sd, device)))
        else:
            with ProcessPoolExecutor(args.workers, initializer=_init) as ex:
                for vn, sd, df in ex.map(_unit, [(vn, sd, "cpu") for vn, sd in todo]):
                    save(vn, sd, df)

    frames = [pd.read_parquet(_part_path(parts, vn, sd)) for vn, sd in units if _part_path(parts, vn, sd).exists()]
    pd.concat(frames, ignore_index=True).to_parquet(out / "mlp_raw.parquet")
    print("MLP done →", out / "mlp_raw.parquet", round((time.time() - t) / 60, 1), "분", flush=True)

    if args.skip_chronos:
        return
    p, _ = _load_arrays()
    for tag, cov in [("zs", False), ("hol", dl.COV_SETS["+ 공휴일"]), ("free", dl.COV_SETS["+ 공휴일·무료 개방"])]:
        f = out / f"chronos_{tag}.parquet"
        if f.exists():
            print("chronos", tag, "있음 — 건너뜀", flush=True)
            continue
        t = time.time()
        dl.run_chronos(p, covariates=cov, device=device).to_parquet(f)
        print("chronos", tag, round(time.time() - t), "s", flush=True)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
