#include "../../RecApp/Core/WindowsDesktopSession.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#if defined(_MSC_VER) && defined(_DEBUG)
#include <crtdbg.h>
namespace {
thread_local bool denyLeaseAllocation = false;
int leaseAllocationHook(int kind, void*, std::size_t, int, long, const unsigned char*, int) {
    if (kind == _HOOK_ALLOC && denyLeaseAllocation) { denyLeaseAllocation = false; return 0; }
    return 1;
}
}
#endif

int main() {
    using namespace graf::windows;
#if defined(_MSC_VER) && defined(_DEBUG)
    {
        WindowsDesktopSession denied("allocation-refusal");
        const auto previous = _CrtSetAllocHook(leaseAllocationHook);
        denyLeaseAllocation = true;
        const auto result = denied.beginReadinessCheck();
        denyLeaseAllocation = false;
        _CrtSetAllocHook(previous);
        assert(result.status == TransitionStatus::rejected && result.reason == ReasonCode::storageUnavailable);
        WindowsDesktopSession retry("no-leaked-slot");
        assert(retry.beginReadinessCheck().accepted());
        assert(retry.block(ReasonCode::microphonePermissionDenied).accepted());
    }
#endif
    WindowsDesktopSession session("one");
    assert(session.beginReadinessCheck().accepted());
    assert(session.markReady().accepted());
    assert(session.beginStart().accepted());
    assert(session.startRecording().accepted());
    assert(session.pause().accepted());
    assert(session.resume().accepted());
    assert(session.stop().accepted());
    assert(session.stop().status == TransitionStatus::idempotent);
    assert(session.beginFinalizing().accepted());
    assert(session.saveLocal().accepted());
    assert(session.queue().accepted());
    assert(session.upload().accepted());
    WindowsDesktopSession second("two");
    assert(second.beginReadinessCheck().accepted());
    assert(second.block(ReasonCode::microphonePermissionDenied).accepted());
    return 0;
}
