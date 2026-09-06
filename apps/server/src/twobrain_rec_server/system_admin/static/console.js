"use strict";
let csrf, leaving=false;
const pageMessage=document.getElementById("message");
async function command(path, data = {}, method = "POST") {
  if (!csrf && method !== "GET") csrf = (await (await fetch("/api/system-admin/v1/auth/csrf", {cache:"no-store"})).json()).csrf_token;
  const response = await fetch(`/api/system-admin/v1/${path}`, {method,cache:"no-store",
    headers:{"Content-Type":"application/json",...(csrf ? {"X-CSRF-Token":csrf} : {})},
    ...(method === "GET" ? {} : {body:JSON.stringify(data)})});
  if (response.status === 401) { leaving=true; document.querySelector("main")?.replaceChildren(); location.replace("/system-admin/login"); throw new Error("Сессия завершена"); }
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Не удалось выполнить действие");
  return result;
}
const deliveryLabels={submitted:"Письмо принято почтовым сервисом. Доставка ещё не подтверждена.",
  unknown:"Результат отправки неизвестен. Можно повторить приглашение через минуту.",
  failed:"Почтовый сервис отклонил отправку. Можно повторить приглашение через минуту."};
document.getElementById("logout").addEventListener("click", async () => {
  try { await command("auth/logout"); location.replace("/system-admin/login"); }
  catch(error) { pageMessage.textContent=error.message; }
});
const dialog=document.getElementById("admin-dialog"), form=document.getElementById("admin-form");
function openAdmin(mode, button) {
  form.reset(); form.elements.mode.value=mode; delete dialog.dataset.changed;
  form.querySelector("button[type=submit]").disabled=false;
  document.getElementById("invite-fields").hidden=mode!=="invite";
  form.elements.email.required=mode==="invite";
  document.getElementById("assignment-fields").hidden=mode==="resend";
  document.getElementById("status-field").hidden=mode!=="edit";
  document.getElementById("admin-dialog-title").textContent={invite:"Пригласить администратора",edit:"Изменить доступ администратора",resend:"Повторить приглашение"}[mode];
  if (button) {
    ["id","version","role","status"].forEach(key=>{if(button.dataset[key]) form.elements[key].value=button.dataset[key];});
    if(button.dataset.expiry) {
      const expiry=new Date(button.dataset.expiry);
      form.elements.expires_at.value=new Date(expiry.getTime()-expiry.getTimezoneOffset()*60000).toISOString().slice(0,16);
    }
  } else form.elements.role.value="support";
  dialog.querySelector(".dialog-message").textContent=""; dialog.showModal();
}
document.querySelectorAll(".edit-admin").forEach(button=>button.addEventListener("click",()=>openAdmin("edit",button)));
document.querySelectorAll(".resend-admin").forEach(button=>button.addEventListener("click",()=>openAdmin("resend",button)));
document.getElementById("invite-admin")?.addEventListener("click",()=>openAdmin("invite"));
document.querySelectorAll("[data-close-dialog]").forEach(button=>button.addEventListener("click",()=>button.closest("dialog").close()));
dialog.addEventListener("close",()=>{if(dialog.dataset.changed) location.reload();});
form.addEventListener("submit",async event=>{
  event.preventDefault(); const values=Object.fromEntries(new FormData(form));
  const button=form.querySelector("button[type=submit]"); button.disabled=true;
  try {
    let result;
    const assignment={role:values.role,expires_at:values.expires_at?new Date(values.expires_at).toISOString():null,reason:values.reason};
    if(values.mode==="invite") result=await command("admins",{...assignment,email:values.email});
    else if(values.mode==="resend") result=await command(`admins/${values.id}/resend-invitation`,{version:Number(values.version),reason:values.reason});
    else result=await command(`admins/${values.id}`,{...assignment,version:Number(values.version),status:values.status},"PATCH");
    dialog.dataset.changed="true";
    dialog.querySelector(".dialog-message").textContent=deliveryLabels[result.delivery_state] || "Доступ изменён. Закройте окно, чтобы обновить таблицу.";
  } catch(error) {dialog.querySelector(".dialog-message").textContent=error.message;button.disabled=false;}
});
const grantDialog=document.getElementById("grants-dialog"), grantForm=document.getElementById("grant-form");
const grantOptions={
  "content.read":["Читать содержимое",["meeting"]],"audio.listen":["Слушать запись",["meeting"]],
  "audio.download":["Скачивать запись",["meeting"]],"content.export":["Выгружать содержимое",["meeting"]],
  "diagnostics.content":["Читать сохранённую диагностику",["meeting"]],
  "billing.manage":["Управлять подпиской",["user","workspace","subscription","invoice"]],
  "catalog.publish":["Публиковать тариф",["plan_version"]],
  "promotions.manage":["Управлять акцией",["campaign"]],"promotions.publish":["Публиковать акцию",["campaign"]]};
