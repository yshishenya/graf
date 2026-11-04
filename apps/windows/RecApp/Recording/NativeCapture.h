#pragma once
#ifdef _WIN32
#include <windows.h>
#include <appmodel.h>
#include <combaseapi.h>
#include <mfapi.h>
#include <mferror.h>
#include <mftransform.h>
#include <winreg.h>
#include <winrt/Windows.ApplicationModel.h>
#include <winrt/Windows.System.Profile.h>
#include "../Audio/RecordingAudioTimeline.h"
#include "../Audio/WasapiEndpointEnumerator.h"
#include "../Capture/WindowsCaptureSessionController.h"
#include "../Contracts/JsonReader.h"
#include "../Diagnostics/MetadataSafeDiagnostics.h"
#include "../Shell/MicrophoneConsentKey.h"
#include "../Shell/RecordingNoticePresenter.h"
#include "../Shell/MeetingReminderModel.h"
#include "../Storage/AtomicFileStore.h"
#include "../Upload/DesktopUploadQueueService.h"
#include "../Upload/DesktopUploadRecoveryScheduler.h"
#include "../Upload/DesktopHttpTransport.h"
#include "../Storage/Sha256.h"
#include "../Web/WebView2Host.h"
#include "V5LocalRecordingWriter.h"
#include "ProtectedLocalRecordingPlayback.h"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cmath>
#include <cwchar>
#include <filesystem>
#include <future>
#include <iterator>
#include <limits>
#include <memory>
#include <mutex>
#include <optional>
#include <process.h>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <utility>
#include <vector>

namespace graf::windows {
namespace native_capture_detail {
// STA calls (notably Recycle Bin) can pump another UI tick. A synchronous
// custody mutation remains in flight until its entire owner-thread call ends.
class CustodyMutationScope final {
public:
    explicit CustodyMutationScope(std::size_t& count) noexcept : count_(count) { ++count_; }
    ~CustodyMutationScope() { --count_; }
    CustodyMutationScope(const CustodyMutationScope&) = delete;
    CustodyMutationScope& operator=(const CustodyMutationScope&) = delete;
private:
    std::size_t& count_;
};

inline bool readMicrophoneConsent(std::wstring_view suffix, bool& found) noexcept {
    constexpr wchar_t base[] = L"Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\microphone";
    std::wstring path(base);
    path.append(suffix);
    wchar_t value[32]{};
    DWORD bytes = sizeof(value);
    DWORD type = 0;
    const auto result = RegGetValueW(HKEY_CURRENT_USER, path.c_str(), L"Value",
                                     RRF_RT_REG_SZ, &type, value, &bytes);
    found = result == ERROR_SUCCESS;
    return found && _wcsicmp(value, L"Allow") == 0;
}

inline std::wstring currentPackageFamilyName() noexcept {
    UINT32 length = 0;
    if (GetCurrentPackageFamilyName(&length, nullptr) != ERROR_INSUFFICIENT_BUFFER || length == 0) return {};
    std::wstring name(length, L'\0');
    if (GetCurrentPackageFamilyName(&length, name.data()) != ERROR_SUCCESS) return {};
    name.resize(std::wcslen(name.c_str()));
    return name;
}

inline bool microphonePrivacyGranted() noexcept {
    bool found = false;
    for (const auto& suffix : graf::windows::microphoneConsentKeySuffixes(currentPackageFamilyName())) {
        const auto granted = readMicrophoneConsent(suffix, found);
        if (found) return granted;
    }
    return false;
}

inline std::string selectedMicrophonePreference() {
    wchar_t value[2048]{};
    DWORD bytes = sizeof(value);
    if (RegGetValueW(HKEY_CURRENT_USER, L"Software\\GRAF\\Windows\\Capture", L"Microphone",
                     RRF_RT_REG_SZ, nullptr, value, &bytes) != ERROR_SUCCESS) return {};
    return winrt::to_string(value);
}

inline bool saveMicrophonePreference(const std::string& identity) {
    HKEY key = nullptr;
    if (RegCreateKeyExW(HKEY_CURRENT_USER, L"Software\\GRAF\\Windows\\Capture", 0, nullptr, 0,
                        KEY_SET_VALUE, nullptr, &key, nullptr) != ERROR_SUCCESS) return false;
    const auto value = winrt::to_hstring(identity);
    const auto result = RegSetValueExW(key, L"Microphone", 0, REG_SZ,
        reinterpret_cast<const BYTE*>(value.c_str()), static_cast<DWORD>((value.size() + 1) * sizeof(wchar_t)));
    RegCloseKey(key);
    return result == ERROR_SUCCESS;
}

inline std::wstring deviceDisplayName(const std::string& name) {
    auto value = std::wstring(winrt::to_hstring(name).c_str());
    value.erase(std::remove_if(value.begin(), value.end(), [](wchar_t c) { return c < 32 || c == 127; }), value.end());
    if (value.size() > 96) value.resize(96);
    return value.empty() ? L"Устройство Windows" : value;
}

inline float rmsLevel(const std::vector<float>& samples) noexcept {
    if (samples.empty()) return 0.0F;
    long double sum = 0.0L;
    for (const auto sample : samples) {
        const auto bounded = std::max(-1.0F, std::min(1.0F, sample));
        sum += static_cast<long double>(bounded) * bounded;
    }
    return static_cast<float>(std::min(1.0L, std::sqrt(sum / samples.size())));
}

inline std::string newSessionId() {
    GUID guid{};
    if (SUCCEEDED(CoCreateGuid(&guid))) {
        wchar_t buffer[39]{};
        if (StringFromGUID2(guid, buffer, static_cast<int>(std::size(buffer))) == 39) {
            std::string result;
            result.reserve(36);
            for (const auto character : std::wstring_view(buffer + 1, 36)) {
                result.push_back(static_cast<char>(character >= L'A' && character <= L'F' ? character + (L'a' - L'A') : character));
            }
            return result;
        }
    }
    return "windows-" + std::to_string(GetCurrentProcessId()) + "-" +
        std::to_string(GetTickCount64());
}

inline bool mediaFoundationAacReady() noexcept {
    if (FAILED(MFStartup(MF_VERSION))) return false;
    MFT_REGISTER_TYPE_INFO outputType{MFMediaType_Audio, MFAudioFormat_AAC};
    IMFActivate** activations = nullptr;
    UINT32 activationCount = 0;
    const auto result = MFTEnumEx(
        MFT_CATEGORY_AUDIO_ENCODER,
        MFT_ENUM_FLAG_SYNCMFT | MFT_ENUM_FLAG_LOCALMFT | MFT_ENUM_FLAG_SORTANDFILTER,
        nullptr, &outputType, &activations, &activationCount);
    for (UINT32 index = 0; index < activationCount; ++index) {
        if (activations[index] != nullptr) activations[index]->Release();
    }
    CoTaskMemFree(activations);
    MFShutdown();
    return SUCCEEDED(result) && activationCount > 0;
}

} // namespace native_capture_detail

struct AecSelection {
    std::shared_ptr<IAec3Processor> processor;
    bool ready = false;
};

class NativeCapture final {
    friend struct NativeCaptureStorageTestPeer;
public:
    enum class QueueTicketState { pending, committed, notCommitted, ambiguous };
    enum class QueueMutationKind { recovery, recording, uploadPrepare, uploadResult, deletionIntent, deletionResult, deletionPurge, lifecycleResult, manualSend };
    struct QueueMutationTicket {
        std::uint64_t id = 0, baseGeneration = 0, targetGeneration = 0, epoch = 0;
        CustodyContext context{};
        QueueTicketState state = QueueTicketState::pending;
        CustodyFileError error = CustodyFileError::none;
        std::uint32_t nativeError = 0;
        bool changed = false;
        QueueMutationKind kind = QueueMutationKind::recovery;
    };
    struct DeletionCompletion {
        std::uint64_t id = 0, epoch = 0;
        bool saved = false, unknown = false;
        std::size_t accepted = 0, pending = 0, rejected = 0;
    };
private:
    struct DeletionFlight {
        enum class Phase { intent, network, result, answer, purge, purgeAnswer, retire,
            purgeList, purgeListed, purgeEnsured, purgeTask, purgeIntent, purgeRows, purgeCommitted, purgeAck, purgeAcked };
        struct PurgeTaskBatch {
            std::optional<BasicLocalPurgeTasks<CustodyString>> tasks;
            CustodyVector<CustodyString> awaiting;
        };
        Phase phase = Phase::intent;
        Phase afterNetwork = Phase::result;
        DeletionCompletion completion;
        QueueMutationTicket waiting;
        ProtectedDesktopHttpConfig config;
        std::shared_ptr<const ProtectedDeletionPlan> plan;
        std::shared_ptr<const ProtectedUploadQueueValue> snapshot;
        std::shared_ptr<const ProtectedDeletionResponse> response;
        std::size_t index = 0;
        std::size_t localIndex = 0;
        bool sharedFailure = false;
        bool serverPurge = false;
        std::shared_ptr<PurgeTaskBatch> purgeTasks;
        std::shared_ptr<PurgeTaskBatch> purgeSource;
        CustodyVector<CustodyString> awaiting;
        std::size_t ensureIndex = 0;
    };
    struct LifecycleBatch {
        CustodyVector<CustodyString> origins;
        std::optional<BasicLifecycleEntries<CustodyString>> entries;
        std::shared_ptr<const ProtectedDeletionResponse> response;
        bool background = false, allocationDeferred = false;
    };
    struct LifecycleFlight {
        ProtectedDesktopHttpConfig config;
        std::uint64_t epoch = 0;
        CustodyVector<CustodyString> origins;
        CustodyVector<unsigned char> checked;
        bool inventoryBuilt = false;
        bool protocolGateCurrent = false;
        bool checkedBackground = false;
        bool draining = false; // Fully validated restriction only; never a positive content grant.
        QueueMutationTicket waiting;
        std::shared_ptr<const LifecycleBatch> answer;
        std::shared_ptr<std::atomic<bool>> cancelled = std::allocate_shared<std::atomic<bool>>(
            CustodyAllocator<std::atomic<bool>>{}, false);
    };
    struct RecordingWork {
        std::mutex mutex;
        std::shared_ptr<IAec3Processor> processor;
        std::shared_ptr<RecordingAudioTimeline> timeline;
        // Native fields are cleared by the storage worker after EOS/finalizer
        // and queue adoption; a UI reference owns only terminal values then.
        std::shared_ptr<V5LocalRecordingWriter> writer;
        std::shared_ptr<const void> activeLease;
        std::shared_ptr<std::atomic<bool>> cancellation = std::allocate_shared<std::atomic<bool>>(
            CustodyAllocator<std::atomic<bool>>{}, false);
        CustodyString session, user, workspace;
        std::shared_ptr<const ProtectedUploadQueueValue> reservation;
        CustodyContext context{};
        std::atomic<std::uint64_t> frames{0};
        std::uint64_t epoch = 0, processedFrames = 0;
        bool ownerKnown = false, prepared = false, started = false, finalizing = false, terminal = false;
        CaptureFinalization result;
        ReasonCode failure = ReasonCode::none;
        RecordingStopReason stopReason = RecordingStopReason::interruption;
    };
    enum class StorageCommand { recovery, recoverRecording, prepareRecording, finalizeRecording, prepareUpload, uploadResult, deletionIntent, deletionResult, deletionPurge, lifecycleResult };
    struct DeletionWork {
        std::shared_ptr<const ProtectedUploadQueueValue> snapshot;
        std::size_t index = 0;
        std::optional<std::size_t> localIndex;
        bool resumeLocalIntent = false;
        CustodyString origin;
        CustodyString user, workspace;
        ProtectedDeletionTargets targets;
        std::shared_ptr<ProtectedDeletionPlan> plan;
        std::optional<BasicLocalPurgeTask<CustodyString>> serverTask;
        BasicDeletionWireResult<CustodyString> answer;
        std::shared_ptr<const LifecycleBatch> lifecycle;
        std::shared_ptr<const ProtectedUploadQueueValue::AuthenticatedContext> authenticatedContext;
        std::shared_ptr<std::atomic<bool>> cancelled = std::allocate_shared<std::atomic<bool>>(
            CustodyAllocator<std::atomic<bool>>{}, false);
    };
    struct DisplayWork {
        std::shared_ptr<const ProtectedUploadQueueValue> snapshot;
        std::shared_ptr<const ProtectedLocalRecordingTimings> result;
        CustodyString user, workspace;
        std::uint64_t epoch = 0;
        std::shared_ptr<std::atomic<bool>> cancelled = std::allocate_shared<std::atomic<bool>>(
            CustodyAllocator<std::atomic<bool>>{}, false);
        std::atomic<bool> done{false};
        std::chrono::steady_clock::time_point retryAt = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        bool started = false; // Storage value mutex, like result.
    };
    // Never stored in UI-owned state. Storage/network workers share only the
    // current package pair; the rest of the batch retains domain values.
    struct ProtectedNetworkWork {
        enum class Phase { idle, requestProof, proofReady, resultReady, resultAdopted };
        std::shared_ptr<DesktopUploadRecoveryScheduler::ProtectedFlight> flight;
        std::shared_ptr<DisplayWork> display; // Explicit read-only mode, never an upload flight.
        std::shared_ptr<const ProtectedUploadQueueValue> recoverySnapshot; // Local-only restart mode, never HTTP.
        std::optional<QueueMutationTicket> claimTicket; // Explicit manual claim preflight reuses this read-only exchange.
        std::shared_ptr<std::atomic<bool>> recoveryCancellation;
        std::shared_ptr<const LocalRecordingPackage::ProtectedInspection> recoveryProof;
        std::shared_ptr<V5LocalRecordingWriter> recoveryWriter; // Worker -> recovery executor only, never UI.
        bool recoveryDone = false;
        std::optional<ProtectedLocalRecordingTiming> timing;
        CustodyContext packageContext{};
        std::uint64_t packageGeneration = 0;
        std::size_t index = 0;
        Phase phase = Phase::idle; // Guarded by StorageStartupWork::mutex.
        bool proceed = false;
        std::shared_ptr<const ProtectedCustodyPackagePair> pair;
        std::shared_ptr<const ProtectedDesktopTransportResult> result;
    };
    struct PlaybackWork {
        std::shared_ptr<const ProtectedUploadQueueValue> snapshot;
        std::size_t index = 0;
        std::uint64_t epoch = 0, documentGeneration = 0, serial = 0;
        std::shared_ptr<std::atomic<bool>> cancelled = std::allocate_shared<std::atomic<bool>>(
            CustodyAllocator<std::atomic<bool>>{}, false);
        ProtectedLocalRecordingPlayback::Snapshot media;
        std::optional<double> seek;
        bool muted = false, authorized = false, paused = true, preparing = true;
        bool started = false, executorDone = false, terminal = false;
    };
    // Worker-only exchange. UI state never retains a pair, inspection or engine.
    struct PlaybackExchange {
        enum class Phase { requestProof, proofReady, idle, requestValidation, validationReady };
        std::shared_ptr<PlaybackWork> operation;
        std::shared_ptr<const ProtectedCustodyPackagePair> pair;
        Phase phase = Phase::requestProof;
        bool proceed = false;
    };
    struct StorageStartupWork {
        explicit StorageStartupWork(const std::filesystem::path& value) : root(value) {}
        const std::filesystem::path root;
        std::mutex mutex;
        std::condition_variable wake;
        std::shared_ptr<std::atomic<bool>> cancellation = std::allocate_shared<std::atomic<bool>>(
            CustodyAllocator<std::atomic<bool>>{}, false);
        CustodyContext context{};
        std::uint64_t generation = 0;
        CustodyFileError error = CustodyFileError::none;
        std::uint32_t nativeError = 0;
        bool ready = false, adopted = false, stop = false, terminal = false;
        // One bounded command/completion and one scalar coalesced intent in UI.
        // Values contain no native leases; the commit stays local to the worker.
        std::shared_ptr<const ProtectedUploadQueueValue> startupValue, resultValue;
        QueueMutationTicket ticket;
        std::optional<QueueMutationTicket> retiredManualSend; // Effect-free cancellation cannot replace a recording's command/ACK.
        StorageCommand command = StorageCommand::recovery;
        std::shared_ptr<RecordingWork> recording;
        std::shared_ptr<DeletionWork> deletion;
        std::shared_ptr<DesktopUploadRecoveryScheduler::ProtectedFlight> upload;
        std::shared_ptr<DisplayWork> display;
        std::shared_ptr<PlaybackWork> playback;
        DesktopHttpTransport::ProtectedUploadSend uploadWire;
        std::uint64_t nextTicket = 0;
        std::uint32_t retryAfterSeconds = 0;
        std::optional<std::int64_t> authExpiresAt;
        bool commandReady = false, inFlight = false, resultReady = false, resultAdopted = false, queueFailed = false;
        bool reconciliationPending = false, reconcileRequested = false, physicalReadback = false;
        bool commandReconciliation = false;
        bool shortDiscardPending = false;
        std::shared_ptr<std::atomic<bool>> recoveryCancellation; // Value-only cancellation/shared-slot admission, never a native proof.
        std::uint64_t readbackGeneration = 0;
    };
    using StorageWorkReference = std::shared_ptr<StorageStartupWork>;
    // Accepted value state only. Native reservation/readback/factory ACKs still
    // grant the first audio block; this predicate never grants file authority.
    [[nodiscard]] bool protectedQueueComplete(const StorageStartupWork& work) const noexcept {
        return work.ready && work.adopted && work.startupValue && protectedQueueValue_ &&
            work.generation != 0 && work.context.role == CustodyRole::queue &&
            work.context.storeId != CustodyId{} && work.context.objectId != CustodyId{} &&
            work.error == CustodyFileError::none && !work.queueFailed &&
            !work.reconciliationPending && !work.commandReconciliation && !work.shortDiscardPending &&
            !work.commandReady && !work.inFlight && (!work.resultReady || work.resultAdopted);
    }
public:
    struct AudioLevels {
        float microphone = 0.0F;
        float systemRender = 0.0F;
    };

    NativeCapture(std::filesystem::path root, AecSelection aec, DesktopHttpTransport::UploadSend wire = {},
        DesktopHttpTransport::ProtectedUploadSend protectedWire = {})
        : aecSelection_(std::move(aec)),
          custodyRoot_(std::move(root)),
          queue_(custodyRoot_ / std::string(graf::windows::kQueueLedgerFileName), custodyRoot_),
          scheduler_(queue_), wire_(std::move(wire)), protectedWire_(std::move(protectedWire)) {
        createRecordingPipeline();
        readiness_.aecReady = aecSelection_.ready;
        // Readiness derives from adopted protected state, never from a path or
        // a constructor flag. Device probes remain explicit below.
        readiness_.webViewRuntimeReady = false;
        // Native metadata probes are explicit, not constructor effects.
    }

    ~NativeCapture() {
        // Normal close drains answers through polling before destruction. Forced
        // teardown only reaps the owned network thread: durable intents remain
        // pending for recovery, never an accepted/purged claim. No second UI loop.
        requestShutdown();
        if (deletionThread_.joinable()) deletionThread_.join();
        deletionFuture_ = {};
        deletionFlight_.reset();
        if (lifecycleThread_.joinable()) lifecycleThread_.join();
        lifecycleFuture_ = {}; lifecycleFlight_.reset();
        shutdown();
        // The controller joins acquisition/dispatcher before the lost-poll
        // finalizer handoff. No native writer is destroyed on this UI thread.
        const auto failure = controller_->drainAbandonedCapture();
        controller_.reset();
        requestProtectedFinalization(failure, RecordingStopReason::interruption);
        stopStorageStartup();
    }

    // Explicit shell startup, not constructor/readiness IO. Until every protected
    // consumer is connected this only establishes the private worker ownership.
    void startStorageValidation() {
        if (storageStartup_ || shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_) return;
        try {
            // Copy the path before dispatch: MSVC Debug path move can allocate
            // inside noexcept. The native thread receives only a shared value.
            auto work = std::allocate_shared<StorageStartupWork>(CustodyAllocator<StorageStartupWork>{}, custodyRoot_);
            work->uploadWire = protectedWire_;
            CustodyAllocator<StorageWorkReference> allocator;
            auto* argument = allocator.allocate(1);
            std::allocator_traits<decltype(allocator)>::construct(allocator, argument, work);
            const auto handle = _beginthreadex(nullptr, 0, &NativeCapture::runStorageStartup, argument, 0, nullptr);
            if (!handle) {
                std::allocator_traits<decltype(allocator)>::destroy(allocator, argument);
                allocator.deallocate(argument, 1);
                return;
            }
            storageThread_.attach(reinterpret_cast<HANDLE>(handle));
            storageStartup_ = std::move(work);
        } catch (...) {
            // Failed dispatch grants no admission; no synchronous disk fallback.
        }
    }

