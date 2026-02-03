"""
SOC EKF demo（1RC/2RC）

运行：
  python3 MCM_Sim/26A/Load-Model/EKF/demo/demo_ekf_soc.py

说明：
- 先用“真值 2RC 模型”生成 SOC/端电压，再叠加测量噪声
- 分别用 1RC-EKF 与 2RC-EKF 估计 SOC（便于对比）

默认会把图保存为当前目录下的 `ekf_soc_demo.png`（便于无 GUI 环境跑通）。
如需弹窗显示：加 `--show`。
"""

from __future__ import annotations

import argparse
from dataclasses import asdict

import numpy as np

from ecm_core import (
    ECM1RCParams,
    ECM2RCParams,
    PiecewiseLinearOCV,
    h_1rc,
    h_2rc,
    step_1rc_x,
    step_2rc_x,
)
from ekf_core import ekf_step_1rc, ekf_step_2rc


def make_current_profile(dt_s: float) -> np.ndarray:
    dt = float(dt_s)
    segs = [
        (20, 0.0),
        (40, 2.0),
        (40, 0.0),
        (40, 3.0),
        (60, 0.0),
        (40, 1.0),
        (60, 0.0),
    ]
    out = []
    for dur, ia in segs:
        n = max(0, int(round(float(dur) / dt)))
        out.extend([float(ia)] * n)
    return np.array(out, dtype=float)


