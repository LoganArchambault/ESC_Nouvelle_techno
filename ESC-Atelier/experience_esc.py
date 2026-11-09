"""Campagne A1/A2 : CPython 3.13, tables neuves, mesures gelées."""
import csv
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
from random import Random
import sys

from lancer import RACINE, Limits, LocalClient, executer, sauver
from atelier.joueur import Bilans

POINTS = range(0, 10001, 2000)
RECOMPENSES = {'win': 1, 'tie': 0, 'loss': -1}
LIMITES = Limits(100, 60, 30, 60)


def lot(nombre, table, apprendre, epsilon, graine, trace, config):
    """Compter uniquement les règlements; relancer après chaque fin de séance."""
    comptes = dict(win=0, tie=0, loss=0)
    seance = 0
    while sum(comptes.values()) < nombre:
        restant = nombre - sum(comptes.values())
        limites = Limits(min(LIMITES.max_hands, restant), LIMITES.max_seconds,
                         LIMITES.idle_seconds, LIMITES.retention_seconds)
        seed = graine + seance
        trace(dict(type='conditions_seance', configuration=config, apprentissage=apprendre,
                   epsilon=epsilon if apprendre else 0, graine_moteur=seed,
                   graine_choix=seed + 1000000, limites=asdict(limites)))
        mains, fin = executer(LocalClient(limites, seed=seed), 'apprise',
                              Random(seed + 1000000), table, RECOMPENSES,
                              apprendre, trace, epsilon=epsilon)
        for main in mains:
            comptes[main['resultat']['outcome']] += 1
        if not mains:
            raise RuntimeError('Séance sans règlement : arrêt, consulter la trace.')
        seance += 1
    return comptes


def campagne(sortie):
    if sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 13):
        raise RuntimeError('Exécuter avec CPython 3.13.')
    sortie.mkdir(parents=True, exist_ok=False)
    metadata = dict(version='esc-cours10-v1', python=sys.version,
                    date_utc=datetime.now(timezone.utc).isoformat(),
                    attribution='récompense terminale à chaque visite',
                    sha256_sources={str(p.relative_to(RACINE)): hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in sorted(RACINE.rglob('*.py'))})
    sauver(sortie / 'metadata.json', metadata)
    with (sortie / 'mes-resultats.csv').open('w', newline='', encoding='utf-8') as f:
        csvfile = csv.DictWriter(f, fieldnames=['configuration', 'mains_entrainement',
                                               'victoires', 'nulles', 'defaites'])
        csvfile.writeheader()
        for nom, epsilon in [('A1', 0.25), ('A2', 0.10)]:
            dossier = sortie / nom
            dossier.mkdir()
            sauver(dossier / 'configuration.json', dict(configuration=nom, epsilon=epsilon,
                   recompenses=RECOMPENSES, limites=asdict(LIMITES), budget=10000,
                   points=list(POINTS), mains_par_mesure=500, epsilon_mesure=0,
                   apprentissage_mesure=False, graine_base=20261109,
                   intention=('Référence du dernier cours.' if nom == 'A1' else
                   'Réduire les choix exploratoires; espérer une exploitation plus rapide, au risque de moins visiter certains états.')))
            table = Bilans()
            sauver(dossier / 'table-0.json', table.exporter())
            with gzip.open(dossier / 'trace.jsonl.gz', 'wt', encoding='utf-8') as tf:
                def trace(e):
                    tf.write(json.dumps(e, ensure_ascii=False) + '\n')
                for point in POINTS:
                    if point:
                        lot(2000, table, True, epsilon, 20261109 + point * 100,
                            trace, nom)
                    sauver(dossier / f'table-{point}.json', table.exporter())
                    avant = deepcopy(table.exporter())
                    copie = Bilans(deepcopy(avant))
                    comptes = lot(500, copie, False, 0, 30261109 + point * 100,
                                  trace, nom)
                    if copie.exporter() != avant or table.exporter() != avant:
                        raise RuntimeError('Table modifiée pendant la mesure.')
                    trace(dict(type='verification_mesure', point=point,
                               table_identique=True, comptes=comptes))
                    csvfile.writerow(dict(configuration=nom, mains_entrainement=point,
                        victoires=comptes['win'], nulles=comptes['tie'], defaites=comptes['loss']))
                    f.flush()
                    print(nom, point, comptes, flush=True)
            sauver(dossier / 'modele-final.json', dict(table.exporter(), recompenses=RECOMPENSES))


if __name__ == '__main__':
    campagne(Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE / 'resultats-cours10')
