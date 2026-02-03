# 交接说明：SmartphoneMeasurements（for MCM 2026 Problem A）

本文件面向“下一位接手者”，用于快速理解本目录的目的、内容结构、数据结构要点，以及如何验证本目录文件在搬运/同步过程中没有遗失或损坏。

## 0. 这是什么（范围界定）

本目录的职责是：
- 保存与“手机侧功耗/使用行为”相关的公开数据（原始文件尽量不改动）
- 为赛题 A 的场景设定、敏感性分析、建议与写作提供可追溯的“量级证据”

本目录不直接解决：
- 电池本体层实验数据（见 `MCM_Sim/26A/data/NASA-BatteryData/`、`MCM_Sim/26A/data/calce-umd/`）
- 赛题 A 的主建模数据拼接表（见 `MCM_Sim/26A/data/数据集/` 与 `MCM_Sim/26A/data/open_data/`）

## 1. 你应该先读哪些文件

- `README.md`：本目录内容概览 + 数据集索引（去哪找哪些数据）
- `FOR_MCM26A.md`：本目录如何服务赛题 A（建模/写作映射）
- `manifest.csv`：原始数据文件清单 + sha256（用于完整性校验）

历史说明：
- 本目录曾有一个总览文件 `【先看这个】数据集说明.md`，其内容已拆分进各目录 README（NASA-BatteryData、calce-umd、本目录 README），因此已删除以避免重复与过期信息。

## 2. 本目录文件清单（应当存在）

- `user_behavior_dataset.csv`：用户级使用行为统计（700 行）
- `SmartphoneMeasurements.zip`：Samsung 手机通信功耗/吞吐测量仓库快照
- `README.md` / `FOR_MCM26A.md` / `HANDOVER.md`：本目录说明文档
- `manifest.csv`：原始数据文件清单（大小/sha256；用于校验 `user_behavior_dataset.csv` 与 `SmartphoneMeasurements.zip`）
- `zip_contents.txt`：`SmartphoneMeasurements.zip` 的内容列表（用于快速核对，不必解压）

## 3. 完整性校验（建议交接时跑一次）

从仓库根目录运行：

```bash
python3 - <<'PY'
import csv
import hashlib
from pathlib import Path

root = Path("MCM_Sim/26A/data/SmartphoneMeasurements")
manifest = root / "manifest.csv"

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

with manifest.open("r", encoding="utf-8", newline="") as f:
    r = csv.DictReader(f)
    rows = list(r)

ok = True
for row in rows:
    p = root / row["path"]
    if not p.exists():
        print("MISSING:", row["path"])
        ok = False
        continue
    got = sha256(p)
    if got != row["sha256"]:
        print("MISMATCH:", row["path"])
        print(" expected:", row["sha256"])
        print(" got     :", got)
        ok = False

print("OK" if ok else "FAILED")
PY
```

## 4. 使用提示

- `SmartphoneMeasurements.zip` 不建议直接在本目录解压出大量派生文件；如需解压/清洗，建议解压到你的工作目录（如 `MCM_Sim/26A/work/` 或 `mcm_temp/`），并写清楚“来源=本目录 + 处理脚本/规则”。
