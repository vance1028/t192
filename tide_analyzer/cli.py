"""命令行接口"""

import argparse
import math
import sys
from datetime import datetime, timedelta

from .tidal import fit_tide, predict_tide, COMMON_CONSTITUENTS
from .extremes import find_extrema, generate_tide_table
from .data_io import (
    read_observation_csv,
    write_forecast_csv,
    write_tide_table_csv,
    read_model_json,
    write_model_json,
    write_json,
)
from .sample_gen import generate_sample_data


def _parse_constituents(constituents_str: str) -> list:
    """解析分潮名称列表字符串"""
    if not constituents_str:
        return ["M2", "S2", "K1", "O1"]
    names = [s.strip() for s in constituents_str.split(",") if s.strip()]
    for name in names:
        if name not in COMMON_CONSTITUENTS:
            raise ValueError(f"未知分潮: {name}。可用分潮: {', '.join(COMMON_CONSTITUENTS.keys())}")
    return names


def cmd_fit(args):
    """拟合子命令"""
    print(f"读取观测数据: {args.input}")
    times, heights, missing_records = read_observation_csv(args.input)
    print(f"  共 {len(times)} 条记录，缺测 {len(missing_records)} 条")

    if missing_records:
        print(f"  缺测记录已跳过，详情见输出文件")

    const_names = _parse_constituents(args.constituents)
    print(f"  拟合分潮: {', '.join(const_names)}")

    try:
        model = fit_tide(times, heights, const_names)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    model["missing_records"] = missing_records

    print(f"\n=== 拟合结果 ===")
    print(f"平均海平面 (Z0): {model['z0']:.4f} m")
    print(f"有效观测点: {model['n_valid']}")
    print(f"缺测点: {model['n_missing']}")
    print(f"RMSE: {model['rmse']:.4f} m")
    print(f"R²: {model['r_squared']:.4f}")

    print(f"\n分潮常数:")
    print(f"{'名称':<8} {'振幅 (m)':<12} {'相位 (°)':<12} {'角频率 (rad/h)':<18}")
    print("-" * 52)
    for name in model["constituent_names"]:
        c = model["constituents"][name]
        print(f"{name:<8} {c['amplitude']:<12.4f} {c['phase_deg']:<12.2f} {c['omega']:<18.6f}")

    if args.output:
        model_out = {k: v for k, v in model.items() if k != "missing_records"}
        model_out["missing_records"] = missing_records
        write_model_json(args.output, model_out)
        print(f"\n模型已保存到: {args.output}")

    if args.missing_report:
        write_json(args.missing_report, {"n_missing": len(missing_records), "records": missing_records})
        print(f"缺测报告已保存到: {args.missing_report}")


def cmd_forecast(args):
    """预测子命令"""
    print(f"读取模型: {args.model}")
    model = read_model_json(args.model)

    start_time = datetime.fromisoformat(args.start)
    duration_hours = args.days * 24
    interval_hours = args.interval

    n_points = int(duration_hours / interval_hours) + 1
    times = [start_time + timedelta(hours=i * interval_hours) for i in range(n_points)]

    print(f"预测时段: {times[0]} ~ {times[-1]}")
    print(f"采样间隔: {interval_hours} 小时，共 {n_points} 个点")

    heights = predict_tide(times, model)

    if args.output:
        write_forecast_csv(args.output, times, heights)
        print(f"预测结果已保存到: {args.output}")

    if args.format == "json":
        json_path = args.output.replace(".csv", ".json") if args.output else "forecast.json"
        data = {
            "start_time": times[0].isoformat(),
            "end_time": times[-1].isoformat(),
            "interval_hours": interval_hours,
            "n_points": n_points,
            "times": [t.isoformat() for t in times],
            "heights": [round(h, 4) for h in heights],
        }
        write_json(json_path, data)
        print(f"JSON 结果已保存到: {json_path}")


