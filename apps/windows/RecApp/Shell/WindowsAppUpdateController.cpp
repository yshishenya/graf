#include "WindowsAppUpdateController.h"

#include <algorithm>
#include <utility>

#ifdef _WIN32
#include <windows.h>
#include <winrt/Windows.ApplicationModel.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Management.Deployment.h>
#include <winrt/Windows.System.h>
#pragma comment(lib, "windowsapp.lib")
#endif

namespace graf::windows {
namespace {

class NativeUpdateCheck final : public AppUpdateCheckOperation {
public:
    NativeUpdateCheck() {
#ifdef _WIN32
        using namespace winrt::Windows;
        try {
            // CheckUpdateAvailabilityAsync on Package::Current has a documented
            // AccessDenied bug. Resolve the same identity for the current user.
            const auto identity = ApplicationModel::Package::Current().Id().FullName();
            const auto package = Management::Deployment::PackageManager{}.FindPackageForUser(L"", identity);
            if (!package || package.Id().FullName() != identity) {
                result_ = {AppUpdateState::unavailable, AppUpdateReason::noPackage};
                return;
            }
            const auto info = package.GetAppInstallerInfo();
            if (!info || !info.Uri()) {
                result_ = {AppUpdateState::unavailable, AppUpdateReason::noAssociation};
                return;
            }
            const auto uri = info.Uri();
            if (uri.SchemeName() != L"https" || uri.Host().empty() ||
                !uri.UserName().empty() || !uri.Password().empty() ||
                !uri.Query().empty() || !uri.Fragment().empty()) {
                result_ = {AppUpdateState::unavailable, AppUpdateReason::invalidSource};
                return;
            }
            // A registered source permits a check, not installation approval.
            operation_ = package.CheckUpdateAvailabilityAsync();
        } catch (const winrt::hresult_error& error) {
            result_ = error.code() == HRESULT_FROM_WIN32(APPMODEL_ERROR_NO_PACKAGE)
                ? AppUpdateResult{AppUpdateState::unavailable, AppUpdateReason::noPackage}
                : AppUpdateResult{AppUpdateState::error};
        }
#else
        result_ = {AppUpdateState::unavailable, AppUpdateReason::unsupported};
#endif
    }

    std::optional<AppUpdateResult> poll() override {
#ifdef _WIN32
        using namespace winrt::Windows;
        if (operation_) {
            if (operation_.Status() == Foundation::AsyncStatus::Started) return std::nullopt;
            const auto answer = operation_.GetResults();
            if (FAILED(answer.ExtendedError())) return AppUpdateResult{AppUpdateState::error};
            switch (answer.Availability()) {
            case ApplicationModel::PackageUpdateAvailability::NoUpdates: return AppUpdateResult{AppUpdateState::current};
            case ApplicationModel::PackageUpdateAvailability::Available: return AppUpdateResult{AppUpdateState::available};
            case ApplicationModel::PackageUpdateAvailability::Required: return AppUpdateResult{AppUpdateState::required};
            case ApplicationModel::PackageUpdateAvailability::Error: return AppUpdateResult{AppUpdateState::error};
            default: return AppUpdateResult{AppUpdateState::unknown};
            }
        }
#endif
        return result_;
    }

    void cancel() noexcept override {
#ifdef _WIN32
        try { if (operation_) operation_.Cancel(); } catch (...) {}
#endif
    }
private:
    AppUpdateResult result_{AppUpdateState::error};
#ifdef _WIN32
    winrt::Windows::Foundation::IAsyncOperation<winrt::Windows::ApplicationModel::PackageUpdateAvailabilityResult>
        operation_{nullptr};
#endif
};

class NativeUpdateInstall final : public AppUpdateInstallOperation {
public:
    ~NativeUpdateInstall() override {
#ifdef _WIN32
        // This adapter owns the app's update-only restart registration.
        if (restartRegistered_) (void)UnregisterApplicationRestart();
#endif
    }

