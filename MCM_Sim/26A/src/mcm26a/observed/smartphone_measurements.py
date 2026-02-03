"""SmartphoneMeasurements（Monsoon + iPerf）数据适配。

用途（对齐赛题 26A / Q2）：
- 提供“通信相关活动”的公开实测功耗量级（Monsoon 0.2s 采样）；
- 提供吞吐日志（iPerf），可估计单位数据能耗（J/MB），用于校验/解释网络功耗机理；
- 可把“平均功耗”粗略映射为“若该活动持续进行的等效 TTE”（长时间/续航层面的对照证据）。

注意：
- 该数据集是特定机型/特定实验条件的测量；这里只做“量级与相对关系”的对照，不做硬校准；
- zip 内还包含 Bluetooth/LTE 吞吐 xlsx，本项目默认不依赖 xlsx（避免额外依赖），因此本适配器
  主要使用 iPerf 的 txt（WiFi / WiFi Direct 相关）与 Monsoon 的 csv。
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MonsoonSummary:
    """单条 Monsoon 测试的功耗汇总（均值）。"""

    phone: str
    test: str
    mean_power_W: float
    duration_s: float
    n_samples: int


@dataclass(frozen=True)
class IperfSummary:
    """单条 iPerf 日志的吞吐汇总（均值）。"""

    phone: str
    test: str
    mean_mbps: float
    duration_s: float


def _monsoon_test_name_from_path(inner_path: str) -> tuple[str, str]:
    # SmartphoneMeasurements-main/Monsoon/<Phone>/<file>.csv
    parts = inner_path.split("/")
    if len(parts) < 4:
        raise ValueError(f"unexpected path: {inner_path}")
    phone = parts[-2]
    filename = parts[-1]
    if not filename.lower().endswith(".csv"):
        raise ValueError(f"unexpected filename: {filename}")
    test = filename[: -len(".csv")]
    return phone, test


def _iperf_test_name_from_path(inner_path: str) -> tuple[str, str]:
    # SmartphoneMeasurements-main/iPerf/<Phone>/<file>.txt
    parts = inner_path.split("/")
    if len(parts) < 4:
        raise ValueError(f"unexpected path: {inner_path}")
    phone = parts[-2]
    filename = parts[-1]
    if not filename.lower().endswith(".txt"):
        raise ValueError(f"unexpected filename: {filename}")
    test = filename[: -len(".txt")]
    return phone, test


def summarize_monsoon_csv_in_zip(z: zipfile.ZipFile, inner_path: str) -> MonsoonSummary:
    """读取 zip 内 Monsoon csv，返回平均功耗等摘要。"""

    phone, test = _monsoon_test_name_from_path(inner_path)

    with z.open(inner_path, "r") as bf:
        # 该数据集 csv 为 ASCII/UTF-8 文本
        tf = io.TextIOWrapper(bf, encoding="utf-8", newline="")
        header = tf.readline().strip()
        if not header:
            raise ValueError(f"empty csv: {inner_path}")
        # 期望列：Time (s), Main Avg Current (A), Main Avg Power (W), Main Avg Voltage (V)
        cols = [c.strip() for c in header.split(",")]
        try:
            t_idx = cols.index("Time (s)")
        except ValueError:
            t_idx = 0
        try:
            p_idx = cols.index("Main Avg Power (W)")
        except ValueError:
            # 兜底：默认第 3 列
            p_idx = 2

        s_p = 0.0
        n = 0
        t_last = 0.0
        for line in tf:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) <= max(t_idx, p_idx):
                continue
            try:
                t = float(parts[t_idx])
                p = float(parts[p_idx])
            except Exception:
                continue
            s_p += p
            n += 1
            t_last = t

    mean_p = float("nan") if n <= 0 else float(s_p / n)
    # 采样间隔约 0.2s，最后一个时间戳近似代表持续时间
    dur = float(t_last)
    return MonsoonSummary(phone=phone, test=test, mean_power_W=mean_p, duration_s=dur, n_samples=int(n))


def summarize_iperf_txt_in_zip(z: zipfile.ZipFile, inner_path: str) -> IperfSummary:
    """读取 zip 内 iPerf txt，返回平均吞吐（Mbps）与持续时间（s）。"""

    phone, test = _iperf_test_name_from_path(inner_path)

    with z.open(inner_path, "r") as bf:
        text = bf.read().decode("utf-8", errors="ignore")

    # 优先使用 “receiver” 汇总行（更稳定）
    # 例：[  5]   0.00-180.06 sec   570 MBytes  26.5 Mbits/sec                  receiver
    receiver_re = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*Mbits/sec\s+.*\breceiver\b", re.IGNORECASE)
    dur_re = re.compile(r"([0-9]+(?:\.[0-9]+)?)-([0-9]+(?:\.[0-9]+)?)\s*sec", re.IGNORECASE)

    mbps = None
    dur_s = None
    for line in text.splitlines()[::-1]:
        m = receiver_re.search(line)
        if m:
            try:
                mbps = float(m.group(1))
            except Exception:
                mbps = None
            m2 = dur_re.search(line)
            if m2:
                try:
                    dur_s = float(m2.group(2)) - float(m2.group(1))
                except Exception:
                    dur_s = None
            break

    # 若没有 receiver 行，则退化为取所有 interval 行的均值
    if mbps is None:
        vals: list[float] = []
        for line in text.splitlines():
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*Mbits/sec", line)
            if not m:
                continue
            try:
                vals.append(float(m.group(1)))
            except Exception:
                continue
        if vals:
            mbps = float(sum(vals) / len(vals))

    if dur_s is None:
        # 兜底：用最后一个区间
        for line in text.splitlines()[::-1]:
            m2 = dur_re.search(line)
            if m2:
                try:
                    dur_s = float(m2.group(2)) - float(m2.group(1))
                except Exception:
                    dur_s = None
                break

    return IperfSummary(phone=phone, test=test, mean_mbps=float("nan") if mbps is None else float(mbps), duration_s=float("nan") if dur_s is None else float(dur_s))


def load_smartphone_measurements_zip(zip_path: Path) -> tuple[list[MonsoonSummary], list[IperfSummary]]:
    """读取 SmartphoneMeasurements.zip 并返回 Monsoon 与 iPerf 的摘要列表。"""

    zpath = Path(zip_path)
    if not zpath.exists():
        raise FileNotFoundError(str(zpath))

    monsoon: list[MonsoonSummary] = []
    iperf: list[IperfSummary] = []

    with zipfile.ZipFile(str(zpath), "r") as z:
        for info in z.infolist():
            name = str(info.filename)
            if name.endswith("/") or info.file_size <= 0:
                continue
            if "/Monsoon/" in name and name.lower().endswith(".csv"):
                monsoon.append(summarize_monsoon_csv_in_zip(z, name))
            if "/iPerf/" in name and name.lower().endswith(".txt"):
                iperf.append(summarize_iperf_txt_in_zip(z, name))

    return monsoon, iperf
