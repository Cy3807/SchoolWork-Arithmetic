"""功能、边界、命令行及规模测试；全部使用标准库 unittest。"""

import random
import re
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from quiz.files import grade_files, write_batch
from quiz.generate import generate, zero_space
from quiz.model import format_number, parse_expression, parse_number


ROOT = Path(__file__).resolve().parents[1]


def independent_value(text):
    """只用于测试的双栈求值器，独立于正式递归下降解析器。"""
    values, operators = [], []
    precedence = {"+": 1, "−": 1, "×": 2, "÷": 2}

    def reduce_top():
        right, left, op = values.pop(), values.pop(), operators.pop()
        if op == "+":
            values.append(left + right)
        elif op == "−":
            values.append(left - right)
        elif op == "×":
            values.append(left * right)
        else:
            values.append(left / right)

    for token in re.findall(r"\d+'\d+/\d+|\d+/\d+|\d+|[()+−×÷]", text):
        if token[0].isdigit():
            if "'" in token:
                integer, fraction = token.split("'")
                n, d = fraction.split("/")
                values.append(Fraction(int(integer)) + Fraction(int(n), int(d)))
            elif "/" in token:
                n, d = token.split("/")
                values.append(Fraction(int(n), int(d)))
            else:
                values.append(Fraction(int(token)))
        elif token == "(":
            operators.append(token)
        elif token == ")":
            while operators[-1] != "(":
                reduce_top()
            operators.pop()
        else:
            while (operators and operators[-1] != "("
                   and precedence[operators[-1]] >= precedence[token]):
                reduce_top()
            operators.append(token)
    while operators:
        reduce_top()
    if len(values) != 1:
        raise AssertionError("独立求值器没有得到唯一结果")
    return values[0]


def verify_tree(test, expression, limit):
    if not expression.op:
        test.assertGreaterEqual(expression.value, 0)
        test.assertLess(expression.value, limit)
        test.assertLess(expression.value.denominator, limit)
        return 0
    count = 1 + verify_tree(test, expression.left, limit) + verify_tree(test, expression.right, limit)
    if expression.op == "-":
        test.assertGreaterEqual(expression.value, 0)
    elif expression.op == "/":
        test.assertGreater(expression.right.value, 0)
        test.assertGreater(expression.value, 0)
        test.assertLess(expression.value, 1)
    return count


class NumberTests(unittest.TestCase):
    def test_exact_fraction_addition(self):
        self.assertEqual(parse_expression("1/6 + 1/8").value, Fraction(7, 24))

    def test_number_formats(self):
        for text, expected in [("0", Fraction(0)), ("3/5", Fraction(3, 5)),
                               ("2’3/8", Fraction(19, 8)), ("6/4", Fraction(3, 2))]:
            with self.subTest(text=text):
                self.assertEqual(parse_number(text), expected)

    def test_output_formats(self):
        for value, text in [(Fraction(0), "0"), (Fraction(6, 4), "1'1/2"),
                            (Fraction(3, 5), "3/5"), (Fraction(4), "4")]:
            self.assertEqual(format_number(value), text)

    def test_invalid_number(self):
        for text in ("1/0", "2'4/3", "hello", "-1", "1.5", ""):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_number(text)


