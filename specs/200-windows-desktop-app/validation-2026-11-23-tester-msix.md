# Тестовый MSIX Windows: сборка на hosted runner — 2026-11-23

Документ фиксирует, что полоса `windows-tester-build` действительно собирает
устанавливаемый пакет. Это не публичный выпуск и не приёмка на физической
машине: установку и запуск проверяют пользователи на своих компьютерах.

## Что было сломано

Первый прогон полосы (run `45075156775`) упал на проверке AEC3, второй
(`45085820803`, job `137404068111`) — на `MakeAppx`:

```
Manifest validation error: The file name "GrafWindowsApp.exe" ...
doesn't exist in the package. 0x80080204
```

Причина: `GenerateAppxPackageOnBuild=true` передавался в командной строке, а
это глобальное свойство MSBuild. Оно попадало не только в проект упаковки, но
и в проект приложения через ссылку на проект. Приложение с
`WindowsPackageType=MSIX` пыталось собрать собственный пакет, а его карта
пакета не содержала исполняемый файл, потому что проект приложения объявляет
`AppxPackage=false`. Проект упаковки до раскладки макета даже не доходил.

## Что исправлено

- `apps/windows/Installer/GrafWindows.Package.wapproj`: `GenerateAppxPackageOnBuild`
  задаётся в самом проекте упаковки; проект приложения получает
  `GenerateAppxPackageOnBuild=false` через `AdditionalProperties` ссылки.
- `.github/workflows/windows-tester-build.yml`: сборка вызывает только
  `wapproj`; MSIX ищется строго в выводе проекта упаковки (пакеты зависимостей
  в `Dependencies\<arch>` исключены); добавлен шаг `Verify package contents`.
- Зависимости копируются из макета `Dependencies\x64`, который создаёт сам
  проект упаковки: версии совпадают с объявленными в манифесте.

## Результат прогона

- Run: `45130873163`, job `137545850346`, head
  `ce6842e6b4598525c40eff00e2fc4b6e4a1e7482`.
- Артефакт: `graf-windows-tester-2026.11.23.5`.
- `GRAF-Windows.msix`, SHA-256 `a4241fb0bd1bd5f5cab943aa97df870242156e2004dfb0b5e54aed92c57c2ece`,
  51 запись.
- Подпись: `Valid`, subject `CN=GRAF`, thumbprint
  `869FCC7A08C024233F084C25E6939C968DD6B14A` (самоподписанный тестовый канал).
- `validate-package-smoke.ps1`: `identity=com.graf.desktop,
  entryPoint=GrafWindowsApp.exe, signatureStatus=Valid`.
- В пакете: `GrafWindowsApp.exe` (PE32+ x86-64), `resources.pri`,
  `WebView2Loader.dll`, `Microsoft.Web.WebView2.Core.dll` и `.winmd`, среда C++
  (`vcruntime140`, `msvcp140` и связанные), библиотеки FFmpeg
  (`avcodec-61`, `avformat-61`, `avutil-59`), значки и полный набор
  `ThirdPartyNotices`.
- Эффективный манифест: `ProcessorArchitecture="x64"`,
  `Resource Language="RU-RU"`, зависимости
  `Microsoft.VCLibs.140.00.UWPDesktop` и `Microsoft.WindowsAppRuntime.2`
  (`MinVersion=2.4.0.0`).
- В комплекте: `Microsoft.VCLibs.x64.14.00.Desktop.appx` и
  `Microsoft.WindowsAppRuntime.2.msix`. Имя и версия каждой зависимости
  читаются из `AppxManifest.xml` самого пакета зависимости, а не из имени
  файла: `framework_dependencies=Microsoft.VCLibs.140.00.UWPDesktop=included@14.0.33728.0;
  Microsoft.WindowsAppRuntime.2=included@2.4.0.0`. Если объявленной зависимости
  нет, полоса падает.
- Первый успешный прогон с этой раскладкой — `45123131370` (версия
  `2026.11.23.4`, SHA-256 `ff5352ce…`): сборка и подпись работали, а проверка
  зависимостей тогда сравнивала только имена файлов.

## Что это не доказывает

- Установку, первый запуск, вход, запись и воспроизведение на физической
  Windows-машине: это делают пользователи по
  `tester-install-ru.md`.
- Доверие без установки сертификата: канал тестовый, сертификат
  самоподписанный.
- Публичный выпуск: нужен сертификат удостоверяющего центра (T124).
- Автообновление: `.appinstaller` формируется только при указании
  `feed_base_url` и здесь не проверялся.

## Замечено попутно

В пакет попадает `System.Core.dll` из справочных сборок .NET 3.5: проект
упаковки наследует неявные ссылки .NET-проекта. На запуск это не влияет, но это
лишний управляемый файл в native-пакете и вопрос происхождения. Вынесено в
отдельную задачу, блокировкой тестового канала не является.
