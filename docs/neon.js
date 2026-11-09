/* Neon icons: a glowing icon tile above every section heading and on the stat, card and ledger blocks. Progressive enhancement: the page reads the same without it. */
(function () {
  var I = {
    layers: '<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    gamepad: '<rect x="2" y="7" width="20" height="12" rx="5"/><path d="M7 11v4M5 13h4M16 12h.01M18 14h.01"/>',
    film: '<rect x="2" y="3" width="20" height="18" rx="2"/><path d="M7 3v18M17 3v18M2 8h5M2 16h5M17 8h5M17 16h5"/>',
    sparkle: '<path d="M12 3l2.2 6.3L21 12l-6.8 2.7L12 21l-2.2-6.3L3 12l6.8-2.7z"/>',
    gauge: '<path d="M4 18a9 9 0 1 1 16 0"/><path d="M12 14l4-5"/><circle cx="12" cy="14" r="1.2"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
    palette: '<path d="M12 3a9 9 0 100 18c1.2 0 2-.8 2-1.8 0-.5-.2-.9-.5-1.2-.3-.4-.5-.7-.5-1.2 0-1 .8-1.8 1.8-1.8H17a4 4 0 004-4c0-4.4-4-8-9-8z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7" r="1"/><circle cx="15" cy="7" r="1"/>',
    bolt: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    vote: '<path d="M4 5h16v11H9l-5 4z"/><path d="M9 10l2 2 4-4"/>',
    type: '<path d="M4 7V5h16v2M12 5v14M9 19h6"/>',
    chart: '<path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/>',
    rocket: '<path d="M5 15c-1 3-1 5-1 5s2 0 5-1"/><path d="M14 4c3 0 6 3 6 6-3 3-5 5-8 6l-4-4c1-3 3-5 6-8z"/><circle cx="15" cy="9" r="1.5"/>',
    trophy: '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M7 6H4v2a3 3 0 0 0 3 3M17 6h3v2a3 3 0 0 1-3 3"/>',
    lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    eyeoff: '<path d="M3 3l18 18M10.6 5.1A9.7 9.7 0 0 1 12 5c5 0 9 4 10 7a11 11 0 0 1-3 4M6.6 6.7A11 11 0 0 0 2 12c1 3 5 7 10 7 1.5 0 2.8-.3 4-.9"/>',
    pointer: '<path d="M5 3l14 7-6 2-2 6z"/>',
    cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    folder: '<path d="M3 6h6l2 3h10v11H3z"/>',
    terminal: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M13 15h4"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 115 0c0 1.5-2.5 2-2.5 3.5M12 17h.01"/>',
    stack: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    flow: '<circle cx="5" cy="6" r="2.5"/><circle cx="5" cy="18" r="2.5"/><circle cx="19" cy="12" r="2.5"/><path d="M7.5 6h4a4 4 0 0 1 4 4M7.5 18h4a4 4 0 0 0 4-4"/>',
    swatch: '<circle cx="9" cy="12" r="6"/><circle cx="15" cy="12" r="6"/>',
    play: '<circle cx="12" cy="12" r="9"/><path d="M10 8.5l5.5 3.5-5.5 3.5z"/>'
  };
  function mk(n, cls) { return '<span class="' + (cls || 'ico') + '" aria-hidden="true"><svg viewBox="0 0 24 24">' + (I[n] || I.sparkle) + '</svg></span>'; }
  function start() {
    var heads = { pipeline: 'flow', series: 'layers', formats: 'grid', cursor: 'pointer', looks: 'palette', games: 'gamepad', gates: 'shield', llm: 'cpu', stack: 'stack', brand: 'swatch', map: 'folder', start: 'terminal', changelog: 'sparkle', faq: 'help', compliance: 'lock', output: 'film' };
    Object.keys(heads).forEach(function (id) {
      var h = document.querySelector('#' + id + ' .head'); if (h && !h.querySelector('.hico')) h.insertAdjacentHTML('afterbegin', mk(heads[id], 'ico hico'));
    });
    var each = function (sel, names, cls) { document.querySelectorAll(sel).forEach(function (el, i) { if (!el.querySelector(':scope > .ico')) el.insertAdjacentHTML('afterbegin', mk(names[i % names.length], cls)); }); };
    each('.stat2', ['layers', 'grid', 'gamepad', 'film', 'sparkle', 'gauge', 'clock', 'shield'], 'ico sm');
    each('.ledger > div', ['gamepad', 'calendar', 'rocket', 'trophy'], 'ico sm');
    each('.series.looks > .card', ['palette', 'bolt', 'vote', 'gauge', 'type', 'chart'], 'ico');
    each('.series:not(.looks) > .card.main', ['film'], 'ico');
    each('.comp > .card', ['shield', 'lock', 'eyeoff'], 'ico');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
