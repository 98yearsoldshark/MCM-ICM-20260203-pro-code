#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载并整理 Battery Intelligence Lab “Data and code” 页面中列出的资源（Models + Data）。

输入：
- sources/urls.txt           直链列表（每行一个 URL）
- sources/ora_*.html         ORA 页面快照（用于把 ORA 文件 URL 映射回“人类文件名”）

输出：
- raw/                       原始下载文件（按 models/ 与 data/ 分类）
- extracted/                 解压后的内容（仅对 .zip 做解压）
- manifest.csv               下载/解压清单（含 sha256、大小、状态、来源 URL）

注意：
- 本脚本不会镜像 “Links to external sites” 中的外部站点（PyBaMM / Battery Archive / CALCE / NASA）。
  这些仅在 download_list.md 里保留链接或指向仓库内其他目录。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"
RAW = ROOT / "raw"
EXTRACTED = ROOT / "extracted"
MANIFEST = ROOT / "manifest.csv"


class OraFileLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_target_a = False
        self._current_href: Optional[str] = None
        self.links: List[Tuple[str, str]] = []  # (filename, href)

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attr = {k.lower(): (v or "") for k, v in attrs}
        cls = attr.get("class", "")
        href = attr.get("href", "")
        if "download-full-text-link" in cls and href:
            self._in_target_a = True
            self._current_href = href

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a":
            self._in_target_a = False
            self._current_href = None

    def handle_data(self, data: str) -> None:
        if not self._in_target_a or not self._current_href:
            return
        name = data.strip()
        if not name:
            return
        self.links.append((name, self._current_href))


@dataclass(frozen=True)
class Item:
    url: str
    kind: str  # "model" | "data"
    dataset: str  # dataset slug or repo name
    filename: str

    @property
    def raw_rel_path(self) -> Path:
        if self.kind == "model":
            return Path("models") / self.dataset / self.filename
        return Path("data") / self.dataset / self.filename

    @property
    def extracted_rel_dir(self) -> Optional[Path]:
        if not self.filename.lower().endswith(".zip"):
            return None
        base = Path(self.filename).with_suffix("").name
        if self.kind == "model":
            return Path("models") / self.dataset / base
        return Path("data") / self.dataset / base


def _read_urls(path: Path) -> List[str]:
    urls: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        urls.append(s)
    return urls


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _curl_download(url: str, out_path: Path) -> str:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # -L: follow redirects
    # --fail: non-2xx => error
    # --continue-at -: resume
    # --http1.1: GitHub 上 curl 的 HTTP/2 偶发失败较多，强制 http1.1 更稳
    cmd = [
        "curl",
        "-L",
        "--fail",
        "--retry",
        "5",
        "--retry-all-errors",
        "--retry-delay",
        "2",
        "--continue-at",
        "-",
        "--http1.1" if "github.com" in url else "--http2",
        "-o",
        str(out_path),
        url,
    ]
    # Remove the protocol selector if we injected a placeholder.
    cmd = [c for c in cmd if c]
    subprocess.run(cmd, check=True)
    return "downloaded"


def _safe_extract_zip(zip_path: Path, out_dir: Path) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    marker = out_dir / ".extracted.ok"
    if marker.exists():
        return "skip"
    # If already extracted by a previous attempt, don't duplicate work.
    if any(out_dir.iterdir()):
        return "skip_nonempty"

    out_dir_resolved = out_dir.resolve()
    with zipfile.ZipFile(zip_path, "r") as zf:
        # ZipSlip protection
        for info in zf.infolist():
            target = (out_dir / info.filename).resolve()
            if out_dir_resolved not in target.parents and target != out_dir_resolved:
                raise ValueError(f"Unsafe zip member path: {info.filename}")
        zf.extractall(out_dir)

    marker.write_text(
        f"extracted_at={datetime.now().isoformat(timespec='seconds')}\nfrom_zip={zip_path.name}\n",
        encoding="utf-8",
    )
    return "extracted"


