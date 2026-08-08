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
        XCTAssertTrue(script.contains("cp -R \"$APP_CORE_RESOURCE_BUNDLE\" \"$APP_BUNDLE/Contents/Resources/\""))
    }

    func testLocalInstallerDefinesExactlyOneDesktopComponent() throws {
        let script = try String(
            contentsOf: Self.repositoryRoot()
                .appendingPathComponent("apps/macos/Installer/Scripts/build-local-installer.sh"),
            encoding: .utf8
        )

        XCTAssertTrue(script.contains("$COMPONENT_DIR/graf-desktop-app.pkg"))
        XCTAssertTrue(script.contains("<line choice=\"desktop-app\"/>"))
        XCTAssertTrue(script.contains("<pkg-ref id=\"pro.2brain.graf.desktop-app\""))
        XCTAssertFalse(script.contains("INCLUDE_DRIVER_COMPONENT"))
        XCTAssertFalse(script.contains("AudioDriver"))
        XCTAssertFalse(script.contains("Audio/Plug-Ins/HAL"))
        XCTAssertFalse(script.contains("audio-driver"))
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
