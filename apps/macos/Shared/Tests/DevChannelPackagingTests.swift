import Foundation

#if canImport(XCTest)
import XCTest

final class DevChannelPackagingTests: XCTestCase {
    func testDevBuilderDeclaresStableLoopbackAndNoProductionUpdater() throws {
        let source = try Self.readRepositoryFile("apps/macos/Scripts/build-dev-app.sh")

        XCTAssertTrue(source.contains("GRAF Dev"))
        XCTAssertTrue(source.contains("pro.2brain.graf.dev"))
        XCTAssertTrue(source.contains("GRAF_DEV_ORIGIN"))
        XCTAssertTrue(source.contains("127.0.0.1"))
        XCTAssertTrue(source.contains("<key>LSEnvironment</key>"))
        XCTAssertTrue(source.contains("<key>GRAF_APP_CHANNEL</key>"))
        XCTAssertTrue(source.contains("<string>dev</string>"))
        XCTAssertTrue(source.contains("<string>GRAF</string>"))
        XCTAssertFalse(source.contains("GRAF-dev"))
        XCTAssertTrue(source.contains("GRAF Local Code Signing"))
        XCTAssertTrue(source.contains("--identifier \"$DEV_BUNDLE_ID\""))
        XCTAssertTrue(source.contains("render-dev-icon.swift"))
        XCTAssertTrue(source.contains("iconutil"))
        XCTAssertTrue(source.contains("DEV"))
        XCTAssertTrue(source.contains("CFBundleExecutable"))
        XCTAssertTrue(source.contains("NSMicrophoneUsageDescription"))
        XCTAssertTrue(source.contains("NSScreenCaptureUsageDescription"))
        XCTAssertTrue(source.contains("APP_BUNDLE/Contents/MacOS/GRAF"))
        XCTAssertTrue(source.contains("com.apple.security.cs.disable-library-validation"))
        XCTAssertTrue(source.contains("SUFeedURL"))
        XCTAssertTrue(source.contains("SUPublicEDKey"))
        XCTAssertTrue(source.contains("must be absent"))
    }

    func testDevInstallerIsAtomicAndDoesNotTouchProduction() throws {
        let source = try Self.readRepositoryFile("apps/macos/Scripts/install-dev-app.sh")

        XCTAssertTrue(source.contains("/Applications/GRAF Dev.app"))
        XCTAssertTrue(source.contains("mktemp"))
        XCTAssertTrue(source.contains("mv"))
        XCTAssertTrue(source.contains("pro.2brain.graf.dev"))
        XCTAssertTrue(source.contains("GRAF Dev"))
        XCTAssertTrue(source.contains("GRAF.app"))
        XCTAssertTrue(source.contains("codesign --verify --deep --strict"))
        XCTAssertTrue(source.contains("designated_requirement"))
        XCTAssertTrue(source.contains("CFBundleExecutable"))
        XCTAssertTrue(source.contains("native GRAF"))
        XCTAssertTrue(source.contains("shell launcher cannot own"))
        XCTAssertTrue(source.contains("LSEnvironment.GRAF_APP_CHANNEL"))
        XCTAssertTrue(source.contains("Dev app is running; use dev-harness promote or rollback"))
        XCTAssertTrue(source.contains("lsregister"))
    }

    func testDevLifecycleUsesNativeApplicationTermination() throws {
        let source = try Self.readRepositoryFile("apps/macos/Scripts/dev-app-lifecycle.swift")

        XCTAssertTrue(source.contains("NSWorkspace.shared.runningApplications"))
        XCTAssertTrue(source.contains("terminate()"))
        XCTAssertTrue(source.contains("bundleURL"))
        XCTAssertFalse(source.localizedCaseInsensitiveContains("kill("))
        XCTAssertFalse(source.localizedCaseInsensitiveContains("osascript"))
    }

    func testDevScriptsFailClosedWithoutTCCWorkaroundsOrExternalOrigins() throws {
        let builder = try Self.readRepositoryFile("apps/macos/Scripts/build-dev-app.sh")
        let installer = try Self.readRepositoryFile("apps/macos/Scripts/install-dev-app.sh")
        let combined = builder + "\n" + installer

        XCTAssertFalse(combined.localizedCaseInsensitiveContains("tccutil reset"))
        XCTAssertFalse(combined.localizedCaseInsensitiveContains("Audio/Plug-Ins/HAL"))
        XCTAssertTrue(combined.contains("GRAF_DEV_ORIGIN must be explicitly supplied"))
        XCTAssertTrue(combined.contains("loopback HTTP"))
        XCTAssertTrue(combined.contains("Refusing production origin"))
        XCTAssertTrue(combined.contains("signing identity is unavailable"))
    }

    private static func readRepositoryFile(_ relativePath: String) throws -> String {
        try String(contentsOf: repositoryRoot().appendingPathComponent(relativePath), encoding: .utf8)
    }

    private static func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != "/" {
            if FileManager.default.fileExists(atPath: candidate.appendingPathComponent("apps/macos/Package.swift").path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw NSError(
            domain: "DevChannelPackagingTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
        )
    }
}
#endif
