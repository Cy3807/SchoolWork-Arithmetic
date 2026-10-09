"""把本次真实测试及基准数据写入技术报告与待本人审核的博客草稿。"""

import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    tests = json.loads((ROOT / "reports/tests.json").read_text(encoding="utf-8"))
    bench = json.loads((ROOT / "reports/benchmark.json").read_text(encoding="utf-8"))
    assert tests["successful"], "测试未通过，不能生成完成报告"
    for result in (tests, bench):
        for relative, expected in result["source_sha256"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            assert actual == expected, f"{relative} 已变化，请先重新验证再生成报告"
    last = bench["rows"][-1]
    end = bench["end_to_end"]
    performance_rows = "\n".join(
        f"| {row['count']} | {row['list_median_seconds']:.6f} | "
        f"{row['set_median_seconds']:.6f} | {row['speedup']:.2f} |"
        for row in bench["rows"]
    )
    core_paths = [ROOT / "Myapp.py", *sorted((ROOT / "quiz").glob("*.py"))]
    core_lines = sum(len(path.read_text(encoding="utf-8").splitlines()) for path in core_paths)
    test_lines = sum(len(path.read_text(encoding="utf-8").splitlines())
                     for path in (ROOT / "tests").glob("*.py"))
    psp_rows = [
        ("Planning", "计划"), ("· Estimate", "估计任务所需时间"),
        ("Development", "开发"), ("· Analysis", "需求分析与学习"),
        ("· Design Spec", "设计文档"), ("· Design Review", "设计复审"),
        ("· Coding Standard", "代码规范"), ("· Design", "具体设计"),
        ("· Coding", "编码与工具生成后的修改"), ("· Code Review", "代码复审"),
        ("· Test", "测试"), ("Reporting", "报告"),
        ("· Test Report", "测试报告"), ("· Size Measurement", "计算工作量"),
        ("· Postmortem & Process Improvement Plan", "总结及改进计划"), ("合计", ""),
    ]
    psp = "\n".join(f"| {stage} | {work} | 待填写 | 待填写 |" for stage, work in psp_rows)
    test_cases = [
        ("指定 -n 10 -r 10", "生成 10 道题及对应答案"),
        ("只给 -n，不给 -r", "退出码 2，并显示帮助信息"),
        ("-n 0、-r 0、非数字参数", "拒绝无效参数"),
        ("1/6 + 1/8", "精确得到 7/24"),
        ("1/2 ÷ 3/4", "得到 2/3，分数不会被误拆成两次除法"),
        ("3+(2+1) 与 1+2+3", "判为重复"),
        ("1+2+3 与 3+2+1", "判为不重复"),
        ("23+45 与 45+23；6×8 与 8×6", "均判为重复"),
        ("保留同优先级右子树的括号", "渲染后解析回原来的表达式树"),
        ("多个范围与随机种子", "操作数、分母及每个中间节点符合约束"),
        ("-n 10000 -r 10", "数量为 10000，无结构重复，独立求值全部一致"),
        ("用生成的答案进行批改", "全部正确"),
        ("把第 2、5 题改成错误答案", "错误题号恰为 2、5"),
        ("答案写成 6/4、2/4 等未约分形式", "按数值比较，等值即正确"),
        ("缺失或空白作答", "对应题号判错"),
        ("题目除零、错位编号或多余答案", "清楚报错，不静默错位批改"),
        ("-r 1 请求超过穷举容量的题数", "及时退出，保留已有输出文件"),
    ]
    table = "\n".join(f"| {index} | {case} | {expected} | 通过 |"
                      for index, (case, expected) in enumerate(test_cases, 1))
    key_source = (ROOT / "quiz/model.py").read_text(encoding="utf-8")
    key_code = key_source.split("    def key(self) -> tuple:\n", 1)[1].split("\n    def render", 1)[0]
    key_code = "def key(self) -> tuple:\n" + "\n".join(line[4:] for line in key_code.splitlines())
    blog = f'''# 软件工程结对项目 小学四则运算题目生成与自动批改

| 项目 | 内容 |
| --- | --- |
| 所属课程 | [软件工程](https://edu.cnblogs.com/campus/gdgy/Class78-Grade2024-CS) |
| 作业要求 | [结对项目](https://edu.cnblogs.com/campus/gdgy/Class78-Grade2024-CS/homework/15703) |
| 作业目标 | 实现四则运算题目生成与批改，练习需求分析、测试和源代码管理 |
| 本人姓名及学号 | 陈昱绰，3123004519 |
| 搭档姓名及学号 | 陈鹏旭，3124004200 |
| GitHub | https://github.com/Cy3807/SchoolWork-Arithmetic |

本次补做使用 Python 实现命令行程序，完成题目生成、答案计算和自动批改。代码与技术文档使用 Codex 协助完成，以下测试和性能数据来自实际运行。个人投入时间和结对经历由本人据实补充。

## 一 PSP 时间记录

单位为分钟。表格记录本人及搭档的实际工作；没有事前记录的预估应说明情况，不补造历史估计。总项与子项不重复相加。

| PSP2.1 | 工作内容 | 预估耗时 | 实际耗时 |
| --- | --- | --- | --- |
{psp}

## 二 需求分析

程序有生成和批改两种模式。生成时使用 `-n` 控制题目数量，`-r` 控制操作数和分数分母的范围，范围不包含上限。批改时使用 `-e` 和 `-a` 指定题目文件与学生作答文件。

需要检查的约束在每个运算节点上：减法不能得到负数，除法结果必须严格大于 0 且小于 1，每题最多有 3 个运算符。题面可以包含自然数、分数、带分数和括号，答案采用最简形式输出。

去重不能只看字符串或答案。题目只允许交换加法和乘法两侧的子表达式，不允许随意改变结合顺序。因此 `3+(2+1)` 和 `1+2+3` 重复，而 `1+2+3` 和 `3+2+1` 不重复。

## 三 设计与实现

核心代码共 {core_lines} 行，测试代码 {test_lines} 行，均按文件实际行数统计，包含注释与空行。

| 模块 | 主要职责 |
| --- | --- |
| Myapp.py | 参数检查、选择模式、错误提示 |
| quiz/model.py | Fraction 分数、Expr 表达式树、规范键、题面渲染与递归下降解析 |
| quiz/generate.py | 随机操作数、合法子树构建和批次去重 |
| quiz/files.py | 编号文件读写、重新求值与批改统计 |

生成时依次解析参数、决定 1 至 3 个运算符、递归创建子树、选择合法运算、生成规范键、用集合查重，最后输出题目与答案。

批改时先读取文件并校验编号，再解析题目和学生作答，比较分数值，最后输出正确、错误数量和题号。

叶子节点保存数值，二元节点保存运算符、左右孩子及计算结果。减法把较大的子表达式放在左边；除法把较小的正数放在左边，无法形成真分数时改用其他运算。这样可以复用已经创建的子树。

## 四 关键代码

### 分数精确计算

```python
from fractions import Fraction
result = Fraction(1, 6) + Fraction(1, 8)  # 7/24
```

使用标准库 Fraction 避免浮点误差。输出时把假分数转换成带分数，例如 `19/8` 显示为 `2'3/8`。批改按分数值比较，因此 `6/4` 和 `1'1/2` 等值。

### 保留结构的去重

```python
{key_code.rstrip()}
```

规范键保留整个表达式树。仅在加法和乘法节点比较并交换两侧的键，减法和除法保持原顺序。键放入集合后，查询通常比逐个遍历历史题目更快。

### 括号与题面解析

题面渲染时，优先级较低的孩子加括号，同优先级的右孩子也保留括号。后者可以避免 `1+(2+3)` 输出成 `1+2+3` 后丢失树形结构，影响去重判断。

批改采用递归下降解析器，按加减、乘除、数字或括号三层处理输入，不使用 `eval`。分数 `3/4` 作为一个数字读取，除法建议使用 `÷`，或带空格的 `/`。

## 五 效能分析

性能分析与改进的人工投入：【待填写实际分钟数】。

测试环境为 {bench['platform']}，Python {bench['python'].split()[0]}。设置 `r=10`、随机种子 `20261009`，对列表查重和集合查重各运行 3 次，取中位数。两种方式生成完全相同的候选和结果，仅改变查重容器。列表是本次专门实现的对照基线，不是历史开发版本。本次是在电脑后台测量的墙钟时间，受主机负载和调度影响，应结合原始多次采样看待结果。

| 题目数量 | 列表查重秒 | 集合查重秒 | 列表耗时除以集合耗时 |
| --- | --- | --- | --- |
{performance_rows}

生成 10000 道题时，集合查重耗时约 {last['set_median_seconds']:.3f} 秒，是列表对照耗时的约 {1/last['speedup']:.2%}。小规模时常数开销和测量波动更明显，因此不能把某一次加速比看作所有输入的固定收益。

![性能分析图](../reports/performance.png)

图左为生成时间，包含构建与查重，不包含文件写入。图右为 cProfile 累计时间，包含子函数调用，各项有重叠，不能相加作为总耗时；剖析本身也会增加运行开销。除入口函数外，主要耗时位于 `build` 和 `random_number`，也就是建树及随机操作数生成。

另一次完整流程实测：生成 {end['generate_seconds']:.3f} 秒，写文件 {end['write_seconds']:.3f} 秒，批改 {end['grade_seconds']:.3f} 秒；10000 道题全部判对。

采用的措施包括集合查重、在构造节点时保存计算结果、复用子树，以及整批拼接文本后写文件。上表直接测量的是查重容器的影响，其他措施没有单独量化收益。

Windows 打包验证还发现了一个兼容性问题：冻结后的程序在重定向输出时可能采用 ANSI 编码，打印中文提示会失败。修复是在入口显式把标准输出和错误输出设置为 UTF-8，并增加强制 ASCII 环境下的回归测试。对应首次失败及修复后的运行记录可在仓库 Actions 中查看。相关接口见 [Python 文本流文档](https://docs.python.org/3/library/io.html#io.TextIOWrapper.reconfigure)。

## 六 测试结果

本地共运行 {tests['tests_run']} 项自动化测试，{tests['passed']} 项通过。以下将相关检查整理为 {len(test_cases)} 组场景，完整测试名与原始结果保存在 `reports/tests.txt`。

| 序号 | 测试内容 | 预期结果 | 实测 |
| --- | --- | --- | --- |
{table}

正确性检查包括三层：先用固定例子验证分数、优先级和去重规则；再对多个范围和随机种子逐节点检查约束；最后把 10000 道输出题面重新解析，并用另一套双栈求值器独立计算，核对结果。这样可以降低生成和批改共用代码而遗漏同一种错误的风险。

## 七 运行方法

```sh
python3 Myapp.py -n 10 -r 10
python3 Myapp.py -n 10000 -r 10 --seed 20261009
python3 Myapp.py -e Exercises.txt -a Answers.txt
python3 tools/check.py
```

Windows 安装 Python 后可把 `python3` 换成 `py -3`。仓库还提供 Windows 自动构建流程，成功后可下载 `Myapp.exe`，使用同样的参数运行。生成文件为 Exercises.txt、Answers.txt，批改结果为 Grade.txt。

## 八 项目总结与结对记录

从实现结果看，表达式树同时承担计算、渲染和去重，能把三者联系起来。去重必须保持原题定义，括号输出也必须保留这一结构；只检查数值相等还不够。

需要改进的方面是题目难度尚未按年级分类，小范围下寻找大量不同题目采用尝试上限，除 `r=1` 外没有精确计算全部容量。程序会明确提示调整数量或范围。

实际分工：【待填写：双方各自完成的分析、学习、修改、测试及复核工作】。

结对感受：【待填写：实际讨论或共同检查的一个具体例子】。

彼此的优点与建议：【待填写：双方各一条，结合实际合作情况】。

## 参考资料

以下同学博客用于了解作业展示结构，不引用其代码、PSP 时间或性能数据。

- [刘俊宁、段旷卓的项目博客](https://www.cnblogs.com/mikko0615/p/23085957)
- [胡浩东、石基业的项目博客](https://www.cnblogs.com/konglang/p/23064533)
- [李彦峰的项目博客](https://www.cnblogs.com/00Lyf/p/23085770)
- [刘文俊、林昕旸的项目博客](https://www.cnblogs.com/liuwenjun9/p/23084426)
- [陈明凯、邓文炜的项目博客](https://www.cnblogs.com/kecit/p/23084378)
'''
    (ROOT / "docs/博客草稿.md").write_text(blog, encoding="utf-8")
    (ROOT / "docs/博客草稿.txt").write_text(blog, encoding="utf-8")
    report = f'''# 本地验证记录

测试时间：{tests['run_at']}。
环境：{tests['platform']}，Python {tests['python'].split()[0]}。
结果：{tests['tests_run']} 项测试，{tests['passed']} 项通过，耗时 {tests['elapsed_seconds']:.3f} 秒。

性能记录时间：{bench['run_at']}。
两种容器各运行 {bench['repeats']} 次，种子 {bench['seed']}，范围 {bench['range_exclusive']}。

| 数量 | 列表秒 | 集合秒 | 加速比 |
| --- | --- | --- | --- |
{performance_rows}

10000 道题写出并重新批改：正确 {end['correct']}，错误 {end['wrong']}。
完整流程 {end['total_seconds']:.3f} 秒，不包含最后写 Grade.txt 的时间。

数据范围及源码 SHA-256 见 reports/tests.json 和 reports/benchmark.json。
性能基线是同次实验的容器对照，不代表先前存在过某个旧版本。
原始题目和答案可用 tools/benchmark.py 重新生成到 reports/large。

本记录由自动化运行生成，不代表学生个人投入时间。
'''
    (ROOT / "docs/本地验证记录.md").write_text(report, encoding="utf-8")
    print(f"已生成博客草稿和验证记录；核心代码 {core_lines} 行，测试代码 {test_lines} 行")


if __name__ == "__main__":
    main()
