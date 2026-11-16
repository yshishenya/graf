#pragma once

#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <string_view>

namespace graf::windows {

enum class AppUpdateState { idle, checking, current, available, required, unknown, unavailable, error,
                            preparing, installing, installed, cancelled };
enum class AppUpdateReason { none, noPackage, noAssociation, invalidSource, unsupported, timeout,
                             noApprovedRelease, captureActive, custodyUnhealthy, notReady, restartFailed };
struct AppUpdateResult {
    AppUpdateState state = AppUpdateState::idle;
    AppUpdateReason reason = AppUpdateReason::none;
};

// One OS operation, polled by the existing shell timer. No completion callback
// owns the window; cancellation is retained until the OS operation is terminal.
class AppUpdateCheckOperation {
public:
    virtual ~AppUpdateCheckOperation() = default;
    virtual std::optional<AppUpdateResult> poll() = 0;
    virtual void cancel() noexcept = 0;
};

// Native release-owner input only, never populated from registry, environment or
// web data. Approval covers the immutable feed's packages/version/signatures,
// redirects and absence of automatic installation. Association alone is NOT
// approval. FullName pins the installed baseline, including version/architecture.
struct AppUpdateApprovedRelease {
    std::wstring packageFullName;
    std::wstring publisher;
    std::wstring architecture;
    std::wstring appInstallerUri;
    [[nodiscard]] bool matchesPackage(std::wstring_view fullName, std::wstring_view actualPublisher,
                                      std::wstring_view actualArchitecture, std::wstring_view source) const noexcept;
};

class AppUpdateInstallOperation {
public:
    virtual ~AppUpdateInstallOperation() = default;
    // Local package/source validation and restart registration, never installation.
    virtual AppUpdateReason prepare(const AppUpdateApprovedRelease&) = 0;
    // Starts OS deployment. A throw must mean NO OS operation was created.
    virtual void start() = 0;
    // A value proves OS terminal state. A throw does NOT prove completion.
    virtual std::optional<AppUpdateResult> poll() = 0;
    virtual void cancel() noexcept = 0;
};

class WindowsAppUpdateController final {
public:
    using Clock = std::chrono::steady_clock;
    using Factory = std::function<std::unique_ptr<AppUpdateCheckOperation>()>;
    using InstallFactory = std::function<std::unique_ptr<AppUpdateInstallOperation>()>;
    using Now = std::function<Clock::time_point()>;
    explicit WindowsAppUpdateController(Factory factory = {},
        std::optional<AppUpdateApprovedRelease> approvedRelease = std::nullopt,
        InstallFactory installFactory = {}, Now now = {});
    ~WindowsAppUpdateController();
    bool check(Clock::time_point now);
    void tick(Clock::time_point now);
    // UI-thread only. Shell must keep this controller alive while installing,
    // gate all new work, drain existing mutations and poll through OS completion.
    bool beginInstall(Clock::time_point now, bool captureActive, bool custodyHealthy);
    void tick(Clock::time_point now, bool workDrained, const std::function<bool()>& freshReady);
    void close() noexcept;
    [[nodiscard]] AppUpdateResult result() const noexcept { return result_; }
    [[nodiscard]] bool busy() const noexcept {
        return nativeCallInProgress_ || operation_ != nullptr || blocksNewWork();
    }
    [[nodiscard]] bool blocksNewWork() const noexcept {
        return result_.state == AppUpdateState::preparing || installOperation_ != nullptr;
    }
    [[nodiscard]] bool canInstall() const noexcept { return available() && !busy() && approvedRelease_.has_value(); }
    [[nodiscard]] bool available() const noexcept {
        return result_.state == AppUpdateState::available || result_.state == AppUpdateState::required;
    }
private:
    void cancel() noexcept;
    void cancelInstall() noexcept;
    Factory factory_;
    std::unique_ptr<AppUpdateCheckOperation> operation_;
    Clock::time_point started_{};
    AppUpdateResult result_;
    bool discardResult_ = false;
    const std::optional<AppUpdateApprovedRelease> approvedRelease_;
    InstallFactory installFactory_;
    Now now_;
    std::unique_ptr<AppUpdateInstallOperation> installOperation_;
    std::uint64_t installGeneration_ = 0;
    bool nativeCallInProgress_ = false;
    bool installCancelRequested_ = false;
    bool installCancelSent_ = false;
};

[[nodiscard]] std::wstring appUpdateDetail(AppUpdateResult result, bool operationPending = false);

} // namespace graf::windows
