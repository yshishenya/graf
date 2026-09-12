# Validation quickstart

## Автоматические проверки

Из корня:

```sh
swift test --package-path apps/macos --filter 'ShortRecording|LocalRecordingWriter|CaptureRecoveryService|DesktopUploadQueueTests'
git diff --check
```

Синтетические кадры, временные каталоги, fake upload client. Длительности 479999/480000/480001 кадров при 16000 Гц. Штатные userRequested/meetingEnded. Failure/exit/recovery/legacy/import не удаляются. Предварительное saving, повтор scan, перезапуск сервиса, cleanup failure и symlink escape не дают сетевого вызова и не трогают чужие файлы. Не считать muted mic тишиной системного звука.

## Установленный GRAF Dev

После проверенного и разрешённого коммита: docs/agent-guidance/local-development.md и infra/dev/README.md; status → build → promote → status → smoke только через dev-harness.

1. Синтетический звук, ручной Start/Stop раньше 30 секунд: сообщение без вопроса, нет встречи и upload, новый Start доступен.
2. Повторить автозапуск/автоостановку, затем Stop из меню со скрытым окном. Сообщение видно, фокус остаётся в текущем приложении; проверить VoiceOver.
3. Запись дольше 30 секунд: воспроизведение содержит самое начало. Проверить системный звук при выключенном микрофоне.
4. Перезапуск после отклонения: нет восстановленной короткой встречи. Аварийный фрагмент сохраняется отдельной синтетической проверкой.
5. Stop короткой записи укладывается в прежние 2 секунды; уведомление исчезает примерно за 6 секунд. Светлая/тёмная тема.

Native status до этих проверок = pending. Required GitHub governance-fast на exact PR SHA, merge отдельно; release-full и подписанный публичный релиз не входят в локальный PASS.
