(() => {
  const state = new WeakMap();
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const text = (tag, value) => { const node=document.createElement(tag); node.textContent=value; return node; };
  let pendingJoin=null;
  // These random generation markers confer no authority and contain no identity.
  const sessionEpoch=()=>document.cookie.split(';').map(value=>value.trim()).filter(value=>value.startsWith('__Host-graf_session_epoch=') || value.startsWith('graf_dev_session_epoch=')).sort().join(';');
  function joinFeedback(eventId,message,busy=false) {
    document.querySelectorAll(`[data-calendar-join="${eventId}"]`).forEach(button=>{
      let status=button.parentElement.querySelector('[data-calendar-join-status]');
      if(!status) {status=text('span','');status.dataset.calendarJoinStatus='';status.setAttribute('role','status');button.after(status);}
      if(status.textContent!==message) status.textContent=message;
      if(busy) button.setAttribute('aria-disabled','true');else button.removeAttribute('aria-disabled');
    });
  }
  function cancelJoin() {
    const operation=pendingJoin;if(!operation) return;
    pendingJoin=null;operation.controller.abort();operation.popup?.close();
    joinFeedback(operation.eventId,'Действие отменено. Повторите попытку.');
  }
  window.addEventListener('pagehide',cancelJoin);
  new MutationObserver(()=>{if(pendingJoin) joinFeedback(pendingJoin.eventId,'Открываем…',true);}).observe(document.documentElement,{childList:true,subtree:true});
  document.addEventListener('click',async event=>{
    const button=event.target.closest?.('[data-calendar-join]');
    // The isolated native capture listener owns desktop joins, including pending clicks.
    if(!button || event.defaultPrevented || !event.isTrusted) return;
    event.preventDefault();
    const eventId=button.dataset.calendarJoin;if(!uuid.test(eventId) || pendingJoin) return;
    if(navigator.userAgent.includes('GRAFDesktop/')) {
      joinFeedback(eventId,'Календарь загружается. Повторите попытку.');return;
    }
    // Reserve the tab during trusted input; async window.open can be blocked.
    const popup=window.open('about:blank','_blank');
    if(!popup) {joinFeedback(eventId,'Разрешите открытие новой вкладки и повторите попытку.');return;}
    const epoch=sessionEpoch();
    const csrf=document.querySelector('meta[name="csrf-token"]')?.content || '';
    const currentAction=()=>[...document.querySelectorAll(`[data-calendar-join="${eventId}"]`)].some(node=>!node.closest('[inert],[hidden]'));
    const operation={eventId,popup,controller:new AbortController()};pendingJoin=operation;
    joinFeedback(eventId,'Открываем…',true);
    const timer=setTimeout(()=>operation.controller.abort(),15000);
    try {
      popup.opener=null;
      const referrer=popup.document.createElement('meta');referrer.name='referrer';referrer.content='no-referrer';popup.document.head.append(referrer);
      const response=await fetch(`/api/v1/calendar/events/${eventId}/join-target`,{credentials:'same-origin',cache:'no-store',redirect:'error',signal:operation.controller.signal,headers:{Accept:'application/json'}});
      if(!response.ok) throw new Error('unavailable');
      await response.json();
      if(pendingJoin!==operation || operation.controller.signal.aborted || sessionEpoch()!==epoch || !csrf || !currentAction() || popup.closed) throw new Error('cancelled');
      // A fresh request binds the handoff to the original page session, including
      // account changes in another tab while the initial resolver was in flight.
      const confirmed=await fetch(`/api/v1/calendar/events/${eventId}/join-target`,{method:'POST',credentials:'same-origin',cache:'no-store',redirect:'error',signal:operation.controller.signal,headers:{Accept:'application/json','X-CSRF-Token':csrf}});
      if(!confirmed.ok) throw new Error('session changed');
      const result=await confirmed.json(),target=new URL(result.https_url);
      if(result.event_id?.toLowerCase()!==eventId.toLowerCase() || target.protocol!=='https:' || target.username || target.password || !target.hostname) throw new Error('invalid target');
      if(pendingJoin!==operation || operation.controller.signal.aborted || sessionEpoch()!==epoch || !currentAction() || popup.closed) throw new Error('cancelled');
      const destination=popup.document.createElement('a');destination.href=target.href;destination.rel='noreferrer';destination.referrerPolicy='no-referrer';popup.document.body.append(destination);destination.click();
      pendingJoin=null;
      joinFeedback(eventId,'Ссылка открыта в новой вкладке');
    } catch {
      popup.close();
      if(pendingJoin===operation) joinFeedback(eventId,'Не удалось открыть встречу. Повторите подключение или обновите календарь.');
    } finally {
      clearTimeout(timer);if(pendingJoin===operation) pendingJoin=null;
    }
  });
  function rowFor(event) {
    const row=document.createElement('article');row.className='calendar-series__occurrence';row.dataset.eventId=event.event_id;
    row.append(text('strong',event.title));
    if(event.cancelled) row.append(text('span','Отменена'));
    if(event.starts_at) {
      const label=event.all_day ? event.starts_at.slice(0,10)+' · весь день' : (window.GRAFTime?.format(event.starts_at,{showZone:true}) || new Intl.DateTimeFormat(document.documentElement.lang || 'ru',{dateStyle:'medium',timeStyle:'short'}).format(new Date(event.starts_at)));
      row.append(text('span',label));
    } else row.append(text('span','Время скрыто настройкой'));
    if(event.open_meeting_available) {
      const join=text('a','Подключиться');join.className='button quiet';join.dataset.calendarJoin=event.event_id;
      join.href=`/api/v1/calendar/events/${event.event_id}/open`;join.target='_blank';join.rel='noopener noreferrer';row.append(join);
    }
    const feedback=text('span','');feedback.dataset.calendarJoinStatus='';feedback.setAttribute('role','status');row.append(feedback);
    if(!event.recordings_partial && !(event.recordings || []).length) row.append(text('span','Нет доступной записи'));
    for(const recording of event.recordings || []) {
      if(!uuid.test(recording.meeting_id)) continue;
      const link=text('a','Открыть запись');link.href=`${location.pathname.startsWith('/desktop/')?'/desktop':''}/meetings/${recording.meeting_id}`;row.append(link);
    }
    if(event.recordings_partial) {
      row.append(text('span','Здесь показана ограниченная выборка записей.'));
      const all=text('a','Все доступные записи');all.href=`${location.pathname.startsWith('/desktop/')?'/desktop':''}/meetings`;row.append(all);
    }
    return row;
  }
  async function load(panel,{refresh=false}={}) {
    let data=state.get(panel);
    if(!data) {data={busy:false,cursor:null,started:false,count:0};state.set(panel,data);}
    if(data.busy) {if(refresh) data.refreshRequested=true;return;}
    if(!refresh && data.started && !data.cursor) return;
    const key=panel.dataset.calendarSeries;if(!/^v2-[0-9a-f]{64}$/.test(key)) return;
    const status=panel.querySelector('[data-calendar-series-status]'),more=panel.querySelector('[data-calendar-series-more]'),rows=panel.querySelector('[data-calendar-series-rows]');
    const focus=document.activeElement,hadFocus=panel.contains(focus),focusedHref=hadFocus?focus.getAttribute('href'):null;
    const wanted=refresh?Math.max(data.count,20):20;
    data.busy=true;more.disabled=true;status.textContent=refresh?'Обновляем даты…':'Загружаем даты…';
    // Old data is no longer actionable while its permissions are being rechecked.
    if(refresh) rows.inert=true;
    try {
      let cursor=refresh?null:data.cursor,result;
      const events=[];
      do {
        const query=new URLSearchParams({limit:String(Math.min(50,wanted-events.length))});
        if(cursor) query.set('cursor',cursor);
        if(data.from) {query.set('from',data.from);query.set('to',data.to);}
        const response=await fetch(`/api/v1/calendar/series/${key}/occurrences?${query}`,{credentials:'same-origin',cache:'no-store',redirect:'error',headers:{Accept:'application/json'}});
        if(!response.ok) {const error=new Error('unavailable');error.cursorExpired=response.status===422;throw error;}
        result=await response.json();
        if(!panel.isConnected || state.get(panel)!==data) return;
        events.push(...result.occurrences.filter(e=>uuid.test(e.event_id)));
        cursor=result.next_cursor;
        data.from=result.coverage_range.from;data.to=result.coverage_range.to;
      } while(refresh && cursor && events.length<wanted && result.occurrences.length);
      const fragment=document.createDocumentFragment();events.forEach(event=>fragment.append(rowFor(event)));
      if(refresh) rows.replaceChildren(fragment);else rows.append(fragment);
      data.started=true;data.cursor=cursor;data.count=rows.children.length;
      more.hidden=!data.cursor;more.textContent='Ещё даты';
      status.textContent=events.length?result.coverage_note:'В этом периоде нет доступных сохранённых дат.';
      rows.inert=false;
      if(refresh && hadFocus) {
        const replacement=[...rows.querySelectorAll('a[href]')].find(link=>link.getAttribute('href')===focusedHref);
        (replacement || (focus===more&&!more.hidden?more:panel.querySelector('summary'))).focus({preventScroll:true});
      }
    } catch(error) {
      if(!panel.isConnected || state.get(panel)!==data) return;
      // A failed refresh must not leave revoked data visible indefinitely.
      if(refresh || error.cursorExpired) {rows.replaceChildren();data.started=false;data.cursor=null;data.count=0;more.hidden=false;}
      status.textContent=error.cursorExpired?'Список дат устарел. Загрузите его заново.':'Не удалось загрузить даты. Повторите попытку.';more.textContent=error.cursorExpired?'Загрузить заново':'Повторить';
      if(refresh&&hadFocus) panel.querySelector('summary').focus({preventScroll:true});
    } finally {
      data.busy=false;
      if(state.get(panel)===data) {rows.inert=false;more.disabled=false;if(data.refreshRequested){data.refreshRequested=false;load(panel,{refresh:true});}}
    }
  }
  document.addEventListener('toggle',event=>{
    const panel=event.target;if(!panel.matches?.('[data-calendar-series]')) return;
    if(panel.open) load(panel);
    else {state.delete(panel);const rows=panel.querySelector('[data-calendar-series-rows]');rows.replaceChildren();rows.inert=false;const more=panel.querySelector('[data-calendar-series-more]');more.hidden=false;more.disabled=false;more.textContent='Загрузить даты';panel.querySelector('[data-calendar-series-status]').textContent='';}
  },true);
  document.addEventListener('graf:calendar-series-refresh',event=>{if(event.target.matches?.('[data-calendar-series][open]')) load(event.target,{refresh:true});});
  document.addEventListener('click',event=>{const button=event.target.closest?.('[data-calendar-series-more]');if(button) load(button.closest('[data-calendar-series]'));});
})();
