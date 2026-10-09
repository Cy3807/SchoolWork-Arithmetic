"""生成满足约束且不重复的题目。"""

import random
from dataclasses import dataclass
from fractions import Fraction
from typing import List, Optional

from .model import Expr, binary


@dataclass
class Batch:
    expressions: List[Expr]
    attempts: int


def random_number(rng: random.Random, limit: int) -> Expr:
    if limit < 3 or rng.randrange(3) == 0:
        return Expr(Fraction(rng.randrange(limit)))
    denominator = rng.randrange(2, limit)
    numerator = rng.randrange(1, denominator)
    whole = rng.randrange(limit) if rng.randrange(2) else 0
    # whole <= limit-1 且余数 < 1，所以整个带分数严格小于 limit。
    return Expr(Fraction(whole) + Fraction(numerator, denominator))


def build(rng: random.Random, limit: int, operators: int) -> Expr:
    if operators == 0:
        return random_number(rng, limit)
    left_operators = rng.randrange(operators)
    left = build(rng, limit, left_operators)
    right = build(rng, limit, operators - 1 - left_operators)
    op = rng.choice(("+", "-", "*", "/"))
    if op == "-" and left.value < right.value:
        left, right = right, left
    if op == "/":
        if left.value > right.value:
            left, right = right, left
        if not 0 < left.value < right.value:
            # 这对子树无法组成真分数除法，保留子树并改用其他运算。
            op = rng.choice(("+", "-", "*"))
            if op == "-" and left.value < right.value:
                left, right = right, left
    return binary(op, left, right)


def zero_space() -> List[Expr]:
    """r=1 时只有操作数 0，穷举最多三个运算符的全部合法结构。"""
    levels = [{Expr(Fraction(0)).key(): Expr(Fraction(0))}]
    for count in range(1, 4):
        unique = {}
        for left_count in range(count):
            for left in levels[left_count].values():
                for right in levels[count - 1 - left_count].values():
                    for op in ("+", "-", "*"):
                        expression = binary(op, left, right)
                        unique[expression.key()] = expression
        levels.append(unique)
    return [expression for level in levels[1:] for expression in level.values()]


def generate(count: int, limit: int, seed: Optional[int] = None,
             membership: str = "set") -> Batch:
    """membership=list 仅供性能基线使用，候选与正式算法完全相同。"""
    if count < 1 or limit < 1:
        raise ValueError("题目数量和数值范围都必须是正整数")
    if membership not in ("set", "list"):
        raise ValueError("未知查重方式")
    rng = random.Random(seed)
    if limit == 1:
        candidates = zero_space()
        if count > len(candidates):
            raise ValueError(f"-r 1 在当前规则下最多有 {len(candidates)} 道题，请减少 -n 或增大 -r")
        rng.shuffle(candidates)
        return Batch(candidates[:count], count)
    seen = set() if membership == "set" else []
    result = []
    maximum_attempts = max(10000, count * 80)
    for attempt in range(1, maximum_attempts + 1):
        expression = build(rng, limit, rng.randint(1, 3))
        key = expression.key()
        if key in seen:
            continue
        if membership == "set":
            seen.add(key)
        else:
            seen.append(key)
        result.append(expression)
        if len(result) == count:
            return Batch(result, attempt)
    raise ValueError(
        f"尝试 {maximum_attempts} 次仅找到 {len(result)} 道不同题目，"
        "请增大 -r 或减少 -n；这不是题目总容量的精确计算"
    )