    using StartGuardFactory = std::function<graf::windows::WindowsCaptureSessionController::StartGuard(const std::string&)>;
    [[nodiscard]] graf::windows::TransitionResult record(StartGuardFactory makeStartGuard = {}) {
        if (!readiness().storageWritable) return {graf::windows::TransitionStatus::rejected,
            indicator().state, graf::windows::ReasonCode::storageUnavailable};
        if (shuttingDown_ || exitAdmissionBlocked_) return {graf::windows::TransitionStatus::rejected, indicator().state};
        if (updateAdmissionBlocked_) return {graf::windows::TransitionStatus::rejected, indicator().state};
        if (indicator().visible || protectedRecordingPending())
            return {TransitionStatus::rejected, indicator().state, ReasonCode::activeSessionExists};
        const native_capture_detail::CustodyMutationScope mutation(synchronousMutations_);
        if (!indicator().visible && indicator().state != graf::windows::SessionState::idle) createRecordingPipeline();
        refreshReadiness();
        // Readiness can enter COM. An update accepted by a nested UI event must
        // prevent the old Record action from starting workers afterwards.
        if (updateAdmissionBlocked_) return {graf::windows::TransitionStatus::rejected, indicator().state};
        recordingAccount_ = currentAccount_;
        recordingOrigin_ = graf::windows::DesktopHttpConfig{}.baseOrigin;
        recordingEndpointIdentity_ = currentEndpointIdentity_;
        graf::windows::WindowsCaptureSessionController::StartGuard guard;
        if (makeStartGuard) {
            // Bind after any pipeline replacement, before either worker starts.
            // A failed automatic binding must never fall back to manual capture.
            try { guard = makeStartGuard(sessionId_); } catch (...) {}
            if (!guard) guard = [](std::string_view) { return false; };
        }
        return beginProtectedRecording(readiness_, std::move(guard));
    }
    [[nodiscard]] const std::string& sessionId() const noexcept { return sessionId_; }
    void refreshPermission() noexcept { readiness_.microphonePermissionGranted = native_capture_detail::microphonePrivacyGranted(); }
    // The server renewed the session while answering a flight and named the new
    // deadline. It travels to the shell, which carries it to the cabinet's own
    // session cookie, exactly as macOS rewrites that cookie.
    void setSessionExpiryHandler(std::function<void(std::int64_t)> handler) {
        sessionExpiryHandler_ = std::move(handler);
        scheduler_.setSessionExpiryHandler([this](std::int64_t seconds) {
            if (sessionExpiryHandler_) sessionExpiryHandler_(seconds);
        });
    }
    void setAuthSessionToken(std::string token, bool currentCookieRead = false) {
        const bool signedOutObserved = token.empty() && currentCookieRead;
        const bool changed = authSessionToken_ != token || authSignedOutObserved_ != signedOutObserved;
        if (changed) {
            if (nativeCookieObserved_) localRestorationAllowed_ = false;
            invalidateAuthentication();
            authSessionToken_ = std::move(token);
            authSignedOutObserved_ = signedOutObserved;
            if (authSessionToken_.empty()) protectedRecoveryEpoch_.reset();
            else recover(graf::windows::RecoveryTrigger::authRecovered);
        }
        if (currentCookieRead) nativeCookieObserved_ = true;
        if (currentCookieRead && !authSessionToken_.empty()) requestAccountRevalidation();
    }
    // Native shell service activation is independent of a WebView/document.
    // It shares the existing recovery cadence; no constructor IO or new timer.
    void startRecordingLifecycle() noexcept {
        if (!lifecycleEnabled_) { lifecycleEnabled_ = true; lifecycleRequested_ = true; }
    }
    void setVisibleRecordingItemIDs(const std::vector<std::string>& ids, std::uint64_t epoch) noexcept try {
        if (epoch != authGeneration_ || !currentAccount_ || ids.size() > 100) return;
        CustodyVector<CustodyString> replacement;
        replacement.reserve(ids.size());
        for (const auto& id : ids) {
            if (!DesktopUploadQueueService::validIdentity(id) ||
                std::find(replacement.begin(), replacement.end(), std::string_view(id)) != replacement.end()) return;
            replacement.emplace_back(id.data(), id.size());
        }
        lifecycleVisible_.swap(replacement); // Hint only; native rows determine all targets.
        // Repeated hints change only priority. Existing startup/recovery/open
        // intents drive the finite cycle; document publication cannot make a loop.
    } catch (...) {} // Failed hint allocation leaves previous priority unchanged.
private:
    void invalidateAuthentication() {
        if (deletionContinuationCancellation_) deletionContinuationCancellation_->store(true);
        cancelRecordingLifecycle(true);
        closeLocalPlayback();
        if (storageStartup_) {
            std::lock_guard<std::mutex> lock(storageStartup_->mutex);
            if (storageStartup_->display) storageStartup_->display->cancelled->store(true);
            if (storageStartup_->deletion) storageStartup_->deletion->cancelled->store(true);
            if (storageStartup_->upload) storageStartup_->upload->cancelled->store(true);
            cancelUnstartedRecording(*storageStartup_);
            storageStartup_->wake.notify_all();
        }
        scheduler_.cancel();
        if (accountCancellation_) accountCancellation_->store(true);
        ++authGeneration_;
        currentAccount_.reset(); provenAccount_.reset();
        pendingAuthenticatedContext_.reset(); authenticatedContextTicket_.reset();
        lifecycleGateFresh_ = false;
        accountRetryAt_ = 0; localPurgeRetryAt_ = 0;
    }
    void requestAccountRevalidation() noexcept {
        accountRevalidationRequested_ = true;
        lifecycleGateFresh_ = false;
        pendingAuthenticatedContext_.reset(); authenticatedContextTicket_.reset();
        if (!accountFuture_.valid()) accountRetryAt_ = 0;
        // The retained local tuple is not a grant to continue scoped HTTP.
        currentAccount_.reset(); scheduler_.cancel(); cancelRecordingLifecycle();
        if (deletionContinuationCancellation_) deletionContinuationCancellation_->store(true);
        if (storageStartup_) {
            std::lock_guard<std::mutex> lock(storageStartup_->mutex);
            if (storageStartup_->upload) storageStartup_->upload->cancelled->store(true);
            if (storageStartup_->deletion) storageStartup_->deletion->cancelled->store(true);
            storageStartup_->wake.notify_all();
        }
    }
    static std::string nativeSessionFingerprint(const DesktopHttpConfig& config) {
        // Exact UTF-8 JSON bytes shared with the Mac binding: no whitespace,
        // normalization, short control escapes, BOM or trailing newline.
        std::string bytes = "{\"headers\":{\"x-auth-session\":";
        const auto quote = [&](std::string_view text) {
            bytes += '"';
            constexpr char hex[] = "0123456789abcdef";
            for (const unsigned char c : text) {
                if (c == '"' || c == '\\') { bytes += '\\'; bytes += static_cast<char>(c); }
                else if (c < 32) {
                    bytes += "\\u00"; bytes += hex[c >> 4]; bytes += hex[c & 15];
                } else bytes += static_cast<char>(c);
            }
            bytes += '"';
        };
        quote(config.sessionToken); bytes += "},\"origin\":"; quote(config.baseOrigin); bytes += '}';
        return sha256(bytes);
    }
    static bool sameAuthenticatedContext(const ProtectedUploadQueueValue::AuthenticatedContext& a,
        const ProtectedUploadQueueValue::AuthenticatedContext& b) noexcept {
        return a.serverOrigin == b.serverOrigin && a.actorUserId == b.actorUserId &&
            a.workspaceId == b.workspaceId && a.sessionFingerprint == b.sessionFingerprint;
    }
    LocalProblemContext localContentContext() const {
        if (!lifecycleEnabled_) return currentAccount_ ? LocalProblemContext{DesktopHttpConfig{}.baseOrigin,
            currentAccount_->userId, currentAccount_->workspaceId} : LocalProblemContext{};
        if (!nativeCookieObserved_ || authSessionToken_.empty() || authSignedOutObserved_ || !localRestorationAllowed_ ||
            !protectedQueueValue_ || !protectedQueueValue_->lastAuthenticatedContext()) return {};
        const auto& context = *protectedQueueValue_->lastAuthenticatedContext();
        DesktopHttpConfig config; config.sessionToken = authSessionToken_;
        if (std::string_view(context.serverOrigin) != config.baseOrigin ||
            std::string_view(context.sessionFingerprint) != nativeSessionFingerprint(config) ||
            (currentAccount_ && (std::string_view(context.actorUserId) != currentAccount_->userId ||
                std::string_view(context.workspaceId) != currentAccount_->workspaceId))) return {};
        return {std::string(context.serverOrigin.begin(), context.serverOrigin.end()),
            std::string(context.actorUserId.begin(), context.actorUserId.end()),
            std::string(context.workspaceId.begin(), context.workspaceId.end())};
    }
    // One context command uses the existing lifecycle ticket, worker commit and
    // independent readback/adoption. No origin inventory or synthetic entry.
    bool pollAuthenticatedContext() {
        if (!pendingAuthenticatedContext_) return false;
        if (shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_) {
            pendingAuthenticatedContext_.reset(); authenticatedContextTicket_.reset(); return false;
        }
        if (!currentAccount_ || !storageStartup_) return true;
        if (authenticatedContextTicket_) {
            if (!lastLifecycleTicket_ || lastLifecycleTicket_->id != *authenticatedContextTicket_ ||
                lastLifecycleTicket_->state == QueueTicketState::pending) return true;
            if (lastLifecycleTicket_->epoch == authGeneration_ && lastLifecycleTicket_->state == QueueTicketState::committed &&
                protectedQueueValue_ && protectedQueueValue_->lastAuthenticatedContext() &&
                sameAuthenticatedContext(*protectedQueueValue_->lastAuthenticatedContext(), *pendingAuthenticatedContext_))
                localRestorationAllowed_ = true;
            authenticatedContextTicket_.reset(); pendingAuthenticatedContext_.reset();
            return false;
        }
        if (lifecycleFlight_) return true;
        const auto observation = localObservation();
        if (!observation.complete || !observation.value) return true;
        if (observation.value->lastAuthenticatedContext() &&
            sameAuthenticatedContext(*observation.value->lastAuthenticatedContext(), *pendingAuthenticatedContext_)) {
            localRestorationAllowed_ = true; pendingAuthenticatedContext_.reset(); return false;
        }
        auto command = std::allocate_shared<DeletionWork>(CustodyAllocator<DeletionWork>{});
        command->snapshot = observation.value; command->authenticatedContext = pendingAuthenticatedContext_;
        command->user = pendingAuthenticatedContext_->actorUserId; command->workspace = pendingAuthenticatedContext_->workspaceId;
        command->origin = pendingAuthenticatedContext_->serverOrigin;
        if (const auto ticket = submitProtectedDeletion(std::move(command), QueueMutationKind::lifecycleResult))
            authenticatedContextTicket_ = ticket->id;
        return true;
    }
    void cancelRecordingLifecycle(bool scopeChanged = false) noexcept {
        if (lifecycleFlight_) lifecycleFlight_->cancelled->store(true);
        if (scopeChanged) {
            lifecycleVisible_.clear(); lifecycleOpen_.clear(); lifecycleCursor_.clear(); lifecycleRestrictions_.clear();
            lifecycleUser_.clear(); lifecycleWorkspace_.clear(); lifecycleOrigin_.clear(); lifecycleEpoch_ = 0;
            lifecycleRetryAt_ = 0;
        }
    }
    bool lifecycleContextCurrent(const LifecycleFlight& flight) const noexcept {
        return currentAccount_ && flight.epoch == authGeneration_ && flight.config.confirmedIdentity &&
            std::string_view(flight.config.sessionToken) == authSessionToken_ &&
            std::string_view(flight.config.confirmedIdentity->userId) == currentAccount_->userId &&
            std::string_view(flight.config.workspaceId) == currentAccount_->workspaceId &&
            flight.config.baseOrigin == lifecycleOrigin_;
    }
    bool restrictiveLifecyclePending() const noexcept {
        // Transient revalidation/cancel does not erase a previously verified
        // denial. A real session/scope change increments the existing epoch.
        return !lifecycleRestrictions_.empty() && lifecycleEpoch_ == authGeneration_;
    }
    void retireRecordingLifecycle() {
        lifecycleFlight_.reset();
        if (deletionShutdownPending_ && !deletionFlight_) shutdown();
    }
    static bool lifecycleReceiptKnown(const ProtectedUploadQueueValue& value, const ProtectedUploadQueueValue::Item& row,
        std::string_view user, std::string_view workspace, std::string_view origin) {
        return std::any_of(value.deletionOperations().begin(), value.deletionOperations().end(), [&](const auto& operation) {
            return deletionPhaseIsAccepted(operation.phase) && std::string_view(operation.actorUserId) == user &&
                std::string_view(operation.workspaceId) == workspace && std::string_view(operation.serverOrigin) == origin &&
                (operation.target == DeletionTarget::ownOrigin ? operation.targetId == row.directoryId :
                    (!row.meetingId.empty() && operation.targetId == row.meetingId));
        });
    }
    void pollRecordingLifecycle() try {
        if (lifecyclePolling_) return;
        const native_capture_detail::CustodyMutationScope polling(lifecyclePolling_);
        if (lifecycleThread_.joinable()) {
            // Future readiness precedes thread-local teardown. Reap actual exit
            // before consuming a result, allowing a second flight or draining.
            if (WaitForSingleObject(lifecycleThread_.native_handle(), 0) != WAIT_OBJECT_0) return;
            lifecycleThread_.join();
            auto answer = lifecycleFuture_.get(); lifecycleFuture_ = {};
            if (lifecycleFlight_) lifecycleFlight_->answer = std::move(answer);
        }
        if (lifecycleFlight_) {
            auto& flight = *lifecycleFlight_;
            if (!lifecycleContextCurrent(flight) || shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ ||
                flight.cancelled->load()) {
                flight.cancelled->store(true); retireRecordingLifecycle(); return;
            }
            if (flight.waiting.id) {
                if (!lastLifecycleTicket_ || lastLifecycleTicket_->id != flight.waiting.id ||
                    lastLifecycleTicket_->state == QueueTicketState::pending) return;
                if (lastLifecycleTicket_->state != QueueTicketState::committed) {
                    retireRecordingLifecycle(); return; // Worker retains ambiguous publication/reconciliation.
                }
                // Only a result already adopted by pollStorageStartup advances
                // checked/cursor. Construct first so a quota refusal cannot skip history.
                CustodyString cursor = lifecycleCursor_;
                if (flight.answer->background) cursor = flight.answer->origins.back();
                for (const auto& origin : flight.answer->origins) {
                    const auto at = std::lower_bound(flight.origins.begin(), flight.origins.end(), origin);
                    if (at == flight.origins.end() || *at != origin) throw std::logic_error("lifecycle_inventory");
                    flight.checked[static_cast<std::size_t>(at - flight.origins.begin())] = 1;
                }
                lifecycleCursor_.swap(cursor);
                if (flight.answer->background) flight.checkedBackground = true;
                const auto expiry = flight.answer->response->authExpiresAt;
                lifecycleRestrictions_.erase(std::remove_if(lifecycleRestrictions_.begin(), lifecycleRestrictions_.end(),
                    [&](const auto& origin) {
                        if (std::find(flight.answer->origins.begin(), flight.answer->origins.end(), origin) != flight.answer->origins.end())
                            return true; // Fresh target answer was committed/read back/adopted.
                        return std::none_of(protectedQueueValue_->items().begin(), protectedQueueValue_->items().end(), [&](const auto& row) {
                            return row.directoryId == origin && protectedLocalContentAllowed(*protectedQueueValue_, row,
                                flight.config.confirmedIdentity->userId, flight.config.workspaceId);
                        }); // A persisted denial or removed row already closes its common content gate.
                    }), lifecycleRestrictions_.end());
                flight.answer.reset(); flight.waiting = {}; flight.draining = false;
                if (expiry && sessionExpiryHandler_) { sessionExpiryHandler_(*expiry); return; }
            }
            if (flight.answer) {
                if (flight.answer->origins.empty()) { retireRecordingLifecycle(); return; }
                if (!flight.answer->entries && !flight.answer->allocationDeferred) {
                    if (flight.answer->response && flight.answer->response->status == 429)
                        lifecycleRetryAt_ = GetTickCount64() + static_cast<std::uint64_t>(flight.answer->response->retryAfterSeconds) * 1000;
                    const bool scopeChanged = flight.answer->response && flight.answer->response->safeReason == "scope_changed";
                    retireRecordingLifecycle();
                    if (scopeChanged) requestAccountRevalidation();
                    return;
                }
                if (flight.answer->entries) {
                    if (!storageStartup_) return;
                    if (flight.draining) {
                        // Cancellation is not executor completion or native release.
                        if (scheduler_.busy()) return;
                        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
                        if (storageStartup_->upload) return;
                    }
                    const auto observation = localObservation();
                    if (!observation.complete || !observation.value) return;
                    const auto& user = flight.config.confirmedIdentity->userId;
                    const auto& workspace = flight.config.workspaceId;
                    auto copy = std::allocate_shared<ProtectedUploadQueueValue>(
                        CustodyAllocator<ProtectedUploadQueueValue>{}, *observation.value);
                    const auto now = static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
                        std::chrono::system_clock::now().time_since_epoch()).count());
                    bool changed = false;
                    if (!copy->applyLifecycleEntries(flight.answer->origins, *flight.answer->entries,
                        user, workspace, flight.config.baseOrigin, now, changed, flight.cancelled.get())) {
                        retireRecordingLifecycle(); return; // No effects from even a late invalid private prefix.
                    }
                    auto restrictions = lifecycleRestrictions_; // Allocate the full closure before any cancellation.
                    bool restrictive = false;
                    for (std::size_t n = 0; n != copy->items().size(); ++n) {
                        if (protectedLocalContentAllowed(*observation.value, observation.value->items()[n], user, workspace) &&
                            !protectedLocalContentAllowed(*copy, copy->items()[n], user, workspace)) {
                            restrictive = true;
                            const auto& origin = copy->items()[n].directoryId;
                            if (std::find(restrictions.begin(), restrictions.end(), origin) == restrictions.end()) restrictions.push_back(origin);
                        }
                    }
                    lifecycleRestrictions_.swap(restrictions);
                    flight.draining = flight.draining || restrictive;
                    if (flight.draining) {
                        closeLocalPlayback(); scheduler_.cancel(); // Entire scope/target answer already checked.
                        if (scheduler_.busy()) return;
                    }
                    // Revalidate again after actual drain against this latest adopted
                    // snapshot. Only the worker can commit/read back/adopt the answer.
                    auto command = std::allocate_shared<DeletionWork>(CustodyAllocator<DeletionWork>{});
                    command->snapshot = observation.value; command->lifecycle = flight.answer;
                    command->user = flight.config.confirmedIdentity->userId; command->workspace = flight.config.workspaceId;
                    command->origin = flight.config.baseOrigin; command->cancelled = flight.cancelled;
                    const auto ticket = submitProtectedDeletion(std::move(command), QueueMutationKind::lifecycleResult);
                    if (ticket) flight.waiting = *ticket;
                    return;
                }
            }
        }
        if (pendingAuthenticatedContext_ && pollAuthenticatedContext()) return;
        if (shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ || !lifecycleEnabled_ ||
            !currentAccount_ || authSessionToken_.empty() || !storageStartup_ || GetTickCount64() < lifecycleRetryAt_) return;
        const auto observation = localObservation();
        if (!observation.complete || !observation.value) return;
        if (!lifecycleFlight_) {
            if (!lifecycleRequested_) return;
            auto flight = std::allocate_shared<LifecycleFlight>(CustodyAllocator<LifecycleFlight>{});
            flight->epoch = authGeneration_;
            flight->protocolGateCurrent = lifecycleGateFresh_; lifecycleGateFresh_ = false;
            auto& config = flight->config;
            config.sessionToken = std::string_view(authSessionToken_); config.workspaceId = std::string_view(currentAccount_->workspaceId);
            config.confirmedIdentity.emplace(); config.confirmedIdentity->userId = std::string_view(currentAccount_->userId);
            config.confirmedIdentity->workspaceId = config.workspaceId;
            config.scopedAccount = BasicDeletionScope<CustodyString>{config.confirmedIdentity->userId, config.workspaceId};
            config.cancellation = flight->cancelled;
            if (lifecycleEpoch_ && (lifecycleEpoch_ != authGeneration_ ||
                std::string_view(lifecycleUser_) != currentAccount_->userId ||
                std::string_view(lifecycleWorkspace_) != currentAccount_->workspaceId)) {
                lifecycleVisible_.clear(); lifecycleOpen_.clear(); lifecycleCursor_.clear();
            }
            lifecycleUser_ = config.confirmedIdentity->userId; lifecycleWorkspace_ = config.workspaceId; lifecycleOrigin_ = config.baseOrigin; lifecycleEpoch_ = authGeneration_;
            lifecycleRequested_ = false; lifecycleFlight_ = std::move(flight);
        }
        auto& flight = *lifecycleFlight_;
        const bool retryDecode = flight.answer && flight.answer->allocationDeferred;
        auto batch = retryDecode ? std::allocate_shared<LifecycleBatch>(CustodyAllocator<LifecycleBatch>{}, *flight.answer) :
            std::allocate_shared<LifecycleBatch>(CustodyAllocator<LifecycleBatch>{});
        const auto config = flight.config;
        const auto send = protectedWire_;
        const auto cycle = lifecycleFlight_;
        const auto snapshot = observation.value;
        const auto visible = lifecycleVisible_;
        const auto opened = lifecycleOpen_;
        const auto cursor = lifecycleCursor_;
        std::packaged_task<std::shared_ptr<const LifecycleBatch>()> task([batch, config, send, cycle, snapshot, visible, opened, cursor, retryDecode] {
            try {
                batch->allocationDeferred = false;
                if (!retryDecode) {
                    const auto cancellation = config.cancellation.get();
                    auto& flight = *cycle; // Exclusive until actual thread exit; UI only cancels.
                    if (!flight.inventoryBuilt) {
                        for (const auto& row : snapshot->items()) {
                            json_detail::checkCancellation(cancellation);
                            if (row.ownerUserId != config.confirmedIdentity->userId || row.ownerWorkspaceId != config.workspaceId ||
                                lifecycleReceiptKnown(*snapshot, row, config.confirmedIdentity->userId, config.workspaceId, config.baseOrigin)) continue;
                            if (!DesktopUploadQueueService::validIdentity(row.directoryId)) return std::shared_ptr<const LifecycleBatch>(batch);
                            flight.origins.push_back(row.directoryId);
                        }
                        std::sort(flight.origins.begin(), flight.origins.end());
                        flight.origins.erase(std::unique(flight.origins.begin(), flight.origins.end()), flight.origins.end());
                        flight.checked.resize(flight.origins.size(), 0); flight.inventoryBuilt = true;
                    }
                    const auto unchecked = [&](const auto& origin) {
                        const auto at = std::lower_bound(flight.origins.begin(), flight.origins.end(), origin);
                        return at != flight.origins.end() && *at == origin && !flight.checked[static_cast<std::size_t>(at - flight.origins.begin())];
                    };
                    CustodyVector<CustodyString> priority;
                    for (const auto& row : snapshot->items()) {
                        json_detail::checkCancellation(cancellation);
                        if (row.ownerUserId != config.confirmedIdentity->userId || row.ownerWorkspaceId != config.workspaceId || !unchecked(row.directoryId)) continue;
                        bool first = row.localRecordingId == opened || std::find(visible.begin(), visible.end(), row.localRecordingId) != visible.end();
                        if (!first) for (const auto& op : snapshot->deletionOperations()) {
                            json_detail::checkCancellation(cancellation);
                            if (op.actorUserId == row.ownerUserId && op.workspaceId == row.ownerWorkspaceId && op.serverOrigin == config.baseOrigin &&
                                (op.target == DeletionTarget::ownOrigin ? op.targetId == row.directoryId : (!row.meetingId.empty() && op.targetId == row.meetingId))) {
                                first = true; break;
                            }
                        }
                        if (first) priority.push_back(row.directoryId);
                    }
                    std::sort(priority.begin(), priority.end()); priority.erase(std::unique(priority.begin(), priority.end()), priority.end());
                    for (const auto& origin : priority) {
                        json_detail::checkCancellation(cancellation); batch->origins.push_back(origin);
                        if (batch->origins.size() == 100) break;
                    }
                    if (batch->origins.empty() && !flight.checkedBackground) {
                        batch->background = true;
                        for (const auto& origin : flight.origins) {
                            json_detail::checkCancellation(cancellation);
                            if (unchecked(origin) && origin > cursor) batch->origins.push_back(origin);
                            if (batch->origins.size() == 100) break;
                        }
                        if (batch->origins.empty()) for (const auto& origin : flight.origins) {
                            json_detail::checkCancellation(cancellation);
                            if (unchecked(origin)) batch->origins.push_back(origin);
                            if (batch->origins.size() == 100) break;
                        }
                    }
                    if (batch->origins.empty()) return std::shared_ptr<const LifecycleBatch>(batch);
                    // The immediately preceding fresh identity lookup already
                    // read this gate for this exact immutable scope/session.
                    const bool readGate = !flight.protocolGateCurrent; flight.protocolGateCurrent = false;
                    batch->response = DesktopHttpTransport::recordingLifecycleProtected(config, batch->origins, readGate, send);
                }
                if (!batch->response || !batch->response->accepted()) return std::shared_ptr<const LifecycleBatch>(batch);
                batch->entries = DesktopApiClient::decodeLifecycleEntries<CustodyString>(batch->response->body, config.cancellation.get());
                if (!batch->entries || batch->entries->size() != batch->origins.size() ||
                    std::any_of(batch->entries->begin(), batch->entries->end(), [&](const auto& entry) {
                        return entry.target != DeletionTarget::ownOrigin ||
                            std::find(batch->origins.begin(), batch->origins.end(), entry.targetId) == batch->origins.end();
                    })) batch->entries.reset();
            } catch (const std::bad_alloc&) {
                batch->entries.reset(); batch->allocationDeferred = batch->response && batch->response->accepted();
            } catch (...) { batch->entries.reset(); }
            return std::shared_ptr<const LifecycleBatch>(batch);
        });
        auto future = task.get_future();
        lifecycleThread_ = std::thread(std::move(task));
        lifecycleFuture_ = std::move(future);
        if (retryDecode) flight.answer.reset();
    } catch (const std::bad_alloc&) {
        // Keep a completed answer/committed ticket for retry after quota relief.
        // No second HTTP request and no cursor movement precede adoption.
    } catch (...) {
        // No detached job. A running charged task stays owned until actual exit.
        if (lifecycleFlight_) lifecycleFlight_->cancelled->store(true);
        if (!lifecycleThread_.joinable()) retireRecordingLifecycle();
    }
