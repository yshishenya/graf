import Foundation
import TwoBrainRecShared

public struct MacOSMicAttributionLogStreamConfiguration: Equatable, Sendable {
    public let executableURL: URL
    public let arguments: [String]

    public init(
        executableURL: URL = URL(fileURLWithPath: "/usr/bin/log"),
        arguments: [String] = [
            "stream",
            "--style",
            "compact",
            "--predicate",
            "eventMessage CONTAINS[c] 'sensor-indicators' OR eventMessage CONTAINS[c] 'sensor indicators'"
        ]
    ) {
        self.executableURL = executableURL
        self.arguments = arguments
    }
}

public enum MacOSMeetingActivityDetectorOutput: Equatable, Sendable {
    case promptEligible(targetID: String, bundleID: String)
    case autoRecordEligible(targetID: String, bundleID: String)
    case candidateObserved(
        bundleID: String,
        score: Int,
        observation: MeetingDetectionAppObservation,
        decision: MeetingDetectionCandidateDecision
    )
    case suppressed(bundleID: String, reason: String)
    case ended(bundleID: String)
}

public final class MacOSMeetingActivityDetector: @unchecked Sendable {
    public typealias Clock = @Sendable () -> Date

    private let filter: MeetingDetectionCandidateFilter
    private let policy: MeetingDetectionPolicy
    private let debounceSeconds: TimeInterval
    private let endGraceSeconds: TimeInterval
    private let clock: Clock
    private var trackedEvents: [String: TrackedMicAttribution] = [:]
    private var emittedBundles: Set<String> = []

    public init(
        filter: MeetingDetectionCandidateFilter = MeetingDetectionCandidateFilter(),
        policy: MeetingDetectionPolicy = MeetingDetectionPolicy(),
        debounceSeconds: TimeInterval = 5,
        endGraceSeconds: TimeInterval = 15,
        clock: @escaping Clock = Date.init
    ) {
        self.filter = filter
        self.policy = policy
        self.debounceSeconds = debounceSeconds
        self.endGraceSeconds = endGraceSeconds
        self.clock = clock
    }

    public func handle(
        event: MacOSMicAttributionEvent,
        registry: MeetingTargetRegistryDocument,
        settings: MeetingDetectionSettings,
        prerequisites: MeetingDetectionCapturePrerequisites = MeetingDetectionCapturePrerequisites()
    ) -> [MacOSMeetingActivityDetectorOutput] {
        switch event.state {
        case .active:
            if var tracked = trackedEvents[event.bundleID] {
                tracked.latestEvent = event
                tracked.inactiveAt = nil
                tracked.stableObservationCount += 1
                trackedEvents[event.bundleID] = tracked
            } else {
                trackedEvents[event.bundleID] = TrackedMicAttribution(event: event)
            }
            return []
        case .inactive:
            guard var tracked = trackedEvents[event.bundleID] else {
                return []
            }
            tracked.latestEvent = event
            tracked.inactiveAt = event.observedAt
            trackedEvents[event.bundleID] = tracked
            return advance(
                now: event.observedAt,
                registry: registry,
                settings: settings,
                prerequisites: prerequisites
            )
        }
    }

    public func advance(
        now: Date? = nil,
        registry: MeetingTargetRegistryDocument,
        settings: MeetingDetectionSettings,
        prerequisites: MeetingDetectionCapturePrerequisites = MeetingDetectionCapturePrerequisites()
    ) -> [MacOSMeetingActivityDetectorOutput] {
        let value = now ?? clock()
        var outputs: [MacOSMeetingActivityDetectorOutput] = []
        for tracked in trackedEvents.values {
            if let inactiveAt = tracked.inactiveAt {
                guard value.timeIntervalSince(inactiveAt) >= endGraceSeconds else {
                    continue
                }
                trackedEvents.removeValue(forKey: tracked.bundleID)
                if emittedBundles.remove(tracked.bundleID) != nil {
                    outputs.append(.ended(bundleID: tracked.bundleID))
                }
                continue
            }

            guard !emittedBundles.contains(tracked.bundleID),
                  value.timeIntervalSince(tracked.firstObservedAt) >= debounceSeconds
            else {
                continue
            }
            let output = outputForStableEvent(
                tracked,
                activeUntil: value,
                registry: registry,
                settings: settings,
                prerequisites: prerequisites
            )
            if shouldMarkEmitted(output) {
                emittedBundles.insert(tracked.bundleID)
            }
            if let output {
                outputs.append(output)
            }
        }
        return outputs
    }

