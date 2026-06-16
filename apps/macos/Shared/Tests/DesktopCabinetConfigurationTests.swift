import Foundation
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class DesktopCabinetConfigurationTests: XCTestCase {
    func testConfigurationAcceptsHttpOriginsAndBuildsDesktopRoutes() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev/base/",
            headers: ["X-Workspace-Id": "workspace-033"]
        ))

        XCTAssertEqual(configuration.meetingsURL().absoluteString, "https://rec.2brain.dev/desktop/meetings")
        XCTAssertEqual(
            configuration.meetingDetailURL(meetingId: "meeting-033").absoluteString,
            "https://rec.2brain.dev/desktop/meetings/meeting-033"
        )
        XCTAssertEqual(configuration.workspaceId, "workspace-033")
    }

    func testConfigurationRejectsNonHTTPOrigins() {
        XCTAssertNil(DesktopCabinetConfiguration(rawBaseURL: "file:///tmp/cabinet", headers: [:]))
        XCTAssertNil(DesktopCabinetConfiguration(rawBaseURL: "ftp://rec.2brain.dev", headers: [:]))
        XCTAssertNil(DesktopCabinetConfiguration(rawBaseURL: "not a url", headers: [:]))
    }

    func testConfiguredHeadersReuseDesktopMetadataAndRedactSecretValues() {
        let headers = DesktopCabinetConfiguration.configuredHeaders(from: [
            "TWO_BRAIN_REC_CLIENT_VERSION": "desktop-033",
            "TWO_BRAIN_REC_USER_ID": "user-033",
            "TWO_BRAIN_REC_WORKSPACE_ID": "workspace-033",
            "TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN": "secret-token"
        ])

        XCTAssertEqual(headers["X-Client-Version"], "desktop-033")
        XCTAssertEqual(headers["X-User-Id"], "user-033")
        XCTAssertEqual(headers["X-Workspace-Id"], "workspace-033")
        XCTAssertEqual(headers["Authorization"], "Bearer secret-token")
        XCTAssertEqual(
            DesktopCabinetConfiguration.sanitizedHeaderPreview(headers),
            [
                "Authorization": "<redacted>",
                "X-Client-Version": "desktop-033",
                "X-User-Id": "user-033",
                "X-Workspace-Id": "workspace-033"
            ]
        )
    }

    func testUnavailableMessagesDoNotExposeSecretsOrLivePaths() {
        let message = DesktopCabinetState.expiredSession.userMessage

        XCTAssertFalse(message.contains("/Users/"))
        XCTAssertFalse(message.localizedCaseInsensitiveContains("token"))
        XCTAssertFalse(message.localizedCaseInsensitiveContains("bearer"))
        XCTAssertTrue(message.localizedCaseInsensitiveContains("войдите"))
    }

    func testAllCabinetStateMessagesStayMetadataOnly() {
        let forbiddenFragments = [
            "/Users/",
            "file://",
            "token",
            "bearer",
            "cookie",
            "signed url",
            "presigned",
            ".wav",
            "transcript:",
            "krisp"
        ]

        for state in DesktopCabinetState.allCases {
            for fragment in forbiddenFragments {
                XCTAssertFalse(
                    state.userMessage.localizedCaseInsensitiveContains(fragment),
                    "\(state) leaked \(fragment)"
                )
            }
        }
    }
}
#endif
