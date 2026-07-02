Tu es MiniMax M3. Tu dois agir comme un ingénieur logiciel Python senior spécialisé en cryptographie pédagogique, algèbre abstraite et protocoles STARK.

Je dois réaliser un projet Python dont l’objectif est d’implémenter un prouveur et un vérifieur STARK simplifiés pour prouver une affirmation sur une suite de Fibonacci.

Objectif mathématique :
Étant donnés c0, c1, N et C, construire un protocole permettant de prouver que la suite définie par :

u0 = c0
u1 = c1
u_{i+2} = u_{i+1} + u_i

vérifie bien u_N = C, sans que le vérifieur recalcule toute la suite.

Le projet doit être pédagogique, rigoureux, bien structuré, testé, et écrit en Python moderne. Il n’a pas vocation à être une implémentation cryptographique de production.

Contraintes générales :

* Utiliser Python moderne, clair, typé et maintenable.
* Le code doit être de très haute qualité.
* Ne jamais utiliser de float.
* Toute l’arithmétique doit se faire dans un corps fini.
* Utiliser le corps fini F_p avec p = 3221225473.
* Préférer les int Python natifs pour éviter les problèmes d’overflow.
* Le code doit être modulaire.
* Chaque module doit avoir des tests unitaires.
* Les tests doivent inclure des cas positifs et des cas négatifs.
* Ne jamais assembler le STARK complet avant d’avoir testé séparément les briques de base.
* Le vérifieur ne doit pas recalculer toute la suite de Fibonacci.
* Le projet doit rester compréhensible et bien documenté.
* Ajouter des docstrings courtes mais précises.
* Ajouter des commentaires seulement quand ils clarifient une idée mathématique ou protocolaire.
* Ne pas produire du code “magique” ou trop compact.
* Ne pas cacher les limites de l’implémentation.

Contraintes d’environnement :

* L’environnement uv est déjà initialisé.
* Ne pas recréer le projet avec `uv init`.
* Travailler dans le projet existant.
* Ne pas utiliser pip directement.
* Ne pas utiliser requirements.txt.
* Toutes les dépendances doivent être gérées dans pyproject.toml.
* Le fichier uv.lock doit être conservé et versionné.
* Toutes les commandes doivent être données avec uv.
* La commande principale de test doit être : uv run pytest
* Le linting/formatage doit utiliser ruff :
  uv run ruff check .
  uv run ruff format .
* Le README doit expliquer uniquement une installation avec uv.

Avant de coder :

1. Inspecter la structure actuelle du projet.
2. Lire le fichier pyproject.toml.
3. Vérifier que le package Python est bien configuré.
4. Vérifier que le dossier src/ et le package stark_fibonacci/ existent ou les créer proprement s’ils manquent.
5. Vérifier que les dépendances de développement nécessaires sont présentes.
6. Ne pas modifier inutilement la configuration existante.
7. Toute modification de pyproject.toml doit être justifiée.

Commandes autorisées :

* uv sync
* uv add --dev pytest hypothesis ruff
* uv run pytest
* uv run ruff check .
* uv run ruff format .

Commandes interdites :

* uv init
* pip install
* création d’un requirements.txt

Si pytest, hypothesis ou ruff ne sont pas encore présents dans pyproject.toml, les ajouter avec :
uv add --dev pytest hypothesis ruff

La commande principale de validation doit rester :
uv run pytest

La commande de qualité doit rester :
uv run ruff check .
uv run ruff format .

Script CLI attendu dans pyproject.toml :
[project.scripts]
stark-fibonacci = "stark_fibonacci.cli:main"

Architecture cible :
stark-fibonacci/
├── pyproject.toml
├── uv.lock
├── README.md
├── .gitignore
├── src/
│   └── stark_fibonacci/
│       ├── **init**.py
│       ├── field.py
│       ├── polynomial.py
│       ├── domain.py
│       ├── trace.py
│       ├── air.py
│       ├── merkle.py
│       ├── transcript.py
│       ├── fri.py
│       ├── proof.py
│       ├── stark.py
│       └── cli.py
└── tests/
├── test_field.py
├── test_polynomial.py
├── test_domain.py
├── test_trace.py
├── test_air.py
├── test_merkle.py
├── test_transcript.py
├── test_fri.py
└── test_stark.py

Méthode de travail obligatoire :
Pour chaque étape :

1. Expliquer brièvement l’objectif mathématique ou informatique.
2. Créer ou modifier uniquement les fichiers nécessaires.
3. Donner le code complet des fichiers modifiés.
4. Ajouter les tests associés.
5. Expliquer les invariants testés.
6. Donner les commandes uv à exécuter.
7. Ne passer à l’étape suivante que lorsque la brique actuelle est cohérente et testable.

Ordre strict d’implémentation :

Étape 1 — Corps fini
Fichier : src/stark_fibonacci/field.py
Tests : tests/test_field.py

Implémenter une classe FieldElement immuable représentant un élément de F_p.

Méthodes obligatoires :

* **add**
* **sub**
* **neg**
* **mul**
* **truediv**
* **pow**
* inverse()
* zero()
* one()
* from_int()

Tests obligatoires :

