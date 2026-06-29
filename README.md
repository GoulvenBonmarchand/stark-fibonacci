# stark-fibonacci

Implémentation en Python d'un prouveur et d'un vérifieur **STARK** (Scalable Transparent Argument of Knowledge) simplifiés, permettant de prouver qu'une suite récurrente de type Fibonacci atteint une valeur donnée sans avoir à refaire le calcul.

Sujet proposé par **Clément Walter** ([Zama](https://www.zama.ai/), ex-[Kakarot zkEVM](https://www.kakarot.org/)).

---

## Objectif

Étant donné $u_0 = c_0$, $u_1 = c_1$ et la relation de récurrence

$$u_n = u_{n-1} + u_{n-2} \quad \text{pour } n \geq 2,$$

produire une preuve que $u_N = C$ pour des $N$, $c_0$, $c_1$, $C$ revendiqués — sans révéler la suite complète et sans que le vérifieur ait à la recalculer.

Le STARK construit prouve trois propriétés :

1. Les conditions initiales $u_0$ et $u_1$ sont respectées.
2. La récurrence $u_n = u_{n-1} + u_{n-2}$ est vérifiée pour tout $n$ de la suite.
3. Le terme final $u_N$ vaut la valeur $C$ revendiquée.

---

## Structure du projet

```
stark-fibonacci/
├── pyproject.toml              # Configuration du projet (uv)
├── uv.lock                     # Verrouillage des dépendances
├── .python-version             # Version Python pinned (>=3.13)
├── .gitignore
├── README.md
├── num-zama-clement-walter-1.md   # Sujet de référence (Zama / Clément Walter)
├── src/
│   └── stark_fibonacci/
│       ├── __init__.py
│       ├── main.py             # Point d'entrée : démo STARK
│       ├── field.py            # Arithmétique des corps finis
│       ├── polynomial.py       # Opérations polynomiales (eval, interpolate, LDE, poly_div, vanishing_poly)
│       ├── merkle.py           # Arbre de Merkle pour les commitments
│       ├── fri.py              # Protocole FRI (prouveur + vérifieur)
│       ├── stark.py            # Prouveur / vérifieur STARK de haut niveau
│       └── utils.py            # Hachage, génération de défis, utilitaires
└── tests/
    ├── test_field.py
    ├── test_polynomial.py
    └── test_merkle.py
```

---

## Prérequis

- **Python ≥ 3.13**
- [`uv`](https://docs.astral.sh/uv/) — gestionnaire de paquets et d'environnement virtuel
- Bonne compréhension de l'algèbre abstraite, de l'algèbre linéaire et de la théorie des nombres de base.

---

## Installation

```bash
# Synchroniser l'environnement et les dépendances
uv sync

# Ajouter une dépendance de dev (ex. pytest)
uv add --dev pytest
```

---

## Utilisation

Lancer la démo STARK (génération + vérification d'une preuve pour la suite de Fibonacci) :

```bash
uv run stark-fibonacci
```

ou directement :

```bash
uv run python -m stark_fibonacci.main
```

---

## Tests

```bash
uv run pytest
```

Les tests actuels couvrent le corps fini, les polynômes et l'arbre de Merkle. Les tests **FRI** et **STARK** restent à ajouter (voir `num-zama-clement-walter-1.md`, Jour 3 et 4).

---

## Pipeline STARK (rappel)

| Étape | Fichier | Rôle |
|---|---|---|
| Arithmétisation | `field.py`, `polynomial.py` | Trace d'exécution → polynômes |
| Extension de domaine (LDE) | `polynomial.py` | Évaluation sur un domaine étendu |
| Commitment | `merkle.py` | Arbre de Merkle sur les évaluations |
| Preuve de bas degré | `fri.py` | Sous-protocole FRI (FRI commitments + queries) |
| Composition | `stark.py` | Prouveur et vérifieur de bout en bout |
| Entrée / démo | `main.py` | Génération et vérification de la preuve |

---

## Ressources

1. **Anatomy of a STARK** — aszepieniec  
   <https://aszepieniec.github.io/stark-anatomy/> · <https://github.com/aszepieniec/stark-anatomy/>  
   _Modulaire, techniquement solide, accompagné de code Python._
2. **STARK 101** — StarkWare  
   <https://starkware.co/stark-101/>  
   _Tutoriel pratique en Python ; utilise précisément une suite de type Fibonacci._
3. **zkVM Overview** — RISC Zero  
   <https://dev.risczero.com/api/zkvm/>  
   _Exemple concret d'usage des STARK en production, traces d'exécution._

---

## Guide Git rapide

- Toujours créer une **branche dédiée** pour chaque fonctionnalité :
  ```bash
  git checkout -b feature/nom-de-la-tache
  ```
- Commits petits, logiques, messages à l'impératif (`feat: ...`, `fix: ...`, `docs: ...`).
- Pousser régulièrement sa branche : `git push origin feature/nom-de-la-tache`.
- Fusionner dans `main` via **Pull Request**.

---

## Auteur

Projet réalisé dans le cadre d'un sujet d'entreprise à **Mines Paris** — encadrement : Clément Walter (Zama).