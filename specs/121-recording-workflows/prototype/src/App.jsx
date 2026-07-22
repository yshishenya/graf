import React, { useEffect, useRef, useState } from "react";
import {
  ArrowClockwise,
  ArrowCounterClockwise,
  ArrowLeft,
  CaretDown,
  Check,
  Circle,
  CloudSlash,
  DotsThree,
  DownloadSimple,
  Gear,
  Link,
  LockSimple,
  MagnifyingGlass,
  Microphone,
  Pause,
  Play,
  ShareNetwork,
  SpeakerHigh,
  Stop,
  Trash,
  UserPlus,
  UsersThree,
  WarningCircle,
  X,
} from "@phosphor-icons/react";

const meetings = [
  { title: "Еженедельная встреча команды", date: "Сегодня, 10:00", duration: "45 мин", status: "Готово" },
  { title: "Синхронизация по продукту", date: "Вчера, 16:30", duration: "32 мин", status: "Готово" },
  { title: "Интервью с пользователем", date: "18 июля, 12:00", duration: "54 мин", status: "Готово" },
];

const scenarios = [
  ["ready", "Готово к записи"],
  ["permission", "Нужно разрешение"],
  ["detected", "Встреча обнаружена"],
  ["active", "Идёт запись"],
  ["paused", "Запись на паузе"],
  ["degraded", "Один источник недоступен"],
  ["offline", "Сохранено локально"],
  ["partial", "Частичная обработка"],
  ["summary", "Итоги готовы"],
  ["candidate", "Новый формат готов"],
  ["share", "Доступ и отзыв"],
  ["deleted", "Запись удалена"],
];

function Modal({ title, children, onClose, wide = false }) {
  const closeRef = useRef(null);
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className={`modal-card ${wide ? "wide" : ""}`} role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <header className="modal-header">
          <h2 id="modal-title">{title}</h2>
          <button ref={closeRef} className="icon-button quiet" aria-label="Закрыть" onClick={onClose}><X size={22} /></button>
        </header>
        {children}
      </section>
    </div>
  );
}

