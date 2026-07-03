# PROJECT.md — STARK Fibonacci

## Description du projet

Dans ce projet, nous avons travaillé sur la construction d’un mini-système STARK appliqué à la suite de Fibonacci. L’objectif n’était pas seulement d’obtenir une implémentation fonctionnelle, mais surtout de comprendre les fondements mathématiques nécessaires pour pouvoir ensuite analyser, guider et vérifier l’implémentation produite avec l’aide de l’IA.

Notre travail s’est donc concentré en priorité sur la compréhension des notions théoriques : corps finis, trace d’exécution, contraintes polynomiales, interpolation, engagements de Merkle et protocole FRI. Le cas de Fibonacci nous a permis d’étudier ces concepts sur un exemple simple, mais représentatif de la logique générale d’un STARK.

## Notre démarche

Nous avons d’abord cherché à comprendre comment une récurrence comme celle de Fibonacci peut être transformée en contraintes algébriques vérifiables. Cette étape était essentielle pour ne pas utiliser l’IA comme une boîte noire. Avant de demander ou d’accepter une implémentation, nous voulions comprendre ce que chaque partie du code devait représenter mathématiquement.

Nous avons ensuite étudié progressivement les différentes briques du protocole : le calcul dans un corps fini, la construction de la trace, l’interpolation polynomiale, puis le rôle du vérifieur et du protocole FRI dans le test de bas degré.

Un début d’implémentation à la main est également disponible. Coder par Théo.

## Choix techniques

Nous avons choisi Python pour garder une implémentation lisible et pédagogique. Le projet est organisé avec `uv` et une structure modulaire afin de séparer clairement les différentes parties : corps fini, polynômes, trace, contraintes, Merkle, FRI, preuve et vérification.

Ce choix nous a permis de relier chaque fichier à une notion mathématique précise, ce qui rend le projet plus facile à comprendre, à tester et à améliorer.

## Difficultés rencontrées

La principale difficulté a été de passer d’une vision algorithmique de Fibonacci à une vision algébrique. Il fallait comprendre comment une suite de valeurs peut devenir une trace d’exécution, puis comment cette trace peut être représentée par des polynômes et vérifiée probabilistiquement.

Le protocole FRI a aussi été une partie complexe, car il demande de comprendre à la fois l’idée mathématique du pliage et son rôle dans la vérification d’un polynôme de bas degré.

## Ce que nous avons appris

Ce projet nous a surtout permis de mieux comprendre la logique interne d’un STARK. Nous avons appris qu’un prouveur ne se contente pas de fournir un résultat : il fournit une trace et des engagements permettant au vérifieur de contrôler, avec peu d’informations, que le calcul respecte bien les contraintes attendues.

Nous avons aussi compris l’importance de maîtriser les bases mathématiques avant de s’appuyer sur l’IA pour coder. L’IA peut aider à accélérer l’implémentation, mais elle doit être guidée par une compréhension précise du protocole.

## Améliorations possibles

Avec plus de temps, nous aurions approfondi l’implémentation à la main, renforcé les tests, mieux formalisé les paramètres de sécurité et rendu le système plus générique afin de pouvoir l’appliquer à d’autres calculs que Fibonacci.

Ce projet constitue donc une première étape : il nous a permis de construire une base mathématique solide et de commencer à relier cette compréhension à une implémentation concrète d’un protocole STARK.
