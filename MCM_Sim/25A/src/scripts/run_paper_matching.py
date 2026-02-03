from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

# 允许直接运行脚本（不要求安装成包）
import sys

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm_sim.fast_simulator import simulate_wear_fast  # noqa: E402
from mcm_sim.io_utils import ensure_dir, save_json  # noqa: E402
from mcm_sim.paper_compare import (  # noqa: E402
    PaperTarget,
    find_darkest_center,
    gradient_magnitude_mean,
    load_and_crop,
    load_targets_from_json,
    pearson_corr,
    side_by_side,
    to_gray_array,
)
from mcm_sim.render import render_field_to_pil, wear_to_height_field  # noqa: E402


def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _uniform(rng: np.random.Generator, a: float, b: float) -> float:
    return float(rng.uniform(a, b))


def base_config() -> Dict[str, Any]:
    """面向“论文热力图对比”的基础配置。"""

    return {
        "random_seed": 0,
        "surface": {
            "type": "rect_height_field",
            "width_m": 1.2,  # X: 120cm
            "depth_m": 0.5,  # Y: 50cm
            "cell_m": 0.005,
        },
        "traffic": {
            # 实验里优先用 total_contacts 直接控制“总体接触次数”
            "total_contacts": 6_000_000,
            "up_ratio": 0.5,
        },
        "contact": {
            "center_distribution": {
                "type": "gmm_separable",
                # lanes 会在采样时覆盖
                "lanes": [{"mu_x_frac": 0.5, "sigma_x_m": 0.10, "weight": 1.0}],
                "mu_y_up_frac": 0.78,
                "mu_y_down_frac": 0.86,
                "sigma_y_m": 0.08,
            },
            "footprint_kernel": {
                "type": "elliptical_gaussian",
                "sigma_x_m": 0.06,
                "sigma_y_m": 0.10,
                "size_m": 0.35,
            },
            "edge_scuff": {
                "enabled": True,
                "band_m": 0.03,
                "fraction_of_contacts": 0.20,
                "kernel": {
                    "type": "elliptical_gaussian",
                    "sigma_x_m": 0.06,
                    "sigma_y_m": 0.015,
                    "size_m": 0.20,
                },
            },
            "sampling": {"method": "poisson"},
        },
        "wear": {
            "law": "archard_like",
            "wear_per_contact_peak_mm": 1e-7,
            "edge_scuff_multiplier": 6.0,
        },
    }


