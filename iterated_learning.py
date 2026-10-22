"""
Iterated Learning Model (ILM) of sperm-whale-like coda evolution.

Question: can a transmission bottleneck (each generation sees only a fraction
of the previous generation's signals and must reconstruct the rest) make a
combinatorial ("alphabet-like") signal system emerge, rather than a
repertoire of unrelated holistic signals ("words")?

Model overview
--------------
- A *meaning* is a tuple of values on several dimensions. Here
  (vocal clan, social unit, individual) = (6, 5, 11) values -> 330 meanings.
  These sizes are modelling choices, not measured quantities.
- A *signal* is a fixed-length string (6 letters from a 6-letter alphabet),
  split into one 2-letter *slot* per dimension.
- Each agent has
    * a lexicon: exact memory of the (meaning -> signal) pairs it observed;
    * a chunk table: (dimension, value) -> 2-letter slot, induced from the
      observed examples when a majority (> 50 %) of the examples sharing that
      value carry the same slot.
- To produce a signal for a meaning:
    * known meaning -> recall it from the lexicon (copied with noise);
    * unknown meaning -> concatenate the chunks of its values; a missing
      chunk is invented once and then kept, to stay self-consistent.
- Compositionality is measured by topographic similarity: the Spearman rank
  correlation between pairwise distances in meaning space (Hamming) and in
  signal space (Levenshtein).

IMPORTANT (regression guard): produce() must NOT give chunks priority over
the lexicon. An earlier version did, which silently inflated results
(22/22 chunks learned). Reference check: run_simulation(40, 0.7, seed=0)
must give ~10 learned chunks at the last generation.
"""

import itertools
import random
from collections import Counter
from functools import lru_cache

import numpy as np
from scipy.stats import rankdata

# ---------------------------------------------------------------------------
# Meaning / signal space parameters
# ---------------------------------------------------------------------------

N_DIMS = 3
VALUES_PER_DIM = (6, 5, 11)  # vocal clans, social units per clan, individuals per unit
SLOT_LEN = 2
ALPHABET = "abcdef"


def all_meanings():
    """All possible meanings (Cartesian product of the dimensions)."""
    return list(itertools.product(*(range(v) for v in VALUES_PER_DIM)))


def random_slot(rng):
    """Random substring of length SLOT_LEN."""
    return "".join(rng.choice(list(ALPHABET)) for _ in range(SLOT_LEN))


