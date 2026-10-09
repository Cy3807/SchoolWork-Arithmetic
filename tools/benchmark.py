"""同候选序列对照查重方式，测生成、写入、批改并保存剖析数据。"""

import cProfile
import json
import platform
import pstats
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quiz.files import grade_files, write_batch
from quiz.generate import generate


def main():
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    sizes, seed, limit, repeats = (100, 1000, 10000), 20261009, 10, 3
    rows = []
    # 预热不计入统计，交替执行两种方式以减少先后顺序的影响。
    generate(100, limit, seed)
    for size in sizes:
        samples = {"list": [], "set": []}
        reference_keys = None
        attempts = None
        for repeat in range(repeats):
            modes = ("list", "set") if repeat % 2 == 0 else ("set", "list")
            for mode in modes:
                start = perf_counter()
                batch = generate(size, limit, seed, mode)
                samples[mode].append(perf_counter() - start)
                keys = [expression.key() for expression in batch.expressions]
                if reference_keys is None:
                    reference_keys = keys
                assert keys == reference_keys, "对照组的候选或结果不一致"
                attempts = batch.attempts
        row = {
            "count": size, "attempts": attempts,
            "list_samples_seconds": samples["list"], "set_samples_seconds": samples["set"],
            "list_median_seconds": statistics.median(samples["list"]),
            "set_median_seconds": statistics.median(samples["set"]),
        }
        row["speedup"] = row["list_median_seconds"] / row["set_median_seconds"]
        rows.append(row)
        print(f"{size}: list={row['list_median_seconds']:.6f}s, "
              f"set={row['set_median_seconds']:.6f}s, ratio={row['speedup']:.2f}x")

    large = reports / "large"
    start = perf_counter()
    batch = generate(10000, limit, seed)
    generated = perf_counter()
    write_batch(batch.expressions, large)
    written = perf_counter()
    grade = grade_files(large / "Exercises.txt", large / "Answers.txt")
    graded = perf_counter()
    (large / "Grade.txt").write_text(grade.text(), encoding="utf-8")
    assert len(grade.correct) == 10000 and not grade.wrong

    profiler = cProfile.Profile()
    profiler.runcall(generate, 10000, limit, seed)
    profiler.dump_stats(str(reports / "generation.prof"))
    stats = pstats.Stats(profiler)
    with (reports / "profile.txt").open("w", encoding="utf-8") as stream:
        pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(20)
    hotspots = []
    for (filename, line, function), (primitive, calls, self_time, cumulative, _) in stats.stats.items():
        if "/quiz/" in filename:
            hotspots.append({
                "function": f"{Path(filename).name}:{line} {function}",
                "calls": calls, "primitive_calls": primitive,
                "self_seconds": self_time, "cumulative_seconds": cumulative,
            })
    hotspots.sort(key=lambda row: row["cumulative_seconds"], reverse=True)
    data = {
        "run_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "python": sys.version, "platform": platform.platform(),
        "machine": platform.machine(), "processor": platform.processor(),
        "seed": seed, "range_exclusive": limit, "repeats": repeats,
        "scope": "纯生成含去重，不含文件输出；三次取中位数；列表为对照基线，非历史版本",
        "rows": rows, "hotspots": hotspots[:8],
        "end_to_end": {
            "count": 10000, "attempts": batch.attempts,
            "generate_seconds": generated - start, "write_seconds": written - generated,
            "grade_seconds": graded - written, "total_seconds": graded - start,
            "correct": len(grade.correct), "wrong": len(grade.wrong),
        },
    }
    (reports / "benchmark.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data["end_to_end"], ensure_ascii=False))


if __name__ == "__main__":
    main()
