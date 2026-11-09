/* The eight looks of the channel, applied to the site. Load in <head> (no flash); the picker is injected once the page exists.
   Choice: ?look=name > localStorage > the default (obsidian). Everything is wrapped in try/catch: storage can be blocked. */
(function () {
  var LOOKS = [
    ['obsidian', 'Obsidian', 'deep glow', '#080B14', '#6FD6F0'],
    ['ocean', 'Ocean', 'aurora', '#050E24', '#7CCBFF'],
    ['indigo', 'Indigo', 'periwinkle', '#080B26', '#A3B6FF'],
    ['cobalt', 'Cobalt', 'bold mesh', '#0A1A5C', '#A9E9FF'],
    ['glass', 'Glass', 'frosted', '#060D22', '#8CCFFF'],
    ['paper', 'Paper', 'light', '#EDF3FF', '#1C5FE8'],
    ['ice', 'Ice', 'monochrome', '#070D18', '#DCEBFF'],
    ['blueprint', 'Blueprint', 'technical', '#0B2D6E', '#B9E4FF']
  ];
  var names = LOOKS.map(function (l) { return l[0]; });
  var KEY = 'sv-look';
  var root = document.documentElement;

  function read() {
    try {
      var q = new URLSearchParams(location.search).get('look');
      if (q && names.indexOf(q) > -1) return q;
    } catch (e) {}
    try {
      var s = localStorage.getItem(KEY);
      if (s && names.indexOf(s) > -1) return s;
    } catch (e) {}
    return 'obsidian';
  }

  function apply(name, save) {
    root.setAttribute('data-look', name);
    var l = LOOKS[names.indexOf(name)];
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', l[3]);
    if (save) { try { localStorage.setItem(KEY, name); } catch (e) {} }
    var btn = document.querySelector('.lookbtn span');
    if (btn) btn.textContent = l[1];
    document.querySelectorAll('.lookmenu button').forEach(function (b) { b.setAttribute('aria-checked', String(b.dataset.look === name)); });
    document.querySelectorAll('.lookgrid button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.look === name)); });
  }

  function swatch(l) { return '<span class="sw8" style="background:linear-gradient(135deg,' + l[3] + ' 45%,' + l[4] + ')"></span>'; }

  function build() {
    var nav = document.querySelector('.navpill');
    if (nav && !nav.querySelector('.lookpick')) {
      var wrap = document.createElement('div');
      wrap.className = 'lookpick';
      wrap.innerHTML = '<button class="lookbtn" type="button" aria-haspopup="true" aria-expanded="false" aria-label="Choose a look"><i></i><span>Look</span></button>' +
        '<div class="lookmenu" role="menu" aria-label="Looks">' + LOOKS.map(function (l) {
          return '<button type="button" role="menuitemradio" data-look="' + l[0] + '" aria-checked="false">' + swatch(l) + l[1] + '<small>' + l[2] + '</small></button>';
        }).join('') + '</div>';
      var cta = nav.querySelector('.cta-pill');
      nav.insertBefore(wrap, cta || null);
      var btn = wrap.querySelector('.lookbtn'), menu = wrap.querySelector('.lookmenu');
      function close() { menu.classList.remove('on'); btn.setAttribute('aria-expanded', 'false'); }
      btn.addEventListener('click', function (e) { e.stopPropagation(); var on = menu.classList.toggle('on'); btn.setAttribute('aria-expanded', String(on)); });
      menu.addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) { apply(b.dataset.look, true); close(); } });
      document.addEventListener('click', close);
      document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
    }
    var grid = document.querySelector('.lookgrid');
    if (grid && !grid.children.length) {
      grid.innerHTML = LOOKS.map(function (l) { return '<button type="button" data-look="' + l[0] + '" aria-pressed="false">' + swatch(l) + l[1] + '</button>'; }).join('');
      grid.addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) apply(b.dataset.look, true); });
    }
    apply(read(), false);
  }

  apply(read(), false);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build); else build();
})();
