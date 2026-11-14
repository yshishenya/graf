#include "../../RecApp/Storage/ProtectedCustodyMemory.h"

std::size_t custodyPeerUsedBytes() { return graf::windows::CustodyOwnedMemory::usedBytes(); }
char* custodyPeerAllocate(std::size_t count) { return graf::windows::CustodyAllocator<char>{}.allocate(count); }
void custodyPeerFree(char* bytes, std::size_t count) { graf::windows::CustodyAllocator<char>{}.deallocate(bytes, count); }
