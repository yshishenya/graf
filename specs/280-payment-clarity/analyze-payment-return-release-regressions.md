# F280 T045 — анализ после полной проверки

Lane: high-risk-product; 2026-10-03. Два независимых допуска требований: [FR035](review-payment-return-release-requirements.md), [финансовые границы и FR032](review-payment-return-release-safety-requirements.md). Checklist перечитан reviewer:17 checked/0 unchecked; исполнитель отметки не менял.

| Требование | Задача и граница | Приёмка |
|---|---|---|
| FR032/036 | T045 обновляет7 старых assertions и вторичную legacy continue ветку | видимое recovery, отсутствие ложного успеха, финансовые проверки сохранены |
| FR035 | T045 узкий manual_resolution invoice + существующий legacy helper, GET/POST одинаковы | ключ/сумма/согласия прежние; 1 invoice/operation, provider0 для terminal/чужих/несогласованных |
| FR037, SC013 | причинный RED8/49, новая отрицательная матрица и полный набор | независимый source/test; новое exact-SHA CI |
| release-deploy | T032 послеT045 | старый CI37107429605 FAILURE, новый frozen candidate/full/CD/live proof |

Missing0/contradicts0/unrequested0 для уточнённого плана; partial реализации T045 ещё открыта. Требование вторичной continue fallback добавлено по конкретному reviewer замечанию; ни автоматическое создание оплаты, ни изменение суммы/grants/ролей не запланированы. Финансовый снимок проверяется существующей _create_initial_checkout_payment; новый допуск не разрешает противоречащий invoice. Отчёты независимых reviewers перенесены механически с относительными ссылками; выводы не переписаны.
