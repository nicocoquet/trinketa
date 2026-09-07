# Service de dépôt ISBN

Ce service conserve les secrets GitHub hors de GitHub Pages. Il authentifie le
collaborateur, crée une branche et une pull request pour les images déposées,
puis peut déclencher le workflow d’analyse ISBN.

Variables Render :

```text
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
SESSION_SECRET=valeur-aleatoire-longue
GITHUB_REPOSITORY=nicocoquet/trinketa
PAGES_URL=https://nicocoquet.github.io/trinketa/depot-isbn/
ALLOWED_USERS=nicocoquet
```

Dans les réglages de la GitHub App, utiliser :

```text
Homepage URL=https://nicocoquet.github.io/trinketa/depot-isbn/
Callback URL=https://trinketa-isbn-auth.onrender.com/auth/callback
```

Permissions de la GitHub App : `Contents: read and write`, `Pull requests: read
and write`, `Actions: read and write`. L’application doit être installée
uniquement sur `nicocoquet/trinketa`.

Le workflow d’analyse utilise la même GitHub App pour pousser sa proposition.
Ajouter dans le dépôt la variable `TRINKETA_APP_ID` et le secret
`TRINKETA_APP_PRIVATE_KEY`.

La liste `ALLOWED_USERS` constitue un premier filtre, mais le service vérifie
également que le compte connecté possède toujours un droit d’écriture réel sur
le dépôt. Pour ajouter un collaborateur, il faut donc à la fois l’inviter sur
GitHub et ajouter son identifiant à cette variable.
