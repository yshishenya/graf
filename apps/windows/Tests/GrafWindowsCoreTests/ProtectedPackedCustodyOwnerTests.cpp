#include "../../RecApp/Storage/ProtectedPackedCustodyOwner.h"
#include "../../RecApp/Storage/ProtectedPackedCustodyTree.h"
#include "../../RecApp/Storage/ProtectedCustodyPrimitives.h"
#include "../../RecApp/Storage/ProtectedCustodyReader.h"
#include "../../RecApp/Storage/ProtectedCustodyWriter.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>
#include <algorithm>
#include <cstring>
#include <cstdlib>
#ifdef _WIN32
#include <windows.h>
#include <sddl.h>
#include <objbase.h>
#include <psapi.h>
#include <vector>
#include <array>
#include <new>
#include <thread>
#include <type_traits>
#include <chrono>
#include <atomic>
#ifdef _MSC_VER
#include <crtdbg.h>
#endif

static_assert(!std::is_copy_assignable_v<graf::windows::CustodyNativeJob>);
static_assert(!std::is_move_assignable_v<graf::windows::CustodyNativeJob>);

// Reuse the codec-test allocation interception only in this generated-data
// executable: inspect the selected plaintext BEFORE its actual deallocate.
namespace {
void* watchedPlain = nullptr;
std::size_t watchedPlainBytes = 0;
bool watchPlain = false, plainFreed = false;
void* dirtyRaw = nullptr;
const std::uint8_t* dirtyBody = nullptr;
std::size_t dirtyBodyBytes = 0;
bool watchDirtyAllocation = false, dirtyFreed = false;
bool failProxyAfterDestination = false;
std::atomic<std::size_t> failPlainAllocation{0};
bool observeCadence = false;
std::size_t cadenceOwnedMax = 0;
void inspectPlainFree(void* memory) {
    if (memory && memory == dirtyRaw) {
        assert(dirtyBody && dirtyBodyBytes);
        assert(std::all_of(dirtyBody, dirtyBody+dirtyBodyBytes, [](auto byte) { return byte == 0; }));
        dirtyRaw = nullptr; dirtyBody = nullptr; dirtyFreed = true;
    }
    if (memory && memory == watchedPlain) {
        const auto* bytes = static_cast<const std::uint8_t*>(memory);
        assert(std::all_of(bytes, bytes+watchedPlainBytes, [](auto byte) { return byte == 0; }));
        watchedPlain = nullptr; plainFreed = true;
    }
}
}
void* operator new(std::size_t bytes) {
    if (observeCadence) cadenceOwnedMax = std::max(cadenceOwnedMax, graf::windows::CustodyOwnedMemory::usedBytes());
    auto expected = failPlainAllocation.load();
    // MSVC large-vector allocation includes up to64B alignment bookkeeping.
    const bool destination = watchedPlain && bytes >= 262144 && bytes-262144 <= 64;
    if (expected && (bytes == expected || (expected == 262144 && destination)) &&
        failPlainAllocation.compare_exchange_strong(expected, 0)) throw std::bad_alloc();
    if (auto* memory = std::malloc(bytes ? bytes : 1)) {
        if (watchDirtyAllocation && bytes >= 262144 && bytes-262144 <= 64) {
            dirtyRaw = memory; watchDirtyAllocation = false;
        }
        if (failProxyAfterDestination && destination) {
            failProxyAfterDestination = false; failPlainAllocation.store(16);
        }
        return memory;
    }
    throw std::bad_alloc();
}
void operator delete(void* memory) noexcept { inspectPlainFree(memory); std::free(memory); }
void operator delete(void* memory, std::size_t) noexcept { inspectPlainFree(memory); std::free(memory); }

