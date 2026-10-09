# 小学四则运算题目生成与批改

软件工程结对项目。Python 命令行程序，支持自然数、分数、带分数、括号、结构去重、一万道题生成与自动批改。

[下载源码、报告和 Windows 程序包](https://github.com/Cy3807/SchoolWork-Arithmetic/releases/tag/v1.0.0)。

| 姓名 | 学号 |
| --- | --- |
| 陈昱绰 | 3123004519 |
| 陈鹏旭 | 3124004200 |

代码和文档由 Codex 协助完成，独立 AI 代理已完成样例、参数、批改、一万题和括号复核。PSP 保留工作量估算，另列真实代理执行时间。

## 运行环境

Python 3.9 及以上。核心程序、测试与基准均只用标准库，无须安装第三方库。
命令行在项目目录执行。macOS/Linux 用 `python3`，Windows 可将命令中的 `python3` 改为 `py -3`。

```sh
python3 Myapp.py -n 10 -r 10
python3 Myapp.py -n 10000 -r 10 --seed 20261009
python3 Myapp.py -e Exercises.txt -a Answers.txt
```

前两条在当前工作目录输出 `Exercises.txt` 和 `Answers.txt`，第三条输出 `Grade.txt`。
生成模式必须提供 `-r`；`-n` 未指定时默认 10。`--output-dir` 可选择其他输出目录。
批改时，`-a` 是学生作答文件；程序根据题目重新求值，不把该文件当作标准答案。

```text
Correct: 5 (1, 3, 5, 7, 9)
Wrong: 5 (2, 4, 6, 8, 10)
```

## 数值与去重规则

- 操作数的值和分数分母小于 `r`，不限制答案与中间结果上限。
- 每题 1 至 3 个运算符，每个减法子表达式结果非负；每个除法子表达式结果严格在 0 和 1 之间。
- 使用 `fractions.Fraction` 精确计算；输出最简整数、分数或 `2'3/8` 形式的带分数。
- 只交换加法和乘法节点的左右子树，不合并结合律。`3+(2+1)` 与 `1+2+3` 重复，`1+2+3` 与 `3+2+1` 不重复。
- 渲染保留同优先级的右子树括号，使题面重新解析后仍保留原树结构。
- `r=1` 时穷举全部合法结构；其他范围设有尝试上限，找到的数量不代表总容量。

输入分数使用 `3/5`；输入除法建议使用 `÷`，或两侧带空格的 `/`。
例如 `1/2 ÷ 3/4`、`1 / 2`。紧邻数字的 `1/2` 会作为一个分数读取。
批改允许未约分的等值答案；缺失或空白作答判错，多余答案、错位编号或非法题目给出错误信息。
输入文件支持 UTF-8、UTF-8 BOM 和 GB18030。原题只要求顺序编号的规范输入。

## 测试与报告

```sh
python3 tools/check.py
python3 tools/benchmark.py
```

测试结果保存到 `reports/tests.txt` 和 `reports/tests.json`。测试包括正式解析器和独立双栈求值器对 10000 道题的核对。
基准对相同种子生成的相同候选序列比较列表与集合查重，三次取中位数；列表是对照基线，不是声称曾经开发过的历史版本。
`reports/benchmark.json` 是原始数据，`reports/profile.txt` 是热点记录。

只有重新画图时需要安装绘图库：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-report.txt
.venv/bin/python tools/plot.py
```

Windows 对应命令为 `.venv\Scripts\python -m pip install -r requirements-report.txt` 和 `.venv\Scripts\python tools/plot.py`。
图保存在 `reports/performance.png`，可直接上传博客园。

## Windows 可执行文件

GitHub Actions 在 Windows 上使用 PyInstaller 打包 `Myapp.exe`，并实际验证生成与批改 10000 道题。
通过后，从仓库 Actions 对应成功运行的 Artifacts 中下载 `Windows-Myapp`，解压后在 PowerShell 执行：

```powershell
.\Myapp.exe -n 10 -r 10
.\Myapp.exe -e Exercises.txt -a Answers.txt
```

程序通过参数运行，直接双击会因缺少参数退出。GitHub 下载工件通常需要登录。

## 文件说明

| 文件或目录 | 用途 |
| --- | --- |
| Myapp.py | 参数校验和运行模式 |
| quiz/model.py | 分数、表达式树、规范键、渲染与解析 |
| quiz/generate.py | 数值生成、合法建树、批次去重 |
| quiz/files.py | 读写、编号校验、作答批改 |
| tests/ | 功能、边界、规模与命令行测试 |
| tools/ | 测试报告、基准和绘图脚本 |
| reports/ | 真实测试与性能数据 |
| examples/ | 实际生成的 10 道题及批改结果 |
| docs/博客草稿.md | 审核和补充身份及个人经历后发布 |
| docs/你需要操作的步骤.txt | 本机运行、截图、博客发布和提交步骤 |
| docs/搭档复核任务.txt | 已由独立 AI 代理执行的复核范围与结果 |
| docs/代理复核记录.md | 代理真实执行时间、独立核算方法与实测证据 |
| docs/PSP时间表.txt | PSP 的含义、各阶段时间估算及合计 |

## 作业来源

[作业要求](https://edu.cnblogs.com/campus/gdgy/Class78-Grade2024-CS/homework/15703)。
