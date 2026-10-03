#include "../../RecApp/Storage/ProtectedPackedCustodyFormat.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <algorithm>
#include <array>
#include <cassert>
#include <limits>

using namespace graf::windows;
namespace {
using Format = ProtectedPackedCustodyFormat;
using Kind = PackedRecordKind;
PackedCustodyContext context() {
    PackedCustodyContext c{{{}, {}, CustodyRole::canonical}, {}};
    c.object.storeId.fill(0x11);
    c.object.objectId.fill(0x22);
    c.containerId.fill(0x33);
    return c;
}
void prefixTests() {
    const auto c = context();
    Format::Prefix golden{};
    const std::array<std::uint8_t, 8> magic{'G', 'R', 'F', 'P', 'C', 'V', '2', 0};
    std::copy(magic.begin(), magic.end(), golden.begin());
    golden[8] = 2; golden[12] = 128;
    std::fill(golden.begin() + 16, golden.begin() + 32, std::uint8_t{0x11});
    std::fill(golden.begin() + 32, golden.begin() + 48, std::uint8_t{0x22});
    std::fill(golden.begin() + 48, golden.begin() + 64, std::uint8_t{0x33});
    golden[66] = 4; golden[68] = 64; golden[70] = 3;
    golden[73] = 64; golden[76] = 64;
    const auto encoded = Format::encodePrefix(c);
    assert(encoded && *encoded == golden);
    assert(Format::prefixMatches(golden.data(), golden.size(), c));
    for (std::size_t i = 0; i < golden.size(); ++i) {
        auto corrupt = golden; corrupt[i] ^= 1;
        assert(!Format::prefixMatches(corrupt.data(), corrupt.size(), c));
    }
    assert(!Format::prefixMatches(golden.data(), 127, c));
    assert(!Format::prefixMatches(nullptr, 128, c));
    std::array<std::uint8_t, 129> extra{};
    std::copy(golden.begin(), golden.end(), extra.begin());
    assert(!Format::prefixMatches(extra.data(), extra.size(), c));
    for (unsigned role = 0; role < 12; ++role) {
        auto candidate = c; candidate.object.role = static_cast<CustodyRole>(role);
        assert(Format::encodePrefix(candidate).has_value() == (role >= 1 && role <= 3));
        assert(Format::prefixMatches(golden.data(), golden.size(), candidate) == (role >= 1 && role <= 3));
    }
    auto unknown = c; unknown.object.role = static_cast<CustodyRole>(65535);
    assert(!Format::encodePrefix(unknown) && !Format::prefixMatches(golden.data(), golden.size(), unknown));
}
PackedReference dataRef() {
    PackedReference r{Kind::data, 1024, Format::appendOffset, 7, 512, {}};
    r.envelopeSha.fill(0x5a); return r;
}
void referenceTests() {
    const auto r = dataRef();
    PackedReferenceBounds bounds{Kind::data, 512, 7, r.offset + 2048, r.offset + 1024};
    Format::Reference golden{};
    golden[0] = 1; golden[5] = 4;
    golden[8] = 0x80; golden[9] = 0x80; golden[16] = 7; golden[25] = 2;
    std::fill(golden.begin() + 32, golden.end(), std::uint8_t{0x5a});
    const auto encoded = Format::encodeReference(r);
    assert(encoded && *encoded == golden);
    const auto decoded = Format::decodeReference(golden.data(), golden.size(), bounds);
    assert(decoded && *decoded == r);
    assert(!Format::decodeReference(golden.data(), 63, bounds));
    assert(!Format::decodeReference(nullptr, 64, bounds));
    std::array<std::uint8_t, 65> extra{};
    std::copy(golden.begin(), golden.end(), extra.begin());
    assert(!Format::decodeReference(extra.data(), extra.size(), bounds));
    auto unknown = golden; unknown[3] = 0xff;
    assert(!Format::decodeReference(unknown.data(), unknown.size(), bounds));
    auto head = golden; head[0] = 5;
    assert(!Format::decodeReference(head.data(), head.size(), bounds));
    for (std::size_t i = 28; i < 32; ++i) {
        auto corrupt = golden; corrupt[i] = 1;
        assert(!Format::decodeReference(corrupt.data(), corrupt.size(), bounds));
    }
    auto bad = bounds;
    bad.generation = 8; assert(Format::decodeReference(golden.data(), golden.size(), bad));
    bad.payloadBytes = 511; assert(!Format::decodeReference(golden.data(), golden.size(), bad));
    bad = bounds; bad.generation = 6; assert(!Format::decodeReference(golden.data(), golden.size(), bad));
    bad = bounds; bad.generation = 0; assert(!Format::decodeReference(golden.data(), golden.size(), bad));
    bad = bounds; bad.parentOffset = bad.committedExtent + 1;
    assert(!Format::decodeReference(golden.data(), golden.size(), bad));
    bad = bounds; --bad.parentOffset; assert(!Format::decodeReference(golden.data(), golden.size(), bad));
    bad = bounds; bad.committedExtent = r.offset + 1023;
    assert(!Format::decodeReference(golden.data(), golden.size(), bad));
    bad = bounds; bad.kind = Kind::nodeL0; bad.payloadBytes = 0;
    assert(!Format::decodeReference(golden.data(), golden.size(), bad));
    const auto rejectRaw = [](const Format::Reference& bytes, PackedReferenceBounds limits) {
        assert(!Format::decodeReference(bytes.data(), bytes.size(), limits));
    };
    bad = bounds; bad.kind = static_cast<Kind>(0xff000001); rejectRaw(unknown, bad);
    bad = bounds; bad.kind = Kind::head; rejectRaw(head, bad);
    auto raw = golden;
    std::fill(raw.begin() + 16, raw.begin() + 24, std::uint8_t{0}); rejectRaw(raw, bounds);
    raw = golden; raw[8] = 0x81;
    bad = bounds; bad.parentOffset = bad.committedExtent; rejectRaw(raw, bad);
    raw = golden; raw[8] = 0x70; rejectRaw(raw, bounds);
    raw = golden; raw[4] = 16; raw[5] = 0; rejectRaw(raw, bounds);
    raw = golden; raw[4] = 1; raw[5] = 0x12;
    bad = bounds; bad.parentOffset = bad.committedExtent = r.offset + 8192; rejectRaw(raw, bad);
    raw = golden; raw[25] = 0; bad = bounds; bad.payloadBytes = 0; rejectRaw(raw, bad);
    raw = golden; raw[24] = 1; raw[25] = 0; raw[26] = 4;
    bad = bounds; bad.payloadBytes = Format::blockBytes + 1; rejectRaw(raw, bad);
    raw = golden; raw[0] = 2; raw[24] = 1; raw[25] = 0;
    bad = bounds; bad.kind = Kind::nodeL0; bad.payloadBytes = 1; rejectRaw(raw, bad);
    raw = golden; raw[0] = 2; raw[4] = 1; raw[5] = 0x20; raw[25] = 0;
    bad = {Kind::nodeL0, 0, 7, r.offset + 16384, r.offset + 16384}; rejectRaw(raw, bad);
    bad = bounds; bad.parentOffset = r.offset; rejectRaw(golden, bad);
    bad = bounds; bad.parentOffset = r.offset - 16; rejectRaw(golden, bad);
    bad = bounds; bad.parentOffset = Format::appendOffset - 1; rejectRaw(golden, bad);
    bad = bounds; bad.committedExtent = Format::appendOffset - 1; rejectRaw(golden, bad);
    const auto invalid = [&](PackedReference candidate) { assert(!Format::encodeReference(candidate)); };
    auto candidate = r; candidate.version = 0; invalid(candidate);
    candidate = r; ++candidate.offset; invalid(candidate);
    candidate = r; candidate.offset = Format::appendOffset - 16; invalid(candidate);
    candidate = r; candidate.envelopeBytes = 16; invalid(candidate);
    candidate = r; candidate.envelopeBytes = candidate.payloadBytes + 4097; invalid(candidate);
    candidate = r; candidate.payloadBytes = 0; invalid(candidate);
    candidate = r; candidate.payloadBytes = Format::blockBytes + 1; invalid(candidate);
    candidate = r; candidate.kind = Kind::head; invalid(candidate);
    candidate = r; candidate.kind = static_cast<Kind>(0xffffffff); invalid(candidate);
    // Extent checks use subtraction: an aligned UINT64_MAX-near offset must not wrap.
    candidate = r; candidate.offset = std::numeric_limits<std::uint64_t>::max() - 15;
    invalid(candidate);
    auto nearEnd = golden;
    std::fill(nearEnd.begin() + 8, nearEnd.begin() + 16, std::uint8_t{0xff}); nearEnd[8] = 0xf0;
    bad = bounds; bad.committedExtent = bad.parentOffset = std::numeric_limits<std::uint64_t>::max();
    assert(!Format::decodeReference(nearEnd.data(), nearEnd.size(), bad));
    candidate = r; candidate.payloadBytes = Format::blockBytes;
    candidate.envelopeBytes = Format::blockBytes + 4096;
    const auto fullBlock = Format::encodeReference(candidate); assert(fullBlock);
    bad = {Kind::data, Format::blockBytes, 7, r.offset + candidate.envelopeBytes, r.offset + candidate.envelopeBytes};
    assert(Format::decodeReference(fullBlock->data(), fullBlock->size(), bad));
    // Independent literal LE fixture: all eight offset/version bytes and large
    // u32 lengths. This must not rely only on agreement between encoder/decoder.
    candidate = r; candidate.offset = 0x0102030405060700ULL; candidate.version = 0x1122334455667788ULL;
    candidate.payloadBytes = Format::blockBytes; candidate.envelopeBytes = Format::blockBytes + 4096;
    auto largeGolden = golden;
    const std::array<std::uint8_t, 8> offsetBytes{0, 7, 6, 5, 4, 3, 2, 1};
    const std::array<std::uint8_t, 8> versionBytes{0x88, 0x77, 0x66, 0x55, 0x44, 0x33, 0x22, 0x11};
    std::copy(offsetBytes.begin(), offsetBytes.end(), largeGolden.begin() + 8);
    std::copy(versionBytes.begin(), versionBytes.end(), largeGolden.begin() + 16);
    largeGolden[4] = 0; largeGolden[5] = 0x10; largeGolden[6] = 4;
    largeGolden[24] = 0; largeGolden[25] = 0; largeGolden[26] = 4;
    const auto largeEncoded = Format::encodeReference(candidate);
    assert(largeEncoded && *largeEncoded == largeGolden);
    bad = {Kind::data, Format::blockBytes, candidate.version + 1,
        candidate.offset + candidate.envelopeBytes, candidate.offset + candidate.envelopeBytes};
    const auto largeDecoded = Format::decodeReference(largeGolden.data(), largeGolden.size(), bad);
    assert(largeDecoded && *largeDecoded == candidate);
    for (const auto kind : {Kind::nodeL0, Kind::nodeL1, Kind::nodeL2}) {
        candidate = r; candidate.kind = kind; candidate.payloadBytes = 0; candidate.envelopeBytes = 8192;
        auto node = Format::encodeReference(candidate); assert(node);
        bad = {kind, 0, 7, r.offset + 8192, r.offset + 8192};
        assert(Format::decodeReference(node->data(), node->size(), bad));
        ++candidate.envelopeBytes; invalid(candidate);
        candidate.envelopeBytes = 8192; candidate.payloadBytes = 1; invalid(candidate);
    }
    for (const auto kind : {Kind::empty, Kind::zero}) {
        const PackedReference inlineRef{kind, 0, 0, 0, 0, {}};
        const auto bytes = Format::encodeReference(inlineRef); assert(bytes);
        bad = {kind, 0, 1, Format::appendOffset, Format::appendOffset};
        const auto result = Format::decodeReference(bytes->data(), bytes->size(), bad);
        assert(result && *result == inlineRef);
        assert(!Format::decodeReference(bytes->data(), bytes->size(), bounds)); // No missing-DATA/implicit-ZERO fallback.
        for (std::size_t i = 4; i < bytes->size(); ++i) {
            auto corrupt = *bytes; corrupt[i] = 1;
            assert(!Format::decodeReference(corrupt.data(), corrupt.size(), bad));
        }
    }
    // Structural parsing deliberately does not establish cryptographic authority.
    auto differentDigest = golden; differentDigest[32] ^= 1;
    assert(Format::decodeReference(differentDigest.data(), differentDigest.size(), bounds));
}
void treeSemantics() {
    std::array<std::uint8_t, 128> body{};
    auto put = [&](std::size_t at, std::uint64_t value, unsigned count) {
        for (unsigned i = 0; i < count; ++i) body[at+i] = static_cast<std::uint8_t>(value >> (8*i));
    };
    put(0, 1, 8); put(16, Format::appendOffset, 8);
    put(24, Format::blockBytes, 4); put(32, 64, 4); put(36, 3, 4);
    auto decode = [&] { return Format::decodeDescriptor(body.data(), body.size(), 1, Format::appendOffset); };
    auto birth = decode(); assert(birth && birth->logicalBytes == 0 && birth->blockCount == 0);
    assert(Format::selectHeads({*birth, *birth}) == 0U);
    for (const auto at : {24, 28, 32, 36, 40, 112, 127}) {
        body[at] ^= 1; assert(!decode()); body[at] ^= 1;
    }
    assert(!Format::decodeDescriptor(body.data(), 127, 1, Format::appendOffset));
    assert(!Format::decodeDescriptor(nullptr, 128, 1, Format::appendOffset));
    assert(!Format::decodeDescriptor(body.data(), 128, 2, Format::appendOffset));
    assert(!Format::decodeDescriptor(body.data(), 128, 1, Format::appendOffset - 1));
    // Correctly shaped in-range root/tail, with actual EOF rather than rounded append position.
    PackedReference root{Kind::nodeL2, 1024, Format::appendOffset + 4096, 2, 0, {}};
    auto encoded = Format::encodeReference(root); assert(encoded);
    std::copy(encoded->begin(), encoded->end(), body.begin()+48);
    put(0, 2, 8); put(8, 7, 8); put(16, root.offset+root.envelopeBytes, 8); put(28, 1, 4);
    auto desc = Format::decodeDescriptor(body.data(), 128, 2, root.offset+root.envelopeBytes); assert(desc);
    assert(Format::selectHeads({*birth, *desc}) == 1U);
    assert(!Format::selectHeads({*desc, *birth})); // wrong slot
    assert(!Format::selectHeads({*desc, *desc})); // equal >g1
    auto gap = *desc; gap.generation = 4; assert(!Format::selectHeads({*birth, gap}));
    assert(!Format::decodeDescriptor(body.data(), 128, 2, root.offset+root.envelopeBytes-1));
    auto childWire = Format::encodeReference(PackedReference{Kind::zero, 0, 0, 0, 0, {}}); assert(childWire);
    assert(Format::decodeChild(childWire->data(), 64, *desc, root, 0, 0)); // ZERO may straddle EOF.
    assert(!Format::decodeChild(childWire->data(), 64, *desc, root, 0, 1)); // wholly beyond EOF
    assert(!Format::decodeChild(childWire->data(), 64, *desc, root, 1, 0)); // unaligned parent base
    assert(!Format::decodeChild(childWire->data(), 64, *desc, root, 0, 64));
    auto empty = Format::encodeReference(PackedReference{}); assert(empty);
    assert(!Format::decodeChild(empty->data(), 64, *desc, root, 0, 0));
    assert(Format::decodeChild(empty->data(), 64, *desc, root, 0, 1));
    PackedReference leaf{Kind::nodeL0, 1024, Format::appendOffset+2048, 2, 0, {}};
    auto data = dataRef(); data.version = 2; data.payloadBytes = 7;
    auto dataWire = Format::encodeReference(data); assert(dataWire);
    assert(Format::decodeChild(dataWire->data(), 64, *desc, leaf, 0, 0));
    data.payloadBytes = 8; dataWire = Format::encodeReference(data);
    assert(!Format::decodeChild(dataWire->data(), 64, *desc, leaf, 0, 0)); // exact tail
    put(8, Format::logicalLimit+1, 8); put(28, 262145, 4);
    assert(!Format::decodeDescriptor(body.data(), 128, 2, root.offset+root.envelopeBytes));
}
}
int main() {
    static_assert(Format::appendOffset == 32896);
    static_assert(Format::logicalLimit == 68719476736ULL);
    static_assert(sizeof(Format::Prefix) == 128 && sizeof(Format::Reference) == 64);
    assert(CustodyOwnedMemory::usedBytes() == 0);
    prefixTests(); referenceTests(); treeSemantics();
    assert(CustodyOwnedMemory::usedBytes() == 0);
}
