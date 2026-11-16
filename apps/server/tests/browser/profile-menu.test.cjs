// Run against tests.fixtures.settings_visual_ui_harness (synthetic data only).
const {chromium, webkit} = require('playwright');
const assert = require('node:assert/strict');
const origin = process.env.SETTINGS_PREVIEW_URL || 'http://127.0.0.1:8897';

async function crossSubmenuGap(page, row, side) {
  const gap = await row.evaluate((anchor, side) => {
    const details = anchor.closest('details');
    const menu = anchor.closest('[data-profile-menu]').getBoundingClientRect();
    const submenu = details.querySelector('[data-profile-menu-submenu]');
    const panel = submenu.getBoundingClientRect();
    const a = anchor.getBoundingClientRect();
    const x = side === 'right' ? (menu.right + panel.left) / 2 : (menu.left + panel.right) / 2;
    const y = (Math.max(a.top, panel.top) + Math.min(a.bottom, panel.bottom)) / 2;
    return {x, y, hit: submenu.contains(document.elementFromPoint(x, y))};
  }, side);
  assert(gap.hit, `${side}: the gap belongs to the submenu's pointer target`);
  await page.mouse.move(gap.x, gap.y);
  // Pause longer than the menu's pointer-leave timer, as a slow mouse user can.
  await page.waitForTimeout(220);
  assert(await row.evaluate(anchor => anchor.closest('details').open), `${side}: crossing the gap keeps the submenu open`);
  const option = row.locator('..').locator('label:has(input[name="theme"])').first();
  await option.hover();
  assert(await option.evaluate(el => el.matches(':hover')), `${side}: the mouse reaches a theme option`);
}

