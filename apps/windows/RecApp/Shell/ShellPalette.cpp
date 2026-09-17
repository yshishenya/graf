#include "ShellPalette.h"

#include <algorithm>

namespace graf::windows {
namespace {

// Значения взяты из палитры кабинета `cabinet.css` (блоки `:root` и
// `html[data-theme="light"]`) и совпадают с macOS `DesktopDesignTokens`.
constexpr ShellColor color(std::uint32_t rgb, double alpha = 1.0) { return ShellColor{rgb, alpha}; }

const std::vector<ShellPaletteEntry> kEntries = {
    // Основа: фон окна, рельса и поверхности карточек.
    {L"ApplicationPageBackgroundThemeBrush", color(0x17181B), color(0xF5F6F8)},
    {L"LayerFillColorDefaultBrush", color(0x1D1F23), color(0xFFFFFF)},
    {L"CardBackgroundFillColorDefaultBrush", color(0x22252A), color(0xFFFFFF)},
    {L"CardStrokeColorDefaultBrush", color(0xFFFFFF, 0.10), color(0x121823, 0.13)},
    {L"ControlFillColorSecondaryBrush", color(0x30343C), color(0xE5E8EE)},
    // Системная акцентная кисть WinUI: без неё заливка берёт цвет системы, и
    // «Начать запись» становится голубой вместо акцента GRAF.
    {L"AccentFillColorDefaultBrush", color(0x7056E9), color(0x6248D5)},
    // Собственные кисти оболочки: те же имена, что у токенов кабинета.
    {L"GrafBackgroundBrush", color(0x17181B), color(0xF5F6F8)},
    {L"GrafPanelBrush", color(0x1D1F23), color(0xFFFFFF)},
    {L"GrafSurfaceBrush", color(0x22252A), color(0xFFFFFF)},
    {L"GrafSurface2Brush", color(0x272A30), color(0xF0F2F5)},
    {L"GrafSurface3Brush", color(0x30343C), color(0xE5E8EE)},
    {L"GrafLineBrush", color(0x7E8898), color(0x7A8494)},
    {L"GrafLineSoftBrush", color(0xFFFFFF, 0.10), color(0x121823, 0.13)},
    {L"GrafTextBrush", color(0xF0F1F4), color(0x1D222B)},
    {L"GrafMutedTextBrush", color(0xADB2BC), color(0x525B68)},
    {L"GrafAccentBrush", color(0xAB99FF), color(0x6248D5)},
    {L"GrafAccentSolidBrush", color(0x7056E9), color(0x6248D5)},
    {L"GrafAccentHoverBrush", color(0x755CDE), color(0x5339C5)},
    {L"GrafAccentForegroundBrush", color(0xFFFFFF), color(0xFFFFFF)},
    {L"GrafSuccessBrush", color(0x2FC9A6), color(0x066E58)},
    {L"GrafWarningBrush", color(0xF0A742), color(0x9A5B00)},
    {L"GrafDangerBrush", color(0xFF6B6B), color(0xB4232C)},
    {L"GrafDangerTextBrush", color(0xFFD6D6), color(0x8F1D27)},
    {L"GrafFocusRingBrush", color(0xC0B6FF), color(0x4D32CC)},
    // Полоса записи одна в обеих темах: это состояние, а не оформление.
    {L"GrafRecordingStripBrush", color(0x342087), color(0x342087)},
};

}  // namespace

bool resolveShellIsDark(std::string_view announced, bool systemIsDark) {
    if (announced == "dark") return true;
    if (announced == "light") return false;
    // «system» и всё, что кабинет не объявляет, решает система.
    return systemIsDark;
}

const std::vector<ShellPaletteEntry>& shellPaletteEntries() { return kEntries; }

ShellColor shellPaletteColor(const ShellPaletteEntry& entry, bool isDark) {
    return isDark ? entry.dark : entry.light;
}

}  // namespace graf::windows
