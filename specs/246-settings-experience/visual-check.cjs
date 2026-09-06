// Run with existing Playwright: NODE_PATH=/path/to/node_modules node <this file>.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.SETTINGS_PREVIEW_URL || 'http://127.0.0.1:8765';
(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    const results = [];
    const paths = ['', '/account', '/recording', '/summaries', '/workspace', '/notifications', '/integrations/calendar', '/billing', '/provider-links'];
    for (const embedded of [false, true]) for (const theme of ['light', 'dark']) for (const width of [1440, 1024, 768, 390, 320]) for (const path of paths) {
      await page.setViewportSize({width, height: 900});
      const response = await page.goto(`${base}${embedded ? '/desktop' : ''}/settings${path}?theme=${theme}`);
      assert.equal(response.status(), 200);
      const geometry = await page.evaluate(() => {
        const column = document.querySelector('.settings-page__content,.calendar-settings__content');
        const main = document.querySelector('main');
        const b = column.getBoundingClientRect(), m = main.getBoundingClientRect(), s = getComputedStyle(main);
        return {delta: Math.abs((b.left-m.left-parseFloat(s.paddingLeft))-(m.right-parseFloat(s.paddingRight)-b.right)), overflow: Math.max(document.documentElement.scrollWidth-innerWidth, main.scrollWidth-main.clientWidth), column: b.width};
      });
      results.push({embedded, theme, width, path, ...geometry});
      assert.ok(geometry.delta <= 2 && geometry.overflow <= 1 && geometry.column <= (path === '/billing' ? 881 : 781), JSON.stringify(results.at(-1)));
      if (path === '/account') {
        const locale = await page.locator('label[for=account-locale]').boundingBox();
        const timezone = await page.locator('[data-timezone-field]').boundingBox();
        if (Math.abs(locale.x - timezone.x) > 2) assert.ok(Math.abs(locale.y - timezone.y) <= 2, 'preference field groups must align; timezone includes its own search and preview');
        const form = page.locator('.account-profile-form');
        const input = form.locator('input[name=display_name]'), submit = form.locator('button[type=submit]');
        const initial = await input.inputValue();
        assert.ok(await submit.isDisabled());
        await input.fill('Новое тестовое имя');
        assert.ok(await submit.isEnabled());
        await form.locator('button[type=reset]').click();
        await form.locator('button[type=submit]:disabled').waitFor();
        assert.equal(await input.inputValue(), initial);
        assert.ok(await submit.isDisabled());
        await input.fill('Новое тестовое имя');
        await form.evaluate(form => form.addEventListener('submit', e => e.preventDefault()));
        await submit.click();
        assert.equal(await form.getAttribute('data-state'), 'saving');
        assert.ok(await submit.isDisabled());
      }
    }
    for (const width of [320, 390, 1440]) for (const path of ['/account', '/integrations/calendar', '/upload-preview']) {
      await page.setViewportSize({width, height: 900});
      await page.goto(`${base}/settings${path}`);
      if (path === '/upload-preview') await page.locator('dialog').evaluate(el => el.showModal());
      const tips = page.locator(path === '/account' ? '.account-email-form .cabinet-tooltip' : path === '/upload-preview' ? 'dialog .cabinet-tooltip' : '.settings-control-row__title .cabinet-tooltip');
      for (const tip of await tips.all()) {
        await tip.locator('button').click();
        await tip.locator('.cabinet-tooltip__body').waitFor({state:'visible'});
        // Measure after the native CSS transition, not an intermediate animation frame.
        await page.waitForFunction(el => getComputedStyle(el).opacity === '1', await tip.locator('.cabinet-tooltip__body').elementHandle());
        const bounds = await tip.evaluate(el => {
          const body = el.querySelector('.cabinet-tooltip__body').getBoundingClientRect();
          return {left: body.left, right: body.right, min: 0, max: innerWidth};
        });
        assert.ok(bounds.left >= bounds.min && bounds.right <= bounds.max, JSON.stringify({path,width,bounds}));
        await page.keyboard.press('Escape');
        assert.ok(await tip.locator('.cabinet-tooltip__body').isHidden());
      }
    }
    for (const query of ['device_revoke=failed', 'device_revoke=reauth_required', 'mode=unavailable']) {
      await page.goto(`${base}/settings/account?${query}`);
      const selector = query.includes('failed') ? '.settings-status--error' : query.includes('reauth') ? '.settings-status--warning' : '.settings-unavailable-card';
      assert.ok(await page.locator(selector).isVisible());
    }
    await page.goto(`${base}/settings/account?theme=light`);
    await page.locator('#account-display-name').focus();
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').getAttribute('id'), 'account-locale');
    await page.keyboard.press('Shift+Tab');
    assert.equal(await page.locator(':focus').getAttribute('id'), 'account-display-name');
    assert.ok(await page.locator(':focus').evaluate(el => getComputedStyle(el).outlineStyle !== 'none' || getComputedStyle(el).boxShadow !== 'none'));
    await page.emulateMedia({forcedColors: 'active'});
    assert.ok(await page.locator(':focus').evaluate(el => getComputedStyle(el).outlineStyle !== 'none'));
    await page.emulateMedia({forcedColors: 'none'});
    // 200% content scale at 1440px, with a 720 CSS-pixel layout viewport.
    await page.setViewportSize({width: 1440, height: 1000});
    await page.evaluate(() => {document.documentElement.style.zoom = '2';});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    const noJS = await browser.newContext({javaScriptEnabled: false});
    const plain = await noJS.newPage();
    for (const prefix of ['', '/desktop']) {
      await plain.goto(`${base}${prefix}/settings/account`);
      const form = plain.locator('.account-profile-form');
      assert.ok(await form.locator('button[type=submit]').isEnabled());
      let posted;
      await plain.route('**/settings/account/profile', async route => {
        posted = route.request();
        await route.fulfill({status: 200, contentType: 'text/html', body: '<p>Синтетический POST принят</p>'});
      });
      await form.locator('input[name=display_name]').fill('Без JavaScript');
      await form.locator('button[type=submit]').click();
      assert.equal(posted.method(), 'POST');
      assert.equal(new URLSearchParams(posted.postData()).get('csrf_token'), 'synthetic-csrf');
    }
    await noJS.close();
    fs.writeFileSync('/tmp/graf-f246-matrix.json', JSON.stringify(results, null, 2));
    for (const [name, path, width] of [['account-light','/account?theme=light',1440], ['account-dark','/account?theme=dark',1440], ['account-narrow','/account?theme=light',390], ['overview','?theme=dark',1440], ['billing','/billing?theme=light',1440]]) {
      await page.setViewportSize({width,height:1000});
      await page.goto(`${base}/settings${path}`);
      await page.screenshot({path:`/tmp/graf-f246-${name}.png`});
    }
    console.log(JSON.stringify({geometry: results.length, forms: 'pass', outcomes: 'pass', keyboard: 'pass', forcedColors: 'pass', scale200: 'pass', noJS: 'pass', tooltips: 'pass'}));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
