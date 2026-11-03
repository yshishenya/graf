# F211 T114: фактические metadata и официальный эталон

PR7863 source ebb720844e9a52f4c80b535fc9f8050508a8729e,
run41255823281/job124698702639;01.11.2026 00:14:35UTC.
Native metadata: keyring type32768 uid0 gid0 mode777 size3607.
Это настоящий отказ до тестов; actual content hash и происхождение0777
не установлены. Ubuntu24.04.5, image20261025.353.1.

Получены по HTTPS из официального archive.ubuntu.com,01.11.2026.
Deb читались в памяти; штатный macOS tar извлёк только публичный ключ,
ничего не устанавливалось. Первая попытка stdlib tarfile не распознала zstd;
повтор использовал существующий /usr/bin/tar, без новых зависимостей.
Сохранены только metadata и контрольные суммы, бинарных ключей/архивов нет.

```json
[
  {
    "url": "https://archive.ubuntu.com/ubuntu/pool/main/u/ubuntu-keyring/ubuntu-keyring_2023.11.28.1build1_all.deb",
    "deb_sha256": "c377ccf26964f4c206c05c0bc7adb708e031beb919bb9a0ff63af983d064cd66",
    "deb_size": 11228,
    "keyrings": [
      {
        "size": 3607,
        "sha256": "80a36b0a6de2f69f49d2df75ef473ccde121e9e190b9ea01d20a4f63778d5c31",
        "archive_metadata": "-rw-r--r--  0 root   root     3607 Nov 26  2023 ./usr/share/keyrings/ubuntu-archive-keyring.gpg"
      }
    ]
  },
  {
    "url": "https://archive.ubuntu.com/ubuntu/pool/main/u/ubuntu-keyring/ubuntu-keyring_2026.08.18_all.deb",
    "deb_sha256": "fec10bd81d9ce809a5c11c6227a367611dd0e2589afebb41d46aefb350be8f40",
    "deb_size": 12718,
    "keyrings": [
      {
        "size": 2334,
        "sha256": "655e378ede8af51ed5f2ffe3669b38f124593abc1aa769c2cc76ef5986a2f835",
        "archive_metadata": "-rw-r--r--  0 root   root     2334 Aug 19 00:33 ./usr/share/keyrings/ubuntu-archive-keyring.gpg"
      }
    ]
  },
  {
    "url": "https://archive.ubuntu.com/ubuntu/project/ubuntu-archive-keyring.gpg",
    "size": 3607,
    "sha256": "80a36b0a6de2f69f49d2df75ef473ccde121e9e190b9ea01d20a4f63778d5c31"
  }
]
```

Старый пакет и прямой project key совпадают по hash/size. Это основание
проверенного pin в проекте T114, не доказательство совпадения key runner.
Новая версия2334bytes/hash отличается и не входит в узкое исправление.
На runtime нет загрузки образца; mismatch остаётся отказом. Требования и
реализация/приёмка разделены; T112/T113/T114/#7859 открыты.
