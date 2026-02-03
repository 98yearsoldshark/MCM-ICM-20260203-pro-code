"""电池子模型：SOC/电压动力学，以及（可选）热效应与老化效应。"""

from .model0 import BatteryParams0
from .model1_ecm import BatteryParams1ECM, ECMOutput, ECMState, ecm_derivatives, solve_ecm_instantaneous
from .model1_ecm2rc import BatteryParams1ECM2RC, ECM2RCOutput, ECM2RCState, ecm2rc_derivatives, solve_ecm2rc_instantaneous
from .model2_thermal import BatteryParams2Thermal, ThermalECMOutput, ThermalECMState, thermal_ecm_derivatives
from .model3_aging import AgingECMOutput, AgingECMState, BatteryParams3Aging, aging_ecm_derivatives
from .ocv import PiecewiseLinearOCV

__all__ = [
    "BatteryParams0",
    "PiecewiseLinearOCV",
    "BatteryParams1ECM",
    "ECMState",
    "ECMOutput",
    "solve_ecm_instantaneous",
    "ecm_derivatives",
    "BatteryParams1ECM2RC",
    "ECM2RCState",
    "ECM2RCOutput",
    "solve_ecm2rc_instantaneous",
    "ecm2rc_derivatives",
    "BatteryParams2Thermal",
    "ThermalECMState",
    "ThermalECMOutput",
    "thermal_ecm_derivatives",
    "BatteryParams3Aging",
    "AgingECMState",
    "AgingECMOutput",
    "aging_ecm_derivatives",
]
