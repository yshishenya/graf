# Langfuse: набор F239 для отдельного релиза

Подготовлено 2026-09-08 только под меткой `dev`. Production остался v5 у всех
профилей. Числовые версии и hash нужно перечитать перед переносом меток.
Модель всех целевых версий — `gpt-5.6-sol`; дополнительных model parameters
нет. Полная проверка реальных мемо выполнялась на auto v60; остальные профили
проверены на совпадение редакционного ядра, схемы и конфигурации, не на полном
корпусе реальных встреч. Акцент профиля не удаляет разделы документа.

| Prompt | Целевая версия | Canonical hash | Текущая production |
| --- | --- | --- | --- |
| graf/meeting-outcome/auto | 60 | `21e79357e331a55a9f91e6dcbbcb8a0c3397e4189792070a67bc1aca10d1ee06` | 5 |
| graf/meeting-outcome/outline | 55 | `145f3ba68d5c364c99b681cc6270f33992fc6ffcd55d84daa92661390f82c5a3` | 5 |
| graf/meeting-outcome/meeting-minutes | 55 | `b4a7c482e8dccd3f5e14c6f48c8f47411e1a2aab186fde5fa68ca08137cbf28a` | 5 |
| graf/meeting-outcome/project-sync | 55 | `85946a814adc6eef5dc1b95d522eeb42395acf6e86d0ba4ee8a095ab3795511a` | 5 |
| graf/meeting-outcome/weekly-team-meeting | 55 | `45db9f9a279bee05591ec2dbef99fece91ac337ca62b9a22ca74dd2f1e76cdcd` | 5 |
| graf/meeting-outcome/one-to-one | 55 | `5b5c80a4ef944b47ae7e916d4979896c945570993db88078c85a56c616992fb0` | 5 |
| graf/meeting-outcome/client-status-update | 55 | `8045045138b59a8bbb84139ab8b9beca7ed4d336ae95ffb11fbc774efad585d7` | 5 |
| graf/meeting-outcome/interview | 55 | `4be006319e7a42b5f0953acbbc9e9b5ea0f47fd58f0a5abb6145ad2c3980f937` | 5 |
| graf/meeting-outcome/sales-discovery | 55 | `a1ba9c9c83f9681178850ba8254870bab59b0e1350ce226130036b8c614d1ba5` | 5 |
| graf/meeting-outcome/custom | 55 | `a15ac1ee652caa58919de6e8f02941e54d2b9d1dff1659f241305c96a46d6aa0` | 5 |

Перенос production — только оператором отдельного релиза вместе с новым
контрактом GRAF и миграцией. В этом задании не выполнялся. Порядок перехода
и настройка времени ожидания: [quickstart.md](quickstart.md).
