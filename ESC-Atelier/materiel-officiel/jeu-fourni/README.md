# Utiliser le jeu Blackjack fourni

Le moteur calcule les cartes, les règles, les actions légales et les résultats. La même interface permet les appels locaux directs et les échanges HTTPS. La représentation d'un agent, ses décisions, son apprentissage, ses récompenses et ses expériences restent à construire séparément.

## 1. Préparer Python

Cible : **CPython 3.13**, correctif de référence **3.13.16**, Windows x64. Les tests locaux ont aussi été exécutés sur 3.13.14. L'installation sur les postes institutionnels reste à vérifier. Le jeu et le client HTTPS utilisent uniquement la bibliothèque standard; aucune bibliothèque d'apprentissage n'est requise par le jeu.

Les commandes suivantes s'exécutent depuis le dossier `jeu-fourni`. Avec le lanceur Python Windows :

```powershell
py -3.13 -c "import sys; print(sys.version); print(sys.executable)"
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
py -3.13 -m unittest discover -s tests -v
py -3.13 examples/cycle_commandes.py --max-hands 1 --max-seconds 60 --idle-seconds 30 --retention-seconds 60 --actions hold
```

La dernière commande impose une seule action à une seule main. Elle vérifie le branchement et affiche une observation JSON; elle ne constitue pas une stratégie de référence. Un naturel peut terminer la main dès sa distribution. Les petites bornes de cet exemple servent à la vérification, sans fixer un protocole d'expérimentation.

Si `py` est absent, utiliser le chemin complet de Python 3.13 avec l'opérateur PowerShell `&`. La commande `python` peut désigner une autre version : vérifier réellement sa sortie.

Une installation du paquet dans un environnement existant est également possible :

```powershell
py -3.13 -m pip install .
```

La construction utilise `setuptools==84.0.0`, indiqué dans `pyproject.toml`. Après installation, `from blackjack import LocalClient, Limits` fonctionne sans définir `PYTHONPATH`. Les fichiers source, les tests et la documentation restent consultables dans ce dossier.

## 2. Appeler le moteur local

```python
from blackjack import Limits, LocalClient

# Bornes explicites d'une vérification ponctuelle.
client = LocalClient(Limits(max_hands=1, max_seconds=60,
                           idle_seconds=30, retention_seconds=60))
observation = client.create_session("verification", "commandes-imposees", "creation-1")
observation = client.start_hand(observation["session_id"],
                                observation["revision"], "distribution-1")
```

Une décision n'est permise que si `legal_actions` contient `hit` et `hold`. `act(session_id, action, expected_revision, request_id)` applique une action choisie par l'appelant. `observe(session_id)` permet de relire l'état et `close_session(session_id, expected_revision, request_id)` confirme une interruption. Chaque nouvelle commande reçoit un identifiant inédit; une reprise conserve l'identifiant et le contenu exacts de la commande incertaine.

Les bornes locales sont obligatoires. Une graine facultative `LocalClient(limits, seed=...)` permet de reproduire un essai local; elle n'entre jamais dans l'observation ou dans les entrées d'un agent. Le mode local n'ouvre ni réseau, ni base de données et n'exige aucun service actif.

## 3. Utiliser le même contrat en HTTPS

```python
import os
from blackjack.client_https import HTTPSClient

client = HTTPSClient("https://hote-fourni-par-le-professeur.example",
                     os.environ["BLACKJACK_TOKEN"])
```

Le nom d'hôte ci-dessus est un exemple à remplacer par l'adresse effectivement fournie. Les cinq méthodes de jeu sont les mêmes qu'en mode local. Le serveur fixe les bornes; aucune mise, graine ou séquence de cartes ne peut être envoyée. Le jeton reste hors du code, de l'URL et des journaux. Le client vérifie les certificats TLS et refuse les redirections. Le service commun et son accès seront fournis séparément; les tests HTTP locaux ne prouvent pas leur disponibilité.

La commande manuelle accepte aussi `--url` et lit `BLACKJACK_TOKEN`. Le délai du transport est de 5 secondes par tentative et le maximum est de 2 tentatives par appel, configurables dans `HTTPSClient`. Une réponse perdue exige une reprise de la même commande; les détails sont dans [l'interface](docs/INTERFACE.md).

## 4. Consulter les responsabilités et les règles

- [Règles et comptabilité](docs/REGLES.md) : mains, séances, réserve, renouvellement et interruptions.
- [Interface et reprise](docs/INTERFACE.md) : champs autorisés, commandes, erreurs et idempotence.
- `tests/test_engine.py` : vérifications du moteur fourni; les fixtures sont dans le harnais de tests et ne sont pas des entrées distantes.
- `examples/cycle_commandes.py` : petit client de commandes imposées, utilisable dans les deux modes.

Le code source permet de comprendre le moteur. Les cartes restantes, la carte cachée, l'état aléatoire et les champs privés ne sont jamais des entrées autorisées pour un agent. Les tests de l'agent et la vérification de ses propres calculs et choix demeurent distincts des tests du jeu fourni.