def _disk_free_bytes(path: Path) -> int:
    usage = os.statvfs(str(path))
    return int(usage.f_bavail) * int(usage.f_frsize)


def _parse_ora_name_map() -> Dict[str, Tuple[str, str]]:
    """
    Return: {url -> (dataset_slug, filename)}
    """
    mapping: Dict[str, Tuple[str, str]] = {}

    datasets = [
        (
            "oxford_battery_degradation_dataset_1",
            SOURCES / "ora_oxford_battery_degradation_dataset_1.html",
            "https://ora.ox.ac.uk/",
        ),
        (
            "energy_trading_battery_degradation_dataset",
            SOURCES / "ora_energy_trading_battery_degradation_dataset.html",
            "https://ora.ox.ac.uk/",
        ),
        (
            "path_dependence_battery_degradation_dataset",
            SOURCES / "ora_path_dependence_battery_degradation_dataset.html",
            "https://ora.ox.ac.uk/",
        ),
    ]

    for slug, html_path, base in datasets:
        if not html_path.exists():
            continue
        html = html_path.read_text(encoding="utf-8", errors="replace")
        parser = OraFileLinkParser()
        parser.feed(html)
        for name, href in parser.links:
            abs_url = urljoin(base, href)
            mapping[abs_url] = (slug, name)

    return mapping


def _parse_github_zip(url: str) -> Tuple[str, str]:
    """
    Return (repo, filename) for a GitHub archive URL.
    Example:
      https://github.com/pybop-team/PyBOP/archive/refs/heads/develop.zip
      -> ("PyBOP", "PyBOP__develop.zip")
    """
    p = urlparse(url)
    parts = [x for x in p.path.split("/") if x]
    # owner/repo/archive/refs/heads/<branch>.zip
    if len(parts) >= 7 and parts[2] == "archive" and parts[3] == "refs" and parts[4] == "heads":
        repo = parts[1]
        branch_zip = parts[6]
        branch = Path(branch_zip).stem
        return repo, f"{repo}__{branch}.zip"
    # fallback
    repo = parts[1] if len(parts) >= 2 else "github"
    filename = Path(parts[-1]).name or "download.zip"
    return repo, filename


