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
    case aggregate
    case multiOutput = "multi_output"
    case hdmiAirplay = "hdmi_airplay"
    case otherVirtual = "other_virtual"
    case unknown
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
    case policyBlocked = "policy_blocked"
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
    case derivedLocalMic = "derived_local_mic"
    case mixedMeetingAudio = "mixed_meeting_audio"
    case reviewPlayback = "review_playback"
}

public enum AudioTrackState: String, Codable, Sendable {
    case pending
    case capturing
    case degraded
    case missing
    case finalized
}

public enum RecordingStartBlocker: String, Codable, Sendable {
    case none
    case captureUnavailable = "capture_unavailable"
    case policyDisabled = "policy_disabled"
    case permissionDenied = "permission_denied"
    case storageUnsafe = "storage_unsafe"
    case indicatorUnavailable = "indicator_unavailable"
    case sourceAppIneligible = "source_app_ineligible"
    case alreadyRecording = "already_recording"
    case captureFailed = "capture_failed"
    case unknown
}

public enum RecordingStopReason: String, Codable, Sendable {
    case userRequested = "user_requested"
    case meetingEnded = "meeting_ended"
    case indicatorLost = "indicator_lost"
    case storageUnsafe = "storage_unsafe"
    case appRestarted = "app_restarted"
    case failed
}

public enum RecordingEvidenceEventType: String, Codable, Sendable {
    case startRequested = "recording.start_requested"
    case startBlocked = "recording.start_blocked"
    case started = "recording.started"
    case stopRequested = "recording.stop_requested"
    case stopped = "recording.stopped"
    case failed = "recording.failed"
    case indicatorLost = "recording.indicator_lost"
    case storageBlocked = "recording.storage_blocked"
}

public enum RecordingEvidenceInitiator: String, Codable, Sendable {
    case user
    case systemFailClosed = "system_fail_closed"
    case recovery
    case validation
}

public enum LocalRecordingSessionStatus: String, Codable, Sendable {
    case active
    case saved
    case degraded
    case blocked
    case failed
}

public enum LocalRecordingTrackStatus: String, Codable, Sendable {
    case pending
    case recording
    case saved
    case missing
    case degraded
    case blocked
    case failed
}

public enum LocalRecordingFailureReason: String, Codable, Sendable {
    case none
    case directoryUnavailable = "directory_unavailable"
    case writeFailed = "write_failed"
    case finalizationFailed = "finalization_failed"
    case emptyRequiredTrack = "empty_required_track"
    case formatNotReady = "format_not_ready"
    /// Kept only to decode historical manifests. New capture code never emits
    /// this generic reason; it uses the concrete capture/finalization outcome.
    case timelineMisaligned = "timeline_misaligned"
    case permissionDenied = "permission_denied"
    case scopeUnavailable = "scope_unavailable"
    case protectedAudioBlocked = "protected_audio_blocked"
    case silentInput = "silent_input"
    case noFrames = "no_frames"
    case captureFailed = "capture_failed"
    case cpuGateFailed = "cpu_gate_failed"
    case stoppedBeforeFrames = "stopped_before_frames"
    case deviceUnavailable = "device_unavailable"
    case appClosed = "app_closed"
    case historicalPackage = "historical_package"
    case unknown

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let rawValue = try container.decode(String.self)

        self = Self(rawValue: rawValue) ?? .historicalPackage
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(rawValue)
    }
}

public enum MuteTruthArtifactState: String, Codable, CaseIterable, Sendable {
    case muteRespecting = "mute_respecting"
    case meetingMuteUnproven = "meeting_mute_unproven"
    case unsupported
    case deferred
    case degraded
    case failed
}

public enum TranscriptionReadinessState: String, Codable, Sendable {
    case ready
    case degraded
    case failed
    case historicalPackage = "historical_package"

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        self = Self(rawValue: try container.decode(String.self)) ?? .historicalPackage
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(rawValue)
    }
}

public enum MediaScribeTrackField: String, Codable, Sendable {
    case micFile = "mic_file"
    case incomingFile = "incoming_file"
    case derivedMicFile = "derived_mic_file"
    case mixedAudioFile = "mixed_audio_file"
    case mediaFile = "media_file"
    case playbackFile = "playback_file"
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
    case retrying
    case uploaded
    case degraded
    case failed
    case blocked
    case terminalDeleted = "terminal_deleted"
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

public enum CapturabilityStatus: String, Codable, Sendable {
    case capturable
    case notCapturable = "not_capturable"
    case unknown
}

public enum DiagnosticRedactionStatus: String, Codable, Sendable {
    case redacted
    case blockedSensitiveContent = "blocked_sensitive_content"
    case adminContentEnabled = "admin_content_enabled"
}
