import Foundation
import CoreAudio
import TwoBrainRecShared

public enum PassthroughRouteEngineState: Equatable, Sendable {
    case disabled
    case idleSafe
    case inactive
    case armed
    case starting
    case active
    case stale(String)
    case blocked(String)
    case failed(String)
    case fallback(String)
}

public struct PassthroughAutoIdlePolicy: Sendable {
    public static let defaultReleaseAfterIdleTicks = 300

    public var releaseAfterIdleTicks: Int
    public var clientActivityPolicy: LiveRouteClientActivityPolicy

    public init(
        releaseAfterIdleTicks: Int = Self.defaultReleaseAfterIdleTicks,
        clientActivityPolicy: LiveRouteClientActivityPolicy = LiveRouteClientActivityPolicy()
    ) {
        self.releaseAfterIdleTicks = releaseAfterIdleTicks
        self.clientActivityPolicy = clientActivityPolicy
    }

    public func shouldReleasePhysicalRoute(
        bridgeActive: Bool,
        virtualClientRunning: Bool,
        consecutiveIdleTicks: Int
    ) -> Bool {
        bridgeActive && !virtualClientRunning && consecutiveIdleTicks >= releaseAfterIdleTicks
    }

    public func shouldReleasePhysicalRoute(
        bridgeActive: Bool,
        clientActivity: ClientActivitySnapshot,
        consecutiveIdleTicks: Int
    ) -> Bool {
        guard bridgeActive else { return false }
        guard !clientActivityPolicy.shouldPreserveRoute(for: clientActivity) else { return false }
        return consecutiveIdleTicks >= releaseAfterIdleTicks
    }
}

public protocol PassthroughBridgeControlling: AnyObject {
    func start() throws
    func stop()
    func refreshAppIOHeartbeat()
}

extension PassthroughBridge: PassthroughBridgeControlling {
    public func refreshAppIOHeartbeat() {
        refreshAppIOHeartbeat(at: Date())
    }
}

public final class PassthroughRouteEngine: @unchecked Sendable {
    public typealias Logger = @Sendable (_ event: String, _ detail: String) -> Void
    public typealias BridgeFactory = @Sendable (_ selectedPhysicalInputId: String?, _ selectedPhysicalOutputId: String?) throws -> PassthroughBridgeControlling
    public static let automaticClientDetectionGraceTicks = 3

    public static let shared = PassthroughRouteEngine()

    private let queue = DispatchQueue(label: "com.2brainrec.passthrough-route-engine")
    private var stateStorage: PassthroughRouteEngineState
    private let sharedMemory: SharedAudioMemory?
    private var bridge: PassthroughBridgeControlling?
    private var heartbeatTimer: DispatchSourceTimer?
    private var automaticStartTimer: DispatchSourceTimer?
    private let activityDetector: VirtualDeviceActivityDetecting
    private let bridgeFactory: BridgeFactory
    private let autoIdlePolicy = PassthroughAutoIdlePolicy()
    private let releasePolicy = LiveRouteReleasePolicy()
    private let idFactory: @Sendable () -> String
    private let routeEvidenceStore: RouteEvidenceStore?
    private var consecutiveIdleTicks = 0
    private var routeSessionId: String?
    private var lastRouteEvidenceEvent: RouteEvidenceEvent?
    private var automaticStartTicks = 0

    public init(
        sharedMemory: SharedAudioMemory? = SharedAudioMemory(),
        activityDetector: VirtualDeviceActivityDetecting = CoreAudioVirtualDeviceActivityDetector(),
        bridgeFactory: @escaping BridgeFactory = { inputId, outputId in
            try PassthroughBridge(
                selectedPhysicalInputId: inputId,
                selectedPhysicalOutputId: outputId
            )
        },
        idFactory: @escaping @Sendable () -> String = { UUID().uuidString },
        routeEvidenceStore: RouteEvidenceStore? = nil
    ) {
        self.sharedMemory = sharedMemory
        self.activityDetector = activityDetector
        self.bridgeFactory = bridgeFactory
        self.idFactory = idFactory
        self.routeEvidenceStore = routeEvidenceStore
        self.stateStorage = .inactive
        sharedMemory?.clearAppHeartbeat()
    }

    public var state: PassthroughRouteEngineState {
        queue.sync { stateStorage }
    }

    public var currentRouteSessionId: String? {
        queue.sync { routeSessionId }
    }

