"""
ECM 1RC vs 2RC：脉冲电流响应对比 demo

运行：
  python3 MCM_Sim/26A/Load-Model/ECM-1RCor2RC/demo/demo_ecm_pulse.py

默认会把图保存为当前目录下的 `ecm_pulse_demo.png`（便于无 GUI 环境跑通）。
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
    make_pulse_current,
    simulate_1rc,
    simulate_2rc,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="弹窗显示图像（有 GUI 环境时使用）")
    ap.add_argument("--out", default="ecm_pulse_demo.png", help="保存图片路径（默认当前目录）")
    args = ap.parse_args()

    dt_s = 1.0

    # 一个“可看出极化效应”的电流序列（单位 A；I>0 放电）
    current = make_pulse_current(
        dt_s=dt_s,
        segments=[
            (20, 0.0),
            (30, 2.0),
            (40, 0.0),
            (30, 3.0),
            (60, 0.0),
            (30, 1.0),
            (40, 0.0),
        ],
    )

    ocv = PiecewiseLinearOCV.from_points(
        [
            [0.0, 3.00],
            [0.10, 3.60],
            [0.90, 4.00],
            [1.0, 4.20],
        ]
    )

    p1 = ECM1RCParams(
        capacity_Ah=4.0,
        r0_ohm=0.08,
        r1_ohm=0.02,
        c1_F=2000.0,
        ocv=ocv,
    )
    # 2RC：增加一个更慢的极化支路，用来体现“两个时间常数”
    p2 = ECM2RCParams(
        capacity_Ah=4.0,
        r0_ohm=0.08,
        r1_ohm=0.02,
        c1_F=2000.0,
        r2_ohm=0.01,
        c2_F=8000.0,
        ocv=ocv,
    )

    soc0 = 0.9
    s1, v1 = simulate_1rc(params=p1, soc0=soc0, dt_s=dt_s, current_A=current)
    s2, v2 = simulate_2rc(params=p2, soc0=soc0, dt_s=dt_s, current_A=current)

    t = np.arange(len(current) + 1) * dt_s
    i = np.array([0.0] + list(current))
    v1 = np.array(v1)
    v2 = np.array(v2)
    soc_1rc = np.array([x.soc for x in s1])
    soc_2rc = np.array([x.soc for x in s2])
    pol_1rc = np.array([x.v1_V for x in s1])
    pol_2rc = np.array([x.v1_V + x.v2_V for x in s2])

    print("[ECM Demo] 参数（1RC）：", asdict(p1))
    print("[ECM Demo] 参数（2RC）：", asdict(p2))
    print("[ECM Demo] 末端 SOC：1RC=%.4f, 2RC=%.4f" % (soc_1rc[-1], soc_2rc[-1]))
    print("[ECM Demo] 末端电压：1RC=%.4f V, 2RC=%.4f V" % (v1[-1], v2[-1]))

    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True)

        axes[0].plot(t, i, label="Current I (A), discharge=positive")
        axes[0].set_ylabel("I (A)")
        axes[0].grid(True, alpha=0.3)
        axes[0].legend()

        axes[1].plot(t, v1, label="1RC")
        axes[1].plot(t, v2, label="2RC", linestyle="--")
        axes[1].set_ylabel("V_term (V)")
        axes[1].grid(True, alpha=0.3)
        axes[1].legend()

        axes[2].plot(t, soc_1rc, label="SOC 1RC")
        axes[2].plot(t, soc_2rc, label="SOC 2RC", linestyle="--")
        axes[2].set_ylabel("SOC")
        axes[2].grid(True, alpha=0.3)
        axes[2].legend()

        axes[3].plot(t, pol_1rc, label="V_polar 1RC(v1)")
        axes[3].plot(t, pol_2rc, label="V_polar 2RC(v1+v2)", linestyle="--")
        axes[3].set_ylabel("V_polar (V)")
        axes[3].set_xlabel("t (s)")
        axes[3].grid(True, alpha=0.3)
        axes[3].legend()

        fig.suptitle("ECM 1RC vs 2RC: Pulse Response")
        plt.tight_layout()
        fig.savefig(args.out, dpi=160)
        print("[ECM Demo] 已保存图片：%s" % args.out)
        if args.show:
            plt.show()
        plt.close(fig)
    except Exception as e:
        print("[ECM Demo] 未绘图（matplotlib 不可用或其它错误）：", repr(e))


if __name__ == "__main__":
    main()
