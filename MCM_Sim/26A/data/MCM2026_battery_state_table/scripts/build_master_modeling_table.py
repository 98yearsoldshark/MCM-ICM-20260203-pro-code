#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成/重建 MCM2026 master_modeling_table（用于把仓库整理到 GitHub）。

背景：
- 主表 `MCM2026A题锂电池数据表：master_modeling_table.csv` 是**派生数据**：
  AndroWatts aggregated.csv（1000 行） × 电池状态表（36 行）的笛卡尔积，得到 36000 行。
- 该 CSV 单文件约 40MB，虽然不算“超大”，但提交到 GitHub 会让仓库显著膨胀。

因此推荐做法：
- GitHub 仓库里只提交：脚本 + 小表（battery_state_table.csv、变量字典、说明文档等）；
- 需要时本地运行本脚本重建主表（可复现、可追溯）。

输入（默认路径与本仓库一致）：
- `MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`
- `MCM_Sim/26A/data/MCM2026_battery_state_table/MCM2026_battery_state_table.csv`

输出：
- `MCM_Sim/26A/data/MCM2026_battery_state_table/MCM2026A题锂电池数据表：master_modeling_table.csv`

注意：
- 本脚本会复刻 `MCM2026_数据来源与说明文档.md` 中第 3.1/3.3 节的规则；
- 不会从网络下载任何数据（下载请见各数据源目录的 sync 脚本）。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


# .../<repo_root>/MCM_Sim/26A/data/MCM2026_battery_state_table/scripts/<this_file>
REPO_ROOT = Path(__file__).resolve().parents[5]
DATA_DIR = REPO_ROOT / "MCM_Sim" / "26A" / "data"
OPEN_DATA_DEFAULT = DATA_DIR / "open_data" / "material" / "res_test" / "aggregated.csv"
STATE_TABLE_DEFAULT = DATA_DIR / "MCM2026_battery_state_table" / "MCM2026_battery_state_table.csv"
OUT_DEFAULT = DATA_DIR / "MCM2026_battery_state_table" / "MCM2026A题锂电池数据表：master_modeling_table.csv"
MANIFEST_DEFAULT = DATA_DIR / "MCM2026_battery_state_table" / "manifest_master_table.csv"


