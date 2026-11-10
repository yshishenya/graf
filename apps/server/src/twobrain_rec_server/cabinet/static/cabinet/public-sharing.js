/* Public reading has no dependency on an owner's session or private review DTO. */
(() => {
  'use strict';
  function parseFragment(hash) {
    const match = /^#(outcomes|recording)(?:\?position_ms=([0-9]{1,8}))?$/.exec(hash || '#outcomes');
    if (!match || (match[2] && (match[1] !== 'recording' || Number(match[2]) > 86400000))) return {tab: 'outcomes', position: null};
    return {tab: match[1], position: match[2] ? Number(match[2]) : null};
  }
  if (typeof module !== 'undefined') module.exports = {parseFragment};
  if (typeof document === 'undefined') return;
  document.querySelectorAll('[data-public-sharing]').forEach(root => {
    const one = selector => root.querySelector(selector);
    const all = selector => [...root.querySelectorAll(selector)];
    const audio = one('[data-playback-player]');
    const status = one('[data-public-status]');
    let current = parseFragment(location.hash), pendingSeek = null;
    let changed = root.dataset.sourceChanged === 'true';
    const tell = text => { status.textContent = text; };
    function seek(ms) {
      if (!audio || changed) return;
      if (!Number.isFinite(audio.duration)) { pendingSeek = ms; audio.load(); return; }
      audio.currentTime = Math.min(ms / 1000, Math.max(0, audio.duration));
      pendingSeek = null;
    }
    function activate(applyPosition = true) {
      current = parseFragment(location.hash);
      if (!one(`[data-public-panel="${current.tab}"]`)) current = {tab:'outcomes',position:null};
      all('[data-public-panel]').forEach(panel => { panel.hidden = panel.dataset.publicPanel !== current.tab; });
      all('[data-public-tab]').forEach(tab => { tab.setAttribute('aria-current', tab.dataset.publicTab === current.tab ? 'page' : 'false'); });
      if (applyPosition && current.position !== null) seek(current.position);
    }
    activate(); window.addEventListener('hashchange', () => activate());
    root.addEventListener('graf:public-recording', event => {
      const fragment = '#recording?position_ms=' + Math.round(event.detail.seconds * 1000);
      if (location.hash !== fragment) history.pushState(null, '', fragment);
      // The shared player already moved when its metadata was ready.
      activate(!Number.isFinite(audio?.duration));
    });
    all('[data-public-seek]').forEach(link => link.addEventListener('click', () => seek(Number(link.dataset.publicSeek))));
    const welcome = one('[data-public-welcome]');
    let seen = false;
    try { seen = sessionStorage.getItem('graf-shared-welcome') === 'seen'; } catch (_) { /* storage is optional */ }
    function dismiss() { welcome.close(); try { sessionStorage.setItem('graf-shared-welcome', 'seen'); } catch (_) {} one('[data-public-tab]').focus(); }
    all('[data-public-welcome-close]').forEach(button => button.addEventListener('click', dismiss));
    welcome.addEventListener('cancel', () => { try { sessionStorage.setItem('graf-shared-welcome', 'seen'); } catch (_) {} });
    if (!seen && root.dataset.authenticated !== 'true' && typeof welcome.showModal === 'function') welcome.showModal();
    async function copy(text) {
      try { await navigator.clipboard.writeText(text); tell('Скопировано'); }
      catch (_) { tell('Не удалось скопировать. Выделите нужный текст и скопируйте его вручную.'); }
    }
    const copyButton = one('[data-public-copy]'); copyButton.hidden = false;
    copyButton.addEventListener('click', () => copy(one(`[data-public-panel="${current.tab}"]`).innerText));
    one('[data-public-copy-link]').addEventListener('click', () => copy(location.href));
    const search = one('[data-public-search]'); if(search) one('[data-public-search-label]').hidden = false;
    search?.addEventListener('input', () => {
      const query = search.value.trim().toLocaleLowerCase(); let count = 0;
      all('[data-public-turn]').forEach(turn => { turn.hidden = !!query && !turn.textContent.toLocaleLowerCase().includes(query); if (!turn.hidden) count++; });
      one('[data-public-search-count]').textContent = query ? `Найдено реплик: ${count}` : '';
    });
    function contextURL(href, native) {
      const url = new URL(href, location.origin);
      url.searchParams.set('tab', current.tab);
      if(root.dataset.mediaVersion) url.searchParams.set('media_version', root.dataset.mediaVersion);
      const position = audio && !changed ? (pendingSeek ?? Math.round(audio.currentTime * 1000)) : current.position;
      url.searchParams.delete('position_ms');
      if (current.tab === 'recording' && !changed && position !== null) url.searchParams.set('position_ms', String(position));
      return native ? url.href : url.pathname + url.search;
    }
    all('[data-public-auth]').forEach(link => link.addEventListener('click', () => { link.href = contextURL(link.href, false); }));
    const nativeLink = one('[data-public-native]');
    const appMenu = nativeLink.closest('details');
    const appHelp = one('[data-public-app-help]');
    nativeLink.addEventListener('click', event => {
      event.currentTarget.href = contextURL(event.currentTarget.href, true);
      appHelp.hidden = false;
      appMenu.open = false;
      appHelp.querySelector('h2').focus({preventScroll: true});
      appHelp.scrollIntoView({block: 'nearest'});
    });
    one('[data-public-app-dismiss]').addEventListener('click', () => {
      appHelp.hidden = true;
      appMenu.querySelector('summary').focus();
    });
    const refresh = one('[data-public-refresh]');
    if (refresh) refresh.addEventListener('click', () => { changed = false; root.dataset.sourceChanged = 'false'; pendingSeek = null; location.hash = '#recording'; if (audio) audio.currentTime = 0; refresh.closest('aside').hidden = true; });
    const footer = one('.public-reader__player');
    if (footer && typeof ResizeObserver !== 'undefined') {
      new ResizeObserver(() => root.style.setProperty('--public-player-height', footer.getBoundingClientRect().height + 'px')).observe(footer);
    }
    if (audio) {
      audio.addEventListener('loadedmetadata', () => { if (pendingSeek !== null) seek(pendingSeek); });
      audio.addEventListener('error', () => tell('Запись не загрузилась. Возможно, владелец изменил доступ или обновил запись. Обновите страницу.'));
    }
  });
})();
