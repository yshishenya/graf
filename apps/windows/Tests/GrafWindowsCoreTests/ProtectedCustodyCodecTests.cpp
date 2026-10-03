#include "../../RecApp/Storage/ProtectedCustodyCodec.h"
#include "../../RecApp/Storage/ProtectedCustodyFiles.h" // Snapshot value only; no file/authority operations.
#include "../../RecApp/Storage/Sha256.h"
#ifdef _WIN32
#include <windows.h>
#include <dpapi.h>
#endif
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <algorithm>
#include <cstring>
#include <limits>
#include <string>
#include <utility>
#include <atomic>
#include <cstdlib>
#include <thread>
#include <cstdio>
#include <type_traits>
#ifdef _MSC_VER
#include <crtdbg.h>
#endif

// Only this synthetic test executable replaces allocation. The real std allocator
// still runs; one selected operator-new failure verifies reservation rollback.
namespace { std::atomic<std::size_t> failAllocationBytes{0}; }
void* operator new(std::size_t bytes) {
    auto expected = bytes;
    if (bytes != 0 && failAllocationBytes.compare_exchange_strong(expected, 0)) throw std::bad_alloc();
    if (auto* memory = std::malloc(bytes == 0 ? 1 : bytes)) return memory;
    throw std::bad_alloc();
}
void operator delete(void* memory) noexcept { std::free(memory); }
void operator delete(void* memory, std::size_t) noexcept { std::free(memory); }

