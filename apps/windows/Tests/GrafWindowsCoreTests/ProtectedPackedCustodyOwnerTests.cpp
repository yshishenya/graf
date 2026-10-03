#include "../../RecApp/Storage/ProtectedPackedCustodyOwner.h"
#include "../../RecApp/Storage/ProtectedPackedCustodyTree.h"
#include "../../RecApp/Storage/ProtectedCustodyPrimitives.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>
#include <algorithm>
#ifdef _WIN32
#include <windows.h>
#include <sddl.h>
#include <objbase.h>
#include <vector>
#include <array>
#include <new>
#include <thread>
#include <type_traits>
#include <chrono>
#include <atomic>
#ifdef _MSC_VER
#include <crtdbg.h>
#include <cstdlib>
#endif

static_assert(!std::is_copy_assignable_v<graf::windows::CustodyNativeJob>);
static_assert(!std::is_move_assignable_v<graf::windows::CustodyNativeJob>);

namespace {
enum class Fault { none, write, shortWrite, zeroWrite, flush, read, changedRead, throwingRead, streamEnd, throwingMetadata, invalidSize };
Fault fault = Fault::none;
unsigned writes = 0, reads = 0, flushes = 0, metadataQueries = 0, ordinal = 1;
bool inspectUnwindAdmission = false, failureRetainedJob = false;
HANDLE faultReached = nullptr, writerReady = nullptr;
bool requireCompetingJobAdmission = false;
std::atomic<bool> competingJobObserved{false}, competingWriterFinished{false};
struct MetadataAllocationFailure final : std::bad_alloc {
    ~MetadataAllocationFailure() override {
        if (inspectUnwindAdmission) {
            std::array<graf::windows::CustodyNativeJob, 4> probes;
            failureRetainedJob = probes[0] && probes[1] && probes[2] && !probes[3];
        }
    }
};
void inject(Fault value, unsigned at = 1) { fault = value; ordinal = at; writes = reads = flushes = metadataQueries = 0; }
BOOL WINAPI testWrite(HANDLE file, LPCVOID bytes, DWORD count, LPDWORD done, LPOVERLAPPED operation) {
    assert(count <= 262144); ++writes;
    if (writes == ordinal) {
        if (fault == Fault::write) { SetLastError(ERROR_WRITE_FAULT); return FALSE; }
        if (fault == Fault::zeroWrite) { *done = 0; return TRUE; }
        if (fault == Fault::shortWrite) return WriteFile(file, bytes, count - 1, done, operation);
    }
    return WriteFile(file, bytes, count, done, operation);
}
BOOL WINAPI testRead(HANDLE file, LPVOID bytes, DWORD count, LPDWORD done, LPOVERLAPPED operation) {
    assert(count <= 262144); ++reads;
    if (reads == ordinal) {
        if (fault == Fault::read) { SetLastError(ERROR_READ_FAULT); return FALSE; }
        if (fault == Fault::throwingRead) throw std::bad_alloc();
    }
    const auto result = ReadFile(file, bytes, count, done, operation);
    if (result && *done && reads == ordinal && fault == Fault::changedRead) static_cast<std::uint8_t*>(bytes)[0] ^= 1;
    return result;
}
BOOL WINAPI testFlush(HANDLE file) {
    ++flushes;
    if (flushes == ordinal && fault == Fault::flush) { SetLastError(ERROR_WRITE_FAULT); return FALSE; }
    return FlushFileBuffers(file);
}
BOOL WINAPI testNextStream(HANDLE search, LPVOID data) {
    if (fault == Fault::streamEnd) { SetLastError(ERROR_ACCESS_DENIED); return FALSE; }
    return FindNextStreamW(search, data);
}
HANDLE WINAPI testFirstStream(LPCWSTR name, STREAM_INFO_LEVELS level, LPVOID data, DWORD flags) {
    ++metadataQueries;
    if (fault == Fault::throwingMetadata && metadataQueries == ordinal) {
        if (faultReached) {
            assert(SetEvent(faultReached));
            assert(WaitForSingleObject(writerReady, 5000) == WAIT_OBJECT_0);
            if (requireCompetingJobAdmission) {
                // This wrapper runs inside the verifier's final metadata check:
                // its Guard still owns ONE job and the SAME State mutex.
                std::array<graf::windows::CustodyNativeJob, 2> probes;
                assert(probes[0] && probes[1]);
                const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
                do {
                    bool thirdAdmitted = false;
                    {
                        graf::windows::CustodyNativeJob third;
                        thirdAdmitted = bool(third);
                    }
                    assert(!competingWriterFinished.load(std::memory_order_acquire));
                    if (!thirdAdmitted) {
                        // verifier1 + publisher1 + probes2 = cap4. Readiness
                        // alone is NOT this observation. Publisher's admitted
                        // job must remain held while it waits on this mutex.
                        competingJobObserved.store(true, std::memory_order_release);
                        break;
                    }
                    std::this_thread::yield();
                } while (std::chrono::steady_clock::now() < deadline);
                assert(competingJobObserved.load(std::memory_order_acquire));
                assert(!competingWriterFinished.load(std::memory_order_acquire));
            }
        }
        throw MetadataAllocationFailure();
    }
    return FindFirstStreamW(name, level, data, flags);
}
BOOL WINAPI testSize(HANDLE file, PLARGE_INTEGER size) {
    if (fault == Fault::invalidSize) { size->QuadPart = 32895; return TRUE; }
    return GetFileSizeEx(file, size);
}
}
// Compile the REAL shared file layer with TU-local faults, not product knobs.
#define WriteFile testWrite
#define ReadFile testRead
#define FlushFileBuffers testFlush
#define FindNextStreamW testNextStream
#define FindFirstStreamW testFirstStream
#define GetFileSizeEx testSize
#include "../../RecApp/Storage/ProtectedCustodyFiles.cpp"
#undef WriteFile
#undef ReadFile
#undef FlushFileBuffers
#undef FindNextStreamW
#undef FindFirstStreamW
#undef GetFileSizeEx

