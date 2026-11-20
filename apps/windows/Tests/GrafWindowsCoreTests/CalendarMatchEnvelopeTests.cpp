#include "../../RecApp/Storage/CalendarMatchEnvelope.h"
#include "../../RecApp/Storage/ProtectedCustodyPrimitives.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    using Intent = CalendarMatchIntent;
    constexpr std::string_view recording = "33333333-3333-4333-8333-333333333333";
    constexpr std::string_view selectedEvent = "44444444-4444-4444-8444-444444444444";
    constexpr std::string_view calendarUser = "11111111-1111-4111-8111-111111111111";
    constexpr std::string_view calendarWorkspace = "22222222-2222-4222-8222-222222222222";
    const CalendarMatchScope calendarScope{"https://graf.test", calendarUser, calendarWorkspace, recording};
    auto otherScope = calendarScope;
    otherScope.recordingId = "../recording";
    assert(sealCalendarMatchDecision(otherScope, Intent::automatic, {}).error == CustodyCodecError::invalidInput);
    assert(sealCalendarMatchDecision(calendarScope, Intent::userSelected, {}).error == CustodyCodecError::invalidInput);
    assert(sealCalendarMatchDecision(calendarScope, Intent::userDeclined, selectedEvent).error == CustodyCodecError::invalidInput);
    assert(openCalendarMatchDecision(calendarScope, {}).error == CustodyCodecError::invalidEnvelope);
    assert(openCalendarMatchDecision(calendarScope, CustodyBytes(calendarMatchEnvelopeLimit + 1)).error ==
        CustodyCodecError::invalidEnvelope);

    constexpr std::string_view device = "55555555-5555-4555-8555-555555555555";
    constexpr std::string_view attempt = "66666666-6666-4666-8666-666666666666";
    const CalendarMatchReplayScope replayScope{calendarScope, device, "revision--initial"};
    const CalendarMatchDecision selected{Intent::userSelected, CustodyString(selectedEvent)};
    const CalendarMatchDecision declined{Intent::userDeclined, {}};
    const CalendarMatchReplayInput input{attempt, 1730000123.125, 64, 1730000000000, 1730000064000, 180};
    for (const auto invalid : {
        CalendarMatchReplayInput{"bad", input.expiresAt, 64, input.startedAtMs, input.stoppedAtMs, 180},
        CalendarMatchReplayInput{attempt, 0.0001, 64, input.startedAtMs, input.stoppedAtMs, 180},
        CalendarMatchReplayInput{attempt, 1e100, 64, input.startedAtMs, input.stoppedAtMs, 180},
        CalendarMatchReplayInput{attempt, input.expiresAt, 0, input.startedAtMs, input.stoppedAtMs, 180},
        CalendarMatchReplayInput{attempt, input.expiresAt, 64, 0, input.stoppedAtMs, 180},
        CalendarMatchReplayInput{attempt, input.expiresAt, 64, input.startedAtMs, input.startedAtMs - 1, 180},
        CalendarMatchReplayInput{attempt, input.expiresAt, 64, input.startedAtMs, input.startedAtMs + 999, 180},
        CalendarMatchReplayInput{attempt, input.expiresAt, 64, 9223372036854775807ULL, 9223372036854776807ULL, 1},
        CalendarMatchReplayInput{attempt, input.expiresAt, 64, input.startedAtMs, 253402300800000ULL, 0},
        CalendarMatchReplayInput{attempt, input.expiresAt, 64, input.startedAtMs, input.stoppedAtMs, 841},
    }) assert(sealCalendarMatchReplay(replayScope, selected, invalid).error == CustodyCodecError::invalidInput);
    const CalendarMatchDecision automatic{Intent::automatic, {}};
    assert(sealCalendarMatchReplay(replayScope, automatic, input).error == CustodyCodecError::invalidInput);
    auto invalidScope = replayScope;
    invalidScope.deviceId = "bad";
    assert(sealCalendarMatchReplay(invalidScope, selected, input).error == CustodyCodecError::invalidInput);
    invalidScope = replayScope;
    invalidScope.revisionId = "revision&param";
    assert(sealCalendarMatchReplay(invalidScope, selected, input).error == CustodyCodecError::invalidInput);
    assert(openCalendarMatchReplay(replayScope, selected, CustodyBytes(calendarMatchEnvelopeLimit + 1)).error ==
        CustodyCodecError::invalidEnvelope);
