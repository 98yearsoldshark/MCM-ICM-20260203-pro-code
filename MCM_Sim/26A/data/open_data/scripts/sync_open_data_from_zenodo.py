#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Zenodo 同步 AndroWatts（open_data）数据（用于 GitHub 版“只提交脚本，不提交大文件”）。

说明：
- 本目录的“大头”通常是：
  - `material/trace_parser/`（perfetto trace + 解析工具）
  - `material/application-android-conso-tel/`（复现实验安卓 app）
- 但主项目实际建模/验证最常用的是：
  - `material/res_test/aggregated.csv`（1000 条聚合指标，体积很小）

如果你准备把仓库提交到 GitHub，推荐策略：
1) 保留 aggregated.csv 与 README（小文件）；删除 trace_parser 与 app（大文件）。
2) 需要时用本脚本从 Zenodo 记录重新拉取（可复现）。

Zenodo 记录：
- Record: 14314943
- DOI: 10.5281/zenodo.14314943

注意：
- 部分网络环境可能无法访问 Zenodo；此时请切换网络/VPN 或在可访问环境下运行。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ZENODO_RECORD_ID = "14314943"
ZENODO_API_URL = f"https://zenodo.org/api/records/{ZENODO_RECORD_ID}"
# 经验上该记录只有一个大压缩包（open_data.zip）。为增强鲁棒性：API 不可用时走直链兜底。
DIRECT_FILE_KEY = "open_data.zip"
DIRECT_FILE_URL = f"https://zenodo.org/records/{ZENODO_RECORD_ID}/files/{DIRECT_FILE_KEY}?download=1"
# 该 md5 来自 Zenodo 文件页展示（用于快速一致性校验/日志记录；不做强制校验也能用）
DIRECT_FILE_CHECKSUM = "md5:4f27acd5e9c10d805ac2a375fc69fe97"


@dataclass(frozen=True)
class FileItem:
    key: str
    size: int | None
    checksum: str | None
    url: str


def _run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"命令失败：{cmd}\n\n输出：\n{p.stdout}")
    return p.stdout


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def _fetch_record_json() -> dict:
    # 这里不用 requests（不保证环境安装），直接用 curl
    txt = _run(["curl", "-L", "-s", ZENODO_API_URL])
    try:
        return json.loads(txt)
    except Exception as e:
        raise RuntimeError(f"解析 Zenodo API JSON 失败：{ZENODO_API_URL}\n错误：{e}\n前 400 字符：\n{txt[:400]}") from e


def _parse_files(rec: dict) -> list[FileItem]:
    files = rec.get("files") or []
    out: list[FileItem] = []
    for f in files:
        key = str(f.get("key") or "")
        links = f.get("links") or {}
        url = str(links.get("download") or links.get("self") or "")
        if not key or not url:
            continue
        size = f.get("size")
        checksum = f.get("checksum")
        out.append(FileItem(key=key, size=int(size) if isinstance(size, (int, float)) else None, checksum=str(checksum) if checksum else None, url=url))
    if not out:
        raise RuntimeError("未解析到 Zenodo files 列表（可能是 API 结构变化或网络返回异常）")
    return out


def _is_archive(p: Path) -> bool:
    s = p.name.lower()
    return s.endswith(".zip") or s.endswith(".tar") or s.endswith(".tar.gz") or s.endswith(".tgz")


def _extract_archive(path: Path, tmp_dir: Path) -> None:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    name = path.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            z.extractall(tmp_dir)
        return
    if name.endswith(".tar") or name.endswith(".tar.gz") or name.endswith(".tgz"):
        with tarfile.open(path) as t:
            t.extractall(tmp_dir)
        return
    raise ValueError(f"不支持的压缩格式：{path}")


def _merge_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name == "__MACOSX":
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def _pick_effective_root(extracted_tmp: Path) -> Path:
    # 常见情况：压缩包内顶层只有一个目录（例如 open_data/ 或 material/）
    kids = [p for p in extracted_tmp.iterdir() if p.name != "__MACOSX"]
    if len(kids) == 1 and kids[0].is_dir():
        return kids[0]
    return extracted_tmp


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
    ap = argparse.ArgumentParser(description="从 Zenodo 同步 open_data（AndroWatts）")
    ap.add_argument("--raw-dir", default="raw", help="下载原始文件保存目录（相对 open_data/）")
    ap.add_argument("--manifest", default="manifest.csv", help="写入 manifest（相对 open_data/）")
    ap.add_argument("--force-download", action="store_true", help="即使文件存在也重新下载")
    ap.add_argument("--no-extract", action="store_true", help="只下载，不解压/合并")
    ap.add_argument(
        "--subset",
        choices=["all", "small"],
        default="all",
        help=(
            "下载子集：\n"
            "- all：下载 Zenodo 记录中的全部文件\n"
            "- small：仅尝试下载包含 aggregated/analysis/accuracy/comparison 的小文件（若记录是单一大 zip，则无法小下载）"
        ),
    )
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parents[1]  # open_data/
    raw_dir = root / str(args.raw_dir)
    manifest_path = root / str(args.manifest)

    # 优先走 API（能拿到完整 file 列表/校验信息）；如果 API 在某些环境不可用，则退化为直链下载。
    try:
        rec = _fetch_record_json()
        files = _parse_files(rec)
    except Exception as e:
        print(f"[warn] 无法访问/解析 Zenodo API，将退化为直链：{e}", file=sys.stderr)
        files = [
            FileItem(
                key=DIRECT_FILE_KEY,
                size=None,
                checksum=DIRECT_FILE_CHECKSUM,
                url=DIRECT_FILE_URL,
            )
        ]

    if args.subset == "small":
        keep_keys = ("aggregated", "analysis", "accuracy", "comparison", "grid", "size")
        files_small = [f for f in files if any(k in f.key.lower() for k in keep_keys)]
        # 若匹配为空，则降级为全量（避免“误删导致无法恢复”）
        files = files_small or files

    rows: list[dict[str, str]] = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for f in files:
        dst = raw_dir / f.key
        status_dl = "n/a"
        status_ex = "n/a"
        try:
            status_dl = _curl_download(f.url, dst, force=bool(args.force_download))
            if not args.no_extract and _is_archive(dst):
                tmp = root / "_tmp_extract"
                if tmp.exists():
                    shutil.rmtree(tmp)
                _extract_archive(dst, tmp)
                eff_root = _pick_effective_root(tmp)
                _merge_tree(eff_root, root)
                shutil.rmtree(tmp, ignore_errors=True)
                status_ex = "merged"

            rows.append(
                {
                    "ts": ts,
                    "key": f.key,
                    "size_bytes": str(dst.stat().st_size) if dst.exists() else "",
                    "sha256": _sha256(dst) if dst.exists() else "",
                    "checksum_zenodo": f.checksum or "",
                    "source_url": f.url,
                    "status_download": status_dl,
                    "status_extract": status_ex,
                }
            )
            print(f"[ok] {f.key}: download={status_dl} extract={status_ex}")
        except Exception as e:
            rows.append(
                {
                    "ts": ts,
                    "key": f.key,
                    "size_bytes": str(dst.stat().st_size) if dst.exists() else "0",
                    "sha256": _sha256(dst) if dst.exists() else "",
                    "checksum_zenodo": f.checksum or "",
                    "source_url": f.url,
                    "status_download": status_dl or "failed",
                    "status_extract": status_ex or "failed",
                    "error": str(e),
                }
            )
            print(f"[fail] {f.key}: {e}", file=sys.stderr)

    _write_manifest(manifest_path, rows)
    print(f"[ok] manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
