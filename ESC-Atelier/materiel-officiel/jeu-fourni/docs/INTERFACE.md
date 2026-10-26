# Lire une observation et reprendre une commande

Les deux clients appliquent `esc-api-v1` et les règles `esc-blackjack-a26-v1`. Le moteur est la source des règles; le transport ne choisit aucune action. Les identifiants sont opaques.

## 1. Appeler les cinq opérations

| Méthode commune | Route distante | Résultat |
| --- | --- | --- |
| `create_session(config_ref, model_ref, request_id)` | `POST /api/v1/sessions` | Réserve 1 000, état `ready`, révision 0; HTTP 201. |
| `observe(session_id)` | `GET /api/v1/sessions/{id}` | Observation courante; HTTP 200. |
| `start_hand(session_id, expected_revision, request_id)` | `POST /api/v1/sessions/{id}/hands` | Distribution explicite, parfois règlement immédiat; HTTP 200. |
| `act(session_id, action, expected_revision, request_id)` | `POST /api/v1/sessions/{id}/actions` | `hit` ou `hold` en décision; HTTP 200. |
| `close_session(session_id, expected_revision, request_id)` | `POST /api/v1/sessions/{id}/close` | Interruption confirmée, ou observation finale déjà obtenue; HTTP 200. |

Les clients ajoutent `protocol_version` aux commandes JSON. Les noms `config_ref` et `model_ref` sont des références déclaratives de 1 à 128 caractères; ils ne modifient pas les règles ou les bornes du serveur. Un `request_id` contient de 1 à 128 lettres ASCII, chiffres, tirets ou soulignements. Il est unique parmi toutes les mutations de l'identité, y compris la création. Chaque révision attendue est un entier positif ou nul; les booléens et chaînes numériques sont refusés.

Champs inconnus, actions autres que `hit`/`hold`, montants, graines et données de paquet sont refusés. Un accès distant utilise `Authorization: Bearer ...`. Une séance inconnue et une séance appartenant à une autre identité donnent toutes deux 404.

## 2. Lire les champs publics

| Champs | Lecture |
| --- | --- |
| `protocol_version`, `ruleset_id` | Versions du contrat et des règles. |
| `session_id`, `hand_id`, `revision` | Séance, main et révision courantes; la main est nulle avant distribution. |
| `session_status`, `end_reason`, `hand_status` | Séance active/finale, raison éventuelle, main `ready`, `decision` ou `hand_over`. |
| `bankroll`, `bankroll_before_hand`, `bet_pending` | Réserve disponible, réserve avant main et mise encore en attente. |
| `player_cards`, `player_total`, `player_usable_ace` | Cartes du joueur, total et présence d'un as utilisable à 11. |
| `dealer_upcard`, `dealer_cards`, `dealer_total` | Avant règlement : une seule carte visible, total nul. Après règlement normal : cartes complètes et total. |
| `legal_actions` | `['hit','hold']` en décision active, liste vide autrement. |
| `shoe_id`, `shoe_reset`, `visible_events` | Génération du paquet et cartes devenues visibles dans la dernière transition. |
| `result` | Nul avant règlement; sinon résultat détaillé de la main. |
| `limits` | Bornes de mains, temps, inactivité et rétention, échéance effective et compteur de mains réglées. |

Les cartes sont des objets `{rank, suit}`. Rangs : `2` à `10`, `J`, `Q`, `K`, `A`; couleurs : `clubs`, `diamonds`, `hearts`, `spades`. Les cartes invisibles n'ont aucun objet de remplacement contenant leur valeur.

Chaque événement contient exactement `event_id`, `shoe_id`, `hand_id`, `owner` et `card`. Les identifiants d'événement sont des chaînes uniques dans la séance; ils n'ont pas de trou causé par une carte cachée. À la distribution : joueur, croupier visible, joueur. À la résolution : carte cachée puis tirages éventuels du croupier. Un tirage joueur précède ces révélations. `GET` restitue les événements de la dernière transition; les relire ne signifie pas qu'ils se sont produits de nouveau.

