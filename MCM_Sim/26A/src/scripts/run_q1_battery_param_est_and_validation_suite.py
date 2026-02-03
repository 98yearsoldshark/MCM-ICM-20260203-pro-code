#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q1：电池参数估计与独立验证（一键复现套件）。

本脚本面向赛题对 Q1 的硬性要求：
- 必须给出连续时间机理模型（ODE/连续状态），不能只做离散曲线拟合；
- 数据只能作为“参数估计与验证”的支撑，而不是替代模型；
- 需要在报告中给出参数估计方法与验证结果。

我们在代码侧把“手机功耗层”与“电池电学层”解耦；这里专注电池端：
- 训练/辨识（parameter estimation）：用 CALCE SP20-1 的 10_16 Initial capacity
  数据片段（含 1A 放电 + 休止恢复）拟合二阶 Thevenin 2RC ECM 的关键参数。
- 独立验证（validation）：在两份 Incremental OCV 验证集（12_2、12_09）以及
  10_16 全量轨迹上，对比观测电压与模型电压，输出误差报表与论文/学习两套图。

并行开发影响（Q2）：
- 本脚本只会“新增输出文件”和（可选）生成一个新的电池配置 JSON，
  不会修改 Q2 共享核心接口/默认配置；按《构建指导》属于影响等级 0~1。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
ROOT_DIR = SRC_DIR.parent  # MCM_Sim/26A


def _slugify(text: str) -> str:
    s = str(text).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "dataset"


def _default_calce_xlsx() -> dict[str, Path]:
    base = ROOT_DIR / "data" / "calce-umd" / "extracted" / "battery-data" / "SP"
    return {
        "train_10_16_initial_capacity": base / "10_16_2015_Initial capacity_SP20-1.xlsx",
        "val_12_2_incremental_ocv": base / "12_2_2015_Incremental OCV test_SP20-1.xlsx",
        "val_12_09_incremental_ocv": base / "12_09_2015_Incremental OCV test_SP20-1.xlsx",
    }


def _best_configs_by_dataset_id() -> dict[str, Path]:
    """三组“最强展示配置”（按数据集定向微调过，用于论文展示/诊断）。"""

    ab = SRC_DIR / "configs" / "ablation"
    return {
        "12_2_2015_incremental_ocv_test_sp20_1": ab
        / "battery_calce_sp20_1_ecmfit_r0fixed_2rc_tauconstrained_diffz_rdrop_vgate_relax2stage_12_2tuned_v1.json",
        "12_09_2015_incremental_ocv_test_sp20_1": ab
        / "battery_calce_sp20_1_ecmfit_r0fixed_2rc_tauconstrained_diffz_rdrop_vgate_relax2stage_12_09tuned_v2.json",
        "10_16_2015_initial_capacity_sp20_1": ab
        / "battery_calce_sp20_1_ecmfit_r0fixed_2rc_tauconstrained_diffz_vgate_relax2stage_10_16deepfix_v3smooth.json",
    }


