"""
Lance l'expérience H1 : effet du goulot de transmission sur l'émergence
de la compositionnalité, sur plusieurs graines indépendantes pour la
robustesse statistique.

Usage (depuis le dossier whale_lang, environnement virtuel activé) :
    python3 run_experiment.py
"""

import csv
import statistics
from pathlib import Path

import matplotlib.pyplot as plt

from iterated_learning import run_simulation

# ---------------------------------------------------------------------------
# Paramètres de l'expérience
# ---------------------------------------------------------------------------

BOTTLENECKS = [1.0, 0.7, 0.5, 0.3, 0.15]  # fraction de sens observés
N_GENERATIONS = 40
N_SEEDS = 20                # nombre de graines indépendantes par condition
MUTATION_RATE = 0.05
OUTPUT_DIR = Path("results")
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    csv_path = OUTPUT_DIR / "topo_similarity_log.csv"
    all_results = {}  # bottleneck -> liste de listes de scores (une par graine)

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["bottleneck_fraction", "seed", "generation", "topo_similarity", "n_learned_chunks"])
        for bottleneck in BOTTLENECKS:
            all_results[bottleneck] = []
            for seed in range(N_SEEDS):
                result = run_simulation(                    
                    n_generations=N_GENERATIONS,
                    bottleneck_fraction=bottleneck,
                    mutation_rate=MUTATION_RATE,
                    seed=seed,
                ) 
                scores, chunk_counts = result["scores"], result["chunk_counts"]
                all_results[bottleneck].append(scores)
                # écriture incrémentale (crash-safe) : une ligne par génération
                for gen, (score, n_chunks) in enumerate(zip(scores, chunk_counts)):
                    writer.writerow([bottleneck, seed, gen, f"{score:.4f}", n_chunks])
                f.flush()
                print(f"bottleneck={bottleneck:.2f} seed={seed} -> "
                      f"score final = {scores[-1]:.3f}")

    # -----------------------------------------------------------------------
    # Graphique : moyenne +/- écart-type par condition, au fil des générations
    # -----------------------------------------------------------------------
    plt.figure(figsize=(8, 5))
    for bottleneck in BOTTLENECKS:
        runs = all_results[bottleneck]  # liste (n_seeds) de listes (n_generations)
        means = [statistics.mean(gen_scores) for gen_scores in zip(*runs)]
        stds = [statistics.stdev(gen_scores) if len(gen_scores) > 1 else 0
                for gen_scores in zip(*runs)]
        generations = list(range(len(means)))
        plt.plot(generations, means, label=f"goulot = {bottleneck}")
        plt.fill_between(
            generations,
            [m - s for m, s in zip(means, stds)],
            [m + s for m, s in zip(means, stds)],
            alpha=0.15,
        )

    plt.xlabel("Génération")
    plt.ylabel("Similarité topographique (compositionnalité)")
    plt.title("Effet du goulot de transmission sur l'émergence de la compositionnalité\n"
               f"({N_SEEDS} graines par condition, moyenne ± écart-type)")
    plt.legend()
    plt.tight_layout()
    fig_path = OUTPUT_DIR / "topo_similarity_plot.png"
    plt.savefig(fig_path, dpi=150)
    print(f"\nGraphique sauvegardé : {fig_path}")
    print(f"Log complet sauvegardé : {csv_path}")


if __name__ == "__main__":
    main()
