import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class DesktopUploadClientTests: XCTestCase {
    func testLocalRolesMapToBackendTrackRoles() {
        XCTAssertEqual(DesktopUploadClient.backendRole(for: .localMic), .microphone)
        XCTAssertEqual(DesktopUploadClient.backendRole(for: .remoteSpeaker), .system)
        XCTAssertEqual(DesktopUploadClient.backendRole(for: .mixedMeetingAudio), .media)
        XCTAssertEqual(DesktopUploadClient.backendRole(for: .reviewPlayback), .playback)
    }

    func testV5UploadDescriptorsContainOnlyCanonicalWAVManifestAndPlayback() {
        let descriptors = DesktopUploadClient.uploadFileDescriptors(for: makeV5QueueItem())

        XCTAssertEqual(descriptors.map(\.transportRole), [.manifest, .media, .playback])
        XCTAssertEqual(descriptors.first { $0.transportRole == .media }?.url.lastPathComponent, "meeting-transcription.wav")
        XCTAssertEqual(descriptors.first { $0.transportRole == .media }?.codec, "wav-pcm-s16le")
        XCTAssertEqual(descriptors.first { $0.transportRole == .media }?.sampleRateHz, 16_000)
        XCTAssertEqual(descriptors.first { $0.transportRole == .playback }?.url.lastPathComponent, "meeting-review.m4a")
        XCTAssertFalse(descriptors.contains { $0.transportRole == .microphone || $0.transportRole == .system })
    }

    func testV5CreateMeetingPayloadDeclaresSingleWAVSource() {
        let payload = DesktopUploadClient.createMeetingPayload(for: makeV5QueueItem())

        XCTAssertEqual(payload.source_kind, "initial_mixed_recording")
        XCTAssertEqual(payload.media_scribe_source_mode, "single_wav_v1")
    }

    func testV5ProgressUsesAllRequiredPackageBytesRatherThanFixedHalf() {
        let item = makeV5QueueItem().withTransition(
            to: .uploading,
            now: Date(timeIntervalSince1970: 2),
            serverTruth: ServerTruthFingerprint(
                acceptedBytesByTrack: ["media": 400],
                expectedTrackRoles: ["manifest", "media", "playback"]
            )
        )

        XCTAssertEqual(item.progressFraction, 400.0 / 1_928.0, accuracy: 0.0001)
        XCTAssertNotEqual(item.progressFraction, 0.5)
    }

    func testConfirmedProgressNeverRegressesWithinTheSameUploadSession() {
        let initial = ServerTruthFingerprint(
            meetingId: "meeting-1",
            uploadSessionId: "session-1",
            acceptedBytesByTrack: ["manifest": 128, "media": 600],
            expectedTrackRoles: ["manifest", "media", "playback"]
        )
        let staleServerRead = ServerTruthFingerprint(
            meetingId: "meeting-1",
            uploadSessionId: "session-1",
            acceptedBytesByTrack: ["manifest": 128, "media": 400, "playback": 300],
            expectedTrackRoles: ["manifest", "media", "playback"]
        )

        let merged = initial.mergingConfirmedProgress(staleServerRead)
        let item = makeV5QueueItem().withTransition(
            to: .uploading,
            now: Date(timeIntervalSince1970: 2),
            serverTruth: merged
        )

        XCTAssertEqual(merged.acceptedBytesByTrack["media"], 600)
        XCTAssertEqual(merged.acceptedBytesByTrack["playback"], 300)
        XCTAssertEqual(item.progressFraction, 1_028.0 / 1_928.0, accuracy: 0.0001)
        XCTAssertNotEqual(item.progressFraction, 0.5)
    }

    func testReconcileDecodesSafeDeletionAccessProcessingAndReviewTruth() async throws {
        let responseObject: [String: Any] = [
            "local_recording_id": "reconcile-fixture",
            "local_media_revision_id": "reconcile-fixture--initial",
            "meeting": [
                "meeting_id": "meeting-reconcile",
                "status": "uploaded",
                "processing_status": "failed_terminal",
                "deletion_state": "complete",
                "access_state": "owner",
            ],
            "media_revision": [
                "media_revision_id": "media-reconcile",
                "local_media_revision_id": "reconcile-fixture--initial",
                "track_sha256_by_role": [:],
            ],
            "upload_session": [
                "session_id": "session-reconcile",
                "status": "finalized",
                "expected_tracks": ["manifest", "media"],
                "accepted_bytes_by_track": ["manifest": 10],
                "missing_ranges_by_track": [:],
                "desktop_truth_rule": "server_ranges_authoritative",
            ],
            "processing": [
                "status": "failed_terminal",
                "workflow_id": "workflow-id-must-not-leave-client",
                "reason_code": "provider_timeout",
            ],
            "review": [
                "available": false,
                "status": "unavailable",
                "media_revision_id": "media-reconcile",
                "transcript_available": false,
                "diarization_available": false,
                "content_available": false,
                "web_url": "/meetings/private",
                "desktop_url": "/desktop/meetings/private",
            ],
            "conflict": [
                "state": "server_meeting_deleted",
                "reason": "server_meeting_deleted",
                "next_action": "send_support_report",
            ],
        ]
        let data = try JSONSerialization.data(withJSONObject: responseObject)
        let client = DesktopUploadClient(
            baseURL: try XCTUnwrap(URL(string: "https://sync.invalid")),
            headers: [:],
            partSizeBytes: 64 * 1024,
            cookieHeaderProvider: { _ in nil },
            requestExecutor: { _ in
                (
                    data,
                    try XCTUnwrap(HTTPURLResponse(
                        url: try XCTUnwrap(URL(string: "https://sync.invalid")),
                        statusCode: 200,
                        httpVersion: nil,
                        headerFields: nil
                    ))
                )
            }
        )

        let reconciliation = try await client.reconcile(makeQueueItem())

        XCTAssertEqual(reconciliation?.serverTruth.deletionState, "complete")
        XCTAssertEqual(reconciliation?.serverTruth.accessState, "owner")
        XCTAssertEqual(reconciliation?.serverTruth.processingReasonCode, "provider_timeout")
        XCTAssertEqual(reconciliation?.serverTruth.reviewAvailable, false)
        XCTAssertEqual(reconciliation?.serverTruth.reviewStatus, "unavailable")
        XCTAssertEqual(reconciliation?.serverTruth.conflictReason, "server_meeting_deleted")
        XCTAssertEqual(reconciliation?.serverTruth.nextAction, "send_support_report")
        XCTAssertEqual(reconciliation?.conflictState, .serverMeetingDeleted)
    }

    func testNewUploadSessionCanTruthfullyRestartConfirmedProgress() {
        let completedOldSession = ServerTruthFingerprint(
            uploadSessionId: "old-session",
            acceptedBytesByTrack: ["manifest": 128, "media": 800, "playback": 1_000],
            expectedTrackRoles: ["manifest", "media", "playback"]
        )
        let newSession = ServerTruthFingerprint(
            uploadSessionId: "new-session",
            acceptedBytesByTrack: ["manifest": 128],
            expectedTrackRoles: ["manifest", "media", "playback"]
        )

        let merged = completedOldSession.mergingConfirmedProgress(newSession)

        XCTAssertEqual(merged.uploadSessionId, "new-session")
        XCTAssertEqual(merged.acceptedBytesByTrack, ["manifest": 128])
    }

    func testDefaultPartSizeProducesRealIntermediateServerConfirmations() {
        XCTAssertEqual(DesktopUploadClient.defaultPartSizeBytes, 4 * 1024 * 1024)
    }

    func testV5UploadRunsFullDesktopRequestSequenceWithServerConfirmedProgress() async throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("desktop-upload-v5-sequence-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)

        let manifest = Data("{\"schema_version\":\"local-recording-manifest.v5\"}".utf8)
        let canonicalWAV = Data(repeating: 1, count: 128 * 1024)
        let reviewM4A = Data(repeating: 2, count: 32 * 1024)
        try manifest.write(to: root.appendingPathComponent("manifest.json"))
        try canonicalWAV.write(to: root.appendingPathComponent("meeting-transcription.wav"))
        try reviewM4A.write(to: root.appendingPathComponent("meeting-review.m4a"))

        let transport = SyntheticV5UploadTransport()
        let client = DesktopUploadClient(
            baseURL: try XCTUnwrap(URL(string: "https://synthetic-upload.invalid")),
            headers: ["X-Client-Version": "synthetic-v5"],
            partSizeBytes: 64 * 1024,
            cookieHeaderProvider: { _ in nil },
            requestExecutor: { request in
                try await transport.data(for: request)
            }
        )
        let progress = SyntheticV5UploadProgressRecorder()

        let result = try await client.upload(
            makeV5QueueItem(at: root, manifest: manifest, canonicalWAV: canonicalWAV, reviewM4A: reviewM4A),
            onProgress: { snapshot in
                await progress.append(snapshot)
            }
        )

        XCTAssertEqual(result.state, .uploaded)
        XCTAssertEqual(result.serverTruth.meetingId, "synthetic-meeting")
        XCTAssertEqual(result.serverTruth.uploadSessionId, "synthetic-session")
        XCTAssertEqual(result.serverTruth.acceptedBytesByTrack, [
            "manifest": Int64(manifest.count),
            "media": Int64(canonicalWAV.count),
            "playback": Int64(reviewM4A.count),
        ])

        let snapshots = await progress.snapshots()
        let totalBytes = Double(manifest.count + canonicalWAV.count + reviewM4A.count)
        let fractions = snapshots.map { snapshot in
            Double(snapshot.acceptedBytesByTrack.values.reduce(Int64(0), +)) / totalBytes
        }
        XCTAssertGreaterThanOrEqual(snapshots.count, 5)
        XCTAssertEqual(try XCTUnwrap(fractions.first), 0, accuracy: 0.0001)
        XCTAssertTrue(fractions.contains { $0 > 0 && $0 < 1 })
        XCTAssertEqual(try XCTUnwrap(fractions.last), 1, accuracy: 0.0001)
        XCTAssertEqual(fractions, fractions.sorted())

        let requests = await transport.recordedRequests()
        XCTAssertEqual(
            requests.map { "\($0.httpMethod ?? "") \($0.url?.path ?? "")" },
            [
                "POST /api/v1/meetings",
                "POST /api/v1/meetings/synthetic-meeting/upload-sessions",
                "PUT /api/v1/upload-sessions/synthetic-session/tracks/manifest/parts/0",
                "PUT /api/v1/upload-sessions/synthetic-session/tracks/media/parts/0",
                "PUT /api/v1/upload-sessions/synthetic-session/tracks/media/parts/1",
                "PUT /api/v1/upload-sessions/synthetic-session/tracks/playback/parts/0",
                "GET /api/v1/upload-sessions/synthetic-session/missing-ranges",
                "GET /api/v1/upload-sessions/synthetic-session/missing-ranges",
                "POST /api/v1/upload-sessions/synthetic-session/finalize",
            ]
        )
        let createMeeting = try XCTUnwrap(requests.first)
        let createPayload = try XCTUnwrap(try JSONSerialization.jsonObject(
            with: try XCTUnwrap(createMeeting.httpBody)
        ) as? [String: Any])
        XCTAssertEqual(createPayload["source_kind"] as? String, "initial_mixed_recording")
        XCTAssertEqual(createPayload["media_scribe_source_mode"] as? String, "single_wav_v1")

        let uploadSession = try XCTUnwrap(requests.dropFirst().first)
        let uploadSessionPayload = try XCTUnwrap(try JSONSerialization.jsonObject(
            with: try XCTUnwrap(uploadSession.httpBody)
        ) as? [String: Any])
        XCTAssertEqual(uploadSessionPayload["expected_tracks"] as? [String], ["manifest", "media", "playback"])

        let partRequests = requests.filter { $0.httpMethod == "PUT" }
        XCTAssertEqual(partRequests.map { $0.httpBody?.count }, [manifest.count, 64 * 1024, 64 * 1024, reviewM4A.count])
        XCTAssertEqual(
            partRequests.map { $0.value(forHTTPHeaderField: "Content-Type") },
            Array(repeating: "application/octet-stream", count: 4)
        )
    }

    func testMalformedV5PackageNeverFallsBackToDualDescriptors() {
        var item = makeV5QueueItem()
        item.artifactProfile.trackCompleteness[1].fileName = "incoming.wav"

        XCTAssertFalse(item.isV5Package)
        XCTAssertTrue(DesktopUploadClient.uploadFileDescriptors(for: item).isEmpty)
        XCTAssertTrue(DesktopUploadClient.uploadSessionFileDescriptors(for: item).isEmpty)
        XCTAssertEqual(
            DesktopUploadClient.createMeetingPayload(for: item).source_kind,
            "initial_mixed_recording"
        )
        XCTAssertEqual(
            DesktopUploadClientError.invalidArtifactPackage.failureCategory,
            .schemaIncompatibility
        )
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
        let item = makeQueueItem(includePlaybackM4A: true)
        let descriptors = DesktopUploadClient.uploadFileDescriptors(
            for: item,
            expectedRoles: [.microphone, .system, .manifest]
        )

        XCTAssertEqual(descriptors.map(\.transportRole), [.microphone, .system, .manifest])
        XCTAssertEqual(
            DesktopUploadClient.idempotencyKey(item: item, scope: "upload-session"),
            DesktopUploadClient.idempotencyKey(
                item: makeQueueItem(includePlaybackM4A: false),
                scope: "upload-session"
            )
        )
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
            schemaVersion: LocalRecordingManifest.legacySchemaVersion,
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

    func testCreateMeetingPayloadIncludesPersistedTitleSourceAndOpaqueCalendarAttempt() throws {
        var item = makeQueueItem(recordingMetadata: RecordingDisplayMetadata(
            recordingStartedAt: CalendarSettingsFixtures.recordingStartedAt,
            recordingStoppedAt: CalendarSettingsFixtures.recordingStartedAt.addingTimeInterval(60),
            title: "Zoom - 2026-07-13 03:26",
            titleStatus: .generated,
            titleSource: .appContext,
            titleConfidence: .high,
            titleGeneratedAt: CalendarSettingsFixtures.recordingStartedAt,
            safeFileBasename: "2026-07-13_03-26_zoom_ab12cd",
            stableSuffix: "ab12cd"
        ))
        item.calendarMatchAttemptId = CalendarSettingsFixtures.attemptID

        let payload = DesktopUploadClient.createMeetingPayload(for: item)
        let json = String(decoding: try JSONEncoder().encode(payload), as: UTF8.self)

        XCTAssertEqual(payload.title_source, .appContext)
        XCTAssertEqual(payload.calendar_match_attempt_id, CalendarSettingsFixtures.attemptID)
        XCTAssertTrue(json.contains("\"title_source\":\"app_context\""))
        XCTAssertTrue(json.contains("\"calendar_match_attempt_id\":\"" + CalendarSettingsFixtures.attemptID + "\""))
    }

    func testCreateMeetingPayloadAfterResolveFailureOmitsCalendarAttempt() throws {
        let item = makeQueueItem(recordingMetadata: RecordingDisplayMetadata(
            recordingStartedAt: CalendarSettingsFixtures.recordingStartedAt,
            recordingStoppedAt: CalendarSettingsFixtures.recordingStartedAt.addingTimeInterval(60),
            title: "Meeting - 2026-07-13 03:26",
            titleStatus: .generated,
            titleSource: .generic,
            titleConfidence: .medium,
            titleGeneratedAt: CalendarSettingsFixtures.recordingStartedAt,
            safeFileBasename: "2026-07-13_03-26_meeting_ab12cd",
            stableSuffix: "ab12cd"
        ))

        let payload = DesktopUploadClient.createMeetingPayload(for: item)
        let json = String(decoding: try JSONEncoder().encode(payload), as: UTF8.self)

        XCTAssertNil(item.calendarMatchAttemptId)
        XCTAssertNil(payload.calendar_match_attempt_id)
        XCTAssertFalse(json.contains("calendar_match_attempt_id"))
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

    func testAuthSessionCookieHeaderUsesOnlyOwnerSessionCookie() throws {
        let sessionCookie = try XCTUnwrap(HTTPCookie(properties: [
            .domain: "rec.2brain.pro",
            .path: "/",
            .name: DesktopUploadClient.ownerSessionCookieName,
            .value: "owner-session-token",
            .secure: "TRUE"
        ]))
        let unrelatedCookie = try XCTUnwrap(HTTPCookie(properties: [
            .domain: "rec.2brain.pro",
            .path: "/",
            .name: "other-cookie",
            .value: "other-value"
        ]))

        XCTAssertEqual(
            DesktopUploadClient.authSessionCookieHeader(from: [unrelatedCookie, sessionCookie]),
            "\(DesktopUploadClient.ownerSessionCookieName)=owner-session-token"
        )
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
          "incident_status": "pending_sync",
          "github_issue_number": null,
          "github_issue_url": null,
          "dedupe_status": "created",
          "affected_count": 1,
          "copy_fallback_available": true,
          "user_message": "Запрос принят сервером. Синхронизация с поддержкой ожидает проверки. Номер: CUST-123"
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder().decode(DesktopSupportIncidentResponse.self, from: payload)

        XCTAssertEqual(response.incidentId, "CUST-123")
        XCTAssertNil(response.githubIssueNumber)
        XCTAssertNil(response.githubIssueURL)
        XCTAssertTrue(response.isPendingSync)
        XCTAssertTrue(response.userMessage.contains("принят сервером"))
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

    func testDefaultPartSizeUsesConfirmedProgressGranularity() {
        XCTAssertEqual(DesktopUploadClient.defaultPartSizeBytes, 4 * 1024 * 1024)
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
            schemaVersion: LocalRecordingManifest.legacySchemaVersion,
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

    private func makeV5QueueItem() -> DesktopUploadQueueItem {
        let directoryPath = "/tmp/v5-directory"
        let profile = ArtifactCompletenessProfile(
            schemaVersion: "local-recording-manifest.v5",
            manifestPresent: true,
            microphonePresent: false,
            systemAudioPresent: false,
            manifestSha256: String(repeating: "a", count: 64),
            microphoneSha256: nil,
            systemAudioSha256: nil,
            manifestSizeBytes: 128,
            microphoneSizeBytes: 0,
            systemAudioSizeBytes: 0,
            durationSeconds: 60,
            trackCompleteness: [
                UploadTrackCompleteness(
                    transportRole: .manifest,
                    fileName: "manifest.json",
                    present: true,
                    byteCount: 128,
                    sha256: String(repeating: "a", count: 64),
                    durationSeconds: 1
                ),
                UploadTrackCompleteness(
                    transportRole: .media,
                    fileName: "meeting-transcription.wav",
                    present: true,
                    byteCount: 800,
                    sha256: String(repeating: "b", count: 64),
                    durationSeconds: 60
                ),
                UploadTrackCompleteness(
                    transportRole: .playback,
                    fileName: "meeting-review.m4a",
                    present: true,
                    byteCount: 1_000,
                    sha256: String(repeating: "c", count: 64),
                    durationSeconds: 60
                )
            ],
            isUploadable: true
        )
        return DesktopUploadQueueItem(
            id: "v5-queue-id",
            sessionId: "v5-session",
            directoryId: "v5-directory",
            directoryPath: directoryPath,
            manifestPath: URL(fileURLWithPath: directoryPath).appendingPathComponent("manifest.json").path,
            microphonePath: "metadata-only",
            systemAudioPath: "metadata-only",
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

    private func makeV5QueueItem(
        at directoryURL: URL,
        manifest: Data,
        canonicalWAV: Data,
        reviewM4A: Data
    ) -> DesktopUploadQueueItem {
        let manifestHash = DesktopUploadClient.sha256Hex(data: manifest)
        let canonicalWAVHash = DesktopUploadClient.sha256Hex(data: canonicalWAV)
        let reviewM4AHash = DesktopUploadClient.sha256Hex(data: reviewM4A)
        let profile = ArtifactCompletenessProfile(
            schemaVersion: LocalRecordingManifest.schemaVersion,
            manifestPresent: true,
            microphonePresent: false,
            systemAudioPresent: false,
            manifestSha256: manifestHash,
            microphoneSha256: nil,
            systemAudioSha256: nil,
            manifestSizeBytes: Int64(manifest.count),
            microphoneSizeBytes: 0,
            systemAudioSizeBytes: 0,
            durationSeconds: 1,
            trackCompleteness: [
                UploadTrackCompleteness(
                    transportRole: .manifest,
                    fileName: "manifest.json",
                    present: true,
                    byteCount: Int64(manifest.count),
                    sha256: manifestHash,
                    durationSeconds: 1
                ),
                UploadTrackCompleteness(
                    transportRole: .media,
                    fileName: "meeting-transcription.wav",
                    present: true,
                    byteCount: Int64(canonicalWAV.count),
                    sha256: canonicalWAVHash,
                    durationSeconds: 1
                ),
                UploadTrackCompleteness(
                    transportRole: .playback,
                    fileName: "meeting-review.m4a",
                    present: true,
                    byteCount: Int64(reviewM4A.count),
                    sha256: reviewM4AHash,
                    durationSeconds: 1
                ),
            ],
            isUploadable: true
        )
        return DesktopUploadQueueItem(
            id: "synthetic-v5-queue-id",
            sessionId: "synthetic-v5-session",
            directoryId: "synthetic-v5-directory",
            directoryPath: directoryURL.path,
            manifestPath: directoryURL.appendingPathComponent("manifest.json").path,
            microphonePath: "metadata-only",
            systemAudioPath: "metadata-only",
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

private actor SyntheticV5UploadProgressRecorder {
    private var values: [ServerTruthFingerprint] = []

    func append(_ value: ServerTruthFingerprint) {
        values.append(value)
    }

    func snapshots() -> [ServerTruthFingerprint] {
        values
    }
}

private actor SyntheticV5UploadTransport {
    private var requests: [URLRequest] = []

    func recordedRequests() -> [URLRequest] {
        requests
    }

    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        requests.append(request)

        let method = request.httpMethod ?? ""
        let path = request.url?.path ?? ""
        let responsePayload: (statusCode: Int, body: Data)
        switch (method, path) {
        case ("POST", "/api/v1/meetings"):
            responsePayload = success(meetingResponse())
        case ("POST", "/api/v1/meetings/synthetic-meeting/upload-sessions"):
            responsePayload = success(uploadSessionResponse(status: "active", acceptedBytes: [:]))
        case ("PUT", let uploadPath) where uploadPath.hasPrefix("/api/v1/upload-sessions/synthetic-session/tracks/"):
            let offset = Int(request.value(forHTTPHeaderField: "X-Byte-Offset") ?? "0") ?? 0
            responsePayload = success([
                "byte_offset": offset,
                "byte_length": request.httpBody?.count ?? 0,
            ])
        case ("GET", "/api/v1/upload-sessions/synthetic-session/missing-ranges"):
            responsePayload = success([
                "session_id": "synthetic-session",
                "missing_ranges_by_track": [:],
            ])
        case ("POST", "/api/v1/upload-sessions/synthetic-session/finalize"):
            responsePayload = success([
                "meeting": meetingResponse(status: "processing", processingStatus: "queued"),
                "upload_session": uploadSessionResponse(
                    status: "finalized",
                    acceptedBytes: acceptedBytesByTrack(),
                    processingStatus: "queued"
                ),
                "object_count": 3,
            ])
        default:
            responsePayload = (404, data(["code": "synthetic_unexpected_request"]))
        }
        guard let url = request.url,
              let response = HTTPURLResponse(
                url: url,
                statusCode: responsePayload.statusCode,
                httpVersion: "HTTP/1.1",
                headerFields: ["Content-Type": "application/json"]
              )
        else {
            throw URLError(.badURL)
        }
        return (responsePayload.body, response)
    }

    private func acceptedBytesByTrack() -> [String: Int] {
        var result: [String: Int] = [:]
        for request in requests where request.httpMethod == "PUT" {
            let pathComponents = request.url?.pathComponents ?? []
            guard let tracksIndex = pathComponents.firstIndex(of: "tracks"),
                  pathComponents.indices.contains(tracksIndex + 1)
            else {
                continue
            }
            let role = pathComponents[tracksIndex + 1]
            result[role, default: 0] += request.httpBody?.count ?? 0
        }
        return result
    }

    private func meetingResponse(
        status: String = "uploading",
        processingStatus: String = "not_submitted"
    ) -> [String: Any] {
        [
            "meeting_id": "synthetic-meeting",
            "local_recording_id": "synthetic-v5-directory",
            "local_media_revision_id": "synthetic-local-revision",
            "title": NSNull(),
            "title_source": "generic",
            "media_revision": [
                "media_revision_id": "synthetic-revision",
                "local_media_revision_id": "synthetic-local-revision",
            ],
            "status": status,
            "processing_status": processingStatus,
        ]
    }

    private func uploadSessionResponse(
        status: String,
        acceptedBytes: [String: Int],
        processingStatus: String = "not_submitted"
    ) -> [String: Any] {
        [
            "session_id": "synthetic-session",
            "meeting_id": "synthetic-meeting",
            "media_revision_id": "synthetic-revision",
            "status": status,
            "expires_at": "2026-07-17T00:00:00Z",
            "accepted_bytes_by_track": acceptedBytes,
            "expected_tracks": ["manifest", "media", "playback"],
            "processing_status": processingStatus,
            "desktop_truth_rule": "accepted_bytes",
        ]
    }

    private func success(_ object: [String: Any]) -> (statusCode: Int, body: Data) {
        (200, data(object))
    }

    private func data(_ object: [String: Any]) -> Data {
        guard let result = try? JSONSerialization.data(withJSONObject: object) else {
            fatalError("Synthetic v5 upload response must be JSON encodable")
        }
        return result
    }
}
#endif
