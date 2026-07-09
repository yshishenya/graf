import Foundation

public enum MeetingDetectionPolicyAction: Equatable, Sendable {
    case suppress(reason: String)
    case detectOnly(targetID: String?)
    case prompt(targetID: String)
    case autoRecord(targetID: String)
}

public struct MeetingDetectionCapturePrerequisites: Equatable, Sendable {
    public let recordingAlreadyActive: Bool
    public let visibleRecordingStateAvailable: Bool
    public let oneActionStopAvailable: Bool
    public let captureRouteReady: Bool

    public init(
        recordingAlreadyActive: Bool = false,
        visibleRecordingStateAvailable: Bool = true,
        oneActionStopAvailable: Bool = true,
        captureRouteReady: Bool = true
    ) {
        self.recordingAlreadyActive = recordingAlreadyActive
        self.visibleRecordingStateAvailable = visibleRecordingStateAvailable
        self.oneActionStopAvailable = oneActionStopAvailable
        self.captureRouteReady = captureRouteReady
    }

    public var allowsRecordingStart: Bool {
        !recordingAlreadyActive &&
            visibleRecordingStateAvailable &&
            oneActionStopAvailable &&
            captureRouteReady
    }
}

public struct MeetingDetectionPolicy: Sendable {
    public init() {}

    public func action(
        for decision: MeetingDetectionCandidateDecision,
        settings: MeetingDetectionSettingsSnapshot,
        prerequisites: MeetingDetectionCapturePrerequisites
    ) -> MeetingDetectionPolicyAction {
        guard settings.detectionMode != .disabled else {
            return .suppress(reason: "detection_disabled")
        }
        switch decision.kind {
        case .suppressed:
            return .suppress(reason: decision.suppressionReasons.first?.rawValue ?? "suppressed")
        case .candidateUpload:
            return .detectOnly(targetID: nil)
        case .knownTarget(let targetID, let mode):
            guard mode == .promptEnabled else {
                return .detectOnly(targetID: targetID)
            }
            if settings.detectionMode == .detectOnly {
                return .detectOnly(targetID: targetID)
            }
            guard prerequisites.allowsRecordingStart else {
                return .suppress(reason: "capture_prerequisite_blocked")
            }
            if settings.targetScopedAutoRecordEnabled,
               settings.autoRecordTargetIds.contains(targetID) {
                return .autoRecord(targetID: targetID)
            }
            return .prompt(targetID: targetID)
        }
    }

    public func action(
        for browserEvaluation: BrowserMeetingTargetEvaluation,
        settings: MeetingDetectionSettingsSnapshot,
        prerequisites: MeetingDetectionCapturePrerequisites
    ) -> MeetingDetectionPolicyAction {
        guard settings.detectionMode != .disabled else {
            return .suppress(reason: "detection_disabled")
        }
        switch browserEvaluation.kind {
        case .manualOnly(let targetID, _):
            return .detectOnly(targetID: targetID)
        case .safeJoinedTarget(let targetID, let mode):
            return action(
                for: MeetingDetectionCandidateDecision(
                    kind: .knownTarget(targetID: targetID, mode: mode),
                    candidateScore: 0,
                    candidateReasons: [.calendarOrJoinHint]
                ),
                settings: settings,
                prerequisites: prerequisites
            )
        }
    }
}

public struct MeetingDetectionSettingsSnapshot: Equatable, Sendable {
    public let detectionMode: MeetingDetectionMode
    public let targetScopedAutoRecordEnabled: Bool
    public let autoRecordTargetIds: Set<String>

    public init(
        detectionMode: MeetingDetectionMode = .detectAndAsk,
        targetScopedAutoRecordEnabled: Bool = false,
        autoRecordTargetIds: Set<String> = []
    ) {
        self.detectionMode = detectionMode
        self.targetScopedAutoRecordEnabled = targetScopedAutoRecordEnabled
        self.autoRecordTargetIds = autoRecordTargetIds
    }
}
