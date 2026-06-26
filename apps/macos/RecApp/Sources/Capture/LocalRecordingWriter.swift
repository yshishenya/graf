import AVFoundation
import Foundation
import TwoBrainRecShared

public enum LocalRecordingWriterError: Error {
    case alreadyRecording
    case notRecording
    case directoryUnavailable
}

public struct LiveRecordingLevels: Equatable, Sendable {
    public var isRecording: Bool
    public var microphoneLevel: Double
    public var incomingLevel: Double
    public var microphoneUpdatedAt: Date?
    public var incomingUpdatedAt: Date?

    public init(
        isRecording: Bool,
        microphoneLevel: Double,
        incomingLevel: Double,
        microphoneUpdatedAt: Date?,
        incomingUpdatedAt: Date?
    ) {
        self.isRecording = isRecording
        self.microphoneLevel = Self.clamp(microphoneLevel)
        self.incomingLevel = Self.clamp(incomingLevel)
        self.microphoneUpdatedAt = microphoneUpdatedAt
        self.incomingUpdatedAt = incomingUpdatedAt
    }

    public static let inactive = LiveRecordingLevels(
        isRecording: false,
        microphoneLevel: 0,
        incomingLevel: 0,
        microphoneUpdatedAt: nil,
        incomingUpdatedAt: nil
    )

    public func microphoneIsLive(now: Date = Date(), staleAfter: TimeInterval = 2) -> Bool {
        isFresh(microphoneUpdatedAt, now: now, staleAfter: staleAfter)
    }

    public func incomingIsLive(now: Date = Date(), staleAfter: TimeInterval = 2) -> Bool {
        isFresh(incomingUpdatedAt, now: now, staleAfter: staleAfter)
    }

    private func isFresh(_ date: Date?, now: Date, staleAfter: TimeInterval) -> Bool {
        guard isRecording, let date else { return false }
        let age = now.timeIntervalSince(date)
        return age >= 0 && age <= staleAfter
    }

    private static func clamp(_ value: Double) -> Double {
        min(1, max(0, value.isFinite ? value : 0))
    }
}

public protocol LocalRecordingSampleSource: Sendable {
    func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int
}

public final class BufferedLocalRecordingSampleSource: LocalRecordingSampleSource, @unchecked Sendable {
    private let lock = NSLock()
    private var buffer: [Float] = []
    private var readOffset = 0
    private let capacity: Int
    private let channelCount: Int
    private var totalAppendedFrameCount: Int64 = 0
    private var lastAppendAt: Date?

    public init(capacity: Int = 48_000 * 20, channelCount: Int = 2) {
        self.capacity = capacity
        self.channelCount = max(1, channelCount)
    }

    public convenience init(capacity: Int) {
        self.init(capacity: capacity, channelCount: 2)
    }

    public func append(_ samples: [Float], at date: Date = Date()) {
        guard !samples.isEmpty else { return }
        lock.lock()
        buffer.append(contentsOf: samples)
        trimUnreadSamplesToCapacity()
        compactIfNeeded()
        totalAppendedFrameCount += Int64((samples.count + channelCount - 1) / channelCount)
        lastAppendAt = date
        lock.unlock()
    }

    public func stats() -> (frameCount: Int64, lastFrameAt: Date?) {
        lock.lock()
        defer { lock.unlock() }
        return (totalAppendedFrameCount, lastAppendAt)
    }

    public func reset() {
        lock.lock()
        buffer.removeAll(keepingCapacity: true)
        readOffset = 0
        totalAppendedFrameCount = 0
        lastAppendAt = nil
        lock.unlock()
    }

    public func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int {
        lock.lock()
        defer { lock.unlock() }
        let count = min(capacity, unreadCount)
        guard count > 0 else {
            compactIfNeeded()
            return 0
        }
        for index in 0..<count {
            destination[index] = buffer[readOffset + index]
        }
        readOffset += count
        compactIfNeeded()
        return count
    }

    private var unreadCount: Int {
        buffer.count - readOffset
    }

    private func trimUnreadSamplesToCapacity() {
        let overflow = unreadCount - capacity
        if overflow > 0 {
            readOffset += overflow
        }
    }

    private func compactIfNeeded() {
        guard readOffset > 0 else { return }
        if readOffset == buffer.count {
            buffer.removeAll(keepingCapacity: true)
            readOffset = 0
            return
        }
        if readOffset >= 16_384 || readOffset > buffer.count / 2 {
            buffer.removeFirst(readOffset)
            readOffset = 0
        }
    }
}

public final class SharedMemoryRecordingSampleSource: LocalRecordingSampleSource, @unchecked Sendable {
    private let sharedMemory: SharedAudioMemory

    public init(sharedMemory: SharedAudioMemory) {
        self.sharedMemory = sharedMemory
    }

    public func readSamples(into destination: UnsafeMutablePointer<Float>, capacity: Int) -> Int {
        let available = min(Int(sharedMemory.captureAvailable()), capacity)
        guard available > 0 else { return 0 }
        return sharedMemory.readCapture(dst: destination, count: available)
    }
}

public final class LocalRecordingWriter: @unchecked Sendable {
    private static let maxDrainReadIterations = 64
    private static let acceptableStopTailPaddingMs = 100

    private let store: LocalRecordingStore
    private let manifestService: LocalRecordingManifestService
    private let leakageFinalizationService: LeakageFinalizationService
    private let routeMetadataService: RecordingRouteMetadataService
    private let microphoneSampleSourceFactory: @Sendable () -> LocalRecordingSampleSource?
    private let incomingSampleSourceFactory: @Sendable () -> LocalRecordingSampleSource?
    private let microphoneInputChannelCount: Int
    private let incomingInputChannelCount: Int
    private let recordMicrophone: Bool
    private let queue = DispatchQueue(label: "pro.2brain.rec.local-recording-writer", qos: .utility)
    private var active: ActiveRecording?

