# -*- coding: utf-8 -*-
# 示例：电影推荐（Item-based 协同过滤）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.c07_推荐系统_Recommendation.collaborative_filtering import item_based_recommend  # noqa: E402
from MCM_Toolkit_2026.utils.file_reader import read_table  # noqa: E402


def solve(data: Union[pd.DataFrame, str, Path], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    端到端示例：给定评分长表，基于某个“目标电影”推荐相似电影。

    Args:
        data: DataFrame 或路径（csv/xlsx/xls）。需要包含 user/item/rating 三列。
        params: 参数：
            - user_col/item_col/rating_col: 列名（默认 user/item/rating）
            - target_item: str（必填）
            - min_count: int（默认 5）
            - top_n: int（默认 10）

    Returns:
        dict: {'recommendations': DataFrame}
    """
    params = params or {}
    if isinstance(data, (str, Path)):
        df = read_table(data)
    else:
        df = data
    if not isinstance(df, pd.DataFrame):
        raise TypeError("data 必须为 DataFrame 或表格文件路径。")

    target_item = params.get("target_item")
    if not target_item:
        raise ValueError("params.target_item 必填。")

    rec = item_based_recommend(
        df,
        user_col=str(params.get("user_col", "user")),
        item_col=str(params.get("item_col", "item")),
        rating_col=str(params.get("rating_col", "rating")),
        target_item=str(target_item),
        min_count=int(params.get("min_count", 5)),
        top_n=int(params.get("top_n", 10)),
    )
    return {"recommendations": rec}


if __name__ == "__main__":
    # Mock Data：生成一份“用户-电影-评分”长表
    rng = np.random.default_rng(0)
    users = [f"U{i}" for i in range(1, 101)]
    movies = ["阿甘正传", "肖申克的救赎", "泰坦尼克号", "星际穿越", "霸王别姬", "这个杀手不太冷"]

    rows = []
    for u in users:
        for m in movies:
            if rng.random() < 0.55:
                # 为了让相关性更明显，给“阿甘正传/肖申克”稍微联动一下
                base = rng.integers(1, 6)
                if m == "肖申克的救赎" and rng.random() < 0.5:
                    base = 4
                if m == "阿甘正传" and rng.random() < 0.5:
                    base = 4
                rows.append({"user": u, "item": m, "rating": float(base)})

    df_demo = pd.DataFrame(rows)
    out = solve(df_demo, params={"target_item": "阿甘正传", "min_count": 10, "top_n": 5})
    print(out["recommendations"])

