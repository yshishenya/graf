#include <atomic>
#include <cstddef>

// Intentionally before the production header, unlike the peer translation unit.
// On MSVC 19.44 /GL this exposed different atomic type metadata at link time.
struct PriorAtomicMember { std::atomic<std::size_t> value{0}; };
#include "../../RecApp/Storage/ProtectedCustodyMemory.h"
#include <cstdio>

std::size_t custodyPeerUsedBytes();
char* custodyPeerAllocate(std::size_t count);
void custodyPeerFree(char*, std::size_t count);

int main() {
    using namespace graf::windows;
    const auto baseline = CustodyOwnedMemory::usedBytes();
    auto bytes = custodyPeerAllocate(257);
    const bool shared = CustodyOwnedMemory::usedBytes() == baseline + 257 &&
        custodyPeerUsedBytes() == baseline + 257;
    const auto excess = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes() + 1;
    bool bounded = false;
    try {
        auto unexpected = CustodyAllocator<char>{}.allocate(excess);
        CustodyAllocator<char>{}.deallocate(unexpected, excess);
    } catch (const std::bad_alloc&) { bounded = true; }
    custodyPeerFree(bytes, 257);
    const bool balanced = CustodyOwnedMemory::usedBytes() == baseline && custodyPeerUsedBytes() == baseline;
    bytes = CustodyAllocator<char>{}.allocate(73);
    const bool reverse = custodyPeerUsedBytes() == baseline + 73;
    CustodyAllocator<char>{}.deallocate(bytes, 73);
    const bool restored = custodyPeerUsedBytes() == baseline;
    std::printf("shared=%d bounded=%d balanced=%d reverse=%d restored=%d\n",
        shared, bounded, balanced, reverse, restored);
    return shared && bounded && balanced && reverse && restored ? 0 : 1;
}
