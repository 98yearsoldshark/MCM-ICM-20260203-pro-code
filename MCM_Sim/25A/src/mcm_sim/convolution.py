from __future__ import annotations

import numpy as np


def convolve2d_same(a: np.ndarray, k: np.ndarray) -> np.ndarray:
    """2D 卷积（same 模式），优先使用 scipy.signal.fftconvolve。

    说明：
    - 这里用 FFT 卷积是为了在长期仿真（很多天、较大网格）时保持速度可接受。
    - 结果为 float 数组。
    """

    a = np.asarray(a, dtype=float)
    k = np.asarray(k, dtype=float)

    try:
        from scipy.signal import fftconvolve  # type: ignore

        return fftconvolve(a, k, mode="same")
    except Exception:
        # scipy 不可用时的降级实现：numpy FFT
        # same 模式：通过 full 卷积再裁剪
        fa_shape = (a.shape[0] + k.shape[0] - 1, a.shape[1] + k.shape[1] - 1)
        fa = np.fft.rfftn(a, fa_shape)
        fk = np.fft.rfftn(k, fa_shape)
        full = np.fft.irfftn(fa * fk, fa_shape)

        ky, kx = k.shape
        start_y = (ky - 1) // 2
        start_x = (kx - 1) // 2
        end_y = start_y + a.shape[0]
        end_x = start_x + a.shape[1]
        return full[start_y:end_y, start_x:end_x]