    public func recordLaunchState(logger: Logger) -> PassthroughRouteEngineState {
        queue.sync {
            if bridge != nil {
                bridge?.refreshAppIOHeartbeat()
                stateStorage = .active
                logger(
                    "passthrough_bridge_launch_active",
                    "non-recording route engine is already active"
                )
                return stateStorage
            }

            stateStorage = .inactive
            logger(
                "passthrough_bridge_launch_available",
                "non-recording route engine will arm and wait for virtual-device client IO"
            )
            return stateStorage
        }
    }

    public func startAutomaticRoute(
        selectedPhysicalInputId: String? = nil,
        selectedPhysicalOutputId: String? = nil,
        logger: @escaping Logger
    ) -> PassthroughRouteEngineState {
        queue.sync {
            if bridge != nil {
                bridge?.refreshAppIOHeartbeat()
                stateStorage = .active
                logger("passthrough_bridge_already_active", "route engine refreshed app IO heartbeat")
                return stateStorage
            }

            if activityDetector.anyExpectedVirtualDeviceRunning() {
                return startRouteLocked(
                    selectedPhysicalInputId: selectedPhysicalInputId,
                    selectedPhysicalOutputId: selectedPhysicalOutputId,
                    reason: "virtual device client already active",
                    startedDetail: "automatic non-recording route engine active",
                    logger: logger
                )
            }

            stateStorage = .armed
            startAutomaticStartTimer(
                selectedPhysicalInputId: selectedPhysicalInputId,
                selectedPhysicalOutputId: selectedPhysicalOutputId,
                logger: logger
            )
            logger("passthrough_bridge_armed", "waiting for explicit virtual-device client IO")
            return stateStorage
        }
    }

    public func startExperimentalRoute(
        selectedPhysicalInputId: String? = nil,
        selectedPhysicalOutputId: String? = nil,
        logger: @escaping Logger
    ) -> PassthroughRouteEngineState {
        startRoute(
            selectedPhysicalInputId: selectedPhysicalInputId,
            selectedPhysicalOutputId: selectedPhysicalOutputId,
            reason: "explicit readiness check",
            startedDetail: "explicit route engine active",
            logger: logger
        )
    }

    private func startRoute(
        selectedPhysicalInputId: String?,
        selectedPhysicalOutputId: String?,
        reason: String,
        startedDetail: String,
        logger: @escaping Logger
    ) -> PassthroughRouteEngineState {
        queue.sync {
            startRouteLocked(
                selectedPhysicalInputId: selectedPhysicalInputId,
                selectedPhysicalOutputId: selectedPhysicalOutputId,
                reason: reason,
                startedDetail: startedDetail,
                logger: logger
            )
        }
    }

    public func stop(logger: Logger? = nil) -> PassthroughRouteEngineState {
        queue.sync {
            stopAutomaticStartTimer()
            stopHeartbeatTimer()
            bridge?.stop()
            bridge = nil
            sharedMemory?.clearAppHeartbeat()
            stateStorage = .idleSafe
            recordEvidenceLocked(lifecycleEventLocked(name: "route.lifecycle.stopped", state: .stopped))
            routeSessionId = nil
            logger?("passthrough_bridge_stopped", "route engine cleared app IO heartbeat")
            return stateStorage
        }
    }

    public func markCoreAudioRestarted(logger: Logger? = nil) -> PassthroughRouteEngineState {
        queue.sync {
            stopAutomaticStartTimer()
            stopHeartbeatTimer()
            bridge?.stop()
            bridge = nil
            sharedMemory?.clearAppHeartbeat()
            stateStorage = .stale("coreaudiod_restarted")
            recordEvidenceLocked(lifecycleEventLocked(name: "route.lifecycle.stale", state: .stale))
            logger?("passthrough_bridge_stale", "coreaudiod restarted; route requires recheck")
            logger?("passthrough_autorepair_triggered", AutorepairTrigger.coreaudiodRestart.rawValue)
            return stateStorage
        }
    }

