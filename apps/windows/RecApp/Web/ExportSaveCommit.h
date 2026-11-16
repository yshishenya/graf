#pragma once

#ifdef _WIN32
#include <atomic>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <string_view>

namespace graf::windows {

enum class ExportSaveResult { saved, cancelled, nameConflict, invalidName, unavailableLocation, incompleteDownload, ioError, recoveryRequired };
[[nodiscard]] constexpr bool retryableExportSave(ExportSaveResult result) noexcept {
    return result == ExportSaveResult::nameConflict || result == ExportSaveResult::unavailableLocation;
}

// The UI revokes, the worker commits. Only the first transition can win.
class ExportCommitPermission {
public:
    void revoke() noexcept;
    [[nodiscard]] bool pending() const noexcept;
    [[nodiscard]] bool beginCommit() noexcept;

private:
    enum class State { pending, revoked, committing };
    std::atomic<State> state_{State::pending};
};

[[nodiscard]] bool validExportFilename(std::wstring_view name) noexcept;

// Pin the destination off the UI thread before enabling the explicit Create action.
class ExportFolderWorker {
public:
    enum class Status { preparing, ready, creating, created, conflict, unavailable, failed, cancelled };
    [[nodiscard]] static std::unique_ptr<ExportFolderWorker> start(std::filesystem::path parent);
    ~ExportFolderWorker();
    [[nodiscard]] Status status() const noexcept;
    [[nodiscard]] bool create(std::wstring name);
    void revoke() noexcept;

private:
    struct State;
    explicit ExportFolderWorker(std::shared_ptr<State> state);
    std::shared_ptr<State> state_;
};

// Created, used and destroyed on the worker with a live WinRT apartment.
// Retain it until WebView2 has stopped writing.
class ExportDownloadScratch {
public:
    [[nodiscard]] static std::unique_ptr<ExportDownloadScratch> create();
    ~ExportDownloadScratch();

    [[nodiscard]] const std::filesystem::path& downloadPath() const noexcept;
    // Called only after WebView2 reports Completed. A successful pin survives retries.
    [[nodiscard]] bool pinCompletedDownload(std::uint64_t downloadedBytes);
    [[nodiscard]] bool pinDestination(const std::filesystem::path& folder);
    [[nodiscard]] ExportSaveResult saveNew(std::wstring_view filename, ExportCommitPermission& permission);
    // A confirmation is valid once, for this preparation only.
    [[nodiscard]] std::optional<std::uint64_t> prepareReplacement(const std::filesystem::path& folder,
        std::wstring_view filename);
    [[nodiscard]] ExportSaveResult saveReplacement(const std::filesystem::path& privateJournal,
        std::uint64_t preparation, ExportCommitPermission& permission);
    [[nodiscard]] static ExportSaveResult recoverReplacement(const std::filesystem::path& privateJournal,
        std::wstring_view intentName);
    void leaveIfBrowserMayBeWriting() noexcept;

private:
    struct State;
    explicit ExportDownloadScratch(std::unique_ptr<State> state);
    std::unique_ptr<State> state_;
};

// The browser stays on the window thread; the worker owns all file I/O.
class ExportSaveWorker {
public:
    [[nodiscard]] static std::shared_ptr<ExportSaveWorker> start(std::filesystem::path destination);
    ~ExportSaveWorker();
    [[nodiscard]] std::optional<std::filesystem::path> takeBrowserPath();
    void browserStopped(std::optional<std::uint64_t> completedBytes) noexcept;
    void revoke() noexcept;
    [[nodiscard]] bool retryDestination(std::filesystem::path destination);
    [[nodiscard]] std::optional<ExportSaveResult> result();

private:
    struct State;
    explicit ExportSaveWorker(std::shared_ptr<State> state);
    std::shared_ptr<State> state_;
};

} // namespace graf::windows
#endif
