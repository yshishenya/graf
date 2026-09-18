// The cabinet's settings pages ask the app the way macOS lets them ask it, and the
// page validates every answer before it shows or saves anything. These checks hold
// the two ends of that agreement: what the app accepts as a request, and what it
// sends back.
#include "../../RecApp/Web/NativeSettingsBridge.h"

#include <cassert>
#include <cstdio>
#include <string>

using graf::windows::NativeSettingsBridge::Action;
using graf::windows::NativeSettingsBridge::Target;

namespace {

void testOnlyTheSettingsPageMayUseTheBridge() {
    // The route macOS bridges: the recording settings page, addressed plainly.
    assert(graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/recording"));
    assert(graf::windows::NativeSettingsBridge::isSettingsRoute(
        "http://127.0.0.1:8080/desktop/settings/recording"));
    // A different page, a query, a fragment and a look-alike path are not it.
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/notifications"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/recording?next=/desktop/meetings"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/recording#section"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/recording/extra"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute("/desktop/settings/recording"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute(""));
}

void testTheRequestVocabularyIsThePagesOwn() {
    using namespace graf::windows::NativeSettingsBridge;
    assert(actionFromToken("read") == Action::read);
    assert(actionFromToken("set") == Action::set);
    assert(actionFromToken("setAll") == Action::setAll);
    // Unknown, differently cased and empty actions are not actions.
    assert(!actionFromToken("write"));
    assert(!actionFromToken("SET"));
    assert(!actionFromToken(""));
    assert(actionToken(Action::read) == "read");
    assert(actionToken(Action::set) == "set");
    assert(actionToken(Action::setAll) == "setAll");

    // The stored preference and the page's select share these three words.
    assert(isRule("always"));
    assert(isRule("ask"));
    assert(isRule("never"));
    assert(!isRule("Always"));
    assert(!isRule("sometimes"));
    assert(!isRule(""));
}

void testTheReplyCarriesWhatThePageValidates() {
    using namespace graf::windows::NativeSettingsBridge;
    const std::vector<Target> targets{
        {"yandex-telemost", "Яндекс Телемост", "always"},
        {"zoom", "Zoom Workplace", "never"},
    };
    const auto reply = settingsReply(targets);
    // The page reads `version`, `targets[].id`, `targets[].name` and `targets[].rule`.
    assert(reply.find("\"version\":1") != std::string::npos);
    assert(reply.find("{\"id\":\"yandex-telemost\",\"name\":\"Яндекс Телемост\",\"rule\":\"always\"}") != std::string::npos);
    assert(reply.find("{\"id\":\"zoom\",\"name\":\"Zoom Workplace\",\"rule\":\"never\"}") != std::string::npos);
    // Russian text is sent as UTF-8; it is not escaped into something else.
    assert(reply.find("Яндекс") != std::string::npos);
}

void testATargetThatWouldBreakTheReplyIsLeftOut() {
    using namespace graf::windows::NativeSettingsBridge;
    // The page refuses the whole reply over one unusable row, and then it would
    // show nothing at all: a row that cannot be answered is dropped instead.
    const std::vector<Target> targets{
        {"", "Без ключа", "always"},
        {"broken-rule", "Сломанное правило", "sometimes"},
        {"good", "Рабочее приложение", "ask"},
    };
    const auto reply = settingsReply(targets);
    assert(reply.find("Без ключа") == std::string::npos);
    assert(reply.find("Сломанное правило") == std::string::npos);
    assert(reply.find("good") != std::string::npos);
    assert(reply.find("always") == std::string::npos);
    // Exactly one target, so exactly one comma-free object after the colon.
    assert(reply.find(",\"name\"") != std::string::npos);
}

void testQuotesAndControlCharactersCannotLeaveTheJson() {
    using namespace graf::windows::NativeSettingsBridge;
    const std::vector<Target> targets{{"we\"ird", "Имя \"в кавычках\"\nи перенос", "ask"}};
    const auto reply = settingsReply(targets);
    // A name that would otherwise end the string early is escaped.
    assert(reply.find("Имя \\\"в кавычках\\\"\\nи перенос") != std::string::npos);
    assert(reply.find("we\\\"ird") != std::string::npos);
    // No raw newline survived: the page parses this as one JSON document.
    assert(reply.find('\n') == std::string::npos);
}

void testARefusalIsStillAnAnswer() {
    using namespace graf::windows::NativeSettingsBridge;
    const auto reply = failureReply("Настройки не сохранены.");
    // The page checks the version before it believes anything, including a refusal.
    assert(reply.find("\"version\":1") != std::string::npos);
    assert(reply.find("\"error\":\"Настройки не сохранены.\"") != std::string::npos);
    // An empty message is never sent as an empty reason.
    const auto blank = failureReply("");
    assert(blank.find("\"error\":\"\"") == std::string::npos);
}

void testEachSettingsPageHasItsOwnRoute() {
    using namespace graf::windows::NativeSettingsBridge;
    assert(isRecordingSettingsRoute("https://rec.2brain.pro/desktop/settings/recording"));
    assert(isNotificationSettingsRoute("https://rec.2brain.pro/desktop/settings/notifications"));
    // Neither page answers for the other, and the general check accepts both.
    assert(!isRecordingSettingsRoute("https://rec.2brain.pro/desktop/settings/notifications"));
    assert(!isNotificationSettingsRoute("https://rec.2brain.pro/desktop/settings/recording"));
    assert(isSettingsRoute("https://rec.2brain.pro/desktop/settings/notifications"));
    assert(!isNotificationSettingsRoute("https://rec.2brain.pro/desktop/settings/notifications?tab=1"));
    assert(!isNotificationSettingsRoute("https://rec.2brain.pro/desktop/settings"));
}

void testTheNotificationReplyIsThePlatformTruth() {
    using namespace graf::windows::NativeSettingsBridge;
    const auto reply = notificationSettingsReply("");
    // The page refuses a reply that misses one of these, and then it would show
    // nothing at all, so the shape is checked here.
    assert(reply.find("\"version\":1") != std::string::npos);
    assert(reply.find("\"preferences\":{\"reminders\":false,\"showTitles\":false,\"sound\":false,\"offsetMinutes\":0}") != std::string::npos);
    assert(reply.find("\"canEdit\":false") != std::string::npos);
    assert(reply.find("\"canRequestPermission\":false") != std::string::npos);
    assert(reply.find("\"permission\":\"Windows") != std::string::npos);
    // A reason given by the app is used as it is.
    assert(notificationSettingsReply("Причина.").find("\"permission\":\"Причина.\"") != std::string::npos);
}

void testTheShimAsksOnlyWhatTheAppCanAnswer() {
    const auto script = std::string(graf::windows::NativeSettingsBridge::documentScript());
    // The page calls exactly this handler and awaits the promise the shim returns.
    assert(script.find("window.webkit.messageHandlers.grafRecordingSettings") != std::string::npos);
    assert(script.find("graf:native-settings") != std::string::npos);
    assert(script.find("graf:native-settings-reply") != std::string::npos);
    assert(script.find("__grafNativeSettingsInstalled") != std::string::npos);
    // Both settings pages the app can answer are advertised, and only those.
    assert(script.find("window.webkit.messageHandlers.grafNotificationSettings") != std::string::npos);
    // Installing it twice would replace a page's own pending requests.
    assert(script.find("if (window.__grafNativeSettingsInstalled) return;") != std::string::npos);
}

void testTheSharedSettingsPageStopsClaimingToBeAMac() {
    const auto script = std::string(graf::windows::NativeSettingsBridge::documentScript());
    // Общая серверная страница написана для macOS. На Windows это неправда, и
    // оболочка приводит слова и кнопку в порядок, не трогая общую страницу.
    assert(script.find("platformWords") != std::string::npos);
    assert(script.find("['На этом Mac', 'На этом компьютере']") != std::string::npos);
    assert(script.find("['Настройки macOS', 'Настройки Windows']") != std::string::npos);
    assert(script.find("['разрешение macOS', 'разрешение Windows']") != std::string::npos);
    assert(script.find("'настройки этого компьютера'") != std::string::npos);
    // Живая проверка 2026-09-19: заголовок страницы «На этом Mac» стоит вне формы
    // настроек, поэтому обход идёт по всему документу — иначе заголовок, легенда
    // раздела, карточка навигации и примечание для страниц без скриптов остаются
    // маковскими.
    assert(script.find("const root = document.body;") != std::string::npos);
    assert(script.find("['Правила автозаписи на Mac', 'Правила автозаписи в Windows']") != std::string::npos);
    assert(script.find("['Уведомления на этом Mac', 'Уведомления на этом компьютере']") != std::string::npos);
    assert(script.find("['изменить уведомления Mac', 'изменить уведомления в приложении']") != std::string::npos);
    // Кнопка системных настроек на Windows скрывается: у этой страницы нет
    // системного разрешения, которое она могла бы открыть.
    assert(script.find("[data-local-notification-action=\"openSystemSettings\"]") != std::string::npos);
    assert(script.find("button.hidden = true") != std::string::npos);
    // Живая проверка 2026-09-19 (раунд 52) показала, что одной подписки на события
    // мало: оболочка ставится, когда документ уже идёт. Поэтому правка запускается
    // сразу, на событии документа, на подстановке и ещё дважды по времени.
    assert(script.find("const runAdaptation = () => {") != std::string::npos);
    assert(script.find("document.addEventListener('DOMContentLoaded', runAdaptation)") != std::string::npos);
    assert(script.find("document.addEventListener('htmx:afterSwap', () => reportAdaptation('swap'))") != std::string::npos);
    assert(script.find("setTimeout(() => reportAdaptation('after-120ms'), 120)") != std::string::npos);
    assert(script.find("setTimeout(() => reportAdaptation('after-600ms'), 600)") != std::string::npos);
    // Отчёт нужен, чтобы отличить «слов не нашлось» от «правка не запускалась»:
    // хозяин пишет неизвестную команду в bridge.log.
    assert(script.find("'diag_' + stage + '_f' + result.found + '_r' + result.replaced") != std::string::npos);
    assert(script.find("window.dispatchEvent(new CustomEvent('graf:native-settings'") != std::string::npos);
    assert(script.find("(result.error ? '_err' : '')") != std::string::npos);
}

} // namespace

int main() {
    testOnlyTheSettingsPageMayUseTheBridge();
    testTheRequestVocabularyIsThePagesOwn();
    testTheReplyCarriesWhatThePageValidates();
    testATargetThatWouldBreakTheReplyIsLeftOut();
    testQuotesAndControlCharactersCannotLeaveTheJson();
    testARefusalIsStillAnAnswer();
    testEachSettingsPageHasItsOwnRoute();
    testTheSharedSettingsPageStopsClaimingToBeAMac();
    testTheNotificationReplyIsThePlatformTruth();
    testTheShimAsksOnlyWhatTheAppCanAnswer();
    std::puts("NativeSettingsBridgeTests passed");
    return 0;
}
