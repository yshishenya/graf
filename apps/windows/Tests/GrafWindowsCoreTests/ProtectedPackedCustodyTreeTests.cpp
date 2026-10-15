#include "../../RecApp/Storage/ProtectedPackedCustodyTree.h"
#include "../../RecApp/Storage/ProtectedCustodyPrimitives.h"
#include "../../RecApp/Storage/ProtectedCustodyReader.h"
#include "../../RecApp/Storage/ProtectedCustodyWriter.h"
#include "../../RecApp/Storage/ProtectedCustodyMetadata.h"
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
static_assert(std::is_nothrow_move_constructible_v<PackedTreeCommit>);
static_assert(std::is_nothrow_copy_constructible_v<PackedTreeCommit>);
static_assert(sizeof(Tree) <= 4096);

#ifdef _WIN32
#include <windows.h>
#include <sddl.h>
#include <objbase.h>
#include <vector>
#include <functional>
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
        assert(context.object.role == CustodyRole::canonical || context.object.role == CustodyRole::media || context.object.role == CustodyRole::playback);
        const auto role = context.object.role == CustodyRole::media ? L"media" : context.object.role == CustodyRole::playback ? L"playback" : L"canonical";
        return root / L"package-a" / L".custody-v1" / role / L"content.packed-v2";
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
void sealedPackedMember() {
    Fixture f;
    const CustodyBytes plain{1, 2, 3};
    PackedRootDescriptor stamp;
    PackedReference historicalData;
    {
        auto owner = f.create();
        historicalData = f.tail(owner, 2, plain);
        auto proof = Tree::verify(owner); assert(proof.ok()); stamp = proof.value->get()->descriptor();
        proof.value.reset();
        f.tail(owner, 3, CustodyBytes{4, 5, 6, 7});
        f.tail(owner, 4, CustodyBytes{8, 9, 10, 11, 12});
    }
    auto own = f.context.object; own.role = CustodyRole::packageState; own.objectId[0] ^= 0x40;
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    const auto commit = [&](std::uint64_t generation, unsigned fault = 0) {
        CustodyPackageValue v; v.schema = 2; v.context = own; v.generation = generation;
        const std::string directory = "package-a"; std::copy(directory.begin(), directory.end(), v.directory.begin());
        v.phase = CustodyPackagePhase::sealedDegraded; v.reason = ReasonCode::clockDiscontinuity; v.refCount = 1;
        auto& ref = v.refs[0]; ref.role = f.context.object.role; ref.objectId = f.context.object.objectId;
        ref.sealed = ref.packed = true; ref.generation = stamp.generation; ref.length = stamp.logicalBytes;
        ref.sha256 = custody_detail::digest(plain.data(), plain.size()); assert(ref.sha256);
        ref.containerId = f.context.containerId; ref.committedExtent = stamp.committedExtent;
        ref.rootRef = Format::encodeReference(stamp.root); assert(ref.rootRef);
        if (fault == 1) ref.sha256->at(0) ^= 1;
        if (fault == 2) ref.containerId->at(0) ^= 1;
        if (fault == 3) *ref.generation = 5; // Structurally valid future stamp, not authority.
        auto bytes = writeCustodyPackage(v, own, generation, directory); assert(bytes.ok());
        assert(commitProtectedCustodyMetadata(f.root, directory, own, generation-1, *bytes.value, cancelled).state == CustodyCommitState::committed);
    };
    const auto pair = [&] { auto p = ProtectedCustodyPackagePair::read(f.root, "package-a", own, cancelled); assert(p.ok()); return std::move(*p.value); };
    commit(1); commit(2);
    {
        auto held = pair();
        {
            auto batch = openProtectedCustodyReaders(f.root, held, cancelled); assert(batch.ok());
            for (unsigned slot : {0U, 1U}) {
                std::array<std::uint8_t, 4> bytes{}; ULONG got = 0;
                assert((*batch.value)[slot][0].stream->Read(bytes.data(), 4, &got) == S_FALSE && got == 3);
                assert(bytes[0] == 1 && bytes[2] == 3);
            }
        }
        for (unsigned slot : {0U, 1U}) {
            auto opened = openProtectedCustodyReader(f.root, held, slot, 0, cancelled); assert(opened.ok());
            std::array<std::uint8_t, 4> bytes{}; ULONG got = 0;
            assert(opened.value->stream->Read(bytes.data(), 4, &got) == S_FALSE && got == 3);
            assert(bytes[0] == 1 && bytes[2] == 3); // Historical, not current bytes; initial cursor zero.
        }
        auto opened = openProtectedCustodyReader(f.root, held, 0, 0, cancelled); assert(opened.ok());
        Microsoft::WRL::ComPtr<IStream> clone; assert(opened.value->stream->Clone(&clone) == S_OK);
        held.reset(); opened.value.reset(); f.denyExternalWriter();
        assert(!ProtectedCustodyFiles::open(f.root, "package-a", own, CustodyFileAccess::writeExisting).ok());
        clone.Reset(); assert(ProtectedCustodyFiles::open(f.root, "package-a", own, CustodyFileAccess::writeExisting).ok());
    }
    for (unsigned fault = 1; fault <= 3; ++fault) {
        commit(fault+2, fault); auto held = pair();
        assert(!openProtectedCustodyReader(f.root, held, static_cast<unsigned>((fault+1)%2), 0, cancelled).ok());
    }
    commit(6); f.corrupt(historicalData.offset);
    { auto held = pair(); assert(!openProtectedCustodyReader(f.root, held, 1, 0, cancelled).ok()); }
}
void livePackedMember() {
    const auto before = CustodyOwnedMemory::usedBytes();
    for (unsigned fault = 0; fault < 6; ++fault) {
        Fixture f;
        const bool empty = fault == 5;
        const CustodyBytes oldBytes = empty ? CustodyBytes{} : CustodyBytes{1, 2, 3};
        PackedRootDescriptor stamp;
        PackedReference historicalData, lowerData;
        {
            auto owner = f.create();
            if (!empty) historicalData = f.tail(owner, 2, oldBytes);
            auto proof = Tree::verify(owner); assert(proof.ok()); stamp = (*proof.value)->descriptor();
            proof.value.reset();
            if (!empty) {
                lowerData = f.tail(owner, 3, CustodyBytes{4, 5, 6, 7});
                f.tail(owner, 4, CustodyBytes{8, 9, 10, 11, 12});
            }
        }
        auto own = f.context.object; own.role = CustodyRole::packageState; own.objectId[0] ^= 0x40;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        const auto commit = [&](std::uint64_t generation, bool sealed) {
            CustodyPackageValue v; v.schema = 2; v.context = own; v.generation = generation;
            const std::string directory = "package-a"; std::copy(directory.begin(), directory.end(), v.directory.begin());
            v.phase = sealed ? CustodyPackagePhase::sealedDegraded : CustodyPackagePhase::capturing;
            v.reason = sealed ? ReasonCode::clockDiscontinuity : ReasonCode::none; v.refCount = 1;
            auto& ref = v.refs[0]; ref.role = f.context.object.role; ref.objectId = f.context.object.objectId;
            ref.packed = true; ref.containerId = f.context.containerId;
            if (sealed) {
                ref.sealed = true; ref.generation = stamp.generation; ref.length = stamp.logicalBytes;
                ref.sha256 = custody_detail::digest(oldBytes.data(), oldBytes.size()); assert(ref.sha256);
                ref.committedExtent = stamp.committedExtent; ref.rootRef = Format::encodeReference(stamp.root); assert(ref.rootRef);
                if (fault == 3) ref.sha256->at(0) ^= 1;
                if (fault == 4) ref.containerId->at(0) ^= 1;
            }
            auto bytes = writeCustodyPackage(v, own, generation, directory); assert(bytes.ok());
            assert(commitProtectedCustodyMetadata(f.root, directory, own, generation-1, *bytes.value, cancelled).state == CustodyCommitState::committed);
        };
        commit(1, false); commit(2, true);
        if (fault == 1) f.corrupt(lowerData.offset); // Nonselected current closure, historical SEALED remains intact.
        if (fault == 2) f.corrupt(historicalData.offset); // LIVE current closure healthy; old SEALED must still be read.
        {
            auto held = ProtectedCustodyPackagePair::read(f.root, "package-a", own, cancelled); assert(held.ok());
            if (!fault || empty) {
                auto single = openProtectedCustodyReader(f.root, *held.value, 1, 0, cancelled); assert(single.ok());
            } // Release before opening another group: no second owner for the same packed role.
            auto batch = openProtectedCustodyReaders(f.root, *held.value, cancelled);
            if (fault && !empty) {
                assert(!batch.value && batch.error == (fault == 4 ? CustodyFileError::identityMismatch : CustodyFileError::invalidContent));
                continue;
            }
            assert(batch.ok());
            for (unsigned slot : {0U, 1U}) {
                STATSTG stat{}; const auto count = empty ? 0U : slot ? 3U : 5U;
                assert((*batch.value)[slot][0].stream->Stat(&stat, STATFLAG_NONAME) == S_OK && stat.cbSize.QuadPart == count);
                std::array<std::uint8_t, 6> bytes{}; ULONG got = 99;
                assert((*batch.value)[slot][0].stream->Read(bytes.data(), 6, &got) == S_FALSE && got == count);
                if (!empty) assert(bytes[0] == (slot ? 1 : 8)); // Actual g4 LIVE vs historical g2 outside BOTH current heads.
            }
            Microsoft::WRL::ComPtr<IStream> clone; assert((*batch.value)[0][0].stream->Clone(&clone) == S_OK);
            std::uint8_t byte = 0; ULONG got = 99;
            cancelled->store(true); const auto aborted = HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED);
            assert(clone->Read(&byte, 1, &got) == aborted && got == 0);
            cancelled->store(false);
            assert((*batch.value)[1][0].stream->Read(&byte, 1, &got) == aborted && got == 0); // Group sticky, not cleared by token reset.
            held.value.reset(); batch.value.reset(); f.denyExternalWriter();
            assert(!ProtectedCustodyFiles::open(f.root, "package-a", own, CustodyFileAccess::writeExisting).ok());
            clone.Reset(); assert(ProtectedCustodyFiles::open(f.root, "package-a", own, CustodyFileAccess::writeExisting).ok());
            assert(f.open(CustodyFileAccess::writeExisting).ok());
        }
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}
void noBytesBeyondEOF(const std::shared_ptr<const Tree>& tree, std::uint64_t block) {
    const auto result = tree->readBlock(block);
    // Block-level API may reject an absent block or return EOF; never synthesize bytes.
    assert(result.ok() ? result.value->bytes.empty() : result.error == CustodyFileError::invalidInput);
}
void mixedPackageGroup() {
    const auto before = CustodyOwnedMemory::usedBytes();
    Fixture f;
    const auto base = f.context;
    std::array<PackedCustodyContext, 3> contexts;
    std::array<std::array<PackedRootDescriptor, 3>, 2> stamps;
    for (unsigned role = 0; role < 3; ++role) {
        contexts[role] = base; contexts[role].object.role = static_cast<CustodyRole>(role+1);
        contexts[role].object.objectId[0] += static_cast<std::uint8_t>(role);
        contexts[role].containerId[0] += static_cast<std::uint8_t>(role);
        f.context = contexts[role];
        auto owner = f.create();
        f.tail(owner, 2, CustodyBytes{static_cast<std::uint8_t>(role+1), 2, 3});
        { auto proof = Tree::verify(owner); assert(proof.ok()); stamps[0][role] = (*proof.value)->descriptor(); }
        f.tail(owner, 3, CustodyBytes{4, 5, 6, 7});
        f.tail(owner, 4, CustodyBytes{static_cast<std::uint8_t>(role+8), 9, 10, 11, 12});
        { auto proof = Tree::verify(owner); assert(proof.ok()); stamps[1][role] = (*proof.value)->descriptor(); }
    }
    f.context = base;
    std::array<CustodyContext, 2> flat;
    for (unsigned role = 0; role < 2; ++role) {
        flat[role] = base.object; flat[role].role = static_cast<CustodyRole>(role+4);
        flat[role].objectId[0] = static_cast<std::uint8_t>(role+71);
        auto files = ProtectedCustodyFiles::open(f.root, "package-a", flat[role], CustodyFileAccess::createNew); assert(files.ok());
        CustodyBytes plain{static_cast<std::uint8_t>(role+21)};
        auto block = ProtectedCustodyCodec::sealBlock(flat[role], 0, 1, plain); assert(block.ok());
        auto written = (*files.value)->writeBlock(0, 1, 1, *block.value); assert(written.ok());
        CustodyIndex index{1, 1, {{1, *written.value, 0}}};
        for (unsigned slot : {0U, 1U}) {
            auto bytes = ProtectedCustodyCodec::sealIndex(flat[role], slot, index); assert(bytes.ok());
            assert((*files.value)->publishIndex(slot, *bytes.value).state == CustodyPublishState::published);
        }
    }
    auto own = base.object; own.role = CustodyRole::packageState; own.objectId[0] = 91;
    const auto cancelled = std::make_shared<std::atomic<bool>>(false);
    for (unsigned slot : {0U, 1U}) {
        CustodyPackageValue v; v.schema = 2; v.context = own; v.generation = slot+1;
        const std::string directory = "package-a"; std::copy(directory.begin(), directory.end(), v.directory.begin());
        v.phase = CustodyPackagePhase::sealedDegraded; v.reason = ReasonCode::clockDiscontinuity; v.refCount = 5;
        for (unsigned role = 0; role < 3; ++role) {
            const auto& stamp = stamps[slot][role]; auto& ref = v.refs[role];
            ref.role = contexts[role].object.role; ref.objectId = contexts[role].object.objectId;
            ref.sealed = ref.packed = true; ref.generation = stamp.generation; ref.length = stamp.logicalBytes;
            const CustodyBytes plain = slot == 0 ? CustodyBytes{static_cast<std::uint8_t>(role+1), 2, 3}
                : CustodyBytes{static_cast<std::uint8_t>(role+8), 9, 10, 11, 12};
            ref.sha256 = custody_detail::digest(plain.data(), plain.size()); assert(ref.sha256);
            ref.containerId = contexts[role].containerId; ref.committedExtent = stamp.committedExtent;
            ref.rootRef = Format::encodeReference(stamp.root); assert(ref.rootRef);
        }
        for (unsigned role = 0; role < 2; ++role) {
            auto& ref = v.refs[role+3]; ref.role = flat[role].role; ref.objectId = flat[role].objectId;
            ref.sealed = true; ref.generation = ref.length = 1;
            const std::uint8_t byte = static_cast<std::uint8_t>(role+21); ref.sha256 = custody_detail::digest(&byte, 1); assert(ref.sha256);
        }
        auto bytes = writeCustodyPackage(v, own, slot+1, directory); assert(bytes.ok());
        assert(commitProtectedCustodyMetadata(f.root, directory, own, slot, *bytes.value, cancelled).state == CustodyCommitState::committed);
    }
    auto held = ProtectedCustodyPackagePair::read(f.root, "package-a", own, cancelled); assert(held.ok());
    auto batch = openProtectedCustodyReaders(f.root, *held.value, cancelled); assert(batch.ok());
    for (unsigned slot : {0U, 1U}) for (unsigned role = 0; role < 3; ++role) {
        std::array<std::uint8_t, 6> bytes{}; ULONG got = 0;
        assert((*batch.value)[slot][role].stream->Read(bytes.data(), 6, &got) == S_FALSE);
        assert(got == (slot == 0 ? 3U : 5U) && bytes[0] == (slot == 0 ? role+1 : role+8));
    }
    Microsoft::WRL::ComPtr<IStream> clone;
    assert((*batch.value)[0][4].stream->Clone(&clone) == S_OK); // A flat Clone retains all packed owners too.
    auto next = (*held.value)->current(); next.generation = 3;
    next.phase = CustodyPackagePhase::finalizing; next.reason = ReasonCode::none;
    next.refs[0] = {}; next.refs[0].role = contexts[0].object.role; next.refs[0].objectId = contexts[0].object.objectId;
    next.refs[0].packed = true; next.refs[0].containerId = contexts[0].containerId;
    held.value.reset(); batch.value.reset();
    for (const auto& context : contexts)
        assert(!ProtectedPackedCustodyOwner::open(f.root, "package-a", context, CustodyFileAccess::writeExisting).ok());
    for (const auto& context : flat)
        assert(!ProtectedCustodyFiles::open(f.root, "package-a", context, CustodyFileAccess::writeExisting).ok());
    assert(!ProtectedCustodyFiles::open(f.root, "package-a", own, CustodyFileAccess::writeExisting).ok());
    clone.Reset();
    for (const auto& context : contexts)
        assert(ProtectedPackedCustodyOwner::open(f.root, "package-a", context, CustodyFileAccess::writeExisting).ok());
    for (const auto& context : flat)
        assert(ProtectedCustodyFiles::open(f.root, "package-a", context, CustodyFileAccess::writeExisting).ok());
    assert(ProtectedCustodyFiles::open(f.root, "package-a", own, CustodyFileAccess::writeExisting).ok());
    {
        auto bytes = writeCustodyPackage(next, own, 3, "package-a"); assert(bytes.ok());
        assert(commitProtectedCustodyMetadata(f.root, "package-a", own, 2, *bytes.value, cancelled).state == CustodyCommitState::committed);
        auto livePair = ProtectedCustodyPackagePair::read(f.root, "package-a", own, cancelled); assert(livePair.ok());
        auto mixed = openProtectedCustodyReaders(f.root, *livePair.value, cancelled); assert(mixed.ok());
        for (unsigned slot : {0U, 1U}) for (unsigned role = 0; role < 5; ++role) {
            std::array<std::uint8_t, 6> actual{}; ULONG got = 0;
            assert((*mixed.value)[slot][role].stream->Read(actual.data(), 6, &got) == S_FALSE);
            assert(got == (role < 3 ? 5U : 1U) && actual[0] == (role < 3 ? role+8 : role+18));
        } // LIVE packed canonical shares a frozen group with packed/flat SEALED siblings in BOTH slots.
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
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
void packedWriter() {
    for (const auto role : {CustodyRole::canonical, CustodyRole::media, CustodyRole::playback}) {
        Fixture fixture;
        fixture.context.object.role = role;
        const auto cancellation = std::make_shared<std::atomic<bool>>(false);
        CustodyBytes expected(Format::blockBytes+7, 0x5a);
        std::uint64_t finalGeneration = 0;
        {
            auto owner = fixture.create();
            auto tree = verified(owner, 1, 0, 0);
            auto opened = ProtectedCustodyWriter::open(tree, cancellation); assert(opened.ok());
            auto& writer = **opened.value;
            assert(writer.writeAt(0, expected.data(), expected.size()).ok());
            // The complete DATA prefix, NOT ZERO for the unsaved short input.
            auto prefix = Tree::verify(owner); assert(prefix.ok());
            assert((*prefix.value)->logicalBytes() == Format::blockBytes);
            assert((*prefix.value)->readBlock(0).value->bytes == CustodyBytes(Format::blockBytes, 0x5a));
            assert(writer.checkpoint().state == CustodyCommitState::committed);
            auto original = Tree::verify(owner); assert(original.ok());
            auto reader = openProtectedCustodyReader(*original.value, cancellation); assert(reader.ok());
            Microsoft::WRL::ComPtr<IStream> clone;
            assert(reader.value->stream->Clone(&clone) == S_OK);
            const CustodyBytes header{9, 8, 7}, crossing{1, 2, 3, 4, 5, 6, 7}, tail{11, 12};
            assert(writer.writeAt(0, header.data(), header.size()).ok());
            std::copy(header.begin(), header.end(), expected.begin());
            assert(writer.writeAt(Format::blockBytes-2, crossing.data(), crossing.size()).ok());
            std::copy(crossing.begin(), crossing.end(), expected.begin()+Format::blockBytes-2);
            const auto writeOffset = 2*Format::blockBytes+5;
            assert(writer.writeAt(writeOffset, tail.data(), tail.size()).ok());
            expected.resize(writeOffset+tail.size(), 0);
            std::copy(tail.begin(), tail.end(), expected.begin()+writeOffset);
            CustodyBytes actual(expected.size()+1, 0xee);
            const auto pending = writer.readAt(0, actual.data(), actual.size());
            assert(pending.ok() && *pending.value == expected.size());
            assert(std::equal(expected.begin(), expected.end(), actual.begin()) && actual.back() == 0xee);
            assert(writer.checkpoint().state == CustodyCommitState::committed);
            // Dirty suffix must not reappear even before a checkpoint.
            assert(writer.writeAt(1, crossing.data(), crossing.size()).ok());
            assert(writer.setSize(1).ok()); expected.resize(1);
            assert(writer.setSize(2*Format::blockBytes+9).ok()); expected.resize(2*Format::blockBytes+9, 0);
            actual.assign(expected.size(), 0xee);
            assert(writer.readAt(0, actual.data(), actual.size()).ok() && actual == expected);
            assert(writer.checkpoint().state == CustodyCommitState::committed);
            finalGeneration = writer.generation();
            assert(writer.writeAt(Format::logicalLimit, nullptr, 0).ok());
            assert(writer.size() == expected.size());
            opened.value.reset(); // Healthy release revokes writes, NOT pinned reads.
            CustodyBytes pinned(Format::blockBytes+7, 0);
            ULONG got = 0;
            assert(clone->Read(pinned.data(), static_cast<ULONG>(pinned.size()), &got) == S_OK);
            assert(got == pinned.size() && pinned == CustodyBytes(pinned.size(), 0x5a));
            assert(tree->setSize(0).state != CustodyCommitState::committed);
        }
        auto coldOwner = fixture.open(CustodyFileAccess::readExisting); assert(coldOwner.ok());
        auto cold = Tree::verify(*coldOwner.value); assert(cold.ok());
        assert((*cold.value)->logicalBytes() == expected.size() && (*cold.value)->generation() == finalGeneration);
        auto reader = openProtectedCustodyReader(*cold.value, cancellation); assert(reader.ok());
        CustodyBytes actual(expected.size(), 0xee); ULONG got = 0;
        assert(reader.value->stream->Read(actual.data(), static_cast<ULONG>(actual.size()), &got) == S_OK);
        assert(got == expected.size() && actual == expected);
    }
}
void packedReader() {
    Fixture fixture;
    auto owner = fixture.create();
    auto tree = verified(owner, 1, 0, 0);
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    assert(openProtectedCustodyReader(nullptr, cancelled).error == CustodyFileError::invalidInput);
    assert(openProtectedCustodyReader(tree, nullptr).error == CustodyFileError::invalidInput);
    cancelled->store(true);
    assert(openProtectedCustodyReader(tree, cancelled).nativeError == ERROR_OPERATION_ABORTED);
    cancelled->store(false);
    {
        auto empty = openProtectedCustodyReader(tree, cancelled); assert(empty.ok());
        std::uint8_t byte = 0x77; ULONG got = 9;
        assert(empty.value->stream->Read(nullptr, 0, &got) == S_OK && got == 0);
        assert(empty.value->stream->Read(&byte, 1, &got) == S_FALSE && got == 0 && byte == 0x77);
    }
    const CustodyBytes bytes(Format::blockBytes, 0x31), tail{1, 3, 5};
    {
        const auto result = tree->appendBlock(bytes);
        assert(result.state == CustodyCommitState::committed && result.snapshot);
        tree = result.snapshot;
    }
    auto reader = openProtectedCustodyReader(tree, cancelled);
    assert(reader.ok() && reader.value->state == CustodySnapshotState::verified);
    const auto length = bytes.size(); // This reader stays pinned to g2 even after both HEADs change.
    {
        const auto result = tree->appendBlock(tail); assert(result.snapshot); tree = result.snapshot;
    }
    {
        const auto result = tree->replaceBlock(0, CustodyBytes(Format::blockBytes, 0x53));
        assert(result.snapshot); tree = result.snapshot;
    }
    STATSTG stat{};
    auto* stream = reader.value->stream.Get();
    assert(stream->Stat(&stat, STATFLAG_DEFAULT) == S_OK && !stat.pwcsName && stat.cbSize.QuadPart == length);
    assert(stat.type == STGTY_STREAM && stat.grfMode == STGM_READ);
    assert(stream->Stat(nullptr, STATFLAG_NONAME) == STG_E_INVALIDPOINTER);
    assert(stream->Stat(&stat, 99) == STG_E_INVALIDFLAG);
    assert(stream->Clone(nullptr) == STG_E_INVALIDPOINTER);
    assert(stream->Read(nullptr, 1, nullptr) == STG_E_INVALIDPOINTER);
    ULONG written = 9;
    assert(stream->Write(bytes.data(), 1, &written) == STG_E_ACCESSDENIED && written == 0);
    assert(stream->SetSize({}) == STG_E_ACCESSDENIED);
    assert(stream->Commit(STGC_DEFAULT) == S_OK && stream->Commit(99) == STG_E_INVALIDFLAG);
    assert(stream->Revert() == STG_E_INVALIDFUNCTION);
    assert(stream->LockRegion({}, {}, 0) == STG_E_INVALIDFUNCTION);
    assert(stream->UnlockRegion({}, {}, 0) == STG_E_INVALIDFUNCTION);
    Microsoft::WRL::ComPtr<ISequentialStream> sequential;
    assert(stream->QueryInterface(IID_PPV_ARGS(&sequential)) == S_OK);
    void* unsupported = reinterpret_cast<void*>(1);
    assert(stream->QueryInterface(__uuidof(IStorage), &unsupported) == E_NOINTERFACE && !unsupported);
    assert(stream->QueryInterface(__uuidof(IStream), nullptr) == E_POINTER);
    sequential.Reset();
    LARGE_INTEGER offset{}; ULARGE_INTEGER position{};
    offset.QuadPart = -1;
    assert(stream->Seek(offset, STREAM_SEEK_SET, &position) == STG_E_INVALIDFUNCTION && position.QuadPart == 0);
    offset.QuadPart = (std::numeric_limits<LONGLONG>::min)();
    assert(stream->Seek(offset, STREAM_SEEK_CUR, nullptr) == STG_E_INVALIDFUNCTION);
    offset.QuadPart = (std::numeric_limits<LONGLONG>::max)();
    assert(stream->Seek(offset, STREAM_SEEK_SET, &position) == S_OK && position.QuadPart == static_cast<ULONGLONG>(offset.QuadPart));
    offset.QuadPart = 1;
    assert(stream->Seek(offset, STREAM_SEEK_CUR, nullptr) == STG_E_INVALIDFUNCTION);
    offset.QuadPart = -2;
    assert(stream->Seek(offset, STREAM_SEEK_END, &position) == S_OK && position.QuadPart == length-2);
    std::array<std::uint8_t, 4> output{};
    ULONG got = 0;
    assert(stream->Read(output.data(), 4, &got) == S_FALSE && got == 2 && output[0] == 0x31 && output[1] == 0x31);
    offset.QuadPart = 0;
    assert(stream->Seek(offset, 99, nullptr) == STG_E_INVALIDFUNCTION);
    assert(stream->Seek(offset, STREAM_SEEK_SET, nullptr) == S_OK);
    Microsoft::WRL::ComPtr<IStream> clone;
    assert(stream->Clone(&clone) == S_OK);
    assert(stream->Read(output.data(), 4, &got) == S_OK && got == 4 && output[0] == 0x31);
    assert(clone->Seek(offset, STREAM_SEEK_CUR, &position) == S_OK && position.QuadPart == 0);
    {
        auto current = openProtectedCustodyReader(tree, cancelled); assert(current.ok());
        assert(current.value->stream->Stat(&stat, STATFLAG_NONAME) == S_OK && stat.cbSize.QuadPart == length+tail.size());
        offset.QuadPart = static_cast<LONGLONG>(length-2);
        assert(current.value->stream->Seek(offset, STREAM_SEEK_SET, nullptr) == S_OK);
        std::array<std::uint8_t, 8> cross{};
        assert(current.value->stream->Read(cross.data(), 8, &got) == S_FALSE && got == 5);
        assert(cross[0] == 0x53 && cross[1] == 0x53 && std::equal(tail.begin(), tail.end(), cross.begin()+2));
        offset.QuadPart = static_cast<LONGLONG>(length+100);
        assert(current.value->stream->Seek(offset, STREAM_SEEK_SET, nullptr) == S_OK);
        assert(current.value->stream->Read(cross.data(), 1, &got) == S_FALSE && got == 0);
        assert(current.value->stream->Seek({}, STREAM_SEEK_SET, nullptr) == S_OK);
        Microsoft::WRL::ComPtr<IStream> target;
        assert(CreateStreamOnHGlobal(nullptr, TRUE, &target) == S_OK);
        ULARGE_INTEGER wanted{}, consumed{}, sent{}; wanted.QuadPart = length+tail.size();
        assert(current.value->stream->CopyTo(target.Get(), wanted, &consumed, &sent) == S_OK);
        assert(consumed.QuadPart == wanted.QuadPart && sent.QuadPart == wanted.QuadPart);
        assert(target->Seek({}, STREAM_SEEK_SET, nullptr) == S_OK);
        CustodyBytes copied(static_cast<std::size_t>(wanted.QuadPart));
        assert(target->Read(copied.data(), static_cast<ULONG>(copied.size()), &got) == S_OK && got == copied.size());
        assert(std::all_of(copied.begin(), copied.begin()+length, [](auto byte) { return byte == 0x53; }));
        assert(std::equal(tail.begin(), tail.end(), copied.begin()+length));
    }
    const auto epoch = owner->epoch();
    owner->revokeWrites();
    tree.reset(); owner.reset(); reader.value.reset();
    fixture.denyExternalWriter();
    assert(!fixture.open(CustodyFileAccess::readExisting).ok());
    assert(clone->Read(output.data(), 4, &got) == S_OK && got == 4 && output[0] == 0x31);
    cancelled->store(true);
    assert(clone->Read(output.data(), 1, &got) == HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED) && got == 0);
    cancelled->store(false);
    assert(clone->Stat(&stat, STATFLAG_NONAME) == HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED));
    clone.Reset();
    auto cold = fixture.open(CustodyFileAccess::readExisting); assert(cold.ok());
    assert((*cold.value)->epoch() != epoch);
    auto coldTree = verified(*cold.value, 4, length+tail.size(), 1);
    auto coldReader = openProtectedCustodyReader(coldTree, cancelled); assert(coldReader.ok());
    assert(coldReader.value->stream->Read(output.data(), 4, &got) == S_OK && got == 4 && output[0] == 0x53);
}