    public init(
        store: LocalRecordingStore = LocalRecordingStore(),
        manifestService: LocalRecordingManifestService = LocalRecordingManifestService(),
        leakageFinalizationService: LeakageFinalizationService = LeakageFinalizationService(),
        routeMetadataService: RecordingRouteMetadataService = RecordingRouteMetadataService(),
        sharedMemoryFactory: @escaping @Sendable () -> SharedAudioMemory? = { SharedAudioMemory() },
        microphoneSampleSourceFactory: @escaping @Sendable () -> LocalRecordingSampleSource? = { nil },
        incomingSampleSourceFactory: (@Sendable () -> LocalRecordingSampleSource?)? = nil,
        microphoneInputChannelCount: Int = 1,
        incomingInputChannelCount: Int = 1,
        recordMicrophone: Bool = true
    ) {
        self.store = store
        self.manifestService = manifestService
        self.leakageFinalizationService = leakageFinalizationService
        self.routeMetadataService = routeMetadataService
        self.microphoneSampleSourceFactory = microphoneSampleSourceFactory
        self.microphoneInputChannelCount = max(1, microphoneInputChannelCount)
        self.incomingInputChannelCount = max(1, incomingInputChannelCount)
        self.incomingSampleSourceFactory = incomingSampleSourceFactory ?? {
            sharedMemoryFactory().map { SharedMemoryRecordingSampleSource(sharedMemory: $0) }
        }
        self.recordMicrophone = recordMicrophone
    }

    public var isRecording: Bool {
        queue.sync { active != nil }
    }

    public func isRecordingAsync() async -> Bool {
        await withCheckedContinuation { continuation in
            queue.async {
                continuation.resume(returning: self.active != nil)
            }
        }
    }

    public func currentLevels(now: Date = Date()) -> LiveRecordingLevels {
        queue.sync { currentLevelsOnQueue(now: now) }
    }

    public func currentLevelsAsync(now: Date = Date()) async -> LiveRecordingLevels {
        await withCheckedContinuation { continuation in
            queue.async {
                continuation.resume(returning: self.currentLevelsOnQueue(now: now))
            }
        }
    }

    private func currentLevelsOnQueue(now: Date) -> LiveRecordingLevels {
        guard let active else { return .inactive }
        var microphoneLevel = active.lastMicrophoneLevel
        var microphoneUpdatedAt = active.lastMicrophoneFrameAt
        if let recorder = active.microphoneRecorder, recorder.isRecording {
            recorder.updateMeters()
            microphoneLevel = Self.normalizedPower(recorder.averagePower(forChannel: 0))
            microphoneUpdatedAt = now
            active.lastMicrophoneLevel = microphoneLevel
            active.lastMicrophoneFrameAt = now
        }
        return LiveRecordingLevels(
            isRecording: true,
            microphoneLevel: microphoneLevel,
            incomingLevel: active.lastIncomingLevel,
            microphoneUpdatedAt: microphoneUpdatedAt,
            incomingUpdatedAt: active.lastIncomingFrameAt
        )
    }

    public func start(
        sessionId: String,
        startedAt: Date,
        scopeApproval: CaptureScopeApproval? = nil,
        permissions: SystemAudioPermissionSnapshot? = nil,
        microphoneSelection: RecordingMicrophoneSelection? = nil,
        targetMuteCapability: TargetMuteCapability? = nil,
        meetingMuteTruthEvidence: [MeetingMuteTruthEvidence] = [],
        limitationCopyShownAt: Date? = nil,
        appleProcessingOutcome: AppleProcessingOutcome? = nil,
        webRTCAEC3Outcome: WebRTCAEC3DecisionRecord? = nil
    ) throws -> LocalRecordingDirectory {
        try queue.sync {
            try startOnQueue(
                sessionId: sessionId,
                startedAt: startedAt,
                scopeApproval: scopeApproval,
                permissions: permissions,
                microphoneSelection: microphoneSelection,
                targetMuteCapability: targetMuteCapability,
                meetingMuteTruthEvidence: meetingMuteTruthEvidence,
                limitationCopyShownAt: limitationCopyShownAt,
                appleProcessingOutcome: appleProcessingOutcome,
                webRTCAEC3Outcome: webRTCAEC3Outcome
            )
        }
    }