* addition modulo p
* soustraction modulo p
* multiplication modulo p
* inverse
* division
* puissance
* théorème de Fermat : a^(p-1) = 1 pour a non nul
* division par zéro interdite
* propriétés avec Hypothesis :

  * associativité de +
  * commutativité de +
  * commutativité de *
  * distributivité
  * a / a = 1 pour a non nul

Étape 2 — Polynômes
Fichier : src/stark_fibonacci/polynomial.py
Tests : tests/test_polynomial.py

Représenter un polynôme par ses coefficients :
coeffs[i] = coefficient de X^i

Implémenter :

* degree()
* evaluate(x)
* **add**
* **sub**
* **mul**
* scale()
* divide_by()
* lagrange_interpolate(points)
* zerofier(domain)

Formules à respecter :
P(x) = a0 + a1 x + ... + ad x^d

Interpolation de Lagrange :
P(X) = somme_i y_i L_i(X)
L_i(X) = produit_{j != i} (X - x_j) / (x_i - x_j)

Tests obligatoires :

* évaluation constante
* évaluation linéaire
* addition
* multiplication
* interpolation retrouvant un polynôme connu
* division exacte
* division avec reste
* zerofier qui s’annule sur tout le domaine

Étape 3 — Domaines multiplicatifs
Fichier : src/stark_fibonacci/domain.py
Tests : tests/test_domain.py

Implémenter :

* primitive_root_of_unity(order)
* multiplicative_subgroup(size)
* blowup_domain(base_size, blowup_factor)

Contraintes :

* size doit diviser p - 1
* dans ce projet, les tailles de domaine sont des puissances de 2
* vérifier que le générateur a un ordre exact

Tests obligatoires :

* générateur d’ordre exact
* domaine sans doublons
* chaque élément x du domaine vérifie x^size = 1
* erreur si la taille est invalide

Étape 4 — Trace Fibonacci
Fichier : src/stark_fibonacci/trace.py
Tests : tests/test_trace.py

Implémenter :
fibonacci_trace(c0: FieldElement, c1: FieldElement, n: int) -> list[FieldElement]

La trace doit contenir :
[u0, u1, ..., uN]

Tests obligatoires :

* longueur correcte
* valeurs initiales correctes
* relation de récurrence respectée
* petits exemples connus
* comportement modulo p

Étape 5 — Contraintes AIR Fibonacci
Fichier : src/stark_fibonacci/air.py
Tests : tests/test_air.py

Construire une représentation des contraintes AIR de Fibonacci.

Contraintes :

1. u0 = c0
2. u1 = c1
3. uN = C
4. u_{i+2} - u_{i+1} - u_i = 0

Si T est le polynôme de trace et si T(g^i) = u_i, alors la contrainte de transition doit être exprimée sous forme polynomiale :
T(g^2 X) - T(g X) - T(X) = 0

Implémenter une classe :
FibonacciAIR

Avec :

* c0
* c1
* claimed_output
* trace_length
* boundary_constraints()
* transition_constraint()

Tests obligatoires :

* une trace valide satisfait la transition
* une trace modifiée échoue
* les conditions initiales sont vérifiées
* la condition finale est vérifiée

Étape 6 — Interpolation et Low Degree Extension
Fichiers : polynomial.py, domain.py, stark.py
Tests associés dans test_polynomial.py et test_stark.py

Implémenter :

* interpolate_trace(trace, domain)
* low_degree_extend(poly, extended_domain)

Principe :

1. La trace discrète est interpolée en un polynôme T.
2. T est évalué sur un domaine plus grand.
3. Cette évaluation est la Low Degree Extension.

Tests obligatoires :

* le polynôme interpolé redonne les valeurs de la trace sur le domaine initial
* la LDE a la bonne taille
* la LDE reste cohérente avec le polynôme initial

Étape 7 — Arbre de Merkle
Fichier : src/stark_fibonacci/merkle.py
Tests : tests/test_merkle.py

Implémenter un arbre de Merkle avec SHA-256.

Classes attendues :

* MerkleProof
* MerkleTree

Méthodes :

* root()
* open(index)
* verify(root, proof)

Contraintes :

* sérialisation déterministe des FieldElement
* gérer les nombres impairs de feuilles
* hash de feuilles et hash de nœuds séparés si possible

Tests obligatoires :

* root déterministe
* ouverture valide pour chaque feuille
* modification de feuille rejetée
* modification d’index rejetée
* modification de chemin rejetée
* nombre impair de feuilles géré correctement

Étape 8 — Transcript Fiat-Shamir
Fichier : src/stark_fibonacci/transcript.py
Tests : tests/test_transcript.py

Implémenter un transcript déterministe pour générer les challenges du protocole.

Méthodes :

* append_message(label: bytes, message: bytes)
* challenge_field(label: bytes) -> FieldElement
* challenge_index(label: bytes, upper_bound: int) -> int

Tests obligatoires :

* déterminisme
* messages différents donnent des challenges différents
* challenge_index reste dans l’intervalle
* séparation de domaine par labels

Étape 9 — FRI simplifié
Fichier : src/stark_fibonacci/fri.py
Tests : tests/test_fri.py