void readerReleaseDrain() {
    const auto before = CustodyOwnedMemory::usedBytes(); // main has initialized the empty reader cache.
    bool observed = false, cloned = false, addRefUnchanged = false, cancelledStillLive = false;
    bool externalReleased = false, allReleased = false, ownerReleased = false, pinsReleased = true;
    {
        Fixture fixture;
        auto owner = fixture.create();
        fixture.tail(owner, 2, CustodyBytes{0x31, 0x53, 0x75});
        auto tree = verified(owner, 2, 3, 1);
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        auto reader = openProtectedCustodyReader(tree, cancelled); assert(reader.ok());
        auto observer = reader.value->readerInstances;
        auto counter = observer.lock();
        const auto count = [&] { return counter ? counter->load(std::memory_order_acquire) : 0U; };
        observed = counter && count() == 1;
        Microsoft::WRL::ComPtr<IStream> clone;
        assert(reader.value->stream->Clone(&clone) == S_OK);
        cloned = count() == 2;
        auto* external = clone.Get(); external->AddRef();
        addRefUnchanged = count() == 2;
        cancelled->store(true);
        clone.Reset(); // The external COM reference still owns the actual clone.
        ULONG got = 9; std::uint8_t byte = 0x77;
        const auto cancelledRead = external->Read(&byte, 1, &got);
        cancelledStillLive = count() == 2 && cancelledRead == HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED) && got == 0 && byte == 0x77;
        const auto references = external->Release(); external = nullptr;
        externalReleased = references == 0 && count() == 1;
        reader.value.reset(); tree.reset(); owner.reset();
        allReleased = counter && count() == 0;
        { auto reopened = fixture.open(CustodyFileAccess::readExisting); ownerReleased = reopened.ok(); }
        {
            std::array<CustodyPin, 32> pins;
            for (const auto& pin : pins) pinsReleased = pinsReleased && static_cast<bool>(pin);
            CustodyPin overflow; pinsReleased = pinsReleased && !overflow;
        }
        counter.reset();
        allReleased = allReleased && observer.expired();
        observer.reset(); // A weak reference still retains the charged control block.
    }
    const bool memoryReleased = CustodyOwnedMemory::usedBytes() == before;
    std::fprintf(stderr, "READER_RELEASE_DRAIN observed=%u cloned=%u addref_unchanged=%u cancelled_still_live=%u external_released=%u all_released=%u owner_released=%u pins_released=%u memory_released=%u\n",
        observed, cloned, addRefUnchanged, cancelledStillLive, externalReleased, allReleased, ownerReleased, pinsReleased, memoryReleased);
    std::fflush(stderr);
    assert(memoryReleased && pinsReleased && ownerReleased && "reader_release_drain_requires_actual_native_and_memory_release");
    assert(observed && "reader_release_drain_requires_actual_instance_observer");
    assert(cloned && addRefUnchanged && "reader_release_drain_counts_instances_not_addrefs");
    assert(cancelledStillLive && externalReleased && allReleased && "reader_release_drain_waits_for_actual_external_release");
}