    AppUpdateReason prepare(const AppUpdateApprovedRelease& approved) override {
#ifdef _WIN32
        using namespace winrt::Windows;
        const auto current = ApplicationModel::Package::Current();
        const auto identity = current.Id();
        manager_ = Management::Deployment::PackageManager{};
        const auto package = manager_.FindPackageForUser(L"", identity.FullName());
        if (!package || package.Id().FullName() != identity.FullName()) return AppUpdateReason::noPackage;
        const auto info = package.GetAppInstallerInfo();
        if (!info || !info.Uri()) return AppUpdateReason::noAssociation;
        const auto uri = info.Uri();
        if (uri.SchemeName() != L"https" || uri.Host().empty() ||
            !uri.UserName().empty() || !uri.Password().empty() ||
            !uri.Query().empty() || !uri.Fragment().empty() ||
            !approved.matchesPackage(identity.FullName(), identity.Publisher(),
                identity.Architecture() == System::ProcessorArchitecture::X64 ? L"x64" : L"unsupported",
                uri.AbsoluteUri()) || !package.Status().VerifyIsOK() ||
            package.SignatureKind() == ApplicationModel::PackageSignatureKind::None)
            return AppUpdateReason::invalidSource;
        // No download/parser/redirect authority is added here. The exact feed
        // must already be release-approved; the OS enforces package signatures.
        uri_ = uri;
        if (FAILED(RegisterApplicationRestart(L"", RESTART_NO_CRASH | RESTART_NO_HANG)))
            return AppUpdateReason::restartFailed;
        restartRegistered_ = true;
        return AppUpdateReason::none;
#else
        (void)approved;
        return AppUpdateReason::unsupported;
#endif
    }

    void start() override {
#ifdef _WIN32
        using namespace winrt::Windows::Management::Deployment;
        // Called only after the shell's fresh readiness check and deadline gate.
        // No unsigned/downgrade bypass, no installer command line or web URI.
        operation_ = manager_.AddPackageByAppInstallerFileAsync(uri_,
            AddPackageByAppInstallerOptions::ForceTargetAppShutdown |
                AddPackageByAppInstallerOptions::LimitToExistingPackages, nullptr);
#endif
    }

    std::optional<AppUpdateResult> poll() override {
#ifdef _WIN32
        using winrt::Windows::Foundation::AsyncStatus;
        // Status exceptions intentionally escape: controller retains admission
        // barrier unless the OS has positively reported a terminal state.
        const auto status = operation_.Status();
        if (status == AsyncStatus::Started) return std::nullopt;
        if (status == AsyncStatus::Canceled) return AppUpdateResult{AppUpdateState::cancelled};
        if (status == AsyncStatus::Error) return AppUpdateResult{AppUpdateState::error};
        if (status != AsyncStatus::Completed) return std::nullopt;
        try {
            const auto result = operation_.GetResults();
            return AppUpdateResult{SUCCEEDED(result.ExtendedErrorCode())
                ? AppUpdateState::installed : AppUpdateState::error};
        } catch (...) { return AppUpdateResult{AppUpdateState::error}; }
#else
        return AppUpdateResult{AppUpdateState::unavailable, AppUpdateReason::unsupported};
#endif
    }

