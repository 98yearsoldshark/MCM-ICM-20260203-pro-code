#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同步/整理 NASA PCoE 电池公开数据到本目录（NASA-BatteryData/）。

目的：
- 为 `MCM_Sim/26A` 的电池端“观测锚定/额外验证”（例如 Q1/Q3）提供可复现的数据来源；
- 让仓库在提交到 GitHub 时**不必携带 GB 级数据**：只提交脚本与说明，数据可一键拉取。

数据来源（直链，公开镜像）：
- 5. Battery Data Set：
  - https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip
- 11. Randomized Battery Usage Data Set：
  - https://phm-datasets.s3.amazonaws.com/NASA/11.+Randomized+Battery+Usage+Data+Set.zip

输出（与本仓库既有路径保持一致，避免改动主代码）：
- `5.+Battery+Data+Set.zip`（默认仅下载，不自动解压）
- `11.+Randomized+Battery+Usage+Data+Set/`（会解压到此目录）
- `manifest.csv`（可选：记录大小/sha256/来源 URL/状态）

用法示例：

  # 下载 5 号 + 下载并解压 11 号
  python3 MCM_Sim/26A/data/NASA-BatteryData/scripts/sync_nasa_batterydata.py

  # 只拉取 11 号（用于 Q3 的脉冲锚定等）
  python3 MCM_Sim/26A/data/NASA-BatteryData/scripts/sync_nasa_batterydata.py --only 11

注意：
- 下载使用系统 `curl`（支持断点续传 `-C -`）。
- 若目标解压目录已存在且非空，默认跳过解压（避免误覆盖）。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


URL_5_ZIP = "https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip"
URL_11_ZIP = "https://phm-datasets.s3.amazonaws.com/NASA/11.+Randomized+Battery+Usage+Data+Set.zip"


@dataclass(frozen=True)
class Item:
    name: str
    url: str
    local_path: Path
    extract_to: Path | None = None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"命令失败：{cmd}\n\n输出：\n{p.stdout}")


def _curl_download(url: str, dst: Path, *, force: bool) -> str:
    """下载到 dst，返回状态字符串。"""

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 0 and not force:
        return "skip_exists"

    # -L 跟随跳转；-C - 断点续传；--retry 增强稳定性
    cmd = [
        "curl",
        "-L",
        "--retry",
        "3",
        "--retry-delay",
        "2",
        "-C",
        "-",
        "-o",
        str(dst),
        url,
    ]
    _run(cmd)
    if not dst.exists() or dst.stat().st_size == 0:
        raise RuntimeError(f"下载完成但文件为空：{dst}")
    return "downloaded"


def _safe_extract_11(zip_path: Path, root: Path, *, force_extract: bool) -> str:
    """解压 11 号数据集到本目录预期路径。"""

    target = root / "11.+Randomized+Battery+Usage+Data+Set"
    if target.exists() and any(target.iterdir()) and not force_extract:
        return "skip_nonempty"

    # 为避免“意外覆盖”，只有 force_extract 才允许清空目标。
    if target.exists() and any(target.iterdir()) and force_extract:
        # 不做 rm -rf：让用户手工删除更安全。
        raise RuntimeError(
            "目标解压目录已存在且非空。\n"
            "为避免误覆盖，请手动删除后重试：\n"
            f"  {target}"
        )

    with zipfile.ZipFile(zip_path) as z:
        # 过滤 __MACOSX 等无关条目
        names = [n for n in z.namelist() if n and not n.startswith("__MACOSX/")]
        top = {n.split("/", 1)[0] for n in names if "/" in n}

        # 两种常见结构：
        # 1) 顶层即 "11.+Randomized+Battery+Usage+Data+Set"（推荐）
        # 2) 顶层即 "11. Randomized Battery Usage Data Set"（需要包一层目录）
        if top == {"11.+Randomized+Battery+Usage+Data+Set"}:
            z.extractall(root)
        else:
            target.mkdir(parents=True, exist_ok=True)
            z.extractall(target)

    if not target.exists() or not any(target.iterdir()):
        raise RuntimeError(f"解压后目录为空或不存在：{target}")
    return "extracted"


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    seen: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="同步 NASA PCoE 电池数据（5/11）到本目录")
    ap.add_argument(
        "--only",
        choices=["5", "11"],
        default=None,
        help="只处理某一个数据集（默认同时处理 5+11）",
    )
    ap.add_argument(
        "--force-download",
        action="store_true",
        help="即使本地文件已存在也重新下载（不建议频繁使用）",
    )
    ap.add_argument(
        "--force-extract-11",
        action="store_true",
        help="允许覆盖式解压 11（安全起见：目前仍要求你先手动删除目标目录）",
    )
    ap.add_argument(
        "--no-manifest",
        action="store_true",
        help="不生成/更新 manifest.csv（默认会生成）",
    )
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    if root.name != "NASA-BatteryData":
        print("[warn] 脚本路径异常：将按 parents[1] 作为根目录：", root)

    items: list[Item] = [
        Item(name="nasa_pcoe_05", url=URL_5_ZIP, local_path=root / "5.+Battery+Data+Set.zip"),
        Item(
            name="nasa_pcoe_11",
            url=URL_11_ZIP,
            local_path=root / "11.+Randomized+Battery+Usage+Data+Set.zip",
            extract_to=root / "11.+Randomized+Battery+Usage+Data+Set",
        ),
    ]

    if args.only is not None:
        items = [it for it in items if it.name.endswith(args.only.zfill(2)) or it.name.endswith(f"_{args.only}")]

    rows: list[dict[str, str]] = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for it in items:
        status_dl = ""
        status_ex = ""
        try:
            status_dl = _curl_download(it.url, it.local_path, force=bool(args.force_download))
            sha = _sha256(it.local_path)
            size = str(it.local_path.stat().st_size)

            if it.extract_to is not None:
                status_ex = _safe_extract_11(it.local_path, root, force_extract=bool(args.force_extract_11))

            rows.append(
                {
                    "ts": ts,
                    "name": it.name,
                    "local_path": str(it.local_path.relative_to(root)),
                    "size_bytes": size,
                    "sha256": sha,
                    "source_url": it.url,
                    "status_download": status_dl,
                    "status_extract": status_ex or "n/a",
                }
            )
            print(f"[ok] {it.name}: download={status_dl} extract={status_ex or 'n/a'}")
        except Exception as e:
            rows.append(
                {
                    "ts": ts,
                    "name": it.name,
                    "local_path": str(it.local_path.relative_to(root)),
                    "size_bytes": str(it.local_path.stat().st_size) if it.local_path.exists() else "0",
                    "sha256": _sha256(it.local_path) if it.local_path.exists() else "",
                    "source_url": it.url,
                    "status_download": status_dl or "failed",
                    "status_extract": status_ex or "failed",
                    "error": str(e),
                }
            )
            print(f"[fail] {it.name}: {e}", file=sys.stderr)

    if not args.no_manifest:
        _write_manifest(root / "manifest.csv", rows)
        print(f"[ok] manifest: {root / 'manifest.csv'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
