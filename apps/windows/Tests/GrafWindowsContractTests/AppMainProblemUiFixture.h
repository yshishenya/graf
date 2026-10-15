#pragma once
// Forced include for the derivative AppMain compile item ONLY. No production
// switches, account setters, device access or replacement catch implementation.
#include <windows.h>
#undef GetClassName
#undef GetCurrentTime
#include "../../RecApp/Recording/NativeCapture.h"
#include "../../RecApp/Storage/Sha256.h"
#include <winrt/Windows.Foundation.h>
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#include <winrt/Microsoft.UI.Xaml.Controls.Primitives.h>
#include <winrt/Microsoft.UI.Xaml.Media.h>
#include <winrt/Microsoft.UI.Xaml.Automation.Peers.h>
#include <winrt/Microsoft.UI.Xaml.Automation.Provider.h>
#include <cstdio>
#include <map>
#include <tuple>

namespace graf::windows {
struct NativeCaptureStorageTestPeer {
    static void pollAccount(NativeCapture& capture) { capture.pollAccount(); }
};
namespace testing {
inline int problemUiResult = 2;
inline void requireProblemUi(bool value, const char* label) {
    if (!value) { std::fprintf(stderr, "PROBLEM_UI failure=%s\n", label); throw std::runtime_error(label); }
}
inline winrt::Microsoft::UI::Xaml::Controls::Button problemUiButton(
    const winrt::Microsoft::UI::Xaml::DependencyObject& object, winrt::hstring const& text) {
    using namespace winrt::Microsoft::UI::Xaml;
    if (auto button = object.try_as<Controls::Button>(); button && button.Content() &&
        winrt::unbox_value<winrt::hstring>(button.Content()) == text) return button;
    for (int i = 0; i < Media::VisualTreeHelper::GetChildrenCount(object); ++i)
        if (auto button = problemUiButton(Media::VisualTreeHelper::GetChild(object, i), text)) return button;
    return nullptr;
}
inline winrt::Microsoft::UI::Xaml::Controls::ContentDialog problemUiDialog(
    const winrt::Microsoft::UI::Xaml::DependencyObject& object) {
    using namespace winrt::Microsoft::UI::Xaml;
    if (auto dialog = object.try_as<Controls::ContentDialog>()) return dialog;
    for (int i = 0; i < Media::VisualTreeHelper::GetChildrenCount(object); ++i)
        if (auto dialog = problemUiDialog(Media::VisualTreeHelper::GetChild(object, i))) return dialog;
    return nullptr;
}
inline void invokeProblemUi(const winrt::Microsoft::UI::Xaml::Controls::Button& button) {
    using namespace winrt::Microsoft::UI::Xaml::Automation;
    requireProblemUi(button && button.IsEnabled(), "actual_enabled_button");
    const auto provider = Peers::ButtonAutomationPeer(button).GetPattern(Peers::PatternInterface::Invoke)
        .as<Provider::IInvokeProvider>();
    requireProblemUi(bool(provider), "actual_invoke_provider");
    provider.Invoke(); // The SDK raises the real Button event, not a copied callback.
}
struct ProblemUiAec final : IAec3Processor {
    bool process(const float*, const float* microphone, float* cleaned) noexcept override {
        std::copy_n(microphone, 480, cleaned); return true; // Never started by this metadata/UI test.
    }
};
using ProblemUiSnapshot = std::map<std::wstring, std::string>;
inline ProblemUiSnapshot problemUiSnapshot(const std::filesystem::path& root) {
    ProblemUiSnapshot result;
    for (const auto& file : std::filesystem::recursive_directory_iterator(root)) if (file.is_regular_file()) {
        auto hash = sha256File(file.path()); requireProblemUi(hash.size() == 64, "generated_snapshot_hash");
        result.emplace(file.path().lexically_relative(root).native(), std::move(hash));
    }
    return result;
}
inline bool sameProblemUiRow(const ProtectedUploadQueueValue::Item& a, const ProtectedUploadQueueValue::Item& b) {
    const auto fields = [](const auto& row) {
        return std::tie(row.localRecordingId, row.directoryId, row.sessionId, row.packageDirectory, row.status,
            row.acceptedBytes, row.attempts, row.safeReason, row.ownerUserId, row.ownerWorkspaceId, row.meetingId,
            row.updatedAtMs, row.mediaRevisionId, row.uploadSessionId, row.serverStatus, row.processingStatus, row.mediaRevisionStatus);
    };
    return fields(a) == fields(b);
}
struct ProblemUiState {
    std::filesystem::path parent, root;
    std::future<void> seed;
    std::future<bool> cleanup;
    ProblemUiSnapshot original, packageBefore, afterRemoval;
    winrt::file_handle packageHandle;
    std::map<std::string, std::string> preferences;
    unsigned writes = 0, accountCalls = 0, phase = 0;
    unsigned primaryEvents = 0, closedEvents = 0;
    winrt::Microsoft::UI::Xaml::Controls::ContentDialog dialog{nullptr};
    std::shared_ptr<const ProtectedUploadQueueValue> beforeAction;
    std::shared_ptr<const ProtectedUploadQueueValue> afterAction;
    std::uint64_t removalTicket = 0;
    std::size_t baseline = CustodyOwnedMemory::usedBytes();
    bool created = false, loaded = false, passed = false, failed = false, selectionPrepared = false, positive = false;
    RecordingNoticePresenter::Clock::time_point deadline = RecordingNoticePresenter::Clock::now() + std::chrono::seconds(60);
    ~ProblemUiState() {
        // Worker captures must finish before original/preferences are destroyed.
        if (seed.valid()) seed.wait();
        if (cleanup.valid()) cleanup.wait();
    }
    NotificationPreferenceStore store() {
        return {[this](std::string_view key) -> std::optional<std::string> {
            const auto found = preferences.find(std::string(key));
            return found == preferences.end() ? std::nullopt : std::optional<std::string>{found->second};
        }, [this](std::string_view key, std::string_view value) {
            ++writes; preferences[std::string(key)] = std::string(value); return true;
        }};
    }
    void startSeed() {
        GUID id{}; requireProblemUi(CoCreateGuid(&id) == S_OK, "generated_guid");
        wchar_t name[40]{}; requireProblemUi(StringFromGUID2(id, name, 40) != 0, "generated_name");
        const auto temporary = std::filesystem::temp_directory_path();
        wchar_t actual[32768]{}; const auto length = GetLongPathNameW(temporary.c_str(), actual, 32768);
        requireProblemUi(length && length < 32768, "generated_temp_namespace");
        parent = std::filesystem::path(actual) / (std::wstring(L"graf-problem-ui-") + name);
        root = parent / L"recordings";
        seed = std::async(std::launch::async, [this] {
            requireProblemUi(CreateDirectoryW(parent.c_str(), nullptr) != FALSE, "exclusive_generated_parent");
            created = true;
            {
            std::string json;
            DesktopUploadQueueService queue(root / L"unused.json", root,
                [&](const auto&, const auto&, std::string_view bytes) { json.assign(bytes); return true; });
            queue.setClock([] { return 1000; });
            for (const auto status : {UploadQueueStatus::needsAuth, UploadQueueStatus::uploaded}) {
                const auto item = status == UploadQueueStatus::needsAuth ? "waiting" : "retained";
                requireProblemUi(queue.enqueue({item, item, item, root / item, status, {11, 22, 33}, 3,
                    status == UploadQueueStatus::needsAuth ? "auth_required" : "",
                    "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"}), "generated_enqueue");
            }
            auto cancellation = std::make_shared<std::atomic_bool>(false);
            auto opened = ProtectedCustodyStoreOwner::open(root, cancellation);
            requireProblemUi(opened.ok(), "generated_protected_owner");
            auto owner = *opened.value;
            {
                auto recording = V5LocalRecordingWriter::open(owner, "waiting", cancellation);
                requireProblemUi(recording.ok(), "genuine_writer_open");
                CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
                for (unsigned i = 0; i != 500; ++i) {
                    frame.ptsFrames = i * 480;
                    requireProblemUi((*recording.value)->append(frame), "genuine_generated_append");
                }
                requireProblemUi((*recording.value)->finalize().normalPackage(), "genuine_generated_finalize");
            } // No writer/package lease is held across the actual user action.
            CustodyBytes bytes(json.begin(), json.end());
            const auto result = commitProtectedCustodyMetadata(owner, owner->queueContext(), 1, bytes, cancellation);
            requireProblemUi(result.state == CustodyCommitState::committed && result.targetGeneration == 2, "generated_commit");
            } // All custody handles/pins are released before the physical byte snapshot.
            original = problemUiSnapshot(root);
            packageBefore = problemUiSnapshot(root / L"waiting");
            requireProblemUi(!packageBefore.empty(), "genuine_package_nonempty");
            packageHandle.attach(CreateFileW((root / L"waiting").c_str(), FILE_READ_ATTRIBUTES,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING,
                FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
            requireProblemUi(bool(packageHandle), "generated_directory_identity_handle");
        });
    }
    DesktopHttpTransport::UploadResponse account(const DesktopHttpConfig& config, const DesktopHttpTransport::UploadRequest& request) {
        requireProblemUi(config.sessionToken == "generated-problem-ui" && request.method == "GET", "metadata_only_wire");
        ++accountCalls; // Read on UI only after the resolver's future is adopted.
        if (request.path == "/desktop/settings/spaces")
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        requireProblemUi(request.path == "/api/v1/auth/me", "identity_only_wire");
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    }
    void startByteCheck() {
        requireProblemUi(!seed.valid(), "previous_worker_consumed");
        seed = std::async(std::launch::async, [this] {
            requireProblemUi(problemUiSnapshot(root) == original, "action_protected_bytes_unchanged");
        });
    }
    void startRemovalCheck() {
        requireProblemUi(!seed.valid() && afterAction, "removal_worker_input");
        seed = std::async(std::launch::async, [this] {
            wchar_t moved[32768]{};
            const auto length = GetFinalPathNameByHandleW(packageHandle.get(), moved, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
            requireProblemUi(length && length < 32768, "same_directory_final_name");
            // Exact fixed-volume namespace and first component, not a substring
            // match or an enumeration of anybody else's Recycle Bin contents.
            const std::filesystem::path destination(moved);
            const auto bin = std::filesystem::path(L"\\\\?\\" + root.root_path().native()) / L"$Recycle.Bin";
            const auto relative = destination.lexically_relative(bin);
            requireProblemUi(!relative.empty() && !relative.is_absolute() && *relative.begin() != L".." &&
                std::distance(relative.begin(), relative.end()) == 2, "same_volume_real_recycle_destination");
            requireProblemUi(!std::filesystem::exists(root / L"waiting") &&
                problemUiSnapshot(destination) == packageBefore, "recycled_package_bytes_preserved");
            afterRemoval = problemUiSnapshot(root);
            // Queue metadata may change; no other file may change OR appear.
            const auto unaffected = [](ProblemUiSnapshot files) {
                for (auto it = files.begin(); it != files.end();) {
                    const auto first = *std::filesystem::path(it->first).begin();
                    if (first == L"waiting" || first == L".custody-v1") it = files.erase(it);
                    else ++it;
                }
                return files;
            };
            requireProblemUi(unaffected(original) == unaffected(afterRemoval), "other_files_preserved_no_new_files");
            packageHandle.close(); // Leave only this generated encrypted package recoverable in the Bin.
        });
    }
    void startCleanup() {
        cleanup = std::async(std::launch::async, [this] {
            if (!created || parent.filename().wstring().find(L"graf-problem-ui-") != 0 || root.parent_path() != parent) return false;
            bool unchanged = false;
            try {
                const auto& expected = passed ? afterRemoval : original;
                unchanged = !expected.empty() && problemUiSnapshot(root) == expected;
                if (passed) {
                    auto cancel = std::make_shared<std::atomic<bool>>(false);
                    auto opened = ProtectedCustodyStoreOwner::open(root, cancel);
                    requireProblemUi(opened.ok(), "cold_queue_owner");
                    auto value = (*opened.value)->readQueueValue(cancel);
                    requireProblemUi(value.ok(), "cold_queue_read");
                    const auto cold = (*value.value)->serialize(cancel), adopted = afterAction->serialize(cancel);
                    requireProblemUi(cold.ok() && adopted.ok() && *cold.value == *adopted.value, "cold_adopted_queue_equal");
                }
            } catch (...) { unchanged = false; }
            afterAction.reset(); packageHandle.close();
            std::error_code error; std::filesystem::remove_all(parent, error);
            return unchanged && !error;
        });
    }
};
struct ProblemUiQuota {
    CustodyAllocator<char> allocator;
    std::size_t count = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
    char* reservation = allocator.allocate(count);
    ~ProblemUiQuota() { allocator.deallocate(reservation, count); }
};
inline bool sameProblemUiHistory(const std::vector<NoticeHistoryEntry>& left, const std::vector<NoticeHistoryEntry>& right) {
    return left.size() == right.size() && std::equal(left.begin(), left.end(), right.begin(), [](const auto& a, const auto& b) {
        return a.sequence == b.sequence && a.occurredAt == b.occurredAt && a.kind == b.kind;
    });
}
} // namespace testing
} // namespace graf::windows
