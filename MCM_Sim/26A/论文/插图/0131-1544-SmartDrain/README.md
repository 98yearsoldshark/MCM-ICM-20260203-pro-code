# SmartDrain 插图构建（Graphviz/DOT）

本目录用于生成论文中的**概念/结构示意图**（框架图/流程图/因果图），并保持“可复现、可版本管理、风格统一”。

## 依赖

- Graphviz（已安装即可）：`dot -V`

## 一键生成

在仓库根目录执行：

```bash
python MCM_Sim/26A/论文/插图/0131-1544-SmartDrain/scripts/render_final_png.py
```

输出目录：

- `MCM_Sim/26A/论文/插图/0131-1544-SmartDrain/out/final/paper/`：论文版（最终 PNG）
- `MCM_Sim/26A/论文/插图/0131-1544-SmartDrain/out/final/study/`：学习版（最终 PNG）

如需批量生成大量“草稿版式”用于对比（只输出 PNG，避免目录过乱）：

```bash
python MCM_Sim/26A/论文/插图/0131-1544-SmartDrain/scripts/render_all.py
```

草稿输出目录：

- `MCM_Sim/26A/论文/插图/0131-1544-SmartDrain/out/drafts/paper/`
- `MCM_Sim/26A/论文/插图/0131-1544-SmartDrain/out/drafts/study/`

## 当前插图

1. `fig01_power_model`：功耗分解 + PMIC 效率到电池端功率的映射（对应论文中 `P_device(t)`、`P_batt(t)`、`η_PMIC` 的公式组）

## fig01 的版式备选（为了解决“左侧排列太突兀”）

- `fig01_power_model_v2_grid`：左侧 2 列×4 行网格（改动小，更紧凑）
- `fig01_power_model_v3_floating`：取消左侧大容器，模块“悬浮排布”（更轻盈）
- `fig01_power_model_v4_list`：左侧收纳为列表卡片（视觉最稳、最像论文信息图）

## fig01 的版式备选（更适配论文版面：更“短”且不太“宽”）

- `fig01_power_model_v16_tb_top_card_row_direct`：顶部卡片 + 底部两节点一行（较短、逻辑直观）
- `fig01_power_model_v21_tb_card_no_t`：在卡片中省略各项的 `(t)`（更窄；正文统一说明均为时变项）
- `fig01_power_model_v22_tb_card_no_t_wrap_eta`：在 v21 基础上把效率说明换行（更窄；目前最推荐）
