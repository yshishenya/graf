import AVFoundation
import CryptoKit
import Foundation
import TwoBrainRecShared

/// Active v5 capture path. It drains independent PTS-bearing source batches and
/// delegates ordering, gaps and mixing to `RecordingAudioTimeline`; it never
/// pairs samples by FIFO position or pads them to a wall-clock stop time.
public final class LocalRecordingWriter: @unchecked Sendable {
    private static let drainInterval = DispatchTimeInterval.milliseconds(10)
    /// A live tick is deliberately bounded so a burst cannot monopolize the
    /// capture queue. Stop uses a larger per-source bound and fails closed only
    /// when the source is still producing beyond that finite drain.
    private static let maximumBatchesPerLiveDrain = 64
    private static let maximumBatchesAtStop = 4_096
    private static let batchFrameLimit = 8_192

    private let store: LocalRecordingStore
    private let manifestService: LocalRecordingManifestService
    private let microphoneSampleSourceFactory: @Sendable () -> LocalRecordingSampleSource?
    private let incomingSampleSourceFactory: @Sendable () -> LocalRecordingSampleSource?
    private let recordMicrophone: Bool
    private let queue = DispatchQueue(label: "pro.2brain.graf.v5-local-recording-writer", qos: .userInitiated)
    private var active: V5ActiveRecording?

    public init(
        store: LocalRecordingStore = LocalRecordingStore(),
        manifestService: LocalRecordingManifestService = LocalRecordingManifestService(),
        microphoneSampleSourceFactory: @escaping @Sendable () -> LocalRecordingSampleSource? = { nil },
        incomingSampleSourceFactory: @escaping @Sendable () -> LocalRecordingSampleSource? = { nil },
        recordMicrophone: Bool = true
    ) {
        self.store = store
        self.manifestService = manifestService
        self.microphoneSampleSourceFactory = microphoneSampleSourceFactory
        self.incomingSampleSourceFactory = incomingSampleSourceFactory
        self.recordMicrophone = recordMicrophone
    }

    public var isRecording: Bool {
        queue.sync { active != nil }
    }

    public func isRecordingAsync() async -> Bool {
        await withCheckedContinuation { continuation in
            queue.async { continuation.resume(returning: self.active != nil) }
        }
    }

    public func currentLevels(now: Date = Date()) -> LiveRecordingLevels {
        queue.sync { levelsOnQueue(now: now) }
    }

    public func currentLevelsAsync(now: Date = Date()) async -> LiveRecordingLevels {
        await withCheckedContinuation { continuation in
            queue.async { continuation.resume(returning: self.levelsOnQueue(now: now)) }
        }
    }

