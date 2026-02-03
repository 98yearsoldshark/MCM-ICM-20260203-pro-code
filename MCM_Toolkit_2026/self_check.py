# -*- coding: utf-8 -*-
# MCM_Toolkit_2026 自检脚本（Smoke Tests）
#
# 目标：
# - 快速验证：依赖可用、语法无误、核心模块可跑通（无外部数据/无网络）
#
# 使用：
#   python MCM_Toolkit_2026/self_check.py
#
# 说明：
# - 这是“冒烟测试”，不追求覆盖全部算法的最优性/正确性证明
# - 可选依赖（xgboost/lightgbm/imbalanced-learn/jieba/tensorflow 等）不作为必检项

from __future__ import annotations

import compileall
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_TOOLKIT_ROOT = Path(__file__).resolve().parent
_PROJECT_ROOT = _TOOLKIT_ROOT.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str = ""


def _require_imports() -> None:
    import numpy  # noqa: F401
    import openpyxl  # noqa: F401
    import pandas  # noqa: F401
    import scipy  # noqa: F401
    import sklearn  # noqa: F401
    import statsmodels  # noqa: F401


def _compile_all(toolkit_root: Path) -> None:
    ok = compileall.compile_dir(str(toolkit_root), quiet=1)
    if not ok:
        raise RuntimeError("compileall 失败：存在语法错误或无法编译的文件。")


def _check_data_process() -> None:
    from MCM_Toolkit_2026.c01_数据处理_DataProcess.interpolation import solve as solve_interp
    from MCM_Toolkit_2026.c01_数据处理_DataProcess.outlier_detection import solve as solve_outlier
    from MCM_Toolkit_2026.c01_数据处理_DataProcess.robust_pca import solve as solve_rpca

    x = np.linspace(0, 1, 6)
    y = np.sin(2 * np.pi * x)
    out = solve_interp({"x": x, "y": y, "x_new": np.linspace(0, 1, 11)}, {"method": "linear"})
    assert "y_new" in out and len(out["y_new"]) == 11

    vec = np.array([1, 2, 3, 100, 4, 5], dtype=float)
    out2 = solve_outlier({"kind": "grubbs", "x": vec}, {"alpha": 0.05})
    assert "outlier_index" in out2

    X = np.eye(6) + 0.05 * np.random.default_rng(0).normal(size=(6, 6))
    out3 = solve_rpca(X, {"lambda": 1.0 / np.sqrt(max(X.shape)), "max_iter": 200})
    assert "L" in out3 and "S" in out3


def _check_supervised_and_decision() -> None:
    from MCM_Toolkit_2026.c03_监督学习_Supervised.logistic_regression import solve as solve_lr
    from MCM_Toolkit_2026.c03_监督学习_Supervised.svm import solve as solve_svm
    from MCM_Toolkit_2026.c10_评价与决策_DecisionMaking.ahp import solve as solve_ahp
    from MCM_Toolkit_2026.c10_评价与决策_DecisionMaking.topsis import solve as solve_topsis

    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 5))
    y = (X[:, 0] - 0.5 * X[:, 1] + rng.normal(0, 0.5, size=200) > 0).astype(int)
    out = solve_lr((X, y), {"task": "classification"})
    assert "metrics" in out and "accuracy" in out["metrics"]

    out2 = solve_svm((X, y), {"task": "classification", "model_type": "svc"})
    assert "metrics" in out2 and "accuracy" in out2["metrics"]

    A = np.array(
        [
            [1, 1 / 3, 3],
            [3, 1, 5],
            [1 / 3, 1 / 5, 1],
        ],
        dtype=float,
    )
    out3 = solve_ahp(A, {"method": "eigen"})
    assert "weights" in out3 and np.isclose(float(np.sum(out3["weights"])), 1.0)

    Xdm = np.array([[80, 70, 90], [60, 85, 75], [75, 65, 80]], dtype=float)
    out4 = solve_topsis(Xdm, {"is_benefit": [True, True, True]})
    assert "score" in out4 and "rank" in out4


