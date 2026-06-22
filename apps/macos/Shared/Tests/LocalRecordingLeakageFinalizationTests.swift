import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LocalRecordingLeakageFinalizationTests: XCTestCase {
    func testContaminatedPackageBlocksManifestTranscriptionReadiness() throws {
        let incoming = leakageIntegrationSineSamples(count: 16_000 * 16, amplitude: 0.5)
        let package = try leakageIntegrationPackage(
            mic: incoming.map { $0 * 0.2 },
            incoming: incoming
        )
        defer { try? FileManager.default.removeItem(at: package) }

        let finalization = LeakageFinalizationService(clock: { Date(timeIntervalSince1970: 50) })
            .finalize(
                micURL: package.appendingPathComponent("mic.wav"),
                incomingURL: package.appendingPathComponent("incoming.wav"),
                micTrack: leakageIntegrationTrack(role: .localMic, durationMs: 16_000),
                incomingTrack: leakageIntegrationTrack(role: .remoteSpeaker, durationMs: 16_000)
            )

        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 51) })
            .manifest(
                sessionId: "leakage-contaminated",
                directoryId: package.lastPathComponent,
                startedAt: Date(timeIntervalSince1970: 34),
                stoppedAt: Date(timeIntervalSince1970: 50),
                tracks: [
                    leakageIntegrationTrack(role: .localMic, durationMs: 16_000),
                    leakageIntegrationTrack(role: .remoteSpeaker, durationMs: 16_000)
                ],
                leakageFinalization: finalization,
                scopeApproval: leakageIntegrationAcceptedScope(),
                permissions: leakageIntegrationAcceptedPermissions()
            )

        XCTAssertEqual(finalization.status, .leakageDetected)
        XCTAssertEqual(finalization.transcriptionGate, .blockedLeakageDetected)
        XCTAssertEqual(manifest.status, .failed)
        XCTAssertEqual(manifest.failureReason, .leakageDetected)
        XCTAssertEqual(manifest.transcriptionReadiness, .failed)
        XCTAssertFalse(manifest.isComplete)
        XCTAssertFalse(manifest.externalEgressStarted)
        XCTAssertFalse(manifest.transcriptionStarted)
    }

    func testTimelineMismatchPackageBlocksManifestTranscriptionReadiness() throws {
        let package = try leakageIntegrationPackage(
            mic: leakageIntegrationLowNoiseSamples(count: 16_000 * 16),
            incoming: leakageIntegrationSineSamples(count: 16_000 * 16, amplitude: 0.5)
        )
        defer { try? FileManager.default.removeItem(at: package) }

        let micTrack = leakageIntegrationTrack(role: .localMic, durationMs: 16_000)
        let incomingTrack = leakageIntegrationTrack(role: .remoteSpeaker, durationMs: 12_000)
        let finalization = LeakageFinalizationService(clock: { Date(timeIntervalSince1970: 70) })
            .finalize(
                micURL: package.appendingPathComponent("mic.wav"),
                incomingURL: package.appendingPathComponent("incoming.wav"),
                micTrack: micTrack,
                incomingTrack: incomingTrack
            )

        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 71) })
            .manifest(
                sessionId: "leakage-timeline-mismatch",
                directoryId: package.lastPathComponent,
                startedAt: Date(timeIntervalSince1970: 54),
                stoppedAt: Date(timeIntervalSince1970: 70),
                tracks: [micTrack, incomingTrack],
                leakageFinalization: finalization,
                scopeApproval: leakageIntegrationAcceptedScope(),
                permissions: leakageIntegrationAcceptedPermissions()
            )

        XCTAssertEqual(finalization.status, .unproven)
        XCTAssertEqual(finalization.alignmentStatus, .misaligned)
        XCTAssertEqual(finalization.transcriptionGate, .blockedTimelineMisaligned)
        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertEqual(manifest.failureReason, .timelineMisaligned)
        XCTAssertEqual(manifest.transcriptionReadiness, .degraded)
        XCTAssertFalse(manifest.isComplete)
    }

    func testAppOwnedMicrophoneStreamHealthDoesNotOverrideLeakageTruth() throws {
        let incoming = leakageIntegrationSineSamples(count: 16_000 * 16, amplitude: 0.5)
        let package = try leakageIntegrationPackage(
            mic: incoming.map { $0 * 0.2 },
            incoming: incoming
        )
        defer { try? FileManager.default.removeItem(at: package) }

        let micTrack = leakageIntegrationTrack(role: .localMic, durationMs: 16_000)
        let incomingTrack = leakageIntegrationTrack(role: .remoteSpeaker, durationMs: 16_000)
        let finalization = LeakageFinalizationService(clock: { Date(timeIntervalSince1970: 90) })
            .finalize(
                micURL: package.appendingPathComponent("mic.wav"),
                incomingURL: package.appendingPathComponent("incoming.wav"),
                micTrack: micTrack,
                incomingTrack: incomingTrack
            )
        let selection = leakageIntegrationRecordingMicrophoneSelection()
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 91) })
            .manifest(
                sessionId: "leakage-app-owned-mic",
                directoryId: package.lastPathComponent,
                startedAt: Date(timeIntervalSince1970: 74),
                stoppedAt: Date(timeIntervalSince1970: 90),
                tracks: [micTrack, incomingTrack],
                leakageFinalization: finalization,
                scopeApproval: leakageIntegrationAcceptedScope(),
                permissions: leakageIntegrationAcceptedPermissions(),
                microphoneSelection: selection,
                microphoneStream: AppOwnedMicrophoneStreamSession(
                    sessionId: "leakage-app-owned-mic",
                    selection: selection,
                    permissionState: .granted,
                    streamKind: .appOwnedSampleSource,
                    stoppedAt: Date(timeIntervalSince1970: 90),
                    sampleRate: 48_000,
                    channelCount: 1,
                    writerSampleRate: 16_000,
                    writerChannelCount: 1,
                    frameCount: 256_000,
                    failureReason: .none
                ),
                microphoneStreamHealth: MicrophoneStreamHealth(
                    gateStatus: .passed,
                    failureReason: .none,
                    framesObserved: true,
                    timingConfidence: .usable,
                    silenceStatus: .audible,
                    cleanupReadiness: .readyForFutureProcessing,
                    evidenceCodes: ["mic_graph_ready", "incoming_reference_present"]
                )
            )

        XCTAssertEqual(finalization.status, .leakageDetected)
        XCTAssertEqual(manifest.status, .failed)
        XCTAssertEqual(manifest.failureReason, .leakageDetected)
        XCTAssertEqual(manifest.transcriptionReadiness, .failed)
        XCTAssertEqual(manifest.microphoneStreamHealth?.cleanupReadiness, .readyForFutureProcessing)
        XCTAssertFalse(manifest.isComplete)
    }

    func testAppleCandidateMetadataDoesNotOverrideLeakageTruth() throws {
        let incoming = leakageIntegrationSineSamples(count: 16_000 * 16, amplitude: 0.5)
        let package = try leakageIntegrationPackage(
            mic: incoming.map { $0 * 0.2 },
            incoming: incoming
        )
        defer { try? FileManager.default.removeItem(at: package) }

        let micTrack = leakageIntegrationTrack(role: .localMic, durationMs: 16_000)
        let incomingTrack = leakageIntegrationTrack(role: .remoteSpeaker, durationMs: 16_000)
        let finalization = LeakageFinalizationService(clock: { Date(timeIntervalSince1970: 110) })
            .finalize(
                micURL: package.appendingPathComponent("mic.wav"),
                incomingURL: package.appendingPathComponent("incoming.wav"),
                micTrack: micTrack,
                incomingTrack: incomingTrack
            )
        let appleOutcome = AppleProcessingOutcome(
            candidateId: "apple-candidate-001",
            primaryOutcome: .acceptedForGuidanceOnly,
            validationRows: [
                AppleProcessingValidationRow(
                    candidateId: "apple-candidate-001",
                    candidateKind: .micModeGuidance,
                    routeClass: .builtInSpeakerphone,
                    scenario: .farEndOnly,
                    baselineStatus: .degraded,
                    candidateStatus: .accepted,
                    lineageStatus: .candidateMetadata,
                    speechPreservationStatus: .preserved,
                    alignmentStatus: .accepted,
                    stabilityStatus: .accepted,
                    diagnosticSafe: true
                )
            ],
            nextStepRecommendation: .deferToWebRTCAEC3
        )
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 111) })
            .manifest(
                sessionId: "leakage-apple-candidate",
                directoryId: package.lastPathComponent,
                startedAt: Date(timeIntervalSince1970: 94),
                stoppedAt: Date(timeIntervalSince1970: 110),
                tracks: [micTrack, incomingTrack],
                leakageFinalization: finalization,
                scopeApproval: leakageIntegrationAcceptedScope(),
                permissions: leakageIntegrationAcceptedPermissions(),
                appleProcessingOutcome: appleOutcome
            )

        XCTAssertEqual(manifest.appleProcessingOutcome, appleOutcome)
        XCTAssertEqual(finalization.status, .leakageDetected)
        XCTAssertEqual(manifest.status, .failed)
        XCTAssertEqual(manifest.failureReason, .leakageDetected)
        XCTAssertEqual(manifest.leakageFinalization?.transcriptionGate, .blockedLeakageDetected)
        XCTAssertFalse(manifest.isComplete)
    }
}

