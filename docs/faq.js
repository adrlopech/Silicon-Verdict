/* Stable FAQ: the questions stay in one list, the answer opens in a fixed panel beside it with a soft cross-fade. Built from the <details> in the page (which stay for no-JS). */
(function () {
  function start() {
    var faq = document.querySelector('#faq .faq'); if (!faq) return;
    var items = [].slice.call(faq.querySelectorAll('details')); if (!items.length) return;
    var icons = ['lock', 'eye-off', 'search-check', 'mic', 'folder-lock', 'clapperboard', 'key-round', 'message-square', 'sparkles', 'terminal', 'layers', 'palette'];
    var ui = function (n) { return '<span class="ui" style="--i:url(assets/icons/ui-' + n + '.svg)" aria-hidden="true"></span>'; };

    // Each drawing shows the answer itself (what happens, with its labels), not a generic picture. The i* classes are styled in rework.css (.il .it, .itm, .iok...).
    var V = function (b, label) { return '<svg class="il" viewBox="0 0 360 150" role="img" aria-label="' + label + '">' + b + '</svg>'; };
    var T = function (x, y, c, t, mid) { return '<text class="' + c + '" x="' + x + '" y="' + y + '"' + (mid ? ' text-anchor="middle"' : '') + '>' + t + '</text>'; };
    var BOX = function (x, y, w, h, extra) { return '<rect class="s f' + (extra || '') + '" x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="10"/>'; };
    var OK = function (x, y) { return '<path class="iok" d="M' + x + ' ' + y + 'l4 4 8-8"/>'; };
    var NO = function (x, y) { return '<path class="ino" d="M' + x + ' ' + (y - 5) + 'l10 10M' + (x + 10) + ' ' + (y - 5) + 'l-10 10"/>'; };
    var AR = function (x, y) { return '<path class="s" d="M' + x + ' ' + y + 'h20m-7-7 7 7-7 7"/>'; };
    var IMG = function (h, x, y, w, hh) { return '<image href="assets/icons/' + h + '" x="' + x + '" y="' + y + '" width="' + w + '" height="' + hh + '"/>'; };
    var wave = ''; [10, 22, 34, 18, 40, 28, 14, 36, 24, 44, 20, 30, 12, 26, 38, 16].forEach(function (h, i) { wave += '<rect class="' + (i % 4 === 1 ? 'h' : 'bar') + '" x="' + (258 + i * 6) + '" y="' + (70 - h / 2) + '" width="3.4" height="' + h + '" rx="1.7"/>'; });
    var ILL = [
      // 1. not a public app: no sign-up form; one owner, one machine, its own two channels
      V(BOX(16, 18, 112, 104) + T(28, 36, 'itm', 'A public app?') + '<rect class="d" x="28" y="48" width="88" height="14" rx="5"/><rect class="d" x="28" y="68" width="88" height="14" rx="5"/><rect class="h" x="28" y="92" width="56" height="18" rx="6" opacity=".55"/>' + T(56, 105, 'itk', 'Sign up', 1) + '<path class="ino" d="M34 44l76 70M110 44l-76 70" opacity=".85"/>' +
        '<circle class="s f" cx="168" cy="58" r="11"/><path class="s" d="M150 92a18 16 0 0 1 36 0"/>' + T(168, 112, 'itm', 'one owner', 1) + AR(192, 72) +
        BOX(220, 50, 46, 44) + T(243, 77, 'it', 'SV', 1) + T(243, 112, 'itm', 'automation', 1) + '<path class="s" d="M270 72h14M284 56v32M284 56h10M284 88h10"/>' + IMG('m/youtube.svg', 300, 44, 30, 22) + IMG('tiktok.svg', 306, 78, 18, 21) + T(180, 140, 'itm', 'no sign-up, no accounts: it only publishes to its own two channels', 1),
        'No sign-up form: one owner runs the automation, which publishes only to its own YouTube and TikTok channels.'),
      // 2. data: nothing from visitors, totals from YouTube, comments answered with the owner's approval
      V(BOX(10, 12, 104, 112) + T(62, 30, 'itm', 'Visitors', 1) + T(62, 56, 'it', '0 cookies', 1) + T(62, 78, 'it', '0 trackers', 1) + T(62, 100, 'it', '0 ads', 1) +
        BOX(126, 12, 104, 112) + T(178, 30, 'itm', 'Statistics', 1) + '<rect class="bar" x="146" y="70" width="12" height="34" rx="3"/><rect class="h" x="164" y="52" width="12" height="52" rx="3"/><rect class="bar" x="182" y="62" width="12" height="42" rx="3"/><rect class="bar" x="200" y="80" width="12" height="24" rx="3"/>' + T(178, 118, 'itm', 'totals only', 1) +
        BOX(242, 12, 108, 112) + T(296, 30, 'itm', 'Comments', 1) + '<rect class="d" x="254" y="40" width="84" height="22" rx="8"/>' + T(262, 55, 'it', 'Which GPU?') + '<path class="s" d="M264 64v10h6"/><rect class="s f ihl" x="270" y="66" width="72" height="22" rx="8"/>' + T(306, 81, 'it', 'The 5080', 1) + OK(258, 100) + T(276, 108, 'itm', 'owner OKs') +
        T(180, 142, 'itm', 'nothing is sold, nothing identifies a viewer', 1),
        'Visitors: no cookies, trackers or ads. Statistics: channel totals only. Comments: a reply is drafted and the owner approves it.'),
      // 3. scripts: an LLM writes, a second pass checks, game claims need a verbatim quote that code finds in the source
      V(BOX(14, 18, 86, 108) + T(57, 36, 'itm', 'LLM script', 1) + '<rect class="d" x="26" y="48" width="62" height="7" rx="3.5"/><rect class="d" x="26" y="62" width="50" height="7" rx="3.5"/><rect class="h" x="26" y="76" width="58" height="7" rx="3.5"/><rect class="d" x="26" y="90" width="44" height="7" rx="3.5"/><rect class="d" x="26" y="104" width="56" height="7" rx="3.5"/>' + AR(106, 72) +
        '<circle class="s f" cx="156" cy="66" r="20"/><path class="s" d="M170 80l14 14"/><path class="iok" d="M147 66l6 6 11-11"/>' + T(156, 120, 'itm', 'second pass', 1) + AR(190, 72) +
        BOX(218, 22, 132, 76, ' ihl') + T(228, 44, 'it', '“Silksong launched') + T(228, 60, 'it', 'in September 2025”') + T(228, 84, 'itm', 'source: its Steam page') + OK(222, 114) + T(240, 122, 'itm', 'code finds the quote'),
        'A script drafted by a language model goes through a second checking pass; a game claim must quote its source word for word, and code checks the quote exists.'),
      // 4. narration: script text, ElevenLabs, one take with every word timed; robotic voices never ship
      V(BOX(12, 46, 104, 48) + T(22, 66, 'it', '“One of these') + T(22, 82, 'it', 'gets an F.”') + AR(122, 70) + BOX(150, 50, 82, 40) + T(191, 75, 'it', 'ElevenLabs', 1) + AR(234, 70) + wave +
        T(180, 124, 'itm', 'one continuous take, every word timed for the captions', 1) + T(180, 140, 'itm', 'a robotic-sounding voice is never published', 1),
        'The script text goes to ElevenLabs, which returns one continuous natural-sounding take with a timestamp for every word.'),
      // 5. QA: one failed check keeps the file on the machine
      V(BOX(12, 34, 58, 82) + '<path class="s f" d="M33 62l18 13-18 13z"/>' + T(41, 132, 'itm', 'video', 1) + AR(76, 75) +
        BOX(104, 14, 124, 122) + T(116, 32, 'itm', 'ffmpeg checks') + OK(116, 48) + T(134, 56, 'it', 'length') + OK(116, 72) + T(134, 80, 'it', 'frame size') + OK(116, 96) + T(134, 104, 'it', 'codec') + NO(117, 124) + T(134, 128, 'it', 'audio level') + AR(234, 75) +
        '<rect class="s f" x="268" y="44" width="70" height="44" rx="6"/><path class="s" d="M260 96h86"/>' + T(303, 72, 'itm', 'local', 1) + T(303, 118, 'it', 'stays here', 1) + T(303, 134, 'itm', 'never uploaded', 1),
        'A video that fails any ffmpeg check, here the audio level, stays on the local machine and is never uploaded.'),
      // 6. footage: official Steam media, credited, each clip used once, the game rests 14 days
      V('<circle cx="36" cy="64" r="24" fill="#fff"/>' + IMG('steam.svg', 20, 48, 32, 32) + T(36, 104, 'itm', 'Steam page', 1) + AR(64, 64) +
        '<rect class="s f" x="96" y="26" width="64" height="38" rx="6"/><rect class="s f" x="96" y="72" width="64" height="38" rx="6"/><path class="s f" d="M122 82l14 9-14 9z"/>' + T(128, 128, 'itm', 'screens, trailer', 1) + AR(168, 64) +
        '<rect class="s f" x="198" y="14" width="56" height="100" rx="10"/><rect class="d" x="206" y="96" width="40" height="8" rx="4"/>' + T(226, 128, 'itm', 'the Short', 1) +
        '<circle class="h" cx="272" cy="40" r="4"/>' + T(282, 44, 'it', 'credited') + '<circle class="h" cx="272" cy="66" r="4"/>' + T(282, 70, 'it', 'used once') + '<circle class="h" cx="272" cy="92" r="4"/>' + T(282, 96, 'it', '14-day rest'),
        'Official screenshots and trailer clips from the game\'s Steam page go into the Short, credited, each used once, and the game rests 14 days.'),
      // 7. control: switch access off on either platform, or write and get an answer within 30 days
      V(BOX(12, 18, 156, 40) + T(26, 42, 'it', 'Google access') + '<rect class="d" x="124" y="28" width="32" height="20" rx="10"/><circle class="s f" cx="134" cy="38" r="7"/>' +
        BOX(12, 68, 156, 40) + T(26, 92, 'it', 'TikTok access') + '<rect class="d" x="124" y="78" width="32" height="20" rx="10"/><circle class="s f" cx="134" cy="88" r="7"/>' +
        '<rect class="s f" x="196" y="36" width="60" height="42" rx="6"/><path class="s" d="M196 40l30 22 30-22"/>' + T(226, 98, 'itm', 'write to us', 1) + AR(264, 57) +
        '<circle class="s f" cx="316" cy="57" r="20"/><path class="s" d="M316 45v12l8 6"/>' + T(316, 98, 'itm', '≤ 30 days', 1) +
        T(180, 136, 'itm', 'switch access off any time, ask what we hold, or have it deleted', 1),
        'Turn off Google or TikTok access at any time, or email us to see or delete your data and get an answer within 30 days.')
    ];
    var CHIPS = [['No accounts', 'No registration', 'Single owner'], ['No trackers', 'Totals only', 'Replies approved'], ['Second pass', 'Source quotes', 'Code-verified'], ['ElevenLabs', 'One take', 'Word timestamps'], ['ffmpeg checks', 'Stays local', 'Never uploaded'], ['Official Steam', 'Credited', 'One use only'], ['Revoke any time', 'Request deletion', '30-day answer']];
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
