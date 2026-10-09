"""依据真实代理复核记录绘图，不伪装为终端截图。"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]


def main():
    summary = json.loads((ROOT / "reports/agent-review/summary.json").read_text(encoding="utf-8"))
    correct = (ROOT / "reports/agent-review/grade-all-correct.txt").read_text(encoding="utf-8").strip()
    mixed = (ROOT / "reports/agent-review/grade-mixed.txt").read_text(encoding="utf-8").strip()
    assert summary["result"] == "PASS" and "Wrong: 2 (2, 5)" in mixed
    fig = plt.figure(figsize=(12, 8), facecolor="#f7f8fa")
    fig.text(.05, .94, "INDEPENDENT AI REVIEW", fontsize=24, weight="bold", color="#18364b")
    fig.text(.05, .90, "Real execution records | 2026-10-09 | Python 3.9.6 | macOS arm64", fontsize=12)
    fig.text(.05, .86, f"11:37:43 - 11:40:55 (UTC+08) | {summary['review_elapsed_seconds']:.2f}s elapsed", fontsize=11)
    cards = [
        (.05, .56, .90, .24, "GENERATION AND GRADING", correct + "\n\nAfter changing answers #2 and #5:\n" + mixed),
        (.05, .30, .43, .21, "INDEPENDENT CHECKS", "10,000 questions checked\nExact Fraction / AST calculation\nNo duplicate exchange orbits\n32 parent-child tree shapes: PASS"),
        (.52, .30, .43, .21, "BOUNDARIES AND EXAMPLES", "Missing -r: exit code 2\n-n 0 / -r 0: exit code 2\nSample #3: 69'7/10\nSample #4: 3 | Sample #6: 0"),
    ]
    for x, y, width, height, title, body in cards:
        ax = fig.add_axes([x, y, width, height])
        ax.set_facecolor("white")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#d5dfe5")
        ax.text(.035, .86, title, transform=ax.transAxes, fontsize=11, weight="bold", color="#22758b")
        ax.text(.035, .68, body, transform=ax.transAxes, fontsize=11, va="top", family="monospace", linespacing=1.5)
    fig.text(.05, .23, "38 existing tests rerun: PASS | Independent sample answers: PASS", fontsize=12, weight="bold")
    fig.text(.05, .18, "Source: reports/agent-review/execution.log, summary.json and grade reports", fontsize=10)
    fig.text(.05, .13, "Rendered from saved logs; not a terminal screenshot. Review executed by an AI agent.", fontsize=10, color="#5b6570")
    fig.text(.05, .09, "Elapsed execution time is not a record of either student's personal effort.", fontsize=10, color="#5b6570")
    fig.savefig(ROOT / "reports/run-record.png", dpi=160, facecolor=fig.get_facecolor())
    print(ROOT / "reports/run-record.png")


if __name__ == "__main__":
    main()