public:
    [[nodiscard]] const std::string& authSessionToken() const noexcept { return authSessionToken_; }
    [[nodiscard]] const auto& currentAccount() const noexcept { return currentAccount_; }
    [[nodiscard]] auto authGeneration() const noexcept { return authGeneration_; }
    [[nodiscard]] bool microphonePermissionGranted() const noexcept { return readiness_.microphonePermissionGranted; }
    [[nodiscard]] bool recordingReady() const noexcept {
        return graf::windows::WindowsReadinessGate::evaluate(readiness()).recordingReady;
    }
    [[nodiscard]] ReadinessInputs readiness() const noexcept {
        auto result = readiness_;
        result.storageWritable = false;
        if (shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ ||
            deletionContinuationId_ || !storageStartup_) return result;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        const auto& work = *storageStartup_;
        result.storageWritable = protectedQueueComplete(work) && !work.stop && !work.terminal &&
            !work.cancellation->load();
        return result;
    }
    [[nodiscard]] const auto& microphones() const noexcept { return microphones_; }
    [[nodiscard]] const std::string& selectedMicrophone() const noexcept { return selectedMicrophone_; }
    [[nodiscard]] const std::wstring& sourceSummary() const noexcept { return sourceSummary_; }
    bool selectMicrophone(std::string identity) {
        if (exitAdmissionBlocked_ || updateAdmissionBlocked_ || indicator().visible) return false;
        const native_capture_detail::CustodyMutationScope mutation(synchronousMutations_);
        if (!native_capture_detail::saveMicrophonePreference(identity)) return false;
        selectedMicrophone_ = std::move(identity);
        microphonePreferenceLoaded_ = true;
        refreshReadiness();
        return true;
    }
    void recover(graf::windows::RecoveryTrigger trigger) {
        protectedPurgeAttemptGeneration_.reset(); // An explicit recovery event rearms a previously refused recycle.
        if (storageStartup_) {
            std::lock_guard<std::mutex> lock(storageStartup_->mutex);
            if (storageStartup_->commandReconciliation || storageStartup_->shortDiscardPending) {
                storageStartup_->reconcileRequested = true; storageStartup_->wake.notify_all();
            }
        }
        if (shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_) return;
        // This is only a retry-classification intent, never account authority or
        // a durable-success reply. The worker outcome is adopted by polling.
        if (trigger == graf::windows::RecoveryTrigger::authRecovered) protectedRecoveryEpoch_ = authGeneration_;
        if (!pendingRecovery_ || trigger == graf::windows::RecoveryTrigger::authRecovered) pendingRecovery_ = trigger;
        lifecycleRequested_ = true;
        requestAccountRevalidation();
    }
    void pollUploads() {
        pollStorageStartup(!pendingRecovery_ || !currentAccount_); // Offline display cannot wait for network recovery.
        pollAccount();
        scheduler_.retireProtected();
        pollProtectedDeletion(); // Retained answers drain even after exit/update closed admission.
        resumeProtectedLocalDeletion();
        pollRecordingLifecycle();
        if (storageStartup_ && protectedQueueValue_) {
            if (!shuttingDown_ && !exitAdmissionBlocked_ && !updateAdmissionBlocked_ && pendingRecovery_)
                requestProtectedUpload();
            return; // A protected root never falls through to the old plaintext queue.
        }
        if (exitAdmissionBlocked_) { (void)scheduler_.drain(); return; } // Cancelled completion only; never new work.
        if (shuttingDown_ || !localQueueComplete()) return;
        const native_capture_detail::CustodyMutationScope mutation(synchronousMutations_);
        (void)scheduler_.drain();
        if (!currentAccount_) return;
        if (shuttingDown_ || updateAdmissionBlocked_ || scheduler_.busy() || !pendingRecovery_) return;
        graf::windows::DesktopHttpConfig config;
        config.sessionToken = authSessionToken_;
        config.workspaceId = currentAccount_->workspaceId;
        // The workspace was verified by /auth/me. No fabricated device identity.
        // The confirmed account travels with the flight so a retry does not ask
        // /auth/me again; setAuthSessionToken clears it before any new upload.
        config.confirmedIdentity = currentAccount_;
        const auto trigger = *pendingRecovery_;
        pendingRecovery_.reset();
        // Failed dispatch is retried by the bounded 30-second recovery timer;
        // an empty queue must not repeatedly requeue auth states on every UI tick.
        (void)scheduler_.startAsync(trigger, std::move(config));
    }
    void requestShutdown() {
        if (exitAdmissionBlocked_) return;
        closeLocalPlayback();
        exitAdmissionBlocked_ = true;
        cancelRecordingLifecycle();
        cancelUnstartedRecording();
        if (deletionContinuationCancellation_) deletionContinuationCancellation_->store(true);
        pendingRecovery_.reset();
        protectedRecoveryEpoch_.reset();
        scheduler_.cancel();
        if (accountCancellation_) accountCancellation_->store(true);
        // App exit is not a deliberate stop: the recoverable fragment is kept.
        (void)controller_->stop(graf::windows::RecordingStopReason::interruption);
        noticePresenter_.dismiss();
    }
    void shutdown() {
        requestShutdown();
        if (deletionFlight_ || lifecycleFlight_ || lifecycleThread_.joinable()) { deletionShutdownPending_ = true; return; }
        if (shuttingDown_) return;
        shuttingDown_ = true;
        stopStorageStartup();
    }
    [[nodiscard]] graf::windows::TransitionResult pause() { return controller_->pause(); }
    [[nodiscard]] graf::windows::TransitionResult resume() { return controller_->resume(); }
    [[nodiscard]] bool privacyPending() const noexcept { return controller_->privacyPending(); }
    [[nodiscard]] std::wstring privacyActionSummary() const {
        if (controller_->privacyPending()) return L"Сохраняем изменение записи микрофона…";
        return controller_->privacyError() == ReasonCode::none ? L"" :
            L"Не удалось изменить паузу микрофона. Проверьте состояние записи и повторите действие.";
    }
    [[nodiscard]] graf::windows::TransitionResult stop() { cancelUnstartedRecording(); return controller_->stop(); }
    [[nodiscard]] graf::windows::TransitionResult stop(graf::windows::RecordingStopReason reason) {
        cancelUnstartedRecording();
        return controller_->stop(reason);
    }
    void tickNotice() { noticePresenter_.tick(std::chrono::steady_clock::now()); }
    std::function<void()> onShortRecordingPresented;
    graf::windows::RecordingNoticePresenter& notificationCard() { return noticePresenter_; }
    void pollHealth() {
        if (pendingStartReadiness_) {
            bool prepared = false, cancelled = !recordingWork_ || shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_;
            if (recordingWork_) {
                std::lock_guard<std::mutex> lock(recordingWork_->mutex);
                prepared = recordingWork_->prepared;
                cancelled = cancelled || recordingWork_->terminal || recordingWork_->cancellation->load() ||
                    recordingWork_->epoch != authGeneration_ || std::string_view(recordingWork_->session) != sessionId_;
            }
            if (!controller_->awaitingPreparation_ || cancelled || prepared) {
                const auto hardware = *pendingStartReadiness_;
                pendingStartReadiness_.reset(); // Consume before a guard or nested Stop can reenter polling.
                if (controller_->awaitingPreparation_ && !cancelled && prepared) {
                    const auto result = startPreparedRecording(hardware, std::move(controller_->startGuard_));
                    if (!result.accepted()) (void)controller_->stop(RecordingStopReason::interruption);
                } else if (controller_->awaitingPreparation_) (void)controller_->stop(RecordingStopReason::interruption);
            }
        }
        (void)controller_->pollHealth();
        const auto& state = indicator();
        if (diagnosticsSessionId_ == sessionId_ ||
            (state.state != graf::windows::SessionState::savedLocal &&
             state.state != graf::windows::SessionState::failed &&
             state.state != graf::windows::SessionState::blocked)) return;
        // Terminal state is published only after worker completion. These are
        // real 10-ms blocks, never unsynchronized live timeline measurements.
        graf::windows::MetadataSnapshot snapshot;
        snapshot.appVersion = "development";
        snapshot.osBuild = "unknown";
#ifdef _M_ARM64
        snapshot.architecture = "ARM64";
#else
        snapshot.architecture = "x64";
#endif
        try {
            const auto version = winrt::Windows::ApplicationModel::Package::Current().Id().Version();
            snapshot.appVersion = std::to_string(version.Major) + "." + std::to_string(version.Minor) +
                "." + std::to_string(version.Build) + "." + std::to_string(version.Revision);
        } catch (...) {} // Unpackaged builds have no package version.
        try {
            const auto version = std::stoull(winrt::to_string(
                winrt::Windows::System::Profile::AnalyticsInfo::VersionInfo().DeviceFamilyVersion()));
            snapshot.osBuild = std::to_string((version >> 16) & 0xFFFF);
        } catch (...) {}
        snapshot.state = state.state;
        snapshot.reason = state.reason;
        snapshot.processedBlocks = protectedRecordingProcessedFrames();
        snapshot.writtenBlocks = protectedRecordingFrames();
        snapshot.durationMs = snapshot.writtenBlocks * 10;
        snapshot.endpointIdentity = recordingEndpointIdentity_;
        snapshot.trustedPrefixRetained = controller_->finalization().trustedPrefixRetained;
        snapshot.renderClock = controller_->clockDiagnostics(graf::windows::AudioSource::systemRender);
        snapshot.microphoneClock = controller_->clockDiagnostics(graf::windows::AudioSource::microphone);
        lastDiagnostics_ = graf::windows::MetadataSafeDiagnostics::serialize(snapshot);
        diagnosticsSessionId_ = sessionId_;
        if (controller_->finalization().shortRecordingDiscarded && !shuttingDown_ &&
            !exitAdmissionBlocked_ && !updateAdmissionBlocked_)
            noticePresenter_.queueShortRecordingDiscarded(std::chrono::steady_clock::now(), onShortRecordingPresented);
    }
    [[nodiscard]] const std::string& diagnostics() const noexcept { return lastDiagnostics_; }
    [[nodiscard]] std::string_view activeRecordingSession() const {
        return protectedRecordingPending() ? std::string_view(sessionId_) : std::string_view{};
    }
    [[nodiscard]] const auto& finalization() const noexcept { return controller_->finalization(); }
    [[nodiscard]] const graf::windows::RecordingIndicatorSnapshot& indicator() const noexcept {
        return controller_->indicator().snapshot();
    }
    [[nodiscard]] AudioLevels audioLevels() const noexcept {
        return {microphoneLevel_.load(std::memory_order_relaxed),
                systemRenderLevel_.load(std::memory_order_relaxed)};
    }

    struct LocalQueueObservation {
        std::shared_ptr<const graf::windows::ProtectedUploadQueueValue> value;
        bool complete = false;
        std::shared_ptr<const ProtectedLocalRecordingTimings> timings;
        LocalProblemContext contentContext;
    };
    struct LocalPlaybackObservation {
        ProtectedLocalRecordingPlayback::Snapshot media;
        std::uint64_t documentGeneration = 0;
        bool present = false, preparing = false, terminal = false;
    };
    [[nodiscard]] LocalPlaybackObservation localPlaybackObservation() const {
        if (!storageStartup_) return {};
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        const auto playback = storageStartup_->playback;
        return playback ? LocalPlaybackObservation{playback->media, playback->documentGeneration,
            true, playback->preparing, playback->terminal} : LocalPlaybackObservation{};
    }
    [[nodiscard]] bool openLocalPlayback(std::string_view id, std::uint64_t documentGeneration, bool muted = false) try {
        const auto context = localContentContext();
        if (!documentGeneration || id.empty() || id.size() > 300 || context.owner.empty() || context.workspace.empty() ||
            restrictiveLifecyclePending()) return false;
        const auto observation = localObservation();
        if (!observation.complete || !observation.value) return false;
        const auto& rows = observation.value->items();
        const auto found = std::find_if(rows.begin(), rows.end(), [&](const auto& row) {
            return std::string_view(row.localRecordingId) == id && std::string_view(row.ownerUserId) == context.owner &&
                std::string_view(row.ownerWorkspaceId) == context.workspace;
        });
        if (found == rows.end()) return false;
        if (lifecycleEnabled_) {
            lifecycleOpen_ = found->localRecordingId;
            if (!lifecycleFlight_) lifecycleRequested_ = true;
        }
        if (!playbackRowCurrent(*observation.value, *found)) return false;
        if (found->status == UploadQueueStatus::quarantined &&
            (std::string_view(found->sessionId) == activeRecordingSession() || !observation.timings ||
             !observation.timings->playableDegraded(observation.value, static_cast<std::size_t>(found - rows.begin())))) return false;
        auto playback = std::allocate_shared<PlaybackWork>(CustodyAllocator<PlaybackWork>{});
        playback->snapshot = observation.value; playback->index = static_cast<std::size_t>(found - rows.begin());
        playback->epoch = authGeneration_; playback->documentGeneration = documentGeneration; playback->muted = muted;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        auto& work = *storageStartup_;
        if (work.stop || work.queueFailed || work.inFlight || !work.adopted ||
            (work.playback && !work.playback->terminal)) return false;
        work.playback = std::move(playback); work.wake.notify_all();
        return true;
    } catch (...) { return false; }
    [[nodiscard]] bool authorizeLocalPlayback(std::uint64_t documentGeneration) {
        if (!storageStartup_) return false;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        const auto playback = storageStartup_->playback;
        if (!playbackCurrent(playback) || playback->documentGeneration != documentGeneration ||
            playback->preparing || !playback->media.ready || playback->authorized) return false;
        playback->authorized = true; playback->paused = false; ++playback->serial;
        storageStartup_->wake.notify_all(); return true;
    }
    [[nodiscard]] bool pauseLocalPlayback(bool pause) {
        if (!storageStartup_) return false;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        const auto playback = storageStartup_->playback;
        if (!playbackCurrent(playback) || !playback->authorized) return false;
        playback->paused = pause; ++playback->serial;
        storageStartup_->wake.notify_all(); return true;
    }
    [[nodiscard]] bool seekLocalPlayback(double seconds) {
        if (!storageStartup_ || !std::isfinite(seconds) || seconds < 0) return false;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        const auto playback = storageStartup_->playback;
        if (!playbackCurrent(playback) || !playback->authorized || seconds > playback->media.durationSeconds) return false;
        playback->seek = seconds; ++playback->serial;
        storageStartup_->wake.notify_all(); return true;
    }
    void closeLocalPlayback() noexcept {
        if (!storageStartup_) return;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        if (storageStartup_->playback) storageStartup_->playback->cancelled->store(true);
        storageStartup_->wake.notify_all();
    }
    // UI-owner observation only, never a grant to inspect files or mutate them.
    [[nodiscard]] LocalQueueObservation localObservation() const {
        if (shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ || !storageStartup_) return {};
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        const auto& work = *storageStartup_;
        if (!work.ready || !work.adopted || !work.startupValue || !protectedQueueValue_ ||
            work.stop || work.terminal || work.queueFailed || work.reconciliationPending ||
            work.error != graf::windows::CustodyFileError::none) return {};
        const auto display = work.display;
        const auto context = localContentContext();
        const bool current = display && display->done.load(std::memory_order_acquire) && !display->cancelled->load() &&
            display->epoch == authGeneration_ && display->snapshot == protectedQueueValue_ && !context.owner.empty() &&
            std::string_view(display->user) == context.owner && std::string_view(display->workspace) == context.workspace;
        return {protectedQueueValue_, protectedQueueComplete(work),
            current ? display->result : nullptr, context};
    }

    [[nodiscard]] const auto& localItems() const noexcept { return queue_.items(); }
    [[nodiscard]] std::optional<QueueMutationTicket> requestProtectedManualSend(
        const std::shared_ptr<const ProtectedUploadQueueValue>& snapshot, std::string_view id,
        std::uint64_t epoch, bool confirmUnowned) {
        if (shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ || epoch != authGeneration_ ||
            !currentAccount_ || authSessionToken_.empty() || !snapshot || !storageStartup_) return std::nullopt;
        const auto observation = localObservation();
        if (!observation.complete || observation.value != snapshot) return std::nullopt;
        for (std::size_t index = 0; index != snapshot->items().size(); ++index) {
            if (std::string_view(snapshot->items()[index].localRecordingId) != id) continue;
            if (!snapshot->canManualSend(index, currentAccount_->userId, currentAccount_->workspaceId, confirmUnowned)) return std::nullopt;
            return requestProtectedUpload(snapshot, index, confirmUnowned);
        }
        return std::nullopt;
    }
    [[nodiscard]] std::optional<QueueMutationTicket> protectedManualSendTicket(std::uint64_t id) const noexcept {
        return lastManualSendTicket_ && lastManualSendTicket_->id == id ? lastManualSendTicket_ : std::nullopt;
    }
    void cancelProtectedManualSend(std::uint64_t id) noexcept {
        if (!storageStartup_ || !lastManualSendTicket_ || lastManualSendTicket_->id != id) return;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        if (storageStartup_->upload && storageStartup_->upload->manualIndex) storageStartup_->upload->cancelled->store(true);
        storageStartup_->wake.notify_all(); // Publication already completed is still adopted as physical truth.
    }
    // The native shell has confirmed this exact adopted row, or recovery is
    // continuing its already durable user intent. Never a server delete route.
    [[nodiscard]] std::optional<QueueMutationTicket> requestProtectedLocalRemoval(
        const std::shared_ptr<const ProtectedUploadQueueValue>& snapshot, std::string_view id,
        std::uint64_t epoch, bool resumeIntent = false) {
        if (shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ ||
            !snapshot || epoch != authGeneration_ || !currentAccount_) return std::nullopt;
        for (std::size_t index = 0; index != snapshot->items().size(); ++index) {
            if (std::string_view(snapshot->items()[index].localRecordingId) != id) continue;
            if (!snapshot->canLocalRemoval(index, currentAccount_->userId, currentAccount_->workspaceId, resumeIntent)) return std::nullopt;
            return beginProtectedDeletionSelection({}, snapshot, index, resumeIntent);
        }
        return std::nullopt;
    }
    [[nodiscard]] std::optional<QueueMutationTicket> beginProtectedDeletionSelection(ProtectedDeletionTargets&& targets,
        const std::shared_ptr<const ProtectedUploadQueueValue>& localSnapshot = {},
        std::optional<std::size_t> localIndex = {}, bool resumeLocalIntent = false) {
        if (deletionFlight_ || deletionCompletion_ || !currentAccount_ || authSessionToken_.empty()) return std::nullopt;
        try {
            auto flight = std::allocate_shared<DeletionFlight>(CustodyAllocator<DeletionFlight>{});
            auto& config = flight->config;
            config.sessionToken = std::string_view(authSessionToken_);
            config.workspaceId = std::string_view(currentAccount_->workspaceId);
            config.confirmedIdentity.emplace();
            config.confirmedIdentity->userId = std::string_view(currentAccount_->userId);
            config.confirmedIdentity->workspaceId = config.workspaceId;
            config.scopedAccount = BasicDeletionScope<CustodyString>{config.confirmedIdentity->userId, config.workspaceId};
            const auto ticket = requestProtectedDeletionSelection(std::move(targets), true, localSnapshot, localIndex, resumeLocalIntent);
            if (!ticket) return std::nullopt;
            config.cancellation = protectedDeletionCancellation(ticket->id);
            flight->completion.id = ticket->id; flight->completion.epoch = ticket->epoch;
            flight->waiting = *ticket;
            deletionFlight_ = std::move(flight); // All allocations precede accepted intent.
            return ticket;
        } catch (...) { return std::nullopt; }
    }
    [[nodiscard]] std::optional<DeletionCompletion> takeProtectedDeletionCompletion(std::uint64_t id) noexcept {
        if (!deletionCompletion_ || deletionCompletion_->id != id) return std::nullopt;
        const auto result = deletionCompletion_; deletionCompletion_.reset(); return result;
    }
    [[nodiscard]] bool beginProtectedLocalPurgePass() try {
        if (!currentAccount_ || authSessionToken_.empty() || !storageStartup_ || deletionFlight_ || deletionCompletion_ ||
            deletionContinuationId_ || shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ ||
            GetTickCount64() < localPurgeRetryAt_) return false;
        const auto observation = localObservation();
        if (!observation.complete || !observation.value) return false;
        auto flight = std::allocate_shared<DeletionFlight>(CustodyAllocator<DeletionFlight>{});
        auto cancellation = std::allocate_shared<std::atomic<bool>>(CustodyAllocator<std::atomic<bool>>{}, false);
        auto& config = flight->config;
        config.sessionToken = std::string_view(authSessionToken_); config.workspaceId = std::string_view(currentAccount_->workspaceId);
        config.confirmedIdentity.emplace(); config.confirmedIdentity->userId = std::string_view(currentAccount_->userId);
        config.confirmedIdentity->workspaceId = config.workspaceId;
        config.scopedAccount = BasicDeletionScope<CustodyString>{config.confirmedIdentity->userId, config.workspaceId};
        config.cancellation = cancellation;
        flight->snapshot = observation.value; // Immutable charged data, no native lease or queue service.
        flight->phase = DeletionFlight::Phase::purgeList; flight->serverPurge = true;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        auto& work = *storageStartup_;
        if (!work.adopted || !work.startupValue || work.stop || work.terminal || work.queueFailed || work.reconciliationPending ||
            work.error != CustodyFileError::none || work.inFlight || work.recording || work.upload || scheduler_.busy() ||
            work.nextTicket == (std::numeric_limits<std::uint64_t>::max)()) return false;
        // Ephemeral reservation only: no fabricated task, saved intent or OS
        // permission. Actual tasks still require their own adopted tickets.
        flight->completion.id = deletionContinuationId_ = ++work.nextTicket;
        flight->completion.epoch = deletionContinuationEpoch_ = authGeneration_;
        deletionContinuationCancellation_ = std::move(cancellation);
        deletionFlight_ = std::move(flight);
        return true;
    } catch (...) { return false; }
    // Accepted pending ticket is not saved/deleted. The existing polling ACK
    // adopts storage truth; no network or purge is dispatched by this entry.
    [[nodiscard]] std::optional<QueueMutationTicket> requestProtectedDeletion(std::string_view id) try {
        if (!currentAccount_ || shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ ||
            id.empty() || id.size() > 300 || !storageStartup_) return std::nullopt;
        const auto observation = localObservation();
        if (!observation.complete || !observation.value) return std::nullopt;
        const auto& rows = observation.value->items();
        const auto found = std::find_if(rows.begin(), rows.end(), [&](const auto& row) {
            return std::string_view(row.localRecordingId) == id && std::string_view(row.ownerUserId) == currentAccount_->userId &&
                std::string_view(row.ownerWorkspaceId) == currentAccount_->workspaceId;
        });
        if (found == rows.end() || found->status == UploadQueueStatus::uploading || !hasUploadServerIdentity(*found))
            return std::nullopt;
        ProtectedDeletionTargets targets;
        targets.push_back({DeletionTarget::ownOrigin, found->directoryId});
        return requestProtectedDeletionSelection(std::move(targets));
    } catch (...) { return std::nullopt; }
    [[nodiscard]] std::optional<QueueMutationTicket> requestProtectedDeletionSelection(ProtectedDeletionTargets&& targets,
        bool reserveContinuation = false, const std::shared_ptr<const ProtectedUploadQueueValue>& localSnapshot = {},
        std::optional<std::size_t> localIndex = {}, bool resumeLocalIntent = false) try {
        if (!currentAccount_ || shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ || !storageStartup_ ||
            deletionContinuationId_ || (localIndex ? !targets.empty() : targets.empty()) ||
            targets.size() > DesktopHttpTransport::kLifecycleSelectionLimit) return std::nullopt;
        const auto observation = localObservation();
        if (!observation.complete || !observation.value) return std::nullopt;
        if (localIndex) {
            if (observation.value != localSnapshot || !localSnapshot->canLocalRemoval(*localIndex,
                currentAccount_->userId, currentAccount_->workspaceId, resumeLocalIntent)) return std::nullopt;
        } else if (localSnapshot || resumeLocalIntent) return std::nullopt;
        for (const auto& target : targets) {
            if (target.target == DeletionTarget::meeting) {
                if (!DesktopApiClient::accountId(target.targetId)) return std::nullopt;
                continue;
            }
            if (target.target != DeletionTarget::ownOrigin || !DesktopUploadQueueService::validIdentity(target.targetId))
                return std::nullopt;
            const auto& rows = observation.value->items();
            const auto found = std::find_if(rows.begin(), rows.end(), [&](const auto& row) { return row.directoryId == target.targetId; });
            if (found == rows.end() || std::string_view(found->ownerUserId) != currentAccount_->userId ||
                std::string_view(found->ownerWorkspaceId) != currentAccount_->workspaceId ||
                found->status == UploadQueueStatus::uploading) return std::nullopt;
        }
        auto deletion = std::allocate_shared<DeletionWork>(CustodyAllocator<DeletionWork>{});
        deletion->snapshot = observation.value; deletion->targets = std::move(targets);
        deletion->localIndex = localIndex; deletion->resumeLocalIntent = resumeLocalIntent;
        deletion->plan = std::allocate_shared<ProtectedDeletionPlan>(CustodyAllocator<ProtectedDeletionPlan>{});
        deletion->user = std::string_view(currentAccount_->userId);
        deletion->workspace = std::string_view(currentAccount_->workspaceId);
        const auto origin = DesktopHttpConfig{}.baseOrigin;
        deletion->origin.assign(origin.begin(), origin.end());
        return submitProtectedDeletion(std::move(deletion), QueueMutationKind::deletionIntent, reserveContinuation);
    } catch (...) { return std::nullopt; }
    enum class LocalPurgePhase { intent, purge };
    // Internal scoped task continuation, not a bridge capability. The caller
    // must adopt intent first and derive success only from the adopted proof.
    [[nodiscard]] std::optional<QueueMutationTicket> requestProtectedLocalPurge(
        const BasicLocalPurgeTask<CustodyString>& task,
        const std::shared_ptr<const ProtectedUploadQueueValue>& expectedSnapshot, std::uint64_t expectedEpoch,
        LocalPurgePhase phase, std::string_view localId = {}, std::uint64_t continuationId = 0,
        bool reserveContinuation = false) try {
        if (!currentAccount_ || authSessionToken_.empty() || shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ ||
            expectedEpoch != authGeneration_ || !expectedSnapshot || !storageStartup_ || !validLocalBufferPurgeTask(task) ||
            (reserveContinuation && phase != LocalPurgePhase::intent) ||
            (phase == LocalPurgePhase::purge && !continuationId)) return std::nullopt;
        const auto observation = localObservation();
        if (!observation.complete || observation.value != expectedSnapshot) return std::nullopt;
        auto deletion = std::allocate_shared<DeletionWork>(CustodyAllocator<DeletionWork>{});
        deletion->snapshot = expectedSnapshot; deletion->serverTask = task;
        deletion->user = std::string_view(currentAccount_->userId);
        deletion->workspace = std::string_view(currentAccount_->workspaceId);
        if (continuationId) {
            if (continuationId != deletionContinuationId_ || expectedEpoch != deletionContinuationEpoch_ ||
                !deletionContinuationCancellation_ || deletionContinuationCancellation_->load()) return std::nullopt;
            deletion->cancelled = deletionContinuationCancellation_;
        }
        if (phase == LocalPurgePhase::purge) {
            const auto& rows = expectedSnapshot->items();
            const auto found = std::find_if(rows.begin(), rows.end(), [&](const auto& row) {
                return std::string_view(row.localRecordingId) == localId;
            });
            if (found == rows.end() || found->status != UploadQueueStatus::uploaded || found->safeReason != "local_delete_pending" ||
                found->meetingId != task.meetingId || found->ownerUserId != deletion->user ||
                found->ownerWorkspaceId != deletion->workspace) return std::nullopt;
            deletion->index = static_cast<std::size_t>(found - rows.begin());
        } else if (!localId.empty()) return std::nullopt;
        return submitProtectedDeletion(std::move(deletion), phase == LocalPurgePhase::intent ?
            QueueMutationKind::deletionIntent : QueueMutationKind::deletionPurge, reserveContinuation, continuationId);
    } catch (...) { return std::nullopt; }
    [[nodiscard]] std::shared_ptr<const std::atomic<bool>> protectedDeletionCancellation(std::uint64_t id) const noexcept {
        return id && id == deletionContinuationId_ ? deletionContinuationCancellation_ : nullptr;
    }
    // The caller has reaped its network thread. A storage ticket/result still
    // awaiting adoption or reconciliation cannot be retired by this control ACK.
    [[nodiscard]] bool endProtectedDeletionContinuation(std::uint64_t id) {
        if (!id || id != deletionContinuationId_ || !storageStartup_) return false;
        if (deletionFlight_ && (deletionThread_.joinable() || deletionFlight_->phase != DeletionFlight::Phase::retire)) return false;
        {
            std::lock_guard<std::mutex> lock(storageStartup_->mutex);
            const auto& work = *storageStartup_;
            if (work.inFlight || work.reconciliationPending || (work.resultReady && !work.resultAdopted)) return false;
            deletionContinuationId_ = deletionContinuationEpoch_ = 0;
            deletionContinuationCancellation_.reset();
        }
        if (updateAdmissionBlocked_) stopStorageStartup();
        return true;
    }
    [[nodiscard]] std::optional<QueueMutationTicket> protectedDeletionTicket(std::uint64_t id) const noexcept {
        return lastDeletionTicket_ && lastDeletionTicket_->id == id ? lastDeletionTicket_ : std::nullopt;
    }
    [[nodiscard]] std::shared_ptr<const ProtectedDeletionPlan> protectedDeletionPlan(std::uint64_t id) const noexcept {
        if (!lastDeletionTicket_ || lastDeletionTicket_->id != id ||
            lastDeletionTicket_->kind != QueueMutationKind::deletionIntent ||
            lastDeletionTicket_->state != QueueTicketState::committed || lastDeletionTicket_->epoch != authGeneration_ ||
            !currentAccount_) return {};
        return lastDeletionPlan_;
    }
    // The answer is retained until the existing worker commits and UI adopts its
    // ticket. Pending is not server acceptance, and never authorizes local purge.
    [[nodiscard]] std::optional<QueueMutationTicket> applyProtectedDeletionAnswer(
        const std::shared_ptr<const ProtectedUploadQueueValue>& expectedSnapshot, std::uint64_t expectedEpoch,
        std::string_view operationId, BasicDeletionWireResult<CustodyString> answer,
        std::uint64_t continuationId = 0) try {
        const bool accepted = continuationId && continuationId == deletionContinuationId_ &&
            expectedEpoch == deletionContinuationEpoch_;
        if (!currentAccount_ || shuttingDown_ || ((!accepted) && (exitAdmissionBlocked_ || updateAdmissionBlocked_)) ||
            expectedEpoch != authGeneration_ || !expectedSnapshot || !DesktopApiClient::accountId(operationId) ||
            !storageStartup_ || answer.body.size() > 2 * 1024 * 1024)
            return std::nullopt;
        // Accepted exit/update drain cannot use the deliberately closed public
        // observation. Admission below still checks the genuine worker state.
        if (protectedQueueValue_ != expectedSnapshot) return std::nullopt;
        const auto& operations = expectedSnapshot->deletionOperations();
        const auto origin = DesktopHttpConfig{}.baseOrigin;
        const auto found = std::find_if(operations.begin(), operations.end(), [&](const auto& operation) {
            return std::string_view(operation.operationId) == operationId &&
                std::string_view(operation.actorUserId) == currentAccount_->userId &&
                std::string_view(operation.workspaceId) == currentAccount_->workspaceId &&
                std::string_view(operation.serverOrigin) == origin;
        });
        if (found == operations.end()) return std::nullopt;
        auto deletion = std::allocate_shared<DeletionWork>(CustodyAllocator<DeletionWork>{});
        deletion->snapshot = expectedSnapshot; deletion->index = static_cast<std::size_t>(found - operations.begin());
        deletion->origin.assign(origin.begin(), origin.end()); deletion->answer = std::move(answer);
        return submitProtectedDeletion(std::move(deletion), QueueMutationKind::deletionResult, false, continuationId);
    } catch (...) { return std::nullopt; }