using namespace graf::windows;
namespace {
struct Fixture {
    std::filesystem::path root;
    PSECURITY_DESCRIPTOR descriptor = nullptr;
    SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), nullptr, FALSE};
    PackedCustodyContext context{{{}, {}, CustodyRole::canonical}, {}};
    Fixture() {
        HANDLE token = nullptr; assert(OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token));
        DWORD count = 0; GetTokenInformation(token, TokenUser, nullptr, 0, &count);
        std::vector<std::uint8_t> bytes(count);
        assert(GetTokenInformation(token, TokenUser, bytes.data(), count, &count)); CloseHandle(token);
        LPWSTR sid = nullptr; assert(ConvertSidToStringSidW(reinterpret_cast<TOKEN_USER*>(bytes.data())->User.Sid, &sid));
        const auto sddl = std::wstring(L"D:P(A;OICI;FA;;;") + sid + L")"; LocalFree(sid);
        assert(ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl.c_str(), SDDL_REVISION_1, &descriptor, nullptr));
        security.lpSecurityDescriptor = descriptor;
        wchar_t temporary[MAX_PATH]{}, actual[MAX_PATH]{};
        assert(GetTempPathW(MAX_PATH, temporary)); assert(GetLongPathNameW(temporary, actual, MAX_PATH));
        GUID id{}; wchar_t text[40]{}; assert(CoCreateGuid(&id) == S_OK); assert(StringFromGUID2(id, text, 40));
        root = std::filesystem::path(actual) / (std::wstring(L"graf-packed-owner-") + text);
        assert(CreateDirectoryW(root.c_str(), &security));
        assert(CreateDirectoryW((root / L".custody-v1").c_str(), &security));
        assert(CreateDirectoryW((root / L"package-a").c_str(), &security));
        context.object.storeId[0] = 7; context.object.objectId[15] = 9; context.containerId[0] = 11;
        HANDLE file = CreateFileW((root / L".custody-v1" / L"store.id").c_str(), GENERIC_WRITE, 0,
            &security, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
        assert(file != INVALID_HANDLE_VALUE); DWORD written = 0;
        assert(WriteFile(file, context.object.storeId.data(), 16, &written, nullptr) && written == 16);
        assert(FlushFileBuffers(file)); CloseHandle(file);
    }
    ~Fixture() {
        std::error_code error; std::filesystem::remove_all(root, error); assert(!error);
        LocalFree(descriptor);
    }
    auto open(CustodyFileAccess access) { return ProtectedPackedCustodyOwner::open(root, "package-a", context, access); }
    auto content() const { return root / L"package-a" / L".custody-v1" / L"canonical" / L"content.packed-v2"; }
};
void deniedWriter(const Fixture& fixture) {
    HANDLE file = CreateFileW(fixture.content().c_str(), GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE,
        nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    assert(file == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
}
CustodyBytes head(const Fixture& fixture) {
    CustodyBytes body(128, 0);
    body[0] = 2; body[16] = 128; body[17] = 128; // generation2, extent32896.
    body[26] = 4; body[32] = 64; body[36] = 3; // block262144, radix64, depth3.
    auto sealed = ProtectedPackedCustodyCodec::seal(fixture.context,
        {PackedRecordKind::head, 16512, 1, 2, 128}, body);
    assert(sealed.ok()); return std::move(*sealed.value);
}
void faults() {
    for (const auto selected : {Fault::write, Fault::shortWrite, Fault::zeroWrite, Fault::flush,
                               Fault::read, Fault::changedRead, Fault::throwingRead}) {
        Fixture fixture;
        auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        auto& owner = **opened.value;
        const auto sealed = head(fixture);
        inject(selected);
        const auto result = owner.publishHead(1, sealed);
        assert(result.state == CustodyPublishState::ambiguous && result.error != CustodyFileError::none);
        const std::array<unsigned, 3> counts{writes, reads, flushes};
        const auto repeated = owner.publishHead(1, sealed);
        assert(repeated.state == CustodyPublishState::ambiguous && repeated.error == result.error);
        assert(!owner.flush().ok() && !owner.readCiphertext(0, 128).ok());
        assert((counts == std::array<unsigned, 3>{writes, reads, flushes}));
        assert(std::filesystem::exists(fixture.content())); // Preserve partial/actual publication.
        inject(Fault::none);
    }
    for (const auto selected : {Fault::write, Fault::shortWrite, Fault::zeroWrite}) {
        Fixture fixture;
        auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        CustodyBytes payload(262144, 0x37);
        const PackedRecordAddress address{PackedRecordKind::data, 32896, 0, 2, 262144};
        const auto sealed = ProtectedPackedCustodyCodec::seal(fixture.context, address, payload); assert(sealed.ok());
        inject(selected, 2); // Cut second chunk of max-size DATA envelope.
        auto result = (*opened.value)->append(address, *sealed.value);
        assert(!result.ok() && writes == 2);
        const auto count = writes;
        assert(!(*opened.value)->append(address, *sealed.value).ok() && writes == count);
        assert(std::filesystem::file_size(fixture.content()) >= 32896 + 262144);
        inject(Fault::none);
    }
    {
        Fixture fixture; auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        inject(Fault::streamEnd);
        assert(!(*opened.value)->readCiphertext(0, 128).ok()); // Unknown ADS enumeration is not empty.
        assert(writes == 0 && reads == 0);
        inject(Fault::none);
        assert(!(*opened.value)->readCiphertext(0, 128).ok()); // Observed fault remains sticky.
    }
}
void admission() {
    Fixture fixture; auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
    {
        std::array<CustodyNativeJob, 4> occupied;
        for (const auto& job : occupied) assert(job);
        inject(Fault::none);
        assert(!(*opened.value)->readCiphertext(0, 128).ok());
        assert(reads == 0 && writes == 0 && flushes == 0);
    }
    {
        std::vector<PackedCipherRead> results;
        for (unsigned i = 0; i < 31; ++i) {
            auto read = (*opened.value)->readCiphertext(0, 128); assert(read.ok());
            results.push_back(std::move(*read.value));
        }
        inject(Fault::none);
        assert(!(*opened.value)->readCiphertext(0, 128).ok());
        assert(reads == 0 && writes == 0 && flushes == 0);
    }
    assert((*opened.value)->readCiphertext(0, 128).ok());
    {
        // Construct the vector first: MSVC Debug also charges its iterator proxy.
        CustodyBytes occupied;
        occupied.resize(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
        inject(Fault::none);
        const auto failed = (*opened.value)->readCiphertext(0, 128);
        assert(!failed.ok() && failed.error == CustodyFileError::allocationFailed);
        assert(reads == 0 && writes == 0 && flushes == 0);
    }
    const auto repeated = (*opened.value)->readCiphertext(0, 128);
    assert(!repeated.ok() && repeated.error == CustodyFileError::allocationFailed); // Preserve the exact sticky fault.
}
void boundsAndAllocation() {
    {
        Fixture fixture; auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        inject(Fault::throwingMetadata);
        for (const auto count : {0U, 266241U, 0xffffffffU}) {
            const auto invalid = (*opened.value)->readCiphertext(0, count);
            assert(!invalid.ok() && invalid.error == CustodyFileError::invalidInput);
        }
        const auto overflow = (*opened.value)->readCiphertext(0x7fffffffffffffffULL, 128);
        assert(!overflow.ok() && overflow.error == CustodyFileError::invalidInput);
        inject(Fault::none);
        assert((*opened.value)->readCiphertext(0, 128).ok()); // No metadata IO or poisoned owner on invalid bounds.
    }
    for (unsigned operation = 0; operation < 4; ++operation) {
        Fixture fixture; auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        const PackedRecordAddress address{PackedRecordKind::data, 32896, 0, 2, 8};
        const auto envelope = ProtectedPackedCustodyCodec::seal(fixture.context, address, CustodyBytes(8, 0x53));
        assert(envelope.ok());
        inject(Fault::throwingMetadata);
        inspectUnwindAdmission = true; failureRetainedJob = false;
        bool escaped = false; CustodyFileError error = CustodyFileError::none;
        try {
            switch (operation) {
            case 0: error = (*opened.value)->appendPosition().error; break;
            case 1: error = (*opened.value)->flush().error; break;
            case 2: error = (*opened.value)->readCiphertext(0, 128).error; break;
            default: error = (*opened.value)->append(address, *envelope.value).error; break;
            }
        } catch (const std::bad_alloc&) { escaped = true; }
        inspectUnwindAdmission = false;
        inject(Fault::none);
        assert(!escaped && error == CustodyFileError::allocationFailed && failureRetainedJob);
        const auto repeated = (*opened.value)->readCiphertext(0, 128);
        assert(!repeated.ok() && repeated.error == CustodyFileError::allocationFailed);
        assert(reads == 0 && writes == 0 && flushes == 0);
    }
}
void postEffectAllocation() {
    for (const bool publish : {false, true}) {
        Fixture fixture; auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        const auto sealed = head(fixture);
        inject(Fault::none);
        if (publish) assert((*opened.value)->publishHead(1, sealed).state == CustodyPublishState::published);
        else assert((*opened.value)->flush().ok());
        assert(metadataQueries > 0 && metadataQueries % 2 == 0);
        const auto afterEffect = metadataQueries / 2 + 1;
        inject(Fault::throwingMetadata, afterEffect); // First path query AFTER successful native flush/readback.
        inspectUnwindAdmission = true; failureRetainedJob = false;
        if (publish) {
            const auto result = (*opened.value)->publishHead(1, sealed);
            assert(result.state == CustodyPublishState::ambiguous && result.error == CustodyFileError::allocationFailed);
            assert(writes == 1 && reads == 1);
        } else assert((*opened.value)->flush().error == CustodyFileError::allocationFailed);
        inspectUnwindAdmission = false;
        assert(failureRetainedJob && flushes == 1);
        inject(Fault::none);
        assert((*opened.value)->readCiphertext(0, 128).error == CustodyFileError::allocationFailed);
        assert(writes == 0 && reads == 0 && flushes == 0);
    }
    {
        Fixture fixture; auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        inject(Fault::invalidSize);
        assert((*opened.value)->appendPosition().error == CustodyFileError::invalidContent);
        inject(Fault::none);
        assert((*opened.value)->flush().error == CustodyFileError::invalidContent);
        assert(writes == 0 && reads == 0 && flushes == 0);
    }
    {
        Fixture fixture; auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        const auto sealed = head(fixture);
        inject(Fault::none);
        assert((*opened.value)->publishHead(1, sealed).state == CustodyPublishState::published);
        const auto afterEffect = metadataQueries / 2 + 1;
        faultReached = CreateEventW(nullptr, TRUE, FALSE, nullptr); writerReady = CreateEventW(nullptr, TRUE, FALSE, nullptr);
        assert(faultReached && writerReady);
        inject(Fault::throwingMetadata, afterEffect);
        CustodyFileError competing = CustodyFileError::none;
        std::thread writer([owner = *opened.value, &competing] {
            assert(WaitForSingleObject(faultReached, 5000) == WAIT_OBJECT_0);
            assert(SetEvent(writerReady));
            competing = owner->flush().error;
        });
        const auto failed = (*opened.value)->publishHead(1, sealed);
        writer.join();
        assert(failed.state == CustodyPublishState::ambiguous && failed.error == CustodyFileError::allocationFailed);
        assert(competing == CustodyFileError::allocationFailed && writes == 1 && reads == 1 && flushes == 1);
        CloseHandle(faultReached); CloseHandle(writerReady); faultReached = writerReady = nullptr;
        inject(Fault::none);
    }
}
void confinement() {
    {
        Fixture fixture; auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        opened.value.reset();
        HANDLE file = CreateFileW(fixture.content().c_str(), GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        assert(file != INVALID_HANDLE_VALUE);
        HANDLE mapping = CreateFileMappingW(file, nullptr, PAGE_READWRITE, 0, 0, nullptr); assert(mapping);
        auto* view = static_cast<std::uint8_t*>(MapViewOfFile(mapping, FILE_MAP_WRITE, 0, 0, 0)); assert(view);
        CloseHandle(file);
        auto denied = fixture.open(CustodyFileAccess::writeExisting);
        assert(!denied.ok() && denied.nativeError == ERROR_SHARING_VIOLATION);
        CloseHandle(mapping); // The retained writable VIEW must still exclude acquisition.
        denied = fixture.open(CustodyFileAccess::writeExisting);
        assert(!denied.ok() && denied.nativeError == ERROR_SHARING_VIOLATION);
        assert(UnmapViewOfFile(view));
        auto released = fixture.open(CustodyFileAccess::writeExisting); assert(released.ok());
    }
    {
        Fixture fixture; auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        opened.value.reset();
        const auto alias = fixture.content().parent_path() / L"synthetic-hardlink.bin";
        assert(CreateHardLinkW(alias.c_str(), fixture.content().c_str(), nullptr));
        auto denied = fixture.open(CustodyFileAccess::writeExisting);
        assert(!denied.ok() && denied.error == CustodyFileError::unsafeFile);
        assert(DeleteFileW(alias.c_str()));
        assert(fixture.open(CustodyFileAccess::writeExisting).ok());
    }
    {
        Fixture fixture; auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        const auto streamPath = fixture.content().wstring() + L":synthetic";
        HANDLE stream = CreateFileW(streamPath.c_str(), GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE,
            nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
        assert(stream != INVALID_HANDLE_VALUE); CloseHandle(stream);
        assert(!(*opened.value)->readCiphertext(0, 128).ok());
        assert(!(*opened.value)->flush().ok()); // Named streams cannot be mistaken for default-only.
    }
}
void publication() {
    Fixture fixture; auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
    const auto sealed = head(fixture);
    assert((*opened.value)->publishHead(1, sealed).state == CustodyPublishState::published);
    auto read = (*opened.value)->readCiphertext(16512, 16384); assert(read.ok());
    assert(read.value->bytes == sealed && ProtectedPackedCustodyCodec::openHead(fixture.context, 1, read.value->bytes, 2).ok());
    read.value.reset();
    CustodyBytes payload(262144, 0x24);
    const PackedRecordAddress address{PackedRecordKind::data, 32896, 0, 3, 262144};
    const auto cipher = ProtectedPackedCustodyCodec::seal(fixture.context, address, payload); assert(cipher.ok());
    inject(Fault::none);
    assert((*opened.value)->append(address, *cipher.value).ok() && writes == 2);
    assert((*opened.value)->flush().ok());
    auto data = (*opened.value)->readCiphertext(32896, static_cast<std::uint32_t>(cipher.value->size()));
    assert(data.ok() && data.value->bytes == *cipher.value && reads == 2);
    inject(Fault::none);
    assert(!(*opened.value)->append(address, *cipher.value).ok() && writes == 0); // No overwrite of old DATA.
    assert((*opened.value)->appendPosition().value == ((32896 + cipher.value->size() + 15) & ~std::uint64_t{15}));
}
void treeGuardFaults() {
    {
        Fixture fixture; auto owner = fixture.open(CustodyFileAccess::createNew); assert(owner.ok());
        {
            std::array<CustodyPin, 31> held;
            assert(std::all_of(held.begin(), held.end(), [](const CustodyPin& pin) { return bool(pin); }));
            inject(Fault::read);
            const auto denied = ProtectedPackedCustodyTree::verify(*owner.value);
            assert(!denied.ok() && denied.error == CustodyFileError::allocationFailed);
            assert(reads == 0 && metadataQueries == 0); // Pin admission precedes DFS and owned allocation.
        }
        inject(Fault::none);
        assert(ProtectedPackedCustodyTree::verify(*owner.value).ok()); // Refusal was not an observed disk failure.
    }
    for (const auto selected : {Fault::read, Fault::changedRead, Fault::throwingRead}) {
        Fixture fixture; auto owner = fixture.open(CustodyFileAccess::createNew); assert(owner.ok());
        inject(selected, 2); // prefix is first, then the independently read first HEAD.
        const auto result = ProtectedPackedCustodyTree::verify(*owner.value);
        assert(!result.ok());
        const auto readCount = reads;
        const auto again = ProtectedPackedCustodyTree::verify(*owner.value);
        assert(!again.ok() && again.error == result.error && again.nativeError == result.nativeError && reads == readCount);
        assert(!(*owner.value)->flush().ok());
        if (selected == Fault::read) assert(result.error == CustodyFileError::ioFailed && result.nativeError == ERROR_READ_FAULT);
        if (selected == Fault::throwingRead) assert(result.error == CustodyFileError::allocationFailed);
        inject(Fault::none);
    }
    {
        Fixture fixture; auto owner = fixture.open(CustodyFileAccess::createNew); assert(owner.ok());
        inject(Fault::none);
        auto baseline = ProtectedPackedCustodyTree::verify(*owner.value); assert(baseline.ok());
        const auto lastMetadata = metadataQueries;
        baseline.value.reset();
        inject(Fault::throwingMetadata, lastMetadata);
        inspectUnwindAdmission = true; failureRetainedJob = false;
        const auto failed = ProtectedPackedCustodyTree::verify(*owner.value);
        inspectUnwindAdmission = false;
        assert(!failed.ok() && failed.error == CustodyFileError::allocationFailed && failureRetainedJob);
        assert(reads == 3 && writes == 0 && flushes == 0);
        inject(Fault::none);
    }
    // Observe an ACTUALLY admitted contender after ALL HEAD reads, during the
    // final identity check. Fault classification must precede mutex/job release.
    Fixture fixture; auto owner = fixture.open(CustodyFileAccess::createNew); assert(owner.ok());
    inject(Fault::none);
    auto baseline = ProtectedPackedCustodyTree::verify(*owner.value); assert(baseline.ok());
    const auto lastMetadata = metadataQueries;
    baseline.value.reset();
    const auto nextHead = head(fixture);
    faultReached = CreateEventW(nullptr, TRUE, FALSE, nullptr); writerReady = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    assert(faultReached && writerReady);
    inject(Fault::throwingMetadata, lastMetadata);
    requireCompetingJobAdmission = true;
    competingJobObserved.store(false, std::memory_order_release);
    competingWriterFinished.store(false, std::memory_order_release);
    CustodyPublishResult competing;
    std::thread writer([retained = *owner.value, &competing, &nextHead] {
        assert(WaitForSingleObject(faultReached, 5000) == WAIT_OBJECT_0);
        assert(SetEvent(writerReady));
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
        for (;;) {
            competing = retained->publishHead(1, nextHead);
            if (competingJobObserved.load(std::memory_order_acquire)) break;
            // The sampling third probe can temporarily take the last slot.
            // Retry ONLY a pre-mutex admission refusal, never a disk effect.
            assert(competing.state == CustodyPublishState::notPublished &&
                competing.error == CustodyFileError::allocationFailed && competing.nativeError == 0);
            assert(std::chrono::steady_clock::now() < deadline);
            std::this_thread::yield();
        }
        competingWriterFinished.store(true, std::memory_order_release);
    });
    const auto failed = ProtectedPackedCustodyTree::verify(*owner.value);
    writer.join();
    assert(competingJobObserved.load(std::memory_order_acquire));
    assert(competingWriterFinished.load(std::memory_order_acquire));
    requireCompetingJobAdmission = false;
    assert(!failed.ok() && failed.error == CustodyFileError::allocationFailed &&
        competing.error == failed.error && competing.nativeError == failed.nativeError &&
        competing.state == CustodyPublishState::notPublished);
    assert(reads == 3 && writes == 0 && flushes == 0);
    CloseHandle(faultReached); CloseHandle(writerReady); faultReached = writerReady = nullptr;
    inject(Fault::none);
}
}
#endif

int main() {
    using namespace graf::windows;
#ifdef _MSC_VER
    // Automated diagnostics must report failure, not wait on a CRT dialog.
    _set_error_mode(_OUT_TO_STDERR);
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
#ifdef _DEBUG
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
#endif
#endif
#ifndef _WIN32
    const auto result = ProtectedPackedCustodyOwner::open({}, "package-a",
        {{{}, {}, CustodyRole::canonical}, {}}, CustodyFileAccess::createNew);
    assert(!result.ok() && result.error == CustodyFileError::unsupportedPlatform);
#else
    const auto before = CustodyOwnedMemory::usedBytes();
    std::fputs("owner: tree guard faults\n", stderr);
    treeGuardFaults();
    assert(CustodyOwnedMemory::usedBytes() == before);
    {
        std::array<CustodyNativeJob, 4> jobs;
        std::array<CustodyPin, 32> pins;
        assert(std::all_of(jobs.begin(), jobs.end(), [](const CustodyNativeJob& job) { return bool(job); }));
        assert(std::all_of(pins.begin(), pins.end(), [](const CustodyPin& pin) { return bool(pin); }));
    }
    std::fputs("owner: publication faults\n", stderr); faults();
    std::fputs("owner: admission\n", stderr); admission();
    std::fputs("owner: confinement\n", stderr); confinement();
    std::fputs("owner: publication\n", stderr); publication();
    std::fputs("owner: bounds/allocation\n", stderr); boundsAndAllocation();
    std::fputs("owner: post-effect allocation\n", stderr); postEffectAllocation();
    {
        Fixture fixture;
        auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        auto owner = std::move(*opened.value);
        const auto epoch = owner->epoch(); assert(epoch != 0);
        assert(owner->appendPosition().value == ProtectedPackedCustodyFormat::appendOffset);
        auto prefix = owner->readCiphertext(0, 128); assert(prefix.ok());
        assert(ProtectedPackedCustodyFormat::prefixMatches(prefix.value->bytes.data(), 128, fixture.context));
        auto head0 = owner->readCiphertext(128, 16384), head1 = owner->readCiphertext(16512, 16384);
        assert(head0.ok() && head1.ok());
        assert(ProtectedPackedCustodyCodec::openHead(fixture.context, 0, head0.value->bytes, 1).ok());
        assert(ProtectedPackedCustodyCodec::openHead(fixture.context, 1, head1.value->bytes, 1).ok());
        head0.value.reset(); head1.value.reset();
        deniedWriter(fixture);
        const PackedRecordAddress address{PackedRecordKind::data, ProtectedPackedCustodyFormat::appendOffset, 0, 2, 3};
        const auto sealed = ProtectedPackedCustodyCodec::seal(fixture.context, address, CustodyBytes{2, 4, 6}); assert(sealed.ok());
        assert(owner->append(address, *sealed.value).ok()); assert(owner->flush().ok());
        auto read = owner->readCiphertext(address.offset, static_cast<std::uint32_t>(sealed.value->size()));
        assert(read.ok() && read.value->bytes == *sealed.value);
        read.value.reset();
        owner->revokeWrites();
        assert(!owner->append(address, *sealed.value).ok());
        assert(owner->readCiphertext(0, 128).ok()); // Revocation does not cancel readers.
        owner.reset(); deniedWriter(fixture); // Retained result still owns the SAME handle.
        assert(!fixture.open(CustodyFileAccess::writeExisting).ok());
        prefix.value.reset();
        auto reopened = fixture.open(CustodyFileAccess::writeExisting); assert(reopened.ok());
        assert((*reopened.value)->epoch() != epoch); // Same file ID is not the old RAM epoch.
        (*reopened.value)->blockWrites();
        assert(!(*reopened.value)->readCiphertext(0, 128).ok());
        assert(!(*reopened.value)->flush().ok());
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
#endif
}
