/* One queue per preference resource, shared by the page and profile menu. */
(() => {
  const queues = new Map();
  const meta = (name, doc = document) => doc.querySelector(`meta[name="${name}"]`)?.content || '';
  const actor = meta('graf-time-user'), workspace = meta('graf-workspace');
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const headers = () => ({'X-CSRF-Token': meta('csrf-token'), 'X-Graf-Expected-Actor': actor,
    'X-Graf-Expected-Workspace': workspace, 'X-Graf-Settings-Autosave': 'true', Accept: 'application/json'});
  const scopeOK = () => actor && workspace && meta('graf-time-user') === actor && meta('graf-workspace') === workspace;
  const read = (form) => {
    const values = {};
    for (const input of form.elements) {
      if (!input.name || input.disabled || ['_csrf', 'csrf_token', 'return_to', 'version'].includes(input.name) || ['submit','button','search'].includes(input.type)) continue;
      if (input.name === 'selected_provider_calendar_ids') {
        values[input.name] ||= [];
        if (input.checked) values[input.name].push(input.value);
      } else if (input.type === 'checkbox') values[input.name] = input.checked;
      else if (input.type !== 'radio' || input.checked) values[input.name] = input.value;
    }
    if (form.hasAttribute('data-calendar-selection-limit')) values.selected_provider_calendar_ids ||= [];
    if (values.selected_provider_calendar_ids) values.selected_provider_calendar_ids.sort();
    return values;
  };
  const write = (form, values) => {
    for (const input of form.elements) {
      if (!(input.name in values)) continue;
      const value = values[input.name];
      if (input.type === 'checkbox') input.checked = Array.isArray(value) ? value.includes(input.value) : value;
      else if (input.type === 'radio') input.checked = input.value === value;
      else if (input.type !== 'hidden') input.value = value;
      if(input.matches('[data-settings-combobox]'))input.dispatchEvent(new Event('settings:sync'));
    }
  };
  const request = async (url, options = {}) => {
    if (!scopeOK()) throw new Error('scope');
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), 15000);
    try {
      const response = await fetch(url, {credentials:'same-origin', cache:'no-store', ...options, signal:abort.signal});
      if (!scopeOK() || !response.ok || response.redirected) throw new Error(response.status === 409 ? 'conflict' : 'unavailable');
      const body = response.status === 204 ? null : await response.blob();
      return new Response(body, {status:response.status,headers:response.headers});
    } finally { clearTimeout(timer); }
  };
  function create(key, adapter) {
    if (queues.has(key)) return queues.get(key);
    let confirmed = {...adapter.initial}, draft = {...confirmed}, active = null, timer, statusTimer, failure = '', revision = adapter.version;
    let disposed = false, recovery = null;
    const uncertain = new Set();
    const dirty = () => !same(draft, confirmed);
    const publish = (state, message = '') => {
      if(disposed)return;
      clearTimeout(statusTimer);adapter.render?.(state, message, {...draft});
      if(state==='saved')statusTimer=setTimeout(()=>{if(!dirty()&&!active&&!failure)adapter.render?.('pristine','',{...draft});},2000);
    };
    const changed = () => Object.fromEntries(Object.entries(draft).filter(([k,v]) => !same(v, confirmed[k])));
    const run = async () => {
      if(disposed)return false;
      clearTimeout(timer);
      if (active) { await active; return failure ? false : run(); }
      if (failure) return false;
      if (!dirty()) return true;
      if (!scopeOK()) {failure='scope';publish('error','Аккаунт изменился. Откройте настройки заново.');return false;}
      if (adapter.valid && !adapter.valid()) {publish('invalid','Проверьте выделенное поле.');return false;}
      const sent = {...draft}, fields = changed();
      publish('saving','Сохраняем…');
      active = (async () => {
        try {
          const result = await adapter.save(fields, sent, confirmed, revision);
          if (!scopeOK() || !result || result.saved !== true || result.actor !== actor || result.workspace !== workspace || !result.values || Object.keys(fields).some(k => !(k in result.values))) throw new Error('unavailable');
          for (const [key,value] of Object.entries(result.values)) {
            if (same(draft[key],sent[key])) draft[key] = value;
            confirmed[key] = value;
          }
          revision = result.version ?? revision;
          publish(dirty() ? 'dirty' : 'saved', dirty() ? '' : 'Сохранено');
        } catch (error) {Object.keys(fields).forEach(k=>uncertain.add(k));failure=error.message;publish('error', failure === 'conflict' ? 'Настройка изменена на другом устройстве.' : 'Не удалось сохранить. Ваш выбор остался здесь.');}
        finally {active=null;}
      })();
      await active;
      return failure ? false : run();
    };
    const queue = {
      edit(values, delay=0) { if(disposed)return;if(!dirty()&&Object.entries(values).every(([k,v])=>same(draft[k],v)))return;Object.assign(draft,values); publish(failure?'error':'dirty',failure?'Не удалось сохранить. Ваш выбор остался здесь.':'');clearTimeout(timer);if(!failure)timer=setTimeout(run,delay); },
      attach(values) { for(const [k,v] of Object.entries(values)) if(!(k in confirmed)){confirmed[k]=v;draft[k]=v;} return {...draft}; },
      refresh(values) { if(!dirty()&&!active){confirmed={...values};draft={...values};} },
      pending: () => dirty() || !!active || !!recovery || !!failure,
      async flush() { if(recovery)await recovery;return run(); },
      async retry(force = false) {
        if (disposed) return;
        if (recovery) return recovery;
        recovery = (async () => {
          if (active) await active;
          try {
            const current = await adapter.load();
            if (disposed) return;
            if (!scopeOK()) throw new Error('scope');
            const wanted = {...changed(), ...Object.fromEntries(Array.from(uncertain, key => [key, draft[key]]))};
            for (const key of Object.keys(wanted)) {
              if (adapter.equivalent?.(key, current.values[key], wanted[key])) wanted[key] = current.values[key];
            }
            const conflict = Object.keys(wanted).some(key => !same(current.values[key], confirmed[key]) && !same(current.values[key], wanted[key]));
            if (conflict && !force) {
              failure = 'conflict';
              publish('conflict', 'Настройка изменена на другом устройстве.');
              return;
            }
            confirmed = {...current.values};
            draft = {...confirmed, ...wanted};
            revision = current.version ?? revision;
            failure = '';
            uncertain.clear();
            if (!dirty()) publish('saved', 'Сохранено');
            await run();
          } catch (_) {
            failure = 'unavailable';
            publish('error', 'Не удалось проверить сохранение. Повторите позже.');
          }
        })();
        try { await recovery; } finally { recovery = null; }
      },
      dispose() { disposed=true;clearTimeout(timer);clearTimeout(statusTimer);queues.delete(key); },
      async discard() { if(recovery)await recovery;if(active)await active;draft={...confirmed};failure='';uncertain.clear();clearTimeout(timer);publish('pristine'); },
    };
    queues.set(key,queue);return queue;
  }
  function init() {
    document.querySelectorAll('form[data-settings-autosave]').forEach((form, index) => {
      if(form.dataset.autosaveReady)return;
      if(!scopeOK())return;
      form.dataset.autosaveReady='true';form.dataset.state='pristine';
      const status=form.querySelector('[data-settings-form-status]');
      if(status){status.id ||= `settings-status-${index}`;for(const input of form.elements){
        if(input.name && !['hidden','submit','button'].includes(input.type)) input.setAttribute('aria-describedby',[input.getAttribute('aria-describedby'),status.id].filter(Boolean).join(' '));
      }}
      form.querySelectorAll('[data-settings-inputs]').forEach(fieldset=>fieldset.disabled=false);
      const url=new URL(form.action,location.href).href;
      const forms=()=>Array.from(document.querySelectorAll('form[data-settings-autosave]')).filter(f=>f.action===url);
      const queue=create(url, {
        initial:read(form), version:form.elements.namedItem('version')?.value,
        equivalent: (key, actual, wanted) => key === 'display_name' && typeof actual === 'string' && typeof wanted === 'string' &&
          actual === wanted.replace(/\s+/gu, ' ').trim(),
        valid:()=>forms().every(f=>f.checkValidity()),
        render(state,message,values) {
          for(const f of forms()) {
            f.dataset.state=state;write(f,values);
            const status=f.querySelector('[data-settings-form-status]');if(!status)continue;
            status.hidden=!message;status.setAttribute('role',state==='error'||state==='conflict'?'alert':'status');status.replaceChildren(document.createTextNode(message));
            if(['error','conflict'].includes(state)) {
              const button=document.createElement('button');button.type='button';button.className='button quiet';button.textContent=state==='conflict'?'Применить мой выбор':'Повторить';button.onclick=()=>queue.retry(state==='conflict');status.append(' ',button);
            }
          }
          if(values.theme){if(values.theme==='system')document.documentElement.removeAttribute('data-theme');else document.documentElement.dataset.theme=values.theme;}
          if(state==='saved'&&values.timezone)window.GRAFTime?.setTimezone?.(values.timezone);
        },
        async save(fields, all, previous, version) {
          const body=new URLSearchParams();
          const values=version!==undefined ? all : fields;
          for(const [k,v] of Object.entries(values)) {if(Array.isArray(v))v.forEach(x=>body.append(k,x));else body.set(k,String(v));}
          if(version!==undefined)body.set('version',version);
          if(url.endsWith('/account/profile')||url.endsWith('/account/preferences'))body.set('expected_values',JSON.stringify(Object.fromEntries(Object.keys(fields).map(k=>[k,previous[k]]))));
          if('selected_provider_calendar_ids' in all)body.set('expected_selected_ids',JSON.stringify(previous.selected_provider_calendar_ids));
          return (await request(url,{method:'POST',headers:headers(),body})).json();
        },
        async load() {
          const response=await request(location.href,{headers:headers()});
          const doc=new DOMParser().parseFromString(await response.text(),'text/html');
          if(meta('graf-time-user',doc)!==actor||meta('graf-workspace',doc)!==workspace)throw new Error('scope');
          const matches=Array.from(doc.querySelectorAll('form[data-settings-autosave]')).filter(f=>new URL(f.getAttribute('action'),location.href).href===url);
          if(!matches.length)throw new Error('unavailable');
          return {values:Object.assign({},...matches.map(read)),version:matches[0].elements.namedItem('version')?.value};
        },
      });
      write(form,queue.attach(read(form)));
      let composing=false;
      const update=event=>{
        if(composing||event.isComposing||!event.target.name||event.target.type==='search')return;
        if(['checkbox','radio'].includes(event.target.type)) {
          // Read after the calendar limit handler has accepted or reverted the choice.
          if(event.type==='change')queueMicrotask(()=>queue.edit(read(form)));
        } else queue.edit(read(form),event.type==='input'?500:0);
      };
      form.addEventListener('input',update);form.addEventListener('change',update);
      form.addEventListener('compositionstart',()=>{composing=true;});
      form.addEventListener('compositionend',event=>{composing=false;update(event);});
      form.addEventListener('calendar:baseline',()=>{if(!queue.pending())queue.refresh(read(form));});
      form.addEventListener('submit',event=>{event.preventDefault();queue.flush();});
    });
  }
  const pending=()=>Array.from(queues.values()).some(q=>q.pending());
  const flushAll=async()=> (await Promise.all(Array.from(queues.values(),q=>q.flush()))).every(Boolean);
  const prepareToLeave=async()=>{
    if(!pending()||await flushAll())return true;
    if(!window.confirm('Изменения не сохранены. Выйти без сохранения?'))return false;
    await Promise.all(Array.from(queues.values(),q=>q.discard()));return true;
  };
  window.GRAFSettings={init,create,request,headers,pending,flushAll,prepareToLeave};
  window.addEventListener('beforeunload',event=>{if(pending()){event.preventDefault();event.returnValue='';}});
  document.addEventListener('click',async event=>{
    const link=event.target.closest('a[href]');
    if(!link||event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||link.target==='_blank'||!pending())return;
    const destination=new URL(link.href,location.href);if(destination.href===location.href||destination.hash&&destination.pathname===location.pathname)return;
    event.preventDefault();event.stopImmediatePropagation();if(await prepareToLeave())location.assign(destination.href);
  },true);
  document.addEventListener('submit',async event=>{
    const form=event.target;if(!form.hasAttribute('action')||form.hasAttribute('data-settings-autosave')||!pending())return;
    event.preventDefault();event.stopImmediatePropagation();const submitter=event.submitter;if(await prepareToLeave())form.requestSubmit(submitter);
  },true);
  document.addEventListener('DOMContentLoaded',init);document.addEventListener('htmx:afterSwap',init);
})();