def sample_config_for_target(target_id: str, rng: np.random.Generator) -> Dict[str, Any]:
    cfg = base_config()

    # seed
    cfg["random_seed"] = int(rng.integers(0, 2**31 - 1))

    # traffic: 对不同 target 调整“总接触次数”和上下楼比例
    traffic = cfg["traffic"]
    if target_id == "paper_fig3_up":
        traffic["up_ratio"] = 1.0
    elif target_id == "paper_fig3_down":
        traffic["up_ratio"] = 0.0
    else:
        traffic["up_ratio"] = _uniform(rng, 0.35, 0.65)

    if target_id == "paper_fig15_short_term_many":
        traffic["total_contacts"] = int(_uniform(rng, 6_000_000, 16_000_000))
    elif target_id == "paper_fig15_long_term_few":
        traffic["total_contacts"] = int(_uniform(rng, 800_000, 5_000_000))
    else:
        traffic["total_contacts"] = int(_uniform(rng, 2_000_000, 12_000_000))

    # contact center distribution
    center = cfg["contact"]["center_distribution"]

    # y 方向：磨损通常靠近踏步前缘（y 较大）
    center["sigma_y_m"] = _uniform(rng, 0.05, 0.11)
    center["mu_y_up_frac"] = _uniform(rng, 0.72, 0.86)
    center["mu_y_down_frac"] = _uniform(rng, 0.76, 0.92)

    # x 方向：按 target 选择“单车道/双车道”
    if target_id == "paper_fig15_long_term_few":
        # 长期少次：往往只有“单侧/单条路径”更明显，且更分散（sigma 更大）
        if float(rng.random()) < 0.75:
            center["lanes"] = [
                {
                    "mu_x_frac": _uniform(rng, 0.65, 0.92),
                    "sigma_x_m": _uniform(rng, 0.09, 0.22),
                    "weight": 1.0,
                }
            ]
        else:
            # 少量情况下允许“弱第二路径”，用于拟合某些样本中存在的轻微偏移/次级磨损
            mu_main = _uniform(rng, 0.65, 0.90)
            mu_side = _uniform(rng, 0.10, 0.45)
            w_main = _uniform(rng, 0.82, 0.95)
            center["lanes"] = [
                {"mu_x_frac": mu_main, "sigma_x_m": _uniform(rng, 0.09, 0.20), "weight": w_main},
                {"mu_x_frac": mu_side, "sigma_x_m": _uniform(rng, 0.06, 0.16), "weight": 1.0 - w_main},
            ]

    elif target_id == "paper_fig12_partial_repair":
        # 允许出现明显偏左/偏右的双车道（更接近论文里某些“两个坑”）
        mu1 = _uniform(rng, 0.25, 0.40)
        mu2 = _uniform(rng, 0.60, 0.80)
        w = _uniform(rng, 0.35, 0.65)
        sx1 = _uniform(rng, 0.06, 0.13)
        sx2 = _uniform(rng, 0.06, 0.13)
        center["lanes"] = [
            {"mu_x_frac": mu1, "sigma_x_m": sx1, "weight": w},
            {"mu_x_frac": mu2, "sigma_x_m": sx2, "weight": 1.0 - w},
        ]
    else:
        # 单车道：主要集中在中间
        center["lanes"] = [
            {"mu_x_frac": _uniform(rng, 0.45, 0.55), "sigma_x_m": _uniform(rng, 0.07, 0.14), "weight": 1.0}
        ]

    # footprint kernel：足底接触范围
    fp = cfg["contact"]["footprint_kernel"]
    fp["sigma_x_m"] = _uniform(rng, 0.045, 0.085)
    fp["sigma_y_m"] = _uniform(rng, 0.070, 0.135)
    fp["size_m"] = _uniform(rng, 0.25, 0.45)

    # edge scuff：踏鼻刮擦（让磨损更靠近前缘、并形成更尖锐的凹陷）
    scuff = cfg["contact"]["edge_scuff"]
    scuff["band_m"] = _uniform(rng, 0.015, 0.05)
    if target_id == "paper_fig15_long_term_few":
        # 长期少次：踏鼻刮擦事件比例通常更低（更接近“缓慢磨损”）
        scuff["fraction_of_contacts"] = _uniform(rng, 0.00, 0.22)
    else:
        scuff["fraction_of_contacts"] = _uniform(rng, 0.05, 0.35)
    k2 = scuff["kernel"]
    k2["sigma_x_m"] = _uniform(rng, 0.045, 0.085)
    k2["sigma_y_m"] = _uniform(rng, 0.008, 0.028)
    k2["size_m"] = _uniform(rng, 0.12, 0.26)

    wear = cfg["wear"]
    wear["edge_scuff_multiplier"] = _uniform(rng, 2.0, 12.0)

    # partial repair：对 fig12 加入“两阶段 + 局部重置”
    if target_id == "paper_fig12_partial_repair":
        cfg["repair"] = {
            "enabled": True,
            # repair 前占总“接触次数”的比例（用作时间代理）
            "fraction": _uniform(rng, 0.4, 0.85),
            # 论文描述：大致 0-68cm 范围修复（注意论文 x 轴是反向显示）
            "x_range_m": [0.0, 0.68],
            "y_range_m": [0.0, 0.50],
            "reset_to_mm": 0.0,
        }

    return cfg


def score_against_target(
    paper_crop: Any,
    sim_img: Any,
    *,
    blur_radius: float = 2.0,
    compare_width: int = 256,
) -> Dict[str, float]:
    # 按 paper crop 的宽高比自适应缩放，避免“拉伸”影响相似度计算
    w, h = paper_crop.size
    compare_height = max(64, int(round(compare_width * (h / max(1, w)))))
    compare_size = (compare_width, compare_height)

    paper01 = to_gray_array(paper_crop, out_size=compare_size, blur_radius=blur_radius, normalize=True)
    sim01 = to_gray_array(sim_img, out_size=compare_size, blur_radius=blur_radius, normalize=True)

    # 兼容“明暗反转”的情况：取 corr 与 corr(paper, 1-sim) 的较大值
    corr_a = pearson_corr(paper01, sim01)
    corr_b = pearson_corr(paper01, 1.0 - sim01)
    corr = float(max(corr_a, corr_b))
    g_p = gradient_magnitude_mean(paper01)
    g_s = gradient_magnitude_mean(sim01)

    cy_p, cx_p = find_darkest_center(paper01)
    cy_s, cx_s = find_darkest_center(sim01)
    center_dist = float(math.hypot(cy_p - cy_s, cx_p - cx_s))

    # 综合评分：相关性为主，中心偏移为罚项（经验权重）
    score = float(corr - 0.35 * center_dist)

    return {
        "score": score,
        "corr": float(corr),
        "center_dist": center_dist,
        "grad_mean_paper": g_p,
        "grad_mean_sim": g_s,
        "grad_ratio_sim_over_paper": float(g_s / g_p) if g_p > 0 else float("nan"),
    }


