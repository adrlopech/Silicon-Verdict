/* Pause control for every looping animation (orbit, rings, orbs, marquee): one state, any button with .pausebtn toggles it. */
(function () {
  var root = document.documentElement;
  function sync() {
    var p = root.classList.contains('motion-paused');
    document.querySelectorAll('.pausebtn').forEach(function (b) {
      b.setAttribute('aria-pressed', String(p));
      b.textContent = b.classList.contains('global') ? (p ? 'Play motion' : 'Pause motion') : (p ? 'Play' : 'Pause');
      b.setAttribute('aria-label', p ? 'Play animations' : 'Pause animations');
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.pausebtn');
    if (!b) return;
    root.classList.toggle('motion-paused');
    sync();
  });
  sync();
})();
