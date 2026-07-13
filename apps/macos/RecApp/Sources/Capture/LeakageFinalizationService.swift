import Foundation
import TwoBrainRecShared

public struct LeakageFinalizationService: Sendable {
    public typealias Clock = @Sendable () -> Date

    private let wavReader: LeakageWAVReader
    private let measurementService: LeakageMeasurementService
    private let clock: Clock

    public init(
        wavReader: LeakageWAVReader = LeakageWAVReader(),
        measurementService: LeakageMeasurementService = LeakageMeasurementService(),
        clock: @escaping Clock = Date.init
    ) {
        self.wavReader = wavReader
        self.measurementService = measurementService
        self.clock = clock
    }

    public func finalize(
        micURL: URL,
        incomingURL: URL,
        micTrack: LocalRecordingTrack,
        incomingTrack: LocalRecordingTrack,
        routeMetadata: RecordingRouteMetadata = RecordingRouteMetadata(),
        threshold: LeakageThresholdVersion = .v1
    ) -> LeakageFinalization {
        let evaluatedAt = clock()
        guard micTrack.isComplete, incomingTrack.isComplete else {
            return LeakageFinalization(
                status: .notMeasured,
                evaluatedAt: evaluatedAt,
                measurementAttempted: false,
                measurementApplicable: false,
                alignmentStatus: .insufficientReference,
                confidence: 0,
                failureReason: .leakageNotMeasured,
                originalEvidenceStatus: .notMeasured,
                transcriptionGate: .blockedNotMeasured,
                routeMetadata: routeMetadata
            )
        }

        let durationDelta = abs(micTrack.durationMs - incomingTrack.durationMs)
        guard micTrack.timelineAligned,
              incomingTrack.timelineAligned,
              durationDelta <= threshold.timelineToleranceMs
        else {
            return LeakageFinalization(
                status: .unproven,
                evaluatedAt: evaluatedAt,
                measurementAttempted: true,
                measurementApplicable: true,
                alignmentStatus: .misaligned,
                confidence: 0,
                failureReason: .timelineMisaligned,
                originalEvidenceStatus: .unproven,
                transcriptionGate: .blockedTimelineMisaligned,
                routeMetadata: routeMetadata
            )
        }

        do {
            let micInfo = try wavReader.readInfo(url: micURL)
            let incomingInfo = try wavReader.readInfo(url: incomingURL)
            let alignmentStatus: LeakageAlignmentStatus = if abs(micInfo.durationMs - incomingInfo.durationMs) <= threshold.timelineToleranceMs {
                .aligned
            } else {
                .misaligned
            }
            let micSamples = try wavReader.readMonoSamples(url: micURL)
            let incomingSamples = try wavReader.readMonoSamples(url: incomingURL)
            let measurement = measurementService.measure(
                micSamples: micSamples,
                incomingSamples: incomingSamples,
                sampleRate: min(micInfo.sampleRate, incomingInfo.sampleRate),
                threshold: threshold,
                measuredAt: evaluatedAt
            )
            let decision = measurementService.finalizationStatus(
                measurement: measurement,
                alignmentStatus: alignmentStatus,
                measurementAttempted: true,
                measurementApplicable: true,
                threshold: threshold
            )
            return LeakageFinalization(
                status: decision.0,
                evaluatedAt: evaluatedAt,
                measurementAttempted: true,
                measurementApplicable: true,
                alignmentStatus: alignmentStatus,
                confidence: measurement.confidence ?? 0,
                failureReason: decision.2,
                originalEvidenceStatus: decision.0,
                transcriptionGate: decision.1,
                routeMetadata: routeMetadata,
                measurement: measurement
            )
        } catch {
            return LeakageFinalization(
                status: .notMeasured,
                evaluatedAt: evaluatedAt,
                measurementAttempted: false,
                measurementApplicable: false,
                alignmentStatus: .unknown,
                confidence: 0,
                failureReason: .leakageNotMeasured,
                originalEvidenceStatus: .notMeasured,
                transcriptionGate: .blockedNotMeasured,
                routeMetadata: routeMetadata
            )
        }
    }

    public static var cleanRoomDecisionRecords: [LeakageDependencyDecisionRecord] {
        [
            LeakageDependencyDecisionRecord(
                option: "apple_voice_processing",
                outcome: "spike_only",
                reason: "Public APIs are plausible but not proven to feed the app-owned microphone track and persisted mic.wav with stable aligned reference.",
                sourceBasis: "Apple public AVAudioEngine and VoiceProcessingIO documentation",
                testCoverageRequired: ["controlled_leakage", "double_talk", "route_change", "alignment"]
            ),
            LeakageDependencyDecisionRecord(
                option: "webrtc_aec3",
                outcome: "deferred",
                reason: "Live cleanup is out of scope for 020 and needs separate CPU, latency, licensing, packaging, and realtime-safety gates.",
                sourceBasis: "Public WebRTC project documentation",
                testCoverageRequired: ["cpu_latency", "delay_estimation", "route_change", "licensing"]
            ),
            LeakageDependencyDecisionRecord(
                option: "mixed_audio_fallback",
                outcome: "decision_record_only",
                reason: "Mixed audio can be considered only after clean dual-track gates fail in a later architecture slice.",
                sourceBasis: "020 speakerphone go/no-go decision",
                testCoverageRequired: ["diarization_truth", "upload_eligibility", "user_facing_truth"]
            )
        ]
    }
}