    public func applyAutorepairAttempt(
        _ attempt: AutorepairAttempt,
        logger: Logger? = nil
    ) -> PassthroughRouteEngineState {
        queue.sync {
            switch attempt.outcome {
            case .succeeded:
                stateStorage = .active
                recordEvidenceLocked(lifecycleEventLocked(name: "route.lifecycle.recovered", state: .healthyAfterFreshEvidence))
                logger?("passthrough_autorepair_succeeded", attempt.trigger.rawValue)
            case .degradedSlow:
                stateStorage = .stale("autorepair_degraded_slow")
                recordEvidenceLocked(lifecycleEventLocked(name: "route.lifecycle.stale", state: .stale))
                logger?("passthrough_autorepair_degraded", attempt.trigger.rawValue)
            case .blockedNonRecoverable:
                stateStorage = .blocked(attempt.nonRecoverableReason?.rawValue ?? "blocked_non_recoverable")
                recordEvidenceLocked(lifecycleEventLocked(name: "route.lifecycle.blocked", state: .blocked))
                logger?("passthrough_autorepair_blocked", attempt.nonRecoverableReason?.rawValue ?? "blocked_non_recoverable")
            case .failed, .retryBudgetExhausted:
                stateStorage = .failed(attempt.outcome.rawValue)
                recordEvidenceLocked(lifecycleEventLocked(name: "route.lifecycle.failed", state: .failed))
                logger?("passthrough_autorepair_failed", attempt.outcome.rawValue)
            case .notStarted:
                break
            }
            return stateStorage
        }
    }

    public func switchToAccepted005Fallback(reason: String, logger: Logger? = nil) -> PassthroughRouteEngineState {
        queue.sync {
            stopAutomaticStartTimer()
            stopHeartbeatTimer()
            bridge?.stop()
            bridge = nil
            sharedMemory?.clearAppHeartbeat()
            stateStorage = .fallback(reason)
            logger?("passthrough_bridge_fallback", reason)
            return stateStorage
        }
    }

    private func startRouteLocked(
        selectedPhysicalInputId: String?,
        selectedPhysicalOutputId: String?,
        reason: String,
        startedDetail: String,
        logger: @escaping Logger
    ) -> PassthroughRouteEngineState {
        if bridge != nil {
            bridge?.refreshAppIOHeartbeat()
            stateStorage = .active
            logger("passthrough_bridge_already_active", "route engine refreshed app IO heartbeat")
            return stateStorage
        }

        stopAutomaticStartTimer()
        ensureRouteSessionLocked()
        stateStorage = .starting
        logger("passthrough_bridge_starting", reason)
        let startedAt = Date()
        do {
            let bridge = try bridgeFactory(selectedPhysicalInputId, selectedPhysicalOutputId)
            try bridge.start()
            bridge.refreshAppIOHeartbeat()
            self.bridge = bridge
            consecutiveIdleTicks = 0
            startHeartbeatTimer(for: bridge, logger: logger)
            stateStorage = .active
            recordEvidenceLocked(lifecycleEventLocked(name: "route.lifecycle.active", state: .active))
            let attempt = PassthroughBridge.startupAttemptEvidence(
                attemptId: UUID().uuidString,
                trigger: .clientIOOpened,
                startedAt: startedAt,
                completedAt: Date(),
                outcome: .ready
            )
            if attempt.isWithinAcceptedWindow {
                logger("passthrough_bridge_started", startedDetail)
            } else {
                logger("passthrough_bridge_started_slow", "startup exceeded 3000 ms; route active after successful bridge start")
            }
        } catch {
            stopHeartbeatTimer()
            bridge = nil
            sharedMemory?.clearAppHeartbeat()
            let attempt = PassthroughBridge.startupAttemptEvidence(
                attemptId: UUID().uuidString,
                trigger: .clientIOOpened,
                startedAt: startedAt,
                completedAt: Date(),
                outcome: .failed,
                blockedReason: String(describing: error)
            )
            stateStorage = attempt.outcome == .blocked
                ? .blocked(attempt.blockedReason ?? "startup_timeout")
                : .failed(String(describing: error))
            logger(
                attempt.outcome == .blocked ? "passthrough_bridge_blocked" : "passthrough_bridge_failed",
                attempt.blockedReason ?? String(describing: error)
            )
        }
        return stateStorage
    }

    public func reconcileClientActivity(logger: Logger? = nil) -> PassthroughRouteEngineState {
        queue.sync {
            reconcileClientActivityLocked(logger: logger)
        }
    }

    public func reconcileClientActivity(
        snapshot: ClientActivitySnapshot,
        logger: Logger? = nil
    ) -> PassthroughRouteEngineState {
        queue.sync {
            reconcileClientActivityLocked(snapshot: snapshot, logger: logger)
        }
    }

    public func recordFrameContinuity(
        _ snapshot: FrameContinuitySnapshot
    ) -> RouteEvidenceEvent {
        queue.sync {
            let event = frameContinuityEventLocked(snapshot)
            recordEvidenceLocked(event)
            return event
        }
    }