const targetLabels={meeting:"Встреча",user:"Пользователь",workspace:"Пространство",subscription:"Подписка (ID пространства)",invoice:"Счёт",plan_version:"Версия тарифа",campaign:"Акция"};
function grantTypes() {
  grantForm.elements.target_type.replaceChildren(...(grantOptions[grantForm.elements.permission.value]?.[1]||[]).map(key=>new Option(targetLabels[key],key)));
}
grantForm.elements.permission.addEventListener("change",grantTypes);
async function loadGrants() {
  const result=await command(`admins/${grantForm.elements.principal_id.value}/grants`,{},"GET");
  const list=document.getElementById("grants-list"); list.replaceChildren();
  if(!result.items.length) list.textContent="Временных назначений нет.";
  for(const grant of result.items) {
    const row=document.createElement("p");
    const expired=new Date(grant.expires_at)<=new Date();
    row.textContent=`${grantOptions[grant.permission]?.[0]||grant.permission} · ${targetLabels[grant.target_type]||grant.target_type} ${grant.target_id} · до ${new Date(grant.expires_at).toLocaleString()} · ${grant.revoked_at?"Отозвано":expired?"Срок истёк":"Действует"}`;
    if(!grant.revoked_at&&!expired) {
      const revoke=document.createElement("button");revoke.type="button";revoke.className="secondary";revoke.textContent="Отозвать";
      revoke.addEventListener("click",async()=>{
        if(!grantForm.elements.reason.reportValidity()) return;
        revoke.disabled=true;
        try {await command(`grants/${grant.id}`,{version:grant.version,reason:grantForm.elements.reason.value},"DELETE");await loadGrants();}
        catch(error) {grantDialog.querySelector(".dialog-message").textContent=error.message;revoke.disabled=false;}
      });row.append(" ",revoke);
    }
    list.append(row);
  }
}
document.querySelectorAll(".grants-admin").forEach(button=>button.addEventListener("click",async()=>{
  grantForm.reset();grantForm.elements.principal_id.value=button.dataset.id;grantForm.elements.version.value=button.dataset.version;
  document.getElementById("grants-recipient").textContent=button.dataset.email;
  grantDialog.querySelector(".dialog-message").textContent="";
  const allowed=button.dataset.role==="billing_manager"?Object.keys(grantOptions).slice(5):["support","system_admin"].includes(button.dataset.role)?Object.keys(grantOptions).slice(0,5):[];
  grantForm.elements.permission.replaceChildren(...allowed.map(key=>new Option(grantOptions[key][0],key)));grantTypes();
  grantForm.querySelector("button[type=submit]").disabled=!allowed.length;
  grantDialog.showModal();
  try {await loadGrants();} catch(error) {grantDialog.querySelector(".dialog-message").textContent=error.message;}
}));
grantForm.addEventListener("submit",async event=>{
  event.preventDefault(); const values=Object.fromEntries(new FormData(grantForm));
  const button=grantForm.querySelector("button[type=submit]");button.disabled=true;
  try {await command("grants",{...values,version:Number(values.version),expires_at:new Date(values.expires_at).toISOString()});
    grantDialog.querySelector(".dialog-message").textContent="Временное право выдано.";await loadGrants();}
  catch(error) {grantDialog.querySelector(".dialog-message").textContent=error.message;}
  finally {button.disabled=false;}
});
document.querySelectorAll("[data-step-up]").forEach(button=>button.addEventListener("click",async()=>{
  const input=document.getElementById(button.dataset.stepUp),message=button.closest("dialog").querySelector(".dialog-message");button.disabled=true;
  try {await command("auth/step-up",{code:input.value});input.value="";message.textContent="Полномочия подтверждены на 5 минут";}
  catch(error) {message.textContent=error.message;} finally {button.disabled=false;}
}));
let lastActivity=0;
for(const name of ["pointerdown","keydown"]) addEventListener(name,()=>{
  if(Date.now()-lastActivity>30000) {lastActivity=Date.now();command("auth/activity").catch(()=>{});}
});
setInterval(async()=>{
  if(document.hidden) return;
  try {await command("me",{},"GET");}
  catch(error) {pageMessage.textContent="Нет связи с сервером. Показанные данные могут устареть.";}
},10000);
addEventListener("pageshow",event=>{if(event.persisted) location.reload();});

