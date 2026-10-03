// Run against tests.fixtures.settings_visual_ui_harness (synthetic data only).
const {chromium, webkit} = require('playwright');
const assert = require('node:assert/strict');
const origin = process.env.SETTINGS_PREVIEW_URL || 'http://127.0.0.1:8897';

(async () => {
  for (const [name, engine] of Object.entries({chromium, webkit})) {
    const browser = await engine.launch({headless: true});
    try {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      let checks = 0;
      for (const [width, height] of [[1080, 620], [744, 530], [744, 400], [560, 530], [375, 620]]) {
        await page.setViewportSize({width, height});
        const response = await page.goto(`${origin}/desktop/meetings?theme=light`);
        assert.equal(response.status(), 200);
        assert.match(await page.title(), /Мои встречи/);
        const trigger = page.getByRole('button', {name: 'Открыть меню профиля', exact: true});
        await trigger.click();
        const menu = page.locator('[data-profile-menu]');
        for (const title of ['Вид', 'Решение проблем', 'Документация']) {
          const details = menu.locator('.sidebar-profile-menu__disclosure').filter({hasText: title});
          await details.locator('summary').click();
          const inline = width <= 520 || (width === 560 && title === 'Документация');
          await page.waitForFunction(({title, inline}) => {
            const d = [...document.querySelectorAll('.sidebar-profile-menu__disclosure')]
              .find(el => el.querySelector('summary').textContent.trim() === title);
            return d.open && d.classList.contains('is-inline') === inline
              && d.querySelector('[data-profile-menu-submenu]').matches(':popover-open') === !inline;
          }, {title, inline}, {timeout: 5000}).catch(async error => {
            const state = await details.evaluate(d => ({open: d.open, classes: d.className,
              panel: d.querySelector('[data-profile-menu-submenu]').outerHTML.slice(0, 150)}));
            throw new Error(`${name} ${width}x${height} ${title}: ${JSON.stringify(state)}`, {cause: error});
          });
          const geometry = await details.evaluate(d => {
            const s = d.querySelector('[data-profile-menu-submenu]');
            const m = d.closest('[data-profile-menu]');
            return {panel: s.getBoundingClientRect().toJSON(), menu: m.getBoundingClientRect().toJSON(),
              count: document.querySelectorAll('[data-profile-menu-submenu]:popover-open').length,
              overflow: getComputedStyle(m).overflowY};
          });
          assert.equal(geometry.overflow, 'auto');
          assert(geometry.menu.top >= 7 && geometry.menu.bottom <= height - 7);
          assert.equal(geometry.count, inline ? 0 : 1, 'only the current panel stays open');
          if (!inline) {
            assert(geometry.panel.left >= geometry.menu.right - 2, `${name}: ${title} opens right`);
            assert(geometry.panel.right <= width - 7 && geometry.panel.top >= 7
              && geometry.panel.bottom <= height - 7, `${name}: ${title} stays inside viewport`);
          }
          checks++;
        }
        await page.mouse.move(width - 1, height - 1);
        await page.keyboard.press('Escape');
        assert(await menu.isHidden());
        assert(await trigger.evaluate(el => el === document.activeElement));
        assert.equal(await page.locator('[data-profile-menu-submenu]:popover-open').count(), 0);
        await trigger.press('Enter');
        const view = menu.locator('summary').filter({hasText: /^Вид$/});
        await view.press('Enter');
        await page.getByRole('radio', {name: /Светлая/}).waitFor({state: 'visible'});
        // macOS WebKit's default keyboard mode uses Option+Tab for radio controls,
        // including in a plain native details/summary without any GRAF code.
        await view.press(name === 'webkit' ? 'Alt+Tab' : 'Tab');
        const focus = await page.evaluate(() => ({theme: document.activeElement?.matches('input[name="theme"]'),
          element: document.activeElement?.outerHTML.slice(0, 250)}));
        assert(focus.theme, `${name} ${width}x${height}: keyboard reaches theme options; ${focus.element}`);
        await page.keyboard.press('Escape');
        checks++;
      }
      for (const width of [1440, 375]) {
        await page.setViewportSize({width, height: 620});
        await page.goto(`${origin}/meetings?theme=light`);
        await page.getByRole('button', {name: 'Открыть меню профиля', exact: true}).click();
        await page.getByText('Вид', {exact: true}).click();
        await page.getByRole('radio', {name: /Светлая/}).waitFor({state: 'visible'});
        await page.waitForFunction(expected => document.querySelectorAll('[data-profile-menu-submenu]:popover-open').length === expected,
          width > 520 ? 1 : 0, {timeout: 5000});
        assert.equal(await page.locator('[data-profile-menu-submenu]:popover-open').count(), width > 520 ? 1 : 0);
        await page.keyboard.press('Escape');
        assert(await page.locator('[data-profile-menu]').isHidden());
        checks++;
      }
      // Scrolling the owner row away must not leave a detached floating panel.
      await page.setViewportSize({width: 744, height: 300});
      await page.goto(`${origin}/desktop/meetings?theme=light`);
      await page.getByRole('button', {name: 'Открыть меню профиля', exact: true}).click();
      await page.getByText('Вид', {exact: true}).click();
      await page.locator('[data-profile-menu]').evaluate(el => { el.scrollTop = el.scrollHeight; });
      await page.waitForFunction(() => !document.querySelector('.sidebar-profile-menu__disclosure').open
        && !document.querySelector('[data-profile-menu-submenu]:popover-open'));
      assert.equal(await page.locator('[data-profile-menu-submenu]:popover-open').count(), 0);
      assert(await page.getByRole('button', {name: 'Закрыть GRAF', exact: true}).isVisible());
      await page.setViewportSize({width: 560, height: 300});
      await page.getByText('Документация', {exact: true}).click();
      const documentation = page.locator('.sidebar-profile-menu__disclosure').filter({hasText: 'Документация'});
      await page.waitForFunction(() => document.querySelector('.sidebar-profile-menu__disclosure.is-inline[open]'));
      const scrollTop = await page.locator('[data-profile-menu]').evaluate(el => {
        el.scrollTop = el.scrollHeight;
        return el.scrollTop;
      });
      // Wait two frames for the scroll handler, not an arbitrary timing delay.
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      assert(await documentation.evaluate(el => el.open && el.classList.contains('is-inline')));
      assert.equal(await page.locator('[data-profile-menu]').evaluate(el => el.scrollTop), scrollTop);
      // The synthetic harness deliberately redirects saves; verify recoverable failure,
      // not production persistence. The taller error must also remain inside the viewport.
      await page.keyboard.press('Escape');
      await page.setViewportSize({width: 744, height: 400});
      await page.getByRole('button', {name: 'Открыть меню профиля', exact: true}).click();
      await page.getByText('Вид', {exact: true}).click();
      await page.getByRole('radio', {name: 'Темная', exact: true}).check();
      await page.getByRole('button', {name: 'Повторить', exact: true}).waitFor();
      assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
      const panel = page.locator('[data-profile-menu-submenu]:popover-open');
      const rect = await panel.boundingBox();
      assert(rect.y >= 7 && rect.y + rect.height <= 393);
      const search = page.getByRole('searchbox', {name: 'Поиск встреч'});
      const searchRect = await search.boundingBox();
      await search.click({position: {x: searchRect.width - 8, y: searchRect.height / 2}});
      assert.equal(await page.locator('[data-profile-menu-submenu]:popover-open').count(), 0);
      assert.deepEqual(errors, [], `${name}: no runtime errors`);
      console.log(`${name}: ${checks + 3} profile-menu scenarios passed`);
    } finally {
      await browser.close();
    }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
