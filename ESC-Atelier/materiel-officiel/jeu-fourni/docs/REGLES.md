# Comprendre les mains et les séances

Le jeu utilise des unités fictives. Une **main** se termine par une victoire, un nul ou une défaite. Une **séance** contient plusieurs mains et commence avec une réserve de 1 000. Son objectif est d'atteindre au moins 2 000; une réserve inférieure à 50 constitue la ruine.

## 1. Distribuer et prendre une décision

Le paquet comporte 52 cartes distinctes, sans remise. L'ordre de distribution est : première carte du joueur, carte visible du croupier, deuxième carte du joueur, carte cachée du croupier. La mise fixe de 50 est débitée une seule fois.

Les figures valent 10. Un as vaut 1 ou 11 : le moteur choisit le meilleur total sans dépasser 21 lorsque cela est possible. `player_usable_ace` indique qu'un as vaut actuellement 11. Par exemple, as–as vaut 12; as–6 vaut 17; as–6–10 vaut 17 avec les as à 1.

Deux actions sont possibles pendant une décision :

- `hit` ajoute une carte au joueur. Au-dessus de 21, la main est perdue. À exactement 21, le moteur résout automatiquement la main.
- `hold` termine les tirages du joueur et fait jouer le croupier.

Le croupier tire sous 17 et reste sur tout 17, même avec un as valant 11. Il continue sous 17 même s'il dépasse déjà le total du joueur. Après un dépassement du joueur, aucun tirage supplémentaire du croupier n'est effectué.

## 2. Résoudre et créditer la réserve

Un naturel est un total de 21 obtenu avec les deux cartes initiales. Il est résolu immédiatement, sans décision : deux naturels font nul; un seul naturel gagne. Un 21 obtenu par tirage ne devient pas un naturel.

Sinon, le dépassement du joueur fait perdre; celui du croupier fait gagner. Sans dépassement, le total le plus élevé gagne et les totaux égaux font nul. À toute fin normale, les cartes distribuées du croupier sont révélées, même après le dépassement du joueur.

| Résultat | Crédit après le débit de 50 | Gain net | Réserve finale si la réserve initiale était 1 000 |
| --- | --- | --- | --- |
| Victoire, y compris un naturel | 100 | +50 | 1 050 |
| Nul | 50 | 0 | 1 000 |
| Défaite | 0 | −50 | 950 |

Le moteur fournit ces faits de jeu. Il ne les transforme pas en récompenses d'apprentissage. Le choix des valeurs et de leur attribution appartient au travail d'agent.

Le résultat reste associé à son `hand_id`. Une nouvelle main nécessite toujours une commande `start_hand`; aucune distribution ne suit automatiquement un règlement.

## 3. Renouveler le paquet

Un paquet neuf est mélangé avant la première main. Ensuite, il est renouvelé avant une main seulement s'il reste moins de 18 cartes. À exactement 18, il est conservé. Il n'est jamais renouvelé pendant une main.

Le changement de `shoe_id` indique le renouvellement. `shoe_reset` vaut vrai dans la réponse de la commande qui a créé le paquet; une lecture ne crée pas un nouveau renouvellement. Les événements visibles permettent de suivre uniquement les cartes réellement révélées. La mémoire facultative des cartes doit dédupliquer leurs `event_id` et se vider lorsque `shoe_id` change.

## 4. Distinguer une fin de jeu d'une interruption

Après règlement, l'objectif et la ruine priment sur la borne de mains. Sinon, cette borne termine la séance avec `truncated` et `hand_limit`. Les bornes effectives figurent dans `limits` dès la création.

Une limite de temps donne `truncated/time_limit`; une expiration d'inactivité donne `expired/idle_timeout`; une fermeture explicite donne `interrupted/explicit_close`. Ces états ne sont pas des défaites. En cas de main inachevée, `result` reste nul, `bet_pending` reste à 50 et `bankroll_before_hand` conserve la réserve avant son débit. La réserve disponible provisoire ne doit pas être interprétée comme une ruine.

Une perte de connexion seule ne clôt pas la séance. Une reprise avant expiration retrouve l'état exact. Après expiration, la main inachevée n'est ni réglée ni ajoutée au compteur des mains terminées. La carte cachée n'est pas révélée par une interruption.
