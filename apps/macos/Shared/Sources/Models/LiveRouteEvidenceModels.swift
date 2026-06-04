import Foundation

public enum MeetingTarget: String, Codable, CaseIterable, Sendable {
    case chrome
    case opera
    case zoom
    case telemost
}

public enum LiveRouteState: String, Codable, Sendable {
    case inactive
    case armed
    case starting
    case active
    case preserved
    case recovering
    case healthyAfterFreshEvidence = "healthy_after_fresh_evidence"
    case stale
    case degraded
    case blocked
    case failed
    case released
    case stopped
}

public enum RouteObservationSource: String, Codable, Sendable {
    case routeEngine = "route_engine"
    case validationScript = "validation_script"
    case recordingManifest = "recording_manifest"
    case diagnosticBundle = "diagnostic_bundle"
}

public enum RouteEvidenceFamily: String, Codable, CaseIterable, Sendable {
    case routeLifecycle = "route_lifecycle"
    case clientActivity = "client_activity"
    case defaultRoute = "default_route"
    case frameContinuity = "frame_continuity"
    case autorepair = "autorepair"
    case releaseDecision = "release_decision"
    case recordingTimeline = "recording_timeline"
    case validationRun = "validation_run"
    case userAction = "user_action"
}

public enum RouteReleaseReason: String, Codable, Sendable {
    case meetingClientClosed = "meeting_client_closed"
    case userStopped = "user_stopped"
    case appShutdown = "app_shutdown"
    case nonRecoverableBlocked = "non_recoverable_blocked"
    case deniedActiveClient = "denied_active_client"
    case deniedAmbiguousEvidence = "denied_ambiguous_evidence"
    case deniedStaleEvidence = "denied_stale_evidence"
}

public enum RouteReleaseOutcome: String, Codable, Sendable {
    case keepActive = "keep_active"
    case denied
    case released
}

public enum RouteInterruptionCategory: String, Codable, Sendable {
    case none
    case autorepairCovered = "autorepair_covered"
    case routeGap = "route_gap"
    case trackGap = "track_gap"
    case userStopped = "user_stopped"
    case blockedNonRecoverable = "blocked_non_recoverable"
    case failedUnknown = "failed_unknown"
}

public enum TimelineAlignmentBand: String, Codable, Sendable {
    case accepted
    case degradedWarning = "degraded_warning"
    case failed
}

public enum DurationGate: String, Codable, Sendable {
    case development30Minute = "development_30_minute"
    case release75Minute = "release_75_minute"
    case autorepairScenario = "autorepair_scenario"
    case recordingArtifact = "recording_artifact"
    case localOffline = "local_offline"
}

public enum ValidationResult: String, Codable, Sendable {
    case accepted
    case blocked
    case failed
    case degraded
    case notTested = "not_tested"
}

public enum UserActionKind: String, Codable, Sendable {
    case runCheck = "run_check"
    case startRecording = "start_recording"
    case stopRecording = "stop_recording"
    case changeMeetingDevice = "change_meeting_device"
    case openDiagnostics = "open_diagnostics"
}

public struct LiveRouteSession: Codable, Equatable, Sendable {
    public let sessionId: String
    public let target: MeetingTarget
    public let state: LiveRouteState
    public let startedAt: Date
    public let endedAt: Date?

    public init(sessionId: String, target: MeetingTarget, state: LiveRouteState, startedAt: Date, endedAt: Date? = nil) {
        self.sessionId = sessionId
        self.target = target
        self.state = state
        self.startedAt = startedAt
        self.endedAt = endedAt
    }
}

public struct ClientActivitySnapshot: Codable, Equatable, Sendable {
    public let source: ClientActivitySource
    public let microphoneOpen: Bool
    public let microphoneRunning: Bool
    public let speakerOpen: Bool
    public let speakerRunning: Bool
    public let stillUsesVirtualMicrophone: Bool?
    public let stillUsesVirtualSpeaker: Bool?
    public let freshnessMs: Int
    public let naturalSilenceAllowed: Bool

    public init(source: ClientActivitySource, microphoneOpen: Bool, microphoneRunning: Bool, speakerOpen: Bool, speakerRunning: Bool, stillUsesVirtualMicrophone: Bool? = nil, stillUsesVirtualSpeaker: Bool? = nil, freshnessMs: Int, naturalSilenceAllowed: Bool) {
        self.source = source
        self.microphoneOpen = microphoneOpen
        self.microphoneRunning = microphoneRunning
        self.speakerOpen = speakerOpen
        self.speakerRunning = speakerRunning
        self.stillUsesVirtualMicrophone = stillUsesVirtualMicrophone
        self.stillUsesVirtualSpeaker = stillUsesVirtualSpeaker
        self.freshnessMs = freshnessMs
        self.naturalSilenceAllowed = naturalSilenceAllowed
    }

