#include "CalendarMatchEnvelope.h"
#include "ProtectedCustodyPrimitives.h"
#include "../Upload/DesktopUploadQueueService.h"

#include <algorithm>

namespace graf::windows {
namespace {
using Error = CustodyCodecError;
using Intent = CalendarMatchIntent;

constexpr std::uint8_t formatVersion = 1;
constexpr std::size_t headerSize = 2, uuidSize = 36, digestSize = 32;
constexpr std::size_t maximumPlaintext = headerSize + uuidSize + digestSize;

std::optional<CustodyBytes> scopeEntropy(const CalendarMatchScope& scope,
    std::string_view domain = "GRAF/windows/calendar-match/decision/v1") {
    if (!validCalendarMatchScope(scope)) return std::nullopt;
    CustodyBytes entropy;
    entropy.reserve(domain.size() + scope.origin.size() + 2 + 3 * uuidSize);
    entropy.insert(entropy.end(), domain.begin(), domain.end());
    entropy.push_back(0);
    entropy.insert(entropy.end(), scope.origin.begin(), scope.origin.end());
    entropy.push_back(0);
    for (const auto id : {scope.userId, scope.workspaceId, scope.recordingId})
        entropy.insert(entropy.end(), id.begin(), id.end());
    return entropy;
}

constexpr std::uint8_t replayVersion = 1;
constexpr std::size_t expirySize = sizeof(std::uint64_t), replayHeaderSize = 1 + expirySize + uuidSize + 1;
constexpr std::size_t replayKeyLimit = 160;
constexpr auto replayPlaintextLimit = replayHeaderSize + replayKeyLimit + calendarMatchReplayBodyLimit + digestSize;
constexpr std::uint64_t maxUtcMs = 253402300799999ULL; // Last millisecond of year 9999.

std::optional<CustodyBytes> replayEntropy(const CalendarMatchReplayScope& scope,
    const CalendarMatchDecision& decision) {
    const bool selected = decision.intent == Intent::userSelected;
    if ((!selected && decision.intent != Intent::userDeclined) ||
        (selected ? !DesktopApiClient::accountId(decision.eventId) : !decision.eventId.empty()) ||
        scope.recording.origin.substr(0, 8) != "https://" || !DesktopApiClient::accountId(scope.deviceId) ||
        scope.revisionId.empty() || scope.revisionId.size() > 300 ||
        scope.revisionId.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_") !=
            std::string_view::npos) return std::nullopt;
    auto entropy = scopeEntropy(scope.recording, "GRAF/windows/calendar-match/create/v1");
    if (!entropy) return std::nullopt;
    entropy->insert(entropy->end(), scope.deviceId.begin(), scope.deviceId.end());
    entropy->insert(entropy->end(), scope.revisionId.begin(), scope.revisionId.end());
    entropy->push_back(0);
    entropy->push_back(selected ? 2 : 3);
    entropy->insert(entropy->end(), decision.eventId.begin(), decision.eventId.end());
    return entropy;
}

CustodyCodecResult<CustodyBytes> protect(const CustodyBytes& entropy, CustodyBytes& plaintext) {
    const auto hash = custody_detail::digest(plaintext.data(), plaintext.size());
    if (!hash) return {std::nullopt, Error::hashFailed, 0};
    plaintext.insert(plaintext.end(), hash->begin(), hash->end());
    return custody_detail::nativeTransform(entropy.data(), entropy.size(), plaintext.data(),
        plaintext.size(), calendarMatchEnvelopeLimit, true);
}
} // namespace

bool validCalendarMatchScope(const CalendarMatchScope& scope) noexcept {
    return DesktopUploadQueueService::validServerOrigin(scope.origin) &&
        DesktopApiClient::accountId(scope.userId) && DesktopApiClient::accountId(scope.workspaceId) &&
        DesktopApiClient::accountId(scope.recordingId);
}

CustodyCodecResult<CustodyBytes> sealCalendarMatchDecision(
    const CalendarMatchScope& scope, Intent intent, std::string_view eventId) {
    const auto entropy = scopeEntropy(scope);
    const std::uint8_t decision = intent == Intent::automatic ? 1 :
        intent == Intent::userSelected ? 2 : intent == Intent::userDeclined ? 3 : 0;
    if (!entropy || decision == 0 ||
        (intent == Intent::userSelected ? !DesktopApiClient::accountId(eventId) : !eventId.empty()))
        return {std::nullopt, Error::invalidInput, 0};
    CustodyBytes plaintext;
    plaintext.reserve(maximumPlaintext);
    plaintext.push_back(formatVersion);
    plaintext.push_back(decision);
    plaintext.insert(plaintext.end(), eventId.begin(), eventId.end());
    return protect(*entropy, plaintext);
}

CustodyCodecResult<CalendarMatchDecision> openCalendarMatchDecision(
    const CalendarMatchScope& scope, const CustodyBytes& envelope) {
    const auto entropy = scopeEntropy(scope);
    if (!entropy) return {std::nullopt, Error::invalidInput, 0};
    if (envelope.empty() || envelope.size() > calendarMatchEnvelopeLimit)
        return {std::nullopt, Error::invalidEnvelope, 0};
    const auto opened = custody_detail::nativeTransform(entropy->data(), entropy->size(),
        envelope.data(), envelope.size(), maximumPlaintext, false);
    if (!opened.value) return {std::nullopt, opened.error, opened.nativeError};
    const auto& bytes = *opened.value;
    if (bytes.size() < headerSize + digestSize || bytes[0] != formatVersion || bytes[1] < 1 || bytes[1] > 3)
        return {std::nullopt, Error::invalidPlaintext, 0};
    const bool selected = bytes[1] == 2;
    const auto payloadSize = headerSize + (selected ? uuidSize : 0);
    if (bytes.size() != payloadSize + digestSize)
        return {std::nullopt, Error::invalidPlaintext, 0};
    // DPAPI can report success on corrupted data; independently check the payload.
    const auto hash = custody_detail::digest(bytes.data(), payloadSize);
    if (!hash) return {std::nullopt, Error::hashFailed, 0};
    if (!std::equal(hash->begin(), hash->end(), bytes.data() + payloadSize))
        return {std::nullopt, Error::invalidPlaintext, 0};
    const std::string_view event(reinterpret_cast<const char*>(bytes.data() + headerSize), selected ? uuidSize : 0);
    if (selected && !DesktopApiClient::accountId(event))
        return {std::nullopt, Error::invalidPlaintext, 0};
    const auto intent = selected ? Intent::userSelected : bytes[1] == 1 ? Intent::automatic : Intent::userDeclined;
    return {CalendarMatchDecision{intent, CustodyString(event.data(), event.size())}, Error::none, 0};
}

CustodyCodecResult<SealedCalendarMatchReplay> sealCalendarMatchReplay(const CalendarMatchReplayScope& scope,
    const CalendarMatchDecision& decision, const CalendarMatchReplayInput& input) {
    const auto entropy = replayEntropy(scope, decision);
    const auto expiryMs = input.expiresAt * 1000.0;
    if (!entropy || !(expiryMs >= 1 && expiryMs <= maxUtcMs) ||
        !DesktopApiClient::accountId(input.attemptId) || input.startedAtMs == 0 ||
        input.stoppedAtMs > maxUtcMs || input.startedAtMs / 1000 >= input.stoppedAtMs / 1000)
        return {std::nullopt, Error::invalidInput, 0};
    const auto request = DesktopApiClient::createMeetingRequest<CustodyString>(scope.recording.recordingId,
        scope.revisionId, input.durationSeconds, input.startedAtMs, input.stoppedAtMs,
        input.displayTimezoneOffsetMinutes, input.attemptId);
    if (!request || !request->hasTimeline() || request->title.empty() || request->titleSource.empty())
        return {std::nullopt, Error::invalidInput, 0};
    auto key = DesktopApiClient::idempotencyKey<CustodyString>(
        "calendar-meeting", scope.recording.recordingId, input.attemptId);
    auto body = DesktopApiClient::createMeetingBody(*request);
    if (key.empty() || key.size() > replayKeyLimit || body.size() > calendarMatchReplayBodyLimit)
        return {std::nullopt, Error::invalidInput, 0};

    CustodyBytes plaintext;
    plaintext.reserve(replayHeaderSize + key.size() + body.size() + digestSize);
    plaintext.push_back(replayVersion);
    const auto expiresAtMs = static_cast<std::uint64_t>(expiryMs);
    for (unsigned i = 0; i < expirySize; ++i)
        plaintext.push_back(static_cast<std::uint8_t>(expiresAtMs >> (8 * i)));
    plaintext.insert(plaintext.end(), input.attemptId.begin(), input.attemptId.end());
    plaintext.push_back(static_cast<std::uint8_t>(key.size()));
    plaintext.insert(plaintext.end(), key.begin(), key.end());
    plaintext.insert(plaintext.end(), body.begin(), body.end());
    auto sealed = protect(*entropy, plaintext);
    if (!sealed.ok()) return {std::nullopt, sealed.error, sealed.nativeError};
    return {SealedCalendarMatchReplay{std::move(*sealed.value),
        {CustodyString(input.attemptId), std::move(key), std::move(body), expiresAtMs}}, Error::none, 0};
}

CustodyCodecResult<CalendarMatchReplay> openCalendarMatchReplay(const CalendarMatchReplayScope& scope,
    const CalendarMatchDecision& decision, const CustodyBytes& envelope) {
    const auto entropy = replayEntropy(scope, decision);
    if (!entropy) return {std::nullopt, Error::invalidInput, 0};
    if (envelope.empty() || envelope.size() > calendarMatchEnvelopeLimit)
        return {std::nullopt, Error::invalidEnvelope, 0};
    const auto opened = custody_detail::nativeTransform(entropy->data(), entropy->size(),
        envelope.data(), envelope.size(), replayPlaintextLimit, false);
    if (!opened.value) return {std::nullopt, opened.error, opened.nativeError};
    const auto& bytes = *opened.value;
    if (bytes.size() <= replayHeaderSize + digestSize || bytes[0] != replayVersion)
        return {std::nullopt, Error::invalidPlaintext, 0};
    const auto payloadSize = bytes.size() - digestSize;
    const auto keySize = bytes[replayHeaderSize - 1];
    if (keySize == 0 || keySize > replayKeyLimit || payloadSize <= replayHeaderSize + keySize)
        return {std::nullopt, Error::invalidPlaintext, 0};
    const auto bodySize = payloadSize - replayHeaderSize - keySize;
    if (bodySize > calendarMatchReplayBodyLimit) return {std::nullopt, Error::invalidPlaintext, 0};
    const auto hash = custody_detail::digest(bytes.data(), payloadSize);
    if (!hash) return {std::nullopt, Error::hashFailed, 0};
    if (!std::equal(hash->begin(), hash->end(), bytes.data() + payloadSize))
        return {std::nullopt, Error::invalidPlaintext, 0};

    std::uint64_t expiresAtMs = 0;
    for (unsigned i = 0; i < expirySize; ++i)
        expiresAtMs |= static_cast<std::uint64_t>(bytes[i + 1]) << (8 * i);
    const auto* chars = reinterpret_cast<const char*>(bytes.data());
    const std::string_view attempt(chars + 1 + expirySize, uuidSize);
    const std::string_view key(chars + replayHeaderSize, keySize);
    const std::string_view body(key.data() + key.size(), bodySize);
    if (expiresAtMs == 0 || expiresAtMs > maxUtcMs || !DesktopApiClient::accountId(attempt) ||
        key.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:") != std::string_view::npos ||
        body.front() != '{' || body.back() != '}' || body.find('\0') != std::string_view::npos)
        return {std::nullopt, Error::invalidPlaintext, 0};
    return {CalendarMatchReplay{CustodyString(attempt), CustodyString(key), CustodyString(body), expiresAtMs},
        Error::none, 0};
}

} // namespace graf::windows
