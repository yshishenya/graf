async page => {
  const check=(ok,msg)=>{if(!ok)throw new Error(msg)};
  await page.goto('http://127.0.0.1:8766/prototype.html');
  for(const width of [320,390,768,820,1024,1440]){
    await page.setViewportSize({width,height:900});
    for(const section of ['account','workspace','billing','recording','summaries','calendar','notifications']){
      await page.evaluate(section=>go(section),section);
      check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Overflow '+width+' '+section);
    }
  }
  await page.setViewportSize({width:1024,height:768});
  await page.evaluate(()=>go('recording'));
  await page.locator('#app-search').fill('Zoom');
  check(await page.locator('[data-rule=zoom]').count()===1,'Zoom visible');
  await page.locator('[data-rule=zoom]').selectOption('never');
  await page.waitForFunction(()=>document.querySelector('#save-status').textContent==='Сохранено');
  await page.evaluate(()=>go('notifications'));
  await page.locator('[data-pref=reminders]').uncheck();
  await page.waitForFunction(()=>document.querySelector('[data-pref=offsetMinutes]').disabled);
  for(const scenario of ['denied','notDetermined','error','empty','offline','browser','recording','normal']){
    await page.locator('#scenario').selectOption(scenario);
    check(await page.locator('h1').isVisible(),'Scenario '+scenario);
  }
  await page.locator('#scenario').selectOption('error');
  await page.locator('[data-pref=sound]').click();
  await page.waitForFunction(()=>document.querySelector('#save-status')?.textContent.includes('Не удалось сохранить'));
  await page.locator('#scenario').selectOption('offline');
  await page.locator('[data-action=reconnect]').click();
  check(await page.locator('#scenario').inputValue()==='normal','Reconnect');
  await page.locator('#theme-lab').click();
  check(await page.locator('html').getAttribute('data-theme')==='light','Light theme');
  await page.locator('[data-nav=meetings]').first().click();
  await page.getByRole('button',{name:'Настройки',exact:true}).click();
  check(await page.locator('h1').innerText()==='Аккаунт','Return to settings');
  return {responsive:42,scenarios:8,recordingSave:true,notifications:true,saveError:true,recovery:true,theme:true,returnPath:true};
}
