/* Premium layer: a quiet icon tile above each section heading and on the stat and card blocks, from the real icon files in assets/icons (Lucide line glyphs). */
(function () {
  var UI = function (n) { return '<span class="ui" style="--i:url(assets/icons/ui-' + n + '.svg)" aria-hidden="true"></span>'; };
  function tile(n, cls) { return '<span class="tile ' + (cls || '') + '" aria-hidden="true">' + UI(n) + '</span>'; }
  function start() {
    var heads = { pipeline: 'workflow', series: 'layers', formats: 'film', cursor: 'mouse-pointer-2', looks: 'palette', games: 'clapperboard', gates: 'shield-check', llm: 'cpu', brand: 'sparkles', start: 'terminal', compliance: 'lock', output: 'film' };
    Object.keys(heads).forEach(function (id) {
      var h = document.querySelector('#' + id + ' .head'); if (h && !h.querySelector('.tile')) h.insertAdjacentHTML('afterbegin', tile(heads[id], 'lg'));
    });
    var each = function (sel, names, cls) { document.querySelectorAll(sel).forEach(function (el, i) { if (!el.querySelector(':scope > .tile') && !el.querySelector(':scope > .ico')) el.insertAdjacentHTML('afterbegin', tile(names[i % names.length], cls)); }); };
    each('.stat2', ['layers', 'film', 'clapperboard', 'sparkles', 'zap', 'gauge', 'chart-column', 'shield-check'], 'sm');
    each('.series.looks > .card', ['palette', 'zap', 'vote', 'gauge', 'captions', 'chart-column'], '');
    each('.series:not(.looks) > .card.main', ['film'], '');
    each('.comp > .card', ['shield-check', 'lock', 'eye-off'], '');
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.ccopy'); if (!b) return;
    var done = function () { var t = b.querySelector('span:last-child'); if (t) { t.textContent = 'Copied'; setTimeout(function () { t.textContent = 'Copy'; }, 1500); } };
    try { navigator.clipboard.writeText(b.getAttribute('data-copy')).then(done); } catch (err) {}
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
