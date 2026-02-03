#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步/校验 UMD CALCE 电池公开数据到本目录（calce-umd/）。

输入：
- sources/urls.txt（每行一个可直接下载的 URL）

输出：
- raw/           原始 zip（按本仓库约定的分类目录存放）
- extracted/      解压后的数据（每个 zip 解压到同名文件夹）
- download_list.md  下载直链清单（按分类分组）
- manifest.csv      文件清单（raw_path,size_bytes,sha256,source_url）

说明：
- 会对 URL 中的 %20 等进行 decode（本地文件名更易读）。
- 下载使用 curl（自动重试）；已存在且可正常打开的 zip 会跳过。
"""

from __future__ import annotations

import csv
import hashlib
import subprocess
import sys
import urllib.parse
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class Item:
    url: str
    raw_rel_path: Path  # relative to raw/


def _read_urls(path: Path) -> List[str]:
    urls: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        urls.append(s)
    return urls


def _raw_rel_path_for_url(url: str) -> Path:
    p = urllib.parse.urlparse(url).path
    filename = urllib.parse.unquote(Path(p).name)

    if "/accelerated/" in p:
        return Path("accelerated") / filename
    if "/anomaly/" in p:
        return Path("anomaly") / filename
    if "/pln/" in p:
        # 在本仓库中统一归类为 storage
        return Path("storage") / filename
    if "/pl/" in p:
        return Path("pl") / filename

    # battery-data 主页的顶层 zip（按前缀分类）
    if filename.startswith("A123_"):
        return Path("battery-data/A123") / filename
    if filename.startswith("CS2_"):
        return Path("battery-data/CS2") / filename
    if filename.startswith("CX2_"):
        return Path("battery-data/CX2") / filename
    if filename.startswith("SP"):
        return Path("battery-data/SP") / filename

    # 兜底：未知文件名放到 misc
    return Path("misc") / filename


def _group_for_raw_rel_path(rel: Path) -> str:
    parts = rel.parts
    if not parts:
        return "misc"
    if parts[0] == "battery-data" and len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return parts[0]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_readable_zip(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            zf.namelist()[:1]
        return True
    except Exception:
        return False


def _curl_download(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "curl",
        "-L",
        "--fail",
        "--retry",
        "3",
        "--retry-delay",
        "2",
        "-o",
        str(out_path),
        url,
    ]
    subprocess.run(cmd, check=True)


def _safe_extract_zip(zip_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir_resolved = out_dir.resolve()

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Basic ZipSlip protection
        for info in zf.infolist():
            target = (out_dir / info.filename).resolve()
            if out_dir_resolved not in target.parents and target != out_dir_resolved:
                raise ValueError(f"Unsafe zip member path: {info.filename}")
        zf.extractall(out_dir)


def _write_download_list(items: List[Item], out_path: Path) -> None:
    groups: Dict[str, List[Item]] = {}
    for it in items:
        g = _group_for_raw_rel_path(it.raw_rel_path)
        groups.setdefault(g, []).append(it)

    # A little nicer ordering for common groups
    preferred = [
        "battery-data/A123",
        "battery-data/CS2",
        "battery-data/CX2",
        "battery-data/SP",
        "pl",
        "storage",
        "accelerated",
        "anomaly",
        "misc",
    ]
    ordered_groups = [g for g in preferred if g in groups] + [
        g for g in sorted(groups.keys()) if g not in preferred
    ]

    lines: List[str] = []
    lines.append("# CALCE-UMD 直接下载链接清单\n")
    lines.append(
        "说明：本清单来自 CALCE (University of Maryland) 电池数据页面的公开直链；"
        "若原站链接有变动，请以 `sources/` 中的页面为准。\n"
    )
    lines.append(f"生成时间：{datetime.now().isoformat(timespec='seconds')}\n\n")

    for g in ordered_groups:
        lines.append(f"## {g}\n")
        for it in sorted(groups[g], key=lambda x: x.raw_rel_path.as_posix().lower()):
            lines.append(f"- `{it.raw_rel_path.as_posix()}`  {it.url}\n")
        lines.append("\n")

    out_path.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    urls_path = root / "sources" / "urls.txt"
    raw_dir = root / "raw"
    extracted_dir = root / "extracted"
    manifest_path = root / "manifest.csv"
    download_list_path = root / "download_list.md"

    if not urls_path.exists():
        print(f"[ERROR] urls 文件不存在: {urls_path}", file=sys.stderr)
        return 2

    urls = _read_urls(urls_path)
    if not urls:
        print(f"[ERROR] urls 为空: {urls_path}", file=sys.stderr)
        return 2

    items: List[Item] = [Item(url=u, raw_rel_path=_raw_rel_path_for_url(u)) for u in urls]

    # Keep output stable
    items = sorted(items, key=lambda x: x.raw_rel_path.as_posix().lower())

    _write_download_list(items, download_list_path)

    manifest_rows: List[Dict[str, str]] = []
    for it in items:
        raw_path = raw_dir / it.raw_rel_path
        extracted_path = extracted_dir / it.raw_rel_path.with_suffix("")  # drop .zip

        # Download
        if raw_path.exists() and raw_path.stat().st_size > 0 and _is_readable_zip(raw_path):
            pass
        else:
            if raw_path.exists():
                raw_path.unlink()
            try:
                _curl_download(it.url, raw_path)
            except subprocess.CalledProcessError as e:
                print(f"[WARN] 下载失败({e.returncode}): {it.url}", file=sys.stderr)
                continue

        # Extract
        if raw_path.suffix.lower() == ".zip":
            # Skip if already extracted and non-empty
            if not (extracted_path.exists() and any(extracted_path.iterdir())):
                try:
                    _safe_extract_zip(raw_path, extracted_path)
                except Exception as e:  # noqa: BLE001
                    print(f"[WARN] 解压失败({type(e).__name__}): {raw_path}", file=sys.stderr)

        manifest_rows.append(
            {
                "raw_path": it.raw_rel_path.as_posix(),
                "size_bytes": str(raw_path.stat().st_size),
                "sha256": _sha256(raw_path),
                "source_url": it.url,
            }
        )

    with manifest_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["raw_path", "size_bytes", "sha256", "source_url"],
        )
        w.writeheader()
        w.writerows(manifest_rows)

    print(f"[OK] download_list: {download_list_path}")
    print(f"[OK] manifest:      {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
