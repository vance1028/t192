"""潮汐调和分析与预测引擎"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

from .least_squares import least_squares


COMMON_CONSTITUENTS = {
    "M2": 0.505870,
    "S2": 0.523599,
    "K1": 0.262516,
    "O1": 0.243395,
    "N2": 0.496395,
    "P1": 0.261084,
    "K2": 0.525051,
    "Q1": 0.233906,
    "M4": 1.011740,
    "MS4": 1.029509,
}


def datetime_to_hours(dt: datetime, t0: Optional[datetime] = None) -> float:
    """将 datetime 转换为相对于 t0 的小时数"""
    if t0 is None:
        t0 = datetime(2000, 1, 1)
    delta = dt - t0
    return delta.total_seconds() / 3600.0


def hours_to_datetime(hours: float, t0: Optional[datetime] = None) -> datetime:
    """将小时数转换回 datetime"""
    if t0 is None:
        t0 = datetime(2000, 1, 1)
    return t0 + timedelta(hours=hours)


def _build_design_matrix(times_hours: List[float], omegas: List[float]) -> List[List[float]]:
    """
    构建设计矩阵 A
    每行对应一个时刻，每列对应一个基函数
    列顺序: 1 (Z0), cos(ω1*t), sin(ω1*t), cos(ω2*t), sin(ω2*t), ...
    """
    n = len(times_hours)
    n_const = len(omegas)
    n_cols = 1 + 2 * n_const
    A = [[0.0] * n_cols for _ in range(n)]

    for i in range(n):
        t = times_hours[i]
        A[i][0] = 1.0
        for j in range(n_const):
            omega = omegas[j]
            A[i][1 + 2 * j] = math.cos(omega * t)
            A[i][2 + 2 * j] = math.sin(omega * t)

    return A


def fit_tide(
    times: List[datetime],
    heights: List[float],
    constituent_names: List[str],
) -> Dict:
    """
    从观测序列中拟合潮汐调和常数

    参数:
        times: 观测时间列表
        heights: 对应潮位列表
        constituent_names: 分潮名称列表（必须在 COMMON_CONSTITUENTS 中）

    返回:
        包含拟合结果的字典
    """
    if len(times) != len(heights):
        raise ValueError("times 和 heights 长度不一致")

    if len(times) == 0:
        raise ValueError("观测数据为空")

    valid_indices = [i for i, h in enumerate(heights) if h is not None and not math.isnan(h)]
    if len(valid_indices) == 0:
        raise ValueError("无有效观测数据")

    missing_count = len(heights) - len(valid_indices)

    t0 = times[0]
    times_hours = [datetime_to_hours(times[i], t0) for i in valid_indices]
    heights_valid = [heights[i] for i in valid_indices]

    omegas = []
    for name in constituent_names:
        if name not in COMMON_CONSTITUENTS:
            raise ValueError(f"未知分潮: {name}")
        omegas.append(COMMON_CONSTITUENTS[name])

    n_params = 1 + 2 * len(omegas)
    if len(times_hours) < n_params:
        raise ValueError(
            f"有效观测点数量 ({len(times_hours)}) 少于待求参数数量 ({n_params})。"
            f"至少需要 {n_params} 个有效观测点，建议至少为参数数量的 2-3 倍。"
        )

    if len(constituent_names) != len(set(constituent_names)):
        raise ValueError("分潮名称不能重复")

    A = _build_design_matrix(times_hours, omegas)

    try:
        x, residual_sum = least_squares(A, heights_valid)
    except ValueError as e:
        raise ValueError(f"最小二乘求解失败: {e}")

    z0 = x[0]
    constituents = {}
    for i, name in enumerate(constituent_names):
        ci = x[1 + 2 * i]
        si = x[2 + 2 * i]
        amplitude = math.sqrt(ci ** 2 + si ** 2)
        phase = math.atan2(si, ci)
        if phase < 0:
            phase += 2 * math.pi
        constituents[name] = {
            "amplitude": amplitude,
            "phase_rad": phase,
            "phase_deg": math.degrees(phase),
            "cos_coeff": ci,
            "sin_coeff": si,
            "omega": omegas[i],
        }

    n_valid = len(heights_valid)
    mean_height = sum(heights_valid) / n_valid
    total_variance = sum((h - mean_height) ** 2 for h in heights_valid)
    r_squared = 1.0 - residual_sum / total_variance if total_variance > 0 else 0.0
    rmse = math.sqrt(residual_sum / n_valid)

    return {
        "t0": t0.isoformat(),
        "z0": z0,
        "constituents": constituents,
        "n_observations": len(times),
        "n_valid": n_valid,
        "n_missing": missing_count,
        "residual_sum_squares": residual_sum,
        "rmse": rmse,
        "r_squared": r_squared,
        "constituent_names": list(constituent_names),
    }


def predict_tide(
    times: List[datetime],
    model: Dict,
) -> List[float]:
    """
    用拟合模型预测指定时刻的潮位

    参数:
        times: 预测时间列表
        model: fit_tide 返回的模型字典

    返回:
        潮位预测值列表
    """
    t0 = datetime.fromisoformat(model["t0"])
    z0 = model["z0"]
    constituents = model["constituents"]

    omegas = []
    amps = []
    phases = []
    for name in model["constituent_names"]:
        c = constituents[name]
        omegas.append(c["omega"])
        amps.append(c["amplitude"])
        phases.append(c["phase_rad"])

    results = []
    for t in times:
        t_hours = datetime_to_hours(t, t0)
        h = z0
        for i in range(len(omegas)):
            h += amps[i] * math.cos(omegas[i] * t_hours - phases[i])
        results.append(h)

    return results
