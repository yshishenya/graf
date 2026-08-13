import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MeetingTargetRegistryTests: XCTestCase {
    func testAssistedAutoStartPolicyRequiresSafeOpaqueReferences() throws {
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let policy = AssistedAutoStartPolicySnapshot(
            policyRef: "sha256:" + String(repeating: "a", count: 64),
            acknowledgementSubjectRef: "sha256:" + String(repeating: "b", count: 64),
            deviceRef: "sha256:" + String(repeating: "c", count: 64),
            policyVersion: "2026.08.12.1",
            acknowledgementVersion: "2026.08.12.1",
            issuedAt: now,
            expiresAt: now.addingTimeInterval(3_600)
        )
        let document = MeetingTargetRegistryDocument(
            registryVersion: "2026.08.12.1",
            generatedAt: now,
            targets: [Self.promptTarget()],
            assistedAutoStartPolicy: policy
        )

        XCTAssertNoThrow(try MeetingTargetRegistryValidator.validate(document, now: now))
        XCTAssertTrue(policy.isActive(at: now))
        XCTAssertFalse(policy.isActive(at: now.addingTimeInterval(3_601)))
    }

    func testAssistedAutoStartPolicyRejectsRawOrMalformedReference() {
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let document = MeetingTargetRegistryDocument(
            registryVersion: "2026.08.12.1",
            generatedAt: now,
            targets: [Self.promptTarget()],
            assistedAutoStartPolicy: AssistedAutoStartPolicySnapshot(
                policyRef: "raw-workspace-id",
                acknowledgementSubjectRef: "raw-user-id",
                deviceRef: "raw-device-id",
                policyVersion: "2026.08.12.1",
                acknowledgementVersion: "2026.08.12.1",
                issuedAt: now,
                expiresAt: now.addingTimeInterval(3_600)
            )
        )

        XCTAssertThrowsError(try MeetingTargetRegistryValidator.validate(document, now: now)) {
            XCTAssertEqual($0 as? MeetingTargetRegistryError, .invalidAssistedAutoStartPolicy)
        }
    }
    func testNoRemoteOrCacheFailsClosedWithoutPackagedSeed() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = MeetingTargetRegistryStore(
            cacheURL: root.appendingPathComponent("registry-cache.json")
        )

        XCTAssertThrowsError(try store.resolve()) { error in
            XCTAssertEqual(error as? MeetingTargetRegistryError, .noUsableRegistry)
        }
    }

    func testValidRemoteRegistryIsCachedAndPreferred() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let cacheURL = root.appendingPathComponent("registry-cache.json")
        let store = MeetingTargetRegistryStore(cacheURL: cacheURL)

        let resolution = try store.resolve(
            remoteData: Self.seedRegistryData(registryVersion: "2026.07.09.1"),
            remoteETag: "etag-remote"
        )
        let cache = try store.loadCache()

        XCTAssertEqual(resolution.source, .remote)
        XCTAssertEqual(resolution.document.registryVersion, "2026.07.09.1")
        XCTAssertEqual(cache.etag, "etag-remote")
        XCTAssertEqual(cache.registry.registryVersion, "2026.07.09.1")
        XCTAssertTrue(FileManager.default.fileExists(atPath: cacheURL.path))
    }

    func testInvalidRemoteFallsBackToPreviousValidCache() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = MeetingTargetRegistryStore(cacheURL: root.appendingPathComponent("cache.json"))
        _ = try store.resolve(remoteData: Self.seedRegistryData(registryVersion: "2026.07.09.1"), remoteETag: "etag-cache")

        let resolution = try store.resolve(remoteData: Self.unsafePromptRegistryData(), remoteETag: "etag-bad")

        XCTAssertEqual(resolution.source, .remoteCache)
        XCTAssertEqual(resolution.document.registryVersion, "2026.07.09.1")
        XCTAssertEqual(resolution.etag, "etag-cache")
    }

    func testUnsafePromptEnabledTargetFailsClosed() throws {
        XCTAssertThrowsError(
            try MeetingDetectionCoding.decoder().decode(
                MeetingTargetRegistryDocument.self,
                from: Self.unsafePromptRegistryData()
            ).validatedForTest()
        ) { error in
            XCTAssertEqual(error as? MeetingTargetRegistryError, .unsafePromptTarget("unsafe_zoom"))
        }
    }

    func testBundleResolutionIsCaseInsensitive() throws {
        let document = try MeetingDetectionCoding.decoder().decode(
            MeetingTargetRegistryDocument.self,
            from: Self.seedRegistryData()
        )

        XCTAssertEqual(document.target(forBundleID: "US.ZOOM.XOS")?.id, "zoom")
    }

    func testRegistryRejectsCaseInsensitiveDuplicateBundleIDs() throws {
        let document = MeetingTargetRegistryDocument(
            registryVersion: "2026.07.21.1",
            generatedAt: Date(timeIntervalSince1970: 1_779_887_120),
            targets: [
                MeetingTargetRegistryTarget(
                    id: "telegram_desktop",
                    displayName: "Telegram Desktop",
                    market: .global,
                    platform: .macos,
                    targetFamily: .nativeApp,
                    mode: .promptEnabled,
                    evidence: .packageVerified,
                    requiredSignals: [.macOSAudioHALAssertion],
                    nativeBundleIds: ["com.tdesktop.Telegram"]
                ),
                MeetingTargetRegistryTarget(
                    id: "telegram_duplicate",
                    displayName: "Telegram duplicate",
                    market: .global,
                    platform: .macos,
                    targetFamily: .nativeApp,
                    mode: .promptEnabled,
                    evidence: .packageVerified,
                    requiredSignals: [.macOSAudioHALAssertion],
                    nativeBundleIds: ["COM.TDESKTOP.TELEGRAM"]
                )
            ]
        )

        XCTAssertThrowsError(try MeetingTargetRegistryValidator.validate(document)) { error in
            XCTAssertEqual(
                error as? MeetingTargetRegistryError,
                .duplicateBundleID("COM.TDESKTOP.TELEGRAM")
            )
        }
    }

    func testExpandedRegistryEnablesEveryVerifiedNativeTarget() throws {
        let data = try Data(
            contentsOf: Self.repositoryRoot()
                .appendingPathComponent(
                    "apps/server/src/twobrain_rec_server/db/migrations/data/0030_meeting_target_registry.json"
                )
        )
        let document = try MeetingDetectionCoding.decoder().decode(
            MeetingTargetRegistryDocument.self,
            from: data
        )
        try MeetingTargetRegistryValidator.validate(document)
        let nativeTargets = document.targets.filter {
            $0.platform == .macos && $0.targetFamily == .nativeApp && !$0.nativeBundleIds.isEmpty
        }
        let bundleIDs = nativeTargets.flatMap(\.nativeBundleIds)

        XCTAssertEqual(nativeTargets.count, 79)
        XCTAssertTrue(nativeTargets.allSatisfy { $0.mode == .promptEnabled })
        XCTAssertEqual(Set(bundleIDs.map { $0.lowercased() }).count, 87)
        XCTAssertEqual(document.target(forBundleID: "COM.TDESKTOP.TELEGRAM")?.id, "telegram_desktop")
    }

    func testUnsafeBrowserTargetWithoutJoinIntentFailsClosed() throws {
        let document = MeetingTargetRegistryDocument(
            registryVersion: "2026.07.08.1",
            generatedAt: Date(timeIntervalSince1970: 1_779_887_120),
            targets: [
                MeetingTargetRegistryTarget(
                    id: "unsafe_browser",
                    displayName: "Unsafe Browser",
                    market: .global,
                    platform: .browser,
                    targetFamily: .browserMeeting,
                    mode: .promptEnabled,
                    evidence: .seed,
                    requiredSignals: [.browserMetadata],
                    browserServicePatterns: [
                        MeetingTargetBrowserServicePattern(
                            serviceFamily: "google_meet",
                            hostCategory: "first_party",
                            patternClass: "meeting_room"
                        )
                    ]
                )
            ]
        )

        XCTAssertThrowsError(try MeetingTargetRegistryValidator.validate(document)) { error in
            XCTAssertEqual(error as? MeetingTargetRegistryError, .unsafeBrowserTarget("unsafe_browser"))
        }
    }

    func testOldSensorSignalIsRejected() {
        XCTAssertThrowsError(
            try MeetingDetectionCoding.decoder().decode(
                MeetingTargetRegistryDocument.self,
                from: Self.seedRegistryData(requiredSignal: "macos_sensor_indicators_mic")
            )
        )
    }

    func testDesktopAppRefreshesRemoteRegistryPeriodicallyAndAfterWake() throws {
        let source = try Self.desktopAppSource()

        XCTAssertTrue(source.contains("meetingDetectionRegistryRefreshIntervalNanoseconds"))
        XCTAssertTrue(source.contains("refreshMeetingDetectionRegistry(reason: \"periodic_registry_refresh\")"))
        XCTAssertTrue(source.contains("refreshMeetingDetectionRegistry(reason: \"system_wake\")"))
        XCTAssertTrue(source.contains("client.fetchMeetingDetectionTargetRegistry(ifNoneMatch: etag)"))
        XCTAssertTrue(source.contains(".twoBrainRecMeetingTargetRegistryDidChange"))
    }

    func testDesktopAppStartupDoesNotRequireLocalRegistryBeforeRemoteFetch() throws {
        let source = try Self.desktopAppSource()
        let body = try Self.functionBody(
            named: "startMeetingDetectionIfNeeded",
            before: "private func stopMeetingDetection()",
            in: source
        )

        XCTAssertTrue(body.contains("try? resolveMeetingDetectionRegistry(remoteData: nil, remoteETag: nil)"))
        XCTAssertTrue(body.contains("event: \"meeting_detection.registry_cache_unavailable\""))
        XCTAssertTrue(body.contains("detail: \"awaitingRemote=true\""))
        XCTAssertTrue(body.contains("await refreshMeetingDetectionRegistry(reason: \"startup\")"))
        XCTAssertFalse(body.contains("try resolveMeetingDetectionRegistry(remoteData: nil, remoteETag: nil)"))
        XCTAssertFalse(body.contains("Проверьте локальный реестр приложений"))
    }

    func testRegistryFetchBypassesFoundationHTTPCache() throws {
        let source = try Self.desktopUploadClientSource()
        let body = try Self.functionBody(
            named: "fetchMeetingDetectionTargetRegistry",
            before: "public func acknowledgeLocalPurgeTask",
            in: source
        )

        XCTAssertTrue(body.contains("request.cachePolicy = .reloadIgnoringLocalCacheData"))
    }

    private func temporaryRoot() -> URL {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meeting-target-registry-\(UUID().uuidString)", isDirectory: true)
        try? FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        return root
    }

    static func seedRegistryData(
        registryVersion: String = "2026.07.08.1",
        requiredSignal: String = "macos_audio_hal_assertion"
    ) -> Data {
        Data(
            """
            {
              "schemaVersion": 1,
              "registryVersion": "\(registryVersion)",
              "generatedAt": "2026-07-08T00:00:00Z",
              "targets": [
                {
                  "id": "zoom",
                  "displayName": "Zoom",
                  "market": "global",
                  "platform": "macos",
                  "targetFamily": "native_app",
                  "nativeBundleIds": ["us.zoom.xos"],
                  "mode": "prompt_enabled",
                  "evidence": "runtime_verified",
                  "requiredSignals": ["\(requiredSignal)"]
                },
                {
                  "id": "yandex_telemost",
                  "displayName": "Yandex Telemost",
                  "market": "russia",
                  "platform": "macos",
                  "targetFamily": "native_app",
                  "nativeBundleIds": ["ru.yandex.desktop.telemost"],
                  "mode": "prompt_enabled",
                  "evidence": "runtime_verified",
                  "requiredSignals": ["\(requiredSignal)"]
                }
              ]
            }
            """.utf8
        )
    }

    static func promptTarget() -> MeetingTargetRegistryTarget {
        MeetingTargetRegistryTarget(
            id: "zoom",
            displayName: "Zoom",
            market: .global,
            platform: .macos,
            targetFamily: .nativeApp,
            mode: .promptEnabled,
            evidence: .runtimeVerified,
            requiredSignals: [.macOSAudioHALAssertion],
            nativeBundleIds: ["us.zoom.xos"]
        )
    }

    static func unsafePromptRegistryData() -> Data {
        Data(
            """
            {
              "schemaVersion": 1,
              "registryVersion": "2026.07.09.2",
              "generatedAt": "2026-07-08T00:00:00Z",
              "targets": [
                {
                  "id": "unsafe_zoom",
                  "displayName": "Unsafe Zoom",
                  "market": "global",
                  "platform": "macos",
                  "targetFamily": "native_app",
                  "nativeBundleIds": [],
                  "mode": "prompt_enabled",
                  "evidence": "seed",
                  "requiredSignals": ["macos_audio_hal_assertion"]
                }
              ]
            }
            """.utf8
        )
    }

    private static func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != "/" {
            let appSourceURL = candidate.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift")
            if FileManager.default.fileExists(atPath: appSourceURL.path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw NSError(
            domain: "MeetingTargetRegistryTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
        )
    }

    private static func desktopAppSource() throws -> String {
        try String(
            contentsOf: repositoryRoot()
                .appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"),
            encoding: .utf8
        )
    }

    private static func desktopUploadClientSource() throws -> String {
        try String(
            contentsOf: repositoryRoot()
                .appendingPathComponent("apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift"),
            encoding: .utf8
        )
    }

    private static func functionBody(named name: String, before endMarker: String, in source: String) throws -> String {
        guard let start = source.range(of: "func \(name)"),
              let end = source[start.lowerBound...].range(of: endMarker)
        else {
            throw NSError(
                domain: "MeetingTargetRegistryTests",
                code: 2,
                userInfo: [NSLocalizedDescriptionKey: "Function \(name) not found"]
            )
        }
        return String(source[start.lowerBound..<end.lowerBound])
    }
}

private extension MeetingTargetRegistryDocument {
    func validatedForTest() throws -> MeetingTargetRegistryDocument {
        try MeetingTargetRegistryValidator.validate(self)
        return self
    }
}
#endif
