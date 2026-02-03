# -*- coding: utf-8 -*-
"""常用文件读取工具：CSV/Excel/TXT（比赛时少写路径处理）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd


def read_table(path: Union[str, Path], *, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    根据后缀自动读取表格数据。

    Args:
        path: 文件路径（csv/xlsx/xls）。
        params: 透传给 pandas 的参数（如 read_csv 的 encoding、sep 等）。

    Returns:
        pd.DataFrame
    """
    params = params or {}
    p = Path(path)
    suf = p.suffix.lower()
    if suf in {".xlsx", ".xls"}:
        return pd.read_excel(p, **params)
    if suf == ".csv":
        return pd.read_csv(p, **params)
    raise ValueError(f"不支持的表格格式：{p.suffix}（仅支持 csv/xlsx/xls）")


def read_text(path: Union[str, Path], *, encoding: str = "utf-8") -> str:
    """读取纯文本文件。"""
    return Path(path).read_text(encoding=encoding, errors="replace")


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：读取文件（表格或文本）。

    Args:
        data: str/Path 或 dict {'path': ...}。
        params: 参数：
            - kind: {"table","text"}（默认按后缀推断：csv/xlsx/xls->table，其余->text）
            - table_params: dict（传给 read_table）
            - encoding: str（text 用）

    Returns:
        dict: {'data': DataFrame 或 str}
    """
    params = params or {}
    path = data.get("path") if isinstance(data, dict) else data
    if not isinstance(path, (str, Path)):
        raise TypeError("data 必须为 str/Path 或包含 path 的 dict。")

    p = Path(path)
    kind = params.get("kind")
    if not kind:
        kind = "table" if p.suffix.lower() in {".csv", ".xlsx", ".xls"} else "text"

    if kind == "table":
        table_params = dict(params.get("table_params", {}) or {})
        return {"data": read_table(p, params=table_params)}
    if kind == "text":
        return {"data": read_text(p, encoding=str(params.get("encoding", "utf-8")))}
    raise ValueError("kind 必须为 table 或 text。")


if __name__ == "__main__":
    # Mock：仅演示接口（不绑定具体文件）
    print("use solve({'path': 'xxx.xlsx'}) or solve({'path': 'xxx.txt'})")

