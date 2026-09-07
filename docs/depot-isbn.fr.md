<div class="isbn-page">
  <header class="isbn-intro">
    <p class="isbn-kicker">Bibliothèque · Ajout d’ouvrages</p>
    <h1>Dépôt par ISBN</h1>
    <p>Photographiez les codes-barres ISBN : Baboulinet se charge de préparer les fiches bibliographiques.</p>
  </header>

  <div class="isbn-deposit" data-isbn-deposit>
    <section class="isbn-session" data-session-state="disconnected">
      <span class="isbn-github-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24"><path d="M12 .7a11.5 11.5 0 0 0-3.64 22.41c.58.11.79-.25.79-.56v-2.23c-3.22.7-3.9-1.37-3.9-1.37-.52-1.34-1.28-1.69-1.28-1.69-1.05-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.57-.29-5.27-1.28-5.27-5.69 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.16 1.18a10.9 10.9 0 0 1 5.75 0c2.19-1.49 3.16-1.18 3.16-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.83 1.19 3.09 0 4.42-2.71 5.39-5.29 5.68.42.36.79 1.06.79 2.14v3.26c0 .31.21.68.8.56A11.5 11.5 0 0 0 12 .7Z"/></svg>
      </span>
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
      <p>Baboulinet lit les ISBN, recherche les informations bibliographiques et prépare les nouvelles fiches. Si un doute subsiste, la photographie est simplement mise de côté pour vérification.</p>
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
