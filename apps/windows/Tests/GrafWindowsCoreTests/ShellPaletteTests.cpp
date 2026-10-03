#include "Shell/ShellPalette.h"

// Проверки обязаны работать и в сборке выпуска, иначе они молча ничего не делают.
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <map>
#include <set>
#include <string>

namespace {

using graf::windows::ShellColor;
using graf::windows::shellPaletteColor;
using graf::windows::shellPaletteEntries;

std::uint32_t findColor(const std::wstring& key, bool isDark) {
    for (const auto& entry : shellPaletteEntries()) {
        if (key == entry.key) {
            const auto value = shellPaletteColor(entry, isDark);
            assert(value.alpha == 1.0);
            return value.rgb;
        }
    }
    std::fprintf(stderr, "missing palette entry\n");
    assert(false);
    return 0;
}

void testBothThemesAreComplete() {
    // Каждая кисть обязана существовать в обеих темах: светлая тема кабинета
    // включена, и окно следует ей. Кисть без светлого значения означала бы, что
    // часть окна остаётся тёмной на светлом фоне.
    std::set<std::wstring> keys;
    for (const auto& entry : shellPaletteEntries()) {
        assert(entry.key != nullptr && entry.key[0] != L'\0');
        assert(keys.insert(entry.key).second);
        for (const auto isDark : {true, false}) {
            const auto value = shellPaletteColor(entry, isDark);
            assert(value.rgb <= 0xFFFFFF);
            assert(value.alpha > 0.0 && value.alpha <= 1.0);
        }
    }
    assert(keys.size() >= 20);
    // Кисти, которыми пользуется оболочка, обязаны быть в наборе: иначе окно
    // вернётся к системной теме и разъедется с кабинетом.
    for (const auto* required : {L"ApplicationPageBackgroundThemeBrush", L"LayerFillColorDefaultBrush",
                                 L"CardBackgroundFillColorDefaultBrush", L"CardStrokeColorDefaultBrush",
                                 L"ControlFillColorSecondaryBrush", L"GrafTextBrush", L"GrafMutedTextBrush",
                                 L"GrafSurface2Brush", L"GrafSurface3Brush", L"GrafLineBrush",
                                 L"GrafRecordingStripBrush", L"AccentFillColorDefaultBrush"}) {
        assert(keys.count(required) == 1);
    }
}

void testValuesMatchTheCabinetPalette() {
    // Значения сверяются с `cabinet.css` и macOS `DesktopDesignTokens`. Это не
    // «примерно похожие» цвета: расхождение здесь видно как разные приложения.
    assert(findColor(L"GrafBackgroundBrush", true) == 0x17181B);
    assert(findColor(L"GrafBackgroundBrush", false) == 0xF5F6F8);
    assert(findColor(L"GrafPanelBrush", true) == 0x1D1F23);
    assert(findColor(L"GrafPanelBrush", false) == 0xFFFFFF);
    assert(findColor(L"GrafSurfaceBrush", true) == 0x22252A);
    assert(findColor(L"GrafSurfaceBrush", false) == 0xFFFFFF);
    assert(findColor(L"GrafSurface3Brush", true) == 0x30343C);
    assert(findColor(L"GrafSurface3Brush", false) == 0xE5E8EE);
    assert(findColor(L"GrafTextBrush", true) == 0xF0F1F4);
    assert(findColor(L"GrafTextBrush", false) == 0x1D222B);
    assert(findColor(L"GrafMutedTextBrush", true) == 0xADB2BC);
    assert(findColor(L"GrafMutedTextBrush", false) == 0x525B68);
    assert(findColor(L"GrafAccentSolidBrush", true) == 0x7056E9);
    assert(findColor(L"GrafAccentSolidBrush", false) == 0x6248D5);
    assert(findColor(L"GrafAccentHoverBrush", false) == 0x5339C5);
    // Системная акцентная кисть WinUI обязана нести акцент GRAF: иначе заливка
    // кнопок и шкал берёт цвет системы и выпадает из оформления окна.
    assert(findColor(L"AccentFillColorDefaultBrush", true) == 0x7056E9);
    assert(findColor(L"AccentFillColorDefaultBrush", false) == 0x6248D5);
    // Полоса записи и белый текст на ней одинаковы в обеих темах.
    assert(findColor(L"GrafRecordingStripBrush", true) == 0x342087);
    assert(findColor(L"GrafRecordingStripBrush", false) == 0x342087);
    assert(findColor(L"GrafAccentForegroundBrush", false) == 0xFFFFFF);
}

void testContrastOfTextOnItsOwnSurface() {
    // Текст оболочки должен читаться на своей поверхности в обеих темах.
    // Считается относительная яркость по WCAG, порог — 4.5:1 для мелкого текста.
    const auto luminance = [](std::uint32_t rgb) {
        const auto channel = [](double value) {
            const auto normalized = value / 255.0;
            return normalized <= 0.03928 ? normalized / 12.92
                                         : std::pow((normalized + 0.055) / 1.055, 2.4);
        };
        const auto red = channel(static_cast<double>((rgb >> 16) & 0xFF));
        const auto green = channel(static_cast<double>((rgb >> 8) & 0xFF));
        const auto blue = channel(static_cast<double>(rgb & 0xFF));
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
    };
    const auto ratio = [&luminance](std::uint32_t first, std::uint32_t second) {
        const auto one = luminance(first);
        const auto two = luminance(second);
        return (std::max(one, two) + 0.05) / (std::min(one, two) + 0.05);
    };
    for (const auto isDark : {true, false}) {
        for (const auto* surface : {L"GrafBackgroundBrush", L"GrafPanelBrush", L"GrafSurfaceBrush",
                                    L"GrafSurface2Brush"}) {
            const auto background = findColor(surface, isDark);
            assert(ratio(findColor(L"GrafTextBrush", isDark), background) >= 4.5);
            // Приглушённый текст — только там, где он крупнее или вспомогательный.
            assert(ratio(findColor(L"GrafMutedTextBrush", isDark), background) >= 3.0);
        }
        // Текст на полосе записи и на акцентной кнопке — белый в обеих темах.
        assert(ratio(findColor(L"GrafAccentForegroundBrush", isDark),
                     findColor(L"GrafRecordingStripBrush", isDark)) >= 4.5);
        assert(ratio(findColor(L"GrafAccentForegroundBrush", isDark),
                     findColor(L"GrafAccentSolidBrush", isDark)) >= 4.5);
    }
}

void testResolutionOfTheAnnouncedTheme() {
    using graf::windows::resolveShellIsDark;
    // Кабинет объявляет ровно три значения; строка объявления решает всё.
    assert(resolveShellIsDark("dark", false));
    assert(resolveShellIsDark("dark", true));
    assert(!resolveShellIsDark("light", false));
    assert(!resolveShellIsDark("light", true));
    // «system» и мусор следуют системе: страница не решает оформление значением,
    // которого кабинет не выставляет.
    for (const auto* announced : {"system", "", "Dark", "LIGHT", "auto", "sepia"}) {
        assert(resolveShellIsDark(announced, true));
        assert(!resolveShellIsDark(announced, false));
    }
}

}  // namespace

int main() {
    testBothThemesAreComplete();
    testValuesMatchTheCabinetPalette();
    testContrastOfTextOnItsOwnSurface();
    testResolutionOfTheAnnouncedTheme();
    return 0;
}
