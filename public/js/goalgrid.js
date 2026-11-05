/* goalgrid.js — 1000 points, un par but. Les buts marqués sont pleins,
   groupés par équipe ; ceux du Portugal en rouge (définitifs depuis le
   5 nov. 2026) ; les buts qui manquent restent vides.
   Usage : To1000Grid.render(el, goals)  — goals = stats.json.goals */
(function () {
  'use strict';
  // Totaux par équipe, ordre chronologique d'arrivée. Al Nassr = le reste,
  // pour suivre le compteur live sans toucher à ce fichier.
  var FIXED = [
    { key: 'sporting', n: 5 },
    { key: 'portugal', n: 146 },
    { key: 'manutd', n: 145 },
    { key: 'real', n: 450 },
    { key: 'juve', n: 101 }
  ];
  function split(goals) {
    var fixed = FIXED.reduce(function (s, t) { return s + t.n; }, 0);
    return FIXED.concat([{ key: 'nassr', n: Math.max(0, goals - fixed) }]);
  }
  function render(el, goals, target) {
    if (!el || typeof goals !== 'number') return;
    target = target || 1000;
    var parts = split(goals), html = '', i = 0;
    parts.forEach(function (p) {
      for (var k = 0; k < p.n && i < target; k++, i++) {
        html += '<i class="g-' + p.key + (i === goals - 1 ? ' g-last' : '') + '"></i>';
      }
    });
    for (; i < target; i++) html += '<i class="g-todo"></i>';
    el.innerHTML = html;
    el.setAttribute('aria-valuenow', goals);
  }
  window.To1000Grid = { render: render, split: split };
})();
