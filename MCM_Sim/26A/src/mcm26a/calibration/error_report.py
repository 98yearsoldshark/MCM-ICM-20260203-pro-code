"""误差报表（JSON 友好）：用于校准/验证阶段的统一对比输出。

目标：
- 把“看曲线觉得还行/不行”的主观判断，变成可复现的指标集合；
- 支持按 step、按电压区间、按休止段早/晚等维度分解误差结构；
- 输出结果可直接写入 JSON，用于后续自动化对比与画图。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .calce_channel import CalceChannelTimeSeries


@dataclass(frozen=True)
class ErrorSummary:
    n: int
    rmse_V: float
    mae_V: float

    def as_dict(self) -> dict[str, float | int]:
        return {"n": int(self.n), "rmse_mV": float(self.rmse_V) * 1000.0, "mae_mV": float(self.mae_V) * 1000.0}


def _rmse(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean(x * x))) if len(x) else float("nan")


def _mae(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.mean(np.abs(x))) if len(x) else float("nan")


def summarize_errors(err: np.ndarray, mask: np.ndarray | None = None) -> ErrorSummary:
    e = np.asarray(err, dtype=float)
    if mask is not None:
        m = np.asarray(mask, dtype=bool)
        e = e[m]
    return ErrorSummary(n=int(len(e)), rmse_V=_rmse(e), mae_V=_mae(e))


def _iter_segments(mask: np.ndarray) -> list[tuple[int, int]]:
    """把布尔 mask 的 True 区间提取为 [start,end) 段。"""

    m = np.asarray(mask, dtype=bool)
    if len(m) == 0:
        return []
    segs: list[tuple[int, int]] = []
    in_seg = False
    start = 0
    for i, v in enumerate(m):
        if v and not in_seg:
            in_seg = True
            start = i
        elif (not v) and in_seg:
            in_seg = False
            segs.append((start, i))
    if in_seg:
        segs.append((start, len(m)))
    return segs


def build_voltage_error_report(
    ts: CalceChannelTimeSeries,
    *,
    v_pred_V: np.ndarray,
    rest_i_thresh_A: float = 0.02,
    rest_window_s: float = 600.0,
    voltage_bands_V: tuple[tuple[float, float], ...] = ((4.2, 3.8), (3.8, 3.3), (3.3, 0.0)),
    v_cut_V: float | None = None,
    discharge_i_thresh_A: float = 0.1,
) -> dict:
    """生成“电压预测误差”报表（JSON 可序列化）。"""

    v_pred = np.asarray(v_pred_V, dtype=float)
    if len(v_pred) != len(ts.v_V):
        raise ValueError("v_pred_V 与 ts.v_V 长度不一致")

    err = v_pred - np.asarray(ts.v_V, dtype=float)

    report: dict = {
        "overall": summarize_errors(err).as_dict(),
        "by_step": {},
        "by_voltage_band": [],
        "rest_segments": {},
        "phone_domain": {},
        "meta": {
            "rest_i_thresh_A": float(rest_i_thresh_A),
            "rest_window_s": float(rest_window_s),
            "voltage_bands_V": [[float(hi), float(lo)] for hi, lo in voltage_bands_V],
            "v_cut_V": (float(v_cut_V) if v_cut_V is not None else None),
            "discharge_i_thresh_A": float(discharge_i_thresh_A),
        },
    }

    # 1) 按 step 分解
    steps = np.asarray(ts.step, dtype=int)
    for sid in sorted(set(int(x) for x in steps.tolist())):
        m = steps == int(sid)
        report["by_step"][str(int(sid))] = summarize_errors(err, m).as_dict()

    # 2) 按电压区间分解（用观测电压分箱，避免预测偏差导致错箱）
    v_meas = np.asarray(ts.v_V, dtype=float)
    for hi, lo in voltage_bands_V:
        m = (v_meas <= float(hi)) & (v_meas > float(lo))
        if int(np.sum(m)) == 0:
            continue
        report["by_voltage_band"].append(
            {
                "band": [float(lo), float(hi)],
                **summarize_errors(err, m).as_dict(),
            }
        )

    # 3) 休止段误差：全体/早期/晚期
    i = np.asarray(ts.i_A, dtype=float)
    rest_mask = np.abs(i) <= float(rest_i_thresh_A)
    segs = _iter_segments(rest_mask)
    if segs:
        rest_all = np.zeros_like(rest_mask, dtype=bool)
        rest_early = np.zeros_like(rest_mask, dtype=bool)
        rest_late = np.zeros_like(rest_mask, dtype=bool)

        t = np.asarray(ts.t_s, dtype=float)
        w = float(rest_window_s)

        for a, b in segs:
            rest_all[a:b] = True
            t0 = float(t[a])
            t1 = float(t[b - 1])
            rest_early[a:b] |= (t[a:b] <= t0 + w)
            rest_late[a:b] |= (t[a:b] >= t1 - w)

        report["rest_segments"] = {
            "rest_all": summarize_errors(err, rest_all).as_dict(),
            "rest_early": summarize_errors(err, rest_early).as_dict(),
            "rest_late": summarize_errors(err, rest_late).as_dict(),
            "n_segments": int(len(segs)),
        }

    # 4) “手机工作域”误差：以 V_cut 为准，重点评估“到关机/截止之前”的拟合质量与 TTE 偏差。
    # 说明：
    # - 公开电池数据常包含“深度放电到 2.5V”等片段，但手机通常在更高电压触发保护/关机（例如 ~3.3V）。
    # - 若把深度放电段纳入 overall，会把模型评价“拉偏”，导致出现看似变差但其实更贴近手机场景的参数。
    if v_cut_V is not None:
        v_cut = float(v_cut_V)
        i_dis = float(discharge_i_thresh_A)

        t = np.asarray(ts.t_s, dtype=float)
        t0 = float(t[0]) if len(t) else 0.0
        t_rel = t - t0
        i = np.asarray(ts.i_A, dtype=float)
        v_meas = np.asarray(ts.v_V, dtype=float)

        def _first_cut_time(v: np.ndarray) -> float | None:
            m = (i >= i_dis) & (v <= v_cut)
            if not bool(np.any(m)):
                return None
            k = int(np.argmax(m))
            return float(t_rel[k])

        t_cut_meas = _first_cut_time(v_meas)
        t_cut_pred = _first_cut_time(v_pred)

        # 若未触发 cutoff，则用全时长作为“可用续航”
        dur = float(t_rel[-1]) if len(t_rel) else 0.0
        tte_meas = float(dur if t_cut_meas is None else t_cut_meas)
        tte_pred = float(dur if t_cut_pred is None else t_cut_pred)

        mask_until_cut = t_rel <= float(tte_meas)
        mask_until_cut_above = mask_until_cut & (v_meas >= v_cut)

        report["phone_domain"] = {
            "v_cut_V": float(v_cut),
            "discharge_i_thresh_A": float(i_dis),
            "t_cut_meas_s": (None if t_cut_meas is None else float(t_cut_meas)),
            "t_cut_pred_s": (None if t_cut_pred is None else float(t_cut_pred)),
            "tte_meas_s": float(tte_meas),
            "tte_pred_s": float(tte_pred),
            "tte_error_s": float(tte_pred - tte_meas),
            "overall_until_cutoff": summarize_errors(err, mask_until_cut).as_dict(),
            "overall_until_cutoff_above_vcut": summarize_errors(err, mask_until_cut_above).as_dict(),
        }

    return report
