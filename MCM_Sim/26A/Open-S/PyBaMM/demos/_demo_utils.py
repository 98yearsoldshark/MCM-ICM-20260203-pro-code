"""
PyBaMM demos 的公共工具函数。

约定：
- demo 默认写入 ../outputs/
- 默认禁用 PyBaMM telemetry（避免无关网络请求 + 提升首次 import 速度）
- matplotlib 使用无 GUI 的 Agg 后端（便于在服务器/CI 跑）
"""

from __future__ import annotations

import os
from pathlib import Path


# 在导入 matplotlib 之前设置后端，避免无显示环境报错
os.environ.setdefault("MPLBACKEND", "Agg")


def project_root() -> Path:
    """返回本交接包根目录：.../MCM_Sim/26A/Open-S/PyBaMM"""
    return Path(__file__).resolve().parents[1]


def outputs_dir() -> Path:
    """确保输出目录存在并返回其路径。"""
    out = project_root() / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out


def disable_pybamm_telemetry() -> None:
    """禁用 PyBaMM telemetry（不影响计算结果）。"""
    try:
        import pybamm

        pybamm.telemetry.disable()
    except Exception:
        # 如果 PyBaMM API 变动或未安装，不阻塞 demo 的其它部分
        return


def savefig(path: Path) -> None:
    """保存当前 matplotlib 图到指定路径。"""
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=160, bbox_inches="tight")

