import Foundation
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

final class InterfacePerformanceContractTests: XCTestCase {
    private final class CountingInputProvider: RecordingMicrophoneInputProviding, @unchecked Sendable {
        private let lock = NSLock()
        private var count = 0
        private var inputDeviceCalls = 0
        private let device = PhysicalAudioDevice(
            id: "mic-1",
            displayName: "Mic",
            direction: .input,
            deviceClass: .builtIn,
            availabilityState: .available
        )

        var callCount: Int {
            lock.lock(); defer { lock.unlock() }
            return count
        }

        var inputDeviceCallCount: Int {
            lock.lock(); defer { lock.unlock() }
            return inputDeviceCalls
        }

        func availableInputs() -> [PhysicalAudioDevice] {
            lock.lock(); count += 1; lock.unlock()
            return [device]
        }

        func defaultInputDevice() -> PhysicalAudioDevice? { device }
        func inputDevice(id: String) -> PhysicalAudioDevice? {
            lock.lock(); inputDeviceCalls += 1; lock.unlock()
            return id == device.id ? device : nil
        }
    }

    func testMicrophoneInputsAreCachedUntilInvalidated() {
        let provider = CountingInputProvider()
        let service = MicrophoneCaptureService(inputProvider: provider)
        _ = service.availableRecordingMicrophoneInputs()
        _ = service.availableRecordingMicrophoneInputs()
        XCTAssertEqual(provider.callCount, 1)
        service.invalidateAvailableRecordingMicrophoneInputs()
        _ = service.availableRecordingMicrophoneInputs()
        XCTAssertEqual(provider.callCount, 2)
    }

    func testMicrophoneResolutionUsesTheCachedInputList() {
        let provider = CountingInputProvider()
        let service = MicrophoneCaptureService(inputProvider: provider)
        _ = service.availableRecordingMicrophoneInputs()
        let selection = service.resolveRecordingMicrophoneSelection(selectedInputDeviceId: "mic-1")
        XCTAssertTrue(selection.isAccepted)
        XCTAssertEqual(provider.callCount, 1)
        XCTAssertEqual(provider.inputDeviceCallCount, 0)
    }

    func testContentViewDoesNotComputeLocalRowsInTheViewBuilder() throws {
        let url = repositoryRoot()
            .appendingPathComponent("apps/macos/RecApp/Sources/AppShell/ContentView.swift")
        let source = try String(contentsOf: url, encoding: .utf8)
        XCTAssertFalse(source.contains("localRecordingRows: EmbeddedCabinetLocalRecordingRow.rows("))
        XCTAssertTrue(source.contains("refreshLocalRecordingRows(for:"))
    }

    func testContentViewRenderPathHasNoDirectFileOrDeviceDiscovery() throws {
        let url = repositoryRoot()
            .appendingPathComponent("apps/macos/RecApp/Sources/AppShell/ContentView.swift")
        let source = try String(contentsOf: url, encoding: .utf8)
        XCTAssertFalse(source.contains("AVCaptureDevice.DiscoverySession"))
        XCTAssertFalse(source.contains("FileManager.default.fileExists"))
        XCTAssertTrue(source.contains("invalidateAvailableRecordingMicrophoneInputs"))
        XCTAssertFalse(source.contains("artifactProfile.totalUploadBytes"))
        XCTAssertTrue(source.contains("LocalRecordingFootprintProvider"))
        XCTAssertTrue(source.contains("refreshLocalFootprintRisk"))
    }

    func testMicrophoneDeviceChangesPublishObservedInputs() throws {
        let source = try String(
            contentsOf: repositoryRoot().appendingPathComponent("apps/macos/RecApp/Sources/AppShell/ContentView.swift"),
            encoding: .utf8
        )
        XCTAssertTrue(source.contains("@State private var recordingMicrophoneInputs"))
        XCTAssertTrue(source.contains("refreshRecordingMicrophoneInputs()"))
        XCTAssertTrue(source.contains("recordingMicrophoneInputs: recordingMicrophoneInputs"))
    }

    func testDeletionSynchronizationNeverDependsOnWindowFocus() throws {
        let source = try String(
            contentsOf: repositoryRoot().appendingPathComponent("apps/macos/RecApp/Sources/AppShell/ContentView.swift"),
            encoding: .utf8
        )
        XCTAssertFalse(source.contains("if appIsActive { await synchronizeRecordingDeletions() }"))
    }

    func testUserTimeCanFormatRepeatedlyWithoutChangingOutput() {
        let date = Date(timeIntervalSince1970: 1_800_000_000)
        let first = UserTime.format(date, timeZone: TimeZone(identifier: "Europe/Moscow") ?? .gmt)
        for _ in 0..<10 {
            XCTAssertEqual(UserTime.format(date, timeZone: TimeZone(identifier: "Europe/Moscow") ?? .gmt), first)
        }
    }

    func testCacheDryRunHasNoDeletionQueueWriteOrPlayerAPIs() throws {
        let source = try String(
            contentsOf: repositoryRoot()
                .appendingPathComponent("apps/macos/RecApp/Sources/Upload/LocalCacheEvictionDryRunService.swift"),
            encoding: .utf8
        )
        for forbidden in [
            ".loadItems(", ".loadDocumentOnQueue(", ".saveDocumentOnQueue(",
            "quarantineMalformedQueueDocument", "removeItem(", "unlink",
            "FileHandle(forWriting", ".localPlaybackURL(", ".canOpenLocalPlayback(",
        ] {
            XCTAssertFalse(source.contains(forbidden), "dry run must not use \(forbidden)")
        }
        XCTAssertTrue(source.contains("Task.detached"))
        XCTAssertTrue(source.contains("LocalCustodyFileProtection.write"))
        XCTAssertTrue(source.contains("maximumItems: Int = 200"))
        XCTAssertTrue(source.contains("maximumConcurrency: Int = 2"))
        XCTAssertTrue(source.contains("requestTimeout: TimeInterval = 5"))
        XCTAssertTrue(source.contains("totalTimeout: TimeInterval = 120"))
        XCTAssertTrue(source.contains("LocalCacheArtifactProbe"))
    }