@lru_cache(maxsize=None)
def levenshtein(a, b):
    """Classic Levenshtein edit distance (dynamic programming, cached)."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        curr = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,        # deletion
                curr[j - 1] + 1,    # insertion
                prev[j - 1] + cost  # substitution
            )
        prev = curr
    return prev[lb]


def spearman_corr(x, y):
    """Spearman rank correlation WITH proper handling of ties (average ranks).

    Ties are very frequent here (Hamming distances take only 4 values, and
    Levenshtein distances only 7). Breaking ties arbitrarily (e.g. with a bare
    argsort) is both biased and platform-dependent, so average ranks are used.
    """
    rx = rankdata(x, method="average")
    ry = rankdata(y, method="average")
    if rx.std() == 0 or ry.std() == 0:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])


def communication_precision(language):
    """Fraction of meanings whose signal is unique (shared with no other
    meaning). 1.0 = a listener could always recover the meaning from the
    signal alone."""
    signals = list(language.values())
    counts = Counter(signals)
    n_unique = sum(1 for s in signals if counts[s] == 1)
    return n_unique / len(signals)


class Agent:
    """Learns a language from examples, then must produce a signal for any
    meaning, seen or unseen."""

    def __init__(self, mutation_rate=0.0, seed=None):
        self.lexicon = {}   # meaning (tuple) -> signal (str): exact memory
        self.chunks = {}    # (dimension, value) -> substring
        self.mutation_rate = mutation_rate
        self.rng = random.Random(seed)

    def learn(self, examples):
        """Learn from a list of observed (meaning, signal) pairs."""
        self.lexicon = dict(examples)
        # Chunk induction: for each (dimension, value), if a MAJORITY (> 50 %)
        # of the examples sharing that value carry the same substring at the
        # right position, keep it as a chunk. (A strict-unanimity rule was
        # tried first and learned no chunk at all with 5 % copy noise.)
        MAJORITY_THRESHOLD = 0.5
        for d in range(N_DIMS):
            for v in range(VALUES_PER_DIM[d]):
                slots = [
                    signal[d * SLOT_LEN:(d + 1) * SLOT_LEN]
                    for meaning, signal in examples
                    if meaning[d] == v
                ]
                if len(slots) >= 2:
                    most_common_slot, count = Counter(slots).most_common(1)[0]
                    if count / len(slots) > MAJORITY_THRESHOLD:
                        self.chunks[(d, v)] = most_common_slot

    def _mutate(self, signal):
        if self.mutation_rate <= 0:
            return signal
        chars = list(signal)
        for i in range(len(chars)):
            if self.rng.random() < self.mutation_rate:
                chars[i] = self.rng.choice(list(ALPHABET))
        return "".join(chars)

    def produce(self, meaning):
        """Produce a signal for a meaning (known or unknown)."""
        if meaning in self.lexicon:
            return self._mutate(self.lexicon[meaning])

        # Unknown meaning: rebuild it from the known chunks
        slots = []
        for d in range(N_DIMS):
            v = meaning[d]
            if (d, v) in self.chunks:
                slots.append(self.chunks[(d, v)])
            else:
                # Missing chunk: invent one and keep it for consistency
                new_chunk = random_slot(self.rng)
                self.chunks[(d, v)] = new_chunk
                slots.append(new_chunk)
        signal = "".join(slots)
        self.lexicon[meaning] = signal  # stay consistent if asked again
        return signal

    def produce_all(self, meanings):
        """Produce the full language (dict meaning -> signal)."""
        return {m: self.produce(m) for m in meanings}


def pairwise_levenshtein(signals, i_idx, j_idx):
    """Vectorised Levenshtein distance for many pairs of EQUAL-length signals
    (same result as levenshtein(), just much faster for the ~54,000 pairs
    needed per topographic-similarity computation)."""
    codes = np.array([[ord(ch) for ch in s] for s in signals], dtype=np.int16)
    a, b = codes[i_idx], codes[j_idx]
    length = codes.shape[1]
    d = np.zeros((length + 1, length + 1, len(i_idx)), dtype=np.int16)
    d[:, 0] = np.arange(length + 1)[:, None]
    d[0, :] = np.arange(length + 1)[:, None]
    for i in range(1, length + 1):
        for j in range(1, length + 1):
            cost = (a[:, i - 1] != b[:, j - 1]).astype(np.int16)
            d[i, j] = np.minimum(np.minimum(d[i - 1, j] + 1, d[i, j - 1] + 1),
                                 d[i - 1, j - 1] + cost)
    return d[length, length].astype(float)


def topographic_similarity(language):
    """Topographic similarity of a full language (dict meaning -> signal).
    Between -1 and 1: close to 1 = strongly compositional, close to 0 =
    arbitrary (holistic). Pairwise distances: Hamming on meanings,
    Levenshtein on signals; then Spearman rank correlation."""
    meanings = list(language.keys())
    signals = list(language.values())
    n = len(meanings)
    m_arr = np.array(meanings)
    i_idx, j_idx = np.triu_indices(n, k=1)
    meaning_dists = (m_arr[i_idx] != m_arr[j_idx]).sum(axis=1)  # Hamming
    signal_dists = pairwise_levenshtein(signals, i_idx, j_idx)
    return spearman_corr(meaning_dists, signal_dists)


def run_simulation(n_generations, bottleneck_fraction, mutation_rate=0.05, seed=0,
                   n_candidates=1, meanings=None):
    """Run the iterated learning model over several generations.

    bottleneck_fraction : fraction of meanings the next generation observes.
    meanings : meanings to use (default: all 330).
    n_candidates : number of independent learners per generation (each with
        its own sample from the bottleneck). With n_candidates = 1 this is the
        plain bottleneck model (H1). With n_candidates > 1 only the candidate
        with the highest communication precision is kept (selection, H2).

    Returns a dict:
        "scores"       -> topographic similarity, one per generation
        "chunk_counts" -> number of learned chunks, one per generation
        "precisions"   -> communication precision, one per generation
        "final_agent"  -> Agent of the last generation
    """
    if meanings is None:
        meanings = all_meanings()

    rng = random.Random(seed)

    current_agent = Agent(mutation_rate=mutation_rate, seed=seed)
    current_agent.lexicon = {m: "".join(random_slot(rng) for _ in range(N_DIMS))
                             for m in meanings}
    language = dict(current_agent.lexicon)
    scores = [topographic_similarity(language)]
    learned_chunk_counts = [0]
    precisions = [communication_precision(language)]

    for gen in range(1, n_generations):
        full_language = current_agent.produce_all(meanings)
        n_observed = max(2, int(len(meanings) * bottleneck_fraction))

        best = None  # (precision, n_chunks, language, agent)
        for c in range(n_candidates):
            observed_meanings = rng.sample(meanings, n_observed)
            examples = [(m, full_language[m]) for m in observed_meanings]

            candidate = Agent(mutation_rate=mutation_rate, seed=seed + gen * 1000 + c)
            candidate.learn(examples)
            n_chunks = len(candidate.chunks)  # counted after learn(), before produce_all()
            candidate_language = candidate.produce_all(meanings)
            precision = communication_precision(candidate_language)

            if best is None or precision > best[0]:
                best = (precision, n_chunks, candidate_language, candidate)

        precision, n_chunks, language, current_agent = best
        scores.append(topographic_similarity(language))
        learned_chunk_counts.append(n_chunks)
        precisions.append(precision)

    return {
        "scores": scores,
        "chunk_counts": learned_chunk_counts,
        "precisions": precisions,
        "final_agent": current_agent,
    }


def meanings_for_clan(clan_value):
    """All (clan, unit, individual) meanings belonging to one clan."""
    return [m for m in all_meanings() if m[0] == clan_value]


def run_simulation_h3(n_generations, bottleneck_fraction, homophily, mutation_rate=0.05, seed=0):
    """Run one lineage per clan IN PARALLEL with a tunable homophily.

    homophily : probability that a learning example comes from the agent's
        own clan. With probability (1 - homophily) it comes from a randomly
        chosen OTHER clan (same (unit, individual) pair, but with the signal
        that other clan produced for it).
        homophily = 1.0 -> complete isolation between clans.

    Returns a dict:
        "topo_by_gen"          -> list (n_generations) of lists (n_clans) of scores
        "final_agents"         -> Agents of the last generation
        "final_learned_chunks" -> per-clan chunk tables snapshotted right after
                                  learn() and BEFORE produce_all() (otherwise
                                  invented chunks pollute the measure)
    """
    rng = random.Random(seed)
    n_clans = VALUES_PER_DIM[0]
    clan_meanings = [meanings_for_clan(c) for c in range(n_clans)]
    n_per_clan = len(clan_meanings[0])  # 55

    current_agents = []
    languages = []
    for c in range(n_clans):
        agent = Agent(mutation_rate=mutation_rate, seed=seed * 10 + c)
        agent.lexicon = {m: "".join(random_slot(rng) for _ in range(N_DIMS))
                         for m in clan_meanings[c]}
        current_agents.append(agent)
        languages.append(dict(agent.lexicon))

    topo_by_gen = [[topographic_similarity(languages[c]) for c in range(n_clans)]]
    learned_chunks_snapshot = [{} for _ in range(n_clans)]

    for gen in range(1, n_generations):
        full_languages = [current_agents[c].produce_all(clan_meanings[c])
                          for c in range(n_clans)]
        n_observed = max(2, int(n_per_clan * bottleneck_fraction))

        new_agents, new_languages = [], []
        for c in range(n_clans):
            examples = []
            for _ in range(n_observed):
                if rng.random() < homophily:
                    source_clan = c
                else:
                    source_clan = rng.choice([x for x in range(n_clans) if x != c])
                _, unit, indiv = rng.choice(clan_meanings[source_clan])
                own_meaning = (c, unit, indiv)
                borrowed_signal = full_languages[source_clan][(source_clan, unit, indiv)]
                examples.append((own_meaning, borrowed_signal))

            new_agent = Agent(mutation_rate=mutation_rate, seed=seed * 10 + c + gen * 1000)
            new_agent.learn(examples)
            learned_chunks_snapshot[c] = dict(new_agent.chunks)  # BEFORE produce_all!
            new_language = new_agent.produce_all(clan_meanings[c])
            new_agents.append(new_agent)
            new_languages.append(new_language)

        current_agents = new_agents
        languages = new_languages
        topo_by_gen.append([topographic_similarity(languages[c]) for c in range(n_clans)])

    return {"topo_by_gen": topo_by_gen, "final_agents": current_agents,
            "final_learned_chunks": learned_chunks_snapshot}
