# File d’ingestion ISBN

Ce répertoire est le point d’entrée des photographies de codes-barres pour la bibliothèque Emeleta.

- `a_traiter/` : déposer ici les nouvelles photographies de codes-barres ISBN.
- `a_verifier/` : cas qui nécessitent une intervention humaine (ISBN illisible, édition ambiguë, sources contradictoires non résolues, etc.).
- `traite/` : photographies ayant produit une notice validée et publiée.

## Règle d’usage

1. Ouvrir la page [Dépôt ISBN](https://nicocoquet.github.io/trinketa/depot-isbn/) et se connecter avec un compte GitHub autorisé.
2. Déposer une ou plusieurs images. L’interface crée une branche et une pull request ; fusionner celle-ci après contrôle pour alimenter `a_traiter/`.
3. Revenir sur la page de dépôt et cliquer sur **Lancer l’analyse**, ou lancer manuellement le workflow **Analyser la file ISBN** dans l’onglet Actions de GitHub.
4. Le traitement lit l’ISBN, interroge les sources bibliographiques et ouvre une seconde pull request de validation. Il ne modifie jamais directement `main`.
5. Contrôler les notices proposées puis fusionner la pull request. Une image suffisamment sûre est archivée sous la forme `BIB-xxx_isbn_<ISBN13>.<extension>` dans `traite/`. Un cas ambigu est déplacé dans `a_verifier/` et documenté dans le rapport.

Le tableur `inventaire_bibliotheque.xlsx` reste la base éditoriale. Le fichier `data/bibliotheque/imports/journal.csv` est uniquement le journal d’ingestion et de traçabilité.
