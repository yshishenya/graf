async (page) => {
  const origin = await page.evaluate(() => location.origin);
  const paths = ['list/ready','list/empty','list/filtered','detail/ready','detail/processing','detail/partial','detail/failed','detail/unavailable','settings/overview','settings/recording','settings/summaries','settings/workspace','settings/account','settings/notifications','shared/empty','shared/ready','shared/summary','shared/blocked','auth/login','auth/code','auth/signup','auth/signup-email','auth/error','auth/success','billing/ready','billing/blocked','billing/error'];
  const results = [];
  for (const system of ['light','dark']) {
    await page.emulateMedia({colorScheme:system});
    for (const theme of ['light','dark','system']) {
      for (const embedded of [false,true]) {
        for (const width of [320,390,768,1024,1440]) {
          await page.setViewportSize({width,height:900});
          for (const path of paths) {
            const response = await page.goto(`${origin}/qa/${path}?theme=${theme}&embedded=${embedded ? 1 : 0}`);
            const geometry = await page.evaluate(() => {
              const main = document.querySelector('main');
              const rect = main?.getBoundingClientRect();
              return {title:document.querySelector('h1')?.textContent,scroll:document.documentElement.scrollWidth,width:innerWidth,main:rect && {left:rect.left,right:rect.right,width:rect.width}};
            });
            results.push({system,theme,embedded,width,path,status:response.status(),...geometry});
            if (response.status() !== 200 || !geometry.title || geometry.scroll > width + 1) throw Error(JSON.stringify(results.at(-1)));
          }
        }
      }
    }
  }
  return {passed:results.length,results};
}
