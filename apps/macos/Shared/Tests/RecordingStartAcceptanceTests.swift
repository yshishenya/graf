import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared
import XCTest

final class RecordingStartAcceptanceTests: XCTestCase {
    @MainActor
    func testStopThenReactivationDuringAsyncStartStillDeniesAcceptanceAfterFailedStop() async throws {
        let decision = AcceptanceDecision()
        let bundleID = "test.synthetic.meeting"
        let fixture = try AcceptanceFixture(failAt: 2, onFirstCommit: {
            let applied = DispatchSemaphore(value: 0)
            Task { @MainActor in
                decision.current = false
                decision.pendingStopBundleID = bundleID
                decision.current = true
                applied.signal()
            }
            XCTAssertEqual(applied.wait(timeout: .now() + 2), .success)
        })
        defer { fixture.remove() }
        let directory = try await fixture.writer.startAsync(
            sessionId: "synthetic-start", startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: acceptanceScope(), permissions: acceptancePermissions(),
            requiresStartAcceptance: true)
        XCTAssertTrue(decision.current)
        let allowed = MeetingDetectionAppModule.allowsPendingStart(
            decisionIsCurrent: decision.current, bundleID: bundleID,
            pendingStopBundleID: decision.pendingStopBundleID)
        XCTAssertFalse(allowed)
        if allowed { try fixture.writer.acceptStart(sessionId: "synthetic-start") }
        fixture.appendAudio()
        do {
            _ = try await fixture.writer.stopAsync(failureReason: .permissionDenied)
            XCTFail("Expected injected final manifest failure")
        } catch { }
        let checkpoint = try fixture.service.read(from: directory.manifestURL)
        XCTAssertEqual(checkpoint.startAcceptance, .pending)
        XCTAssertNil(checkpoint.scopeApproval)
        let recovered = try XCTUnwrap(CaptureRecoveryService().recoverIncompleteRecordings(in: fixture.root).first)
        XCTAssertEqual(recovered.manifest.startAcceptance, .pending)
        XCTAssertEqual(recovered.manifest.status, .blocked)
        XCTAssertNil(recovered.manifest.scopeApproval)
    }

    func testPendingStartDecisionRejectsStaleDecisionWithoutConfusingOtherTargets() {
        XCTAssertFalse(MeetingDetectionAppModule.allowsPendingStart(
            decisionIsCurrent: false, bundleID: "one", pendingStopBundleID: nil))
        XCTAssertTrue(MeetingDetectionAppModule.allowsPendingStart(
            decisionIsCurrent: true, bundleID: "one", pendingStopBundleID: nil))
        XCTAssertTrue(MeetingDetectionAppModule.allowsPendingStart(
            decisionIsCurrent: true, bundleID: "one", pendingStopBundleID: "two"))
    }

    @MainActor
    func testDecisionRevokedDuringAsyncStartCannotBeRecoveredAfterFailedStop() async throws {
        let decision = AcceptanceDecision()
        let fixture = try AcceptanceFixture(failAt: 2, onFirstCommit: {
            let applied = DispatchSemaphore(value: 0)
            Task { @MainActor in
                decision.current = false
                applied.signal()
            }
            XCTAssertEqual(applied.wait(timeout: .now() + 2), .success)
        })
        defer { fixture.remove() }
        let directory = try await fixture.writer.startAsync(
            sessionId: "synthetic-start", startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: acceptanceScope(), permissions: acceptancePermissions(),
            requiresStartAcceptance: true)
        XCTAssertFalse(decision.current)
        // The application takes this same stale-decision branch after await;
        // no acceptance operation is called for the revoked generation.
        fixture.appendAudio()
        do {
            _ = try await fixture.writer.stopAsync(failureReason: .permissionDenied)
            XCTFail("Expected injected final manifest failure")
        } catch { }
        XCTAssertEqual(try fixture.service.read(from: directory.manifestURL).startAcceptance, .pending)
        let recovered = try XCTUnwrap(CaptureRecoveryService().recoverIncompleteRecordings(in: fixture.root).first)
        XCTAssertEqual(recovered.manifest.status, .blocked)
        XCTAssertNil(recovered.manifest.scopeApproval)
    }

