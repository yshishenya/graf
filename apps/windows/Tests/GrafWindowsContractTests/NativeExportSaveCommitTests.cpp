#include "../../RecApp/Web/ExportSaveCommit.h"

#include <windows.h>
#include <objbase.h>
#include <roapi.h>
#include <aclapi.h>
#include <sddl.h>
#include <shlobj.h>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <thread>
#include <vector>

using namespace graf::windows;
namespace fs = std::filesystem;

#ifdef GRAF_WINDOWS_TEST_EXPORT_REPLACEMENT_PHASES
namespace graf::windows {
extern std::string_view replacementTestPhase;
}
#endif

namespace {

void require(bool ok, const char* step) {
    if (!ok) throw std::runtime_error(step);
}

// Use the Win32 long-path form for fixture I/O. Product calls receive ordinary paths.
fs::path fixtureIoPath(const fs::path& path) {
    return L"\\\\?\\" + fs::absolute(path).native();
}

struct Workspace {
    fs::path path;
    explicit Workspace(const fs::path& parent) {
        GUID id{};
        wchar_t text[40]{};
        require(SUCCEEDED(CoCreateGuid(&id)) && StringFromGUID2(id, text, ARRAYSIZE(text)), "fixture-guid");
        path = parent / (std::wstring(L"graf-export-test-") + text);
        require(fs::create_directory(path), "fixture-root");
    }
    ~Workspace() {
        std::error_code ignored;
        fs::remove_all(fixtureIoPath(path), ignored);
    }
};

void write(const fs::path& path, const std::string& bytes) {
    std::ofstream file(fixtureIoPath(path), std::ios::binary);
    file.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
    file.close();
    require(static_cast<bool>(file), "fixture-write");
}

std::string read(const fs::path& path) {
    std::ifstream file(fixtureIoPath(path), std::ios::binary);
    require(static_cast<bool>(file), "fixture-read");
    return {std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>()};
}

template<class Read>
auto waitFor(Read read) {
    for (unsigned i = 0; i < 300; ++i) {
        if (auto value = read()) return value;
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    throw std::runtime_error("worker-timeout");
}

void verifyPrivateAcl(const fs::path& path) {
    PACL acl = nullptr;
    PSECURITY_DESCRIPTOR sd = nullptr;
    require(GetNamedSecurityInfoW(fixtureIoPath(path).c_str(), SE_FILE_OBJECT, DACL_SECURITY_INFORMATION,
        nullptr, nullptr, &acl, nullptr, &sd) == ERROR_SUCCESS, "published-acl-read");
    SECURITY_DESCRIPTOR_CONTROL control{};
    DWORD revision = 0;
    const bool ok = acl && acl->AceCount == 2 && GetSecurityDescriptorControl(sd, &control, &revision) &&
        (control & SE_DACL_PROTECTED);
    LocalFree(sd);
    require(ok, "published-acl-private");
}

void denyNewFilesInFixture(const fs::path& folder) {
    PACL oldAcl = nullptr;
    PSECURITY_DESCRIPTOR raw = nullptr;
    auto path = fixtureIoPath(folder).native();
    require(GetNamedSecurityInfoW(path.c_str(), SE_FILE_OBJECT, DACL_SECURITY_INFORMATION,
        nullptr, nullptr, &oldAcl, nullptr, &raw) == ERROR_SUCCESS, "fixture-location-read-acl");
    const std::unique_ptr<void, decltype(&LocalFree)> descriptor(raw, &LocalFree);
    alignas(DWORD) BYTE sid[SECURITY_MAX_SID_SIZE]{};
    DWORD size = sizeof(sid);
    require(CreateWellKnownSid(WinWorldSid, nullptr, sid, &size) != FALSE, "fixture-location-sid");
    EXPLICIT_ACCESSW deny{};
    deny.grfAccessPermissions = FILE_ADD_FILE;
    deny.grfAccessMode = DENY_ACCESS;
    BuildTrusteeWithSidW(&deny.Trustee, sid);
    PACL changed = nullptr;
    require(SetEntriesInAclW(1, &deny, oldAcl, &changed) == ERROR_SUCCESS, "fixture-location-create-acl");
    const std::unique_ptr<ACL, decltype(&LocalFree)> acl(changed, &LocalFree);
    require(SetNamedSecurityInfoW(path.data(), SE_FILE_OBJECT, DACL_SECURITY_INFORMATION,
        nullptr, nullptr, acl.get(), nullptr) == ERROR_SUCCESS, "fixture-location-deny-write");
}

#ifdef GRAF_WINDOWS_TEST_EXPORT_REPLACEMENT_PHASES
void createJournal(const fs::path& path) {
    HANDLE token = nullptr;
    require(OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token) != FALSE, "journal-token");
    DWORD count = 0;
    GetTokenInformation(token, TokenUser, nullptr, 0, &count);
    std::vector<BYTE> bytes(count);
    const auto got = GetTokenInformation(token, TokenUser, bytes.data(), count, &count);
    CloseHandle(token);
    LPWSTR sid = nullptr;
    require(got && ConvertSidToStringSidW(reinterpret_cast<TOKEN_USER*>(bytes.data())->User.Sid, &sid), "journal-sid");
    const std::unique_ptr<void, decltype(&LocalFree)> sidOwner(sid, LocalFree);
    const auto sddl = std::wstring(L"O:") + sid + L"D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;" + sid + L")";
    PSECURITY_DESCRIPTOR raw = nullptr;
    require(ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl.c_str(), SDDL_REVISION_1, &raw, nullptr) != FALSE,
        "journal-descriptor");
    const std::unique_ptr<void, decltype(&LocalFree)> descriptor(raw, LocalFree);
    SECURITY_ATTRIBUTES security{sizeof(security), raw, FALSE};
    require(CreateDirectoryW(path.c_str(), &security) != FALSE, "journal-create");
}

