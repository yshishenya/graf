# Public landing B2C brief

Status: working product/copy brief for the implemented public landing slice.
This is not a production release spec yet.

## Goal

The landing page should convert a visitor directly into the login page and
first use. It should feel like a calm consumer productivity product, not an
enterprise security page and not a technical architecture explainer.

The page has one primary path:

```text
Начать -> вход -> кабинет -> скачать приложение -> включить автозапись -> готовые итоги встречи
```

Do not use a secondary "see how it works" CTA on the first screen.

## Positioning

GRAF is an AI meeting recorder that automatically records online meetings in
the conferencing apps people already use, then turns the conversation into a
transcript, summary, decisions, and tasks.

The simple promise:

> Встречи записываются сами. GRAF сохраняет главное.

## Hero copy

Recommended H1:

```text
Встреча останется с вами
```

Recommended subcopy:

```text
GRAF сам записывает звонок и собирает главное после него.
```

Primary CTA:

```text
Начать
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

Avoid making the user choose between learning and starting. The next click is
always the login page.

## Start and download path

The landing primary CTA opens:

```text
/download
```

The secondary login CTA opens:

```text
/login?next=/meetings
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
- H1: "Встреча останется с вами".
- Subcopy focused on automatic recording and meeting results.
- One CTA: "Начать".
- Product visual showing an upcoming/active meeting becoming transcript,
  summary, and tasks.
- Compatibility strip: lead with "Любой сервис для созвонов" and use a compact
  moving wordmark rail with Russian and global conferencing services as
  examples, not as an exhaustive dependency list.

### Core benefits

- Автоматически записывает встречи.
- Работает в любых приложениях для конференций.
- Без бота в звонке.
- Делает транскрипт, саммари, решения и задачи.

### How it works

1. Включите автозапись.
2. Говорите как обычно.
3. Получайте итоги.

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
