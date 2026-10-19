"""전처리.md 규칙대로 만든 패널을 outputs/preprocessed_panel.csv 로 저장.

python tools/make_preprocessed.py
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import hv  # noqa: E402

# 전처리.md 의 1~4절 코드(블록 6개)를 그대로 실행한다(문서와 CSV 가 어긋나지 않게)
md = (ROOT / "전처리.md").read_text(encoding="utf-8")
blocks = re.findall(r"```python\n(.*?)```", md, re.S)[:6]
ns = {"__name__": "prep"}
import os
os.chdir(ROOT)
for b in blocks:
    exec(b, ns)
panel, w = ns["panel"], ns["w"]

# 달력 규칙(무료 개방일·명절 연휴) — hv.add_free_rule, 제공 달력 열만 사용
cal = hv.add_free_rule(ns["c"])[["date", "is_myeongjeol", "is_free_rule", "is_offday"]]
panel = panel.merge(cal, on="date", how="left")

# 날씨: 비 온 날 여부(≥5mm). 예측에는 원점 전날까지만 쓴다(당일 값은 「완벽한 예보 가정」 전용)
wx = w[["date", "site", "t2m", "precip_mm"]].assign(rain=lambda d: (d["precip_mm"] >= hv.RAIN_MM).astype(int),
                                                   clear=lambda d: (d["precip_mm"] < 1).astype(int))
panel = panel.merge(wx, on=["date", "site"], how="left")

panel["in_train_period"] = (panel["date"] >= ns["TRAIN_START"]).astype(int)

cols = [
    "date", "site", "group", "weekday", "closed_weekday", "is_closed_weekday",
    "status", "is_open", "y", "total", "paid", "free",
    "is_holiday", "holiday_name", "seollal_offset", "chuseok_offset",
    "is_last_wednesday", "is_myeongjeol", "is_free_rule", "is_offday",
    "t2m", "precip_mm", "rain", "clear", "in_train_period",
]
out = panel[cols].sort_values(["site", "date"]).reset_index(drop=True)

# 점검
assert len(out) == 63194 and out.shape[1] == 25 and not out.duplicated(["site", "date"]).any()
assert out.loc[out["status"] != "open", "y"].isna().all()
assert (out["status"] == "open").sum() == out["y"].notna().sum() == 53196

path = ROOT / "outputs" / "preprocessed_panel.csv"
out.to_csv(path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
print(path, out.shape)
print(out["status"].value_counts().to_dict())
print(out[out["in_train_period"] == 1]["status"].value_counts().to_dict())
