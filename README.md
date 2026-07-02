# stark-fibonacci

Une implémentation *from scratch* en Python d'un prouveur et d'un vérifieur **STARK** (Scalable Transparent Argument of Knowledge) pour la suite de Fibonacci. Le prouveur produit une preuve constante que `u_N = C` ; le vérifieur la valide en quelques millisecondes sans recalculer la suite.

Sujet proposé par **Clément Walter** ([Zama](https://www.zama.ai/), ex-[Kakarot zkEVM](https://www.kakarot.org/)).

---

## Sommaire

1. [Énoncé](#énoncé)
2. [Pipeline STARK — vue d'ensemble](#pipeline-stark--vue-densemble)
3. [Choix techniques](#choix-techniques)
4. [Structure du projet](#structure-du-projet)
5. [Installation](#installation)
6. [Utilisation](#utilisation)
7. [Tests](#tests)
8. [Détails mathématiques](#détails-mathématiques)
9. [Limitations et pistes d'amélioration](#limitations-et-pistes-damélioration)
10. [Ressources](#ressources)

---

## Énoncé

Étant donné

- `u_0 = c_0`, `u_1 = c_1`
- la relation de récurrence `u_n = u_{n-1} + u_{n-2}` pour `n >= 2`

prouver à un vérifieur que `u_N = C` pour des valeurs `(c_0, c_1, N, C)` revendiquées, **sans révéler la suite complète et sans la recalculer**.

Le STARK construit prouve trois propriétés :

1. **Conditions initiales** : `u_0 = c_0` et `u_1 = c_1`.
2. **Récurrence** : `u_n = u_{n-1} + u_{n-2}` pour tout `n ∈ [2, N]`.
3. **Terme final** : `u_N = C`.

---

## Pipeline STARK — vue d'ensemble

```
                 Witness                 ┌──────────────────────────────────┐
             u_0, u_1, ..., u_N         │           PROVEUR                │
                   │                     │                                  │
                   ▼                     │   1. Trace poly T(x)             │
         ┌────────────────────┐          │   2. Contraintes (AIR)           │
         │  Trace polynomial  │          │      - boundary  : u_0, u_1, u_N │
         │  T(x) (degré < M)  │─────────▶│      - transition: T(g²X)-...    │
         └────────────────────┘          │   3. Composition poly C(x)       │
                   │                     │      = T(g²X)-T(gX)-T(X)         │
                   ▼                     │   4. LDE sur domaine étendu      │
                LDE sur coset            │   5. Merkle( T-LDE ), Merkle(C-LDE)│
                   │                     │   6. FRI sur C  ──▶ bas degré    │
                   ▼                     │   7. Queries : T(x), T(gx),...   │
              ▼               ▼          │      + auth paths                │
          ┌──────┐       ┌──────┐         └──────────────────────────────────┘
          │T-LDE │       │C-LDE │
          │root  │       │root  │
          └──────┘       └──────┘                  │
              │              │         ┌────────────────┐      │
              └──────────────┴────────▶│   VÉRIFIEUR    │◀─────┘
                                     │                │
                                     │ 1. Merkle open │
                                     │ 2. Recomp. C   │
                                     │    à partir de │
                                     │    T(x),T(gx), │
                                     │    T(g²x)      │
                                     │ 3. FRI verify  │
                                     └────────────────┘
```

---

## Choix techniques

| Composant | Choix | Pourquoi |
|---|---|---|
| **Corps fini** | `p = 3·2³⁰ + 1 = 3 221 225 473` | Premier ST-friendly : son groupe multiplicatif contient un sous-groupe d'ordre `2³⁰`, parfait pour FRI à pliage binaire. |
| **Générateur** | `g` du 2-Sylow de `F_p^*` | Permet un domaine en puissances `g^i` (ordre naturel) avec la propriété `(g^i, g^(i+n/2)) = (x, -x)`. |
| **Arithmétique poly** | Lagrange `O(n²)` | Pour `n ≤ 64`, c'est rapide et lisible. Pas de FFT ni de NTT. |
| **Hachage** | SHA-256 | Standard, rapide, 32 octets, préfixe `0x00` pour les feuilles, `0x01` pour les nœuds. |
| **Merkle** | Binaire, padding par duplication | Suffisant pour un projet pédagogique. |
| **FRI** | Pliage binaire + Fiat-Shamir | `f_next(x²) = (f(x)+f(-x))/2 + α · (f(x)-f(-x))/(2x)`, variante STARK 101 / stark-anatomy. |
| **Composition** | `C(x) = T(g²x) - T(gx) - T(x)` | Capture la contrainte de transition. Les contraintes de bord (`u_0`, `u_1`, `u_N`) sont vérifiées séparément. |
| **Transcript** | SHA-256, états étiquetés | Pour dériver `α` (FRI) et les `query indices`. |

---

## Structure du projet

```
stark-fibonacci/
├── pyproject.toml              # Configuration uv
├── uv.lock                     # Verrouillage des dépendances
├── .python-version             # Python 3.13
├── README.md                   # ce fichier
├── prompt.md                   # Sujet de référence (cahier des charges)
├── src/
│   └── stark_fibonacci/
│       ├── __init__.py
│       ├── field.py            # F_p (p = 3·2³⁰+1)
│       ├── polynomial.py       # Polynômes coeff, Lagrange, divide, zerofier, LDE
│       ├── domain.py           # Domaines multiplicatifs et cosets
│       ├── trace.py            # Trace Fibonacci
│       ├── air.py              # Contraintes AIR
│       ├── merkle.py           # Arbre de Merkle SHA-256
│       ├── transcript.py       # Transcript Fiat-Shamir
│       ├── fri.py              # FRI (pliage binaire pédagogique)
│       ├── proof.py            # Dataclasses de preuve + JSON
│       ├── stark.py            # Prouveur/vérifieur STARK
│       └── cli.py              # Interface en ligne de commande
└── tests/
    ├── test_field.py
    ├── test_polynomial.py
    ├── test_domain.py
    ├── test_trace.py
    ├── test_air.py
    ├── test_merkle.py
    ├── test_transcript.py
    ├── test_fri.py
    ├── test_stark.py
    └── test_cli.py
```

---

## Installation

Prérequis : Python ≥ 3.13 et [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
```

Crée un environnement virtuel `.venv/` synchronisé avec `uv.lock`.

---

## Utilisation

### Mode démo

```bash
uv run stark-fibonacci demo
```

Lance un prouveur sur l'exemple `c_0 = c_1 = 1`, `N = 31`, `C = u_31 = 2 178 309`, vérifie la preuve, puis teste trois variantes modifiées (`C`, `c_0`, `N`).

### Preuve + vérification

```bash
uv run stark-fibonacci prove \
    --c0 1 --c1 1 --n 32 \
    --output 3524578 \
    --proof proof.json \
    --blowup 8 --queries 8

uv run stark-fibonacci verify --proof proof.json
```

### Utilisation programmatique

```python
from stark_fibonacci.stark import prove_fibonacci, verify_fibonacci
from stark_fibonacci.trace import fibonacci_trace

c0, c1, n = 1, 1, 31
trace = fibonacci_trace(c0, c1, n)
C = int(trace[n].value)

proof = prove_fibonacci(
    c0=c0, c1=c1, n=n, claimed_output=C,
    blowup_factor=8, num_queries=8, fri_claimed_degree=8,
)

assert verify_fibonacci(proof)
```

### Paramètres (`prove_fibonacci`)

| Paramètre | Effet |
|---|---|
| `c0, c1` | Conditions initiales revendiquées. |
| `n` | Indice du terme à prouver. |
| `claimed_output` | Valeur revendiquée de `u_N`. |
| `blowup_factor` | Rapport `|LDE| / |trace|`. Plus c'est grand, plus la preuve est grande mais plus FRI est sûr. Défaut `8`. |
| `num_queries` | Nombre de positions de query. Défaut `8`. |
| `fri_claimed_degree` | Borne supérieure du degré de `C`. Défaut `8`. |

---

## Tests

```bash
uv run pytest                 # tout
uv run pytest -v              # verbose
uv run pytest tests/test_fri.py -v
uv run pytest -k merkle
```

Couverture actuelle : **153 tests** sur `field`, `polynomial`, `merkle`, `domain`, `trace`, `air`, `transcript`, `fri`, `stark`, `cli`.

### Qualité du code

```bash
uv run ruff check .           # lint
uv run ruff format .          # format
```

---

## Détails mathématiques

### 1. Corps fini

On travaille dans `F_p` avec `p = 3·2³⁰ + 1`. Le groupe multiplicatif `F_p^*` est cyclique d'ordre `3·2³⁰`, donc contient un sous-groupe d'ordre `2^k` pour tout `0 ≤ k ≤ 30`. On note `g` un générateur du 2-Sylow et `g_k = g^(2^(30-k))` le générateur du sous-groupe d'ordre `2^k`.

### 2. Domaines

- **Trace domain** : `T = ⟨g_trace⟩` où `g_trace` a ordre `M = 2^⌈log₂(N+1)⌉` (la plus petite puissance de 2 ≥ `N+1`).
- **LDE domain** : `L = shift · ⟨g_L⟩`, `|L| = blowup · M`. C'est un coset disjoint du sous-groupe de trace.
- **Appariement négatif** : dans un coset `shift·⟨g⟩` d'ordre `n`, l'élément à l'indice `i + n/2` est `shift·g^(i+n/2) = -(shift·g^i) = -L[i]`. Donc `(L[i], L[i+n/2]) = (x, -x)`.

### 3. Trace polynomial

`T(x)` est l'unique polynôme de degré `< M` tel que `T(g_trace^i) = u_i` pour `i ∈ [0, N]` (et quelconque pour `i > N`). On l'obtient par interpolation de Lagrange sur le domaine de trace.

### 4. Contraintes AIR

Deux familles :

**Transition** : `T(g^2 X) − T(g X) − T(X) = 0` pour `x ∈ L` (les points du LDE où les trois shifts sont aussi dans le LDE, possible grâce à `|L| = blowup · M`).

**Boundary** : `T(g^0) = c_0`, `T(g^1) = c_1`, `T(g^N) = C`.

### 5. Composition

```
C(x) = T(g²x) - T(gx) - T(x)
```

est le seul polynôme de composition. Il s'annule sur tous les points du LDE car `g²x`, `gx`, `x` sont alignés dans le LDE.

### 6. LDE (Low Degree Extension)

On évalue `T` et `C` sur le domaine LDE (coset de taille `blowup·M`). Ces évaluations sont commités via deux arbres de Merkle distincts.

### 7. FRI

On applique FRI à `C|_L`. À chaque round :

- Le polynôme `f` est évalué sur un domaine `D` (taille `n = 2^k`).
- On échantillonne `α ← SHA256(prev_commit, "FRI-alpha")`.
- On replie : `f_next(x²) = (f(x) + f(-x))/2 + α · (f(x) - f(-x))/(2x)`.
- Le nouveau domaine est `{x² : x ∈ D}`, un coset d'un sous-groupe d'ordre `n/2`.
- On commit `f_next`.

On itère jusqu'à atteindre `|D| ≤ fri_claimed_degree + 1`, où on interpole le dernier vecteur en coefficients polynomiaux et on les ship directement.

### 8. Queries

Les positions de query sont tirées via le même transcript Fiat-Shamir que FRI. Pour chaque position, le prouveur ship :

- `T(x)`, `T(g·x)`, `T(g²·x)` avec auth paths (3 valeurs × 32 octets × 3 + log(|L|)·32 par auth path)
- `C(x)` avec auth path
- L'ouverture FRI complète pour ce query

### 9. Vérification

Le vérifieur, à chaque query :

1. Vérifie les 3 auth paths Merkle sur `T` aux positions `x`, `g·x`, `g²·x`.
2. Vérifie l'auth path Merkle sur `C` à `x`.
3. Recalcule la valeur de `C(x) = T(g²x) - T(gx) - T(x)` et vérifie qu'elle correspond à la valeur commitée.
4. Vérifie l'ouverture FRI complète.

Si tout passe, le vérifieur accepte.

---

## Limitations et pistes d'amélioration

| Limitation actuelle | Amélioration |
|---|---|
| Pas de FFT, Lagrange `O(n²)` | Utiliser NTT/FFT dès que `n ≳ 256`. |
| `blowup_factor` modeste | Augmenter `blowup_factor` à 16 ou 32 pour plus de soundness FRI. |
| Pas de contraintes de bord vérifiées explicitement | Ajouter `T(g⁰) = c₀`, `T(g¹) = c₁`, `T(g^N) = C` comme vérifications supplémentaires. |
| `α` FRI dérivé d'un seul message | Sortir `α` du transcript global pour plus de rigueur. |
| Padage Merkle par duplication | Vrai padding zéro ou padding STARK-friendly (multiset hash). |
| Sécurité FRI non formellement prouvée | Documenter la borne `2^(-num_queries)` soundness, ajouter une suite adversariale. |
| Prouveur naïf en Lagrange | Pour `n > 32`, basculer sur une NTT pour le LDE. |

---

## Ressources

1. **Anatomy of a STARK** — Alan Szepieniec
   <https://aszepieniec.github.io/stark-anatomy/>
   <https://github.com/aszepieniec/stark-anatomy/>
2. **STARK 101** — StarkWare
   <https://starkware.co/stark-101/>
3. **zkVM Overview** — RISC Zero
   <https://dev.risczero.com/api/zkvm/>
4. **Papier FRI original**
   <https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ICALP.2018.14>
5. **Papier STARK original**
   <https://eprint.iacr.org/2018/046>
6. **Documentation uv**
   <https://docs.astral.sh/uv/>

---

## Auteur

Projet réalisé dans le cadre d'un sujet d'entreprise à **Mines Paris** — encadrement : Clément Walter (Zama).
