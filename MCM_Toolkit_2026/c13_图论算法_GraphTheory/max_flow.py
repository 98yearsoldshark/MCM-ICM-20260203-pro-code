# -*- coding: utf-8 -*-
# 最大流（Max Flow）：scipy.sparse.csgraph.maximum_flow
#
# 参考来源（资料目录）：
# - 4、Python各类算法代码集合/41-2 .../10第10章 图论模型/.../Pex10_16.py（networkx.maximum_flow）
#
# 说明：
# - SciPy 的 maximum_flow 返回“反对称”的流矩阵（含反向边的负值）
# - 这里把它转成常见的“非负流量邻接矩阵”（仅保留正向流）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_flow

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _build_capacity_matrix(
    *,
    n: int,
    edges: Sequence[Tuple[int, int, Union[int, float]]],
    directed: bool = True,
) -> np.ndarray:
    cap = np.zeros((n, n), dtype=int)
    for u, v, c in edges:
        ci = int(round(float(c)))
        if not np.isclose(ci, float(c)):
            raise ValueError("SciPy maximum_flow 要求容量为整数；请提供整数 capacity。")
        cap[int(u), int(v)] += ci
        if not directed:
            cap[int(v), int(u)] += ci
    return cap


def max_flow(
    capacity: Union[np.ndarray, Sequence[Sequence[float]]],
    *,
    source: int,
    sink: int,
) -> Dict[str, Any]:
    """
    求解最大流。

    Args:
        capacity: 容量矩阵（n×n），capacity[i,j] 表示 i->j 的容量（>=0）。
        source: 源点编号（0-based）。
        sink: 汇点编号（0-based）。

    Returns:
        dict:
            - flow_value: 最大流量
            - flow_matrix: ndarray (n×n)，非负流量矩阵（只保留正向流）
            - flow_edges: list[(u,v,flow,cap)]（只列出 flow>0 的边）
            - result: SciPy MaximumFlowResult（原始结果，含反对称 flow）
    """
    cap_in = np.asarray(capacity)
    if cap_in.dtype.kind in {"f"}:
        cap_round = np.round(cap_in)
        if not np.allclose(cap_in, cap_round):
            raise ValueError("SciPy maximum_flow 要求容量为整数；请提供整数 capacity。")
        cap = cap_round.astype(int)
    else:
        cap = cap_in.astype(int)
    if cap.ndim != 2 or cap.shape[0] != cap.shape[1]:
        raise ValueError("capacity 必须为 n×n 方阵。")
    if np.any(cap < 0):
        raise ValueError("capacity 不能为负。")
    n = int(cap.shape[0])
    s = int(source)
    t = int(sink)
    if not (0 <= s < n and 0 <= t < n):
        raise ValueError("source/sink 超出范围。")
    if s == t:
        raise ValueError("source 与 sink 不能相同。")

    res = maximum_flow(csr_matrix(cap), s, t)
    flow_raw = res.flow.toarray().astype(int)
    flow_mat = np.maximum(flow_raw, 0).astype(int)
    flow_edges: List[Tuple[int, int, float, float]] = []
    ui, vi = np.nonzero(flow_mat > 0)
    for u, v in zip(ui.tolist(), vi.tolist()):
        flow_edges.append((int(u), int(v), float(flow_mat[u, v]), float(cap[u, v])))

    return {"flow_value": float(res.flow_value), "flow_matrix": flow_mat, "flow_edges": flow_edges, "result": res}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：最大流。

    Args:
        data: 支持：
            - capacity 矩阵（n×n）
            - dict:
                - {'capacity': cap, 'source': s, 'sink': t}
                - 或 {'n': n, 'edges': [(u,v,cap),...], 'source': s, 'sink': t}
        params: 预留（当前未用）

    Returns:
        dict: 见 max_flow()。
    """
    _ = params or {}

    if isinstance(data, dict):
        if "capacity" in data:
            cap = data["capacity"]
        elif "n" in data and "edges" in data:
            cap = _build_capacity_matrix(n=int(data["n"]), edges=data["edges"], directed=True)
        else:
            raise ValueError("data dict 需要包含 capacity 或 (n, edges)。")
        s = data.get("source")
        t = data.get("sink")
    else:
        cap = data
        s = None
        t = None

    if s is None or t is None:
        raise ValueError("需要提供 source 与 sink（0-based）。")

    return max_flow(cap, source=int(s), sink=int(t))


if __name__ == "__main__":
    # Mock Data：复现资料中的示例（Pex10_16）
    edges = [
        (0, 1, 5),
        (0, 2, 3),
        (1, 3, 2),
        (2, 1, 1),
        (2, 4, 4),
        (3, 2, 1),
        (3, 4, 3),
        (3, 5, 2),
        (4, 5, 5),
    ]
    cap = _build_capacity_matrix(n=6, edges=edges)
    out = solve({"capacity": cap, "source": 0, "sink": 5})
    print("flow_value =", out["flow_value"])
    print("flow_edges =", out["flow_edges"])
