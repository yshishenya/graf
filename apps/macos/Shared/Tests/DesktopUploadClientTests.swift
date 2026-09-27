import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class DesktopUploadClientTests: XCTestCase {
    func testStartAcceptanceRejectsInvalidLiveManifestBeforeUploadAndReconcile() async throws {
        for invalidation in ["pending", "unknown", "session", "directory", "missing", "read-error", "malformed"] {
            for entry in ["upload", "reconcile"] {
                let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
                defer { try? FileManager.default.removeItem(at: root) }
                let item = try makeStartAcceptancePackage(at: root)
                XCTAssertTrue(item.isUploadEligible)
                let manifestURL = root.appendingPathComponent("manifest.json")
                switch invalidation {
                case "missing": try FileManager.default.removeItem(at: manifestURL)
                case "read-error":
                    try FileManager.default.removeItem(at: manifestURL)
                    try FileManager.default.createDirectory(at: manifestURL, withIntermediateDirectories: false)
                case "malformed": try Data("{".utf8).write(to: manifestURL, options: .atomic)
                default:
                    var object = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: manifestURL)) as? [String: Any])
                    switch invalidation {
                    case "session": object["sessionId"] = "other-session"
                    case "directory": object["directoryId"] = "other-directory"
                    default: object["startAcceptance"] = invalidation
                    }
                    try JSONSerialization.data(withJSONObject: object).write(to: manifestURL, options: .atomic)
                }
                let transport = SyntheticV5UploadTransport()
                let client = DesktopUploadClient(baseURL: URL(string: "https://synthetic-upload.invalid")!,
                    headers: [:], partSizeBytes: 64 * 1024, authSessionTokenProvider: { _ in nil },
                    requestExecutor: { try await transport.data(for: $0) })
                if entry == "upload" {
                    do {
                        _ = try await client.upload(item)
                        XCTFail("Invalid live manifest must refuse direct upload: \(invalidation)")
                    } catch {
                        // The decisive assertion is zero requests, regardless of the local error type.
                    }
                } else {
                    _ = try? await client.reconcile(item)
                }
                let requests = await transport.recordedRequests()
                XCTAssertTrue(requests.isEmpty, "\(invalidation)/\(entry)")
            }
        }
    }

    func testStartAcceptanceAcceptedAndLegacyManifestAllowDirectUpload() async throws {
        for acceptance in [nil, "accepted"] as [String?] {
            let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
            defer { try? FileManager.default.removeItem(at: root) }
            let item = try makeStartAcceptancePackage(at: root, acceptance: acceptance)
            let transport = SyntheticV5UploadTransport()
            let client = DesktopUploadClient(baseURL: URL(string: "https://synthetic-upload.invalid")!,
                headers: [:], partSizeBytes: 64 * 1024, authSessionTokenProvider: { _ in nil },
                requestExecutor: { try await transport.data(for: $0) })
            let result = try await client.upload(item)
            let requests = await transport.recordedRequests()
            XCTAssertEqual(result.state, .uploaded)
            XCTAssertEqual(requests.count, 9)
            XCTAssertEqual(requests.last?.url?.lastPathComponent, "finalize")
        }
    }

    func testStartAcceptanceServerOnlyGETWithoutManifestDoesNotAuthorizeUpload() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        var item = try makeStartAcceptancePackage(at: root)
        item.meetingId = "synthetic-known-meeting"
        item.ownerScope = try RecordingDeletionScope(serverOrigin: "https://synthetic-upload.invalid",
            workspaceID: "synthetic-workspace", actorUserID: "synthetic-owner")
        try FileManager.default.removeItem(at: URL(fileURLWithPath: item.manifestPath))
        XCTAssertTrue(item.isUploadEligible, "The cached profile remains allowed after local manifest removal")
        XCTAssertFalse(FileManager.default.fileExists(atPath: item.manifestPath))

        let responseData = try JSONSerialization.data(withJSONObject: [
            "local_recording_id": item.directoryId,
            "local_media_revision_id": item.localMediaRevisionId,
            "meeting": ["meeting_id": "synthetic-known-meeting", "status": "uploading", "access_state": "owner"],
            "media_revision": ["track_sha256_by_role": [:]],
            "upload_session": ["accepted_bytes_by_track": [:], "missing_ranges_by_track": [:]],
            "processing": ["status": "not_submitted"],
            "conflict": ["state": "none", "next_action": "continue_upload"],
        ] as [String: Any])
        let recorder = StartAcceptanceRequestRecorder()
        let client = DesktopUploadClient(baseURL: URL(string: "https://synthetic-upload.invalid")!,
            headers: [:], partSizeBytes: 64 * 1024, authSessionTokenProvider: { _ in nil },
            requestExecutor: { request in
                await recorder.record(request)
                return (responseData, try XCTUnwrap(HTTPURLResponse(url: try XCTUnwrap(request.url),
                    statusCode: 200, httpVersion: nil, headerFields: nil)))
            })

        let serverTruth = try await client.reconcileServerTruth(item)
        let reconciliation = try XCTUnwrap(serverTruth)
        XCTAssertTrue(reconciliation.canContinueUpload)
        let requests = await recorder.snapshot()
        XCTAssertEqual(requests.count, 1)
        XCTAssertEqual(requests.first?.httpMethod, "GET")
        XCTAssertEqual(requests.first?.url?.path, "/api/v1/desktop/recordings/\(item.directoryId)/sync-state")
        XCTAssertEqual(requests.first?.value(forHTTPHeaderField: "X-Graf-Expected-Actor"), "synthetic-owner")
        XCTAssertEqual(requests.first?.value(forHTTPHeaderField: "X-Graf-Expected-Workspace"), "synthetic-workspace")
        XCTAssertNil(requests.first?.httpBody)

        // Applying permissive server truth still cannot replace local start admission.
        item.serverTruth = reconciliation.serverTruth
        do {
            _ = try await client.upload(item)
            XCTFail("Server-only reconciliation must not authorize an upload without its live manifest")
        } catch RecordingStartAcceptanceGate.Refusal.manifestUnavailable {
        } catch {
            XCTFail("Expected local manifest refusal, got \(error)")
        }
        let afterUpload = await recorder.snapshot()
        XCTAssertEqual(afterUpload.count, 1, "The failed upload must add no transport requests")
        XCTAssertEqual(afterUpload.first?.httpMethod, "GET")
    }

    func testStartAcceptanceRechecksLiveManifestAfterEveryProgressAwait() async throws {
        for permittedRequests in 0...8 {
            let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
            defer { try? FileManager.default.removeItem(at: root) }
            let item = try makeStartAcceptancePackage(at: root)
            let manifestURL = root.appendingPathComponent("manifest.json")
            let pending = try Self.startAcceptanceJSON(Data(contentsOf: manifestURL), value: "pending")
            let transport = SyntheticV5UploadTransport()
            let client = DesktopUploadClient(baseURL: URL(string: "https://synthetic-upload.invalid")!,
                headers: [:], partSizeBytes: 64 * 1024, authSessionTokenProvider: { _ in nil },
                requestExecutor: { try await transport.data(for: $0) })
            do {
                _ = try await client.upload(item, onProgress: { _ in
                    if await transport.recordedRequests().count >= permittedRequests {
                        // Do not cancel from the observer: the live admission check must stop upload.
                        try pending.write(to: manifestURL, options: .atomic)
                    }
                })
                XCTFail("Pending at boundary \(permittedRequests) must stop remaining requests")
            } catch {}
            XCTAssertEqual(try Data(contentsOf: manifestURL), pending)
            let requests = await transport.recordedRequests()
            XCTAssertEqual(requests.count, permittedRequests, "boundary \(permittedRequests)")
            XCTAssertFalse(requests.contains { $0.url?.path.hasSuffix("/finalize") == true })
        }
    }

    func testStartAcceptanceRechecksLiveManifestAfterTransportAwait() async throws {
        for permittedRequests in 1...8 {
            let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
            defer { try? FileManager.default.removeItem(at: root) }
            let item = try makeStartAcceptancePackage(at: root)
            let manifestURL = root.appendingPathComponent("manifest.json")
            let pending = try Self.startAcceptanceJSON(Data(contentsOf: manifestURL), value: "pending")
            let transport = SyntheticV5UploadTransport()
            let client = DesktopUploadClient(baseURL: URL(string: "https://synthetic-upload.invalid")!,
                headers: [:], partSizeBytes: 64 * 1024, authSessionTokenProvider: { _ in nil },
                requestExecutor: { request in
                    let response = try await transport.data(for: request)
                    if await transport.recordedRequests().count == permittedRequests {
                        try pending.write(to: manifestURL, options: .atomic)
                    }
                    return response
                })
            do {
                _ = try await client.upload(item)
                XCTFail("Pending after response \(permittedRequests) must stop remaining requests")
            } catch {}
            XCTAssertEqual(try Data(contentsOf: manifestURL), pending)
            let requests = await transport.recordedRequests()
            XCTAssertEqual(requests.count, permittedRequests, "response \(permittedRequests)")
            XCTAssertFalse(requests.contains { $0.url?.path.hasSuffix("/finalize") == true })
        }
    }

    private func makeStartAcceptancePackage(at root: URL, acceptance: String? = nil) throws -> DesktopUploadQueueItem {
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let media = Data(repeating: 1, count: 128 * 1024)
        let playback = Data(repeating: 2, count: 32 * 1024)
        var manifest = try makeRuntimeManifest(canonicalWAV: media, reviewM4A: playback)
        if let acceptance { manifest = try Self.startAcceptanceJSON(manifest, value: acceptance) }
        try manifest.write(to: root.appendingPathComponent("manifest.json"))
        try media.write(to: root.appendingPathComponent("meeting-transcription.wav"))
        try playback.write(to: root.appendingPathComponent("meeting-review.m4a"))
        return makeV5QueueItem(at: root, manifest: manifest, canonicalWAV: media, reviewM4A: playback)
    }

    // Inject the field as JSON so these regression tests also compile before the model gains it.
    private static func startAcceptanceJSON(_ data: Data, value: String) throws -> Data {
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        object["startAcceptance"] = value
        return try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
    }

    private func makeRuntimeManifest(canonicalWAV: Data, reviewM4A: Data) throws -> Data {
        let startedAt = Date(timeIntervalSince1970: 10)
        let manifest = LocalRecordingManifest(
            sessionId: "synthetic-v5-session", createdAt: startedAt, startedAt: startedAt,
            stoppedAt: startedAt.addingTimeInterval(1), status: .saved,
            directoryId: "synthetic-v5-directory", transcriptionReadiness: .ready,
            tracks: [
                LocalRecordingTrack(trackId: "canonical-media", role: .mixedMeetingAudio,
                    sourceKind: .canonicalMix, mediaScribeField: .mediaFile, status: .saved,
                    fileName: "meeting-transcription.wav", format: "wav-pcm-s16le",
                    sampleRate: 16_000, channelCount: 1, bitsPerSample: 16, durationMs: 1_000,
                    byteCount: Int64(canonicalWAV.count), sha256: DesktopUploadClient.sha256Hex(data: canonicalWAV),
                    frameCount: 16_000, timelineStartMs: 0, timelineAligned: true),
                LocalRecordingTrack(trackId: "review-playback", role: .reviewPlayback,
                    sourceKind: .canonicalMix, mediaScribeField: .playbackFile, status: .saved,
                    fileName: "meeting-review.m4a", format: "m4a-aac-lc",
                    sampleRate: 48_000, channelCount: 1, bitsPerSample: 0, durationMs: 1_000,
                    byteCount: Int64(reviewM4A.count), sha256: DesktopUploadClient.sha256Hex(data: reviewM4A),
                    frameCount: 48_000, aacPresentationFrameDelta: 0, timelineStartMs: 0, timelineAligned: true)
            ], scopeApproval: CaptureScopeApproval(scopeApprovalId: "synthetic-scope", scopeKind: .display,
                sourceDisplayName: "Synthetic Meeting", approvedAt: startedAt,
                approvalMode: .userConfirmedSuggestedScope, eligibleReason: .manualMeetingScope),
            permissions: SystemAudioPermissionSnapshot(microphone: .granted, systemAudio: .granted,
                evaluatedAt: startedAt))
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return try encoder.encode(manifest)
    }

    func testLocalRolesMapToBackendTrackRoles() {
        XCTAssertNil(DesktopUploadClient.backendRole(for: .localMic))
        XCTAssertNil(DesktopUploadClient.backendRole(for: .remoteSpeaker))
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

    func testV5CreateMeetingPayloadDeclaresSingleWAVSource() throws {
        let payload = try DesktopUploadClient.createMeetingPayload(for: makeV5QueueItem())

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
                "summary_status": "failed",
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
            authSessionTokenProvider: { _ in nil },
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

        // Server-only status/deletion reads must work after the local package is gone.
        let reconciliation = try await client.reconcileServerTruth(makeQueueItem())

        XCTAssertEqual(reconciliation?.serverTruth.deletionState, "complete")
        XCTAssertEqual(reconciliation?.serverTruth.accessState, "owner")
        XCTAssertEqual(reconciliation?.serverTruth.processingReasonCode, "provider_timeout")
        XCTAssertEqual(reconciliation?.serverTruth.reviewAvailable, false)
        XCTAssertEqual(reconciliation?.serverTruth.reviewStatus, "unavailable")
        XCTAssertEqual(reconciliation?.serverTruth.transcriptAvailable, false)
        XCTAssertEqual(reconciliation?.serverTruth.summaryStatus, "failed")
        XCTAssertEqual(reconciliation?.serverTruth.conflictReason, "server_meeting_deleted")
        XCTAssertEqual(reconciliation?.serverTruth.nextAction, "send_support_report")
        XCTAssertEqual(reconciliation?.conflictState, .serverMeetingDeleted)
    }

    func testServerTruthReadinessMetadataRoundTripsAndCannotLeakThroughOmittedProgress() throws {
        let old = try JSONDecoder().decode(ServerTruthFingerprint.self,
            from: Data(#"{"acceptedBytesByTrack":{},"requiredTrackSha256":{}}"#.utf8))
        XCTAssertNil(old.transcriptAvailable)
        let ready = ServerTruthFingerprint(uploadSessionId: "session", acceptedBytesByTrack: ["media": 100],
            summaryStatus: "available", transcriptAvailable: true)
        XCTAssertEqual(try JSONDecoder().decode(ServerTruthFingerprint.self, from: JSONEncoder().encode(ready)), ready)
        let merged = ready.mergingConfirmedProgress(.init(uploadSessionId: "session", acceptedBytesByTrack: ["media": 50]))
        XCTAssertEqual(merged.acceptedBytesByTrack["media"], 100)
        XCTAssertNil(merged.summaryStatus)
        XCTAssertNil(merged.transcriptAvailable)
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

    func testUploadChecksCurrentEligibilityBeforeEveryNextRequestIncludingFinalize() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let media = Data(repeating: 1, count: 128 * 1024)
        let playback = Data(repeating: 2, count: 32 * 1024)
        let manifest = try makeRuntimeManifest(canonicalWAV: media, reviewM4A: playback)
        try manifest.write(to: root.appendingPathComponent("manifest.json"))
        try media.write(to: root.appendingPathComponent("meeting-transcription.wav"))
        try playback.write(to: root.appendingPathComponent("meeting-review.m4a"))

        // Revoke admission after each response, including both missing-range reads.
        // The progress handler is the queue's current-state check, not a stale item flag.
        for permittedRequests in 0...8 {
            let transport = SyntheticV5UploadTransport()
            let client = DesktopUploadClient(baseURL: URL(string: "https://synthetic-upload.invalid")!,
                headers: [:], partSizeBytes: 64 * 1024, authSessionTokenProvider: { _ in nil },
                requestExecutor: { try await transport.data(for: $0) })
            do {
                _ = try await client.upload(
                    makeV5QueueItem(at: root, manifest: manifest, canonicalWAV: media, reviewM4A: playback),
                    onProgress: { _ in
                        if await transport.recordedRequests().count >= permittedRequests {
                            throw CancellationError()
                        }
                    })
                XCTFail("Revoked eligibility must cancel the remaining requests")
            } catch is CancellationError {
                let requests = await transport.recordedRequests()
                XCTAssertEqual(requests.count, permittedRequests)
                XCTAssertFalse(requests.contains { $0.url?.path.hasSuffix("/finalize") == true })
            }
        }
    }

    func testV5UploadRunsFullDesktopRequestSequenceWithServerConfirmedProgress() async throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("desktop-upload-v5-sequence-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)

        let canonicalWAV = Data(repeating: 1, count: 128 * 1024)
        let reviewM4A = Data(repeating: 2, count: 32 * 1024)
        let manifest = try makeRuntimeManifest(canonicalWAV: canonicalWAV, reviewM4A: reviewM4A)
        try manifest.write(to: root.appendingPathComponent("manifest.json"))
        try canonicalWAV.write(to: root.appendingPathComponent("meeting-transcription.wav"))
        try reviewM4A.write(to: root.appendingPathComponent("meeting-review.m4a"))

        let transport = SyntheticV5UploadTransport()
        let client = DesktopUploadClient(
            baseURL: try XCTUnwrap(URL(string: "https://synthetic-upload.invalid")),
            headers: ["X-Client-Version": "synthetic-v5"],
            partSizeBytes: 64 * 1024,
            authSessionTokenProvider: { _ in nil },
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
        XCTAssertThrowsError(try DesktopUploadClient.createMeetingPayload(for: item))
        XCTAssertEqual(
            DesktopUploadClientError.invalidArtifactPackage.failureCategory,
            .schemaIncompatibility
        )
    }

    func testIdempotencyKeyIsDeterministicAndScoped() {
        let item = makeQueueItem()

        XCTAssertEqual(
            DesktopUploadClient.idempotencyKey(item: item, scope: "meeting"),
            "desktop-upload:meeting:v5-directory:v5-session"
        )
        XCTAssertNotEqual(
            DesktopUploadClient.idempotencyKey(item: item, scope: "meeting"),
            DesktopUploadClient.idempotencyKey(item: item, scope: "upload-session")
        )
    }

    func testV5DescriptorsRejectHistoricalServerSessionRoles() {
        let descriptors = DesktopUploadClient.uploadFileDescriptors(
            for: makeV5QueueItem(), expectedRoles: [.microphone, .system]
        )
        XCTAssertTrue(descriptors.isEmpty)
    }

    func testProgressFractionUsesServerExpectedRolesWhenPlaybackIsNotPartOfExistingSession() {
        let item = makeHistoricalQueueItem(includePlaybackM4A: true).withTransition(
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

    func testCreateMeetingPayloadUsesPersistedRecordingTimes() throws {
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

        let payload = try DesktopUploadClient.createMeetingPayload(for: item)

        XCTAssertEqual(payload.started_at, startedAt)
        XCTAssertEqual(payload.ended_at, stoppedAt)
        XCTAssertEqual(payload.recording_display_timezone_offset_minutes, 180)
        XCTAssertEqual(payload.duration_seconds, 60)
    }

    func testCreateMeetingPayloadUsesPersistedGeneratedTitle() throws {
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

        XCTAssertEqual(try DesktopUploadClient.createMeetingPayload(for: item).title, "Meeting - 1970-01-01 00:00")
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

        let payload = try DesktopUploadClient.createMeetingPayload(for: item)
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

        let payload = try DesktopUploadClient.createMeetingPayload(for: item)
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

    func testSanitizedHeaderPreviewRedactsExplicitNativeSession() throws {
        let client = DesktopUploadClient(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.pro")),
            headers: ["X-Auth-Session": "owner-session-token"],
            authSessionTokenProvider: { _ in nil }
        )

        XCTAssertEqual(client.sanitizedHeaderPreview["X-Auth-Session"], "<redacted>")
        XCTAssertFalse(client.sanitizedHeaderPreview.values.contains("owner-session-token"))
    }

    func testCurrentAuthenticationUsesOnlyDedicatedHeaderOrSessionProvider() throws {
        let baseURL = try XCTUnwrap(URL(string: "https://rec.2brain.pro"))
        XCTAssertFalse(DesktopUploadClient(
            baseURL: baseURL,
            headers: ["X-User-Id": "not-authentication"],
            authSessionTokenProvider: { _ in nil }
        ).hasCurrentAuthentication)
        XCTAssertTrue(DesktopUploadClient(
            baseURL: baseURL,
            headers: ["Authorization": "Bearer fake-test-value"],
            authSessionTokenProvider: { _ in nil }
        ).hasCurrentAuthentication)
        XCTAssertTrue(DesktopUploadClient(
            baseURL: baseURL,
            authSessionTokenProvider: { _ in "fake-test-session" }
        ).hasCurrentAuthentication)
        XCTAssertFalse(DesktopUploadClient(
            baseURL: baseURL,
            authSessionTokenProvider: { _ in "   " }
        ).hasCurrentAuthentication)
    }

    func testAuthSessionTokenUsesOnlyOwnerSessionCookie() throws {
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
            DesktopUploadClient.authSessionToken(from: [unrelatedCookie, sessionCookie]),
            "owner-session-token"
        )
    }

    func testAuthSessionTokenUsesLocalCookieForLoopbackOrigin() throws {
        let localCookie = try XCTUnwrap(HTTPCookie(properties: [
            .domain: "127.0.0.1",
            .path: "/",
            .name: DesktopUploadClient.localOwnerSessionCookieName,
            .value: "local-owner-session-token"
        ]))
        let localURL = try XCTUnwrap(URL(string: "http://127.0.0.1:8081/desktop/meetings"))

        XCTAssertEqual(
            DesktopUploadClient.authSessionToken(from: [localCookie], localURL),
            "local-owner-session-token"
        )
        XCTAssertNil(DesktopUploadClient.authSessionToken(from: [localCookie]))
    }

    func testAuthSessionTokenSelectsMostSpecificApplicableLocalCookieDeterministically() throws {
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let url = try XCTUnwrap(URL(string: "http://127.0.0.1:8081/desktop/meetings/current"))
        let expired = try authCookie(
            name: DesktopUploadClient.localOwnerSessionCookieName,
            value: "expired",
            domain: "127.0.0.1",
            path: "/desktop/meetings",
            secure: false,
            expiresAt: now.addingTimeInterval(-1)
        )
        let exactRoot = try authCookie(
            name: DesktopUploadClient.localOwnerSessionCookieName,
            value: "root",
            domain: "127.0.0.1",
            path: "/",
            secure: false,
            expiresAt: now.addingTimeInterval(600)
        )
        let exactPath = try authCookie(
            name: DesktopUploadClient.localOwnerSessionCookieName,
            value: "current",
            domain: "127.0.0.1",
            path: "/desktop/meetings",
            secure: false,
            expiresAt: now.addingTimeInterval(300)
        )
        let wrongPath = try authCookie(
            name: DesktopUploadClient.localOwnerSessionCookieName,
            value: "wrong-path",
            domain: "127.0.0.1",
            path: "/desktop/admin",
            secure: false,
            expiresAt: now.addingTimeInterval(900)
        )

        let cookies = [expired, exactRoot, exactPath, wrongPath]
        XCTAssertEqual(DesktopUploadClient.authSessionToken(from: cookies, url, now: now), "current")
        XCTAssertEqual(DesktopUploadClient.authSessionToken(from: Array(cookies.reversed()), url, now: now), "current")
    }

    func testProductionHostCookieRequiresSecureExactHostAndRootPath() throws {
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let url = try XCTUnwrap(URL(string: "https://rec.2brain.pro/desktop/meetings"))
        let valid = try authCookie(value: "valid", domain: "rec.2brain.pro")
        let insecure = try authCookie(value: "insecure", domain: "rec.2brain.pro", secure: false)
        let domainCookie = try authCookie(value: "domain", domain: ".rec.2brain.pro")
        let parentDomain = try authCookie(value: "parent", domain: ".2brain.pro")
        let nonRootPath = try authCookie(value: "path", domain: "rec.2brain.pro", path: "/desktop")

        XCTAssertEqual(
            DesktopUploadClient.authSessionToken(
                from: [insecure, domainCookie, parentDomain, nonRootPath, valid],
                url,
                now: now
            ),
            "valid"
        )

        let plan = DesktopCabinetSessionBridge.reconciliation(
            webCookies: [insecure, domainCookie, parentDomain, nonRootPath],
            nativeCookies: [insecure, domainCookie, parentDomain, nonRootPath, valid],
            originURL: url,
            now: now
        )
        XCTAssertEqual(Set(plan.cookiesToDelete.map(\.value)), ["domain", "insecure", "parent", "path", "valid"])
        XCTAssertTrue(plan.cookiesToSet.isEmpty)
    }

    func testAuthSessionTokenRejectsSecureCookieOnHTTPAndWrongDomain() throws {
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let httpURL = try XCTUnwrap(URL(string: "http://127.0.0.1:8081/desktop/meetings"))
        let secureLocal = try authCookie(
            name: DesktopUploadClient.localOwnerSessionCookieName,
            value: "secure-local",
            domain: "127.0.0.1",
            secure: true
        )
        let wrongDomain = try authCookie(
            name: DesktopUploadClient.localOwnerSessionCookieName,
            value: "wrong-domain",
            domain: "localhost"
        )

        XCTAssertNil(DesktopUploadClient.authSessionToken(from: [secureLocal, wrongDomain], httpURL, now: now))
    }

    func testCabinetCookieReconciliationReplacesStaleCookieAndHandlesLogout() throws {
        let origin = try XCTUnwrap(URL(string: "https://rec.2brain.pro/desktop/meetings"))
        let oldCookie = try authCookie(value: "old-session", domain: "rec.2brain.pro")
        let currentCookie = try authCookie(value: "current-session", domain: "rec.2brain.pro")
        let unrelated = try authCookie(name: "unrelated", value: "keep", domain: "rec.2brain.pro")

        let replacement = DesktopCabinetSessionBridge.reconciliation(
            webCookies: [currentCookie, unrelated],
            nativeCookies: [oldCookie, unrelated],
            originURL: origin
        )
        XCTAssertEqual(replacement.cookiesToDelete.map(\.value), ["old-session"])
        XCTAssertEqual(replacement.cookiesToSet.map(\.value), ["current-session"])

        let logout = DesktopCabinetSessionBridge.reconciliation(
            webCookies: [unrelated],
            nativeCookies: [currentCookie, unrelated],
            originURL: origin
        )
        XCTAssertEqual(logout.cookiesToDelete.map(\.value), ["current-session"])
        XCTAssertTrue(logout.cookiesToSet.isEmpty)
    }

    func testCabinetCookieReconciliationIgnoresSubsecondExpiryNormalization() throws {
        let origin = try XCTUnwrap(URL(string: "https://rec.2brain.pro/desktop/meetings"))
        let webCookie = try authCookie(
            value: "current-session",
            domain: "rec.2brain.pro",
            expiresAt: Date(timeIntervalSince1970: 1_800_000_000.75)
        )
        let nativeCookie = try authCookie(
            value: "current-session",
            domain: "rec.2brain.pro",
            expiresAt: Date(timeIntervalSince1970: 1_800_000_000)
        )

        let plan = DesktopCabinetSessionBridge.reconciliation(
            webCookies: [webCookie],
            nativeCookies: [nativeCookie],
            originURL: origin,
            now: Date(timeIntervalSince1970: 1_799_999_000)
        )

        XCTAssertTrue(plan.cookiesToDelete.isEmpty)
        XCTAssertTrue(plan.cookiesToSet.isEmpty)
    }

    func testNativeRequestPromotesOwnerSessionWithoutForwardingCookies() async throws {
        let recorder = NativeAuthRequestRecorder()
        let client = DesktopUploadClient(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.pro")),
            headers: ["Cookie": "browser-cookie-must-not-leave-native-client"],
            partSizeBytes: DesktopUploadClient.defaultPartSizeBytes,
            authSessionTokenProvider: { _ in "owner-session-token" },
            requestExecutor: { request in
                await recorder.record(request)
                return (
                    Data("""
                    {
                      "task_id": "purge-task",
                      "meeting_id": "meeting-id",
                      "task_type": "purge_local_buffers",
                      "state": "acknowledged",
                      "safe_reason": null,
                      "expires_at": "2026-07-23T00:00:00Z",
                      "ack_url": null
                    }
                    """.utf8),
                    try XCTUnwrap(HTTPURLResponse(
                        url: try XCTUnwrap(request.url),
                        statusCode: 200,
                        httpVersion: nil,
                        headerFields: nil
                    ))
                )
            }
        )
        let task = DesktopLocalPurgeTask(
            taskId: "purge-task",
            meetingId: "meeting-id",
            taskType: .purgeLocalBuffers,
            state: .pending,
            safeReason: nil,
            expiresAt: Date(timeIntervalSince1970: 1_800_000_000),
            ackURL: nil
        )

        _ = try await client.acknowledgeLocalPurgeTask(
            task,
            state: .acknowledged,
            reasonCode: "local_artifacts_deleted"
        )

        let recordedRequest = await recorder.request()
        let request = try XCTUnwrap(recordedRequest)
        XCTAssertFalse(request.httpShouldHandleCookies)
        XCTAssertNil(request.value(forHTTPHeaderField: "Cookie"))
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-Auth-Session"), "owner-session-token")
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.url?.path, "/api/v1/desktop/local-purge-tasks/purge-task/ack")
    }

    private func authCookie(
        name: String = DesktopUploadClient.ownerSessionCookieName,
        value: String,
        domain: String,
        path: String = "/",
        secure: Bool = true,
        expiresAt: Date? = nil
    ) throws -> HTTPCookie {
        var properties: [HTTPCookiePropertyKey: Any] = [
            .domain: domain,
            .path: path,
            .name: name,
            .value: value,
        ]
        if secure {
            properties[.secure] = "TRUE"
        }
        if let expiresAt {
            properties[.expires] = expiresAt
        }
        return try XCTUnwrap(HTTPCookie(properties: properties))
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

    private func makeQueueItem(recordingMetadata: RecordingDisplayMetadata? = nil) -> DesktopUploadQueueItem {
        var item = makeV5QueueItem()
        item.recordingMetadata = recordingMetadata
        return item
    }

    private func makeHistoricalQueueItem(
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

private actor StartAcceptanceRequestRecorder {
    private var requests: [URLRequest] = []

    func record(_ request: URLRequest) { requests.append(request) }
    func snapshot() -> [URLRequest] { requests }
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

private actor NativeAuthRequestRecorder {
    private var value: URLRequest?

    func record(_ request: URLRequest) {
        value = request
    }

    func request() -> URLRequest? {
        value
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