constexpr auto oldPayload = "previous export";
constexpr auto newPayload = "replacement export";
constexpr auto filename = L"existing.txt";

BY_HANDLE_FILE_INFORMATION fileInfo(const fs::path& path) {
    const auto file = CreateFileW(fixtureIoPath(path).c_str(), FILE_READ_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        nullptr, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
    require(file != INVALID_HANDLE_VALUE, "fixture-info-open");
    BY_HANDLE_FILE_INFORMATION result{};
    const auto success = GetFileInformationByHandle(file, &result);
    CloseHandle(file);
    require(success != FALSE, "fixture-info-read");
    return result;
}

ExportSaveResult replaceFixture(const fs::path& folder, bool revoke) {
    auto scratch = ExportDownloadScratch::create();
    require(static_cast<bool>(scratch), "replacement-scratch");
    std::ofstream marker(folder / L"scratch-path.bin", std::ios::binary);
    const auto path = scratch->downloadPath().parent_path().native();
    marker.write(reinterpret_cast<const char*>(path.data()), static_cast<std::streamsize>(path.size() * sizeof(wchar_t)));
    marker.close();
    require(static_cast<bool>(marker), "replacement-scratch-marker");
    write(scratch->downloadPath(), newPayload);
    require(scratch->pinCompletedDownload(std::char_traits<char>::length(newPayload)), "replacement-pin");
    const auto preparation = scratch->prepareReplacement(folder / L"target", filename);
    require(preparation.has_value(), "replacement-prepare");
    const auto original = folder / L"target" / filename;
    const auto writer = CreateFileW(original.c_str(), GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    const auto error = writer == INVALID_HANDLE_VALUE ? GetLastError() : ERROR_SUCCESS;
    if (writer != INVALID_HANDLE_VALUE) CloseHandle(writer);
    require(error == ERROR_SHARING_VIOLATION, "replacement-original-frozen");
    ExportCommitPermission permission;
    if (revoke) permission.revoke();
    const auto result = scratch->saveReplacement(folder / L"journal", *preparation, permission);
    if (result == ExportSaveResult::saved || result == ExportSaveResult::cancelled)
        require(!permission.pending() && scratch->saveReplacement(folder / L"journal", *preparation, permission) ==
            ExportSaveResult::cancelled, "replacement-once");
    return result;
}

void cleanChildScratch(const fs::path& folder) {
    const auto marker = read(folder / L"scratch-path.bin");
    require(!marker.empty() && marker.size() % sizeof(wchar_t) == 0, "child-scratch-marker");
    std::wstring path(marker.size() / sizeof(wchar_t), L'\0');
    std::memcpy(path.data(), marker.data(), marker.size());
    PWSTR raw = nullptr;
    require(SUCCEEDED(SHGetKnownFolderPath(FOLDERID_LocalAppData, KF_FLAG_DONT_VERIFY, nullptr, &raw)) && raw,
        "child-scratch-local");
    const std::unique_ptr<wchar_t, decltype(&CoTaskMemFree)> local(raw, CoTaskMemFree);
    const fs::path scratch(path);
    const auto name = scratch.filename().native();
    constexpr std::wstring_view prefix = L"graf-export-download-";
    GUID guid{};
    require(scratch.parent_path() == fs::path(local.get()) && name.size() == prefix.size() + 38 &&
        name.compare(0, prefix.size(), prefix) == 0 && SUCCEEDED(CLSIDFromString(name.c_str() + prefix.size(), &guid)),
        "child-scratch-owned");
    const auto attr = GetFileAttributesW(scratch.c_str());
    require(attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_REPARSE_POINT), "child-scratch-no-reparse");
    require(fs::remove(scratch / L"payload.bin") && fs::remove(scratch), "child-scratch-clean");
}

void runInterrupted(const fs::path& folder, std::wstring_view phase) {
    wchar_t executable[32768]{};
    const auto size = GetModuleFileNameW(nullptr, executable, ARRAYSIZE(executable));
    require(size && size < ARRAYSIZE(executable), "replacement-child-path");
    auto command = L"\"" + std::wstring(executable) + L"\" --replace-child \"" + folder.native() + L"\" " + std::wstring(phase);
    STARTUPINFOW start{};
    start.cb = sizeof(start);
    PROCESS_INFORMATION process{};
    require(CreateProcessW(executable, command.data(), nullptr, nullptr, FALSE, 0, nullptr, nullptr, &start, &process) != FALSE,
        "replacement-child-start");
    CloseHandle(process.hThread);
    const auto waited = WaitForSingleObject(process.hProcess, 20000);
    DWORD code = 0;
    if (waited != WAIT_OBJECT_0) { TerminateProcess(process.hProcess, 78); WaitForSingleObject(process.hProcess, 3000); }
    const bool ok = waited == WAIT_OBJECT_0 && GetExitCodeProcess(process.hProcess, &code) && code == 77;
    CloseHandle(process.hProcess);
    require(ok, "replacement-child-checkpoint");
}

void verifyPreparation(const fs::path& root) {
    const auto target = root / L"target";
    const auto journal = root / L"journal";
    require(fs::create_directories(target), "preparation-target");
    createJournal(journal);
    write(target / filename, oldPayload);
    write(target / L"other.txt", oldPayload);
    const auto streamed = target / L"named-stream.txt";
    write(streamed, oldPayload);
    write(fs::path(streamed.native() + L":fixture"), "named stream");
    auto scratch = ExportDownloadScratch::create();
    require(scratch != nullptr, "preparation-scratch");
    require(!scratch->prepareReplacement(target, streamed.filename().native()), "reject-named-stream");
    const auto longName = target / L"Filename with a short alias.txt";
    write(longName, oldPayload);
    wchar_t alias[MAX_PATH]{};
    const auto length = GetShortPathNameW(longName.c_str(), alias, ARRAYSIZE(alias));
    if (length != 0 && length < ARRAYSIZE(alias)) {
        const auto shortName = fs::path(alias).filename().native();
        if (shortName != longName.filename().native()) {
            require(!scratch->prepareReplacement(target, shortName), "reject-short-alias");
            std::puts("EXPORT_REPLACEMENT_SHORT_ALIAS=PASS");
        } else std::puts("EXPORT_REPLACEMENT_SHORT_ALIAS=UNAVAILABLE");
    } else std::puts("EXPORT_REPLACEMENT_SHORT_ALIAS=UNAVAILABLE");
    write(scratch->downloadPath(), newPayload);
    require(scratch->pinCompletedDownload(std::char_traits<char>::length(newPayload)), "preparation-pin");
    const auto first = scratch->prepareReplacement(target, filename);
    const auto second = scratch->prepareReplacement(target, L"other.txt");
    require(first && second && first != second, "preparation-revisions");
    ExportCommitPermission stale, current;
    require(scratch->saveReplacement(journal, *first, stale) == ExportSaveResult::cancelled &&
        stale.pending() && read(target / filename) == oldPayload && fs::is_empty(journal), "stale-confirmation-no-effects");
    require(scratch->saveReplacement(journal, *second, current) == ExportSaveResult::saved &&
        read(target / filename) == oldPayload && read(target / L"other.txt") == newPayload &&
        fs::is_empty(journal), "current-confirmation-works");
    const auto late = scratch->prepareReplacement(target, filename);
    require(late.has_value(), "late-stream-preparation");
    const auto stream = (target / filename).native() + L":fixture";
    const auto streamHandle = CreateFileW(stream.c_str(), FILE_WRITE_DATA,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (streamHandle != INVALID_HANDLE_VALUE) {
        CloseHandle(streamHandle);
        ExportCommitPermission approval;
        require(scratch->saveReplacement(journal, *late, approval) == ExportSaveResult::unavailableLocation &&
            approval.pending() && read(target / filename) == oldPayload && fs::is_empty(journal),
            "late-named-stream-revokes-version");
        std::puts("EXPORT_REPLACEMENT_LATE_STREAM=REJECTED");
    } else {
        const auto error = GetLastError();
        require(error == ERROR_ACCESS_DENIED || error == ERROR_SHARING_VIOLATION, "late-stream-open-error");
        std::puts("EXPORT_REPLACEMENT_LATE_STREAM=BLOCKED_BY_OS");
    }
    std::puts("EXPORT_REPLACEMENT_PREPARATION=PASS");
}

void verifyReplacement(const fs::path& root) {
    verifyPreparation(root / L"preparation");
    for (const std::wstring_view phase : {L"save", L"revoke", L"intent", L"backup", L"publish", L"cleanup", L"foreign",
            L"tamper", L"edited-final", L"edited-backup", L"transient-name"}) {
        const auto folder = root / phase;
        const auto target = folder / L"target";
        const auto journal = folder / L"journal";
        require(fs::create_directories(target), "replacement-target");
        createJournal(journal);
        write(target / filename, oldPayload);
        const auto originalCreation = fileInfo(target / filename).ftCreationTime;
        if (phase == L"save" || phase == L"revoke") {
            const bool revoke = phase == L"revoke";
            const auto result = replaceFixture(folder, revoke);
            if (result != (revoke ? ExportSaveResult::cancelled : ExportSaveResult::saved))
                std::printf("replacement-result=%d\n", static_cast<int>(result));
            require(result == (revoke ? ExportSaveResult::cancelled : ExportSaveResult::saved) &&
                read(target / filename) == (revoke ? oldPayload : newPayload) && fs::is_empty(journal), "replacement-return");
            continue;
        }
        runInterrupted(folder, phase == L"edited-final" ? L"publish" :
            phase == L"foreign" || phase == L"tamper" || phase == L"edited-backup" ||
                phase == L"transient-name" ? L"backup" : phase);
        cleanChildScratch(folder);
        const auto record = fs::directory_iterator(journal)->path();
        verifyPrivateAcl(record);
        if (phase == L"foreign") write(target / filename, "third party");
        if (phase == L"tamper") write(record, "broken intent");
        fs::path backup;
        for (const auto& entry : fs::directory_iterator(target))
            if (entry.path().extension() == L".bak") backup = entry.path();
        if (phase == L"backup") {
            auto scratch = ExportDownloadScratch::create();
            require(scratch && !backup.empty() && !scratch->prepareReplacement(target, backup.filename().native()),
                "reject-foreign-intent-reserve");
            runInterrupted(folder, L"recovery-cleanup");
        }
        const auto edit = phase == L"edited-final" ? target / filename : backup;
        const bool edited = phase == L"edited-final" || phase == L"edited-backup";
        if (edited) {
            require(!backup.empty(), "edited-restore-point");
            const auto before = fileInfo(edit);
            const auto modified = fs::last_write_time(fixtureIoPath(edit));
            auto payload = read(edit);
            payload.front() = 'X';
            write(edit, payload);
            fs::last_write_time(fixtureIoPath(edit), modified);
            const auto after = fileInfo(edit);
            require(before.dwVolumeSerialNumber == after.dwVolumeSerialNumber &&
                before.nFileIndexHigh == after.nFileIndexHigh && before.nFileIndexLow == after.nFileIndexLow &&
                before.nFileSizeHigh == after.nFileSizeHigh && before.nFileSizeLow == after.nFileSizeLow &&
                CompareFileTime(&before.ftLastWriteTime, &after.ftLastWriteTime) == 0, "edit-keeps-id-size-time");
        }
        if (phase == L"transient-name") {
            write(target / filename, "transient competitor");
            const auto file = CreateFileW((target / filename).c_str(), FILE_WRITE_ATTRIBUTES, FILE_SHARE_READ,
                nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
            require(file != INVALID_HANDLE_VALUE, "transient-open");
            const FILETIME distinct{1, originalCreation.dwHighDateTime - 1};
            const auto set = SetFileTime(file, &distinct, nullptr, nullptr);
            CloseHandle(file);
            require(set && fs::remove(target / filename), "transient-set-and-remove");
        }
        const auto result = ExportDownloadScratch::recoverReplacement(journal, record.filename().native());
        if (phase == L"transient-name") {
            require(read(target / filename) == oldPayload, "transient-keeps-original");
            const auto restored = fileInfo(target / filename).ftCreationTime;
            if (CompareFileTime(&originalCreation, &restored) != 0) {
                require(result == ExportSaveResult::recoveryRequired && fs::exists(fixtureIoPath(record)) &&
                    std::distance(fs::directory_iterator(target), fs::directory_iterator{}) == 2, "tunneling-keeps-intent-and-stage");
                std::puts("EXPORT_REPLACEMENT_RESTORE_TUNNELING=RETAINED");
            } else {
                require(result == ExportSaveResult::cancelled && fs::is_empty(journal), "transient-normal-recovery");
                std::puts("EXPORT_REPLACEMENT_RESTORE_TUNNELING=UNAVAILABLE");
            }
        } else if (edited) {
            require(result == ExportSaveResult::recoveryRequired && fs::exists(fixtureIoPath(record)) && fs::exists(fixtureIoPath(backup)) &&
                read(edit).front() == 'X' && (phase == L"edited-final" ? read(backup) == oldPayload :
                    !fs::exists(target / filename)), "edited-object-preserves-reserve");
        } else if (phase == L"foreign" || phase == L"tamper") {
            require(result == ExportSaveResult::recoveryRequired && fs::exists(fixtureIoPath(record)), "ambiguous-keeps-intent");
            require((phase == L"foreign" && read(target / filename) == "third party") ||
                (phase == L"tamper" && !fs::exists(target / filename)), "ambiguous-keeps-final");
            unsigned kept = 0;
            for (const auto& entry : fs::directory_iterator(target))
                if (entry.path().extension() == L".bak" && read(entry.path()) == oldPayload) ++kept;
            require(kept == 1, "ambiguous-keeps-original");
        } else {
            const bool published = phase == L"publish" || phase == L"cleanup";
            require(result == (published ? ExportSaveResult::saved : ExportSaveResult::cancelled) &&
                read(target / filename) == (published ? newPayload : oldPayload) && fs::is_empty(journal) &&
                std::distance(fs::directory_iterator(target), fs::directory_iterator{}) == 1, "replacement-recovered");
        }
    }
    std::puts("EXPORT_REPLACEMENT_PROCESS_INTERRUPTION=PASS");
}
#endif

} // namespace

int wmain(int argc, wchar_t** argv) {
    try {
        require(SUCCEEDED(RoInitialize(RO_INIT_MULTITHREADED)), "worker-apartment");
        struct Apartment { ~Apartment() { RoUninitialize(); } };
        const Apartment apartment;
#ifdef GRAF_WINDOWS_TEST_EXPORT_REPLACEMENT_PHASES
        if (argc == 4 && std::wstring_view(argv[1]) == L"--replace-child") {
            const fs::path folder(argv[2]);
            const std::wstring phase(argv[3]);
            std::string checkpoint;
            for (const auto c : phase) {
                if (c > 127) return 79;
                checkpoint.push_back(static_cast<char>(c));
            }
            replacementTestPhase = checkpoint;
            if (phase == L"recovery-cleanup") {
                const auto journal = folder / L"journal";
                const auto record = fs::directory_iterator(journal)->path();
                (void)ExportDownloadScratch::recoverReplacement(journal, record.filename().native());
            } else (void)replaceFixture(folder, false);
            return 79;
        }
#endif
        for (const std::wstring_view name : {L"", L"..", L"file ", L"file.", L"folder\\file",
                L"file:stream", L"a/b", L"nul.wav", L"cOm1 .txt", L"LPT\u00b2.wav", L"CONOUT$"}) {
            require(!validExportFilename(name), "unsafe-filename");
        }
        require(validExportFilename(L"Запись встречи.wav") && validExportFilename(L"lpt10.txt") &&
            validExportFilename(L".metadata"), "valid-filenames");

        const Workspace to(argc == 2 ? fs::path(argv[1]) : fs::temp_directory_path());
#ifdef GRAF_WINDOWS_TEST_EXPORT_REPLACEMENT_PHASES
        {
            const Workspace replacement(to.path);
            verifyReplacement(replacement.path);
        }
#endif
        {
            using Status = ExportFolderWorker::Status;
            const Workspace parent(to.path);
            const auto ready = [&] {
                auto worker = ExportFolderWorker::start(parent.path);
                require(static_cast<bool>(worker), "folder-worker");
                require(waitFor([&]() -> std::optional<Status> {
                    const auto status = worker->status();
                    if (status == Status::preparing) return {};
                    return status;
                }) == Status::ready, "folder-parent-pinned");
                return worker;
            };
            const auto done = [](const ExportFolderWorker& worker) {
                return waitFor([&]() -> std::optional<Status> {
                    const auto status = worker.status();
                    if (status == Status::ready || status == Status::creating) return {};
                    return status;
                });
            };
            auto cancelled = ready();
            cancelled->revoke();
            require(!cancelled->create(L"cancelled") && done(*cancelled) == Status::cancelled &&
                fs::is_empty(parent.path), "folder-revoked-before-create");
            auto accepted = ready();
            const auto moved = parent.path.wstring() + L"-moved";
            require(!MoveFileExW(parent.path.c_str(), moved.c_str(), 0), "folder-parent-cannot-move");
            require(!accepted->create(L"..") && accepted->create(L"Новая папка") &&
                !accepted->create(L"duplicate-request"), "folder-validated-once");
            require(done(*accepted) == Status::created, "folder-created");
            accepted->revoke();
            require(fs::is_directory(parent.path / L"Новая папка") &&
                !fs::exists(parent.path / L"duplicate-request"), "folder-completed-not-removed");
            write(parent.path / L"occupied", "original");
            for (const auto name : {L"Новая папка", L"occupied"}) {
                auto conflict = ready();
                require(conflict->create(name) && done(*conflict) == Status::conflict, "folder-no-replacement");
            }
            require(read(parent.path / L"occupied") == "original", "folder-collision-preserves-file");
            std::puts("EXPORT_FOLDER_PIN_REVOKE_CONFLICT=PASS");
        }
        auto scratch = ExportDownloadScratch::create();
        auto parallel = ExportDownloadScratch::create();
        require(scratch && parallel, "private-download-directory");
        const auto source = scratch->downloadPath();
        const auto other = parallel->downloadPath();
        require(source.is_absolute() && !fs::exists(source) && other.parent_path() != source.parent_path(),
            "unique-absent-targets");
        verifyPrivateAcl(source.parent_path());
        const auto output = to.path / L"Запись встречи.wav";
        std::string data(3 * 65536 + 17, 'a');
        for (std::size_t i = 0; i < data.size(); ++i) data[i] = static_cast<char>(i % 251);
        write(source, data);

        ExportCommitPermission revoked;
        revoked.revoke();
        require(scratch->saveNew(output.filename().native(), revoked) ==
            ExportSaveResult::cancelled && fs::is_empty(to.path), "revocation-no-output");

        ExportCommitPermission incorrectLength;
        require(!scratch->pinCompletedDownload(data.size() + 1) &&
            scratch->saveNew(output.filename().native(), incorrectLength) ==
            ExportSaveResult::incompleteDownload && fs::is_empty(to.path), "truncated-download-no-output");

        const auto alias = source.parent_path() / L"payload-alias";
        fs::create_hard_link(source, alias);
        require(!scratch->pinCompletedDownload(data.size()) && fs::is_empty(to.path), "aliased-source-no-output");
        require(fs::remove(alias), "remove-test-alias");
        require(scratch->pinCompletedDownload(data.size()) &&
            !scratch->pinCompletedDownload(data.size()), "source-pinned-once");
        const auto unexpectedWriter = CreateFileW(source.c_str(), GENERIC_WRITE | DELETE,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
        if (unexpectedWriter != INVALID_HANDLE_VALUE) CloseHandle(unexpectedWriter);
        require(unexpectedWriter == INVALID_HANDLE_VALUE, "completed-source-cannot-be-replaced");

        ExportCommitPermission wrongLocation;
        require(!scratch->pinDestination(to.path / L"missing") &&
            scratch->saveNew(output.filename().native(), wrongLocation) == ExportSaveResult::unavailableLocation &&
            fs::is_empty(to.path), "unknown-destination-no-output");
        require(scratch->pinDestination(to.path), "pin-destination");

        ExportCommitPermission occupied;
        write(output, "prior file");
        const auto oldTime = fs::last_write_time(output);
        const auto conflict = scratch->saveNew(output.filename().native(), occupied);
        if (conflict != ExportSaveResult::nameConflict) std::printf("conflict-result=%d\n", static_cast<int>(conflict));
        require(conflict == ExportSaveResult::nameConflict && read(output) == "prior file" &&
            fs::last_write_time(output) == oldTime, "occupied-name-unchanged");
        require(std::distance(fs::directory_iterator(to.path), fs::directory_iterator()) == 1, "conflict-temp-cleaned");

        const auto newFile = to.path / L"Запись встречи 2.wav";
        ExportCommitPermission accepted;
        const auto result = scratch->saveNew(newFile.filename().native(), accepted);
        if (result != ExportSaveResult::saved) std::printf("publish-result=%d\n", static_cast<int>(result));
        require(result == ExportSaveResult::saved && read(newFile) == data, "new-file-exact-bytes");
        verifyPrivateAcl(newFile);
        accepted.revoke();
        require(!accepted.pending() && !accepted.beginCommit(), "commit-is-single-use");
        require(std::distance(fs::directory_iterator(to.path), fs::directory_iterator()) == 2, "no-extra-file");
        const auto partial = fs::path(other.native() + L".crdownload");
        write(partial, "parallel fixture");
        scratch.reset();
        require(!fs::exists(source.parent_path()) && read(partial) == "parallel fixture", "only-own-scratch-cleaned");
        parallel.reset();
        require(!fs::exists(other.parent_path()), "partial-scratch-cleaned");
        auto uncertain = ExportDownloadScratch::create();
        require(static_cast<bool>(uncertain), "uncertain-fixture");
        const auto unknownDirectory = uncertain->downloadPath().parent_path();
        const auto unrelated = unknownDirectory / L"unrecognized.tmp";
        write(uncertain->downloadPath(), "known fixture");
        write(unrelated, "unknown fixture");
        uncertain.reset();
        require(read(unrelated) == "unknown fixture" &&
            std::distance(fs::directory_iterator(unknownDirectory), fs::directory_iterator()) == 1,
            "unknown-entry-preserved");
        require(fs::remove(unrelated) && fs::remove(unknownDirectory), "remove-unknown-test-fixture");

        const auto revokedOutput = to.path / L"revoked-worker.bin";
        const auto worker = ExportSaveWorker::start(revokedOutput);
        require(static_cast<bool>(worker), "worker-start");
        const auto workerPath = *waitFor([&] { return worker->takeBrowserPath(); });
        require(!fs::exists(revokedOutput) && !worker->takeBrowserPath(), "browser-path-one-time");
        write(workerPath, data);
        worker->revoke();
        require(fs::exists(workerPath) && !worker->result(), "worker-waits-for-browser-stop");
        worker->browserStopped(data.size());
        require(*waitFor([&] { return worker->result(); }) == ExportSaveResult::cancelled &&
            !fs::exists(workerPath.parent_path()) && !fs::exists(revokedOutput), "worker-revoked-download-cleaned");

        const auto workerOutput = to.path / L"worker.bin";
        const auto nextWorker = ExportSaveWorker::start(workerOutput);
        require(static_cast<bool>(nextWorker), "next-worker-start");
        const auto nextPath = *waitFor([&] { return nextWorker->takeBrowserPath(); });
        write(nextPath, data);
        nextWorker->browserStopped(data.size());
        require(*waitFor([&] { return nextWorker->result(); }) == ExportSaveResult::saved &&
            !fs::exists(nextPath.parent_path()) && read(workerOutput) == data, "next-worker-saved-exactly");

        for (const bool cancel : {false, true}) {
            const auto existing = to.path / (cancel ? L"retry-cancel.bin" : L"retry-occupied.bin");
            const auto unused = to.path / (cancel ? L"retry-must-not-exist.bin" : L"retry-saved.bin");
            const auto retry = ExportSaveWorker::start(existing);
            require(static_cast<bool>(retry), "retry-worker-start");
            const auto input = *waitFor([&] { return retry->takeBrowserPath(); });
            require(!retry->retryDestination(unused), "retry-needs-conflict");
            write(input, data);
            write(existing, "appeared after download started");
            const auto occupiedTime = fs::last_write_time(existing);
            retry->browserStopped(data.size());
            const auto checkConflict = [&] {
                require(waitFor([&] { return retry->result(); }) == ExportSaveResult::nameConflict &&
                    fs::exists(input) && !retry->takeBrowserPath() && read(existing) == "appeared after download started" &&
                    fs::last_write_time(existing) == occupiedTime, "late-conflict-keeps-download-and-original");
            };
            checkConflict();
            require(!retry->retryDestination(to.path / L"..") && retry->retryDestination(existing),
                "retry-validates-name");
            checkConflict();
            if (cancel) {
                retry->revoke();
                require(!retry->retryDestination(unused) &&
                    waitFor([&] { return retry->result(); }) == ExportSaveResult::cancelled &&
                    !fs::exists(unused), "retry-revocation-is-final");
            } else {
                require(retry->retryDestination(unused) &&
                    !retry->retryDestination(to.path / L"duplicate-retry.bin") &&
                    waitFor([&] { return retry->result(); }) == ExportSaveResult::saved &&
                    read(unused) == data && !fs::exists(to.path / L"duplicate-retry.bin"), "retry-saves-exact-bytes-once");
            }
            require(!fs::exists(input.parent_path()) && read(existing) == "appeared after download started" &&
                fs::last_write_time(existing) == occupiedTime, "retry-cleans-scratch-and-preserves-original");
        }
        const auto invalid = to.path / L"missing-a" / L"export.bin";
        const auto alternative = to.path / L"missing-b" / L"export.bin";
        const Workspace recovered(to.path);
        const auto corrected = recovered.path / L"export.bin";
        for (const bool cancel : {false, true}) {
            const auto retry = ExportSaveWorker::start(invalid);
            require(static_cast<bool>(retry), "location-worker-start");
            const auto checkLocation = [&] {
                require(waitFor([&] { return retry->result(); }) == ExportSaveResult::unavailableLocation &&
                    !retry->takeBrowserPath() && !fs::exists(invalid.parent_path()) &&
                    !fs::exists(alternative.parent_path()), "location-failure-does-not-start-download");
            };
            checkLocation();
            require(!retry->retryDestination(L"relative.bin") && retry->retryDestination(alternative),
                "location-retry-needs-absolute-path");
            checkLocation();
            if (cancel) {
                retry->revoke();
                require(!retry->retryDestination(corrected) && !retry->takeBrowserPath() &&
                    waitFor([&] { return retry->result(); }) == ExportSaveResult::cancelled,
                    "location-cancelled-before-download");
            } else {
                require(retry->retryDestination(corrected), "location-retry-accepted");
                const auto input = *waitFor([&] { return retry->takeBrowserPath(); });
                require(!retry->takeBrowserPath(), "location-browser-path-once");
                write(input, data);
                retry->browserStopped(data.size());
                require(waitFor([&] { return retry->result(); }) == ExportSaveResult::saved &&
                    read(corrected) == data && !fs::exists(input.parent_path()), "location-corrected-and-cleaned");
            }
        }
        const Workspace unwritable(to.path);
        const auto denied = unwritable.path / L"late-location.bin";
        const auto transferred = recovered.path / denied.filename();
        const auto lateLocation = ExportSaveWorker::start(denied);
        require(static_cast<bool>(lateLocation), "late-location-worker");
        const auto lateInput = *waitFor([&] { return lateLocation->takeBrowserPath(); });
        write(lateInput, data);
        denyNewFilesInFixture(unwritable.path);
        lateLocation->browserStopped(data.size());
        require(waitFor([&] { return lateLocation->result(); }) == ExportSaveResult::unavailableLocation &&
            fs::exists(lateInput) && fs::is_empty(unwritable.path) && !lateLocation->takeBrowserPath(),
            "late-location-retains-completed-download");
        require(lateLocation->retryDestination(transferred) &&
            waitFor([&] { return lateLocation->result(); }) == ExportSaveResult::saved &&
            read(transferred) == data && fs::is_empty(unwritable.path) && !fs::exists(lateInput.parent_path()),
            "late-location-same-download-in-other-folder");
        std::puts("EXPORT_WORKER_LOCATION_RETRY=PASS");
        std::puts("EXPORT_WORKER_RETRY=PASS");
        std::puts("NATIVE_EXPORT_WORKER=PASS");
        std::puts("NATIVE_EXPORT_SAVE_COMMIT=PASS");
        std::puts("NATIVE_EXPORT_SCRATCH=PASS");
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "%s\n", error.what());
        return 1;
    }
}