using namespace graf::windows;
namespace {
using IndexEntries = decltype(CustodyIndex::entries);
static_assert(!std::is_nothrow_default_constructible_v<IndexEntries>);
static_assert(!std::is_nothrow_move_constructible_v<IndexEntries>);
static_assert(std::is_nothrow_move_assignable_v<IndexEntries>);
static_assert(!std::is_nothrow_default_constructible_v<CustodyIndex>);
static_assert(!std::is_nothrow_move_constructible_v<CustodyIndex>);
static_assert(std::is_nothrow_move_assignable_v<CustodyIndex>);
static_assert(!std::is_nothrow_default_constructible_v<CustodySnapshot>);
static_assert(!std::is_nothrow_move_constructible_v<CustodySnapshot>);
static_assert(std::is_nothrow_move_assignable_v<CustodySnapshot>);

// Raw reservation has no default vector/proxy allocation of its own. These
// synthetic bytes are never read or written; this is not an N-record fixture.
struct EntriesPressure {
    CustodyAllocator<std::uint8_t> allocator;
    std::size_t count;
    std::uint8_t* bytes;
    EntriesPressure() : count(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes()),
        bytes(allocator.allocate(count)) {
        assert(count != 0 && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
    }
    ~EntriesPressure() { allocator.deallocate(bytes, count); }
    EntriesPressure(const EntriesPressure&) = delete;
    EntriesPressure& operator=(const EntriesPressure&) = delete;
};
void assertEntry(const CustodyIndexEntry& entry, std::uint64_t version, std::uint32_t envelope, std::uint32_t flags) {
    assert(entry.version == version && entry.envelopeBytes == envelope && entry.flags == flags);
}
void assertSeed(const CustodyIndex& index) {
    assert(index.generation == 17 && index.logicalLength == 262148 && index.entries.size() == 2);
    assertEntry(index.entries[0], 5, 273, 0);
    assertEntry(index.entries[1], 0, 0, 1);
}
void entriesMoveAssignmentBudget() {
    const auto baseline = CustodyOwnedMemory::usedBytes();
    {
        CustodyIndex source{17, 262148, {{5, 273, 0}, {0, 0, 1}}};
        CustodyIndex target{8, 4, {{9, 141, 0}}};
        target.entries.reserve(5);
        const auto* sourceData = source.entries.data();
        const auto sourceCapacity = source.entries.capacity();
        const auto* oldTargetData = target.entries.data();
        const auto oldTargetCapacity = target.entries.capacity();
        {
            EntriesPressure pressure;
            const auto charged = CustodyOwnedMemory::usedBytes();
            target = std::move(source); // Entries assignment must not allocate a new proxy.
            assertSeed(target);
            assert(target.entries.data() == sourceData && target.entries.capacity() == sourceCapacity);
            // A valid equal-allocator transfer may free target's old storage or
            // swap it into the moved-from source; neither may add a new charge.
            if (source.entries.empty()) {
                assert(source.entries.capacity() == 0);
                assert(CustodyOwnedMemory::usedBytes() == charged - oldTargetCapacity * sizeof(CustodyIndexEntry));
            } else {
                assert(source.entries.data() == oldTargetData && source.entries.capacity() == oldTargetCapacity);
                assert(source.entries.size() == 1);
                assertEntry(source.entries[0], 9, 141, 0);
                assert(CustodyOwnedMemory::usedBytes() == charged);
            }
        }
        {
            EntriesPressure pressure;
            const auto charged = CustodyOwnedMemory::usedBytes();
            auto& alias = target;
            target = std::move(alias); // Self-move must preserve exact value/storage.
            assertSeed(target);
            assert(target.entries.data() == sourceData && target.entries.capacity() == sourceCapacity);
            assert(CustodyOwnedMemory::usedBytes() == charged);
        }
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
}
void entriesMoveBudgetTests() {
    const auto baseline = CustodyOwnedMemory::usedBytes();
    std::size_t proxyCharge = 0;
    {
        const auto used = CustodyOwnedMemory::usedBytes();
        IndexEntries empty;
        assert(empty.empty());
        proxyCharge = CustodyOwnedMemory::usedBytes() - used;
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
    std::size_t indexProxyCharge = 0, snapshotProxyCharge = 0;
    {
        const auto used = CustodyOwnedMemory::usedBytes();
        CustodyIndex empty;
        assert(empty.entries.empty());
        indexProxyCharge = CustodyOwnedMemory::usedBytes() - used;
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline && indexProxyCharge == proxyCharge);
    {
        const auto used = CustodyOwnedMemory::usedBytes();
        CustodySnapshot empty;
        assert(empty.index.entries.empty());
        snapshotProxyCharge = CustodyOwnedMemory::usedBytes() - used;
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline && snapshotProxyCharge == proxyCharge);
    // Product policy landed: throwing constructor traits are now compile gates.
    std::fprintf(stderr, "entries-move-budget proxy=%zu index_proxy=%zu snapshot_proxy=%zu traits entries_default=%u entries_move=%u index_default=%u index_move=%u snapshot_default=%u snapshot_move=%u assignment=%u\n",
        proxyCharge, indexProxyCharge, snapshotProxyCharge,
        static_cast<unsigned>(std::is_nothrow_default_constructible_v<IndexEntries>),
        static_cast<unsigned>(std::is_nothrow_move_constructible_v<IndexEntries>),
        static_cast<unsigned>(std::is_nothrow_default_constructible_v<CustodyIndex>),
        static_cast<unsigned>(std::is_nothrow_move_constructible_v<CustodyIndex>),
        static_cast<unsigned>(std::is_nothrow_default_constructible_v<CustodySnapshot>),
        static_cast<unsigned>(std::is_nothrow_move_constructible_v<CustodySnapshot>),
        static_cast<unsigned>(std::is_nothrow_move_assignable_v<CustodyIndex>));
    if (proxyCharge == 0) {
        std::fputs("entries-move-budget SKIP allocation-fault-proof: no charged iterator proxy\n", stderr);
        // Assignment/self-move still require preservation and no allocation.
        entriesMoveAssignmentBudget();
        assert(CustodyOwnedMemory::usedBytes() == baseline);
        return;
    }
    {
        CustodyIndex source{17, 262148, {{5, 273, 0}, {0, 0, 1}}};
        const auto* data = source.entries.data();
        const auto capacity = source.entries.capacity();
        std::fputs("entries-move-budget stage=index-move\n", stderr);
        {
            EntriesPressure pressure;
            bool caught = false;
            try { CustodyIndex moved(std::move(source)); }
            catch (const std::bad_alloc&) { caught = true; }
            assert(caught && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
            assertSeed(source);
            assert(source.entries.data() == data && source.entries.capacity() == capacity);
        }
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
    {
        IndexEntries source{{5, 273, 0}, {0, 0, 1}};
        const auto* data = source.data();
        const auto capacity = source.capacity();
        std::fputs("entries-move-budget stage=entries-move\n", stderr);
        {
            EntriesPressure pressure;
            bool caught = false;
            try { IndexEntries moved(std::move(source)); }
            catch (const std::bad_alloc&) { caught = true; }
            assert(caught && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
            assert(source.data() == data && source.capacity() == capacity && source.size() == 2);
            assertEntry(source[0], 5, 273, 0);
            assertEntry(source[1], 0, 0, 1);
        }
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
    {
        std::fputs("entries-move-budget stage=default-construction\n", stderr);
        EntriesPressure pressure;
        bool entriesCaught = false, indexCaught = false, snapshotCaught = false;
        try { IndexEntries empty; }
        catch (const std::bad_alloc&) { entriesCaught = true; }
        assert(entriesCaught && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
        try { CustodyIndex empty; }
        catch (const std::bad_alloc&) { indexCaught = true; }
        assert(indexCaught && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
        try { CustodySnapshot empty; }
        catch (const std::bad_alloc&) { snapshotCaught = true; }
        assert(snapshotCaught && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
    {
        CustodySnapshot source{CustodyIndex{17, 262148, {{5, 273, 0}, {0, 0, 1}}},
            CustodySnapshotState::verified, CustodyFileError::invalidContent, 23};
        const auto* data = source.index.entries.data();
        const auto capacity = source.index.entries.capacity();
        std::fputs("entries-move-budget stage=snapshot-value-move\n", stderr);
        {
            EntriesPressure pressure;
            bool caught = false;
            try { CustodySnapshot moved(std::move(source)); }
            catch (const std::bad_alloc&) { caught = true; }
            assert(caught && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
            assertSeed(source.index);
            assert(source.index.entries.data() == data && source.index.entries.capacity() == capacity);
            assert(source.state == CustodySnapshotState::verified &&
                source.recoveryError == CustodyFileError::invalidContent && source.nativeError == 23);
        }
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
    entriesMoveAssignmentBudget();
    assert(CustodyOwnedMemory::usedBytes() == baseline);
    std::fputs("entries-move-budget caught-default/move failures; assignment/self-move/cleanup complete\n", stderr);
}
CustodyContext context() {
    CustodyContext c{{}, {}, CustodyRole::canonical};
    c.storeId[0] = 7; c.objectId[15] = 9;
    return c;
}
void memoryBudgetTests(const CustodyContext& c) {
    using Memory = CustodyOwnedMemory;
    constexpr auto limit = Memory::limit;
    assert(Memory::usedBytes() == 0);
    std::size_t byteProxy = 0, indexProxy = 0;
    { CustodyBytes empty; byteProxy = Memory::usedBytes(); }
    { CustodyIndex empty; indexProxy = Memory::usedBytes(); }
    assert(Memory::usedBytes() == 0);
    {
        CustodyBytes a; a.reserve(4096); a.resize(8, 42);
        CustodyIndex index; index.entries.reserve(8);
        auto b = a; // Copy reserves its actual capacity, not the source's capacity.
        const auto charged = a.capacity() + b.capacity() + index.entries.capacity() * sizeof(CustodyIndexEntry)
            + 2 * byteProxy + indexProxy;
        assert(Memory::usedBytes() == charged);
        CustodyBytes moved(std::move(a));
        assert(Memory::usedBytes() == charged + byteProxy);
        std::optional<CustodyBytes> retained(std::move(moved));
        b.clear(); // Live capacity remains charged even at size zero.
        assert(Memory::usedBytes() == charged + 2 * byteProxy);
        b.swap(*retained); assert(Memory::usedBytes() == charged + 2 * byteProxy);
    }
    assert(Memory::usedBytes() == 0);
    {
        CustodyBytes large; large.reserve(40 * 1024 * 1024); large.push_back(42);
        const auto charged = Memory::usedBytes(); auto* original = large.data();
        bool rejected = false;
        try { large.reserve(48 * 1024 * 1024); } catch (const std::bad_alloc&) { rejected = true; }
        assert(rejected && large.data() == original && large.size() == 1 && large[0] == 42);
        assert(Memory::usedBytes() == charged); // Old+new, not merely growth delta.
        large.clear(); assert(Memory::usedBytes() == charged);
        CustodyBytes{}.swap(large); assert(Memory::usedBytes() == byteProxy);
    }
    {
        CustodyBytes full; full.reserve(limit - Memory::usedBytes());
        bool rejected = false;
        try { CustodyBytes extra(1); } catch (const std::bad_alloc&) { rejected = true; }
        assert(rejected && Memory::usedBytes() == limit);
    }
    assert(Memory::usedBytes() == 0);
    bool overflow = false;
    try { (void)CustodyAllocator<CustodyIndexEntry>{}.allocate(std::numeric_limits<std::size_t>::max()); }
    catch (const std::bad_alloc&) { overflow = true; }
    assert(overflow && Memory::usedBytes() == 0);
    {
        // Small allocation: MSVC adds alignment overhead to operator-new requests
        // at 4096 bytes and above. Test the real failure, not a guessed big size.
        CustodyBytes bytes; failAllocationBytes = 1024;
        const auto before = Memory::usedBytes();
        bool rejected = false;
        try { bytes.reserve(1024); } catch (const std::bad_alloc&) { rejected = true; }
        assert(rejected && failAllocationBytes == 0 && Memory::usedBytes() == before);
        bytes.reserve(1024); assert(Memory::usedBytes() == before + bytes.capacity());
    }
    {
        // Prepare all proxies before the parallel capacity reservations. Each
        // worker retains its own buffer, including every unsuccessful worker.
        std::array<CustodyBytes, 12> buffers;
        const auto proxyBytes = Memory::usedBytes();
        assert(proxyBytes == buffers.size() * byteProxy && (limit - proxyBytes) % 4 == 0);
        const auto capacity = (limit - proxyBytes) / 4;
        std::atomic<unsigned> attempted{0}, accepted{0}; std::atomic<bool> release{false};
        std::array<std::thread, 12> threads;
        for (std::size_t i = 0; i < threads.size(); ++i) threads[i] = std::thread([&, i] {
            try { buffers[i].reserve(capacity); ++accepted; } catch (const std::bad_alloc&) {}
            ++attempted;
            while (!release.load()) std::this_thread::yield();
        });
        while (attempted.load() != threads.size()) std::this_thread::yield();
        assert(accepted == 4 && Memory::usedBytes() == limit);
        release = true; for (auto& worker : threads) worker.join();
    }
    assert(Memory::usedBytes() == 0);
#ifdef _WIN32
    const CustodyBytes payload{1, 2, 3, 4};
    const auto cipher = ProtectedCustodyCodec::sealBlock(c, 0, 1, payload); assert(cipher.ok());
    const CustodyIndex index{1, 4, {{1, static_cast<std::uint32_t>(cipher.value->size()), 0}}};
    const auto sealed = ProtectedCustodyCodec::sealIndex(c, 0, index); assert(sealed.ok());
    CustodyBytes full; full.reserve(limit - Memory::usedBytes());
    assert(Memory::usedBytes() == limit);
    assert(ProtectedCustodyCodec::sealBlock(c, 0, 1, payload).error == CustodyCodecError::allocationFailed);
    assert(ProtectedCustodyCodec::openBlock(c, 0, 1, 4, *cipher.value).error == CustodyCodecError::allocationFailed);
    assert(ProtectedCustodyCodec::sealIndex(c, 0, index).error == CustodyCodecError::allocationFailed);
    assert(ProtectedCustodyCodec::openIndex(c, 0, *sealed.value).error == CustodyCodecError::allocationFailed);
    assert(Memory::usedBytes() == limit);
#else
    (void)c;
#endif
}
#ifdef _WIN32
void put(CustodyBytes& bytes, std::size_t at, std::uint64_t value, std::size_t count) {
    for (std::size_t i = 0; i < count; ++i) bytes.at(at + i) = static_cast<std::uint8_t>(value >> (i * 8));
}
// Independent test fixture: protect malformed decoded records with the real DPAPI.
// No product crypto injection switch, files, microphone, network or key export.
CustodyBytes entropy(const CustodyContext& c, std::uint16_t kind, std::uint64_t selector, std::uint64_t version) {
    const std::string prefix = "graf.custody.v1";
    CustodyBytes result(prefix.begin(), prefix.end());
    result.insert(result.end(), c.storeId.begin(), c.storeId.end());
    result.insert(result.end(), c.objectId.begin(), c.objectId.end());
    const auto base = result.size(); result.resize(base + 20);
    put(result, base, static_cast<std::uint16_t>(c.role), 2);
    put(result, base + 2, kind, 2); put(result, base + 4, selector, 8); put(result, base + 12, version, 8);
    return result;
}
CustodyBytes nativeBytes(const CustodyContext& c, std::uint16_t kind, std::uint64_t selector,
                        std::uint64_t version, const CustodyBytes& bytes, bool protect) {
    auto binding = entropy(c, kind, selector, version);
    DATA_BLOB input{static_cast<DWORD>(bytes.size()), const_cast<BYTE*>(bytes.data())};
    DATA_BLOB extra{static_cast<DWORD>(binding.size()), binding.data()}, output{};
    const auto ok = protect
        ? CryptProtectData(&input, nullptr, &extra, nullptr, nullptr, CRYPTPROTECT_UI_FORBIDDEN, &output)
        : CryptUnprotectData(&input, nullptr, &extra, nullptr, nullptr, CRYPTPROTECT_UI_FORBIDDEN, &output);
    assert(ok && output.pbData);
    CustodyBytes result(output.pbData, output.pbData + output.cbData);
    SecureZeroMemory(output.pbData, output.cbData); LocalFree(output.pbData);
    return result;
}
CustodyBytes decode(const CustodyContext& c, std::uint16_t kind, std::uint64_t selector,
                   std::uint64_t version, const CustodyBytes& envelope) {
    return nativeBytes(c, kind, selector, version, CustodyBytes(envelope.begin() + 16, envelope.end()), false);
}
CustodyBytes wrap(const CustodyContext& c, std::uint16_t kind, std::uint64_t selector,
                 std::uint64_t version, const CustodyBytes& plain) {
    auto cipher = nativeBytes(c, kind, selector, version, plain, true);
    CustodyBytes out(16); std::memcpy(out.data(), "GRAFDP01", 8);
    put(out, 8, 1, 2); put(out, 10, kind, 2); put(out, 12, cipher.size(), 4);
    out.insert(out.end(), cipher.begin(), cipher.end()); return out;
}
void checksum(CustodyBytes& index) {
    std::fill(index.begin() + 80, index.begin() + 112, std::uint8_t{0});
    const auto digest = sha256(std::string_view(reinterpret_cast<const char*>(index.data()), index.size()));
    for (std::size_t i = 0; i < 32; ++i)
        index[80 + i] = static_cast<std::uint8_t>(std::stoul(digest.substr(i * 2, 2), nullptr, 16));
}
#endif
}

int main(int argc, char** argv) {
#ifdef _MSC_VER
    _set_error_mode(_OUT_TO_STDERR);
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
#ifdef _DEBUG
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
#endif
#endif
    if (argc == 2 && std::strcmp(argv[1], "--entries-move-budget") == 0) {
        entriesMoveBudgetTests();
        return 0;
    }
    using Codec = ProtectedCustodyCodec;
    auto c = context();
    entriesMoveBudgetTests();
    memoryBudgetTests(c);
    assert(CustodyOwnedMemory::usedBytes() == 0);
    assert(Codec::logicalLimit(c.role) == (std::uint64_t{64} << 30));
    assert(Codec::logicalLimit(CustodyRole::manifest) == 4096);
    assert(Codec::logicalLimit(CustodyRole::queue) == 4 * 1024 * 1024);
    assert(Codec::logicalLimit(CustodyRole::recovery) == 64 * 1024);
    assert(Codec::logicalLimit(static_cast<CustodyRole>(0)) == 0);
    assert(Codec::logicalLimit(static_cast<CustodyRole>(10)) == 0);
    assert(Codec::blockEnvelopeLimit(0) == 0);
    assert(Codec::blockEnvelopeLimit(Codec::blockBytes + 1) == 0);
    assert(Codec::blockEnvelopeLimit(Codec::blockBytes) == Codec::blockBytes + 4096);
    assert(Codec::indexEnvelopeLimit(c.role) == 4198400 + 65536);
    assert(Codec::indexEnvelopeLimit(static_cast<CustodyRole>(10)) == 0);
    assert(!Codec::sealBlock(c, 0, 0, CustodyBytes{1}).ok());
    assert(!Codec::sealBlock(c, 262144, 1, CustodyBytes{1}).ok());
    assert(!Codec::sealBlock(c, 0, 1, CustodyBytes{}).ok());
    assert(!Codec::sealBlock(c, 0, 1, CustodyBytes(Codec::blockBytes + 1)).ok());
    assert(!Codec::sealIndex(c, 0, CustodyIndex{}).ok());
    assert(!Codec::sealIndex(c, 2, CustodyIndex{1, 0, {}}).ok());
    assert(!Codec::sealIndex(c, 0, CustodyIndex{2, 0, {}}).ok());
    assert(!Codec::sealIndex(c, 0, CustodyIndex{1, (std::uint64_t{64} << 30) + 1, {}}).ok());
    assert(!Codec::sealIndex(c, 0, CustodyIndex{1, std::numeric_limits<std::uint64_t>::max(), {}}).ok());
    for (const auto entry : {CustodyIndexEntry{0, 18, 0}, CustodyIndexEntry{1, 0, 1},
                             CustodyIndexEntry{0, 17, 1}, CustodyIndexEntry{1, 17, 2},
                             CustodyIndexEntry{1, 4098, 0}, CustodyIndexEntry{1, 16, 0}})
        assert(!Codec::sealIndex(c, 0, CustodyIndex{1, 1, {entry}}).ok());
    for (std::size_t size : {std::size_t{0}, std::size_t{15}, std::size_t{16}}) {
        assert(!Codec::openBlock(c, 0, 1, 1, CustodyBytes(size)).ok());
        assert(!Codec::openIndex(c, 0, CustodyBytes(size)).ok());
    }
#ifdef _WIN32
    for (std::uint32_t size : {1U, 4096U, 65536U, Codec::blockBytes}) {
        CustodyBytes payload(size);
        for (std::size_t i = 0; i < payload.size(); ++i) payload[i] = static_cast<std::uint8_t>(i % 251);
        const auto sealed = Codec::sealBlock(c, 7, 19, payload);
        assert(sealed.ok() && sealed.value->size() <= Codec::blockEnvelopeLimit(size));
        const auto opened = Codec::openBlock(c, 7, 19, size, *sealed.value);
        assert(opened.ok() && *opened.value == payload);
        const auto plain = decode(c, 1, 7, 19, *sealed.value);
        assert(plain.size() == 104 + size && std::memcmp(plain.data(), "GRAFBL01", 8) == 0);
        assert(plain[48] == 7 && plain[56] == 19 && plain[12] == 104);
        auto wrong = c; wrong.storeId[0] ^= 1;
        assert(!Codec::openBlock(wrong, 7, 19, size, *sealed.value).ok());
        wrong = c; wrong.objectId[0] ^= 1;
        assert(!Codec::openBlock(wrong, 7, 19, size, *sealed.value).ok());
        wrong = c; wrong.role = CustodyRole::media;
        assert(!Codec::openBlock(wrong, 7, 19, size, *sealed.value).ok());
        assert(!Codec::openBlock(c, 8, 19, size, *sealed.value).ok());
        assert(!Codec::openBlock(c, 7, 20, size, *sealed.value).ok());
        assert(!Codec::openBlock(c, 7, 19, size == 1 ? 2 : size - 1, *sealed.value).ok());
        for (std::size_t offset : {std::size_t{0}, std::size_t{8}, std::size_t{10}, std::size_t{12}, sealed.value->size() - 1}) {
            auto bad = *sealed.value; bad[offset] ^= 1;
            assert(!Codec::openBlock(c, 7, 19, size, bad).ok());
        }
        auto bad = *sealed.value; bad.pop_back();
        assert(!Codec::openBlock(c, 7, 19, size, bad).ok());
        bad = *sealed.value; bad.push_back(0);
        assert(!Codec::openBlock(c, 7, 19, size, bad).ok());
        for (std::size_t offset : {0U, 8U, 10U, 12U, 16U, 32U, 48U, 56U, 64U, 68U, 72U, 104U}) {
            auto malformed = plain; malformed[offset] ^= 1;
            assert(!Codec::openBlock(c, 7, 19, size, wrap(c, 1, 7, 19, malformed)).ok());
        }
    }
    for (std::uint16_t role = 1; role <= 9; ++role) {
        c.role = static_cast<CustodyRole>(role);
        const auto empty = Codec::sealIndex(c, 0, CustodyIndex{1, 0, {}});
        assert(empty.ok()); const auto reopened = Codec::openIndex(c, 0, *empty.value);
        assert(reopened.ok() && reopened.value->entries.empty() && reopened.value->logicalLength == 0);
        assert(!Codec::openIndex(c, 1, *empty.value).ok()); // slot binding, even at birth
        const auto atLimit = Codec::logicalLimit(c.role);
        const auto count = static_cast<std::size_t>(atLimit / Codec::blockBytes + (atLimit % Codec::blockBytes != 0));
        CustodyIndex index{3, atLimit, {}}; index.entries.assign(count, CustodyIndexEntry{0, 0, 1});
        const auto sealed = Codec::sealIndex(c, 0, index); assert(sealed.ok());
        const auto valid = Codec::openIndex(c, 0, *sealed.value); assert(valid.ok() && valid.value->entries.size() == count);
        index.logicalLength++; assert(!Codec::sealIndex(c, 0, index).ok());
    }
    c = context();
    const auto block = Codec::sealBlock(c, 0, 4, CustodyBytes{1}); assert(block.ok());
    CustodyIndex index{2, 1, {{4, static_cast<std::uint32_t>(block.value->size()), 0}}};
    const auto sealed = Codec::sealIndex(c, 1, index); assert(sealed.ok());
    const auto valid = Codec::openIndex(c, 1, *sealed.value);
    assert(valid.ok() && valid.value->generation == 2 && valid.value->entries[0].version == 4);
    const auto plain = decode(c, 2, 1, 0, *sealed.value);
    assert(plain.size() == 128 && std::memcmp(plain.data(), "GRAFIX01", 8) == 0);
    assert(plain[12] == 112 && plain[66] == 4 && plain[72] == 0);
    for (std::size_t offset : {0U, 8U, 10U, 12U, 16U, 32U, 48U, 56U, 64U, 68U, 72U, 80U, 112U, 120U, 124U}) {
        auto malformed = plain; malformed[offset] ^= 1;
        assert(!Codec::openIndex(c, 1, wrap(c, 2, 1, 0, malformed)).ok());
    }
    // A valid checksum cannot make a structurally invalid decrypted index valid.
    for (const auto field : {std::pair<std::size_t, std::uint64_t>{68, 0xffffffff}, {72, 1},
                            {124, 2}, {120, 0}, {64, 1}, {48, 0}}) {
        auto malformed = plain; put(malformed, field.first, field.second, field.first == 48 || field.first == 72 ? 8 : 4);
        checksum(malformed);
        assert(!Codec::openIndex(c, 1, wrap(c, 2, 1, 0, malformed)).ok());
    }
#else
    assert(Codec::sealBlock(c, 0, 1, CustodyBytes{1}).error == CustodyCodecError::unsupportedPlatform);
    assert(Codec::sealIndex(c, 0, CustodyIndex{1, 0, {}}).error == CustodyCodecError::unsupportedPlatform);
#endif
}
