import Foundation

public enum AudioDirection: String, Codable, Sendable {
    case input
    case output
    case duplex
}

public enum PhysicalDeviceClass: String, Codable, Sendable {
    case builtIn = "built_in"
    case wired
    case usb
    case bluetooth
    case airpodsClass = "airpods_class"
    case unknown
}

public enum VirtualDeviceAvailabilityState: String, Codable, Sendable {
    case missing
    case installed
    case available
    case unavailable
    case hidden
    case incompatible
    case requiresRestart = "requires_restart"
}

public enum PhysicalDeviceAvailabilityState: String, Codable, Sendable {
    case available
    case disconnected
    case muted
    case silent
    case noisy
    case profileSwitching = "profile_switching"
    case unsupported
}

public enum RoutePath: String, Codable, Sendable {
    case micToVirtualInput = "mic_to_virtual_input"
    case remoteOutputToVirtualSpeaker = "remote_output_to_virtual_speaker"
    case speakerPassthrough = "speaker_passthrough"
    case captureMirror = "capture_mirror"
}

public enum RouteValidationType: String, Codable, Sendable {
    case syntheticSignal = "synthetic_signal"
    case browserMeeting = "browser_meeting"
    case testRecording = "test_recording"
    case testPlayback = "test_playback"
    case appIOHeartbeat = "app_io_heartbeat"
    case latencyProbe = "latency_probe"
    case bluetoothPilot = "bluetooth_pilot"
}

public enum RouteVerificationStatus: String, Codable, Sendable {
    case notStarted = "not_started"
    case running
    case passed
    case failed
    case stale
}

public enum LiveRouteReadinessStatus: String, Codable, Sendable {
    case notStarted = "not_started"
    case checking
    case ready
    case stale
    case degraded
    case failed
}

public enum LivePassthroughStatus: String, Codable, Sendable {
    case inactive
    case checking
    case ready
    case active
    case stale
    case degraded
    case failed
    case blocked
}

public enum PassthroughFailureReason: String, Codable, Sendable {
    case none
    case permissionDenied = "permission_denied"
    case muted
    case silent
    case unavailable
    case selfRouted = "self_routed"
    case aggregateUnmanaged = "aggregate_unmanaged"
    case deviceChanged = "device_changed"
    case appHeartbeatMissing = "app_heartbeat_missing"
    case coreaudiodRestarted = "coreaudiod_restarted"
    case latencyExceeded = "latency_exceeded"
    case leakageExceeded = "leakage_exceeded"
    case unknown
}

public enum RouteRecoveryEventType: String, Codable, Sendable {
    case physicalInputChanged = "physical_input_changed"
    case physicalOutputChanged = "physical_output_changed"
    case browserTargetChanged = "browser_target_changed"
    case bluetoothProfileChanged = "bluetooth_profile_changed"
    case appHeartbeatLost = "app_heartbeat_lost"
    case appHeartbeatRestored = "app_heartbeat_restored"
    case driverReloaded = "driver_reloaded"
    case coreaudiodRestarted = "coreaudiod_restarted"
}

public enum RouteEvidenceStatus: String, Codable, Sendable {
    case notStarted = "not_started"
    case passed
    case blocked
    case degraded
    case failed
}

public enum BrowserTargetEvidenceStatus: String, Codable, Sendable {
    case passed
    case blocked
    case notAccepted = "not_accepted"
}

public enum ReleaseHardeningResult: String, Codable, Sendable {
    case passed
    case blocked
    case notAccepted = "not_accepted"
}

public enum MeasurementStatus: String, Codable, Sendable {
    case passed
    case degraded
    case blocked
}

public enum IntelligibilityStatus: String, Codable, Sendable {
    case notIntelligible = "not_intelligible"
    case intelligible
    case unknown
}

public enum RouteInvalidationSource: String, Codable, Sendable {
    case physicalDevice = "physical_device"
    case outputRoute = "output_route"
    case browserTarget = "browser_target"
    case bluetoothProfile = "bluetooth_profile"
    case appIO = "app_io"
    case coreaudiod
}

public enum CaptureMode: String, Codable, Sendable {
    case audioRecording = "audio_recording"
    case transcriptOnly = "transcript_only"
}

public enum CaptureSessionState: String, Codable, Sendable {
    case idle
    case detecting
    case ready
    case starting
    case active
    case paused
    case degraded
    case stopping
    case stopped
    case failed
    case finalized
}

public enum SourceAppEligibility: String, Codable, Sendable {
    case eligible
    case ineligible
    case unknown
}

public enum VisibleIndicatorState: String, Codable, Sendable {
    case hidden
    case ready
    case active
    case paused
    case degraded
    case error
}

public enum AudioTrackRole: String, Codable, Sendable {
    case localMic = "local_mic"
    case remoteSpeaker = "remote_speaker"
}

public enum AudioTrackState: String, Codable, Sendable {
    case pending
    case capturing
    case degraded
    case missing
    case finalized
}

public enum LocalBufferArtifactType: String, Codable, Sendable {
    case audioChunk = "audio_chunk"
    case trackManifest = "track_manifest"
    case sessionManifest = "session_manifest"
    case diagnosticManifest = "diagnostic_manifest"
}

public enum UploadState: String, Codable, Sendable {
    case notReady = "not_ready"
    case queued
    case uploading
    case uploaded
    case failed
    case serverUnavailable = "server_unavailable"
    case networkUnavailable = "network_unavailable"
}

public enum PurgeState: String, Codable, Sendable {
    case retained
    case pendingPurge = "pending_purge"
    case purged
    case purgeFailed = "purge_failed"
    case expiredUnreachable = "expired_unreachable"
}

public enum DeletionReportState: String, Codable, Sendable {
    case notRequested = "not_requested"
    case acknowledged
    case pendingClient = "pending_client"
    case outsideControl = "outside_control"
}

public enum DriverInstallationState: String, Codable, Sendable {
    case notInstalled = "not_installed"
    case installed
    case needsRepair = "needs_repair"
    case needsUpdate = "needs_update"
    case incompatible
    case uninstalling
    case uninstalled
    case requiresRestart = "requires_restart"
}

public enum PassthroughStatus: String, Codable, Sendable {
    case healthy
    case degraded
    case failed
    case appIOMissing = "app_io_missing"
    case latencyExceeded = "latency_exceeded"
    case mutedByPhysicalDevice = "muted_by_physical_device"
    case physicalDeviceMissing = "physical_device_missing"
    case unknown
}

public enum AppIOState: String, Codable, Sendable {
    case unavailable
    case waitingForApp = "waiting_for_app"
    case connected
    case heartbeatLost = "heartbeat_lost"
    case recovering
}

public enum CapturabilityStatus: String, Codable, Sendable {
    case capturable
    case notCapturable = "not_capturable"
    case unknown
}

public enum BluetoothProfileState: String, Codable, Sendable {
    case stable
    case switching
    case oneSidedAudio = "one_sided_audio"
    case unsupported
    case unknown
}

public enum DiagnosticRedactionStatus: String, Codable, Sendable {
    case redacted
    case blockedSensitiveContent = "blocked_sensitive_content"
    case adminContentEnabled = "admin_content_enabled"
}

public enum InstallerOperation: String, Codable, Sendable {
    case install
    case update
    case repair
    case rollback
    case uninstall
}

public enum InstallerOperationState: String, Codable, Sendable {
    case notStarted = "not_started"
    case running
    case requiresPermission = "requires_permission"
    case requiresRestart = "requires_restart"
    case succeeded
    case failed
    case partiallyCompleted = "partially_completed"
    case deferredActiveCall = "deferred_active_call"
}
