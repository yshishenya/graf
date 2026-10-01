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
  function rowFor(event, panel, view) {
    const row=document.createElement('article');row.className='calendar-series__occurrence';row.dataset.eventId=event.event_id;
    const detail=document.createElement('div');detail.className='calendar-series__date';
    if(event.starts_at) {
      const zone=event.all_day?'UTC':window.GRAFTime?.timezone || 'UTC';
      const instant=new Date(event.starts_at),locale=document.documentElement.lang || 'ru';
      const day=text('time',new Intl.DateTimeFormat(locale,{timeZone:zone,day:'numeric',month:'short',weekday:'short',year:'numeric'}).format(instant));
      day.dateTime=event.starts_at;
      day.title=(event.all_day?window.GRAFTime?.format(event.starts_at.slice(0,10)):window.GRAFTime?.format(event.starts_at,{showZone:true})) || day.textContent;
      day.setAttribute('aria-label',day.title);
      detail.append(day,text('span',event.all_day?'Весь день':new Intl.DateTimeFormat(locale,{timeZone:zone,hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(instant)));
    } else detail.append(text('span','Время скрыто настройкой'));
    const seriesTitle=panel.closest('.calendar-home-upcoming__row')?.querySelector(':scope > div > strong')?.textContent;
    if(event.title && event.title!==seriesTitle) {
      const exception=text('span',event.title);exception.className='calendar-series__exception';exception.title=event.title;detail.append(exception);
    }
    row.append(detail);
    const actions=document.createElement('div');actions.className='calendar-series__actions';
    if(event.cancelled) {row.classList.add('is-cancelled');actions.append(text('span','Отменена'));}
    if(view==='upcoming') {
      if(event.starts_at && event.temporal_state==='ongoing' && !event.cancelled) {
        const live=text('span','Идёт сейчас');live.className='calendar-series__live';detail.append(live);
      }
      if(event.open_meeting_available && !event.cancelled) {
        const join=text('a','Подключиться');join.className='button quiet';join.dataset.calendarJoin=event.event_id;
        join.href=`/api/v1/calendar/events/${event.event_id}/open`;join.target='_blank';join.rel='noopener noreferrer';join.setAttribute('aria-label',`Подключиться · ${detail.firstElementChild.textContent}`);actions.append(join);
      } else if(!event.cancelled) actions.append(text('span','Без ссылки'));
    } else {
      const recordings=(event.recordings || []).filter(recording=>uuid.test(recording.meeting_id));
      recordings.forEach((recording,index)=>{
        const link=text('a',recordings.length===1?'Открыть запись':`Запись ${index+1}`);
        link.className='calendar-series__recording';
        link.setAttribute('aria-label',`Открыть ${recordings.length===1?'запись':`запись ${index+1}`} · ${detail.firstElementChild.textContent}`);
        link.href=`${location.pathname.startsWith('/desktop/')?'/desktop':''}/meetings/${recording.meeting_id}`;
        actions.append(link);
      });
      if(!recordings.length && !event.cancelled) {
        const missing=text('span',event.recordings_partial?'—':'Нет доступной записи');
        if(event.recordings_partial) {missing.title='В выборке нет связанной записи';missing.setAttribute('aria-label',missing.title);}
        actions.append(missing);
      }
    }
    row.append(actions);
    const feedback=text('span','');feedback.dataset.calendarJoinStatus='';feedback.setAttribute('role','status');feedback.setAttribute('aria-live','polite');actions.append(feedback);
    return row;
  }
  function reset(panel,view='upcoming') {
    state.get(panel)?.controller?.abort();
    const data={view,busy:false,cursor:null,started:false,count:0};state.set(panel,data);
    panel.querySelector('[data-calendar-series-rows]').replaceChildren();
    panel.querySelector('[data-calendar-series-rows]').inert=false;
    panel.querySelectorAll('[data-calendar-series-view]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.calendarSeriesView===view)));
    panel.querySelector('[data-calendar-series-scope]').textContent=view==='history'?'Последние 180 дней':'Ближайшие 30 дней';
    const more=panel.querySelector('[data-calendar-series-more]');more.hidden=true;more.disabled=false;
    panel.querySelector('[data-calendar-series-status]').textContent='';
    return data;
  }
  async function load(panel,{refresh=false}={}) {
    const data=state.get(panel) || reset(panel);
    if(data.busy) {
      if(refresh) {data.refreshRequested=true;panel.querySelector('[data-calendar-series-rows]').inert=true;}
      return;
    }
    if(!refresh && data.started && !data.cursor) return;
    const key=panel.dataset.calendarSeries;if(!/^v2-[0-9a-f]{64}$/.test(key)) return;
    const status=panel.querySelector('[data-calendar-series-status]'),more=panel.querySelector('[data-calendar-series-more]'),rows=panel.querySelector('[data-calendar-series-rows]');
    const focus=document.activeElement,hadFocus=panel.contains(focus),focusedHref=hadFocus?focus.getAttribute('href'):null;
    const hadRowFocus=rows.contains(focus);
    const wanted=refresh?Math.max(data.count,20):20;
    const controller=new AbortController();data.controller=controller;
    const timer=setTimeout(()=>controller.abort(),15000);
    data.busy=true;more.disabled=true;status.textContent=refresh?'Обновляем…':'Загружаем…';
    rows.setAttribute('aria-busy','true');
    // Old data is no longer actionable while its permissions are being rechecked.
    if(refresh) rows.inert=true;
    try {
      let cursor=refresh?null:data.cursor,result;
      const events=[];
      do {
        const query=new URLSearchParams({limit:String(Math.min(50,wanted-events.length)),view:data.view});
        if(cursor) query.set('cursor',cursor);
        if(!refresh && data.from) {query.set('from',data.from);query.set('to',data.to);}
        const response=await fetch(`/api/v1/calendar/series/${key}/occurrences?${query}`,{credentials:'same-origin',cache:'no-store',redirect:'error',signal:controller.signal,headers:{Accept:'application/json'}});
        if(!response.ok) {const error=new Error('unavailable');error.cursorExpired=response.status===422;error.accessDenied=response.status===401 || response.status===403 || response.status===404;throw error;}
        result=await response.json();
        if(!panel.isConnected || state.get(panel)!==data || controller.signal.aborted) return;
        events.push(...result.occurrences.filter(e=>uuid.test(e.event_id)));
        cursor=result.next_cursor;
        data.from=result.coverage_range.from;data.to=result.coverage_range.to;
      } while(refresh && cursor && events.length<wanted && result.occurrences.length);
      const fragment=document.createDocumentFragment();events.forEach(event=>fragment.append(rowFor(event,panel,data.view)));
      if(refresh) rows.replaceChildren(fragment);else rows.append(fragment);
      data.started=true;data.cursor=cursor;data.count=rows.children.length;
      more.hidden=!data.cursor;more.textContent=data.view==='history'?'Ранее':'Ещё даты';
      status.textContent=data.count?'':data.view==='history'?'За последние 180 дней нет доступных сохранённых встреч.':'В ближайшие 30 дней нет доступных сохранённых встреч.';
      rows.inert=false;
      if(refresh && hadFocus) {
        const replacement=[...rows.querySelectorAll('a[href]')].find(link=>link.getAttribute('href')===focusedHref);
        (replacement || (focus.isConnected && !rows.contains(focus) && !focus.hidden ? focus : panel.querySelector(':scope > summary'))).focus({preventScroll:true});
      } else if(focus===more && more.hidden) panel.querySelector('[data-calendar-series-view][aria-pressed="true"]').focus({preventScroll:true});
    } catch(error) {
      if(!panel.isConnected || state.get(panel)!==data) return;
      // A failed refresh or access revocation must not retain previously visible data.
      if(refresh || error.cursorExpired || error.accessDenied) {rows.replaceChildren();data.started=false;data.cursor=null;data.count=0;delete data.from;delete data.to;}
      status.textContent=error.cursorExpired?'Список устарел. Загрузите его заново.':error.accessDenied?'Доступ к серии изменился. Обновите календарь или повторите попытку.':'Не удалось загрузить встречи. Повторите попытку.';
      more.hidden=false;more.textContent=error.cursorExpired?'Загрузить заново':'Повторить';
      if(hadRowFocus && !focus.isConnected) panel.querySelector(':scope > summary').focus({preventScroll:true});
    } finally {
      clearTimeout(timer);data.busy=false;
      if(state.get(panel)===data) {rows.inert=false;rows.removeAttribute('aria-busy');more.disabled=false;if(data.refreshRequested){data.refreshRequested=false;load(panel,{refresh:true});}}
    }
  }
  document.addEventListener('toggle',event=>{
    const panel=event.target;if(!panel.matches?.('[data-calendar-series]')) return;
    if(panel.open) load(panel);else reset(panel);
  },true);
  document.addEventListener('graf:calendar-series-refresh',event=>{if(event.target.matches?.('[data-calendar-series][open]')) load(event.target,{refresh:true});});
  document.addEventListener('click',event=>{
    const button=event.target.closest?.('[data-calendar-series-view],[data-calendar-series-more]');if(!button) return;
    const panel=button.closest('[data-calendar-series]');
    if(button.hasAttribute('data-calendar-series-view')) {
      if(state.get(panel)?.view===button.dataset.calendarSeriesView) return;
      reset(panel,button.dataset.calendarSeriesView);
    }
    load(panel);
  });
})();
