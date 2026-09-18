#include "../../RecApp/Shell/MicrophoneConsentKey.h"

#include <string>

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>

namespace {

using graf::windows::microphoneConsentKeySuffixes;

void testPackagedConsentComesFirst() {
    // Порядок решает всё: общий ключ NonPackaged остаётся «Allow» после отказа
    // в системном запросе, и проверка его первым делает приложение слепым.
    const auto suffixes = microphoneConsentKeySuffixes(L"com.graf.desktop_1abc2def3ghi4");
    assert(suffixes.size() == 3);
    assert(suffixes[0] == L"\\com.graf.desktop_1abc2def3ghi4");
    assert(suffixes[1] == L"\\NonPackaged");
    assert(suffixes[2].empty());
}

void testUnpackagedFallsBack() {
    const auto suffixes = microphoneConsentKeySuffixes(L"");
    assert(suffixes.size() == 2);
    assert(suffixes[0] == L"\\NonPackaged");
    assert(suffixes[1].empty());
    for (const auto& suffix : suffixes) {
        assert(suffix.empty() || suffix.front() == L'\\');
    }
}

} // namespace

int main() {
    testPackagedConsentComesFirst();
    testUnpackagedFallsBack();
    std::printf("MicrophoneConsentKeyTests: ok\n");
    return 0;
}
