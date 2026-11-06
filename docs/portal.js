(function () {
  var RM = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // count-up
  function count(el) {
    var end = parseFloat(el.dataset.count), dec = (el.dataset.count.split('.')[1] || '').length;
    var pre = el.dataset.pre || '', suf = el.dataset.suf || '';
    if (RM) { el.textContent = pre + end.toFixed(dec) + suf; return; }
    var t0 = performance.now(), dur = 1600;
    (function f(t) {
      var p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 4);
      el.textContent = pre + (end * e).toFixed(dec) + suf;
      if (p < 1) requestAnimationFrame(f);
    })(t0);
  }
  if ('IntersectionObserver' in window) {
    var co = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { count(e.target); co.unobserve(e.target); } });
    }, { threshold: .5 });
    $$('[data-count]').forEach(function (el) { co.observe(el); });
  } else { $$('[data-count]').forEach(count); }

  // hero phone: 3D tilt + slide cycle + safe zone toggle
  var phone = $('.phone');
  if (phone && !RM) {
    var wrap = $('.phone-wrap');
    wrap.addEventListener('mousemove', function (e) {
      var r = wrap.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
      phone.style.transform = 'rotateY(' + (x * 24) + 'deg) rotateX(' + (-y * 14) + 'deg)';
    });
    wrap.addEventListener('mouseleave', function () { phone.style.transform = ''; });
  }
  var slides = $$('.slide'), si = 0;
  if (slides.length) {
    slides[0].classList.add('on');
    setInterval(function () {
      slides[si].classList.remove('on'); si = (si + 1) % slides.length; slides[si].classList.add('on');
    }, 2600);
  }
  var szb = $('#sztoggle');
  if (szb) szb.addEventListener('click', function () {
    phone.classList.toggle('nosz');
    szb.textContent = phone.classList.contains('nosz') ? 'Show safe zones' : 'Hide safe zones';
  });

  // parallax orbs + sticky pieces
  var orbs = $$('.orb');
  // timeline
  var tl = $('.tl'), fill = $('.tl-fill'), steps = $$('.step');
  // side dots + totop
  var secs = $$('main section[id]'), dots = $$('.dots a'), top = $('.totop');
  function onScroll() {
    var y = window.scrollY, vh = window.innerHeight;
    if (!RM) orbs.forEach(function (o, i) { o.style.transform = 'translateY(' + (y * (0.05 + i * 0.04)) + 'px)'; });
    if (tl && fill) {
      var r = tl.getBoundingClientRect();
      var p = Math.max(0, Math.min(1, (vh * .55 - r.top) / r.height));
      fill.style.height = (p * 100) + '%';
      steps.forEach(function (s) {
        var b = s.getBoundingClientRect();
        s.classList.toggle('on', b.top < vh * .6);
      });
    }
    var cur = '';
    secs.forEach(function (s) { if (s.getBoundingClientRect().top < vh * .4) cur = s.id; });
    dots.forEach(function (d) { d.classList.toggle('on', d.getAttribute('href') === '#' + cur); });
    if (top) top.classList.toggle('show', y > 700);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  onScroll();
  if (top) top.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: RM ? 'auto' : 'smooth' }); });

  // mobile menu
  var bg = $('.burger'), nl = $('.nav-links.long');
  if (bg) {
    bg.addEventListener('click', function () { nl.classList.toggle('open'); });
    $$('a', nl).forEach(function (a) { a.addEventListener('click', function () { nl.classList.remove('open'); }); });
  }

  // tabs
  $$('.tabs').forEach(function (tb) {
    var root = tb.parentNode;
    $$('.tab', tb).forEach(function (t) {
      t.addEventListener('click', function () {
        $$('.tab', tb).forEach(function (x) { x.classList.remove('on'); });
        $$('.panel', root).forEach(function (x) { x.classList.remove('on'); });
        t.classList.add('on');
        $('#' + t.dataset.t, root).classList.add('on');
      });
    });
  });

  // cursor demo
  var stage = $('.cur-stage');
  if (stage) {
    var cur = $('.cur', stage), rip = $('.ripple', stage);
    var air = $('.tgl.air', stage), wifi = $('.tgl.wifi', stage), bt = $('.tgl.bt', stage);
    function at(el, dx, dy) {
      var s = stage.getBoundingClientRect(), r = el.getBoundingClientRect();
      return [r.left - s.left + r.width * (dx || .85), r.top - s.top + r.height * (dy || .5)];
    }
    function move(p) { cur.style.transform = 'translate(' + p[0] + 'px,' + p[1] + 'px)'; }
    function click(p) {
      cur.classList.add('click'); rip.style.left = p[0] + 'px'; rip.style.top = p[1] + 'px';
      rip.classList.remove('go'); void rip.offsetWidth; rip.classList.add('go');
      setTimeout(function () { cur.classList.remove('click'); }, 160);
    }
    var running = false;
    function wait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
    async function loop() {
      if (running) return; running = true;
      while (true) {
        if (RM) break;
        air.classList.remove('on2'); air.classList.add('off'); wifi.classList.remove('off'); bt.classList.remove('off');
        move([stage.clientWidth * .5, stage.clientHeight * .9]); await wait(900);
        var p = at(wifi); move(p); await wait(1100); click(p); wifi.classList.add('off'); await wait(500);
        p = at(bt); move(p); await wait(1100); click(p); bt.classList.add('off'); await wait(900);
        wifi.classList.remove('off'); bt.classList.remove('off');
        p = at(air); move(p); await wait(1100); click(p); air.classList.add('on2'); air.classList.remove('off');
        await wait(350); wifi.classList.add('off'); bt.classList.add('off');
        await wait(2600);
      }
    }
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) { if (es[0].isIntersecting) loop(); }, { threshold: .4 }).observe(stage);
    } else loop();
  }

  // copy buttons
  $$('.cp').forEach(function (b) {
    b.addEventListener('click', function () {
      var t = b.closest('.term').querySelector('pre').innerText;
      try { navigator.clipboard.writeText(t); b.textContent = 'Copied ✓'; setTimeout(function () { b.textContent = 'Copy'; }, 1500); } catch (e) {}
    });
  });
})();
