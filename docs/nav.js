/* Pill nav + command palette (Cmd/Ctrl+K, "/"). Shared by every page; no dependencies. */
(function () {
  var local = !!document.getElementById('pipeline');
  var H = local ? '' : 'index.html';
  var path = location.pathname.split('/').pop() || 'index.html';
  var ic = {
    home: '<path d="M3 11l9-8 9 8v10H3z"/><path d="M9 21v-6h6v6"/>',
    layers: '<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>',
    film: '<rect x="2" y="3" width="20" height="18" rx="2"/><path d="M7 3v18M17 3v18M2 8h5M2 16h5M17 8h5M17 16h5"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    pad: '<rect x="2" y="7" width="20" height="11" rx="5"/><path d="M7 10v5M4.5 12.5h5M16 11.5h.01M18 13.5h.01"/>',
    palette: '<path d="M12 3a9 9 0 100 18c1.2 0 2-.8 2-1.8 0-.5-.2-.9-.5-1.2-.3-.4-.5-.7-.5-1.2 0-1 .8-1.8 1.8-1.8H17a4 4 0 004-4c0-4.4-4-8-9-8z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7" r="1"/><circle cx="15" cy="7" r="1"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 115 0c0 1.5-2.5 2-2.5 3.5M12 17h.01"/>',
    file: '<path d="M14 3H6a1 1 0 00-1 1v16a1 1 0 001 1h12a1 1 0 001-1V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
    play: '<rect x="2" y="5" width="20" height="14" rx="4"/><path d="M10 9l5 3-5 3z"/>',
    note: '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>'
  };
  function svg(n) { return '<svg viewBox="0 0 24 24" aria-hidden="true">' + ic[n] + '</svg>'; }

  var items = [
    { g: 'Sections', t: 'Overview', h: H + '#top', k: 'home hero start intro', i: 'home' },
    { g: 'Sections', t: 'Pipeline', h: H + '#pipeline', k: 'steps how it works gemini elevenlabs local voice backup remotion qa', i: 'layers' },
    { g: 'Sections', t: 'Series', h: H + '#series', k: 'content motion graphics minecraft', i: 'film' },
    { g: 'Sections', t: 'Formats', h: H + '#formats', k: 'myth tier versus evolution easter', i: 'grid' },
    { g: 'Sections', t: 'Games', h: H + '#games', k: 'roster steam game curiosities', i: 'pad' },
    { g: 'Sections', t: 'Brand look', h: H + '#brand', k: 'logo colors palette typography identity', i: 'palette' },
    { g: 'Sections', t: 'Updates', h: H + '#changelog', k: 'changelog news releases', i: 'clock' },
    { g: 'Sections', t: 'FAQ', h: H + '#faq', k: 'questions help data privacy', i: 'help' },
    { g: 'Pages', t: 'Terms of Service', h: 'terms.html', k: 'legal terms', i: 'file', cur: path === 'terms.html' },
    { g: 'Pages', t: 'Privacy Policy', h: 'privacy.html', k: 'legal data privacy gdpr', i: 'shield', cur: path === 'privacy.html' },
    { g: 'Channels', t: 'YouTube', hint: '@SiliconVerdictHQ', h: 'https://www.youtube.com/@SiliconVerdictHQ', k: 'watch videos shorts channel', i: 'play', ext: 1 },
    { g: 'Channels', t: 'TikTok', hint: '@siliconverdict', h: 'https://www.tiktok.com/@siliconverdict', k: 'watch videos channel', i: 'note', ext: 1 }
  ];

  var ov = document.createElement('div');
  ov.className = 'cmd-ov';
  ov.setAttribute('role', 'dialog');
  ov.setAttribute('aria-modal', 'true');
  ov.setAttribute('aria-label', 'Jump to');
  ov.innerHTML = '<div class="cmd"><div class="cmd-in">' + svg('search') +
    '<input type="text" placeholder="Jump to pipeline, games, FAQ…" aria-label="Jump to" autocomplete="off" spellcheck="false" role="combobox" aria-expanded="true" aria-controls="cmd-list">' +
    '<kbd>Esc</kbd></div><div class="cmd-list" id="cmd-list" role="listbox"></div>' +
    '<div class="cmd-foot"><span><kbd>↑</kbd><kbd>↓</kbd> move</span><span><kbd>↵</kbd> open</span><span><kbd>Esc</kbd> close</span></div></div>';
  document.body.appendChild(ov);
  var input = ov.querySelector('input'), list = ov.querySelector('.cmd-list');
  var shown = [], sel = 0, lastFocus = null;

  function render() {
    var q = input.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    shown = items.filter(function (it) {
      var hay = (it.t + ' ' + it.k + ' ' + (it.hint || '')).toLowerCase();
      return q.every(function (w) { return hay.indexOf(w) > -1; });
    });
    if (sel >= shown.length) sel = 0;
    if (!shown.length) { list.innerHTML = '<div class="cmd-empty">No matches. Try “faq” or “games”.</div>'; return; }
    var html = '', g = '';
    shown.forEach(function (it, n) {
      if (it.g !== g) { g = it.g; html += '<div class="cmd-g">' + g + '</div>'; }
      html += '<a class="cmd-i" role="option" id="cmd-' + n + '" aria-selected="' + (n === sel) + '" data-n="' + n + '" href="' + it.h + '"' +
        (it.ext ? ' target="_blank" rel="noopener"' : '') + '>' + svg(it.i) + '<span>' + it.t + '</span>' +
        (it.cur ? '<small>You are here</small>' : it.hint ? '<small>' + it.hint + '</small>' : '') + '</a>';
    });
    list.innerHTML = html;
    input.setAttribute('aria-activedescendant', 'cmd-' + sel);
  }
  function mark() {
    list.querySelectorAll('.cmd-i').forEach(function (a) {
      var on = +a.getAttribute('data-n') === sel;
      a.setAttribute('aria-selected', on);
      if (on) a.scrollIntoView({ block: 'nearest' });
    });
    input.setAttribute('aria-activedescendant', 'cmd-' + sel);
  }
  function open() {
    lastFocus = document.activeElement;
    ov.classList.add('open');
    document.documentElement.classList.add('cmd-lock');
    input.value = ''; sel = 0; render();
    setTimeout(function () { input.focus(); }, 0);
  }
  function close() {
    ov.classList.remove('open');
    document.documentElement.classList.remove('cmd-lock');
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  input.addEventListener('input', function () { sel = 0; render(); });
  ov.addEventListener('mousedown', function (e) { if (e.target === ov) close(); });
  list.addEventListener('mousemove', function (e) {
    var a = e.target.closest('.cmd-i');
    if (a && +a.getAttribute('data-n') !== sel) { sel = +a.getAttribute('data-n'); mark(); }
  });
  list.addEventListener('click', function (e) { if (e.target.closest('.cmd-i')) setTimeout(close, 0); });

  document.addEventListener('keydown', function (e) {
    var typing = /^(INPUT|TEXTAREA|SELECT)$/.test((document.activeElement || {}).tagName || '');
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); ov.classList.contains('open') ? close() : open(); return; }
    if (!ov.classList.contains('open')) {
      if (e.key === '/' && !typing && !e.metaKey && !e.ctrlKey) { e.preventDefault(); open(); }
      return;
    }
    if (e.key === 'Escape') { e.preventDefault(); close(); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); if (shown.length) { sel = (sel + 1) % shown.length; mark(); } }
    else if (e.key === 'ArrowUp') { e.preventDefault(); if (shown.length) { sel = (sel - 1 + shown.length) % shown.length; mark(); } }
    else if (e.key === 'Enter') { var a = list.querySelector('.cmd-i[aria-selected="true"]'); if (a) { e.preventDefault(); a.click(); } }
    else if (e.key === 'Tab') { e.preventDefault(); input.focus(); }
  });
  document.querySelectorAll('[data-cmdk]').forEach(function (b) { b.addEventListener('click', open); });
  var mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
  document.querySelectorAll('.cmdk kbd').forEach(function (k) { k.textContent = mac ? '⌘K' : 'Ctrl K'; });

  // highlight the pill link for the section on screen (home page only)
  if (local) {
    var links = [].slice.call(document.querySelectorAll('.pill-links a[href^="#"]'));
    var secs = links.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); });
    var tick = function () {
      var cur = -1, vh = window.innerHeight;
      secs.forEach(function (s, n) { if (s && s.getBoundingClientRect().top < vh * .4) cur = n; });
      links.forEach(function (a, n) { a.classList.toggle('active', n === cur); });
    };
    window.addEventListener('scroll', tick, { passive: true });
    tick();
  }
})();