void packedReaderAdmission() {
    Fixture fixture;
    auto owner = fixture.create();
    fixture.tail(owner, 2, CustodyBytes{0x31, 0x53, 0x75});
    auto tree = verified(owner, 2, 3, 1);
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    auto reader = openProtectedCustodyReader(tree, cancelled); assert(reader.ok());
    auto instances = reader.value->readerInstances.lock();
    assert(instances && instances->load(std::memory_order_acquire) == 1);
    ULONG got = 0; std::uint8_t byte = 0;
    assert(reader.value->stream->Read(&byte, 1, &got) == S_OK && got == 1);
    const auto beforeClone = CustodyOwnedMemory::usedBytes();
    {
        Microsoft::WRL::ComPtr<IStream> clone;
        assert(reader.value->stream->Clone(&clone) == S_OK);
        assert(instances->load(std::memory_order_acquire) == 2);
        assert(CustodyOwnedMemory::usedBytes() > beforeClone); // The actual COM object is charged.
    }
    assert(instances->load(std::memory_order_acquire) == 1);
    assert(CustodyOwnedMemory::usedBytes() == beforeClone);
    {
        // Owner + Tree + Reader + these29 = process cap32. No fictional31 packed clones.
        std::array<CustodyPin, 29> held;
        for (const auto& pin : held) assert(pin);
        IStream* clone = reinterpret_cast<IStream*>(1);
        assert(reader.value->stream->Clone(&clone) == STG_E_INSUFFICIENTMEMORY && !clone);
        assert(instances->load(std::memory_order_acquire) == 1); // Refused pin creates no Reader.
        assert(openProtectedCustodyReader(tree, cancelled).error == CustodyFileError::allocationFailed);
        assert(reader.value->stream->Read(&byte, 1, &got) == S_OK && got == 1 && byte == 0x53); // Warm cache, no result pin.
    }
    {
        const auto pressureSize = CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes();
        auto* pressure = CustodyAllocator<std::uint8_t>{}.allocate(pressureSize);
        IStream* clone = reinterpret_cast<IStream*>(1);
        assert(reader.value->stream->Clone(&clone) == STG_E_INSUFFICIENTMEMORY && !clone);
        assert(instances->load(std::memory_order_acquire) == 1); // Refused allocation creates no Reader.
        assert(!openProtectedCustodyReader(tree, cancelled).ok());
        CustodyAllocator<std::uint8_t>{}.deallocate(pressure, pressureSize);
    }
    assert(reader.value->stream->Read(&byte, 1, &got) == S_OK && got == 1 && byte == 0x75);
}

