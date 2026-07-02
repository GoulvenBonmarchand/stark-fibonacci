# stark-fibonacci

Implémentation **from scratch** en Python d'un prouveur et d'un vérifieur **STARK** (Scalable Transparent Argument of Knowledge) pour la suite de Fibonacci. Le prouveur produit une preuve constante que `u_N = C` ; le vérifieur la valide en quelques millisecondes **sans recalculer la suite**.

Sujet proposé par **Clément Walter** ([Zama](https://www.zama.ai/), ex-[Kakarot zkEVM](https://www.kakarot.org/)).

---

## À propos

Un **STARK** permet à un prouveur de convaincre un vérifieur qu'un calcul a été effectué correctement, sans que le vérifieur ait à le refaire. Ici le calcul est tout simple : la suite `u₀ = c₀`, `u₁ = c₁`, `u_{i+2} = u_{i+1} + u_i`. La preuve atteste que `u_N = C` pour `N` quelconque.

Pour cela, on exprime la suite comme l'évaluation d'un polynôme `T(x)` sur un sous-groupe multiplicatif de `F_p`, on encode les contraintes (conditions initiales, récurrence, terme final) comme un **AIR** (Algebraic Intermediate Representation), on commite les valeurs via un arbre de Merkle, et on prouve que la **composition** `C(x) = T(g²x) − T(gx) − T(x)` est bien un polynôme de bas degré grâce à un **FRI**.

Le corps fini utilisé est `F_p` avec `p = 3 · 2³⁰ + 1 = 3 221 225 473`, dont le groupe multiplicatif contient un sous-groupe d'ordre `2³⁰` idéal pour FRI à pliage binaire.

Le pipeline :

```
  Trace T      Interpolate      LDE           Merkle commits    FRI
u₀..u_N  ──▶ T(x) de degré < M ─▶ évaluations ─▶ racines      ─▶ bas degré
                                          │            │
                                          │     Queries (aléatoires)
                                          ▼            ▼
                                       ┌──────────────────────┐
                                       │       VÉRIFIEUR      │
                                       │  - check Merkle open │
                                       │  - check C(x) =      │
                                       │    T(g²x)-T(gx)-T(x) │
                                       │  - check FRI chain   │
                                       └──────────────────────┘
```

---

## Installation

Prérequis : Python ≥ 3.13 et [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
```

---

## Utilisation

### Démo

```bash
uv run stark-fibonacci demo
```

Lance un prouveur sur `c₀ = c₁ = 1`, `N = 31`, `C = 2 178 309`, vérifie la preuve, puis teste trois variantes modifiées.

Sortie typique :

```
======================================================================
STARK — Fibonacci recurrence (proof that u_N = C without recomputing)
======================================================================
Statement: u_0 = 1, u_1 = 1, N = 31, C = 2178309

Honest proof:
  prover time : 0.250 s
  verifier OK : True
  verifier t  : 0.006 s
```

### Preuve + vérification manuelles

```bash
uv run stark-fibonacci prove \
    --c0 1 --c1 1 --n 32 --output 3524578 --proof proof.json
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

---

## Tests

```bash
uv run pytest                                # 153 tests
uv run pytest -v                             # verbose
uv run pytest tests/test_fri.py              # un fichier
uv run pytest -k merkle                      # par mot-clé
```

**Qualité du code :**

```bash
uv run ruff check .        # lint
uv run ruff format .       # format
```

---

## Architecture

```
src/stark_fibonacci/
├── field.py        # F_p (p = 3·2³⁰+1), éléments immuables
├── polynomial.py   # Coefficients, Lagrange, divide, zerofier, LDE
├── domain.py       # Sous-groupes multiplicatifs et cosets
├── trace.py        # Trace Fibonacci u_0, u_1, ..., u_N
├── air.py          # Contraintes AIR (boundary + transition)
├── merkle.py       # Arbre de Merkle SHA-256
├── transcript.py   # Fiat-Shamir (challenges déterministes)
├── fri.py          # FRI à pliage binaire
├── proof.py        # Dataclasses de preuve + JSON
├── stark.py        # Prouveur et vérifieur STARK
└── cli.py          # Interface en ligne de commande

tests/                      # 10 fichiers de tests, 153 assertions
```

---

## Limites de sécurité

Ce projet est **pédagogique**. Quelques points à savoir avant d'aller plus loin :

- **Interpolation Lagrange `O(n²)`** : utilisable pour `n ≤ 64` ; au-delà, prévoir une NTT.
- **Boundary pas vérifié explicitement** : le vérifieur valide la récurrence à des points aléatoires mais ne contraint pas `T(g⁰) = c₀`, `T(g¹) = c₁`, `T(g^N) = C` au sens strict (piste d'amélioration évidente).
- **Pas de padding zero dans Merkle** : padding par duplication de la dernière feuille (suffisant pour ce projet).
- **`α` FRI est engageant** mais pas dérivé d'un transcript global signé.
- **Borne de soundness FRI** = `2^{-num_queries}` non formellement documentée.

Ce ne sont pas des trous pour le cas honnête (Fibonacci simple) mais autant le savoir.

---

## Ressources

- [STARK 101 — StarkWare](https://starkware.co/stark-101/) — tutoriel Python qui utilise précisément Fibonacci
- [Anatomy of a STARK — Alan Szepieniec](https://aszepieniec.github.io/stark-anatomy/) — la référence pédagogique
- [Papier STARK original](https://eprint.iacr.org/2018/046)
- [Papier FRI](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ICALP.2018.14)

---

Projet réalisé dans le cadre d'un sujet d'entreprise à **Mines Paris** — encadrement : Clément Walter (Zama).
