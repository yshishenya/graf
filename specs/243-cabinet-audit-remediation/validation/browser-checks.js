async (page) => {
  const origin = await page.evaluate(() => location.origin);
  const failures = [];
  let checks = 0;
  const check = (ok, label, detail = null) => {
    checks += 1;
    if (!ok) failures.push({ label, detail });
  };
  const settle = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const bounds = async (locator) => locator.evaluate(element => {
    const rect = element.getBoundingClientRect();
    return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom,
      width: innerWidth, height: innerHeight, scroll: document.documentElement.scrollWidth };
  });
  const fits = (rect) => rect.left >= 7 && rect.top >= 7 && rect.right <= rect.width - 7 && rect.bottom <= rect.height - 7;
  for (const system of ["light", "dark"]) {
    await page.emulateMedia({ colorScheme: system });
    for (const theme of ["system", "light", "dark"]) {
      for (const width of [375, 550, 768, 1200]) {
        await page.setViewportSize({ width, height: 812 });
        for (const path of ["/settings/account", "/settings/integrations/calendar"]) {
          await page.goto(`${origin}${path}?theme=${theme}`);
          const label = `${system}/${theme}/${width}${path}`;
          check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${label}:hidden-overflow`);
          const triggers = page.locator(".cabinet-tooltip__trigger");
          for (let index = 0; index < await triggers.count(); index += 1) {
            const trigger = triggers.nth(index);
            await trigger.scrollIntoViewIfNeeded();
            await trigger.focus();
            await settle();
            const body = page.locator(`#${await trigger.getAttribute("popovertarget")}`);
            check(await body.evaluate(el => el.matches(":popover-open")), `${label}:keyboard-open-${index}`);
            const rect = await bounds(body);
            check(fits(rect), `${label}:tooltip-bounds-${index}`, rect);
            await page.keyboard.press("Escape");
            await settle();
            check(!await body.evaluate(el => el.matches(":popover-open")), `${label}:escape-${index}`);
          }
          await page.locator("[data-profile-menu-trigger]").click();
          const menu = page.locator("[data-profile-menu]");
          const disclosure = menu.locator("details").last();
          await disclosure.locator("summary").click();
          await settle();
          const submenu = disclosure.locator("[data-profile-menu-submenu]");
          await submenu.scrollIntoViewIfNeeded();
          check(fits(await bounds(submenu)), `${label}:submenu-bounds`, await bounds(submenu));
          check(await menu.locator(".sidebar-profile-menu__item > span:last-child").evaluateAll(es => es.every(e => e.scrollWidth <= e.clientWidth + 1)), `${label}:menu-label-wrap`);
          await page.keyboard.press("Escape");
          check(await menu.isHidden(), `${label}:menu-escape`);
        }
      }
    }
  }
  // Resize an open disclosure and exercise short windows / 200% layout zoom.
  for (const dimensions of [{ width: 550, height: 812 }, { width: 550, height: 400 }, { width: 375, height: 400 }]) {
    await page.setViewportSize(dimensions);
    await page.goto(`${origin}/settings/account`);
    await page.evaluate(() => { document.documentElement.style.zoom = "2"; });
    const trigger = page.locator(".cabinet-tooltip__trigger").first();
    await trigger.scrollIntoViewIfNeeded();
    await trigger.click();
    await settle();
    const tip = page.locator(".cabinet-tooltip__body:popover-open");
    check(fits(await bounds(tip)), `zoom:${JSON.stringify(dimensions)}`, await bounds(tip));
    await page.keyboard.press("Escape");
    await page.locator("[data-profile-menu-trigger]").click();
    const menu = page.locator("[data-profile-menu]");
    await menu.locator("details").last().locator("summary").click();
    await settle();
    check(fits(await bounds(menu)), `zoom-menu:${JSON.stringify(dimensions)}`, await bounds(menu));
    const lastItem = menu.locator("details").last().locator("[data-profile-menu-submenu] button").last();
    await lastItem.scrollIntoViewIfNeeded();
    check(fits(await bounds(lastItem)), `zoom-menu-last-item:${JSON.stringify(dimensions)}`, await bounds(lastItem));
    check(await menu.locator(".sidebar-profile-menu__item > span:last-child").evaluateAll(es => es.every(e => e.scrollWidth <= e.clientWidth + 1)), `zoom-menu-label-wrap:${JSON.stringify(dimensions)}`);
    await page.keyboard.press("Escape");
  }
  await page.setViewportSize({ width: 550, height: 812 });
  await page.goto(`${origin}/settings/account`);
  const hoverTrigger = page.locator(".cabinet-tooltip__trigger").first();
  const hoverBody = page.locator(`#${await hoverTrigger.getAttribute("popovertarget")}`);
  await hoverTrigger.hover();
  check(await hoverBody.evaluate(el => el.matches(":popover-open")), "hover:opens");
  await hoverBody.hover();
  await page.waitForTimeout(200);
  check(await hoverBody.evaluate(el => el.matches(":popover-open")), "hover:body-remains-open");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(200);
  check(!await hoverBody.evaluate(el => el.matches(":popover-open")), "hover:escape-stays-closed");
  await hoverTrigger.click();
  await page.locator("h1").first().click();
  check(!await hoverBody.evaluate(el => el.matches(":popover-open")), "tooltip:outside-dismiss");
  for (const theme of ["light", "dark"]) {
    await page.goto(`${origin}/settings/integrations/calendar?theme=${theme}`);
    await page.locator('[data-calendar-provider-open^="calendar-disconnect-dialog-"]').first().click();
    const dialog = page.locator(".calendar-disconnect-dialog[open]");
    check(await dialog.evaluate(el => {
      const probe = document.createElement("span");
      probe.style.color = "var(--danger-border)";
      el.append(probe);
      const expected = getComputedStyle(probe).color;
      probe.remove();
      return getComputedStyle(el).borderTopColor === expected && parseFloat(getComputedStyle(el).borderTopWidth) > 0;
    }), `calendar:${theme}:warning-border`);
    await page.keyboard.press("Escape");
  }
  const context = await page.context().browser().newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 812 } });
  try {
    const noJS = await context.newPage();
    for (const path of ["/settings/account", "/settings/integrations/calendar"]) {
      await noJS.goto(`${origin}${path}`);
      check(await noJS.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `no-js:hidden:${path}`);
      const trigger = noJS.locator(".cabinet-tooltip__trigger").first();
      await trigger.focus();
      await noJS.keyboard.press("Enter");
      const body = noJS.locator(".cabinet-tooltip__body:popover-open");
      check(await body.count() === 1, `no-js:enter:${path}`);
      check(fits(await bounds(body)), `no-js:bounds:${path}`, await bounds(body));
      await noJS.keyboard.press("Escape");
      check(await body.count() === 0, `no-js:escape:${path}`);
      await trigger.focus();
      await noJS.keyboard.press("Space");
      check(await body.count() === 1, `no-js:space:${path}`);
      await noJS.locator("h1").first().click();
      check(await body.count() === 0, `no-js:outside-dismiss:${path}`);
    }
  } finally { await context.close(); }
  return { checks, failures };
}
