async (page) => {
  const origin = await page.evaluate(() => location.origin);
  const failures = []; let measured = 0;
  const measure = async (label) => {
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const result = await page.evaluate(() => {
      const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
      const ctx = canvas.getContext('2d', {willReadFrequently:true});
      const rgba = color => {ctx.clearRect(0,0,1,1);ctx.fillStyle=color;ctx.fillRect(0,0,1,1); const v=ctx.getImageData(0,0,1,1).data;return [v[0]/255,v[1]/255,v[2]/255,v[3]/255];};
      const over = (a,b) => [0,1,2].map(i=>a[i]*a[3]+b[i]*(1-a[3])).concat(1);
      const luminance = c => c.slice(0,3).reduce((v,x,i)=>v+(x<=0.04045?x/12.92:((x+0.055)/1.055)**2.4)*[.2126,.7152,.0722][i],0);
      const ratio = (a,b) => (Math.max(luminance(a),luminance(b))+.05)/(Math.min(luminance(a),luminance(b))+.05);
      const rows=[];
      const scope = document.querySelector('dialog[open]') || document;
      for (const el of scope.querySelectorAll(scope === document ? 'main *, [data-profile-menu] *' : '*')) {
        const r=el.getBoundingClientRect(); const cs=getComputedStyle(el);
        if (!r.width || !r.height || r.bottom<=0 || r.top>=innerHeight || cs.visibility!=='visible' || el.closest('[hidden],button:disabled,[aria-disabled="true"],svg')) continue;
        const direct=[...el.childNodes].some(n=>n.nodeType===Node.TEXT_NODE && n.textContent.trim());
        const placeholder=el instanceof HTMLInputElement && el.placeholder;
        if (!direct && !placeholder) continue;
        let bg=[1,1,1,1], opacity=1; const chain=[];
        for(let p=el;p;p=p.parentElement) chain.unshift(p);
        for(const p of chain) { const style=getComputedStyle(p); bg=over(rgba(style.backgroundColor),bg);opacity*=Number(style.opacity); }
        const fg=rgba(placeholder?getComputedStyle(el,'::placeholder').color:cs.color); fg[3]*=opacity;
        const contrast=ratio(over(fg,bg),bg);
        const large=parseFloat(cs.fontSize)>=24 || (parseFloat(cs.fontSize)>=18.66 && parseInt(cs.fontWeight)>=700);
        rows.push({tag:el.tagName,class:el.className,text:(placeholder||el.textContent.trim()).slice(0,70),contrast,threshold:large?3:4.5});
      }
      return rows;
    });
    if (!result.length) throw Error(`No visible text ${label}`);
    measured+=result.length;
    failures.push(...result.filter(x=>x.contrast<x.threshold).map(x=>({label,...x})));
  };
  for(const system of ['light','dark']) {
    await page.emulateMedia({colorScheme:system,reducedMotion:"reduce"});
    for(const theme of ['light','dark','system']) {
      for(const width of [390,1440]) {
        await page.setViewportSize({width,height:900});
        for(const path of ['/meetings?mode=populated','/qa/list/empty','/qa/list/filtered','/qa/detail/ready','/qa/detail/processing','/qa/detail/failed','/qa/billing/ready','/qa/settings/account']) {
          await page.goto(`${origin}${path}${path.includes('?')?'&':'?'}theme=${theme}`);
          await measure(`${system}/${theme}/${width}${path}`);
        }
        await page.goto(`${origin}/meetings?mode=populated&theme=${theme}`);
        await page.locator('[data-manual-upload-open]').first().click();
        await measure(`${system}/${theme}/${width}/upload`);
        await page.keyboard.press('Escape');
        await page.locator('[data-profile-menu-trigger]').click();
        await measure(`${system}/${theme}/${width}/profile`);
        await page.locator('[data-profile-menu] details').first().locator('summary').click();
        await measure(`${system}/${theme}/${width}/themes`);
        await page.keyboard.press('Escape');
      }
    }
  }
  return {measured,failures};
}
