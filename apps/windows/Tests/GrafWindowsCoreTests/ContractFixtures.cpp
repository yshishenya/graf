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

    const auto readiness = WindowsReadinessGate::evaluate({true, true, true, true, true, true, true, false, true});
    assert(readiness.recordingReady);
    assert(!readiness.webViewReady);
    const auto blocked = WindowsReadinessGate::evaluate({true, true, true, true, true, true, true, true, false});
    assert(!blocked.recordingReady);
    assert(blocked.blockers[0] == ReasonCode::aacEncoderUnavailable);

    const auto diagnostics = MetadataSafeDiagnostics::serialize({
        "0.1.0", "19045", "x64", SessionState::recording, ReasonCode::none,
        1, 2, 3000, "endpoint-id",
    });
    assert(diagnostics.find("endpoint-id") == std::string::npos);
    assert(diagnostics.find("endpoint_fingerprint") != std::string::npos);

    const auto path = std::filesystem::temp_directory_path() / "graf-feature-200-contract-fixture.json";
    const auto writeResult = AtomicFileStore::write(path, "{\"state\":\"ready\"}");
    assert(writeResult.ok());
    std::ifstream input(path, std::ios::binary);
    const std::string contents((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    assert(contents == "{\"state\":\"ready\"}");
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
