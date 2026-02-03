"""AndroWatts（Zenodo）数据集适配：aggregated.csv -> 可用于 Q2 的观测对照。

数据来源（仓库内镜像）：
- `MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`

本模块做什么：
- 读取 aggregated.csv（1000 条测试的聚合指标）；
- 将其整理成“观测功耗分解”（W）以及与我们模型输入字段相近的“场景段（Segment）”。

重要说明（对齐赛题）：
- 本模块只用于“参数估计/验证/量级佐证”，不允许替代连续时间模型本身。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from mcm26a.scenarios.schedule import Segment


@dataclass(frozen=True)
class ObservedPowerW:
    """观测功耗（W）：从 AndroWatts 的 power rails 聚合得到。"""

    total_w: float
    screen_w: float
    cpu_w: float
    gpu_w: float
    radio_w: float
    gps_w: float
    background_w: float
    base_w: float
    other_w: float

    def as_dict(self) -> dict[str, float]:
        return {
            "total_w": float(self.total_w),
            "screen_w": float(self.screen_w),
            "cpu_w": float(self.cpu_w),
            "gpu_w": float(self.gpu_w),
            "radio_w": float(self.radio_w),
            "gps_w": float(self.gps_w),
            "background_w": float(self.background_w),
            "base_w": float(self.base_w),
            "other_w": float(self.other_w),
        }


@dataclass(frozen=True)
class AndroWattsCase:
    """一条测试样本：包含观测功耗与映射后的模型输入段。"""

    test_id: int
    duration_s: float
    soc0: float | None
    temp_c: float | None
    segment: Segment
    obs: ObservedPowerW


def _to_num(s: Any) -> float | None:
    try:
        v = float(s)
    except Exception:
        return None
    if not np.isfinite(v):
        return None
    return float(v)


def _sum_cols_uW(row: pd.Series, cols: list[str]) -> float:
    return float(sum(float(row.get(c, 0.0) or 0.0) for c in cols))


def load_aggregated_csv(path: str | Path) -> pd.DataFrame:
    """读取 aggregated.csv 并做最小清洗（处理 err/缺失）。"""

    p = Path(path)
    df = pd.read_csv(p)

    # 统一字段名（与作者 analysis.py 一致）
    ren = {
        "RougeMesuré": "RedLvl",
        "VertMesuré": "GreenLvl",
        "BleuMesuré": "BlueLvl",
        "CPU_LITTLE_FREQ_KHz": "CPU_little",
        "CPU_MID_FREQ_KHz": "CPU_mid",
        "CPU_BIG_FREQ_KHz": "CPU_big",
        "GPU0_FREQ": "GPU0",
        "GPU_1FREQ": "GPU1",
        "GPU_MEM_AVG": "GPU_mem",
        "TOTAL_DATA_WIFI_BYTES": "WIFI_data",
    }
    df = df.rename(columns=ren)

    # 处理 CPU_mid 的 err
    if "CPU_mid" in df.columns:
        df["CPU_mid"] = pd.to_numeric(df["CPU_mid"].replace("err", np.nan), errors="coerce")
        df["CPU_mid"] = df["CPU_mid"].fillna(df["CPU_mid"].median())

    # WIFI_data/C_ID/M_ID 里可能有 0，需要时再处理；这里保持原样
    return df


def estimate_duration_s(row: pd.Series) -> float:
    """估计测试时长（秒）。

经验结论：
- aggregated.csv 同时包含两套列：
  - `*_ENERGY_AVG_UWS`：在本仓库快速自检中更像“平均功率（uW）”
  - `*_ENERGY_UW`：更像“总能量（uW*s）”