(async () => {
  for (const [name, engine] of Object.entries({chromium, webkit})) {
    const browser = await engine.launch({headless: true});
    try {
      const page = await browser.newPage();
      const ax = name === 'chromium' ? await page.context().newCDPSession(page) : null;
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      let checks = 0;
      for (const [width, height] of [[1080, 620], [744, 530], [744, 400], [560, 530], [500, 620], [480, 620], [375, 620]]) {
        await page.setViewportSize({width, height});
        const response = await page.goto(`${origin}/desktop/meetings?theme=light`);
        assert.equal(response.status(), 200);
        assert.match(await page.title(), /Мои встречи/);
        // Simulate a classic scrollbar narrowing the row in engines with overlay scrollbars.
        if (width === 744 && height === 400) await page.addStyleTag({
          content: '[data-profile-menu] { padding-inline-end: 24px; }'
        });
        const trigger = page.getByRole('button', {name: 'Открыть меню профиля', exact: true});
        await trigger.click();
        const menu = page.locator('[data-profile-menu]');
        let axIds;
        if (ax) {
          const {root} = await ax.send('DOM.getDocument');
          ({nodeIds: axIds} = await ax.send('DOM.querySelectorAll', {nodeId: root.nodeId,
            selector: '[data-profile-menu] .sidebar-profile-menu__disclosure > summary'}));
          assert.equal(axIds.length, 3);
        }
        for (const [index, title] of ['Вид', 'Решение проблем', 'Документация'].entries()) {
          const details = menu.locator('.sidebar-profile-menu__disclosure').filter({hasText: title});
          const summary = details.locator('summary');
          const checkDisclosure = async expanded => {
            assert.equal(await summary.ariaSnapshot(), `- text: ${title}`);
            assert.equal(await details.evaluate(el => el.open), expanded);
            if (ax) {
              const {nodes: [node]} = await ax.send('Accessibility.getPartialAXTree',
                {nodeId: axIds[index], fetchRelatives: false});
              assert.equal(node.name.value, title);
              assert.equal(node.properties.find(property => property.name === 'expanded')?.value.value, expanded);
            }
          };
          await checkDisclosure(false);
          await summary.click();
          const inline = width <= 480 || (width === 500 && title !== 'Вид')
            || (width === 560 && title === 'Документация');
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
          await checkDisclosure(true);
          assert.match(await summary.evaluate(el => getComputedStyle(el, '::after').content), /›/);
          const geometry = await details.evaluate(d => {
            const s = d.querySelector('[data-profile-menu-submenu]');
            const m = d.closest('[data-profile-menu]');
            return {panel: s.getBoundingClientRect().toJSON(), menu: m.getBoundingClientRect().toJSON(),
              count: document.querySelectorAll('[data-profile-menu-submenu]:popover-open').length,
              overflow: getComputedStyle(m).overflowY, inset: m.getBoundingClientRect().right
                - d.querySelector('summary').getBoundingClientRect().right};
          });
          assert.equal(geometry.overflow, 'auto');
          if (width === 744 && height === 400) assert(geometry.inset >= 24);
          assert(geometry.menu.top >= 7 && geometry.menu.bottom <= height - 7);
          assert.equal(geometry.count, inline ? 0 : 1, 'only the current panel stays open');
          if (!inline) {
            assert(Math.abs(geometry.panel.left - geometry.menu.right - 8) <= 2, `${name}: ${title} opens right`);
            assert(geometry.panel.right <= width - 7 && geometry.panel.top >= 7
              && geometry.panel.bottom <= height - 7, `${name}: ${title} stays inside viewport`);
          }
          if (width === 1080 && title === 'Вид') await crossSubmenuGap(page, details.locator('summary'), 'right');
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
      // Synthetic right-edge placement exercises the real fallback, including CSS zoom.
      for (const zoom of [1, 2]) {
        await page.setViewportSize({width: 1200, height: 620});
        await page.mouse.move(1199, 619);
        await page.goto(`${origin}/desktop/meetings?theme=light`);
        await page.addStyleTag({content: `html { zoom: ${zoom}; } [data-profile-menu] { left: auto; right: 8px; }`});
        const edgeTrigger = page.getByRole('button', {name: 'Открыть меню профиля', exact: true});
        await edgeTrigger.click();
        const edgeMenu = page.locator('[data-profile-menu]');
        const edgeView = edgeMenu.locator('summary').filter({hasText: /^Вид$/});
        await edgeView.click();
        await page.waitForFunction(() => {
          const details = document.querySelector('.sidebar-profile-menu__disclosure');
          return details.open && (details.classList.contains('is-inline')
            || details.querySelector('[data-profile-menu-submenu]').matches(':popover-open'));
        });
        const edge = await edgeView.evaluate(summary => {
          const details = summary.closest('details');
          return {open: details.open, inline: details.classList.contains('is-inline'),
            menu: details.closest('[data-profile-menu]').getBoundingClientRect().toJSON(),
            viewportWidth: document.documentElement.clientWidth,
            panel: details.querySelector('[data-profile-menu-submenu]').getBoundingClientRect().toJSON(),
            count: document.querySelectorAll('[data-profile-menu-submenu]:popover-open').length,
            overflow: document.documentElement.scrollWidth > innerWidth};
        });
        assert(edge.open && !edge.inline, `${name} zoom=${zoom}: available left side must not become inline`);
        assert(edge.menu.right + 8 + edge.panel.width > edge.viewportWidth - 8, 'right side does not fit');
        assert(edge.menu.left - edge.panel.width - 8 >= 8, 'left side fits');
        assert.equal(edge.count, 1);
        assert(Math.abs(edge.panel.right - (edge.menu.left - 8)) <= 2, `${name}: panel opens left`);
        assert(!edge.overflow && edge.panel.left >= 7 && edge.panel.right <= edge.viewportWidth - 7
          && edge.panel.top >= 7 && edge.panel.bottom <= 613);
        await crossSubmenuGap(page, edgeView, 'left');
        await edgeView.press(name === 'webkit' ? 'Alt+Tab' : 'Tab');
        assert(await page.evaluate(() => document.activeElement?.matches('input[name="theme"]')));
        await page.keyboard.press('Escape');
        assert(await edgeMenu.isHidden());
        assert(await edgeTrigger.evaluate(el => el === document.activeElement));
        assert.equal(await page.locator('[data-profile-menu-submenu]:popover-open').count(), 0);
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
      // Open-menu theme and keyboard parity, not native app or persistence proof.
      for (const width of [1080, 375]) {
        const styles = {};
        for (const [theme, colorScheme] of [['light', 'light'], ['dark', 'dark'], ['system', 'light'], ['system', 'dark']]) {
          await page.emulateMedia({colorScheme});
          await page.setViewportSize({width, height: 620});
          await page.mouse.move(width - 1, 619); // Do not let a previous pointer hover open the keyboard target.
          assert.equal((await page.goto(`${origin}/desktop/meetings?theme=${theme}`)).status(), 200);
          const trigger = page.getByRole('button', {name: 'Открыть меню профиля', exact: true});
          await trigger.press('Enter');
          const menu = page.locator('[data-profile-menu]');
          const view = menu.locator('summary').filter({hasText: /^Вид$/});
          await view.press('Enter');
          await menu.getByRole('radio', {name: 'Системная', exact: true}).waitFor({state: 'visible'});
          const label = {light: 'Светлая', dark: 'Темная', system: 'Системная'}[theme];
          assert.equal(await menu.getByRole('radio', {checked: true}).count(), 1);
          assert.equal(await menu.getByRole('radio', {name: label, exact: true, checked: true}).count(), 1,
            'selected theme exposes its label and checked state separately');
          assert.match(await menu.locator('input[name="theme"]:checked + span')
            .evaluate(el => getComputedStyle(el, '::after').content), /✓/);
          const appearance = await menu.evaluate(el => ({
            background: getComputedStyle(el).backgroundColor, color: getComputedStyle(el).color
          }));
          if (theme === 'system') assert.deepEqual(appearance, styles[colorScheme], `${name}: system ${colorScheme}`);
          else styles[theme] = appearance;
          if (theme === 'dark') assert.notDeepEqual(styles.dark, styles.light, 'theme actually changes menu colors');
          await view.press(name === 'webkit' ? 'Alt+Tab' : 'Tab');
          assert(await page.evaluate(() => document.activeElement?.matches('input[name="theme"]:checked')));
          await page.keyboard.press(theme === 'light' ? 'ArrowDown' : 'ArrowUp');
          const selected = theme === 'dark' ? 'light' : 'dark';
          await page.waitForFunction(value => document.querySelector('input[name="theme"]:checked')?.value === value
            && document.documentElement.dataset.theme === value, selected);
          await page.getByRole('button', {name: 'Повторить', exact: true}).waitFor({state: 'visible'});
          // Error copy resizes the panel; wait for its ResizeObserver/rAF positioning.
          const positioned = await page.waitForFunction(() => {
            const el = document.querySelector('[data-profile-menu]');
            const details = el.querySelector('.sidebar-profile-menu__disclosure');
            const geometry = {menu: el.getBoundingClientRect().toJSON(), inline: details.classList.contains('is-inline'),
              panel: details.querySelector('[data-profile-menu-submenu]').getBoundingClientRect().toJSON(),
              overflow: document.documentElement.scrollWidth > innerWidth};
            return !geometry.overflow && geometry.menu.top >= 7 && geometry.menu.bottom <= innerHeight - 7
              && geometry.inline === (innerWidth === 375) && (geometry.inline ||
                (geometry.panel.left >= geometry.menu.right - 2 && geometry.panel.right <= innerWidth - 7
                  && geometry.panel.top >= 7 && geometry.panel.bottom <= innerHeight - 7)) ? geometry : false;
          }, undefined, {timeout: 5000});
          const geometry = await positioned.jsonValue();
          await positioned.dispose();
          assert(!geometry.overflow);
          assert(geometry.menu.top >= 7 && geometry.menu.bottom <= 613);
          assert.equal(geometry.inline, width === 375);
          if (!geometry.inline) assert(geometry.panel.left >= geometry.menu.right - 2
            && geometry.panel.right <= width - 7 && geometry.panel.top >= 7 && geometry.panel.bottom <= 613,
            `${name} ${theme}/${colorScheme} ${width}: ${JSON.stringify(geometry)}`);
          await page.keyboard.press('Escape');
          assert(await menu.isHidden());
          assert(await trigger.evaluate(el => el === document.activeElement));
          assert.equal(await page.locator('[data-profile-menu-submenu]:popover-open').count(), 0);
          checks++;
        }
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
      // At this width the floating panel can cover the search field.
      // Use the viewport corner, outside both menus even after the error grows.
      await page.mouse.click(743, 399);
      assert.equal(await page.locator('[data-profile-menu-submenu]:popover-open').count(), 0);
      assert.deepEqual(errors, [], `${name}: no runtime errors`);
      // Emulate a browser without Popover support for submenu elements only.
      const fallback = await browser.newPage({viewport: {width: 1080, height: 620}});
      try {
        const fallbackErrors = [];
        fallback.on('pageerror', error => fallbackErrors.push(error.message));
        await fallback.addInitScript(() => {
          const show = HTMLElement.prototype.showPopover;
          const matches = Element.prototype.matches;
          const query = Element.prototype.querySelector;
          const isSubmenu = el => el instanceof HTMLElement && el.hasAttribute('data-profile-menu-submenu');
          Object.defineProperty(HTMLElement.prototype, 'showPopover', {
            configurable: true, get() { return isSubmenu(this) ? undefined : show; }
          });
          Element.prototype.matches = function (selector) {
            if (isSubmenu(this) && selector === ':popover-open') throw new DOMException('Unsupported selector', 'SyntaxError');
            return matches.call(this, selector);
          };
          Element.prototype.querySelector = function (selector) {
            if (selector === '[data-profile-menu-submenu]:popover-open') throw new DOMException('Unsupported selector', 'SyntaxError');
            return query.call(this, selector);
          };
        });
        await fallback.goto(`${origin}/desktop/meetings?theme=light`);
        const trigger = fallback.getByRole('button', {name: 'Открыть меню профиля', exact: true});
        await trigger.press('Enter');
        await fallback.locator('[data-profile-menu] summary').filter({hasText: /^Вид$/}).press('Enter');
        await fallback.locator('.sidebar-profile-menu__disclosure.is-inline[open]').waitFor();
        assert(await fallback.getByRole('radio', {name: /Светлая/}).isVisible());
        await fallback.locator('[data-profile-menu]').dispatchEvent('scroll');
        await fallback.keyboard.press('Escape');
        assert(await trigger.evaluate(el => el === document.activeElement));
        assert.deepEqual(fallbackErrors, []);
        checks++;
      } finally {
        await fallback.close();
      }
      console.log(`${name}: ${checks + 3} profile-menu scenarios passed`);
    } finally {
      await browser.close();
    }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
