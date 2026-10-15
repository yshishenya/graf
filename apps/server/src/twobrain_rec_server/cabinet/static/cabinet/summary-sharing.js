/* Sharing owns the saved document and delivery result; search/preview never send. */
(() => {
  function batchResult(batch) {
    const states = (batch.recipients || []).map(row => row.state);
    if (states.some(state => state === 'pending' || state === 'sending')) return {title:'Отправляем…',complete:false};
    if (states.length && states.every(state => state === 'accepted')) return {title:'Итоги отправлены',complete:true};
    if (states.some(state => state === 'failed' || state === 'suppressed')) return {title:'Отправлено не всем',complete:true};
    if (states.includes('unknown')) return {title:'Проверьте отправку',complete:true};
    if (states.length && states.every(state => state === 'cancelled')) return {title:'Отправка отменена',complete:true};
    return {title:'Проверьте отправку',complete:true};
  }
  window.GRAFSummarySharing = {batchResult};
  const meta = name => document.querySelector(`meta[name="${name}"]`)?.content || '';
  const actor = meta('graf-time-user'), currentWorkspace = meta('graf-workspace');
  const sameActor = () => meta('graf-time-user') === actor && meta('graf-workspace') === currentWorkspace;
  const messages = {
    share_links_disabled:'Ссылки пока недоступны. Отправьте итоги по почте.',
    share_invitations_disabled:'Отправка по почте пока недоступна.',
    summary_unavailable:'Итоги ещё не готовы. Откройте окно после их готовности.',
    summary_not_ready:'Итоги ещё не готовы. Откройте окно после их готовности.',
    auto_already_ready:'Для готовых итогов нажмите «Отправить». Автоотправку этой встречи можно включить до их готовности.',
    auto_recipient_invalid:'Выберите подтверждённых участников.',
    summary_batch_not_found:'Отправка пока не найдена. Повторите проверку.',
    summary_default_missing:'Выбранные итоги ещё не готовы.',
    summary_email_unavailable:'Отправка по почте пока недоступна.',
    summary_operation_conflict:'Эта отправка уже создана. Проверьте её результат.',
    summary_sharing_conflict:'Настройки изменились. Обновите состояние и повторите действие.',
    conflict:'Настройки изменились. Обновите состояние и повторите действие.',
    invalid_recipient:'Проверьте адрес электронной почты.',
    invalid_invitation:'Проверьте адрес электронной почты.',
    invalid_summary_recipients:'Укажите от 1 до 50 получателей.',
    invalid_share_expiry:'Выберите срок ссылки: 7, 30 или 90 дней.',
    summary_sharing_unavailable:'Не удалось открыть ссылку. Повторите позже.',
    summary_owner_rate_limited:'Слишком много отправок. Попробуйте позже.',
    meeting_not_found:'Доступ к встрече изменился. Обновите страницу.',
    forbidden:'Доступ изменился. Обновите страницу.',
    share_rate_limited:'Слишком много отправок. Попробуйте позже.',
    unavailable:'Не удалось получить ответ. Проверьте соединение и повторите проверку.'
  };
  const errorText = error => messages[error.code] || (error.status === 409 ? messages.conflict : messages.unavailable);
  async function request(path, {method='GET',body,workspace=''}={}) {
    if (!sameActor()) throw Object.assign(new Error(),{code:'forbidden'});
    const url = new URL(path, window.location.origin);
    if (workspace) url.searchParams.set('workspace_id',workspace);
    const controller = new AbortController(), timer = setTimeout(()=>controller.abort(),15000);
    try {
      const response = await fetch(url,{method,credentials:'same-origin',cache:'no-store',signal:controller.signal,
        headers:{Accept:'application/json','Content-Type':'application/json','X-CSRF-Token':meta('csrf-token')},
        ...(body === undefined ? {} : {body:JSON.stringify(body)})});
      if (!sameActor() || response.redirected) throw Object.assign(new Error(),{code:'forbidden'});
      const data = response.status === 204 ? {} : await response.json();
      if (!response.ok) throw Object.assign(new Error(),{code:data.code,status:response.status});
      return data;
    } finally { clearTimeout(timer); }
  }
  function node(tag,text,className) {
    const element = document.createElement(tag); if(text)element.textContent=text;if(className)element.className=className;return element;
  }
  const date = value => value ? new Intl.DateTimeFormat('ru',{day:'numeric',month:'long',year:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(value)) : '';
  const emailValid = value => /^[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+$/.test(value) && value.length <= 254;
  function initDialog(dialog) {
    if (dialog.dataset.summaryReady === 'true') return;
    dialog.dataset.summaryReady='true';
    const find = selector => dialog.querySelector(selector);
    const meetingId=dialog.dataset.meetingId, workspace=dialog.dataset.shareWorkspaceId || currentWorkspace;
    const base=`/api/v1/cabinet/meetings/${meetingId}/summary-sharing`;
    const api=(suffix,options={})=>request(base+suffix,{workspace,...options});
    const opener=document.querySelector(`[data-share-dialog-open][aria-controls="${dialog.id}"]`);
    const status=find('[data-share-status]'), title=find('[data-summary-share-title]'), input=find('[data-share-recipient-input]');
    const results=find('[data-share-recipient-results]'), recipients=find('[data-summary-share-recipients]');
    const copy=find('[data-summary-share-copy]'), send=find('[data-summary-share-send]');
    const editor=find('[data-summary-share-editor]'), outcome=find('[data-summary-share-result]');
    const formatControls=document.querySelector('[data-summary-format-controls]');
    const templateKey=()=>formatControls?.dataset.currentTemplateKey || formatControls?.dataset.currentSummaryFormatKey || 'meeting_minutes';
    find('[data-summary-share-format]').textContent=formatControls?.dataset.currentTemplateName || 'Выбранные итоги';
    let link=null, batch=null, auto=null, selected=[], busy=false, pollTimer=null, searchTimer=null, searchRevision=0, closed=false;
    const storageKey=`graf-summary-send:${actor}:${workspace}:${meetingId}`;
    let sendKey=null, frozenPayload=null, retryUnconfirmed=false;
    try { sendKey=sessionStorage.getItem(storageKey); } catch (_) { /* Memory still prevents repeat clicks. */ }
    const setStatus=(text,error=false)=>{status.textContent=text;status.dataset.tone=error?'error':'neutral';};
    const rememberKey=value=>{sendKey=value;if(!value)frozenPayload=null;try{value?sessionStorage.setItem(storageKey,value):sessionStorage.removeItem(storageKey);}catch(_){}};
    function close() {
      closed=true;clearTimeout(pollTimer);dialog.close();opener?.setAttribute('aria-expanded','false');opener?.focus({preventScroll:true});
    }
    function tab(mode,focus=false) {
      dialog.querySelectorAll('[data-summary-share-tab]').forEach(button=>{
        const active=button.dataset.summaryShareTab===mode;button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;
        if(active&&focus)button.focus();
      });
      dialog.querySelectorAll('[data-summary-share-panel]').forEach(panel=>{panel.hidden=panel.dataset.summarySharePanel!==mode;});
      setStatus('');
    }
    dialog.querySelectorAll('[data-summary-share-tab]').forEach(button=>{
      button.addEventListener('click',()=>tab(button.dataset.summaryShareTab));
      button.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();tab(event.key==='Home'?'link':event.key==='End'?'email':button.dataset.summaryShareTab==='link'?'email':'link',true);}});
    });
    find('[data-summary-share-close]').addEventListener('click',close);find('[data-summary-share-done]').addEventListener('click',close);
    dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
    dialog.addEventListener('click',event=>{if(event.target===dialog)close();});
    dialog.addEventListener('close',()=>{closed=true;clearTimeout(pollTimer);});
    function setBusy(value) {busy=value;copy.disabled=value;send.disabled=value;dialog.setAttribute('aria-busy',String(value));}
    async function action(fn) {
      if(busy)return;setBusy(true);setStatus('');
      try {await fn();}catch(error){if(error.status===409){await loadLink();await loadAuto();}setStatus(errorText(error),true);}
      finally {setBusy(false);}
    }
    function renderLink(data) {
      link=['active','expired','replacement_required'].includes(data.state)?data:null;
      find('[data-summary-link-controls]').hidden=!link;
      const field=find('[data-summary-share-url]');field.value=data.share_url||'';
      find('[data-summary-share-url-label]').hidden=!data.share_url;
      find('[data-summary-share-expiry-date]').textContent=data.expires_at?`До ${date(data.expires_at)}`:'';
      copy.textContent=data.state==='replacement_required'?'Заменить и скопировать ссылку':data.state==='expired'?'Продлить и скопировать ссылку':'Скопировать ссылку';
      if(data.state==='expired')setStatus('Срок ссылки истёк. Продлите его, чтобы снова открыть доступ.');
      if(data.state==='replacement_required')setStatus('Чтобы скопировать прежнюю ссылку, нужен её адрес. Здесь можно явно заменить её.');
    }
    async function loadLink(){try{renderLink(await api('/link'));}catch(error){setStatus(errorText(error),true);}}
    copy.addEventListener('click',()=>action(async()=>{
      if(link?.state==='replacement_required'&&!window.confirm('Заменить ссылку? Прежняя ссылка перестанет работать.'))return;
      if(link?.state==='expired'&&!window.confirm('Продлить срок ссылки? Итоги снова станут доступны по прежнему адресу.'))return;
      const options={template_key:templateKey(),expires_in_days:Number(find('[data-summary-share-expiry]').value)};
      const data=link&&link.state!=='active'?await api(link.state==='expired'?'/link/expiry':'/link/rotate',{method:'POST',body:{grant_id:link.grant_id,expected_version:link.version,...options}}):await api('/link',{method:'POST',body:options});
      renderLink(data);
      if(data.state!=='active'||!data.share_url){setStatus('Ссылка пока недоступна. Проверьте её настройки.',true);return;}
      const shareURL=new URL(data.share_url,window.location.origin);
      if(!['https:','http:'].includes(shareURL.protocol)){setStatus('Ссылка пока недоступна.',true);return;}
      try{await navigator.clipboard.writeText(shareURL.href);setStatus('Ссылка скопирована');}
      catch(_){find('[data-summary-share-url]').focus();find('[data-summary-share-url]').select();setStatus('Выделите и скопируйте ссылку.');}
    }));
    dialog.querySelectorAll('[data-summary-link-action]').forEach(button=>button.addEventListener('click',()=>action(async()=>{
      if(!link)return;const operation=button.dataset.summaryLinkAction;
      const confirmation={rotate:'Заменить ссылку? Прежняя ссылка перестанет работать.',revoke:'Отключить ссылку? Итоги по ней станут недоступны.',update:'Обновить итоги по ссылке? Получатели увидят выбранную редакцию.'};
      if(confirmation[operation]&&!window.confirm(confirmation[operation]))return;
      const data=await api(operation==='revoke'?'/link':`/link/${operation}`,{method:operation==='revoke'?'DELETE':'POST',body:{grant_id:link.grant_id,expected_version:link.version,template_key:templateKey(),expires_in_days:Number(find('[data-summary-share-expiry]').value)}});
      renderLink(data);setStatus(operation==='revoke'?'Ссылка отключена':operation==='update'?'Итоги обновлены':'Настройки ссылки сохранены');
    })));
    find('[data-summary-share-preview]').addEventListener('click',()=>action(async()=>{
      const preview=find('[data-summary-share-preview-content]');if(!preview.hidden){preview.hidden=true;return;}
      const data=(link?.summary&&find('[data-summary-share-panel="link"]').hidden===false)?link.summary:await api(`/preview?template_key=${encodeURIComponent(templateKey())}`);
      preview.replaceChildren();
      const summary=data.summary?.projection||data.summary||data.projection||data;preview.append(node('h3',summary.meeting_label||'Итоги'));
      for(const section of summary.summary_sections||[]){preview.append(node('h4',section.label||({summary:'Кратко',decisions:'Решения',action_items:'Задачи',key_points:'Ключевое',followups:'Следующие шаги'}[section.category])||'Итоги'));if(section.text)preview.append(node('p',section.text));for(const item of section.items||[])preview.append(node('p',item.text||''));}
      if(!summary.summary_sections?.length&&summary.protocol){const append=value=>{if(typeof value==='string')preview.append(node('p',value));else if(Array.isArray(value))value.forEach(append);else if(value&&typeof value==='object')Object.entries(value).filter(([key])=>!['schema_version','template_key'].includes(key)).forEach(([,value])=>append(value));};append(summary.protocol);}
      preview.hidden=false;preview.focus();
    }));
    function showSelected() {
      input.disabled=!!sendKey&&!!frozenPayload;find('[data-summary-share-add]').disabled=input.disabled;
      recipients.replaceChildren();for(const email of selected){const row=node('li');row.append(node('span',email));const remove=node('button','×','icon-button');remove.type='button';remove.setAttribute('aria-label',`Убрать ${email}`);remove.disabled=!!sendKey&&(!retryUnconfirmed||!!frozenPayload);remove.addEventListener('click',()=>{selected=selected.filter(value=>value!==email);showSelected();input.focus();});row.append(remove);recipients.append(row);}
    }
    function add(email) {
      if(sendKey&&(!retryUnconfirmed||frozenPayload)){setStatus('Сначала проверьте текущую отправку.',true);return;}
      const address=email.trim().toLowerCase();if(!emailValid(address)){setStatus('Введите email или выберите человека из списка.',true);input.focus();return;}
      if(!selected.includes(address)){if(selected.length>=50){setStatus('Можно выбрать до 50 получателей.',true);return;}selected.push(address);}
      input.value='';results.replaceChildren();results.hidden=true;input.setAttribute('aria-expanded','false');showSelected();input.focus();setStatus('');
    }
    find('[data-summary-share-add]').addEventListener('click',()=>add(input.value));
    input.addEventListener('keydown',event=>{
      const options=Array.from(results.querySelectorAll('[role="option"]'));
      if(event.key==='Enter'){event.preventDefault();add(input.value);}
      else if(event.key==='ArrowDown'&&options.length){event.preventDefault();options[0].focus();}
      else if(event.key==='Escape'){results.hidden=true;input.setAttribute('aria-expanded','false');}
    });
    input.addEventListener('input',()=>{
      clearTimeout(searchTimer);const revision=++searchRevision;searchTimer=setTimeout(async()=>{
        try{const data=await api(`/recipients?query=${encodeURIComponent(input.value)}`);if(revision!==searchRevision||!dialog.isConnected)return;
          results.replaceChildren();for(const row of data.recipients||[]){if(!row.email)continue;const option=node('button');option.type='button';option.setAttribute('role','option');option.append(node('strong',row.display_label||row.email));if(row.display_label!==row.email)option.append(node('small',row.email));option.addEventListener('click',()=>add(row.email));option.addEventListener('keydown',event=>{const all=Array.from(results.children),index=all.indexOf(option);if(['ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();all[(index+(event.key==='ArrowDown'?1:all.length-1))%all.length].focus();}if(event.key==='Escape'){results.hidden=true;input.focus();}});results.append(option);}
          results.hidden=!results.children.length;input.setAttribute('aria-expanded',String(!results.hidden));
        }catch(error){if(revision===searchRevision)setStatus(errorText(error),true);}
      },250);
    });
    function renderBatch(data) {
      batch=data;retryUnconfirmed=false;editor.hidden=true;outcome.hidden=false;const state=batchResult(data);const changed=title.textContent!==state.title;title.textContent=state.title;if(changed)title.focus({preventScroll:true});
      const list=find('[data-summary-share-result-recipients]');list.replaceChildren();
      const labels={accepted:'Отправлено',failed:'Не отправлено',unknown:'Не удалось подтвердить',pending:'Ожидает отправки',sending:'Отправляем…',cancelled:'Отменено',suppressed:'Автоматические письма отключены'};
      for(const recipient of data.recipients||[]){const row=node('li');row.append(node('span',recipient.email));if(state.title!=='Итоги отправлены')row.append(node('small',labels[recipient.state]||'Проверьте отправку'));if(recipient.can_retry){const retry=node('button','Повторить');retry.type='button';retry.addEventListener('click',()=>action(async()=>{renderBatch(await api(`/batches/${data.batch_id}/recipients/${recipient.recipient_id}/retry`,{method:'POST',body:{}}));schedulePoll();}));row.append(retry);}list.append(row);}
      find('[data-summary-share-result-copy]').textContent=(data.recipients||[]).some(row=>row.state==='unknown')?'Не отправляйте повторно, пока результат не подтверждён.':'';
      find('[data-summary-share-check]').hidden=state.title==='Итоги отправлены'||state.title==='Отправка отменена';
      find('[data-summary-share-cancel]').hidden=!data.can_cancel;
      if(state.complete){clearTimeout(pollTimer);if(!(data.recipients||[]).some(row=>row.state==='unknown'))rememberKey(null);}
    }
    function schedulePoll() {
      clearTimeout(pollTimer);if(closed||!batch||batchResult(batch).complete)return;
      pollTimer=setTimeout(async()=>{try{renderBatch(await api(`/batches/${batch.batch_id}`));schedulePoll();}catch(error){setStatus(errorText(error),true);}},1500);
    }
    async function checkBatch(){
      if(batch)renderBatch(await api(`/batches/${batch.batch_id}`));
      else if(sendKey){
        try{renderBatch(await api(`/batches?idempotency_key=${encodeURIComponent(sendKey)}`));}
        catch(error){if(error.code!=='summary_batch_not_found')throw error;
          retryUnconfirmed=true;send.textContent='Повторить отправку';showSelected();
          setStatus(frozenPayload?'Отправка пока не найдена. Можно повторить её с теми же получателями.':'Отправка пока не найдена. Укажите прежних получателей и повторите: уже созданная отправка не продублируется.');
        }
      }
      schedulePoll();
    }
    find('[data-summary-share-check]').addEventListener('click',()=>action(checkBatch));
    find('[data-summary-share-cancel]').addEventListener('click',()=>action(async()=>{if(!batch)return;renderBatch(await api(`/batches/${batch.batch_id}/cancel`,{method:'POST',body:{}}));schedulePoll();}));
    find('[data-summary-share-email-form]').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
      if(sendKey&&!retryUnconfirmed){await checkBatch();return;}if(!frozenPayload&&input.value.trim()){add(input.value);if(input.value.trim())return;}
      if(!selected.length&&!frozenPayload){setStatus('Выберите получателей.',true);input.focus();return;}
      if(!sendKey)rememberKey(crypto.randomUUID());
      frozenPayload=frozenPayload||{template_key:templateKey(),recipients:[...selected],idempotency_key:sendKey};
      retryUnconfirmed=false;showSelected();send.textContent='Отправляем…';
      try{renderBatch(await api('/batches',{method:'POST',body:frozenPayload}));schedulePoll();}
      catch(error){send.textContent='Проверить отправку';if(error.status&&error.status<500&&error.status!==409){rememberKey(null);frozenPayload=null;showSelected();send.textContent='Отправить';}throw error;}
    });});
    const autoStatusText={waiting_summary:'Отправим после готовности итогов.',scheduled:'Отправка запланирована',requires_review:'Состав участников нужно проверить. Отправьте итоги вручную.',paused:'Автоотправка приостановлена в настройках.',off:'Автоотправка выключена.',cancelled:'Отправка отменена.',sending:'Отправляем…',sent:'Итоги отправлены.',completed:'Отправка завершена.',partial:'Отправлено не всем.',unknown:'Проверьте отправку.',expired:'Срок автоотправки истёк. Отправьте итоги вручную.'};
    function renderAuto(data) {
      auto=data;const controls=find('[data-summary-autosend-controls]');controls.hidden=false;
      const scope=find('[data-summary-auto-scope]');scope.querySelector('[value="series"]').disabled=!(data.available_scopes||[]).includes('series');
      if(data.effective_scope)scope.value=data.effective_scope;
      const roster=find('[data-summary-auto-roster]');roster.replaceChildren();for(const person of data.roster||[]){const label=node('label');const checkbox=node('input');checkbox.type='checkbox';checkbox.value=person.user_id||'';checkbox.checked=!!person.selected;checkbox.disabled=!person.eligible;label.append(checkbox,node('span',person.email));roster.append(label);}
      const enabled=!!data.rules?.[scope.value]?.enabled;find('[data-summary-auto-enable]').hidden=enabled;find('[data-summary-auto-disable]').hidden=!enabled;
      find('[data-summary-auto-enable]').disabled=!data.eligible||!(data.roster||[]).some(person=>person.eligible)||data.paused;
      find('[data-summary-auto-cancel]').hidden=!data.batch?.can_cancel;
      find('[data-summary-auto-status]').textContent=(autoStatusText[data.state]||'Автоотправка пока недоступна.')+(data.batch?.scheduled_at?` · ${date(data.batch.scheduled_at)}`:'');
    }
    async function loadAuto(){try{renderAuto(await api('/auto-send'));}catch(error){find('[data-summary-autosend-controls]').hidden=true;}}
    find('[data-summary-auto-scope]').addEventListener('change',()=>{const enabled=!!auto?.rules?.[find('[data-summary-auto-scope]').value]?.enabled;find('[data-summary-auto-enable]').hidden=enabled;find('[data-summary-auto-disable]').hidden=!enabled;});
    async function saveAuto(enabled) {
      const scope=find('[data-summary-auto-scope]').value;const ids=Array.from(find('[data-summary-auto-roster]').querySelectorAll('input:checked')).map(box=>box.value);
      if(enabled&&!ids.length){setStatus('Выберите участников для автоотправки.',true);return;}
      renderAuto(await api('/auto-send',{method:'POST',body:{scope,enabled,template_key:templateKey(),recipient_user_ids:ids,expected_version:auto?.rules?.[scope]?.version||0}}));setStatus(enabled?'Автоотправка включена':'Автоотправка выключена');
    }
    find('[data-summary-auto-enable]').addEventListener('click',()=>action(()=>saveAuto(true)));
    find('[data-summary-auto-disable]').addEventListener('click',()=>action(()=>saveAuto(false)));
    find('[data-summary-auto-cancel]').addEventListener('click',()=>action(async()=>{await api(`/batches/${auto.batch.batch_id}/cancel`,{method:'POST',body:{}});await loadAuto();setStatus('Отправка отменена');}));
    async function open(mode='link') {
      closed=false;tab(mode);if(!dialog.open)dialog.showModal();title.focus({preventScroll:true});await loadLink();await loadAuto();
      if(sendKey)try{await checkBatch();}catch(error){setStatus(errorText(error),true);}
    }
    const requestedMode=opener?.dataset.summaryShareMode||'link';
    if(opener)delete opener.dataset.summaryShareMode;
    open(requestedMode);
  }
  async function initSettings(section) {
    if(section.dataset.summaryReady==='true')return;section.dataset.summaryReady='true';
    const ask=section.querySelector('[data-summary-pref-ask]'),pause=section.querySelector('[data-summary-pref-pause]'),status=section.querySelector('[data-summary-pref-status]');
    let confirmed=null,busy=false;
    function render(data){confirmed=data;ask.checked=data.ask_enabled;pause.checked=data.paused;ask.disabled=false;pause.disabled=false;
      const rules=section.querySelector('[data-summary-pref-rules]');rules.replaceChildren();for(const rule of (data.rules||[]).filter(rule=>rule.enabled)){const row=node('li');row.append(node('span',rule.label||(rule.scope==='series'?'Серия встреч':'Встреча')));const disable=node('button','Выключить');disable.type='button';disable.addEventListener('click',()=>updateRule(rule));row.append(disable);rules.append(row);}
      if(!rules.children.length)rules.append(node('li','Автоотправка ещё не включена ни для одной встречи.'));
      const queue=section.querySelector('[data-summary-pref-queue]');queue.replaceChildren();for(const item of data.queue||[]){const row=node('li');row.append(node('span',`Отправка ${date(item.scheduled_at)}`));if(item.can_cancel){const cancel=node('button','Отменить');cancel.type='button';cancel.addEventListener('click',async()=>{try{await request(`/api/v1/cabinet/meetings/${item.meeting_id}/summary-sharing/batches/${item.batch_id}/cancel`,{method:'POST',body:{}});render(await request('/api/v1/cabinet/summary-sharing/preferences'));status.textContent='Отправка отменена';}catch(error){status.textContent=errorText(error);}});row.append(cancel);}queue.append(row);}
    }
    async function updateRule(rule){try{await request(`/api/v1/cabinet/summary-sharing/preferences/rules/${rule.id}/disable`,{method:'POST',body:{expected_version:rule.version}});render(await request('/api/v1/cabinet/summary-sharing/preferences'));status.textContent='Автоотправка выключена';}catch(error){status.textContent=errorText(error);}}
    async function save(){if(busy||!confirmed)return;const focus=document.activeElement;busy=true;ask.disabled=true;pause.disabled=true;status.textContent='Сохраняем…';
      try{render(await request('/api/v1/cabinet/summary-sharing/preferences',{method:'PATCH',body:{ask_enabled:ask.checked,paused:pause.checked,expected_version:confirmed.version}}));status.textContent='Сохранено';}
      catch(error){status.textContent=errorText(error);try{render(await request('/api/v1/cabinet/summary-sharing/preferences'));}catch(_){}}
      finally{busy=false;ask.disabled=!confirmed;pause.disabled=!confirmed;if(focus===ask||focus===pause)focus.focus({preventScroll:true});}
    }
    ask.addEventListener('change',save);pause.addEventListener('change',save);
    try{render(await request('/api/v1/cabinet/summary-sharing/preferences'));}catch(error){status.textContent=errorText(error);}
  }
  async function initAsk(button) {
    if(button.dataset.summaryReady==='true')return;button.dataset.summaryReady='true';
    const main=button.closest('[data-meeting-id]');
    const opener=main?.querySelector('[data-share-dialog-open]');
    if(!opener||opener.disabled||!['ready','available'].includes(main.dataset.summaryRenderedState))return;
    try{const data=await request('/api/v1/cabinet/summary-sharing/preferences');if(data.ask_enabled)button.hidden=false;}catch(_){return;}
    button.addEventListener('click',()=>{opener.dataset.summaryShareMode='email';opener.click();});
  }
  function init(){document.querySelectorAll('[data-summary-share-ask]').forEach(initAsk);document.querySelectorAll('[data-summary-share-dialog]').forEach(initDialog);document.querySelectorAll('[data-summary-sharing-settings]').forEach(initSettings);}
  init();document.addEventListener('htmx:afterSwap',init);
})();
