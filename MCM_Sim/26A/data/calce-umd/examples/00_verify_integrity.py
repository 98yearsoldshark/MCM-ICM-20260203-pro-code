#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CALCE-UMD 数据完整性校验（以 manifest.csv 为准）。

做什么：
- 检查 manifest.csv 是否可读、条目是否唯一
- 检查 raw/ 下 zip 是否存在、大小是否一致、zip 是否可打开
- （可选）计算 sha256 并与 manifest.csv 对比
- 检查 extracted/ 下对应解压目录是否存在且非空

用法：
  python3 .../examples/00_verify_integrity.py
  python3 .../examples/00_verify_integrity.py --no-sha
  python3 .../examples/00_verify_integrity.py --report MCM_Sim/26A/data/calce-umd/INTEGRITY_REPORT.md
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import zipfile


@dataclass(frozen=True)
class Issue:
    kind: str
    path: str
    detail: str


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


def _write_report(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="校验 CALCE-UMD 数据完整性（对照 manifest.csv）")
    parser.add_argument("--no-sha", action="store_true", help="跳过 sha256 计算（更快）")
    parser.add_argument("--no-zip", action="store_true", help="跳过 zip 可读性检查（不推荐）")
    parser.add_argument("--no-extracted", action="store_true", help="跳过 extracted/ 解压目录检查")
    parser.add_argument(
        "--report",
        type=str,
        default="",
        help="输出 Markdown 报告（例如：MCM_Sim/26A/data/calce-umd/INTEGRITY_REPORT.md）",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "manifest.csv"
    raw_dir = root / "raw"
    extracted_dir = root / "extracted"

    issues: List[Issue] = []

    if not manifest_path.exists():
        print(f"[ERROR] 找不到 manifest.csv：{manifest_path}", file=sys.stderr)
        return 2

    rows = list(csv.DictReader(manifest_path.open(encoding="utf-8")))
    if not rows:
        print(f"[ERROR] manifest.csv 为空：{manifest_path}", file=sys.stderr)
        return 2

    raw_paths = [r.get("raw_path", "").strip() for r in rows]
    if any(not p for p in raw_paths):
        issues.append(Issue("manifest", "manifest.csv", "存在空 raw_path"))
    if len(set(raw_paths)) != len(raw_paths):
        issues.append(Issue("manifest", "manifest.csv", "raw_path 不唯一（存在重复）"))

    checked_sha = 0
    for r in rows:
        rel = Path(r["raw_path"])
        raw_path = raw_dir / rel

        # raw file existence
        if not raw_path.exists():
            issues.append(Issue("missing_raw", rel.as_posix(), "raw 文件不存在"))
            continue

        # size check
        try:
            expected_size = int(r.get("size_bytes", "0") or "0")
        except ValueError:
            expected_size = 0
        actual_size = raw_path.stat().st_size
        if expected_size and actual_size != expected_size:
            issues.append(
                Issue(
                    "size_mismatch",
                    rel.as_posix(),
                    f"size_bytes 不一致：manifest={expected_size} actual={actual_size}",
                )
            )

        # zip readability
        if not args.no_zip and raw_path.suffix.lower() == ".zip":
            if not _is_readable_zip(raw_path):
                issues.append(Issue("bad_zip", rel.as_posix(), "zip 无法打开/损坏"))
                continue

        # sha check
        if not args.no_sha:
            digest = _sha256(raw_path)
            checked_sha += 1
            if digest != r.get("sha256", ""):
                issues.append(Issue("sha_mismatch", rel.as_posix(), "sha256 与 manifest 不一致"))

        # extracted check
        if not args.no_extracted and raw_path.suffix.lower() == ".zip":
            extracted_path = extracted_dir / rel.with_suffix("")
            if not extracted_path.exists():
                issues.append(Issue("missing_extracted", extracted_path.as_posix(), "解压目录不存在"))
            else:
                try:
                    next(extracted_path.iterdir())
                except StopIteration:
                    issues.append(Issue("empty_extracted", extracted_path.as_posix(), "解压目录为空"))

    ok = len(issues) == 0
    print("[OK]" if ok else "[FAIL]", "entries=", len(rows), "sha_checked=", checked_sha)

    if issues:
        for it in issues[:50]:
            print(f"- {it.kind}: {it.path}  {it.detail}", file=sys.stderr)
        if len(issues) > 50:
            print(f"... 还有 {len(issues) - 50} 条问题未显示", file=sys.stderr)

    if args.report:
        report_in = Path(args.report)
        # 约定：
        # - 仅给文件名（无目录）时，默认写到数据根目录（calce-umd/）下
        # - 给出带目录的相对路径时，按当前工作目录解析（更符合直觉）
        if report_in.is_absolute():
            report_path = report_in
        elif len(report_in.parts) == 1:
            report_path = (root / report_in).resolve()
        else:
            report_path = (Path.cwd() / report_in).resolve()
        lines: List[str] = []
        lines.append("# CALCE-UMD 数据完整性报告\n\n")
        lines.append(f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}\n")
        lines.append(f"- 数据根目录：`{root}`\n")
        lines.append(f"- manifest 条目数：{len(rows)}\n")
        lines.append(f"- raw zip 数量：{len(list(raw_dir.rglob('*.zip')))}\n")
        lines.append(f"- extracted 目录检查：{'跳过' if args.no_extracted else '已检查'}\n")
        lines.append(f"- sha256 检查：{'跳过' if args.no_sha else f'已检查 {checked_sha} 个文件'}\n")
        lines.append(f"- 结果：{'PASS' if ok else 'FAIL'}\n\n")

        if issues:
            lines.append("## 问题列表\n\n")
            for it in issues:
                lines.append(f"- `{it.kind}` `{it.path}`：{it.detail}\n")
        else:
            lines.append("## 结论\n\n- 未发现缺失或不一致。\n")

        _write_report(report_path, lines)
        print(f"[OK] report: {report_path}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
