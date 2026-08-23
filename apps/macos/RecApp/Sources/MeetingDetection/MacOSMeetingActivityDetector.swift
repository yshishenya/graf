import Foundation
import TwoBrainRecShared

public struct MacOSAudioOwnershipLogStreamConfiguration: Equatable, Sendable {
    public static let defaultPredicate = "((process == 'runningboardd' OR process == 'RunningBoard') AND (eventMessage CONTAINS[c] 'AudioHAL' OR composedMessage CONTAINS[c] 'AudioHAL')) OR (subsystem == 'com.apple.controlcenter' AND category == 'sensor-indicators' AND eventMessage BEGINSWITH 'Active activity attributions changed to ')"
    public static let snapshotPredicate = "process == 'ControlCenter' AND subsystem == 'com.apple.controlcenter' AND category == 'sensor-indicators' AND eventMessage BEGINSWITH 'Active activity attributions changed to '"

    public let executableURL: URL
    public let arguments: [String]
    public let snapshotArguments: [String]
    public let snapshotTimeoutNanoseconds: UInt64
    public let restartDelayNanoseconds: UInt64

    public init(
        executableURL: URL = URL(fileURLWithPath: "/usr/bin/log"),
        arguments: [String]? = nil,
        snapshotArguments: [String]? = nil,
        snapshotTimeoutNanoseconds: UInt64 = 3_500_000_000,
        restartDelayNanoseconds: UInt64 = 1_000_000_000
    ) {
        self.executableURL = executableURL
        self.arguments = arguments ?? [
            "stream", "--style", "compact", "--predicate", Self.defaultPredicate,
        ]
        self.snapshotArguments = snapshotArguments ?? [
            "show", "--last", "2h", "--style", "compact", "--predicate", Self.snapshotPredicate,
        ]
        self.snapshotTimeoutNanoseconds = snapshotTimeoutNanoseconds
        self.restartDelayNanoseconds = restartDelayNanoseconds
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

public enum MacOSMeetingActivityDetectorConsumerOutcome: Equatable, Sendable {
    case accepted
    case retryable(reason: String)
    case terminal(reason: String)
}

public final class MacOSMeetingActivityDetector: @unchecked Sendable {
    public typealias Clock = @Sendable () -> Date

    private let filter: MeetingDetectionCandidateFilter
    private let policy: MeetingDetectionPolicy
    private let debounceSeconds: TimeInterval
    private let endGraceSeconds: TimeInterval
    private let retryIntervalSeconds: TimeInterval
    private let clock: Clock
    private var trackedEvents: [String: TrackedAudioOwnership] = [:]

    public init(
        filter: MeetingDetectionCandidateFilter = MeetingDetectionCandidateFilter(),
        policy: MeetingDetectionPolicy = MeetingDetectionPolicy(),
        debounceSeconds: TimeInterval = 5,
        endGraceSeconds: TimeInterval = 15,
        retryIntervalSeconds: TimeInterval = 2,
        clock: @escaping Clock = Date.init
    ) {
        self.filter = filter
        self.policy = policy
        self.debounceSeconds = debounceSeconds
        self.endGraceSeconds = endGraceSeconds
        self.retryIntervalSeconds = retryIntervalSeconds
        self.clock = clock
    }

    public func handle(
        event: MacOSAudioOwnershipEvent,
        registry: MeetingTargetRegistryDocument,
        settings: MeetingDetectionSettings,
        prerequisites: MeetingDetectionCapturePrerequisites = MeetingDetectionCapturePrerequisites()
    ) -> [MacOSMeetingActivityDetectorOutput] {
        guard reconcile(event: event) else { return [] }
        if event.state == .active {
            return []
        }
        return advance(
            now: event.observedAt,
            registry: registry,
            settings: settings,
            prerequisites: prerequisites
        )
    }

    @discardableResult
    public func reconcile(event: MacOSAudioOwnershipEvent) -> Bool {
        if var tracked = trackedEvents[event.bundleID] {
            guard tracked.apply(event) else { return false }
            trackedEvents[event.bundleID] = tracked
            return true
        }
        guard event.state == .active else { return false }
        trackedEvents[event.bundleID] = TrackedAudioOwnership(event: event)
        return true
    }

    public func advance(
        now: Date? = nil,
        registry: MeetingTargetRegistryDocument,
        settings: MeetingDetectionSettings,
        prerequisites: MeetingDetectionCapturePrerequisites = MeetingDetectionCapturePrerequisites()
    ) -> [MacOSMeetingActivityDetectorOutput] {
        let value = now ?? clock()
        var outputs: [MacOSMeetingActivityDetectorOutput] = []
        for bundleID in trackedEvents.keys.sorted() {
            guard var tracked = trackedEvents[bundleID] else { continue }
            if let inactiveAt = tracked.inactiveAt {
                guard value.timeIntervalSince(inactiveAt) >= endGraceSeconds else {
                    continue
                }
                trackedEvents.removeValue(forKey: tracked.bundleID)
                if tracked.didEmitLifecycleOutput {
                    outputs.append(.ended(bundleID: tracked.bundleID))
                }
                continue
            }

            guard !tracked.isHandled,
                  value.timeIntervalSince(tracked.firstObservedAt) >= debounceSeconds
            else {
                continue
            }
            if let lastOfferedAt = tracked.lastOfferedAt,
               value.timeIntervalSince(lastOfferedAt) < retryIntervalSeconds {
                continue
            }
            let output = outputForStableEvent(
                tracked,
                activeUntil: value,
                registry: registry,
                settings: settings,
                prerequisites: prerequisites
            )
            guard let output else { continue }
            if case .suppressed(_, let reason) = output {
                guard tracked.lastSuppressionReason != reason else { continue }
                tracked.lastSuppressionReason = reason
            } else {
                tracked.lastSuppressionReason = nil
                tracked.lastOfferedAt = value
            }
            tracked.didEmitLifecycleOutput = true
            trackedEvents[bundleID] = tracked
            outputs.append(output)
        }
        return outputs
    }

    public func recordConsumerOutcome(
        bundleID: String,
        outcome: MacOSMeetingActivityDetectorConsumerOutcome,
        at: Date? = nil
    ) {
        guard var tracked = trackedEvents[bundleID] else { return }
        switch outcome {
        case .accepted, .terminal:
            tracked.isHandled = true
            tracked.lastOfferedAt = nil
        case .retryable:
            tracked.isHandled = false
            tracked.lastOfferedAt = at ?? clock()
        }
        trackedEvents[bundleID] = tracked
    }

    public func reset() {
        trackedEvents.removeAll(keepingCapacity: true)
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
        }
    }

    public func isActive(bundleID: String) -> Bool {
        guard let tracked = trackedEvents[bundleID] else { return false }
        return !tracked.activeSources.isEmpty
    }

    private func outputForStableEvent(
        _ tracked: TrackedAudioOwnership,
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

private struct TrackedAudioOwnership: Sendable {
    var firstObservedAt: Date
    var latestEvent: MacOSAudioOwnershipEvent
    var activeSources: Set<MacOSAudioOwnershipSource>
    var sourceObservedAt: [MacOSAudioOwnershipSource: Date]
    var inactiveAt: Date?
    var stableObservationCount: Int
    var isHandled = false
    var didEmitLifecycleOutput = false
    var lastOfferedAt: Date?
    var lastSuppressionReason: String?

    var bundleID: String { latestEvent.bundleID }

    init(event: MacOSAudioOwnershipEvent) {
        firstObservedAt = event.observedAt
        latestEvent = event
        activeSources = event.state == .active ? [event.source] : []
        sourceObservedAt = [event.source: event.observedAt]
        inactiveAt = event.state == .inactive ? event.observedAt : nil
        stableObservationCount = 1
    }

    mutating func apply(_ event: MacOSAudioOwnershipEvent) -> Bool {
        if let lastObservedAt = sourceObservedAt[event.source], event.observedAt < lastObservedAt {
            return false
        }
        sourceObservedAt[event.source] = event.observedAt
        latestEvent = event
        switch event.state {
        case .active:
            firstObservedAt = min(firstObservedAt, event.observedAt)
            let inserted = activeSources.insert(event.source).inserted
            inactiveAt = nil
            if inserted {
                stableObservationCount += 1
            }
            return true
        case .inactive:
            if activeSources.remove(event.source) != nil, activeSources.isEmpty {
                inactiveAt = event.observedAt
            }
            return true
        }
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
