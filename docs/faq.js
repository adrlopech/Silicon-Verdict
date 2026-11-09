/* Stable FAQ: the questions stay in one list, the answer opens in a fixed panel beside it with a soft cross-fade. Built from the <details> in the page (which stay for no-JS). */
(function () {
  function start() {
    var faq = document.querySelector('#faq .faq'); if (!faq) return;
    var items = [].slice.call(faq.querySelectorAll('details')); if (!items.length) return;
    var icons = ['lock', 'eye-off', 'shield-check', 'clapperboard', 'gauge', 'film', 'cpu', 'message-square', 'sparkles', 'terminal', 'layers', 'palette'];
    var ui = function (n) { return '<span class="ui" style="--i:url(assets/icons/ui-' + n + '.svg)" aria-hidden="true"></span>'; };
    var wrap = document.createElement('div'); wrap.className = 'faqx rv';
    var list = document.createElement('div'); list.className = 'faqx-list'; list.setAttribute('role', 'tablist'); list.setAttribute('aria-label', 'Questions');
    var panel = document.createElement('div'); panel.className = 'faqx-a'; panel.setAttribute('role', 'tabpanel'); panel.setAttribute('aria-live', 'polite');
    var btns = items.map(function (d, i) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'faqx-q'; b.setAttribute('role', 'tab'); b.setAttribute('aria-selected', 'false');
      b.innerHTML = '<span class="tile">' + ui(icons[i % icons.length]) + '</span><span>' + d.querySelector('summary').textContent + '</span>';
      b.addEventListener('click', function () { show(i); }); list.appendChild(b); return b;
    });
    function show(i, first) {
      btns.forEach(function (b, j) { b.setAttribute('aria-selected', String(i === j)); });
      var d = items[i], q = d.querySelector('summary').textContent, a = d.querySelector('p').innerHTML;
      var paint = function () {
        panel.innerHTML = '<span class="tile lg">' + ui(icons[i % icons.length]) + '</span><h3>' + q + '</h3><p>' + a + '</p>';
        panel.classList.remove('swap');
      };
      if (first) paint(); else { panel.classList.add('swap'); setTimeout(paint, 280); }
    }
    wrap.appendChild(list); wrap.appendChild(panel); faq.parentNode.insertBefore(wrap, faq);
    wrap.classList.add('in'); show(0, true);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
