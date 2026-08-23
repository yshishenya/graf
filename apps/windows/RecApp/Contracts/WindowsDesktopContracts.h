#pragma once

#include <array>
#include <cstdint>
#include <string_view>

namespace graf::windows {

inline constexpr std::string_view kManifestSchemaVersion = "local-recording-manifest.v5";
inline constexpr std::string_view kCanonicalMixProfile = "canonical-mix.v1";
inline constexpr std::string_view kV5SourceKind = "initial_mixed_recording";
inline constexpr std::string_view kV5MediaScribeSourceMode = "single_wav_v1";
inline constexpr std::string_view kQueueSchemaVersion = "desktop-upload-queue.v2";
inline constexpr std::string_view kBridgeProtocol = "graf.desktop.bridge";
inline constexpr std::uint32_t kBridgeProtocolVersion = 1;
inline constexpr std::size_t kBridgeMaxSerializedBytes = 64 * 1024;
inline constexpr std::size_t kBridgeMaxPayloadDepth = 8;

inline constexpr std::array<std::string_view, 3> kV5WireRoles = {
    "manifest", "media", "playback",
};

enum class SessionState {
    idle,
    checkingReadiness,
    ready,
    starting,
    recording,
    paused,
    degraded,
    stopping,
    finalizing,
    savedLocal,
    queued,
    uploaded,
    blocked,
    failed,
};

enum class ReasonCode {
    none,
    activeSessionExists,
    recordingPolicyBlocked,
    microphonePermissionDenied,
    microphoneEndpointUnavailable,
    renderEndpointUnavailable,
    formatNormalizationUnavailable,
    aecUnavailable,
    storageUnavailable,
    webViewRuntimeUnavailable,
    aacEncoderUnavailable,
    endpointInvalidated,
    clockDiscontinuity,
    queueOverflow,
    finalizationFailed,
    malformedLedger,
    authRequired,
    networkUnavailable,
    localPurgeUnverified,
};

enum class ArtifactRole {
    manifest,
    media,
    playback,
};

enum class TransitionStatus {
    accepted,
    idempotent,
    rejected,
};

struct TransitionResult {
    TransitionStatus status = TransitionStatus::rejected;
    SessionState state = SessionState::idle;
    ReasonCode reason = ReasonCode::none;

    [[nodiscard]] bool accepted() const noexcept {
        return status != TransitionStatus::rejected;
    }
};

[[nodiscard]] constexpr bool isCaptureState(SessionState state) noexcept {
    return state == SessionState::starting || state == SessionState::recording ||
           state == SessionState::paused || state == SessionState::degraded ||
           state == SessionState::stopping || state == SessionState::finalizing;
}

[[nodiscard]] constexpr std::string_view toString(SessionState state) noexcept {
    switch (state) {
    case SessionState::idle: return "idle";
    case SessionState::checkingReadiness: return "checking_readiness";
    case SessionState::ready: return "ready";
    case SessionState::starting: return "starting";
    case SessionState::recording: return "recording";
    case SessionState::paused: return "paused";
    case SessionState::degraded: return "degraded";
    case SessionState::stopping: return "stopping";
    case SessionState::finalizing: return "finalizing";
    case SessionState::savedLocal: return "saved_local";
    case SessionState::queued: return "queued";
    case SessionState::uploaded: return "uploaded";
    case SessionState::blocked: return "blocked";
    case SessionState::failed: return "failed";
    }
    return "unknown";
}

[[nodiscard]] constexpr std::string_view toString(ReasonCode reason) noexcept {
    switch (reason) {
    case ReasonCode::none: return "none";
    case ReasonCode::activeSessionExists: return "active_session_exists";
    case ReasonCode::recordingPolicyBlocked: return "recording_policy_blocked";
    case ReasonCode::microphonePermissionDenied: return "microphone_permission_denied";
    case ReasonCode::microphoneEndpointUnavailable: return "microphone_endpoint_unavailable";
    case ReasonCode::renderEndpointUnavailable: return "render_endpoint_unavailable";
    case ReasonCode::formatNormalizationUnavailable: return "format_normalization_unavailable";
    case ReasonCode::aecUnavailable: return "aec_unavailable";
    case ReasonCode::storageUnavailable: return "storage_unavailable";
    case ReasonCode::webViewRuntimeUnavailable: return "webview_runtime_unavailable";
    case ReasonCode::aacEncoderUnavailable: return "aac_encoder_unavailable";
    case ReasonCode::endpointInvalidated: return "endpoint_invalidated";
    case ReasonCode::clockDiscontinuity: return "clock_discontinuity";
    case ReasonCode::queueOverflow: return "queue_overflow";
    case ReasonCode::finalizationFailed: return "finalization_failed";
    case ReasonCode::malformedLedger: return "malformed_ledger";
    case ReasonCode::authRequired: return "auth_required";
    case ReasonCode::networkUnavailable: return "network_unavailable";
    case ReasonCode::localPurgeUnverified: return "local_purge_unverified";
    }
    return "unknown";
}

} // namespace graf::windows
