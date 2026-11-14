#include "../../RecApp/Storage/ProtectedPackedCustodyCodec.h"
#include "../../RecApp/Storage/Sha256.h"
#ifdef _WIN32
#include <windows.h>
#include <dpapi.h>
#endif
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <algorithm>
#include <cassert>
#include <cstring>
#include <limits>
#include <string>

using namespace graf::windows;
using Codec = ProtectedPackedCustodyCodec;
using Kind = PackedRecordKind;
using Error = CustodyCodecError;
namespace {
PackedCustodyContext context() {
    PackedCustodyContext c{{{}, {}, CustodyRole::canonical}, {}};
    c.object.storeId[0] = 1; c.object.objectId[15] = 2; c.containerId[7] = 3;
    return c;
}
#ifdef _WIN32
std::array<std::uint8_t, 32> hash(const CustodyBytes& bytes) {
    const auto text = sha256(std::string_view(reinterpret_cast<const char*>(bytes.data()), bytes.size()));
    std::array<std::uint8_t, 32> out{};
    const auto nibble = [](char c) { return c <= '9' ? c - '0' : c - 'a' + 10; };
    for (std::size_t i = 0; i < out.size(); ++i)
        out[i] = static_cast<std::uint8_t>(nibble(text[i * 2]) * 16 + nibble(text[i * 2 + 1]));
    return out;
}
PackedReference reference(const PackedRecordAddress& a, const CustodyBytes& envelope) {
    return {a.kind, static_cast<std::uint32_t>(envelope.size()), a.offset, a.version,
        a.kind == Kind::data ? a.bodyBytes : 0U, hash(envelope)};
}
void put(CustodyBytes& bytes, std::size_t at, std::uint64_t value, std::size_t count) {
    for (std::size_t i = 0; i < count; ++i) bytes.at(at + i) = static_cast<std::uint8_t>(value >> (i * 8));
}
CustodyBytes fixtureEntropy(const PackedCustodyContext& c, const PackedRecordAddress& a) {
    constexpr char domain[] = "graf.custody.packed.v2";
    CustodyBytes bytes(domain, domain + sizeof(domain) - 1);
    bytes.resize(90); put(bytes, 22, 2, 2); put(bytes, 24, static_cast<std::uint32_t>(a.kind), 1);
    put(bytes, 25, static_cast<std::uint16_t>(c.object.role), 1);
    std::copy(c.object.storeId.begin(), c.object.storeId.end(), bytes.begin() + 26);
    std::copy(c.object.objectId.begin(), c.object.objectId.end(), bytes.begin() + 42);
    std::copy(c.containerId.begin(), c.containerId.end(), bytes.begin() + 58);
    put(bytes, 74, a.offset, 8); put(bytes, 82, a.selector, 8);
    return bytes;
}
CustodyBytes nativeFixture(const PackedCustodyContext& c, const PackedRecordAddress& a,
    const CustodyBytes& bytes, bool protect) {
    auto binding = fixtureEntropy(c, a);
    DATA_BLOB input{static_cast<DWORD>(bytes.size()), const_cast<BYTE*>(bytes.data())};
    DATA_BLOB extra{static_cast<DWORD>(binding.size()), binding.data()}, output{};
    const auto ok = protect ? CryptProtectData(&input, nullptr, &extra, nullptr, nullptr, CRYPTPROTECT_UI_FORBIDDEN, &output)
        : CryptUnprotectData(&input, nullptr, &extra, nullptr, nullptr, CRYPTPROTECT_UI_FORBIDDEN, &output);
    assert(ok && output.pbData);
    CustodyBytes result(output.pbData, output.pbData + output.cbData);
    SecureZeroMemory(output.pbData, output.cbData); LocalFree(output.pbData);
    return result;
}
CustodyBytes wrap(const PackedCustodyContext& c, const PackedRecordAddress& a, const CustodyBytes& plain) {
    auto cipher = nativeFixture(c, a, plain, true);
    CustodyBytes out(a.kind == Kind::head ? 16384 : 16 + cipher.size());
    std::memcpy(out.data(), "GRFPEV2", 8); put(out, 8, 2, 2); put(out, 10, static_cast<std::uint32_t>(a.kind), 1);
    put(out, 11, static_cast<std::uint16_t>(c.object.role), 1); put(out, 12, cipher.size(), 4);
    std::copy(cipher.begin(), cipher.end(), out.begin() + 16); return out;
}
void malformedPlaintext(const PackedCustodyContext& c, const PackedRecordAddress& a, const CustodyBytes& plain) {
    const auto tryPlain = [&](const CustodyBytes& candidate) {
        const auto wrapped = wrap(c, a, candidate);
        if (a.kind == Kind::head) return Codec::openHead(c, static_cast<std::uint32_t>(a.selector), wrapped).error;
        return Codec::openReferenced(c, a.selector, reference(a, wrapped), wrapped).error;
    };
    assert(tryPlain(plain) == Error::none);
    for (const std::size_t at : {0U, 7U, 8U, 10U, 11U, 12U, 16U, 32U, 48U, 64U, 72U, 88U, 92U, 95U, 96U, 127U, 128U}) {
        auto bad = plain; bad.at(at) ^= 1; assert(tryPlain(bad) == Error::invalidPlaintext);
    }
    auto bad = plain; put(bad, 80, 0, 8); assert(tryPlain(bad) == Error::invalidPlaintext);
    if (a.kind != Kind::head) {
        bad = plain; bad[80] ^= 1; assert(tryPlain(bad) == Error::invalidPlaintext);
    }
    bad = plain; bad.pop_back(); assert(tryPlain(bad) == Error::invalidPlaintext);
    bad = plain; bad.push_back(0); assert(tryPlain(bad) == Error::invalidPlaintext);
}
#endif
}
int main() {
    const auto c = context();
    const CustodyBytes payload{7, 8, 9};
    const PackedRecordAddress data{Kind::data, 32896, 0, 1, 3};
    auto bad = data;
    for (const auto kind : {Kind::empty, Kind::zero, static_cast<Kind>(7)}) {
        bad.kind = kind;
        assert(Codec::seal(c, bad, payload).error == Error::invalidInput);
    }
    bad = data; bad.version = 0; assert(Codec::seal(c, bad, payload).error == Error::invalidInput);
    bad = data; bad.offset++; assert(Codec::seal(c, bad, payload).error == Error::invalidInput);
    bad = data; bad.offset = 128; assert(Codec::seal(c, bad, payload).error == Error::invalidInput);
    bad = data; bad.offset = std::numeric_limits<std::uint64_t>::max() - 15;
    assert(Codec::seal(c, bad, payload).error == Error::invalidInput);
    bad = data; bad.selector = 262144; assert(Codec::seal(c, bad, payload).error == Error::invalidInput);
    bad = data; bad.bodyBytes = 4; assert(Codec::seal(c, bad, payload).error == Error::invalidInput);
    auto wrong = c; wrong.object.role = CustodyRole::queue;
    assert(Codec::seal(wrong, data, payload).error == Error::invalidInput);
    assert(Codec::openHead(c, 2, CustodyBytes(16384)).error == Error::invalidInput);
    assert(Codec::openHead(c, 0, CustodyBytes(16383)).error == Error::invalidEnvelope);
#ifndef _WIN32
    assert(Codec::seal(c, data, payload).error == Error::unsupportedPlatform);
#else
    for (const auto role : {CustodyRole::canonical, CustodyRole::media, CustodyRole::playback}) {
        auto roleContext = c; roleContext.object.role = role;
        for (const auto kind : {Kind::data, Kind::nodeL0, Kind::nodeL1, Kind::nodeL2}) {
            auto a = data; a.kind = kind; a.version = 0x0102030405060708ULL;
            a.offset = 0x0102030405060700ULL; a.bodyBytes = kind == Kind::data ? 3 : 4096;
            const CustodyBytes body(a.bodyBytes, std::uint8_t{42});
            auto sealed = Codec::seal(roleContext, a, body); assert(sealed.ok());
            const auto plain = nativeFixture(roleContext, a, CustodyBytes(sealed.value->begin() + 16, sealed.value->end()), false);
            assert(plain.size() == 128 + a.bodyBytes);
            const std::array<std::uint8_t, 8> offsetLE{0, 7, 6, 5, 4, 3, 2, 1};
            const std::array<std::uint8_t, 8> versionLE{8, 7, 6, 5, 4, 3, 2, 1};
            assert(std::equal(offsetLE.begin(), offsetLE.end(), plain.begin() + 64));
            assert(std::equal(versionLE.begin(), versionLE.end(), plain.begin() + 80));
            assert(plain[8] == 2 && plain[9] == 0 && plain[12] == 128 && plain[13] == 0);
            std::array<std::uint8_t, 96> golden{};
            const std::array<std::uint8_t, 8> magic{'G', 'R', 'F', 'P', 'T', 'V', '2', 0};
            std::copy(magic.begin(), magic.end(), golden.begin());
            golden[8] = 2; golden[10] = static_cast<std::uint8_t>(kind);
            golden[11] = static_cast<std::uint8_t>(role); golden[12] = 128;
            golden[16] = 1; golden[47] = 2; golden[55] = 3;
            std::copy(offsetLE.begin(), offsetLE.end(), golden.begin() + 64);
            std::copy(versionLE.begin(), versionLE.end(), golden.begin() + 80);
            golden[88] = kind == Kind::data ? std::uint8_t{3} : std::uint8_t{0};
            golden[89] = kind == Kind::data ? std::uint8_t{0} : std::uint8_t{16};
            assert(std::equal(golden.begin(), golden.end(), plain.begin()));
            auto forDigest = kind == Kind::data ? body : plain;
            if (kind != Kind::data) std::fill(forDigest.begin() + 96, forDigest.begin() + 128, std::uint8_t{0});
            const auto independentDigest = hash(forDigest);
            assert(std::equal(independentDigest.begin(), independentDigest.end(), plain.begin() + 96));
            malformedPlaintext(roleContext, a, plain);
            const auto r = reference(a, *sealed.value);
            auto opened = Codec::openReferenced(roleContext, a.selector, r, *sealed.value);
            assert(opened.ok() && opened.value->body == body && opened.value->version == a.version);
            auto substituted = roleContext; substituted.containerId[0] ^= 1;
            assert(!Codec::openReferenced(substituted, a.selector, r, *sealed.value).ok());
            substituted = roleContext; substituted.object.storeId[0] ^= 1;
            assert(!Codec::openReferenced(substituted, a.selector, r, *sealed.value).ok());
            substituted = roleContext; substituted.object.objectId[0] ^= 1;
            assert(!Codec::openReferenced(substituted, a.selector, r, *sealed.value).ok());
            auto wrongRef = r; wrongRef.version++;
            assert(Codec::openReferenced(roleContext, a.selector, wrongRef, *sealed.value).error == Error::invalidPlaintext);
            wrongRef = r; wrongRef.envelopeSha[0] ^= 1;
            assert(Codec::openReferenced(roleContext, a.selector, wrongRef, *sealed.value).error == Error::invalidEnvelope);
            wrongRef = r; wrongRef.envelopeBytes--;
            assert(Codec::openReferenced(roleContext, a.selector, wrongRef, *sealed.value).error == Error::invalidEnvelope);
            auto broken = *sealed.value; broken[0] ^= 1;
            assert(Codec::openReferenced(roleContext, a.selector, r, broken).error == Error::invalidEnvelope);
            broken = *sealed.value; broken.push_back(0);
            assert(Codec::openReferenced(roleContext, a.selector, r, broken).error == Error::invalidEnvelope);
            for (const std::size_t at : {0U, 7U, 8U, 10U, 11U, 12U}) {
                broken = *sealed.value; broken[at] ^= 1;
                assert(Codec::openReferenced(roleContext, a.selector, reference(a, broken), broken).error == Error::invalidEnvelope);
            }
            broken = *sealed.value; broken.resize(16);
            assert(Codec::openReferenced(roleContext, a.selector, r, broken).error == Error::invalidEnvelope);
            if (kind != Kind::nodeL2) {
                const std::uint64_t step = kind == Kind::data ? 1 : (kind == Kind::nodeL0 ? 64 : 4096);
                assert(!Codec::openReferenced(roleContext, a.selector + step, r, *sealed.value).ok());
            }
        }
    }
    const CustodyBytes headBody(128, std::uint8_t{0}); // Semantic descriptor validation belongs to the tree layer.
    for (const std::uint64_t generation : {1ULL, 2ULL, 3ULL}) {
        for (const std::uint64_t slot : {0ULL, 1ULL}) {
            const PackedRecordAddress a{Kind::head, 128 + slot * 16384, slot, generation, 128};
            auto sealed = Codec::seal(c, a, headBody);
            if (generation != 1 && (generation - 1) % 2 != slot) {
                assert(sealed.error == Error::invalidInput); continue;
            }
            assert(sealed.ok() && sealed.value->size() == 16384);
            std::uint32_t cipherSize = 0;
            for (unsigned i = 0; i < 4; ++i) cipherSize |= std::uint32_t{(*sealed.value)[12 + i]} << (i * 8);
            const auto plain = nativeFixture(c, a, CustodyBytes(sealed.value->begin() + 16, sealed.value->begin() + 16 + cipherSize), false);
            malformedPlaintext(c, a, plain);
            auto opened = Codec::openHead(c, static_cast<std::uint32_t>(slot), *sealed.value);
            assert(opened.ok() && opened.value->version == generation && opened.value->body == headBody);
            assert(Codec::openHead(c, static_cast<std::uint32_t>(slot), *sealed.value, generation).ok());
            assert(!Codec::openHead(c, static_cast<std::uint32_t>(slot), *sealed.value, generation + 2).ok());
            assert(!Codec::openHead(c, static_cast<std::uint32_t>(1 - slot), *sealed.value).ok());
            auto broken = *sealed.value; broken.back() = 1;
            assert(Codec::openHead(c, static_cast<std::uint32_t>(slot), broken).error == Error::invalidEnvelope);
        }
    }
    const CustodyBytes full(262144, std::uint8_t{42});
    auto fullAddress = data; fullAddress.bodyBytes = 262144;
    auto fullSealed = Codec::seal(c, fullAddress, full); assert(fullSealed.ok());
    assert(fullSealed.value->size() <= 266240);
    assert(Codec::openReferenced(c, 0, reference(fullAddress, *fullSealed.value), *fullSealed.value).value->body == full);
    const auto fullRef = reference(fullAddress, *fullSealed.value);
    {
        CustodyBytes occupied; occupied.reserve(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
        assert(Codec::seal(c, data, payload).error == Error::allocationFailed);
        assert(Codec::openReferenced(c, 0, fullRef, *fullSealed.value).error == Error::allocationFailed);
        assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
    }
#endif
}
