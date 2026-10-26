"""Décisions publiques et moyennes de retours terminaux, sans sélection apprise."""

from collections import Counter


def etat(observation):
    rang = observation['dealer_upcard']['rank']
    valeur = 11 if rang == 'A' else 10 if rang in ('J', 'Q', 'K') else int(rang)
    return observation['player_total'], valeur


def choisir(observation, politique, rng):
    if observation['session_status'] != 'active' or observation['hand_status'] != 'decision':
        raise ValueError('Aucune décision permise.')
    actions = observation['legal_actions']
    if not actions:
        raise ValueError('Aucune action légale.')
    if politique == 'fixed17':
        action = 'hit' if observation['player_total'] < 17 else 'hold'
        if action not in actions:
            raise ValueError('Action Fixed-17 absente de legal_actions.')
        return action
    if politique == 'aleatoire':
        return rng.choice(actions)
    raise ValueError('Politique inconnue.')


def action_acceptee(avant, apres, action):
    """Une expiration peut changer la révision sans appliquer le choix demandé."""
    if (avant['session_status'] != 'active' or avant['hand_status'] != 'decision'
            or action not in avant['legal_actions']
            or apres['session_id'] != avant['session_id']
            or apres['hand_id'] != avant['hand_id']
            or apres['revision'] != avant['revision'] + 1):
        return False
    if action == 'hit':
        return (len(apres['player_cards']) == len(avant['player_cards']) + 1
                and apres['player_cards'][:-1] == avant['player_cards'])
    return apres['hand_status'] == 'hand_over' and apres['result'] is not None


class Bilans:
    def __init__(self, document=None):
        document = document or {}
        self.table = {}
        for ligne in document.get('bilans', []):
            cle = (tuple(ligne['etat']), ligne['action'])
            self.table[cle] = [ligne['N'], ligne['S']]
        self.attribuees = set(tuple(x) for x in document.get('mains_attribuees', []))

    def consulter(self, situation, action):
        n, s = self.table.get((tuple(situation), action), (0, 0))
        return {'N': n, 'S': s, 'Q': s / n if n else 0}

    def attribuer(self, session_id, hand_id, trajectoire, resultat, retour):
        identite = (session_id, hand_id)
        if resultat is None or identite in self.attribuees:
            return []
        occurrences = Counter((tuple(v['etat']), v['action']) for v in trajectoire)
        changements = []
        for (situation, action), nombre in sorted(occurrences.items()):
            avant = self.consulter(situation, action)
            n, s = self.table.setdefault((situation, action), [0, 0])
            self.table[(situation, action)] = [n + nombre, s + nombre * retour]
            changements.append({'etat': situation, 'action': action, 'occurrences': nombre,
                                 'avant': avant, 'apres': self.consulter(situation, action)})
        self.attribuees.add(identite)
        return changements

    def exporter(self):
        return {'bilans': [dict(etat=s, action=a, **self.consulter(s, a))
                           for s, a in sorted(self.table)],
                'mains_attribuees': sorted(self.attribuees)}
