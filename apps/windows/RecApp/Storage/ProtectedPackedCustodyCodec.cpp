#include "ProtectedPackedCustodyCodec.h"
#include "ProtectedCustodyPrimitives.h"
#include <algorithm>
#include <cstring>
#include <limits>
#include <utility>

namespace graf::windows {
namespace {
using Kind = PackedRecordKind;
using Error = CustodyCodecError;
using Format = ProtectedPackedCustodyFormat;
using custody_detail::digest;
using custody_detail::WipeBytes;
constexpr std::size_t headerBytes = 128, framingBytes = 16, headCellBytes = 16384;
template<class T> CustodyCodecResult<T> failure(Error error, std::uint32_t native = 0) {
    return {std::nullopt, error, native};
}
template<class Buffer> void put(Buffer& out, std::size_t at, std::uint64_t value, std::size_t width) {
    for (std::size_t i = 0; i < width; ++i) out[at + i] = static_cast<std::uint8_t>(value >> (i * 8));
}
std::uint64_t get(const CustodyBytes& in, std::size_t at, std::size_t width) {
    std::uint64_t value = 0;
    for (std::size_t i = 0; i < width; ++i) value |= std::uint64_t{in[at + i]} << (i * 8);
    return value;
}
std::size_t envelopeLimit(const PackedRecordAddress& a) {
    return a.kind == Kind::data ? static_cast<std::size_t>(a.bodyBytes) + 4096 :
        (a.kind == Kind::head ? headCellBytes : 8192);
}
bool addressValid(const PackedCustodyContext& c, const PackedRecordAddress& a, bool coldHead = false) {
    if (!Format::encodePrefix(c)) return false;
    if (a.kind == Kind::head) return a.selector <= 1 && a.offset == 128 + a.selector * headCellBytes &&
        a.bodyBytes == 128 && ((coldHead && a.version == 0) || (a.version != 0 &&
        (a.version == 1 || (a.version - 1) % 2 == a.selector)));
    if (a.version == 0 || a.offset < Format::appendOffset || a.offset % 16 != 0 ||
        a.offset > std::numeric_limits<std::uint64_t>::max() - envelopeLimit(a)) return false;
    if (a.kind == Kind::data) return a.bodyBytes > 0 && a.bodyBytes <= Format::blockBytes && a.selector < 262144;
    if (a.bodyBytes != 4096) return false;
    switch (a.kind) {
    case Kind::nodeL0: return a.selector < 262144 && a.selector % 64 == 0;
    case Kind::nodeL1: return a.selector < 262144 && a.selector % 4096 == 0;
    case Kind::nodeL2: return a.selector == 0;
    default: return false;
    }
}
std::array<std::uint8_t, headerBytes> header(const PackedCustodyContext& c, const PackedRecordAddress& a) {
    std::array<std::uint8_t, headerBytes> out{};
    std::memcpy(out.data(), "GRFPTV2", 8); put(out, 8, 2, 2);
    put(out, 10, static_cast<std::uint32_t>(a.kind), 1);
    put(out, 11, static_cast<std::uint16_t>(c.object.role), 1); put(out, 12, headerBytes, 4);
    std::copy(c.object.storeId.begin(), c.object.storeId.end(), out.begin() + 16);
    std::copy(c.object.objectId.begin(), c.object.objectId.end(), out.begin() + 32);
    std::copy(c.containerId.begin(), c.containerId.end(), out.begin() + 48);
    put(out, 64, a.offset, 8); put(out, 72, a.selector, 8); put(out, 80, a.version, 8);
    put(out, 88, a.bodyBytes, 4);
    return out;
}
auto entropy(const PackedCustodyContext& c, const PackedRecordAddress& a) {
    constexpr char domain[] = "graf.custody.packed.v2";
    constexpr auto prefix = sizeof(domain) - 1;
    std::array<std::uint8_t, prefix + 68> out{};
    std::memcpy(out.data(), domain, prefix);
    put(out, prefix, 2, 2); put(out, prefix + 2, static_cast<std::uint32_t>(a.kind), 1);
    put(out, prefix + 3, static_cast<std::uint16_t>(c.object.role), 1);
    std::copy(c.object.storeId.begin(), c.object.storeId.end(), out.begin() + prefix + 4);
    std::copy(c.object.objectId.begin(), c.object.objectId.end(), out.begin() + prefix + 20);
    std::copy(c.containerId.begin(), c.containerId.end(), out.begin() + prefix + 36);
    put(out, prefix + 52, a.offset, 8); put(out, prefix + 60, a.selector, 8);
    return out;
}
std::optional<std::array<std::uint8_t, 32>> internalDigest(const PackedRecordAddress& a, const CustodyBytes& plain) {
    return a.kind == Kind::data ? digest(plain.data() + headerBytes, a.bodyBytes) : digest(plain.data(), plain.size());
}
CustodyCodecResult<PackedDecodedRecord> open(
    const PackedCustodyContext& c, PackedRecordAddress a, const CustodyBytes& envelope, bool coldHead) {
    if (!addressValid(c, a, coldHead)) return failure<PackedDecodedRecord>(Error::invalidInput);
    if (envelope.size() <= framingBytes || envelope.size() > envelopeLimit(a) ||
        (a.kind == Kind::head && envelope.size() != headCellBytes) ||
        std::memcmp(envelope.data(), "GRFPEV2", 8) != 0 || get(envelope, 8, 2) != 2 ||
        get(envelope, 10, 1) != static_cast<std::uint32_t>(a.kind) ||
        get(envelope, 11, 1) != static_cast<std::uint16_t>(c.object.role))
        return failure<PackedDecodedRecord>(Error::invalidEnvelope);
    const auto cipherBytes = static_cast<std::size_t>(get(envelope, 12, 4));
    if (cipherBytes == 0 || cipherBytes > envelope.size() - framingBytes ||
        (a.kind != Kind::head && cipherBytes != envelope.size() - framingBytes) ||
        !std::all_of(envelope.begin() + framingBytes + cipherBytes, envelope.end(), [](auto byte) { return byte == 0; }))
        return failure<PackedDecodedRecord>(Error::invalidEnvelope);
    const auto binding = entropy(c, a);
    auto decoded = custody_detail::nativeTransform(binding.data(), binding.size(),
        envelope.data() + framingBytes, cipherBytes, headerBytes + a.bodyBytes, false, headerBytes + a.bodyBytes);
    if (!decoded.ok()) return failure<PackedDecodedRecord>(decoded.error, decoded.nativeError);
    auto& plain = *decoded.value; WipeBytes wipe{plain};
    if (coldHead && a.version == 0) a.version = get(plain, 80, 8);
    if (!addressValid(c, a)) return failure<PackedDecodedRecord>(Error::invalidPlaintext);
    const auto expected = header(c, a);
    if (!std::equal(expected.begin(), expected.begin() + 96, plain.begin()))
        return failure<PackedDecodedRecord>(Error::invalidPlaintext);
    std::array<std::uint8_t, 32> checksum{};
    std::copy_n(plain.begin() + 96, checksum.size(), checksum.begin());
    std::fill(plain.begin() + 96, plain.begin() + headerBytes, std::uint8_t{0});
    const auto actual = internalDigest(a, plain);
    if (!actual) return failure<PackedDecodedRecord>(Error::hashFailed);
    if (*actual != checksum) return failure<PackedDecodedRecord>(Error::invalidPlaintext);
    return {PackedDecodedRecord{CustodyBytes(plain.begin() + headerBytes, plain.end()), a.version}, Error::none, 0};
}
}
CustodyCodecResult<CustodyBytes> ProtectedPackedCustodyCodec::seal(
    const PackedCustodyContext& c, const PackedRecordAddress& a, const CustodyBytes& body) try {
    if (!addressValid(c, a) || body.size() != a.bodyBytes) return failure<CustodyBytes>(Error::invalidInput);
    CustodyBytes plain(headerBytes + body.size()); WipeBytes wipe{plain};
    const auto typed = header(c, a);
    std::copy(typed.begin(), typed.end(), plain.begin());
    std::copy(body.begin(), body.end(), plain.begin() + headerBytes);
    const auto checksum = internalDigest(a, plain);
    if (!checksum) return failure<CustodyBytes>(Error::hashFailed);
    std::copy(checksum->begin(), checksum->end(), plain.begin() + 96);
    const auto binding = entropy(c, a);
    auto protectedBytes = custody_detail::nativeTransform(binding.data(), binding.size(),
        plain.data(), plain.size(), envelopeLimit(a) - framingBytes, true);
    if (!protectedBytes.ok()) return protectedBytes;
    const auto& cipher = *protectedBytes.value;
    CustodyBytes out(a.kind == Kind::head ? headCellBytes : framingBytes + cipher.size());
    std::memcpy(out.data(), "GRFPEV2", 8); put(out, 8, 2, 2);
    put(out, 10, static_cast<std::uint32_t>(a.kind), 1); put(out, 11, static_cast<std::uint16_t>(c.object.role), 1);
    put(out, 12, cipher.size(), 4); std::copy(cipher.begin(), cipher.end(), out.begin() + framingBytes);
    return {std::move(out), Error::none, 0};
} catch (const std::bad_alloc&) { return failure<CustodyBytes>(Error::allocationFailed); }
CustodyCodecResult<PackedDecodedRecord> ProtectedPackedCustodyCodec::openReferenced(
    const PackedCustodyContext& c, std::uint64_t selector, const PackedReference& ref, const CustodyBytes& envelope) try {
    const PackedRecordAddress a{ref.kind, ref.offset, selector, ref.version, ref.kind == Kind::data ? ref.payloadBytes : 4096U};
    if (!Format::encodeReference(ref) || !addressValid(c, a)) return failure<PackedDecodedRecord>(Error::invalidInput);
    if (envelope.size() != ref.envelopeBytes) return failure<PackedDecodedRecord>(Error::invalidEnvelope);
    const auto checksum = digest(envelope.data(), envelope.size());
    if (!checksum) return failure<PackedDecodedRecord>(Error::hashFailed);
    if (*checksum != ref.envelopeSha) return failure<PackedDecodedRecord>(Error::invalidEnvelope);
    return open(c, a, envelope, false);
} catch (const std::bad_alloc&) { return failure<PackedDecodedRecord>(Error::allocationFailed); }
CustodyCodecResult<PackedDecodedRecord> ProtectedPackedCustodyCodec::openHead(
    const PackedCustodyContext& c, std::uint32_t slot, const CustodyBytes& cell, std::uint64_t expectedGeneration) try {
    return open(c, {Kind::head, 128 + std::uint64_t{slot} * headCellBytes, slot, expectedGeneration, 128}, cell, true);
} catch (const std::bad_alloc&) { return failure<PackedDecodedRecord>(Error::allocationFailed); }
} // namespace graf::windows
