#include <windows.h>
#include <dpapi.h>
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <algorithm>
#include <cassert>
#include <cstring>
#include "../../RecApp/Storage/ProtectedPackedCustodyCodec.h"
#include "../../RecApp/Storage/Sha256.h"

// Only this synthetic executable replaces native calls. No application fault
// switch, input devices, files, credentials or protection downgrade.
namespace {
enum class Fault { none, failure, shortOutput, longOutput, empty, corrupt };
Fault fault = Fault::none;
unsigned protects = 0, unprotects = 0, frees = 0;
BYTE* allocation = nullptr;
std::size_t allocatedBytes = 0, ownedAtFree = 0;
BOOL transform(DATA_BLOB* in, DATA_BLOB* extra, DWORD flags, DATA_BLOB* out, bool protect) {
    assert(!allocation && flags == CRYPTPROTECT_UI_FORBIDDEN && extra && extra->cbData);
    protect ? ++protects : ++unprotects;
    if (fault == Fault::empty) return TRUE;
    if (fault == Fault::failure) {
        out->cbData = 32; out->pbData = static_cast<BYTE*>(LocalAlloc(LMEM_FIXED, 32));
        assert(out->pbData); std::memset(out->pbData, 42, 32);
    } else {
        const auto ok = protect ? CryptProtectData(in, nullptr, extra, nullptr, nullptr, flags, out)
            : CryptUnprotectData(in, nullptr, extra, nullptr, nullptr, flags, out);
        if (!ok) return ok;
        if (fault == Fault::shortOutput || fault == Fault::longOutput) {
            const DWORD size = fault == Fault::shortOutput ? out->cbData - 1 : out->cbData + 1;
            SecureZeroMemory(out->pbData, out->cbData); LocalFree(out->pbData);
            out->cbData = size; out->pbData = static_cast<BYTE*>(LocalAlloc(LMEM_FIXED, size));
            assert(out->pbData); std::memset(out->pbData, 42, size);
        } else if (fault == Fault::corrupt) {
            assert(out->cbData > 128); out->pbData[128] ^= 1;
        }
    }
    allocation = out->pbData; allocatedBytes = out->cbData;
    if (fault == Fault::failure) { SetLastError(ERROR_INVALID_DATA); return FALSE; }
    return TRUE;
}
BOOL WINAPI testProtect(DATA_BLOB* in, LPCWSTR description, DATA_BLOB* extra, PVOID reserved,
    CRYPTPROTECT_PROMPTSTRUCT* prompt, DWORD flags, DATA_BLOB* out) {
    assert(!description && !reserved && !prompt);
    return transform(in, extra, flags, out, true);
}
BOOL WINAPI testUnprotect(DATA_BLOB* in, LPWSTR* description, DATA_BLOB* extra, PVOID reserved,
    CRYPTPROTECT_PROMPTSTRUCT* prompt, DWORD flags, DATA_BLOB* out) {
    assert(!description && !reserved && !prompt);
    return transform(in, extra, flags, out, false);
}
HLOCAL WINAPI testFree(HLOCAL memory) {
    assert(memory == allocation);
    assert(std::all_of(allocation, allocation + allocatedBytes, [](BYTE value) { return value == 0; }));
    ownedAtFree = graf::windows::CustodyOwnedMemory::usedBytes();
    allocation = nullptr; allocatedBytes = 0; ++frees;
    return LocalFree(memory);
}
}
#define CryptProtectData testProtect
#define CryptUnprotectData testUnprotect
#define LocalFree testFree
#include "../../RecApp/Storage/ProtectedCustodyPrimitives.cpp"
#undef CryptProtectData
#undef CryptUnprotectData
#undef LocalFree

