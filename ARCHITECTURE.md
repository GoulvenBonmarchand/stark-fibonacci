# Architecture détaillée du prouveur/vérifieur STARK-Fibonacci

> **Public** : ingénieurs et étudiants en cryptographie / preuves à divulgation nulle de connaissance.
> **Pré-requis** : algèbre de base (groupes, anneaux, corps finis) et familiarité avec la notion de polynôme. Aucune connaissance préalable des SNARK/STARK n'est requise, bien que cela aide.

Ce document explique **ligne par ligne, fichier par fichier** comment l'implémentation Python produit et vérifie une preuve STARK pour la suite de Fibonacci. Il replace chaque bloc de code dans son contexte algorithmique et mathématique, en donnant pour chaque étape :

1. **l'intention** (à quoi sert ce morceau),
2. **les mathématiques sous-jacentes** (la propriété exacte que l'on exploite),
3. **l'implémentation concrète** (ce que fait le code).

---

## Sommaire

1. [Idée de haut niveau](#1-idée-de-haut-niveau)
2. [Carte des fichiers](#2-carte-des-fichiers)
3. [Fondations mathématiques](#3-fondations-mathématiques)
4. [Module `field.py` — le terrain de jeu](#4-module-fieldpy--le-terrain-de-jeu)
5. [Module `polynomial.py` — l'algèbre polynomiale](#5-module-polynomialpy--lalgèbre-polynomiale)
6. [Module `merkle.py` — engagements par arbre de hachage](#6-module-merklepy--engagements-par-arbre-de-hachage)
7. [Module `utils.py` — Fiat-Shamir et sérialisation](#7-module-utilspy--fiat-shamir-et-sérialisation)
8. [Module `fri.py` — Fast Reed-Solomon IOP of Proximity](#8-module-fripy--fast-reed-solomon-iop-of-proximity)
9. [Module `stark.py` — la pipeline STARK complète](#9-module-starkpy--la-pipeline-stark-complète)
10. [Module `main.py` — démonstration end-to-end](#10-module-mainpy--démonstration-end-to-end)
11. [Le prouveur pas-à-pas](#11-le-prouveur-pas-à-pas)
12. [Le vérifieur pas-à-pas](#12-le-vérifieur-pas-à-pas)
13. [Pourquoi ça marche : soundness et sécurité](#13-pourquoi-ça-marche--soundness-et-sécurité)
14. [Coûts asymptotiques et taille de preuve](#14-coûts-asymptotiques-et-taille-de-preuve)
15. [Limitations et pistes d'évolution](#15-limitations-et-pistes-dévolution)

---

## 1. Idée de haut niveau

### 1.1. L'énoncé

On se donne :
- deux valeurs initiales `c₀ = u₀` et `c₁ = u₁`,
- un entier `N ≥ 2`,
- une valeur revendiquée `C`.

On prétend que la suite définie par `uₙ = uₙ₋₁ + uₙ₋₂` vérifie `u_N = C`. Le but du STARK est de **prouver cette affirmation sans révéler la suite complète ni la recalculer**. Pour le vérifieur, recalculer 32 termes demanderait des microsecondes — l'intérêt est pédagogique : la même machinerie prouve des énoncés arbitrairement gros avec un vérifieur quasi-constant.

### 1.2. L'architecture en trois couches

Un STARK n'est pas un seul objet mathématique mais un **empilement de trois protocoles** :

| Couche | Rôle | Module |
|--------|------|--------|
| **Arithmétique (AIR)** | Traduit l'énoncé en contraintes polynomiales | `stark.py` |
| **IOP de proximité (FRI)** | Prouve qu'une fonction est proche d'un polynôme de bas degré | `fri.py` |
| **Engagement polynomial** | Permet au vérifieur de demander des valeurs ponctuelles avec authentification | `merkle.py` |

Le reste (corps fini, polynômes, hachage) fournit la boîte à outils élémentaire.

### 1.3. Le flux global

```
                    PROVEUR                                  VÉRIFIEUR
                    ───────                                  ─────────
   u₀..u_N ─► Polynôme trace T(x)                params (c₀, c₁, N, C) publics
              (interpolation sur domaine T)       
                    │                                    Reçoit :
                    ▼                                    ─ trace_root
   Polynôme de composition C(x)                      ─ comp_root
   = quotients de contraintes                        ─ FRI proof
                    │                                    ─ queries
                    ▼                                    
   LDE sur domaine L (coset, |L|=blowup·|T|)        
   Merkle(T|_L), Merkle(C|_L) ──────────────►        Recalcule α, indices de query
                    │                                 
   FRI(C|_L) pour prouver bas degré                 ───►  verify_fri
                    │                                    Recompose chaque query :
   Queries (Fiat-Shamir)                            ───►  ├─ auth path T → 3 valeurs
   ├─ T(x), T(gx), T(g²x) avec auth paths               ├─ auth path C → C(x)
   ├─ C(x) avec auth path                              └─ C(x) == recompute(...) ?
   └─ ouverture FRI                                    
```

---

## 2. Carte des fichiers

```
src/stark_fibonacci/
├── __init__.py          # rien à signaler
├── field.py             # arithmétique F_p + génération de domaines
├── polynomial.py        # algèbre des polynômes (Lagrange, division, LDE)
├── merkle.py            # arbre de Merkle SHA-256 avec padding
├── fri.py               # prouveur/vérifieur FRI binaire
├── stark.py             # pipeline STARK (preuve de la suite Fibonacci)
├── utils.py             # hachage, sérialisation, échantillonnage
└── main.py              # point d'entrée CLI : demo end-to-end
```

Dépendances :
- `field.py` est **la base** : aucune dépendance interne.
- `polynomial.py` dépend de `field.py`.
- `merkle.py` est autonome (utilise seulement `hashlib`).
- `utils.py` dépend de `field.py`.
- `fri.py` dépend de `field`, `polynomial`, `merkle`, `utils`.
- `stark.py` dépend de tout le monde : `field`, `polynomial`, `merkle`, `fri`, `utils`.
- `main.py` orchestre `stark.py` pour la démo.

---

## 3. Fondations mathématiques

Cette section pose tout le formalisme. Les notations utilisées dans cette section sont reprises à l'identique dans le code.

### 3.1. Corps fini `F_p`

On travaille sur **`F_p`**, le corps fini à `p` éléments, avec :

$$p = 3 \cdot 2^{30} + 1 = 3\,221\,225\,473.$$

**Pourquoi ce premier ?** Son groupe multiplicatif `F_p^* = F_p \setminus \{0\}` est cyclique d'ordre `p − 1 = 3 · 2³⁰`. On en déduit qu'il existe un sous-groupe d'ordre **exactement** `2^k` pour tout `0 ≤ k ≤ 30` : c'est le **2-Sylow** de `F_p^*`. Cette propriété est cruciale pour FRI, car le pliage binaire exige qu'on puisse diviser la taille du domaine par 2 à chaque tour.

**Notation.** Soit `g` un générateur de ce 2-Sylow (d'ordre `2³⁰`).

### 3.2. Sous-groupes et cosets

Pour `k ≤ 30`, posons `g_k = g^{2^{30-k}}`. Alors `<g_k>` est le sous-groupe d'ordre `2^k`. L'élément à la position `i` dans ce sous-groupe est `g_k^i`.

Pour construire un **domaine** d'évaluation `L` (utilisé pour le LDE), on prend un **coset** : on fixe un décalage `s ∉ {0}` et on pose :

$$L = \{s \cdot g_k^i : 0 \leq i < 2^k\}.$$

**Pourquoi un coset et pas le sous-groupe directement ?** Parce que dans le sous-groupe `<g_k>`, l'élément `1 = g_k^0` apparaît déjà comme domaine de trace. Pour ne pas confondre les « engagements » (sur le coset `L`) avec les « vraies » valeurs de la trace (sur le sous-groupe), on les sépare géométriquement. C'est aussi exactement la construction du `STARK 101`.

### 3.3. La propriété « x ↔ −x »

Sur tout coset `D = s · <g_k>` d'ordre `n = 2^k`, on a l'**appariement négatif** :

$$D[i + n/2] = s \cdot g_k^{i + n/2} = s \cdot g_k^{i} \cdot g_k^{n/2} = -D[i],$$

car `g_k^{n/2}` est l'unique élément d'ordre 2 dans `F_p^*`, c'est-à-dire `−1`. Donc dans l'ordre naturel d'indices :

$$\big(D[i], D[i + n/2]\big) = (x, -x).$$

C'est crucial pour FRI : le pliage binaire est `f_{next}(x²) = (f(x) + f(−x))/2 + r · (f(x) − f(−x))/(2x)`, ce qui ne suppose que la disponibilité d'échantillons en `x` et `−x`. Pour nos domaines en cosets, ils tombent naturellement aux indices `i` et `i + n/2`.

### 3.4. Polynômes sur `F_p`

Un polynôme `P ∈ F_p[x]` est représenté par la liste de ses coefficients en degré ascendant :

$$P(x) = c_0 + c_1 \cdot x + c_2 \cdot x^2 + \dots + c_d \cdot x^d,$$

stockée comme `[c₀, c₁, …, c_d]`. Cette convention est utilisée **partout** dans le code (cf. `polynomial.py`).

**Pourquoi pas une représentation plus exotique (point-evaluation, NTT) ?** Parce qu'on travaille sur `n ≤ 128`, l'interpolation de Lagrange en `O(n²)` est très rapide en Python pur. Une NTT impose un agencement différent, plus rapide asymptotiquement mais inutile ici.

### 3.5. Évaluation et interpolation de Lagrange

Étant donné un domaine `D = (d₀, …, d_{n-1})` et des valeurs `v = (v₀, …, v_{n-1})`, il existe un **unique** polynôme `L` de degré `< n` tel que `L(d_i) = v_i`. La formule de Lagrange est :

$$L(x) = \sum_{i=0}^{n-1} v_i \cdot \prod_{j \neq i} \frac{x - d_j}{d_i - d_j}.$$

C'est la base de la construction du **polynôme de trace** : on connaît les valeurs `u_i` sur le domaine de trace, et `T(x)` est l'unique polynôme qui les interpole.

### 3.6. Polynômes d'annulation

Pour un sous-ensemble fini `S ⊂ F_p`, on note :

$$Z_S(x) = \prod_{s \in S} (x - s).$$

C'est le **polynôme d'annulation** de `S` — il s'annule exactement sur `S`.

Si `P` est un polynôme qui s'annule sur `S`, alors `Z_S` divise `P` dans `F_p[x]`. Le quotient `P / Z_S` est alors de degré `deg(P) − |S|`. Cette division est la clef de voûte de l'**AIR** : on remplace chaque contrainte « `P` s'annule sur `S` » par « `P / Z_S` est un polynôme », qui est une affirmation de **bas degré** — exactement ce que FRI sait prouver.

### 3.7. Reed–Solomon et « proche d'un polynôme »

Soit `D` un domaine et `f : D → F_p` une fonction. On note `δ(f, P_d)` la **distance de Reed–Solomon** :

$$\delta(f, P_d) = \min\{ |D \setminus S| / |D| : \exists P \in F_p[x], \deg P < d, \forall x \in S, f(x) = P(x) \},$$

où `P_d` désigne les polynômes de degré `< d`. Plus simplement : « quelle proportion de points `f` doit-on modifier pour que `f` devienne l'évaluation d'un polynôme de degré `< d` ? ».

FRI est un **IOP de proximité** : il produit une preuve que `f` est δ-proche de `P_d`, où `δ` est petit (ici `δ = 1 − 1/blowup_factor`).

### 3.8. Engagement par arbre de Merkle

Un **engagement** sur une suite de valeurs `v₀, …, v_{n-1}` est un objet :
- **liant** (`binding`) : le prouveur ne peut pas modifier `v` après publication de l'engagement,
- **opaque** (`hiding`) optionnelle : on peut souhaiter cacher les valeurs (ici on ne le cache pas).

Un arbre de Merkle binaire sur les feuilles `H(v_i)` (avec `H` un hachage, ici SHA-256), avec nœuds internes `H(gauche || droite)`, fournit exactement cela. La racine est l'engagement.

Une **preuve d'ouverture** pour la position `i` est la liste des nœuds frères (« siblings ») de la feuille `i` jusqu'à la racine. Le vérifieur rehash et compare à la racine publiée.

### 3.9. Transformation de Fiat-Shamir

Pour transformer un protocole interactif en non-interactif, on remplace chaque défi aléatoire du vérifieur par `H(transcrit)`, où `H` est un hachage et le « transcrit » est la concaténation de tous les messages échangés jusque-là. C'est **Fiat-Shamir**. Sous l'hypothèse que `H` se comporte comme un oracle aléatoire, cette transformation préserve la sécurité (`soundness`) dans le modèle de l'oracle aléatoire.

---

## 4. Module `field.py` — le terrain de jeu

`field.py` ne fait qu'une chose : représenter les éléments de `F_p` et générer les domaines nécessaires (sous-groupes, cosets).

### 4.1. La classe `FieldElement`

```python
DEFAULT_PRIME: int = 3 * (1 << 30) + 1

class FieldElement:
    __slots__ = ("value", "prime")

    def __init__(self, value: int, prime: int = DEFAULT_PRIME) -> None:
        ...
        self.value = value % prime
```

**Pourquoi `__slots__` ?** Pour économiser la mémoire : chaque `FieldElement` ne porte que deux entiers. Avec des centaines de FieldElements par preuve, ça compte.

**Pourquoi `value % prime` dans le constructeur ?** Pour garantir la **forme canonique** : deux représentations du même élément (par exemple `2` et `p + 2`) donnent la même valeur après réduction. C'est ce qui rend `==` et `hash` fiables.

**Pourquoi tester `prime > 2` ?** Pour rejeter les « corps » triviaux (`F_1`, `F_2`) où les opérations arithmétiques n'ont pas les propriétés attendues (notamment l'inversibilité).

#### 4.1.1. L'inversion via Fermat

```python
def __truediv__(self, other):
    ...
    inv = pow(other.value, self.prime - 2, self.prime)
    return FieldElement(self.value * inv, self.prime)
```

Par le **petit théorème de Fermat**, pour `a ≠ 0`, on a `a^{p−1} ≡ 1 (mod p)`. Donc :

$$a^{-1} \equiv a^{p-2} \pmod{p}.$$

`pow(a, p-2, p)` calcule cette exponentiation modulaire en `O(log p)` multiplications (méthode « square-and-multiply » du Python natif, qui est en C et ultra-rapide).

#### 4.1.2. Surcharges Python

Les opérateurs `+`, `-`, `*`, `**`, `/`, `==`, `hash()` sont surchargés. La méthode `_coerce(other)` permet de mélanger `FieldElement` et `int` (`FieldElement(3) + 5` marche grâce à `__radd__`). La méthode `_check_prime` empêche de mélanger deux corps différents.

### 4.2. Construction de `g` (générateur du 2-Sylow)

```python
def primitive_root(prime: int = DEFAULT_PRIME) -> int:
    ...
    g = 2
    while g < prime:
        ok = True
        for q in factors:
            if pow(g, (p - 1) // q, p) == 1:
                ok = False
                break
        if ok:
            return g
        g += 1
```

L'algorithme cherche `g` tel que `g^{(p-1)/q} ≠ 1` pour tout facteur premier `q` de `p − 1`. Pour `p = 3·2³⁰ + 1`, on a `p − 1 = 2³⁰ · 3`, donc `q ∈ {2, 3}`. Concrètement, on cherche un générateur du groupe cyclique `F_p^*`. C'est une variante de la méthode standard : tester que `g^{(p-1)/q} ≠ 1` pour tous les `q` est équivalent à vérifier que `g` n'appartient à aucun sous-groupe propre strict.

`two_adic_generator(prime, order)` élève ce générateur à `g^{(p-1)/2^order}` pour obtenir un élément **exactement** d'ordre `2^order`. L'assertion vérifie le résultat.

### 4.3. Génération de domaines

```python
def subgroup_of_order(prime, order):
    g = two_adic_generator(prime, MAX_TWO_ADIC_ORDER)
    base = pow(g, 1 << (MAX_TWO_ADIC_ORDER - order.bit_length() + 1), prime)
    elements = [1]
    cur = 1
    for _ in range(order - 1):
        cur = (cur * base) % prime
        elements.append(cur)
    elements.sort()
    return elements
```

Cette fonction calcule **tous les éléments** d'un sous-groupe d'ordre `2^k` :

$$G = \{g^{2^{30-k} \cdot i} : 0 \le i < 2^k\} = \{1, base, base^2, \ldots, base^{2^k-1}\}.$$

**Attention :** la liste retournée est **triée** (en ordre croissant des entiers représentants), ce qui est commode pour l'affichage mais **pas** pour FRI : pour FRI on a besoin du « natural order » `g^i`. La fonction `gen_domain` de `fri.py` construit, elle, la bonne liste.

### 4.4. `coset_of_subgroup`

Multiplie chaque élément du sous-groupe par un décalage (`shift`). Le résultat est trié.

**Pourquoi trier ?** Parce que le tri élimine les ambiguïtés de représentation. Mais le vérifieur **doit** utiliser le même ordre que le prouveur (trié ou naturel selon le contexte), sans quoi les auth paths Merkle pointent au mauvais endroit.

### 4.5. Échantillonnage depuis une semence

```python
def sample_in_field(seed: bytes, prime=DEFAULT_PRIME) -> int:
    out = int.from_bytes(hashlib.sha256(seed).digest(), "big")
    return out % prime
```

Le hachage SHA-256 d'une semence donne 256 bits, dont on prend le modulo `p`. Pour `p ≈ 2³¹`, le biais induit est au plus `2^{256} mod p < p`, négligeable en pratique. Une version stricte utiliserait plusieurs itérations, inutile ici.

---

## 5. Module `polynomial.py` — l'algèbre polynomiale

`polynomial.py` implémente les opérations polynomiales élémentaires sur `F_p[x]`. C'est le cœur algorithmique du STARK.

### 5.1. Représentation

Tous les polynômes sont des `list[FieldElement]` en ordre ascendant. `zero_poly()` retourne `[0]` (et pas `[]`) pour que le degré soit bien défini. La fonction `strip()` supprime les zéros en tête (degré le plus haut). `degree()` retourne `−1` pour le polynôme nul.

### 5.2. Évaluation : Horner

```python
def eval_poly_at(coeffs, x):
    if not coeffs:
        return FieldElement.zero()
    acc = coeffs[-1]
    for c in reversed(coeffs[:-1]):
        acc = acc * x + c
    return acc
```

Schéma de Horner : on calcule

$$(\cdots((c_d \cdot x) + c_{d-1}) \cdot x + \cdots) \cdot x + c_0$$

en `d` multiplications et `d` additions. C'est l'évaluation polynomiale la plus stable numériquement et la plus rapide en pratique.

### 5.3. Addition, soustraction, multiplication, scalaire

Toutes scolaires, en `O(n + m)` ou `O(n · m)` pour la multiplication. La multiplication a une optimisation : on saute les coefficients nuls (`if ca.is_zero(): continue`) — très efficace sur des polynômes creux.

### 5.4. Division euclidienne

```python
def poly_div(num, den):
    ...
    lead_b_inv = b[-1].inverse()
    ...
    while len(r) >= len(b) and not is_zero(r):
        coef = r[-1] * lead_b_inv
        idx = len(r) - len(b)
        q[idx] = coef
        for i, cb in enumerate(b):
            r[idx + i] = r[idx + i] - coef * cb
        r = strip(r)
```

L'algorithme classique de division euclidienne `num = q · den + r`, en `O(n · m)` :

1. On inverse le coefficient dominant de `den` (`lead_b_inv`).
2. Tant que le reste `r` est de degré `≥ deg(den)`, on extrait le coefficient dominant de `r`, on multiple `den` pour l'annuler, et on l'ajoute à `q`.
3. On strippe (c'est-à-dire on tronque les zéros de tête).

Le test `len(a) < len(b)` traite le cas trivial où `num < den`.

**Note mathématique.** La division est garantie exacte dans deux cas :
- quand `den` divise `num` (cas où `num` et `den` ont une racine commune multiple — c'est le cas transitionnel),
- le cas reste est `0`.

### 5.5. Polynômes d'annulation

```python
def vanishing_eval_at(domain, x):
    acc = FieldElement.one()
    for d in domain:
        acc = acc * (x - d)
    return acc
```

Évalue `Z(x) = ∏_{d ∈ D}(x − d)` sans construire les coefficients. C'est **exactement** ce dont on a besoin côté vérifieur : pour la composition, on a juste besoin de `Z_transition(x)` au point `x` courant — inutile de matérialiser le polynôme.

```python
def vanishing_poly_coeffs(domain):
    coeffs = [FieldElement.one()]
    for d in domain:
        coeffs = mul_polys(coeffs, [-d, FieldElement.one()])
    return strip(coeffs)
```

Variante qui construit les coefficients — utile côté prouveur pour `poly_div`.

### 5.6. Interpolation de Lagrange

```python
def interpolate_lagrange(domain, values):
    n = len(domain)
    ...
    denom = []
    for i in range(n):
        prod = FieldElement.one()
        di = domain[i]
        for j in range(n):
            if j == i: continue
            prod = prod * (di - domain[j])
        denom.append(prod)
    ...
    for i in range(n):
        wi = values[i] * denom[i].inverse()
        basis = [FieldElement.one()]
        for j in range(n):
            if j == i: continue
            basis = mul_polys(basis, [-domain[j], FieldElement.one()])
        for k, c in enumerate(basis):
            out[k] = out[k] + wi * c
    return strip(out)
```

L'algorithme « bête » :

$$L(x) = \sum_{i=0}^{n-1} v_i \cdot \prod_{j \neq i} \frac{x - d_j}{d_i - d_j}.$$

Complexité `O(n²)` en multiplications de corps. Pour `n = 32`, c'est ~1024 multiplications, rapide.

**Détails fins.** `denom[i]` précalcule `∏_{j≠i}(d_i − d_j)` (le dénominateur du i-ième coefficient). `wi` est ce dénominateur inversé multiplié par `v_i`. Pour chaque `i`, on accumule `wi · ∏_{j≠i}(x − d_j)` dans `out`.

Une version plus avancée utiliserait des poids barycentriques pour la stabilité numérique, mais en `O(n²)` c'est inutile ici.

### 5.7. LDE (low-degree extension)

```python
def low_degree_extension(trace_domain, trace_values, lde_domain):
    ...
    for x in lde_domain:
        num = FieldElement.zero()
        for i in range(n):
            wi = FieldElement.one()
            di = trace_domain[i]
            for j in range(n):
                if j == i: continue
                wi = wi * (x - trace_domain[j]) * (di - trace_domain[j]).inverse()
            num = num + trace_values[i] * wi
        out.append(num)
    return out
```

Étant donné un polynôme `T` connu par ses valeurs `T(d_i) = v_i` sur un domaine `trace_domain`, on évalue `T` sur un sur-ensemble `lde_domain` en utilisant la formule de Lagrange **directement** (pas besoin de calculer d'abord les coefficients).

Complexité : `O(|lde| · |trace|)`. Pour `|lde| = 128`, `|trace| = 32`, c'est 4096 multiplications, instantané.

**Variante barycentrique (commentaire dans le code).** Pour de très grandes traces, on peut précalculer des poids barycentriques `w_i = 1 / ∏_{j≠i}(d_i − d_j)` puis évaluer en `O(n)` par point avec une somme `L(x) = (∑ w_i v_i / (x − d_i)) / ∑ w_i / (x − d_i)`. Le commentaire mentionne ce raffinement mais ne l'implémente pas — non nécessaire pour la taille du problème.

---

## 6. Module `merkle.py` — engagements par arbre de hachage

`merkle.py` implémente un arbre de Merkle binaire classique avec SHA-256.

### 6.1. Construction

```python
class MerkleTree:
    def __init__(self, leaves):
        if len(leaves) == 0:
            raise ValueError(...)
        n = 1
        while n < len(leaves):
            n *= 2
        padded = list(leaves) + [leaves[-1]] * (n - len(leaves))
        self._layers = [padded]
        while len(self._layers[-1]) > 1:
            prev = self._layers[-1]
            nxt = [_hash(prev[2*i], prev[2*i+1]) for i in range(len(prev) // 2)]
            self._layers.append(nxt)
```

**Padding par duplication.** Comme nos domaines de LDE ont une taille qui est une puissance de 2, ce padding ne s'active pas souvent. Quand il s'active, on duplique la dernière feuille pour atteindre la puissance de 2 supérieure. C'est une simplification : un STARK de production utilise un schéma de padding STARK-friendly (multiset hash) ou un padding zéro. Pour un projet pédagogique, la duplication suffit et reste indistinguable tant qu'aucune position de query ne touche la zone paddée.

**Construction bottom-up.** Chaque couche est construite à partir de la précédente. Au final, `self._layers` est une liste `bottom → top`. La racine est `self._layers[-1][0]`.

### 6.2. Authentification

```python
def get_authentication_path(self, index):
    path = []
    idx = index
    for layer in range(len(self._layers) - 1):
        cur = self._layers[layer]
        sib_idx = idx ^ 1
        position = "left" if idx % 2 == 1 else "right"
        path.append((cur[sib_idx], position))
        idx //= 2
    return path
```

Pour remonter de la feuille `index` à la racine, on collecte, à chaque niveau, le **nœud frère** (`sib = idx XOR 1`).

- Si `idx` est pair (donc index pair dans la couche), le frère est à droite : on stocke `("right", hash_droit)` pour ne pas se tromper lors du rehashing.
- Si `idx` est impair, le frère est à gauche.

`idx //= 2` (équivalent à `idx >>= 1`) remonte d'un niveau.

### 6.3. Vérification

```python
@staticmethod
def verify(root, index, leaf, path, domain_size):
    h = leaf
    for sib, position in path:
        if position == "left":
            h = _hash(sib, h)
        elif position == "right":
            h = _hash(h, sib)
    return h == root
```

Rejoue la reconstruction : à chaque niveau, on connaît `h` (le hash courant) et le frère. Selon la position, on hash dans le bon sens. À la fin, on compare à la racine publiée.

L'argument `domain_size` est ignoré dans cette implémentation mais conservé pour la sémantique de production (un vérifieur a besoin de savoir combien de feuilles étaient réellement commises, pour ne pas confondre une preuve authentique avec une preuve forgée par padding).

### 6.4. Pourquoi SHA-256 ?

SHA-256 est :
- **résistant aux collisions** (à hauteur des connaissances actuelles),
- **rapide** même en Python natif (via `hashlib`, l'implémentation est en C),
- **universel** (pas de débat sur sa disponibilité).

Pour la taille de ce projet, pas besoin de Blake2, Keccak ou autre.

---

## 7. Module `utils.py` — Fiat-Shamir et sérialisation

### 7.1. Sérialisation canonique

```python
def field_element_to_bytes(fe: FieldElement) -> bytes:
    return fe.value.to_bytes(32, "big")
```

Chaque FieldElement est sérialisé sur 32 octets big-endian. Cela fixe la taille d'une feuille Merkle (`H(x || y)` ≡ 64 octets d'entrée + 32 octets SHA-256) et permet une désérialisation non-ambiguïe.

### 7.2. `hash_many`

```python
def hash_many(*parts: bytes) -> bytes:
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h.digest()
```

Concatène **explicitement** tous les chunks (la méthode `update` traite les chaînes comme des flux). Utilisé partout où on a besoin d'un hachage sur plusieurs entrées sans ambiguïté de séparateur — par exemple les challenges Fiat-Shamir où le nom du challenge est préfixé (`"STARK-transcript"`).

### 7.3. Échantillonnage de défis Fiat-Shamir

```python
def sample_field_element(seed, prime=DEFAULT_PRIME) -> FieldElement:
    out = int.from_bytes(hashlib.sha256(seed).digest(), "big")
    return FieldElement(out % prime, prime)
```

« Hache la graine, reduce mod p ». Pour `p ≈ 2³¹`, le résultat est essentiellement uniforme modulo un biais négligeable (`2²⁵⁶ mod p < p`).

```python
def sample_distinct_ints(seed, lo, hi_inclusive, count) -> list[int]:
    ...
    seen = set()
    out = []
    cur = seed
    while len(out) < count:
        h = int.from_bytes(hashlib.sha256(cur).digest(), "big")
        cand = lo + (h % span)
        if cand not in seen:
            seen.add(cand); out.append(cand)
        cur = hashlib.sha256(cur).digest()
    return out
```

**Rejection sampling.** On tire des candidats en chaîne (le nouveau `cur` est `H(cur)`) jusqu'à obtenir `count` valeurs distinctes. Pour `count ≪ span`, c'est quasi-immédiat. Pour `count ≈ span`, ça devient lent — non concerné ici (`num_queries = 8`, `span = 128` typiquement).

**Pourquoi distinctes ?** Pour que le vérifieur puisse traiter les queries **indépendamment** (pas de collisions, pas d'ambiguïté d'analyse).

---

## 8. Module `fri.py` — Fast Reed-Solomon IOP of Proximity

`fri.py` est le cœur algorithmique après le STARK lui-même. C'est le composant qui transforme un « engagement polynomial » en une preuve concise que la fonction engagée est proche d'un polynôme de bas degré.

### 8.1. Notations

- `f` : la fonction à prouver « proche d'un bas degré » (ici : `C(x)` sur le LDE).
- `D` : un domaine fini `D ⊂ F_p`, `|D| = n = 2^k`.
- `r` : un défi (Fiat-Shamir).

### 8.2. Le pliage binaire

Soit `n = 2^k`. Pour `D` d'ordre `n`, on a la paire naturelle `(x, −x)` aux indices `(i, i+n/2)`. L'idée est : étant donné `f : D → F_p` et un défi `r`, construire `f_next : D_next → F_p` avec `D_next = {x² : x ∈ D}` (donc `|D_next| = n/2`) et :

$$f_{next}(x^2) = \frac{f(x) + f(-x)}{2} + r \cdot \frac{f(x) - f(-x)}{2x}.$$

Pourquoi cette formule ? Parce que si `f(x) = P(x)` pour un polynôme `P` de degré `< n/2`, alors `P(x) − P(−x)` est un polynôme **impair** divisible par `x`. On peut écrire `P(x) = E(x²) + x · O(x²)` où `E` est pair et `O` impair. Alors :

- `(P(x) + P(−x))/2 = E(x²)`, qui ne dépend que de `x²`.
- `(P(x) − P(−x))/(2x) = O(x²)`, qui ne dépend que de `x²`.

Si `f = P + ε` où `ε` est l'erreur (que l'on veut amplifier), le pliage « en moyenne » préserve le polynôme bas degré et réduit l'erreur par un facteur `1` en espérance. En itérant `log n` fois, on tombe à un polynôme de degré constant qu'on peut envoyer explicitement.

C'est l'argument central de FRI : on montre que si `δ(f, P_d) ≤ δ₀`, alors `δ(f_next, P_{d/2}) ≤ max(δ₀, ρ)` pour une constante `ρ < 1/2`. Plus formellement (Ben-Sasson et al., 2014) : chaque pliage divise asymptotiquement la distance par au moins `ρ`, jusqu'à ce qu'on atteigne le bas degré.

### 8.3. Domaines en `natural order`

```python
def gen_domain(size, prime=DEFAULT_PRIME, shift=3):
    order = size.bit_length() - 1
    g = two_adic_generator(prime, order)
    coset = [FieldElement((shift * pow(g, i, prime)) % prime, prime)
             for i in range(size)]
    return coset, shift, order
```

`g` est un générateur du sous-groupe d'ordre `2^k`. Le domaine retourné est en **natural order** : l'élément à l'index `i` est `shift · g^i`. **Important** : ce n'est **pas** trié ! L'ordre est exactement celui qu'on attend pour FRI : `D[i]` et `D[i + n/2]` sont `(x, −x)`.

### 8.4. Construction couche par couche

```python
def _build_layer(domain, evaluations):
    if len(domain) != len(evaluations): ...
    leaves = [_leaf_hash(x, y) for x, y in zip(domain, evaluations)]
    tree = MerkleTree(leaves)
    return FriLayer(domain=list(domain), evaluations=list(evaluations), root=tree.root())
```

Pour chaque couche, on construit :
- la liste des feuilles `H(x_i || f(x_i))`,
- l'arbre de Merkle,
- la structure `FriLayer` (domaine, évaluations, racine).

La racine est publiée et sert à dériver le prochain défi (Fiat-Shamir).

### 8.5. Pliage effectif

```python
def _fold_layer(domain, evaluations, r):
    n = len(domain)
    half = n // 2
    prime = domain[0].prime
    two_inv = FieldElement(2, prime).inverse()
    next_domain, next_evals = [], []
    for i in range(half):
        x = domain[i]
        fx = evaluations[i]
        fy = evaluations[i + half]
        avg = (fx + fy) * two_inv
        slope = (fx - fy) * (two_inv / x)
        f1 = avg + r * slope
        next_domain.append(x * x)
        next_evals.append(f1)
    return next_domain, next_evals
```

Implémentation **directe** de la formule de pliage. Noter :
- `two_inv` est précalculé (économie d'une exponentiation modulaire par pliage).
- Le nouveau domaine est construit en place : `next_domain[i] = D[i]²`. Comme `D[i] = shift · g^i`, on a `D[i]² = shift² · g^{2i}`, qui est exactement le coset d'ordre `n/2` qu'on attend.

### 8.6. Le polynôme final

Quand `|D| ≤ max_degree_plus_one`, on ne peut plus plier. Au lieu de cela, on interpole (Lagrange) les évaluations restantes pour obtenir les coefficients d'un polynôme `F(x)` de degré `< |D|`. Ces coefficients sont envoyés tels quels.

**Pourquoi ?** Pour `n` petit, c'est plus simple et plus sûr que de continuer à plier. Le vérifieur vérifie deux choses :
- `deg F < max_degree_plus_one`,
- pour chaque query, `F` est bien la continuation du pliage (cf. §8.8).

### 8.7. Le prouveur

```python
def prove_fri(initial_domain, initial_evaluations, max_degree_plus_one=16,
              num_queries=8, initial_shift=3):
    ...
    layers = []
    fold_challenges = []
    cur_domain = initial_domain
    cur_evals = initial_evaluations
    while len(cur_domain) > max_degree_plus_one:
        layer = _build_layer(cur_domain, cur_evals)
        layers.append(layer)
        r = sample_field_element(hash_many(b"FRI-fold", layer.root), prime)
        fold_challenges.append(r)
        cur_domain, cur_evals = _fold_layer(cur_domain, cur_evals, r)

    from .polynomial import interpolate_lagrange
    final_poly = interpolate_lagrange(cur_domain, cur_evals)
    final_poly_commit = hash_many(b"FRI-final", field_elements_to_bytes(*final_poly))

    transcript = hash_many(
        b"FRI-transcript",
        b"".join(L.root for L in layers),
        final_poly_commit,
    )
    raw_indices = sample_distinct_ints(transcript, 0, n0 - 1, num_queries)

    queries = []
    for idx0 in raw_indices:
        q = FriQuery(initial_index=idx0)
        cur_idx = idx0
        for layer in layers:
            n_layer = len(layer.domain)
            half = n_layer // 2
            if cur_idx < half:
                left_i, right_i = cur_idx, cur_idx + half
            else:
                left_i, right_i = cur_idx - half, cur_idx
            ...
            cur_idx = cur_idx % half
        queries.append(q)
    return FriProof(...)
```

**Étapes :**

1. **Boucle de pliage.** Tant que `|D| > max_degree_plus_one` :
   - on construit la couche (Merkle sur `(D[i], f(D[i]))`),
   - on tire `r ← H("FRI-fold" || root)` (Fiat-Shamir),
   - on applique le pliage.

2. **Polynôme final.** On interpole les évaluations résiduelles en coefficients.

3. **Commitment final.** `H("FRI-final" || coeffs)` est engagé.

4. **Transcrit.** `T = H("FRI-transcript" || roots || final_commit)`.

5. **Queries.** On tire `num_queries` positions distinctes via rejection sampling depuis `T`.

6. **Ouvertures.** Pour chaque query `i₀`, on suit la chaîne de pliages :
   - à la couche 0, on a `x = D[i₀]`, on tire `f(x)` et `f(D[i₀ + n/2])` (= `f(−x)`). Auth paths Merkle pour les deux.
   - on calcule `i₁ = i₀ mod (n/2)` : la « position » dans la couche suivante (l'indice dans le nouveau domaine `D_next` qui contient `x²`).
   - à la couche 1, on lit `f_next(x²)` = la valeur de la couche suivante au bon indice.
   - récursion jusqu'à la dernière couche, puis évaluation finale du polynôme final au bon point.

### 8.8. Le vérifieur

```python
def verify_fri(proof, max_degree_plus_one=16):
    ...
    final_poly = strip(proof.final_poly_coeffs)
    if len(final_poly) >= max_degree_plus_one:
        return False

    expected_folds = []
    for root in proof.layer_roots:
        r = sample_field_element(hash_many(b"FRI-fold", root), prime)
        expected_folds.append(r)
    if expected_folds != proof.fold_challenges:
        return False

    final_poly_commit = hash_many(b"FRI-final", field_elements_to_bytes(*final_poly))
    transcript = hash_many(b"FRI-transcript",
                           b"".join(proof.layer_roots), final_poly_commit)
    expected_indices = sample_distinct_ints(transcript, 0, n0 - 1, len(proof.queries))
    if sorted(expected_indices) != sorted(q.initial_index for q in proof.queries):
        return False

    for q in proof.queries:
        for li, opening in enumerate(q.layer_openings):
            ...
            left_point = layer_domain_point(shift, original_order, li, opening.left_index, prime)
            right_point = layer_domain_point(shift, original_order, li, opening.right_index, prime)
            left_leaf = _leaf_hash(left_point, opening.left_value)
            right_leaf = _leaf_hash(right_point, opening.right_value)
            if not MerkleTree.verify(proof.layer_roots[li], opening.left_index, left_leaf,
                                     opening.left_auth_path, n_layer): return False
            if not MerkleTree.verify(proof.layer_roots[li], opening.right_index, right_leaf,
                                     opening.right_auth_path, n_layer): return False

            r = expected_folds[li]
            x = left_point
            two_inv = FieldElement(2, prime).inverse()
            folded = (opening.left_value + opening.right_value) * two_inv + r * (
                (opening.left_value - opening.right_value) * (two_inv / x))

            if li + 1 < len(q.layer_openings):
                nxt = q.layer_openings[li + 1]
                if folded != nxt.left_value and folded != nxt.right_value:
                    return False
                ...
            else:
                final_eval = eval_poly_at(final_poly, x * x)
                if folded != final_eval:
                    return False
    return True
```

**Logique :**

1. **Vérifier le polynôme final.** Sa représentation stripped a degré `< max_degree_plus_one`.

2. **Recalculer les défis de pliage.** À partir des racines publiées, on dérive `r_i = H("FRI-fold" || root_i)`. Ils doivent correspondre à ceux envoyés.

3. **Recalculer le transcrit et les indices de query.** Si le prouveur a triché sur les indices, ils doivent différer.

4. **Pour chaque query, vérifier couche par couche :**
   - Authentifier la feuille gauche et droite sur la couche (Merkle).
   - Recalculer la valeur pliée.
   - Soit on la compare à la valeur suivante fournie par le prouveur (cohérence cross-couche), soit on l'évalue sur le polynôme final (dernière couche).

**Le point subtil :** `left_point = layer_domain_point(shift, original_order, li, opening.left_index, prime)`. Cette fonction calcule le point exact du coset au bon niveau et indice, ce qui permet au vérifieur de rejouer `x ↦ x²` sans connaître le polynôme original.

### 8.9. Complexité et taille

- **Complexité du prouveur** : `O(n log² n)` si on utilise NTT, ou `O(n²)` en Lagrange.
- **Complexité du vérifieur** : `O(log² n)` par query (remerkle + évaluation polynomiale).
- **Taille de la preuve** : `O(log² n)` octets.

---

## 9. Module `stark.py` — la pipeline STARK complète

C'est ici que tout s'assemble. Le module orchestre les composants précédents pour produire une preuve STARK spécifique à l'énoncé Fibonacci.

### 9.1. Le `StarkParams`

```python
@dataclass
class StarkParams:
    c0: int
    c1: int
    N: int
    C: int
    blowup_factor: int = 4
    num_queries: int = 8
    max_degree_plus_one: int = 16
    shift: int = 3
    prime: int = DEFAULT_PRIME
```

L'instance publique que tout le monde partage :
- `c0`, `c1`, `N`, `C` : l'énoncé.
- `blowup_factor` : `|L| / |T|`. Plus il est grand, plus la preuve est lourde mais plus FRI est sound.
- `num_queries` : nombre de positions de query (soundness `2^{-num_queries}`).
- `max_degree_plus_one` : taille finale de FRI (degré final + 1).
- `shift` : décalage du coset LDE.

### 9.2. Génération de la trace

```python
def generate_trace(c0, c1, N, prime=DEFAULT_PRIME):
    out = [FieldElement(c0, prime), FieldElement(c1, prime)]
    for _ in range(N - 1):
        out.append(out[-1] + out[-2])
    return out
```

Calcul direct `O(N)`. Renvoie `[u₀, u₁, …, u_N]`.

### 9.3. Construction du domaine de trace

```python
def build_trace_domain(N, prime=DEFAULT_PRIME, shift=1):
    M = trace_domain_size(N)
    order = M.bit_length() - 1
    g = two_adic_generator(prime, order)
    coset = [FieldElement((shift * pow(g, i, prime)) % prime, prime) for i in range(M)]
    return coset, order, shift
```

`M` est la plus petite puissance de 2 `≥ N + 1`. Le domaine de trace est `<g_trace>` tout court (shift = 1) car on veut que `T(g^i) = u_i` sans translation.

**Pourquoi `M ≥ N + 1` ?** Parce qu'on a `N + 1` valeurs à interpoler ; le théorème d'interpolation de Lagrange exige un degré `< M`, donc `M ≥ N + 1` points.

### 9.4. Le polynôme de trace

```python
trace_domain = [FieldElement(pow(g_trace, i, prime), prime) for i in range(M)]
trace_coeffs = interpolate_lagrange(trace_domain, trace)
```

`T(x)` est **l'unique** polynôme de degré `< M` tel que `T(g_trace^i) = u_i` pour `i ∈ [0, N]`. Pour `i > N`, `T(g_trace^i)` n'a aucune contrainte — il prend la valeur naturelle de l'interpolation.

**Sémantique.** `T(x)` est l'objet que le prouveur engage. Il code toute la suite `u₀, …, u_N` dans un seul polynôme de degré `< M`.

### 9.5. La composition des contraintes

C'est la partie la plus subtile. Le code construit :

$$C(x) = \frac{T(g^2 x) - T(g x) - T(x)}{Z_\text{trans}(x)} + \alpha \cdot \sum_{i \in \{0, 1, N\}} \frac{T(x) - c_i^*}{x - g^i},$$

avec `c₀* = c₀, c₁* = c₁, c_N* = C` et `Z_trans(x) = ∏_{i=0}^{N-2}(x - g^i)`.

**D'où vient cette formule ?**

On veut prouver trois types de contraintes :

1. **Contraintes de transition** : `T(g²x) − T(gx) − T(x) = 0` pour `x ∈ {g⁰, g¹, …, g^{N-2}}` (indices où les trois points sont dans la trace). Formellement, le numérateur `T(g²x) − T(gx) − T(x)` s'annule sur le sous-ensemble `{g⁰, …, g^{N-2}}` du domaine de trace, donc `Z_trans` divise le numérateur.

2. **Contraintes de boundary** : `T(g⁰) = c₀, T(g¹) = c₁, T(g^N) = C`. Le numérateur `T(x) − c_i` s'annule en `g^i`, donc `(x − g^i)` divise.

Pour **combiner linéairement** ces contraintes en un seul polynôme, on multiplie les quotients par un coefficient `α^k` dérivé de l'instruction (pour ne pas fixer trop rigides les challenges Fiat-Shamir dans une version pédagogique).

**Pourquoi diviser par le polynôme d'annulation ?** Pour transformer une affirmation sur des points discrets en une affirmation de bas degré. Si la contrainte n'est pas satisfaite, la division ne tombe pas juste — `T(g²x) − T(gx) − T(x)` n'a pas `Z_trans` comme diviseur, et le quotient contient des zéros fictifs. Mais ce qui compte pour la soundness, c'est :

> **Si toutes les contraintes sont satisfaites, alors `C(x)` est exactement le quotient décrit — un polynôme de degré `≤ N`.**

C'est ce qu'on prouve à FRI.

#### 9.5.1. Détail algorithmique

```python
n = len(trace_coeffs)
trans_coeffs = []
trans2_coeffs = []
g_pow = FieldElement(1, prime); g2_pow = FieldElement(1, prime)
g_factor = FieldElement(g, prime); g2_factor = FieldElement((g * g) % prime, prime)
for _ in range(n):
    trans_coeffs.append(trace_coeffs[_] * g_pow)
    trans2_coeffs.append(trace_coeffs[_] * g2_pow)
    g_pow = g_pow * g_factor
    g2_pow = g2_pow * g2_factor
```

**Astuce algébrique.** Au lieu de construire explicitement les polynômes `T(gx)` et `T(g²x)` (ce qui demanderait de recomposer les coefficients), on les écrit directement :

$$T(g x) = \sum_i c_i (g x)^i = \sum_i (c_i g^i) x^i.$$

Donc les coefficients de `T(gx)` sont `(c_i · g^i)_i`. On les accumule en place avec une multiplication cumulative par `g`. C'est une accélération `O(n)` au lieu de `O(n²)` si on passait par `mul_polys`.

```python
trans_constr = sub_polys(sub_polys(trans2_coeffs, trans_coeffs), trace_coeffs)
z_trans_coeffs = [FieldElement.one(prime)]
for i in range(N - 1):
    g_i = FieldElement(pow(g, i, prime), prime)
    z_trans_coeffs = mul_polys(z_trans_coeffs, [-g_i, FieldElement.one(prime)])

q_trans, r_trans = poly_div(trans_constr, z_trans_coeffs)
if not (len(r_trans) == 1 and r_trans[0].is_zero()):
    raise RuntimeError("transition constraint is not in the vanishing ideal")
```

On construit `Z_trans` puis on divise. Si le reste est non nul, le prouveur sait que **sa propre trace est inconsistante** — assertion de cohérence interne (la récurrence n'a pas été tenue).

**Note :** ce test n'est pas effectué en production (le prouveur est sensé être honnête). Il sert d'assertion de cohérence pendant le développement.

#### 9.5.2. Les quotients de boundary

```python
for i, claimed in [(0, params.c0), (1, params.c1), (N, params.C)]:
    const_poly = [FieldElement(-claimed % prime, prime)] + \
                 [FieldElement.zero(prime) for _ in range(len(trace_coeffs) - 1)]
    numerator = add_polys(trace_coeffs, const_poly)
    denom = [-FieldElement(pow(g, i, prime), prime), FieldElement.one(prime)]
    q_b, r_b = poly_div(numerator, denom)
    ...
    boundary_coeffs = add_polys(boundary_coeffs, q_b)
```

Pour chaque claim `c_i`, on calcule `(T(x) − c_i)/(x − g^i)`. Comme `T(g^i) = c_i`, la division tombe juste (reste nul).

#### 9.5.3. Définition de `α`

```python
alpha = sample_field_element(
    hash_many(b"STARK-alpha",
              str((params.c0, params.c1, params.N, params.C)).encode()),
    prime,
)
```

`α` est dérivé du `STARK-alpha` et de l'instruction publique `(c₀, c₁, N, C)`. C'est **déterministe** : le prouveur et le vérifieur calculent exactement la même valeur. Pour une implémentation stricte, `α` devrait sortir du transcrit Fiat-Shamir — c'est noté comme limitation dans `README.md`.

#### 9.5.4. Assemblage final

```python
max_deg = max(len(q_trans), len(boundary_coeffs))
q_trans_a = q_trans + [FieldElement.zero(prime)] * (max_deg - len(q_trans))
boundary_a = boundary_coeffs + [FieldElement.zero(prime)] * (max_deg - len(boundary_coeffs))
composition = add_polys(q_trans_a, scalar_mul(boundary_a, alpha))
return strip(composition)
```

On aligne les degrés (padding par zéros à droite) et on somme `q_trans + α · boundary_coeffs`.

**Degré de `C`.** Borné par `N` (typiquement `N = 31`), soit `deg(C) < 32`. C'est très bas degré par rapport à `|L| = 128`, ce qui rend FRI très sound avec peu de queries.

### 9.6. Le LDE

```python
lde_size = params.blowup_factor * M
g_lde = two_adic_generator(prime, lde_order)
lde_domain = [FieldElement((lde_shift * pow(g_lde, i, prime)) % prime, prime)
              for i in range(lde_size)]
trace_lde = [eval_poly_at(trace_coeffs, x) for x in lde_domain]
comp_lde = [eval_poly_at(comp_coeffs, x) for x in lde_domain]
```

On construit le **coset LDE** : un décalage `shift` du sous-groupe de taille `blowup · M`. On évalue `T` et `C` sur ce coset.

**Pourquoi `blowup · M` plutôt que `M` ?** Le LDE sert à introduire de la **redondance**. Si le prouveur s'engage uniquement sur les points de trace, il peut tricher en prétendant que la trace est plus « simple » qu'elle ne l'est. En évaluant sur un sur-ensemble, on réduit la capacité du prouveur à tricher : pour une fonction quelconque, la proportion de points qui coïncident avec un polynôme de degré `< M` est typiquement `M / (blowup · M) = 1/blowup`. Plus `blowup` est grand, plus la capacité de tricher est faible.

**Formellement.** Le **`distance parameter` est `1 − 1/blowup`**. FRI prouve que `δ(f, P_{<M}) ≤ 1 − 1/blowup`. Plus `blowup` est grand, plus la borne est stricte, donc plus la soundness de l'ensemble est élevée.

### 9.7. Les engagements Merkle

```python
trace_leaves = [hash_many(field_elements_to_bytes(x, y))
                for x, y in zip(lde_domain, trace_lde)]
comp_leaves = [hash_many(field_elements_to_bytes(x, y))
               for x, y in zip(lde_domain, comp_lde)]
trace_tree = MerkleTree(trace_leaves)
comp_tree = MerkleTree(comp_leaves)
```

Chaque feuille est `H(x_i || y_i)` où `(x_i, y_i)` est un point du LDE. La racine est un engagement **liant** sur la fonction entière.

### 9.8. FRI sur la composition

```python
fri_proof = prove_fri(lde_domain, comp_lde,
                       max_degree_plus_one=params.max_degree_plus_one,
                       num_queries=params.num_queries,
                       initial_shift=lde_shift)
```

On applique FRI sur les évaluations de `C` sur le LDE. Le `max_degree_plus_one` est la borne supérieure sur le degré de `C`. Pour notre config, `C` a degré `< N = 31 < 32 = max_degree_plus_one`, donc FRI doit terminer en 3-4 couches.

### 9.9. Le transcrit et les queries

```python
transcript = hash_many(
    b"STARK-transcript",
    trace_tree.root(),
    comp_tree.root(),
    b"".join(fri_proof.layer_roots),
    field_elements_to_bytes(*fri_proof.final_poly_coeffs),
)
raw_indices = sample_distinct_ints(transcript, 0, lde_size - 1, params.num_queries)
```

**Transcrit global.** Tous les engagements (« commitments ») sont mixés :
- `trace_root` : engagement sur `T`.
- `comp_root` : engagement sur `C`.
- Toutes les `fri_layer_roots`.
- Le polynôme final FRI (ses coefficients).

Ce transcrit **engage** toutes les valeurs aléatoires (et donc toutes les queries) sur la totalité du protocole. Sans cela, un prouveur malhonnête pourrait voir les queries d'abord et produire des engagements compatibles.

#### 9.9.1. Construction des queries

```python
for idx in raw_indices:
    gx_idx = (idx + params.blowup_factor) % lde_size
    g2x_idx = (idx + 2 * params.blowup_factor) % lde_size
    queries.append(StarkQuery(
        initial_index=idx,
        trace_x_index=idx,
        trace_x_value=trace_lde[idx],
        trace_x_auth_path=trace_tree.get_authentication_path(idx),
        trace_gx_index=gx_idx,
        trace_gx_value=trace_lde[gx_idx],
        trace_gx_auth_path=trace_tree.get_authentication_path(gx_idx),
        trace_g2x_index=g2x_idx,
        trace_g2x_value=trace_lde[g2x_idx],
        trace_g2x_auth_path=trace_tree.get_authentication_path(g2x_idx),
        ...
    ))
```

**Trois lectures par query :** `T(x), T(gx), T(g²x)`. Pourquoi ? Parce que la **contrainte de transition** nécessite les trois valeurs simultanément pour vérifier `(T(g²x) − T(gx) − T(x)) / Z_trans(x)`.

L'index `gx_idx = idx + blowup_factor` provient d'une arithmétique modulo `lde_size`. Cette astuce utilise le fait que `g_lde = g_trace^blowup_factor` au sein du sous-groupe LDE — c'est une heureuse coïncidence due à l'ordre `blowup · M` du LDE contre l'ordre `M` du sous-groupe de trace.

### 9.10. Le vérifieur STARK

#### 9.10.1. Reconstruction du LDE

```python
g_lde = two_adic_generator(prime, lde_order)
lde_domain = [FieldElement((lde_shift * pow(g_lde, i, prime)) % prime, prime)
              for i in range(lde_size)]
```

**Le vérifieur reconstruit le domaine** à partir des paramètres publics (le shift est tiré de `proof.fri_proof.initial_domain_shift`). C'est exactement la même construction que le prouveur, donc déterministe.

#### 9.10.2. Vérification FRI

```python
if not verify_fri(proof.fri_proof, max_degree_plus_one=params.max_degree_plus_one):
    return False
```

Le vérifieur délègue à `verify_fri` la tâche de vérifier que `C` est bas degré.

#### 9.10.3. Recalcul du transcrit et des queries

```python
transcript = hash_many(b"STARK-transcript", proof.trace_root, proof.comp_root,
                       b"".join(proof.fri_proof.layer_roots),
                       field_elements_to_bytes(*proof.fri_proof.final_poly_coeffs))
expected_indices = sample_distinct_ints(transcript, 0, lde_size - 1, len(proof.queries))
if sorted(expected_indices) != sorted(q.initial_index for q in proof.queries):
    return False
```

Si les queries que le prouveur a envoyés ne correspondent pas au transcrit recalculé, on rejette.

#### 9.10.4. Vérification par query

```python
for q in proof.queries:
    x = lde_domain[q.initial_index]
    gx = lde_domain[q.trace_gx_index]
    g2x = lde_domain[q.trace_g2x_index]
    ...
    for pt, pt_idx, pt_val, pt_path in [
        (x, q.trace_x_index, q.trace_x_value, q.trace_x_auth_path),
        (gx, q.trace_gx_index, q.trace_gx_value, q.trace_gx_auth_path),
        (g2x, q.trace_g2x_index, q.trace_g2x_value, q.trace_g2x_auth_path),
    ]:
        leaf = hash_many(field_elements_to_bytes(pt, pt_val))
        if not MerkleTree.verify(proof.trace_root, pt_idx, leaf, pt_path, lde_size):
            return False

    comp_leaf = hash_many(field_elements_to_bytes(x, q.comp_value))
    if not MerkleTree.verify(proof.comp_root, q.comp_index, comp_leaf, q.comp_auth_path, lde_size):
        return False

    recomputed = recompute_composition(
        trace_x=q.trace_x_value,
        trace_gx=q.trace_gx_value,
        trace_g2x=q.trace_g2x_value,
        x=x,
        params=params,
    )
    if recomputed != q.comp_value:
        return False
```

**Trois auth paths sur la trace** — une par valeur engagée. **Un auth path sur la composition** — pour `C(x)`. Puis **recompute + compare** : on vérifie que la composition `C(x)`, telle qu'engagée, correspond exactement à la formule attendue compte tenu des valeurs de trace engagées.

#### 9.10.5. `recompute_composition`

C'est la **même formule** que `compose_constraints`, mais sans division polynomiale (on évalue juste le numérateur au point `x` et on divise par `Z_trans(x)`). Les **terms de boundary** sont évalués de la même manière, en zéros quand `x = g^i` (un edge case).

**Point subtil :** si `x = g^i` pour un `i ∈ {0, 1, N}`, le boundary term correspondant est nul (contrainte déjà satisfaite par construction). Pareil pour les `i ∈ {0, …, N-2}` côté transition : si `x` est un des points où la transition est censée tenir, alors `Z_trans(x) = 0` et le term transition est « infini » — mais comme la contrainte est satisfaite, la valeur **dans le quotient** est précisément ce que l'interpolation fournirait. En pratique, le code skippe le term transition dès que `Z_trans(x) = 0`.

---

## 10. Module `main.py` — démonstration end-to-end

`main.py` est purement démonstratif. Il :

1. génère la trace Fibonacci pour `(c₀=1, c₁=2, N=31)`,
2. calcule `C = u_N`,
3. construit un `StarkParams` avec les paramètres par défaut,
4. appelle `prove_stark` (chronométré),
5. appelle `verify_stark` (chronométré),
6. imprime les timings,
7. **teste trois falsifications** :
   - modifier `C` → doit rejeter,
   - modifier `c₀` → doit rejeter,
   - modifier `N` → doit rejeter.

La sortie typique (`uv run stark-fibonacci`) :

```
Honest proof:
  prover time : 0.107 s
  verifier OK : True
  verifier t  : 0.004 s

Tampering tests (each should be rejected):
      wrong C: REJECTED
     wrong c0: REJECTED
      wrong N: REJECTED
```

**Ratio prouveur/vérifieur.** Le prouveur est ~25× plus lent que le vérifieur. C'est attendu : le prouveur fait de l'interpolation et plein de multiplications modulaires ; le vérifieur fait surtout des hachages et quelques divisions. Pour un STARK de production, ce ratio explose à `1000×` ou plus.

---

## 11. Le prouveur pas-à-pas

Résumons la chronologie du prouveur avec un regard mathématique :

```
Entrée publique: (c₀, c₁, N, C)

1. WITNESS
   Calcul de u₀, …, u_N par récurrence.  [O(N)]

2. TRACE POLYNOMIAL
   T(x) = Lagr(famille {(g^i, u_i)}_{0≤i≤N})  avec M = 2^k ≥ N+1.  [O(M²)]
   T(g^i) = u_i pour 0 ≤ i ≤ N ;  T(g^i) libre pour i > N.

3. COMPOSITION POLYNOMIAL
   C(x) = (T(g²x) − T(gx) − T(x)) / Z_trans(x)           // transition
        + α · ((T(x)−c₀)/(x−g⁰) + (T(x)−c₁)/(x−g¹) + (T(x)−C)/(x−g^N))  // boundary
   où  Z_trans(x) = ∏_{i=0}^{N−2}(x − g^i)
   et  α = SHA256("STARK-alpha" || (c₀,c₁,N,C)).  [O(N²) pour les divisions]

   Note : Si la trace est honnête, deg(C) ≤ N.

4. LDE DOMAIN
   L = shift · <g_{lde}>  avec |L| = blowup · M.
   Trace evals: t_i = T(L[i])  pour 0 ≤ i < blowup·M.  [O(blowup · M²) en Lagrange]
   Comp evals:  c_i = C(L[i]).
   (En production on utiliserait NTT.)

5. MERKLE COMMITMENTS
   F_trace = SHA256(L[i] || t_i)  sur i
   F_comp  = SHA256(L[i] || c_i)  sur i
   root_T = Merkle(F_trace);  root_C = Merkle(F_comp).

6. FRI SUR LA COMPOSITION
   fold r_i ← H("FRI-fold" || root_i)
   appliquer pliage binaire jusqu'à |D| ≤ max_degree_plus_one
   interpréter en F(x), publier les racines + coefficients.

7. TRANSCRIPT
   T = SHA256("STARK-transcript" || root_T || root_C || fri_roots || F_coeffs)
   indices = sample_distinct(T, 0, |L|−1, num_queries).

8. QUERIES
   Pour chaque idx:
     ship  T(L[idx]), T(L[idx+b]), T(L[idx+2b]) + 3 auth paths sur root_T
     ship  C(L[idx]) + auth path sur root_C
     ship  ouverture FRI complète.

Output : StarkProof
```

**Coût total.** Dominé par l'interpolation (étapes 2, 3, 4) : `O(M² + N² + blowup · M²)` ≈ `O(blowup · M²)` en Lagrange.

---

## 12. Le vérifieur pas-à-pas

```
Entrée publique: (c₀, c₁, N, C)
Entrée privée: StarkProof

1. RECONSTRUIRE LE LDE DOMAIN depuis les params publics.  [O(blowup · M)]

2. VÉRIFIER FRI:  verify_fri(proof.fri_proof, max_degree_plus_one).
   Si False → rejeter.

3. RECALCULER LE TRANSCRIPT et les indices de query. Comparer.
   Si mismatch → rejeter.

4. POUR CHAQUE QUERY:
   (a) Vérifier 3 auth paths Merkle sur root_T pour T(x), T(gx), T(g²x).
       Une seule erreur → rejeter.
   (b) Vérifier 1 auth path Merkle sur root_C pour C(x).
   (c) Recalculer C(x) à partir de T(x), T(gx), T(g²x) (et x).
       Comparer à C(x) commise.
       Si différent → rejeter.

5. Toutes les queries passées → ACCEPT.
```

**Coût total.** Dominé par les vérifications Merkle : `O(num_queries · log|L|)` hachages. Pour `num_queries = 8` et `|L| = 128`, c'est ~56 hachages, soit quelques millisecondes.

---

## 13. Pourquoi ça marche : soundness et sécurité

### 13.1. Les deux sources de soundness

Un STARK garantit **deux choses simultanément** :

1. **Soundness (complétude ↔ sécurité) :** un prouveur malhonnête qui produit une preuve acceptée mais pour un énoncé faux est **exponentiellement improbable** (en `num_queries`, et en `2^{-λ}` plus généralement).

2. **Connaissance zéro (ZK) :** la preuve ne révèle rien de la trace au-delà de l'énoncé public. (Ici on **n'implémente pas** le ZK — c'est volontaire, voir §15.)

### 13.2. Sketch de l'argument de soundness

Supposons qu'un prouveur malhonnête `P*` tente de prouver un énoncé `(c₀, c₁, N, C)` **faux** pour une trace `u₀, …, u_N` qui ne satisfait pas `u_N = C`. Pour être accepté, `P*` doit :

1. **Produire un polynôme de composition `C*` accepté par FRI.** Par la **soundness de FRI** (Ben-Sasson et al., 2014), la probabilité que `C*` soit proche d'un polynôme de degré `< N` alors qu'il ne l'est pas est `≤ 2^{-num_queries}` (modulo les détails techniques de `ρ`-list-decoding).

2. **Pour chaque query, fournir des valeurs `(T*_x, T*_{gx}, T*_{g²x}, C*_x)` cohérentes** avec ses engagements Merkle et la formule de composition. Si la contrainte de transition n'est pas satisfaite à `x` (c.-à-d. `T*_{g²x} − T*_{gx} − T*_x ≠ 0`), alors `C*_x` ne peut pas être cohérent avec la valeur engagée — le vérifieur rejette.

3. **Pour les 3 points de boundary `g^0, g^1, g^N`, les claims `c₀, c₁, C` doivent correspondre** à `T*`. Comme la trace ne satisfait pas l'énoncé, au moins une de ces claims est incorrecte — mais le prouveur peut s'arranger pour ne pas sélectionner ces indices dans ses queries. La **probabilité qu'aucune query ne touche `{g^0, g^1, g^N}`** est `≈ (1 − 3/|L|)^{num_queries}`. Pour `num_queries = 8` et `|L| = 128`, c'est `≈ 0.83`. Donc un prouveur malhonnête a **17% de chance** de tomber sur au moins un point de boundary — et, ce faisant, d'être détecté.

4. **La soundness globale** combine ces effets : `soundness_error ≤ max(2^{-num_queries}, (3/|L|)^{num_queries})`. Pour les paramètres typiques, c'est dominé par `2^{-num_queries}`.

### 13.3. Robustesse de chaque composant

| Composant | Hypothèse cryptographique | Attaque |
|-----------|---------------------------|---------|
| SHA-256 (engagements) | résistance aux collisions de second-preimage | forge une feuille alternative avec même root |
| Fiat-Shamir | modèle de l'oracle aléatoire | prédire les challenges pour tricher |
| FRI | `ρ`-list-decoding bound | prouveur triche sur la distance de Reed-Solomon |

**En pratique**, dans les paramètres choisis :
- `num_queries = 8` donne une soundness `< 2^{-8} = 1/256`. Pour une soundness à `2^{-128}` il faudrait `num_queries ≈ 128`, ou un `blowup_factor` plus grand couplé à des résultats théoriques plus fins.

---

## 14. Coûts asymptotiques et taille de preuve

### 14.1. Le prouveur

| Étape | Coût en Lagrange | Coût en NTT |
|-------|-------------------|-------------|
| Trace | `O(N)` | idem |
| Interpolation trace | `O(M²)` | `O(M log M)` |
| Composition | `O(N²)` | idem |
| LDE trace | `O(|L| · M)` | `O(|L|)` |
| LDE comp | `O(|L| · N)` | `O(|L|)` |
| FRI | `O(|L| · log|L|)` | `O(|L|)` |
| Merkles | `O(|L|)` | idem |
| **Total** | `O(|L|²)` ≈ `O(M² · blowup²)` | `O(|L| log|L|)` ≈ `O(blowup · M log M)` |

L'implémentation actuelle est en Lagrange. Pour passer à l'échelle (≥ 1 000 000 de termes), il faudra **switcher sur NTT**.

### 14.2. Le vérifieur

| Étape | Coût |
|-------|------|
| Construction LDE | `O(|L|)` |
| Merkle (3 + 1 auth paths de longueur `log|L|`) | `O(num_queries · log|L|)` |
| Recompose | `O(num_queries · N)` |
| FRI | `O(num_queries · log²|L|)` |
| **Total** | `O(num_queries · log²|L|)` |

Pour `num_queries = 8`, `|L| = 128` : environ **200 hachages + 8 evaluations polynomiales**, soit quelques millisecondes.

### 14.3. Taille de la preuve

| Composant | Taille |
|-----------|--------|
| `trace_root`, `comp_root` | 64 octets |
| FRI : `log²|L|` racines (32 octets chacune) | ~256 octets |
| FRI : `log|L|` challenges | ~96 octets |
| FRI : `max_degree_plus_one` coefficients (chacun ~32 octets) | ~512 octets |
| Queries : `num_queries × (3 T-values + 1 C-value + auths)` | ~9 ko |
| **Total** | **~10 ko** |

C'est énorme par requête de query : chaque query coûte ~1 ko. C'est dominé par les auth paths. Un STARK de production utilise des engagements sur des Merkle «巨型 » (de hauteur `> 30`) pour comprimer cette taille.

---

## 15. Limitations et pistes d'évolution

### 15.1. Les limitations Actuelles

| Limitation | Pourquoi | Comment améliorer |
|-----------|----------|-------------------|
| Pas de NTT | Simple, lisible | Ajouter `pyfftw` ou un backend NTT maison |
| Pas de ZK | La trace est révélée dans les queries | Multiplier les commitments par un polynôme aléatoire d'« aveuglement » ; ou utiliser les constructions basées sur DEEP-ALI |
| `α` dérivé du public | Non-Fiat-Shamir strict | Inclure `α` dans le transcrit Fiat-Shamir global |
| Padding Merkle naïf | Vulnérable à des attaques subtiles | Padding zéro ou `MerkleMountainRange`/`MerkleSparseTree` |
| Petites tailles | N trop petit pour stress-test | Augmenter `blowup_factor` à 8 ou 16 |
| `max_degree_plus_one = 16` | Trop petit | Le rendre dépendant de `N` |
| Calcul arithmétique naïf | `FieldElement` en pur Python | Stocker en `int` natifs, vectoriser NumPy |

### 15.2. Pistes pour aller plus loin

1. **STARK complet (avec ZK)** — la première étape consiste à « cacher » la trace dans un engagement masqué. La technique classique est le `DEEP-ALI` (Ben-Sasson et al., 2018) ou l'utilisation de polynômes d'aléatorisation.

2. **NTT** — passage à `ntt_poly = NTT(coeffs)`, puis évaluation en `O(n)` via `O(n log n)` au total.

3. **Symboles finis plus grands (`p ≈ 2⁶⁴`)** — nécessaire pour des traces vraiment massives. Le `Goldilocks prime` `p = 2⁶⁴ − 2³² + 1` est un bon choix ; Plonky3 l'utilise.

4. **FRI multi-cosets** — pour augmenter la soundness sans grossir la preuve.

5. **Preuves avec des claims multiples** — permettre au prouveur de prouver plusieurs claims en parallèle, en partageant les engagements.

---

## Annexe : correspondance code ↔ math

Pour naviguer rapidement, voici une table de référence :

| Symbole math | Fichier | Ligne / fonction |
|--------------|---------|------------------|
| `p = 3·2³⁰+1` | `field.py` | `DEFAULT_PRIME` |
| `g` (2-Sylow) | `field.py` | `two_adic_generator` |
| `F_p` | `field.py` | `class FieldElement` |
| `T(x)` | `stark.py` | `prove_stark` (`interpolate_lagrange`) |
| `C(x)` | `stark.py` | `compose_constraints` |
| `α` | `stark.py` | dans `compose_constraints` et `recompute_composition` |
| `Z_trans(x)` | `stark.py` | `compose_constraints` (boucle `for i in range(N - 1)`) |
| LDE `L` | `stark.py` | `lde_domain` |
| FRI folding | `fri.py` | `_fold_layer` |
| Merkle | `merkle.py` | `class MerkleTree` |
| Fiat-Shamir | `utils.py` | `sample_field_element`, `sample_distinct_ints` |
| Transcrit | `stark.py`/`fri.py` | `hash_many(b"STARK-transcript", ...)` |

---

## Crédits et références

- [Anatomy of a STARK](https://aszepieniec.github.io/stark-anatomy/) — aszepieniec. _Le tutoriel dont ce code s'inspire structurellement._
- [STARK 101](https://starkware.co/stark-101/) — StarkWare. _Tutoriel Python qui prouve précisément Fibonacci._
- *Ben-Sasson, Bentov, Horesh, Riabzev* — _Scalable, transparent, and post-quantum secure computational integrity_ (2018).
- Sujet original : Clément Walter (Zama), Mines Paris.

— *fin du document*