    void cancel() noexcept override {
#ifdef _WIN32
        try { if (operation_) operation_.Cancel(); } catch (...) {}
#endif
    }
private:
#ifdef _WIN32
    winrt::Windows::Management::Deployment::PackageManager manager_{nullptr};
    winrt::Windows::Foundation::Uri uri_{nullptr};
    winrt::Windows::Foundation::IAsyncOperationWithProgress<
        winrt::Windows::Management::Deployment::DeploymentResult,
        winrt::Windows::Management::Deployment::DeploymentProgress> operation_{nullptr};
    bool restartRegistered_ = false;
#endif
};

} // namespace

bool AppUpdateApprovedRelease::matchesPackage(std::wstring_view fullName, std::wstring_view actualPublisher,
    std::wstring_view actualArchitecture, std::wstring_view source) const noexcept {
    const auto bounded = [](std::wstring_view value, std::size_t limit) {
        return !value.empty() && value.size() <= limit &&
            std::none_of(value.begin(), value.end(), [](wchar_t c) { return c < L' ' || c == 127; });
    };
    return bounded(packageFullName, 512) && bounded(publisher, 8192) &&
        architecture == L"x64" && bounded(appInstallerUri, 2048) &&
        packageFullName == fullName && publisher == actualPublisher &&
        architecture == actualArchitecture && appInstallerUri == source;
}

WindowsAppUpdateController::WindowsAppUpdateController(Factory factory,
    std::optional<AppUpdateApprovedRelease> approvedRelease, InstallFactory installFactory, Now now)
    : factory_(factory ? std::move(factory) : Factory{[] { return std::make_unique<NativeUpdateCheck>(); }}),
      approvedRelease_(std::move(approvedRelease)),
      installFactory_(installFactory ? std::move(installFactory)
          : InstallFactory{[] { return std::make_unique<NativeUpdateInstall>(); }}),
      now_(now ? std::move(now) : Now{[] { return Clock::now(); }}) {}

WindowsAppUpdateController::~WindowsAppUpdateController() { cancel(); cancelInstall(); }

bool WindowsAppUpdateController::check(Clock::time_point now) {
    if (busy()) return false;
    discardResult_ = false;
    started_ = now;
    result_ = {AppUpdateState::checking};
    nativeCallInProgress_ = true;
    try {
        operation_ = factory_();
        if (discardResult_) {
            if (operation_) operation_->cancel();
        } else if (!operation_) result_ = {AppUpdateState::error};
    } catch (...) { if (!discardResult_) result_ = {AppUpdateState::error}; }
    nativeCallInProgress_ = false;
    return true;
}

void WindowsAppUpdateController::tick(Clock::time_point now) {
    tick(now, false, {});
}

bool WindowsAppUpdateController::beginInstall(Clock::time_point now, bool captureActive, bool custodyHealthy) {
    if (busy()) return false;
    AppUpdateReason reason = AppUpdateReason::none;
    if (!approvedRelease_) reason = AppUpdateReason::noApprovedRelease;
    else if (captureActive) reason = AppUpdateReason::captureActive;
    else if (!custodyHealthy) reason = AppUpdateReason::custodyUnhealthy;
    else if (!available()) reason = AppUpdateReason::notReady;
    if (reason != AppUpdateReason::none) {
        result_ = {AppUpdateState::unavailable, reason};
        return false;
    }
    ++installGeneration_;
    started_ = now;
    installCancelRequested_ = installCancelSent_ = false;
    result_ = {AppUpdateState::preparing};
    return true;
}

void WindowsAppUpdateController::tick(Clock::time_point now, bool workDrained,
    const std::function<bool()>& freshReady) {
    // COM calls can dispatch UI messages. Keep operation ownership and the
    // preparation attempt unchanged until the outer call has returned.
    if (nativeCallInProgress_) return;
    if (installOperation_) {
        nativeCallInProgress_ = true;
        try {
            const auto answer = installOperation_->poll();
            if (answer) {
                // Cancel may lose to successful deployment. Report OS truth,
                // never fabricate rollback from the cancellation request.
                result_ = *answer;
                installOperation_.reset();
            }
        } catch (...) { /* Unknown OS state must retain the barrier and operation. */ }
        nativeCallInProgress_ = false;
        if (installCancelRequested_) cancelInstall();
        return;
    }
    if (result_.state == AppUpdateState::preparing) {
        if (now - started_ >= std::chrono::seconds(30)) {
            result_ = {AppUpdateState::error, AppUpdateReason::timeout};
            return;
        }
        if (!workDrained) return;
        const auto generation = installGeneration_;
        const auto stillPreparing = [&] {
            return generation == installGeneration_ && result_.state == AppUpdateState::preparing;
        };
        nativeCallInProgress_ = true;
        try {
            auto candidate = installFactory_();
            const auto reason = candidate ? candidate->prepare(*approvedRelease_) : AppUpdateReason::notReady;
            if (stillPreparing()) {
                if (reason != AppUpdateReason::none) result_ = {AppUpdateState::error, reason};
                else if (now_() - started_ >= std::chrono::seconds(30))
                    result_ = {AppUpdateState::error, AppUpdateReason::timeout};
                else {
                    const bool ready = freshReady && freshReady();
                    if (stillPreparing()) {
                        if (now_() - started_ >= std::chrono::seconds(30))
                            result_ = {AppUpdateState::error, AppUpdateReason::timeout};
                        else if (!ready) result_ = {AppUpdateState::unavailable, AppUpdateReason::notReady};
                        else {
                            installOperation_ = std::move(candidate);
                            result_ = {AppUpdateState::installing};
                            installOperation_->start();
                        }
                    }
                }
            }
        } catch (...) {
            if (generation == installGeneration_) {
                // start() may only throw before it has created an OS operation.
                installOperation_.reset();
                result_ = {AppUpdateState::error};
            }
        }
        nativeCallInProgress_ = false;
        if (installCancelRequested_) cancelInstall();
        return;
    }
    if (!operation_) return;
    nativeCallInProgress_ = true;
    // Deadline wins even if a late success is already queued when UI wakes.
    if (!discardResult_ && now - started_ >= std::chrono::seconds(30)) {
        result_ = {AppUpdateState::error, AppUpdateReason::timeout};
        cancel();
    }
    try {
        const auto answer = operation_->poll();
        if (!answer) {
            nativeCallInProgress_ = false;
            return;
        }
        if (!discardResult_) result_ = *answer;
    } catch (...) {
        if (!discardResult_) result_ = {AppUpdateState::error};
    }
    operation_.reset();
    nativeCallInProgress_ = false;
}

void WindowsAppUpdateController::cancel() noexcept {
    const bool sendCancel = operation_ && !discardResult_;
    discardResult_ = true;
    if (sendCancel) {
        const bool wasInProgress = std::exchange(nativeCallInProgress_, true);
        operation_->cancel();
        nativeCallInProgress_ = wasInProgress;
    }
}

void WindowsAppUpdateController::cancelInstall() noexcept {
    if (!installOperation_) return;
    installCancelRequested_ = true;
    if (!nativeCallInProgress_ && !installCancelSent_) {
        installCancelSent_ = true;
        nativeCallInProgress_ = true;
        installOperation_->cancel();
        nativeCallInProgress_ = false;
    }
}

void WindowsAppUpdateController::close() noexcept {
    if (installOperation_) {
        cancelInstall();
        return; // Cancel is not OS completion; keep blocking all new work.
    }
    if (result_.state == AppUpdateState::preparing) {
        ++installGeneration_;
        result_ = {AppUpdateState::cancelled};
    }
    cancel();
    if (operation_ || result_.state == AppUpdateState::checking) result_ = {};
}

std::wstring appUpdateDetail(AppUpdateResult result, bool operationPending) {
    if (result.state == AppUpdateState::idle && operationPending)
        return L"Завершаем предыдущую проверку… После этого можно будет проверить обновления снова.";
    switch (result.reason) {
    case AppUpdateReason::noPackage: return L"Проверка доступна в установленном пакете GRAF. Запустите установленное приложение и повторите проверку.";
    case AppUpdateReason::noAssociation: return L"Для этой установки не настроен источник обновлений. Узнать, есть ли новая версия, пока нельзя. Обратитесь к поставщику приложения.";
    case AppUpdateReason::invalidSource: return L"Источник обновлений не соответствует требованиям безопасности. Обратитесь к поставщику приложения.";
    case AppUpdateReason::unsupported: return L"Системная проверка обновлений недоступна. Обратитесь к поставщику приложения.";
    case AppUpdateReason::timeout: return L"Проверка или подготовка обновления не завершилась вовремя. Повторите попытку после завершения текущего запроса.";
    case AppUpdateReason::noApprovedRelease: return L"Канал установки обновлений ещё не утверждён. Проверка обновлений не разрешает установку.";
    case AppUpdateReason::captureActive: return L"Обновление не начато: сначала остановите запись и дождитесь её сохранения.";
    case AppUpdateReason::custodyUnhealthy: return L"Обновление не начато: сначала устраните ошибку локального хранилища.";
    case AppUpdateReason::notReady: return L"Условия установки изменились или приложение ещё не готово. Обновление не начато.";
    case AppUpdateReason::restartFailed: return L"Не удалось подготовить перезапуск приложения. Обновление не начато.";
    case AppUpdateReason::none: break;
    }
    switch (result.state) {
    case AppUpdateState::idle: return L"Проверьте, есть ли обновление GRAF.";
    case AppUpdateState::checking: return L"Проверяем обновления через Windows… Запись продолжает работать.";
    case AppUpdateState::current: return L"В зарегистрированном источнике нет обновлений для этой версии GRAF.";
    case AppUpdateState::available: return L"Доступно обновление GRAF. Установка требует утверждённого канала и отдельного подтверждения; запись не прерывается.";
    case AppUpdateState::required: return L"Источник сообщает об обязательном обновлении GRAF. Установка требует утверждённого канала и отдельного подтверждения; запись не прерывается.";
    case AppUpdateState::unknown: return L"Windows не смогла определить наличие обновлений. Повторите проверку позже.";
    case AppUpdateState::unavailable: return L"Проверка обновлений недоступна. Обратитесь к поставщику приложения.";
    case AppUpdateState::error: return L"Не удалось выполнить операцию обновления. Проверьте подключение к интернету и повторите попытку.";
    case AppUpdateState::preparing: return L"Готовимся к обновлению: завершаем операции с файлами. Новая запись временно недоступна. Подготовку можно отменить.";
    case AppUpdateState::installing: return L"Windows выполняет обновление или завершает его отмену. Новая запись недоступна до завершения операции. Перезапуск приложения не гарантирован.";
    case AppUpdateState::installed: return L"Windows завершила операцию обновления. Если приложение не перезапустилось, откройте его снова.";
    case AppUpdateState::cancelled: return L"Операция обновления отменена. Можно проверить обновления снова.";
    }
    return L"Повторите проверку обновлений.";
}

} // namespace graf::windows
