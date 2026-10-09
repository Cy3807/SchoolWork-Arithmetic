"""根据 benchmark.json 生成可上传到博客园的 PNG 性能图。"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = json.loads((ROOT / "reports/benchmark.json").read_text(encoding="utf-8"))
    rows = data["rows"]
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    figure, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), layout="constrained")
    figure.suptitle("Arithmetic quiz benchmark | r=10 | seed=20261009", fontsize=15, fontweight="bold")
    sizes = [row["count"] for row in rows]
    for mode, label, color in (("list", "List lookup baseline", "#bd632f"),
                               ("set", "Set lookup implemented", "#22758b")):
        axes[0].plot(sizes, [row[f"{mode}_median_seconds"] for row in rows],
                     marker="o", linewidth=2, label=label, color=color)
    axes[0].set(xscale="log", yscale="log", xlabel="Number of unique questions",
                ylabel="Generation time (seconds, log scale)", title="Same candidate sequence, median of 3 runs")
    axes[0].set_xticks(sizes, [str(size) for size in sizes])
    axes[0].grid(alpha=0.2, which="both")
    axes[0].legend(loc="upper left", fontsize=9)
    final = rows[-1]
    axes[0].text(0.97, 0.06, f"10,000 questions: {final['speedup']:.1f}x speedup",
                 transform=axes[0].transAxes, ha="right", color="#22758b", fontweight="bold")

    hotspots = list(reversed(data["hotspots"][:6]))
    names = [row["function"].split(" ", 1)[-1] for row in hotspots]
    times = [row["cumulative_seconds"] for row in hotspots]
    axes[1].barh(names, times, color="#22758b", height=0.62)
    axes[1].set(xlabel="Cumulative seconds (includes child calls)", title="cProfile: top project functions")
    axes[1].grid(axis="x", alpha=0.2)
    axes[1].set_axisbelow(True)
    axes[1].margins(x=0.23)
    for index, value in enumerate(times):
        axes[1].text(value, index, f"  {value:.3f}", va="center", fontsize=9)
    figure.savefig(ROOT / "reports/performance.png", dpi=180, facecolor="white")
    figure.savefig(ROOT / "reports/performance.svg", facecolor="white")
    svg_path = ROOT / "reports/performance.svg"
    svg_path.write_text("\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
                        encoding="utf-8")
    print(ROOT / "reports/performance.png")


if __name__ == "__main__":
    main()
