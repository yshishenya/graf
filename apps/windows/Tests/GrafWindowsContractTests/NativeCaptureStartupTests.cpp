#ifdef NDEBUG
#undef NDEBUG
#endif
#include "../../RecApp/Recording/NativeCapture.h"
#include "../../RecApp/Storage/Sha256.h"
#include <cassert>
#include <cstdio>
#include <filesystem>
#include <map>
#include <memory>
#include <string>
#include <system_error>
#include <type_traits>
#include <utility>
#if defined(_MSC_VER) && defined(_DEBUG)
#include <crtdbg.h>
#endif
namespace {
using namespace graf::windows;
static_assert(std::is_same_v<decltype(std::declval<NativeCapture&>().deletionLedger()),
    const DesktopUploadQueueService&>);
static_assert(std::is_same_v<decltype(std::declval<const NativeCapture&>().deletionLedger()),
    const DesktopUploadQueueService&>);

class GeneratedAec final : public graf::windows::IAec3Processor {
public:
    bool process(const float*, const float*, float*) noexcept override { return false; }
};
struct GeneratedRoot final {
    std::filesystem::path root;
    GeneratedRoot() {
        GUID id{};
        assert(CoCreateGuid(&id) == S_OK);
        wchar_t text[40]{};
        assert(StringFromGUID2(id, text, 40) != 0);
        root = std::filesystem::temp_directory_path() /
            (std::wstring(L"graf-native-startup-") + text);
        assert(CreateDirectoryW(root.c_str(), nullptr) != FALSE);
    }
    ~GeneratedRoot() {
        std::error_code error;
        std::filesystem::remove_all(root, error);
        assert(!error);
    }
    GeneratedRoot(const GeneratedRoot&) = delete;
    GeneratedRoot& operator=(const GeneratedRoot&) = delete;
};

void writeFixture(const std::filesystem::path& path, const std::string& bytes) {
    const auto file = CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr,
        CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
    assert(file != INVALID_HANDLE_VALUE);
    DWORD written = 0;
    assert(WriteFile(file, bytes.data(), static_cast<DWORD>(bytes.size()), &written, nullptr));
    assert(written == bytes.size());
    assert(FlushFileBuffers(file));
    assert(CloseHandle(file));
}

using Snapshot = std::map<std::wstring, std::string>;
Snapshot snapshot(const std::filesystem::path& ownedRoot) {
    Snapshot result;
    assert(std::filesystem::is_directory(ownedRoot));
    for (const auto& entry : std::filesystem::recursive_directory_iterator(ownedRoot)) {
        const auto name = entry.path().lexically_relative(ownedRoot).native();
        const auto type = entry.symlink_status().type();
        assert(type == std::filesystem::file_type::directory || type == std::filesystem::file_type::regular);
        if (type == std::filesystem::file_type::directory) result.emplace(name, "directory");
        else {
            const auto hash = sha256File(entry.path());
            assert(hash.size() == 64);
            result.emplace(name, std::to_string(entry.file_size()) + ":" + hash);
        }
    }
    return result;
}

void stageOneConstructor() {
    bool storageWritable = true;
    bool queueComplete = true;
    {
        GeneratedRoot fixture;
        graf::windows::NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false});
        storageWritable = capture.readiness().storageWritable;
        queueComplete = capture.localQueueComplete();
    }
    // Actual capture destruction and exact fixture cleanup precede RED asserts.
    assert(!storageWritable);
    assert(!queueComplete);
}

void closedCalls(NativeCapture& capture) {
    assert(!capture.readiness().storageWritable && !capture.recordingReady() && !capture.localQueueComplete());
    assert(capture.localItems().empty());
    assert(capture.deletionLedger().items().empty());
    assert(capture.deletionLedger().deletionOperations().empty());
    assert(capture.deletionLedger().localPurgeAcknowledgements().empty());
    const std::wstring unavailable = L"Защищённое локальное хранилище недоступно. Записи не изменены.";
    assert(capture.custodySummary() == unavailable && capture.readinessSummary() == unavailable);
    const auto session = capture.sessionId();
    const auto manual = capture.record();
    assert(manual.status == TransitionStatus::rejected && manual.reason == ReasonCode::storageUnavailable);
    unsigned starts = 0;
    const auto automatic = capture.record([&](const std::string&) {
        ++starts;
        return WindowsCaptureSessionController::StartGuard([](std::string_view) { return true; });
    });
    assert(automatic.status == TransitionStatus::rejected && automatic.reason == ReasonCode::storageUnavailable);
    assert(starts == 0 && capture.sessionId() == session && !capture.indicator().visible);
    assert(capture.authSessionToken().empty());
    const auto epoch = capture.authGeneration();
    capture.setAuthSessionToken("generated-not-a-session");
    capture.setAuthSessionToken({}); // Clear BEFORE any poll: no auth/network IO.
    assert(capture.authGeneration() == epoch + 2 && !capture.currentAccount());
    for (const auto trigger : {RecoveryTrigger::launch, RecoveryTrigger::activation,
        RecoveryTrigger::authRecovered, RecoveryTrigger::networkRecovered, RecoveryTrigger::wake,
        RecoveryTrigger::scheduled}) {
        capture.recover(trigger);
        assert(capture.authSessionToken().empty());
        capture.pollUploads();
        assert(!capture.uploadsBusy());
    }
    assert(!capture.requestProtectedManualSend({}, "generated-recording", capture.authGeneration(), true));
    assert(!capture.requestProtectedLocalRemoval({}, "generated-recording", capture.authGeneration()));
    assert(!capture.requestProtectedLocalRemoval({}, "generated-recording", capture.authGeneration(), true));
    assert(!capture.beginProtectedDeletionSelection({{DeletionTarget::ownOrigin, "generated-recording"}}));
    assert(!capture.beginProtectedLocalPurgePass());
    (void)capture.pause(); (void)capture.resume(); (void)capture.stop();
    (void)capture.stop(RecordingStopReason::interruption);
    capture.pollHealth();
    assert(capture.indicator().state == SessionState::idle && !capture.indicator().visible);
    assert(!capture.localQueueComplete() && !capture.uploadsBusy());
}

