"""边界情况测试"""

from tide_analyzer.tidal import fit_tide
from tide_analyzer.sample_gen import generate_sample_data
from datetime import datetime

print("=" * 60)
print("测试1: 数据点太少 (3个点，5个参数)")
print("=" * 60)
times, heights, meta = generate_sample_data(
    start_time=datetime(2025, 1, 1),
    duration_hours=2,
    interval_hours=1,
    z0=0,
    constituent_params={"M2": {"amplitude": 1.0, "phase_deg": 0}},
    noise_std=0,
    missing_fraction=0,
    seed=42,
)
print(f"观测点数: {len(times)}")
try:
    model = fit_tide(times, heights, ["M2", "S2"])
    print("  应该报错但没报错")
except ValueError as e:
    print(f"  ✓ 正确报错: {e}")

print()
print("=" * 60)
print("测试2: 频率太接近 (M2 和 N2 频率接近，短时间内难以区分)")
print("=" * 60)
times, heights, meta = generate_sample_data(
    start_time=datetime(2025, 1, 1),
    duration_hours=12,
    interval_hours=1,
    z0=0,
    constituent_params={
        "M2": {"amplitude": 1.0, "phase_deg": 0},
        "N2": {"amplitude": 0.2, "phase_deg": 90},
    },
    noise_std=0,
    missing_fraction=0,
    seed=42,
)
print(f"观测点数: {len(times)}")
try:
    model = fit_tide(times, heights, ["M2", "N2"])
    print(f"  成功，但拟合结果偏离真实值较大:")
    print(f"    M2: {model['constituents']['M2']['amplitude']:.4f} (真实 1.0)")
    print(f"    N2: {model['constituents']['N2']['amplitude']:.4f} (真实 0.2)")
    print("  (注: 短时间内频率接近的分潮确实难以准确区分)")
except ValueError as e:
    print(f"  报错: {e}")

print()
print("=" * 60)
print("测试3: 全部缺测")
print("=" * 60)
times = [datetime(2025, 1, 1) + __import__("datetime").timedelta(hours=i) for i in range(10)]
heights = [float("nan")] * 10
try:
    model = fit_tide(times, heights, ["M2"])
    print("  应该报错但没报错")
except ValueError as e:
    print(f"  ✓ 正确报错: {e}")

print()
print("=" * 60)
print("测试4: 预测稳定性 - 同一段时间多次预测结果一致")
print("=" * 60)
times_full, heights_full, meta = generate_sample_data(
    start_time=datetime(2025, 1, 1),
    duration_hours=720,
    interval_hours=1,
    z0=0.5,
    constituent_params={
        "M2": {"amplitude": 1.2, "phase_deg": 45.0},
        "S2": {"amplitude": 0.4, "phase_deg": 120.0},
        "K1": {"amplitude": 0.3, "phase_deg": 80.0},
        "O1": {"amplitude": 0.25, "phase_deg": 200.0},
    },
    noise_std=0.02,
    missing_fraction=0.01,
    seed=42,
)
model = fit_tide(times_full, heights_full, ["M2", "S2", "K1", "O1"])

from tide_analyzer.tidal import predict_tide
forecast_times = [datetime(2025, 2, 1) + __import__("datetime").timedelta(hours=i) for i in range(24)]
pred1 = predict_tide(forecast_times, model)
pred2 = predict_tide(forecast_times, model)
if pred1 == pred2:
    print("  ✓ 两次预测结果完全一致")
else:
    diff = max(abs(a - b) for a, b in zip(pred1, pred2))
    print(f"  ✗ 预测结果不一致，最大差异: {diff}")

print()
print("=" * 60)
print("测试5: 极值点排序和交替性")
print("=" * 60)
from tide_analyzer.extremes import find_extrema
import math

sample_times = [datetime(2025, 1, 1) + __import__("datetime").timedelta(minutes=i * 6) for i in range(240)]
sample_heights = [
    math.sin(0.5 * i / 10) + 0.5 * math.sin(0.25 * i / 10)
    for i in range(len(sample_times))
]
extrema = find_extrema(sample_times, sample_heights)
print(f"找到 {len(extrema)} 个极值点")

sorted_ok = all(
    extrema[i]["time"] <= extrema[i + 1]["time"]
    for i in range(len(extrema) - 1)
)
print(f"  按时间排序: {'✓ 是' if sorted_ok else '✗ 否'}")

alternating = True
for i in range(len(extrema) - 1):
    if extrema[i]["type"] == extrema[i + 1]["type"]:
        alternating = False
        print(f"  相邻极值类型相同: {i}和{i+1}都是{extrema[i]['type']}")
        break
print(f"  高低潮交替: {'✓ 是' if alternating else '✗ 否'}")

print()
print("所有测试完成!")
