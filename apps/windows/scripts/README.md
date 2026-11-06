# Windows build and evidence scripts

The first claim is x64 on Windows 10 22H2 (19045) and the separately recorded
supported Windows 11 build set. ARM64 is a gate, not an implied target.

Pinned setup dependencies:

- Windows App SDK `2.4.0`;
- WebView2 SDK `1.0.4129.50` with Evergreen Runtime at install/runtime;
- C++/WinRT `3.0.260818.1`;
- GrafAEC3 source identity from `Native/GrafAEC3/upstream.lock`.

All scripts must keep the same boundaries:

- synthetic audio contains only generated tones/noise and never real meetings;
- evidence contains metadata, bounded counters, durations, safe reason codes and
  redacted device identity only;
- raw audio, transcripts, cookies, tokens, signed URLs and local private paths
  stay outside git and committed evidence;
- callbacks remain bounded packet drains; file I/O, WebView calls and AEC3 stay
  on workers;
- no virtual audio driver, Stereo Mix dependency, kernel component, elevated
  service or direct MediaScribe/MinIO egress;
- every Windows claim names the host OS/build, architecture, exact SHA and
  skipped ARM64/hardware lanes.

`build-graf-aec3.ps1 -VerifyOnly` checks only the pinned checkout and upstream
license files. A successful verification is not a successful Windows build or
hardware/audio-quality gate.

Application/MSIX builds require the real pinned AEC3 backend; they now fail if
it is missing. An external cache can be selected with the MSBuild properties
`GrafAEC3Root` and `GrafAEC3BuildRoot`. Both must refer to the same clean pinned
checkout and its Meson Windows x64 build. `-VerifyBuildArtifacts` requires the
provenance written only after a successful build: pinned inputs, unchanged source
and header tree, architecture, configuration, recipe and hashes of libraries and
generated headers. Old caches without provenance must be rebuilt. The builder
compares unpacked Abseil with the pinned archive plus patch before compilation;
changed inputs during compilation invalidate the result. Linker errors still
reject missing dependencies.
ARM64 remains unsupported until its own source/build/hardware validation.

Run the build-gate regressions and the actual packaged executable self-check on Windows:

```powershell
.\apps\windows\scripts\validate-aec3-build.ps1 `
  -SourceDirectory <pinned-source> -BuildDirectory <meson-build> `
  -MSBuild <MSBuild.exe> -Executable <installed-GrafWindowsApp.exe> `
  -ExpectedExecutableSha256 <independently-recorded-installed-package-exe-sha256>
```

This checks missing/forged dependencies, unsupported architecture, wrong source
revision, stale/missing provenance, changed library bytes and the accepted real
dependency. The script accepts only the exact `GrafWindowsApp.exe` path under the
registered GRAF MSIX install location, verifies its hash, and launches it through
the installed package's AppUserModelID. Do not start an MSIX-built EXE directly
from the build folder: that omits package activation and cannot validate packaged
runtime behavior. Close GRAF before passing `-Executable`; if a GRAF process is
already running, the script refuses activation. It never terminates a process
on timeout. `--verify-audio-backend` accepts the packaged launch argument and
requires package identity; it returns the distinctive code **73** only after
real AEC construction and reverse-before-microphone processing. It does not
open devices, record, write user files or contact the network. A normal exit
code 0, a hash mismatch, an out-of-package path or a timeout/failure is not a
pass. Without `-Executable` that part is explicitly NOT_RUN. Compare the
installed executable hash with the MSIX payload. Neither this check nor
portable tests replaces real capture/AEC hardware acceptance.

`validate-package-smoke.ps1 -Package <msix>` requires a certificate and a
`Valid` signature result on the checking host. An embedded certificate alone
does not pass. `test-package-smoke.ps1` exercises the actual validator with a
synthetic archive and simulated OS signature results (valid, untrusted, changed,
unknown and unsigned). It does not install a package or change trust settings.
These regressions are not a substitute for validating a real signed MSIX, nor
does a development certificate trusted in the VM prove public distribution.

## Нативная проверка входа WebView2 (T103)

В x64 Developer PowerShell Visual Studio:

```powershell
.\apps\windows\Tests\GrafWindowsContractTests\RunWebView2AuthNativeTests.ps1 `
  -GeneratedHeaders <generated-winrt-headers> `
  -RuntimeDllDirectory <native-runtime-dlls> `
  -Python <python.exe> `
  -SyntheticCertificate <test-certificate.pem> `
  -SyntheticPrivateKey <test-private-key.pem>
```

