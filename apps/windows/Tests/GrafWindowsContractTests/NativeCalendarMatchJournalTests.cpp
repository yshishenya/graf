#include "../../RecApp/Storage/CalendarMatchJournal.h"
#include "../../RecApp/Storage/PrivateLocalFiles.h"
#include <objbase.h>
#include <winioctl.h>

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <fstream>
#include <iterator>

namespace graf::windows {
unsigned grafCalendarJournalTestFlushFailure = 0;
void (*grafCalendarJournalTestBeforePublish)() = nullptr;
void (*grafCalendarJournalTestAfterReplayFlush)() = nullptr;
}

namespace {
namespace fs = std::filesystem;
using namespace graf::windows;
using local_file_detail::File;
using State = CalendarJournalState;
using Intent = CalendarMatchIntent;
constexpr CalendarMatchScope scope{"https://graf.test", "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333"};
constexpr std::string_view event = "44444444-4444-4444-8444-444444444444";
constexpr std::string_view secondId = "55555555-5555-4555-8555-555555555555";
constexpr CalendarMatchReplayScope replayScope{scope, secondId, "revision--initial"};
constexpr CalendarMatchReplayInput replayInput{
    "66666666-6666-4666-8666-666666666666", 1730000123.125, 64, 1730000000000, 1730000064000, 180};
constexpr CalendarMatchReplayInput otherReplayInput{
    "77777777-7777-4777-8777-777777777777", 1730000123.125, 64, 1730000000000, 1730000064000, 180};

std::wstring guid() {
    GUID id{};
    wchar_t text[40]{};
    assert(SUCCEEDED(CoCreateGuid(&id)) && StringFromGUID2(id, text, ARRAYSIZE(text)));
    return text;
}

struct Fixture {
    const fs::path root = fs::temp_directory_path() / (L"g104-" + guid());
    Fixture() { assert(fs::create_directory(root)); }
    ~Fixture() {
        std::error_code ignored;
        fs::remove_all(root, ignored);
    }
};

File child(const fs::path& root, std::wstring_view mode, std::wstring_view gate = {}) {
    wchar_t image[MAX_PATH]{};
    const auto count = GetModuleFileNameW(nullptr, image, ARRAYSIZE(image));
    assert(count > 0 && count < ARRAYSIZE(image));
    auto command = L"\"" + std::wstring(image) + L"\" \"" + root.native() + L"\" " + std::wstring(mode);
    if (!gate.empty()) command += L" \"" + std::wstring(gate) + L"\"";
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    assert(CreateProcessW(image, command.data(), nullptr, nullptr, FALSE, 0, nullptr, nullptr, &startup, &process));
    CloseHandle(process.hThread);
    return File(process.hProcess);
}

DWORD finish(const File& process) {
    if (WaitForSingleObject(process.value, 15000) != WAIT_OBJECT_0) {
        TerminateProcess(process.value, 1);
        assert(false && "journal child timeout");
    }
    DWORD code = 0;
    assert(GetExitCodeProcess(process.value, &code));
    return code;
}

std::string readBytes(const fs::path& file) {
    std::ifstream in(file, std::ios::binary);
    assert(in);
    return {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
}

void writeBytes(const fs::path& file, std::string_view bytes) {
    std::ofstream out(file, std::ios::binary | std::ios::trunc);
    out.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
    out.close();
    assert(out);
}

void junction(const fs::path& link, const fs::path& target) {
    assert(CreateDirectoryW(link.c_str(), nullptr));
    const File directory(CreateFileW(link.c_str(), GENERIC_WRITE, 0, nullptr, OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
    assert(directory);
    struct Reparse {
        DWORD tag; WORD length, reserved;
        WORD substituteOffset, substituteLength, printOffset, printLength;
        wchar_t names[1024];
    } record{};
    const auto substitute = L"\\??\\" + target.native();
    assert(substitute.size() + 1 < ARRAYSIZE(record.names));
    record.tag = IO_REPARSE_TAG_MOUNT_POINT;
    record.substituteLength = static_cast<WORD>(substitute.size() * sizeof(wchar_t));
    record.printOffset = static_cast<WORD>(record.substituteLength + sizeof(wchar_t));
    record.length = static_cast<WORD>(8 + record.printOffset + sizeof(wchar_t));
    std::copy(substitute.begin(), substitute.end(), record.names);
    DWORD bytes = 0;
    assert(DeviceIoControl(directory.value, FSCTL_SET_REPARSE_POINT, &record, 8 + record.length, nullptr, 0, &bytes, nullptr));
}

HANDLE publishReady = nullptr, publishGo = nullptr;
void waitToPublish() {
    assert(SetEvent(publishReady) && WaitForSingleObject(publishGo, 10000) == WAIT_OBJECT_0);
}

void verifySelected(const CalendarMatchJournal& lease) {
    const auto loaded = lease.read(scope);
    assert(loaded.state == State::committed && loaded.decision &&
        loaded.decision->intent == Intent::userSelected && std::string_view(loaded.decision->eventId) == event);
}

void verifyReplay(const CalendarMatchJournal& lease) {
    const auto loaded = lease.readReplay(replayScope);
    assert(loaded.state == State::committed && loaded.value &&
        loaded.value->attemptId == replayInput.attemptId && loaded.value->expiresAtMs == 1730000123125);
    const auto request = DesktopApiClient::createMeetingRequest<CustodyString>(scope.recordingId, replayScope.revisionId,
        replayInput.durationSeconds, replayInput.startedAtMs, replayInput.stoppedAtMs,
        replayInput.displayTimezoneOffsetMinutes, replayInput.attemptId);
    assert(request && loaded.value->body == DesktopApiClient::createMeetingBody(*request));
    assert(loaded.value->idempotencyKey ==
        DesktopApiClient::idempotencyKey<CustodyString>("calendar-meeting", scope.recordingId, replayInput.attemptId));
}
} // namespace

int wmain(int argc, wchar_t** argv) {
    if (argc > 1) {
        assert(argc >= 3);
        const std::wstring_view mode(argv[2]);
        const auto lease = CalendarMatchJournal::prepare(argv[1]);
        assert(lease);
        if (mode == L"read") { verifySelected(*lease); return 0; }
        if (mode == L"read-replay") { verifyReplay(*lease); return 0; }
        assert(argc == 4);
        const std::wstring gate = argv[3];
        const File ready(OpenEventW(EVENT_MODIFY_STATE, FALSE, (gate + L"-ready").c_str()));
        const File go(OpenEventW(SYNCHRONIZE, FALSE, (gate + L"-go").c_str()));
        assert(ready && go);
        publishReady = ready.value;
        publishGo = go.value;
        grafCalendarJournalTestBeforePublish = waitToPublish;
        if (mode == L"create-a" || mode == L"create-b")
            return 10 + static_cast<int>(lease->commitReplay(replayScope, mode == L"create-a" ? replayInput : otherReplayInput));
        const auto state = lease->commit(scope,
            mode == L"select" ? Intent::userSelected : Intent::userDeclined,
            mode == L"select" ? event : std::string_view{});
        return 10 + static_cast<int>(state);
    }

    const Fixture fixture;
    const auto root = fixture.root / L"graf";
    const auto journal = root / L"calendar-match";
    const auto file = journal / L"33333333-3333-4333-8333-333333333333.decision";
    const auto replayFile = journal / L"33333333-3333-4333-8333-333333333333.create";
    grafCalendarJournalTestFlushFailure = 2;
    assert(!CalendarMatchJournal::prepare(root));
    grafCalendarJournalTestFlushFailure = 0;
    const auto lease = CalendarMatchJournal::prepare(root);
    assert(lease && lease->read(scope).state == State::absent);
    assert(lease->commitReplay(replayScope, replayInput) == State::absent);
    assert(fs::is_empty(journal));

    grafCalendarJournalTestFlushFailure = 1;
    assert(lease->commit(scope, Intent::userSelected, event) == State::publicationUnconfirmed);
    const auto original = readBytes(file);
    const auto failed = lease->read(scope);
    assert(failed.state == State::publicationUnconfirmed && !failed.decision);
    assert(lease->commit(scope, Intent::userSelected, event) == State::publicationUnconfirmed);
    assert(readBytes(file) == original);

    assert(lease->commitReplay(replayScope, replayInput) == State::publicationUnconfirmed);
    assert(!fs::exists(replayFile));
    grafCalendarJournalTestFlushFailure = 0;
    assert(lease->readReplay(replayScope).state == State::absent);
    grafCalendarJournalTestFlushFailure = 3;
    assert(lease->commitReplay(replayScope, replayInput) == State::publicationUnconfirmed);
    const auto replayBytes = readBytes(replayFile);
    const auto unconfirmed = lease->readReplay(replayScope);
    assert(unconfirmed.state == State::publicationUnconfirmed && !unconfirmed.value);
    assert(lease->commitReplay(replayScope, otherReplayInput) == State::conflict);
    assert(readBytes(replayFile) == replayBytes);
    grafCalendarJournalTestFlushFailure = 0;
    assert(finish(child(root, L"read-replay")) == 0);
    assert(lease->commitReplay(replayScope, replayInput) == State::committed);
    auto changedTiming = replayInput;
    ++changedTiming.durationSeconds;
    assert(lease->commitReplay(replayScope, changedTiming) == State::conflict);
    assert(readBytes(replayFile) == replayBytes && readBytes(file) == original);
    auto movedDevice = replayScope;
    movedDevice.deviceId = event;
    assert(lease->readReplay(movedDevice).state == State::authenticationFailed);
    assert(lease->commitReplay(movedDevice, replayInput) == State::authenticationFailed);
    const auto movedDecision = journal / L"moved-decision";
    fs::rename(file, movedDecision);
    assert(lease->readReplay(replayScope).state == State::absent);
    assert(lease->commitReplay(replayScope, otherReplayInput) == State::absent);
    fs::rename(movedDecision, file);
    writeBytes(replayFile, original);
    assert(lease->readReplay(replayScope).state == State::authenticationFailed);
    writeBytes(replayFile, replayBytes);
    writeBytes(file, replayBytes);
    assert(lease->read(scope).state == State::authenticationFailed &&
        lease->readReplay(replayScope).state == State::authenticationFailed);
    writeBytes(file, original);
    writeBytes(replayFile, std::string_view(replayBytes).substr(0, replayBytes.size() / 2));
    const auto replayDamage = lease->readReplay(replayScope).state;
    assert(replayDamage == State::invalidEnvelope || replayDamage == State::authenticationFailed);
    assert(lease->commitReplay(replayScope, replayInput) == replayDamage);
    writeBytes(replayFile, std::string(calendarMatchEnvelopeLimit + 1, 'x'));
    assert(lease->readReplay(replayScope).state == State::invalidEnvelope);
    writeBytes(replayFile, replayBytes);
    const auto replayAlias = fixture.root / L"replay-alias";
    assert(CreateHardLinkW(replayAlias.c_str(), replayFile.c_str(), nullptr));
    assert(lease->readReplay(replayScope).state == State::unavailable);
    assert(fs::remove(replayAlias));
    verifyReplay(*lease);
    grafCalendarJournalTestFlushFailure = 0;
    assert(finish(child(root, L"read")) == 0);
    assert(lease->commit(scope, Intent::userSelected, event) == State::committed);
    assert(lease->commit(scope, Intent::userDeclined, {}) == State::conflict);
    assert(readBytes(file) == original);

    auto second = scope;
    second.recordingId = secondId;
    assert(lease->read(second).state == State::absent);
    assert(lease->commit(second, Intent::automatic, {}) == State::committed);
    const auto secondFile = journal / L"55555555-5555-4555-8555-555555555555.decision";
    const auto secondBytes = readBytes(secondFile);
    writeBytes(secondFile, original);
    assert(lease->read(second).state == State::authenticationFailed);
    writeBytes(secondFile, secondBytes);

    auto foreign = scope;
    foreign.workspaceId = secondId;
    assert(lease->read(foreign).state == State::authenticationFailed);
    writeBytes(file, std::string_view(original).substr(0, original.size() / 2));
    const auto damaged = lease->read(scope).state;
    assert(damaged == State::invalidEnvelope || damaged == State::authenticationFailed);
    assert(lease->commit(scope, Intent::userSelected, event) == damaged);
    writeBytes(file, std::string(calendarMatchEnvelopeLimit + 1, 'x'));
    assert(lease->read(scope).state == State::invalidEnvelope);
    writeBytes(file, original);

    {
        const File locked(CreateFileW(file.c_str(), GENERIC_READ, 0, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr));
        assert(locked && lease->read(scope).state == State::unavailable);
    }
    const auto alias = fixture.root / L"alias";
    assert(CreateHardLinkW(alias.c_str(), file.c_str(), nullptr));
    assert(lease->read(scope).state == State::unavailable);
    assert(fs::remove(alias));
    verifySelected(*lease);

    const auto replacement = fixture.root / L"replacement";
    assert(fs::create_directory(replacement));
    junction(replacement / L"calendar-match", journal);
    assert(!CalendarMatchJournal::prepare(replacement));
    assert(RemoveDirectoryW((replacement / L"calendar-match").c_str()));
    assert(readBytes(file) == original);

    const auto raceRoot = fixture.root / L"race";
    assert(fs::create_directory(raceRoot));
    const auto gateName = L"Local\\graf-journal-" + guid();
    const auto aName = gateName + L"-a", bName = gateName + L"-b";
    const File aReady(CreateEventW(nullptr, TRUE, FALSE, (aName + L"-ready").c_str()));
    const File aGo(CreateEventW(nullptr, TRUE, FALSE, (aName + L"-go").c_str()));
    const File bReady(CreateEventW(nullptr, TRUE, FALSE, (bName + L"-ready").c_str()));
    const File bGo(CreateEventW(nullptr, TRUE, FALSE, (bName + L"-go").c_str()));
    assert(aReady && aGo && bReady && bGo);
    const auto a = child(raceRoot, L"select", aName);
    const auto b = child(raceRoot, L"decline", bName);
    HANDLE ready[] = {aReady.value, bReady.value};
    assert(WaitForMultipleObjects(ARRAYSIZE(ready), ready, TRUE, 10000) == WAIT_OBJECT_0);
    const auto raceJournal = raceRoot / L"calendar-match";
    const auto raceFile = raceJournal / file.filename();
    assert(!fs::exists(raceFile));
    assert(std::distance(fs::directory_iterator(raceJournal), fs::directory_iterator{}) == 2);
    assert(SetEvent(aGo.value) && finish(a) == 10 + static_cast<DWORD>(State::committed));
    const auto winnerBytes = readBytes(raceFile);
    assert(SetEvent(bGo.value) && finish(b) == 10 + static_cast<DWORD>(State::conflict));
    assert(readBytes(raceFile) == winnerBytes);
    assert(std::distance(fs::directory_iterator(raceJournal), fs::directory_iterator{}) == 1);
    const auto winner = CalendarMatchJournal::prepare(raceRoot);
    assert(winner);
    verifySelected(*winner);
    assert(ResetEvent(aReady.value) && ResetEvent(bReady.value) && ResetEvent(aGo.value) && ResetEvent(bGo.value));
    const auto firstCreate = child(raceRoot, L"create-a", aName);
    const auto secondCreate = child(raceRoot, L"create-b", bName);
    assert(WaitForMultipleObjects(ARRAYSIZE(ready), ready, TRUE, 10000) == WAIT_OBJECT_0);
    const auto raceReplay = raceJournal / replayFile.filename();
    assert(!fs::exists(raceReplay));
    assert(SetEvent(aGo.value) && finish(firstCreate) == 10 + static_cast<DWORD>(State::committed));
    const auto replayWinnerBytes = readBytes(raceReplay);
    assert(SetEvent(bGo.value) && finish(secondCreate) == 10 + static_cast<DWORD>(State::conflict));
    assert(readBytes(raceReplay) == replayWinnerBytes && readBytes(raceFile) == winnerBytes);
    assert(std::distance(fs::directory_iterator(raceJournal), fs::directory_iterator{}) == 2);
    verifyReplay(*winner);
}
