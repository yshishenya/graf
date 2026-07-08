import Foundation

#if canImport(XCTest)
import XCTest

final class InstallerPackagingTests: XCTestCase {
    func testLocalInstallerPackagesSwiftPMResourceBundleForMeetingDetection() throws {
        let script = try String(
            contentsOf: Self.repositoryRoot()
                .appendingPathComponent("apps/macos/Installer/Scripts/build-local-installer.sh"),
            encoding: .utf8
        )

        XCTAssertTrue(script.contains("APP_CORE_RESOURCE_BUNDLE_NAME=\"TwoBrainRecMacOS_TwoBrainRecAppCore.bundle\""))
        XCTAssertTrue(script.contains("APP_CORE_RESOURCE_BUNDLE=\"$BIN_DIR/$APP_CORE_RESOURCE_BUNDLE_NAME\""))
        XCTAssertTrue(script.contains("meeting-target-registry.seed.json"))
        XCTAssertTrue(script.contains("cp -R \"$APP_CORE_RESOURCE_BUNDLE\" \"$APP_BUNDLE/Contents/Resources/\""))
    }

    private static func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != "/" {
            let installerScript = candidate
                .appendingPathComponent("apps/macos/Installer/Scripts/build-local-installer.sh")
            if FileManager.default.fileExists(atPath: installerScript.path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw NSError(
            domain: "InstallerPackagingTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
        )
    }
}
#endif
