(() => {
  document.documentElement.dataset.cabinetJs = "ready";

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
  let pendingDeleteRows = [];
  let deleteReturnFocus = null;
  let deleteReturnMeetingId = "";
  let playbackRecoveryTimer = null;
  let playbackRecoveryRequest = null;

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

  const listInteractionIsActive = () => {
    const region = document.querySelector("#meeting-list-region");
    if (!region) return false;
    const modalIsOpen = document.querySelector("[data-delete-dialog][open], [data-meeting-delete-dialog][open], [data-manual-upload-dialog][open], [data-content-export-dialog][open], [data-meeting-context-panel=details][open]");
    return Boolean(modalIsOpen) || region.contains(document.activeElement) || region.matches(":hover") || selectedRows().length > 0;
  };

  const setRowContextualAvailability = (row, visible) => {
    row?.querySelectorAll("[data-row-contextual]").forEach((control) => {
      control.setAttribute("aria-hidden", visible ? "false" : "true");
      control.tabIndex = visible ? 0 : -1;
    });
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
      const selected = row.querySelector("[data-meeting-select]")?.checked === true;
      row.classList.toggle("is-selected", selected);
      if (selected) setRowContextualAvailability(row, true);
    });
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
    const returnControl = isUsableFocusTarget(deleteReturnFocus)
      ? deleteReturnFocus
      : isUsableFocusTarget(rowDeleteControl) ? rowDeleteControl : null;
    if (restoreFocus && returnControl) {
      setRowContextualAvailability(currentReturnRow, true);
      returnControl.focus({ preventScroll: true });
    } else if (restoreFocus) {
      document.querySelector("[data-list-title]")?.focus({ preventScroll: true });
    }
    deleteReturnFocus = null;
    deleteReturnMeetingId = "";
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
    if (!response.ok) throw new Error("deletion_request_failed");
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
      const source = event.detail?.elt || event.target;
      if (source instanceof Element && source.matches("[data-upload-progress-poll]") && listInteractionIsActive()) {
        event.preventDefault();
      }
    });
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
      if (event.target.closest("[data-clear-selection]")) {
        const returnRow = selectedRows()[0];
        allRows().forEach((row) => {
          const checkbox = row.querySelector("[data-meeting-select]");
          if (checkbox) checkbox.checked = false;
          setRowContextualAvailability(row, row.contains(document.activeElement));
        });
        updateSelection();
        (returnRow?.isConnected ? returnRow : document.querySelector("[data-list-title]"))?.focus({ preventScroll: true });
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
        if (!shouldSelectAll) rows[0]?.focus({ preventScroll: true });
        return;
      }
      const confirm = event.target.closest("[data-delete-confirm]");
      if (confirm) {
        if (!pendingDeleteRows.length) return;
        const dialog = document.querySelector("[data-delete-dialog]");
        const error = dialog?.querySelector("[data-delete-error]");
        if (error) error.hidden = true;
        confirm.disabled = true;
        confirm.textContent = "Удаляем…";
        const failedRows = [];
        for (const row of pendingDeleteRows) {
          const form = row.querySelector("[data-row-delete-form]");
          if (!form) {
            failedRows.push(row);
            continue;
          }
          try {
            await submitDeletionForm(form);
            const checkbox = row.querySelector("[data-meeting-select]");
            if (checkbox) checkbox.checked = false;
            row.remove();
          } catch (_err) {
            failedRows.push(row);
          }
        }
        confirm.disabled = false;
        confirm.textContent = "Удалить";
        updateSelection();
        if (failedRows.length && error) {
          const failures = failedRows.length;
          error.textContent = failures === 1 ? "Не удалось удалить одну запись. Попробуйте ещё раз." : `Не удалось удалить ${failures} ${plural(failures, "запись", "записи", "записей")}. Попробуйте ещё раз.`;
          error.hidden = false;
          pendingDeleteRows = failedRows;
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
    document.body.addEventListener("pointerover", (event) => {
      const row = event.target.closest?.("[data-meeting-row]");
      if (row) setRowContextualAvailability(row, true);
    });
    document.body.addEventListener("pointerout", (event) => {
      const row = event.target.closest?.("[data-meeting-row]");
      if (!row || row.contains(event.relatedTarget)) return;
      const selected = row.querySelector("[data-meeting-select]")?.checked === true;
      if (!selected && !row.contains(document.activeElement)) setRowContextualAvailability(row, false);
    });
    document.body.addEventListener("focusin", (event) => {
      const row = event.target.closest?.("[data-meeting-row]");
      if (row) setRowContextualAvailability(row, true);
    });
    document.body.addEventListener("focusout", (event) => {
      const row = event.target.closest?.("[data-meeting-row]");
      if (!row) return;
      window.setTimeout(() => {
        const selected = row.querySelector("[data-meeting-select]")?.checked === true;
        if (!selected && !row.contains(document.activeElement)) setRowContextualAvailability(row, false);
      }, 0);
    });
    allRows().forEach((row) => setRowContextualAvailability(row, false));
    updateSelection();
  };

  const initListDisclosures = () => {
    const form = document.querySelector(".cabinet-list-controls");
    if (form && form.dataset.refinementReady !== "true") {
      form.dataset.refinementReady = "true";
      const syncRefinementState = () => {
        const status = form.querySelector("#meeting-status");
        const access = form.querySelector("#meeting-access");
        const search = form.querySelector("#meeting-search");
        const sort = form.querySelector("#meeting-sort");
        const filterDisclosure = form.querySelector("[data-filter-disclosure]");
        const filterCount = filterDisclosure?.querySelector(".cabinet-control-count");
        const reset = form.querySelector("[data-filter-reset]");
        const activeFilterCount = Number(Boolean(status?.value)) + Number(Boolean(access?.value));
        filterDisclosure?.classList.toggle("is-active", activeFilterCount > 0);
        if (filterCount) {
          filterCount.hidden = activeFilterCount === 0;
          filterCount.textContent = String(activeFilterCount);
          filterCount.setAttribute("aria-label", `Активных фильтров: ${activeFilterCount}`);
        }
        if (reset) reset.hidden = !(search?.value.trim() || activeFilterCount > 0);
        const sortLabel = sort?.selectedOptions[0]?.textContent?.trim();
        if (sortLabel) {
          const visibleSortLabel = document.querySelector("[data-current-sort-label]");
          if (visibleSortLabel) visibleSortLabel.textContent = sortLabel;
          form.querySelector("[data-sort-disclosure] > summary")?.setAttribute("aria-label", `Сортировка: ${sortLabel}`);
        }
      };
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

  const activateDetailTab = (name) => {
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
    if (window.location.hash === "#outcomes") activateDetailTab("outcomes");
  };

  const initSummaryFormats = () => {
    document.querySelectorAll("[data-summary-format-controls]").forEach((controls) => {
      if (controls.dataset.summaryFormatReady === "true") return;
      const button = controls.querySelector("[data-summary-format-button]");
      const listbox = controls.querySelector("[data-summary-format-listbox]");
      const status = document.querySelector("[data-summary-candidate-status]");
      const dialog = document.querySelector("[data-summary-format-dialog]");
      const meetingId = controls.dataset.meetingId || "";
      const candidateStorageKey = `graf-summary-candidate-${meetingId}`;
      let currentOutcomeSetId = controls.dataset.currentOutcomeSetId || null;
      let activeTemplate = null;
      let pollingTimer = null;
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
        if (!actions.length) return;
        const actionRow = document.createElement("div");
        actionRow.className = "summary-candidate-actions";
        actions.forEach(({ text, action, primary = false }) => {
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
        summary_transcript_snapshot_invalid: "Расшифровка изменилась. Обновите страницу и попробуйте снова.",
        summary_generation_unavailable: "Новый вариант сейчас недоступен. Текущие итоги сохранены.",
        summary_revision_conflict: "Итоги уже изменились. Обновите страницу."
      }[code] || "Не удалось подготовить новый вариант. Текущие итоги сохранены.");
      const retryCandidateAction = () => activeTemplate
        ? { text: "Повторить", action: () => requestCandidate(activeTemplate), primary: true }
        : { text: "Обновить страницу", action: () => window.location.reload(), primary: true };
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
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.code || "summary_request_failed");
        return payload;
      };
      const resolveCandidate = async (candidate, accept) => {
        setBusy(true);
        try {
          const resolved = await mutate(
            `/api/v1/cabinet/meetings/${meetingId}/summary-candidates/${candidate.candidate_id}/${accept ? "accept" : "reject"}`,
            "POST",
            { expected_current_outcome_set_id: currentOutcomeSetId }
          );
          currentOutcomeSetId = resolved.current_outcome_set_id || currentOutcomeSetId;
          if (accept) window.location.reload();
          else if (status) status.hidden = true;
        } catch (error) {
          showStatus(candidateErrorCopy(error instanceof Error ? error.message : ""), "failed");
        } finally {
          setBusy(false);
        }
      };
      const renderCandidate = (candidate) => {
        if (candidate.state === "generating") {
          window.sessionStorage.setItem(candidateStorageKey, JSON.stringify({
            poll_url: candidate.poll_url,
            template: activeTemplate
          }));
          showStatus("Готовим новый вариант. Текущие итоги остаются на месте.");
          return;
        }
        window.clearTimeout(pollingTimer);
        window.sessionStorage.removeItem(candidateStorageKey);
        pollingTimer = null;
        setBusy(false);
        if (candidate.state === "ready") {
          showStatus("Новый вариант готов. Текущие итоги сохранены.", "ready", [
            { text: "Оставить текущие", action: () => resolveCandidate(candidate, false) },
            { text: "Использовать", action: () => resolveCandidate(candidate, true), primary: true }
          ]);
          return;
        }
        if (candidate.state === "accepted") {
          window.location.reload();
          return;
        }
        showStatus("Не удалось подготовить новый вариант. Текущие итоги сохранены.", "failed", [
          retryCandidateAction()
        ]);
      };
      const pollCandidate = async (candidate) => {
        try {
          const response = await fetch(candidate.poll_url, { credentials: "same-origin", cache: "no-store" });
          if (!response.ok) throw new Error("summary_poll_failed");
          const next = await response.json();
          renderCandidate(next);
          if (next.state === "generating") {
            pollingTimer = window.setTimeout(() => pollCandidate(next), 1200);
          }
        } catch (_error) {
          setBusy(false);
          showStatus("Не удалось обновить новый вариант. Текущие итоги сохранены.", "failed", [
            retryCandidateAction()
          ]);
        }
      };
      const requestCandidate = async (template) => {
        if (!template || !meetingId) return;
        activeTemplate = template;
        setBusy(true);
        showStatus(`Готовим формат «${template.name}». Текущие итоги остаются на месте.`);
        try {
          const candidate = await mutate(
            `/api/v1/cabinet/meetings/${meetingId}/summary-candidates`,
            "POST",
            {
              template_key: template.key,
              template_id: template.id || null,
              template_version: template.version,
              expected_current_outcome_set_id: currentOutcomeSetId
            }
          );
          renderCandidate(candidate);
          if (candidate.state === "generating") {
            pollingTimer = window.setTimeout(() => pollCandidate(candidate), 1200);
          }
        } catch (error) {
          setBusy(false);
          showStatus(candidateErrorCopy(error instanceof Error ? error.message : ""), "failed", [
            { text: "Повторить", action: () => requestCandidate(template), primary: true }
          ]);
        }
      };
      const templateFrom = (option) => ({
        id: option.dataset.templateId || null,
        key: option.dataset.templateKey,
        version: Number(option.dataset.templateVersion || "1"),
        name: option.dataset.templateName || option.textContent.trim()
      });
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
        requestCandidate(templateFrom(option));
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
        requestCandidate(templateFrom(option));
      });
      document.addEventListener("click", (event) => {
        if (!listbox.hidden && event.target instanceof Node && !controls.contains(event.target)) {
          close({ restoreFocus: false });
        }
      });
      const resumeCandidate = window.sessionStorage.getItem(candidateStorageKey);
      if (resumeCandidate) {
        let resumed = { poll_url: resumeCandidate, template: null };
        try {
          const stored = JSON.parse(resumeCandidate);
          if (stored && typeof stored.poll_url === "string") resumed = stored;
        } catch (_error) {
          // A pre-121 URL-only value can still be polled; retry falls back to reload.
        }
        activeTemplate = resumed.template || null;
        setBusy(true);
        showStatus("Проверяем новый вариант. Текущие итоги остаются на месте.");
        pollCandidate({ poll_url: resumed.poll_url });
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
        if (event.target.closest?.('[role="menuitem"]')) closePanel(panel);
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
      const reportPlaybackFailure = () => {
        if (playbackError) playbackError.hidden = false;
        setToggleState(false);
      };
      const play = () => {
        if (playbackError) playbackError.hidden = true;
        return player.play().catch(reportPlaybackFailure);
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
      player.addEventListener("error", reportPlaybackFailure);
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
      });
      document.querySelectorAll("[data-seek-seconds]").forEach((button) => {
        if (button.dataset.seekReady === "true") return;
        button.dataset.seekReady = "true";
        button.addEventListener("click", () => {
          const seekSeconds = Number.parseFloat(button.dataset.seekSeconds || "0");
          if (!Number.isFinite(seekSeconds)) return;
          seekTo(seekSeconds, { autoplay: true });
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

  const refreshMeetingList = async (refreshUrl) => {
    const target = document.querySelector("#meeting-list-region");
    if (!target || !window.htmx?.ajax) return;
    const url = refreshUrl || `${window.location.pathname}${window.location.search}`;
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

    const setValidation = (message = "", tone = "neutral") => {
      if (!validation) return;
      validation.textContent = message;
      validation.dataset.tone = tone;
      validation.hidden = !message;
    };

    const syncReady = () => {
      const duration = Number.parseInt(durationInput?.value || "0", 10);
      const ready = Boolean(selectedFile && Number.isFinite(duration) && duration > 0 && csrfToken);
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
      host.setAttribute("aria-live", "polite");
      const listRegion = document.querySelector("#meeting-list-region");
      const toolbar = document.querySelector(".meeting-toolbar");
      if (listRegion?.parentNode) listRegion.parentNode.insertBefore(host, listRegion);
      else toolbar?.after(host);
      return host;
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
      const percent = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
      activity.progress?.classList.toggle("is-indeterminate", !determinate);
      if (determinate) {
        activity.progress?.setAttribute("aria-valuenow", String(percent));
        if (activity.progressBar) activity.progressBar.style.width = `${percent}%`;
        if (activity.percentLabel) {
          activity.percentLabel.textContent = `${percent}%`;
          activity.percentLabel.hidden = false;
        }
      } else {
        activity.progress?.removeAttribute("aria-valuenow");
        if (activity.progressBar) activity.progressBar.style.width = "36%";
        if (activity.percentLabel) {
          activity.percentLabel.textContent = "…";
          activity.percentLabel.hidden = false;
        }
      }
    };

    const setActivityState = (activity, state, message, tone = "neutral") => {
      activity.state = state;
      activity.row.dataset.uploadActivityState = state;
      if (activity.status) {
        activity.status.textContent = message;
        activity.status.dataset.tone = tone;
      }
      updateActivityControls(activity);
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
          <span class="upload-activity-progress" role="progressbar" aria-label="Прогресс загрузки" aria-valuemin="0" aria-valuemax="100">
            <span data-upload-activity-progress-bar></span>
          </span>
        </div>
        <span class="upload-activity-percent" data-upload-activity-percent>0%</span>
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
      setActivityProgress(activity, 0, true);
      setActivityState(activity, "uploading", continued ? "Продолжаем загрузку…" : "Загружаем файл…");

      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable) {
          setActivityProgress(activity, 0, false);
          return;
        }
        const percent = Math.max(0, Math.min(100, Math.round((event.loaded / event.total) * 100)));
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
          setActivityProgress(activity, 100, true);
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
          await refreshMeetingList(dialog.dataset.uploadRefreshUrl);
          return;
        }
        const failureCode = typeof payload.code === "string" ? payload.code : "";
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

    const closeDialog = () => {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
      focusDialogElement(lastTrigger);
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

  const renderPlaybackTerminalState = (detail) => {
    detail.dataset.playbackPollActive = "false";
    detail.removeAttribute("data-playback-poll-url");
    stopPlaybackRecoveryPolling();
    const terminal = document.createElement("section");
    terminal.className = "playback-terminal-state";
    terminal.dataset.playbackState = "unavailable";
    terminal.setAttribute("role", "status");
    terminal.setAttribute("tabindex", "-1");
    const title = document.createElement("strong");
    title.textContent = "Запись больше недоступна";
    const body = document.createElement("span");
    body.textContent = "Эта страница больше не может показывать запись.";
    terminal.append(title, body);
    detail.replaceChildren(terminal);
    terminal.focus();
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
      if (response.status === 404 || response.status === 410) {
        renderPlaybackTerminalState(detail);
        return;
      }
      if (!response.ok || response.redirected) {
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
        await navigator.clipboard.writeText(await response.text());
        setStatus("Текст скопирован.", "success");
      } catch (error) {
        const code = error instanceof Error ? error.message : "export_failed";
        setStatus(errorMessage(code), "error");
      } finally {
        setBusy(false);
        copy.focus({ preventScroll: true });
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
      const recipientInput = form?.querySelector("[data-share-recipient-input]");
      const meetingId = form?.dataset.meetingId || "";
      const setResultsVisible = (visible) => {
        if (results) results.hidden = !visible;
        recipientInput?.setAttribute("aria-expanded", visible ? "true" : "false");
      };
      const focusResultOption = (current, offset) => {
        const options = Array.from(results?.querySelectorAll('[role="option"]') || []);
        if (!options.length) return;
        const index = options.indexOf(current);
        options[(index + offset + options.length) % options.length].focus({ preventScroll: true });
      };
      const setStatus = (message, tone = "neutral") => {
        if (!status) return;
        status.textContent = message;
        status.dataset.tone = tone;
      };
      const mutate = async (url, options) => {
        const response = await fetch(url, {
          credentials: "same-origin",
          ...options,
          headers: {
            "Content-Type": "application/json",
            ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
            ...(options?.headers || {})
          }
        });
        if (!response.ok) throw new Error(String(response.status));
        return response.status === 204 ? null : response.json();
      };
      const grantRecipient = async (userId, label) => {
        try {
          await mutate(`/api/v1/cabinet/meetings/${meetingId}/shares`, {
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
          setStatus(`Доступ к итогам открыт: ${label}`, "success");
        } catch (_error) {
          setStatus("Не удалось открыть доступ. Попробуйте ещё раз.", "error");
        }
      };
      const close = () => {
        dialog.close();
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
      form?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const query = recipientInput?.value.trim() || "";
        if (query.length < 2) {
          setStatus("Введите имя или email.", "error");
          return;
        }
        setResultsVisible(false);
        setStatus("Ищем…");
        try {
          const response = await fetch(`${form.action}?query=${encodeURIComponent(query)}`, {
            credentials: "same-origin"
          });
          if (!response.ok) throw new Error(String(response.status));
          const payload = await response.json();
          const items = Array.isArray(payload.items) ? payload.items : [];
          if (items.length && results) {
            results.replaceChildren();
            items.forEach((item) => {
              const button = document.createElement("button");
              button.type = "button";
              button.setAttribute("role", "option");
              button.setAttribute("aria-selected", "false");
              button.textContent = item.display_label;
              button.addEventListener("focus", () => {
                results.querySelectorAll('[role="option"]').forEach((option) => {
                  option.setAttribute("aria-selected", option === button ? "true" : "false");
                });
              });
              button.addEventListener("click", () => grantRecipient(item.user_id, item.display_label));
              results.append(button);
            });
            setResultsVisible(true);
            setStatus("Выберите человека.");
            results.querySelector("button")?.focus({ preventScroll: true });
            return;
          }
          if (query.includes("@")) {
            await mutate(`/api/v1/cabinet/meetings/${meetingId}/share-invitations`, {
              method: "POST",
              body: JSON.stringify({
                address: query,
                content_scope: "summary_only",
                can_download: false,
                can_export: false
              })
            });
            setStatus("Приглашение отправлено.", "success");
            return;
          }
          setStatus("Никого не нашли. Проверьте имя.", "error");
        } catch (_error) {
          setStatus("Не удалось пригласить. Попробуйте ещё раз.", "error");
        }
      });
      recipientInput?.addEventListener("keydown", (event) => {
        if (event.key === "ArrowDown" && !results?.hidden) {
          event.preventDefault();
          results.querySelector('[role="option"]')?.focus({ preventScroll: true });
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
          if (event.key === "Home") results.querySelector('[role="option"]')?.focus({ preventScroll: true });
          else if (event.key === "End") results.querySelector('[role="option"]:last-of-type')?.focus({ preventScroll: true });
          else focusResultOption(option, event.key === "ArrowDown" ? 1 : -1);
        } else if (event.key === "Escape") {
          event.preventDefault();
          event.stopPropagation();
          setResultsVisible(false);
          recipientInput?.focus({ preventScroll: true });
        }
      });
      dialog.querySelectorAll("[data-share-revoke-url]").forEach((button) => {
        button.addEventListener("click", async () => {
          try {
            await mutate(button.dataset.shareRevokeUrl, { method: "DELETE" });
            button.closest("[data-share-viewer-row]")?.remove();
            setStatus("Доступ отозван.", "success");
          } catch (_error) {
            setStatus("Не удалось отозвать доступ.", "error");
          }
        });
      });
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
    initManualUpload();
    initDetailTabs();
    initSummaryFormats();
    initSummaryTemplateSettings();
    initMeetingContextPanels();
    initShareDialogs();
    initPlayback();
    initPlaybackRecoveryPolling();
    initSpeakerNameForms();
    initContentExport();
    initMeetingDeleteDialog();
    initCalendarSettings();
  };

  document.body.addEventListener("htmx:afterSwap", (event) => {
    const target = event.detail?.target;
    if (target instanceof Element && (target.id === "meeting-list-region" || target.matches("[data-meeting-list]"))) {
      target.querySelectorAll("[data-meeting-select]").forEach((input) => {
        input.checked = false;
      });
      target.querySelectorAll("[data-meeting-row]").forEach((row) => setRowContextualAvailability(row, false));
      updateSelection();
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
