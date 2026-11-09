"""Contrôles du budget et de la séparation des mesures."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from atelier.joueur import Bilans
from experience_esc import lot


class ExperienceTests(TestCase):
    def test_relance_et_budget_exact_apres_fin_anticipee(self):
        limites = []
        def client(l, **kw):
            limites.append(l.max_hands)
            return None
        def executer(*args, **kw):
            return ([{'resultat': {'outcome': 'win'}}] * min(3, limites[-1]), {})
        with patch('experience_esc.LocalClient', client), patch('experience_esc.executer', executer):
            comptes = lot(8, Bilans(), True, 0.1, 42, lambda e: None, 'A2')
        self.assertEqual(comptes, dict(win=8, tie=0, loss=0))
        self.assertEqual(limites, [8, 5, 2])

    def test_mesure_reelle_sans_modification_et_epsilon_zero(self):
        b = Bilans()
        avant = deepcopy(b.exporter())
        traces = []
        comptes = lot(120, b, False, 0.25, 42, traces.append, 'A1')
        self.assertEqual(sum(comptes.values()), 120)
        self.assertEqual(b.exporter(), avant)
        self.assertTrue(all(e['epsilon'] == 0 for e in traces if e['type'] == 'conditions_seance'))
