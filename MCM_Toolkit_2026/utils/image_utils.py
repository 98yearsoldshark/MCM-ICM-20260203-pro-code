# -*- coding: utf-8 -*-
"""图像预处理小工具（可选依赖 Pillow）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.optional_deps import require_package  # noqa: E402


def load_image(
    path: Union[str, Path],
    *,
    resize: Optional[Tuple[int, int]] = (32, 32),
    grayscale: bool = True,
) -> np.ndarray:
    """
    读取图片并转为 numpy 数组。

    Args:
        path: 图片路径。
        resize: (w,h)；None 表示不缩放。
        grayscale: 是否转灰度。

    Returns:
        np.ndarray: uint8 数组；灰度为 (H,W)，彩色为 (H,W,3)。
    """
    PIL = require_package("PIL", pip_name="pillow")
    Image = getattr(PIL, "Image")

    img = Image.open(str(path))
    if resize is not None:
        img = img.resize(resize)
    if grayscale:
        img = img.convert("L")
    else:
        img = img.convert("RGB")
    return np.array(img)


def binarize(arr: np.ndarray, *, threshold: int = 128, invert: bool = False) -> np.ndarray:
    """
    二值化处理。

    Args:
        arr: 灰度图数组 (H,W) 或彩色图 (H,W,3)（彩色会先转灰度近似）。
        threshold: 阈值（0~255）。
        invert: 是否反转（True 表示黑白互换）。

    Returns:
        np.ndarray: 0/1 数组 (H,W)。
    """
    if arr.ndim == 3:
        # 简易灰度：取平均
        gray = arr.mean(axis=2)
    else:
        gray = arr.astype(float)
    out = (gray <= threshold).astype(int)
    if invert:
        out = 1 - out
    return out


def flatten(arr: np.ndarray) -> np.ndarray:
    """
    将图像拉平成一维特征（形状 (1, -1)）。
    """
    return arr.reshape(1, -1)


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：图片 -> 二值化 -> 拉直向量。

    Args:
        data: 支持：
            - str/Path：图片路径
            - dict {'path': ...}
            - ndarray：直接给数组
        params: 参数：
            - resize: (w,h) | None（默认 (32,32)）
            - grayscale: bool（默认 True）
            - threshold: int（默认 128）
            - invert: bool（默认 False）
            - binarize: bool（默认 True；False 表示直接 flatten 原数组）

    Returns:
        dict:
            - vector: ndarray，形状 (1, n_features)
            - image: ndarray，处理后的图像数组
    """
    params = params or {}

    if isinstance(data, dict):
        obj = data.get("path", data.get("image", data.get("array")))
    else:
        obj = data

    if isinstance(obj, (str, Path)):
        arr = load_image(obj, resize=params.get("resize", (32, 32)), grayscale=bool(params.get("grayscale", True)))
    else:
        arr = np.asarray(obj)

    if bool(params.get("binarize", True)):
        img = binarize(arr, threshold=int(params.get("threshold", 128)), invert=bool(params.get("invert", False)))
    else:
        img = arr

    vec = flatten(np.asarray(img))
    return {"vector": vec, "image": img}


if __name__ == "__main__":
    # Mock Demo：无需真实图片，直接用随机“灰度图”
    rng = np.random.default_rng(0)
    fake_img = rng.integers(0, 256, size=(32, 32), dtype=np.uint8)
    out = solve(fake_img)
    print(out["vector"].shape)
