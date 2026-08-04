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
  const rowPrimaryFocusTarget = (row) => row?.querySelector("[data-meeting-open]") || null;
  const selectableRows = () => allRows().filter((row) => row.querySelector("[data-meeting-select]"));
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
      .map((meetingId) => allRows().find((row) => row.dataset.meetingId === meetingId))
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

  const trapModalFocus = (dialog, event) => {
    if (event.key !== "Tab" || !dialog.open) return;
    const elements = modalFocusTargets(dialog);
    if (!elements.length) return;
    const current = elements.indexOf(document.activeElement);
    const next = event.shiftKey
      ? (current <= 0 ? elements.length - 1 : current - 1)
      : (current < 0 || current === elements.length - 1 ? 0 : current + 1);
    if (
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
    rows.forEach((row) => selectedMeetingIds.add(row.dataset.meetingId));
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
      if (checkbox) checkbox.checked = selectedMeetingIds.has(row.dataset.meetingId);
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
    if (authorizationLost) meetingListRequestGeneration += 1;
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
      && location.pathname.startsWith("/desktop/")
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
    const deletingIds = new Set(rows.map((row) => row.dataset.meetingId));
    const anchorRow = orderedRows.find((row) => row.dataset.meetingId === deleteReturnMeetingId)
      || rows[0];
    const anchorIndex = orderedRows.indexOf(anchorRow);
    const nextRow = orderedRows.slice(anchorIndex + 1).find(
      (row) => !deletingIds.has(row.dataset.meetingId),
    );
    const previousRow = orderedRows.slice(0, Math.max(anchorIndex, 0)).reverse().find(
      (row) => !deletingIds.has(row.dataset.meetingId),
    );
    deleteFocusFallbackIds = [nextRow?.dataset.meetingId, previousRow?.dataset.meetingId].filter(Boolean);
  };

  const openDeleteDialog = (rows) => {
    const dialog = document.querySelector("[data-delete-dialog]");
    if (!dialog) return;
    const title = dialog.querySelector("[data-delete-title]");
    const count = dialog.querySelector("[data-delete-count]");
    const error = dialog.querySelector("[data-delete-error]");
    deleteReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    deleteReturnMeetingId = deleteReturnFocus?.closest("[data-meeting-row]")?.dataset.meetingId || "";
    pendingDeleteRows = rows.filter(Boolean);
    if (!pendingDeleteRows.length) return;
    captureDeletionFocusFallback(pendingDeleteRows);
    document.querySelector("#delete-feedback-region")?.replaceChildren();
    if (error) error.hidden = true;
    if (title) title.textContent = pendingDeleteRows.length === 1 ? dialog.dataset.titleOne : dialog.dataset.titleMany;
    if (count) count.textContent = deletingLabel(pendingDeleteRows.length);
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
    const currentReturnRow = allRows().find((row) => row.dataset.meetingId === deleteReturnMeetingId);
    const rowDeleteControl = currentReturnRow?.querySelector("[data-row-delete]");
    const fallbackRow = deleteFocusFallbackIds
      .map((meetingId) => allRows().find((row) => row.dataset.meetingId === meetingId))
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
      let submitted = false;
      const sync = () => {
        if (hidden) hidden.value = slots.map((slot) => slot.value).join("");
      };
      const maybeSubmit = () => {
        if (submitted || !slots.every((target) => target.value.length === 1)) return;
        submitted = true;
        if (form.requestSubmit) {
          form.requestSubmit();
        } else {
          form.submit();
        }
      };
      slots.forEach((slot, index) => {
        slot.addEventListener("input", () => {
          slot.value = slot.value.replace(/\D/g, "").slice(0, 1);
          sync();
          if (slot.value && slots[index + 1]) slots[index + 1].focus();
          maybeSubmit();
        });
        slot.addEventListener("keydown", (event) => {
          if (event.key === "Backspace" && !slot.value && slots[index - 1]) slots[index - 1].focus();
        });
        slot.addEventListener("paste", (event) => {
          const text = (event.clipboardData || window.clipboardData).getData("text").replace(/\D/g, "").slice(0, 6);
          if (!text) return;
          event.preventDefault();
          slots.forEach((target, offset) => { target.value = text[offset] || ""; });
          sync();
          const next = slots[Math.min(text.length, slots.length) - 1];
          if (next) next.focus();
          maybeSubmit();
        });
      });
      form.addEventListener("submit", () => {
        submitted = true;
        sync();
      });
      slots[0]?.focus();
    });
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

  const initSummaryFormats = () => {
    document.querySelectorAll("[data-summary-format-controls]").forEach((controls) => {
      if (controls.dataset.summaryFormatReady === "true") return;
      const button = controls.querySelector("[data-summary-format-button]");
      const refreshButton = controls.querySelector("[data-summary-refresh-button]");
      const listbox = controls.querySelector("[data-summary-format-listbox]");
      const pendingLabel = controls.querySelector("[data-summary-pending-format-label]");
      const status = document.querySelector("[data-summary-candidate-status]");
      const preview = document.querySelector("[data-summary-candidate-preview]");
      const dialog = document.querySelector("[data-summary-format-dialog]");
      const meetingId = controls.dataset.meetingId || "";
      const candidateStorageKey = `graf-summary-candidate-${meetingId}`;
      let currentOutcomeSetId = controls.dataset.currentOutcomeSetId || null;
      let activeTemplate = null;
      let pollingTimer = null;
      let pollAttempts = 0;
      let pollDeadline = 0;
      let pollDelay = 1500;
      let activeRequestIntent = "manual_format";
      let activeRequestIntentId = null;
      let candidateRequestGeneration = 0;
      let candidateRequestInFlightGeneration = null;
      if (!button || !listbox) return;
      controls.dataset.summaryFormatReady = "true";
      const options = () => Array.from(listbox.querySelectorAll('[role="option"]'));
      const close = ({ restoreFocus = true } = {}) => {
        listbox.hidden = true;
        button.setAttribute("aria-expanded", "false");
        if (restoreFocus) button.focus({ preventScroll: true });
      };
      const open = () => {
        listbox.hidden = false;
        button.setAttribute("aria-expanded", "true");
        const selected = listbox.querySelector('[role="option"][aria-selected="true"]');
        (selected || options()[0])?.focus({ preventScroll: true });
      };
      const setBusy = (busy) => {
        button.disabled = busy;
        if (refreshButton) refreshButton.disabled = busy;
        controls.setAttribute("aria-busy", busy ? "true" : "false");
      };
      const showStatus = (message, state = "generating", actions = []) => {
        if (!status) return;
        status.hidden = false;
        status.dataset.state = state;
        status.replaceChildren();
        const copy = document.createElement("span");
        copy.textContent = message;
        status.append(copy);
        const validActions = actions.filter((item) => (
          item
          && typeof item.text === "string"
          && typeof item.action === "function"
        ));
        if (!validActions.length) return;
        const actionRow = document.createElement("div");
        actionRow.className = "summary-candidate-actions";
        validActions.forEach(({ text, action, primary = false }) => {
          const actionButton = document.createElement("button");
          actionButton.type = "button";
          actionButton.textContent = text;
          if (primary) actionButton.className = "button";
          actionButton.addEventListener("click", action);
          actionRow.append(actionButton);
        });
        status.append(actionRow);
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
        summary_generation_unavailable: "Новый вариант сейчас недоступен. Текущие итоги сохранены.",
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
        if (dialog instanceof HTMLDialogElement) {
          dialog.showModal();
          dialog.querySelector("[data-summary-format-option]")?.focus({ preventScroll: true });
        } else {
          open();
        }
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
        showStatus("Проверяем новый вариант. Текущие итоги остаются на месте.");
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
      const clearPreview = () => {
        if (!preview) return;
        preview.hidden = true;
        preview.replaceChildren();
      };
      const loadPreview = async (candidate, generation = candidateRequestGeneration) => {
        if (generation !== candidateRequestGeneration) return null;
        clearPreview();
        if (candidate.state !== "ready") return null;
        try {
          const response = await fetch(
            `/api/v1/cabinet/meetings/${meetingId}/summary-candidates/${candidate.candidate_id}/preview`,
            { credentials: "same-origin", cache: "no-store" }
          );
          if (!response.ok) return null;
          const body = await response.json();
          if (generation !== candidateRequestGeneration) return null;
          const items = Array.isArray(body.items)
            ? body.items.filter((item) => item && typeof item === "object").slice(0, 24)
            : [];
          return items.length ? items : null;
        } catch (_error) {
          return null;
        }
      };
      const resolveCandidate = async (candidate, accept, generation = candidateRequestGeneration) => {
        if (generation !== candidateRequestGeneration) return;
        setBusy(true);
        try {
          const resolved = await mutate(
            `/api/v1/cabinet/meetings/${meetingId}/summary-candidates/${candidate.candidate_id}/${accept ? "accept" : "reject"}`,
            "POST",
            { expected_current_outcome_set_id: currentOutcomeSetId }
          );
          if (generation !== candidateRequestGeneration) return;
          currentOutcomeSetId = resolved.current_outcome_set_id || currentOutcomeSetId;
          if (accept) window.location.reload();
          else {
            if (status) status.hidden = true;
            clearPreview();
          }
        } catch (error) {
          if (isMeetingDetailRecoveredError(error)) return;
          if (generation !== candidateRequestGeneration) return;
          const code = error instanceof Error ? error.message : "";
          if (code === "summary_source_revision_stale") clearPreview();
          showStatus(candidateErrorCopy(code), "failed", [retryCandidateAction(code)]);
        } finally {
          if (generation === candidateRequestGeneration) setBusy(false);
        }
      };
      const candidateSections = [
        ["summary", "Кратко"],
        ["action_items", "Действия"],
        ["decisions", "Решения"],
        ["key_points", "Ключевые пункты"],
        ["followups", "Следующие шаги"],
        ["risks", "Риски"],
        ["questions", "Вопросы"],
        ["evidence", "Подтверждения"]
      ];
      const renderCandidateItem = (item) => {
        const article = document.createElement("article");
        article.className = "outcome-item";
        const text = document.createElement("p");
        text.className = "outcome-item-text";
        text.textContent = item.text || "Без текста";
        article.append(text);
        const metadata = [
          ["Ответственный", item.owner_text],
          ["Срок", item.due_date_text]
        ].filter(([, value]) => typeof value === "string" && value.trim());
        if (metadata.length) {
          const row = document.createElement("div");
          row.className = "notes-item-meta-row";
          metadata.forEach(([label, value]) => {
            const meta = document.createElement("span");
            meta.className = "notes-item-meta";
            meta.textContent = `${label}: ${value.trim()}`;
            row.append(meta);
          });
          article.append(row);
        }
        const refs = Array.isArray(item.source_refs)
          ? item.source_refs.filter((ref) => (
              ref?.seekable && Number.isFinite(Number.parseFloat(ref.start_seconds))
            ))
          : [];
        if (refs.length && document.querySelector("[data-transcript-turn]")) {
          const sources = document.createElement("div");
          sources.className = "notes-item-sources";
          const label = document.createElement("span");
          label.className = "notes-source-label";
          label.textContent = "Источник:";
          sources.append(label);
          const appendSource = (host, ref) => {
            const seconds = Number.parseFloat(ref.start_seconds);
            const source = document.createElement("button");
            source.type = "button";
            source.className = "notes-source-link";
            source.textContent = formatTime(seconds);
            source.dataset.seekSeconds = String(seconds);
            source.dataset.sourceSegment = ref.transcript_segment_id || "";
            source.setAttribute("aria-label", `Открыть источник ${formatTime(seconds)} в расшифровке`);
            host.append(source);
          };
          refs.slice(0, 2).forEach((ref) => appendSource(sources, ref));
          const overflow = refs.slice(2);
          if (overflow.length) {
            const more = document.createElement("details");
            more.className = "notes-source-more";
            const summary = document.createElement("summary");
            summary.textContent = `Ещё ${overflow.length}`;
            const sourceNoun = overflow.length === 1
              ? "источник"
              : overflow.length < 5 ? "источника" : "источников";
            summary.setAttribute("aria-label", `Показать ещё ${overflow.length} ${sourceNoun}`);
            more.append(summary);
            overflow.forEach((ref) => appendSource(more, ref));
            sources.append(more);
          }
          if (sources.childElementCount > 1) article.append(sources);
        }
        return article;
      };
      const appendCandidateSections = (host, entries) => {
        entries.forEach(([key, label, items]) => {
          const section = document.createElement("section");
          section.className = "summary-candidate-section";
          const heading = document.createElement("h4");
          heading.textContent = label;
          const list = document.createElement("div");
          list.className = "summary-candidate-items";
          items.forEach((item) => list.append(renderCandidateItem(item)));
          section.append(heading, list);
          host.append(section);
        });
      };
      const renderCandidate = (candidate, generation = candidateRequestGeneration) => {
        if (generation !== candidateRequestGeneration) return false;
        if (candidate.state === "generating") {
          clearPreview();
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
          showStatus(`Готовим формат «${candidate.format_name || activeTemplate?.name || "итогов"}». Текущие итоги остаются на месте.`);
          return;
        }
        window.clearTimeout(pollingTimer);
        window.sessionStorage.removeItem(candidateStorageKey);
        pollingTimer = null;
        setBusy(false);
        if (pendingLabel) pendingLabel.hidden = true;
        const renderPreview = () => {
          if (!preview) return;
          preview.hidden = false;
          preview.replaceChildren();
          preview.setAttribute("aria-label", "Предпросмотр нового варианта итогов");
          const heading = document.createElement("h3");
          heading.textContent = "Новый вариант";
          const source = document.createElement("p");
          source.className = "summary-candidate-source";
          const sourceLabel = candidate?.provenance?.source_revision_label
            ? `Источник: ${candidate.provenance.source_revision_label}`
            : "Источник: текущая расшифровка";
          source.textContent = candidate?.provenance?.source_result_id
            ? sourceLabel
            : "Источник: подтверждённая расшифровка недоступна";
          const previewItems = Array.isArray(candidate.preview) ? candidate.preview.slice(0, 24) : [];
          if (previewItems.length) {
            const grouped = candidateSections
              .map(([key, label]) => [
                key,
                label,
                previewItems.filter((item) => item.category === key)
              ])
              .filter(([, , items]) => items.length);
            const primary = grouped.filter(([key]) => ["summary", "action_items", "decisions"].includes(key));
            const secondary = grouped.filter(([key]) => !["summary", "action_items", "decisions"].includes(key));
            preview.append(heading, source);
            appendCandidateSections(preview, primary);
            if (secondary.length) {
              const more = document.createElement("details");
              more.className = "summary-candidate-more";
              const summary = document.createElement("summary");
              summary.textContent = `Ещё разделы · ${secondary.length}`;
              more.append(summary);
              appendCandidateSections(more, secondary);
              preview.append(more);
            }
          } else {
            const empty = document.createElement("p");
            empty.textContent = "Предпросмотр недоступен для этого варианта.";
            preview.append(heading, source, empty);
          }
        };
        if (candidate.state === "ready") {
          const previewItems = Array.isArray(candidate.preview) ? candidate.preview.slice(0, 24) : [];
          if (!previewItems.length) {
            clearPreview();
            setBusy(true);
            showStatus(
              `Вариант «${candidate.format_name || activeTemplate?.name || "итогов"}» готов. Загружаем предпросмотр…`,
              "generating",
            );
            void loadPreview(candidate, generation).then((loadedPreview) => {
              if (generation !== candidateRequestGeneration) return;
              setBusy(false);
              if (!loadedPreview?.length) {
                showStatus(
                  "Предпросмотр пока недоступен. Текущие итоги сохранены.",
                  "failed",
                  [{ text: "Обновить страницу", action: () => window.location.reload(), primary: true }],
                );
                return;
              }
              renderCandidate({ ...candidate, preview: loadedPreview }, generation);
            });
            return;
          }
          showStatus(`Вариант «${candidate.format_name || activeTemplate?.name || "итогов"}» готов. Текущие итоги сохранены.`, "ready", [
            { text: "Оставить текущие", action: () => resolveCandidate(candidate, false, generation) },
            { text: "Использовать", action: () => resolveCandidate(candidate, true, generation), primary: true }
          ]);
          renderPreview();
          return;
        }
        if (candidate.state === "accepted") {
          window.location.reload();
          return;
        }
        if (candidate.state === "expired") {
          const retry = retryCandidateAction(candidate) || {
            text: "Обновить страницу", action: () => window.location.reload(), primary: true
          };
          showStatus("Вариант устарел. Текущие итоги сохранены — запустите генерацию ещё раз.", "failed", [
            retry
          ]);
          return;
        }
        if (candidate.state === "stale") {
          const retry = retryCandidateAction(candidate) || {
            text: "Обновить страницу", action: () => window.location.reload(), primary: true
          };
          showStatus("Расшифровка изменилась, поэтому вариант закрыт. Текущие итоги сохранены.", "failed", [
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
        if (generation !== candidateRequestGeneration) return;
        window.clearTimeout(pollingTimer);
        pollingTimer = null;
        if (document.hidden) {
          setBusy(false);
          showStatus("Проверка приостановлена в фоне. Она продолжится при возвращении.", "generating", [
            { text: "Продолжить", action: () => resumeCandidatePolling(candidate, generation), primary: true }
          ]);
          return;
        }
        if (document.hidden || pollAttempts >= 40 || (pollDeadline && Date.now() >= pollDeadline)) {
          if (pollAttempts >= 40 || (pollDeadline && Date.now() >= pollDeadline)) {
            setBusy(false);
            showStatus("Генерация занимает больше обычного. Текущие итоги сохранены.", "failed", [
              { text: "Проверить снова", action: () => resumeCandidatePolling(candidate, generation), primary: true },
              { text: "Оставить текущие", action: () => { if (status) status.hidden = true; } }
            ]);
          }
          return;
        }
        pollingTimer = window.setTimeout(() => {
          pollingTimer = null;
          pollCandidate(candidate, generation);
        }, pollDelay);
      };
      const pollCandidate = async (candidate, generation = candidateRequestGeneration) => {
        if (generation !== candidateRequestGeneration) return;
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
          if (generation !== candidateRequestGeneration) return;
          renderCandidate(next, generation);
          if (next.state === "generating") {
            pollDelay = Math.min(10000, Math.round(pollDelay * 1.5));
            schedulePoll(next, generation);
          }
        } catch (error) {
          if (isMeetingDetailRecoveredError(error)) return;
          if (generation !== candidateRequestGeneration) return;
          pollingTimer = null;
          setBusy(false);
          const code = error instanceof Error ? error.message : "";
          const transientPollFailure = !code
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
            [retry, ...(transientPollFailure
              ? [{ text: "Оставить текущие", action: () => { if (status) status.hidden = true; } }]
              : [])]
          );
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
        showStatus(`Готовим формат «${template.name}». Текущие итоги остаются на месте.`);
        const body = {
          template_key: template.key,
          template_id: template.id || null,
          template_version: template.version,
          expected_current_outcome_set_id: currentOutcomeSetId,
          request_intent: requestIntent
        };
        if (requestIntentId) body.request_intent_id = requestIntentId;
        try {
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
        await requestCandidate(template, {
          requestIntent: "manual_refresh",
          requestIntentId: newRequestIntentId()
        });
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
      const applyServerCandidate = (candidate) => {
        currentOutcomeSetId = candidate.current_outcome_set_id || currentOutcomeSetId;
        activeTemplate = templateFromCandidate(candidate);
        renderCandidate(candidate);
        if (candidate.state === "generating") {
          pollingTimer = window.setTimeout(() => pollCandidate(candidate), 1200);
        }
      };
      button.addEventListener("click", () => listbox.hidden ? open() : close());
      button.addEventListener("keydown", (event) => {
        if (!["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        open();
        const items = options();
        const target = event.key === "ArrowUp" || event.key === "End"
          ? items[items.length - 1]
          : items[0];
        target?.focus({ preventScroll: true });
      });
      listbox.addEventListener("keydown", (event) => {
        const option = event.target.closest?.('[role="option"]');
        if (!option) return;
        if (event.key === "Escape") {
          event.preventDefault();
          close();
          return;
        }
        if (!["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        const items = options();
        const current = items.indexOf(option);
        const next = event.key === "Home" ? 0
          : event.key === "End" ? items.length - 1
          : (current + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
        items[next]?.focus({ preventScroll: true });
      });
      listbox.addEventListener("click", (event) => {
        const option = event.target.closest?.("[data-summary-format-option]");
        if (!option) return;
        close();
        const template = templateFrom(option);
        if (isCurrentFormat(template)) {
          showCurrentFormatAction(template);
          return;
        }
        requestTemplateVariant(template);
      });
      const allFormats = listbox.querySelector("[data-summary-format-all]");
      const closeDialog = () => {
        if (!(dialog instanceof HTMLDialogElement)) return;
        dialog.close();
        button.focus({ preventScroll: true });
      };
      allFormats?.addEventListener("click", async () => {
        close({ restoreFocus: false });
        if (!(dialog instanceof HTMLDialogElement)) return;
        dialog.showModal();
        dialog.querySelector("[data-summary-format-option]")?.focus({ preventScroll: true });
        const personalHost = dialog.querySelector("[data-summary-personal-options]");
        try {
          const response = await fetch("/api/v1/cabinet/summary-templates", { credentials: "same-origin", cache: "no-store" });
          if (!response.ok) return;
          const templates = await response.json();
          if (!personalHost || !templates.personal?.length) return;
          personalHost.hidden = false;
          personalHost.replaceChildren(...templates.personal.map((template) => {
            const option = document.createElement("button");
            option.type = "button";
            option.dataset.summaryFormatOption = "";
            option.dataset.templateId = template.template_id;
            option.dataset.templateKey = template.template_key;
            option.dataset.templateVersion = String(template.version);
            option.dataset.templateName = template.name;
            option.textContent = template.name;
            return option;
          }));
        } catch (_error) {
          // Built-in formats remain usable when the optional personal list cannot refresh.
        }
      });
      dialog?.querySelector("[data-summary-format-dialog-close]")?.addEventListener("click", closeDialog);
      dialog?.addEventListener("cancel", (event) => {
        event.preventDefault();
        closeDialog();
      });
      dialog?.addEventListener("keydown", (event) => trapModalFocus(dialog, event));
      dialog?.addEventListener("click", (event) => {
        if (event.target === dialog) closeDialog();
        const option = event.target.closest?.("[data-summary-format-option]");
        if (!option) return;
        closeDialog();
        const template = templateFrom(option);
        if (isCurrentFormat(template)) {
          showCurrentFormatAction(template);
          return;
        }
        requestTemplateVariant(template);
      });
      document.addEventListener("click", (event) => {
        if (!listbox.hidden && event.target instanceof Node && !controls.contains(event.target)) {
          close({ restoreFocus: false });
        }
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
        showStatus("Проверяем новый вариант. Текущие итоги остаются на месте.");
        pollCandidate({ poll_url: resumed.poll_url });
        return true;
      };
      const initialCandidateLoadGeneration = candidateRequestGeneration;
      fetch(`/api/v1/cabinet/meetings/${meetingId}/summary-candidates`, {
        credentials: "same-origin",
        cache: "no-store"
      }).then((response) => response.ok ? response.json() : null).then((payload) => {
        if (initialCandidateLoadGeneration !== candidateRequestGeneration) return;
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
        resumeCachedCandidate();
      }).catch(() => {
        resumeCachedCandidate();
      });
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
          const actions = document.createElement("div");
          actions.className = "summary-template-actions";
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
          renderTemplates(payload.personal || []);
          if (defaultSelect) {
            canManageDefault = payload.can_manage_default === true;
            defaultSelect.value = payload.default_template_key;
            defaultSelect.disabled = !canManageDefault;
          }
          if (defaultHelp) {
            defaultHelp.textContent = payload.can_manage_default
              ? "Используется для новых итогов, если формат встречи не выбран отдельно."
              : "Изменить может владелец пространства.";
          }
        } catch (_error) {
          if (list) list.textContent = "Не удалось загрузить личные форматы.";
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
    toggle.textContent = "▶";
    toggle.setAttribute("aria-label", "Воспроизвести");
  };

  const initSourceNavigation = () => {
    if (document.body.dataset.sourceNavigationReady === "true") return;
    document.body.dataset.sourceNavigationReady = "true";
    document.addEventListener("click", (event) => {
      const control = event.target.closest?.("[data-seek-seconds]");
      if (!control) return;
      const seconds = Number.parseFloat(control.dataset.seekSeconds || "0");
      if (!Number.isFinite(seconds)) return;
      const sourceJump = control.hasAttribute("data-source-segment");
      if (sourceJump) activateDetailTab("recording");
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
        target.scrollIntoView({ block: "center" });
        target.focus({ preventScroll: true });
        const live = document.querySelector("[data-playback-live-status]");
        if (live) live.textContent = `Открыт источник ${formatTime(seconds)} в расшифровке.`;
      });
    });
  };

  const initPlayback = () => {
    document.querySelectorAll("[data-playback-shell]").forEach((shell) => {
      if (shell.dataset.playbackReady === "true") return;
      shell.dataset.playbackReady = "true";
      const player = shell.querySelector("[data-playback-player]");
      if (!player) return;
      const toggle = shell.querySelector("[data-playback-toggle]");
      const current = shell.querySelector("[data-playback-current]");
      const duration = shell.querySelector("[data-playback-duration]");
      const progress = shell.querySelector("[data-playback-progress]");
      const speedToggle = shell.querySelector("[data-playback-speed-toggle]");
      const playbackError = shell.querySelector("[data-playback-error]");
      const lanes = Array.from(shell.querySelectorAll("[data-speaker-lane]"));
      const transcriptTurns = Array.from(document.querySelectorAll("[data-transcript-turn]"));
      const setToggleState = (playing) => {
        if (!toggle) return;
        toggle.textContent = playing ? "Ⅱ" : "▶";
        toggle.setAttribute("aria-label", playing ? "Приостановить" : "Воспроизвести");
      };
      const reportFailure = () => reportPlaybackFailure(player);
      const play = () => {
        if (playbackError) playbackError.hidden = true;
        return player.play().catch(reportFailure);
      };
      const playbackDuration = () => {
        if (Number.isFinite(player.duration) && player.duration > 0) return player.duration;
        const fallback = Number.parseFloat(progress?.max || "0");
        return Number.isFinite(fallback) && fallback > 0 ? fallback : 0;
      };
      const currentTranscriptTurn = (seconds) => {
        if (!transcriptTurns.length) return null;
        return transcriptTurns.reduce((match, turn) => {
          const start = Number.parseFloat(turn.dataset.startSeconds || "0");
          return Number.isFinite(start) && start <= seconds ? turn : match;
        }, transcriptTurns[0]);
      };
      const followTranscript = (seconds) => {
        const turn = currentTranscriptTurn(seconds);
        if (!turn) return;
        const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        turn.scrollIntoView({ block: "center", behavior: reducedMotion ? "auto" : "smooth" });
      };
      const syncTime = () => {
        if (current) current.textContent = formatTime(player.currentTime);
        if (progress) progress.value = String(player.currentTime || 0);
        if (duration && Number.isFinite(player.duration)) duration.textContent = formatTime(player.duration);
        const max = playbackDuration();
        const position = max > 0 ? Math.max(0, Math.min(100, player.currentTime / max * 100)) : 0;
        shell.style.setProperty("--playback-position", `${position}%`);
        lanes.forEach((lane) => {
          const active = Array.from(lane.querySelectorAll("[data-lane-segment]")).some((segment) => {
            const start = Number.parseFloat(segment.dataset.startSeconds || "0");
            const end = Number.parseFloat(segment.dataset.endSeconds || "0");
            return start <= player.currentTime && player.currentTime < end;
          });
          lane.classList.toggle("is-active", active);
          if (active) lane.setAttribute("aria-current", "true");
          else lane.removeAttribute("aria-current");
        });
        const activeTurn = currentTranscriptTurn(player.currentTime);
        transcriptTurns.forEach((turn) => turn.classList.toggle("is-current", turn === activeTurn));
      };
      const seekTo = (seconds, { follow = true, autoplay = false } = {}) => {
        if (!Number.isFinite(seconds)) return;
        const max = playbackDuration();
        player.currentTime = Math.max(0, Math.min(max || Number.POSITIVE_INFINITY, seconds));
        syncTime();
        if (follow) followTranscript(player.currentTime);
        if (autoplay) play();
      };
      player.addEventListener("loadedmetadata", () => {
        if (progress && Number.isFinite(player.duration)) progress.max = String(player.duration);
        syncTime();
      });
      player.addEventListener("timeupdate", syncTime);
      player.addEventListener("play", () => {
        setToggleState(true);
      });
      player.addEventListener("pause", () => {
        setToggleState(false);
      });
      player.addEventListener("ended", () => setToggleState(false));
      player.addEventListener("error", reportFailure);
      toggle?.addEventListener("click", () => {
        if (player.paused) play();
        else player.pause();
      });
      shell.querySelectorAll("[data-playback-skip]").forEach((button) => {
        button.addEventListener("click", () => {
          const delta = Number.parseFloat(button.dataset.playbackSkip || "0");
          if (!Number.isFinite(delta)) return;
          seekTo(player.currentTime + delta);
        });
      });
      progress?.addEventListener("input", () => {
        const next = Number.parseFloat(progress.value || "0");
        if (Number.isFinite(next)) {
          seekTo(next);
        }
      });
      lanes.forEach((lane) => {
        const track = lane.querySelector("[data-timeline-track]");
        if (!track) return;
        track.addEventListener("click", (event) => {
          const rect = track.getBoundingClientRect();
          const clientX = event.detail === 0 ? rect.left + rect.width / 2 : event.clientX;
          const ratio = rect.width > 0 ? Math.max(0, Math.min(1, (clientX - rect.left) / rect.width)) : 0;
          seekTo(playbackDuration() * ratio);
        });
        track.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          track.click();
        });
      });
      if (speedToggle) {
        const speeds = (speedToggle.dataset.speedOptions || "1").split(",")
          .map((value) => Number.parseFloat(value))
          .filter((value) => Number.isFinite(value) && value > 0);
        speedToggle.addEventListener("click", () => {
          const currentSpeed = player.playbackRate || 1;
          const index = speeds.findIndex((speed) => Math.abs(speed - currentSpeed) < 0.001);
          const nextSpeed = speeds[(index + 1) % speeds.length] || 1;
          player.playbackRate = nextSpeed;
          speedToggle.textContent = `${nextSpeed}x`;
        });
      }
    });
  };

  const initCalendarSettings = () => {
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
      dialog.addEventListener("close", () => restoreDialogFocus(dialog));
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

  const initSettingsFormState = () => {
    document.querySelectorAll("[data-settings-form]").forEach((form) => {
      if (form.dataset.settingsFormReady === "true") return;
      form.dataset.settingsFormReady = "true";
      const status = form.querySelector("[data-settings-form-status]");
      const submit = form.querySelector("button[type='submit']");
      const snapshot = () => new URLSearchParams(new FormData(form)).toString();
      let initial = snapshot();
      const update = () => {
        const dirty = snapshot() !== initial;
        form.dataset.state = dirty ? "dirty" : "pristine";
        if (status) {
          status.textContent = dirty ? "Есть несохранённые изменения" : "";
          status.hidden = !dirty;
        }
      };
      form.addEventListener("input", update);
      form.addEventListener("change", update);
      form.addEventListener("reset", () => window.setTimeout(update, 0));
      form.addEventListener("submit", () => {
        initial = snapshot();
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

  const initSettingsConfirmations = () => {
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

  const uploadMessages = {
    request_validation_error: "Проверьте файл.",
    csrf_token_missing: "Сессия устарела. Обновите страницу и попробуйте ещё раз.",
    csrf_token_invalid: "Сессия устарела. Обновите страницу и попробуйте ещё раз.",
    auth_session_required_for_manual_upload: "Войдите снова, чтобы загрузить файл.",
    auth_session_invalid: "Войдите снова, чтобы загрузить файл.",
    auth_session_expired: "Войдите снова, чтобы загрузить файл.",
    empty_media_upload: "Файл пустой. Выберите другой медиафайл.",
    upload_part_bytes_exceeded: "Файл больше текущего лимита. Выберите файл меньше.",
    unsafe_meeting_title: "Название содержит небезопасные данные. Измените его или оставьте поле пустым.",
    media_revision_not_accepting_uploads: "Эта загрузка уже принята. Откройте встречу в списке.",
    meeting_not_accepting_uploads: "Эта загрузка уже принята. Откройте встречу в списке.",
    idempotency_conflict: "Эта попытка отличается от уже начатой загрузки. Выберите файл заново.",
    media_revision_fingerprint_conflict: "Эта встреча уже приняла другой файл. Выберите файл заново."
  };

  const safeUploadMessage = (code) => uploadMessages[code] || "Не удалось загрузить файл. Попробуйте ещё раз.";
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
      if (dropTitle) dropTitle.textContent = "Перетащите файл сюда";
      dropZone?.classList.remove("has-file");
    };

    const resetDraft = () => {
      selectedFile = null;
      if (fileInput) fileInput.value = "";
      if (titleInput) titleInput.value = "";
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
        if (activity.progress) activity.progress.hidden = true;
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
      const progressActive = state === "uploading" && activity.progressDeterminate !== false;
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

    const createUploadActivity = ({ file, title, duration, localId }) => {
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
          <span data-upload-activity-status></span>
          <span class="upload-activity-progress" role="progressbar" aria-label="Прогресс загрузки" aria-valuemin="0" aria-valuemax="100" hidden>
            <span data-upload-activity-progress-bar></span>
          </span>
        </div>
        <span class="upload-activity-percent" data-upload-activity-percent hidden></span>
        <div class="upload-activity-actions" aria-label="Управление загрузкой">
          <button class="upload-activity-action" type="button" data-upload-activity-cancel>Отменить</button>
          <button class="upload-activity-action" type="button" data-upload-activity-retry hidden>Повторить</button>
          <button class="upload-activity-action" type="button" data-upload-activity-recover hidden>Восстановить</button>
          <button class="upload-activity-action" type="button" data-upload-activity-resume hidden>Продолжить</button>
          <a class="upload-activity-action" href="#" data-upload-activity-detail hidden>Открыть</a>
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
      if (activity.title) data.append("title", activity.title);

      const xhr = new XMLHttpRequest();
      activity.xhr = xhr;
      activity.accepted = false;
      activity.recoveryMode = null;
      activity.announcedProgressBucket = null;
      setActivityState(activity, "uploading", continued ? "Продолжаем загрузку…" : "Загружаем файл…");
      setActivityProgress(activity, 0, true);

      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable) {
          setActivityProgress(activity, 0, false);
          return;
        }
        const percent = Math.max(0, Math.min(99, Math.round((event.loaded / event.total) * 100)));
        setActivityProgress(activity, percent, true);
        setActivityState(activity, "uploading", "Загружаем файл…");
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
            activity.detailHref = `${dialog.dataset.uploadDetailBase || "/meetings"}/${meetingId}`;
            if (activity.detailLink) activity.detailLink.href = activity.detailHref;
          }
          const workflowStarted = payload.workflow_started === true;
          setActivityState(
            activity,
            "accepted",
            workflowStarted
              ? "Файл принят. Обработка началась."
              : "Файл принят. Обработка ещё не запущена. Проверьте статус встречи.",
            workflowStarted ? "success" : "warning"
          );
          clearUploadActivityPayload(activity);
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
        setActivityState(activity, "failed", safeUploadMessage(payload.code), "error");
      };
      xhr.onerror = () => {
        activity.xhr = null;
        setActivityState(activity, "failed", "Передача не подтверждена. Попробуйте ещё раз.", "error");
      };
      xhr.onabort = () => {
        activity.xhr = null;
        if (!activity.accepted) {
          setActivityState(activity, "canceled", "Передача остановлена. Можно продолжить из этой вкладки.", "warning");
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

    dialog.addEventListener("keydown", (event) => trapModalFocus(dialog, event));

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
        localId: localIdInput.value
      });
      startActivityUpload(activity);
      closeDialog();
      resetDraft();
    });

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) closeDialog();
    });
  };

  const setRailPinned = (shell, toggle, pinned) => {
    shell.classList.toggle("is-rail-pinned", pinned);
    toggle.setAttribute("aria-expanded", pinned ? "true" : "false");
    toggle.setAttribute("aria-label", pinned ? "Свернуть меню" : "Развернуть меню");
  };

  const initCabinetRail = () => {
    const shell = document.querySelector("[data-cabinet-shell].desktop-embedded");
    const sidebar = shell?.querySelector("[data-cabinet-navigation]");
    const toggle = shell?.querySelector("[data-cabinet-rail-toggle]");
    if (!shell || !sidebar || !toggle || shell.dataset.railReady === "true") return;
    shell.dataset.railReady = "true";
    toggle.addEventListener("click", () => {
      setRailPinned(shell, toggle, !shell.classList.contains("is-rail-pinned"));
    });
    sidebar.querySelectorAll("a[href]").forEach((link) => {
      link.addEventListener("click", () => setRailPinned(shell, toggle, false));
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") setRailPinned(shell, toggle, false);
    });
    document.addEventListener("click", (event) => {
      if (!shell.classList.contains("is-rail-pinned") || !(event.target instanceof Element)) return;
      if (!event.target.closest("[data-cabinet-navigation]")) setRailPinned(shell, toggle, false);
    });
  };

  const stopPlaybackRecoveryPolling = () => {
    if (!playbackRecoveryTimer) return;
    window.clearInterval(playbackRecoveryTimer);
    playbackRecoveryTimer = null;
  };

  const renderMeetingDetailRecovery = (detail, kind) => {
    stopPlaybackRecoveryPolling();
    const listPath = location.pathname.startsWith("/desktop/")
      ? "/desktop/meetings"
      : "/meetings";
    const copy = {
      session: ["Нужно войти снова", "Сессия завершилась.", "Войти"],
      workspace: ["Нужно выбрать пространство", "Доступ к выбранному пространству больше не подтверждён.", "Войти и выбрать пространство"],
      unavailable: ["Встреча больше недоступна", "Эта страница больше не может показывать запись.", "К списку встреч"],
    }[kind] || ["Встреча больше недоступна", "Эта страница больше не может показывать запись.", "К списку встреч"];
    const recovery = document.createElement("main");
    recovery.id = "cabinet-main";
    recovery.className = "cabinet-main";
    recovery.tabIndex = -1;
    const state = document.createElement("section");
    state.className = "empty-state cabinet-card";
    state.setAttribute("role", "status");
    state.setAttribute("aria-live", "polite");
    const title = document.createElement("h1");
    title.id = "meeting-detail-recovery-title";
    title.textContent = copy[0];
    const body = document.createElement("span");
    body.textContent = copy[1];
    const action = document.createElement("a");
    action.className = "new-button";
    action.textContent = copy[2];
    const requiresSignIn = kind === "session" || kind === "workspace";
    action.href = requiresSignIn
      ? `/login?next=${encodeURIComponent(listPath)}`
      : listPath;
    state.setAttribute("aria-labelledby", title.id);
    state.append(title, body, action);
    recovery.append(state);
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

  const showPlaybackRecoveryNotice = (detail) => {
    const playback = detail.querySelector(".detail-playback");
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
    detail.querySelector("[data-playback-recovery-copy]")?.remove();
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
      headers: { "HX-Request": "true" }
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
      const currentPlayback = detail.querySelector(".detail-playback");
      const nextPlayback = nextDetail?.querySelector(".detail-playback");
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
      if (playbackChanged) currentPlayback.replaceWith(nextPlayback);
      if (transcriptChanged) currentTranscript.replaceWith(nextTranscript);
      initPlayback();
      initPlaybackRecoveryPolling();
    } catch {
      showPlaybackRecoveryNotice(detail);
      return;
    } finally {
      playbackRecoveryRequest = null;
    }
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
          window.location.reload();
        } catch {
          if (error) error.hidden = false;
          if (submit) submit.disabled = false;
        }
      });
    });
  };

  const initContentExport = () => {
    const dialog = document.querySelector("[data-content-export-dialog]");
    const form = dialog?.querySelector("[data-content-export-form]");
    if (!dialog || !form || dialog.dataset.contentExportReady === "true") return;
    dialog.dataset.contentExportReady = "true";
    const scope = form.querySelector("[data-export-scope]");
    const format = form.querySelector("[data-export-format]");
    const title = dialog.querySelector("[data-export-dialog-title]");
    const status = form.querySelector("[data-export-status]");
    const submit = form.querySelector("[data-export-submit]");
    const copy = form.querySelector("[data-export-copy]");
    const speakers = form.querySelector("input[name='include_speaker_labels']");
    const timestamps = form.querySelector("input[name='include_timestamps']");
    const evidence = form.querySelector("input[name='include_evidence']");
    const formatGroups = [
      ["Текст", [["txt", "Текст (.txt)"], ["md", "Markdown (.md)"]]],
      ["Таблицы", [["csv", "Таблица CSV (.csv)"], ["xlsx", "Excel (.xlsx)"]]],
      ["Данные", [["json", "JSON (.json)"]]],
      ["Субтитры", [["srt", "Субтитры (.srt)"]]]
    ];
    let returnFocus = null;
    let submitting = false;

    const setStatus = (message, state = "") => {
      if (!status) return;
      status.textContent = message;
      status.dataset.state = state;
    };
    const updateOptions = () => {
      if (!scope || !format) return;
      const machineFormat = ["csv", "xlsx", "json"].includes(format.value);
      if (speakers) {
        if (machineFormat) speakers.checked = true;
        speakers.disabled = machineFormat;
      }
      if (timestamps) {
        if (machineFormat || format.value === "srt") timestamps.checked = true;
        timestamps.disabled = machineFormat || format.value === "srt";
      }
      if (evidence) evidence.disabled = scope.value === "transcript";
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
    const buildPayload = (requestedFormat = format?.value) => {
      const selectedScope = scope?.value || "transcript";
      return {
        content_scope: selectedScope,
        format: requestedFormat,
        processing_result_id: form.dataset.processingResultId,
        outcome_set_id: selectedScope === "transcript" ? null : (form.dataset.outcomeSetId || null),
        include_speaker_labels: include("include_speaker_labels"),
        include_timestamps: include("include_timestamps"),
        include_evidence: selectedScope !== "transcript" && include("include_evidence")
      };
    };
    const requestExport = async (requestedFormat = format?.value) => {
      const token = form.dataset.csrfToken || csrfToken;
      const response = await fetch(form.dataset.endpoint, {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "X-CSRF-Token": token } : {})
        },
        body: JSON.stringify(buildPayload(requestedFormat))
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
      if (submit) submit.disabled = busy;
      if (copy) copy.disabled = busy;
      if (busy) dialog.setAttribute("aria-busy", "true");
      else dialog.removeAttribute("aria-busy");
    };
    const errorMessage = (code) => ({
      export_revision_stale: "Данные изменились. Закройте окно, обновите встречу и повторите.",
      meeting_deletion_active: "Экспорт недоступен: встреча удаляется.",
      meeting_not_found: "Доступ к встрече изменился. Обновите страницу.",
      export_policy_denied: "Политика доступа к этому составу изменилась.",
      export_unavailable: "Этот состав сейчас недоступен по готовности или политике.",
      export_generation_failed: "Не удалось собрать файл. Повторите экспорт.",
      audit_unavailable: "Экспорт остановлен: не удалось сохранить обязательную запись аудита. Повторите позже.",
      unsupported_export_combination: "Выберите совместимый формат.",
      clipboard_unavailable: "Не удалось скопировать текст. Используйте скачивание TXT."
    }[code] || "Не удалось подготовить файл. Попробуйте ещё раз.");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (submitting || !scope || !format || !submit) return;
      setBusy(true);
      setStatus("Готовим файл…", "progress");
      try {
        const response = await requestExport();
        if (!response) return;
        const blob = await response.blob();
        const disposition = response.headers.get("Content-Disposition") || "";
        const filename = disposition.match(/filename="([^"]+)"/)?.[1] || "graf-export." + format.value;
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
        submit.focus({ preventScroll: true });
      }
    });
    copy?.addEventListener("click", async () => {
      if (submitting) return;
      setBusy(true);
      setStatus("Готовим текст для копирования…", "progress");
      try {
        if (!navigator.clipboard?.writeText) throw new Error("clipboard_unavailable");
        const response = await requestExport("txt");
        if (!response) return;
        await navigator.clipboard.writeText(await response.text());
        setStatus("Текст скопирован.", "success");
      } catch (error) {
        const code = error instanceof Error ? error.message : "export_failed";
        setStatus(errorMessage(code), "error");
      } finally {
        if (copy.isConnected) {
          setBusy(false);
          copy.focus({ preventScroll: true });
        }
      }
    });
  };

  const initMeetingDeleteDialog = () => {
    const dialog = document.querySelector("[data-meeting-delete-dialog]");
    const opener = document.querySelector("[data-meeting-delete-dialog-open]");
    if (!dialog || !opener || dialog.dataset.ready === "true") return;
    dialog.dataset.ready = "true";
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
    dialog.addEventListener("keydown", (event) => trapModalFocus(dialog, event));
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
        const response = await fetch(url, {
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
        if (!response.ok) throw new Error(String(response.status));
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
        const copy = row.querySelector("[data-share-copy-button]");
        const rotateUrl = row.querySelector("[data-share-rotate-url]")?.dataset.shareRotateUrl || "";
        const revoke = row.querySelector("[data-share-revoke-url]");
        let rowBusy = false;
        const setRowBusy = (busy) => {
          rowBusy = busy;
          [copy, revoke].forEach((control) => {
            if (control) control.disabled = busy;
          });
        };
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
        scope.textContent = "Итоги · ссылка готова";
        identity.append(name, scope);
        const actions = document.createElement("span");
        actions.className = "share-viewer-row__actions";
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
        status.textContent = `${statusLabel} · ${scopeLabel}${expiresAt && !Number.isNaN(expiresAt.valueOf()) ? ` · до ${expiresAt.toLocaleDateString("ru-RU")}` : ""}`;
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
              content_scope: "summary_only",
              can_download: false,
              can_export: false
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
          setStatus(`Доступ к итогам открыт: ${label}. Ссылка готова для копирования.${notificationMessage}`, "success");
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
              can_export: true
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
          const response = await fetch(`${form.action}?query=${encodeURIComponent(query)}`, {
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

  const initCabinet = () => {
    initAuthTransition();
    initCabinetRail();
    initListDisclosures();
    initCodeForms();
    initMeetingList();
    announceUploadProgress();
    initManualUpload();
    initDetailTabs();
    initSummaryFormats();
    initSummaryTemplateSettings();
    initMeetingContextPanels();
    initShareDialogs();
    initSourceNavigation();
    initPlayback();
    initMeetingDetailAuthorizationRecovery();
    initPlaybackRecoveryPolling();
    initSpeakerNameForms();
    initContentExport();
    initMeetingDeleteDialog();
    initCalendarSettings();
    initSettingsFormState();
    initSettingsConfirmations();
    initShareInvitationAutoAccept();
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
      if (pendingDeleteRows.length) {
        const pendingMeetingIds = new Set(pendingDeleteRows.map((row) => row.dataset.meetingId));
        pendingDeleteRows = allRows().filter((row) => pendingMeetingIds.has(row.dataset.meetingId));
        if (!pendingDeleteRows.length) {
          closeDeleteDialog();
        } else {
          const deleteDialog = document.querySelector("[data-delete-dialog]");
          const title = deleteDialog?.querySelector("[data-delete-title]");
          const count = deleteDialog?.querySelector("[data-delete-count]");
          const error = deleteDialog?.querySelector("[data-delete-error]");
          const confirm = deleteDialog?.querySelector("[data-delete-confirm]");
          const failures = pendingDeleteRows.length;
          if (title) {
            title.textContent = failures === 1
              ? deleteDialog.dataset.titleOne
              : deleteDialog.dataset.titleMany;
          }
          if (count) count.textContent = deletingLabel(failures);
          if (error) {
            error.textContent = `Не удалось удалить ${failures} ${plural(
              failures,
              "запись",
              "записи",
              "записей",
            )}. Попробуйте ещё раз.`;
            error.hidden = false;
          }
          if (confirm) confirm.textContent = "Повторить";
        }
      }
      reconcileMeetingSelection();
      announceMeetingResultCount();
      restoreMeetingListRequestFocus(event);
      restoreListRefreshFocus();
    }
    initCabinet();
  });

  window.addEventListener("pageshow", updateSelection);

  if (!csrfToken) return;

  document.body.addEventListener("htmx:configRequest", (event) => {
    const detail = event.detail || {};
    const verb = String(detail.verb || "get").toUpperCase();
    if (!["POST", "PUT", "PATCH", "DELETE"].includes(verb)) return;
    detail.headers = detail.headers || {};
    detail.headers["X-CSRF-Token"] = csrfToken;
  });
})();
