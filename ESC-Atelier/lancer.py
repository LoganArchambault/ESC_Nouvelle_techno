"""Point d'entrée local : python 3.13 lancer.py --help."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
from random import Random
import sys
from uuid import uuid4

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE / 'materiel-officiel' / 'jeu-fourni' / 'src'))
from blackjack import Limits, LocalClient
from atelier.joueur import Bilans, action_acceptee, choisir, etat


def sauver(path, document):
    temporaire = path.with_suffix(path.suffix + '.tmp')
    temporaire.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')
    temporaire.replace(path)


def executer(client, politique, rng, bilans, recompenses, apprendre, trace):
    def appel(operation, **arguments):
        if operation != 'observe':
            arguments['request_id'] = uuid4().hex
        trace({'type': 'commande', 'operation': operation, 'arguments': arguments})
        reponse = getattr(client, operation)(**arguments)
        trace({'type': 'observation', 'operation': operation, 'observation': reponse})
        return reponse

    observation = appel('create_session', config_ref='atelier08-v1', model_ref=politique)
    trajectoire = []
    traitees = set()
    resumes = []
    while True:
        # Traiter le dernier résultat même si la séance vient de finir par hand_limit.
        hid = observation['hand_id']
        resultat = observation['result']
        if observation['hand_status'] == 'hand_over' and resultat is not None and hid not in traitees:
            retour = recompenses[resultat['outcome']]
            changements = (bilans.attribuer(observation['session_id'], hid, trajectoire,
                                            resultat, retour) if apprendre else [])
            resume = {'type': 'main_reglee', 'session_id': observation['session_id'],
                      'hand_id': hid, 'trajectoire': list(trajectoire), 'resultat': resultat,
                      'retour': retour if apprendre else None, 'apprentissage': apprendre,
                      'bilans': changements}
            trace(resume)
            resumes.append(resume)
            traitees.add(hid)
            trajectoire = []
        if observation['session_status'] != 'active':
            trace({'type': 'fin', 'session_id': observation['session_id'],
                   'statut': observation['session_status'], 'raison': observation['end_reason'],
                   'mains_reglees': observation['limits']['hands_settled'],
                   'trajectoire_sans_reglement': trajectoire})
            return resumes, observation
        if observation['hand_status'] in ('ready', 'hand_over'):
            observation = appel('start_hand', session_id=observation['session_id'],
                                expected_revision=observation['revision'])
        elif observation['hand_status'] == 'decision':
            action = choisir(observation, politique, rng)
            avant = observation
            observation = appel('act', session_id=avant['session_id'], action=action,
                                expected_revision=avant['revision'])
            acceptee = action_acceptee(avant, observation, action)
            visite = {'etat': etat(avant), 'action': action,
                      'revision_avant': avant['revision'], 'revision_apres': observation['revision']}
            trace({'type': 'choix', **visite, 'accepte': acceptee})
            if acceptee:
                trajectoire.append(visite)
        else:
            raise RuntimeError('Statut de main inconnu : ' + observation['hand_status'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--politique', required=True, choices=['fixed17', 'aleatoire'])
    parser.add_argument('--max-hands', type=int, required=True)
    parser.add_argument('--max-seconds', type=float, required=True)
    parser.add_argument('--idle-seconds', type=float, required=True)
    parser.add_argument('--retention-seconds', type=float, required=True)
    parser.add_argument('--seances', type=int, default=1)
    parser.add_argument('--apprendre', action='store_true')
    parser.add_argument('--victoire', type=int, default=1)
    parser.add_argument('--nul', type=int, default=0)
    parser.add_argument('--defaite', type=int, default=-1)
    parser.add_argument('--sortie', type=Path, default=RACINE / 'preuves')
    parser.add_argument('--table', type=Path, help='Table conservée entre les séances et exécutions.')
    parser.add_argument('--autoriser-version-hors-cible', action='store_true',
                        help='Diagnostic seulement; ne valide pas la cible du cours.')
    args = parser.parse_args()
    cible = platform.python_implementation() == 'CPython' and sys.version_info[:2] == (3, 13)
    if not cible and not args.autoriser_version_hors_cible:
        parser.error('CPython 3.13 requis. Vérifiez py -3.13 ou le chemin de Python 3.13.')
    if args.seances < 1:
        parser.error('--seances doit être positif.')
    if args.apprendre and args.politique != 'aleatoire':
        parser.error('Pour cet atelier, seuls les choix aléatoires alimentent les bilans.')
    if args.apprendre and args.table is None:
        parser.error('--table est requis avec --apprendre.')
    limites = Limits(args.max_hands, args.max_seconds, args.idle_seconds, args.retention_seconds)
    recompenses = {'win': args.victoire, 'tie': args.nul, 'loss': args.defaite}
    document = json.loads(args.table.read_text(encoding='utf-8')) if args.table and args.table.exists() else {}
    if document and document.get('recompenses') != recompenses:
        parser.error('Récompenses différentes de la table existante : utilisez un autre fichier.')
    bilans = Bilans(document)
    args.sortie.mkdir(parents=True, exist_ok=True)
    nom = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:8]
    dossier = args.sortie / nom
    dossier.mkdir()
    empreintes = {str(p.relative_to(RACINE)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(RACINE.rglob('*.py'))}
    metadata = {'version': 'atelier08-v1', 'date_utc': datetime.now(timezone.utc).isoformat(),
                'commande_argv': [sys.executable, *sys.argv], 'repertoire': str(Path.cwd()),
                'python': sys.version, 'implementation': platform.python_implementation(),
                'cible_cpython313_validee': cible, 'sha256_sources': empreintes,
                'politique': args.politique, 'apprentissage': args.apprendre,
                'limites': asdict(limites), 'recompenses_proposees': recompenses,
                'bilans_avant': bilans.exporter()}
    sauver(dossier / 'metadata.json', metadata)
    with (dossier / 'trace.jsonl').open('w', encoding='utf-8') as fichier:
        def trace(evenement):
            fichier.write(json.dumps(evenement, ensure_ascii=False) + '\n')
            fichier.flush()
        try:
            for _ in range(args.seances):
                # Aucun accès privé; hasard moteur et hasard des choix indépendants.
                resumes, fin = executer(LocalClient(limites), args.politique, Random(), bilans,
                                        recompenses, args.apprendre, trace)
                if args.apprendre:
                    args.table.parent.mkdir(parents=True, exist_ok=True)
                    sauver(args.table, dict(bilans.exporter(), recompenses=recompenses))
                print(f"{fin['session_id']} : {len(resumes)} main(s) réglée(s), "
                      f"{fin['session_status']}/{fin['end_reason']}")
                for r in resumes:
                    print(f"  {r['hand_id']} : {r['resultat']['outcome']}, "
                          f"{len(r['trajectoire'])} décision(s)")
                    for b in r['bilans']:
                        print('   ', b)
        except Exception as erreur:
            trace({'type': 'erreur', 'classe': type(erreur).__name__, 'message': str(erreur)})
            raise
        finally:
            sauver(dossier / 'bilans-apres.json', bilans.exporter())
    print('Preuve :', dossier)
    if not cible:
        print('DIAGNOSTIC HORS CIBLE : exécution CPython 3.13 encore à réaliser.')


if __name__ == '__main__':
    main()
