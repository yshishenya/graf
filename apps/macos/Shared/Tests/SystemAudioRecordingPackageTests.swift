import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioRecordingPackageTests: XCTestCase {
    func testDualIndependentSourcesProduceMicIncomingAndManifest() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-package-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let micSource = BufferedLocalRecordingSampleSource()
        let incomingSource = BufferedLocalRecordingSampleSource()
        micSource.append(Array(repeating: 0.12, count: 48_000))
        incomingSource.append(Array(repeating: 0.20, count: 48_000))

        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { micSource },
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: true
        )
        let scopeApproval = CaptureScopeApproval(
            scopeApprovalId: "scope-package",
            scopeKind: .display,
            sourceDisplayName: "Current Display",
            approvedAt: Date(timeIntervalSince1970: 9),
            approvalMode: .userConfirmedSuggestedScope,
            eligibleReason: .manualMeetingScope
        )
        let permissions = SystemAudioPermissionSnapshot(
            microphone: .granted,
            systemAudio: .granted,
            evaluatedAt: Date(timeIntervalSince1970: 9)
        )

        let directory = try writer.start(
            sessionId: "session",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: scopeApproval,
            permissions: permissions
        )
        Thread.sleep(forTimeInterval: 0.2)
        let manifest = try writer.stop(stoppedAt: Date(timeIntervalSince1970: 11))

        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.localMicURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.remoteSpeakerURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.manifestURL.path))
        XCTAssertEqual(Set(manifest.tracks.map(\.role)), Set([.localMic, .remoteSpeaker]))
        XCTAssertEqual(manifest.tracks.first { $0.role == .localMic }?.sourceKind, .microphone)
        XCTAssertEqual(manifest.tracks.first { $0.role == .remoteSpeaker }?.sourceKind, .systemAudio)
        XCTAssertEqual(manifest.status, .saved)
        XCTAssertTrue(manifest.isComplete)
        XCTAssertEqual(manifest.scopeApproval?.scopeApprovalId, "scope-package")
        XCTAssertEqual(manifest.permissions?.microphone, .granted)
        XCTAssertEqual(manifest.permissions?.systemAudio, .granted)
        XCTAssertFalse(manifest.externalEgressStarted)
        XCTAssertFalse(manifest.transcriptionStarted)
    }

    func testAsyncStopProducesSameDualTrackPackageWithoutMainThreadFinalization() async throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-package-async-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let micSource = BufferedLocalRecordingSampleSource()
        let incomingSource = BufferedLocalRecordingSampleSource()
        micSource.append(Array(repeating: 0.18, count: 48_000))
        incomingSource.append(Array(repeating: 0.22, count: 48_000))

        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { micSource },
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: true
        )
        let scopeApproval = CaptureScopeApproval(
            scopeApprovalId: "scope-async-package",
            scopeKind: .display,
            sourceDisplayName: "Current Display",
            approvedAt: Date(timeIntervalSince1970: 19),
            approvalMode: .userConfirmedSuggestedScope,
            eligibleReason: .manualMeetingScope
        )
        let permissions = SystemAudioPermissionSnapshot(
            microphone: .granted,
            systemAudio: .granted,
            evaluatedAt: Date(timeIntervalSince1970: 19)
        )

        let directory = try writer.start(
            sessionId: "session-async",
            startedAt: Date(timeIntervalSince1970: 20),
            scopeApproval: scopeApproval,
            permissions: permissions
        )
        Thread.sleep(forTimeInterval: 0.2)
        let manifest = try await writer.stopAsync(stoppedAt: Date(timeIntervalSince1970: 21))

        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.localMicURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.remoteSpeakerURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.manifestURL.path))
        XCTAssertEqual(Set(manifest.tracks.map(\.role)), Set([.localMic, .remoteSpeaker]))
        XCTAssertEqual(manifest.status, .saved)
        XCTAssertTrue(manifest.isComplete)
        XCTAssertEqual(manifest.scopeApproval?.scopeApprovalId, "scope-async-package")
        XCTAssertEqual(manifest.permissions?.microphone, .granted)
        XCTAssertEqual(manifest.permissions?.systemAudio, .granted)
    }

    func testAsyncStartAndStopProduceDualTrackPackageWithoutMainThreadFinalization() async throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-package-async-start-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let micSource = BufferedLocalRecordingSampleSource()
        let incomingSource = BufferedLocalRecordingSampleSource()
        micSource.append(Array(repeating: 0.16, count: 48_000))
        incomingSource.append(Array(repeating: 0.24, count: 48_000))

        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { micSource },
            incomingSampleSourceFactory: { incomingSource },
            recordMicrophone: true
        )
        let scopeApproval = CaptureScopeApproval(
            scopeApprovalId: "scope-async-start-package",
            scopeKind: .display,
            sourceDisplayName: "Current Display",
            approvedAt: Date(timeIntervalSince1970: 29),
            approvalMode: .userConfirmedSuggestedScope,
            eligibleReason: .manualMeetingScope
        )
        let permissions = SystemAudioPermissionSnapshot(
            microphone: .granted,
            systemAudio: .granted,
            evaluatedAt: Date(timeIntervalSince1970: 29)
        )

        let directory = try await writer.startAsync(
            sessionId: "session-async-start",
            startedAt: Date(timeIntervalSince1970: 30),
            scopeApproval: scopeApproval,
            permissions: permissions
        )
        Thread.sleep(forTimeInterval: 0.2)
        let manifest = try await writer.stopAsync(stoppedAt: Date(timeIntervalSince1970: 31))

        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.localMicURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.remoteSpeakerURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: directory.manifestURL.path))
        XCTAssertEqual(Set(manifest.tracks.map(\.role)), Set([.localMic, .remoteSpeaker]))
        XCTAssertEqual(manifest.status, .saved)
        XCTAssertTrue(manifest.isComplete)
        XCTAssertEqual(manifest.scopeApproval?.scopeApprovalId, "scope-async-start-package")
        XCTAssertEqual(manifest.permissions?.microphone, .granted)
        XCTAssertEqual(manifest.permissions?.systemAudio, .granted)
    }

    func testAsyncStartFailureDoesNotLeaveWriterRecording() async throws {
        let blockedRoot = FileManager.default.temporaryDirectory
            .appendingPathComponent("system-audio-package-blocked-root-\(UUID().uuidString)")
        FileManager.default.createFile(atPath: blockedRoot.path, contents: Data())
        defer { try? FileManager.default.removeItem(at: blockedRoot) }

        let writer = LocalRecordingWriter(
            store: LocalRecordingStore(rootURL: blockedRoot),
            microphoneSampleSourceFactory: { BufferedLocalRecordingSampleSource() },
            incomingSampleSourceFactory: { BufferedLocalRecordingSampleSource() },
            recordMicrophone: true
        )

        do {
            _ = try await writer.startAsync(
                sessionId: "session-blocked-start",
                startedAt: Date(timeIntervalSince1970: 40),
                scopeApproval: scopeApproval(id: "scope-blocked-start"),
                permissions: grantedPermissions()
            )
            XCTFail("Start should fail when the recording root is a file")
        } catch LocalRecordingWriterError.directoryUnavailable {
            XCTAssertFalse(writer.isRecording)
        }
    }
}
#endif

private func scopeApproval(id: String) -> CaptureScopeApproval {
    CaptureScopeApproval(
        scopeApprovalId: id,
        scopeKind: .display,
        sourceDisplayName: "Current Display",
        approvedAt: Date(timeIntervalSince1970: 39),
        approvalMode: .userConfirmedSuggestedScope,
        eligibleReason: .manualMeetingScope
    )
}

private func grantedPermissions() -> SystemAudioPermissionSnapshot {
    SystemAudioPermissionSnapshot(
        microphone: .granted,
        systemAudio: .granted,
        evaluatedAt: Date(timeIntervalSince1970: 39)
    )
}
