# Заявка в SignPath Foundation — материалы

Документ фиксирует, что именно подаём в бесплатную программу подписи
SignPath Foundation, и какие ответы даём на их проверку. Заявка подаётся
владельцем после merge лицензии.

## Что подаём

- Проект: GRAF (`yshishenya/graf`).
- Сайт продукта: <https://rec.2brain.pro>.
- Лицензия: GNU AGPL-3.0 (`LICENSE` в корне репозитория).
- Платформа подписи: Windows x64, пакет MSIX для App Installer.
- Форма заявки: <https://signpath.org/open-source>.

## Что подтверждаем на проверке

1. **Проект открытый.** Репозиторий публичный, в корне лежит `LICENSE` с
   AGPL-3.0. Сторонние компоненты сохраняют свои лицензии и перечислены в
   `ThirdPartyNotices` внутри пакета: FFmpeg (LGPL-2.1), WebRTC AEC3 (BSD),
   Abseil (Apache-2.0), WebView2, Windows App SDK, C++/WinRT.
2. **Проект выпущен и поддерживается.** Публичная версия для macOS
   распространяется с сайта; Windows-пакет собирается и проверяется в CI.
3. **Сборка воспроизводима из публичных источников.** Никаких приватных
   зависимостей и закрытых бинарников:
   - AEC3 — публичное зеркало и закреплённый коммит
     (`apps/windows/Native/GrafAEC3/upstream.lock`);
   - FFmpeg — закреплённый архив 7.1.5 и сборочный скрипт;
   - .NET-пакеты — NuGet (`apps/windows/Directory.Packages.props`);
   - сборка — `apps/windows/Installer/GrafWindows.Package.wapproj`,
     `Release|x64`.
4. **Подписывается только собранный артефакт.** Тестовые и локальные сборки
   не подписываются: у них отдельный самоподписанный канал.

## Команды сборки для CI

```powershell
# зависимости
apps/windows/scripts/build-graf-aec3.ps1 -Configuration Release -Architecture x64
apps/windows/scripts/build-graf-ffmpeg.ps1 -InstallDirectory <dir>

# пакет
msbuild apps/windows/Installer/GrafWindows.Package.wapproj /restore /m `
  /p:Configuration=Release /p:Platform=x64 `
  /p:GrafFFmpegRoot=<ffmpeg> /p:GrafAEC3Root=<aec3-src> /p:GrafAEC3BuildRoot=<aec3-build>
```

Артефакт подписи: `GrafWindows.Package_<версия>_x64.msix` из
`apps/windows/Installer/out/`. Зависимости для установки лежат рядом в
`Dependencies\x64`.

## Что понадобится после одобрения

- организация и проект SignPath, политика подписи (slugs выдаёт портал);
- секрет CI с токеном SignPath;
- шаг подписи в отдельной полосе публичного выпуска: подписывается тот же
  MSIX, что прошёл проверки содержимого;
- проверка `signtool verify /pa /all /tw` и запись Subject сертификата — из
  него получается утверждённый `Publisher` для манифеста.

## Чего SignPath не решает

- Он не выбирает `Publisher` за нас: Subject берётся из выданного
  сертификата, и только после этого меняется манифест (T138).
- Он не заменяет приёмку установки и обновления на чистой Windows.
- Он не отменяет релизный порядок: подпись — шаг внутри замороженного
  кандидата, а не повод публиковать в обход `release-full` и `decide`.
