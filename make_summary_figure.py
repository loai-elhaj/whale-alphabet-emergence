"""Builds results/summary.png (three panels, one per hypothesis) from the CSV
logs written by run_h1_bottleneck.py, run_h2_selection.py, run_h3_homophily.py.

Usage:  python3 make_summary_figure.py
"""

import csv
from collections import defaultdict
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE, GREY = "#1f6fb4", "#d9731a", "#666666"


def read(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def final_by(rows, key, gen_col="generation", value="topo_similarity"):
    """Value at the last generation, grouped by `key`: {key: [values over seeds]}."""
    last = max(int(r[gen_col]) for r in rows)
    out = defaultdict(list)
    for r in rows:
        if int(r[gen_col]) == last:
            out[float(r[key])].append(float(r[value]))
    return out


def main():
    h1 = final_by(read("results/h1/h1_bottleneck_log.csv"), "bottleneck_fraction")
    h2_rows = read("results/h2/h2_selection_log.csv")
    h2_topo = final_by(h2_rows, "n_candidates")
    h2_prec = final_by(h2_rows, "n_candidates", value="communication_precision")

    h3_seed = read("results/h3/h3_summary_by_seed.csv")
    h3_topo, h3_formed = defaultdict(list), defaultdict(list)
    for r in h3_seed:
        h = float(r["homophily"])
        h3_topo[h].append(float(r["mean_topo_similarity"]))
        h3_formed[h].append(1.0 if int(r["n_qualifying_values"]) > 0 else 0.0)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))

    # --- H1
    ax = axes[0]
    keys = sorted(h1, reverse=True)  # 1.0 (no bottleneck) ... 0.15 (tight)
    xs = range(len(keys))
    for x, k in zip(xs, keys):
        ax.scatter([x] * len(h1[k]), h1[k], s=10, color=BLUE, alpha=0.25)
    ax.errorbar(xs, [statistics.mean(h1[k]) for k in keys],
                yerr=[statistics.stdev(h1[k]) for k in keys],
                fmt="o-", color=BLUE, capsize=3, lw=2)
    ax.set_xticks(list(xs)); ax.set_xticklabels([str(k) for k in keys])
    ax.set_xlabel("Bottleneck (fraction of meanings observed)\nloose → tight")
    ax.set_ylabel("Topographic similarity (final generation)")
    ax.set_title("H1  Bottleneck: supported", loc="left", fontweight="bold")

    # --- H2
    ax = axes[1]
    keys = sorted(h2_topo)
    xs = range(len(keys))
    ax.errorbar(xs, [statistics.mean(h2_topo[k]) for k in keys],
                yerr=[statistics.stdev(h2_topo[k]) for k in keys],
                fmt="o-", color=BLUE, capsize=3, lw=2, label="Compositionality")
    ax.set_ylim(0, 0.6)
    ax.set_xticks(list(xs)); ax.set_xticklabels([str(int(k)) for k in keys])
    ax.set_xlabel("Candidates per generation (selection strength)")
    ax.set_ylabel("Topographic similarity", color=BLUE)
    ax2 = ax.twinx()
    ax2.plot(list(xs), [statistics.mean(h2_prec[k]) for k in keys], "s--", color=ORANGE,
             lw=2, label="Communication precision")
    ax2.set_ylim(0.8, 1.0)
    ax2.set_ylabel("Communication precision", color=ORANGE)
    ax.set_title("H2  Selection: weak / inconclusive", loc="left", fontweight="bold")

    # --- H3
    ax = axes[2]
    keys = sorted(h3_topo, reverse=True)
    ax.plot(keys, [statistics.mean(h3_formed[k]) for k in keys], "o-", color=BLUE, lw=2)
    ax.set_ylim(-0.02, 1.05)
    ax.set_ylabel("P(clan-specific structure forms)", color=BLUE)
    ax.set_xlabel("Homophily (P example comes from own clan)")
    ax.invert_xaxis()
    ax3 = ax.twinx()
    ax3.plot(keys, [statistics.mean(h3_topo[k]) for k in keys], "s--", color=ORANGE, lw=2)
    ax3.set_ylim(0, 0.7)
    ax3.set_ylabel("Topographic similarity", color=ORANGE)
    ax.set_title("H3  Homophily: supported", loc="left", fontweight="bold")

    for a in axes:
        a.spines["top"].set_visible(False)
    plt.tight_layout()
    plt.savefig("results/summary.png", dpi=170)
    print("Saved results/summary.png")


if __name__ == "__main__":
    main()
