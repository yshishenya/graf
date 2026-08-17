import Foundation
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class DevChannelStorageTests: XCTestCase {
    func testChannelParsingKeepsDevExplicitAndProductionDefault() {
        XCTAssertEqual(GrafAppChannel.from(environment: [GrafAppChannel.environmentKey: "dev"]), .installedDev)
        XCTAssertEqual(GrafAppChannel.from(environment: [GrafAppChannel.environmentKey: "local"]), .disposableLocal)
        XCTAssertEqual(GrafAppChannel.from(environment: [:]), .production)
        XCTAssertEqual(
            GrafAppChannel.from(environment: [DesktopCabinetConfiguration.localAppEnvironmentKey: "1"]),
            .disposableLocal
        )
    }

    func testProductionAndDevUseDistinctStableApplicationSupportNamespaces() {
        XCTAssertEqual(GrafAppChannel.production.applicationSupportFolderName, "GRAF")
        XCTAssertEqual(GrafAppChannel.installedDev.applicationSupportFolderName, "GRAF Dev")
        XCTAssertEqual(GrafAppChannel.production.displayName, "GRAF")
        XCTAssertEqual(GrafAppChannel.installedDev.displayName, "GRAF Dev")
        XCTAssertNotEqual(
            GrafAppChannel.production.applicationSupportFolderName,
            GrafAppChannel.installedDev.applicationSupportFolderName
        )
    }

    func testDevStoragePathsDoNotOverlapProductionPaths() {
        let base = FileManager.default.temporaryDirectory
            .appendingPathComponent("graf-dev-channel-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: base) }

        let productionRecordings = LocalRecordingStore.defaultRootURL(
            applicationSupportURL: base,
            channel: .production
        )
        let devRecordings = LocalRecordingStore.defaultRootURL(
            applicationSupportURL: base,
            channel: .installedDev
        )
        let productionQueue = DesktopUploadQueueService.defaultQueueURL(
            fileManager: .default,
            applicationSupportURL: base,
            channel: .production
        )
        let devQueue = DesktopUploadQueueService.defaultQueueURL(
            fileManager: .default,
            applicationSupportURL: base,
            channel: .installedDev
        )
        let productionDetection = MeetingDetectionAppModule.applicationSupportDirectory(
            fileManager: .default,
            applicationSupportURL: base,
            channel: .production
        )
        let devDetection = MeetingDetectionAppModule.applicationSupportDirectory(
            fileManager: .default,
            applicationSupportURL: base,
            channel: .installedDev
        )

        XCTAssertNotEqual(productionRecordings.standardizedFileURL, devRecordings.standardizedFileURL)
        XCTAssertNotEqual(productionQueue.standardizedFileURL, devQueue.standardizedFileURL)
        XCTAssertNotEqual(productionDetection.standardizedFileURL, devDetection.standardizedFileURL)
        XCTAssertTrue(devRecordings.path.contains("GRAF Dev"))
        XCTAssertTrue(devQueue.path.contains("GRAF Dev"))
        XCTAssertTrue(devDetection.path.contains("GRAF Dev"))
    }
}
#endif