    public func start(
        sessionId: String,
        startedAt: Date,
        scopeApproval: CaptureScopeApproval? = nil,
        permissions: SystemAudioPermissionSnapshot? = nil,
        microphoneSelection: RecordingMicrophoneSelection? = nil,
        targetMuteCapability: TargetMuteCapability? = nil,
        meetingMuteTruthEvidence: [MeetingMuteTruthEvidence] = [],
        limitationCopyShownAt: Date? = nil
    ) throws -> LocalRecordingDirectory {
        return try queue.sync {
            try startOnQueue(
                sessionId: sessionId,
                startedAt: startedAt,
                scopeApproval: scopeApproval,
                permissions: permissions,
                microphoneSelection: microphoneSelection,
                targetMuteCapability: targetMuteCapability,
                meetingMuteTruthEvidence: meetingMuteTruthEvidence,
                limitationCopyShownAt: limitationCopyShownAt
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
        limitationCopyShownAt: Date? = nil
    ) async throws -> LocalRecordingDirectory {
        return try await withCheckedThrowingContinuation { continuation in
            queue.async {
                do {
                    continuation.resume(returning: try self.startOnQueue(
                        sessionId: sessionId,
                        startedAt: startedAt,
                        scopeApproval: scopeApproval,
                        permissions: permissions,
                        microphoneSelection: microphoneSelection,
                        targetMuteCapability: targetMuteCapability,
                        meetingMuteTruthEvidence: meetingMuteTruthEvidence,
                        limitationCopyShownAt: limitationCopyShownAt
                    ))
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    public func pausePrivacy(startedAt: Date = Date()) throws {
        try queue.sync { try pausePrivacyOnQueue(startedAt: startedAt) }
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
        try queue.sync { try resumePrivacyOnQueue(endedAt: endedAt) }
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

    public func stop(
        stoppedAt: Date = Date(),
        failureReason: LocalRecordingFailureReason = .none
    ) throws -> LocalRecordingManifest {
        try queue.sync { try stopOnQueue(stoppedAt: stoppedAt, failureReason: failureReason) }
    }

    public func stopAsync(
        stoppedAt: Date = Date(),
        failureReason: LocalRecordingFailureReason = .none
    ) async throws -> LocalRecordingManifest {
        try await withCheckedThrowingContinuation { continuation in
            queue.async {
                do {
                    continuation.resume(returning: try self.stopOnQueue(
                        stoppedAt: stoppedAt,
                        failureReason: failureReason
                    ))
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    public func currentDirectoryURL() -> URL? {
        queue.sync { active?.directory.directoryURL }
    }

    public func currentDirectoryURLAsync() async -> URL? {
        await withCheckedContinuation { continuation in
            queue.async { continuation.resume(returning: self.active?.directory.directoryURL) }
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
        limitationCopyShownAt: Date?
    ) throws -> LocalRecordingDirectory {
        guard active == nil else { throw LocalRecordingWriterError.alreadyRecording }
        let directory: LocalRecordingDirectory
        do {
            directory = try store.createDirectory(sessionId: sessionId)
        } catch {
            throw LocalRecordingWriterError.directoryUnavailable
        }

        do {
            let rawMicrophoneSource = recordMicrophone ? microphoneSampleSourceFactory() : nil
            let privacySource = rawMicrophoneSource.map { PrivacySuppressingSampleSource(base: $0) }
            let microphoneSource = privacySource ?? (rawMicrophoneSource as? TimestampedLocalRecordingSampleSource)
            let incomingSource = incomingSampleSourceFactory() as? TimestampedLocalRecordingSampleSource
            let canonicalWriter = try CanonicalRecordingWriter(directory: directory)
            let timeline = RecordingAudioTimeline { [canonicalWriter] chunk in
                try canonicalWriter.append(chunk)
            }
            let timer = DispatchSource.makeTimerSource(queue: queue)
            let active = V5ActiveRecording(
                sessionId: sessionId,
                startedAt: startedAt,
                directory: directory,
                canonicalWriter: canonicalWriter,
                timeline: timeline,
                microphoneSource: microphoneSource,
                incomingSource: incomingSource,
                privacySource: privacySource,
                scopeApproval: scopeApproval,
                permissions: permissions,
                microphoneSelection: microphoneSelection,
                targetMuteCapability: targetMuteCapability,
                meetingMuteTruthEvidence: meetingMuteTruthEvidence,
                limitationCopyShownAt: limitationCopyShownAt,
                recordMicrophone: recordMicrophone
            )
            if recordMicrophone && microphoneSource == nil {
                active.recordFailure(.deviceUnavailable)
            }
            if incomingSource == nil {
                active.recordFailure(.deviceUnavailable)
            }
            timer.schedule(deadline: .now(), repeating: Self.drainInterval)
            timer.setEventHandler { [weak self, weak active] in
                guard let self, let active, self.active === active else { return }
                self.drainAvailable(
                    for: active,
                    maximumBatchesPerSource: Self.maximumBatchesPerLiveDrain,
                    failWhenLimitIsReached: false
                )
            }
            self.active = active
            active.timer = timer
            timer.resume()
            return directory
        } catch {
            try? FileManager.default.removeItem(at: directory.directoryURL)
            throw LocalRecordingWriterError.directoryUnavailable
        }
    }

    private func stopOnQueue(
        stoppedAt: Date,
        failureReason: LocalRecordingFailureReason
    ) throws -> LocalRecordingManifest {
        guard let active else { throw LocalRecordingWriterError.notRecording }
        active.timer?.cancel()
        finalizePrivacySegment(for: active, endedAt: stoppedAt)
        defer { self.active = nil }

        drainAvailable(
            for: active,
            maximumBatchesPerSource: Self.maximumBatchesAtStop,
            failWhenLimitIsReached: true
        )
        let resolvedFailure: LocalRecordingFailureReason
        var artifact: CanonicalRecordingArtifact?
        if active.terminalFailureReason == nil, failureReason == .none {
            do {
                try active.timeline.finish()
                artifact = try active.canonicalWriter.finish()
            } catch {
                active.recordFailure(Self.failureReason(for: error))
            }
        }
        if active.terminalFailureReason != nil || failureReason != .none {
            active.canonicalWriter.abort()
            removeFinalArtifacts(in: active.directory)
        }
        resolvedFailure = failureReason != .none
            ? failureReason
            : active.terminalFailureReason ?? .none

        let tracks: [LocalRecordingTrack]
        do {
            tracks = try makeTracks(for: active, artifact: artifact, failureReason: resolvedFailure)
        } catch {
            active.canonicalWriter.abort()
            removeFinalArtifacts(in: active.directory)
            active.recordFailure(.finalizationFailed)
            let finalFailure = failureReason != .none ? failureReason : .finalizationFailed
            tracks = missingTracks(failureReason: finalFailure)
        }

        let microphoneStream = microphoneStream(for: active, stoppedAt: stoppedAt)
        let microphoneHealth = microphoneStream.map { stream in
            MicrophoneStreamHealth(
                gateStatus: stream.frameCount > 0 && stream.failureReason == .none ? .passed : .failed,
                failureReason: stream.failureReason,
                framesObserved: stream.frameCount > 0,
                timingConfidence: stream.frameCount > 0 ? .usable : .missing,
                silenceStatus: stream.frameCount > 0 ? .audible : .unknown,
                lastLevel: active.lastMicrophoneLevel,
                lastLevelAt: active.lastMicrophoneFrameAt,
                cleanupReadiness: stream.frameCount > 0 ? .readyForFutureProcessing : .unproven,
                evidenceCodes: stream.frameCount > 0 ? ["app_owned_pts_capture"] : ["no_timestamped_mic_frames"]
            )
        }
        let manifest = manifestService.v5Manifest(
            sessionId: active.sessionId,
            directoryId: active.directory.directoryId,
            startedAt: active.startedAt,
            stoppedAt: stoppedAt,
            tracks: tracks,
            failureReason: failureReason != .none ? failureReason : active.terminalFailureReason ?? resolvedFailure,
            scopeApproval: active.scopeApproval,
            permissions: active.permissions,
            microphoneSelection: active.microphoneSelection,
            microphoneStream: microphoneStream,
            microphoneStreamHealth: microphoneHealth,
            privacySegments: active.privacySegments,
            targetMuteCapability: active.targetMuteCapability,
            meetingMuteTruthEvidence: active.meetingMuteTruthEvidence,
            limitationCopyShownAt: active.limitationCopyShownAt
        )
        try manifestService.write(manifest, to: active.directory.manifestURL)
        return manifest
    }

    private func pausePrivacyOnQueue(startedAt: Date) throws {
        guard let active else { throw LocalRecordingWriterError.notRecording }
        guard active.activePrivacySegment == nil else { return }
        active.privacySource?.update(state: .paused)
        active.activePrivacySegment = ProductPrivacySegment(
            segmentId: "\(active.sessionId)-privacy-\(active.privacySegments.count + 1)",
            sessionId: active.sessionId,
            control: .pause,
            startedAt: startedAt,
            startMonotonicMs: monotonicMs(for: startedAt, relativeTo: active.startedAt),
            localMicTreatment: .silenced,
            initiator: .user,
            diagnosticSafe: true
        )
    }

    private func resumePrivacyOnQueue(endedAt: Date) throws {
        guard let active else { throw LocalRecordingWriterError.notRecording }
        active.privacySource?.update(state: .capturing)
        finalizePrivacySegment(for: active, endedAt: endedAt)
    }

    private func drainAvailable(
        for active: V5ActiveRecording,
        maximumBatchesPerSource: Int,
        failWhenLimitIsReached: Bool
    ) {
        guard active.terminalFailureReason == nil else { return }
        for (source, sourceKind) in [
            (active.microphoneSource, RecordingAudioInput.microphone),
            (active.incomingSource, RecordingAudioInput.systemAudio)
        ] {
            guard let source else { continue }
            if source.hasTimestampedOverflow {
                active.recordFailure(.writeFailed)
                return
            }
            var drained = 0
            while drained < max(1, maximumBatchesPerSource),
                  let batch = source.readTimestampedBatch(maximumFrameCount: Self.batchFrameLimit)
            {
                drained += 1
                do {
                    try active.timeline.append(source: sourceKind, batch: batch)
                    active.observe(batch: batch, source: sourceKind)
                } catch {
                    active.recordFailure(Self.failureReason(for: error))
                    return
                }
            }
            guard failWhenLimitIsReached, drained == max(1, maximumBatchesPerSource) else {
                continue
            }
            if source.readTimestampedBatch(maximumFrameCount: Self.batchFrameLimit) != nil {
                active.recordFailure(.writeFailed)
                return
            }
        }
    }

    private func makeTracks(
        for active: V5ActiveRecording,
        artifact: CanonicalRecordingArtifact?,
        failureReason: LocalRecordingFailureReason
    ) throws -> [LocalRecordingTrack] {
        guard let artifact, failureReason == .none else {
            return missingTracks(failureReason: failureReason == .none ? .noFrames : failureReason)
        }
        let mediaBytes = try byteCount(of: artifact.transcriptionAudioURL)
        let playbackBytes = try byteCount(of: artifact.reviewAudioURL)
        let playbackFile = try AVAudioFile(forReading: artifact.reviewAudioURL)
        let playbackDurationMs = Int((Double(playbackFile.length) / playbackFile.fileFormat.sampleRate) * 1_000)
        let aacPresentationFrameDelta = playbackFile.length - artifact.canonicalFrameCount
        let media = LocalRecordingTrack(
            trackId: "mixed-meeting-audio",
            role: .mixedMeetingAudio,
            sourceKind: .canonicalMix,
            mediaScribeField: .mediaFile,
            status: .saved,
            fileName: "meeting-transcription.wav",
            format: "wav-pcm-s16le",
            sampleRate: CanonicalRecordingWriter.transcriptionSampleRate,
            channelCount: 1,
            bitsPerSample: 16,
            durationMs: artifact.transcriptionDurationMs,
            byteCount: mediaBytes,
            sha256: try Self.sha256(of: artifact.transcriptionAudioURL),
            frameCount: artifact.transcriptionFrameCount,
            timelineStartMs: 0,
            timelineAligned: true,
            failureReason: .none
        )
        let playback = LocalRecordingTrack(
            trackId: "review-playback",
            role: .reviewPlayback,
            sourceKind: .canonicalMix,
            mediaScribeField: .playbackFile,
            status: .saved,
            fileName: "meeting-review.m4a",
            format: "m4a-aac-lc",
            sampleRate: playbackFile.fileFormat.sampleRate,
            channelCount: Int(playbackFile.fileFormat.channelCount),
            bitsPerSample: 0,
            durationMs: playbackDurationMs,
            byteCount: playbackBytes,
            sha256: try Self.sha256(of: artifact.reviewAudioURL),
            frameCount: playbackFile.length,
            aacPresentationFrameDelta: aacPresentationFrameDelta,
            timelineStartMs: 0,
            timelineAligned: true,
            failureReason: .none
        )
        return [media, playback]
    }

    private func missingTracks(failureReason: LocalRecordingFailureReason) -> [LocalRecordingTrack] {
        let status: LocalRecordingTrackStatus = switch failureReason {
        case .writeFailed, .finalizationFailed, .captureFailed, .deviceUnavailable, .appClosed:
            .failed
        case .permissionDenied, .scopeUnavailable, .protectedAudioBlocked:
            .blocked
        default:
            .missing
        }
        return [
            LocalRecordingTrack(
                trackId: "mixed-meeting-audio",
                role: .mixedMeetingAudio,
                sourceKind: .canonicalMix,
                mediaScribeField: .mediaFile,
                status: status,
                fileName: "meeting-transcription.wav",
                format: "wav-pcm-s16le",
                sampleRate: CanonicalRecordingWriter.transcriptionSampleRate,
                channelCount: 1,
                bitsPerSample: 16,
                durationMs: 0,
                byteCount: 0,
                frameCount: 0,
                timelineStartMs: 0,
                timelineAligned: false,
                failureReason: failureReason
            ),
            LocalRecordingTrack(
                trackId: "review-playback",
                role: .reviewPlayback,
                sourceKind: .canonicalMix,
                mediaScribeField: .playbackFile,
                status: status,
                fileName: "meeting-review.m4a",
                format: "m4a-aac-lc",
                sampleRate: CanonicalRecordingWriter.canonicalSampleRate,
                channelCount: 1,
                bitsPerSample: 0,
                durationMs: 0,
                byteCount: 0,
                frameCount: 0,
                timelineStartMs: 0,
                timelineAligned: false,
                failureReason: failureReason
            )
        ]
    }

    private func microphoneStream(for active: V5ActiveRecording, stoppedAt: Date) -> AppOwnedMicrophoneStreamSession? {
        guard let microphoneSelection = active.microphoneSelection else { return nil }
        let failure = active.microphoneFrameCount > 0 ? .none : active.terminalFailureReason ?? .noFrames
        return AppOwnedMicrophoneStreamSession(
            sessionId: active.sessionId,
            selection: microphoneSelection,
            permissionState: active.permissions?.microphone ?? .unknown,
            streamKind: .appOwnedSampleSource,
            startedAt: active.startedAt,
            stoppedAt: stoppedAt,
            monotonicStartMs: 0,
            monotonicStopMs: monotonicMs(for: stoppedAt, relativeTo: active.startedAt),
            sampleRate: CanonicalRecordingWriter.canonicalSampleRate,
            channelCount: 1,
            writerSampleRate: CanonicalRecordingWriter.transcriptionSampleRate,
            writerChannelCount: 1,
            frameCount: active.microphoneFrameCount,
            droppedFrameCount: 0,
            silentFrameCount: 0,
            clippedFrameCount: 0,
            routeChangeCount: 0,
            lastFrameAt: active.lastMicrophoneFrameAt,
            failureReason: failure
        )
    }

    private func levelsOnQueue(now: Date) -> LiveRecordingLevels {
        guard let active else { return .inactive }
        return LiveRecordingLevels(
            isRecording: true,
            microphoneLevel: active.lastMicrophoneLevel,
            incomingLevel: active.lastIncomingLevel,
            microphoneUpdatedAt: active.lastMicrophoneFrameAt,
            incomingUpdatedAt: active.lastIncomingFrameAt
        )
    }

    private func finalizePrivacySegment(for active: V5ActiveRecording, endedAt: Date) {
        guard let segment = active.activePrivacySegment else { return }
        active.privacySegments.append(segment.finalized(
            endedAt: endedAt,
            endMonotonicMs: monotonicMs(for: endedAt, relativeTo: active.startedAt),
            treatment: .silenced
        ))
        active.activePrivacySegment = nil
    }

    private static func failureReason(for error: Error) -> LocalRecordingFailureReason {
        switch error {
        case RecordingAudioTimelineError.uncomparablePresentationTimes,
             RecordingAudioTimelineError.sourceClockObservationMissing,
             RecordingAudioTimelineError.sourceClockMappingUnstable,
             RecordingAudioTimelineError.routeGenerationChanged,
             RecordingAudioTimelineError.gapExceedsBound,
             RecordingAudioTimelineError.lateBatch:
            .timelineMisaligned
        case RecordingAudioTimelineError.missingRequiredSource:
            .noFrames
        case RecordingAudioTimelineError.sourceOverflow:
            .writeFailed
        case CanonicalRecordingWriterError.noFrames:
            .noFrames
        case CanonicalRecordingWriterError.finalizationFailed,
             CanonicalRecordingWriterError.conversionFailed:
            .finalizationFailed
        default:
            .captureFailed
        }
    }

    fileprivate static func rmsLevel(_ samples: [Float]) -> Double {
        guard !samples.isEmpty else { return 0 }
        let meanSquare = samples.reduce(0.0) { partial, sample in
            partial + Double(sample * sample)
        } / Double(samples.count)
        return min(1, sqrt(meanSquare))
    }

    private static func sha256(of url: URL) throws -> String {
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        var hasher = SHA256()
        while true {
            let data = try handle.read(upToCount: 64 * 1024) ?? Data()
            guard !data.isEmpty else { break }
            hasher.update(data: data)
        }
        return hasher.finalize().map { String(format: "%02x", $0) }.joined()
    }

    private func byteCount(of url: URL) throws -> Int64 {
        guard let value = try fileAttributes(at: url)[.size] as? NSNumber else {
            throw CanonicalRecordingWriterError.finalizationFailed
        }
        return value.int64Value
    }

    private func fileAttributes(at url: URL) throws -> [FileAttributeKey: Any] {
        try FileManager.default.attributesOfItem(atPath: url.path)
    }

    private func removeFinalArtifacts(in directory: LocalRecordingDirectory) {
        try? FileManager.default.removeItem(at: directory.transcriptionAudioURL)
        try? FileManager.default.removeItem(at: directory.reviewAudioURL)
    }

    private func monotonicMs(for date: Date, relativeTo startedAt: Date) -> Int {
        Int(max(0, date.timeIntervalSince(startedAt) * 1_000))
    }
}

private final class V5ActiveRecording {
    let sessionId: String
    let startedAt: Date
    let directory: LocalRecordingDirectory
    let canonicalWriter: CanonicalRecordingWriter
    let timeline: RecordingAudioTimeline
    let microphoneSource: TimestampedLocalRecordingSampleSource?
    let incomingSource: TimestampedLocalRecordingSampleSource?
    let privacySource: PrivacySuppressingSampleSource?
    let scopeApproval: CaptureScopeApproval?
    let permissions: SystemAudioPermissionSnapshot?
    let microphoneSelection: RecordingMicrophoneSelection?
    let targetMuteCapability: TargetMuteCapability?
    let meetingMuteTruthEvidence: [MeetingMuteTruthEvidence]
    let limitationCopyShownAt: Date?
    let recordMicrophone: Bool
    var timer: DispatchSourceTimer?
    var terminalFailureReason: LocalRecordingFailureReason?
    var lastMicrophoneLevel: Double = 0
    var lastIncomingLevel: Double = 0
    var lastMicrophoneFrameAt: Date?
    var lastIncomingFrameAt: Date?
    var microphoneFrameCount: Int64 = 0
    var privacySegments: [ProductPrivacySegment] = []
    var activePrivacySegment: ProductPrivacySegment?

    init(
        sessionId: String,
        startedAt: Date,
        directory: LocalRecordingDirectory,
        canonicalWriter: CanonicalRecordingWriter,
        timeline: RecordingAudioTimeline,
        microphoneSource: TimestampedLocalRecordingSampleSource?,
        incomingSource: TimestampedLocalRecordingSampleSource?,
        privacySource: PrivacySuppressingSampleSource?,
        scopeApproval: CaptureScopeApproval?,
        permissions: SystemAudioPermissionSnapshot?,
        microphoneSelection: RecordingMicrophoneSelection?,
        targetMuteCapability: TargetMuteCapability?,
        meetingMuteTruthEvidence: [MeetingMuteTruthEvidence],
        limitationCopyShownAt: Date?,
        recordMicrophone: Bool
    ) {
        self.sessionId = sessionId
        self.startedAt = startedAt
        self.directory = directory
        self.canonicalWriter = canonicalWriter
        self.timeline = timeline
        self.microphoneSource = microphoneSource
        self.incomingSource = incomingSource
        self.privacySource = privacySource
        self.scopeApproval = scopeApproval
        self.permissions = permissions
        self.microphoneSelection = microphoneSelection
        self.targetMuteCapability = targetMuteCapability
        self.meetingMuteTruthEvidence = meetingMuteTruthEvidence
        self.limitationCopyShownAt = limitationCopyShownAt
        self.recordMicrophone = recordMicrophone
    }

    func recordFailure(_ reason: LocalRecordingFailureReason) {
        if terminalFailureReason == nil {
            terminalFailureReason = reason
        }
    }

    func observe(batch: RecordingAudioBatch, source: RecordingAudioInput) {
        let frameCount = Int64(batch.samples.count / max(1, batch.format.channelCount))
        let level = LocalRecordingWriter.rmsLevel(batch.samples)
        switch source {
        case .microphone:
            microphoneFrameCount += frameCount
            lastMicrophoneLevel = level
            lastMicrophoneFrameAt = Date()
        case .systemAudio:
            lastIncomingLevel = level
            lastIncomingFrameAt = Date()
        }
    }
}
