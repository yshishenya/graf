import Foundation

public enum MacArchitecture: String, Codable, Sendable {
    case appleSilicon = "apple_silicon"
    case intel
    case unknown
}

public enum PlatformSupport {
    public static let minimumSupportedMacOS = OperatingSystemVersion(
        majorVersion: 14,
        minorVersion: 5,
        patchVersion: 0
    )

    public static var currentArchitecture: MacArchitecture {
        #if arch(arm64)
        return .appleSilicon
        #elseif arch(x86_64)
        return .intel
        #else
        return .unknown
        #endif
    }

    public static func isSupported(
        operatingSystemVersion: OperatingSystemVersion = ProcessInfo.processInfo.operatingSystemVersion,
        architecture: MacArchitecture = currentArchitecture
    ) -> Bool {
        (architecture == .appleSilicon || architecture == .intel) &&
            isAtLeastMinimumMacOS(operatingSystemVersion)
    }

    public static func isAtLeastMinimumMacOS(_ version: OperatingSystemVersion) -> Bool {
        if version.majorVersion != minimumSupportedMacOS.majorVersion {
            return version.majorVersion > minimumSupportedMacOS.majorVersion
        }

        if version.minorVersion != minimumSupportedMacOS.minorVersion {
            return version.minorVersion > minimumSupportedMacOS.minorVersion
        }

        return version.patchVersion >= minimumSupportedMacOS.patchVersion
    }
}