private func leakageIntegrationPackage(mic: [Float], incoming: [Float]) throws -> URL {
    let directory = FileManager.default.temporaryDirectory
        .appendingPathComponent("leakage-integration-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    try leakageIntegrationWriteWAV(samples: mic, to: directory.appendingPathComponent("mic.wav"))
    try leakageIntegrationWriteWAV(samples: incoming, to: directory.appendingPathComponent("incoming.wav"))
    return directory
}

private func leakageIntegrationWriteWAV(samples: [Float], to url: URL) throws {
    var data = Data()
    let dataByteCount = UInt32(samples.count * MemoryLayout<Int16>.stride)
    data.leakageIntegrationAppendLE(UInt32(0x4646_4952))
    data.leakageIntegrationAppendLE(UInt32(36) + dataByteCount)
    data.leakageIntegrationAppendLE(UInt32(0x4556_4157))
    data.leakageIntegrationAppendLE(UInt32(0x2074_6d66))
    data.leakageIntegrationAppendLE(UInt32(16))
    data.leakageIntegrationAppendLE(UInt16(1))
    data.leakageIntegrationAppendLE(UInt16(1))
    data.leakageIntegrationAppendLE(UInt32(16_000))
    data.leakageIntegrationAppendLE(UInt32(16_000 * MemoryLayout<Int16>.stride))
    data.leakageIntegrationAppendLE(UInt16(MemoryLayout<Int16>.stride))
    data.leakageIntegrationAppendLE(UInt16(16))
    data.leakageIntegrationAppendLE(UInt32(0x6174_6164))
    data.leakageIntegrationAppendLE(dataByteCount)
    for sample in samples {
        var intSample = Int16(max(-1, min(1, sample)) * Float(Int16.max)).littleEndian
        data.append(Data(bytes: &intSample, count: MemoryLayout<Int16>.size))
    }
    try data.write(to: url)
}

private func leakageIntegrationTrack(role: AudioTrackRole, durationMs: Int) -> LocalRecordingTrack {
    LocalRecordingTrack(
        trackId: role.rawValue,
        role: role,
        status: .saved,
        fileName: role == .localMic ? "mic.wav" : "incoming.wav",
        format: "wav-pcm-s16le",
        sampleRate: 16_000,
        channelCount: 1,
        bitsPerSample: 16,
        durationMs: durationMs,
        byteCount: Int64(44 + durationMs * 32),
        frameCount: Int64(durationMs * 16),
        timelineStartMs: 0,
        timelineAligned: true
    )
}

private func leakageIntegrationAcceptedScope() -> CaptureScopeApproval {
    CaptureScopeApproval(
        scopeApprovalId: "scope-leakage-integration",
        scopeKind: .display,
        sourceDisplayName: "Current Display",
        approvedAt: Date(timeIntervalSince1970: 33),
        approvalMode: .userConfirmedSuggestedScope,
        eligibleReason: .manualMeetingScope
    )
}

private func leakageIntegrationAcceptedPermissions() -> SystemAudioPermissionSnapshot {
    SystemAudioPermissionSnapshot(
        microphone: .granted,
        systemAudio: .granted,
        evaluatedAt: Date(timeIntervalSince1970: 33)
    )
}

private func leakageIntegrationRecordingMicrophoneSelection() -> RecordingMicrophoneSelection {
    RecordingMicrophoneSelection(
        selectionId: "selection-leakage",
        mode: .userSelected,
        inputDeviceId: "built-in-mic",
        inputDisplayName: "Built-in Microphone",
        deviceClass: .builtIn,
        workingDeviceKind: .physical,
        selectionResult: .accepted,
        resolvedAt: Date(timeIntervalSince1970: 73)
    )
}

private func leakageIntegrationSineSamples(count: Int, amplitude: Float) -> [Float] {
    (0..<count).map { index in
        sin(Float(index) * 2 * .pi * 440 / 16_000) * amplitude
    }
}

private func leakageIntegrationLowNoiseSamples(count: Int) -> [Float] {
    (0..<count).map { index in
        let value = ((index * 1103515245 + 12345) & 0x7fffffff) % 997
        return (Float(value) / 997.0 - 0.5) * 0.0005
    }
}

private extension Data {
    mutating func leakageIntegrationAppendLE(_ value: UInt16) {
        var little = value.littleEndian
        append(Data(bytes: &little, count: MemoryLayout<UInt16>.size))
    }

    mutating func leakageIntegrationAppendLE(_ value: UInt32) {
        var little = value.littleEndian
        append(Data(bytes: &little, count: MemoryLayout<UInt32>.size))
    }
}
#endif
