import AppKit
import SwiftUI
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class DesktopDesignTokensTests: XCTestCase {
    func testColorTokensMatchTheCabinetPaletteInDarkAndLightThemes() throws {
        try assertToken(DesktopDesignTokens.background, dark: 0x17181B, light: 0xF5F6F8)
        try assertToken(DesktopDesignTokens.panel, dark: 0x1D1F23, light: 0xFFFFFF)
        try assertToken(DesktopDesignTokens.surface, dark: 0x22252A, light: 0xFFFFFF)
        try assertToken(DesktopDesignTokens.surface2, dark: 0x272A30, light: 0xF0F2F5)
        try assertToken(DesktopDesignTokens.surface3, dark: 0x30343C, light: 0xE5E8EE)
        try assertToken(DesktopDesignTokens.line, dark: 0x7E8898, light: 0x7A8494)
        try assertToken(
            DesktopDesignTokens.lineSoft,
            dark: 0xFFFFFF, light: 0x121823,
            darkAlpha: 0.10, lightAlpha: 0.13
        )
        try assertToken(DesktopDesignTokens.text, dark: 0xF0F1F4, light: 0x1D222B)
        try assertToken(DesktopDesignTokens.muted, dark: 0xADB2BC, light: 0x525B68)
        try assertToken(DesktopDesignTokens.accent, dark: 0xAB99FF, light: 0x6248D5)
        try assertToken(DesktopDesignTokens.accentSolid, dark: 0x7056E9, light: 0x6248D5)
        try assertToken(DesktopDesignTokens.accentHover, dark: 0x755CDE, light: 0x5339C5)
        try assertToken(DesktopDesignTokens.accentForeground, dark: 0xFFFFFF, light: 0xFFFFFF)
        try assertToken(DesktopDesignTokens.green, dark: 0x2FC9A6, light: 0x066E58)
        try assertToken(DesktopDesignTokens.amber, dark: 0xF0A742, light: 0x9A5B00)
        try assertToken(DesktopDesignTokens.red, dark: 0xFF6B6B, light: 0xB4232C)
        try assertToken(DesktopDesignTokens.dangerText, dark: 0xFFD6D6, light: 0x8F1D27)
        try assertToken(DesktopDesignTokens.focusRing, dark: 0xC0B6FF, light: 0x4D32CC)
        try assertToken(DesktopDesignTokens.speakerContrastText, dark: 0x151719, light: 0xFFFFFF)
    }

    func testStateTonesMatchTheCabinetTintedSurfaces() throws {
        try assertToken(
            DesktopDesignTokens.successSurface,
            dark: 0x2FC9A6, light: 0x066E58, darkAlpha: 0.09, lightAlpha: 0.09
        )
        try assertToken(
            DesktopDesignTokens.successBorder,
            dark: 0x5BA59E, light: 0x477A7A, darkAlpha: 1, lightAlpha: 1
        )
        try assertToken(
            DesktopDesignTokens.warningSurface,
            dark: 0xF0A742, light: 0x9A5B00, darkAlpha: 0.09, lightAlpha: 0.09
        )
        try assertToken(
            DesktopDesignTokens.warningBorder,
            dark: 0xB29671, light: 0x897150, darkAlpha: 1, lightAlpha: 1
        )
        try assertToken(
            DesktopDesignTokens.dangerSurface,
            dark: 0xFF6B6B, light: 0xB4232C, darkAlpha: 0.08, lightAlpha: 0.08
        )
        try assertToken(
            DesktopDesignTokens.dangerBorder,
            dark: 0xB97B83, light: 0x955764, darkAlpha: 1, lightAlpha: 1
        )
        try assertToken(
            DesktopDesignTokens.accentSurface,
            dark: 0xAB99FF, light: 0x6248D5, darkAlpha: 0.10, lightAlpha: 0.10
        )
        try assertToken(
            DesktopDesignTokens.accentBorder,
            dark: 0x918FC3, light: 0x706BAF, darkAlpha: 1, lightAlpha: 1
        )
        try assertToken(
            DesktopDesignTokens.overlayBackdrop,
            dark: 0x05070C, light: 0x05070C, darkAlpha: 0.70, lightAlpha: 0.40
        )
    }

    func testRadiusScaleMatchesTheContract() {
        XCTAssertEqual(DesktopDesignTokens.Radius.xs, 6)
        XCTAssertEqual(DesktopDesignTokens.Radius.sm, 8)
        XCTAssertEqual(DesktopDesignTokens.Radius.control, 9)
        XCTAssertEqual(DesktopDesignTokens.Radius.compact, 10)
        XCTAssertEqual(DesktopDesignTokens.Radius.card, 12)
        XCTAssertEqual(DesktopDesignTokens.Radius.panel, 14)
        XCTAssertEqual(DesktopDesignTokens.Radius.dialog, 16)
        XCTAssertEqual(DesktopDesignTokens.Radius.pill, 999)
    }

    func testFontSizeScaleMatchesTheContract() {
        XCTAssertEqual(DesktopDesignTokens.FontSize.caption, 11)
        XCTAssertEqual(DesktopDesignTokens.FontSize.helper, 12)
        XCTAssertEqual(DesktopDesignTokens.FontSize.label, 14)
        XCTAssertEqual(DesktopDesignTokens.FontSize.subtitle, 15)
        XCTAssertEqual(DesktopDesignTokens.FontSize.section, 16)
        XCTAssertEqual(DesktopDesignTokens.FontSize.headingSmall, 18)
        XCTAssertEqual(DesktopDesignTokens.FontSize.dialogTitle, 19)
        XCTAssertEqual(DesktopDesignTokens.FontSize.pageTitle, 20)
        XCTAssertEqual(DesktopDesignTokens.FontSize.headingLarge, 24)
        XCTAssertEqual(DesktopDesignTokens.FontSize.display, 28)
    }

    func testTokenModuleAvoidsTheSystemAccentColor() throws {
        let source = try Self.readRepositoryFile(
            "apps/macos/RecApp/Sources/Cabinet/DesktopDesignTokens.swift"
        )
        XCTAssertFalse(source.contains("accentColor"), "Brand colors come from the cabinet palette")
    }

    func testWebEmbeddedBackgroundTracksTheBackgroundTokenInBothThemes() throws {
        let dark = try resolve(DesktopMeetingShellChrome.webEmbeddedBackgroundNSColor, in: .darkAqua)
        let light = try resolve(DesktopMeetingShellChrome.webEmbeddedBackgroundNSColor, in: .aqua)
        assertComponents(dark, hex: 0x17181B, alpha: 1, label: "webEmbeddedBackground dark")
        assertComponents(light, hex: 0xF5F6F8, alpha: 1, label: "webEmbeddedBackground light")
    }

    private func assertToken(
        _ color: Color,
        dark: UInt32,
        light: UInt32,
        darkAlpha: CGFloat = 1,
        lightAlpha: CGFloat = 1,
        file: StaticString = #filePath,
        line: UInt = #line
    ) throws {
        let darkColor = try resolve(color, in: .darkAqua)
        let lightColor = try resolve(color, in: .aqua)
        assertComponents(darkColor, hex: dark, alpha: darkAlpha, label: "dark", file: file, line: line)
        assertComponents(lightColor, hex: light, alpha: lightAlpha, label: "light", file: file, line: line)
    }

    private func resolve(_ color: Color, in appearanceName: NSAppearance.Name) throws -> NSColor {
        try resolve(NSColor(color), in: appearanceName)
    }

    private func resolve(_ color: NSColor, in appearanceName: NSAppearance.Name) throws -> NSColor {
        let appearance = try XCTUnwrap(NSAppearance(named: appearanceName))
        var resolved: NSColor?
        appearance.performAsCurrentDrawingAppearance {
            resolved = color.usingColorSpace(.sRGB)
        }
        return try XCTUnwrap(resolved)
    }

    private func assertComponents(
        _ color: NSColor,
        hex: UInt32,
        alpha: CGFloat,
        label: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let tolerance: CGFloat = 1.0 / 255.0
        XCTAssertEqual(color.redComponent, CGFloat((hex >> 16) & 0xFF) / 255, accuracy: tolerance, "\(label) red", file: file, line: line)
        XCTAssertEqual(color.greenComponent, CGFloat((hex >> 8) & 0xFF) / 255, accuracy: tolerance, "\(label) green", file: file, line: line)
        XCTAssertEqual(color.blueComponent, CGFloat(hex & 0xFF) / 255, accuracy: tolerance, "\(label) blue", file: file, line: line)
        XCTAssertEqual(color.alphaComponent, alpha, accuracy: tolerance, "\(label) alpha", file: file, line: line)
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
            let marker = candidate.appendingPathComponent("apps/macos/Package.swift")
            if FileManager.default.fileExists(atPath: marker.path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw NSError(
            domain: "DesktopDesignTokensTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
        )
    }
}
#endif
