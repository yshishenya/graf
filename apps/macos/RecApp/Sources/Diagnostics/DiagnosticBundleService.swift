import CryptoKit
import Foundation
import TwoBrainRecShared

public struct DiagnosticBundleInput: Sendable {
    public let schemaVersion: String
    public let createdAt: Date
    public let manifest: [String: DiagnosticFieldValue]

    public init(
        schemaVersion: String,
        createdAt: Date,
        manifest: [String: DiagnosticFieldValue]
    ) {
        self.schemaVersion = schemaVersion
        self.createdAt = createdAt
        self.manifest = manifest
    }
}

public struct DiagnosticBundle: Sendable {
    public let schemaVersion: String
    public let createdAt: Date
    public let redactionState: DiagnosticRedactionStatus
    public let contentHash: String
    public let manifest: [String: DiagnosticFieldValue]
    public let removedFields: [String]
}

public struct DiagnosticBundleService: Sendable {
    private let redactor: DiagnosticRedactor

    public init(redactor: DiagnosticRedactor = DiagnosticRedactor()) {
        self.redactor = redactor
    }

    public func buildBundle(_ input: DiagnosticBundleInput) throws -> DiagnosticBundle {
        var manifest = input.manifest
        manifest["schemaVersion"] = .string(input.schemaVersion)
        manifest["createdAt"] = .string(Self.formatDate(input.createdAt))

        let redaction = redactor.redact(manifest)
        var finalizedManifest = redaction.manifest
        finalizedManifest["redactionState"] = .string(redaction.status.rawValue)
        finalizedManifest["contentHash"] = .string(try contentHash(for: finalizedManifest))

        return DiagnosticBundle(
            schemaVersion: input.schemaVersion,
            createdAt: input.createdAt,
            redactionState: redaction.status,
            contentHash: finalizedManifest.stringValue(forKey: "contentHash") ?? "",
            manifest: finalizedManifest,
            removedFields: redaction.removedFields
        )
    }

    private func contentHash(for manifest: [String: DiagnosticFieldValue]) throws -> String {
        let jsonObject = manifest.mapValues { $0.jsonCompatibleValue }
        let data = try JSONSerialization.data(
            withJSONObject: jsonObject,
            options: [.sortedKeys, .withoutEscapingSlashes]
        )
        let digest = SHA256.hash(data: data)
        return digest.map { String(format: "%02x", $0) }.joined()
    }

    private static func formatDate(_ date: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: date)
    }
}

private extension DiagnosticFieldValue {
    var jsonCompatibleValue: Any {
        switch self {
        case .string(let value):
            return value
        case .int(let value):
            return value
        case .double(let value):
            return value
        case .bool(let value):
            return value
        case .object(let object):
            return object.mapValues { $0.jsonCompatibleValue }
        case .array(let values):
            return values.map { $0.jsonCompatibleValue }
        case .null:
            return NSNull()
        }
    }
}

private extension Dictionary where Key == String, Value == DiagnosticFieldValue {
    func stringValue(forKey key: String) -> String? {
        guard case .string(let value) = self[key] else {
            return nil
        }
        return value
    }
}
