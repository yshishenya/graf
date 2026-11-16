#include "Shell/MainWindowPlacement.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <limits>

using namespace graf::windows;

namespace {
void expect(std::optional<MainWindowRect> const& actual, MainWindowRect expected) {
    assert(actual);
    assert(actual->x == expected.x && actual->y == expected.y);
    assert(actual->width == expected.width && actual->height == expected.height);
}
}

int main() {
    const MainWindowPlacement saved{L"synthetic-monitor", 137, 83, 901, 577, 120};
    // Physical pixels survive a cold restart without another rounding pass.
    expect(restoreMainWindowRect(saved, {-1920, -1040, 1920, 1040}, 120, true),
        {-1783, -957, 901, 577});
    // Two successive cold starts must not drift an odd-sized physical frame.
    auto next = saved;
    for (int launch = 0; launch < 2; ++launch) {
        const auto rect = restoreMainWindowRect(next, {-1920, -1040, 1920, 1040}, 120, true);
        expect(rect, {-1783, -957, 901, 577});
        next = {saved.monitorIdentity, rect->x + 1920, rect->y + 1040, rect->width, rect->height, 120};
    }
    expect(restoreMainWindowRect(saved, {-3840, -2160, 3840, 2160}, 240, true),
        {-3566, -1994, 1802, 1154});
    // A removed monitor retains logical size, centered on the primary work area.
    expect(restoreMainWindowRect(saved, {0, 40, 1920, 1040}, 240, false),
        {59, 40, 1802, 1040});
    auto edge = saved; edge.offsetX = -80; edge.offsetY = 2000;
    expect(restoreMainWindowRect(edge, {1920, -200, 1280, 680}, 120, true),
        {1920, -97, 901, 577});
    edge.offsetX = -1; edge.offsetY = -1;
    expect(restoreMainWindowRect(edge, {-3840, -2160, 3840, 2160}, 180, true),
        {-3840, -2160, 1352, 866});
    expect(restoreMainWindowRect(saved, {-800, 0, 800, 500}, 120, true), {-800, 0, 800, 500});
    expect(restoreMainWindowRect(std::nullopt, {1920, 40, 1920, 1040}, 96, false),
        {2340, 250, 1080, 620});
    expect(restoreMainWindowRect(std::nullopt, {0, 0, 3840, 2160}, 192, false),
        {840, 460, 2160, 1240});
    for (int field = 0; field < 4; ++field) {
        auto invalid = saved;
        if (field == 0) invalid.width = 0;
        if (field == 1) invalid.height = -1;
        if (field == 2) invalid.dpi = 0;
        if (field == 3) invalid.monitorIdentity.clear();
        assert(!validMainWindowPlacement(invalid));
        expect(restoreMainWindowRect(invalid, {0, 0, 1920, 1080}, 96, true),
            {420, 230, 1080, 620});
    }
    auto overflow = saved;
    overflow.width = std::numeric_limits<int>::max(); overflow.dpi = 1;
    expect(restoreMainWindowRect(overflow, {0, 0, 1920, 1080}, 192, true),
        {0, 0, 1920, 1080});
    overflow = saved; overflow.offsetX = std::numeric_limits<int>::max();
    expect(restoreMainWindowRect(overflow, {1920, 0, 1920, 1080}, 120, true),
        {2205, 152, 1350, 775});
    assert(!restoreMainWindowRect(saved, {0, 0, 0, 1080}, 96, true));
    assert(!restoreMainWindowRect(saved, {0, 0, 1920, 1080}, 0, true));
    assert(!restoreMainWindowRect(saved, {std::numeric_limits<int>::max(), 0, 10, 10}, 96, true));
    return 0;
}
