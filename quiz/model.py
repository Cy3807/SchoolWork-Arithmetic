"""分数格式、表达式树和安全解析，不执行输入中的 Python 代码。"""

import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Optional


def normalize(text: str) -> str:
    return text.translate(str.maketrans({
        "’": "'", "‘": "'", "−": "-", "–": "-",
        "×": "*", "÷": "/", "（": "(", "）": ")",
    }))


def parse_number(text: str) -> Fraction:
    """读取非负整数、分数或带分数；允许作答使用等值的未约分分数。"""
    text = normalize(text.strip())
    match = re.fullmatch(r"(?:(\d+)'(\d+)/(\d+)|(\d+)/(\d+)|(\d+))", text)
    if not match:
        raise ValueError("数字格式应为整数、3/5 或 2'3/8")
    whole, numerator, denominator, simple_n, simple_d, integer = match.groups()
    try:
        if whole is not None:
            if not 0 < int(numerator) < int(denominator):
                raise ValueError("带分数的分数部分必须是真分数")
            return Fraction(int(whole)) + Fraction(int(numerator), int(denominator))
        if simple_n is not None:
            return Fraction(int(simple_n), int(simple_d))
        return Fraction(int(integer))
    except ZeroDivisionError as error:
        raise ValueError("分母不能为零") from error


def format_number(value: Fraction) -> str:
    """结果统一约分，假分数显示为带分数。"""
    sign = "-" if value < 0 else ""
    whole, remainder = divmod(abs(value.numerator), value.denominator)
    if remainder == 0:
        return sign + str(whole)
    fraction = f"{remainder}/{value.denominator}"
    return sign + (f"{whole}'{fraction}" if whole else fraction)


@dataclass(frozen=True)
class Expr:
    """叶子保存数值，二元节点保存子树及已计算的精确结果。"""

    value: Fraction
    op: str = ""
    left: Optional["Expr"] = None
    right: Optional["Expr"] = None

    def key(self) -> tuple:
        if not self.op:
            return ("n", self.value.numerator, self.value.denominator)
        left, right = self.left.key(), self.right.key()
        if self.op in ("+", "*") and right < left:
            left, right = right, left
        return (self.op, left, right)

    def render(self, parent_precedence: int = 0, right_child: bool = False) -> str:
        if not self.op:
            return format_number(self.value)
        precedence = 1 if self.op in ("+", "-") else 2
        symbol = {"+": "+", "-": "−", "*": "×", "/": "÷"}[self.op]
        text = (f"{self.left.render(precedence)} {symbol} "
                f"{self.right.render(precedence, True)}")
        # 同优先级的右孩子也加括号，保留题目去重所依赖的树形结构。
        if precedence < parent_precedence or (right_child and precedence == parent_precedence):
            return f"({text})"
        return text


def binary(op: str, left: Expr, right: Expr) -> Expr:
    if op == "+":
        value = left.value + right.value
    elif op == "-":
        value = left.value - right.value
    elif op == "*":
        value = left.value * right.value
    elif op == "/":
        if right.value == 0:
            raise ValueError("除数不能为零")
        value = left.value / right.value
    else:
        raise ValueError("不支持的运算符")
    return Expr(value, op, left, right)


TOKEN = re.compile(r"\d+'\d+/\d+|\d+/\d+|\d+|[()+*/-]")


class Parser:
    """递归下降解析器：加减层、乘除层、数字或括号层。"""

    def __init__(self, text: str):
        text = normalize(text.strip())
        if text.endswith("="):
            text = text[:-1].rstrip()
        self.tokens = []
        cursor = 0
        for match in TOKEN.finditer(text):
            if text[cursor:match.start()].strip():
                raise ValueError("表达式包含非法字符")
            self.tokens.append(match.group())
            cursor = match.end()
        if text[cursor:].strip():
            raise ValueError("表达式包含非法字符")
        self.position = 0

    def peek(self) -> str:
        return self.tokens[self.position] if self.position < len(self.tokens) else ""

    def parse(self) -> Expr:
        if not self.tokens:
            raise ValueError("表达式不能为空")
        expression = self.sum()
        if self.peek():
            raise ValueError("表达式存在多余内容或缺少运算符")
        return expression

    def sum(self) -> Expr:
        result = self.product()
        while self.peek() in ("+", "-"):
            op = self.peek()
            self.position += 1
            result = binary(op, result, self.product())
        return result

    def product(self) -> Expr:
        result = self.atom()
        while self.peek() in ("*", "/"):
            op = self.peek()
            self.position += 1
            result = binary(op, result, self.atom())
        return result

    def atom(self) -> Expr:
        token = self.peek()
        if token == "(":
            self.position += 1
            result = self.sum()
            if self.peek() != ")":
                raise ValueError("括号不匹配")
            self.position += 1
            return result
        if not token or not token[0].isdigit():
            raise ValueError("此处需要数字或左括号")
        self.position += 1
        return Expr(parse_number(token))


def parse_expression(text: str) -> Expr:
    return Parser(text).parse()
