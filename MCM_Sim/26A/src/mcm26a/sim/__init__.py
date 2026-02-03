"""仿真引擎：ODE 积分、事件终止与耗尽时间（TTE）计算。"""

from .model0 import SimResult0, simulate_model0
from .model1 import SimResult1, TraceResult1, simulate_model1_ecm, simulate_model1_ecm_trace
from .model2 import SimResult2, TraceResult2, simulate_model2_thermal, simulate_model2_thermal_trace
from .model3 import SimResult3, TraceResult3, simulate_model3_aging, simulate_model3_aging_trace

__all__ = [
    "SimResult0",
    "simulate_model0",
    "SimResult1",
    "simulate_model1_ecm",
    "TraceResult1",
    "simulate_model1_ecm_trace",
    "SimResult2",
    "simulate_model2_thermal",
    "TraceResult2",
    "simulate_model2_thermal_trace",
    "SimResult3",
    "simulate_model3_aging",
    "TraceResult3",
    "simulate_model3_aging_trace",
]