namespace {
enum class Fault { none, write, shortWrite, zeroWrite, flush, read, changedRead, throwingRead, streamEnd, throwingMetadata, invalidSize };
Fault injectedFault = Fault::none;
unsigned writes = 0, reads = 0, flushes = 0, metadataQueries = 0, ordinal = 1;
std::uint64_t cadenceWriteBytes = 0, cadenceReadBytes = 0;
unsigned cadenceData = 0, cadenceNodes = 0;
bool inspectUnwindAdmission = false, failureRetainedJob = false;
bool observeLogicalAppend = false, logicalHeadAttempted = false;
std::atomic<bool>* cancelOnFinalHead = nullptr;
unsigned cancellationHeadReads = 0;
unsigned metadataAtHead = 0;
unsigned lastPreHeadRead = 0, metadataAtMinimum = 0, pressureAtMetadata = 0;
std::size_t minimumPreHeadBytes = 0, pressureBytes = 0;
std::uint8_t* heldPressure = nullptr;
const graf::windows::CustodyBytes* substitutedPeer = nullptr;
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
void inject(Fault value, unsigned at = 1) { injectedFault = value; ordinal = at; writes = reads = flushes = metadataQueries = 0; }
BOOL WINAPI testWrite(HANDLE file, LPCVOID bytes, DWORD count, LPDWORD done, LPOVERLAPPED operation) {
    assert(count <= 262144); ++writes;
    if (observeCadence) cadenceWriteBytes += count; // Requested, not transferred under fault injection.
    if (observeLogicalAppend && operation && operation->OffsetHigh == 0 &&
        (operation->Offset == 128 || operation->Offset == 16512) && count == 16384) {
        logicalHeadAttempted = true; metadataAtHead = metadataQueries;
    }
    if (writes == ordinal) {
        if (injectedFault == Fault::write) { SetLastError(ERROR_WRITE_FAULT); return FALSE; }
        if (injectedFault == Fault::zeroWrite) { *done = 0; return TRUE; }
        if (injectedFault == Fault::shortWrite) return WriteFile(file, bytes, count - 1, done, operation);
    }
    return WriteFile(file, bytes, count, done, operation);
}
BOOL WINAPI testRead(HANDLE file, LPVOID bytes, DWORD count, LPDWORD done, LPOVERLAPPED operation) {
    assert(count <= 262144); ++reads;
    if (observeCadence) cadenceReadBytes += count;
    if (cancelOnFinalHead && logicalHeadAttempted && operation && operation->OffsetHigh == 0 &&
        (operation->Offset == 128 || operation->Offset == 16512) && count == 16384) {
        ++cancellationHeadReads;
        // Files reads back the published cell once; Tree then reads both HEAD cells.
        assert(cancellationHeadReads <= 3); // No new transition after the in-flight commit.
        if (cancellationHeadReads == 3) cancelOnFinalHead->store(true);
    }
    if (reads == ordinal) {
        if (injectedFault == Fault::read) { SetLastError(ERROR_READ_FAULT); return FALSE; }
        if (injectedFault == Fault::throwingRead) throw std::bad_alloc();
    }
    const auto result = ReadFile(file, bytes, count, done, operation);
    if (result && *done && reads == ordinal && injectedFault == Fault::changedRead) static_cast<std::uint8_t*>(bytes)[0] ^= 1;
    if (result && substitutedPeer && logicalHeadAttempted && operation &&
        operation->OffsetHigh == 0 && operation->Offset == 16512 && count == 16384 && *done == count)
        std::copy(substitutedPeer->begin(), substitutedPeer->end(), static_cast<std::uint8_t*>(bytes));
    return result;
}
BOOL WINAPI testFlush(HANDLE file) {
    ++flushes;
    if (flushes == ordinal && injectedFault == Fault::flush) { SetLastError(ERROR_WRITE_FAULT); return FALSE; }
    return FlushFileBuffers(file);
}
BOOL WINAPI testNextStream(HANDLE search, LPVOID data) {
    if (injectedFault == Fault::streamEnd) { SetLastError(ERROR_ACCESS_DENIED); return FALSE; }
    return FindNextStreamW(search, data);
}
HANDLE WINAPI testFirstStream(LPCWSTR name, STREAM_INFO_LEVELS level, LPVOID data, DWORD flags) {
    ++metadataQueries;
    if (observeLogicalAppend && flushes == 1 && !logicalHeadAttempted) {
        const auto used = graf::windows::CustodyOwnedMemory::usedBytes();
        if (reads != lastPreHeadRead || used < minimumPreHeadBytes) {
            lastPreHeadRead = reads; minimumPreHeadBytes = used; metadataAtMinimum = metadataQueries;
        }
    }
    if (pressureAtMetadata && metadataQueries == pressureAtMetadata) {
        pressureBytes = graf::windows::CustodyOwnedMemory::limit-graf::windows::CustodyOwnedMemory::usedBytes();
        heldPressure = graf::windows::CustodyAllocator<std::uint8_t>{}.allocate(pressureBytes);
    }
    if (injectedFault == Fault::throwingMetadata && metadataQueries == ordinal) {
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
    if (injectedFault == Fault::invalidSize) { size->QuadPart = 32895; return TRUE; }
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
namespace graf::windows {
namespace {
bool replaceNodeSibling = false, siblingReplaced = false, siblingDecoded = false;
std::uint64_t siblingGeneration = 3, siblingLength = 2ULL*262144;
class TestPackedCodec final {
public:
    static auto seal(const PackedCustodyContext& context, const PackedRecordAddress& address, const CustodyBytes& body) {
        if (observeCadence) {
            if (address.kind == PackedRecordKind::data) ++cadenceData;
            else if (address.kind == PackedRecordKind::nodeL0 || address.kind == PackedRecordKind::nodeL1 ||
                address.kind == PackedRecordKind::nodeL2) ++cadenceNodes; // HEAD is not an appended NODE.
        }
        if (dirtyRaw && !dirtyBody && address.kind == PackedRecordKind::data) {
            const auto raw = reinterpret_cast<std::uintptr_t>(dirtyRaw);
            const auto data = reinterpret_cast<std::uintptr_t>(body.data());
            assert(data >= raw && data-raw <= 64);
            dirtyBody = body.data(); dirtyBodyBytes = body.size();
        }
        if (replaceNodeSibling && address.kind == PackedRecordKind::nodeL0 && address.version == siblingGeneration) {
            assert(body.size() == 4096 && !siblingReplaced);
            assert(body[0] == static_cast<std::uint8_t>(PackedRecordKind::data));
            CustodyBytes altered(body);
            PackedReference zero; zero.kind = PackedRecordKind::zero;
            const auto wire = ProtectedPackedCustodyFormat::encodeReference(zero); assert(wire);
            std::copy(wire->begin(), wire->end(), altered.begin());
            siblingReplaced = true;
            // Real sealing recomputes checksum, DPAPI envelope and the worker's
            // expected SHA. Only the bounded BASE structural diff can refuse it.
            return ProtectedPackedCustodyCodec::seal(context, address, altered);
        }
        return ProtectedPackedCustodyCodec::seal(context, address, body);
    }
    static auto openReferenced(const PackedCustodyContext& context, std::uint64_t selector,
        const PackedReference& reference, const CustodyBytes& bytes) {
        auto result = ProtectedPackedCustodyCodec::openReferenced(context, selector, reference, bytes);
        if (watchPlain && !plainFreed && !watchedPlain && result.ok() && reference.kind == PackedRecordKind::data) {
            watchedPlain = result.value->body.data(); watchedPlainBytes = result.value->body.size();
        }
        if (replaceNodeSibling && siblingReplaced && result.ok() &&
            reference.kind == PackedRecordKind::nodeL0 && reference.version == siblingGeneration) {
            const PackedRootDescriptor candidate{siblingGeneration, siblingLength,
                reference.offset+reference.envelopeBytes, static_cast<std::uint32_t>((siblingLength+262143)/262144), {}};
            const auto child = ProtectedPackedCustodyFormat::decodeChild(result.value->body.data(),
                64, candidate, reference, selector, 0);
            assert(child && child->kind == PackedRecordKind::zero);
            siblingDecoded = true; // Independent read passed SHA, DPAPI and child semantics.
        }
        return result;
    }
    static auto openHead(const PackedCustodyContext& context, std::uint32_t slot, const CustodyBytes& bytes) {
        return ProtectedPackedCustodyCodec::openHead(context, slot, bytes);
    }
};
}
}
// Same real worker; only its in-memory codec call is faulted in this test TU.
#define ProtectedPackedCustodyCodec TestPackedCodec
#include "../../RecApp/Storage/ProtectedPackedCustodyTree.cpp"
#undef ProtectedPackedCustodyCodec
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
void resizePlainWipe() {
    for (unsigned failure = 0; failure <
#ifdef _DEBUG
        3
#else
        2
#endif
        ; ++failure) {
        Fixture fixture;
        auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        auto birth = ProtectedPackedCustodyTree::verify(*opened.value); assert(birth.ok());
        const auto first = (*birth.value)->appendBlock(CustodyBytes{0x31, 0x53, 0x75}); assert(first.snapshot);
        watchPlain = true; plainFreed = false; watchedPlain = nullptr;
        failProxyAfterDestination = failure == 2;
        failPlainAllocation.store(failure == 1 ? 262144 : 0);
        const auto result = first.snapshot->setSize(262144);
        watchPlain = false;
        std::fprintf(stderr, "resize-wipe case=%u freed=%d watched=%d pending=%zu state=%u error=%u\n",
            failure, plainFreed ? 1 : 0, watchedPlain ? 1 : 0, failPlainAllocation.load(),
            static_cast<unsigned>(result.state), static_cast<unsigned>(result.error));
        assert(plainFreed && !watchedPlain && failPlainAllocation.load() == 0);
        if (failure) {
            assert(result.error == CustodyFileError::allocationFailed && !result.snapshot && result.lease);
            assert(result.state == CustodyCommitState::notCommitted);
            assert(first.snapshot->setSize(262144).error == result.error);
        } else {
            assert(result.snapshot && result.state == CustodyCommitState::committed);
            const auto read = result.snapshot->readBlock(0); assert(read.ok());
            assert(read.value->bytes.size() == 262144 && read.value->bytes[0] == 0x31 &&
                read.value->bytes[1] == 0x53 && read.value->bytes[2] == 0x75);
            assert(std::all_of(read.value->bytes.begin()+3, read.value->bytes.end(), [](auto byte) { return byte == 0; }));
        }
    }
}
void packedWriterCadence(unsigned targetMiB) {
    constexpr std::uint64_t block = 262144, frameBytes = 480*sizeof(float);
    const auto before = CustodyOwnedMemory::usedBytes();
    const auto memory = [] {
        PROCESS_MEMORY_COUNTERS_EX value{};
        assert(K32GetProcessMemoryInfo(GetCurrentProcess(), reinterpret_cast<PROCESS_MEMORY_COUNTERS*>(&value), sizeof(value)));
        return value;
    };
    const auto nativeBefore = memory();
    const auto ms = [](auto elapsed) { return std::chrono::duration<double, std::milli>(elapsed).count(); };
    {
        Fixture fixture;
        auto owner = fixture.open(CustodyFileAccess::createNew); assert(owner.ok());
        auto initial = ProtectedPackedCustodyTree::verify(*owner.value); assert(initial.ok());
        auto writer = ProtectedCustodyWriter::open(*initial.value, std::make_shared<std::atomic<bool>>(false)); assert(writer.ok());
        CustodyBytes input(frameBytes);
        for (std::size_t i = 0; i < 480; ++i) {
            const auto value = static_cast<float>(static_cast<int>(i%29)-14)/32.0F;
            std::memcpy(input.data()+i*sizeof(float), &value, sizeof(value));
        }
        const auto target = targetMiB*1024ULL*1024;
        const auto frameCount = (target+frameBytes-1)/frameBytes;
        const auto total = frameCount*frameBytes; // No padding/truncation to nominal MiB.
        std::shared_ptr<const ProtectedPackedCustodyTree> pinned;
        auto extent = (*owner.value)->appendPosition(); assert(extent.ok());
        auto lastExtent = *extent.value;
        inject(Fault::none); cadenceWriteBytes = cadenceReadBytes = 0; cadenceData = cadenceNodes = 0;
        cadenceOwnedMax = CustodyOwnedMemory::usedBytes(); observeCadence = true;
        std::array<unsigned, 5> previous{};
        std::array<std::uint64_t, 2> previousBytes{};
        std::array<unsigned, 5> last{};
        std::array<std::uint64_t, 2> lastBytes{};
        double lastCheckpointMs = 0, maxFrameMs = 0;
        std::size_t sampledPrivateMax = nativeBefore.PrivateUsage;
        const auto started = std::chrono::steady_clock::now();
        std::uint64_t milestone = 1024*1024;
        std::fprintf(stderr, "packed-cadence synthetic_only=1 paced=0 target_mib=%u frames=%llu actual_bytes=%llu modelled_ms=%llu\n",
            targetMiB, static_cast<unsigned long long>(frameCount), static_cast<unsigned long long>(total), static_cast<unsigned long long>(frameCount*10));
        for (std::uint64_t frame = 0; frame < frameCount; ++frame) {
            const auto at = frame*frameBytes;
            const auto callStarted = std::chrono::steady_clock::now();
            const auto written = (*writer.value)->writeAt(at, input.data(), input.size());
            const auto callMs = ms(std::chrono::steady_clock::now()-callStarted);
            assert(written.ok() && *written.value == frameBytes);
            maxFrameMs = std::max(maxFrameMs, callMs);
            const auto accepted = at+frameBytes;
            assert((*writer.value)->size() == accepted && (*writer.value)->generation() == 1+accepted/block);
            if (accepted/block != at/block) {
                const std::array<unsigned, 5> now{writes, reads, flushes, cadenceData, cadenceNodes};
                for (std::size_t i = 0; i < last.size(); ++i) last[i] = now[i]-previous[i];
                lastBytes = {cadenceWriteBytes-previousBytes[0], cadenceReadBytes-previousBytes[1]};
                assert(last[3] == 1 && last[4] <= 3 && last[2] == 2);
                extent = (*owner.value)->appendPosition(); assert(extent.ok());
                assert(*extent.value > lastExtent && *extent.value-lastExtent <= 290816);
                lastExtent = *extent.value; lastCheckpointMs = callMs;
                sampledPrivateMax = std::max(sampledPrivateMax, memory().PrivateUsage);
                if (!pinned) {
                    auto proof = ProtectedPackedCustodyTree::verify(*owner.value); assert(proof.ok());
                    pinned = *proof.value; // Diagnostic cold scan is excluded from the next live IO window.
                    assert(pinned->generation() == 2 && pinned->logicalBytes() == block);
                }
                previous = {writes, reads, flushes, cadenceData, cadenceNodes};
                previousBytes = {cadenceWriteBytes, cadenceReadBytes};
            }
            if (accepted >= milestone) {
                DWORD handles = 0; assert(GetProcessHandleCount(GetCurrentProcess(), &handles));
                std::fprintf(stderr, "packed-cadence mib=%llu accepted_bytes=%llu generation=%llu loop_wall_ms=%.3f last_checkpoint_call_ms=%.3f "
                    "last_io=%u/%u/%u last_data_nodes=%u/%u last_requested_bytes=%llu/%llu physical_bytes=%llu owned_new_sample_max=%zu sampled_private_max=%zu handles=%lu\n",
                    static_cast<unsigned long long>(milestone/(1024*1024)), static_cast<unsigned long long>(accepted),
                    static_cast<unsigned long long>((*writer.value)->generation()), ms(std::chrono::steady_clock::now()-started), lastCheckpointMs,
                    last[0], last[1], last[2], last[3], last[4], static_cast<unsigned long long>(lastBytes[0]), static_cast<unsigned long long>(lastBytes[1]),
                    static_cast<unsigned long long>(lastExtent), cadenceOwnedMax, sampledPrivateMax, handles);
                std::fflush(stderr); milestone *= 2;
            }
        }
        const auto tailStarted = std::chrono::steady_clock::now();
        const auto tail = (*writer.value)->checkpoint();
        const auto tailMs = ms(std::chrono::steady_clock::now()-tailStarted);
        const auto generation = 1+total/block+(total%block != 0);
        assert(tail.state == CustodyCommitState::committed && (*writer.value)->generation() == generation && (*writer.value)->size() == total);
        auto old = pinned->readBlock(0); assert(old.ok() && old.value->bytes.size() == block);
        for (std::size_t i = 0; i < old.value->bytes.size(); ++i) assert(old.value->bytes[i] == input[i%frameBytes]);
        old.value.reset(); pinned.reset(); initial.value.reset();
        const auto releaseStarted = std::chrono::steady_clock::now();
        writer.value.reset(); owner.value.reset();
        const auto releaseMs = ms(std::chrono::steady_clock::now()-releaseStarted);
        observeCadence = false; // Cold cost/native samples are a separate scope.
        const auto coldStarted = std::chrono::steady_clock::now();
        auto reopened = fixture.open(CustodyFileAccess::readExisting); assert(reopened.ok());
        auto cold = ProtectedPackedCustodyTree::verify(*reopened.value); assert(cold.ok());
        const auto coldMs = ms(std::chrono::steady_clock::now()-coldStarted);
        assert((*cold.value)->generation() == generation && (*cold.value)->logicalBytes() == total);
        for (std::uint64_t position = 0; position*block < total; ++position) {
            auto read = (*cold.value)->readBlock(position); assert(read.ok());
            assert(read.value->bytes.size() == std::min(block, total-position*block));
            for (std::size_t i = 0; i < read.value->bytes.size(); ++i) assert(read.value->bytes[i] == input[(position*block+i)%frameBytes]);
        }
        std::fprintf(stderr, "packed-cadence tail_scope=storage_only_no_dispatcher_or_encoder tail_ms=%.3f actual_remainder=%llu generation=%llu "
            "release_ms=%.3f cold_full_verify_ms=%.3f max_frame_call_ms=%.3f owned_new_sample_max=%zu sampled_private_max=%zu\n",
            tailMs, static_cast<unsigned long long>(total%block), static_cast<unsigned long long>(generation), releaseMs, coldMs, maxFrameMs,
            cadenceOwnedMax, sampledPrivateMax);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
    std::fprintf(stderr, "packed-cadence exact_bytes_verified=1 owned_after_release=%zu native_private_after=%zu\n", before, memory().PrivateUsage);
    inject(Fault::none);
}
enum class CommitCase { append, tail, interior, shrink, grow, empty };
void packedWriterCancellation() {
    for (const bool sparse : {false, true}) {
        Fixture fixture;
        auto owner = fixture.open(CustodyFileAccess::createNew); assert(owner.ok());
        auto initial = ProtectedPackedCustodyTree::verify(*owner.value); assert(initial.ok());
        auto cancellation = std::make_shared<std::atomic<bool>>(false);
        auto writer = ProtectedCustodyWriter::open(*initial.value, cancellation); assert(writer.ok());
        const std::uint8_t byte = 0x53;
        assert((*writer.value)->writeAt(sparse ? 3*262144ULL+1 : 0, &byte, 1).ok());
        inject(Fault::none); observeLogicalAppend = true; logicalHeadAttempted = false;
        cancellationHeadReads = 0; cancelOnFinalHead = cancellation.get();
        const auto result = (*writer.value)->checkpoint();
        cancelOnFinalHead = nullptr; observeLogicalAppend = false;
        assert(cancellation->load() && cancellationHeadReads == 3 && (*writer.value)->generation() == 2);
        assert(result.state == (sparse ? CustodyCommitState::notCommitted : CustodyCommitState::committed));
        const auto stoppedWrites = writes;
        assert(!(*writer.value)->writeAt(0, &byte, 1).ok() && writes == stoppedWrites);
        std::fprintf(stderr, "packed-writer cancellation sparse=%d state=%u generation=%llu head_reads=%u\n",
            sparse, static_cast<unsigned>(result.state), static_cast<unsigned long long>((*writer.value)->generation()), cancellationHeadReads);
        inject(Fault::none);
    }
}
void packedWriterAdmission() {
    for (unsigned cause = 0; cause < 3; ++cause) for (unsigned action = 0; action < 4; ++action) {
        Fixture fixture;
        auto owner = fixture.open(CustodyFileAccess::createNew); assert(owner.ok());
        auto initial = ProtectedPackedCustodyTree::verify(*owner.value); assert(initial.ok());
        auto seed = (*initial.value)->appendBlock(CustodyBytes{0x31}); assert(seed.snapshot);
        auto writer = ProtectedCustodyWriter::open(seed.snapshot, std::make_shared<std::atomic<bool>>(false)); assert(writer.ok());
        const std::uint8_t byte = 0x53;
        assert((*writer.value)->writeAt(0, &byte, 1).ok()); // Populated dirty hit.
        if (cause == 0) (*owner.value)->blockWrites();
        else if (cause == 1) (*owner.value)->revokeWrites();
        else {
            inject(Fault::read);
            const auto fault = (*owner.value)->readCiphertext(0, 128);
            assert(!fault.ok() && fault.nativeError == ERROR_READ_FAULT);
            inject(Fault::none);
        }
        const auto expected = cause == 0 ? CustodyFileError::recoveryRequired :
            cause == 1 ? CustodyFileError::writerFailed : CustodyFileError::ioFailed;
        const auto native = cause == 2 ? ERROR_READ_FAULT : 0U;
        const auto denied = action == 0 ? (*writer.value)->writeAt(0, &byte, 1) :
            action == 1 ? (*writer.value)->writeAt(0, nullptr, 0) :
            action == 2 ? (*writer.value)->setSize((*writer.value)->size()) :
            (*writer.value)->writeAt(UINT64_MAX, nullptr, 1);
        assert(!denied.ok() && denied.error == expected && denied.nativeError == native);
        const auto stoppedWrites = writes;
        const auto again = (*writer.value)->checkpoint();
        assert(again.error == CustodyFileError::writerFailed && again.nativeError == native && writes == stoppedWrites);
        if (cause == 1) {
            auto read = seed.snapshot->readBlock(0); assert(read.ok() && read.value->bytes == CustodyBytes{0x31});
        }
        inject(Fault::none);
    }
}
void packedWriterResources() {
    for (unsigned refusal = 0; refusal < 4; ++refusal) {
        Fixture fixture; auto owner = fixture.open(CustodyFileAccess::createNew); assert(owner.ok());
        auto tree = ProtectedPackedCustodyTree::verify(*owner.value); assert(tree.ok());
        const auto cancellation = std::make_shared<std::atomic<bool>>(false);
        const auto before = CustodyOwnedMemory::usedBytes();
        inject(Fault::none);
        if (refusal == 0) {
            const auto bytes = CustodyOwnedMemory::limit-before;
            auto* pressure = CustodyAllocator<std::uint8_t>{}.allocate(bytes);
            const auto denied = ProtectedCustodyWriter::open(*tree.value, cancellation);
            assert(!denied.ok() && denied.error == CustodyFileError::allocationFailed);
            CustodyAllocator<std::uint8_t>{}.deallocate(pressure, bytes);
        } else if (refusal == 1) {
            failPlainAllocation.store(sizeof(ProtectedCustodyWriter));
            const auto denied = ProtectedCustodyWriter::open(*tree.value, cancellation);
            assert(!denied.ok() && denied.error == CustodyFileError::allocationFailed && failPlainAllocation.load() == 0);
        } else if (refusal == 2) {
            std::array<CustodyPin, 32> held;
            assert(std::any_of(held.begin(), held.end(), [](const auto& pin) { return !pin; }));
            const auto denied = ProtectedCustodyWriter::open(*tree.value, cancellation);
            assert(!denied.ok() && denied.error == CustodyFileError::allocationFailed);
        } else {
            std::array<CustodyNativeJob, 4> held;
            assert(std::all_of(held.begin(), held.end(), [](const auto& job) { return bool(job); }));
            const auto denied = ProtectedCustodyWriter::open(*tree.value, cancellation);
            assert(!denied.ok() && denied.error == CustodyFileError::allocationFailed);
        }
        assert(writes == 0 && reads == 0 && flushes == 0 && CustodyOwnedMemory::usedBytes() == before);
        auto retry = ProtectedCustodyWriter::open(*tree.value, cancellation); assert(retry.ok());
    }
    {
        Fixture fixture; auto owner = fixture.open(CustodyFileAccess::createNew); assert(owner.ok());
        auto tree = ProtectedPackedCustodyTree::verify(*owner.value); assert(tree.ok());
        auto writer = ProtectedCustodyWriter::open(*tree.value, std::make_shared<std::atomic<bool>>(false)); assert(writer.ok());
        std::array<CustodyDirtySlot, 4> held;
        assert(std::all_of(held.begin(), held.end(), [](const auto& slot) { return bool(slot); }));
        inject(Fault::none); const std::uint8_t byte = 0x53;
        const auto denied = (*writer.value)->writeAt(0, &byte, 1);
        assert(!denied.ok() && denied.error == CustodyFileError::allocationFailed && writes == 0 && reads == 0);
        inject(Fault::none);
    }
    for (const auto fault : {Fault::none, Fault::flush}) {
        Fixture fixture; auto owner = fixture.open(CustodyFileAccess::createNew); assert(owner.ok());
        auto tree = ProtectedPackedCustodyTree::verify(*owner.value); assert(tree.ok());
        auto writer = ProtectedCustodyWriter::open(*tree.value, std::make_shared<std::atomic<bool>>(false)); assert(writer.ok());
        dirtyRaw = nullptr; dirtyBody = nullptr; dirtyBodyBytes = 0; dirtyFreed = false; watchDirtyAllocation = true;
        const std::uint8_t input[]{0x31, 0x53, 0x75};
        assert((*writer.value)->writeAt(0, input, sizeof(input)).ok());
        assert(dirtyRaw && !watchDirtyAllocation);
        inject(fault);
        const auto result = (*writer.value)->checkpoint();
        assert((result.state == CustodyCommitState::committed) == (fault == Fault::none));
        if (fault == Fault::flush) assert(!dirtyFreed && dirtyBody);
        writer.value.reset(); // Failed dirty storage is wiped before its actual raw allocation is freed.
        assert(dirtyFreed && !dirtyRaw && !dirtyBody);
        inject(Fault::none);
    }
}
void packedWriterCuts() {
    const auto prepare = [](Fixture& fixture, std::shared_ptr<ProtectedPackedCustodyOwner>& owner) {
        auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok()); owner = *opened.value;
        auto tree = ProtectedPackedCustodyTree::verify(owner); assert(tree.ok());
        auto seed = (*tree.value)->appendBlock(CustodyBytes{0x31, 0x53, 0x75}); assert(seed.snapshot);
        auto writer = ProtectedCustodyWriter::open(seed.snapshot, std::make_shared<std::atomic<bool>>(false)); assert(writer.ok());
        const std::uint8_t byte = 0x37;
        assert((*writer.value)->writeAt(1, &byte, 1).ok());
        return std::move(*writer.value);
    };
    std::array<unsigned, 3> counts{};
    {
        Fixture fixture; std::shared_ptr<ProtectedPackedCustodyOwner> owner;
        auto writer = prepare(fixture, owner);
        inject(Fault::none); const auto result = writer->checkpoint();
        assert(result.state == CustodyCommitState::committed && writer->generation() == 3);
        counts = {writes, reads, flushes};
    }
    for (const auto fault : {Fault::write, Fault::shortWrite, Fault::zeroWrite, Fault::flush,
        Fault::read, Fault::changedRead, Fault::throwingRead}) {
        const auto count = fault == Fault::flush ? counts[2] :
            fault == Fault::read || fault == Fault::changedRead || fault == Fault::throwingRead ? counts[1] : counts[0];
        for (unsigned at = 1; at <= count; ++at) {
            Fixture fixture; std::shared_ptr<ProtectedPackedCustodyOwner> owner;
            auto writer = prepare(fixture, owner);
            inject(fault, at); observeLogicalAppend = true; logicalHeadAttempted = false;
            const auto result = writer->checkpoint(); observeLogicalAppend = false;
            assert(result.state == (logicalHeadAttempted ? CustodyCommitState::ambiguous : CustodyCommitState::notCommitted));
            assert(result.error != CustodyFileError::none && result.baseGeneration == 2 && result.targetGeneration <= 3);
            if (fault == Fault::read) assert(result.nativeError == ERROR_READ_FAULT);
            if (fault == Fault::write || fault == Fault::shortWrite || fault == Fault::zeroWrite || fault == Fault::flush)
                assert(result.nativeError == ERROR_WRITE_FAULT);
            const std::array<unsigned, 3> stopped{writes, reads, flushes};
            const std::uint8_t byte = 0x37;
            assert(!writer->writeAt(0, &byte, 1).ok());
            const auto again = writer->checkpoint();
            assert(again.state == result.state && again.error == CustodyFileError::writerFailed && again.nativeError == result.nativeError);
            assert((stopped == std::array<unsigned, 3>{writes, reads, flushes}));
            owner.reset(); deniedWriter(fixture); // Actual failed base remains owned by Writer.
            inject(Fault::none);
        }
    }
    std::fprintf(stderr, "packed-writer cuts writes=%u reads=%u flushes=%u\n", counts[0], counts[1], counts[2]);
}
void logicalAppendFaults(unsigned payloadSize = 262144, CommitCase mode = CommitCase::append) {
    const bool resize = mode == CommitCase::shrink || mode == CommitCase::grow || mode == CommitCase::empty;
    const auto expectedLength = [mode, payloadSize](const auto& tree) {
        if (mode == CommitCase::shrink) return std::uint64_t{262145};
        if (mode == CommitCase::grow) return ProtectedPackedCustodyFormat::logicalLimit;
        if (mode == CommitCase::empty) return std::uint64_t{0};
        return mode == CommitCase::append ? tree->logicalBytes()+payloadSize :
            std::max<std::uint64_t>(tree->logicalBytes(), 262144ULL+payloadSize);
    };
    const auto commit = [mode, resize, expectedLength](const std::shared_ptr<const ProtectedPackedCustodyTree>& tree, const CustodyBytes& payload) {
        if (resize) return tree->setSize(expectedLength(tree));
        return mode == CommitCase::append ? tree->appendBlock(payload) : tree->replaceBlock(1, payload);
    };
    const auto prepare = [mode](const std::shared_ptr<ProtectedPackedCustodyOwner>& owner) {
        auto verified = ProtectedPackedCustodyTree::verify(owner); assert(verified.ok());
        auto tree = std::move(*verified.value);
        if (mode != CommitCase::append) {
            for (unsigned i = 0; i < (mode == CommitCase::interior ? 3U : 1U); ++i) {
                const auto full = tree->appendBlock(CustodyBytes(262144, static_cast<std::uint8_t>(0x31+i)));
                assert(full.snapshot); tree = full.snapshot;
            }
            const auto shortBase = tree->appendBlock(CustodyBytes{1, 3, 5}); assert(shortBase.snapshot);
            tree = shortBase.snapshot;
        }
        return tree;
    };
    if (mode != CommitCase::empty) {
        Fixture fixture;
        auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        const CustodyBytes payload(payloadSize, 0x37);
        auto base = prepare(*opened.value);
        if (mode == CommitCase::append) {
            const auto first = base->appendBlock(CustodyBytes(262144, 0x37)); assert(first.snapshot);
            base = first.snapshot;
        }
        inject(Fault::none); observeLogicalAppend = true; logicalHeadAttempted = false;
        siblingGeneration = base->generation()+1;
        siblingLength = expectedLength(base);
        replaceNodeSibling = true; siblingReplaced = siblingDecoded = false;
        const auto refused = commit(base, payload);
        replaceNodeSibling = false; observeLogicalAppend = false;
        assert(siblingReplaced && siblingDecoded && !logicalHeadAttempted && flushes == 1);
        assert(refused.state == CustodyCommitState::notCommitted && !refused.snapshot && refused.lease);
        assert(refused.error == CustodyFileError::invalidContent);
        const std::array<unsigned, 3> stopped{writes, reads, flushes};
        const auto again = commit(base, payload);
        assert(again.error == refused.error && (stopped == std::array<unsigned, 3>{writes, reads, flushes}));
        deniedWriter(fixture);
    }
    std::array<unsigned, 3> completedCounts{};
    unsigned postHeadMetadata = 0;
    unsigned prospectiveProofMetadata = 0;
    unsigned validatedReads = 0;
    std::size_t prospectiveProofBytes = 0;
    {
        Fixture fixture;
        auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        auto tree = prepare(*opened.value);
        const CustodyBytes payload(payloadSize, 0x37);
        inject(Fault::none); observeLogicalAppend = true; logicalHeadAttempted = false;
        lastPreHeadRead = metadataAtMinimum = 0; minimumPreHeadBytes = CustodyOwnedMemory::limit;
        const auto result = commit(tree, payload);
        observeLogicalAppend = false;
        assert(result.state == CustodyCommitState::committed && result.snapshot && logicalHeadAttempted);
        assert(result.snapshot->logicalBytes() == expectedLength(tree));
        completedCounts = {writes, reads, flushes}; postHeadMetadata = metadataAtHead+1;
        prospectiveProofMetadata = metadataAtMinimum;
        validatedReads = lastPreHeadRead; prospectiveProofBytes = minimumPreHeadBytes;
        assert(flushes == 2); // Record durability, then HEAD durability.
        if (mode != CommitCase::empty) {
            const auto read = result.snapshot->readBlock(mode == CommitCase::append ? 0 : 1);
            assert(read.ok());
            if (!resize) assert(read.value->bytes == payload);
            else if (mode == CommitCase::shrink) assert(read.value->bytes == CustodyBytes({1}));
            else {
                assert(read.value->bytes.size() == 262144 && read.value->bytes[0] == 1 &&
                    read.value->bytes[1] == 3 && read.value->bytes[2] == 5);
                assert(std::all_of(read.value->bytes.begin()+3, read.value->bytes.end(), [](auto byte) { return byte == 0; }));
            }
        }
    }
    for (const auto selected : {Fault::write, Fault::shortWrite, Fault::zeroWrite, Fault::flush,
        Fault::read, Fault::changedRead, Fault::throwingRead, Fault::throwingMetadata}) {
        const auto limit = selected == Fault::flush ? completedCounts[2] :
            (selected == Fault::throwingMetadata ? 2U :
            (selected == Fault::read || selected == Fault::changedRead || selected == Fault::throwingRead ?
                completedCounts[1] : completedCounts[0]));
        for (unsigned at = 1; at <= limit; ++at) {
            Fixture fixture;
            auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
            auto owner = std::move(*opened.value);
            auto tree = prepare(owner);
            const CustodyBytes payload(payloadSize, 0x37);
            inject(selected, selected == Fault::throwingMetadata && at == 2 ? postHeadMetadata : at);
            observeLogicalAppend = true; logicalHeadAttempted = false;
            inspectUnwindAdmission = selected == Fault::throwingMetadata; failureRetainedJob = false;
            const auto result = commit(tree, payload);
            observeLogicalAppend = false; inspectUnwindAdmission = false;
            assert(!result.snapshot && result.error != CustodyFileError::none && result.lease);
            assert(result.state == (logicalHeadAttempted ? CustodyCommitState::ambiguous : CustodyCommitState::notCommitted));
            if (selected == Fault::throwingMetadata) assert(failureRetainedJob);
            if (selected == Fault::throwingMetadata || selected == Fault::throwingRead)
                assert(result.error == CustodyFileError::allocationFailed);
            if (selected == Fault::read) assert(result.nativeError == ERROR_READ_FAULT);
            if (selected == Fault::write || selected == Fault::zeroWrite || selected == Fault::shortWrite || selected == Fault::flush)
                assert(result.nativeError == ERROR_WRITE_FAULT);
            const std::array<unsigned, 3> stopped{writes, reads, flushes};
            const auto again = commit(tree, payload);
            assert(!again.snapshot && again.error == result.error && again.nativeError == result.nativeError);
            assert((stopped == std::array<unsigned, 3>{writes, reads, flushes}));
            // Bad input and the other mode cannot conceal a latched storage fault.
            const auto invalid = mode != CommitCase::append ? tree->appendBlock(CustodyBytes{}) :
                tree->replaceBlock(std::numeric_limits<std::uint64_t>::max(), CustodyBytes{});
            assert(invalid.error == result.error && invalid.nativeError == result.nativeError);
            assert((stopped == std::array<unsigned, 3>{writes, reads, flushes}));
            assert(std::filesystem::exists(fixture.content()));
            owner.reset(); tree.reset(); deniedWriter(fixture); // Result retains custody even after failure.
            inject(Fault::none);
        }
    }
    {
        Fixture fixture;
        auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        auto tree = prepare(*opened.value);
        const CustodyBytes payload(payloadSize, 0x37);
        inject(Fault::none); observeLogicalAppend = true; logicalHeadAttempted = false;
        pressureAtMetadata = prospectiveProofMetadata;
        const auto refused = commit(tree, payload);
        observeLogicalAppend = false; pressureAtMetadata = 0;
        assert(heldPressure && !logicalHeadAttempted && flushes == 1);
        assert(reads == validatedReads && CustodyOwnedMemory::limit-pressureBytes == prospectiveProofBytes);
        assert(refused.error == CustodyFileError::allocationFailed && !refused.snapshot && refused.lease);
        assert(refused.state == CustodyCommitState::notCommitted);
        CustodyAllocator<std::uint8_t>{}.deallocate(heldPressure, pressureBytes); heldPressure = nullptr;
        const std::array<unsigned, 3> stopped{writes, reads, flushes};
        const auto again = commit(tree, payload);
        assert(again.error == refused.error && (stopped == std::array<unsigned, 3>{writes, reads, flushes}));
        deniedWriter(fixture);
    }
    if (mode == CommitCase::append && payloadSize == 262144) {
        Fixture fixture;
        auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        auto verified = ProtectedPackedCustodyTree::verify(*opened.value); assert(verified.ok());
        const CustodyBytes payload(262144, 0x37);
        const auto base = (*verified.value)->appendBlock(payload); assert(base.snapshot);
        CustodyBytes body(128, 0);
        body[0] = 2; body[16] = 128; body[17] = 128;
        body[26] = 4; body[32] = 64; body[36] = 3; // Valid empty g2, not corrupted framing.
        const auto alternate = ProtectedPackedCustodyCodec::seal(fixture.context,
            {PackedRecordKind::head, 16512, 1, 2, 128}, body);
        assert(alternate.ok() && ProtectedPackedCustodyCodec::openHead(fixture.context, 1, *alternate.value).ok());
        substitutedPeer = &*alternate.value;
        inject(Fault::none); observeLogicalAppend = true; logicalHeadAttempted = false;
        const auto refused = base.snapshot->appendBlock(payload);
        substitutedPeer = nullptr; observeLogicalAppend = false;
        assert(logicalHeadAttempted && refused.state == CustodyCommitState::ambiguous);
        assert(refused.error == CustodyFileError::invalidContent && !refused.snapshot && refused.lease);
        const std::array<unsigned, 3> stopped{writes, reads, flushes};
        const auto again = base.snapshot->appendBlock(payload);
        assert(again.error == refused.error && (stopped == std::array<unsigned, 3>{writes, reads, flushes}));
        deniedWriter(fixture);
    }
    {
        Fixture fixture;
        auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        auto tree = prepare(*opened.value);
        const CustodyBytes payload(payloadSize, 0x37);
        CustodyAllocator<std::uint8_t> allocator;
        const auto count = CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes();
        auto* pressure = allocator.allocate(count); // Synthetic charged bytes, never read.
        inject(Fault::none);
        const auto refused = commit(tree, payload);
        assert(!refused.snapshot && refused.error == CustodyFileError::allocationFailed);
        assert(refused.state == CustodyCommitState::notCommitted && writes == 0 && reads == 0 && flushes == 0);
        allocator.deallocate(pressure, count);
        const auto repeated = commit(tree, payload);
        assert(repeated.error == refused.error && writes == 0 && reads == 0 && flushes == 0);
        deniedWriter(fixture);
    }
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
void assertReaderFailed(IStream* stream, HRESULT expected) {
    std::uint8_t byte = 0xa5;
    ULONG got = 9;
    assert(stream->Read(&byte, 1, &got) == expected && got == 0 && byte == 0xa5);
    got = 9;
    assert(stream->Read(nullptr, 0, &got) == expected && got == 0); // Zero request is not a fault bypass.
    LARGE_INTEGER offset{};
    ULARGE_INTEGER position{}; position.QuadPart = 9;
    assert(stream->Seek(offset, STREAM_SEEK_SET, &position) == expected && position.QuadPart == 0);
    STATSTG stat{}; stat.cbSize.QuadPart = 9;
    assert(stream->Stat(&stat, STATFLAG_NONAME) == expected && !stat.pwcsName && stat.cbSize.QuadPart == 0);
    IStream* rejected = stream;
    assert(stream->Clone(&rejected) == expected && !rejected);
    assert(stream->Commit(STGC_DEFAULT) == expected);
}
void packedReaderFaults() {
    constexpr ULONG blockBytes = ProtectedCustodyCodec::blockBytes;
    const auto prepare = [](const std::shared_ptr<ProtectedPackedCustodyOwner>& owner) {
        auto verified = ProtectedPackedCustodyTree::verify(owner); assert(verified.ok());
        auto tree = std::move(*verified.value);
        {
            const auto full = tree->appendBlock(CustodyBytes(ProtectedCustodyCodec::blockBytes, 0x37));
            assert(full.snapshot); tree = full.snapshot;
        }
        {
            const auto tail = tree->appendBlock(CustodyBytes{1, 3, 5});
            assert(tail.snapshot); tree = tail.snapshot;
        }
        return tree;
    };
    for (const auto selected : {Fault::read, Fault::throwingRead}) {
        Fixture fixture;
        auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        auto owner = std::move(*opened.value);
        std::weak_ptr<ProtectedPackedCustodyOwner> retained = owner;
        auto tree = prepare(owner);
        auto cancellation = std::make_shared<std::atomic<bool>>(false);
        auto reader = openProtectedCustodyReader(tree, cancellation); assert(reader.ok());
        auto stream = std::move(reader.value->stream);
        std::uint8_t byte = 0;
        ULONG got = 0;
        assert(stream->Read(&byte, 1, &got) == S_OK && got == 1 && byte == 0x37);
        LARGE_INTEGER start{};
        assert(stream->Seek(start, STREAM_SEEK_SET, nullptr) == S_OK);
        Microsoft::WRL::ComPtr<IStream> clone;
        assert(stream->Clone(clone.GetAddressOf()) == S_OK);
        std::vector<std::uint8_t> output(blockBytes+3, 0xa5);
        inject(selected); // Next actual native read, after the cached block0 prefix has been copied.
        got = 9;
        const auto expected = selected == Fault::read ? HRESULT_FROM_WIN32(ERROR_READ_FAULT) : E_OUTOFMEMORY;
        assert(stream->Read(output.data(), static_cast<ULONG>(output.size()), &got) == expected);
        assert(got == 0 && reads == 1 && writes == 0 && flushes == 0);
        assert(std::all_of(output.begin(), output.begin()+blockBytes, [](std::uint8_t value) { return value == 0; }));
        assert(std::all_of(output.begin()+blockBytes, output.end(), [](std::uint8_t value) { return value == 0xa5; }));
        const auto fault = tree->checkRead();
        assert(!fault.ok() && fault.error == (selected == Fault::read ? CustodyFileError::ioFailed : CustodyFileError::allocationFailed));
        assert(fault.nativeError == (selected == Fault::read ? ERROR_READ_FAULT : 0U));
        inject(Fault::none);
        assertReaderFailed(stream.Get(), expected);
        assertReaderFailed(clone.Get(), expected);
        cancellation->store(true); // A later cancellation cannot replace the first storage failure.
        assertReaderFailed(clone.Get(), expected);
        cancellation->store(false);
        assert(reads == 0 && writes == 0 && flushes == 0 && metadataQueries == 0);
        owner.reset(); tree.reset();
        assert(!retained.expired()); deniedWriter(fixture);
        stream.Reset();
        assert(!retained.expired()); deniedWriter(fixture);
        clone.Reset();
        assert(retained.expired()); // Failed streams keep the actual owner until the last actual release.
    }
    // Each operation must observe a physical fault even when block0 is cached.
    for (unsigned operation = 0; operation < 5; ++operation) {
        for (const bool allocation : {false, true}) {
            Fixture fixture;
            auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
            auto tree = prepare(*opened.value);
            auto cancellation = std::make_shared<std::atomic<bool>>(false);
            auto reader = openProtectedCustodyReader(tree, cancellation); assert(reader.ok());
            auto& stream = reader.value->stream;
            std::uint8_t byte = 0;
            ULONG got = 0;
            assert(stream->Read(&byte, 1, &got) == S_OK && got == 1 && byte == 0x37);
            LARGE_INTEGER start{};
            assert(stream->Seek(start, STREAM_SEEK_SET, nullptr) == S_OK);
            Microsoft::WRL::ComPtr<IStream> clone;
            assert(stream->Clone(clone.GetAddressOf()) == S_OK);
            if (!allocation) (*opened.value)->blockWrites();
            inject(allocation ? Fault::throwingMetadata : Fault::none);
            inspectUnwindAdmission = allocation; failureRetainedJob = false;
            const auto expected = allocation ? E_OUTOFMEMORY : STG_E_READFAULT;
            HRESULT result = S_OK;
            switch (operation) {
            case 0:
                byte = 0xa5; got = 9;
                result = stream->Read(&byte, 1, &got);
                assert(got == 0 && byte == 0xa5);
                break;
            case 1: result = stream->Seek(start, STREAM_SEEK_SET, nullptr); break;
            case 2: { STATSTG stat{}; result = stream->Stat(&stat, STATFLAG_NONAME); break; }
            case 3: { IStream* rejected = stream.Get(); result = stream->Clone(&rejected); assert(!rejected); break; }
            default: result = stream->Commit(STGC_DEFAULT); break;
            }
            inspectUnwindAdmission = false;
            assert(result == expected && reads == 0 && writes == 0 && flushes == 0);
            if (allocation) assert(failureRetainedJob && metadataQueries == 1);
            else assert(metadataQueries == 0);
            const auto fault = tree->checkRead();
            assert(!fault.ok() && fault.error == (allocation ? CustodyFileError::allocationFailed : CustodyFileError::recoveryRequired));
            assert(fault.nativeError == 0);
            inject(Fault::none);
            assertReaderFailed(stream.Get(), expected);
            assertReaderFailed(clone.Get(), expected);
            cancellation->store(true);
            assertReaderFailed(stream.Get(), expected);
            assert(reads == 0 && writes == 0 && flushes == 0 && metadataQueries == 0);
        }
    }
    {
        Fixture fixture;
        auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        auto tree = prepare(*opened.value);
        auto cancellation = std::make_shared<std::atomic<bool>>(false);
        auto reader = openProtectedCustodyReader(tree, cancellation); assert(reader.ok());
        auto& stream = reader.value->stream;
        std::uint8_t byte = 0;
        ULONG got = 0;
        assert(stream->Read(&byte, 1, &got) == S_OK && got == 1 && byte == 0x37);
        LARGE_INTEGER start{};
        assert(stream->Seek(start, STREAM_SEEK_SET, nullptr) == S_OK);
        Microsoft::WRL::ComPtr<IStream> clone;
        assert(stream->Clone(clone.GetAddressOf()) == S_OK);
        inject(Fault::none);
        {
            std::array<CustodyNativeJob, 4> occupied;
            assert(std::all_of(occupied.begin(), occupied.end(), [](const CustodyNativeJob& job) { return bool(job); }));
            assertReaderFailed(stream.Get(), E_OUTOFMEMORY); // Admission before metadata or cached-byte success.
            assertReaderFailed(clone.Get(), E_OUTOFMEMORY);
            assert(reads == 0 && writes == 0 && flushes == 0 && metadataQueries == 0);
        }
        assertReaderFailed(stream.Get(), E_OUTOFMEMORY);
        assertReaderFailed(clone.Get(), E_OUTOFMEMORY);
        assert(reads == 0 && writes == 0 && flushes == 0 && metadataQueries == 0);
        assert(tree->checkRead().ok()); // Admission refused the stream operation, not the healthy physical owner.
    }
    inject(Fault::none);
}
}
#endif

int main(int argc, char** argv) {
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
    (void)argc; (void)argv;
    const auto result = ProtectedPackedCustodyOwner::open({}, "package-a",
        {{{}, {}, CustodyRole::canonical}, {}}, CustodyFileAccess::createNew);
    assert(!result.ok() && result.error == CustodyFileError::unsupportedPlatform);
#else
    if (argc == 2 && std::strcmp(argv[1], "--resize-wipe") == 0) { resizePlainWipe(); return 0; }
    if (argc == 2 && std::strcmp(argv[1], "--packed-writer-cancel") == 0) { packedWriterCancellation(); return 0; }
    if (argc == 2 && std::strcmp(argv[1], "--packed-writer-admission") == 0) { packedWriterAdmission(); return 0; }
    if (argc == 2 && std::strcmp(argv[1], "--packed-writer-resources") == 0) { packedWriterResources(); return 0; }
    if (argc == 2 && std::strcmp(argv[1], "--packed-writer-cuts") == 0) { packedWriterCuts(); return 0; }
    if (argc == 2 && std::strcmp(argv[1], "--packed-writer-cadence") == 0) { packedWriterCadence(64); return 0; }
    if (argc == 2 && std::strcmp(argv[1], "--packed-writer-cadence-short") == 0) { packedWriterCadence(2); return 0; }
    const auto beforeCache = CustodyOwnedMemory::usedBytes();
    std::size_t emptyCharge = 0;
    {
        const CustodyBytes empty;
        emptyCharge = CustodyOwnedMemory::usedBytes()-beforeCache;
    }
    assert(CustodyOwnedMemory::usedBytes() == beforeCache);
    {
        Fixture fixture;
        auto owner = fixture.open(CustodyFileAccess::createNew); assert(owner.ok());
        auto tree = ProtectedPackedCustodyTree::verify(*owner.value); assert(tree.ok());
        auto reader = openProtectedCustodyReader(*tree.value, std::make_shared<std::atomic<bool>>(false));
        assert(reader.ok());
        STATSTG stat{}; ULONG got = 9; std::uint8_t byte = 0x77;
        assert(reader.value->stream->Stat(&stat, STATFLAG_NONAME) == S_OK && stat.cbSize.QuadPart == 0);
        assert(reader.value->stream->Read(nullptr, 0, &got) == S_OK && got == 0);
        assert(reader.value->stream->Read(&byte, 1, &got) == S_FALSE && got == 0 && byte == 0x77);
    }
    std::fprintf(stderr, "reader-cache empty_proxy_charge=%zu observed_delta=%zu\n",
        emptyCharge, CustodyOwnedMemory::usedBytes()-beforeCache);
    assert(CustodyOwnedMemory::usedBytes() == beforeCache+emptyCharge);
    // Preserve exact final comparisons with the same live EMPTY global cache.
    const auto before = CustodyOwnedMemory::usedBytes();
    std::fputs("owner: tree guard faults\n", stderr);
    treeGuardFaults();
    packedWriterCancellation();
    packedWriterAdmission();
    packedWriterResources();
    packedWriterCuts();
    packedWriterCadence(2);
    std::fputs("owner: packed reader faults\n", stderr);
    packedReaderFaults();
    std::fputs("owner: live logical append cuts\n", stderr);
    logicalAppendFaults();
    logicalAppendFaults(3);
    logicalAppendFaults(5, CommitCase::tail);
    logicalAppendFaults(262144, CommitCase::interior);
    logicalAppendFaults(1, CommitCase::shrink);
    logicalAppendFaults(1, CommitCase::grow);
    logicalAppendFaults(1, CommitCase::empty);
    resizePlainWipe();
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
