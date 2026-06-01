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

    public init(releaseAfterIdleTicks: Int = Self.defaultReleaseAfterIdleTicks) {
        self.releaseAfterIdleTicks = releaseAfterIdleTicks
    }

    public func shouldReleasePhysicalRoute(
        bridgeActive: Bool,
        virtualClientRunning: Bool,
        consecutiveIdleTicks: Int
    ) -> Bool {
        bridgeActive && !virtualClientRunning && consecutiveIdleTicks >= releaseAfterIdleTicks
    }
}

public final class PassthroughRouteEngine: @unchecked Sendable {
    public typealias Logger = @Sendable (_ event: String, _ detail: String) -> Void

    public static let shared = PassthroughRouteEngine()

    private let queue = DispatchQueue(label: "com.2brainrec.passthrough-route-engine")
    private var stateStorage: PassthroughRouteEngineState
    private let sharedMemory: SharedAudioMemory?
    private var bridge: PassthroughBridge?
    private var heartbeatTimer: DispatchSourceTimer?
    private var automaticStartTimer: DispatchSourceTimer?
    private let activityDetector: VirtualDeviceActivityDetecting
    private let autoIdlePolicy = PassthroughAutoIdlePolicy()
    private var consecutiveIdleTicks = 0

    public init(
        sharedMemory: SharedAudioMemory? = SharedAudioMemory(),
        activityDetector: VirtualDeviceActivityDetecting = CoreAudioVirtualDeviceActivityDetector()
    ) {
        self.sharedMemory = sharedMemory
        self.activityDetector = activityDetector
        self.stateStorage = .inactive
        sharedMemory?.clearAppHeartbeat()
    }

    public var state: PassthroughRouteEngineState {
        queue.sync { stateStorage }
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
            logger?("passthrough_bridge_stale", "coreaudiod restarted; route requires recheck")
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
        stateStorage = .starting
        logger("passthrough_bridge_starting", reason)
        let startedAt = Date()
        do {
            let bridge = try PassthroughBridge(
                selectedPhysicalInputId: selectedPhysicalInputId,
                selectedPhysicalOutputId: selectedPhysicalOutputId
            )
            try bridge.start()
            bridge.refreshAppIOHeartbeat()
            self.bridge = bridge
            consecutiveIdleTicks = 0
            startHeartbeatTimer(for: bridge, logger: logger)
            stateStorage = .active
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
                stateStorage = .blocked("startup_timeout")
                logger("passthrough_bridge_blocked", "startup exceeded 3000 ms")
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

    private func startAutomaticStartTimer(
        selectedPhysicalInputId: String?,
        selectedPhysicalOutputId: String?,
        logger: @escaping Logger
    ) {
        stopAutomaticStartTimer()
        let timer = DispatchSource.makeTimerSource(queue: queue)
        timer.schedule(deadline: .now() + 0.5, repeating: 1.0)
        timer.setEventHandler { [weak self] in
            guard let self, self.bridge == nil else { return }
            guard self.activityDetector.anyExpectedVirtualDeviceRunning() else { return }
            _ = self.startRouteLocked(
                selectedPhysicalInputId: selectedPhysicalInputId,
                selectedPhysicalOutputId: selectedPhysicalOutputId,
                reason: "virtual device client became active",
                startedDetail: "automatic non-recording route engine active",
                logger: logger
            )
        }
        automaticStartTimer = timer
        timer.resume()
    }

    private func startHeartbeatTimer(for bridge: PassthroughBridge, logger: @escaping Logger) {
        stopHeartbeatTimer()
        let timer = DispatchSource.makeTimerSource(queue: queue)
        timer.schedule(deadline: .now() + 1.0, repeating: 1.0)
        timer.setEventHandler { [weak self, weak bridge] in
            guard let self, let bridge else { return }
            let virtualClientRunning = self.activityDetector.anyExpectedVirtualDeviceRunning()
            self.consecutiveIdleTicks = virtualClientRunning ? 0 : self.consecutiveIdleTicks + 1
            if self.autoIdlePolicy.shouldReleasePhysicalRoute(
                bridgeActive: self.bridge != nil,
                virtualClientRunning: virtualClientRunning,
                consecutiveIdleTicks: self.consecutiveIdleTicks
            ) {
                _ = self.releaseBridgeForIdleLocked(logger: logger)
                return
            }
            bridge.refreshAppIOHeartbeat()
        }
        heartbeatTimer = timer
        timer.resume()
    }

    private func reconcileClientActivityLocked(logger: Logger? = nil) -> PassthroughRouteEngineState {
        if autoIdlePolicy.shouldReleasePhysicalRoute(
            bridgeActive: bridge != nil,
            virtualClientRunning: activityDetector.anyExpectedVirtualDeviceRunning(),
            consecutiveIdleTicks: autoIdlePolicy.releaseAfterIdleTicks
        ) {
            return releaseBridgeForIdleLocked(logger: logger)
        }
        return stateStorage
    }

    private func releaseBridgeForIdleLocked(logger: Logger? = nil) -> PassthroughRouteEngineState {
        stopHeartbeatTimer()
        bridge?.stop()
        bridge = nil
        consecutiveIdleTicks = 0
        sharedMemory?.clearAppHeartbeat()
        stateStorage = .idleSafe
        logger?("passthrough_bridge_idle_released", "virtual-device client IO closed; physical route released")
        startAutomaticStartTimer(
            selectedPhysicalInputId: nil,
            selectedPhysicalOutputId: nil,
            logger: logger ?? { _, _ in }
        )
        return stateStorage
    }

    private func stopAutomaticStartTimer() {
        automaticStartTimer?.cancel()
        automaticStartTimer = nil
    }

    private func stopHeartbeatTimer() {
        heartbeatTimer?.cancel()
        heartbeatTimer = nil
    }
}

public protocol VirtualDeviceActivityDetecting: Sendable {
    func anyExpectedVirtualDeviceRunning() -> Bool
}

public struct CoreAudioVirtualDeviceActivityDetector: VirtualDeviceActivityDetecting {
    private let expectedNames: Set<String>

    public init(expectedNames: Set<String> = ["2brain Rec Microphone", "2brain Rec Speaker"]) {
        self.expectedNames = expectedNames
    }

    public func anyExpectedVirtualDeviceRunning() -> Bool {
        for deviceID in deviceIDs() {
            guard let name = deviceName(deviceID), expectedNames.contains(name) else { continue }
            if isRunning(deviceID) {
                return true
            }
        }
        return false
    }

    private func deviceIDs() -> [AudioDeviceID] {
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

    private func deviceName(_ deviceID: AudioDeviceID) -> String? {
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

    private func isRunning(_ deviceID: AudioDeviceID) -> Bool {
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
