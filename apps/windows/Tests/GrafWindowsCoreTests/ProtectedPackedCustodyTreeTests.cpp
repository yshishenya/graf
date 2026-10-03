#include "../../RecApp/Storage/ProtectedPackedCustodyTree.h"
#include "../../RecApp/Storage/ProtectedCustodyPrimitives.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <type_traits>

using namespace graf::windows;
using Tree = ProtectedPackedCustodyTree;
using Format = ProtectedPackedCustodyFormat;
using Kind = PackedRecordKind;

static_assert(!std::is_constructible_v<Tree, PackedRootDescriptor>);
static_assert(!std::is_nothrow_move_constructible_v<CustodyBytes>);
static_assert(!std::is_nothrow_move_constructible_v<PackedPlainRead>);

#ifdef _WIN32
#include <windows.h>
#include <sddl.h>
#include <objbase.h>
#include <vector>
#ifdef _DEBUG
#include <crtdbg.h>
#endif

namespace {
void put32(CustodyBytes& bytes, std::size_t at, std::uint32_t value) {
    assert(at + 4 <= bytes.size());
    for (unsigned i = 0; i < 4; ++i)
        bytes[at + i] = static_cast<std::uint8_t>(value >> (8 * i));
}
void put64(CustodyBytes& bytes, std::size_t at, std::uint64_t value) {
    assert(at + 8 <= bytes.size());
    for (unsigned i = 0; i < 8; ++i)
        bytes[at + i] = static_cast<std::uint8_t>(value >> (8 * i));
}
void putRef(CustodyBytes& bytes, std::size_t at, const PackedReference& ref) {
    const auto wire = Format::encodeReference(ref);
    assert(wire && at + wire->size() <= bytes.size());
    std::copy(wire->begin(), wire->end(), bytes.begin() + at);
}
PackedReference zeroRef() {
    PackedReference ref;
    ref.kind = Kind::zero;
    return ref;
}

// Only this generated TempGUID directory is removed. No user inventory/devices.
struct Fixture {
    std::filesystem::path root;
    PSECURITY_DESCRIPTOR descriptor = nullptr;
    SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), nullptr, FALSE};
    PackedCustodyContext context{{{}, {}, CustodyRole::canonical}, {}};

    Fixture() {
        HANDLE token = nullptr;
        assert(OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token));
        DWORD count = 0;
        assert(!GetTokenInformation(token, TokenUser, nullptr, 0, &count));
        assert(GetLastError() == ERROR_INSUFFICIENT_BUFFER && count != 0);
        std::vector<std::uint8_t> bytes(count);
        assert(GetTokenInformation(token, TokenUser, bytes.data(), count, &count));
        assert(CloseHandle(token));
        LPWSTR sid = nullptr;
        assert(ConvertSidToStringSidW(reinterpret_cast<TOKEN_USER*>(bytes.data())->User.Sid, &sid));
        const auto sddl = std::wstring(L"D:P(A;OICI;FA;;;") + sid + L")";
        LocalFree(sid);
        assert(ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl.c_str(), SDDL_REVISION_1, &descriptor, nullptr));
        security.lpSecurityDescriptor = descriptor;
        wchar_t temporary[MAX_PATH]{}, actual[MAX_PATH]{};
        const auto length = GetTempPathW(MAX_PATH, temporary);
        assert(length != 0 && length < MAX_PATH);
        const auto expanded = GetLongPathNameW(temporary, actual, MAX_PATH);
        assert(expanded != 0 && expanded < MAX_PATH);
        GUID id{};
        wchar_t text[40]{};
        assert(CoCreateGuid(&id) == S_OK && StringFromGUID2(id, text, 40));
        root = std::filesystem::path(actual) / (std::wstring(L"graf-packed-tree-") + text);
        assert(CreateDirectoryW(root.c_str(), &security));
        assert(CreateDirectoryW((root / L".custody-v1").c_str(), &security));
        assert(CreateDirectoryW((root / L"package-a").c_str(), &security));
        context.object.storeId.fill(0x17);
        context.object.objectId.fill(0x29);
        context.containerId.fill(0x3b);
        HANDLE file = CreateFileW((root / L".custody-v1" / L"store.id").c_str(),
            GENERIC_WRITE, 0, &security, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
        assert(file != INVALID_HANDLE_VALUE);
        DWORD written = 0;
        assert(WriteFile(file, context.object.storeId.data(), 16, &written, nullptr) && written == 16);
        assert(FlushFileBuffers(file));
        assert(CloseHandle(file));
    }
    ~Fixture() {
        std::error_code error;
        std::filesystem::remove_all(root, error);
        assert(!error);
        LocalFree(descriptor);
    }
    Fixture(const Fixture&) = delete;
    Fixture& operator=(const Fixture&) = delete;

    auto open(CustodyFileAccess access) const {
        return ProtectedPackedCustodyOwner::open(root, "package-a", context, access);
    }
    auto create() const {
        auto result = open(CustodyFileAccess::createNew);
        assert(result.ok());
        return std::move(*result.value);
    }
    auto content() const {
        return root / L"package-a" / L".custody-v1" / L"canonical" / L"content.packed-v2";
    }
    void denyExternalWriter() const {
        HANDLE file = CreateFileW(content().c_str(), GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        assert(file == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
    }
    // Called only after every owner/proof/read result has released its handles.
    void corrupt(std::uint64_t offset) const {
        HANDLE file = CreateFileW(content().c_str(), GENERIC_READ | GENERIC_WRITE,
            0, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        assert(file != INVALID_HANDLE_VALUE);
        assert(offset <= static_cast<std::uint64_t>(std::numeric_limits<LONGLONG>::max()));
        LARGE_INTEGER position{};
        position.QuadPart = static_cast<LONGLONG>(offset);
        assert(SetFilePointerEx(file, position, nullptr, FILE_BEGIN));
        std::uint8_t byte = 0;
        DWORD done = 0;
        assert(ReadFile(file, &byte, 1, &done, nullptr) && done == 1);
        byte ^= 0x80;
        assert(SetFilePointerEx(file, position, nullptr, FILE_BEGIN));
        assert(WriteFile(file, &byte, 1, &done, nullptr) && done == 1);
        assert(FlushFileBuffers(file));
        assert(CloseHandle(file));
    }
    void copyHeadToWrongSlot() const {
        HANDLE file = CreateFileW(content().c_str(), GENERIC_READ | GENERIC_WRITE,
            0, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        assert(file != INVALID_HANDLE_VALUE);
        CustodyBytes cell(16384, 0);
        LARGE_INTEGER position{};
        position.QuadPart = 16512;
        DWORD done = 0;
        assert(SetFilePointerEx(file, position, nullptr, FILE_BEGIN));
        assert(ReadFile(file, cell.data(), 16384, &done, nullptr) && done == 16384);
        position.QuadPart = 128;
        assert(SetFilePointerEx(file, position, nullptr, FILE_BEGIN));
        assert(WriteFile(file, cell.data(), 16384, &done, nullptr) && done == 16384);
        assert(FlushFileBuffers(file));
        assert(CloseHandle(file));
    }
    PackedReference append(const std::shared_ptr<ProtectedPackedCustodyOwner>& owner,
        Kind kind, std::uint64_t selector, std::uint64_t version, const CustodyBytes& body) const {
        const auto position = owner->appendPosition();
        assert(position.ok() && body.size() <= Format::blockBytes);
        const PackedRecordAddress address{kind, *position.value, selector, version,
            static_cast<std::uint32_t>(body.size())};
        auto sealed = ProtectedPackedCustodyCodec::seal(context, address, body);
        assert(sealed.ok());
        const auto digest = custody_detail::digest(sealed.value->data(), sealed.value->size());
        assert(digest);
        const auto result = owner->append(address, *sealed.value);
        assert(result.ok() && *result.value == sealed.value->size());
        return {kind, static_cast<std::uint32_t>(sealed.value->size()), address.offset,
            version, kind == Kind::data ? address.bodyBytes : 0, *digest};
    }
    PackedReference node(const std::shared_ptr<ProtectedPackedCustodyOwner>& owner,
        Kind kind, std::uint64_t base, std::uint64_t version, const PackedReference& first,
        std::uint32_t slot = 0) const {
        CustodyBytes body(4096, 0);
        assert(slot < 64);
        putRef(body, std::size_t{slot} * 64, first);
        return append(owner, kind, base, version, body);
    }
    PackedReference path(const std::shared_ptr<ProtectedPackedCustodyOwner>& owner,
        std::uint64_t version, const PackedReference& data, std::uint64_t leafBase = 0) const {
        const auto leaf = node(owner, Kind::nodeL0, leafBase, version, data);
        const auto middle = node(owner, Kind::nodeL1, 0, version, leaf);
        return node(owner, Kind::nodeL2, 0, version, middle);
    }
    CustodyBytes headBody(std::uint64_t version, std::uint64_t logicalBytes,
        const PackedReference& rootRef) const {
        CustodyBytes body(128, 0);
        put64(body, 0, version);
        put64(body, 8, logicalBytes);
        // Exact actual EOF, not rounded appendPosition(). Root is the last record.
        put64(body, 16, rootRef.offset + rootRef.envelopeBytes);
        put32(body, 24, Format::blockBytes);
        put32(body, 28, static_cast<std::uint32_t>((logicalBytes + Format::blockBytes - 1) / Format::blockBytes));
        put32(body, 32, 64);
        put32(body, 36, 3);
        putRef(body, 48, rootRef);
        return body;
    }
    void publish(const std::shared_ptr<ProtectedPackedCustodyOwner>& owner,
        std::uint32_t slot, std::uint64_t version, const CustodyBytes& body) const {
        assert(owner->flush().ok());
        const PackedRecordAddress address{Kind::head, slot == 0 ? 128ULL : 16512ULL,
            slot, version, 128};
        const auto cell = ProtectedPackedCustodyCodec::seal(context, address, body);
        assert(cell.ok());
        const auto result = owner->publishHead(slot, *cell.value);
        assert(result.state == CustodyPublishState::published);
        // Physical fixture publication only: no logical commit/ACK claim.
    }
    PackedReference tail(const std::shared_ptr<ProtectedPackedCustodyOwner>& owner,
        std::uint64_t version, const CustodyBytes& bytes) const {
        const auto data = append(owner, Kind::data, 0, version, bytes);
        const auto rootRef = path(owner, version, data);
        publish(owner, static_cast<std::uint32_t>((version - 1) % 2), version,
            headBody(version, bytes.size(), rootRef));
        return data;
    }
};

auto verified(const std::shared_ptr<ProtectedPackedCustodyOwner>& owner,
    std::uint64_t generation, std::uint64_t bytes, std::uint32_t slot) {
    auto result = Tree::verify(owner);
    assert(result.ok());
    auto tree = std::move(*result.value);
    assert(tree && tree->generation() == generation && tree->logicalBytes() == bytes && tree->selectedSlot() == slot);
    return tree;
}
void noBytesBeyondEOF(const std::shared_ptr<const Tree>& tree, std::uint64_t block) {
    const auto result = tree->readBlock(block);
    // Block-level API may reject an absent block or return EOF; never synthesize bytes.
    assert(result.ok() ? result.value->bytes.empty() : result.error == CustodyFileError::invalidInput);
}
void rejectsAndLatches(const std::shared_ptr<ProtectedPackedCustodyOwner>& owner) {
    const auto result = Tree::verify(owner);
    assert(!result.ok() && result.error != CustodyFileError::none);
    const auto repeated = Tree::verify(owner);
    assert(!repeated.ok() && repeated.error == result.error && repeated.nativeError == result.nativeError);
    const auto physical = owner->readCiphertext(0, 128);
    assert(!physical.ok() && physical.error == result.error && physical.nativeError == result.nativeError);
    assert(!owner->flush().ok());
}

void birth() {
    Fixture fixture;
    auto owner = fixture.create();
    auto tree = verified(owner, 1, 0, 0);
    fixture.denyExternalWriter();
    noBytesBeyondEOF(tree, 0);
    noBytesBeyondEOF(tree, std::numeric_limits<std::uint64_t>::max());
    owner->revokeWrites();
    auto again = Tree::verify(owner);
    assert(again.ok() && (*again.value)->generation() == 1);
    assert(owner->readCiphertext(0, 128).ok());
}
void dataPairAndReopen() {
    Fixture fixture;
    auto owner = fixture.create();
    const CustodyBytes first{0x19, 0x27, 0x35};
    fixture.tail(owner, 2, first);
    {
        const auto tree = verified(owner, 2, first.size(), 1);
        const auto read = tree->readBlock(0);
        assert(read.ok() && read.value->bytes == first);
        noBytesBeyondEOF(tree, 1); // Remaining refs in all three nodes are EMPTY.
    }
    const CustodyBytes next{0x41, 0x52, 0x63, 0x74};
    fixture.tail(owner, 3, next);
    {
        const auto tree = verified(owner, 3, next.size(), 0);
        const auto read = tree->readBlock(0);
        assert(read.ok() && read.value->bytes == next);
    }
    const auto epoch = owner->epoch();
    owner.reset();
    auto reopened = fixture.open(CustodyFileAccess::readExisting);
    assert(reopened.ok() && (*reopened.value)->epoch() != epoch);
    const auto tree = verified(*reopened.value, 3, next.size(), 0);
    const auto read = tree->readBlock(0);
    assert(read.ok() && read.value->bytes == next);
}
void zeroAndTail() {
    Fixture fixture;
    auto owner = fixture.create();
    CustodyBytes leafBody(4096, 0);
    putRef(leafBody, 0, zeroRef()); // Explicit first full zero block.
    const CustodyBytes tailBytes{1, 3, 5, 7, 9, 11, 13};
    const auto data = fixture.append(owner, Kind::data, 1, 2, tailBytes);
    putRef(leafBody, 64, data);
    const auto leaf = fixture.append(owner, Kind::nodeL0, 0, 2, leafBody);
    const auto middle = fixture.node(owner, Kind::nodeL1, 0, 2, leaf);
    const auto root = fixture.node(owner, Kind::nodeL2, 0, 2, middle);
    fixture.publish(owner, 1, 2, fixture.headBody(2, Format::blockBytes + tailBytes.size(), root));
    const auto tree = verified(owner, 2, Format::blockBytes + tailBytes.size(), 1);
    {
        const auto read = tree->readBlock(0);
        assert(read.ok() && read.value->bytes.size() == Format::blockBytes);
        assert(std::all_of(read.value->bytes.begin(), read.value->bytes.end(), [](auto byte) { return byte == 0; }));
    }
    const auto read = tree->readBlock(1);
    assert(read.ok() && read.value->bytes == tailBytes);
    noBytesBeyondEOF(tree, 2);
}
void largeInlineZero() {
    Fixture fixture;
    auto owner = fixture.create();
    // One root node, ZERO subtree crosses EOF; no 64GiB data fixture/flat array.
    const auto root = fixture.node(owner, Kind::nodeL2, 0, 2, zeroRef());
    const std::uint64_t length = std::uint64_t{4096} * Format::blockBytes - 1;
    fixture.publish(owner, 1, 2, fixture.headBody(2, length, root));
    const auto before = CustodyOwnedMemory::usedBytes();
    const auto tree = verified(owner, 2, length, 1);
    // Retained allocation check only; this is not peak/native-allocation evidence.
    assert(CustodyOwnedMemory::usedBytes() - before < 1024 * 1024);
    const auto read = tree->readBlock(4095);
    assert(read.ok() && read.value->bytes.size() == Format::blockBytes - 1);
    assert(std::all_of(read.value->bytes.begin(), read.value->bytes.end(), [](auto byte) { return byte == 0; }));
    noBytesBeyondEOF(tree, 4096);
}

enum class BadDescriptor { count, blockSize, radix, depth, flags, reserved, extent, shortExtent, tail, emptyRoot, zeroRoot };
void descriptors() {
    for (const auto bad : {BadDescriptor::count, BadDescriptor::blockSize, BadDescriptor::radix,
        BadDescriptor::depth, BadDescriptor::flags, BadDescriptor::reserved, BadDescriptor::extent,
        BadDescriptor::shortExtent, BadDescriptor::tail, BadDescriptor::emptyRoot, BadDescriptor::zeroRoot}) {
        Fixture fixture;
        auto owner = fixture.create();
        const auto data = fixture.append(owner, Kind::data, 0, 2, CustodyBytes{2, 4, 6});
        const auto root = fixture.path(owner, 2, data);
        auto body = fixture.headBody(2, 3, root);
        switch (bad) {
        case BadDescriptor::count: put32(body, 28, 2); break;
        case BadDescriptor::blockSize: put32(body, 24, Format::blockBytes - 1); break;
        case BadDescriptor::radix: put32(body, 32, 63); break;
        case BadDescriptor::depth: put32(body, 36, 2); break;
        case BadDescriptor::flags: body[40] = 1; break;
        case BadDescriptor::reserved: body[127] = 1; break;
        case BadDescriptor::extent: put64(body, 16, root.offset + root.envelopeBytes + 1); break;
        case BadDescriptor::shortExtent: put64(body, 16, root.offset + root.envelopeBytes - 1); break;
        case BadDescriptor::tail: put64(body, 8, 4); break;
        case BadDescriptor::emptyRoot: putRef(body, 48, PackedReference{}); break;
        case BadDescriptor::zeroRoot: putRef(body, 48, zeroRef()); break;
        }
        fixture.publish(owner, 1, 2, body);
        rejectsAndLatches(owner);
    }
}
enum class BadShape { base, level, emptyInside, dataOutside, childSHA, rootSHA, forward };
void shapes() {
    for (const auto bad : {BadShape::base, BadShape::level, BadShape::emptyInside,
        BadShape::dataOutside, BadShape::childSHA, BadShape::rootSHA, BadShape::forward}) {
        Fixture fixture;
        auto owner = fixture.create();
        auto data = fixture.append(owner, Kind::data, 0, 2, CustodyBytes{0x24, 0x46, 0x68});
        if (bad == BadShape::childSHA) data.envelopeSha[0] ^= 1;
        if (bad == BadShape::forward) {
            const auto position = owner->appendPosition();
            assert(position.ok());
            data.offset = *position.value; // Child points at its own would-be parent.
        }
        if (bad == BadShape::emptyInside) data = PackedReference{};
        CustodyBytes leafBody(4096, 0);
        if (bad == BadShape::dataOutside) putRef(leafBody, 0, zeroRef());
        putRef(leafBody, bad == BadShape::dataOutside ? 64 : 0, data);
        auto leaf = fixture.append(owner, bad == BadShape::level ? Kind::nodeL1 : Kind::nodeL0,
            bad == BadShape::base ? 64 : 0, 2, leafBody);
        const auto middle = fixture.node(owner, Kind::nodeL1, 0, 2, leaf);
        auto root = fixture.node(owner, Kind::nodeL2, 0, 2, middle);
        if (bad == BadShape::rootSHA) root.envelopeSha[31] ^= 1;
        fixture.publish(owner, 1, 2, fixture.headBody(2, 3, root));
        rejectsAndLatches(owner);
        // SHA mutations keep stored records valid; no claim of instrumented DPAPI ordering.
    }
}
void pairs() {
    for (unsigned bad = 0; bad < 3; ++bad) {
        Fixture fixture;
        auto owner = fixture.create();
        const auto data = fixture.append(owner, Kind::data, 0, 2, CustodyBytes{1, 2, 3});
        const auto root = fixture.path(owner, 2, data);
        if (bad == 0) {
            fixture.publish(owner, 1, 2, fixture.headBody(2, 3, root));
            owner.reset();
            // seal() itself rejects g2/slot0: relocate the valid slot1 cell only
            // after releasing the guard, as synthetic at-rest tampering.
            fixture.copyHeadToWrongSlot();
            auto reopened = fixture.open(CustodyFileAccess::readExisting);
            assert(reopened.ok());
            owner = std::move(*reopened.value);
        } else if (bad == 1) {
            fixture.publish(owner, 1, 2, fixture.headBody(2, 3, root));
            fixture.publish(owner, 0, 3, fixture.headBody(2, 3, root)); // HEAD version != descriptor generation.
        } else {
            fixture.publish(owner, 0, 3, fixture.headBody(3, 3, root)); // g1/g3, nonadjacent.
        }
        rejectsAndLatches(owner);
    }
}
void currentAndLowerCorruption() {
    for (const bool lowerPeer : {false, true}) {
        Fixture fixture;
        auto owner = fixture.create();
        const auto oldData = fixture.tail(owner, 2, CustodyBytes{0x21, 0x43, 0x65});
        if (lowerPeer) fixture.tail(owner, 3, CustodyBytes{0x87, 0xa9, 0xcb, 0xed});
        owner.reset();
        fixture.corrupt(oldData.offset + oldData.envelopeBytes - 1);
        auto reopened = fixture.open(CustodyFileAccess::readExisting);
        assert(reopened.ok()); // Prefix-only physical open must not mint a tree proof.
        if (lowerPeer) {
            const auto cell = (*reopened.value)->readCiphertext(128, 16384);
            assert(cell.ok() && ProtectedPackedCustodyCodec::openHead(fixture.context, 0, cell.value->bytes, 3).ok());
        }
        rejectsAndLatches(*reopened.value); // Valid highest HEAD cannot hide old peer DATA failure.
    }
    {
        Fixture fixture;
        auto owner = fixture.create();
        fixture.tail(owner, 2, CustodyBytes{1, 4, 9});
        owner.reset();
        fixture.corrupt(128); // Invalid lower birth HEAD, current g2 otherwise untouched.
        auto reopened = fixture.open(CustodyFileAccess::readExisting);
        assert(reopened.ok());
        rejectsAndLatches(*reopened.value);
    }
}
void lifetimesAndFaults() {
    Fixture fixture;
    auto owner = fixture.create();
    const CustodyBytes bytes{0x12, 0x34, 0x56};
    fixture.tail(owner, 2, bytes);
    auto tree = verified(owner, 2, bytes.size(), 1);
    std::weak_ptr<ProtectedPackedCustodyOwner> weak = owner;
    owner->revokeWrites();
    auto read = tree->readBlock(0);
    assert(read.ok() && read.value->bytes == bytes);
    owner.reset();
    assert(!weak.expired());
    fixture.denyExternalWriter();
    tree.reset();
    assert(!weak.expired() && read.value->bytes == bytes); // Actual guard retained by plaintext result.
    fixture.denyExternalWriter();
    read.value.reset();
    assert(weak.expired());
    auto reopened = fixture.open(CustodyFileAccess::readExisting);
    assert(reopened.ok());
    auto reopenedTree = verified(*reopened.value, 2, bytes.size(), 1);
    assert(reopenedTree->readBlock(0).ok()); // Warm any optional cache.
    (*reopened.value)->blockWrites();
    const auto physical = (*reopened.value)->readCiphertext(0, 128);
    assert(!physical.ok());
    const auto failed = reopenedTree->readBlock(0);
    assert(!failed.ok() && failed.error == physical.error && failed.nativeError == physical.nativeError);
    const auto again = reopenedTree->readBlock(0);
    assert(!again.ok() && again.error == failed.error && again.nativeError == failed.nativeError);
    const auto reverify = Tree::verify(*reopened.value);
    assert(!reverify.ok() && reverify.error == failed.error && reverify.nativeError == failed.nativeError);
}
void oneBorrowedJob() {
    Fixture fixture;
    auto owner = fixture.create();
    fixture.tail(owner, 2, CustodyBytes{3, 1, 4});
    {
        std::array<CustodyNativeJob, 3> existing;
        assert(existing[0] && existing[1] && existing[2]);
        // Exactly one remaining slot: nested per-node admissions must not be required.
        const auto tree = verified(owner, 2, 3, 1);
        const auto read = tree->readBlock(0);
        assert(read.ok() && read.value->bytes == (CustodyBytes{3, 1, 4}));
    }
    {
        std::array<CustodyNativeJob, 4> existing;
        assert(existing[0] && existing[1] && existing[2] && existing[3]);
        const auto denied = Tree::verify(owner);
        assert(!denied.ok() && denied.error == CustodyFileError::allocationFailed);
    }
}
void pinnedOldRootAcrossPublications() {
    Fixture fixture;
    auto owner = fixture.create();
    const CustodyBytes oldBytes{0x16, 0x28, 0x3a};
    fixture.tail(owner, 2, oldBytes);
    const auto oldTree = verified(owner, 2, oldBytes.size(), 1);
    const auto checkOld = [&] {
        assert(oldTree->generation() == 2 && oldTree->logicalBytes() == oldBytes.size());
        const auto read = oldTree->readBlock(0);
        assert(read.ok() && read.value->bytes == oldBytes);
    };
    checkOld();
    fixture.tail(owner, 3, CustodyBytes{0x4c, 0x5e, 0x60, 0x72});
    checkOld();
    const CustodyBytes currentBytes{0x84, 0x96, 0xa8, 0xba, 0xcc};
    fixture.tail(owner, 4, currentBytes); // Slot1 no longer contains the g2 HEAD.
    const auto currentTree = verified(owner, 4, currentBytes.size(), 1);
    const auto current = currentTree->readBlock(0);
    assert(current.ok() && current.value->bytes == currentBytes);
    checkOld();
    // Same-owner immutable child lifetime only. Old proof is not current
    // publication/ACK authority; raw fixture publications are not logical commits.
}

// Artificial allocator pressure, not an N-record fixture or disk volume. The
// uninitialized synthetic allocation is never read and is charged exactly once.
struct ChargedPressure {
    CustodyAllocator<std::uint8_t> allocator;
    std::size_t count = 0;
    std::uint8_t* bytes = nullptr;
    explicit ChargedPressure(std::size_t headroom) {
        const auto used = CustodyOwnedMemory::usedBytes();
        assert(headroom < CustodyOwnedMemory::limit && used < CustodyOwnedMemory::limit - headroom);
        count = CustodyOwnedMemory::limit - headroom - used;
        bytes = allocator.allocate(count);
        assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit - headroom);
    }
    ~ChargedPressure() { allocator.deallocate(bytes, count); }
    ChargedPressure(const ChargedPressure&) = delete;
    ChargedPressure& operator=(const ChargedPressure&) = delete;
};
void allocationLatched(const std::shared_ptr<ProtectedPackedCustodyOwner>& owner,
    std::uint32_t nativeError, const std::shared_ptr<const Tree>& tree = nullptr) {
    const auto physical = owner->readCiphertext(0, 128);
    assert(!physical.value && physical.error == CustodyFileError::allocationFailed && physical.nativeError == nativeError);
    const auto proof = Tree::verify(owner);
    assert(!proof.value && proof.error == CustodyFileError::allocationFailed && proof.nativeError == nativeError);
    if (tree) {
        const auto read = tree->readBlock(0);
        assert(!read.value && read.error == CustodyFileError::allocationFailed && read.nativeError == nativeError);
    }
}
std::size_t emptyProxyCharge() {
    const auto before = CustodyOwnedMemory::usedBytes();
    const CustodyBytes empty(0);
    return CustodyOwnedMemory::usedBytes() - before;
}
void exactFitReturnRefusal(bool zero) {
    const auto proxy = emptyProxyCharge(); // Actual STL charge; no hard-coded proxy size.
    if (proxy == 0) return; // Release STL has no charged iterator proxy.
    const auto before = CustodyOwnedMemory::usedBytes();
    {
        Fixture fixture;
        auto owner = fixture.create();
        std::shared_ptr<const Tree> tree;
        if (zero) {
            const auto root = fixture.node(owner, Kind::nodeL2, 0, 2, zeroRef());
            fixture.publish(owner, 1, 2, fixture.headBody(2, Format::blockBytes, root));
            tree = verified(owner, 2, Format::blockBytes, 1);
        }
        std::uint32_t native = 0;
        {
            // ZERO fits its payload + result proxy, physical read fits its
            // result proxy + ciphertext proxy + 128 bytes. The next move proxy
            // must refuse under the held Guard rather than terminating.
            ChargedPressure pressure(zero ? Format::blockBytes + proxy : 128 + 2*proxy);
            if (zero) {
                const auto result = tree->readBlock(0);
                assert(!result.value && result.error == CustodyFileError::allocationFailed);
                native = result.nativeError;
            } else {
                const auto result = owner->readCiphertext(0, 128);
                assert(!result.value && result.error == CustodyFileError::allocationFailed);
                native = result.nativeError;
            }
            allocationLatched(owner, native, tree);
        }
        allocationLatched(owner, native, tree);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}
void retainedMoveKeepsCustody(bool plain) {
    if (emptyProxyCharge() == 0) return;
    const auto before = CustodyOwnedMemory::usedBytes();
    {
        Fixture fixture;
        auto owner = fixture.create();
        if (plain) {
            const CustodyBytes expected{0x31, 0x72, 0x93};
            fixture.tail(owner, 2, expected);
            auto tree = verified(owner, 2, expected.size(), 1);
            std::weak_ptr<const Tree> weak = tree;
            auto read = tree->readBlock(0); assert(read.ok());
            tree.reset(); owner.reset(); // Result is the sole remaining custody.
            {
                ChargedPressure pressure(0);
                bool refused = false;
                try { PackedPlainRead moved(std::move(*read.value)); }
                catch (const std::bad_alloc&) { refused = true; }
                assert(refused && read.value->pin && read.value->proof && !weak.expired());
                assert(read.value->bytes == expected && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
                fixture.denyExternalWriter();
                std::array<CustodyPin, 29> held; // Owner + Tree + result = three pins.
                for (const auto& pin : held) assert(pin);
                CustodyPin overflow; assert(!overflow);
            }
            { const auto again = read.value->proof->readBlock(0); assert(again.ok() && again.value->bytes == expected); }
            read.value.reset(); assert(weak.expired());
        } else {
            std::weak_ptr<ProtectedPackedCustodyOwner> weak = owner;
            auto read = owner->readCiphertext(0, 128); assert(read.ok());
            owner.reset();
            {
                ChargedPressure pressure(0);
                bool refused = false;
                try { PackedCipherRead moved(std::move(*read.value)); }
                catch (const std::bad_alloc&) { refused = true; }
                assert(refused && read.value->pin && read.value->owner && !weak.expired());
                assert(read.value->bytes.size() == 128 && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
                fixture.denyExternalWriter();
                std::array<CustodyPin, 30> held;
                for (const auto& pin : held) assert(pin);
                CustodyPin overflow; assert(!overflow);
            }
            { const auto again = read.value->owner->readCiphertext(0, 128); assert(again.ok() && again.value->bytes == read.value->bytes); }
            read.value.reset(); assert(weak.expired());
        }
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}
void chargedVerifyRefusal() {
    Fixture fixture;
    auto owner = fixture.create();
    fixture.tail(owner, 2, CustodyBytes{0x25, 0x47, 0x69});
    std::uint32_t nativeError = 0;
    {
        ChargedPressure pressure(0);
        const auto refused = Tree::verify(owner);
        assert(!refused.value && refused.error == CustodyFileError::allocationFailed);
        nativeError = refused.nativeError;
        allocationLatched(owner, nativeError);
    }
    allocationLatched(owner, nativeError); // Releasing charged pressure does not heal the owner.
}
void chargedReadRefusals() {
    for (const bool zero : {false, true}) {
        Fixture fixture;
        auto owner = fixture.create();
        PackedReference root;
        if (zero) {
            root = fixture.node(owner, Kind::nodeL2, 0, 2, zeroRef());
        } else {
            const CustodyBytes bytes(Format::blockBytes, 0x5d);
            const auto data = fixture.append(owner, Kind::data, 0, 2, bytes);
            root = fixture.path(owner, 2, data);
        }
        fixture.publish(owner, 1, 2, fixture.headBody(2, Format::blockBytes, root));
        const auto tree = verified(owner, 2, Format::blockBytes, 1);
        std::uint32_t nativeError = 0;
        {
            ChargedPressure pressure(32768);
            {
                // Establish that root ciphertext/decryption fits this headroom.
                // All temporary buffers release before the actual Tree read.
                const auto cipher = owner->readCiphertext(root.offset, root.envelopeBytes);
                assert(cipher.ok());
                auto decoded = ProtectedPackedCustodyCodec::openReferenced(
                    fixture.context, 0, root, cipher.value->bytes);
                assert(decoded.ok() && decoded.value->body.size() == 4096);
                custody_detail::WipeBytes wipe{decoded.value->body};
            }
            assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit - 32768);
            // DATA envelope or full ZERO result needs >32KiB: no partial bytes.
            const auto refused = tree->readBlock(0);
            assert(!refused.value && refused.error == CustodyFileError::allocationFailed);
            nativeError = refused.nativeError;
            allocationLatched(owner, nativeError, tree);
        }
        allocationLatched(owner, nativeError, tree); // Not a retryable admission refusal.
    }
}
void resultPinRefusalIsTransient() {
    Fixture fixture;
    auto owner = fixture.create();
    const CustodyBytes bytes{0x31, 0x53, 0x75};
    fixture.tail(owner, 2, bytes);
    const auto tree = verified(owner, 2, bytes.size(), 1);
    {
        // Owner1 + Tree proof1 + 30 held pins = exact process cap32.
        std::array<CustodyPin, 30> held;
        for (const auto& pin : held) assert(pin);
        CustodyPin overflow;
        assert(!overflow);
        const auto refused = tree->readBlock(0);
        assert(!refused.value && refused.error == CustodyFileError::allocationFailed);
    }
    // Early result-pin refusal must not poison the owner or the existing proof.
    const auto read = tree->readBlock(0);
    assert(read.ok() && read.value->bytes == bytes);
    const auto physical = owner->readCiphertext(0, 128);
    assert(physical.ok());
    const auto current = Tree::verify(owner);
    assert(current.ok() && (*current.value)->generation() == 2);
}
} // namespace
#endif

int main(int argc, char** argv) {
#ifdef _WIN32
    _set_error_mode(_OUT_TO_STDERR);
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
#ifdef _DEBUG
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
#endif
    if (argc == 2 && std::strcmp(argv[1], "--exact-fit-zero") == 0) { exactFitReturnRefusal(true); return 0; }
    if (argc == 2 && std::strcmp(argv[1], "--exact-fit-physical") == 0) { exactFitReturnRefusal(false); return 0; }
    if (argc == 2 && std::strcmp(argv[1], "--retained-plain-move") == 0) { retainedMoveKeepsCustody(true); return 0; }
    if (argc == 2 && std::strcmp(argv[1], "--retained-cipher-move") == 0) { retainedMoveKeepsCustody(false); return 0; }
#else
    (void)argc; (void)argv;
#endif
    const auto missing = Tree::verify(nullptr);
    assert(!missing.ok() && missing.error == CustodyFileError::invalidInput);
#ifdef _WIN32
    const auto before = CustodyOwnedMemory::usedBytes();
    birth();
    dataPairAndReopen();
    zeroAndTail();
    largeInlineZero();
    descriptors();
    shapes();
    pairs();
    currentAndLowerCorruption();
    lifetimesAndFaults();
    oneBorrowedJob();
    pinnedOldRootAcrossPublications();
    chargedVerifyRefusal();
    chargedReadRefusals();
    resultPinRefusalIsTransient();
    exactFitReturnRefusal(true);
    exactFitReturnRefusal(false);
    retainedMoveKeepsCustody(true);
    retainedMoveKeepsCustody(false);
    assert(CustodyOwnedMemory::usedBytes() == before);
#else
    // Native fixtures never run portably. Only deterministic structural wire here.
    const PackedCustodyContext context{{{}, {}, CustodyRole::canonical}, {}};
    const auto prefix = Format::encodePrefix(context);
    assert(prefix && Format::prefixMatches(prefix->data(), prefix->size(), context));
#endif
    return 0;
}
