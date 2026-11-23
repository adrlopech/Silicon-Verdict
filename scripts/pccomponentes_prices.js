// Price extractor for pccomponentes.com, run inside the browser (Claude in Chrome's javascript tool): the site blocks scripts that do not run in a real browser.
// 1. Open https://www.pccomponentes.com/search?query=<query>&sort=price_asc   (query and match come from data/products/<family>.json)
// 2. Run this file's body, then:  await pcExtract({match: '<match regex>', kind: 'cpu' | 'gpu'})
// It returns {price, name} of the cheapest listing of the standalone part (never a PC or laptop that contains it), or null when there is none.
// guide/prices.md has the whole routine; scripts/save_prices.py stores the answers in data/prices/<date>.json.
window.pcExtract = async ({ match, kind }) => {
  await new Promise((r) => setTimeout(r, 4000)); // the listing is drawn by the page's own scripts
  const re = new RegExp(match, 'i');
  const lines = document.querySelector('main').innerText.split('\n').map((x) => x.trim());
  const found = [];
  for (let i = 0; i < lines.length; i++) {
    const name = lines[i];
    const isGpu = /^(Tarjeta|Gráfica)/i.test(name);
    const isCpu = /^(Procesador|AMD |Intel )/i.test(name) && !/ PC |Ordenador|Windows|\/\d+ ?GB/i.test(name);
    if (!(kind === 'gpu' ? isGpu : isCpu) || !re.test(name)) continue;
    for (let j = i + 1; j < i + 8; j++) {
      const m = (lines[j] || '').match(/^([\d.]+(?:,\d+)?)\s*€/);
      if (m) {
        found.push({ price: parseFloat(m[1].replace(/\./g, '').replace(',', '.')), name: name.slice(0, 120) });
        break;
      }
    }
  }
  found.sort((a, b) => a.price - b.price);
  return found[0] || null;
};
