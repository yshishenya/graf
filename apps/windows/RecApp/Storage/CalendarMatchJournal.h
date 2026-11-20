#pragma once

#include "CalendarMatchEnvelope.h"
#include <filesystem>
#include <memory>

namespace graf::windows {

enum class CalendarJournalState {
    committed, absent, conflict, invalidInput, invalidEnvelope, authenticationFailed, unavailable, publicationUnconfirmed,
};

template<class Value> struct CalendarJournalReadValue {
    CalendarJournalState state;
    std::optional<Value> value;
};
struct CalendarJournalRead {
    CalendarJournalState state;
    std::optional<CalendarMatchDecision> decision;
};
using CalendarReplayRead = CalendarJournalReadValue<CalendarMatchReplay>;

// Worker-only. Provision before the protected owner pins GRAF's ancestors.
class CalendarMatchJournal final {
public:
    [[nodiscard]] static std::unique_ptr<CalendarMatchJournal> prepare(const std::filesystem::path& grafLocalRoot) noexcept;
    ~CalendarMatchJournal();
    [[nodiscard]] bool belongsTo(const std::filesystem::path& grafLocalRoot) const noexcept;
    [[nodiscard]] CalendarJournalRead read(const CalendarMatchScope&) const;
    [[nodiscard]] CalendarJournalState commit(
        const CalendarMatchScope&, CalendarMatchIntent, std::string_view eventId) const;
    [[nodiscard]] CalendarReplayRead readReplay(const CalendarMatchReplayScope&,
        std::optional<CalendarMatchIntent> expectedIntent = {}) const;
    [[nodiscard]] CalendarJournalState commitReplay(
        const CalendarMatchReplayScope&, const CalendarMatchReplayInput&) const;
private:
    struct Lease;
    explicit CalendarMatchJournal(std::unique_ptr<Lease>) noexcept;
    std::unique_ptr<Lease> lease_;
};

} // namespace graf::windows
