#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 Battery Intelligence Lab 的 “Data and code” 页面生成可直接下载清单。

输出（在 Battery-Intelligence-Lab/ 目录下）：
- download_list.md      人类可读的下载清单（含直链/说明）
- sources/urls.txt      直链列表（每行一个 URL，便于批量下载）
- sources/data-and-code.md         页面抓取快照（markdown 形式）
- sources/ora_*.html               ORA(牛津)数据集页面快照
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"


def _http_get(url: str, *, timeout: int = 60, headers: Dict[str, str] | None = None) -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": "codex-cli (educational use)",
            **(headers or {}),
        },
        method="GET",
    )
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read()


def _http_get_text(url: str, *, timeout: int = 60, headers: Dict[str, str] | None = None) -> str:
    return _http_get(url, timeout=timeout, headers=headers).decode("utf-8", errors="replace")


class OraFileLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_target_a = False
        self._current_href: str | None = None
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
class GitHubRepo:
    name: str
    url: str


@dataclass(frozen=True)
class OraDataset:
    name: str
    object_url: str
    sources_slug: str  # for sources filename


def _github_default_branch(repo_url: str) -> str:
    # repo_url like: https://github.com/owner/repo
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Bad repo url: {repo_url}")
    owner = parts[-2]
    repo = parts[-1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    data = json.loads(_http_get_text(api_url, headers={"Accept": "application/vnd.github+json"}))
    return str(data.get("default_branch") or "main")


def main() -> int:
    SOURCES.mkdir(parents=True, exist_ok=True)

    # 1) Snapshot the BIL page (GitHub Pages might be blocked on some networks; use jina.ai proxy)
    bil_proxy_url = "https://r.jina.ai/http://battery-intelligence-lab.github.io/data-and-code/"
    bil_md = _http_get_text(bil_proxy_url)
    (SOURCES / "data-and-code.md").write_text(bil_md, encoding="utf-8")

    # 2) Core resources listed on the page
    repos = [
        GitHubRepo("PyBOP", "https://github.com/pybop-team/PyBOP"),
        GitHubRepo("SLIDE", "https://github.com/davidhowey/SLIDE"),
        GitHubRepo("Spectral_li-ion_SPM", "https://github.com/davidhowey/Spectral_li-ion_SPM"),
        GitHubRepo("Supercapacitor-Model", "https://github.com/scro2542/Supercapacitor-Model"),
        GitHubRepo("EKF-Battery-Impedance-Temperature", "https://github.com/robert-richardson/EKF-Battery-Impedance-Temperature"),
    ]

    datasets = [
        OraDataset(
            "Oxford Battery Degradation Dataset 1",
            "https://ora.ox.ac.uk/objects/uuid:03ba4b01-cfed-46d3-9b1a-7d4a7bdf6fac",
            "ora_oxford_battery_degradation_dataset_1",
        ),
        OraDataset(
            "Oxford Energy trading battery degradation dataset",
            "https://ora.ox.ac.uk/objects/uuid:9aae61af-2949-49f1-8ad5-6aea448979e5",
            "ora_energy_trading_battery_degradation_dataset",
        ),
        OraDataset(
            "Oxford Path dependence battery degradation dataset",
            "https://ora.ox.ac.uk/objects/uuid:de62b5d2-6154-426d-bcbb-30253ddb7d1e",
            "ora_path_dependence_battery_degradation_dataset",
        ),
    ]

    # 3) Fetch ORA pages + parse direct file links
    ora_files: Dict[str, List[Tuple[str, str]]] = {}
    for ds in datasets:
        html = _http_get_text(ds.object_url)
        (SOURCES / f"{ds.sources_slug}.html").write_text(html, encoding="utf-8")

        parser = OraFileLinkParser()
        parser.feed(html)
        # Normalize to absolute URLs
        files = [(name, urljoin(ds.object_url, href)) for name, href in parser.links]
        ora_files[ds.name] = files

    # 4) GitHub direct zip URLs (default branch)
    github_zip: Dict[str, str] = {}
    for r in repos:
        try:
            branch = _github_default_branch(r.url)
        except Exception:  # noqa: BLE001
            branch = "main"
        github_zip[r.name] = f"{r.url}/archive/refs/heads/{branch}.zip"

    # 5) Write urls.txt (direct download links)
    urls: List[str] = []
    urls.extend(github_zip.values())
    for files in ora_files.values():
        urls.extend([u for _, u in files])
    (SOURCES / "urls.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")

    # 6) Write download_list.md (human readable)
    out_lines: List[str] = []
    out_lines.append("# Battery Intelligence Lab（Data and code）下载清单\n")
    out_lines.append(f"生成时间：{datetime.now().isoformat(timespec='seconds')}\n\n")
    out_lines.append("说明：\n")
    out_lines.append("- 本清单依据 Battery Intelligence Lab 页面 “Data and code” 整理。\n")
    out_lines.append("- 为便于自动化下载：直链列表见 `sources/urls.txt`。\n")
    out_lines.append("- 外部站点（PyBaMM / Battery Archive / CALCE / NASA）不在此处镜像下载，仅保留链接与本仓库内对应目录指引。\n\n")

    out_lines.append("## Models（代码）\n")
    for r in repos:
        out_lines.append(f"- {r.name}\n")
        out_lines.append(f"  - 仓库：{r.url}\n")
        out_lines.append(f"  - 直链(zip)：{github_zip[r.name]}\n")
    out_lines.append("\n")

    out_lines.append("## Data（数据集：Oxford ORA）\n")
    for ds in datasets:
        out_lines.append(f"- {ds.name}\n")
        out_lines.append(f"  - 主页：{ds.object_url}\n")
        files = ora_files.get(ds.name, [])
        if not files:
            out_lines.append("  - 文件：未解析到（请手动打开主页确认）\n")
        else:
            out_lines.append("  - 文件（直链）：\n")
            for name, url in files:
                out_lines.append(f"    - {name}  {url}\n")
    out_lines.append("\n")

    out_lines.append("## External（外部资源）\n")
    out_lines.append("- PyBaMM: https://www.pybamm.org/\n")
    out_lines.append("- Battery Archive: https://batteryarchive.org/ （本仓库目录：`MCM_Sim/26A/data/Battery-Archive/`）\n")
    out_lines.append("- CALCE datasets: http://www.calce.umd.edu/batteries/data.htm （本仓库目录：`MCM_Sim/26A/data/calce-umd/`）\n")
    out_lines.append("- NASA Prognostics Battery dataset: https://ti.arc.nasa.gov/tech/dash/groups/pcoe/prognostic-data-repository/\n")
    out_lines.append("\n")

    (ROOT / "download_list.md").write_text("".join(out_lines), encoding="utf-8")

    print(f"[OK] wrote: {ROOT / 'download_list.md'}")
    print(f"[OK] wrote: {SOURCES / 'urls.txt'}")
    print(f"[OK] wrote: {SOURCES / 'data-and-code.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

