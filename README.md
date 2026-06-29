# stark-fibonacci

Une implémentation from-scratch en Python d'un prouveur et d'un vérifieur **STARK** (Scalable Transparent Argument of Knowledge) pour la suite de Fibonacci. Le prouveur produit une preuve constante que `u_N = C` ; le vérifieur la valide en quelques millisecondes sans recalculer la suite.

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
9. [Limitations & pistes d'amélioration](#limitations--pistes-damélioration)
10. [Ressources](#ressources)
11. [Guide Git](#guide-git)

---

## Énoncé

Étant donné
- `u_0 = c_0`, `u_1 = c_1`
- la relation de récurrence `u_n = u_{n-1} + u_{n-2}` pour `n ≥ 2`

prouver à un vérifieur que `u_N = C` pour un `N` et des valeurs `(c_0, c_1, C)` revendiqués, **sans révéler la suite complète et sans la recalculer**.

Le STARK construit prouve trois propriétés :
1. **Conditions initiales** : `u_0 = c_0` et `u_1 = c_1`.
2. **Récurrence** : `u_n = u_{n-1} + u_{n-2}` pour tout `n ∈ [2, N]`.
3. **Terme final** : `u_N = C`.

---

## Pipeline STARK — vue d'ensemble

```
                 Witness                 ┌──────────────────────────────────┐
            u_0, u_1, ..., u_N           │           PROVEUR                │
                  │                       │                                  │
                  ▼                       │   1. Trace poly T(x)             │
        ┌────────────────────┐            │   2. Contraintes                 │
        │  Trace polynomial │            │      • boundary  : u_0, u_1, u_N │
        │  T(x)  (degré N)  │───────────▶│      • transition: T(g²x)-...    │
        └────────────────────┘            │   3. Composition poly C(x)       │
                  │                       │      (boundary + transition)    │
                  │                       │   4. LDE sur domaine étendu      │
                  │                       │   5. Merkle( T ) , Merkle( C )   │
                  │                       │   6. FRI sur C  ──▶ bas degré    │
                  ▼                       │   7. Queries : T(x), C(x)        │
        Merkle commitment                  │      + auth paths                │
                  │                       └──────────────────────────────────┘
                  ▼                                       │
                  │              ┌────────────────┐       │
              T(N) = C ?        │   VÉRIFIEUR    │◀──────┘
                  │              │                │
                  ▼              │ 1. Merkle open │
              ACCEPTER           │ 2. Recomp. C(x)│
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
| **Arithmétique poly** | Lagrange `O(n²)` | Pour `n ≤ 128`, c'est rapide et lisible. Pas de FFT. |
| **Hachage** | SHA-256 | Standard, rapide, 32 octets. |
| **Merkle** | Binaire padded | Padage par duplication de la dernière feuille → toujours une puissance de 2 ; suffisant pour un projet pédagogique. |
| **FRI** | Pliage binaire + Fiat-Shamir | Le pliage `f₁(x²) = (f(x)+f(-x))/2 + r·(f(x)-f(-x))/(2x)` est la variante STARK 101 / stark-anatomy. |
| **Composition** | `C = T_trans/Z_trans + α·Σ T_bound` | Combinaison linéaire des quotients par leurs polynômes d'annulation. |

---

## Structure du projet

```
stark-fibonacci/
├── pyproject.toml              # Configuration du projet (uv)
├── uv.lock                     # Verrouillage des dépendances
├── .python-version             # Python 3.13
├── README.md                   # ce fichier
├── num-zama-clement-walter-1.md   # Sujet de référence
├── src/
│   └── stark_fibonacci/
│       ├── __init__.py
│       ├── main.py             # Point d'entrée CLI : démo STARK
│       ├── field.py            # Arithmétique F_p + domaines
│       ├── polynomial.py       # Opérations poly (Lagrange, div, LDE, vanishing)
│       ├── merkle.py           # Arbre de Merkle SHA-256
│       ├── fri.py              # Prouveur / vérifieur FRI
│       ├── stark.py            # Prouveur / vérifieur STARK (Fibonacci)
│       └── utils.py            # Hachage, échantillonnage (Fiat-Shamir)
└── tests/
    ├── test_field.py           # 13 tests
    ├── test_polynomial.py      # 18 tests
    ├── test_merkle.py          #  8 tests
    ├── test_fri.py             #  7 tests
    └── test_stark.py           # 12 tests
```

---

## Installation

Prérequis : Python ≥ 3.13 et [`uv`](https://docs.astral.sh/uv/).

```bash
# Synchroniser les dépendances (créé .venv automatiquement)
uv sync

# Lancer la démo STARK
uv run stark-fibonacci
```

Sortie attendue (extrait) :
```
========================================================================
STARK — Fibonacci recurrence (proof that u_N = C without recomputing)
========================================================================
Statement: u_0 = 1, u_1 = 2, N = 31, C = 3524578

Honest proof:
  prover time : 0.107 s
  verifier OK : True
  verifier t  : 0.004 s

Tampering tests (each should be rejected):
     wrong C: REJECTED
    wrong c0: REJECTED
     wrong N: REJECTED
All tampering attempts correctly rejected.
```

---

## Utilisation

### CLI — démo end-to-end

```bash
uv run stark-fibonacci
```

Voir le code dans `src/stark_fibonacci/main.py` pour comprendre l'orchestration.

### Utilisation programmatique

```python
from stark_fibonacci.stark import StarkParams, prove_stark, verify_stark
from stark_fibonacci.field import FieldElement

prime = FieldElement(0).prime
N = 31
trace = [FieldElement(1, prime), FieldElement(2, prime)]
for _ in range(N - 1):
    trace.append(trace[-1] + trace[-2])
C = int(trace[-1])

params = StarkParams(
    c0=1, c1=2, N=N, C=C,
    blowup_factor=4,
    num_queries=8,
    max_degree_plus_one=16,
    shift=3,
)
proof = prove_stark(params)
assert verify_stark(proof)
```

### Réglages (`StarkParams`)

| Champ | Effet |
|---|---|
| `c0, c1` | Conditions initiales revendiquées. |
| `N` | Indice du terme à prouver. |
| `C` | Valeur revendiquée de `u_N`. |
| `blowup_factor` | Rapport `|LDE| / |trace|`. Plus c'est grand, plus la preuve est grande mais plus FRI est sûr. Défaut `4`. |
| `num_queries` | Nombre de positions de query. Défaut `8`. |
| `max_degree_plus_one` | Taille finale de FRI (degré max du polynôme final + 1). Défaut `16`. |
| `shift` | Coset pour le domaine LDE. |

---

## Tests

```bash
uv run pytest                 # tout
uv run pytest -v              # verbose
uv run pytest tests/test_stark.py    # un fichier
uv run pytest -k merkle              # par mot-clé
```

Couverture actuelle : **58 tests** sur `field`, `polynomial`, `merkle`, `fri`, `stark`.

---

## Détails mathématiques

### 1. Corps fini

On travaille dans `F_p` avec `p = 3·2³⁰ + 1`. Le groupe multiplicatif `F_p^*` est cyclique d'ordre `3·2³⁰`, donc contient un sous-groupe d'ordre `2^k` pour tout `0 ≤ k ≤ 30`. On note `g` un générateur de ce 2-Sylow et `g_k = g^(2^(30-k))` le générateur du sous-groupe d'ordre `2^k`.

### 2. Domaines

- **Trace domain** : `T = ⟨g_trace⟩` où `g_trace` a ordre `M = 2^⌈log₂(N+1)⌉` (la plus petite puissance de 2 ≥ `N+1`).
- **LDE domain** : `L = shift · ⟨g_L⟩`, `|L| = blowup·M`. C'est un coset disjoint du sous-groupe de trace.
- **Appariement négatif** : dans un coset `shift·⟨g⟩` d'ordre `n`, l'élément à l'indice `i + n/2` est `shift·g^(i+n/2) = -(shift·g^i) = -L[i]`. Donc `(L[i], L[i+n/2]) = (x, -x)`.

### 3. Trace polynomial

`T(x)` est l'unique polynôme de degré `< M` tel que `T(g_trace^i) = u_i` pour `i ∈ [0, N]` (et quelconque pour `i > N`). On l'obtient par interpolation de Lagrange sur le domaine de trace.

### 4. Contraintes

Deux familles de contraintes :

**Transition** : `T(g²·x) − T(g·x) − T(x) = 0` pour `x ∈ {g^0, g^1, …, g^(N−2)}` (les indices où les trois points sont dans la trace).

Le quotient `Q_trans(x) = (T(g²x) − T(gx) − T(x)) / Z_trans(x)` est un polynôme de degré `≤ N`, où `Z_trans(x) = ∏_{i=0}^{N-2}(x − g^i)`.

**Boundary** : `T(g^i) = claim_i` pour `i ∈ {0, 1, N}` avec `claim_0 = c_0`, `claim_1 = c_1`, `claim_N = C`.

Chaque quotient `Q_bound_i(x) = (T(x) − claim_i) / (x − g^i)` est un polynôme de degré `≤ N`.

### 5. Composition

On combine linéairement les quotients :

```
C(x) = Q_trans(x) + α · ( Q_bound_0(x) + Q_bound_1(x) + Q_bound_N(x) )
```

avec `α = SHA256("STARK-alpha" || (c0,c1,N,C))`. C'est une valeur fixe dérivée de l'instruction publique. (Pour une implémentation plus stricte, on tirerait `α` du transcript Fiat-Shamir ; pour un projet pédagogique, ça suffit.)

`C` a degré `≤ N` ≤ ~64 dans notre configuration. Si toutes les contraintes sont satisfaites, `C` est exactement le polynôme décrit ci-dessus.

### 6. LDE (low-degree extension)

On évalue `T` et `C` sur le domaine LDE (coset de taille `blowup·M`). Ces évaluations sont commités via deux arbres de Merkle distincts. Les feuilles sont `SHA256( domain_point || evaluation )`.

### 7. FRI

On applique FRI à `C|_L`. À chaque round :

- Le polynôme `f` est évalué sur un domaine `D` (taille `n = 2^k`).
- On échantillonne `r ← SHA256(prev_commit)`.
- On replie : pour `i ∈ [0, n/2)`, `f_next[i] = (f(x) + f(-x))/2 + r · (f(x) − f(-x))/(2x)` où `x = D[i]`.
- Le nouveau domaine est `{x² : x ∈ D}`, un coset d'un sous-groupe d'ordre `n/2`.
- On commit `f_next`.

On itère jusqu'à atteindre `|D| ≤ max_degree_plus_one`, où on interpole le dernier vecteur en coefficients polynomiaux et on les ship directement. Le vérifieur contrôle que ce polynôme a degré `< max_degree_plus_one`.

**Preuve** : pour chaque query, le prouveur ship `(f(x), f(-x))` avec auth paths pour chaque couche. Le vérifieur recalcule le pliage et vérifie la cohérence couche par couche, plus la dernière évaluation contre le polynôme shipé.

### 8. Queries

Le transcript Fiat-Shamir est :

```
T_STARK = SHA256(
  "STARK-transcript" ||
  Merkle(T|_L).root ||
  Merkle(C|_L).root ||
  Σ roots FRI ||
  poly final FRI
)
```

Les positions de query sont tirées de `T_STARK` par rejection sampling. Pour chaque position, le prouveur ship :

- `T(x)`, `T(g·x)`, `T(g²·x)` avec auth paths (3 valeurs × 32 octets × 3 + log(|L|)·32 par auth path)
- `C(x)` avec auth path
- L'ouverture FRI complète pour ce query

### 9. Vérification

Le vérifieur, à chaque query :

1. Vérifie les 3 auth paths Merkle sur `T` aux positions `x`, `g·x`, `g²·x`.
2. Vérifie l'auth path Merkle sur `C` à `x`.
3. Recalcule la valeur de `C(x)` à partir de la formule de composition et vérifie qu'elle correspond à la valeur commitée.
4. Vérifie l'ouverture FRI complète.

Si tout passe, le vérifieur accepte.

---

## Limitations & pistes d'amélioration

| Limitation actuelle | Amélioration |
|---|---|
| Pas de FFT, Lagrange `O(n²)` | Utiliser NTT/FFT dès que `n ≳ 256`. |
| `max_degree_plus_one = 16` → traces courtes | Augmenter avec `blowup_factor` plus grand. |
| `α` dérivé de l'instruction, pas du transcript | Sortir `α` du transcript Fiat-Shamir pour plus de rigueur. |
| Padage Merkle par duplication | Vrai padding zéro ou padding STARK-friendly (multiset hash). |
| Pas de transcript binding complet | Ajouter un transcript global sérialisé et signé. |
| Sécurité FRI statistique non formellement prouvée | Documenter la borne `2^{-num_queries}` soundness. |
| Tests FRI négatifs limités | Ajouter une suite adversariale (mutations aléatoires du proof). |

---

## Ressources

1. **Anatomy of a STARK** — aszepieniec  
   <https://aszepieniec.github.io/stark-anatomy/> · <https://github.com/aszepieniec/stark-anatomy/>  
   _Modulaire, techniquement solide, code Python._
2. **STARK 101** — StarkWare  
   <https://starkware.co/stark-101/>  
   _Tutoriel Python ; utilise précisément une suite de type Fibonacci._
3. **zkVM Overview** — RISC Zero  
   <https://dev.risczero.com/api/zkvm/>  
   _Exemple concret d'usage des STARK en production._
4. **Goldilocks prime** — utilisé par Polygon Plonky3, succinct.  
   _Notre prime `p = 3·2³⁰+1` est plus petite (32 bits) et adaptée à un projet pédagogique._

---

## Guide Git

- Toujours créer une **branche dédiée** pour chaque fonctionnalité :
  ```bash
  git checkout -b feature/nom-de-la-tache
  ```
- Commits petits, logiques, messages à l'impératif (`feat: ...`, `fix: ...`, `docs: ...`).
- Pousser régulièrement : `git push origin feature/nom-de-la-tache`.
- Fusionner dans `main` via **Pull Request**.

---

## Auteur

Projet réalisé dans le cadre d'un sujet d'entreprise à **Mines Paris** — encadrement : Clément Walter (Zama).