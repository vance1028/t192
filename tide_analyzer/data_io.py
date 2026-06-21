"""数据读写：CSV/JSON 格式，缺测处理"""

import csv
import json
import math
from datetime import datetime
from typing import List, Dict, Tuple


def read_observation_csv(filepath: str) -> Tuple[List[datetime], List[float], List[Dict]]:
    """
    读取潮位观测 CSV 文件

    CSV 格式要求:
        - 两列: time, height
        - time 为 ISO 格式时间字符串
        - height 为数值，空值或 "NaN" 表示缺测

    返回:
        (times, heights, missing_records)
        missing_records 为缺测行信息列表
    """
    times = []
    heights = []
    missing_records = []

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if "time" not in reader.fieldnames or "height" not in reader.fieldnames:
            raise ValueError("CSV 文件必须包含 time 和 height 列")

        for i, row in enumerate(reader, start=2):
            time_str = row.get("time", "").strip()
            height_str = row.get("height", "").strip()

            if not time_str:
                missing_records.append({
                    "row": i,
                    "reason": "time 为空",
                })
                continue

            try:
                t = datetime.fromisoformat(time_str)
            except (ValueError, TypeError):
                missing_records.append({
                    "row": i,
                    "time": time_str,
                    "reason": "时间格式错误",
                })
                continue

            if not height_str or height_str.lower() in ("nan", "na", "null", "none", ""):
                times.append(t)
                heights.append(float("nan"))
                missing_records.append({
                    "row": i,
                    "time": time_str,
                    "reason": "潮位缺测",
                })
                continue

            try:
                h = float(height_str)
                times.append(t)
                heights.append(h)
            except (ValueError, TypeError):
                times.append(t)
                heights.append(float("nan"))
                missing_records.append({
                    "row": i,
                    "time": time_str,
                    "height_raw": height_str,
                    "reason": "潮位数值错误",
                })

    return times, heights, missing_records


def write_forecast_csv(filepath: str, times: List[datetime], heights: List[float]) -> None:
    """写入预测潮位 CSV"""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "height"])
        for t, h in zip(times, heights):
            writer.writerow([t.isoformat(), f"{h:.4f}"])


def write_tide_table_csv(filepath: str, table: List[Dict]) -> None:
    """写入潮汐表 CSV"""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "type", "time", "height"])
        for day in table:
            for entry in day.get("highs", []):
                writer.writerow([day["date"], "high", entry["time"], entry["height"]])
            for entry in day.get("lows", []):
                writer.writerow([day["date"], "low", entry["time"], entry["height"]])


def read_model_json(filepath: str) -> Dict:
    """读取模型 JSON 文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def write_model_json(filepath: str, model: Dict) -> None:
    """写入模型 JSON 文件"""
    def _convert(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, float) and math.isnan(obj):
            return None
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2, ensure_ascii=False, default=_convert)


def write_json(filepath: str, data) -> None:
    """通用 JSON 写入"""
    def _convert(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, float) and math.isnan(obj):
            return None
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=_convert)