void rootMatrix() {
    for (int scenario = 0; scenario != 8; ++scenario) {
        GeneratedRoot fixture;
        auto inputRoot = fixture.root;
        const auto ledger = fixture.root / std::string(kQueueLedgerFileName);
        if (scenario == 1) inputRoot /= L"missing";
        if (scenario == 2) inputRoot.clear();
        if (scenario == 3) {
            assert(CreateDirectoryW((fixture.root / L"recording").c_str(), nullptr));
            const std::string legacy = R"({"schema_version":"desktop-upload-queue.v2","items":[{"local_recording_id":"generated-recording","directory_id":"directory","session_id":"session","package_directory":")" +
                (fixture.root / L"recording").generic_u8string() +
                R"(","status":0,"accepted_bytes":[0,0,0],"attempts":0,"safe_reason":"","owner_user_id":"","owner_workspace_id":"","meeting_id":""}]})";
            // Validate the generated legacy shape on a separate test-owned file.
            const auto control = fixture.root / L"legacy-control";
            writeFixture(control, legacy);
            { DesktopUploadQueueService parser(control, fixture.root);
              assert(parser.load() && parser.items().size() == 1); }
            assert(std::filesystem::remove(control));
            writeFixture(ledger, legacy);
        }
        if (scenario == 4) writeFixture(ledger, "{\"schema_version\":\"desktop-upload-queue.v2\",\"items\":[");
        if (scenario == 5) {
            // Raw synthetic reserved/prepared traces, NOT genuine protected envelopes.
            const auto custody = fixture.root / L".custody-v1";
            assert(CreateDirectoryW(custody.c_str(), nullptr));
            writeFixture(custody / L"store.id", std::string(16, '\x17'));
            for (const auto* role : {L"queue", L"migration-intent"}) {
                const auto directory = custody / role;
                assert(CreateDirectoryW(directory.c_str(), nullptr));
                writeFixture(directory / L"id.bin", std::string(16, '\x29'));
            }
            writeFixture(custody / L"migration-intent" / L"index.0",
                R"({"stage":"prepared","generation":1,"subject":"queue"})");
            writeFixture(custody / L"migration-intent" / L"index.1",
                R"({"stage":"prepared","generation":2,"subject":"queue"})");
        }
        if (scenario == 6) {
            writeFixture(ledger, std::string("\0\xff\x01", 3));
            writeFixture(fixture.root / L"unknown.bin", "generated opaque bytes");
        }
        if (scenario == 7) {
            const auto shortPackage = fixture.root / L"marked-short";
            assert(CreateDirectoryW(shortPackage.c_str(), nullptr));
            writeFixture(shortPackage / L"manifest.json",
                R"({"schema_version":"local-recording-manifest.v5","short_recording_discarded":true})");
            writeFixture(shortPackage / L"meeting-review.m4a", "generated non-audio bytes");
            assert(DesktopUploadQueueService::isShortRecordingMarked(shortPackage));
        }
        const auto before = snapshot(fixture.root);
        for (int restart = 0; restart != 2; ++restart) {
            {
                NativeCapture capture(inputRoot, {std::make_shared<GeneratedAec>(), false});
                assert(snapshot(fixture.root) == before);
                for (const bool updateBlocked : {false, true}) {
                    capture.setUpdateAdmissionBlocked(updateBlocked);
                    closedCalls(capture);
                    assert(snapshot(fixture.root) == before);
                }
                capture.setUpdateAdmissionBlocked(false);
                capture.shutdown();
                closedCalls(capture);
                assert(snapshot(fixture.root) == before);
            }
            assert(snapshot(fixture.root) == before);
        }
    }
}
} // namespace
int main() {
#if defined(_MSC_VER) && defined(_DEBUG)
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
#endif
    stageOneConstructor();
    rootMatrix();
    std::puts("NativeCaptureStartupTests: actual class closed-root matrix; NOT WinUI callbacks or injected flight proof");
    return 0;
}