def run_match_for_target(
    target: PaperTarget,
    *,
    out_dir: Path,
    n_trials: int,
    top_k: int,
    rng: np.random.Generator,
) -> None:
    tgt_dir = ensure_dir(out_dir / target.id)
    paper_crop = load_and_crop(target.image_path, target.crop_frac)
    paper_crop.save(tgt_dir / "paper_crop.png")

    trials: List[Dict[str, Any]] = []

    best: List[Tuple[float, Dict[str, Any]]] = []

    for i in range(n_trials):
        cfg = sample_config_for_target(target.id, rng)
        sim_out = simulate_wear_fast(cfg)

        z = wear_to_height_field(sim_out.wear_depth_mm, z_max=0.98, z_min=0.78)
        # 论文图的坐标轴通常是：x 从右到左，y 从上到下。
        # PIL 图像坐标本身就是 y 从上到下，因此这里仅 flip_x。
        sim_img = render_field_to_pil(z, cmap_name="viridis", flip_x=True, flip_y=False, out_size=paper_crop.size)

        s = score_against_target(paper_crop, sim_img)

        record = {
            "trial": i,
            "target_id": target.id,
            "target_desc": target.desc,
            **s,
            "config": cfg,
            "debug": sim_out.debug,
        }
        trials.append(record)

        best.append((s["score"], record))
        best.sort(key=lambda x: x[0], reverse=True)
        if len(best) > top_k:
            best = best[:top_k]

    # 保存全量汇总（jsonlines，便于后续筛选/分析）
    with (tgt_dir / "trials.jsonl").open("w", encoding="utf-8") as f:
        for r in trials:
            # config/debug 可能较大，但 jsonl 方便后处理；如需瘦身可后续再裁剪
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 保存 top_k 结果（图 + config）
    for rank, (_, rec) in enumerate(best, start=1):
        rdir = ensure_dir(tgt_dir / f"top_{rank:02d}")

        cfg = rec["config"]
        sim_out = simulate_wear_fast(cfg, rng=np.random.default_rng(int(cfg["random_seed"])))
        z = wear_to_height_field(sim_out.wear_depth_mm, z_max=0.98, z_min=0.78)
        sim_img = render_field_to_pil(z, cmap_name="viridis", flip_x=True, flip_y=False, out_size=paper_crop.size)
        sim_img.save(rdir / "sim.png")

        side_by_side(paper_crop, sim_img).save(rdir / "paper_vs_sim.png")

        # 关键指标与配置
        save_json(rdir / "score.json", {k: rec[k] for k in rec.keys() if isinstance(rec[k], (int, float, str))})
        save_json(rdir / "config.json", cfg)
        save_json(rdir / "debug.json", rec["debug"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Match fast wear simulation heatmaps to paper heatmap crops.")
    parser.add_argument("--trials-per-target", type=int, default=250, help="Random trials per target (default: 250)")
    parser.add_argument("--top-k", type=int, default=5, help="Save top-k results per target (default: 5)")
    parser.add_argument("--seed", type=int, default=20260125, help="RNG seed (default: 20260125)")
    parser.add_argument(
        "--only",
        type=str,
        default="",
        help="Comma-separated target ids to run (default: all)",
    )
    args = parser.parse_args()

    targets_path = SRC_DIR / "configs" / "paper_targets.json"
    targets = load_targets_from_json(targets_path)

    only_ids = {s.strip() for s in str(args.only).split(",") if s.strip()}
    if only_ids:
        targets = [t for t in targets if t.id in only_ids]
        if not targets:
            raise SystemExit(f"No targets matched --only={args.only!r}")

    out_root = ensure_dir(SRC_DIR / "runs" / f"paper_match_{ts()}")
    save_json(out_root / "targets_used.json", {"targets_path": str(targets_path), "n_targets": len(targets)})

    rng = np.random.default_rng(int(args.seed))

    for t in targets:
        print(f"[{t.id}] {t.desc} ...")
        run_match_for_target(
            t,
            out_dir=out_root,
            n_trials=int(args.trials_per_target),
            top_k=int(args.top_k),
            rng=rng,
        )

    # 生成一个简单的汇总报告，便于快速查看“拟合程度”
    lines: List[str] = []
    lines.append("# Paper Heatmap Matching Report")
    lines.append("")
    lines.append(f"- output: `{out_root}`")
    lines.append(f"- trials_per_target: {int(args.trials_per_target)}")
    lines.append(f"- top_k: {int(args.top_k)}")
    lines.append("")
    lines.append("| target_id | score | corr | center_dist | grad_ratio(sim/paper) | preview |")
    lines.append("|---|---:|---:|---:|---:|---|")

    for t in targets:
        top1 = out_root / t.id / "top_01"
        score_path = top1 / "score.json"
        if not score_path.exists():
            continue
        with score_path.open("r", encoding="utf-8") as f:
            s = json.load(f)
        preview_rel = f"{t.id}/top_01/paper_vs_sim.png"
        lines.append(
            "| {tid} | {score:.3f} | {corr:.3f} | {cd:.3f} | {gr:.3f} | `{prev}` |".format(
                tid=t.id,
                score=float(s.get("score", float("nan"))),
                corr=float(s.get("corr", float("nan"))),
                cd=float(s.get("center_dist", float("nan"))),
                gr=float(s.get("grad_ratio_sim_over_paper", float("nan"))),
                prev=preview_rel,
            )
        )

    (out_root / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("done. output:", out_root)


if __name__ == "__main__":
    main()
