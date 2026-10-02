const assert = require('node:assert/strict');
const path = require('node:path');
const engines = require('playwright');
const engine = process.env.GRAF_BROWSER || 'chromium';
assert.ok(['chromium', 'webkit'].includes(engine), 'supported browser required');
const css = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css');
const fields = {
  text: '<input value="Synthetic">', search: '<input type="search">', email: '<input type="email">',
  password: '<input type="password">', number: '<input type="number">', date: '<input type="date">',
  select: '<select><option>Synthetic</option></select>', textarea: '<textarea>Synthetic</textarea>',
  code: '<input class="code-slot" maxlength="1" placeholder="0">',
  combo: '<span class="settings-combobox"><input role="combobox" aria-expanded="false"></span>',
  title: '<input class="meeting-title-input" value="Synthetic title">',
};
const actions = {
  button: '<button>Action</button>', link: '<a href="#target">Link</a>',
  summary: '<details><summary>Expand</summary></details>', checkbox: '<input type="checkbox">',
  radio: '<input type="radio">', range: '<input type="range">', file: '<input type="file">',
};

(async () => {
  const browser = await engines[engine].launch({headless: true});
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const row = ([id, html]) => `<div data-case="${id}"><input data-before aria-label="Before">${html}</div>`;
    await page.setContent(`<main><section>${row(['outside', '<input type="search">'])}</section>
      <section class="settings-page">${Object.entries(fields).map(row).join('')}${Object.entries(actions).map(row).join('')}</section>
      <section class="calendar-settings">${row(['calendar', '<select><option>Synthetic</option></select>'])}</section></main>`);
    await page.addStyleTag({path: css});
    await page.evaluate(() => {
      window.actionClicks = 0;
      document.addEventListener('click', event => {
        if (event.target.matches('button, a, summary, input[type="checkbox"], input[type="radio"], input[type="range"], input[type="file"]')) window.actionClicks++;
      });
    });
    const target = id => page.locator(`[data-case="${id}"]`).locator('input:not([data-before]),select,textarea,button,a,summary').first();
    const styles = locator => locator.evaluate(el => {
      const s = getComputedStyle(el), r = el.getBoundingClientRect();
      const root = getComputedStyle(document.documentElement);
      const rgb = color => {
        const sample = document.createElement('span'); sample.style.color = color; document.body.append(sample);
        const value = getComputedStyle(sample).color; sample.remove(); return value;
      };
      return {outline: s.outlineStyle, outlineWidth: s.outlineWidth, border: s.borderTopColor,
        borderWidth: s.borderTopWidth, shadow: s.boxShadow, width: r.width, height: r.height,
        focus: rgb(root.getPropertyValue('--focus-ring')), backgrounds: ['--bg', '--panel', '--surface', '--surface-2'].map(v => rgb(root.getPropertyValue(v))),
        offset: s.outlineOffset, active: el === document.activeElement};
    });
    const contrast = (a, b) => {
      const luminance = color => color.match(/[\d.]+/g).slice(0, 3).map(v => Number(v) / 255)
        .map(v => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
        .reduce((sum, v, i) => sum + v * [0.2126, 0.7152, 0.0722][i], 0);
      const x = luminance(a), y = luminance(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
    };
    for (const theme of ['light', 'dark']) {
      await page.evaluate(theme => document.documentElement.dataset.theme = theme, theme);
      for (const increased of [false, true]) {
        await page.emulateMedia({contrast: increased ? 'more' : 'no-preference'});
        const actionsBefore = await page.evaluate(() => window.actionClicks);
        for (const id of [...Object.keys(fields), 'outside', 'calendar']) {
          const input = target(id);
          await page.locator(`[data-case="${id}"] [data-before]`).focus();
          await input.evaluate(el => Promise.all(el.getAnimations().map(a => a.finished.catch(() => {}))));
          const before = await styles(input);
          await input.click();
          for (const mode of ['mouse', 'keyboard']) {
            if (mode === 'keyboard') {
              await page.locator(`[data-case="${id}"] [data-before]`).focus();
              await page.keyboard.press(engine === 'webkit' ? 'Alt+Tab' : 'Tab');
            }
            await input.evaluate(el => Promise.all(el.getAnimations().map(a => a.finished.catch(() => {}))));
            const s = await styles(input), label = `${engine}/${theme}/${increased}/${id}/${mode}`;
            assert.equal(s.active, true, label);
            if (id === 'select' || id === 'calendar') {
              assert.equal(s.outline, 'solid', label);
              assert.equal(s.outlineWidth, '2px', label);
              assert.equal(s.offset, '-2px', label);
              assert.equal(s.shadow, 'none', label);
            } else {
              assert.equal(s.outline, 'none', label);
              assert.match(s.shadow, /inset/, label);
              assert.match(s.shadow, id === 'title' ? /0px 0px 0px 2px/ : /0px 0px 0px 1px/, label);
              if (id !== 'title') assert.equal(s.border, s.focus, label);
            }
            assert.equal(s.borderWidth, before.borderWidth, label);
            assert.equal(s.width, before.width, label); assert.equal(s.height, before.height, label);
            for (const bg of s.backgrounds) assert.ok(contrast(s.focus, bg) >= 3, `contrast ${label}`);
          }
        }
        for (const id of Object.keys(actions)) {
          await page.locator(`[data-case="${id}"] [data-before]`).focus();
          await page.keyboard.press(engine === 'webkit' ? 'Alt+Tab' : 'Tab');
          const s = await styles(target(id));
          assert.equal(s.active, true, `keyboard target ${id}`);
          assert.equal(s.outline, 'solid', `keyboard indicator ${id}`);
          assert.equal(s.outlineWidth, '2px', id);
          assert.doesNotMatch(s.shadow, /inset/, `actions are not styled as fields: ${id}`);
        }
        assert.equal(await page.evaluate(() => window.actionClicks), actionsBefore, 'focus must not activate an action');
        assert.equal(await target('checkbox').isChecked(), false);
        assert.equal(await target('radio').isChecked(), false);
        assert.equal(await target('range').inputValue(), '50');
        assert.equal(await target('summary').evaluate(el => el.parentElement.open), false);
        await target('text').click(); await target('button').click();
        assert.equal(await page.evaluate(() => window.actionClicks), actionsBefore + 1, 'explicit click still activates');
        assert.equal((await styles(target('button'))).outline, 'none', 'mouse button does not acquire a keyboard ring');
      }
    }
    // Chromium implements forced-colors emulation; WebKit is checked above with prefers-contrast.
    if (engine === 'chromium') {
      await page.emulateMedia({forcedColors: 'active'});
      assert.equal(await page.evaluate(() => matchMedia('(forced-colors: active)').matches), true);
      for (const id of [...Object.keys(fields), 'outside', 'calendar']) {
        await target(id).focus();
        await target(id).evaluate(el => Promise.all(el.getAnimations().map(a => a.finished.catch(() => {}))));
        const s = await styles(target(id));
        assert.equal(s.outline, 'solid', `forced colors ${id}`);
        assert.equal(s.outlineWidth, '2px', id);
        assert.equal(s.shadow, 'none', id);
        // Forced colors can repaint a transparent native border; the inset outline covers it.
        assert.equal(s.offset, '-2px', `single contour ${id}`);
      }
      await page.locator('[data-case="button"] [data-before]').focus();
      await page.keyboard.press('Tab');
      assert.equal((await styles(target('button'))).outline, 'solid');
    }
    assert.deepEqual(errors, []);
    console.log(`${engine}: field contours, keyboard actions, geometry, themes and contrast PASS`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
