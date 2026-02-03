"""CALCE 通用 xlsx（Channel_* 工作表）读取：整理为可用于仿真/验证的时间序列。

背景：
- CALCE 的部分数据（如 Incremental OCV、DST/US06/FUDS 等）使用“Channel_*”工作表存放主数据；
- 这类表通常包含 Test_Time(s)、Step_Index、Current(A)、Voltage(V) 等列；
- 本模块只做数据整理与单位/符号约定，不做参数拟合。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CalceChannelTimeSeries:
    """CALCE 通用时间序列（单位已换算为 SI，符号已统一）。"""

    t_s: np.ndarray
    dt_s: np.ndarray
    step: np.ndarray
    i_A: np.ndarray  # 约定：放电为正；充电为负（由 Current(A) 取反实现）
    v_V: np.ndarray
    temp_C: np.ndarray | None = None
    r_internal_ohm: np.ndarray | None = None


def _infer_dt_s(t_s: np.ndarray) -> np.ndarray:
    t = np.asarray(t_s, dtype=float)
    dt = np.diff(t, prepend=t[0])
    med = float(np.median(dt[dt > 0])) if np.any(dt > 0) else 1.0
    dt = np.where(dt > 0, dt, med)
    return dt


def load_calce_channel_xlsx(path: str | Path, *, sheet_prefix: str = "Channel_") -> pd.DataFrame:
    """读取 CALCE 的通用 xlsx：优先拼接所有 Channel_* 工作表；若不存在则回退到首个“像数据表”的工作表。

兼容：
- Incremental OCV / DST / US06 / FUDS 等：通常为 Channel_* 多工作表。
- Initial capacity 等：可能只有 Sheet1（或类似名字）的单工作表。
"""

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    xls = pd.ExcelFile(p)
    sheets = [s for s in xls.sheet_names if str(s).startswith(str(sheet_prefix))]
    if not sheets:
        # 回退策略：找一个包含关键列的 sheet（优先 Sheet1）
        candidates = list(xls.sheet_names)
        if "Sheet1" in candidates:
            candidates.remove("Sheet1")
            candidates.insert(0, "Sheet1")

        need = {"Test_Time(s)", "Step_Index", "Current(A)", "Voltage(V)"}
        for s in candidates:
            df = xls.parse(s)
            if need.issubset(set(df.columns)):
                return df

        raise ValueError(f"未找到以 {sheet_prefix!r} 开头的工作表，且无可用数据表，实际 sheets={xls.sheet_names}")

    frames: list[pd.DataFrame] = []
    for s in sheets:
        df = xls.parse(s)
        frames.append(df)

    out = pd.concat(frames, ignore_index=True)
    return out


def extract_channel_time_series(
    df: pd.DataFrame,
    *,
    discharge_positive: bool = True,
    drop_na: bool = True,
) -> CalceChannelTimeSeries:
    """从 Channel_* 拼接后的 DataFrame 中抽取时间序列。"""

    need = ["Test_Time(s)", "Step_Index", "Current(A)", "Voltage(V)"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"缺少列：{missing}，实际列={list(df.columns)}")

    d = df.copy()
    if drop_na:
        d = d[np.isfinite(d["Test_Time(s)"]) & np.isfinite(d["Step_Index"]) & np.isfinite(d["Current(A)"]) & np.isfinite(d["Voltage(V)"])]
    if d.empty:
        raise ValueError("有效数据为空（可能是列名不匹配或全为 NaN）")

    # 按 Test_Time 排序（CALCE 通常是累计秒）
    d = d.sort_values("Test_Time(s)", kind="mergesort")

    t_s = d["Test_Time(s)"].to_numpy(dtype=float)
    dt_s = _infer_dt_s(t_s)
    step = d["Step_Index"].to_numpy(dtype=int)

    i_raw = d["Current(A)"].to_numpy(dtype=float)
    # CALCE 通常：放电为负电流；为了统一项目约定，将放电取正：i = -Current(A)
    i_A = (-i_raw) if discharge_positive else i_raw

    v_V = d["Voltage(V)"].to_numpy(dtype=float)

    temp_C = None
    for col in ("Temperature (C)_1", "Temperature(C)", "Temp(C)"):
        if col in d.columns:
            x = d[col].to_numpy(dtype=float)
            if np.any(np.isfinite(x)):
                temp_C = x
            break

    r_internal = None
    for col in ("Internal_Resistance(Ohm)", "Internal Resistance(Ohm)", "Resistance(Ohm)"):
        if col in d.columns:
            x = d[col].to_numpy(dtype=float)
            if np.any(np.isfinite(x)):
                r_internal = x
            break

    return CalceChannelTimeSeries(t_s=t_s, dt_s=dt_s, step=step, i_A=i_A, v_V=v_V, temp_C=temp_C, r_internal_ohm=r_internal)
