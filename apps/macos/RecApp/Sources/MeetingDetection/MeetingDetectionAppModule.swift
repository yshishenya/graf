import Foundation
import TwoBrainRecShared

public enum MeetingDetectionAppModule {
    public static let applicationSupportDirectoryName = "MeetingDetection"

    public static func applicationSupportDirectory(
        fileManager: FileManager = .default
    ) -> URL {
        let base = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ??
            fileManager.temporaryDirectory
        return base
            .appendingPathComponent("GRAF", isDirectory: true)
            .appendingPathComponent(applicationSupportDirectoryName, isDirectory: true)
    }

    public static func settingsURL(fileManager: FileManager = .default) -> URL {
        applicationSupportDirectory(fileManager: fileManager)
            .appendingPathComponent("settings.json")
    }

    public static func targetRegistryCacheURL(fileManager: FileManager = .default) -> URL {
        applicationSupportDirectory(fileManager: fileManager)
            .appendingPathComponent("target-registry-cache.json")
    }

    public static func telemetryUploaderStateURL(fileManager: FileManager = .default) -> URL {
        applicationSupportDirectory(fileManager: fileManager)
            .appendingPathComponent("telemetry-uploader-state.json")
    }
}
