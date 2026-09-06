#include "../../RecApp/Contracts/WindowsDesktopContracts.h"
#include "../../RecApp/Core/WindowsDesktopSession.h"
#include "../../RecApp/Diagnostics/MetadataSafeDiagnostics.h"
#include "../../RecApp/Permissions/WindowsReadinessGate.h"
#include "../../RecApp/Storage/AtomicFileStore.h"
#include "../../RecApp/Upload/DesktopApiClient.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <array>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <utility>

int main() {
    using namespace graf::windows;

    assert(kManifestSchemaVersion == "local-recording-manifest.v5");
    assert(kCanonicalMixProfile == "canonical-mix.v1");
    assert(kQueueSchemaVersion == "desktop-upload-queue.v2");
    assert(kBridgeProtocol == "graf.desktop.bridge");
    assert(kBridgeProtocolVersion == 1);

    WindowsDesktopSession session("session-001");
    assert(session.beginReadinessCheck().accepted());
    WindowsDesktopSession second("session-002");
    assert(second.beginReadinessCheck().reason == ReasonCode::activeSessionExists);
    assert(session.markReady().accepted());
    assert(session.beginStart().accepted());
    assert(session.startRecording().accepted());
    assert(session.pause().accepted());
    assert(session.resume().accepted());
    assert(session.markDegraded(ReasonCode::clockDiscontinuity).accepted());
    assert(session.stop().accepted());
    assert(session.stop().status == TransitionStatus::idempotent);
    assert(session.beginFinalizing().accepted());
    assert(session.saveLocal().accepted());
    assert(session.queue().accepted());
    assert(session.upload().accepted());

    const std::array<std::pair<bool ReadinessInputs::*, ReasonCode>, 7> required = {{
        {&ReadinessInputs::microphonePermissionGranted, ReasonCode::microphonePermissionDenied},
        {&ReadinessInputs::microphoneEndpointReady, ReasonCode::microphoneEndpointUnavailable},
        {&ReadinessInputs::renderEndpointReady, ReasonCode::renderEndpointUnavailable},
        {&ReadinessInputs::formatNormalizationReady, ReasonCode::formatNormalizationUnavailable},
        {&ReadinessInputs::aecReady, ReasonCode::aecUnavailable},
        {&ReadinessInputs::storageWritable, ReasonCode::storageUnavailable},
        {&ReadinessInputs::aacEncoderReady, ReasonCode::aacEncoderUnavailable},
    }};
    const auto unavailable = WindowsReadinessGate::evaluate({});
    assert(!unavailable.recordingReady && unavailable.blockerCount == required.size());
    ReadinessInputs ready;
    for (const auto& [field, reason] : required) {
        (void)reason;
        ready.*field = true;
    }
    // Native technical readiness alone permits recording, with or without WebView.
    for (const bool webReady : {false, true}) {
        ready.webViewRuntimeReady = webReady;
        const auto readiness = WindowsReadinessGate::evaluate(ready);
        assert(readiness.recordingReady && readiness.blockerCount == 0);
        assert(readiness.webViewReady == webReady);
        for (const auto& [field, reason] : required) {
            auto denied = ready;
            denied.*field = false;
            const auto blocked = WindowsReadinessGate::evaluate(denied);
            assert(!blocked.recordingReady && blocked.blockerCount == 1);
            assert(blocked.blockers[0] == reason);
        }
    }

    const auto diagnostics = MetadataSafeDiagnostics::serialize({
        "0.1.0", "19045", "x64", SessionState::recording, ReasonCode::none,
        300, 300, 3000, "endpoint-id", false,
    });
    assert(diagnostics.find("endpoint-id") == std::string::npos);
    assert(diagnostics.find("endpoint_fingerprint") != std::string::npos);
    assert(diagnostics.find("\"processed_blocks\":300") != std::string::npos);
    assert(diagnostics.find("\"written_blocks\":300") != std::string::npos);
    assert(diagnostics.find("\"duration_ms\":3000") != std::string::npos);
    assert(diagnostics.find("\"trusted_prefix_retained\":false") != std::string::npos);
    assert(diagnostics.find("dropped_frames") == std::string::npos);
    assert(diagnostics.find("overflow_count") == std::string::npos);
    assert(diagnostics.size() <= 1024);

    const auto path = std::filesystem::temp_directory_path() / "graf-feature-200-contract-fixture.json";
    const auto writeResult = AtomicFileStore::write(path, "{\"state\":\"ready\"}");
    assert(writeResult.ok());
    std::ifstream input(path, std::ios::binary);
    const std::string contents((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    assert(contents == "{\"state\":\"ready\"}");
    input.close();
    std::filesystem::remove(path);

    const auto meeting = DesktopApiClient::createMeetingRequest("recording-001", "recording-001--initial", 60);
    assert(meeting.has_value());
    assert(meeting->sourceKind == kV5SourceKind);
    assert(meeting->mediaScribeSourceMode == kV5MediaScribeSourceMode);
    const auto upload = DesktopApiClient::uploadSessionRequest(
        std::array<std::uint64_t, 3>{100, 200, 300},
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef");
    assert(upload.has_value());
    assert(upload->expectedTracks[1] == "media");
    assert(DesktopApiClient::idempotencyKey("meeting", "recording-001", "session-001") ==
           "desktop-upload:meeting:recording-001:session-001");
    return 0;
}
