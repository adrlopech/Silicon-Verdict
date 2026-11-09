/* Stable FAQ: the questions stay in one list, the answer opens in a fixed panel beside it with a soft cross-fade. Built from the <details> in the page (which stay for no-JS). */
(function () {
  function start() {
    var faq = document.querySelector('#faq .faq'); if (!faq) return;
    var items = [].slice.call(faq.querySelectorAll('details')); if (!items.length) return;
    var icons = ['lock', 'eye-off', 'search-check', 'mic', 'folder-lock', 'clapperboard', 'key-round', 'message-square', 'sparkles', 'terminal', 'layers', 'palette'];
    var ui = function (n) { return '<span class="ui" style="--i:url(assets/icons/ui-' + n + '.svg)" aria-hidden="true"></span>'; };

    var V = function (b) { return '<svg class="il" viewBox="0 0 360 150" aria-hidden="true">' + b + '</svg>'; };
    var bars = ''; [14, 30, 52, 26, 66, 88, 54, 34, 60, 78, 42, 24, 50, 70, 36, 20].forEach(function (h, i) { bars += '<rect class="' + (i % 5 === 2 ? 'h' : 'bar') + '" x="' + (60 + i * 14) + '" y="' + (75 - h / 2) + '" width="8" height="' + h + '" rx="4"/>'; });
    var ILL = [
      V('<rect class="s f" x="108" y="18" width="144" height="92" rx="12"/><path class="s" d="M146 126h68M180 110v16"/><circle class="s f" cx="180" cy="54" r="13"/><path class="s" d="M156 94a24 20 0 0 1 48 0"/><path class="s" d="M44 40l40 40M84 40L44 80"/><rect class="s f" x="276" y="52" width="48" height="40" rx="8"/><path class="s" d="M286 52v-8a14 14 0 0 1 28 0v8"/>'),
      V('<path class="s f" d="M180 14c26 14 52 14 52 14v44c0 34-26 52-52 62-26-10-52-28-52-62V28s26 0 52-14z"/><path class="s" d="M160 70l14 14 28-30"/><circle class="s f" cx="64" cy="48" r="20"/><path class="s" d="M50 34l28 28M78 34L50 62"/><circle class="s f" cx="296" cy="100" r="20"/><path class="s" d="M282 86l28 28M310 86L282 114"/>'),
      V('<rect class="s f" x="74" y="14" width="112" height="124" rx="12"/><rect class="d" x="92" y="34" width="60" height="8" rx="4"/><rect class="d" x="92" y="56" width="76" height="8" rx="4"/><rect class="d" x="92" y="78" width="48" height="8" rx="4"/><path class="s" d="M162 34l6 6 10-12"/><circle class="s f" cx="244" cy="76" r="34"/><path class="s" d="M268 102l34 32"/><path class="s" d="M230 76l11 11 20-22"/>'),
      V(bars + '<path class="s" d="M60 130h240" style="opacity:.35"/><circle class="s f" cx="320" cy="34" r="20"/><rect class="s" x="314" y="24" width="12" height="18" rx="6"/><path class="s" d="M308 38a12 12 0 0 0 24 0M320 50v7"/>'),
      V('<rect class="s f" x="40" y="22" width="150" height="106" rx="12"/><circle class="s f" cx="64" cy="48" r="10"/><path class="s" d="M59 48l4 4 7-8"/><rect class="d" x="84" y="44" width="84" height="8" rx="4"/><circle class="s f" cx="64" cy="76" r="10"/><path class="s" d="M59 71l10 10M69 71L59 81"/><rect class="d" x="84" y="72" width="64" height="8" rx="4"/><circle class="s f" cx="64" cy="104" r="10"/><path class="s" d="M59 104l4 4 7-8"/><rect class="d" x="84" y="100" width="76" height="8" rx="4"/><path class="s" d="M204 76h40m-8-8 8 8-8 8"/><path class="s f" d="M262 54h36l12 14h26v58h-74z"/>'),
      V('<rect class="s f" x="96" y="14" width="150" height="92" rx="12" opacity=".5"/><rect class="s f" x="76" y="30" width="150" height="92" rx="12" opacity=".75"/><rect class="s f" x="56" y="46" width="150" height="92" rx="12"/><path class="s" d="M108 72l40 17-40 17z" fill="rgba(var(--ac),.25)"/><path class="s" d="M280 40l8 18 18 8-18 8-8 18-8-18-18-8 18-8z"/>'),
      V('<rect class="s f" x="46" y="26" width="110" height="44" rx="22"/><circle class="h" cx="70" cy="48" r="12"/><rect class="s f" x="46" y="82" width="110" height="44" rx="22"/><circle class="d" cx="132" cy="104" r="12"/><path class="s" d="M196 76h50m-8-8 8 8-8 8"/><circle class="s f" cx="290" cy="76" r="28"/><path class="s" d="M274 76h32M290 60v32" style="display:none"/><path class="s" d="M276 90l28-28M276 62l28 28"/>')
    ];
    var CHIPS = [['No accounts', 'No registration', 'Single owner'], ['No trackers', 'No audience data', 'Publish only'], ['Second pass', 'Source quotes', 'Code-verified'], ['ElevenLabs', 'One take', 'Word timestamps'], ['ffmpeg checks', 'Stays local', 'Never uploaded'], ['Official Steam', 'Credited', 'One use only'], ['Revoke any time', 'Request deletion', 'Email']];
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
        var ch = (CHIPS[i % CHIPS.length]).map(function (c, k) { return '<span class="pl">' + ui(['check', 'shield-check', 'sparkles'][k]) + c + '</span>'; }).join('');
        panel.innerHTML = '<div class="faqx-t"><span class="tile lg">' + ui(icons[i % icons.length]) + '</span><div><h3>' + q + '</h3><p>' + a + '</p></div></div><div class="pills">' + ch + '</div><div class="faqx-ill">' + ILL[i % ILL.length] + '</div>';
        panel.classList.remove('swap');
      };
      if (first) paint(); else { panel.classList.add('swap'); setTimeout(paint, 280); }
    }
    wrap.appendChild(list); wrap.appendChild(panel); faq.parentNode.insertBefore(wrap, faq);
    wrap.classList.add('in'); show(0, true);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
