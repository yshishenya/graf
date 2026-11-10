import AppKit
import SwiftUI
import XCTest
@testable import TwoBrainRecAppCore

final class DesktopDesignTokenContractTests: XCTestCase {
    func testCoreNativePaletteMatchesCabinetCSS() throws {
        let css = try readCSS()
        let dark = try variables(in: css, selector: ":root")
        let light = try variables(in: css, selector: "html[data-theme=\"light\"]")

        let pairs: [(String, Color, String)] = [
            ("bg", DesktopDesignTokens.background, "background"),
            ("panel", DesktopDesignTokens.panel, "panel"),
            ("surface", DesktopDesignTokens.surface, "surface"),
            ("surface-2", DesktopDesignTokens.surface2, "surface2"),
            ("surface-3", DesktopDesignTokens.surface3, "surface3"),
            ("line", DesktopDesignTokens.line, "line"),
            ("text", DesktopDesignTokens.text, "text"),
            ("muted", DesktopDesignTokens.muted, "muted"),
            ("accent", DesktopDesignTokens.accent, "accent"),
            ("accent-solid", DesktopDesignTokens.accentSolid, "accentSolid"),
            ("green", DesktopDesignTokens.green, "green"),
            ("amber", DesktopDesignTokens.amber, "amber"),
            ("red", DesktopDesignTokens.red, "red")
        ]

        for (cssName, color, label) in pairs {
            let darkHex = try XCTUnwrap(dark[cssName], "missing dark --\(cssName)")
            let lightHex = try XCTUnwrap(light[cssName], "missing light --\(cssName)")
            try assertColor(color, darkHex: darkHex, lightHex: lightHex, label: label)
        }
    }

    private func readCSS() throws -> String {
        let root = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        return try String(
            contentsOf: root.appendingPathComponent(
                "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
            ),
            encoding: .utf8
        )
    }

    private func variables(in css: String, selector: String) throws -> [String: String] {
        let escaped = NSRegularExpression.escapedPattern(for: selector)
        let regex = try NSRegularExpression(pattern: "(?m)^\(escaped)\\s*\\{([^}]*)\\}")
        let range = NSRange(css.startIndex..<css.endIndex, in: css)
        guard let match = regex.firstMatch(in: css, range: range),
              let bodyRange = Range(match.range(at: 1), in: css) else {
            throw NSError(domain: "DesktopDesignTokenContractTests", code: 1)
        }
        var result: [String: String] = [:]
        for line in css[bodyRange].split(separator: ";") {
            let parts = line.split(separator: ":", maxSplits: 1).map {
                $0.trimmingCharacters(in: .whitespacesAndNewlines)
            }
            guard parts.count == 2, parts[0].hasPrefix("--") else { continue }
            result[String(parts[0].dropFirst(2))] = parts[1]
        }
        return result
    }

    private func assertColor(_ color: Color, darkHex: String, lightHex: String, label: String) throws {
        let dark = try resolve(color, appearance: .darkAqua)
        let light = try resolve(color, appearance: .aqua)
        assertComponents(dark, hex: try XCTUnwrap(UInt32(darkHex.dropFirst(), radix: 16)), label: "\(label) dark")
        assertComponents(light, hex: try XCTUnwrap(UInt32(lightHex.dropFirst(), radix: 16)), label: "\(label) light")
    }

    private func resolve(_ color: Color, appearance name: NSAppearance.Name) throws -> NSColor {
        let appearance = try XCTUnwrap(NSAppearance(named: name))
        var resolved: NSColor?
        appearance.performAsCurrentDrawingAppearance {
            resolved = NSColor(color).usingColorSpace(.sRGB)
        }
        return try XCTUnwrap(resolved)
    }

    private func assertComponents(_ color: NSColor, hex: UInt32, label: String) {
        let tolerance: CGFloat = 1.0 / 255.0
        XCTAssertEqual(color.redComponent, CGFloat((hex >> 16) & 0xFF) / 255, accuracy: tolerance, "\(label) red")
        XCTAssertEqual(color.greenComponent, CGFloat((hex >> 8) & 0xFF) / 255, accuracy: tolerance, "\(label) green")
        XCTAssertEqual(color.blueComponent, CGFloat(hex & 0xFF) / 255, accuracy: tolerance, "\(label) blue")
    }
}
