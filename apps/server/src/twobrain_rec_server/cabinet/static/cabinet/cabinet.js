(() => {
  document.documentElement.dataset.cabinetJs = "ready";

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
  let pendingDeleteRows = [];
  let deleteReturnFocus = null;
  let deleteReturnMeetingId = "";
  let deleteFocusFallbackIds = [];
  let listRefreshFocusMeetingIds = [];
  let listRefreshShouldRestoreFocus = false;
  let listRefreshFocusOrigin = null;
  let playbackRecoveryTimer = null;
  let playbackRecoveryRequest = null;
  let calendarUpcomingRefreshTimer = null;
  let processingRecoveryCountdownTimer = null;
  let processingRecoveryPollTimer = null;
  let processingRecoveryRequest = null;
  let processingRecoveryStatusController = null;
  let processingRecoveryActionRequest = null;
  let processingRecoveryGeneration = 0;
  let processingReprocessReturnFocus = null;
  const processingListProjectionRequests = new Map();
  const processingListProjectionLastFetchedAt = new Map();
  const processingListProjectionStates = new Map();
  let processingListProjectionPollTimer = null;
  const resetProcessingListProjectionState = ({ preserveSnapshots = false } = {}) => {
    if (processingListProjectionPollTimer) window.clearTimeout(processingListProjectionPollTimer);
    processingListProjectionPollTimer = null;
    processingListProjectionRequests.forEach((entry, meetingId) => {
      entry.controller?.abort();
      if (preserveSnapshots) processingListProjectionLastFetchedAt.delete(meetingId);
    });
    processingListProjectionRequests.clear();
    if (!preserveSnapshots) {
      processingListProjectionLastFetchedAt.clear();
      processingListProjectionStates.clear();
    }
  };
  const selectedMeetingIds = new Set();
  const announcedUploadProgressBuckets = new Map();
  const announcedUploadProgressMetadata = new Map();
  const uploadProgressTrackingTtlMs = 5 * 60 * 1000;
  let uploadProgressTrackingPruneTimer = null;
  let meetingResultCountShouldAnnounce = false;
  let meetingResultCountHadRefinement = false;
  let meetingResultCountAnnouncementVersion = 0;
  let meetingListRequestGeneration = 0;
  let activeMeetingListRequests = 0;
  const authoritativeMeetingListRequests = new WeakSet();
  const authoritativeMeetingListRequestGenerations = new WeakMap();
  const progressPollRequestGenerations = new WeakMap();
  const meetingListRequestFocusRecoveries = new WeakMap();
  const handledMeetingListAuthorizationRequests = new WeakSet();
  const observedDetachedMeetingListRequests = new WeakSet();
  let scrubManualUploadPrivateState = () => false;
  let revokeManualUploadMeeting = () => {};
  const speakerTimelineResizeHandlers = new WeakMap();
  const accessLossProblemCodes = new Set([
    "auth_session_rejected",
    "device_quarantined",
    "device_revoked",
    "device_untrusted",
    "workspace_scope_denied",
  ]);
  const detailActionProblemCodes = new Set([
    "csrf_token_invalid",
    "csrf_token_missing",
    "export_forbidden",
    "export_policy_denied",
    "speaker_not_found",
  ]);
  const summaryActionProblemCodes = new Set([
    "summary_candidate_not_found",
    "summary_candidate_state_invalid",
    "summary_candidate_unavailable",
    "summary_dispatch_state_invalid",
    "summary_generation_forbidden",
    "summary_generation_unavailable",
    "summary_resolution_forbidden",
    "summary_revision_conflict",
    "summary_transcript_snapshot_invalid",
    "summary_transcript_too_large",
    "meeting_deleting",
    "meeting_deletion_active",
    "meeting_deleted",
    "summary_candidate_expired",
    "summary_source_revision_stale",
  ]);
  const sharingActionProblemCodes = new Set([
    "comment_permission_forbidden",
    "invalid_comment_permission",
    "grantee_not_found",
    "invalid_share_audience",
    "invitation_delivery_unavailable",
    "meeting_not_found",
    "public_share_scope_invalid",
    "share_expiry_required",
    "share_forbidden",
    "share_grant_not_found",
    "share_invitations_disabled",
    "share_not_found",
    "share_policy_blocked",
    "share_team_audience_unavailable",
  ]);

  const meetingDetailRecoveredError = () => {
    const error = new Error("meeting_detail_recovered");
    error.meetingDetailRecovered = true;
    return error;
  };

  const isMeetingDetailRecoveredError = (error) => error?.meetingDetailRecovered === true;

  const clearMeetingHistoryCache = () => {
    try {
      sessionStorage.removeItem("htmx-history-cache");
    } catch {
      // The page still blocks new history snapshots when storage is unavailable.
    }
  };

  const neutralizePrivateLocation = (neutralPath) => {
    try {
      history.replaceState(null, "", neutralPath);
    } catch {
      window.location.replace(neutralPath);
    }
  };
  clearMeetingHistoryCache();

  const plural = (value, one, few, many) => {
    const mod10 = value % 10;
    const mod100 = value % 100;
    if (mod10 === 1 && mod100 !== 11) return one;
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
    return many;
  };

  const currentList = () => document.querySelector("[data-meeting-list]");
  const allRows = () => Array.from(currentList()?.querySelectorAll("[data-meeting-row]") || []);
  const GENERATED_CAPTURE_TITLE_RE = /^(?:current(?: display)? system audio|system audio|yandex telemost|zoom(?:\.us)?|meeting)\s*[-—]\s*\d{4}-\d{2}-\d{2}(?:[ T]\d{1,2}:\d{2})?$/i;
  const formatMeetingListDate = (value) => window.GRAFTime.format(value);
  const localRecordingDisplayTitle = (item) => {
    const rawTitle = (item.title || "").trim();
    if (typeof item.generatedTitlePrefix === "string") {
      return `${item.generatedTitlePrefix}${formatMeetingListDate(item.startedAt)}`;
    }
    if (!GENERATED_CAPTURE_TITLE_RE.test(rawTitle)) return rawTitle || "Запись";
    const date = formatMeetingListDate(item.startedAt);
    return date === "Без даты" ? "Запись" : `Запись ${date}`;
  };
  const meetingListSort = () => document.querySelector("#meeting-sort")?.value || "started_desc";
  const sortMeetingRows = (list) => {
    const sort = meetingListSort();
    const key = sort.startsWith("updated") ? "sortUpdated" : sort.startsWith("duration") ? "sortDuration" : "sortStarted";
    const value = (row) => {
      if (sort === "title_asc") return (row.dataset.sortTitle || "").toLowerCase();
      const raw = row.dataset[key];
      if (!raw) return null;
      const number = key === "sortDuration" ? Number(raw) : Date.parse(raw);
      return Number.isFinite(number) ? number : null;
    };
    const focused = document.activeElement;
    const sorted = Array.from(list.querySelectorAll("[data-meeting-row]")).sort((left, right) => {
      const a = value(left), b = value(right);
      if (a === null && b !== null) return 1;
      if (a !== null && b === null) return -1;
      const order = a === b ? 0 : a < b ? -1 : 1;
      if (order) return order * (sort.endsWith("_desc") ? -1 : 1);
      const leftId = left.dataset.meetingId || left.dataset.grafLocalRecordingId || "";
      const rightId = right.dataset.meetingId || right.dataset.grafLocalRecordingId || "";
      return leftId < rightId ? -1 : leftId > rightId ? 1 : 0;
    });
    let previous = null;
    for (const row of sorted) {
      const next = previous ? previous.nextElementSibling : list.firstElementChild;
      if (row !== next) list.insertBefore(row, next);
      previous = row;
    }
    if (focused instanceof HTMLElement && focused.isConnected && document.activeElement !== focused) {
      focused.focus({preventScroll: true});
    }
  };
  const localRecordingMatches = (item) => {
    const access = document.querySelector("#meeting-access")?.value;
    const status = document.querySelector("#meeting-status")?.value;
    // Local custody does not prove server processing/readiness or team access.
    if ((access && access !== "owner") || status) return false;
    const query = (document.querySelector("#meeting-search")?.value || "").trim().toLowerCase().replace(/\s+/g, " ");
    if (!query) return true;
    const title = localRecordingDisplayTitle(item);
    const duration = window.GRAFTime.formatDuration(item.durationSeconds);
    const time = formatMeetingListDate(meetingListSort().startsWith("updated") ? item.updatedAt : item.startedAt);
    return [title, duration, time, `${title} ${duration}`, `${title} ${time}`, `${duration} ${time}`, `${title} ${duration} ${time}`]
      .some((text) => text.toLowerCase().replace(/\s+/g, " ").includes(query));
  };
  const updateMixedResultCount = () => {
    const host = currentList();
    let empty = host?.querySelector("[data-deletion-empty]");
    if (host && allRows().length === 0 && !host.querySelector(".empty-state")) {
      empty = document.createElement("p");
      empty.className = "empty-state";
      empty.dataset.deletionEmpty = "";
      empty.textContent = "Записей пока нет.";
      host.append(empty);
    } else if (allRows().length) { empty?.remove(); }
    const count = document.querySelector("[data-meeting-result-count]");
    if (count) {
      const incomplete = document.querySelector('[data-meeting-result-complete="false"]');
      count.textContent = `Найдено: ${incomplete ? "больше " : ""}${allRows().length}`;
    }
  };
  let localRecordingRows = [];
  const localRecordingMarkup = new WeakMap();
  const renderLocalRecordingRows = () => {
    const host = currentList();
    if (!host) return;
    const focused = document.activeElement;
    const focusedLocal = focused?.closest("[data-graf-local-recording-row]")?.dataset.grafLocalRecordingId;
    const focusedControl = focused?.matches("[data-meeting-select]") ? "[data-meeting-select]:not(:disabled)"
      : focused?.matches("[data-row-delete]") ? "[data-row-delete]:not(:disabled)"
      : focused?.dataset.grafLocalRecordingAction === "send" ? '[data-graf-local-recording-action="send"]:not(:disabled)'
      : "[data-meeting-open]:not(:disabled)";
    const existingRows = new Map([...host.querySelectorAll("[data-graf-local-recording-row]")].map(row => [row.dataset.grafLocalRecordingId, row]));
    let transferredFocus = null;
    const restoreLocalFocus = () => {
      if (!focusedLocal || document.activeElement === focused && focused.isConnected) return;
      const row = transferredFocus?.isConnected ? transferredFocus
        : allRows().find(row => row.dataset.grafLocalRecordingId === focusedLocal);
      const target = [row?.querySelector(focusedControl), rowPrimaryFocusTarget(row),
        ...allRows().map(rowPrimaryFocusTarget), document.querySelector("[data-list-title]")]
        .find(target => isUsableFocusTarget(target) && !target.matches(':disabled, [aria-disabled="true"]'));
      target?.focus({preventScroll: true});
    };
    for (const item of localRecordingRows) {
      if (!item.meetingId) continue;
      if (selectedMeetingIds.delete(`local:${item.id}`)) selectedMeetingIds.add(item.meetingId);
      if (focusedLocal === item.id) transferredFocus = allRows().find(row => row.dataset.meetingId === item.meetingId);
    }
    applyNativeDeletionOperations(nativeDeletionOperations);
    // A server identity belongs to the server result set, including filters and pagination.
    // Its absence must never turn a retained local copy into a new user recording.
    const localOnly = localRecordingRows.filter((item) => !item.localDeletionPending && !item.meetingId && localRecordingMatches(item));
    const visibleIds = new Set(localOnly.map(item => item.id));
    for (const [id, row] of existingRows) if (!visibleIds.has(id)) row.remove();
    let list = host.querySelector("ol.meeting-list");
    const emptyState = host.querySelector(":scope > .empty-state");
    if (!localOnly.length) {
      if (list?.hasAttribute("data-graf-local-recording-list") && !list.querySelector("[data-meeting-row]")) list.remove();
      if (emptyState) emptyState.hidden = false;
      updateMixedResultCount();
      restoreLocalFocus();
      return;
    }
    if (!list) {
      list = document.createElement("ol");
      list.className = "meeting-list";
      list.setAttribute("role", "list");
      list.setAttribute("aria-label", "Встречи");
      list.dataset.grafLocalRecordingList = "";
      host.append(list);
    }
    if (emptyState) emptyState.hidden = true;
    localOnly.forEach((item) => {
      const row = document.createElement("li");
      row.className = "meeting-row cabinet-row is-local-recording";
      row.dataset.meetingRow = "";
      row.dataset.grafLocalRecordingRow = "";
      row.dataset.grafLocalRecordingId = item.id;
      row.dataset.sortStarted = item.startedAt || "";
      row.dataset.sortUpdated = item.updatedAt || "";
      row.dataset.sortDuration = String(item.durationSeconds);

      const selection = document.createElement("label");
      selection.className = "row-select-hit";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.dataset.meetingSelect = "";
      checkbox.disabled = !item.canDelete;
      checkbox.checked = selectedMeetingIds.has(`local:${item.id}`);
      checkbox.setAttribute("aria-label", `Выбрать запись ${localRecordingDisplayTitle(item)}`);
      selection.append(checkbox);
      const icon = document.createElement("span");
      icon.className = "row-icon";
      icon.dataset.mediaKind = "recording";
      icon.setAttribute("aria-hidden", "true");
      icon.innerHTML = '<svg class="ui-icon" data-icon="audio" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z"></path><path d="M16 9a5 5 0 0 1 0 6"></path><path d="M19.364 18.364a9 9 0 0 0 0-12.728"></path></svg>';
      const content = document.createElement("div");
      content.className = "meeting-content";
      const heading = document.createElement("span");
      heading.className = "meeting-heading";
      const title = document.createElement(item.canOpen ? "button" : "strong");
      title.className = `meeting-title row-title${item.canOpen ? " local-recording-open" : ""}`;
      const displayTitle = localRecordingDisplayTitle(item);
      row.dataset.sortTitle = displayTitle;
      title.textContent = displayTitle;
      if (item.canOpen) {
        title.type = "button";
        title.dataset.meetingOpen = "";
        title.dataset.grafLocalRecordingAction = "open";
        title.dataset.grafLocalRecordingId = item.id;
        title.setAttribute("aria-label", `Открыть локальную запись ${displayTitle}`);
      }
      const duration = document.createElement("span");
      duration.className = "meeting-duration muted";
      const durationLabel = window.GRAFTime.formatDuration;
      duration.textContent = item.showsPartialDuration
        ? `Сохранено ${durationLabel(item.durationSeconds)} из ${durationLabel(item.sessionDurationSeconds)}`
        : durationLabel(item.durationSeconds);
      heading.append(title, duration);
      const meta = document.createElement("span");
      meta.className = "row-meta";
      meta.textContent = item.status;
      content.append(heading, meta);
      const actions = document.createElement("span");
      actions.className = "row-delete-form upload-activity-actions";
      if (item.canSend) {
        const send = document.createElement("button");
        send.className = "button quiet upload-activity-action";
        send.type = "button";
        send.textContent = "Отправить";
        send.dataset.grafLocalRecordingAction = "send";
        send.dataset.grafLocalRecordingId = item.id;
        actions.append(send);
      }
      if (item.canDelete) {
        const remove = document.createElement("button");
        remove.className = "row-delete icon-button";
        remove.type = "button";
        remove.innerHTML = '<svg class="ui-icon" data-icon="trash" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 11v6"></path><path d="M14 11v6"></path><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path><path d="M3 6h18"></path><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>';
        remove.setAttribute("aria-label", `Удалить локальную запись ${displayTitle}`);
        remove.dataset.rowDelete = "";
        remove.dataset.grafLocalRecordingId = item.id;
        actions.append(remove);
      }
      const time = document.createElement("time");
      time.className = "meeting-date";
      time.id = `graf-local-time-${item.id}`;
      if (item.canOpen) title.setAttribute("aria-describedby", time.id);
      const timeValue = meetingListSort().startsWith("updated") ? item.updatedAt : item.startedAt;
      if (timeValue && Number.isFinite(Date.parse(timeValue))) time.dateTime = timeValue;
      time.textContent = `${timeValue && meetingListSort().startsWith("updated") ? "Обновлено " : ""}${formatMeetingListDate(timeValue)}`;
      row.append(selection, icon, content, actions, time);
      // Compare the complete rendered output, including localized dates and sort
      // context, while ignoring transient selection/focus mutations on the live row.
      const markup = row.outerHTML;
      const existing = existingRows.get(item.id);
      if (existing && localRecordingMarkup.get(existing) === markup) return;
      localRecordingMarkup.set(row, markup);
      if (existing?.isConnected) existing.replaceWith(row);
      else list.append(row);
    });
    sortMeetingRows(list);
    updateMixedResultCount();
    restoreLocalFocus();
  };
  let nativeDeletionOperations = [];
  const nativeDeletionReplies = new Map();
  const recordingRowIdentity = (row) => row.dataset.meetingId || `local:${row.dataset.grafLocalRecordingId}`;
  const applyNativeDeletionOperations = (operations) => {
    for (const operation of operations) {
      if (operation.phase === "rejected") continue;
      const id = operation.target?.meeting?._0 || operation.receipt?.meeting_id;
      if (!id) continue;
      revokeManualUploadMeeting(id);
      const detail = document.querySelector("main[data-meeting-id]");
      if (detail?.dataset.meetingId === id) renderMeetingDetailRecovery(detail, operation.phase === "accepted" || operation.phase === "verified" ? "deleted" : "deleting");
      for (const row of allRows().filter(row => row.dataset.meetingId === id)) {
        selectedMeetingIds.delete(recordingRowIdentity(row));
        if (["accepted", "verified"].includes(operation.phase)) {
          row.remove();
        } else {
          row.querySelectorAll("button, input").forEach(control => { control.disabled = true; });
          row.querySelectorAll("a").forEach(link => { link.removeAttribute("href"); link.setAttribute("aria-disabled", "true"); });
          const status = row.querySelector(".row-meta");
          if (status) status.textContent = "Удаление ожидает подтверждения";
        }
      }
    }
  };
  const renderNativeDeletionStatus = (operations) => {
    let details = document.querySelector("[data-native-deletion-status]");
    const localPending = localRecordingRows.filter(item => item.localDeletionPending);
    if (!operations.length && !localPending.length) { details?.remove(); return; }
    if (!details) {
      details = document.createElement("details");
      details.dataset.nativeDeletionStatus = "";
      details.className = "cabinet-fragment";
      const summary = document.createElement("summary");
      summary.textContent = "Удаления";
      details.append(summary, document.createElement("ul"));
      document.querySelector("#meeting-list-region")?.after(details);
    }
    const list = details.querySelector("ul");
    list.replaceChildren();
    for (const item of localPending) {
      const row = document.createElement("li");
      row.textContent = `${localRecordingDisplayTitle(item)}: очистка файлов на этом Mac ещё не завершена. Повторим попытку автоматически.`;
      list.append(row);
    }
    for (const operation of operations.slice(-100).reverse()) {
      const row = document.createElement("li");
      const labels = {queued:"Удаление ожидает подключения", sending:"Удаляем…", resolving:"Проверяем, принято ли удаление",
        accepted:"Запись удалена из списка. Очистка проверяется отдельно.", verified:"Данные этой записи очищены на этом Mac", rejected:"Нет права удалить запись"};
      const waiting = {connection:"Ожидаем подключения для подтверждения удаления", authentication:"Войдите в исходный аккаунт для продолжения удаления",
        rateLimit:"Сервер попросил подождать. Повторим запрос автоматически", serverUpdate:"Для завершения удаления требуется обновление сервера",
        localCleanup:"Запись удалена из списка. Не удалось очистить файлы на этом Mac; повторим попытку"};
      row.textContent = waiting[operation.waitReason] || labels[operation.phase] || "Состояние удаления неизвестно";
      const meetingId = operation.receipt?.meeting_id;
      if (typeof meetingId === "string" && /^[0-9a-f-]{36}$/i.test(meetingId)) {
        const report = document.createElement("a");
        report.href = `/desktop/meetings/${meetingId}/deletion-report`;
        report.textContent = " Состояние удаления";
        row.append(report);
      }
      list.append(row);
    }
  };
  window.GRAFLocalRecordings = {
    deletionCompleted(requestId, result) {
      nativeDeletionReplies.get(requestId)?.(result);
      nativeDeletionReplies.delete(requestId);
    },
    update(rows, operations = [], recoveryRequired = false) {
      let recovery = document.querySelector("[data-local-account-recovery]");
      if (!recoveryRequired) recovery?.remove();
      else if (!recovery) {
        recovery = document.createElement("p");
        recovery.dataset.localAccountRecovery = "";
        recovery.setAttribute("role", "status");
        recovery.textContent = "Некоторые локальные записи скрыты: их аккаунт не подтверждён. Войдите в исходный аккаунт и дождитесь подключения. Если записи не появились, используйте диагностику GRAF. Файлы сохранены.";
        document.querySelector("#meeting-list-region")?.after(recovery);
      }
      const rejected = operations.some(operation => operation.phase === "rejected" && nativeDeletionOperations.some(previous => previous.id === operation.id && previous.phase !== "rejected"));
      nativeDeletionOperations = Array.isArray(operations) ? operations : [];
      localRecordingRows = Array.isArray(rows) ? rows : [];
      renderLocalRecordingRows();
      applyNativeDeletionOperations(nativeDeletionOperations);
      renderNativeDeletionStatus(nativeDeletionOperations);
      updateMixedResultCount();
      reconcileMeetingSelection();
      if (rejected) requestMeetingListRefresh();
    },
  };
  const requestNativeDeletion = (rows) => new Promise((resolve) => {
    const requestId = crypto.randomUUID();
    const timer = setTimeout(() => {
      nativeDeletionReplies.delete(requestId);
      resolve({unknown: true});
    }, 35000);
    nativeDeletionReplies.set(requestId, (result) => { clearTimeout(timer); resolve(result); });
    window.webkit.messageHandlers.grafLocalRecording.postMessage({
      action: "deleteSelection", version: 1, requestId,
      localIds: rows.filter(row => row.hasAttribute("data-graf-local-recording-row")).map(row => row.dataset.grafLocalRecordingId),
      meetingIds: rows.filter(row => !row.hasAttribute("data-graf-local-recording-row")).map(row => row.dataset.meetingId),
    });
  });
  const rowPrimaryFocusTarget = (row) => row?.querySelector("[data-meeting-open], [data-graf-local-recording-action=\"open\"]")
    || row?.querySelector("[data-meeting-select]:not(:disabled)") || null;
  const selectableRows = () => allRows().filter((row) => row.querySelector("[data-meeting-select]:not(:disabled)"));
  const selectedRows = () => selectableRows().filter((row) => row.querySelector("[data-meeting-select]")?.checked);
  const deletingLabel = (value) => `Вы удаляете ${value} ${plural(value, "запись", "записи", "записей")}.`;

  const publishDeletionFeedback = (message, state = "warning") => {
    const target = document.querySelector("#delete-feedback-region");
    if (!target) return;
    const feedback = document.createElement("section");
    feedback.className = "cabinet-fragment cabinet-deletion-feedback";
    feedback.dataset.cabinetFragment = "deletion-feedback";
    feedback.dataset.state = state;
    const copy = document.createElement("p");
    copy.textContent = message;
    feedback.append(copy);
    target.replaceChildren(feedback);
  };

  const announceDeletionResult = (message) => {
    const announcer = document.querySelector("[data-meeting-result-announcer]");
    if (!announcer) return;
    announcer.textContent = "";
    window.requestAnimationFrame(() => {
      if (announcer.isConnected) announcer.textContent = message;
    });
  };

  const pruneUploadProgressTracking = () => {
    const cutoff = Date.now() - uploadProgressTrackingTtlMs;
    announcedUploadProgressMetadata.forEach((metadata, meetingId) => {
      if (Number.isFinite(metadata?.lastSeenAt) && metadata.lastSeenAt >= cutoff) return;
      announcedUploadProgressMetadata.delete(meetingId);
      announcedUploadProgressBuckets.delete(meetingId);
    });
  };

  const scheduleUploadProgressTrackingPrune = () => {
    if (uploadProgressTrackingPruneTimer !== null) return;
    uploadProgressTrackingPruneTimer = globalThis.setTimeout(() => {
      uploadProgressTrackingPruneTimer = null;
      pruneUploadProgressTracking();
      if (announcedUploadProgressMetadata.size) scheduleUploadProgressTrackingPrune();
    }, uploadProgressTrackingTtlMs);
  };

  const rememberUploadProgressMetadata = (meetingId, title) => {
    announcedUploadProgressMetadata.set(meetingId, { title, lastSeenAt: Date.now() });
    scheduleUploadProgressTrackingPrune();
  };

  const announceUploadProgress = () => {
    pruneUploadProgressTracking();
    const announcer = document.querySelector("[data-upload-progress-announcer]");
    if (!announcer) return;
    const rows = allRows();
    const rowsByMeetingId = new Map(rows.map((row) => [row.dataset.meetingId || "", row]));
    const activeMeetingIds = new Set();
    const messages = [];
    rows.forEach((row) => {
      const status = row.querySelector("[data-upload-progress-active][data-upload-progress-percent]");
      const compactStatus = row.querySelector(".meeting-status[data-status-kind]");
      const meetingId = row.dataset.meetingId || "";
      const percent = Number.parseInt(status?.dataset.uploadProgressPercent || "", 10);
      if (!meetingId) return;
      if (!status || !Number.isFinite(percent)) {
        if (compactStatus?.dataset.statusKind === "uploading") {
          activeMeetingIds.add(meetingId);
          const title = row.querySelector(".row-title")?.textContent?.trim()
            || announcedUploadProgressMetadata.get(meetingId)?.title
            || "Встреча";
          rememberUploadProgressMetadata(meetingId, title);
          const previousState = announcedUploadProgressBuckets.get(meetingId);
          if (Number.isFinite(previousState?.bucket)) {
            messages.push(`${title}: ${compactStatus.textContent.trim()}`);
          }
          announcedUploadProgressBuckets.set(meetingId, { bucket: null });
        }
        return;
      }
      activeMeetingIds.add(meetingId);
      const title = row.querySelector(".row-title")?.textContent?.trim()
        || announcedUploadProgressMetadata.get(meetingId)?.title
        || "Встреча";
      rememberUploadProgressMetadata(meetingId, title);
      const bucket = Math.floor(Math.max(0, Math.min(99, percent)) / 10) * 10;
      const previousBucket = announcedUploadProgressBuckets.get(meetingId)?.bucket;
      if (previousBucket !== undefined && previousBucket !== bucket) {
        messages.push(`${title}: ${status.textContent.trim()}`);
      }
      announcedUploadProgressBuckets.set(meetingId, { bucket });
    });
    Array.from(announcedUploadProgressBuckets.keys()).forEach((meetingId) => {
      if (activeMeetingIds.has(meetingId)) return;
      const row = rowsByMeetingId.get(meetingId);
      if (!row) return;
      const status = row?.querySelector(".meeting-status[data-status-kind]");
      if (status?.dataset.statusKind === "uploading") return;
      if (row && status?.textContent?.trim()) {
        const title = row.querySelector(".row-title")?.textContent?.trim()
          || announcedUploadProgressMetadata.get(meetingId)?.title
          || "Встреча";
        messages.push(`${title}: ${status.textContent.trim()}`);
      } else if (row) {
        const title = row.querySelector(".row-title")?.textContent?.trim()
          || announcedUploadProgressMetadata.get(meetingId)?.title
          || "Встреча";
        messages.push(`${title}: Отправка завершена`);
      }
      announcedUploadProgressBuckets.delete(meetingId);
      announcedUploadProgressMetadata.delete(meetingId);
    });
    announcer.textContent = messages.join(". ");
  };

  const announceMeetingResultCount = () => {
    if (!meetingResultCountShouldAnnounce) return;
    meetingResultCountShouldAnnounce = false;
    const announcer = document.querySelector("[data-meeting-result-announcer]");
    const count = document.querySelector("[data-meeting-result-count]")?.textContent?.trim() || "";
    const resultIsComplete = document.querySelector("[data-list-current-content]")
      ?.dataset.meetingResultComplete === "true";
    if (!announcer) return;
    meetingResultCountAnnouncementVersion += 1;
    const announcementVersion = meetingResultCountAnnouncementVersion;
    const message = count || (meetingResultCountHadRefinement
      ? resultIsComplete
        ? "Показаны все встречи"
        : "Показана первая часть встреч без поиска и фильтров"
      : "");
    meetingResultCountHadRefinement = false;
    if (!message) return;
    announcer.textContent = "";
    window.requestAnimationFrame(() => {
      if (
        announcer.isConnected
        && announcementVersion === meetingResultCountAnnouncementVersion
      ) announcer.textContent = message;
    });
  };

  const clearMeetingListAnnouncements = () => {
    meetingResultCountShouldAnnounce = false;
    meetingResultCountHadRefinement = false;
    meetingResultCountAnnouncementVersion += 1;
    document.querySelector("[data-upload-progress-announcer]")?.replaceChildren();
    document.querySelector("[data-upload-activity-announcer]")?.replaceChildren();
    document.querySelector("[data-meeting-result-announcer]")?.replaceChildren();
    announcedUploadProgressBuckets.clear();
    announcedUploadProgressMetadata.clear();
    if (uploadProgressTrackingPruneTimer !== null) {
      globalThis.clearTimeout(uploadProgressTrackingPruneTimer);
      uploadProgressTrackingPruneTimer = null;
    }
  };

  const listInteractionIsActive = () => {
    return Boolean(document.querySelector(
      "[data-delete-dialog][open], [data-meeting-delete-dialog][open], [data-manual-upload-dialog][open], [data-content-export-dialog][open]",
    ));
  };

  const isUsableFocusTarget = (target) => target instanceof HTMLElement &&
    target.isConnected &&
    target.closest("[hidden], [aria-hidden='true']") === null;

  const restoreMeetingActionFocus = (target) => {
    const visibleTarget = isUsableFocusTarget(target)
      ? target
      : document.querySelector('[data-meeting-panel-open="more"]');
    visibleTarget?.focus({ preventScroll: true });
  };

  const restoreListRefreshFocus = (recovery = null, { force = false } = {}) => {
    if (!listRefreshShouldRestoreFocus) return false;
    const active = document.activeElement;
    const userMovedFocus = !force
      && active instanceof HTMLElement
      && active.isConnected
      && active !== document.body
      && active !== document.documentElement
      && active !== listRefreshFocusOrigin;
    if (userMovedFocus) {
      listRefreshFocusMeetingIds = [];
      listRefreshShouldRestoreFocus = false;
      listRefreshFocusOrigin = null;
      return false;
    }
    const focusRow = listRefreshFocusMeetingIds
      .map((meetingId) => allRows().find((row) => recordingRowIdentity(row) === meetingId))
      .find(Boolean);
    let focusTarget = rowPrimaryFocusTarget(focusRow) || document.querySelector("[data-list-title]");
    if (recovery instanceof HTMLElement) {
      focusTarget = recovery.querySelector("[data-list-retry], [data-list-sign-in]") || recovery;
      if (focusTarget === recovery) recovery.tabIndex = -1;
    }
    focusTarget?.focus({ preventScroll: true });
    listRefreshFocusMeetingIds = [];
    listRefreshShouldRestoreFocus = false;
    listRefreshFocusOrigin = null;
    return true;
  };

  const modalFocusTargets = (dialog) => Array.from(dialog.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )).filter((element) => isUsableFocusTarget(element) && !element.matches(":disabled"));

  const trapModalFocus = (dialog, event, { cycleAll = false } = {}) => {
    if (event.key !== "Tab" || !dialog.open) return;
    const elements = modalFocusTargets(dialog);
    if (!elements.length) return;
    const current = elements.indexOf(document.activeElement);
    const next = event.shiftKey
      ? (current <= 0 ? elements.length - 1 : current - 1)
      : (current < 0 || current === elements.length - 1 ? 0 : current + 1);
    if (
      cycleAll ||
      (event.shiftKey && current <= 0) ||
      (!event.shiftKey && (current < 0 || current === elements.length - 1))
    ) {
      event.preventDefault();
      elements[next].focus({ preventScroll: true });
    }
  };

  const updateSelection = () => {
    const list = currentList();
    const toolbar = document.querySelector("[data-selection-toolbar]");
    const countLabel = document.querySelector("[data-selection-count]");
    const selectionToggle = document.querySelector("[data-selection-toggle]");
    const selectionToggleLabel = document.querySelector("[data-selection-toggle-label]");
    if (!list || !toolbar || !countLabel) return;
    const rows = selectedRows();
    const total = selectableRows().length;
    const allSelected = total > 0 && rows.length === total;
    const toolbarOwnedFocus = rows.length === 0
      && document.activeElement instanceof HTMLElement
      && toolbar.contains(document.activeElement);
    if (toolbarOwnedFocus) {
      (rowPrimaryFocusTarget(allRows()[0]) || document.querySelector("[data-list-title]"))
        ?.focus({ preventScroll: true });
    }
    selectedMeetingIds.clear();
    rows.forEach((row) => selectedMeetingIds.add(recordingRowIdentity(row)));
    countLabel.textContent = `Выбрано: ${rows.length}`;
    toolbar.hidden = rows.length === 0;
    if (selectionToggle) {
      selectionToggle.checked = allSelected;
      selectionToggle.indeterminate = rows.length > 0 && !allSelected;
      selectionToggle.setAttribute(
        "aria-label",
        allSelected ? "Снять выбор со всех видимых встреч" : "Выбрать все видимые встречи",
      );
    }
    if (selectionToggleLabel) {
      selectionToggleLabel.textContent = allSelected ? "Снять выбор" : "Выбрать все";
    }
    allRows().forEach((row) => {
      const selected = row.querySelector("[data-meeting-select]")?.checked === true;
      row.classList.toggle("is-selected", selected);
    });
  };

  const reconcileMeetingSelection = () => {
    allRows().forEach((row) => {
      const checkbox = row.querySelector("[data-meeting-select]");
      if (checkbox) checkbox.checked = selectedMeetingIds.has(recordingRowIdentity(row));
    });
    updateSelection();
  };

  const scrubSessionMeetingMetadata = (neutralPath) => {
    const manualUploadWasOpen = scrubManualUploadPrivateState({ authorizationLost: true });
    const deleteDialogWasOpen = document.querySelector("[data-delete-dialog]")?.hasAttribute("open") === true;
    if (
      deleteDialogWasOpen
      || pendingDeleteRows.length
      || deleteReturnFocus
      || deleteReturnMeetingId
      || deleteFocusFallbackIds.length
    ) closeDeleteDialog({ restoreFocus: false });
    clearMeetingListAnnouncements();
    document.querySelector(".upcoming")?.remove();
    document.querySelector("[data-upload-activity-list]")?.replaceChildren();
    document.querySelector("#delete-feedback-region")?.replaceChildren();
    const search = document.querySelector("#meeting-search");
    if (search) search.value = "";
    clearMeetingHistoryCache();
    try {
      sessionStorage.removeItem("htmx-current-path-for-history");
    } catch {
      // The neutral URL still replaces the private query when storage is unavailable.
    }
    neutralizePrivateLocation(neutralPath);
    return manualUploadWasOpen || deleteDialogWasOpen;
  };

  const renderMeetingListRecovery = (kind, requestEvent = null) => {
    const authorizationLost = ["session", "workspace", "access"].includes(kind);
    if (authorizationLost) {
      meetingListRequestGeneration += 1;
      resetProcessingListProjectionState();
    }
    const target = document.querySelector("#meeting-list-region");
    if (!target) return;
    const copy = {
      offline: {
        title: "Нет подключения",
        description: "Запись на Mac продолжает работать.",
        action: "Повторить",
      },
      service: {
        title: "Не удалось загрузить встречи",
        description: "Попробуйте ещё раз.",
        action: "Повторить",
      },
      session: {
        title: "Нужно войти снова",
        description: "Сессия завершилась.",
        action: "Войти",
      },
      workspace: {
        title: "Нужно выбрать пространство",
        description: "Доступ к выбранному пространству больше не подтверждён.",
        action: "Войти и выбрать пространство",
      },
      access: {
        title: "Нет доступа к встречам",
        description: "Обратитесь к владельцу рабочего пространства.",
        action: null,
      },
    }[kind];
    if (!copy) return;
    const recovery = document.createElement("section");
    recovery.className = "list-recovery-state";
    recovery.setAttribute("role", "status");
    recovery.setAttribute("aria-live", "polite");
    const title = document.createElement("strong");
    title.textContent = copy.title;
    const description = document.createElement("span");
    description.textContent = copy.description;
    const listPath = location.pathname.startsWith("/desktop/")
      ? "/desktop/meetings"
      : "/meetings";
    recovery.append(title, description);
    if (copy.action) {
      const requiresSignIn = kind === "session" || kind === "workspace";
      const action = document.createElement(requiresSignIn ? "a" : "button");
      action.className = "button quiet list-recovery-action";
      action.textContent = copy.action;
      if (requiresSignIn) {
        action.href = `/login?next=${encodeURIComponent(listPath)}`;
        action.setAttribute("data-list-sign-in", "");
      } else {
        action.type = "button";
        action.setAttribute("data-list-retry", "");
      }
      recovery.append(action);
    }
    let manualUploadWasOpen = false;
    if (["session", "workspace", "access"].includes(kind)) {
      manualUploadWasOpen = scrubSessionMeetingMetadata(listPath);
      selectedMeetingIds.clear();
    } else {
      clearMeetingListAnnouncements();
    }
    target.removeAttribute("aria-busy");
    let loading = target.querySelector("[data-list-loading-state]");
    let current = target.querySelector("[data-list-current-content]");
    if (!loading || !current) {
      loading = document.createElement("div");
      loading.className = "list-loading-state";
      loading.setAttribute("data-list-loading-state", "");
      loading.setAttribute("role", "status");
      loading.setAttribute("aria-live", "polite");
      loading.hidden = true;
      loading.textContent = "Загружаем встречи…";
      current = document.createElement("div");
      current.setAttribute("data-list-current-content", "");
      target.replaceChildren(loading, current);
    }
    loading.hidden = true;
    current.hidden = false;
    current.replaceChildren(recovery);
    const toolbar = document.querySelector("[data-selection-toolbar]");
    if (toolbar) toolbar.hidden = true;
    if (
      !restoreMeetingListRequestFocus(requestEvent, recovery, { force: authorizationLost })
      && !restoreListRefreshFocus(recovery, { force: authorizationLost })
      && manualUploadWasOpen
    ) {
      const focusTarget = recovery.querySelector("[data-list-retry], [data-list-sign-in]") || recovery;
      if (focusTarget === recovery) recovery.tabIndex = -1;
      focusTarget.focus({ preventScroll: true });
    }
    return recovery;
  };

  const showMeetingListLoading = () => {
    const target = document.querySelector("#meeting-list-region");
    const loading = target?.querySelector("[data-list-loading-state]");
    const current = target?.querySelector("[data-list-current-content]");
    if (!target || !loading || !current) return;
    target.setAttribute("aria-busy", "true");
    loading.hidden = false;
    if (document.activeElement instanceof HTMLElement
      && document.activeElement.closest("[data-list-retry]")) {
      loading.tabIndex = -1;
      loading.focus({ preventScroll: true });
    }
    current.hidden = true;
    const toolbar = document.querySelector("[data-selection-toolbar]");
    if (toolbar) toolbar.hidden = true;
  };

  const requestTargetsMeetingList = (event) => {
    const source = event.detail?.elt || event.target;
    const target = event.detail?.target;
    return target?.id === "meeting-list-region" ||
      (source instanceof Element && Boolean(source.closest(".cabinet-list-controls, [data-list-retry]")));
  };

  const requestIsMeetingListProgressPoll = (event) => {
    const source = event.detail?.requestConfig?.elt || event.detail?.elt || event.target;
    return source instanceof Element && source.matches("[data-upload-progress-poll]");
  };

  const beginAuthoritativeMeetingListRequest = (event) => {
    const request = event.detail?.xhr;
    if (!request || typeof request !== "object" || authoritativeMeetingListRequests.has(request)) return;
    meetingListRequestGeneration += 1;
    resetProcessingListProjectionState();
    activeMeetingListRequests += 1;
    authoritativeMeetingListRequests.add(request);
    authoritativeMeetingListRequestGenerations.set(request, meetingListRequestGeneration);
  };

  const finishAuthoritativeMeetingListRequest = (event) => {
    const request = event.detail?.xhr;
    if (!request || !authoritativeMeetingListRequests.delete(request)) return;
    activeMeetingListRequests = Math.max(0, activeMeetingListRequests - 1);
  };

  const rememberProgressPollGeneration = (event) => {
    const request = event.detail?.xhr;
    if (request && typeof request === "object") {
      progressPollRequestGenerations.set(request, meetingListRequestGeneration);
    }
  };

  const rememberMeetingListRequestFocus = (event) => {
    const request = event.detail?.xhr;
    const active = document.activeElement;
    if (!request || typeof request !== "object") return;
    const previousSnapshot = meetingListRequestFocusRecoveries.get(request);
    if (
      previousSnapshot?.kind === "retry"
      && active instanceof HTMLElement
      && active.closest("[data-list-loading-state]")
    ) return;
    meetingListRequestFocusRecoveries.delete(request);
    if (!(active instanceof HTMLElement)) return;
    const row = active.closest("[data-meeting-row]");
    const meetingId = row?.dataset.meetingId || "";
    if (row && meetingId) {
      let selector = "";
      if (active !== row) {
        selector = [
          "[data-meeting-open]",
          "[data-meeting-select]",
          "[data-row-delete]",
          ".calendar-context-list-action",
        ].find((candidate) => active.matches(candidate)) || "";
        if (!selector) return;
      }
      meetingListRequestFocusRecoveries.set(request, {
        kind: "row",
        meetingIds: [meetingId],
        origin: active,
        selector,
      });
      return;
    }
    if (active.closest("[data-selection-toolbar]")) {
      const selector = [
        "[data-selection-toggle]",
        "[data-clear-selection]",
        "[data-selection-delete]",
      ].find((candidate) => active.matches(candidate)) || "";
      meetingListRequestFocusRecoveries.set(request, {
        kind: "toolbar",
        meetingIds: Array.from(selectedMeetingIds),
        origin: active,
        selector,
      });
      return;
    }
    if (active.closest("[data-list-retry]")) {
      meetingListRequestFocusRecoveries.set(request, {
        kind: "retry",
        meetingIds: [],
        origin: active,
        selector: "",
      });
    }
  };

  const restoreMeetingListRequestFocus = (event, recovery = null, { force = false } = {}) => {
    const request = event?.detail?.xhr;
    if (!request || typeof request !== "object") return false;
    const snapshot = meetingListRequestFocusRecoveries.get(request);
    if (!snapshot) return false;
    meetingListRequestFocusRecoveries.delete(request);
    const active = document.activeElement;
    const retryLoadingOwnsFocus = snapshot.kind === "retry"
      && active instanceof HTMLElement
      && Boolean(active.closest("[data-list-loading-state]"));
    const userMovedFocus = !force
      && isUsableFocusTarget(active)
      && active !== document.body
      && active !== document.documentElement
      && active !== snapshot.origin
      && !retryLoadingOwnsFocus;
    if (userMovedFocus) return false;
    let focusTarget = null;
    if (snapshot.kind === "toolbar") {
      const toolbar = document.querySelector("[data-selection-toolbar]");
      focusTarget = toolbar?.querySelector(
        snapshot.selector || "[data-selection-toggle], [data-clear-selection], [data-selection-delete]",
      );
      if (!isUsableFocusTarget(focusTarget)) focusTarget = null;
    } else {
      const row = snapshot.meetingIds
        .map((meetingId) => allRows().find((candidate) => candidate.dataset.meetingId === meetingId))
        .find(Boolean);
      focusTarget = row
        ? (snapshot.selector ? row.querySelector(snapshot.selector) : null)
          || rowPrimaryFocusTarget(row)
        : null;
    }
    if (recovery instanceof HTMLElement) {
      focusTarget = recovery.querySelector("[data-list-retry], [data-list-sign-in]") || recovery;
      if (focusTarget === recovery) recovery.tabIndex = -1;
    }
    focusTarget ||= document.querySelector("[data-list-title]");
    focusTarget?.focus({ preventScroll: true });
    return Boolean(focusTarget);
  };

  const progressPollIsStale = (event) => {
    const request = event.detail?.xhr;
    const startedAt = request && typeof request === "object"
      ? progressPollRequestGenerations.get(request)
      : undefined;
    return activeMeetingListRequests > 0
      || (startedAt !== undefined && startedAt !== meetingListRequestGeneration);
  };

  const authoritativeMeetingListRequestIsStale = (event) => {
    const request = event.detail?.xhr;
    const startedAt = request && typeof request === "object"
      ? authoritativeMeetingListRequestGenerations.get(request)
      : undefined;
    return startedAt !== undefined && startedAt !== meetingListRequestGeneration;
  };

  const authorizationRecoveryKind = (
    status,
    recoveryHeader = "",
    problemCode = "",
    unknownForbiddenMeansAccess = false,
  ) => {
    if (status === 401) return "session";
    if (status !== 403) return "";
    if (recoveryHeader === "reselect-space") return "workspace";
    if (problemCode === "auth_session_invalid") return "session";
    if (
      problemCode === "workspace_scope_denied"
      && (location.pathname.startsWith("/desktop/") || document.body?.dataset?.surfaceMode === "desktop_embedded")
    ) return "workspace";
    if (unknownForbiddenMeansAccess || accessLossProblemCodes.has(problemCode)) return "access";
    return "";
  };

  const responseProblemCode = async (response) => {
    try {
      const payload = await response.clone().json();
      return typeof payload.code === "string" ? payload.code : "";
    } catch {
      return "";
    }
  };

  const xhrProblemCode = (xhr) => {
    try {
      const payload = JSON.parse(xhr?.responseText || "{}");
      return typeof payload.code === "string" ? payload.code : "";
    } catch {
      return "";
    }
  };

  const isShareRequest = (source, target) => (
    (source instanceof Element && source.closest("[data-share-dialog-open]"))
    || (target instanceof Element && (
      target.id === "meeting-share-host" || target.closest("#meeting-share-host, [data-share-dialog]")
    ))
  );

  const meetingListAuthorizationRecoveryKind = (event) => {
    const xhr = event.detail?.xhr;
    const status = Number(xhr?.status || 0);
    if (status !== 401 && status !== 403) return "";
    return authorizationRecoveryKind(
      status,
      xhr?.getResponseHeader?.("X-GRAF-Cabinet-Recovery") || "",
      status === 403 ? xhrProblemCode(xhr) : "",
      true,
    );
  };

  const handleMeetingListRequestError = (event) => {
    if (!requestTargetsMeetingList(event)) return;
    const authorizationRecovery = meetingListAuthorizationRecoveryKind(event);
    const ignored = requestIsMeetingListProgressPoll(event)
      ? progressPollIsStale(event) || listInteractionIsActive()
      : authoritativeMeetingListRequestIsStale(event);
    finishAuthoritativeMeetingListRequest(event);
    if (authorizationRecovery) {
      const request = event.detail?.xhr;
      if (request && handledMeetingListAuthorizationRequests.has(request)) return;
      if (request && typeof request === "object") handledMeetingListAuthorizationRequests.add(request);
      rememberMeetingListRequestFocus(event);
      renderMeetingListRecovery(authorizationRecovery, event);
      return;
    }
    if (ignored) return;
    rememberMeetingListRequestFocus(event);
    const xhr = event.detail?.xhr;
    const status = Number(xhr?.status || 0);
    if (status >= 400 && status < 500 && status !== 401 && status !== 403) {
      meetingResultCountShouldAnnounce = false;
      meetingResultCountHadRefinement = false;
      const target = document.querySelector("#meeting-list-region");
      target?.removeAttribute("aria-busy");
      const loading = target?.querySelector("[data-list-loading-state]");
      const current = target?.querySelector("[data-list-current-content]");
      if (loading) loading.hidden = true;
      if (current) current.hidden = false;
      restoreMeetingListRequestFocus(event, current?.querySelector(".list-recovery-state"));
      restoreListRefreshFocus();
      return;
    }
    const kind = navigator.onLine ? "service" : "offline";
    renderMeetingListRecovery(kind, event);
  };

  const observeDetachedMeetingListRequest = (event) => {
    const request = event.detail?.xhr;
    const source = event.detail?.elt || event.target;
    if (
      !request
      || typeof request !== "object"
      || typeof request.addEventListener !== "function"
      || !(source instanceof Element)
      || observedDetachedMeetingListRequests.has(request)
    ) return;
    observedDetachedMeetingListRequests.add(request);
    request.addEventListener("readystatechange", () => {
      if (
        request.readyState !== 4
        || ![401, 403].includes(Number(request.status))
        || source.isConnected !== false
      ) return;
      handleMeetingListRequestError(event);
    });
  };

  const captureDeletionFocusFallback = (rows) => {
    const orderedRows = allRows();
    const deletingIds = new Set(rows.map(recordingRowIdentity));
    const anchorRow = orderedRows.find((row) => recordingRowIdentity(row) === deleteReturnMeetingId)
      || rows[0];
    const anchorIndex = orderedRows.indexOf(anchorRow);
    const nextRow = orderedRows.slice(anchorIndex + 1).find(
      (row) => !deletingIds.has(recordingRowIdentity(row)),
    );
    const previousRow = orderedRows.slice(0, Math.max(anchorIndex, 0)).reverse().find(
      (row) => !deletingIds.has(recordingRowIdentity(row)),
    );
    deleteFocusFallbackIds = [nextRow, previousRow].filter(Boolean).map(recordingRowIdentity);
  };

  const openDeleteDialog = (rows) => {
    const dialog = document.querySelector("[data-delete-dialog]");
    if (!dialog) return;
    const title = dialog.querySelector("[data-delete-title]");
    const count = dialog.querySelector("[data-delete-count]");
    const error = dialog.querySelector("[data-delete-error]");
    deleteReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    deleteReturnMeetingId = deleteReturnFocus?.closest("[data-meeting-row]")
      ? recordingRowIdentity(deleteReturnFocus.closest("[data-meeting-row]")) : "";
    pendingDeleteRows = rows.filter(Boolean);
    if (!pendingDeleteRows.length) return;
    captureDeletionFocusFallback(pendingDeleteRows);
    document.querySelector("#delete-feedback-region")?.replaceChildren();
    if (error) error.hidden = true;
    if (title) title.textContent = pendingDeleteRows.length === 1 ? dialog.dataset.titleOne : dialog.dataset.titleMany;
    if (count) {
      const localCount = pendingDeleteRows.filter(row => row.hasAttribute("data-graf-local-recording-row")
        && localRecordingRows.some(item => item.id === row.dataset.grafLocalRecordingId && item.deletionIsLocalOnly === true)).length;
      count.textContent = deletingLabel(pendingDeleteRows.length)
        + (localCount ? ` Только на этом Mac: ${localCount}.`
          + (localCount === pendingDeleteRows.length ? " Эти записи ещё не отправлялись на сервер." : "") : "")
        + (localCount < pendingDeleteRows.length ? ` На сервере или ожидают его подтверждения: ${pendingDeleteRows.length - localCount}.` : "");
    }
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    dialog.querySelector("[data-delete-cancel]")?.focus({ preventScroll: true });
  };

  const closeDeleteDialog = ({ restoreFocus = true } = {}) => {
    const dialog = document.querySelector("[data-delete-dialog]");
    pendingDeleteRows = [];
    if (!dialog) return;
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
    const currentReturnRow = allRows().find((row) => recordingRowIdentity(row) === deleteReturnMeetingId);
    const rowDeleteControl = deleteReturnFocus?.matches("[data-meeting-select]")
      ? currentReturnRow?.querySelector("[data-meeting-select]")
      : currentReturnRow?.querySelector("[data-row-delete]") || rowPrimaryFocusTarget(currentReturnRow);
    const fallbackRow = deleteFocusFallbackIds
      .map((meetingId) => allRows().find((row) => recordingRowIdentity(row) === meetingId))
      .find(Boolean);
    const fallbackControl = rowPrimaryFocusTarget(fallbackRow);
    const returnControl = isUsableFocusTarget(deleteReturnFocus)
      ? deleteReturnFocus
      : isUsableFocusTarget(rowDeleteControl) ? rowDeleteControl : null;
    if (restoreFocus && returnControl) {
      returnControl.focus({ preventScroll: true });
    } else if (restoreFocus && fallbackControl) {
      fallbackControl.focus({ preventScroll: true });
    } else if (restoreFocus) {
      document.querySelector("[data-list-title]")?.focus({ preventScroll: true });
    }
    deleteReturnFocus = null;
    deleteReturnMeetingId = "";
    deleteFocusFallbackIds = [];
  };

  const submitDeletionForm = async (form) => {
    const headers = {
      "HX-Request": "true"
    };
    if (csrfToken) headers["X-CSRF-Token"] = csrfToken;
    const response = await fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      credentials: "same-origin",
      headers
    });
    const problemCode = [403, 404].includes(response.status)
      ? await responseProblemCode(response)
      : "";
    if (response.status === 404 && problemCode === "meeting_not_found") return "missing";
    const recoveryKind = authorizationRecoveryKind(
      response.status,
      response.headers.get("X-GRAF-Cabinet-Recovery") || "",
      problemCode,
    );
    if (recoveryKind) return recoveryKind;
    if (!response.ok) throw new Error("deletion_request_failed");
    return "";
  };

  const requestMeetingListRefresh = ({ focusMeetingIds = [], restoreFocus = false } = {}) => {
    const form = document.querySelector(".cabinet-list-controls");
    if (!(form instanceof HTMLFormElement)) return false;
    listRefreshFocusMeetingIds = focusMeetingIds.filter(Boolean);
    listRefreshShouldRestoreFocus = restoreFocus;
    listRefreshFocusOrigin = restoreFocus && document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    form.requestSubmit();
    return true;
  };

  const syncMeetingListRefinementState = (form) => {
    const status = form?.querySelector("#meeting-status");
    const access = form?.querySelector("#meeting-access");
    const search = form?.querySelector("#meeting-search");
    const sort = form?.querySelector("#meeting-sort");
    const filterDisclosure = form?.querySelector("[data-filter-disclosure]");
    const reset = form?.querySelector("[data-filter-reset]");
    const activeFilterCount = Number(Boolean(status?.value)) + Number(Boolean(access?.value));
    filterDisclosure?.classList.toggle("is-active", activeFilterCount > 0);
    const filterSummary = filterDisclosure?.querySelector("summary");
    const visibleFilterLabel = filterSummary?.querySelector(".cabinet-control-label");
    const filterLabel = activeFilterCount > 0 ? `Фильтры: ${activeFilterCount}` : "Фильтры";
    if (filterSummary) filterSummary.setAttribute("aria-label", filterLabel);
    if (visibleFilterLabel) visibleFilterLabel.textContent = filterLabel;
    if (reset) reset.hidden = !(search?.value.trim() || activeFilterCount > 0);
    const sortLabel = sort?.selectedOptions[0]?.textContent?.trim();
    if (sortLabel) {
      const visibleSortLabel = form?.querySelector("[data-sort-disclosure] .cabinet-control-label");
      if (visibleSortLabel) visibleSortLabel.textContent = sortLabel;
      form?.querySelector("[data-sort-disclosure] > summary")
        ?.setAttribute("aria-label", `Сортировка: ${sortLabel}`);
    }
  };

  const initMeetingList = () => {
    if (!currentList() || document.body.dataset.cabinetMeetingListReady === "true") {
      updateSelection();
      return;
    }
    document.body.dataset.cabinetMeetingListReady = "true";
    const deleteDialog = document.querySelector("[data-delete-dialog]");
    deleteDialog?.addEventListener("cancel", (event) => {
      event.preventDefault();
      closeDeleteDialog();
    });
    document.body.addEventListener("htmx:beforeRequest", (event) => {
      const isProgressPoll = requestIsMeetingListProgressPoll(event);
      if (isProgressPoll) {
        if (activeMeetingListRequests > 0 || listInteractionIsActive()) {
          event.preventDefault();
          return;
        }
        observeDetachedMeetingListRequest(event);
        rememberProgressPollGeneration(event);
        rememberMeetingListRequestFocus(event);
        return;
      }
      if (requestTargetsMeetingList(event)) {
        beginAuthoritativeMeetingListRequest(event);
        observeDetachedMeetingListRequest(event);
        rememberMeetingListRequestFocus(event);
        const triggeringEvent = event.detail?.requestConfig?.triggeringEvent;
        const triggeringTarget = triggeringEvent?.target;
        const refinementSelector = "#meeting-search, #meeting-status, #meeting-access, [data-filter-reset]";
        const requestShouldAnnounce = (
          triggeringTarget instanceof Element
          && Boolean(triggeringTarget.closest(refinementSelector))
        ) || (
          triggeringEvent?.type === "submit"
          && document.activeElement instanceof Element
          && Boolean(document.activeElement.closest(refinementSelector))
        );
        if (requestShouldAnnounce) {
          meetingResultCountShouldAnnounce = true;
          meetingResultCountHadRefinement ||= Boolean(
            document.querySelector("[data-meeting-result-count]"),
          );
        }
        showMeetingListLoading();
      }
    });
    document.body.addEventListener("htmx:beforeSwap", (event) => {
      if (!requestTargetsMeetingList(event)) return;
      if (meetingListAuthorizationRecoveryKind(event)) return;
      const staleProgressPoll = requestIsMeetingListProgressPoll(event)
        && (progressPollIsStale(event) || listInteractionIsActive());
      const staleAuthoritativeRequest = !requestIsMeetingListProgressPoll(event)
        && authoritativeMeetingListRequestIsStale(event);
      if (staleProgressPoll || staleAuthoritativeRequest) {
        event.preventDefault();
        if (event.detail) event.detail.shouldSwap = false;
        return;
      }
      meetingListRequestGeneration += 1;
      resetProcessingListProjectionState({
        preserveSnapshots: requestIsMeetingListProgressPoll(event),
      });
      rememberMeetingListRequestFocus(event);
    });
    document.body.addEventListener("htmx:afterRequest", finishAuthoritativeMeetingListRequest);
    document.body.addEventListener("htmx:sendError", handleMeetingListRequestError);
    document.body.addEventListener("htmx:timeout", handleMeetingListRequestError);
    document.body.addEventListener("htmx:responseError", handleMeetingListRequestError);
    document.body.addEventListener("change", (event) => {
      if (event.target.closest("[data-meeting-select]")) updateSelection();
    });
    document.body.addEventListener("click", async (event) => {
      const reset = event.target.closest("[data-filter-reset]");
      if (reset) {
        event.preventDefault();
        const form = reset.closest("form") || document.querySelector(".cabinet-list-controls");
        if (!(form instanceof HTMLFormElement)) return;
        const search = form.querySelector("#meeting-search");
        const status = form.querySelector("#meeting-status");
        const access = form.querySelector("#meeting-access");
        if (search) search.value = "";
        if (status) status.value = "";
        if (access) access.value = "";
        syncMeetingListRefinementState(form);
        requestMeetingListRefresh({ restoreFocus: true });
        return;
      }
      if (event.target.closest("[data-list-retry]")) {
        const form = document.querySelector(".cabinet-list-controls");
        if (form instanceof HTMLFormElement) {
          form.requestSubmit();
        }
        return;
      }
      const deleteButton = event.target.closest("[data-row-delete]");
      if (deleteButton) {
        openDeleteDialog([deleteButton.closest("[data-meeting-row]")]);
        return;
      }
      if (event.target.closest("[data-selection-delete]")) {
        openDeleteDialog(selectedRows());
        return;
      }
      if (event.target.closest("[data-clear-selection]")) {
        const returnRow = selectedRows()[0];
        allRows().forEach((row) => {
          const checkbox = row.querySelector("[data-meeting-select]");
          if (checkbox) checkbox.checked = false;
        });
        updateSelection();
        ((returnRow?.isConnected ? rowPrimaryFocusTarget(returnRow) : null)
          || document.querySelector("[data-list-title]"))?.focus({ preventScroll: true });
        return;
      }
      if (event.target.closest("[data-delete-cancel]")) {
        closeDeleteDialog();
        return;
      }
      const selectionToggle = event.target.closest("[data-selection-toggle]");
      if (selectionToggle) {
        const rows = selectableRows();
        const shouldSelectAll = selectedRows().length !== rows.length;
        rows.forEach((row) => {
          const checkbox = row.querySelector("[data-meeting-select]");
          if (checkbox) checkbox.checked = shouldSelectAll;
        });
        updateSelection();
        if (!shouldSelectAll) {
          (rowPrimaryFocusTarget(rows[0]) || document.querySelector("[data-list-title]"))
            ?.focus({ preventScroll: true });
        }
        return;
      }
      const confirm = event.target.closest("[data-delete-confirm]");
      if (confirm) {
        if (!pendingDeleteRows.length) return;
        const dialog = document.querySelector("[data-delete-dialog]");
        const error = dialog?.querySelector("[data-delete-error]");
        if (error) error.hidden = true;
        document.querySelector("#delete-feedback-region")?.replaceChildren();
        confirm.disabled = true;
        confirm.textContent = "Удаляем…";
        if (pendingDeleteRows.some(row => row.hasAttribute("data-graf-local-recording-row")) &&
            !(window.GRAFRecordingDeletionBridgeVersion === 1 && window.webkit?.messageHandlers?.grafLocalRecording)) {
          confirm.disabled = false;
          confirm.textContent = "Удалить";
          if (error) { error.textContent = "Для удаления локальных записей обновите приложение GRAF."; error.hidden = false; }
          return;
        }
        if (window.GRAFRecordingDeletionBridgeVersion === 1 && window.webkit?.messageHandlers?.grafLocalRecording) {
          const selection = [...pendingDeleteRows];
          if (selection.length > 100) {
            confirm.disabled = false;
            confirm.textContent = "Удалить";
            if (error) { error.textContent = "Выберите не более 100 записей."; error.hidden = false; }
            return;
          }
          const result = await requestNativeDeletion(selection);
          confirm.disabled = false;
          confirm.textContent = "Удалить";
          closeDeleteDialog();
          if (result.saved) {
            const message = `Удалено из списка: ${result.accepted}. Ожидают подтверждения: ${result.pending}. Отклонено: ${result.rejected}.`;
            announceDeletionResult(message);
            if (result.pending || result.rejected) publishDeletionFeedback(message + " Состояние очистки доступно в разделе «Удаления».", "warning");
            if (result.accepted === selection.length) {
              selection.forEach(row => { selectedMeetingIds.delete(recordingRowIdentity(row)); row.remove(); });
            }
            updateMixedResultCount();
            if (!document.activeElement || document.activeElement === document.body) {
              (rowPrimaryFocusTarget(allRows()[0]) || document.querySelector("[data-list-title]"))?.focus({preventScroll: true});
            }
            requestMeetingListRefresh({ restoreFocus: true });
          } else {
            publishDeletionFeedback(result.unknown
              ? "Ответ приложения пока не получен. Проверьте раздел «Удаления» перед повторной попыткой."
              : "Не удалось сохранить запрос удаления. Повторите попытку.", "error");
          }
          updateSelection();
          return;
        }
        const failedRows = [];
        let deletedCount = 0;
        let missingCount = 0;
        for (const row of pendingDeleteRows) {
          const form = row.querySelector("[data-row-delete-form]");
          if (!form) {
            failedRows.push(row);
            continue;
          }
          try {
            const deletionResult = await submitDeletionForm(form);
            if (deletionResult === "missing") {
              selectedMeetingIds.delete(row.dataset.meetingId);
              revokeManualUploadMeeting(row.dataset.meetingId);
              row.replaceChildren();
              row.removeAttribute("data-meeting-id");
              row.remove();
              missingCount += 1;
              continue;
            }
            if (deletionResult) {
              closeDeleteDialog({ restoreFocus: false });
              renderMeetingListRecovery(deletionResult);
              return;
            }
            const checkbox = row.querySelector("[data-meeting-select]");
            if (checkbox) checkbox.checked = false;
            revokeManualUploadMeeting(row.dataset.meetingId);
            row.remove();
            deletedCount += 1;
          } catch (_err) {
            failedRows.push(row);
          }
        }
        confirm.disabled = false;
        confirm.textContent = "Удалить";
        updateSelection();
        if (failedRows.length && error) {
          const failures = failedRows.length;
          const failureMessage = `Не удалось удалить ${failures} ${plural(failures, "запись", "записи", "записей")}. Попробуйте ещё раз.`;
          error.textContent = failureMessage;
          error.hidden = false;
          pendingDeleteRows = failedRows;
          confirm.textContent = "Повторить";
          publishDeletionFeedback(failureMessage, "error");
          if (deletedCount + missingCount > 0) requestMeetingListRefresh();
          return;
        }
        if (deletedCount > 0) {
          const message = deletedCount === 1
            ? "Запись удалена из списка."
            : `Удалено ${deletedCount} ${plural(deletedCount, "запись", "записи", "записей")} из списка.`;
          announceDeletionResult(message);
        } else if (missingCount > 0) {
          announceDeletionResult("Встреча больше недоступна. Список обновлён.");
        }
        const refreshFocusMeetingIds = [...deleteFocusFallbackIds];
        closeDeleteDialog({ restoreFocus: false });
        if (deletedCount + missingCount > 0 && requestMeetingListRefresh({
          focusMeetingIds: refreshFocusMeetingIds,
          restoreFocus: true,
        })) return;
        document.querySelector("[data-list-title]")?.focus({ preventScroll: true });
        return;
      }
      const row = event.target.closest("[data-meeting-row]");
      if (!row || event.target.closest("a,button,input,.row-select-hit")) return;
      const primaryLink = row.querySelector("[data-meeting-open]");
      primaryLink?.click();
    });
    reconcileMeetingSelection();
  };

  const initListDisclosures = () => {
    const form = document.querySelector(".cabinet-list-controls");
    if (form && form.dataset.refinementReady !== "true") {
      form.dataset.refinementReady = "true";
      const syncRefinementState = () => syncMeetingListRefinementState(form);
      form.addEventListener("input", syncRefinementState);
      form.addEventListener("change", syncRefinementState);
      syncRefinementState();
    }
    document.querySelectorAll("[data-filter-disclosure], [data-sort-disclosure]").forEach((details) => {
      if (details.dataset.disclosureReady === "true") return;
      details.dataset.disclosureReady = "true";
      details.addEventListener("toggle", () => {
        if (!details.open) return;
        document.querySelectorAll("[data-filter-disclosure], [data-sort-disclosure]").forEach((peer) => {
          if (peer !== details) peer.open = false;
        });
      });
    });
    if (document.body.dataset.listDisclosureDismissReady !== "true") {
      document.body.dataset.listDisclosureDismissReady = "true";
      document.body.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        const details = event.target instanceof Element
          ? event.target.closest("[data-filter-disclosure], [data-sort-disclosure]")
          : null;
        const openDisclosure = details?.open
          ? details
          : document.querySelector("[data-filter-disclosure][open], [data-sort-disclosure][open]");
        if (!openDisclosure) return;
        openDisclosure.open = false;
        openDisclosure.querySelector("summary")?.focus({ preventScroll: true });
      });
      document.body.addEventListener("click", (event) => {
        if (!(event.target instanceof Element)) return;
        if (event.target.closest("[data-filter-disclosure], [data-sort-disclosure]")) return;
        document.querySelectorAll("[data-filter-disclosure][open], [data-sort-disclosure][open]").forEach((details) => {
          details.open = false;
        });
      });
    }
  };

  const initCodeForms = () => {
    document.querySelectorAll("[data-code-form]").forEach((form) => {
      if (form.dataset.codeReady === "true") return;
      form.dataset.codeReady = "true";
      const slots = Array.from(form.querySelectorAll("[data-code-slot]"));
      const hidden = form.querySelector("[data-code-hidden]");
      if (slots.length !== 6 || !hidden) return;
      hidden.disabled = false;
      let submitted = false;
      const sanitize = (value) => String(value || "").replace(/\D/g, "").slice(0, 6);
      const sync = () => {
        hidden.value = slots.map((slot) => slot.value).join("");
      };
      const isComplete = () => slots.every((slot) => /^\d$/.test(slot.value));
      const focusSlot = (index) => slots[Math.max(0, Math.min(index, slots.length - 1))]?.focus();
      const maybeSubmit = () => {
        if (submitted || !isComplete()) return;
        sync();
        submitted = true;
        if (form.requestSubmit) {
          form.requestSubmit();
        } else {
          form.submit();
        }
      };
      const fillFromStart = (value) => {
        const digits = sanitize(value);
        const commit = () => {
          slots.forEach((slot, index) => { slot.value = digits[index] || ""; });
          sync();
          focusSlot(Math.min(digits.length, slots.length - 1));
          maybeSubmit();
        };
        commit();
        window.setTimeout(commit, 0);
      };
      slots.forEach((slot, index) => {
        slot.addEventListener("input", () => {
          const digits = sanitize(slot.value);
          if (digits.length > 1) {
            fillFromStart(digits);
            return;
          }
          const commit = () => {
            slot.value = digits;
            sync();
            if (digits && slots[index + 1]) focusSlot(index + 1);
            maybeSubmit();
          };
          commit();
          window.setTimeout(commit, 0);
        });
        slot.addEventListener("keydown", (event) => {
          if (event.key === "Backspace") {
            event.preventDefault();
            if (slot.value) slot.value = "";
            else if (slots[index - 1]) {
              slots[index - 1].value = "";
              focusSlot(index - 1);
            }
            sync();
            return;
          }
          if (event.key === "Delete") {
            event.preventDefault();
            slot.value = "";
            sync();
            return;
          }
          if (event.key === "ArrowLeft") {
            event.preventDefault();
            focusSlot(index - 1);
          } else if (event.key === "ArrowRight") {
            event.preventDefault();
            focusSlot(index + 1);
          } else if (event.key === "Home") {
            event.preventDefault();
            focusSlot(0);
          } else if (event.key === "End") {
            event.preventDefault();
            focusSlot(slots.length - 1);
          }
        });
        slot.addEventListener("paste", (event) => {
          const pasted = event.clipboardData?.getData("text") || window.clipboardData?.getData("Text") || "";
          const digits = sanitize(pasted);
          if (!digits) return;
          event.preventDefault();
          fillFromStart(digits);
        });
      });
      form.addEventListener("submit", (event) => {
        sync();
        if (!isComplete()) {
          event.preventDefault();
          submitted = false;
          focusSlot(slots.findIndex((slot) => !/^\d$/.test(slot.value)));
          return;
        }
        submitted = true;
      });
      slots[0]?.focus();
    });
  };

  const initOutcomeFocus = () => {
    const outcome = document.querySelector("[data-outcome-focus]:not([data-outcome-focused])");
    if (!outcome) return;
    outcome.dataset.outcomeFocused = "true";
    outcome.focus();
  };

  const initAuthTransition = () => {
    const page = document.querySelector(".auth-page");
    if (!page || page.dataset.authTransitionReady === "true") return;
    page.dataset.authTransitionReady = "true";
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    page.addEventListener("click", (event) => {
      const link = event.target.closest("a[href]");
      if (!link) return;
      if (link.getAttribute("aria-disabled") === "true") return;
      if (link.target || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      event.preventDefault();
      document.body.classList.add("auth-leaving");
      window.setTimeout(() => { window.location.href = url.href; }, 130);
    });
  };

  const activateDetailTab = (name, { updateUrl = true } = {}) => {
    const tabs = Array.from(document.querySelectorAll("[data-detail-tab]"));
    const panels = Array.from(document.querySelectorAll("[data-detail-panel]"));
    tabs.forEach((tab) => {
      const selected = tab.dataset.detailTab === name;
      tab.classList.toggle("active", selected);
      tab.setAttribute("aria-selected", selected ? "true" : "false");
      tab.tabIndex = selected ? 0 : -1;
    });
    panels.forEach((panel) => {
      const selected = panel.dataset.detailPanel === name;
      panel.classList.toggle("active", selected);
      panel.hidden = !selected;
    });
    const controls = document.querySelector("[data-summary-format-controls]");
    if (controls) {
      controls.hidden = name !== "outcomes";
      if (controls.hidden) {
        const popover = controls.querySelector("[data-summary-format-popover]");
        if (popover) {
          if (popover.matches(":popover-open")) popover.hidePopover();
          popover.hidden = true;
        }
        controls.querySelector("[data-summary-format-button]")?.setAttribute("aria-expanded", "false");
        const info = controls.querySelector(".summary-format-info");
        if (info) info.open = false;
      }
    }
    document.querySelector(".detail-page-main")?.dispatchEvent(new Event("detail-tab-change"));
    if (updateUrl && ["outcomes", "recording"].includes(name)) {
      const hash = `#${name}`;
      if (window.location.hash !== hash) {
        window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${hash}`);
      }
    }
  };

  const initDetailTabs = () => {
    const tabs = Array.from(document.querySelectorAll("[data-detail-tab]"));
    const panels = Array.from(document.querySelectorAll("[data-detail-panel]"));
    if (!tabs.length || !panels.length) return;
    tabs.forEach((tab) => {
      if (tab.dataset.detailTabReady === "true") return;
      tab.dataset.detailTabReady = "true";
      tab.addEventListener("click", () => activateDetailTab(tab.dataset.detailTab || "recording"));
      tab.addEventListener("keydown", (event) => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        const current = tabs.indexOf(tab);
        const next = event.key === "Home" ? 0
          : event.key === "End" ? tabs.length - 1
          : (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
        activateDetailTab(tabs[next].dataset.detailTab || "recording");
        tabs[next].focus();
      });
    });
    if (window.location.hash === "#outcomes") activateDetailTab("outcomes", { updateUrl: false });
    if (window.location.hash === "#recording") activateDetailTab("recording", { updateUrl: false });
  };

  const processingOwnsField = (object, field) => (
    object !== null
    && typeof object === "object"
    && Object.prototype.hasOwnProperty.call(object, field)
  );

  const processingNewAttemptAllowed = (projection) => (
    projection?.retry_class === "terminal"
    && projection?.manual_action === "new_attempt"
    && projection?.attempt_in_flight !== true
  );

  const processingClientCommandId = () => {
    const randomId = typeof window.crypto?.randomUUID === "function"
      ? window.crypto.randomUUID()
      : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
    return `processing-check-${randomId}`;
  };

  const processingArtifactVisible = (projection, name) => {
    const artifacts = projection?.artifacts;
    if (processingOwnsField(artifacts, name)) return artifacts[name]?.visible === true;
    return projection?.[`${name}_available`] === true;
  };

  const processingArtifactState = (projection, name, fallback = "processing") => {
    const artifacts = projection?.artifacts;
    if (processingOwnsField(artifacts, name)) return String(artifacts[name]?.state || fallback);
    if (name === "summary") return String(projection?.summary_status || fallback);
    return processingArtifactVisible(projection, name) ? "available" : fallback;
  };

  const processingTimestamp = (value) => {
    if (typeof value !== "string" && !(value instanceof Date)) return null;
    const timestamp = new Date(value).getTime();
    return Number.isFinite(timestamp) ? timestamp : null;
  };

  const processingServerSecondsRemaining = (projection, now = Date.now(), clientServerOffset = 0) => {
    const deadline = processingTimestamp(projection?.next_attempt_at);
    const serverTime = processingTimestamp(projection?.server_time);
    if (deadline === null || serverTime === null) return null;
    const offset = Number.isFinite(clientServerOffset) ? clientServerOffset : 0;
    return Math.max(0, Math.ceil((deadline - (now + offset)) / 1000));
  };

  const processingCountdownDuration = (seconds) => {
    const bounded = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(bounded / 3600);
    const minutes = Math.floor((bounded % 3600) / 60);
    const rest = bounded % 60;
    return hours > 0
      ? `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`
      : `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
  };

  const processingCountdownCopy = (seconds, source, nextAttemptAt = null, replacement = false) => {
    if (replacement && Number.isFinite(seconds) && processingTimestamp(nextAttemptAt) !== null) {
      const time = window.GRAFTime.format(nextAttemptAt, { showZone: true });
      return `GRAF повторит попытку автоматически в ${time} (через ${processingCountdownDuration(seconds)}).`;
    }
    const prefix = source === "server_fallback" ? "Примерно через" : "Следующая проверка через";
    if (!Number.isFinite(seconds) || seconds <= 0) return "Следующая проверка доступна сейчас.";
    if (seconds >= 3600) {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${prefix} ${hours} ч${minutes ? ` ${minutes} мин` : ""}.`;
    }
    if (seconds >= 60) return `${prefix} ${Math.floor(seconds / 60)} мин.`;
    return `${prefix} ${seconds} сек.`;
  };

  const processingSummaryState = (projection) => {
    const artifacts = projection?.artifacts;
    if (processingOwnsField(artifacts, "summary")) {
      return String(artifacts.summary?.state || projection?.summary_status || "");
    }
    return String(projection?.summary_status || "");
  };

  const processingSummaryPending = (state) => [
    "queued",
    "pending",
    "processing",
    "running",
    "generating",
    "submitted",
    "blocked_dependency",
  ].includes(String(state || "").toLowerCase());

  const processingTranscriptReady = (projection) => (
    processingArtifactVisible(projection, "transcript")
    && processingArtifactVisible(projection, "diarization")
  );

  const processingProjectionTerminal = (projection) => {
    const retryClass = String(projection?.retry_class || "none");
    const state = String(projection?.state || "").toLowerCase();
    return retryClass === "terminal"
      || ["failed_terminal", "canceled"].includes(state)
      || (state === "blocked" && retryClass !== "unknown_outcome");
  };
  const processingTerminalFailure = processingProjectionTerminal;

  const processingProjectionMatchesDetail = (detail, projection) => {
    const meetingId = String(detail.dataset.meetingId || "");
    const responseMeetingId = String(projection?.meeting_id || "");
    if (meetingId && responseMeetingId && meetingId !== responseMeetingId) return false;
    const mediaRevisionId = String(detail.dataset.mediaRevisionId || "");
    const responseRevisionId = String(projection?.media_revision_id || "");
    return !mediaRevisionId || !responseRevisionId || mediaRevisionId === responseRevisionId;
  };

  const processingProjectionIsStale = (detail, projection) => {
    const current = processingTimestamp(detail.dataset.processingProjectionUpdatedAt);
    const incoming = processingTimestamp(projection?.updated_at);
    return current !== null && incoming !== null && incoming < current;
  };

  const updateProcessingExportVisibility = (transcriptVisible) => {
    document.querySelectorAll("[data-content-export-form]").forEach((form) => {
      const scope = form.querySelector("[data-export-scope]");
      if (!scope) return;
      ["transcript", "combined"].forEach((scopeName) => {
        const option = scope.querySelector(`option[value="${scopeName}"]`);
        if (!option) return;
        if (!option.dataset.processingServerDisabled) {
          option.dataset.processingServerDisabled = option.disabled ? "true" : "false";
        }
        option.disabled = option.dataset.processingServerDisabled === "true" || !transcriptVisible;
      });
      if (scope.selectedOptions?.[0]?.disabled) {
        const available = Array.from(scope.options).find((option) => !option.disabled);
        if (available) {
          scope.value = available.value;
          scope.dispatchEvent(new Event("change"));
        }
      }
      form.dataset.processingTranscriptVisible = transcriptVisible ? "true" : "false";
      form.dispatchEvent(new Event("export-availability-change"));
    });
  };

  const stopProcessingRecoveryCountdown = () => {
    if (processingRecoveryCountdownTimer !== null) {
      globalThis.clearInterval(processingRecoveryCountdownTimer);
      processingRecoveryCountdownTimer = null;
    }
  };

  const resetProcessingRecoveryCountdown = (detail) => {
    stopProcessingRecoveryCountdown();
    const countdown = detail.querySelector("[data-processing-countdown]");
    if (!countdown) return;
    countdown.hidden = true;
    countdown.textContent = "";
    delete countdown.dataset.seconds;
  };

  const processingServerClockOffset = (detail) => {
    const offset = Number(detail.dataset.processingServerClockOffsetMs);
    return Number.isFinite(offset) ? offset : 0;
  };

  const stopProcessingRecoveryPolling = () => {
    if (processingRecoveryPollTimer !== null) {
      globalThis.clearTimeout(processingRecoveryPollTimer);
      processingRecoveryPollTimer = null;
    }
  };

  const scheduleProcessingStatusRetry = (
    generation = processingRecoveryGeneration,
    delay = 15000,
  ) => {
    stopProcessingRecoveryPolling();
    processingRecoveryPollTimer = window.setTimeout(() => {
      processingRecoveryPollTimer = null;
      if (
        !document.hidden
        && generation === processingRecoveryGeneration
        && processingRecoveryActionRequest === null
      ) {
        void refreshProcessingStatus({ force: true, generation });
      }
    }, delay);
  };

  const announceProcessingChange = (detail, message, signature = message) => {
    const live = detail.querySelector("[data-processing-live]");
    if (!live || !message || detail.dataset.processingAnnouncement === signature) return;
    detail.dataset.processingAnnouncement = signature;
    live.textContent = "";
    window.requestAnimationFrame(() => {
      if (live.isConnected && detail.dataset.processingAnnouncement === signature) {
        live.textContent = message;
      }
    });
  };

  const updateProcessingStage = (detail, name, state, label) => {
    const item = detail.querySelector(`[data-processing-stage-item="${name}"]`);
    if (!item) return;
    item.dataset.stageState = state;
    item.classList.toggle("is-ready", state === "ready");
    item.classList.toggle("is-active", state === "active");
    item.classList.toggle("is-unavailable", state === "unavailable");
    const status = item.querySelector("[data-processing-stage-status]");
    if (status) status.textContent = label;
  };

  const processingSummaryCopy = (state, hasStoredOutput = false, transcriptReady = false) => ({
    available: ["Итоги готовы.", "success"],
    partial: [
      transcriptReady ? "Итоги доступны частично. Расшифровка остаётся доступной." : "Итоги доступны частично.",
      "warning",
    ],
    queued: ["Итоги готовятся отдельно. Расшифровка может быть доступна раньше.", "pending"],
    pending: ["Итоги готовятся отдельно. Расшифровка может быть доступна раньше.", "pending"],
    processing: ["Итоги готовятся отдельно. Расшифровка может быть доступна раньше.", "pending"],
    running: ["Итоги готовятся отдельно. Расшифровка может быть доступна раньше.", "pending"],
    generating: ["Итоги готовятся отдельно. Расшифровка может быть доступна раньше.", "pending"],
    blocked_dependency: ["Подготовка итогов задерживается. Продолжим автоматически.", "pending"],
    submitted: ["Итоги готовятся отдельно. Расшифровка может быть доступна раньше.", "pending"],
    failed: [transcriptReady ? "Не удалось подготовить итоги. Расшифровка сохранена." : "Не удалось подготовить итоги.", "failed"],
    unavailable: [transcriptReady ? "Итоги пока недоступны. Расшифровка сохранена." : "Итоги пока недоступны.", "warning"],
    not_requested: [
      hasStoredOutput
        ? "Сохраненные итоги доступны. Новые итоги ещё не запрошены."
        : transcriptReady
        ? "Итоги ещё не запрошены. Расшифровка остаётся доступной."
        : "Итоги ещё не запрошены.",
      "warning",
    ],
  }[String(state || "").toLowerCase()] || null);

  const processingTerminalReasonCopy = {
    invalid_audio_payload: "Файл записи не является декодируемым аудио или поврежден.",
    mediascribe_validation_failed: "Сервис транскрипции отклонил файл: проверьте формат и повторите обработку.",
    mediascribe_payload_too_large: "Файл записи превышает допустимый размер.",
    mediascribe_auth_failed: "Сервис транскрипции отклонил доступ; повторить можно после проверки настройки сервера.",
    mediascribe_malformed_response: "Сервис транскрипции вернул некорректный ответ. Повторите обработку; если ошибка повторится, обратитесь к оператору.",
  };

  const processingRecoveryCopy = (projection, transcriptReady, replacementPublished = false) => {
    const retryClass = String(projection?.retry_class || "none");
    const reason = String(projection?.reason_code || "").toLowerCase();
    const reasonCopy = processingTerminalReasonCopy[reason] || "";
    const projectionState = String(projection?.state || "").toLowerCase();
    const inFlight = projection?.attempt_in_flight === true;
    const replacementAttemptOrdinal = Number(projection?.attempt_ordinal ?? 0);
    const replacement = Number.isSafeInteger(replacementAttemptOrdinal)
      && replacementAttemptOrdinal > 1
      && (projection?.content_available === true || transcriptReady);
    if (replacement && processingTerminalFailure(projection)) {
      return {
        state: "terminal",
        title: "Не удалось подготовить новую версию",
        copy: "Текущая версия не изменилась.",
        canCheck: false,
        canStartNewAttempt: false,
        canReprocess: true,
        reprocessLabel: "Попробовать снова",
        showRefresh: false,
        showCountdown: false,
      };
    }
    if (replacement && (!replacementPublished || inFlight || projectionState !== "processed")) {
      return {
        state: "active",
        title: "Готовим новую версию",
        copy: "",
        canCheck: false,
        showRefresh: false,
        showCountdown: false,
      };
    }
    if (projection?.manual_action === "retry_preparation") {
      return {
        state: "retryable",
        title: "Подготовка записи временно приостановлена",
        copy: "GRAF повторит подготовку автоматически. Можно запустить попытку раньше — параллельная обработка не создастся.",
        canCheck: !inFlight,
        checkLabel: "Повторить подготовку",
        busyLabel: "Запускаем подготовку…",
        showRefresh: false,
        showCountdown: true,
      };
    }
    if (projection?.manual_action === "upload_another") {
      const storageFull = reason === "storage_capacity_exceeded";
      return {
        state: "terminal",
        title: storageFull ? "Недостаточно места для аудио" : "Не удалось подготовить запись",
        copy: storageFull
          ? "Загрузите запись без сохранения аудио — расшифровка и итоги останутся доступны. Освободить или увеличить хранилище можно позже."
          : reasonCopy
          ? `${reasonCopy} Загрузите другую копию или файл в другом формате.`
          : "Этот файл не удалось обработать. Загрузите другую копию или файл в другом формате.",
        canCheck: false,
        canStartNewAttempt: false,
        canUploadAnother: true,
        uploadWithoutArchive: storageFull,
        showRefresh: false,
      };
    }
    if (projection?.manual_action === "contact_support") {
      const accessFailure = [
        "blocked_config",
        "blocked_unauthorized",
        "mediascribe_auth_failed",
      ].includes(reason);
      return {
        state: "terminal",
        title: accessFailure ? "Сервис расшифровки временно недоступен" : "Нужна помощь с обработкой",
        copy: reasonCopy || (accessFailure
          ? "GRAF не может продолжить из-за настройки доступа к сервису расшифровки. Запись сохранена; вернитесь позже или к списку встреч."
          : "Автоматическое продолжение недоступно. Запись сохранена; обновите статус позже или вернитесь к списку встреч."),
        canCheck: false,
        canStartNewAttempt: false,
        showRefresh: true,
      };
    }
    if (
      reason === "blocked_free_processing_exhausted"
      && projection?.manual_action === "new_attempt"
    ) {
      return {
        state: "terminal",
        title: "Лимит расшифровки исчерпан",
        copy: "Для этой записи не хватило доступного времени расшифровки. После обновления лимита запустите обработку заново.",
        canCheck: false,
        canStartNewAttempt: processingNewAttemptAllowed(projection),
        showRefresh: false,
      };
    }
    if (projectionState === "canceled") {
      return {
        state: "terminal",
        title: "Обработка отменена",
        copy: "Обработка этой записи остановлена. Вернитесь к списку встреч, чтобы продолжить работу.",
        canCheck: false,
        canStartNewAttempt: false,
        showRefresh: false,
      };
    }
    if (projectionState === "blocked" || (projectionState === "failed_terminal" && retryClass !== "terminal")) {
      return {
        state: "terminal",
        title: "Обработка остановлена",
        copy: reasonCopy || "Автоматическое продолжение недоступно. Обновите страницу или вернитесь к списку встреч.",
        canCheck: false,
        canStartNewAttempt: false,
        showRefresh: true,
      };
    }
    if (retryClass === "unknown_outcome") {
      return {
        state: "unknown",
        title: "Проверяем исходную попытку",
        copy: "Не удалось подтвердить отправку, поэтому GRAF проверяет исходную попытку и не создаёт дубликат.",
        canCheck: projection?.manual_action === "check_now" && !inFlight,
        showRefresh: projection?.manual_action !== "check_now",
        showCountdown: projection?.next_attempt_at != null,
      };
    }
    if (retryClass === "terminal") {
      if (reason === "no_recognizable_speech") {
        return {
          state: "terminal",
          title: "Речь не распознана",
          copy: "В записи не найдено распознаваемой речи. Доступные результаты сохранены; при необходимости можно начать обработку заново.",
          canCheck: false,
          canStartNewAttempt: processingNewAttemptAllowed(projection),
          showRefresh: true,
        };
      }
      const canStartNewAttempt = processingNewAttemptAllowed(projection);
      return {
        state: "terminal",
        title: "Обработка завершилась без результата",
        copy: reasonCopy
          ? `${reasonCopy}${canStartNewAttempt ? " Если нужно, начните обработку заново кнопкой ниже." : ""}`
          : canStartNewAttempt
          ? "Доступные результаты сохранены. Если нужно, начните обработку заново кнопкой ниже."
          : "Автоматический перезапуск недоступен. Обновите страницу позже или вернитесь к списку встреч.",
        canCheck: false,
        canStartNewAttempt,
        showRefresh: true,
      };
    }
    if (retryClass === "retryable") {
      if (inFlight) {
        return {
          state: "active",
          title: "Обработка продолжается",
          copy: "GRAF уже проверяет запись. Дождитесь результата или обновите страницу позже.",
          canCheck: false,
          canStartNewAttempt: false,
          showRefresh: false,
          showCountdown: false,
        };
      }
      if (["processing_retry_deadline_exceeded", "mediascribe_poll_limit_exceeded"].includes(reason)) {
        return {
          state: "retryable",
          title: "Результат ещё не подтверждён",
          copy: reasonCopy || "MediaScribe не сообщил об ошибке. Автоматическое ожидание остановлено; проверьте обработку вручную.",
          canCheck: projection?.manual_action === "check_now" && !inFlight,
          canStartNewAttempt: false,
          showRefresh: true,
          showCountdown: false,
        };
      }
      const canCheck = projection?.manual_action === "check_now" && !inFlight;
      if (!canCheck) {
        return {
          state: "terminal",
          title: "Обработка требует внимания",
          copy: "GRAF не может безопасно повторить эту операцию автоматически. Обновите страницу позже или вернитесь к списку встреч.",
          canCheck: false,
          canStartNewAttempt: false,
          showRefresh: true,
          showCountdown: false,
        };
      }
      return {
        state: "retryable",
        title: "Обработка временно приостановлена",
        copy: "Запись сохранена. GRAF попробует проверить её автоматически.",
        canCheck,
        canStartNewAttempt: false,
        showRefresh: projection?.manual_action !== "check_now",
        showCountdown: true,
      };
    }
    if (inFlight) {
      return {
        state: "active",
        title: "Обработка продолжается",
        copy: "GRAF проверяет запись. Спикеры и итог могут появиться по отдельности.",
        canCheck: false,
        showRefresh: false,
      };
    }
    if (transcriptReady) return null;
    if (reason === "no_recognizable_speech") {
      return {
          state: "terminal",
          title: "Речь не распознана",
          copy: "В записи не найдено распознаваемой речи. Доступные результаты сохранены.",
          canCheck: false,
          canStartNewAttempt: processingNewAttemptAllowed(projection),
          showRefresh: true,
        };
    }
    return {
      state: "active",
      title: "Обработка записи",
      copy: "Спикеры ещё определяются. Расшифровка появится после завершения диаризации.",
      canCheck: false,
      canStartNewAttempt: false,
      showRefresh: false,
    };
  };

  const renderProcessingCountdown = (detail, projection) => {
    stopProcessingRecoveryCountdown();
    const countdown = detail.querySelector("[data-processing-countdown]");
    if (!countdown || !["retryable", "unknown_outcome"].includes(projection?.retry_class)) {
      if (countdown) {
        countdown.hidden = true;
        countdown.textContent = "";
        delete countdown.dataset.seconds;
      }
      return null;
    }
    const update = () => {
      const seconds = processingServerSecondsRemaining(
        projection,
        Date.now(),
        processingServerClockOffset(detail),
      );
      if (seconds === null) {
        countdown.hidden = true;
        countdown.textContent = "";
        delete countdown.dataset.seconds;
        return null;
      }
      countdown.hidden = false;
      countdown.textContent = processingCountdownCopy(
        seconds,
        projection?.next_attempt_source,
        projection?.next_attempt_at,
        Number(projection?.attempt_ordinal ?? detail.dataset.processingAttemptOrdinal ?? 0) > 1
          && (
            projection?.content_available === true
            || detail.dataset.processingTranscriptContentReady === "true"
            || detail.dataset.processingTranscriptVisible === "true"
          ),
      );
      countdown.dataset.seconds = String(seconds);
      return seconds;
    };
    const seconds = update();
    if (seconds !== null && seconds > 0) {
      processingRecoveryCountdownTimer = window.setInterval(update, 1000);
    }
    return seconds;
  };

  const scheduleProcessingRecoveryPolling = (detail, projection) => {
    stopProcessingRecoveryPolling();
    if (processingRecoveryActionRequest !== null || processingTerminalFailure(projection)) return;
    const transcriptReady = typeof processingTranscriptReady === "function"
      ? processingTranscriptReady(projection)
      : false;
    const summaryState = processingSummaryState(projection);
    const terminalProjection = processingTerminalFailure(projection);
    const attemptOrdinal = Number(projection?.attempt_ordinal ?? 0);
    const replacementContentPending = Number.isSafeInteger(attemptOrdinal)
      && attemptOrdinal > 1
      && String(projection?.state || "").toLowerCase() === "processed"
      && detail.dataset.processingPublishedAttempt !== String(attemptOrdinal);
    const shouldPoll = !terminalProjection && (
      (typeof processingTranscriptReady === "function" && !transcriptReady)
      || processingSummaryPending(summaryState)
      || summaryState === "not_requested"
      || projection?.retry_class === "retryable" && projection?.next_attempt_at != null
      || projection?.retry_class === "unknown_outcome"
      || projection?.attempt_in_flight === true
      || replacementContentPending
    );
    if (!shouldPoll || !detail.dataset.processingStatusUrl) return;
    const remaining = processingServerSecondsRemaining(
      projection,
      Date.now(),
      processingServerClockOffset(detail),
    );
    const delay = document.hidden || remaining === null
      ? 15000
      : projection?.attempt_in_flight === true || processingSummaryPending(summaryState)
      ? 15000
      : remaining > 0
      ? Math.max(1000, remaining * 1000)
      : 1000;
    processingRecoveryPollTimer = window.setTimeout(() => {
      void refreshProcessingStatus();
    }, delay);
  };

  const refreshPlaybackContent = (current, next) => {
    if (!current.querySelector("[data-playback-player]") || !next.querySelector("[data-playback-player]")
      || !current.dataset.meetingId || !current.dataset.mediaRevisionId
      || ["meetingId", "workspaceId", "mediaRevisionId", "sourceMode"].some(key => current.dataset[key] !== next.dataset[key])) return false;
    // Keep the live audio, comments and draft attached; only transcript-owned controls change.
    for (const selector of [".playback-speaker-overview", "[data-playback-avatars]", "[data-playback-listen-menu]"]) {
      const target = current.querySelector(selector), replacement = next.querySelector(selector);
      if (target && replacement) target.replaceChildren(...replacement.childNodes);
    }
    const timeline = current.querySelector("[data-speaker-timeline]"), nextTimeline = next.querySelector("[data-speaker-timeline]");
    if (timeline && nextTimeline) {
      const wrapper = nextTimeline.closest("[data-speaker-timeline-shell]");
      if (wrapper && !timeline.closest("[data-speaker-timeline-shell]")) timeline.replaceWith(wrapper);
      else {
        timeline.replaceChildren(...nextTimeline.childNodes);
        Object.assign(timeline.dataset, nextTimeline.dataset);
      }
    }
    const manager = current.querySelector("[data-speaker-manager]"), nextManager = next.querySelector("[data-speaker-manager]");
    if (nextManager) {
      if (!manager) current.querySelector(".playback-tools")?.append(nextManager);
      else if (current.dataset.processingResultId !== next.dataset.processingResultId) manager.replaceWith(nextManager);
    } else manager?.remove();
    for (const selector of ["[data-playback-timeline-toggle]", "[data-playback-next]"]) {
      const target = current.querySelector(selector), replacement = next.querySelector(selector);
      if (target && replacement) target.disabled = replacement.disabled;
    }
    for (const selector of [".speaker-timeline-resize-row", "[data-playback-carousel]", "[data-playback-comment]"]) {
      const target = current.querySelector(selector), replacement = next.querySelector(selector);
      if (target && replacement) target.hidden = replacement.hidden;
    }
    const listen = current.querySelector("[data-playback-listen-toggle]")?.parentElement;
    const nextListen = next.querySelector("[data-playback-listen-toggle]")?.parentElement;
    if (listen && nextListen) listen.hidden = nextListen.hidden;
    for (const key of ["processingResultId", "commentsAvailable", "commentsCanComment", "playbackReason"]) current.dataset[key] = next.dataset[key] || "";
    speakerTimelineResizeHandlers.get(current.querySelector("[data-speaker-timeline-shell]"))?.();
    current.dataset.playbackContextChanged = "true";
    return true;
  };

  const refreshProcessingDetailContentOnce = async (
    detail,
    projection,
    { resetRetryBudget = false, forceSummary = false, summaryTemplate = null } = {},
  ) => {
    if (detail.dataset.requestedSummaryTemplate && !forceSummary) return false;
    if (forceSummary && summaryTemplate) detail.dataset.requestedSummaryTemplate = summaryTemplate;
    if (resetRetryBudget) delete detail.dataset.processingContentRefreshRetryCount;
    const transcriptReady = processingTranscriptReady(projection);
    const summaryReady = ["available", "partial"].includes(processingSummaryState(projection).toLowerCase());
    const summaryDisplayState = summaryReady ? "available"
      : processingSummaryPending(processingSummaryState(projection)) ? "processing"
      : ["failed", "unavailable"].includes(processingSummaryState(projection)) ? "unavailable" : "deferred";
    const refreshSummaryState = transcriptReady && detail.dataset.summaryRenderedState
      && detail.dataset.summaryRenderedState !== summaryDisplayState;
    const attemptOrdinal = Number(projection?.attempt_ordinal ?? 0);
    const refreshReplacement = Number.isSafeInteger(attemptOrdinal)
      && attemptOrdinal > 1
      && String(projection?.state || "").toLowerCase() === "processed"
      && detail.dataset.processingPublishedAttempt !== String(attemptOrdinal);
    const refreshTranscript = transcriptReady
      && detail.dataset.processingTranscriptContentReady !== "true";
    const refreshSummary = forceSummary || (summaryReady
      && detail.dataset.processingSummaryContentReady !== "true");
    if (!refreshTranscript && !refreshSummary && !refreshReplacement && !refreshSummaryState) return false;
    let pollUrl = detail.dataset.playbackPollUrl;
    if (!pollUrl) return false;
    if (summaryTemplate) {
      const url = new URL(pollUrl, window.location.href);
      url.searchParams.set("summary_format", summaryTemplate);
      pollUrl = url.href;
    }
    const titleVersion = detail.querySelector("[name='expected_version']")?.value;
    const refreshGeneration = processingRecoveryGeneration;
    const refreshScheduleGeneration = detail.dataset.processingScheduleGeneration || "0";
    const refreshClaim = [
      refreshGeneration,
      refreshScheduleGeneration,
      projection?.updated_at || "",
      transcriptReady,
      summaryReady,
      refreshReplacement,
      summaryDisplayState,
      summaryTemplate,
    ].join("|");
    if (detail.dataset.processingContentRefreshClaim === refreshClaim) return false;
    detail.dataset.processingContentRefreshClaim = refreshClaim;
    const refreshIsCurrent = () => (
      detail.isConnected
      && refreshGeneration === processingRecoveryGeneration
      && (detail.dataset.processingScheduleGeneration || "0") === refreshScheduleGeneration
      && detail.dataset.processingContentRefreshClaim === refreshClaim
      && processingProjectionMatchesDetail(detail, projection)
      && (!summaryTemplate || detail.dataset.requestedSummaryTemplate === summaryTemplate)
    );
    const releaseRefreshClaim = () => {
      if (detail.dataset.processingContentRefreshClaim === refreshClaim) {
        delete detail.dataset.processingContentRefreshClaim;
      }
    };
    const discardStaleRefresh = () => {
      if (refreshIsCurrent()) return false;
      releaseRefreshClaim();
      return true;
    };
    const retryFragmentRefresh = () => {
      releaseRefreshClaim();
      const retryCount = Number(detail.dataset.processingContentRefreshRetryCount || "0") + 1;
      if (retryCount > 3) {
        delete detail.dataset.processingContentRefreshRetryCount;
        stopProcessingRecoveryPolling();
        processingRecoveryPollTimer = window.setTimeout(() => {
          processingRecoveryPollTimer = null;
          if (detail.isConnected && refreshGeneration === processingRecoveryGeneration
            && (!summaryTemplate || detail.dataset.requestedSummaryTemplate === summaryTemplate)) {
            if (forceSummary) void refreshProcessingDetailContentOnce(detail, projection, { forceSummary, summaryTemplate });
            else void refreshProcessingStatus({ force: true, generation: refreshGeneration });
          }
        }, 15000);
        return;
      }
      detail.dataset.processingContentRefreshRetryCount = String(retryCount);
      if (processingRecoveryPollTimer !== null) stopProcessingRecoveryPolling();
      window.setTimeout(() => {
        if (detail.isConnected && (!summaryTemplate || detail.dataset.requestedSummaryTemplate === summaryTemplate)) {
          void refreshProcessingDetailContentOnce(detail, projection, { forceSummary, summaryTemplate });
        }
      }, Math.min(2000 * retryCount, 8000));
    };
    try {
      const response = await fetch(pollUrl, {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          "HX-Request": "true",
          ...(detail.dataset.cabinetEmbedded === "true" ? { "X-GRAF-Client": "desktop" } : {}),
        },
      });
      if (discardStaleRefresh() || await recoverMeetingDetailFromResponse(response)) return false;
      if (!response.ok) {
        retryFragmentRefresh();
        return false;
      }
      const responseText = await response.text();
      if (discardStaleRefresh()) return false;
      const fragment = new DOMParser().parseFromString(responseText, "text/html");
      const nextDetail = fragment.querySelector("[data-playback-poll-url]");
      const currentPlayback = detail.nextElementSibling?.matches?.(".detail-playback")
        ? detail.nextElementSibling
        : null;
      const nextPlayback = fragment.querySelector(".detail-playback");
      if (!nextDetail || (refreshReplacement && (!currentPlayback || !nextPlayback))) {
        retryFragmentRefresh();
        return false;
      }
      if (forceSummary && (nextDetail.dataset.summaryRenderedState !== "available"
        || (summaryTemplate && nextDetail.querySelector("[data-summary-format-controls]")?.dataset.currentTemplateKey !== summaryTemplate))) {
        retryFragmentRefresh();
        return false;
      }
      nextDetail.dataset.processingTranscriptContentReady =
        refreshTranscript ? "true" : detail.dataset.processingTranscriptContentReady || "false";
      nextDetail.dataset.processingSummaryContentReady =
        refreshSummary ? "true" : detail.dataset.processingSummaryContentReady || "false";
      if (refreshReplacement) {
        nextDetail.dataset.processingPublishedAttempt = String(attemptOrdinal);
      }
      if (discardStaleRefresh()) return false;
      if (titleVersion !== detail.querySelector("[name='expected_version']")?.value) {
        retryFragmentRefresh();
        return false;
      }
      releaseRefreshClaim();
      stopProcessingRecoveryCountdown();
      stopProcessingRecoveryPolling();
      const selectedTab = detail.querySelector('[data-detail-tab][aria-selected="true"]')?.dataset.detailTab;
      const focusedID = detail.contains?.(document.activeElement) ? document.activeElement?.id : null;
      if (refreshReplacement) {
        currentPlayback?.querySelector("audio")?.pause();
        if (currentPlayback && nextPlayback) currentPlayback.replaceWith(nextPlayback);
      } else if (refreshTranscript && currentPlayback && nextPlayback && !refreshPlaybackContent(currentPlayback, nextPlayback)) {
        currentPlayback.querySelector("audio")?.pause();
        currentPlayback.replaceWith(nextPlayback);
      }
      if (titleEditorActive()) {
        if (!meetingTitleEditor.refreshDetail(nextDetail)) { retryFragmentRefresh(); return false; }
      } else detail.replaceWith(nextDetail);
      window.setTimeout(() => {
        initCabinet();
        if (selectedTab && typeof activateDetailTab === "function") activateDetailTab(selectedTab, { updateUrl: false });
        if (focusedID) document.getElementById(focusedID)?.focus({ preventScroll: true });
      }, 0);
      return true;
    } catch {
      retryFragmentRefresh();
      return false;
    }
  };

  const renderProcessingProjection = (detail, projection) => {
    if (!processingProjectionMatchesDetail(detail, projection) || processingProjectionIsStale(detail, projection)) return false;
    const updatedAt = processingTimestamp(projection?.updated_at);
    if (updatedAt !== null) detail.dataset.processingProjectionUpdatedAt = projection.updated_at;
    if (typeof projection?.workflow_id === "string" && projection.workflow_id) {
      detail.dataset.processingWorkflowId = projection.workflow_id;
    }
    const attemptOrdinal = Number(projection?.attempt_ordinal);
    if (Number.isSafeInteger(attemptOrdinal) && attemptOrdinal > 0) {
      detail.dataset.processingAttemptOrdinal = String(attemptOrdinal);
    }
    const scheduleGeneration = Number(projection?.schedule_generation);
    detail.dataset.processingScheduleGeneration = Number.isSafeInteger(scheduleGeneration) && scheduleGeneration >= 0
      ? String(scheduleGeneration)
      : "0";
    detail.dataset.processingReasonCode = String(projection?.reason_code || "").toLowerCase();
    detail.dataset.processingManualAction = String(projection?.manual_action || "none");
    detail.dataset.processingTerminal = processingTerminalFailure(projection) ? "true" : "false";
    const serverTime = processingTimestamp(projection?.server_time);
    if (serverTime !== null) {
      detail.dataset.processingServerClockOffsetMs = String(serverTime - Date.now());
    } else {
      delete detail.dataset.processingServerClockOffsetMs;
    }
    delete detail.dataset.processingRecoveryError;
    const transcriptReady = processingTranscriptReady(projection);
    const statusLabel = detail.querySelector("[data-meeting-status-label]");
    const projectionState = String(projection?.state || "").toLowerCase();
    const retryClass = String(projection?.retry_class || "none");
    const reason = String(projection?.reason_code || "").toLowerCase();
    if (statusLabel) {
      statusLabel.textContent = retryClass === "terminal"
        || ["failed_terminal", "blocked", "canceled"].includes(projectionState)
        ? "Нужна помощь"
        : ["processing_retry_deadline_exceeded", "mediascribe_poll_limit_exceeded"].includes(reason)
        ? "Нужна проверка"
        : transcriptReady && projectionState === "processed" ? "Готово" : "Обрабатывается";
    }
    const transcriptState = processingArtifactState(projection, "transcript");
    const transcriptVisible = transcriptReady;
    const terminalTranscript = ["failed", "unavailable"].includes(transcriptState);
    const transcript = detail.querySelector("[data-playback-transcript]");
    const pending = detail.querySelector("[data-transcript-pending]");
    if (transcript) {
      transcript.hidden = !transcriptVisible;
      transcript.setAttribute("aria-hidden", transcriptVisible ? "false" : "true");
    }
    const terminalProcessing = processingTerminalFailure(projection);
    if (pending) pending.hidden = transcriptVisible || terminalTranscript || terminalProcessing;
    detail.dataset.processingTranscriptVisible = transcriptVisible ? "true" : "false";
    const replacementAttempt = Number(
      projection?.attempt_ordinal ?? detail.dataset.processingAttemptOrdinal ?? 0,
    ) > 1 && (
      projection?.content_available === true
      || detail.dataset.processingTranscriptContentReady === "true"
      || detail.dataset.processingTranscriptVisible === "true"
    );
    const replacementPublished = detail.dataset.processingPublishedAttempt === String(attemptOrdinal);
    const replacementActive = replacementAttempt
      && !terminalProcessing
      && (projectionState !== "processed" || !replacementPublished);
    detail.dataset.processingReplacementActive = replacementActive ? "true" : "false";
    if (replacementActive) {
      const popover = detail.querySelector("[data-summary-format-popover]");
      if (popover) {
        if (popover.matches(":popover-open")) popover.hidePopover();
        popover.hidden = true;
      }
      detail.querySelector("[data-summary-format-button]")?.setAttribute("aria-expanded", "false");
    }
    updateProcessingExportVisibility(transcriptReady);
    detail.dataset.processingRetryClass = String(projection?.retry_class || "none");
    detail.dataset.processingSummaryStatus = processingSummaryState(projection);

    const sourceState = String(projection?.state || "").toLowerCase() === "not_submitted"
      ? "active"
      : "ready";
    updateProcessingStage(detail, "source", sourceState, sourceState === "ready" ? "Сохранено" : "Ожидаем отправку");
    updateProcessingStage(
      detail,
      "transcript",
      transcriptReady ? "ready" : ["failed", "unavailable"].includes(transcriptState) ? "unavailable" : "active",
      transcriptReady ? "Готово" : ["failed", "unavailable"].includes(transcriptState) ? "Недоступно" : "Готовится",
    );
    const diarizationState = processingArtifactState(projection, "diarization");
    updateProcessingStage(
      detail,
      "diarization",
      processingArtifactVisible(projection, "diarization")
        ? "ready"
        : ["failed", "unavailable"].includes(diarizationState) ? "unavailable" : "active",
      processingArtifactVisible(projection, "diarization")
        ? "Готово"
        : ["failed", "unavailable"].includes(diarizationState) ? "Недоступно" : "Определяются",
    );
    const summaryState = processingSummaryState(projection);
    const summaryCopy = processingSummaryCopy(
      summaryState,
      detail.dataset.storedOutcomesAvailable === "true",
      transcriptReady,
    );
    const summaryStatus = detail.querySelector("[data-processing-summary-status]");
    if (summaryStatus) {
      summaryStatus.hidden = !summaryCopy;
      summaryStatus.textContent = summaryCopy?.[0] || "";
      summaryStatus.dataset.state = summaryCopy?.[1] || "";
    }
    updateProcessingStage(
      detail,
      "summary",
      ["available", "partial"].includes(summaryState) ? "ready"
        : ["failed", "unavailable"].includes(summaryState) ? "unavailable"
        : "active",
      summaryState === "available" ? "Готово"
        : summaryState === "partial" ? "Доступно частично"
        : ["failed", "unavailable"].includes(summaryState) ? "Недоступно"
        : summaryState === "not_requested" ? "Не запрошены" : "Готовятся",
    );

    const recovery = detail.querySelector("[data-processing-recovery]");
    if (!recovery) return true;
    const copy = processingRecoveryCopy(projection, transcriptReady, replacementPublished);
    recovery.dataset.processingReplacement = replacementAttempt ? "true" : "false";
    if (replacementActive) {
      detail.nextElementSibling?.querySelector?.("audio")?.pause();
    }
    const showSurface = copy !== null;
    recovery.hidden = !showSurface;
    recovery.dataset.state = copy?.state || "ready";
    const title = recovery.querySelector("[data-processing-recovery-title]");
    const message = recovery.querySelector("[data-processing-recovery-copy]");
    if (title) title.textContent = copy?.title || "Обработка завершена";
    if (message) message.textContent = copy?.copy || "";
    const countdownSeconds = processingRecoveryActionRequest !== null || copy?.showCountdown !== true
      ? null
      : renderProcessingCountdown(detail, projection);
    if (countdownSeconds === null || copy?.showCountdown !== true) {
      resetProcessingRecoveryCountdown(detail);
    }
    const check = recovery.querySelector("[data-processing-check]");
    const newAttempt = recovery.querySelector("[data-processing-new-attempt]");
    const reprocess = recovery.querySelector("[data-processing-reprocess-open]");
    const uploadAnother = recovery.querySelector("[data-processing-upload-another]");
    const refresh = recovery.querySelector("[data-processing-refresh]");
    const busyAction = recovery.dataset.processingBusyAction || "";
    const busy = processingRecoveryRequest !== null
      || processingRecoveryActionRequest !== null
      || projection?.attempt_in_flight === true;
    recovery.setAttribute("aria-busy", busy ? "true" : "false");
    if (check) {
      check.hidden = !copy?.canCheck && !(busy && busyAction === "check");
      check.disabled = busy || !copy?.canCheck;
      check.setAttribute("aria-busy", busy && busyAction === "check" ? "true" : "false");
      check.textContent = busy && busyAction === "check"
        ? copy?.busyLabel || "Проверяем…"
        : copy?.checkLabel || "Проверить обработку";
    }
    if (newAttempt) {
      newAttempt.hidden = !copy?.canStartNewAttempt && !(busy && busyAction === "new_attempt");
      newAttempt.disabled = busy || !copy?.canStartNewAttempt;
      newAttempt.setAttribute("aria-busy", busy && busyAction === "new_attempt" ? "true" : "false");
      newAttempt.textContent = busy && busyAction === "new_attempt" ? "Запускаем…" : "Начать обработку заново";
    }
    if (reprocess) {
      const canReprocess = copy?.canReprocess === true
        && detail.dataset.processingReprocessAvailable === "true";
      reprocess.hidden = !canReprocess && !(busy && busyAction === "reprocess");
      reprocess.disabled = busy || !canReprocess;
      reprocess.setAttribute("aria-busy", busy && busyAction === "reprocess" ? "true" : "false");
      reprocess.textContent = copy?.reprocessLabel || "Повторно обработать запись";
    }
    if (uploadAnother) {
      uploadAnother.hidden = !copy?.canUploadAnother;
      uploadAnother.href = copy?.uploadWithoutArchive
        ? uploadAnother.dataset.noArchiveHref
        : uploadAnother.dataset.defaultHref;
      uploadAnother.textContent = copy?.uploadWithoutArchive
        ? "Загрузить без сохранения аудио"
        : "Загрузить другой файл";
    }
    if (refresh) refresh.hidden = !copy?.showRefresh;
    const summaryAnnouncement = summaryCopy?.[0] || "";
    const announcement = replacementActive
      ? "Готовим новую версию."
      : replacementAttempt && terminalProcessing
      ? "Не удалось подготовить новую версию. Текущая версия не изменилась."
      : transcriptReady
      ? `Расшифровка и спикеры готовы.${summaryAnnouncement ? ` ${summaryAnnouncement}` : ""}`
      : `${copy?.title || "Обработка записи"}. ${copy?.copy || ""}`;
    const signature = replacementActive
      ? "replacement-active"
      : [
        projection?.state,
        projection?.retry_class,
        projection?.attempt_in_flight,
        transcriptReady,
        processingArtifactVisible(projection, "diarization"),
        summaryState,
      ].join("|");
    announceProcessingChange(detail, announcement, signature);
    scheduleProcessingRecoveryPolling(detail, projection);
    return true;
  };

  const focusProcessingRecovery = (detail) => {
    const focus = () => {
      if (!detail.isConnected) return;
      const check = detail.querySelector("[data-processing-check]");
      const newAttempt = detail.querySelector("[data-processing-new-attempt]");
      const reprocess = detail.querySelector("[data-processing-reprocess-open]");
      const title = detail.querySelector("[data-processing-recovery-title]");
      const titleVisible = title && !title.hidden && !title.closest("[hidden]");
      const target = check && !check.hidden && !check.disabled
        ? check
        : newAttempt && !newAttempt.hidden && !newAttempt.disabled
        ? newAttempt
        : reprocess && !reprocess.hidden && !reprocess.disabled
        ? reprocess
        : titleVisible
        ? title
        : detail;
      try {
        target.focus({ preventScroll: true });
      } catch {
        target.focus();
      }
    };
    if (typeof window.requestAnimationFrame === "function") window.requestAnimationFrame(focus);
    else focus();
  };

  const setProcessingRecoveryBusy = (detail, busy, action = "check") => {
    const recovery = detail.querySelector("[data-processing-recovery]");
    if (!recovery) return;
    recovery.setAttribute("aria-busy", busy ? "true" : "false");
    if (busy) recovery.dataset.processingBusyAction = action;
    else delete recovery.dataset.processingBusyAction;
    const check = recovery.querySelector("[data-processing-check]");
    const newAttempt = recovery.querySelector("[data-processing-new-attempt]");
    const reprocess = recovery.querySelector("[data-processing-reprocess-open]");
    if (check) {
      if (busy && action === "check") check.hidden = false;
      check.disabled = busy;
      check.setAttribute("aria-busy", busy && action === "check" ? "true" : "false");
      const preparing = detail.dataset.processingManualAction === "retry_preparation";
      check.textContent = busy && action === "check"
        ? preparing ? "Запускаем подготовку…" : "Проверяем…"
        : preparing ? "Повторить подготовку" : "Проверить обработку";
    }
    if (newAttempt) {
      if (busy && action === "new_attempt") newAttempt.hidden = false;
      newAttempt.disabled = busy;
      newAttempt.setAttribute("aria-busy", busy && action === "new_attempt" ? "true" : "false");
      newAttempt.textContent = busy && action === "new_attempt" ? "Запускаем…" : "Начать обработку заново";
    }
    if (reprocess) {
      if (busy && action === "reprocess") reprocess.hidden = false;
      reprocess.disabled = busy;
      reprocess.setAttribute("aria-busy", busy && action === "reprocess" ? "true" : "false");
      reprocess.textContent = "Повторно обработать запись";
    }
  };

  const processingRecoveryActionFailureCopy = (status, manualAction) => {
    const preparation = manualAction === "retry_preparation";
    if (status === 401 || status === 403) {
      return [
        preparation ? "Не удалось повторить подготовку" : "Не удалось проверить обработку",
        "Сессия больше не подтверждена. Обновите страницу и войдите снова.",
      ];
    }
    if (status >= 500) {
      return [
        preparation ? "Подготовка временно недоступна" : "Сервис обработки временно недоступен",
        preparation
          ? "Новая попытка подготовки не запущена. Попробуйте ещё раз позже."
          : "Проверка не запущена. Попробуйте ещё раз позже или обновите страницу.",
      ];
    }
    return [
      preparation ? "Не удалось повторить подготовку" : "Не удалось проверить обработку",
      preparation
        ? "Новая попытка не запущена. Нажмите «Повторить подготовку» ещё раз позже."
        : "Проверка не завершилась. Нажмите «Проверить обработку» ещё раз или обновите страницу.",
    ];
  };

  const renderProcessingRecoveryFailure = (
    detail,
    {
      title = "Не удалось обновить статус обработки",
      message = null,
      signature = "status-fetch-failed",
      failedAction = "check",
    } = {},
  ) => {
    resetProcessingRecoveryCountdown(detail);
    stopProcessingRecoveryPolling();
    const recovery = detail.querySelector("[data-processing-recovery]");
    if (!recovery) return;
    delete recovery.dataset.processingBusyAction;
    const transcript = detail.querySelector("[data-playback-transcript]");
    const pending = detail.querySelector("[data-transcript-pending]");
    const transcriptWasVisible = detail.dataset.processingTranscriptVisible === "true";
    if (transcript) {
      transcript.hidden = !transcriptWasVisible;
      transcript.setAttribute("aria-hidden", transcriptWasVisible ? "false" : "true");
    }
    if (pending) pending.hidden = transcriptWasVisible;
    updateProcessingExportVisibility(transcriptWasVisible);
    detail.dataset.processingRecoveryError = "true";
    recovery.hidden = false;
    recovery.dataset.state = "unknown";
    recovery.setAttribute("aria-busy", "false");
    const titleNode = recovery.querySelector("[data-processing-recovery-title]");
    const messageNode = recovery.querySelector("[data-processing-recovery-copy]");
    if (titleNode) titleNode.textContent = title;
    const resolvedMessage = message || (
      transcriptWasVisible
        ? "Проверка временно недоступна. Расшифровка и спикеры остаются доступны; попробуйте проверить статус ещё раз позже."
        : "Обновите страницу или нажмите «Проверить обработку» ещё раз. Расшифровка появится после подтверждения готовности спикеров."
    );
    if (messageNode) messageNode.textContent = resolvedMessage;
    const check = recovery.querySelector("[data-processing-check]");
    if (check) {
      check.hidden = failedAction !== "check";
      check.disabled = failedAction !== "check";
      check.setAttribute("aria-busy", "false");
      check.textContent = detail.dataset.processingManualAction === "retry_preparation"
        ? "Повторить подготовку"
        : "Проверить обработку";
    }
    const newAttempt = recovery.querySelector("[data-processing-new-attempt]");
    if (newAttempt) {
      const canStartNewAttempt = failedAction === "new_attempt"
        && processingNewAttemptAllowed({
          retry_class: detail.dataset.processingRetryClass,
          manual_action: detail.dataset.processingManualAction,
          reason_code: detail.dataset.processingReasonCode,
          attempt_in_flight: false,
        });
      newAttempt.hidden = !canStartNewAttempt;
      newAttempt.disabled = false;
      newAttempt.setAttribute("aria-busy", "false");
      newAttempt.textContent = "Начать обработку заново";
    }
    const uploadAnother = recovery.querySelector("[data-processing-upload-another]");
    if (uploadAnother) {
      uploadAnother.hidden = detail.dataset.processingManualAction !== "upload_another";
    }
    const refresh = recovery.querySelector("[data-processing-refresh]");
    if (refresh) refresh.hidden = false;
    announceProcessingChange(detail, `${title}. ${resolvedMessage}`, signature);
  };

  const abortProcessingRecoveryStatusRequest = () => {
    const request = processingRecoveryRequest;
    if (!request) return;
    processingRecoveryStatusController?.abort();
    if (processingRecoveryRequest === request) processingRecoveryRequest = null;
    processingRecoveryStatusController = null;
  };

  const refreshProcessingStatus = async ({ force = false, generation = processingRecoveryGeneration } = {}) => {
    const recovery = document.querySelector("[data-processing-recovery]");
    const detail = recovery?.closest("[data-processing-status-url]");
    const statusUrl = detail?.dataset.processingStatusUrl;
    if (!detail || !statusUrl || processingRecoveryActionRequest !== null) return false;
    if (!force && detail.dataset.processingTerminal === "true") return false;
    if (generation !== processingRecoveryGeneration) return false;
    if (processingRecoveryRequest) {
      if (!force) return false;
      abortProcessingRecoveryStatusRequest();
    }
    stopProcessingRecoveryPolling();
    const requestGeneration = generation;
    const controller = typeof AbortController === "function" ? new AbortController() : null;
    const requestOptions = {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: { Accept: "application/json" },
    };
    if (controller) requestOptions.signal = controller.signal;
    const request = fetch(statusUrl, requestOptions);
    processingRecoveryRequest = request;
    processingRecoveryStatusController = controller;
    try {
      const statusResponse = await request;
      if (requestGeneration !== processingRecoveryGeneration || processingRecoveryRequest !== request) return false;
      if (processingRecoveryRequest === request) processingRecoveryRequest = null;
      if (!detail.isConnected) return false;
      if (await recoverMeetingDetailFromResponse(statusResponse)) return false;
      if (
        requestGeneration !== processingRecoveryGeneration
        || (processingRecoveryRequest !== null && processingRecoveryRequest !== request)
      ) return false;
      if (!statusResponse.ok) throw new Error(`processing_status_${statusResponse.status}`);
      const projection = await statusResponse.json();
      if (!projection || typeof projection !== "object" || !processingProjectionMatchesDetail(detail, projection)) {
        throw new Error("processing_status_invalid");
      }
      const rendered = renderProcessingProjection(detail, projection);
      if (rendered && typeof refreshProcessingDetailContentOnce === "function") {
        await refreshProcessingDetailContentOnce(detail, projection, { resetRetryBudget: true });
      }
      if (!rendered && requestGeneration === processingRecoveryGeneration) {
        processingRecoveryPollTimer = window.setTimeout(() => {
          void refreshProcessingStatus({ force: true });
        }, 1000);
      }
      return rendered;
    } catch (error) {
      if (error?.name === "AbortError" || requestGeneration !== processingRecoveryGeneration) return false;
      if (processingRecoveryRequest !== null && processingRecoveryRequest !== request) return false;
      if (processingRecoveryRequest === request) processingRecoveryRequest = null;
      if (detail.isConnected && detail.dataset.processingTerminal !== "true") {
        if (detail.dataset.processingReplacementActive !== "true") {
          renderProcessingRecoveryFailure(detail);
        }
        processingRecoveryPollTimer = window.setTimeout(() => {
          processingRecoveryPollTimer = null;
          if (
            requestGeneration === processingRecoveryGeneration
            && processingRecoveryActionRequest === null
          ) {
            void refreshProcessingStatus({ force: true, generation: requestGeneration });
          }
        }, 15000);
      }
      return false;
    } finally {
      if (processingRecoveryRequest === request) processingRecoveryRequest = null;
      if (processingRecoveryStatusController === controller) processingRecoveryStatusController = null;
    }
  };

  const processingProjectionFromActionPayload = (detail, payload) => {
    const candidates = [payload?.projection, payload?.processing, payload];
    return candidates.find((candidate) => (
      candidate
      && typeof candidate === "object"
      && (processingOwnsField(candidate, "state")
        || processingOwnsField(candidate, "retry_class")
        || processingOwnsField(candidate, "artifacts"))
      && processingProjectionMatchesDetail(detail, candidate)
    )) || null;
  };

  const runProcessingManualCheck = async (detail, recovery) => {
    if (processingRecoveryActionRequest !== null) return;
    const generation = ++processingRecoveryGeneration;
    resetProcessingRecoveryCountdown(detail);
    stopProcessingRecoveryPolling();
    abortProcessingRecoveryStatusRequest();
    const countdown = recovery.querySelector("[data-processing-countdown]");
    if (countdown) countdown.hidden = true;
    setProcessingRecoveryBusy(detail, true);
    announceProcessingChange(detail, "Проверяем статус обработки.", `manual-check-${generation}`);
    const checkUrl = detail.dataset.processingCheckUrl
      || `/api/v1/meetings/${encodeURIComponent(detail.dataset.meetingId || "")}/processing/check`;
    if (!csrfToken || !detail.dataset.meetingId || !checkUrl) {
      const [title] = processingRecoveryActionFailureCopy(
        403,
        detail.dataset.processingManualAction,
      );
      renderProcessingRecoveryFailure(detail, {
        title,
        message: "Сессия не подтверждена. Обновите страницу и войдите снова.",
        signature: `manual-check-failed-${generation}`,
      });
      scheduleProcessingStatusRetry(generation, 1000);
      focusProcessingRecovery(detail);
      return;
    }
    const request = fetch(checkUrl, {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify({
        command_id: processingClientCommandId(),
        schedule_generation: Number.parseInt(detail.dataset.processingScheduleGeneration || "0", 10) || 0,
      }),
    });
    processingRecoveryActionRequest = request;
    let recoveryHandled = false;
    try {
      const response = await request;
      if (generation !== processingRecoveryGeneration || processingRecoveryActionRequest !== request) return;
      if (await recoverMeetingDetailFromResponse(response, { actionProblemCodes: detailActionProblemCodes })) {
        recoveryHandled = true;
        return;
      }
      const payload = response.status === 204 ? null : await response.json().catch(() => null);
      if (!response.ok) {
        if (response.status === 409) {
          processingRecoveryActionRequest = null;
          await refreshProcessingStatus({ force: true, generation });
          return;
        }
        const error = new Error(`processing_check_${response.status}`);
        error.status = response.status;
        throw error;
      }
      const projection = processingProjectionFromActionPayload(detail, payload);
      if (projection) renderProcessingProjection(detail, projection);
      processingRecoveryActionRequest = null;
      await refreshProcessingStatus({ force: true, generation });
    } catch (error) {
      if (generation !== processingRecoveryGeneration || processingRecoveryActionRequest !== request) return;
      processingRecoveryActionRequest = null;
      const [title, message] = processingRecoveryActionFailureCopy(
        Number(error?.status || 0),
        detail.dataset.processingManualAction,
      );
      renderProcessingRecoveryFailure(detail, {
        title,
        message,
        signature: `manual-check-failed-${generation}`,
      });
      scheduleProcessingStatusRetry(generation);
    } finally {
      if (processingRecoveryActionRequest === request) processingRecoveryActionRequest = null;
      if (generation === processingRecoveryGeneration && !recoveryHandled && detail.isConnected) {
        focusProcessingRecovery(detail);
      }
    }
  };

  const runProcessingNewAttempt = async (detail, recovery) => {
    if (processingRecoveryActionRequest !== null) return;
    const generation = ++processingRecoveryGeneration;
    resetProcessingRecoveryCountdown(detail);
    stopProcessingRecoveryPolling();
    abortProcessingRecoveryStatusRequest();
    setProcessingRecoveryBusy(detail, true, "new_attempt");
    announceProcessingChange(detail, "Запускаем новую обработку записи.", `new-attempt-${generation}`);
    const attemptUrl = detail.dataset.processingAttemptUrl
      || `/api/v1/meetings/${encodeURIComponent(detail.dataset.meetingId || "")}/processing/attempt`;
    if (!csrfToken || !detail.dataset.meetingId || !attemptUrl) {
      renderProcessingRecoveryFailure(detail, {
        title: "Не удалось начать обработку заново",
        message: "Сессия не подтверждена. Обновите страницу и войдите снова.",
        signature: `new-attempt-failed-${generation}`,
        failedAction: "new_attempt",
      });
      scheduleProcessingStatusRetry(generation, 1000);
      focusProcessingRecovery(detail);
      return;
    }
    const request = fetch(attemptUrl, {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "X-CSRF-Token": csrfToken,
      },
    });
    processingRecoveryActionRequest = request;
    let recoveryHandled = false;
    try {
      const response = await request;
      if (generation !== processingRecoveryGeneration || processingRecoveryActionRequest !== request) return;
      if (await recoverMeetingDetailFromResponse(response, { actionProblemCodes: detailActionProblemCodes })) {
        recoveryHandled = true;
        return;
      }
      const payload = response.status === 204 ? null : await response.json().catch(() => null);
      if (!response.ok) {
        if (response.status === 409) {
          if (payload?.code === "processing_quota_exceeded") {
            processingRecoveryActionRequest = null;
            renderProcessingRecoveryFailure(detail, {
              title: "Лимит расшифровки ещё не обновился",
              message: "Новая попытка не запущена. Дождитесь обновления лимита и нажмите «Начать обработку заново» ещё раз.",
              signature: `new-attempt-quota-${generation}`,
              failedAction: "new_attempt",
            });
            return;
          }
          processingRecoveryActionRequest = null;
          await refreshProcessingStatus({ force: true, generation });
          return;
        }
        const error = new Error(`processing_attempt_${response.status}`);
        error.status = response.status;
        throw error;
      }
      const projection = processingProjectionFromActionPayload(detail, payload);
      if (projection) renderProcessingProjection(detail, projection);
      processingRecoveryActionRequest = null;
      await refreshProcessingStatus({ force: true, generation });
    } catch (error) {
      if (generation !== processingRecoveryGeneration || processingRecoveryActionRequest !== request) return;
      processingRecoveryActionRequest = null;
      renderProcessingRecoveryFailure(detail, {
        title: "Не удалось начать обработку заново",
        message: Number(error?.status || 0) === 409
          ? "Новая попытка сейчас недоступна. Обновите страницу, чтобы увидеть актуальный статус."
          : "Новая попытка не запущена. Обновите страницу и попробуйте ещё раз позже.",
        signature: `new-attempt-failed-${generation}`,
        failedAction: "new_attempt",
      });
      scheduleProcessingStatusRetry(generation);
    } finally {
      if (processingRecoveryActionRequest === request) processingRecoveryActionRequest = null;
      if (generation === processingRecoveryGeneration && !recoveryHandled && detail.isConnected) {
        focusProcessingRecovery(detail);
      }
    }
  };

  const restoreProcessingReprocessFocus = () => {
    if (!(processingReprocessReturnFocus instanceof HTMLElement)) return;
    const menu = processingReprocessReturnFocus.closest('[role="menu"]');
    if (menu?.hidden) {
      menu.hidden = false;
      document.querySelector('[data-meeting-panel-open="more"]')
        ?.setAttribute("aria-expanded", "true");
    }
    if (isUsableFocusTarget(processingReprocessReturnFocus)) {
      processingReprocessReturnFocus.focus({ preventScroll: true });
    } else {
      restoreMeetingActionFocus(processingReprocessReturnFocus);
    }
    processingReprocessReturnFocus = null;
  };

  const setProcessingReprocessDialogBusy = (dialog, busy) => {
    const form = dialog.querySelector("[data-processing-reprocess-form]");
    const submit = dialog.querySelector("[data-processing-reprocess-submit]");
    form?.setAttribute("aria-busy", busy ? "true" : "false");
    if (submit) {
      submit.disabled = busy;
      submit.textContent = busy ? "Готовим…" : "Подготовить";
    }
    dialog.querySelectorAll("[data-processing-reprocess-cancel]").forEach((button) => {
      button.disabled = busy;
    });
  };

  const setProcessingReprocessError = (dialog, message = "") => {
    const error = dialog.querySelector("[data-processing-reprocess-error]");
    if (!error) return;
    error.hidden = !message;
    error.textContent = message;
  };

  const runProcessingReprocess = async (detail, dialog) => {
    if (processingRecoveryActionRequest !== null) return;
    const submit = dialog.querySelector("[data-processing-reprocess-submit]");
    const reprocessUrl = detail.dataset.processingReprocessUrl;
    if (
      !csrfToken
      || !detail.dataset.meetingId
      || !detail.dataset.processingWorkflowId
      || !detail.dataset.mediaRevisionId
      || !reprocessUrl
    ) {
      setProcessingReprocessError(
        dialog,
        "Не удалось подтвердить актуальную версию встречи. Обновите страницу и попробуйте снова.",
      );
      return;
    }
    const generation = ++processingRecoveryGeneration;
    resetProcessingRecoveryCountdown(detail);
    stopProcessingRecoveryPolling();
    abortProcessingRecoveryStatusRequest();
    setProcessingRecoveryBusy(detail, true, "reprocess");
    setProcessingReprocessDialogBusy(dialog, true);
    setProcessingReprocessError(dialog);
    const request = fetch(reprocessUrl, {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify({
        expected_workflow_id: detail.dataset.processingWorkflowId,
        expected_media_revision_id: detail.dataset.mediaRevisionId,
      }),
    });
    processingRecoveryActionRequest = request;
    let recoveryHandled = false;
    try {
      const response = await request;
      if (generation !== processingRecoveryGeneration || processingRecoveryActionRequest !== request) return;
      if (await recoverMeetingDetailFromResponse(response, { actionProblemCodes: detailActionProblemCodes })) {
        recoveryHandled = true;
        return;
      }
      const payload = response.status === 204 ? null : await response.json().catch(() => null);
      if (!response.ok) {
        const failure = new Error(`processing_reprocess_${response.status}`);
        failure.status = response.status;
        throw failure;
      }
      processingRecoveryActionRequest = null;
      const projection = processingProjectionFromActionPayload(detail, payload);
      if (projection) renderProcessingProjection(detail, projection);
      setProcessingReprocessDialogBusy(dialog, false);
      dialog.close();
      processingReprocessReturnFocus = null;
      await refreshProcessingStatus({ force: true, generation });
      if (detail.isConnected) focusProcessingRecovery(detail);
    } catch (error) {
      if (generation !== processingRecoveryGeneration || processingRecoveryActionRequest !== request) return;
      processingRecoveryActionRequest = null;
      setProcessingRecoveryBusy(detail, false, "reprocess");
      setProcessingReprocessDialogBusy(dialog, false);
      setProcessingReprocessError(
        dialog,
        Number(error?.status || 0) === 409
          ? "Страница встречи устарела. Закройте окно, обновите статус и подтвердите запуск снова."
          : Number(error?.status || 0) === 401 || Number(error?.status || 0) === 403
          ? "Сессия больше не подтверждена. Обновите страницу и войдите снова."
          : "Повторная обработка не запущена. Попробуйте ещё раз позже.",
      );
      submit?.focus({ preventScroll: true });
      scheduleProcessingStatusRetry(generation);
    } finally {
      if (processingRecoveryActionRequest === request) processingRecoveryActionRequest = null;
      if (recoveryHandled) processingReprocessReturnFocus = null;
    }
  };

  const initProcessingReprocess = () => {
    const dialog = document.querySelector("[data-processing-reprocess-dialog]");
    const detail = document.querySelector("[data-processing-reprocess-url]");
    if (!dialog || !detail || typeof dialog.showModal !== "function") return;
    const closeDialog = (restoreFocus = true) => {
      if (processingRecoveryActionRequest !== null) return;
      if (dialog.open) dialog.close();
      setProcessingReprocessDialogBusy(dialog, false);
      setProcessingReprocessError(dialog);
      if (restoreFocus) restoreProcessingReprocessFocus();
      else processingReprocessReturnFocus = null;
    };
    document.querySelectorAll("[data-processing-reprocess-open]").forEach((opener) => {
      if (opener.dataset.processingReprocessReady === "true") return;
      opener.dataset.processingReprocessReady = "true";
      opener.addEventListener("click", () => {
        processingReprocessReturnFocus = opener;
        setProcessingReprocessDialogBusy(dialog, false);
        setProcessingReprocessError(dialog);
        dialog.showModal();
        dialog.querySelector("#processing-reprocess-dialog-title")?.focus({ preventScroll: true });
      });
    });
    if (dialog.dataset.processingReprocessReady === "true") return;
    dialog.dataset.processingReprocessReady = "true";
    dialog.querySelectorAll("[data-processing-reprocess-cancel]").forEach((button) => {
      button.addEventListener("click", () => closeDialog(true));
    });
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      closeDialog(true);
    });
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) closeDialog(true);
    });
    const keepFocusInsideDialog = (event) => trapModalFocus(dialog, event);
    dialog.addEventListener("keydown", keepFocusInsideDialog);
    dialog.querySelector("[data-processing-reprocess-form]")?.addEventListener("submit", (event) => {
      event.preventDefault();
      void runProcessingReprocess(detail, dialog);
    });
  };

  const initProcessingRecovery = () => {
    const recovery = document.querySelector("[data-processing-recovery]");
    const detail = recovery?.closest("[data-processing-status-url]");
    if (!recovery || !detail?.dataset.processingStatusUrl) {
      stopProcessingRecoveryCountdown();
      stopProcessingRecoveryPolling();
      return;
    }
    if (recovery.dataset.processingRecoveryReady === "true") return;
    recovery.dataset.processingRecoveryReady = "true";
    const transcript = detail.querySelector("[data-playback-transcript]");
    if (detail.dataset.processingTranscriptContentReady == null) {
      detail.dataset.processingTranscriptContentReady = transcript && !transcript.hidden
        ? "true"
        : "false";
    }
    if (detail.dataset.processingSummaryContentReady == null) {
      detail.dataset.processingSummaryContentReady = detail.dataset.storedOutcomesAvailable === "true"
        ? "true"
        : "false";
    }
    if (detail.dataset.processingTranscriptVisible == null) {
      detail.dataset.processingTranscriptVisible = transcript && !transcript.hidden
        ? "true"
        : "false";
    }
    updateProcessingExportVisibility(detail.dataset.processingTranscriptVisible === "true");
    recovery.querySelector("[data-processing-recovery-copy]")?.setAttribute("id", "processing-recovery-copy");
    recovery.querySelector("[data-processing-check]")?.addEventListener("click", () => {
      void runProcessingManualCheck(detail, recovery);
    });
    recovery.querySelector("[data-processing-new-attempt]")?.addEventListener("click", () => {
      void runProcessingNewAttempt(detail, recovery);
    });
    recovery.querySelector("[data-processing-refresh]")?.addEventListener("click", () => window.location.reload());
    if (document.body.dataset.processingRecoveryListeners !== "true") {
      document.body.dataset.processingRecoveryListeners = "true";
      window.addEventListener("online", () => {
        if (processingRecoveryActionRequest === null) void refreshProcessingStatus();
      });
      document.addEventListener("visibilitychange", () => {
        if (!document.hidden && processingRecoveryActionRequest === null) void refreshProcessingStatus();
      });
    }
    void refreshProcessingStatus();
  };

  const renderProcessingListProjection = (row, projection, generation) => {
    const rowMeetingId = String(row?.dataset.meetingId || "");
    if (
      !row?.isConnected
      || !currentList()?.contains(row)
      || !rowMeetingId
      || String(projection?.meeting_id || "") !== rowMeetingId
      || generation !== meetingListRequestGeneration
    ) return;
    const retryClass = String(projection?.retry_class || "none");
    const state = String(projection?.state || "").toLowerCase();
    const transcriptReady = processingTranscriptReady(projection);
    const summaryState = processingSummaryState(projection);
    if (
      retryClass === "terminal"
      || ["blocked", "failed_terminal", "canceled"].includes(state)
      || (state === "processed" && (
        !processingSummaryPending(summaryState)
        || (transcriptReady && row.dataset.processingTranscriptVisible !== "true")
      ))
    ) {
      const restoreFocus = row.contains(document.activeElement);
      if (requestMeetingListRefresh({ focusMeetingIds: [rowMeetingId], restoreFocus })) return;
    }
    const replacement = Number(projection?.attempt_ordinal ?? 0) > 1
      && projection?.content_available === true;
    const text = replacement && !processingTerminalFailure(projection)
      ? "Готовится новая версия"
      : retryClass === "retryable"
      ? "Обработка временно приостановлена"
      : retryClass === "unknown_outcome"
      ? "Проверяем исходную попытку"
      : retryClass === "terminal"
      ? "Требует внимания"
      : transcriptReady
      ? `Расшифровка готова · ${summaryState === "available" ? "итоги готовы" : summaryState === "partial" ? "итоги доступны частично" : processingSummaryPending(summaryState) ? "итоги готовятся" : "итоги недоступны"}`
      : "Спикеры определяются · расшифровка готовится";
    const node = row.querySelector(".meeting-content-readiness");
    if (node) node.dataset.processingListStatus = "true";
    if (!node) return;
    const signature = `${row.dataset.meetingId || ""}|${text}|${retryClass}|${transcriptReady}|${summaryState}`;
    const previous = processingListProjectionStates.get(row.dataset.meetingId || "")?.signature;
    node.textContent = text;
    node.dataset.processingRetryClass = retryClass;
    row.dataset.processingTranscriptVisible = transcriptReady ? "true" : "false";
    processingListProjectionStates.set(row.dataset.meetingId || "", { signature, projection });
    if (previous && previous !== signature) {
      const announcer = document.querySelector("[data-processing-list-announcer]");
      if (announcer) announcer.textContent = "Статусы обработки встреч обновлены.";
    }
  };

  const requestProcessingListProjection = (row) => {
    const meetingId = String(row.dataset.meetingId || "");
    if (!meetingId) return;
    const generation = meetingListRequestGeneration;
    const now = Date.now();
    const existing = processingListProjectionRequests.get(meetingId);
    if (existing?.generation === generation) return;
    if (existing) {
      existing.controller?.abort();
      processingListProjectionRequests.delete(meetingId);
    }
    if (now - (processingListProjectionLastFetchedAt.get(meetingId) || 0) < 15000) return;
    processingListProjectionLastFetchedAt.set(meetingId, now);
    const controller = typeof AbortController === "function" ? new AbortController() : null;
    const request = fetch(`/api/v1/meetings/${encodeURIComponent(meetingId)}/processing`, {
      credentials: "same-origin",
      cache: "no-store",
      headers: { Accept: "application/json" },
      ...(controller ? { signal: controller.signal } : {}),
    });
    const entry = { controller, generation };
    processingListProjectionRequests.set(meetingId, entry);
    void request.then(async (response) => {
      if (!response.ok) return;
      const projection = await response.json();
      if (projection && typeof projection === "object") {
        renderProcessingListProjection(row, projection, generation);
      }
    }).catch(() => {}).finally(() => {
      if (processingListProjectionRequests.get(meetingId) === entry) {
        processingListProjectionRequests.delete(meetingId);
      }
    });
  };

  const initProcessingListProjection = () => {
    const list = currentList();
    if (!list) return;
    const rows = allRows().filter((row) => {
      const kind = row.querySelector(".meeting-status[data-status-kind]")?.dataset.statusKind || "";
      return kind === "processing" || row.dataset.summaryPending === "true";
    });
    if (!rows.length) {
      resetProcessingListProjectionState();
      return;
    }
    const activeMeetingIds = new Set(rows.map((row) => row.dataset.meetingId || ""));
    processingListProjectionStates.forEach((_state, meetingId) => {
      if (!activeMeetingIds.has(meetingId)) {
        processingListProjectionStates.delete(meetingId);
        processingListProjectionLastFetchedAt.delete(meetingId);
      }
    });
    rows.forEach((row) => {
      const snapshot = processingListProjectionStates.get(row.dataset.meetingId || "")?.projection;
      if (snapshot) renderProcessingListProjection(row, snapshot, meetingListRequestGeneration);
      requestProcessingListProjection(row);
    });
    if (!processingListProjectionPollTimer) {
      processingListProjectionPollTimer = window.setTimeout(() => {
        processingListProjectionPollTimer = null;
        initProcessingListProjection();
      }, 15000);
    }
  };

  const initSummaryFormats = () => {
    document.querySelectorAll("[data-summary-format-controls]").forEach((controls) => {
      if (controls.dataset.summaryFormatReady === "true") return;
      const button = controls.querySelector("[data-summary-format-button]");
      const info = controls.querySelector(".summary-format-info");
      const refreshButton = controls.querySelector("[data-summary-refresh-button]");
      const listbox = controls.querySelector("[data-summary-format-listbox]");
      const pendingLabel = controls.querySelector("[data-summary-pending-format-label]");
      const status = document.querySelector("[data-summary-candidate-status]");
      const statusLive = status?.querySelector("[data-summary-candidate-live]");
      const statusActions = status?.querySelector("[data-summary-candidate-actions]");
      const popover = controls.querySelector("[data-summary-format-popover]");
      const allFormats = controls.querySelector("[data-summary-format-all]");
      const back = controls.querySelector("[data-summary-format-back]");
      const settings = controls.querySelector("[data-summary-format-settings]");
      const description = controls.querySelector("[data-summary-format-description]");
      const personalHost = controls.querySelector("[data-summary-personal-options]");
      const loadStatus = controls.querySelector("[data-summary-format-load-status]");
      let personalLoading = false;
      let personalLoaded = false;
      const meetingId = controls.dataset.meetingId || "";
      const candidateStorageKey = `graf-summary-candidate-${meetingId}`;
      let currentOutcomeSetId = controls.dataset.currentOutcomeSetId || null;
      let refreshBaselineOutcomeSetId = currentOutcomeSetId;
      let activeTemplate = null;
      let pollingTimer = null;
      let pollAttempts = 0;
      let pollDeadline = 0;
      let pollDelay = 1500;
      let activeRequestIntent = "manual_format";
      let activeRequestIntentId = null;
      let candidateRequestGeneration = 0;
      let candidateRequestInFlightGeneration = null;
      const acceptedFocusKey = `graf-summary-focus-${meetingId}`;
      if (!button || !listbox || !popover) return;
      controls.dataset.summaryFormatReady = "true";
      const options = () => Array.from(listbox.querySelectorAll('[role="option"]'));
      const visibleOptions = () => options().filter((option) => !option.disabled && !option.closest("[hidden]"));
      const close = ({ restoreFocus = true } = {}) => {
        if (popover.matches(":popover-open")) popover.hidePopover();
        popover.hidden = true;
        button.setAttribute("aria-expanded", "false");
        if (restoreFocus && button.isConnected) button.focus({ preventScroll: true });
      };
      const focusOption = (option) => {
        options().forEach((item) => { item.tabIndex = item === option ? 0 : -1; });
        option?.focus({ preventScroll: true });
        if (!option) return;
        const row = option.getBoundingClientRect();
        const list = listbox.getBoundingClientRect();
        const scale = list.height / listbox.offsetHeight || 1;
        if (row.top < list.top) listbox.scrollTop -= (list.top - row.top) / scale;
        else if (row.bottom > list.bottom) listbox.scrollTop += (row.bottom - list.bottom) / scale;
      };
      const focusCurrentFormat = () => {
        const items = visibleOptions();
        focusOption(items.find((item) => item.getAttribute("aria-selected") === "true") || items[0]);
      };
      const sizePopover = () => {
        if (popover.hidden) return;
        const anchor = button.getBoundingClientRect();
        const scale = anchor.width / button.offsetWidth || 1;
        popover.style.maxHeight = `${Math.max(0, Math.min(440, (window.innerHeight - 24) / scale))}px`;
        const bounds = popover.getBoundingClientRect();
        popover.style.left = `${Math.max(12, Math.min(anchor.left, window.innerWidth - bounds.width - 12)) / scale}px`;
        popover.style.top = `${Math.max(12, Math.min(anchor.bottom + 7, window.innerHeight - bounds.height - 12)) / scale}px`;
      };
      const open = (full = false) => {
        if (info) info.open = false;
        popover.hidden = false;
        if (!popover.matches(":popover-open")) popover.showPopover();
        button.setAttribute("aria-expanded", "true");
        listbox.querySelectorAll("[data-summary-format-extra]").forEach((option) => { option.hidden = !full; });
        if (personalHost) personalHost.hidden = !full || !personalHost.children.length;
        if (allFormats) allFormats.hidden = full;
        if (back) back.hidden = !full;
        if (settings) settings.hidden = !full;
        if (loadStatus) loadStatus.hidden = !full || !loadStatus.textContent;
        sizePopover();
        focusCurrentFormat();
      };
      const setBusy = (busy) => {
        if (busy) close({ restoreFocus: false });
        button.disabled = busy;
        if (refreshButton) refreshButton.disabled = busy;
        controls.setAttribute("aria-busy", busy ? "true" : "false");
      };
      const reloadAfterSummaryChange = (template = activeTemplate) => {
        const templateKey = typeof template === "string" ? template : template?.key;
        const detail = controls.closest("[data-processing-status-url]");
        if (!detail?.isConnected) return;
        void refreshProcessingDetailContentOnce(detail, {
          meeting_id: detail.dataset.meetingId,
          media_revision_id: detail.dataset.mediaRevisionId,
          summary_status: "available",
        }, { forceSummary: true, summaryTemplate: templateKey });
      };
      const showStatus = (message, state = "generating", actions = []) => {
        if (!status || !statusLive || !statusActions) return;
        status.hidden = false;
        status.dataset.state = state;
        statusLive.textContent = message;
        statusActions.replaceChildren();
        const validActions = actions.filter((item) => (
          item
          && typeof item.text === "string"
          && typeof item.action === "function"
        ));
        if (!validActions.length) return;
        validActions.forEach(({ text, action, primary = false }) => {
          const actionButton = document.createElement("button");
          actionButton.type = "button";
          actionButton.textContent = text;
          if (primary) actionButton.className = "button";
          actionButton.addEventListener("click", action);
          statusActions.append(actionButton);
        });
      };
      const candidateErrorCopy = (code) => ({
        summary_transcript_too_large: "Расшифровка слишком большая для этого действия.",
        summary_transcript_unavailable: "Расшифровка пока недоступна. Обновите страницу и попробуйте снова.",
        summary_source_unavailable: "Источник итогов пока недоступен. Обновите страницу и попробуйте снова.",
        transcript_unavailable: "Расшифровка пока недоступна. Обновите страницу и попробуйте снова.",
        source_unavailable: "Источник итогов пока недоступен. Обновите страницу и попробуйте снова.",
        summary_transcript_snapshot_invalid: "Расшифровка изменилась. Обновите страницу и попробуйте снова.",
        summary_transcript_changed: "Расшифровка изменилась. Обновите страницу и запросите новый вариант.",
        outcome_transcript_changed: "Расшифровка изменилась. Обновите страницу и запросите новый вариант.",
        summary_dependency_unavailable: "Сервис генерации временно недоступен. Текущие итоги сохранены.",
        summary_generation_unavailable: "Сервис генерации временно недоступен. Текущие итоги сохранены.",
        summary_prompt_resolution_conflict: "Настройки формата изменились. Обновите страницу и попробуйте снова.",
        summary_prompt_invalid: "Настройки выбранного формата недоступны. Выберите другой формат.",
        summary_prompt_snapshot_corrupt: "Настройки выбранного формата недоступны. Выберите другой формат.",
        summary_prompt_not_selected: "Не удалось определить настройки формата. Выберите формат ещё раз.",
        prompt_invalid: "Настройки выбранного формата недоступны. Выберите другой формат.",
        summary_generation_in_progress: "Другой вариант уже готовится. Обновите статус через несколько секунд.",
        generation_in_progress: "Другой вариант уже готовится. Обновите статус через несколько секунд.",
        generation_call_not_completed: "Ответ модели не был сохранён полностью. Обновите статус.",
        generation_call_content_incomplete: "Ответ модели не был сохранён полностью. Обновите статус.",
        generation_call_content_hash_mismatch: "Не удалось проверить сохранённый ответ. Обновите статус.",
        content_unavailable: "Ответ модели не был сохранён полностью. Обновите статус.",
        input_too_large: "Расшифровка слишком большая для генерации итогов. Расшифровка и текущие итоги сохранены.",
        summary_revision_conflict: "Итоги уже изменились. Обновите страницу.",
        revision_changed: "Итоги уже изменились. Обновите страницу.",
        result_invalid: "Модель вернула неподтверждённый результат. Можно попробовать другой вариант.",
        source_changed: "Расшифровка изменилась. Обновите страницу и запросите новый вариант.",
        template_unavailable: "Этот формат больше недоступен. Выберите другой формат.",
        provider_outcome_unknown: "Не удалось подтвердить ответ модели. Проверьте статус и повторите позже.",
        temporary_unavailable: "Сервис временно недоступен. Текущие итоги сохранены.",
        prompt_unavailable: "Настройки формата временно недоступны. Текущие итоги сохранены.",
        provider_unavailable: "Сервис генерации временно недоступен. Текущие итоги сохранены.",
        summary_request_unavailable: "Не удалось связаться с сервисом итогов. Текущие итоги сохранены.",
        summary_poll_unavailable: "Не удалось обновить статус нового варианта. Текущие итоги сохранены.",
        summary_candidate_not_found: "Новый вариант больше недоступен. Обновите страницу.",
        summary_generation_forbidden: "У вас больше нет доступа к созданию итогов.",
        generation_failed: "Не удалось проверить новый вариант. Обновите страницу.",
        meeting_deleting: "Встреча удаляется. Новый вариант создать нельзя.",
        meeting_deleted: "Встреча удалена.",
        cancelled: "Подготовка нового варианта отменена.",
        dismissed: "Вариант закрыт. Текущие итоги сохранены.",
        meeting_deletion_active: "Встреча удаляется. Новый вариант больше недоступен.",
        summary_candidate_expired: "Вариант устарел. Текущие итоги сохранены.",
        summary_same_format_noop: "Этот формат уже выбран. Нажмите «Обновить итоги», чтобы создать новый вариант.",
        summary_template_unavailable: "Выбранный формат больше недоступен. Выберите другой активный формат.",
        summary_refresh_intent_missing: "Не удалось подтвердить обновление. Выберите «Обновить итоги» ещё раз.",
        summary_source_revision_stale: "Расшифровка изменилась. Текущие итоги сохранены."
      }[code] || "Не удалось подготовить новый вариант. Текущие итоги сохранены.");
      const retryCandidateAction = (candidate = {}) => {
        if (typeof candidate === "string") {
          if ([
            "meeting_deleting", "meeting_deletion_active", "meeting_deleted",
            "summary_candidate_expired", "summary_candidate_not_found",
            "summary_candidate_state_invalid", "summary_candidate_unavailable",
            "summary_resolution_forbidden", "summary_revision_conflict",
            "summary_same_format_noop", "summary_source_revision_stale",
            "summary_generation_in_progress"
          ].includes(candidate)) {
            return { text: "Обновить страницу", action: () => window.location.reload(), primary: true };
          }
          if (candidate === "summary_template_unavailable") {
            return { text: "Выбрать формат", action: openFormatPicker, primary: true };
          }
          return { text: "Обновить итоги", action: requestCurrentRefresh, primary: true };
        }
        if (candidate.next_action === "new_candidate") {
          const template = templateFromCandidate(candidate) || activeTemplate;
          return {
            text: "Создать новый вариант",
            action: () => template && requestCandidate(template, {
              requestIntent: "manual_refresh",
              requestIntentId: newRequestIntentId()
            }),
            primary: true
          };
        }
        if (candidate.retryable) {
          const template = templateFromCandidate(candidate) || activeTemplate;
          return {
            text: "Попробовать ещё раз",
            action: () => template && requestCandidate(template, {
              requestIntent: "manual_refresh",
              requestIntentId: newRequestIntentId()
            }),
            primary: true
          };
        }
        if (candidate.next_action === "refresh" || candidate.next_action === "refresh_status") {
          return { text: "Обновить страницу", action: () => window.location.reload(), primary: true };
        }
        return null;
      };
      const candidateErrorAction = (code, template, error = null) => {
        const transientTransportFailure = !code
          || error?.name === "TypeError"
          || error?.status >= 500
          || [408, 425, 429].includes(error?.status);
        if (transientTransportFailure) {
          return {
            text: "Попробовать ещё раз",
            action: () => template && requestCandidate(template, {
              requestIntent: "manual_refresh",
              requestIntentId: newRequestIntentId()
            }),
            primary: true
          };
        }
        if ([
          "summary_revision_conflict",
          "summary_transcript_changed",
          "outcome_transcript_changed",
          "summary_prompt_resolution_conflict",
          "summary_template_unavailable",
          "summary_transcript_unavailable",
          "summary_source_unavailable",
          "summary_prompt_invalid",
          "summary_prompt_snapshot_corrupt",
          "summary_prompt_not_selected",
          "summary_generation_in_progress",
          "generation_call_not_completed",
          "generation_call_content_incomplete",
          "generation_call_content_hash_mismatch",
          "summary_candidate_not_found",
          "summary_generation_forbidden"
        ].includes(code)) {
          return { text: "Обновить страницу", action: () => window.location.reload(), primary: true };
        }
        if ([
          "summary_generation_unavailable",
          "summary_dispatch_unavailable",
          "summary_dispatch_retries_exhausted",
          "summary_request_unavailable",
          "summary_poll_unavailable",
          "langfuse_prompt_unavailable",
          "prompt_snapshot_export_unavailable",
          "litellm_endpoint_unavailable",
          "litellm_unavailable",
          "litellm_retryable_response"
        ].includes(code)) {
          return {
            text: "Попробовать ещё раз",
            action: () => template && requestCandidate(template, {
              requestIntent: "manual_refresh",
              requestIntentId: newRequestIntentId()
            }),
            primary: true
          };
        }
        return null;
      };
      const openFormatPicker = () => {
        open(true);
        void loadPersonalFormats();
      };
      const retryTerminalCandidateAction = (code = "") => retryCandidateAction(code);
      const templateFromCandidate = (candidate) => {
        if (!candidate) return null;
        const safeCandidate = candidate || {};
        const provenance = safeCandidate.provenance || {};
        const candidateKey = provenance.template_key || safeCandidate.template_key || "";
        const candidateId = provenance.template_id || safeCandidate.template_id || null;
        const candidateVersion = Number(provenance.template_version || candidate.template_version || "1");
        if (!candidateKey || !Number.isInteger(candidateVersion)) return null;
        const option = options().find((item) => (
          item.dataset.templateKey === candidateKey
          && Number(item.dataset.templateVersion || "1") === candidateVersion
          && (item.dataset.templateId || null) === candidateId
        ));
        if (option) return templateFrom(option);
        return {
          id: candidateId,
          key: candidateKey,
          version: candidateVersion,
          name: candidate?.format_name || candidate?.template_name || candidateKey
        };
      };
      const resumeCandidatePolling = (candidate, generation = candidateRequestGeneration) => {
        if (generation !== candidateRequestGeneration) return;
        pollAttempts = 0;
        pollDeadline = Date.now() + 5 * 60 * 1000;
        pollDelay = 1500;
        setBusy(true);
        showStatus("Проверяем новую версию. Текущие итоги остаются доступны.");
        schedulePoll(candidate, generation);
      };
      const mutate = async (url, method, body) => {
        const response = await fetch(url, {
          method,
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "Content-Type": "application/json",
            ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {})
          },
          body: body === undefined ? undefined : JSON.stringify(body)
        });
        if (await recoverMeetingDetailFromResponse(response, { actionProblemCodes: summaryActionProblemCodes })) {
          throw meetingDetailRecoveredError();
        }
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          const error = new Error(payload.code || (response.status >= 500 ? "summary_request_unavailable" : "summary_request_failed"));
          error.status = response.status;
          throw error;
        }
        return payload;
      };
      const dismissStatus = () => {
        setBusy(false);
        if (status) status.hidden = true;
        button.focus({ preventScroll: true });
      };
      const renderCandidate = (candidate, generation = candidateRequestGeneration) => {
        if (generation !== candidateRequestGeneration) return false;
        if (Object.prototype.hasOwnProperty.call(candidate, "current_outcome_set_id")) {
          currentOutcomeSetId = candidate.current_outcome_set_id || null;
        }
        if (candidate.state === "generating") {
          if (candidate.reason_code === "temporary_unavailable") {
            window.clearTimeout(pollingTimer);
            pollingTimer = null;
            setBusy(false);
            if (pendingLabel) pendingLabel.hidden = true;
            const retry = retryCandidateAction(candidate);
            showStatus(candidateErrorCopy(candidate.reason_code), "failed", retry ? [retry] : []);
            return;
          }
          window.sessionStorage.setItem(candidateStorageKey, JSON.stringify({
            poll_url: candidate.poll_url,
            template: activeTemplate,
            requestIntent: activeRequestIntent,
            requestIntentId: activeRequestIntentId,
            pollAttempts,
            pollDeadline,
            pollDelay
          }));
          if (pendingLabel) {
            pendingLabel.hidden = false;
            pendingLabel.textContent = activeTemplate?.name
              ? `Готовим вариант: ${activeTemplate.name}`
              : "Готовим новый вариант";
          }
          showStatus(`Готовим формат «${candidate.format_name || activeTemplate?.name || "итогов"}». Текущие итоги остаются доступны.`);
          return;
        }
        window.clearTimeout(pollingTimer);
        window.sessionStorage.removeItem(candidateStorageKey);
        pollingTimer = null;
        setBusy(false);
        if (pendingLabel) pendingLabel.hidden = true;
        if (candidate.state === "ready") {
          showStatus(
            `Новая версия «${candidate.format_name || activeTemplate?.name || "итогов"}» проверена. Обновите экран, чтобы увидеть результат.`,
            "ready",
            [{ text: "Обновить экран", action: reloadAfterSummaryChange, primary: true }],
          );
          return;
        }
        if (candidate.state === "accepted") {
          showStatus("Итоги обновлены. Обновляем экран.", "ready");
          window.setTimeout(reloadAfterSummaryChange, 0);
          return;
        }
        if (candidate.state === "expired") {
          const retry = retryCandidateAction(candidate) || {
            text: "Обновить страницу", action: () => window.location.reload(), primary: true
          };
          showStatus("Новая версия устарела. Текущие итоги сохранены — запустите обновление ещё раз.", "failed", [
            retry
          ]);
          return;
        }
        if (candidate.state === "stale") {
          const retry = retryCandidateAction(candidate) || {
            text: "Обновить страницу", action: () => window.location.reload(), primary: true
          };
          showStatus("Расшифровка изменилась, поэтому новая версия закрыта. Текущие итоги сохранены.", "failed", [
            retry
          ]);
          return;
        }
        if (candidate.state === "blocked") {
          const retry = retryCandidateAction(candidate) || {
            text: "Обновить страницу", action: () => window.location.reload(), primary: true
          };
          showStatus("Сервис генерации временно недоступен. Текущие итоги сохранены.", "failed", [
            retry
          ]);
          return;
        }
        if (candidate.state === "closed") {
          const retry = retryCandidateAction(candidate) || {
            text: "Обновить страницу", action: () => window.location.reload(), primary: true
          };
          showStatus("Вариант закрыт, текущие итоги сохранены.", "failed", [
            retry
          ]);
          return;
        }
        const retry = retryCandidateAction(candidate) || {
          text: "Обновить страницу", action: () => window.location.reload(), primary: true
        };
        showStatus("Не удалось подготовить новый вариант. Текущие итоги сохранены.", "failed", [retry]);
        return true;
      };
      const schedulePoll = (candidate, generation = candidateRequestGeneration) => {
        if (generation !== candidateRequestGeneration || !controls.isConnected) return;
        window.clearTimeout(pollingTimer);
        pollingTimer = null;
        if (document.hidden) {
          setBusy(false);
          showStatus("Проверка приостановлена в фоне. Она продолжится при возвращении.", "generating", [
            { text: "Продолжить", action: () => resumeCandidatePolling(candidate, generation), primary: true }
          ]);
          return;
        }
        if (pollAttempts >= 40 || (pollDeadline && Date.now() >= pollDeadline)) {
          pollDelay = 15000;
          showStatus("Подготовка занимает больше обычного. Продолжим проверять автоматически.", "slow");
        }
        pollingTimer = window.setTimeout(() => {
          pollingTimer = null;
          pollCandidate(candidate, generation);
        }, pollDelay);
      };
      const pollCandidate = async (candidate, generation = candidateRequestGeneration) => {
        if (generation !== candidateRequestGeneration || !controls.isConnected) return;
        if (document.hidden) {
          pollingTimer = null;
          setBusy(false);
          showStatus("Проверка приостановлена в фоне. Она продолжится при возвращении.", "generating", [
            { text: "Продолжить", action: () => resumeCandidatePolling(candidate, generation), primary: true }
          ]);
          return;
        }
        pollAttempts += 1;
        try {
          const response = await fetch(candidate.poll_url, { credentials: "same-origin", cache: "no-store" });
          if (generation !== candidateRequestGeneration || !controls.isConnected) return;
          if (await recoverMeetingDetailFromResponse(response, { actionProblemCodes: summaryActionProblemCodes })) {
            throw meetingDetailRecoveredError();
          }
          if (!response.ok) {
            const payload = await response.json().catch(() => ({}));
            const error = new Error(payload.code || (response.status === 404
              ? "summary_candidate_not_found"
              : "summary_poll_failed"));
            error.status = response.status;
            throw error;
          }
          const next = await response.json();
          if (generation !== candidateRequestGeneration || !controls.isConnected) return;
          renderCandidate(next, generation);
          if (next.state === "generating") {
            pollDelay = Math.min(10000, Math.round(pollDelay * 1.5));
            schedulePoll(next, generation);
          }
        } catch (error) {
          if (isMeetingDetailRecoveredError(error)) return;
          if (generation !== candidateRequestGeneration || !controls.isConnected) return;
          pollingTimer = null;
          setBusy(false);
          const code = error instanceof Error ? error.message : "";
          const transientPollFailure = !code
            || error instanceof TypeError
            || code === "summary_poll_failed"
            || code === "summary_poll_unavailable"
            || code === "summary_request_unavailable"
            || error?.status >= 500
            || [408, 425, 429].includes(error?.status);
          const retry = transientPollFailure
            ? {
                text: "Проверить снова",
                action: () => resumeCandidatePolling(candidate, generation),
                primary: true
              }
            : retryTerminalCandidateAction(code);
          showStatus(
            transientPollFailure
              ? "Не удалось обновить новый вариант. Текущие итоги сохранены."
              : candidateErrorCopy(code),
            "failed",
            retry ? [retry] : []
          );
          if (transientPollFailure) {
            pollDelay = 15000;
            schedulePoll(candidate, generation);
          }
        }
      };
      const requestCandidate = async (template, {
        requestIntent = "manual_format",
        requestIntentId = null
      } = {}) => {
        if (!template || !meetingId) return;
        const generation = ++candidateRequestGeneration;
        candidateRequestInFlightGeneration = generation;
        activeTemplate = template;
        activeRequestIntent = requestIntent;
        activeRequestIntentId = requestIntentId;
        const currentTemplateKey = controls.dataset.currentTemplateKey || "";
        const currentTemplateVersion = Number(controls.dataset.currentTemplateVersion || "1");
        if (
          requestIntent === "manual_format"
          && template.key === currentTemplateKey
          && template.version === currentTemplateVersion
        ) {
          candidateRequestInFlightGeneration = null;
          setBusy(false);
          showStatus(
            "Этот формат уже выбран. Нажмите «Обновить итоги», чтобы создать новый вариант.",
            "ready",
            [{
              text: "Обновить итоги",
              action: () => requestCurrentRefresh(),
              primary: true
            }]
          );
          return;
        }
        setBusy(true);
        if (pendingLabel) {
          pendingLabel.hidden = false;
          pendingLabel.textContent = `Готовим вариант: ${template.name}`;
        }
        showStatus(`Готовим формат «${template.name}». Текущие итоги остаются доступны.`);
        try {
          const expectedCurrentOutcomeSetId = await currentOutcomeSetIdForTemplate(template);
          const body = {
            template_key: template.key,
            template_id: template.id || null,
            template_version: template.version,
            expected_current_outcome_set_id: expectedCurrentOutcomeSetId,
            request_intent: requestIntent
          };
          if (requestIntentId) body.request_intent_id = requestIntentId;
          const candidate = await mutate(
            `/api/v1/cabinet/meetings/${meetingId}/summary-candidates`,
            "POST",
            body
          );
          if (candidate.state === "generating") {
            pollAttempts = 0;
            pollDeadline = Date.now() + 5 * 60 * 1000;
            pollDelay = 1500;
          }
          if (generation !== candidateRequestGeneration) return;
          renderCandidate(candidate, generation);
          if (candidate.state === "generating") schedulePoll(candidate, generation);
        } catch (error) {
          if (isMeetingDetailRecoveredError(error)) return;
          if (generation !== candidateRequestGeneration) return;
          setBusy(false);
          if (pendingLabel) pendingLabel.hidden = true;
          const code = error instanceof Error ? error.message : "";
          const retry = code === "summary_template_unavailable"
            ? retryCandidateAction(code)
            : candidateErrorAction(code, activeTemplate, error)
              || { text: "Обновить страницу", action: () => window.location.reload(), primary: true };
          showStatus(candidateErrorCopy(code), "failed", [retry]);
        } finally {
          if (generation === candidateRequestGeneration) candidateRequestInFlightGeneration = null;
        }
      };
      const currentTemplate = async () => {
        const key = controls.dataset.currentTemplateKey || "";
        const version = Number(controls.dataset.currentTemplateVersion || "1");
        const name = controls.dataset.currentTemplateName || "итогов";
        const local = options().find((option) => option.dataset.templateKey === key);
        if (local) return templateFrom(local);
        try {
          const response = await fetch("/api/v1/cabinet/summary-templates", {
            credentials: "same-origin",
            cache: "no-store"
          });
          if (response.ok) {
            const payload = await response.json();
            const template = [...(payload.recommended || []), ...(payload.personal || [])]
              .find((candidate) => candidate.template_key === key);
            if (template) {
              return {
                id: template.template_id || null,
                key: template.template_key,
                version: Number(template.version),
                name: template.name
              };
            }
          }
        } catch (_error) {
          // The picker still provides active alternatives when refresh lookup fails.
        }
        return { id: controls.dataset.currentTemplateId || null, key, version, name };
      };
      const currentOutcomeSetIdForTemplate = async (template) => {
        if (!template?.key) return null;
        const currentKey = controls.dataset.currentTemplateKey || "";
        const currentVersion = Number(controls.dataset.currentTemplateVersion || "1");
        if (template.key === currentKey && template.version === currentVersion) {
          return currentOutcomeSetId;
        }
        const response = await fetch(
          `/api/v1/cabinet/meetings/${meetingId}/summaries/${encodeURIComponent(template.key)}`,
          { credentials: "same-origin", cache: "no-store" }
        );
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          const error = new Error(payload.code || "summary_poll_unavailable");
          error.status = response.status;
          throw error;
        }
        return payload.current_outcome_set_id || null;
      };
       const pollSummaryRefresh = async (template, generation) => {
        if (generation !== candidateRequestGeneration || !controls.isConnected) return;
        if (document.hidden) {
          pollingTimer = window.setTimeout(() => pollSummaryRefresh(template, generation), 15000);
          return;
        }
        try {
          const response = await fetch(
            `/api/v1/cabinet/meetings/${meetingId}/summaries/${encodeURIComponent(template.key)}`,
            { credentials: "same-origin", cache: "no-store" }
          );
          if (generation !== candidateRequestGeneration || !controls.isConnected) return;
          if (await recoverMeetingDetailFromResponse(response, { actionProblemCodes: summaryActionProblemCodes })) {
            throw meetingDetailRecoveredError();
          }
          const payload = await response.json().catch(() => ({}));
          if (!response.ok) {
            const error = new Error(payload.code || "summary_poll_unavailable");
            error.status = response.status;
            throw error;
          }
          if (generation !== candidateRequestGeneration || !controls.isConnected) return;
          currentOutcomeSetId = payload.current_outcome_set_id || currentOutcomeSetId;
          const state = payload.catalog_entry?.generation_state;
          if (["preparing", "updating", "blocked", "deferred"].includes(state)) {
            showStatus("Обновляем итоги. Текущие итоги остаются доступны.");
            pollingTimer = window.setTimeout(() => pollSummaryRefresh(template, generation), Date.now() > pollDeadline ? 15000 : 3000);
            return;
          }
          pollingTimer = null;
          candidateRequestInFlightGeneration = null;
          setBusy(false);
          if (payload.current_outcome_set_id && payload.current_outcome_set_id !== refreshBaselineOutcomeSetId && state === "idle") {
            showStatus("Итоги обновлены. Обновляем экран.", "ready");
            window.setTimeout(() => reloadAfterSummaryChange(template), 0);
          } else {
            showStatus("Обновление не завершено. Текущие итоги сохранены.", "failed", [
              { text: "Обновить страницу", action: () => window.location.reload(), primary: true }
            ]);
          }
        } catch (error) {
          if (isMeetingDetailRecoveredError(error) || generation !== candidateRequestGeneration || !controls.isConnected) return;
          if (error instanceof TypeError || !error.status || error.status >= 500 || [408, 425, 429].includes(error.status)) {
            showStatus("Связь временно недоступна. Продолжим проверять автоматически.", "slow");
            pollingTimer = window.setTimeout(() => pollSummaryRefresh(template, generation), 15000);
            return;
          }
          pollingTimer = null;
          candidateRequestInFlightGeneration = null;
          setBusy(false);
          const code = error instanceof Error ? error.message : "summary_poll_unavailable";
          showStatus(candidateErrorCopy(code), "failed", [
            { text: "Обновить страницу", action: () => window.location.reload(), primary: true }
          ]);
        }
      };
      const requestSummaryRefresh = async (template, requestIntentId, generation) => {
        if (!template?.key || generation !== candidateRequestGeneration) return;
        activeTemplate = template;
        activeRequestIntent = "manual_refresh";
        activeRequestIntentId = requestIntentId;
        setBusy(true);
        showStatus("Обновляем итоги. Текущие итоги остаются доступны.");
        try {
          refreshBaselineOutcomeSetId = await currentOutcomeSetIdForTemplate(template);
          if (generation !== candidateRequestGeneration || !controls.isConnected) return;
          const payload = await mutate(
            `/api/v1/cabinet/meetings/${meetingId}/summaries/${encodeURIComponent(template.key)}/refresh`,
            "POST",
            {
              schema_version: 1,
              idempotency_key: requestIntentId,
              expected_current_outcome_set_id: refreshBaselineOutcomeSetId,
              template_id: template.id || null,
              template_version: template.version,
              generation_options: {}
            }
          );
          if (generation !== candidateRequestGeneration) return;
          currentOutcomeSetId = payload.current_outcome_set_id || currentOutcomeSetId;
          pollAttempts = 0;
          pollDeadline = Date.now() + 5 * 60 * 1000;
          pollDelay = 1200;
          showStatus("Обновляем итоги. Текущие итоги остаются доступны.");
          pollingTimer = window.setTimeout(() => pollSummaryRefresh(template, generation), pollDelay);
        } catch (error) {
          if (isMeetingDetailRecoveredError(error) || generation !== candidateRequestGeneration) return;
          setBusy(false);
          candidateRequestInFlightGeneration = null;
          const code = error instanceof Error ? error.message : "summary_request_unavailable";
          showStatus(candidateErrorCopy(code), "failed", [
            { text: "Обновить страницу", action: () => window.location.reload(), primary: true }
          ]);
        }
       };
      const requestCurrentRefresh = async () => {
        // Invalidate an in-flight history load before resolving the current template.
        const refreshGeneration = ++candidateRequestGeneration;
        candidateRequestInFlightGeneration = refreshGeneration;
        const template = await currentTemplate();
        if (refreshGeneration !== candidateRequestGeneration) return;
        if (!template.key) {
          candidateRequestInFlightGeneration = null;
          openFormatPicker();
          return;
        }
        await requestSummaryRefresh(template, newRequestIntentId(), refreshGeneration);
      };
      const newRequestIntentId = () => typeof window.crypto?.randomUUID === "function"
          ? window.crypto.randomUUID()
          : (() => {
              const bytes = new Uint8Array(16);
              if (typeof window.crypto?.getRandomValues === "function") {
                window.crypto.getRandomValues(bytes);
              } else {
                for (let index = 0; index < bytes.length; index += 1) {
                  bytes[index] = Math.floor(Math.random() * 256);
                }
              }
              bytes[6] = (bytes[6] & 0x0f) | 0x40;
              bytes[8] = (bytes[8] & 0x3f) | 0x80;
              const hex = [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
              return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
            })();
      const requestTemplateVariant = (template) => requestCandidate(template, {
        requestIntent: "manual_refresh",
        requestIntentId: newRequestIntentId()
      });
      refreshButton?.addEventListener("click", requestCurrentRefresh);
      document.addEventListener("visibilitychange", () => {
        if (!document.hidden && pollingTimer === null && candidateRequestInFlightGeneration === null) {
          const stored = window.sessionStorage.getItem(candidateStorageKey);
          if (!stored) return;
          try {
            const resumed = JSON.parse(stored);
            if (resumed?.poll_url) {
              activeTemplate = resumed.template?.key && Number.isInteger(resumed.template?.version)
                ? resumed.template
                : null;
              activeRequestIntent = resumed.requestIntent || "manual_format";
              activeRequestIntentId = resumed.requestIntentId || null;
              pollAttempts = Number(resumed.pollAttempts || 0);
              pollDeadline = Number(resumed.pollDeadline || (Date.now() + 5 * 60 * 1000));
              pollDelay = Number(resumed.pollDelay || 1500);
              setBusy(true);
              schedulePoll({ poll_url: resumed.poll_url }, candidateRequestGeneration);
            }
          } catch (_error) {
            // The normal request path will recreate the durable candidate state.
          }
        }
      });
      const isCurrentFormat = (template) => {
        if (!template || !currentOutcomeSetId) return false;
        const currentKey = controls.dataset.currentSummaryFormatKey || "";
        if (currentKey !== template.key) return false;
        const currentTemplateId = controls.dataset.currentSummaryFormatTemplateId || "";
        const currentVersion = Number(controls.dataset.currentSummaryFormatVersion || "0");
        if (template.id) {
          return Boolean(currentTemplateId)
            && currentTemplateId === template.id
            && currentVersion === template.version;
        }
        return currentVersion === template.version;
      };
      const showCurrentFormatAction = (template) => {
        activeTemplate = template;
        showStatus(
          "Этот формат уже выбран. Если хотите обновить итоги, создайте новый вариант.",
          "ready",
          [{
            text: "Создать новый вариант",
            action: () => requestCurrentRefresh(),
            primary: true
          }]
        );
      };
      const templateFrom = (option) => ({
        id: option.dataset.templateId || null,
        key: option.dataset.templateKey,
        version: Number(option.dataset.templateVersion || "1"),
        name: option.dataset.templateName || option.textContent.trim()
      });
      const personalFormatOption = (template) => {
        const option = document.createElement("button");
        const safeName = typeof template.name === "string" && template.name.trim()
          ? template.name.trim()
          : "Личный формат";
        option.type = "button";
        option.tabIndex = -1;
        option.setAttribute("role", "option");
        option.setAttribute("aria-describedby", "summary-format-description");
        option.dataset.summaryFormatOption = "";
        option.dataset.templateId = template.template_id || "";
        option.dataset.templateKey = template.template_key || "";
        option.dataset.templateVersion = String(Number(template.version) || 1);
        option.dataset.templateName = safeName;
        option.dataset.templatePurpose = typeof template.purpose === "string" && template.purpose.trim()
          ? template.purpose.trim() : "Личный формат итогов";
        const icon = document.createElement("span");
        icon.className = "summary-format-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = "▤";
        const name = document.createElement("span");
        name.className = "summary-format-name";
        name.textContent = safeName;
        const marker = document.createElement("span");
        marker.className = "summary-format-check";
        marker.setAttribute("aria-hidden", "true");
        marker.textContent = "✓";
        option.append(icon, name, marker);
        option.setAttribute("aria-selected", isCurrentFormat(templateFrom(option)) ? "true" : "false");
        return option;
      };
      const loadPersonalFormats = async () => {
        if (!personalHost || personalLoading || personalLoaded) return;
        personalLoading = true;
        if (loadStatus) {
          loadStatus.textContent = "Загружаем личные форматы…";
          loadStatus.hidden = false;
        }
        try {
          const response = await fetch("/api/v1/cabinet/summary-templates", { credentials: "same-origin", cache: "no-store" });
          if (!response.ok) throw new Error("personal_formats_unavailable");
          const templates = await response.json();
          if (!controls.isConnected) return;
          const personal = Array.isArray(templates.personal) ? templates.personal : [];
          personalHost.replaceChildren(...personal.filter((template) => template && typeof template === "object").map(personalFormatOption));
          personalHost.hidden = !back || back.hidden || !personalHost.children.length;
          personalLoaded = true;
          if (loadStatus) { loadStatus.textContent = ""; loadStatus.hidden = true; }
        } catch (_error) {
          if (!controls.isConnected || !loadStatus) return;
          loadStatus.textContent = "Личные форматы не загрузились. Откройте «Все форматы» ещё раз или перейдите в настройки.";
          loadStatus.hidden = !back || back.hidden;
        } finally {
          personalLoading = false;
          if (controls.isConnected) sizePopover();
        }
      };
      const applyServerCandidate = (candidate) => {
        currentOutcomeSetId = candidate.current_outcome_set_id || currentOutcomeSetId;
        activeTemplate = templateFromCandidate(candidate);
        renderCandidate(candidate);
        if (candidate.state === "generating") {
          pollingTimer = window.setTimeout(() => pollCandidate(candidate), 1200);
        }
      };
      button.addEventListener("click", () => popover.hidden ? open() : close());
      info?.addEventListener("toggle", () => {
        if (info.open) close({ restoreFocus: false });
      });
      controls.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        if (info?.open) {
          event.preventDefault();
          event.stopPropagation();
          info.open = false;
          info.querySelector("summary")?.focus({ preventScroll: true });
        } else if (!popover.hidden) {
          event.preventDefault();
          event.stopPropagation();
          close();
        }
      });
      button.addEventListener("keydown", (event) => {
        if (!["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        open();
        const items = visibleOptions();
        const target = event.key === "ArrowUp" || event.key === "End"
          ? items[items.length - 1]
          : items[0];
        focusOption(target);
      });
      listbox.addEventListener("keydown", (event) => {
        const option = event.target.closest?.('[role="option"]');
        if (!option) return;
        if (!["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        const items = visibleOptions();
        const current = items.indexOf(option);
        const next = event.key === "Home" ? 0
          : event.key === "End" ? items.length - 1
          : (current + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
        focusOption(items[next]);
      });
      listbox.addEventListener("click", (event) => {
        const option = event.target.closest?.("[data-summary-format-option]");
        if (!option || option.disabled || button.disabled || option.closest("[hidden]")) return;
        close();
        const template = templateFrom(option);
        if (isCurrentFormat(template)) {
          showCurrentFormatAction(template);
          return;
        }
        requestTemplateVariant(template);
      });
      popover.addEventListener("pointerdown", (event) => {
        const target = event.target.closest?.("button, a");
        if (!target || target.disabled || event.button !== 0) return;
        // WebKit does not focus buttons on click; keep the menu focus inside until selection.
        event.preventDefault();
        target.focus({ preventScroll: true });
      });
      allFormats?.addEventListener("click", openFormatPicker);
      back?.addEventListener("click", () => open());
      const describeOption = (event) => {
        const option = event.target.closest?.("[data-summary-format-option]");
        if (!option || !description) return;
        description.textContent = option.dataset.templatePurpose || "Личный формат итогов";
        if (event.type === "focusin") {
          options().forEach((item) => { item.tabIndex = item === option ? 0 : -1; });
        }
      };
      listbox.addEventListener("focusin", describeOption);
      listbox.addEventListener("mouseover", describeOption);
      controls.addEventListener("focusout", () => {
        window.setTimeout(() => {
          if (!popover.hidden && !popover.contains(document.activeElement) && document.activeElement !== button) close({ restoreFocus: false });
        }, 0);
      });
      window.addEventListener("resize", sizePopover);
      document.addEventListener("scroll", sizePopover, true);
      document.addEventListener("click", (event) => {
        if (!popover.hidden && event.target instanceof Node && !controls.contains(event.target)) {
          close({ restoreFocus: false });
        }
        if (info?.open && event.target instanceof Node && !info.contains(event.target)) info.open = false;
      });
      const resumeCandidate = window.sessionStorage.getItem(candidateStorageKey);
      const resumeCachedCandidate = () => {
        if (!resumeCandidate) return false;
        let resumed = { poll_url: resumeCandidate, template: null };
        try {
          const stored = JSON.parse(resumeCandidate);
          if (stored && typeof stored.poll_url === "string") resumed = stored;
        } catch (_error) {
          // A pre-121 URL-only value can still be polled; server state remains authoritative.
        }
        activeTemplate = resumed.template || null;
        activeRequestIntent = resumed.requestIntent || "manual_format";
        activeRequestIntentId = resumed.requestIntentId || null;
        pollAttempts = Number(resumed.pollAttempts || 0);
        pollDeadline = Number(resumed.pollDeadline || (Date.now() + 5 * 60 * 1000));
        pollDelay = Number(resumed.pollDelay || 1500);
        setBusy(true);
        showStatus("Проверяем новую версию. Текущие итоги остаются доступны.");
        pollCandidate({ poll_url: resumed.poll_url });
        return true;
      };
      const initialCandidateLoadGeneration = candidateRequestGeneration;
      const showCandidateHistoryFailure = () => showStatus(
        "Не удалось проверить сохранённые варианты. Текущие итоги доступны.",
        "attention",
        [{ text: "Повторить", action: () => window.location.reload(), primary: true }]
      );
      fetch(`/api/v1/cabinet/meetings/${meetingId}/summary-candidates`, {
        credentials: "same-origin",
        cache: "no-store"
      }).then((response) => response.ok ? response.json() : null).then((payload) => {
        if (initialCandidateLoadGeneration !== candidateRequestGeneration || !controls.isConnected) return;
        const candidates = Array.isArray(payload) ? payload : (Array.isArray(payload?.candidates) ? payload.candidates : []);
        const acceptedIndex = candidates.findIndex((candidate) => (
          candidate.state === "accepted"
          && candidate.outcome_set_id
          && candidate.outcome_set_id === candidate.current_outcome_set_id
        ));
        const current = candidates.find((candidate, index) => [
          "generating", "ready", "blocked"
        ].includes(candidate.state) || (
          ["failed", "stale", "expired"].includes(candidate.state)
          && (acceptedIndex < 0 || index < acceptedIndex)
        ));
        if (current) {
          window.clearTimeout(pollingTimer);
          applyServerCandidate(current);
          return;
        }
        const latestFailure = candidates.find((candidate) => candidate.state === "failed");
        if (latestFailure) {
          applyServerCandidate(latestFailure);
          return;
        }
        if (!resumeCachedCandidate() && payload === null) {
          showCandidateHistoryFailure();
        }
      }).catch(() => {
        if (!resumeCachedCandidate()) {
          showCandidateHistoryFailure();
        }
      });
      if (window.sessionStorage.getItem(acceptedFocusKey) === "current") {
        window.sessionStorage.removeItem(acceptedFocusKey);
        window.requestAnimationFrame(() => {
          activateDetailTab("outcomes");
          document.querySelector("[data-summary-current-result]")?.focus({ preventScroll: false });
        });
      }
    });
  };

  const initSummaryTemplateSettings = () => {
    document.querySelectorAll("[data-summary-template-settings]").forEach((settings) => {
      if (settings.dataset.summaryTemplateReady === "true") return;
      settings.dataset.summaryTemplateReady = "true";
      const endpoint = settings.dataset.templateEndpoint;
      const defaultEndpoint = settings.dataset.summaryDefaultEndpoint;
      const defaultSelect = settings.querySelector("[data-summary-default-template]");
      const defaultHelp = settings.querySelector("[data-summary-default-help]");
      const list = settings.querySelector("[data-summary-personal-template-list]");
      const status = settings.querySelector("[data-summary-template-settings-status]");
      const dialog = settings.querySelector("[data-summary-template-dialog]");
      const form = dialog?.querySelector("[data-summary-template-form]");
      const error = dialog?.querySelector("[data-summary-template-form-error]");
      const title = dialog?.querySelector("[data-summary-template-dialog-title]");
      let editingTemplate = null;
      let returnFocus = null;
      let canManageDefault = false;
      const setStatus = (message) => { if (status) status.textContent = message; };
      const setError = (message = "") => {
        if (!error) return;
        error.textContent = message;
        error.hidden = !message;
        if (message) error.focus({ preventScroll: true });
      };
      const request = async (url, method = "GET", body) => {
        const response = await fetch(url, {
          method,
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            ...(body === undefined ? {} : { "Content-Type": "application/json" }),
            ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {})
          },
          body: body === undefined ? undefined : JSON.stringify(body)
        });
        const payload = response.status === 204 ? null : await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload?.code || "summary_template_request_failed");
        return payload;
      };
      const closeDialog = () => {
        if (!(dialog instanceof HTMLDialogElement)) return;
        dialog.close();
        if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
        returnFocus = null;
      };
      const setSections = (sections) => {
        form?.querySelectorAll('input[name="sections"]').forEach((input) => {
          input.checked = sections.includes(input.value);
        });
      };
      const openEditor = (trigger, template = null) => {
        if (!(dialog instanceof HTMLDialogElement) || !form) return;
        returnFocus = trigger;
        editingTemplate = template?.template_id ? template : null;
        form.reset();
        setError();
        const name = form.elements.namedItem("name");
        const purpose = form.elements.namedItem("purpose");
        const language = form.elements.namedItem("output_language");
        const detail = form.elements.namedItem("detail_level");
        if (title) title.textContent = editingTemplate ? "Изменить формат" : "Новый формат";
        if (template) {
          if (name) name.value = editingTemplate ? template.name : `${template.name} — копия`.slice(0, 80);
          if (purpose) purpose.value = template.purpose;
          if (language) language.value = template.output_language || "ru";
          if (detail) detail.value = template.detail_level || "standard";
          setSections(template.sections || ["summary", "action_items"]);
        }
        dialog.showModal();
        name?.focus({ preventScroll: true });
      };
      const templateErrorCopy = (code) => ({
        summary_template_conflict: "Формат уже изменился. Обновите список и повторите.",
        summary_template_limit: "Достигнут лимит личных форматов.",
        summary_template_not_found: "Формат больше недоступен."
      }[code] || "Не удалось сохранить формат. Проверьте поля и попробуйте снова.");
      const mutateTemplate = async (template, action) => {
        try {
          setStatus("Сохраняем…");
          if (action === "duplicate") {
            await request(`${endpoint}/${template.template_id}/duplicate`, "POST");
          } else if (action === "archive") {
            await request(`${endpoint}/${template.template_id}/archive`, "POST");
          } else if (action === "delete") {
            if (!window.confirm(`Удалить формат «${template.name}»? Старые итоги встреч сохранятся.`)) return;
            await request(`${endpoint}/${template.template_id}`, "DELETE");
          }
          await loadTemplates();
          setStatus(action === "duplicate" ? "Копия создана." : action === "archive" ? "Формат скрыт." : "Формат удалён.");
        } catch (requestError) {
          setStatus(templateErrorCopy(requestError instanceof Error ? requestError.message : ""));
        }
      };
      const renderTemplates = (templates) => {
        if (!list) return;
        if (!templates.length) {
          const empty = document.createElement("p");
          empty.className = "muted";
          empty.textContent = "Личных форматов пока нет.";
          list.replaceChildren(empty);
          return;
        }
        list.replaceChildren(...templates.map((template) => {
          const row = document.createElement("article");
          row.className = "summary-template-row";
          const copy = document.createElement("div");
          const name = document.createElement("strong");
          const purpose = document.createElement("span");
          purpose.className = "muted";
          name.textContent = template.name;
          purpose.textContent = template.purpose;
          copy.append(name, purpose);
          const actions = document.createElement("details");
          actions.className = "summary-template-actions";
          const summary = document.createElement("summary");
          summary.textContent = "Действия";
          summary.setAttribute("aria-label", `Действия с форматом «${template.name}»`);
          actions.append(summary);
          [
            ["Изменить", () => openEditor(actions.querySelector("button"), template)],
            ["Копировать", () => mutateTemplate(template, "duplicate")],
            ["Скрыть", () => mutateTemplate(template, "archive")],
            ["Удалить", () => mutateTemplate(template, "delete")]
          ].forEach(([text, handler]) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "button quiet";
            button.textContent = text;
            button.addEventListener("click", handler);
            actions.append(button);
          });
          row.append(copy, actions);
          return row;
        }));
      };
      const loadTemplates = async () => {
        try {
          const payload = await request(endpoint);
          const personal = payload.personal || [];
          renderTemplates(personal);
          if (defaultSelect) {
            canManageDefault = payload.can_manage_default === true;
            defaultSelect.querySelectorAll("option[data-personal-template]").forEach((option) => option.remove());
            personal.forEach((template) => {
              const option = document.createElement("option");
              option.value = template.template_key;
              option.textContent = `${template.name} — личный`;
              option.dataset.personalTemplate = "";
              option.dataset.templateId = template.template_id;
              option.dataset.templateVersion = String(template.version);
              defaultSelect.append(option);
            });
            defaultSelect.value = payload.default_template_key;
            defaultSelect.disabled = !canManageDefault;
          }
          if (defaultHelp) {
            defaultHelp.textContent = payload.can_manage_default
              ? "Используется для новых итогов, если формат встречи не выбран отдельно."
              : "Изменить может владелец пространства.";
          }
        } catch (_error) {
          setStatus("Личные форматы не загрузились. Повторите попытку.");
          if (list) {
            list.replaceChildren();
            const message = document.createElement("p");
            message.className = "muted";
            message.textContent = "Не удалось загрузить личные форматы.";
            const retry = document.createElement("button");
            retry.type = "button";
            retry.className = "button quiet";
            retry.textContent = "Повторить";
            retry.addEventListener("click", () => {
              setStatus("Загружаем личные форматы…");
              loadTemplates();
            });
            list.append(message, retry);
          }
        }
      };
      defaultSelect?.addEventListener("change", async () => {
        const option = defaultSelect.selectedOptions[0];
        if (!option || !defaultEndpoint) return;
        defaultSelect.disabled = true;
        setStatus("Сохраняем формат по умолчанию…");
        try {
          await request(defaultEndpoint, "PUT", {
            template_key: option.value,
            template_id: option.dataset.templateId || null,
            template_version: Number(option.dataset.templateVersion || "1")
          });
          setStatus("Формат по умолчанию обновлён.");
        } catch (requestError) {
          setStatus(templateErrorCopy(requestError instanceof Error ? requestError.message : ""));
          await loadTemplates();
        } finally {
          if (defaultSelect) defaultSelect.disabled = !canManageDefault;
        }
      });
      settings.querySelector("[data-summary-template-create]")?.addEventListener("click", (event) => {
        openEditor(event.currentTarget);
      });
      settings.querySelectorAll("[data-summary-template-copy]").forEach((button) => {
        button.addEventListener("click", () => {
          const row = button.closest("[data-summary-template-built-in]");
          openEditor(button, {
            name: row.dataset.templateName,
            purpose: row.dataset.templatePurpose,
            sections: (row.dataset.templateSections || "").split(",").filter(Boolean),
            output_language: "ru",
            detail_level: "standard"
          });
        });
      });
      dialog?.querySelectorAll("[data-summary-template-dialog-close], [data-summary-template-dialog-cancel]").forEach((button) => {
        button.addEventListener("click", closeDialog);
      });
      dialog?.addEventListener("cancel", (event) => {
        event.preventDefault();
        closeDialog();
      });
      dialog?.addEventListener("click", (event) => {
        if (event.target === dialog) closeDialog();
      });
      dialog?.addEventListener("keydown", (event) => trapModalFocus(dialog, event));
      form?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const data = new FormData(form);
        const sections = data.getAll("sections");
        if (!sections.length) {
          setError("Выберите хотя бы один раздел.");
          return;
        }
        const payload = {
          name: String(data.get("name") || "").trim(),
          purpose: String(data.get("purpose") || "").trim(),
          sections,
          output_language: String(data.get("output_language") || "ru"),
          detail_level: String(data.get("detail_level") || "standard"),
          ...(editingTemplate ? { expected_version: editingTemplate.version } : {})
        };
        const submit = form.querySelector("[data-summary-template-submit]");
        if (submit) submit.disabled = true;
        try {
          await request(
            editingTemplate ? `${endpoint}/${editingTemplate.template_id}` : endpoint,
            editingTemplate ? "PATCH" : "POST",
            payload
          );
          closeDialog();
          await loadTemplates();
          setStatus(editingTemplate ? "Формат обновлён." : "Формат создан.");
        } catch (requestError) {
          setError(templateErrorCopy(requestError instanceof Error ? requestError.message : ""));
        } finally {
          if (submit) submit.disabled = false;
        }
      });
      loadTemplates();
    });
  };

  const initMeetingContextPanels = () => {
    const triggers = Array.from(document.querySelectorAll("[data-meeting-panel-open]"));
    const panels = Array.from(document.querySelectorAll("[data-meeting-context-panel]"));
    if (!triggers.length || !panels.length) return;
    const triggerFor = (panel) => triggers.find(
      (trigger) => trigger.dataset.meetingPanelOpen === panel.dataset.meetingContextPanel
    );
    const panelIsOpen = (panel) => panel instanceof HTMLDialogElement ? panel.open : !panel.hidden;
    const menuItems = (panel) => Array.from(panel.querySelectorAll('[role="menuitem"]'))
      .filter((item) => isUsableFocusTarget(item) && !item.matches(":disabled"));
    const focusMenuItem = (panel, index) => {
      const items = menuItems(panel);
      if (!items.length) return;
      items[(index + items.length) % items.length].focus({ preventScroll: true });
    };
    const closePanel = (panel, restoreFocus = false) => {
      if (panel instanceof HTMLDialogElement) {
        if (panel.open) panel.close();
      } else {
        panel.hidden = true;
      }
      const trigger = triggerFor(panel);
      if (trigger?.getAttribute("aria-haspopup") === "menu") trigger.setAttribute("aria-expanded", "false");
      if (restoreFocus) restoreMeetingActionFocus(trigger);
    };
    const closePanels = () => panels.forEach((panel) => closePanel(panel));
    const openPanel = (panel, edge = 0) => {
      closePanels();
      const trigger = triggerFor(panel);
      if (trigger?.getAttribute("aria-haspopup") === "menu") trigger.setAttribute("aria-expanded", "true");
      if (panel instanceof HTMLDialogElement && typeof panel.showModal === "function") {
        panel.showModal();
        modalFocusTargets(panel)[0]?.focus({ preventScroll: true });
      } else {
        panel.hidden = false;
        focusMenuItem(panel, edge);
      }
    };
    triggers.forEach((trigger) => {
      if (trigger.dataset.meetingPanelReady === "true") return;
      trigger.dataset.meetingPanelReady = "true";
      const panel = panels.find((candidate) => candidate.dataset.meetingContextPanel === trigger.dataset.meetingPanelOpen);
      if (!panel) return;
      trigger.addEventListener("click", () => {
        if (panelIsOpen(panel)) {
          closePanel(panel, true);
          return;
        }
        openPanel(panel);
      });
      if (trigger.getAttribute("role") !== "menuitem") {
        trigger.addEventListener("keydown", (event) => {
          if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
          event.preventDefault();
          openPanel(panel, event.key === "ArrowUp" ? -1 : 0);
        });
      }
      if (!(panel instanceof HTMLDialogElement) || panel.dataset.meetingDialogReady === "true") return;
      panel.dataset.meetingDialogReady = "true";
      panel.querySelector("[data-meeting-panel-close]")?.addEventListener("click", () => closePanel(panel, true));
      panel.addEventListener("cancel", (event) => {
        event.preventDefault();
        closePanel(panel, true);
      });
      panel.addEventListener("click", (event) => {
        if (event.target === panel) closePanel(panel, true);
      });
      panel.addEventListener("keydown", (event) => trapModalFocus(panel, event));
    });
    panels.filter((panel) => panel.getAttribute("role") === "menu").forEach((panel) => {
      if (panel.dataset.meetingMenuReady === "true") return;
      panel.dataset.meetingMenuReady = "true";
      panel.addEventListener("keydown", (event) => {
        const item = event.target.closest?.('[role="menuitem"]');
        if (!item) return;
        const items = menuItems(panel);
        const current = items.indexOf(item);
        if (event.key === "Escape") {
          event.preventDefault();
          closePanel(panel, true);
        } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
          event.preventDefault();
          focusMenuItem(panel, current + (event.key === "ArrowDown" ? 1 : -1));
        } else if (event.key === "Home" || event.key === "End") {
          event.preventDefault();
          focusMenuItem(panel, event.key === "End" ? -1 : 0);
        }
      });
      panel.addEventListener("click", (event) => {
        const item = event.target.closest?.('[role="menuitem"]');
        if (!item) return;
        if (item.matches("a[href]")) {
          window.setTimeout(() => closePanel(panel), 0);
          return;
        }
        closePanel(panel);
      });
    });
    if (document.body.dataset.meetingPanelEscapeReady === "true") return;
    document.body.dataset.meetingPanelEscapeReady = "true";
    document.addEventListener("click", (event) => {
      const openPanel = panels.find((panel) => panel.getAttribute("role") === "menu" && panelIsOpen(panel));
      if (!openPanel || event.target.closest?.("[data-meeting-context-panel], [data-meeting-panel-open]")) return;
      const opensDestination = event.target.closest?.(
        "[data-share-dialog-open], [data-export-dialog-open], [data-meeting-delete-dialog-open]"
      );
      closePanel(openPanel, !opensDestination);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      const openPanel = panels.find((panel) => panel.getAttribute("role") === "menu" && panelIsOpen(panel));
      if (openPanel) closePanel(openPanel, true);
    });
  };

  const formatTime = (seconds) => {
    if (!Number.isFinite(seconds) || seconds < 0) return "00:00";
    const rounded = Math.floor(seconds);
    const minutes = Math.floor(rounded / 60);
    const rest = String(rounded % 60).padStart(2, "0");
    return `${String(minutes).padStart(2, "0")}:${rest}`;
  };

  const reportPlaybackFailure = (player) => {
    const shell = player?.closest?.("[data-playback-shell]");
    const playbackError = shell?.querySelector("[data-playback-error]");
    if (playbackError) playbackError.hidden = false;
    const toggle = shell?.querySelector("[data-playback-toggle]");
    if (!toggle) return;
    const playIcon = toggle.querySelector("[data-playback-play-icon]");
    const pauseIcon = toggle.querySelector("[data-playback-pause-icon]");
    if (playIcon) playIcon.hidden = false;
    if (pauseIcon) pauseIcon.hidden = true;
    toggle.setAttribute("aria-label", "Воспроизвести");
  };

  const scrollTranscriptTurnIntoView = (turn, behavior = "auto") => {
    const main = turn.closest(".detail-page-main");
    if (!main) { turn.scrollIntoView({ block: "center", behavior }); return; }
    const bounds = main.getBoundingClientRect();
    const header = main.querySelector("[data-meeting-detail-header]");
    const top = header && getComputedStyle(header).position === "sticky"
      ? Math.max(bounds.top, header.getBoundingClientRect().bottom) : bounds.top;
    const height = Math.max(0, bounds.bottom - top);
    const target = turn.getBoundingClientRect().height > height
      ? turn.querySelector(".text") || turn : turn;
    const rect = target.getBoundingClientRect();
    main.scrollTo({
      top: main.scrollTop + rect.top - top - Math.max(0, (height - rect.height) / 2),
      behavior,
    });
  };

  const initSourceNavigation = () => {
    if (document.body.dataset.sourceNavigationReady === "true") return;
    document.body.dataset.sourceNavigationReady = "true";
    let sourceReturnTarget = null;
    let sourceReturnScrollTop = 0;
    const clearSourceReturn = () => {
      sourceReturnTarget = null;
      const returnButton = document.querySelector("[data-source-return]");
      if (returnButton) returnButton.hidden = true;
    };
    document.addEventListener("keydown", (event) => {
      if (event.target.closest?.("[data-detail-tab]") && ["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) clearSourceReturn();
    });
    document.addEventListener("click", (event) => {
      if (event.target.closest?.("[data-detail-tab]")) clearSourceReturn();
      if (event.target.closest?.("[data-source-return]")) {
        const target = sourceReturnTarget;
        activateDetailTab("outcomes");
        clearSourceReturn();
        window.requestAnimationFrame(() => {
          if (!target?.isConnected) return;
          const main = target.closest(".detail-page-main");
          if (main) main.scrollTop = sourceReturnScrollTop;
          target.focus({ preventScroll: true });
        });
        return;
      }
      const control = event.target.closest?.("[data-seek-seconds]");
      if (!control) return;
      const seconds = Number.parseFloat(control.dataset.seekSeconds || "0");
      if (!Number.isFinite(seconds)) return;
      const sourceJump = control.hasAttribute("data-source-segment");
      if (sourceJump) {
        sourceReturnTarget = control;
        sourceReturnScrollTop = control.closest(".detail-page-main")?.scrollTop || 0;
        const returnButton = document.querySelector("[data-source-return]");
        if (returnButton) returnButton.hidden = false;
        activateDetailTab("recording");
      }
      const player = document.querySelector("[data-playback-player]");
      if (player) {
        try {
          player.currentTime = Math.max(0, seconds);
          void player.play().catch(() => reportPlaybackFailure(player));
        } catch (_error) {
          reportPlaybackFailure(player);
        }
      }
      if (!sourceJump) return;
      const turns = Array.from(document.querySelectorAll("[data-transcript-turn]"));
      const sourceSegment = (control.dataset.sourceSegment || "").trim();
      const exactTarget = sourceSegment
        ? turns.find((turn) => (
            (turn.dataset.sourceSegments || "").split(/\s+/).includes(sourceSegment)
          ))
        : null;
      const target = exactTarget || turns.reduce((match, turn) => {
        const start = Number.parseFloat(turn.dataset.startSeconds || "0");
        return Number.isFinite(start) && start <= seconds ? turn : match;
      }, turns[0] || null);
      if (!target) return;
      window.requestAnimationFrame(() => {
        scrollTranscriptTurnIntoView(target);
        target.focus({ preventScroll: true });
        const live = document.querySelector("[data-playback-live-status]");
        if (live) live.textContent = `Открыт источник ${formatTime(seconds)} в расшифровке.`;
      });
    });
    const sourceId = new URLSearchParams(window.location.hash.slice(1)).get("graf-source");
    if (sourceId) {
      const target = Array.from(document.querySelectorAll("[data-transcript-turn]")).find(
        (turn) => (turn.dataset.sourceSegments || "").split(/\s+/).includes(sourceId),
      );
      const live = document.querySelector("[data-playback-live-status]");
      if (!target) {
        if (live) live.textContent = "Источник этой ревизии недоступен в текущей расшифровке.";
        return;
      }
      // Exact segment identity only: a newer transcript must not resolve by guessed time.
      activateDetailTab("recording", { updateUrl: false });
      const seconds = Number(target.dataset.startSeconds);
      const player = document.querySelector("[data-playback-player]");
      if (player && Number.isFinite(seconds)) {
        try {
          player.currentTime = Math.max(0, seconds);
        } catch (_error) {
          reportPlaybackFailure(player);
        }
      }
      // Initial navigation must wait for the first header/player ResizeObserver layout.
      window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
        scrollTranscriptTurnIntoView(target);
        target.focus({ preventScroll: true });
        if (live) live.textContent = `Открыт источник ${formatTime(Number(target.dataset.startSeconds))} в расшифровке.`;
      }));
    }
  };

  const DEFAULT_TIMELINE_HEIGHT = 120;
  const TIMELINE_RESIZE_STEP = 24;
  const resizeSpeakerTimelines = () => {
    document.querySelectorAll("[data-speaker-timeline-shell]").forEach((shell) => {
      speakerTimelineResizeHandlers.get(shell)?.();
    });
  };

  const initSpeakerTimelineResize = () => {
    if (document.body.dataset.speakerTimelineResizeViewportReady !== "true") {
      document.body.dataset.speakerTimelineResizeViewportReady = "true";
      window.addEventListener("resize", resizeSpeakerTimelines, { passive: true });
    }
    document.querySelectorAll("[data-speaker-timeline-shell]").forEach((shell) => {
      if (shell.dataset.speakerTimelineResizeReady === "true") return;
      const timeline = shell.querySelector("[data-speaker-timeline]");
      const playback = shell.closest("[data-playback-shell]");
      const handle = playback?.querySelector("[data-speaker-timeline-resize]");
      if (!timeline || !handle || !playback) return;
      shell.dataset.speakerTimelineResizeReady = "true";

      const defaultHeight = Number.parseFloat(
        timeline.dataset.speakerTimelineDefaultHeight || String(DEFAULT_TIMELINE_HEIGHT),
      ) || DEFAULT_TIMELINE_HEIGHT;
      let minimumHeight = 33;
      let currentHeight = minimumHeight;
      let baselineBarTop = playback.getBoundingClientRect().top;
      let drag = null;

      const measureNaturalHeight = () => {
        const inlineHeight = timeline.style.height;
        const inlineMaxHeight = timeline.style.maxHeight;
        timeline.style.height = "auto";
        timeline.style.maxHeight = "none";
        const measuredHeight = Math.ceil(
          Number(timeline.scrollHeight)
            || Number(timeline.getBoundingClientRect?.().height)
            || 0,
        );
        timeline.style.height = inlineHeight;
        timeline.style.maxHeight = inlineMaxHeight;
        return measuredHeight;
      };
      const refreshNaturalHeight = () => {
        const measuredHeight = measureNaturalHeight();
        minimumHeight = Math.min(33, measuredHeight || 33);
        return measuredHeight;
      };
      const contentHeight = () => Math.max(
        minimumHeight,
        Number(timeline.scrollHeight) || minimumHeight,
      );
      const viewportHeight = () => Math.max(
        minimumHeight,
        Math.floor(minimumHeight + Math.max(0, baselineBarTop - 12)),
      );
      const maximumHeight = () => Math.max(
        minimumHeight,
        Math.min(contentHeight(), viewportHeight()),
      );
      const applyHeight = (requestedHeight) => {
        const naturalHeight = contentHeight();
        if (naturalHeight <= minimumHeight + 1) {
          currentHeight = minimumHeight;
          timeline.style.height = "";
          timeline.style.maxHeight = "";
          handle.hidden = true;
          handle.setAttribute("aria-valuemin", String(minimumHeight));
          handle.setAttribute("aria-valuemax", String(minimumHeight));
          handle.setAttribute("aria-valuenow", String(minimumHeight));
          handle.setAttribute("aria-valuetext", "Стандартная высота");
          shell.dataset.speakerTimelineExpandable = "false";
          delete shell.dataset.speakerTimelineHeight;
          return;
        }
        const maxHeight = maximumHeight();
        currentHeight = Math.max(minimumHeight, Math.min(maxHeight, requestedHeight));
        handle.hidden = shell.classList.contains("is-collapsed");
        handle.setAttribute("aria-valuemin", String(minimumHeight));
        handle.setAttribute("aria-valuemax", String(maxHeight));
        handle.setAttribute("aria-valuenow", String(currentHeight));
        handle.setAttribute(
          "aria-valuetext",
          currentHeight <= minimumHeight
            ? "Стандартная высота"
            : `${Math.round(currentHeight)} пикселей из ${Math.round(maxHeight)}`,
        );
        shell.dataset.speakerTimelineExpandable = "true";
        shell.dataset.speakerTimelineHeight = String(currentHeight);
        timeline.style.height = `${currentHeight}px`;
        timeline.style.maxHeight = `${currentHeight}px`;
      };
      const resetViewportBaseline = () => {
        const previousHeight = currentHeight;
        timeline.style.height = "";
        timeline.style.maxHeight = "";
        handle.hidden = false;
        baselineBarTop = playback.getBoundingClientRect().top;
        refreshNaturalHeight();
        applyHeight(previousHeight);
      };
      const stopDrag = (event) => {
        if (!drag) return;
        if (event?.pointerId !== undefined && drag.pointerId !== event.pointerId) return;
        drag = null;
        handle.classList.remove("is-dragging");
        document.body?.classList.remove("is-resizing-speaker-timeline");
        document.removeEventListener("pointermove", moveDrag);
        document.removeEventListener("pointerup", stopDrag);
        document.removeEventListener("pointercancel", stopDrag);
      };
      const moveDrag = (event) => {
        if (!drag) return;
        applyHeight(drag.startHeight + drag.startY - event.clientY);
      };
      handle.addEventListener("pointerdown", (event) => {
        if (event.button !== undefined && event.button !== 0) return;
        event.preventDefault();
        handle.focus({ preventScroll: true });
        drag = {
          pointerId: event.pointerId,
          startY: event.clientY,
          startHeight: currentHeight,
        };
        handle.classList.add("is-dragging");
        document.body?.classList.add("is-resizing-speaker-timeline");
        handle.setPointerCapture?.(event.pointerId);
        document.addEventListener("pointermove", moveDrag);
        document.addEventListener("pointerup", stopDrag);
        document.addEventListener("pointercancel", stopDrag);
      });
      handle.addEventListener("keydown", (event) => {
        let requestedHeight = null;
        if (event.key === "ArrowUp") requestedHeight = currentHeight + TIMELINE_RESIZE_STEP;
        if (event.key === "ArrowDown") requestedHeight = currentHeight - TIMELINE_RESIZE_STEP;
        if (event.key === "Home") requestedHeight = minimumHeight;
        if (event.key === "End") requestedHeight = maximumHeight();
        if (requestedHeight === null) return;
        event.preventDefault();
        applyHeight(requestedHeight);
      });
      speakerTimelineResizeHandlers.set(shell, resetViewportBaseline);
      timeline.style.height = "";
      timeline.style.maxHeight = "";
      handle.hidden = false;
      baselineBarTop = playback.getBoundingClientRect().top;
      refreshNaturalHeight();
      applyHeight(Math.min(defaultHeight, measureNaturalHeight()));
      const collapse = playback.querySelector("[data-playback-timeline-toggle]");
      collapse?.addEventListener("click", () => {
        const collapsed = shell.classList.toggle("is-collapsed");
        shell.inert = collapsed;
        handle.hidden = collapsed || contentHeight() <= minimumHeight + 1;
        collapse.setAttribute("aria-expanded", String(!collapsed));
        collapse.setAttribute("aria-label", collapsed ? "Показать дорожки" : "Скрыть дорожки");
      });
    });
  };

  const mergePlaybackIntervals = (intervals) => {
    const ordered = intervals.filter(([start, end]) => Number.isFinite(start) && Number.isFinite(end) && end > Math.max(0, start))
      .map(([start, end]) => [Math.max(0, start), end]).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const merged = [];
    for (const interval of ordered) {
      const previous = merged[merged.length - 1];
      if (previous && interval[0] <= previous[1]) previous[1] = Math.max(previous[1], interval[1]);
      else merged.push(interval);
    }
    return merged;
  };

  const initPlayback = () => {
    document.querySelectorAll("[data-playback-shell]").forEach((shell) => {
      window.GRAFPlaybackComments?.init(shell);
      if (shell.dataset.playbackReady === "true") {
        if (shell.dataset.playbackContextChanged === "true") {
          delete shell.dataset.playbackContextChanged;
          shell.dispatchEvent(new Event("graf:playback-context-updated"));
        }
        return;
      }
      shell.dataset.playbackReady = "true";
      const player = shell.querySelector("[data-playback-player]");
      if (!player) return;
      const toggle = shell.querySelector("[data-playback-toggle]");
      const current = shell.querySelector("[data-playback-current]");
      const duration = shell.querySelector("[data-playback-duration]");
      const progress = shell.querySelector("[data-playback-progress]");
      const speedToggle = shell.querySelector("[data-playback-speed-toggle]");
      const playbackError = shell.querySelector("[data-playback-error]");
      const lanes = () => Array.from(shell.querySelectorAll("[data-speaker-lane]"));
      const avatars = () => Array.from(shell.querySelectorAll("[data-playback-avatar]"));
      const transcriptTurns = () => Array.from(document.querySelectorAll("[data-transcript-turn]"));
      const selectedSpeakers = new Set();
      let allowedIntervals = [];
      let highlightTimer;
      let selectionTimer;
      const live = shell.querySelector("[data-playback-listen-status]");
      const setToggleState = (playing) => {
        const playIcon = toggle?.querySelector("[data-playback-play-icon]");
        const pauseIcon = toggle?.querySelector("[data-playback-pause-icon]");
        if (playIcon) playIcon.hidden = playing;
        if (pauseIcon) pauseIcon.hidden = !playing;
        toggle?.setAttribute("aria-label", playing ? "Приостановить" : "Воспроизвести");
      };
      const playbackDuration = () => Number.isFinite(player.duration) && player.duration > 0
        ? player.duration : Number.parseFloat(progress?.max || "0") || 0;
      const currentTranscriptTurn = (seconds) => {
        const turns = transcriptTurns();
        const active = turns.filter((turn) => Number(turn.dataset.startSeconds) <= seconds && seconds < Number(turn.dataset.endSeconds));
        const selectedIds = (shell.dataset.playbackSourceSegments || "").split(/\s+/).filter(Boolean);
        return active.find((turn) => selectedIds.some((id) => (turn.dataset.sourceSegments || "").split(/\s+/).includes(id))) || active.at(-1)
          || turns.filter((turn) => Number(turn.dataset.startSeconds) <= seconds).at(-1) || null;
      };
      const followTranscript = (seconds, sourceIds = "") => {
        const ids = sourceIds.split(/\s+/).filter(Boolean);
        const turn = transcriptTurns().find((turn) => ids.some((id) => (turn.dataset.sourceSegments || "").split(/\s+/).includes(id)))
          || currentTranscriptTurn(seconds);
        if (!turn) return;
        activateDetailTab("recording");
        scrollTranscriptTurnIntoView(turn, window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth");
        transcriptTurns().forEach((item) => item.classList.remove("is-source-highlight"));
        turn.classList.add("is-source-highlight");
        window.clearTimeout(highlightTimer);
        highlightTimer = window.setTimeout(() => turn.classList.remove("is-source-highlight"), 2000);
      };
      const syncTime = () => {
        if (current) current.textContent = formatTime(player.currentTime);
        if (progress) { progress.value = String(player.currentTime || 0); progress.setAttribute("aria-valuetext", formatTime(player.currentTime)); }
        if (duration) duration.textContent = formatTime(playbackDuration());
        const max = playbackDuration();
        shell.style.setProperty("--playback-position", `${max > 0 ? Math.max(0, Math.min(100, player.currentTime / max * 100)) : 0}%`);
        const activeKeys = new Set();
        lanes().forEach((lane) => {
          const active = Array.from(lane.querySelectorAll("[data-lane-segment]")).some((segment) => Number(segment.dataset.startSeconds) <= player.currentTime && player.currentTime < Number(segment.dataset.endSeconds));
          lane.classList.toggle("is-active", active);
          if (active) { lane.setAttribute("aria-current", "true"); activeKeys.add(lane.dataset.speakerKey); }
          else lane.removeAttribute("aria-current");
        });
        avatars().forEach((avatar) => avatar.classList.toggle("is-active", activeKeys.has(avatar.dataset.playbackAvatar)));
        const activeTurn = currentTranscriptTurn(player.currentTime);
        transcriptTurns().forEach((turn) => turn.classList.toggle("is-current", turn === activeTurn));
      };
      const enforceSelection = () => {
        if (!selectedSpeakers.size) return true;
        const interval = allowedIntervals.find(([, end]) => player.currentTime < end);
        if (!interval) {
          player.pause();
          if (live) live.textContent = "Речь выбранных спикеров закончилась.";
          return false;
        }
        if (player.currentTime < interval[0]) player.currentTime = interval[0];
        return true;
      };
      const scheduleSelectionBoundary = () => {
        window.clearTimeout(selectionTimer);
        if (player.paused || !selectedSpeakers.size) return;
        if (!enforceSelection()) return;
        const interval = allowedIntervals.find(([, end]) => player.currentTime < end);
        if (!interval) return;
        selectionTimer = window.setTimeout(() => {
          if (!shell.isConnected) return;
          enforceSelection(); syncTime(); scheduleSelectionBoundary();
        }, Math.max(10, (interval[1] - player.currentTime) / player.playbackRate * 1000));
      };
      const play = () => {
        if (playbackError) playbackError.hidden = true;
        if (!enforceSelection()) return;
        try { void player.play().catch(() => reportPlaybackFailure(player)); }
        catch (_error) { reportPlaybackFailure(player); }
      };
      const seekTo = (seconds, { follow = true, autoplay = false, sourceIds = "" } = {}) => {
        if (!Number.isFinite(seconds)) return;
        try { player.currentTime = Math.max(0, Math.min(playbackDuration() || Infinity, seconds)); }
        catch (_error) { reportPlaybackFailure(player); return; }
        shell.dataset.playbackSourceSegments = sourceIds;
        syncTime();
        if (follow) followTranscript(player.currentTime, sourceIds);
        if (autoplay) play();
      };
      const navigateSpeech = (direction, speakerKey = null, autoplay = false) => {
        const turns = transcriptTurns().filter((turn) => !speakerKey || turn.dataset.speakerKey === speakerKey)
          .sort((a, b) => Number(a.dataset.startSeconds) - Number(b.dataset.startSeconds));
        const target = direction > 0
          ? turns.find((turn) => Number(turn.dataset.startSeconds) > player.currentTime)
          : turns.filter((turn) => Number(turn.dataset.startSeconds) < player.currentTime).at(-1);
        if (target) seekTo(Number(target.dataset.startSeconds), { autoplay, sourceIds: target.dataset.sourceSegments });
        else if (live) live.textContent = direction > 0 ? "Следующей реплики нет." : "Предыдущей реплики нет.";
      };
      const syncSelection = () => {
        allowedIntervals = mergePlaybackIntervals(lanes().filter((lane) => selectedSpeakers.has(lane.dataset.speakerKey))
          .flatMap((lane) => Array.from(lane.querySelectorAll("[data-lane-segment]"), (segment) => [Number(segment.dataset.startSeconds), Number(segment.dataset.endSeconds)])));
        shell.querySelectorAll("[data-speaker-lane], .playback-speaker-interval").forEach((lane) => lane.classList.toggle("is-unselected", selectedSpeakers.size > 0 && !selectedSpeakers.has(lane.dataset.speakerKey)));
        const all = shell.querySelector("[data-listen-all]");
        if (all) all.checked = !selectedSpeakers.size;
        shell.querySelectorAll("[data-listen-speaker]").forEach((input) => { input.checked = selectedSpeakers.has(input.dataset.listenSpeaker); });
        const count = shell.querySelector("[data-listen-count]");
        if (count) { count.hidden = !selectedSpeakers.size; count.textContent = String(selectedSpeakers.size); }
        if (live) live.textContent = selectedSpeakers.size ? `Выбрано спикеров: ${selectedSpeakers.size}. Остальные пропускаются.` : "Прослушиваются все спикеры.";
      };
      const menus = [
        [speedToggle, shell.querySelector("[data-playback-speed-menu]")],
        [shell.querySelector("[data-playback-listen-toggle]"), shell.querySelector("[data-playback-listen-menu]")],
      ].filter(([button, menu]) => button && menu);
      const closeMenus = (restore = false) => menus.forEach(([button, menu]) => {
        if (menu.hidden) return;
        menu.hidden = true; button.setAttribute("aria-expanded", "false");
        if (restore) button.focus({ preventScroll: true });
      });
      menus.forEach(([button, menu]) => {
        button.addEventListener("click", () => {
          const opening = menu.hidden;
          closeMenus(); menu.hidden = !opening; button.setAttribute("aria-expanded", String(opening));
          if (opening) menu.querySelector('[aria-checked="true"], input:checked, button, input')?.focus();
        });
        menu.addEventListener("keydown", (event) => {
          if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
          const items = Array.from(menu.querySelectorAll("button,input"));
          const index = items.indexOf(document.activeElement);
          const next = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : (index + (["ArrowLeft", "ArrowUp"].includes(event.key) ? -1 : 1) + items.length) % items.length;
          event.preventDefault(); items[next]?.focus();
        });
      });
      shell.querySelectorAll("[data-playback-speed-option]").forEach((button) => button.addEventListener("click", () => {
        player.playbackRate = Number(button.dataset.playbackSpeedOption);
        closeMenus(true);
      }));
      player.addEventListener("ratechange", () => {
        scheduleSelectionBoundary();
        if (speedToggle) speedToggle.textContent = `${player.playbackRate}x`;
        shell.querySelectorAll("[data-playback-speed-option]").forEach((button) => button.setAttribute("aria-checked", String(Number(button.dataset.playbackSpeedOption) === player.playbackRate)));
      });
      shell.addEventListener("change", (event) => {
        const input = event.target;
        if (input.matches("[data-listen-all]")) selectedSpeakers.clear();
        else if (input.matches("[data-listen-speaker]")) {
          if (input.checked) selectedSpeakers.add(input.dataset.listenSpeaker); else selectedSpeakers.delete(input.dataset.listenSpeaker);
        } else return;
        syncSelection(); play();
      });
      const togglePlayback = () => { if (player.paused) play(); else player.pause(); };
      toggle?.addEventListener("click", togglePlayback);
      shell.querySelectorAll("[data-playback-skip]").forEach((button) => button.addEventListener("click", () => seekTo(player.currentTime + Number(button.dataset.playbackSkip))));
      shell.querySelector("[data-playback-next]")?.addEventListener("click", () => navigateSpeech(1));
      progress?.addEventListener("input", () => seekTo(Number(progress.value)));
      shell.addEventListener("click", (event) => {
        const avatar = event.target.closest("[data-playback-avatar]");
        if (avatar) { selectedSpeakers.clear(); syncSelection(); navigateSpeech(1, avatar.dataset.playbackAvatar, true); return; }
        const track = event.target.closest("[data-timeline-track]");
        if (!track) return;
        const segment = event.target.closest("[data-lane-segment]");
        if (segment) { seekTo(Number(segment.dataset.startSeconds), { sourceIds: segment.dataset.sourceSegments }); return; }
        if (!event.detail) return;
        const rect = track.getBoundingClientRect();
        if (rect.width) seekTo(playbackDuration() * Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)));
      });
      shell.addEventListener("keydown", (event) => {
        if (!event.target.matches("[data-timeline-track]") || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
        event.preventDefault(); event.stopPropagation();
        seekTo(event.key === "Home" ? 0 : event.key === "End" ? playbackDuration() : player.currentTime + (event.key === "ArrowLeft" ? -15 : 15));
      });
      shell.addEventListener("pointermove", (event) => {
        const track = event.target.closest("[data-timeline-track]");
        if (!track) return;
        const rect = track.getBoundingClientRect();
        shell.style.setProperty("--playback-hover-position", `${Math.max(0, Math.min(100, (event.clientX - rect.left) / rect.width * 100))}%`);
        shell.classList.add("is-timeline-hover");
      });
      shell.addEventListener("pointerout", (event) => {
        if (event.target.closest("[data-timeline-track]") && !event.relatedTarget?.closest?.("[data-timeline-track]")) shell.classList.remove("is-timeline-hover");
      });
      const carousel = shell.querySelector("[data-playback-avatars]");
      const syncCarousel = () => shell.querySelectorAll("[data-avatar-scroll]").forEach((button) => {
        button.disabled = !carousel || (Number(button.dataset.avatarScroll) < 0 ? carousel.scrollLeft <= 1 : carousel.scrollLeft + carousel.clientWidth >= carousel.scrollWidth - 1);
      });
      shell.querySelectorAll("[data-avatar-scroll]").forEach((button) => button.addEventListener("click", () => {
        carousel?.scrollBy({ left: Number(button.dataset.avatarScroll) * Math.max(32, carousel.clientWidth), behavior: "auto" });
      }));
      carousel?.addEventListener("scroll", syncCarousel, { passive: true });
      if (carousel && typeof ResizeObserver !== "undefined") {
        const observer = new ResizeObserver(() => { if (!shell.isConnected) observer.disconnect(); else syncCarousel(); });
        observer.observe(carousel);
      }
      syncCarousel();
      shell.addEventListener("graf:playback-context-updated", () => {
        const keys = new Set(lanes().map(lane => lane.dataset.speakerKey));
        selectedSpeakers.forEach(key => { if (!keys.has(key)) selectedSpeakers.delete(key); });
        syncSelection(); syncTime(); syncCarousel(); scheduleSelectionBoundary();
      });
      player.addEventListener("loadedmetadata", () => { if (progress && Number.isFinite(player.duration)) progress.max = String(player.duration); syncTime(); });
      player.addEventListener("timeupdate", () => { if (!player.paused) enforceSelection(); syncTime(); scheduleSelectionBoundary(); });
      player.addEventListener("seeked", scheduleSelectionBoundary);
      player.addEventListener("play", () => { if (enforceSelection()) setToggleState(true); scheduleSelectionBoundary(); });
      player.addEventListener("pause", () => { window.clearTimeout(selectionTimer); setToggleState(false); });
      player.addEventListener("ended", () => { player.pause(); seekTo(0, { follow: false }); setToggleState(false); });
      player.addEventListener("error", () => reportPlaybackFailure(player));
      const keyboard = (event) => {
        if (!shell.isConnected) { document.removeEventListener("keydown", keyboard); document.removeEventListener("click", outside); return; }
        if (event.defaultPrevented) return;
        if (event.key === "Escape" && menus.some(([, menu]) => !menu.hidden)) { event.preventDefault(); closeMenus(true); return; }
        if (event.altKey || event.ctrlKey || event.metaKey || event.target.closest?.('input,textarea,select,[contenteditable="true"],[role="menu"],[role="dialog"],dialog,[data-playback-listen-menu]') || document.querySelector('dialog[open], [role="dialog"][aria-modal="true"]') || menus.some(([, menu]) => !menu.hidden)) return;
        if (event.key === " " && event.target.closest?.("button,a[href],[role=button]")) return;
        if (![" ", "ArrowLeft", "ArrowRight"].includes(event.key)) return;
        event.preventDefault();
        if (event.key === " ") { if (!event.repeat) togglePlayback(); }
        else if (event.shiftKey) navigateSpeech(event.key === "ArrowLeft" ? -1 : 1);
        else seekTo(player.currentTime + (event.key === "ArrowLeft" ? -15 : 15));
      };
      const outside = (event) => {
        if (!shell.isConnected) { document.removeEventListener("keydown", keyboard); document.removeEventListener("click", outside); return; }
        if (!event.target.closest?.(".playback-menu-anchor")) closeMenus();
      };
      document.addEventListener("keydown", keyboard);
      document.addEventListener("click", outside);
      syncTime();
    });
  };

  const initCalendarSettings = () => {
    document.querySelectorAll("[data-calendar-local-datetime], [data-calendar-local-time]").forEach((element) => {
      element.textContent = window.GRAFTime.format(element.getAttribute("datetime"));
    });
    const mutationCopy = {
      connect: "Проверяем доступ…",
      selection: "Сохраняем выбор…",
      sync: "Синхронизируем календарь…",
      disconnect: "Отключаем календарь…",
    };
    const initCalendarMutation = (form) => {
      if (!(form instanceof HTMLFormElement) || form.dataset.calendarMutationReady === "true") return;
      form.dataset.calendarMutationReady = "true";
      const kind = form.dataset.calendarMutation || "mutation";
      const submit = form.querySelector("[data-calendar-mutation-submit], button[type='submit']");
      const status = form.querySelector("[data-calendar-mutation-status]");
      const selectionLimit = Number.parseInt(form.dataset.calendarSelectionLimit || "", 10);
      const selectedCalendarCount = () => form.querySelectorAll(
        "input[name='selected_provider_calendar_ids']:checked"
      ).length;
      const showSelectionLimit = () => {
        if (!status) return;
        status.dataset.preserveMessage = "true";
        status.textContent = `Можно выбрать до ${selectionLimit} календарей.`;
        status.hidden = false;
      };
      form.addEventListener("submit", async (event) => {
        if (Number.isFinite(selectionLimit) && selectedCalendarCount() > selectionLimit) {
          event.preventDefault();
          showSelectionLimit();
          status?.focus?.({ preventScroll: true });
          return;
        }
        if (kind === "sync") event.preventDefault();
        form.dataset.state = "submitting";
        form.setAttribute("aria-busy", "true");
        if (submit) {
          submit.disabled = true;
          submit.dataset.originalLabel = submit.textContent || "";
          submit.textContent = mutationCopy[kind] || "Выполняем…";
        }
        if (status) {
          status.textContent = mutationCopy[kind] || "Выполняем…";
          status.hidden = false;
        }
        if (kind === "sync") {
          const controller = new AbortController();
          const timeout = window.setTimeout(() => controller.abort(), 10000);
          try {
            const response = await fetch(form.action, {
              method: "POST", body: new FormData(form), credentials: "same-origin", signal: controller.signal,
              headers: { "Accept": "text/html" },
            });
            if (!response.ok || (response.redirected && !new URL(response.url).pathname.endsWith("/settings/integrations/calendar"))) throw new Error("calendar_sync_failed");
            const result = new DOMParser().parseFromString(await response.text(), "text/html");
            if (status) status.textContent = result.querySelector(".calendar-notice")?.textContent?.trim()
              || "Синхронизация запрошена. Состояние обновится автоматически.";
            form.dataset.syncPending = "true";
          } catch (_) {
            if (status) status.textContent = "Не удалось запросить синхронизацию. Повторите попытку.";
          } finally {
            window.clearTimeout(timeout);
            form.dataset.state = "idle";
            form.removeAttribute("aria-busy");
            if (submit) {
              submit.disabled = false;
              submit.textContent = submit.dataset.originalLabel || "Синхронизировать";
            }
            void refreshCalendarDisplay();
          }
        }
      });
      form.addEventListener("invalid", () => {
        if (!status) return;
        status.textContent = "Проверьте обязательные поля.";
        status.hidden = false;
      }, true);
      form.addEventListener("input", () => {
        if (!status || form.dataset.state === "submitting") return;
        delete status.dataset.preserveMessage;
        status.textContent = "";
        status.hidden = true;
      });
      if (Number.isFinite(selectionLimit)) {
        form.addEventListener("change", (event) => {
          const target = event.target;
          if (!(target instanceof HTMLInputElement)
            || target.name !== "selected_provider_calendar_ids"
            || !target.checked
            || selectedCalendarCount() <= selectionLimit) return;
          target.checked = false;
          showSelectionLimit();
        });
        form.addEventListener("keyup", (event) => {
          const target = event.target;
          if (!(target instanceof HTMLInputElement)
            || target.name !== "selected_provider_calendar_ids"
            || (event.key !== " " && event.key !== "Spacebar")
            || target.checked
            || selectedCalendarCount() !== selectionLimit) return;
          showSelectionLimit();
        });
      }
    };
    document.querySelectorAll("[data-calendar-mutation]").forEach(initCalendarMutation);
    const resultRegion = document.querySelector("[data-calendar-has-result='true'] .calendar-notice");
    if (resultRegion && window.location.search && !resultRegion.dataset.focused) {
      resultRegion.dataset.focused = "true";
      window.setTimeout(() => resultRegion.focus({ preventScroll: true }), 0);
    }
    const dialogOpeners = new WeakMap();
    const restoreDialogFocus = (dialog) => {
      const opener = dialogOpeners.get(dialog);
      dialogOpeners.delete(dialog);
      if (opener?.isConnected) opener.focus({ preventScroll: true });
    };
    const openCalendarDialog = (dialog, opener) => {
      if (!dialog) return;
      if (opener) dialogOpeners.set(dialog, opener);
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
      const firstField = dialog.querySelector("input:not([type='hidden']), button[type='submit'], button:not([data-calendar-provider-close])");
      firstField?.focus({ preventScroll: true });
    };
    const closeCalendarDialog = (dialog) => {
      if (!dialog) return;
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
      dialog.querySelector("form")?.reset();
      restoreDialogFocus(dialog);
    };
    document.querySelectorAll("[data-calendar-provider-open]").forEach((button) => {
      if (button.dataset.calendarProviderOpenReady === "true") return;
      button.dataset.calendarProviderOpenReady = "true";
      button.addEventListener("click", () => {
        const dialogId = button.dataset.calendarProviderOpen || "";
        openCalendarDialog(document.getElementById(dialogId), button);
      });
    });
    document.querySelectorAll("[data-calendar-provider-close]").forEach((button) => {
      if (button.dataset.calendarProviderCloseReady === "true") return;
      button.dataset.calendarProviderCloseReady = "true";
      button.addEventListener("click", () => {
        closeCalendarDialog(button.closest("[data-calendar-provider-dialog]"));
      });
    });
    document.querySelectorAll("[data-calendar-provider-dialog]").forEach((dialog) => {
      if (dialog.dataset.calendarProviderDialogReady === "true") return;
      dialog.dataset.calendarProviderDialogReady = "true";
      dialog.addEventListener("close", () => {
        dialog.querySelector("form")?.reset();
        restoreDialogFocus(dialog);
      });
      dialog.addEventListener("cancel", (event) => {
        event.preventDefault();
        closeCalendarDialog(dialog);
      });
      dialog.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        event.preventDefault();
        closeCalendarDialog(dialog);
      });
      dialog.addEventListener("click", (event) => {
        if (event.target === dialog) closeCalendarDialog(dialog);
      });
    });
    document.querySelectorAll("[data-calendar-disconnect-cancel]").forEach((button) => {
      if (button.dataset.calendarCancelReady === "true") return;
      button.dataset.calendarCancelReady = "true";
      button.addEventListener("click", () => {
        const details = button.closest("details");
        if (details) details.open = false;
      });
    });
  };

  let calendarRefreshInFlight = false;
  let calendarRefreshListenersReady = false;

  // Only server-rendered display regions are replaced. Forms and dialogs retain
  // their DOM identity, entered values and focus while a provider is syncing.
  const refreshCalendarDisplay = async () => {
    if (calendarRefreshInFlight || document.hidden || !navigator.onLine) return;
    if (!document.querySelector("[data-calendar-live]")) return;
    calendarRefreshInFlight = true;
    const pageURL = window.location.href;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(pageURL, {
        credentials: "same-origin", cache: "no-store", signal: controller.signal,
        headers: { "Accept": "text/html" },
      });
      if (window.location.href !== pageURL) return;
      if (!response.ok || response.redirected) throw new Error("calendar_refresh_failed");
      const next = new DOMParser().parseFromString(await response.text(), "text/html");
      document.querySelectorAll("[data-calendar-live]").forEach((region) => {
        const replacement = [...next.querySelectorAll("[data-calendar-live]")]
          .find((item) => item.dataset.calendarLive === region.dataset.calendarLive);
        if (!replacement) return;
        const active = document.activeElement;
        const focusedLink = region.contains(active) && active instanceof HTMLAnchorElement
          ? active.getAttribute("href") : null;
        // Preserve the details element itself (and its open state).
        if (active === region.querySelector(":scope > summary")) {
          active.innerHTML = replacement.querySelector(":scope > summary")?.innerHTML || active.innerHTML;
          [...region.children].filter((child) => child.tagName !== "SUMMARY").forEach((child) => child.remove());
          [...replacement.children].filter((child) => child.tagName !== "SUMMARY").forEach((child) => region.append(child.cloneNode(true)));
        } else {
          region.innerHTML = replacement.innerHTML;
        }
        if (focusedLink) {
          const link = [...region.querySelectorAll("a[href]")]
            .find((item) => item.getAttribute("href") === focusedLink);
          (link || region.querySelector("summary"))?.focus({ preventScroll: true });
        }
      });
      document.querySelectorAll("[data-calendar-source]").forEach((source) => {
        const replacement = [...next.querySelectorAll("[data-calendar-source]")]
          .find((item) => item.dataset.calendarSource === source.dataset.calendarSource);
        if (!replacement) return;
        source.dataset.state = replacement.dataset.state;
        const sync = source.querySelector("[data-calendar-mutation='sync'] button[type='submit']");
        const nextSync = replacement.querySelector("[data-calendar-mutation='sync'] button[type='submit']");
        if (sync && nextSync && sync.form?.dataset.state !== "submitting") {
          sync.disabled = nextSync.disabled;
          sync.setAttribute("aria-disabled", String(nextSync.disabled));
          sync.textContent = nextSync.textContent;
          if (sync.form?.dataset.syncPending === "true" && !["queued", "syncing"].includes(replacement.dataset.syncState)) {
            const status = sync.form.querySelector("[data-calendar-mutation-status]");
            if (status) status.textContent = replacement.dataset.syncState === "synced"
              ? "Календарь обновлён."
              : replacement.querySelector(".calendar-source-card__states")?.textContent?.trim() || "Проверьте состояние подключения.";
            delete sync.form.dataset.syncPending;
          }
        }
        const form = source.querySelector(".calendar-selection-form");
        const nextForm = replacement.querySelector(".calendar-selection-form");
        if ((!form || (form.dataset.state === "pristine" && !form.contains(document.activeElement))) && Boolean(form) !== Boolean(nextForm)) {
          const pickerRegion = source.querySelector("[data-calendar-picker-region]");
          const nextPickerRegion = replacement.querySelector("[data-calendar-picker-region]");
          if (pickerRegion && nextPickerRegion) pickerRegion.innerHTML = nextPickerRegion.innerHTML;
        }
        if (form && nextForm && form.dataset.state === "pristine" && !form.contains(document.activeElement)) {
          const picker = form.querySelector(".calendar-picker");
          const nextPicker = nextForm.querySelector(".calendar-picker");
          if (picker && nextPicker && picker.innerHTML !== nextPicker.innerHTML) {
            picker.innerHTML = nextPicker.innerHTML;
            // Reset baseline after a provider catalog update, without replacing the form.
            form.dispatchEvent(new CustomEvent("calendar:baseline"));
          }
        }
      });
      initCalendarSettings();
      initSettingsFormState();
      document.querySelectorAll("[data-calendar-refresh-status]").forEach((status) => { status.hidden = true; });
    } catch (_) {
      document.querySelectorAll("[data-calendar-refresh-status]").forEach((status) => {
        status.textContent = "Не удалось обновить календарь. Проверьте соединение или вход в GRAF. Повторим автоматически.";
        status.hidden = false;
      });
    } finally {
      window.clearTimeout(timeout);
      calendarRefreshInFlight = false;
    }
  };

  const initCalendarUpcomingRefresh = () => {
    if (calendarUpcomingRefreshTimer !== null) window.clearTimeout(calendarUpcomingRefreshTimer);
    calendarUpcomingRefreshTimer = null;
    if (!document.querySelector("[data-calendar-live]")) return;
    if (!calendarRefreshListenersReady) {
      calendarRefreshListenersReady = true;
      document.addEventListener("visibilitychange", () => {
        if (!document.hidden) void refreshCalendarDisplay();
      });
      window.addEventListener("online", () => { void refreshCalendarDisplay(); });
    }
    calendarUpcomingRefreshTimer = window.setTimeout(async () => {
      calendarUpcomingRefreshTimer = null;
      await refreshCalendarDisplay();
      initCalendarUpcomingRefresh();
    }, 30000);
  };

  let recordingSettingsNonce = null;
  const initRecordingSettings = () => {
    const root = document.querySelector('[data-recording-settings]');
    if (!root || root.dataset.ready === 'true') return;
    root.dataset.ready = 'true';
    const controls = root.querySelector('[data-recording-settings-controls]');
    const list = root.querySelector('[data-recording-settings-targets]');
    const all = root.querySelector('[data-recording-settings-all]');
    const status = root.querySelector('[data-recording-settings-status]');
    const retry = root.querySelector('[data-recording-settings-retry]');
    const template = root.querySelector('[data-recording-settings-select]');
    const search = root.querySelector('[data-recording-settings-search]');
    const empty = root.querySelector('[data-recording-settings-empty]');
    const rows = new Map();
    const filter = () => {
      const query = search.value.trim().toLocaleLowerCase();
      let visible = 0;
      for (const row of rows.values()) {
        row.hidden = !row.firstElementChild.textContent.toLocaleLowerCase().includes(query);
        if (!row.hidden) visible++;
      }
      empty.hidden = visible > 0 || rows.size === 0;
    };
    search.addEventListener('input', filter);
    let busy = false;
    let refreshPending = false;
    let confirmed = null;

    const render = (snapshot) => {
      const ids = new Set(snapshot.targets.map((target) => target.id));
      for (const [id, row] of rows) {
        if (!ids.has(id)) { row.remove(); rows.delete(id); }
      }
      for (const [index, target] of snapshot.targets.entries()) {
        let row = rows.get(target.id);
        if (!row) {
          row = document.createElement('label');
          row.className = 'settings-control-row';
          const name = document.createElement('span');
          name.className = 'settings-control-row__title';
          const select = template.content.firstElementChild.cloneNode(true);
          select.dataset.recordingTarget = target.id;
          row.append(name, select);
          rows.set(target.id, row);
        }
        if (list.children[index] !== row) list.insertBefore(row, list.children[index] || null);
        row.firstElementChild.textContent = target.name;
        const select = row.querySelector('select');
        select.setAttribute('aria-label', `Автозапись: ${target.name}`);
        select.value = target.rule;
      }
      filter();
      const rules = new Set(snapshot.targets.map((target) => target.rule));
      all.value = rules.size === 1 ? snapshot.targets[0].rule : '';
      all.disabled = busy || snapshot.targets.length === 0;
      controls.hidden = false;
      status.textContent = snapshot.error || (snapshot.targets.length ? '' : 'Приложения для автозаписи пока недоступны.');
    };

    const request = async (action = 'read', fields = {}) => {
      if (busy) { if (action === 'read') refreshPending = true; return; }
      const bridge = window.webkit?.messageHandlers?.grafRecordingSettings;
      if (!bridge || !recordingSettingsNonce) {
        status.textContent = 'Не удалось подключить настройки этого Mac. Обновите страницу или приложение GRAF.';
        retry.hidden = false;
        return;
      }
      busy = true;
      const nonce = recordingSettingsNonce;
      const focused = root.contains(document.activeElement) ? document.activeElement : null;
      status.textContent = action === 'read' ? 'Загрузка настроек…' : 'Сохранение…';
      retry.hidden = true;
      controls.querySelectorAll('select').forEach((select) => { select.disabled = true; });
      let timer;
      try {
        const snapshot = await Promise.race([
          bridge.postMessage({ version: 1, nonce, action, ...fields }),
          new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('timeout')), 5000); }),
        ]);
        if (!root.isConnected || nonce !== recordingSettingsNonce) return;
        if (snapshot?.version !== 1 || !Array.isArray(snapshot.targets) ||
            snapshot.targets.some((target) => typeof target.id !== 'string' || typeof target.name !== 'string' || !['always', 'ask', 'never'].includes(target.rule))) {
          throw new Error('unsupported');
        }
        confirmed = snapshot;
        render(snapshot);
        if (!snapshot.error && snapshot.targets.length) status.textContent = action === 'read' ? 'Изменения сохраняются сразу на этом Mac.' : 'Сохранено на этом Mac.';
        retry.hidden = !snapshot.error;
      } catch {
        if (!root.isConnected || nonce !== recordingSettingsNonce) return;
        if (confirmed) render(confirmed);
        status.textContent = action === 'read'
          ? 'Не удалось загрузить настройки. Повторите загрузку.'
          : 'Не удалось подтвердить сохранение. Повторите загрузку, чтобы проверить текущие настройки.';
        retry.hidden = false;
      } finally {
        clearTimeout(timer);
        busy = false;
        if (root.isConnected) {
          controls.querySelectorAll('select').forEach((select) => { select.disabled = false; });
          all.disabled = !confirmed?.targets.length;
          if (focused?.isConnected && document.activeElement === document.body) focused.focus({ preventScroll: true });
          if (refreshPending) { refreshPending = false; request(); }
        }
      }
    };
    root.addEventListener('change', (event) => {
      if (event.target === all) request('setAll', { rule: all.value });
      else if (event.target?.dataset.recordingTarget) request('set', { targetID: event.target.dataset.recordingTarget, rule: event.target.value });
    });
    retry.addEventListener('click', () => request());
    root.addEventListener('graf:recording-settings-refresh', () => request());
    request();
  };
  window.GRAFRecordingSettings = {
    connect(nonce) { recordingSettingsNonce = nonce; initRecordingSettings(); this.refresh(); },
    refresh() { document.querySelector('[data-recording-settings]')?.dispatchEvent(new Event('graf:recording-settings-refresh')); },
  };

  let notificationSettingsNonce = null;
  const initLocalNotificationSettings = () => {
    const root = document.querySelector('[data-local-notification-settings]');
    if (!root || root.dataset.ready === 'true') return;
    root.dataset.ready = 'true';
    const controls = root.querySelector('[data-local-notification-controls]');
    const status = root.querySelector('[data-local-notification-status]');
    const permission = root.querySelector('[data-local-notification-permission]');
    const retry = root.querySelector('[data-local-notification-retry]');
    const reload = root.querySelector('[data-local-notification-reload]');
    const fields = [...controls.querySelectorAll('[data-local-notification-field]')];
    let busy = false, confirmed = null, sequence = 0, refreshPending = false;
    const render = (snapshot) => {
      fields.forEach(input => {
        const value = snapshot.preferences[input.dataset.localNotificationField];
        if (input.type === 'checkbox') input.checked = value;
        else input.value = String(value);
        input.disabled = input.dataset.localNotificationField === 'offsetMinutes' && !snapshot.preferences.reminders;
      });
      permission.textContent = snapshot.permission;
      controls.querySelector('[data-local-notification-action="requestPermission"]').hidden = !snapshot.canRequestPermission;
      controls.disabled = busy || !snapshot.canEdit;
    };
    const request = async (action = 'read', patch = {}) => {
      if (busy) { if (action === 'read') refreshPending = true; return; }
      const bridge = window.webkit?.messageHandlers?.grafNotificationSettings;
      if (!bridge || !notificationSettingsNonce) {
        controls.disabled = true;
        status.textContent = 'Не удалось подключить настройки этого Mac. Обновите страницу после входа в GRAF.';
        reload.hidden = false;
        return;
      }
      const nonce = notificationSettingsNonce, current = ++sequence;
      const focused = root.contains(document.activeElement) ? document.activeElement : null;
      busy = true; controls.disabled = true; retry.hidden = true; reload.hidden = true;
      status.textContent = action === 'read' ? 'Проверяем настройки…' : action === 'set' ? 'Сохранение…' : 'Выполняем…';
      let timer;
      try {
        const snapshot = await Promise.race([
          bridge.postMessage({version: 1, nonce, action, ...patch}),
          new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('timeout')), 5000); }),
        ]);
        if (!root.isConnected || nonce !== notificationSettingsNonce || current !== sequence) return;
        const prefs = snapshot?.preferences;
        if (snapshot?.version !== 1 || !prefs || !['reminders', 'showTitles', 'sound'].every(key => typeof prefs[key] === 'boolean') ||
            ![0, 1, 5].includes(prefs.offsetMinutes) || typeof snapshot.canEdit !== 'boolean' ||
            typeof snapshot.canRequestPermission !== 'boolean' || typeof snapshot.permission !== 'string') throw new Error('unsupported');
        confirmed = snapshot; render(snapshot);
        status.textContent = snapshot.error || (!snapshot.canEdit ? 'Войдите в GRAF и обновите страницу, чтобы изменить настройки.' : snapshot.message || (action === 'read' ? '' : 'Готово.'));
        retry.hidden = !snapshot.error;
        reload.hidden = snapshot.canEdit;
      } catch (_) {
        if (!root.isConnected || nonce !== notificationSettingsNonce || current !== sequence) return;
        if (confirmed) render(confirmed);
        status.textContent = 'Не удалось подтвердить изменение. Проверьте текущее значение.';
        retry.hidden = false; reload.hidden = false;
      } finally {
        clearTimeout(timer);
        if (current === sequence) {
          busy = false;
          controls.disabled = !notificationSettingsNonce || !confirmed?.canEdit;
          if (focused?.isConnected && document.activeElement === document.body) focused.focus({preventScroll: true});
          if (refreshPending) { refreshPending = false; request(); }
        }
      }
    };
    root.addEventListener('change', event => {
      const input = event.target, field = input.dataset.localNotificationField;
      if (field) request('set', {field, value: input.type === 'checkbox' ? input.checked : Number(input.value)});
    });
    controls.querySelectorAll('[data-local-notification-action]').forEach(button => {
      button.addEventListener('click', () => request(button.dataset.localNotificationAction));
    });
    retry.addEventListener('click', () => request());
    root.addEventListener('graf:notification-settings-refresh', () => request());
    root.addEventListener('graf:notification-settings-disconnect', () => {
      sequence++; busy = false; refreshPending = false; confirmed = null; controls.disabled = true;
      fields.forEach(input => { if (input.type === 'checkbox') input.checked = false; else input.value = ''; });
      permission.textContent = '';
      status.textContent = 'Аккаунт изменился. Обновите страницу настроек.'; reload.hidden = false;
    });
    window.addEventListener('focus', () => { if (root.isConnected) request(); });
    request();
  };
  window.GRAFNotificationSettings = {
    connect(nonce) { notificationSettingsNonce = nonce; initLocalNotificationSettings(); this.refresh(); },
    refresh() { document.querySelector('[data-local-notification-settings]')?.dispatchEvent(new Event('graf:notification-settings-refresh')); },
    disconnect() {
      notificationSettingsNonce = null;
      document.querySelector('[data-local-notification-settings]')?.dispatchEvent(new Event('graf:notification-settings-disconnect'));
    },
  };

  const initSettingsFormState = () => {
    document.querySelectorAll("[data-settings-form]").forEach((form) => {
      if (form.dataset.settingsFormReady === "true") return;
      form.dataset.settingsFormReady = "true";
      const status = form.querySelector("[data-settings-form-status]");
      const submit = form.querySelector("button[type='submit']");
      const reset = form.querySelector("[data-settings-form-reset]");
      const disablePristine = form.hasAttribute("data-settings-form-disable-pristine");
      if (status) {
        status.setAttribute("role", "status");
        status.setAttribute("aria-live", "polite");
      }
      const snapshot = () => new URLSearchParams(new FormData(form)).toString();
      let initial = snapshot();
      const update = () => {
        const dirty = snapshot() !== initial;
        form.dataset.state = dirty ? "dirty" : "pristine";
        if (status && status.dataset.preserveMessage !== "true") {
          status.textContent = dirty ? "Есть несохранённые изменения" : "";
          status.hidden = !dirty;
        }
        if (disablePristine) {
          if (submit) submit.disabled = !dirty;
          if (reset) reset.disabled = !dirty;
        }
      };
      form.addEventListener("calendar:baseline", () => { initial = snapshot(); update(); });
      form.addEventListener("input", update);
      form.addEventListener("change", update);
      form.addEventListener("reset", () => window.setTimeout(update, 0));
      form.addEventListener("submit", () => {
        if (!form.hasAttribute("data-account-preferences")) initial = snapshot();
        form.dataset.state = "saving";
        if (status) {
          status.textContent = "Сохраняем…";
          status.hidden = false;
        }
        if (submit) submit.disabled = true;
      });
      update();
    });
  };

  const initAccountPreferences = () => {
    document.querySelectorAll("[data-account-preferences]").forEach((form) => {
      if (form.dataset.accountPreferencesReady === "true") return;
      form.dataset.accountPreferencesReady = "true";
      const autoSave = form.dataset.accountPreferencesAutoSave === "true";
      const status = form.querySelector("[data-account-preferences-status]");
      const returnField = form.elements.namedItem("return_to");
      let persistedTheme = form.elements.namedItem("theme")?.value || "system";
      let saveInFlight = false;
      const applyTheme = (theme) => {
        if (theme === "system") document.documentElement.removeAttribute("data-theme");
        else document.documentElement.dataset.theme = theme;
        document.documentElement.style.colorScheme = theme === "system" ? "" : theme;
      };
      const currentTheme = form.elements.namedItem("theme")?.value || "system";
      persistedTheme = currentTheme;
      applyTheme(currentTheme);
      form.addEventListener("change", (event) => {
        if (event.target?.name === "theme") {
          applyTheme(event.target.value);
          if (autoSave && !saveInFlight) form.requestSubmit();
        }
      });

      const timezoneSelect = form.querySelector("[data-timezone-select]");
      const search = form.querySelector("[data-timezone-search]");
      const preview = form.querySelector("[data-timezone-preview]");
      const result = form.querySelector("[data-timezone-search-result]");
      const initialTimezone = timezoneSelect?.value;
      const options = timezoneSelect ? Array.from(timezoneSelect.options).map(option => option.cloneNode(true)) : [];
      const normalizeSearch = (value) => value.toLowerCase().normalize("NFKC").replace(/[−–]/g, "-").replace(/\s+/g, " ").trim();
      const filterTimezones = () => {
        if (!timezoneSelect || !search) return;
        const selected = timezoneSelect.value;
        const query = normalizeSearch(search.value);
        const matches = options.filter(option => normalizeSearch(`${option.textContent} ${option.value}`).includes(query));
        // Keep the draft selection while searching; typing alone never changes the setting.
        timezoneSelect.replaceChildren(...options.filter(option => option.value === selected || matches.includes(option)).map(option => option.cloneNode(true)));
        timezoneSelect.value = selected;
        if (result) {
          result.hidden = !query;
          result.textContent = matches.length ? `Найдено: ${matches.length}` : "Совпадений нет. Измените запрос; выбранный пояс сохранён в поле.";
        }
      };
      const updateTimezonePreview = () => {
        if (!timezoneSelect || !preview) return;
        preview.hidden = false;
        preview.textContent = `Сейчас: ${window.GRAFTime.format(new Date(), { timeZone: timezoneSelect.value, showZone: true })}`;
      };
      form.querySelector("[data-timezone-search-wrap]")?.removeAttribute("hidden");
      search?.addEventListener("input", filterTimezones);
      timezoneSelect?.addEventListener("change", updateTimezonePreview);
      updateTimezonePreview();

      let saving = false;
      form.addEventListener("submit", async (event) => {
        if (autoSave) {
          event.preventDefault();
          if (saveInFlight) return;
          saveInFlight = true;
          if (returnField) returnField.value = `${window.location.pathname}${window.location.search}`;
          form.dataset.state = "saving";
          if (status) status.textContent = "Сохраняем тему…";
          const body = new FormData(form);
          form.querySelectorAll("input[name='theme']").forEach((input) => { input.disabled = true; });
          try {
            const response = await fetch(form.action, {
              method: "POST",
              body,
              credentials: "same-origin",
              redirect: "follow",
              headers: csrfToken ? { "X-CSRF-Token": csrfToken } : {},
            });
            const responsePath = new URL(response.url || window.location.href, window.location.href).pathname;
            if (!response.ok || responsePath.startsWith("/login")) throw new Error("account_preferences_save_failed");
            persistedTheme = form.elements.namedItem("theme")?.value || persistedTheme;
            form.dataset.state = "saved";
            if (status) status.textContent = "Тема сохранена";
            form.closest("[data-profile-menu-root]")?.querySelector("[data-profile-menu-trigger]")?.click();
          } catch {
            applyTheme(persistedTheme);
            const selected = Array.from(form.querySelectorAll("input[name='theme']"))
              .find((input) => input.value === persistedTheme);
            if (selected) selected.checked = true;
            form.dataset.state = "error";
            if (status) status.textContent = "Не удалось сохранить тему";
          } finally {
            form.querySelectorAll("input[name='theme']").forEach((input) => { input.disabled = false; });
            saveInFlight = false;
          }
          return;
        }

        event.preventDefault();
        if (saving) return;
        saving = true;
        const settingsStatus = form.querySelector("[data-settings-form-status]");
        const body = new FormData(form);
        const controls = Array.from(form.elements).filter(control => !control.disabled);
        controls.forEach(control => { control.disabled = true; });
        if (settingsStatus) { settingsStatus.textContent = "Сохраняем настройки…"; settingsStatus.hidden = false; }
        try {
          const response = await fetch(form.action, {
            method: "POST", body, credentials: "same-origin", redirect: "follow",
            headers: csrfToken ? { "X-CSRF-Token": csrfToken } : {},
          });
          if (!response.ok || !response.redirected) throw new Error(response.status === 422 ? "invalid_preferences" : "preferences_save_failed");
          const destination = new URL(response.url, location.href);
          if (destination.origin !== location.origin) throw new Error("preferences_save_failed");
          window.location.assign(destination.href);
        } catch (error) {
          form.dataset.state = "error";
          if (settingsStatus) {
            settingsStatus.textContent = error.message === "invalid_preferences"
              ? "Проверьте часовой пояс и остальные настройки, затем сохраните ещё раз."
              : "Не удалось сохранить настройки. Проверьте соединение и повторите отправку.";
            settingsStatus.hidden = false;
          }
        } finally {
          saving = false;
          controls.forEach(control => { control.disabled = false; });
          const submit = form.querySelector("button[type='submit']");
          if (submit) submit.disabled = false;
        }
      });
      form.addEventListener("reset", () => window.setTimeout(() => {
        applyTheme(form.elements.namedItem("theme")?.value || "system");
        if (timezoneSelect) {
          timezoneSelect.replaceChildren(...options.map(option => option.cloneNode(true)));
          timezoneSelect.value = initialTimezone;
        }
        if (search) search.value = "";
        filterTimezones();
        updateTimezonePreview();
        form.dispatchEvent(new Event("change", { bubbles: true }));
      }, 0));
    });
  };

  const initSettingsConfirmations = () => {
    document.querySelectorAll("[data-session-confirmation]").forEach((panel) => {
      if (panel.dataset.confirmReady === "true") return;
      panel.dataset.confirmReady = "true";
      const cancel = () => {
        const target = document.getElementById(panel.dataset.returnFocus) || document.getElementById("account-sessions-title");
        panel.remove();
        target?.focus();
      };
      panel.querySelector("[data-session-cancel]")?.addEventListener("click", (event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        cancel();
      });
      panel.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        event.preventDefault();
        event.stopPropagation();
        cancel();
      });
    });
    document.querySelectorAll("[data-confirm]").forEach((button) => {
      if (button.dataset.confirmReady === "true") return;
      button.dataset.confirmReady = "true";
      button.addEventListener("click", (event) => {
        if (!window.confirm(button.dataset.confirm || "Подтвердить действие?")) {
          event.preventDefault();
        }
      });
    });
  };

  const authUploadFailure = (code) => [
    "csrf_token_missing",
    "csrf_token_invalid",
    "auth_session_required_for_manual_upload",
    "auth_session_invalid",
    "auth_session_expired"
  ].includes(code);
  const conflictUploadFailure = (code) => [
    "media_revision_fingerprint_conflict",
    "media_revision_not_accepting_uploads",
    "meeting_not_accepting_uploads",
    "idempotency_conflict"
  ].includes(code);
  const uploadFailureMessage = (code) => ({
    empty_media_upload: "Файл пустой",
    upload_part_bytes_exceeded: "Файл слишком большой",
    unsafe_meeting_title: "Измените название"
  })[code] || "Не удалось загрузить";

  const formatBytes = (value) => {
    if (!Number.isFinite(value) || value <= 0) return "";
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
    return `${(value / 1024 / 1024).toFixed(value < 10 * 1024 * 1024 ? 1 : 0)} MB`;
  };

  const readMediaDuration = (file) => new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const media = document.createElement(file.type?.startsWith("video/") ? "video" : "audio");
    let settled = false;
    const done = (value) => {
      if (settled) return;
      settled = true;
      URL.revokeObjectURL(url);
      resolve(value);
    };
    const timer = window.setTimeout(() => done(null), 3500);
    media.preload = "metadata";
    media.onloadedmetadata = () => {
      window.clearTimeout(timer);
      done(Number.isFinite(media.duration) && media.duration > 0 ? Math.ceil(media.duration) : null);
    };
    media.onerror = () => {
      window.clearTimeout(timer);
      done(null);
    };
    media.src = url;
  });

  const currentMeetingListUrl = () => {
    const fallback = `${window.location.pathname}${window.location.search}`;
    const form = document.querySelector(".cabinet-list-controls");
    if (!(form instanceof HTMLFormElement)) return fallback;
    try {
      const url = new URL(form.action || fallback, window.location.href);
      const current = new URL(fallback, window.location.href);
      const params = new URLSearchParams(current.search);
      new URLSearchParams(url.search).forEach((value, key) => params.set(key, value));
      new FormData(form).forEach((value, key) => {
        if (typeof value !== "string") return;
        params.delete(key);
        if (value) params.append(key, value);
      });
      url.search = params.toString();
      return `${url.pathname}${url.search}`;
    } catch {
      return fallback;
    }
  };

  const refreshMeetingList = async () => {
    const target = document.querySelector("#meeting-list-region");
    if (!target || !window.htmx?.ajax) return;
    const url = currentMeetingListUrl();
    try {
      await window.htmx.ajax("GET", url, {
        target: "#meeting-list-region",
        select: "#meeting-list-region",
        swap: "outerHTML"
      });
    } catch (_err) {
      // The accepted meeting link remains available if the list refresh cannot complete.
    }
  };

  const initManualUpload = () => {
    const dialog = document.querySelector("[data-manual-upload-dialog]");
    if (!dialog || dialog.dataset.manualUploadReady === "true") return;
    dialog.dataset.manualUploadReady = "true";

    const form = dialog.querySelector("[data-manual-upload-form]");
    const dropZone = dialog.querySelector("[data-manual-upload-dropzone]");
    const dropTitle = dialog.querySelector("[data-manual-upload-drop-title]");
    const fileInput = dialog.querySelector("[data-manual-upload-file]");
    const fileCard = dialog.querySelector("[data-manual-upload-file-card]");
    const fileName = dialog.querySelector("[data-manual-upload-file-name]");
    const titleInput = dialog.querySelector("[data-manual-upload-title]");
    const archiveInput = dialog.querySelector("[data-manual-upload-archive]");
    const durationInput = dialog.querySelector("[data-manual-upload-duration]");
    const localIdInput = dialog.querySelector("[data-manual-upload-local-id]");
    const fileMeta = dialog.querySelector("[data-manual-upload-file-meta]");
    const fileDuration = dialog.querySelector("[data-manual-upload-file-duration]");
    const validation = dialog.querySelector("[data-manual-upload-validation]");
    const submit = dialog.querySelector("[data-manual-upload-submit]");
    let selectedFile = null;
    let lastTrigger = null;
    let uploadCounter = 0;
    const activeUploadActivities = new Set();

    const setValidation = (message = "", tone = "neutral") => {
      if (!validation) return;
      validation.textContent = message;
      validation.dataset.tone = tone;
      validation.hidden = !message;
    };

    const syncReady = () => {
      const duration = Number.parseInt(durationInput?.value || "0", 10);
      const ready = Boolean(
        dialog.dataset.uploadAvailable === "true"
          && selectedFile
          && Number.isFinite(duration)
          && duration > 0
          && csrfToken,
      );
      if (submit) submit.disabled = !ready;
    };

    const ensureLocalId = () => {
      if (!localIdInput || localIdInput.value) return;
      localIdInput.value = `manual-upload-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
    };

    const resetFilePreview = () => {
      if (fileCard) fileCard.hidden = true;
      if (fileName) fileName.textContent = "Файл не выбран";
      if (fileMeta) fileMeta.textContent = "";
      if (fileDuration) fileDuration.textContent = "";
      if (dropTitle) dropTitle.textContent = "Перетащите файл";
      dropZone?.classList.remove("has-file");
    };

    const resetDraft = () => {
      selectedFile = null;
      if (fileInput) fileInput.value = "";
      if (titleInput) titleInput.value = "";
      if (archiveInput) archiveInput.checked = true;
      if (durationInput) durationInput.value = "";
      if (localIdInput) localIdInput.value = "";
      resetFilePreview();
      setValidation();
      syncReady();
    };

    const ensureUploadHost = () => {
      let host = document.querySelector("[data-upload-activity-list]");
      if (host) return host;
      host = document.createElement("div");
      host.className = "upload-activity-list";
      host.dataset.uploadActivityList = "";
      const listRegion = document.querySelector("#meeting-list-region");
      const toolbar = document.querySelector(".meeting-toolbar");
      if (listRegion?.parentNode) listRegion.parentNode.insertBefore(host, listRegion);
      else toolbar?.after(host);
      return host;
    };

    const announceUploadActivity = (activity, message) => {
      const announcer = document.querySelector("[data-upload-activity-announcer]");
      if (!announcer || !message) return;
      const title = activity.titleLabel?.textContent?.trim() || "Загрузка";
      announcer.textContent = `${title}: ${message}`;
    };

    const updateActivityControls = (activity) => {
      const state = activity.state;
      if (activity.cancelButton) activity.cancelButton.hidden = state !== "uploading";
      if (activity.retryButton) {
        activity.retryButton.hidden = state !== "failed" || activity.recoveryMode !== null;
      }
      if (activity.recoverButton) {
        activity.recoverButton.hidden = state !== "failed" || activity.recoveryMode === null;
        if (activity.recoveryMode === "auth") activity.recoverButton.textContent = "Обновить страницу";
        if (activity.recoveryMode === "conflict") activity.recoverButton.textContent = "Выбрать другой файл";
      }
      if (activity.resumeButton) activity.resumeButton.hidden = state !== "canceled";
      if (activity.detailLink) activity.detailLink.hidden = !activity.detailHref;
    };

    const setActivityProgress = (activity, value, determinate = true) => {
      const percent = Math.max(0, Math.min(99, Number.isFinite(value) ? value : 0));
      activity.progressDeterminate = determinate;
      activity.progress?.classList.toggle("is-indeterminate", !determinate);
      if (determinate) {
        if (activity.progress) activity.progress.hidden = false;
        activity.progress?.setAttribute("aria-valuenow", String(percent));
        if (activity.progressBar) activity.progressBar.style.width = `${percent}%`;
        if (activity.percentLabel) {
          activity.percentLabel.textContent = `${percent}%`;
          activity.percentLabel.hidden = false;
        }
        const bucket = Math.floor(percent / 10) * 10;
        if (bucket >= 10 && bucket !== activity.announcedProgressBucket) {
          activity.announcedProgressBucket = bucket;
          announceUploadActivity(activity, `Загружаем ${bucket}%`);
        }
      } else {
        if (activity.progress) activity.progress.hidden = false;
        activity.progress?.removeAttribute("aria-valuenow");
        if (activity.progressBar) activity.progressBar.style.width = "0";
        if (activity.percentLabel) {
          activity.percentLabel.textContent = "";
          activity.percentLabel.hidden = true;
        }
      }
    };

    const setActivityState = (activity, state, message, tone = "neutral") => {
      const previousState = activity.state;
      activity.state = state;
      if (!activity.row) return;
      activity.row.dataset.uploadActivityState = state;
      if (activity.status) {
        activity.status.textContent = message;
        activity.status.dataset.tone = tone;
      }
      const progressActive = state === "uploading";
      if (activity.progress) {
        activity.progress.hidden = !progressActive;
        if (!progressActive) {
          activity.progress.classList.remove("is-indeterminate");
          activity.progress.removeAttribute("aria-valuenow");
        }
      }
      if (activity.progressBar && !progressActive) activity.progressBar.style.width = "0";
      if (activity.percentLabel && !progressActive) {
        activity.percentLabel.textContent = "";
        activity.percentLabel.hidden = true;
      }
      if (state !== previousState) announceUploadActivity(activity, message);
      updateActivityControls(activity);
    };

    const clearUploadActivityPayload = (activity) => {
      activity.file = null;
      activity.title = "";
      activity.duration = 0;
      activity.localId = "";
    };

    const scrubUploadActivities = () => {
      activeUploadActivities.forEach((activity) => {
        const xhr = activity.xhr;
        activity.xhr = null;
        if (xhr && !activity.accepted) {
          xhr.onload = null;
          xhr.onerror = null;
          xhr.onabort = null;
          xhr.upload.onprogress = null;
          xhr.abort();
        }
        clearUploadActivityPayload(activity);
        activity.row?.replaceChildren();
        activity.row = null;
      });
      activeUploadActivities.clear();
    };

    const revokedUploadMeetingIds = new Set();
    revokeManualUploadMeeting = (meetingId) => {
      revokedUploadMeetingIds.add(meetingId);
      for (const activity of activeUploadActivities) {
        if (activity.meetingId !== meetingId) continue;
        clearUploadActivityPayload(activity);
        activity.detailHref = "";
        activity.detailLink?.removeAttribute("href");
        activity.row?.remove();
        activity.row = null;
        activeUploadActivities.delete(activity);
        document.querySelector("[data-upload-activity-announcer]")?.replaceChildren();
      }
    };

    const createUploadActivity = ({ file, title, duration, localId, archiveAudio }) => {
      const host = ensureUploadHost();
      uploadCounter += 1;
      const row = document.createElement("article");
      row.className = "upload-activity-row";
      row.dataset.uploadActivityRow = "";
      row.dataset.uploadActivityState = "queued";
      row.innerHTML = `
        <span class="upload-activity-icon" aria-hidden="true"></span>
        <div class="upload-activity-copy">
          <strong data-upload-activity-title></strong>
          <span data-upload-activity-meta></span>
          <span class="upload-activity-state">
            <span data-upload-activity-status></span>
            <span class="upload-activity-percent" data-upload-activity-percent hidden></span>
          </span>
          <span class="upload-activity-progress" role="progressbar" aria-label="Прогресс загрузки" aria-valuemin="0" aria-valuemax="100" hidden>
            <span data-upload-activity-progress-bar></span>
          </span>
        </div>
        <div class="upload-activity-actions" aria-label="Управление загрузкой">
          <button class="button quiet upload-activity-action" type="button" data-upload-activity-cancel>Отменить</button>
          <button class="button quiet upload-activity-action" type="button" data-upload-activity-retry hidden>Повторить</button>
          <button class="button quiet upload-activity-action" type="button" data-upload-activity-recover hidden>Восстановить</button>
          <button class="button quiet upload-activity-action" type="button" data-upload-activity-resume hidden>Продолжить</button>
          <a class="button quiet upload-activity-action" href="#" data-upload-activity-detail hidden>Открыть</a>
        </div>
      `;
      host.prepend(row);

      const displayTitle = title || file.name || `Загрузка ${uploadCounter}`;
      const activity = {
        row,
        file,
        title,
        duration,
        localId,
        archiveAudio,
        state: "queued",
        xhr: null,
        accepted: false,
        recoveryMode: null,
        detailHref: "",
        progressDeterminate: true,
        announcedProgressBucket: null,
        titleLabel: row.querySelector("[data-upload-activity-title]"),
        meta: row.querySelector("[data-upload-activity-meta]"),
        status: row.querySelector("[data-upload-activity-status]"),
        progress: row.querySelector(".upload-activity-progress"),
        progressBar: row.querySelector("[data-upload-activity-progress-bar]"),
        percentLabel: row.querySelector("[data-upload-activity-percent]"),
        cancelButton: row.querySelector("[data-upload-activity-cancel]"),
        retryButton: row.querySelector("[data-upload-activity-retry]"),
        recoverButton: row.querySelector("[data-upload-activity-recover]"),
        resumeButton: row.querySelector("[data-upload-activity-resume]"),
        detailLink: row.querySelector("[data-upload-activity-detail]")
      };
      if (activity.titleLabel) activity.titleLabel.textContent = displayTitle;
      if (activity.meta) {
        activity.meta.textContent = `${file.name || "Файл"} · ${formatBytes(file.size)} · ${duration} сек.`;
      }
      activeUploadActivities.add(activity);
      row.addEventListener("click", (event) => {
        if (!(event.target instanceof Element)) return;
        if (event.target.closest("[data-upload-activity-cancel]")) {
          if (activity.xhr && !activity.accepted) activity.xhr.abort();
          return;
        }
        if (event.target.closest("[data-upload-activity-retry]")) {
          startActivityUpload(activity, { continued: false });
          return;
        }
        if (event.target.closest("[data-upload-activity-recover]")) {
          if (activity.recoveryMode === "auth") {
            window.location.reload();
          } else if (activity.recoveryMode === "conflict") {
            resetDraft();
            openDialog(lastTrigger);
          }
          return;
        }
        if (event.target.closest("[data-upload-activity-resume]")) {
          startActivityUpload(activity, { continued: true });
        }
      });
      return activity;
    };

    const startActivityUpload = (activity, { continued = false } = {}) => {
      if (!activity.file || activity.xhr || activity.accepted) return;
      const data = new FormData();
      data.append("file", activity.file);
      data.append("duration_seconds", String(activity.duration));
      data.append("local_recording_id", activity.localId);
      data.append("archive_audio", activity.archiveAudio ? "true" : "false");
      if (activity.title) data.append("title", activity.title);

      const xhr = new XMLHttpRequest();
      activity.xhr = xhr;
      activity.accepted = false;
      activity.recoveryMode = null;
      activity.announcedProgressBucket = null;
      setActivityState(activity, "uploading", continued ? "Загрузка продолжена" : "Загрузка");
      setActivityProgress(activity, 0, true);

      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable) {
          setActivityProgress(activity, 0, false);
          return;
        }
        const percent = Math.max(0, Math.min(99, Math.round((event.loaded / event.total) * 100)));
        setActivityProgress(activity, percent, true);
        setActivityState(activity, "uploading", "Загрузка");
      };
      xhr.onload = async () => {
        activity.xhr = null;
        let payload = {};
        try {
          payload = JSON.parse(xhr.responseText || "{}");
        } catch (_err) {
          payload = {};
        }
        if (xhr.status >= 200 && xhr.status < 300) {
          activity.accepted = true;
          const meetingId = payload.meeting?.meeting_id;
          if (meetingId) {
            activity.meetingId = meetingId;
            // The server may commit before its upload response reaches this page.
            if (revokedUploadMeetingIds.has(meetingId)) {
              revokeManualUploadMeeting(meetingId);
              return;
            }
            activity.row.dataset.uploadActivityMeetingId = meetingId;
            activity.row.dataset.meetingId = meetingId;
            activity.detailHref = `${dialog.dataset.uploadDetailBase || "/meetings"}/${meetingId}`;
            if (activity.detailLink) activity.detailLink.href = activity.detailHref;
          }
          const workflowStarted = payload.workflow_started === true;
          setActivityState(
            activity,
            "accepted",
            workflowStarted
              ? "На сервере · Обрабатываем"
              : "На сервере · Ждёт обработки",
            workflowStarted ? "success" : "warning"
          );
          clearUploadActivityPayload(activity);
          applyNativeDeletionOperations(nativeDeletionOperations);
          await refreshMeetingList();
          return;
        }
        const failureCode = typeof payload.code === "string" ? payload.code : "";
        const recoveryKind = authorizationRecoveryKind(
          xhr.status,
          xhr.getResponseHeader("X-GRAF-Cabinet-Recovery") || "",
          failureCode,
        );
        if (recoveryKind) {
          renderMeetingListRecovery(recoveryKind);
          return;
        }
        activity.recoveryMode = authUploadFailure(failureCode)
          ? "auth"
          : conflictUploadFailure(failureCode) ? "conflict" : null;
        setActivityState(activity, "failed", uploadFailureMessage(failureCode), "error");
      };
      xhr.onerror = () => {
        activity.xhr = null;
        setActivityState(activity, "failed", "Не удалось загрузить", "error");
      };
      xhr.onabort = () => {
        activity.xhr = null;
        if (!activity.accepted) {
          setActivityState(activity, "canceled", "Загрузка остановлена", "warning");
        }
      };
      xhr.open("POST", dialog.dataset.uploadEndpoint || "/api/v1/cabinet/media-uploads");
      xhr.setRequestHeader("X-CSRF-Token", csrfToken);
      xhr.send(data);
    };

    const setSelectedFile = async (file) => {
      selectedFile = file || null;
      if (localIdInput) localIdInput.value = "";
      if (durationInput) durationInput.value = "";
      if (!selectedFile) {
        resetFilePreview();
        setValidation();
        syncReady();
        return;
      }

      ensureLocalId();
      if (fileCard) fileCard.hidden = false;
      if (fileName) fileName.textContent = selectedFile.name || "Файл без названия";
      if (fileMeta) fileMeta.textContent = formatBytes(selectedFile.size);
      if (fileDuration) fileDuration.textContent = "Проверяем…";
      if (dropTitle) dropTitle.textContent = "Файл выбран";
      dropZone?.classList.add("has-file");
      setValidation();

      const activeFile = selectedFile;
      const duration = await readMediaDuration(selectedFile);
      if (activeFile !== selectedFile) return;
      if (duration && durationInput) {
        durationInput.value = String(duration);
        if (fileDuration) fileDuration.textContent = `${duration} сек.`;
        setValidation();
      } else {
        if (fileDuration) fileDuration.textContent = "Длительность не прочитана";
        setValidation("Не удалось прочитать длительность файла. Выберите другой аудио- или видеофайл.", "error");
      }
      syncReady();
    };

    const focusDialogElement = (element) => element?.focus({ preventScroll: true });

    const openDialog = (trigger) => {
      lastTrigger = trigger;
      if (dialog.dataset.uploadAvailable !== "true" || !csrfToken) {
        setValidation("Войдите снова, чтобы загрузить файл.", "error");
      }
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
      dialog.scrollTop = 0;
      const focusTarget = fileInput || dialog.querySelector("a,button,input");
      focusDialogElement(focusTarget);
    };

    const closeDialog = ({ restoreFocus = true } = {}) => {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
      if (restoreFocus) focusDialogElement(lastTrigger);
    };

    scrubManualUploadPrivateState = ({ authorizationLost = false } = {}) => {
      const wasOpen = dialog.open || dialog.hasAttribute("open");
      if (authorizationLost) dialog.dataset.uploadAvailable = "false";
      scrubUploadActivities();
      resetDraft();
      if (wasOpen) closeDialog({ restoreFocus: false });
      if (authorizationLost) {
        document.querySelectorAll("[data-manual-upload-open]").forEach((trigger) => {
          if (trigger instanceof HTMLButtonElement) trigger.disabled = true;
          trigger.setAttribute(
            "aria-label",
            "Загрузить запись — недоступно. Войдите снова.",
          );
        });
      }
      lastTrigger = null;
      return wasOpen;
    };

    dialog.addEventListener("keydown", (event) => trapModalFocus(dialog, event, { cycleAll: true }));
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      closeDialog();
    });
    dialog.addEventListener("focusin", (event) => {
      const target = event.target === fileInput ? dropZone : event.target;
      if (target instanceof HTMLElement) target.scrollIntoView({ block: "nearest" });
    });

    document.body.addEventListener("click", (event) => {
      if (!(event.target instanceof Element)) return;
      const button = event.target.closest("[data-manual-upload-open]");
      if (!button) return;
      event.preventDefault();
      openDialog(button);
    });

    dialog.querySelectorAll("[data-manual-upload-close]").forEach((button) => {
      button.addEventListener("click", closeDialog);
    });
    form?.addEventListener("submit", (event) => event.preventDefault());

    fileInput?.addEventListener("change", async () => {
      await setSelectedFile(fileInput.files?.[0] || null);
    });

    if (dropZone) {
      const hasDraggedFiles = (event) => Array.from(event.dataTransfer?.types || []).includes("Files");
      const stopDropEvent = (event) => {
        event.preventDefault();
        event.stopPropagation();
      };
      ["dragenter", "dragover"].forEach((type) => {
        dropZone.addEventListener(type, (event) => {
          if (!hasDraggedFiles(event)) return;
          stopDropEvent(event);
          dropZone.classList.add("is-dragover");
          if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
        });
      });
      dropZone.addEventListener("dragleave", (event) => {
        const nextTarget = event.relatedTarget;
        if (!(nextTarget instanceof Node) || !dropZone.contains(nextTarget)) {
          dropZone.classList.remove("is-dragover");
        }
      });
      dropZone.addEventListener("drop", async (event) => {
        stopDropEvent(event);
        dropZone.classList.remove("is-dragover");
        const files = Array.from(event.dataTransfer?.files || []);
        if (files.length > 1) {
          selectedFile = null;
          if (fileInput) fileInput.value = "";
          if (durationInput) durationInput.value = "";
          if (localIdInput) localIdInput.value = "";
          resetFilePreview();
          setValidation("Можно загрузить только один файл.", "error");
          syncReady();
          return;
        }
        await setSelectedFile(files[0] || null);
      });
    }

    submit?.addEventListener("click", () => {
      if (!selectedFile || !durationInput || !localIdInput || !csrfToken) {
        if (!selectedFile) setValidation("Выберите один файл.", "error");
        else if (!csrfToken) setValidation("Войдите снова, чтобы загрузить файл.", "error");
        syncReady();
        return;
      }
      const duration = Number.parseInt(durationInput.value || "0", 10);
      if (!Number.isFinite(duration) || duration <= 0) {
        setValidation("Не удалось прочитать длительность файла. Выберите другой аудио- или видеофайл.", "error");
        syncReady();
        return;
      }
      ensureLocalId();
      const title = titleInput?.value?.trim();
      const activity = createUploadActivity({
        file: selectedFile,
        title,
        duration,
        localId: localIdInput.value,
        archiveAudio: archiveInput?.checked !== false,
      });
      startActivityUpload(activity);
      closeDialog();
      resetDraft();
    });

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) closeDialog();
    });

    if (window.location.hash === "#manual-upload") {
      const trigger = document.querySelector("[data-manual-upload-open]");
      if (trigger) {
        const params = new URLSearchParams(window.location.search);
        if (params.get("archive_audio") === "false" && archiveInput) archiveInput.checked = false;
        openDialog(trigger);
      }
    }
  };

  const setRailPinned = (shell, toggle, pinned) => {
    shell.classList.toggle("is-rail-pinned", pinned);
    toggle.setAttribute("aria-expanded", pinned ? "true" : "false");
    const label = shell.dataset.activeNav === "settings"
      ? (pinned ? "Скрыть разделы настроек" : "Показать разделы настроек")
      : (pinned ? "Скрыть боковую панель" : "Показать боковую панель");
    toggle.setAttribute("aria-label", label);
    toggle.setAttribute("title", label);
    shell.setAttribute("data-rail-tooltip", label);
  };

  const initCabinetRail = () => {
    document.querySelectorAll("[data-cabinet-shell]").forEach((shell) => {
      const sidebar = shell.querySelector("[data-cabinet-navigation]");
      const toggle = shell.querySelector("[data-cabinet-rail-toggle]");
      if (!sidebar || !toggle || shell.dataset.railReady === "true") return;
      shell.dataset.railReady = "true";
      const settingsRail = shell.dataset.activeNav === "settings";
      const expandedMedia = window.matchMedia(
        settingsRail ? "(min-width: 768px)" : shell.classList.contains("desktop-embedded") ? "(min-width: 1121px)" : "(min-width: 981px)"
      );
      const narrowMedia = window.matchMedia("(max-width: 640px)");
      const railKey = shell.dataset.activeNav === "settings" ? "graf-settings-rail" : "graf-cabinet-rail";
      const storedRailState = sessionStorage.getItem(railKey);
      let manuallySet = ["expanded", "collapsed"].includes(storedRailState);
      let preferredPinned = manuallySet
        ? storedRailState === "expanded"
        : shell.classList.contains("is-rail-pinned") || expandedMedia.matches;
      const syncViewport = () => {
        if (settingsRail && expandedMedia.matches) {
          setRailPinned(shell, toggle, true);
          return;
        }
        if (!manuallySet) preferredPinned = expandedMedia.matches;
        setRailPinned(shell, toggle, preferredPinned && !(narrowMedia.matches && shell.querySelector("main")?.contains(document.activeElement)));
      };
      const setManualRailState = (pinned) => {
        manuallySet = true;
        preferredPinned = pinned;
        sessionStorage.setItem(railKey, pinned ? "expanded" : "collapsed");
        setRailPinned(shell, toggle, pinned);
      };
      setRailPinned(shell, toggle, (settingsRail && expandedMedia.matches || preferredPinned) && !(narrowMedia.matches && shell.querySelector("main")?.contains(document.activeElement)));
      expandedMedia.addEventListener("change", syncViewport);
      narrowMedia.addEventListener("change", syncViewport);
      shell.addEventListener("focusin", (event) => {
        if (narrowMedia.matches && shell.querySelector("main")?.contains(event.target)) setRailPinned(shell, toggle, false);
      });
      toggle.addEventListener("click", () => {
        setManualRailState(!shell.classList.contains("is-rail-pinned"));
        toggle.focus({ preventScroll: true });
      });
      document.addEventListener("keydown", (event) => {
        const openOverlay = document.querySelector(
          "dialog[open], [data-profile-menu]:not([hidden])"
        );
        if (event.key === "Escape" && !openOverlay && !(settingsRail && expandedMedia.matches)) {
          const focusWasInSidebar = settingsRail && sidebar.contains(document.activeElement);
          setManualRailState(false);
          if (focusWasInSidebar) toggle.focus({ preventScroll: true });
        }
      });
    });
  };

  let cabinetTooltipsReady = false;
  const positionCabinetTooltip = (body) => {
    const trigger = body.closest(".cabinet-tooltip")?.querySelector(".cabinet-tooltip__trigger");
    if (!trigger) return;
    const anchor = trigger.getBoundingClientRect();
    const scale = body.offsetWidth ? body.getBoundingClientRect().width / body.offsetWidth : 1;
    body.style.setProperty("--tooltip-viewport-width", `${window.innerWidth / scale}px`);
    body.style.setProperty("--tooltip-viewport-height", `${window.innerHeight / scale}px`);
    const rect = body.getBoundingClientRect();
    const left = Math.max(8, Math.min(anchor.left, window.innerWidth - rect.width - 8));
    const below = anchor.bottom + 8;
    const top = Math.max(8, Math.min(
      below + rect.height <= window.innerHeight - 8 ? below : anchor.top - rect.height - 8,
      window.innerHeight - rect.height - 8,
    ));
    body.style.setProperty("--tooltip-left", `${left / scale}px`);
    body.style.setProperty("--tooltip-top", `${top / scale}px`);
    body.style.setProperty("--tooltip-bottom", "auto");
  };

  const initCabinetTooltips = () => {
    if (cabinetTooltipsReady) return;
    cabinetTooltipsReady = true;
    const show = (root) => {
      const body = root.querySelector(".cabinet-tooltip__body");
      if (!body || typeof body.showPopover !== "function") return;
      if (!body.matches(":popover-open")) body.showPopover();
      positionCabinetTooltip(body);
    };
    // Delegation also covers HTMX replacements without retaining old controls.
    ["pointerover", "focusin"].forEach((name) => document.addEventListener(name, (event) => {
      const root = event.target.closest?.(".cabinet-tooltip");
      if (root && !root.contains(event.relatedTarget)) show(root);
    }));
    ["pointerout", "focusout"].forEach((name) => document.addEventListener(name, (event) => {
      const root = event.target.closest?.(".cabinet-tooltip");
      if (!root || root.contains(event.relatedTarget)) return;
      // Allow the pointer to cross the small gap into the tooltip itself.
      window.setTimeout(() => {
        if (root.matches(":hover") || root.contains(document.activeElement)) return;
        root.querySelector(".cabinet-tooltip__body:popover-open")?.hidePopover();
      }, 150);
    }));
    document.addEventListener("click", (event) => {
      const trigger = event.target.closest?.(".cabinet-tooltip__trigger");
      if (!trigger || typeof trigger.popoverTargetElement?.showPopover !== "function") return;
      event.preventDefault();
      show(trigger.closest(".cabinet-tooltip"));
    });
    const reposition = () => document.querySelectorAll(".cabinet-tooltip__body:popover-open").forEach(positionCabinetTooltip);
    window.addEventListener("resize", reposition);
    document.addEventListener("scroll", reposition, true);
  };

  const initCabinetProfileMenus = () => {
    document.querySelectorAll("[data-profile-menu-root]").forEach((root) => {
      const trigger = root.querySelector("[data-profile-menu-trigger]");
      const menu = root.querySelector("[data-profile-menu]");
      if (!trigger || !menu || root.getAttribute("data-profile-menu-ready") === "true") return;
      root.setAttribute("data-profile-menu-ready", "true");
      const originalParent = root.parentElement;
      const mobileNav = root.closest("[data-cabinet-shell]")?.querySelector(".cabinet-mobile-nav");
      const mobileMedia = window.matchMedia("(max-width: 980px)");
      const syncProfileLocation = () => {
        if (!mobileNav) return;
        const target = mobileMedia.matches ? mobileNav : originalParent;
        if (root.parentElement !== target) target.append(root);
      };
      syncProfileLocation();
      if (mobileNav) mobileMedia.addEventListener("change", syncProfileLocation);
      const supportsPopover = typeof menu.showPopover === "function";
      const popoverOpen = () => supportsPopover && menu.matches(":popover-open");
      const positionMenu = () => {
        const rect = trigger.getBoundingClientRect();
        const scale = trigger.offsetWidth ? rect.width / trigger.offsetWidth : 1;
        menu.style.setProperty("--profile-menu-bottom", `${Math.max(8, window.innerHeight - rect.top + 8) / scale}px`);
        menu.style.setProperty("--profile-menu-viewport-width", `${window.innerWidth / scale}px`);
        menu.style.setProperty("--profile-menu-viewport-height", `${window.innerHeight / scale}px`);
      };
      const disclosures = Array.from(menu.querySelectorAll(".sidebar-profile-menu__disclosure"));
      const syncDisclosurePosition = (details) => {
        details.classList.remove("is-flipped", "is-inline");
        if (!details.open) return;
        const submenu = details.querySelector("[data-profile-menu-submenu]");
        if (!(submenu instanceof HTMLElement)) return;
        window.requestAnimationFrame(() => {
          if (!details.open || !details.isConnected) return;
          const rect = submenu.getBoundingClientRect();
          details.classList.toggle("is-flipped", rect.right > window.innerWidth - 8);
          const placed = submenu.getBoundingClientRect();
          details.classList.toggle("is-inline", placed.left < 8 || placed.right > window.innerWidth - 8
            || placed.top < 8 || placed.bottom > window.innerHeight - 8);
        });
      };
      let hoveredDisclosure = null;
      let disclosureCloseTimer;
      const closeDisclosures = (except = null) => {
        disclosures.forEach((details) => { if (details !== except) details.open = false; });
      };
      menu.addEventListener("pointerover", (event) => {
        if (event.pointerType !== "mouse" || !(event.target instanceof Element)) return;
        window.clearTimeout(disclosureCloseTimer);
        if (event.target === menu) return; // Padding connects the row to its submenu.
        hoveredDisclosure = event.target.closest(".sidebar-profile-menu__disclosure");
        closeDisclosures(hoveredDisclosure);
        if (hoveredDisclosure) hoveredDisclosure.open = true;
      });
      menu.addEventListener("pointerleave", (event) => {
        if (event.pointerType !== "mouse") return;
        if (event.relatedTarget instanceof Node && menu.contains(event.relatedTarget)) {
          window.clearTimeout(disclosureCloseTimer);
          return;
        }
        hoveredDisclosure = null;
        // Let the pointer cross the gap into the child panel without closing it.
        disclosureCloseTimer = window.setTimeout(() => {
          if (menu.matches(":hover") || menu.querySelector(":focus-visible")) return;
          closeDisclosures();
        }, 150);
      });
      menu.addEventListener("focusin", (event) => {
        closeDisclosures(event.target.closest(".sidebar-profile-menu__disclosure"));
      });
      disclosures.forEach((details) => {
        details.querySelector("summary")?.addEventListener("click", (event) => {
          // Hover already opened it. Keep native click activation for keyboard/touch.
          if (event.detail > 0 && hoveredDisclosure === details) event.preventDefault();
        });
        details.addEventListener("toggle", () => {
          if (details.open) closeDisclosures(details);
          syncDisclosurePosition(details);
        });
      });
      const setOpen = (open, restoreFocus = false) => {
        if (open) {
          positionMenu();
          menu.hidden = false;
          if (supportsPopover && !popoverOpen()) menu.showPopover();
        } else {
          if (popoverOpen()) menu.hidePopover();
          menu.hidden = true;
        }
        trigger.setAttribute("aria-expanded", open ? "true" : "false");
        if (!open) {
          window.clearTimeout(disclosureCloseTimer);
          hoveredDisclosure = null;
          disclosures.forEach((details) => { details.open = false; syncDisclosurePosition(details); });
        }
        if (!open && restoreFocus) trigger.focus({ preventScroll: true });
      };
      trigger.addEventListener("click", () => setOpen(menu.hidden || (supportsPopover && !popoverOpen())));
      window.addEventListener("resize", () => {
        if (!menu.hidden) {
          positionMenu();
          disclosures.forEach(syncDisclosurePosition);
        }
      });
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !menu.hidden) setOpen(false, true);
      });
      document.addEventListener("click", (event) => {
        if (!menu.hidden && event.target instanceof Node && !root.contains(event.target)) setOpen(false);
      });
    });
  };

  const stopPlaybackRecoveryPolling = () => {
    if (!playbackRecoveryTimer) return;
    window.clearInterval(playbackRecoveryTimer);
    playbackRecoveryTimer = null;
  };

  const renderMeetingDetailRecovery = (detail, kind) => {
    stopPlaybackRecoveryPolling();
    const playback = detail.closest("[data-cabinet-shell]")?.querySelector(".playback-bar");
    const player = playback?.querySelector("[data-playback-player]");
    player?.pause?.();
    player?.removeAttribute?.("src");
    player?.load?.();
    playback?.remove();
    const listPath = location.pathname.startsWith("/desktop/") || document.body?.dataset?.surfaceMode === "desktop_embedded"
      ? "/desktop/meetings"
      : "/meetings";
    const copy = {
      session: ["Нужно войти снова", "Сессия завершилась.", "Войти"],
      workspace: ["Нужно выбрать пространство", "Доступ к выбранному пространству больше не подтверждён.", "Войти и выбрать пространство"],
      deleting: ["Удаление ожидает подтверждения", "Запрос сохранён в приложении. Состояние доступно в разделе «Удаления».", "К списку встреч"],
      deleted: ["Запись удалена из списка", "Состояние очистки доступно в разделе «Удаления».", "К списку встреч"],
      unavailable: ["Встреча больше недоступна", "Запись удалена или доступ закрыт.", "К списку встреч"],
    }[kind] || ["Встреча больше недоступна", "Запись удалена или доступ закрыт.", "К списку встреч"];
    const recoveryTemplate = document.querySelector("[data-meeting-detail-recovery-template]");
    const recovery = recoveryTemplate?.content?.firstElementChild?.cloneNode(true);
    const state = recovery?.querySelector("[data-cabinet-state]");
    const title = recovery?.querySelector("h1");
    const body = recovery?.querySelector(".cabinet-state__description");
    const action = recovery?.querySelector(".cabinet-state__action a");
    if (
      !(recovery instanceof HTMLElement)
      || !(state instanceof HTMLElement)
      || !(title instanceof HTMLElement)
      || !(body instanceof HTMLElement)
      || !(action instanceof HTMLElement)
    ) {
      detail.textContent = "";
      document.title = "GRAF";
      clearMeetingHistoryCache();
      location.replace(listPath);
      return;
    }
    title.textContent = copy[0];
    body.textContent = copy[1];
    action.textContent = copy[2];
    const requiresSignIn = kind === "session" || kind === "workspace";
    action.href = requiresSignIn
      ? `/login?next=${encodeURIComponent(listPath)}`
      : listPath;
    state.setAttribute("aria-labelledby", title.id);
    detail.replaceWith(recovery);
    document.title = `${copy[0]} - GRAF`;
    clearMeetingHistoryCache();
    try {
      sessionStorage.removeItem("htmx-current-path-for-history");
    } catch {
      // The neutral URL still replaces the private detail path when storage is unavailable.
    }
    neutralizePrivateLocation(listPath);
    recovery.focus({ preventScroll: true });
  };

  const renderShareRequestError = (detail) => {
    const host = detail.querySelector("#meeting-share-host");
    if (!host) return;
    const status = document.createElement("p");
    status.className = "truth-copy meeting-share-action-error";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.textContent = "Не удалось открыть настройки доступа. Проверьте разрешения и попробуйте ещё раз.";
    host.replaceChildren(status);
  };

  const meetingDetailRecoveryKindFromXhr = (xhr, { preserveDetail = false } = {}) => {
    const status = Number(xhr?.status || 0);
    const problemCode = [403, 404, 410].includes(status) ? xhrProblemCode(xhr) : "";
    if (detailActionProblemCodes.has(problemCode)) return "";
    if (preserveDetail && (sharingActionProblemCodes.has(problemCode) || [404, 410].includes(status))) return "";
    if ([404, 410].includes(status)) return "unavailable";
    if (status === 401 || status === 403) {
      return authorizationRecoveryKind(
        status,
        xhr?.getResponseHeader?.("X-GRAF-Cabinet-Recovery") || "",
        problemCode,
        true,
      );
    }
    try {
      if (xhr?.responseURL && new URL(xhr.responseURL, window.location.href).pathname === "/login") {
        return "session";
      }
    } catch {
      // An invalid response URL cannot authorize retaining private detail content.
    }
    return "";
  };

  const recoverMeetingDetailFromResponse = async (response, { actionProblemCodes = new Set() } = {}) => {
    const detail = document.querySelector("[data-playback-poll-url]");
    if (!detail) return false;
    let recoveryKind = "";
    if (response.redirected) {
      try {
        if (new URL(response.url, window.location.href).pathname === "/login") {
          recoveryKind = "session";
        }
      } catch {
        recoveryKind = "session";
      }
    }
    const problemCode = [403, 404, 410].includes(response.status)
      ? await responseProblemCode(response)
      : "";
    if (!recoveryKind && (detailActionProblemCodes.has(problemCode) || actionProblemCodes.has(problemCode))) return false;
    if (!recoveryKind && [404, 410].includes(response.status)) recoveryKind = "unavailable";
    else if (!recoveryKind && (response.status === 401 || response.status === 403)) {
      recoveryKind = authorizationRecoveryKind(
        response.status,
        response.headers.get("X-GRAF-Cabinet-Recovery") || "",
        problemCode,
        true,
      );
    }
    if (!recoveryKind) return false;
    renderMeetingDetailRecovery(detail, recoveryKind);
    return true;
  };

  const initMeetingDetailAuthorizationRecovery = () => {
    const detail = document.querySelector("[data-playback-poll-url]");
    if (!detail || document.body.dataset.meetingDetailRecoveryReady === "true") return;
    document.body.dataset.meetingDetailRecoveryReady = "true";
    const recoverFromHtmx = (event) => {
      const currentDetail = document.querySelector("[data-playback-poll-url]");
      if (!currentDetail) return;
      const source = event.detail?.elt || event.target;
      const target = event.detail?.target;
      const belongsToDetail = target === currentDetail
        || (target instanceof Element && currentDetail.contains(target))
        || (source instanceof Element && currentDetail.contains(source));
      if (!belongsToDetail) return;
      const shareRequest = isShareRequest(source, target);
      const recoveryKind = meetingDetailRecoveryKindFromXhr(
        event.detail?.xhr,
        { preserveDetail: shareRequest },
      );
      if (!recoveryKind) {
        if (shareRequest && Number(event.detail?.xhr?.status || 0) >= 400) {
          event.preventDefault();
          if (event.detail) event.detail.shouldSwap = false;
          renderShareRequestError(currentDetail);
        }
        return;
      }
      event.preventDefault();
      if (event.detail) event.detail.shouldSwap = false;
      renderMeetingDetailRecovery(currentDetail, recoveryKind);
    };
    document.body.addEventListener("htmx:beforeSwap", recoverFromHtmx);
    document.body.addEventListener("htmx:responseError", recoverFromHtmx);
  };

  const playbackRecoveryCopy = "Не удалось обновить статус. GRAF попробует снова автоматически.";

  const detailPlayback = (detail) => {
    const playback = detail?.nextElementSibling;
    return playback?.matches?.(".detail-playback") ? playback : null;
  };

  const showPlaybackRecoveryNotice = (detail) => {
    const playback = detailPlayback(detail);
    const liveStatus = detail.querySelector("[data-playback-live-status]");
    if (playback && !playback.querySelector("[data-playback-recovery-copy]")) {
      const notice = document.createElement("p");
      notice.className = "truth-copy playback-recovery-copy";
      notice.dataset.playbackRecoveryCopy = "";
      notice.textContent = playbackRecoveryCopy;
      playback.append(notice);
    }
    if (liveStatus && liveStatus.textContent !== playbackRecoveryCopy) {
      liveStatus.textContent = playbackRecoveryCopy;
    }
  };

  const clearPlaybackRecoveryNotice = (detail) => {
    detailPlayback(detail)?.querySelector("[data-playback-recovery-copy]")?.remove();
  };

  const refreshPlaybackRecovery = async () => {
    const detail = document.querySelector("[data-playback-poll-url]");
    if (!detail || detail.dataset.playbackPollActive !== "true" || playbackRecoveryRequest) return;
    const pollUrl = detail.dataset.playbackPollUrl;
    if (!pollUrl) return;
    playbackRecoveryRequest = fetch(pollUrl, {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        "HX-Request": "true",
        ...(detail.dataset.cabinetEmbedded === "true" ? { "X-GRAF-Client": "desktop" } : {}),
      }
    });
    try {
      const response = await playbackRecoveryRequest;
      if (!detail.isConnected) return;
      if (await recoverMeetingDetailFromResponse(response)) return;
      if (!response.ok) {
        showPlaybackRecoveryNotice(detail);
        return;
      }
      const documentFragment = new DOMParser().parseFromString(await response.text(), "text/html");
      const nextDetail = documentFragment.querySelector("[data-playback-poll-url]");
      const currentPlayback = detailPlayback(detail);
      const nextPlayback = detailPlayback(nextDetail);
      const currentTranscript = detail.querySelector("[data-playback-transcript]");
      const nextTranscript = nextDetail?.querySelector("[data-playback-transcript]");
      const currentLiveStatus = detail.querySelector("[data-playback-live-status]");
      const nextLiveStatus = nextDetail?.querySelector("[data-playback-live-status]");
      if (!nextDetail || !currentPlayback || !nextPlayback || !currentTranscript || !nextTranscript) {
        showPlaybackRecoveryNotice(detail);
        return;
      }
      clearPlaybackRecoveryNotice(detail);
      detail.dataset.playbackPollActive = nextDetail.dataset.playbackPollActive || "false";
      const recoverySignature = (node) => [
        node.dataset.playbackState || "",
        node.dataset.sourceMode || "",
        ...["meetingId", "workspaceId", "mediaRevisionId", "processingResultId", "commentsAvailable", "commentsCanComment"].map(key => node.dataset[key] || ""),
        (node.textContent || "").trim()
      ].join("\u001f");
      const playbackUnchanged = recoverySignature(currentPlayback) === recoverySignature(nextPlayback);
      const playbackChanged = !playbackUnchanged;
      const transcriptChanged = currentTranscript.innerHTML !== nextTranscript.innerHTML;
      currentPlayback.dataset.playbackReason = nextPlayback.dataset.playbackReason || "";
      if (currentLiveStatus && nextLiveStatus && currentLiveStatus.textContent !== nextLiveStatus.textContent) {
        currentLiveStatus.textContent = nextLiveStatus.textContent || "";
      }
      if (!playbackChanged && !transcriptChanged) {
        initPlaybackRecoveryPolling();
        return;
      }
      if (playbackChanged && !refreshPlaybackContent(currentPlayback, nextPlayback)) {
        currentPlayback.querySelector("audio")?.pause();
        currentPlayback.replaceWith(nextPlayback);
      }
      if (transcriptChanged) currentTranscript.replaceWith(nextTranscript);
      initPlayback();
      initSpeakerTimelineResize();
      initSpeakerNameForms();
      initPlaybackRecoveryPolling();
    } catch {
      showPlaybackRecoveryNotice(detail);
      return;
    } finally {
      playbackRecoveryRequest = null;
    }
  };

  let recordingLifecycleTimer = null;
  let recordingLifecycleRequest = null;
  const refreshRecordingLifecycle = async () => {
    if (document.hidden || recordingLifecycleRequest) return;
    const detail = document.querySelector("main[data-meeting-id][data-playback-poll-url]");
    const rows = allRows().filter(row => /^[0-9a-f-]{36}$/i.test(row.dataset.meetingId || ""));
    const uploadRows = [...document.querySelectorAll("[data-upload-activity-meeting-id]")];
    const targets = detail ? [detail] : [...uploadRows, ...rows];
    const ids = [...new Set(targets.map(node => node.dataset.meetingId))];
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
    if (!ids.length || !csrf) return;
    const controller = new AbortController();
    recordingLifecycleRequest = controller;
    const timeout = setTimeout(() => controller.abort(), 10000);
    let changed = false;
    try {
      // Every visible alias participates; only the HTTP payload is capped.
      for (let offset = 0; offset < ids.length; offset += 100) {
        const batch = ids.slice(offset, offset + 100);
        const response = await fetch("/api/v1/desktop/recordings/lifecycle", {
          method: "POST", credentials: "same-origin", cache: "no-store", signal: controller.signal,
          headers: {"Content-Type":"application/json", "X-CSRF-Token":csrf, "Accept":"application/json"},
          body: JSON.stringify({meeting_ids:batch}),
        });
        if (csrf !== document.querySelector('meta[name="csrf-token"]')?.content) return;
        if (!response.ok) {
          if (response.status === 401 && detail?.isConnected) renderMeetingDetailRecovery(detail, "session");
          return;
        }
        const entries = await response.json();
        if (!Array.isArray(entries)) return;
        for (const entry of entries) {
          if (entry.target_type !== "meeting" || !batch.includes(entry.target_id) || entry.state === "allowed") continue;
          if (!["deletion_accepted", "unavailable"].includes(entry.state)) continue;
          revokeManualUploadMeeting(entry.target_id);
          for (const node of targets.filter(node => node.isConnected && node.dataset.meetingId === entry.target_id)) {
            if (node === detail) { renderMeetingDetailRecovery(node, "unavailable"); return; }
            selectedMeetingIds.delete(recordingRowIdentity(node));
            node.remove();
            changed = true;
          }
        }
      }
    } catch (_error) {
      // Lack of a response is not deletion authority. Existing media requests still enforce access.
    } finally {
      clearTimeout(timeout);
      recordingLifecycleRequest = null;
      if (changed) { updateMixedResultCount(); updateSelection(); requestMeetingListRefresh({restoreFocus:true}); }
    }
  };
  const initRecordingLifecyclePolling = () => {
    if (recordingLifecycleTimer) return;
    recordingLifecycleTimer = setInterval(refreshRecordingLifecycle, 30000);
    window.addEventListener("online", refreshRecordingLifecycle);
    window.addEventListener("focus", refreshRecordingLifecycle);
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) recordingLifecycleRequest?.abort();
      else refreshRecordingLifecycle();
    });
    refreshRecordingLifecycle();
  };

  const initPlaybackRecoveryPolling = () => {
    const detail = document.querySelector("[data-playback-poll-url]");
    const active = detail?.dataset.playbackPollActive === "true";
    if (!active && playbackRecoveryTimer) {
      stopPlaybackRecoveryPolling();
      return;
    }
    if (active && !playbackRecoveryTimer) {
      playbackRecoveryTimer = window.setInterval(() => {
        if (!document.hidden) refreshPlaybackRecovery();
      }, 3000);
    }
    if (document.body.dataset.playbackRecoveryListeners !== "true") {
      document.body.dataset.playbackRecoveryListeners = "true";
      window.addEventListener("online", refreshPlaybackRecovery);
      document.addEventListener("visibilitychange", () => {
        if (!document.hidden) refreshPlaybackRecovery();
      });
    }
  };

  const initSpeakerNameForms = () => {
    document.querySelectorAll("[data-speaker-manager]").forEach((manager) => {
      if (manager.dataset.speakerManagerReady === "true") return;
      manager.dataset.speakerManagerReady = "true";
      const toggle = manager.querySelector("[data-speaker-manager-toggle]");
      const popover = document.getElementById(toggle?.getAttribute("aria-controls") || "");
      if (!toggle || !popover) return;
      const close = () => {
        popover.hidden = true;
        toggle.setAttribute("aria-expanded", "false");
      };
      toggle.addEventListener("click", () => {
        const opening = popover.hidden;
        popover.hidden = !opening;
        toggle.setAttribute("aria-expanded", String(opening));
      });
      manager.addEventListener("keydown", (event) => {
        if (event.key !== "Escape" || popover.hidden) return;
        event.preventDefault();
        close();
        toggle.focus({ preventScroll: true });
      });
      document.addEventListener("click", (event) => {
        if (!popover.hidden && !manager.contains(event.target)) close();
      });
    });
    document.querySelectorAll("[data-speaker-name-open]").forEach((button) => {
      if (button.dataset.speakerNameOpenReady === "true") return;
      button.dataset.speakerNameOpenReady = "true";
      button.addEventListener("click", () => {
        const form = document.getElementById(button.getAttribute("aria-controls") || "");
        if (!form) return;
        form.hidden = false;
        button.setAttribute("aria-expanded", "true");
        form.querySelector("input[name='display_name']")?.focus({ preventScroll: true });
      });
    });
    document.querySelectorAll("[data-speaker-name-cancel]").forEach((button) => {
      if (button.dataset.speakerNameCancelReady === "true") return;
      button.dataset.speakerNameCancelReady = "true";
      button.addEventListener("click", () => {
        const form = button.closest("[data-speaker-name-form]");
        if (!form) return;
        form.hidden = true;
        const opener = document.querySelector(`[aria-controls="${form.id}"]`);
        opener?.setAttribute("aria-expanded", "false");
        opener?.focus({ preventScroll: true });
      });
    });
    document.querySelectorAll("[data-speaker-name-form]").forEach((form) => {
      if (form.dataset.speakerNameReady === "true") return;
      form.dataset.speakerNameReady = "true";
      form.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        event.preventDefault();
        event.stopPropagation();
        form.querySelector("[data-speaker-name-cancel]")?.click();
      });
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const error = form.querySelector("[data-speaker-name-error]");
        const submit = form.querySelector("button[type='submit']");
        const input = form.querySelector("input[name='display_name']");
        if (error) error.hidden = true;
        if (submit) submit.disabled = true;
        try {
          const response = await fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            credentials: "same-origin",
            headers: csrfToken ? { "X-CSRF-Token": csrfToken } : {}
          });
          if (await recoverMeetingDetailFromResponse(response)) return;
          if (!response.ok) throw new Error("speaker_name_save_failed");
          let responseText = "";
          if (typeof response.text === "function") {
            try {
              responseText = await response.text();
            } catch {
              responseText = "";
            }
          }
          const confirmedValue = input?.value.trim() || "";
          const speakerKey = form.dataset.speakerKey || "";
          const fallbackLabel = confirmedValue || speakerKey.replace(/^speaker_/i, "SPEAKER_");
          const confirmedLabel = speakerLabelFromResponse(responseText, speakerKey, fallbackLabel);
          replaceSpeakerNameInPlace(form, confirmedLabel, confirmedValue);
          if (submit) submit.disabled = false;
          const opener = Array.from(document.querySelectorAll("[aria-controls]"))
            .find((control) => control.getAttribute("aria-controls") === form.id);
          if (opener) {
            form.hidden = true;
            opener.setAttribute("aria-expanded", "false");
            opener.focus({ preventScroll: true });
          } else {
            submit?.focus({ preventScroll: true });
          }
        } catch {
          if (error) error.hidden = false;
          if (submit) submit.disabled = false;
          input?.focus({ preventScroll: true });
        }
      });
    });
  };

  const speakerLabelFromResponse = (responseText, speakerKey, fallback) => {
    if (!responseText || !speakerKey || typeof DOMParser === "undefined") return fallback;
    try {
      const parsed = new DOMParser().parseFromString(responseText, "text/html");
      const label = Array.from(parsed.querySelectorAll("[data-speaker-key]"))
        .filter((node) => node.dataset.speakerKey === speakerKey)
        .map((node) => node.querySelector(".timeline-label, .speaker-manager-name, .speaker-label, strong")?.textContent?.trim() || "")
        .find(Boolean);
      return label || fallback;
    } catch {
      return fallback;
    }
  };

  const replaceSpeakerNameInPlace = (form, displayLabel, confirmedValue) => {
    const speakerKey = form.dataset.speakerKey || "";
    if (!speakerKey) return;
    const nodes = Array.from(document.querySelectorAll("[data-speaker-key]"))
      .filter((node) => node.dataset.speakerKey === speakerKey);
    nodes.forEach((node) => {
      const timelineLabel = node.querySelector?.(".timeline-label");
      if (timelineLabel) timelineLabel.textContent = displayLabel;
      const managerName = node.querySelector?.(".speaker-manager-name");
      if (managerName) {
        managerName.textContent = displayLabel;
        managerName.title = displayLabel;
      }
      const transcriptLabel = node.querySelector?.(".speaker-label");
      if (transcriptLabel) transcriptLabel.textContent = displayLabel;
      const simpleLabel = node.querySelector?.("strong");
      if (simpleLabel) simpleLabel.textContent = displayLabel;
      const timelineSpeaker = node.querySelector?.(".timeline-speaker");
      if (timelineSpeaker) timelineSpeaker.title = displayLabel;
      node.querySelectorAll?.("[data-speaker-initials]").forEach((initials) => { initials.textContent = displayLabel.slice(0, 1).toUpperCase(); });
      if (node.hasAttribute?.("data-playback-avatar")) {
        node.title = displayLabel;
        node.setAttribute("aria-label", `Следующая реплика: ${displayLabel}`);
      }
      const listen = node.querySelector?.("[data-listen-speaker]");
      listen?.setAttribute("aria-label", `Слушать: ${displayLabel}`);
      const track = node.querySelector?.("[data-timeline-track]");
      if (track) track.setAttribute(
        "aria-label",
        `Дорожка ${displayLabel}: стрелки перемещают позицию`,
      );
      node.querySelectorAll?.("[data-lane-segment]").forEach((segment) => {
        const label = `${displayLabel} ${formatTime(Number(segment.dataset.startSeconds))}-${formatTime(Number(segment.dataset.endSeconds))}`;
        segment.title = label;
        segment.setAttribute("aria-label", label);
      });
      const nameInput = node.querySelector?.("input[name='display_name']");
      if (nameInput) nameInput.value = confirmedValue;
      const label = node.querySelector?.("label[for]");
      if (label) label.textContent = `Имя для ${displayLabel}`;
    });
  };

  const initContentExport = () => {
    const dialog = document.querySelector("[data-content-export-dialog]");
    const form = dialog?.querySelector("[data-content-export-form]");
    if (!dialog || !form || dialog.dataset.contentExportReady === "true") return;
    dialog.dataset.contentExportReady = "true";
    const main = form.closest(".detail-page-main");
    const directCopy = main?.querySelector("[data-detail-copy]");
    const directStatus = main?.querySelector("[data-detail-copy-status]");
    const scope = form.querySelector("[data-export-scope]");
    const format = form.querySelector("[data-export-format]");
    const title = dialog.querySelector("[data-export-dialog-title]");
    const status = form.querySelector("[data-export-status]");
    const submit = form.querySelector("[data-export-submit]");
    const copy = form.querySelector("[data-export-copy]");
    const speakers = form.querySelector("input[name='include_speaker_labels']");
    const timestamps = form.querySelector("input[name='include_timestamps']");
    const formatGroups = [
      ["Текст", [["txt", "Текст (.txt)"], ["md", "Markdown (.md)"]]],
      ["Таблицы", [["csv", "Таблица CSV (.csv)"], ["xlsx", "Excel (.xlsx)"]]],
      ["Данные", [["json", "JSON (.json)"]]],
      ["Субтитры", [["srt", "Субтитры (.srt)"], ["vtt", "WebVTT (.vtt)"]]]
    ];
    let returnFocus = null;
    let submitting = false;

    const setStatus = (message, state = "", target = status) => {
      if (!target?.isConnected) return;
      target.textContent = message;
      target.dataset.state = state;
    };
    const detailScope = () => main?.querySelector('[data-detail-tab][aria-selected="true"]')?.dataset.detailTab === "outcomes" ? "summary" : "transcript";
    const available = (selectedScope, requestedFormat) => {
      const option = Array.from(scope?.options || []).find((item) => item.value === selectedScope);
      const key = "exportFormats" + selectedScope.charAt(0).toUpperCase() + selectedScope.slice(1);
      return form.isConnected
        && main?.dataset.processingReplacementActive !== "true"
        && !!option && !option.disabled
        && (form.dataset[key] || "").split(",").includes(requestedFormat);
    };
    const syncAvailability = () => {
      if (submit) submit.disabled = submitting || !available(scope?.value || "", format?.value);
      if (copy) copy.disabled = submitting || !available(scope?.value || "", "txt");
      if (directCopy) {
        const allowed = available(detailScope(), "txt");
        directCopy.hidden = false;
        directCopy.disabled = submitting || !allowed;
        directCopy.setAttribute("aria-busy", submitting ? "true" : "false");
        directCopy.title = detailScope() === "summary" ? "Копировать итоги" : "Копировать расшифровку";
        if (!allowed && !submitting) setStatus("Содержимое этой вкладки пока недоступно для копирования.", "unavailable", directStatus);
        else if (directStatus?.dataset.state === "unavailable") setStatus("", "", directStatus);
      }
    };
    main?.addEventListener("detail-tab-change", syncAvailability);
    form.addEventListener("export-availability-change", syncAvailability);
    const updateOptions = () => {
      if (!scope || !format) return;
      const machineFormat = ["csv", "xlsx", "json"].includes(format.value);
      if (speakers) {
        if (machineFormat) speakers.checked = true;
        speakers.disabled = machineFormat;
      }
      if (timestamps) {
        if (machineFormat || format.value === "srt" || format.value === "vtt") timestamps.checked = true;
        timestamps.disabled = machineFormat || format.value === "srt" || format.value === "vtt";
      }
      syncAvailability();
    };
    const updateFormats = () => {
      if (!scope || !format) return;
      const key = "exportFormats" + scope.value.charAt(0).toUpperCase() + scope.value.slice(1);
      const values = (form.dataset[key] || "").split(",").filter(Boolean);
      const previous = format.value;
      const groups = formatGroups.map(([label, groupValues]) => {
        const available = groupValues.filter(([value]) => values.includes(value));
        if (!available.length) return null;
        const group = document.createElement("optgroup");
        group.label = label;
        group.append(...available.map(([value, text]) => {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = text;
          return option;
        }));
        return group;
      }).filter(Boolean);
      format.replaceChildren(...groups);
      if (values.includes(previous)) format.value = previous;
      setStatus("");
      updateOptions();
    };
    const close = () => {
      if (submitting) return;
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
      restoreMeetingActionFocus(returnFocus);
      returnFocus = null;
    };
    const open = (trigger) => {
      returnFocus = trigger;
      setStatus("");
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
      title?.focus({ preventScroll: true });
    };
    document.querySelectorAll("[data-export-dialog-open]").forEach((button) => {
      button.addEventListener("click", () => open(button));
    });
    dialog.querySelectorAll("[data-export-dialog-close], [data-export-dialog-cancel]").forEach(
      (button) => button.addEventListener("click", (event) => {
        event.preventDefault();
        close();
      })
    );
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      close();
    });
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) close();
    });
    dialog.addEventListener("keydown", (event) => trapModalFocus(dialog, event));
    scope?.addEventListener("change", updateFormats);
    format?.addEventListener("change", updateOptions);
    updateFormats();

    const include = (name) => form.querySelector("input[name='" + name + "']")?.checked === true;
    const buildPayload = (requestedFormat = format?.value, selectedScope = scope?.value || "transcript") => {
      return {
        content_scope: selectedScope,
        format: requestedFormat,
        processing_result_id: form.dataset.processingResultId,
        outcome_set_id: selectedScope === "transcript" ? null : (form.dataset.outcomeSetId || null),
        include_speaker_labels: include("include_speaker_labels"),
        include_timestamps: include("include_timestamps"),
        include_evidence: false
      };
    };
    const requestExport = async (requestedFormat = format?.value, selectedScope = scope?.value || "transcript") => {
      if (!available(selectedScope, requestedFormat)) throw new Error("export_unavailable");
      const token = form.dataset.csrfToken || csrfToken;
      const response = await fetch(form.dataset.endpoint, {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "X-CSRF-Token": token } : {})
        },
        body: JSON.stringify(buildPayload(requestedFormat, selectedScope))
      });
      if (await recoverMeetingDetailFromResponse(response)) return null;
      if (!response.ok) {
        const problem = await response.json().catch(() => ({}));
        throw new Error(problem.code || "export_failed");
      }
      return response;
    };
    const setBusy = (busy) => {
      submitting = busy;
      syncAvailability();
      if (busy) dialog.setAttribute("aria-busy", "true");
      else dialog.removeAttribute("aria-busy");
    };
    const errorMessage = (code) => ({
      export_revision_stale: "Данные изменились. Закройте окно, обновите встречу и повторите.",
      meeting_deletion_active: "Экспорт недоступен: встреча удаляется.",
      meeting_not_found: "Доступ к встрече изменился. Обновите страницу.",
      export_policy_denied: "Политика доступа к этому составу изменилась.",
      export_unavailable: "Этот состав сейчас недоступен по готовности или политике.",
      subtitle_timing_unavailable: "Не удалось подготовить субтитры: у одного из фрагментов нет корректного времени. Выберите другой формат, чтобы сохранить весь текст.",
      export_generation_failed: "Не удалось собрать файл. Повторите экспорт.",
      audit_unavailable: "Экспорт остановлен: не удалось сохранить обязательную запись аудита. Повторите позже.",
      unsupported_export_combination: "Выберите совместимый формат.",
      clipboard_unavailable: "Не удалось скопировать текст. Используйте скачивание TXT."
    }[code] || "Не удалось подготовить файл. Попробуйте ещё раз.");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (submitting || !scope || !format || !submit) return;
      const selectedScope = scope.value;
      const selectedFormat = format.value;
      if (!available(selectedScope, selectedFormat)) return;
      setBusy(true);
      setStatus("Готовим файл…", "progress");
      try {
        const response = await requestExport(selectedFormat, selectedScope);
        if (!response) return;
        const blob = await response.blob();
        if (!submit.isConnected || !available(selectedScope, selectedFormat)) throw new Error("export_unavailable");
        const disposition = response.headers.get("Content-Disposition") || "";
        const filename = disposition.match(/filename="([^"]+)"/)?.[1] || "graf-export." + selectedFormat;
        const href = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = href;
        link.download = filename;
        link.hidden = true;
        document.body.append(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(href), 60000);
        setStatus(
          form.dataset.exportDelivery === "save" ? "Файл готов к сохранению." : "Скачивание началось.",
          "success"
        );
        setBusy(false);
        close();
      } catch (error) {
        const code = error instanceof Error ? error.message : "export_failed";
        setStatus(errorMessage(code), "error");
        setBusy(false);
        if (submit.isConnected && !submit.disabled && dialog.open) submit.focus({ preventScroll: true });
      } finally {
        setBusy(false);
      }
    });
    const copyText = async (trigger, selectedScope) => {
      if (submitting || !trigger.isConnected || !available(selectedScope, "txt")) return;
      const feedback = trigger === directCopy ? directStatus : status;
      setBusy(true);
      setStatus("Готовим текст для копирования…", "progress", feedback);
      try {
        if (!navigator.clipboard?.writeText) throw new Error("clipboard_unavailable");
        const response = await requestExport("txt", selectedScope);
        if (!response) return;
        const text = await response.text();
        if (!trigger.isConnected || !available(selectedScope, "txt")) throw new Error("export_unavailable");
        await navigator.clipboard.writeText(text);
        setStatus("Текст скопирован.", "success", feedback);
      } catch (error) {
        const code = error instanceof Error ? error.message : "export_failed";
        setStatus(errorMessage(code), "error", feedback);
      } finally {
        setBusy(false);
      }
    };
    copy?.addEventListener("click", () => copyText(copy, scope?.value || "transcript"));
    directCopy?.addEventListener("click", () => copyText(directCopy, detailScope()));
    syncAvailability();
  };

  const initMeetingDeleteDialog = () => {
    const dialog = document.querySelector("[data-meeting-delete-dialog]");
    const opener = document.querySelector("[data-meeting-delete-dialog-open]");
    if (!dialog || !opener || dialog.dataset.ready === "true") return;
    dialog.dataset.ready = "true";
    dialog.querySelector("form")?.addEventListener("submit", async event => {
      if (window.GRAFRecordingDeletionBridgeVersion !== 1 || !window.webkit?.messageHandlers?.grafLocalRecording) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      const detail = document.querySelector("main[data-meeting-id]");
      if (!detail) return;
      const submit = dialog.querySelector('[type="submit"]');
      if (submit?.disabled) return;
      if (submit) submit.disabled = true;
      const result = await requestNativeDeletion([detail]);
      if (result.saved && (result.accepted || result.pending)) {
        detail.querySelectorAll("audio, video").forEach(player => { player.pause(); player.removeAttribute("src"); player.load(); });
        location.assign("/desktop/meetings");
      } else {
        if (submit) submit.disabled = false;
        let error = dialog.querySelector('[data-native-delete-error]');
        if (!error) { error = document.createElement("p"); error.dataset.nativeDeleteError = ""; error.setAttribute("role","alert"); dialog.append(error); }
        error.textContent = result.rejected ? "Нет права удалить запись." : result.unknown
          ? "Ответ приложения пока не получен. Проверьте раздел «Удаления»."
          : "Не удалось сохранить запрос удаления. Повторите попытку.";
      }
    }, true);
    let returnFocus = null;
    const close = () => {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
      restoreMeetingActionFocus(returnFocus);
      returnFocus = null;
    };
    opener.addEventListener("click", () => {
      returnFocus = opener;
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
      dialog.querySelector("[data-meeting-delete-dialog-title]")?.focus({ preventScroll: true });
    });
    dialog.querySelector("[data-meeting-delete-dialog-cancel]")?.addEventListener("click", close);
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      close();
    });
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) close();
    });
    dialog.addEventListener("keydown", (event) => trapModalFocus(dialog, event, { cycleAll: true }));
  };

  const initShareDialogs = () => {
    document.querySelectorAll("[data-share-dialog]").forEach((dialog) => {
      if (!(dialog instanceof HTMLDialogElement) || dialog.dataset.shareReady === "true") return;
      dialog.dataset.shareReady = "true";
      const opener = document.querySelector(`[aria-controls="${dialog.id}"]`);
      const status = dialog.querySelector("[data-share-status]");
      const form = dialog.querySelector("[data-share-recipient-form]");
      const results = dialog.querySelector("[data-share-recipient-results]");
      const confirmationHost = dialog.querySelector("[data-share-recipient-confirmation]");
      const viewers = dialog.querySelector("[data-share-viewers]");
      const recipientInput = form?.querySelector("[data-share-recipient-input]");
      const meetingId = form?.dataset.meetingId || "";
      const shareRequestUrl = (path) => {
        const url = new URL(path, window.location.origin);
        if (dialog.dataset.shareWorkspaceId) url.searchParams.set("workspace_id", dialog.dataset.shareWorkspaceId);
        return url;
      };
      const collaborationRole = dialog.querySelector("[data-share-comment-role]");
      const rolePermissions = (role) => ({ can_comment: role === "commenter" || role === "editor", can_edit: role === "editor" });
      const roleLabel = (grant) => grant?.can_edit ? "Редактирование" : grant?.can_comment ? "Комментирование" : "Просмотр";
      const externalInvitationsEnabled = dialog.dataset.shareExternalInvitations === "available";
      const setResultsVisible = (visible) => {
        if (results) results.hidden = !visible;
        recipientInput?.setAttribute("aria-expanded", visible ? "true" : "false");
        if (!visible) recipientInput?.removeAttribute("aria-activedescendant");
      };
      const setConfirmationVisible = (visible) => {
        if (confirmationHost) confirmationHost.hidden = !visible;
      };
      const focusResult = (option) => {
        if (!(option instanceof HTMLElement)) return;
        results?.querySelectorAll('[role="option"]').forEach((item) => {
          item.setAttribute("aria-selected", item === option ? "true" : "false");
        });
        recipientInput?.setAttribute("aria-activedescendant", option.id);
        recipientInput?.focus({ preventScroll: true });
      };
      const focusResultOption = (current, offset) => {
        const options = Array.from(results?.querySelectorAll('[role="option"]') || []);
        if (!options.length) return;
        const currentIndex = options.indexOf(current);
        const index = currentIndex === -1 ? (offset > 0 ? -1 : 0) : currentIndex;
        focusResult(options[(index + offset + options.length) % options.length]);
      };
      const setStatus = (message, tone = "neutral") => {
        if (!status) return;
        status.textContent = message;
        status.dataset.tone = tone;
      };
      const shareErrorMessage = (code) => ({
        comment_permission_forbidden: "Право менять роли больше недоступно. Обновите список доступа.",
        invalid_comment_permission: "Эта роль недоступна для выбранного состава встречи.",
        share_invitations_disabled: "Внешние приглашения пока отключены. Выберите участника рабочей области.",
        meeting_not_found: "Доступ к встрече изменился. Обновите страницу.",
        invalid_invitation: "Проверьте адрес электронной почты.",
        invalid_invitation_ttl: "Срок действия приглашения недоступен. Попробуйте ещё раз.",
        external_share_scope_invalid: "Внешний доступ возможен только к итогам без скачивания.",
        grantee_not_found: "Не удалось подтвердить участника. Попробуйте найти его заново.",
        grantee_already_has_access: "У этого участника уже есть доступ к встрече.",
        share_policy_blocked: "Этот способ доступа пока недоступен по политике.",
        share_not_found: "Ссылка больше недоступна. Обновите список доступов.",
        share_grant_not_found: "Доступ уже отозван или истёк.",
        auth_session_expired: "Сессия истекла. Обновите страницу и войдите снова.",
        csrf_token_missing: "Сессия страницы устарела. Обновите страницу.",
        csrf_token_invalid: "Сессия страницы устарела. Обновите страницу.",
        cabinet_store_unavailable: "Сервис доступа временно недоступен. Попробуйте позже.",
        postal_config_missing: "Почтовая доставка пока не настроена. Выберите участника рабочей области.",
        postal_delivery_disabled: "Почтовая доставка пока отключена. Выберите участника рабочей области.",
        postal_timeout: "Почтовый сервис не подтвердил доставку. Повторите позже.",
        postal_request_failed: "Не удалось связаться с почтовым сервисом. Повторите позже.",
        postal_malformed_response: "Почтовый сервис не подтвердил доставку. Повторите позже.",
        postal_delivery_outcome_unknown: "Доставка не подтверждена. Не отправляйте повторно сразу — проверьте позже.",
        share_team_audience_unavailable: "Командный доступ пока не настроен.",
        rate_limited: "Слишком много запросов. Попробуйте позже.",
        clipboard_unavailable: "Не удалось скопировать ссылку. Скопируйте её из адресной строки."
      }[code] || "Не удалось изменить доступ. Попробуйте ещё раз.");
      const recipientSourceLabel = (item) => {
        let source = item.source === "workspace_calendar"
          ? "Календарь и рабочая область"
          : item.source === "calendar"
            ? "Календарь"
            : "Рабочая область";
        if (item.freshness === "stale") source += " · данные могут устареть";
        if (item.freshness === "unknown") source += " · источник недоступен";
        return source;
      };
      const maskInvitationAddress = (address) => {
        const [local, domain] = String(address || "").trim().toLowerCase().split("@");
        if (!local || !domain) return "Приглашение";
        const maskedLocal = local.length <= 2 ? `${local[0]}*` : `${local[0]}***${local[local.length - 1]}`;
        return `${maskedLocal}@${domain}`;
      };
      const isLikelyEmail = (address) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address);
      const mutate = async (url, options) => {
        const response = await fetch(shareRequestUrl(url), {
          credentials: "same-origin",
          cache: "no-store",
          ...options,
          headers: {
            "Content-Type": "application/json",
            ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
            ...(options?.headers || {})
          }
        });
        if (await recoverMeetingDetailFromResponse(response, { actionProblemCodes: sharingActionProblemCodes })) {
          throw meetingDetailRecoveredError();
        }
        if (!response.ok) {
          const problem = await response.json().catch(() => ({}));
          throw new Error(problem.code || String(response.status));
        }
        return response.status === 204 ? null : response.json();
      };
      const copyShareUrl = async (shareUrl) => {
        if (!shareUrl) throw new Error("clipboard_unavailable");
        const absoluteUrl = new URL(shareUrl, window.location.origin).href;
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(absoluteUrl);
          return;
        }
        const fallback = document.createElement("textarea");
        fallback.value = absoluteUrl;
        fallback.readOnly = true;
        fallback.setAttribute("aria-hidden", "true");
        fallback.style.position = "fixed";
        fallback.style.opacity = "0";
        document.body.append(fallback);
        try {
          fallback.select();
          if (!document.execCommand("copy")) throw new Error("clipboard_unavailable");
        } finally {
          fallback.remove();
        }
      };
      const showEmptyViewers = () => {
        if (!viewers || viewers.querySelector("[data-share-viewer-row]")) return;
        const empty = document.createElement("p");
        empty.className = "muted";
        empty.dataset.shareEmpty = "true";
        empty.textContent = "Пока доступ есть только у владельца.";
        viewers.append(empty);
      };
      const bindViewerRow = (row, shareUrl = "") => {
        const role = row.querySelector("[data-share-existing-role]");
        let savedRole = role?.value;
        const copy = row.querySelector("[data-share-copy-button]");
        const rotateUrl = row.querySelector("[data-share-rotate-url]")?.dataset.shareRotateUrl || "";
        const revoke = row.querySelector("[data-share-revoke-url]");
        let rowBusy = false;
        const setRowBusy = (busy) => {
          rowBusy = busy;
          [copy, revoke, role].forEach((control) => {
            if (control) control.disabled = busy;
          });
        };
        role?.addEventListener("change", async () => {
          if (rowBusy) return;
          setRowBusy(true);
          try {
            const grant = await mutate(role.dataset.sharePermissionsUrl, { method: "PATCH", body: JSON.stringify(rolePermissions(role.value)) });
            savedRole = role.value;
            const label = row.querySelector("[data-share-role-label]");
            if (label) label.textContent = roleLabel(grant);
            const scope = row.querySelector("[data-share-scope-label]");
            if (scope) scope.textContent = grant.content_scope === "full_meeting" ? "Запись" : "Итоги";
            setStatus("Права получателя изменены.", "success");
          } catch (error) {
            role.value = savedRole;
            setStatus(shareErrorMessage(error?.code || error?.message), "error");
          } finally { setRowBusy(false); }
        });
        copy?.addEventListener("click", async () => {
          if (rowBusy) return;
          setRowBusy(true);
          try {
            let resolvedUrl = shareUrl;
            if (!resolvedUrl && rotateUrl) {
              const payload = await mutate(rotateUrl, { method: "POST" });
              resolvedUrl = payload?.share_url || "";
              shareUrl = resolvedUrl;
              setStatus("Создана новая ссылка — прежняя больше не работает.", "progress");
            }
            await copyShareUrl(resolvedUrl);
            setStatus("Ссылка скопирована.", "success");
          } catch (error) {
            setStatus(shareErrorMessage(error?.code || error?.message), "error");
          } finally {
            setRowBusy(false);
          }
        });
        revoke?.addEventListener("click", async () => {
          if (rowBusy) return;
          setRowBusy(true);
          try {
            await mutate(revoke.dataset.shareRevokeUrl, { method: "DELETE" });
            row.remove();
            showEmptyViewers();
            setStatus("Доступ отозван.", "success");
          } catch (error) {
            setStatus(shareErrorMessage(error?.code || error?.message), "error");
          } finally {
            setRowBusy(false);
          }
        });
      };
      const appendViewerRow = (label, payload) => {
        if (!viewers) return;
        viewers.querySelector("[data-share-empty]")?.remove();
        const row = document.createElement("div");
        row.className = "share-viewer-row";
        row.dataset.shareViewerRow = "true";
        const identity = document.createElement("span");
        const name = document.createElement("strong");
        name.textContent = label;
        const scope = document.createElement("small");
        scope.className = "muted";
        scope.dataset.shareScopeLabel = "true";
        scope.textContent = payload?.grant?.content_scope === "full_meeting" ? "Запись" : "Итоги";
        const roleText = document.createElement("small");
        roleText.dataset.shareRoleLabel = "true";
        roleText.textContent = roleLabel(payload?.grant);
        identity.append(name, scope, roleText);
        const actions = document.createElement("span");
        actions.className = "share-viewer-row__actions";
        if (dialog.dataset.shareCanManageRoles === "true" && payload?.grant?.grant_id) {
          const role = document.createElement("select");
          role.dataset.shareExistingRole = "true";
          role.dataset.sharePermissionsUrl = `/api/v1/cabinet/meetings/${meetingId}/shares/${payload.grant.grant_id}/permissions`;
          role.setAttribute("aria-label", `Права ${label}`);
          for (const [value, text] of [["viewer", "Просмотр"], ["commenter", "Комментирование"], ["editor", "Редактирование"]]) {
            const option = document.createElement("option"); option.value = value; option.textContent = text; role.append(option);
          }
          role.value = payload.grant.can_edit ? "editor" : payload.grant.can_comment ? "commenter" : "viewer";
          actions.append(role);
        }
        const copy = document.createElement("button");
        copy.type = "button";
        copy.dataset.shareCopyButton = "true";
        copy.textContent = "Скопировать ссылку";
        const revoke = document.createElement("button");
        revoke.type = "button";
        revoke.dataset.shareRevokeUrl = `/api/v1/cabinet/meetings/${meetingId}/shares/${payload?.grant?.grant_id || ""}`;
        revoke.textContent = "Отозвать";
        actions.append(copy, revoke);
        row.append(identity, actions);
        viewers.append(row);
        bindViewerRow(row, payload?.share_url || "");
        return row;
      };
      const bindInvitationRow = (row) => {
        const revoke = row.querySelector("[data-share-invitation-revoke-url]");
        revoke?.addEventListener("click", async () => {
          revoke.disabled = true;
          try {
            await mutate(revoke.dataset.shareInvitationRevokeUrl, { method: "DELETE" });
            row.remove();
            showEmptyViewers();
            setStatus("Приглашение отменено.", "success");
          } catch (error) {
            revoke.disabled = false;
            setStatus(shareErrorMessage(error?.code || error?.message), "error");
          }
        });
      };
      const appendInvitationRow = (payload, displayLabel = "Приглашение") => {
        const invitation = payload?.invitation || payload;
        if (!viewers || !invitation?.invitation_id) return;
        viewers.querySelector("[data-share-empty]")?.remove();
        const row = document.createElement("div");
        row.className = "share-viewer-row share-viewer-row--invitation";
        row.dataset.shareInvitationRow = "true";
        const identity = document.createElement("span");
        const label = document.createElement("strong");
        label.textContent = displayLabel || invitation.display_label || "Приглашение";
        const status = document.createElement("small");
        status.className = "muted";
        const expiresAt = invitation.expires_at ? new Date(invitation.expires_at) : null;
        const statusLabel = {
          pending: "Письмо готовится к отправке",
          sending: "Письмо отправляется",
          sent: "Письмо передано в отправку",
          outcome_unknown: "Письмо не подтверждено — не отправляйте повторно сразу"
        }[invitation.status] || invitation.status || "Готовится к отправке";
        const scopeLabel = invitation.content_scope === "full_meeting" ? "запись" : "итоги";
        status.textContent = `${statusLabel} · ${scopeLabel} · ${roleLabel(invitation)}${expiresAt && !Number.isNaN(expiresAt.valueOf()) ? ` · до ${window.GRAFTime.format(invitation.expires_at, { showZone: true })}` : ""}`;
        identity.append(label, status);
        const revoke = document.createElement("button");
        revoke.type = "button";
        revoke.dataset.shareInvitationRevokeUrl = `/api/v1/cabinet/meetings/${meetingId}/share-invitations/${invitation.invitation_id}`;
        revoke.textContent = "Отменить";
        row.append(identity, revoke);
        viewers.append(row);
        bindInvitationRow(row);
      };
      const grantRecipient = async (userId, label, button) => {
        if (button?.disabled) return;
        if (button) button.disabled = true;
        try {
          const payload = await mutate(`/api/v1/cabinet/meetings/${meetingId}/shares`, {
            method: "POST",
            body: JSON.stringify({
              audience_type: "user",
              audience_id: userId,
              content_scope: collaborationRole ? "full_meeting" : "summary_only",
              can_download: false,
              can_export: false,
              ...(collaborationRole ? rolePermissions(collaborationRole.value) : {})
            })
          });
          setResultsVisible(false);
          setConfirmationVisible(false);
          recipientInput?.focus({ preventScroll: true });
          appendViewerRow(label, payload);
          const notificationMessage = {
            sent: " Участнику также отправлено письмо.",
            failed: " Письмо не отправлено — скопируйте ссылку вручную.",
            outcome_unknown: " Статус письма не подтверждён — скопируйте ссылку вручную.",
            not_available: " Письмо не отправлено: у участника нет подтверждённого email."
          }[payload?.notification_status] || "";
          setStatus(`Доступ открыт: ${label}. ${roleLabel(payload?.grant)}. Ссылка готова для копирования.${notificationMessage}`, "success");
        } catch (error) {
          if (isMeetingDetailRecoveredError(error)) return;
          setStatus("Не удалось открыть доступ. Попробуйте ещё раз.", "error");
        }
      };
      const close = () => {
        dialog.close();
        opener?.setAttribute("aria-expanded", "false");
        if (opener instanceof HTMLElement) opener.focus({ preventScroll: true });
      };
      dialog.querySelector("[data-share-dialog-close]")?.addEventListener("click", close);
      dialog.addEventListener("cancel", (event) => {
        event.preventDefault();
        close();
      });
      dialog.addEventListener("click", (event) => {
        if (event.target === dialog) close();
      });
      dialog.addEventListener("keydown", (event) => trapModalFocus(dialog, event));
      let searchSequence = 0;
      let searchController = null;
      const sendExternalInvitation = async (address, button) => {
        if (button?.disabled) return;
        if (button) button.disabled = true;
        try {
          const invitation = await mutate(`/api/v1/cabinet/meetings/${meetingId}/share-invitations`, {
            method: "POST",
            body: JSON.stringify({
              address,
              content_scope: "full_meeting",
              can_download: true,
              can_export: true,
              ...(collaborationRole ? rolePermissions(collaborationRole.value) : {})
            })
          });
          setResultsVisible(false);
          setConfirmationVisible(false);
          recipientInput?.focus({ preventScroll: true });
          appendInvitationRow(invitation, maskInvitationAddress(address));
          setStatus("Приглашение к записи создано. Письмо поставлено в отправку — доставка может занять несколько минут; получатель откроет одноразовую ссылку из email.", "success");
        } catch (error) {
          setStatus(shareErrorMessage(error?.code || error?.message), "error");
          if (button?.isConnected) button.disabled = false;
        }
      };
      const renderExternalInvitationConfirmation = (address) => {
        if (!confirmationHost) return;
        setResultsVisible(false);
        confirmationHost.replaceChildren();
        const prompt = document.createElement("div");
        prompt.className = "share-recipient-confirmation";
        const title = document.createElement("strong");
        title.textContent = `Отправить приглашение на ${maskInvitationAddress(address)}?`;
        const note = document.createElement("small");
        note.className = "muted";
        note.textContent = "Получатель откроет одноразовую ссылку из письма. Если аккаунта GRAF ещё нет, он создастся автоматически — будут доступны саммари, расшифровка и скачивание аудио.";
        const actions = document.createElement("span");
        actions.className = "share-viewer-row__actions";
        const confirm = document.createElement("button");
        confirm.type = "button";
        confirm.id = `share-external-send-${meetingId}`;
        confirm.textContent = "Отправить приглашение";
        confirm.addEventListener("click", () => sendExternalInvitation(address, confirm));
        const cancel = document.createElement("button");
        cancel.type = "button";
        cancel.textContent = "Изменить адрес";
        cancel.addEventListener("click", () => {
          setConfirmationVisible(false);
          setResultsVisible(false);
          recipientInput?.focus({ preventScroll: true });
        });
        actions.append(confirm, cancel);
        prompt.append(title, note, actions);
        confirmationHost.append(prompt);
        setConfirmationVisible(true);
        setStatus("Проверьте адрес перед отправкой.");
        confirm.focus({ preventScroll: true });
      };
      form?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const query = recipientInput?.value.trim() || "";
        if (query.length === 1) {
          setStatus("Введите имя или email.", "error");
          return;
        }
        setConfirmationVisible(false);
        setResultsVisible(false);
        setStatus("Ищем…");
        const sequence = ++searchSequence;
        searchController?.abort();
        searchController = new AbortController();
        try {
          const searchUrl = shareRequestUrl(form.action);
          searchUrl.searchParams.set("query", query);
          const response = await fetch(searchUrl, {
            credentials: "same-origin",
            cache: "no-store",
            signal: searchController.signal
          });
          if (await recoverMeetingDetailFromResponse(response, { actionProblemCodes: sharingActionProblemCodes })) {
            throw meetingDetailRecoveredError();
          }
          if (!response.ok) throw new Error(String(response.status));
          const payload = await response.json();
          if (sequence !== searchSequence) return;
          const items = Array.isArray(payload.items) ? payload.items : [];
          if (items.length && results) {
            results.replaceChildren();
            items.forEach((item) => {
              const button = document.createElement("button");
              button.type = "button";
              button.tabIndex = -1;
              button.id = `share-recipient-option-${meetingId}-${item.user_id}`;
              button.setAttribute("role", "option");
              button.setAttribute("aria-selected", "false");
              const label = document.createElement("strong");
              label.textContent = item.display_label;
              const source = document.createElement("small");
              source.className = "muted";
              source.textContent = recipientSourceLabel(item);
              const action = document.createElement("span");
              action.className = "share-recipient-option__action";
              action.textContent = "Открыть доступ к итогам";
              button.append(label, source, action);
              button.setAttribute("aria-label", `${action.textContent}: ${item.display_label}, ${source.textContent}`);
              button.addEventListener("click", () => grantRecipient(item.user_id, item.display_label, button));
              results.append(button);
            });
            setResultsVisible(true);
            setStatus("Выберите человека.");
            focusResult(results.querySelector("button"));
            return;
          }
          if (query.includes("@")) {
            if (!externalInvitationsEnabled) {
              setStatus(shareErrorMessage("share_invitations_disabled"), "error");
              return;
            }
            if (!isLikelyEmail(query)) {
              setStatus("Проверьте адрес электронной почты.", "error");
              return;
            }
            renderExternalInvitationConfirmation(query);
            return;
          }
          setStatus(query ? "Никого не нашли. Проверьте имя." : "Выберите участника или начните вводить имя.", query ? "error" : "neutral");
        } catch (error) {
          if (isMeetingDetailRecoveredError(error)) return;
          setStatus("Не удалось пригласить. Попробуйте ещё раз.", "error");
        }
      });
      recipientInput?.addEventListener("input", () => {
        searchSequence += 1;
        searchController?.abort();
        searchController = null;
        setConfirmationVisible(false);
        setResultsVisible(false);
        setStatus(recipientInput.value.trim() ? "Нажмите «Найти»." : "");
      });
      recipientInput?.addEventListener("focus", () => {
        if (results && !recipientInput.value.trim() && !results.dataset.initialSuggestionsLoaded) {
          results.dataset.initialSuggestionsLoaded = "true";
          form?.requestSubmit();
        }
      }, { once: true });
      recipientInput?.addEventListener("keydown", (event) => {
        if (!results || results.hidden) return;
        const activeId = recipientInput.getAttribute("aria-activedescendant") || "";
        const active = activeId ? document.getElementById(activeId) : null;
        if (event.key === "ArrowDown") {
          event.preventDefault();
          focusResultOption(active, 1);
        } else if (event.key === "ArrowUp") {
          event.preventDefault();
          focusResultOption(active, -1);
        } else if (event.key === "Home") {
          event.preventDefault();
          focusResult(results.querySelector('[role="option"]'));
        } else if (event.key === "End") {
          event.preventDefault();
          const options = results.querySelectorAll('[role="option"]');
          focusResult(options[options.length - 1]);
        } else if (event.key === "Enter" && active) {
          event.preventDefault();
          active.click();
        } else if (event.key === "Escape" && !results?.hidden) {
          event.preventDefault();
          event.stopPropagation();
          setResultsVisible(false);
        }
      });
      results?.addEventListener("keydown", (event) => {
        const option = event.target.closest?.('[role="option"]');
        if (!option) return;
        if (["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) {
          event.preventDefault();
          if (event.key === "Home") focusResult(results.querySelector('[role="option"]'));
          else if (event.key === "End") {
            const options = results.querySelectorAll('[role="option"]');
            focusResult(options[options.length - 1]);
          }
          else focusResultOption(option, event.key === "ArrowDown" ? 1 : -1);
        } else if (event.key === "Escape") {
          event.preventDefault();
          event.stopPropagation();
          setResultsVisible(false);
          recipientInput?.focus({ preventScroll: true });
        }
      });
      dialog.querySelectorAll("[data-share-viewer-row]").forEach((row) => bindViewerRow(row));
      dialog.querySelectorAll("[data-share-invitation-row]").forEach((row) => bindInvitationRow(row));
      if (!dialog.open) dialog.showModal();
      recipientInput?.focus({ preventScroll: true });
    });
  };

  const copyBillingText = async (value) => {
    if (!value) throw new Error("clipboard_empty");
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(value);
        return;
      } catch {
        // Fall through to the native textarea fallback when permissions deny
        // clipboard access (common in embedded or non-secure contexts).
      }
    }
    const fallback = document.createElement("textarea");
    fallback.value = value;
    fallback.setAttribute("readonly", "true");
    fallback.style.position = "fixed";
    fallback.style.opacity = "0";
    document.body.append(fallback);
    fallback.select();
    try {
      if (!document.execCommand("copy")) throw new Error("clipboard_unavailable");
    } finally {
      fallback.remove();
    }
  };

  const initBillingCopyControls = () => {
    document.querySelectorAll("[data-copy-value], [data-copy-target]").forEach((button) => {
      if (button.dataset.copyReady === "true") return;
      button.dataset.copyReady = "true";
      button.addEventListener("click", async () => {
        const targetId = button.dataset.copyTarget;
        const target = targetId ? document.getElementById(targetId) : null;
        const value = targetId ? target?.value || target?.textContent?.trim() : button.dataset.copyValue;
        let status = button.parentElement?.querySelector("[data-copy-status]");
        if (!status) {
          status = document.createElement("span");
          status.dataset.copyStatus = "true";
          status.setAttribute("role", "status");
          status.setAttribute("aria-live", "polite");
          button.parentElement?.append(status);
        }
        try {
          await copyBillingText(value);
          status.textContent = "Скопировано.";
        } catch {
          status.textContent = "Не удалось скопировать. Выделите текст вручную.";
        }
      });
    });
  };

  let meetingTitleEditor = null;
  let meetingTitleHeaderObserver = null;
  const titleEditorActive = () => meetingTitleEditor?.active() || false;

  const initMeetingTitleEditor = () => {
    const form = document.querySelector("[data-meeting-title-form]");
    if (form?.dataset.ready === "true") return;
    meetingTitleHeaderObserver?.disconnect();
    if (!form) return;
    form.dataset.ready = "true";
    const detail = form.closest("[data-meeting-id]");
    const header = form.closest("[data-meeting-detail-header]");
    const headerObserver = new ResizeObserver(() => {
      if (!form.isConnected) { headerObserver.disconnect(); return; }
      header.classList.toggle("meeting-title-header-scrolls", header.offsetHeight > detail.clientHeight / 2);
    });
    headerObserver.observe(header);
    headerObserver.observe(detail);
    meetingTitleHeaderObserver = headerObserver;
    const input = form.querySelector("[data-meeting-title-input]");
    const display = form.querySelector("[data-meeting-title-open]");
    const version = form.elements.expected_version;
    const error = form.querySelector("#meeting-title-error");
    const status = form.querySelector("[data-meeting-title-status]");
    let confirmed = form.dataset.confirmedTitle;
    let editing = !error.hidden;
    let pending = null;
    let uncertain = false;
    let terminal = false;
    let needsExplicitRetry = editing;
    const current = () => form.isConnected && detail === document.querySelector("#cabinet-main");
    const dirty = () => input.value.trim() !== confirmed;
    const showError = (message) => {
      error.textContent = message;
      error.hidden = !message;
      input.setAttribute("aria-invalid", String(Boolean(message)));
    };
    const showEditor = (open, focus = false) => {
      editing = open;
      input.hidden = !open;
      display.hidden = open;
      if (focus) (open ? input : display).focus({ preventScroll: true });
      if (open && focus) input.select();
    };
    const accept = (title, token) => {
      confirmed = title;
      form.dataset.confirmedTitle = title;
      version.value = token;
      input.value = title;
      display.textContent = title;
      display.setAttribute("aria-label", `Переименовать встречу: ${title}`);
      document.title = `${title} - GRAF`;
      uncertain = false;
      needsExplicitRetry = false;
      showError("");
      clearMeetingHistoryCache();
    };
    const recover = async (response, code = "") => {
      if (!current()) return true;
      if (code === "meeting_deletion_active") {
        terminal = true;
        renderMeetingDetailRecovery(detail, "unavailable");
        return true;
      }
      if (await recoverMeetingDetailFromResponse(response)) {
        terminal = true;
        return true;
      }
      if ([401, 403, 404, 410].includes(response.status)) {
        terminal = true;
        input.readOnly = true;
        showError("Сессия страницы устарела. Обновите страницу.");
        return true;
      }
      return false;
    };
    const finish = () => {
      if (!current()) return;
      input.readOnly = terminal;
      form.removeAttribute("aria-busy");
      pending = null;
    };
    const save = (explicit = false) => {
      if (terminal || !current()) return Promise.resolve(true);
      if (pending) return pending;
      if (needsExplicitRetry && !explicit) return Promise.resolve(false);
      if (!dirty() && !uncertain) {
        showError("");
        showEditor(false, document.activeElement === input);
        return Promise.resolve(true);
      }
      if (!input.value.trim() || Array.from(input.value.trim()).length > 500) {
        showError(!input.value.trim() ? "Введите название встречи" : "Название должно содержать не больше 500 символов");
        needsExplicitRetry = true;
        return Promise.resolve(false);
      }
      input.readOnly = true;
      form.setAttribute("aria-busy", "true");
      const controller = new AbortController();
      const timer = window.setTimeout(() => controller.abort(), 15000);
      pending = (async () => {
        try {
          const response = await fetch(form.action, {
            method: "POST", body: new FormData(form), credentials: "same-origin",
            headers: { Accept: "application/json", "X-CSRF-Token": csrfToken }, signal: controller.signal,
          });
          if (!current()) return false;
          const data = await response.clone().json().catch(() => ({}));
          if (await recover(response, data.code)) return terminal;
          if (!current()) return false;
          if (!response.ok) {
            needsExplicitRetry = true;
            if (data.code === "meeting_title_conflict" && typeof data.title_version === "string") {
              confirmed = data.title;
              version.value = data.title_version;
              uncertain = false;
              showError(`${data.message}. Текущее название: ${data.title}`);
            } else {
              uncertain = response.status >= 500;
              showError(data.message || "Не удалось подтвердить сохранение. Нажмите Enter, чтобы повторить, или Esc, чтобы проверить название.");
            }
            return false;
          }
          if (data.meeting_id !== detail.dataset.meetingId || typeof data.title !== "string" || !data.title_version) throw new Error("Unexpected title response");
          const focus = document.activeElement === input;
          accept(data.title, data.title_version);
          showEditor(false, focus);
          status.textContent = "Название сохранено";
          return true;
        } catch {
          if (current()) {
            uncertain = true;
            needsExplicitRetry = true;
            showError("Не удалось подтвердить сохранение. Нажмите Enter, чтобы повторить, или Esc, чтобы проверить название.");
          }
          return false;
        } finally {
          window.clearTimeout(timer);
          finish();
        }
      })();
      return pending;
    };
    const cancel = async () => {
      if (pending || terminal) return;
      if (!uncertain) {
        accept(confirmed, version.value);
        showEditor(false, true);
        return;
      }
      // After an ambiguous response only the server can confirm the current name.
      input.readOnly = true;
      form.setAttribute("aria-busy", "true");
      const controller = new AbortController();
      const timer = window.setTimeout(() => controller.abort(), 15000);
      pending = (async () => {
        try {
          const response = await fetch(form.action.replace(/\/title$/, ""), {
            credentials: "same-origin", cache: "no-store", signal: controller.signal,
            headers: { "HX-Request": "true" },
          });
          if (await recover(response)) return;
          if (!response.ok) throw new Error("Title refresh failed");
          const page = new DOMParser().parseFromString(await response.text(), "text/html");
          const fresh = page.querySelector("[data-meeting-title-form]");
          if (!fresh || fresh.closest("[data-meeting-id]")?.dataset.meetingId !== detail.dataset.meetingId) throw new Error("Missing title");
          if (!current()) return;
          accept(fresh.dataset.confirmedTitle, fresh.elements.expected_version.value);
          showEditor(false, true);
        } catch {
          if (current()) showError("Не удалось проверить название. Проверьте соединение и нажмите Esc ещё раз.");
        } finally {
          window.clearTimeout(timer);
          finish();
        }
      })();
      await pending;
    };
    display.addEventListener("click", () => showEditor(true, true));
    form.addEventListener("submit", (event) => { event.preventDefault(); void save(true); });
    input.addEventListener("keydown", (event) => {
      if (event.isComposing || event.keyCode === 229) return;
      if (event.key === "Escape") { event.preventDefault(); void cancel(); }
      if (event.key === "Enter") { event.preventDefault(); void save(true); }
    });
    input.addEventListener("blur", () => { if (editing) void save(); });
    input.addEventListener("paste", (event) => {
      if (/[\x00-\x1f\x7f-\x9f\u2028\u2029]/.test(event.clipboardData?.getData("text") || "")) {
        event.preventDefault();
        showError("Название должно быть одной строкой");
      }
    });
    showEditor(editing);
    meetingTitleEditor = {
      refreshDetail: (nextDetail) => {
        const nextForm = nextDetail.querySelector("[data-meeting-title-form]");
        if (!current() || !nextForm || nextDetail.dataset.meetingId !== detail.dataset.meetingId
          || nextForm.getAttribute("action") !== form.getAttribute("action")) return false;
        const ancestors = [];
        let node = form, nextNode = nextForm;
        while (node !== detail && nextNode !== nextDetail) {
          if (node.parentElement.tagName !== nextNode.parentElement.tagName) return false;
          ancestors.push([node, nextNode]);
          node = node.parentElement; nextNode = nextNode.parentElement;
        }
        if (node !== detail || nextNode !== nextDetail) return false;
        // Keep the editor and its captured main/header connected: detaching would blur/save.
        for (const [kept, incoming] of ancestors) {
          const parent = kept.parentElement, nextParent = incoming.parentElement;
          while (kept.previousSibling) kept.previousSibling.remove();
          while (kept.nextSibling) kept.nextSibling.remove();
          const siblings = Array.from(nextParent.childNodes), index = siblings.indexOf(incoming);
          kept.before(...siblings.slice(0, index));
          kept.after(...siblings.slice(index + 1));
          for (const attribute of Array.from(parent.attributes)) parent.removeAttribute(attribute.name);
          for (const attribute of nextParent.attributes) parent.setAttribute(attribute.name, attribute.value);
        }
        return true;
      },
      active: () => current() && !terminal && (editing || Boolean(pending)),
      blocksNavigation: () => current() && !terminal && (dirty() || uncertain || Boolean(pending)),
      save,
      focus: () => input.focus({ preventScroll: true }),
    };
  };

  document.addEventListener("click", (event) => {
    const editor = meetingTitleEditor;
    const link = event.target.closest?.("a[href]");
    if (!editor?.blocksNavigation() || !link || event.defaultPrevented || event.button !== 0
      || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey
      || link.hasAttribute("download") || (link.target && link.target !== "_self")) return;
    const url = new URL(link.href, location.href);
    if (url.origin !== location.origin || (url.pathname === location.pathname && url.search === location.search && url.hash)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    void editor.save().then((saved) => {
      if (saved) location.assign(url.href);
      else editor.focus();
    });
  }, true);
  document.addEventListener("htmx:confirm", (event) => {
    const editor = meetingTitleEditor;
    const target = event.detail?.target;
    const form = document.querySelector("[data-meeting-title-form]");
    if (!editor?.blocksNavigation() || !form || !target?.contains?.(form)) return;
    event.preventDefault();
    void editor.save().then((saved) => {
      if (saved) event.detail.issueRequest(true);
      else editor.focus();
    });
  });
  document.addEventListener("htmx:beforeRequest", (event) => {
    const form = document.querySelector("[data-meeting-title-form]");
    if (form && event.detail?.target?.contains?.(form)) {
      event.detail.xhr.grafTitleVersion = form.elements.expected_version.value;
    }
  });
  document.addEventListener("htmx:beforeSwap", (event) => {
    const form = document.querySelector("[data-meeting-title-form]");
    if (!form || !event.detail?.target?.contains?.(form)) return;
    const requestedVersion = event.detail.xhr?.grafTitleVersion;
    if (titleEditorActive() || (requestedVersion && requestedVersion !== form.elements.expected_version.value)) {
      event.detail.shouldSwap = false;
    }
  });
  window.addEventListener("beforeunload", (event) => {
    if (!meetingTitleEditor?.blocksNavigation()) return;
    event.preventDefault();
    event.returnValue = "";
  });

  const initCabinet = () => {
    initMeetingTitleEditor();
    initAuthTransition();
    initCabinetRail();
    initCabinetProfileMenus();
    initCabinetTooltips();
    initListDisclosures();
    initCodeForms();
    initOutcomeFocus();
    initMeetingList();
    announceUploadProgress();
    initManualUpload();
    initDetailTabs();
    initProcessingRecovery();
    initProcessingListProjection();
    initRecordingLifecyclePolling();
    initSummaryFormats();
    initSummaryTemplateSettings();
    initMeetingContextPanels();
    initProcessingReprocess();
    initShareDialogs();
    initSourceNavigation();
    initPlayback();
    initSpeakerTimelineResize();
    initMeetingDetailAuthorizationRecovery();
    initPlaybackRecoveryPolling();
    initSpeakerNameForms();
    initContentExport();
    initMeetingDeleteDialog();
    initCalendarSettings();
    initCalendarUpcomingRefresh();
    initSettingsFormState();
    initRecordingSettings();
    initLocalNotificationSettings();
    initAccountPreferences();
    initSettingsConfirmations();
    initShareInvitationAutoAccept();
    initBillingCopyControls();
  };

  const initShareInvitationAutoAccept = () => {
    const form = document.querySelector("form[data-share-invitation-auto-accept-form]");
    if (!form || form.dataset.submitted === "true") return;
    form.dataset.submitted = "true";
    form.hidden = true;
    if (typeof form.requestSubmit === "function") form.requestSubmit();
    else form.submit();
  };

  // Keep meeting-list fencing listeners ahead of feature-specific HTMX listeners.
  // Several request paths share the same event names; the list handler must see
  // every request first so stale swaps and detached authorization responses are
  // fenced before secondary UI handlers inspect them.
  initCabinet();

  const shareRequestSource = (event) => {
    const source = event.detail?.elt || event.target;
    if (source instanceof Element && source.matches("[data-share-dialog-open]")) return source;
    return document.querySelector("[data-share-dialog-open][data-share-request-pending='true']");
  };
  const shareRequestErrorMessage = (status) => {
    if (status === 401 || status === 403) return "Сессия страницы устарела. Обновите страницу и войдите снова.";
    if (status === 404) return "Встреча или доступ к ней больше недоступны.";
    if (status === 429) return "Слишком много запросов. Попробуйте открыть окно позже.";
    return "Не удалось открыть окно «Поделиться». Проверьте соединение и попробуйте ещё раз.";
  };
  const resetShareRequestSource = (source) => {
    source.removeAttribute("aria-busy");
    source.disabled = false;
    delete source.dataset.shareRequestPending;
  };
  const showShareRequestError = (source, status = 0) => {
    if (source.dataset.shareRequestPending !== "true") return;
    resetShareRequestSource(source);
    const host = document.querySelector("#meeting-share-host");
    if (!host) return;
    host.replaceChildren();
    const shell = document.createElement("div");
    shell.className = "share-load-error";
    shell.setAttribute("role", "alert");
    const message = document.createElement("p");
    message.textContent = shareRequestErrorMessage(status);
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "Повторить";
    retry.addEventListener("click", () => source.click());
    shell.append(message, retry);
    host.append(shell);
  };
  document.body.addEventListener("htmx:beforeRequest", (event) => {
    const source = shareRequestSource(event);
    if (!source) return;
    source.setAttribute("aria-busy", "true");
    source.disabled = true;
    source.dataset.shareRequestPending = "true";
  });
  document.body.addEventListener("htmx:afterRequest", (event) => {
    const source = shareRequestSource(event);
    if (!source || event.detail?.successful) return;
    showShareRequestError(source, event.detail?.xhr?.status || 0);
  });
  ["htmx:sendError", "htmx:timeout", "htmx:swapError"].forEach((eventName) => {
    document.body.addEventListener(eventName, (event) => {
      const source = shareRequestSource(event);
      if (source) showShareRequestError(source);
    });
  });

  document.body.addEventListener("htmx:afterSwap", (event) => {
    const target = event.detail?.target;
    const source = shareRequestSource(event);
    if (source && target instanceof Element && target.id === "meeting-share-host") {
      resetShareRequestSource(source);
      source.setAttribute("aria-expanded", "true");
    }
    if (target instanceof Element && (target.id === "meeting-list-region" || target.matches("[data-meeting-list]"))) {
      renderLocalRecordingRows();
      // A refresh may replace aliases or change filters, but cannot enlarge or
      // discard the set the user is confirming. Detached rows retain that intent.
      pendingDeleteRows = pendingDeleteRows.map(row =>
        allRows().find(current => recordingRowIdentity(current) === recordingRowIdentity(row)) || row
      );
      reconcileMeetingSelection();
      announceMeetingResultCount();
      restoreMeetingListRequestFocus(event);
      restoreListRefreshFocus();
    }
    initCabinet();
  });

  window.addEventListener("pageshow", (event) => {
    updateSelection();
    if (event.persisted) refreshMeetingList();
  });

  document.body.addEventListener("htmx:configRequest", (event) => {
    const detail = event.detail || {};
    detail.headers = detail.headers || {};
    if (document.body?.dataset?.surfaceMode === "desktop_embedded") detail.headers["X-GRAF-Client"] = "desktop";
    const verb = String(detail.verb || "get").toUpperCase();
    if (!csrfToken || !["POST", "PUT", "PATCH", "DELETE"].includes(verb)) return;
    detail.headers["X-CSRF-Token"] = csrfToken;
  });
})();

// Server events only. No browser push, sound, toasts or native event forwarding.
(() => {
  const root = document.querySelector('[data-notification-inbox]');
  if (!root) return;
  const bell = root.querySelector('[data-notification-bell]');
  const panel = root.querySelector('[data-notification-panel]');
  const heading = panel.querySelector('h2');
  const dot = root.querySelector('[data-notification-dot]');
  const list = panel.querySelector('[data-notification-items]');
  const status = panel.querySelector('[data-notification-status]');
  const more = panel.querySelector('[data-notification-more]');
  // Keep the inbox outside the scrolling sidebar and the replaceable meeting content.
  document.body.append(panel);
  const sidebarFoot = root.parentElement;
  const mobileNav = root.closest('[data-cabinet-shell]')?.querySelector('.cabinet-mobile-nav');
  const mobileMedia = window.matchMedia('(max-width: 980px)');
  const syncLocation = () => {
    const target = mobileNav && mobileMedia.matches ? mobileNav : sidebarFoot;
    const profile = target.querySelector('[data-profile-menu-root]');
    target.insertBefore(root, profile);
  };
  syncLocation();
  mobileMedia.addEventListener('change', syncLocation);
  const positionPanel = () => {
    const rect = bell.getBoundingClientRect();
    const scale = panel.offsetWidth ? panel.getBoundingClientRect().width / panel.offsetWidth : 1;
    panel.style.width = Math.min(400, (window.innerWidth - 24) / scale) + 'px';
    const width = panel.getBoundingClientRect().width;
    const bottom = Math.max(12, Math.min(window.innerHeight - rect.bottom, window.innerHeight - Math.min(480 * scale, window.innerHeight - 24) - 12));
    panel.style.left = Math.max(12, Math.min(rect.right + 12, window.innerWidth - width - 12)) / scale + 'px';
    panel.style.bottom = bottom / scale + 'px';
    panel.style.maxHeight = (window.innerHeight - bottom - 12) / scale + 'px';
  };
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const embedded = bell.pathname.startsWith('/desktop/');
  const openedNoticeKey = 'graf-notification-open';
  const consumeOpenedNotice = async () => {
    let pending;
    try {
      const stored = sessionStorage.getItem(openedNoticeKey);
      sessionStorage.removeItem(openedNoticeKey);
      pending = JSON.parse(stored || 'null');
    } catch (_) { return; }
    if (!pending || !/^[0-9a-f-]{36}$/.test(pending.id) || !Number.isSafeInteger(pending.revision)
        || pending.revision < 1 || typeof pending.csrf !== 'string' || !pending.csrf
        || !Number.isFinite(pending.createdAt) || Date.now() - pending.createdAt < 0
        || Date.now() - pending.createdAt > 30000
        || pending.target !== location.pathname + location.search) return;
    const route = location.pathname.match(/^\/(?:desktop\/)?(?:meetings|shared-meetings)\/([0-9a-f-]{36})$/);
    const detail = document.querySelector('main#cabinet-main[data-meeting-id]');
    const shared = location.pathname.startsWith('/shared-meetings/')
      && document.querySelector('main#cabinet-main .shared-summary');
    if (!route || !(detail?.dataset.meetingId === route[1] || shared)) return;
    try {
      // The source page's token binds this intent to its authenticated session.
      // The existing endpoint rechecks recipient, workspace and current object access.
      const response = await fetch('/api/v1/notifications/' + pending.id + '/read', {
        method:'POST', credentials:'same-origin', headers:{Accept:'application/json','X-CSRF-Token':pending.csrf},
        body:new URLSearchParams({revision:String(pending.revision)})
      });
      if (response.ok && !response.redirected && root.isConnected) await load(false, true);
    } catch (_) { /* An unconfirmed read remains available through “Просмотрено”. */ }
  };
  let filter = 'important', next = null, epoch = 0, scopeEpoch = 0, controller = null, pageCount = 1;
  const setDot = value => {
    dot.hidden = !value;
    bell.setAttribute('aria-label', value ? 'Уведомления: есть новое важное' : 'Уведомления');
  };
  const clear = () => {
    epoch++; scopeEpoch++; controller?.abort(); list.replaceChildren(); setDot(false);
    next = null; more.hidden = true; pageCount = 1; status.textContent = '';
  };
  const close = (restore = false) => { panel.hidden = true; bell.setAttribute('aria-expanded', 'false'); if (restore) bell.focus(); };
  const text = (tag, value) => { const node = document.createElement(tag); node.textContent = value; return node; };
  bell.setAttribute('aria-controls', panel.id); bell.setAttribute('aria-expanded', 'false');
  const cardFor = item => {
    const url = new URL(item.href, location.origin);
    if (url.origin !== location.origin || !/^\/(meetings|shared-meetings)\/[0-9a-f-]+$/.test(url.pathname)) return null;
    const card = text('article', ''); card.className = 'notification-card';
    card.dataset.id = item.id; card.dataset.content = JSON.stringify(item);
    card.append(text('h3', item.title), text('p', item.meeting_title), text('p', item.body));
    const date = new Date(item.updated_at);
    if (Number.isFinite(date.getTime())) {
      const time = text('time', date.toLocaleString('ru-RU', {day:'numeric',month:'long',hour:'2-digit',minute:'2-digit'}));
      time.dateTime = item.updated_at; card.append(time);
    }
    if (item.personal) card.append(text('p', 'Лично вам'));
    if (item.resolved) card.append(text('p', 'Проблема решена'));
    const link = text('a', 'Открыть встречу'); link.href = (embedded && url.pathname.startsWith('/meetings/') ? '/desktop' : '') + url.pathname + url.search; card.append(link);
    link.onclick = event => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      try {
        sessionStorage.removeItem(openedNoticeKey);
        if (item.unseen && csrf && card.isConnected) sessionStorage.setItem(openedNoticeKey, JSON.stringify({
          id:item.id, revision:item.revision, target:link.pathname + link.search, createdAt:Date.now(), csrf
        }));
      } catch (_) { /* Navigation remains available when storage is disabled. */ }
    };
    if (item.requires_action && item.unseen) {
      const read = text('button', 'Просмотрено'); read.type = 'button';
      read.onclick = async () => {
        const scope = scopeEpoch; read.disabled = true;
        try {
          const response = await fetch('/api/v1/notifications/' + item.id + '/read', {
            method:'POST', credentials:'same-origin', headers:{Accept:'application/json','X-CSRF-Token':csrf},
            body:new URLSearchParams({revision:String(item.revision)})
          });
          if (scope !== scopeEpoch || !card.isConnected) return;
          if (response.redirected || [401,403,404,410].includes(response.status)) {
            clear();
            status.textContent = 'Доступ изменился. Откройте уведомления заново.';
            heading.focus({preventScroll:true});
            return;
          }
          if (!response.ok) throw new Error('read_failed');
          link.focus({preventScroll:true}); await load();
        } catch (_) {
          if (scope === scopeEpoch && card.isConnected) { status.textContent = 'Не удалось сохранить просмотр. Повторите попытку.'; read.disabled = false; }
        }
      }; card.append(read);
    } else if (item.requires_action) card.append(text('p', 'Просмотрено · Требует действия'));
    return card;
  };
  // Revalidate every loaded page and reuse unchanged nodes, preserving keyboard focus.
  const render = items => {
    const existing = new Map(Array.from(list.children).map(node => [node.dataset.id, node]));
    const keep = new Set();
    let index = 0;
    for (const item of items) {
      const old = existing.get(item.id);
      const node = old?.dataset.content === JSON.stringify(item) ? old : cardFor(item);
      if (!node || keep.has(item.id)) continue;
      keep.add(item.id);
      const hadFocus = old?.contains(document.activeElement);
      const position = list.children[index] || null;
      if (node !== position) list.insertBefore(node, position);
      index++;
      if (old && old !== node) { old.remove(); if (hadFocus) node.querySelector('a').focus({preventScroll:true}); }
    }
    Array.from(list.children).forEach(node => {
      if (!keep.has(node.dataset.id)) { const focused = node.contains(document.activeElement); node.remove(); if (focused) heading.focus({preventScroll:true}); }
    });
    if (!keep.size) list.append(text('p', filter === 'important'
      ? 'Сейчас ничего не требует вашего действия. Готовые результаты — в списке встреч и истории.'
      : 'Здесь появятся готовые результаты и встречи, которыми с вами поделились.'));
  };
  const load = async (append = false, background = false) => {
    const generation = ++epoch;
    controller?.abort(); controller = new AbortController();
    const wanted = pageCount + (append ? 1 : 0);
    if (!background && !panel.hidden) status.textContent = 'Проверяем…';
    try {
      const items = []; let cursor = null, data, fetched = 0;
      do {
        const params = new URLSearchParams({filter: panel.hidden ? 'important' : filter, limit: panel.hidden ? '1' : '30'});
        if (cursor) params.set('cursor', cursor);
        const response = await fetch('/api/v1/notifications?' + params, {credentials:'same-origin',cache:'no-store',signal:controller.signal,headers:{Accept:'application/json'}});
        if (!response.ok || response.redirected) throw new Error('unavailable');
        data = await response.json();
        if (generation !== epoch) return;
        items.push(...data.items); cursor = data.next_cursor; fetched++;
      } while (!panel.hidden && cursor && fetched < wanted);
      setDot(data.has_unseen_action_required); status.textContent = '';
      if (!panel.hidden) { render(items); next = cursor; pageCount = fetched; more.hidden = !next; }
    } catch (error) {
      if (generation !== epoch || error.name === 'AbortError') return;
      // Unverified private content never remains visible after an access/network failure.
      clear();
      if (!panel.hidden) {
        status.textContent = 'Не удалось проверить уведомления.';
        const retry = text('button', 'Повторить'); retry.type = 'button'; retry.onclick = () => load(); list.append(retry);
        if (!panel.contains(document.activeElement)) heading.focus({preventScroll:true});
      }
    }
  };
  bell.onclick = event => {
    event.preventDefault(); if (!panel.hidden) { close(true); return; }
    clear(); filter = 'important';
    panel.querySelectorAll('[data-notification-filter]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.notificationFilter === filter)));
    panel.hidden = false; bell.setAttribute('aria-expanded','true'); positionPanel(); heading.focus({preventScroll:true}); load();
  };
  panel.querySelector('[data-notification-close]').onclick = () => close(true);
  panel.querySelectorAll('[data-notification-filter]').forEach(button => button.onclick = () => {
    if (filter === button.dataset.notificationFilter) return;
    clear(); filter = button.dataset.notificationFilter;
    panel.querySelectorAll('[data-notification-filter]').forEach(b => b.setAttribute('aria-pressed', String(b === button))); load();
  });
  more.onclick = () => load(true);
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && !panel.hidden) { close(true); event.stopPropagation(); } });
  document.addEventListener('click', event => { if (!root.contains(event.target) && !panel.contains(event.target)) close(); });
  window.addEventListener('resize', () => { if (!panel.hidden) close(panel.contains(document.activeElement)); });
  document.addEventListener('scroll', event => { if (!panel.hidden && !panel.contains(event.target)) positionPanel(); }, true);
  document.addEventListener('visibilitychange', () => { clear(); if (!document.hidden) load(); });
  window.addEventListener('pageshow', () => { clear(); load(); consumeOpenedNotice(); });
  window.addEventListener('pagehide', clear);
  document.addEventListener('htmx:afterRequest', event => {
    const code = event.detail?.xhr?.status;
    if ([401,403,404,410].includes(code)) { clear(); if (!document.hidden) load(); }
  });
  document.addEventListener('htmx:afterSwap', () => { if (root.isConnected && !document.hidden) load(false, true); });
  document.addEventListener('htmx:afterSettle', consumeOpenedNotice);
  window.setInterval(() => { if (root.isConnected && !document.hidden) load(false, true); }, 30000);
  load();
  consumeOpenedNotice();
})();

(() => {
  const form=document.querySelector('[data-notification-settings]'); if(!form)return;
  const save=form.querySelector('[type=submit]'), reset=form.querySelector('[type=reset]'), status=form.querySelector('[data-settings-form-status]');
  const reload=form.querySelector('[data-notification-settings-reload]');
  const snapshot=()=>new URLSearchParams(new FormData(form)).toString(); let initial=snapshot(), saving=false;
  const changed=()=>{const dirty=snapshot()!==initial;save.disabled=saving||!dirty;reset.disabled=saving||!dirty;save.hidden=reset.hidden=!dirty||saving;if(reload)reload.hidden=!dirty||saving;form.dataset.state=dirty?'dirty':'pristine';};
  form.addEventListener('change',()=>{changed(); if(!saving && snapshot()!==initial)form.requestSubmit();}); form.addEventListener('reset',()=>setTimeout(()=>{status.hidden=true;changed();},0));
  window.addEventListener('beforeunload',event=>{if(!saving&&snapshot()!==initial){event.preventDefault();event.returnValue='';}});
  form.addEventListener('submit',async event=>{
    event.preventDefault(); if(saving)return; const submitted=new FormData(form); saving=true; changed(); form.querySelectorAll('input[type=checkbox]').forEach(input=>input.disabled=true); status.hidden=false;status.textContent='Сохраняем…';
    try {
      const response=await fetch(form.action,{method:'POST',credentials:'same-origin',body:new URLSearchParams(submitted),headers:{Accept:'text/html'}});
      if(!response.ok){
        if(response.status===409){
          const latest=await fetch(form.action,{credentials:'same-origin',cache:'no-store'});
          const documentCopy=new DOMParser().parseFromString(await latest.text(),'text/html');
          const current=documentCopy.querySelector('[data-notification-settings]');
          if(!latest.ok||!current)throw new Error('unavailable');
          const enabled=name=>current.querySelector(`input[type=checkbox][name="${name}"]`)?.checked ? 'включены':'выключены';
          status.textContent=`Настройки изменены на другом устройстве. Сохранено: письма ${enabled('optional_email_enabled')}, подсказки ${enabled('optional_in_app_enabled')}. Ваш выбор остался в форме. `;
          const useMine=document.createElement('button');useMine.type='button';useMine.textContent='Сохранить мой выбор';
          useMine.onclick=()=>{form.elements.namedItem('version').value=current.elements.namedItem('version').value;form.requestSubmit();};status.append(useMine);
          return;
        }
        throw new Error('save_failed');
      }
      const page=new DOMParser().parseFromString(await response.text(),'text/html');
      const saved=page.querySelector('[data-notification-settings]');if(!saved)throw new Error('unavailable');
      form.elements.namedItem('version').value=saved.elements.namedItem('version').value;
      form.elements.namedItem('version').defaultValue=form.elements.namedItem('version').value;
      submitted.set('version',form.elements.namedItem('version').value);
      form.querySelectorAll('input[type=checkbox]').forEach(input=>{input.defaultChecked=input.checked;});
      initial=new URLSearchParams(submitted).toString();status.textContent='Настройки сохранены';
    }catch(_){status.textContent='Не удалось сохранить. Ваш выбор остался в форме. Попробуйте ещё раз.';}
    finally{saving=false;form.querySelectorAll('input[type=checkbox]').forEach(input=>input.disabled=false);changed();}
  }); changed();
})();
