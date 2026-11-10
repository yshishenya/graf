import Foundation
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

final class InterfacePerformanceContractTests: XCTestCase {
    private final class CountingInputProvider: RecordingMicrophoneInputProviding, @unchecked Sendable {
        private let lock = NSLock()
        private var count = 0

        var callCount: Int {
            lock.lock(); defer { lock.unlock() }
            return count
        }

        func availableInputs() -> [PhysicalAudioDevice] {
            lock.lock(); count += 1; lock.unlock()
            return []
        }

        func defaultInputDevice() -> PhysicalAudioDevice? { nil }
        func inputDevice(id _: String) -> PhysicalAudioDevice? { nil }
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

    private func repositoryRoot() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }
}
