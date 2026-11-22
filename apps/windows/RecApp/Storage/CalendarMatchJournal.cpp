#include "CalendarMatchJournal.h"

#ifdef _WIN32
#include "PrivateLocalFiles.h"
#include <objbase.h>
#endif

namespace graf::windows {
#ifdef GRAF_WINDOWS_TEST_CALENDAR_JOURNAL_FLUSH
extern unsigned grafCalendarJournalTestFlushFailure;
extern void (*grafCalendarJournalTestBeforePublish)();
extern void (*grafCalendarJournalTestAfterReplayFlush)();
#endif
namespace {
using State = CalendarJournalState;
#ifdef _WIN32
using namespace local_file_detail;
constexpr auto nameMissing = static_cast<NTSTATUS>(0xC0000034L);
constexpr auto folderName = L"calendar-match";
constexpr ACCESS_MASK folderAccess = directoryFlushAccess | FILE_TRAVERSE | FILE_READ_ATTRIBUTES;
constexpr DWORD shareDirectory = FILE_SHARE_READ | FILE_SHARE_WRITE;


bool confirmPublication(HANDLE journal, [[maybe_unused]] std::wstring_view suffix) {
#ifdef GRAF_WINDOWS_TEST_CALENDAR_JOURNAL_FLUSH
    if ((grafCalendarJournalTestFlushFailure == 1 && suffix == L".decision") ||
        (grafCalendarJournalTestFlushFailure == 3 && suffix == L".create")) return false;
#endif
    const bool flushed = FlushFileBuffers(journal) != FALSE;
#ifdef GRAF_WINDOWS_TEST_CALENDAR_JOURNAL_FLUSH
    if (flushed && suffix == L".create" && grafCalendarJournalTestAfterReplayFlush)
        grafCalendarJournalTestAfterReplayFlush();
#endif
    return flushed;
}

const auto acceptExisting = [](const auto&) { return true; };

template<class Value, class Open, class Matches>
CalendarJournalReadValue<Value> useJournal(HANDLE folder, const CalendarMatchScope& scope,
    std::wstring_view suffix, const CustodyBytes* staged, Open open, Matches matches) {
    if (!validCalendarMatchScope(scope)) return {State::invalidInput, {}};
    if (!privateObject(folder, true)) return {State::unavailable, {}};
    NTSTATUS status = 0;
    auto name = std::wstring(scope.recordingId.begin(), scope.recordingId.end());
    name += suffix;
    auto observe = [&]() -> CalendarJournalReadValue<Value> {
        auto file = openRelative(folder, name, FILE_READ_DATA | FILE_READ_ATTRIBUTES | READ_CONTROL,
            FILE_SHARE_READ, FILE_OPEN, FILE_NON_DIRECTORY_FILE, nullptr, &status);
        if (!file) return {status == nameMissing ? State::absent : State::unavailable, {}};
        if (!privateObject(file.value, false)) return {State::unavailable, {}};
        LARGE_INTEGER size{};
        if (!GetFileSizeEx(file.value, &size)) return {State::unavailable, {}};
        if (size.QuadPart <= 0 || size.QuadPart > static_cast<LONGLONG>(calendarMatchEnvelopeLimit))
            return {State::invalidEnvelope, {}};
        CustodyBytes bytes(static_cast<std::size_t>(size.QuadPart));
        DWORD read = 0;
        if (!ReadFile(file.value, bytes.data(), static_cast<DWORD>(bytes.size()), &read, nullptr) || read != bytes.size())
            return {State::unavailable, {}};
        auto opened = open(bytes);
        if (!opened.ok()) {
            switch (opened.error) {
            case CustodyCodecError::nativeFailed: return {State::authenticationFailed, {}};
            case CustodyCodecError::invalidEnvelope:
            case CustodyCodecError::invalidPlaintext: return {State::invalidEnvelope, {}};
            default: return {State::unavailable, {}};
            }
        }
        if (staged && !matches(*opened.value))
            return {State::conflict, {}};
        if (!confirmPublication(folder, suffix)) return {State::publicationUnconfirmed, {}};
        return {State::committed, std::move(opened.value)};
    };
    auto existing = observe();
    if (!staged || existing.state != State::absent) return existing;

    GUID id{};
    wchar_t temp[40]{};
    PrivateSecurity security;
    if (FAILED(CoCreateGuid(&id)) || !StringFromGUID2(id, temp, ARRAYSIZE(temp)) ||
        !security.initialize(false, true)) return {State::unavailable, {}};
    NTSTATUS publish = 0;
    {
        StagedFile pending{openRelative(folder, temp, FILE_WRITE_DATA | FILE_READ_ATTRIBUTES | READ_CONTROL | DELETE,
            0, FILE_CREATE, FILE_NON_DIRECTORY_FILE, security.descriptor.value)};
        DWORD written = 0;
        if (!pending.file || !privateObject(pending.file.value, false) ||
            !WriteFile(pending.file.value, staged->data(), static_cast<DWORD>(staged->size()), &written, nullptr) ||
            written != staged->size() || !FlushFileBuffers(pending.file.value)) return {State::unavailable, {}};
#ifdef GRAF_WINDOWS_TEST_CALENDAR_JOURNAL_FLUSH
        if (grafCalendarJournalTestBeforePublish) grafCalendarJournalTestBeforePublish();
#endif
        publish = renameNoReplace(pending.file.value, name);
        if (publish == 0) {
            pending.published = true;
            return {confirmPublication(folder, suffix) ? State::committed : State::publicationUnconfirmed, {}};
        }
    }
    if (publish != nameCollision) return {State::unavailable, {}};
    auto winner = observe();
    return winner.state == State::absent ? CalendarJournalReadValue<Value>{State::unavailable, {}} : std::move(winner);
}
#endif
} // namespace

struct CalendarMatchJournal::Lease {
    std::filesystem::path root;
#ifdef _WIN32
    std::vector<local_file_detail::File> ancestors;
    local_file_detail::File folder;
#endif
};

CalendarMatchJournal::CalendarMatchJournal(std::unique_ptr<Lease> lease) noexcept : lease_(std::move(lease)) {}
CalendarMatchJournal::~CalendarMatchJournal() = default;

bool CalendarMatchJournal::belongsTo(const std::filesystem::path& root) const noexcept {
    return lease_->root == root;
}

std::unique_ptr<CalendarMatchJournal> CalendarMatchJournal::prepare(const std::filesystem::path& root) noexcept {
#ifdef _WIN32
    try {
        constexpr auto birthAccess = folderAccess | FILE_ADD_SUBDIRECTORY;
        const auto name = root.filename().native();
        if (!validPathComponent(name)) return {};
        auto writableParent = pinFixedLocalDirectory(root.parent_path(), birthAccess);
        if (writableParent.empty()) return {};
        const auto parent = writableParent.back().value;
        PrivateSecurity security;
        if (!security.initialize(true, true)) return {};
        NTSTATUS status = 0;
        auto grafRoot = openRelative(parent, name, birthAccess, shareDirectory,
            FILE_OPEN, FILE_DIRECTORY_FILE, nullptr, &status);
        if (!grafRoot && status == nameMissing) {
            grafRoot = openRelative(parent, name, birthAccess, shareDirectory,
                FILE_CREATE, FILE_DIRECTORY_FILE, security.descriptor.value);
            if (!grafRoot || !privateObject(grafRoot.value, true)) return {};
        }
        if (!grafRoot || !plainObject(grafRoot.value, true)) return {};
        auto folder = openRelative(grafRoot.value, folderName, folderAccess, shareDirectory,
            FILE_OPEN_IF, FILE_DIRECTORY_FILE, security.descriptor.value);
        if (!folder || !privateObject(folder.value, true) || !FlushFileBuffers(folder.value)) return {};
#ifdef GRAF_WINDOWS_TEST_CALENDAR_JOURNAL_FLUSH
        if (grafCalendarJournalTestFlushFailure == 2) return {};
#endif
        // A prior attempt may have created either directory without confirming its entry.
        if (!FlushFileBuffers(grafRoot.value) || !FlushFileBuffers(parent)) return {};
        auto ancestors = pinFixedLocalDirectory(root);
        if (ancestors.empty()) return {};
        auto lease = std::make_unique<Lease>();
        lease->root = root;
        lease->ancestors = std::move(ancestors);
        lease->folder = std::move(folder);
        // Ancestor write handles are local; they close before the custody owner opens.
        return std::unique_ptr<CalendarMatchJournal>(new CalendarMatchJournal(std::move(lease)));
    } catch (...) { return {}; }
#else
    (void)root;
    return {};
#endif
}

CalendarJournalRead CalendarMatchJournal::read(const CalendarMatchScope& scope) const {
#ifdef _WIN32
    try {
        auto observed = useJournal<CalendarMatchDecision>(lease_->folder.value, scope, L".decision", nullptr,
            [&](const auto& bytes) { return openCalendarMatchDecision(scope, bytes); }, acceptExisting);
        return {observed.state, std::move(observed.value)};
    } catch (...) { return {State::unavailable, {}}; }
#else
    (void)scope;
    return {State::unavailable, {}};
#endif
}

CalendarJournalState CalendarMatchJournal::commit(const CalendarMatchScope& scope,
    CalendarMatchIntent intent, std::string_view eventId) const {
#ifdef _WIN32
    try {
        const auto sealed = sealCalendarMatchDecision(scope, intent, eventId);
        if (!sealed.ok()) return sealed.error == CustodyCodecError::invalidInput ? State::invalidInput : State::unavailable;
        return useJournal<CalendarMatchDecision>(lease_->folder.value, scope, L".decision", &*sealed.value,
            [&](const auto& bytes) { return openCalendarMatchDecision(scope, bytes); },
            [&](const auto& decision) {
                return decision.intent == intent && std::string_view(decision.eventId) == eventId;
            }).state;
    } catch (...) { return State::unavailable; }
#else
    (void)scope; (void)intent; (void)eventId;
    return State::unavailable;
#endif
}

CalendarReplayRead CalendarMatchJournal::readReplay(const CalendarMatchReplayScope& scope,
    std::optional<CalendarMatchIntent> expectedIntent) const {
#ifdef _WIN32
    try {
        const auto choice = read(scope.recording);
        if (!choice.decision) return {choice.state, {}};
        if (expectedIntent && choice.decision->intent != *expectedIntent) return {State::conflict, {}};
        return useJournal<CalendarMatchReplay>(lease_->folder.value, scope.recording, L".create", nullptr,
            [&](const auto& bytes) { return openCalendarMatchReplay(scope, *choice.decision, bytes); }, acceptExisting);
    } catch (...) { return {State::unavailable, {}}; }
#else
    (void)scope; (void)expectedIntent;
    return {State::unavailable, {}};
#endif
}

CalendarJournalState CalendarMatchJournal::commitReplay(const CalendarMatchReplayScope& scope,
    const CalendarMatchReplayInput& input) const {
#ifdef _WIN32
    try {
        const auto choice = read(scope.recording);
        if (!choice.decision) return choice.state;
        const auto staged = sealCalendarMatchReplay(scope, *choice.decision, input);
        if (!staged.ok()) return staged.error == CustodyCodecError::invalidInput ? State::invalidInput : State::unavailable;
        const auto open = [&](const auto& bytes) { return openCalendarMatchReplay(scope, *choice.decision, bytes); };
        const auto& proposed = staged.value->replay;
        return useJournal<CalendarMatchReplay>(lease_->folder.value, scope.recording, L".create", &staged.value->envelope, open,
            [&](const auto& existing) {
                return existing.attemptId == proposed.attemptId && existing.expiresAtMs == proposed.expiresAtMs &&
                    existing.idempotencyKey == proposed.idempotencyKey && existing.body == proposed.body;
            }).state;
    } catch (...) { return State::unavailable; }
#else
    (void)scope; (void)input;
    return State::unavailable;
#endif
}

} // namespace graf::windows
