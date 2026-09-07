(() => {
  const validTimezone = (value) => {
    try { new Intl.DateTimeFormat("ru-RU", { timeZone: value }).format(); return value; }
    catch { return "UTC"; }
  };
  const preferred = document.querySelector('meta[name="graf-time-preferred"]')?.content?.trim() || "";
  let timezone = preferred ? validTimezone(preferred) : Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  const format = (value, { dateOnly = false, timeOnly = false, showZone = false, timeZone = timezone } = {}) => {
    if (value == null || value === "") return "Без даты";
    // Calendar dates have no instant and must never shift across time zones.
    if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
      return value.split("-").reverse().join(".");
    }
    const normalized = typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(value)
      ? `${value}Z` : value;
    const instant = new Date(normalized);
    if (!Number.isFinite(instant.getTime())) return "Без даты";
    const zone = validTimezone(timeZone);
    const parts = Object.fromEntries(new Intl.DateTimeFormat("ru-RU", {
      timeZone: zone, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    }).formatToParts(instant).map(({ type, value: part }) => [type, part]));
    const day = `${parts.day}.${parts.month}.${parts.year}`;
    const time = `${parts.hour}:${parts.minute}`;
    const label = dateOnly ? day : timeOnly ? time : `${day}, ${time}`;
    if (!showZone && zone !== "UTC") return label;
    const offset = new Intl.DateTimeFormat("en-US", { timeZone: zone, timeZoneName: "longOffset" })
      .formatToParts(instant).find(part => part.type === "timeZoneName").value.replace("GMT", "UTC").replace(/^UTC[+-]00:00$/, "UTC");
    return `${label} (${offset})`;
  };
  const formatDuration = (value) => {
    const total = Math.max(0, Math.floor(Number(value) || 0));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor(total / 60) % 60;
    if (hours) return `${hours} ч${minutes ? ` ${minutes} мин` : ""}`;
    return minutes ? `${minutes} мин` : `${total} с`;
  };
  window.GRAFTime = { timezone, format, formatDuration };
  const hydrate = () => {
    document.querySelectorAll("[data-user-datetime]").forEach((element) => {
      const value = element.getAttribute("datetime");
      element.textContent = format(value, { showZone: element.dataset.showZone === "true" });
      element.title = format(value, { showZone: true });
    });
    document.querySelectorAll("[data-user-timezone]").forEach((element) => {
      element.textContent = timezone;
    });
  };
  document.addEventListener("DOMContentLoaded", hydrate);
  document.addEventListener("htmx:afterSwap", hydrate);
  window.addEventListener("pageshow", hydrate);

  if (preferred) {
    // An account selection owns presentation; device cookies must never replace it.
    try { sessionStorage.removeItem("graf-time-reload"); } catch { /* Storage is optional. */ }
    return;
  }
  const serverZone = document.querySelector('meta[name="graf-timezone"]')?.content;
  const reloadAllowed = document.querySelector('meta[name="graf-time-reload"]')?.content === "true";
  const cookie = `graf_timezone=${timezone}`;
  if (serverZone !== timezone) {
    let saved = false;
    try {
      document.cookie = `${cookie}; Path=/; SameSite=Lax; Max-Age=31536000${location.protocol === "https:" ? "; Secure" : ""}`;
      saved = document.cookie.split(";").some((part) => part.trim() === cookie);
    } catch { /* Cookie access can be disabled in an embedded browser. */ }
    if (!saved) {
      // Search and generated titles stay in the server zone when it cannot receive ours.
      timezone = serverZone || "UTC";
      window.GRAFTime.timezone = timezone;
    }
    // Do not replay POST, auth callbacks or actions; server explicitly permits read-only pages.
    if (saved && reloadAllowed) {
      try {
        const key = "graf-time-reload";
        const target = `${location.href}|${timezone}`;
        if (sessionStorage.getItem(key) !== target) {
          sessionStorage.setItem(key, target);
          location.replace(location.href);
        } else {
          timezone = serverZone || "UTC";
          window.GRAFTime.timezone = timezone;
        }
      } catch {
        // Blocked browser storage: keep the same zone as server search and titles.
        timezone = serverZone || "UTC";
        window.GRAFTime.timezone = timezone;
      }
    }
  } else {
    try { sessionStorage.removeItem("graf-time-reload"); } catch { /* Storage is optional. */ }
  }
})();
