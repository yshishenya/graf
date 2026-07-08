import Foundation

public enum MeetingDetectionSeedRegistryData {
    public static func load() throws -> Data {
        let packagedBundleName = "TwoBrainRecMacOS_TwoBrainRecAppCore.bundle"
        let packagedBundleURL = Bundle.main.bundleURL
            .appendingPathComponent("Contents", isDirectory: true)
            .appendingPathComponent("Resources", isDirectory: true)
            .appendingPathComponent(packagedBundleName, isDirectory: true)
        if let resourceURL = Bundle(url: packagedBundleURL)?.url(
            forResource: "meeting-target-registry.seed",
            withExtension: "json",
            subdirectory: "Resources"
        ) {
            return try Data(contentsOf: resourceURL)
        }
        if let resourceURL = Bundle.module.url(
            forResource: "meeting-target-registry.seed",
            withExtension: "json",
            subdirectory: "Resources"
        ) {
            return try Data(contentsOf: resourceURL)
        }
        let checkoutURL = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Resources/meeting-target-registry.seed.json")
        return try Data(contentsOf: checkoutURL)
    }
}
