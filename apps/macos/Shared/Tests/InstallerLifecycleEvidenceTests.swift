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
        XCTAssertTrue(source.contains("UpdateSigningKey.json"))
        XCTAssertTrue(source.contains("release-signing-common.sh"))
        XCTAssertTrue(source.contains("cannot override trust"))
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

    func testTeamlessSigningDisablesLibraryValidationForEmbeddedSparkle() throws {
        let installer = try Self.readRepositoryFile("apps/macos/Installer/Scripts/build-local-installer.sh")
        let validator = try Self.readRepositoryFile("apps/macos/Scripts/validate-app-updates.sh")

        XCTAssertTrue(installer.contains("com.apple.security.cs.disable-library-validation"))
        XCTAssertTrue(installer.contains(#"--entitlements "$APP_ENTITLEMENTS""#))
        XCTAssertTrue(installer.contains("TeamIdentifier"))
        XCTAssertTrue(validator.contains("teamless signing requires disabled library validation"))
        XCTAssertTrue(validator.contains("team-identified signing must keep library validation enabled"))
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
        XCTAssertTrue(source.contains("legacy arbitrary private-file input is forbidden"))
        XCTAssertTrue(source.contains("legacy Keychain-account override is forbidden"))
        XCTAssertTrue(source.contains("release_signing_select_signer"))
        XCTAssertTrue(source.contains("UpdateSigningKey.json"))
        XCTAssertTrue(source.contains("release-signing-common.sh"))
        XCTAssertTrue(source.contains("generate_appcast"))
        XCTAssertTrue(source.contains("generate_keys"))
        XCTAssertTrue(source.contains("sign_update"))
        XCTAssertTrue(source.contains("derive-sparkle-public-key.swift"))
        XCTAssertTrue(source.contains("GRAF.app SUPublicEDKey"))
        XCTAssertTrue(source.contains("--verify"))
        XCTAssertTrue(source.contains("ephemeral-ci"))
        XCTAssertTrue(source.contains("--embed-release-notes"))
        XCTAssertTrue(source.contains("validate-app-updates.sh"))
        XCTAssertTrue(source.contains("apps/macos/.build/updates"))
        XCTAssertTrue(source.contains("GRAF-$VERSION.zip"))
        XCTAssertTrue(source.contains("GRAF_VERSION must exceed every existing staged appcast version"))
        XCTAssertTrue(source.contains(".graf-update-staging.lock"))
        XCTAssertTrue(source.contains("another release staging attempt is already in progress"))
        XCTAssertTrue(source.contains("cleanup_staging"))
        XCTAssertTrue(source.contains("the prior staging directory was retained when possible"))
        XCTAssertFalse(source.contains("GRAF_UPDATE_OUTPUT_DIR"))
        XCTAssertFalse(source.contains("scp "))
        XCTAssertFalse(source.contains("rsync "))
        XCTAssertFalse(source.contains("gh release"))
        XCTAssertFalse(source.localizedCaseInsensitiveContains("private key:"))
    }

    func testReleaseSigningManifestIsPublicOnlyBeforeOrAfterApprovedEnrollment() throws {
        let manifestURL = try Self.repositoryRoot()
            .appendingPathComponent("apps/macos/Installer/UpdateSigningKey.json")
        let data = try Data(contentsOf: manifestURL)
        let manifest = try XCTUnwrap(
            try JSONSerialization.jsonObject(with: data) as? [String: Any]
        )

        XCTAssertEqual(manifest["schemaVersion"] as? Int, 1)
        let status = try XCTUnwrap(manifest["status"] as? String)
        XCTAssertTrue(["unprovisioned", "active"].contains(status))
        let trustGeneration = try XCTUnwrap(manifest["trustGeneration"] as? Int)
        if status == "unprovisioned" {
            XCTAssertEqual(trustGeneration, 0)
            XCTAssertNil(manifest["keyId"] as? String)
            XCTAssertNil(manifest["publicKey"] as? String)
        } else {
            XCTAssertGreaterThan(trustGeneration, 0)
            let keyID = try XCTUnwrap(manifest["keyId"] as? String)
            XCTAssertNotNil(keyID.range(of: #"^sha256:[0-9a-f]{64}$"#, options: .regularExpression))
            let publicKey = try XCTUnwrap(manifest["publicKey"] as? String)
            XCTAssertEqual(Data(base64Encoded: publicKey)?.count, 32)
        }

        let channels = try XCTUnwrap(manifest["channels"] as? [String: Any])
        let primary = try XCTUnwrap(channels["primary"] as? [String: String])
        let recovery = try XCTUnwrap(channels["recovery"] as? [String: String])
        XCTAssertEqual(primary["kind"], "github-environment")
        XCTAssertEqual(primary["environment"], "graf-release-signing")
        XCTAssertEqual(recovery["kind"], "macos-keychain")
        XCTAssertEqual(recovery["account"], "graf-release-signing")
    }

    func testReleaseSigningCommonHelperFailsClosedForManifestAndEphemeralInputs() throws {
        let source = try Self.readRepositoryFile("apps/macos/Installer/Scripts/release-signing-common.sh")
        let provisioner = try Self.readRepositoryFile("apps/macos/Installer/Scripts/provision-release-signing-custody.sh")

        XCTAssertTrue(source.contains("release_signing_require_active_manifest"))
        XCTAssertTrue(source.contains("public signing manifest is not active"))
        XCTAssertTrue(source.contains("key identifier does not match its public key"))
        XCTAssertTrue(source.contains("legacy arbitrary private-file input is forbidden"))
        XCTAssertTrue(source.contains("GRAF_RELEASE_SIGNING_MODE must be keychain or ephemeral-ci"))
        XCTAssertTrue(source.contains("ephemeral CI signing is restricted to GitHub Actions"))
        XCTAssertTrue(source.contains("ephemeral CI key file permissions must be 0600"))
        XCTAssertTrue(source.contains("outside the runner temporary directory"))
        XCTAssertTrue(source.contains("[ ! -L \"$candidate\" ]"))
        XCTAssertTrue(source.contains("safe signing attestation does not bind the requested release"))
        XCTAssertTrue(source.contains("safe signing attestation does not bind the requested commit"))
        XCTAssertTrue(source.contains("safe signing attestation is older than 24 hours"))
        XCTAssertTrue(source.contains("release_signing_require_keychain_attestation"))
        XCTAssertTrue(source.contains("safe Keychain attestation does not bind the requested commit"))
        let prepare = try Self.readRepositoryFile("apps/macos/Installer/Scripts/prepare-app-update.sh")
        XCTAssertTrue(prepare.contains("explicitly approved Keychain fallback"))
        XCTAssertTrue(prepare.contains("GRAF_RELEASE_SIGNING_DEGRADED_APPROVAL_ID"))
        XCTAssertFalse(source.localizedCaseInsensitiveContains("private key:"))
        XCTAssertTrue(provisioner.contains("mktemp -d"))
        XCTAssertTrue(provisioner.contains("TRANSFER_FILE=\"$TRANSFER_DIRECTORY/signing-key\""))
        XCTAssertTrue(provisioner.contains("rm -rf \"$TRANSFER_DIRECTORY\""))
        XCTAssertTrue(provisioner.contains("--resume is an explicit owner-only recovery"))
        let custodyHarness = try Self.readRepositoryFile("apps/macos/Installer/Scripts/test-release-signing-custody.sh")
        XCTAssertTrue(custodyHarness.contains("current source contains a probable secret literal"))
        XCTAssertTrue(custodyHarness.contains("$REPO_ROOT/.github"))
    }

    func testManualTrustBootstrapIsExplicitAndCannotWeakenOrdinaryUpdates() throws {
        let ordinary = try Self.readRepositoryFile("apps/macos/Scripts/validate-app-updates.sh")
        let bootstrapValidator = try Self.readRepositoryFile("apps/macos/Installer/Scripts/validate-manual-update-bootstrap.sh")
        let bootstrapBuilder = try Self.readRepositoryFile("apps/macos/Installer/Scripts/build-trust-bootstrap.sh")

        XCTAssertTrue(ordinary.contains("Sparkle public key changed without an approved rotation"))
        XCTAssertTrue(ordinary.contains("manual trust bootstrap requires a new public signing generation"))
        XCTAssertTrue(ordinary.contains("manual trust bootstrap cannot change the update feed URL"))
        XCTAssertTrue(bootstrapValidator.contains("GRAF_MANUAL_TRUST_BOOTSTRAP=1"))
        XCTAssertTrue(bootstrapValidator.contains("manual trust bootstrap must not receive an appcast"))
        XCTAssertTrue(bootstrapBuilder.contains("validate-manual-update-bootstrap.sh"))
        XCTAssertTrue(bootstrapBuilder.contains("appcast_staged=no"))
        XCTAssertFalse(bootstrapBuilder.contains("prepare-app-update.sh"))
    }

    func testProtectedReleaseSigningWorkflowsStayManualPinnedAndSecretSafe() throws {
        let verifier = try Self.readRepositoryFile(".github/workflows/verify-release-signing-custody.yml")
        let signer = try Self.readRepositoryFile(".github/workflows/sign-graf-app-update.yml")

        for workflow in [verifier, signer] {
            XCTAssertTrue(workflow.contains("workflow_dispatch:"))
            XCTAssertTrue(workflow.contains("if: github.ref == 'refs/heads/master'"))
            XCTAssertFalse(workflow.contains("pull_request:"))
            XCTAssertFalse(workflow.contains("set -x"))
            XCTAssertFalse(workflow.contains("scp "))
            XCTAssertFalse(workflow.contains("rsync "))
        }
        XCTAssertTrue(verifier.contains("graf-release-signing-test"))
        XCTAssertTrue(verifier.contains("graf-release-signing"))
        XCTAssertTrue(verifier.contains("actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5"))
        XCTAssertTrue(verifier.contains("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"))
        XCTAssertTrue(verifier.contains("chmod 600"))
        XCTAssertTrue(verifier.contains("rm -f \"$KEY_FILE\""))
        XCTAssertTrue(verifier.contains("\"channel\": \"github-environment\""))
        XCTAssertTrue(verifier.contains("\"state\": \"ready\""))
        XCTAssertTrue(verifier.contains("\"checkedAt\": \"$CHECKED_AT\""))
        XCTAssertTrue(signer.contains("concurrency:"))
        XCTAssertTrue(signer.contains("cancel-in-progress: false"))
        XCTAssertTrue(signer.contains("GRAF_RELEASE_SIGNING_MODE=ephemeral-ci"))
        XCTAssertTrue(signer.contains("GRAF_RELEASE_SIGNING_ATTESTATION=\"$ATTESTATION\""))
        XCTAssertTrue(signer.contains("GRAF_RELEASE_SIGNING_KEYCHAIN_ATTESTATION=\"$KEYCHAIN_ATTESTATION\""))
        XCTAssertTrue(signer.contains("keychain_attestation_asset:"))
        XCTAssertTrue(signer.contains("name: graf-release-signing"))
        XCTAssertTrue(signer.contains("GRAF_REQUIRE_RELEASE_PROVENANCE=1"))
        XCTAssertTrue(signer.contains("gh release upload"))
        XCTAssertTrue(signer.contains("\"checkedAt\": \"$CHECKED_AT\""))
        XCTAssertFalse(signer.contains("GRAF_SPARKLE_PRIVATE_KEY_FILE"))
    }

    func testProductionUpdatePreparationRequiresCleanRemoteTaggedProvenance() throws {
        let source = try Self.readRepositoryFile("apps/macos/Installer/Scripts/prepare-app-update.sh")
        let readme = try Self.readRepositoryFile("apps/macos/Installer/README.md")
        let checklist = try Self.readRepositoryFile("qa/macos/release-candidate-checklist.md")

        XCTAssertTrue(source.contains("GRAF_REQUIRE_RELEASE_PROVENANCE"))
        XCTAssertTrue(source.contains("status --porcelain --untracked-files=all"))
        XCTAssertTrue(source.contains("refs/heads/$RELEASE_BRANCH"))
        XCTAssertTrue(source.contains("refs/tags/$RELEASE_TAG^{}"))
        XCTAssertTrue(source.contains("release provenance requires a clean worktree"))
        XCTAssertTrue(source.contains("release provenance requires HEAD to match origin/$RELEASE_BRANCH"))
        XCTAssertTrue(source.contains("release provenance requires published tag $RELEASE_TAG at HEAD"))
        XCTAssertTrue(readme.contains("GRAF_REQUIRE_RELEASE_PROVENANCE=1"))
        XCTAssertTrue(readme.contains("GitHub Release assets"))
        XCTAssertTrue(readme.contains("replace `graf-appcast.xml` last"))
        XCTAssertTrue(checklist.contains("clean commit published at the exact release tag"))
        XCTAssertTrue(checklist.contains("public SHA-256"))
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

        XCTAssertTrue(checklist.contains("v2026.07.17.6"))
        XCTAssertTrue(checklist.contains("4be444e82ec449a3bb5312920fb0cd6008072c56"))
        XCTAssertTrue(checklist.contains("v2026.07.16.7"))
        XCTAssertTrue(checklist.contains("not a runtime switch"))
        XCTAssertTrue(checklist.contains("only through the separately approved local"))
        XCTAssertFalse(checklist.contains("v2026.07.16.6"))
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
