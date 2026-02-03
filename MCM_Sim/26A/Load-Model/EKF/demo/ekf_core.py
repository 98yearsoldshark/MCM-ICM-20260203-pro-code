"""
最小 EKF（扩展卡尔曼滤波）实现：用于 SOC + 极化支路状态估计。

模型：
- 状态：1RC -> x=[SOC, V1]；2RC -> x=[SOC, V1, V2]
- 输入：电流 I（A，I>0 放电）
- 观测：端电压 V（V）
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from ecm_core import ECM1RCParams, ECM2RCParams, h_1rc, h_2rc, step_1rc_x, step_2rc_x


def _clamp_soc(x: np.ndarray) -> np.ndarray:
    out = x.copy()
    out[0] = float(np.clip(out[0], 0.0, 1.0))
    return out


def ekf_step_1rc(
    x: np.ndarray,
    P: np.ndarray,
    *,
    I_A: float,
    V_meas: float,
    dt_s: float,
    params: ECM1RCParams,
    Q: np.ndarray,
    R: float,
) -> Tuple[np.ndarray, np.ndarray, float, float]:
    """
    单步 EKF（1RC）。

    返回：
    - x_new, P_new
    - V_pred（更新前的预测电压）
    - residual（创新：V_meas - V_pred）
    """

    # 1) Predict
    x_pred_list, a1 = step_1rc_x(x, I_A=I_A, dt_s=dt_s, p=params)
    x_pred = np.array(x_pred_list, dtype=float)
    F = np.array([[1.0, 0.0], [0.0, float(a1)]], dtype=float)
    P_pred = F @ P @ F.T + Q

    # 2) Update
    V_pred = float(h_1rc(x_pred, I_A=I_A, p=params))
    dOCV = float(params.ocv.docv_dsoc(float(x_pred[0])))
    H = np.array([[dOCV, -1.0]], dtype=float)  # shape (1,2)

    residual = float(V_meas) - V_pred
    S = float(H @ P_pred @ H.T + float(R))  # scalar
    if not np.isfinite(S) or S <= 0:
        # 数值保护：不更新，直接返回预测
        return _clamp_soc(x_pred), P_pred, V_pred, residual

    K = (P_pred @ H.T) / S  # (2,1)
    x_new = x_pred + (K[:, 0] * residual)

    # Joseph 形式，数值更稳
    I2 = np.eye(2)
    KH = K @ H
    P_new = (I2 - KH) @ P_pred @ (I2 - KH).T + K * float(R) * K.T

    return _clamp_soc(x_new), P_new, V_pred, residual


def ekf_step_2rc(
    x: np.ndarray,
    P: np.ndarray,
    *,
    I_A: float,
    V_meas: float,
    dt_s: float,
    params: ECM2RCParams,
    Q: np.ndarray,
    R: float,
) -> Tuple[np.ndarray, np.ndarray, float, float]:
    """单步 EKF（2RC），返回同 ekf_step_1rc。"""

    # 1) Predict
    x_pred_list, a1, a2 = step_2rc_x(x, I_A=I_A, dt_s=dt_s, p=params)
    x_pred = np.array(x_pred_list, dtype=float)
    F = np.diag([1.0, float(a1), float(a2)]).astype(float)
    P_pred = F @ P @ F.T + Q

    # 2) Update
    V_pred = float(h_2rc(x_pred, I_A=I_A, p=params))
    dOCV = float(params.ocv.docv_dsoc(float(x_pred[0])))
    H = np.array([[dOCV, -1.0, -1.0]], dtype=float)  # shape (1,3)

    residual = float(V_meas) - V_pred
    S = float(H @ P_pred @ H.T + float(R))
    if not np.isfinite(S) or S <= 0:
        return _clamp_soc(x_pred), P_pred, V_pred, residual

    K = (P_pred @ H.T) / S  # (3,1)
    x_new = x_pred + (K[:, 0] * residual)

    I3 = np.eye(3)
    KH = K @ H
    P_new = (I3 - KH) @ P_pred @ (I3 - KH).T + K * float(R) * K.T

    return _clamp_soc(x_new), P_new, V_pred, residual