- 因此 duration_s ≈ sum(ENERGY_UW)/sum(ENERGY_AVG_UWS)
"""

    cols_avg = [c for c in row.index if str(c).endswith("_ENERGY_AVG_UWS")]
    cols_u = [c for c in row.index if str(c).endswith("_ENERGY_UW")]
    p_uW = _sum_cols_uW(row, cols_avg)
    e_uWs = _sum_cols_uW(row, cols_u)
    if p_uW <= 1e-12:
        return 30.0  # 兜底：多数测试接近 30s
    dur = e_uWs / p_uW
    # 合理范围裁剪，避免极端值影响仿真稳定性
    return float(min(120.0, max(5.0, dur)))


def observed_power_from_row(row: pd.Series) -> ObservedPowerW:
    """从原始 rails 聚合出与模型组件对齐的观测功耗（W）。"""

    # 使用 *_ENERGY_AVG_UWS 作为“平均功率（uW）”估计
    rails = [c for c in row.index if str(c).endswith("_ENERGY_AVG_UWS")]
    p_total_uW = _sum_cols_uW(row, rails)

    # 组件映射（可解释、但不是唯一映射；论文中应说明这是“合理聚合”）
    screen_cols = ["Display_ENERGY_AVG_UWS", "L22M_DISP_ENERGY_AVG_UWS"]
    gpu_cols = ["GPU3D_ENERGY_AVG_UWS", "GPU_ENERGY_AVG_UWS"]
    cpu_cols = [
        "CPU_BIG_ENERGY_AVG_UWS",
        "CPU_MID_ENERGY_AVG_UWS",
        "CPU_LITTLE_ENERGY_AVG_UWS",
        "S9M_VDD_CPUCL0_M_ENERGY_AVG_UWS",
        "TPU_ENERGY_AVG_UWS",
    ]
    radio_cols = ["WLANBT_ENERGY_AVG_UWS", "CELLULAR_ENERGY_AVG_UWS", "CELLULAR_ENERGY_AVG_UWS.1"]
    gps_cols = ["GPS_ENERGY_AVG_UWS"]

    # background: 选取“存储/传感器/内存/相机”等较典型后台/外设 rail
    background_cols = [
        "UFS(Disk)_ENERGY_AVG_UWS",
        "Sensor_ENERGY_AVG_UWS",
        "Memory_ENERGY_AVG_UWS",
        "Memory_ENERGY_AVG_UWS.1",
        "Camera_ENERGY_AVG_UWS",
        "L21S_VDD2L_MEM_ENERGY_AVG_UWS",
        "S12S_VDD_AUR_ENERGY_AVG_UWS",
    ]

    # base: 基础设施 rail（含系统/基带基础等；其余未归类也会进 other/base）
    base_cols = ["INFRASTRUCTURE_ENERGY_AVG_UWS", "INFRASTRUCTURE_ENERGY_AVG_UWS.1", "S6M_LLDO1_ENERGY_AVG_UWS", "S8M_LLDO2_ENERGY_AVG_UWS"]

    p_screen = _sum_cols_uW(row, screen_cols)
    p_cpu = _sum_cols_uW(row, cpu_cols)
    p_gpu = _sum_cols_uW(row, gpu_cols)
    p_radio = _sum_cols_uW(row, radio_cols)
    p_gps = _sum_cols_uW(row, gps_cols)
    p_bg = _sum_cols_uW(row, background_cols)
    p_base = _sum_cols_uW(row, base_cols)

    known = p_screen + p_cpu + p_gpu + p_radio + p_gps + p_bg + p_base
    p_other = max(0.0, float(p_total_uW - known))

    scale = 1e-6  # uW -> W
    return ObservedPowerW(
        total_w=float(p_total_uW) * scale,
        screen_w=float(p_screen) * scale,
        cpu_w=float(p_cpu) * scale,
        gpu_w=float(p_gpu) * scale,
        radio_w=float(p_radio) * scale,
        gps_w=float(p_gps) * scale,
        background_w=float(p_bg) * scale,
        base_w=float(p_base) * scale,
        other_w=float(p_other) * scale,
    )


def map_row_to_segment(
    row: pd.Series,
    *,
    duration_s: float,
    max_screen_nits: float = 500.0,
) -> Segment:
    """把 AndroWatts 的“设备状态特征”映射为模型输入段（Segment）。

