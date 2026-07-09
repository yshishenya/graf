import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class InstallerLifecycleEvidenceTests: XCTestCase {
    func testInstallerLifecycleEvidenceUsesCommonResultValues() {
        let evidence = InstallerLifecycleEvidence(
            operation: "repair",
            preState: "installed",
            postState: "repaired",
            coreAudioRefreshRequired: true,
            runtimeProbeResult: "accepted",
            result: .passed
        )

        XCTAssertEqual(evidence.operation, "repair")
        XCTAssertTrue(evidence.coreAudioRefreshRequired)
        XCTAssertEqual(evidence.runtimeProbeResult, "accepted")
        XCTAssertEqual(evidence.result, .passed)
    }

    func testSkippedLifecycleOperationIsNotAccepted() {
        let evidence = InstallerLifecycleEvidence(
            operation: "uninstall",
            preState: "installed",
            postState: "unknown",
            coreAudioRefreshRequired: true,
            runtimeProbeResult: "not_run",
            result: .notAccepted
        )

        XCTAssertEqual(evidence.result, .notAccepted)
        XCTAssertEqual(evidence.runtimeProbeResult, "not_run")
    }

    func testInstallerSupportsExplicitLocalSelfSignedPermissionRetentionPath() throws {
        let source = try Self.readRepositoryFile("apps/macos/Installer/Scripts/build-local-installer.sh")

        XCTAssertTrue(source.contains("ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING"))
        XCTAssertTrue(source.contains("GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING"))
        XCTAssertTrue(source.contains("GRAF Local Code Signing"))
        XCTAssertTrue(source.contains("Using local self-signed app signing identity for local validation only"))
        XCTAssertTrue(source.contains("not Developer ID signed or notarized"))
        XCTAssertTrue(source.contains("grep -q '^Signature=adhoc'"))
        XCTAssertTrue(source.contains("grep -q '^Authority='"))
    }

    func testInstallerKeepsReleaseLikeSigningStrictByDefault() throws {
        let source = try Self.readRepositoryFile("apps/macos/Installer/Scripts/build-local-installer.sh")

        XCTAssertTrue(source.contains("Apple Development|Developer ID Application|Apple Distribution|Mac Developer"))
        XCTAssertTrue(source.contains("Use an Apple Development or Developer ID Application identity for release-like builds."))
        XCTAssertFalse(source.contains("ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=\"1\""))
        XCTAssertTrue(source.contains("GRAF_INCLUDE_DRIVER_COMPONENT:-${TWO_BRAIN_REC_INCLUDE_DRIVER_COMPONENT:-0}"))
    }

    func testInstallerDeclaresStableGrafAppIdentityAndPermissions() throws {
        let source = try Self.readRepositoryFile("apps/macos/Installer/Scripts/build-local-installer.sh")

        XCTAssertTrue(source.contains("<string>pro.2brain.graf</string>"))
        XCTAssertTrue(source.contains("<string>GRAF</string>"))
        XCTAssertTrue(source.contains("NSMicrophoneUsageDescription"))
        XCTAssertTrue(source.contains("NSScreenCaptureUsageDescription"))
        XCTAssertTrue(source.contains("pro.2brain.graf.desktop-app"))
        XCTAssertFalse(source.contains("start_selected=\"true\" start_enabled=\"true\""))
    }

    func testInstallerReadmeDocumentsLocalOnlySigningBoundary() throws {
        let readme = try Self.readRepositoryFile("apps/macos/Installer/README.md")

        XCTAssertTrue(readme.contains("Local Self-Signed Permission-Retention Builds"))
        XCTAssertTrue(readme.contains("GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1"))
        XCTAssertTrue(readme.contains("same certificate/private key pair"))
        XCTAssertTrue(readme.contains("This local self-signed path is not public release readiness"))
        XCTAssertTrue(readme.contains("Developer ID Application certificate"))
        XCTAssertTrue(readme.contains("Developer ID Installer"))
        XCTAssertTrue(readme.contains("successful notarization"))
        XCTAssertFalse(readme.localizedCaseInsensitiveContains("private key:"))
    }

    private static func readRepositoryFile(_ relativePath: String) throws -> String {
        try String(
            contentsOf: repositoryRoot().appendingPathComponent(relativePath),
            encoding: .utf8
        )
    }

    private static func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != "/" {
            let marker = candidate.appendingPathComponent("apps/macos/Installer/Scripts/build-local-installer.sh")
            if FileManager.default.fileExists(atPath: marker.path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw NSError(
            domain: "InstallerLifecycleEvidenceTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
        )
    }
}
#endif