def simulate_truth_2rc(
    *,
    params: ECM2RCParams,
    dt_s: float,
    current_A: np.ndarray,
    soc0: float,
) -> tuple[np.ndarray, np.ndarray]:
    """用 2RC 生成真值：返回 (soc_true, v_true)。"""

    x = np.array([float(soc0), 0.0, 0.0], dtype=float)
    soc_list = [float(x[0])]
    v_list = [float(params.ocv.ocv(float(x[0])))]
    for i in current_A:
        x_list, *_ = step_2rc_x(x, I_A=float(i), dt_s=float(dt_s), p=params)
        x = np.array(x_list, dtype=float)
        soc_list.append(float(x[0]))
        v_list.append(float(h_2rc(x, I_A=float(i), p=params)))
    return np.array(soc_list, dtype=float), np.array(v_list, dtype=float)


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="弹窗显示图像（有 GUI 环境时使用）")
    ap.add_argument("--out", default="ekf_soc_demo.png", help="保存图片路径（默认当前目录）")
    args = ap.parse_args()

    rng = np.random.default_rng(0)
    dt_s = 1.0
    current = make_current_profile(dt_s)

    ocv = PiecewiseLinearOCV.from_points(
        [
            [0.0, 3.00],
            [0.10, 3.60],
            [0.90, 4.00],
            [1.0, 4.20],
        ]
    )

    # ===== 真值模型（2RC）=====
    p_true = ECM2RCParams(
        capacity_Ah=4.0,
        r0_ohm=0.08,
        r1_ohm=0.02,
        c1_F=2000.0,
        r2_ohm=0.01,
        c2_F=8000.0,
        ocv=ocv,
    )

    soc0_true = 0.9
    soc_true, v_true = simulate_truth_2rc(params=p_true, dt_s=dt_s, current_A=current, soc0=soc0_true)

    # 电压测量噪声（标准差 20mV）
    sigma_v = 0.02
    v_meas = v_true + rng.normal(0.0, sigma_v, size=v_true.shape)

    print("[EKF Demo] 真值参数（2RC）：", asdict(p_true))
    print("[EKF Demo] 电压测量噪声 sigma=%.3f V" % sigma_v)

    # ===== 1RC EKF（模型不匹配：用 1RC 去估计 2RC 真值）=====
    p_1rc = ECM1RCParams(
        capacity_Ah=p_true.capacity_Ah,
        # 故意给一点参数偏差（工程里很常见），用来体现“模型/参数不匹配”对 SOC 的影响
        r0_ohm=p_true.r0_ohm * 1.10,
        r1_ohm=p_true.r1_ohm * 1.20,
        c1_F=p_true.c1_F * 0.80,
        ocv=ocv,
    )
    x1 = np.array([0.8, 0.0], dtype=float)  # 故意给一个偏差初值
    P1 = np.diag([0.05**2, 0.1**2]).astype(float)
    Q1 = np.diag([1e-7, 1e-5]).astype(float)  # 可调：过程噪声
    R = float(sigma_v**2)

    soc_hat_1rc = [float(x1[0])]
    v_pred_1rc = [float(h_1rc(x1, I_A=0.0, p=p_1rc))]
    res_1rc = [float(v_meas[0] - v_pred_1rc[0])]

    for k, i in enumerate(current, start=1):
        x1, P1, v_pred, res = ekf_step_1rc(
            x1,
            P1,
            I_A=float(i),
            V_meas=float(v_meas[k]),
            dt_s=dt_s,
            params=p_1rc,
            Q=Q1,
            R=R,
        )
        soc_hat_1rc.append(float(x1[0]))
        v_pred_1rc.append(float(v_pred))
        res_1rc.append(float(res))

    soc_hat_1rc = np.array(soc_hat_1rc, dtype=float)
    v_pred_1rc = np.array(v_pred_1rc, dtype=float)

    # ===== 2RC EKF（模型匹配）=====
    x2 = np.array([0.8, 0.0, 0.0], dtype=float)
    # 2RC 的观测对 V1/V2 的敏感度更高（系数 -1），如果给 V1/V2 太大的不确定度，
    # 创新会优先“被 V1/V2 吃掉”，导致 SOC 修正变慢。这里刻意把 SOC 不确定度设大一些，
    # 而把 V1/V2 设小一些，便于演示 SOC 也能被有效纠正。
    P2 = np.diag([0.20**2, 0.02**2, 0.02**2]).astype(float)
    Q2 = np.diag([1e-7, 1e-7, 1e-7]).astype(float)

    soc_hat_2rc = [float(x2[0])]
    v_pred_2rc = [float(h_2rc(x2, I_A=0.0, p=p_true))]
    res_2rc = [float(v_meas[0] - v_pred_2rc[0])]

    for k, i in enumerate(current, start=1):
        x2, P2, v_pred, res = ekf_step_2rc(
            x2,
            P2,
            I_A=float(i),
            V_meas=float(v_meas[k]),
            dt_s=dt_s,
            params=p_true,
            Q=Q2,
            R=R,
        )
        soc_hat_2rc.append(float(x2[0]))
        v_pred_2rc.append(float(v_pred))
        res_2rc.append(float(res))

    soc_hat_2rc = np.array(soc_hat_2rc, dtype=float)
    v_pred_2rc = np.array(v_pred_2rc, dtype=float)

    t = np.arange(len(v_true)) * dt_s
    i_plot = np.array([0.0] + list(current), dtype=float)

    print("[EKF Demo] SOC RMSE：1RC-EKF=%.6f, 2RC-EKF=%.6f" % (rmse(soc_hat_1rc, soc_true), rmse(soc_hat_2rc, soc_true)))
    print("[EKF Demo] 电压拟合 RMSE：1RC-EKF=%.6fV, 2RC-EKF=%.6fV" % (rmse(v_pred_1rc, v_true), rmse(v_pred_2rc, v_true)))

    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(4, 1, figsize=(11, 10), sharex=True)

        axes[0].plot(t, i_plot, label="Current I (A), discharge=positive")
        axes[0].set_ylabel("I (A)")
        axes[0].grid(True, alpha=0.3)
        axes[0].legend()

        axes[1].plot(t, v_true, label="V true", linewidth=2)
        axes[1].plot(t, v_meas, label="V meas (noise)", alpha=0.5)
        axes[1].plot(t, v_pred_1rc, label="V pred (1RC-EKF)", linestyle="--")
        axes[1].plot(t, v_pred_2rc, label="V pred (2RC-EKF)", linestyle="--")
        axes[1].set_ylabel("V (V)")
        axes[1].grid(True, alpha=0.3)
        axes[1].legend(ncol=2)

        axes[2].plot(t, soc_true, label="SOC true", linewidth=2)
        axes[2].plot(t, soc_hat_1rc, label="SOC hat (1RC-EKF)", linestyle="--")
        axes[2].plot(t, soc_hat_2rc, label="SOC hat (2RC-EKF)", linestyle="--")
        axes[2].set_ylabel("SOC")
        axes[2].grid(True, alpha=0.3)
        axes[2].legend(ncol=2)

        axes[3].plot(t, np.array(res_1rc), label="residual (1RC)")
        axes[3].plot(t, np.array(res_2rc), label="residual (2RC)")
        axes[3].axhline(0.0, color="k", linewidth=1)
        axes[3].set_ylabel("V_meas - V_pred (V)")
        axes[3].set_xlabel("t (s)")
        axes[3].grid(True, alpha=0.3)
        axes[3].legend()

        fig.suptitle("SOC EKF Demo (truth=2RC, estimate=1RC vs 2RC)")
        plt.tight_layout()
        fig.savefig(args.out, dpi=160)
        print("[EKF Demo] 已保存图片：%s" % args.out)
        if args.show:
            plt.show()
        plt.close(fig)
    except Exception as e:
        print("[EKF Demo] 未绘图（matplotlib 不可用或其它错误）：", repr(e))


if __name__ == "__main__":
    main()
