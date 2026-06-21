"""极值检测与潮汐表生成"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple


def find_extrema(
    times: List[datetime],
    heights: List[float],
) -> List[Dict]:
    """
    从潮位序列中找出所有局部极大和局部极小点

    使用三点比较法，加上抛物线插值以获得更精确的极值时间和高度

    返回按时间排序的极值列表，每个元素包含：
        time: datetime
        height: float
        type: "high" 或 "low"
    """
    if len(times) != len(heights):
        raise ValueError("times 和 heights 长度不一致")
    if len(times) < 3:
        return []

    extrema = []

    for i in range(1, len(times) - 1):
        h_prev = heights[i - 1]
        h_curr = heights[i]
        h_next = heights[i + 1]

        if h_prev is None or h_curr is None or h_next is None:
            continue
        if math.isnan(h_prev) or math.isnan(h_curr) or math.isnan(h_next):
            continue

        is_max = h_curr > h_prev and h_curr >= h_next
        is_min = h_curr < h_prev and h_curr <= h_next

        if not (is_max or is_min):
            continue

        t_prev = (times[i] - times[0]).total_seconds() / 3600.0
        t_curr = (times[i + 1] - times[0]).total_seconds() / 3600.0
        t_next = (times[i - 1] - times[0]).total_seconds() / 3600.0

        t0 = (times[i - 1] - times[0]).total_seconds() / 3600.0
        t1 = (times[i] - times[0]).total_seconds() / 3600.0
        t2 = (times[i + 1] - times[0]).total_seconds() / 3600.0
        y0 = h_prev
        y1 = h_curr
        y2 = h_next

        denom = (t0 - t1) * (t0 - t2) * (t1 - t2)
        if abs(denom) < 1e-12:
            continue

        A = (t2 * (y1 - y0) + t1 * (y0 - y2) + t0 * (y2 - y1)) / denom
        B = (t2 * t2 * (y0 - y1) + t1 * t1 * (y2 - y0) + t0 * t0 * (y1 - y2)) / denom
        C = (t1 * t2 * (t1 - t2) * y0 + t2 * t0 * (t2 - t0) * y1 + t0 * t1 * (t0 - t1) * y2) / denom

        if abs(A) < 1e-15:
            continue

        t_extreme = -B / (2 * A)
        h_extreme = C - B * B / (4 * A)

        if t_extreme < t0 or t_extreme > t2:
            t_extreme = t1
            h_extreme = h_curr

        actual_time = times[0] + timedelta(hours=t_extreme)
        extrema.append({
            "time": actual_time,
            "height": h_extreme,
            "type": "high" if is_max else "low",
        })

    return _clean_extrema(extrema)


def _clean_extrema(extrema: List[Dict]) -> List[Dict]:
    """
    清理极值列表，确保：
    1. 高低潮交替出现
    2. 同一采样点不会同时标为高潮和低潮
    3. 过于接近的重复极值被合并
    """
    if len(extrema) < 2:
        return extrema

    extrema.sort(key=lambda x: x["time"])

    cleaned = []
    for ex in extrema:
        if not cleaned:
            cleaned.append(ex)
            continue

        last = cleaned[-1]
        dt = (ex["time"] - last["time"]).total_seconds() / 60.0

        if dt < 1.0:
            continue

        if ex["type"] == last["type"]:
            if ex["type"] == "high":
                if ex["height"] > last["height"]:
                    cleaned[-1] = ex
            else:
                if ex["height"] < last["height"]:
                    cleaned[-1] = ex
        else:
            cleaned.append(ex)

    result = []
    for ex in cleaned:
        if result and ex["type"] == result[-1]["type"]:
            if ex["type"] == "high":
                if ex["height"] > result[-1]["height"]:
                    result[-1] = ex
            else:
                if ex["height"] < result[-1]["height"]:
                    result[-1] = ex
        else:
            result.append(ex)

    return result


def generate_tide_table(extrema: List[Dict]) -> List[Dict]:
    """
    将极值列表整理为每日潮汐表

    返回按日期分组的潮汐表，每天包含高潮和低潮列表
    """
    daily = {}

    for ex in extrema:
        date_key = ex["time"].date().isoformat()
        if date_key not in daily:
            daily[date_key] = {"date": date_key, "highs": [], "lows": []}

        entry = {
            "time": ex["time"].isoformat(),
            "height": round(ex["height"], 4),
        }

        if ex["type"] == "high":
            daily[date_key]["highs"].append(entry)
        else:
            daily[date_key]["lows"].append(entry)

    table = []
    for date_key in sorted(daily.keys()):
        day = daily[date_key]
        day["highs"].sort(key=lambda x: x["time"])
        day["lows"].sort(key=lambda x: x["time"])
        table.append(day)

    return table
