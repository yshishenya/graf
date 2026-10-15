# F280: оплата одного периода без автопродления

[Выпуск v2026.10.01.2](https://github.com/yshishenya/graf/releases/tag/v2026.10.01.2) опубликован 2026-10-01T19:47:20Z. Тег и три работающие службы соответствуют `e9d34cf349a6bc2248a9d4e206138fd77dee9c56`. T020–T022 завершены; T011/T012 и финансовая F278 остаются открытыми.

## Поведение и проверка

Автопродление включено в новой форме по умолчанию, но его можно снять и оплатить выбранный месяц или год. При False не сохраняется новая карта для будущих списаний и не разрешается продление; оплаченный период и остаток сохраняются. Повтор операции сохраняет исходный режим и ключ. Оферта обязательна и не принимается автоматически. Выбор OFF сохраняется в текущей вкладке при промокоде, смене периода, reload и возврате после ошибки; namespace ограничен user/workspace/session. Без JavaScript разовая оплата доступна в текущей форме. Сохранение выбора между загрузками требует JavaScript и доступного sessionStorage.

Backend RED8/GREEN49. Общий HTTP/PostgreSQL465PASS/2FAIL: оба устаревших ожидания исправлены, полный return82PASS. Contract/UI69PASS; accessibility Chromium16PASS/WebKit16PASS. Финальные DOM→HTTP→SQL Chromium1PASS82.45с, WebKit1PASS173.89с: режим False сохранён в operation/invoice, один синтетический provider request с save_payment_method=False. Пересечения не суммируются; исторические отказы сохранены в validation-optional-renewal.md. Test-only поправки static assets101PASS и purchase2PASS сохраняют защитные проверки и четыре runtime хеша.

Три независимых source/flow/security/browser заключения PASS0 применимых замечаний; reviewer-owned43/0 и builtin8/0, всего51/0. Подробности review-optional-renewal-final.md и review-optional-renewal-requirements.md. Новых задач реализации convergence не выявил.

## Допуск и развёртывание

Основной PR #7409: head `8db50a9ab6d40d83d350ab28ebb7e3c9dafcd3ef`, merge `c9331a7702fd4716085ce60558c8c30c74e699be`; governance-fast36909005557, macos-pr36909005532, pr-metadata36909037123, общий validate-pr-checks.py PASS. Test-only #7410 и prep #7412 также прошли все три точные проверки и общий validator; последний prep head `93d176e1b028441cc38530b85c4ea48d85920040`, runs36913383141/36913383112/36913383326. Состав включает только F280 PR #7412/#7410/#7409/#7407 после v2026.10.01.1.

Кандидат `rc-20261001T192325Z-5444e62a992b`, train `train-20261001T192228Z-e9d34cf349a6`. [Единственный release-full36913925182](https://github.com/yshishenya/graf/actions/runs/36913925182) PASS на точном SHA: все серверные группы, PostgreSQL strict/performance, macOS и итоговый aggregator прошли. Этап CI драйвера1201с включает ожидание GitHub; это не сумма длительностей тестов. Full digest `sha256:c4dc84bc35ed2bed5e1e7acb8f7f76f004a326e73810c8509361a8a5038ad052`, train/decision GO, decision digest `sha256:a940867a45c0c838b0d4e2d5601ec1f53396aaccb4e7d5155ed76f31e3db9250`.

CD dry-run и execute PASS; deploy213с, свежая резервная копия20261001T194350Z, readiness_verdict=infra_smoke_ready. Playback/normalization scope остаётся worker_capability_only. Публичный Release и отдельная неизменяемая publication attestation соответствуют кандидату. Исторический governance FAIL36908074789 не использовался для допуска и не переписан.

Откат не потребовался и не выполнялся. Постоянный image result=deployed, попытка `d51ae8c9f1a742caaf7f7e845bbaa446`, прежний source SHA `002c15d34975edff3b8029a0dc496952188ad165`. Нормализованные result/identity/baseline references и digest записаны в evidence/optional-renewal-release.json; это не доказательство выполнения отката.

## Свежая проверка установленного выпуска

rec-api, rec-processing-worker, rec-maintenance: точный SHA и все четыре хеша исходников совпали, checkout/public=true, YooKassa production и ожидаемый магазин, observation=true, running=true. API/processing healthy; maintenance running без отдельного health статуса.

Установленный модуль в отдельном процессе: False/True×2 передают соответствующий save_payment_method и исходный idempotence key; некорректные значения отвергаются до провайдера. Установленный шаблон: recurring checked/optional, offer unchecked/required. PASS; синтетический helper с заглушкой, без БД, реальной сессии и сетевых вызовов провайдера. Этот результат не доказывает реальный платёж.

Публичные live/ready HTTP200/200. PKG заново скачан:9259700байт, SHA256 `b5df859986d0ad36a07302c87c598b7a7d6e027a65e4024dd70fe0cba3338662`. Прежние подписанные байты сохранены; macOS не пересобиралась и повторная установка человеком не аттестуется.

## Закрытие и границы

Разрешение владельца на коммиты, публичную оплату и выпуск уже дано. Закрывается только #7408 после live issue-closeout validator и полного русского комментария. #7366/#7285/#7378/#7379 остаются открытыми: человеческая приёмка T011/T012, реальные платежи/чеки/банк/возвраты F278 и измерение конверсии/удержания не доказаны этим выпуском. Документы закрытия не меняют frozen source. [Запись доказательств](evidence/optional-renewal-release.json).

Предварительный live issue-closeout validator для #7408 прошёл на exact candidate SHA с предложенным полным closure comment и T020–T022: merged PR #7409, текущие обязательные проверки и release-full36913925182 сверены. Фактическое закрытие выполняется после отдельного сохранения этих документов; затем validator перечитывает фактический issue.