    func testActualRenameFailurePreservesPreviousManifest() throws {
        let fixture = try AcceptanceFixture()
        defer { fixture.remove() }
        let directory = try fixture.start()
        let oldBytes = try Data(contentsOf: directory.manifestURL)
        var accepted = try fixture.service.read(from: directory.manifestURL)
        accepted.startAcceptance = .accepted
        accepted.scopeApproval = acceptanceScope()
        let parent = directory.directoryURL
        defer { try? FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: parent.path) }
        let service = LocalRecordingManifestService(beforeCommit: { _, _ in
            try FileManager.default.setAttributes([.posixPermissions: 0o500], ofItemAtPath: parent.path)
        })
        XCTAssertThrowsError(try service.write(accepted, to: directory.manifestURL))
        XCTAssertEqual(try Data(contentsOf: directory.manifestURL), oldBytes)
        XCTAssertEqual(try fixture.service.read(from: directory.manifestURL).startAcceptance, .pending)
    }

    func testInitialCommitFailureDoesNotActivateWriter() throws {
        let fixture = try AcceptanceFixture(failAt: 1)
        defer { fixture.remove() }
        XCTAssertThrowsError(try fixture.start())
        XCTAssertFalse(fixture.writer.isRecording)
        XCTAssertNil(fixture.writer.currentDirectoryURL())
    }

    func testPendingSurvivesFailedFinalizationAndRepeatedRecoveryWriteFailure() throws {
        let fixture = try AcceptanceFixture(failAt: 2, failFollowing: true)
        defer { fixture.remove() }
        let directory = try fixture.start()
        let initial = try fixture.service.read(from: directory.manifestURL)
        XCTAssertEqual(initial.startAcceptance, .pending)
        XCTAssertNil(initial.scopeApproval)
        fixture.appendAudio()
        XCTAssertThrowsError(try fixture.writer.stop(failureReason: .permissionDenied))
        XCTAssertFalse(fixture.writer.isRecording)
        XCTAssertEqual(try fixture.service.read(from: directory.manifestURL).status, .active)
        for _ in 0..<2 {
            let recovered = try XCTUnwrap(CaptureRecoveryService().recoverIncompleteRecordings(
                in: fixture.root, manifestService: fixture.service).first)
            XCTAssertEqual(recovered.manifest.startAcceptance, .pending)
            XCTAssertEqual(recovered.manifest.status, .blocked)
            XCTAssertNil(recovered.manifest.scopeApproval)
            XCTAssertEqual(try fixture.service.read(from: directory.manifestURL).startAcceptance, .pending)
        }
        let recovered = try XCTUnwrap(CaptureRecoveryService().recoverIncompleteRecordings(in: fixture.root).first)
        XCTAssertEqual(recovered.manifest.startAcceptance, .pending)
        XCTAssertEqual(recovered.manifest.status, .blocked)
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.directoryURL.path))
    }

    func testFailedAcceptanceCannotLeakApprovalIntoFinalManifest() throws {
        let fixture = try AcceptanceFixture(failAt: 2)
        defer { fixture.remove() }
        let directory = try fixture.start()
        XCTAssertThrowsError(try fixture.writer.acceptStart(sessionId: "synthetic-start"))
        XCTAssertEqual(try fixture.service.read(from: directory.manifestURL).startAcceptance, .pending)
        fixture.appendAudio()
        let final = try fixture.writer.stop()
        XCTAssertEqual(final.startAcceptance, .pending)
        XCTAssertNil(final.scopeApproval)
        XCTAssertFalse(final.isComplete)
    }

    func testWrongSessionAndStoppedSessionCannotBeAccepted() throws {
        let fixture = try AcceptanceFixture()
        defer { fixture.remove() }
        let directory = try fixture.start()
        XCTAssertThrowsError(try fixture.writer.acceptStart(sessionId: "other-session"))
        XCTAssertEqual(try fixture.service.read(from: directory.manifestURL).startAcceptance, .pending)
        _ = try fixture.writer.stop()
        XCTAssertThrowsError(try fixture.writer.acceptStart(sessionId: "synthetic-start"))
        XCTAssertEqual(try fixture.service.read(from: directory.manifestURL).startAcceptance, .pending)
    }

    func testAcceptedStartPersistsAndRecoveryPreservesIt() throws {
        let fixture = try AcceptanceFixture()
        defer { fixture.remove() }
        let directory = try fixture.start()
        let start = ContinuousClock.now
        try fixture.writer.acceptStart(sessionId: "synthetic-start")
        let elapsed = start.duration(to: .now)
        print("start_acceptance_commit_duration=\(elapsed)")
        XCTAssertLessThan(elapsed, .milliseconds(100))
        let accepted = try fixture.service.read(from: directory.manifestURL)
        XCTAssertEqual(accepted.startAcceptance, .accepted)
        XCTAssertNotNil(accepted.scopeApproval)
        fixture.appendAudio()
        let final = try fixture.writer.stop()
        XCTAssertEqual(final.startAcceptance, .accepted)
        XCTAssertTrue(final.isComplete)
        // A process may exit with the last committed active checkpoint while
        // valid audio files already exist. Recover using a fresh service.
        try fixture.service.write(accepted, to: directory.manifestURL)
        let recovered = try XCTUnwrap(CaptureRecoveryService().recoverIncompleteRecordings(in: fixture.root).first)
        XCTAssertEqual(recovered.manifest.startAcceptance, .accepted)
        XCTAssertTrue(recovered.manifest.isComplete)
    }

    func testManualStartAndHistoricalMissingFieldKeepExistingSemantics() throws {
        let fixture = try AcceptanceFixture()
        defer { fixture.remove() }
        let directory = try fixture.start(requiresAcceptance: false)
        fixture.appendAudio()
        let final = try fixture.writer.stop()
        XCTAssertEqual(final.startAcceptance, .accepted)
        XCTAssertTrue(final.isComplete)
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: directory.manifestURL)) as? [String: Any])
        json.removeValue(forKey: "startAcceptance")
        try JSONSerialization.data(withJSONObject: json).write(to: directory.manifestURL)
        let legacy = try fixture.service.read(from: directory.manifestURL)
        XCTAssertNil(legacy.startAcceptance)
        XCTAssertTrue(legacy.isComplete)
        json["startAcceptance"] = "unknown-future-value"
        try JSONSerialization.data(withJSONObject: json).write(to: directory.manifestURL)
        XCTAssertThrowsError(try fixture.service.read(from: directory.manifestURL))
    }

    func testOldReaderWithoutNewFieldStillCannotApprovePendingStart() throws {
        let fixture = try AcceptanceFixture()
        defer { fixture.remove() }
        let directory = try fixture.start()
        fixture.appendAudio()
        _ = try fixture.writer.stop()
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: directory.manifestURL)) as? [String: Any])
        json.removeValue(forKey: "startAcceptance")
        try JSONSerialization.data(withJSONObject: json).write(to: directory.manifestURL)
        let oldView = try fixture.service.read(from: directory.manifestURL)
        XCTAssertNil(oldView.scopeApproval)
        XCTAssertFalse(oldView.isComplete)
    }

    func testPendingRecoveryNeverRepairsOrRemovesAudio() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("start-acceptance-\(UUID())")
        defer { try? FileManager.default.removeItem(at: root) }
        let directory = try LocalRecordingStore(rootURL: root).createDirectory(sessionId: "pending-start")
        let service = LocalRecordingManifestService()
        let manifest = service.activeV5Manifest(
            sessionId: "pending-start", directoryId: directory.directoryId,
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: acceptanceScope(), permissions: acceptancePermissions()
        )
        try service.write(manifest, to: directory.manifestURL)
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: directory.manifestURL)) as? [String: Any])
        json["startAcceptance"] = "pending"
        try JSONSerialization.data(withJSONObject: json).write(to: directory.manifestURL, options: .atomic)
        let partial = directory.directoryURL.appendingPathComponent("meeting-transcription.partial.wav")
        var audio = CanonicalRecordingWriter.pcm16MonoWAVHeader(dataByteCount: 0)
        audio.append(Data(repeating: 1, count: 32_000))
        try audio.write(to: partial)

        let recovered = try XCTUnwrap(CaptureRecoveryService().recoverIncompleteRecordings(in: root).first)

        XCTAssertEqual(recovered.manifest.status, .blocked)
        XCTAssertEqual(recovered.manifest.failureReason, .permissionDenied)
        XCTAssertNil(recovered.manifest.scopeApproval)
        XCTAssertFalse(recovered.manifest.isComplete)
        XCTAssertTrue(FileManager.default.fileExists(atPath: partial.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.transcriptionAudioURL.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.reviewAudioURL.path))
        XCTAssertTrue(CaptureRecoveryService().recoverIncompleteRecordings(in: root).isEmpty)
    }
}

