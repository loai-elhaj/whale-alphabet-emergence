"""
Modèle d'apprentissage itéré (Iterated Learning Model) — MVP du projet cachalot.

Question testée (H1) : un goulot de transmission (chaque génération n'observe
qu'une fraction des exemples de la génération précédente et doit reconstruire
le reste) suffit-il à faire émerger une structure combinatoire (compositionnelle)
dans le langage, plutôt qu'un simple répertoire de signaux figés (holistique) ?

Principe général :
- Un "sens" (meaning) est un tuple de valeurs sur plusieurs dimensions,
  ex. (2, 0, 4) avec 3 dimensions et 5 valeurs possibles chacune.
- Un "signal" est une chaîne de caractères de longueur fixe, découpée en
  autant de "slots" que de dimensions.
- Chaque agent possède :
    - un lexique (mémorisation exacte des paires sens->signal observées)
    - une table de "chunks" (association dimension+valeur -> sous-chaîne),
      apprise en repérant des motifs cohérents dans les exemples observés
- Pour produire un signal :
    - si le sens est dans le lexique -> on le ressort (avec un peu de bruit
      de copie, pour simuler l'imperfection de reproduction motrice)
    - si le sens est inconnu -> on essaie de le reconstruire en concaténant
      les chunks connus pour chacune de ses valeurs ; si un chunk manque,
      on l'invente une fois et on le retient pour rester cohérent

La compositionnalité du langage d'une génération est mesurée par la
similarité topographique : corrélation entre les distances dans l'espace
des sens et les distances dans l'espace des signaux.
"""

import random
import itertools
from collections import Counter
import numpy as np


# ---------------------------------------------------------------------------
# Paramètres de l'espace des sens et des signaux
# ---------------------------------------------------------------------------

N_DIMS = 3
VALUES_PER_DIM = (6, 5, 11)  # clan vocal, unite sociale, individu
SLOT_LEN = 2
ALPHABET = "abcdef"


def all_meanings():
    """Retourne la liste de tous les sens possibles (produit cartésien des dimensions)."""
    return list(itertools.product(*(range(v) for v in VALUES_PER_DIM)))


def random_slot(rng):
    """Génère une sous-chaîne aléatoire de longueur SLOT_LEN."""
    return "".join(rng.choice(list(ALPHABET)) for _ in range(SLOT_LEN))


def levenshtein(a, b):
    """Distance de Levenshtein classique (programmation dynamique)."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        curr = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,       # suppression
                curr[j - 1] + 1,   # insertion
                prev[j - 1] + cost # substitution
            )
        prev = curr
    return prev[lb]


def spearman_corr(x, y):
    """Corrélation de rang de Spearman, implémentée sans scipy."""
    def rank(v):
        order = np.argsort(v)
        ranks = np.empty_like(order, dtype=float)
        ranks[order] = np.arange(len(v))
        return ranks
    rx, ry = rank(np.array(x)), rank(np.array(y))
    if rx.std() == 0 or ry.std() == 0:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])


def communication_precision(language):
    """Fraction des sens dont le signal est unique (sans ambiguïté avec
    aucun autre sens). 1.0 = communication parfaitement précise, un
    auditeur pourrait toujours deviner le bon sens à partir du signal seul."""
    signals = list(language.values())
    counts = Counter(signals)
    n_unique = sum(1 for s in signals if counts[s] == 1)
    return n_unique / len(signals)


class Agent:
    """Un agent qui apprend un langage à partir d'exemples, puis doit
    produire un signal pour n'importe quel sens (connu ou pas)."""

    def __init__(self, mutation_rate=0.0, seed=None):
        self.lexicon = {}   # sens (tuple) -> signal (str), mémorisation exacte
        self.chunks = {}    # (dimension, valeur) -> sous-chaîne
        self.mutation_rate = mutation_rate
        self.rng = random.Random(seed)

    def learn(self, examples):
        """Apprend à partir d'une liste de paires (sens, signal) observées."""
        self.lexicon = dict(examples)
        # Induction de chunks : pour chaque dimension et chaque valeur,
        # si une MAJORITÉ (>50%) des exemples partageant cette valeur ont
        # la même sous-chaîne au bon endroit, on retient cette sous-chaîne
        # comme chunk. Règle assouplie par rapport à l'unanimité stricte,
        # jugée trop rigide et peu réaliste (cf. README, section Limites).
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
        """Produit un signal pour un sens donné (connu ou inconnu)."""
        if meaning in self.lexicon:
            return self._mutate(self.lexicon[meaning])

        # Sens inconnu : on essaie de reconstruire à partir des chunks connus
        slots = []
        for d in range(N_DIMS):
            v = meaning[d]
            if (d, v) in self.chunks:
                slots.append(self.chunks[(d, v)])
            else:
                # Chunk manquant : on invente une fois, et on le retient
                # pour rester cohérent le reste de sa "vie"
                new_chunk = random_slot(self.rng)
                self.chunks[(d, v)] = new_chunk
                slots.append(new_chunk)
        signal = "".join(slots)
        self.lexicon[meaning] = signal  # pour cohérence si on redemande ce sens
        return signal

    def produce_all(self, meanings):
        """Produit le langage complet (dict sens->signal) sur une liste de sens."""
        return {m: self.produce(m) for m in meanings}


