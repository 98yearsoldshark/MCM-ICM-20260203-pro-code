#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
隐私/个人信息快速扫描（用于 GitHub 发布前自检）。

默认只扫描「git 已跟踪」文件（即可能被 push 的内容），避免把本地未提交的临时文件也纳入噪声。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class Finding:
    kind: str
    path: str
    line_no: int
    excerpt: str


def _run(cmd: List[str], cwd: Path) -> Tuple[int, str]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return p.returncode, p.stdout


def _repo_root(cwd: Path) -> Path:
    code, out = _run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if code != 0:
        return cwd.resolve()
    return Path(out.strip()).resolve()


def _git_tracked_files(repo: Path) -> List[Path]:
    # 用 -z 避免中文/空格路径问题
    p = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=str(repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if p.returncode != 0:
        return []
    raw = p.stdout.split(b"\x00")
    files: List[Path] = []
    for item in raw:
        if not item:
            continue
        try:
            s = item.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            s = item.decode("utf-8", errors="replace")
        files.append((repo / s).resolve())
    return files


def _iter_text_lines(path: Path, max_bytes: Optional[int]) -> Optional[Iterable[Tuple[int, str]]]:
    try:
        if max_bytes is not None and path.stat().st_size > max_bytes:
            return None
    except OSError:
        return None

    try:
        # 使用二进制读取，快速判定是否包含 NUL（粗判二进制）
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:
        return None

    text = data.decode("utf-8", errors="replace")
    return enumerate(text.splitlines(), start=1)


def scan_files(repo: Path, files: List[Path], max_bytes: Optional[int]) -> List[Finding]:
    # 常见泄漏模式：本机路径、邮箱、手机号、队号字段、token 前缀等
    rules: List[Tuple[str, re.Pattern[str]]] = [
        ("abs_path_macos", re.compile(r"/Users/[^/\s]+/")),
        ("abs_path_linux", re.compile(r"/home/[^/\s]+/")),
        ("abs_path_windows", re.compile(r"(?:[A-Za-z]:\\\\Users\\\\[^\\\\\s]+\\\\|C:/Users/[^/\\s]+/)")),
        ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
        # 避免把 CSV/浮点小数尾数误判成手机号（常见：xxx.10533810864）
        ("phone_cn", re.compile(r"(?<![0-9.])1[3-9]\d{9}(?!\d)")),
        ("team_number_tcn", re.compile(r"\btcn\s*=\s*\d+\b", re.IGNORECASE)),
        ("team_number_text", re.compile(r"Team\s+Number|Team\s+Control\s+Number", re.IGNORECASE)),
        ("token_like", re.compile(r"\b(ghp_|github_pat_|AKIA|AIzaSy|sk-)\w+", re.IGNORECASE)),
    ]

    findings: List[Finding] = []

    for f in files:
        rel = os.path.relpath(f, repo)
        lines = _iter_text_lines(f, max_bytes=max_bytes)
        if lines is None:
            continue

        for line_no, line in lines:
            for kind, pat in rules:
                if pat.search(line):
                    # 只截取一小段，避免把整行隐私全打印出来
                    excerpt = line.strip()
                    if len(excerpt) > 240:
                        excerpt = excerpt[:240] + "…"
                    findings.append(Finding(kind=kind, path=rel, line_no=line_no, excerpt=excerpt))
                    # 同一行命中多个规则也记录（便于定位）
    return findings


def scan_git_history(repo: Path) -> List[str]:
    """
    检查 git 历史里的作者邮箱（最常见的“隐私泄漏点”，文件内容再干净也没用）。
    只做提示，不自动改写历史。
    """
    code, out = _run(["git", "log", "--format=%an <%ae>"], cwd=repo)
    if code != 0:
        return []
    uniq = sorted({line.strip() for line in out.splitlines() if line.strip()})
    suspicious = []
    for entry in uniq:
        m = re.search(r"<([^>]+)>", entry)
        if not m:
            continue
        email = m.group(1)
        # 允许 GitHub noreply；其他邮箱都提示一下（用户自行判断是否需要改写历史）
        if email.endswith("@users.noreply.github.com"):
            continue
        suspicious.append(entry)
    return suspicious


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="隐私/个人信息快速扫描（GitHub 发布前自检）")
    ap.add_argument(
        "--all-files",
        action="store_true",
        help="扫描仓库内所有文件（默认仅扫描 git 已跟踪文件）。",
    )
    ap.add_argument(
        "--max-bytes",
        type=int,
        default=5_000_000,
        help="单文件扫描大小上限（字节）。默认 5MB；设为 0 表示不限制。",
    )
    args = ap.parse_args(argv)

    cwd = Path.cwd()
    repo = _repo_root(cwd)
    max_bytes = None if args.max_bytes == 0 else args.max_bytes

    if args.all_files:
        # all-files 模式：遍历仓库目录，但排除 .git
        files = [p for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts]
    else:
        files = _git_tracked_files(repo)

    findings = scan_files(repo, files, max_bytes=max_bytes)
    history_warn = scan_git_history(repo)

    print(f"[scan] repo={repo}")
    print(f"[scan] files={len(files)} (mode={'all' if args.all_files else 'git-tracked'})")
    print(f"[scan] max_bytes={('no-limit' if max_bytes is None else max_bytes)}")
    print("")

    if history_warn:
        print("[warn] git 历史作者邮箱包含非 noreply（推送到 GitHub 后可被看到）：")
        for e in history_warn:
            print(f"  - {e}")
        print("")

    if not findings:
        print("[ok] 未在已扫描文件中发现明显的隐私模式命中。")
        return 0

    # 统计
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.kind] = counts.get(f.kind, 0) + 1

    print("[hit] 发现可疑命中（不一定都是真泄漏，请人工复核）：")
    for k in sorted(counts.keys()):
        print(f"  - {k}: {counts[k]}")
    print("")

    # 输出前 N 条（避免刷屏）
    max_show = 200
    for i, f in enumerate(findings[:max_show], start=1):
        print(f"{i:03d}. {f.kind} {f.path}:{f.line_no} {f.excerpt}")
    if len(findings) > max_show:
        print(f"... 还有 {len(findings) - max_show} 条未显示（可调整脚本的 max_show 或先缩小范围）")

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