    public var hasFreshVirtualClientEvidence: Bool {
        freshnessMs >= 0 && freshnessMs <= 5_000
            && (stillUsesVirtualMicrophone != false)
            && (stillUsesVirtualSpeaker != false)
            && (microphoneOpen || speakerOpen || microphoneRunning || speakerRunning)
    }
}

public struct MacOSDefaultRouteSnapshot: Codable, Equatable, Sendable {
    public let inputDeviceId: String?
    public let inputDeviceClass: PhysicalDeviceClass
    public let outputDeviceId: String?
    public let outputDeviceClass: PhysicalDeviceClass
    public let observedAt: Date

    public init(inputDeviceId: String?, inputDeviceClass: PhysicalDeviceClass, outputDeviceId: String?, outputDeviceClass: PhysicalDeviceClass, observedAt: Date) {
        self.inputDeviceId = inputDeviceId
        self.inputDeviceClass = inputDeviceClass
        self.outputDeviceId = outputDeviceId
        self.outputDeviceClass = outputDeviceClass
        self.observedAt = observedAt
    }

    public var isAcceptedForAutomaticRouting: Bool {
        Self.acceptedDeviceClasses.contains(inputDeviceClass) && Self.acceptedDeviceClasses.contains(outputDeviceClass)
    }

    public static let acceptedDeviceClasses: Set<PhysicalDeviceClass> = [.builtIn, .wired, .usb]
}

public struct FrameContinuitySnapshot: Codable, Equatable, Sendable {
    public let microphoneFramesObserved: Int
    public let incomingFramesObserved: Int
    public let missingFrameCount: Int
    public let dropoutCount: Int
    public let windowMs: Int

    public init(microphoneFramesObserved: Int, incomingFramesObserved: Int, missingFrameCount: Int, dropoutCount: Int, windowMs: Int) {
        self.microphoneFramesObserved = microphoneFramesObserved
        self.incomingFramesObserved = incomingFramesObserved
        self.missingFrameCount = missingFrameCount
        self.dropoutCount = dropoutCount
        self.windowMs = windowMs
    }
}

public struct RouteReleaseDecision: Codable, Equatable, Sendable {
    public let outcome: RouteReleaseOutcome
    public let reason: RouteReleaseReason
    public let clientEvidenceFresh: Bool
    public let decidedAt: Date

    public init(outcome: RouteReleaseOutcome, reason: RouteReleaseReason, clientEvidenceFresh: Bool, decidedAt: Date) {
        self.outcome = outcome
        self.reason = reason
        self.clientEvidenceFresh = clientEvidenceFresh
        self.decidedAt = decidedAt
    }
}

public struct RecordingTimelineIntegrityEvidence: Codable, Equatable, Sendable {
    public let routeSessionId: String
    public let autorepairAttemptIds: [String]
    public let micDurationSeconds: Double
    public let incomingDurationSeconds: Double
    public let durationDifferenceSeconds: Double
    public let alignmentBand: TimelineAlignmentBand
    public let interruptionCategory: RouteInterruptionCategory

    public init(routeSessionId: String, autorepairAttemptIds: [String], micDurationSeconds: Double, incomingDurationSeconds: Double, interruptionCategory: RouteInterruptionCategory) {
        self.routeSessionId = routeSessionId
        self.autorepairAttemptIds = autorepairAttemptIds
        self.micDurationSeconds = micDurationSeconds
        self.incomingDurationSeconds = incomingDurationSeconds
        self.durationDifferenceSeconds = abs(micDurationSeconds - incomingDurationSeconds)
        self.alignmentBand = Self.band(forDurationDifferenceSeconds: abs(micDurationSeconds - incomingDurationSeconds))
        self.interruptionCategory = interruptionCategory
    }

    public static func band(forDurationDifferenceSeconds value: Double) -> TimelineAlignmentBand {
        if value <= 3 { return .accepted }
        if value <= 10 { return .degradedWarning }
        return .failed
    }
}

public struct ValidationRunEvidence: Codable, Equatable, Sendable {
    public let runId: String
    public let durationGate: DurationGate
    public let result: ValidationResult
    public let targetsCovered: [MeetingTarget]
    public let deviceClassesCovered: [PhysicalDeviceClass]
    public let userActionCount: Int
    public let startedAt: Date
    public let completedAt: Date?

    public init(runId: String, durationGate: DurationGate, result: ValidationResult, targetsCovered: [MeetingTarget], deviceClassesCovered: [PhysicalDeviceClass], userActionCount: Int, startedAt: Date, completedAt: Date? = nil) {
        self.runId = runId
        self.durationGate = durationGate
        self.result = result
        self.targetsCovered = targetsCovered
        self.deviceClassesCovered = deviceClassesCovered
        self.userActionCount = userActionCount
        self.startedAt = startedAt
        self.completedAt = completedAt
    }

    public var isAcceptedWithoutNormalUserActions: Bool {
        result == .accepted && userActionCount == 0
    }
}
