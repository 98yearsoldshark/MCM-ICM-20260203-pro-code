# 字段到 Segment 的映射（面向 Q1）

目标：把 bugreport / Battery Historian 的事件时间线，抽象成主代码可用的分段常值输入：

- 结构体：`mcm26a.scenarios.schedule.Segment`
- 文件：`MCM_Sim/26A/src/mcm26a/scenarios/schedule.py`

下面给出“建议映射”（并不要求每项都能从 bugreport 精确提取；缺失时可用合理默认值并在论文里说明）：

|Segment 字段|含义|典型来源（bugreport/历史记录）|缺失时建议|
|---|---|---|---|
|`duration_s`|该段持续时间（秒）|事件时间戳差分/窗口聚合|按 30s~5min 分箱|
|`ambient_temp_c`|环境温度（°C）|若无可用则当作场景参数|设定 0/10/23/35 四档用于敏感性|
|`screen_on`|屏幕是否点亮|Screen on/off 事件|按时间窗内是否亮屏判定|
|`brightness_nits`|亮度（nits）|亮度 level/setting（若能提取）|用 50/200/500 nits 三档|
|`cpu_load`|CPU 负载强度（0~1）|CPU active / wakelock 密度（近似）|用 low/med/high 分档映射|
|`gpu_load`|GPU 负载强度（0~1）|游戏/视频等活动窗口（近似）|可先=0，后续再加|
|`radio_mode`|网络模式（wifi/lte/5g/none）|连接状态、移动数据/Wi‑Fi 状态|若未知先用 `wifi`/`lte` 二档|
|`signal_quality`|信号强弱（good/ok/poor）|信号格/RSRP 相关字段（若有）|设为 `ok`|
|`net_activity`|网络活动（idle/browse/video/download）|数据传输窗口、应用活动（近似）|按轻/中/重三档分配|
|`gps_on`|GPS 是否开启|Location 请求/传感器状态|按是否出现定位请求判定|
|`background_level`|后台强度（low/med/high）|wakelock、后台同步、JobScheduler（近似）|默认 `med`|

注：你不必把 bugreport 解析到“逐秒准确”。Q1 的重点是：**你提供了一个从真实行为到可解释输入函数的可复现方法**，并能在后续 Q2/Q3 用同一套输入驱动连续时间模型。