const contentDialog=document.getElementById("content-dialog"),caseForm=document.getElementById("content-case-form"),contentText=document.getElementById("content-text");
let contentState=null;
function clearContent() {
  if(leaving) return;
  if(contentState) contentState.request=(contentState.request||0)+1;
  contentText.replaceChildren();document.getElementById("content-controls").hidden=true;
  document.getElementById("content-more").hidden=true;document.getElementById("content-title").textContent="Расшифровка встречи";
}
contentDialog.addEventListener("close",()=>{contentState=null;clearContent();});
document.querySelectorAll(".open-content").forEach(button=>button.addEventListener("click",()=>{
  clearContent();caseForm.reset();caseForm.hidden=false;document.getElementById("content-search-form").reset();
  document.getElementById("content-meeting-id").textContent=button.dataset.id;
  contentState={id:button.dataset.id,caseId:null,resultId:null,after:-1,search:null};
  contentDialog.querySelector(".dialog-message").textContent="";contentDialog.showModal();
}));
async function loadContent(append=false) {
  const state=contentState;
  const request=state.request=(state.request||0)+1;
  const result=await command(`meetings/${state.id}/content`,{case_context_id:state.caseId,
    result_id:state.resultId,after:append?state.after:-1,search:state.search});
  if(contentState!==state||state.request!==request||!contentDialog.open||document.hidden) return;
  if(!append) contentText.replaceChildren();
  state.resultId=result.result_id;state.after=result.next_cursor;
  document.getElementById("content-title").textContent=result.meeting.title||"Встреча без названия";
  document.getElementById("content-controls").hidden=result.state!=="available";
  document.getElementById("content-more").hidden=result.next_cursor===null;
  contentDialog.querySelector(".dialog-message").textContent=result.state==="available"?`Версия результата: ${result.result_version}`:"Полной расшифровки пока нет. Проверьте состояние обработки.";
  for(const segment of result.items) {
    const row=document.createElement("p"),label=document.createElement("strong");
    const seconds=Math.floor(Number(segment.start_seconds));
    label.textContent=`${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,"0")} · ${segment.speaker_label} `;
    row.append(label,document.createTextNode(segment.text));contentText.append(row);
  }
  if(!result.items.length&&result.state==="available") contentText.textContent="По выбранным условиям фрагментов нет.";
}
caseForm.addEventListener("submit",async event=>{
  event.preventDefault();const button=caseForm.querySelector("button");button.disabled=true;
  try {const state=contentState;const result=await command(`meetings/${state.id}/case`,{reason:caseForm.elements.reason.value});
    if(contentState!==state) return;state.caseId=result.case_context_id;await loadContent();caseForm.hidden=true;}
  catch(error) {clearContent();contentDialog.querySelector(".dialog-message").textContent=error.message;}
  finally {button.disabled=false;}
});
document.getElementById("content-search-form").addEventListener("submit",async event=>{
  event.preventDefault();contentState.search=document.getElementById("content-search").value||null;
  try {await loadContent();}catch(error) {clearContent();contentDialog.querySelector(".dialog-message").textContent=error.message;}
});
document.getElementById("content-more").addEventListener("click",async event=>{
  event.target.disabled=true;try {await loadContent(true);}catch(error) {clearContent();contentDialog.querySelector(".dialog-message").textContent=error.message;}
  finally {event.target.disabled=false;}
});
async function recheckContent() {
  if(!contentDialog.open||!contentState?.caseId) return;
  const state=contentState;
  try {await command(`meetings/${state.id}/content/access`,{case_context_id:state.caseId});}
  catch(error) {if(contentState===state) {clearContent();contentDialog.querySelector(".dialog-message").textContent="Просмотр закрыт: доступ отозван, встреча удаляется или нет связи с сервером.";}}
}
setInterval(()=>{if(!document.hidden) recheckContent();},10000);
document.addEventListener("visibilitychange",()=>{
  if(document.hidden) clearContent();else if(contentDialog.open&&contentState?.caseId) {
    // Hidden content is discarded; resuming always obtains a fresh audited read.
    loadContent().catch(error=>{clearContent();contentDialog.querySelector(".dialog-message").textContent=error.message;});
  }
});

document.querySelectorAll("time[datetime]").forEach(element=>{
  const date=new Date(element.dateTime);
  if(!Number.isNaN(date.getTime())) {element.textContent=date.toLocaleString();element.title=`${element.dateTime} (источник)`;}
});