def _run(cmd: list[str]) -> None:
    print("[RUN]", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_key_metrics(payload: dict[str, Any]) -> dict[str, float | int | None]:
    rep = payload.get("report", {}) or {}
    overall = rep.get("overall", {}) or {}
    phone = rep.get("phone_domain", {}) or {}
    until = phone.get("overall_until_cutoff_above_vcut", phone.get("overall_until_cutoff", {})) or {}
    rest = rep.get("rest_segments", {}) or {}
    rest_early = rest.get("rest_early", {}) or {}

    def _f(x) -> float | None:
        return None if x is None else float(x)

    def _i(x) -> int | None:
        return None if x is None else int(x)

    return {
        "rmse_mV": _f(overall.get("rmse_mV")),
        "mae_mV": _f(overall.get("mae_mV")),
        "n": _i(overall.get("n")),
        "rmse_phone_domain_mV": _f(until.get("rmse_mV")),
        "mae_phone_domain_mV": _f(until.get("mae_mV")),
        "n_phone_domain": _i(until.get("n")),
        "tte_error_s": _f(phone.get("tte_error_s")),
        "rest_early_rmse_mV": _f(rest_early.get("rmse_mV")),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1：CALCE 电池参数估计与验证套件（输出报表+图像）")
    ap.add_argument(
        "--out-tag",
        default="q1fit_2rc_v1",
        help="生成的 2RC 配置文件名后缀（默认 q1fit_2rc_v1，会写入 configs/）",
    )
    ap.add_argument("--skip-calibration", action="store_true", help="跳过参数估计，只做验证/汇总（需要 out-tag 对应配置已存在）")
    ap.add_argument("--no-plots", action="store_true", help="验证阶段不生成图像（只输出 JSON 报表与 summary）")
    ap.add_argument("--skip-best", action="store_true", help="跳过三组“最强展示配置”（ablation/tuned）的额外出图与汇总")
    ap.add_argument("--skip-online-r0", action="store_true", help="跳过“在线估计 R0”的增强验证（默认开启，推荐写进 Q1）")
    args = ap.parse_args()

    # 1) 参数估计：生成一个新的 2RC 配置（避免覆盖既有配置，便于复现实验口径）
    cfg_seed = SRC_DIR / "configs" / "battery_calce_sp20_1.json"
    cfg_1rc = SRC_DIR / "configs" / "battery_calce_sp20_1_ecmfit_r0fixed_r1soc.json"
    cfg_2rc_base = SRC_DIR / "configs" / "battery_calce_sp20_1_ecmfit_r0fixed_2rc.json"
    cfg_2rc_new = SRC_DIR / "configs" / f"battery_calce_sp20_1_{str(args.out_tag).strip()}.json"

    paths = _default_calce_xlsx()
    for k, p in paths.items():
        if not p.exists():
            raise SystemExit(f"[ERROR] 找不到数据集（{k}）：{p}")

    if not args.skip_calibration:
        cal_script = SRC_DIR / "scripts" / "calibrate_model1_ecm2rc_r0fixed_r1r2soc_tau_from_calce_sp20_1_10_16_segment.py"
        _run(
            [
                sys.executable,
                str(cal_script),
                "--xlsx",
                str(paths["train_10_16_initial_capacity"]),
                "--seed-phone",
                str(cfg_seed),
                "--out",
                str(cfg_2rc_new),
            ]
        )
    if not cfg_2rc_new.exists():
        raise SystemExit(f"[ERROR] 2RC 配置不存在：{cfg_2rc_new}（可用 --skip-calibration 跳过拟合时，需先生成该文件）")

    # 2) 验证：三份数据（2 个 Incremental OCV + 1 个 Initial capacity）
    val_xlsx = [
        paths["val_12_2_incremental_ocv"],
        paths["val_12_09_incremental_ocv"],
        paths["train_10_16_initial_capacity"],  # 额外测试（与训练片段有重叠，但可用于 sanity check）
    ]

    v1_script = SRC_DIR / "scripts" / "validate_model1_ecm_on_calce_sp20_1_incremental_ocv.py"
    v2_script = SRC_DIR / "scripts" / "validate_model1_ecm2rc_on_calce_sp20_1_incremental_ocv.py"
    v2_online_r0_script = SRC_DIR / "scripts" / "validate_model1_ecm2rc_on_calce_sp20_1_incremental_ocv_online_r0.py"
    best_cfg_by_ds = _best_configs_by_dataset_id()

    for xlsx in val_xlsx:
        dataset_id = _slugify(xlsx.stem)
        # 1RC：seed vs r0fixed_r1soc
        cmd1 = [
            sys.executable,
            str(v1_script),
            "--xlsx",
            str(xlsx),
            "--phone",
            str(cfg_seed),
            "--phone",
            str(cfg_1rc),
        ]
        if args.no_plots:
            cmd1.append("--no-plots")
        _run(cmd1)

        # 2RC（严格口径）：base vs new（diff_v_gate=model 表示纯前向；对未启用 diff_z 的配置不产生影响）
        cmd2 = [
            sys.executable,
            str(v2_script),
            "--xlsx",
            str(xlsx),
            "--phone",
            str(cfg_2rc_base),
            "--phone",
            str(cfg_2rc_new),
            "--diff-v-gate",
            "model",
        ]
        if args.no_plots:
            cmd2.append("--no-plots")
        _run(cmd2)

        # 2RC（在线估计 R0）：在同一数据集早期时间窗内识别一次 R0，然后整段前向预测。
        # 说明：这仍是连续时间机理模型；“在线辨识”口径符合真实手机可落地叙事。
        if not args.skip_online_r0:
            cmd_online = [
                sys.executable,
                str(v2_online_r0_script),
                "--xlsx",
                str(xlsx),
                "--phone",
                str(cfg_2rc_new),
                "--diff-v-gate",
                "model",
            ]
            if args.no_plots:
                cmd_online.append("--no-plots")
            _run(cmd_online)

        # 2RC（三组最强展示）：按数据集选择对应 tuned 配置（观测辅助/诊断模式）
        if not args.skip_best:
            best_cfg = best_cfg_by_ds.get(dataset_id)
            if best_cfg is not None:
                if not best_cfg.exists():
                    raise SystemExit(f"[ERROR] 期望的 best 配置不存在：{best_cfg}")
                cmd_best = [
                    sys.executable,
                    str(v2_script),
                    "--xlsx",
                    str(xlsx),
                    "--phone",
                    str(best_cfg),
                    "--diff-v-gate",
                    "measured",
                ]
                if args.no_plots:
                    cmd_best.append("--no-plots")
                _run(cmd_best)

    # 3) 汇总：读取 out_reports/validation/<dataset_id>/<config>.json，拼成一张表
    out_root = SRC_DIR / "out_reports" / "validation"
    summary_rows: list[dict[str, Any]] = []

    cfg_tags = [
        cfg_seed.stem,
        cfg_1rc.stem,
        cfg_2rc_base.stem,
        cfg_2rc_new.stem,
    ]
    if not args.skip_online_r0:
        cfg_tags += [
            f"{cfg_2rc_new.stem}__open_loop",
            f"{cfg_2rc_new.stem}__online_r0fit",
        ]

    for xlsx in val_xlsx:
        dataset_id = _slugify(xlsx.stem)
        ds_dir = out_root / dataset_id
        tags = list(cfg_tags)
        if not args.skip_best:
            best_cfg = best_cfg_by_ds.get(dataset_id)
            if best_cfg is not None:
                tags.append(best_cfg.stem)

        for tag in tags:
            rep_path = ds_dir / f"{tag}.json"
            if not rep_path.exists():
                # 若某配置/某数据没跑出来（或历史被删），就跳过，不让套件整体失败
                continue
            payload = _read_json(rep_path)
            m = _extract_key_metrics(payload)
            mode = payload.get("mode", {}) or {}
            if tag.endswith("__open_loop") or tag.endswith("__online_r0fit"):
                group = "online_estimation"
            else:
                group = "strict_validation" if tag in cfg_tags else "best_show"
            summary_rows.append(
                {
                    "dataset_id": dataset_id,
                    "dataset_xlsx": str(xlsx),
                    "config_tag": tag,
                    "group": group,
                    "diff_v_gate": mode.get("diff_v_gate", None),
                    **m,
                }
            )

    out_csv = out_root / "_q1_battery_validation_summary.csv"
    out_md = out_root / "_q1_battery_validation_summary.md"

    # CSV（便于后续做统计/画图）
    cols = [
        "dataset_id",
        "config_tag",
        "group",
        "diff_v_gate",
        "rmse_mV",
        "mae_mV",
        "rmse_phone_domain_mV",
        "mae_phone_domain_mV",
        "tte_error_s",
        "rest_early_rmse_mV",
        "n",
        "n_phone_domain",
        "dataset_xlsx",
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in summary_rows:
            w.writerow({k: r.get(k, None) for k in cols})

    # Markdown（便于直接贴进论文写作/检查）
    cfg_new = _read_json(cfg_2rc_new)
    meta = cfg_new.get("meta", {}) or {}
    batt = (cfg_new.get("battery", cfg_new) or {}).get("ecm", {})
    # 兼容两种结构：顶层 battery / 直接 ecm
    batt_obj = cfg_new.get("battery", cfg_new) or {}
    ecm = batt_obj.get("ecm", batt_obj.get("battery", {}).get("ecm", {}))  # type: ignore[assignment]
    md_lines = [
        "# Q1 电池端：参数估计与验证（自动生成）",
        "",
        "## 参数估计（2RC）配置",
        f"- 配置文件：`{cfg_2rc_new}`",
        f"- seed OCV 配置：`{cfg_seed}`",
        f"- 训练数据：`{paths['train_10_16_initial_capacity']}`（Initial capacity）",
        "",
        "## 三组“最强展示配置”（观测辅助/诊断模式）",
        "说明：这三组配置属于定向微调/观测辅助（diff_v_gate=measured），用于更好地复现尖峰/平台/回弹形态；",
        "在论文中建议以“增强模型（观测辅助）”展示，并与 strict_validation 口径的独立验证结果并列呈现。",
        "",
    ]
    if args.skip_best:
        md_lines.append("- 本次运行跳过了 best_show（--skip-best）。")
    else:
        for ds_id, cfg in best_cfg_by_ds.items():
            md_lines.append(f"- {ds_id}: `{cfg}`")

    md_lines += [
        "",
        "## 在线估计 R0（增强验证，推荐写入 Q1）",
        "说明：不改变 2RC 连续时间模型本体，只在使用早期用“休止->负载”的电压跳变估计一次有效 R0，",
        "随后固定 R0 对整段轨迹前向预测；这更贴近真实手机端可落地做法（测得 I(t)、V(t) 后在线辨识参数）。",
        f"- 脚本：`{SRC_DIR / 'scripts' / 'validate_model1_ecm2rc_on_calce_sp20_1_incremental_ocv_online_r0.py'}`",
        f"- 结果文件命名：`{cfg_2rc_new.stem}__open_loop.json` 与 `{cfg_2rc_new.stem}__online_r0fit.json`",
        "",
    ]

    md_lines += [
        "",
        "关键参数（从配置中读取）：",
        f"- R0_ohm = {ecm.get('R0_ohm', 'NA')}",
        f"- C1_F = {ecm.get('C1_F', 'NA')}",
        f"- C2_F = {ecm.get('C2_F', 'NA')}",
        f"- R1_curve = {('yes' if isinstance(ecm.get('R1_curve', None), dict) else 'no')}",
        f"- R2_curve = {('yes' if isinstance(ecm.get('R2_curve', None), dict) else 'no')}",
        "",
        "配置 meta（便于论文可追溯引用）：",
        "```json",
        json.dumps(meta, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 验证结果汇总",
        f"- 汇总表（CSV）：`{out_csv}`",
        "",
        "| dataset_id | config_tag | group | diff_v_gate | RMSE(mV) | RMSE_phone_domain(mV) | TTE误差(s) |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for r in summary_rows:
        md_lines.append(
            f"| {r.get('dataset_id','')} | {r.get('config_tag','')} | {r.get('group','')} | {r.get('diff_v_gate','')} | "
            f"{(r.get('rmse_mV') if r.get('rmse_mV') is not None else '')} | "
            f"{(r.get('rmse_phone_domain_mV') if r.get('rmse_phone_domain_mV') is not None else '')} | "
            f"{(r.get('tte_error_s') if r.get('tte_error_s') is not None else '')} |"
        )
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print("[OK] Q1 电池端参数估计与验证已完成：")
    print("- 2RC 配置：", cfg_2rc_new)
    print("- 汇总 CSV：", out_csv)
    print("- 汇总 MD ：", out_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
