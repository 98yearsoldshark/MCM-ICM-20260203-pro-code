# -*- coding: utf-8 -*-
# 最小费用最大流（Min-Cost Max-Flow）
#
# 参考来源（资料目录）：
# - 4、Python各类算法代码集合/41-2 .../10第10章 图论模型/.../Pex10_17.py（networkx.max_flow_min_cost）
#
# 说明：
# - SciPy 没有直接提供 min_cost_flow，这里用“线性规划”方式求解：
#   1) 先用最大流（scipy.sparse.csgraph.maximum_flow）求最大流量 Fmax
#   2) 固定流量为 Fmax，解一个线性规划 min Σ cost_e * f_e
#      s.t. 流守恒 + 0<=f_e<=cap_e
#
# 优点：不需要额外依赖（不强制 networkx）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_flow

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


Edge = Tuple[int, int, Union[int, float], Union[int, float]]  # (u,v,cap,cost)


def _infer_n(edges: Sequence[Edge], n: Optional[int]) -> int:
    if n is not None:
        nn = int(n)
        if nn <= 0:
            raise ValueError("n 必须为正整数。")
        return nn
    mx = -1
    for u, v, *_ in edges:
        mx = max(mx, int(u), int(v))
    if mx < 0:
        raise ValueError("edges 不能为空，或请显式提供 n。")
    return mx + 1


def _max_flow_value(n: int, edges: Sequence[Edge], source: int, sink: int) -> float:
    cap_mat = np.zeros((n, n), dtype=int)
    for u, v, cap, _cost in edges:
        c = float(cap)
        if c < 0:
            raise ValueError("cap 不能为负。")
        ci = int(round(c))
        if not np.isclose(ci, c):
            raise ValueError("SciPy maximum_flow 要求容量为整数；请提供整数 cap。")
        cap_mat[int(u), int(v)] += ci
    res = maximum_flow(csr_matrix(cap_mat), int(source), int(sink))
    return float(res.flow_value)


def min_cost_flow_given_value(
    *,
    n: int,
    edges: Sequence[Edge],
    source: int,
    sink: int,
    flow_value: float,
) -> Dict[str, Any]:
    """
    固定总流量 F，求最小费用流。
    """
    s = int(source)
    t = int(sink)
    if not (0 <= s < n and 0 <= t < n):
        raise ValueError("source/sink 超出范围。")
    if s == t:
        raise ValueError("source 与 sink 不能相同。")

    F = float(flow_value)
    if F < 0:
        raise ValueError("flow_value 不能为负。")

    m = int(len(edges))
    if m == 0:
        return {"success": True, "flow_value": 0.0, "min_cost": 0.0, "edge_flows": [], "result": None}

    c = np.array([float(cost) for *_uvc, cost in edges], dtype=float)
    bounds = [(0.0, float(cap)) for _u, _v, cap, _cost in edges]

    # 流守恒：对每个节点 i：sum_out - sum_in = b_i
    Aeq = np.zeros((n, m), dtype=float)
    for e, (u, v, _cap, _cost) in enumerate(edges):
        u_i = int(u)
        v_i = int(v)
        Aeq[u_i, e] += 1.0
        Aeq[v_i, e] -= 1.0

    beq = np.zeros(n, dtype=float)
    beq[s] = F
    beq[t] = -F

    res = linprog(c, A_eq=Aeq, b_eq=beq, bounds=bounds, method="highs")
    if not res.success:
        return {"success": False, "message": str(res.message), "result": res}

    x = np.asarray(res.x, dtype=float).reshape(-1)
    edge_flows: List[Tuple[int, int, float, float, float]] = []
    for (u, v, cap, cost), f in zip(edges, x.tolist()):
        if f > 0:
            edge_flows.append((int(u), int(v), float(f), float(cap), float(cost)))

    return {
        "success": True,
        "flow_value": F,
        "min_cost": float(res.fun),
        "edge_flows": edge_flows,
        "x": x,
        "result": res,
    }


def min_cost_max_flow(
    edges: Sequence[Edge],
    *,
    source: int,
    sink: int,
    n: Optional[int] = None,
) -> Dict[str, Any]:
    """
    最小费用最大流：先求最大流量，再求该流量下的最小费用流。
    """
    nn = _infer_n(edges, n)
    Fmax = _max_flow_value(nn, edges, source, sink)
    out = min_cost_flow_given_value(n=nn, edges=edges, source=source, sink=sink, flow_value=Fmax)
    out["max_flow_value"] = Fmax
    out["n"] = nn
    return out


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：最小费用最大流。

    Args:
        data: dict，包含：
            - edges: list[(u,v,cap,cost)]
            - source: int
            - sink: int
            - n: int（可选）
        params:
            - flow_value: float | None（若提供，则固定该流量求最小费用；否则求最小费用最大流）

    Returns:
        dict: 见 min_cost_max_flow() / min_cost_flow_given_value()。
    """
    params = params or {}
    if not isinstance(data, dict) or "edges" not in data or "source" not in data or "sink" not in data:
        raise TypeError("data 必须为 dict，且包含 edges/source/sink。")
    edges = data["edges"]
    s = int(data["source"])
    t = int(data["sink"])
    n = data.get("n")

    if params.get("flow_value") is not None:
        nn = _infer_n(edges, n)
        return min_cost_flow_given_value(n=nn, edges=edges, source=s, sink=t, flow_value=float(params["flow_value"]))
    return min_cost_max_flow(edges, source=s, sink=t, n=n)


if __name__ == "__main__":
    # Mock Data：复现资料 Pex10_17 的示例（1-based 改为 0-based）
    edges: List[Edge] = [
        (0, 1, 5, 3),
        (0, 2, 3, 6),
        (1, 3, 2, 8),
        (2, 1, 1, 2),
        (2, 4, 4, 2),
        (3, 2, 1, 1),
        (3, 4, 3, 4),
        (3, 5, 2, 10),
        (4, 5, 5, 2),
    ]
    out = solve({"edges": edges, "source": 0, "sink": 5})
    print("max_flow_value =", out.get("max_flow_value"))
    print("min_cost =", out.get("min_cost"))
    print("edge_flows =", out.get("edge_flows"))
