#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重构 Q2 论文材料目录（拆分中英文 + 为每张图补充数据版本）。

目标结构（以每个子文件夹为单位）：
- 子文件夹根目录只保留：
  - figure.png                论文版图片（paper）
  - paper_fragment_zh.md      中文版论文插入片段（可直接粘贴到中文论文）
- 其余内容统一放入子文件夹的 other/：
  - about.md                  图源/生成方式说明
  - paper_fragment_en.md      英文版论文插入片段
  - figure_study.png          学习版图片（study）
  - figure_data*.csv          该图对应的数据版本（便于后续 AI/人类用数据理解）
  - context_full.md           （可选备份）原始中英混合 context

说明：
- 本脚本只对 `MCM_Sim/26A/论文/理论模型/论文阶段/Q2材料/` 生效；
- 数据版本尽量复用 `src/out_reports/q2/` 已产出的 CSV；少数图（variants/轨迹）会小规模重算以导出数据表。
 - 会尝试从每个子文件夹 `other/about.md` 中解析 out_plots 的原始图片路径，并把“最新的 out_plots 图片”
   同步复制到 `figure.png`/`other/figure_study.png`，保证论文材料与当前代码输出一致。
"""

from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
REPO_DIR = SRC_DIR.parent.parent  # .../MCM_Sim

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model3_aging, simulate_model3_aging_trace
from mcm26a.viz.q2_plots import _scenario_title, _variant_label_zh


@dataclass(frozen=True)
class Q2Paths:
    materials_root: Path
    out_reports: Path
    scenarios_json: Path
    power_stateful_json: Path
    phone_json: Path


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _now_ts() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _backup_existing(p: Path, history_dir: Path) -> None:
    """把已存在的文件移动到 history_dir，避免“覆盖=删除旧文件”。

    说明：
    - 用户要求不要删除旧文件；因此当我们需要写入/覆盖同名产物时，
      先把旧文件移动到 other/_history/ 下做留档。
    - 仅对文件做备份；目录不处理。
    """

    if not p.exists() or p.is_dir():
        return
    _ensure_dir(history_dir)
    ts = _now_ts()
    dst = history_dir / f"{ts}_{p.name}"
    k = 1
    while dst.exists():
        dst = history_dir / f"{ts}_{k}_{p.name}"
        k += 1
    shutil.move(str(p), str(dst))


def _files_identical(a: Path, b: Path) -> bool:
    """判断两文件内容是否完全一致（用于避免重复备份/重复覆盖）。"""

    if not (a.exists() and b.exists()):
        return False
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
    except Exception:
        return False
    try:
        with a.open("rb") as fa, b.open("rb") as fb:
            while True:
                ca = fa.read(64 * 1024)
                cb = fb.read(64 * 1024)
                if ca != cb:
                    return False
                if not ca:
                    return True
    except Exception:
        return False


def _write_text(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8")


def _safe_move(src: Path, dst: Path, *, history_dir: Path | None = None) -> None:
    if not src.exists():
        return
    _ensure_dir(dst.parent)
    if dst.exists():
        if history_dir is not None:
            _backup_existing(dst, history_dir)
        else:
            dst.unlink()
    shutil.move(str(src), str(dst))


def _split_context_md(text: str) -> tuple[str, str, str]:
    """把 context.md 拆成：插入建议/中文正文/英文正文（均不含对应标题行）。"""

    zh_marker = "# 可直接粘贴到论文的文本（中文）"
    en_marker = "# 可直接粘贴到论文的文本（英文）"

    if zh_marker not in text:
        # 兼容：只有中文（例如 00 总览）
        return (text.strip() + "\n", "", "")

    before_zh, rest = text.split(zh_marker, 1)
    before_zh = before_zh.strip() + "\n"

    if en_marker in rest:
        zh_part, en_part = rest.split(en_marker, 1)
    else:
        zh_part, en_part = rest, ""

    return (before_zh, zh_part.strip() + "\n", en_part.strip() + "\n")


def _normalize_title_to_filename(s: str) -> str:
    # 仅用于“兜底”生成文件名（尽量 ASCII）
    s = re.sub(r"\s+", "_", s.strip())
    s = re.sub(r"[^0-9A-Za-z_\\-\\.]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_") or "figure"


def _pick_png_pair(folder: Path) -> tuple[Path | None, Path | None]:
    """返回 (paper_png, study_png)；按文件名是否包含 _study 识别。"""
    pngs = sorted(folder.glob("*.png"))
    paper = [p for p in pngs if "_study" not in p.name]
    study = [p for p in pngs if "_study" in p.name]
    paper_png = paper[0] if paper else None
    study_png = study[0] if study else None
    return paper_png, study_png


def _extract_outplot_png_paths_from_about(text: str) -> tuple[Path | None, Path | None]:
    """从 about.md 中提取 out_plots 论文版/学习版图片路径（若存在）。"""

    # 约定：about.md 里用 `...` 包裹路径
    mp = re.search(r"-\s*paper：`([^`]+\.png)`", text)
    ms = re.search(r"-\s*study：`([^`]+\.png)`", text)
    paper = Path(mp.group(1)) if mp else None
    study = Path(ms.group(1)) if ms else None
    return paper, study


def _sync_figures_from_about(folder: Path) -> None:
    """把 out_plots 的最新图片同步到 Q2材料 子文件夹（figure.png / other/figure_study.png）。"""

    other = _ensure_dir(folder / "other")
    history = _ensure_dir(other / "_history")
    about = other / "about.md"
    if not about.exists():
        return

    try:
        paper_rel, study_rel = _extract_outplot_png_paths_from_about(_read_text(about))
    except Exception:
        return

    root = REPO_DIR.parent  # workspace root（包含 MCM_Sim/）

    if paper_rel is not None:
        src = root / paper_rel
        if src.exists():
            _ensure_dir(folder)
            dst = folder / "figure.png"
            if dst.exists() and not _files_identical(src, dst):
                _backup_existing(dst, history)
            if not _files_identical(src, dst):
                shutil.copy2(str(src), str(dst))

    if study_rel is not None:
        src = root / study_rel
        if src.exists():
            dst = other / "figure_study.png"
            if dst.exists() and not _files_identical(src, dst):
                _backup_existing(dst, history)
            if not _files_identical(src, dst):
                shutil.copy2(str(src), str(dst))


def _export_data_01_tte_matrix(paths: Q2Paths) -> pd.DataFrame:
    df = pd.read_csv(paths.out_reports / "tte_summary.csv")
    raw = load_scenarios_json(paths.scenarios_json)
    df = df[df["variant"].astype(str) == "-"].copy()
    df["scenario_title_zh"] = df["scenario_id"].astype(str).map(lambda sid: _scenario_title(raw, sid))
    return df[["scenario_id", "scenario_title_zh", "soc0", "n", "mean_h", "p05_h", "p50_h", "p95_h"]].sort_values(
        ["scenario_id", "soc0"]
    )


def _export_data_03_uq_distribution(paths: Q2Paths) -> pd.DataFrame:
    df = pd.read_csv(paths.out_reports / "tte_samples.csv")
    df = df[(df["variant"].astype(str) == "-") & (df["soc0"].astype(float) == 1.0)].copy()
    raw = load_scenarios_json(paths.scenarios_json)
    df["scenario_title_zh"] = df["scenario_id"].astype(str).map(lambda sid: _scenario_title(raw, sid))
    return df[["sample_idx", "scenario_id", "scenario_title_zh", "soc0", "tte_h", "status", "soc_end", "temp_peak_C"]].sort_values(
        ["scenario_id", "sample_idx"]
    )


def _export_data_04_uq_spread(paths: Q2Paths) -> pd.DataFrame:
    df = pd.read_csv(paths.out_reports / "uq_spread.csv")
    df = df[(df["variant"].astype(str) == "-") & (df["soc0"].astype(float) == 1.0)].copy()
    raw = load_scenarios_json(paths.scenarios_json)
    df["scenario_title_zh"] = df["scenario_id"].astype(str).map(lambda sid: _scenario_title(raw, sid))
    cols = [
        "scenario_id",
        "scenario_title_zh",
        "soc0",
        "n",
        "mean_h",
        "std_h",
        "cv",
        "p05_h",
        "p50_h",
        "p95_h",
        "width90_h",
        "width90_pct",
    ]
    return df[cols].sort_values(["width90_h"], ascending=False)


def _export_data_05_component_driver_matrix(paths: Q2Paths) -> pd.DataFrame:
    df = pd.read_csv(paths.out_reports / "component_drivers_matrix.csv")
    raw = load_scenarios_json(paths.scenarios_json)
    df["scenario_title_zh"] = df["scenario_id"].astype(str).map(lambda sid: _scenario_title(raw, sid))
    return df[["scenario_id", "scenario_title_zh", "component_id", "title_zh", "mean_delta_h", "n"]].sort_values(
        ["scenario_id", "mean_delta_h"], ascending=[True, False]
    )


def _export_data_06_little_effect(paths: Q2Paths) -> pd.DataFrame:
    df = pd.read_csv(paths.out_reports / "little_effect" / "little_effect_factors.csv")
    return df.sort_values(["scenario_id", "delta_pct"], ascending=[True, False])


def _export_data_07_androwatts_total_power(paths: Q2Paths) -> pd.DataFrame:
    df = pd.read_csv(paths.out_reports / "validation_open_data" / "per_case.csv")
    keep = [
        "test_id",
        "duration_s",
        "soc0",
        "temp_c",
        "brightness_nits",
        "cpu_load",
        "gpu_load",
        "gps_on",
        "obs_total_w",
        "pred_total_w",
        "obs_screen_w",
        "obs_cpu_w",
        "obs_gpu_w",
        "obs_radio_w",
        "obs_gps_w",
        "obs_background_w",
        "obs_base_w",
        "pred_screen_w",
        "pred_cpu_w",
        "pred_gpu_w",
        "pred_radio_w",
        "pred_gps_w",
        "pred_background_w",
        "pred_base_w",
    ]
    keep = [c for c in keep if c in df.columns]
    return df[keep].sort_values(["obs_total_w"], ascending=False)


def _export_data_08_energy_per_mb(paths: Q2Paths) -> pd.DataFrame:
    df = pd.read_csv(paths.out_reports / "validation_smartphone_measurements" / "per_test.csv")
    # 该图主要看 energy_per_mb_j 的分布；保留必要字段即可
    keep = [
        "phone",
        "test",
        "role",
        "proto",
        "link",
        "mean_power_w",
        "baseline_power_w",
        "delta_power_w",
        "throughput_MBps",
        "energy_per_mb_j",
        "duration_s",
        "tte_equiv_h",
    ]
    keep = [c for c in keep if c in df.columns]
    return df[keep].sort_values(["energy_per_mb_j"], ascending=False)


def _export_data_09_tte_proxy_compare(paths: Q2Paths) -> pd.DataFrame:
    d = paths.out_reports / "validation_tte_trace_smartphone_measurements"
    # 终稿优先使用 per-test（点数更充分）；若不存在则回退到 per-group
    p_test = d / "per_test_tte.csv"
    if p_test.exists():
        df = pd.read_csv(p_test)
        # per-test 可能包含更多列，保留全部以便追溯（重构目录里 root 只放图）
        return df.sort_values(["tte_obs_equiv_h"], ascending=False)

    df = pd.read_csv(d / "per_group_tte.csv")
    return df.sort_values(["tte_obs_equiv_h"], ascending=False)


def _export_data_10_long_horizon_overlay(paths: Q2Paths) -> pd.DataFrame:
    """把用户分布与场景预测合并到一个表（用 source 字段区分）。"""
    users = pd.read_csv(paths.out_reports / "validation_user_behavior" / "users.csv")
    sc = pd.read_csv(paths.out_reports / "validation_user_behavior" / "scenario_tte_pred.csv")
    # 兼容：旧版本只有 tte_est_h；新版本同时提供 daily 与 active 两种口径
    rows: list[pd.DataFrame] = []
    if "tte_est_daily_h" in users.columns:
        a_daily = users[["user_id", "class", "tte_est_daily_h"]].copy()
        a_daily["source"] = "user_behavior_daily"
        a_daily.rename(columns={"tte_est_daily_h": "tte_h"}, inplace=True)
        rows.append(a_daily)
    elif "tte_est_h" in users.columns:
        a_legacy = users[["user_id", "class", "tte_est_h"]].copy()
        a_legacy["source"] = "user_behavior_daily"
        a_legacy.rename(columns={"tte_est_h": "tte_h"}, inplace=True)
        rows.append(a_legacy)

    if "tte_est_active_h" in users.columns:
        a_active = users[["user_id", "class", "tte_est_active_h"]].copy()
        a_active["source"] = "user_behavior_active"
        a_active.rename(columns={"tte_est_active_h": "tte_h"}, inplace=True)
        rows.append(a_active)

    if not rows:
        raise ValueError("validation_user_behavior/users.csv 缺少 tte 列（tte_est_daily_h / tte_est_active_h / tte_est_h）")

    a = pd.concat(rows, ignore_index=True)
    a["scenario_id"] = ""
    a["title_zh"] = ""
    a["tte_p05_h"] = np.nan
    a["tte_p50_h"] = np.nan
    a["tte_p95_h"] = np.nan

    b = sc[["scenario_id", "title_zh", "tte_mean_h", "tte_p05_h", "tte_p50_h", "tte_p95_h"]].copy()
    b["source"] = "model_scenario"
    b["user_id"] = np.nan
    b["class"] = np.nan
    b.rename(columns={"tte_mean_h": "tte_h"}, inplace=True)

    cols = ["source", "user_id", "class", "scenario_id", "title_zh", "tte_h", "tte_p05_h", "tte_p50_h", "tte_p95_h"]
    return pd.concat([a[cols], b[cols]], ignore_index=True)


def _agg_master_table(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """按 validate_q2_master_table.py 的口径生成两张图的聚合数据。"""
    # 1) TTE vs SOH：按负载×老化档位聚合，输出均值与范围
    tte_agg = (
        df.groupby(["load_label", "battery_state_label"], observed=False)
        .agg(
            SOH_mean=("SOH", "mean"),
            tte_mean_h=("tte_h", "mean"),
            tte_min_h=("tte_h", "min"),
            tte_max_h=("tte_h", "max"),
            n=("tte_h", "count"),
        )
        .reset_index()
    )

    # 2) soc_end vs SOH：按负载×老化档位聚合，输出均值与范围
    soc_agg = (
        df.groupby(["load_label", "battery_state_label"], observed=False)
        .agg(
            SOH_mean=("SOH", "mean"),
            soc_mean=("soc_end", "mean"),
            soc_min=("soc_end", "min"),
            soc_max=("soc_end", "max"),
            n=("soc_end", "count"),
        )
        .reset_index()
    )
    return tte_agg, soc_agg


def _export_data_11_tte_vs_soh(paths: Q2Paths) -> pd.DataFrame:
    df = pd.read_csv(paths.out_reports / "validation_master_table" / "tte_by_state.csv")
    tte_agg, _soc_agg = _agg_master_table(df)
    return tte_agg.sort_values(["load_label", "SOH_mean"], ascending=[True, False])


def _export_data_12_soc_end_vs_soh(paths: Q2Paths) -> pd.DataFrame:
    df = pd.read_csv(paths.out_reports / "validation_master_table" / "tte_by_state.csv")
    _tte_agg, soc_agg = _agg_master_table(df)
    return soc_agg.sort_values(["load_label", "SOH_mean"], ascending=[True, False])


def _export_data_02_variants(
    paths: Q2Paths,
    *,
    soc0: float = 1.0,
    # 兜底重算时尽量对齐 make_q2_plots.py 的默认参数（dt=5，driver_seeds=25）
    dt_s: float = 5.0,
    n_seeds: int = 25,
    seed0: int = 1000,
) -> pd.DataFrame:
    """导出“条件对照（OAT/variants）”数据版本（对应 fig05_variants_compare）。

    优先策略：
    0) 若存在 out_reports/q2/conditions_oat_stats.csv（no12 口径：统一 x 轴的 OAT 条件开关），
       则优先使用它（与修正后的图 02 同源）。
    1) 若 out_reports/q2/tte_summary.csv 已包含 variants（由 run_q2_report.py --include-variants 生成），
       则直接从报表读入（与 figure.png 同源，最稳）。
    2) 否则做“兜底重算”（仅为了导出 data.csv，便于 AI/程序读取；终稿不建议依赖兜底）。
    """

    raw = load_scenarios_json(paths.scenarios_json)

    # 0) 优先：no12 口径的统一 OAT 条件表（修正图 02 x 轴的核心）
    oat = Path(paths.out_reports) / "conditions_oat_stats.csv"
    if oat.exists():
        try:
            df = pd.read_csv(oat)
            df = df[df["soc0"].astype(float) == float(soc0)].copy()
            if not df.empty:
                if "scenario_title_zh" not in df.columns:
                    df["scenario_title_zh"] = df["scenario_id"].astype(str).map(lambda sid: _scenario_title(raw, sid))
                if "variant_label_zh" not in df.columns:
                    df["variant_label_zh"] = df["variant"].astype(str).map(_variant_label_zh)
                # 基线放前
                df["variant_is_baseline"] = (df["variant"].astype(str) == "-").astype(int)
                df = df.sort_values(["scenario_id", "variant_is_baseline"], ascending=[True, False]).drop(columns=["variant_is_baseline"])
                return df
        except Exception:
            # 若读失败则继续回退到旧逻辑
            pass

    # 0) 优先读 variants_stats.csv（与图 02 同源化的推荐路径）
    vstats = Path(paths.out_reports) / "variants_stats.csv"
    if vstats.exists():
        try:
            df = pd.read_csv(vstats)
            df = df[df["soc0"].astype(float) == float(soc0)].copy()
            # 若没有 variants（只有 baseline），则继续走后续兜底逻辑
            if df["variant"].astype(str).nunique() > 1:
                # 若缺少中文标题/标签则补齐
                if "scenario_title_zh" not in df.columns:
                    df["scenario_title_zh"] = df["scenario_id"].astype(str).map(lambda sid: _scenario_title(raw, sid))
                if "variant_label_zh" not in df.columns:
                    df["variant_label_zh"] = df["variant"].astype(str).map(_variant_label_zh)
                # 基线放前
                df["variant_is_baseline"] = (df["variant"].astype(str) == "-").astype(int)
                df = df.sort_values(["scenario_id", "variant_is_baseline"], ascending=[True, False]).drop(columns=["variant_is_baseline"])
                return df
        except Exception:
            pass

    # 1) 优先从报表读（同源）
    summ = Path(paths.out_reports) / "tte_summary.csv"
    term = Path(paths.out_reports) / "termination_stats.csv"
    if summ.exists():
        try:
            df = pd.read_csv(summ)
            df = df[df["soc0"].astype(float) == float(soc0)].copy()
            if df["variant"].astype(str).nunique() > 1:
                # 补充终止概率（若有）
                if term.exists():
                    try:
                        dtm = pd.read_csv(term)
                        dtm = dtm[dtm["soc0"].astype(float) == float(soc0)].copy()
                        df = df.merge(
                            dtm[["scenario_id", "variant", "p_cutoff", "p_soc_min", "p_insufficient_power"]],
                            on=["scenario_id", "variant"],
                            how="left",
                        )
                    except Exception:
                        pass

                df["scenario_title_zh"] = df["scenario_id"].astype(str).map(lambda sid: _scenario_title(raw, sid))
                df["variant_label_zh"] = df["variant"].astype(str).map(_variant_label_zh)
                keep = [
                    "scenario_id",
                    "scenario_title_zh",
                    "variant",
                    "variant_label_zh",
                    "soc0",
                    "n",
                    "mean_h",
                    "p05_h",
                    "p50_h",
                    "p95_h",
                    "p_cutoff",
                    "p_soc_min",
                    "p_insufficient_power",
                ]
                keep = [c for c in keep if c in df.columns]
                out = df[keep].copy()
                # 基线放前
                out["variant_is_baseline"] = (out["variant"].astype(str) == "-").astype(int)
                out = out.sort_values(["scenario_id", "variant_is_baseline"], ascending=[True, False]).drop(columns=["variant_is_baseline"])
                return out
        except Exception:
            # 读报表失败则回退到兜底重算
            pass

    # 2) 兜底：重算 variants（仅用于导出 data.csv）
    power1 = PowerParams1Stateful.from_json(paths.power_stateful_json)
    batt = BatteryParams3Aging.from_json(paths.phone_json)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    rows: list[dict[str, Any]] = []
    sids = list(raw.get("scenarios", {}).keys())
    for sid_idx, sid in enumerate(sids):
        spec = raw["scenarios"][sid]
        variants = list(spec.get("variants", {}).keys())
        vnames = ["-"] + [str(v) for v in variants]
        for v in vnames:
            sc = materialize_scenario(raw, sid, variant=(None if v == "-" else v))
            xs: list[float] = []
            statuses: list[str] = []
            for k in range(int(n_seeds)):
                seed = int(seed0) + sid_idx * 100 + k
                pm = StatefulPowerModel1(power1, seed=seed)
                r = simulate_model3_aging(
                    sc,
                    power_params=power0_dummy,
                    power_model=pm,
                    battery_params=batt,
                    soc0=float(soc0),
                    dt_s=float(dt_s),
                )
                if r.tte_h is not None:
                    xs.append(float(r.tte_h))
                    statuses.append(str(r.status))

            n = len(xs)
            denom = float(n) if n > 0 else float("nan")
            counts = {
                "cutoff": float(sum(1 for s in statuses if s == "cutoff")),
                "soc_min": float(sum(1 for s in statuses if s == "soc_min")),
                "insufficient_power": float(sum(1 for s in statuses if s == "insufficient_power")),
            }
            arr = np.array(xs, dtype=float) if xs else np.array([], dtype=float)
            rows.append(
                {
                    "scenario_id": str(sid),
                    "scenario_title_zh": _scenario_title(raw, sid),
                    "variant": str(v),
                    "variant_label_zh": _variant_label_zh(str(v)),
                    "soc0": float(soc0),
                    "dt_s": float(dt_s),
                    "n_seeds": int(n_seeds),
                    "n": int(n),
                    "mean_h": float(np.mean(arr)) if xs else float("nan"),
                    "p05_h": float(np.quantile(arr, 0.05)) if xs else float("nan"),
                    "p50_h": float(np.quantile(arr, 0.50)) if xs else float("nan"),
                    "p95_h": float(np.quantile(arr, 0.95)) if xs else float("nan"),
                    "p_cutoff": float(counts["cutoff"] / denom) if np.isfinite(denom) else float("nan"),
                    "p_soc_min": float(counts["soc_min"] / denom) if np.isfinite(denom) else float("nan"),
                    "p_insufficient_power": float(counts["insufficient_power"] / denom) if np.isfinite(denom) else float("nan"),
                }
            )

    df = pd.DataFrame(rows)
    df["variant_is_baseline"] = (df["variant"].astype(str) == "-").astype(int)
    df = df.sort_values(["scenario_id", "variant_is_baseline"], ascending=[True, False]).drop(columns=["variant_is_baseline"])
    return df


def _export_data_13_or_14_trace(paths: Q2Paths, *, scenario_id: str, soc0: float = 1.0, dt_s: float = 5.0, seed: int = 1) -> pd.DataFrame:
    raw = load_scenarios_json(paths.scenarios_json)
    power1 = PowerParams1Stateful.from_json(paths.power_stateful_json)
    batt = BatteryParams3Aging.from_json(paths.phone_json)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    sc = materialize_scenario(raw, scenario_id)
    pm = StatefulPowerModel1(power1, seed=int(seed))
    tr = simulate_model3_aging_trace(
        sc,
        power_params=power0_dummy,
        power_model=pm,
        battery_params=batt,
        soc0=float(soc0),
        dt_s=float(dt_s),
    )
    df = pd.DataFrame(
        {
            "t_s": np.array(tr.t_s, dtype=float),
            "t_h": np.array(tr.t_s, dtype=float) / 3600.0,
            "soc": np.array(tr.soc, dtype=float),
            "soc_pct": np.array(tr.soc, dtype=float) * 100.0,
            "v_term_V": np.array(tr.v_term_V, dtype=float),
            "temp_C": np.array(tr.temp_C, dtype=float),
            "p_total_W": np.array(tr.p_W, dtype=float),
        }
    )
    df["scenario_id"] = str(scenario_id)
    df["scenario_title_zh"] = _scenario_title(raw, scenario_id)
    df["soc0"] = float(soc0)
    df["dt_s"] = float(dt_s)
    df["seed"] = int(seed)
    df["status"] = str(tr.status)
    return df


def _write_df_csv(df: pd.DataFrame, path: Path) -> None:
    _ensure_dir(path.parent)
    # 不删除旧文件：若重复运行导致覆盖，则先把旧 data.csv 移到 other/_history/ 留档。
    if path.exists():
        _backup_existing(path, _ensure_dir(path.parent / "_history"))
    df.to_csv(path, index=False, encoding="utf-8")


def _restructure_one_folder(folder: Path, *, backup_context: bool = True) -> None:
    other = _ensure_dir(folder / "other")
    history = _ensure_dir(other / "_history")

    # 1) about.md -> other/
    _safe_move(folder / "about.md", other / "about.md", history_dir=history)

    # 2) context.md -> split
    ctx = folder / "context.md"
    if ctx.exists():
        full = _read_text(ctx)
        if backup_context:
            # 不删除旧文件：把原始 context.md 移到 other/context_full.md（若已存在则先备份）
            dst = other / "context_full.md"
            if dst.exists():
                _backup_existing(dst, history)
            _safe_move(ctx, dst, history_dir=history)
        else:
            # 仍保留原文件（放入历史目录）
            _safe_move(ctx, history / f"{_now_ts()}_context.md", history_dir=history)
        insert_sug, zh, en = _split_context_md(full)

        # 00 总览可能没有中英分段；此时 insert_sug 就是全文
        if zh.strip() or en.strip():
            zh_out = (
                "# 插入建议（论文中可删除）\n\n"
                + insert_sug.strip()
                + "\n\n"
                + "# 中文正文（可直接粘贴）\n\n"
                + zh.strip()
                + "\n"
            )
            zh_path = folder / "paper_fragment_zh.md"
            if zh_path.exists():
                _backup_existing(zh_path, history)
            _write_text(zh_path, zh_out)

            if en.strip():
                en_out = "# English fragment (copy into paper)\n\n" + en.strip() + "\n"
                en_path = other / "paper_fragment_en.md"
                if en_path.exists():
                    _backup_existing(en_path, history)
                _write_text(en_path, en_out)
        else:
            # 只中文（比如 00 总览）
            zh_path = folder / "paper_fragment_zh.md"
            if zh_path.exists():
                _backup_existing(zh_path, history)
            _write_text(zh_path, insert_sug.strip() + "\n")

    # 3) png 重命名/归档
    paper_png, study_png = _pick_png_pair(folder)
    if paper_png is not None:
        if paper_png.name != "figure.png":
            _safe_move(paper_png, folder / "figure.png", history_dir=history)
    if study_png is not None:
        _safe_move(study_png, other / "figure_study.png", history_dir=history)

    # 4) 若 about.md 提供 out_plots 图片来源，则把最新图片同步过来（覆盖旧图）
    _sync_figures_from_about(folder)


def main() -> int:
    paths = Q2Paths(
        materials_root=REPO_DIR / "26A" / "论文" / "理论模型" / "论文阶段" / "Q2材料",
        out_reports=REPO_DIR / "26A" / "src" / "out_reports" / "q2",
        scenarios_json=REPO_DIR / "26A" / "src" / "configs" / "scenarios_v0.json",
        power_stateful_json=REPO_DIR / "26A" / "src" / "configs" / "power_params_v2_no7_awcal_mo_v2.json",
        phone_json=REPO_DIR / "26A" / "src" / "configs" / "phone_default_v3_aging.json",
    )

    root = paths.materials_root
    if not root.exists():
        raise FileNotFoundError(f"未找到 Q2材料 目录：{root}")

    # 先重构目录（移动/拆分/重命名）
    subdirs = sorted([p for p in root.iterdir() if p.is_dir()])
    for d in subdirs:
        _restructure_one_folder(d, backup_context=True)

    # 导出数据版本（写到 each/other/）
    data_jobs: dict[str, tuple[str, Any]] = {
        "01-Q2-TTE矩阵_场景×SOC0": ("data.csv", lambda: _export_data_01_tte_matrix(paths)),
        "02-Q2-变体对比_条件变化对TTE影响": ("data.csv", lambda: _export_data_02_variants(paths)),
        "03-Q2-不确定性分布_UQ": ("data.csv", lambda: _export_data_03_uq_distribution(paths)),
        "04-Q2-不确定性宽度排名_模型好坏边界": ("data.csv", lambda: _export_data_04_uq_spread(paths)),
        "05-Q2-drivers矩阵_每种情形下驱动因素": ("data.csv", lambda: _export_data_05_component_driver_matrix(paths)),
        "06-Q2-surprisingly_little_影响出乎意料地小": ("data.csv", lambda: _export_data_06_little_effect(paths)),
        "07-Q2-观测对照_AndroWatts总功耗": ("data.csv", lambda: _export_data_07_androwatts_total_power(paths)),
        "08-Q2-观测对照_通信单位能耗JMB": ("data.csv", lambda: _export_data_08_energy_per_mb(paths)),
        "09-Q2-观测对照_TTE层面对齐": ("data.csv", lambda: _export_data_09_tte_proxy_compare(paths)),
        "10-Q2-观测对照_长时间TTE分布": ("data.csv", lambda: _export_data_10_long_horizon_overlay(paths)),
        "11-Q2-历史老化影响_TTEvsSOH": ("data.csv", lambda: _export_data_11_tte_vs_soh(paths)),
        "12-Q2-提前关机证据_终止SOCvsSOH": ("data.csv", lambda: _export_data_12_soc_end_vs_soh(paths)),
        "13-Q2-解释性轨迹_待机": ("data.csv", lambda: _export_data_13_or_14_trace(paths, scenario_id="S0_standby")),
        "14-Q2-解释性轨迹_游戏": ("data.csv", lambda: _export_data_13_or_14_trace(paths, scenario_id="S3_gaming")),
    }

    for dname, (fname, fn) in data_jobs.items():
        d = root / dname / "other"
        if not d.exists():
            continue
        try:
            df = fn()
        except Exception as e:
            _write_text(d / "figure_data_ERROR.txt", f"{type(e).__name__}: {e}\n")
            continue
        _write_df_csv(df, d / fname)

    # 更新汇总稿中的图片路径（旧名 -> figure.png）
    summary = root / "Q2_中文插入稿_汇总.md"
    if summary.exists():
        s = _read_text(summary)
        # 把每个子文件夹内的图片名统一替换为 figure.png（仅替换已知 01~14）
        for d in subdirs:
            if not re.match(r"^\d\d-Q2-", d.name):
                continue
            # 匹配 ./<dir>/<something>.png -> ./<dir>/figure.png
            s = re.sub(rf"(\./{re.escape(d.name)}/)[^)]+\.png", r"\g<1>figure.png", s)
        _write_text(summary, s)

    print(f"完成：已重构 Q2材料 目录并导出数据版本 -> {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
