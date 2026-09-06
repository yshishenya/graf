"use strict";
let challenge = location.hash.slice(1);
if (challenge) history.replaceState(null, "", location.pathname);
let csrf;
const message = document.getElementById("message");
const panels = ["password-form", "mfa-form", "recovery-form", "enrolment-form", "seed-panel", "recovery-codes", "reset-request-form", "reset-complete-form"];
function show(id) {
  panels.forEach(name => { document.getElementById(name).hidden = name !== id; });
  document.getElementById(id).querySelector("input,button,a")?.focus();
}
async function submit(path, payload) {
  if (!csrf) {
    const response = await fetch("/api/system-admin/v1/auth/csrf", {cache: "no-store"});
    if (!response.ok) throw new Error("Сервис входа недоступен");
    csrf = (await response.json()).csrf_token;
  }
  const response = await fetch(`/api/system-admin/v1/auth/${path}`, {
    method: "POST", headers: {"Content-Type": "application/json", "X-CSRF-Token": csrf},
    body: JSON.stringify(payload), cache: "no-store"
  });
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Не удалось выполнить запрос. Попробуйте снова.");
  return result;
}
function form(id, action) {
  const element = document.getElementById(id);
  element.addEventListener("submit", async event => {
    event.preventDefault();
    const button = element.querySelector("button[type=submit]");
    button.disabled = true; message.textContent = "Проверяем…";
    try { const result = await action(Object.fromEntries(new FormData(element))); message.textContent = result || ""; }
    catch (error) { message.textContent = error.message; }
    finally { button.disabled = false; }
  });
}
form("password-form", async payload => {
  const result = await submit("login", payload);
  challenge = result.challenge;
  document.getElementById("password").value = "";
  show("mfa-form");
});
form("mfa-form", async payload => {
  await submit("mfa", {...payload, challenge});
  location.replace("/system-admin");
});
form("recovery-form", async payload => {
  const result = await submit("mfa", {...payload, challenge});
  challenge = result.challenge;
  document.getElementById("recovery").value = "";
  document.getElementById("new-password").disabled = true;
  show("enrolment-form");
});
form("enrolment-form", async payload => {
  const result = await submit("enrolment/begin", {...payload, challenge});
  challenge = result.challenge;
  document.getElementById("new-password").value = "";
  document.getElementById("seed").textContent = result.seed;
  show("seed-panel");
});
form("confirm-form", async payload => {
  const result = await submit("enrolment/confirm", {...payload, challenge});
  document.getElementById("seed").textContent = "";
  document.getElementById("codes").textContent = result.recovery_codes.join("\n");
  challenge = "";
  show("recovery-codes");
});
document.getElementById("use-recovery").addEventListener("click", () => show("recovery-form"));
document.getElementById("forgot-password").addEventListener("click", () => show("reset-request-form"));
form("reset-request-form", async payload => {
  const result = await submit("password-reset/request", payload);
  show("password-form");
  return result.message;
});
form("reset-complete-form", async payload => {
  const result = await submit("password-reset/complete", {...payload,token:challenge});
  challenge="";document.getElementById("reset-password").value="";
  show("password-form");
  return result.message;
});
show(challenge ? (location.pathname.endsWith("/reset") ? "reset-complete-form" : "enrolment-form") : "password-form");
addEventListener("pageshow", event => { if (event.persisted) location.reload(); });
