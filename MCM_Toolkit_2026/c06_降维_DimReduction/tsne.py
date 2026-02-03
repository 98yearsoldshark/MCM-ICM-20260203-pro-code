# -*- coding: utf-8 -*-
# t-SNE：非线性降维可视化（sklearn.manifold.TSNE）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../数据处理类题型参考代码.../基于t-sne算法的降维可视化实例

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
from sklearn.manifold import TSNE

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def tsne_embed(
    X: Union[np.ndarray, list],
    *,
    n_components: int = 2,
    perplexity: float = 30.0,
    learning_rate: Union[str, float] = "auto",
    max_iter: int = 1000,
    init: str = "pca",
    random_state: int = 0,
) -> Dict[str, Any]:
    """
    t-SNE 降维嵌入。

    Args:
        X: (n×d) 特征矩阵。
        n_components: 输出维度（默认 2）。
        perplexity: 困惑度（与邻域大小相关，常用 5~50）。
        learning_rate: 学习率（可用 'auto'）。
        max_iter: 迭代次数。
        init: 初始化方式（'pca' 或 'random'）。
        random_state: 随机种子。

    Returns:
        dict:
            - embedding: (n×n_components)
            - model: TSNE 对象（便于查看参数）
    """
    X_arr = np.asarray(X, dtype=float)
    if X_arr.ndim != 2:
        raise ValueError("X 必须为二维矩阵 (n×d)。")

    model = TSNE(
        n_components=int(n_components),
        perplexity=float(perplexity),
        learning_rate=learning_rate,
        max_iter=int(max_iter),
        init=str(init),
        random_state=int(random_state),
    )
    emb = model.fit_transform(X_arr)
    return {"embedding": np.asarray(emb, dtype=float), "model": model}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：t-SNE 降维。

    Args:
        data: 矩阵或 dict：
            - 直接传入 X
            - dict: {'X': X}
        params: 参数：
            - n_components/perplexity/learning_rate/n_iter/init/random_state

    Returns:
        dict: {'embedding': ...}
    """
    params = params or {}
    if isinstance(data, dict):
        X = data.get("X")
    else:
        X = data
    if X is None:
        raise ValueError("data 需要提供 X。")

    return tsne_embed(
        X,
        n_components=int(params.get("n_components", 2)),
        perplexity=float(params.get("perplexity", 30.0)),
        learning_rate=params.get("learning_rate", "auto"),
        max_iter=int(params.get("max_iter", params.get("n_iter", 1000))),
        init=str(params.get("init", "pca")),
        random_state=int(params.get("random_state", 0)),
    )


if __name__ == "__main__":
    # Mock Data：3 团高维数据 -> 2D 可视化嵌入
    rng = np.random.default_rng(0)
    X1 = rng.normal(0, 1, size=(100, 10))
    X2 = rng.normal(4, 1, size=(100, 10))
    X3 = rng.normal(-3, 1, size=(100, 10))
    X = np.vstack([X1, X2, X3])

    out = solve(X, {"perplexity": 30, "max_iter": 800, "random_state": 0})
    print("embedding shape =", out["embedding"].shape)
