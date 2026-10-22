"""
H3 - Homophily and clan differentiation.

Six clan lineages evolve in parallel. For each learning example, with
probability `homophily` the example comes from the learner's own clan, and
with probability 1 - homophily from a random other clan (same unit/individual
pair, but the signal that other clan produced for it).

Three measures per condition:
  1. compositionality (mean topographic similarity across the 6 clans);
  2. differentiation index: for each (unit/individual) value for which at
     least MIN_CLANS_WITH_CHUNK clans learned a chunk, the fraction of
     DISTINCT chunks among those clans (1.0 = every clan uses its own chunk).
     It is undefined when no value reaches the threshold;
  3. probability of structure formation: fraction of seeds in which at least
     one value reaches the threshold (always defined).

Usage:  python3 run_h3_homophily.py
Output: results/h3/h3_homophily_log.csv (per clan), results/h3/h3_summary_by_seed.csv,
        results/h3/h3_homophily_plot.png
"""

import csv
import math
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from iterated_learning import run_simulation_h3, VALUES_PER_DIM, N_DIMS

BOTTLENECK = 0.5
N_GENERATIONS = 40
N_SEEDS = 30
HOMOPHILY_VALUES = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.3, 0.2]
MUTATION_RATE = 0.05
MIN_CLANS_WITH_CHUNK = 4
OUTPUT_DIR = Path("results/h3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def differentiation_index(final_learned_chunks, min_clans_with_chunk=MIN_CLANS_WITH_CHUNK):
    """Returns (mean index, number of qualifying values); the index is None
    if no value qualifies. `final_learned_chunks` must be a snapshot taken
    right after learn() and BEFORE produce_all()."""
    ratios = []
    for d in range(1, N_DIMS):  # unit and individual dimensions
        for v in range(VALUES_PER_DIM[d]):
            seen = [clan[(d, v)] for clan in final_learned_chunks if (d, v) in clan]
            if len(seen) >= min_clans_with_chunk:
                ratios.append(len(set(seen)) / len(seen))
    if not ratios:
        return None, 0
    return statistics.mean(ratios), len(ratios)


def main():
    clan_csv = OUTPUT_DIR / "h3_homophily_log.csv"
    seed_csv = OUTPUT_DIR / "h3_summary_by_seed.csv"
    summary = []  # (homophily, seed, mean_topo, diff_idx, n_qualified)

    with open(clan_csv, "w", newline="") as f1, open(seed_csv, "w", newline="") as f2:
        w1, w2 = csv.writer(f1), csv.writer(f2)
        w1.writerow(["homophily", "seed", "clan", "final_topo_similarity"])
        w2.writerow(["homophily", "seed", "mean_topo_similarity",
                     "differentiation_index", "n_qualifying_values"])
        for h in HOMOPHILY_VALUES:
            for seed in range(N_SEEDS):
                res = run_simulation_h3(N_GENERATIONS, BOTTLENECK, h, MUTATION_RATE, seed)
                final_scores = res["topo_by_gen"][-1]
                diff, n_q = differentiation_index(res["final_learned_chunks"])
                mean_topo = statistics.mean(final_scores)
                summary.append((h, seed, mean_topo, diff, n_q))
                for clan, score in enumerate(final_scores):
                    w1.writerow([h, seed, clan, f"{score:.4f}"])
                w2.writerow([h, seed, f"{mean_topo:.4f}",
                             "" if diff is None else f"{diff:.4f}", n_q])
                f1.flush(); f2.flush()
                d_txt = "N/A" if diff is None else f"{diff:.3f}"
                print(f"homophily={h} seed={seed} -> topo={mean_topo:.3f} "
                      f"differentiation={d_txt} (qualifying values: {n_q})")

    print("\n--- Summary by homophily ---")
    topo_m, diff_m, formed_p, n_diff = {}, {}, {}, {}
    for h in HOMOPHILY_VALUES:
        rows = [s for s in summary if s[0] == h]
        topos = [r[2] for r in rows]
        diffs = [r[3] for r in rows if r[3] is not None]
        topo_m[h] = statistics.mean(topos)
        diff_m[h] = statistics.mean(diffs) if diffs else math.nan
        formed_p[h] = sum(1 for r in rows if r[4] > 0) / len(rows)
        n_diff[h] = len(diffs)
        print(f"homophily={h}: topo={topo_m[h]:.3f}  differentiation={diff_m[h]:.3f} "
              f"({n_diff[h]}/{N_SEEDS} seeds)  P(structure forms)={formed_p[h]:.3f}")

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 5))
    ax1.plot(HOMOPHILY_VALUES, [topo_m[h] for h in HOMOPHILY_VALUES], "o-")
    ax1.set_title("Compositionality")
    ax1.set_ylabel("Mean topographic similarity")
    ax2.plot(HOMOPHILY_VALUES, [diff_m[h] for h in HOMOPHILY_VALUES], "o-", color="orange")
    for h in HOMOPHILY_VALUES:
        if not math.isnan(diff_m[h]):
            ax2.annotate(f"n={n_diff[h]}", (h, diff_m[h]), textcoords="offset points",
                         xytext=(0, 8), fontsize=8)
    ax2.set_title("Clan differentiation (when measurable)")
    ax2.set_ylabel("Differentiation index")
    ax3.plot(HOMOPHILY_VALUES, [formed_p[h] for h in HOMOPHILY_VALUES], "o-", color="green")
    ax3.set_title(f"Probability that a stable structure forms\n(over {N_SEEDS} seeds, no missing data)")
    ax3.set_ylabel("Fraction of seeds")
    ax3.set_ylim(-0.05, 1.05)
    for ax in (ax1, ax2, ax3):
        ax.set_xlabel("Homophily (probability that an example comes from own clan)")
        ax.invert_xaxis()
    fig.suptitle(f"H3: homophily gradient (bottleneck = {BOTTLENECK}, {N_SEEDS} seeds per condition)")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "h3_homophily_plot.png", dpi=150)
    print(f"\nSaved: {OUTPUT_DIR / 'h3_homophily_plot.png'}, {clan_csv}, {seed_csv}")


if __name__ == "__main__":
    main()