    private func startAutomaticStartTimer(
        selectedPhysicalInputId: String?,
        selectedPhysicalOutputId: String?,
        logger: @escaping Logger
    ) {
        stopAutomaticStartTimer()
        ensureRouteSessionLocked()
        let timer = DispatchSource.makeTimerSource(queue: queue)
        timer.schedule(deadline: .now() + 0.5, repeating: 1.0)
        timer.setEventHandler { [weak self] in
            guard let self, self.bridge == nil else { return }
            self.automaticStartTicks += 1
            let virtualDeviceRunning = self.activityDetector.anyExpectedVirtualDeviceRunning()
            guard virtualDeviceRunning || self.automaticStartTicks >= Self.automaticClientDetectionGraceTicks else { return }
            _ = self.startRouteLocked(
                selectedPhysicalInputId: selectedPhysicalInputId,
                selectedPhysicalOutputId: selectedPhysicalOutputId,
                reason: virtualDeviceRunning
                    ? "virtual device client became active"
                    : "automatic route warmup after client detection grace",
                startedDetail: "automatic non-recording route engine active",
                logger: logger
            )
        }
        automaticStartTimer = timer
        automaticStartTicks = 0
        recordEvidenceLocked(lifecycleEventLocked(name: "route.lifecycle.armed", state: .armed))
        timer.resume()
    }

    private func startHeartbeatTimer(for bridge: PassthroughBridgeControlling, logger: @escaping Logger) {
        stopHeartbeatTimer()
        let timer = DispatchSource.makeTimerSource(queue: queue)
        timer.schedule(deadline: .now() + 1.0, repeating: 1.0)
        timer.setEventHandler { [weak self, weak bridge] in
            guard let self, let bridge else { return }
            let clientActivity = self.activityDetector.expectedVirtualDeviceClientActivity()
            self.consecutiveIdleTicks = self.autoIdlePolicy.clientActivityPolicy.shouldPreserveRoute(for: clientActivity) ? 0 : self.consecutiveIdleTicks + 1
            if self.autoIdlePolicy.shouldReleasePhysicalRoute(
                bridgeActive: self.bridge != nil,
                clientActivity: clientActivity,
                consecutiveIdleTicks: self.consecutiveIdleTicks
            ) {
                _ = self.releaseBridgeForIdleLocked(snapshot: clientActivity, logger: logger)
                return
            }
            logger("passthrough_route_preserved", "fresh client activity preserved physical route")
            bridge.refreshAppIOHeartbeat()
        }
        heartbeatTimer = timer
        timer.resume()
    }

    private func reconcileClientActivityLocked(logger: Logger? = nil) -> PassthroughRouteEngineState {
        reconcileClientActivityLocked(
            snapshot: activityDetector.expectedVirtualDeviceClientActivity(),
            logger: logger
        )
    }

    private func reconcileClientActivityLocked(
        snapshot: ClientActivitySnapshot,
        logger: Logger? = nil
    ) -> PassthroughRouteEngineState {
            if autoIdlePolicy.clientActivityPolicy.shouldPreserveRoute(for: snapshot) {
            consecutiveIdleTicks = 0
            if bridge != nil {
                stateStorage = .active
                recordEvidenceLocked(lifecycleEventLocked(name: "route.lifecycle.preserved", state: .preserved, clientActivity: snapshot))
                logger?("passthrough_route_preserved", "fresh client activity preserved physical route")
            }
            return stateStorage
        }

        consecutiveIdleTicks += 1
        if autoIdlePolicy.shouldReleasePhysicalRoute(
            bridgeActive: bridge != nil,
            clientActivity: snapshot,
            consecutiveIdleTicks: consecutiveIdleTicks
        ) {
            return releaseBridgeForIdleLocked(snapshot: snapshot, logger: logger)
        }
        return stateStorage
    }

    private func releaseBridgeForIdleLocked(
        snapshot: ClientActivitySnapshot,
        logger: Logger? = nil
    ) -> PassthroughRouteEngineState {
        let decision = releasePolicy.decision(
            for: snapshot,
            requestedReason: .meetingClientClosed,
            decidedAt: Date()
        )
        guard decision.outcome == .released else {
            recordEvidenceLocked(releaseDecisionEventLocked(decision, clientActivity: snapshot))
            logger?("passthrough_bridge_release_denied", decision.reason.rawValue)
            return stateStorage
        }
        stopHeartbeatTimer()
        bridge?.stop()
        bridge = nil
        consecutiveIdleTicks = 0
        sharedMemory?.clearAppHeartbeat()
        stateStorage = .idleSafe
        recordEvidenceLocked(releaseDecisionEventLocked(decision, clientActivity: snapshot))
        routeSessionId = nil
        logger?("passthrough_bridge_idle_released", "virtual-device client IO closed; physical route released")
        startAutomaticStartTimer(
            selectedPhysicalInputId: nil,
            selectedPhysicalOutputId: nil,
            logger: logger ?? { _, _ in }
        )
        return stateStorage
    }