using namespace graf::windows;
namespace {
std::array<std::uint8_t, 32> digest(const CustodyBytes& bytes) {
    const auto result = custody_detail::digest(bytes.data(), bytes.size()); assert(result); return *result;
}
}
int main() {
    using Codec = ProtectedPackedCustodyCodec;
    using Kind = PackedRecordKind;
    using Error = CustodyCodecError;
    const PackedCustodyContext c{{{}, {}, CustodyRole::canonical}, {}};
    for (const auto kind : {Kind::data, Kind::nodeL0, Kind::nodeL1, Kind::nodeL2, Kind::head}) {
        const PackedRecordAddress a{kind, kind == Kind::head ? 128ULL : 32896ULL, 0, 1,
            kind == Kind::data ? 3U : (kind == Kind::head ? 128U : 4096U)};
        const CustodyBytes body(a.bodyBytes, std::uint8_t{42});
        fault = Fault::none;
        auto sealed = Codec::seal(c, a, body); assert(sealed.ok() && !allocation);
        const PackedReference ref{kind, static_cast<std::uint32_t>(sealed.value->size()), a.offset, a.version,
            kind == Kind::data ? 3U : 0U, digest(*sealed.value)};
        const auto open = [&] { return kind == Kind::head ? Codec::openHead(c, 0, *sealed.value)
            : Codec::openReferenced(c, 0, ref, *sealed.value); };
        assert(open().ok());
        if (kind != Kind::head) {
            auto bad = ref; bad.envelopeSha[0] ^= 1;
            const auto before = unprotects;
            assert(Codec::openReferenced(c, 0, bad, *sealed.value).error == Error::invalidEnvelope);
            bad = ref; bad.envelopeBytes--;
            assert(Codec::openReferenced(c, 0, bad, *sealed.value).error == Error::invalidEnvelope);
            assert(unprotects == before); // Includes NODE_L2 root before child decoding.
        }
        for (const auto selected : {Fault::failure, Fault::shortOutput, Fault::longOutput, Fault::empty, Fault::corrupt}) {
            fault = selected;
            const auto before = frees;
            auto result = open(); assert(!result.ok() && !allocation);
            assert(result.error == (selected == Fault::failure ? Error::nativeFailed : Error::invalidPlaintext));
            if (selected == Fault::failure) assert(result.nativeError == ERROR_INVALID_DATA);
            assert(frees == before + (selected == Fault::empty ? 0U : 1U));
        }
        fault = Fault::failure;
        auto failedSeal = Codec::seal(c, a, body);
        assert(failedSeal.error == Error::nativeFailed && failedSeal.nativeError == ERROR_INVALID_DATA && !allocation);
    }
    // Direct primitive proves exact native size is checked before owned copy,
    // including TRUE output over the caller cap and allocation refusal cleanup.
    const std::array<std::uint8_t, 2> input{7, 8}; const std::uint8_t entropy = 1;
    fault = Fault::none;
    auto cipher = custody_detail::nativeTransform(&entropy, 1, input.data(), input.size(), 4096, true); assert(cipher.ok());
    const auto base = CustodyOwnedMemory::usedBytes();
    {
        CustodyBytes full; full.reserve(CustodyOwnedMemory::limit - base);
        // There is NO owned-copy capacity. A transient copy before validation
        // would throw, even if it was released before NativeOutput destruction.
        for (const auto selected : {Fault::shortOutput, Fault::longOutput}) {
            fault = selected;
            const auto result = custody_detail::nativeTransform(&entropy, 1, cipher.value->data(), cipher.value->size(), 16, false, 2);
            assert(result.error == Error::invalidPlaintext && ownedAtFree == CustodyOwnedMemory::limit && !allocation);
        }
        fault = Fault::none;
        auto oversized = custody_detail::nativeTransform(&entropy, 1, input.data(), input.size(), 1, true);
        assert(oversized.error == Error::invalidPlaintext && ownedAtFree == CustodyOwnedMemory::limit && !allocation);
        bool rejected = false;
        try { (void)custody_detail::nativeTransform(&entropy, 1, input.data(), input.size(), 4096, true); }
        catch (const std::bad_alloc&) { rejected = true; }
        assert(rejected && !allocation && ownedAtFree == CustodyOwnedMemory::limit);
    }
    assert(CustodyOwnedMemory::usedBytes() == base && protects > 0 && unprotects > 0);
}
