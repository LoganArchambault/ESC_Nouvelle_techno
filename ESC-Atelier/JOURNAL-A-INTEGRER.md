# Proposition à intégrer au journal existant — 26 octobre 2026

Noms des membres : à compléter. Ce texte décrit le travail préparé et exécuté par l’assistant; les vérifications personnelles des membres restent à consigner après réalisation.

- Périmètre : état (total joueur fourni par le moteur, valeur de carte visible du croupier), as 11 et figures 10. Fixed-17 : hit sous 17, hold dès 17, seulement en décision légale. Aucun apprentissage pour cette référence.
- Récompenses proposées, à confirmer : victoire +1, nul 0, défaite −1, pour donner un poids absolu égal à gagner et perdre; gains en crédits distincts.
- Question provisoire : comment les moyennes de retours des actions hit et hold évoluent-elles, pour un même état, lorsque la collecte aléatoire apporte de nouvelles visites? La collecte actuelle ne permet pas une conclusion de performance.
- Version : atelier08-v1, empreintes du code dans metadata.json de chaque preuve. Commandes, bornes et traces : voir LECTURE-PREUVES.md et preuves/.
- Résultat obtenu par l’assistant : Fixed-17, une main puis cinq dans une même séance; première mise à jour réelle de la main d9eb1702a47e48e6af585aeed9c8b141, retour -1, 3 visites. Les bilans avant/après sont recalculables dans preuves/20261026T182202-3bc4cf7e/trace.jsonl. Courte collecte suivante avec la même table conservée. Fins par hand_limit, pas des défaites de séance. 11 tests du joueur et 29 tests officiels réussis sous CPython 3.13.16.
- Blocage/limite : projet et journal existants du binôme non fournis; intégration non réalisée. Exécution Windows et compréhension par chaque membre non encore attestées. Les récompenses et conclusions restent à décider par le binôme.
- Prochaine vérification : reproduire les commandes sur notre poste, vérifier les changements, expliquer une décision et une transition chacun, recalculer un couple de la première main à la main, puis consigner ce qui a réellement été vérifié. Sélection par Q, exploration epsilon et gel réservés à la prochaine rencontre.
