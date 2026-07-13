import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

@main
struct MeetingMuteTruthRuntimeProof {
    static func main() async throws {
        let configuration = try RuntimeProofConfiguration(arguments: CommandLine.arguments)
        let store = LocalRecordingStore(rootURL: configuration.outputRootURL)
        let micSource = BufferedLocalRecordingSampleSource(capacity: 48_000 * 8, channelCount: 1)
        let incomingSource = BufferedLocalRecordingSampleSource(capacity: 48_000 * 8, channelCount: 1)
        let writer = LocalRecordingWriter(
            store: store,
            microphoneSampleSourceFactory: { micSource },
            incomingSampleSourceFactory: { incomingSource },
            microphoneInputChannelCount: 1,
            incomingInputChannelCount: 1,
            recordMicrophone: true
        )

        let startedAt = Date()
        let sessionId = "meeting-mute-truth-runtime-proof-\(UUID().uuidString)"
        let capability = TargetMuteCapability.chromeTelemost
        let evidence = MeetingMuteTruthService().evidence(
            sessionId: sessionId,
            capability: capability,
            limitationCopyShown: true,
            recordedAt: startedAt
        )
        let scopeApproval = CaptureScopeApproval(
            scopeApprovalId: "\(sessionId)-scope",
            scopeKind: .display,
            sourceDisplayName: "Runtime proof synthetic meeting scope",
            approvedAt: startedAt,
            approvalMode: .userConfirmedSuggestedScope,
            eligibleReason: .manualMeetingScope
        )
        let permissions = SystemAudioPermissionSnapshot(
            microphone: .granted,
            systemAudio: .granted,
            evaluatedAt: startedAt
        )

        let directory = try await writer.startAsync(
            sessionId: sessionId,
            startedAt: startedAt,
            scopeApproval: scopeApproval,
            permissions: permissions,
            targetMuteCapability: capability,
            meetingMuteTruthEvidence: [evidence],
            limitationCopyShownAt: startedAt
        )

        appendSyntheticFrames(to: micSource, amplitude: 0.08, at: startedAt)
        appendSyntheticFrames(to: incomingSource, amplitude: 0.12, at: startedAt)
        try await Task.sleep(nanoseconds: 120_000_000)

        let pausedAt = startedAt.addingTimeInterval(1)
        try await writer.pausePrivacyAsync(startedAt: pausedAt)
        appendSyntheticFrames(to: micSource, amplitude: 0.65, at: pausedAt)
        appendSyntheticFrames(to: incomingSource, amplitude: 0.18, at: pausedAt)
        try await Task.sleep(nanoseconds: 120_000_000)

        let resumedAt = startedAt.addingTimeInterval(2)
        try await writer.resumePrivacyAsync(endedAt: resumedAt)
        appendSyntheticFrames(to: micSource, amplitude: 0.1, at: resumedAt)
        appendSyntheticFrames(to: incomingSource, amplitude: 0.2, at: resumedAt)
        try await Task.sleep(nanoseconds: 120_000_000)

        let stoppedAt = startedAt.addingTimeInterval(3)
        let manifest = try await writer.stopAsync(stoppedAt: stoppedAt)
        try validate(manifest: manifest, directory: directory)

        print("meeting-mute-truth runtime proof: OK")
        print("directory=\(directory.directoryURL.path)")
        print("manifest=\(directory.manifestURL.path)")
        print("decision=\(manifest.meetingMuteTruth?.decision.rawValue ?? "missing")")
        print("privacySegments=\(manifest.privacySegments?.count ?? 0)")
    }

    private static func appendSyntheticFrames(
        to source: BufferedLocalRecordingSampleSource,
        amplitude: Float,
        at date: Date
    ) {
        let frameCount = 48_000
        let samples = (0..<frameCount).map { index -> Float in
            let phase = Float(index % 96) / 96
            return sin(phase * 2 * .pi) * amplitude
        }
        source.append(samples, at: date)
    }

    private static func validate(
        manifest: LocalRecordingManifest,
        directory: LocalRecordingDirectory
    ) throws {
        guard FileManager.default.fileExists(atPath: directory.manifestURL.path) else {
            throw RuntimeProofError.validation("manifest was not written")
        }
        guard manifest.meetingMuteTruth?.decision == .meetingMuteUnproven else {
            throw RuntimeProofError.validation("unexpected mute-truth decision")
        }
        guard manifest.targetMuteCapability?.firstMatrixStatus == .pauseValidated else {
            throw RuntimeProofError.validation("missing pause-validated target capability")
        }
        guard manifest.meetingMuteTruthEvidence?.first?.source == .productPause else {
            throw RuntimeProofError.validation("missing product-pause evidence")
        }
        guard let segment = manifest.privacySegments?.first,
              segment.localMicTreatment == .silenced,
              segment.durationMs == 1_000 else {
            throw RuntimeProofError.validation("missing one-second silenced privacy segment")
        }
        guard manifest.meetingMuteTruth?.safeForDiagnostics == true else {
            throw RuntimeProofError.validation("mute-truth decision is not diagnostics-safe")
        }
    }
}

private struct RuntimeProofConfiguration {
    let outputRootURL: URL?

    init(arguments: [String]) throws {
        var outputRootURL: URL?
        var index = 1
        while index < arguments.count {
            let argument = arguments[index]
            switch argument {
            case "--default-store":
                outputRootURL = nil
            case "--output-root":
                index += 1
                guard index < arguments.count else {
                    throw RuntimeProofError.usage("missing path after --output-root")
                }
                outputRootURL = URL(fileURLWithPath: arguments[index], isDirectory: true)
            case "--help", "-h":
                throw RuntimeProofError.usage(Self.usage)
            default:
                throw RuntimeProofError.usage("unknown argument: \(argument)\n\(Self.usage)")
            }
            index += 1
        }
        self.outputRootURL = outputRootURL
    }

    private static let usage = """
    Usage:
      swift run --package-path apps/macos MeetingMuteTruthRuntimeProof --default-store
      swift run --package-path apps/macos MeetingMuteTruthRuntimeProof --output-root /tmp/recordings
    """
}

private enum RuntimeProofError: Error, CustomStringConvertible {
    case usage(String)
    case validation(String)

    var description: String {
        switch self {
        case let .usage(message):
            message
        case let .validation(message):
            "runtime proof validation failed: \(message)"
        }
    }
}