def _check_forecasting() -> None:
    from MCM_Toolkit_2026.c11_预测预报_Forecasting.arima import solve as solve_arima
    from MCM_Toolkit_2026.c11_预测预报_Forecasting.grey_gm11 import solve as solve_gm11
    from MCM_Toolkit_2026.c11_预测预报_Forecasting.markov_chain import solve as solve_markov
    from MCM_Toolkit_2026.c11_预测预报_Forecasting.hmm import solve as solve_hmm

    rng = np.random.default_rng(0)
    y = np.cumsum(rng.normal(size=60)) + 0.2 * np.arange(60)
    out = solve_arima(y, {"order": (1, 1, 1), "horizon": 3, "trend": "n"})
    assert "forecast" in out and len(out["forecast"]) == 3

    x0 = np.array([10, 12, 13, 16, 18, 21], dtype=float)
    out2 = solve_gm11(x0, {"horizon": 3})
    assert "x0_hat" in out2 and len(out2["x0_hat"]) == (len(x0) + 3)

    states = [0, 1, 1, 2, 1, 0, 0, 1]
    out3 = solve_markov(states, {"n_steps": 2})
    assert "P" in out3 and "next_dist" in out3

    # 离散 HMM：用一个极小例子验证 viterbi 可跑通
    data = {
        "observations": [0, 1, 2, 1, 0],
        "startprob": [0.6, 0.4],
        "transmat": [[0.7, 0.3], [0.4, 0.6]],
        "emission": {"type": "discrete", "B": [[0.5, 0.4, 0.1], [0.1, 0.3, 0.6]]},
    }
    out4 = solve_hmm(data, {"do_viterbi": True})
    assert "states" in out4 and len(out4["states"]) == len(data["observations"])


def _check_optimization_and_graph() -> None:
    from MCM_Toolkit_2026.c12_优化算法_Optimization.linear_programming import solve as solve_lp
    from MCM_Toolkit_2026.c12_优化算法_Optimization.milp import solve as solve_milp
    from MCM_Toolkit_2026.c12_优化算法_Optimization.quadratic_programming import solve as solve_qp
    from MCM_Toolkit_2026.c13_图论算法_GraphTheory.dijkstra import solve as solve_dijkstra
    from MCM_Toolkit_2026.c13_图论算法_GraphTheory.max_flow import solve as solve_max_flow
    from MCM_Toolkit_2026.c13_图论算法_GraphTheory.min_cost_max_flow import solve as solve_mcmf

    # LP: max x+y s.t. x<=2, y<=1, x,y>=0
    out = solve_lp({"c": [-1, -1], "A_ub": [[1, 0], [0, 1]], "b_ub": [2, 1], "bounds": [(0, None), (0, None)]})
    assert out["success"] is True and out["x"] is not None

    # 0-1 ILP
    out2 = solve_milp(
        {"c": [10, 7, 3], "A_ub": [[4, 3, 2]], "b_ub": [6], "bounds": [(0, 1), (0, 1), (0, 1)], "integrality": [1, 1, 1]},
        {"maximize": True},
    )
    assert out2["success"] is True and out2["x"] is not None

    # QP: min 1/2 x^T P x + q^T x, s.t. x>=0, x1+x2=1
    out3 = solve_qp(
        {"P": [[4.0, 1.0], [1.0, 2.0]], "q": [1.0, 1.0], "A_ub": [[-1.0, 0.0], [0.0, -1.0]], "b_ub": [0.0, 0.0], "A_eq": [[1.0, 1.0]], "b_eq": [1.0]},
        {"solver": "scipy"},
    )
    assert out3["success"] is True and out3["x"] is not None

    # Dijkstra
    edges = [(0, 1, 1.0), (1, 2, 2.0), (0, 2, 10.0)]
    out4 = solve_dijkstra({"n": 3, "edges": edges, "source": 0})
    assert out4["dist"][2] == 3.0

    # Max Flow（容量必须为整数）
    cap = np.array(
        [
            [0, 5, 3, 0, 0, 0],
            [0, 0, 0, 2, 0, 0],
            [0, 1, 0, 0, 4, 0],
            [0, 0, 1, 0, 3, 2],
            [0, 0, 0, 0, 0, 5],
            [0, 0, 0, 0, 0, 0],
        ],
        dtype=int,
    )
    out5 = solve_max_flow({"capacity": cap, "source": 0, "sink": 5})
    assert out5["flow_value"] >= 0

    # Min-Cost Max-Flow（LP 实现）
    edges2 = [
        (0, 1, 5, 3),
        (0, 2, 3, 6),
        (1, 3, 2, 8),
        (2, 1, 1, 2),
        (2, 4, 4, 2),
        (3, 2, 1, 1),
        (3, 4, 3, 4),
        (3, 5, 2, 10),
        (4, 5, 5, 2),
    ]
    out6 = solve_mcmf({"edges": edges2, "source": 0, "sink": 5})
    assert out6.get("success") is True and out6.get("max_flow_value") is not None


def _check_statistics_and_ode() -> None:
    from MCM_Toolkit_2026.c15_统计分析_Statistics.hypothesis_tests import solve as solve_tests
    from MCM_Toolkit_2026.c17_微分方程_DifferentialEquations.ode_ivp import solve as solve_ode

    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, size=30)
    b = rng.normal(0.2, 1, size=25)
    out = solve_tests((a, b), {"test": "ttest_ind"})
    assert "pvalue" in out["result"]

    def dy(t: float, y: np.ndarray) -> np.ndarray:
        return np.array([-0.5 * y[0]], dtype=float)

    t_eval = np.linspace(0, 5, 51)
    out2 = solve_ode({"fun": dy, "t_span": (0.0, 5.0), "y0": [1.0], "t_eval": t_eval})
    assert out2["success"] is True and out2["y"].shape == (1, len(t_eval))


