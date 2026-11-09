/* The eight looks of the channel, blended as you scroll. The backdrop (looks.css) is one fixed mix of all of them; only its tint moves.
   Each <section data-look="name"> has a look; the colour tokens glide between the looks of the sections around the middle of the viewport
   (continuous, eased twice: by position and by a slow follow), so there is never a visible switch. The light look (paper) stays out of the flow.
   Pages without tagged sections keep obsidian. ?look=name pins a look for checking a design (CSS tokens only, no blending). */
(function () {
  var NAMES = ['obsidian', 'ocean', 'indigo', 'cobalt', 'glass', 'paper', 'ice', 'blueprint'];
  var THEME = { obsidian: '#080B14', ocean: '#050E24', indigo: '#080B26', cobalt: '#0A1A5C', glass: '#060D22', paper: '#EDF3FF', ice: '#070D18', blueprint: '#0B2D6E' };
  // dark looks only: page colour, accent, second accent, card base (rgb)
  var P = {
    obsidian: { bg: [8, 11, 20], ac: [111, 214, 240], ac2: [63, 140, 245], card: [16, 25, 44] },
    ocean: { bg: [5, 14, 36], ac: [124, 203, 255], ac2: [47, 107, 255], card: [10, 26, 60] },
    indigo: { bg: [8, 11, 38], ac: [163, 182, 255], ac2: [76, 85, 240], card: [17, 20, 64] },
    cobalt: { bg: [10, 26, 92], ac: [169, 233, 255], ac2: [91, 151, 255], card: [20, 44, 128] },
    glass: { bg: [6, 13, 34], ac: [140, 207, 255], ac2: [88, 119, 255], card: [16, 28, 62] },
    ice: { bg: [7, 13, 24], ac: [220, 235, 255], ac2: [134, 169, 216], card: [18, 28, 46] },
    blueprint: { bg: [11, 45, 110], ac: [185, 228, 255], ac2: [92, 140, 255], card: [14, 56, 132] }
  };
  var root = document.documentElement;

  function pin(name) {
    root.setAttribute('data-look', name);
    var m = document.querySelector('meta[name="theme-color"]');
    if (m) m.setAttribute('content', THEME[name]);
  }

  var forced = null;
  try { forced = new URLSearchParams(location.search).get('look'); } catch (e) {}
  if (forced && NAMES.indexOf(forced) > -1) { pin(forced); return; }
  pin('obsidian');

  var mix = function (a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; };
  var rgb = function (c) { return 'rgb(' + Math.round(c[0]) + ',' + Math.round(c[1]) + ',' + Math.round(c[2]) + ')'; };
  var tri = function (c) { return Math.round(c[0]) + ',' + Math.round(c[1]) + ',' + Math.round(c[2]); };
  var ease = function (t) { return t * t * (3 - 2 * t); };
  var WHITE = [255, 255, 255];

  function paint(s) {
    var st = root.style;
    var teal = mix(s.ac, s.ac2, .5), blue2 = mix(s.ac2, WHITE, .22), card2 = mix(s.card, WHITE, .06);
    st.setProperty('--bg', rgb(s.bg)); st.setProperty('--bgc', tri(s.bg));
    st.setProperty('--ac', tri(s.ac)); st.setProperty('--ac2', tri(s.ac2)); st.setProperty('--cardc', tri(s.card));
    st.setProperty('--cyan', rgb(s.ac)); st.setProperty('--green', rgb(s.ac)); st.setProperty('--blue', rgb(s.ac2)); st.setProperty('--blue2', rgb(blue2)); st.setProperty('--teal', rgb(teal));
    st.setProperty('--card', 'rgba(' + tri(s.card) + ',.55)'); st.setProperty('--card-2', 'rgba(' + tri(card2) + ',.62)');
    st.setProperty('--line-c', 'rgba(' + tri(s.ac) + ',.22)');
    st.setProperty('--o1', rgb(s.ac2)); st.setProperty('--o2', rgb(s.ac)); st.setProperty('--o3', rgb(teal));
  }

  function start() {
    var secs = [].slice.call(document.querySelectorAll('section[data-look]')).filter(function (s) { return P[s.getAttribute('data-look')]; });
    if (!secs.length) return;
    var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    var marks = [], cur = JSON.parse(JSON.stringify(P.obsidian));

    function measure() {
      marks = secs.map(function (s) { var r = s.getBoundingClientRect(); return { y: r.top + window.scrollY + r.height / 2, p: P[s.getAttribute('data-look')] }; });
    }
    function target() {
      var y = window.scrollY + innerHeight * .5, i = 0;
      if (y <= marks[0].y) return marks[0].p;
      if (y >= marks[marks.length - 1].y) return marks[marks.length - 1].p;
      while (i < marks.length - 2 && y > marks[i + 1].y) i++;
      var a = marks[i], b = marks[i + 1], t = ease((y - a.y) / (b.y - a.y));
      return { bg: mix(a.p.bg, b.p.bg, t), ac: mix(a.p.ac, b.p.ac, t), ac2: mix(a.p.ac2, b.p.ac2, t), card: mix(a.p.card, b.p.card, t) };
    }
    var last = 0;
    function frame(now) {
      var tg = target(), k = reduce ? 1 : Math.min(1, (now - (last || now) + 16) / 16 * .035); // slow follow: ~1.5 s to settle
      last = now;
      var d = 0;
      ['bg', 'ac', 'ac2', 'card'].forEach(function (n) { for (var j = 0; j < 3; j++) d = Math.max(d, Math.abs(cur[n][j] - tg[n][j])); });
      if (d > .12) { ['bg', 'ac', 'ac2', 'card'].forEach(function (n) { cur[n] = mix(cur[n], tg[n], k); }); paint(cur); } // settled = no repaint
      requestAnimationFrame(frame);
    }
    measure();
    window.addEventListener('resize', measure);
    window.addEventListener('load', measure);
    setTimeout(measure, 1200);
    requestAnimationFrame(frame);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
