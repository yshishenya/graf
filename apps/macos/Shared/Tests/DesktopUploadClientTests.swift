import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class DesktopUploadClientTests: XCTestCase {
    func testLocalRolesMapToBackendTrackRoles() {
        XCTAssertEqual(DesktopUploadClient.backendRole(for: .localMic), .microphone)
        XCTAssertEqual(DesktopUploadClient.backendRole(for: .remoteSpeaker), .system)
        XCTAssertNil(DesktopUploadClient.backendRole(for: .mixedMeetingAudio))
    }

    func testIdempotencyKeyIsDeterministicAndScoped() {
        let item = makeQueueItem()

        XCTAssertEqual(
            DesktopUploadClient.idempotencyKey(item: item, scope: "meeting"),
            "desktop-upload:meeting:directory:session"
        )
        XCTAssertNotEqual(
            DesktopUploadClient.idempotencyKey(item: item, scope: "meeting"),
            DesktopUploadClient.idempotencyKey(item: item, scope: "upload-session")
        )
    }

    func testUploadFileDescriptorsUseBackendTransportRoles() {
        let descriptors = DesktopUploadClient.uploadFileDescriptors(for: makeQueueItem())

        XCTAssertEqual(descriptors.map(\.transportRole), [.microphone, .system, .manifest])
        XCTAssertEqual(descriptors.first { $0.transportRole == .manifest }?.codec, "json")
        XCTAssertEqual(descriptors.first { $0.transportRole == .microphone }?.sampleRateHz, 16_000)
    }

    func testConfiguredHeadersIncludeBearerTokenWithoutPersistingSecrets() {
        let headers = DesktopUploadClient.configuredHeaders(from: [
            "TWO_BRAIN_REC_CLIENT_VERSION": "smoke-014",
            "TWO_BRAIN_REC_USER_ID": "00000000-0000-0000-0000-000000014003",
            "TWO_BRAIN_REC_ORGANIZATION_ID": "00000000-0000-0000-0000-000000014001",
            "TWO_BRAIN_REC_WORKSPACE_ID": "00000000-0000-0000-0000-000000014002",
            "TWO_BRAIN_REC_DEVICE_ID": "00000000-0000-0000-0000-000000014004",
            "TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN": "secret-smoke-token"
        ])

        XCTAssertEqual(headers["X-Client-Version"], "smoke-014")
        XCTAssertEqual(headers["X-Organization-Id"], "00000000-0000-0000-0000-000000014001")
        XCTAssertEqual(headers["X-Workspace-Id"], "00000000-0000-0000-0000-000000014002")
        XCTAssertEqual(headers["X-User-Id"], "00000000-0000-0000-0000-000000014003")
        XCTAssertEqual(headers["X-Device-Id"], "00000000-0000-0000-0000-000000014004")
        XCTAssertEqual(headers["Authorization"], "Bearer secret-smoke-token")
    }

    func testBearerHeaderDoesNotDoublePrefix() {
        XCTAssertEqual(
            DesktopUploadClient.authorizationHeaderValue(forBearerToken: "Bearer already-prefixed"),
            "Bearer already-prefixed"
        )
        XCTAssertNil(DesktopUploadClient.authorizationHeaderValue(forBearerToken: "   "))
    }

    func testConfiguredHeadersIgnoreGenericBearerFallback() {
        let headers = DesktopUploadClient.configuredHeaders(from: [
            "TWO_BRAIN_REC_CLIENT_VERSION": "smoke-014",
            "TWO_BRAIN_REC_BEARER_TOKEN": "generic-token-that-must-not-be-used"
        ])

        XCTAssertNil(headers["Authorization"])
    }

    func testConfiguredFallsBackToPackagedProductionUploadOriginWithoutShellEnvironment() throws {
        let suiteName = "DesktopUploadClientTests.packaged-default"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defaults.removePersistentDomain(forName: suiteName)

        let client = try XCTUnwrap(DesktopUploadClient.configured(from: [:], defaults: defaults))

        XCTAssertEqual(client.baseOrigin.absoluteString, "https://rec.2brain.pro")
        XCTAssertEqual(client.sanitizedHeaderPreview["X-Client-Version"], "local-macos")
        XCTAssertNil(client.sanitizedHeaderPreview["Authorization"])
    }

    func testPartNumberUsesZeroBasedServerConvention() {
        XCTAssertEqual(
            DesktopUploadClient.partNumber(forByteOffset: 0, partSizeBytes: 128),
            0
        )
        XCTAssertEqual(
            DesktopUploadClient.partNumber(forByteOffset: 127, partSizeBytes: 128),
            0
        )
        XCTAssertEqual(
            DesktopUploadClient.partNumber(forByteOffset: 128, partSizeBytes: 128),
            1
        )
    }

    func testDefaultPartSizeMatchesServerSingleTrackLimit() {
        XCTAssertEqual(DesktopUploadClient.defaultPartSizeBytes, 1024 * 1024 * 1024)
    }

    private func makeQueueItem() -> DesktopUploadQueueItem {
        let profile = ArtifactCompletenessProfile(
            schemaVersion: LocalRecordingManifest.schemaVersion,
            manifestPresent: true,
            microphonePresent: true,
            systemAudioPresent: true,
            manifestSha256: String(repeating: "a", count: 64),
            microphoneSha256: String(repeating: "b", count: 64),
            systemAudioSha256: String(repeating: "c", count: 64),
            manifestSizeBytes: 128,
            microphoneSizeBytes: 256,
            systemAudioSizeBytes: 512,
            durationSeconds: 60,
            trackCompleteness: [],
            isUploadable: true
        )
        return DesktopUploadQueueItem(
            id: "queue-id",
            sessionId: "session",
            directoryId: "directory",
            directoryPath: "/tmp/directory",
            manifestPath: "/tmp/directory/manifest.json",
            microphonePath: "/tmp/directory/mic.wav",
            systemAudioPath: "/tmp/directory/incoming.wav",
            state: .queued,
            retryMode: .automatic,
            retentionDeadline: Date(timeIntervalSince1970: 1_000),
            createdAt: Date(timeIntervalSince1970: 1),
            updatedAt: Date(timeIntervalSince1970: 1),
            artifactProfile: profile,
            retentionDecision: RetentionDecision(
                decision: .retain,
                decidedAt: Date(timeIntervalSince1970: 1),
                reason: "test",
                localArtifactsRetained: true,
                policyReference: "test"
            )
        )
    }
}
#endif