def _build_items(urls: Iterable[str]) -> List[Item]:
    ora_map = _parse_ora_name_map()

    items: List[Item] = []
    for url in urls:
        if "github.com" in url and "/archive/refs/heads/" in url and url.endswith(".zip"):
            repo, fname = _parse_github_zip(url)
            items.append(Item(url=url, kind="model", dataset=repo, filename=fname))
            continue

        if url.startswith("https://ora.ox.ac.uk/"):
            if url in ora_map:
                slug, name = ora_map[url]
                items.append(Item(url=url, kind="data", dataset=slug, filename=name))
            else:
                # Unknown ORA link (page structure changed?) -> keep id as filename
                fid = url.rstrip("/").split("/")[-1]
                items.append(Item(url=url, kind="data", dataset="ora_unknown", filename=fid))
            continue

        # Fallback: store by hostname + basename
        host = urlparse(url).netloc.replace(":", "_") or "unknown"
        name = Path(urlparse(url).path).name or "download"
        items.append(Item(url=url, kind="data", dataset=host, filename=name))

    # stable order: download models first (typically smaller), then data.
    def _key(it: Item) -> Tuple[int, str]:
        kind_order = 0 if it.kind == "model" else 1
        return kind_order, it.raw_rel_path.as_posix().lower()

    return sorted(items, key=_key)


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync Battery Intelligence Lab assets (models + ORA data).")
    ap.add_argument(
        "--extract-data-zips",
        action="store_true",
        help="解压 data/*.zip（可能占用大量磁盘；默认关闭）",
    )
    args = ap.parse_args()

    urls_path = SOURCES / "urls.txt"
    if not urls_path.exists():
        print(f"[ERROR] 缺少: {urls_path}", file=sys.stderr)
        return 2

    urls = _read_urls(urls_path)
    if not urls:
        print(f"[ERROR] urls.txt 为空: {urls_path}", file=sys.stderr)
        return 2

    items = _build_items(urls)

    RAW.mkdir(parents=True, exist_ok=True)
    EXTRACTED.mkdir(parents=True, exist_ok=True)

    # Write manifest incrementally to avoid losing progress if the run is interrupted.
    with MANIFEST.open("w", encoding="utf-8", newline="") as mf:
        writer = csv.DictWriter(
            mf,
            fieldnames=[
                "kind",
                "dataset",
                "filename",
                "raw_path",
                "extracted_dir",
                "size_bytes",
                "sha256",
                "status_download",
                "status_extract",
                "url",
            ],
        )
        writer.writeheader()

        rows: List[Dict[str, str]] = []
        for it in items:
            raw_path = RAW / it.raw_rel_path

            # Decide extraction policy:
            # - Always extract model zips (code repos).
            # - Only extract data zips when explicitly requested.
            extracted_dir: Optional[Path] = None
            if it.extracted_rel_dir is not None:
                if it.kind == "model" or args.extract_data_zips:
                    extracted_dir = EXTRACTED / it.extracted_rel_dir
                else:
                    extracted_dir = None

            status_download = ""
            status_extract = ""
            sha = ""
            size = ""

            # Safeguard: keep some free space before starting a new download.
            free_before = _disk_free_bytes(ROOT)
            if free_before < 1024 * 1024 * 1024 and not raw_path.exists():
                status_download = "skipped_low_disk"
                status_extract = "n/a"
            else:
                if raw_path.exists() and raw_path.stat().st_size > 0:
                    status_download = "skip"
                else:
                    try:
                        status_download = _curl_download(it.url, raw_path)
                    except subprocess.CalledProcessError as e:
                        status_download = f"failed({e.returncode})"
                        status_extract = "n/a"

            if raw_path.exists():
                try:
                    size = str(raw_path.stat().st_size)
                except Exception:  # noqa: BLE001
                    size = ""
                try:
                    sha = _sha256(raw_path)
                except Exception as e:  # noqa: BLE001
                    sha = f"failed({type(e).__name__})"

            if extracted_dir is not None:
                if raw_path.exists() and raw_path.suffix.lower() == ".zip":
                    try:
                        status_extract = _safe_extract_zip(raw_path, extracted_dir)
                    except Exception as e:  # noqa: BLE001
                        status_extract = f"failed({type(e).__name__})"
                else:
                    status_extract = "n/a"
            else:
                status_extract = "n/a"

            row = {
                "kind": it.kind,
                "dataset": it.dataset,
                "filename": it.filename,
                "raw_path": it.raw_rel_path.as_posix(),
                "extracted_dir": it.extracted_rel_dir.as_posix() if extracted_dir else "",
                "size_bytes": size,
                "sha256": sha,
                "status_download": status_download,
                "status_extract": status_extract,
                "url": it.url,
            }
            rows.append(row)
            writer.writerow(row)
            mf.flush()
            os.fsync(mf.fileno())

    # Basic verification: ensure every URL has a corresponding local file (unless skipped/failed)
    missing: List[str] = []
    failed: List[str] = []
    for r in rows:
        st = r["status_download"]
        if st.startswith("failed"):
            failed.append(r["url"])
            continue
        if st.startswith("skipped"):
            continue
        p = RAW / r["raw_path"]
        if not p.exists() or p.stat().st_size == 0:
            missing.append(r["url"])

    print(f"[OK] manifest: {MANIFEST}")
    if failed:
        print(f"[WARN] 下载失败: {len(failed)} 个（请重试或手动下载）", file=sys.stderr)
        for u in failed[:50]:
            print(f"  - {u}", file=sys.stderr)
        return 1
    if missing:
        print(f"[WARN] 缺失下载文件: {len(missing)} 个（见 manifest.csv / 终端输出）", file=sys.stderr)
        for u in missing[:50]:
            print(f"  - {u}", file=sys.stderr)
        return 1

    print("[OK] 下载文件齐全（未计入 skipped/failed 项）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
