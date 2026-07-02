/* =========================================================================
   newsletter.js — Capture e-mail "1000e but" pour to1000.com
   Motif identique à ads.js : DORMANT tant que rien n'est configuré.

   ── COMMENT ACTIVER (2 lignes à décommenter) ────────────────────────────
   Dans index.html et news.html, juste AVANT <script src="/newsletter.js">,
   se trouve ce bloc :

       <script>
         // window.NEWSLETTER_FORM_ACTION = 'https://buttondown.com/api/emails/embed-subscribe/TON_COMPTE';
         // window.NEWSLETTER_EMAIL_FIELD = 'email'; // nom du champ attendu par l'ESP
       </script>

   1. Crée un compte ESP (Buttondown, MailerLite, Brevo…) et récupère
      l'URL d'action de son formulaire "embed" :
        - Buttondown  : https://buttondown.com/api/emails/embed-subscribe/<username>
                        (champ : "email")
        - MailerLite  : URL d'action du formulaire embed (champ : "fields[email]")
        - Brevo       : URL d'action du formulaire (champ : "EMAIL")
   2. Décommente les 2 lignes ci-dessus en remplaçant l'URL (et le nom du
      champ si différent de "email").

   Tant que NEWSLETTER_FORM_ACTION est vide/absente, la section reste
   MASQUÉE (attribut hidden) : aucune promesse mensongère à l'utilisateur,
   aucun script tiers chargé.
   ========================================================================= */
(function () {
  'use strict';

  var ACTION = window.NEWSLETTER_FORM_ACTION || '';
  var FIELD = window.NEWSLETTER_EMAIL_FIELD || 'email';

  if (!ACTION) return; // pas d'ESP configuré → les sections .nl-section restent hidden

  function boot() {
    document.querySelectorAll('.nl-section').forEach(function (sec) {
      var form = sec.querySelector('form.nl-form');
      var input = sec.querySelector('input[type="email"]');
      var ok = sec.querySelector('.nl-ok');
      if (!form || !input) return;

      form.setAttribute('action', ACTION);
      form.setAttribute('method', 'post');
      form.setAttribute('target', '_blank'); // la confirmation ESP s'ouvre à part
      input.setAttribute('name', FIELD);

      form.addEventListener('submit', function () {
        // POST natif vers l'ESP (nouvel onglet) ; côté to1000 on confirme sobrement
        setTimeout(function () {
          form.style.display = 'none';
          if (ok) ok.style.display = 'block';
          try { input.value = ''; } catch (e) {}
        }, 150);
      });

      sec.removeAttribute('hidden');
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