Implémenter une version pédagogique de FRI.

But :
Prouver qu’une fonction évaluée sur un domaine est proche d’un polynôme de bas degré.

Implémenter :

* fri_fold(domain, evaluations, alpha)
* fri_prove(domain, evaluations, claimed_degree, transcript)
* fri_verify(proof, root, domain_size, claimed_degree, transcript)

Formule pédagogique de pliage :
f_next(x^2) = (f(x) + f(-x))/2 + alpha * (f(x) - f(-x))/(2x)

Tests obligatoires :

* le pliage divise la taille du domaine par 2
* le pliage conserve la structure de bas degré
* une preuve FRI valide est acceptée
* une preuve FRI modifiée est rejetée
* un chemin Merkle FRI modifié est rejeté

Étape 10 — Objet preuve
Fichier : src/stark_fibonacci/proof.py

Créer les dataclasses nécessaires :

* PublicInputs
* QueryOpening
* FRIProof
* StarkProof

Contraintes :

* les preuves doivent être sérialisables en JSON
* les bytes doivent être encodés en hexadécimal
* ajouter to_json() et from_json() si utile

Étape 11 — Prouveur STARK
Fichier : src/stark_fibonacci/stark.py
Tests : tests/test_stark.py

Implémenter :
prove_fibonacci(c0: int, c1: int, n: int, claimed_output: int, blowup_factor: int = 8, num_queries: int = 16) -> StarkProof

Étapes internes :

1. Convertir c0, c1 et claimed_output dans F_p.
2. Générer la trace Fibonacci.
3. Vérifier localement que trace[n] == claimed_output.
4. Construire le domaine de trace.
5. Interpoler la trace en polynôme T.
6. Construire le domaine étendu.
7. Évaluer T sur le domaine étendu.
8. Construire le Merkle commitment de la LDE.
9. Construire les contraintes AIR.
10. Construire un polynôme de composition simplifié.
11. Committer les évaluations nécessaires.
12. Lancer FRI.
13. Générer les ouvertures aléatoires.
14. Retourner un objet StarkProof sérialisable.

Tests obligatoires :

* une preuve est produite
* les public inputs sont corrects
* deux preuves identiques sont déterministes si le transcript est déterministe
* claimed_output faux provoque une erreur

Étape 12 — Vérifieur STARK
Fichier : src/stark_fibonacci/stark.py
Tests : tests/test_stark.py

Implémenter :
verify_fibonacci(proof: StarkProof) -> bool

Le vérifieur doit :

1. Lire les public inputs.
2. Reconstruire le transcript.
3. Vérifier les Merkle openings.
4. Vérifier les contraintes de bord ouvertes.
5. Vérifier les contraintes de transition ouvertes.
6. Vérifier la preuve FRI.
7. Retourner True ou False.

Tests obligatoires :

* preuve valide acceptée
* mauvais c0 rejeté
* mauvais c1 rejeté
* mauvais output rejeté
* root Merkle modifiée rejetée
* ouverture modifiée rejetée
* couche FRI modifiée rejetée

Étape 13 — CLI
Fichier : src/stark_fibonacci/cli.py
Tests : tests/test_cli.py

Commandes attendues :
uv run stark-fibonacci demo
uv run stark-fibonacci prove --c0 1 --c1 1 --n 32 --output 3524578 --proof proof.json
uv run stark-fibonacci verify --proof proof.json

Le mode demo doit :

1. Générer une preuve pour un exemple simple.
2. Vérifier la preuve.
3. Afficher clairement le résultat.
4. Montrer que le vérifieur ne recalcule pas toute la suite.

Étape 14 — README
Fichier : README.md

Le README doit contenir :

* objectif du projet
* explication simple d’un STARK
* explication de la suite Fibonacci
* installation avec uv
* commandes de test
* commandes CLI
* architecture des fichiers
* limites de sécurité
* ressources utilisées

Ressources mathématiques et informatiques à utiliser :

1. STARK 101 — StarkWare
   https://starkware.co/stark-101/

2. Anatomy of a STARK — Alan Szepieniec
   https://aszepieniec.github.io/stark-anatomy/
   https://github.com/aszepieniec/stark-anatomy/

3. RISC Zero — STARK by Hand
   https://dev.risczero.com/proof-system/stark-by-hand

4. Papier FRI original
   https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ICALP.2018.14

5. Papier STARK original
   https://eprint.iacr.org/2018/046

6. Documentation uv
   https://docs.astral.sh/uv/

7. Documentation pytest
   https://docs.pytest.org/

8. Documentation Hypothesis
   https://hypothesis.readthedocs.io/

9. Documentation Ruff
   https://docs.astral.sh/ruff/

Règle importante :
Tu dois produire une implémentation progressive. Ne code pas tout d’un coup. Commence uniquement par l’étape 1 : field.py et tests/test_field.py. Attends ensuite que je valide avant de passer à l’étape suivante.

Pour l’étape 1, fournis :

* l’explication mathématique courte
* le code complet de field.py
* le code complet de tests/test_field.py
* les commandes uv à exécuter
* les invariants testés
* les limites éventuelles
