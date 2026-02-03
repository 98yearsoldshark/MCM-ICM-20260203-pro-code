"""
生成 SmartDrain 插图（最终版 PNG）。

用途：
- 只生成“论文可用”的最终 PNG（避免 out 目录堆满大量草稿/多格式输出）。
- 需要时仍可用 render_all.py 批量生成草稿版本做版式对比。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path) -> None:
    subprocess.run(cmd, check=True, cwd=str(cwd))


def _ensure_dot_available(*, cwd: Path) -> None:
    try:
        _run(["dot", "-V"], cwd=cwd)
    except Exception as e:  # pragma: no cover
        raise RuntimeError("未检测到 Graphviz(dot)。请先安装 Graphviz，并确保 dot 在 PATH 中。") from e


def _ensure_icons(*, base_dir: Path) -> None:
    icon_dir = base_dir / "assets" / "icons"
    required = [
        icon_dir / "phone_50.png",
        icon_dir / "battery_50.png",
        icon_dir / "bolt_50.png",
        icon_dir / "screen_50.png",
        icon_dir / "chip_50.png",
        icon_dir / "wifi_50.png",
        icon_dir / "gps_50.png",
        icon_dir / "layers_50.png",
        icon_dir / "tap_50.png",
    ]
    if all(p.exists() for p in required):
        return
    _run([sys.executable, str(base_dir / "scripts" / "make_icons.py")], cwd=base_dir)


def main() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    src_dir = base_dir / "src"
    out_dir = base_dir / "out" / "final"

    _ensure_dot_available(cwd=base_dir)
    _ensure_icons(base_dir=base_dir)

    figures = [
        # (mode, dot_filename, out_filename)
        ("paper", "fig01_power_model_paper_final_icons.dot", "fig01_power_model.png"),
        ("study", "fig01_power_model_study_final_icons.dot", "fig01_power_model.png"),
    ]

    for mode, dot_name, out_name in figures:
        in_path = src_dir / dot_name
        if not in_path.exists():
            raise FileNotFoundError(f"缺少 DOT 源文件：{in_path}")

        mode_dir = out_dir / mode
        mode_dir.mkdir(parents=True, exist_ok=True)
        out_png = mode_dir / out_name

        # PNG：提高 dpi 让文字更清晰（论文中缩放后仍清楚）
        _run(["dot", "-Tpng", "-Gdpi=320", str(in_path), "-o", str(out_png)], cwd=base_dir)

        print(f"[OK] {mode}: {out_png}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
