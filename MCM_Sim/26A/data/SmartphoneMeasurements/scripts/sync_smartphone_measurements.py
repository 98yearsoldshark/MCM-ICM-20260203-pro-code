#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同步 SmartphoneMeasurements 目录下的可再下载文件。

目的：
- GitHub 仓库不提交 `SmartphoneMeasurements.zip`（可再下载且可能较大/许可需回溯）；
- 克隆仓库后可一键拉取，使 Q2/Q3 的“通信功耗观测对照”脚本可复现。

当前会下载：
- `SmartphoneMeasurements.zip`：pspachos/SmartphoneMeasurements 的 GitHub 仓库快照（main 分支）。

注意：
- 上游仓库可能更新；本脚本默认只做“能复现运行”的下载，不强制固定 commit。
- 如你需要完全可复现（hash 固定），建议：
  1) 把 zip 的 sha256 写进 manifest；
  2) 把下载 URL 固定到某个 commit 的 archive。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ZIP_URL = "https://codeload.github.com/pspachos/SmartphoneMeasurements/zip/refs/heads/main"


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
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 0 and not force:
        return "skip_exists"
    cmd = [
        "curl",
        "-L",
        "--retry",
        "3",
        "--retry-delay",
        "2",
        "-o",
        str(dst),
        url,
    ]
    _run(cmd)
    if not dst.exists() or dst.stat().st_size == 0:
        raise RuntimeError(f"下载完成但文件为空：{dst}")
    return "downloaded"


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
    ap = argparse.ArgumentParser(description="下载 SmartphoneMeasurements.zip（用于 Q2/Q3 观测对照）")
    ap.add_argument("--force", action="store_true", help="强制重新下载")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    dst = root / "SmartphoneMeasurements.zip"
    user_csv = root / "user_behavior_dataset.csv"

    rows: list[dict[str, str]] = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 先把本地已有的 user_behavior_dataset.csv 也写入 manifest，便于追溯。
    if user_csv.exists() and user_csv.stat().st_size > 0:
        rows.append(
            {
                "ts": ts,
                "path": user_csv.name,
                "size_bytes": str(user_csv.stat().st_size),
                "sha256": _sha256(user_csv),
                "source_url": "(见 README.md：GeorgeHanyMilad/Mobile-Usage-Behavior-Analysis)",
                "status": "present",
            }
        )

    try:
        status = _curl_download(ZIP_URL, dst, force=bool(args.force))
        rows.append(
            {
                "ts": ts,
                "path": dst.name,
                "size_bytes": str(dst.stat().st_size),
                "sha256": _sha256(dst),
                "source_url": ZIP_URL,
                "status": status,
            }
        )
        print(f"[ok] {dst.name}: {status}")
    except Exception as e:
        rows.append(
            {
                "ts": ts,
                "path": dst.name,
                "size_bytes": str(dst.stat().st_size) if dst.exists() else "0",
                "sha256": _sha256(dst) if dst.exists() else "",
                "source_url": ZIP_URL,
                "status": "failed",
                "error": str(e),
            }
        )
        print(f"[fail] {e}", file=sys.stderr)

    # 覆盖写入（manifest 很小，且上游 zip 可能变化）
    _write_manifest(root / "manifest.csv", rows)
    print(f"[ok] manifest: {root / 'manifest.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
