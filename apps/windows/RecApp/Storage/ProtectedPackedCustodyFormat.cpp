#include "ProtectedPackedCustodyFormat.h"
#include <algorithm>
#include <limits>

namespace graf::windows {
namespace {
using Format = ProtectedPackedCustodyFormat;
using Kind = PackedRecordKind;
template<std::size_t N> void put(std::array<std::uint8_t, N>& out,
    std::size_t at, std::uint64_t value, std::size_t width) noexcept {
    for (std::size_t i = 0; i < width; ++i) out[at + i] = static_cast<std::uint8_t>(value >> (i * 8));
}
std::uint64_t get(const std::uint8_t* in, std::size_t at, std::size_t width) noexcept {
    std::uint64_t value = 0;
    for (std::size_t i = 0; i < width; ++i) value |= std::uint64_t{in[at + i]} << (i * 8);
    return value;
}
bool inlineKind(Kind kind) noexcept { return kind == Kind::empty || kind == Kind::zero; }
bool nodeKind(Kind kind) noexcept {
    return kind == Kind::nodeL0 || kind == Kind::nodeL1 || kind == Kind::nodeL2;
}
bool validShape(const PackedReference& r) noexcept {
    if (inlineKind(r.kind)) return r.envelopeBytes == 0 && r.offset == 0 && r.version == 0 &&
        r.payloadBytes == 0 && r.envelopeSha == std::array<std::uint8_t, 32>{};
    if (r.kind != Kind::data && !nodeKind(r.kind)) return false;
    if (r.offset < Format::appendOffset || r.offset % 16 != 0 || r.version == 0 || r.envelopeBytes <= 16 ||
        r.offset > std::numeric_limits<std::uint64_t>::max() - r.envelopeBytes) return false;
    if (r.kind == Kind::data) return r.payloadBytes > 0 && r.payloadBytes <= Format::blockBytes &&
        r.envelopeBytes <= r.payloadBytes + 4096;
    return r.payloadBytes == 0 && r.envelopeBytes <= 8192;
}
}
std::optional<ProtectedPackedCustodyFormat::Prefix>
ProtectedPackedCustodyFormat::encodePrefix(const PackedCustodyContext& c) noexcept {
    if (c.object.role != CustodyRole::canonical && c.object.role != CustodyRole::media &&
        c.object.role != CustodyRole::playback) return std::nullopt;
    Prefix out{};
    const std::array<std::uint8_t, 8> magic{'G', 'R', 'F', 'P', 'C', 'V', '2', 0};
    std::copy(magic.begin(), magic.end(), out.begin());
    put(out, 8, 2, 4); put(out, 12, 128, 4);
    std::copy(c.object.storeId.begin(), c.object.storeId.end(), out.begin() + 16);
    std::copy(c.object.objectId.begin(), c.object.objectId.end(), out.begin() + 32);
    std::copy(c.containerId.begin(), c.containerId.end(), out.begin() + 48);
    put(out, 64, blockBytes, 4); put(out, 68, 64, 2); put(out, 70, 3, 2);
    put(out, 72, 16384, 4); put(out, 76, 64, 4);
    return out;
}
bool ProtectedPackedCustodyFormat::prefixMatches(
    const std::uint8_t* bytes, std::size_t count, const PackedCustodyContext& c) noexcept {
    if (!bytes || count != Prefix{}.size()) return false;
    const auto expected = encodePrefix(c);
    return expected && std::equal(expected->begin(), expected->end(), bytes);
}
std::optional<ProtectedPackedCustodyFormat::Reference>
ProtectedPackedCustodyFormat::encodeReference(const PackedReference& r) noexcept {
    if (!validShape(r)) return std::nullopt;
    Reference out{};
    put(out, 0, static_cast<std::uint32_t>(r.kind), 4); put(out, 4, r.envelopeBytes, 4);
    put(out, 8, r.offset, 8); put(out, 16, r.version, 8); put(out, 24, r.payloadBytes, 4);
    std::copy(r.envelopeSha.begin(), r.envelopeSha.end(), out.begin() + 32);
    return out;
}
std::optional<PackedReference> ProtectedPackedCustodyFormat::decodeReference(
    const std::uint8_t* bytes, std::size_t count, const PackedReferenceBounds& b) noexcept {
    if (!bytes || count != Reference{}.size() || get(bytes, 28, 4) != 0 || b.generation == 0 ||
        b.committedExtent < appendOffset || b.parentOffset < appendOffset ||
        b.parentOffset > b.committedExtent) return std::nullopt;
    PackedReference r{static_cast<Kind>(get(bytes, 0, 4)), static_cast<std::uint32_t>(get(bytes, 4, 4)),
        get(bytes, 8, 8), get(bytes, 16, 8), static_cast<std::uint32_t>(get(bytes, 24, 4)), {}};
    std::copy(bytes + 32, bytes + 64, r.envelopeSha.begin());
    if (!validShape(r) || r.kind != b.kind || r.payloadBytes != b.payloadBytes) return std::nullopt;
    if (!inlineKind(r.kind) && (r.version > b.generation || r.offset > b.parentOffset ||
        r.envelopeBytes > b.parentOffset - r.offset)) return std::nullopt;
    return r;
}
std::optional<PackedRootDescriptor> ProtectedPackedCustodyFormat::decodeDescriptor(
    const std::uint8_t* bytes, std::size_t count, std::uint64_t version, std::uint64_t actualBytes) noexcept {
    if (!bytes || count != 128 || !version || get(bytes, 0, 8) != version ||
        get(bytes, 8, 8) > logicalLimit || get(bytes, 16, 8) < appendOffset ||
        get(bytes, 16, 8) > actualBytes || get(bytes, 24, 4) != blockBytes ||
        get(bytes, 32, 4) != 64 || get(bytes, 36, 4) != 3 || get(bytes, 40, 8) != 0 ||
        std::any_of(bytes+112, bytes+128, [](std::uint8_t b) { return b != 0; })) return std::nullopt;
    const auto length = get(bytes, 8, 8), extent = get(bytes, 16, 8);
    const auto blocks = static_cast<std::uint32_t>((length + blockBytes - 1) / blockBytes);
    if (get(bytes, 28, 4) != blocks) return std::nullopt;
    auto root = decodeReference(bytes+48, 64, {blocks ? Kind::nodeL2 : Kind::empty, 0, version, extent, extent});
    if (!root) return std::nullopt;
    // g1 is exclusively the exact empty birth, never a nonempty or recovered generation.
    if (version == 1 && (length != 0 || extent != appendOffset)) return std::nullopt;
    return PackedRootDescriptor{version, length, extent, blocks, *root};
}
std::optional<std::uint32_t> ProtectedPackedCustodyFormat::selectHeads(
    const std::array<PackedRootDescriptor, 2>& heads) noexcept {
    const auto a = heads[0].generation, b = heads[1].generation;
    if (!a || !b) return std::nullopt;
    if (a == b) return a == 1 && heads[0] == heads[1] && heads[0].logicalBytes == 0 &&
        heads[0].root.kind == Kind::empty && heads[0].committedExtent == appendOffset ?
        std::optional<std::uint32_t>{0} : std::nullopt;
    if ((a-1)%2 != 0 || (b-1)%2 != 1) return std::nullopt;
    const auto selected = a > b ? 0U : 1U;
    const auto& newer = heads[selected]; const auto& older = heads[1-selected];
    if (newer.generation - older.generation != 1 || newer.committedExtent < older.committedExtent)
        return std::nullopt;
    return selected;
}
std::optional<PackedReference> ProtectedPackedCustodyFormat::decodeChild(
    const std::uint8_t* bytes, std::size_t count, const PackedRootDescriptor& descriptor,
    const PackedReference& parent, std::uint64_t base, std::uint32_t slot) noexcept {
    if (!bytes || count != 64 || slot >= 64 || !nodeKind(parent.kind) || !validShape(parent) ||
        parent.version > descriptor.generation || parent.offset > descriptor.committedExtent ||
        parent.envelopeBytes > descriptor.committedExtent-parent.offset) return std::nullopt;
    const std::uint64_t span = parent.kind == Kind::nodeL2 ? 262144 : parent.kind == Kind::nodeL1 ? 4096 : 64;
    if (base % span || base > 262144-span) return std::nullopt;
    const auto firstBlock = base + slot*(span/64);
    const auto kind = static_cast<Kind>(get(bytes, 0, 4));
    Kind expected;
    std::uint32_t payload = 0;
    if (firstBlock >= descriptor.blockCount) expected = Kind::empty;
    else if (kind == Kind::zero) expected = Kind::zero;
    else if (parent.kind == Kind::nodeL0) {
        expected = Kind::data;
        payload = static_cast<std::uint32_t>(std::min<std::uint64_t>(blockBytes,
            descriptor.logicalBytes - firstBlock*blockBytes));
    } else expected = parent.kind == Kind::nodeL2 ? Kind::nodeL1 : Kind::nodeL0;
    return decodeReference(bytes, count, {expected, payload, descriptor.generation,
        descriptor.committedExtent, parent.offset});
}
} // namespace graf::windows
