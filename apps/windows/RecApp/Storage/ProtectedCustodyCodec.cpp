#include "ProtectedCustodyCodec.h"
#include "ProtectedCustodyPrimitives.h"

#include <algorithm>
#include <cstring>
#include <string>
#include <utility>

namespace graf::windows {
namespace {
using Codec = ProtectedCustodyCodec;
using Error = CustodyCodecError;
using custody_detail::digest;
using custody_detail::WipeBytes;
constexpr std::size_t envelopeHeader = 16, blockHeader = 104, indexHeader = 112;
constexpr std::uint16_t blockKind = 1, indexKind = 2;

template<class T> CustodyCodecResult<T> failure(Error error, std::uint32_t native = 0) {
    return {std::nullopt, error, native};
}
void put(CustodyBytes& out, std::size_t at, std::uint64_t value, std::size_t width) {
    for (std::size_t i = 0; i < width; ++i) out[at + i] = static_cast<std::uint8_t>(value >> (i * 8));
}
std::uint64_t get(const CustodyBytes& in, std::size_t at, std::size_t width) {
    std::uint64_t value = 0;
    for (std::size_t i = 0; i < width; ++i) value |= std::uint64_t{in[at + i]} << (i * 8);
    return value;
}
void initialize(CustodyBytes& out, const char* magic, const CustodyContext& c, std::size_t header) {
    std::memcpy(out.data(), magic, 8);
    put(out, 8, 1, 2); put(out, 10, static_cast<std::uint16_t>(c.role), 2); put(out, 12, header, 4);
    std::copy(c.storeId.begin(), c.storeId.end(), out.begin() + 16);
    std::copy(c.objectId.begin(), c.objectId.end(), out.begin() + 32);
}
bool headerMatches(const CustodyBytes& in, const char* magic, const CustodyContext& c, std::size_t header) {
    return in.size() >= header && std::memcmp(in.data(), magic, 8) == 0 &&
        get(in, 8, 2) == 1 && get(in, 10, 2) == static_cast<std::uint16_t>(c.role) &&
        get(in, 12, 4) == header &&
        std::equal(c.storeId.begin(), c.storeId.end(), in.begin() + 16) &&
        std::equal(c.objectId.begin(), c.objectId.end(), in.begin() + 32);
}
std::uint64_t blockCount(std::uint64_t length) {
    return length / Codec::blockBytes + (length % Codec::blockBytes != 0);
}
bool blockRequest(const CustodyContext& c, std::uint64_t position, std::uint64_t version,
                  std::uint32_t payloadBytes) {
    const auto limit = Codec::logicalLimit(c.role);
    return version != 0 && Codec::blockEnvelopeLimit(payloadBytes) != 0 &&
        position < blockCount(limit) && payloadBytes <= limit - position * Codec::blockBytes;
}
bool indexRequest(const CustodyContext& c, std::uint32_t slot, std::uint64_t generation, std::uint64_t length) {
    const auto limit = Codec::logicalLimit(c.role);
    return limit != 0 && slot <= 1 && generation != 0 && length <= limit &&
        (generation == 1 || (generation - 1) % 2 == slot);
}
bool entryValid(const CustodyIndexEntry& entry, std::uint32_t payloadBytes) {
    if (entry.flags == 1) return entry.version == 0 && entry.envelopeBytes == 0;
    return entry.flags == 0 && entry.version != 0 && entry.envelopeBytes > envelopeHeader &&
        entry.envelopeBytes <= Codec::blockEnvelopeLimit(payloadBytes);
}
bool entriesValid(const CustodyIndex& index) {
    if (index.entries.size() != blockCount(index.logicalLength)) return false;
    auto remaining = index.logicalLength;
    for (const auto& entry : index.entries) {
        const auto bytes = static_cast<std::uint32_t>(std::min(remaining, std::uint64_t{Codec::blockBytes}));
        if (!entryValid(entry, bytes)) return false;
        remaining -= bytes;
    }
    return true;
}

CustodyCodecResult<CustodyBytes> nativeTransform(
    const CustodyContext& c, std::uint16_t kind, std::uint64_t selector, std::uint64_t version,
    const std::uint8_t* bytes, std::size_t count, std::size_t outputLimit, bool protect) {
#ifdef _WIN32
    const std::string prefix = "graf.custody.v1";
    CustodyBytes entropy(prefix.begin(), prefix.end());
    entropy.insert(entropy.end(), c.storeId.begin(), c.storeId.end());
    entropy.insert(entropy.end(), c.objectId.begin(), c.objectId.end());
    const auto at = entropy.size(); entropy.resize(at + 20);
    put(entropy, at, static_cast<std::uint16_t>(c.role), 2); put(entropy, at + 2, kind, 2);
    put(entropy, at + 4, selector, 8); put(entropy, at + 12, version, 8);
    return custody_detail::nativeTransform(entropy.data(), entropy.size(), bytes, count, outputLimit, protect);
#else
    (void)c; (void)kind; (void)selector; (void)version; (void)bytes; (void)count; (void)outputLimit; (void)protect;
    return failure<CustodyBytes>(Error::unsupportedPlatform);
#endif
}
CustodyCodecResult<CustodyBytes> seal(
    const CustodyContext& c, std::uint16_t kind, std::uint64_t selector, std::uint64_t version,
    const CustodyBytes& plain, std::size_t envelopeLimit) {
    auto cipher = nativeTransform(c, kind, selector, version, plain.data(), plain.size(),
                                  envelopeLimit - envelopeHeader, true);
    if (!cipher.ok()) return cipher;
    CustodyBytes out(envelopeHeader + cipher.value->size());
    std::memcpy(out.data(), "GRAFDP01", 8); put(out, 8, 1, 2); put(out, 10, kind, 2);
    put(out, 12, cipher.value->size(), 4);
    std::copy(cipher.value->begin(), cipher.value->end(), out.begin() + envelopeHeader);
    return {std::move(out), Error::none, 0};
}
CustodyCodecResult<CustodyBytes> open(
    const CustodyContext& c, std::uint16_t kind, std::uint64_t selector, std::uint64_t version,
    const CustodyBytes& envelope, std::size_t envelopeLimit, std::size_t plainLimit) {
    if (envelope.size() <= envelopeHeader || envelope.size() > envelopeLimit ||
        std::memcmp(envelope.data(), "GRAFDP01", 8) != 0 || get(envelope, 8, 2) != 1 ||
        get(envelope, 10, 2) != kind || get(envelope, 12, 4) != envelope.size() - envelopeHeader)
        return failure<CustodyBytes>(Error::invalidEnvelope);
    return nativeTransform(c, kind, selector, version, envelope.data() + envelopeHeader,
                            envelope.size() - envelopeHeader, plainLimit, false);
}
} // namespace

std::uint64_t ProtectedCustodyCodec::logicalLimit(CustodyRole role) noexcept {
    switch (role) {
    case CustodyRole::canonical: case CustodyRole::media: case CustodyRole::playback: return std::uint64_t{64} << 30;
    case CustodyRole::manifest: return 4096;
    case CustodyRole::queue: return 4 * 1024 * 1024;
    case CustodyRole::recovery: case CustodyRole::packageState:
    case CustodyRole::bootstrap: case CustodyRole::migrationIntent: return 64 * 1024;
    }
    return 0;
}
std::size_t ProtectedCustodyCodec::blockEnvelopeLimit(std::uint32_t bytes) noexcept {
    return bytes != 0 && bytes <= blockBytes ? static_cast<std::size_t>(bytes) + 4096 : 0;
}
std::size_t ProtectedCustodyCodec::indexEnvelopeLimit(CustodyRole role) noexcept {
    const auto limit = logicalLimit(role);
    return limit == 0 ? 0 : 4096 + static_cast<std::size_t>(blockCount(limit)) * 16 + 65536;
}
CustodyCodecResult<CustodyBytes> ProtectedCustodyCodec::sealBlock(
    const CustodyContext& c, std::uint64_t position, std::uint64_t version, const CustodyBytes& payload) try {
    if (payload.size() > blockBytes || !blockRequest(c, position, version, static_cast<std::uint32_t>(payload.size())))
        return failure<CustodyBytes>(Error::invalidInput);
    const auto hash = digest(payload.data(), payload.size());
    if (!hash) return failure<CustodyBytes>(Error::hashFailed);
    CustodyBytes plain(blockHeader + payload.size()); WipeBytes wipe{plain};
    initialize(plain, "GRAFBL01", c, blockHeader);
    put(plain, 48, position, 8); put(plain, 56, version, 8); put(plain, 64, payload.size(), 4);
    std::copy(hash->begin(), hash->end(), plain.begin() + 72);
    std::copy(payload.begin(), payload.end(), plain.begin() + blockHeader);
    return seal(c, blockKind, position, version, plain, blockEnvelopeLimit(static_cast<std::uint32_t>(payload.size())));
} catch (const std::bad_alloc&) {
    return failure<CustodyBytes>(Error::allocationFailed);
}
CustodyCodecResult<CustodyBytes> ProtectedCustodyCodec::openBlock(
    const CustodyContext& c, std::uint64_t position, std::uint64_t version,
    std::uint32_t expected, const CustodyBytes& envelope) try {
    if (!blockRequest(c, position, version, expected)) return failure<CustodyBytes>(Error::invalidInput);
    auto result = open(c, blockKind, position, version, envelope, blockEnvelopeLimit(expected), blockHeader + expected);
    if (!result.ok()) return result;
    auto& plain = *result.value; WipeBytes wipe{plain};
    if (plain.size() != blockHeader + expected || !headerMatches(plain, "GRAFBL01", c, blockHeader) ||
        get(plain, 48, 8) != position || get(plain, 56, 8) != version ||
        get(plain, 64, 4) != expected || get(plain, 68, 4) != 0)
        return failure<CustodyBytes>(Error::invalidPlaintext);
    const auto hash = digest(plain.data() + blockHeader, expected);
    if (!hash) return failure<CustodyBytes>(Error::hashFailed);
    if (!std::equal(hash->begin(), hash->end(), plain.begin() + 72))
        return failure<CustodyBytes>(Error::invalidPlaintext);
    return {CustodyBytes(plain.begin() + blockHeader, plain.end()), Error::none, 0};
} catch (const std::bad_alloc&) {
    return failure<CustodyBytes>(Error::allocationFailed);
}
CustodyCodecResult<CustodyBytes> ProtectedCustodyCodec::sealIndex(
    const CustodyContext& c, std::uint32_t slot, const CustodyIndex& index) try {
    if (!indexRequest(c, slot, index.generation, index.logicalLength) || !entriesValid(index))
        return failure<CustodyBytes>(Error::invalidInput);
    CustodyBytes plain(indexHeader + index.entries.size() * 16); WipeBytes wipe{plain};
    initialize(plain, "GRAFIX01", c, indexHeader);
    put(plain, 48, index.generation, 8); put(plain, 56, index.logicalLength, 8);
    put(plain, 64, blockBytes, 4); put(plain, 68, index.entries.size(), 4);
    for (std::size_t i = 0; i < index.entries.size(); ++i) {
        const auto at = indexHeader + i * 16; const auto& entry = index.entries[i];
        put(plain, at, entry.version, 8); put(plain, at + 8, entry.envelopeBytes, 4); put(plain, at + 12, entry.flags, 4);
    }
    const auto hash = digest(plain.data(), plain.size());
    if (!hash) return failure<CustodyBytes>(Error::hashFailed);
    std::copy(hash->begin(), hash->end(), plain.begin() + 80);
    // The bound is specific to this exact entry count, not the largest allowed object.
    return seal(c, indexKind, slot, 0, plain, 4096 + index.entries.size() * 16 + 65536);
} catch (const std::bad_alloc&) {
    return failure<CustodyBytes>(Error::allocationFailed);
}
CustodyCodecResult<CustodyIndex> ProtectedCustodyCodec::openIndex(
    const CustodyContext& c, std::uint32_t slot, const CustodyBytes& envelope) try {
    const auto limit = logicalLimit(c.role);
    if (limit == 0 || slot > 1) return failure<CustodyIndex>(Error::invalidInput);
    auto result = open(c, indexKind, slot, 0, envelope, indexEnvelopeLimit(c.role),
                       indexHeader + static_cast<std::size_t>(blockCount(limit)) * 16);
    if (!result.ok()) return failure<CustodyIndex>(result.error, result.nativeError);
    auto& plain = *result.value; WipeBytes wipe{plain};
    if (!headerMatches(plain, "GRAFIX01", c, indexHeader) || get(plain, 64, 4) != blockBytes || get(plain, 72, 8) != 0)
        return failure<CustodyIndex>(Error::invalidPlaintext);
    const auto generation = get(plain, 48, 8), length = get(plain, 56, 8), count = get(plain, 68, 4);
    if (!indexRequest(c, slot, generation, length) || count != blockCount(length) ||
        plain.size() != indexHeader + static_cast<std::size_t>(count) * 16 ||
        envelope.size() > 4096 + static_cast<std::size_t>(count) * 16 + 65536)
        return failure<CustodyIndex>(Error::invalidPlaintext);
    std::array<std::uint8_t, 32> expected{};
    std::copy_n(plain.begin() + 80, expected.size(), expected.begin());
    std::fill(plain.begin() + 80, plain.begin() + indexHeader, std::uint8_t{0});
    const auto hash = digest(plain.data(), plain.size());
    if (!hash) return failure<CustodyIndex>(Error::hashFailed);
    if (*hash != expected) return failure<CustodyIndex>(Error::invalidPlaintext);
    // No allocation based on untrusted count until bounds, lengths and checksum pass.
    CustodyIndex index{generation, length, {}}; index.entries.reserve(static_cast<std::size_t>(count));
    for (std::size_t i = 0; i < count; ++i) {
        const auto at = indexHeader + i * 16;
        index.entries.push_back({get(plain, at, 8), static_cast<std::uint32_t>(get(plain, at + 8, 4)),
                                 static_cast<std::uint32_t>(get(plain, at + 12, 4))});
    }
    if (!entriesValid(index)) return failure<CustodyIndex>(Error::invalidPlaintext);
    return {std::move(index), Error::none, 0};
} catch (const std::bad_alloc&) {
    return failure<CustodyIndex>(Error::allocationFailed);
}
} // namespace graf::windows
