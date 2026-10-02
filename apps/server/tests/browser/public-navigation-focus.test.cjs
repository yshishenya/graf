// Regression: a completed opening animation must not leave focusable links
// while the menu closes. Only real local templates/controller; no network.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '../../src/twobrain_rec_server/public');
const template = fs.readFileSync(path.join(root, 'templates/public/landing.html'), 'utf8');
const header = template.match(/<header class="site-header"[\s\S]*?<\/header>/)[0];
const css = ['landing.css', 'content-header.css'].map(name => fs.readFileSync(path.join(root, 'static/public', name), 'utf8')).join('\n');
const controller = fs.readFileSync(process.argv[2] || path.join(root, 'static/public/landing.js'), 'utf8');
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const context = await browser.newContext({viewport: {width: 390, height: 700}});
    await context.route('**/*', route => route.abort());
    const page = await context.newPage();
    await page.setContent(`<style>${css}</style><a class="skip-link" href="#main">Skip</a>${header}<main id="main"><a href="#after" id="after">After header</a></main>`);
    await page.addScriptTag({content: controller});
    const button = page.locator('[data-menu-button]');
    const nav = page.locator('[data-mobile-nav]');
    await page.waitForTimeout(350);
    await button.focus();
    await page.keyboard.press('Space');
    assert.equal(await button.getAttribute('aria-expanded'), 'true');
    await page.waitForTimeout(350);
    await page.keyboard.press('Escape');
    assert.equal(await button.getAttribute('aria-expanded'), 'false');
    assert.equal(await button.evaluate(e => e === document.activeElement), true);
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').getAttribute('href'), '#after');
    await button.click();
    await nav.locator('a[href="/guides"]').focus();
    assert.equal(await page.locator(':focus').getAttribute('href'), '/guides');
    await page.setViewportSize({width: 1440, height: 700});
    await page.waitForTimeout(50);
    assert.equal(await button.getAttribute('aria-expanded'), 'false');
    const noJs = await browser.newContext({viewport: {width: 390, height: 700}, javaScriptEnabled: false});
    await noJs.route('**/*', route => route.abort());
    const fallback = await noJs.newPage();
    await fallback.setContent(`<style>${css}</style>${header}`);
    assert.equal(await fallback.locator('[data-mobile-nav] a[href="/guides"]').isVisible(), true);
    console.log('public_navigation_focus=pass');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
