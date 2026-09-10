"""
Test de H3, version enrichie : grille resserrée de valeurs d'homophilie
pour localiser précisément le seuil d'effondrement identifié entre 0.8 et
0.5, avec 30 graines par condition (déjà validé comme nécessaire pour la
robustesse dans la version précédente).

Nouveauté : en plus de la compositionnalité et de l'indice de
différenciation (qui devient peu fiable à faible homophilie, faute de
valeurs qualifiées), on mesure la PROBABILITÉ QU'UNE STRUCTURE STABLE SE
FORME DU TOUT (fraction de graines ayant au moins une valeur qualifiée).
Contrairement à l'indice de différenciation, cette mesure reste calculable
sur toutes les graines à chaque niveau d'homophilie, sans donnée
manquante - elle documente proprement ce qui était jusqu'ici une limite
plutôt qu'un résultat.

Usage :
    python3 run_experiment_h3.py
"""

import csv
import statistics
from pathlib import Path

import matplotlib.pyplot as plt

from iterated_learning import run_simulation_h3, VALUES_PER_DIM, N_DIMS

BOTTLENECK = 0.5
N_GENERATIONS = 40
N_SEEDS = 30
HOMOPHILY_VALUES = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.3, 0.2]
MUTATION_RATE = 0.05
OUTPUT_DIR = Path("results_h3")
OUTPUT_DIR.mkdir(exist_ok=True)

N_CLANS = VALUES_PER_DIM[0]
MIN_CLANS_WITH_CHUNK = 4


def differentiation_index(final_learned_chunks, min_clans_with_chunk=MIN_CLANS_WITH_CHUNK):
    """Pour chaque (dimension, valeur) parmi unité et individu, combien de
    chunks DISTINCTS les clans utilisent-ils ? Ne compte que les valeurs
    où au moins `min_clans_with_chunk` clans ont effectivement formé un
    chunk. Renvoie (indice_moyen, nombre_de_valeurs_qualifiées) ; l'indice
    peut valoir None si aucune valeur n'atteint le seuil.

    IMPORTANT : final_learned_chunks doit être un instantané pris juste
    après learn(), AVANT produce_all()."""
    ratios = []
    for d in range(1, N_DIMS):
        for v in range(VALUES_PER_DIM[d]):
            chunks_seen = [clan_chunks[(d, v)] for clan_chunks in final_learned_chunks
                           if (d, v) in clan_chunks]
            if len(chunks_seen) >= min_clans_with_chunk:
                ratios.append(len(set(chunks_seen)) / len(chunks_seen))
    if not ratios:
        return None, 0
    return statistics.mean(ratios), len(ratios)


def main():
    csv_path = OUTPUT_DIR / "h3_homophily_log.csv"
    rows = []
    summary = []  # (homophily, seed, mean_topo, diff_idx_or_None, n_qualified, structure_formed)

    for homophily in HOMOPHILY_VALUES:
        for seed in range(N_SEEDS):
            result = run_simulation_h3(
                n_generations=N_GENERATIONS,
                bottleneck_fraction=BOTTLENECK,
                homophily=homophily,
                mutation_rate=MUTATION_RATE,
                seed=seed,
            )
            final_scores = result["topo_by_gen"][-1]
            diff_idx, n_qualified = differentiation_index(result["final_learned_chunks"])
            structure_formed = n_qualified > 0

            for clan, score in enumerate(final_scores):
                rows.append([homophily, seed, clan, f"{score:.4f}"])

            mean_topo = statistics.mean(final_scores)
            summary.append((homophily, seed, mean_topo, diff_idx, n_qualified, structure_formed))
            diff_display = f"{diff_idx:.3f}" if diff_idx is not None else "N/A"
            print(f"homophily={homophily} seed={seed} -> "
                  f"topo moyen={mean_topo:.3f}  differentiation={diff_display}  "
                  f"(sur {n_qualified} valeurs qualifiées)")

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["homophily", "seed", "clan", "topo_similarity_finale"])
        writer.writerows(rows)

    # -------------------------------------------------------------------
    # Résumé par valeur d'homophilie : les TROIS mesures
    # -------------------------------------------------------------------
    print("\n--- Résumé par force d'homophilie ---")
    homophily_means_topo = {}
    homophily_means_diff = {}
    homophily_formation_prob = {}
    homophily_n_exploitable = {}

    for h in HOMOPHILY_VALUES:
        rows_h = [s for s in summary if s[0] == h]
        topos = [m for hh, s, m, d, n, f in rows_h]
        diffs = [d for hh, s, m, d, n, f in rows_h if d is not None]
        formed = [f for hh, s, m, d, n, f in rows_h]

        homophily_means_topo[h] = statistics.mean(topos)
        homophily_means_diff[h] = statistics.mean(diffs) if diffs else None
        homophily_formation_prob[h] = sum(formed) / len(formed)
        homophily_n_exploitable[h] = len(diffs)

        diff_display = f"{homophily_means_diff[h]:.3f}" if diffs else "N/A"
        print(f"homophily={h}: topo={statistics.mean(topos):.3f}  "
              f"differentiation={diff_display} ({len(diffs)}/{N_SEEDS} graines exploitables)  "
              f"probabilite_de_formation={homophily_formation_prob[h]:.3f}")

    # -------------------------------------------------------------------
    # Graphique à trois volets
    # -------------------------------------------------------------------
    import math
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 5))

    ax1.plot(HOMOPHILY_VALUES, [homophily_means_topo[h] for h in HOMOPHILY_VALUES], "o-")
    ax1.set_xlabel("Force de l'homophilie")
    ax1.set_ylabel("Similarité topographique moyenne")
    ax1.set_title("Compositionnalité")
    ax1.invert_xaxis()

    diff_values = [homophily_means_diff[h] if homophily_means_diff[h] is not None else math.nan
                   for h in HOMOPHILY_VALUES]
    ax2.plot(HOMOPHILY_VALUES, diff_values, "o-", color="orange")
    # annoter chaque point avec le nombre de graines exploitables
    for h in HOMOPHILY_VALUES:
        if homophily_means_diff[h] is not None:
            ax2.annotate(f"n={homophily_n_exploitable[h]}",
                         (h, homophily_means_diff[h]),
                         textcoords="offset points", xytext=(0, 8), fontsize=8)
    ax2.set_xlabel("Force de l'homophilie")
    ax2.set_ylabel("Indice de différenciation entre clans")
    ax2.set_title("Différenciation (quand mesurable)")
    ax2.invert_xaxis()

    ax3.plot(HOMOPHILY_VALUES, [homophily_formation_prob[h] for h in HOMOPHILY_VALUES],
             "o-", color="green")
    ax3.set_xlabel("Force de l'homophilie")
    ax3.set_ylabel("Fraction de graines avec structure formée")
    ax3.set_title(f"Probabilité de formation de structure\n(sur {N_SEEDS} graines, sans donnée manquante)")
    ax3.invert_xaxis()
    ax3.set_ylim(-0.05, 1.05)

    fig.suptitle(f"H3 : gradient d'homophilie (goulot={BOTTLENECK}, {N_SEEDS} graines par condition)")
    plt.tight_layout()
    fig_path = OUTPUT_DIR / "h3_homophily_plot.png"
    plt.savefig(fig_path, dpi=150)
    print(f"\nGraphique sauvegardé : {fig_path}")
    print(f"Log complet sauvegardé : {csv_path}")


if __name__ == "__main__":
    main()
