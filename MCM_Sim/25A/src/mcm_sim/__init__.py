"""MCM wear forward simulation package.

这个包用于“正向生成磨损热力图”：
给定人流模型 + 接触模型 + 材料磨损系数 -> 输出磨损形貌（二维磨损深度场）。
"""

from .stair_wear_sim import solve  # noqa: F401

__all__ = ["solve"]

