# -*- coding: utf-8 -*-
# 示例：读取 xlsx（来自目录 6）并做灰色关联分析（GRA）
#
# 数据文件（已复制到 Toolkit 内，便于自包含运行）：
# - MCM_Toolkit_2026/data_samples/folder6_grey_gdp.xlsx
# - MCM_Toolkit_2026/data_samples/folder6_grey_mines.xlsx

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.c10_评价与决策_DecisionMaking.grey_relational import solve as gra_solve  # noqa: E402
from MCM_Toolkit_2026.utils.file_reader import read_table  # noqa: E402


def demo_gdp_case() -> None:
    """GDP 与产业结构：比较各产业序列与 GDP 序列的灰色关联度。"""
    xlsx = _PROJECT_ROOT / "MCM_Toolkit_2026" / "data_samples" / "folder6_grey_gdp.xlsx"
    df = read_table(xlsx)

    # 参考序列：GDP；对比序列：第一/二/三产业（按年份序列）
    ref = df["国内生产总值"].to_numpy(dtype=float)
    series_names = ["第一产业", "第二产业", "第三产业"]
    X = np.vstack([df[name].to_numpy(dtype=float) for name in series_names])  # 3×T

    out = gra_solve(X, {"ref": ref.tolist(), "rho": 0.5, "normalize_method": "initial"})
    grade = out["grade"]
    order = out["order"]

    print("\n[GDP] 灰色关联度（越大越相关）")
    for idx in order:
        print(f"- {series_names[int(idx)]}: {grade[int(idx)]:.4f}")


def demo_mines_case() -> None:
    """矿井综合评价：以“理想对象”为参考序列，比较各矿与理想的灰色关联度。"""
    xlsx = _PROJECT_ROOT / "MCM_Toolkit_2026" / "data_samples" / "folder6_grey_mines.xlsx"
    df = read_table(xlsx)

    # 第一列为指标名，其余为对象数值
    indicator_col = df.columns[0]
    indicators = df[indicator_col].astype(str).tolist()
    value_df = df.drop(columns=[indicator_col]).copy()

    # 将“成本”类指标转为“效益型”（越大越好）：max+min - x
    cost_like = {name for name in indicators if "成本" in name}
    for i, ind in enumerate(indicators):
        if ind in cost_like:
            row = value_df.iloc[i, :].to_numpy(dtype=float)
            value_df.iloc[i, :] = row.max() + row.min() - row

    # 参考序列（理想对象）与对比序列（各矿）
    ref = value_df["理想对象"].to_numpy(dtype=float)
    mine_cols = [c for c in value_df.columns if c != "理想对象"]
    X = value_df[mine_cols].to_numpy(dtype=float).T  # 矿(行)×指标(列)

    out = gra_solve(X, {"ref": ref.tolist(), "rho": 0.5, "normalize_method": "minmax"})
    grade = out["grade"]
    order = out["order"]

    print("\n[矿井] 与理想对象的灰色关联度（越大越接近理想）")
    for idx in order:
        print(f"- {mine_cols[int(idx)]}: {grade[int(idx)]:.4f}")


if __name__ == "__main__":
    demo_gdp_case()
    demo_mines_case()

