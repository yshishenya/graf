# Windows Development

Читай этот файл перед работой над `apps/windows`, Windows-сборкой, MSIX и
общими серверными изменениями, которые затрагивают Windows-клиент.

## Источники правды

- Продуктовые требования и задачи: `specs/200-windows-desktop-app/`.
- Runbook сборки и проверки: `specs/200-windows-desktop-app/quickstart.md`.
- Паритет функций macOS и Windows:
  `specs/200-windows-desktop-app/parity-matrix.md`.
- Одна пользовательская функция на обеих платформах описывается в Spec Kit
  один раз; нативные различия перечисляются явно.

## Где что запускается

- `windows-pr` (`.github/workflows/windows-pr.yml`) — Windows x64 lane:
  CMake/MSVC сборка выбранных целей, ограниченные CTest-наборы и T124 package
  suite. Lane диагностический: он не заменяет release/deploy приёмку.
- `governance-fast` — общий серверный/инфраструктурный fast lane. Любые
  серверные изменения из Windows-ветки проверяются здесь, поэтому Windows и
  macOS используют одну серверную истину.
- `macos-pr` — macOS native lane. Общие файлы кабинета и сервера обязаны
  оставаться рабочими на обеих платформах.

Local Windows host обязателен для заявлений про WinUI/WebView2, WASAPI,
Media Foundation, MSIX и аппаратную матрицу. macOS и Linux не дают такого
доказательства.

## Общие файлы

- Общий кабинет (`apps/server/src/twobrain_rec_server/cabinet/`) и серверные
  API меняются один раз для обеих платформ.
- Нативные оболочки ведём параллельно по одному контракту и одному сценарию.
- Если одна платформа опережает другую, в задаче явно указывается, какая часть
  ещё открыта, и это отражается в `parity-matrix.md`.
- Секреты, реальные записи, транскрипции, cookies, токены и подписанные ссылки
  не попадают в evidence, скриншоты и диагностику.

## Локальная проверка на Windows

```powershell
Push-Location apps/windows
cmake --preset x64-release
cmake --build --preset x64-release
ctest --preset x64-release --output-on-failure
Pop-Location
```

Полный список обязательных проверок, включая MSIX и `validate-audio-contract.ps1`,
находится в `specs/200-windows-desktop-app/quickstart.md`; не сокращай его
список без нового решения владельца.

## Правила для агентов

- Не выдавай Linux/macOS-сборку или переносимые тесты за Windows-приёмку.
- Не отключай Windows-native шаги, чтобы уложиться в лимит CI; сначала
  проверь бюджет и причину таймаута.
- Диагностический FAIL `windows-pr` не скрывается и не переквалифицируется в
  PASS; в описании PR указывается точная причина и границы проверки.
- Перед merge общие требования и CI обоих продуктов (macOS и Windows) должны
  быть проверены на одном exact SHA.