注意：
- 这是“验证适配器”，是合理但不唯一的映射；
- 目标是将公开数据集的状态特征映射到我们模型需要的外生输入（亮度/负载/网络/温度）。
"""

    # 亮度：数据中 Brightness ∈ [0,100]，可视为百分比。映射到 nits（最大值用常见手机量级）。
    b = _to_num(row.get("Brightness"))
    b = 0.0 if b is None else float(max(0.0, min(100.0, b)))
    screen_on = b > 0.5
    brightness_nits = float(max_screen_nits) * (b / 100.0) if screen_on else 0.0

    # APL（Average Picture Level）：尽量从 RGB 亮度测量估计（若可用），否则留空交给功耗模型做经验映射。
    # 注：AndroWatts 的 RGB 字段是设备测得的屏幕像素强度（与内容有关），比仅用 brightness 更贴近 no7 的屏幕机理。
    apl = float("nan")
    r = _to_num(row.get("RedLvl"))
    g = _to_num(row.get("GreenLvl"))
    b2 = _to_num(row.get("BlueLvl"))
    if r is not None and g is not None and b2 is not None:
        apl = float(max(0.0, min(1.0, (float(r) + float(g) + float(b2)) / 3.0 / 255.0)))

    # 温度：AVG_SOC_TEMP(m°C) -> °C（若缺失则用 23°C）
    t_mc = _to_num(row.get("AVG_SOC_TEMP"))
    temp_c = 23.0 if t_mc is None else float(t_mc) / 1000.0

    # CPU/GPU “负载” proxy：用频率归一化（无需知道具体任务，只要能对齐量级）
    # 注：这不是“利用功耗反推负载”的作弊做法，而是常见可观测状态（频率/簇占用）proxy。
    cpu_big = _to_num(row.get("CPU_big")) or 0.0
    cpu_mid = _to_num(row.get("CPU_mid")) or 0.0
    cpu_little = _to_num(row.get("CPU_little")) or 0.0

    # 使用全局经验上限（来自数据集统计的 max；避免偶发异常值影响）
    max_big = 2_900_000.0
    max_mid = 4_650_000.0
    max_little = 1_800_000.0

    nb = min(1.0, max(0.0, cpu_big / max_big))
    nm = min(1.0, max(0.0, cpu_mid / max_mid))
    nl = min(1.0, max(0.0, cpu_little / max_little))
    cpu_load = float(min(1.0, 0.60 * nb + 0.30 * nm + 0.10 * nl))

    gpu0 = _to_num(row.get("GPU0")) or 0.0
    gpu1 = _to_num(row.get("GPU1")) or 0.0
    max_gpu0 = 900_000.0
    max_gpu1 = 900_000.0
    ng = max(min(1.0, max(0.0, gpu0 / max_gpu0)), min(1.0, max(0.0, gpu1 / max_gpu1)))
    gpu_load = float(min(1.0, ng))

    # 网络：用 WIFI_data 近似（bytes），换算成 MB/s 后离散到 net_activity
    wifi_bytes = _to_num(row.get("WIFI_data"))
    wifi_bytes = 0.0 if wifi_bytes is None else max(0.0, float(wifi_bytes))
    wifi_rate_MBps = 0.0 if duration_s <= 0 else (wifi_bytes / duration_s / 1e6)

    # 观测吞吐（连续）：若可得，则作为 q(t) 的平均值输入，优先级高于离散 net_activity 映射。
    net_throughput_MBps = float(max(0.0, wifi_rate_MBps))

    if wifi_rate_MBps >= 0.30:
        net_activity = "video"
    elif wifi_rate_MBps >= 0.02:
        net_activity = "browse"
    else:
        net_activity = "idle"

    # radio_mode：AndroWatts 以 Wi-Fi 为主；若 Wi-Fi 无流量且蜂窝 rail 很高，可视为蜂窝
    cell_uW = _to_num(row.get("CELLULAR_ENERGY_AVG_UWS")) or 0.0
    wlan_uW = _to_num(row.get("WLANBT_ENERGY_AVG_UWS")) or 0.0
    radio_mode = "wifi" if (wifi_rate_MBps > 0.0 or wlan_uW >= cell_uW) else "lte"

    # GPS：若 GPS rail 非零则认为开启
    gps_uW = _to_num(row.get("GPS_ENERGY_AVG_UWS")) or 0.0
    gps_on = bool(gps_uW > 1000.0)  # 1mW 阈值，避免数值噪声

    # activity：用于叙事与屏幕 Markov（对本适配器影响很小）
    if gps_on:
        activity = "navigation"
    elif gpu_load >= 0.55:
        activity = "game"
    elif net_activity == "video":
        activity = "video"
    elif screen_on:
        activity = "browse"
    else:
        activity = "standby"

    # 后台强度：用“外设/后台 rail”功耗量级做粗分档（仅用于把公开数据映射到模型输入，不作为因果结论）。
    background_cols = [
        "UFS(Disk)_ENERGY_AVG_UWS",
        "Sensor_ENERGY_AVG_UWS",
        "Memory_ENERGY_AVG_UWS",
        "Memory_ENERGY_AVG_UWS.1",
        "Camera_ENERGY_AVG_UWS",
        "L21S_VDD2L_MEM_ENERGY_AVG_UWS",
        "S12S_VDD_AUR_ENERGY_AVG_UWS",
    ]
    p_bg_uW = _sum_cols_uW(row, background_cols)
    p_bg_W = float(p_bg_uW) * 1e-6
    # 阈值来自数据分布的经验分位（约 0.20/0.30W），避免把几乎所有点都分到同一档。
    if p_bg_W >= 0.30:
        background_level = "high"
    elif p_bg_W >= 0.20:
        background_level = "medium"
    else:
        background_level = "low"

    signal_quality = "good"

    return Segment(
        duration_s=float(duration_s),
        ambient_temp_c=float(temp_c),
        screen_on=bool(screen_on),
        brightness_nits=float(brightness_nits),
        screen_apl=float(apl),
        activity=str(activity),
        cpu_load=float(cpu_load),
        gpu_load=float(gpu_load),
        radio_mode=str(radio_mode),
        signal_quality=str(signal_quality),
        net_activity=str(net_activity),
        net_throughput_MBps=float(net_throughput_MBps),
        gps_on=bool(gps_on),
        background_level=str(background_level),
    )


def build_cases(
    df: pd.DataFrame,
    *,
    max_n: int | None = None,
    seed: int = 0,
    max_screen_nits: float = 500.0,
) -> list[AndroWattsCase]:
    """从 DataFrame 构造用于仿真的案例列表。"""

    if max_n is not None and int(max_n) > 0 and len(df) > int(max_n):
        df = df.sample(n=int(max_n), random_state=int(seed)).reset_index(drop=True)

    cases: list[AndroWattsCase] = []
    for _, row in df.iterrows():
        test_id = int(_to_num(row.get("ID")) or _to_num(row.get("phone_test_id")) or 0)
        dur = float(estimate_duration_s(row))
        obs = observed_power_from_row(row)

        soc0 = None
        if "BATTERY__PERCENT" in row.index:
            v = _to_num(row.get("BATTERY__PERCENT"))
            if v is not None:
                soc0 = float(max(0.0, min(1.0, v / 100.0)))

        temp_c = None
        if "AVG_SOC_TEMP" in row.index:
            v = _to_num(row.get("AVG_SOC_TEMP"))
            if v is not None:
                temp_c = float(v) / 1000.0

        seg = map_row_to_segment(row, duration_s=dur, max_screen_nits=float(max_screen_nits))
        cases.append(
            AndroWattsCase(
                test_id=int(test_id),
                duration_s=float(dur),
                soc0=soc0,
                temp_c=temp_c,
                segment=seg,
                obs=obs,
            )
        )
    return cases
