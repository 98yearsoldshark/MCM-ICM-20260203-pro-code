from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageFilter, ImageOps


@dataclass(frozen=True)
class CropFrac:
    """按比例裁剪：left/right/top/bottom 取值在 [0,1]。"""

    left: float
    right: float
    top: float
    bottom: float


@dataclass(frozen=True)
class PaperTarget:
    id: str
    desc: str
    image_path: Path
    crop_frac: CropFrac


def _to_crop_frac(d: Dict[str, Any]) -> CropFrac:
    return CropFrac(
        left=float(d["left"]),
        right=float(d["right"]),
        top=float(d["top"]),
        bottom=float(d["bottom"]),
    )


def load_targets_from_json(path: Path) -> List[PaperTarget]:
    import json

    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)

    targets: List[PaperTarget] = []
    for t in obj.get("targets", []):
        targets.append(
            PaperTarget(
                id=str(t["id"]),
                desc=str(t.get("desc", "")),
                image_path=Path(str(t["image_path"])),
                crop_frac=_to_crop_frac(t["crop_frac"]),
            )
        )
    return targets


def crop_image_by_frac(img: Image.Image, crop: CropFrac) -> Image.Image:
    w, h = img.size
    l = int(round(w * crop.left))
    r = int(round(w * crop.right))
    t = int(round(h * crop.top))
    b = int(round(h * crop.bottom))
    l = max(0, min(l, w - 1))
    r = max(l + 1, min(r, w))
    t = max(0, min(t, h - 1))
    b = max(t + 1, min(b, h))
    return img.crop((l, t, r, b))


def load_and_crop(path: Path, crop: CropFrac) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # 避免某些图片带 EXIF 旋转信息
    return crop_image_by_frac(img, crop)


def to_gray_array(
    img: Image.Image,
    *,
    out_size: Tuple[int, int],
    blur_radius: float = 0.0,
    normalize: bool = True,
) -> np.ndarray:
    """将图片转为灰度数组，用于相似度比较。"""

    if blur_radius > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=float(blur_radius)))

    g = img.convert("L").resize(out_size, Image.BILINEAR)
    a = np.asarray(g, dtype=float)

    if normalize:
        # 归一化到 [0,1]，减少“配色/曝光”对相似度的影响
        mn = float(np.min(a))
        mx = float(np.max(a))
        if mx > mn:
            a = (a - mn) / (mx - mn)
        else:
            a = np.zeros_like(a)
    return a


def pearson_corr(a: np.ndarray, b: np.ndarray) -> float:
    """两幅同尺寸灰度图的皮尔逊相关系数（[-1,1]）。"""

    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    if a.size != b.size or a.size == 0:
        return float("nan")

    a = a - float(np.mean(a))
    b = b - float(np.mean(b))

    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def gradient_magnitude_mean(img01: np.ndarray) -> float:
    """计算平均梯度幅值（paper 里用来衡量“光滑性”）。"""

    # Sobel-like：简单差分即可体现粗糙度差异（无需引入 skimage）
    gx = np.diff(img01, axis=1, append=img01[:, -1:])
    gy = np.diff(img01, axis=0, append=img01[-1:, :])
    g = np.sqrt(gx * gx + gy * gy)
    return float(np.mean(g))


def find_darkest_center(img01: np.ndarray) -> Tuple[float, float]:
    """返回最暗像素的 (y_frac, x_frac) 位置，用于对齐磨损中心。"""

    idx = int(np.argmin(img01))
    h, w = img01.shape
    y = idx // w
    x = idx % w
    return (y / max(1, h - 1), x / max(1, w - 1))


def side_by_side(
    left: Image.Image,
    right: Image.Image,
    *,
    pad: int = 10,
    bg: Tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    lw, lh = left.size
    rw, rh = right.size
    h = max(lh, rh)
    out = Image.new("RGB", (lw + pad + rw, h), color=bg)
    out.paste(left.convert("RGB"), (0, (h - lh) // 2))
    out.paste(right.convert("RGB"), (lw + pad, (h - rh) // 2))
    return out