private:
    [[nodiscard]] bool deletionContextCurrent(const DeletionFlight& flight) const noexcept {
        return currentAccount_ && flight.completion.epoch == authGeneration_ &&
            std::string_view(flight.config.sessionToken) == authSessionToken_ &&
            std::string_view(flight.config.confirmedIdentity->userId) == currentAccount_->userId &&
            std::string_view(flight.config.workspaceId) == currentAccount_->workspaceId;
    }
    void launchProtectedPurgeRequest(DeletionFlight& flight, DeletionFlight::Phase next,
        LocalPurgeAckState state = LocalPurgeAckState::failed, std::string_view reason = {}) {
        using Phase = DeletionFlight::Phase;
        auto batch = std::allocate_shared<DeletionFlight::PurgeTaskBatch>(CustodyAllocator<DeletionFlight::PurgeTaskBatch>{});
        CustodyString meeting, code(reason);
        std::optional<BasicLocalPurgeTask<CustodyString>> expected;
        const auto awaitingSnapshot = next == Phase::purgeListed ? flight.snapshot : nullptr;
        if (next == Phase::purgeEnsured) meeting = flight.awaiting[flight.ensureIndex];
        if (next == Phase::purgeAcked) expected = (*flight.purgeTasks->tasks)[flight.index];
        std::packaged_task<std::shared_ptr<const ProtectedDeletionResponse>()> task(
            [config = flight.config, wire = protectedWire_, batch, awaitingSnapshot, next, meeting = std::move(meeting),
             expected = std::move(expected), state, code = std::move(code)] {
                std::shared_ptr<const ProtectedDeletionResponse> response;
                if (next == Phase::purgeListed) response = DesktopHttpTransport::localPurgeTasksProtected(config, true, wire);
                else if (next == Phase::purgeEnsured) response = DesktopHttpTransport::ensureLocalPurgeTaskProtected(config, meeting, false, wire);
                else {
                    const auto now = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
                    const auto instant = now > 0 ? DesktopApiClient::formatUtcInstant<CustodyString>(static_cast<std::uint64_t>(now)) : CustodyString{};
                    response = DesktopHttpTransport::acknowledgeLocalPurgeTaskProtected(config, expected->taskId, state, code, instant, false, wire);
                }
                if (!response || !response->answered() || !config.cancellation || config.cancellation->load()) return response;
                if (next == Phase::purgeListed && response->status == 200) {
                    batch->tasks = DesktopApiClient::decodeLocalPurgeTaskList<CustodyString>(response->body, config.cancellation.get());
                    if (batch->tasks) {
                        batch->awaiting = awaitingSnapshot->meetingsAwaitingLocalPurge(config.confirmedIdentity->userId,
                            config.workspaceId, config.baseOrigin, config.cancellation.get());
                        batch->awaiting.erase(std::remove_if(batch->awaiting.begin(), batch->awaiting.end(), [&](const auto& id) {
                            return std::any_of(batch->tasks->begin(), batch->tasks->end(), [&](const auto& task) {
                                return task.meetingId == id && task.taskType == "purge_local_buffers";
                            });
                        }), batch->awaiting.end());
                    }
                } else if ((next == Phase::purgeEnsured && (response->status == 200 || response->status == 201)) ||
                    (next == Phase::purgeAcked && response->status == 200)) {
                    auto decoded = DesktopApiClient::decodeLocalPurgeTask<CustodyString>(response->body, config.cancellation.get());
                    const bool exact = decoded && (next == Phase::purgeEnsured ? decoded->meetingId == meeting :
                        (decoded->taskId == expected->taskId && decoded->meetingId == expected->meetingId &&
                         decoded->taskType == expected->taskType && decoded->state == (state == LocalPurgeAckState::acknowledged ? "acknowledged" : "failed")));
                    if (exact) { batch->tasks.emplace(); batch->tasks->push_back(std::move(*decoded)); }
                }
                return response;
            });
        auto future = task.get_future();
        deletionThread_ = std::thread(std::move(task));
        deletionFuture_ = std::move(future); flight.response.reset();
        // The producer owns batch until the common handler observes actual
        // thread exit and joins. Only an immutable data snapshot crosses;
        // never UI, mutable queue/service pointers or native leases.
        flight.purgeTasks = std::move(batch); flight.afterNetwork = next;
        flight.phase = Phase::network;
    }
    void pollProtectedPurgeTasks(DeletionFlight& flight, bool newEffects) {
        using Phase = DeletionFlight::Phase;
        if (!newEffects) { flight.phase = Phase::retire; return; }
        if (flight.phase == Phase::purgeList) {
            try { launchProtectedPurgeRequest(flight, Phase::purgeListed); }
            catch (...) { flight.phase = Phase::retire; }
            return;
        }
        if (flight.phase == Phase::purgeListed || flight.phase == Phase::purgeEnsured || flight.phase == Phase::purgeAcked) {
            if (!flight.purgeTasks || !flight.purgeTasks->tasks) { flight.phase = Phase::retire; return; }
            if (flight.phase == Phase::purgeListed) {
                flight.awaiting = std::move(flight.purgeTasks->awaiting); flight.snapshot.reset();
                flight.index = 0;
            } else if (flight.phase == Phase::purgeEnsured) { ++flight.ensureIndex; flight.index = 0; }
            else {
                // ACK has its own small decoded response batch. Continue with
                // the retained source list, never with the ACK as new work.
                flight.purgeTasks = std::move(flight.purgeSource); ++flight.index;
            }
            flight.response.reset(); flight.phase = Phase::purgeTask;
        }
        if (flight.phase == Phase::purgeIntent || flight.phase == Phase::purgeCommitted) {
            const auto ticket = protectedDeletionTicket(flight.waiting.id);
            if (!ticket || ticket->state == QueueTicketState::pending) return;
            if (ticket->state != QueueTicketState::committed) { flight.phase = Phase::retire; return; }
            if (flight.phase == Phase::purgeIntent) flight.localIndex = 0;
            else if (!ticket->changed) ++flight.localIndex; // Busy/absent refusal is not success and must not spin.
            flight.snapshot.reset(); flight.phase = Phase::purgeRows;
        }
        if (flight.phase == Phase::purgeTask) {
            if (flight.index == flight.purgeTasks->tasks->size()) {
                if (flight.ensureIndex == flight.awaiting.size()) { flight.phase = Phase::retire; return; }
                try { launchProtectedPurgeRequest(flight, Phase::purgeEnsured); }
                catch (...) { flight.phase = Phase::retire; }
                return;
            }
            const auto& task = (*flight.purgeTasks->tasks)[flight.index];
            if (task.acknowledged()) { ++flight.index; return; }
            const auto observation = localObservation(); if (!observation.complete || !observation.value) return;
            if (!validLocalBufferPurgeTask(task) || observation.value->localPurgeAcknowledged(task)) flight.phase = Phase::purgeAck;
            else {
                const auto ticket = requestProtectedLocalPurge(task, observation.value, flight.completion.epoch,
                    LocalPurgePhase::intent, {}, flight.completion.id);
                if (!ticket) {
                    std::lock_guard<std::mutex> lock(storageStartup_->mutex);
                    if (storageStartup_->terminal || storageStartup_->stop || storageStartup_->queueFailed) flight.phase = Phase::retire;
                    return;
                }
                flight.waiting = *ticket; flight.phase = Phase::purgeIntent; return;
            }
        }
        if (flight.phase == Phase::purgeRows) {
            const auto observation = localObservation(); if (!observation.complete || !observation.value) return;
            const auto& task = (*flight.purgeTasks->tasks)[flight.index];
            const auto& rows = observation.value->items();
            while (flight.localIndex < rows.size()) {
                const auto& row = rows[flight.localIndex];
                if (row.meetingId != task.meetingId || row.status != UploadQueueStatus::uploaded ||
                    row.ownerUserId != flight.config.confirmedIdentity->userId || row.ownerWorkspaceId != flight.config.workspaceId) {
                    ++flight.localIndex; continue;
                }
                const auto ticket = requestProtectedLocalPurge(task, observation.value, flight.completion.epoch,
                    LocalPurgePhase::purge, row.localRecordingId, flight.completion.id);
                if (!ticket) return; // Actual display/playback drain can refuse admission temporarily.
                flight.waiting = *ticket; flight.phase = Phase::purgeCommitted; return;
            }
            flight.phase = Phase::purgeAck;
        }
        if (flight.phase == Phase::purgeAck) {
            const auto observation = localObservation(); if (!observation.complete || !observation.value) return;
            const auto& task = (*flight.purgeTasks->tasks)[flight.index];
            const bool proven = observation.value->localPurgeAcknowledged(task);
            const bool remains = std::any_of(observation.value->items().begin(), observation.value->items().end(),
                [&](const auto& row) { return row.meetingId == task.meetingId; });
            const auto reason = proven ? "local_artifacts_deleted" : validLocalBufferPurgeTask(task) && remains ? "local_purge_failed" : "local_purge_unverified";
            try {
                flight.purgeSource = flight.purgeTasks;
                launchProtectedPurgeRequest(flight, Phase::purgeAcked,
                    proven ? LocalPurgeAckState::acknowledged : LocalPurgeAckState::failed, reason);
            } catch (...) { flight.phase = Phase::retire; }
        }
    }
    void pollProtectedDeletion() try {
        if (!deletionFlight_ || deletionPolling_) return;
        const native_capture_detail::CustodyMutationScope polling(deletionPolling_);
        auto& flight = *deletionFlight_;
        using Phase = DeletionFlight::Phase;
        const bool current = deletionContextCurrent(flight);
        if (!current && deletionContinuationCancellation_) deletionContinuationCancellation_->store(true);
        const bool newEffects = current && !shuttingDown_ && !exitAdmissionBlocked_ && !updateAdmissionBlocked_ &&
            flight.config.cancellation && !flight.config.cancellation->load();
        if (!flight.serverPurge && (flight.phase == Phase::intent || flight.phase == Phase::answer || flight.phase == Phase::purgeAnswer)) {
            const auto ticket = protectedDeletionTicket(flight.waiting.id);
            if (!ticket || ticket->state == QueueTicketState::pending) return;
            if (ticket->state != QueueTicketState::committed) {
                flight.completion.unknown = ticket->state == QueueTicketState::ambiguous;
                flight.phase = Phase::retire;
            } else if (flight.phase == Phase::intent) {
                flight.plan = protectedDeletionPlan(ticket->id);
                flight.completion.saved = true;
                flight.phase = flight.plan && newEffects ? Phase::result : Phase::retire;
            } else if (flight.phase == Phase::purgeAnswer) {
                ++flight.localIndex; flight.snapshot.reset();
                flight.phase = newEffects ? Phase::purge : Phase::retire;
            } else {
                // This ACK adopted the response before any next HTTP. The old
                // pinned snapshot may now be released; the next request pins anew.
                const auto expiry = flight.response ? flight.response->authExpiresAt : std::nullopt;
                ++flight.index; flight.snapshot.reset();
                if (!flight.sharedFailure) flight.response.reset();
                flight.phase = newEffects ? Phase::result : Phase::retire;
                if (expiry && current && !exitAdmissionBlocked_ && !updateAdmissionBlocked_ && sessionExpiryHandler_) {
                    sessionExpiryHandler_(*expiry);
                    return; // The handler may reenter; do not access the old context afterwards.
                }
            }
        }
        if (flight.phase == Phase::network) {
            // A ready packaged_task future can precede thread-local destruction.
            if (WaitForSingleObject(deletionThread_.native_handle(), 0) != WAIT_OBJECT_0) return;
            deletionThread_.join();
            try { flight.response = deletionFuture_.get(); } catch (...) { flight.response.reset(); }
            flight.phase = flight.afterNetwork;
            if (!flight.response || !current) flight.phase = Phase::retire;
            if (flight.serverPurge && flight.response) {
                if (newEffects && flight.response->status == 429) localPurgeRetryAt_ = GetTickCount64() +
                    static_cast<std::uint64_t>(flight.response->retryAfterSeconds) * 1000;
                const auto expiry = flight.response->authExpiresAt;
                if (expiry && newEffects && sessionExpiryHandler_) sessionExpiryHandler_(*expiry);
            }
            return; // Retained response is observable before its separate storage admission.
        }
        if (flight.serverPurge) pollProtectedPurgeTasks(flight, newEffects);
        if (flight.phase == Phase::result) {
            if (!flight.plan || !current) flight.phase = Phase::retire;
            else if (flight.index == flight.plan->requests.size()) flight.phase = Phase::purge;
            else if (flight.response) {
                // Retain the original response through allocation/admission
                // refusal; a failed copy must never discard a received answer.
                BasicDeletionWireResult<CustodyString> answer{flight.response->status, flight.response->body,
                    flight.response->transportFailed, flight.response->retryAfterSeconds, flight.response->safeReason};
                flight.sharedFailure = DesktopUploadQueueService::deletionFailureIsShared(answer);
                if (!flight.snapshot) {
                    if (!newEffects) { flight.phase = Phase::retire; }
                    else {
                        const auto observation = localObservation();
                        if (!observation.complete || !observation.value) return;
                        flight.snapshot = observation.value; // Shared failure, following a prior ACK; no HTTP.
                    }
                }
                if (flight.phase == Phase::result) {
                    // Never rebind a response to a different queue generation.
                    if (flight.snapshot != protectedQueueValue_) {
                        flight.completion.unknown = true; flight.phase = Phase::retire;
                    } else {
                        const auto ticket = applyProtectedDeletionAnswer(flight.snapshot, flight.completion.epoch,
                            flight.plan->requests[flight.index].operationId, std::move(answer), flight.completion.id);
                        if (!ticket) {
                            std::lock_guard<std::mutex> lock(storageStartup_->mutex);
                            if (!storageStartup_->terminal && !storageStartup_->stop && !storageStartup_->queueFailed) return;
                            flight.completion.unknown = true; flight.phase = Phase::retire;
                        } else {
                            flight.waiting = *ticket; flight.phase = Phase::answer;
                            return;
                        }
                    }
                }
            } else if (!newEffects) flight.phase = Phase::retire;
            else {
                const auto observation = localObservation();
                if (!observation.complete || !observation.value) return;
                flight.snapshot = observation.value;
                // Only owning values enter the network thread, never this/UI,
                // a queue pointer or a native storage lease.
                try {
                    std::packaged_task<std::shared_ptr<const ProtectedDeletionResponse>()> task(
                        [config = flight.config, plan = flight.plan, index = flight.index, wire = protectedWire_] {
                            return DesktopHttpTransport::deletionProtected(config, plan->requests[index], index == 0, wire);
                        });
                    auto future = task.get_future();
                    deletionThread_ = std::thread(std::move(task));
                    deletionFuture_ = std::move(future); flight.phase = Phase::network;
                    return;
                } catch (...) { flight.phase = Phase::retire; }
            }
        }
        if (flight.phase == Phase::purge) {
            if (!newEffects || !flight.plan || flight.localIndex == flight.plan->localOnly.size()) flight.phase = Phase::retire;
            else {
                const auto observation = localObservation();
                if (!observation.complete || !observation.value) return;
                const auto& rows = observation.value->items();
                const auto& id = flight.plan->localOnly[flight.localIndex];
                const auto found = std::find_if(rows.begin(), rows.end(), [&](const auto& row) { return row.localRecordingId == id; });
                if (found == rows.end()) { ++flight.localIndex; return; }
                auto deletion = std::allocate_shared<DeletionWork>(CustodyAllocator<DeletionWork>{});
                deletion->snapshot = observation.value;
                deletion->index = static_cast<std::size_t>(found - rows.begin());
                deletion->user = std::string_view(flight.config.confirmedIdentity->userId);
                deletion->workspace = std::string_view(flight.config.workspaceId);
                deletion->cancelled = deletionContinuationCancellation_;
                const auto ticket = submitProtectedDeletion(std::move(deletion), QueueMutationKind::deletionPurge,
                    false, flight.completion.id);
                if (!ticket) return; // Cancellation/drain and allocation refusal preserve the adopted intent.
                flight.waiting = *ticket; flight.phase = Phase::purgeAnswer;
                return;
            }
        }
        if (flight.phase != Phase::retire || deletionThread_.joinable()) return;
        if (!endProtectedDeletionContinuation(flight.completion.id)) return;
        if (current && flight.plan && protectedQueueValue_) {
            for (const auto& id : flight.plan->localOnly) {
                const auto& rows = protectedQueueValue_->items();
                if (std::any_of(rows.begin(), rows.end(), [&](const auto& row) { return row.localRecordingId == id; }))
                    ++flight.completion.pending;
                else ++flight.completion.accepted; // Only actual absence followed by adopted queue removal.
            }
            for (const auto& id : flight.plan->operationIds) {
                const auto& operations = protectedQueueValue_->deletionOperations();
                const auto found = std::find_if(operations.begin(), operations.end(), [&](const auto& op) { return op.operationId == id; });
                if (found != operations.end() && deletionPhaseIsAccepted(found->phase)) ++flight.completion.accepted;
                else if (found != operations.end() && found->phase == DeletionOperationPhase::rejected) ++flight.completion.rejected;
                else ++flight.completion.pending;
            }
        }
        if (!flight.serverPurge) deletionCompletion_ = flight.completion;
        deletionFlight_.reset();
        if (deletionShutdownPending_) shutdown();
    } catch (...) {
        // The retained intent/answer remains owned and can be retried by polling.
    }
    std::uint64_t localPurgeRetryAt_ = 0;
    void resumeProtectedLocalDeletion() try {
        if (backgroundDeletionId_ && deletionCompletion_ && deletionCompletion_->id == backgroundDeletionId_) {
            deletionCompletion_.reset(); backgroundDeletionId_ = 0;
        }
        if (deletionFlight_ || deletionCompletion_ || shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ ||
            !currentAccount_ || authSessionToken_.empty() || !storageStartup_) return;
        const auto observation = localObservation();
        if (!observation.complete || !observation.value) return;
        std::uint64_t generation = 0;
        { std::lock_guard<std::mutex> lock(storageStartup_->mutex); generation = storageStartup_->generation; }
        if (protectedPurgeAttemptGeneration_ == generation) return;
        for (std::size_t index = 0; index != observation.value->items().size(); ++index) {
            if (!observation.value->canLocalRemoval(index, currentAccount_->userId, currentAccount_->workspaceId, true)) continue;
            const auto ticket = requestProtectedLocalRemoval(observation.value,
                observation.value->items()[index].localRecordingId, authGeneration_, true);
            if (ticket) { backgroundDeletionId_ = ticket->id; protectedPurgeAttemptGeneration_ = generation; }
            return;
        }
    } catch (...) {} // A refused charged allocation leaves the durable intent eligible.
    [[nodiscard]] std::optional<QueueMutationTicket> submitProtectedDeletion(std::shared_ptr<DeletionWork> deletion,
        QueueMutationKind kind, bool reserve = false, std::uint64_t continuationId = 0) {
        auto cancellation = reserve ? std::allocate_shared<std::atomic<bool>>(CustodyAllocator<std::atomic<bool>>{}, false) : nullptr;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        auto& work = *storageStartup_;
        if (deletionContinuationId_ != continuationId || (reserve && kind != QueueMutationKind::deletionIntent)) return std::nullopt;
        if ((kind == QueueMutationKind::deletionIntent || kind == QueueMutationKind::deletionPurge) && work.recoveryCancellation) {
            work.recoveryCancellation->store(true);
            work.wake.notify_all();
        }
        if (kind == QueueMutationKind::deletionPurge) {
            if (work.display) work.display->cancelled->store(true);
            if (work.playback) work.playback->cancelled->store(true);
            work.wake.notify_all();
            if (work.recoveryCancellation || (work.display && !work.display->done.load(std::memory_order_acquire)) ||
                (work.playback && !work.playback->terminal)) return std::nullopt;
        }
        if (!work.adopted || !work.startupValue || work.stop || work.terminal || work.queueFailed ||
            work.reconciliationPending || work.error != CustodyFileError::none || work.inFlight || work.recording || work.upload ||
            scheduler_.busy() || work.nextTicket == (std::numeric_limits<std::uint64_t>::max)()) return std::nullopt;
        work.deletion = std::move(deletion);
        work.ticket = {};
        auto& ticket = work.ticket;
        ticket.id = ++work.nextTicket; ticket.epoch = authGeneration_; ticket.kind = kind;
        if (reserve) {
            deletionContinuationId_ = ticket.id; deletionContinuationEpoch_ = ticket.epoch;
            deletionContinuationCancellation_ = std::move(cancellation);
        }
        ticket.context = work.context; ticket.baseGeneration = ticket.targetGeneration = work.generation;
        lastQueueTicket_ = ticket;
        if (kind == QueueMutationKind::lifecycleResult) lastLifecycleTicket_ = ticket;
        else lastDeletionTicket_ = ticket;
        if (kind == QueueMutationKind::deletionIntent) lastDeletionPlan_.reset();
        work.command = kind == QueueMutationKind::deletionIntent ? StorageCommand::deletionIntent :
            kind == QueueMutationKind::deletionPurge ? StorageCommand::deletionPurge :
            kind == QueueMutationKind::lifecycleResult ? StorageCommand::lifecycleResult : StorageCommand::deletionResult;
        work.commandReady = work.inFlight = true;
        work.wake.notify_all();
        return ticket;
    }
