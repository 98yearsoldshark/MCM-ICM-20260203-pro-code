# -*- coding: utf-8 -*-
"""可选依赖的统一处理（缺包时给出清晰提示）。"""

from __future__ import annotations

import importlib
from typing import Any, Optional


def is_installed(import_name: str) -> bool:
    """判断某个模块是否已安装。"""
    try:
        importlib.import_module(import_name)
        return True
    except Exception:
        return False


def require_package(import_name: str, *, pip_name: Optional[str] = None, extra_hint: str = "") -> Any:
    """
    导入可选依赖；若不存在则抛出带安装建议的 ImportError。

    Args:
        import_name: Python import 名称（如 'xgboost'）。
        pip_name: pip 安装名（默认与 import_name 相同）。
        extra_hint: 额外提示（可为空）。

    Returns:
        module: 成功导入后的模块对象。
    """
    pip_name = pip_name or import_name
    try:
        return importlib.import_module(import_name)
    except Exception as e:
        hint = f"缺少可选依赖：`{import_name}`。可执行：`pip install {pip_name}`。"
        if extra_hint:
            hint = hint + " " + extra_hint.strip()
        raise ImportError(hint) from e

