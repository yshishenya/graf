(() => {
  document.documentElement.dataset.cabinetJs = "ready";

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
  let pendingDeleteRows = [];

  const plural = (value, one, few, many) => {
    const mod10 = value % 10;
    const mod100 = value % 100;
    if (mod10 === 1 && mod100 !== 11) return one;
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
    return many;
  };

  const currentList = () => document.querySelector("[data-meeting-list]");
  const allRows = () => Array.from(currentList()?.querySelectorAll("[data-meeting-row]") || []);
  const selectedRows = () => allRows().filter((row) => row.querySelector("[data-meeting-select]")?.checked);
  const deletingLabel = (value) => `Вы удаляете ${value} ${plural(value, "запись", "записи", "записей")}.`;

  const updateSelection = () => {
    const list = currentList();
    const toolbar = document.querySelector("[data-selection-toolbar]");
    const listTitle = document.querySelector("[data-list-title]");
    const countLabel = document.querySelector("[data-selection-count]");
    const selectionToggle = document.querySelector("[data-selection-toggle]");
    if (!list || !toolbar || !countLabel) return;
    const rows = selectedRows();
    const total = allRows().length;
    const allSelected = total > 0 && rows.length === total;
    countLabel.textContent = `Выбрано ${rows.length} / ${total}`;
    toolbar.hidden = rows.length === 0;
    toolbar.dataset.selectionState = allSelected ? "all" : "partial";
    if (selectionToggle) {
      selectionToggle.checked = allSelected;
      selectionToggle.indeterminate = rows.length > 0 && !allSelected;
      selectionToggle.setAttribute("aria-label", allSelected ? "Снять выбор" : "Выбрать все видимые записи");
    }
    if (listTitle) listTitle.hidden = rows.length > 0;
    allRows().forEach((row) => {
      row.classList.toggle("is-selected", row.querySelector("[data-meeting-select]")?.checked === true);
    });
  };

  const openDeleteDialog = (rows) => {
    const dialog = document.querySelector("[data-delete-dialog]");
    if (!dialog) return;
    const title = dialog.querySelector("[data-delete-title]");
    const count = dialog.querySelector("[data-delete-count]");
    const error = dialog.querySelector("[data-delete-error]");
    pendingDeleteRows = rows.filter(Boolean);
    if (!pendingDeleteRows.length) return;
    if (error) error.hidden = true;
    if (title) title.textContent = pendingDeleteRows.length === 1 ? dialog.dataset.titleOne : dialog.dataset.titleMany;
    if (count) count.textContent = deletingLabel(pendingDeleteRows.length);
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  };

  const closeDeleteDialog = () => {
    const dialog = document.querySelector("[data-delete-dialog]");
    pendingDeleteRows = [];
    if (!dialog) return;
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  };

  const formValues = (form) => {
    const values = {};
    new FormData(form).forEach((value, key) => {
      if (typeof value === "string") values[key] = value;
    });
    return values;
  };

  const submitDeletionForm = async (form) => {
    if (window.htmx?.ajax) {
      const headers = {};
      if (csrfToken) headers["X-CSRF-Token"] = csrfToken;
      await window.htmx.ajax("POST", form.action, {
        target: "#delete-feedback-region",
        swap: "innerHTML",
        select: "[data-cabinet-fragment='deletion-feedback']",
        values: formValues(form),
        headers
      });
      return;
    }
    form.submit();
  };

  const initMeetingList = () => {
    if (!currentList() || document.body.dataset.cabinetMeetingListReady === "true") {
      updateSelection();
      return;
    }
    document.body.dataset.cabinetMeetingListReady = "true";
    document.body.addEventListener("change", (event) => {
      if (event.target.closest("[data-meeting-select]")) updateSelection();
    });
    document.body.addEventListener("click", async (event) => {
      const deleteButton = event.target.closest("[data-row-delete]");
      if (deleteButton) {
        openDeleteDialog([deleteButton.closest("[data-meeting-row]")]);
        return;
      }
      if (event.target.closest("[data-selection-delete]")) {
        openDeleteDialog(selectedRows());
        return;
      }
      if (event.target.closest("[data-delete-cancel]")) {
        closeDeleteDialog();
        return;
      }
      const selectionToggle = event.target.closest("[data-selection-toggle]");
      if (selectionToggle) {
        const rows = allRows();
        const shouldSelectAll = selectedRows().length !== rows.length;
        rows.forEach((row) => {
          const checkbox = row.querySelector("[data-meeting-select]");
          if (checkbox) checkbox.checked = shouldSelectAll;
        });
        updateSelection();
        return;
      }
      const confirm = event.target.closest("[data-delete-confirm]");
      if (confirm) {
        if (!pendingDeleteRows.length) return;
        const dialog = document.querySelector("[data-delete-dialog]");
        const error = dialog?.querySelector("[data-delete-error]");
        confirm.disabled = true;
        confirm.textContent = "Удаляем...";
        let failures = 0;
        for (const row of pendingDeleteRows) {
          const form = row.querySelector("[data-row-delete-form]");
          if (!form) {
            failures += 1;
            continue;
          }
          try {
            await submitDeletionForm(form);
            const checkbox = row.querySelector("[data-meeting-select]");
            if (checkbox) checkbox.checked = false;
            row.dataset.deletionRequested = "true";
          } catch (_err) {
            failures += 1;
          }
        }
        confirm.disabled = false;
        confirm.textContent = "Удалить";
        updateSelection();
        if (failures && error) {
          error.textContent = failures === 1 ? "Не удалось удалить одну запись. Попробуйте еще раз." : `Не удалось удалить ${failures} ${plural(failures, "запись", "записи", "записей")}. Попробуйте еще раз.`;
          error.hidden = false;
          pendingDeleteRows = [];
          return;
        }
        closeDeleteDialog();
        return;
      }
      const row = event.target.closest("[data-meeting-row]");
      if (!row || event.target.closest("a,button,input")) return;
      const checkbox = row.querySelector("[data-meeting-select]");
      if (!checkbox) return;
      checkbox.checked = !checkbox.checked;
      updateSelection();
    });
    updateSelection();
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

  const activateDetailTab = (name) => {
    const tabs = Array.from(document.querySelectorAll("[data-detail-tab]"));
    const panels = Array.from(document.querySelectorAll("[data-detail-panel]"));
    tabs.forEach((tab) => {
      const selected = tab.dataset.detailTab === name;
      tab.classList.toggle("active", selected);
      tab.setAttribute("aria-selected", selected ? "true" : "false");
    });
    panels.forEach((panel) => {
      const selected = panel.dataset.detailPanel === name;
      panel.classList.toggle("active", selected);
      panel.hidden = !selected;
    });
  };

  const initDetailTabs = () => {
    const tabs = Array.from(document.querySelectorAll("[data-detail-tab]"));
    const panels = Array.from(document.querySelectorAll("[data-detail-panel]"));
    if (!tabs.length || !panels.length) return;
    tabs.forEach((tab) => {
      if (tab.dataset.detailTabReady === "true") return;
      tab.dataset.detailTabReady = "true";
      tab.addEventListener("click", () => activateDetailTab(tab.dataset.detailTab || "recording"));
    });
    if (window.location.hash === "#outcomes") activateDetailTab("outcomes");
  };

  const formatTime = (seconds) => {
    if (!Number.isFinite(seconds) || seconds < 0) return "00:00";
    const rounded = Math.floor(seconds);
    const minutes = Math.floor(rounded / 60);
    const rest = String(rounded % 60).padStart(2, "0");
    return `${String(minutes).padStart(2, "0")}:${rest}`;
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
      const syncTime = () => {
        if (current) current.textContent = formatTime(player.currentTime);
        if (progress) progress.value = String(player.currentTime || 0);
        if (duration && Number.isFinite(player.duration)) duration.textContent = formatTime(player.duration);
      };
      player.addEventListener("loadedmetadata", () => {
        if (progress && Number.isFinite(player.duration)) progress.max = String(player.duration);
        syncTime();
      });
      player.addEventListener("timeupdate", syncTime);
      player.addEventListener("play", () => {
        if (toggle) toggle.textContent = "Pause";
      });
      player.addEventListener("pause", () => {
        if (toggle) toggle.textContent = "Play";
      });
      toggle?.addEventListener("click", () => {
        if (player.paused) player.play().catch(() => {});
        else player.pause();
      });
      shell.querySelectorAll("[data-playback-skip]").forEach((button) => {
        button.addEventListener("click", () => {
          const delta = Number.parseFloat(button.dataset.playbackSkip || "0");
          if (!Number.isFinite(delta)) return;
          const max = Number.isFinite(player.duration) ? player.duration : Number.POSITIVE_INFINITY;
          player.currentTime = Math.max(0, Math.min(max, player.currentTime + delta));
          syncTime();
        });
      });
      progress?.addEventListener("input", () => {
        const next = Number.parseFloat(progress.value || "0");
        if (Number.isFinite(next)) {
          player.currentTime = next;
          syncTime();
        }
      });
      document.querySelectorAll("[data-seek-seconds]").forEach((button) => {
        if (button.dataset.seekReady === "true") return;
        button.dataset.seekReady = "true";
        button.addEventListener("click", () => {
          const seekSeconds = Number.parseFloat(button.dataset.seekSeconds || "0");
          if (!Number.isFinite(seekSeconds)) return;
          player.currentTime = seekSeconds;
          syncTime();
          player.play().catch(() => {});
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
    const openCalendarDialog = (dialog) => {
      if (!dialog) return;
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
      const firstField = dialog.querySelector("input:not([type='hidden']), button[type='submit'], button:not([data-calendar-provider-close])");
      firstField?.focus({ preventScroll: true });
    };
    const closeCalendarDialog = (dialog) => {
      if (!dialog) return;
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
    };
    document.querySelectorAll("[data-calendar-provider-open]").forEach((button) => {
      if (button.dataset.calendarProviderOpenReady === "true") return;
      button.dataset.calendarProviderOpenReady = "true";
      button.addEventListener("click", () => {
        const dialogId = button.dataset.calendarProviderOpen || "";
        openCalendarDialog(document.getElementById(dialogId));
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

  const uploadMessages = {
    request_validation_error: "Проверьте файл и длительность.",
    csrf_token_missing: "Сессия устарела. Обновите страницу и попробуйте еще раз.",
    csrf_token_invalid: "Сессия устарела. Обновите страницу и попробуйте еще раз.",
    auth_session_required_for_manual_upload: "Войдите снова, чтобы загрузить файл.",
    auth_session_invalid: "Войдите снова, чтобы загрузить файл.",
    auth_session_expired: "Войдите снова, чтобы загрузить файл.",
    empty_media_upload: "Файл пустой. Выберите другой медиафайл.",
    upload_part_bytes_exceeded: "Файл больше текущего лимита. Выберите файл меньше.",
    unsafe_meeting_title: "Название содержит небезопасные данные. Измените его или оставьте поле пустым.",
    media_revision_not_accepting_uploads: "Эта загрузка уже принята. Откройте встречу в списке.",
    meeting_not_accepting_uploads: "Эта загрузка уже принята. Откройте встречу в списке.",
    idempotency_conflict: "Эта попытка отличается от уже начатой загрузки. Выберите файл заново."
  };

  const safeUploadMessage = (code) => uploadMessages[code] || "Не удалось загрузить файл. Попробуйте еще раз.";

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

  const refreshMeetingList = async (dialog) => {
    const target = document.querySelector("#meeting-list-region");
    if (!target || !window.htmx?.ajax) return;
    const refreshUrl = dialog.dataset.uploadRefreshUrl || `${window.location.pathname}${window.location.search}`;
    try {
      await window.htmx.ajax("GET", refreshUrl, {
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
    const status = dialog.querySelector("[data-manual-upload-status]");
    const percentLabel = dialog.querySelector("[data-manual-upload-percent]");
    const progress = dialog.querySelector("[data-manual-upload-progress]");
    const submit = dialog.querySelector("[data-manual-upload-submit]");
    const abort = dialog.querySelector("[data-manual-upload-abort]");
    const accepted = dialog.querySelector("[data-manual-upload-accepted]");
    const detailLink = dialog.querySelector("[data-manual-upload-detail]");
    let selectedFile = null;
    let currentRequest = null;
    let acceptedByServer = false;
    let lastTrigger = null;

    const setStatus = (message, tone = "neutral") => {
      if (!status) return;
      status.textContent = message;
      status.dataset.tone = tone;
    };

    const setPercent = (value, visible = false) => {
      if (!percentLabel) return;
      percentLabel.hidden = !visible;
      percentLabel.textContent = `${Math.max(0, Math.min(100, value || 0))}%`;
    };

    const syncReady = () => {
      const duration = Number.parseInt(durationInput?.value || "0", 10);
      const ready = Boolean(selectedFile && Number.isFinite(duration) && duration > 0 && csrfToken);
      if (submit) submit.disabled = !ready || Boolean(currentRequest);
    };

    const ensureLocalId = () => {
      if (!localIdInput || localIdInput.value) return;
      localIdInput.value = `manual-upload-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
    };

    const resetProgress = () => {
      acceptedByServer = false;
      if (accepted) accepted.hidden = true;
      if (detailLink) {
        detailLink.hidden = true;
        detailLink.href = "#";
      }
      if (progress) {
        progress.hidden = true;
        progress.removeAttribute("aria-valuenow");
        progress.value = 0;
      }
      setPercent(0);
      if (abort) abort.hidden = true;
    };

    const resetFilePreview = () => {
      if (fileCard) fileCard.hidden = true;
      if (fileName) fileName.textContent = "Файл не выбран";
      if (fileMeta) fileMeta.textContent = "";
      if (fileDuration) fileDuration.textContent = "";
      if (dropTitle) dropTitle.textContent = "Перетащите файл сюда";
      dropZone?.classList.remove("has-file");
    };

    const setSelectedFile = async (file) => {
      resetProgress();
      selectedFile = file || null;
      if (localIdInput) localIdInput.value = "";
      if (durationInput) durationInput.value = "";
      if (!selectedFile) {
        resetFilePreview();
        setStatus("Выберите один файл.");
        syncReady();
        return;
      }

      ensureLocalId();
      if (fileCard) fileCard.hidden = false;
      if (fileName) fileName.textContent = selectedFile.name || "Файл без названия";
      if (fileMeta) fileMeta.textContent = formatBytes(selectedFile.size);
      if (fileDuration) fileDuration.textContent = "Проверяем...";
      if (dropTitle) dropTitle.textContent = "Файл выбран";
      dropZone?.classList.add("has-file");
      setStatus("Проверяем длительность...");

      const activeFile = selectedFile;
      const duration = await readMediaDuration(selectedFile);
      if (activeFile !== selectedFile) return;
      if (duration && durationInput) {
        durationInput.value = String(duration);
        if (fileDuration) fileDuration.textContent = `${duration} сек.`;
        setStatus("Файл готов к загрузке.");
      } else {
        if (fileDuration) fileDuration.textContent = "Укажите длительность";
        setStatus("Введите примерную длительность перед загрузкой.", "warning");
      }
      syncReady();
    };

    const openDialog = (trigger) => {
      lastTrigger = trigger;
      if (dialog.dataset.uploadAvailable !== "true" || !csrfToken) {
        setStatus("Войдите снова, чтобы загрузить файл.", "error");
      }
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
      const focusTarget = fileInput || dialog.querySelector("a,button,input");
      focusTarget?.focus({ preventScroll: true });
    };

    const closeDialog = () => {
      if (currentRequest && !acceptedByServer) currentRequest.abort();
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
      lastTrigger?.focus({ preventScroll: true });
    };

    document.querySelectorAll("[data-manual-upload-open]").forEach((button) => {
      if (button.dataset.manualUploadOpenReady === "true") return;
      button.dataset.manualUploadOpenReady = "true";
      button.addEventListener("click", () => openDialog(button));
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
          resetProgress();
          selectedFile = null;
          if (fileInput) fileInput.value = "";
          if (durationInput) durationInput.value = "";
          if (localIdInput) localIdInput.value = "";
          resetFilePreview();
          setStatus("Можно загрузить только один файл.", "error");
          syncReady();
          return;
        }
        await setSelectedFile(files[0] || null);
      });
    }

    durationInput?.addEventListener("input", () => {
      const duration = Number.parseInt(durationInput.value || "0", 10);
      if (selectedFile && Number.isFinite(duration) && duration > 0) {
        if (fileDuration) fileDuration.textContent = `${duration} сек.`;
        setStatus("Файл готов к загрузке.");
      }
      syncReady();
    });

    submit?.addEventListener("click", () => {
      if (!selectedFile || !durationInput || !localIdInput || !csrfToken || currentRequest) {
        syncReady();
        return;
      }
      const duration = Number.parseInt(durationInput.value || "0", 10);
      if (!Number.isFinite(duration) || duration <= 0) {
        setStatus("Введите положительную длительность.", "error");
        syncReady();
        return;
      }
      ensureLocalId();
      const data = new FormData();
      data.append("file", selectedFile);
      data.append("duration_seconds", String(duration));
      data.append("local_recording_id", localIdInput.value);
      const title = titleInput?.value?.trim();
      if (title) data.append("title", title);

      const xhr = new XMLHttpRequest();
      currentRequest = xhr;
      acceptedByServer = false;
      submit.disabled = true;
      if (abort) abort.hidden = false;
      if (progress) {
        progress.hidden = false;
        progress.value = 0;
        progress.removeAttribute("aria-valuenow");
      }
      setPercent(0, true);
      setStatus("Загружаем файл...");

      xhr.upload.onprogress = (event) => {
        if (!progress || !event.lengthComputable) return;
        const percent = Math.max(0, Math.min(100, Math.round((event.loaded / event.total) * 100)));
        progress.value = percent;
        progress.setAttribute("aria-valuenow", String(percent));
        setPercent(percent, true);
        setStatus("Загружаем файл...");
      };
      xhr.onload = async () => {
        currentRequest = null;
        if (abort) abort.hidden = true;
        let payload = {};
        try {
          payload = JSON.parse(xhr.responseText || "{}");
        } catch (_err) {
          payload = {};
        }
        if (xhr.status >= 200 && xhr.status < 300) {
          acceptedByServer = true;
          if (progress) {
            progress.value = 100;
            progress.setAttribute("aria-valuenow", "100");
          }
          setPercent(100, true);
          setStatus("Файл принят. Обработка началась.", "success");
          const meetingId = payload.meeting?.meeting_id;
          if (meetingId && detailLink) {
            detailLink.href = `${dialog.dataset.uploadDetailBase || "/meetings"}/${meetingId}`;
            detailLink.hidden = false;
          }
          if (accepted) accepted.hidden = false;
          await refreshMeetingList(dialog);
          return;
        }
        setStatus(safeUploadMessage(payload.code), "error");
        syncReady();
      };
      xhr.onerror = () => {
        currentRequest = null;
        if (abort) abort.hidden = true;
        setStatus("Передача не подтверждена. Попробуйте еще раз.", "error");
        syncReady();
      };
      xhr.onabort = () => {
        currentRequest = null;
        if (abort) abort.hidden = true;
        if (!acceptedByServer) setStatus("Передача остановлена до подтверждения.", "warning");
        syncReady();
      };
      xhr.open("POST", dialog.dataset.uploadEndpoint || "/api/v1/cabinet/media-uploads");
      xhr.setRequestHeader("X-CSRF-Token", csrfToken);
      xhr.send(data);
    });

    abort?.addEventListener("click", () => {
      if (currentRequest && !acceptedByServer) currentRequest.abort();
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

  const initCabinet = () => {
    initAuthTransition();
    initCabinetRail();
    initCodeForms();
    initMeetingList();
    initManualUpload();
    initDetailTabs();
    initPlayback();
    initCalendarSettings();
  };

  document.body.addEventListener("htmx:afterSwap", (event) => {
    const target = event.detail?.target;
    if (target instanceof Element && (target.id === "meeting-list-region" || target.matches("[data-meeting-list]"))) {
      target.querySelectorAll("[data-meeting-select]").forEach((input) => {
        input.checked = false;
      });
    }
    initCabinet();
  });

  initCabinet();

  if (!csrfToken) return;

  document.body.addEventListener("htmx:configRequest", (event) => {
    const detail = event.detail || {};
    const verb = String(detail.verb || "get").toUpperCase();
    if (!["POST", "PUT", "PATCH", "DELETE"].includes(verb)) return;
    detail.headers = detail.headers || {};
    detail.headers["X-CSRF-Token"] = csrfToken;
  });
})();