public:
    [[nodiscard]] bool localQueueComplete() const noexcept {
        if (!storageStartup_) return false;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        // Clean teardown closes Record, not accepted queue truth used by the
        // update caller together with its independent native-drain check.
        return protectedQueueComplete(*storageStartup_);
    }
    [[nodiscard]] graf::windows::LocalProblemContext localProblemContext() const {
        if (!currentAccount_) return {};
        return {graf::windows::DesktopHttpConfig{}.baseOrigin, currentAccount_->userId, currentAccount_->workspaceId};
    }
    [[nodiscard]] bool ownsRecordingSession(const graf::windows::LocalProblemContext& context,
                                           std::string_view id) const {
        const auto current = localProblemContext();
        if (id.empty() || current.owner.empty() || current.workspace.empty() ||
            context.origin != current.origin || context.owner != current.owner || context.workspace != current.workspace) return false;
        bool found = false;
        const auto observation = localObservation();
        if (observation.value && observation.complete) for (const auto& item : observation.value->items()) {
            if (std::string_view(item.sessionId) != id) continue;
            if (item.localRecordingId.empty() || std::string_view(item.ownerUserId) != context.owner ||
                std::string_view(item.ownerWorkspaceId) != context.workspace) return false;
            found = true;
        }
        if (id == sessionId_ && recordingAccount_) {
            if (recordingOrigin_ != context.origin || recordingAccount_->userId != context.owner ||
                recordingAccount_->workspaceId != context.workspace) return false;
            found = true;
        }
        return found;
    }
    [[nodiscard]] graf::windows::CustodyVector<graf::windows::ProtectedLocalProblemProjection> recordingProblems(std::uint64_t nowMs) const {
        const auto context = localProblemContext();
        // The queue's origin is confirmed by its current native account, never
        // copied from a notification target or used to adopt an unowned row.
        graf::windows::LocalProblemContext queueContext;
        if (currentAccount_) queueContext = {graf::windows::DesktopHttpConfig{}.baseOrigin,
            currentAccount_->userId, currentAccount_->workspaceId};
        std::optional<graf::windows::CurrentCaptureProblem> capture;
        if (recordingAccount_) {
            const auto& state = indicator();
            using State = graf::windows::SessionState;
            const bool deliberateShort = controller_->finalization().shortRecordingDiscarded &&
                state.state == State::blocked && state.reason == graf::windows::ReasonCode::none;
            const bool blocker = !deliberateShort && (state.state == State::failed || state.state == State::degraded ||
                (state.state == State::blocked && state.reason != graf::windows::ReasonCode::none) ||
                (state.state == State::stopping && state.reason == graf::windows::ReasonCode::finalizationFailed));
            capture = graf::windows::CurrentCaptureProblem{sessionId_,
                {recordingOrigin_, recordingAccount_->userId, recordingAccount_->workspaceId}, blocker};
        }
        const auto observation = localObservation();
        const graf::windows::CustodyVector<graf::windows::ProtectedUploadQueueValue::Item> noRows;
        auto problems = graf::windows::projectProtectedLocalRecordingProblems(context, queueContext,
            observation.value ? observation.value->items() : noRows, observation.complete, capture, nowMs);
        const auto active = activeRecordingSession();
        problems.erase(std::remove_if(problems.begin(), problems.end(), [&](const auto& problem) {
            return !active.empty() && std::string_view(problem.sessionId) == active &&
                !(capture && capture->blocker && capture->sessionId == active);
        }), problems.end());
        return problems;
    }
    [[nodiscard]] const auto& custodyRoot() const noexcept { return custodyRoot_; }
    [[nodiscard]] bool uploadsBusy() const noexcept { return scheduler_.busy(); }
    void setUpdateAdmissionBlocked(bool blocked) noexcept {
        updateAdmissionBlocked_ = blocked;
        if (blocked) {
            cancelRecordingLifecycle();
            cancelUnstartedRecording();
            if (controller_ && indicator().visible) {
                try { (void)controller_->stop(RecordingStopReason::interruption); } catch (...) {}
            }
            if (deletionContinuationCancellation_) deletionContinuationCancellation_->store(true);
            if (!deletionContinuationId_) stopStorageStartup();
        }
    }
    [[nodiscard]] bool updateAdmissionBlocked() const noexcept { return updateAdmissionBlocked_; }
    [[nodiscard]] bool updateWorkDrained() const noexcept {
        if (deletionContinuationId_ || lifecycleFlight_ || lifecycleThread_.joinable()) return false;
        if (storageStartup_) {
            std::lock_guard<std::mutex> lock(storageStartup_->mutex);
            if (updateAdmissionBlocked_ && (!storageStartup_->terminal ||
                (storageThread_ && WaitForSingleObject(storageThread_.get(), 0) != WAIT_OBJECT_0))) return false;
            if (!storageStartup_->terminal && !storageStartup_->adopted) return false;
            if (!storageStartup_->terminal && storageStartup_->inFlight) return false;
            if (storageStartup_->playback && !storageStartup_->playback->terminal) return false;
        }
        return !graf::windows::isCaptureState(indicator().state) && !scheduler_.busy() &&
            !protectedRecordingPending() && synchronousMutations_ == 0;
    }
    [[nodiscard]] bool shutdownWorkDrained() const noexcept {
        if (!shuttingDown_ || !updateWorkDrained() || accountFuture_.valid()) return false;
        if (storageStartup_) {
            std::lock_guard<std::mutex> lock(storageStartup_->mutex);
            if (!storageStartup_->terminal || !storageThread_ ||
                WaitForSingleObject(storageThread_.get(), 0) != WAIT_OBJECT_0) return false;
        }
        return true;
    }
    // The shell asks before its ordinary recovery tick: a server-requested pause
    // must not be cut short by the cadence that normally drives retries.
    [[nodiscard]] std::uint64_t uploadDeferralRemainingMs() const noexcept {
        return scheduler_.deferralRemainingMs();
    }
    // Read-only legacy inspection, never protected deletion authority.
    [[nodiscard]] const graf::windows::DesktopUploadQueueService& deletionLedger() const noexcept { return queue_; }

    [[nodiscard]] std::wstring custodySummary() const {
        const auto observation = localObservation();
        if (!observation.value) return L"Защищённое локальное хранилище недоступно. Записи не изменены.";
        if (!observation.complete) return L"Проверяем состояние локальных записей. Записи не изменены.";
        std::size_t pending = 0;
        std::size_t needsAuth = 0;
        std::size_t uploaded = 0;
        std::size_t damaged = 0;
        std::size_t blocked = 0;
        const auto active = activeRecordingSession();
        for (const auto& item : observation.value->items()) {
            if (!active.empty() && std::string_view(item.sessionId) == active) continue;
            switch (item.status) {
            case graf::windows::UploadQueueStatus::pending:
            case graf::windows::UploadQueueStatus::retry:
            case graf::windows::UploadQueueStatus::uploading:
                ++pending;
                break;
            case graf::windows::UploadQueueStatus::needsAuth:
                ++needsAuth;
                break;
            case graf::windows::UploadQueueStatus::uploaded:
                ++uploaded;
                break;
            case graf::windows::UploadQueueStatus::quarantined:
                ++damaged;
                break;
            case graf::windows::UploadQueueStatus::blocked:
                ++blocked;
                break;
            }
        }
        if (damaged != 0) return L"Требуют проверки: " + std::to_wstring(damaged) + L". Локальные записи не отправлены.";
        if (blocked != 0) return L"Отправка приостановлена сервером: " + std::to_wstring(blocked) + L". Автоматические попытки остановлены.";
        if (needsAuth != 0) return L"Нужен вход — локальные записи ждут отправки";
        if (pending != 0 && authSessionToken_.empty()) return L"Локальные записи ждут входа в аккаунт.";
        if (pending != 0 && !currentAccount_) return L"Не удалось подтвердить аккаунт для отправки. Записи остаются на компьютере.";
        if (pending != 0) return L"В очереди: " + std::to_wstring(pending) +
            (scheduler_.busy() ? L" · проверяем отправку" : L" · сохранены на компьютере");
        if (uploaded != 0) return L"Все локальные записи отправлены";
        return L"Локальная очередь пуста";
    }

    [[nodiscard]] std::size_t custodyAttentionCount() const {
        const auto observation = localObservation();
        if (!observation.value || !observation.complete) return 1;
        std::size_t count = 0;
        const auto active = activeRecordingSession();
        for (const auto& item : observation.value->items()) {
            if (!active.empty() && std::string_view(item.sessionId) == active) continue;
            if (item.status == graf::windows::UploadQueueStatus::needsAuth ||
                item.status == graf::windows::UploadQueueStatus::quarantined) {
                ++count;
            }
        }
        return count;
    }

    [[nodiscard]] std::wstring readinessSummary() const {
        const auto inputs = readiness();
        if (!inputs.storageWritable) return L"Защищённое локальное хранилище недоступно. Записи не изменены.";
        const auto gate = graf::windows::WindowsReadinessGate::evaluate(inputs);
        if (gate.recordingReady) return L"Микрофон и системный звук готовы";
        for (std::size_t index = 0; index < gate.blockerCount; ++index) {
            switch (gate.blockers[index]) {
            case graf::windows::ReasonCode::microphonePermissionDenied: return L"Разрешите доступ к микрофону в настройках Windows";
            case graf::windows::ReasonCode::microphoneEndpointUnavailable: return L"Микрофон не найден или недоступен";
            case graf::windows::ReasonCode::renderEndpointUnavailable: return L"Устройство вывода не найдено";
            case graf::windows::ReasonCode::formatNormalizationUnavailable: return L"Формат устройства пока не поддерживается";
            case graf::windows::ReasonCode::aecUnavailable: return L"Обработка эха ещё не установлена";
            case graf::windows::ReasonCode::storageUnavailable: return L"Нет доступа к локальному хранилищу";
            case graf::windows::ReasonCode::aacEncoderUnavailable: return L"Недоступен кодировщик AAC. Для Windows N установите Media Feature Pack и перезапустите GRAF.";
            default: break;
            }
        }
        return L"Проверяем готовность записи";
    }

