"""
Supplementary check for H2: do the results change when the simulation runs
longer? At bottleneck 0.7, compositionality is still rising at generation 40,
so a selection effect might need more generations to appear.

Compares no selection (1 candidate) with strong selection (10 candidates) over
150 generations, 20 seeds each.

Usage:  python3 run_h2_long.py
Output: results/h2/h2_long_log.csv
"""

import csv
import statistics
from pathlib import Path

from scipy.stats import mannwhitneyu

from iterated_learning import run_simulation

BOTTLENECK = 0.7
N_GENERATIONS = 150
N_SEEDS = 20
CONDITIONS = [1, 10]
OUTPUT_DIR = Path("results/h2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    finals = {n: [] for n in CONDITIONS}
    with open(OUTPUT_DIR / "h2_long_log.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n_candidates", "seed", "generation", "topo_similarity"])
        for n in CONDITIONS:
            for seed in range(N_SEEDS):
                res = run_simulation(N_GENERATIONS, BOTTLENECK, 0.05, seed, n_candidates=n)
                for gen, s in enumerate(res["scores"]):
                    if gen % 10 == 0 or gen == N_GENERATIONS - 1:
                        w.writerow([n, seed, gen, f"{s:.4f}"])
                finals[n].append(res["scores"][-1])
                print(f"n_candidates={n} seed={seed} -> final topo={res['scores'][-1]:.3f}", flush=True)
    for n in CONDITIONS:
        print(f"n_candidates={n}: topo at generation {N_GENERATIONS - 1} = "
              f"{statistics.mean(finals[n]):.3f} +/- {statistics.stdev(finals[n]):.3f}")
    _, p = mannwhitneyu(finals[10], finals[1], alternative="greater")
    print(f"10 candidates > 1 candidate ?  one-sided p = {p:.4f}")


if __name__ == "__main__":
    main()
