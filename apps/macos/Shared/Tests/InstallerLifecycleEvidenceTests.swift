import Foundation

#if canImport(XCTest)
import XCTest

final class InstallerLifecycleEvidenceTests: XCTestCase {
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
        XCTAssertFalse(source.contains("INCLUDE_DRIVER_COMPONENT"))
        XCTAssertFalse(source.contains("AudioDriver"))
        XCTAssertFalse(source.contains("Audio/Plug-Ins/HAL"))
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

    func testInstallerEmbedsSparkleAndFailsClosedOnPartialTrustConfiguration() throws {
        let source = try Self.readRepositoryFile("apps/macos/Installer/Scripts/build-local-installer.sh")

        XCTAssertTrue(source.contains("Sparkle.xcframework/macos-arm64_x86_64/Sparkle.framework"))
        XCTAssertTrue(source.contains("Contents/Frameworks/Sparkle.framework"))
        XCTAssertTrue(source.contains("Sparkle-LICENSE.txt"))
        XCTAssertTrue(source.contains("GRAF_UPDATE_FEED_URL"))
        XCTAssertTrue(source.contains("GRAF_SPARKLE_PUBLIC_ED_KEY"))
        XCTAssertTrue(source.contains("Incomplete trusted update configuration"))
        XCTAssertTrue(source.contains("SUFeedURL"))
        XCTAssertTrue(source.contains("SUPublicEDKey"))
        XCTAssertTrue(source.contains("SURequireSignedFeed"))
        XCTAssertTrue(source.contains("SUVerifyUpdateBeforeExtraction"))
        XCTAssertTrue(source.contains("SUSignedFeedFailureExpirationInterval"))
        XCTAssertTrue(source.contains("SUScheduledCheckInterval"))
        XCTAssertTrue(source.contains("86400"))
        XCTAssertTrue(source.contains("SUEnableAutomaticChecks"))
        XCTAssertTrue(source.contains("SUAutomaticallyUpdate"))
        XCTAssertTrue(source.contains("SUAllowsAutomaticUpdates"))
        XCTAssertTrue(source.contains("SUEnableSystemProfiling"))
    }

    func testInstallerSignsNestedUpdaterCodeInsideOutWithoutDeepSigning() throws {
        let source = try Self.readRepositoryFile("apps/macos/Installer/Scripts/build-local-installer.sh")

        XCTAssertTrue(source.contains("XPCServices/Downloader.xpc"))
        XCTAssertTrue(source.contains("XPCServices/Installer.xpc"))
        XCTAssertTrue(source.contains("Updater.app"))
        XCTAssertTrue(source.contains("Autoupdate"))
        XCTAssertTrue(source.contains("--options runtime"))
        XCTAssertTrue(source.contains("--preserve-metadata=identifier,entitlements,flags"))
        XCTAssertFalse(source.contains("codesign --force --deep"))
    }