private:
    static bool recoveryRowCurrent(const ProtectedUploadQueueValue& value, const ProtectedUploadQueueValue::Item& expected,
        bool unowned = false) {
        if (unowned ? !isPreparedUnownedRecording(expected) : !isPreparedOwnedRecording(expected)) return false;
        const auto found = std::find_if(value.items().begin(), value.items().end(), [&](const auto& row) {
            return sameUploadIdentity(row, expected) && row.safeReason == expected.safeReason &&
                row.updatedAtMs == expected.updatedAtMs && !hasUploadServerIdentity(row);
        });
        return found != value.items().end() && !recordingReservationConflict(value,
            std::filesystem::u8path(expected.packageDirectory.begin(), expected.packageDirectory.end()), &*found);
    }
    static bool playbackRowCurrent(const ProtectedUploadQueueValue& value, const ProtectedUploadQueueValue::Item& expected) {
        const auto found = std::find_if(value.items().begin(), value.items().end(), [&](const auto& row) {
            return row.localRecordingId == expected.localRecordingId && row.directoryId == expected.directoryId &&
                row.sessionId == expected.sessionId && row.packageDirectory == expected.packageDirectory &&
                row.ownerUserId == expected.ownerUserId && row.ownerWorkspaceId == expected.ownerWorkspaceId;
        });
        if (found == value.items().end() || !protectedLocalContentAllowed(value, *found,
            std::string_view(expected.ownerUserId), std::string_view(expected.ownerWorkspaceId))) return false;
        if (expected.status == UploadQueueStatus::quarantined || found->status == UploadQueueStatus::quarantined) {
            if (!isPreparedOwnedRecording(expected) || !isPreparedOwnedRecording(*found) ||
                !sameUploadIdentity(*found, expected) || found->updatedAtMs != expected.updatedAtMs) return false;
        }
        return !value.deletionBlocks(*found);
    }
    // Caller holds the storage value mutex. Fresh native validation is still
    // required by the executor before any command that can emit/change audio.
    bool playbackCurrent(const std::shared_ptr<PlaybackWork>& playback) const noexcept try {
        const auto context = localContentContext();
        if (!playback || playback->terminal || playback->cancelled->load() || context.owner.empty() ||
            shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ ||
            storageStartup_->stop || storageStartup_->queueFailed || playback->epoch != authGeneration_ ||
            playback->serial == (std::numeric_limits<std::uint64_t>::max)() || !protectedQueueValue_) return false;
        const auto& row = playback->snapshot->items()[playback->index];
        return std::string_view(row.ownerUserId) == context.owner && std::string_view(row.ownerWorkspaceId) == context.workspace &&
            playbackRowCurrent(*protectedQueueValue_, row);
    } catch (...) { return false; }
    static void runPlayback(const StorageWorkReference& work, const std::shared_ptr<PlaybackExchange>& exchange) noexcept {
        const auto operation = exchange->operation;
        std::shared_ptr<const LocalRecordingPackage::ProtectedInspection> proof;
        std::unique_ptr<ProtectedLocalRecordingPlayback> player;
        try {
            std::unique_lock<std::mutex> lock(work->mutex);
            work->wake.wait(lock, [&] { return exchange->phase == PlaybackExchange::Phase::proofReady || operation->cancelled->load(); });
            const auto pair = exchange->phase == PlaybackExchange::Phase::proofReady ? exchange->pair : nullptr;
            const bool proceed = exchange->proceed && !operation->cancelled->load();
            exchange->phase = PlaybackExchange::Phase::idle;
            lock.unlock();
            if (proceed && pair) {
                auto inspected = LocalRecordingPackage::inspectProtected(work->root, pair,
                    operation->snapshot->items()[operation->index].sessionId, operation->cancelled);
                if (inspected.ok()) proof = std::move(*inspected.value);
            }
            // Each validation belongs to the captured command serial. Pause and
            // cancellation remain responsive even while storage is busy.
            const auto validate = [&](std::uint64_t serial) {
                lock.lock(); exchange->phase = PlaybackExchange::Phase::requestValidation;
                work->wake.notify_all();
                while (exchange->phase != PlaybackExchange::Phase::validationReady && !operation->cancelled->load()) {
                    work->wake.wait_for(lock, std::chrono::milliseconds(20));
                    if (player) {
                        const bool pause = operation->paused;
                        lock.unlock();
                        const auto result = pause ? player->pause() : S_OK;
                        auto media = player->observe();
                        if (FAILED(result) && result != MF_E_NOTACCEPTING && SUCCEEDED(media.error)) media.error = result;
                        lock.lock(); operation->media = media; operation->preparing = !media.ready;
                        if (FAILED(media.error)) { operation->cancelled->store(true); break; }
                    }
                }
                const bool accepted = exchange->phase == PlaybackExchange::Phase::validationReady &&
                    exchange->proceed && !operation->cancelled->load() && operation->serial == serial;
                if (exchange->phase == PlaybackExchange::Phase::validationReady) exchange->phase = PlaybackExchange::Phase::idle;
                lock.unlock(); return accepted;
            };
            if (proof && validate(0)) {
                auto opened = ProtectedLocalRecordingPlayback::open(proof, operation->cancelled, operation->muted);
                if (opened.ok()) player = std::move(*opened.value);
            }
            if (!player) {
                lock.lock(); operation->media.error = E_FAIL; lock.unlock();
            }
            std::uint64_t applied = 0;
            const auto readyDeadline = std::chrono::steady_clock::now() + std::chrono::seconds(20);
            bool becameReady = false;
            while (player && !operation->cancelled->load()) {
                const auto media = player->observe();
                lock.lock(); operation->media = media; operation->preparing = !media.ready;
                if (FAILED(media.error)) { lock.unlock(); break; }
                becameReady = becameReady || media.ready;
                if (!becameReady && std::chrono::steady_clock::now() >= readyDeadline) {
                    operation->media.error = HRESULT_FROM_WIN32(ERROR_TIMEOUT); lock.unlock(); break;
                }
                if (operation->authorized && operation->paused && operation->serial != applied) {
                    const auto pauseSerial = operation->serial;
                    lock.unlock(); const auto pausedResult = player->pause(); lock.lock();
                    if (FAILED(pausedResult) && pausedResult != MF_E_NOTACCEPTING) {
                        operation->media.error = pausedResult; lock.unlock(); break;
                    }
                    if (SUCCEEDED(pausedResult) && operation->serial == pauseSerial && !operation->seek) applied = pauseSerial;
                }
                if (!operation->authorized || !media.ready || media.seeking || operation->serial == applied) {
                    work->wake.wait_for(lock, std::chrono::milliseconds(20)); lock.unlock(); continue;
                }
                const auto serial = operation->serial;
                const auto paused = operation->paused;
                const auto seek = operation->seek;
                lock.unlock();
                HRESULT result = S_OK;
                if (seek || !paused) {
                    if (!validate(serial)) continue;
                    // Freeze this command only after its ACK. A later UI command
                    // increments serial and is handled on the next worker tick.
                    lock.lock();
                    if (operation->cancelled->load() || operation->serial != serial) { lock.unlock(); continue; }
                    lock.unlock();
                    if (seek) result = player->seek(*seek);
                    else if (!paused) result = player->play();
                }
                lock.lock();
                if (FAILED(result) && result != MF_E_NOTACCEPTING) { operation->media.error = result; lock.unlock(); break; }
                if (SUCCEEDED(result) && operation->serial == serial) {
                    operation->seek.reset();
                    if (!seek || paused) applied = serial; // Resume only after asynchronous seek has settled.
                }
                if (result == MF_E_NOTACCEPTING) work->wake.wait_for(lock, std::chrono::milliseconds(20));
                lock.unlock();
            }
        } catch (...) {
            std::lock_guard<std::mutex> lock(work->mutex); operation->media.error = E_FAIL;
        }
        operation->cancelled->store(true);
        if (player) while (!player->startClose()) Sleep(2); // Actual clone/reader drain, never a timeout grant.
        player.reset(); proof.reset();
        std::lock_guard<std::mutex> lock(work->mutex);
        operation->preparing = false; operation->executorDone = true;
        work->wake.notify_all(); // Storage still must release exchange->pair before terminal.
    }
    std::optional<QueueMutationTicket> requestProtectedUpload(
        std::shared_ptr<const ProtectedUploadQueueValue> snapshot = {},
        std::optional<std::size_t> manualIndex = std::nullopt, bool confirmUnowned = false) try {
        if (deletionContinuationId_) return std::nullopt;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        if (storageStartup_->upload && storageStartup_->reconciliationPending) {
            storageStartup_->reconcileRequested = true;
            pendingRecovery_.reset();
            storageStartup_->wake.notify_all();
            return std::nullopt; // Existing recovery intent retries physical validation, never HTTP.
        }
        if (pendingAuthenticatedContext_ || restrictiveLifecyclePending()) return std::nullopt;
        if (!currentAccount_ || !storageStartup_->adopted || storageStartup_->stop || storageStartup_->queueFailed ||
            storageStartup_->inFlight || storageStartup_->recoveryCancellation || storageStartup_->upload || storageStartup_->recording || scheduler_.busy() ||
            (manualIndex && snapshot != protectedQueueValue_) || (!manualIndex && !pendingRecovery_) ||
            storageStartup_->nextTicket == (std::numeric_limits<std::uint64_t>::max)()) return std::nullopt;
        if (storageStartup_->display && !storageStartup_->display->done.load(std::memory_order_acquire)) {
            storageStartup_->display->cancelled->store(true);
            storageStartup_->wake.notify_all();
            return std::nullopt; // Keep recovery intent until the shared inspection slot actually drains.
        }
        ProtectedDesktopHttpConfig config;
        config.sessionToken.assign(authSessionToken_.begin(), authSessionToken_.end());
        config.workspaceId.assign(currentAccount_->workspaceId.begin(), currentAccount_->workspaceId.end());
        config.confirmedIdentity.emplace();
        config.confirmedIdentity->userId.assign(currentAccount_->userId.begin(), currentAccount_->userId.end());
        config.confirmedIdentity->workspaceId = config.workspaceId;
        auto flight = scheduler_.beginProtected(manualIndex ? RecoveryTrigger::scheduled : *pendingRecovery_, std::move(config), authGeneration_);
        if (!flight) return std::nullopt;
        flight->snapshot = std::move(snapshot); flight->manualIndex = manualIndex; flight->confirmUnowned = confirmUnowned;
        storageStartup_->upload = std::move(flight);
        storageStartup_->ticket = {};
        auto& ticket = storageStartup_->ticket;
        ticket.kind = manualIndex ? QueueMutationKind::manualSend : QueueMutationKind::uploadPrepare;
        ticket.id = ++storageStartup_->nextTicket; ticket.epoch = authGeneration_;
        ticket.context = storageStartup_->context; ticket.baseGeneration = storageStartup_->generation;
        ticket.targetGeneration = ticket.baseGeneration;
        lastQueueTicket_ = ticket;
        if (manualIndex) lastManualSendTicket_ = ticket;
        storageStartup_->command = StorageCommand::prepareUpload;
        storageStartup_->commandReady = storageStartup_->inFlight = true;
        protectedRecoveryEpoch_.reset(); pendingRecovery_.reset();
        storageStartup_->wake.notify_all();
        return ticket;
    } catch (...) { return std::nullopt; } // Admission refusal never claims a durable success.

    static void inspectDisplay(const StorageWorkReference& work, const std::shared_ptr<ProtectedNetworkWork>& network) noexcept {
        const auto display = network->display;
        try {
            auto result = std::allocate_shared<ProtectedLocalRecordingTimings>(CustodyAllocator<ProtectedLocalRecordingTimings>{});
            result->snapshot = display->snapshot;
            result->rows.resize(display->snapshot->items().size());
            for (std::size_t index = 0; index != result->rows.size() && !display->cancelled->load(); ++index) {
                const auto& row = display->snapshot->items()[index];
                if (!isPreparedUnownedRecording(row) && (row.ownerUserId != display->user || row.ownerWorkspaceId != display->workspace)) continue;
                std::unique_lock<std::mutex> lock(work->mutex);
                network->index = index;
                network->phase = ProtectedNetworkWork::Phase::requestProof;
                work->wake.notify_all();
                work->wake.wait(lock, [&] { return network->phase == ProtectedNetworkWork::Phase::proofReady; });
                auto pair = std::move(network->pair);
                const bool proceed = network->proceed && !display->cancelled->load();
                lock.unlock();
                std::optional<ProtectedLocalRecordingTiming> timing;
                CustodyContext context{}; std::uint64_t generation = 0;
                if (proceed && pair) {
                    context = pair->current().context; generation = pair->current().generation;
                    auto inspected = LocalRecordingPackage::inspectProtected(work->root, pair, row.sessionId, display->cancelled);
                    if (inspected.error == CustodyFileError::allocationFailed) throw std::bad_alloc{};
                    if (inspected.ok()) {
                        const auto& evidence = (*inspected.value)->evidence();
                        timing = ProtectedLocalRecordingTiming{evidence.durationMs, evidence.startedAtMs, evidence.stoppedAtMs,
                            evidence.displayTimezoneOffsetMinutes, evidence.integrity == PackageIntegrity::degraded &&
                            evidence.playback.decodedFrames != 0 && evidence.playback.containerDuration100ns != 0,
                            isPreparedUnownedRecording(row) && evidence.integrity == PackageIntegrity::valid &&
                            pair->current().phase == CustodyPackagePhase::sealedNormal};
                    }
                }
                pair.reset(); // Inspection/readers/pair all release here before value publication.
                lock.lock();
                network->timing = timing;
                network->packageContext = context; network->packageGeneration = generation;
                network->phase = ProtectedNetworkWork::Phase::resultReady;
                work->wake.notify_all();
                work->wake.wait(lock, [&] { return network->phase == ProtectedNetworkWork::Phase::resultAdopted; });
                if (network->proceed) result->rows[index] = network->timing;
                network->timing.reset(); network->phase = ProtectedNetworkWork::Phase::idle;
            }
            std::lock_guard<std::mutex> lock(work->mutex);
            if (!work->stop && !display->cancelled->load()) display->result = std::move(result);
        } catch (...) { display->cancelled->store(true); }
        {
            std::lock_guard<std::mutex> lock(work->mutex);
            display->done.store(true, std::memory_order_release);
            work->wake.notify_all();
        }
    }
    static void inspectRecovery(const StorageWorkReference& work, const std::shared_ptr<ProtectedNetworkWork>& network) noexcept {
        std::shared_ptr<const LocalRecordingPackage::ProtectedInspection> proof;
        std::unique_lock<std::mutex> lock(work->mutex);
        network->phase = ProtectedNetworkWork::Phase::requestProof;
        work->wake.notify_all();
        work->wake.wait(lock, [&] { return network->phase == ProtectedNetworkWork::Phase::proofReady; });
        auto pair = std::move(network->pair);
        auto writer = std::move(network->recoveryWriter);
        const bool proceed = network->proceed && !network->recoveryCancellation->load();
        network->phase = ProtectedNetworkWork::Phase::idle;
        lock.unlock();
        if (proceed) try {
            if (writer) {
                // No normal proof or queue promotion, even on a verified degraded result.
                const auto finished = V5LocalRecordingWriter::finishRecovery(std::move(writer));
#ifdef GRAF_WINDOWS_TEST_COLD_RECOVERY
                GRAF_WINDOWS_TEST_COLD_RECOVERY(1, finished.error, finished.nativeError);
#endif
                (void)finished;
            } else {
                auto inspected = LocalRecordingPackage::inspectProtected(work->root, std::move(pair),
                    network->recoverySnapshot->items()[network->index].sessionId, network->recoveryCancellation);
                if (inspected.ok()) proof = std::move(*inspected.value);
            }
        } catch (...) {} // Preserve the original reservation on refusal, never infer a normal package.
        pair.reset();
        writer.reset(); // Includes cancelled/refused acquisition; no native field survives resultReady.
        lock.lock();
        network->recoveryProof = std::move(proof);
        network->phase = ProtectedNetworkWork::Phase::resultReady;
#ifdef GRAF_WINDOWS_TEST_RECOVERY_READY
        GRAF_WINDOWS_TEST_RECOVERY_READY(); // Observation only; no proof or native references leave this executor.
#endif
        work->wake.notify_all();
        work->wake.wait(lock, [&] { return network->phase == ProtectedNetworkWork::Phase::resultAdopted; });
        proof = std::move(network->recoveryProof);
        lock.unlock(); proof.reset(); lock.lock(); // Last readers/native release on this executor before owner reconciliation.
        network->recoveryDone = true;
        work->wake.notify_all();
    }
    static bool protectedUploadStep(const StorageWorkReference& work,
        const std::shared_ptr<ProtectedNetworkWork>& network, std::size_t index) {
        const auto flight = network->flight;
        std::unique_lock<std::mutex> lock(work->mutex);
        network->index = index; network->phase = ProtectedNetworkWork::Phase::requestProof;
#ifdef GRAF_WINDOWS_TEST_UPLOAD_STAGE
        GRAF_WINDOWS_TEST_UPLOAD_STAGE(0, 0, 0);
#endif
        work->wake.notify_all();
        work->wake.wait(lock, [&] { return network->phase == ProtectedNetworkWork::Phase::proofReady; });
#ifdef GRAF_WINDOWS_TEST_UPLOAD_STAGE
        GRAF_WINDOWS_TEST_UPLOAD_STAGE(1, 0, 0);
#endif
        auto pair = std::move(network->pair);
        auto result = std::move(network->result);
        const bool admitted = network->proceed && !flight->cancelled->load();
        network->phase = ProtectedNetworkWork::Phase::idle;
        lock.unlock();
        if (!admitted) { pair.reset(); return false; }
        std::shared_ptr<const LocalRecordingPackage::ProtectedInspection> proof;
        try {
            if (!result) {
                // Full content/hash/AAC inspection shares the existing network
                // executor, leaving storage available for prepare/finalize.
#ifdef GRAF_WINDOWS_TEST_UPLOAD_STAGE
                GRAF_WINDOWS_TEST_UPLOAD_STAGE(2, 0, 0);
#endif
                auto inspected = LocalRecordingPackage::inspectProtected(work->root, std::move(pair),
                    std::string_view(flight->snapshot->items()[flight->selected[index]].sessionId), flight->cancelled);
#ifdef GRAF_WINDOWS_TEST_UPLOAD_STAGE
                GRAF_WINDOWS_TEST_UPLOAD_STAGE(3, inspected.error, inspected.nativeError);
#endif
                if (inspected.ok()) proof = std::move(*inspected.value);
                else if (inspected.error == CustodyFileError::invalidContent ||
                         inspected.error == CustodyFileError::identityMismatch) {
                    auto rejected = std::allocate_shared<ProtectedDesktopTransportResult>(CustodyAllocator<ProtectedDesktopTransportResult>{});
                    rejected->status = DesktopTransportStatus::invalidPackage;
                    result = std::move(rejected);
                } else result = flight->fallback; // Quota/key/IO/cancel is not proven corruption.
            }
            if (!result) {
#ifdef GRAF_WINDOWS_TEST_UPLOAD_STAGE
                GRAF_WINDOWS_TEST_UPLOAD_STAGE(4, 0, 0);
#endif
                result = DesktopHttpTransport::uploadProtected(flight->config,
                    flight->snapshot->items()[flight->selected[index]], std::move(proof), work->uploadWire);
#ifdef GRAF_WINDOWS_TEST_UPLOAD_STAGE
                GRAF_WINDOWS_TEST_UPLOAD_STAGE(5, result ? static_cast<unsigned>(result->status) : 0U, !!result);
#endif
            }
        } catch (...) { result = flight->fallback; }
#ifdef GRAF_WINDOWS_TEST_UPLOAD_STAGE
        GRAF_WINDOWS_TEST_UPLOAD_STAGE(6, 0, 0);
#endif
        pair.reset();
        proof.reset(); // Last inspection/native release never belongs to UI.
#ifdef GRAF_WINDOWS_TEST_UPLOAD_STAGE
        GRAF_WINDOWS_TEST_UPLOAD_STAGE(7, 0, 0);
#endif
        if (!result) result = flight->fallback;
        lock.lock();
        network->result = std::move(result); network->phase = ProtectedNetworkWork::Phase::resultReady;
        work->wake.notify_all();
        work->wake.wait(lock, [&] { return network->phase == ProtectedNetworkWork::Phase::resultAdopted; });
        const bool next = network->proceed && !flight->cancelled->load() &&
            !network->result->retryAfterSeconds && network->result->status != DesktopTransportStatus::authRequired;
        if (network->proceed) network->result.reset(); // Failed commit retains the result through physical reconciliation.
        return next;
    }

    [[nodiscard]] bool protectedRecordingPrepared() const {
        if (!recordingWork_) return false;
        std::lock_guard<std::mutex> lock(recordingWork_->mutex);
        return recordingWork_->prepared && !recordingWork_->terminal && !recordingWork_->finalizing;
    }
    [[nodiscard]] std::uint64_t protectedRecordingFrames() const noexcept {
        return recordingWork_ ? recordingWork_->frames.load() : 0;
    }
    [[nodiscard]] std::uint64_t protectedRecordingProcessedFrames() const {
        if (!recordingWork_) return 0;
        std::lock_guard<std::mutex> lock(recordingWork_->mutex);
        return recordingWork_->processedFrames;
    }
    [[nodiscard]] bool protectedRecordingPending() const {
        if (!recordingWork_) return false;
        std::lock_guard<std::mutex> lock(recordingWork_->mutex);
        return !recordingWork_->terminal;
    }
    [[nodiscard]] bool requestProtectedRecording() {
        if (!storageStartup_ || shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ ||
            deletionContinuationId_ || protectedRecordingPending()) return false;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        if (!protectedQueueComplete(*storageStartup_) || storageStartup_->stop || storageStartup_->terminal ||
            storageStartup_->cancellation->load() ||
            storageStartup_->nextTicket == (std::numeric_limits<std::uint64_t>::max)()) return false;
        try {
            auto recording = std::allocate_shared<RecordingWork>(CustodyAllocator<RecordingWork>{});
            recording->processor = aecSelection_.processor;
            recording->timeline = timeline_;
            recording->activeLease = controller_->session().activeLease_;
            recording->session.assign(sessionId_.begin(), sessionId_.end());
            recording->epoch = authGeneration_;
            recording->ownerKnown = currentAccount_.has_value() || authSignedOutObserved_;
            if (currentAccount_) {
                recording->user.assign(currentAccount_->userId.begin(), currentAccount_->userId.end());
                recording->workspace.assign(currentAccount_->workspaceId.begin(), currentAccount_->workspaceId.end());
            }
            storageStartup_->recording = recording;
            recordingWork_ = std::move(recording);
            storageStartup_->ticket = {};
            auto& ticket = storageStartup_->ticket;
            ticket.id = ++storageStartup_->nextTicket;
            ticket.kind = QueueMutationKind::recording;
            ticket.epoch = recordingWork_->epoch;
            ticket.context = storageStartup_->context;
            ticket.baseGeneration = ticket.targetGeneration = storageStartup_->generation;
            lastQueueTicket_ = ticket;
            storageStartup_->command = StorageCommand::prepareRecording;
            storageStartup_->commandReady = storageStartup_->inFlight = true;
            storageStartup_->wake.notify_all();
            return true;
        } catch (...) { return false; } // No synchronous factory/IO fallback.
    }
    [[nodiscard]] TransitionResult beginProtectedRecording(const ReadinessInputs& hardware,
        WindowsCaptureSessionController::StartGuard guard = {}) {
        if (shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ ||
            pendingStartReadiness_ || protectedRecordingPending() || indicator().visible)
            return {TransitionStatus::rejected, indicator().state, ReasonCode::storageUnavailable};
        const auto reserved = controller_->prepareRecording(nullptr, std::move(guard));
        if (!reserved.accepted()) return reserved;
        pendingStartReadiness_ = hardware; // Device prerequisites only; never storage authority.
        if (!requestProtectedRecording()) {
            pendingStartReadiness_.reset();
            return controller_->stop(RecordingStopReason::interruption);
        }
        return reserved;
    }
    [[nodiscard]] TransitionResult startPreparedRecording(const ReadinessInputs& source,
        WindowsCaptureSessionController::StartGuard guard = {}) {
        if (!storageStartup_ || !recordingWork_ || shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_)
            return {TransitionStatus::rejected, indicator().state, ReasonCode::storageUnavailable};
        {
            std::lock_guard<std::mutex> storageLock(storageStartup_->mutex);
            std::lock_guard<std::mutex> recordingLock(recordingWork_->mutex);
            if (storageStartup_->stop || storageStartup_->queueFailed || storageStartup_->recording != recordingWork_ ||
                !recordingWork_->prepared || recordingWork_->started || recordingWork_->terminal ||
                recordingWork_->finalizing || !recordingWork_->writer || recordingWork_->cancellation->load() ||
                recordingWork_->epoch != authGeneration_ ||
                std::string_view(recordingWork_->session) != sessionId_)
                return {TransitionStatus::rejected, indicator().state, ReasonCode::storageUnavailable};
            recordingWork_->started = true;
        }
        auto readiness = source;
        // Ignore any caller storage flag. The private factory ACK/retained
        // actual writer, not a generated prerequisite, grants this continuation.
        readiness.storageWritable = true;
        const auto epoch = recordingWork_->epoch;
        auto currentGuard = [this, epoch, guard = std::move(guard)](std::string_view id) {
            return !shuttingDown_ && !exitAdmissionBlocked_ && !updateAdmissionBlocked_ && epoch == authGeneration_ &&
                recordingWork_ && id == std::string_view(recordingWork_->session) &&
                !recordingWork_->cancellation->load() && (!guard || guard(id));
        };
        TransitionResult result;
        try {
            if (controller_->awaitingPreparation_) {
                controller_->startGuard_ = std::move(currentGuard);
                result = controller_->launchPreparedRecording(readiness);
            } else result = controller_->record(readiness, std::move(currentGuard));
        }
        catch (...) {
            // A throwing/partial start must still cross the controller's EOS fence.
            result = controller_->stop(RecordingStopReason::interruption);
        }
        {
            std::lock_guard<std::mutex> recordingLock(recordingWork_->mutex);
            recordingWork_->activeLease = controller_->session().activeLease_;
        }
        if (result.state == SessionState::idle || result.state == SessionState::blocked ||
            result.state == SessionState::failed)
            requestProtectedFinalization(result.reason, RecordingStopReason::interruption);
        return result;
    }
    void requestProtectedFinalization(ReasonCode failure, RecordingStopReason stopReason) noexcept {
        if (!storageStartup_ || !recordingWork_) return;
        std::lock_guard<std::mutex> storageLock(storageStartup_->mutex);
        std::lock_guard<std::mutex> recordingLock(recordingWork_->mutex);
        if (recordingWork_->terminal || recordingWork_->finalizing || !recordingWork_->prepared ||
            storageStartup_->inFlight || storageStartup_->nextTicket == (std::numeric_limits<std::uint64_t>::max)()) return;
        recordingWork_->failure = failure;
        recordingWork_->stopReason = stopReason;
        recordingWork_->finalizing = true;
        storageStartup_->ticket = {};
        auto& ticket = storageStartup_->ticket;
        ticket.id = ++storageStartup_->nextTicket;
        ticket.kind = QueueMutationKind::recording;
        ticket.epoch = recordingWork_->epoch;
        ticket.context = storageStartup_->context;
        ticket.baseGeneration = ticket.targetGeneration = storageStartup_->generation;
        lastQueueTicket_ = ticket;
        storageStartup_->command = StorageCommand::finalizeRecording;
        storageStartup_->commandReady = storageStartup_->inFlight = true;
        storageStartup_->wake.notify_all();
    }
    static void cancelUnstartedRecording(StorageStartupWork& work) noexcept {
        if (!work.recording) return;
        std::lock_guard<std::mutex> lock(work.recording->mutex);
        if (!work.recording->started) work.recording->cancellation->store(true);
        work.wake.notify_all();
    }
    void cancelUnstartedRecording() noexcept {
        if (!storageStartup_) return;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        cancelUnstartedRecording(*storageStartup_);
    }
    // Called with the storage value mutex held. Stop may arrive while an upload
    // occupies the command slot; retry this transition after that command drains.
    static void finalizeStoppedRecording(StorageStartupWork& work) {
        if (!work.stop || !work.recording || work.inFlight) return;
        std::lock_guard<std::mutex> recordingLock(work.recording->mutex);
        if (work.recording->started || work.recording->finalizing || !work.recording->writer || !work.recording->prepared) return;
        work.recording->finalizing = true;
        work.ticket = {};
        work.ticket.kind = QueueMutationKind::recording;
        if (work.nextTicket != (std::numeric_limits<std::uint64_t>::max)()) work.ticket.id = ++work.nextTicket;
        work.ticket.epoch = work.recording->epoch;
        work.ticket.context = work.context;
        work.ticket.baseGeneration = work.ticket.targetGeneration = work.generation;
        work.command = StorageCommand::finalizeRecording;
        work.commandReady = work.inFlight = true;
    }
    static unsigned __stdcall runStorageStartup(void* argument) {
        auto* reference = static_cast<StorageWorkReference*>(argument);
        auto work = std::move(*reference);
        CustodyAllocator<StorageWorkReference> allocator;
        std::allocator_traits<decltype(allocator)>::destroy(allocator, reference);
        allocator.deallocate(reference, 1);
        // Native leases never cross into a future/UI completion. The worker
        // retains the actual owner after the value-only ACK, until drain.
        std::shared_ptr<const void> drainingActiveLease;
        std::shared_ptr<ProtectedCustodyStoreOwner> owner;
        std::shared_ptr<const ProtectedUploadQueueValue> value;
        std::shared_ptr<ProtectedNetworkWork> network;
        std::shared_ptr<PlaybackExchange> playbackExchange;
        std::optional<CustodyMetadataCommit> uploadCommit;
        std::optional<CustodyMetadataCommit> commandCommit;
        std::shared_ptr<const ProtectedUploadQueueValue> uploadCandidate;
        std::shared_ptr<const ProtectedUploadQueueValue> commandCandidate;
        std::optional<QueueMutationTicket> uploadTicket;
        CustodyFileError error = CustodyFileError::none;
        std::uint32_t nativeError = 0;
        try {
            auto opened = ProtectedCustodyStoreOwner::open(work->root, work->cancellation);
            error = opened.error; nativeError = opened.nativeError;
            if (opened.ok()) {
                owner = std::move(*opened.value);
                auto projection = owner->readQueueValue(work->cancellation);
                error = projection.error; nativeError = projection.nativeError;
                if (projection.ok()) value = std::move(*projection.value);
                else owner.reset();
            }
        } catch (const std::bad_alloc&) { error = CustodyFileError::allocationFailed; owner.reset(); value.reset(); }
          catch (...) { error = CustodyFileError::ioFailed; owner.reset(); value.reset(); }
        {
            std::lock_guard<std::mutex> lock(work->mutex);
            work->error = error; work->nativeError = nativeError;
            if (owner) {
                work->context = owner->queueContext();
                work->generation = owner->queueGeneration();
                work->startupValue = value;
            }
            work->ready = true;
        }
        if (owner) {
            std::unique_lock<std::mutex> lock(work->mutex);
            work->wake.wait(lock, [&] { return work->adopted || work->stop; });
            const auto restartSnapshot = value;
            std::size_t restartIndex = 0;
            while (true) {
                finalizeStoppedRecording(*work);
                if (network && network->recoverySnapshot) {
                    const bool stopping = work->stop || work->queueFailed || work->commandReconciliation;
                    bool current = false;
                    lock.unlock(); // Shared alias policy normalizes paths: no filesystem IO under the value mutex.
                    if (!stopping) try { current = value && recoveryRowCurrent(*value, network->recoverySnapshot->items()[network->index], network->claimTicket.has_value()); }
                    catch (...) {} // A refused allocation/path check cancels, never grants recovery.
                    lock.lock();
                    if (!current) network->recoveryCancellation->store(true);
                }
                if (work->playback && (work->stop || work->queueFailed || !value ||
                    !playbackRowCurrent(*value, work->playback->snapshot->items()[work->playback->index])))
                    work->playback->cancelled->store(true);
                if (work->display && (work->display->snapshot != value || work->stop || work->queueFailed)) work->display->cancelled->store(true);
                work->wake.wait(lock, [&] {
                    return work->commandReady || (work->stop && !work->commandReconciliation && !work->recording && !work->upload &&
                            (!work->playback || work->playback->terminal) &&
                            (!work->display || work->display->done.load(std::memory_order_acquire)) && !work->recoveryCancellation) ||
                        (!work->stop && !work->queueFailed && !work->inFlight && !work->recording && !work->upload && !network &&
                            restartSnapshot && restartIndex < restartSnapshot->items().size()) ||
                        (network && network->recoverySnapshot && network->recoveryDone) ||
                        (work->playback && !work->playback->started) ||
                        (playbackExchange && (playbackExchange->operation->executorDone ||
                            playbackExchange->phase == PlaybackExchange::Phase::requestProof ||
                            playbackExchange->phase == PlaybackExchange::Phase::requestValidation)) ||
                        (work->display && ((!work->display->started && !work->upload && !network) ||
                            (network && network->display && work->display->done.load(std::memory_order_acquire)))) ||
                        (work->upload && work->upload->done.load(std::memory_order_acquire) && !work->recording &&
                            (!work->reconciliationPending || work->reconcileRequested)) ||
                        (work->commandReconciliation && (!network || (!network->display && !network->recoverySnapshot)) &&
                            (!work->reconciliationPending || work->reconcileRequested)) ||
                        (network && (network->phase == ProtectedNetworkWork::Phase::requestProof ||
                            (network->phase == ProtectedNetworkWork::Phase::resultReady &&
                                (!network->recoverySnapshot || !network->recoveryProof || network->recoveryCancellation->load() ||
                                    (!work->recording && !work->inFlight)))));
                });
                if (network && network->recoverySnapshot && network->recoveryDone) {
                    if (network->claimTicket) {
                        work->retiredManualSend = *network->claimTicket;
                        network->flight->done.store(true, std::memory_order_release);
                        network->flight->leaseReleased.store(true);
                        work->upload.reset(); // Executor has actually released its proof, never a timeout grant.
                    }
                    lock.unlock(); network.reset(); lock.lock();
                    work->recoveryCancellation.reset();
                    work->wake.notify_all();
                    continue;
                }
                if (!work->commandReady && !work->stop && !work->queueFailed && !work->inFlight && !work->recording &&
                    !work->upload && !network && restartSnapshot && restartIndex < restartSnapshot->items().size()) {
                    const auto index = restartIndex++;
                    const auto& row = restartSnapshot->items()[index];
                    if (row.status != UploadQueueStatus::quarantined || row.safeReason != "capture_prepared" ||
                        !DesktopApiClient::accountId(row.ownerUserId) || !DesktopApiClient::accountId(row.ownerWorkspaceId) ||
                        hasUploadServerIdentity(row) || restartSnapshot->deletionBlocks(row)) continue;
                    try {
                        network = std::allocate_shared<ProtectedNetworkWork>(CustodyAllocator<ProtectedNetworkWork>{});
                        network->recoverySnapshot = restartSnapshot; network->index = index;
                        network->recoveryCancellation = std::allocate_shared<std::atomic<bool>>(CustodyAllocator<std::atomic<bool>>{}, false);
                        std::thread([work, network] { inspectRecovery(work, network); }).detach();
                        work->recoveryCancellation = network->recoveryCancellation;
                    } catch (...) { network.reset(); }
                    continue;
                }
                if (playbackExchange && playbackExchange->operation->executorDone) {
                    const auto operation = playbackExchange->operation;
                    lock.unlock(); playbackExchange->pair.reset(); playbackExchange.reset(); lock.lock();
                    operation->terminal = true; work->wake.notify_all();
                    continue;
                }
                const bool networkPending = (network && (network->phase == ProtectedNetworkWork::Phase::requestProof ||
                    (network->phase == ProtectedNetworkWork::Phase::resultReady &&
                        (!network->recoverySnapshot || !network->recoveryProof || network->recoveryCancellation->load() ||
                            (!work->recording && !work->inFlight))) ||
                    (network->display && network->display->done.load(std::memory_order_acquire)))) ||
                    (work->upload && work->upload->done.load(std::memory_order_acquire) && !work->recording &&
                        (!work->reconciliationPending || work->reconcileRequested));
                if (!work->commandReady && !networkPending && work->playback && !work->playback->started) {
                    const auto operation = work->playback;
                    operation->started = true;
                    if (work->stop || operation->cancelled->load()) {
                        operation->preparing = false; operation->executorDone = operation->terminal = true; continue;
                    }
                    try {
                        playbackExchange = std::allocate_shared<PlaybackExchange>(CustodyAllocator<PlaybackExchange>{});
                        playbackExchange->operation = operation;
                        std::thread([work, exchange = playbackExchange] { runPlayback(work, exchange); }).detach();
                    } catch (...) {
                        playbackExchange.reset(); operation->media.error = E_OUTOFMEMORY;
                        operation->preparing = false; operation->executorDone = operation->terminal = true;
                    }
                    continue;
                }
                // Recording commands/EOS/finalization have priority. Playback
                // owns its own executor and never occupies the upload slot.
                if (!work->commandReady && !networkPending && playbackExchange &&
                    (playbackExchange->phase == PlaybackExchange::Phase::requestProof ||
                     playbackExchange->phase == PlaybackExchange::Phase::requestValidation)) {
                    const auto exchange = playbackExchange;
                    const auto operation = exchange->operation;
                    const bool opening = exchange->phase == PlaybackExchange::Phase::requestProof;
                    const auto& expected = operation->snapshot->items()[operation->index];
                    std::shared_ptr<const ProtectedCustodyPackagePair> openedPair;
                    bool accepted = !work->stop && !work->queueFailed && !operation->cancelled->load() &&
                        (expected.status != UploadQueueStatus::quarantined || !work->recording || work->recording->session != expected.sessionId);
                    lock.unlock();
                    try {
                        if (accepted) {
                            auto current = owner->readQueueValue(operation->cancelled);
                            accepted = current.ok() && playbackRowCurrent(**current.value, expected);
                            if (accepted && expected.status == UploadQueueStatus::quarantined)
                                accepted = recoveryRowCurrent(**current.value, expected);
                        }
                        if (accepted && opening) {
                            auto pair = owner->readPackage(expected.directoryId, operation->cancelled);
                            accepted = pair.ok() && ((*pair.value)->current().phase == CustodyPackagePhase::sealedDegraded ||
                                (expected.status != UploadQueueStatus::quarantined &&
                                 (*pair.value)->current().phase == CustodyPackagePhase::sealedNormal));
                            if (accepted) openedPair = std::move(*pair.value);
                        } else if (accepted) {
                            auto checked = owner->revalidatePackage(exchange->pair, operation->cancelled);
                            accepted = checked.ok() && *checked.value;
                        }
                    } catch (...) { accepted = false; }
                    lock.lock();
                    if (opening) exchange->pair = std::move(openedPair);
                    exchange->proceed = accepted && !work->stop && !work->queueFailed && !operation->cancelled->load();
                    if (!exchange->proceed) operation->cancelled->store(true);
                    exchange->phase = opening ? PlaybackExchange::Phase::proofReady : PlaybackExchange::Phase::validationReady;
                    work->wake.notify_all(); continue;
                }
                if (network && network->display && network->display->done.load(std::memory_order_acquire)) {
                    lock.unlock(); network->pair.reset(); lock.lock();
                    network.reset();
                    continue;
                }
                if (!work->commandReady && !network && work->display && !work->display->started && !work->upload) {
                    auto display = work->display;
                    display->started = true;
                    if (work->stop || display->cancelled->load()) { display->done.store(true, std::memory_order_release); continue; }
                    try {
                        network = std::allocate_shared<ProtectedNetworkWork>(CustodyAllocator<ProtectedNetworkWork>{});
                        network->display = display;
                        std::thread([work, network] { inspectDisplay(work, network); }).detach();
                    } catch (...) {
                        network.reset(); display->cancelled->store(true); display->done.store(true, std::memory_order_release);
                    }
                    continue;
                }
                if (!work->commandReady &&
                    ((work->commandReconciliation && (!network || (!network->display && !network->recoverySnapshot)) &&
                        (!work->reconciliationPending || work->reconcileRequested)) ||
                     (work->upload && work->upload->done.load(std::memory_order_acquire) && !work->recording))) {
                    const bool reconcileCommand = work->commandReconciliation;
                    const auto unresolvedRecording = reconcileCommand ? work->recording : nullptr;
                    const auto flight = work->upload;
                    work->reconcileRequested = false;
                    lock.unlock();
                    // A cancelled display still owns its proof exchange until
                    // executor completion. Its existing handshake retires it
                    // before deletion readback; only a finished upload is here.
                    if (network && !network->display) network->pair.reset();
                    CustodyFileResult<std::shared_ptr<const ProtectedUploadQueueValue>> current;
                    try {
                        if (owner) current = owner->readQueueValue(work->cancellation);
                        if (!current.ok()) {
                            // Failed owners cannot validate a later generation.
                            // Release native references here, retaining all domain
                            // result/candidate/ticket values until fresh adoption.
                            if (reconcileCommand) commandCommit.reset(); else uploadCommit.reset();
                            owner.reset();
                            auto reopened = ProtectedCustodyStoreOwner::open(work->root, work->cancellation);
                            current.error = reopened.error; current.nativeError = reopened.nativeError;
                            if (reopened.ok()) {
                                owner = std::move(*reopened.value);
                                current = owner->readQueueValue(work->cancellation);
                            }
                        }
                        if (current.ok()) {
                            const auto context = owner->queueContext();
                            if (context.storeId != work->context.storeId || context.objectId != work->context.objectId ||
                                context.role != work->context.role) current = {std::nullopt, CustodyFileError::identityMismatch, 0};
                        }
                    }
                    catch (const std::bad_alloc&) { current.error = CustodyFileError::allocationFailed; }
                    catch (...) { current.error = CustodyFileError::ioFailed; }
                    lock.lock();
                    if (!current.ok()) {
                        work->reconciliationPending = work->queueFailed = true;
                        work->error = current.error; work->nativeError = current.nativeError;
                        continue; // One failed attempt sleeps until a new recovery/stop intent.
                    }
                    work->resultValue = *current.value;
                    if (!reconcileCommand && uploadTicket) work->ticket = *uploadTicket;
                    work->readbackGeneration = owner->queueGeneration();
                    work->physicalReadback = work->resultReady = true;
                    work->resultAdopted = false;
                    work->wake.wait(lock, [&] { return work->resultAdopted || work->stop; });
                    value = std::move(*current.value);
                    work->generation = work->readbackGeneration;
                    work->reconciliationPending = work->queueFailed = false;
                    work->error = CustodyFileError::none; work->nativeError = 0;
                    if (!work->stop) {
                        work->resultValue.reset();
                        work->physicalReadback = work->resultReady = work->resultAdopted = false;
                    }
                    lock.unlock();
                    if (reconcileCommand) {
                        commandCommit.reset(); commandCandidate.reset();
                        if (unresolvedRecording) {
                            // Readback accepts disk truth, never resumes a Start
                            // whose original publication had an unknown outcome.
                            std::shared_ptr<V5LocalRecordingWriter> writer;
                            {
                                std::lock_guard<std::mutex> recordingLock(unresolvedRecording->mutex);
                                writer = std::move(unresolvedRecording->writer);
                                unresolvedRecording->timeline.reset(); unresolvedRecording->processor.reset();
                            }
                            writer.reset();
                            std::lock_guard<std::mutex> recordingLock(unresolvedRecording->mutex);
                            drainingActiveLease = std::move(unresolvedRecording->activeLease);
                            unresolvedRecording->result = {false, ReasonCode::storageUnavailable, false};
                            unresolvedRecording->terminal = true;
                        }
                        lock.lock();
                        auto retired = std::move(work->deletion);
                        if (unresolvedRecording) work->recording.reset();
                        work->commandReconciliation = false; work->inFlight = false;
                        const bool stopping = work->stop;
                        lock.unlock(); retired.reset(); if (!stopping) drainingActiveLease.reset(); lock.lock();
                        continue;
                    }
                    uploadCommit.reset(); uploadCandidate.reset(); uploadTicket.reset();
                    if (network) network->result.reset();
                    lock.lock();
                    network.reset(); work->upload.reset();
                    flight->leaseReleased.store(true);
                    continue;
                }
                if (!work->commandReady && network && network->phase == ProtectedNetworkWork::Phase::requestProof) {
                    if (network->recoverySnapshot) {
                        const auto& row = network->recoverySnapshot->items()[network->index];
                        const auto cancellation = network->recoveryCancellation;
                        const bool current = !work->stop && !work->queueFailed && !cancellation->load();
                        lock.unlock();
                        if (current) try {
                            auto queue = owner->readQueueValue(cancellation);
                            if (queue.ok() && recoveryRowCurrent(**queue.value, row, network->claimTicket.has_value()) &&
                                std::string_view(row.packageDirectory) == (work->root / std::string_view(row.directoryId)).u8string()) {
                                auto pair = owner->readPackage(row.directoryId, cancellation);
                                if (pair.ok()) {
                                    const auto phase = (*pair.value)->current().phase;
                                    if (phase == CustodyPackagePhase::sealedNormal) network->pair = std::move(*pair.value);
                                    else if (!network->claimTicket && (phase == CustodyPackagePhase::capturing || phase == CustodyPackagePhase::finalizing)) {
                                        pair.value.reset(); // Retire isolated readonly state lease before writable acquisition.
                                        auto prepared = V5LocalRecordingWriter::prepareRecovery(owner, row.sessionId, cancellation);
#ifdef GRAF_WINDOWS_TEST_COLD_RECOVERY
                                        GRAF_WINDOWS_TEST_COLD_RECOVERY(0, prepared.error, prepared.nativeError);
#endif
                                        if (prepared.ok()) network->recoveryWriter = std::move(*prepared.value);
                                    }
                                }
                            }
                        } catch (...) {}
                        lock.lock();
                        network->proceed = current && !work->stop && !cancellation->load() && (!!network->pair || !!network->recoveryWriter);
                        network->phase = ProtectedNetworkWork::Phase::proofReady;
                        work->wake.notify_all();
                        continue;
                    }
                    if (network->display) {
                        const auto display = network->display;
                        const auto& row = display->snapshot->items()[network->index];
                        network->proceed = false;
                        const bool current = !work->stop && !work->queueFailed && value == display->snapshot && !display->cancelled->load();
                        lock.unlock();
                        try {
                            const bool readable = protectedLocalContentAllowed(*display->snapshot, row,
                                std::string_view(display->user), std::string_view(display->workspace));
                            const bool claimable = isPreparedUnownedRecording(row) && !uploadAccessBlocks(row) &&
                                !display->snapshot->deletionBlocks(row);
                            if (current && (readable || claimable) && (row.status != UploadQueueStatus::quarantined ||
                                recoveryRowCurrent(*display->snapshot, row, isPreparedUnownedRecording(row)))) {
                                auto pair = owner->readPackage(row.directoryId, display->cancelled);
                                if (pair.error == CustodyFileError::allocationFailed) display->cancelled->store(true);
                                if (pair.ok() && ((*pair.value)->current().phase == CustodyPackagePhase::sealedNormal ||
                                    (*pair.value)->current().phase == CustodyPackagePhase::sealedDegraded)) network->pair = std::move(*pair.value);
                            }
                        } catch (...) {} // Unknown display evidence, never a queue corruption mutation.
                        lock.lock();
                        network->proceed = current && !work->stop && !display->cancelled->load() && !!network->pair;
                        network->phase = ProtectedNetworkWork::Phase::proofReady;
                        work->wake.notify_all();
                        continue;
                    }
                    const auto flight = network->flight;
                    const auto& expected = flight->snapshot->items()[flight->selected[network->index]];
                    network->proceed = false;
                    lock.unlock();
                    try {
                        auto current = owner->readQueueValue(flight->cancelled);
                        if (current.ok() && !flight->cancelled->load()) {
                            const auto& rows = (*current.value)->items();
                            const auto found = std::find_if(rows.begin(), rows.end(), [&](const auto& row) { return sameUploadIdentity(row, expected); });
                            if (found != rows.end() && protectedLocalContentAllowed(**current.value, *found,
                                std::string_view(expected.ownerUserId), std::string_view(expected.ownerWorkspaceId))) {
                                auto pair = owner->readPackage(expected.directoryId, flight->cancelled);
                                const bool invalidPackage = pair.ok() && (*pair.value)->current().phase != CustodyPackagePhase::sealedNormal;
                                if (pair.ok() && !invalidPackage) network->pair = std::move(*pair.value);
                                if (!network->pair) {
                                    if (invalidPackage) {
                                        auto rejected = std::allocate_shared<ProtectedDesktopTransportResult>(CustodyAllocator<ProtectedDesktopTransportResult>{});
                                        rejected->status = DesktopTransportStatus::invalidPackage;
                                        network->result = std::move(rejected);
                                    } else network->result = flight->fallback; // Quota/key/IO refusal is not proven corruption.
                                }
                                network->proceed = true;
                            }
                        }
                    } catch (...) { network->result = flight->fallback; network->proceed = !flight->cancelled->load(); }
                    lock.lock();
                    if (work->stop || work->queueFailed || flight->cancelled->load()) network->proceed = false;
                    network->phase = ProtectedNetworkWork::Phase::proofReady;
                    work->wake.notify_all();
                    continue;
                }
                if (!work->commandReady && network && network->phase == ProtectedNetworkWork::Phase::resultReady &&
                    (!network->recoverySnapshot || !network->recoveryProof || network->recoveryCancellation->load() ||
                        (!work->recording && !work->inFlight))) {
                    if (network->recoverySnapshot) {
                        if (network->claimTicket) {
                            if (work->stop || work->queueFailed || !network->recoveryProof || network->recoveryCancellation->load()) {
                                auto& cancelled = *network->claimTicket;
                                cancelled.state = QueueTicketState::notCommitted;
                                cancelled.error = network->recoveryCancellation->load() ? CustodyFileError::ioFailed : CustodyFileError::invalidContent;
                                cancelled.nativeError = network->recoveryCancellation->load() ? ERROR_OPERATION_ABORTED : 0;
                                network->phase = ProtectedNetworkWork::Phase::resultAdopted;
                                work->wake.notify_all(); continue; // Retire independently of another recording's unresolved publication.
                            }
                            work->ticket = *network->claimTicket;
                            work->ticket.context = work->context;
                            work->ticket.baseGeneration = work->ticket.targetGeneration = work->generation;
                            work->command = StorageCommand::prepareUpload;
                            work->commandReady = work->inFlight = true;
                            continue;
                        }
                        if (work->stop || work->queueFailed || !network->recoveryProof || network->recoveryCancellation->load() ||
                            work->nextTicket == (std::numeric_limits<std::uint64_t>::max)()) {
                            network->phase = ProtectedNetworkWork::Phase::resultAdopted; work->wake.notify_all(); continue;
                        }
                        work->ticket = {};
                        auto& resultTicket = work->ticket;
                        resultTicket.kind = QueueMutationKind::recovery;
                        resultTicket.id = ++work->nextTicket;
                        resultTicket.context = work->context;
                        resultTicket.baseGeneration = resultTicket.targetGeneration = work->generation;
                        work->command = StorageCommand::recoverRecording;
                        work->commandReady = work->inFlight = true;
                        continue;
                    }
                    if (network->display) {
                        const auto display = network->display;
                        const bool current = !work->stop && !work->queueFailed && value == display->snapshot && !display->cancelled->load();
                        network->proceed = false;
                        lock.unlock();
                        if (current && network->timing) try {
                            auto pair = owner->readPackage(display->snapshot->items()[network->index].directoryId, display->cancelled);
                            if (pair.error == CustodyFileError::allocationFailed) display->cancelled->store(true);
                            if (pair.ok()) {
                                const auto& actual = (*pair.value)->current();
                                const auto& expected = network->packageContext;
                                network->proceed = actual.context.storeId == expected.storeId && actual.context.objectId == expected.objectId &&
                                    actual.context.role == expected.role && actual.generation == network->packageGeneration;
                            }
                        } catch (...) {}
                        lock.lock();
                        network->proceed = network->proceed && !work->stop && !display->cancelled->load();
                        network->phase = ProtectedNetworkWork::Phase::resultAdopted;
                        work->wake.notify_all();
                        continue;
                    }
                    if (network->flight->cancelled->load()) {
                        // The executor must receive its ACK and actually exit, but
                        // a cancelled answer never allocates/applies a queue command.
                        network->proceed = false;
                        network->phase = ProtectedNetworkWork::Phase::resultAdopted;
                        work->wake.notify_all(); continue;
                    }
                    if (work->nextTicket == (std::numeric_limits<std::uint64_t>::max)()) {
                        work->queueFailed = true; network->proceed = false;
                        network->phase = ProtectedNetworkWork::Phase::resultAdopted; work->wake.notify_all();
                        continue;
                    }
                    work->ticket = {};
                    auto& resultTicket = work->ticket;
                    resultTicket.kind = QueueMutationKind::uploadResult;
                    resultTicket.id = ++work->nextTicket; resultTicket.epoch = network->flight->epoch;
                    resultTicket.context = work->context; resultTicket.baseGeneration = work->generation;
                    resultTicket.targetGeneration = resultTicket.baseGeneration;
                    work->command = StorageCommand::uploadResult;
                    work->commandReady = work->inFlight = true;
                }
                if (!work->commandReady && work->commandReconciliation) continue;
                if (!work->commandReady && work->stop) break;
                if (!work->commandReady) continue; // A deferred inspection/playback wake is never a command admission.
                if (work->command == StorageCommand::prepareUpload && !network && work->upload && work->upload->manualIndex &&
                    isPreparedUnownedRecording(work->upload->snapshot->items()[*work->upload->manualIndex])) {
                    try {
                        network = std::allocate_shared<ProtectedNetworkWork>(CustodyAllocator<ProtectedNetworkWork>{});
                        network->flight = work->upload;
                        network->claimTicket = work->ticket;
                        network->recoverySnapshot = work->upload->snapshot;
                        network->index = *work->upload->manualIndex;
                        network->recoveryCancellation = work->upload->cancelled;
                        std::thread([work, network] { inspectRecovery(work, network); }).detach();
                        work->recoveryCancellation = network->recoveryCancellation;
                        work->commandReady = work->inFlight = false; // Start/Stop/finalize continue while hash/AAC runs elsewhere.
                        continue;
                    } catch (...) {
                        network.reset(); work->upload->cancelled->store(true); // No proof: never fall back to an unverified claim.
                    }
                }
                auto ticket = work->ticket;
                const auto command = work->command;
                auto recording = work->recording;
                auto deletion = work->deletion;
                work->commandReady = false;
                lock.unlock();
                std::shared_ptr<const ProtectedUploadQueueValue> candidate;
                const bool recordingCommand = command == StorageCommand::prepareRecording || command == StorageCommand::finalizeRecording;
                const bool recoveringRecording = command == StorageCommand::recoverRecording;
                const bool uploading = command == StorageCommand::prepareUpload || command == StorageCommand::uploadResult;
                const bool deleting = command == StorageCommand::deletionIntent || command == StorageCommand::deletionResult ||
                    command == StorageCommand::deletionPurge || command == StorageCommand::lifecycleResult;
                auto& commit = uploading ? uploadCommit : commandCommit;
                bool commitReturned = false;
                bool lifecycleRefused = false;
                std::optional<V5WriterResult> recordingResult;
                bool shortRemoved = false;
                try {
                    const auto cancellation = recoveringRecording ? network->recoveryCancellation : recordingCommand ? recording->cancellation :
                        uploading ? work->upload->cancelled : deleting ?
                            deletion->cancelled : work->cancellation;
                    if (command == StorageCommand::finalizeRecording) {
                        // The UI handed off only after actual dispatcher EOS.
                        // The native job/future and its last result stay here.
                        auto finalizer = std::async(std::launch::async, [recording] {
                            auto failure = recording->failure;
                            if (!recording->timeline->close() && failure == ReasonCode::none)
                                failure = ReasonCode::clockDiscontinuity;
                            for (const auto& frame : recording->timeline->takeFrames()) {
                                if (!recording->writer->append(frame)) {
                                    failure = ReasonCode::storageUnavailable;
                                    break;
                                }
                                recording->frames.store(recording->writer->frameCount());
                            }
                            if (!recording->timeline->healthy() && failure == ReasonCode::none)
                                failure = ReasonCode::clockDiscontinuity;
                            const auto result = recording->writer->finalize(failure, recording->stopReason);
                            {
                                std::lock_guard<std::mutex> recordingLock(recording->mutex);
                                recording->processedFrames = recording->timeline->processedFrames();
                            }
                            return result;
                        });
                        const auto result = finalizer.get();
                        recordingResult.emplace(result);
                    }
                    if (recordingResult) {
                        // EOS/finalizer completed. Release every native consumer
                        // before metadata reconciliation can reopen the store;
                        // retain the result/active slot through readback and ACK.
                        std::shared_ptr<V5LocalRecordingWriter> writer;
                        {
                            std::lock_guard<std::mutex> recordingLock(recording->mutex);
                            writer = std::move(recording->writer);
                            recording->timeline.reset(); recording->processor.reset();
                        }
                        writer.reset();
                    }
                    // Revalidate the genuine owner under continuous leases. No
                    // caller path, cached readiness or JSON-derived generation.
                    auto current = owner->readQueueValue(cancellation);
                    ticket.error = current.error; ticket.nativeError = current.nativeError;
                    if (current.ok() && ticket.baseGeneration == owner->queueGeneration() &&
                        ticket.context.storeId == owner->queueContext().storeId &&
                        ticket.context.objectId == owner->queueContext().objectId && ticket.context.role == CustodyRole::queue) {
                        json_detail::checkCancellation(cancellation.get());
                        auto copy = std::allocate_shared<ProtectedUploadQueueValue>(
                            CustodyAllocator<ProtectedUploadQueueValue>{}, **current.value);
                        candidate = copy; // Retain even a failed private mutation until ACK.
                        json_detail::checkCancellation(cancellation.get());
                        const auto now = static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
                            std::chrono::system_clock::now().time_since_epoch()).count());
                        if (command == StorageCommand::prepareRecording) {
                            const auto prepared = owner->prepareRecordingReservation(*copy, recording->session,
                                recording->user, recording->workspace, recording->ownerKnown, now, cancellation);
                            ticket.error = prepared.error; ticket.nativeError = prepared.nativeError;
                            ticket.changed = prepared.ok() && *prepared.value;
                        }
                        else if (command == StorageCommand::recovery) ticket.changed = copy->requeueNeedsAuth(now, cancellation.get());
                        else if (recoveringRecording) {
                            const auto recovered = LocalRecordingPackage::recoverPreparedRecording(*owner, *copy, *network->recoverySnapshot,
                                network->recoverySnapshot->items()[network->index].sessionId, network->recoveryProof, now, cancellation);
                            ticket.error = recovered.error; ticket.nativeError = recovered.nativeError;
                            ticket.changed = recovered.ok() && *recovered.value;
                        }
                        else if (command == StorageCommand::deletionIntent) {
                            const bool prepared = deletion->snapshot == value && (deletion->localIndex ?
                                (deletion->plan && copy->planLocalRemoval(*deletion->localIndex, deletion->user,
                                    deletion->workspace, now, *deletion->plan, ticket.changed, cancellation.get(), deletion->resumeLocalIntent)) :
                                deletion->serverTask ?
                                copy->prepareLocalPurgeTask(*deletion->serverTask, deletion->user, deletion->workspace,
                                    now, ticket.changed, cancellation.get()) :
                                (deletion->plan && copy->planDeletionSelection(deletion->targets, deletion->user, deletion->workspace,
                                    deletion->origin, now, *deletion->plan, ticket.changed, cancellation.get())));
                            if (!prepared)
                                ticket.error = CustodyFileError::conflict;
                        }
                        else if (command == StorageCommand::lifecycleResult) {
                            bool valid = deletion->snapshot == value;
                            if (valid && deletion->authenticatedContext) {
                                const auto& context = *deletion->authenticatedContext;
                                valid = context.actorUserId == deletion->user && context.workspaceId == deletion->workspace &&
                                    context.serverOrigin == deletion->origin;
                                if (valid && (!copy->lastAuthenticatedContext() ||
                                    !sameAuthenticatedContext(*copy->lastAuthenticatedContext(), context))) {
                                    valid = copy->setLastAuthenticatedContext(context, now, cancellation.get());
                                    ticket.changed = valid;
                                }
                            } else if (valid) {
                                valid = deletion->lifecycle && deletion->lifecycle->entries &&
                                    copy->applyLifecycleEntries(deletion->lifecycle->origins, *deletion->lifecycle->entries,
                                        deletion->user, deletion->workspace, deletion->origin, now, ticket.changed, cancellation.get());
                            }
                            if (!valid) { lifecycleRefused = true; ticket.error = CustodyFileError::conflict; }
                        }
                        else if (command == StorageCommand::deletionResult) {
                            if (deletion->snapshot != value || deletion->index >= deletion->snapshot->deletionOperations().size() ||
                                !copy->applyDeletionAnswer(deletion->snapshot->deletionOperations()[deletion->index],
                                    deletion->answer, now, ticket.changed, cancellation.get())) ticket.error = CustodyFileError::conflict;
                        }
                        else if (command == StorageCommand::deletionPurge) {
                            if (deletion->snapshot != value || deletion->index >= value->items().size())
                                ticket.error = CustodyFileError::conflict;
                            else {
                                auto removed = owner->purgeLocalPackage(value->items()[deletion->index].localRecordingId,
                                    ticket.baseGeneration, *copy, now, cancellation,
                                    deletion->serverTask ? &*deletion->serverTask : nullptr, deletion->user, deletion->workspace);
                                ticket.error = removed.error; ticket.nativeError = removed.nativeError;
                                ticket.changed = removed.ok() && *removed.value;
                            }
                        }
                        else if (command == StorageCommand::prepareUpload) {
                            auto& flight = *work->upload;
                            if (flight.manualIndex) {
                                bool prepared = false;
                                if (flight.config.confirmedIdentity && network && network->claimTicket) {
                                    const auto& expected = network->recoverySnapshot->items()[network->index];
                                    const auto claimed = LocalRecordingPackage::recoverPreparedRecording(*owner, *copy,
                                        *network->recoverySnapshot, expected.sessionId, network->recoveryProof, now, cancellation,
                                        flight.config.confirmedIdentity->userId, flight.config.confirmedIdentity->workspaceId);
                                    ticket.error = claimed.error; ticket.nativeError = claimed.nativeError;
                                    prepared = claimed.ok() && *claimed.value;
                                    if (prepared) flight.manualIndex = static_cast<std::size_t>(std::find_if(copy->items().begin(), copy->items().end(),
                                        [&](const auto& row) { return row.localRecordingId == expected.localRecordingId; }) - copy->items().begin());
                                } else if (flight.snapshot == value && flight.config.confirmedIdentity &&
                                    !isPreparedUnownedRecording(copy->items()[*flight.manualIndex])) {
                                    prepared = copy->prepareManualSend(*flight.manualIndex, flight.config.confirmedIdentity->userId,
                                        flight.config.confirmedIdentity->workspaceId, flight.confirmUnowned, now, cancellation.get());
                                }
                                if (!prepared && ticket.error == CustodyFileError::none)
                                    ticket.error = CustodyFileError::conflict;
                                if (prepared) { flight.selected.push_back(*flight.manualIndex); ticket.changed = true; }
                            } else {
                                flight.selected = copy->prepareUploads(flight.trigger == RecoveryTrigger::authRecovered,
                                    flight.maxAttempts, now, cancellation.get());
                                ticket.changed = copy->updatedAtMs() != (*current.value)->updatedAtMs();
                            }
                            flight.snapshot = candidate;
                        } else if (command == StorageCommand::uploadResult) {
                            const auto& expected = network->flight->snapshot->items()[network->flight->selected[network->index]];
                            ticket.changed = copy->applyUploadResult(expected, *network->result, now, cancellation.get());
                            if (!ticket.changed) ticket.error = CustodyFileError::conflict;
                        }
                        else if (recordingResult && recording->reservation) {
                            const auto finished = owner->finishRecordingReservation(*copy, *recording->reservation,
                                recording->session, *recordingResult, now, cancellation);
                            ticket.error = finished.error; ticket.nativeError = finished.nativeError;
                            ticket.changed = finished.ok() && *finished.value;
                        }
                        json_detail::checkCancellation(cancellation.get());
                        if (ticket.error != CustodyFileError::none) {
                            // A failed whole-selection validation may have changed
                            // its private copy. Never serialize/publish that prefix.
                            ticket.changed = false;
                            ticket.targetGeneration = ticket.baseGeneration;
                            ticket.state = QueueTicketState::notCommitted;
                        } else if (!ticket.changed && !(command == StorageCommand::prepareUpload && !work->upload->selected.empty())) {
                            ticket.targetGeneration = ticket.baseGeneration;
                            ticket.state = deleting && ticket.error == CustodyFileError::none ?
                                QueueTicketState::committed : QueueTicketState::notCommitted;
                        } else {
                            auto bytes = copy->serialize(cancellation);
                            ticket.error = bytes.error; ticket.nativeError = bytes.nativeError;
                            if (bytes.ok()) {
                                json_detail::checkCancellation(cancellation.get());
                                auto saved = commitProtectedCustodyMetadata(owner, ticket.context,
                                    ticket.baseGeneration, *bytes.value, cancellation);
                                commitReturned = true;
                                ticket.state = saved.state == CustodyCommitState::committed ? QueueTicketState::committed :
                                    saved.state == CustodyCommitState::ambiguous ? QueueTicketState::ambiguous : QueueTicketState::notCommitted;
                                ticket.error = saved.error; ticket.nativeError = saved.nativeError;
                                ticket.targetGeneration = saved.targetGeneration ? saved.targetGeneration : ticket.baseGeneration;
                                commit.emplace(std::move(saved)); // Retained on this worker until ACK/drain.
                            }
                        }
                    } else if (current.ok()) ticket.error = CustodyFileError::conflict;
                } catch (const json_detail::ParseCancelled&) {
                    ticket.error = CustodyFileError::ioFailed;
                    ticket.nativeError = ERROR_OPERATION_ABORTED;
                } catch (const std::bad_alloc&) {
                    ticket.error = CustodyFileError::allocationFailed;
                    // A throwing native result transfer may follow publication.
                    if (commitReturned) ticket.state = QueueTicketState::ambiguous;
                } catch (...) {
                    ticket.error = CustodyFileError::ioFailed;
                    if (commitReturned) ticket.state = QueueTicketState::ambiguous;
                }
                if (ticket.state == QueueTicketState::pending) ticket.state = QueueTicketState::notCommitted;
                if (command == StorageCommand::deletionIntent && deletion->plan)
                    deletion->plan->saved = ticket.state == QueueTicketState::committed;
                lock.lock();
                work->ticket = ticket;
                work->resultValue = candidate;
                work->resultReady = true;
                work->retryAfterSeconds = command == StorageCommand::uploadResult ? network->result->retryAfterSeconds : 0;
                work->authExpiresAt = command == StorageCommand::uploadResult ? network->result->authExpiresAt : std::nullopt;
                work->queueFailed = (!lifecycleRefused && ticket.error != CustodyFileError::none) || ticket.state == QueueTicketState::ambiguous;
                // Lost UI polling retains candidate and commit. Close/update
                // instead reconciles physical truth here before actual drain.
                work->wake.wait(lock, [&] { return work->resultAdopted || work->stop; });
                const bool adopted = work->resultAdopted;
                const bool allowFactory = adopted && !work->stop;
                if (ticket.state == QueueTicketState::committed) {
                    value = std::move(candidate);
                    work->generation = ticket.targetGeneration;
                }
                const bool reconcileCommand = (deleting || recordingCommand || recoveringRecording) && ticket.state == QueueTicketState::ambiguous;
                if (reconcileCommand) {
                    work->commandReconciliation = true; commandCandidate = candidate;
                } else if (deleting) work->deletion.reset();
                work->inFlight = reconcileCommand || recordingCommand;
                if (!work->stop) {
                    work->resultValue.reset();
                    work->resultReady = work->resultAdopted = false;
                } // Terminal value-only readback survives a late UI poll, without native leases.
                lock.unlock();
                deletion.reset(); // Retire this value only, before/independently of a later command.
                if (recoveringRecording) {
                    lock.lock(); network->phase = ProtectedNetworkWork::Phase::resultAdopted;
                    work->wake.notify_all(); lock.unlock();
                }
                if (command == StorageCommand::prepareUpload && network && network->claimTicket) {
                    lock.lock();
                    network->phase = ProtectedNetworkWork::Phase::resultAdopted;
                    work->wake.notify_all();
                    work->wake.wait(lock, [&] { return network->recoveryDone; });
                    lock.unlock(); network.reset(); lock.lock();
                    work->recoveryCancellation.reset();
                    lock.unlock(); // Full proof/readers are gone before network launch or physical reconciliation.
                }
                if (uploading && (ticket.error != CustodyFileError::none || ticket.state == QueueTicketState::ambiguous)) {
                    uploadCandidate = candidate; uploadTicket = ticket;
                } else if (!reconcileCommand) commit.reset(); // Failed results retain ownership through physical reconciliation.
                if (recordingCommand && reconcileCommand) { lock.lock(); continue; }
                if (command == StorageCommand::prepareRecording) {
                    bool prepared = false;
                    try {
                        if (allowFactory && ticket.state == QueueTicketState::committed && ticket.error == CustodyFileError::none &&
                            !recording->cancellation->load()) {
                            recording->reservation = value;
#ifdef GRAF_WINDOWS_TEST_START_BEFORE_FACTORY
                            GRAF_WINDOWS_TEST_START_BEFORE_FACTORY();
#endif
                            auto opened = V5LocalRecordingWriter::open(owner, recording->session, recording->cancellation);
                            if (opened.ok()) {
                                std::lock_guard<std::mutex> recordingLock(recording->mutex);
                                recording->writer = std::move(*opened.value);
                                recording->context = recording->writer->packageContext();
                                prepared = !recording->cancellation->load();
                            }
                        }
                    } catch (...) {} // Preserve durable reservation/partial birth, never retry the factory.
                    if (!prepared) {
                        std::shared_ptr<V5LocalRecordingWriter> writer;
                        {
                            std::lock_guard<std::mutex> recordingLock(recording->mutex);
                            writer = std::move(recording->writer);
                            recording->timeline.reset(); recording->processor.reset();
                        }
                        writer.reset();
                    }
                    lock.lock();
                    {
                        std::lock_guard<std::mutex> recordingLock(recording->mutex);
                        if (prepared && !work->stop && !recording->cancellation->load()) recording->prepared = true;
                        else {
                            // Native writer may have completed concurrently with Stop.
                            // Retire it outside the value mutex before terminal below.
                            prepared = false;
                        }
                    }
                    if (!prepared) {
                        lock.unlock();
                        std::shared_ptr<V5LocalRecordingWriter> writer;
                        {
                            std::lock_guard<std::mutex> recordingLock(recording->mutex);
                            writer = std::move(recording->writer);
                            recording->timeline.reset(); recording->processor.reset();
                        }
                        writer.reset();
                        {
                            std::lock_guard<std::mutex> recordingLock(recording->mutex);
                            drainingActiveLease = std::move(recording->activeLease);
                            recording->result = {false, ReasonCode::storageUnavailable, false};
                            recording->terminal = true;
                        }
                        lock.lock(); work->recording.reset();
                        if (!work->stop) drainingActiveLease.reset();
                    }
                    work->inFlight = false;
                    continue;
                }
                if (command == StorageCommand::prepareUpload) {
                    const auto flight = work->upload;
                    bool launched = false;
                    if (ticket.state == QueueTicketState::committed && !flight->cancelled->load()) try {
                        network = std::allocate_shared<ProtectedNetworkWork>(CustodyAllocator<ProtectedNetworkWork>{});
                        network->flight = flight;
                        launched = DesktopUploadRecoveryScheduler::launchProtected(flight,
                            [work, network](std::size_t index) { return protectedUploadStep(work, network, index); },
                            [work] { std::lock_guard<std::mutex> completedLock(work->mutex); work->wake.notify_all(); });
                    } catch (...) {}
                    if (!launched) {
                        network.reset();
                        flight->done.store(true, std::memory_order_release);
                        if (ticket.error == CustodyFileError::none && flight->selected.empty()) {
                            lock.lock(); work->upload.reset(); lock.unlock();
                            flight->leaseReleased.store(true);
                        }
                    }
                } else if (command == StorageCommand::uploadResult) {
                    lock.lock();
                    network->proceed = ticket.state == QueueTicketState::committed && ticket.error == CustodyFileError::none &&
                        !work->stop && !network->flight->cancelled->load();
                    network->phase = ProtectedNetworkWork::Phase::resultAdopted;
                    work->wake.notify_all();
                    lock.unlock();
                }
                if (command == StorageCommand::finalizeRecording) {
                    if (adopted && ticket.state == QueueTicketState::committed && ticket.error == CustodyFileError::none &&
                        recordingResult && recordingResult->shortRecordingDiscarded) {
                        bool stopReadbackAttempted = false;
                        for (;;) {
                            bool recoveryNeeded = shortRemoved;
                            if (!shortRemoved) {
                                const auto removed = owner->discardShortRecording(recording->session,
                                    recordingResult->packageContext, recordingResult->packageGeneration, work->cancellation);
                                ticket.error = removed.error; ticket.nativeError = removed.nativeError;
                                shortRemoved = removed.ok() && *removed.value;
                                recoveryNeeded = removed.error == CustodyFileError::recoveryRequired;
                            }
                            if (shortRemoved) {
                                const auto context = owner->queueContext();
                                if (owner->queueGeneration() == ticket.targetGeneration &&
                                    context.storeId == ticket.context.storeId && context.objectId == ticket.context.objectId &&
                                    context.role == ticket.context.role) {
                                    ticket.error = CustodyFileError::none; ticket.nativeError = 0;
                                    break;
                                }
                                recoveryNeeded = true; ticket.error = CustodyFileError::conflict;
                            }
                            std::unique_lock<std::mutex> pendingLock(work->mutex);
                            work->shortDiscardPending = true;
                            if (work->stop && !recoveryNeeded) {
                                work->shortDiscardPending = false;
                                ticket.error = CustodyFileError::recoveryRequired;
                                break;
                            }
                            if (!work->stop)
                                work->wake.wait(pendingLock, [&] { return work->stop || work->reconcileRequested; });
                            else if (stopReadbackAttempted)
                                work->wake.wait_for(pendingLock, std::chrono::seconds(30), [&] { return work->reconcileRequested; });
                            if (work->stop) stopReadbackAttempted = true;
                            work->shortDiscardPending = false; work->reconcileRequested = false;
                        }
                    }
                    const bool durable = ticket.state == QueueTicketState::committed && ticket.error == CustodyFileError::none;
                    std::shared_ptr<V5LocalRecordingWriter> writer;
                    {
                        std::lock_guard<std::mutex> recordingLock(recording->mutex);
                        writer = std::move(recording->writer);
                        recording->timeline.reset(); recording->processor.reset();
                    }
                    writer.reset(); // Native teardown never holds the UI value mutex.
                    std::lock_guard<std::mutex> recordingLock(recording->mutex);
                    const bool keepable = recordingResult && recordingResult->keepablePackage();
                    const bool discarded = shortRemoved && ticket.error == CustodyFileError::none;
                    recording->result = {durable && keepable,
                        (durable && keepable) || discarded ? ReasonCode::none :
                            recordingResult && recordingResult->captureFailure != ReasonCode::none ?
                                recordingResult->captureFailure : ReasonCode::storageUnavailable,
                        recordingResult && (recordingResult->trustedPrefixRetained || recordingResult->normalPackage()), discarded};
                    drainingActiveLease = std::move(recording->activeLease);
                    recording->terminal = true;
                }
                lock.lock();
                if (command == StorageCommand::finalizeRecording) {
                    work->recording.reset();
                    work->inFlight = false;
                    if (ticket.error != CustodyFileError::none) work->queueFailed = true;
                    if (!work->stop) drainingActiveLease.reset(); // Live session owns its slot until terminal.
                }
            }
        }
        value.reset();
        owner.reset(); // Last native release on worker, before terminal.
        drainingActiveLease.reset();
        std::lock_guard<std::mutex> lock(work->mutex);
        if (work->inFlight && !work->resultReady) {
            // An accepted scalar command cancelled before the worker started
            // still has a terminal outcome; never leave its ticket pending.
            work->ticket.state = QueueTicketState::notCommitted;
            work->ticket.error = CustodyFileError::ioFailed;
            work->ticket.nativeError = ERROR_OPERATION_ABORTED;
            work->ticket.targetGeneration = work->ticket.baseGeneration;
            work->resultReady = true;
            work->inFlight = false;
        }
        work->terminal = true;
        return 0;
    }
    void pollStorageStartup(bool allowDisplay) {
        if (!storageStartup_) return;
        bool restart = false;
        std::shared_ptr<DesktopUploadRecoveryScheduler::ProtectedFlight> acknowledgedUpload;
        std::uint32_t retryAfter = 0;
        std::optional<std::int64_t> expiry;
        {
            std::lock_guard<std::mutex> lock(storageStartup_->mutex);
            restart = storageStartup_->stop && storageStartup_->terminal && !shuttingDown_ && !exitAdmissionBlocked_ &&
                !updateAdmissionBlocked_ && storageThread_ && WaitForSingleObject(storageThread_.get(), 0) == WAIT_OBJECT_0;
            if (storageStartup_->ready && !storageStartup_->adopted) {
                // Storage truth is not account, Record or consumer permission.
                protectedQueueValue_ = storageStartup_->startupValue;
                storageStartup_->adopted = true;
                storageStartup_->wake.notify_all();
            }
            if (storageStartup_->resultReady && !storageStartup_->resultAdopted) {
                lastQueueTicket_ = storageStartup_->ticket;
                if (lastQueueTicket_->kind == QueueMutationKind::manualSend) lastManualSendTicket_ = lastQueueTicket_;
                if (lastQueueTicket_->kind == QueueMutationKind::lifecycleResult) lastLifecycleTicket_ = lastQueueTicket_;
                if (lastQueueTicket_->kind == QueueMutationKind::deletionIntent || lastQueueTicket_->kind == QueueMutationKind::deletionResult ||
                    lastQueueTicket_->kind == QueueMutationKind::deletionPurge)
                    lastDeletionTicket_ = lastQueueTicket_;
                if (lastQueueTicket_->kind == QueueMutationKind::deletionIntent &&
                    lastQueueTicket_->state == QueueTicketState::committed && lastQueueTicket_->epoch == authGeneration_ &&
                    currentAccount_ && storageStartup_->deletion) lastDeletionPlan_ = storageStartup_->deletion->plan;
                if (storageStartup_->physicalReadback) {
                    protectedQueueValue_ = storageStartup_->resultValue;
                    storageStartup_->generation = storageStartup_->readbackGeneration;
                } else if (lastQueueTicket_->state == QueueTicketState::committed) {
                    // Even a stale account accepts physical storage truth only.
                    // Existing public queue_/effects stay behind closed admission.
                    protectedQueueValue_ = storageStartup_->resultValue;
                    storageStartup_->generation = lastQueueTicket_->targetGeneration;
                    if (lastQueueTicket_->kind == QueueMutationKind::uploadResult && storageStartup_->upload) {
                        acknowledgedUpload = storageStartup_->upload;
                        retryAfter = storageStartup_->retryAfterSeconds;
                        expiry = storageStartup_->authExpiresAt;
                    }
                }
                storageStartup_->resultAdopted = true;
                storageStartup_->wake.notify_all();
            }
            if (storageStartup_->retiredManualSend) {
                if (lastManualSendTicket_ && lastManualSendTicket_->id == storageStartup_->retiredManualSend->id)
                    lastManualSendTicket_ = storageStartup_->retiredManualSend;
                storageStartup_->retiredManualSend.reset();
            }
            if (!shuttingDown_ && !exitAdmissionBlocked_ && !updateAdmissionBlocked_ &&
                authSessionToken_.empty() && protectedRecoveryEpoch_ && storageStartup_->adopted && storageStartup_->startupValue &&
                !storageStartup_->stop && !storageStartup_->queueFailed && !storageStartup_->inFlight &&
                !storageStartup_->recording && !storageStartup_->upload && !deletionContinuationId_ &&
                storageStartup_->nextTicket != (std::numeric_limits<std::uint64_t>::max)()) {
                storageStartup_->ticket = {};
                storageStartup_->command = StorageCommand::recovery;
                auto& ticket = storageStartup_->ticket;
                ticket.id = ++storageStartup_->nextTicket; ticket.epoch = *protectedRecoveryEpoch_;
                ticket.context = storageStartup_->context; ticket.baseGeneration = storageStartup_->generation;
                ticket.targetGeneration = ticket.baseGeneration;
                lastQueueTicket_ = ticket; // Accepted intent is pending, never the previous success.
                storageStartup_->commandReady = storageStartup_->inFlight = true;
                protectedRecoveryEpoch_.reset();
                storageStartup_->wake.notify_all();
            }
            auto& work = *storageStartup_;
            if (work.display && (work.display->snapshot != protectedQueueValue_ || work.display->epoch != authGeneration_))
                work.display->cancelled->store(true);
            const bool retired = !work.display || (work.display->done.load(std::memory_order_acquire) &&
                (work.display->snapshot != protectedQueueValue_ || work.display->epoch != authGeneration_ ||
                    (!work.display->result && std::chrono::steady_clock::now() >= work.display->retryAt)));
            const auto content = localContentContext();
            if (allowDisplay && retired && !content.owner.empty() && protectedQueueValue_ && work.adopted && !work.stop && !work.queueFailed &&
                !work.inFlight && !work.recoveryCancellation && !work.upload && !deletionContinuationId_ && (!work.resultReady || work.resultAdopted) &&
                !shuttingDown_ && !exitAdmissionBlocked_ && !updateAdmissionBlocked_) try {
                auto display = std::allocate_shared<DisplayWork>(CustodyAllocator<DisplayWork>{});
                display->snapshot = protectedQueueValue_;
                display->epoch = authGeneration_;
                display->user.assign(content.owner.begin(), content.owner.end());
                display->workspace.assign(content.workspace.begin(), content.workspace.end());
                work.display = std::move(display);
                work.wake.notify_all();
            } catch (...) {} // Existing polling retries a refused charged allocation.
        }
        // Shell callbacks may pump another UI tick. Never invoke them while
        // holding the storage value mutex or before the exact adoption ACK.
        if (acknowledgedUpload && acknowledgedUpload->epoch == authGeneration_ && !acknowledgedUpload->cancelled->load() &&
            !shuttingDown_ && !exitAdmissionBlocked_ && !updateAdmissionBlocked_ && currentAccount_) {
            if (retryAfter) scheduler_.deferFor(retryAfter);
            if (expiry && sessionExpiryHandler_) sessionExpiryHandler_(*expiry);
        }
        if (restart) {
            storageThread_.close(); storageStartup_.reset();
            startStorageValidation(); // Cancelled update requires a fresh native validation.
        }
    }
    void stopStorageStartup() noexcept {
        protectedRecoveryEpoch_.reset();
        if (!storageStartup_) return;
        std::lock_guard<std::mutex> lock(storageStartup_->mutex);
        cancelUnstartedRecording(*storageStartup_);
        // The held root's disk checks use this cancellation too. An accepted
        // recording must finish sealed bytes and queue ACK before root teardown.
        if (storageStartup_->upload) storageStartup_->upload->cancelled->store(true);
        if (storageStartup_->display) storageStartup_->display->cancelled->store(true);
        if (storageStartup_->playback) storageStartup_->playback->cancelled->store(true);
        if (storageStartup_->deletion) storageStartup_->deletion->cancelled->store(true);
        if (storageStartup_->recoveryCancellation) storageStartup_->recoveryCancellation->store(true);
        storageStartup_->reconcileRequested = true;
        if (!storageStartup_->recording && !storageStartup_->upload && !storageStartup_->deletion && !storageStartup_->recoveryCancellation &&
            !storageStartup_->commandReconciliation)
            storageStartup_->cancellation->store(true);
        storageStartup_->stop = true;
        finalizeStoppedRecording(*storageStartup_);
        storageStartup_->wake.notify_all();
    }
    struct AccountProof {
        DesktopHttpTransport::IdentityResult account;
        std::shared_ptr<const ProtectedUploadQueueValue::AuthenticatedContext> context;
    };
    void pollAccount() {
        if (accountFuture_.valid() && accountFuture_.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            AccountProof result; result.account.status = DesktopTransportStatus::retryableFailure;
            try { result = accountFuture_.get(); } catch (...) {}
            if (accountRequestGeneration_ == authGeneration_) {
                const auto& identity = result.account.identity;
                if (identity) {
                    const auto previousContent = localContentContext();
                    if ((provenAccount_ && (provenAccount_->userId != identity->userId ||
                        provenAccount_->workspaceId != identity->workspaceId)) ||
                        (!previousContent.owner.empty() && (previousContent.owner != identity->userId ||
                            previousContent.workspace != identity->workspaceId))) {
                        localRestorationAllowed_ = false;
                        invalidateAuthentication();
                        protectedRecoveryEpoch_ = authGeneration_;
                        pendingRecovery_ = RecoveryTrigger::authRecovered;
                    }
                    currentAccount_ = identity; provenAccount_ = identity;
                    pendingAuthenticatedContext_ = std::move(result.context);
                    lifecycleGateFresh_ = !!pendingAuthenticatedContext_;
                    lifecycleRequested_ = true;
                } else if (result.account.status != DesktopTransportStatus::retryableFailure) {
                    localRestorationAllowed_ = false;
                    invalidateAuthentication();
                }
                accountRetryAt_ = identity && accountRevalidationRequested_ ? 0 : GetTickCount64() + 30000;
                if (accountRevalidationRequested_) currentAccount_.reset();
            }
        }
        if (shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_ || authSessionToken_.empty() ||
            accountFuture_.valid() || (currentAccount_ && !accountRevalidationRequested_) ||
            GetTickCount64() < accountRetryAt_) return;
        DesktopHttpConfig config; config.sessionToken = authSessionToken_;
        accountCancellation_ = std::make_shared<std::atomic_bool>(false); config.cancellation = accountCancellation_;
        const bool protocolRequired = lifecycleEnabled_;
        std::packaged_task<AccountProof()> task([config, wire = wire_, protocol = protectedWire_, protocolRequired] {
            AccountProof proof;
            proof.account.status = DesktopTransportStatus::retryableFailure;
            try {
                const DesktopHttpTransport transport(config);
                DesktopHttpTransport::IdentityGet get;
                if (wire) get = [&wire](const auto& value, std::string_view path) {
                    auto response = wire(value, {"GET", std::string(path), "", true});
                    return DesktopHttpTransport::IdentityResponse{response.status, std::move(response.body), response.transportFailed};
                };
                proof.account = transport.accountIdentity(get);
                if (!proof.account.identity || !protocolRequired) return proof;
                const auto& identity = *proof.account.identity;
                BasicDeletionWireResult<std::string> gate;
                if (protocol) {
                    ProtectedDesktopHttpConfig scoped;
                    scoped.baseOrigin = config.baseOrigin; scoped.sessionToken = config.sessionToken;
                    scoped.workspaceId = identity.workspaceId; scoped.cancellation = config.cancellation;
                    scoped.confirmedIdentity = BasicDesktopAccountIdentity<CustodyString>{CustodyString(identity.userId), CustodyString(identity.workspaceId)};
                    scoped.scopedAccount = BasicDeletionScope<CustodyString>{CustodyString(identity.userId), CustodyString(identity.workspaceId)};
                    const auto answer = protocol(scoped, {"GET", CustodyString(DesktopApiClient::notificationContextPath), {}, true});
                    gate = {answer.status, std::string(answer.body.begin(), answer.body.end()), answer.transportFailed,
                        DesktopHttpTransport::rateLimitPauseSeconds(answer.status, std::string_view(answer.retryAfter)), {}};
                } else {
                    auto scoped = config; scoped.workspaceId = identity.workspaceId;
                    scoped.confirmedIdentity = identity;
                    const auto answer = DesktopHttpTransport(scoped).notificationContext({identity.userId, identity.workspaceId});
                    gate = {answer.status, answer.body, answer.transportFailed, answer.retryAfterSeconds, answer.safeReason};
                }
                const auto reason = DesktopUploadQueueService::deletionGateReason(gate, identity, config.cancellation.get());
                if (!reason.empty()) {
                    proof.account.identity.reset();
                    proof.account.status = reason == "authentication" || reason == "scope_changed" ?
                        DesktopTransportStatus::authRequired : DesktopTransportStatus::retryableFailure;
                    return proof;
                }
                auto context = std::allocate_shared<ProtectedUploadQueueValue::AuthenticatedContext>(
                    CustodyAllocator<ProtectedUploadQueueValue::AuthenticatedContext>{});
                context->serverOrigin = config.baseOrigin; context->actorUserId = identity.userId;
                context->workspaceId = identity.workspaceId; context->sessionFingerprint = nativeSessionFingerprint(config);
                proof.context = std::move(context);
                return proof;
            } catch (...) {
                proof.account.identity.reset(); proof.account.status = DesktopTransportStatus::retryableFailure;
                return proof;
            }
        });
        accountRequestGeneration_ = authGeneration_;
        try {
            auto future = task.get_future();
            std::thread(std::move(task)).detach();
            accountFuture_ = std::move(future); accountRevalidationRequested_ = false;
            // Stop old scoped continuations before the fresh lookup is pending.
            currentAccount_.reset(); scheduler_.cancel(); cancelRecordingLifecycle();
            if (storageStartup_) {
                std::lock_guard<std::mutex> lock(storageStartup_->mutex);
                if (storageStartup_->upload) storageStartup_->upload->cancelled->store(true);
                storageStartup_->wake.notify_all();
            }
        } catch (...) { accountRetryAt_ = GetTickCount64() + 30000; }
    }

    void createRecordingPipeline() {
        controller_.reset();
        sessionId_ = native_capture_detail::newSessionId();
        timeline_ = std::make_shared<RecordingAudioTimeline>(*aecSelection_.processor);
        recordingWork_.reset();
        pendingStartReadiness_.reset();
        controller_ = std::make_unique<WindowsCaptureSessionController>(
            sessionId_,
            [this](AudioBatch batch) {
                const auto recording = recordingWork_;
                if (!recording) return false;
                V5LocalRecordingWriter* writer = nullptr;
                {
                    std::lock_guard<std::mutex> lock(recording->mutex);
                    if (!recording->prepared || !recording->started || recording->finalizing ||
                        recording->terminal || !recording->writer) return false;
                    writer = recording->writer.get();
                }
                // The storage worker retains this writer until actual controller
                // EOS/dispatcher completion. No mutex spans storage IO on UI.
                const auto level = native_capture_detail::rmsLevel(batch.samples);
                if (batch.source == AudioSource::microphone) microphoneLevel_.store(level, std::memory_order_relaxed);
                else systemRenderLevel_.store(level, std::memory_order_relaxed);
                if (!recording->timeline->push(std::move(batch))) return false;
                for (const auto& frame : recording->timeline->takeFrames()) {
                    if (!writer->append(frame)) return false;
                    recording->frames.store(writer->frameCount());
                }
                return true;
            },
            [this](ReasonCode failure, RecordingStopReason stopReason) -> std::optional<CaptureFinalization> {
                if (!recordingWork_) return CaptureFinalization{false, ReasonCode::storageUnavailable, false};
                requestProtectedFinalization(failure, stopReason);
                std::lock_guard<std::mutex> lock(recordingWork_->mutex);
                if (!recordingWork_->terminal) return std::nullopt;
                auto result = recordingWork_->result;
                // Physical state/queue adoption remains true for a stale account,
                // but its old action cannot produce a new normal UI reply.
                if (recordingWork_->epoch != authGeneration_ || shuttingDown_ || exitAdmissionBlocked_ || updateAdmissionBlocked_) {
                    result.savedLocal = false;
                    result.shortRecordingDiscarded = false;
                    if (result.reason == ReasonCode::none) result.reason = ReasonCode::storageUnavailable;
                }
                return result;
            },
            [this](bool paused) {
                if (recordingWork_ && recordingWork_->timeline) recordingWork_->timeline->setMicrophonePaused(paused);
            },
            [this](bool opening, std::uint64_t wallMs, std::uint64_t monotonicMs) -> PrivacyCheckpointResult {
                const auto recording = recordingWork_;
                if (!recording) return {};
                V5LocalRecordingWriter* writer = nullptr;
                {
                    std::lock_guard<std::mutex> lock(recording->mutex);
                    if (!recording->started || recording->finalizing || recording->terminal || !recording->writer) return {};
                    writer = recording->writer.get();
                }
                // The same dispatcher owns append and both metadata commands;
                // EOS closes history before the storage worker can finalize it.
                const auto saved = opening ? writer->pausePrivacy(wallMs, monotonicMs) : writer->closePrivacy(wallMs, monotonicMs);
                return {saved.ok() && *saved.value, !writer->healthy()};
            });
    }
