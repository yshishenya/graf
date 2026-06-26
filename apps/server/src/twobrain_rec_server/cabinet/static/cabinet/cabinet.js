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
      const sync = () => {
        if (hidden) hidden.value = slots.map((slot) => slot.value).join("");
      };
      slots.forEach((slot, index) => {
        slot.addEventListener("input", () => {
          slot.value = slot.value.replace(/\D/g, "").slice(0, 1);
          sync();
          if (slot.value && slots[index + 1]) slots[index + 1].focus();
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
        });
      });
      form.addEventListener("submit", sync);
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

  const initCabinet = () => {
    initAuthTransition();
    initCodeForms();
    initMeetingList();
    initDetailTabs();
    initPlayback();
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
