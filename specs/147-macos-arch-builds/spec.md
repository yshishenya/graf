# Feature 147: Universal macOS installer

## Цель

Поставлять один публичный macOS installer для Apple Silicon и старых Intel
Mac, сохранив system-audio-first capture и исключив retired virtual driver из
source, build, installer и validation path.

## Требования

- Installer по умолчанию называется `graf.pkg` и содержит ровно один
  `GRAF.app` component.
- `GRAF.app/Contents/MacOS/GRAF` содержит `arm64` и `x86_64` Mach-O slices.
- SwiftPM собирает каждую архитектуру отдельно; `lipo` объединяет только
  проверенные single-architecture binaries.
- Минимальная версия macOS — 14.5 для обеих архитектур.
- Public download page показывает одну macOS кнопку и одну ссылку на
  `downloads/graf.pkg`; выбор архитектуры отсутствует.
- Legacy virtual audio driver не входит в package или acceptance path.
- Несовместимая архитектура и macOS ниже 14.5 отклоняются.

## Не входит

- Два публичных пакета или client-side architecture detection.
- Возврат virtual driver.
- Изменение capture pipeline и production signing policy.
