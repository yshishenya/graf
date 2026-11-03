#include "../../RecApp/Contracts/WindowsDesktopContracts.h"
#include "../../RecApp/Core/WindowsDesktopSession.h"
#include "../../RecApp/Diagnostics/MetadataSafeDiagnostics.h"
#include "../../RecApp/Permissions/WindowsReadinessGate.h"
#include "../../RecApp/Storage/AtomicFileStore.h"
#include "../../RecApp/Storage/Sha256.h"
#include "../../RecApp/Storage/ProtectedCustodyCodec.h"
#include "../../RecApp/Upload/DesktopApiClient.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <array>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <sstream>
#include <utility>

int main() {
    using namespace graf::windows;

    assert(sha256("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    std::istringstream hashInput("abc");
    assert(sha256Stream(hashInput) == sha256("abc"));

    assert(kManifestSchemaVersion == "local-recording-manifest.v5");
    assert(kCanonicalMixProfile == "canonical-mix.v1");
    assert(kQueueSchemaVersion == "desktop-upload-queue.v3");
    assert(kQueueSchemaVersionV2 == "desktop-upload-queue.v2");
    assert(kQueueLedgerFileName == "desktop-upload-queue.v2");
    assert(kBridgeProtocol == "graf.desktop.bridge");
    assert(kBridgeProtocolVersion == 1);

    WindowsDesktopSession session("session-001");
    assert(session.beginReadinessCheck().accepted());
    WindowsDesktopSession second("session-002");
    assert(second.beginReadinessCheck().reason == ReasonCode::activeSessionExists);
    assert(session.markReady().accepted());
    assert(session.beginStart().accepted());
    assert(session.startRecording().accepted());
    assert(session.pause().accepted());
    assert(session.resume().accepted());
    assert(session.markDegraded(ReasonCode::clockDiscontinuity).accepted());
    assert(session.stop().accepted());
    assert(session.stop().status == TransitionStatus::idempotent);
    assert(session.beginFinalizing().accepted());
    assert(session.saveLocal().accepted());
    assert(session.queue().accepted());
    assert(session.upload().accepted());

    const std::array<std::pair<bool ReadinessInputs::*, ReasonCode>, 7> required = {{
        {&ReadinessInputs::microphonePermissionGranted, ReasonCode::microphonePermissionDenied},
        {&ReadinessInputs::microphoneEndpointReady, ReasonCode::microphoneEndpointUnavailable},
        {&ReadinessInputs::renderEndpointReady, ReasonCode::renderEndpointUnavailable},
        {&ReadinessInputs::formatNormalizationReady, ReasonCode::formatNormalizationUnavailable},
        {&ReadinessInputs::aecReady, ReasonCode::aecUnavailable},
        {&ReadinessInputs::storageWritable, ReasonCode::storageUnavailable},
        {&ReadinessInputs::aacEncoderReady, ReasonCode::aacEncoderUnavailable},
    }};
    const auto unavailable = WindowsReadinessGate::evaluate({});
    assert(!unavailable.recordingReady && unavailable.blockerCount == required.size());
    ReadinessInputs ready;
    for (const auto& [field, reason] : required) {
        (void)reason;
        ready.*field = true;
    }
    // Native technical readiness alone permits recording, with or without WebView.
    for (const bool webReady : {false, true}) {
        ready.webViewRuntimeReady = webReady;
        const auto readiness = WindowsReadinessGate::evaluate(ready);
        assert(readiness.recordingReady && readiness.blockerCount == 0);
        assert(readiness.webViewReady == webReady);
        for (const auto& [field, reason] : required) {
            auto denied = ready;
            denied.*field = false;
            const auto blocked = WindowsReadinessGate::evaluate(denied);
            assert(!blocked.recordingReady && blocked.blockerCount == 1);
            assert(blocked.blockers[0] == reason);
        }
    }

    const auto diagnostics = MetadataSafeDiagnostics::serialize({
        "0.1.0", "19045", "x64", SessionState::recording, ReasonCode::none,
        300, 300, 3000, "endpoint-id", false,
    });
    assert(diagnostics.find("endpoint-id") == std::string::npos);
    assert(diagnostics.find("endpoint_fingerprint") != std::string::npos);
    assert(diagnostics.find("\"processed_blocks\":300") != std::string::npos);
    assert(diagnostics.find("\"written_blocks\":300") != std::string::npos);
    assert(diagnostics.find("\"duration_ms\":3000") != std::string::npos);
    assert(diagnostics.find("\"trusted_prefix_retained\":false") != std::string::npos);
    assert(diagnostics.find("dropped_frames") == std::string::npos);
    assert(diagnostics.find("overflow_count") == std::string::npos);
    assert(diagnostics.size() <= 1024);

    const auto path = std::filesystem::temp_directory_path() / "graf-feature-200-contract-fixture.json";
    const auto writeResult = AtomicFileStore::write(path, "{\"state\":\"ready\"}");
    assert(writeResult.ok());
    std::ifstream input(path, std::ios::binary);
    const std::string contents((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    assert(contents == "{\"state\":\"ready\"}");
    input.close();
    assert(sha256File(path) == sha256(contents));
    std::filesystem::remove(path);

    const auto meeting = DesktopApiClient::createMeetingRequest("recording-001", "recording-001--initial", 60);
    assert(meeting.has_value());
    assert(meeting->sourceKind == kV5SourceKind);
    assert(meeting->mediaScribeSourceMode == kV5MediaScribeSourceMode);
    // A package without bounds keeps the old body shape exactly.
    assert(!meeting->hasTimeline() && meeting->title.empty());

    // 2026-09-18T09:05:00Z at UTC+03:00 displays as 12:05 the same day. The label
    // and both instants are fixed regardless of the machine time zone.
    const std::uint64_t startedAtMs = 1789722300000ULL;
    // Changing the owner/allocator must not change the bytes sent to the server.
    for (const auto instant : {std::uint64_t{0}, startedAtMs}) for (const int offset : {-840, -300, 0, 180, 840, 841}) {
        auto ordinary = DesktopApiClient::createMeetingRequest("recording-001", "recording-001--initial", 60,
            instant, instant + 61'000, offset);
        auto charged = DesktopApiClient::createMeetingRequest<CustodyString>("recording-001", "recording-001--initial", 60,
            instant, instant + 61'000, offset);
        assert(ordinary && charged && ordinary->hasTimeline() == charged->hasTimeline());
        if (ordinary->hasTimeline()) { ordinary->title += "\\\"\n\r\t"; charged->title += "\\\"\n\r\t"; }
        assert(std::string_view(DesktopApiClient::createMeetingBody(*charged)) == DesktopApiClient::createMeetingBody(*ordinary));
        assert(std::string_view(DesktopApiClient::formatDisplayMinute<CustodyString>(instant, offset)) ==
            DesktopApiClient::formatDisplayMinute(instant, offset));
        assert(std::string_view(DesktopApiClient::formatUtcInstant<CustodyString>(instant)) == DesktopApiClient::formatUtcInstant(instant));
    }
    assert(std::string_view(DesktopApiClient::idempotencyKey<CustodyString>("meeting", "recording-001", "session-001")) ==
        DesktopApiClient::idempotencyKey("meeting", "recording-001", "session-001"));
    {
        CustodyBytes exhausted;
        exhausted.resize(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
        bool refused = false;
        try { (void)DesktopApiClient::idempotencyKey<CustodyString>("meeting", "recording-001", "session-001"); }
        catch (const std::bad_alloc&) { refused = true; }
        assert(refused && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
    }
    const auto timed = DesktopApiClient::createMeetingRequest(
        "recording-001", "recording-001--initial", 60, startedAtMs, startedAtMs + 61'000, 180);
    assert(timed.has_value());
    assert(timed->hasTimeline());
    assert(timed->title == "Meeting - 2026-09-18 12:05");
    assert(timed->titleSource == "generic");
    assert(timed->startedAtIso == "2026-09-18T09:05:00Z");
    assert(timed->endedAtIso == "2026-09-18T09:06:01Z");
    assert(timed->displayTimezoneOffsetMinutes == 180);
    // A negative offset crossing midnight, and an implausible offset rejected.
    assert(DesktopApiClient::formatDisplayMinute(startedAtMs, -300) == "2026-09-18 04:05");
    assert(DesktopApiClient::formatDisplayMinute(startedAtMs, 15 * 60).empty());
    assert(DesktopApiClient::formatDisplayMinute(startedAtMs, 0) == "2026-09-18 09:05");
    assert(DesktopApiClient::formatUtcInstant(0).empty());
    assert(DesktopApiClient::formatUtcInstant(startedAtMs) == "2026-09-18T09:05:00Z");
    const auto reordered = DesktopApiClient::createMeetingRequest(
        "recording-001", "recording-001--initial", 60, startedAtMs, startedAtMs - 1, 180);
    assert(reordered.has_value() && !reordered->hasTimeline() && reordered->title.empty());
    // The exact bytes on the wire, so a renamed or dropped field cannot pass as
    // a working upload. Optional fields stay absent rather than becoming null.
    assert(DesktopApiClient::createMeetingBody(*meeting) ==
           "{\"local_recording_id\":\"recording-001\",\"local_media_revision_id\":\"recording-001--initial\","
           "\"source_kind\":\"initial_mixed_recording\",\"media_scribe_source_mode\":\"single_wav_v1\","
           "\"duration_seconds\":60}");
    assert(DesktopApiClient::createMeetingBody(*timed) ==
           "{\"local_recording_id\":\"recording-001\",\"local_media_revision_id\":\"recording-001--initial\","
           "\"source_kind\":\"initial_mixed_recording\",\"media_scribe_source_mode\":\"single_wav_v1\","
           "\"duration_seconds\":60,\"title\":\"Meeting - 2026-09-18 12:05\",\"title_source\":\"generic\","
           "\"started_at\":\"2026-09-18T09:05:00Z\",\"ended_at\":\"2026-09-18T09:06:01Z\","
           "\"recording_display_timezone_offset_minutes\":180}");
    assert(DesktopApiClient::createMeetingBody(*reordered) == DesktopApiClient::createMeetingBody(*meeting));
    const auto upload = DesktopApiClient::uploadSessionRequest(
        std::array<std::uint64_t, 3>{100, 200, 300},
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef");
    assert(upload.has_value());
    assert(upload->expectedTracks[1] == "media");
    const auto chargedUpload = DesktopApiClient::uploadSessionRequest<CustodyString>(upload->expectedTrackSizes, upload->manifestSha256);
    assert(chargedUpload && chargedUpload->expectedTracks == upload->expectedTracks &&
        chargedUpload->expectedTrackSizes == upload->expectedTrackSizes &&
        std::string_view(chargedUpload->manifestSha256) == upload->manifestSha256);
    assert(DesktopApiClient::idempotencyKey("meeting", "recording-001", "session-001") ==
           "desktop-upload:meeting:recording-001:session-001");

    // T119: untrusted resolver data, not permission to open a URL or record.
    constexpr auto eventId = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
    constexpr auto upperId = "AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE";
    const auto joinBody = [](std::string_view id, std::string_view family, std::string_view url) {
        return "{\"event_id\":\"" + std::string(id) + "\",\"provider_family\":\"" +
            std::string(family) + "\",\"https_url\":\"" + std::string(url) + "\"}";
    };
    const auto body = joinBody(eventId, "calendar", "https://example.test:443/meeting?room=1#join");
    assert(DesktopApiClient::calendarJoinTargetPath(upperId) ==
        "/api/v1/calendar/events/aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee/join-target");
    for (const auto invalidId : {"", "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee?x=1",
         "{aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee}", "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeeg"}) {
        assert(DesktopApiClient::calendarJoinTargetPath(invalidId).empty());
        assert(!DesktopApiClient::decodeCalendarJoinTarget(body, invalidId));
    }
    const auto target = DesktopApiClient::decodeCalendarJoinTarget(body, upperId);
    assert(target && target->eventId == eventId && target->providerFamily == "calendar");
    assert(target->httpsUrl == "https://example.test:443/meeting?room=1#join");
    assert(DesktopApiClient::decodeCalendarJoinTarget(joinBody(upperId, "unknown", "https://zoom.us/j/1"), eventId));
    assert(DesktopApiClient::decodeCalendarJoinTarget(
        joinBody("00000000-0000-0000-0000-000000000000", "calendar", "https://example.test"),
        "00000000-0000-0000-0000-000000000000"));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(body, "11111111-2222-4333-8444-555555555555"));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(joinBody("bad", "calendar", "https://example.test"), eventId));
    for (const auto invalidBody : {"{}", "[]", "null", "{\"event_id\":true}",
        "{\"event_id\":\"aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee\",\"provider_family\":null,\"https_url\":\"x\"}",
        "{\"event_id\":\"aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee\",\"provider_family\":\"calendar\",\"https_url\":{}}"}) {
        assert(!DesktopApiClient::decodeCalendarJoinTarget(invalidBody, eventId));
    }
    for (const auto suffix : {",\"event_id\":\"aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee\"}",
         ",\"provider_family\":\"calendar\"}", ",\"https_url\":\"https://example.test\"}"}) {
        assert(!DesktopApiClient::decodeCalendarJoinTarget(body.substr(0, body.size() - 1) + suffix, eventId));
    }
    assert(!DesktopApiClient::decodeCalendarJoinTarget(body + "{}", eventId));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(joinBody(eventId, "\xc0\xaf", "https://example.test"), eventId));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(joinBody(eventId, "calendar", "\\uD800"), eventId));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(joinBody(eventId, "calendar", "\\u0000"), eventId));
    const auto unicode = DesktopApiClient::decodeCalendarJoinTarget(
        joinBody(eventId, "\\u043a", "https:\\/\\/example.test/?x=\\uD83D\\uDE00#join"), eventId);
    assert(unicode && unicode->providerFamily == "\xd0\xba" &&
        unicode->httpsUrl == "https://example.test/?x=\xf0\x9f\x98\x80#join");
    assert(DesktopApiClient::decodeCalendarJoinTarget(joinBody(eventId, std::string(64, 'c'), "x"), eventId));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(joinBody(eventId, std::string(65, 'c'), "x"), eventId));
    std::string escapedUrl;
    for (int i = 0; i < 8192; ++i) escapedUrl += "\\u0061";
    const auto longTarget = DesktopApiClient::decodeCalendarJoinTarget(joinBody(eventId, "calendar", escapedUrl), eventId);
    assert(longTarget && longTarget->httpsUrl == std::string(8192, 'a'));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(joinBody(eventId, "calendar", std::string(8193, 'a')), eventId));
    const auto boundedBody = body + std::string(65536 - body.size(), ' ');
    assert(DesktopApiClient::decodeCalendarJoinTarget(boundedBody, eventId));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(boundedBody + " ", eventId));
    // Future response metadata is ignored, never interpreted as authority.
    std::string nested = "0";
    for (int i = 0; i < 7; ++i) nested = "[" + nested + "]";
    const auto withExtra = [&](std::string_view value) {
        return body.substr(0, body.size() - 1) + ",\"extra\":" + std::string(value) + "}";
    };
    assert(DesktopApiClient::decodeCalendarJoinTarget(withExtra(nested), eventId));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(withExtra("[" + nested + "]"), eventId));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(withExtra("{\"a\":1,\"a\":2}"), eventId));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(withExtra("\"\xc0\xaf\""), eventId));
    assert(DesktopApiClient::decodeCalendarJoinTarget(withExtra("\"\\u0000\""), eventId));
    const auto extraRoot = [&](std::string_view fields) {
        return body.substr(0, body.size() - 1) + "," + std::string(fields) + "}";
    };
    assert(DesktopApiClient::decodeCalendarJoinTarget(extraRoot("\"\\u0065xtra\":0"), eventId));
    assert(DesktopApiClient::decodeCalendarJoinTarget(withExtra("{\"\\u0061\":0}"), eventId));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(extraRoot("\"extra\":0,\"\\u0065xtra\":1"), eventId));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(withExtra("{\"a\":0,\"\\u0061\":1}"), eventId));
    assert(!DesktopApiClient::decodeCalendarJoinTarget(extraRoot("\"\\u0065vent_id\":\"aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee\""), eventId));
    auto escapedKnown = body;
    escapedKnown.replace(2, 1, "\\u0065");
    assert(DesktopApiClient::decodeCalendarJoinTarget(escapedKnown, eventId));
    // Existing auth/upload callers keep the old raw-key policy.
    assert(!DesktopApiClient::jsonObjectFields("{\"\\u0061\":0}"));
    return 0;
}