class PackedCopySink final : public IStream {
public:
    std::function<void()> afterWrite;
    ULONG limit = (std::numeric_limits<ULONG>::max)(), largest = 0;
    HRESULT result = S_OK;
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void** output) override {
        if (!output) return E_POINTER;
        *output = nullptr;
        if (iid != __uuidof(IUnknown) && iid != __uuidof(ISequentialStream) && iid != __uuidof(IStream)) return E_NOINTERFACE;
        *output = static_cast<IStream*>(this); AddRef(); return S_OK;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return ++refs_; }
    ULONG STDMETHODCALLTYPE Release() override { const auto count = --refs_; if (!count) delete this; return count; }
    HRESULT STDMETHODCALLTYPE Write(const void*, ULONG count, ULONG* written) override {
        assert(count <= Format::blockBytes); largest = std::max(largest, count);
        if (written) *written = std::min(count, limit);
        if (afterWrite) afterWrite();
        return result;
    }
    HRESULT STDMETHODCALLTYPE Read(void*, ULONG, ULONG*) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE Seek(LARGE_INTEGER, DWORD, ULARGE_INTEGER*) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE SetSize(ULARGE_INTEGER) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE CopyTo(IStream*, ULARGE_INTEGER, ULARGE_INTEGER*, ULARGE_INTEGER*) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE Commit(DWORD) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE Revert() override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE LockRegion(ULARGE_INTEGER, ULARGE_INTEGER, DWORD) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE UnlockRegion(ULARGE_INTEGER, ULARGE_INTEGER, DWORD) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE Stat(STATSTG*, DWORD) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE Clone(IStream**) override { return E_NOTIMPL; }
