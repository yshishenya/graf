#include "../../RecApp/Contracts/WindowsDesktopContracts.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    struct Evidence { const char* os; const char* architecture; const char* sourceClass; const char* reason; };
    const Evidence evidence{"Windows10-22H2", "x64", "render_loopback", "none"};
    assert(evidence.os[0] != '\0' && evidence.architecture[0] != '\0');
    assert(evidence.sourceClass[0] != '\0' && evidence.reason[0] != '\0');
    assert(kManifestSchemaVersion == "local-recording-manifest.v5");
    return 0;
}
