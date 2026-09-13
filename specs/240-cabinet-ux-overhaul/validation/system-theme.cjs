// Run against tests.fixtures.calendar_visual_ui_harness on loopback.
const assert = require('node:assert/strict');
const { setTimeout: delay } = require('node:timers/promises');
const { chromium, webkit } = require('playwright');
const base = process.env.GRAF_QA_BASE_URL || 'http://127.0.0.1:8765';
assert.equal(new URL(base).hostname, '127.0.0.1');
const properties = ['color-scheme', 'background-color', 'color', 'border-top-color',
  '--bg', '--panel', '--surface', '--surface-2', '--surface-3', '--text', '--muted',
  '--subtle', '--line', '--line-soft', '--accent', '--accent-solid', '--accent-foreground'];
const selectors = ['body', '.sidebar', '.cabinet-main', '.detail-page-main',
  '.detail-playback', '.settings-page', '.calendar-settings', '.primary'];
async function palette(page) {
  return page.evaluate(({ selectors, properties }) => Object.fromEntries(
    selectors.map(selector => [selector, [...document.querySelectorAll(selector)].map(element => {
      const style = getComputedStyle(element);
      return properties.map(property => style.getPropertyValue(property).trim());
    })])
  ), { selectors, properties });
}

async function expectPalette(page, expected, message) {
  // WebKit recomputes painted colors after the media-query change; page JS may be disabled.
  for (let attempt = 0; ; attempt++) {
    try { assert.deepEqual(await palette(page), expected, message); return; }
    catch (error) { if (attempt === 40) throw error; }
    await delay(25);
  }
}

(async () => {
  for (const [name, engine] of Object.entries({ chromium, webkit })) {
    const browser = await engine.launch(name === 'chromium' ? { channel: 'chrome' } : {});
    let checks = 0;
    try {
      for (const javaScriptEnabled of [true, false]) {
        const context = await browser.newContext({ javaScriptEnabled, reducedMotion: 'reduce' });
        if (process.env.GRAF_THEME_CSS) {
          await context.route(/\/cabinet\.css(?:\?|$)/, route => route.fulfill({
            path: process.env.GRAF_THEME_CSS, contentType: 'text/css',
          }));
        }
        const page = await context.newPage();
        for (const width of [390, 1440]) {
          await page.setViewportSize({ width, height: 900 });
          for (const prefix of ['', '/desktop']) {
            for (const path of ['/meetings?mode=populated', '/meetings/synthetic-theme?',
              '/settings/integrations/calendar?mode=connected']) {
              const url = base + prefix + path;
              const expected = {};
              for (const theme of ['light', 'dark']) {
                await page.emulateMedia({ colorScheme: theme });
                await page.goto(`${url}&theme=${theme}`);
                assert.ok(await page.locator('.app-shell').count());
                expected[theme] = await palette(page);
                await page.emulateMedia({ colorScheme: theme === 'dark' ? 'light' : 'dark' });
                await expectPalette(page, expected[theme], `${url}: explicit ${theme}`);
                checks++;
              }
              await page.goto(`${url}&theme=system`);
              for (const colorScheme of ['dark', 'light', 'dark']) {
                await page.emulateMedia({ colorScheme });
                await expectPalette(page, expected[colorScheme],
                  `${name} ${url} ${width}px JS=${javaScriptEnabled}: system ${colorScheme}`);
                checks++;
              }
            }
          }
        }
        await context.close();
      }
      console.log(`${name}: ${checks} palette comparisons PASS`);
    } finally {
      await browser.close();
    }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
