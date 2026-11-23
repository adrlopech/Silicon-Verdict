// Helpers for TikTok Studio (https://www.tiktok.com/tiktokstudio/upload), run inside the browser with Claude in Chrome's javascript tool.
// They replace the screen coordinates the upload used to need (which broke whenever the window size changed): every element is found by its class, role or text.
//
// What still goes through real keystrokes (the `computer` tool, not JavaScript): the description text, because the editor (Draft.js) ignores programmatic edits and crashes the page on execCommand.
// Everything else is done here. Define the helpers once per page load (paste this file's body), then:
//
//   tt.focusCaption()                                   -> then: key cmd+a, key Delete, type the caption, type " #tag" ... (see guide/publishing.md)
//   await tt.pickHashtag('#siliconverdict')             -> {ok, suggestions}   (call after typing the tag, once the dropdown is up)
//   await tt.schedule({ date: '2026-11-24', time: '20:00' })   -> {ok, value}  (minutes must be a multiple of 5; Madrid time = the page's "(GMT+1) Hora local")
//   tt.state()                                          -> caption, picked hashtags, mode, date, time, the buttons that exist
//   await tt.press('Programar')                         -> clicks the button with that text; then:  await tt.confirmReview()  if the "Seguir con la publicación" dialog appears
//
// Event sequences (pointerdown ... click) are needed: a bare element.click() does nothing on this page's React components.
window.tt = (() => {
  const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  const MONTH_NAMES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const fire = (el) => {
    for (const t of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true, view: window }));
  };
  const editor = () => document.querySelector('.public-DraftEditor-content');
  const pickers = () => [...document.querySelectorAll('.Picker__root.schedule-picker')];
  const pickerValue = (root) => root.querySelector('.Picker__value')?.textContent.trim() || '';
  const dateRoot = () => pickers().find((r) => /\d{4}$/.test(pickerValue(r)));
  const timeRoot = () => pickers().find((r) => /^\d{2}:\d{2}$/.test(pickerValue(r)));
  const closePopups = () => document.body.click();

  async function pickHashtag(tag) {
    const want = tag.trim().toLowerCase();
    const options = [...document.querySelectorAll('[role=option] > span:first-child')];
    const hit = options.find((s) => s.textContent.trim().toLowerCase() === want);
    const suggestions = options.map((s) => s.textContent.trim()).slice(0, 6);
    if (!hit) return { ok: false, suggestions }; // the exact tag is not offered: pick another one (the dropdown lists what TikTok knows)
    fire(hit.parentElement);
    await sleep(600);
    return { ok: [...document.querySelectorAll('.mention')].some((m) => m.innerText.trim().toLowerCase() === want), suggestions };
  }

  async function setTime(hhmm) {
    const [h, m] = hhmm.split(':');
    if (Number(m) % 5) throw new Error('minutes must be a multiple of 5');
    fire(timeRoot().querySelector('.Picker__value'));
    await sleep(700);
    const [hours, minutes] = [...document.querySelectorAll('.TimePicker__column')];
    const hour = [...hours.children].find((x) => x.textContent.trim() === h);
    const minute = [...minutes.children].find((x) => x.textContent.trim() === m);
    if (!hour || !minute) throw new Error(`time ${hhmm} is not offered`);
    fire(hour);
    await sleep(300);
    fire(minute);
    await sleep(300);
    closePopups();
  }

  async function setDate(ymd) {
    const [y, mo, d] = ymd.split('-').map(Number);
    fire(dateRoot().querySelector('.Picker__value'));
    await sleep(800);
    for (let guard = 0; guard < 14; guard++) { // walk to the right month (the calendar opens on today's)
      const month = MONTH_NAMES.indexOf((document.querySelector('.DatePicker__titleMonth')?.textContent || '').trim().toLowerCase());
      const year = Number((document.querySelector('.DatePicker__titleYear')?.textContent || '').trim());
      const diff = (y - year) * 12 + (mo - 1 - month);
      if (!diff) break;
      const nav = [...document.querySelectorAll('.DatePicker__nav')].find((b) => (b.getAttribute('aria-label') || b.textContent || '').toLowerCase().includes(diff > 0 ? 'next' : 'previous'));
      fire(nav);
      await sleep(400);
    }
    // the grid also shows the tail of the previous month and the head of the next: the days of THIS month run from the first "1" until the numbers drop again
    const buttons = [...document.querySelectorAll('.DatePicker__grid .DatePicker__day')];
    const start = buttons.findIndex((b) => b.textContent.trim() === '1');
    let end = buttons.length;
    for (let i = start + 1; i < buttons.length; i++) if (Number(buttons[i].textContent.trim()) < Number(buttons[i - 1].textContent.trim())) { end = i; break; }
    const day = buttons.slice(start, end).find((b) => Number(b.textContent.trim()) === d);
    if (!day || day.disabled) throw new Error(`date ${ymd} is not selectable`);
    fire(day);
    await sleep(500);
    closePopups();
  }

  async function schedule({ date, time }) {
    const radio = document.querySelector('input[type=radio][value=schedule]');
    radio.scrollIntoView({ block: 'center' });
    if (!radio.checked) radio.click();
    await sleep(900);
    await setDate(date);
    await setTime(time);
    const want = `${Number(date.slice(8))} ${MONTHS[Number(date.slice(5, 7)) - 1]} ${date.slice(0, 4)}`;
    const value = { date: pickerValue(dateRoot()), time: pickerValue(timeRoot()) };
    return { ok: value.date === want && value.time === time, value };
  }

  function state() {
    return {
      caption: editor()?.innerText ?? null,
      hashtags: [...document.querySelectorAll('.mention')].map((m) => m.innerText.trim()),
      mode: document.querySelector('input[type=radio]:checked')?.value ?? null,
      date: dateRoot() ? pickerValue(dateRoot()) : null,
      time: timeRoot() ? pickerValue(timeRoot()) : null,
      buttons: [...document.querySelectorAll('button')].map((b) => b.innerText.trim()).filter((t) => /^(Publicar|Programar|Guardar borrador|Descartar)/.test(t)),
    };
  }

  async function press(text) {
    const btn = [...document.querySelectorAll('button')].find((b) => b.innerText.trim() === text && !b.disabled);
    if (!btn) return false;
    btn.scrollIntoView({ block: 'center' });
    fire(btn);
    await sleep(1500);
    return true;
  }

  async function confirmReview() { // "¿Seguir con la publicación?": the content review is still running; "Publicar ahora" only continues the scheduled post
    const dialogButton = [...document.querySelectorAll('[role=dialog] button, .TUXModal button, button')].find((b) => b.innerText.trim() === 'Publicar ahora');
    if (!dialogButton) return false;
    fire(dialogButton);
    await sleep(2000);
    return true;
  }

  return { focusCaption: () => editor()?.focus(), pickHashtag, schedule, state, press, confirmReview, fire };
})();
