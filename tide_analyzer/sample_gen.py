"""样本数据生成：根据给定分潮常数合成观测数据"""

import math
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

from .tidal import COMMON_CONSTITUENTS, datetime_to_hours


def generate_sample_data(
    start_time: datetime,
    duration_hours: int,
    interval_hours: float = 1.0,
    z0: float = 0.0,
    constituent_params: Dict[str, Dict[str, float]] = None,
    noise_std: float = 0.05,
    missing_fraction: float = 0.02,
    seed: int = None,
) -> Tuple[List[datetime], List[float], Dict]:
    """
    合成带噪声和缺测点的潮汐观测数据

    参数:
        start_time: 起始时间
        duration_hours: 总时长（小时）
        interval_hours: 采样间隔（小时）
        z0: 平均海平面
        constituent_params: 分潮参数字典 {name: {amplitude, phase_deg}}
        noise_std: 高斯噪声标准差
        missing_fraction: 缺测比例
        seed: 随机数种子

    返回:
        (times, heights, meta_info)
    """
    if seed is not None:
        random.seed(seed)

    if constituent_params is None:
        constituent_params = {
            "M2": {"amplitude": 1.2, "phase_deg": 45.0},
            "S2": {"amplitude": 0.4, "phase_deg": 120.0},
            "K1": {"amplitude": 0.3, "phase_deg": 80.0},
            "O1": {"amplitude": 0.25, "phase_deg": 200.0},
        }

    n_points = int(duration_hours / interval_hours) + 1
    times = [start_time + timedelta(hours=i * interval_hours) for i in range(n_points)]

    t0 = start_time
    omegas = []
    amps = []
    phases = []
    const_names = []
    for name, params in constituent_params.items():
        if name not in COMMON_CONSTITUENTS:
            raise ValueError(f"未知分潮: {name}")
        const_names.append(name)
        omegas.append(COMMON_CONSTITUENTS[name])
        amps.append(params["amplitude"])
        phases.append(math.radians(params["phase_deg"]))

    heights = []
    for t in times:
        t_hours = datetime_to_hours(t, t0)
        h = z0
        for i in range(len(omegas)):
            h += amps[i] * math.cos(omegas[i] * t_hours - phases[i])
        h += random.gauss(0, noise_std)
        heights.append(h)

    missing_indices = set()
    n_missing = int(n_points * missing_fraction)
    while len(missing_indices) < n_missing:
        idx = random.randint(0, n_points - 1)
        missing_indices.add(idx)

    for idx in missing_indices:
        heights[idx] = float("nan")

    meta = {
        "start_time": start_time.isoformat(),
        "duration_hours": duration_hours,
        "interval_hours": interval_hours,
        "z0": z0,
        "constituents": {
            name: {
                "amplitude": constituent_params[name]["amplitude"],
                "phase_deg": constituent_params[name]["phase_deg"],
                "omega": COMMON_CONSTITUENTS[name],
            }
            for name in const_names
        },
        "noise_std": noise_std,
        "missing_fraction": missing_fraction,
        "n_points": n_points,
        "n_missing": len(missing_indices),
        "seed": seed,
    }

    return times, heights, meta
