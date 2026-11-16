#pragma once

#include "ProtectedCustodyCodec.h"
#include "../Upload/DesktopApiClient.h"

namespace graf::windows {

struct CalendarMatchScope {
    std::string_view origin, userId, workspaceId, recordingId;
};

struct CalendarMatchDecision {
    CalendarMatchIntent intent;
    CustodyString eventId;
};

struct CalendarMatchReplayScope {
    CalendarMatchScope recording;
    std::string_view deviceId, revisionId;
};

struct CalendarMatchReplayInput {
    std::string_view attemptId;
    double expiresAt; // UTC epoch seconds from the validated resolve response.
    std::uint32_t durationSeconds;
    std::uint64_t startedAtMs, stoppedAtMs;
    int displayTimezoneOffsetMinutes;
};

struct CalendarMatchReplay {
    CustodyString attemptId, idempotencyKey, body;
    std::uint64_t expiresAtMs;
};

struct SealedCalendarMatchReplay {
    CustodyBytes envelope;
    CalendarMatchReplay replay;
};

inline constexpr std::size_t calendarMatchEnvelopeLimit = 4096;
inline constexpr std::size_t calendarMatchReplayBodyLimit = 2048;

[[nodiscard]] bool validCalendarMatchScope(const CalendarMatchScope&) noexcept;

[[nodiscard]] CustodyCodecResult<CustodyBytes> sealCalendarMatchDecision(
    const CalendarMatchScope&, CalendarMatchIntent, std::string_view eventId);
[[nodiscard]] CustodyCodecResult<CalendarMatchDecision> openCalendarMatchDecision(
    const CalendarMatchScope&, const CustodyBytes&);
[[nodiscard]] CustodyCodecResult<SealedCalendarMatchReplay> sealCalendarMatchReplay(
    const CalendarMatchReplayScope&, const CalendarMatchDecision&, const CalendarMatchReplayInput&);
[[nodiscard]] CustodyCodecResult<CalendarMatchReplay> openCalendarMatchReplay(
    const CalendarMatchReplayScope&, const CalendarMatchDecision&, const CustodyBytes&);

} // namespace graf::windows