private:
    ULONG refs_ = 1;
};
void packedReaderCopy() {
    Fixture fixture;
    auto owner = fixture.create();
    fixture.tail(owner, 2, CustodyBytes{1, 3, 5});
    auto tree = verified(owner, 2, 3, 1);
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    ULARGE_INTEGER count{}, read{}, written{}; count.QuadPart = 4;
    {
        auto source = openProtectedCustodyReader(tree, cancelled); assert(source.ok());
        Microsoft::WRL::ComPtr<IStream> target;
        assert(CreateStreamOnHGlobal(nullptr, TRUE, &target) == S_OK);
        assert(source.value->stream->CopyTo(target.Get(), count, &read, &written) == S_FALSE && read.QuadPart == 3 && written.QuadPart == 3);
        assert(target->Seek({}, STREAM_SEEK_SET, nullptr) == S_OK);
        std::array<std::uint8_t, 3> bytes{}; ULONG got = 0;
        assert(target->Read(bytes.data(), 3, &got) == S_OK && got == 3 && (bytes == std::array<std::uint8_t, 3>{1, 3, 5}));
    }
    for (const auto failure : {S_OK, STG_E_WRITEFAULT}) {
        auto source = openProtectedCustodyReader(tree, cancelled); assert(source.ok());
        Microsoft::WRL::ComPtr<PackedCopySink> target; target.Attach(new PackedCopySink);
        target->limit = 2; target->result = failure;
        assert(source.value->stream->CopyTo(target.Get(), count, &read, &written) == (failure == S_OK ? STG_E_MEDIUMFULL : failure));
        assert(read.QuadPart == 3 && written.QuadPart == 2);
    }
    {
        auto source = openProtectedCustodyReader(tree, cancelled); assert(source.ok());
        Microsoft::WRL::ComPtr<PackedCopySink> target; target.Attach(new PackedCopySink);
        auto* actual = source.value->stream.Get();
        target->afterWrite = [&] {
            source.value.reset(); // CopyTo must hold the actual source, not just counters.
            tree.reset(); owner.reset();
            fixture.denyExternalWriter();
            STATSTG stat{}; assert(actual->Stat(&stat, STATFLAG_NONAME) == S_OK); // No IO mutex held across callback.
            target.Reset(); // Destination is held too, while its callback is executing.
            cancelled->store(true);
        };
        assert(actual->CopyTo(target.Get(), count, &read, &written) == HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED));
        assert(!source.value && !target && read.QuadPart == 3 && written.QuadPart == 3);
        cancelled->store(false);
    }
    auto cold = fixture.open(CustodyFileAccess::readExisting); assert(cold.ok());
    const auto proof = verified(*cold.value, 2, 3, 1); assert(proof);
}
void liveResize() {
    Fixture fixture;
    {
        auto owner = fixture.create();
        auto tree = verified(owner, 1, 0, 0);
        const auto noop = tree->setSize(0);
        assert(noop.state == CustodyCommitState::committed && noop.snapshot == tree);
        const auto first = tree->appendBlock(CustodyBytes{1, 3, 5, 7}); assert(first.snapshot);
        const auto old = first.snapshot;
        auto reader = openProtectedCustodyReader(old, std::make_shared<std::atomic<bool>>(false)); assert(reader.ok());
        Microsoft::WRL::ComPtr<IStream> clone; assert(reader.value->stream->Clone(&clone) == S_OK);
        const auto shortened = old->setSize(2); assert(shortened.snapshot);
        tree = shortened.snapshot;
        assert(tree->readBlock(0).value->bytes == CustodyBytes({1, 3}));
        const auto grown = tree->setSize(Format::logicalLimit); assert(grown.snapshot);
        tree = grown.snapshot;
        auto prefix = tree->readBlock(0); assert(prefix.ok());
        assert(prefix.value->bytes.size() == Format::blockBytes && prefix.value->bytes[0] == 1 && prefix.value->bytes[1] == 3);
        assert(std::all_of(prefix.value->bytes.begin()+2, prefix.value->bytes.end(), [](auto byte) { return byte == 0; }));
        for (const auto block : {1ULL, 63ULL, 64ULL, 4095ULL, 4096ULL, 262143ULL}) {
            const auto zero = tree->readBlock(block); assert(zero.ok());
            assert(zero.value->bytes == CustodyBytes(Format::blockBytes, 0));
        }
        assert(old->readBlock(0).value->bytes == CustodyBytes({1, 3, 5, 7}));
        STATSTG stat{}; ULONG got = 0; std::array<std::uint8_t, 4> output{};
        assert(clone->Stat(&stat, STATFLAG_NONAME) == S_OK && stat.cbSize.QuadPart == 4);
        assert(clone->Read(output.data(), 4, &got) == S_OK && got == 4 && (output == std::array<std::uint8_t, 4>{1, 3, 5, 7}));
        const auto before = std::filesystem::file_size(fixture.content());
        assert(old->setSize(4).error == CustodyFileError::conflict);
        assert(tree->setSize(Format::logicalLimit+1).error == CustodyFileError::invalidInput);
        assert(std::filesystem::file_size(fixture.content()) == before);
        for (const std::uint64_t length : {1ULL, 262143ULL, 262144ULL, 262145ULL, 0ULL, 5ULL}) {
            const auto at = std::filesystem::file_size(fixture.content());
            const auto result = tree->setSize(length);
            assert(result.state == CustodyCommitState::committed && result.snapshot);
            assert(result.snapshot->generation() == tree->generation()+1 && result.snapshot->logicalBytes() == length);
            assert(std::filesystem::file_size(fixture.content())-at <= 327680);
            tree = result.snapshot;
            const auto same = tree->setSize(length);
            assert(same.state == CustodyCommitState::committed && same.snapshot == tree);
            noBytesBeyondEOF(tree, (length+Format::blockBytes-1)/Format::blockBytes);
        }
        assert(tree->readBlock(0).value->bytes == CustodyBytes(5, 0));
        owner->revokeWrites();
        assert(tree->setSize(5).error == CustodyFileError::writerFailed);
        assert(tree->readBlock(0).ok());
    }
    auto opened = fixture.open(CustodyFileAccess::readExisting); assert(opened.ok());
    auto reopened = Tree::verify(*opened.value); assert(reopened.ok());
    assert((*reopened.value)->logicalBytes() == 5 && (*reopened.value)->readBlock(0).value->bytes == CustodyBytes(5, 0));
}
void liveShortBlock() {
    Fixture fixture;
    auto owner = fixture.create();
    const auto birth = verified(owner, 1, 0, 0);
    const CustodyBytes bytes{1, 3, 5};
    const auto committed = birth->appendBlock(bytes);
    assert(committed.state == CustodyCommitState::committed && committed.snapshot);
    assert(committed.snapshot->logicalBytes() == bytes.size());
    const auto read = committed.snapshot->readBlock(0);
    assert(read.ok() && read.value->bytes == bytes);
}
void liveResizeBoundaries() {
    for (const std::uint64_t index : {0ULL, 63ULL, 64ULL, 4095ULL, 4096ULL, 262143ULL}) {
        Fixture fixture;
        const auto length = index*Format::blockBytes+7;
        {
            auto owner = fixture.create();
            auto initial = verified(owner, 1, 0, 0);
            const auto expanded = initial->setSize(length); assert(expanded.snapshot);
            auto tree = expanded.snapshot;
            if (index) {
                const auto prefix = tree->replaceBlock(0, CustodyBytes(Format::blockBytes, 0x51));
                assert(prefix.snapshot); tree = prefix.snapshot;
            }
            const auto filled = tree->replaceBlock(index, CustodyBytes{1, 3, 5, 7, 9, 11, 13}); assert(filled.snapshot);
            const auto cut = filled.snapshot->setSize(length-4); assert(cut.snapshot);
            const auto at = std::filesystem::file_size(fixture.content());
            const auto regrown = cut.snapshot->setSize(length); assert(regrown.snapshot);
            assert(std::filesystem::file_size(fixture.content())-at <= 327680);
            auto tail = regrown.snapshot->readBlock(index); assert(tail.ok());
            assert(tail.value->bytes == CustodyBytes({1, 3, 5, 0, 0, 0, 0}));
            const auto old = filled.snapshot->readBlock(index); assert(old.ok());
            assert(old.value->bytes == CustodyBytes({1, 3, 5, 7, 9, 11, 13}));
            if (index) {
                const auto prefix = regrown.snapshot->readBlock(0); assert(prefix.ok());
                assert(prefix.value->bytes == CustodyBytes(Format::blockBytes, 0x51));
            }
        }
        auto opened = fixture.open(CustodyFileAccess::readExisting); assert(opened.ok());
        auto reopened = Tree::verify(*opened.value); assert(reopened.ok());
        assert((*reopened.value)->logicalBytes() == length);
        const auto tail = (*reopened.value)->readBlock(index); assert(tail.ok());
        assert(tail.value->bytes == CustodyBytes({1, 3, 5, 0, 0, 0, 0}));
    }
    Fixture fixture;
    auto owner = fixture.create();
    auto tree = verified(owner, 1, 0, 0);
    const auto at = std::filesystem::file_size(fixture.content());
    {
        std::array<CustodyNativeJob, 4> held;
        for (const auto& job : held) assert(job);
        assert(tree->setSize(1).error == CustodyFileError::allocationFailed);
    }
    {
        std::array<CustodyPin, 30> held;
        for (const auto& pin : held) assert(pin);
        assert(tree->setSize(1).error == CustodyFileError::allocationFailed);
    }
    {
        std::array<CustodyDirtySlot, 4> held;
        for (const auto& slot : held) assert(slot);
        assert(tree->setSize(1).error == CustodyFileError::allocationFailed);
    }
    assert(std::filesystem::file_size(fixture.content()) == at);
    assert(tree->setSize(1).snapshot); // Admission refusals did not poison Owner.
    {
        Fixture exhaustedFixture;
        auto exhaustedOwner = exhaustedFixture.create();
        const auto data = exhaustedFixture.append(exhaustedOwner, Kind::data, 0, 2, CustodyBytes{1, 3, 5});
        const auto root = exhaustedFixture.path(exhaustedOwner, 2, data);
        const auto maximum = (std::numeric_limits<std::uint64_t>::max)();
        exhaustedFixture.publish(exhaustedOwner, 1, maximum-1, exhaustedFixture.headBody(maximum-1, 3, root));
        exhaustedFixture.publish(exhaustedOwner, 0, maximum, exhaustedFixture.headBody(maximum, 3, root));
        const auto full = verified(exhaustedOwner, maximum, 3, 0);
        const auto before = std::filesystem::file_size(exhaustedFixture.content());
        assert(full->setSize(3).snapshot == full); // No new generation for a no-op.
        assert(full->setSize(4).error == CustodyFileError::invalidInput);
        assert(full->setSize(0).error == CustodyFileError::invalidInput);
        assert(std::filesystem::file_size(exhaustedFixture.content()) == before && full->readBlock(0).ok());
    }
}
void liveRewrites() {
    Fixture fixture;
    const CustodyBytes tail{1, 3, 5};
    std::array<CustodyBytes, 3> expected{
        CustodyBytes(Format::blockBytes, 0x31), CustodyBytes(Format::blockBytes, 0x32),
        CustodyBytes(Format::blockBytes, 0x33)};
    const auto assertBytes = [&](const std::shared_ptr<const Tree>& tree,
        const std::array<CustodyBytes, 3>& full) {
        assert(tree->logicalBytes() == 3ULL*Format::blockBytes+tail.size());
        for (std::uint64_t i = 0; i < full.size(); ++i) {
            const auto read = tree->readBlock(i);
            assert(read.ok() && read.value->bytes == full[i]);
        }
        const auto read = tree->readBlock(3);
        assert(read.ok() && read.value->bytes == tail);
        noBytesBeyondEOF(tree, 4);
    };
    {
        auto owner = fixture.create();
        auto tree = verified(owner, 1, 0, 0);
        for (const auto& bytes : expected) {
            const auto appended = tree->appendBlock(bytes); assert(appended.snapshot);
            tree = appended.snapshot;
        }
        const auto appended = tree->appendBlock(tail); assert(appended.snapshot);
        tree = appended.snapshot;
        const auto old = tree;
        const auto original = expected;
        const auto before = std::filesystem::file_size(fixture.content());
        for (const auto index : {4ULL, std::numeric_limits<std::uint64_t>::max()}) {
            const auto refused = tree->replaceBlock(index, expected[0]);
            assert(!refused.snapshot && refused.error == CustodyFileError::invalidInput);
        }
        for (const CustodyBytes bytes : {CustodyBytes{}, CustodyBytes{1}, CustodyBytes(Format::blockBytes+1, 0x55)}) {
            const auto refused = tree->replaceBlock(1, bytes);
            assert(!refused.snapshot && refused.error == CustodyFileError::invalidInput);
        }
        assert(std::filesystem::file_size(fixture.content()) == before);
        assertBytes(tree, expected); // Invalid input did not poison the reader.
        for (const auto index : {1U, 0U, 2U}) {
            expected[index].assign(Format::blockBytes, static_cast<std::uint8_t>(0x60+index));
            const auto at = std::filesystem::file_size(fixture.content());
            const auto rewritten = tree->replaceBlock(index, expected[index]);
            assert(rewritten.snapshot && rewritten.state == CustodyCommitState::committed);
            assert(rewritten.snapshot->generation() == tree->generation()+1);
            assert(std::filesystem::file_size(fixture.content())-at <= 290816);
            tree = rewritten.snapshot;
            assertBytes(tree, expected);
            assertBytes(old, original); // Also after eviction from BOTH HEAD cells.
        }
        const auto at = std::filesystem::file_size(fixture.content());
        const auto stale = old->replaceBlock(1, original[1]);
        assert(!stale.snapshot && stale.error == CustodyFileError::conflict);
        assert(std::filesystem::file_size(fixture.content()) == at);
    }
    auto opened = fixture.open(CustodyFileAccess::readExisting); assert(opened.ok());
    const auto reopened = Tree::verify(*opened.value); assert(reopened.ok());
    assertBytes(*reopened.value, expected); // Cold verification traverses both closures.
}
void liveRewriteBoundaries() {
    for (const std::uint64_t index : {0ULL, 63ULL, 64ULL, 4095ULL, 4096ULL, 262143ULL}) {
        Fixture fixture;
        const CustodyBytes replacement(Format::blockBytes, 0x62);
        const auto assertBytes = [&](const std::shared_ptr<const Tree>& tree) {
            assert(tree->logicalBytes() == Format::logicalLimit);
            const auto read = tree->readBlock(index);
            assert(read.ok() && read.value->bytes == replacement);
            for (const auto neighbor : {index ? index-1 : 1, index == 262143 ? index-1 : index+1}) {
                const auto zero = tree->readBlock(neighbor);
                assert(zero.ok() && zero.value->bytes == CustodyBytes(Format::blockBytes, 0));
            }
            noBytesBeyondEOF(tree, 262144);
        };
        {
            auto owner = fixture.create();
            CustodyBytes body(4096, 0);
            for (std::uint32_t i = 0; i < 64; ++i) putRef(body, i*64U, zeroRef());
            const auto root = fixture.append(owner, Kind::nodeL2, 0, 2, body);
            fixture.publish(owner, 1, 2, fixture.headBody(2, Format::logicalLimit, root));
            const auto base = verified(owner, 2, Format::logicalLimit, 1);
            const auto before = std::filesystem::file_size(fixture.content());
            const auto rewrite = base->replaceBlock(index, replacement);
            assert(rewrite.snapshot && rewrite.state == CustodyCommitState::committed);
            assert(std::filesystem::file_size(fixture.content())-before <= 290816);
            assertBytes(rewrite.snapshot);
            const auto old = base->readBlock(index);
            assert(old.ok() && old.value->bytes == CustodyBytes(Format::blockBytes, 0));
        }
        auto opened = fixture.open(CustodyFileAccess::readExisting); assert(opened.ok());
        const auto checked = Tree::verify(*opened.value); assert(checked.ok());
        assertBytes(*checked.value);
    }
}
void liveTailReplacements() {
    for (const auto size : {1U, 3U, Format::blockBytes-1, Format::blockBytes}) {
        Fixture fixture;
        {
            auto owner = fixture.create();
            auto tree = verified(owner, 1, 0, 0);
            const CustodyBytes original(size, 0x29);
            const auto first = tree->appendBlock(original);
            assert(first.snapshot && first.snapshot->logicalBytes() == size);
            tree = first.snapshot;
            const auto assertBytes = [](const std::shared_ptr<const Tree>& snapshot, const CustodyBytes& expected) {
                const auto read = snapshot->readBlock(0);
                assert(read.ok() && read.value->bytes == expected);
                noBytesBeyondEOF(snapshot, 1);
            };
            assertBytes(tree, original);
            if (size < Format::blockBytes) {
                const auto before = std::filesystem::file_size(fixture.content());
                const auto invalid = tree->replaceBlock(0, CustodyBytes(size-1, 0x55));
                assert(!invalid.snapshot && invalid.error == CustodyFileError::invalidInput);
                const auto unaligned = tree->appendBlock(CustodyBytes{0x55});
                assert(!unaligned.snapshot && unaligned.error == CustodyFileError::invalidInput);
                assert(std::filesystem::file_size(fixture.content()) == before);
                {
                    std::array<CustodyNativeJob, 4> jobs;
                    const auto refused = tree->replaceBlock(0, original);
                    assert(!refused.snapshot && refused.error == CustodyFileError::allocationFailed);
                }
                {
                    std::array<CustodyPin, 29> pins; // Owner + birth + first + 29 = 32.
                    const auto refused = tree->replaceBlock(0, original);
                    assert(!refused.snapshot && refused.error == CustodyFileError::allocationFailed);
                }
                {
                    std::array<CustodyDirtySlot, 4> slots;
                    const auto refused = tree->replaceBlock(0, original);
                    assert(!refused.snapshot && refused.error == CustodyFileError::allocationFailed);
                }
                assert(std::filesystem::file_size(fixture.content()) == before);
                const auto rewrite = tree->replaceBlock(0, CustodyBytes(size, 0x41));
                assert(rewrite.snapshot && rewrite.snapshot->generation() == 3 && rewrite.snapshot->logicalBytes() == size);
                assertBytes(rewrite.snapshot, CustodyBytes(size, 0x41));
                const auto grow = rewrite.snapshot->replaceBlock(0, CustodyBytes(size+1, 0x52));
                assert(grow.snapshot && grow.snapshot->logicalBytes() == size+1);
                assertBytes(grow.snapshot, CustodyBytes(size+1, 0x52));
                // g2 has been evicted from both cells. Its exact short bytes remain pinned.
                assertBytes(first.snapshot, original);
                const auto staleAt = std::filesystem::file_size(fixture.content());
                const auto stale = first.snapshot->replaceBlock(0, original);
                assert(!stale.snapshot && stale.error == CustodyFileError::conflict);
                assert(std::filesystem::file_size(fixture.content()) == staleAt);
                if (size+1 < Format::blockBytes) {
                    const auto filled = grow.snapshot->replaceBlock(0, CustodyBytes(Format::blockBytes, 0x63));
                    assert(filled.snapshot && filled.snapshot->logicalBytes() == Format::blockBytes);
                    tree = filled.snapshot;
                } else tree = grow.snapshot;
                assertBytes(first.snapshot, original);
            }
            const auto aligned = tree->replaceBlock(0, CustodyBytes(Format::blockBytes-1, 0x72));
            assert(!aligned.snapshot && aligned.error == CustodyFileError::invalidInput);
            const CustodyBytes replacement(Format::blockBytes, 0x72);
            const auto full = tree->replaceBlock(0, replacement);
            assert(full.snapshot && full.snapshot->logicalBytes() == Format::blockBytes);
            assertBytes(full.snapshot, replacement); // Last full block at aligned EOF, not just interior.
            tree = full.snapshot;
            const auto last = tree->appendBlock(CustodyBytes{0x7f});
            assert(last.snapshot && last.snapshot->logicalBytes() == Format::blockBytes+1ULL);
            const auto tail = last.snapshot->readBlock(1);
            assert(tail.ok() && tail.value->bytes == CustodyBytes{0x7f});
        } // Release all continuous owners before cold verification of BOTH heads.
        auto reopened = fixture.open(CustodyFileAccess::readExisting); assert(reopened.ok());
        auto checked = Tree::verify(*reopened.value); assert(checked.ok());
        assert((*checked.value)->logicalBytes() == Format::blockBytes+1ULL);
        const auto tail = (*checked.value)->readBlock(1);
        assert(tail.ok() && tail.value->bytes == CustodyBytes{0x7f});
        noBytesBeyondEOF(*checked.value, 2);
    }
    Fixture fixture;
    auto owner = fixture.create();
    const auto empty = verified(owner, 1, 0, 0);
    const auto before = std::filesystem::file_size(fixture.content());
    for (const CustodyBytes bytes : {CustodyBytes{}, CustodyBytes(Format::blockBytes+1, 0x55)}) {
        assert(empty->appendBlock(bytes).error == CustodyFileError::invalidInput);
        assert(empty->replaceBlock(0, bytes).error == CustodyFileError::invalidInput);
    }
    assert(empty->replaceBlock(0, CustodyBytes{1}).error == CustodyFileError::invalidInput);
    assert(std::filesystem::file_size(fixture.content()) == before);
}
void liveFullBlocks() {
    Fixture fixture;
    auto owner = fixture.create();
    auto tree = verified(owner, 1, 0, 0);
    std::shared_ptr<const Tree> first;
    {
        const CustodyBytes bytes(Format::blockBytes, 0x55);
        const auto before = std::filesystem::file_size(fixture.content());
        {
            std::array<CustodyNativeJob, 4> jobs;
            for (const auto& job : jobs) assert(job);
            const auto denied = tree->appendBlock(bytes);
            assert(denied.error == CustodyFileError::allocationFailed && !denied.snapshot);
        }
        {
            std::array<CustodyPin, 30> pins; // Owner + Tree + 30 = exact process cap.
            for (const auto& pin : pins) assert(pin);
            const auto denied = tree->appendBlock(bytes);
            assert(denied.error == CustodyFileError::allocationFailed && !denied.snapshot);
        }
        {
            std::array<CustodyDirtySlot, 4> slots;
            for (const auto& slot : slots) assert(slot);
            const auto denied = tree->appendBlock(bytes);
            assert(denied.error == CustodyFileError::allocationFailed && !denied.snapshot);
        }
        assert(std::filesystem::file_size(fixture.content()) == before);
    }
    for (std::uint64_t block = 0; block < 3; ++block) {
        std::array<CustodyNativeJob, 3> jobs;
        for (const auto& job : jobs) assert(job); // Only ONE borrowed worker job is left.
        CustodyBytes bytes(Format::blockBytes, static_cast<std::uint8_t>(0x31 + block));
        const auto before = std::filesystem::file_size(fixture.content());
        const auto commit = tree->appendBlock(bytes);
        assert(commit.state == CustodyCommitState::committed && commit.error == CustodyFileError::none);
        assert(commit.snapshot && commit.snapshot->generation() == block + 2);
        assert(commit.snapshot->logicalBytes() == (block + 1) * Format::blockBytes);
        assert(commit.snapshot->selectedSlot() == (block + 1) % 2);
        assert(std::filesystem::file_size(fixture.content()) - before <= 290816);
        const auto read = commit.snapshot->readBlock(block);
        assert(read.ok() && read.value->bytes == bytes);
        tree = commit.snapshot;
        if (!first) first = tree;
    }
    // g2 is no longer in either HEAD, but its pinned bytes still belong to it.
    assert(first->generation() == 2 && first->logicalBytes() == Format::blockBytes);
    const auto old = first->readBlock(0);
    assert(old.ok() && old.value->bytes == CustodyBytes(Format::blockBytes, 0x31));
    const auto before = std::filesystem::file_size(fixture.content());
    const auto stale = first->appendBlock(CustodyBytes(Format::blockBytes, 0x55));
    assert(stale.state == CustodyCommitState::notCommitted && !stale.snapshot);
    assert(stale.error == CustodyFileError::conflict && std::filesystem::file_size(fixture.content()) == before);
    tree.reset(); first.reset(); owner.reset();
}
void liveBoundaries() {
    {
        Fixture fixture;
        auto owner = fixture.create();
        const auto birth = verified(owner, 1, 0, 0);
        const CustodyBytes bytes(Format::blockBytes, 0x33);
        const auto second = birth->appendBlock(bytes); assert(second.snapshot);
        const auto third = second.snapshot->appendBlock(bytes); assert(third.snapshot);
        auto otherPeer = fixture.headBody(2, 0, PackedReference{});
        put64(otherPeer, 16, Format::appendOffset);
        fixture.publish(owner, 1, 2, otherPeer);
        // Both heads valid, highest g3 unchanged: only exact peer freshness differs.
        const auto current = verified(owner, 3, 2ULL*Format::blockBytes, 0);
        const auto before = std::filesystem::file_size(fixture.content());
        const auto refused = third.snapshot->appendBlock(bytes);
        assert(refused.error == CustodyFileError::conflict && !refused.snapshot);
        assert(std::filesystem::file_size(fixture.content()) == before && current->readBlock(1).ok());
        const auto emptyInput = current->appendBlock(CustodyBytes{});
        assert(emptyInput.error == CustodyFileError::invalidInput && !emptyInput.snapshot);
        assert(std::filesystem::file_size(fixture.content()) == before);
    }
    for (const std::uint32_t blocks : {1U, 63U, 64U, 4095U, 4096U, 262143U}) {
        Fixture fixture;
        auto owner = fixture.create();
        // Compact ZERO prefix: no giant data fixture or per-block memory.
        CustodyBytes body(4096, 0);
        for (std::uint32_t slot = 0; slot < 64 && slot*4096U < blocks; ++slot)
            putRef(body, slot*64U, zeroRef());
        const auto root = fixture.append(owner, Kind::nodeL2, 0, 2, body);
        const auto length = std::uint64_t{blocks}*Format::blockBytes;
        fixture.publish(owner, 1, 2, fixture.headBody(2, length, root));
        const auto base = verified(owner, 2, length, 1);
        const CustodyBytes shortBytes{0x6d, 0x71, 0x7b};
        const auto before = std::filesystem::file_size(fixture.content());
        const auto committed = base->appendBlock(shortBytes);
        assert(committed.state == CustodyCommitState::committed && committed.snapshot);
        assert(std::filesystem::file_size(fixture.content())-before <= 290816);
        const auto appended = committed.snapshot->readBlock(blocks);
        assert(appended.ok() && appended.value->bytes == shortBytes);
        const auto prefix = committed.snapshot->readBlock(blocks-1);
        assert(prefix.ok() && std::all_of(prefix.value->bytes.begin(), prefix.value->bytes.end(), [](auto b) { return b == 0; }));
        assert(committed.snapshot->logicalBytes() == length+shortBytes.size());
        const CustodyBytes bytes(Format::blockBytes, 0x6d);
        const auto replacementAt = std::filesystem::file_size(fixture.content());
        const auto filled = committed.snapshot->replaceBlock(blocks, bytes);
        assert(filled.snapshot && filled.snapshot->logicalBytes() == length+Format::blockBytes);
        assert(std::filesystem::file_size(fixture.content())-replacementAt <= 290816);
        const auto full = verified(owner, 4, length+Format::blockBytes, 1);
        const auto final = full->readBlock(blocks);
        assert(final.ok() && final.value->bytes == bytes);
        const auto old = committed.snapshot->readBlock(blocks);
        assert(old.ok() && old.value->bytes == shortBytes);
        if (blocks == 262143) {
            const auto end = std::filesystem::file_size(fixture.content());
            const auto overflow = full->appendBlock(bytes);
            assert(overflow.error == CustodyFileError::invalidInput && !overflow.snapshot);
            assert(std::filesystem::file_size(fixture.content()) == end);
        }
    }
    {
        Fixture fixture;
        auto owner = fixture.create();
        fixture.tail(owner, 2, CustodyBytes{1, 3, 5});
        const auto tail = verified(owner, 2, 3, 1);
        const auto before = std::filesystem::file_size(fixture.content());
        const auto refused = tail->appendBlock(CustodyBytes(Format::blockBytes, 0x33));
        assert(refused.error == CustodyFileError::invalidInput && !refused.snapshot);
        assert(std::filesystem::file_size(fixture.content()) == before && tail->readBlock(0).ok());
    }
    {
        Fixture fixture;
        auto owner = fixture.create();
        const auto last = std::numeric_limits<std::uint64_t>::max();
        for (std::uint32_t slot = 0; slot < 2; ++slot) {
            const auto generation = last-slot;
            auto body = fixture.headBody(generation, 0, PackedReference{});
            put64(body, 16, Format::appendOffset);
            fixture.publish(owner, slot, generation, body);
        }
        const auto exhausted = verified(owner, last, 0, 0);
        const auto before = std::filesystem::file_size(fixture.content());
        const auto refused = exhausted->appendBlock(CustodyBytes(Format::blockBytes, 0x33));
        assert(refused.error == CustodyFileError::invalidInput && !refused.snapshot);
        assert(std::filesystem::file_size(fixture.content()) == before);
    }
    {
        Fixture fixture;
        auto owner = fixture.create();
        const auto last = std::numeric_limits<std::uint64_t>::max();
        fixture.tail(owner, last-1, CustodyBytes{1, 3, 5});
        fixture.tail(owner, last, CustodyBytes{2, 4, 6});
        const auto exhausted = verified(owner, last, 3, 0);
        const auto before = std::filesystem::file_size(fixture.content());
        const auto refused = exhausted->replaceBlock(0, CustodyBytes{1, 3, 5, 7});
        assert(refused.error == CustodyFileError::invalidInput && !refused.snapshot);
        assert(std::filesystem::file_size(fixture.content()) == before && exhausted->readBlock(0).ok());
    }
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
    {
        auto reader = openProtectedCustodyReader(tree, std::make_shared<std::atomic<bool>>(false)); assert(reader.ok());
        LARGE_INTEGER offset{}; offset.QuadPart = -3;
        assert(reader.value->stream->Seek(offset, STREAM_SEEK_END, nullptr) == S_OK);
        std::array<std::uint8_t, 5> bytes{1, 1, 1, 1, 1}; ULONG got = 0;
        assert(reader.value->stream->Read(bytes.data(), 5, &got) == S_FALSE && got == 3);
        assert((bytes == std::array<std::uint8_t, 5>{0, 0, 0, 1, 1}));
    }
    const auto read = tree->readBlock(4095);
    assert(read.ok() && read.value->bytes.size() == Format::blockBytes - 1);
    assert(std::all_of(read.value->bytes.begin(), read.value->bytes.end(), [](auto byte) { return byte == 0; }));
    noBytesBeyondEOF(tree, 4096);
    const CustodyBytes replacement(Format::blockBytes, 0x62);
    const auto filled = tree->replaceBlock(4095, replacement);
    assert(filled.snapshot && filled.snapshot->logicalBytes() == length+1);
    const auto actual = filled.snapshot->readBlock(4095);
    assert(actual.ok() && actual.value->bytes == replacement);
    const auto prefix = filled.snapshot->readBlock(4094);
    assert(prefix.ok() && prefix.value->bytes == CustodyBytes(Format::blockBytes, 0));
    const auto old = tree->readBlock(4095);
    assert(old.ok() && old.value->bytes.size() == Format::blockBytes-1);
}

