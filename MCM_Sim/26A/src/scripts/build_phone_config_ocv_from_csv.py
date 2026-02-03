#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具脚本：从 CSV 的 OCV(SOC) 曲线生成新的手机电池配置 JSON（用于 Q3“假设敏感性”与更真实的电池端形状）。

典型用途：
- 使用 `data/01-SOC_SOH/OCV_vs_SOC_curve.csv` 替换默认的粗糙 OCV 曲线；
- 在论文中作为“OCV 曲线来源”假设对照（Q3）。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _load_ocv_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    # 只依赖 numpy：避免在竞赛环境强依赖 pandas
    data = np.genfromtxt(str(path), delimiter=",", names=True)
    if "SOC" not in data.dtype.names:
        raise ValueError("CSV 必须包含列 SOC")
    # 常见命名：V0 或 OCV 或 Voltage；取第一个非 SOC 列
    v_col = None
    for c in data.dtype.names:
        if c == "SOC":
            continue
        v_col = c
        break
    if v_col is None:
        raise ValueError("CSV 必须包含电压列（例如 V0）")
    soc = np.asarray(data["SOC"], dtype=float)
    v = np.asarray(data[v_col], dtype=float)
    m = np.isfinite(soc) & np.isfinite(v)
    soc = soc[m]
    v = v[m]
    if soc.size < 2:
        raise ValueError("OCV 曲线点数不足")
    # 排序并截断到 [0,1]
    idx = np.argsort(soc)
    soc = soc[idx]
    v = v[idx]
    soc = np.clip(soc, 0.0, 1.0)
    # 强制单调不减（避免数值噪声导致非物理反插值）
    v = np.maximum.accumulate(v)
    return soc, v


def _downsample_pwl(soc: np.ndarray, v: np.ndarray, *, n_points: int) -> list[list[float]]:
    n = int(n_points)
    if n < 2:
        raise ValueError("n_points 必须 >= 2")
    grid = np.linspace(0.0, 1.0, n)
    vv = np.interp(grid, soc, v)
    # 再做一次单调化（插值后可能出现极小数值回摆）
    vv = np.maximum.accumulate(vv)
    pts = [[float(s), float(x)] for s, x in zip(grid.tolist(), vv.tolist())]
    # 端点强制：避免浮点误差
    pts[0][0] = 0.0
    pts[-1][0] = 1.0
    return pts


def main() -> int:
    ap = argparse.ArgumentParser(description="从 OCV CSV 生成电池配置 JSON（替换 ocv_curve.points）")
    ap.add_argument("--base", required=True, help="基础电池配置 JSON（例如 configs/phone_default_v3_aging.json）")
    ap.add_argument("--ocv-csv", required=True, help="OCV CSV（必须包含 SOC 列与电压列）")
    ap.add_argument("--out", required=True, help="输出 JSON 路径")
    ap.add_argument("--n-points", type=int, default=101, help="输出分段线性点数（默认 101）")
    ap.add_argument("--notes", default="", help="写入 meta.notes_zh 的额外说明")
    args = ap.parse_args()

    base_path = Path(args.base)
    ocv_path = Path(args.ocv_csv)
    out_path = Path(args.out)

    obj = json.loads(base_path.read_text(encoding="utf-8"))
    batt = obj.get("battery", obj)
    ecm = batt.get("ecm", {})
    if not isinstance(ecm, dict):
        raise ValueError("配置文件缺少 battery.ecm 字段")

    soc, v = _load_ocv_csv(ocv_path)
    pts = _downsample_pwl(soc, v, n_points=int(args.n_points))

    ecm["ocv_curve"] = {"type": "piecewise_linear", "points": pts}
    batt["ecm"] = ecm
    obj["battery"] = batt

    meta = obj.get("meta", {}) if isinstance(obj.get("meta", {}), dict) else {}
    extra = str(args.notes).strip()
    note = f"OCV 曲线由 CSV 生成：{ocv_path}"
    if extra:
        note = note + "；" + extra
    meta["notes_zh"] = note
    obj["meta"] = meta

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