def cmd_table(args):
    """潮汐表子命令"""
    print(f"读取模型: {args.model}")
    model = read_model_json(args.model)

    start_time = datetime.fromisoformat(args.start)
    end_time = start_time + timedelta(days=args.days)

    print(f"生成潮汐表: {start_time.date()} ~ {end_time.date()} ({args.days} 天)")

    sample_interval = 0.1
    duration_hours = args.days * 24 + 24
    n_points = int(duration_hours / sample_interval) + 1
    times = [start_time - timedelta(hours=12) + timedelta(hours=i * sample_interval) for i in range(n_points)]

    heights = predict_tide(times, model)

    extrema = find_extrema(times, heights)
    print(f"找到 {len(extrema)} 个极值点")

    start_date = start_time.date()
    end_date = (start_time + timedelta(days=args.days)).date()
    extrema_filtered = [
        ex for ex in extrema
        if start_date <= ex["time"].date() < end_date
    ]
    print(f"  其中 {len(extrema_filtered)} 个在指定日期范围内")

    table = generate_tide_table(extrema_filtered)

    if args.output:
        write_tide_table_csv(args.output, table)
        print(f"潮汐表 (CSV) 已保存到: {args.output}")

    if args.json_output:
        write_json(args.json_output, {"tide_table": table})
        print(f"潮汐表 (JSON) 已保存到: {args.json_output}")

    print(f"\n=== 潮汐表 ===")
    for day in table:
        print(f"\n{day['date']}:")
        for entry in day.get("highs", []):
            t = datetime.fromisoformat(entry["time"])
            print(f"  高潮: {t.strftime('%H:%M:%S')}  {entry['height']:.4f} m")
        for entry in day.get("lows", []):
            t = datetime.fromisoformat(entry["time"])
            print(f"  低潮: {t.strftime('%H:%M:%S')}  {entry['height']:.4f} m")


def cmd_generate_sample(args):
    """生成样本数据子命令"""
    print("生成样本数据...")

    start_time = datetime.fromisoformat(args.start)
    const_names = _parse_constituents(args.constituents)

    const_params = {}
    amps = [1.2, 0.4, 0.3, 0.25, 0.15, 0.1, 0.08, 0.06, 0.05, 0.04]
    phases = [45.0, 120.0, 80.0, 200.0, 30.0, 160.0, 90.0, 220.0, 60.0, 180.0]
    for i, name in enumerate(const_names):
        const_params[name] = {
            "amplitude": args.amplitude_scale * amps[i % len(amps)],
            "phase_deg": phases[i % len(phases)],
        }

    times, heights, meta = generate_sample_data(
        start_time=start_time,
        duration_hours=args.days * 24,
        interval_hours=args.interval,
        z0=args.z0,
        constituent_params=const_params,
        noise_std=args.noise,
        missing_fraction=args.missing,
        seed=args.seed,
    )

    if args.output:
        import csv
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "height"])
            for t, h in zip(times, heights):
                if math.isnan(h):
                    writer.writerow([t.isoformat(), "NaN"])
                else:
                    writer.writerow([t.isoformat(), f"{h:.4f}"])
        print(f"观测数据已保存到: {args.output}")

    if args.meta_output:
        write_json(args.meta_output, meta)
        print(f"元数据已保存到: {args.meta_output}")

    print(f"\n=== 样本数据信息 ===")
    print(f"起始时间: {meta['start_time']}")
    print(f"时长: {meta['duration_hours']} 小时")
    print(f"采样间隔: {meta['interval_hours']} 小时")
    print(f"总点数: {meta['n_points']}")
    print(f"缺测点: {meta['n_missing']} ({meta['missing_fraction']*100:.1f}%)")
    print(f"噪声标准差: {meta['noise_std']} m")
    print(f"平均海平面: {meta['z0']} m")
    print(f"\n分潮参数:")
    for name, params in meta["constituents"].items():
        print(f"  {name}: 振幅={params['amplitude']:.4f} m, 相位={params['phase_deg']:.2f}°")