enum class BadDescriptor { count, blockSize, radix, depth, flags, reserved, extent, shortExtent, tail, fullTail, emptyRoot, zeroRoot };
void descriptors() {
    for (const auto bad : {BadDescriptor::count, BadDescriptor::blockSize, BadDescriptor::radix,
        BadDescriptor::depth, BadDescriptor::flags, BadDescriptor::reserved, BadDescriptor::extent,
        BadDescriptor::shortExtent, BadDescriptor::tail, BadDescriptor::fullTail, BadDescriptor::emptyRoot, BadDescriptor::zeroRoot}) {
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
        case BadDescriptor::fullTail: put64(body, 8, Format::blockBytes); break;
        case BadDescriptor::emptyRoot: putRef(body, 48, PackedReference{}); break;
        case BadDescriptor::zeroRoot: putRef(body, 48, zeroRef()); break;
        }
        if (bad == BadDescriptor::fullTail) {
            const auto decoded = Format::decodeDescriptor(body.data(), body.size(), 2, std::filesystem::file_size(fixture.content()));
            assert(decoded && decoded->blockCount == 1 && decoded->logicalBytes == Format::blockBytes);
        } // Descriptor/framing are valid; authenticated short DATA must fail full-block semantics.
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

void coldRetainedRoots() {
    for (const auto role : {CustodyRole::canonical, CustodyRole::media, CustodyRole::playback}) {
        Fixture fixture;
        fixture.context.object.role = role;
        const CustodyBytes oldBytes{0x13, 0x35, 0x57};
        PackedRootDescriptor stamp;
        {
            auto owner = fixture.create();
            fixture.tail(owner, 2, oldBytes);
            stamp = verified(owner, 2, oldBytes.size(), 1)->descriptor();
            fixture.tail(owner, 3, CustodyBytes{0x24, 0x46});
            fixture.tail(owner, 4, CustodyBytes{0x68});
        } // No old owner, Tree, reader or RAM proof survives this ownership gap.
        auto opened = fixture.open(CustodyFileAccess::writeExisting); assert(opened.ok());
        auto owner = std::move(*opened.value);
        auto current = verified(owner, 4, 1, 1);
        auto checked = Tree::verifyRetained(owner, fixture.context, stamp); assert(checked.ok());
        auto retained = std::move(*checked.value);
        assert(retained->descriptor() == stamp && retained->generation() == 2 && retained->logicalBytes() == oldBytes.size());
        assert(retained->readBlock(0).value->bytes == oldBytes);
        noBytesBeyondEOF(retained, 1);
        const auto before = owner->appendPosition(); assert(before.ok());
        for (const auto result : {retained->appendBlock(oldBytes), retained->replaceBlock(0, oldBytes),
            retained->setSize(0), retained->setSize(retained->logicalBytes())}) {
            assert(result.state == CustodyCommitState::notCommitted && !result.snapshot && result.lease == retained);
            assert(result.error == CustodyFileError::conflict);
        }
        auto writer = ProtectedCustodyWriter::open(retained, std::make_shared<std::atomic<bool>>(false));
        assert(!writer.ok() && writer.error == CustodyFileError::conflict);
        const auto after = owner->appendPosition(); assert(after.ok() && after.value == before.value);
        // A healthy readonly rejection must not revoke the genuine current writer.
        auto resized = current->setSize(2);
        assert(resized.state == CustodyCommitState::committed && resized.snapshot->generation() == 5);
        assert(retained->readBlock(0).value->bytes == oldBytes);
        const auto cancelled = std::make_shared<std::atomic<bool>>(false);
        auto reader = openProtectedCustodyReader(retained, cancelled); assert(reader.ok());
        Microsoft::WRL::ComPtr<IStream> clone;
        assert(reader.value->stream->Clone(&clone) == S_OK);
        assert(retained->checkRead().ok());
        auto genuineWriter = ProtectedCustodyWriter::open(resized.snapshot, cancelled); assert(genuineWriter.ok());
        genuineWriter.value.reset(); // Healthy writer release revokes writes, not historical reads.
        current.reset(); retained.reset(); resized.snapshot.reset(); resized.lease.reset();
        owner.reset(); opened.value.reset(); checked.value.reset();
        fixture.denyExternalWriter(); // Only Reader/Clone now retain the actual HANDLE.
        std::array<std::uint8_t, 4> bytes{}; ULONG got = 0;
        assert(clone->Read(bytes.data(), 4, &got) == S_FALSE && got == 3);
        assert(std::equal(oldBytes.begin(), oldBytes.end(), bytes.begin()));
        cancelled->store(true);
        assert(reader.value->stream->Read(bytes.data(), 1, &got) == HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED) && got == 0);
    }
}

