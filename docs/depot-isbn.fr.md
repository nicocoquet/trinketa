# Dépôt de photographies ISBN

Cette interface alimente la file bibliographique de Trinketa. La connexion
GitHub est obligatoire et réservée aux collaborateurs autorisés.

<div class="isbn-deposit" data-isbn-deposit>
  <section class="isbn-session" data-session-state="disconnected">
    <span class="isbn-session-dot" aria-hidden="true"></span>
    <span data-session-label>Connexion GitHub requise</span>
    <button type="button" class="isbn-button" data-login>Se connecter avec GitHub</button>
    <button type="button" class="isbn-button isbn-button-secondary" data-logout hidden>Se déconnecter</button>
  </section>

  <section class="isbn-panel" aria-labelledby="isbn-upload-title">
    <p class="isbn-step">01 · Dépôt</p>
    <h2 id="isbn-upload-title">Ajouter des photographies</h2>
    <p>Déposez jusqu’à dix photographies de codes-barres. Elles seront converties en JPEG, réorientées et débarrassées de leurs métadonnées avant la création de la pull request.</p>
    <div class="isbn-drop" data-drop role="button" tabindex="0" aria-label="Sélectionner ou déposer des photographies ISBN">
      <span class="isbn-camera" aria-hidden="true">▣</span>
      <strong>Glissez les images ici</strong>
      <span>ou sélectionnez-les sur votre appareil</span>
      <input type="file" data-file-input accept=".jpg,.jpeg,.png,.webp,.heic,.heif,image/jpeg,image/png,image/webp,image/heic,image/heif" multiple hidden>
      <button type="button" class="isbn-button isbn-button-secondary" data-select>Sélectionner</button>
    </div>
    <ul class="isbn-files" data-files hidden></ul>
    <label class="isbn-public" data-public hidden>
      <input type="checkbox" data-confirm>
      <span>Je comprends que ces photographies seront visibles publiquement dans le dépôt GitHub après fusion de la pull request.</span>
    </label>
    <button type="button" class="isbn-button isbn-submit" data-upload disabled>Créer la pull request de dépôt</button>
    <p class="isbn-status" data-upload-status role="status" aria-live="polite">Connectez-vous avec GitHub pour commencer.</p>
    <div class="isbn-result" data-upload-result hidden>
      <strong>La proposition de dépôt est prête.</strong>
      <a href="#" data-pr-link target="_blank" rel="noopener">Ouvrir la pull request <span>→</span></a>
      <p>Fusionnez-la lorsque le contrôle <code>deploy</code> est vert. Les images apparaîtront ensuite dans la file à traiter.</p>
    </div>
  </section>

  <section class="isbn-panel" aria-labelledby="isbn-analysis-title">
    <p class="isbn-step">02 · Analyse</p>
    <h2 id="isbn-analysis-title">Lancer l’analyse bibliographique</h2>
    <p><strong data-queue-count>—</strong> photographie(s) actuellement présente(s) dans <code>a_traiter/</code>.</p>
    <p>Le traitement lit les ISBN, interroge les sources bibliographiques et ouvre une nouvelle pull request. Les cas ambigus sont dirigés vers <code>a_verifier/</code>.</p>
    <button type="button" class="isbn-button" data-analyse disabled>Lancer l’analyse de la file ISBN</button>
    <p class="isbn-status" data-analysis-status role="status" aria-live="polite"></p>
    <a class="isbn-actions-link" href="https://github.com/nicocoquet/trinketa/actions/workflows/analyse-isbn.yml" target="_blank" rel="noopener">Consulter les traitements sur GitHub <span>→</span></a>
  </section>
</div>

Les photographies doivent montrer nettement le code-barres ISBN. Évitez tout
élément personnel dans le cadrage, puisque le dépôt et le site sont publics.