def _check_xlsx_examples(toolkit_root: Path) -> None:
    import pandas as pd

    from MCM_Toolkit_2026.c03_监督学习_Supervised.logistic_regression import solve as solve_lr
    from MCM_Toolkit_2026.c10_评价与决策_DecisionMaking.grey_relational import solve as solve_gra
    from MCM_Toolkit_2026.c03_监督学习_Supervised.curve_fitting import solve as solve_fit

    credit = pd.read_excel(toolkit_root / "data_samples" / "folder6_logistic_credit.xlsx")
    credit = credit.copy()
    credit["Y"] = pd.to_numeric(credit["Y"], errors="coerce")
    credit = credit.dropna(subset=["Y"])
    X = credit[["X1", "X2", "X3"]]
    y = credit["Y"].astype(int)
    out = solve_lr((X, y), {"task": "classification"})
    assert "accuracy" in out["metrics"]

    gdp = pd.read_excel(toolkit_root / "data_samples" / "folder6_grey_gdp.xlsx")
    X = gdp.select_dtypes(include=["number"]).to_numpy()
    out2 = solve_gra(X, {"rho": 0.5})
    assert "grade" in out2

    growth = pd.read_excel(toolkit_root / "data_samples" / "folder5_curve_fitting_growth.xlsx")
    out3 = solve_fit(growth, {"x_col": "x", "y_col": "y", "model": "polynomial", "degree": 3})
    assert "metrics" in out3 and "r2" in out3["metrics"]


def _check_advanced_algorithms() -> None:
    # 进阶/少见算法：免疫/鱼群/QGA/MOPSO + GRNN/RBF/WNN（小规模冒烟）
    from MCM_Toolkit_2026.c08_神经网络_NeuralNetwork.grnn import solve as solve_grnn
    from MCM_Toolkit_2026.c08_神经网络_NeuralNetwork.rbf_network import solve as solve_rbf
    from MCM_Toolkit_2026.c08_神经网络_NeuralNetwork.wavelet_neural_network import solve as solve_wnn
    from MCM_Toolkit_2026.c12_优化算法_Optimization.artificial_fish_swarm_tsp import solve as solve_afsa
    from MCM_Toolkit_2026.c12_优化算法_Optimization.immune_algorithm import solve as solve_iga
    from MCM_Toolkit_2026.c12_优化算法_Optimization.mopso import solve as solve_mopso
    from MCM_Toolkit_2026.c12_优化算法_Optimization.quantum_genetic_algorithm import solve as solve_qga
    from MCM_Toolkit_2026.c10_评价与决策_DecisionMaking.matter_element import solve as solve_me

    rng = np.random.default_rng(0)

    # 免疫遗传算法：选 k 个点（用 bit 表示）
    n_bits = 20
    k = 5

    def obj_bin(x: np.ndarray) -> float:
        # toy objective：让前 5 位尽量为 1（最小化）
        return float(-np.sum(x[:5] == 1))

    out = solve_iga({"objective": obj_bin, "n_bits": n_bits, "n_ones": k}, {"pop_size": 25, "memory_size": 5, "generations": 20, "seed": 0})
    assert "best_x" in out and int(np.sum(out["best_x"])) == k

    # 人工鱼群 TSP
    coords = rng.uniform(0, 50, size=(12, 2))
    out2 = solve_afsa({"coords": coords}, {"fish_num": 8, "max_iter": 12, "try_number": 40, "visual": 6, "seed": 0})
    assert np.isfinite(float(out2["best_length"]))

    # QGA：小规模运行验证
    def qobj(x: np.ndarray) -> float:
        return float(np.sin(4 * np.pi * x[0]) * x[0] + np.sin(20 * np.pi * x[1]) * x[1])

    out3 = solve_qga({"objective": qobj, "bit_lengths": [10, 10], "bounds": [(-3.0, 12.1), (4.1, 5.8)]}, {"pop_size": 20, "generations": 40, "seed": 0})
    assert np.isfinite(float(out3["best_fitness"]))

    # MOPSO：ZDT1（小规模）
    def zdt1(x: np.ndarray) -> Tuple[float, float]:
        x = np.asarray(x, dtype=float).reshape(-1)
        f1 = float(x[0])
        g = 1.0 + 9.0 * float(np.mean(x[1:]))
        f2 = float(g * (1.0 - np.sqrt(f1 / g)))
        return f1, f2

    out4 = solve_mopso({"objective": zdt1, "bounds": [(0.0, 1.0)] * 5}, {"n_pop": 30, "n_rep": 40, "max_iter": 20, "seed": 0})
    assert out4["rep_costs"].ndim == 2

    # GRNN / RBF / WNN：小数据回归冒烟
    X = rng.uniform(-2, 2, size=(120, 2))
    y = np.sin(X[:, 0]) + 0.5 * np.cos(2 * X[:, 1]) + 0.05 * rng.normal(size=120)

    out5 = solve_grnn((X, y), {"sigma": 0.6, "random_state": 0})
    assert "mse" in out5["metrics"]

    out6 = solve_rbf((X, y), {"n_centers": 12, "random_state": 0})
    assert "mse" in out6["metrics"]

    # WNN：训练较慢，epochs 降到很小，只验证流程
    out7 = solve_wnn((X, y), {"n_hidden": 6, "epochs": 10, "random_state": 0, "normalize": True})
    assert "mse" in out7["metrics"]

    # 物元分析法：简单 2 指标 2 等级
    classical = np.array([[[0, 5], [5, 10]], [[0, 3], [3, 6]]], dtype=float)  # (2,2,2)
    X_obj = np.array([[2.0, 1.0], [8.0, 5.0]], dtype=float)
    out8 = solve_me({"X": X_obj, "classical_domains": classical, "weights": [0.5, 0.5], "grade_names": ["低", "高"]})
    assert len(out8["grade"]) == 2 and out8["kp"].shape == (2, 2)


