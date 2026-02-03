# 完整性检查报告（Battery-Intelligence-Lab）

生成时间：2026-01-30

本报告用于回答“本目录是否缺失/遗失资源”，并给后续接手者提供最短的自检路径。

## 结论

截至本报告生成时：

- `sources/urls.txt` 共 32 条直链，与 `manifest.csv` 的 32 条记录一一对应。
- `manifest.csv` 中无 `failed(...)` / `skipped_low_disk` 项。
- `raw/` 下所有 32 个文件均存在且大小与 `manifest.csv` 记录一致（未发现缺失或 0 字节文件）。

## 快速自检方法（建议后续接手者复跑）

在仓库根目录执行：

```bash
python3 - <<'PY'
import csv
from collections import Counter
from pathlib import Path

base = Path("MCM_Sim/26A/data/Battery-Intelligence-Lab")
manifest = base / "manifest.csv"
urls = base / "sources/urls.txt"
raw = base / "raw"

urls_n = len([l for l in urls.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")])
rows = list(csv.DictReader(manifest.open(newline="", encoding="utf-8")))

missing = []
size_mismatch = []
for r in rows:
    p = raw / r["raw_path"]
    if not p.exists() or p.stat().st_size == 0:
        missing.append(r["url"])
        continue
    if r["size_bytes"] and p.stat().st_size != int(r["size_bytes"]):
        size_mismatch.append(r["url"])

print("urls.txt:", urls_n)
print("manifest rows:", len(rows))
print("status_download:", Counter(r["status_download"] for r in rows))
print("status_extract:", Counter(r["status_extract"] for r in rows))
print("missing:", len(missing))
print("size_mismatch:", len(size_mismatch))
PY
```

## 关于 `skip`

`manifest.csv` 里的 `skip` 是“已存在所以跳过重复工作”，不是“缺失”：

- `status_download=skip`：`raw/<...>` 文件已存在且非空，本次不重复下载（幂等）。
- `status_extract=skip / skip_nonempty`：解压目录已存在（或目录非空），本次不重复解压。
- `status_extract=n/a`：不适用（例如非 zip 文件，或 data/*.zip 默认不解压）。

如果需要强制重下：删除对应的 `raw/...` 文件后再运行

```bash
python3 MCM_Sim/26A/data/Battery-Intelligence-Lab/scripts/sync_assets.py
```

