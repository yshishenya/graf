async (page) => {
  const origin = await page.evaluate(() => location.origin);
  const checks = [];
  for (const embedded of [false, true]) {
    for (const theme of ['light', 'dark', 'system']) {
      await page.goto(`${origin}${embedded ? '/desktop' : ''}/settings/account?theme=${theme}`);
      for (const width of [1440, 980, 768, 390, 320, 981, 1440]) {
        await page.setViewportSize({width, height: 812});
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        const trigger = page.locator('[data-profile-menu-trigger]');
        if (await trigger.count() !== 1 || !await trigger.isVisible()) throw Error(`profile unavailable ${embedded}/${theme}/${width}`);
        await trigger.click();
        const menu = page.locator('[data-profile-menu]');
        await menu.waitFor({state:'visible'});
        const bounds = await menu.boundingBox();
        if (!bounds || bounds.x < 0 || bounds.y < 0 || bounds.x + bounds.width > width + 1 || bounds.y + bounds.height > 813) throw Error(`menu outside viewport ${JSON.stringify(bounds)}`);
        if (await menu.locator('form[data-account-preferences]').count() !== 1) throw Error('theme form lost');
        await page.keyboard.press('Escape');
        if (await trigger.getAttribute('aria-expanded') !== 'false' || !await trigger.evaluate(el => el === document.activeElement)) throw Error('focus not restored');
        checks.push({embedded,theme,width});
      }
    }
  }
  return {passed:checks.length, checks};
}