def main():
    parser = argparse.ArgumentParser(
        prog="tide-analyzer",
        description="离线潮汐调和分析与预测工具",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # fit
    fit_parser = subparsers.add_parser("fit", help="从观测数据拟合潮汐调和常数")
    fit_parser.add_argument("-i", "--input", required=True, help="观测 CSV 文件路径")
    fit_parser.add_argument("-o", "--output", help="输出模型 JSON 文件路径")
    fit_parser.add_argument("-c", "--constituents", default="M2,S2,K1,O1",
                            help="分潮名称，逗号分隔 (默认: M2,S2,K1,O1)")
    fit_parser.add_argument("--missing-report", help="缺测记录报告输出路径")
    fit_parser.set_defaults(func=cmd_fit)

    # forecast
    forecast_parser = subparsers.add_parser("forecast", help="用模型预测潮位序列")
    forecast_parser.add_argument("-m", "--model", required=True, help="模型 JSON 文件路径")
    forecast_parser.add_argument("-o", "--output", help="输出预测 CSV 文件路径")
    forecast_parser.add_argument("-s", "--start", required=True, help="预测起始时间 (ISO 格式)")
    forecast_parser.add_argument("-d", "--days", type=int, default=7, help="预测天数 (默认: 7)")
    forecast_parser.add_argument("--interval", type=float, default=1.0, help="采样间隔小时数 (默认: 1.0)")
    forecast_parser.add_argument("--format", default="csv", choices=["csv", "json", "both"],
                                 help="输出格式 (默认: csv)")
    forecast_parser.set_defaults(func=cmd_forecast)

    # table
    table_parser = subparsers.add_parser("table", help="生成每日高潮低潮表")
    table_parser.add_argument("-m", "--model", required=True, help="模型 JSON 文件路径")
    table_parser.add_argument("-o", "--output", help="输出潮汐表 CSV 文件路径")
    table_parser.add_argument("-s", "--start", required=True, help="起始日期 (ISO 格式)")
    table_parser.add_argument("-d", "--days", type=int, default=7, help="天数 (默认: 7)")
    table_parser.add_argument("--json-output", help="JSON 格式潮汐表输出路径")
    table_parser.set_defaults(func=cmd_table)

    # generate-sample
    gen_parser = subparsers.add_parser("generate-sample", help="生成带噪声和缺测的样本观测数据")
    gen_parser.add_argument("-o", "--output", required=True, help="输出样本 CSV 文件路径")
    gen_parser.add_argument("-s", "--start", default="2025-01-01T00:00:00",
                            help="起始时间 (默认: 2025-01-01T00:00:00)")
    gen_parser.add_argument("-d", "--days", type=int, default=30, help="天数 (默认: 30)")
    gen_parser.add_argument("--interval", type=float, default=1.0,
                            help="采样间隔小时数 (默认: 1.0)")
    gen_parser.add_argument("-c", "--constituents", default="M2,S2,K1,O1",
                            help="分潮名称，逗号分隔 (默认: M2,S2,K1,O1)")
    gen_parser.add_argument("--z0", type=float, default=0.0, help="平均海平面 (默认: 0.0)")
    gen_parser.add_argument("--amplitude-scale", type=float, default=1.0,
                            help="振幅缩放系数 (默认: 1.0)")
    gen_parser.add_argument("--noise", type=float, default=0.05,
                            help="高斯噪声标准差 (默认: 0.05)")
    gen_parser.add_argument("--missing", type=float, default=0.02,
                            help="缺测比例 (默认: 0.02)")
    gen_parser.add_argument("--seed", type=int, default=42, help="随机数种子 (默认: 42)")
    gen_parser.add_argument("--meta-output", help="元数据 JSON 输出路径")
    gen_parser.set_defaults(func=cmd_generate_sample)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