    public func purgeStaleInactive(now: Date? = nil) {
        let value = now ?? clock()
        for tracked in trackedEvents.values {
            guard let inactiveAt = tracked.inactiveAt,
                  value.timeIntervalSince(inactiveAt) >= endGraceSeconds
            else {
                continue
            }
            trackedEvents.removeValue(forKey: tracked.bundleID)
            emittedBundles.remove(tracked.bundleID)
        }
    }

    private func outputForStableEvent(
        _ tracked: TrackedMicAttribution,
        activeUntil: Date,
        registry: MeetingTargetRegistryDocument,
        settings: MeetingDetectionSettings,
        prerequisites: MeetingDetectionCapturePrerequisites
    ) -> MacOSMeetingActivityDetectorOutput? {
        let event = tracked.latestEvent
        let observation = MeetingDetectionAppObservation(
            bundleID: event.bundleID,
            displayName: event.displayName ?? registry.target(forBundleID: event.bundleID)?.displayName ?? event.bundleID,
            stableObservationCount: max(2, tracked.stableObservationCount),
            activeDurationSeconds: activeUntil.timeIntervalSince(tracked.firstObservedAt)
        )
        let decision = filter.evaluate(
            observation: observation,
            registry: registry,
            uploadMode: settings.uploadMode
        )
        switch policy.action(
            for: decision,
            settings: settings.policySnapshot,
            prerequisites: prerequisites
        ) {
        case .prompt(let targetID):
            return .promptEligible(targetID: targetID, bundleID: event.bundleID)
        case .autoRecord(let targetID):
            return .autoRecordEligible(targetID: targetID, bundleID: event.bundleID)
        case .detectOnly:
            if decision.shouldUploadCandidateIdentity {
                return .candidateObserved(
                    bundleID: event.bundleID,
                    score: decision.candidateScore,
                    observation: observation,
                    decision: decision
                )
            }
            return shouldEmitSoftSuppression(decision)
                ? nil
                : .suppressed(bundleID: event.bundleID, reason: "detect_only")
        case .suppress(let reason):
            return shouldEmitSoftSuppression(decision)
                ? nil
                : .suppressed(bundleID: event.bundleID, reason: reason)
        }
    }

    private func shouldMarkEmitted(_ output: MacOSMeetingActivityDetectorOutput?) -> Bool {
        switch output {
        case .promptEligible, .autoRecordEligible, .candidateObserved, .suppressed:
            true
        case .ended, nil:
            false
        }
    }

    private func shouldEmitSoftSuppression(_ decision: MeetingDetectionCandidateDecision) -> Bool {
        guard case .suppressed = decision.kind,
              !decision.suppressionReasons.isEmpty
        else {
            return false
        }
        let softReasons: Set<MeetingDetectionSuppressionReason> = [.shortDuration, .lowScore]
        return decision.suppressionReasons.allSatisfy { softReasons.contains($0) }
    }
}

private struct TrackedMicAttribution: Sendable {
    let firstObservedAt: Date
    var latestEvent: MacOSMicAttributionEvent
    var inactiveAt: Date?
    var stableObservationCount: Int

    var bundleID: String { latestEvent.bundleID }

    init(event: MacOSMicAttributionEvent) {
        firstObservedAt = event.observedAt
        latestEvent = event
        inactiveAt = nil
        stableObservationCount = 1
    }
}

public extension MeetingDetectionSettings {
    var policySnapshot: MeetingDetectionSettingsSnapshot {
        MeetingDetectionSettingsSnapshot(
            detectionMode: detectionMode,
            targetScopedAutoRecordEnabled: targetScopedAutoRecordEnabled,
            autoRecordTargetIds: autoRecordTargetIds
        )
    }
}