private final class AcceptanceFixture {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("acceptance-writer-\(UUID())")
    let microphone = BufferedLocalRecordingSampleSource(channelCount: 1)
    let system = BufferedLocalRecordingSampleSource(channelCount: 1)
    let service: LocalRecordingManifestService
    let writer: LocalRecordingWriter

    init(failAt: Int? = nil, failFollowing: Bool = false,
         onFirstCommit: (@Sendable () -> Void)? = nil) throws {
        let failures = AcceptanceCommitFailures(failAt: failAt, failFollowing: failFollowing,
            onFirstCommit: onFirstCommit)
        service = LocalRecordingManifestService(beforeCommit: { manifest, temporaryURL in
            XCTAssertTrue(LocalCustodyFileProtection.isProtected(temporaryURL))
            try failures.check()
        })
        writer = LocalRecordingWriter(store: LocalRecordingStore(rootURL: root), manifestService: service,
            microphoneSampleSourceFactory: { [microphone] in microphone },
            incomingSampleSourceFactory: { [system] in system })
    }

    func start(requiresAcceptance: Bool = true) throws -> LocalRecordingDirectory {
        try writer.start(sessionId: "synthetic-start", startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: acceptanceScope(), permissions: acceptancePermissions(),
            requiresStartAcceptance: requiresAcceptance)
    }

