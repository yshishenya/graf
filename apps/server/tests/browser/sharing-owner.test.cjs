const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium, webkit} = require(require.resolve('playwright', {paths:[process.env.GRAF_NODE_MODULES || process.cwd()]}));
const assets = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet');
(async () => {
  const browser = await (process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium).launch({headless:true});
  try {
    for (const width of [320, 1440]) {
      const page = await browser.newPage({viewport:{width,height:900}});
      page.setDefaultTimeout(5000);
      const mutations=[], errors=[];
      let version=1, audience='invite_only', scope='summary_only', grants=[];
      const fingerprint=()=>version.toString(16).padStart(64,'0');
      const link=()=>audience==='link'?{state:'active',grant_id:'synthetic-link',version,content_scope:scope,share_url:'https://graf.test/synthetic-reader',expires_at:'2026-12-01T00:00:00Z'}:{state:'absent'};
      const general=()=>({audience,content_scope:scope,fingerprint:fingerprint(),capabilities:{workspace:false,link:true},link:link()});
      page.on('pageerror',e=>errors.push(e.message));
      page.on('dialog',dialog=>dialog.accept());
      await page.route('**/*',async route=>{
        const request=route.request(), url=new URL(request.url());
        if(url.pathname==='/share')return route.fulfill({contentType:'text/html',body:'<meta charset="utf-8"><meta name="graf-time-user" content="owner"><meta name="graf-workspace" content="workspace"><link rel="stylesheet" href="/cabinet.css">'+'<div class="meeting-detail-header">'+fs.readFileSync(process.argv[2],'utf8')+'</div><section class="playback-bar" style="position:fixed;bottom:0;left:0;right:0;height:180px">Проигрыватель</section><dialog data-content-export-dialog><form data-content-export-form><label>Формат<select><option>TXT</option></select></label></form></dialog>'});
        if(url.pathname==='/cabinet.css')return route.fulfill({contentType:'text/css',body:fs.readFileSync(path.join(assets,'cabinet.css'),'utf8')});
        const base='/api/v1/cabinet/meetings/synthetic-meeting';
        if(request.method()!=='GET')mutations.push({path:url.pathname,method:request.method(),body:request.postDataJSON()});
        if(url.pathname===base+'/sharing/general-access'){
          if(request.method()==='POST'){
            const body=request.postDataJSON();assert.equal(body.expected_fingerprint,fingerprint());audience=body.audience;scope=body.content_scope;version++;
          }
          return route.fulfill({json:general()});
        }
        if(url.pathname===base+'/access')return route.fulfill({json:{share:{active_grants:grants,active_invitations:[],can_manage_roles:true}}});
        if(url.pathname.endsWith('/auto-send'))return route.fulfill({json:{state:'off',rules:{},roster:[]}});
        if(url.pathname.endsWith('/recipients'))return route.fulfill({json:{recipients:[{user_id:'synthetic-person',email:'person@example.test',display_label:'Учебный получатель'}]}});
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
      await page.locator('[data-sharing-audience] option[value=workspace]:disabled').waitFor({state:'attached'});
      assert.equal(mutations.length,0,'Opening must not grant access');
      await page.getByRole('combobox',{name:'Что доступно получателю'}).selectOption('full_meeting');
      assert.equal(mutations.length,0,'Selecting unpublished scope must not publish');
      await page.getByRole('button',{name:'Скопировать ссылку',exact:true}).click();
      await page.getByText('Ссылка скопирована',{exact:true}).waitFor();
      assert.equal(audience,'link');assert.equal(scope,'full_meeting');
      const savedVersion=version;
      await page.getByRole('button',{name:'Скопировать ссылку',exact:true}).click();
      await page.getByText('Ссылка скопирована',{exact:true}).waitFor();
      assert.equal(version,savedVersion,'Copy must preserve link version');
      await page.getByRole('combobox',{name:'Что доступно получателю'}).selectOption('summary_only');
      await page.getByText('Состав материалов изменён',{exact:true}).waitFor();
      assert.equal(scope,'summary_only');
      await page.locator('[data-sharing-person]').fill('person');
      await page.getByRole('option',{name:/Учебный получатель/}).click();
      await page.locator('[data-sharing-invite-role]').selectOption('commenter');
      await page.getByRole('button',{name:'Пригласить',exact:true}).click();
      await page.getByRole('combobox',{name:'Права Учебный получатель',exact:true}).waitFor();
      const invitation=mutations.find(x=>x.path.endsWith('/shares'));
      assert.equal(invitation.body.can_comment,true);assert.equal(invitation.body.can_edit,false);assert.equal(invitation.body.can_download,false);
      await page.getByRole('combobox',{name:'Права Учебный получатель',exact:true}).selectOption('summary');
      await page.getByText('Права изменены',{exact:true}).waitFor();
      assert.equal(grants[0].content_scope,'summary_only');assert.equal(grants[0].can_comment,false);
      await page.getByRole('button',{name:'Отозвать',exact:true}).click();
      await page.getByText('Доступ отозван',{exact:true}).waitFor();assert.equal(grants.length,0);
      await page.getByRole('tab',{name:'Экспорт',exact:true}).click();
      assert.equal(await page.locator('[data-sharing-export-host] [data-content-export-form]').isVisible(),true);
      await page.getByRole('tab',{name:'Экспорт',exact:true}).press('Escape');
      assert.equal(await page.locator('[data-summary-share-dialog]').isVisible(),false);
      assert.equal(await page.locator('[data-content-export-dialog] [data-content-export-form]').count(),1);
      assert.equal(await page.evaluate(()=>document.activeElement?.hasAttribute('data-share-dialog-open')),true);
      assert.deepEqual(errors,[]);
      await page.close();
    }
    console.log('Owner sharing: explicit publication, stable copy, narrowed scope/roles, revoke, export restore, Escape/focus 320/1440 PASS');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
