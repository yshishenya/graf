# F273/T106 — серверная граница public событий

Основа e8a67a7e21046a641b2bdd0f1caf75aca7895e6f, lane active Spec Kit slice.
До кода выполнен scoped analyze пяти групп: public scope/config; register
и отзыв уровня3; context/relay/delivery/final provider guard; causal RED/GREEN;
честный промежуточный объём и release boundaries. Coverage5/5, mapped T106,
CRITICAL/HIGH/MEDIUM0, unmapped0, Constitution II/III/IV/VI не нарушены.
T106 явно входит в Spec tasks issue#7696; отдельная задача не создаётся.
Полный T106, SDK lifecycle, индивидуальный серверный отзыв, runtime/T0
и коммерческий рост не принимаются.

Первый prerequisite с --require-spec отклонён установленной версией; повтор
использует поддержанный --require-tasks --include-tasks. Это не продуктовый
сбой и не доказательство приёмки.

Независимое before-code ревью:5/0,P1/P2/HIGH0. Анализ и sync существующего
#7696 завершены до кода; canon255 PASS. RED двух новых настоящих сценариев
воспроизвёл context enabled=true и relay202 после изменения реестра. GREEN
2passed/27deselected. Внешние флаги/SDK/редакция не изменены.
Для прежних проверок включённой аналитики добавлена opt-in fixture
public_basis_register в существующем conftest: временный валидный пустой
реестр; её запрашивают только затронутые public тесты. Существующий CLI
public_analytics_config создаёт тот же учебный реестр в TemporaryDirectory
и восстанавливает окружение после вывода synthetic config.
Первый широкий focused:112passed,1failed,1skipped. Отказ был старым
тестом UTM без явного реестра; добавлен тот же opt-in prerequisite, assert
сохранены. Пропущенная настоящая modal проверка отдельно исполнена с
готовым Playwright:1passed за3,23с. Node consent harness PASS,0skips.

Исправленный профиль30passed за13,19с,0skips, включая прежний отказавший
UTM тест, весь consent enforcement с настоящим modal и PostHog autocapture
контракт. До этого112passed включали неизменные public/lifecycle/provider
профили. Изолированные PostgreSQL контейнеры обоих прогонов удалены
штатным runner (isolated_container_removed); стенды не сохранены. Ruff,
process, Spec Kit governance и diff-check PASS. Общий final PostHog gate
и его модуль не менялись. Независимое implementation review/converge
следует отдельно; полный T106/runtime/SDK/T0 остаются открытыми.

Независимое implementation review/converge PASS:checklist5/0,P1/P2/HIGH0.
Принятые hashes analytics.py c789fa7ab77ee5090c0542fd422fadab175e50a618c8d7229e10c34416d3694d
и web.py d61c93bb74ae6b0f1bd193844a093985b9d85f25b11e9b4e78e01d3cf9ec19a3
сверены. Дополнительно весь настоящий PostHog provider профиль8passed0,08с;
это регрессия сохранённого final gate, а не разрешение новой внешней отправки.
Коммит/PR/точные GitHub проверки и выпуск принимаются отдельно.
