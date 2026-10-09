"""编号文本文件的读写与批改。"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .model import Expr, format_number, parse_expression, parse_number


def write_batch(expressions: List[Expr], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    exercises = [f"{index}. {expression.render()} =\n"
                 for index, expression in enumerate(expressions, 1)]
    answers = [f"{index}. {format_number(expression.value)}\n"
               for index, expression in enumerate(expressions, 1)]
    (directory / "Exercises.txt").write_text("".join(exercises), encoding="utf-8")
    (directory / "Answers.txt").write_text("".join(answers), encoding="utf-8")


def read_lines(path: Path) -> List[str]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("gb18030")
    return text.splitlines()


def strip_number(line: str, expected: int) -> str:
    """允许无编号；有编号时必须从 1 连续递增，防止错位批改。"""
    match = re.match(r"^\s*(\d+)[.、]\s*(.*)$", line)
    if match:
        if int(match.group(1)) != expected:
            raise ValueError(f"第 {expected} 行的题号应为 {expected}")
        return match.group(2).strip()
    return line.strip()


@dataclass
class Grade:
    correct: List[int]
    wrong: List[int]

    def text(self) -> str:
        def line(label: str, numbers: List[int]) -> str:
            return f"{label}: {len(numbers)} ({', '.join(map(str, numbers))})\n"
        return line("Correct", self.correct) + line("Wrong", self.wrong)


def grade_files(exercise_path: Path, answer_path: Path) -> Grade:
    exercises, answers = read_lines(exercise_path), read_lines(answer_path)
    if not exercises:
        raise ValueError("题目文件不能为空")
    if len(answers) > len(exercises):
        raise ValueError("答案行数多于题目行数，请检查是否选错文件")
    correct, wrong = [], []
    for index, line in enumerate(exercises, 1):
        try:
            expected = parse_expression(strip_number(line, index)).value
        except ValueError as error:
            raise ValueError(f"第 {index} 道题无效：{error}") from error
        if index > len(answers):
            wrong.append(index)
            continue
        answer = strip_number(answers[index - 1], index)
        try:
            is_correct = parse_number(answer) == expected
        except ValueError:
            is_correct = False
        (correct if is_correct else wrong).append(index)
    return Grade(correct, wrong)