def _check_folder10_additions() -> None:
    # 目录 10 新补齐：排队论/元胞自动机/移动平均
    from MCM_Toolkit_2026.c11_预测预报_Forecasting.moving_average import solve as solve_ma
    from MCM_Toolkit_2026.c14_仿真模拟_Simulation.queueing_models import solve as solve_queue
    from MCM_Toolkit_2026.c14_仿真模拟_Simulation.traffic_flow_nasch import solve as solve_nasch

    # moving average
    y = np.arange(10, dtype=float)
    out = solve_ma(y, {"windows": [3, 5], "modes": ["centered", "trailing"]})
    assert 3 in out["centered"] and 5 in out["trailing"]
    assert out["centered"][3].shape == y.shape

    # queueing: M/M/1/K
    out2 = solve_queue({"model": "mmck", "lambda_rate": 4.0, "mu_rate": 5.0, "servers": 1, "capacity": 10, "horizon": 200.0}, {"seed": 0})
    assert 0.0 <= out2["blocking_prob"] <= 1.0
    assert np.isfinite(out2["L"]) and np.isfinite(out2["W"])

    # queueing: repairman
    out3 = solve_queue({"model": "repairman", "repairmen": 2, "machines": 6, "mean_uptime": 1.0, "mean_repair": 0.4, "horizon": 200.0}, {"seed": 0})
    assert np.isclose(float(np.sum(out3["p_state"])), 1.0, atol=1e-2)

    # NaSch traffic flow
    out4 = solve_nasch({}, {"road_length": 100, "steps": 120, "burn_in": 30, "n_densities": 6, "seed": 0})
    assert out4["density"].shape == out4["flow"].shape == (6,)


def _run_check(name: str, fn: Callable[[], None]) -> CheckResult:
    try:
        fn()
        return CheckResult(name=name, ok=True)
    except Exception as e:
        tb = traceback.format_exc(limit=12)
        return CheckResult(name=name, ok=False, message=f"{e}\n{tb}")


def main(argv: Optional[List[str]] = None) -> int:
    _ = argv or []
    toolkit_root = Path(__file__).resolve().parent

    checks: List[Callable[[], None]] = [
        _require_imports,
        lambda: _compile_all(toolkit_root),
        _check_data_process,
        _check_supervised_and_decision,
        _check_forecasting,
        _check_optimization_and_graph,
        _check_statistics_and_ode,
        lambda: _check_xlsx_examples(toolkit_root),
        _check_advanced_algorithms,
        _check_folder10_additions,
    ]
    names = [
        "imports",
        "compileall",
        "data_process",
        "supervised_and_decision",
        "forecasting",
        "optimization_and_graph",
        "statistics_and_ode",
        "xlsx_examples",
        "advanced_algorithms",
        "folder10_additions",
    ]

    print("MCM_Toolkit_2026 self check")
    print("python =", sys.version.split()[0])
    print("toolkit_root =", toolkit_root)

    results: List[CheckResult] = []
    for name, fn in zip(names, checks):
        r = _run_check(name, fn)
        results.append(r)
        print(f"- {name}: {'OK' if r.ok else 'FAIL'}")
        if not r.ok:
            print(r.message)

    failed = [r for r in results if not r.ok]
    if failed:
        print(f"FAILED: {len(failed)}/{len(results)}")
        return 1
    print(f"ALL PASSED: {len(results)}/{len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
