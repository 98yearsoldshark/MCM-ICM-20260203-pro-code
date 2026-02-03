# -*- coding: utf-8 -*-
# 示例：读取 xlsx + 曲线拟合（目录 5：数学建模拟合）

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.c03_监督学习_Supervised.curve_fitting import solve as curve_fit_solve


def main() -> None:
    xlsx_path = _PROJECT_ROOT / "MCM_Toolkit_2026" / "data_samples" / "folder5_curve_fitting_growth.xlsx"
    df = pd.read_excel(xlsx_path)

    poly = curve_fit_solve(df, {"x_col": "x", "y_col": "y", "model": "polynomial", "degree": 3})
    expb = curve_fit_solve(df, {"x_col": "x", "y_col": "y", "model": "exp_base", "p0": [1.1, 1.0, 0.0]})

    print("poly(deg=3) metrics =", poly["metrics"])
    print("exp_base params(a,b,c) =", np.round(expb["params"], 6))
    print("exp_base metrics =", expb["metrics"])


if __name__ == "__main__":
    main()

