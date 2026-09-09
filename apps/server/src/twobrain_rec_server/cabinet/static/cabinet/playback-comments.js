(() => {
  "use strict";
  const instances = new WeakMap();
  let outsideEditor = null;
  document.addEventListener("pointerdown", event => outsideEditor?.(event));
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const button = (label, action, className = "") => {
    const node = el("button", className, label);
    node.type = "button";
    node.addEventListener("click", action);
    return node;
  };
  const time = (ms) => {
    const seconds = Math.max(0, Math.floor(Number(ms) / 1000));
    return [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60]
      .map(value => String(value).padStart(2, "0")).join(":");
  };
  const count = value => Array.from(value).length;
  const emojiNames = { "👍": "Согласен палец вверх", "👎": "Не согласен палец вниз", "❤️": "Сердце любовь", "🎉": "Праздник поздравление", "😄": "Радость улыбка", "😕": "Сомнение", "👀": "Глаза внимание", "✅": "Готово галочка", "🙏": "Спасибо", "🚀": "Ракета" };
  const errors = {
    401: "Сессия завершилась. Войдите снова.",
    403: "Недостаточно прав для этого действия.",
    404: "Обсуждение или эта версия записи больше недоступны.",
    409: "Обсуждение изменилось. Обновите его перед повторным сохранением. Ваш текст сохранён в форме.",
    422: "Проверьте текст, упоминания и временную отметку."
  };

  function init(shell) {
    if (instances.has(shell)) { instances.get(shell)(); return; }
    const trigger = shell.querySelector("[data-playback-comment]");
    const audio = shell.querySelector("[data-playback-player]");
    if (!trigger || !audio || !shell.dataset.meetingId) return;
    instances.set(shell, renderBadges);
    const base = new URL(shell.dataset.commentsUrl || `/api/v1/cabinet/meetings/${encodeURIComponent(shell.dataset.meetingId)}/comments`, location.origin);
    if (base.origin !== location.origin) return;
    if (shell.dataset.workspaceId) base.searchParams.set("workspace_id", shell.dataset.workspaceId);
    let capabilities = { can_comment: false }, emojiOptions = [], roots = [], nextCursor = null;
    let sourceCounts = new Map(), sourceFilter = [];
    let composer = null, picker = null, returnFocus = trigger, loading = false, mutationPending = false, requestSequence = 0;
    const aside = el("aside", "playback-comments");
    aside.hidden = true;
    aside.setAttribute("aria-label", "Обсуждения записи");
    const head = el("header", "playback-comments-header");
    const heading = el("h2", "", "Обсуждения");
    const close = button("Закрыть", () => hide(), "playback-comments-close");
    head.append(heading, close);
    const status = el("p", "playback-comments-status");
    status.setAttribute("role", "status");
    const filters = el("div", "playback-comments-filters");
    const stateSelect = el("select");
    stateSelect.setAttribute("aria-label", "Состояние обсуждения");
    for (const [value, label] of [["open", "Открытые"], ["resolved", "Завершённые"], ["all", "Все обсуждения"]]) {
      const option = el("option", "", label); option.value = value; stateSelect.append(option);
    }
    const authorSelect = el("select");
    authorSelect.setAttribute("aria-label", "Автор обсуждения");
    const allAuthors = el("option", "", "Все авторы"); allAuthors.value = ""; authorSelect.append(allAuthors);
    const source = button("Расшифровка", () => { sourceFilter = []; load(); }, "playback-comments-source");
    source.disabled = true;
    source.title = "Источник комментариев";
    filters.append(stateSelect, authorSelect, source);
    const list = el("div", "playback-comments-list");
    const more = button("Загрузить ещё", () => load(true)); more.hidden = true;
    const add = button("Добавить комментарий", () => edit()); add.hidden = true;
    aside.append(head, filters, status, list, more, add);
    shell.append(aside);

    async function request(suffix = "", method = "GET", body, params = {}) {
      const url = new URL(base);
      url.pathname += suffix;
      for (const [key, value] of Object.entries(params)) if (value != null && value !== "") {
        for (const item of Array.isArray(value) ? value : [value]) url.searchParams.append(key, item);
      }
      const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
      const response = await fetch(url, {
        method, credentials: "same-origin", cache: "no-store",
        headers: { Accept: "application/json", ...(body ? { "Content-Type": "application/json" } : {}), ...(method !== "GET" && csrf ? { "X-CSRF-Token": csrf } : {}) },
        ...(body ? { body: JSON.stringify(body) } : {})
      });
      if (!response.ok) {
        const error = new Error(errors[response.status] || "Не удалось загрузить или сохранить обсуждение. Попробуйте ещё раз.");
        error.status = response.status; throw error;
      }
      return response.status === 204 ? {} : response.json();
    }
    function announce(message) { status.textContent = message; }
    function busy() {
      list.inert = loading || mutationPending;
      filters.inert = mutationPending;
      more.disabled = loading || mutationPending;
      aside.setAttribute("aria-busy", String(loading || mutationPending));
    }
    function beginMutation() {
      ++requestSequence; loading = false; mutationPending = true; busy();
    }
    function seek(comment) {
      if (String(comment.media_revision_id) !== shell.dataset.mediaRevisionId) {
        announce("Этот комментарий относится к другой версии записи."); return;
      }
      const sourceId = comment.source_segment_id;
      const turn = sourceId && [...document.querySelectorAll("[data-transcript-turn]")].find(node => (node.dataset.sourceSegments || "").split(/[\s,]+/).includes(sourceId));
      if (sourceId && !turn) {
        announce("Источник комментария отсутствует в текущей расшифровке."); return;
      }
      shell.dataset.playbackSourceSegments = sourceId || "";
      audio.currentTime = Math.max(0, Number(comment.start_ms) / 1000);
      if (turn) { turn.scrollIntoView({ block: "center" }); turn.focus({ preventScroll: true }); }
    }
    function hide() {
      if (composer?.dataset.pending === "true") return;
      aside.hidden = true;
      dismissEditor();
      trigger.setAttribute("aria-expanded", "false");
      (returnFocus?.isConnected ? returnFocus : trigger).focus();
    }
    function show() { aside.hidden = false; trigger.setAttribute("aria-expanded", "true"); }
    function dismissPicker() { picker?.remove(); picker = null; }
    function dismissEditor() { dismissPicker(); composer?.remove(); composer = null; outsideEditor = null; }
    function renderBadges() {
      if (!shell.isConnected) return;
      for (const turn of document.querySelectorAll("[data-transcript-turn]")) {
        const ids = [...new Set((turn.dataset.sourceSegments || "").split(/\s+/).filter(Boolean))];
        const total = ids.reduce((sum, id) => sum + (sourceCounts.get(id) || 0), 0);
        let badge = turn.querySelector("[data-comment-count]");
        if (!total) { badge?.remove(); continue; }
        if (!badge) {
          badge = button("", event => {
            returnFocus = event.currentTarget;
            sourceFilter = ids; stateSelect.value = "all"; authorSelect.value = "";
            show(); close.focus(); load();
          }, "playback-comment-count");
          const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
          icon.setAttribute("viewBox", "0 0 20 20"); icon.setAttribute("aria-hidden", "true");
          const outline = document.createElementNS("http://www.w3.org/2000/svg", "path");
          outline.setAttribute("d", "M5 3.5h10a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H8l-4 3v-3a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2Z");
          icon.append(outline); badge.append(icon, el("span"));
          badge.dataset.commentCount = ""; turn.append(badge);
        }
        badge.lastChild.textContent = String(total);
        badge.setAttribute("aria-label", `Обсуждения реплики: ${total}`);
      }
    }
    function render() {
      const draft = composer;
      const draftRoot = draft?.dataset.rootId;
      const focused = draft?.contains(document.activeElement) ? document.activeElement : null;
      if (draftRoot) draft.remove();
      list.replaceChildren();
      if (!roots.length) {
        list.append(el("p", "playback-comments-empty", "Нет обсуждений с выбранными фильтрами."));
        list.append(button("Показать все открытые", () => { stateSelect.value = "open"; authorSelect.value = ""; sourceFilter = []; load(); }));
      }
      for (const root of roots) list.append(thread(root));
      more.hidden = !nextCursor;
      add.hidden = !capabilities.can_comment;
      source.textContent = sourceFilter.length ? "Эта реплика ×" : "Расшифровка";
      source.disabled = !sourceFilter.length;
      renderBadges();
      if (draftRoot) {
        (list.querySelector(`[data-comment-id="${draftRoot}"]`) || aside).append(draft);
        focused?.focus({ preventScroll: true });
      }
    }
    function rememberAuthors(items) {
      const known = new Set([...authorSelect.options].map(option => option.value));
      for (const item of items) if (item.author_user_id && !known.has(item.author_user_id)) {
        const option = el("option", "", item.author_label); option.value = item.author_user_id; authorSelect.append(option); known.add(item.author_user_id);
      }
    }
    async function load(append = false) {
      const sequence = ++requestSequence;
      loading = true; busy(); announce("Загружаем обсуждения…");
      try {
        const data = await request("", "GET", null, { status: stateSelect.value, author_id: authorSelect.value, source_segment_ids: sourceFilter, limit: 50, cursor: append ? nextCursor : null });
        if (sequence !== requestSequence || !shell.isConnected) return;
        if (data.media_revision_id !== shell.dataset.mediaRevisionId) {
          capabilities = { can_comment: false }; roots = []; nextCursor = null; sourceCounts.clear(); render();
          announce("Версия записи изменилась. Обновите страницу, чтобы открыть обсуждения."); return;
        }
        capabilities = data.capabilities; emojiOptions = capabilities.emoji_options || [];
        sourceCounts = new Map((data.source_counts || []).map(item => [item.source_segment_id, item.count]));
        roots = append ? [...roots, ...data.items.filter(item => !roots.some(root => root.id === item.id))] : data.items;
        nextCursor = data.next_cursor; rememberAuthors(roots); render(); announce("");
        return true;
      } catch (error) {
        if (sequence === requestSequence) {
          if ([401, 403, 404].includes(error.status)) { capabilities = { can_comment: false }; roots = []; nextCursor = null; sourceCounts.clear(); render(); }
          announce(error.message);
        }
      }
      finally { if (sequence === requestSequence) { loading = false; busy(); } }
      return false;
    }
    async function openThread(id) {
      const sequence = ++requestSequence; loading = true; busy();
      show(); announce("Загружаем обсуждение…");
      try {
        const data = await request(`/${encodeURIComponent(id)}`);
        if (sequence !== requestSequence || !shell.isConnected) return;
        if (data.media_revision_id !== shell.dataset.mediaRevisionId) throw new Error("Обсуждение относится к другой версии записи. Обновите страницу.");
        roots = [data]; nextCursor = null; render(); announce("");
        loading = false; busy();
        const target = list.querySelector(`[data-comment-card-id="${CSS.escape(id)}"]`);
        target?.focus({ preventScroll: true });
        target?.scrollIntoView({ block: "nearest", behavior: "instant" });
      } catch (error) { if (sequence === requestSequence) announce(error.message); }
      finally { if (sequence === requestSequence) { loading = false; busy(); } }
    }
    async function change(control, suffix, method, body) {
      if (mutationPending || loading) return false;
      beginMutation();
      control.disabled = true;
      try {
        const data = await request(suffix, method, body);
        if (data.id) {
          const updated = data.parent_id ? await request(`/${data.parent_id}`) : data;
          roots = roots.map(root => root.id === updated.id ? updated : root);
          render();
        } else await load();
        announce("");
        return true;
      } catch (error) { announce(error.message); }
      finally { mutationPending = false; busy(); control.disabled = false; }
      return false;
    }
    function thread(root) {
      const container = el("section", "playback-comment-thread");
      container.dataset.commentId = root.id;
      container.append(commentCard(root, root));
      const replies = el("div", "playback-comment-replies");
      for (const reply of root.replies || []) replies.append(commentCard(reply, root));
      container.append(replies);
      if (root.next_reply_cursor) {
        const next = button("Ещё ответы", async () => {
          next.disabled = true;
          try {
            const data = await request(`/${encodeURIComponent(root.id)}/replies`, "GET", null, { limit: 50, cursor: root.next_reply_cursor });
            root.replies = [...(root.replies || []), ...data.items.filter(item => !(root.replies || []).some(reply => reply.id === item.id))]
              .sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at) || a.id.localeCompare(b.id));
            root.next_reply_cursor = data.next_cursor; render();
          } catch (error) { announce(error.message); next.disabled = false; }
        });
        container.append(next);
      }
      return container;
    }
    function commentCard(comment, root) {
      const card = el("article", "playback-comment");
      card.dataset.commentCardId = comment.id;
      card.tabIndex = -1;
      const meta = el("div", "playback-comment-meta");
      meta.append(el("strong", "", comment.author_label || "Участник"));
      const stamp = el("time"); stamp.dateTime = comment.created_at;
      stamp.textContent = new Date(comment.created_at).toLocaleString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
      meta.append(stamp);
      if (comment.edited_at) meta.append(el("span", "", "изменён"));
      card.append(meta);
      if (!comment.parent_id) card.append(button(time(root.start_ms), () => seek(root), "playback-comment-anchor"));
      card.append(el("p", "playback-comment-body", comment.body));
      const actions = el("div", "playback-comment-actions");
      const rights = { can_edit: comment.can_edit, can_delete: comment.can_delete, can_resolve: comment.can_resolve, can_react: capabilities.can_comment, can_reply: capabilities.can_comment };
      if (rights.can_reply) actions.append(button("Ответить", event => edit({ root }, event.currentTarget)));
      const reactions = el("div", "playback-comment-reactions");
      for (const reaction of comment.reactions || []) {
        const control = button(`${reaction.emoji} ${reaction.count}`, () => change(control, `/${comment.id}/reaction`, "PUT", { emoji: reaction.emoji, selected: !reaction.selected }));
        control.disabled = !rights.can_react;
        control.setAttribute("aria-pressed", String(reaction.selected));
        control.setAttribute("aria-label", `Реакция ${reaction.emoji}: ${reaction.count}`);
        reactions.append(control);
      }
      if (rights.can_react) reactions.append(button("＋ Реакция", event => {
        const opener = event.currentTarget;
        emojiPicker(opener, emoji => change(opener, `/${comment.id}/reaction`, "PUT", { emoji, selected: true }));
      }));
      if (rights.can_edit) actions.append(button("Изменить", event => edit({ comment, root }, event.currentTarget)));
      if (rights.can_resolve && !comment.parent_id) {
        const resolve = button(root.resolved ? "Возобновить" : "Завершить", async () => {
          if (await change(resolve, `/${root.id}/resolution`, "PUT", { expected_version: root.version, resolved: !root.resolved })) await load();
        }); actions.append(resolve);
      }
      actions.append(button("Ссылка", async () => {
        const url = new URL(location.href); url.searchParams.set("comment_id", comment.id);
        try { await navigator.clipboard.writeText(url.href); announce("Ссылка скопирована. Доступ к записи не изменился."); }
        catch { announce("Не удалось скопировать ссылку."); }
      }));
      if (rights.can_delete) actions.append(button("Удалить", event => confirmDelete(comment, event.currentTarget)));
      card.append(reactions, actions);
      return card;
    }
    function confirmDelete(comment, opener) {
      const dialog = el("dialog", "playback-comment-delete");
      dialog.setAttribute("aria-label", "Удалить комментарий");
      const title = el("h2", "", "Удалить комментарий?");
      const description = el("p", "", comment.parent_id ? "Комментарий и его реакции будут удалены." : "Обсуждение, все ответы и реакции будут удалены.");
      const error = el("p"); error.setAttribute("role", "alert");
      const cancel = button("Отмена", () => dialog.close());
      const refresh = button("Обновить список", () => { dialog.close(); load(); }); refresh.hidden = true;
      const confirm = button("Удалить", async () => {
        if (mutationPending) return;
        beginMutation();
        confirm.disabled = true; cancel.disabled = true; refresh.disabled = true;
        try {
          await request(`/${comment.id}`, "DELETE", { expected_version: comment.version });
          dialog.close(); await load();
        } catch (failure) {
          error.textContent = failure.status === 409 ? "Обсуждение изменилось. Обновите список и снова выберите комментарий для удаления." : failure.message;
          refresh.hidden = failure.status !== 409;
        }
        finally { mutationPending = false; busy(); confirm.disabled = !refresh.hidden; cancel.disabled = false; refresh.disabled = false; }
      }, "playback-comment-danger");
      dialog.append(title, description, error, refresh, cancel, confirm);
      dialog.addEventListener("close", () => { dialog.remove(); (opener.isConnected ? opener : close).focus(); });
      shell.append(dialog); dialog.showModal(); cancel.focus();
    }
    function emojiPicker(opener, select) {
      dismissPicker();
      const popup = el("div", "playback-comment-picker"); picker = popup;
      popup.setAttribute("role", "dialog"); popup.setAttribute("aria-label", "Выбрать emoji");
      const search = el("input"); search.type = "search"; search.placeholder = "Поиск emoji"; search.setAttribute("aria-label", "Поиск emoji");
      const options = el("div", "playback-comment-emoji-options");
      const draw = () => {
        options.replaceChildren();
        for (const emoji of emojiOptions) {
          const label = emojiNames[emoji] || emoji;
          if (search.value && !`${emoji} ${label}`.toLocaleLowerCase().includes(search.value.toLocaleLowerCase())) continue;
          const choice = button(emoji, () => { dismissPicker(); select(emoji); opener.focus(); });
          choice.title = label; options.append(choice);
        }
        if (!options.childElementCount) options.append(el("p", "", "Нет подходящих emoji"));
      };
      search.addEventListener("input", draw); popup.append(search, options);
      opener.parentElement.append(popup); draw(); search.focus();
      popup.addEventListener("keydown", event => { if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); dismissPicker(); opener.focus(); } });
    }
    function edit(context = {}, opener = trigger) {
      if (composer?.dataset.pending === "true") return;
      if (!capabilities.can_comment) { show(); return; }
      dismissEditor(); returnFocus = opener;
      const { comment, root } = context;
      const form = el("form", "playback-comment-editor"); composer = form;
      outsideEditor = event => {
        if (!form.isConnected) { outsideEditor = null; return; }
        if (!form.contains(event.target) && !trigger.contains(event.target) && form.dataset.pending !== "true") dismissEditor();
      };
      if (root) form.dataset.rootId = root.id;
      form.setAttribute("aria-label", comment ? "Изменить комментарий" : root ? "Ответить на комментарий" : "Новый комментарий");
      const anchor = {
        media_revision_id: shell.dataset.mediaRevisionId,
        start_ms: Math.max(0, Math.round((audio.currentTime || 0) * 1000))
      };
      const requestId = crypto.randomUUID();
      let mentions = (comment?.mentions || []).map(item => ({ user_id: item.user_id, start: item.start, end: item.end }));
      let previous = comment?.body || "", pending = false, mentionSequence = 0, expectedVersion = comment?.version;
      const label = el("div", "playback-comment-editor-title", comment ? "Изменить комментарий" : root ? "Ответ" : "Комментарий");
      if (!comment && !root) {
        const stamp = button(time(anchor.start_ms), () => seek(anchor), "playback-comment-anchor"); label.append(stamp);
        const activeTurns = [...document.querySelectorAll("[data-transcript-turn]")].filter(node => Number(node.dataset.startSeconds) <= anchor.start_ms / 1000 && Number(node.dataset.endSeconds) > anchor.start_ms / 1000);
        const turn = activeTurns.find(node => node.classList.contains("is-current")) || activeTurns.at(-1);
        const segmentId = turn?.dataset.sourceSegments?.split(/[\s,]+/)[0];
        if (segmentId && shell.dataset.processingResultId) {
          const moment = anchor.start_ms;
          let wholeTurn = false;
          Object.assign(anchor, { source_segment_id: segmentId, processing_result_id: shell.dataset.processingResultId });
          const bind = button("К реплике", () => {
            wholeTurn = !wholeTurn;
            if (!wholeTurn) {
              delete anchor.end_ms;
              anchor.start_ms = moment; bind.textContent = "К реплике";
            } else {
              Object.assign(anchor, { start_ms: Math.round(Number(turn.dataset.startSeconds) * 1000), end_ms: Math.round(Number(turn.dataset.endSeconds) * 1000) });
              bind.textContent = "К моменту";
            }
            stamp.textContent = time(anchor.start_ms);
          }); label.append(bind);
        }
      }
      const input = el("textarea"); input.rows = 1; input.value = previous; input.placeholder = "Добавить комментарий…"; input.setAttribute("aria-label", "Текст комментария");
      const error = el("p", "playback-comment-editor-error"); error.setAttribute("role", "alert");
      const tools = el("div", "playback-comment-editor-tools");
      const submit = el("button", "playback-comment-send", comment ? "Сохранить" : "Отправить"); submit.type = "submit";
      const cancel = button("Отмена", () => { dismissEditor(); (opener.isConnected ? opener : trigger).focus(); });
      const emoji = button("☺", () => emojiPicker(emoji, value => insert(value))); emoji.setAttribute("aria-label", "Добавить emoji");
      const mention = button("@", () => { insert("@"); suggest(); }); mention.setAttribute("aria-label", "Упомянуть участника");
      const browse = button("Все комментарии", () => { dismissEditor(); show(); load(); });
      const refresh = button("Обновить обсуждение", async () => {
        refresh.disabled = true;
        try {
          const data = await request(`/${comment.id}`);
          let current = data.id === comment.id ? data : (data.replies || []).find(item => item.id === comment.id);
          let cursor = data.next_reply_cursor;
          while (!current && cursor) {
            const page = await request(`/${data.id}/replies`, "GET", null, { cursor, limit: 100 });
            current = page.items.find(item => item.id === comment.id); cursor = page.next_cursor;
          }
          if (!current) throw new Error("Комментарий больше недоступен. Ваш текст остаётся в форме.");
          expectedVersion = current.version;
          error.textContent = "Версия обновлена. Проверьте свой текст перед сохранением.";
        } catch (failure) { error.textContent = failure.message; }
        finally { refresh.disabled = false; }
      });
      refresh.hidden = !comment;
      tools.append(emoji, mention, cancel, submit);
      form.append(label, input, error, refresh, tools);
      if (!root && !comment) form.append(browse);
      (root ? list.querySelector(`[data-comment-id="${root.id}"]`) || aside : shell).append(form);
      function validate() {
        form.dataset.pending = String(pending);
        submit.disabled = pending || !input.value.trim() || count(input.value) > 10000 || mentions.length > 20;
        for (const control of form.querySelectorAll("button")) if (control !== submit) control.disabled = pending;
      }
      function trackEdit() {
        const old = Array.from(previous), next = Array.from(input.value);
        let start = 0; while (start < old.length && start < next.length && old[start] === next[start]) start++;
        let end = old.length, nextEnd = next.length;
        while (end > start && nextEnd > start && old[end - 1] === next[nextEnd - 1]) { end--; nextEnd--; }
        const delta = nextEnd - end;
        mentions = mentions.filter(item => item.end <= start || item.start >= end).map(item => item.start >= end ? { ...item, start: item.start + delta, end: item.end + delta } : item);
        previous = input.value; validate();
      }
      function insert(value) {
        input.setRangeText(value, input.selectionStart, input.selectionEnd, "end"); trackEdit(); input.focus();
      }
      async function suggest() {
        const prefix = input.value.slice(0, input.selectionStart);
        const match = /(?:^|\s)@([^@\n]{0,100})$/.exec(prefix);
        const sequence = ++mentionSequence;
        if (!match) { dismissPicker(); return; }
        try {
          const url = new URL(base); url.pathname = url.pathname.replace(/\/comments$/, "/comment-mention-candidates"); url.searchParams.set("q", match[1]);
          const response = await fetch(url, { credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" } });
          if (!response.ok) throw new Error(errors[response.status] || "Не удалось найти участников.");
          const data = await response.json();
          if (sequence !== mentionSequence || composer !== form || !form.isConnected) return;
          dismissPicker(); const popup = el("div", "playback-comment-picker playback-comment-mentions"); picker = popup;
          popup.setAttribute("role", "group"); popup.setAttribute("aria-label", "Участники с доступом к записи");
          for (const candidate of data.items) popup.append(button(candidate.display_label, () => {
            const end = input.selectionStart, start = prefix.lastIndexOf("@");
            const display = `@${candidate.display_label}`;
            input.setSelectionRange(start, end); insert(display + " ");
            mentions = mentions.filter(item => item.user_id !== candidate.user_id);
            mentions.push({ user_id: candidate.user_id, start: count(input.value.slice(0, start)), end: count(input.value.slice(0, start)) + count(display) });
            dismissPicker(); validate(); input.focus();
          }));
          if (!data.items.length) popup.append(el("p", "", "Нет участников с доступом"));
          form.append(popup);
        } catch (failure) { if (sequence === mentionSequence) error.textContent = failure.message; }
      }
      input.addEventListener("input", () => { trackEdit(); suggest(); });
      input.addEventListener("keydown", event => {
        if (event.key === "ArrowDown" && picker) { event.preventDefault(); picker.querySelector("button")?.focus(); }
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && !submit.disabled) { event.preventDefault(); form.requestSubmit(); }
      });
      form.addEventListener("submit", async event => {
        event.preventDefault(); if (submit.disabled || mutationPending || loading) return;
        beginMutation();
        pending = true; dismissPicker(); validate(); error.textContent = ""; input.readOnly = true;
        try {
          const body = { body: input.value, mentions };
          const path = comment ? `/${comment.id}` : root ? `/${root.id}/replies` : "";
          if (comment) body.expected_version = expectedVersion;
          else Object.assign(body, { request_id: requestId }, root ? {} : anchor);
          const data = await request(path, comment ? "PATCH" : "POST", body);
          if (composer !== form) return;
          const updated = data.parent_id ? await request(`/${data.parent_id}`) : data;
          dismissEditor(); show();
          if (await load()) { roots = [updated]; nextCursor = null; render(); announce("Комментарий сохранён."); }
          close.focus();
        } catch (failure) { error.textContent = failure.message; }
        finally { mutationPending = false; busy(); pending = false; input.readOnly = false; validate(); }
      });
      validate(); input.focus();
    }
    trigger.setAttribute("aria-expanded", "false");
    trigger.addEventListener("click", async () => {
      returnFocus = trigger;
      await load();
      if (loading) return;
      if (capabilities.can_comment) edit(); else show();
    });
    stateSelect.addEventListener("change", () => load()); authorSelect.addEventListener("change", () => load());
    shell.addEventListener("keydown", event => {
      if (event.key !== "Escape" || event.target.closest("dialog")) return;
      if (picker) { event.preventDefault(); event.stopPropagation(); dismissPicker(); composer?.querySelector("textarea")?.focus(); }
      else if (composer) { event.preventDefault(); event.stopPropagation(); if (composer.dataset.pending !== "true") { dismissEditor(); trigger.focus(); } }
      else if (!aside.hidden) { event.preventDefault(); event.stopPropagation(); hide(); }
    });
    const commentId = new URL(location.href).searchParams.get("comment_id");
    load().then(() => { if (commentId) openThread(commentId); });
  }
  window.GRAFPlaybackComments = { init };
})();
