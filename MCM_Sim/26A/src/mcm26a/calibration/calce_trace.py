"""CALCE 数据读取：把原始表格整理为可用于校准的时间序列（仅做数据整理，不做拟合）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CalceTimeSeries:
    """CALCE 时间序列（单位已换算为 SI）。"""

    t_s: np.ndarray
    dt_s: np.ndarray
    step: np.ndarray
    i_A: np.ndarray  # 约定：放电为正；充电为负（由数据 mA 符号推断）
    v_V: np.ndarray


def _infer_dt_s(t_s: np.ndarray) -> np.ndarray:
    t = t_s.astype(float)
    dt = np.diff(t, prepend=t[0])
    med = float(np.median(dt[dt > 0])) if np.any(dt > 0) else 1.0
    dt = np.where(dt > 0, dt, med)
    return dt


def load_calce_low_current_ocv_xlsx(path: str | Path) -> pd.DataFrame:
    """读取 CALCE 的低电流 OCV xlsx（原始表）。"""

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    df = pd.read_excel(p)
    need = ["Duration (sec)", "Pgm step", "mV", "mA"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"缺少列：{missing}，实际列={list(df.columns)}")
    return df


def extract_time_series(
    df: pd.DataFrame,
    *,
    steps: tuple[int, ...] = (2, 3, 4),
) -> CalceTimeSeries:
    """从原始 DataFrame 中抽取指定 steps 的时间序列。"""

    d = df.copy()
    d = d[np.isfinite(d["Duration (sec)"]) & np.isfinite(d["mV"]) & np.isfinite(d["mA"]) & np.isfinite(d["Pgm step"])]
    d["Pgm step"] = d["Pgm step"].astype(int)
    d = d[d["Pgm step"].isin([int(s) for s in steps])]
    if d.empty:
        raise ValueError(f"未找到 steps={steps} 的数据")

    # 按时间排序（Duration 通常为累计秒）
    d = d.sort_values("Duration (sec)", kind="mergesort")

    t_s = d["Duration (sec)"].to_numpy(dtype=float)
    dt_s = _infer_dt_s(t_s)
    step = d["Pgm step"].to_numpy(dtype=int)
    v_V = d["mV"].to_numpy(dtype=float) / 1000.0

    # CALCE：放电通常为负电流（mA<0）；约定 i_A=放电为正 => i_A = -mA/1000
    i_A = -d["mA"].to_numpy(dtype=float) / 1000.0

    return CalceTimeSeries(t_s=t_s, dt_s=dt_s, step=step, i_A=i_A, v_V=v_V)