public:
    void refreshReadiness() {
        if (controller_->indicator().snapshot().visible) return;
        if (!microphonePreferenceLoaded_) {
            selectedMicrophone_ = native_capture_detail::selectedMicrophonePreference();
            microphonePreferenceLoaded_ = true;
        }
        readiness_.aacEncoderReady = native_capture_detail::mediaFoundationAacReady();
        const auto endpoints = enumerator_.snapshot();
        graf::windows::WasapiEndpointSnapshot render;
        graf::windows::WasapiEndpointSnapshot microphone;
        microphones_.clear();
        if (endpoints.ok()) {
            for (const auto& endpoint : endpoints.endpoints) {
                if (endpoint.flow == graf::windows::WasapiDataFlow::render && endpoint.isDefault) render = endpoint;
                if (graf::windows::WasapiEndpointEnumerator::isAllowedMicrophone(endpoint)) {
                    microphones_.push_back(endpoint);
                    if (selectedMicrophone_.empty()
                            ? (microphone.stableId.empty() || (!microphone.isDefault && endpoint.isDefault))
                            : endpoint.stableId == selectedMicrophone_) microphone = endpoint;
                }
            }
        }
        if (!render.stableId.empty() && !microphone.stableId.empty()) {
            controller_->setEndpoints(render, microphone);
        }
        const auto supportsSampleRate = [](std::uint32_t sampleRate) {
            return sampleRate >= 8'000 && sampleRate <= 192'000;
        };
        readiness_.microphoneEndpointReady = !microphone.stableId.empty();
        currentEndpointIdentity_ = microphone.stableId;
        readiness_.renderEndpointReady = !render.stableId.empty();
        readiness_.formatNormalizationReady = supportsSampleRate(render.sampleRate) &&
            supportsSampleRate(microphone.sampleRate) && render.channels > 0 && microphone.channels > 0;
        readiness_.microphonePermissionGranted = native_capture_detail::microphonePrivacyGranted();
        sourceSummary_ = microphone.stableId.empty()
            ? L"Выбранный микрофон недоступен. Подключите его или выберите другой."
            : L"Микрофон: " + native_capture_detail::deviceDisplayName(microphone.friendlyName);
        sourceSummary_ += render.stableId.empty() ? L" · Вывод недоступен"
            : L" · Системный звук: " + native_capture_detail::deviceDisplayName(render.friendlyName);
    }

