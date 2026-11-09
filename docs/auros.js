/* Particle sphere behind the hero: a rotating orb of dots in the page accent (tracks the colour tokens), pale at the edges. Static with reduced motion. */
(function () {
  var cv = document.querySelector('canvas.sphere');
  if (!cv || !cv.getContext) return;
  var ctx = cv.getContext('2d'), dpr = Math.min(2, window.devicePixelRatio || 1), W = 0, H = 0, pts = [];
  var N = innerWidth < 700 ? 520 : 1100, G = Math.PI * (3 - Math.sqrt(5));
  for (var i = 0; i < N; i++) { var y = 1 - (i / (N - 1)) * 2, r = Math.sqrt(1 - y * y), th = G * i; pts.push([Math.cos(th) * r, y, Math.sin(th) * r, 0.6 + Math.random() * 0.9]); }
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var ang = 0.6, visible = true;
  function size() { var b = cv.getBoundingClientRect(); W = b.width; H = b.height; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); }
  function rgb() {
    var v = getComputedStyle(document.documentElement).getPropertyValue('--ac').trim().split(',').map(Number);
    return v.length === 3 && !v.some(isNaN) ? v : [111, 214, 240];
  }
  function draw() {
    ctx.clearRect(0, 0, W, H);
    var c = rgb(), R = Math.min(W * 0.5, H * 0.52, 640), cx = W / 2, cy = H * 0.5, tilt = 0.38, ct = Math.cos(tilt), st = Math.sin(tilt), ca = Math.cos(ang), sa = Math.sin(ang);
    for (var k = 0; k < pts.length; k++) {
      var p = pts[k], x = p[0] * ca + p[2] * sa, z = -p[0] * sa + p[2] * ca, y2 = p[1] * ct - z * st, z2 = p[1] * st + z * ct;
      var depth = (z2 + 1) / 2, s = 1 / (1.9 - z2 * 0.55), px = cx + x * R * s * 1.5, py = cy + y2 * R * s * 1.5;
      var edge = 1 - Math.abs(z2), t = Math.max(0, Math.min(1, edge * 0.9 + (1 - depth) * 0.25));
      var rr = c[0] + (255 - c[0]) * t * 0.7, gg = c[1] + (255 - c[1]) * t * 0.7, bb = c[2] + (255 - c[2]) * t * 0.7;
      ctx.fillStyle = 'rgba(' + (rr | 0) + ',' + (gg | 0) + ',' + (bb | 0) + ',' + (0.16 + depth * 0.62).toFixed(3) + ')';
      ctx.beginPath(); ctx.arc(px, py, p[3] * (0.6 + depth * 1.2), 0, 6.2832); ctx.fill();
    }
  }
  function loop() { if (visible) { ang += 0.0022; draw(); } requestAnimationFrame(loop); }
  size(); draw();
  window.addEventListener('resize', function () { size(); draw(); });
  if ('IntersectionObserver' in window) new IntersectionObserver(function (e) { visible = e[0].isIntersecting; }).observe(cv);
  if (!reduce) requestAnimationFrame(loop);
})();
