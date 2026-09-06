import Foundation
import TwoBrainRecShared

public enum MacOSAudioOwnershipObserverPhase: String, Equatable, Sendable {
    case snapshotStarted = "snapshot_started"
    case snapshotCompleted = "snapshot_completed"
    case snapshotUnavailable = "snapshot_unavailable"
    case liveStarted = "live_started"
    case unexpectedFinish = "unexpected_finish"
    case retryScheduled = "retry_scheduled"
}

public enum MacOSAudioOwnershipObservation: Equatable, Sendable {
    case reconcile(generation: Int)
    case snapshot(events: [MacOSAudioOwnershipEvent], generation: Int)
    case lifecycle(phase: MacOSAudioOwnershipObserverPhase, generation: Int)
    case ownership(MacOSAudioOwnershipEvent)
}

public final class MacOSAudioOwnershipLogStream: @unchecked Sendable {
    private let configuration: MacOSAudioOwnershipLogStreamConfiguration
    private let parser: MacOSAudioOwnershipParser
    private let stateQueue = DispatchQueue(label: "pro.2brain.graf.audio-ownership-log-stream")
    private var process: Process?
    private var stopRequested = false
    private var restartRequested = false

    public init(
        configuration: MacOSAudioOwnershipLogStreamConfiguration = MacOSAudioOwnershipLogStreamConfiguration(),
        parser: MacOSAudioOwnershipParser = MacOSAudioOwnershipParser()
    ) {
        self.configuration = configuration
        self.parser = parser
    }

    public func observations() -> AsyncStream<MacOSAudioOwnershipObservation> {
        AsyncStream { continuation in
            let supervisor = Task.detached(priority: .utility) { [weak self] in
                guard let self else {
                    continuation.finish()
                    return
                }
                await self.runSupervisor(continuation: continuation)
            }
            continuation.onTermination = { [weak self] _ in
                supervisor.cancel()
                self?.stop()
            }
        }
    }

    public func restart() {
        let currentProcess = stateQueue.sync { () -> Process? in
            guard !stopRequested else { return nil }
            restartRequested = true
            return process
        }
        if currentProcess?.isRunning == true {
            currentProcess?.terminate()
        }
    }

    public func stop() {
        let currentProcess = stateQueue.sync { () -> Process? in
            stopRequested = true
            restartRequested = false
            let current = process
            process = nil
            return current
        }
        if currentProcess?.isRunning == true {
            currentProcess?.terminate()
        }
    }

    private func runSupervisor(
        continuation: AsyncStream<MacOSAudioOwnershipObservation>.Continuation
    ) async {
        var generation = 0
        while !Task.isCancelled, !isStopped {
            generation += 1
            clearPendingRestart()
            var activeSensorMicBundleIDs: Set<String> = []
            continuation.yield(.reconcile(generation: generation))
            continuation.yield(.lifecycle(phase: .snapshotStarted, generation: generation))

            let snapshot = runChild(
                arguments: configuration.snapshotArguments,
                mode: .snapshot,
                timeoutNanoseconds: configuration.snapshotTimeoutNanoseconds,
                activeSensorMicBundleIDs: &activeSensorMicBundleIDs,
                continuation: continuation
            )
            guard !snapshot.stopped, !Task.isCancelled else { break }
            if snapshot.restartRequested || consumePendingRestart() {
                continue
            }
            if snapshot.started,
               snapshot.terminationStatus == 0,
               let currentSensorMicBundleIDs = snapshot.currentSensorMicBundleIDs {
                let observedAt = Date()
                let events = currentSensorMicBundleIDs.sorted().map {
                    MacOSAudioOwnershipEvent(
                        bundleID: $0,
                        source: .sensorIndicator,
                        state: .active,
                        observedAt: observedAt
                    )
                }
                continuation.yield(.snapshot(events: events, generation: generation))
                continuation.yield(.lifecycle(phase: .snapshotCompleted, generation: generation))
            } else {
                activeSensorMicBundleIDs.removeAll(keepingCapacity: true)
                continuation.yield(.lifecycle(phase: .snapshotUnavailable, generation: generation))
            }

            continuation.yield(.lifecycle(phase: .liveStarted, generation: generation))
            let live = runChild(
                arguments: configuration.arguments,
                mode: .live,
                timeoutNanoseconds: configuration.liveRefreshTimeoutNanoseconds,
                activeSensorMicBundleIDs: &activeSensorMicBundleIDs,
                continuation: continuation
            )
            guard !live.stopped, !Task.isCancelled else { break }
            if live.restartRequested || consumePendingRestart() {
                continue
            }
            if !(await scheduleRetry(generation: generation, continuation: continuation)) {
                break
            }
        }
        continuation.finish()
    }

    private func scheduleRetry(
        generation: Int,
        continuation: AsyncStream<MacOSAudioOwnershipObservation>.Continuation
    ) async -> Bool {
        continuation.yield(.lifecycle(phase: .unexpectedFinish, generation: generation))
        continuation.yield(.lifecycle(phase: .retryScheduled, generation: generation))
        do {
            try await Task.sleep(nanoseconds: configuration.restartDelayNanoseconds)
            return !Task.isCancelled && !isStopped
        } catch {
            return false
        }
    }

