"""从 CALCE 的低电流 OCV 测试数据中提取 OCV-SOC 曲线，并生成可用于 ECM 的配置参数。

为什么选这类数据：
- 低电流（如 0.05C）下极化压降较小，端电压更接近开路电压 OCV；
- 只用一份数据也能构建“可解释”的 OCV-SOC 曲线，为 Model-1/2/3 提供关键输入。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CalceOCVFit:
    """从一份低电流测试中拟合得到的 OCV 结果（用于写入 JSON 配置）。"""

    capacity_Ah: float
    energy_Wh: float
    nominal_voltage_V: float
    ocv_points: list[tuple[float, float]]  # (soc, ocv_V)，soc 升序
    r0_est_ohm: float | None


def _require_columns(df: pd.DataFrame, cols: list[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"缺少列：{missing}，实际列={list(df.columns)}")


def load_calce_low_current_ocv_xlsx(path: str | Path) -> pd.DataFrame:
    """读取 CALCE 低电流 OCV xlsx，并返回原始 DataFrame。"""

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    df = pd.read_excel(p)
    _require_columns(df, ["Duration (sec)", "Pgm step", "mV", "mA"])
    return df


def _infer_dt_s(duration_s: np.ndarray) -> np.ndarray:
    """由 Duration(sec) 推断每行时间步长 dt。"""

    t = duration_s.astype(float)
    dt = np.diff(t, prepend=t[0])
    # 兜底：第一行 dt=0，用全局中位数替代
    med = float(np.median(dt[dt > 0])) if np.any(dt > 0) else 1.0
    dt = np.where(dt > 0, dt, med)
    return dt


def _enforce_monotone_increasing(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """确保电压随 SOC 单调不减（避免噪声导致轻微“回折”）。"""

    pts = sorted([(float(s), float(v)) for s, v in points], key=lambda x: x[0])

    # 合并重复 SOC 点：保留电压较大的那个（更贴近 OCV 上包络）
    merged: list[tuple[float, float]] = []
    for s, v in pts:
        if merged and abs(merged[-1][0] - s) <= 1e-12:
            merged[-1] = (merged[-1][0], max(float(merged[-1][1]), float(v)))
        else:
            merged.append((s, v))

    out: list[tuple[float, float]] = []
    last_v = -1e18
    for s, v in merged:
        v2 = v if v >= last_v else last_v
        out.append((s, v2))
        last_v = v2
    return out


def fit_ocv_from_low_current_discharge(
    df: pd.DataFrame,
    *,
    discharge_step: int,
    n_points: int = 21,
    current_threshold_A: float = 0.02,
) -> CalceOCVFit:
    """仅用“低电流放电段”拟合 OCV-SOC（推荐）。

    参数：
    - discharge_step：放电所在的 Pgm step 编号（该文件通常为 3）
    - n_points：输出 OCV 分段线性点数（含端点），建议 11~41
    - current_threshold_A：筛除小电流/休息段用的阈值
    """

    if int(n_points) < 5:
        raise ValueError("n_points 太小，建议 >= 5")

    seg = df[df["Pgm step"].astype(int) == int(discharge_step)].copy()
    if seg.empty:
        raise ValueError(f"未找到 Pgm step={discharge_step} 的数据段")

    t_s = seg["Duration (sec)"].to_numpy(dtype=float)
    dt_s = _infer_dt_s(t_s)
    v_V = seg["mV"].to_numpy(dtype=float) / 1000.0
    i_A_raw = seg["mA"].to_numpy(dtype=float) / 1000.0

    # 约定：该 CALCE 文件中放电电流为负，故 I_discharge = -i_A_raw（取正值）
    i_discharge_A = -i_A_raw

    mask = i_discharge_A > float(current_threshold_A)
    if not np.any(mask):
        raise ValueError("放电段没有足够的有效电流数据（请检查电流符号或阈值）")

    t_s = t_s[mask]
    dt_s = dt_s[mask]
    v_V = v_V[mask]
    i_discharge_A = i_discharge_A[mask]

    # 由库仑计数得到容量与 SOC
    ah_removed = np.cumsum(i_discharge_A * dt_s / 3600.0)
    capacity_Ah = float(ah_removed[-1])
    if capacity_Ah <= 0:
        raise ValueError("拟合得到的容量为非正值（请检查数据）")

    soc = 1.0 - (ah_removed / capacity_Ah)
    soc = np.clip(soc, 0.0, 1.0)

    # 放电输出能量（Wh）
    energy_Wh = float(np.sum(v_V * i_discharge_A * dt_s / 3600.0))
    nominal_v = energy_Wh / capacity_Ah

    # 在 SOC 轴上等分取样：每个 bin 取电压中位数，鲁棒对抗噪声
    edges = np.linspace(0.0, 1.0, int(n_points))
    pts: list[tuple[float, float]] = []
    for s in edges:
        # 用一个小窗口取样，避免“单点噪声”
        w = 0.02
        m = (soc >= max(0.0, s - w)) & (soc <= min(1.0, s + w))
        if not np.any(m):
            continue
        v_med = float(np.median(v_V[m]))
        pts.append((float(s), v_med))

    # 强制加上端点（0 与 1）
    pts.append((0.0, float(np.min(v_V))))
    pts.append((1.0, float(np.max(v_V))))
    pts = _enforce_monotone_increasing(pts)

    return CalceOCVFit(
        capacity_Ah=capacity_Ah,
        energy_Wh=energy_Wh,
        nominal_voltage_V=float(nominal_v),
        ocv_points=pts,
        r0_est_ohm=None,
    )


def estimate_r0_from_step_transition(
    df: pd.DataFrame,
    *,
    rest_step: int,
    load_step: int,
    discharge: bool,
    n_rest: int = 20,
    n_load: int = 20,
    current_threshold_A: float = 0.02,
) -> float | None:
    """从“休息 -> 负载”的电压跳变粗略估计 R0（很粗，仅作先验参考）。

    注意：低电流下 ΔV 很小，R0 估计对噪声非常敏感；因此默认不强行写入配置。
    """

    rest = df[df["Pgm step"].astype(int) == int(rest_step)].copy()
    load = df[df["Pgm step"].astype(int) == int(load_step)].copy()
    if rest.empty or load.empty:
        return None

    rest_tail = rest.tail(int(n_rest))
    load_head = load.head(int(n_load))

    v_rest = float(np.median(rest_tail["mV"].to_numpy(dtype=float) / 1000.0))
    v_load = float(np.median(load_head["mV"].to_numpy(dtype=float) / 1000.0))
    i_A = float(np.median(load_head["mA"].to_numpy(dtype=float) / 1000.0))

    # 统一为“放电电流为正值”
    i_discharge = -i_A if discharge else i_A
    if i_discharge <= float(current_threshold_A):
        return None

    r0 = (v_rest - v_load) / float(i_discharge)
    if not np.isfinite(r0) or r0 <= 0:
        return None
    return float(r0)
