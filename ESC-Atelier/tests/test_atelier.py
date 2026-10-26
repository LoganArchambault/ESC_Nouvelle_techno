"""Vérifications de notre joueur; aucun accès à l'état privé du moteur."""

from copy import deepcopy
from random import Random
import unittest

from lancer import Limits, LocalClient, executer
from atelier.joueur import Bilans, action_acceptee, choisir, etat


def observation(total=16, rang='A'):
    return dict(session_status='active', hand_status='decision', legal_actions=['hit', 'hold'],
                player_total=total, dealer_upcard={'rank': rang, 'suit': 'clubs'},
                session_id='s', hand_id='h', revision=1, result=None,
                player_cards=[{'rank': '6'}, {'rank': '10'}])


class PolitiqueTests(unittest.TestCase):
    def test_frontiere_et_totaux_moteur(self):
        for total in range(4, 21):
            with self.subTest(total=total):
                self.assertEqual(choisir(observation(total), 'fixed17', Random(0)),
                                 'hit' if total < 17 else 'hold')

    def test_cartes_visibles(self):
        for rang, valeur in [('A', 11), ('K', 10), ('Q', 10), ('J', 10), ('7', 7)]:
            self.assertEqual(etat(observation(16, rang)), (16, valeur))

    def test_arret_et_action_illegale(self):
        for changement in [dict(session_status='truncated'), dict(hand_status='hand_over'),
                           dict(legal_actions=[]), dict(legal_actions=['hold'])]:
            o = observation()
            o.update(changement)
            with self.assertRaises(ValueError):
                choisir(o, 'fixed17', Random(0))

    def test_hasard_utilise_uniquement_la_liste_legale(self):
        class GenerateurTemoin:
            def choice(self, actions):
                self.actions = actions
                return actions[-1]
        rng = GenerateurTemoin()
        o = observation()
        self.assertEqual(choisir(o, 'aleatoire', rng), 'hold')
        self.assertIs(rng.actions, o['legal_actions'])

    def test_expiration_ne_prouve_pas_acceptation(self):
        avant = observation()
        apres = deepcopy(avant)
        apres.update(revision=2, session_status='expired', end_reason='idle_timeout')
        self.assertFalse(action_acceptee(avant, apres, 'hit'))
        self.assertFalse(action_acceptee(avant, apres, 'hold'))
        apres['player_cards'].append({'rank': '2'})
        self.assertTrue(action_acceptee(avant, apres, 'hit'))


class BilansTests(unittest.TestCase):
    def test_inconnu_sans_insertion(self):
        b = Bilans()
        self.assertEqual(b.consulter((16, 10), 'hit'), dict(N=0, S=0, Q=0))
        self.assertEqual(b.exporter()['bilans'], [])

    def test_repetitions_zero_et_deuxieme_attribution(self):
        b = Bilans()
        visites = [dict(etat=(13, 9), action='hit')] * 2
        b.attribuer('s', 'h1', visites, {'outcome': 'win'}, 1)
        self.assertEqual(b.consulter((13, 9), 'hit'), dict(N=2, S=2, Q=1))
        self.assertEqual(b.attribuer('s', 'h1', visites, {'outcome': 'win'}, 1), [])
        b.attribuer('s', 'h2', visites[:1], {'outcome': 'tie'}, 0)
        self.assertEqual(b.consulter((13, 9), 'hit'), dict(N=3, S=2, Q=2/3))
        b.attribuer('s', 'h3', visites[:1], None, 0)
        self.assertEqual(b.consulter((13, 9), 'hit')['N'], 3)
        self.assertEqual(Bilans(b.exporter()).exporter(), b.exporter())

    def test_moyenne_connue_nulle(self):
        b = Bilans()
        b.attribuer('s', 'h', [dict(etat=(17, 10), action='hold')], {'outcome': 'tie'}, 0)
        self.assertEqual(b.consulter((17, 10), 'hold'), dict(N=1, S=0, Q=0))


class CycleTests(unittest.TestCase):
    def test_cinq_mains_meme_seance_et_aucun_apprentissage_fixed17(self):
        traces = []
        b = Bilans()
        mains, fin = executer(LocalClient(Limits(5, 60, 30, 60), seed=8),
                              'fixed17', Random(10), b, {'win': 1, 'tie': 0, 'loss': -1},
                              False, traces.append)
        self.assertEqual(len(mains), 5)
        self.assertEqual(len({m['session_id'] for m in mains}), 1)
        self.assertEqual(fin['end_reason'], 'hand_limit')
        self.assertEqual(b.exporter()['bilans'], [])
        for t in traces:
            if t['type'] == 'choix':
                self.assertTrue(t['accepte'])
                self.assertEqual(t['action'], 'hit' if t['etat'][0] < 17 else 'hold')

    def test_attribution_de_toutes_les_visites_reelles(self):
        b = Bilans()
        mains, _ = executer(LocalClient(Limits(5, 60, 30, 60), seed=2),
                             'aleatoire', Random(42), b, {'win': 1, 'tie': 0, 'loss': -1},
                             True, lambda t: None)
        self.assertEqual(sum(x['N'] for x in b.exporter()['bilans']),
                         sum(len(m['trajectoire']) for m in mains))
        self.assertGreater(sum(x['N'] for x in b.exporter()['bilans']), 0)
        for m in mains:
            for ligne in m['bilans']:
                self.assertEqual(ligne['apres']['N'] - ligne['avant']['N'], ligne['occurrences'])
                self.assertEqual(ligne['apres']['S'] - ligne['avant']['S'],
                                 ligne['occurrences'] * m['retour'])

    def test_naturel_sans_decision_et_interruption_sans_retour(self):
        # Réponses publiques simulées : ce test ne prétend pas être une main aléatoire réelle.
        class ClientScenario:
            def __init__(self, naturel):
                self.naturel = naturel
            def create_session(self, **kw):
                o = observation()
                o.update(hand_status='ready', hand_id=None, revision=0)
                return o
            def start_hand(self, **kw):
                o = observation(21 if self.naturel else 16)
                if self.naturel:
                    o.update(session_status='truncated', hand_status='hand_over', legal_actions=[],
                             result={'outcome': 'win'}, end_reason='hand_limit',
                             limits={'hands_settled': 1})
                return o
            def act(self, **kw):
                o = observation()
                o.update(session_status='expired', revision=2, legal_actions=[],
                         end_reason='idle_timeout', limits={'hands_settled': 0})
                return o
        for naturel in (True, False):
            b = Bilans()
            mains, _ = executer(ClientScenario(naturel), 'aleatoire', Random(0), b,
                                 {'win': 1, 'tie': 0, 'loss': -1}, True, lambda t: None)
            self.assertEqual(b.exporter()['bilans'], [])
            self.assertEqual(len(mains), int(naturel))


if __name__ == '__main__':
    unittest.main()
