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
    const service = await browser.newPage();
    const neutral = {
      main: '<main tabindex="-1">Page</main>', heading: '<h1 tabindex="-1">Heading</h1>',
      h2: '<h2 tabindex="-1">Heading</h2>', section: '<section tabindex="-1">Info</section>',
      div: '<div tabindex="-1">Info</div>', paragraph: '<p tabindex="-1">Info</p>',
      status: '<section role="status" tabindex="-1">Result</section>',
      alert: '<p role="alert" tabindex="-1">Error</p>',
      panel: '<section role="tabpanel" tabindex="-1">Result panel</section>',
      region: '<section role="region" tabindex="-1">Info region</section>',
      ariaHeading: '<div role="heading" tabindex="-1">Heading</div>',
    };
    const interactive = {
      button: '<button tabindex="-1">Action</button>', link: '<a href="#" tabindex="-1">Link</a>',
      option: '<div role="option" tabindex="-1">Option</div>',
      menuitem: '<div role="menuitem" tabindex="-1">Action</div>',
      custom: '<div class="button" tabindex="-1">Action</div>',
      editable: '<div contenteditable="true" tabindex="-1">Edit</div>',
      zero: '<div tabindex="0">Custom control</div>', positive: '<div tabindex="1">Custom control</div>',
    };
    const serviceStyle = locator => locator.evaluate(el => ({
      active: document.activeElement === el, outline: getComputedStyle(el).outlineStyle,
      tabindex: el.getAttribute('tabindex'), width: el.getBoundingClientRect().width,
    }));
    for (const theme of ['light', 'dark']) {
      for (const wrapper of ['settings-page', 'calendar-settings', 'notification-panel']) {
        await service.setContent(`<div class="${wrapper}">${Object.entries({...neutral, ...interactive}).map(([id, html]) =>
          `<div data-service="${id}"><input data-before aria-label="Before">${html}<button data-after>After</button></div>`).join('')}</div>`);
        await service.addStyleTag({path: css});
        await service.evaluate(theme => document.documentElement.dataset.theme = theme, theme);
        for (const [id] of Object.entries(neutral)) {
          const row = service.locator(`[data-service="${id}"]`), target = row.locator(':scope > :nth-child(2)');
          const before = await serviceStyle(target);
          for (const modality of ['mouse', 'keyboard']) {
            await row.locator('[data-before]').click();
            if (modality === 'keyboard') await service.keyboard.press(engine === 'webkit' ? 'Alt+Tab' : 'Tab');
            await target.focus();
            const style = await serviceStyle(target), label = `${theme}/${wrapper}/${id}/${modality}`;
            assert.equal(style.active, true, label); assert.equal(style.outline, 'none', label);
            assert.equal(style.tabindex, '-1', label); assert.equal(style.width, before.width, label);
            await service.keyboard.press(engine === 'webkit' ? 'Alt+Tab' : 'Tab');
            assert.equal(await row.locator('[data-after]').evaluate(el => document.activeElement === el), true, `Tab after ${label}`);
          }
        }
        for (const id of Object.keys(interactive)) {
          const row = service.locator(`[data-service="${id}"]`), target = row.locator(':scope > :nth-child(2)');
          await row.locator('[data-before]').focus();
          await service.keyboard.press(engine === 'webkit' ? 'Alt+Tab' : 'Tab');
          await target.focus();
          assert.equal((await serviceStyle(target)).active, true, `interactive ${id}`);
          assert.equal((await serviceStyle(target)).outline, 'solid', `preserved ${theme}/${wrapper}/${id}`);
        }
      }
    }
    if (engine === 'chromium') {
      await service.emulateMedia({forcedColors: 'active'});
      await service.locator('[data-service="main"] main').focus();
      assert.equal((await serviceStyle(service.locator('[data-service="main"] main'))).outline, 'none');
      await service.locator('[data-service="option"] [role="option"]').focus();
      assert.equal((await serviceStyle(service.locator('[data-service="option"] [role="option"]'))).outline, 'solid');
    }
    await service.close();

    const guides = await browser.newPage();
    const publicCss = path.join(__dirname, '../../src/twobrain_rec_server/public/static/public');
    for (const width of [960, 340]) {
      await guides.setViewportSize({width, height: 800});
      await guides.setContent('<input aria-label="Before"><div class="guides-page section-light"><ol class="guide-cards"><li class="guide-card"><h2><a href="#guide">Synthetic long guide heading for wrapped keyboard focus<span class="guide-card-hit" aria-hidden="true"></span></a></h2><p>Synthetic description</p><span class="guide-read">Read guide</span></li></ol></div>');
      for (const file of ['landing.css', 'content.css']) await guides.addStyleTag({path: path.join(publicCss, file)});
      await guides.evaluate(() => { window.guideClicks = 0; document.querySelector('a').addEventListener('click', event => {event.preventDefault(); window.guideClicks++;}); });
      const link = guides.locator('.guide-card a'), hit = guides.locator('.guide-card-hit'), card = guides.locator('.guide-card');
      const guideStyles = () => link.evaluate(el => ({line: getComputedStyle(el).textDecorationLine,
        thickness: getComputedStyle(el).textDecorationThickness, outline: getComputedStyle(el).outlineStyle,
        cardOutline: getComputedStyle(el.closest('.guide-card')).outlineStyle,
        hitOutline: getComputedStyle(el.querySelector('.guide-card-hit')).outlineStyle,
        visible: el.matches(':focus-visible')}));
      await guides.locator('input').focus(); await guides.keyboard.press(engine === 'webkit' ? 'Alt+Tab' : 'Tab');
      assert.equal(await link.evaluate(el => document.activeElement === el), true, 'guide Tab target');
      let style = await guideStyles();
      assert.equal(style.line, 'underline'); assert.equal(style.thickness, '3px');
      assert.equal(style.outline, 'none'); assert.equal(style.hitOutline, 'none'); assert.equal(style.cardOutline, 'none');
      const cardBox = await card.boundingBox(), hitBox = await hit.boundingBox();
      assert.ok(Math.abs(hitBox.width - cardBox.width) <= 2 && Math.abs(hitBox.height - cardBox.height) <= 2, 'whole card hit area');
      if (width === 340) assert.ok(await link.evaluate(el => el.getClientRects().length > 1), 'multiline heading');
      await guides.locator('input').click();
      await guides.mouse.click(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height - 12);
      assert.equal(await guides.evaluate(() => window.guideClicks), 1, 'whole card click preserved');
      assert.equal((await guideStyles()).visible, false, 'mouse focus remains quiet');
      if (engine === 'chromium') {
        await guides.emulateMedia({forcedColors: 'active'});
        await guides.locator('input').focus(); await guides.keyboard.press('Tab');
        style = await guideStyles(); assert.equal(style.line, 'underline'); assert.equal(style.thickness, '3px');
        assert.equal(style.hitOutline, 'none');
        await guides.emulateMedia({forcedColors: 'none'});
      }
    }
    await guides.close();
    console.log(`${engine}: service targets, interactive negative tabindex, Tab continuity and guide heading focus PASS`);

    assert.deepEqual(errors, []);
    console.log(`${engine}: field contours, keyboard actions, geometry, themes and contrast PASS`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
