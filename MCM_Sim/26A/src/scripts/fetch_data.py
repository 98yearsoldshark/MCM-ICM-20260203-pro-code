#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键拉取/同步 26A 所需的大体积数据（便于整理到 GitHub）。

为什么需要这个脚本？
- `MCM_Sim/26A/data/` 下包含多个公开数据集（CALCE / NASA / BatteryArchive / BIL 等）。
- 其中部分数据体积为 GB 级，不适合直接提交到 GitHub。
- 本项目已为多数数据源准备了可复现的同步脚本；本文件只是做一个“总入口”。

使用方式：

  # 拉取 Q1/Q2/Q3 的常用数据（推荐）
  PYTHONPATH=MCM_Sim/26A/src python3 MCM_Sim/26A/src/scripts/fetch_data.py --profile core

  # 全部拉取（可能非常耗时/占空间）
  PYTHONPATH=MCM_Sim/26A/src python3 MCM_Sim/26A/src/scripts/fetch_data.py --profile all

说明：
- 下载依赖系统 `curl`；解压可能需要较大磁盘空间。
- 若某些站点在你的网络环境下不可达，请考虑切换网络/VPN，或改用目录内 README 提供的手工下载方式。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = REPO_ROOT / "MCM_Sim" / "26A" / "data"


@dataclass(frozen=True)
class Task:
    name: str
    script: Path
    extra_args: list[str]
    description_zh: str


def _run(task: Task) -> None:
    if not task.script.exists():
        raise FileNotFoundError(f"找不到脚本：{task.script}")
    cmd = [sys.executable, str(task.script), *task.extra_args]

    # 这里刻意把将执行的命令打印出来，便于你复制到论文“数据复现流程/附录”里
    print(f"\n=== {task.name} ===\n{task.description_zh}\n$ {' '.join(cmd)}")
    p = subprocess.run(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"任务失败：{task.name}（exit={p.returncode}）")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="一键同步 MCM 2026 A 所需大体积数据")
    ap.add_argument(
        "--profile",
        choices=["core", "q1", "q2", "q3", "all"],
        default="core",
        help=(
            "选择要同步的数据范围：\n"
            "- core：Q1/Q2/Q3 常用（CALCE + NASA + SmartphoneMeasurements）\n"
            "- q1：仅电池参数估计/验证（CALCE）\n"
            "- q2：仅手机侧观测对照补充（SmartphoneMeasurements）\n"
            "- q3：敏感性/观测锚定补充（NASA + SmartphoneMeasurements）\n"
            "- all：全部（含 BatteryArchive / Battery-Intelligence-Lab）"
        ),
    )
    ap.add_argument("--force", action="store_true", help="对部分任务传递强制重新下载参数（若支持）")
    args = ap.parse_args(argv)

    # 1) CALCE（电池侧 OCV/ECM 校准最常用）
    calce = Task(
        name="CALCE-UMD",
        script=DATA_DIR / "calce-umd" / "scripts" / "sync_calce_umd.py",
        extra_args=[],
        description_zh="下载并解压 CALCE-UMD 电池公开数据（体积较大）。",
    )

    # 2) NASA（Q3 的脉冲锚定/随机负载验证常用）
    nasa_args: list[str] = []
    if args.force:
        nasa_args.append("--force-download")
    nasa = Task(
        name="NASA-BatteryData",
        script=DATA_DIR / "NASA-BatteryData" / "scripts" / "sync_nasa_batterydata.py",
        extra_args=nasa_args,
        description_zh="下载 NASA PCoE 5/11 号电池数据，并解压 11 号随机使用数据集。",
    )

    # 3) SmartphoneMeasurements（通信功耗观测对照）
    sm_args: list[str] = []
    if args.force:
        sm_args.append("--force")
    smartphone = Task(
        name="SmartphoneMeasurements",
        script=DATA_DIR / "SmartphoneMeasurements" / "scripts" / "sync_smartphone_measurements.py",
        extra_args=sm_args,
        description_zh="下载 SmartphoneMeasurements.zip（用于 Q2/Q3 的观测对照实验）。",
    )

    # 4) BatteryArchive（可选增强：额外电芯证据）
    battery_archive = Task(
        name="Battery-Archive",
        script=DATA_DIR / "Battery-Archive" / "scripts" / "sync_battery_archive.py",
        extra_args=[],
        description_zh="同步 BatteryArchive.org 导出的公开数据（可能耗时较长）。",
    )

    # 5) Battery Intelligence Lab（可选增强：外部方法/数据索引）
    bil = Task(
        name="Battery-Intelligence-Lab",
        script=DATA_DIR / "Battery-Intelligence-Lab" / "scripts" / "sync_assets.py",
        extra_args=[],
        description_zh="下载 Battery Intelligence Lab Data and code 页面列出的资源（体积可能很大）。",
    )

    if args.profile == "core":
        tasks = [calce, nasa, smartphone]
    elif args.profile == "q1":
        tasks = [calce]
    elif args.profile == "q2":
        tasks = [smartphone]
    elif args.profile == "q3":
        tasks = [nasa, smartphone]
    else:
        tasks = [calce, nasa, smartphone, battery_archive, bil]

    print("将执行以下同步任务：")
    for t in tasks:
        print(f"- {t.name}: {t.script.relative_to(REPO_ROOT)}")

    for t in tasks:
        _run(t)

    print("\n[ok] 数据同步完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
