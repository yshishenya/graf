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
    public let recordingPrerequisite: RecordingPrerequisiteSnapshot?

    public init(
        recordingAlreadyActive: Bool = false,
        visibleRecordingStateAvailable: Bool = true,
        oneActionStopAvailable: Bool = true,
        captureRouteReady: Bool = true,
        recordingPrerequisite: RecordingPrerequisiteSnapshot? = nil
    ) {
        self.recordingAlreadyActive = recordingAlreadyActive
        self.visibleRecordingStateAvailable = visibleRecordingStateAvailable
        self.oneActionStopAvailable = oneActionStopAvailable
        self.captureRouteReady = captureRouteReady
        self.recordingPrerequisite = recordingPrerequisite
    }

    public var allowsRecordingStart: Bool {
        !recordingAlreadyActive &&
            visibleRecordingStateAvailable &&
            oneActionStopAvailable &&
            captureRouteReady &&
            (recordingPrerequisite?.allowsRecording ?? true)
    }

    public var blockedReasonCode: String {
        if recordingAlreadyActive {
            return RecordingStartBlocker.alreadyRecording.rawValue
        }
        if !visibleRecordingStateAvailable {
            return RecordingStartBlocker.indicatorUnavailable.rawValue
        }
        if !oneActionStopAvailable {
            return "one_action_stop_unavailable"
        }
        if !captureRouteReady {
            return RecordingStartBlocker.captureUnavailable.rawValue
        }
        if let recordingPrerequisite, recordingPrerequisite.blockedReason != .none {
            return recordingPrerequisite.blockedReason.rawValue
        }
        return "capture_prerequisite_blocked"
    }
}

public struct MeetingDetectionPolicy: Sendable {
    public init() {}

    public func action(
        for decision: MeetingDetectionCandidateDecision,
        settings: MeetingDetectionSettingsSnapshot,
        prerequisites: MeetingDetectionCapturePrerequisites
    ) -> MeetingDetectionPolicyAction {
        switch decision.kind {
        case .suppressed:
            return .suppress(reason: decision.suppressionReasons.first?.rawValue ?? "suppressed")
        case .candidateUpload:
            return .detectOnly(targetID: nil)
        case .knownTarget(let targetID, let mode):
            guard mode == .promptEnabled else {
                return .detectOnly(targetID: targetID)
            }
            guard settings.detectionMode == .detectAndAsk else {
                return .detectOnly(targetID: targetID)
            }
            if settings.recordingRule(for: targetID) == .never {
                return .suppress(reason: "target_policy_never")
            }
            guard prerequisites.allowsRecordingStart else {
                return .suppress(reason: prerequisites.blockedReasonCode)
            }
            switch settings.recordingRule(for: targetID) {
            case .never:
                return .suppress(reason: "target_policy_never")
            case .always where settings.assistedAutoStartAuthorized:
                return .autoRecord(targetID: targetID)
            case .always:
                return .suppress(reason: "assisted_auto_start_unauthorized")
            case .ask:
                return .prompt(targetID: targetID)
            }
        }
    }

    public func action(
        for browserEvaluation: BrowserMeetingTargetEvaluation,
        settings: MeetingDetectionSettingsSnapshot,
        prerequisites: MeetingDetectionCapturePrerequisites
    ) -> MeetingDetectionPolicyAction {
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
    public let automaticRecordingRules: [String: AutomaticRecordingRule]
    public let assistedAutoStartAuthorized: Bool

    public init(
        detectionMode: MeetingDetectionMode = .detectAndAsk,
        targetScopedAutoRecordEnabled: Bool = false,
        autoRecordTargetIds: Set<String> = [],
        automaticRecordingRules: [String: AutomaticRecordingRule] = [:],
        assistedAutoStartAuthorized: Bool = false
    ) {
        self.detectionMode = detectionMode
        self.targetScopedAutoRecordEnabled = targetScopedAutoRecordEnabled
        self.autoRecordTargetIds = autoRecordTargetIds
        self.automaticRecordingRules = automaticRecordingRules
        self.assistedAutoStartAuthorized = assistedAutoStartAuthorized
    }

    public func recordingRule(for targetID: String) -> AutomaticRecordingRule {
        if let rule = automaticRecordingRules[targetID] {
            return rule
        }
        guard automaticRecordingRules.isEmpty else { return .ask }
        return targetScopedAutoRecordEnabled && autoRecordTargetIds.contains(targetID)
            ? .always
            : .ask
    }
}
