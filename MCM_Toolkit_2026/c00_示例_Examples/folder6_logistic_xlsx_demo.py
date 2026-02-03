# -*- coding: utf-8 -*-
# 示例：读取 xlsx（来自目录 6）并跑一遍逻辑回归二分类
#
# 数据文件（已复制到 Toolkit 内，便于自包含运行）：
# - MCM_Toolkit_2026/data_samples/folder6_logistic_credit.xlsx

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.c03_监督学习_Supervised.logistic_regression import solve as lr_solve  # noqa: E402
from MCM_Toolkit_2026.utils.file_reader import read_table  # noqa: E402


if __name__ == "__main__":
    xlsx = _PROJECT_ROOT / "MCM_Toolkit_2026" / "data_samples" / "folder6_logistic_credit.xlsx"
    df = read_table(xlsx)

    # 原数据包含：企业编号、X1/X2/X3、Y、预测值
    # 为避免“预测值”泄露，这里只用 X1~X3 预测 Y
    df = df.copy()
    # 原表里 Y 可能包含“？”等缺失标记，先转数值并丢弃缺失行
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
    df = df.dropna(subset=["Y"])

    X = df[["X1", "X2", "X3"]]
    y = df["Y"].astype(int)

    out = lr_solve((X, y), {"test_size": 0.3, "random_state": 42, "model_params": {"max_iter": 500}})
    print(out["metrics"])
