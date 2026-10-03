#pragma once

#include "ProtectedCustodyCodec.h"
#include <array>
#include <optional>

namespace graf::windows {

enum class PackedRecordKind : std::uint32_t {
    empty = 0, data = 1, nodeL0 = 2, nodeL1 = 3, nodeL2 = 4, head = 5, zero = 6,
};
struct PackedCustodyContext {
    CustodyContext object;
    CustodyId containerId;
};
struct PackedReference {
    PackedRecordKind kind = PackedRecordKind::empty;
    std::uint32_t envelopeBytes = 0;
    std::uint64_t offset = 0;
    std::uint64_t version = 0;
    std::uint32_t payloadBytes = 0;
    std::array<std::uint8_t, 32> envelopeSha{};
    bool operator==(const PackedReference& other) const noexcept {
        return kind == other.kind && envelopeBytes == other.envelopeBytes &&
            offset == other.offset && version == other.version &&
            payloadBytes == other.payloadBytes && envelopeSha == other.envelopeSha;
    }
};
struct PackedReferenceBounds {
    PackedRecordKind kind;
    std::uint32_t payloadBytes;
    std::uint64_t generation;
    std::uint64_t committedExtent;
    // Child must end before its append-region parent. For a HEAD root this is
    // the committed extent, not the physical HEAD-cell offset before the tree.
    std::uint64_t parentOffset;
};
// Parsed wire value, NEVER a verified root/proof or publication authority.
struct PackedRootDescriptor {
    std::uint64_t generation = 0;
    std::uint64_t logicalBytes = 0;
    std::uint64_t committedExtent = 0;
    std::uint32_t blockCount = 0;
    PackedReference root;
    bool operator==(const PackedRootDescriptor& other) const noexcept {
        return generation == other.generation && logicalBytes == other.logicalBytes &&
            committedExtent == other.committedExtent && blockCount == other.blockCount && root == other.root;
    }
};

// Structural wire primitives only: no I/O, DPAPI, hash verification or proof.
// A parsed reference/prefix is NOT authority. The owner/tree layer must verify
// expected role, path/selector, explicit ZERO/EOF semantics and envelope SHA
// before decrypting/using records. These functions allocate no heap memory.
class ProtectedPackedCustodyFormat final {
public:
    using Prefix = std::array<std::uint8_t, 128>;
    using Reference = std::array<std::uint8_t, 64>;
    static constexpr std::uint32_t blockBytes = ProtectedCustodyCodec::blockBytes;
    static constexpr std::uint64_t appendOffset = 32896;
    static constexpr std::uint64_t logicalLimit = 68719476736ULL;
    [[nodiscard]] static std::optional<Prefix> encodePrefix(const PackedCustodyContext&) noexcept;
    [[nodiscard]] static bool prefixMatches(
        const std::uint8_t*, std::size_t, const PackedCustodyContext&) noexcept;
    [[nodiscard]] static std::optional<Reference> encodeReference(const PackedReference&) noexcept;
    [[nodiscard]] static std::optional<PackedReference> decodeReference(
        const std::uint8_t*, std::size_t, const PackedReferenceBounds&) noexcept;
    [[nodiscard]] static std::optional<PackedRootDescriptor> decodeDescriptor(
        const std::uint8_t*, std::size_t, std::uint64_t headVersion, std::uint64_t actualFileBytes) noexcept;
    [[nodiscard]] static std::optional<std::uint32_t> selectHeads(
        const std::array<PackedRootDescriptor, 2>&) noexcept;
    // Expected base/level comes from the authenticated parent path, not child bytes.
    [[nodiscard]] static std::optional<PackedReference> decodeChild(
        const std::uint8_t*, std::size_t, const PackedRootDescriptor&,
        const PackedReference& parent, std::uint64_t nodeBase, std::uint32_t slot) noexcept;
};

} // namespace graf::windows
