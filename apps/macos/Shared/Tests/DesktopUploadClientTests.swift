import Foundation
@testable import TwoBrainRecAppCore
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

    func testUploadFileDescriptorsIncludeOptionalPlaybackM4AReviewArtifact() throws {
        let descriptors = DesktopUploadClient.uploadFileDescriptors(for: makeQueueItem(includePlaybackM4A: true))
        let playback = try XCTUnwrap(descriptors.first(where: { $0.transportRole == .playback }))

        XCTAssertEqual(descriptors.map(\.transportRole), [.microphone, .system, .manifest, .playback])
        XCTAssertEqual(playback.url.lastPathComponent, "meeting-review.m4a")
        XCTAssertEqual(playback.byteCount, 1_024)
        XCTAssertEqual(playback.sha256, String(repeating: "d", count: 64))
        XCTAssertEqual(playback.codec, "m4a-aac-lc")
        XCTAssertEqual(playback.sampleRateHz, 48_000)
        XCTAssertEqual(playback.channelCount, 1)
        XCTAssertEqual(playback.durationSeconds, 60)
    }

    func testUploadFileDescriptorsRespectExistingServerSessionRoles() {
        let descriptors = DesktopUploadClient.uploadFileDescriptors(
            for: makeQueueItem(includePlaybackM4A: true),
            expectedRoles: [.microphone, .system, .manifest]
        )

        XCTAssertEqual(descriptors.map(\.transportRole), [.microphone, .system, .manifest])
    }

    func testUploadFileDescriptorsTreatEmptyExpectedRolesAsUnrestrictedLegacySession() {
        let descriptors = DesktopUploadClient.uploadFileDescriptors(
            for: makeQueueItem(includePlaybackM4A: true),
            expectedRoles: []
        )

        XCTAssertEqual(descriptors.map(\.transportRole), [.microphone, .system, .manifest, .playback])
    }

    func testUploadSessionFileDescriptorsDropMissingOptionalPlaybackBeforeSessionCreation() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("desktop-upload-client-missing-playback-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)

        let descriptors = DesktopUploadClient.uploadSessionFileDescriptors(
            for: makeQueueItem(includePlaybackM4A: true, directoryURL: root)
        )

        XCTAssertEqual(descriptors.map(\.transportRole), [.microphone, .system, .manifest])
    }

    func testUploadSessionFileDescriptorsKeepPresentOptionalPlaybackBeforeSessionCreation() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("desktop-upload-client-present-playback-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try Data(repeating: 1, count: 1_024).write(to: root.appendingPathComponent("meeting-review.m4a"))

        let descriptors = DesktopUploadClient.uploadSessionFileDescriptors(
            for: makeQueueItem(includePlaybackM4A: true, directoryURL: root)
        )

        XCTAssertEqual(descriptors.map(\.transportRole), [.microphone, .system, .manifest, .playback])
    }

    func testUploadSessionFileDescriptorsDropSizeMismatchedOptionalPlaybackBeforeSessionCreation() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("desktop-upload-client-mismatched-playback-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try Data(repeating: 1, count: 1_023).write(to: root.appendingPathComponent("meeting-review.m4a"))

        let descriptors = DesktopUploadClient.uploadSessionFileDescriptors(
            for: makeQueueItem(includePlaybackM4A: true, directoryURL: root)
        )

        XCTAssertEqual(descriptors.map(\.transportRole), [.microphone, .system, .manifest])
    }

    func testProgressFractionUsesServerExpectedRolesWhenPlaybackIsNotPartOfExistingSession() {
        let item = makeQueueItem(includePlaybackM4A: true).withTransition(
            to: .retrying,
            now: Date(timeIntervalSince1970: 2),
            serverTruth: ServerTruthFingerprint(
                acceptedBytesByTrack: [
                    "microphone": 256,
                    "system": 512,
                    "manifest": 128
                ],
                expectedTrackRoles: ["microphone", "system", "manifest"]
            )
        )

        XCTAssertEqual(item.progressFraction, 1)
    }

    func testServerTruthHasAcceptedAllFallsBackToLegacyArtifactSizes() {
        let incomplete = ServerTruthFingerprint(acceptedBytesByTrack: [
            "manifest": 128,
            "microphone": 256,
            "system": 511
        ])
        let complete = ServerTruthFingerprint(acceptedBytesByTrack: [
            "manifest": 128,
            "microphone": 256,
            "system": 512
        ])
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

        XCTAssertFalse(incomplete.hasAcceptedAll(profile: profile))
        XCTAssertTrue(complete.hasAcceptedAll(profile: profile))
    }

    func testCreateMeetingPayloadUsesPersistedRecordingTimes() {
        let startedAt = Date(timeIntervalSince1970: 1_782_470_600)
        let stoppedAt = Date(timeIntervalSince1970: 1_782_474_200)
        let item = makeQueueItem(recordingMetadata: RecordingDisplayMetadata(
            recordingStartedAt: startedAt,
            recordingStoppedAt: stoppedAt,
            recordingDisplayTimeZoneOffsetMinutes: 180,
            title: "Zoom - 2026-06-26 11:30",
            titleStatus: .generated,
            titleSource: .appContext,
            titleConfidence: .high,
            titleGeneratedAt: Date(timeIntervalSince1970: 1_782_470_601),
            safeFileBasename: "2026-06-26_11-30_zoom-2026-06-26-11-30_ab12cd",
            stableSuffix: "ab12cd"
        ))

        let payload = DesktopUploadClient.createMeetingPayload(for: item)

        XCTAssertEqual(payload.started_at, startedAt)
        XCTAssertEqual(payload.ended_at, stoppedAt)
        XCTAssertEqual(payload.recording_display_timezone_offset_minutes, 180)
        XCTAssertEqual(payload.duration_seconds, 60)
    }

    func testCreateMeetingPayloadUsesPersistedGeneratedTitle() {
        let item = makeQueueItem(recordingMetadata: RecordingDisplayMetadata(
            recordingStartedAt: Date(timeIntervalSince1970: 1),
            recordingStoppedAt: Date(timeIntervalSince1970: 2),
            title: "Meeting - 1970-01-01 00:00",
            titleStatus: .generated,
            titleSource: .generic,
            titleConfidence: .medium,
            titleGeneratedAt: Date(timeIntervalSince1970: 3),
            safeFileBasename: "1970-01-01_00-00_meeting-1970-01-01-00-00_ab12cd",
            stableSuffix: "ab12cd"
        ))

        XCTAssertEqual(DesktopUploadClient.createMeetingPayload(for: item).title, "Meeting - 1970-01-01 00:00")
    }

    func testConfiguredHeadersIncludeBearerTokenWithoutPersistingSecrets() {
        let headers = DesktopUploadClient.configuredHeaders(from: [
            "GRAF_CLIENT_VERSION": "smoke-014",
            "GRAF_USER_ID": "00000000-0000-0000-0000-000000014003",
            "GRAF_ORGANIZATION_ID": "00000000-0000-0000-0000-000000014001",
            "GRAF_WORKSPACE_ID": "00000000-0000-0000-0000-000000014002",
            "GRAF_DEVICE_ID": "00000000-0000-0000-0000-000000014004",
            "GRAF_UPLOAD_BEARER_TOKEN": "secret-smoke-token"
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
            "GRAF_CLIENT_VERSION": "smoke-014",
            "GRAF_BEARER_TOKEN": "generic-token-that-must-not-be-used"
        ])

        XCTAssertNil(headers["Authorization"])
    }

    func testConfiguredHeadersAcceptLegacyTwoBrainKeys() {
        let headers = DesktopUploadClient.configuredHeaders(from: [
            "TWO_BRAIN_REC_CLIENT_VERSION": "legacy-014",
            "TWO_BRAIN_REC_USER_ID": "legacy-user",
            "TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN": "legacy-token"
        ])

        XCTAssertEqual(headers["X-Client-Version"], "legacy-014")
        XCTAssertEqual(headers["X-User-Id"], "legacy-user")
        XCTAssertEqual(headers["Authorization"], "Bearer legacy-token")
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

    func testDesktopCalendarUpcomingUsesReadOnlyCalendarEndpoint() {
        XCTAssertEqual(
            DesktopUploadClient.desktopCalendarUpcomingPath,
            "/api/v1/desktop/calendar/upcoming"
        )
    }

    func testSupportIncidentRequestUsesDesktopEndpointTimeoutAndIdempotency() throws {
        let report = try XCTUnwrap(makeSupportIncidentReport())
        let client = DesktopUploadClient(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.pro")),
            headers: [
                "X-Client-Version": "test-client",
                "Authorization": "Bearer test-token"
            ]
        )

        let request = try client.supportIncidentRequest(for: report)
        let body = String(data: try XCTUnwrap(request.httpBody), encoding: .utf8) ?? ""

        XCTAssertEqual(request.url?.path, DesktopUploadClient.supportIncidentPath)
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.timeoutInterval, DesktopUploadClient.supportIncidentTimeoutSeconds)
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
        XCTAssertEqual(
            request.value(forHTTPHeaderField: "Idempotency-Key"),
            "support-incident:\(report.safeReportFingerprint)"
        )
        XCTAssertTrue(body.contains("\"schema_version\":\"desktop-support-incident.v1\""))
        XCTAssertTrue(body.contains("\"normal_user_action\":\"send_support_report\""))
        XCTAssertTrue(body.contains("\"redaction_state\":\"metadata_only\""))
        XCTAssertFalse(body.contains("/tmp/directory"))
        XCTAssertFalse(body.contains("test-token"))
    }

    func testSupportIncidentContextFingerprintsDesktopScopeHeaders() throws {
        let client = DesktopUploadClient(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.pro")),
            headers: [
                "X-Workspace-Id": "workspace-raw",
                "X-User-Id": "user-raw",
                "X-Device-Id": "device-raw"
            ]
        )

        let context = client.supportIncidentContext()

        XCTAssertEqual(context.environmentBaseURLIdentity, "rec.2brain.pro")
        XCTAssertTrue(context.workspaceFingerprint.hasPrefix("ws_fpr_"))
        XCTAssertTrue(context.userFingerprint.hasPrefix("usr_fpr_"))
        XCTAssertTrue(context.deviceFingerprint.hasPrefix("dev_fpr_"))
        XCTAssertEqual(context.safeDeviceIdentifier, "device:\(context.deviceFingerprint)")
        XCTAssertFalse(context.workspaceFingerprint.contains("workspace-raw"))
        XCTAssertFalse(context.userFingerprint.contains("user-raw"))
        XCTAssertFalse(context.deviceFingerprint.contains("device-raw"))
    }

    func testSupportIncidentResponseDecodesCustodyNumber() throws {
        let payload = """
        {
          "incident_id": "CUST-123",
          "incident_status": "created",
          "github_issue_number": 123,
          "github_issue_url": "https://github.com/yshishenya/crisp/issues/123",
          "dedupe_status": "created",
          "affected_count": 1,
          "copy_fallback_available": true,
          "user_message": "Отчет отправлен. Мы разберемся. Номер: CUST-123"
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder().decode(DesktopSupportIncidentResponse.self, from: payload)

        XCTAssertEqual(response.incidentId, "CUST-123")
        XCTAssertEqual(response.githubIssueNumber, 123)
        XCTAssertEqual(response.userMessage, DesktopSupportIncidentFixture.successMessage)
    }

    func testQueueItemPreservesOptionalCalendarContextEventId() throws {
        var item = makeQueueItem()
        item.calendarContextEventId = "00000000-0000-0000-0000-000000000060"

        let encoded = try JSONEncoder().encode(item)
        let decoded = try JSONDecoder().decode(DesktopUploadQueueItem.self, from: encoded)

        XCTAssertEqual(decoded.calendarContextEventId, "00000000-0000-0000-0000-000000000060")
    }

    func testCalendarContextLinkRequestDoesNotCarryProviderCredentials() throws {
        let request = DesktopCalendarContextLinkRequest(
            eventId: "00000000-0000-0000-0000-000000000060",
            contextReason: "manual_selection"
        )
        let json = String(data: try JSONEncoder().encode(request), encoding: .utf8) ?? ""

        XCTAssertTrue(json.contains("\"event_id\":\"00000000-0000-0000-0000-000000000060\""))
        XCTAssertTrue(json.contains("\"context_reason\":\"manual_selection\""))
        XCTAssertFalse(json.contains("credential"))
        XCTAssertFalse(json.contains("provider"))
        XCTAssertFalse(json.contains("token"))
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

    func testOnlyRecordingNotFoundMeansServerUnknownLocalCustody() {
        XCTAssertTrue(DesktopUploadClient.isServerUnknownRecording(status: 404, code: "recording_not_found"))
        XCTAssertFalse(DesktopUploadClient.isServerUnknownRecording(status: 404, code: "meeting_not_found"))
        XCTAssertFalse(DesktopUploadClient.isServerUnknownRecording(status: 403, code: "recording_not_found"))
    }

    func testProblemCodesDriveUploadFailureCategoryBeforeHTTPStatus() {
        XCTAssertEqual(
            DesktopUploadClientError.failureCategory(forHTTPStatus: 409, code: "session_expired"),
            .authSession
        )
        XCTAssertEqual(
            DesktopUploadClientError.failureCategory(forHTTPStatus: 400, code: "recording_duration_exceeded"),
            .storageQuota
        )
        XCTAssertEqual(
            DesktopUploadClientError.failureCategory(forHTTPStatus: 409, code: "range_conflict"),
            .serverValidation
        )
        XCTAssertEqual(
            DesktopUploadClientError.failureCategory(forHTTPStatus: 409, code: "unexpected_track_role"),
            .serverValidation
        )
        XCTAssertEqual(
            DesktopUploadClientError.failureCategory(forHTTPStatus: 409, code: "storage_unavailable"),
            .network
        )
        XCTAssertEqual(
            DesktopUploadClientError.failureCategory(
                forHTTPStatus: 503,
                code: "support_incident.github_unavailable"
            ),
            .network
        )
    }

    private func makeSupportIncidentReport() -> DesktopSupportIncidentReport? {
        var item = makeQueueItem()
        item = item.withTransition(
            to: .blocked,
            now: Date(timeIntervalSince1970: 20),
            failureCategory: .serverValidation,
            failureReason: "http_status_503:support_incident.github_unavailable",
            retryMode: .manualOnly,
            syncConflictState: .retentionExpired
        )
        let projection = DesktopUploadCustodyProjection(item: item, now: Date(timeIntervalSince1970: 20))
        return DesktopSupportIncidentReport(
            item: item,
            projection: projection,
            context: DesktopSupportIncidentReportContext(
                appVersion: "2026.06.27",
                buildVersion: "1234",
                environmentBaseURLIdentity: "rec.2brain.pro",
                workspaceFingerprint: "ws_fpr_7e57",
                userFingerprint: "usr_fpr_7e57",
                deviceFingerprint: "dev_fpr_7e57",
                safeDeviceIdentifier: "device:dev_fpr_7e57"
            )
        )
    }

    private func makeQueueItem(
        recordingMetadata: RecordingDisplayMetadata? = nil,
        includePlaybackM4A: Bool = false,
        directoryURL: URL? = nil
    ) -> DesktopUploadQueueItem {
        let directoryPath = directoryURL?.path ?? "/tmp/directory"
        var tracks: [UploadTrackCompleteness] = [
            UploadTrackCompleteness(
                transportRole: .microphone,
                fileName: "mic.wav",
                present: true,
                byteCount: 256,
                sha256: String(repeating: "b", count: 64),
                durationSeconds: 60
            ),
            UploadTrackCompleteness(
                transportRole: .system,
                fileName: "incoming.wav",
                present: true,
                byteCount: 512,
                sha256: String(repeating: "c", count: 64),
                durationSeconds: 60
            ),
            UploadTrackCompleteness(
                transportRole: .manifest,
                fileName: "manifest.json",
                present: true,
                byteCount: 128,
                sha256: String(repeating: "a", count: 64),
                durationSeconds: 1
            )
        ]
        if includePlaybackM4A {
            tracks.append(UploadTrackCompleteness(
                transportRole: .playback,
                fileName: "meeting-review.m4a",
                present: true,
                byteCount: 1_024,
                sha256: String(repeating: "d", count: 64),
                durationSeconds: 60
            ))
        }
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
            trackCompleteness: tracks,
            isUploadable: true
        )
        return DesktopUploadQueueItem(
            id: "queue-id",
            sessionId: "session",
            directoryId: "directory",
            directoryPath: directoryPath,
            manifestPath: URL(fileURLWithPath: directoryPath).appendingPathComponent("manifest.json").path,
            microphonePath: URL(fileURLWithPath: directoryPath).appendingPathComponent("mic.wav").path,
            systemAudioPath: URL(fileURLWithPath: directoryPath).appendingPathComponent("incoming.wav").path,
            state: .queued,
            retryMode: .automatic,
            retentionDeadline: Date(timeIntervalSince1970: 1_000),
            createdAt: Date(timeIntervalSince1970: 1),
            updatedAt: Date(timeIntervalSince1970: 1),
            recordingMetadata: recordingMetadata,
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
