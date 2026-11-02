# Atelier — Fixed-17 et politique apprise

Version : atelier08-v1. Auteur du code ajouté : assistant IA, à vérifier et à expliquer par les membres du binôme. Noms des membres : à compléter.

Ce dossier contient le matériel officiel v1.1 intact dans `materiel-officiel/`, et une proposition d'implémentation de l'atelier. Aucun projet existant du binôme n'a été fourni : les ajouts restent à intégrer au besoin. Ce n'est pas le projet final A1/A2/B1/B2.

## Démarrage sous Windows (PowerShell)

Extraire le ZIP, puis ouvrir PowerShell dans le dossier contenant `lancer.py`.

```powershell
py -3.13 -c "import sys, platform; print(platform.python_implementation()); print(sys.version); print(sys.executable)"
py -3.13 -m unittest discover -s tests -v
```

La version doit réellement être CPython 3.13. Aucun paquet à installer, réseau ou jeton nécessaire. Si le lanceur manque, remplacer `py -3.13` par `& 'CHEMIN_VERIFIE_VERS_PYTHON_3.13.exe'`. Le programme ajoute lui-même le dossier `src` officiel au chemin d'importation.

Une main Fixed-17 :

```powershell
py -3.13 lancer.py --politique fixed17 --max-hands 1 --max-seconds 60 --idle-seconds 30 --retention-seconds 60
```

Nouvelle séance de cinq mains, distribuées explicitement dans la même séance :

```powershell
py -3.13 lancer.py --politique fixed17 --max-hands 5 --max-seconds 60 --idle-seconds 30 --retention-seconds 60
```

Première main avec choix aléatoires et apprentissage :

```powershell
py -3.13 lancer.py --politique aleatoire --apprendre --table preuves/table-mon-binome.json --max-hands 1 --max-seconds 60 --idle-seconds 30 --retention-seconds 60
```

Si cette main est un naturel, elle ne produit aucune décision : conserver sa trace et exécuter une nouvelle séance pour obtenir une main décisionnelle. Aucun objectif de victoire. Après vérification de la première mise à jour, courte collecte en gardant la même table :

```powershell
py -3.13 lancer.py --politique aleatoire --apprendre --table preuves/table-mon-binome.json --max-hands 5 --max-seconds 60 --idle-seconds 30 --retention-seconds 60
```

Sous Linux/macOS : remplacer `py -3.13` par le chemin de CPython 3.13, généralement `python3.13`.

## Politique apprise

Entraîner à partir de la table existante (ou en créer une si elle n'existe pas) :

```powershell
py -3.13 lancer.py --politique apprise --apprendre --table preuves/table-mon-binome.json --max-hands 5 --max-seconds 60 --idle-seconds 30 --retention-seconds 60
```

Entraînement : à chaque décision, exploration uniforme parmi les actions légales avec epsilon = 0,25; sinon, choix uniforme parmi les actions légales de Q maximal. Les lectures inconnues valent zéro sans ajouter d'entrée. Chaque visite acceptée reçoit la récompense terminale au règlement, puis la table est réutilisée pour les mains suivantes.

Mesurer avec la même table, sans apprentissage et avec epsilon = 0 :

```powershell
py -3.13 lancer.py --politique apprise --table preuves/table-mon-binome.json --max-hands 5 --max-seconds 60 --idle-seconds 30 --retention-seconds 60
```

La mesure exige un fichier de table existant et ne le modifie pas; les égalités restent départagées uniformément au hasard. Q est une récompense moyenne estimée, pas une probabilité de victoire. Utiliser les mêmes options de récompense que lors de la création de la table.

## Fichiers à comprendre

- `atelier/joueur.py` : état public, politiques Fixed-17, aléatoire et apprise, reconnaissance d'une action acceptée et table N/S/Q.
- `lancer.py` : cycle création → distribution → décisions → règlement, sauvegarde immédiate des traces, table persistante entre séances.
- `tests/test_atelier.py` : propres vérifications de la frontière, des bilans et du pilotage.
- `preuves/` : exécutions réelles réalisées par l'assistant; chaque nouvelle commande produit un autre sous-dossier.
- `LECTURE-PREUVES.md` : résultats et calcul manuel de la première mise à jour.
- `JOURNAL-A-INTEGRER.md` : proposition à relire et intégrer au journal existant, sans inventer une exécution par les membres.

## Récompenses proposées, à décider en binôme

Par défaut : victoire +1, nul 0, défaite −1. Cela donne le même poids absolu à victoire et défaite. Les gains du moteur restent +50/0/−50 crédits. Options : `--victoire`, `--nul`, `--defaite` (entiers). Changer les récompenses exige une nouvelle table pour éviter de mélanger deux systèmes.

Pour chaque visite acceptée, au règlement : N augmente de 1, S augmente du retour terminal, Q devient S/N. Les répétitions comptent toutes. Une lecture inconnue retourne 0 sans insertion; ce n'est pas une moyenne observée. Un nul réglé augmente N. Une main inachevée n'attribue aucun retour. Les identifiants des mains attribuées empêchent la double attribution dans les bilans.

## Lire une preuve

Chaque sous-dossier contient :

- `metadata.json` : commande argv réelle, interpréteur, quatre bornes, politique, récompenses, empreintes SHA-256 du code et bilans avant.
- `trace.jsonl` : une ligne JSON par commande, réponse publique, choix, règlement et fin. Les commandes sont écrites avant leur exécution.
- `bilans-apres.json` : table après le passage, même en cas d'erreur.

La trace `main_reglee` relie hand_id, trajectoire ordonnée, résultat, retour et occurrences avec bilans avant/après. `truncated/hand_limit` signifie que la borne est atteinte; le résultat de la dernière main reste distinct.

Les mains et événements affichés ne sont pas rejouables dans un nouveau processus LocalClient : les preuves doivent être conservées. Ce programme local s'arrête sur une erreur, conserve la commande et ne lance pas de mutation de remplacement. Il ne propose pas de reprise durable de séance ni de transport HTTPS.

## Limites à expliquer

L'état `(total, carte visible)` regroupe les as utilisables et non utilisables. La politique utilise seulement le total fourni; aucune carte cachée, graine ou donnée privée ne participe au choix. Les tests déterministes du cycle utilisent des graines locales de test, jamais des entrées de la politique. Les preuves d'atelier sont produites sans graine imposée.

Fixed-17 n'apprend pas. La collecte aléatoire alimente une table mais ne choisit jamais selon Q; la politique apprise l'utilise pour ses décisions. Aucun score minimal, campagne finale ou couverture exhaustive n'est revendiqué.

Les tests synthétiques vérifient 16/17, naturels, interruption, réattribution, inconnus et zéro; ils sont identifiés comme tels. Une partie aléatoire ne prouve pas à elle seule ces cas limites. Le test du hasard vérifie l'appel à `Random.choice` sur la liste légale, pas une fréquence exacte dans une petite collecte.

Validation réalisée ici sous CPython 3.13.16 sur Linux; exécution sur votre poste Windows encore à vérifier. L'option `--autoriser-version-hors-cible` sert uniquement au diagnostic et marque les traces non conformes à la cible de version.
