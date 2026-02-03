"""
生成 SmartDrain 插图用的小图标（PNG）。

说明：
- 图标用于 Graphviz(DOT) 的 HTML Label 中的 <IMG SRC="...">。
- 为避免版权/授权问题，这里用 PIL 直接绘制简单的线性图标。
- 默认同时输出两套尺寸：64px（预览/备用）与 24px（嵌入论文插图更紧凑）。
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


STROKE = (51, 65, 85, 255)  # #334155
FILL = (255, 255, 255, 0)  # transparent


def _rounded_rect(draw: ImageDraw.ImageDraw, xy, r: int, outline, width: int) -> None:
    # PIL >= 8.2: rounded_rectangle
    draw.rounded_rectangle(xy, radius=r, outline=outline, width=width)


def icon_phone(size: int = 64) -> Image.Image:
    im = Image.new("RGBA", (size, size), FILL)
    d = ImageDraw.Draw(im)
    w = max(2, size // 16)
    pad = size // 8
    _rounded_rect(d, (pad, pad, size - pad, size - pad), r=size // 8, outline=STROKE, width=w)
    # screen
    sp = pad + size // 10
    _rounded_rect(d, (sp, sp, size - sp, size - sp - size // 8), r=size // 12, outline=STROKE, width=w)
    # home button
    cx = size // 2
    cy = size - pad - size // 12
    r = size // 20
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=STROKE, width=w)
    return im


def icon_chip(size: int = 64) -> Image.Image:
    im = Image.new("RGBA", (size, size), FILL)
    d = ImageDraw.Draw(im)
    w = max(2, size // 18)
    pad = size // 4
    _rounded_rect(d, (pad, pad, size - pad, size - pad), r=size // 16, outline=STROKE, width=w)
    # inner core
    ip = pad + size // 10
    _rounded_rect(d, (ip, ip, size - ip, size - ip), r=size // 20, outline=STROKE, width=w)
    # pins
    pin_len = size // 10
    pin_gap = size // 6
    for x in (size // 2 - pin_gap, size // 2, size // 2 + pin_gap):
        d.line((x, pad - pin_len, x, pad), fill=STROKE, width=w)
        d.line((x, size - pad, x, size - pad + pin_len), fill=STROKE, width=w)
    for y in (size // 2 - pin_gap, size // 2, size // 2 + pin_gap):
        d.line((pad - pin_len, y, pad, y), fill=STROKE, width=w)
        d.line((size - pad, y, size - pad + pin_len, y), fill=STROKE, width=w)
    return im


def icon_battery(size: int = 64) -> Image.Image:
    im = Image.new("RGBA", (size, size), FILL)
    d = ImageDraw.Draw(im)
    w = max(2, size // 18)
    pad = size // 6
    # body
    body = (pad, pad + size // 6, size - pad - size // 10, size - pad - size // 6)
    _rounded_rect(d, body, r=size // 10, outline=STROKE, width=w)
    # nub
    nub_w = size // 12
    nub_h = size // 6
    x0 = body[2]
    y0 = size // 2 - nub_h // 2
    _rounded_rect(d, (x0, y0, x0 + nub_w, y0 + nub_h), r=size // 20, outline=STROKE, width=w)
    # plus sign
    cx = (body[0] + body[2]) // 2
    cy = (body[1] + body[3]) // 2
    L = size // 6
    d.line((cx - L // 2, cy, cx + L // 2, cy), fill=STROKE, width=w)
    d.line((cx, cy - L // 2, cx, cy + L // 2), fill=STROKE, width=w)
    return im


def icon_screen(size: int = 64) -> Image.Image:
    """屏幕/显示模块（矩形屏幕）。"""
    im = Image.new("RGBA", (size, size), FILL)
    d = ImageDraw.Draw(im)
    w = max(2, size // 18)
    pad = size // 6
    _rounded_rect(d, (pad, pad, size - pad, size - pad), r=size // 10, outline=STROKE, width=w)
    # inner bezel
    ip = pad + size // 10
    _rounded_rect(d, (ip, ip, size - ip, size - ip), r=size // 14, outline=STROKE, width=max(1, w - 1))
    # small status bar hint
    d.line((ip + size // 10, ip + size // 8, size - ip - size // 10, ip + size // 8), fill=STROKE, width=max(1, w - 1))
    return im


def icon_wifi(size: int = 64) -> Image.Image:
    """网络/通信（Wi‑Fi 弧线）。"""
    im = Image.new("RGBA", (size, size), FILL)
    d = ImageDraw.Draw(im)
    w = max(2, size // 18)
    cx = cy = size // 2
    # arcs
    for r in (size * 2 // 5, size // 3, size // 5):
        bbox = (cx - r, cy - r, cx + r, cy + r)
        d.arc(bbox, start=210, end=330, fill=STROKE, width=w)
    # dot
    r = max(2, size // 18)
    d.ellipse((cx - r, cy + size // 6 - r, cx + r, cy + size // 6 + r), fill=STROKE, outline=STROKE)
    return im


def icon_gps(size: int = 64) -> Image.Image:
    """定位（简化位置 pin）。"""
    im = Image.new("RGBA", (size, size), FILL)
    d = ImageDraw.Draw(im)
    w = max(2, size // 18)
    cx = size // 2
    top = size // 5
    r = size * 2 // 9
    # circle head
    d.ellipse((cx - r, top, cx + r, top + 2 * r), outline=STROKE, width=w)
    # inner dot
    rr = max(2, r // 3)
    d.ellipse((cx - rr, top + r - rr, cx + rr, top + r + rr), fill=STROKE, outline=STROKE)
    # tail triangle
    tip_y = size - size // 6
    d.polygon([(cx, tip_y), (cx - r + 2, top + 2 * r - 2), (cx + r - 2, top + 2 * r - 2)], outline=STROKE, fill=None)
    d.line((cx, tip_y, cx - r + 2, top + 2 * r - 2), fill=STROKE, width=w)
    d.line((cx, tip_y, cx + r - 2, top + 2 * r - 2), fill=STROKE, width=w)
    return im


def icon_layers(size: int = 64) -> Image.Image:
    """后台/系统（叠层矩形）。"""
    im = Image.new("RGBA", (size, size), FILL)
    d = ImageDraw.Draw(im)
    w = max(2, size // 18)
    pad = size // 5
    off = size // 10
    _rounded_rect(d, (pad + off, pad - off, size - pad + off, size - pad - off), r=size // 14, outline=STROKE, width=w)
    _rounded_rect(d, (pad - off, pad + off, size - pad - off, size - pad + off), r=size // 14, outline=STROKE, width=w)
    return im


def icon_tap(size: int = 64) -> Image.Image:
    """交互/触控（触点 + 波纹）。"""
    im = Image.new("RGBA", (size, size), FILL)
    d = ImageDraw.Draw(im)
    w = max(2, size // 18)
    cx = cy = size // 2
    # ripple arcs
    for r in (size // 4, size // 3):
        bbox = (cx - r, cy - r, cx + r, cy + r)
        d.arc(bbox, start=20, end=200, fill=STROKE, width=max(1, w - 1))
    # touch point
    r0 = max(2, size // 10)
    d.ellipse((cx - r0, cy - r0, cx + r0, cy + r0), outline=STROKE, width=w)
    d.ellipse((cx - r0 // 2, cy - r0 // 2, cx + r0 // 2, cy + r0 // 2), fill=STROKE, outline=STROKE)
    return im


def icon_bolt(size: int = 64) -> Image.Image:
    """基础/常驻功耗（闪电）。"""
    im = Image.new("RGBA", (size, size), FILL)
    d = ImageDraw.Draw(im)
    w = max(2, size // 18)
    # simple bolt polyline
    x0 = size * 3 // 7
    y0 = size // 7
    pts = [
        (x0 + size // 10, y0),
        (x0 - size // 12, size * 4 // 9),
        (x0 + size // 8, size * 4 // 9),
        (x0 - size // 10, size - size // 7),
        (x0 + size * 3 // 10, size * 5 // 9),
        (x0 + size // 10, size * 5 // 9),
    ]
    d.line(pts + [pts[0]], fill=STROKE, width=w, joint="curve")
    return im


def main() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    out_dir = base_dir / "assets" / "icons"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 说明：
    # - Graphviz 的 <IMG> 不一定支持 WIDTH/HEIGHT 控制尺寸（不同版本差异较大）。
    # - 因此我们用“预先生成不同像素尺寸的 PNG”来稳定控制图标在 DOT 中的占用空间。
    # - 50px：更大图标（用于“更醒目”的版式实验）
    # - 28px：用于模块小格子里（更醒目；适合论文缩放后仍可辨识）
    # - 24px：用于节点标题等位置
    # - 20px：更紧凑的备用尺寸
    sizes = [64, 50, 28, 24, 20]
    for sz in sizes:
        suffix = "" if sz == 64 else f"_{sz}"
        icons = {
            f"phone{suffix}.png": icon_phone(size=sz),
            f"chip{suffix}.png": icon_chip(size=sz),
            f"battery{suffix}.png": icon_battery(size=sz),
            f"screen{suffix}.png": icon_screen(size=sz),
            f"wifi{suffix}.png": icon_wifi(size=sz),
            f"gps{suffix}.png": icon_gps(size=sz),
            f"layers{suffix}.png": icon_layers(size=sz),
            f"tap{suffix}.png": icon_tap(size=sz),
            f"bolt{suffix}.png": icon_bolt(size=sz),
        }
        for name, im in icons.items():
            path = out_dir / name
            im.save(path, format="PNG")
            print(f"[OK] {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
