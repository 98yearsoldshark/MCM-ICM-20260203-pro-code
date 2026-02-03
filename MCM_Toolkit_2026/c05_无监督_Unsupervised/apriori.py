# -*- coding: utf-8 -*-
# Apriori：频繁项集与关联规则（纯 Python 实现，适合中小规模数据）

from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple, Union

import pandas as pd


def _to_transactions(data: Any) -> List[FrozenSet[str]]:
    """
    将输入数据标准化为 transactions（每条交易是一个 frozenset[str]）。

    支持：
    - list[list[str]] / list[set[str]]
    - pandas.DataFrame：一热编码（列名为 item，值为 0/1）
    """
    if isinstance(data, pd.DataFrame):
        # 认为是 one-hot：非 0 表示出现
        tx: List[FrozenSet[str]] = []
        for _, row in data.iterrows():
            items = [str(col) for col, v in row.items() if bool(v)]
            tx.append(frozenset(items))
        return tx

    if isinstance(data, (list, tuple)):
        tx = []
        for t in data:
            if isinstance(t, (set, frozenset, list, tuple)):
                tx.append(frozenset(str(x) for x in t))
            else:
                raise TypeError("transactions 必须是可迭代的 item 集合。")
        return tx

    raise TypeError("不支持的 transactions 数据类型。")


def _support_count(transactions: Sequence[FrozenSet[str]], itemset: FrozenSet[str]) -> int:
    return sum(1 for t in transactions if itemset.issubset(t))


def apriori_frequent_itemsets(
    transactions: Sequence[FrozenSet[str]],
    *,
    min_support: float = 0.4,
    max_len: Optional[int] = None,
) -> Dict[FrozenSet[str], float]:
    """
    挖掘频繁项集。

    Args:
        transactions: 交易列表。
        min_support: 最小支持度（0~1）。
        max_len: 最大项集长度（None 表示不限制）。

    Returns:
        dict: itemset -> support（支持度）
    """
    n = len(transactions)
    if n == 0:
        return {}

    # 1-项集
    items = sorted({i for t in transactions for i in t})
    freq: Dict[FrozenSet[str], float] = {}

    Lk: List[FrozenSet[str]] = []
    for it in items:
        fs = frozenset([it])
        sup = _support_count(transactions, fs) / n
        if sup >= min_support:
            freq[fs] = sup
            Lk.append(fs)

    k = 2
    while Lk:
        if max_len is not None and k > max_len:
            break

        # 生成候选集 Ck：join step
        candidates: set[FrozenSet[str]] = set()
        Lk_sorted = sorted(Lk, key=lambda s: sorted(s))
        for i in range(len(Lk_sorted)):
            for j in range(i + 1, len(Lk_sorted)):
                a = sorted(Lk_sorted[i])
                b = sorted(Lk_sorted[j])
                if a[: k - 2] != b[: k - 2]:
                    break
                cand = frozenset(set(a) | set(b))
                if len(cand) == k:
                    candidates.add(cand)

        # prune：若 cand 的任意 (k-1) 子集不在 Lk，则删掉
        Lk_set = set(Lk)
        pruned: List[FrozenSet[str]] = []
        for cand in candidates:
            ok = True
            for sub in combinations(cand, k - 1):
                if frozenset(sub) not in Lk_set:
                    ok = False
                    break
            if ok:
                pruned.append(cand)

        # 计数筛选
        new_Lk: List[FrozenSet[str]] = []
        for cand in pruned:
            sup = _support_count(transactions, cand) / n
            if sup >= min_support:
                freq[cand] = sup
                new_Lk.append(cand)

        Lk = new_Lk
        k += 1

    return freq


def association_rules(
    frequent_itemsets: Dict[FrozenSet[str], float],
    *,
    min_confidence: float = 0.8,
    min_lift: float = 1.0,
) -> pd.DataFrame:
    """
    从频繁项集生成关联规则。

    Args:
        frequent_itemsets: itemset->support。
        min_confidence: 最小置信度。
        min_lift: 最小提升度。

    Returns:
        pd.DataFrame: 规则表（antecedent, consequent, support, confidence, lift）。
    """
    rows: List[Dict[str, Any]] = []

    for itemset, sup_xy in frequent_itemsets.items():
        if len(itemset) < 2:
            continue
        items = sorted(itemset)
        for r in range(1, len(items)):
            for ante in combinations(items, r):
                X = frozenset(ante)
                Y = itemset - X
                sup_x = frequent_itemsets.get(X)
                sup_y = frequent_itemsets.get(Y)
                if sup_x is None or sup_y is None or sup_x == 0:
                    continue
                conf = sup_xy / sup_x
                lift = conf / sup_y if sup_y > 0 else float("inf")
                if conf >= min_confidence and lift >= min_lift:
                    rows.append(
                        {
                            "antecedent": tuple(sorted(X)),
                            "consequent": tuple(sorted(Y)),
                            "support": sup_xy,
                            "confidence": conf,
                            "lift": lift,
                        }
                    )

    return pd.DataFrame(rows).sort_values(["confidence", "lift"], ascending=False).reset_index(drop=True)


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：Apriori 频繁项集 + 关联规则。

    Args:
        data: 交易数据，支持 list[list[str]] 或 one-hot DataFrame。
        params: 参数：
            - min_support: float（默认 0.4）
            - max_len: int | None
            - min_confidence: float（默认 0.8）
            - min_lift: float（默认 1.0）

    Returns:
        dict:
            - frequent_itemsets: DataFrame（itemset, support）
            - rules: DataFrame（antecedent, consequent, support, confidence, lift）
    """
    params = params or {}
    tx = _to_transactions(data)

    min_support = float(params.get("min_support", 0.4))
    max_len = params.get("max_len")
    if max_len is not None:
        max_len = int(max_len)

    freq = apriori_frequent_itemsets(tx, min_support=min_support, max_len=max_len)
    fi = (
        pd.DataFrame(
            [{"itemset": tuple(sorted(k)), "support": v} for k, v in freq.items()],
        )
        .sort_values("support", ascending=False)
        .reset_index(drop=True)
    )

    rules = association_rules(
        freq,
        min_confidence=float(params.get("min_confidence", 0.8)),
        min_lift=float(params.get("min_lift", 1.0)),
    )
    return {"frequent_itemsets": fi, "rules": rules}


if __name__ == "__main__":
    # Mock Data
    transactions = [["A", "B", "C"], ["A", "B"], ["B", "C"], ["A", "B", "C", "D"], ["B", "C", "D"]]
    out = solve(transactions, params={"min_support": 0.4, "min_confidence": 0.8})
    print(out["frequent_itemsets"])
    print(out["rules"])

