---
author:
  affiliation: Zama
  email: clément.walter@zama.ai
  name: Clément Walter
label: label-zama-clement-walter-1
short_title: 18 ZAMA - zero knowledge proof
subject: entreprise
subtitle: null
title: 18 STARK - zero knowledge proof - Prouver que le nième terme d'une suite récurrente
  est N sans refaire le calcul"
---

*Clément Walter propose 4 sujets, les suivants sont moins bien détaillés, mais il sera présent pour les préciser avec vous. L’essentiel est que vous soyez très motivé(e)s pour découvrir son domaine.*

## L'entreprise et le porteur du projet

[Zama](https://www.zama.org/) *is an open source cryptography company that builds state-of-the-art Fully Homomorphic Encryption (FHE) solutions for blockchain* see <https://docs.zama.org/homepage>.

Ce sujet est proposé par Clément Walter (p09), co-fondateur de [`Kakarot`](https://www.kakarot.org/) [`zkEVM`](https://zkevm.ethereum.foundation/) (acheté par `Zama`), et actuellement chez Zama https://www.zama.ai/ qui
développe des outils de cryptographie à preuve d'exécution (STARKs) pour la
confidentialité et la vérifiabilité des données.

## Aperçu du Projet

Ce sujet vous propose de découvrir les techniques de STARKs (Scalable Transparent Argument of Knowledge). Il demande une forte motivation, beaucoup d'autonomie et une bonne compréhension de l'algèbre abstraite, de l'algèbre linéaire et de la théorie des nombres de base.

Ce projet est une introduction aux STARKs (Scalable Transparent Argument of Knowledge), un algorithme qui permet de produire une preuve qu'un résultat est correct sans avoir à le reproduire, autrement dit qui permet de produire une preuve d'exécution.

Ces méthodes sont aujourd'hui en pleine évolution et sont principalement utilisées pour garantir la confidentialité de certaines données tout en garantissant que les opérations (les calculs, l'exécution d'un programme) ont été faites correctement.

### Objectif Général du Projet

Implémenter en Python un prouveur et un vérifieur STARK simplifiés pour prouver une affirmation concernant une suite récurrente de type Fibonacci.

### Énoncé du Problème

> Étant donné $u_0 = c_0$ et $u_1 = c_1$, et la relation de récurrence  
> $u_n = u_{n-1} + u_{n-2}$ pour $n >= 2$,  
> comment pouvons-nous prouver à quelqu'un que  
> $u_N = C$ pour un $N$, un $u_0$, et un $u_1$ revendiqués spécifiques ?

Nous construirons un STARK qui prouve&nbsp;:

1.  Les conditions initiales $u_0$ et $u_1$ sont respectées.
2.  La récurrence $u_n = u_{n-1} + u_{n-2}$ est vérifiée pour tout $n$ dans la suite.
3.  Le terme final $u_N$ est égal à la valeur $C$ revendiquée.

### Résultats du Projet

- Une base de code Python pour le prouveur et le vérifieur STARK, respectant une bonne structure de projet, capable de prouver l'affirmation de la suite de Fibonacci.
- Un historique Git propre reflétant le développement collaboratif.
- Une démonstration en direct montrant une génération et une vérification de preuve réussies pour les paramètres de suite choisis.
- Une présentation expliquant les étapes mathématiques et informatiques, y compris les défis rencontrés et les leçons apprises.

### Prérequis

- Bonne compréhension de l'algèbre abstraite, de l'algèbre linéaire et de la théorie des nombres de base.
- Des concepts de programmation de base (variables, boucles, fonctions) sont bénéfiques, mais une initiation rapide sera fournie.

## Ressources Essentielles

Ces ressources sont fortement recommandées et constitueront la base du matériel d'apprentissage du projet&nbsp;:

1.  **"Anatomy of a STARK" par aszepieniec&nbsp;:**

    - Pages GitHub&nbsp;: <https://aszepieniec.github.io/stark-anatomy/>
    - Dépôt GitHub&nbsp;: <https://github.com/aszepieniec/stark-anatomy/>
    - _Pourquoi&nbsp;:_ Modulaire, techniquement solide, et accompagné de code Python. Excellent pour une exploration approfondie des composants STARK.

2.  **"STARK 101" par StarkWare&nbsp;:**

    - Page officielle&nbsp;: <https://starkware.co/stark-101/>
    - _Pourquoi&nbsp;:_ Un tutoriel pratique en Python pour écrire un prouveur STARK de A à Z, utilisant une suite de type Fibonacci, offrant un excellent point de départ.

3.  **"zkVM Overview | RISC Zero Developer Docs"&nbsp;:**
    - Documentation&nbsp;: <https://dev.risczero.com/api/zkvm/>
    - _Pourquoi&nbsp;:_ Fournit un exemple concret de l'utilisation des STARK en production, donne une compréhension de haut niveau des concepts comme les traces d'exécution et les idées de base des machines virtuelles à preuve d'exécution (zkVM).

## Plan du projet sur 5 Jours

### Jour 1&nbsp;: Fondations et Configuration Python/Git 

*Complexité&nbsp;: Faible-Moyenne*

**Matin&nbsp;: Introduction et Bases Mathématiques**

**Après-midi&nbsp;: Configuration de l'Espace de Travail Python et Git**

- **Livrable&nbsp;:** Un répertoire de projet propre et initialisé, un dépôt Git, Cursor, et un environnement virtuel `uv` avec `numpy` installé.

### Jour 2&nbsp;: Arithmétisation et Polynômes 

*Complexité&nbsp;: Moyenne*

**Matin&nbsp;: Représentation de la Trace et Polynômes**

- **Livrable&nbsp;:** Classe `FieldElement` fonctionnelle et fonctions polynomiales de base.

**Après-midi&nbsp;: Extension à Bas Degré (LDE) et Polynômes de Commitment**

- **Livrable&nbsp;:** Fonctions `low_degree_extend`, `vanishing_poly_coeffs`, et constructeur/vérifieur `MerkleTree` fonctionnels.

### Jour 3&nbsp;: Le Protocole FRI 

*Complexité&nbsp;: Élevée*

**Matin&nbsp;: Théorie FRI et Implémentation du Pliage**

- **Livrable&nbsp;:** Une fonction pour un seul tour de pliage FRI.

**Après-midi&nbsp;: Implémentation Complète du Prouveur FRI**

- **Livrable&nbsp;:** Une fonction `prove_fri` fonctionnelle.

### Jour 4&nbsp;: Assemblage du Prouveur et du Vérificateur STARK 

*Complexité&nbsp;: Élevée*

**Matin&nbsp;: Assemblage du Prouveur STARK et Division Polynomiale**

- **Livrable&nbsp;:** Une fonction `prove_stark` complète.

**Après-midi&nbsp;: Assemblage du Vérificateur STARK et Débogage Initial**

- **Livrable&nbsp;:** Une fonction `verify_stark` complète.

### Jour 5&nbsp;: Débogage, Polissage et Préparation de la Présentation 

*Complexité&nbsp;: Moyenne-Faible*

**Matin&nbsp;: Débug et Raffinement du Code**

- **Livrable&nbsp;:** Un prouveur/vérifieur STARK fonctionnel pour l'affirmation de la suite de Fibonacci.

**Après-midi&nbsp;: Préparation de la Présentation et Polissage Final**

- **Livrable&nbsp;:** Une base de code propre et une CLI pour générer et vérifier une preuve pour la démonstration.

---

## Guide des Outils Git et Dev

### Structure Finale Attendue du Projet

```
stark_projet/
├── pyproject.toml           # Configuration du projet, dépendances (pour uv)
├── .gitignore               # Fichiers/dossiers à ignorer par Git (par exemple, .venv/, __pycache__)
├── README.md                # Description du projet, comment l'exécuter, etc.
├── src/                     # Répertoire du code source
│   └── stark_project/       # Le paquet Python principal du projet
│       ├── __init__.py      # Fait de 'stark_project' un paquet Python
│       ├── main.py          # Point d'entrée&nbsp;: exécute la démo STARK
│       ├── field.py         # Implémente l'arithmétique des corps finis
│       ├── polynomial.py    # Implémente les opérations polynomiales (eval, interpolate, LDE, poly_div, vanishing_poly_coeffs)
│       ├── merkle.py        # Implémente l'arbre de Merkle pour les commitments
│       ├── fri.py           # Implémente le protocole FRI (parties prouveur et vérifieur)
│       ├── stark.py         # Les fonctions de haut niveau du prouveur et du vérifieur STARK pour la preuve de séquence
│       └── utils.py         # Fonctions utilitaires générales (par exemple, fonctions de hachage, génération de défis)
├── tests/                   # (Facultatif mais recommandé) Répertoire pour les tests unitaires
│   ├── test_field.py
│   ├── test_polynomial.py
│   ├── test_merkle.py
│   └── ...
└── .git/                    # Métadonnées du dépôt Git (caché)
```

### Commandes Principales `uv`

- **Installation/Mise à Jour des Dépendances&nbsp;:**

  ```bash
  uv sync
  ```

  - Exécuter ceci chaque fois que `pyproject.toml` change.

- **Exécution de Scripts Python dans l'Environnement Virtuel&nbsp;:**

  ```bash
  uv run python src/stark_project/main.py
  ```

  - `uv run` utilise automatiquement l'environnement virtuel du projet, il n'est donc pas nécessaire de l'activer manuellement.

- **Entrée dans le Shell de l'Environnement Virtuel (pour le travail interactif)&nbsp;:**

  ```bash
  uv shell
  ```

  - Noter qu'il est préférable d'utiliser le mode "Jupyter: Create Interactive Window" de Cursor.

- **Ajout d'une Nouvelle Dépendance (par exemple, pour les tests)&nbsp;:**
  ```bash
  uv add pytest
  ```

### Guide Git

Des pratiques Git cohérentes sont cruciales pour le développement collaboratif.

1.  **Début de Journée / Avant de Coder&nbsp;:**

    - Toujours récupérer les dernières modifications de la branche principale&nbsp;:
      ```bash
      git pull --rebase origin main
      ```

2.  **Travail sur une Nouvelle Tâche/Fonctionnalité&nbsp;:**

    - **Toujours créer une nouvelle branche** pour les nouvelles fonctionnalités importantes ou les corrections de bogues. Cela maintient la branche `main` propre et stable.
      ```bash
      git checkout -b feature/nom-de-votre-tache-descriptive
      # Exemple&nbsp;: git checkout -b feature/implementer-division-poly
      ```
    - Commiter souvent, avec des changements petits et logiques.
    - Utiliser `git add -p` pour mettre en staging des modifications spécifiques dans un fichier, permettant des commits plus granulaires.
    - Rédiger des messages de commit clairs et descriptifs au mode impératif (par exemple, "feat: Ajouter la classe FieldElement" au lieu de "Ajout de la classe FieldElement").

3.  **Partage du Travail / Collaboration&nbsp;:**

    - Pousser périodiquement votre branche vers le dépôt distant, surtout avant de faire une pause ou lorsque vous voulez que les autres voient votre progression&nbsp;:
      ```bash
      git push origin feature/nom-de-votre-tache-descriptive
      ```
    - Pour fusionner les modifications dans `main`, **préférer la création de Pull Requests (PRs)** sur github - aka Merge Requests (MRs) sur gitlab.

4.  **Débogage et Raffinement&nbsp;:**
    - Utiliser `git status` fréquemment pour voir les changements.
    - Utiliser `git log` pour revoir l'historique des commits.
    - Si une erreur est commise, `git reset` (avec précaution !) ou `git revert` peuvent aider.

---
