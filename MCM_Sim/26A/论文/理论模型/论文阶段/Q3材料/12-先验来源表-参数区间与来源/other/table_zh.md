| 参数 | 含义 | 先验(默认) | 先验(tight) | 数据锚定/来源 | 来源文件/许可 |
| --- | --- | --- | --- | --- | --- |
| batt_capacity_scale | 容量缩放（制造/机型差异+标定误差） | logU[0.90, 1.10] | logU[0.97, 1.03] | 工程先验：以手机电池标称容量±10% 覆盖机型/批次差异；老化主效应由 SOH 单独描述。 | （工程先验；可在论文中补充任一公开电池规格书作为引用） |
| batt_r0_scale | 欧姆内阻 R0 缩放（端电压下陷关键驱动） | logU[0.80, 1.30] | logU[0.95, 1.05] | 工程先验：覆盖温度/批次/老化导致的直流内阻变化；老化主效应由 (SOH, α_R) 共同调制。 | （工程先验；可用公开 ECM 参数辨识论文/数据集补强） |
| batt_r1_scale | 极化支路 R1 缩放（动态恢复/尖峰后回升形状） | logU[0.80, 1.30] | logU[0.95, 1.05] | 工程先验：同 R0，允许不同手机/不同工况下的极化强度变化。 | （工程先验；可用公开 ECM 参数辨识论文/数据集补强） |
| v_cut_V | 欠压截止阈值（设备级关机阈值，单位 V） | U[3.2, 3.4] | U[3.27, 3.33] | 工程先验：智能手机通常会在 3.2~3.4V 附近触发欠压/关机保护（比电芯最低电压更保守）。 | （工程先验；建议在论文中补充公开电源管理/电池保护文档引用） |
| soc_min | 最小 SOC（保护性下限） | {0, 0.03, 0.05, 0.10} | {0.03, 0.05} | 工程先验：不同设备对“0% 电量”的标定不同，通常保留 3%~10% 的保护余量。 | （工程先验） |
| soh | 健康度 SOH（容量保持率，慢变量） | U[0.70, 1.00] | U[0.90, 1.00] | 公开电池状态表（n=36）SOH 分位数：P05=0.639, P50=0.876, P95=1.000。默认先验覆盖中度老化到新电池。 | data/MCM2026_battery_state_table/MCM2026_battery_state_table.csv（开源数据；许可见同目录说明） |
| alpha_r | 老化增阻强度 α_R（SOH→R0 增长映射系数，慢变量） | logU[0.1, 3.0] | logU[0.5, 1.5] | 工程先验：用于覆盖“温和/中等/激进”增阻情形；tight 仅用于 sanity check（先验收窄应降低参数方差占比）。 | （工程先验；可后续用 CALCE/NASA 等公开老化数据拟合收窄） |
| eta_pmic | 电源管理链效率 η_PMIC（电池端→负载端） | U[0.90, 0.95] | U[0.92, 0.95] | 工程先验：典型 DC-DC/PMIC 在中等负载效率约 90%~95%。 | （工程先验；建议补充任一公开 PMIC 数据手册引用） |
| base_scale | 基础功耗缩放（系统常开 + 轻载） | logU[0.70, 1.30] | logU[0.90, 1.10] | AndroWatts( n=1000 ) 部件能耗占比分位数：P05=0.051, P50=0.077, P95=0.107；相对中位数约 0.66~1.39。 用于锚定“系统基础+基础设施”量级。 | data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0） |
| screen_scale | 屏幕功耗缩放（亮度模型之外的设备差异） | logU[0.70, 1.30] | logU[0.90, 1.10] | AndroWatts( n=1000 ) 部件能耗占比分位数：P05=0.048, P50=0.126, P95=0.325；相对中位数约 0.38~2.58。 屏幕占比本身受亮度/使用强影响；我们把主要可变性放在 brightness 与场景输入，scale 保持较窄。 | data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0） |
| cpu_scale | CPU 功耗缩放（同类任务/同场景下的软硬件效率差异） | logU[0.60, 1.40] | logU[0.90, 1.10] | AndroWatts( n=1000 ) 部件能耗占比分位数：P05=0.358, P50=0.539, P95=0.701；相对中位数约 0.66~1.30。 | data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0） |
| gpu_scale | GPU 功耗缩放（图形负载差异） | logU[0.60, 1.40] | logU[0.90, 1.10] | AndroWatts( n=1000 ) 部件能耗占比分位数：P05=0.041, P50=0.126, P95=0.177；相对中位数约 0.32~1.41。 | data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0） |
| gps_scale | GPS 功耗缩放（定位模块差异） | logU[0.70, 1.30] | logU[0.90, 1.10] | AndroWatts 中 GPS 占比普遍极小（接近 0），不足以提供稳定锚定；此处采用工程先验。 | （工程先验；可后续补充公开定位功耗测量研究） |
| background_base_scale | 后台基线功耗缩放（常驻服务/系统维护） | logU[0.70, 1.30] | logU[0.90, 1.10] | AndroWatts( n=1000 ) 部件能耗占比分位数：P05=0.051, P50=0.077, P95=0.107；相对中位数约 0.66~1.39。 与 base_scale 同源锚定：后台与基础设施能耗同属“常驻+轻载”类别。 | data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0） |
| rrc_state_scale | 无线状态机功耗缩放（IDLE/CONNECTED/TAIL 的状态功耗） | logU[0.60, 1.60] | logU[0.90, 1.10] | AndroWatts( n=1000 ) 部件能耗占比分位数：P05=0.056, P50=0.111, P95=0.177；相对中位数约 0.50~1.59。 无线项在不同应用/网络环境下差异较大；该 scale 用于吸收机型/环境不确定性。 | data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0） |
| rrc_data_scale | 无线数据能耗缩放（每 MB 能耗） | logU[0.60, 1.60] | logU[0.90, 1.10] | AndroWatts( n=1000 ) 部件能耗占比分位数：P05=0.002, P50=0.003, P95=0.005；相对中位数约 0.57~1.76。 蜂窝网络占比虽小但波动明显；用于锚定数据传输相关不确定性量级。 | data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0） |
| rrc_tail_scale | 尾态时长缩放（TAIL 持续时间不确定性） | logU[0.70, 1.30] | logU[0.90, 1.10] | 工程先验：不同系统/网络协议的 tail timer 存在差异；在缺乏一致公开标定数据时用 ±30% 覆盖。 | （工程先验；可后续补充公开 RRC tail 测量研究） |
| poor_signal_psi_scale | 弱信号惩罚缩放（poor vs good 信号能耗倍率） | logU[0.90, 1.30] | logU[0.95, 1.05] | 工程先验：弱信号通常提高发射功率并增加重传；在无设备特定测量时用温和倍率区间覆盖。 | （工程先验） |
| bg_lambda_scale | 后台唤醒频率缩放（Poisson 到达率） | logU[0.50, 2.00] | logU[0.80, 1.25] | 工程先验：后台任务频率跨用户/应用差异很大；用倍数先验覆盖“安静/中等/嘈杂”系统。 | （工程先验；可后续用真实日志/测量数据定界） |
| interaction_scale | 交互项缩放（屏幕×网络×高 CPU 的协同功耗） | U[0.00, 1.60] | U[0.00, 1.00] | 工程先验：用于吸收“单项功耗叠加≠真实总功耗”的二阶效应（例如高负载导致额外损耗/调度开销）。 | （工程先验；可后续通过实测功耗回归标定） |
