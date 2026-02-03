# 可直接下载清单（SOC EKF）

本文件用于“复刻/迁移”本目录依赖的外部资料（第三方仓库、论文线索等）。

---

## 1) 代码仓库（推荐）

### larchuto / Battery-Kalman（Python EKF 示例）

已下载到：
- `MCM_Sim/26A/Load-Model/EKF/third_party/Battery-Kalman/`

复刻命令：
```bash
git clone --depth 1 https://github.com/larchuto/Battery-Kalman.git Battery-Kalman
```

说明：
- 该仓库可能未提供明确 LICENSE；如需用于公开发布/商用，请先确认授权。

### AlterWL / Battery_SOC_Estimation（MATLAB/Simulink + EKF + 参数辨识）

已下载到：
- `MCM_Sim/26A/Load-Model/EKF/third_party/Battery_SOC_Estimation/`

复刻命令：
```bash
git clone --depth 1 https://github.com/AlterWL/Battery_SOC_Estimation.git Battery_SOC_Estimation
```

---

## 2) 论文/关键词（用于检索）

典型检索关键词：
- “Gregory Plett extended Kalman filter SOC estimation”
- “battery Thevenin model EKF SOC”
- “dOCV dSOC numerical differentiation EKF”

提示：
- Plett 在 2004 年前后发表过一系列关于电池状态/参数估计的 EKF 论文（常被引用作为入门与工程参考）。
- 本目录不内置付费论文 PDF；请通过学校/机构渠道获取全文。

