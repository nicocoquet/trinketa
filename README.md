# Trinketa

Site statique MkDocs d'inventaire du mobilier et des livres anciens, alimenté par les classeurs `inventaire_mobilier.xlsx` et `inventaire_bibliotheque.xlsx`, publié sur GitHub Pages : https://nicocoquet.github.io/trinketa/

## Comment fonctionne la génération

Les deux classeurs et le dossier `photos/` sont les sources de référence. Les
pages d’inventaire et de catalogue ne doivent pas être corrigées à la main : elles sont recréées
à chaque déploiement dans cet ordre :

1. `scripts/generate_mobilier.py` produit l’inventaire du mobilier sous
   `docs/inventario/` et la page Statistiques commune ;
2. `scripts/apply_bibliotheque_pipeline.py` injecte dans le classeur les notices validées issues du pipeline ISBN ;
3. `scripts/generate_bibliotheque.py` produit le catalogue des livres et le
   fichier `docs/assets/data/bibliotheque-statistiques.json` ;
4. MkDocs transforme le dossier `docs/` en site statique et le publie.

Le fichier JSON des statistiques est une sortie technique générée. Le
JavaScript le lit dans le navigateur pour construire les indicateurs, les
graphiques, les filtres et la carte. Il ne faut pas le modifier manuellement.

Les fiches Markdown des catalogues, la page Statistiques, le JSON et les copies
des photographies sont également des sorties générées. Elles sont exclues de
Git par `.gitignore` : leur absence dans l'arborescence de la branche `main` est
normale. Elles sont recréées avant chaque construction du site.

Pour vérifier localement l'ensemble du processus :

```bash
python -m pip install -r requirements.txt
python scripts/generate_mobilier.py
python scripts/apply_bibliotheque_pipeline.py
python scripts/generate_bibliotheque.py
mkdocs build --strict
```

## Inventaire du mobilier

### Mise à jour courante

1. Modifier `inventaire_mobilier.xlsx` sans changer son nom ;
2. Ajouter les nouveaux fichiers dans `photos/` ;
3. Remplacer le classeur et valider les modifications dans la branche `main`.

### Ajouter un objet dans l'inventaire

1. Ajouter une ligne au tableau dans la feuille **Mobilier** ;
2. Attribuer un identifiant unique et séquentiel (`MOB-002`, `MOB-003`, etc.) ;
3. Compléter les champs connus sans renommer les feuilles ni les colonnes ;
4. Inscrire **Oui** dans la colonne **Publié** lorsque la fiche peut apparaître en ligne.

Les champs inconnus peuvent rester vides.

### Ajouter des photographies

1. Renommer les images avec l’identifiant de l’objet : `MOB-002-01.jpeg`, `MOB-002-02.jpeg`, etc. ;
2. Les placer dans le dossier `photos/` ;
3. Ajouter une ligne par fichier dans la feuille **Photos** ;
4. Répéter le même identifiant pour toutes les vues du même objet ;
5. Attribuer un ordre et choisir une seule image principale.

Pour masquer temporairement une fiche sans la supprimer du classeur, passez sa valeur **Publié** de **Oui** à **Non**.

## Bibliothèque

### Ingestion par ISBN — fonctionnement recommandé

Le point d’entrée des nouveaux livres est désormais `photos/bibliotheque/isbn/` :

- `a_traiter/` reçoit les nouvelles photographies de codes-barres ;
- `a_verifier/` reçoit uniquement les cas qui demandent une décision humaine ;
- `traite/` archive les images qui ont produit une notice validée et publiée.

Procédure courante :

1. ouvrir [la page de dépôt ISBN](https://nicocoquet.github.io/trinketa/depot-isbn/) depuis le bouton de la Bibliothèque ; les images sont réorientées, converties en JPEG et débarrassées de leurs métadonnées avant leur écriture dans GitHub ;
2. se connecter avec un compte GitHub autorisé, déposer les photographies et fusionner la pull request de dépôt après contrôle ;
3. cliquer sur **Lancer l’analyse** dans la même page, ou déclencher manuellement le workflow **Analyser la file ISBN** dans GitHub Actions ;
4. le traitement tente successivement deux lecteurs de codes-barres puis un OCR des chiffres imprimés, valide mathématiquement l’ISBN, interroge la BnF et Open Library, attribue le prochain `BIB-xxx` lorsque l’identification est suffisamment sûre et ouvre une nouvelle pull request ;
5. contrôler puis fusionner cette pull request. L’image est archivée dans `traite/`, ou déplacée dans `a_verifier/` si l’identification est ambiguë ;
6. chaque traitement est consigné dans `data/bibliotheque/imports/journal.csv` et accompagné d’un rapport Markdown.

Toutes les écritures passent ainsi par une branche et une pull request : la
protection de `main` reste effective. L’analyse est un workflow GitHub
déterministe et ne dépend plus d’un compte ChatGPT.

Le classeur `inventaire_bibliotheque.xlsx` reste la base éditoriale. Le journal d’ingestion n’est qu’une trace technique destinée à la traçabilité et à la détection des doublons.

Pour inspecter localement la file et connaître le prochain identifiant disponible :

```bash
python scripts/check_bibliotheque_queue.py
```

### Mise à jour manuelle

Il reste possible de modifier directement `inventaire_bibliotheque.xlsx` et d’ajouter les photographies documentaires dans `photos/bibliotheque/`. Les champs inconnus peuvent rester vides.

Pour masquer temporairement une fiche sans la supprimer du classeur, passez sa valeur **Publié** de **Oui** à **Non**.

## Statistiques

La page **Statistiques** réunit dans une même vue :

- les estimations et répartitions du mobilier ;
- les indicateurs, graphiques et la carte des lieux d’édition de la bibliothèque.

Elle est régénérée automatiquement à partir des deux classeurs lors de chaque déploiement. Le script du mobilier construit la page unifiée, puis le script de la bibliothèque produit le jeu de données interactif consommé par cette page.
