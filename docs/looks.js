/* The eight looks of the channel, applied to the site as you scroll: each section can carry data-look="name" and the page blends into it
   (the colour tokens are registered custom properties, so the change is animated in looks.css). Pages without tagged sections keep obsidian.
   ?look=name forces one look (handy for checking a design). Everything is wrapped in try/catch. */
(function () {
  var NAMES = ['obsidian', 'ocean', 'indigo', 'cobalt', 'glass', 'paper', 'ice', 'blueprint'];
  var THEME = { obsidian: '#080B14', ocean: '#050E24', indigo: '#080B26', cobalt: '#0A1A5C', glass: '#060D22', paper: '#EDF3FF', ice: '#070D18', blueprint: '#0B2D6E' };
  var root = document.documentElement, current = '';

  function set(name) {
    if (!name || name === current || NAMES.indexOf(name) < 0) return;
    current = name;
    root.setAttribute('data-look', name);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', THEME[name]);
  }

  var forced = null;
  try { forced = new URLSearchParams(location.search).get('look'); } catch (e) {}
  set(forced && NAMES.indexOf(forced) > -1 ? forced : 'obsidian');
  if (forced && NAMES.indexOf(forced) > -1) return;

  function start() {
    var secs = [].slice.call(document.querySelectorAll('section[data-look]'));
    if (!secs.length || !('IntersectionObserver' in window)) return;
    // the section crossing the middle of the viewport decides the look
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) set(en.target.getAttribute('data-look')); });
    }, { rootMargin: '-50% 0px -49% 0px', threshold: 0 });
    secs.forEach(function (s) { io.observe(s); });
    window.addEventListener('scroll', function () { if (window.scrollY < 40) set('obsidian'); }, { passive: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