Используйте только отдельный синтетический сертификат, не рабочие ключи.
Скрипт собирает настоящий `WebView2Host` и проверяет 14 случаев:
обычный кабинет 200; HTML-формы входа 400/429 и привязки почты 429/503;
JSON503, который не должен стать формой; истёкшую сессию и требование выбора
пространства; безопасный возврат к тарифам и встрече; реальный отказ TLS и
обрыв до HTTP-ответа; отправку синтетической формы методом POST с ответом 400.
При восстановлении проверяется отсутствие автоматического перехода на вход,
затем выполняется явное действие через тот же host. Это не проверка нажатия
кнопки AppMain или её изображения. Каждый случай получает новый
временный профиль; каталог среды проверяется до создания контроллера и
повторно до навигации. Только локальный HTTPS, без реального аккаунта,
микрофона, установки приложения или изменения системного доверия.
Исключение проверки сертификата действует лишь в синтетической среде теста
и отключено в случае `tls-failure`.

Общий успех — `T103_CASES=PASS` и exit 0 после проверки окончательных
серверных счётчиков и очистки. При отказе собственный временный каталог
сохраняется для разбора. Время ожидания одного сценария ограничено 35 с
(сама проверка до 20 с, штатное завершение браузера до 10 с);
сборка и файловые операции в этот предел не входят. Набор запускается
отдельно от переносимого CTest, поскольку ему нужны WinUI и настоящий
WebView2. Он не заменяет проверку установленного пакета, реального аккаунта,
нажатия доступной с клавиатуры кнопки, всех видов сетевых ошибок и полной
матрицы T103. Для транспортного обрыва допускаются 1–3 GET к странице входа
(повтор самого браузера), остальные счётчики должны быть нулевыми; для всех
остальных случаев итоговые строки счётчиков сравниваются точно.

В `initial200` дополнительно проверяется T112: исходный значок скрыт, нативная
доступность показывает его, замена кнопки через `htmx:afterSwap` сохраняет
видимость и делегированное нажатие. Один клик по вложенному элементу должен
дойти до настоящего host handler ровно один раз. Снятие нативной доступности
снова скрывает значок. Тест не передаёт nonce вручную и не вызывает установку;
Package API, окно AppMain и клавиатурная приёмка этим не проверяются.

## T112: проверка обновлений

`WindowsAppUpdateTests` входит в CTest. Он проверяет состояния и ограничение
времени, один одновременно выполняющийся запрос, закрытие/повторное открытие,
отбрасывание позднего ответа и честное отображение отмены. На Windows запуск
этого же исполняемого файла с `--native-no-package` проверяет настоящий Package
API без подмены операции: отсутствие package identity должно дать
`unavailable/noPackage`. Такой запуск нужно делать вне контекста MSIX.
Обычный запуск использует синтетические операции и не проверяет сеть.

Пункт трея «Проверить обновления…» открывает отдельное немодальное окно.
Общая кнопка кабинета появляется только после подтверждённого Available/Required,
а не по наличию моста. Оба пути запускают проверку, не установку. Закрытие окна
отменяет текущий запрос; пока Windows не завершила его, второй не создаётся.
Нельзя считать эти проверки приёмкой канала поставки, установленного окна,
доступности, безопасной установки, сохранности или подписанного перехода
между версиями: эти части T112 остаются открытыми.
