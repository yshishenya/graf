# Public landing B2C brief

Status: working product/copy brief for the implemented public landing slice.
Feature 142 and its current contracts are the implementation source of truth.

## Goal

The landing page should move a new visitor to the download path while keeping
login obvious for returning users. It should feel like a calm consumer
productivity product, not an enterprise security page or a technical
architecture explainer.

The page has one primary path:

```text
Начать -> вход -> кабинет -> скачать приложение -> включить автозапись -> готовые итоги встречи
```

The secondary hero CTA may jump to the first product-proof chapter; it must not
send a new visitor into a login wall. Login remains visible in the header and
final CTA.

## Positioning

GRAF is an AI meeting recorder that can automatically capture selected meeting
applications, with manual recording available for other supported calls, then
turns the conversation into a transcript, summary, decisions, and tasks.

The simple promise:

> Встречи записываются сами. GRAF сохраняет главное.

## Hero copy

Current H1:

```text
Встреча закончится
Главное останется
```

Current subcopy:

```text
Включите автозапись для нужных приложений — без бота в звонке. После встречи
GRAF сохранит расшифровку, решения и следующие шаги.
```

Primary CTA:

```text
Скачать GRAF
```

## Message hierarchy

1. Automatic recording.
2. Works with the conferencing apps people already use.
3. No need to take notes during the call.
4. No bot in the participant list.
5. Transcript, summary, decisions, and tasks after the call.
6. Calendar sync as a helper mechanism, not the main promise.

## Sales conversion rule

The page should sell the relief, not the setup. Lead with the outcome: the user
does not need to remember to record, take notes, or reconstruct decisions after
the meeting.

Every major section should answer one conversion question:

- What happens automatically?
- Will it work with the calls I already have?
- What do I get after the meeting?
- What is the next click?

The hero's next click is either the download path or the first proof chapter;
returning users can use the header or final login CTA.

## Start and download path

The landing primary CTA opens:

```text
/download
```

The final/header login CTA opens:

```text
/login?next=/meetings
```

The hero product CTA opens:

```text
#how
```

The `/download` handoff route serves the current installer package for the
desktop app. Users who start from login still see the same download path from
the login page and from the first-run cabinet state.

## Calendar copy rule

Do not make calendar sync the hero-level value proposition. Calendar sync only
explains how automatic recording can find scheduled calls and reduce missed
recordings.

Use it in a lower "How it works" section:

```text
Включите автозапись
GRAF видит запланированные звонки и помогает не забыть запись.
```

Avoid hero lines such as:

```text
GRAF синхронизируется с календарем...
Подключите календарь...
```

## Suggested page structure

### Hero

- Wordmark.
- H1: "Встреча закончится / Главное останется".
- Subcopy focused on automatic recording and meeting results.
- Primary CTA: "Скачать GRAF"; secondary proof link: "Посмотреть продукт".
- Product visual showing an upcoming/active meeting becoming transcript,
  summary, and tasks.
- Compatibility rail: use the current registry-driven application list as
  examples of approved auto-record targets, not as partner logos or an
  exhaustive compatibility promise.

### Core benefits

- Автоматически записывает встречи.
- Работает в любых приложениях для конференций.
- Без бота в звонке.
- Делает транскрипт, саммари, решения и задачи.

### How it works

1. Выберите приложения для автозаписи.
2. Говорите как обычно; активная запись всегда видна и управляется кнопками
   «Пауза» и «Остановить».
3. Получайте расшифровку, решения и следующие шаги.

### After the meeting

Show the output as one finished meeting result, not as numbered feature cards:

- transcript excerpts with timecodes;
- short summary;
- decision tags;
- assigned tasks.

### Final CTA

Repeat only the primary action:

```text
Начать
```

## Claims to gate before publishing

These claims must be backed by the active feature spec and validation evidence
before the landing page ships:

- automatic recording;
- broad conferencing-app compatibility;
- no bot in the call;
- transcript generation;
- summary, decisions, and tasks;
- fast turnaround copy such as "через минуты";
- named platform examples or integration logos.

If a claim is not accepted yet, either remove it from the public page or make
the implementation slice prove it before release.

## Avoid

- Technical-first messaging about self-hosting, server boundaries, MediaScribe,
  or internal architecture in the hero.
- Platform-specific copy in the hero.
- "Book a demo", "Request pilot", or sales-led CTAs for the B2C path.
- A secondary CTA that lets the user avoid the login page.
- Overstated claims such as "works with every app" unless the acceptance
  evidence supports that exact wording.
