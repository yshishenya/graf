# Research

Decision: сначала измеримость. Production read-only 15 октября UTC / 16 октября локально: product runtime disabled; acquisition одна запись без bridge; PostHog старые события. Метрика overview вернул 500; Search Console: 2 indexed/13 excluded на 12 октября. Полные актуальные источники — docs/growth/audit-2026-10-16.md.

Decision: отделить уровни. /guides и три руководства уже имеют серверный агрегат без JS; Zoom/F282 вызывают только renderer. Использовать отдельный каталог только уровня 1 и anonymous_only в существующем helper. normalize_public_campaign_attribution обрабатывает только текущие UTM/referer; существующий writer проверяет legal basis. Cookie и L2 не трогать. Отсутствие JS не доказывает отсутствие server measurement.

Alternatives: вставка Метрики нарушила бы scope; глобальный middleware захватил бы private/help/неизвестные пути; новые таблицы/провайдер не нужны. Нужна отдельная F273 работа по identity, consent, organic handoff и постоянной доставке. Запросы не заменяют сессии/воронку.

Decision: GEO через оригинальные проверяемые материалы, читаемый HTML, фактические возможности, источники и измерение. Robots allow не доказывает индексацию. llms.txt не ставить выше основных работ, не обещать FAQ rich results, позиции или цитирование.

Уточнение существующего legal gate: отсутствие withdrawal register означает отсутствие записанного отзыва, а не запрет обезличенного уровня 1. Он разрешён действующей настройкой; выключение уровня или явный отзыв блокирует запись. Этот контракт не меняется. Проверка missing register должна подтвердить доступность, а не выдуманный новый запрет.
