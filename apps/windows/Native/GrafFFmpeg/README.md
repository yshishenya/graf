# Штатный FFmpeg для Windows AAC

GRAF использует неизменённый FFmpeg 7.1.5 x64: shared LGPL 2.1-or-later,
avutil-59.dll, avcodec-61.dll, avformat-61.dll. Native AAC encoder и IPOD/MOV
muxer с их штатными зависимостями; без private allocator, GPL/nonfree/version3,
сетевых протоколов, внешних codec libraries и программ ffmpeg/ffprobe/ffplay.

Pin owner — F200/T116. Минимальный MOV graph 8.1.3 давал MSVC C1001 в
libavformat/cbs.c с оптимизацией и без неё. Обычная 7.1.5 с оптимизацией прошла
отдельную исследовательскую сборку/короткую AVIO проверку. Это не приёмка
приложения и не утверждение, что 7.1.5 — последняя версия всего FFmpeg.
При смене MSVC или появлении поддерживаемого FFmpeg с исправленным MOV/CBS
graph повторить source/build/security/license/audio review перед обновлением.

## Сборка

Нужны VS2022 Build Tools, VC Tools14.44.35207, Windows SDK10.0.26100.0,
developer PowerShell с целевым x64. Из корня исходников GRAF:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File apps/windows/scripts/build-graf-ffmpeg.ps1 `
  -BuildDirectory C:\GrafBuild\ffmpeg-work -InstallDirectory C:\GrafBuild\ffmpeg-7.1.5-x64
```

Каталоги должны быть свежими и отдельными. Recipe загружает official source и
закреплённые MSYS2/make/diffutils с проверкой размера/SHA из manifest.json.
Source SHA ранее сопоставлен с официальной подписью; recipe не импортирует
ключи и не заявляет новую GPG-проверку. MSYS — только build tool, не runtime.
Configure/make работают вне source tree, без патчей и inherited compiler flags.
Команды, логи, configs, source pre/post inventory, PE/import/export/object
records и полный исходный tar сохраняются в verified prefix. После успеха
создаются build-provenance.json и include/graf/GrafFFmpegBuildManifest.h;
промежуточный build удаляется. При неудаче каталоги остаются для разбора,
successful attestation не создаётся. Оператор/CI обеспечивает общий timeout.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File apps/windows/scripts/build-graf-ffmpeg.ps1 `
  -InstallDirectory C:\GrafBuild\ffmpeg-7.1.5-x64 -VerifyBuildArtifacts
```

Verify не скачивает, не собирает и не загружает DLL. Он проверяет происхождение,
artifact inventory, generated pins, exact3 DLL/PE/ABI/config/license inputs.
Нельзя создавать provenance для произвольных DLL вручную. Исторический prefix
принимается только после отдельной полной проверки, не по одному новому hash.

## Подключение

`GRAF_FFMPEG_ROOT` либо MSBuild `/p:GrafFFmpegRoot=...` / Windows CMake
`-DGRAF_FFMPEG_ROOT=...` указывает verified prefix. Include root — `<root>/include`.
Header использует namespace graf::ffmpeg, ModulePin{filename,version,bytes,
sha256}, modules в порядке avutil/avcodec/avformat; digest — array<uint8_t,32>.
Также содержит machine, release, configurationBytes/configurationSha256 и
source/provenance hashes. Его данные относятся к данной проверенной сборке:
MSVC link bytes не обязаны совпадать между сборками. Изменение DLL/headers/config
требует нового header и сборки EXE/MSIX; mutable runtime manifest не используется.

WinUI и native CMake получают exact3 app-local DLL без import libs/delay-load.
Portable targets не требуют FFmpeg. Нет PATH/внешнего executable/MF encoder
fallback; MF reader/playback остаются. Build не доказывает installed loaded
modules, audio/long-duration/protected IO/recovery/hardware acceptance T116/T118.
GRAF owned buffers сохраняют общий64MiB и wipe; internal FFmpeg memory отдельно
измеряется/штатно освобождается, полный wipe не обещается.

## Лицензия и соответствующие исходники

MSIX включает точные COPYING.LGPLv2.1 и LICENSE.md, этот README, manifest,
recipe и полный ffmpeg-7.1.5.tar.xz из verified prefix. Source copyright notices
сохранены в tar; корневого COPYRIGHT в этом архиве нет. LICENSE.md описывает
также optional GPL/external components, которые данная конфигурация не включает.
SOURCES.json закрепляет upstream notice bytes. Оператор также сохраняет exact
source/recipe/provenance рядом с дистрибутивом; ссылка только на главную FFmpeg
не заменяет соответствующие исходники.

Для исследования/модификации скопировать материалы из ThirdPartyNotices/FFmpeg
в свой рабочий каталог. Восстановить раскладку apps/windows/scripts/
build-graf-ffmpeg.ps1 и apps/windows/Native/GrafFFmpeg/{manifest.json,notices/}.
Официальный tar можно распаковать обычным tar. Recipe source не патчит.
Для изменённой библиотеки сохранить соответствующие исходники/свои изменения,
обновить проверенные inputs и пересобрать shared DLL, generated header и GRAF
с этим prefix. Исходники GRAF: https://github.com/yshishenya/graf; при поставке
оператор связывает инструкцию с точной опубликованной версией приложения.
Integrity pins не должны отменять права на модификацию/замену, предоставленные
LGPL. Эти условия, доступность corresponding source и пользовательские notices
проверяются на конечной поставке. Наличие файлов не является licensing/release PASS.
