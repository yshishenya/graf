import AppKit
import SwiftUI

/// Единый набор оформления приложения. Значения совпадают с палитрой кабинета
/// (`cabinet.css`, тёмная и светлая темы), чтобы приложение и веб выглядели
/// одинаково. Динамические цвета следуют системному оформлению macOS.
public enum DesktopDesignTokens {
    public enum Radius {
        public static let xs: CGFloat = 6
        public static let sm: CGFloat = 8
        public static let control: CGFloat = 9
        public static let compact: CGFloat = 10
        public static let card: CGFloat = 12
        public static let panel: CGFloat = 14
        public static let dialog: CGFloat = 16
        public static let pill: CGFloat = 999
    }

    public enum FontSize {
        public static let caption: CGFloat = 11
        public static let helper: CGFloat = 12
        public static let label: CGFloat = 14
        public static let subtitle: CGFloat = 15
        public static let section: CGFloat = 16
        public static let headingSmall: CGFloat = 18
        public static let dialogTitle: CGFloat = 19
        public static let pageTitle: CGFloat = 20
        public static let headingLarge: CGFloat = 24
        public static let display: CGFloat = 28
    }

    public static let background = color(dark: 0x17181B, light: 0xF5F6F8)
    public static let panel = color(dark: 0x1D1F23, light: 0xFFFFFF)
    public static let surface = color(dark: 0x22252A, light: 0xFFFFFF)
    public static let surface2 = color(dark: 0x272A30, light: 0xF0F2F5)
    public static let surface3 = color(dark: 0x30343C, light: 0xE5E8EE)
    public static let line = color(dark: 0x7E8898, light: 0x7A8494)
    public static let lineSoft = color(dark: 0xFFFFFF, light: 0x121823, darkAlpha: 0.10, lightAlpha: 0.13)
    public static let text = color(dark: 0xF0F1F4, light: 0x1D222B)
    public static let muted = color(dark: 0xADB2BC, light: 0x525B68)
    public static let accent = color(dark: 0xAB99FF, light: 0x6248D5)
    public static let accentSolid = color(dark: 0x7056E9, light: 0x6248D5)
    public static let accentHover = color(dark: 0x755CDE, light: 0x5339C5)
    public static let accentForeground = color(dark: 0xFFFFFF, light: 0xFFFFFF)
    public static let green = color(dark: 0x2FC9A6, light: 0x066E58)
    public static let amber = color(dark: 0xF0A742, light: 0x9A5B00)
    public static let red = color(dark: 0xFF6B6B, light: 0xB4232C)
    public static let dangerText = color(dark: 0xFFD6D6, light: 0x8F1D27)
    public static let focusRing = color(dark: 0xC0B6FF, light: 0x4D32CC)

    // Поверхности совпадают с `color-mix(..., transparent)` кабинета.
    public static let successSurface = tinted(dark: 0x2FC9A6, light: 0x066E58, alpha: 0.09)
    public static let warningSurface = tinted(dark: 0xF0A742, light: 0x9A5B00, alpha: 0.09)
    public static let dangerSurface = tinted(dark: 0xFF6B6B, light: 0xB4232C, alpha: 0.08)
    public static let accentSurface = tinted(dark: 0xAB99FF, light: 0x6248D5, alpha: 0.10)
    // Границы совпадают с `color-mix(in srgb, <тон> N%, var(--line))` кабинета.
    public static let successBorder = color(dark: 0x5BA59E, light: 0x477A7A)
    public static let warningBorder = color(dark: 0xB29671, light: 0x897150)
    public static let dangerBorder = color(dark: 0xB97B83, light: 0x955764)
    public static let accentBorder = color(dark: 0x918FC3, light: 0x706BAF)
    public static let overlayBackdrop = color(dark: 0x05070C, light: 0x05070C, darkAlpha: 0.70, lightAlpha: 0.40)
    public static let speakerContrastText = color(dark: 0x151719, light: 0xFFFFFF)

    // MARK: - Helpers

    private static func rgb(_ value: Int, alpha: CGFloat = 1) -> NSColor {
        NSColor(
            srgbRed: CGFloat((value >> 16) & 0xFF) / 255,
            green: CGFloat((value >> 8) & 0xFF) / 255,
            blue: CGFloat(value & 0xFF) / 255,
            alpha: alpha
        )
    }

    private static func nsColor(
        dark: Int,
        light: Int,
        darkAlpha: CGFloat,
        lightAlpha: CGFloat
    ) -> NSColor {
        NSColor(name: nil) { appearance in
            let isDark = appearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
            return isDark
                ? rgb(dark, alpha: darkAlpha)
                : rgb(light, alpha: lightAlpha)
        }
    }

    private static func color(
        dark: Int,
        light: Int,
        darkAlpha: CGFloat = 1,
        lightAlpha: CGFloat = 1
    ) -> Color {
        Color(nsColor: nsColor(dark: dark, light: light, darkAlpha: darkAlpha, lightAlpha: lightAlpha))
    }

    private static func tinted(dark: Int, light: Int, alpha: CGFloat) -> Color {
        color(dark: dark, light: light, darkAlpha: alpha, lightAlpha: alpha)
    }
}