    func appendAudio() {
        for (source, level) in [(microphone, Float(0.4)), (system, Float(0.2))] {
            source.append(RecordingAudioBatch(samples: Array(repeating: level, count: 4_800),
                format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
                presentationTime: RecordingAudioPresentationTimestamp(seconds: 100, clockDomain: .hostTime),
                discontinuity: .none, routeGeneration: 0))
        }
    }

    func remove() {
        if writer.isRecording { _ = try? writer.stop(failureReason: .permissionDenied) }
        try? FileManager.default.removeItem(at: root)
    }
}

private final class AcceptanceCommitFailures: @unchecked Sendable {
    private let lock = NSLock()
    private var count = 0
    private let failAt: Int?
    private let failFollowing: Bool
    private let onFirstCommit: (@Sendable () -> Void)?
    init(failAt: Int?, failFollowing: Bool, onFirstCommit: (@Sendable () -> Void)?) {
        self.failAt = failAt
        self.failFollowing = failFollowing
        self.onFirstCommit = onFirstCommit
    }
    func check() throws {
        try lock.withLock {
            count += 1
            if count == 1 { onFirstCommit?() }
            if let failAt, count == failAt || (failFollowing && count > failAt) {
                throw CocoaError(.fileWriteOutOfSpace)
            }
        }
    }
}

@MainActor private final class AcceptanceDecision {
    var current = true
    var pendingStopBundleID: String?
}

private func acceptanceScope() -> CaptureScopeApproval {
    CaptureScopeApproval(scopeApprovalId: "synthetic-scope", scopeKind: .display,
        sourceDisplayName: "Synthetic display", approvedAt: Date(timeIntervalSince1970: 9),
        approvalMode: .userConfirmedSuggestedScope, eligibleReason: .manualMeetingScope)
}

private func acceptancePermissions() -> SystemAudioPermissionSnapshot {
    SystemAudioPermissionSnapshot(microphone: .granted, systemAudio: .granted,
        evaluatedAt: Date(timeIntervalSince1970: 9))
}
