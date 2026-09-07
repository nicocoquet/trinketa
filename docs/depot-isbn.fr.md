<div class="isbn-page">
  <header class="isbn-intro">
    <p class="isbn-kicker">Bibliothèque · Ajout d’ouvrages</p>
    <h1>Ajouter des livres à la bibliothèque</h1>
    <p>Photographiez les codes-barres ISBN : Trinketa se charge de préparer les fiches bibliographiques.</p>
  </header>

  <div class="isbn-deposit" data-isbn-deposit>
    <section class="isbn-session" data-session-state="disconnected">
      <span class="isbn-session-dot" aria-hidden="true"></span>
      <span data-session-label>Identifiez-vous pour commencer</span>
      <button type="button" class="isbn-button" data-login>Continuer avec GitHub</button>
      <button type="button" class="isbn-button isbn-button-secondary" data-logout hidden>Se déconnecter</button>
    </section>

    <section class="isbn-panel" aria-labelledby="isbn-upload-title">
      <p class="isbn-step">Étape 1</p>
      <h2 id="isbn-upload-title">Envoyer les photographies</h2>
      <p>Ajoutez jusqu’à dix photographies nettes. Les formats courants, y compris HEIC, sont acceptés et automatiquement préparés pour la bibliothèque.</p>
      <div class="isbn-drop" data-drop role="button" tabindex="0" aria-label="Sélectionner ou déposer des photographies ISBN">
        <span class="isbn-camera" aria-hidden="true">▣</span>
        <strong>Glissez vos photographies ici</strong>
        <span>ou choisissez-les sur votre appareil</span>
        <input type="file" data-file-input accept=".jpg,.jpeg,.png,.webp,.heic,.heif,image/jpeg,image/png,image/webp,image/heic,image/heif" multiple hidden>
        <button type="button" class="isbn-button isbn-button-secondary" data-select>Choisir des photographies</button>
      </div>
      <ul class="isbn-files" data-files hidden></ul>
      <aside class="isbn-notice">
        <strong>Pour le moment</strong>
        <span>les photographies déposées sont visibles dans le dépôt public du projet. Leurs métadonnées personnelles et leur éventuelle position GPS sont supprimées automatiquement.</span>
      </aside>
      <button type="button" class="isbn-button isbn-submit" data-upload disabled>Envoyer les photographies</button>
      <p class="isbn-status" data-upload-status role="status" aria-live="polite">Connectez-vous pour commencer.</p>
      <div class="isbn-result" data-upload-result hidden>
        <strong>Les photographies ont bien été envoyées.</strong>
        <a href="#" data-pr-link target="_blank" rel="noopener">Ouvrir et valider l’ajout <span>→</span></a>
        <p>Après validation, elles apparaîtront dans la file d’analyse ci-dessous.</p>
      </div>
    </section>

    <section class="isbn-panel" aria-labelledby="isbn-analysis-title">
      <p class="isbn-step">Étape 2</p>
      <h2 id="isbn-analysis-title">Préparer les fiches bibliographiques</h2>
      <p class="isbn-queue"><strong data-queue-count>—</strong> photographie(s) en attente d’analyse.</p>
      <p>Trinketa lit les ISBN, recherche les informations bibliographiques et prépare les nouvelles fiches. Si un doute subsiste, la photographie est simplement mise de côté pour vérification.</p>
      <button type="button" class="isbn-button" data-analyse disabled>Analyser les photographies</button>
      <p class="isbn-status" data-analysis-status role="status" aria-live="polite"></p>
      <a class="isbn-actions-link" href="https://github.com/nicocoquet/trinketa/actions/workflows/analyse-isbn.yml" target="_blank" rel="noopener">Voir l’historique des traitements <span>→</span></a>
    </section>
  </div>

  <footer class="isbn-help">
    <strong>Pour une bonne reconnaissance</strong>
    <p>Cadrez le code-barres bien droit, avec suffisamment de lumière et sans reflet. Évitez tout élément personnel autour du livre.</p>
  </footer>
</div>