#ifdef _WIN32
    constexpr std::string_view otherId = "55555555-5555-4555-8555-555555555555";
    for (const auto intent : {Intent::automatic, Intent::userSelected, Intent::userDeclined}) {
        const auto event = intent == Intent::userSelected ? selectedEvent : std::string_view{};
        const auto sealed = sealCalendarMatchDecision(calendarScope, intent, event);
        assert(sealed.ok() && sealed.value->size() <= calendarMatchEnvelopeLimit);
        const auto opened = openCalendarMatchDecision(calendarScope, *sealed.value);
        assert(opened.ok() && opened.value->intent == intent && std::string_view(opened.value->eventId) == event);
        for (const auto& foreign : {
            CalendarMatchScope{"https://other.test", calendarUser, calendarWorkspace, recording},
            CalendarMatchScope{calendarScope.origin, otherId, calendarWorkspace, recording},
            CalendarMatchScope{calendarScope.origin, calendarUser, otherId, recording},
            CalendarMatchScope{calendarScope.origin, calendarUser, calendarWorkspace, otherId},
        }) assert(!openCalendarMatchDecision(foreign, *sealed.value).ok());
        CustodyBytes truncated(sealed.value->begin(), sealed.value->begin() + sealed.value->size() / 2);
        assert(!openCalendarMatchDecision(calendarScope, truncated).ok());
    }

    // A version-1 automatic payload with a valid shape and a deliberately wrong digest.
    std::string entropy = "GRAF/windows/calendar-match/decision/v1";
    entropy.push_back(0);
    entropy.append(calendarScope.origin).push_back(0);
    entropy.append(calendarUser).append(calendarWorkspace).append(recording);
    const auto* scopeBytes = reinterpret_cast<const std::uint8_t*>(entropy.data());
    CustodyBytes badDigest(34, 0);
    badDigest[0] = 1;
    badDigest[1] = 1;
    const auto bad = custody_detail::nativeTransform(scopeBytes, entropy.size(), badDigest.data(), badDigest.size(),
        calendarMatchEnvelopeLimit, true);
    assert(bad.ok());
    const auto nativeOpened = custody_detail::nativeTransform(scopeBytes, entropy.size(),
        bad.value->data(), bad.value->size(), badDigest.size(), false, badDigest.size());
    assert(nativeOpened.ok() && *nativeOpened.value == badDigest);
    assert(openCalendarMatchDecision(calendarScope, *bad.value).error == CustodyCodecError::invalidPlaintext);

    for (const auto* decision : {&selected, &declined}) {
        const auto sealed = sealCalendarMatchReplay(replayScope, *decision, input);
        assert(sealed.ok());
        const auto& envelope = sealed.value->envelope;
        const auto replay = openCalendarMatchReplay(replayScope, *decision, envelope);
        assert(replay.ok() && replay.value->attemptId == attempt && replay.value->expiresAtMs == 1730000123125);
        const auto request = DesktopApiClient::createMeetingRequest<CustodyString>(
            recording, replayScope.revisionId, input.durationSeconds, input.startedAtMs, input.stoppedAtMs,
            input.displayTimezoneOffsetMinutes, attempt);
        assert(request && replay.value->body == DesktopApiClient::createMeetingBody(*request));
        assert(replay.value->idempotencyKey ==
            DesktopApiClient::idempotencyKey<CustodyString>("calendar-meeting", recording, attempt));
        assert(replay.value->body == sealed.value->replay.body && replay.value->idempotencyKey == sealed.value->replay.idempotencyKey);
        assert(!openCalendarMatchReplay(replayScope, decision == &selected ? declined : selected, envelope).ok());
        const CalendarMatchDecision otherEvent{Intent::userSelected, CustodyString(otherId)};
        assert(!openCalendarMatchReplay(replayScope, otherEvent, envelope).ok());
        assert(!openCalendarMatchDecision(calendarScope, envelope).ok());
        const auto decisionBytes = sealCalendarMatchDecision(calendarScope, decision->intent, decision->eventId);
        assert(decisionBytes.ok() && !openCalendarMatchReplay(replayScope, *decision, *decisionBytes.value).ok());
        assert(!openCalendarMatchReplay(replayScope, *decision,
            CustodyBytes(envelope.begin(), envelope.begin() + envelope.size() / 2)).ok());
        for (const auto& other : {
            CalendarMatchReplayScope{{"https://other.test", calendarUser, calendarWorkspace, recording}, device, replayScope.revisionId},
            CalendarMatchReplayScope{{calendarScope.origin, otherId, calendarWorkspace, recording}, device, replayScope.revisionId},
            CalendarMatchReplayScope{{calendarScope.origin, calendarUser, otherId, recording}, device, replayScope.revisionId},
            CalendarMatchReplayScope{{calendarScope.origin, calendarUser, calendarWorkspace, otherId}, device, replayScope.revisionId},
            CalendarMatchReplayScope{calendarScope, selectedEvent, replayScope.revisionId},
            CalendarMatchReplayScope{calendarScope, device, "revision--other"},
        }) assert(!openCalendarMatchReplay(other, *decision, envelope).ok());
    }

    std::string replayEntropy = "GRAF/windows/calendar-match/create/v1";
    replayEntropy.push_back(0);
    replayEntropy.append(calendarScope.origin).push_back(0);
    replayEntropy.append(calendarUser).append(calendarWorkspace).append(recording);
    replayEntropy.append(device).append(replayScope.revisionId).push_back(0);
    replayEntropy.push_back(2);
    replayEntropy.append(selectedEvent);
    const auto* replayScopeBytes = reinterpret_cast<const std::uint8_t*>(replayEntropy.data());
    const auto validReplay = sealCalendarMatchReplay(replayScope, selected, input);
    assert(validReplay.ok());
    const auto& validEnvelope = validReplay.value->envelope;
    const auto decoded = custody_detail::nativeTransform(replayScopeBytes, replayEntropy.size(),
        validEnvelope.data(), validEnvelope.size(), calendarMatchEnvelopeLimit, false);
    assert(decoded.ok() && decoded.value->size() > 46 + 32);
    auto payload = *decoded.value;
    payload.resize(payload.size() - 32);
    const auto rejectRaw = [&](CustodyBytes bytes, bool validDigest = true) {
        const auto hash = custody_detail::digest(bytes.data(), bytes.size());
        assert(hash);
        bytes.insert(bytes.end(), hash->begin(), hash->end());
        if (!validDigest) bytes.back() ^= 1;
        const auto sealed = custody_detail::nativeTransform(replayScopeBytes, replayEntropy.size(),
            bytes.data(), bytes.size(), calendarMatchEnvelopeLimit, true);
        assert(sealed.ok());
        assert(openCalendarMatchReplay(replayScope, selected, *sealed.value).error == CustodyCodecError::invalidPlaintext);
    };
    rejectRaw(payload, false);
    auto unknown = payload;
    unknown[0] = 2;
    rejectRaw(unknown);
    auto oversizedKey = payload;
    oversizedKey[45] = 161;
    rejectRaw(oversizedKey);
    auto oversizedBody = payload;
    oversizedBody.resize(46 + oversizedBody[45] + 2049, 'x');
    rejectRaw(oversizedBody);
#endif
}