    public func lastRouteEvidence() -> RouteEvidenceEvent? {
        queue.sync { lastRouteEvidenceEvent }
    }

    private func lifecycleEventLocked(
        name: String,
        state: LiveRouteState,
        clientActivity: ClientActivitySnapshot? = nil
    ) -> RouteEvidenceEvent {
        let sessionId = ensureRouteSessionLocked()
        return RouteEvidenceEvent(
            eventId: idFactory(),
            sessionId: sessionId,
            family: .routeLifecycle,
            name: Self.canonicalLifecycleName(name, state: state),
            observedAt: Date(),
            source: .routeEngine,
            routeState: state,
            clientActivity: clientActivity
        )
    }

    private func releaseDecisionEventLocked(
        _ decision: RouteReleaseDecision,
        clientActivity: ClientActivitySnapshot
    ) -> RouteEvidenceEvent {
        let sessionId = ensureRouteSessionLocked()
        return RouteEvidenceEvent(
            eventId: idFactory(),
            sessionId: sessionId,
            family: .releaseDecision,
            name: Self.releaseDecisionEventName(decision),
            observedAt: decision.decidedAt,
            source: .routeEngine,
            routeState: decision.outcome == .released ? .released : .preserved,
            clientActivity: clientActivity,
            releaseDecision: decision
        )
    }

    private func frameContinuityEventLocked(_ snapshot: FrameContinuitySnapshot) -> RouteEvidenceEvent {
        let sessionId = ensureRouteSessionLocked()
        return RouteEvidenceEvent(
            eventId: idFactory(),
            sessionId: sessionId,
            family: .frameContinuity,
            name: "frame_continuity.observed",
            observedAt: Date(),
            source: .routeEngine,
            routeState: .active,
            frameContinuity: snapshot
        )
    }

    @discardableResult
    private func ensureRouteSessionLocked() -> String {
        if let routeSessionId {
            return routeSessionId
        }
        let id = idFactory()
        routeSessionId = id
        return id
    }

    private func recordEvidenceLocked(_ event: RouteEvidenceEvent) {
        lastRouteEvidenceEvent = event
        _ = try? routeEvidenceStore?.append(event)
    }

    private static func canonicalLifecycleName(_ name: String, state: LiveRouteState) -> String {
        if name.hasPrefix("route.lifecycle.") {
            return name
        }
        switch state {
        case .healthyAfterFreshEvidence:
            return "route.lifecycle.recovered"
        default:
            if name.hasPrefix("route.") {
                return "route.lifecycle." + name.dropFirst("route.".count)
            }
            return name
        }
    }

    private static func releaseDecisionEventName(_ decision: RouteReleaseDecision) -> String {
        switch (decision.outcome, decision.reason) {
        case (.released, .meetingClientClosed):
            return "idle_release.released_after_client_closed"
        case (.keepActive, .deniedActiveClient):
            return "idle_release.release_denied_client_active"
        case (.denied, .deniedAmbiguousEvidence), (.denied, .deniedStaleEvidence):
            return "idle_release.release_denied_unknown_state"
        case (.keepActive, _):
            return "idle_release.keep_active"
        case (.released, _):
            return "idle_release.released_after_client_closed"
        case (.denied, _):
            return "idle_release.release_denied_unknown_state"
        }
    }

    private func stopAutomaticStartTimer() {
        automaticStartTimer?.cancel()
        automaticStartTimer = nil
        automaticStartTicks = 0
    }

    private func stopHeartbeatTimer() {
        heartbeatTimer?.cancel()
        heartbeatTimer = nil
    }
}

public protocol VirtualDeviceActivityDetecting: Sendable {
    func anyExpectedVirtualDeviceRunning() -> Bool
    func expectedVirtualDeviceClientActivity() -> ClientActivitySnapshot
}

