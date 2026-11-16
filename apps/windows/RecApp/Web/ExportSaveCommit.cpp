#include "ExportSaveCommit.h"

#ifdef _WIN32
#include "../Storage/Sha256.h"
#include "../Storage/PrivateLocalFiles.h"
#include <windows.h>
#include <winternl.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Storage.h>
#include <winrt/Windows.Storage.Provider.h>
#include <sddl.h>
#include <aclapi.h>
#include <wincrypt.h>
#include <objbase.h>
#include <roapi.h>
#include <shlobj.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <istream>
#include <mutex>
#include <optional>
#include <thread>
#include <utility>
#include <vector>

namespace graf::windows {
#ifdef GRAF_WINDOWS_TEST_EXPORT_REPLACEMENT_PHASES
std::string_view replacementTestPhase;
#define GRAF_EXPORT_CHECKPOINT(phase) do { if (replacementTestPhase == phase) TerminateProcess(GetCurrentProcess(), 77); } while (false)
#else
#define GRAF_EXPORT_CHECKPOINT(phase) ((void)0)
#endif
namespace {

using namespace local_file_detail;

bool outsideCloudSyncRoot(HANDLE file) {
    std::wstring actual(32768, L'\0');
    const auto count = GetFinalPathNameByHandleW(file, actual.data(), static_cast<DWORD>(actual.size()), VOLUME_NAME_DOS);
    if (count < 7 || count >= actual.size() || actual.compare(0, 4, L"\\\\?\\") != 0) return false;
    const std::wstring_view path(actual.data() + 4, count - 4);
    using namespace winrt::Windows::Storage::Provider;
    const auto manager = winrt::get_activation_factory<StorageProviderSyncRootManager, IStorageProviderSyncRootManagerStatics>();
    for (const auto& root : manager.GetCurrentSyncRoots()) {
        const auto directory = root.Path();
        if (!directory) return false;
        const auto registered = directory.Path();
        std::wstring_view prefix(registered);
        while (prefix.size() > 3 && prefix.back() == L'\\') prefix.remove_suffix(1);
        if (prefix.empty()) return false;
        if (path.size() >= prefix.size() && equalName(path.substr(0, prefix.size()), prefix) &&
            (path.size() == prefix.size() || prefix.back() == L'\\' || path[prefix.size()] == L'\\')) return false;
    }
    return true;
}

std::vector<File> pinLocalDirectory(const std::filesystem::path& path, ACCESS_MASK finalAccess = 0) {
    auto dirs = pinFixedLocalDirectory(path, finalAccess);
    if (dirs.empty() || !outsideCloudSyncRoot(dirs.back().value)) return {};
    return dirs;
}

constexpr wchar_t kDownloadFile[] = L"payload.bin";
constexpr wchar_t kPartialDownloadFile[] = L"payload.bin.crdownload";

void removeOwnedDownload(HANDLE folder, std::wstring_view name) {
    const auto file = openRelative(folder, name, DELETE | FILE_READ_ATTRIBUTES,
        0, FILE_OPEN, FILE_NON_DIRECTORY_FILE);
    if (!file || !plainObject(file.value, false)) return;
    FILE_DISPOSITION_INFO remove{TRUE};
    (void)SetFileInformationByHandle(file.value, FileDispositionInfo, &remove, sizeof(remove));
}

bool exactSize(HANDLE file, std::uint64_t expected) {
    LARGE_INTEGER size{};
    return GetFileSizeEx(file, &size) && size.QuadPart >= 0 &&
        static_cast<std::uint64_t>(size.QuadPart) == expected;
}

ExportSaveResult copyDownload(HANDLE input, HANDLE output, std::uint64_t remaining, ExportCommitPermission& permission) {
    std::array<char, 64 * 1024> bytes;
    while (remaining != 0) {
        if (!permission.pending()) return ExportSaveResult::cancelled;
        const auto count = static_cast<DWORD>(std::min<std::uint64_t>(remaining, bytes.size()));
        DWORD read = 0, written = 0;
        if (!ReadFile(input, bytes.data(), count, &read, nullptr) || read != count)
            return ExportSaveResult::incompleteDownload;
        if (!WriteFile(output, bytes.data(), read, &written, nullptr) || written != read)
            return ExportSaveResult::unavailableLocation;
        remaining -= read;
    }
    return ExportSaveResult::saved;
}

ExportSaveResult renameWithoutReplacement(HANDLE file, std::wstring_view name) {
    const auto outcome = renameNoReplace(file, name);
    if (outcome == 0) return ExportSaveResult::saved;
    if (outcome == nameCollision) return ExportSaveResult::nameConflict;
    switch (static_cast<ULONG>(outcome)) {
    case 0xC0000022UL: // STATUS_ACCESS_DENIED
    case 0xC0000044UL: // STATUS_QUOTA_EXCEEDED
    case 0xC000007FUL: // STATUS_DISK_FULL
    case 0xC00000A2UL: // STATUS_MEDIA_WRITE_PROTECTED
    case 0xC0000802UL: // STATUS_DISK_QUOTA_EXCEEDED
        return ExportSaveResult::unavailableLocation;
    default:
        return ExportSaveResult::ioError;
    }
}

constexpr std::wstring_view intentPrefix = L".graf-export-replace-";
constexpr std::wstring_view intentSuffix = L".intent";
constexpr std::uint32_t intentVersion = 1;

struct FileVersion {
    std::int64_t size = 0, created = 0, modified = 0;
    std::uint32_t attributes = 0, reserved = 0;
    std::array<char, 64> sha256{};
    bool operator==(const FileVersion& other) const noexcept {
        return size == other.size && created == other.created && modified == other.modified &&
            attributes == other.attributes && reserved == other.reserved && sha256 == other.sha256;
    }
};

struct ReplacementIntent {
    std::uint32_t version = intentVersion;
    std::uint32_t reserved = 0;
    FILE_ID_INFO journal{}, directory{}, original{}, replacement{};
    FileVersion originalVersion{}, replacementVersion{};
    wchar_t folder[30001]{};
    wchar_t finalName[256]{};
    wchar_t token[39]{};
};
static_assert(sizeof(FILE_ID_INFO) == 24 && sizeof(wchar_t) == 2 && sizeof(ReplacementIntent) == 60888);

bool replacementFilename(std::wstring_view name) {
    return validExportFilename(name) && !equalName(name.substr(0, intentPrefix.size()), intentPrefix);
}

bool canonicalFilename(HANDLE file, std::wstring_view name) {
    std::wstring path(32768, L'\0');
    const auto count = GetFinalPathNameByHandleW(file, path.data(), static_cast<DWORD>(path.size()), VOLUME_NAME_DOS);
    if (count == 0 || count >= path.size()) return false;
    const std::wstring_view actual(path.data(), count);
    const auto separator = actual.find_last_of(L'\\');
    return separator != actual.npos && actual.substr(separator + 1) == name;
}

bool versionMetadata(HANDLE file, FileVersion& version) {
    // A named stream can have separate share state; never admit a file with one.
    alignas(FILE_STREAM_INFO) std::array<BYTE, 4096> streams{};
    if (!plainObject(file, false) ||
        !GetFileInformationByHandleEx(file, FileStreamInfo, streams.data(), static_cast<DWORD>(streams.size()))) return false;
    const auto& stream = *reinterpret_cast<const FILE_STREAM_INFO*>(streams.data());
    constexpr std::wstring_view unnamed = L"::$DATA";
    LARGE_INTEGER size{};
    FILE_BASIC_INFO basic{};
    if (stream.NextEntryOffset || stream.StreamNameLength != unnamed.size() * sizeof(wchar_t) ||
        std::wstring_view(stream.StreamName, unnamed.size()) != unnamed || !GetFileSizeEx(file, &size) ||
        size.QuadPart < 0 || size.QuadPart != stream.StreamSize.QuadPart ||
        !GetFileInformationByHandleEx(file, FileBasicInfo, &basic, sizeof(basic))) return false;
    version.size = size.QuadPart;
    version.created = basic.CreationTime.QuadPart;
    version.modified = basic.LastWriteTime.QuadPart;
    version.attributes = basic.FileAttributes;
    return true;
}

std::optional<FileVersion> fileVersion(HANDLE file) {
    class HandleInput : public std::streambuf {
    public:
        explicit HandleInput(HANDLE file) : file_(file) {}
        std::uint64_t total = 0;
    private:
        std::streamsize xsgetn(char* output, std::streamsize count) override {
            std::streamsize done = 0;
            while (done < count) {
                const auto chunk = static_cast<DWORD>(std::min<std::streamsize>(count - done, 64 * 1024));
                DWORD read = 0;
                if (!ReadFile(file_, output + done, chunk, &read, nullptr)) throw std::ios_base::failure("export read");
                if (read == 0) break;
                total += read;
                done += read;
            }
            return done;
        }
        HANDLE file_;
    } source(file);
    FileVersion before{}, after{};
    if (!versionMetadata(file, before) || !SetFilePointerEx(file, LARGE_INTEGER{}, nullptr, FILE_BEGIN))
        return std::nullopt;
    std::istream input(&source);
    const auto digest = sha256Stream(input);
    if (digest.size() != before.sha256.size() || source.total != static_cast<std::uint64_t>(before.size) ||
        !versionMetadata(file, after) || !(before == after)) return std::nullopt;
    std::copy(digest.begin(), digest.end(), before.sha256.begin());
    return before;
}

bool matchesPublishedReplacement(HANDLE file, FileVersion expected, std::int64_t originalCreation) {
    const auto actual = fileVersion(file);
    if (!actual) return false;
    // NTFS can preserve the old name's creation time on a rename to that name.
    if (actual->created == originalCreation) expected.created = originalCreation;
    return *actual == expected;
}

template<std::size_t N>
std::wstring_view field(const wchar_t (&text)[N]) {
    const auto end = std::find(std::begin(text), std::end(text), L'\0');
    return end == std::end(text) ? std::wstring_view{} : std::wstring_view(text, end - text);
}

template<std::size_t N>
bool setField(wchar_t (&text)[N], std::wstring_view value) {
    if (value.empty() || value.size() >= N || value.find(L'\0') != value.npos) return false;
    std::copy(value.begin(), value.end(), std::begin(text));
    return true;
}

bool identity(HANDLE file, FILE_ID_INFO& id) {
    return GetFileInformationByHandleEx(file, FileIdInfo, &id, sizeof(id)) != FALSE;
}

bool sameIdentity(const FILE_ID_INFO& a, const FILE_ID_INFO& b) {
    return a.VolumeSerialNumber == b.VolumeSerialNumber && std::memcmp(&a.FileId, &b.FileId, sizeof(a.FileId)) == 0;
}

std::wstring tokenFromIntentName(std::wstring_view name) {
    if (name.size() != intentPrefix.size() + 38 + intentSuffix.size() ||
        name.substr(0, intentPrefix.size()) != intentPrefix ||
        name.substr(name.size() - intentSuffix.size()) != intentSuffix) return {};
    std::wstring token(name.substr(intentPrefix.size(), 38));
    GUID guid{};
    wchar_t canonical[39]{};
    if (FAILED(CLSIDFromString(token.c_str(), &guid)) ||
        !StringFromGUID2(guid, canonical, ARRAYSIZE(canonical)) || !equalName(token, canonical)) return {};
    return token;
}

std::wstring replacementName(std::wstring_view token, const wchar_t* extension) {
    return std::wstring(intentPrefix) + std::wstring(token) + extension;
}

struct SealedIntent {
    DATA_BLOB blob{};
    ~SealedIntent() {
        if (blob.pbData) { SecureZeroMemory(blob.pbData, blob.cbData); LocalFree(blob.pbData); }
    }
};

bool transformIntent(DATA_BLOB input, SealedIntent& output, bool seal) {
    BYTE purpose[] = "GRAF Windows export replacement v1";
    DATA_BLOB entropy{sizeof(purpose), purpose};
    return (seal ? CryptProtectData(&input, nullptr, &entropy, nullptr, nullptr, CRYPTPROTECT_UI_FORBIDDEN, &output.blob)
        : CryptUnprotectData(&input, nullptr, &entropy, nullptr, nullptr, CRYPTPROTECT_UI_FORBIDDEN, &output.blob)) != FALSE;
}

bool removeExactFile(File& file) {
    FILE_DISPOSITION_INFO_EX disposition{FILE_DISPOSITION_FLAG_DELETE | FILE_DISPOSITION_FLAG_POSIX_SEMANTICS |
        FILE_DISPOSITION_FLAG_IGNORE_READONLY_ATTRIBUTE};
    if (!SetFileInformationByHandle(file.value, FileDispositionInfoEx, &disposition, sizeof(disposition))) return false;
    file.reset();
    return true;
}

bool removeIntent(File& file, HANDLE journal) {
    return removeExactFile(file) && FlushFileBuffers(journal);
}

struct ObservedName {
    File file;
    FILE_ID_INFO id{};
    bool known = false;
};

ObservedName observeName(HANDLE folder, std::wstring_view name) {
    constexpr auto missing = static_cast<NTSTATUS>(0xC0000034L); // STATUS_OBJECT_NAME_NOT_FOUND
    NTSTATUS error = 0;
    auto file = openRelative(folder, name, DELETE | FILE_READ_DATA | FILE_READ_ATTRIBUTES,
        FILE_SHARE_READ, FILE_OPEN, FILE_NON_DIRECTORY_FILE, nullptr, &error);
    FILE_ID_INFO id{};
    const auto known = file ? plainObject(file.value, false) && identity(file.value, id) &&
        canonicalFilename(file.value, name) : error == missing;
    return {std::move(file), id, known};
}

struct ExportMta {
    CO_MTA_USAGE_COOKIE cookie = nullptr;
    ExportMta() { (void)CoIncrementMTAUsage(&cookie); }
    ~ExportMta() { if (cookie) (void)CoDecrementMTAUsage(cookie); }
};

const std::shared_ptr<ExportMta>& exportMta() {
    static const auto mta = std::make_shared<ExportMta>();
    return mta;
}

} // namespace

void ExportCommitPermission::revoke() noexcept {
    auto expected = State::pending;
    state_.compare_exchange_strong(expected, State::revoked);
}

bool ExportCommitPermission::pending() const noexcept { return state_.load() == State::pending; }

bool ExportCommitPermission::beginCommit() noexcept {
    auto expected = State::pending;
    return state_.compare_exchange_strong(expected, State::committing);
}

bool validExportFilename(std::wstring_view name) noexcept {
    return validPathComponent(name);
}

struct ExportFolderWorker::State {
    std::mutex mutex;
    std::condition_variable changed;
    ExportCommitPermission permission;
    std::atomic<Status> status{Status::preparing};
    std::wstring name;
};

ExportFolderWorker::ExportFolderWorker(std::shared_ptr<State> state) : state_(std::move(state)) {}
ExportFolderWorker::~ExportFolderWorker() { revoke(); }

std::unique_ptr<ExportFolderWorker> ExportFolderWorker::start(std::filesystem::path parent) {
    try {
        const auto mta = exportMta();
        if (!mta->cookie) return {};
        auto state = std::make_shared<State>();
        auto worker = std::unique_ptr<ExportFolderWorker>(new ExportFolderWorker(state));
        std::thread([state, parent = std::move(parent), mta] {
            auto result = Status::failed;
            if (mta->cookie && SUCCEEDED(RoInitialize(RO_INIT_MULTITHREADED))) {
                try {
                    auto pinned = pinLocalDirectory(parent);
                    if (pinned.empty()) result = Status::unavailable;
                    else {
                        std::unique_lock lock(state->mutex);
                        if (state->permission.pending()) state->status = Status::ready;
                        state->changed.wait(lock, [&] { return !state->name.empty() || !state->permission.pending(); });
                        const auto name = std::move(state->name);
                        lock.unlock();
                        if (!state->permission.beginCommit()) result = Status::cancelled;
                        else {
                            NTSTATUS failure{};
                            const auto folder = openRelative(pinned.back().value, name, FILE_READ_ATTRIBUTES,
                                FILE_SHARE_READ | FILE_SHARE_WRITE, FILE_CREATE, FILE_DIRECTORY_FILE, nullptr, &failure);
                            result = folder ? Status::created : failure == nameCollision ? Status::conflict : Status::failed;
                        }
                    }
                } catch (...) {}
                RoUninitialize();
            }
            state->status = result;
        }).detach();
        return worker;
    } catch (...) { return {}; }
}

ExportFolderWorker::Status ExportFolderWorker::status() const noexcept { return state_->status.load(); }

bool ExportFolderWorker::create(std::wstring name) {
    if (!validExportFilename(name)) return false;
    std::lock_guard lock(state_->mutex);
    if (state_->status != Status::ready || !state_->permission.pending()) return false;
    state_->name = std::move(name);
    state_->status = Status::creating;
    state_->changed.notify_one();
    return true;
}

void ExportFolderWorker::revoke() noexcept {
    state_->permission.revoke();
    std::lock_guard lock(state_->mutex);
    state_->changed.notify_one();
}

struct ExportDownloadScratch::State {
    struct Replacement {
        std::vector<File> folders;
        File original;
        std::filesystem::path folder;
        std::wstring filename;
        FileVersion version;
        std::uint64_t preparation;
    };
    std::vector<File> parent;
    std::optional<File> directory;
    std::optional<File> completed;
    std::vector<File> targetDirs;
    std::optional<Replacement> replacement;
    std::uint64_t downloadedBytes = 0;
    std::filesystem::path download;
    bool preserve = false;
    ~State() {
        completed.reset();
        if (preserve || !directory || !*directory || !plainObject(directory->value, true)) return;
        removeOwnedDownload(directory->value, kDownloadFile);
        removeOwnedDownload(directory->value, kPartialDownloadFile);
        FILE_DISPOSITION_INFO remove{TRUE}; // Only removes an empty directory.
        (void)SetFileInformationByHandle(directory->value, FileDispositionInfo, &remove, sizeof(remove));
    }
};

ExportDownloadScratch::ExportDownloadScratch(std::unique_ptr<State> state) : state_(std::move(state)) {}
ExportDownloadScratch::~ExportDownloadScratch() = default;

std::unique_ptr<ExportDownloadScratch> ExportDownloadScratch::create() {
    try {
        PWSTR local = nullptr;
        const auto found = SHGetKnownFolderPath(FOLDERID_LocalAppData, KF_FLAG_DONT_VERIFY, nullptr, &local);
        const std::unique_ptr<wchar_t, decltype(&CoTaskMemFree)> localPath(local, &CoTaskMemFree);
        if (FAILED(found) || !local) return {};
        auto state = std::make_unique<State>();
        state->parent = pinLocalDirectory(local);
        if (state->parent.empty()) return {};
        GUID id{};
        wchar_t identifier[40]{};
        PrivateSecurity security;
        if (FAILED(CoCreateGuid(&id)) || !StringFromGUID2(id, identifier, ARRAYSIZE(identifier)) || !security.initialize(true))
            return {};
        const auto name = std::wstring(L"graf-export-download-") + identifier;
        state->download = std::filesystem::path(local) / name / kDownloadFile;
        state->directory.emplace(openRelative(state->parent.back().value, name, DELETE | FILE_TRAVERSE | FILE_READ_ATTRIBUTES,
            FILE_SHARE_READ | FILE_SHARE_WRITE, FILE_CREATE, FILE_DIRECTORY_FILE, security.descriptor.value));
        if (!*state->directory || !plainObject(state->directory->value, true)) return {};
        return std::unique_ptr<ExportDownloadScratch>(new ExportDownloadScratch(std::move(state)));
    } catch (...) { return {}; }
}

const std::filesystem::path& ExportDownloadScratch::downloadPath() const noexcept { return state_->download; }

void ExportDownloadScratch::leaveIfBrowserMayBeWriting() noexcept { state_->preserve = true; }

bool ExportDownloadScratch::pinCompletedDownload(std::uint64_t downloadedBytes) {
    if (state_->completed || !plainObject(state_->directory->value, true)) return false;
    auto input = openRelative(state_->directory->value, kDownloadFile, FILE_READ_DATA | FILE_READ_ATTRIBUTES,
        FILE_SHARE_READ, FILE_OPEN, FILE_NON_DIRECTORY_FILE);
    if (!input || !plainObject(input.value, false) || !exactSize(input.value, downloadedBytes)) return false;
    state_->downloadedBytes = downloadedBytes;
    state_->completed.emplace(std::move(input));
    return true;
}

bool ExportDownloadScratch::pinDestination(const std::filesystem::path& folder) {
    state_->targetDirs.clear();
    state_->targetDirs = pinLocalDirectory(folder);
    return !state_->targetDirs.empty();
}

ExportSaveResult ExportDownloadScratch::saveNew(std::wstring_view filename, ExportCommitPermission& permission) {
    if (!permission.pending()) return ExportSaveResult::cancelled;
    if (!validExportFilename(filename)) return ExportSaveResult::invalidName;
    if (!state_->completed) return ExportSaveResult::incompleteDownload;
    try {
        const auto input = state_->completed->value;
        const auto downloadedBytes = state_->downloadedBytes;
        if (!plainObject(input, false) || !exactSize(input, downloadedBytes) ||
            !SetFilePointerEx(input, LARGE_INTEGER{}, nullptr, FILE_BEGIN))
            return ExportSaveResult::incompleteDownload;

        const auto& targetDirs = state_->targetDirs;
        if (targetDirs.empty()) return ExportSaveResult::unavailableLocation;
        const auto target = targetDirs.back().value;
        const auto locationAllowed = [&] {
            return std::all_of(targetDirs.begin(), targetDirs.end(),
                [](const File& dir) { return plainObject(dir.value, true); }) && outsideCloudSyncRoot(target);
        };
        if (!locationAllowed()) return ExportSaveResult::unavailableLocation;
        GUID id{};
        wchar_t identifier[40]{};
        PrivateSecurity security;
        if (FAILED(CoCreateGuid(&id)) || !StringFromGUID2(id, identifier, ARRAYSIZE(identifier)) || !security.initialize())
            return ExportSaveResult::ioError;
        const auto temp = std::wstring(L".graf-export-") + identifier + L".tmp";
        StagedFile staged{openRelative(target, temp, DELETE | FILE_WRITE_DATA | FILE_READ_ATTRIBUTES,
            0, FILE_CREATE, FILE_NON_DIRECTORY_FILE, security.descriptor.value)};
        if (!staged.file || !plainObject(staged.file.value, false)) return ExportSaveResult::unavailableLocation;

        const auto copied = copyDownload(input, staged.file.value, downloadedBytes, permission);
        if (copied != ExportSaveResult::saved) return copied;
        if (!exactSize(staged.file.value, downloadedBytes) || !FlushFileBuffers(staged.file.value))
            return ExportSaveResult::unavailableLocation;
        if (!locationAllowed()) return ExportSaveResult::unavailableLocation;
        if (!permission.beginCommit()) return ExportSaveResult::cancelled;
        const auto result = renameWithoutReplacement(staged.file.value, filename);
        staged.published = result == ExportSaveResult::saved;
        return result;
    } catch (...) {
        return ExportSaveResult::ioError;
    }
}

std::optional<std::uint64_t> ExportDownloadScratch::prepareReplacement(const std::filesystem::path& folder,
    std::wstring_view filename) {
    state_->replacement.reset();
    if (!replacementFilename(filename)) return std::nullopt;
    try {
        auto folders = pinLocalDirectory(folder, directoryFlushAccess);
        if (folders.empty()) return std::nullopt;
        auto original = openRelative(folders.back().value, filename, DELETE | FILE_READ_DATA | FILE_READ_ATTRIBUTES,
            FILE_SHARE_READ, FILE_OPEN, FILE_NON_DIRECTORY_FILE);
        if (!original || !canonicalFilename(original.value, filename) || !FlushFileBuffers(folders.back().value))
            return std::nullopt;
        const auto version = fileVersion(original.value);
        if (!version) return std::nullopt;
        static std::atomic<std::uint64_t> nextPreparation{1};
        const auto preparation = nextPreparation.fetch_add(1, std::memory_order_relaxed);
        if (preparation == 0) return std::nullopt;
        state_->replacement.emplace(State::Replacement{std::move(folders), std::move(original), folder,
            std::wstring(filename), *version, preparation});
        return preparation;
    } catch (...) { return std::nullopt; }
}

ExportSaveResult ExportDownloadScratch::saveReplacement(const std::filesystem::path& privateJournal,
    std::uint64_t preparation, ExportCommitPermission& permission) {
    if (!state_->replacement || state_->replacement->preparation != preparation) return ExportSaveResult::cancelled;
    auto chosen = std::move(state_->replacement);
    state_->replacement.reset();
    if (!permission.pending()) return ExportSaveResult::cancelled;
    if (!state_->completed) return ExportSaveResult::incompleteDownload;
    bool handedToRecovery = false;
    try {
        const auto input = state_->completed->value;
        const auto size = state_->downloadedBytes;
        if (!plainObject(input, false) || !exactSize(input, size) ||
            !SetFilePointerEx(input, LARGE_INTEGER{}, nullptr, FILE_BEGIN)) return ExportSaveResult::incompleteDownload;
        auto journals = pinLocalDirectory(privateJournal, directoryFlushAccess);
        if (journals.empty()) return ExportSaveResult::unavailableLocation;
        const auto journal = journals.back().value;
        const auto target = chosen->folders.back().value;
        auto record = std::make_unique<ReplacementIntent>();
        if (!privateObject(journal, true) || !identity(journal, record->journal) ||
            !identity(target, record->directory) || sameIdentity(record->directory, record->journal) ||
            !identity(chosen->original.value, record->original) || !plainObject(chosen->original.value, false) ||
            !setField(record->folder, chosen->folder.native()) || !setField(record->finalName, chosen->filename))
            return ExportSaveResult::unavailableLocation;
        record->originalVersion = chosen->version;

        GUID guid{};
        wchar_t token[39]{};
        PrivateSecurity security;
        if (FAILED(CoCreateGuid(&guid)) || !StringFromGUID2(guid, token, ARRAYSIZE(token)) ||
            !setField(record->token, token) || !security.initialize(false, true)) return ExportSaveResult::ioError;
        const auto temp = replacementName(token, L".tmp");
        const auto backup = replacementName(token, L".bak");
        const auto intent = replacementName(token, L".intent");
        StagedFile staged{openRelative(target, temp, DELETE | FILE_READ_DATA | FILE_WRITE_DATA | FILE_READ_ATTRIBUTES,
            0, FILE_CREATE, FILE_NON_DIRECTORY_FILE, security.descriptor.value)};
        if (!staged.file || !plainObject(staged.file.value, false)) return ExportSaveResult::unavailableLocation;
        const auto copied = copyDownload(input, staged.file.value, size, permission);
        if (copied != ExportSaveResult::saved) return copied;
        if (!exactSize(staged.file.value, size) || !identity(staged.file.value, record->replacement) ||
            !FlushFileBuffers(staged.file.value) || !outsideCloudSyncRoot(target) ||
            !FlushFileBuffers(target)) return ExportSaveResult::unavailableLocation;
        const auto version = fileVersion(staged.file.value);
        if (!version || static_cast<std::uint64_t>(version->size) != size) return ExportSaveResult::ioError;
        record->replacementVersion = *version;

        SealedIntent sealed;
        if (!transformIntent({sizeof(ReplacementIntent), reinterpret_cast<BYTE*>(record.get())}, sealed, true) ||
            sealed.blob.cbData == 0 || sealed.blob.cbData > 128 * 1024) return ExportSaveResult::ioError;
        auto intentFile = openRelative(journal, intent, DELETE | FILE_WRITE_DATA | FILE_READ_ATTRIBUTES | READ_CONTROL,
            0, FILE_CREATE, FILE_NON_DIRECTORY_FILE, security.descriptor.value);
        if (!intentFile) return ExportSaveResult::unavailableLocation;
        DWORD written = 0;
        if (!privateObject(intentFile.value, false) ||
            !WriteFile(intentFile.value, sealed.blob.pbData, sealed.blob.cbData, &written, nullptr) ||
            written != sealed.blob.cbData || !FlushFileBuffers(intentFile.value) || !FlushFileBuffers(journal)) {
            return removeIntent(intentFile, journal) ? ExportSaveResult::unavailableLocation : ExportSaveResult::recoveryRequired;
        }
        handedToRecovery = true;
        staged.published = true; // From here the durable intent owns the staged file.
        const auto abandon = [&](ExportSaveResult result) {
            if (!removeIntent(intentFile, journal)) return ExportSaveResult::recoveryRequired;
            staged.published = false;
            return result;
        };
        const auto plainDirectories = [](const auto& chain) {
            return std::all_of(chain.begin(), chain.end(), [](const File& dir) { return plainObject(dir.value, true); });
        };
        if (!plainDirectories(chosen->folders) || !plainDirectories(journals) ||
            !outsideCloudSyncRoot(target) || !privateObject(journal, true) ||
            !(fileVersion(chosen->original.value) == record->originalVersion))
            return abandon(ExportSaveResult::unavailableLocation);
        if (!permission.beginCommit()) return abandon(ExportSaveResult::cancelled);
        GRAF_EXPORT_CHECKPOINT("intent");
        if (renameWithoutReplacement(chosen->original.value, backup) != ExportSaveResult::saved ||
            !FlushFileBuffers(target)) return ExportSaveResult::recoveryRequired;
        GRAF_EXPORT_CHECKPOINT("backup");
        if (renameWithoutReplacement(staged.file.value, chosen->filename) != ExportSaveResult::saved ||
            !FlushFileBuffers(target)) return ExportSaveResult::recoveryRequired;
        GRAF_EXPORT_CHECKPOINT("publish");
        if (!canonicalFilename(staged.file.value, chosen->filename) ||
            !matchesPublishedReplacement(staged.file.value, record->replacementVersion, record->originalVersion.created) ||
            !(fileVersion(chosen->original.value) == record->originalVersion) ||
            !removeExactFile(chosen->original) || !FlushFileBuffers(target)) return ExportSaveResult::recoveryRequired;
        GRAF_EXPORT_CHECKPOINT("cleanup");
        if (!removeIntent(intentFile, journal)) return ExportSaveResult::recoveryRequired;
        return ExportSaveResult::saved;
    } catch (...) {
        return handedToRecovery ? ExportSaveResult::recoveryRequired : ExportSaveResult::ioError;
    }
}

ExportSaveResult ExportDownloadScratch::recoverReplacement(const std::filesystem::path& privateJournal,
    std::wstring_view intentName) {
    using Result = ExportSaveResult;
    try {
        const auto token = tokenFromIntentName(intentName);
        if (token.empty()) return Result::recoveryRequired;
        auto journals = pinLocalDirectory(privateJournal, directoryFlushAccess);
        if (journals.empty() || !privateObject(journals.back().value, true)) return Result::recoveryRequired;
        const auto journal = journals.back().value;
        auto file = openRelative(journal, intentName, DELETE | FILE_READ_DATA | FILE_READ_ATTRIBUTES | READ_CONTROL,
            0, FILE_OPEN, FILE_NON_DIRECTORY_FILE);
        LARGE_INTEGER size{};
        if (!file || !privateObject(file.value, false) || !GetFileSizeEx(file.value, &size) ||
            size.QuadPart <= 0 || size.QuadPart > 128 * 1024) return Result::recoveryRequired;
        std::vector<BYTE> bytes(static_cast<std::size_t>(size.QuadPart));
        DWORD read = 0;
        if (!ReadFile(file.value, bytes.data(), static_cast<DWORD>(bytes.size()), &read, nullptr) ||
            read != bytes.size()) return Result::recoveryRequired;
        SealedIntent opened;
        if (!transformIntent({read, bytes.data()}, opened, false) || opened.blob.cbData != sizeof(ReplacementIntent))
            return Result::recoveryRequired;
        auto record = std::make_unique<ReplacementIntent>();
        std::memcpy(record.get(), opened.blob.pbData, sizeof(ReplacementIntent));
        const auto finalName = field(record->finalName);
        const auto tempName = replacementName(token, L".tmp");
        const auto backupName = replacementName(token, L".bak");
        if (record->version != intentVersion || record->reserved != 0 || !equalName(field(record->token), token) ||
            !replacementFilename(finalName) ||
            sameIdentity(record->original, record->replacement) ||
            record->original.VolumeSerialNumber != record->directory.VolumeSerialNumber ||
            record->replacement.VolumeSerialNumber != record->directory.VolumeSerialNumber) return Result::recoveryRequired;

        auto folders = pinLocalDirectory(std::filesystem::path(field(record->folder)), directoryFlushAccess);
        FILE_ID_INFO id{}, journalId{};
        if (folders.empty() || !identity(folders.back().value, id) || !sameIdentity(id, record->directory) ||
            !identity(journal, journalId) || !sameIdentity(journalId, record->journal) ||
            sameIdentity(journalId, id)) return Result::recoveryRequired;
        const auto target = folders.back().value;
        auto final = observeName(target, finalName);
        auto backup = observeName(target, backupName);
        auto temp = observeName(target, tempName);
        if (!final.known || !backup.known || !temp.known ||
            (backup.file && !sameIdentity(backup.id, record->original)) ||
            (temp.file && (!sameIdentity(temp.id, record->replacement) ||
                !(fileVersion(temp.file.value) == record->replacementVersion)))) return Result::recoveryRequired;
        Result result = Result::cancelled;
        if (final.file && sameIdentity(final.id, record->replacement) && !temp.file) {
            if (!matchesPublishedReplacement(final.file.value, record->replacementVersion, record->originalVersion.created) ||
                !FlushFileBuffers(target) || (backup.file && (!(fileVersion(backup.file.value) == record->originalVersion) ||
                    !removeExactFile(backup.file)))) return Result::recoveryRequired;
            result = Result::saved;
        } else if (final.file && sameIdentity(final.id, record->original) && !backup.file) {
            if (!(fileVersion(final.file.value) == record->originalVersion) ||
                (temp.file && !removeExactFile(temp.file))) return Result::recoveryRequired;
        } else if (!final.file && backup.file) {
            if (!(fileVersion(backup.file.value) == record->originalVersion) ||
                renameWithoutReplacement(backup.file.value, finalName) != Result::saved ||
                !FlushFileBuffers(target) || !canonicalFilename(backup.file.value, finalName) ||
                !(fileVersion(backup.file.value) == record->originalVersion) ||
                (temp.file && !removeExactFile(temp.file))) return Result::recoveryRequired;
        } else return Result::recoveryRequired;
        if (!FlushFileBuffers(target)) return Result::recoveryRequired;
        GRAF_EXPORT_CHECKPOINT("recovery-cleanup");
        if (!removeIntent(file, journal)) return Result::recoveryRequired;
        return result;
    } catch (...) { return Result::recoveryRequired; }
}

struct ExportSaveWorker::State {
    std::mutex mutex;
    std::condition_variable changed;
    std::optional<ExportCommitPermission> permission{std::in_place};
    std::optional<std::filesystem::path> ready;
    std::optional<std::uint64_t> bytes;
    std::optional<ExportSaveResult> result;
    std::optional<std::filesystem::path> retry;
    bool handedToBrowser = false;
    bool stopped = false;
    bool revoked = false;
};

ExportSaveWorker::ExportSaveWorker(std::shared_ptr<State> state) : state_(std::move(state)) {}
ExportSaveWorker::~ExportSaveWorker() { revoke(); }

std::shared_ptr<ExportSaveWorker> ExportSaveWorker::start(std::filesystem::path destination) {
    try {
        // Keep COM's MTA alive between independent exports as well as during a job.
        const auto mta = exportMta();
        if (!mta->cookie) return {};
        auto state = std::make_shared<State>();
        auto worker = std::shared_ptr<ExportSaveWorker>(new ExportSaveWorker(state));
        std::thread([state, destination = std::move(destination), apartment = mta]() mutable {
            auto result = ExportSaveResult::ioError;
            if (apartment->cookie && SUCCEEDED(RoInitialize(RO_INIT_MULTITHREADED))) {
                try {
                    auto scratch = ExportDownloadScratch::create();
                    if (scratch && !validExportFilename(destination.filename().native())) {
                        result = ExportSaveResult::invalidName;
                    } else if (scratch) {
                        bool pinFolder = true;
                        bool completed = false;
                        for (;;) {
                            if (!state->permission->pending()) {
                                result = ExportSaveResult::cancelled;
                                break;
                            }
                            if (pinFolder && !scratch->pinDestination(destination.parent_path())) {
                                result = ExportSaveResult::unavailableLocation;
                            } else {
                                if (!completed) {
                                    std::unique_lock lock(state->mutex);
                                    if (!state->revoked && !state->stopped) state->ready = scratch->downloadPath();
                                    state->changed.wait(lock, [&] { return state->revoked || state->stopped; });
                                    if (state->revoked && state->handedToBrowser && !state->stopped &&
                                        !state->changed.wait_for(lock, std::chrono::seconds(10), [&] { return state->stopped; }))
                                        scratch->leaveIfBrowserMayBeWriting();
                                    const auto bytes = state->revoked ? std::nullopt : state->bytes;
                                    result = state->revoked ? ExportSaveResult::cancelled : ExportSaveResult::incompleteDownload;
                                    lock.unlock();
                                    if (!bytes || !scratch->pinCompletedDownload(*bytes)) break;
                                    completed = true;
                                }
                                result = scratch->saveNew(destination.filename().native(), *state->permission);
                            }
                            if (!retryableExportSave(result)) break;
                            std::unique_lock lock(state->mutex);
                            if (!state->revoked) {
                                state->result = result;
                                state->changed.wait(lock, [&] { return state->revoked || state->retry.has_value(); });
                            }
                            if (state->revoked) {
                                result = ExportSaveResult::cancelled;
                                break;
                            }
                            auto next = std::move(*state->retry);
                            state->retry.reset();
                            state->permission.emplace();
                            lock.unlock();
                            pinFolder = result == ExportSaveResult::unavailableLocation ||
                                next.parent_path() != destination.parent_path();
                            destination = std::move(next);
                        }
                    }
                } catch (...) { result = ExportSaveResult::ioError; }
                RoUninitialize();
            }
            std::lock_guard lock(state->mutex);
            state->ready.reset();
            state->result = result;
        }).detach();
        return worker;
    } catch (...) { return {}; }
}

std::optional<std::filesystem::path> ExportSaveWorker::takeBrowserPath() {
    std::lock_guard lock(state_->mutex);
    if (state_->revoked || state_->stopped || !state_->ready) return {};
    state_->handedToBrowser = true;
    return std::exchange(state_->ready, std::nullopt);
}

void ExportSaveWorker::browserStopped(std::optional<std::uint64_t> completedBytes) noexcept {
    std::lock_guard lock(state_->mutex);
    if (state_->stopped) return;
    state_->stopped = true;
    if (state_->handedToBrowser) state_->bytes = completedBytes;
    state_->changed.notify_one();
}

void ExportSaveWorker::revoke() noexcept {
    std::lock_guard lock(state_->mutex);
    state_->permission->revoke();
    state_->revoked = true;
    if (state_->result && retryableExportSave(*state_->result)) state_->result.reset();
    state_->changed.notify_one();
}

bool ExportSaveWorker::retryDestination(std::filesystem::path destination) {
    if (!destination.is_absolute() || !validExportFilename(destination.filename().native())) return false;
    std::lock_guard lock(state_->mutex);
    if (state_->revoked || !state_->result || !retryableExportSave(*state_->result)) return false;
    state_->retry = std::move(destination);
    state_->result.reset();
    state_->changed.notify_one();
    return true;
}

std::optional<ExportSaveResult> ExportSaveWorker::result() {
    std::lock_guard lock(state_->mutex);
    return state_->result;
}

} // namespace graf::windows
#endif
