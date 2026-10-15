#include "../../RecApp/Upload/DesktopApiClient.h"
#include "../../RecApp/Web/WebViewBridge.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

using namespace graf::windows;

namespace {
constexpr auto eventId = "abcdefab-1234-4567-89ab-abcdefabcdef";
constexpr auto requestId = "11111111-2222-3333-4444-555555555555";
const std::string ids = std::string("\"eventId\":\"") + eventId + "\",\"requestId\":\"" + requestId + "\"";
const std::string join = "{\"action\":\"joinCalendarEvent\"," + ids + "}";
const std::string cancel = "{" + ids + "}";
std::string envelope(std::string_view command, std::string_view payload, std::string_view extra = {}) {
    // Lexical decoding is not source/origin/nonce/auth verification.
    return "{\"command\":\"" + std::string(command) + "\",\"payload\":" +
        std::string(payload) + std::string(extra) + "}";
}
}

int main() {
    const auto parsed = DesktopApiClient::decodeCalendarJoinIntent(join, "calendar_join");
    assert(parsed && parsed->eventId == eventId && parsed->requestId == requestId);
    const auto cancelled = DesktopApiClient::decodeCalendarJoinIntent(cancel, "calendar_join_cancel");
    assert(cancelled && cancelled->eventId == eventId && cancelled->requestId == requestId);
    assert(!DesktopApiClient::decodeCalendarJoinIntent(join, "calendar_join_cancel"));
    assert(!DesktopApiClient::decodeCalendarJoinIntent(cancel, "calendar_join"));
    for (const auto command : {"", "calendar_join_reply", "calendar_join_cancelled", "capture_start"}) {
        assert(!DesktopApiClient::decodeCalendarJoinIntent(join, command));
        assert(!DesktopApiClient::calendarJoinEnvelopePayload(envelope(command, join), command));
    }
    const auto escaped = DesktopApiClient::decodeCalendarJoinIntent(
        R"({"\u0061ction":"joinCalendar\u0045vent","event\u0049d":"ABCDEFAB-1234-4567-89AB-ABCDEFABCDEF","requestId":"\u00311111111-2222-3333-4444-555555555555"})",
        "calendar_join");
    assert(escaped && escaped->eventId == eventId && escaped->requestId == requestId);
    assert(DesktopApiClient::decodeCalendarJoinIntent(
        R"({"eventId":"00000000-0000-0000-0000-000000000000","requestId":"00000000-0000-0000-0000-000000000000"})",
        "calendar_join_cancel")); // UUID syntax, not account authority.
    for (const auto& invalid : {std::string("null"), std::string("[]"), std::string("{}"), join + "{}",
             "{\"action\":\"joinCalendarEvent\",\"eventId\":null,\"requestId\":\"" + std::string(requestId) + "\"}",
             "{\"action\":\"joinCalendarEvent\",\"eventId\":\"bad\",\"requestId\":\"" + std::string(requestId) + "\"}",
             "{\"action\":false," + ids + "}", "{\"action\":\"joinCalendarEvent \"," + ids + "}",
             "{\"action\":\"joinCalendarEvent\"," + ids + ",\"url\":\"https://example.org\"}",
             "{\"action\":\"joinCalendarEvent\"," + ids + ",\"record\":true}",
             "{\"action\":\"joinCalendarEvent\",\"action\":\"joinCalendarEvent\"," + ids + "}",
             "{\"action\":\"joinCalendarEvent\",\"\\u0061ction\":\"joinCalendarEvent\"," + ids + "}",
             "{\"action\":\"joinCalendarEvent\"," + ids + ",\"event\\u0049d\":\"" + eventId + "\"}",
             "{\"action\":\"\\uD800\"," + ids + "}", "{\"action\":\"\\uDC00\"," + ids + "}",
             "{\"action\":\"\\u0000\"," + ids + "}", "{\"action\":\"\xc0\xaf\"," + ids + "}"}) {
        assert(!DesktopApiClient::decodeCalendarJoinIntent(invalid, "calendar_join"));
        assert(!DesktopApiClient::calendarJoinEnvelopePayload(envelope("calendar_join", invalid), "calendar_join"));
    }
    for (const auto& invalid : {"{\"eventId\":\"" + std::string(eventId) + "\",\"requestId\":true}",
             "{" + ids + ",\"requestId\":\"" + requestId + "\"}",
             "{" + ids + ",\"request\\u0049d\":\"" + requestId + "\"}", "{" + ids + ",\"action\":\"cancel\"}"}) {
        assert(!DesktopApiClient::decodeCalendarJoinIntent(invalid, "calendar_join_cancel"));
    }
    const auto raw = envelope("calendar_join", join);
    assert(DesktopApiClient::calendarJoinEnvelopePayload(raw, "calendar_join") == join);
    assert(DesktopApiClient::calendarJoinEnvelopePayload(envelope("calendar_join_cancel", cancel), "calendar_join_cancel") == cancel);
    assert(!DesktopApiClient::calendarJoinEnvelopePayload(raw, "calendar_join_cancel"));
    assert(DesktopApiClient::calendarJoinEnvelopePayload(
        "{\"command\":\"calendar_\\u006aoin\",\"pay\\u006coad\":" + join + "}", "calendar_join") == join);
    for (const auto& extra : {std::string(",\"command\":\"calendar_join\""), std::string(",\"\\u0063ommand\":\"calendar_join\""),
             ",\"payload\":" + join, ",\"pay\\u006coad\":" + join,
             std::string(",\"extra\":{\"a\":0,\"\\u0061\":1}"), std::string(",\"extra\":\"\\uD800\""),
             std::string(",\"extra\":\"\xc0\xaf\"")}) {
        assert(!DesktopApiClient::calendarJoinEnvelopePayload(envelope("calendar_join", join, extra), "calendar_join"));
    }
    assert(!DesktopApiClient::calendarJoinEnvelopePayload("{\"payload\":" + join + "}", "calendar_join"));
    assert(!DesktopApiClient::calendarJoinEnvelopePayload("{\"command\":\"calendar_join\"}", "calendar_join"));
    assert(!DesktopApiClient::calendarJoinEnvelopePayload(raw + "garbage", "calendar_join"));
    assert(DesktopApiClient::calendarJoinEnvelopePayload(
        envelope("calendar_join", join, ",\"extra\":\"\\uD83D\\uDE00\""), "calendar_join") == join);
    assert(DesktopApiClient::calendarJoinEnvelopePayload(
        envelope("calendar_join", join, ",\"extra\":\"\\u0000\""), "calendar_join") == join);
    // Result owns the original raw payload, not a normalized SDK object or views.
    auto input = envelope("calendar_join", " \n" + join + " \t");
    const auto owned = DesktopApiClient::calendarJoinEnvelopePayload(input, "calendar_join");
    input.assign(65536, 'x');
    assert(owned && *owned == join && DesktopApiClient::decodeCalendarJoinIntent(*owned, "calendar_join"));
    for (const std::size_t limit : {65535U, 65536U}) {
        assert(DesktopApiClient::decodeCalendarJoinIntent(join + std::string(limit - join.size(), ' '), "calendar_join"));
        assert(DesktopApiClient::calendarJoinEnvelopePayload(raw + std::string(limit - raw.size(), ' '), "calendar_join"));
    }
    assert(!DesktopApiClient::decodeCalendarJoinIntent(join + std::string(65537 - join.size(), ' '), "calendar_join"));
    assert(!DesktopApiClient::calendarJoinEnvelopePayload(raw + std::string(65537 - raw.size(), ' '), "calendar_join"));
    // Envelope has a separate root level; validate nested unknown fields too.
    const auto nested = std::string(8, '[') + "0" + std::string(8, ']');
    assert(DesktopApiClient::calendarJoinEnvelopePayload(envelope("calendar_join", join, ",\"extra\":" + nested), "calendar_join"));
    assert(!DesktopApiClient::calendarJoinEnvelopePayload(envelope("calendar_join", join, ",\"extra\":[" + nested + "]"), "calendar_join"));
    // This staging decoder never grants runtime command authority before the
    // document/route/current-owner handler is wired into the shared operation.
    WebViewBridge bridge("https://example.org");
    assert(!bridge.isAllowedWebCommand("calendar_join") && !bridge.isAllowedWebCommand("calendar_join_cancel"));
}