    public func startAsync(
        sessionId: String,
        startedAt: Date,
        scopeApproval: CaptureScopeApproval? = nil,
        permissions: SystemAudioPermissionSnapshot? = nil,
        microphoneSelection: RecordingMicrophoneSelection? = nil,
        targetMuteCapability: TargetMuteCapability? = nil,
        meetingMuteTruthEvidence: [MeetingMuteTruthEvidence] = [],
        limitationCopyShownAt: Date? = nil,
        appleProcessingOutcome: AppleProcessingOutcome? = nil,
        webRTCAEC3Outcome: WebRTCAEC3DecisionRecord? = nil
    ) async throws -> LocalRecordingDirectory {
        try await withCheckedThrowingContinuation { continuation in
            queue.async {
                do {
                    let directory = try self.startOnQueue(
                        sessionId: sessionId,
                        startedAt: startedAt,
                        scopeApproval: scopeApproval,
                        permissions: permissions,
                        microphoneSelection: microphoneSelection,
                        targetMuteCapability: targetMuteCapability,
                        meetingMuteTruthEvidence: meetingMuteTruthEvidence,
                        limitationCopyShownAt: limitationCopyShownAt,
                        appleProcessingOutcome: appleProcessingOutcome,
                        webRTCAEC3Outcome: webRTCAEC3Outcome
                    )
                    continuation.resume(returning: directory)
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    private func startOnQueue(
        sessionId: String,
        startedAt: Date,
        scopeApproval: CaptureScopeApproval?,
        permissions: SystemAudioPermissionSnapshot?,
        microphoneSelection: RecordingMicrophoneSelection?,
        targetMuteCapability: TargetMuteCapability?,
        meetingMuteTruthEvidence: [MeetingMuteTruthEvidence],
        limitationCopyShownAt: Date?,
        appleProcessingOutcome: AppleProcessingOutcome?,
        webRTCAEC3Outcome: WebRTCAEC3DecisionRecord?
    ) throws -> LocalRecordingDirectory {
        guard active == nil else { throw LocalRecordingWriterError.alreadyRecording }
        let directory: LocalRecordingDirectory
        do {
            directory = try store.createDirectory(sessionId: sessionId)
        } catch {
            throw LocalRecordingWriterError.directoryUnavailable
        }

        var startSucceeded = false
        var microphoneForCleanup: AVAudioRecorder?
        var microphoneWriterForCleanup: PCM16MonoWAVFileWriter?
        var remoteWriterForCleanup: PCM16MonoWAVFileWriter?
        var scratchForCleanup: UnsafeMutablePointer<Float>?
        defer {
            if !startSucceeded {
                microphoneForCleanup?.stop()
                try? microphoneWriterForCleanup?.close()
                try? remoteWriterForCleanup?.close()
                scratchForCleanup?.deallocate()
                try? FileManager.default.removeItem(at: directory.directoryURL)
            }
        }

        let rawMicrophoneSampleSource = microphoneSampleSourceFactory()
        let privacySuppressingSource = rawMicrophoneSampleSource.map {
            PrivacySuppressingSampleSource(base: $0)
        }
        let microphoneSampleSource: LocalRecordingSampleSource? = privacySuppressingSource ?? rawMicrophoneSampleSource
        let microphoneWriter: PCM16MonoWAVFileWriter?
        let microphone: AVAudioRecorder?
        if let microphoneSampleSource {
            microphone = nil
            microphoneWriter = try PCM16MonoWAVFileWriter(
                url: directory.localMicURL,
                inputChannelCount: microphoneInputChannelCount
            )
            microphoneWriterForCleanup = microphoneWriter
            _ = microphoneSampleSource
        } else {
            microphoneWriter = nil
            microphone = try Self.makeMicrophoneRecorder(url: directory.localMicURL)
            microphoneForCleanup = microphone
        }
        if recordMicrophone, microphoneSampleSource == nil {
            microphone?.isMeteringEnabled = true
            microphone?.record()
        } else if microphoneSampleSource == nil {
            try LocalCustodyFileProtection.createEmptyFile(at: directory.localMicURL)
        }

        let remoteWriter = try PCM16MonoWAVFileWriter(
            url: directory.remoteSpeakerURL,
            inputChannelCount: incomingInputChannelCount
        )
        remoteWriterForCleanup = remoteWriter
        let incomingSampleSource = incomingSampleSourceFactory()
        let timer = DispatchSource.makeTimerSource(queue: queue)
        let scratch = UnsafeMutablePointer<Float>.allocate(capacity: 8192)
        scratchForCleanup = scratch
        timer.schedule(deadline: .now(), repeating: .milliseconds(50))
        timer.setEventHandler { [weak self] in
            guard let self, let active = self.active else { return }
            if let microphoneSampleSource = active.microphoneSampleSource,
               let microphoneWriter = active.microphoneWriter {
                let read = microphoneSampleSource.readSamples(into: active.scratch, capacity: active.scratchCapacity)
                if read > 0 {
                    do {
                        try microphoneWriter.write(samples: active.scratch, count: read)
                        let level = Self.rmsLevel(samples: active.scratch, count: read)
                        active.updateMicrophoneLevel(
                            level,
                            at: Date(),
                            suppressed: active.privacySuppressingSource?.lastReadWasSuppressed == true
                        )
                    } catch {
                        active.microphoneWriteFailed = true
                    }
                }
            }
            guard let incomingSampleSource = active.incomingSampleSource else { return }
            let incomingRead = incomingSampleSource.readSamples(into: active.scratch, capacity: active.scratchCapacity)
            if incomingRead > 0 {
                do {
                    try active.remoteWriter.write(samples: active.scratch, count: incomingRead)
                    active.lastIncomingLevel = Self.rmsLevel(samples: active.scratch, count: incomingRead)
                    active.lastIncomingFrameAt = Date()
                } catch {
                    active.incomingWriteFailed = true
                }
            }
        }

        let activeRecording = ActiveRecording(
            sessionId: sessionId,
            startedAt: startedAt,
            directory: directory,
            microphoneRecorder: microphone,
            microphoneWriter: microphoneWriter,
            microphoneSampleSource: microphoneSampleSource,
            remoteWriter: remoteWriter,
            incomingSampleSource: incomingSampleSource,
            timer: timer,
            scratch: scratch,
            scratchCapacity: 8192,
            scopeApproval: scopeApproval,
            permissions: permissions,
            microphoneSelection: microphoneSelection,
            privacySuppressingSource: privacySuppressingSource,
            targetMuteCapability: targetMuteCapability,
            meetingMuteTruthEvidence: meetingMuteTruthEvidence,
            limitationCopyShownAt: limitationCopyShownAt,
            appleProcessingOutcome: appleProcessingOutcome,
            webRTCAEC3Outcome: webRTCAEC3Outcome
        )
        active = activeRecording
        startSucceeded = true
        timer.resume()
        return directory
    }

    public func pausePrivacy(startedAt: Date = Date()) throws {
        try queue.sync {
            try pausePrivacyOnQueue(startedAt: startedAt)
        }
    }

    public func pausePrivacyAsync(startedAt: Date = Date()) async throws {
        try await withCheckedThrowingContinuation { continuation in
            queue.async {
                do {
                    try self.pausePrivacyOnQueue(startedAt: startedAt)
                    continuation.resume()
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    public func resumePrivacy(endedAt: Date = Date()) throws {
        try queue.sync {
            try resumePrivacyOnQueue(endedAt: endedAt)
        }
    }

    public func resumePrivacyAsync(endedAt: Date = Date()) async throws {
        try await withCheckedThrowingContinuation { continuation in
            queue.async {
                do {
                    try self.resumePrivacyOnQueue(endedAt: endedAt)
                    continuation.resume()
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    private func pausePrivacyOnQueue(startedAt: Date) throws {
        guard let active else { throw LocalRecordingWriterError.notRecording }
        guard active.activePrivacySegment == nil else { return }
        active.privacySuppressingSource?.update(state: .paused)
        active.microphoneRecorder?.pause()
        let treatment = localMicTreatment(for: active)
        active.activePrivacySegment = ProductPrivacySegment(
            segmentId: "\(active.sessionId)-privacy-\(active.privacySegments.count + 1)",
            sessionId: active.sessionId,
            control: .pause,
            startedAt: startedAt,
            startMonotonicMs: monotonicMs(for: startedAt, relativeTo: active.startedAt),
            localMicTreatment: treatment,
            initiator: .user,
            diagnosticSafe: true
        )
    }

    private func resumePrivacyOnQueue(endedAt: Date) throws {
        guard let active else { throw LocalRecordingWriterError.notRecording }
        active.privacySuppressingSource?.update(state: .capturing)
        if recordMicrophone {
            active.microphoneRecorder?.record()
        }
        finalizeActivePrivacySegment(for: active, endedAt: endedAt, treatment: localMicTreatment(for: active))
    }

    public func stop(
        stoppedAt: Date = Date(),
        failureReason: LocalRecordingFailureReason = .none
    ) throws -> LocalRecordingManifest {
        try queue.sync {
            try stopOnQueue(stoppedAt: stoppedAt, failureReason: failureReason)
        }
    }

    public func stopAsync(
        stoppedAt: Date = Date(),
        failureReason: LocalRecordingFailureReason = .none
    ) async throws -> LocalRecordingManifest {
        try await withCheckedThrowingContinuation { continuation in
            queue.async {
                do {
                    continuation.resume(
                        returning: try self.stopOnQueue(
                            stoppedAt: stoppedAt,
                            failureReason: failureReason
                        )
                    )
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    private func stopOnQueue(
        stoppedAt: Date,
        failureReason: LocalRecordingFailureReason
    ) throws -> LocalRecordingManifest {
        guard let active else { throw LocalRecordingWriterError.notRecording }
        active.privacySuppressingSource?.update(state: .stopping)
        finalizeActivePrivacySegment(for: active, endedAt: stoppedAt, treatment: localMicTreatment(for: active))
        active.timer.cancel()
        defer {
            active.microphoneRecorder?.stop()
            try? active.microphoneWriter?.close()
            try? active.remoteWriter.close()
            active.scratch.deallocate()
            self.active = nil
        }
        let drainResult = try drainPendingSamples(for: active)
        active.microphoneRecorder?.stop()
        let elapsedDurationMs = Int(max(0, stoppedAt.timeIntervalSince(active.startedAt) * 1000))
        let elapsedFrameCount = Int64(max(0, stoppedAt.timeIntervalSince(active.startedAt) * 16_000))
        let paddingResult = try padTimelineSilence(for: active, targetFrameCount: Int(elapsedFrameCount))
        try active.microphoneWriter?.close()
        try active.remoteWriter.close()

        let micTrack = track(
            role: .localMic,
            url: active.directory.localMicURL,
            durationMs: active.microphoneWriter?.durationMs ?? elapsedDurationMs,
            frameCount: Int64(active.microphoneWriter?.frameCount ?? Int(elapsedFrameCount)),
            fileName: "mic.wav",
            timelineAligned: true,
            observedLevel: active.microphoneFrameObserved
                ? (active.microphoneNonSilentFrameObserved ? max(active.lastObservedMicrophoneLevel ?? 0, 0.0001) : 0)
                : nil,
            paddedToTimeline: paddingResult.microphonePadded,
            paddedFrameCount: paddingResult.microphonePaddedFrameCount,
            forcedFailureReason: drainResult.microphoneTruncated || active.microphoneWriteFailed ? .writeFailed : nil
        )
        let timelineToleranceMs = 1_000
        let remoteTimelineAligned = abs(active.remoteWriter.durationMs - micTrack.durationMs) <= timelineToleranceMs
        let remoteTrack = track(
            role: .remoteSpeaker,
            url: active.directory.remoteSpeakerURL,
            durationMs: active.remoteWriter.durationMs,
            frameCount: Int64(active.remoteWriter.frameCount),
            fileName: "incoming.wav",
            timelineAligned: remoteTimelineAligned,
            observedLevel: active.lastIncomingLevel,
            paddedToTimeline: paddingResult.incomingPadded,
            paddedFrameCount: paddingResult.incomingPaddedFrameCount,
            forcedFailureReason: drainResult.incomingTruncated || active.incomingWriteFailed ? .writeFailed : nil
        )
        let routeMetadata = routeMetadataService.snapshot()
        let leakageFinalization = leakageFinalizationService.finalize(
            micURL: active.directory.localMicURL,
            incomingURL: active.directory.remoteSpeakerURL,
            micTrack: micTrack,
            incomingTrack: remoteTrack,
            routeMetadata: routeMetadata
        )
        let recordingFailureReason = if failureReason != .none {
            failureReason
        } else {
            [remoteTrack, micTrack].first(where: { $0.failureReason != .none })?.failureReason ?? .none
        }
        let captureHealth = CaptureHealthMonitor().snapshot(
            sessionId: active.sessionId,
            phase: .stop,
            micDurationMs: micTrack.durationMs,
            incomingDurationMs: remoteTrack.durationMs,
            micFrameCount: micTrack.frameCount,
            incomingFrameCount: remoteTrack.frameCount,
            silentFrameCount: remoteTrack.failureReason == .silentInput ? remoteTrack.frameCount : 0,
            recordingFailureReason: recordingFailureReason
        )
        let microphoneStream = microphoneStreamSession(for: active, micTrack: micTrack, stoppedAt: stoppedAt)
        let microphoneHealth: MicrophoneStreamHealth?
        if let microphoneStream {
            microphoneHealth = makeMicrophoneStreamHealth(for: microphoneStream, active: active)
        } else {
            microphoneHealth = nil
        }

        let manifest = manifestService.manifest(
            sessionId: active.sessionId,
            directoryId: active.directory.directoryId,
            startedAt: active.startedAt,
            stoppedAt: stoppedAt,
            tracks: [micTrack, remoteTrack],
            leakageFinalization: leakageFinalization,
            failureReason: failureReason,
            scopeApproval: active.scopeApproval,
            permissions: active.permissions,
            microphoneSelection: active.microphoneSelection,
            microphoneStream: microphoneStream,
            microphoneStreamHealth: microphoneHealth,
            appleProcessingOutcome: active.appleProcessingOutcome,
            webRTCAEC3Outcome: active.webRTCAEC3Outcome,
            captureHealth: captureHealth,
            privacySegments: active.privacySegments,
            targetMuteCapability: active.targetMuteCapability,
            meetingMuteTruthEvidence: active.meetingMuteTruthEvidence,
            limitationCopyShownAt: active.limitationCopyShownAt
        )
        try manifestService.write(manifest, to: active.directory.manifestURL)
        return manifest
    }

    private func microphoneStreamSession(
        for active: ActiveRecording,
        micTrack: LocalRecordingTrack,
        stoppedAt: Date
    ) -> AppOwnedMicrophoneStreamSession? {
        guard let microphoneSelection = active.microphoneSelection else { return nil }
        let observedFrameCount = active.microphoneFrameObserved ? micTrack.frameCount : 0
        let streamFailureReason = active.microphoneFrameObserved || micTrack.failureReason != .none
            ? micTrack.failureReason
            : LocalRecordingFailureReason.noFrames
        return AppOwnedMicrophoneStreamSession(
            sessionId: active.sessionId,
            selection: microphoneSelection,
            permissionState: active.permissions?.microphone ?? .unknown,
            streamKind: active.microphoneSampleSource == nil ? .legacyRecorderFallback : .appOwnedSampleSource,
            startedAt: active.startedAt,
            stoppedAt: stoppedAt,
            monotonicStartMs: 0,
            monotonicStopMs: monotonicMs(for: stoppedAt, relativeTo: active.startedAt),
            sampleRate: 48_000,
            channelCount: microphoneInputChannelCount,
            writerSampleRate: 16_000,
            writerChannelCount: 1,
            frameCount: observedFrameCount,
            droppedFrameCount: 0,
            silentFrameCount: streamFailureReason == .silentInput ? observedFrameCount : 0,
            clippedFrameCount: 0,
            routeChangeCount: 0,
            lastFrameAt: active.lastObservedMicrophoneFrameAt,
            failureReason: streamFailureReason
        )
    }

    private func makeMicrophoneStreamHealth(
        for stream: AppOwnedMicrophoneStreamSession,
        active: ActiveRecording
    ) -> MicrophoneStreamHealth {
        let readiness: FutureProcessingReadiness
        if stream.provesGraphReadiness {
            readiness = .readyForFutureProcessing
        } else if stream.streamKind == .legacyRecorderFallback {
            readiness = .legacyNotReady
        } else if stream.permissionState != .granted || !stream.selection.isAccepted {
            readiness = .blocked
        } else {
            readiness = .unproven
        }

        let gateStatus: CaptureHealthGateStatus = switch readiness {
        case .readyForFutureProcessing:
            .passed
        case .blocked:
            .blocked
        case .legacyNotReady, .unproven:
            stream.frameCount > 0 ? .degraded : .failed
        }

        let silenceStatus: MicrophoneSilenceStatus = if stream.failureReason == .silentInput {
            .silent
        } else if stream.frameCount > 0 {
            .audible
        } else {
            .unknown
        }

        return MicrophoneStreamHealth(
            gateStatus: gateStatus,
            failureReason: stream.failureReason,
            framesObserved: stream.frameCount > 0,
            timingConfidence: stream.frameCount > 0 ? .usable : .missing,
            silenceStatus: silenceStatus,
            lastLevel: stream.frameCount > 0 ? active.lastObservedMicrophoneLevel : nil,
            lastLevelAt: stream.lastFrameAt,
            cleanupReadiness: readiness,
            evidenceCodes: microphoneStreamEvidenceCodes(for: stream, readiness: readiness)
        )
    }

    private func microphoneStreamEvidenceCodes(
        for stream: AppOwnedMicrophoneStreamSession,
        readiness: FutureProcessingReadiness
    ) -> [String] {
        var codes: [String] = []
        codes.append(stream.streamKind.rawValue)
        codes.append(stream.selection.mode.rawValue)
        codes.append(readiness.rawValue)
        if stream.frameCount > 0 {
            codes.append("mic_frames_observed")
        }
        if stream.failureReason != .none {
            codes.append(stream.failureReason.rawValue)
        }
        return codes
    }

    private func finalizeActivePrivacySegment(
        for active: ActiveRecording,
        endedAt: Date,
        treatment: ProductPrivacyLocalMicTreatment
    ) {
        guard let segment = active.activePrivacySegment else { return }
        active.privacySegments.append(
            segment.finalized(
                endedAt: endedAt,
                endMonotonicMs: monotonicMs(for: endedAt, relativeTo: active.startedAt),
                treatment: treatment
            )
        )
        active.activePrivacySegment = nil
    }

    private func monotonicMs(for date: Date, relativeTo startedAt: Date) -> Int {
        Int(max(0, date.timeIntervalSince(startedAt) * 1000))
    }

    private func localMicTreatment(for active: ActiveRecording) -> ProductPrivacyLocalMicTreatment {
        active.privacySuppressingSource == nil ? .redacted : .silenced
    }

    private func padTimelineSilence(for active: ActiveRecording, targetFrameCount: Int) throws -> PaddingResult {
        var result = PaddingResult()
        guard targetFrameCount > 0 else { return result }
        if let microphoneWriter = active.microphoneWriter,
           microphoneWriter.frameCount > 0,
           microphoneWriter.frameCount < targetFrameCount {
            let paddingFrameCount = targetFrameCount - microphoneWriter.frameCount
            try microphoneWriter.writeSilence(frameCount: paddingFrameCount)
            result.microphonePadded = true
            result.microphonePaddedFrameCount = paddingFrameCount
        }
        if active.remoteWriter.frameCount > 0,
           active.remoteWriter.frameCount < targetFrameCount {
            let paddingFrameCount = targetFrameCount - active.remoteWriter.frameCount
            try active.remoteWriter.writeSilence(frameCount: paddingFrameCount)
            result.incomingPadded = true
            result.incomingPaddedFrameCount = paddingFrameCount
        }
        return result
    }

    private func drainPendingSamples(for active: ActiveRecording) throws -> DrainResult {
        var result = DrainResult()
        if let microphoneSampleSource = active.microphoneSampleSource,
           let microphoneWriter = active.microphoneWriter {
            result.microphoneTruncated = try drain(
                source: microphoneSampleSource,
                writer: microphoneWriter,
                scratch: active.scratch,
                capacity: active.scratchCapacity
            ) { count in
                let level = Self.rmsLevel(samples: active.scratch, count: count)
                active.updateMicrophoneLevel(
                    level,
                    at: Date(),
                    suppressed: active.privacySuppressingSource?.lastReadWasSuppressed == true
                )
            }
        }

        if let incomingSampleSource = active.incomingSampleSource {
            result.incomingTruncated = try drain(
                source: incomingSampleSource,
                writer: active.remoteWriter,
                scratch: active.scratch,
                capacity: active.scratchCapacity
            ) { count in
                active.lastIncomingLevel = Self.rmsLevel(samples: active.scratch, count: count)
                active.lastIncomingFrameAt = Date()
            }
        }
        return result
    }

    private func drain(
        source: LocalRecordingSampleSource,
        writer: PCM16MonoWAVFileWriter,
        scratch: UnsafeMutablePointer<Float>,
        capacity: Int,
        updateLevel: (Int) -> Void
    ) throws -> Bool {
        var iterations = 0
        while true {
            if iterations >= Self.maxDrainReadIterations {
                return true
            }
            let read = source.readSamples(into: scratch, capacity: capacity)
            guard read > 0 else { return false }
            try writer.write(samples: scratch, count: read)
            updateLevel(read)
            iterations += 1
        }
    }

    public func currentDirectoryURL() -> URL? {
        queue.sync { active?.directory.directoryURL }
    }

    public func currentDirectoryURLAsync() async -> URL? {
        await withCheckedContinuation { continuation in
            queue.async {
                continuation.resume(returning: self.active?.directory.directoryURL)
            }
        }
    }

    private func track(
        role: AudioTrackRole,
        url: URL,
        durationMs: Int,
        frameCount: Int64,
        fileName: String,
        timelineAligned: Bool,
        observedLevel: Double? = nil,
        paddedToTimeline: Bool = false,
        paddedFrameCount: Int = 0,
        forcedFailureReason: LocalRecordingFailureReason? = nil
    ) -> LocalRecordingTrack {
        let byteCount = (try? FileManager.default.attributesOfItem(atPath: url.path)[.size] as? NSNumber)?
            .int64Value ?? 0
        let fileMetadata = Self.audioFileMetadata(url: url)
        let effectiveFrameCount = fileMetadata?.frameCount ?? frameCount
        let effectiveDurationMs = fileMetadata?.durationMs ?? durationMs
        let complete = byteCount > 44 && effectiveFrameCount > 0 && effectiveDurationMs > 0
        let failureReason: LocalRecordingFailureReason
        if let forcedFailureReason {
            failureReason = forcedFailureReason
        } else if complete {
            if observedLevel == 0 {
                failureReason = .silentInput
            } else if paddedToTimeline && Self.paddingDurationMs(paddedFrameCount) > Self.acceptableStopTailPaddingMs {
                failureReason = .timelineMisaligned
            } else {
                failureReason = timelineAligned ? .none : .timelineMisaligned
            }
        } else {
            failureReason = .noFrames
        }
        let status: LocalRecordingTrackStatus = switch failureReason {
        case .none:
            .saved
        case .protectedAudioBlocked:
            .blocked
        case .directoryUnavailable, .captureFailed, .writeFailed, .finalizationFailed:
            .failed
        case .silentInput, .noFrames, .emptyRequiredTrack, .timelineMisaligned, .formatNotReady,
             .permissionDenied, .scopeUnavailable, .cpuGateFailed, .stoppedBeforeFrames,
             .halProbeObserved, .deviceUnavailable, .legacyNotReady, .appClosed,
             .leakageDetected, .leakageUnproven, .leakageNotMeasured,
             .insufficientReference, .derivedResidualLeakage,
             .derivedDeletionNotRegistered, .unknown:
            complete ? .degraded : .missing
        }
        return LocalRecordingTrack(
            trackId: "\(role.rawValue)-track",
            role: role,
            status: status,
            fileName: fileName,
            format: "wav-pcm-s16le",
            sampleRate: 16_000,
            channelCount: 1,
            bitsPerSample: 16,
            durationMs: complete ? effectiveDurationMs : 0,
            byteCount: byteCount,
            frameCount: complete ? effectiveFrameCount : 0,
            timelineStartMs: 0,
            timelineAligned: complete && timelineAligned && failureReason == .none,
            failureReason: failureReason
        )
    }

    private static func audioFileMetadata(url: URL) -> (frameCount: Int64, durationMs: Int)? {
        guard let file = try? AVAudioFile(forReading: url) else { return nil }
        let frameCount = file.length
        guard frameCount > 0 else { return nil }
        let sampleRate = file.fileFormat.sampleRate
        guard sampleRate > 0 else { return nil }
        let durationMs = Int((Double(frameCount) / sampleRate) * 1000)
        return (frameCount, durationMs)
    }

    private static func makeMicrophoneRecorder(url: URL) throws -> AVAudioRecorder? {
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: 16_000,
            AVNumberOfChannelsKey: 1,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsFloatKey: false,
            AVLinearPCMIsBigEndianKey: false
        ]
        let recorder = try AVAudioRecorder(url: url, settings: settings)
        recorder.isMeteringEnabled = true
        recorder.prepareToRecord()
        return recorder
    }

    private static func normalizedPower(_ decibels: Float) -> Double {
        guard decibels.isFinite else { return 0 }
        let floor: Float = -60
        if decibels <= floor { return 0 }
        if decibels >= 0 { return 1 }
        return Double((decibels - floor) / -floor)
    }

    private static func rmsLevel(samples: UnsafePointer<Float>, count: Int) -> Double {
        guard count > 0 else { return 0 }
        var sum: Double = 0
        for index in 0..<count {
            let sample = Double(samples[index])
            sum += sample * sample
        }
        return min(1, sqrt(sum / Double(count)))
    }

    private static func paddingDurationMs(_ frameCount: Int) -> Int {
        Int((Double(max(0, frameCount)) / 16_000.0) * 1000.0)
    }
}

private struct DrainResult {
    var microphoneTruncated = false
    var incomingTruncated = false
}

private struct PaddingResult {
    var microphonePadded = false
    var incomingPadded = false
    var microphonePaddedFrameCount = 0
    var incomingPaddedFrameCount = 0
}

private final class ActiveRecording {
    let sessionId: String
    let startedAt: Date
    let directory: LocalRecordingDirectory
    let microphoneRecorder: AVAudioRecorder?
    let microphoneWriter: PCM16MonoWAVFileWriter?
    let microphoneSampleSource: LocalRecordingSampleSource?
    let remoteWriter: PCM16MonoWAVFileWriter
    let incomingSampleSource: LocalRecordingSampleSource?
    let timer: DispatchSourceTimer
    let scratch: UnsafeMutablePointer<Float>
    let scratchCapacity: Int
    let scopeApproval: CaptureScopeApproval?
    let permissions: SystemAudioPermissionSnapshot?
    let microphoneSelection: RecordingMicrophoneSelection?
    let privacySuppressingSource: PrivacySuppressingSampleSource?
    let targetMuteCapability: TargetMuteCapability?
    let meetingMuteTruthEvidence: [MeetingMuteTruthEvidence]
    let limitationCopyShownAt: Date?
    let appleProcessingOutcome: AppleProcessingOutcome?
    let webRTCAEC3Outcome: WebRTCAEC3DecisionRecord?
    var lastMicrophoneLevel: Double
    var lastObservedMicrophoneLevel: Double?
    var lastIncomingLevel: Double
    var lastMicrophoneFrameAt: Date?
    var lastObservedMicrophoneFrameAt: Date?
    var lastIncomingFrameAt: Date?
    var microphoneFrameObserved: Bool
    var microphoneNonSilentFrameObserved: Bool
    var microphoneWriteFailed: Bool
    var incomingWriteFailed: Bool
    var privacySegments: [ProductPrivacySegment]
    var activePrivacySegment: ProductPrivacySegment?

    init(
        sessionId: String,
        startedAt: Date,
        directory: LocalRecordingDirectory,
        microphoneRecorder: AVAudioRecorder?,
        microphoneWriter: PCM16MonoWAVFileWriter?,
        microphoneSampleSource: LocalRecordingSampleSource?,
        remoteWriter: PCM16MonoWAVFileWriter,
        incomingSampleSource: LocalRecordingSampleSource?,
        timer: DispatchSourceTimer,
        scratch: UnsafeMutablePointer<Float>,
        scratchCapacity: Int,
        scopeApproval: CaptureScopeApproval?,
        permissions: SystemAudioPermissionSnapshot?,
        microphoneSelection: RecordingMicrophoneSelection?,
        privacySuppressingSource: PrivacySuppressingSampleSource?,
        targetMuteCapability: TargetMuteCapability?,
        meetingMuteTruthEvidence: [MeetingMuteTruthEvidence],
        limitationCopyShownAt: Date?,
        appleProcessingOutcome: AppleProcessingOutcome?,
        webRTCAEC3Outcome: WebRTCAEC3DecisionRecord?
    ) {
        self.sessionId = sessionId
        self.startedAt = startedAt
        self.directory = directory
        self.microphoneRecorder = microphoneRecorder
        self.microphoneWriter = microphoneWriter
        self.microphoneSampleSource = microphoneSampleSource
        self.remoteWriter = remoteWriter
        self.incomingSampleSource = incomingSampleSource
        self.timer = timer
        self.scratch = scratch
        self.scratchCapacity = scratchCapacity
        self.scopeApproval = scopeApproval
        self.permissions = permissions
        self.microphoneSelection = microphoneSelection
        self.privacySuppressingSource = privacySuppressingSource
        self.targetMuteCapability = targetMuteCapability
        self.meetingMuteTruthEvidence = meetingMuteTruthEvidence
        self.limitationCopyShownAt = limitationCopyShownAt
        self.appleProcessingOutcome = appleProcessingOutcome
        self.webRTCAEC3Outcome = webRTCAEC3Outcome
        self.lastMicrophoneLevel = 0
        self.lastObservedMicrophoneLevel = nil
        self.lastIncomingLevel = 0
        self.lastMicrophoneFrameAt = nil
        self.lastObservedMicrophoneFrameAt = nil
        self.lastIncomingFrameAt = nil
        self.microphoneFrameObserved = false
        self.microphoneNonSilentFrameObserved = false
        self.microphoneWriteFailed = false
        self.incomingWriteFailed = false
        self.privacySegments = []
        self.activePrivacySegment = nil
    }

    func updateMicrophoneLevel(_ level: Double, at date: Date, suppressed: Bool) {
        lastMicrophoneLevel = level
        lastMicrophoneFrameAt = date
        guard !suppressed else { return }
        microphoneFrameObserved = true
        lastObservedMicrophoneLevel = level
        lastObservedMicrophoneFrameAt = date
        if level > 0 {
            microphoneNonSilentFrameObserved = true
        }
    }
}

struct PCM16MonoDownsampleResult {
    let data: Data
    let frameCount: Int
}

enum PCM16MonoDownsampler {
    static func downsample(
        samples: UnsafePointer<Float>,
        count: Int,
        inputChannelCount: Int,
        inputSampleRate: Int,
        outputSampleRate: Int
    ) -> PCM16MonoDownsampleResult {
        let channelCount = max(1, inputChannelCount)
        let inputFrameCount = count / channelCount
        guard inputFrameCount > 0 else {
            return PCM16MonoDownsampleResult(data: Data(), frameCount: 0)
        }

        let ratio = max(1, inputSampleRate / outputSampleRate)
        var data = Data()
        data.reserveCapacity(((inputFrameCount + ratio - 1) / ratio) * MemoryLayout<Int16>.stride)

        var frameIndex = 0
        var outputFrameCount = 0
        while frameIndex < inputFrameCount {
            let windowFrameCount = min(ratio, inputFrameCount - frameIndex)
            var monoSum: Float = 0

            for windowOffset in 0..<windowFrameCount {
                let sampleIndex = (frameIndex + windowOffset) * channelCount
                var channelSum: Float = 0
                for channelIndex in 0..<channelCount {
                    channelSum += samples[sampleIndex + channelIndex]
                }
                monoSum += channelSum / Float(channelCount)
            }

            let mono = max(-1, min(1, monoSum / Float(windowFrameCount)))
            var intSample = Int16(mono * Float(Int16.max)).littleEndian
            data.append(Data(bytes: &intSample, count: MemoryLayout<Int16>.size))
            outputFrameCount += 1
            frameIndex += ratio
        }

        return PCM16MonoDownsampleResult(data: data, frameCount: outputFrameCount)
    }
}

private final class PCM16MonoWAVFileWriter {
    private let handle: FileHandle
    private(set) var frameCount = 0
    private var isClosed = false
    private let inputSampleRate = 48_000
    private let inputChannelCount: Int
    private let outputSampleRate = 16_000
    private let outputChannelCount = 1
    private let bitsPerSample = 16

    init(url: URL, inputChannelCount: Int = 1) throws {
        self.inputChannelCount = max(1, inputChannelCount)
        try LocalCustodyFileProtection.createEmptyFile(at: url)
        handle = try FileHandle(forWritingTo: url)
        try handle.write(contentsOf: Data(repeating: 0, count: 44))
    }

    var durationMs: Int {
        Int((Double(frameCount) / Double(outputSampleRate)) * 1000)
    }

    func write(samples: UnsafePointer<Float>, count: Int) throws {
        guard !isClosed else { return }
        guard count > 0 else { return }
        let result = PCM16MonoDownsampler.downsample(
            samples: samples,
            count: count,
            inputChannelCount: inputChannelCount,
            inputSampleRate: inputSampleRate,
            outputSampleRate: outputSampleRate
        )
        guard !result.data.isEmpty else { return }
        try handle.write(contentsOf: result.data)
        frameCount += result.frameCount
    }

    func writeSilence(frameCount count: Int) throws {
        guard !isClosed else { return }
        guard count > 0 else { return }
        let chunkFrameCount = 4096
        var remaining = count
        let silence = Data(repeating: 0, count: chunkFrameCount * MemoryLayout<Int16>.stride)
        while remaining > 0 {
            let frames = min(remaining, chunkFrameCount)
            try handle.write(contentsOf: silence.prefix(frames * MemoryLayout<Int16>.stride))
            frameCount += frames
            remaining -= frames
        }
    }

    func close() throws {
        guard !isClosed else { return }
        let dataByteCount = UInt32(frameCount * MemoryLayout<Int16>.stride)
        let riffByteCount = UInt32(36) + dataByteCount
        var header = Data()
        header.append(contentsOf: [0x52, 0x49, 0x46, 0x46])
        header.appendLE(riffByteCount)
        header.append(contentsOf: [0x57, 0x41, 0x56, 0x45])
        header.append(contentsOf: [0x66, 0x6d, 0x74, 0x20])
        header.appendLE(UInt32(16))
        header.appendLE(UInt16(1))
        header.appendLE(UInt16(outputChannelCount))
        header.appendLE(UInt32(outputSampleRate))
        header.appendLE(UInt32(outputSampleRate * outputChannelCount * MemoryLayout<Int16>.stride))
        header.appendLE(UInt16(outputChannelCount * MemoryLayout<Int16>.stride))
        header.appendLE(UInt16(bitsPerSample))
        header.append(contentsOf: [0x64, 0x61, 0x74, 0x61])
        header.appendLE(dataByteCount)
        try handle.seek(toOffset: 0)
        try handle.write(contentsOf: header)
        try handle.close()
        isClosed = true
    }
}

private extension Data {
    mutating func appendLE(_ value: UInt16) {
        var little = value.littleEndian
        append(Data(bytes: &little, count: MemoryLayout<UInt16>.size))
    }

    mutating func appendLE(_ value: UInt32) {
        var little = value.littleEndian
        append(Data(bytes: &little, count: MemoryLayout<UInt32>.size))
    }
}