void retainedStampRejections() {
    for (unsigned fault = 0; fault < 14; ++fault) {
        Fixture fixture;
        auto owner = fixture.create();
        fixture.tail(owner, 2, CustodyBytes{1, 2, 3});
        auto stamp = verified(owner, 2, 3, 1)->descriptor();
        fixture.tail(owner, 3, CustodyBytes{4});
        const auto lowerExtent = verified(owner, 3, 1, 0)->descriptor().committedExtent;
        fixture.tail(owner, 4, CustodyBytes{5, 6});
        const auto current = verified(owner, 4, 2, 1);
        auto context = fixture.context;
        switch (fault) {
        case 0: context.object.storeId[0] ^= 1; break;
        case 1: context.object.objectId[0] ^= 1; break;
        case 2: context.object.role = CustodyRole::media; break;
        case 3: context.containerId[0] ^= 1; break;
        case 4: stamp.generation = 5; break;
        case 5: stamp = current->descriptor(); ++stamp.committedExtent; break;
        case 6: stamp.generation = 3; break; // Same lower generation, different full descriptor.
        case 7: stamp.committedExtent = lowerExtent+1; break; // Below highest/actual EOF, above newer lower peer.
        case 8: ++stamp.blockCount; break;
        case 9: stamp.logicalBytes = Format::logicalLimit+1; break;
        case 10: stamp.root.version = 3; break;
        case 11: stamp.root.offset = stamp.committedExtent; break;
        case 12: stamp.root.envelopeSha[0] ^= 1; break;
        case 13: stamp.generation = 1; break;
        }
        const auto bad = Tree::verifyRetained(owner, context, stamp);
        assert(!bad.ok() && bad.error != CustodyFileError::none);
        const auto repeat = Tree::verifyRetained(owner, fixture.context, current->descriptor());
        assert(!repeat.ok() && repeat.error == bad.error && repeat.nativeError == bad.nativeError);
        const auto mutation = current->setSize(current->logicalBytes());
        assert(!mutation.snapshot && mutation.error == bad.error && mutation.nativeError == bad.nativeError);
    }
}

