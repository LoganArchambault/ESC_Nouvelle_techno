# Lecture des preuves réelles

Exécutions réalisées par l’assistant le 26 octobre 2026 sous CPython 3.13.16 (Linux). À reproduire et expliquer sur votre poste.

| Politique | Mains demandées | Mains réglées | Décisions acceptées | Fin | Dossier |
|---|---:|---:|---:|---|---|
| fixed17 | 5 | 5 | 5 | truncated/hand_limit | 20261026T182202-14166ff8 |
| aleatoire | 1 | 1 | 3 | truncated/hand_limit | 20261026T182202-3bc4cf7e |
| fixed17 | 1 | 1 | 1 | truncated/hand_limit | 20261026T182202-e1a2e8d5 |
| aleatoire | 5 | 5 | 5 | truncated/hand_limit | 20261026T182249-fff1ee0c |

Toutes les séances utilisent les bornes temps 60 s, inactivité 30 s, rétention 60 s. Chaque essai a créé une nouvelle séance. Les séances à cinq mains contiennent cinq distributions dans la même séance.

## Première attribution réelle

Trace : `preuves/20261026T182202-3bc4cf7e/trace.jsonl`

Séance : `7c39d174ddb64df1b7e011685cd4dade`. Main : `d9eb1702a47e48e6af585aeed9c8b141`.

Résultat : **loss**, raison `lower_total`, gain externe -50 crédits. Retour interne choisi : **-1**.

Trajectoire, dans l’ordre :
1. État (12, 10), action `hit`, révision 1 → 2.
2. État (13, 10), action `hit`, révision 2 → 3.
3. État (18, 10), action `hold`, révision 3 → 4.

| Couple état–action | Occurrences | N avant | S avant | Q avant | N après | S après | Q après |
|---|---:|---:|---:|---:|---:|---:|---:|
| (12, 10), hit | 1 | 0 | 0 | 0 | 1 | -1 | -1.0 |
| (13, 10), hit | 1 | 0 | 0 | 0 | 1 | -1 | -1.0 |
| (18, 10), hold | 1 | 0 | 0 | 0 | 1 | -1 | -1.0 |

Calcul manuel pour (12, 10), hit : N = 0 + 1 = 1; S = 0 + 1 × (-1) = -1; Q = -1 / 1 = -1.0.

Le retour vient du résultat final, pas d’une récompense intermédiaire. La table est conservée pour la séance aléatoire suivante. Un naturel observé dans les passages n’ajoute aucune visite.

## Vérifications ciblées

11 tests du joueur et 29 tests officiels réussis; sorties dans `preuves/tests.txt`. La frontière 16/17 est vérifiée par test explicite, indépendamment des totaux rencontrés au hasard. Les tests simulés ne remplacent pas les traces réelles ci-dessus.

Exercice de moyenne du cours : 2, 4, 3 donnent N=3, S=9, moyenne=3; après 5, N=4, S=14, moyenne=3,5. Aucun programme supplémentaire n’est nécessaire pour cet exercice.