function Sidebar({ view, setView, openScenarios }) {
  const nav = [
    ["meetings", "Встречи", UsersThree],
    ["search", "Поиск", MagnifyingGlass],
    ["settings", "Настройки", Gear],
  ];

  return (
    <aside className="sidebar">
      <button className="brand" onClick={() => setView("summary")} aria-label="GRAF, открыть последнюю встречу">
        <img src="/graf-icon.png" alt="" />
        <span>GRAF</span>
      </button>
      <nav aria-label="Основная навигация">
        {nav.map(([key, label, Icon]) => (
          <button key={key} className={view === key ? "active" : ""} onClick={() => setView(key)}>
            <Icon size={24} weight="regular" />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <button className="profile-button" aria-label="Профиль пользователя и состояния прототипа" onClick={openScenarios}>
          <span className="avatar">АВ</span><CaretDown size={14} />
        </button>
      </div>
    </aside>
  );
}

function Player({ openScenarios }) {
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(28);
  return (
    <footer className="player" aria-label="Проигрыватель записи">
      <button className="player-spacer" onClick={openScenarios}>GRAF&nbsp; v1.3.0</button>
      <div className="transport">
        <button className="player-button" aria-label={playing ? "Пауза" : "Воспроизвести"} onClick={() => setPlaying(!playing)}>
          {playing ? <Pause size={22} weight="fill" /> : <Play size={22} weight="fill" />}
        </button>
        <button className="icon-button" aria-label="Назад на 10 секунд"><ArrowCounterClockwise size={23} /></button>
        <button className="icon-button" aria-label="Вперёд на 10 секунд"><ArrowClockwise size={23} /></button>
      </div>
      <span className="time">12:48</span>
      <input aria-label="Позиция воспроизведения" className="timeline" type="range" min="0" max="100" value={progress} onChange={(e) => setProgress(e.target.value)} />
      <span className="time total">45:12</span>
      <button className="icon-button" aria-label="Громкость"><SpeakerHigh size={23} /></button>
      <button className="speed" aria-label="Скорость воспроизведения">1× <CaretDown size={13} /></button>
    </footer>
  );
}

function SummaryContent({ tab, setTab, openShare, openMore, candidate, setCandidate }) {
  const [formatOpen, setFormatOpen] = useState(false);
  const [acceptedFormat, setAcceptedFormat] = useState("Авто");
  const formats = ["Авто", "Конспект", "Протокол встречи", "Синхронизация проекта"];

  const chooseFormat = (format) => {
    setFormatOpen(false);
    if (format !== acceptedFormat) setCandidate({ name: format });
  };

  return (
    <main className="meeting-shell">
      <header className="meeting-header">
        <div>
          <h1>Еженедельная встреча команды</h1>
          <div className="meeting-meta">21 июля 2026 г., 10:00 <span>•</span> 45 мин <span className="ready-pill">Готово</span></div>
        </div>
        <div className="header-actions">
          <button className="secondary-button" onClick={openShare}><ShareNetwork size={22} /> Поделиться</button>
          <button className="icon-button framed" aria-label="Другие действия" onClick={openMore}><DotsThree size={26} weight="bold" /></button>
        </div>
      </header>

      <div className="tabs" role="tablist" aria-label="Содержимое встречи">
        <button role="tab" aria-selected={tab === "summary"} className={tab === "summary" ? "active" : ""} onClick={() => setTab("summary")}>Итоги</button>
        <button role="tab" aria-selected={tab === "transcript"} className={tab === "transcript" ? "active" : ""} onClick={() => setTab("transcript")}>Расшифровка</button>
      </div>

      {tab === "summary" ? (
        <section className="content-panel">
          <div className="content-heading">
            <h2>Итоги</h2>
            <div className="format-wrap">
              <button className="format-button" aria-expanded={formatOpen} onClick={() => setFormatOpen(!formatOpen)}>Формат: {acceptedFormat} <CaretDown size={14} /></button>
              {formatOpen && (
                <div className="format-menu">
                  {formats.map((format) => <button key={format} onClick={() => chooseFormat(format)}>{format}<span>{format === acceptedFormat && <Check size={17} />}</span></button>)}
                  <button className="all-formats" onClick={() => chooseFormat("Еженедельная встреча")}>Все форматы</button>
                </div>
              )}
            </div>
          </div>

          {candidate && (
            <div className="candidate-banner">
              <div><Check size={20} /><span><strong>{candidate.name}</strong> готов. Текущие итоги сохранены.</span></div>
              <div><button className="text-button" onClick={() => setCandidate(null)}>Оставить текущие</button><button className="primary-small" onClick={() => { setAcceptedFormat(candidate.name); setCandidate(null); }}>Использовать</button></div>
            </div>
          )}

          <article className="summary-section first">
            <h3>Кратко</h3>
            <p>Обсудили прогресс по текущим проектам, риски по релизу и приоритеты на следующую неделю.<br />Достигли договорённости о фокусе на стабильности и завершении интеграции аналитики.<br />Подтвердили сроки релиза и ответственных.</p>
          </article>
          <article className="summary-section">
            <h3>Решения</h3>
            <ul>
              <li>Сфокусироваться на стабилизации релиза V2.1 и закрытии P1-ошибок.</li>
              <li>Завершить интеграцию аналитики до 28 июля.</li>
              <li>Перенести запуск маркетинговой кампании на 4 августа.</li>
              <li>Утвердить план нагрузочного тестирования как обязательный этап перед релизом.</li>
            </ul>
          </article>
          <article className="summary-section next-steps">
            <h3>Следующие шаги</h3>
            {[
              ["Анна: подготовить список P1-ошибок и предложений по исправлению", "до 22 июля"],
              ["Сергей: завершить интеграцию аналитики в продакшн-среду", "до 28 июля"],
              ["Мария: обновить план нагрузочного тестирования и согласовать", "до 24 июля"],
              ["Иван: подготовить релиз-ноты и чек-лист релиза", "до 30 июля"],
            ].map(([task, due]) => <div className="task-row" key={task}><Circle size={19} /><span>{task}</span><small>{due}</small></div>)}
          </article>
        </section>
      ) : (
        <section className="transcript-panel" role="tabpanel">
          <div className="transcript-toolbar"><h2>Расшифровка</h2><button className="secondary-button compact"><MagnifyingGlass size={18} /> Найти</button></div>
          <div className="utterance"><strong>Анна</strong><time>00:12</time><p>Давайте начнём с прогресса по релизу. Что остаётся критичным на этой неделе?</p></div>
          <div className="utterance"><strong>Сергей</strong><time>00:28</time><p>Основной риск — стабильность аналитики. Интеграцию закончим к 28 июля, но нужен отдельный прогон.</p></div>
          <div className="utterance"><strong>Мария</strong><time>00:51</time><p>Тогда фиксирую нагрузочное тестирование обязательным этапом перед релизом.</p></div>
        </section>
      )}
    </main>
  );
}

function MeetingsView({ startRecording, openMeeting }) {
  return (
    <main className="library-shell">
      <header className="page-title-row"><div><h1>Встречи</h1><p>Записи, итоги и расшифровки в одном месте.</p></div><button className="primary-button" onClick={startRecording}><Microphone size={20} weight="fill" /> Начать запись</button></header>
      <div className="meeting-list">
        {meetings.map((meeting, index) => (
          <button className="meeting-row" key={meeting.title} onClick={openMeeting}>
            <span className="meeting-date-box">{index === 0 ? "21" : index === 1 ? "20" : "18"}<small>июл</small></span>
            <span className="meeting-row-copy"><strong>{meeting.title}</strong><small>{meeting.date} · {meeting.duration}</small></span>
            <span className="ready-pill">{meeting.status}</span>
          </button>
        ))}
      </div>
    </main>
  );
}

function SearchView({ openMeeting }) {
  const [query, setQuery] = useState("");
  const results = meetings.filter((item) => item.title.toLowerCase().includes(query.toLowerCase()));
  return (
    <main className="library-shell narrow-page">
      <h1>Поиск</h1>
      <label className="search-box"><MagnifyingGlass size={21} /><input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Название встречи или фраза" /></label>
      <div className="search-results">{results.map((item) => <button key={item.title} onClick={openMeeting}><strong>{item.title}</strong><small>{item.date} · {item.duration}</small></button>)}</div>
    </main>
  );
}

function SettingsView() {
  return (
    <main className="library-shell narrow-page">
      <h1>Настройки</h1>
      <section className="settings-card"><div><h3>Язык встреч</h3><p>Используется для расшифровки и итогов.</p></div><button className="select-like">Русский <CaretDown size={14} /></button></section>
      <section className="settings-card"><div><h3>Форматы итогов</h3><p>Авто выбирает структуру по содержанию встречи.</p></div><button className="secondary-button compact">Управлять</button></section>
      <section className="settings-card"><div><h3>Хранение записей</h3><p>Записи хранятся в вашем пространстве GRAF.</p></div><span className="muted-value">Без ограничений</span></section>
    </main>
  );
}

function RecordingBar({ state, onPause, onResume, onStop }) {
  const degraded = state === "degraded";
  return (
    <div className={`recording-bar ${degraded ? "warning" : ""}`} role="status" aria-live="polite">
      <div className="recording-state"><span className="live-dot" /><div><strong>{state === "paused" ? "Запись на паузе" : degraded ? "Запись продолжается" : "Идёт запись"}</strong><small>{degraded ? "Звук компьютера недоступен · микрофон записывается" : "00:18:42 · Микрофон и звук компьютера"}</small></div></div>
      <div className="recording-actions">
        {state === "paused" ? <button className="secondary-button" onClick={onResume}><Play size={19} /> Продолжить</button> : <button className="secondary-button" onClick={onPause}><Pause size={19} /> Пауза</button>}
        <button className="stop-button" onClick={onStop}><Stop size={18} weight="fill" /> Завершить</button>
      </div>
    </div>
  );
}

export function App() {
  const [view, setView] = useState("summary");
  const [tab, setTab] = useState("summary");
  const [modal, setModal] = useState(null);
  const [recording, setRecording] = useState(null);
  const [candidate, setCandidate] = useState(null);
  const [toast, setToast] = useState("");
  const [viewer, setViewer] = useState(true);
  const [email, setEmail] = useState("");
  const [deleted, setDeleted] = useState(false);
  const [processing, setProcessing] = useState(null);

  const notify = (message) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2400);
  };

  const startFlow = () => setModal("permission");
  const beginRecording = () => { setModal(null); setRecording("active"); setView("meetings"); };
  const stopRecording = () => { setRecording(null); setProcessing("offline"); setView("summary"); window.setTimeout(() => setProcessing("partial"), 1600); window.setTimeout(() => setProcessing(null), 3600); };

  const openScenario = (key) => {
    setModal(null); setDeleted(false); setCandidate(null); setProcessing(null); setRecording(null);
    if (key === "ready") setView("meetings");
    if (key === "permission") setModal("permission");
    if (key === "detected") setModal("detected");
    if (["active", "paused", "degraded"].includes(key)) { setView("meetings"); setRecording(key); }
    if (key === "offline") { setView("summary"); setProcessing("offline"); }
    if (key === "partial") { setView("summary"); setProcessing("partial"); }
    if (key === "summary") setView("summary");
    if (key === "candidate") { setView("summary"); setCandidate({ name: "Протокол встречи" }); }
    if (key === "share") { setView("summary"); setModal("share"); }
    if (key === "deleted") { setView("summary"); setDeleted(true); }
  };

  const copyLink = async () => {
    try { await navigator.clipboard?.writeText("https://graf.local/m/weekly-team"); } catch { /* local prototype fallback */ }
    notify("Ссылка для приглашённых скопирована");
  };

  return (
    <div className="app-shell">
      <Sidebar view={view} setView={setView} openScenarios={() => setModal("scenarios")} />
      {deleted ? (
        <main className="empty-state"><Trash size={44} /><h1>Запись недоступна</h1><p>Она удалена или у вас больше нет доступа.</p><button className="secondary-button" onClick={() => { setDeleted(false); setView("meetings"); }}><ArrowLeft size={18} /> К встречам</button></main>
      ) : view === "summary" ? (
        <SummaryContent tab={tab} setTab={setTab} openShare={() => setModal("share")} openMore={() => setModal("more")} candidate={candidate} setCandidate={setCandidate} />
      ) : view === "meetings" ? (
        <MeetingsView startRecording={startFlow} openMeeting={() => setView("summary")} />
      ) : view === "search" ? <SearchView openMeeting={() => setView("summary")} /> : <SettingsView />}

      {view === "summary" && !deleted && <Player openScenarios={() => setModal("scenarios")} />}
      {recording && <RecordingBar state={recording} onPause={() => setRecording("paused")} onResume={() => setRecording("active")} onStop={stopRecording} />}

      {processing && (
        <div className={`status-banner ${processing}`} role="status">
          {processing === "offline" ? <CloudSlash size={20} /> : <ArrowClockwise size={20} className="spin" />}
          <div><strong>{processing === "offline" ? "Запись сохранена на Mac" : "Готовим итоги"}</strong><span>{processing === "offline" ? "Отправим на обработку, когда появится сеть." : "Расшифровку уже можно открыть. Итоги появятся чуть позже."}</span></div>
        </div>
      )}

      {modal === "permission" && <Modal title="Разрешите запись звука" onClose={() => setModal(null)}>
        <div className="permission-visual"><Microphone size={30} /></div>
        <p className="modal-lead">GRAF нужен доступ к микрофону и звуку компьютера. Запись начнётся только после вашего нажатия.</p>
        <div className="permission-list"><div><Check size={18} /> Микрофон</div><div><Check size={18} /> Звук компьютера</div></div>
        <div className="modal-actions"><button className="text-button" onClick={() => setModal(null)}>Не сейчас</button><button className="primary-button" onClick={beginRecording}>Разрешить и начать</button></div>
      </Modal>}

      {modal === "detected" && <Modal title="Похоже, началась встреча" onClose={() => setModal(null)}>
        <p className="modal-lead">Записать разговор в Zoom? Ничего не начнётся без вашего подтверждения.</p>
        <div className="detected-app"><span className="zoom-mark">Z</span><div><strong>Zoom</strong><small>Активный разговор</small></div></div>
        <div className="modal-actions"><button className="text-button" onClick={() => setModal(null)}>Не сейчас</button><button className="primary-button" onClick={beginRecording}><Microphone size={18} /> Начать запись</button></div>
      </Modal>}

      {modal === "share" && <Modal title="Поделиться встречей" onClose={() => setModal(null)} wide>
        <div className="invite-row"><label><span className="sr-only">Электронная почта</span><input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Имя или email" /></label><button className="primary-button" disabled={!email.includes("@")} onClick={() => { setEmail(""); setViewer(true); notify("Приглашение отправлено"); }}><UserPlus size={18} /> Пригласить</button></div>
        <div className="viewer-list"><h3>Есть доступ</h3><div className="viewer-row"><span className="avatar small">АВ</span><div><strong>Вы</strong><small>alexey@graf.local</small></div><span>Владелец</span></div>{viewer && <div className="viewer-row"><span className="avatar small alternate">М</span><div><strong>Мария Волкова</strong><small>maria@graf.local</small></div><button className="text-button danger-text" onClick={() => setViewer(false)}>Закрыть доступ</button></div>}</div>
        <details className="share-details"><summary><LockSimple size={18} /> Что увидят приглашённые</summary><p>Только итоги встречи. Расшифровка и аудио останутся закрыты.</p></details>
        <div className="share-footer"><span><LockSimple size={17} /> Только приглашённые</span><button className="secondary-button compact" onClick={copyLink}><Link size={18} /> Копировать ссылку</button></div>
      </Modal>}

      {modal === "more" && <Modal title="Действия со встречей" onClose={() => setModal(null)}>
        <div className="action-list"><button onClick={() => notify("Экспорт подготовлен")}><DownloadSimple size={21} /><div><strong>Экспортировать</strong><small>Аудио, расшифровка или итоги</small></div></button><button className="danger-action" onClick={() => setModal("delete")}><Trash size={21} /><div><strong>Удалить встречу</strong><small>Запись и данные исчезнут из GRAF</small></div></button></div>
      </Modal>}

      {modal === "delete" && <Modal title="Удалить встречу?" onClose={() => setModal(null)}>
        <p className="modal-lead">Запись, расшифровка и итоги будут удалены из GRAF. Это действие нельзя отменить.</p>
        <div className="modal-actions"><button className="text-button" onClick={() => setModal(null)}>Отмена</button><button className="danger-button" onClick={() => { setModal(null); setDeleted(true); }}>Удалить</button></div>
      </Modal>}

      {modal === "scenarios" && <Modal title="Состояния прототипа" onClose={() => setModal(null)} wide>
        <p className="scenario-note">Служебная панель для проверки сценариев. В продукте её не будет.</p>
        <div className="scenario-grid">{scenarios.map(([key, label], index) => <button key={key} onClick={() => openScenario(key)}><span>{String(index + 1).padStart(2, "0")}</span>{label}</button>)}</div>
      </Modal>}

      {toast && <div className="toast" role="status"><Check size={18} /> {toast}</div>}
    </div>
  );
}
