"""
生成 SmartDrain 论文插图（Graphviz/DOT）。

设计目标：
- 同一张图输出两套版本：paper（论文简洁版）与 study（学习解释版）
- 只输出 PNG（减少 out 目录杂乱；矢量版如需再单独补充）
- 批量生成的内容默认放到 out/drafts（避免污染最终产物 out/final）
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


def main() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    src_dir = base_dir / "src"
    out_dir = base_dir / "out" / "drafts"

    _ensure_dot_available(cwd=base_dir)

    figures = [
        # (mode, dot_filename, out_stem)
        ("paper", "fig01_power_model_paper.dot", "fig01_power_model"),
        ("study", "fig01_power_model_study.dot", "fig01_power_model"),
        ("paper", "fig01_power_model_paper_v2_grid.dot", "fig01_power_model_v2_grid"),
        ("study", "fig01_power_model_study_v2_grid.dot", "fig01_power_model_v2_grid"),
        ("paper", "fig01_power_model_paper_v3_floating.dot", "fig01_power_model_v3_floating"),
        ("study", "fig01_power_model_study_v3_floating.dot", "fig01_power_model_v3_floating"),
        ("paper", "fig01_power_model_paper_v4_list.dot", "fig01_power_model_v4_list"),
        ("study", "fig01_power_model_study_v4_list.dot", "fig01_power_model_v4_list"),
        ("paper", "fig01_power_model_paper_v5_list_compact.dot", "fig01_power_model_v5_list_compact"),
        ("study", "fig01_power_model_study_v5_list_compact.dot", "fig01_power_model_v5_list_compact"),
        ("paper", "fig01_power_model_paper_v6_grouped.dot", "fig01_power_model_v6_grouped"),
        ("study", "fig01_power_model_study_v6_grouped.dot", "fig01_power_model_v6_grouped"),
        ("paper", "fig01_power_model_paper_v7_equation.dot", "fig01_power_model_v7_equation"),
        ("study", "fig01_power_model_study_v7_equation.dot", "fig01_power_model_v7_equation"),
        ("paper", "fig01_power_model_paper_v8_direct.dot", "fig01_power_model_v8_direct"),
        ("study", "fig01_power_model_study_v8_direct.dot", "fig01_power_model_v8_direct"),
        ("paper", "fig01_power_model_paper_v9_pmic_inline_eta.dot", "fig01_power_model_v9_pmic_inline_eta"),
        ("study", "fig01_power_model_study_v9_pmic_inline_eta.dot", "fig01_power_model_v9_pmic_inline_eta"),
        ("paper", "fig01_power_model_paper_v10_compact_min.dot", "fig01_power_model_v10_compact_min"),
        ("study", "fig01_power_model_study_v10_compact_min.dot", "fig01_power_model_v10_compact_min"),
        ("paper", "fig01_power_model_paper_v11_equation_wrap.dot", "fig01_power_model_v11_equation_wrap"),
        ("study", "fig01_power_model_study_v11_equation_wrap.dot", "fig01_power_model_v11_equation_wrap"),
        ("paper", "fig01_power_model_paper_v12_equation_grouped.dot", "fig01_power_model_v12_equation_grouped"),
        ("study", "fig01_power_model_study_v12_equation_grouped.dot", "fig01_power_model_v12_equation_grouped"),
        ("paper", "fig01_power_model_paper_v13_tb_grid4x2.dot", "fig01_power_model_v13_tb_grid4x2"),
        ("study", "fig01_power_model_study_v13_tb_grid4x2.dot", "fig01_power_model_v13_tb_grid4x2"),
        ("paper", "fig01_power_model_paper_v14_tb_pmic_inline.dot", "fig01_power_model_v14_tb_pmic_inline"),
        ("study", "fig01_power_model_study_v14_tb_pmic_inline.dot", "fig01_power_model_v14_tb_pmic_inline"),
        ("paper", "fig01_power_model_paper_v15_tb_top_card_row_chain.dot", "fig01_power_model_v15_tb_top_card_row_chain"),
        ("study", "fig01_power_model_study_v15_tb_top_card_row_chain.dot", "fig01_power_model_v15_tb_top_card_row_chain"),
        ("paper", "fig01_power_model_paper_v16_tb_top_card_row_direct.dot", "fig01_power_model_v16_tb_top_card_row_direct"),
        ("study", "fig01_power_model_study_v16_tb_top_card_row_direct.dot", "fig01_power_model_v16_tb_top_card_row_direct"),
        ("paper", "fig01_power_model_paper_v17_tb_grid3x3_row_direct.dot", "fig01_power_model_v17_tb_grid3x3_row_direct"),
        ("study", "fig01_power_model_study_v17_tb_grid3x3_row_direct.dot", "fig01_power_model_v17_tb_grid3x3_row_direct"),
        ("paper", "fig01_power_model_paper_v18_tb_grid3x3_row_pmic.dot", "fig01_power_model_v18_tb_grid3x3_row_pmic"),
        ("study", "fig01_power_model_study_v18_tb_grid3x3_row_pmic.dot", "fig01_power_model_v18_tb_grid3x3_row_pmic"),
        ("paper", "fig01_power_model_paper_v19_tb_card_no_title.dot", "fig01_power_model_v19_tb_card_no_title"),
        ("study", "fig01_power_model_study_v19_tb_card_no_title.dot", "fig01_power_model_v19_tb_card_no_title"),
        ("paper", "fig01_power_model_paper_v20_tb_group_card.dot", "fig01_power_model_v20_tb_group_card"),
        ("study", "fig01_power_model_study_v20_tb_group_card.dot", "fig01_power_model_v20_tb_group_card"),
        ("paper", "fig01_power_model_paper_v21_tb_card_no_t.dot", "fig01_power_model_v21_tb_card_no_t"),
        ("study", "fig01_power_model_study_v21_tb_card_no_t.dot", "fig01_power_model_v21_tb_card_no_t"),
        ("paper", "fig01_power_model_paper_v22_tb_card_no_t_wrap_eta.dot", "fig01_power_model_v22_tb_card_no_t_wrap_eta"),
        ("study", "fig01_power_model_study_v22_tb_card_no_t_wrap_eta.dot", "fig01_power_model_v22_tb_card_no_t_wrap_eta"),
        ("paper", "fig01_power_model_paper_v24_tb_ultra_compact.dot", "fig01_power_model_v24_tb_ultra_compact"),
        ("study", "fig01_power_model_study_v24_tb_ultra_compact.dot", "fig01_power_model_v24_tb_ultra_compact"),
        ("paper", "fig01_power_model_paper_v23_tb_card_no_t_wrap_eta_tight.dot", "fig01_power_model_v23_tb_card_no_t_wrap_eta_tight"),
        ("study", "fig01_power_model_study_v23_tb_card_no_t_wrap_eta_tight.dot", "fig01_power_model_v23_tb_card_no_t_wrap_eta_tight"),
        ("paper", "fig01_power_model_paper_v24b_tb_ultra_compact_fixed.dot", "fig01_power_model_v24b_tb_ultra_compact_fixed"),
        ("study", "fig01_power_model_study_v24b_tb_ultra_compact_fixed.dot", "fig01_power_model_v24b_tb_ultra_compact_fixed"),
    ]

    for mode, dot_name, out_stem in figures:
        in_path = src_dir / dot_name
        if not in_path.exists():
            raise FileNotFoundError(f"缺少 DOT 源文件：{in_path}")

        mode_dir = out_dir / mode
        mode_dir.mkdir(parents=True, exist_ok=True)

        out_png = mode_dir / f"{out_stem}.png"

        # PNG：用于快速预览与对比版式；提高 dpi 让文字更清晰
        _run(["dot", "-Tpng", "-Gdpi=260", str(in_path), "-o", str(out_png)], cwd=base_dir)

        print(f"[OK] {mode}: {out_png}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
