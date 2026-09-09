const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, webkit } = require(require.resolve('playwright', { paths: [process.env.GRAF_NODE_MODULES || process.cwd()] }));
const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');
const source = fs.readFileSync(path.join(assets, 'cabinet.js'), 'utf8');
const picker = source.slice(source.indexOf('const initSummaryFormats ='), source.indexOf('const initSummaryTemplateSettings ='));
const html = fs.readFileSync(process.argv[2], 'utf8');
const maliciousName = '<img src=x onerror=alert(1)> Личный формат с очень длинным названием';
(async () => {
  const engine = process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium;
  const browser = await engine.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1100, height: 860 } });
    page.setDefaultTimeout(5000);
    const errors = [], writes = [];
    let personalDelay = null, personalFails = true;
    page.on('pageerror', error => errors.push(error.message));
    await page.route('https://graf.test/**', async route => {
      const request = route.request(), url = request.url();
      if (['script', 'stylesheet'].includes(request.resourceType())) return route.fulfill({ body: '', contentType: request.resourceType() === 'script' ? 'application/javascript' : 'text/css' });
      if (url.endsWith('/summary-templates')) {
        await personalDelay;
        return route.fulfill(personalFails ? { status: 503, json: {} } : { json: { personal: [{
          template_id: 'personal-id', template_key: 'personal-test', version: 1,
          name: maliciousName, purpose: 'Личная краткая подсказка', sections: ['summary']
        }, ...Array.from({length: 23}, (_, i) => ({ template_id: `personal-${i}`, template_key: `personal-extra-${i}`, version: 1, name: `Личный формат ${i + 2}`, purpose: 'Краткие итоги встречи' }))] } });
      }
      if (request.method() === 'POST') {
        writes.push(request.postDataJSON());
        return route.fulfill({ status: 503, json: { code: 'summary_generation_unavailable' } });
      }
      if (url.endsWith('/summary-candidates')) return route.fulfill({ json: [] });
      if (url.includes('/summaries/')) return route.fulfill({ json: { current_outcome_set_id: null } });
      return route.fulfill({ contentType: 'text/html', body: html });
    });
    await page.goto('https://graf.test/meeting');
    await page.addStyleTag({ path: path.join(assets, 'cabinet.css') });
    await page.addScriptTag({ content: `(() => {
      document.documentElement.dataset.cabinetJs = 'ready';
      const csrfToken = 'synthetic', summaryActionProblemCodes = [];
      const recoverMeetingDetailFromResponse = async () => false;
      const isMeetingDetailRecoveredError = () => false;
      ${picker}
      initSummaryFormats();
    })();` });
    const button = page.locator('[data-summary-format-button]');
    const popover = page.locator('[data-summary-format-popover]');
    const visible = () => page.locator('[data-summary-format-listbox] [role="option"]:visible');
    const all = page.locator('[data-summary-format-all]');
    const back = page.locator('[data-summary-format-back]');
    const description = page.locator('[data-summary-format-description]');
    fs.mkdirSync('/tmp/graf-format-picker', { recursive: true });
    await button.click();
    await popover.screenshot({path: `/tmp/graf-format-picker/${process.env.GRAF_BROWSER || 'chromium'}-quick-menu.png`});
    assert.equal(await visible().count(), 4);
    assert.equal(await page.locator('dialog:modal').count(), 0);
    await visible().nth(1).focus();
    assert.equal(await description.textContent(), await visible().nth(1).getAttribute('data-template-purpose'));
    await visible().nth(2).hover();
    assert.equal(await description.textContent(), await visible().nth(2).getAttribute('data-template-purpose'));
    await visible().nth(0).focus();
    await page.keyboard.press('End');
    assert.equal(await visible().nth(3).evaluate(el => el === document.activeElement), true);
    await page.keyboard.press('Home');
    await page.keyboard.press('ArrowUp');
    assert.equal(await visible().nth(3).evaluate(el => el === document.activeElement), true);
    await page.keyboard.press(process.env.GRAF_BROWSER === 'webkit' ? 'Alt+Tab' : 'Tab');
    assert.equal(await all.evaluate(el => el === document.activeElement), true, `Tab leaves options for catalog action: ${await page.evaluate(()=>document.activeElement.outerHTML.slice(0,350))}`);
    await all.click();
    await page.waitForFunction(() => document.querySelector('[data-summary-format-load-status]')?.textContent.includes('не загрузились'));
    assert.equal(await visible().count(), 9, 'built-ins survive personal list failure');
    await back.click();
    personalFails = false;
    let releasePersonal;
    personalDelay = new Promise(resolve => { releasePersonal = resolve; });
    await all.click();
    assert.equal(await visible().count(), 9, 'built-ins open before personal request finishes');
    const fifth = page.locator('[data-template-key="graf-weekly-team-meeting-v1"]');
    assert.equal(await fifth.evaluate(el => el === document.activeElement), true, 'full catalog focuses current fifth format');
    await visible().nth(6).focus();
    releasePersonal(); personalDelay = null;
    await page.waitForFunction(() => document.querySelector('[data-template-key="personal-test"]'));
    assert.equal(await visible().count(), 33);
    assert.equal(await visible().nth(6).evaluate(el => el === document.activeElement), true, 'late personal response must not steal focus');
    const personal = page.locator('[data-template-key="personal-test"]');
    assert.equal(await personal.locator('img').count(), 0);
    assert((await personal.textContent()).includes(maliciousName));
    assert.equal(await page.locator('[role="listbox"] [data-summary-format-settings]').count(), 0);
    await fifth.click();
    assert.equal(await popover.isVisible(), false);
    assert.equal(writes.length, 0, 'selecting current saved format must not generate');
    await button.click();
    await all.click();
    await back.click();
    assert.equal(await visible().count(), 4);
    await page.keyboard.press('Escape');
    assert.equal(await popover.isVisible(), false);
    assert.equal(await button.evaluate(el => el === document.activeElement), true);
    await button.click();
    await page.locator('h1').click();
    assert.equal(await popover.isVisible(), false, 'outside click closes chooser');
    await button.click();
    await all.click();
    await page.locator('[data-summary-format-settings]').focus();
    await page.keyboard.press('Tab');
    await popover.waitFor({ state: 'hidden' });
    await personal.locator('.summary-format-name').evaluate(el => { el.textContent = 'Личный формат для проектных встреч и обсуждений команды'; });
    for (const theme of ['light', 'dark']) {
      await page.evaluate(theme => { document.documentElement.dataset.theme = theme; }, theme);
      for (const width of [390, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 860 });
        await button.click();
        if (width === 1024) await page.screenshot({ path: `/tmp/graf-format-picker/${process.env.GRAF_BROWSER || 'chromium'}-${theme}-quick.png` });
        await all.click();
        await personal.focus();
        const layout = await popover.evaluate(el => {
          const rect = el.getBoundingClientRect();
          return { width: el.clientWidth, scroll: el.scrollWidth, left: rect.left, right: rect.right, bottom: rect.bottom, viewport: innerWidth,
            footer: el.querySelector('[data-summary-format-settings]').getBoundingClientRect().bottom,
            listScroll: el.querySelector('[role="listbox"]').scrollHeight, listHeight: el.querySelector('[role="listbox"]').clientHeight };
        });
        assert(layout.scroll <= layout.width + 1, `horizontal overflow: ${JSON.stringify(layout)}`);
        assert(layout.left >= 0 && layout.right <= layout.viewport, 'menu stays within viewport');
        assert(layout.footer <= layout.bottom && layout.bottom <= 860, 'settings footer stays inside menu and viewport');
        assert(layout.listScroll > layout.listHeight, 'large catalog scrolls independently');
        if (width === 1024) {
          await page.locator('[data-summary-format-listbox]').evaluate(el => { el.scrollTop = 0; });
          await popover.screenshot({path: `/tmp/graf-format-picker/${process.env.GRAF_BROWSER || 'chromium'}-${theme}-all-menu.png`});
        }
        if ([390, 1024].includes(width)) await page.screenshot({ path: `/tmp/graf-format-picker/${process.env.GRAF_BROWSER || 'chromium'}-${theme}-${width}.png` });
        await page.keyboard.press('Escape');
      }
    }
    await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
    await button.click(); await all.click();
    assert(await page.locator('[data-summary-format-settings]').isVisible());
    const zoomed = await popover.boundingBox();
    assert(zoomed.x >= 0 && zoomed.x + zoomed.width <= 1440 && zoomed.y + zoomed.height <= 860, `200% zoom stays within viewport: ${JSON.stringify(zoomed)}`);
    await page.keyboard.press('Escape');
    await page.evaluate(() => { document.documentElement.style.zoom = ''; });
    await button.click(); await all.click();
    await personal.click();
    await page.waitForFunction(() => !document.querySelector('[data-summary-format-button]').disabled);
    assert.equal(writes.length, 1, 'one personal selection creates one request');
    assert.equal(writes[0].template_key, 'personal-test');
    assert.equal(writes[0].template_id, 'personal-id');
    assert.equal(await popover.isVisible(), false);
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
