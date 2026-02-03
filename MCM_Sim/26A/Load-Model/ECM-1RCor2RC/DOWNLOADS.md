# 可直接下载清单（ECM 1RC/2RC）

本文件用于“复刻/迁移”本目录依赖的外部资料（第三方仓库、论文线索等）。

---

## 1) 代码仓库（推荐）

### NREL / thevenin（Thevenin nRC ECM）

已下载到：
- `MCM_Sim/26A/Load-Model/ECM-1RCor2RC/third_party/thevenin/`

复刻命令（建议浅克隆）：
```bash
git clone --depth 1 https://github.com/NREL/thevenin.git thevenin
```

用途：
- 对照 1RC/2RC/nRC 的状态方程与端电压计算
- 可直接当 Python 包使用（具体见其 README/文档）

---

## 2) 论文/关键词（用于检索）

如果需要更系统的建模/参数辨识背景，建议用以下关键词检索：
- “battery equivalent circuit model Thevenin 1RC 2RC parameter identification”
- “HPPC battery R0 R1 C1 identification”
- “SOC estimation EKF Thevenin model OCV-SOC derivative”

注：
- 本目录不内置付费论文 PDF；请通过学校/机构渠道获取全文。

