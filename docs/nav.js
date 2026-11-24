/* Pill nav, shared by every page: the phone menu (a full-screen list behind the menu button) and, on pages with in-page links,
   the link of the section on screen highlighted. No dependencies. */
(function () {
  var nav = document.querySelector('.navpill');
  if (!nav) return;
  var btn = nav.querySelector('.menu-btn');
  var menu = document.getElementById('menu');

  function setOpen(open) {
    if (!btn || !menu) return;
    btn.setAttribute('aria-expanded', String(open));
    btn.setAttribute('aria-label', open ? 'Close the menu' : 'Open the menu');
    document.documentElement.classList.toggle('menu-open', open);
    if (open) { var first = menu.querySelector('a'); if (first) first.focus(); }
  }
  if (btn && menu) {
    btn.addEventListener('click', function () { setOpen(btn.getAttribute('aria-expanded') !== 'true'); });
    menu.addEventListener('click', function (e) { if (e.target.closest('a')) setOpen(false); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && btn.getAttribute('aria-expanded') === 'true') { setOpen(false); btn.focus(); }
    });
    window.addEventListener('resize', function () { if (window.innerWidth > 900) setOpen(false); });
  }

  // highlight the link of the section on screen
  var links = [].slice.call(document.querySelectorAll('.pill-links a[href^="#"]'));
  if (!links.length) return;
  var secs = links.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); });
  var tick = function () {
    var cur = -1, vh = window.innerHeight;
    secs.forEach(function (s, n) { if (s && s.getBoundingClientRect().top < vh * .4) cur = n; });
    links.forEach(function (a, n) { a.classList.toggle('active', n === cur); });
  };
  window.addEventListener('scroll', tick, { passive: true });
  tick();
})();
