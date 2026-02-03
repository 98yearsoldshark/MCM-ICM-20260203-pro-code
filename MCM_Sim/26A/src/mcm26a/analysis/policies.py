"""策略库：用于“反事实/省电策略”评估的默认动作集合。"""

from __future__ import annotations

from mcm26a.scenarios import (
    disable_gps,
    force_radio_mode,
    set_background_level,
    set_brightness_for_screen_on,
    set_signal_quality,
)

from .model0_policy import PolicyAction


def default_policy_actions() -> list[PolicyAction]:
    """默认策略动作集合（可用于论文的反事实对比）。

    注意：
    - 这些动作是“理想化策略/反事实”定义，用于解释模型与做敏感性对比；
      不代表真实操作系统一定能在所有时刻做到（论文中需要说明这一点）。
    """

    return [
        PolicyAction(
            action_id="brightness_100",
            title_zh="降低亮度至 100 nits（仅屏幕点亮段）",
            description_zh="评估亮度下降带来的续航提升（对视频/游戏/导航通常显著）。",
            apply=lambda sc: set_brightness_for_screen_on(sc, brightness_nits=100.0),
        ),
        PolicyAction(
            action_id="disable_gps",
            title_zh="关闭 GPS",
            description_zh="评估 GPS 的边际耗电（对导航类场景显著）。",
            apply=disable_gps,
        ),
        PolicyAction(
            action_id="force_wifi",
            title_zh="强制使用 Wi-Fi（假设可用）",
            description_zh="对比 Wi-Fi 与蜂窝网络的能耗差异（现实中取决于 Wi-Fi 可用性）。",
            apply=lambda sc: force_radio_mode(sc, radio_mode="wifi"),
        ),
        PolicyAction(
            action_id="good_signal",
            title_zh="改善信号（poor -> good）",
            description_zh="用于解释“信号差导致异常耗电”的机理影响（现实中通常只能部分改善）。",
            apply=lambda sc: set_signal_quality(sc, signal_quality="good"),
        ),
        PolicyAction(
            action_id="bg_low",
            title_zh="限制后台（统一设为 low）",
            description_zh="评估后台活动的边际耗电（对待机/混合日常较显著）。",
            apply=lambda sc: set_background_level(sc, level="low"),
        ),
    ]

