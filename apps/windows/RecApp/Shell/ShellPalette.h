#pragma once

#include <cstdint>
#include <string_view>
#include <vector>

namespace graf::windows {

// Цвет оформления оболочки: значение и прозрачность.
struct ShellColor {
    std::uint32_t rgb = 0;
    double alpha = 1.0;
};

// Одна кисть оболочки в двух темах. Значения совпадают с палитрой кабинета
// (`cabinet.css`, тёмная и светлая темы) и с macOS `DesktopDesignTokens`, чтобы
// приложение и веб выглядели одинаково. Светлые значения нужны не «на всякий
// случай»: кабинет умеет отдавать светлую тему, и окно должно следовать ей.
struct ShellPaletteEntry {
    const wchar_t* key;
    ShellColor dark;
    ShellColor light;
};

// Какая тема действует. Объявление кабинета решает всё, кроме «system»: там
// решает система. Неизвестное значение не становится оформлением.
[[nodiscard]] bool resolveShellIsDark(std::string_view announced, bool systemIsDark);

// Полный набор кистей оболочки в порядке применения.
[[nodiscard]] const std::vector<ShellPaletteEntry>& shellPaletteEntries();

// Цвет кисти для темы. Отдельная функция нужна проверкам и сборке кистей.
[[nodiscard]] ShellColor shellPaletteColor(const ShellPaletteEntry& entry, bool isDark);

}  // namespace graf::windows