private:
    graf::windows::WasapiEndpointEnumerator enumerator_;
    std::vector<graf::windows::WasapiEndpointSnapshot> microphones_;
    std::string selectedMicrophone_;
    bool microphonePreferenceLoaded_ = false;
    std::wstring sourceSummary_;
    std::string currentEndpointIdentity_;
    std::string recordingEndpointIdentity_;
    std::string diagnosticsSessionId_;
    std::string lastDiagnostics_;
    AecSelection aecSelection_;
    std::string sessionId_;
    std::shared_ptr<graf::windows::RecordingAudioTimeline> timeline_;
    std::filesystem::path custodyRoot_;
    std::shared_ptr<StorageStartupWork> storageStartup_;
    std::shared_ptr<const ProtectedUploadQueueValue> protectedQueueValue_;
    std::optional<std::uint64_t> protectedRecoveryEpoch_;
    std::optional<QueueMutationTicket> lastQueueTicket_;
    std::optional<QueueMutationTicket> lastManualSendTicket_;
    std::optional<QueueMutationTicket> lastDeletionTicket_;
    std::optional<QueueMutationTicket> lastLifecycleTicket_;
    std::shared_ptr<LifecycleFlight> lifecycleFlight_;
    std::thread lifecycleThread_;
    std::future<std::shared_ptr<const LifecycleBatch>> lifecycleFuture_;
    CustodyVector<CustodyString> lifecycleVisible_;
    CustodyVector<CustodyString> lifecycleRestrictions_; // Validated restrictive targets only, retained through failed publication.
    CustodyString lifecycleOpen_, lifecycleCursor_, lifecycleUser_, lifecycleWorkspace_, lifecycleOrigin_;
    std::uint64_t lifecycleEpoch_ = 0, lifecycleRetryAt_ = 0;
    bool lifecycleEnabled_ = false, lifecycleRequested_ = false;
    std::size_t lifecyclePolling_ = 0;
    std::shared_ptr<const ProtectedDeletionPlan> lastDeletionPlan_;
    std::uint64_t deletionContinuationId_ = 0, deletionContinuationEpoch_ = 0;
    std::shared_ptr<std::atomic<bool>> deletionContinuationCancellation_;
    std::shared_ptr<DeletionFlight> deletionFlight_;
    std::uint64_t backgroundDeletionId_ = 0;
    std::optional<std::uint64_t> protectedPurgeAttemptGeneration_;
    std::optional<DeletionCompletion> deletionCompletion_;
    std::thread deletionThread_;
    std::future<std::shared_ptr<const ProtectedDeletionResponse>> deletionFuture_;
    std::size_t deletionPolling_ = 0;
    bool deletionShutdownPending_ = false;
    winrt::handle storageThread_;
    std::shared_ptr<RecordingWork> recordingWork_;
    std::optional<ReadinessInputs> pendingStartReadiness_;
    graf::windows::RecordingNoticePresenter noticePresenter_;
    graf::windows::DesktopUploadQueueService queue_;
    // The shell's handler for the session deadline the server names while
    // answering. Empty means the shell does not carry it anywhere.
    std::function<void(std::int64_t)> sessionExpiryHandler_;
    graf::windows::DesktopUploadRecoveryScheduler scheduler_;
    DesktopHttpTransport::UploadSend wire_; // Same copied wire seam; default uses native HTTP.
    DesktopHttpTransport::ProtectedUploadSend protectedWire_; // Typed wire substitution; no storage/account authority.
    std::optional<graf::windows::RecoveryTrigger> pendingRecovery_;
    bool shuttingDown_ = false;
    bool exitAdmissionBlocked_ = false;
    bool updateAdmissionBlocked_ = false;
    std::size_t synchronousMutations_ = 0;
    std::unique_ptr<graf::windows::WindowsCaptureSessionController> controller_;
    graf::windows::ReadinessInputs readiness_;
    std::string authSessionToken_;
    bool authSignedOutObserved_ = false;
    std::optional<graf::windows::DesktopAccountIdentity> currentAccount_;
    std::optional<graf::windows::DesktopAccountIdentity> recordingAccount_;
    std::string recordingOrigin_;
    std::future<AccountProof> accountFuture_;
    std::optional<DesktopAccountIdentity> provenAccount_;
    bool accountRevalidationRequested_ = false, lifecycleGateFresh_ = false;
    bool nativeCookieObserved_ = false, localRestorationAllowed_ = true;
    std::shared_ptr<const ProtectedUploadQueueValue::AuthenticatedContext> pendingAuthenticatedContext_;
    std::optional<std::uint64_t> authenticatedContextTicket_;
    std::shared_ptr<std::atomic_bool> accountCancellation_;
    std::uint64_t authGeneration_ = 0;
    std::uint64_t accountRequestGeneration_ = 0;
    ULONGLONG accountRetryAt_ = 0;
    std::atomic<float> microphoneLevel_{0.0F};
    std::atomic<float> systemRenderLevel_{0.0F};
};

} // namespace graf::windows
#endif