public extension VirtualDeviceActivityDetecting {
    func expectedVirtualDeviceClientActivity() -> ClientActivitySnapshot {
        let running = anyExpectedVirtualDeviceRunning()
        return ClientActivitySnapshot(
            source: .deviceIsRunning,
            microphoneOpen: running,
            microphoneRunning: running,
            speakerOpen: running,
            speakerRunning: running,
            stillUsesVirtualMicrophone: running,
            stillUsesVirtualSpeaker: running,
            freshnessMs: 0,
            naturalSilenceAllowed: true
        )
    }
}

public struct CoreAudioVirtualDeviceActivityDetector: VirtualDeviceActivityDetecting {
    public struct DeviceSnapshot: Equatable, Sendable {
        public let name: String
        public let isRunning: Bool

        public init(name: String, isRunning: Bool) {
            self.name = name
            self.isRunning = isRunning
        }
    }

    private let expectedMicrophoneNames: Set<String>
    private let expectedSpeakerNames: Set<String>
    private let snapshotProvider: @Sendable () -> [DeviceSnapshot]

    public init(
        expectedMicrophoneNames: Set<String> = ["2brain Rec Microphone"],
        expectedSpeakerNames: Set<String> = ["2brain Rec Speaker"],
        snapshotProvider: (@Sendable () -> [DeviceSnapshot])? = nil
    ) {
        self.expectedMicrophoneNames = expectedMicrophoneNames
        self.expectedSpeakerNames = expectedSpeakerNames
        self.snapshotProvider = snapshotProvider ?? {
            Self.coreAudioDeviceSnapshots()
        }
    }

    public func anyExpectedVirtualDeviceRunning() -> Bool {
        snapshotProvider().contains { snapshot in
            (expectedMicrophoneNames.contains(snapshot.name) || expectedSpeakerNames.contains(snapshot.name))
                && snapshot.isRunning
        }
    }

    public func expectedVirtualDeviceClientActivity() -> ClientActivitySnapshot {
        let snapshots = snapshotProvider()
        let microphone = snapshots.first { expectedMicrophoneNames.contains($0.name) }
        let speaker = snapshots.first { expectedSpeakerNames.contains($0.name) }
        let microphoneClientActive = microphone?.isRunning ?? false
        let speakerClientActive = speaker?.isRunning ?? false

        return ClientActivitySnapshot(
            source: .coreAudioClient,
            microphoneOpen: microphoneClientActive,
            microphoneRunning: microphoneClientActive,
            speakerOpen: speakerClientActive,
            speakerRunning: speakerClientActive,
            stillUsesVirtualMicrophone: microphoneClientActive,
            stillUsesVirtualSpeaker: speakerClientActive,
            freshnessMs: 0,
            naturalSilenceAllowed: true
        )
    }

    private static func coreAudioDeviceSnapshots() -> [DeviceSnapshot] {
        deviceIDs().compactMap { deviceID in
            guard let name = deviceName(deviceID) else { return nil }
            return DeviceSnapshot(name: name, isRunning: isRunning(deviceID))
        }
    }

    private static func deviceIDs() -> [AudioDeviceID] {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: AudioObjectPropertyElement(kAudioObjectPropertyElementMain)
        )
        var byteCount: UInt32 = 0
        guard AudioObjectGetPropertyDataSize(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            0,
            nil,
            &byteCount
        ) == noErr, byteCount > 0 else {
            return []
        }

        let count = Int(byteCount) / MemoryLayout<AudioDeviceID>.size
        var devices = Array(repeating: AudioDeviceID(0), count: count)
        guard AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            0,
            nil,
            &byteCount,
            &devices
        ) == noErr else {
            return []
        }
        return devices
    }

    private static func deviceName(_ deviceID: AudioDeviceID) -> String? {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioObjectPropertyName,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: AudioObjectPropertyElement(kAudioObjectPropertyElementMain)
        )
        var value: CFString?
        var byteCount = UInt32(MemoryLayout<CFString?>.size)
        let status = withUnsafeMutablePointer(to: &value) { pointer in
            AudioObjectGetPropertyData(deviceID, &address, 0, nil, &byteCount, pointer)
        }
        guard status == noErr else { return nil }
        return value as String?
    }

    private static func isRunning(_ deviceID: AudioDeviceID) -> Bool {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyDeviceIsRunning,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: AudioObjectPropertyElement(kAudioObjectPropertyElementMain)
        )
        var value: UInt32 = 0
        var byteCount = UInt32(MemoryLayout<UInt32>.size)
        let status = AudioObjectGetPropertyData(deviceID, &address, 0, nil, &byteCount, &value)
        return status == noErr && value != 0
    }
}
