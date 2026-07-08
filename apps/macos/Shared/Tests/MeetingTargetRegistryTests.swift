import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MeetingTargetRegistryTests: XCTestCase {
    func testPackagedSeedRegistryLoadsWhenNoRemoteOrCacheExists() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = MeetingTargetRegistryStore(
            cacheURL: root.appendingPathComponent("registry-cache.json"),
            seedData: Self.seedRegistryData()
        )

        let resolution = try store.resolve()

        XCTAssertEqual(resolution.source, .packagedSeed)
        XCTAssertEqual(resolution.document.registryVersion, "2026.07.08.1")
        XCTAssertEqual(resolution.document.target(forBundleID: "ru.yandex.desktop.telemost")?.id, "yandex_telemost")
    }

    func testValidRemoteRegistryIsCachedAndPreferred() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let cacheURL = root.appendingPathComponent("registry-cache.json")
        let store = MeetingTargetRegistryStore(cacheURL: cacheURL, seedData: Self.seedRegistryData())

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
        let store = MeetingTargetRegistryStore(cacheURL: root.appendingPathComponent("cache.json"), seedData: Self.seedRegistryData())
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

    func testPackagedSeedIncludesBrowserFoundationTargets() throws {
        let document = try MeetingDetectionCoding.decoder().decode(
            MeetingTargetRegistryDocument.self,
            from: MeetingDetectionSeedRegistryData.load()
        )
        try MeetingTargetRegistryValidator.validate(document)

        let targetIDs = Set(document.targets.map(\.id))
        XCTAssertTrue(targetIDs.contains("yandex_telemost_web"))
        XCTAssertTrue(targetIDs.contains("google_meet_web"))
    }

    private func temporaryRoot() -> URL {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meeting-target-registry-\(UUID().uuidString)", isDirectory: true)
        try? FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        return root
    }

    static func seedRegistryData(registryVersion: String = "2026.07.08.1") -> Data {
        Data(
            """
            {
              "schemaVersion": 1,
              "registryVersion": "\(registryVersion)",
              "generatedAt": "2026-07-08T00:00:00Z",
              "minimumClientVersion": "0.1.0",
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
                  "requiredSignals": ["macos_audio_hal_assertion"]
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
                  "requiredSignals": ["macos_audio_hal_assertion"]
                }
              ]
            }
            """.utf8
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
}

private extension MeetingTargetRegistryDocument {
    func validatedForTest() throws -> MeetingTargetRegistryDocument {
        try MeetingTargetRegistryValidator.validate(self)
        return self
    }
}
#endif
