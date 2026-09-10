"""
Test de H2, version enrichie : au lieu d'une seule intensité de sélection
(6 candidats), on teste un gradient (1, 3, 6, 10 candidats), avec 20 graines
par condition pour une vraie robustesse statistique.

n_candidates=1 sert de référence (= H1 seul, sans sélection).

Comme on compare plusieurs conditions à la même référence, on applique une
correction de Bonferroni au seuil de significativité (0.05 / nombre de
comparaisons), pour ne pas surestimer la confiance qu'on peut avoir dans
un résultat significatif obtenu par hasard sur plusieurs tests.

Usage :
    python3 run_experiment_h2.py
"""

import csv
import statistics
from pathlib import Path

import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu

from iterated_learning import run_simulation

BOTTLENECK = 0.7
N_GENERATIONS = 40
N_SEEDS = 20
N_CANDIDATES_LIST = [1, 3, 6, 10]  # 1 = reference (pas de selection)
REFERENCE = 1
MUTATION_RATE = 0.05
OUTPUT_DIR = Path("results_h2")
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    csv_path = OUTPUT_DIR / "h2_selection_log.csv"
    all_results = {}  # n_candidates -> liste de listes de scores (une par graine)
    all_final = {}    # n_candidates -> liste des (topo, chunks, precision) finaux

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["n_candidates", "seed", "generation", "topo_similarity",
                          "n_learned_chunks", "communication_precision"])

        for n_candidates in N_CANDIDATES_LIST:
            all_results[n_candidates] = []
            all_final[n_candidates] = []
            for seed in range(N_SEEDS):
                result = run_simulation(
                    n_generations=N_GENERATIONS,
                    bottleneck_fraction=BOTTLENECK,
                    mutation_rate=MUTATION_RATE,
                    seed=seed,
                    n_candidates=n_candidates,
                )
                scores = result["scores"]
                chunks = result["chunk_counts"]
                precisions = result["precisions"]

                all_results[n_candidates].append(scores)
                all_final[n_candidates].append((scores[-1], chunks[-1], precisions[-1]))

                for gen, (s, c, p) in enumerate(zip(scores, chunks, precisions)):
                    writer.writerow([n_candidates, seed, gen, f"{s:.4f}", c, f"{p:.4f}"])
                f.flush()
                print(f"n_candidates={n_candidates} seed={seed} -> "
                      f"score final = {scores[-1]:.3f}  chunks final = {chunks[-1]}")

    # -------------------------------------------------------------------
    # Résumé par condition
    # -------------------------------------------------------------------
    print("\n--- Résumé par intensité de sélection ---")
    for n_candidates in N_CANDIDATES_LIST:
        topos = [t for t, c, p in all_final[n_candidates]]
        chunks_vals = [c for t, c, p in all_final[n_candidates]]
        precisions = [p for t, c, p in all_final[n_candidates]]
        print(f"n_candidates={n_candidates}: "
              f"topo={statistics.mean(topos):.3f} ± {statistics.stdev(topos):.3f}  "
              f"chunks={statistics.mean(chunks_vals):.1f}/22  "
              f"precision={statistics.mean(precisions):.3f}")

    # -------------------------------------------------------------------
    # Tests statistiques : chaque condition vs la référence (n_candidates=1)
    # Correction de Bonferroni pour comparaisons multiples
    # -------------------------------------------------------------------
    comparisons = [n for n in N_CANDIDATES_LIST if n != REFERENCE]
    bonferroni_threshold = 0.05 / len(comparisons)
    print(f"\n--- Tests de Mann-Whitney vs référence (n_candidates={REFERENCE}) ---")
    print(f"Seuil de significativité corrigé (Bonferroni, {len(comparisons)} comparaisons) "
          f"= 0.05 / {len(comparisons)} = {bonferroni_threshold:.4f}")

    ref_topos = [t for t, c, p in all_final[REFERENCE]]
    for n_candidates in comparisons:
        topos = [t for t, c, p in all_final[n_candidates]]
        stat, p = mannwhitneyu(topos, ref_topos, alternative="greater")
        verdict = "SIGNIFICATIF" if p < bonferroni_threshold else "non significatif"
        print(f"n_candidates={n_candidates} > référence ? p = {p:.4e}  -> {verdict}")

    # -------------------------------------------------------------------
    # Graphique : courbes de compositionnalité au fil des générations
    # -------------------------------------------------------------------
    plt.figure(figsize=(8, 5))
    for n_candidates in N_CANDIDATES_LIST:
        runs = all_results[n_candidates]
        means = [statistics.mean(gen_scores) for gen_scores in zip(*runs)]
        stds = [statistics.stdev(gen_scores) if len(gen_scores) > 1 else 0
                for gen_scores in zip(*runs)]
        generations = list(range(len(means)))
        label = "sans sélection (référence)" if n_candidates == REFERENCE else f"{n_candidates} candidats"
        plt.plot(generations, means, label=label)
        plt.fill_between(
            generations,
            [m - s for m, s in zip(means, stds)],
            [m + s for m, s in zip(means, stds)],
            alpha=0.12,
        )

    plt.xlabel("Génération")
    plt.ylabel("Similarité topographique (compositionnalité)")
    plt.title(f"Effet de l'intensité de sélection par précision de communication (goulot={BOTTLENECK})\n"
               f"({N_SEEDS} graines par condition, moyenne ± écart-type)")
    plt.legend()
    plt.tight_layout()
    fig_path = OUTPUT_DIR / "h2_selection_plot.png"
    plt.savefig(fig_path, dpi=150)
    print(f"\nGraphique sauvegardé : {fig_path}")
    print(f"Log complet sauvegardé : {csv_path}")


if __name__ == "__main__":
    main()
