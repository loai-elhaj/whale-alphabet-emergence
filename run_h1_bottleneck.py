"""
H1 - Transmission bottleneck.

Does a tighter bottleneck (smaller fraction of meanings observed by each new
generation) increase compositionality (topographic similarity) and the number
of chunks learned?

Usage:  python3 run_h1_bottleneck.py
Output: results/h1/h1_bottleneck_log.csv, results/h1/h1_bottleneck_plot.png
"""

import csv
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu

from iterated_learning import run_simulation

BOTTLENECKS = [1.0, 0.7, 0.5, 0.3, 0.15]  # fraction of meanings observed
N_GENERATIONS = 40
N_SEEDS = 20
MUTATION_RATE = 0.05
OUTPUT_DIR = Path("results/h1")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    csv_path = OUTPUT_DIR / "h1_bottleneck_log.csv"
    curves = {}  # bottleneck -> list (per seed) of lists (per generation) of scores
    final = {}   # bottleneck -> list (per seed) of (final topo, final chunks)

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["bottleneck_fraction", "seed", "generation",
                         "topo_similarity", "n_learned_chunks"])
        for b in BOTTLENECKS:
            curves[b], final[b] = [], []
            for seed in range(N_SEEDS):
                res = run_simulation(N_GENERATIONS, b, MUTATION_RATE, seed)
                scores, chunks = res["scores"], res["chunk_counts"]
                curves[b].append(scores)
                final[b].append((scores[-1], chunks[-1]))
                for gen, (s, c) in enumerate(zip(scores, chunks)):
                    writer.writerow([b, seed, gen, f"{s:.4f}", c])
                f.flush()
                print(f"bottleneck={b:.2f} seed={seed} -> final topo={scores[-1]:.3f} "
                      f"chunks={chunks[-1]}")

    print("\n--- Summary (last generation, mean +/- sd over seeds) ---")
    for b in BOTTLENECKS:
        topos = [t for t, c in final[b]]
        chunks = [c for t, c in final[b]]
        print(f"bottleneck={b}: topo={statistics.mean(topos):.3f} +/- {statistics.stdev(topos):.3f}  "
              f"chunks={statistics.mean(chunks):.1f}/22")

    # One-sided Mann-Whitney between consecutive conditions: is the tighter
    # bottleneck more compositional than the previous (looser) one?
    n_tests = len(BOTTLENECKS) - 1
    alpha = 0.05 / n_tests
    print(f"\n--- Mann-Whitney U, consecutive conditions (Bonferroni alpha = 0.05/{n_tests} = {alpha:.4f}) ---")
    for loose, tight in zip(BOTTLENECKS[:-1], BOTTLENECKS[1:]):
        _, p = mannwhitneyu([t for t, c in final[tight]], [t for t, c in final[loose]],
                            alternative="greater")
        print(f"bottleneck {tight} > {loose} ?  p = {p:.3e}  -> "
              f"{'significant' if p < alpha else 'not significant'}")

    plt.figure(figsize=(8, 5))
    for b in BOTTLENECKS:
        means = [statistics.mean(g) for g in zip(*curves[b])]
        stds = [statistics.stdev(g) for g in zip(*curves[b])]
        gens = list(range(len(means)))
        plt.plot(gens, means, label=f"bottleneck = {b}")
        plt.fill_between(gens, [m - s for m, s in zip(means, stds)],
                         [m + s for m, s in zip(means, stds)], alpha=0.15)
    plt.xlabel("Generation")
    plt.ylabel("Topographic similarity (compositionality)")
    plt.title(f"H1: effect of the transmission bottleneck ({N_SEEDS} seeds, mean ± sd)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "h1_bottleneck_plot.png", dpi=150)
    print(f"\nSaved: {OUTPUT_DIR / 'h1_bottleneck_plot.png'} and {csv_path}")


if __name__ == "__main__":
    main()
