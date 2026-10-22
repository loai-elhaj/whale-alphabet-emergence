"""
H2 - Selection for communication precision.

Each generation, N independent candidate learners are produced (each from its
own sample of the bottleneck); only the candidate with the highest
communication precision (fraction of meanings with a unique signal) is kept.
N = 1 is the reference (no selection). Does stronger selection increase
compositionality?

Bonferroni correction is applied because three conditions are compared to the
same reference.

Usage:  python3 run_h2_selection.py
Output: results/h2/h2_selection_log.csv, results/h2/h2_selection_plot.png
"""

import csv
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu

from iterated_learning import run_simulation

BOTTLENECK = 0.7
N_GENERATIONS = 40
N_SEEDS = 20
N_CANDIDATES_LIST = [1, 3, 6, 10]  # 1 = reference (no selection)
REFERENCE = 1
MUTATION_RATE = 0.05
OUTPUT_DIR = Path("results/h2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    csv_path = OUTPUT_DIR / "h2_selection_log.csv"
    curves = {}  # n_candidates -> list (per seed) of lists (per generation)
    final = {}   # n_candidates -> list of (topo, chunks, precision)

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["n_candidates", "seed", "generation", "topo_similarity",
                         "n_learned_chunks", "communication_precision"])
        for n in N_CANDIDATES_LIST:
            curves[n], final[n] = [], []
            for seed in range(N_SEEDS):
                res = run_simulation(N_GENERATIONS, BOTTLENECK, MUTATION_RATE, seed,
                                     n_candidates=n)
                s, c, p = res["scores"], res["chunk_counts"], res["precisions"]
                curves[n].append(s)
                final[n].append((s[-1], c[-1], p[-1]))
                for gen, (si, ci, pi) in enumerate(zip(s, c, p)):
                    writer.writerow([n, seed, gen, f"{si:.4f}", ci, f"{pi:.4f}"])
                f.flush()
                print(f"n_candidates={n} seed={seed} -> final topo={s[-1]:.3f} chunks={c[-1]}")

    print("\n--- Summary by selection strength (last generation) ---")
    for n in N_CANDIDATES_LIST:
        topos = [t for t, c, p in final[n]]
        chunks = [c for t, c, p in final[n]]
        precs = [p for t, c, p in final[n]]
        print(f"n_candidates={n}: topo={statistics.mean(topos):.3f} +/- {statistics.stdev(topos):.3f}  "
              f"chunks={statistics.mean(chunks):.1f}/22  precision={statistics.mean(precs):.3f}")

    comparisons = [n for n in N_CANDIDATES_LIST if n != REFERENCE]
    alpha = 0.05 / len(comparisons)
    print(f"\n--- Mann-Whitney U vs reference (n_candidates={REFERENCE}), one-sided ---")
    print(f"Bonferroni alpha = 0.05/{len(comparisons)} = {alpha:.4f}")
    ref = [t for t, c, p in final[REFERENCE]]
    for n in comparisons:
        _, p = mannwhitneyu([t for t, c, pp in final[n]], ref, alternative="greater")
        print(f"n_candidates={n} > reference ?  p = {p:.4e}  -> "
              f"{'significant' if p < alpha else 'not significant'}")

    plt.figure(figsize=(8, 5))
    for n in N_CANDIDATES_LIST:
        means = [statistics.mean(g) for g in zip(*curves[n])]
        stds = [statistics.stdev(g) for g in zip(*curves[n])]
        gens = list(range(len(means)))
        label = "no selection (reference)" if n == REFERENCE else f"{n} candidates"
        plt.plot(gens, means, label=label)
        plt.fill_between(gens, [m - s for m, s in zip(means, stds)],
                         [m + s for m, s in zip(means, stds)], alpha=0.12)
    plt.xlabel("Generation")
    plt.ylabel("Topographic similarity (compositionality)")
    plt.title(f"H2: selection for communication precision (bottleneck = {BOTTLENECK}, "
              f"{N_SEEDS} seeds)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "h2_selection_plot.png", dpi=150)
    print(f"\nSaved: {OUTPUT_DIR / 'h2_selection_plot.png'} and {csv_path}")


if __name__ == "__main__":
    main()