class ExpressionTests(unittest.TestCase):
    def test_operator_precedence(self):
        self.assertEqual(parse_expression("2 + 3 × 4").value, 14)

    def test_parentheses(self):
        self.assertEqual(parse_expression("（2 + 3）× 4 =").value, 20)

    def test_fraction_on_divisor_side(self):
        self.assertEqual(parse_expression("1/2 ÷ 3/4").value, Fraction(2, 3))

    def test_ascii_division_with_spaces(self):
        self.assertEqual(parse_expression("1 / 2 / 3").value, Fraction(1, 6))

    def test_addition_duplicate(self):
        self.assertEqual(parse_expression("23+45").key(), parse_expression("45+23").key())

    def test_multiplication_duplicate(self):
        self.assertEqual(parse_expression("6*8").key(), parse_expression("8*6").key())

    def test_nested_duplicate_from_assignment(self):
        self.assertEqual(parse_expression("3+(2+1)").key(), parse_expression("1+2+3").key())

    def test_associativity_is_not_a_duplicate_rule(self):
        self.assertNotEqual(parse_expression("1+2+3").key(), parse_expression("3+2+1").key())

    def test_same_answer_does_not_mean_duplicate(self):
        self.assertNotEqual(parse_expression("1+4").key(), parse_expression("2+3").key())

    def test_noncommutative_operators(self):
        for a, b in [("3-2", "2-3"), ("3 ÷ 2", "2 ÷ 3")]:
            self.assertNotEqual(parse_expression(a).key(), parse_expression(b).key())

    def test_render_preserves_tree_structure(self):
        for text in ("1+(2+3)", "1*(2*3)", "3-(2-1)", "1 ÷ (2 ÷ 3)",
                     "(1+2)*3", "2*(3 ÷ 4)"):
            original = parse_expression(text)
            rendered = parse_expression(original.render())
            self.assertEqual(rendered, original)

    def test_reject_invalid_expressions(self):
        for text in ("1 ÷ 0", "(1+2", "1+", "1 2", "1+2)", "", "__import__('os')"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_expression(text)


class GeneratorTests(unittest.TestCase):
    def test_seed_reproducibility(self):
        self.assertEqual(generate(100, 10, 7), generate(100, 10, 7))

    def test_list_and_set_have_identical_candidates(self):
        self.assertEqual(generate(200, 10, 7, "list"), generate(200, 10, 7, "set"))

    def test_multiple_limits_and_seeds(self):
        for limit in (2, 3, 5, 10, 100):
            for seed in (0, 7, 20261009):
                batch = generate(100, limit, seed)
                self.assertEqual(len({e.key() for e in batch.expressions}), 100)
                for expression in batch.expressions:
                    count = verify_tree(self, expression, limit)
                    self.assertTrue(1 <= count <= 3)

    def test_ten_thousand_roundtrip_and_independent_calculation(self):
        batch = generate(10000, 10, 20261009)
        self.assertEqual(len(batch.expressions), 10000)
        self.assertEqual(len({e.key() for e in batch.expressions}), 10000)
        observed_operators = set()
        has_fraction = False
        for expression in batch.expressions:
            self.assertTrue(1 <= verify_tree(self, expression, 10) <= 3)
            text = expression.render()
            observed_operators.update(symbol for symbol in "+−×÷" if symbol in text)
            has_fraction |= "/" in text
            reparsed = parse_expression(text)
            self.assertEqual(reparsed, expression)
            self.assertEqual(independent_value(text), expression.value)
            self.assertEqual(parse_number(format_number(expression.value)), expression.value)
        self.assertEqual(observed_operators, set("+−×÷"))
        self.assertTrue(has_fraction)

    def test_limit_one_exact_capacity(self):
        space = zero_space()
        batch = generate(len(space), 1, 0)
        self.assertEqual(len({e.key() for e in batch.expressions}), len(space))
        self.assertTrue(all(e.value == 0 for e in batch.expressions))
        with self.assertRaisesRegex(ValueError, "最多"):
            generate(len(space) + 1, 1)

    def test_small_range_exhaustion_stops(self):
        with self.assertRaisesRegex(ValueError, "仅找到"):
            generate(10000, 2, 0)

    def test_invalid_parameters(self):
        for count, limit in ((0, 10), (10, 0), (-1, 1)):
            with self.assertRaises(ValueError):
                generate(count, limit)


class FileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.exercises = self.directory / "Exercises.txt"
        self.answers = self.directory / "Answers.txt"
        write_batch(generate(10, 10, 42).expressions, self.directory)

    def test_all_correct(self):
        result = grade_files(self.exercises, self.answers)
        self.assertEqual(result.correct, list(range(1, 11)))
        self.assertEqual(result.wrong, [])

    def test_changed_answers_report_exact_indexes(self):
        lines = self.answers.read_text().splitlines()
        lines[1], lines[4] = "2. 999999", "5. 999999"
        self.answers.write_text("\n".join(lines), encoding="utf-8")
        self.assertEqual(grade_files(self.exercises, self.answers).wrong, [2, 5])

    def test_equivalent_unreduced_and_mixed_answers(self):
        self.exercises.write_text("1. 1/2 + 1 =\n2. 1/4 + 1/4 =\n", encoding="utf-8")
        self.answers.write_text("1. 6/4\n2. 2/4\n", encoding="utf-8")
        self.assertEqual(grade_files(self.exercises, self.answers).correct, [1, 2])

    def test_missing_and_blank_answers_are_wrong(self):
        self.answers.write_text("1. \n", encoding="utf-8")
        self.assertEqual(grade_files(self.exercises, self.answers).wrong, list(range(1, 11)))

    def test_extra_answers_rejected(self):
        with self.answers.open("a", encoding="utf-8") as stream:
            stream.write("11. 0\n")
        with self.assertRaises(ValueError):
            grade_files(self.exercises, self.answers)

    def test_wrong_numbering_rejected(self):
        self.answers.write_text("2. 0\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "题号"):
            grade_files(self.exercises, self.answers)

    def test_gbk_and_utf8_bom(self):
        self.exercises.write_bytes("1. 1/2 + 1/2 =\n".encode("gb18030"))
        self.answers.write_bytes("1. 1\n".encode("utf-8-sig"))
        self.assertEqual(grade_files(self.exercises, self.answers).correct, [1])

    def test_malformed_exercise_rejected(self):
        self.exercises.write_text("1. 1 ÷ 0 =\n", encoding="utf-8")
        self.answers.write_text("1. 0\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "第 1 道题"):
            grade_files(self.exercises, self.answers)

    def test_grade_output_format(self):
        self.exercises.write_text("1. 1+1 =\n2. 2+2 =\n", encoding="utf-8")
        self.answers.write_text("1. 2\n2. 0\n", encoding="utf-8")
        self.assertEqual(grade_files(self.exercises, self.answers).text(), "Correct: 1 (1)\nWrong: 1 (2)\n")


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def run_app(self, *arguments):
        return subprocess.run([sys.executable, str(ROOT / "Myapp.py"), *arguments],
                              cwd=self.directory, capture_output=True, text=True, timeout=20)

    def test_default_current_directory_and_grading(self):
        result = self.run_app("-r", "10", "--seed", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len((self.directory / "Exercises.txt").read_text().splitlines()), 10)
        result = self.run_app("-e", "Exercises.txt", "-a", "Answers.txt")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Correct: 10", (self.directory / "Grade.txt").read_text())

    def test_missing_range_displays_help(self):
        result = self.run_app("-n", "10")
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr)
        self.assertIn("-r", result.stderr)

    def test_invalid_cli_parameters(self):
        for arguments in (("-r", "0"), ("-r", "abc"), ("-n", "0", "-r", "10"),
                          ("-e", "x"), ("-e", "x", "-a", "y", "-r", "10")):
            with self.subTest(arguments=arguments):
                self.assertEqual(self.run_app(*arguments).returncode, 2)

    def test_missing_file_returns_readable_error(self):
        result = self.run_app("-e", "missing.txt", "-a", "missing2.txt")
        self.assertEqual(result.returncode, 1)
        self.assertIn("错误", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_capacity_failure_does_not_overwrite_existing_files(self):
        path = self.directory / "Exercises.txt"
        path.write_text("preserve me", encoding="utf-8")
        result = self.run_app("-n", "1000", "-r", "1")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(path.read_text(), "preserve me")


if __name__ == "__main__":
    unittest.main(verbosity=2)
