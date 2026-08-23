#include "../../RecApp/Diagnostics/MetadataSafeDiagnostics.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    const auto json = MetadataSafeDiagnostics::serialize({"1", "19045", "x64", SessionState::degraded,
        ReasonCode::clockDiscontinuity, 1, 2, 3, "C:\\private\\endpoint"});
    assert(json.find("private") == std::string::npos);
    assert(json.find("endpoint_fingerprint") != std::string::npos);
    assert(json.find("transcript") == std::string::npos);
    return 0;
}
