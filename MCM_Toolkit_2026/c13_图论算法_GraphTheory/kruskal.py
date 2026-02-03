# -*- coding: utf-8 -*-
# Kruskal 最小生成树（MST）：边排序 + 并查集
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/.../KRUSKAL.M

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


Edge = Tuple[int, int, float]


@dataclass
class UnionFind:
    parent: np.ndarray
    rank: np.ndarray

    @classmethod
    def create(cls, n: int) -> "UnionFind":
        return cls(parent=np.arange(n, dtype=int), rank=np.zeros(n, dtype=int))

    def find(self, x: int) -> int:
        x = int(x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = int(self.parent[x])
        return x

    def union(self, a: int, b: int) -> bool:
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            self.parent[ra] = rb
        elif self.rank[ra] > self.rank[rb]:
            self.parent[rb] = ra
        else:
            self.parent[rb] = ra
            self.rank[ra] += 1
        return True


def kruskal_mst(n: int, edges: Sequence[Edge]) -> Dict[str, Any]:
    """
    Kruskal 最小生成树。

    Args:
        n: 节点数（0..n-1）。
        edges: 边列表 [(u,v,w), ...]，无向图。

    Returns:
        dict:
            - mst_edges: MST 边列表
            - total_weight: 总权重
            - is_connected: 是否连通（若不连通则是最小生成森林）
    """
    if n <= 0:
        raise ValueError("n 必须 > 0。")
    edges_sorted = sorted([(int(u), int(v), float(w)) for u, v, w in edges], key=lambda e: e[2])

    uf = UnionFind.create(n)
    mst: List[Edge] = []
    total = 0.0
    for u, v, w in edges_sorted:
        if uf.union(u, v):
            mst.append((u, v, w))
            total += w
            if len(mst) == n - 1:
                break

    is_connected = len(mst) == n - 1
    return {"mst_edges": mst, "total_weight": float(total), "is_connected": is_connected}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：Kruskal MST。

    Args:
        data: dict，包含：
            - n: int
            - edges: list[(u,v,w)]
        params: 保留（暂无额外参数）

    Returns:
        dict: kruskal_mst() 返回值。
    """
    _ = params  # 保留接口一致性
    if not isinstance(data, dict) or "n" not in data or "edges" not in data:
        raise TypeError("data 必须为 dict，且包含 n 与 edges。")
    return kruskal_mst(int(data["n"]), data["edges"])


if __name__ == "__main__":
    edges = [
        (0, 1, 7),
        (0, 2, 9),
        (0, 5, 14),
        (1, 2, 10),
        (1, 3, 15),
        (2, 3, 11),
        (2, 5, 2),
        (3, 4, 6),
        (4, 5, 9),
    ]
    out = solve({"n": 6, "edges": edges})
    print("total_weight =", out["total_weight"])
    print("mst_edges =", out["mst_edges"])

