async page => {
  const check = (condition, message) => { if (!condition) throw new Error(message); };
  await page.route('**/api/v1/notifications?*', route => route.fulfill({json:{items:[],has_unseen_action_required:false,next_cursor:null}}));
  await page.addInitScript(targets => {
    const rules = targets.map(t => ({...t,rule:'ask'}));
    let prefs = {reminders:true,offsetMinutes:1,showTitles:false,sound:false};
    window.__settingsFailure = false;
    window.webkit = {messageHandlers:{
      grafRecordingSettings:{postMessage:async request => {
        if (window.__settingsFailure) return {version:1,targets:structuredClone(rules),error:'Не удалось сохранить настройки.'};
        rules.forEach(t => { if(request.action==='setAll'||(request.action==='set'&&request.targetID===t.id))t.rule=request.rule; });
        return {version:1,targets:structuredClone(rules)};
      }},
      grafNotificationSettings:{postMessage:async request => {
        if(request.action==='set'&&!window.__settingsFailure)prefs[request.field]=request.value;
        return {version:1,preferences:{...prefs},permission:'Уведомления macOS выключены',canRequestPermission:false,canEdit:true,message:'Сохранено на этом Mac',error:window.__settingsFailure?'Не удалось сохранить настройки.':null};
      }}
    }};
    window.addEventListener('DOMContentLoaded',()=>setTimeout(()=>{
      window.GRAFRecordingSettings?.connect('synthetic');window.GRAFNotificationSettings?.connect('synthetic');
    },0));
  }, [{"id": "three_cx", "name": "3CX"}, {"id": "eight_by_eight_work", "name": "8x8 Work"}, {"id": "adobe_connect", "name": "Adobe Connect"}, {"id": "aircall", "name": "Aircall"}, {"id": "alfaview", "name": "alfaview"}, {"id": "avaya_cloud_office", "name": "Avaya Cloud Office"}, {"id": "ayugram_desktop", "name": "AyuGram Desktop"}, {"id": "cisco_jabber", "name": "Cisco Jabber"}, {"id": "cloudtalk_phone", "name": "CloudTalk Phone"}, {"id": "cloudya", "name": "Cloudya"}, {"id": "dialpad", "name": "Dialpad"}, {"id": "dingtalk", "name": "DingTalk"}, {"id": "dion", "name": "Dion"}, {"id": "discord", "name": "Discord"}, {"id": "element_calls", "name": "Element / Matrix calls"}, {"id": "enreach_contact", "name": "Enreach Contact"}, {"id": "express", "name": "eXpress"}, {"id": "facetime", "name": "FaceTime"}, {"id": "gather", "name": "Gather"}, {"id": "gotomeeting", "name": "GoTo Meeting"}, {"id": "iva_connect", "name": "IVA Connect"}, {"id": "jami", "name": "Jami"}, {"id": "jitsi_desktop", "name": "Jitsi Desktop / Jitsi Meet"}, {"id": "kakaotalk_calls", "name": "KakaoTalk calls"}, {"id": "kontur_talk", "name": "Kontur Talk"}, {"id": "kotatogram_desktop", "name": "Kotatogram Desktop"}, {"id": "lark", "name": "Lark / Feishu"}, {"id": "lifesize", "name": "Lifesize"}, {"id": "line_calls", "name": "LINE calls"}, {"id": "linphone", "name": "Linphone"}, {"id": "loop_messenger", "name": "LOOP Messenger calls"}, {"id": "mattermost_calls", "name": "Mattermost calls"}, {"id": "microsoft_teams_classic", "name": "Microsoft Teams classic"}, {"id": "microsoft_teams_new", "name": "Microsoft Teams new"}, {"id": "mts_link", "name": "MTS Link"}, {"id": "mumble", "name": "Mumble"}, {"id": "onsip", "name": "OnSIP"}, {"id": "pachca", "name": "Pachca"}, {"id": "pexip", "name": "Pexip Infinity Connect"}, {"id": "quo_business_phone", "name": "Quo / OpenPhone"}, {"id": "ringcentral", "name": "RingCentral / Glip"}, {"id": "rocket_chat_calls", "name": "Rocket.Chat calls"}, {"id": "salutejazz", "name": "SaluteJazz"}, {"id": "signal_calls", "name": "Signal calls"}, {"id": "sipgate", "name": "sipgate"}, {"id": "skype", "name": "Skype"}, {"id": "slack_calls", "name": "Slack calls"}, {"id": "tandem", "name": "Tandem"}, {"id": "teamspeak", "name": "TeamSpeak 3"}, {"id": "teamviewer_meeting", "name": "TeamViewer Meeting"}, {"id": "teamviewer_quickjoin", "name": "TeamViewer QuickJoin"}, {"id": "telegram_a", "name": "Telegram A"}, {"id": "telegram_desktop", "name": "Telegram Desktop / TDX / Forkgram / 64Gram"}, {"id": "telegram_macos", "name": "Telegram for macOS / Telegram Lite"}, {"id": "telephone_sip", "name": "Telephone SIP calls"}, {"id": "tencent_meeting", "name": "Tencent Meeting"}, {"id": "trueconf", "name": "TrueConf"}, {"id": "tuple", "name": "Tuple"}, {"id": "viber_calls", "name": "Viber calls"}, {"id": "videomost", "name": "VideoMost"}, {"id": "vinteo", "name": "VINTEO"}, {"id": "vk_calls", "name": "VK Calls"}, {"id": "vk_messenger_calls", "name": "VK Messenger calls"}, {"id": "vk_teams", "name": "VK Teams"}, {"id": "vonage_business", "name": "Vonage Business Communications"}, {"id": "voov_meeting", "name": "VooV Meeting"}, {"id": "vsee", "name": "VSee Messenger"}, {"id": "webex", "name": "Webex"}, {"id": "webex_current", "name": "Webex current"}, {"id": "wechat_calls", "name": "WeChat calls"}, {"id": "wecom_calls", "name": "WeCom / WeChat Work calls"}, {"id": "whatsapp", "name": "WhatsApp"}, {"id": "wire_calls", "name": "Wire calls"}, {"id": "yandex_telemost", "name": "Yandex Telemost"}, {"id": "yealink_meeting", "name": "Yealink Meeting"}, {"id": "zoho_cliq", "name": "Zoho Cliq"}, {"id": "zoom", "name": "Zoom"}, {"id": "zoom_phone", "name": "Zoom Phone"}, {"id": "zulip_calls", "name": "Zulip calls"}]);
  const results=[];
  for (const theme of ['dark','light']) for (const width of [320,390,768,820,1024,1440]) {
    await page.setViewportSize({width,height:width===820?600:900});
    for (const section of ['account','recording','notifications']) {
      await page.goto(`http://127.0.0.1:8767/desktop/settings/${section}?theme=${theme}`);
      if(section==='recording')await page.locator('[data-recording-settings-controls]').waitFor({state:'visible'});
      if(section==='notifications')await page.waitForFunction(()=>!document.querySelector('[data-local-notification-controls]').disabled);
      const bounds=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,
        bad:[...document.querySelectorAll('.settings-page input,.settings-page select,.settings-page button,.settings-control-row__title')].filter(el=>el.getClientRects().length).filter(el=>{const r=el.getBoundingClientRect();return r.left<0||r.right>innerWidth+1;}).map(el=>el.textContent||el.getAttribute('aria-label'))}));
      check(bounds.scroll<=width+1 && !bounds.bad.length,JSON.stringify({theme,width,section,bounds}));
      const contrast = await page.locator('[data-cabinet-shell]').evaluate(shell => {
        const style = getComputedStyle(shell);
        const luminance = name => {
          const hex = style.getPropertyValue(name).trim().replace('#','');
          const rgb = hex.length === 3 ? [...hex].map(x => x+x).join('') : hex;
          return [0,2,4].map(i => parseInt(rgb.slice(i,i+2),16)/255)
            .map(v => v<=.04045 ? v/12.92 : ((v+.055)/1.055)**2.4)
            .reduce((sum,v,i) => sum+v*[.2126,.7152,.0722][i],0);
        };
        return [['--text','--surface'],['--muted','--surface-2'],['--accent-foreground','--accent-solid'],['--accent-foreground','--accent-hover']].map(([a,b]) => {
          const values=[luminance(a),luminance(b)].sort((x,y)=>x-y);
          return (values[1]+.05)/(values[0]+.05);
        });
      });
      check(contrast.every(value => value>=4.5),JSON.stringify({theme,width,section,contrast}));
      results.push({theme,width,section,overflow:false,contrast});
      if(width===820)await page.screenshot({animations:'disabled',path:`output/playwright/f260-${section}-${theme}.png`});
    }
  }
  await page.setViewportSize({width:820,height:600});
  await page.goto('http://127.0.0.1:8767/desktop/settings/recording');
  await page.locator('[data-recording-settings-controls]').waitFor({state:'visible'});
  check(await page.locator('[data-recording-target]').count()===79,'Full registry');
  await page.getByRole('searchbox').fill('Zoom');
  check(await page.locator('[data-recording-settings-targets] label:visible').count()===2,'Zoom search');
  await page.locator('[data-recording-target="zoom"]').selectOption('never');
  await page.waitForFunction(()=>document.querySelector('[data-recording-settings-all]').value==='');
  await page.locator('[data-recording-settings-all]').selectOption('always');
  await page.getByRole('searchbox').fill('');
  check(await page.locator('[data-recording-target]').evaluateAll(xs=>xs.every(x=>x.value==='always')),'Bulk includes hidden apps');
  await page.getByRole('searchbox').fill('Zoom');
  await page.evaluate(()=>window.__settingsFailure=true);
  await page.locator('[data-recording-target="zoom"]').selectOption('never');
  await page.waitForFunction(()=>document.querySelector('[data-recording-target="zoom"]').value==='always');
  await page.getByRole('searchbox').fill('No such app');
  check(await page.locator('[data-recording-settings-empty]').isVisible(),'Empty search');
  await page.goto('http://127.0.0.1:8767/desktop/settings/notifications');
  await page.waitForFunction(()=>!document.querySelector('[data-local-notification-controls]').disabled);
  await page.locator('[data-local-notification-field=reminders]').uncheck();
  await page.waitForFunction(()=>document.querySelector('[data-local-notification-field=offsetMinutes]').disabled);
  await page.locator('[data-local-notification-field=showTitles]').check();
  await page.evaluate(()=>window.__settingsFailure=true);
  await page.locator('[data-local-notification-field=sound]').click();
  await page.waitForFunction(()=>!document.querySelector('[data-local-notification-field=sound]').checked);
  await page.evaluate(()=>window.GRAFNotificationSettings.disconnect());
  check(await page.locator('[data-local-notification-field=reminders]').isDisabled(),'Disconnected controls');
  await page.goto('http://127.0.0.1:8767/desktop/settings/account');
  await page.locator('#account-display-name').focus();
  await page.keyboard.press('Tab');
  check(await page.locator(':focus').getAttribute('id')==='account-locale','Keyboard traversal');
  await page.emulateMedia({forcedColors:'active',reducedMotion:'reduce'});
  check(await page.locator(':focus').evaluate(el=>getComputedStyle(el).outlineStyle!=='none'),'Visible keyboard focus');
  await page.emulateMedia({forcedColors:'none'});
  await page.setViewportSize({width:1440,height:1000});
  await page.goto('http://127.0.0.1:8767/desktop/settings/recording');
  await page.evaluate(()=>document.documentElement.style.zoom='2');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'200% overflow');
  await page.screenshot({animations:'disabled',path:'output/playwright/f260-recording-200.png'});
  const noJS=await page.context().browser().newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
  const plain=await noJS.newPage();await plain.goto('http://127.0.0.1:8767/settings/notifications');
  check(await plain.locator('[data-notification-settings] button[type=submit]').isVisible(),'No-JS save');
  check(await plain.locator('[name=csrf_token]').count()>0,'No-JS CSRF');await noJS.close();
  return {matrix:results.length,registry:79,search:true,bulkHidden:true,confirmedError:true,authClear:true,keyboard:true,zoom200:true,noJS:true};
}
