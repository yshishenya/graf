#include "../../RecApp/Web/WebViewBridge.h"
#include "../../RecApp/Web/WebView2Host.h"
#include "../../RecApp/Contracts/WindowsDesktopContracts.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    WebViewBridge bridge("https://rec.2brain.pro");
    bridge.rotateNonce("nonce-1");
    WebViewBridgeEnvelope message{std::string(kBridgeProtocol), kBridgeProtocolVersion, 1, "nonce-1",
        "https://rec.2brain.pro", BridgeDirection::webToNative, "request_app_quit", R"({"action":"quit"})", 1};
    assert(bridge.validate(message) == BridgeValidationError::none);
    assert(bridge.validate(message) == BridgeValidationError::replay);
    message.messageId = 2; message.command = "local_recording"; message.payloadJson = R"({"action":"open","id":"known"})";
    assert(bridge.validate(message) == BridgeValidationError::none);
    // Объявление оформления обязано проходить проверку: иначе живая смена темы
    // в кабинете молча теряется, а окно остаётся прежним до перезагрузки.
    message.messageId = 3; message.command = "app_appearance"; message.payloadJson = R"({"theme":"light"})";
    assert(bridge.validate(message) == BridgeValidationError::none);
    message.messageId = 4; message.command = "capture_start"; message.payloadJson = R"({"action":"open","id":"known"})";
    assert(bridge.validate(message) == BridgeValidationError::commandDenied);
    message.messageId = 5; message.command = "request_app_quit";
    assert(bridge.validate(message) == BridgeValidationError::none);
    assert(WebView2Host::isAllowedQuitPayload(R"({"action":"quit"})"));
    assert(!WebView2Host::isAllowedQuitPayload(R"({"action":"terminate"})"));
    message.messageId = 6; message.command = "request_app_quit"; message.origin = "https://evil.example";
    assert(bridge.validate(message) == BridgeValidationError::wrongOrigin);
    message.messageId = 7; message.origin = "https://rec.2brain.pro"; message.payloadJson = std::string(65 * 1024, 'x');
    assert(bridge.validate(message) == BridgeValidationError::payloadTooLarge);
    message.messageId = 8; message.payloadJson = "not-json";
    assert(bridge.validate(message) == BridgeValidationError::malformedEnvelope);
    message.messageId = 8; message.payloadJson = "{}{}";
    assert(bridge.validate(message) == BridgeValidationError::malformedEnvelope);
    message.messageId = 9; message.payloadJson = "{";
    assert(bridge.validate(message) == BridgeValidationError::malformedEnvelope);
    message.payloadJson = "{}";
    for (const auto command : {"request_native_settings", "open_native_settings", "request_diagnostics",
                              "open_native_diagnostics", "request_runtime_repair", "ack_display", "ack",
                              "read_file", "write_file", "get_cookie", "run_process", "stop_recording"}) {
        message.command = command;
        assert(bridge.validate(message) == BridgeValidationError::commandDenied);
    }
    message.command = "local_recording";
    for (const auto origin : {"https://id.vk.ru", "https://oauth.yandex.ru", "https://passport.yandex.ru"}) {
        message.origin = origin;
        assert(bridge.validate(message) == BridgeValidationError::wrongOrigin);
    }
    message.origin = "https://rec.2brain.pro";
    message.nonce = "stale";
    assert(bridge.validate(message) == BridgeValidationError::staleNonce);
    message.nonce = "nonce-1";
    message.direction = BridgeDirection::nativeToWeb;
    assert(bridge.validate(message) == BridgeValidationError::wrongDirection);
    message.direction = BridgeDirection::webToNative;
    message.payloadJson = std::string(9, '[') + "0" + std::string(9, ']');
    assert(bridge.validate(message) == BridgeValidationError::payloadTooDeep);
    bridge.invalidate();
    message.payloadJson = "{}";
    assert(bridge.validate(message) == BridgeValidationError::staleNonce);
    bridge.rotateNonce("nonce-2");
    message.messageId = 1;
    message.nonce = "nonce-2";
    assert(bridge.validate(message) == BridgeValidationError::none);
    WebView2Host host;
    // Built field by field: a positional aggregate silently changes meaning
    // whenever the row gains a field.
    WebViewLocalRecordingRow knownRow;
    knownRow.id = "known";
    knownRow.title = "Запись";
    knownRow.status = "Ожидает отправки";
    knownRow.durationSeconds = 1;
    knownRow.sessionDurationSeconds = 1;
    knownRow.canOpen = true;
    knownRow.canSend = true;
    host.setLocalRecordings({knownRow});
    assert(!host.localRecordingActionAllowed("open", "known"));
    host.setRuntimeState(WebRuntimeState::ready);
    assert(host.localRecordingActionAllowed("open", "known"));
    assert(host.localRecordingActionAllowed("send", "known"));
    assert(!host.localRecordingActionAllowed("delete", "known"));
    assert(!host.localRecordingActionAllowed("read_file", "known"));
    assert(!host.localRecordingActionAllowed("open", "../../private"));
    host.setLocalRecordings({});
    assert(!host.localRecordingActionAllowed("open", "known"));
    host.close();
    assert(!host.localRecordingActionAllowed("send", "known"));
    // Страницы настроек кабинета и удаление записи идут тем же конвертом, что и
    // остальные команды. Пока этих двух команд не было в списке разрешённых,
    // страница настроек показывала «Не удалось загрузить настройки этого Mac»
    // вместо честного ответа, а удаление из кабинета не доходило до приложения.
    message.messageId = 2; message.command = "native_settings";
    message.payloadJson =
        R"({"handler":"grafNotificationSettings","requestId":1,"request":{"version":1,"action":"read"}})";
    assert(bridge.validate(message) == BridgeValidationError::none);
    message.messageId = 3; message.command = "delete_selection";
    message.payloadJson = R"({"action":"delete","version":1,"requestId":"r-1","ids":[],"localIds":[]})";
    assert(bridge.validate(message) == BridgeValidationError::none);
    message.messageId = 4; message.command = "native_settings_purge";
    assert(bridge.validate(message) == BridgeValidationError::commandDenied);
    return 0;
}
