async (page) => {
  const origin = await page.evaluate(() => location.origin);
  let passed = 0;
  for (const embedded of [false, true]) for (const width of [320, 390, 640, 768, 1440]) {
    await page.setViewportSize({width, height:812});
    await page.goto(`${origin}/qa/detail/ready?embedded=${embedded ? 1 : 0}`);
    const valid = await page.evaluate(() => {
      const a = document.querySelector('.speaker-manager-trigger').getBoundingClientRect();
      const b = document.querySelector('.playback-controls').getBoundingClientRect();
      return a.width > 0 && b.width > 0 && (a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top);
    });
    if (!valid) throw Error(`Playback controls overlap: ${embedded}/${width}`);
    passed++;
  }
  return {passed};
}
