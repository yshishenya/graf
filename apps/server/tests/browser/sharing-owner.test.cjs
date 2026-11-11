const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium, webkit} = require(require.resolve('playwright', {paths:[process.env.GRAF_NODE_MODULES || process.cwd()]}));
const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');
(async () => {
  const browser = await (process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium).launch({headless:true});
  try {
    for (const width of [320, 390, 480, 1440]) {
      const page = await browser.newPage({viewport:{width,height:800},colorScheme:width===390||width===1440?'dark':'light'});
      page.setDefaultTimeout(5000);
      const mutations=[], errors=[];
      let version=1, audience='invite_only', scope='summary_only', grants=[], savedLink=true, workspaceEnabled=false, linkEnabled=true, holdAccess=null, holdPeople=null;
      let releaseGeneral;const generalGate=new Promise(resolve=>{releaseGeneral=resolve;});
      const fingerprint=()=>version.toString(16).padStart(64,'0');
      const link=()=>!savedLink?{state:'absent',grant_id:null,version:0,content_scope:'summary_only'}:audience==='link'?{state:'active',grant_id:'synthetic-link',version,content_scope:scope,share_url:'https://graf.test/synthetic-reader',expires_at:'2026-12-01T00:00:00Z'}:{state:width===320?'expired':'replacement_required',grant_id:'old-link',version,content_scope:'summary_only'};
      const general=()=>({audience,content_scope:scope,fingerprint:fingerprint(),capabilities:{workspace:workspaceEnabled,link:linkEnabled},link:link()});
      page.on('pageerror',e=>errors.push(e.message));
      page.on('dialog',dialog=>dialog.accept());
      await page.route('**/*',async route=>{
        const request=route.request(), url=new URL(request.url());
        if(url.pathname==='/share')return route.fulfill({contentType:'text/html',body:'<meta charset="utf-8"><meta name="graf-time-user" content="owner"><meta name="graf-workspace" content="workspace"><link rel="stylesheet" href="/cabinet.css">'+'<div class="app-shell desktop-embedded"><main class="main detail-page-main"><div class="meeting-detail-header">'+fs.readFileSync(process.argv[2],'utf8')+'</div></main><section class="playback-bar" style="height:180px">Проигрыватель</section></div><dialog data-content-export-dialog><form data-content-export-form><label>Формат<select><option>TXT</option></select></label></form></dialog>'});
        if(url.pathname==='/cabinet.css')return route.fulfill({contentType:'text/css',body:fs.readFileSync(path.join(assets,'cabinet.css'),'utf8')});
        const base='/api/v1/cabinet/meetings/synthetic-meeting';
        if(request.method()!=='GET')mutations.push({path:url.pathname,method:request.method(),body:request.postDataJSON()});
        if(url.pathname===base+'/sharing/general-access'){
          if(request.method()==='GET')await generalGate;
          if(request.method()==='POST'){
            const body=request.postDataJSON();assert.equal(body.expected_fingerprint,fingerprint());audience=body.audience;scope=body.content_scope;version++;
          }
          return route.fulfill({json:general()});
        }
        if(url.pathname===base+'/access'){if(holdAccess)await holdAccess;return route.fulfill({json:{share:{active_grants:grants,active_invitations:[],can_manage_roles:true}}});}
        if(url.pathname.endsWith('/auto-send'))return route.fulfill({json:{state:'off',rules:{},roster:[]}});
        if(url.pathname.endsWith('/recipients')){if(holdPeople)await holdPeople;return route.fulfill({json:{recipients:[{user_id:'synthetic-person',email:'person@example.test',display_label:'Учебный получатель'}]}});}
        if(url.pathname===base+'/share-invitations'&&request.method()==='POST')return route.fulfill({status:202,json:{status:'pending'}});
        if(url.pathname===base+'/shares'&&request.method()==='POST'){
          const body=request.postDataJSON();grants=[{...body,grant_id:'synthetic-grant',version:1,display_name:'Учебный получатель'}];return route.fulfill({json:{grant:grants[0]}});
        }
        if(url.pathname.endsWith('/synthetic-grant/permissions')){assert.equal(request.postDataJSON().expected_version,grants[0].version);Object.assign(grants[0],request.postDataJSON());grants[0].version++;return route.fulfill({json:grants[0]});}
        if(url.pathname.endsWith('/synthetic-grant')&&request.method()==='DELETE'){assert.equal(Number(url.searchParams.get('expected_version')),grants[0].version);grants=[];return route.fulfill({status:204});}
        if(url.pathname.endsWith('/link/scope')){assert.equal(request.postDataJSON().expected_version,version);scope=request.postDataJSON().content_scope;version++;return route.fulfill({json:link()});}
        if(url.pathname.endsWith('/link'))return route.fulfill({json:link()});
        return route.abort();
      });
      await page.goto('https://graf.test/share');
      await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>{window.copied=text;}}}));
      await page.addScriptTag({path:path.join(assets,'summary-sharing.js')});
      assert.equal(await page.locator('[data-sharing-scope]').isDisabled(),true);
      assert.equal(await page.locator('[data-summary-share-copy]').isDisabled(),true);
      releaseGeneral();
      await page.locator('[data-sharing-audience] option[value=workspace]:disabled').waitFor({state:'attached'});
      await page.locator('[data-sharing-scope]:enabled').waitFor({state:'attached'});
      const panel = page.locator('[data-summary-share-dialog]');
      const panelBox = await panel.boundingBox(), cabinetBox = await page.locator('main').boundingBox();
      assert(panelBox.y + panelBox.height <= cabinetBox.y + cabinetBox.height, 'Sharing panel must fit above the player');
      if(width>=480)assert.equal(await panel.evaluate(el=>el.scrollHeight<=el.clientHeight+1),true,'Panel must not scroll at the default desktop size');
      assert.equal(await page.locator('[data-sharing-invite-role]').isVisible(),true);
      assert.equal(await page.locator('[data-sharing-invite-role]').inputValue(),'viewer');
      assert.equal(await page.locator('[data-sharing-audience-description]').isVisible(),true);
      assert.equal(await page.locator('[data-sharing-audience]').evaluate(el=>getComputedStyle(el).appearance),'none');
      assert(await page.locator('.sharing-audience-control').evaluate(el=>{const field=el.getBoundingClientRect();return field.height>=40&&Array.from(el.querySelectorAll('svg')).every(icon=>{const r=icon.getBoundingClientRect();return r.left>=field.left&&r.right<=field.right&&Math.abs(r.top+r.height/2-field.top-field.height/2)<1;});}),'Audience icons must be centered inside the field');
      assert.equal(await page.locator('[data-sharing-scope]').isVisible(),true);
      assert.equal(await page.locator('[data-summary-share-expiry]').isVisible(),false);
      await page.locator('[data-summary-share-copy]').click({trial:true});
      assert.equal(mutations.length,0,'Opening must not grant access');
      assert.equal(await page.locator('[data-summary-share-copy]').textContent(),'Скопировать ссылку','Closed audience must not promise renewal or rotation');
      await page.getByText('Дополнительные настройки',{exact:true}).click();
      await page.locator('[data-sharing-scope]').selectOption('full_meeting');
      assert.equal(mutations.length,0,'Selecting unpublished scope must not publish');
      await page.getByRole('button',{name:'Скопировать ссылку',exact:true}).click();
      await page.getByText('Ссылка скопирована',{exact:true}).waitFor();
      assert.equal(mutations.length,0,'Copying an invitation-only link must not publish');
      assert.equal(audience,'invite_only');
      assert.equal(await page.evaluate(()=>window.copied),'https://graf.test/shared-meetings/synthetic-meeting?workspace_id=workspace');
      page.removeAllListeners('dialog');page.on('dialog',dialog=>dialog.dismiss());
      await page.getByRole('combobox',{name:'Общий доступ',exact:true}).selectOption('link');
      await page.locator('[data-summary-share-dialog][aria-busy=false]').waitFor();
      assert.equal(audience,'invite_only');assert.equal(mutations.length,0,'Cancelled publication must not mutate');
      page.removeAllListeners('dialog');page.on('dialog',dialog=>dialog.accept());
      workspaceEnabled=true;
      await page.getByRole('combobox',{name:'Общий доступ',exact:true}).selectOption('link');
      await page.getByText('Общий доступ сохранён',{exact:true}).waitFor();
      assert.equal(audience,'link');assert.equal(scope,'full_meeting');
      await page.getByRole('button',{name:'Скопировать ссылку',exact:true}).click();
      await page.getByText('Ссылка скопирована',{exact:true}).waitFor();
      const savedVersion=version;
      await page.getByRole('button',{name:'Скопировать ссылку',exact:true}).click();
      await page.getByText('Ссылка скопирована',{exact:true}).waitFor();
      assert.equal(version,savedVersion,'Copy must preserve link version');
      await page.getByRole('combobox',{name:'Материалы общего доступа'}).selectOption('summary_only');
      await page.getByText('Состав материалов изменён',{exact:true}).waitFor();
      assert.equal(scope,'summary_only');
      const external = 'external@example.test';
      const filePermissions = page.locator('[data-sharing-invite-export]');
      await page.locator('[data-sharing-invite-role]').selectOption('viewer');
      assert.equal(await filePermissions.isChecked(),false);
      for (const allowFiles of [false, true]) {
        if(allowFiles)await filePermissions.check();
        await page.locator('[data-sharing-person]').fill(external);
        const [response] = await Promise.all([
          page.waitForResponse(response=>new URL(response.url()).pathname.endsWith('/share-invitations')&&response.request().method()==='POST'),
          page.getByRole('button',{name:'Пригласить',exact:true}).click(),
        ]);
        assert.equal(response.status(),202);
        assert.deepEqual(response.request().postDataJSON(),{
          address:external,content_scope:'full_meeting',can_comment:false,can_edit:false,can_download:allowFiles,can_export:allowFiles
        });
        await page.locator('[data-summary-share-dialog][aria-busy=false]').waitFor();
      }
      await filePermissions.uncheck();
      await page.locator('[data-sharing-person]').fill('person');
      await page.getByRole('option',{name:/Учебный получатель/}).click();
      await page.locator('[data-sharing-invite-role]').selectOption('commenter');
      await page.getByRole('button',{name:'Пригласить',exact:true}).click();
      await page.getByRole('combobox',{name:'Права Учебный получатель',exact:true}).waitFor();
      const invitation=mutations.find(x=>x.path.endsWith('/shares'));
      assert.equal(invitation.body.can_comment,true);assert.equal(invitation.body.can_edit,false);assert.equal(invitation.body.can_download,false);
      await page.getByRole('combobox',{name:'Права Учебный получатель',exact:true}).focus();
      await page.getByRole('combobox',{name:'Права Учебный получатель',exact:true}).selectOption('summary');
      await page.getByText('Права изменены',{exact:true}).waitFor();
      assert.equal(grants[0].content_scope,'summary_only');assert.equal(grants[0].can_comment,false);
      assert.equal(await page.locator('[data-summary-share-title]').evaluate(el=>el===document.activeElement),true,'Replacing a focused role must preserve dialog keyboard focus');
      await page.keyboard.press('Escape');assert.equal(await panel.isVisible(),false);
      await panel.evaluate(el=>el.show());
      let releaseAccess;holdAccess=new Promise(resolve=>{releaseAccess=resolve;});
      const accessRequested=page.waitForRequest(request=>new URL(request.url()).pathname==='/api/v1/cabinet/meetings/synthetic-meeting/access');
      await page.getByRole('combobox',{name:'Права Учебный получатель',exact:true}).focus();
      await page.getByRole('combobox',{name:'Права Учебный получатель',exact:true}).selectOption('viewer');
      await accessRequested;
      await page.locator('[data-sharing-person]').focus();releaseAccess();holdAccess=null;
      await page.getByText('Права изменены',{exact:true}).waitFor();
      assert.equal(await page.locator('[data-sharing-person]').evaluate(el=>el===document.activeElement),true,'A delayed access response must not steal focus moved outside the list');
      await page.getByRole('button',{name:'Отозвать',exact:true}).focus();
      await page.getByRole('button',{name:'Отозвать',exact:true}).press('Enter');
      await page.getByText('Доступ отозван',{exact:true}).waitFor();assert.equal(grants.length,0);
      assert.equal(await page.locator('[data-summary-share-title]').evaluate(el=>el===document.activeElement),true,'Revoking the focused row must preserve dialog keyboard focus');
      await page.keyboard.press('Escape');assert.equal(await panel.isVisible(),false);
      await panel.evaluate(el=>el.show());
      linkEnabled=false;
      await page.getByRole('combobox',{name:'Общий доступ',exact:true}).selectOption('workspace');
      await page.getByText('Общий доступ сохранён',{exact:true}).waitFor();
      const beforeWorkspaceCopy=mutations.length;
      await page.getByRole('button',{name:'Скопировать ссылку',exact:true}).click();
      await page.getByText('Ссылка скопирована',{exact:true}).waitFor();
      assert.equal(audience,'workspace');assert.equal(mutations.length,beforeWorkspaceCopy,'Copying workspace link must preserve access');
      assert.equal(await page.evaluate(()=>window.copied),'https://graf.test/shared-meetings/synthetic-meeting?workspace_id=workspace');
      await page.evaluate(()=>{navigator.clipboard.writeText=async()=>{throw new Error('Clipboard denied');};});
      await page.getByRole('button',{name:'Скопировать ссылку',exact:true}).click();
      await page.getByText('Выделите и скопируйте ссылку.',{exact:true}).waitFor();
      assert.equal(await page.locator('[data-summary-share-url]').isVisible(),true);
      assert.equal(await page.locator('[data-sharing-link-label]').textContent(),'Ссылка с проверкой доступа');
      assert.equal(await page.locator('[data-summary-share-url]').inputValue(),'https://graf.test/shared-meetings/synthetic-meeting?workspace_id=workspace');
      assert.equal(audience,'workspace');assert.equal(mutations.length,beforeWorkspaceCopy);
      await page.locator('[data-sharing-person]').fill('черновик');
      await page.getByRole('tab',{name:'Поделиться',exact:true}).press('ArrowRight');
      assert.equal(await page.getByRole('tab',{name:'Экспорт',exact:true}).evaluate(el=>el===document.activeElement),true);
      assert.equal(await page.locator('[data-sharing-export-host] [data-content-export-form]').isVisible(),true);
      await page.getByRole('tab',{name:'Экспорт',exact:true}).press('ArrowLeft');
      assert.equal(await page.getByRole('tab',{name:'Поделиться',exact:true}).evaluate(el=>el===document.activeElement),true);
      assert.equal(await page.locator('[data-sharing-person]').inputValue(),'черновик');
      assert.equal(mutations.length,beforeWorkspaceCopy,'Switching tabs must not change access');
      await page.getByRole('tab',{name:'Экспорт',exact:true}).click();
      assert.equal(await page.locator('[data-sharing-export-host] [data-content-export-form]').isVisible(),true);
      await page.getByRole('tab',{name:'Экспорт',exact:true}).press('Escape');
      assert.equal(await page.locator('[data-summary-share-dialog]').isVisible(),false);
      assert.equal(await page.locator('[data-content-export-dialog] [data-content-export-form]').count(),1);
      assert.equal(await page.evaluate(()=>document.activeElement?.hasAttribute('data-share-dialog-open')),true);
      assert.deepEqual(errors,[]);
      // A saved summary link keeps its scope; the new-action default only applies without one.
      audience='invite_only';scope='summary_only';grants=[];savedLink=false;mutations.length=0;linkEnabled=true;
      await page.reload();
      await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>{window.copied=text;}}}));
      await page.addScriptTag({path:path.join(assets,'summary-sharing.js')});
      await page.locator('[data-sharing-audience]:enabled').waitFor();
      assert.equal(await page.locator('[data-sharing-invite-role]').inputValue(),'viewer');
      assert.equal(await page.locator('[data-sharing-scope]').inputValue(),'full_meeting');
      assert.equal(await page.locator('[data-sharing-invite-export]').isChecked(),false);
      assert.equal(await page.locator('[data-summary-share-expiry]').inputValue(),'30');
      assert.equal(mutations.length,0);
      await page.getByText('Дополнительные настройки',{exact:true}).click();
      await filePermissions.check();
      await page.locator('[data-sharing-invite-role]').selectOption('summary');
      assert.equal(await filePermissions.isChecked(),false);
      assert.equal(await filePermissions.isDisabled(),true);
      assert((await page.locator('[data-sharing-invite-description]').innerText()).includes('без расшифровки и записи'));
      let releasePeople;holdPeople=new Promise(resolve=>{releasePeople=resolve;});
      const peopleRequested=page.waitForRequest(request=>new URL(request.url()).pathname.endsWith('/recipients'));
      await page.locator('[data-sharing-person]').fill(external);
      await peopleRequested;
      await page.locator('[data-sharing-invite-form]').getByRole('button',{name:'Пригласить',exact:true}).click();
      await page.getByText('Приглашение отправлено',{exact:true}).waitFor();
      const peopleResponded=page.waitForResponse(response=>new URL(response.url()).pathname.endsWith('/recipients'));
      releasePeople();holdPeople=null;await peopleResponded;
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      assert.equal(await page.locator('[data-sharing-people]').isVisible(),false,'Late search must not reopen suggestions after invitation');
      assert.deepEqual(mutations.at(-1).body,{address:external,content_scope:'summary_only',can_comment:false,can_edit:false,can_download:false,can_export:false});
      await page.locator('[data-sharing-invite-role]').selectOption('viewer');
      assert.equal(await filePermissions.isChecked(),false);
      assert.equal(await filePermissions.isDisabled(),false);
      await page.getByText('Дополнительные настройки',{exact:true}).click();
      mutations.length=0;
      await page.getByRole('button',{name:'Скопировать ссылку',exact:true}).click();
      await page.getByText('Ссылка скопирована',{exact:true}).waitFor();
      assert.equal(mutations.length,0);
      await page.locator('[data-sharing-person]').fill(external);
      await page.locator('[data-sharing-invite-form]').getByRole('button',{name:'Пригласить',exact:true}).click();
      await page.getByText('Приглашение отправлено',{exact:true}).waitFor();
      assert.deepEqual(mutations.at(-1).body,{address:external,content_scope:'full_meeting',can_comment:false,can_edit:false,can_download:false,can_export:false});
      await page.getByRole('combobox',{name:'Общий доступ',exact:true}).selectOption('link');
      await page.getByText('Общий доступ сохранён',{exact:true}).waitFor();
      assert.equal(mutations.at(-1).body.content_scope,'full_meeting');
      assert(await page.locator('[data-sharing-scope]').isVisible());
      if(width>=480)assert(await panel.evaluate(el=>el.scrollHeight<=el.clientHeight+1),'Full-meeting sharing must fit the default desktop size');
      assert((await page.locator('[data-sharing-audience-description]').innerText()).includes('Вход не нужен'));
      await page.addStyleTag({content:'.summary-share-dialog {font-size:200%;}'});
      await page.getByText('Дополнительные настройки',{exact:true}).click();
      assert(await page.locator('.summary-share-tabs button').evaluateAll(buttons=>buttons.every(el=>el.scrollWidth<=el.clientWidth+1)),'Advanced tabs must not overlap at 200% text');
      await page.getByRole('button',{name:'Скопировать ссылку',exact:true}).focus();
      await page.getByRole('button',{name:'Скопировать ссылку',exact:true}).scrollIntoViewIfNeeded();
      const copyBox=await page.locator('[data-summary-share-copy]').boundingBox();
      const mainBox=await page.locator('main').boundingBox();
      assert(copyBox.y>=0&&copyBox.y+copyBox.height<=mainBox.y+mainBox.height+1,'Footer must remain reachable at 200% text');
      assert(await page.locator('[data-summary-share-dialog]').evaluate(el=>el.scrollWidth<=el.clientWidth+1),'Text enlargement must not create horizontal overflow');
      assert(await page.locator('[data-sharing-audience]').evaluate(el=>{const field=el.getBoundingClientRect();const icon=el.parentElement.querySelector('svg').getBoundingClientRect();return Math.abs(field.top+field.height/2-icon.top-icon.height/2)<1;}));
      await page.keyboard.press('Escape');
      assert.equal(await page.evaluate(()=>document.activeElement?.hasAttribute('data-share-dialog-open')),true);
      assert.deepEqual(errors,[]);
      for(const target of ['workspace','link']){
        audience='invite_only';scope='summary_only';grants=[];savedLink=false;mutations.length=0;
        await page.reload();
        await page.addScriptTag({path:path.join(assets,'summary-sharing.js')});
        await page.locator('[data-sharing-scope]:enabled').waitFor();
        assert.equal(await page.locator('[data-sharing-scope]').isVisible(),true);
        assert.equal(await page.locator('[data-sharing-scope]').inputValue(),'full_meeting');
        await page.locator('[data-sharing-scope]').selectOption('summary_only');
        assert.equal(mutations.length,0,'Choosing materials before publication must only change the draft');
        page.removeAllListeners('dialog');page.on('dialog',dialog=>dialog.dismiss());
        await page.locator('[data-sharing-audience]').selectOption(target);
        await page.locator('[data-summary-share-dialog][aria-busy=false]').waitFor();
        assert.equal(audience,'invite_only');assert.equal(mutations.length,0);
        assert.equal(await page.locator('[data-sharing-scope]').inputValue(),'summary_only','Cancelled publication must retain the chosen materials');
        page.removeAllListeners('dialog');page.on('dialog',dialog=>dialog.accept());
        await page.locator('[data-sharing-audience]').selectOption(target);
        await page.getByText('Общий доступ сохранён',{exact:true}).waitFor();
        assert.equal(mutations.length,1,'Summary sharing must not require a temporary full-meeting grant');
        assert.equal(mutations[0].body.audience,target);
        assert.equal(mutations[0].body.content_scope,'summary_only');
        assert.equal(scope,'summary_only');
      }
      await page.close();
    }
    console.log('Owner sharing: explicit publication, stable copy, narrowed scope/roles, revoke, export restore, Escape/focus 320/1440 PASS');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
