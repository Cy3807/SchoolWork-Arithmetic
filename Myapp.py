#!/usr/bin/env python3
"""命令行入口：生成题目或批改作答。"""

import argparse
import sys
from pathlib import Path
from time import perf_counter

from quiz.files import grade_files, write_batch
from quiz.generate import generate


def positive_integer(text: str) -> int:
    try:
        value = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("请输入正整数") from error
    if value < 1:
        raise argparse.ArgumentTypeError("请输入大于或等于 1 的整数")
    return value


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="小学四则运算题目生成与自动批改")
    parser.add_argument("-n", type=positive_integer, help="题目数量，默认 10")
    parser.add_argument("-r", type=positive_integer, help="操作数与分母的上限，不含上限")
    parser.add_argument("-e", type=Path, help="待批改的题目文件")
    parser.add_argument("-a", type=Path, help="学生作答文件")
    parser.add_argument("--seed", type=int, help="固定随机种子，便于复现")
    parser.add_argument("--output-dir", type=Path, default=Path("."), help="输出目录，默认当前目录")
    options = parser.parse_args(argv)
    grading = options.e is not None or options.a is not None
    if grading:
        if options.e is None or options.a is None:
            parser.error("批改模式必须同时提供 -e 和 -a")
        if options.n is not None or options.r is not None or options.seed is not None:
            parser.error("批改模式不能同时使用 -n、-r 或 --seed")
    elif options.r is None:
        parser.print_help(sys.stderr)
        parser.error("生成模式必须提供 -r 参数")
    start = perf_counter()
    try:
        if grading:
            result = grade_files(options.e, options.a)
            options.output_dir.mkdir(parents=True, exist_ok=True)
            (options.output_dir / "Grade.txt").write_text(result.text(), encoding="utf-8")
            print(result.text(), end="")
        else:
            batch = generate(options.n or 10, options.r, options.seed)
            write_batch(batch.expressions, options.output_dir)
            print(f"已生成 {len(batch.expressions)} 道题，尝试 {batch.attempts} 次。")
            print(f"输出目录：{options.output_dir.resolve()}")
        print(f"耗时：{perf_counter() - start:.4f} 秒")
    except (ValueError, OSError, UnicodeError, RecursionError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
