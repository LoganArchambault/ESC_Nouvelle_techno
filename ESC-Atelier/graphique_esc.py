"""Graphique des évaluations, jamais des victoires cumulées d'entraînement."""
import csv
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def graphique(dossier):
    with (dossier / 'mes-resultats.csv').open(encoding='utf-8', newline='') as f:
        lignes = list(csv.DictReader(f))
    fig, ax = plt.subplots(figsize=(9, 5.4))
    for nom in ('A1', 'A2'):
        points = sorted([r for r in lignes if r['configuration'] == nom],
                        key=lambda r: int(r['mains_entrainement']))
        x, y = [], []
        for r in points:
            v, n, d = (int(r[c]) for c in ('victoires', 'nulles', 'defaites'))
            if v + n + d != 500 or min(v, n, d) < 0:
                raise ValueError('Chaque mesure doit contenir 500 résultats réels.')
            x.append(int(r['mains_entrainement']))
            y.append(100 * v / (v + n + d))
        ax.plot(x, y, marker='o', label=nom)
    ax.set(xlim=(0, 10000), ylim=(0, 100), xticks=list(range(0, 10001, 2000)),
           xlabel="Mains d'entraînement réglées", ylabel='Taux de victoire en mesure (%)',
           title='ESC — A1 (ε = 0,25) et A2 (ε = 0,10)')
    ax.grid(alpha=0.3)
    ax.legend()
    fig.text(0.5, 0.015, '500 mains par point · ε = 0 · apprentissage désactivé · une répétition', ha='center')
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(dossier / 'comparaison-A1-A2.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    graphique(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / 'resultats-cours10')