def topographic_similarity(language):
    """Calcule la similarité topographique d'un langage complet
    (dict sens->signal). Renvoie un score entre -1 et 1 :
    proche de 1 = fortement compositionnel, proche de 0 = arbitraire."""
    meanings = list(language.keys())
    meaning_dists, signal_dists = [], []
    for m1, m2 in itertools.combinations(meanings, 2):
        md = sum(1 for a, b in zip(m1, m2) if a != b)  # distance de Hamming
        sd = levenshtein(language[m1], language[m2])
        meaning_dists.append(md)
        signal_dists.append(sd)
    return spearman_corr(meaning_dists, signal_dists)


def run_simulation(n_generations, bottleneck_fraction, mutation_rate=0.05, seed=0,
                    n_candidates=1, meanings=None):
    """Fait tourner le modèle d'apprentissage itéré sur plusieurs générations.

    meanings : liste de sens à utiliser (par défaut, tous les 330 sens).
        Utile pour H3, où on veut restreindre la simulation aux sens d'un
        seul clan (isolement / homophilie).
    n_candidates : nombre de "candidats" indépendants générés à chaque
        génération (chacun avec son propre échantillon tiré du goulot).
        Avec n_candidates=1 (défaut), comportement identique à H1 seul.
        Avec n_candidates>1, on ne garde que le candidat le plus précis
        (communication_precision la plus haute) — c'est le test de H2.

    Retourne un DICTIONNAIRE (pas une liste de valeurs dans un ordre fixe -
    plus robuste si on doit encore l'étendre plus tard) avec les clés :
        "scores"        -> liste des similarités topographiques, une par génération
        "chunk_counts"  -> liste du nombre de chunks appris, une par génération
        "precisions"    -> liste des précisions de communication, une par génération
        "final_agent"   -> l'objet Agent de la toute dernière génération
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
            n_chunks = len(candidate.chunks)
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
    """Tous les sens (unité, individu) appartenant à un clan donné."""
    return [m for m in all_meanings() if m[0] == clan_value]


def run_simulation_h3(n_generations, bottleneck_fraction, homophily, mutation_rate=0.05, seed=0):
    """Fait tourner les N_CLANS lignées EN PARALLÈLE, avec un paramètre
    d'homophilie réglable (contrairement à l'isolement total testé en
    premier, qui correspond au cas extrême homophily=1.0).

    homophily : probabilité qu'un exemple d'apprentissage vienne du propre
        clan de l'agent. Avec probabilité (1 - homophily), l'exemple vient
        d'un AUTRE clan tiré au hasard (le même couple unité/individu,
        mais avec le signal produit par ce clan-là pour ce couple).
        homophily=1.0 -> isolement total, aucune information ne traverse
        les clans (c'est ce qu'on avait testé au premier essai).
        homophily proche de 0 -> les agents apprennent presque uniquement
        des autres clans, très peu du leur.

    Retourne un dictionnaire :
        "topo_by_gen"  -> liste (n_generations) de listes (N_CLANS) de scores
        "final_agents" -> liste (N_CLANS) des agents de la toute dernière génération
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
            learned_chunks_snapshot[c] = dict(new_agent.chunks)  # AVANT produce_all !
            new_language = new_agent.produce_all(clan_meanings[c])
            new_agents.append(new_agent)
            new_languages.append(new_language)

        current_agents = new_agents
        languages = new_languages
        topo_by_gen.append([topographic_similarity(languages[c]) for c in range(n_clans)])

    return {"topo_by_gen": topo_by_gen, "final_agents": current_agents,
            "final_learned_chunks": learned_chunks_snapshot}
