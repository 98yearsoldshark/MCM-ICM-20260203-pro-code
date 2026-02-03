#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载并整理 BatteryArchive.org (Redash 公共仪表板) 数据到本目录：

- sources/   BatteryArchive.org 页面快照（用于追溯 iframe 的 dashboard token）
- raw/       dashboard 元数据（api/dashboards/public/<token>）
- extracted/ 导出的 CSV 数据（按“循环测试 / 破坏测试”与查询名称分目录）

输出文件：
- download_list.md  可直接下载的清单（含接口与脚本用法）
- manifest.csv      每个导出文件的来源与统计信息（行数/大小/sha256/状态）

说明：
- BatteryArchive 的公开页面通过 iframe 嵌入 Redash 仪表板；本脚本会从页面中自动提取 token，
  并进一步从“Cell List”的 Selection Table 中解析到“Data”仪表板 token。
- 数据通过 Redash API 获取：POST /api/queries/<id>/results?api_key=<dashboard_token>
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


BATTERYARCHIVE_SITE = "https://www.batteryarchive.org"
BATTERYARCHIVE_DB = "https://database.batteryarchive.org"


@dataclass(frozen=True)
class QuerySpec:
    dashboard_token: str
    query_id: int
    query_name: str
    parameters_template: Dict[str, Any]
    out_dir: Path  # under extracted/
    category: str  # cycling|disruptive


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "query"


def _encode_cell_id(cell_id: str) -> str:
    # Keep alnum/_.-~ readable; encode '/', spaces etc.
    return urllib.parse.quote(cell_id, safe="~_.-")


def _curl_get(url: str) -> bytes:
    cmd = [
        "curl",
        "-L",
        "-sS",
        "--fail",
        "--retry",
        "3",
        "--retry-delay",
        "2",
        url,
    ]
    p = subprocess.run(cmd, check=False, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"GET failed ({p.returncode}): {url}\n{p.stderr.decode('utf-8', 'ignore')}")
    return p.stdout


def _curl_download(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "curl",
        "-L",
        "-sS",
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


def _curl_post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False)
    cmd = [
        "curl",
        "-sS",
        "-L",
        "--fail",
        "--retry",
        "3",
        "--retry-delay",
        "2",
        "-X",
        "POST",
        url,
        "-H",
        "Content-Type: application/json",
        "-d",
        body,
    ]
    p = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"POST failed ({p.returncode}): {url}\n{p.stderr}")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON response from: {url}\n{p.stdout[:500]}") from e


def _extract_first_dashboard_token(html: str) -> Optional[str]:
    m = re.search(r"https://database\.batteryarchive\.org/public/dashboards/([A-Za-z0-9]+)", html)
    return m.group(1) if m else None


def _extract_public_dashboard_token_from_link(template: str) -> Optional[str]:
    # Examples:
    #   public/dashboards/<token>?org_slug=default&p_cell_id={{ @ }}
    #   https://database.batteryarchive.org/public/dashboards/<token>?...
    m = re.search(r"(?:^|/)public/dashboards/([A-Za-z0-9]+)", template)
    if m:
        return m.group(1)
    m = re.search(r"https://database\.batteryarchive\.org/public/dashboards/([A-Za-z0-9]+)", template)
    return m.group(1) if m else None


def _dashboard_public_api(token: str) -> str:
    return f"{BATTERYARCHIVE_DB}/api/dashboards/public/{token}"


def _query_results_api(query_id: int, api_key: str) -> str:
    return f"{BATTERYARCHIVE_DB}/api/queries/{query_id}/results?api_key={api_key}"


def _write_csv(rows: List[Dict[str, Any]], columns: List[str], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in columns})
    tmp_path.replace(out_path)