    func testUpdateValidatorChecksIdentityTrustAndPublicReleaseGatesWithoutMutatingTCC() throws {
        let source = try Self.readRepositoryFile("apps/macos/Scripts/validate-app-updates.sh")

        XCTAssertTrue(source.contains("pro.2brain.graf"))
        XCTAssertTrue(source.contains("Contents/Frameworks/Sparkle.framework"))
        XCTAssertTrue(source.contains("Sparkle license notice is missing"))
        XCTAssertTrue(source.contains("codesign --verify --deep --strict"))
        XCTAssertTrue(source.contains("codesign -R="))
        XCTAssertTrue(source.contains("Sparkle public key changed without an approved rotation"))
        XCTAssertTrue(source.contains("UPDATE_CONTINUITY=in-app"))
        XCTAssertTrue(source.contains("GRAF_REQUIRE_PUBLIC_UPDATE_TRUST"))
        XCTAssertTrue(source.contains("GRAF_REQUIRE_OWNER_ONLY_UPDATE_TRUST"))
        XCTAssertTrue(source.contains("Developer ID Application"))
        XCTAssertTrue(source.contains("owner-only update requires GRAF Local Code Signing"))
        XCTAssertTrue(source.contains("owner-only update requires designated-requirement continuity"))
        XCTAssertTrue(source.contains(#"grep -Eq 'flags=.*\(runtime\)'"#))
        XCTAssertFalse(source.contains("grep -Eq '^flags="))
        XCTAssertTrue(source.contains("xcrun stapler validate"))
        XCTAssertTrue(source.contains("spctl --assess --type execute"))
        XCTAssertTrue(source.contains("archive contains duplicate paths"))
        XCTAssertTrue(source.contains("archive contains an unexpected top-level entry"))
        XCTAssertTrue(source.contains("archive executable differs from the validated app"))
        XCTAssertTrue(source.contains("appcast release notes must contain Russian user-facing text"))
        XCTAssertTrue(source.contains("CFBundleVersion contains an invalid calendar date"))
        XCTAssertTrue(source.contains("SURequireSignedFeed"))
        XCTAssertTrue(source.contains("SUVerifyUpdateBeforeExtraction"))
        XCTAssertFalse(source.contains("tccutil reset"))
        XCTAssertFalse(source.localizedCaseInsensitiveContains("private key:"))
    }

    func testUpdatePreparationUsesOfficialToolsAndStagesWithoutPublishing() throws {
        let source = try Self.readRepositoryFile("apps/macos/Installer/Scripts/prepare-app-update.sh")

        XCTAssertTrue(source.contains("GRAF_PREVIOUS_APP_BUNDLE"))
        XCTAssertTrue(source.contains("GRAF_UPDATE_RELEASE_NOTES"))
        XCTAssertTrue(source.contains("GRAF_UPDATE_DOWNLOAD_BASE_URL"))
        XCTAssertTrue(source.contains("GRAF_SPARKLE_PRIVATE_KEY_FILE"))
        XCTAssertTrue(source.contains("GRAF_SPARKLE_KEYCHAIN_ACCOUNT"))
        XCTAssertTrue(source.contains("generate_appcast"))
        XCTAssertTrue(source.contains("generate_keys"))
        XCTAssertTrue(source.contains("sign_update"))
        XCTAssertTrue(source.contains("derive-sparkle-public-key.swift"))
        XCTAssertTrue(source.contains("does not match GRAF.app SUPublicEDKey"))
        XCTAssertTrue(source.contains("--verify"))
        XCTAssertTrue(source.contains("/bin/realpath"))
        XCTAssertTrue(source.contains("--embed-release-notes"))
        XCTAssertTrue(source.contains("validate-app-updates.sh"))
        XCTAssertTrue(source.contains("apps/macos/.build/updates"))
        XCTAssertTrue(source.contains("GRAF-$VERSION.zip"))
        XCTAssertTrue(source.contains("GRAF_VERSION must exceed every existing staged appcast version"))
        XCTAssertTrue(source.contains("cleanup_staging"))
        XCTAssertTrue(source.contains("the prior staging directory was retained when possible"))
        XCTAssertFalse(source.contains("GRAF_UPDATE_OUTPUT_DIR"))
        XCTAssertFalse(source.contains("scp "))
        XCTAssertFalse(source.contains("rsync "))
        XCTAssertFalse(source.contains("gh release"))
        XCTAssertFalse(source.localizedCaseInsensitiveContains("private key:"))
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
        XCTAssertFalse(readme.localizedCaseInsensitiveContains("driver diagnostics package"))
        XCTAssertFalse(readme.contains("GRAF_INCLUDE_DRIVER_COMPONENT"))
    }

    func testInstallerReadmeAndReleaseChecklistDocumentThePublicUpdateBoundary() throws {
        let readme = try Self.readRepositoryFile("apps/macos/Installer/README.md")
        let checklist = try Self.readRepositoryFile("qa/macos/release-candidate-checklist.md")

        XCTAssertTrue(readme.contains("one final manual `.pkg` installation"))
        XCTAssertTrue(readme.contains("GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1"))
        XCTAssertTrue(readme.contains("GRAF_PREVIOUS_APP_BUNDLE"))
        XCTAssertTrue(readme.contains("prepare-app-update.sh"))
        XCTAssertTrue(readme.contains("two sequential in-app"))
        XCTAssertTrue(readme.contains("Never use\n`tccutil reset`"))
        XCTAssertTrue(readme.contains("does not upload, publish, tag"))
        XCTAssertTrue(checklist.contains("Developer ID Application signing"))
        XCTAssertTrue(checklist.contains("signed appcast"))
        XCTAssertTrue(checklist.contains("Two sequential same-identity in-app updates"))
        XCTAssertTrue(checklist.contains("no privileged audio component"))
    }

    func testV5RollbackChecklistRequiresVerifiedBaselineWithoutLiveToggle() throws {
        let checklist = try Self.readRepositoryFile("qa/macos/release-candidate-checklist.md")

        XCTAssertTrue(checklist.contains("v2026.07.16.6"))
        XCTAssertTrue(checklist.contains("v2026.07.16.7"))
        XCTAssertTrue(checklist.contains("not a runtime switch"))
        XCTAssertTrue(checklist.contains("only through the separately approved local"))
        XCTAssertFalse(checklist.contains("v2026.07.17.3"))
    }

    func testUninstallIsAppOnlyAndDoesNotMutateCoreAudio() throws {
        let source = try Self.readRepositoryFile("apps/macos/Installer/Scripts/uninstall.sh")

        XCTAssertTrue(source.contains("/Applications/GRAF.app"))
        XCTAssertTrue(source.contains("/Applications/2brain Rec.app"))
        XCTAssertFalse(source.contains("GRAF_APP_PATH"))
        XCTAssertFalse(source.contains("GRAF_LEGACY_APP_PATH"))
        XCTAssertFalse(source.contains("Audio/Plug-Ins/HAL"))
        XCTAssertFalse(source.localizedCaseInsensitiveContains("driver"))
        XCTAssertFalse(source.contains("coreaudiod"))
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
