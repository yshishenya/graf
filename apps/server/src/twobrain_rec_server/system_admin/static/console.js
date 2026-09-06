"use strict";
let csrf, leaving=false;
const pageMessage=document.getElementById("message");
async function command(path, data = {}, method = "POST", extraHeaders = {}) {
  if (!csrf && method !== "GET") csrf = (await (await fetch("/api/system-admin/v1/auth/csrf", {cache:"no-store"})).json()).csrf_token;
  const response = await fetch(`/api/system-admin/v1/${path}`, {method,cache:"no-store",
    headers:{"Content-Type":"application/json",...extraHeaders,...(csrf ? {"X-CSRF-Token":csrf} : {})},
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

const operationDialog=document.getElementById("operation-dialog"), operationForm=document.getElementById("operation-preview-form");
const operationConfirm=document.getElementById("operation-confirm"), operationSubmit=document.getElementById("operation-submit");
const operationEffects=document.getElementById("operation-effects"), operationRefresh=document.getElementById("operation-refresh");
const operationStates={queued:"В очереди",running:"Выполняется",awaiting_reconciliation:"Ожидает проверки результата",succeeded:"Выполнено",failed:"Не выполнено",cancelled:"Отменено",partially_succeeded:"Выполнено частично"};
let operationState=null;
document.querySelectorAll(".meeting-command").forEach(button=>button.addEventListener("click",()=>{
  operationForm.reset();operationEffects.replaceChildren();operationConfirm.hidden=true;operationRefresh.hidden=true;
  operationForm.hidden=false;operationSubmit.disabled=false;document.getElementById("operation-ack").checked=false;
  operationState={kind:button.dataset.kind,target:button.dataset.id,version:Number(button.dataset.version)};
  document.getElementById("operation-title").textContent=button.textContent;
  document.getElementById("operation-target").textContent=`Встреча ${operationState.target}`;
  operationDialog.querySelector(".dialog-message").textContent="";operationDialog.showModal();
}));
operationForm.addEventListener("input",()=>{if(operationState&&!operationState.sent) {operationState.preview=null;operationConfirm.hidden=true;}});
operationForm.addEventListener("submit",async event=>{
  event.preventDefault();const state=operationState, button=operationForm.querySelector("button[type=submit]");button.disabled=true;
  operationForm.elements.reason.readOnly=true;
  try {
    const preview=await command("previews",{command:state.kind,targets:[{type:"meeting",id:state.target,expected_version:state.version}],parameters:{},reason:operationForm.elements.reason.value});
    if(operationState!==state||!operationDialog.open) return;
    state.preview=preview;state.key=crypto.randomUUID();operationEffects.replaceChildren();
    for(const line of [`Причина: ${preview.command.reason}`,...preview.effects,...preview.warnings,`Предпросмотр действует до ${new Date(preview.expires_at).toLocaleString()}`]) {
      const paragraph=document.createElement("p");paragraph.textContent=line;operationEffects.append(paragraph);
    }
    document.getElementById("operation-ack").checked=false;operationConfirm.hidden=false;
    operationDialog.querySelector(".dialog-message").textContent="";
  }catch(error) {operationDialog.querySelector(".dialog-message").textContent=error.message;}
  finally {button.disabled=false;operationForm.elements.reason.readOnly=false;}
});
async function refreshOperation() {
  const state=operationState;if(!state?.id) return;
  try {
    const result=await command(`operations/${state.id}`,{},"GET");
    if(operationState!==state||!operationDialog.open) return;
    operationDialog.querySelector(".dialog-message").textContent=`Операция ${state.id}: ${operationStates[result.state]||result.state}.`;
    const failureReasons={source_unavailable:"Исходная запись недоступна",source_expired:"Срок хранения исходника истёк",quota_exceeded:"Недостаточно квоты",not_terminal:"Текущую попытку нельзя перезапустить",not_eligible:"Нет завершённого результата для повторной обработки",unknown_outcome:"Результат отправки провайдеру ещё не подтверждён",already_in_flight:"Обработка уже выполняется",configuration_failure:"Нужно проверить настройки обработки",version_conflict:"Встреча изменилась",authority_revoked:"Полномочия отозваны",processing_failed:"Обработка завершилась ошибкой",deletion_failed:"Удаление требует разбора",meeting_not_found:"Встреча не найдена",deletion_closed:"Встреча удаляется или удалена",stale_meeting_view:"Состояние обработки изменилось"};
    for(const target of result.targets||[]) if(target.error_code) operationDialog.querySelector(".dialog-message").textContent+=` ${failureReasons[target.error_code]||"Нужна проверка состояния встречи"}.`;
    operationRefresh.hidden=["succeeded","failed","cancelled","partially_succeeded"].includes(result.state);
  }catch(error) {operationDialog.querySelector(".dialog-message").textContent=error.message;}
}
operationSubmit.addEventListener("click",async()=>{
  const state=operationState;
  if(!state?.preview||!document.getElementById("operation-ack").checked) {
    operationDialog.querySelector(".dialog-message").textContent="Проверьте последствия и отметьте подтверждение.";return;
  }
  operationSubmit.disabled=true;state.sent=true;operationForm.hidden=true;
  try {
    const result=await command("operations",{preview_id:state.preview.preview_id,expected_preview_hash:state.preview.effect_hash},"POST",{"Idempotency-Key":state.key});
    if(operationState!==state) return;
    state.id=result.operation_id;operationConfirm.hidden=true;operationRefresh.hidden=false;await refreshOperation();
  }catch(error) {
    // Keep the same preview/key after a lost response: a retry observes the
    // original command, even if the preview has since expired.
    operationSubmit.disabled=false;operationDialog.querySelector(".dialog-message").textContent=error.message;
  }
});
operationRefresh.addEventListener("click",refreshOperation);
setInterval(()=>{if(!document.hidden&&operationDialog.open&&!operationRefresh.hidden) refreshOperation();},5000);

const overviewDialog=document.getElementById("overview-dialog");
let overviewState=null;
const diagnosticLabels={id:"Идентификатор",workspace_id:"Пространство",created_by_user_id:"Владелец",device_id:"Устройство",status:"Состояние",processing_status:"Обработка",duration_seconds:"Длительность, секунд",created_at:"Создано",started_at:"Начало",ended_at:"Завершение",deletion_state:"Удаление",deletion_epoch:"Версия удаления",version:"Версия состояния",observed_at:"Получено",source:"Источник",request_id:"Запрос удаления",reason_code:"Причина",accepted_at:"Принято",completed_at:"Завершено",system_operation_id:"Административная операция",state:"Состояние",backup_state:"Резервные копии",local_purge_state:"Локальные копии",external_dependency_state:"Внешние системы",generated_at:"Отчёт создан",updated_at:"Обновлено",revision_number:"Версия исходника",source_kind:"Тип источника",immutable:"Исходник зафиксирован",media_revision_id:"Исходник",workflow_id:"Процесс Temporal",workflow_run_id:"Запуск Temporal",stage:"Этап",retry_class:"Тип повтора",retry_count:"Повторов",last_reason_code:"Последняя причина",attempt_ordinal:"Попытка",next_attempt_at:"Следующий повтор",deadline_at:"Предельный срок"};
const diagnosticStates={graf_database:"База GRAF",processed:"Обработано",failed_terminal:"Завершено с ошибкой",blocked:"Заблокировано",blocked_unknown:"Отправка требует сверки",not_submitted:"Не отправлено",starting:"Подготовка",workflow_started:"Запуск процесса",submitting:"Отправка",submitted:"Отправлено",polling:"Ожидание результата",importing:"Сохранение результата",waiting_retry:"Ожидание повтора",failed_retryable:"Временная ошибка",canceled:"Отменено",none:"Не запрошено",deleting:"Удаляется",complete:"Завершено",pending_expiry:"Ожидает истечения срока",pending_backup_expiry:"Ожидает удаления резервных копий",not_applicable:"Не применяется",unknown:"Нет подтверждения",local_pending:"Ожидает устройство",accepted:"Принято",ready:"Готово",admin:"Администратор"};
function diagnosticFields(row) {
  const list=document.createElement("dl");
  for(const [key,value] of Object.entries(row)) {
    if(key==="deletion"||key==="report") continue;
    const term=document.createElement("dt"),description=document.createElement("dd");term.textContent=diagnosticLabels[key]||key;
    description.textContent=value===null?"Нет данных":typeof value==="boolean"?(value?"Да":"Нет"):key.endsWith("_at")?new Date(value).toLocaleString():diagnosticStates[value]||String(value);
    list.append(term,description);
  }
  return list;
}
async function loadOverviewHistory(kind,append=false) {
  const state=overviewState,container=document.getElementById(`overview-${kind}`),button=document.getElementById(`${kind}-more`);
  button.disabled=true;
  try {
    const cursor=append?state[kind]:null;
    const result=await command(`meetings/${state.id}/${kind}${cursor!==null?`?before=${encodeURIComponent(cursor)}`:""}`,{},"GET");
    if(overviewState!==state||!overviewDialog.open) return;
    if(!append) container.replaceChildren();
    for(const row of result.items) container.append(diagnosticFields(row));
    if(!append&&!result.items.length) container.textContent="Сохранённой истории нет.";
    state[kind]=result.next_cursor;button.hidden=result.next_cursor===null;
  }catch(error) {if(overviewState===state) {container.textContent=error.message;button.hidden=true;}}
  finally {button.disabled=false;}
}
document.querySelectorAll(".open-overview").forEach(button=>button.addEventListener("click",async()=>{
  overviewState={id:button.dataset.id,revisions:null,processing:null};const state=overviewState;
  document.getElementById("overview-fields").replaceChildren();document.getElementById("overview-revisions").replaceChildren();document.getElementById("overview-processing").replaceChildren();
  document.getElementById("revisions-more").hidden=true;document.getElementById("processing-more").hidden=true;
  overviewDialog.querySelector(".dialog-message").textContent="Загрузка…";overviewDialog.showModal();
  try {
    const row=await command(`meetings/${state.id}`,{},"GET");
    if(overviewState!==state||!overviewDialog.open) return;
    const fields=document.getElementById("overview-fields");fields.append(diagnosticFields(row));
    if(row.deletion) {const heading=document.createElement("h3");heading.textContent="Отчёт удаления";fields.append(heading,diagnosticFields(row.deletion));if(row.deletion.report) fields.append(diagnosticFields(row.deletion.report));}
    overviewDialog.querySelector(".dialog-message").textContent="Метаданные без содержимого встречи. Время показано в вашем часовом поясе.";
    await Promise.allSettled([loadOverviewHistory("revisions"),loadOverviewHistory("processing")]);
  }catch(error) {overviewDialog.querySelector(".dialog-message").textContent=error.message;}
}));
for(const kind of ["revisions","processing"]) document.getElementById(`${kind}-more`).addEventListener("click",()=>loadOverviewHistory(kind,true));
overviewDialog.addEventListener("close",()=>{overviewState=null;});
