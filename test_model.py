"""Quick sanity checks (run: python3 test_model.py).

1. Regression guard: run_simulation(40, 0.7, seed=0) learns ~10 chunks at the
   last generation (NOT 22, which would mean chunks have priority over the
   lexicon in produce()).
2. A random language has topographic similarity close to 0.
3. The vectorised Levenshtein equals the scalar implementation.
4. Spearman correlation handles ties like scipy.
"""
import random

import numpy as np
from scipy.stats import spearmanr

import iterated_learning as il


def test_regression_guard():
    res = il.run_simulation(40, 0.7, mutation_rate=0.05, seed=0)
    assert 8 <= res["chunk_counts"][-1] <= 14, res["chunk_counts"][-1]


def test_random_language_near_zero():
    rng = random.Random(0)
    lang = {m: "".join(il.random_slot(rng) for _ in range(il.N_DIMS)) for m in il.all_meanings()}
    assert abs(il.topographic_similarity(lang)) < 0.05


def test_vectorised_levenshtein():
    rng = random.Random(1)
    sigs = ["".join(rng.choice(il.ALPHABET) for _ in range(6)) for _ in range(120)]
    i, j = np.triu_indices(len(sigs), 1)
    fast = il.pairwise_levenshtein(sigs, i, j)
    slow = np.array([il.levenshtein(sigs[a], sigs[b]) for a, b in zip(i, j)])
    assert (fast == slow).all()


def test_spearman_ties():
    x = [0, 1, 1, 2, 2, 2, 3, 3]
    y = [1, 1, 2, 2, 3, 3, 3, 4]
    assert abs(il.spearman_corr(x, y) - spearmanr(x, y)[0]) < 1e-9


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