@dataclass(frozen=True)
class BuildStats:
    n_phone_tests: int
    n_states: int
    n_rows: int
    n_cols: int


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def _sum_cols(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    if not cols:
        return pd.Series(np.zeros(len(df), dtype=float))
    x = pd.DataFrame({c: _to_num(df[c]).fillna(0.0) for c in cols})
    return x.sum(axis=1)


def build_master_table(aggregated_csv: Path, battery_state_table_csv: Path) -> tuple[pd.DataFrame, BuildStats]:
    """构造 master_modeling_table（36000×93）。"""

    # 1) AndroWatts：1000 条手机功耗测试
    df = pd.read_csv(aggregated_csv)
    if "ID" not in df.columns:
        raise ValueError("aggregated.csv 缺少 ID 列，无法生成 phone_test_id")
    df = df.rename(columns={"ID": "phone_test_id"})

    # 2) 电池状态表：36 条老化状态（SOH+OCV）
    st = pd.read_csv(battery_state_table_csv)
    # 去掉内部标记列（以 '_' 开头）
    st = st[[c for c in st.columns if not str(c).startswith("_")]]

    # 3) 派生列（对齐说明文档 3.1）
    # 单位换算
    df["soc0"] = _to_num(df.get("BATTERY__PERCENT")).div(100.0)
    df["temp_c"] = _to_num(df.get("AVG_SOC_TEMP")).div(1000.0)
    df["I_obs_A"] = _to_num(df.get("BATTERY_DISCHARGE_RATE_UAS")).mul(1e-6)

    # 合计功耗：P_total_uW = sum(*_ENERGY_UW)
    energy_uw_cols = [c for c in df.columns if ("_ENERGY_UW" in str(c)) and ("_ENERGY_AVG_UWS" not in str(c))]
    df["P_total_uW"] = _sum_cols(df, energy_uw_cols)

    # 合计能量代理（uW*s）：E_total_uWh_est = sum(*_ENERGY_AVG_UWS)
    energy_avg_cols = [c for c in df.columns if "_ENERGY_AVG_UWS" in str(c)]
    df["E_total_uWh_est"] = _sum_cols(df, energy_avg_cols)

    # 估计测试时长：duration_s_est = E_total / P_total（秒）
    # 防止除零：P_total==0 -> NaN
    df["duration_s_est"] = df["E_total_uWh_est"] / df["P_total_uW"].replace({0.0: np.nan})
    df["duration_h_est"] = df["duration_s_est"] / 3600.0

    # 4) 笛卡尔积拼接（对齐说明文档 3.3）
    df["_tmp_join_key"] = 1
    st["_tmp_join_key"] = 1
    out = df.merge(st, on="_tmp_join_key", how="inner", suffixes=("", ""))
    out = out.drop(columns=["_tmp_join_key"])

    # 5) 组合派生（需要电池侧 Q_eff_C）
    if "Q_eff_C" not in out.columns:
        raise ValueError("battery_state_table.csv 缺少 Q_eff_C 列")
    out["dSOC_dt_est_per_s"] = -out["I_obs_A"] / _to_num(out["Q_eff_C"])
    out["t_empty_s_est"] = out["soc0"] / (-out["dSOC_dt_est_per_s"]).replace({0.0: np.nan})
    out["t_empty_h_est"] = out["t_empty_s_est"] / 3600.0

    # 6) 列顺序（确保与既有版本一致，便于对比/复现）
    prefix = [
        "phone_test_id",
        "battery_state_id",
        "battery_dataset",
        "battery_cell",
        "battery_state_label",
        "battery_sample",
        "Q_full_Ah",
        "SOH",
        "Q_eff_C",
        "soc0",
        "temp_c",
        "I_obs_A",
        "P_total_uW",
        "duration_s_est",
        "dSOC_dt_est_per_s",
        "t_empty_h_est",
        "ocv_c0",
        "ocv_c1",
        "ocv_c2",
        "ocv_c3",
        "ocv_c4",
        "ocv_c5",
    ]
    # AndroWatts 原始列（保持其原始顺序；已把 ID 改名为 phone_test_id，因此要剔除）
    agg_cols = [c for c in pd.read_csv(aggregated_csv, nrows=0).columns.tolist() if c != "ID"]
    suffix = ["E_total_uWh_est", "duration_h_est", "t_empty_s_est"]

    ordered = [c for c in prefix if c in out.columns] + [c for c in agg_cols if c in out.columns] + suffix
    missing = [c for c in (prefix + agg_cols + suffix) if c not in out.columns]
    if missing:
        raise ValueError(f"生成的主表缺少列：{missing}")
    out = out[ordered]

    stats = BuildStats(
        n_phone_tests=int(len(df)),
        n_states=int(len(st)),
        n_rows=int(out.shape[0]),
        n_cols=int(out.shape[1]),
    )
    return out, stats


def _write_manifest(path: Path, *, out_csv: Path, stats: BuildStats, source_a: Path, source_b: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "ts": ts,
        "out_csv": str(out_csv),
        "out_size_bytes": str(out_csv.stat().st_size),
        "out_sha256": _sha256(out_csv),
        "n_phone_tests": str(stats.n_phone_tests),
        "n_states": str(stats.n_states),
        "n_rows": str(stats.n_rows),
        "n_cols": str(stats.n_cols),
        "source_aggregated_csv": str(source_a),
        "source_battery_state_table_csv": str(source_b),
    }
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        w.writeheader()
        w.writerow(row)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="生成/重建 master_modeling_table.csv（36000×93）")
    ap.add_argument("--aggregated", default=str(OPEN_DATA_DEFAULT), help="AndroWatts aggregated.csv 路径")
    ap.add_argument("--battery-states", default=str(STATE_TABLE_DEFAULT), help="电池状态表路径（36×15）")
    ap.add_argument("--out", default=str(OUT_DEFAULT), help="输出 CSV 路径")
    ap.add_argument("--manifest", default=str(MANIFEST_DEFAULT), help="输出 manifest（可追溯）")
    ap.add_argument("--no-manifest", action="store_true", help="不写 manifest")
    ap.add_argument("--sample-check", action="store_true", help="生成后做一个轻量自检（随机抽样）")
    args = ap.parse_args(argv)

    aggregated = Path(args.aggregated)
    states = Path(args.battery_states)
    out_csv = Path(args.out)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    if not aggregated.exists():
        raise FileNotFoundError(f"找不到 aggregated.csv：{aggregated}")
    if not states.exists():
        raise FileNotFoundError(f"找不到 battery_state_table.csv：{states}")

    out, stats = build_master_table(aggregated, states)
    out.to_csv(out_csv, index=False)

    print(f"[ok] 写入：{out_csv}")
    print(f"[info] shape={stats.n_rows}×{stats.n_cols} (phone_tests={stats.n_phone_tests}, states={stats.n_states})")

    if args.sample_check:
        # 抽样检查：同一 phone_test_id 下，各 state 共享同一套 AndroWatts 字段
        r = out.sample(n=2000, random_state=7)
        g = r.groupby("phone_test_id", sort=False)
        # 只检查少量关键字段，避免耗时
        key_cols = ["P_total_uW", "soc0", "temp_c", "I_obs_A", "duration_s_est"]
        ok = True
        for pid, sub in g:
            if len(sub) < 2:
                continue
            for c in key_cols:
                if sub[c].nunique(dropna=False) != 1:
                    ok = False
                    print(f"[warn] phone_test_id={pid} 列 {c} 在不同 battery_state 下不一致（不应发生）")
                    break
            if not ok:
                break
        if ok:
            print("[ok] sample_check: 通过")

    if not args.no_manifest:
        _write_manifest(Path(args.manifest), out_csv=out_csv, stats=stats, source_a=aggregated, source_b=states)
        print(f"[ok] manifest：{args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