    private func runChild(
        arguments: [String],
        mode: ChildMode,
        timeoutNanoseconds: UInt64?,
        activeSensorMicBundleIDs: inout Set<String>,
        continuation: AsyncStream<MacOSAudioOwnershipObservation>.Continuation
    ) -> ChildResult {
        let child = Process()
        let output = Pipe()
        child.executableURL = configuration.executableURL
        child.arguments = arguments
        child.standardOutput = output
        child.standardError = Pipe()

        guard register(child) else {
            return currentChildResult(started: false, terminationStatus: nil)
        }
        do {
            try child.run()
        } catch {
            return complete(
                child,
                started: false,
                terminationStatus: nil,
                currentSensorMicBundleIDs: nil
            )
        }
        if shouldInterrupt(child), child.isRunning {
            child.terminate()
        }
        let timeoutWorkItem = timeoutNanoseconds.map { timeout in
            let item = DispatchWorkItem { [weak child] in
                guard let child, child.isRunning else { return }
                child.terminate()
            }
            DispatchQueue.global(qos: .utility).asyncAfter(
                deadline: .now() + .nanoseconds(Int(timeout)),
                execute: item
            )
            return item
        }

        let reader = output.fileHandleForReading
        var pending = ""
        var currentSensorMicBundleIDs: Set<String>?
        while !Task.isCancelled {
            let data = reader.availableData
            if data.isEmpty {
                break
            }
            pending += String(decoding: data, as: UTF8.self)
            let lines = pending.split(separator: "\n", omittingEmptySubsequences: false)
            pending = lines.last.map(String.init) ?? ""
            for line in lines.dropLast() {
                processLine(
                    from: String(line),
                    mode: mode,
                    activeSensorMicBundleIDs: &activeSensorMicBundleIDs,
                    currentSensorMicBundleIDs: &currentSensorMicBundleIDs,
                    continuation: continuation
                )
            }
        }
        if !pending.isEmpty {
            processLine(
                from: pending,
                mode: mode,
                activeSensorMicBundleIDs: &activeSensorMicBundleIDs,
                currentSensorMicBundleIDs: &currentSensorMicBundleIDs,
                continuation: continuation
            )
        }
        child.waitUntilExit()
        timeoutWorkItem?.cancel()
        try? reader.close()
        return complete(
            child,
            started: true,
            terminationStatus: child.terminationStatus,
            currentSensorMicBundleIDs: currentSensorMicBundleIDs
        )
    }

    private func processLine(
        from line: String,
        mode: ChildMode,
        activeSensorMicBundleIDs: inout Set<String>,
        currentSensorMicBundleIDs: inout Set<String>?,
        continuation: AsyncStream<MacOSAudioOwnershipObservation>.Continuation
    ) {
        if mode == .snapshot {
            guard parser.isSensorIndicatorAttributionLine(line) else { return }
            guard let bundleIDs = parser.parseSensorIndicatorMicrophoneBundleIDs(line: line) else {
                activeSensorMicBundleIDs.removeAll(keepingCapacity: true)
                currentSensorMicBundleIDs = nil
                return
            }
            activeSensorMicBundleIDs = bundleIDs
            currentSensorMicBundleIDs = bundleIDs
            return
        }
        for event in Self.events(
            from: line,
            parser: parser,
            activeSensorMicBundleIDs: &activeSensorMicBundleIDs
        ) {
            continuation.yield(.ownership(event))
        }
    }

    private func register(_ child: Process) -> Bool {
        stateQueue.sync {
            guard !stopRequested, !restartRequested else { return false }
            process = child
            return true
        }
    }

    private func shouldInterrupt(_ child: Process) -> Bool {
        stateQueue.sync {
            stopRequested || restartRequested || process !== child
        }
    }

    private func complete(
        _ child: Process,
        started: Bool,
        terminationStatus: Int32?,
        currentSensorMicBundleIDs: Set<String>?
    ) -> ChildResult {
        stateQueue.sync {
            if process === child {
                process = nil
            }
            return ChildResult(
                started: started,
                terminationStatus: terminationStatus,
                stopped: stopRequested,
                restartRequested: restartRequested,
                currentSensorMicBundleIDs: currentSensorMicBundleIDs
            )
        }
    }

    private var isStopped: Bool {
        stateQueue.sync { stopRequested }
    }

    private func clearPendingRestart() {
        stateQueue.sync {
            restartRequested = false
        }
    }

    private func consumePendingRestart() -> Bool {
        stateQueue.sync {
            let pending = restartRequested
            restartRequested = false
            return pending
        }
    }

    private func currentChildResult(started: Bool, terminationStatus: Int32?) -> ChildResult {
        stateQueue.sync {
            ChildResult(
                started: started,
                terminationStatus: terminationStatus,
                stopped: stopRequested,
                restartRequested: restartRequested,
                currentSensorMicBundleIDs: nil
            )
        }
    }

    static func events(
        from line: String,
        parser: MacOSAudioOwnershipParser,
        activeSensorMicBundleIDs: inout Set<String>,
        observedAt: Date = Date()
    ) -> [MacOSAudioOwnershipEvent] {
        if let currentSensorMicBundleIDs = parser.parseSensorIndicatorMicrophoneBundleIDs(line: line) {
            let started = currentSensorMicBundleIDs.subtracting(activeSensorMicBundleIDs).sorted()
            let ended = activeSensorMicBundleIDs.subtracting(currentSensorMicBundleIDs).sorted()
            activeSensorMicBundleIDs = currentSensorMicBundleIDs
            return started.map {
                MacOSAudioOwnershipEvent(
                    bundleID: $0,
                    source: .sensorIndicator,
                    state: .active,
                    observedAt: observedAt
                )
            } + ended.map {
                MacOSAudioOwnershipEvent(
                    bundleID: $0,
                    source: .sensorIndicator,
                    state: .inactive,
                    observedAt: observedAt
                )
            }
        }
        return parser.parse(line: line, observedAt: observedAt).map { [$0] } ?? []
    }
}

private struct ChildResult: Sendable {
    let started: Bool
    let terminationStatus: Int32?
    let stopped: Bool
    let restartRequested: Bool
    let currentSensorMicBundleIDs: Set<String>?
}

private enum ChildMode: Sendable {
    case snapshot
    case live
}