Un résultat contient `outcome` (`win`, `tie`, `loss`), `reason`, `stake`, `credit`, `net_gain`, `bankroll_before`, `bankroll_after`. Les raisons sont `player_natural`, `dealer_natural`, `both_natural`, `player_bust`, `dealer_bust`, `higher_total`, `lower_total`, `equal_total`.

`limits` contient `max_hands`, `max_seconds`, `idle_seconds`, `retention_seconds`, `expires_at` (secondes Unix) et `hands_settled`. L'inactivité est mesurée depuis la dernière mutation acceptée; une lecture ou une répétition ne prolonge pas une séance. Une lecture peut constater et enregistrer l'expiration effective. Les heures et durées ne sont pas des entrées du modèle initial.

## 3. Reprendre sans doubler la mise

Une commande acceptée augmente la révision une fois. Une répétition avec le même identifiant et le même contenu renvoie la réponse initiale, même si la révision a changé depuis. Un contenu différent sous le même identifiant provoque un conflit. Deux commandes différentes visant la même révision ne peuvent pas toutes deux être appliquées.

Après un délai dépassé, conserver la commande, sa révision et son `request_id`. Le client HTTPS réessaie cette commande à l'identique, au plus selon `max_attempts`. Il n'envoie aucune nouvelle mutation tant qu'une commande reste incertaine. `retry_pending()` la reprend; `observe(session_id)` permet d'examiner l'état sans modifier cette commande en attente. Une réponse 429 ou 503 reste susceptible de reprise. Les reprises automatiques de 429 respectent `Retry-After` si celui-ci ne dépasse pas deux secondes; au-delà, l'erreur revient à l'appelant pour une attente explicite. Le délai réseau n'est pas une preuve d'absence d'application.

La période de reprise finit `retention_seconds` après la fin effective de la séance. À l'accès suivant cette période, les états/cartes et réponses conservées sont purgés; une trace minimale identité–identifiant empêche de recréer une ancienne séance et provoque 410. L'application de transport préparée ici n'effectue pas de purge périodique en arrière-plan. Une interruption ou expiration conserve les seules mains réellement réglées.

Une nouvelle exécution du client doit restaurer ses identifiants, sa commande incertaine et son journal avant de reprendre. L'exemple ponctuel `cycle_commandes.py` s'arrête sur une incertitude; il ne constitue pas une reprise durable entre processus.

## 4. Interpréter les erreurs

| Code HTTP / code métier | Réaction |
| --- | --- |
| 400 `invalid_request` | Corriger le JSON mal formé, les clés en double ou nombres non finis. |
| 401 `unauthenticated` | Rétablir l'accès; aucune création implicite. |
| 404 `session_not_found` | Vérifier l'identifiant et l'identité. |
| 409 `revision_conflict`, `invalid_transition`, `idempotency_conflict` | Relire et vérifier la commande; ne pas changer arbitrairement l'identifiant d'une commande incertaine. |
| 410 `session_gone` | Période de reprise terminée; ne pas recréer silencieusement le même essai. |
| 422 `invalid_payload`, `unsupported_version` | Corriger champs/types/valeurs/version. |
| 429 `rate_limited` | Respecter `Retry-After`; reprendre la même commande. |
| 503 `service_unavailable` | Reprendre la même commande ou lire l'état; aucune nouvelle main supposée. |

Une erreur métier locale lève `GameError` avec les mêmes codes applicables. Le corps distant est `{error:{code,message,request_id},revision}`. La révision est nulle si la séance n'est pas accessible. Les messages ne contiennent ni carte cachée, ni jeton, ni trace interne. Une échéance effective peut finaliser la séance avant l'action demandée; sa réponse porte la raison réelle, sans défaite inventée.

## 5. Références techniques

| Source | Contribution |
| --- | --- |
| [Python : urllib.request](https://docs.python.org/3.13/library/urllib.request.html) | Transport HTTP(S) de bibliothèque standard. |
| [Python : ssl](https://docs.python.org/3.13/library/ssl.html) | Contexte TLS et vérification des certificats. |

Le source installé n'exporte pas de fixture, de fonction de débogage ou d'accès public au paquet. Les champs privés, les erreurs internes et l'état d'autres identités ne font pas partie du contrat de jeu.
