import Foundation
import CoreAudio
import TwoBrainRecShared

public enum PassthroughRouteEngineState: Equatable, Sendable {
    case disabled
    case inactive
    case armed
    case starting
    case active
    case stale(String)
    case blocked(String)
    case failed(String)
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
                "non-recording route engine will start automatically when the app opens"
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

            return startRouteLocked(
                selectedPhysicalInputId: selectedPhysicalInputId,
                selectedPhysicalOutputId: selectedPhysicalOutputId,
                reason: "automatic app launch",
                startedDetail: "automatic non-recording route engine active",
                logger: logger
            )
        }
    }

    public func startExperimentalRoute(
        selectedPhysicalInputId: String? = nil,
        selectedPhysicalOutputId: String? = nil,
        logger: Logger
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
        logger: Logger
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
            stateStorage = .inactive
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

    private func startRouteLocked(
        selectedPhysicalInputId: String?,
        selectedPhysicalOutputId: String?,
        reason: String,
        startedDetail: String,
        logger: Logger
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
        do {
            let bridge = try PassthroughBridge(
                selectedPhysicalInputId: selectedPhysicalInputId,
                selectedPhysicalOutputId: selectedPhysicalOutputId
            )
            try bridge.start()
            bridge.refreshAppIOHeartbeat()
            self.bridge = bridge
            startHeartbeatTimer(for: bridge)
            stateStorage = .active
            logger("passthrough_bridge_started", startedDetail)
        } catch {
            stopHeartbeatTimer()
            bridge = nil
            sharedMemory?.clearAppHeartbeat()
            stateStorage = .failed(String(describing: error))
            logger("passthrough_bridge_failed", String(describing: error))
        }
        return stateStorage
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

    private func startHeartbeatTimer(for bridge: PassthroughBridge) {
        stopHeartbeatTimer()
        let timer = DispatchSource.makeTimerSource(queue: queue)
        timer.schedule(deadline: .now() + 1.0, repeating: 1.0)
        timer.setEventHandler { [weak bridge] in
            bridge?.refreshAppIOHeartbeat()
        }
        heartbeatTimer = timer
        timer.resume()
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