    func testCacheDryRunIsDiagnosticsOnlyAndNotInARenderPath() throws {
        let root = repositoryRoot()
        for path in [
            "apps/macos/RecApp/Sources/AppShell/ContentView.swift",
            "apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift",
        ] {
            let source = try String(contentsOf: root.appendingPathComponent(path), encoding: .utf8)
            XCTAssertFalse(source.contains("LocalCacheEvictionDryRun"), path)
            XCTAssertFalse(source.contains("GRAF_RUN_CACHE_EVICTION_DRY_RUN"), path)
        }
        let lifecycle = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/AppShell/AppLifecycleDelegate.swift"),
            encoding: .utf8
        )
        XCTAssertTrue(lifecycle.contains("LocalCacheEvictionDryRunDiagnostics.isRequested"))
        XCTAssertTrue(lifecycle.contains("Task.detached"))
    }

    func testEligibilityPredicateIsPureAndPlayerFree() throws {
        let source = try String(
            contentsOf: repositoryRoot()
                .appendingPathComponent("apps/macos/Shared/Sources/Models/LocalCacheEligibility.swift"),
            encoding: .utf8
        )
        for forbidden in [
            "FileManager", ".localPlaybackURL(", ".canOpenLocalPlayback(", ".canProjectLocalPlayback(",
            "Task {", "Task.detached", "URL(", "Data(contentsOf",
        ] {
            XCTAssertFalse(source.contains(forbidden), "predicate must stay pure: \(forbidden)")
        }
        XCTAssertTrue(source.contains("canonical_ready"))
        XCTAssertTrue(source.contains("objectVerified"))
        XCTAssertTrue(source.contains("archiveAudio"))
        XCTAssertTrue(source.contains("retentionTooClose"))
    }

    func testLocalCacheCleanupOnlyUnlinksTheTranscriptionFile() throws {
        let source = try String(
            contentsOf: repositoryRoot()
                .appendingPathComponent("apps/macos/RecApp/Sources/Upload/LocalCacheCleanupService.swift"),
            encoding: .utf8
        )
        XCTAssertTrue(source.contains("meeting-transcription.wav"))
        XCTAssertTrue(source.contains("Darwin.unlink"))
        XCTAssertTrue(source.contains("LocalCacheFileIdentity.state"))
        XCTAssertTrue(source.contains("LocalCacheCleanupReceipt"))
        XCTAssertFalse(source.contains("reviewAudioPath"))
        XCTAssertTrue(source.contains("removeFile(atPath: transcriptionURL.path)"))
        XCTAssertFalse(source.contains("removeFile(atPath: item.reviewAudioPath)"))
        XCTAssertFalse(source.contains("removeFile(atPath: item.manifestPath)"))
        for forbidden in [
            ".loadItems(", ".loadDocumentOnQueue(", ".saveDocumentOnQueue(",
            "quarantineMalformed", "removeItem(", "requestRecordingDeletion",
            "localPlaybackURL",
        ] {
            XCTAssertFalse(source.contains(forbidden), "cleanup must not use \(forbidden)")
        }
    }

    func testLocalCacheEvictionRunsOffMainAndOutsideTheRenderPath() throws {
        let root = repositoryRoot()
        let scheduler = try String(
            contentsOf: root.appendingPathComponent(
                "apps/macos/RecApp/Sources/Upload/LocalCacheEvictionScheduler.swift"
            ),
            encoding: .utf8
        )
        XCTAssertTrue(scheduler.contains("public actor LocalCacheEvictionScheduler"))
        XCTAssertTrue(scheduler.contains("Task.detached"))
        XCTAssertTrue(scheduler.contains("nonisolated func notify"))
        XCTAssertFalse(scheduler.contains("removeItem("))

        let runtime = try String(
            contentsOf: root.appendingPathComponent(
                "apps/macos/RecApp/Sources/Upload/LocalCacheEvictionRuntime.swift"
            ),
            encoding: .utf8
        )
        XCTAssertTrue(runtime.contains("Task.detached"))
        XCTAssertTrue(runtime.contains("LocalRecordingFootprintMeasurer"))

        let content = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/AppShell/ContentView.swift"),
            encoding: .utf8
        )
        XCTAssertFalse(content.contains("LocalRecordingFootprintMeasurer"))
        XCTAssertTrue(content.contains("LocalCacheEvictionRuntime.footprintProvider"))
    }

    func testMeetingDetectionUsesTheFootprintProviderTTL() throws {
        let root = repositoryRoot()
        let content = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/AppShell/ContentView.swift"),
            encoding: .utf8
        )
        XCTAssertFalse(content.contains("<= 300"))
        XCTAssertTrue(content.contains("MeetingDetectionFootprintFreshness.freshRisk"))
        XCTAssertTrue(content.contains("Task { await refreshLocalFootprintRisk(force: true) }"))

        let usage = try String(
            contentsOf: root.appendingPathComponent(
                "apps/macos/RecApp/Sources/Buffering/LocalRecordingStorageUsage.swift"
            ),
            encoding: .utf8
        )
        XCTAssertTrue(usage.contains("defaultCacheTTL: TimeInterval = 60"))
        XCTAssertTrue(usage.contains("MeetingDetectionFootprintFreshness"))
    }

    private func repositoryRoot() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }
}
