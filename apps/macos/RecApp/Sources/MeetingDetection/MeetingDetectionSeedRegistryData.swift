import Foundation

public enum MeetingDetectionSeedRegistryData {
    public static func load() throws -> Data {
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