void retainedClosureAndEmpty() {
    for (unsigned corrupted = 0; corrupted < 6; ++corrupted) {
        Fixture fixture;
        PackedRootDescriptor stamp;
        std::array<std::uint64_t, 4> offsets{};
        {
            auto owner = fixture.create();
            const auto data = fixture.append(owner, Kind::data, 0, 2, CustodyBytes{1, 2, 3});
            const auto leaf = fixture.node(owner, Kind::nodeL0, 0, 2, data);
            const auto middle = fixture.node(owner, Kind::nodeL1, 0, 2, leaf);
            const auto root = fixture.node(owner, Kind::nodeL2, 0, 2, middle);
            fixture.publish(owner, 1, 2, fixture.headBody(2, 3, root));
            stamp = verified(owner, 2, 3, 1)->descriptor();
            offsets = {data.offset, leaf.offset, middle.offset, root.offset};
            fixture.tail(owner, 3, CustodyBytes{4});
            fixture.tail(owner, 4, CustodyBytes{5});
        }
        fixture.corrupt(corrupted < 4 ? offsets[corrupted] + 16 : corrupted == 4 ? 128+16 : 16512+16);
        auto owner = fixture.open(CustodyFileAccess::readExisting); assert(owner.ok());
        if (corrupted < 4) assert(Tree::verify(*owner.value).ok()); // Neither current head reaches the corrupt old record.
        const auto rejected = Tree::verifyRetained(*owner.value, fixture.context, stamp);
        assert(!rejected.ok() && rejected.error != CustodyFileError::none);
        assert(!Tree::verify(*owner.value).ok()); // Full historical observation latches the shared owner.
    }
    Fixture fixture;
    auto owner = fixture.create();
    const auto birth = verified(owner, 1, 0, 0)->descriptor();
    auto tree = verified(owner, 1, 0, 0);
    auto expanded = tree->setSize(Format::logicalLimit); assert(expanded.snapshot);
    const auto large = expanded.snapshot->descriptor();
    auto empty = expanded.snapshot->setSize(0); assert(empty.snapshot);
    const auto emptyStamp = empty.snapshot->descriptor();
    auto grown = empty.snapshot->setSize(1); assert(grown.snapshot);
    for (const auto& stamp : {birth, emptyStamp, large}) {
        const auto result = Tree::verifyRetained(owner, fixture.context, stamp); assert(result.ok());
        assert((*result.value)->logicalBytes() == stamp.logicalBytes);
        if (stamp.logicalBytes) {
            const auto tail = (*result.value)->readBlock(stamp.blockCount-1);
            assert(tail.ok() && tail.value->bytes.size() == Format::blockBytes);
            assert(std::all_of(tail.value->bytes.begin(), tail.value->bytes.end(), [](auto b) { return b == 0; }));
        } else noBytesBeyondEOF(*result.value, 0);
        assert((*result.value)->setSize(stamp.logicalBytes).error == CustodyFileError::conflict);
    }
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
void retainedAdmissions() {
    Fixture fixture;
    auto owner = fixture.create();
    const auto current = verified(owner, 1, 0, 0);
    const auto stamp = current->descriptor();
    {
        std::array<CustodyPin, 30> held;
        for (const auto& pin : held) assert(pin);
        const auto rejected = Tree::verifyRetained(owner, fixture.context, stamp);
        assert(!rejected.ok() && rejected.error == CustodyFileError::allocationFailed);
    }
    {
        std::array<CustodyNativeJob, 4> held;
        for (const auto& job : held) assert(job);
        const auto rejected = Tree::verifyRetained(owner, fixture.context, stamp);
        assert(!rejected.ok() && rejected.error == CustodyFileError::allocationFailed);
    }
    assert(current->checkRead().ok()); // Admission refusal is not observed corruption.
    const auto retained = Tree::verifyRetained(owner, fixture.context, stamp); assert(retained.ok());
    assert((*retained.value)->setSize(0).error == CustodyFileError::conflict);
    assert(current->setSize(0).state == CustodyCommitState::committed);
    {
        ChargedPressure pressure(0);
        const auto rejected = Tree::verifyRetained(owner, fixture.context, stamp);
        assert(!rejected.ok() && rejected.error == CustodyFileError::allocationFailed);
    }
    const auto repeated = Tree::verifyRetained(owner, fixture.context, stamp);
    assert(!repeated.ok() && repeated.error == CustodyFileError::allocationFailed);
    // An already observed physical allocation fault precedes readonly conflict.
    assert((*retained.value)->setSize(0).error == CustodyFileError::allocationFailed);
}
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
    const auto retainedMissing = Tree::verifyRetained(nullptr, {{{}, {}, CustodyRole::canonical}, {}}, {});
    assert(!retainedMissing.ok() && retainedMissing.error == CustodyFileError::invalidInput);
#ifdef _WIN32
    const auto beforeCache = CustodyOwnedMemory::usedBytes();
    const auto emptyCharge = emptyProxyCharge();
    assert(CustodyOwnedMemory::usedBytes() == beforeCache);
    {
        Fixture fixture;
        auto owner = fixture.create();
        auto tree = verified(owner, 1, 0, 0);
        auto reader = openProtectedCustodyReader(tree, std::make_shared<std::atomic<bool>>(false));
        assert(reader.ok());
        STATSTG stat{}; ULONG got = 9; std::uint8_t byte = 0x77;
        assert(reader.value->stream->Stat(&stat, STATFLAG_NONAME) == S_OK && stat.cbSize.QuadPart == 0);
        assert(reader.value->stream->Read(nullptr, 0, &got) == S_OK && got == 0);
        assert(reader.value->stream->Read(&byte, 1, &got) == S_FALSE && got == 0 && byte == 0x77);
    }
    std::fprintf(stderr, "reader-cache empty_proxy_charge=%zu observed_delta=%zu\n",
        emptyCharge, CustodyOwnedMemory::usedBytes()-beforeCache);
    assert(CustodyOwnedMemory::usedBytes() == beforeCache+emptyCharge);
    // Baseline includes only the independently measured EMPTY process-static cache.
    const auto before = CustodyOwnedMemory::usedBytes();
    if (argc == 2 && std::strcmp(argv[1], "--reader-release-drain") == 0) {
        readerReleaseDrain(); packedReaderAdmission();
        assert(CustodyOwnedMemory::usedBytes() == before);
        return 0;
    }
    birth();
    packedWriter();
    packedReader();
    readerReleaseDrain();
    packedReaderAdmission();
    packedReaderCopy();
    liveShortBlock();
    liveResize();
    liveResizeBoundaries();
    liveRewrites();
    liveRewriteBoundaries();
    liveTailReplacements();
    liveFullBlocks();
    liveBoundaries();
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
    coldRetainedRoots();
    sealedPackedMember();
    livePackedMember();
    mixedPackageGroup();
    retainedStampRejections();
    retainedClosureAndEmpty();
    retainedAdmissions();
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