def _pack_dir_to_tar_gz(src_dir: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = archive_path.with_suffix(archive_path.suffix + ".tmp")
    with tarfile.open(tmp_path, "w:gz") as tf:
        tf.add(src_dir, arcname=src_dir.name)
    tmp_path.replace(archive_path)


def _count_csv_in_tar_gz(archive_path: Path) -> int:
    try:
        with tarfile.open(archive_path, "r:gz") as tf:
            n = 0
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if not m.name.endswith(".csv"):
                    continue
                # macOS BSD tar 可能会写入 AppleDouble 元数据条目（以 "._" 开头），这里忽略它们
                if Path(m.name).name.startswith("._"):
                    continue
                n += 1
            return n
    except Exception:  # noqa: BLE001
        return 0


def _query_to_rows(resp: Dict[str, Any]) -> Tuple[List[str], List[Dict[str, Any]], str]:
    if "query_result" not in resp:
        msg = resp.get("message") or resp.get("job", {}).get("error") or "unknown error"
        raise RuntimeError(msg)
    data = resp["query_result"]["data"]
    cols = [c["name"] for c in data.get("columns", [])]
    rows = data.get("rows", [])
    retrieved_at = data.get("retrieved_at") or ""
    return cols, rows, retrieved_at


def _find_selection_table_widget(dashboard: Dict[str, Any]) -> Dict[str, Any]:
    for w in dashboard.get("widgets", []):
        vis = w.get("visualization") or {}
        if vis.get("type") == "SELECTION_TABLE":
            return w
    raise RuntimeError("未找到 Selection Table 组件（SELECTION_TABLE）。")


def _unique_queries_from_dashboard(dashboard: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for w in dashboard.get("widgets", []):
        vis = w.get("visualization")
        if not vis:
            continue
        q = vis.get("query")
        if not q or "id" not in q:
            continue
        out[q["id"]] = q
    return out


def _params_from_query_options(query_obj: Dict[str, Any]) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    for p in (query_obj.get("options", {}) or {}).get("parameters", []) or []:
        name = p.get("name")
        if not name:
            continue
        params[name] = p.get("value")
    return params


def _write_download_list(
    out_path: Path,
    cycle_list_token: str,
    cycle_data_token: str,
    disruptive_list_token: str,
    disruptive_data_token: str,
    cycle_list_query: Dict[str, Any],
    disruptive_list_query: Dict[str, Any],
    cycle_data_queries: Dict[int, Dict[str, Any]],
    disruptive_data_queries: Dict[int, Dict[str, Any]],
) -> None:
    lines: List[str] = []
    lines.append("# BatteryArchive.org 可直接下载清单（Redash 公共接口）\n\n")
    lines.append("本目录数据通过 BatteryArchive 的公开 Redash 仪表板导出。\n\n")
    lines.append(f"生成时间：{_now_iso()}\n\n")
    lines.append("## 一键下载（推荐）\n\n")
    lines.append("```bash\n")
    lines.append("python3 MCM_Sim/26A/data/Battery-Archive/scripts/sync_battery_archive.py\n")
    lines.append("```\n\n")
    lines.append("脚本默认会将每个 query 的逐 cell CSV **打包为 `tar.gz`**（节省磁盘空间），输出位置：\n\n")
    lines.append("- `extracted/cycling/*.tar.gz`\n")
    lines.append("- `extracted/disruptive/*.tar.gz`\n\n")
    lines.append("解压示例：\n\n")
    lines.append("```bash\n")
    lines.append("tar -xzf MCM_Sim/26A/data/Battery-Archive/extracted/cycling/energy_and_capacity_decay.tar.gz\n")
    lines.append("```\n\n")
    lines.append("## 循环测试（Cycling tests）\n\n")
    lines.append(f"- Cell 列表 dashboard token：`{cycle_list_token}`\n")
    lines.append(f"- Data dashboard token：`{cycle_data_token}`\n")
    lines.append(f"- Cell 列表 query：`{cycle_list_query.get('id')}` {cycle_list_query.get('name')}\n\n")
    lines.append("Data dashboard 的查询（按查询名/ID）：\n\n")
    for qid, q in sorted(cycle_data_queries.items(), key=lambda x: (str(x[1].get("name") or ""), x[0])):
        lines.append(f"- `{qid}` {q.get('name')}\n")
    lines.append("\n")
    lines.append("接口示例（获取循环 Cell 列表）：\n\n")
    lines.append("```bash\n")
    lines.append(
        f"curl -sS -X POST \"{_query_results_api(int(cycle_list_query.get('id')), cycle_list_token)}\" \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\"queryId\":<QUERY_ID>,\"parameters\":{...}}'\n"
    )
    lines.append("```\n\n")
    lines.append("## 破坏测试（Disruptive tests）\n\n")
    lines.append(f"- Cell 列表 dashboard token：`{disruptive_list_token}`\n")
    lines.append(f"- Data dashboard token：`{disruptive_data_token}`\n")
    lines.append(
        f"- Cell 列表 query：`{disruptive_list_query.get('id')}` {disruptive_list_query.get('name')}\n\n"
    )
    lines.append("Data dashboard 的查询（按查询名/ID）：\n\n")
    for qid, q in sorted(disruptive_data_queries.items(), key=lambda x: (str(x[1].get("name") or ""), x[0])):
        lines.append(f"- `{qid}` {q.get('name')}\n")
    lines.append("\n")
    lines.append("注：更详细的“每个输出文件来自哪个 query/参数”的对应关系见 `manifest.csv`。\n")
    out_path.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sources_dir = root / "sources"
    raw_dir = root / "raw"
    extracted_dir = root / "extracted"
    download_list_path = root / "download_list.md"
    manifest_path = root / "manifest.csv"

    sources_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)

    # 1) 下载页面快照（用于提取 iframe dashboard token）
    cycle_list_url = f"{BATTERYARCHIVE_SITE}/cycle_list.html?t=0001"
    disruptive_list_url = f"{BATTERYARCHIVE_SITE}/disruptive_list.html?t=0001"
    study_url = f"{BATTERYARCHIVE_SITE}/study_summaries.html"
    metadata_url = f"{BATTERYARCHIVE_SITE}/metadata.html"

    snapshots = [
        (cycle_list_url, sources_dir / "cycle_list.html"),
        (disruptive_list_url, sources_dir / "disruptive_list.html"),
        (study_url, sources_dir / "study_summaries.html"),
        (metadata_url, sources_dir / "metadata.html"),
    ]
    for url, path in snapshots:
        if not path.exists() or path.stat().st_size == 0:
            try:
                _curl_download(url, path)
            except Exception as e:  # noqa: BLE001
                print(f"[WARN] 页面下载失败（继续）：{url} ({type(e).__name__})", file=sys.stderr)

    cycle_html = (sources_dir / "cycle_list.html").read_text(encoding="utf-8", errors="ignore")
    disruptive_html = (sources_dir / "disruptive_list.html").read_text(encoding="utf-8", errors="ignore")

    cycle_list_token = _extract_first_dashboard_token(cycle_html)
    disruptive_list_token = _extract_first_dashboard_token(disruptive_html)
    if not cycle_list_token or not disruptive_list_token:
        print("[ERROR] 无法从 BatteryArchive 页面中提取 dashboard token。", file=sys.stderr)
        return 2

    # 2) 下载 dashboard 元数据（raw/）
    dashboards_dir = raw_dir / "dashboards"
    dashboards_dir.mkdir(parents=True, exist_ok=True)

    def fetch_dashboard(token: str) -> Dict[str, Any]:
        out_path = dashboards_dir / f"{token}.json"
        if not out_path.exists() or out_path.stat().st_size == 0:
            data = _curl_get(_dashboard_public_api(token))
            out_path.write_bytes(data)
        return json.loads(out_path.read_text(encoding="utf-8"))

    cycle_list_dash = fetch_dashboard(cycle_list_token)
    disruptive_list_dash = fetch_dashboard(disruptive_list_token)

    # 3) 从 Selection Table 的按钮模板中解析 Data dashboard token
    cycle_list_widget = _find_selection_table_widget(cycle_list_dash)
    disruptive_list_widget = _find_selection_table_widget(disruptive_list_dash)

    def extract_data_dashboard_token(widget: Dict[str, Any]) -> str:
        vis = widget.get("visualization") or {}
        opts = vis.get("options") or {}
        btns = opts.get("buttonArr") or []
        for b in btns:
            tpl = b.get("linkUrlTemplate") or ""
            token = _extract_public_dashboard_token_from_link(tpl)
            if token:
                return token
        raise RuntimeError("Selection Table 中未找到 Data dashboard 的链接模板（buttonArr）。")

    cycle_data_token = extract_data_dashboard_token(cycle_list_widget)
    disruptive_data_token = extract_data_dashboard_token(disruptive_list_widget)

    cycle_data_dash = fetch_dashboard(cycle_data_token)
    disruptive_data_dash = fetch_dashboard(disruptive_data_token)

    # 4) 获取 Cell List query 及默认参数（从 dashboard 元数据中读取）
    cycle_list_query = (cycle_list_widget.get("visualization") or {}).get("query") or {}
    disruptive_list_query = (disruptive_list_widget.get("visualization") or {}).get("query") or {}
    if not cycle_list_query.get("id") or not disruptive_list_query.get("id"):
        print("[ERROR] dashboard 元数据中缺少 Cell List 的 query id。", file=sys.stderr)
        return 2

    cycle_list_params = _params_from_query_options(cycle_list_query)
    disruptive_list_params = _params_from_query_options(disruptive_list_query)

    # 5) 导出 Cell List（CSV）
    cycling_dir = extracted_dir / "cycling"
    disruptive_dir = extracted_dir / "disruptive"
    cycling_dir.mkdir(parents=True, exist_ok=True)
    disruptive_dir.mkdir(parents=True, exist_ok=True)

    cycle_cells_csv = cycling_dir / "cell_list.csv"
    disruptive_cells_csv = disruptive_dir / "cell_list.csv"

    def export_query_to_csv(
        *,
        api_key: str,
        query_id: int,
        query_name: str,
        parameters: Dict[str, Any],
        out_csv: Path,
        extra_cols: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, str]:
        resp = _curl_post_json(
            _query_results_api(query_id, api_key),
            {"queryId": query_id, "parameters": parameters},
        )
        cols, rows, retrieved_at = _query_to_rows(resp)
        if extra_cols:
            for k in extra_cols.keys():
                if k not in cols:
                    cols = [k] + cols
            for r in rows:
                for k, v in extra_cols.items():
                    r.setdefault(k, v)
        _write_csv(rows, cols, out_csv)
        return len(rows), retrieved_at

    manifest_rows: List[Dict[str, str]] = []

    if not cycle_cells_csv.exists() or cycle_cells_csv.stat().st_size == 0:
        nrows, retrieved_at = export_query_to_csv(
            api_key=cycle_list_token,
            query_id=int(cycle_list_query["id"]),
            query_name=str(cycle_list_query.get("name") or "Cycle Test Cell List"),
            parameters=cycle_list_params,
            out_csv=cycle_cells_csv,
        )
        status = "ok"
        rows_str = str(nrows)
    else:
        status = "skip"
        retrieved_at = ""
        rows_str = ""

    if cycle_cells_csv.exists() and cycle_cells_csv.stat().st_size > 0:
        manifest_rows.append(
            {
                "category": "cycling",
                "kind": "cell_list",
                "query_id": str(cycle_list_query["id"]),
                "query_name": str(cycle_list_query.get("name") or ""),
                "dashboard_token": cycle_list_token,
                "output": cycle_cells_csv.relative_to(root).as_posix(),
                "records": rows_str,
                "retrieved_at": retrieved_at,
                "status": status,
                "size_bytes": str(cycle_cells_csv.stat().st_size),
                "sha256": _sha256(cycle_cells_csv),
            }
        )

    if not disruptive_cells_csv.exists() or disruptive_cells_csv.stat().st_size == 0:
        nrows, retrieved_at = export_query_to_csv(
            api_key=disruptive_list_token,
            query_id=int(disruptive_list_query["id"]),
            query_name=str(disruptive_list_query.get("name") or "Disruptive Test Cell List"),
            parameters=disruptive_list_params,
            out_csv=disruptive_cells_csv,
        )
        status = "ok"
        rows_str = str(nrows)
    else:
        status = "skip"
        retrieved_at = ""
        rows_str = ""

    if disruptive_cells_csv.exists() and disruptive_cells_csv.stat().st_size > 0:
        manifest_rows.append(
            {
                "category": "disruptive",
                "kind": "cell_list",
                "query_id": str(disruptive_list_query["id"]),
                "query_name": str(disruptive_list_query.get("name") or ""),
                "dashboard_token": disruptive_list_token,
                "output": disruptive_cells_csv.relative_to(root).as_posix(),
                "records": rows_str,
                "retrieved_at": retrieved_at,
                "status": status,
                "size_bytes": str(disruptive_cells_csv.stat().st_size),
                "sha256": _sha256(disruptive_cells_csv),
            }
        )

    # 读取 Cell ID 列表（从 CSV）
    def read_cell_ids(csv_path: Path) -> List[str]:
        ids: List[str] = []
        seen: set[str] = set()
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                cid = (row.get("cell_id") or "").strip()
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                ids.append(cid)
        return ids

    cycle_cell_ids = read_cell_ids(cycle_cells_csv)
    disruptive_cell_ids = read_cell_ids(disruptive_cells_csv)

    # 6) 解析 Data dashboard 中的 query 列表
    cycle_data_queries = _unique_queries_from_dashboard(cycle_data_dash)
    disruptive_data_queries = _unique_queries_from_dashboard(disruptive_data_dash)

    # 7) 写 download_list.md（清单）——先写，便于用户查看
    _write_download_list(
        download_list_path,
        cycle_list_token=cycle_list_token,
        cycle_data_token=cycle_data_token,
        disruptive_list_token=disruptive_list_token,
        disruptive_data_token=disruptive_data_token,
        cycle_list_query=cycle_list_query,
        disruptive_list_query=disruptive_list_query,
        cycle_data_queries=cycle_data_queries,
        disruptive_data_queries=disruptive_data_queries,
    )

    # 8) 导出每个 query 的数据（逐 cell 下载 -> 打包为 tar.gz，节省磁盘空间）
    def export_queries_as_archives(
        *,
        category: str,
        api_key: str,
        cell_ids: List[str],
        queries: Dict[int, Dict[str, Any]],
    ) -> None:
        base_dir = extracted_dir / category
        base_dir.mkdir(parents=True, exist_ok=True)

        for qid, q in sorted(queries.items(), key=lambda x: (str(x[1].get("name") or ""), x[0])):
            qname = str(q.get("name") or f"query_{qid}")
            slug = _slugify(qname)
            out_dir = base_dir / slug
            archive_path = base_dir / f"{slug}.tar.gz"

            base_params = _params_from_query_options(q)
            if "cell_id" not in base_params:
                continue

            # 已打包：直接记录到 manifest，不再重复下载
            if archive_path.exists() and archive_path.stat().st_size > 0 and not out_dir.exists():
                manifest_rows.append(
                    {
                        "category": category,
                        "kind": "archive",
                        "query_id": str(qid),
                        "query_name": qname,
                        "dashboard_token": api_key,
                        "output": archive_path.relative_to(root).as_posix(),
                        "records": str(_count_csv_in_tar_gz(archive_path)),
                        "retrieved_at": "",
                        "status": "skip",
                        "size_bytes": str(archive_path.stat().st_size),
                        "sha256": _sha256(archive_path),
                    }
                )
                continue

            out_dir.mkdir(parents=True, exist_ok=True)
            failures = 0
            for i, cell_id in enumerate(cell_ids, start=1):
                out_csv = out_dir / f"{_encode_cell_id(cell_id)}.csv"
                if out_csv.exists() and out_csv.stat().st_size > 0:
                    continue

                params = dict(base_params)
                params["cell_id"] = [cell_id]
                try:
                    resp = _curl_post_json(
                        _query_results_api(qid, api_key),
                        {"queryId": qid, "parameters": params},
                    )
                    cols, rows, _retrieved_at = _query_to_rows(resp)
                    if "cell_id" not in cols:
                        cols = ["cell_id"] + cols
                        for r in rows:
                            r["cell_id"] = cell_id
                    _write_csv(rows, cols, out_csv)
                except Exception as e:  # noqa: BLE001
                    failures += 1
                    print(
                        f"[WARN] 导出失败: {category} qid={qid} cell={cell_id} ({type(e).__name__})",
                        file=sys.stderr,
                    )

                if i % 10 == 0:
                    time.sleep(0.2)

            # 打包并清理目录（若目录为空，也会生成空包；这里做一次检查避免）
            csv_count = len(list(out_dir.glob("*.csv")))
            if csv_count > 0:
                _pack_dir_to_tar_gz(out_dir, archive_path)
                shutil.rmtree(out_dir)

            status = "ok" if failures == 0 and csv_count == len(cell_ids) else "partial"
            manifest_rows.append(
                {
                    "category": category,
                    "kind": "archive",
                    "query_id": str(qid),
                    "query_name": qname,
                    "dashboard_token": api_key,
                    "output": archive_path.relative_to(root).as_posix() if archive_path.exists() else "",
                    "records": str(_count_csv_in_tar_gz(archive_path)) if archive_path.exists() else "0",
                    "retrieved_at": "",
                    "status": status,
                    "size_bytes": str(archive_path.stat().st_size) if archive_path.exists() else "",
                    "sha256": _sha256(archive_path) if archive_path.exists() else "",
                }
            )

    export_queries_as_archives(category="cycling", api_key=cycle_data_token, cell_ids=cycle_cell_ids, queries=cycle_data_queries)
    export_queries_as_archives(
        category="disruptive", api_key=disruptive_data_token, cell_ids=disruptive_cell_ids, queries=disruptive_data_queries
    )

    # 9) 写 manifest.csv
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "category",
                "kind",
                "query_id",
                "query_name",
                "dashboard_token",
                "output",
                "records",
                "retrieved_at",
                "status",
                "size_bytes",
                "sha256",
            ],
        )
        w.writeheader()
        w.writerows(manifest_rows)

    print(f"[OK] download_list: {download_list_path}")
    print(f"[OK] manifest:      {manifest_path}")
    print(f"[OK] extracted:     {extracted_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
