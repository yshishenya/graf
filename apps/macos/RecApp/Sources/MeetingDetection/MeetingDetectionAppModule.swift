import Foundation
import TwoBrainRecShared

public enum MeetingDetectionAppModule {
    public static let applicationSupportDirectoryName = "MeetingDetection"

    public static var bundledTargetRegistryURL: URL? {
        if Bundle.main.bundleURL.pathExtension.lowercased() == "app" {
            return packagedTargetRegistryURL(resourceURL: Bundle.main.resourceURL)
        }
        return Bundle.module.url(
            forResource: "meeting-target-registry-baseline",
            withExtension: "json",
            subdirectory: "Resources"
        )
    }

    static func packagedTargetRegistryURL(
        resourceURL: URL?,
        fileManager: FileManager = .default
    ) -> URL? {
        guard let url = resourceURL?
            .appendingPathComponent("TwoBrainRecMacOS_TwoBrainRecAppCore.bundle", isDirectory: true)
            .appendingPathComponent("Resources", isDirectory: true)
            .appendingPathComponent("meeting-target-registry-baseline.json"),
              fileManager.fileExists(atPath: url.path) else {
            return nil
        }
        return url
    }

    public static func applicationSupportBaseURL(
        fileManager: FileManager = .default,
        applicationSupportURL: URL? = nil
    ) -> URL {
        if let applicationSupportURL {
            return applicationSupportURL
        }
        if let override = ProcessInfo.processInfo.environment["GRAF_APPLICATION_SUPPORT_DIRECTORY"],
           !override.isEmpty {
            return URL(fileURLWithPath: override, isDirectory: true)
        }
        return fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ??
            fileManager.temporaryDirectory
    }

    public static func applicationSupportDirectory(
        fileManager: FileManager = .default,
        applicationSupportURL: URL? = nil,
        channel: GrafAppChannel = .current
    ) -> URL {
        let base = applicationSupportBaseURL(
            fileManager: fileManager,
            applicationSupportURL: applicationSupportURL
        )
        return base
            .appendingPathComponent(channel.applicationSupportFolderName, isDirectory: true)
            .appendingPathComponent(applicationSupportDirectoryName, isDirectory: true)
    }

    public static func settingsURL(
        fileManager: FileManager = .default,
        applicationSupportURL: URL? = nil,
        channel: GrafAppChannel = .current
    ) -> URL {
        applicationSupportDirectory(
            fileManager: fileManager,
            applicationSupportURL: applicationSupportURL,
            channel: channel
        )
            .appendingPathComponent("settings.json")
    }

    public static func targetRegistryCacheURL(
        fileManager: FileManager = .default,
        applicationSupportURL: URL? = nil,
        channel: GrafAppChannel = .current
    ) -> URL {
        applicationSupportDirectory(
            fileManager: fileManager,
            applicationSupportURL: applicationSupportURL,
            channel: channel
        )
            .appendingPathComponent("target-registry-cache.json")
    }

    public static func telemetryUploaderStateURL(
        fileManager: FileManager = .default,
        applicationSupportURL: URL? = nil,
        channel: GrafAppChannel = .current
    ) -> URL {
        applicationSupportDirectory(
            fileManager: fileManager,
            applicationSupportURL: applicationSupportURL,
            channel: channel
        )
            .appendingPathComponent("telemetry-uploader-state.json")
    }
}
