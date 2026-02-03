"""参数校准工具（参数估计）。"""

from .calce_channel import CalceChannelTimeSeries, extract_channel_time_series, load_calce_channel_xlsx
from .calce_ocv import CalceOCVFit, fit_ocv_from_low_current_discharge, load_calce_low_current_ocv_xlsx
from .calce_trace import CalceTimeSeries, extract_time_series, load_calce_low_current_ocv_xlsx as load_calce_df
from .error_report import ErrorSummary, build_voltage_error_report
from .ecm_current import ECMFitResult, iterative_calibrate_ocv_and_resistance
from .ecm_current_socdep import (
    ECMSOCDepFitResult,
    ECMSOCDepFitResultR0R1,
    fit_c1_and_r1_curve_given_r0,
    fit_r0_c1_and_r1_curve,
    fit_r0_curve_c1_and_r1_curve,
)
from .ecm2rc_current_socdep import (
    ECM2RCSOCDepFitResult,
    ECM2RCSOCDepTauFitResult,
    ECM2RCSOCDepTauR0CurveFitResult,
    fit_c1_c2_and_r1_r2_curves_given_r0,
    fit_r1_r2_curves_and_taus_given_r0,
    fit_r0_curve_and_r1_r2_curves_and_taus,
)
from .ecm2rc_current_const import ECM2RCConstFitResult, fit_2rc_const_given_r0
from .r0_estimator import R0Estimate, estimate_r0_from_rest_load_transitions

__all__ = [
    "CalceOCVFit",
    "load_calce_low_current_ocv_xlsx",
    "fit_ocv_from_low_current_discharge",
    "CalceTimeSeries",
    "load_calce_df",
    "extract_time_series",
    "CalceChannelTimeSeries",
    "load_calce_channel_xlsx",
    "extract_channel_time_series",
    "ErrorSummary",
    "build_voltage_error_report",
    "R0Estimate",
    "estimate_r0_from_rest_load_transitions",
    "ECMFitResult",
    "iterative_calibrate_ocv_and_resistance",
    "ECMSOCDepFitResult",
    "ECMSOCDepFitResultR0R1",
    "fit_r0_c1_and_r1_curve",
    "fit_c1_and_r1_curve_given_r0",
    "fit_r0_curve_c1_and_r1_curve",
    "ECM2RCSOCDepFitResult",
    "fit_c1_c2_and_r1_r2_curves_given_r0",
    "ECM2RCSOCDepTauFitResult",
    "fit_r1_r2_curves_and_taus_given_r0",
    "ECM2RCSOCDepTauR0CurveFitResult",
    "fit_r0_curve_and_r1_r2_curves_and_taus",
    "ECM2RCConstFitResult",
    "fit_2rc_const_given_r0",
]
