#include "../../RecApp/Upload/DesktopHttpTransport.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <chrono>
#include <thread>

using namespace graf::windows;
using Clock = std::chrono::steady_clock;
using State = CalendarJoinResolutionState;

namespace {
constexpr auto eventId = "abcdefab-1234-4567-89ab-abcdefabcdef";
const std::string body = std::string("{\"event_id\":\"") + eventId +
    "\",\"provider_family\":\"calendar\",\"https_url\":\"https://example.org/join?key=synthetic#room\"}";
DesktopHttpConfig config() {
    DesktopHttpConfig result;
    result.baseOrigin = "https://example.org";
    result.workspaceId = "22222222-2222-4222-8222-222222222222";
    result.sessionToken = "synthetic-session";
    result.confirmedIdentity = DesktopAccountIdentity{
        "11111111-1111-4111-8111-111111111111", result.workspaceId};
    result.deviceId = "must-not-travel";
    result.scopedAccount = DeletionScope{"foreign", "foreign"};
    return result;
}
}

int main() {
    unsigned calls = 0;
    const auto deadline = Clock::now() + std::chrono::seconds(3);
    DesktopHttpTransport::CalendarJoinGet get = [&](const DesktopHttpConfig& wire,
        std::string_view path, Clock::time_point limit) {
        ++calls;
        assert(path == std::string("/api/v1/calendar/events/") + eventId + "/join-target");
        assert(limit == deadline && wire.deviceId.empty() && wire.scopedAccount);
        assert(wire.sessionToken == "synthetic-session" && wire.workspaceId == config().workspaceId);
        assert(wire.scopedAccount->userId == wire.confirmedIdentity->userId);
        assert(wire.scopedAccount->workspaceId == wire.confirmedIdentity->workspaceId);
        return DesktopHttpTransport::UploadResponse{200, body, false, {}, "1790000000"};
    };
    const auto resolved = DesktopHttpTransport(config()).calendarJoinTarget(
        "ABCDEFAB-1234-4567-89AB-ABCDEFABCDEF", deadline, get);
    assert(calls == 1 && resolved.state == State::resolved && resolved.target);
    assert(resolved.target->eventId == eventId && resolved.authExpiresAt == 1790000000);
    assert(resolved.target->httpsUrl == "https://example.org/join?key=synthetic#room");
    assert(DesktopHttpTransport(config()).calendarJoinTarget(eventId, deadline, get).target && calls == 2);
    const auto rejectedConfig = [&](DesktopHttpConfig bad) {
        const auto before = calls;
        const auto result = DesktopHttpTransport(std::move(bad)).calendarJoinTarget(eventId, deadline, get);
        assert(result.state != State::resolved && !result.target && calls == before);
    };
    auto bad = config(); bad.confirmedIdentity.reset(); rejectedConfig(bad);
    bad = config(); bad.confirmedIdentity->userId = "bad"; rejectedConfig(bad);
    bad = config(); bad.confirmedIdentity->workspaceId = "bad"; rejectedConfig(bad);
    bad = config(); bad.workspaceId.clear(); rejectedConfig(bad);
    bad = config(); bad.workspaceId = "33333333-3333-4333-8333-333333333333"; rejectedConfig(bad);
    for (const auto& token : {std::string{}, std::string("bad\r\ninjection"),
             std::string("bad\0value", 9), std::string(4097, 'x'), std::string("space token")}) {
        bad = config(); bad.sessionToken = token; rejectedConfig(bad);
    }
    for (const auto origin : {"http://localhost", "https://", "https://a@b", "https://a/path",
             "https://a?query", "https://a#fragment", "https://a\\b", "https://a\n"}) {
        bad = config(); bad.baseOrigin = origin; rejectedConfig(bad);
    }
    bad = config(); bad.clientVersion = "bad\nheader"; rejectedConfig(bad);
    bad = config(); bad.clientVersion = std::string(121, 'x'); rejectedConfig(bad);
    assert(!DesktopHttpTransport(config()).calendarJoinTarget("../bad", deadline, get).target && calls == 2);
    assert(DesktopHttpTransport(config()).calendarJoinTarget(eventId, Clock::now(), get).state == State::dependencyUnavailable);
    assert(DesktopHttpTransport(config()).calendarJoinTarget(eventId, deadline, {}).state == State::dependencyUnavailable);
    assert(calls == 2);
    for (const auto& entry : {std::pair{0U, State::dependencyUnavailable}, {200U, State::resolved},
             {201U, State::invalidTarget}, {204U, State::invalidTarget}, {301U, State::invalidTarget},
             {302U, State::invalidTarget}, {307U, State::invalidTarget}, {308U, State::invalidTarget},
             {401U, State::authRequired}, {403U, State::eventUnavailable}, {404U, State::eventUnavailable},
             {410U, State::eventUnavailable}, {408U, State::dependencyUnavailable},
             {429U, State::dependencyUnavailable}, {503U, State::dependencyUnavailable}}) {
        const auto result = DesktopHttpTransport(config()).calendarJoinTarget(eventId, deadline,
            [&](const auto&, auto, auto) { return DesktopHttpTransport::UploadResponse{entry.first, body}; });
        assert(result.state == entry.second && bool(result.target) == (entry.second == State::resolved));
    }
    for (const auto& invalid : {std::string("{}"), body + "garbage",
             std::string("{\"event_id\":\"33333333-3333-4333-8333-333333333333\",\"provider_family\":\"calendar\",\"https_url\":\"https://example.org\"}"),
             body + std::string(65537 - body.size(), ' ')}) {
        const auto result = DesktopHttpTransport(config()).calendarJoinTarget(eventId, deadline,
            [&](const auto&, auto, auto) { return DesktopHttpTransport::UploadResponse{200, invalid}; });
        assert(result.state == State::invalidTarget && !result.target && !result.authExpiresAt);
    }
    for (const std::size_t size : {65535U, 65536U}) {
        assert(DesktopHttpTransport(config()).calendarJoinTarget(eventId, deadline,
            [&](const auto&, auto, auto) { return DesktopHttpTransport::UploadResponse{
                200, body + std::string(size - body.size(), ' ')}; }).target);
    }
    assert(DesktopHttpTransport(config()).calendarJoinTarget(eventId, deadline,
        [](const auto&, auto, auto) { return DesktopHttpTransport::UploadResponse{200, body, true}; }).state == State::dependencyUnavailable);
    assert(DesktopHttpTransport(config()).calendarJoinTarget(eventId, deadline,
        [](const auto&, auto, auto) -> DesktopHttpTransport::UploadResponse { throw 1; }).state == State::dependencyUnavailable);
    auto cancel = std::make_shared<std::atomic_bool>(true);
    bad = config(); bad.cancellation = cancel;
    assert(DesktopHttpTransport(bad).calendarJoinTarget(eventId, deadline, get).state == State::cancelled && calls == 2);
    cancel->store(false);
    const auto cancelled = DesktopHttpTransport(bad).calendarJoinTarget(eventId, deadline,
        [&](const auto&, auto, auto) { cancel->store(true); return DesktopHttpTransport::UploadResponse{200, body}; });
    assert(cancelled.state == State::cancelled && !cancelled.target && !cancelled.authExpiresAt);
    for (const auto status : {200U, 401U}) {
        const auto result = DesktopHttpTransport(config()).calendarJoinTarget(eventId,
            Clock::now() + std::chrono::milliseconds(2),
            [&](const auto&, auto, auto limit) { std::this_thread::sleep_until(limit);
                return DesktopHttpTransport::UploadResponse{status, body, false, {}, "1790000000"}; });
        assert(result.state == State::dependencyUnavailable && !result.target && !result.authExpiresAt);
    }
    const auto invalidExpiry = DesktopHttpTransport(config()).calendarJoinTarget(eventId, deadline,
        [](const auto&, auto, auto) { return DesktopHttpTransport::UploadResponse{200, body, false, {}, "-1"}; });
    assert(invalidExpiry.target && !invalidExpiry.authExpiresAt);
}
