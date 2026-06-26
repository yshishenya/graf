import Foundation

public enum LocalCustodyFileProtection {
    public static let userOnlyPermissions = 0o600

    public static func write(_ data: Data, to url: URL) throws {
        try FileManager.default.createDirectory(
            at: url.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try data.write(to: url, options: [.atomic, .completeFileProtection])
        try apply(to: url)
    }

    @discardableResult
    public static func createEmptyFile(at url: URL) throws -> Bool {
        try FileManager.default.createDirectory(
            at: url.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        let created = FileManager.default.createFile(
            atPath: url.path,
            contents: nil,
            attributes: protectedAttributes
        )
        try apply(to: url)
        return created
    }

    public static func apply(to url: URL) throws {
        guard FileManager.default.fileExists(atPath: url.path) else { return }
        try FileManager.default.setAttributes(protectedAttributes, ofItemAtPath: url.path)
    }

    public static func isProtected(_ url: URL) -> Bool {
        guard let attributes = try? FileManager.default.attributesOfItem(atPath: url.path) else {
            return false
        }
        let protection = attributes[.protectionKey] as? String
        let permissions = (attributes[.posixPermissions] as? NSNumber)?.intValue
        return protection == FileProtectionType.complete.rawValue &&
            permissions == userOnlyPermissions
    }

    private static var protectedAttributes: [FileAttributeKey: Any] {
        [
            .protectionKey: FileProtectionType.complete,
            .posixPermissions: NSNumber(value: userOnlyPermissions)
        ]
    }
}
