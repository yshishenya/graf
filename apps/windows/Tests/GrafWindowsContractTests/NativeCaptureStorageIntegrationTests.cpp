#ifdef NDEBUG
#undef NDEBUG
#endif
#include "../../RecApp/Recording/NativeCapture.h"
#include "../../RecApp/Recording/LocalRecordingPackage.h"
#include "../../RecApp/Recording/ProtectedLocalRecordingPlayback.h"
#include "../../RecApp/Storage/Sha256.h"
#include "../GeneratedRecordingFixtures.h"
#include <cassert>
#include <chrono>
#include <charconv>
#include <cmath>
#include <exception>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <limits>
#include <thread>
#include <type_traits>
#include <mfapi.h>
#include <winternl.h>

namespace {
using namespace graf::windows;
using ProtectedUploadEntry = decltype(&DesktopHttpTransport::uploadProtected);
static_assert(std::is_invocable_v<ProtectedUploadEntry, const ProtectedDesktopHttpConfig&,
    const ProtectedUploadQueueValue::Item&, std::shared_ptr<const LocalRecordingPackage::ProtectedInspection>,
    const DesktopHttpTransport::ProtectedUploadSend&>, "protected_upload_requires_charged_queue_item");
static_assert(!std::is_invocable_v<ProtectedUploadEntry, const ProtectedDesktopHttpConfig&,
    const UploadCustodyItem&, std::shared_ptr<const LocalRecordingPackage::ProtectedInspection>,
    const DesktopHttpTransport::ProtectedUploadSend&>, "protected_upload_rejects_ordinary_queue_item");
}
#if defined(_MSC_VER) && defined(_DEBUG)
#include <crtdbg.h>
#include <dbghelp.h>

// Executable-only one-shot cut, armed after a real PUT ACK and the following
// wire failure. All acquisition/encoding and ordinary allocations stay real.
namespace {
struct TerminalAllocationCut { bool armed = false, hit = false, qualified = false; };
thread_local TerminalAllocationCut terminalAllocation;
std::atomic<DWORD> deletionRetirementThread{0};
void pauseDeletionRetirement() noexcept;

bool traceTerminalAllocation() {
    std::array<void*, 64> frames{};
    const auto count = CaptureStackBackTrace(1, static_cast<DWORD>(frames.size()), frames.data(), nullptr);
    bool qualified = false;
    constexpr auto absent = std::numeric_limits<USHORT>::max();
    USHORT emptyFrame = absent, catchFrame = absent;
    std::array<char, 4096> catchInstance{};
    std::size_t catchInstanceSize = 0;
    for (USHORT index = 0; index < count; ++index) {
        alignas(SYMBOL_INFO) std::array<std::byte, sizeof(SYMBOL_INFO) + 4096> storage{};
        auto* symbol = reinterpret_cast<SYMBOL_INFO*>(storage.data());
        symbol->SizeOfStruct = sizeof(SYMBOL_INFO); symbol->MaxNameLen = 4096;
        const auto raw = reinterpret_cast<DWORD64>(frames[index]);
        const auto pc = raw ? raw - 1 : 0;
        DWORD64 displacement = 0;
        const bool resolved = SymFromAddr(GetCurrentProcess(), pc, &displacement, symbol) != FALSE;
        IMAGEHLP_LINE64 line{}; line.SizeOfStruct = sizeof(line); DWORD offset = 0;
        const bool located = SymGetLineFromAddr64(GetCurrentProcess(), pc, &offset, &line) != FALSE;
        const std::string_view name = resolved ? std::string_view(symbol->Name, symbol->NameLen) : "unresolved";
        const std::string_view path = located && line.FileName ? line.FileName : "unresolved";
        const auto slash = path.find_last_of("\\/");
        const auto file = slash == std::string_view::npos ? path : path.substr(slash + 1);
        std::fprintf(stderr, "TERMINAL_ALLOCATION frame=%u pc=%016llx symbol=%.*s file=%.*s line=%lu\n",
            static_cast<unsigned>(index), static_cast<unsigned long long>(pc),
            static_cast<int>(name.size()), name.data(), static_cast<int>(file.size()), file.data(),
            located ? line.LineNumber : 0UL);
        // RED identity: the frozen319 catch creates/moves/returns a NEW result.
        // Other post-ACK allocations cannot stand in for this exact boundary.
        if (name.find("uploadPrepared") != std::string_view::npos &&
            file == "DesktopHttpTransport.cpp" && located && line.LineNumber >= 1194 && line.LineNumber <= 1196)
            qualified = true;
        // MSVC's catch funclet maps this inlined default member initializer to
        // the header. Require BOTH that exact ctor and its actual wire caller,
        // plus the string construction frame; a generic catch/abort is not RED.
        if (name.find("basic_string") != std::string_view::npos && name.find("_Construct_empty") != std::string_view::npos &&
            file == "xstring" && emptyFrame == absent) emptyFrame = index;
        const auto instance = name.find("uploadPrepared");
        if (instance != std::string_view::npos && name.find("catch$") != std::string_view::npos &&
            file == "DesktopHttpTransport.h" && located && line.LineNumber == 35 && emptyFrame < index) {
            const auto suffix = name.find("'::", instance);
            if (suffix != std::string_view::npos && suffix - instance < catchInstance.size()) {
                catchInstanceSize = suffix - instance;
                std::memcpy(catchInstance.data(), name.data() + instance, catchInstanceSize);
                catchFrame = index;
            }
        }
        if (instance != std::string_view::npos && file == "DesktopHttpTransport.cpp" &&
            located && line.LineNumber == 1168 && catchFrame < index &&
            name.substr(instance) == std::string_view(catchInstance.data(), catchInstanceSize)) qualified = true;
    }
    std::fprintf(stderr, "TERMINAL_ALLOCATION hit=1 qualified=%u\n", qualified ? 1U : 0U);
    std::fflush(stderr); // Preserve the proof even if MSVC's noexcept ctor aborts.
    return qualified;
}
}
void* operator new(std::size_t bytes) {
    if (terminalAllocation.armed) {
        terminalAllocation.armed = false; // Symbol lookup must not recurse into the cut.
        terminalAllocation.hit = true;
        terminalAllocation.qualified = traceTerminalAllocation();
        throw std::bad_alloc();
    }
    if (auto* memory = std::malloc(bytes ? bytes : 1)) return memory;
    throw std::bad_alloc();
}
void operator delete(void* memory) noexcept { pauseDeletionRetirement(); std::free(memory); }
void operator delete(void* memory, std::size_t) noexcept { pauseDeletionRetirement(); std::free(memory); }
#endif

// Existing native fault-test pattern: compile the actual file layer with
// executable-local wrappers, never add a production failure switch.
namespace {
std::size_t idleOwnedBytes = 0;
bool enforceProtectedHttpControlTypes = true;
enum class IoCut { none, flush, ambiguousRename, pauseAfterFlush, pauseAfterRename };
std::atomic<IoCut> ioCut{IoCut::none};
std::atomic<unsigned> liveMetadataRenameTarget{0}, liveMetadataRenameCount{0};
std::atomic<bool> liveMetadataRenameAfter{false};
std::atomic<bool> degradedManifestRenameCut{false};
std::mutex cutMutex;
std::condition_variable cutWake;
bool cutReached = false, cutReleased = false;
std::atomic<bool> pauseReopenRead{false};
std::atomic<bool> denyDeletionReadback{false}; // Armed only after the generated deletion's publication result.
std::atomic<bool> longIndexReported{false};
void pauseAtCut();
#if defined(_MSC_VER) && defined(_DEBUG)
void pauseDeletionRetirement() noexcept {
    auto thread = deletionRetirementThread.load();
    if (thread && thread == GetCurrentThreadId() && deletionRetirementThread.compare_exchange_strong(thread, 0))
        pauseAtCut(); // First actual worker deallocation after adoption ACK.
}
#endif
// Synchronous generated metadata probe only; inactive during all capture/MF work.
std::atomic<std::atomic<bool>*> discoveryCancellation{nullptr};
std::atomic<unsigned> discoveryReads{0}, discoveryReadCut{0}, discoverySecondIndex{0};
std::atomic<unsigned> discoveryFired{0};
std::atomic<bool> pauseOldPackedRead{false};
std::wstring oldPackedPath; // Set before arming; cleared only after worker drain.
std::atomic<bool> failPlaybackWrite{false};
std::atomic<unsigned> playbackWriteCuts{0};
std::wstring playbackWritePath; // Generated fixture only; immutable until finalizer drain.
std::atomic<bool> pausePlaybackPackageMetadata{false};
std::atomic<bool> pausePlaybackQueueMetadata{false};
BOOL WINAPI integrationWrite(HANDLE file, LPCVOID bytes, DWORD length, LPDWORD written, LPOVERLAPPED operation) {
    if (length && operation && failPlaybackWrite.load()) {
        const auto offset = (static_cast<std::uint64_t>(operation->OffsetHigh) << 32) | operation->Offset;
        if (offset >= ProtectedPackedCustodyFormat::appendOffset) {
            wchar_t path[32768]{};
            const auto size = GetFinalPathNameByHandleW(file, path, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
            assert(size && size < 32768);
            if (std::wstring_view(path, size) == playbackWritePath && failPlaybackWrite.exchange(false)) {
                ++playbackWriteCuts;
                std::fprintf(stderr, "PROTECTED_MF_WRITE cut=1 offset=%llu bytes=%lu\n",
                    static_cast<unsigned long long>(offset), length);
                std::fflush(stderr);
                if (written) *written = 0;
                SetLastError(ERROR_WRITE_FAULT);
                return FALSE;
            }
        }
    }
    return WriteFile(file, bytes, length, written, operation);
}
BOOL WINAPI integrationRead(HANDLE file, LPVOID bytes, DWORD length, LPDWORD got, LPOVERLAPPED overlapped) {
    if (denyDeletionReadback.load()) {
        if (got) *got = 0;
        SetLastError(ERROR_READ_FAULT); return FALSE;
    }
    if (pauseReopenRead.exchange(false)) pauseAtCut(); // Fresh native open after old owner/commit teardown.
    const auto result = ReadFile(file, bytes, length, got, overlapped);
    const auto error = GetLastError();
    if (result && length && pausePlaybackQueueMetadata.load()) {
        wchar_t path[32768]{};
        const auto size = GetFinalPathNameByHandleW(file, path, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
        assert(size && size < 32768);
        if (std::wstring_view(path, size).find(L"\\queue\\") != std::wstring_view::npos &&
            pausePlaybackQueueMetadata.exchange(false)) {
            std::fputs("PROTECTED_PLAYBACK queue_validation_cut=1\n", stderr); std::fflush(stderr);
            pauseAtCut();
        }
    }
    if (result && length && pausePlaybackPackageMetadata.load()) {
        wchar_t path[32768]{};
        const auto size = GetFinalPathNameByHandleW(file, path, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
        assert(size && size < 32768);
        if (std::wstring_view(path, size).find(L"\\package-state\\") != std::wstring_view::npos &&
            pausePlaybackPackageMetadata.exchange(false)) {
            std::fputs("PROTECTED_PLAYBACK metadata_before_publication_cut=1\n", stderr); std::fflush(stderr);
            pauseAtCut();
        }
    }
    if (result && length && got && *got == length && overlapped && pauseOldPackedRead.load()) {
        const auto offset = (static_cast<std::uint64_t>(overlapped->OffsetHigh) << 32) | overlapped->Offset;
        if (offset >= ProtectedPackedCustodyFormat::appendOffset) {
            wchar_t path[32768]{};
            const auto size = GetFinalPathNameByHandleW(file, path, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
            assert(size && size < 32768);
            const std::wstring_view name(path, size);
            if (name == oldPackedPath && pauseOldPackedRead.exchange(false)) {
                std::fputs("PROTECTED_INSPECTION nonempty_old_package_packed_append_read=1\n", stderr);
                std::fflush(stderr);
                pauseAtCut();
            }
        }
    }
    const auto cancellation = discoveryCancellation.load();
    if (result && cancellation) {
        wchar_t path[32768]{};
        const auto size = GetFinalPathNameByHandleW(file, path, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
        assert(size && size < 32768);
        const std::wstring_view name(path, size);
        if (name.find(L"\\package-state\\") != std::wstring_view::npos) {
            const auto read = ++discoveryReads;
            if (name.size() >= 7 && name.substr(name.size() - 7) == L"index.1") discoverySecondIndex = read;
            if (read == discoveryReadCut) { discoveryFired = read; cancellation->store(true); }
        }
    }
    SetLastError(error);
    return result;
}
void pauseAtCut() {
    std::unique_lock<std::mutex> lock(cutMutex);
    cutReached = true; cutWake.notify_all();
    cutWake.wait(lock, [] { return cutReleased; });
}
HANDLE WINAPI integrationCreateFile(LPCWSTR path, DWORD access, DWORD share, LPSECURITY_ATTRIBUTES security,
    DWORD disposition, DWORD flags, HANDLE templateFile) {
    const auto handle = CreateFileW(path, access, share, security, disposition, flags, templateFile);
    const auto error = GetLastError();
    if (handle == INVALID_HANDLE_VALUE && path && std::wstring_view(path).find(L"index.tmp-") != std::wstring_view::npos) {
        std::fprintf(stderr, "NATIVE_INDEX_CREATE failed=1 path_units=%zu native=%lu\n", std::wstring_view(path).size(), error);
        std::fflush(stderr);
    }
    if (handle != INVALID_HANDLE_VALUE && path && std::wstring_view(path).size() >= MAX_PATH &&
        std::wstring_view(path).find(L"index.tmp-") != std::wstring_view::npos && !longIndexReported.exchange(true)) {
        assert(std::wstring_view(path).substr(0, 4) == L"\\\\?\\");
        std::fprintf(stderr, "NATIVE_INDEX_CREATE long_success=1 path_units=%zu extended=1\n", std::wstring_view(path).size());
        std::fflush(stderr);
    }
    SetLastError(error);
    return handle;
}
BOOL WINAPI integrationFlush(HANDLE file) {
    const auto cut = ioCut.load();
    if (cut == IoCut::flush) { SetLastError(ERROR_WRITE_FAULT); return FALSE; }
    const auto result = FlushFileBuffers(file);
    if (result && cut == IoCut::pauseAfterFlush) pauseAtCut();
    return result;
}
NTSTATUS NTAPI integrationRename(HANDLE file, PIO_STATUS_BLOCK io, PVOID info, ULONG length, FILE_INFORMATION_CLASS kind) {
    using Function = NTSTATUS(NTAPI*)(HANDLE, PIO_STATUS_BLOCK, PVOID, ULONG, FILE_INFORMATION_CLASS);
    const auto procedure = GetProcAddress(GetModuleHandleW(L"ntdll.dll"), "NtSetInformationFile"); assert(procedure);
    Function function = nullptr; static_assert(sizeof(function) == sizeof(procedure));
    std::memcpy(&function, &procedure, sizeof(function));
    bool degradedCut = false;
    if (degradedManifestRenameCut.load()) {
        wchar_t path[32768]{};
        const auto size = GetFinalPathNameByHandleW(file,path,32768,FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
        assert(size && size < 32768);
        if (std::wstring_view(path,size).find(L"\\manifest\\") != std::wstring_view::npos)
            degradedCut = degradedManifestRenameCut.exchange(false);
        if (degradedCut) {
            ++liveMetadataRenameCount;
            std::fprintf(stderr,"DEGRADED_MANIFEST_CUT qualified_role=1 after=%u\n",liveMetadataRenameAfter ? 1U : 0U);
            std::fflush(stderr);
            if (!liveMetadataRenameAfter) { io->Status = static_cast<NTSTATUS>(0xC0000022UL); return io->Status; }
        }
    }
    const auto target = liveMetadataRenameTarget.load();
    const auto ordinal = target ? ++liveMetadataRenameCount : 0;
    const bool fail = target && ordinal == target;
    if (fail) {
        wchar_t path[32768]{};
        const auto size = GetFinalPathNameByHandleW(file, path, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
        assert(size && size < 32768);
        const auto role = ordinal == 2 ? L"\\manifest\\" : L"\\package-state\\";
        assert(std::wstring_view(path, size).find(role) != std::wstring_view::npos);
        if (!liveMetadataRenameAfter) {
            std::fprintf(stderr, "LIVE_METADATA rename_cut=%u after=0 qualified_role=1\n", ordinal);
            std::fflush(stderr);
            io->Status = static_cast<NTSTATUS>(0xC0000022UL); return io->Status;
        }
    }
    const auto result = function(file, io, info, length, kind);
    if (degradedCut && liveMetadataRenameAfter) {
        assert(result == 0 && io->Status == 0);
        io->Status = static_cast<NTSTATUS>(0xC0000022UL);
    }
    if (fail && liveMetadataRenameAfter) {
        assert(result == 0 && io->Status == 0 && "after_cut_requires_actual_successful_rename");
        io->Status = static_cast<NTSTATUS>(0xC0000022UL);
        std::fprintf(stderr, "LIVE_METADATA rename_cut=%u after=1 qualified_role=1 original_status=0 original_io_status=0\n", ordinal);
        std::fflush(stderr);
    }
    if (result == 0 && ioCut.load() == IoCut::pauseAfterRename) pauseAtCut();
    if (result == 0 && ioCut.load() == IoCut::ambiguousRename) io->Status = static_cast<NTSTATUS>(0xC0000022UL);
    return result;
}
FARPROC WINAPI integrationProcedure(HMODULE module, LPCSTR name) {
    if (std::strcmp(name, "NtSetInformationFile") == 0) {
        const auto function = &integrationRename; FARPROC procedure = nullptr;
        static_assert(sizeof(function) == sizeof(procedure));
        std::memcpy(&procedure, &function, sizeof(function)); return procedure;
    }
    return GetProcAddress(module, name);
}
}
#define FlushFileBuffers integrationFlush
#define GetProcAddress integrationProcedure
#define ReadFile integrationRead
#define WriteFile integrationWrite
#define CreateFileW integrationCreateFile
#include "../../RecApp/Storage/ProtectedCustodyFiles.cpp"
#undef CreateFileW
#undef ReadFile
#undef WriteFile
#undef FlushFileBuffers
#undef GetProcAddress

namespace {
// Only the owning test worker arms/accesses these; no MF callback touches them.
thread_local bool observeClone = false;
thread_local IStream* observedPlaybackClone = nullptr;
std::atomic<bool> retainConsumerClone{false};
std::atomic<IStream*> retainedConsumerClone{nullptr};
std::mutex consumerCloneMutex;
IStream* takeConsumerClone() {
    std::lock_guard<std::mutex> lock(consumerCloneMutex);
    retainConsumerClone.store(false);
    return retainedConsumerClone.exchange(nullptr);
}
HRESULT WINAPI integrationPlaybackByteStream(IStream* input, IMFByteStream** output) {
    const auto result = MFCreateMFByteStreamOnStream(input, output);
    if (SUCCEEDED(result) && output && *output && observeClone) {
        observedPlaybackClone = input; // Borrow only: partial-open teardown must not wait for a test AddRef.
        observeClone = false;
    }
    if (SUCCEEDED(result) && output && *output && retainConsumerClone.load()) {
        std::lock_guard<std::mutex> lock(consumerCloneMutex);
        if (retainConsumerClone.exchange(false)) {
            input->AddRef(); retainedConsumerClone.store(input, std::memory_order_release);
        }
    }
    return result;
}
}
#define MFCreateMFByteStreamOnStream integrationPlaybackByteStream
#include "../../RecApp/Recording/ProtectedLocalRecordingPlayback.cpp"
#undef MFCreateMFByteStreamOnStream

namespace graf::windows {
// Observation only: no READY, identity, generation or owner injection.
struct NativeCaptureStorageTestPeer {
    static bool ready(const NativeCapture& capture) {
        if (!capture.storageStartup_) return false;
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return capture.storageStartup_->ready;
    }
    static std::uint64_t generation(const NativeCapture& capture) {
        if (!capture.storageStartup_) return 0;
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return capture.storageStartup_->adopted ? capture.storageStartup_->generation : 0;
    }
    static bool opened(const NativeCapture& capture) {
        if (!capture.storageStartup_) return false;
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        if (capture.storageStartup_->error != CustodyFileError::none || !capture.storageStartup_->generation) {
            std::fprintf(stderr, "startup refused: error=%u native=%u generation=%llu\n",
                static_cast<unsigned>(capture.storageStartup_->error), capture.storageStartup_->nativeError,
                static_cast<unsigned long long>(capture.storageStartup_->generation));
            return false;
        }
        return true;
    }
    static bool released(const NativeCapture& capture) {
        if (!capture.storageStartup_) return true;
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return capture.storageStartup_->terminal;
    }
    static auto projection(const NativeCapture& capture) { return capture.protectedQueueValue_; }
    static bool deletionResponseRetained(const NativeCapture& capture) {
        return capture.deletionFlight_ && capture.deletionFlight_->response && !capture.deletionThread_.joinable() &&
            capture.deletionFlight_->phase == NativeCapture::DeletionFlight::Phase::result;
    }
    static bool resultReady(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return capture.storageStartup_->resultReady;
    }
    static auto ticket(const NativeCapture& capture) { return capture.lastQueueTicket_; }
    static DWORD storageThread(const NativeCapture& capture) { return GetThreadId(capture.storageThread_.get()); }
    static auto storageWork(const NativeCapture& capture) { return capture.storageStartup_; }
    static bool deletionSlotRetired(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return !capture.storageStartup_->inFlight && !capture.storageStartup_->deletion;
    }
    static bool deletionFlightRetired(const NativeCapture& capture) {
        return !capture.deletionFlight_ && !capture.deletionThread_.joinable() && !capture.deletionContinuationId_;
    }
    static bool deletionNetworkExited(NativeCapture& capture) {
        return capture.deletionThread_.joinable() &&
            WaitForSingleObject(capture.deletionThread_.native_handle(), 0) == WAIT_OBJECT_0;
    }
    static bool deletionReconciliationPending(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return capture.storageStartup_->deletionReconciliation && capture.storageStartup_->reconciliationPending;
    }
    static auto workerTicket(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return capture.storageStartup_->ticket;
    }
    static bool reconciliationPending(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return capture.storageStartup_->reconciliationPending;
    }
    static bool physicalReadback(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return capture.storageStartup_->physicalReadback && capture.storageStartup_->resultReady;
    }
    static auto storageError(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return capture.storageStartup_->error;
    }
    static void diagnosePreparation(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        const auto& work = *capture.storageStartup_;
        std::fprintf(stderr, "PREPARATION command=%u command_ready=%u in_flight=%u failed=%u stop=%u generation=%llu upload=%u error=%u native=%u\n",
            static_cast<unsigned>(work.command), work.commandReady, work.inFlight, work.queueFailed, work.stop,
            static_cast<unsigned long long>(work.generation), work.upload ? 1U : 0U,
            static_cast<unsigned>(work.error), work.nativeError);
        if (work.recording) {
            std::lock_guard<std::mutex> recordingLock(work.recording->mutex);
            const auto& recording = *work.recording;
            std::fprintf(stderr, "PREPARATION prepared=%u started=%u finalizing=%u terminal=%u writer=%u reason=%u\n",
                recording.prepared, recording.started, recording.finalizing, recording.terminal,
                recording.writer ? 1U : 0U, static_cast<unsigned>(recording.result.reason));
        } else std::fputs("PREPARATION recording=absent\n", stderr);
        std::fflush(stderr);
    }
    // Enter the same private continuation as Record. Hardware prerequisites
    // may be generated; storage authority must come from the actual birth ACK.
    static bool requestRecording(NativeCapture& capture) { return capture.requestProtectedRecording(); }
    static void pollAccount(NativeCapture& capture) { capture.pollAccount(); }
    static void pollStorage(NativeCapture& capture) { capture.pollStorageStartup(true); }
    static bool displayFinished(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        const auto display = capture.storageStartup_->display;
        return display && display->done.load(std::memory_order_acquire);
    }
    static bool accountResultReady(const NativeCapture& capture) {
        return capture.accountFuture_.valid() &&
            capture.accountFuture_.wait_for(std::chrono::seconds(0)) == std::future_status::ready;
    }
    static bool prepared(const NativeCapture& capture) { return capture.protectedRecordingPrepared(); }
    static bool finalizationServiced(const NativeCapture& capture, std::string_view session) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        const auto& work = *capture.storageStartup_;
        if (work.commandReady || !work.inFlight || work.command != NativeCapture::StorageCommand::finalizeRecording ||
            !work.recording || work.recording != capture.recordingWork_ || !work.ticket.id ||
            work.ticket.kind != NativeCapture::QueueMutationKind::recording) return false;
        std::lock_guard<std::mutex> recordingLock(work.recording->mutex);
        return std::string_view(work.recording->session) == session && work.ticket.epoch == work.recording->epoch &&
            work.recording->started && work.recording->finalizing && !work.recording->terminal;
    }
    static bool preparationQueued(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        const auto& work = *capture.storageStartup_;
        if (!work.commandReady || !work.inFlight || work.command != NativeCapture::StorageCommand::prepareRecording ||
            !work.recording) return false;
        std::lock_guard<std::mutex> recordingLock(work.recording->mutex);
        return !work.recording->prepared && !work.recording->terminal && !work.recording->writer;
    }
    static bool preparationInProgress(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        const auto& work = *capture.storageStartup_;
        if (work.commandReady || !work.inFlight || work.command != NativeCapture::StorageCommand::prepareRecording ||
            !work.recording) return false;
        std::lock_guard<std::mutex> recordingLock(work.recording->mutex);
        return !work.recording->prepared && !work.recording->terminal && !work.recording->writer;
    }
    static std::uint64_t writtenFrames(const NativeCapture& capture) { return capture.protectedRecordingFrames(); }
    static WindowsCaptureSessionController& controller(NativeCapture& capture) { return *capture.controller_; }
    static TransitionResult startPrepared(NativeCapture& capture, const ReadinessInputs& hardware) {
        return capture.startPreparedRecording(hardware);
    }
};
struct CaptureSessionTestPeer {
    static bool bothEndsProcessed(const WindowsCaptureSessionController& controller) {
        return controller.sourceEndsProcessed_.load(std::memory_order_acquire) == std::uint8_t{3};
    }
    static bool completed(const WindowsCaptureSessionController& controller) {
        return controller.renderWorker_->finished() && controller.microphoneWorker_->finished() &&
            controller.dispatchFinished_.load(std::memory_order_acquire);
    }
    static void lateStopFailure(WindowsCaptureSessionController& controller) {
        controller.microphoneWorker_->completeNativeStop(-1);
    }
    template<class Render, class Microphone>
    static void devices(WindowsCaptureSessionController& controller, Render render, Microphone microphone) {
        controller.setEndpoints({"render", "Generated render", WasapiDataFlow::render, 48'000, 1, true, false, 1},
                                {"mic", "Generated microphone", WasapiDataFlow::capture, 48'000, 1, true, true, 1});
        controller.renderWorker_->deviceRunForTesting_ = std::move(render);
        controller.microphoneWorker_->deviceRunForTesting_ = std::move(microphone);
    }
};
}

namespace {
using namespace graf::windows;
class GeneratedAec final : public IAec3Processor {
public:
    bool process(const float*, const float* microphone, float* cleaned) noexcept override {
        std::copy_n(microphone, 480, cleaned);
        return true; // Generated acquisition fixture, not evidence for real AEC.
    }
};
struct Fixture {
    std::filesystem::path parent, root;
    Fixture() {
        GUID id{}; assert(CoCreateGuid(&id) == S_OK);
        wchar_t name[40]{}; assert(StringFromGUID2(id, name, 40));
        // GetTempPath may return an 8.3 alias; match the actual long namespace,
        // as the existing native custody fixture does. Do not weaken product IO.
        const auto temporary = std::filesystem::temp_directory_path();
        wchar_t actual[32768]{};
        const auto length = GetLongPathNameW(temporary.c_str(), actual, 32768);
        assert(length && length < 32768);
        parent = std::filesystem::path(actual) / (std::wstring(L"graf-storage-integration-") + name);
        assert(CreateDirectoryW(parent.c_str(), nullptr));
        root = parent / L"recordings"; // The real worker must birth this private child.
    }
    ~Fixture() {
        std::error_code error; std::filesystem::remove_all(parent, error); assert(!error);
    }
};
template<class Predicate> bool waitFor(Predicate predicate, std::chrono::seconds timeout = std::chrono::seconds(10)) {
    const auto deadline = std::chrono::steady_clock::now() + timeout;
    while (!predicate()) {
        if (std::chrono::steady_clock::now() >= deadline) return false;
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    return true;
}
using Snapshot = std::map<std::wstring, std::string>;
Snapshot snapshot(const std::filesystem::path& root) {
    Snapshot result;
    for (const auto& entry : std::filesystem::recursive_directory_iterator(root)) {
        if (!entry.is_regular_file()) continue;
        const auto hash = sha256File(entry.path()); assert(hash.size() == 64);
        result.emplace(entry.path().lexically_relative(root).native(), hash);
    }
    return result;
}
// Genuine protected persistence of generated domain rows, not package/account
// authority. The fixture writer only captures JSON; no plaintext ledger is made.
void seedQueue(const std::filesystem::path& root, bool selection = false) {
    auto seed = std::async(std::launch::async, [root, selection] {
        std::string json;
        DesktopUploadQueueService queue(root / L"unused.json", root,
            [&](const auto&, const auto&, std::string_view bytes) { json.assign(bytes); return true; });
        queue.setClock([] { return 1000; });
        const DesktopAccountIdentity owner{"11111111-1111-4111-8111-111111111111",
            "22222222-2222-4222-8222-222222222222"};
        for (const auto status : {UploadQueueStatus::needsAuth, UploadQueueStatus::uploaded}) {
            const auto id = status == UploadQueueStatus::needsAuth ? "waiting" : "retained";
            UploadCustodyItem row{id, selection ? std::string(id) + "-dir" : id, id, root / id, status, {11, 22, 33}, 3,
                status == UploadQueueStatus::needsAuth ? "auth_required" : "",
                owner.userId, owner.workspaceId};
            if (selection && status == UploadQueueStatus::uploaded) row.meetingId = "33333333-3333-4333-8333-333333333333";
            assert(queue.enqueue(std::move(row)));
        }
        if (selection) assert(queue.enqueue({"local-only", "local-only-dir", "local-only", root / "local-only",
            UploadQueueStatus::pending, {}, 0, "", owner.userId, owner.workspaceId}));
        std::string operation;
        assert(queue.requestDeletion(DeletionTarget::meeting, "33333333-3333-4333-8333-333333333333",
            owner, selection ? DesktopHttpConfig{}.baseOrigin : "https://example.test", operation));
        const std::string marker = "\"purge_acknowledgements\":[";
        const auto at = json.find(marker); assert(at != std::string::npos);
        json.insert(at + marker.size(), R"({"task_id":"44444444-4444-4444-8444-444444444444","meeting_id":"33333333-3333-4333-8333-333333333333","acknowledged_at_ms":900})");
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        auto ownerResult = ProtectedCustodyStoreOwner::open(root, cancel); assert(ownerResult.ok());
        auto store = *ownerResult.value;
        assert(store->queueGeneration() == 1);
        CustodyBytes bytes(json.begin(), json.end());
        auto saved = commitProtectedCustodyMetadata(store, store->queueContext(), 1, bytes, cancel);
        assert(saved.state == CustodyCommitState::committed && saved.targetGeneration == 2);
    });
    seed.get();
}
void startAndAdopt(NativeCapture& capture, std::uint64_t generation) {
    capture.startStorageValidation();
    assert(waitFor([&] { return NativeCaptureStorageTestPeer::ready(capture); }));
    assert(NativeCaptureStorageTestPeer::opened(capture));
    capture.pollUploads();
    assert(NativeCaptureStorageTestPeer::generation(capture) == generation);
    assert(NativeCaptureStorageTestPeer::projection(capture));
}
void protectedManualSend() {
    const DesktopHttpTransport::UploadSend accountWire = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        if (request.path == "/desktop/settings/spaces") return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        if (request.path == "/api/v1/auth/me") return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
        return {403, "{}"};
    };
    for (const auto cut : {IoCut::none, IoCut::flush, IoCut::ambiguousRename, IoCut::pauseAfterFlush, IoCut::pauseAfterRename}) {
        Fixture fixture; seedQueue(fixture.root);
        {
            std::atomic<unsigned> networkCalls{0};
            const DesktopHttpTransport::ProtectedUploadSend wire = [&](const auto&, const auto&) {
                ++networkCalls; return DesktopHttpTransport::ProtectedUploadResponse{503, "{}"};
            };
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, accountWire, wire);
            startAndAdopt(capture, 2);
            capture.setAuthSessionToken("generated-manual-send");
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
            const auto before = NativeCaptureStorageTestPeer::projection(capture);
            assert(!capture.requestProtectedManualSend({}, "waiting", capture.authGeneration(), false));
            assert(!capture.requestProtectedManualSend(before, "absent", capture.authGeneration(), false));
            assert(!capture.requestProtectedManualSend(before, "waiting", capture.authGeneration() + 1, false));
            { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
            ioCut.store(cut);
            const auto pending = capture.requestProtectedManualSend(before, "waiting", capture.authGeneration(), false);
            assert(pending && pending->kind == NativeCapture::QueueMutationKind::manualSend && pending->state == NativeCapture::QueueTicketState::pending);
            assert(!capture.requestProtectedManualSend(before, "waiting", capture.authGeneration(), false));
            if (cut == IoCut::pauseAfterFlush || cut == IoCut::pauseAfterRename) {
                const bool reached = waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; });
                capture.setAuthSessionToken({});
                { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; cutWake.notify_all(); }
                assert(reached);
            }
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            ioCut.store(IoCut::none);
            assert(networkCalls == 0 && NativeCaptureStorageTestPeer::projection(capture) == before && !capture.updateWorkDrained());
            capture.setAuthSessionToken({}); // Lost/stale UI still adopts physical truth, never launches HTTP.
            NativeCaptureStorageTestPeer::pollStorage(capture);
            const auto result = capture.protectedManualSendTicket(pending->id); assert(result);
            const bool committed = cut == IoCut::none || cut == IoCut::pauseAfterRename;
            assert(result->state == (committed ? NativeCapture::QueueTicketState::committed :
                cut == IoCut::ambiguousRename ? NativeCapture::QueueTicketState::ambiguous : NativeCapture::QueueTicketState::notCommitted));
            const auto after = NativeCaptureStorageTestPeer::projection(capture);
            if (committed) {
                assert(after != before && after->items()[0].attempts == 0 && after->items()[0].safeReason == "manual_retry");
                assert(after->items()[0].acceptedBytes == before->items()[0].acceptedBytes &&
                    after->items()[1].updatedAtMs == before->items()[1].updatedAtMs);
            } else assert(after == before);
            assert(!capture.readiness().storageWritable && !capture.localQueueComplete());
            capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
            assert(networkCalls == 0);
        }
        NativeCapture cold(fixture.root, {std::make_shared<GeneratedAec>(), false});
        const bool durable = cut == IoCut::none || cut == IoCut::ambiguousRename || cut == IoCut::pauseAfterRename;
        startAndAdopt(cold, durable ? 3 : 2);
        assert(NativeCaptureStorageTestPeer::projection(cold)->items()[0].attempts == (durable ? 0U : 3U));
        cold.shutdown(); assert(waitFor([&] { return cold.shutdownWorkDrained(); }));
        std::fprintf(stderr, "PROTECTED_MANUAL_SEND cut=%u durable=%u network=0\n", static_cast<unsigned>(cut), durable ? 1U : 0U);
    }
    for (const bool unowned : {false, true}) {
        testing::GeneratedRecordingRoot paths;
        constexpr auto session = "generated-manual-send";
        std::async(std::launch::async, [&] {
            auto cancellation = std::make_shared<std::atomic<bool>>(false);
            auto opened = ProtectedCustodyStoreOwner::open(paths.root, cancellation); assert(opened.ok());
            auto store = std::move(*opened.value);
            auto created = V5LocalRecordingWriter::open(store, session, cancellation); assert(created.ok());
            auto writer = std::move(*created.value);
            CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
            for (unsigned index = 0; index != 500; ++index) { frame.ptsFrames = index * 480; assert(writer->append(frame)); }
            assert(writer->finalize(ReasonCode::none, RecordingStopReason::interruption).normalPackage()); writer.reset();
            const auto current = store->readQueueValue(cancellation); assert(current.ok());
            auto value = std::allocate_shared<ProtectedUploadQueueValue>(CustodyAllocator<ProtectedUploadQueueValue>{}, **current.value);
            ProtectedUploadQueueValue::Item row; row.localRecordingId = row.directoryId = row.sessionId = session;
            const auto directory = (paths.root / session).u8string(); row.packageDirectory.assign(directory.begin(), directory.end());
            if (!unowned) { row.ownerUserId = "11111111-1111-4111-8111-111111111111"; row.ownerWorkspaceId = "22222222-2222-4222-8222-222222222222"; }
            assert(value->enqueue(std::move(row), 1000, cancellation.get()));
            const auto bytes = value->serialize(cancellation); assert(bytes.ok());
            assert(commitProtectedCustodyMetadata(store, store->queueContext(), store->queueGeneration(), *bytes.value, cancellation).state == CustodyCommitState::committed);
        }).get();
        std::atomic<unsigned> networkCalls{0}; std::mutex mutex; std::condition_variable wake; bool released = false;
        const DesktopHttpTransport::ProtectedUploadSend wire = [&](const auto&, const auto& request) {
            assert(request.method == "GET" && request.path.find("/sync-state?") != std::string_view::npos);
            ++networkCalls; std::unique_lock<std::mutex> lock(mutex); wake.wait(lock, [&] { return released; });
            return DesktopHttpTransport::ProtectedUploadResponse{503, "{}"};
        };
        NativeCapture capture(paths.root, {std::make_shared<GeneratedAec>(), false}, accountWire, wire);
        startAndAdopt(capture, 2); capture.setAuthSessionToken("generated-manual-send");
        assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
        const auto before = NativeCaptureStorageTestPeer::projection(capture);
        if (unowned) assert(!capture.requestProtectedManualSend(before, session, capture.authGeneration(), false));
        const auto pending = capture.requestProtectedManualSend(before, session, capture.authGeneration(), unowned); assert(pending);
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
        assert(networkCalls == 0 && NativeCaptureStorageTestPeer::projection(capture) == before);
        NativeCaptureStorageTestPeer::pollStorage(capture);
        const bool called = waitFor([&] { return networkCalls.load() == 1; });
        { std::lock_guard<std::mutex> lock(mutex); released = true; wake.notify_all(); }
        assert(called);
        const auto ticket = capture.protectedManualSendTicket(pending->id);
        assert(ticket && ticket->state == NativeCapture::QueueTicketState::committed);
        const auto after = NativeCaptureStorageTestPeer::projection(capture);
        assert(after != before && !after->items()[0].ownerUserId.empty() && after->items()[0].safeReason == "manual_retry");
        assert(waitFor([&] { capture.pollUploads(); return !capture.uploadsBusy() && capture.localObservation().complete; }));
        assert(capture.protectedManualSendTicket(pending->id)->state == NativeCapture::QueueTicketState::committed);
        capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        std::fprintf(stderr, "PROTECTED_MANUAL_SEND unowned=%u durable_before_http=1 device_audio=0\n", unowned ? 1U : 0U);
    }
}

void protectedDeletionIntent() {
    for (const auto cut : {IoCut::none, IoCut::flush, IoCut::ambiguousRename,
                          IoCut::pauseAfterFlush, IoCut::pauseAfterRename}) {
        Fixture fixture; seedQueue(fixture.root);
        bool durable = cut == IoCut::none || cut == IoCut::ambiguousRename || cut == IoCut::pauseAfterRename;
        bool retiredBeforeNext = true;
        std::atomic<unsigned> calls{0};
        const DesktopHttpTransport::UploadSend wire = [&](const auto& config, const auto& request) -> DesktopHttpTransport::UploadResponse {
            ++calls;
            assert(request.method == "GET");
            const std::string workspace = config.sessionToken == "generated-other-workspace" ?
                "66666666-6666-4666-8666-666666666666" : "22222222-2222-4222-8222-222222222222";
            if (request.path == "/desktop/settings/spaces")
                return {200, "{\"spaces\":[{\"id\":\"" + workspace + "\",\"active\":true}]}"};
            assert(request.path == "/api/v1/auth/me");
            return {200, "{\"user_id\":\"11111111-1111-4111-8111-111111111111\",\"workspace_id\":\"" + workspace +
                "\",\"active_session_id\":\"33333333-3333-4333-8333-333333333333\"}"};
        };
        {
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, wire);
            startAndAdopt(capture, 2);
            assert(!capture.requestProtectedDeletion("waiting")); // No confirmed account.
            capture.setAuthSessionToken("generated-deletion-owner");
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
            const auto before = NativeCaptureStorageTestPeer::projection(capture);
            const auto original = snapshot(fixture.root);
            assert(!capture.requestProtectedDeletion("absent"));
            if (cut == IoCut::none) {
                capture.setAuthSessionToken("generated-other-workspace");
                assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
                assert(!capture.requestProtectedDeletion("waiting"));
                capture.setAuthSessionToken("generated-deletion-owner");
                assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
                CustodyAllocator<char> allocator;
                const auto count = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
                auto* reservation = allocator.allocate(count);
                assert(!capture.requestProtectedDeletion("waiting"));
                allocator.deallocate(reservation, count);
                assert(NativeCaptureStorageTestPeer::projection(capture) == before && snapshot(fixture.root) == original);
                assert(capture.openLocalPlayback("waiting", 1, true)); // Positive admission control, no device output.
                capture.closeLocalPlayback();
                assert(waitFor([&] { return capture.localPlaybackObservation().terminal; }));
            }
            { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
            ioCut.store(cut);
            const auto pending = capture.requestProtectedDeletion("waiting");
            assert(pending && pending->kind == NativeCapture::QueueMutationKind::deletionIntent &&
                pending->state == NativeCapture::QueueTicketState::pending && !pending->changed);
            assert(!capture.requestProtectedDeletion("waiting")); // Exactly one in-flight candidate.
            const bool paused = cut == IoCut::pauseAfterFlush || cut == IoCut::pauseAfterRename;
            if (paused) {
                assert(waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }));
                capture.setAuthSessionToken({}); // Cancel before/after actual publication, not a fabricated epoch.
                { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; cutWake.notify_all(); }
            }
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            ioCut.store(IoCut::none);
            assert(NativeCaptureStorageTestPeer::projection(capture) == before);
            assert(NativeCaptureStorageTestPeer::generation(capture) == 2 && !capture.updateWorkDrained());
#if defined(_MSC_VER) && defined(_DEBUG)
            if (cut == IoCut::none) deletionRetirementThread.store(NativeCaptureStorageTestPeer::storageThread(capture));
#endif
            NativeCaptureStorageTestPeer::pollStorage(capture);
            const auto result = NativeCaptureStorageTestPeer::ticket(capture); assert(result);
            assert(result->id == pending->id && result->kind == NativeCapture::QueueMutationKind::deletionIntent);
            const bool committed = cut == IoCut::none || cut == IoCut::pauseAfterRename;
            assert(result->state == (committed ? NativeCapture::QueueTicketState::committed :
                cut == IoCut::ambiguousRename ? NativeCapture::QueueTicketState::ambiguous : NativeCapture::QueueTicketState::notCommitted));
            const auto after = NativeCaptureStorageTestPeer::projection(capture);
            if (committed) {
                assert(after != before && before->deletionOperations().size() == 1 && after->deletionOperations().size() == 2);
                const auto& operation = after->deletionOperations().back();
                assert(operation.phase == DeletionOperationPhase::queued && operation.target == DeletionTarget::ownOrigin &&
                    operation.targetId == "waiting" && operation.attemptCount == 0 && operation.receiptRequestId.empty());
                assert(after->deletionBlocks(after->items()[0]) && !after->deletionBlocks(after->items()[1]));
                assert(!capture.openLocalPlayback("waiting", 1, true));
                if (cut == IoCut::none) {
                    const auto once = snapshot(fixture.root);
#if defined(_MSC_VER) && defined(_DEBUG)
                    assert(waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }));
                    retiredBeforeNext = NativeCaptureStorageTestPeer::deletionSlotRetired(capture);
                    const auto duplicate = retiredBeforeNext ? capture.requestProtectedDeletion("waiting") : std::nullopt;
                    { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; cutWake.notify_all(); }
#else
                    assert(waitFor([&] { return capture.updateWorkDrained(); }));
                    const auto duplicate = capture.requestProtectedDeletion("waiting");
#endif
                    if (retiredBeforeNext) {
                    assert(duplicate);
                    assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
                    NativeCaptureStorageTestPeer::pollStorage(capture);
                    const auto repeated = NativeCaptureStorageTestPeer::ticket(capture); assert(repeated);
                    assert(repeated->state == NativeCapture::QueueTicketState::committed && !repeated->changed &&
                        repeated->targetGeneration == 3 && snapshot(fixture.root) == once);
                    assert(NativeCaptureStorageTestPeer::projection(capture)->deletionOperations().size() == 2);
                    assert(waitFor([&] { return capture.updateWorkDrained(); }));
                    assert(capture.currentAccount() && capture.localObservation().complete && !capture.openLocalPlayback("waiting", 1, true));
                    }
                } else assert(!capture.currentAccount() && result->epoch != capture.authGeneration());
            } else assert(after == before);
            // Unpublished queue tails/slots may change on failed publication.
            // Authority is checked by cold reopen below, not whole-tree equality.
            for (const auto& [path, hash] : original) assert(std::filesystem::is_regular_file(fixture.root / path));
            assert(calls == (cut == IoCut::none ? 6U : 2U) && !capture.localQueueComplete() && !capture.readiness().storageWritable);
            capture.shutdown();
            assert(waitFor([&] { return capture.shutdownWorkDrained(); }));
        }
        std::fprintf(stderr, "PROTECTED_DELETION_RETIREMENT retired_before_next=%u\n", retiredBeforeNext ? 1U : 0U);
        assert(retiredBeforeNext && "deletion_command_state_must_retire_before_new_admission");
        NativeCapture restarted(fixture.root, {std::make_shared<GeneratedAec>(), false});
        startAndAdopt(restarted, durable ? 3 : 2);
        const auto restored = NativeCaptureStorageTestPeer::projection(restarted);
        assert(restored->deletionOperations().size() == (durable ? 2 : 1));
        assert(restored->deletionBlocks(restored->items()[0]) == durable);
        restarted.shutdown();
        assert(waitFor([&] { return restarted.shutdownWorkDrained(); }));
        std::fprintf(stderr, "PROTECTED_DELETION_INTENT cut=%u durable=%u network_delete=0 physical_delete=0\n",
            static_cast<unsigned>(cut), durable ? 1U : 0U);
    }
}
void protectedDeletionApplication() {
    const DesktopHttpTransport::UploadSend account = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(request.method == "GET");
        if (request.path == "/desktop/settings/spaces")
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        assert(request.path == "/api/v1/auth/me");
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    };
    for (unsigned mode = 0; mode != 18; ++mode) {
    Fixture fixture; seedQueue(fixture.root, mode == 11);
    std::atomic<unsigned> gets{0}, posts{0};
    std::atomic<bool> exitHeld{false}, exitReleased{false};
    std::atomic<bool> forceRelease{false}, forcedTimeout{false};
    bool reconciliationHeld = true;
    const DesktopHttpTransport::ProtectedUploadSend wire = [&](const auto& config, const auto& request) {
        DesktopHttpTransport::ProtectedUploadResponse response; response.status = 200;
        if (request.method == "GET") {
            ++gets;
            assert(request.path == DesktopApiClient::notificationContextPath);
            response.body = R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","recording_deletion_protocol_version":1})";
            if (mode == 9) { response.status = 429; response.retryAfter = "67"; }
        } else {
            assert(request.method == "POST"); ++posts;
            if (mode == 13) while (!config.cancellation->load() && !forceRelease.load()) Sleep(1);
            if (mode == 12 && posts == 1) {
                struct ExitCut {
                    std::atomic<bool>* held = nullptr;
                    std::atomic<bool>* released = nullptr;
                    ~ExitCut() { if (held) { held->store(true); while (!released->load()) Sleep(1); } }
                };
                thread_local ExitCut cut;
                cut.held = &exitHeld; cut.released = &exitReleased;
            }
            const auto target = request.path == DesktopApiClient::ownOriginDeletionPath<CustodyString>("waiting") ? "waiting" : "retained";
            response.body = R"({"receipt_type":"origin_cancellation","request_id":"77777777-7777-4777-8777-777777777777","local_recording_id":")";
            response.body += target; response.body += R"(","phase":"accepted"})";
            if (mode == 10) { response.status = 503; response.transportFailed = true; response.body.clear(); }
        }
        return response;
    };
    auto owned = std::make_unique<NativeCapture>(fixture.root, AecSelection{std::make_shared<GeneratedAec>(), false}, account, wire);
    auto& capture = *owned;
    startAndAdopt(capture, 2); capture.setAuthSessionToken("generated-deletion-application");
    assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
    if (mode == 0) {
        const auto before = snapshot(fixture.root);
        ProtectedDeletionTargets targets{{DeletionTarget::ownOrigin, "waiting"}};
        CustodyAllocator<char> allocator;
        const auto count = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
        auto* reserved = allocator.allocate(count);
        assert(!capture.beginProtectedDeletionSelection(std::move(targets)));
        allocator.deallocate(reserved, count);
        assert(snapshot(fixture.root) == before && gets == 0 && posts == 0);
    }
    if (mode == 16) ioCut.store(IoCut::flush);
    if (mode == 17) ioCut.store(IoCut::ambiguousRename);
    const auto ticket = capture.beginProtectedDeletionSelection(mode == 11 ?
        ProtectedDeletionTargets{{DeletionTarget::ownOrigin, "local-only-dir"}} :
        ProtectedDeletionTargets{{DeletionTarget::ownOrigin, "waiting"}, {DeletionTarget::ownOrigin, "retained"}});
    assert(ticket);
    assert(!capture.beginProtectedDeletionSelection({{DeletionTarget::ownOrigin, "waiting"}}));
    if (mode >= 16) {
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
        ioCut.store(IoCut::none);
        if (mode == 17) denyDeletionReadback.store(true);
        capture.shutdown(); capture.pollUploads();
        if (mode == 17) {
            const bool held = waitFor([&] { return NativeCaptureStorageTestPeer::deletionReconciliationPending(capture); });
            const bool suspended = !capture.takeProtectedDeletionCompletion(ticket->id) && !capture.updateWorkDrained();
            denyDeletionReadback.store(false); capture.recover(RecoveryTrigger::scheduled);
            assert(held && suspended);
        }
    }
    if (mode == 1) capture.shutdown(); // Native must defer full stop, independently of AppMain's observer.
    if (mode == 2) capture.setUpdateAdmissionBlocked(true);
    if (mode == 12) {
        std::thread release([&] {
            const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
            while (!exitReleased.load() && std::chrono::steady_clock::now() < deadline) Sleep(1);
            if (!exitReleased.exchange(true)) forcedTimeout.store(true);
        });
        const bool held = waitFor([&] { capture.pollUploads(); return exitHeld.load(); });
        capture.pollUploads();
        const bool premature = NativeCaptureStorageTestPeer::deletionResponseRetained(capture) || capture.updateWorkDrained();
        exitReleased.store(true); release.join();
        assert(held && !premature && !forcedTimeout.load() && posts == 1);
    }
    if (mode == 13) assert(waitFor([&] { capture.pollUploads(); return posts == 1; }));
    if (mode != 1 && mode != 2 && mode != 11 && mode != 13 && mode < 16) {
        assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::deletionResponseRetained(capture); }));
        assert(gets == 1 && posts == (mode == 9 ? 0U : 1U));
        if (mode == 3) capture.setAuthSessionToken({});
        if (mode == 4) capture.shutdown();
        if (mode == 5) capture.setUpdateAdmissionBlocked(true);
        if (mode == 6) ioCut.store(IoCut::flush);
        if (mode == 7 || mode == 15) ioCut.store(IoCut::ambiguousRename);
        if (mode == 8) {
            CustodyAllocator<char> allocator;
            const auto count = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
            auto* reserved = allocator.allocate(count);
            capture.pollUploads();
            assert(NativeCaptureStorageTestPeer::deletionResponseRetained(capture) && posts == 1);
            allocator.deallocate(reserved, count);
        }
        if (mode == 0) {
            { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
            ioCut.store(IoCut::pauseAfterRename);
            capture.pollUploads();
            const bool cut = waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; });
            const bool suspended = posts == 1 && !capture.takeProtectedDeletionCompletion(ticket->id);
            { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; cutWake.notify_all(); }
            assert(cut && suspended);
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            assert(posts == 1 && NativeCaptureStorageTestPeer::projection(capture)->deletionOperations().back().phase == DeletionOperationPhase::queued);
            ioCut.store(IoCut::none);
            NativeCaptureStorageTestPeer::pollStorage(capture); // Actual adoption, not a simulated acknowledgement.
        } else if (mode == 6 || mode == 7 || mode == 15) {
            capture.pollUploads();
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            ioCut.store(IoCut::none);
            if (mode == 7 || mode == 15) denyDeletionReadback.store(true);
            capture.pollUploads();
            if (mode == 7 || mode == 15) {
                reconciliationHeld = waitFor([&] { return NativeCaptureStorageTestPeer::deletionReconciliationPending(capture); }) &&
                    posts == 1 && !capture.updateWorkDrained() && !capture.takeProtectedDeletionCompletion(ticket->id);
                if (mode == 7) {
                    denyDeletionReadback.store(false); capture.recover(RecoveryTrigger::scheduled);
                    assert(reconciliationHeld);
                }
            }
        }
    }
    if (mode >= 13 && mode <= 15) {
        const auto work = NativeCaptureStorageTestPeer::storageWork(capture);
        winrt::handle storageExited(OpenThread(SYNCHRONIZE, FALSE, NativeCaptureStorageTestPeer::storageThread(capture)));
        assert(storageExited);
        std::thread release([&] {
            const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
            while (!forceRelease.load() && std::chrono::steady_clock::now() < deadline) Sleep(1);
            if (!forceRelease.exchange(true)) {
                forcedTimeout.store(true);
                if (mode == 15) {
                    denyDeletionReadback.store(false);
                    std::lock_guard<std::mutex> lock(work->mutex);
                    work->reconcileRequested = true; work->wake.notify_all();
                }
            }
        });
        owned.reset(); // No UI poll, no destructor reconciliation loop; network join is still mandatory.
        forceRelease.store(true); release.join();
        if (mode == 15) {
            // The destructor returned while genuine reconciliation still failed.
            // Only now release the IO cut and wake the retained storage owner.
            denyDeletionReadback.store(false);
            std::lock_guard<std::mutex> lock(work->mutex);
            work->reconcileRequested = true; work->wake.notify_all();
        }
        assert(!forcedTimeout.load() && reconciliationHeld);
        assert(waitFor([&] { return WaitForSingleObject(storageExited.get(), 0) == WAIT_OBJECT_0; }));
        assert(posts == 1);
        NativeCapture restarted(fixture.root, {std::make_shared<GeneratedAec>(), false});
        startAndAdopt(restarted, mode == 15 ? 4 : 3);
        const auto restored = NativeCaptureStorageTestPeer::projection(restarted);
        unsigned accepted = 0;
        for (const auto& operation : restored->deletionOperations()) if (deletionPhaseIsAccepted(operation.phase)) ++accepted;
        assert(accepted == (mode == 15 ? 1U : 0U));
        restarted.shutdown(); assert(waitFor([&] { return restarted.shutdownWorkDrained(); }));
        std::fprintf(stderr, "PROTECTED_DELETION_APPLICATION forced_destroy=%u retained_intent=1 posts=1 cold_accepted=%u\n", mode, accepted);
        continue;
    }
    std::optional<NativeCapture::DeletionCompletion> result;
    const bool completed = waitFor([&] {
        capture.pollUploads(); result = capture.takeProtectedDeletionCompletion(ticket->id); return result.has_value();
    });
    assert(completed && "deletion_application_must_run_http_persist_ack");
    assert(result->saved == (mode < 16) && !result->rejected && result->unknown == (mode == 7 || mode == 17));
    const unsigned accepted = mode == 0 || mode == 8 || mode == 12 ? 2 : mode == 4 || mode == 5 || mode == 7 ? 1 : 0;
    // The old domain fixture deliberately mismatches directoryId/path. Never
    // relax physical confinement just to remove that local-only row (mode 11).
    if (mode != 3) assert(result->accepted == accepted && result->pending == (mode >= 16 ? 0 : mode == 11 ? 1 : 2 - accepted));
    assert(gets == (mode == 1 || mode == 2 || mode == 11 || mode >= 16 ? 0U : 1U));
    assert(posts == (mode == 1 || mode == 2 || mode == 9 || mode == 11 || mode >= 16 ? 0U : mode == 0 || mode == 8 || mode == 12 ? 2U : 1U));
    assert(!capture.takeProtectedDeletionCompletion(ticket->id));
    assert(!capture.localQueueComplete() && !capture.readiness().storageWritable);
    capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
    std::fprintf(stderr, "PROTECTED_DELETION_APPLICATION mode=%u accepted=%zu pending=%zu unknown=%u posts=%u audio=0 real_network=0\n",
        mode, result->accepted, result->pending, result->unknown ? 1U : 0U, posts.load());
    }
}
void protectedDeletionContinuation() {
    const DesktopHttpTransport::UploadSend wire = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(request.method == "GET");
        if (request.path == "/desktop/settings/spaces")
            return {200, "{\"spaces\":[{\"id\":\"22222222-2222-4222-8222-222222222222\",\"active\":true}]}"};
        assert(request.path == "/api/v1/auth/me");
        return {200, "{\"user_id\":\"11111111-1111-4111-8111-111111111111\","
            "\"workspace_id\":\"22222222-2222-4222-8222-222222222222\","
            "\"active_session_id\":\"33333333-3333-4333-8333-333333333333\"}"};
    };
    for (unsigned mode = 0; mode != 6; ++mode) {
        Fixture fixture; seedQueue(fixture.root);
        NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, wire);
        startAndAdopt(capture, 2); capture.setAuthSessionToken("generated-continuation-owner");
        assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
        const auto pending = capture.requestProtectedDeletionSelection({{DeletionTarget::ownOrigin, "waiting"}}, true);
        assert(pending && capture.protectedDeletionCancellation(pending->id));
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
        NativeCaptureStorageTestPeer::pollStorage(capture);
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::deletionSlotRetired(capture); }));
        const auto result = capture.protectedDeletionTicket(pending->id);
        assert(result && result->state == NativeCapture::QueueTicketState::committed);
        assert(!capture.updateWorkDrained() && "deletion_continuation_must_survive_intent_ack");
        const auto plan = capture.protectedDeletionPlan(pending->id); assert(plan && plan->requests.size() == 1);
        const auto before = NativeCaptureStorageTestPeer::projection(capture);
        assert(!capture.requestProtectedDeletionSelection({{DeletionTarget::ownOrigin, "retained"}}, true));
        BasicDeletionWireResult<CustodyString> answer;
        answer.status = 200;
        answer.body = "{\"receipt_type\":\"origin_cancellation\",\"request_id\":\"77777777-7777-4777-8777-777777777777\","
            "\"local_recording_id\":\"waiting\",\"phase\":\"accepted\"}";
        if (mode == 1) capture.requestShutdown();
        if (mode == 2) capture.setUpdateAdmissionBlocked(true);
        if (mode == 3) capture.setAuthSessionToken({});
        if (mode == 4) ioCut.store(IoCut::ambiguousRename);
        if (mode == 5) ioCut.store(IoCut::flush);
        const auto submitted = capture.applyProtectedDeletionAnswer(before, pending->epoch,
            plan->requests.front().operationId, std::move(answer), pending->id);
        if (mode == 3) {
            assert(!submitted && NativeCaptureStorageTestPeer::projection(capture) == before);
        } else {
            assert(submitted && !capture.endProtectedDeletionContinuation(pending->id));
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            ioCut.store(IoCut::none);
            if (mode == 4) denyDeletionReadback.store(true);
            NativeCaptureStorageTestPeer::pollStorage(capture);
            if (mode == 4) {
                assert(waitFor([&] { return NativeCaptureStorageTestPeer::deletionReconciliationPending(capture); }));
                assert(!capture.endProtectedDeletionContinuation(pending->id) && NativeCaptureStorageTestPeer::projection(capture) == before);
                denyDeletionReadback.store(false);
                capture.recover(RecoveryTrigger::scheduled);
                assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
                assert(!capture.endProtectedDeletionContinuation(pending->id)); // Physical value still awaits adoption.
                NativeCaptureStorageTestPeer::pollStorage(capture);
            }
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::deletionSlotRetired(capture); }));
            if (mode == 5) {
                assert(capture.protectedDeletionTicket(submitted->id)->state == NativeCapture::QueueTicketState::notCommitted);
                assert(NativeCaptureStorageTestPeer::projection(capture) == before);
            } else assert(NativeCaptureStorageTestPeer::projection(capture)->deletionOperations().back().phase == DeletionOperationPhase::accepted);
        }
        assert(capture.endProtectedDeletionContinuation(pending->id));
        assert(!capture.endProtectedDeletionContinuation(pending->id));
        if (mode == 0) {
            const auto next = capture.requestProtectedDeletionSelection({{DeletionTarget::ownOrigin, "retained"}}, true);
            assert(next && next->id != pending->id && !capture.endProtectedDeletionContinuation(pending->id));
            assert(capture.protectedDeletionCancellation(next->id) && !capture.updateWorkDrained());
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            NativeCaptureStorageTestPeer::pollStorage(capture);
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::deletionSlotRetired(capture); }));
            assert(capture.endProtectedDeletionContinuation(next->id));
        }
        capture.shutdown(); assert(waitFor([&] { return capture.shutdownWorkDrained(); }));
        std::fprintf(stderr, "PROTECTED_DELETION_CONTINUATION mode=%u answer_ack=%u audio=0 network_delete=0\n", mode, mode != 3);
    }
}
void protectedLocalPurge(bool userRemoval = false) {
    // Only generated encrypted fixtures; never a device, user recording or server.
    const DesktopHttpTransport::UploadSend account = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(request.method == "GET");
        if (request.path == "/desktop/settings/spaces")
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        assert(request.path == "/api/v1/auth/me");
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    };
    for (unsigned mode = 0; mode != 9; ++mode) {
        testing::GeneratedRecordingRoot fixture;
        std::uint64_t persistedGeneration = 0;
        constexpr auto name = "generated-local-purge";
        const auto path = fixture.root / name;
        std::async(std::launch::async, [&] {
            auto cancel = std::make_shared<std::atomic<bool>>(false);
            auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(opened.ok());
            auto owner = std::move(*opened.value);
            if (mode != 1) {
                auto created = V5LocalRecordingWriter::open(owner, name, cancel); assert(created.ok());
                CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
                for (unsigned i = 0; i != 500; ++i) { frame.ptsFrames = i * 480; assert((*created.value)->append(frame)); }
                assert((*created.value)->finalize().normalPackage());
            }
            auto current = owner->readQueueValue(cancel); assert(current.ok());
            auto copy = std::allocate_shared<ProtectedUploadQueueValue>(CustodyAllocator<ProtectedUploadQueueValue>{}, **current.value);
            ProtectedUploadQueueValue::Item row;
            row.localRecordingId = row.directoryId = row.sessionId = name;
            const auto directory = path.u8string(); row.packageDirectory.assign(directory.begin(), directory.end());
            row.ownerUserId = "11111111-1111-4111-8111-111111111111";
            row.ownerWorkspaceId = "22222222-2222-4222-8222-222222222222";
            assert(copy->enqueue(row, 1000, cancel.get()));
            if (userRemoval) {
                BasicDesktopTransportResult<CustodyString> classified;
                classified.status = mode % 2 ? DesktopTransportStatus::retryableFailure : DesktopTransportStatus::uploaded;
                classified.serverTruth.emplace(); classified.serverTruth->localRecordingId = row.localRecordingId;
                classified.serverTruth->meetingId = "88888888-8888-4888-8888-888888888888";
                classified.serverTruth->meetingExists = true; classified.serverTruth->acceptedBytes = {11,22,33};
                assert(copy->applyUploadResult(row, classified, 1500, cancel.get()));
            }
            if (mode == 7) {
                row.localRecordingId = row.directoryId = row.sessionId = "generated-alias";
                const auto alias = (fixture.root / "GENERATED-LOCAL-PURGE").u8string();
                row.packageDirectory.assign(alias.begin(), alias.end());
                assert(copy->enqueue(std::move(row), 1001, cancel.get()));
            }
            if (mode == 6) {
                ProtectedDeletionPlan plan; bool changed = false;
                if (userRemoval) assert(copy->planLocalRemoval(0, row.ownerUserId, row.ownerWorkspaceId, 2000, plan, changed, cancel.get()) && changed);
                else assert(copy->planDeletionSelection({{DeletionTarget::ownOrigin, name}},
                    row.ownerUserId, row.ownerWorkspaceId, "https://rec.2brain.pro", 2000, plan, changed, cancel.get()) && changed);
                assert(plan.requests.empty() && plan.operationIds.empty() && plan.localOnly.size() == 1);
            }
            auto bytes = copy->serialize(cancel); assert(bytes.ok());
            assert(commitProtectedCustodyMetadata(owner, owner->queueContext(), owner->queueGeneration(), *bytes.value, cancel).state == CustodyCommitState::committed);
            if (userRemoval && mode == 6) {
                const auto disk = snapshot(fixture.root);
                const auto currentIntent = owner->readQueueValue(cancel); assert(currentIntent.ok());
                const auto intentBytes = (*currentIntent.value)->serialize(cancel); assert(intentBytes.ok());
                for (unsigned wrongScope = 0; wrongScope != 6; ++wrongScope) {
                    auto candidate = **currentIntent.value;
                    std::string_view user = row.ownerUserId, workspace = row.ownerWorkspaceId;
                    if (wrongScope == 0 || wrongScope == 1) user = {};
                    if (wrongScope == 0 || wrongScope == 2) workspace = {};
                    if (wrongScope == 3) user = "99999999-9999-4999-8999-999999999999";
                    if (wrongScope == 4) workspace = "99999999-9999-4999-8999-999999999999";
                    if (wrongScope == 5) user = "invalid";
                    const auto refused = owner->purgeLocalPackage(name, owner->queueGeneration(), candidate, 3000, cancel, nullptr, user, workspace);
                    assert(refused.ok() && !*refused.value && snapshot(fixture.root) == disk);
                    const auto unchanged = candidate.serialize(cancel); assert(unchanged.ok() && *unchanged.value == *intentBytes.value);
                }
            }
        }).get();
        if (mode == 0) {
            const auto before = snapshot(fixture.root);
            winrt::handle wrong(CreateFileW(fixture.root.c_str(), FILE_READ_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_DELETE,
                nullptr, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
            assert(wrong && !DesktopLocalPurgeService::recycle(path, 0, reinterpret_cast<std::uintptr_t>(wrong.get())));
            assert(snapshot(fixture.root) == before && "wrong_source_identity_must_abort_before_recycle");
        }
        {
            winrt::handle held;
            if (mode == 8) {
                // Attribute-only handles do not acquire delete-sharing
                // exclusion. Hold the real directory reader used by Files.
                held.attach(CreateFileW(path.c_str(), FILE_READ_ATTRIBUTES | FILE_LIST_DIRECTORY, FILE_SHARE_READ, nullptr, OPEN_EXISTING,
                    FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
                assert(held);
            }
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, account,
                [](const auto&, const auto&) -> DesktopHttpTransport::ProtectedUploadResponse {
                    assert(false && "local_only_purge_must_not_issue_http"); return {};
                });
            startAndAdopt(capture, 2);
            capture.setAuthSessionToken("generated-local-purge-owner");
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
            if (mode == 6) {
                assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::projection(capture)->items().empty(); }));
            } else {
                const auto releaseCut = [] {
                    pauseOldPackedRead.store(false);
                    { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
                    cutWake.notify_all();
                };
                if (mode == 5) {
                    oldPackedPath = L"\\\\?\\" + (path / L".custody-v1" / L"canonical" / L"content.packed-v2").native();
                    { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
                    pauseOldPackedRead.store(true);
                    const bool paused = waitFor([&] {
                        NativeCaptureStorageTestPeer::pollStorage(capture);
                        std::lock_guard<std::mutex> lock(cutMutex); return cutReached;
                    });
                    if (!paused) releaseCut();
                    assert(paused);
                }
                const auto before = NativeCaptureStorageTestPeer::projection(capture);
                if (userRemoval) {
                    assert(!capture.requestProtectedLocalRemoval({}, name, capture.authGeneration()));
                    assert(!capture.requestProtectedLocalRemoval(before, name, capture.authGeneration() + 1));
                    assert(!capture.requestProtectedLocalRemoval(before, name, capture.authGeneration(), true));
                }
                const auto ticket = userRemoval ? capture.requestProtectedLocalRemoval(before, name, capture.authGeneration()) :
                    capture.beginProtectedDeletionSelection({{DeletionTarget::ownOrigin, name}});
                if (!ticket && mode == 5) releaseCut();
                assert(ticket);
                const bool ready = waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); });
                if (!ready && mode == 5) releaseCut();
                assert(ready);
                NativeCaptureStorageTestPeer::pollStorage(capture); // Durable intent adopted, not removed.
                if (userRemoval) {
                    const auto value = NativeCaptureStorageTestPeer::projection(capture);
                    assert(value->items()[0].status == UploadQueueStatus::quarantined && value->items()[0].safeReason == "local_delete_pending");
                    assert(value->items()[0].meetingId == before->items()[0].meetingId &&
                        value->items()[0].acceptedBytes == before->items()[0].acceptedBytes &&
                        value->deletionOperations().empty() && value->purgeAcknowledgements().empty());
                    assert(!capture.requestProtectedLocalRemoval(before, name, capture.authGeneration()));
                }
                const bool retired = waitFor([&] { return NativeCaptureStorageTestPeer::deletionSlotRetired(capture); });
                if (!retired && mode == 5) releaseCut();
                assert(retired);
                if (mode == 4) capture.setAuthSessionToken({});
                if (mode == 2) ioCut.store(IoCut::flush);
                if (mode == 3) ioCut.store(IoCut::ambiguousRename);
                if (mode == 5) {
                    bool premature = false;
                    const auto until = std::chrono::steady_clock::now() + std::chrono::milliseconds(100);
                    while (std::chrono::steady_clock::now() < until) {
                        capture.pollUploads(); premature = premature || capture.takeProtectedDeletionCompletion(ticket->id).has_value() || !std::filesystem::exists(path);
                        Sleep(1);
                    }
                    releaseCut();
                    assert(!premature && "purge_must_wait_for_actual_display_reader_exit");
                }
                std::optional<NativeCapture::DeletionCompletion> result;
                assert(waitFor([&] {
                    capture.pollUploads();
                    if (mode == 2 || mode == 3) {
                        if (NativeCaptureStorageTestPeer::resultReady(capture)) ioCut.store(IoCut::none);
                    }
                    result = capture.takeProtectedDeletionCompletion(ticket->id); return result.has_value();
                }));
                ioCut.store(IoCut::none);
                const bool removed = mode != 2 && mode != 4 && mode != 7 && mode != 8;
                if (mode != 4) assert(result->accepted == (removed ? 1U : 0U) && result->pending == (removed ? 0U : 1U));
                assert(result->unknown == (mode == 3));
                assert(std::filesystem::exists(path) == (mode == 4 || mode == 7 || mode == 8));
                if (mode == 8) {
                    const auto generation = NativeCaptureStorageTestPeer::generation(capture);
                    held.close();
                    capture.recover(RecoveryTrigger::scheduled);
                    assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::projection(capture)->items().empty(); }));
                    assert(!std::filesystem::exists(path) && NativeCaptureStorageTestPeer::generation(capture) == generation + 1);
                }
            }
            assert(!capture.localQueueComplete() && !capture.readiness().storageWritable);
            capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
            persistedGeneration = NativeCaptureStorageTestPeer::generation(capture);
        }
        oldPackedPath.clear();
        {
            NativeCapture restarted(fixture.root, {std::make_shared<GeneratedAec>(), false}, account);
            startAndAdopt(restarted, persistedGeneration);
            assert(NativeCaptureStorageTestPeer::projection(restarted)->items().size() == (mode == 2 || mode == 4 ? 1U : mode == 7 ? 2U : 0U));
            if (mode == 2) {
                restarted.setAuthSessionToken("generated-local-purge-restart");
                assert(waitFor([&] { restarted.pollUploads(); return NativeCaptureStorageTestPeer::projection(restarted)->items().empty(); }));
            }
            restarted.shutdown(); assert(waitFor([&] { restarted.pollUploads(); return restarted.shutdownWorkDrained(); }));
        }
        std::fprintf(stderr, "%s mode=%u actual_recycle=%u cold_queue=1 audio=0 real_network=0\n",
            userRemoval ? "PROTECTED_LOCAL_REMOVAL" : "PROTECTED_LOCAL_PURGE", mode, mode != 1 && mode != 4 && mode != 7);
    }
}
void protectedServerPurge() {
    // Generated encrypted fixtures and classified upload-result data, not a
    // real server receipt, device capture or public acceptance.
    const DesktopHttpTransport::UploadSend account = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        if (request.path == "/desktop/settings/spaces")
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        assert(request.path == "/api/v1/auth/me");
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    };
    for (unsigned mode = 0; mode != 7; ++mode) {
        testing::GeneratedRecordingRoot fixture;
        BasicLocalPurgeTask<CustodyString> task;
        task.taskId = "77777777-7777-4777-8777-777777777777";
        task.meetingId = "88888888-8888-4888-8888-888888888888"; task.taskType = "purge_local_buffers";
        const bool two = mode >= 1 && mode <= 3;
        const auto first = fixture.root / "generated-server-purge-0";
        const auto second = fixture.root / "generated-server-purge-1";
        std::async(std::launch::async, [&] {
            auto cancel = std::make_shared<std::atomic<bool>>(false);
            auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(opened.ok());
            auto owner = std::move(*opened.value);
            auto current = owner->readQueueValue(cancel); assert(current.ok());
            auto copy = std::allocate_shared<ProtectedUploadQueueValue>(CustodyAllocator<ProtectedUploadQueueValue>{}, **current.value);
            for (unsigned i = 0; i != (two ? 2U : 1U); ++i) {
                const auto name = i ? "generated-server-purge-1" : "generated-server-purge-0";
                auto created = V5LocalRecordingWriter::open(owner, name, cancel); assert(created.ok());
                CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
                for (unsigned j = 0; j != 500; ++j) { frame.ptsFrames = j * 480; assert((*created.value)->append(frame)); }
                assert((*created.value)->finalize().normalPackage());
                ProtectedUploadQueueValue::Item row;
                row.localRecordingId = row.directoryId = row.sessionId = name;
                const auto path = (fixture.root / name).u8string(); row.packageDirectory.assign(path.begin(), path.end());
                row.ownerUserId = i && mode == 3 ? "99999999-9999-4999-8999-999999999999" : "11111111-1111-4111-8111-111111111111";
                row.ownerWorkspaceId = "22222222-2222-4222-8222-222222222222";
                assert(copy->enqueue(row, 1000, cancel.get()));
                BasicDesktopTransportResult<CustodyString> classified;
                classified.status = i && mode == 2 ? DesktopTransportStatus::retryableFailure : DesktopTransportStatus::uploaded;
                classified.serverTruth.emplace(); classified.serverTruth->localRecordingId = row.localRecordingId;
                classified.serverTruth->meetingId = task.meetingId;
                classified.serverTruth->meetingExists = true;
                assert(copy->applyUploadResult(row, classified, 2000, cancel.get()));
            }
            auto bytes = copy->serialize(cancel); assert(bytes.ok());
            assert(commitProtectedCustodyMetadata(owner, owner->queueContext(), owner->queueGeneration(), *bytes.value, cancel).state == CustodyCommitState::committed);
        }).get();
        std::uint64_t generation = 0;
        {
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, account);
            startAndAdopt(capture, 2); capture.setAuthSessionToken("generated-server-purge-owner");
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
            using Phase = NativeCapture::LocalPurgePhase;
            const auto snapshot = NativeCaptureStorageTestPeer::projection(capture);
            const auto epoch = capture.authGeneration();
            assert(snapshot->items()[0].meetingId == task.meetingId);
            assert(!capture.requestProtectedLocalPurge(task, snapshot, epoch, Phase::purge, "generated-server-purge-0"));
            assert(!capture.requestProtectedLocalPurge(task, snapshot, epoch + 1, Phase::intent));
            auto invalid = task; invalid.taskType = "purge_local_exports";
            assert(!capture.requestProtectedLocalPurge(invalid, snapshot, epoch, Phase::intent));
            const auto intent = capture.requestProtectedLocalPurge(task, snapshot, epoch, Phase::intent, {}, 0, true); assert(intent);
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            assert(std::filesystem::exists(first) && !snapshot->localPurgeAcknowledged(task));
            assert(!capture.requestProtectedLocalPurge(task, snapshot, epoch, Phase::purge, "generated-server-purge-0", intent->id));
            NativeCaptureStorageTestPeer::pollStorage(capture);
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::deletionSlotRetired(capture); }));
            assert(!capture.requestProtectedLocalPurge(task, snapshot, epoch, Phase::purge, "generated-server-purge-0", intent->id));
            auto adopted = NativeCaptureStorageTestPeer::projection(capture);
            assert(adopted->items()[0].safeReason == "local_delete_pending");
            if (mode == 6) {
                capture.setAuthSessionToken({});
                assert(!capture.requestProtectedLocalPurge(task, adopted, epoch, Phase::purge, "generated-server-purge-0", intent->id));
                assert(capture.endProtectedDeletionContinuation(intent->id));
            } else {
                winrt::handle held;
                if (mode == 1) {
                    held.attach(CreateFileW(second.c_str(), FILE_READ_ATTRIBUTES | FILE_LIST_DIRECTORY, FILE_SHARE_READ, nullptr,
                        OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr)); assert(held);
                }
                const auto run = [&](std::string_view id) {
                    const auto expected = NativeCaptureStorageTestPeer::projection(capture);
                    std::optional<NativeCapture::QueueMutationTicket> ticket;
                    assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture);
                        ticket = capture.requestProtectedLocalPurge(task, expected, epoch, Phase::purge, id, intent->id); return ticket.has_value(); }));
                    assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
                    ioCut.store(IoCut::none);
                    NativeCaptureStorageTestPeer::pollStorage(capture);
                    assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture); return NativeCaptureStorageTestPeer::deletionSlotRetired(capture); }));
                    return capture.protectedDeletionTicket(ticket->id);
                };
                if (mode == 4) ioCut.store(IoCut::flush);
                if (mode == 5) ioCut.store(IoCut::ambiguousRename);
                const auto removed = run("generated-server-purge-0"); assert(removed);
                assert(!std::filesystem::exists(first));
                adopted = NativeCaptureStorageTestPeer::projection(capture);
                assert(adopted->localPurgeAcknowledged(task) == (mode == 0 || mode == 5));
                if (two) {
                    assert(!adopted->localPurgeAcknowledged(task) && std::filesystem::exists(second));
                    if (mode == 1) {
                        const auto busy = run("generated-server-purge-1"); assert(busy && !busy->changed);
                        assert(!NativeCaptureStorageTestPeer::projection(capture)->localPurgeAcknowledged(task));
                        held.close();
                        assert(run("generated-server-purge-1"));
                        assert(NativeCaptureStorageTestPeer::projection(capture)->localPurgeAcknowledged(task));
                    } else assert(!capture.requestProtectedLocalPurge(task, adopted, epoch, Phase::purge, "generated-server-purge-1", intent->id));
                }
                assert(capture.endProtectedDeletionContinuation(intent->id));
            }
            assert(!capture.localQueueComplete() && !capture.readiness().storageWritable);
            capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
            generation = NativeCaptureStorageTestPeer::generation(capture);
        }
        {
            NativeCapture cold(fixture.root, {std::make_shared<GeneratedAec>(), false}, account);
            startAndAdopt(cold, generation);
            const auto value = NativeCaptureStorageTestPeer::projection(cold);
            assert(value->localPurgeAcknowledged(task) == (mode == 0 || mode == 1 || mode == 5));
            auto invalid = task; invalid.meetingId = "99999999-9999-4999-8999-999999999999";
            assert(!value->localPurgeAcknowledged(invalid)); invalid = task; invalid.taskType = "purge_local_exports";
            assert(!value->localPurgeAcknowledged(invalid));
            if (mode == 4 || mode == 6) assert(value->items().size() == 1 && value->items()[0].safeReason == "local_delete_pending");
            if (mode == 0 || mode == 4) {
                cold.setAuthSessionToken("generated-server-purge-cold");
                assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(cold); return cold.currentAccount().has_value(); }));
                using Phase = NativeCapture::LocalPurgePhase;
                const auto settle = [&](const NativeCapture::QueueMutationTicket& ticket) {
                    assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(cold); }));
                    NativeCaptureStorageTestPeer::pollStorage(cold);
                    assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(cold); return NativeCaptureStorageTestPeer::deletionSlotRetired(cold); }));
                    const auto result = cold.protectedDeletionTicket(ticket.id); assert(result);
                    return *result;
                };
                const auto intent = cold.requestProtectedLocalPurge(task, value, cold.authGeneration(), Phase::intent, {}, 0, true); assert(intent);
                const auto result = settle(*intent);
                assert(result.state == NativeCapture::QueueTicketState::committed && !result.changed && result.baseGeneration == result.targetGeneration);
                if (mode == 4) {
                    // OS deletion succeeded but publication failed. A cold retry
                    // proves absence under the retained intent, then commits
                    // row removal and proof together, without inventing success.
                    const auto retry = cold.requestProtectedLocalPurge(task, NativeCaptureStorageTestPeer::projection(cold),
                        cold.authGeneration(), Phase::purge, "generated-server-purge-0", intent->id); assert(retry);
                    assert(settle(*retry).state == NativeCapture::QueueTicketState::committed);
                    assert(NativeCaptureStorageTestPeer::projection(cold)->localPurgeAcknowledged(task));
                } else assert(NativeCaptureStorageTestPeer::projection(cold)->localPurgeAcknowledged(task));
                assert(cold.endProtectedDeletionContinuation(intent->id));
            }
            cold.shutdown(); assert(waitFor([&] { cold.pollUploads(); return cold.shutdownWorkDrained(); }));
        }
        std::fprintf(stderr, "PROTECTED_SERVER_PURGE mode=%u cold_queue=1 audio=0 real_network=0\n", mode);
    }
}
void protectedPurgeFlight() {
    const DesktopHttpTransport::UploadSend account = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        if (request.path == "/desktop/settings/spaces") return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        assert(request.path == "/api/v1/auth/me");
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    };
    for (unsigned mode = 0; mode != 13; ++mode) {
        testing::GeneratedRecordingRoot fixture;
        const auto path = fixture.root / "generated-purge-flight";
        const auto json = [](bool exports = false, bool acknowledged = false) {
            return std::string(R"({"task_id":")") + (exports ? "66666666-6666-4666-8666-666666666666" : "77777777-7777-4777-8777-777777777777") +
                R"(","meeting_id":"88888888-8888-4888-8888-888888888888","task_type":")" +
                (exports ? "purge_local_exports" : "purge_local_buffers") + R"(","state":")" +
                (acknowledged ? "acknowledged" : "pending") + R"(","expires_at":"2026-10-20T12:00:00Z"})";
        };
        auto task = DesktopApiClient::decodeLocalPurgeTask<CustodyString>(json()); assert(task);
        std::async(std::launch::async, [&] {
            auto cancel = std::make_shared<std::atomic<bool>>(false);
            auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(opened.ok()); auto owner = *opened.value;
            auto created = V5LocalRecordingWriter::open(owner, "generated-purge-flight", cancel); assert(created.ok());
            CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
            for (unsigned j = 0; j != 500; ++j) { frame.ptsFrames = j * 480; assert((*created.value)->append(frame)); }
            assert((*created.value)->finalize().normalPackage()); created.value.reset();
            auto current = owner->readQueueValue(cancel); assert(current.ok());
            auto copy = std::allocate_shared<ProtectedUploadQueueValue>(CustodyAllocator<ProtectedUploadQueueValue>{}, **current.value);
            ProtectedUploadQueueValue::Item row; row.localRecordingId = row.directoryId = row.sessionId = "generated-purge-flight";
            const auto directory = path.u8string(); row.packageDirectory.assign(directory.begin(), directory.end());
            row.ownerUserId = "11111111-1111-4111-8111-111111111111"; row.ownerWorkspaceId = "22222222-2222-4222-8222-222222222222";
            assert(copy->enqueue(row, 1000, cancel.get()));
            BasicDesktopTransportResult<CustodyString> result; result.status = DesktopTransportStatus::uploaded;
            result.serverTruth.emplace(); result.serverTruth->localRecordingId = row.localRecordingId; result.serverTruth->meetingId = task->meetingId;
            assert(copy->applyUploadResult(row, result, 2000, cancel.get()));
            if (mode == 1 || mode == 7 || mode == 10) {
                ProtectedDeletionPlan plan; bool changed = false;
                assert(copy->planDeletionSelection({{DeletionTarget::ownOrigin, row.directoryId}}, row.ownerUserId, row.ownerWorkspaceId,
                    "https://rec.2brain.pro", 3000, plan, changed, cancel.get()) && changed);
                BasicDeletionWireResult<CustodyString> answer; answer.status = 200;
                answer.body = R"({"receipt_type":"meeting_deletion","request_id":"55555555-5555-4555-8555-555555555555","meeting_id":"88888888-8888-4888-8888-888888888888","phase":"accepted","local_recording_id":"generated-purge-flight"})";
                assert(copy->applyDeletionAnswer(copy->deletionOperations().back(), answer, 4000, changed, cancel.get()) && changed);
            }
            auto bytes = copy->serialize(cancel); assert(bytes.ok());
            assert(commitProtectedCustodyMetadata(owner, owner->queueContext(), owner->queueGeneration(), *bytes.value, cancel).state == CustodyCommitState::committed);
        }).get();
        std::atomic<unsigned> lists{0}, ensures{0}, acks{0};
        std::atomic<bool> held{false}, release{false}, lost{mode == 4}, ackReached{false}, ackRelease{false};
        const DesktopHttpTransport::ProtectedUploadSend wire = [&](const auto& config, const auto& request) -> DesktopHttpTransport::ProtectedUploadResponse {
            assert(config.scopedAccount && config.confirmedIdentity && config.scopedAccount->userId == config.confirmedIdentity->userId);
            const auto response = [](const std::string& text, unsigned status = 200) { DesktopHttpTransport::ProtectedUploadResponse value;
                value.status = status; value.body.assign(text.begin(), text.end()); return value; };
            if (request.path == DesktopApiClient::notificationContextPath) return response(R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","recording_deletion_protocol_version":1})");
            if (request.path == DesktopApiClient::purgeTasksPath) {
                ++lists;
                if (mode == 3 || mode == 8 || mode == 9 || mode == 12) { held.store(true); while (!release.load()) Sleep(1); }
                if (mode == 12) { auto limited = response("", 429); limited.retryAfter = "120"; return limited; }
                if (mode == 11) {
                    std::string oversized = R"({"tasks":[)";
                    for (unsigned i = 0; i != 201; ++i) { if (i) oversized += ','; oversized += json(); }
                    return response(oversized + "]}");
                }
                return response(mode == 1 || mode == 10 ? R"({"tasks":[]})" : std::string(R"({"tasks":[)") + json(mode == 5 || mode == 7) +
                    (mode == 2 ? ",{\"task_id\":\"invalid\"}" : "") + "]}");
            }
            if (request.path == "/api/v1/desktop/meetings/88888888-8888-4888-8888-888888888888/local-purge-task") {
                ++ensures; assert(request.method == "POST" && request.body.empty());
                auto ensured = json();
                if (mode == 10) { const auto at = ensured.find("88888888-8888-4888-8888-888888888888"); assert(at != std::string::npos);
                    ensured.replace(at, 36, "99999999-9999-4999-8999-999999999999"); }
                return response(ensured, 201);
            }
            assert(request.path == DesktopApiClient::localPurgeAckPath<CustodyString>(request.body.find("unverified") != CustodyString::npos ?
                "66666666-6666-4666-8666-666666666666" : "77777777-7777-4777-8777-777777777777"));
            ++acks;
            const bool failed = request.body.find("unverified") != CustodyString::npos;
            if (failed) {
                assert(std::filesystem::exists(path)); auto failedTask = json(true);
                const auto at = failedTask.find("pending"); assert(at != std::string::npos);
                failedTask.replace(at, 7, "failed"); return response(failedTask);
            }
            assert(!std::filesystem::exists(path));
            // The owner thread observes the adopted proof before this ACK
            // returns. A separate cold owner is checked after actual shutdown,
            // never opened concurrently with the genuine exclusive root lease.
            ackReached.store(true); while (!ackRelease.load()) Sleep(1);
            if (lost.exchange(false)) { auto dropped = response("", 0); dropped.transportFailed = true; return dropped; }
            auto valueResponse = response(json(false, true));
            if (mode == 6) { valueResponse.status = 429; valueResponse.retryAfter = "120"; }
            return valueResponse;
        };
        const auto retire = [&](NativeCapture& capture) {
            const bool finished = waitFor([&] {
                capture.pollUploads();
                if (ackReached.load() && !ackRelease.load()) {
                    const auto value = NativeCaptureStorageTestPeer::projection(capture);
                    const bool proven = value && value->localPurgeAcknowledged(*task);
                    ackRelease.store(true); // A failing witness must not strand the wire.
                    assert(proven);
                }
                return NativeCaptureStorageTestPeer::deletionFlightRetired(capture);
            });
            ackRelease.store(true);
            assert(finished);
        };
        std::uint64_t generation = 0;
        {
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, account, wire);
            startAndAdopt(capture, 2); capture.setAuthSessionToken("generated-purge-flight-owner");
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
            assert(capture.beginProtectedLocalPurgePass());
            if (mode == 3 || mode == 8 || mode == 9 || mode == 12) {
                const bool reached = waitFor([&] { capture.pollUploads(); return held.load(); });
                if (!reached) release.store(true);
                assert(reached);
                if (mode == 3) capture.setAuthSessionToken({});
                if (mode == 8) capture.requestShutdown();
                if (mode == 9) capture.setUpdateAdmissionBlocked(true);
                release.store(true);
                if (mode == 12) {
                    // The old 429 is already received, but not yet adopted on
                    // the owner thread. It cannot delay the new auth epoch.
                    assert(waitFor([&] { return NativeCaptureStorageTestPeer::deletionNetworkExited(capture); }));
                    capture.setAuthSessionToken("generated-purge-flight-next");
                    assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
                }
            }
            retire(capture);
            if (mode == 6) {
                assert(waitFor([&] { capture.pollUploads(); return capture.updateWorkDrained() && capture.localObservation().complete; }));
                assert(!capture.beginProtectedLocalPurgePass());
                capture.setAuthSessionToken("generated-purge-flight-next");
                assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
            }
            if (mode == 6 || mode == 12) assert(waitFor([&] { capture.pollUploads(); return capture.beginProtectedLocalPurgePass(); }));
            assert(!capture.localQueueComplete() && !capture.readiness().storageWritable);
            capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
            generation = NativeCaptureStorageTestPeer::generation(capture);
        }
        const bool removed = mode == 0 || mode == 1 || mode == 4 || mode == 6 || mode == 7;
        assert(std::filesystem::exists(path) == !removed);
        assert(ensures == ((mode == 1 || mode == 7 || mode == 10) ? 1U : 0U));
        assert(acks == (mode == 7 ? 2U : removed || mode == 5 ? 1U : 0U));
        {
            NativeCapture cold(fixture.root, {std::make_shared<GeneratedAec>(), false}, account, wire); startAndAdopt(cold, generation);
            assert(NativeCaptureStorageTestPeer::projection(cold)->localPurgeAcknowledged(*task) == removed);
            if (mode == 4) {
                cold.setAuthSessionToken("generated-purge-flight-cold");
                assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(cold); return cold.currentAccount().has_value(); }));
                ackReached.store(false); ackRelease.store(false);
                assert(cold.beginProtectedLocalPurgePass());
                retire(cold);
                assert(acks == 2 && NativeCaptureStorageTestPeer::generation(cold) == generation);
            }
            cold.shutdown(); assert(waitFor([&] { cold.pollUploads(); return cold.shutdownWorkDrained(); }));
        }
        std::fprintf(stderr, "PROTECTED_PURGE_FLIGHT mode=%u cold_proof=1 audio=0 real_network=0\n", mode);
    }
}
void protectedDeletionDisplayDrain() {
    Fixture fixture; seedQueue(fixture.root);
    auto seed = std::async(std::launch::async, [&] {
        auto cancellation = std::make_shared<std::atomic<bool>>(false);
        auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(opened.ok());
        auto writer = V5LocalRecordingWriter::open(*opened.value, "waiting", cancellation); assert(writer.ok());
        CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
        for (unsigned n = 0; n != 100; ++n) { frame.ptsFrames = n * 480; assert((*writer.value)->append(frame)); }
        assert((*writer.value)->finalize().normalPackage());
    });
    seed.get(); // The display must inspect a genuine sealed generated package.
    const DesktopHttpTransport::UploadSend wire = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(request.method == "GET");
        if (request.path == "/desktop/settings/spaces")
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        assert(request.path == "/api/v1/auth/me");
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    };
    {
        NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, wire);
        startAndAdopt(capture, 2); capture.setAuthSessionToken("generated-deletion-display-owner");
        assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
        oldPackedPath = L"\\\\?\\" + (fixture.root / L"waiting" / L".custody-v1" / L"canonical" / L"content.packed-v2").native();
        { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
        pauseOldPackedRead.store(true);
        const auto releaseCut = [] {
            pauseOldPackedRead.store(false);
            { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
            cutWake.notify_all();
        };
        const bool displayPaused = waitFor([&] {
            NativeCaptureStorageTestPeer::pollStorage(capture);
            std::lock_guard<std::mutex> lock(cutMutex); return cutReached;
        });
        if (!displayPaused) { releaseCut(); assert(displayPaused); return; }
        ioCut.store(IoCut::ambiguousRename);
        const auto ticket = capture.requestProtectedDeletionSelection({{DeletionTarget::ownOrigin, "waiting"}}, true);
        const bool intentReady = ticket && waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); });
        ioCut.store(IoCut::none);
        if (!intentReady) { releaseCut(); assert(intentReady); return; }
        NativeCaptureStorageTestPeer::pollStorage(capture);
        const bool displayStillHeld = !NativeCaptureStorageTestPeer::displayFinished(capture);
        // Give the actual storage worker a bounded service window while the
        // display executor still owns its native package readers/proof exchange.
        const auto until = std::chrono::steady_clock::now() + std::chrono::milliseconds(100);
        bool prematureReadback = false;
        while (std::chrono::steady_clock::now() < until) {
            prematureReadback = prematureReadback || NativeCaptureStorageTestPeer::physicalReadback(capture);
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        const bool prematureDrain = capture.endProtectedDeletionContinuation(ticket->id);
        releaseCut(); // Release the generated IO cut before assertions/teardown.
        assert(displayStillHeld && !prematureReadback && !prematureDrain &&
            "deletion_readback_must_wait_for_display_executor_drain");
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::physicalReadback(capture); }));
        NativeCaptureStorageTestPeer::pollStorage(capture);
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::deletionSlotRetired(capture); }));
        assert(capture.endProtectedDeletionContinuation(ticket->id));
        capture.shutdown(); assert(waitFor([&] { return capture.shutdownWorkDrained(); }));
    }
    oldPackedPath.clear();
    std::fputs("PROTECTED_DELETION_DISPLAY actual_inspection=1 premature_readback=0 actual_drain=1 audio=0 network_delete=0\n", stderr);
}
void protectedDeletionSelection() {
    const DesktopHttpTransport::UploadSend wire = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(request.method == "GET");
        if (request.path == "/desktop/settings/spaces")
            return {200, "{\"spaces\":[{\"id\":\"22222222-2222-4222-8222-222222222222\",\"active\":true}]}"};
        assert(request.path == "/api/v1/auth/me");
        return {200, "{\"user_id\":\"11111111-1111-4111-8111-111111111111\","
            "\"workspace_id\":\"22222222-2222-4222-8222-222222222222\","
            "\"active_session_id\":\"33333333-3333-4333-8333-333333333333\"}"};
    };
    for (const auto cut : {IoCut::none, IoCut::flush, IoCut::ambiguousRename,
                          IoCut::pauseAfterFlush, IoCut::pauseAfterRename}) {
        Fixture fixture; seedQueue(fixture.root, true);
        const bool durable = cut == IoCut::none || cut == IoCut::ambiguousRename || cut == IoCut::pauseAfterRename;
        {
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, wire);
            startAndAdopt(capture, 2); capture.setAuthSessionToken("generated-batch-owner");
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
            const auto before = NativeCaptureStorageTestPeer::projection(capture);
            const auto disk = snapshot(fixture.root);
            ProtectedDeletionTargets targets{{DeletionTarget::ownOrigin, "local-only-dir"},
                {DeletionTarget::ownOrigin, "waiting-dir"}, {DeletionTarget::ownOrigin, "retained-dir"},
                {DeletionTarget::meeting, "33333333-3333-4333-8333-333333333333"},
                {DeletionTarget::meeting, "88888888-8888-4888-8888-888888888888"}};
            if (cut == IoCut::none) {
                auto invalid = targets; invalid.push_back({DeletionTarget::ownOrigin, "unknown"});
                assert(!capture.requestProtectedDeletionSelection(std::move(invalid)));
                ProtectedDeletionTargets excessive(101, targets.front());
                assert(!capture.requestProtectedDeletionSelection(std::move(excessive)));
                const auto count = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
                CustodyAllocator<char> allocator; auto* reservation = allocator.allocate(count);
                // Targets are already charged; admission cannot allocate its owned work/plan.
                assert(!capture.requestProtectedDeletionSelection(std::move(targets)));
                allocator.deallocate(reservation, count);
                targets = {{DeletionTarget::ownOrigin, "local-only-dir"}, {DeletionTarget::ownOrigin, "waiting-dir"},
                    {DeletionTarget::ownOrigin, "retained-dir"}, {DeletionTarget::meeting, "33333333-3333-4333-8333-333333333333"},
                    {DeletionTarget::meeting, "88888888-8888-4888-8888-888888888888"}};
                assert(snapshot(fixture.root) == disk && NativeCaptureStorageTestPeer::projection(capture) == before);
            }
            { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
            ioCut.store(cut);
            const auto pending = capture.requestProtectedDeletionSelection(std::move(targets));
            assert(pending && pending->state == NativeCapture::QueueTicketState::pending && !capture.protectedDeletionPlan(pending->id));
            if (cut == IoCut::pauseAfterFlush || cut == IoCut::pauseAfterRename) {
                assert(waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }));
                capture.setAuthSessionToken({});
                { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; cutWake.notify_all(); }
            }
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            ioCut.store(IoCut::none);
            // Lost polling cannot return saved or release in-flight ownership.
            assert(NativeCaptureStorageTestPeer::projection(capture) == before &&
                !capture.protectedDeletionPlan(pending->id) && !capture.updateWorkDrained());
            NativeCaptureStorageTestPeer::pollStorage(capture);
            const auto result = capture.protectedDeletionTicket(pending->id); assert(result);
            const bool committed = cut == IoCut::none || cut == IoCut::pauseAfterRename;
            assert(result->state == (committed ? NativeCapture::QueueTicketState::committed :
                cut == IoCut::ambiguousRename ? NativeCapture::QueueTicketState::ambiguous : NativeCapture::QueueTicketState::notCommitted));
            const auto after = NativeCaptureStorageTestPeer::projection(capture);
            if (committed) {
                assert(after != before && after->deletionOperations().size() == 3 &&
                    after->items()[2].safeReason == "local_delete_pending" && after->deletionBlocks(after->items()[2]));
                const auto plan = capture.protectedDeletionPlan(pending->id);
                if (cut == IoCut::none) {
                    assert(plan && plan->saved && plan->operationIds.size() == 3 && plan->requests.size() == 3 &&
                        plan->localOnly.size() == 1 && plan->localOnly.front() == "local-only");
                    assert(plan->requests[0].targetId == "waiting-dir" && before->items()[0].localRecordingId == "waiting");
                } else assert(!plan && !capture.currentAccount());
            } else assert(after == before && !capture.protectedDeletionPlan(pending->id));
            capture.shutdown(); assert(waitFor([&] { return capture.shutdownWorkDrained(); }));
        }
        NativeCapture restarted(fixture.root, {std::make_shared<GeneratedAec>(), false});
        startAndAdopt(restarted, durable ? 3 : 2);
        const auto restored = NativeCaptureStorageTestPeer::projection(restarted);
        assert(restored->deletionOperations().size() == (durable ? 3 : 1));
        assert((restored->items()[2].safeReason == "local_delete_pending") == durable);
        restarted.shutdown(); assert(waitFor([&] { return restarted.shutdownWorkDrained(); }));
        std::fprintf(stderr, "PROTECTED_DELETION_SELECTION cut=%u durable=%u whole_batch=1 network_delete=0 physical_delete=0\n",
            static_cast<unsigned>(cut), durable ? 1U : 0U);
    }
    // Same operation on another origin is rejected AFTER a new private prefix.
    // It must not commit that prefix just because changed became true earlier.
    Fixture fixture; seedQueue(fixture.root);
    NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, wire);
    startAndAdopt(capture, 2); capture.setAuthSessionToken("generated-batch-owner");
    assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
    const auto before = NativeCaptureStorageTestPeer::projection(capture);
    const auto pending = capture.requestProtectedDeletionSelection({{DeletionTarget::ownOrigin, "waiting"},
        {DeletionTarget::meeting, "33333333-3333-4333-8333-333333333333"}}); assert(pending);
    assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
    NativeCaptureStorageTestPeer::pollStorage(capture);
    const auto rejected = capture.protectedDeletionTicket(pending->id);
    assert(rejected && rejected->state == NativeCapture::QueueTicketState::notCommitted && !rejected->changed &&
        NativeCaptureStorageTestPeer::projection(capture) == before && NativeCaptureStorageTestPeer::generation(capture) == 2);
    capture.shutdown(); assert(waitFor([&] { return capture.shutdownWorkDrained(); }));
    NativeCapture reopened(fixture.root, {std::make_shared<GeneratedAec>(), false}); startAndAdopt(reopened, 2);
    assert(NativeCaptureStorageTestPeer::projection(reopened)->deletionOperations().size() == 1);
    reopened.shutdown(); assert(waitFor([&] { return reopened.shutdownWorkDrained(); }));
}
void protectedDeletionAnswer() {
    for (const auto cut : {IoCut::none, IoCut::flush, IoCut::ambiguousRename,
                          IoCut::pauseAfterFlush, IoCut::pauseAfterRename}) {
        Fixture fixture; seedQueue(fixture.root);
        const bool durable = cut == IoCut::none || cut == IoCut::ambiguousRename || cut == IoCut::pauseAfterRename;
        const DesktopHttpTransport::UploadSend wire = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
            assert(request.method == "GET"); // Generated account responses only; no delete HTTP or device audio.
            if (request.path == "/desktop/settings/spaces")
                return {200, "{\"spaces\":[{\"id\":\"22222222-2222-4222-8222-222222222222\",\"active\":true}]}"};
            assert(request.path == "/api/v1/auth/me");
            return {200, "{\"user_id\":\"11111111-1111-4111-8111-111111111111\","
                "\"workspace_id\":\"22222222-2222-4222-8222-222222222222\","
                "\"active_session_id\":\"33333333-3333-4333-8333-333333333333\"}"};
        };
        {
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, wire);
            startAndAdopt(capture, 2);
            capture.setAuthSessionToken("generated-deletion-owner");
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
            const auto intent = capture.requestProtectedDeletion("waiting"); assert(intent);
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture); return capture.updateWorkDrained(); }));
            const auto before = NativeCaptureStorageTestPeer::projection(capture);
            assert(before->deletionOperations().size() == 2 && NativeCaptureStorageTestPeer::generation(capture) == 3);
            const auto operation = before->deletionOperations().back();
            const auto epoch = capture.authGeneration();
            BasicDeletionWireResult<CustodyString> answer;
            answer.status = 200;
            answer.body = "{\"receipt_type\":\"meeting_deletion\",\"request_id\":\"77777777-7777-4777-8777-777777777777\","
                "\"meeting_id\":\"88888888-8888-4888-8888-888888888888\",\"local_recording_id\":\"waiting\",\"phase\":\"accepted\"}";
            assert(!capture.applyProtectedDeletionAnswer(before, epoch, "99999999-9999-4999-8999-999999999999", answer));
            assert(!capture.applyProtectedDeletionAnswer(before, epoch + 1, operation.operationId, answer));
            assert(!capture.applyProtectedDeletionAnswer({}, epoch, operation.operationId, answer));
            { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
            ioCut.store(cut);
            const auto pending = capture.applyProtectedDeletionAnswer(before, epoch, operation.operationId, answer);
            assert(pending && pending->kind == NativeCapture::QueueMutationKind::deletionResult &&
                pending->state == NativeCapture::QueueTicketState::pending && !pending->changed);
            assert(!capture.applyProtectedDeletionAnswer(before, epoch, operation.operationId, answer));
            if (cut == IoCut::pauseAfterFlush || cut == IoCut::pauseAfterRename) {
                assert(waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }));
                capture.setAuthSessionToken({});
                { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; cutWake.notify_all(); }
            }
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            ioCut.store(IoCut::none);
            assert(NativeCaptureStorageTestPeer::projection(capture) == before &&
                NativeCaptureStorageTestPeer::generation(capture) == 3 && !capture.updateWorkDrained());
            NativeCaptureStorageTestPeer::pollStorage(capture);
            const auto result = NativeCaptureStorageTestPeer::ticket(capture); assert(result && result->id == pending->id);
            const bool committed = cut == IoCut::none || cut == IoCut::pauseAfterRename;
            assert(result->state == (committed ? NativeCapture::QueueTicketState::committed :
                cut == IoCut::ambiguousRename ? NativeCapture::QueueTicketState::ambiguous : NativeCapture::QueueTicketState::notCommitted));
            const auto after = NativeCaptureStorageTestPeer::projection(capture);
            if (committed) {
                assert(after != before && after->deletionOperations().back().phase == DeletionOperationPhase::accepted &&
                    after->deletionOperations().back().attemptCount == 1 &&
                    after->items()[0].meetingId == "88888888-8888-4888-8888-888888888888");
                if (cut == IoCut::none) {
                    assert(waitFor([&] { return capture.updateWorkDrained(); }));
                    const auto once = snapshot(fixture.root);
                    assert(!capture.applyProtectedDeletionAnswer(before, epoch, operation.operationId, answer));
                    const auto duplicate = capture.applyProtectedDeletionAnswer(after, epoch, operation.operationId, answer); assert(duplicate);
                    assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture); return capture.updateWorkDrained(); }));
                    const auto repeated = NativeCaptureStorageTestPeer::ticket(capture);
                    assert(repeated && repeated->id == duplicate->id && !repeated->changed &&
                        repeated->state == NativeCapture::QueueTicketState::committed && repeated->targetGeneration == 4 &&
                        snapshot(fixture.root) == once);
                } else assert(!capture.currentAccount() && result->epoch != capture.authGeneration());
            } else assert(after == before);
            assert(!capture.localQueueComplete() && !capture.readiness().storageWritable);
            capture.shutdown(); assert(waitFor([&] { return capture.shutdownWorkDrained(); }));
        }
        NativeCapture restarted(fixture.root, {std::make_shared<GeneratedAec>(), false});
        startAndAdopt(restarted, durable ? 4 : 3);
        const auto restored = NativeCaptureStorageTestPeer::projection(restarted);
        const auto& operation = restored->deletionOperations().back();
        assert(operation.phase == (durable ? DeletionOperationPhase::accepted : DeletionOperationPhase::queued));
        assert(operation.attemptCount == (durable ? 1U : 0U));
        assert(restored->items()[0].meetingId == (durable ? "88888888-8888-4888-8888-888888888888" : ""));
        restarted.shutdown(); assert(waitFor([&] { return restarted.shutdownWorkDrained(); }));
        std::fprintf(stderr, "PROTECTED_DELETION_ANSWER cut=%u durable=%u network_delete=0 physical_delete=0\n",
            static_cast<unsigned>(cut), durable ? 1U : 0U);
    }
}
void protectedAccountProblems() {
    Fixture fixture; seedQueue(fixture.root);
    const auto disk = snapshot(fixture.root);
    std::atomic<unsigned> accountCalls{0};
    const DesktopHttpTransport::UploadSend wire = [&](const auto& config, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(request.method == "GET"); // This metadata probe must never upload.
        const bool other = config.sessionToken == "generated-other-workspace";
        assert(other || config.sessionToken == "generated-owner" || config.sessionToken == "generated-stale-owner");
        const std::string workspace = other ? "55555555-5555-4555-8555-555555555555" : "22222222-2222-4222-8222-222222222222";
        ++accountCalls;
        if (request.path == "/desktop/settings/spaces")
            return {200, "{\"spaces\":[{\"id\":\"" + workspace + "\",\"active\":true}]}"};
        assert(request.path == "/api/v1/auth/me");
        return {200, "{\"user_id\":\"11111111-1111-4111-8111-111111111111\",\"workspace_id\":\"" + workspace +
            "\",\"active_session_id\":\"33333333-3333-4333-8333-333333333333\"}"};
    };
    bool owned = false, isolated = false, loggedOut = false, stale = false, quotaRefused = false, restored = false;
    {
        NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, wire);
        startAndAdopt(capture, 2);
        const auto adoptAccount = [&](const char* token) {
            capture.setAuthSessionToken(token);
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
        };
        const auto states = [&](LocalProblemState waiting, LocalProblemState retained) {
            const auto problems = capture.recordingProblems(2000);
            return problems.size() == 2 &&
                std::any_of(problems.begin(), problems.end(), [&](const auto& p) { return p.sessionId == "waiting" && p.state == waiting; }) &&
                std::any_of(problems.begin(), problems.end(), [&](const auto& p) { return p.sessionId == "retained" && p.state == retained; });
        };
        adoptAccount("generated-owner");
        const auto owner = capture.localProblemContext();
        auto foreignOrigin = owner; foreignOrigin.origin = "https://other.example.test";
        auto foreignUser = owner; foreignUser.owner = "66666666-6666-4666-8666-666666666666";
        owned = capture.ownsRecordingSession(owner, "waiting") && capture.ownsRecordingSession(owner, "retained") &&
            !capture.ownsRecordingSession(owner, "") && !capture.ownsRecordingSession(owner, "absent") &&
            !capture.ownsRecordingSession(foreignOrigin, "waiting") && !capture.ownsRecordingSession(foreignUser, "waiting") &&
            states(LocalProblemState::problem, LocalProblemState::positivelyResolved);
        {
            CustodyAllocator<char> allocator;
            const auto count = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
            auto* reservation = allocator.allocate(count);
            try { (void)capture.recordingProblems(2000); } catch (const std::bad_alloc&) { quotaRefused = true; }
            allocator.deallocate(reservation, count);
        }
        restored = states(LocalProblemState::problem, LocalProblemState::positivelyResolved);
        adoptAccount("generated-other-workspace");
        const auto other = capture.localProblemContext();
        isolated = other.workspace != owner.workspace && !capture.ownsRecordingSession(owner, "waiting") &&
            !capture.ownsRecordingSession(other, "waiting") && states(LocalProblemState::unknown, LocalProblemState::unknown);
        capture.setAuthSessionToken({});
        loggedOut = !capture.currentAccount() && !capture.ownsRecordingSession(owner, "waiting") &&
            states(LocalProblemState::unknown, LocalProblemState::unknown);
        capture.setAuthSessionToken("generated-stale-owner");
        NativeCaptureStorageTestPeer::pollAccount(capture);
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::accountResultReady(capture); }));
        // Both real resolver GETs completed, but the UI has not adopted them.
        const auto epoch = capture.authGeneration();
        capture.setAuthSessionToken({});
        NativeCaptureStorageTestPeer::pollAccount(capture);
        stale = capture.authGeneration() != epoch && accountCalls == 6 && !capture.currentAccount() &&
            !capture.ownsRecordingSession(owner, "waiting") && states(LocalProblemState::unknown, LocalProblemState::unknown);
        assert(!capture.localQueueComplete() && !capture.readiness().storageWritable);
        assert(snapshot(fixture.root) == disk);
        capture.shutdown();
        assert(waitFor([&] { return capture.shutdownWorkDrained(); }));
    }
    assert(owned && "protected_account_projection_requires_current_owned_rows");
    assert(isolated && loggedOut && stale && "protected_account_projection_revokes_workspace_logout_and_stale_completion");
    assert(quotaRefused && restored && "protected_account_projection_quota_refusal_is_not_empty_success");
}
void protectedDisplayOwnerQuota() {
    const auto baseline = CustodyOwnedMemory::usedBytes();
    struct Outcomes {
        bool opened = false, created = false, control = false, quotaFull = false, recovered = false, diskUnchanged = false;
        bool queueReadable = false, futureCreated = false, memoryReleased = false;
        CustodyFileError pressureError = CustodyFileError::none, recoveryError = CustodyFileError::none;
        CustodyFileError queueError = CustodyFileError::none, factoryError = CustodyFileError::none;
        std::uint32_t pressureNative = 0, recoveryNative = 0, queueNative = 0, factoryNative = 0;
    };
    std::array<Outcomes, 2> outcomes{};
    for (unsigned mode = 0; mode != outcomes.size(); ++mode) {
        Fixture fixture; // Each read entry point gets an independent root/owner/worker.
        auto worker = std::async(std::launch::async, [&, mode] {
            Outcomes result;
            auto cancellation = std::make_shared<std::atomic<bool>>(false);
            auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancellation);
            result.opened = opened.ok();
            if (!result.opened) return result;
            auto owner = *opened.value;
            constexpr auto name = "generated-display-owner-quota";
            {
                auto package = owner->createPackage(name, cancellation);
                result.created = package.ok();
            } // Release the genuine capturing package before read-only discovery.
            if (!result.created) return result;
            {
                if (mode == 0) {
                    auto pair = owner->readPackage(name, cancellation);
                    result.control = pair.ok() && (*pair.value)->current().phase == CustodyPackagePhase::capturing;
                } else {
                    auto queue = owner->readQueueValue(cancellation);
                    result.control = queue.ok() && owner->queueGeneration() == 1;
                }
            }
            if (!result.control) return result;
            const auto before = snapshot(fixture.root);
            {
                CustodyBytes reservation;
                reservation.resize(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
                result.quotaFull = CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit;
                if (mode == 0) {
                    auto pair = owner->readPackage(name, cancellation);
                    result.pressureError = pair.error;
                    result.pressureNative = pair.nativeError;
                } else {
                    auto queue = owner->readQueueValue(cancellation);
                    result.pressureError = queue.error;
                    result.pressureNative = queue.nativeError;
                }
            } // Free the full reservation before retrying on the SAME owner.
            {
                auto freshCancellation = std::make_shared<std::atomic<bool>>(false);
                if (mode == 0) {
                    auto pair = owner->readPackage(name, freshCancellation);
                    result.recovered = pair.ok() && (*pair.value)->current().phase == CustodyPackagePhase::capturing;
                    result.recoveryError = pair.error;
                    result.recoveryNative = pair.nativeError;
                } else {
                    auto queue = owner->readQueueValue(freshCancellation);
                    result.recovered = queue.ok() && owner->queueGeneration() == 1;
                    result.recoveryError = queue.error;
                    result.recoveryNative = queue.nativeError;
                }
            }
            {
                auto freshCancellation = std::make_shared<std::atomic<bool>>(false);
                auto queue = owner->readQueueValue(freshCancellation);
                result.queueReadable = queue.ok() && owner->queueGeneration() == 1;
                result.queueError = queue.error; result.queueNative = queue.nativeError;
            }
            result.diskUnchanged = snapshot(fixture.root) == before;
            { // Intentional birth is AFTER the read-only disk comparison.
                auto freshCancellation = std::make_shared<std::atomic<bool>>(false);
                auto package = owner->createPackage("generated-after-transient-quota", freshCancellation);
                result.futureCreated = package.ok() && (*package.value)->current().phase == CustodyPackagePhase::capturing &&
                    (*package.value)->current().generation == 1;
                result.factoryError = package.error; result.factoryNative = package.nativeError;
            }
            return result; // Only scalars cross threads; all native owners release on this worker.
        });
        auto& result = outcomes[mode];
        result = worker.get();
        result.memoryReleased = waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; });
        std::fprintf(stderr, "PROTECTED_DISPLAY_OWNER_QUOTA mode=%s opened=%u created=%u control=%u quota_full=%u pressure_error=%u pressure_native=%u recovered=%u recovery_error=%u recovery_native=%u disk_unchanged=%u memory_released=%u queue_readable=%u queue_error=%u queue_native=%u future_created=%u factory_error=%u factory_native=%u\n",
            mode == 0 ? "package" : "queue",
            result.opened, result.created, result.control, result.quotaFull, static_cast<unsigned>(result.pressureError),
            result.pressureNative, result.recovered, static_cast<unsigned>(result.recoveryError), result.recoveryNative,
            result.diskUnchanged, result.memoryReleased, result.queueReadable, static_cast<unsigned>(result.queueError),
            result.queueNative, result.futureCreated, static_cast<unsigned>(result.factoryError), result.factoryNative);
        std::fflush(stderr);
    }
    // Collect BOTH paths and release both fixtures/workers before any named failure.
    for (const auto& result : outcomes) {
        assert(result.memoryReleased && "protected_display_owner_quota_requires_worker_memory_drain");
        assert(result.opened && result.created && result.control && "protected_display_owner_quota_requires_genuine_control");
        assert(result.quotaFull && result.pressureError == CustodyFileError::allocationFailed &&
            "protected_display_owner_quota_requires_exact_allocation_refusal");
        assert(result.diskUnchanged && "protected_display_owner_quota_must_not_mutate_disk");
    }
    assert(outcomes[0].recovered && "protected_display_owner_must_recover_after_transient_quota");
    assert(outcomes[1].recovered && "protected_display_queue_read_must_recover_after_transient_quota");
    for (const auto& result : outcomes) {
        assert(result.queueReadable && "protected_display_owner_quota_must_preserve_subsequent_queue_read");
        assert(result.futureCreated && "protected_display_owner_quota_must_preserve_future_package_birth");
    }
}
void protectedDisplayTimingAndRestart() {
    Fixture fixture;
    constexpr const char* session = "generated-display-timing";
    auto seed = std::async(std::launch::async, [&] {
        auto cancellation = std::make_shared<std::atomic<bool>>(false);
        auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(opened.ok());
        auto store = *opened.value;
        auto writer = V5LocalRecordingWriter::open(store, session, cancellation); assert(writer.ok());
        CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
        for (unsigned n = 0; n != 100; ++n) {
            frame.ptsFrames = n * 480;
            assert((*writer.value)->append(frame));
        }
        const auto result = (*writer.value)->finalize(ReasonCode::none, RecordingStopReason::interruption);
        assert(result.normalPackage() && result.semanticVerified && result.durationMs == 1000 &&
            result.startedAtMs > 1000 && result.stoppedAtMs >= result.startedAtMs);
        const auto& package = (*writer.value)->package()->current();
        assert(std::any_of(package.refs.begin(), package.refs.begin() + package.refCount, [](const auto& ref) {
            return ref.role == CustodyRole::playback && ref.packed && ref.sealed && ref.length && *ref.length &&
                ref.generation && *ref.generation && ref.containerId && ref.rootRef && ref.sha256;
        }));
        writer.value.reset(); // Native writer teardown remains on this seed worker.
        auto current = store->readQueueValue(cancellation); assert(current.ok());
        auto value = std::allocate_shared<ProtectedUploadQueueValue>(CustodyAllocator<ProtectedUploadQueueValue>{}, **current.value);
        ProtectedUploadQueueValue::Item row;
        row.localRecordingId = row.directoryId = row.sessionId = session;
        const auto path = result.packageDirectory.u8string();
        row.packageDirectory.assign(path.begin(), path.end());
        row.ownerUserId = "11111111-1111-4111-8111-111111111111";
        row.ownerWorkspaceId = "22222222-2222-4222-8222-222222222222";
        row.status = UploadQueueStatus::uploaded; // Generated classification, not a claim of server acceptance.
        assert(value->enqueue(std::move(row), 1000, cancellation.get()));
        auto bytes = value->serialize(cancellation); assert(bytes.ok());
        auto saved = commitProtectedCustodyMetadata(store, store->queueContext(), store->queueGeneration(), *bytes.value, cancellation);
        assert(saved.state == CustodyCommitState::committed && saved.targetGeneration == 2);
        return ProtectedLocalRecordingTiming{result.durationMs, result.startedAtMs, result.stoppedAtMs,
            result.displayTimezoneOffsetMinutes}; // Only scalar display expectations cross to the test/UI thread.
    });
    const auto expected = seed.get();
    const auto diskBefore = snapshot(fixture.root);
    std::atomic<unsigned> accountCalls{0}, unexpectedCalls{0}, uploadCalls{0};
    const DesktopHttpTransport::UploadSend accountWire = [&](const auto& config, const auto& request) -> DesktopHttpTransport::UploadResponse {
        if (config.sessionToken != "generated-display-owner" || request.method != "GET") {
            ++unexpectedCalls; return {403, "{}"};
        }
        if (request.path == "/desktop/settings/spaces") {
            ++accountCalls;
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        }
        if (request.path == "/api/v1/auth/me") {
            ++accountCalls;
            return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
        }
        ++unexpectedCalls; return {403, "{}"};
    };
    const DesktopHttpTransport::ProtectedUploadSend uploadWire = [&](const auto&, const auto&) {
        ++uploadCalls; return DesktopHttpTransport::ProtectedUploadResponse{503, "{}"};
    };
    bool accountAdopted = false, timingObserved = false, sameQueue = false, admissionClosed = false, drained = false;
    bool quotaUnknown = false, logoutRevoked = false, staleRevoked = false, cutObserved = false;
    {
        NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, accountWire, uploadWire);
        startAndAdopt(capture, 2); // Cold discovery after every seed native owner has released.
        const auto adopted = capture.localObservation().value;
        capture.setAuthSessionToken("generated-display-owner");
        accountAdopted = waitFor([&] {
            NativeCaptureStorageTestPeer::pollAccount(capture);
            return capture.currentAccount().has_value();
        });
        if (accountAdopted) {
            CustodyBytes reservation;
            reservation.resize(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
            NativeCaptureStorageTestPeer::pollStorage(capture);
            const auto observation = capture.localObservation();
            quotaUnknown = observation.value == adopted && !observation.timings;
        }
        if (accountAdopted) timingObserved = waitFor([&] {
            // pollUploads would consume authRecovered and cancel display with upload preparation.
            NativeCaptureStorageTestPeer::pollStorage(capture);
            const auto observation = capture.localObservation();
            if (!observation.complete || observation.value != adopted || !observation.timings ||
                observation.timings->snapshot != observation.value || observation.value->items().size() != 1 ||
                observation.timings->rows.size() != observation.value->items().size() || !observation.timings->rows[0]) return false;
            const auto& row = observation.value->items()[0];
            const auto& timing = *observation.timings->rows[0];
            return std::string_view(row.sessionId) == session && row.status == UploadQueueStatus::uploaded && row.updatedAtMs == 1000 &&
                timing.durationMs == expected.durationMs && timing.startedAtMs == expected.startedAtMs &&
                timing.stoppedAtMs == expected.stoppedAtMs && timing.displayTimezoneOffsetMinutes == expected.displayTimezoneOffsetMinutes;
        });
        sameQueue = capture.localObservation().value == adopted && NativeCaptureStorageTestPeer::generation(capture) == 2;
        admissionClosed = !capture.localQueueComplete() && !capture.readiness().storageWritable;
        capture.setAuthSessionToken({});
        logoutRevoked = !capture.localObservation().timings;
        oldPackedPath = L"\\\\?\\" + (fixture.root / session / L".custody-v1" / L"canonical" / L"content.packed-v2").native();
        { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
        pauseOldPackedRead.store(true);
        capture.setAuthSessionToken("generated-display-owner");
        const bool secondAccount = waitFor([&] {
            NativeCaptureStorageTestPeer::pollAccount(capture);
            return capture.currentAccount().has_value();
        });
        if (secondAccount) cutObserved = waitFor([&] {
            NativeCaptureStorageTestPeer::pollStorage(capture);
            std::lock_guard<std::mutex> lock(cutMutex); return cutReached;
        });
        capture.setAuthSessionToken({});
        staleRevoked = !capture.localObservation().timings;
        pauseOldPackedRead.store(false);
        { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
        cutWake.notify_all(); // Never hold the actual generated IO cut during teardown.
        const bool oldDisplayFinished = waitFor([&] {
            NativeCaptureStorageTestPeer::pollStorage(capture);
            return NativeCaptureStorageTestPeer::displayFinished(capture);
        });
        staleRevoked = staleRevoked && oldDisplayFinished && !capture.localObservation().timings;
        capture.shutdown();
        drained = waitFor([&] {
            NativeCaptureStorageTestPeer::pollAccount(capture);
            NativeCaptureStorageTestPeer::pollStorage(capture);
            return capture.shutdownWorkDrained();
        });
        assert(drained && "protected_display_timing_requires_actual_shutdown_drain");
    }
    oldPackedPath.clear();
    const bool diskUnchanged = snapshot(fixture.root) == diskBefore;
    const bool memoryReleased = waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; });
    std::fprintf(stderr, "PROTECTED_DISPLAY timing=%u account=%u same_queue=%u admission_closed=%u account_calls=%u unexpected_calls=%u upload_calls=%u drain=%u disk_unchanged=%u memory_released=%u quota_unknown=%u logout_revoked=%u native_cut=%u stale_revoked=%u\n",
        timingObserved, accountAdopted, sameQueue, admissionClosed, accountCalls.load(), unexpectedCalls.load(), uploadCalls.load(),
        drained, diskUnchanged, memoryReleased, quotaUnknown, logoutRevoked, cutObserved, staleRevoked);
    assert(drained && memoryReleased && "protected_display_timing_releases_workers_and_native_owners");
    assert(accountAdopted && accountCalls == 4 && "protected_display_timing_requires_actual_account_resolver");
    assert(timingObserved && "protected_display_uploaded_row_requires_genuine_package_timing");
    assert(quotaUnknown && logoutRevoked && cutObserved && staleRevoked &&
        "protected_display_timing_quota_and_stale_native_completion_remain_unknown");
    assert(sameQueue && diskUnchanged && unexpectedCalls == 0 && uploadCalls == 0 && admissionClosed &&
        "protected_display_timing_does_not_mutate_queue_or_dispatch_upload");
}
void recoveryCommitAndRestart() {
    Fixture fixture; seedQueue(fixture.root);
    bool observed = true;
    {
        NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false});
        startAndAdopt(capture, 2);
        const auto before = NativeCaptureStorageTestPeer::projection(capture);
        assert(before->items().size() == 2 && before->items()[0].status == UploadQueueStatus::needsAuth);
        observed = observed && capture.localObservation().value == before && capture.localObservation().complete;
        observed = observed && capture.custodySummary() == L"Нужен вход — локальные записи ждут отправки" &&
            capture.custodyAttentionCount() == 1;
        capture.recover(RecoveryTrigger::authRecovered); // Actual production event caller.
        capture.pollUploads();
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
        // No polling ACK yet: disk completion must not publish a private candidate.
        assert(NativeCaptureStorageTestPeer::projection(capture) == before);
        assert(NativeCaptureStorageTestPeer::generation(capture) == 2);
        assert(!capture.updateWorkDrained());
        const auto pending = capture.localObservation();
        observed = observed && pending.value == before && !pending.complete;
        observed = observed && capture.custodySummary() == L"Проверяем состояние локальных записей. Записи не изменены." &&
            capture.custodyAttentionCount() == 1;
        capture.setAuthSessionToken("generated-not-a-session");
        capture.setAuthSessionToken({}); // Clear before poll, so no network/auth IO.
        capture.pollUploads();
        const auto ticket = NativeCaptureStorageTestPeer::ticket(capture); assert(ticket);
        assert(ticket->state == NativeCapture::QueueTicketState::committed && ticket->changed);
        assert(ticket->baseGeneration == 2 && ticket->targetGeneration == 3);
        assert(ticket->epoch != capture.authGeneration()); // Physical truth, no stale capability.
        const auto after = NativeCaptureStorageTestPeer::projection(capture);
        assert(waitFor([&] { return capture.updateWorkDrained(); })); // Pure wait; no new dispatch.
        observed = observed && capture.localObservation().value == after && capture.localObservation().complete;
        observed = observed && capture.custodySummary() == L"Локальные записи ждут входа в аккаунт.";
        assert(after != before && before->items()[0].status == UploadQueueStatus::needsAuth);
        assert(after->items()[0].status == UploadQueueStatus::retry && after->items()[0].safeReason == "auth_recovered");
        assert(after->items()[0].ownerUserId == before->items()[0].ownerUserId);
        assert(after->items()[0].ownerWorkspaceId == before->items()[0].ownerWorkspaceId);
        assert(after->items()[0].acceptedBytes == before->items()[0].acceptedBytes && after->items()[0].attempts == 3);
        assert(after->items()[1].status == UploadQueueStatus::uploaded && after->items()[1].updatedAtMs == 1000);
        assert(after->deletionOperations().size() == 1 && after->purgeAcknowledgements().size() == 1);
        assert(after->deletionOperations()[0].operationId == before->deletionOperations()[0].operationId);
        assert(after->purgeAcknowledgements()[0].acknowledgedAtMs == 900);
        assert(capture.localItems().empty() && !capture.localQueueComplete() && !capture.uploadsBusy());
        assert(!capture.readiness().storageWritable);
        assert(!capture.requestProtectedManualSend(before, "waiting", capture.authGeneration() + 1, false));
        assert(capture.record().reason == ReasonCode::storageUnavailable);
        const auto disk = snapshot(fixture.root);
        capture.recover(RecoveryTrigger::authRecovered);
        assert(waitFor([&] {
            capture.pollUploads(); const auto current = NativeCaptureStorageTestPeer::ticket(capture);
            return current && current->id != ticket->id && current->state != NativeCapture::QueueTicketState::pending;
        }));
        const auto noop = NativeCaptureStorageTestPeer::ticket(capture); assert(noop);
        assert(noop->state == NativeCapture::QueueTicketState::notCommitted && !noop->changed);
        assert(noop->error == CustodyFileError::none && noop->baseGeneration == 3 && noop->targetGeneration == 3);
        assert(snapshot(fixture.root) == disk);
        assert(waitFor([&] { return capture.updateWorkDrained(); }));
        observed = observed && capture.localObservation().value == after && capture.localObservation().complete;
        capture.setUpdateAdmissionBlocked(true);
        observed = observed && !capture.localObservation().value && !capture.localObservation().complete;
        assert(waitFor([&] { capture.pollUploads(); return capture.updateWorkDrained(); }));
        capture.shutdown();
    }
    NativeCapture restarted(fixture.root, {std::make_shared<GeneratedAec>(), false});
    startAndAdopt(restarted, 3);
    observed = observed && restarted.localObservation().value == NativeCaptureStorageTestPeer::projection(restarted) &&
        restarted.localObservation().complete;
    assert(NativeCaptureStorageTestPeer::projection(restarted)->items()[0].status == UploadQueueStatus::retry);
    restarted.shutdown();
    assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(restarted); }));
    assert(observed && "protected_observation_preserves_adopted_generation_and_pending");
}
void allocationFailurePreservesProjection() {
    Fixture fixture; seedQueue(fixture.root);
    NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false});
    startAndAdopt(capture, 2);
    const auto before = NativeCaptureStorageTestPeer::projection(capture);
    const auto disk = snapshot(fixture.root);
    CustodyAllocator<char> allocator;
    const auto count = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
    auto* reservation = allocator.allocate(count);
    capture.recover(RecoveryTrigger::authRecovered);
    capture.pollUploads(); // Scalar dispatch needs no new charged allocation.
    assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
    const bool failedBeforeAck = !capture.localObservation().value && !capture.localObservation().complete;
    allocator.deallocate(reservation, count);
    capture.pollUploads();
    const auto ticket = NativeCaptureStorageTestPeer::ticket(capture); assert(ticket);
    assert(ticket->state == NativeCapture::QueueTicketState::notCommitted && ticket->error == CustodyFileError::allocationFailed);
    assert(NativeCaptureStorageTestPeer::projection(capture) == before && NativeCaptureStorageTestPeer::generation(capture) == 2);
    assert(snapshot(fixture.root) == disk && !capture.localQueueComplete());
    assert(waitFor([&] { return capture.updateWorkDrained(); }));
    const bool failedAfterAck = !capture.localObservation().value && !capture.localObservation().complete;
    const bool failedSummary = capture.custodySummary() == L"Защищённое локальное хранилище недоступно. Записи не изменены." &&
        capture.custodyAttentionCount() == 1;
    capture.shutdown();
    assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(capture); }));
    assert(failedBeforeAck && failedAfterAck && failedSummary && "protected_observation_hides_failed_retained_projection");
}
void nativeCommitCuts() {
    for (const auto cut : {IoCut::flush, IoCut::ambiguousRename, IoCut::pauseAfterFlush, IoCut::pauseAfterRename}) {
        Fixture fixture; seedQueue(fixture.root);
        bool observed = true;
        {
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false});
            startAndAdopt(capture, 2);
            const auto before = NativeCaptureStorageTestPeer::projection(capture);
            { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
            ioCut.store(cut);
            capture.recover(RecoveryTrigger::authRecovered);
            capture.pollUploads();
            const bool paused = cut == IoCut::pauseAfterFlush || cut == IoCut::pauseAfterRename;
            if (paused) {
                assert(waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }));
                assert(!capture.updateWorkDrained());
                const auto pending = capture.localObservation();
                observed = pending.value == before && !pending.complete;
                capture.setUpdateAdmissionBlocked(true); // Real cancel/close while IO is outstanding.
                observed = observed && !capture.localObservation().value && !capture.localObservation().complete;
                { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; cutWake.notify_all(); }
                assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(capture); }));
            } else assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            ioCut.store(IoCut::none);
            capture.pollUploads();
            const auto ticket = NativeCaptureStorageTestPeer::ticket(capture); assert(ticket);
            if (cut == IoCut::pauseAfterRename) {
                assert(ticket->state == NativeCapture::QueueTicketState::committed && ticket->targetGeneration == 3);
                assert(NativeCaptureStorageTestPeer::projection(capture)->items()[0].status == UploadQueueStatus::retry);
            } else {
                assert(ticket->state == (cut == IoCut::ambiguousRename ? NativeCapture::QueueTicketState::ambiguous : NativeCapture::QueueTicketState::notCommitted));
                assert(NativeCaptureStorageTestPeer::projection(capture) == before);
            }
            assert(!capture.localQueueComplete() && !capture.uploadsBusy());
            observed = observed && !capture.localObservation().value && !capture.localObservation().complete;
            capture.shutdown();
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(capture); }));
        }
        // The ambiguous rename did publish bytes: only genuine restart may
        // reconcile that generation, never the failed caller's success path.
        NativeCapture restarted(fixture.root, {std::make_shared<GeneratedAec>(), false});
        const bool physicallyPublished = cut == IoCut::ambiguousRename || cut == IoCut::pauseAfterRename;
        startAndAdopt(restarted, physicallyPublished ? 3 : 2);
        observed = observed && restarted.localObservation().value == NativeCaptureStorageTestPeer::projection(restarted) &&
            restarted.localObservation().complete;
        assert(NativeCaptureStorageTestPeer::projection(restarted)->items()[0].status ==
            (physicallyPublished ? UploadQueueStatus::retry : UploadQueueStatus::needsAuth));
        restarted.shutdown();
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(restarted); }));
        assert(observed && "protected_observation_rejects_failed_or_stopped_commit");
    }
}
void coalescedIntentAndLostOwner() {
    Fixture fixture; seedQueue(fixture.root);
    const auto baseline = CustodyOwnedMemory::usedBytes();
    {
        auto capture = std::make_unique<NativeCapture>(fixture.root, AecSelection{std::make_shared<GeneratedAec>(), false});
        capture->recover(RecoveryTrigger::authRecovered); // Before actual startup; no invented context/base.
        capture->setAuthSessionToken("generated-not-a-session");
        capture->setAuthSessionToken({});
        capture->recover(RecoveryTrigger::authRecovered); // Latest scalar epoch replaces the old intent.
        startAndAdopt(*capture, 2);
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(*capture); }));
        assert(NativeCaptureStorageTestPeer::generation(*capture) == 2);
        const auto ticket = NativeCaptureStorageTestPeer::ticket(*capture); assert(ticket);
        assert(ticket->state == NativeCapture::QueueTicketState::pending && ticket->epoch == capture->authGeneration());
        capture.reset(); // No completion poll: worker must reconcile before its last native release.
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
    }
    NativeCapture restarted(fixture.root, {std::make_shared<GeneratedAec>(), false});
    startAndAdopt(restarted, 3);
    assert(NativeCaptureStorageTestPeer::projection(restarted)->items()[0].status == UploadQueueStatus::retry);
    restarted.shutdown();
    assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(restarted); }));
}
void shutdownRecoveryAdmission() {
    for (const bool accepted : {false, true}) {
        Fixture fixture; seedQueue(fixture.root);
        NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false});
        startAndAdopt(capture, 2);
        const auto before = NativeCaptureStorageTestPeer::projection(capture);
        capture.recover(RecoveryTrigger::authRecovered);
        if (accepted) capture.pollUploads(); // Actual submission, not a test ticket.
        capture.requestShutdown(); // App-level accepted deletion may still be running.
        const bool exitClosed = !capture.localObservation().value && !capture.localObservation().complete;
        assert(waitFor([&] {
            capture.pollUploads();
            if (!accepted) {
                assert(!NativeCaptureStorageTestPeer::ticket(capture));
                assert(NativeCaptureStorageTestPeer::projection(capture) == before);
                return true;
            }
            return NativeCaptureStorageTestPeer::generation(capture) == 3;
        }));
        if (accepted) assert(NativeCaptureStorageTestPeer::ticket(capture)->state ==
            NativeCapture::QueueTicketState::committed);
        capture.shutdown();
        assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        assert(exitClosed && !capture.localObservation().value && !capture.localObservation().complete);
        NativeCapture restarted(fixture.root, {std::make_shared<GeneratedAec>(), false});
        startAndAdopt(restarted, accepted ? 3 : 2);
        assert(NativeCaptureStorageTestPeer::projection(restarted)->items()[0].status ==
            (accepted ? UploadQueueStatus::retry : UploadQueueStatus::needsAuth));
        restarted.shutdown();
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(restarted); }));
    }
}
void birthAndRestart() {
    Fixture fixture;
    Snapshot first;
    bool observed = true;
    for (int restart = 0; restart != 2; ++restart) {
        NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false});
        observed = observed && !capture.localObservation().value && !capture.localObservation().complete;
        if (restart == 0) assert(!std::filesystem::exists(fixture.root)); // Constructor does no IO.
        capture.startStorageValidation();
        capture.startStorageValidation(); // A repeated shell activation cannot birth twice.
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::ready(capture); }));
        assert(NativeCaptureStorageTestPeer::opened(capture));
        assert(NativeCaptureStorageTestPeer::generation(capture) == 0); // No ACK yet.
        observed = observed && !capture.localObservation().value && !capture.localObservation().complete;
        assert(!capture.updateWorkDrained());
        assert(!capture.readiness().storageWritable && !capture.localQueueComplete());
        assert(capture.record().reason == ReasonCode::storageUnavailable);
        const auto custody = fixture.root / L".custody-v1";
        for (const auto* role : {L"bootstrap", L"queue"}) {
            assert(std::filesystem::file_size(custody / role / L"id.bin") == 16);
            for (const auto* slot : {L"index.0", L"index.1"}) assert(std::filesystem::is_regular_file(custody / role / slot));
            const auto id = CreateFileW((custody / role / L"id.bin").c_str(), GENERIC_READ | GENERIC_WRITE,
                FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
            assert(id == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
        }
        assert(!std::filesystem::exists(fixture.root / std::string(kQueueLedgerFileName)));
        capture.pollUploads();
        assert(NativeCaptureStorageTestPeer::generation(capture) == 1);
        observed = observed && capture.localObservation().value == NativeCaptureStorageTestPeer::projection(capture) &&
            capture.localObservation().complete;
        observed = observed && capture.custodySummary() == L"Локальная очередь пуста" && capture.custodyAttentionCount() == 0;
        capture.pollUploads(); // Adoption is idempotent, not another physical commit.
        assert(NativeCaptureStorageTestPeer::generation(capture) == 1);
        capture.setUpdateAdmissionBlocked(true);
        observed = observed && !capture.localObservation().value && !capture.localObservation().complete;
        assert(waitFor([&] { capture.pollUploads(); return capture.updateWorkDrained(); }));
        assert(NativeCaptureStorageTestPeer::released(capture));
        capture.setUpdateAdmissionBlocked(false);
        capture.pollUploads(); // Replace the old stopped work, but do not ACK the new work.
        observed = observed && !capture.localObservation().value && !capture.localObservation().complete;
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::ready(capture); }));
        observed = observed && !capture.localObservation().value && !capture.localObservation().complete;
        capture.pollUploads();
        assert(NativeCaptureStorageTestPeer::generation(capture) == 1 && !NativeCaptureStorageTestPeer::released(capture));
        observed = observed && capture.localObservation().value == NativeCaptureStorageTestPeer::projection(capture) &&
            capture.localObservation().complete;
        const auto current = snapshot(fixture.root);
        if (restart == 0) first = current; else assert(current == first);
        capture.shutdown();
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(capture); }));
        // Independently decode BOTH durable payloads after the actual owner has
        // drained. Native proofs are created/released on this test worker only.
        auto verified = std::async(std::launch::async, [root = fixture.root] {
            auto cancellation = std::make_shared<std::atomic<bool>>(false);
            auto bootstrap = ProtectedCustodyBootstrapPair::read(root, cancellation);
            if (!bootstrap.ok() || (*bootstrap.value)->current().mode != CustodyBootstrapMode::protectedStore) return false;
            auto input = ProtectedCustodyQueueInput::read(*bootstrap.value, cancellation);
            if (!input.ok()) return false;
            auto queue = ProtectedUploadQueueCandidate::read(*input.value, cancellation);
            return queue.ok() && (*queue.value)->items().empty() && (*queue.value)->deletionOperations().empty()
                && (*queue.value)->purgeAcknowledgements().empty() && !(*queue.value)->legacy();
        });
        assert(verified.get());
    }
    assert(observed && "protected_observation_requires_current_startup_adoption");
}
void unknownRootIsPreserved() {
    Fixture fixture;
    assert(CreateDirectoryW(fixture.root.c_str(), nullptr));
    const auto path = fixture.root / L"unknown.bin";
    const auto file = CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
    assert(file != INVALID_HANDLE_VALUE);
    constexpr char bytes[] = "generated unknown inventory";
    DWORD written = 0;
    assert(WriteFile(file, bytes, sizeof(bytes), &written, nullptr) && written == sizeof(bytes));
    assert(FlushFileBuffers(file) && CloseHandle(file));
    const auto before = snapshot(fixture.root);
    NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false});
    capture.startStorageValidation();
    assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(capture); }));
    capture.pollUploads();
    assert(NativeCaptureStorageTestPeer::generation(capture) == 0);
    assert(!capture.localQueueComplete() && !capture.readiness().storageWritable);
    assert(!capture.localObservation().value && !capture.localObservation().complete);
    assert(snapshot(fixture.root) == before);
    assert(!std::filesystem::exists(fixture.root / L".custody-v1"));
    capture.shutdown();
}

void blockedRecordingDrains() {
    Fixture fixture;
    NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), true});
    startAndAdopt(capture, 1);
    assert(NativeCaptureStorageTestPeer::requestRecording(capture));
    assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::prepared(capture); }));
    ReadinessInputs denied; // Hardware denial, never a caller-created storage proof.
    const auto result = NativeCaptureStorageTestPeer::startPrepared(capture, denied);
    assert(result.accepted() && result.state == SessionState::blocked);
    capture.shutdown();
    assert(!capture.shutdownWorkDrained());
    assert(waitFor([&] {
        capture.pollHealth(); capture.pollUploads();
        return capture.shutdownWorkDrained();
    }, std::chrono::seconds(180)));
    assert(!capture.localQueueComplete());
}

void protectedPackageDiscovery() {
    auto worker = std::async(std::launch::async, [] {
        for (unsigned cut = 0; cut < 13; ++cut) {
            Fixture fixture;
            auto cancel = std::make_shared<std::atomic<bool>>(false);
            CustodyContext context{}, queue{};
            {
                auto store = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(store.ok());
                queue = (*store.value)->queueContext();
                auto package = (*store.value)->createPackage("package-a", cancel); assert(package.ok());
                auto pair = (*package.value)->readPair(); assert(pair.ok());
                context = (*pair.value)->current().context; // Mutation/exclusion fixture only, never a discovery input.
            }
            auto directory = std::string("package-a");
            const auto metadata = fixture.root / L"package-a" / L".custody-v1" / L"package-state";
            const auto id = metadata / L"id.bin";
            const auto replaceId = [&](const CustodyId& value, std::size_t length = 16) {
                std::ofstream output(id, std::ios::binary | std::ios::trunc);
                output.write(reinterpret_cast<const char*>(value.data()), static_cast<std::streamsize>(length));
                output.close(); assert(output);
            };
            switch (cut) {
            case 1: assert(std::filesystem::remove(id)); break;
            case 2: replaceId(context.objectId, 15); break;
            case 3: replaceId({}); break;
            case 4: replaceId(context.storeId); break;
            case 5: replaceId(queue.objectId); break;
            case 6: {
                CustodyId bootstrap{};
                std::ifstream input(fixture.root / L".custody-v1" / L"bootstrap" / L"id.bin", std::ios::binary);
                input.read(reinterpret_cast<char*>(bootstrap.data()), 16); assert(input);
                replaceId(bootstrap); break;
            }
            case 7: { auto wrong = context.objectId; wrong[0] ^= 1; replaceId(wrong); break; }
            case 8: assert(CreateHardLinkW((fixture.parent / L"identity-link").c_str(), id.c_str(), nullptr)); break;
            case 9: assert(std::filesystem::remove(metadata / L"index.0")); break;
            case 10: assert(std::filesystem::remove(metadata / L"index.1")); break;
            case 11: {
                std::ofstream output(metadata / L"index.0", std::ios::binary | std::ios::trunc);
                output.put('\0'); output.close(); assert(output); break;
            }
            case 12:
                std::filesystem::rename(fixture.root / L"package-a", fixture.root / L"other");
                directory = "other"; break;
            default: break;
            }
            const auto before = snapshot(fixture.root);
            auto store = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(store.ok());
            auto pair = (*store.value)->readPackage(directory, cancel);
            if (cut) {
                assert(!pair.ok() && pair.error != CustodyFileError::none);
            } else {
                assert(pair.ok() && (*pair.value)->current().phase == CustodyPackagePhase::capturing);
                assert((*pair.value)->current().context.objectId == context.objectId);
                assert((*store.value)->queueGeneration() == 1);
                pair.value.reset();
                discoveryCancellation = cancel.get();
                discoveryReads = discoverySecondIndex = discoveryReadCut = 0;
                pair = (*store.value)->readPackage(directory, cancel); assert(pair.ok());
                const auto totalReads = discoveryReads.load(), secondIndex = discoverySecondIndex.load();
                assert(secondIndex > 1 && totalReads > secondIndex);
                pair.value.reset();
                for (const auto readCut : {1U, secondIndex, totalReads}) {
                    discoveryReads = discoverySecondIndex = discoveryFired = 0; discoveryReadCut = readCut;
                    const auto cancelled = (*store.value)->readPackage(directory, cancel);
                    assert(!cancelled.ok() && cancelled.error == CustodyFileError::ioFailed &&
                        cancelled.nativeError == ERROR_OPERATION_ABORTED && discoveryFired == readCut);
                    // Physical pair validation may finish this slot's DATA read
                    // before the semantic layer observes cancellation.
                    assert(discoveryReads >= readCut && discoveryReads <= totalReads);
                    cancel->store(false);
                    assert(ProtectedCustodyFiles::open(fixture.root, directory, context, CustodyFileAccess::writeExisting).ok());
                    assert(snapshot(fixture.root) == before);
                }
                discoveryCancellation = nullptr;
                for (const auto& invalid : std::array<std::string, 6>{"", "../", "a/b", "a\\b", std::string(301, 'a'), "\xc0"})
                    assert((*store.value)->readPackage(invalid, cancel).error == CustodyFileError::invalidInput);
                cancel->store(true);
                const auto cancelled = (*store.value)->readPackage(directory, cancel);
                assert(!cancelled.ok() && cancelled.nativeError == ERROR_OPERATION_ABORTED);
                cancel->store(false);
                {
                    std::array<CustodyNativeJob, 2> held;
                    for (const auto& job : held) assert(job);
                    auto admitted = (*store.value)->readPackage(directory, cancel); assert(admitted.ok());
                }
                {
                    std::array<CustodyNativeJob, 3> held;
                    for (const auto& job : held) assert(job);
                    assert((*store.value)->readPackage(directory, cancel).error == CustodyFileError::allocationFailed);
                }
                {
                    std::array<CustodyPin, 31> held;
                    for (const auto& pin : held) assert(pin);
                    assert((*store.value)->readPackage(directory, cancel).error == CustodyFileError::allocationFailed);
                }
                pair = (*store.value)->readPackage(directory, cancel); assert(pair.ok());
                store.value.reset();
                HANDLE competing = CreateFileW(id.c_str(), GENERIC_WRITE, FILE_SHARE_READ, nullptr,
                    OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
                assert(competing == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
                const auto storeId = fixture.root / L".custody-v1" / L"store.id";
                HANDLE rootWriter = CreateFileW(storeId.c_str(), GENERIC_WRITE, FILE_SHARE_READ, nullptr,
                    OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
                assert(rootWriter == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
                pair.value.reset();
                competing = CreateFileW(id.c_str(), GENERIC_WRITE, FILE_SHARE_READ, nullptr,
                    OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
                assert(competing != INVALID_HANDLE_VALUE); assert(CloseHandle(competing));
                rootWriter = CreateFileW(storeId.c_str(), GENERIC_WRITE, FILE_SHARE_READ, nullptr,
                    OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
                assert(rootWriter != INVALID_HANDLE_VALUE); assert(CloseHandle(rootWriter));
            }
            assert(snapshot(fixture.root) == before); // Discovery never repairs IDs/slots or publishes bytes.
        }
        std::fputs("PACKAGE_DISCOVERY generated_restart=1 cuts=12 cancellation=1 job_pin_refusal=1 retained_identity=1\n", stderr);
    });
    worker.get();
}

struct ProtectedUploadExpected {
    std::array<CustodyBytes,3> bytes;
    std::array<std::string,3> hashes;
};
ProtectedUploadExpected readProtectedUploadExpected(const Fixture& fixture,
    const std::shared_ptr<const ProtectedCustodyPackagePair>& pair,
    const std::shared_ptr<std::atomic<bool>>& cancellation) {
    auto readers = openProtectedCustodyReaders(fixture.root, pair, cancellation);
    assert(readers.ok());
    ProtectedUploadExpected expected;
    const auto& package = pair->current();
    constexpr std::array<CustodyRole,3> roles{CustodyRole::manifest, CustodyRole::media, CustodyRole::playback};
    for (std::size_t track = 0; track < roles.size(); ++track) {
        std::size_t i = 0;
        while (i < package.refCount && package.refs[i].role != roles[track]) ++i;
        assert(i < package.refCount && package.refs[i].sealed && package.refs[i].length);
        const auto size = *package.refs[i].length;
        auto* stream = readers.value->at(pair->selectedSlot()).at(i).stream.Get();
        assert(stream && size && size <= CustodyOwnedMemory::limit);
        const auto digest = sha256ProtectedStream(stream, size, cancellation);
        assert(digest.ok() && package.refs[i].sha256 && *digest.value == *package.refs[i].sha256);
        constexpr char hex[] = "0123456789abcdef";
        for (const auto byte : *digest.value) { expected.hashes[track] += hex[byte >> 4]; expected.hashes[track] += hex[byte & 15]; }
        auto& bytes = expected.bytes[track];
        bytes.resize(static_cast<std::size_t>(size));
        LARGE_INTEGER zero{};
        assert(stream->Seek(zero, STREAM_SEEK_SET, nullptr) == S_OK);
        for (std::size_t offset = 0; offset < bytes.size();) {
            const auto length = static_cast<ULONG>(std::min<std::size_t>(256 * 1024, bytes.size() - offset));
            ULONG got = 0;
            assert(stream->Read(bytes.data() + offset, length, &got) == S_OK && got == length);
            offset += got;
        }
        assert(sha256(std::string_view(reinterpret_cast<const char*>(bytes.data()), bytes.size())) == expected.hashes[track]);
    }
    // Close this independent reader group before semantic inspection opens its
    // genuine exclusive leases. Only charged generated bytes survive the return.
    return expected;
}

// This is the real transport integration, not protected scheduler acceptance.
// The later flight/result continuation must use this same wire seam.
void protectedUploadFromCold(const Fixture& fixture, const std::string& session,
    const DesktopAccountIdentity& account,
    const std::shared_ptr<const LocalRecordingPackage::ProtectedInspection>& proof,
    const ProtectedUploadExpected& expected,
    const std::shared_ptr<std::atomic<bool>>& cancellation, const ProtectedUploadQueueValue::Item& item) {
#if defined(_MSC_VER) && defined(_DEBUG)
    wchar_t executable[MAX_PATH]{};
    const auto executableLength = GetModuleFileNameW(nullptr, executable, MAX_PATH);
    assert(executableLength && executableLength < MAX_PATH);
    const auto symbols = std::filesystem::path(executable).parent_path();
    SymSetOptions(SYMOPT_UNDNAME | SYMOPT_LOAD_LINES | SYMOPT_DEFERRED_LOADS |
        SYMOPT_FAIL_CRITICAL_ERRORS | SYMOPT_NO_PROMPTS);
    assert(SymInitializeW(GetCurrentProcess(), symbols.c_str(), TRUE));
    struct SymbolCleanup { ~SymbolCleanup() { assert(SymCleanup(GetCurrentProcess())); } } symbolCleanup;
#endif
    constexpr std::array<std::string_view,3> names{"manifest", "media", "playback"};
    std::array<std::uint64_t,3> sizes{}, accepted{};
    for (std::size_t i = 0; i < sizes.size(); ++i) sizes[i] = expected.bytes[i].size();
    const auto& hashes = expected.hashes;
    ProtectedDesktopHttpConfig config;
    config.sessionToken = "generated-t116-session"; // Literal fixture, never a live credential.
    config.workspaceId = account.workspaceId;
    config.confirmedIdentity = BasicDesktopAccountIdentity<CustodyString>{CustodyString(account.userId), CustodyString(account.workspaceId)};
    config.cancellation = cancellation;
    config.partSizeBytes = 64 * 1024;
    unsigned sync = 0, create = 0, uploadSession = 0, ranges = 0, finalize = 0, parts = 0;
    std::optional<DesktopHttpTransport::ProtectedUploadRequest> retained;
    std::weak_ptr<const CustodyBytes> retainedOwner;
    std::string retainedHash;
    std::size_t retainedLength = 0;
    const char* retainedData = nullptr;
    const auto before = snapshot(fixture.root);
    using Response = DesktopHttpTransport::ProtectedUploadResponse;
    const auto number = [](CustodyString& body, std::uint64_t value) {
        char digits[20];
        const auto end = std::to_chars(std::begin(digits), std::end(digits), value);
        assert(end.ec == std::errc{}); body.append(digits, static_cast<std::size_t>(end.ptr - digits));
    };
    const auto ack = [&](std::uint64_t offset, std::uint64_t length) {
        Response reply{200, "{\"byte_offset\":"};
        number(reply.body, offset); reply.body += ",\"byte_length\":";
        number(reply.body, length); reply.body += '}';
        return reply;
    };
    struct CopyProbe {
        unsigned* copies;
        explicit CopyProbe(unsigned& count) : copies(&count) {}
        CopyProbe(const CopyProbe& other) : copies(other.copies) { ++*copies; }
    };
    unsigned copies = 0;
    const CopyProbe probe(copies);
    const DesktopHttpTransport::ProtectedUploadSend send = [&, probe](const auto& captured, const auto& request) -> Response {
        constexpr bool chargedControlTypes =
            std::is_same_v<std::decay_t<decltype(captured.baseOrigin)>, CustodyString> &&
            std::is_same_v<std::decay_t<decltype(captured.workspaceId)>, CustodyString> &&
            std::is_same_v<std::decay_t<decltype(captured.deviceId)>, CustodyString> &&
            std::is_same_v<std::decay_t<decltype(captured.clientVersion)>, CustodyString> &&
            std::is_same_v<std::decay_t<decltype(captured.sessionToken)>, CustodyString> &&
            std::is_same_v<std::decay_t<decltype(captured.confirmedIdentity->userId)>, CustodyString> &&
            std::is_same_v<std::decay_t<decltype(captured.confirmedIdentity->workspaceId)>, CustodyString> &&
            std::is_same_v<std::decay_t<decltype(captured.scopedAccount->userId)>, CustodyString> &&
            std::is_same_v<std::decay_t<decltype(captured.scopedAccount->workspaceId)>, CustodyString> &&
            std::is_same_v<std::decay_t<decltype(request.method)>, CustodyString> &&
            std::is_same_v<std::decay_t<decltype(request.path)>, CustodyString> &&
            std::is_same_v<std::decay_t<decltype(request.body)>, CustodyString> &&
            std::is_same_v<std::decay_t<decltype(request.idempotencyKey)>, CustodyString> &&
            std::is_same_v<std::decay_t<decltype(request.contentSha256)>, CustodyString>;
        std::fprintf(stderr, "PROTECTED_HTTP request_config_types_charged=%u enforced=%u\n",
            chargedControlTypes ? 1U : 0U, enforceProtectedHttpControlTypes ? 1U : 0U);
        std::fflush(stderr);
        assert(!enforceProtectedHttpControlTypes || chargedControlTypes);
        assert(probe.copies == &copies);
        assert(captured.sessionToken == config.sessionToken && !captured.cancellation->load());
        if (request.path.find("/sync-state?") != std::string::npos) {
            assert(request.method == "GET" && ++sync == 1);
            return {404, R"({"code":"recording_not_found"})"};
        }
        if (request.path == "/api/v1/meetings") {
            assert(request.method == "POST" && ++create == 1 && !request.idempotencyKey.empty());
            return {201, R"({"meeting_id":"generated-meeting"})"};
        }
        if (request.path == "/api/v1/meetings/generated-meeting/upload-sessions") {
            assert(request.method == "POST" && ++uploadSession == 1 && !request.idempotencyKey.empty());
            const auto body = request.bodyView(); assert(body);
            const auto fields = DesktopApiClient::jsonObjectFields(*body); assert(fields);
            assert(fields->at("manifest_sha256") == "\"" + hashes[0] + "\"");
            const auto tracks = DesktopApiClient::jsonArrayValues(fields->at("expected_tracks"));
            const auto declared = DesktopApiClient::jsonObjectFields(fields->at("expected_track_sizes"));
            assert(tracks && tracks->size() == 3 && declared && declared->size() == 3);
            for (std::size_t i = 0; i < names.size(); ++i) {
                assert(tracks->at(i) == "\"" + std::string(names[i]) + "\"");
                assert(declared->at(names[i]) == std::to_string(sizes[i]));
            }
            return {201, R"({"session_id":"generated-upload","accepted_bytes_by_track":{}})"};
        }
        if (request.path == "/api/v1/upload-sessions/generated-upload/missing-ranges") {
            assert(request.method == "GET" && ++ranges <= 2);
            if (ranges == 2) { assert(accepted == sizes); return {200, R"({"missing_ranges_by_track":{}})"}; }
            Response reply{200, "{\"missing_ranges_by_track\":{"};
            for (std::size_t i = 0; i < names.size(); ++i) {
                if (i) reply.body += ',';
                reply.body += '"'; reply.body += names[i]; reply.body += "\":[{\"start\":0,\"end\":";
                number(reply.body, sizes[i]); reply.body += "}]";
            }
            reply.body += "}}";
            return reply;
        }
        if (request.path == "/api/v1/upload-sessions/generated-upload/finalize") {
            assert(request.method == "POST" && ++finalize == 1 && ranges == 2 && accepted == sizes);
            const auto body = request.bodyView(); assert(body);
            const auto fields = DesktopApiClient::jsonObjectFields(*body); assert(fields);
            assert(fields->at("manifest_sha256") == "\"" + hashes[0] + "\"");
            const auto tracks = DesktopApiClient::jsonArrayValues(fields->at("tracks")); assert(tracks && tracks->size() == 3);
            constexpr std::array<std::string_view,3> codecs{"json", "wav-pcm-s16le", "m4a-aac-lc"};
            constexpr std::array<unsigned,3> rates{1,16000,48000}, durations{1,30,30};
            for (std::size_t i = 0; i < names.size(); ++i) {
                const auto track = DesktopApiClient::jsonObjectFields(tracks->at(i)); assert(track);
                assert(track->at("track_role") == "\"" + std::string(names[i]) + "\"");
                assert(track->at("sha256") == "\"" + hashes[i] + "\"");
                assert(track->at("byte_length") == std::to_string(sizes[i]));
                assert(track->at("codec") == "\"" + std::string(codecs[i]) + "\"");
                assert(track->at("sample_rate_hz") == std::to_string(rates[i]));
                assert(track->at("duration_seconds") == std::to_string(durations[i]) && track->at("channel_count") == "1");
            }
            return {200, "{}"};
        }
        assert(request.method == "PUT" && !request.jsonBody && request.byteOffset);
        std::size_t track = 0;
        while (track < names.size() && request.path.find("/tracks/" + std::string(names[track]) + "/parts/") == std::string::npos) ++track;
        assert(track < names.size() && *request.byteOffset == accepted[track]);
        const auto body = request.bodyView(); assert(body && !body->empty() && body->size() <= config.partSizeBytes);
        assert(request.body.empty()); // No second, uncharged plaintext string.
        const auto copy = request;
        assert(copy.bodyView() && copy.bodyView()->data() == body->data()); // Same owning buffer.
        assert(request.protectedBody && reinterpret_cast<const char*>(request.protectedBody->data()) == body->data());
        if (!retained) {
            retained = copy; retainedOwner = request.protectedBody;
            retainedHash = request.contentSha256; retainedLength = body->size(); retainedData = body->data();
        }
        assert(std::string_view(request.contentSha256) == sha256(*body));
        const auto prefix = "/api/v1/upload-sessions/generated-upload/tracks/" + std::string(names[track]) + "/parts/";
        assert(std::string_view(request.path) == prefix + std::to_string(*request.byteOffset / config.partSizeBytes));
        assert(body->size() == std::min<std::uint64_t>(config.partSizeBytes, sizes[track] - accepted[track]));
        const auto got = body->size();
        assert(std::memcmp(expected.bytes[track].data() + *request.byteOffset, body->data(), got) == 0);
        accepted[track] += got; ++parts;
        return ack(*request.byteOffset, got);
    };
    assert(std::string_view(item.sessionId) == session && std::string_view(item.ownerUserId) == account.userId &&
        std::string_view(item.ownerWorkspaceId) == account.workspaceId);
    std::fputs("PROTECTED_HTTP direct_charged_queue_item=pass\n", stderr);
    {
        auto uncancellable = config;
        uncancellable.cancellation.reset();
        unsigned calls = 0;
        const DesktopHttpTransport::ProtectedUploadSend wire = [&](const auto&, const auto&) -> Response { ++calls; return {}; };
        assert(!DesktopHttpTransport::uploadProtected(uncancellable, item, proof, wire) && calls == 0);
        std::fputs("PROTECTED_HTTP missing_cancellation_zero_wire=pass\n", stderr);
    }
    const auto preparedCopies = copies;
    const auto result = DesktopHttpTransport::uploadProtected(config, item, proof, send);
    assert(copies == preparedCopies);
    std::fputs("PROTECTED_HTTP response_direct_charged_wire=pass callback_not_copied=pass\n", stderr);
    assert(result && result->status == DesktopTransportStatus::uploaded && result->serverTruth && result->serverTruth->finalized);
    assert(result->serverTruth->acceptedBytes == sizes && sync == 1 && create == 1 && uploadSession == 1 && finalize == 1 && parts >= 3);
    assert(retained && !retainedOwner.expired() && retained->bodyView() && retained->bodyView()->data() == retainedData);
    assert(retained->bodyView()->size() == retainedLength && sha256(*retained->bodyView()) == retainedHash);
    const auto charged = CustodyOwnedMemory::usedBytes();
    retained.reset(); // Transport and all original requests have already ended.
    assert(retainedOwner.expired() && charged >= CustodyOwnedMemory::usedBytes() + retainedLength);
    retainedOwner.reset(); // Release the separately charged control block too.
    assert(snapshot(fixture.root) == before); // Transport itself never writes a plaintext copy/ledger.
    std::fputs("PROTECTED_HTTP actual_transport_bytes=pass protected_result_adoption=pending\n", stderr);

    // The same charged row must retain the ordinary protocol's replacement
    // key: repeated expiry reuses it; a different expired session changes it.
    for (const auto expired : {"generated-expired-one", "generated-expired-one", "generated-expired-two"}) {
        unsigned calls = 0;
        const DesktopHttpTransport::ProtectedUploadSend replacementWire = [&](const auto&, const auto& request) -> Response {
            if (++calls == 1) {
                assert(request.method == "GET" && request.path.find("/sync-state?") != std::string::npos);
                Response reply{200, R"({"meeting":{"meeting_id":"generated-meeting"},"upload_session":{"session_id":")"};
                reply.body += expired;
                reply.body += R"(","status":"expired","accepted_bytes_by_track":{}},"conflict":{"state":"upload_session_expired"}})";
                return reply;
            }
            assert(calls == 2 && request.method == "POST" && request.path == "/api/v1/meetings/generated-meeting/upload-sessions");
            const auto expectedKey = DesktopApiClient::idempotencyKey(
                std::string("upload-session-after-") + expired, item.directoryId, item.sessionId);
            assert(!expectedKey.empty() && std::string_view(request.idempotencyKey) == expectedKey);
            return {503, ""}; // No parts/finalize after the replacement is refused.
        };
        const auto replacement = DesktopHttpTransport::uploadProtected(config, item, proof, replacementWire);
        assert(calls == 2 && replacement && replacement->status == DesktopTransportStatus::retryableFailure &&
            replacement->serverTruth && replacement->serverTruth->meetingExists && !replacement->serverTruth->finalized);
        assert(snapshot(fixture.root) == before);
    }
    std::fputs("PROTECTED_HTTP charged_item_replacement_session_key=pass\n", stderr);

    // Exhaust admission BEFORE entering transport, without a confirmed account.
    // A late result owner would still perform the two identity GETs; refuse
    // instead with no request, then prove the identical control reaches them.
    auto unconfirmed = config;
    unconfirmed.confirmedIdentity.reset();
    unconfirmed.workspaceId.clear();
    unsigned earlyCalls = 0;
    const DesktopHttpTransport::ProtectedUploadSend earlyWire = [&](const auto&, const auto& request) -> Response {
        ++earlyCalls;
        if (earlyCalls == 1) {
            assert(request.path == "/desktop/settings/spaces");
            Response reply{200, "{\"spaces\":[{\"id\":\""};
            reply.body.append(account.workspaceId.data(), account.workspaceId.size()); reply.body += "\",\"active\":true}]}";
            return reply;
        }
        if (earlyCalls == 2) {
            assert(request.path == "/api/v1/auth/me");
            Response reply{200, "{\"user_id\":\""};
            reply.body.append(account.userId.data(), account.userId.size()); reply.body += "\",\"workspace_id\":\"";
            reply.body.append(account.workspaceId.data(), account.workspaceId.size());
            reply.body += "\",\"active_session_id\":\"33333333-3333-4333-8333-333333333333\"}";
            return reply;
        }
        assert(earlyCalls == 3 && request.path.find("/sync-state?") != std::string::npos);
        return {503, ""};
    };
    {
        CustodyBytes exhausted;
        exhausted.resize(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
        assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
        const auto refused = DesktopHttpTransport::uploadProtected(unconfirmed, item, proof, earlyWire);
        assert(!refused && earlyCalls == 0);
    }
    const auto admitted = DesktopHttpTransport::uploadProtected(unconfirmed, item, proof, earlyWire);
    assert(admitted && admitted->status == DesktopTransportStatus::retryableFailure &&
        !admitted->serverTruth && earlyCalls == 3);
    std::fputs("PROTECTED_HTTP preowned_admission_zero_wire_including_account=pass\n", stderr);

    std::size_t moveProxyAllowance = 0;
    {
        const auto chargedBefore = CustodyOwnedMemory::usedBytes();
        Response empty; moveProxyAllowance = CustodyOwnedMemory::usedBytes() - chargedBefore;
    }
    // The first account response returns successfully before pressure reaches
    // the parser. No auth/me, sync-state or mutation may follow that refusal.
    for (const bool knownWorkspace : {false, true}) {
        auto accountConfig = unconfirmed;
        if (knownWorkspace) accountConfig.workspaceId = account.workspaceId;
        std::optional<CustodyBytes> accountBudget;
        unsigned accountCalls = 0;
        bool accountReplyReturned = false;
        const DesktopHttpTransport::ProtectedUploadSend accountWire = [&](const auto& captured, const auto& request) -> Response {
            assert(request.method == "GET");
            if (++accountCalls != 1) {
                assert(accountCalls == 2 && (knownWorkspace
                    ? request.path.find("/sync-state?") != std::string::npos
                    : request.path == "/api/v1/auth/me"));
                return {401, ""}; // RED sentinel, never authority.
            }
            assert(captured.deviceId.empty());
            assert(request.path == (knownWorkspace ? "/api/v1/auth/me" : "/desktop/settings/spaces"));
            Response reply{200, knownWorkspace ? "{\"user_id\":\"" : "{\"spaces\":[{\"id\":\""};
            if (knownWorkspace) {
                reply.body.append(account.userId.data(), account.userId.size()); reply.body += "\",\"workspace_id\":\"";
            }
            reply.body.append(account.workspaceId.data(), account.workspaceId.size());
            reply.body += knownWorkspace
                ? "\",\"active_session_id\":\"33333333-3333-4333-8333-333333333333\"}"
                : "\",\"active\":true}]}";
            accountBudget.emplace();
            const auto available = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
            assert(available >= moveProxyAllowance);
            accountBudget->resize(available - moveProxyAllowance);
            assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit - moveProxyAllowance);
            struct ReturnProbe {
                bool& returned;
                int exceptions = std::uncaught_exceptions();
                ~ReturnProbe() noexcept { returned = std::uncaught_exceptions() == exceptions; }
            } returned{accountReplyReturned};
            return Response(std::move(reply));
        };
        const auto refused = DesktopHttpTransport::uploadProtected(accountConfig, item, proof, accountWire);
        const bool retryable = refused && refused->status == DesktopTransportStatus::retryableFailure;
        std::fprintf(stderr, "PROTECTED_HTTP account_parser_quota returned=%u calls=%u retryable=%u truth=%u known_workspace=%u\n",
            accountReplyReturned ? 1U : 0U, accountCalls, retryable ? 1U : 0U,
            refused && refused->serverTruth ? 1U : 0U, knownWorkspace ? 1U : 0U);
        assert(accountReplyReturned && accountCalls == 1 && retryable && !refused->serverTruth);
        accountBudget.reset();
        assert(snapshot(fixture.root) == before);
    }

    // A valid finalized sync response is data, not admission to allocate outside
    // the shared quota. The identical healthy control must still be accepted.
    for (const bool pressured : {false, true}) {
        std::optional<CustodyBytes> syncBudget;
        unsigned syncCalls = 0;
        bool syncReplyReturned = false;
        const DesktopHttpTransport::ProtectedUploadSend syncWire = [&](const auto&, const auto& request) -> Response {
            assert(++syncCalls == 1 && request.method == "GET" && request.path.find("/sync-state?") != std::string::npos);
            Response reply{200, R"({"meeting":{"meeting_id":"generated-existing","status":"ingested_pending_processing"},"conflict":{"state":"none"}})"};
            if (pressured) {
                syncBudget.emplace();
                const auto available = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
                assert(available >= moveProxyAllowance);
                syncBudget->resize(available - moveProxyAllowance);
                assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit - moveProxyAllowance);
            }
            struct ReturnProbe {
                bool& returned;
                int exceptions = std::uncaught_exceptions();
                ~ReturnProbe() noexcept { returned = std::uncaught_exceptions() == exceptions; }
            } returned{syncReplyReturned};
            return Response(std::move(reply));
        };
        const auto resolved = DesktopHttpTransport::uploadProtected(config, item, proof, syncWire);
        const bool retryable = resolved && resolved->status == DesktopTransportStatus::retryableFailure;
        const bool finalized = resolved && resolved->status == DesktopTransportStatus::uploaded &&
            resolved->serverTruth && resolved->serverTruth->finalized;
        std::fprintf(stderr, "PROTECTED_HTTP sync_owned_quota returned=%u calls=%u retryable=%u truth=%u pressured=%u finalized=%u\n",
            syncReplyReturned ? 1U : 0U, syncCalls, retryable ? 1U : 0U,
            resolved && resolved->serverTruth ? 1U : 0U, pressured ? 1U : 0U, finalized ? 1U : 0U);
        assert(syncReplyReturned && syncCalls == 1 && (pressured
            ? retryable && !resolved->serverTruth : finalized));
        syncBudget.reset();
        assert(snapshot(fixture.root) == before);
    }

    enum class Cut { cancel, invalidRange, rangesQuota, bodyQuota, badAck, allocation, afterAckAllocation, terminalAllocation };
    for (const auto cut : {Cut::cancel, Cut::invalidRange, Cut::rangesQuota, Cut::bodyQuota, Cut::badAck, Cut::allocation, Cut::afterAckAllocation
#if defined(_MSC_VER) && defined(_DEBUG)
        , Cut::terminalAllocation
#endif
    }) {
        const bool afterAck = cut == Cut::afterAckAllocation || cut == Cut::terminalAllocation;
        std::optional<CustodyBytes> budget;
        std::weak_ptr<const CustodyBytes> bodyOwner;
        unsigned put = 0, missing = 0;
        bool replyReturned = false;
        const DesktopHttpTransport::ProtectedUploadSend faultWire = [&](const auto&, const auto& request) -> Response {
            assert(!cancellation->load());
            if (request.path.find("/sync-state?") != std::string::npos)
                return {404, R"({"code":"recording_not_found"})"};
            if (request.path == "/api/v1/meetings")
                return {201, R"({"meeting_id":"generated-meeting"})"};
            if (request.path == "/api/v1/meetings/generated-meeting/upload-sessions")
                return {201, R"({"session_id":"generated-upload","accepted_bytes_by_track":{}})"};
            if (request.path == "/api/v1/upload-sessions/generated-upload/missing-ranges") {
                if (++missing == 2) {
                    assert(afterAck);
                    std::fputs("PROTECTED_HTTP after_ack_allocation=armed\n", stderr);
#if defined(_MSC_VER) && defined(_DEBUG)
                    if (cut == Cut::terminalAllocation) {
                        terminalAllocation = {};
                        terminalAllocation.armed = true;
                    }
#endif
                    throw std::bad_alloc();
                }
                assert(missing == 1);
                if (cut == Cut::cancel) cancellation->store(true);
                Response reply{200, "{\"missing_ranges_by_track\":{\"manifest\":[{\"start\":0,\"end\":"};
                number(reply.body, sizes[0] + (cut == Cut::invalidRange ? 1 : 0)); reply.body += "}]";
                if (cut == Cut::bodyQuota) {
                    reply.body += ",\"media\":[{\"start\":0,\"end\":";
                    number(reply.body, sizes[1]); reply.body += "}]";
                }
                reply.body += "}}";
                if (cut == Cut::rangesQuota) {
                    budget.emplace();
                    const auto available = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
                    assert(available >= moveProxyAllowance);
                    budget->resize(available - moveProxyAllowance);
                    assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit - moveProxyAllowance);
                    struct ReturnProbe {
                        bool& returned;
                        int exceptions = std::uncaught_exceptions();
                        ~ReturnProbe() noexcept { returned = std::uncaught_exceptions() == exceptions; }
                    } returned{replyReturned};
                    return Response(std::move(reply)); // Exactly one move, independent of NRVO.
                }
                return reply;
            }
            assert(request.method == "PUT" && ++put == 1 &&
                (cut == Cut::bodyQuota || cut == Cut::badAck || cut == Cut::allocation || afterAck));
            const auto body = request.bodyView();
            assert(body && request.body.empty() && request.protectedBody && request.byteOffset == 0);
            assert(body->size() == sizes[0] && std::string_view(request.contentSha256) == hashes[0]);
            assert(std::memcmp(expected.bytes[0].data(), body->data(), body->size()) == 0);
            bodyOwner = request.protectedBody;
            if (cut == Cut::allocation) throw std::bad_alloc();
            if (cut == Cut::bodyQuota) {
                // Ranges parsing and the first real body already succeeded.
                // Leave room for ACK/control data, but not the next 64KiB part.
                auto reply = ack(0, body->size());
                budget.emplace();
                constexpr std::size_t headroom = 32 * 1024;
                const auto available = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
                assert(available > headroom && sizes[1] >= config.partSizeBytes);
                budget->resize(available - headroom);
                return reply;
            }
            return ack(afterAck ? 0 : 1, body->size());
        };
        const auto failed = DesktopHttpTransport::uploadProtected(config, item, proof, faultWire);
        if (cut == Cut::rangesQuota) {
            assert(replyReturned);
            std::fputs("PROTECTED_HTTP ranges_parser_owned_quota_reply_returned=pass\n", stderr);
        }
        if (cut == Cut::bodyQuota) {
            // A valid manifest ACK under pressure distinguishes this refusal
            // from the earlier ranges-parser cut. Even after cleanup the next
            // actual media part cannot fit; allocation precedes Seek/Read.
            const auto available = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
            assert(available >= 32 * 1024 && available < config.partSizeBytes);
            std::fprintf(stderr, "PROTECTED_HTTP request_body_quota_after_manifest_ack=pass available=%zu required=%zu\n",
                available, config.partSizeBytes);
        }
#if defined(_MSC_VER) && defined(_DEBUG)
        if (cut == Cut::terminalAllocation) assert(terminalAllocation.armed && !terminalAllocation.hit);
        terminalAllocation.armed = false; // Never fail an oracle/cleanup allocation.
        if (cut == Cut::terminalAllocation) {
            assert(!terminalAllocation.hit); // GREEN must not allocate a late terminal.
        }
#endif
        assert(failed && failed->status == ((cut == Cut::invalidRange || cut == Cut::badAck)
            ? DesktopTransportStatus::serverRejected : DesktopTransportStatus::retryableFailure));
        const std::array<std::uint64_t,3> acceptedBeforeFailure{afterAck || cut == Cut::bodyQuota ? sizes[0] : 0, 0, 0};
        assert((failed->serverTruth && std::string_view(failed->serverTruth->localRecordingId) == std::string_view(item.localRecordingId) &&
            failed->serverTruth->meetingExists && failed->serverTruth->uploadSessionExists &&
            !failed->serverTruth->finalized && failed->serverTruth->acceptedBytes == acceptedBeforeFailure));
        assert(missing == (afterAck ? 2U : 1U) && put == ((cut == Cut::bodyQuota || cut == Cut::badAck || cut == Cut::allocation || afterAck) ? 1U : 0U));
        assert(bodyOwner.expired());
        bodyOwner.reset(); budget.reset();
        cancellation->store(false); // Completed fixture call only; never revive a native request.
        assert(snapshot(fixture.root) == before);
    }
    // Live readers legitimately replace the retained cache block here. The
    // exact idle charge is checked by main after this worker releases the proof.
    std::fputs("PROTECTED_HTTP cancel_range_quota_ack_allocation=pass\n", stderr);
    std::fputs("PROTECTED_HTTP after_ack_allocation_retains_progress=pass\n", stderr);
#if defined(_MSC_VER) && defined(_DEBUG)
    std::fputs("PROTECTED_HTTP preowned_terminal_no_late_allocation=pass\n", stderr);
#endif
}

enum class VerticalCase { normal, staleEpoch, lostPoll, nativeStopFault, lateDevice, lateUi, ownedUpload, scheduledUpload };
auto generatedProducer(NativeCapture& capture, std::atomic<bool>& emit, AudioSource source, bool lateDevice = false) {
    return [&capture, &emit, source, lateDevice](const std::atomic_bool& running, std::atomic_bool& ready,
                                               const CaptureBatchCallback& callback) {
        ready.store(true);
        for (std::uint64_t frame = 0; frame != 3000 && running.load(); ++frame) {
            // Both sources together stay below 254 data packets + two EOS.
            while (running.load() && (!emit.load() ||
                frame > NativeCaptureStorageTestPeer::writtenFrames(capture) + 32))
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            if (!running.load()) return;
            AudioBatch batch{source, 48'000, 1, static_cast<std::int64_t>(frame * 480),
                1, 1, false, std::vector<float>(480), frame * 480};
            for (std::size_t sample = 0; sample != batch.samples.size(); ++sample)
                batch.samples[sample] = static_cast<float>(std::sin((frame * 480 + sample) * 0.017)) * 0.125F;
            callback(std::move(batch));
        }
        while (running.load()) std::this_thread::sleep_for(std::chrono::milliseconds(1));
        if (lateDevice && source == AudioSource::microphone)
            std::this_thread::sleep_for(std::chrono::milliseconds(5'200));
    };
}
void protectedPackageBirthAdmission() {
    const auto baseline = CustodyOwnedMemory::usedBytes();
    for (const bool busy : {false, true}) {
        Fixture fixture;
        auto worker = std::async(std::launch::async, [&] {
            auto cancellation = std::make_shared<std::atomic<bool>>(false);
            auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancellation);
            assert(opened.ok());
            std::optional<std::array<CustodyNativeJob, 2>> jobs;
            if (busy) {
                jobs.emplace();
                for (const auto& job : *jobs) assert(job);
            }
            auto package = (*opened.value)->createPackage("generated-birth-admission", cancellation);
            std::fprintf(stderr, "PROTECTED_BIRTH held_jobs=%u ok=%u error=%u native=%u\n",
                busy ? 2U : 0U, package.ok() ? 1U : 0U, static_cast<unsigned>(package.error), package.nativeError);
            std::fflush(stderr);
            assert(package.ok() && "package_birth_must_fit_two_available_native_jobs");
            assert((*package.value)->current().phase == CustodyPackagePhase::capturing &&
                (*package.value)->current().generation == 1);
        });
        worker.get();
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
    }
}
CustodyBytes readGeneratedManifest(const std::filesystem::path& root,
    const std::shared_ptr<const ProtectedCustodyPackagePair>& pair,
    const std::shared_ptr<const std::atomic<bool>>& cancellation,
    std::shared_ptr<ProtectedCustodyRecordingPackage> package = {}) {
    auto readers = package ? openProtectedCustodyReaders(package, pair, cancellation) :
        openProtectedCustodyReaders(root, pair, cancellation);
    if (!readers.ok()) std::fprintf(stderr, "PRIVACY_MANIFEST readers_error=%u native=%u\n",
        static_cast<unsigned>(readers.error), readers.nativeError);
    assert(readers.ok());
    const auto& current = pair->current();
    std::size_t ref = 0;
    while (ref != current.refCount && current.refs[ref].role != CustodyRole::manifest) ++ref;
    assert(ref != current.refCount && current.refs[ref].length && *current.refs[ref].length <= 65536);
    CustodyBytes bytes(static_cast<std::size_t>(*current.refs[ref].length)); ULONG got = 0;
    auto* stream = readers.value->at(pair->selectedSlot()).at(ref).stream.Get(); assert(stream);
    assert(stream->Read(bytes.data(), static_cast<ULONG>(bytes.size()), &got) == S_OK && got == bytes.size());
    std::uint8_t extra{};
    assert(stream->Read(&extra, 1, &got) == S_FALSE && got == 0);
    return bytes;
}
void protectedPrivacyManifest() {
    bool historyPresent = false;
    auto worker = std::async(std::launch::async, [&] {
        testing::GeneratedProtectedRecording recording("generated-privacy-history");
        recording.append(100);
        const auto result = recording.writer->finalize();
        assert(result.normalPackage() && result.durationMs == 1000);
        const auto before = snapshot(recording.paths.root);
        for (const bool close : {false, true}) {
            const auto refused = close ? recording.writer->closePrivacy(0, 0) : recording.writer->pausePrivacy(0, 0);
            assert(!refused.ok() && refused.error == CustodyFileError::writerFailed && snapshot(recording.paths.root) == before);
        }
        auto pair = recording.coldPair(); assert(pair.ok());
        const auto bytes = readGeneratedManifest(recording.paths.root, *pair.value, recording.cancel);
        const std::string_view json(reinterpret_cast<const char*>(bytes.data()), bytes.size());
        historyPresent = json.find("\"privacySegments\":[]") != std::string_view::npos;
        std::fprintf(stderr, "PRIVACY_MANIFEST cold_normal=1 empty_history_present=%u\n", historyPresent ? 1U : 0U);
        std::fflush(stderr);
    });
    worker.get(); // Dispose generated/native ownership before the named RED assertion.
    assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
    assert(historyPresent && "genuine_v5_writer_must_serialize_mac_privacy_history");
}
void protectedPrivacyCheckpoints() {
    auto worker = std::async(std::launch::async, [] {
        testing::GeneratedProtectedRecording recording("generated-privacy-history");
        constexpr std::uint64_t wall = 1767344400000, rollback = 1767340800000;
        const std::string open = R"({"segmentId":"generated-privacy-history-privacy-1","sessionId":"generated-privacy-history","control":"pause","startedAt":"2026-01-02T09:00:00Z","startMonotonicMs":100,"durationMs":0,"localMicTreatment":"silenced","initiator":"user","diagnosticSafe":true})";
        const std::string closed = R"({"segmentId":"generated-privacy-history-privacy-1","sessionId":"generated-privacy-history","control":"pause","startedAt":"2026-01-02T09:00:00Z","startMonotonicMs":100,"endedAt":"2026-01-02T08:00:00Z","endMonotonicMs":250,"durationMs":150,"localMicTreatment":"silenced","initiator":"user","diagnosticSafe":true})";
        const auto expectHistory = [&](std::string_view segment, bool cold = false) {
            auto pair = cold ? recording.coldPair() : recording.writer->package()->readPair(); assert(pair.ok());
            const auto bytes = readGeneratedManifest(recording.paths.root, *pair.value, recording.cancel,
                cold ? nullptr : recording.writer->package());
            const std::string_view json(reinterpret_cast<const char*>(bytes.data()), bytes.size());
            assert(json.find("\"privacySegments\":[" + std::string(segment) + "]") != std::string_view::npos);
            assert(json.find("0000000000000000000000000000000000000000000000000000000000000000") == std::string_view::npos);
        };
        auto before = snapshot(recording.paths.root);
        for (const bool close : {false, true}) {
            const auto bad = close ? recording.writer->closePrivacy(wall, UINT64_MAX) : recording.writer->pausePrivacy(UINT64_MAX, 100);
            assert(!bad.ok() && bad.error == CustodyFileError::invalidInput && bad.nativeError == 0);
        }
        assert(snapshot(recording.paths.root) == before);
        // Fail allocation before OPEN: retry must create segment1, not a phantom segment2.
        {
            const CustodyBytes pressure(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes()-4096);
            const auto refused = recording.writer->pausePrivacy(wall, 100);
            assert(!refused.ok() && refused.error == CustodyFileError::allocationFailed && refused.nativeError == 0);
        }
        assert(snapshot(recording.paths.root) == before);
        const auto paused = recording.writer->pausePrivacy(wall, 100); assert(paused.ok() && *paused.value);
        expectHistory(open);
        before = snapshot(recording.paths.root);
        const auto duplicate = recording.writer->pausePrivacy(wall, 100);
        assert(duplicate.ok() && !*duplicate.value && snapshot(recording.paths.root) == before);
        const auto invalidEnd = recording.writer->closePrivacy(rollback, 99);
        assert(!invalidEnd.ok() && invalidEnd.error == CustodyFileError::invalidInput && snapshot(recording.paths.root) == before);
        // A failed best-effort CLOSE keeps durable OPEN, but closes memory after
        // the caller's accepted boundary. Finalization must serialize that CLOSE.
        {
            const CustodyBytes pressure(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes()-4096);
            const auto refused = recording.writer->closePrivacy(rollback, 250);
            assert(!refused.ok() && refused.error == CustodyFileError::allocationFailed && refused.nativeError == 0);
        }
        assert(snapshot(recording.paths.root) == before);
        expectHistory(open);
        const auto alreadyClosed = recording.writer->closePrivacy(rollback, 250);
        assert(alreadyClosed.ok() && !*alreadyClosed.value && snapshot(recording.paths.root) == before);
        recording.append(100);
        const auto result = recording.writer->finalize(); assert(result.normalPackage() && result.durationMs == 1000);
        expectHistory(closed, true); // Genuine cold restart, actual final writer JSON and EOF.
        std::fputs("PRIVACY_HISTORY open_durable=1 close_allocation_failed_open_retained=1 memory_close_finalized=1 wall_rollback=1 cold_v5_valid=1\n", stderr);
    });
    worker.get();
    assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
}
void protectedPrivacyDegraded() {
    for (unsigned mode = 0; mode != 3; ++mode) {
        bool historyRetained = false;
        auto worker = std::async(std::launch::async, [&] {
            testing::GeneratedProtectedRecording recording("generated-privacy-degraded");
            constexpr std::uint64_t wall = 1767344400000;
            if (mode != 2) {
                const auto opened = recording.writer->pausePrivacy(wall, 100); assert(opened.ok() && *opened.value);
                if (mode == 1) {
                    const CustodyBytes pressure(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes()-4096);
                    const auto closed = recording.writer->closePrivacy(wall+100, 250);
                    assert(!closed.ok() && closed.error == CustodyFileError::allocationFailed);
                } else {
                    assert(recording.writer->closePrivacy(wall+100, 250).ok());
                    assert(recording.writer->pausePrivacy(wall+200, 300).ok());
                }
            }
            recording.append(100);
            const auto result = recording.writer->finalize(ReasonCode::clockDiscontinuity);
            assert(result.trustedPrefixRetained && result.semanticVerified && !result.normalPackage());
            auto pair = recording.coldPair(); assert(pair.ok());
            const auto& current = (*pair.value)->current();
            const bool hasManifest = std::any_of(current.refs.begin(), current.refs.begin()+current.refCount,
                [](const auto& ref) { return ref.role == CustodyRole::manifest; });
            if (hasManifest) {
                const auto bytes = readGeneratedManifest(recording.paths.root, *pair.value, recording.cancel);
                const std::string_view json(reinterpret_cast<const char*>(bytes.data()),bytes.size());
                assert(json.find("\"capture_status\":\"degraded\"") != std::string_view::npos);
                assert(json.find("\"capture_reason_code\":\"clock_discontinuity\"") != std::string_view::npos);
                assert(json.find("\"duration_ms\":1000") != std::string_view::npos && json.find("\"artifacts\":") == std::string_view::npos);
                assert(json.find("\"endMonotonicMs\":250,\"durationMs\":150") != std::string_view::npos || mode == 2);
                assert((json.find("generated-privacy-degraded-privacy-2") != std::string_view::npos) == (mode == 0));
                assert((json.find("\"startMonotonicMs\":300,\"durationMs\":0") != std::string_view::npos) == (mode == 0));
                assert((json.find("\"privacySegments\":[]") != std::string_view::npos) == (mode == 2));
                historyRetained = true;
            }
            auto inspected = LocalRecordingPackage::inspectProtected(recording.paths.root,*pair.value,recording.session,recording.cancel);
            assert(inspected.ok() && (*inspected.value)->evidence().integrity == PackageIntegrity::degraded &&
                (*inspected.value)->evidence().trustedPrefixFrames == 100 && (*inspected.value)->evidence().durationMs == 1000);
            std::fprintf(stderr,"PRIVACY_DEGRADED mode=%u cold_history=%u\n",mode,historyRetained ? 1U : 0U);
            std::fflush(stderr);
        });
        worker.get(); // Release all native/generated owners before qualified RED.
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        assert(historyRetained && "degraded_prefix_must_retain_protected_privacy_manifest");
    }
}
void protectedPrivacyDegradedCuts() {
    for (const bool after : {false,true}) {
        auto worker = std::async(std::launch::async, [after] {
            testing::GeneratedProtectedRecording recording("generated-privacy-degraded-cut");
            assert(recording.writer->pausePrivacy(1767344400000,100).ok());
            recording.append(100);
            liveMetadataRenameCount = 0; liveMetadataRenameAfter = after; degradedManifestRenameCut = true;
            const auto result = recording.writer->finalize(ReasonCode::clockDiscontinuity);
            degradedManifestRenameCut = false;
            assert(liveMetadataRenameCount == 1 && result.nativeError == 0xC0000022UL);
            assert(!result.semanticVerified && !result.trustedPrefixRetained && !result.normalPackage());
            const auto before = snapshot(recording.paths.root);
            const auto repeat = recording.writer->finalize();
            assert(!repeat.semanticVerified && repeat.packageGeneration == result.packageGeneration && snapshot(recording.paths.root) == before);
            auto pair = recording.coldPair(); assert(pair.ok());
            assert((*pair.value)->current().phase != CustodyPackagePhase::sealedNormal &&
                (*pair.value)->current().phase != CustodyPackagePhase::sealedDegraded);
            assert(!LocalRecordingPackage::inspectProtected(recording.paths.root,*pair.value,recording.session,recording.cancel).ok());
            std::fprintf(stderr,"DEGRADED_MANIFEST_CUT after=%u no_false_seal=1 no_blind_retry=1\n",after ? 1U : 0U);
        });
        worker.get();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
    }
}
void protectedPrivacyCapacity(bool degraded = false) {
    auto worker = std::async(std::launch::async, [degraded] {
        testing::GeneratedProtectedRecording recording("generated-privacy-capacity");
        unsigned count = 0;
        for (;;) {
            const auto before = snapshot(recording.paths.root);
            const auto wall = count ? 253402300799999ULL : 0ULL;
            const auto paused = recording.writer->pausePrivacy(wall, count*2);
            if (!paused.ok()) {
                assert(paused.error == CustodyFileError::invalidInput && paused.nativeError == 0);
                assert(count > 1 && snapshot(recording.paths.root) == before);
                const auto retry = recording.writer->pausePrivacy(wall, count*2);
                assert(!retry.ok() && retry.error == CustodyFileError::invalidInput && snapshot(recording.paths.root) == before);
                break;
            }
            assert(*paused.value);
            const auto closed = recording.writer->closePrivacy(wall, count*2+1);
            assert(closed.ok() && *closed.value); ++count;
            assert(count < 65536); // Test runaway guard only, never a product history cap.
        }
        recording.append(100);
        const auto result = recording.writer->finalize(degraded ? ReasonCode::clockDiscontinuity : ReasonCode::none);
        assert(degraded ? result.trustedPrefixRetained && !result.normalPackage() : result.normalPackage());
        auto pair = recording.coldPair(); assert(pair.ok());
        auto inspection = LocalRecordingPackage::inspectProtected(recording.paths.root, *pair.value, recording.session, recording.cancel);
        assert(inspection.ok() && (*inspection.value)->evidence().integrity == (degraded ? PackageIntegrity::degraded : PackageIntegrity::valid));
        inspection.value.reset(); // Retire its whole reader group before opening another under the 32-owner limit.
        const auto bytes = readGeneratedManifest(recording.paths.root, *pair.value, recording.cancel);
        const std::string_view json(reinterpret_cast<const char*>(bytes.data()), bytes.size());
        std::size_t found = 0, cursor = 0;
        while ((cursor = json.find("\"control\":\"pause\"", cursor)) != std::string_view::npos) { ++found; ++cursor; }
        assert(found == count && bytes.size() <= 65536);
        assert(json.find("1970-01-01T00:00:00Z") != std::string_view::npos);
        assert(json.find("9999-12-31T23:59:59Z") != std::string_view::npos);
        std::fprintf(stderr, "PRIVACY_HISTORY capacity_segments=%u bytes=%zu degraded=%u no_trim=1 finalization_reserved=1\n", count, bytes.size(),degraded ? 1U : 0U);
    });
    worker.get();
    assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
}
void protectedPrivacyCloseCuts() {
    auto worker = std::async(std::launch::async, [] {
        for (const bool after : {false, true}) for (unsigned cut = 1; cut <= 3; ++cut) {
            testing::GeneratedProtectedRecording recording("generated-privacy-cuts");
            const auto paused = recording.writer->pausePrivacy(1767344400000, 100); assert(paused.ok() && *paused.value);
            liveMetadataRenameCount = 0; liveMetadataRenameAfter = after; liveMetadataRenameTarget = cut;
            const auto closed = recording.writer->closePrivacy(1767344401000, 250);
            liveMetadataRenameTarget = 0;
            assert(!closed.ok() && closed.nativeError == 0xC0000022UL && liveMetadataRenameCount == cut);
            const auto before = snapshot(recording.paths.root);
            const auto retry = recording.writer->closePrivacy(1767344401000, 250);
            assert(!retry.ok() && retry.error == CustodyFileError::writerFailed && snapshot(recording.paths.root) == before);
            auto pair = recording.coldPair(); assert(pair.ok());
            auto readers = openProtectedCustodyReaders(recording.paths.root, *pair.value, recording.cancel); assert(readers.ok());
            bool openRetained = false;
            for (unsigned slot = 0; slot != 2; ++slot) {
                const auto& value = (*pair.value)->slots()[slot];
                std::size_t ref = 0;
                while (ref != value.refCount && value.refs[ref].role != CustodyRole::manifest) ++ref;
                if (ref == value.refCount) {
                    // First OPEN binds one slot only. A fault before CLOSE's
                    // pre-sync may leave its nonselected birth predecessor.
                    assert(!after && cut == 1 && slot != (*pair.value)->selectedSlot());
                    continue;
                }
                assert(value.refs[ref].length);
                CustodyBytes bytes(static_cast<std::size_t>(*value.refs[ref].length)); ULONG got = 0;
                auto* stream = readers.value->at(slot).at(ref).stream.Get(); assert(stream);
                assert(stream->Read(bytes.data(), static_cast<ULONG>(bytes.size()), &got) == S_OK && got == bytes.size());
                const std::string_view json(reinterpret_cast<const char*>(bytes.data()), bytes.size());
                assert(json.find("\"segmentId\":\"generated-privacy-cuts-privacy-1\"") != std::string_view::npos);
                const bool isOpen = json.find("\"endMonotonicMs\"") == std::string_view::npos;
                assert(json.find(isOpen ? "\"durationMs\":0" : "\"endMonotonicMs\":250,\"durationMs\":150") != std::string_view::npos);
                openRetained |= isOpen;
                if (slot == (*pair.value)->selectedSlot()) assert(isOpen == !(after && cut == 3));
                std::uint8_t extra{}; assert(stream->Read(&extra, 1, &got) == S_FALSE && got == 0);
            }
            assert(openRetained && snapshot(recording.paths.root) == before);
            std::fprintf(stderr, "PRIVACY_HISTORY close_cut=%u after=%u exact_fault=1 old_open_retained=1 no_blind_retry=1\n", cut, after);
        }
    });
    worker.get();
    assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
}
void protectedLiveMetadataCheckpoint() {
    const auto baseline = CustodyOwnedMemory::usedBytes();
    auto expectedIdle = baseline;
    bool committed = false, coldReadable = false;
    {
        auto worker = std::async(std::launch::async, [&] {
            testing::GeneratedProtectedRecording recording("generated-live-checkpoint");
            auto package = recording.writer->package();
            auto unchanged = package->current(); ++unchanged.generation;
            assert(package->commit(unchanged).state == CustodyCommitState::notCommitted);
            // Opaque generated metadata tests storage, NOT the logical v5
            // privacy model, a recording-ready flag or Pause acceptance.
            CustodyBytes latest;
            for (unsigned step = 0; step != 5; ++step) {
                const std::string value = "{\"generated_checkpoint\":" + std::to_string(step) + "}";
                latest.assign(value.begin(), value.end());
                if (step == 4) latest.resize(65536, ' ');
                const auto beforePressure = snapshot(recording.paths.root);
                {
                    std::array<CustodyNativeJob, 4> jobs;
                    for (const auto& job : jobs) assert(job);
                    assert(package->commitMetadata(CustodyRole::manifest, latest).state == CustodyCommitState::notCommitted);
                }
                assert(snapshot(recording.paths.root) == beforePressure);
                std::optional<std::array<CustodyNativeJob, 2>> jobs(std::in_place);
                for (const auto& job : *jobs) assert(job);
                const auto saved = package->commitMetadata(CustodyRole::manifest, latest);
                jobs.reset();
                std::fprintf(stderr, "LIVE_METADATA step=%u state=%u error=%u native=%u\n", step,
                    static_cast<unsigned>(saved.state), static_cast<unsigned>(saved.error), saved.nativeError);
                std::fflush(stderr);
                if (saved.state != CustodyCommitState::committed) return;
                assert(saved.snapshot && saved.snapshot->state == CustodySnapshotState::verified);
                assert(package->current().phase == CustodyPackagePhase::capturing);
                auto pair = package->readPair(); assert(pair.ok());
                auto readers = openProtectedCustodyReaders(package, *pair.value, recording.cancel);
                assert(readers.ok()); // Both state slots and their actual member closures.
                expectedIdle = idleOwnedBytes; // Existing static ReadCache's measured empty Debug proxy.
                const auto slot = (*pair.value)->selectedSlot();
                const auto& current = (*pair.value)->current();
                std::size_t ref = 0;
                while (ref != current.refCount && current.refs[ref].role != CustodyRole::manifest) ++ref;
                assert(ref != current.refCount && current.refs[ref].generation == saved.targetGeneration);
                CustodyBytes actual(latest.size()); ULONG got = 0;
                auto* stream = readers.value->at(slot).at(ref).stream.Get(); assert(stream);
                assert(stream->Read(actual.data(), static_cast<ULONG>(actual.size()), &got) == S_OK);
                assert(got == actual.size() && actual == latest);
            }
            const auto before = snapshot(recording.paths.root);
            for (const auto role : {CustodyRole::manifest, CustodyRole::recovery}) {
                const CustodyBytes invalid(role == CustodyRole::manifest ? 65537 : 1, 42);
                assert(package->commitMetadata(role, invalid).state == CustodyCommitState::notCommitted);
            }
            assert(snapshot(recording.paths.root) == before);
            committed = true;
            package.reset();
            auto pair = recording.coldPair(); assert(pair.ok());
            auto readers = openProtectedCustodyReaders(recording.paths.root, *pair.value, recording.cancel);
            coldReadable = readers.ok(); // No writer lease or ready setter survives restart.
            if (coldReadable) {
                const auto slot = (*pair.value)->selectedSlot();
                const auto& current = (*pair.value)->current();
                std::size_t ref = 0;
                while (ref != current.refCount && current.refs[ref].role != CustodyRole::manifest) ++ref;
                assert(ref != current.refCount);
                CustodyBytes actual(latest.size()); ULONG got = 0;
                auto* stream = readers.value->at(slot).at(ref).stream.Get(); assert(stream);
                assert(stream->Read(actual.data(), static_cast<ULONG>(actual.size()), &got) == S_OK);
                assert(got == actual.size() && actual == latest);
                std::uint8_t byte{};
                assert(stream->Read(&byte, 1, &got) == S_FALSE && got == 0);
            }
            assert(snapshot(recording.paths.root) == before);
        });
        worker.get(); // All native owners and the unique generated root retire before RED assertion.
    }
    assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == expectedIdle; }));
    assert(committed && coldReadable && "capturing_metadata_must_be_durable_and_keep_both_member_closures_readable");
}
void protectedLiveMetadataCuts() {
    auto worker = std::async(std::launch::async, [] {
        for (const bool after : {false, true}) for (unsigned cut = 1; cut <= 3; ++cut) {
            testing::GeneratedProtectedRecording recording("generated-live-cut");
            auto package = recording.writer->package();
            const CustodyBytes first{'1'}, previous{'2'}, next{'3'};
            for (const auto* bytes : {&first, &previous}) {
                const auto saved = package->commitMetadata(CustodyRole::manifest, *bytes);
                assert(saved.state == CustodyCommitState::committed);
            }
            {
                liveMetadataRenameCount = 0; liveMetadataRenameAfter = after; liveMetadataRenameTarget = cut;
                const auto saved = package->commitMetadata(CustodyRole::manifest, next);
                liveMetadataRenameTarget = 0;
                assert(liveMetadataRenameCount == cut && saved.state == CustodyCommitState::ambiguous);
                assert(saved.nativeError == 0xC0000022UL);
                const auto beforeRetry = snapshot(recording.paths.root);
                assert(package->commitMetadata(CustodyRole::manifest, next).state == CustodyCommitState::notCommitted);
                assert(snapshot(recording.paths.root) == beforeRetry);
            } // Release the ambiguous result's SAME owner before actual cold reopen.
            package.reset();
            const auto beforeRead = snapshot(recording.paths.root);
            auto pair = recording.coldPair(); assert(pair.ok());
            auto readers = openProtectedCustodyReaders(recording.paths.root, *pair.value, recording.cancel);
            assert(readers.ok());
            bool retainedPrevious = false;
            for (unsigned slot = 0; slot != 2; ++slot) {
                const auto& value = (*pair.value)->slots()[slot];
                std::size_t ref = 0;
                while (ref != value.refCount && value.refs[ref].role != CustodyRole::manifest) ++ref;
                assert(ref != value.refCount && value.refs[ref].length == 1);
                std::uint8_t actual{}; ULONG got = 0;
                auto* stream = readers.value->at(slot).at(ref).stream.Get(); assert(stream);
                assert(stream->Read(&actual, 1, &got) == S_OK && got == 1);
                retainedPrevious |= actual == previous[0];
                if (slot == (*pair.value)->selectedSlot()) assert(actual == (after && cut == 3 ? next[0] : previous[0]));
                assert(stream->Read(&actual, 1, &got) == S_FALSE && got == 0);
            }
            assert(retainedPrevious && snapshot(recording.paths.root) == beforeRead);
            std::fprintf(stderr, "LIVE_METADATA cut=%u after=%u both_closures=1 previous_retained=1 readonly_restart=1\n", cut, after);
        }
    });
    worker.get();
    assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
}
void protectedLiveMetadataFinalizeAndCorruption() {
    auto worker = std::async(std::launch::async, [] {
        for (const bool corrupt : {false, true}) {
            testing::GeneratedProtectedRecording recording("generated-live-finalize");
            auto package = recording.writer->package();
            const CustodyBytes bytes{'1'};
            for (unsigned step = 0; step != 2; ++step) {
                const auto saved = package->commitMetadata(CustodyRole::manifest, bytes);
                assert(saved.state == CustodyCommitState::committed);
            }
            if (corrupt) {
                // Current metadata is g2/index.1; damage its older peer only.
                const auto peer = package->path()/L".custody-v1"/L"manifest"/L"index.0";
                std::filesystem::resize_file(peer, 8);
                const auto before = snapshot(recording.paths.root);
                const auto generation = package->current().generation;
                for (unsigned retry = 0; retry != 2; ++retry) {
                    const auto saved = package->commitMetadata(CustodyRole::manifest, bytes);
                    const auto expected = retry ? CustodyFileError::writerFailed : CustodyFileError::invalidContent;
                    assert(saved.state == CustodyCommitState::notCommitted && saved.error == expected && saved.nativeError == 0);
                    assert(package->current().generation == generation && snapshot(recording.paths.root) == before);
                    std::fprintf(stderr, "LIVE_METADATA corrupted_peer retry=%u error=%u native=%u\n", retry,
                        static_cast<unsigned>(saved.error), saved.nativeError);
                }
                std::fputs("LIVE_METADATA corrupted_peer=refused no_repair=1\n", stderr);
            } else {
                recording.append(100);
                package.reset();
                std::optional<std::array<CustodyNativeJob, 2>> jobs(std::in_place);
                for (const auto& job : *jobs) assert(job);
                const auto result = recording.writer->finalize();
                jobs.reset();
                assert(result.normalPackage() && result.durationMs == 1000 && result.semanticVerified);
                auto pair = recording.coldPair(); assert(pair.ok());
                auto inspected = LocalRecordingPackage::inspectProtected(recording.paths.root, *pair.value, recording.session, recording.cancel);
                assert(inspected.ok() && (*inspected.value)->evidence().integrity == PackageIntegrity::valid);
                assert((*inspected.value)->evidence().durationMs == result.durationMs);
                std::fputs("LIVE_METADATA finalize_after_checkpoints=1 cold_v5_inspection=valid\n", stderr);
            }
        }
    });
    worker.get();
    assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
}
void protectedFinalizeAdmission() {
    for (const bool busy : {false, true}) {
        Fixture fixture;
        auto worker = std::async(std::launch::async, [&] {
            auto cancellation = std::make_shared<std::atomic<bool>>(false);
            auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(opened.ok());
            auto writer = V5LocalRecordingWriter::open(*opened.value, "generated-finalize-admission", cancellation);
            assert(writer.ok());
            CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
            for (unsigned n = 0; n != 100; ++n) {
                frame.ptsFrames = n * 480;
                assert((*writer.value)->append(frame));
            }
            std::optional<std::array<CustodyNativeJob, 2>> jobs;
            if (busy) {
                jobs.emplace();
                for (const auto& job : *jobs) assert(job);
            }
            const auto result = (*writer.value)->finalize(ReasonCode::none, RecordingStopReason::interruption);
            jobs.reset(); // The named result assertion never retains the generated busy jobs.
            std::fprintf(stderr, "PROTECTED_FINALIZE held_jobs=%u keepable=%u error=%u storage=%u native=%u phase=%u generation=%llu semantic=%u trusted=%u short=%u duration=%llu\n",
                busy ? 2U : 0U, result.keepablePackage() ? 1U : 0U, static_cast<unsigned>(result.error),
                static_cast<unsigned>(result.storageError), result.nativeError, static_cast<unsigned>(result.packagePhase),
                static_cast<unsigned long long>(result.packageGeneration), result.semanticVerified ? 1U : 0U,
                result.trustedPrefixRetained ? 1U : 0U, result.shortRecordingDiscarded ? 1U : 0U,
                static_cast<unsigned long long>(result.durationMs));
            std::fflush(stderr);
            assert(result.keepablePackage() && result.durationMs == 1000 &&
                "protected_finalization_must_fit_two_available_native_jobs");
        });
        worker.get();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
    }
}
void protectedLiveBornInspection() {
    struct Outcomes {
        bool sealed = false, firstRead = false, inspected = false, acknowledged = false;
        bool queuePrivate = false, diskUnchanged = false, encryptedOnly = false, exception = false;
        bool jobsHeld = false, cutObserved = false, preparedWhileHeld = false;
        CustodyFileError jobError = CustodyFileError::none;
        std::uint32_t jobNative = 0;
        CustodyFileError inspectionError = CustodyFileError::none, ackError = CustodyFileError::none;
        std::uint32_t inspectionNative = 0, ackNative = 0;
        std::uint64_t duration = 0, decodedFrames = 0, trustedFrames = 0;
    };
    auto worker = std::async(std::launch::async, [] {
        std::array<Outcomes, 2> outcomes{};
        for (unsigned mode = 0; mode != outcomes.size(); ++mode) {
            auto& result = outcomes[mode];
            try {
                testing::GeneratedProtectedRecording capture("generated-live-born-inspection");
                capture.append(500);
                const bool degraded = mode == 1;
                const auto sealed = capture.writer->finalize(
                    degraded ? ReasonCode::aecUnavailable : ReasonCode::none, RecordingStopReason::interruption);
                result.sealed = sealed.semanticVerified && sealed.durationMs == 5000 &&
                    (degraded ? sealed.trustedPrefixRetained : sealed.normalPackage()) &&
                    capture.writer->package()->current().phase ==
                        (degraded ? CustodyPackagePhase::sealedDegraded : CustodyPackagePhase::sealedNormal);
                if (!result.sealed) continue;
                capture.writer.reset(); // Intentionally KEEP the genuine born StoreOwner and its birth handles.
                auto pair = capture.store->readPackage(capture.session, capture.cancel);
                result.firstRead = pair.ok();
                if (pair.ok()) {
                    {
                        std::array<CustodyNativeJob, 4> jobs;
                        result.jobsHeld = std::all_of(jobs.begin(), jobs.end(),
                            [](const auto& job) { return static_cast<bool>(job); });
                        auto pressure = LocalRecordingPackage::inspectProtected(
                            capture.paths.root, *pair.value, capture.session, capture.cancel);
                        result.jobError = pressure.error; result.jobNative = pressure.nativeError;
                    }
                    const auto oldDisk = snapshot(capture.paths.root / capture.session);
                    oldPackedPath = L"\\\\?\\" + (capture.paths.root / capture.session /
                        L".custody-v1" / L"canonical" / L"content.packed-v2").native();
                    std::future<CustodyFileResult<std::shared_ptr<const LocalRecordingPackage::ProtectedInspection>>> read;
                    std::future<bool> prepare;
                    // Declared after both futures: exceptions release the cut BEFORE
                    // either async future's destructor waits for its native worker.
                    struct ReleaseCut {
                        ~ReleaseCut() {
                            pauseOldPackedRead.store(false);
                            { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
                            cutWake.notify_all();
                        }
                    };
                    {
                        ReleaseCut releaseOnFailure;
                        { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
                        pauseOldPackedRead.store(true);
                        read = std::async(std::launch::async, [&] {
                            return LocalRecordingPackage::inspectProtected(
                                capture.paths.root, *pair.value, capture.session, capture.cancel);
                        });
                        result.cutObserved = waitFor([] {
                            std::lock_guard<std::mutex> lock(cutMutex); return cutReached;
                        });
                        if (result.cutObserved) {
                            prepare = std::async(std::launch::async, [&] {
                                auto package = capture.store->createPackage("generated-live-born-second", capture.cancel);
                                const bool prepared = package.ok() && (*package.value)->current().generation == 1 &&
                                    (*package.value)->current().phase == CustodyPackagePhase::capturing;
                                package.value.reset(); // Last native package release stays on its worker.
                                return prepared;
                            });
                            if (prepare.wait_for(std::chrono::seconds(10)) == std::future_status::ready)
                                result.preparedWhileHeld = prepare.get();
                        }
                    } // Release even on failed observation/preparation; never await full inspection while held.
                    if (prepare.valid()) (void)prepare.get();
                    auto inspection = read.get();
                    oldPackedPath.clear();
                    result.inspectionError = inspection.error; result.inspectionNative = inspection.nativeError;
                    if (inspection.ok()) {
                        const auto& evidence = (*inspection.value)->evidence();
                        result.duration = evidence.durationMs;
                        result.decodedFrames = evidence.playback.decodedFrames;
                        result.trustedFrames = evidence.trustedPrefixFrames;
                        result.inspected = evidence.durationMs == 5000 &&
                            evidence.integrity == (degraded ? PackageIntegrity::degraded : PackageIntegrity::valid) &&
                            (degraded ? evidence.trustedPrefixFrames == 500 :
                                evidence.manifestSessionMatched && evidence.playback.decodedFrames > 0);
                    }
                    // Keep any genuine inspection alive through fresh metadata ACK.
                    auto ack = capture.store->revalidatePackage(*pair.value, capture.cancel);
                    result.acknowledged = ack.ok() && *ack.value;
                    result.ackError = ack.error; result.ackNative = ack.nativeError;
                    result.diskUnchanged = oldDisk == snapshot(capture.paths.root / capture.session);
                }
                {
                    auto queue = capture.store->readQueueValue(capture.cancel);
                    result.queuePrivate = queue.ok() && (*queue.value)->items().empty() &&
                        capture.store->queueGeneration() == 1; // No claim/account/upload authority is invented.
                }
                // The second package is an intentional genuine birth; only the old
                // inspected package must remain byte-identical throughout it.
                const auto after = snapshot(capture.paths.root);
                result.encryptedOnly = std::all_of(after.begin(), after.end(), [](const auto& file) {
                    const auto path = std::filesystem::path(file.first);
                    const auto name = path.filename().wstring();
                    return name != L"canonical-mix.f32" && name != L"media.wav" && name != L"playback.m4a" &&
                        name != L"manifest.json" && name != L"recovery.json" && path.extension() != L".tmp";
                });
            } catch (...) { oldPackedPath.clear(); result.exception = true; }
        }
        return outcomes; // Only scalars leave; every proof/native owner/root releases on this worker.
    });
    const auto outcomes = worker.get();
    const bool memoryReleased = waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; });
    for (unsigned mode = 0; mode != outcomes.size(); ++mode) {
        const auto& result = outcomes[mode];
        std::fprintf(stderr, "PROTECTED_LIVE_BORN_INSPECTION degraded=%u sealed=%u first_read=%u inspected=%u inspection_error=%u inspection_native=%u duration=%llu frames=%llu trusted_frames=%llu ack=%u ack_error=%u ack_native=%u queue_private=%u disk_unchanged=%u encrypted_only=%u exception=%u memory_released=%u\n",
            mode, result.sealed, result.firstRead, result.inspected, static_cast<unsigned>(result.inspectionError),
            result.inspectionNative, static_cast<unsigned long long>(result.duration),
            static_cast<unsigned long long>(result.decodedFrames), static_cast<unsigned long long>(result.trustedFrames),
            result.acknowledged, static_cast<unsigned>(result.ackError), result.ackNative,
            result.queuePrivate, result.diskUnchanged, result.encryptedOnly, result.exception, memoryReleased);
        std::fprintf(stderr, "PROTECTED_LIVE_BORN_PREPARATION degraded=%u jobs_held=%u job_error=%u job_native=%u nonempty_read_cut=%u prepared_before_release=%u\n",
            mode, result.jobsHeld, static_cast<unsigned>(result.jobError), result.jobNative,
            result.cutObserved, result.preparedWhileHeld);
    }
    std::fflush(stderr);
    assert(memoryReleased && "protected_live_born_inspection_requires_worker_memory_drain");
    for (const auto& result : outcomes) {
        assert(!result.exception && result.sealed && result.firstRead &&
            "protected_live_born_inspection_requires_genuine_sealed_package");
        assert(result.queuePrivate && result.diskUnchanged && result.encryptedOnly &&
            "protected_live_born_inspection_must_preserve_private_encrypted_disk");
    }
    for (const auto& result : outcomes)
        assert(result.inspected && "protected_live_born_owner_must_allow_genuine_inspection");
    for (const auto& result : outcomes)
        assert(result.acknowledged && "protected_live_born_inspection_requires_fresh_retained_ack");
    for (const auto& result : outcomes) {
        assert(result.jobsHeld && result.jobError == CustodyFileError::allocationFailed && result.inspected &&
            "protected_live_born_inspection_must_retry_after_native_job_quota");
        assert(result.cutObserved && result.preparedWhileHeld &&
            "protected_live_born_second_package_must_prepare_before_old_read_release");
    }
}
void protectedPackageRevalidation() {
    struct Outcomes {
        bool sealed = false, writerPair = false, writerRefused = false;
        bool firstRead = false, inspected = false, secondRefused = false, acknowledged = false;
        bool missingPair = false, missingToken = false, wrongToken = false, foreignStore = false;
        bool jobsHeld = false, jobRetry = false, quotaFull = false, quotaRetry = false;
        bool cancelledToken = false, diskUnchanged = false, cut = false, cutRefused = false;
        bool stickyRefused = false, faultQuotaFull = false, postQuotaRefused = false;
        bool semanticChanged = false, semanticRefused = false, cachedUnchanged = false;
        bool exception = false;
        CustodyFileError secondError = CustodyFileError::none, ackError = CustodyFileError::none;
        CustodyFileError jobError = CustodyFileError::none, quotaError = CustodyFileError::none;
        CustodyFileError cutError = CustodyFileError::none;
        CustodyFileError stickyError = CustodyFileError::none, faultQuotaError = CustodyFileError::none;
        CustodyFileError postQuotaError = CustodyFileError::none, semanticError = CustodyFileError::none;
        CustodyFileError inspectionError = CustodyFileError::none;
        std::uint32_t inspectionNative = 0;
        std::uint64_t inspectedDuration = 0, decodedFrames = 0;
        std::uint32_t secondNative = 0, ackNative = 0, jobNative = 0, quotaNative = 0, cutNative = 0;
    };
    auto worker = std::async(std::launch::async, [] {
        std::array<Outcomes, 4> outcomes{};
        const auto accepted = [](const CustodyFileResult<bool>& value) {
            return value.ok() && *value.value;
        };
        for (unsigned mode = 0; mode != outcomes.size(); ++mode) {
            auto& result = outcomes[mode];
            try {
                testing::GeneratedProtectedRecording capture("generated-package-revalidation");
                capture.append(500);
                const auto sealed = capture.writer->finalize(ReasonCode::none, RecordingStopReason::interruption);
                result.sealed = sealed.normalPackage() && sealed.semanticVerified &&
                    !sealed.shortRecordingDiscarded && sealed.durationMs == 5000;
                if (!result.sealed) continue;
                const auto before = snapshot(capture.paths.root);
                if (mode == 0) {
                    // Sealed content alone must not turn a writable-origin lease into a fresh read ACK.
                    auto writable = capture.writer->package()->readPair();
                    result.writerPair = writable.ok();
                    if (writable.ok()) result.writerRefused = !accepted(
                        capture.store->revalidatePackage(*writable.value, capture.cancel));
                }
                capture.writer.reset();
                // Exercise a genuinely cold StoreOwner after restart. The birth
                // owner's store.id still has write access and is a separate live
                // inspection conflict; do not misclassify that as package ACK RED.
                capture.store.reset();
                auto reopened = ProtectedCustodyStoreOwner::open(capture.paths.root, capture.cancel);
                if (!reopened.ok()) continue;
                capture.store = std::move(*reopened.value);
                auto pair = capture.store->readPackage(capture.session, capture.cancel);
                result.firstRead = pair.ok();
                if (!pair.ok()) continue;
                auto inspection = LocalRecordingPackage::inspectProtected(
                    capture.paths.root, *pair.value, capture.session, capture.cancel);
                result.inspectionError = inspection.error; result.inspectionNative = inspection.nativeError;
                if (inspection.ok()) {
                    result.inspectedDuration = (*inspection.value)->evidence().durationMs;
                    result.decodedFrames = (*inspection.value)->evidence().playback.decodedFrames;
                }
                result.inspected = inspection.ok() &&
                    (*inspection.value)->evidence().integrity == PackageIntegrity::valid &&
                    (*inspection.value)->evidence().manifestSessionMatched &&
                    (*inspection.value)->evidence().durationMs == 5000 &&
                    (*inspection.value)->evidence().playback.decodedFrames > 0;
                if (!result.inspected) continue;
                {
                    auto second = capture.store->readPackage(capture.session, capture.cancel);
                    result.secondRefused = !second.ok();
                    result.secondError = second.error; result.secondNative = second.nativeError;
                }
                {
                    auto ack = capture.store->revalidatePackage(*pair.value, capture.cancel);
                    result.acknowledged = accepted(ack);
                    result.ackError = ack.error; result.ackNative = ack.nativeError;
                }
                // Do not gate negative cases on ACK: the initial stub must still exercise all cases.
                if (mode == 0) {
                    result.missingPair = !accepted(capture.store->revalidatePackage({}, capture.cancel));
                    result.missingToken = !accepted(capture.store->revalidatePackage(*pair.value, {}));
                    auto different = std::make_shared<std::atomic<bool>>(false);
                    result.wrongToken = !accepted(capture.store->revalidatePackage(*pair.value, different));
                    {
                        Fixture foreign;
                        auto foreignToken = std::make_shared<std::atomic<bool>>(false);
                        auto owner = ProtectedCustodyStoreOwner::open(foreign.root, foreignToken);
                        result.foreignStore = owner.ok() && !accepted(
                            (*owner.value)->revalidatePackage(*pair.value, capture.cancel));
                    }
                    {
                        std::array<CustodyNativeJob, 4> jobs;
                        result.jobsHeld = std::all_of(jobs.begin(), jobs.end(),
                            [](const auto& job) { return static_cast<bool>(job); });
                        auto pressure = capture.store->revalidatePackage(*pair.value, capture.cancel);
                        result.jobError = pressure.error; result.jobNative = pressure.nativeError;
                    }
                    result.jobRetry = accepted(capture.store->revalidatePackage(*pair.value, capture.cancel));
                    {
                        CustodyBytes reservation; // Include the existing Debug vector proxy before reserving.
                        reservation.resize(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
                        result.quotaFull = CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit;
                        auto pressure = capture.store->revalidatePackage(*pair.value, capture.cancel);
                        result.quotaError = pressure.error; result.quotaNative = pressure.nativeError;
                    }
                    result.quotaRetry = accepted(capture.store->revalidatePackage(*pair.value, capture.cancel));
                }
                result.diskUnchanged = before == snapshot(capture.paths.root);
                if (mode == 0) {
                    // Cancel the exact operation token LAST; never reset a cancelled token for another case.
                    capture.cancel->store(true);
                    result.cancelledToken = !accepted(capture.store->revalidatePackage(*pair.value, capture.cancel));
                } else if (mode < 3) {
                    // Independent roots ensure an index.0 sticky fault cannot mask the index.1 reread.
                    const auto index = capture.paths.root / capture.session / ".custody-v1" /
                        "package-state" / ("index." + std::to_string(mode - 1));
                    std::error_code error;
                    std::filesystem::resize_file(index, 8, error);
                    result.cut = !error;
                    if (result.cut) {
                        auto changed = capture.store->revalidatePackage(*pair.value, capture.cancel);
                        result.cutRefused = !accepted(changed);
                        result.cutError = changed.error; result.cutNative = changed.nativeError;
                        auto retry = capture.store->revalidatePackage(*pair.value, capture.cancel);
                        result.stickyRefused = !accepted(retry); result.stickyError = retry.error;
                        {
                            CustodyBytes reservation;
                            reservation.resize(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
                            result.faultQuotaFull = CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit;
                            auto pressure = capture.store->revalidatePackage(*pair.value, capture.cancel);
                            result.faultQuotaError = pressure.error;
                        }
                        auto afterPressure = capture.store->revalidatePackage(*pair.value, capture.cancel);
                        result.postQuotaRefused = !accepted(afterPressure); result.postQuotaError = afterPressure.error;
                    }
                } else {
                    // Authenticated, shape-valid metadata with the SAME index/generation but a different tuple.
                    const auto& held = *pair.value;
                    const auto selected = held->selectedSlot();
                    const auto generation = held->current().generation;
                    auto changed = held->current();
                    auto ref = std::find_if(changed.refs.begin(), changed.refs.begin() + changed.refCount,
                        [](const auto& value) { return value.role == CustodyRole::playback && value.sealed && value.sha256; });
                    if (ref == changed.refs.begin() + changed.refCount) continue;
                    const auto originalHash = *ref->sha256;
                    (*ref->sha256)[0] ^= 1;
                    const auto& index = held->indices().indices[selected];
                    if (index.entries.size() != 1) continue;
                    const auto& entry = index.entries[0];
                    auto plain = writeCustodyPackage(changed, changed.context, changed.generation, capture.session);
                    if (!plain.ok() || plain.value->size() != index.logicalLength) continue;
                    auto cipher = ProtectedCustodyCodec::sealBlock(changed.context, 0, entry.version, *plain.value);
                    if (!cipher.ok() || cipher.value->size() != entry.envelopeBytes) continue;
                    const auto block = capture.paths.root / capture.session / ".custody-v1" / "package-state" /
                        ("block.0." + std::to_string(entry.version));
                    if (!std::filesystem::is_regular_file(block)) continue;
                    {
                        std::ofstream output(block, std::ios::binary | std::ios::trunc);
                        output.write(reinterpret_cast<const char*>(cipher.value->data()),
                            static_cast<std::streamsize>(cipher.value->size()));
                        output.close(); result.semanticChanged = static_cast<bool>(output);
                    } // Only charged codec ciphertext reaches the existing generated file.
                    const auto after = snapshot(capture.paths.root);
                    const auto key = std::filesystem::relative(block, capture.paths.root).wstring();
                    result.semanticChanged = result.semanticChanged && before.size() == after.size() &&
                        before.at(key) != after.at(key) && std::all_of(before.begin(), before.end(), [&](const auto& file) {
                            const auto found = after.find(file.first);
                            return found != after.end() && (file.first == key || file.second == found->second);
                        }); // Both indices and every other encrypted file remain unchanged.
                    auto ack = capture.store->revalidatePackage(held, capture.cancel);
                    result.semanticRefused = !accepted(ack); result.semanticError = ack.error;
                    result.cachedUnchanged = held->current().generation == generation &&
                        held->selectedSlot() == selected &&
                        std::any_of(held->current().refs.begin(), held->current().refs.begin() + held->current().refCount,
                            [&](const auto& value) { return value.role == CustodyRole::playback && value.sha256 &&
                                *value.sha256 == originalHash; });
                }
            } catch (...) { result.exception = true; }
            // Inspection, pair, StoreOwner and generated roots all release here on this worker.
        }
        return outcomes; // Scalars only; no owner/proof/control block crosses to the asserting thread.
    });
    const auto outcomes = worker.get();
    const bool memoryReleased = waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; });
    for (unsigned mode = 0; mode != outcomes.size(); ++mode) {
        const auto& result = outcomes[mode];
        std::fprintf(stderr, "PROTECTED_PACKAGE_INSPECTION case=%u error=%u native=%u duration=%llu frames=%llu\n",
            mode, static_cast<unsigned>(result.inspectionError), result.inspectionNative,
            static_cast<unsigned long long>(result.inspectedDuration), static_cast<unsigned long long>(result.decodedFrames));
        std::fprintf(stderr, "PROTECTED_PACKAGE_MUTATION case=%u sticky_refused=%u sticky_error=%u fault_quota_full=%u fault_quota_error=%u post_quota_refused=%u post_quota_error=%u semantic_changed=%u semantic_refused=%u semantic_error=%u cached_unchanged=%u\n",
            mode, result.stickyRefused, static_cast<unsigned>(result.stickyError), result.faultQuotaFull,
            static_cast<unsigned>(result.faultQuotaError), result.postQuotaRefused, static_cast<unsigned>(result.postQuotaError),
            result.semanticChanged, result.semanticRefused, static_cast<unsigned>(result.semanticError), result.cachedUnchanged);
        std::fprintf(stderr, "PROTECTED_PACKAGE_REVALIDATION case=%u sealed=%u first_read=%u inspected=%u second_refused=%u second_error=%u second_native=%u ack=%u ack_error=%u ack_native=%u writer_pair=%u writer_refused=%u missing_pair=%u missing_token=%u wrong_token=%u foreign_store=%u jobs_held=%u job_error=%u job_native=%u job_retry=%u quota_full=%u quota_error=%u quota_native=%u quota_retry=%u cancelled_token=%u disk_unchanged=%u cut=%u cut_refused=%u cut_error=%u cut_native=%u exception=%u memory_released=%u\n",
            mode, result.sealed, result.firstRead, result.inspected, result.secondRefused,
            static_cast<unsigned>(result.secondError), result.secondNative, result.acknowledged,
            static_cast<unsigned>(result.ackError), result.ackNative, result.writerPair, result.writerRefused,
            result.missingPair, result.missingToken, result.wrongToken, result.foreignStore,
            result.jobsHeld, static_cast<unsigned>(result.jobError), result.jobNative, result.jobRetry,
            result.quotaFull, static_cast<unsigned>(result.quotaError), result.quotaNative, result.quotaRetry,
            result.cancelledToken, result.diskUnchanged, result.cut, result.cutRefused,
            static_cast<unsigned>(result.cutError), result.cutNative, result.exception, memoryReleased);
    }
    std::fflush(stderr);
    assert(memoryReleased && "protected_package_revalidation_must_release_all_native_owners");
    for (const auto& result : outcomes) {
        assert(!result.exception && result.sealed && result.firstRead && result.inspected &&
            "protected_package_revalidation_requires_genuine_sealed_inspection");
        assert(result.secondRefused && result.secondError == CustodyFileError::ioFailed &&
            result.secondNative == ERROR_SHARING_VIOLATION &&
            "protected_package_revalidation_second_open_must_reproduce_sharing_conflict");
        assert(result.diskUnchanged && "protected_package_revalidation_must_not_write_before_cut");
    }
    for (const auto& result : outcomes)
        assert(result.acknowledged && "protected_package_revalidation_must_ack_retained_readonly_lease");
    const auto& control = outcomes[0];
    assert(control.writerPair && control.writerRefused && control.missingPair && control.missingToken &&
        control.wrongToken && control.foreignStore && control.cancelledToken &&
        "protected_package_revalidation_must_reject_invalid_authority");
    assert(control.jobsHeld && control.jobError == CustodyFileError::allocationFailed && control.jobRetry &&
        "protected_package_revalidation_must_recover_after_native_job_quota");
    assert(control.quotaFull && control.quotaError == CustodyFileError::allocationFailed && control.quotaRetry &&
        "protected_package_revalidation_must_recover_after_memory_quota");
    for (unsigned mode = 1; mode != 3; ++mode) {
        const auto& result = outcomes[mode];
        assert(result.cut && result.cutRefused && result.cutError == CustodyFileError::invalidContent &&
            "protected_package_revalidation_must_reread_each_actual_index");
        assert(result.stickyRefused && result.stickyError == CustodyFileError::writerFailed &&
            "protected_package_revalidation_must_preserve_each_index_fault");
        assert(result.faultQuotaFull && result.faultQuotaError == CustodyFileError::allocationFailed &&
            result.postQuotaRefused && result.postQuotaError == CustodyFileError::writerFailed &&
            "protected_package_revalidation_quota_must_not_clear_index_fault");
    }
    assert(outcomes[3].semanticChanged && outcomes[3].semanticRefused &&
        outcomes[3].semanticError == CustodyFileError::conflict && outcomes[3].cachedUnchanged &&
        "protected_package_revalidation_must_compare_actual_semantic_tuple");
}
void protectedPlaybackConsumer() {
    const auto cold = CustodyOwnedMemory::usedBytes();
    testing::GeneratedRecordingRoot paths;
    constexpr auto session = "generated-playback-consumer";
    std::async(std::launch::async, [&] {
        auto cancellation = std::make_shared<std::atomic<bool>>(false);
        auto opened = ProtectedCustodyStoreOwner::open(paths.root, cancellation); assert(opened.ok());
        auto store = std::move(*opened.value);
        auto created = V5LocalRecordingWriter::open(store, session, cancellation); assert(created.ok());
        auto writer = std::move(*created.value);
        CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
        for (unsigned index = 0; index != 500; ++index) {
            frame.ptsFrames = index * 480; assert(writer->append(frame));
        }
        const auto sealed = writer->finalize(ReasonCode::none, RecordingStopReason::interruption);
        assert(sealed.normalPackage() && sealed.semanticVerified); writer.reset();
        auto current = store->readQueueValue(cancellation); assert(current.ok());
        auto value = std::allocate_shared<ProtectedUploadQueueValue>(CustodyAllocator<ProtectedUploadQueueValue>{}, **current.value);
        ProtectedUploadQueueValue::Item row;
        row.localRecordingId = row.directoryId = row.sessionId = session;
        const auto directory = (paths.root / session).u8string(); row.packageDirectory.assign(directory.begin(), directory.end());
        row.ownerUserId = "11111111-1111-4111-8111-111111111111";
        row.ownerWorkspaceId = "22222222-2222-4222-8222-222222222222";
        row.status = UploadQueueStatus::uploaded;
        assert(value->enqueue(std::move(row), 1000, cancellation.get()));
        auto bytes = value->serialize(cancellation); assert(bytes.ok());
        auto saved = commitProtectedCustodyMetadata(store, store->queueContext(), store->queueGeneration(), *bytes.value, cancellation);
        assert(saved.state == CustodyCommitState::committed);
    }).get();
    // The genuine seed finalizer initializes the process-lifetime empty read
    // cache. Exactly the separately measured proxy may remain, no payload/owner.
    const auto baseline = CustodyOwnedMemory::usedBytes();
    std::fprintf(stderr, "PROTECTED_PLAYBACK cold_owned=%zu seeded_owned=%zu empty_cache_owned=%zu\n", cold, baseline, idleOwnedBytes);
    assert(baseline == idleOwnedBytes);
    const auto before = snapshot(paths.root);
    const DesktopHttpTransport::UploadSend accountWire = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        if (request.method != "GET") return {403, "{}"};
        if (request.path == "/desktop/settings/spaces") return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        if (request.path == "/api/v1/auth/me") return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
        return {403, "{}"};
    };
    {
        NativeCapture capture(paths.root, {std::make_shared<GeneratedAec>(), false}, accountWire);
        startAndAdopt(capture, 2);
        assert(!capture.openLocalPlayback(session, 17, true)); // No account authority.
        capture.setAuthSessionToken("generated-playback-owner");
        assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
        assert(!capture.openLocalPlayback("absent", 17, true));
        for (const bool metadata : {true, false}) {
            oldPackedPath = L"\\\\?\\" + (paths.root / session / L".custody-v1" / L"canonical" / L"content.packed-v2").native();
            { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
            pausePlaybackPackageMetadata.store(metadata); pauseOldPackedRead.store(!metadata);
            assert(capture.openLocalPlayback(session, 15, true));
            const bool readHeld = waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; });
            const bool prematureAuthorization = capture.authorizeLocalPlayback(15);
            capture.closeLocalPlayback();
            { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
            cutWake.notify_all(); pauseOldPackedRead.store(false); pausePlaybackPackageMetadata.store(false);
            assert(readHeld && !prematureAuthorization);
            assert(waitFor([&] { return capture.localPlaybackObservation().terminal; }));
            assert(!capture.authorizeLocalPlayback(15)); // Neither late publication nor inspection can resurrect a closed request.
            oldPackedPath.clear();
        }
        retainConsumerClone.store(true);
        assert(capture.openLocalPlayback(session, 17, true));
        assert(!capture.openLocalPlayback(session, 18, true)); // One real worker, no replacement leak.
        const bool playbackReady = waitFor([&] {
            const auto state = capture.localPlaybackObservation();
            return state.media.ready && !state.preparing && !state.terminal;
        });
        if (!playbackReady) {
            if (auto* failedHold = takeConsumerClone()) failedHold->Release();
            capture.closeLocalPlayback();
            assert(waitFor([&] { return capture.localPlaybackObservation().terminal; }));
        }
        assert(playbackReady); // Partial initialization cannot deadlock test-owned clone cleanup.
        auto state = capture.localPlaybackObservation();
        assert(state.present && state.documentGeneration == 17 && state.media.paused && state.media.muted);
        assert(!capture.authorizeLocalPlayback(16)); // Stale document cannot autoplay.
        assert(!capture.seekLocalPlayback(std::numeric_limits<double>::quiet_NaN()));
        assert(capture.authorizeLocalPlayback(17));
        assert(waitFor([&] { const auto s = capture.localPlaybackObservation(); return !s.media.paused && s.media.positionSeconds > 0.10; }));
        assert(capture.pauseLocalPlayback(true));
        assert(waitFor([&] { return capture.localPlaybackObservation().media.paused; }));
        assert(capture.seekLocalPlayback(2));
        assert(waitFor([&] { const auto s = capture.localPlaybackObservation(); return !s.media.seeking && s.media.positionSeconds >= 1.9; }));
        assert(capture.pauseLocalPlayback(false));
        assert(waitFor([&] { return !capture.localPlaybackObservation().media.paused; }));
        { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
        pausePlaybackQueueMetadata.store(true);
        const bool seekAccepted = capture.seekLocalPlayback(1);
        const bool validationHeld = waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; });
        const bool pauseAccepted = validationHeld && capture.pauseLocalPlayback(true);
        const bool pausePublishedBeforeAck = pauseAccepted && waitFor([&] {
            return capture.localPlaybackObservation().media.paused;
        }, std::chrono::seconds(1));
        // Same intent as the window button: invert actual observed pause state.
        const bool resumeAccepted = pausePublishedBeforeAck &&
            capture.pauseLocalPlayback(!capture.localPlaybackObservation().media.paused);
        const bool resumedWithoutAck = resumeAccepted && waitFor([&] {
            return !capture.localPlaybackObservation().media.paused;
        }, std::chrono::seconds(1));
        { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
        cutWake.notify_all(); pausePlaybackQueueMetadata.store(false);
        const bool pauseContract = seekAccepted && validationHeld && pauseAccepted &&
            pausePublishedBeforeAck && resumeAccepted && !resumedWithoutAck;
        if (!pauseContract) {
            if (auto* failedHold = takeConsumerClone()) failedHold->Release();
            capture.closeLocalPlayback();
            assert(waitFor([&] { return capture.localPlaybackObservation().terminal; }));
        }
        std::fprintf(stderr, "PROTECTED_PLAYBACK seek_accepted=%u validation_held=%u pause_accepted=%u pause_published_before_ack=%u resume_accepted=%u resumed_without_ack=%u\n",
            seekAccepted, validationHeld, pauseAccepted, pausePublishedBeforeAck, resumeAccepted, resumedWithoutAck);
        std::fflush(stderr);
        assert(pauseContract && "pause_observation_must_publish_before_storage_ack");
        assert(waitFor([&] { return !capture.localPlaybackObservation().media.paused; }));
        assert(snapshot(paths.root) == before); // All playback effects so far were read-only.
        const auto packageBefore = snapshot(paths.root / session);
        capture.setAuthSessionToken({});
        auto* held = takeConsumerClone(); assert(held);
        const bool prematureTerminal = waitFor([&] { return capture.localPlaybackObservation().terminal; }, std::chrono::seconds(1));
        const bool replacementRefused = !capture.openLocalPlayback(session, 18, true);
        // A retained MF clone must not occupy storage's recording command slot.
        const bool preparationAccepted = NativeCaptureStorageTestPeer::requestRecording(capture);
        const bool preparedBeforeRelease = waitFor([&] { return NativeCaptureStorageTestPeer::prepared(capture); });
        held->Release(); // Always release before asserting a failed bounded observation.
        assert(!prematureTerminal && replacementRefused && preparationAccepted && preparedBeforeRelease);
        assert(waitFor([&] { return capture.localPlaybackObservation().terminal; }));
        assert(!capture.authorizeLocalPlayback(17) && !capture.pauseLocalPlayback(false));
        assert(!capture.localQueueComplete() && !capture.readiness().storageWritable);
        capture.shutdown();
        assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        assert(snapshot(paths.root / session) == packageBefore);
    }
    assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
    std::fputs("NATIVE_STORAGE protected_playback_consumer=passed generated_muted=1 UI_acceptance=0\n", stderr);
}

void protectedMediaEngine() {
    struct Outcomes {
        bool sealed = false, inspected = false, missingProof = false, missingToken = false;
        bool wrongToken = false, cancelledToken = false, negativeDrain = true;
        bool opened = false, ready = false, muted = false, invalidSeek = false;
        bool progressed = false, paused = false, sought = false, resumed = false;
        bool closed = false, repeatedClose = false, commandsClosed = false, diskUnchanged = false;
        bool heldMfClone = false, closePending = false, releaseDrained = false;
        unsigned openError = 0;
        std::uint32_t nativeError = 0;
        HRESULT error = S_OK;
        double duration = 0, playedAt = 0, pausedAt = 0, soughtAt = 0, resumedAt = 0;
    };
    auto worker = std::async(std::launch::async, [] {
        Outcomes result;
        try {
            testing::GeneratedProtectedRecording capture("generated-media-engine");
            capture.append(500); // Five seconds of generated PCM, no input device or real-time capture.
            const auto sealed = capture.writer->finalize(ReasonCode::none, RecordingStopReason::interruption);
            result.sealed = sealed.normalPackage() && sealed.semanticVerified &&
                !sealed.shortRecordingDiscarded && sealed.durationMs == 5000;
            auto pair = capture.coldPair();
            if (!result.sealed || !pair.ok()) return result;
            const auto& package = (*pair.value)->current();
            result.sealed = std::any_of(package.refs.begin(), package.refs.begin() + package.refCount,
                [](const auto& ref) {
                    return ref.role == CustodyRole::playback && ref.packed && ref.sealed &&
                        ref.length && *ref.length && ref.generation && *ref.generation &&
                        ref.containerId && ref.rootRef && ref.sha256;
                });
            const auto before = snapshot(capture.paths.root);
            const auto close = [](ProtectedLocalRecordingPlayback& player) {
                return waitFor([&] {
                    const bool completed = player.startClose();
                    return completed && player.drained();
                }, std::chrono::seconds(30));
            };
            const auto refused = [&](auto attempt) {
                const bool rejected = !attempt.ok() && (!attempt.value || !*attempt.value);
                if (attempt.value && *attempt.value) {
                    result.negativeDrain = close(**attempt.value) && result.negativeDrain;
                    attempt.value.reset(); // Even a wrongly accepted negative drains on this worker.
                }
                return rejected;
            };
            // A separate genuine inspection prevents the cancelled reader's sticky
            // status from contaminating the subsequent positive renderer case.
            const auto context = (*pair.value)->current().context;
            pair.value.reset(); // Release the exclusive identity lease before opening another genuine pair.
            {
                auto cancelled = std::make_shared<std::atomic<bool>>(false);
                auto cancelledPair = ProtectedCustodyPackagePair::read(
                    capture.paths.root, capture.session, context, cancelled);
                if (cancelledPair.ok()) {
                    auto inspection = LocalRecordingPackage::inspectProtected(
                        capture.paths.root, *cancelledPair.value, capture.session, cancelled);
                    if (inspection.ok()) {
                        cancelled->store(true);
                        result.cancelledToken = refused(ProtectedLocalRecordingPlayback::open(
                            std::move(*inspection.value), cancelled, true));
                    }
                }
            }
            pair = ProtectedCustodyPackagePair::read(capture.paths.root, capture.session, context, capture.cancel);
            if (!pair.ok()) return result;
            {
                auto inspection = LocalRecordingPackage::inspectProtected(
                    capture.paths.root, *pair.value, capture.session, capture.cancel);
                result.inspected = inspection.ok() &&
                    (*inspection.value)->evidence().integrity == PackageIntegrity::valid &&
                    (*inspection.value)->evidence().manifestSessionMatched &&
                    (*inspection.value)->evidence().durationMs == 5000 &&
                    (*inspection.value)->evidence().playback.decodedFrames > 0;
                if (result.inspected) {
                    const auto& proof = *inspection.value;
                    result.missingProof = refused(ProtectedLocalRecordingPlayback::open({}, capture.cancel, true));
                    result.missingToken = refused(ProtectedLocalRecordingPlayback::open(proof, {}, true));
                    auto wrong = std::make_shared<std::atomic<bool>>(false);
                    result.wrongToken = refused(ProtectedLocalRecordingPlayback::open(proof, wrong, true));
                    observedPlaybackClone = nullptr;
                    observeClone = true; // Negative factories above never acquire the external hold.
                    auto opened = ProtectedLocalRecordingPlayback::open(std::move(*inspection.value), capture.cancel, true);
                    observeClone = false;
                    result.openError = static_cast<unsigned>(opened.error);
                    result.nativeError = opened.nativeError;
                    result.opened = opened.ok() && opened.value && *opened.value;
                    if (result.opened) {
                        auto player = std::move(*opened.value);
                        // Declared after player: exception unwinding releases the external
                        // Clone BEFORE the player's drain-waiting destructor can run.
                        Microsoft::WRL::ComPtr<IStream> externalClone = observedPlaybackClone;
                        observedPlaybackClone = nullptr; // Same worker; never dereference a failed-open observation.
                        result.heldMfClone = externalClone.Get() != nullptr;
                        if (result.heldMfClone) {
                            std::fputs("PROTECTED_MEDIA_ENGINE held_mf_clone=1\n", stderr); std::fflush(stderr);
                        }
                        const auto observeUntil = [&](auto predicate) {
                            bool matched = false;
                            (void)waitFor([&] {
                                const auto state = player->observe();
                                result.error = state.error;
                                if (FAILED(state.error)) return true;
                                matched = predicate(state);
                                return matched;
                            });
                            return matched;
                        };
                        result.ready = observeUntil([&](const auto& state) {
                            result.duration = state.durationSeconds;
                            return state.ready && state.paused && !state.seeking && !state.ended &&
                                std::isfinite(state.positionSeconds) && state.positionSeconds >= 0 &&
                                std::isfinite(state.durationSeconds) && state.durationSeconds >= 4.5 &&
                                state.durationSeconds <= 5.5;
                        });
                        result.muted = player->observe().muted;
                        if (result.opened && result.ready && result.muted) {
                            const bool nan = FAILED(player->seek(std::numeric_limits<double>::quiet_NaN()));
                            const bool below = FAILED(player->seek(-1.0));
                            const bool above = FAILED(player->seek(result.duration + 1.0));
                            result.invalidSeek = nan && below && above;
                            const auto start = player->observe().positionSeconds;
                            if (SUCCEEDED(player->play())) result.progressed = observeUntil([&](const auto& state) {
                                result.playedAt = state.positionSeconds;
                                return state.ready && state.muted && !state.paused && !state.seeking && !state.ended &&
                                    std::isfinite(state.positionSeconds) && state.positionSeconds >= start + 0.1;
                            });
                            if (result.progressed && SUCCEEDED(player->pause())) {
                                result.paused = observeUntil([&](const auto& state) {
                                    result.pausedAt = state.positionSeconds;
                                    return state.muted && state.paused && !state.seeking && !state.ended &&
                                        std::isfinite(state.positionSeconds);
                                });
                                if (result.paused) {
                                    const auto until = std::chrono::steady_clock::now() + std::chrono::milliseconds(200);
                                    bool stable = true;
                                    const bool observed = waitFor([&] {
                                        const auto state = player->observe();
                                        result.error = state.error;
                                        stable = stable && SUCCEEDED(state.error) && state.muted && state.paused &&
                                            !state.seeking && !state.ended && std::isfinite(state.positionSeconds) &&
                                            std::abs(state.positionSeconds - result.pausedAt) <= 0.05;
                                        return !stable || std::chrono::steady_clock::now() >= until;
                                    });
                                    result.paused = observed && stable;
                                }
                            }
                            const auto target = result.duration / 2.0;
                            if (result.paused && SUCCEEDED(player->seek(target))) result.sought = observeUntil([&](const auto& state) {
                                result.soughtAt = state.positionSeconds;
                                return state.muted && state.paused && !state.seeking && !state.ended &&
                                    std::isfinite(state.positionSeconds) && std::abs(state.positionSeconds - target) <= 0.15;
                            });
                            if (result.sought && SUCCEEDED(player->play())) result.resumed = observeUntil([&](const auto& state) {
                                result.resumedAt = state.positionSeconds;
                                return state.muted && !state.paused && !state.seeking && !state.ended &&
                                    std::isfinite(state.positionSeconds) && state.positionSeconds >= result.soughtAt + 0.1;
                            });
                        }
                        std::fputs("PROTECTED_MEDIA_ENGINE stage=closing\n", stderr); std::fflush(stderr);
                        const bool firstClose = player->startClose();
                        result.closePending = result.heldMfClone && !firstClose && !player->drained() && capture.cancel->load();
                        const bool pendingPlay = FAILED(player->play()), pendingPause = FAILED(player->pause());
                        const bool pendingSeek = FAILED(player->seek(0.0));
                        externalClone.Reset(); // Always release, even when a functional observation failed.
                        result.releaseDrained = close(*player);
                        result.closed = result.releaseDrained && capture.cancel->load();
                        result.repeatedClose = player->startClose() && player->drained();
                        const bool play = FAILED(player->play()), pause = FAILED(player->pause());
                        const bool seek = FAILED(player->seek(0.0));
                        result.commandsClosed = pendingPlay && pendingPause && pendingSeek && play && pause && seek;
                        player.reset(); // Destructor retries any pending close here, never on the caller/UI.
                    }
                    observedPlaybackClone = nullptr;
                }
            }
            pair.value.reset();
            result.diskUnchanged = before == snapshot(capture.paths.root);
        } catch (...) { observeClone = false; observedPlaybackClone = nullptr; result.error = E_FAIL; }
        return result; // All native owners and generated files leave on this worker.
    });
    const auto result = worker.get();
    const bool memory = waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; });
    std::fprintf(stderr,
        "PROTECTED_MEDIA_ENGINE sealed=%u inspected=%u missing_proof=%u missing_token=%u wrong_token=%u cancelled_token=%u negative_drain=%u opened=%u open_error=%u native=%u error=%lu ready=%u muted=%u invalid_seek=%u progress=%u paused=%u sought=%u resumed=%u held_mf_clone=%u close_pending=%u release_drained=%u closed=%u repeated_close=%u commands_closed=%u disk_unchanged=%u memory=%u duration=%.3f played_at=%.3f paused_at=%.3f sought_at=%.3f resumed_at=%.3f\n",
        result.sealed, result.inspected, result.missingProof, result.missingToken, result.wrongToken,
        result.cancelledToken, result.negativeDrain, result.opened, result.openError, result.nativeError,
        static_cast<unsigned long>(result.error), result.ready, result.muted, result.invalidSeek,
        result.progressed, result.paused, result.sought, result.resumed, result.heldMfClone, result.closePending,
        result.releaseDrained, result.closed, result.repeatedClose,
        result.commandsClosed, result.diskUnchanged, memory, result.duration, result.playedAt,
        result.pausedAt, result.soughtAt, result.resumedAt);
    std::fflush(stderr);
    assert(memory && result.negativeDrain && "protected_media_engine_must_release_native_and_charged_owners");
    assert(result.sealed && result.inspected && result.diskUnchanged && "protected_media_engine_requires_unchanged_genuine_sealed_inspection");
    assert(result.missingProof && result.missingToken && result.wrongToken && result.cancelledToken &&
        "protected_media_engine_rejects_missing_or_nonidentical_or_cancelled_authority");
    assert(result.heldMfClone && result.closePending && result.releaseDrained &&
        "protected_media_engine_must_wait_for_exact_external_mf_clone_release");
    assert(result.opened && result.ready && result.muted && result.invalidSeek && result.progressed &&
        result.paused && result.sought && result.resumed && result.closed && result.repeatedClose && result.commandsClosed &&
        "protected_media_engine_must_play_pause_seek_and_drain");
}
void protectedEncoderWriteFailure() {
    Fixture fixture;
    auto worker = std::async(std::launch::async, [&] {
        auto cancellation = std::make_shared<std::atomic<bool>>(false);
        auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(opened.ok());
        constexpr std::string_view session = "generated-encoder-write-failure";
        auto writer = V5LocalRecordingWriter::open(*opened.value, session, cancellation); assert(writer.ok());
        CanonicalAudioFrame frame;
        std::uint32_t noise = 0x12345678;
        for (unsigned n = 0; n != 3000; ++n) {
            frame.ptsFrames = n * 480;
            for (auto& sample : frame.mixed) {
                noise ^= noise << 13; noise ^= noise >> 17; noise ^= noise << 5;
                sample = static_cast<float>(noise & 65535) / 65536.0F - 0.5F;
            }
            assert((*writer.value)->append(frame));
        }
        playbackWritePath = L"\\\\?\\" + (fixture.root / session / L".custody-v1" / L"playback" / L"content.packed-v2").wstring();
        playbackWriteCuts = 0;
        failPlaybackWrite = true; // Birth/capture remain real; only derived playback append may fail.
        std::fputs("PROTECTED_MF_WRITE stage=before_finalize generated_frames=3000\n", stderr); std::fflush(stderr);
        const auto result = (*writer.value)->finalize();
        failPlaybackWrite = false;
        std::fprintf(stderr, "PROTECTED_MF_WRITE stage=returned cuts=%u error=%u storage=%u native=%u keepable=%u trusted=%u\n",
            playbackWriteCuts.load(), static_cast<unsigned>(result.error), static_cast<unsigned>(result.storageError),
            result.nativeError, result.keepablePackage() ? 1U : 0U, result.trustedPrefixRetained ? 1U : 0U);
        std::fflush(stderr);
        return playbackWriteCuts == 1 && result.error == V5WriterError::encodeFailed &&
            result.storageError == CustodyFileError::ioFailed && result.nativeError == static_cast<std::uint32_t>(HRESULT_FROM_WIN32(ERROR_WRITE_FAULT)) &&
            !result.normalPackage() && !result.keepablePackage();
    });
    const bool valid = worker.get(); // Full adapter/MF/native teardown, not just error publication.
    playbackWritePath.clear();
    assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
    assert(valid && "encoder_write_fault_must_return_exact_failure_without_normal_package");
}
void protectedRecordingVerticalAndRestart(VerticalCase test = VerticalCase::normal,
    IoCut resultCut = IoCut::none, bool refuseReopen = false, bool stopPrepared = false,
    bool inspectionPrepared = false, bool inspectionActiveStop = false, bool privacyFlow = false) {
    std::fprintf(stderr, "V5_CASE=%u stage=start\n", static_cast<unsigned>(test));
    const bool staleEpoch = test == VerticalCase::staleEpoch;
    const bool ownedUpload = test == VerticalCase::ownedUpload;
    const bool scheduledUpload = test == VerticalCase::scheduledUpload;
    const bool ownedAccount = ownedUpload || scheduledUpload;
    const bool losePoll = test != VerticalCase::normal && !staleEpoch && !ownedAccount;
    const bool degraded = test == VerticalCase::nativeStopFault || test == VerticalCase::lateDevice;
    Fixture fixture;
    std::string session;
    std::optional<DesktopAccountIdentity> confirmed;
    auto accountCalls = std::make_shared<std::atomic<unsigned>>(0);
    const DesktopHttpTransport::UploadSend accountWire = [accountCalls](const auto& config, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(config.sessionToken == "generated-t116-session" && request.method == "GET");
        if (request.path == "/desktop/settings/spaces") {
            assert(accountCalls->fetch_add(1) == 0);
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        }
        assert(request.path == "/api/v1/auth/me" && accountCalls->fetch_add(1) == 1);
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    };
    {
        auto owned = ownedAccount
            ? std::make_unique<NativeCapture>(fixture.root, AecSelection{std::make_shared<GeneratedAec>(), true}, accountWire)
            : std::make_unique<NativeCapture>(fixture.root, AecSelection{std::make_shared<GeneratedAec>(), true});
        auto& capture = *owned;
        startAndAdopt(capture, 1);
        if (ownedAccount) {
            capture.setAuthSessionToken("generated-t116-session");
            assert(waitFor([&] { capture.pollUploads(); return capture.currentAccount().has_value(); }));
            confirmed = capture.currentAccount(); // Production resolver/adoption, never a private account setter.
            assert(accountCalls->load() == 2);
        }
        assert(!capture.localQueueComplete() && !capture.readiness().storageWritable);
        assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::requestRecording(capture); }));
        const bool prepared = waitFor([&] {
            capture.pollUploads();
            return NativeCaptureStorageTestPeer::prepared(capture);
        });
        if (!prepared) NativeCaptureStorageTestPeer::diagnosePreparation(capture);
        assert(prepared);
        session = capture.sessionId();
        auto before = NativeCaptureStorageTestPeer::projection(capture);
        assert(before && before->items().empty());
        std::atomic<bool> emit{false};
        CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(capture),
            generatedProducer(capture, emit, AudioSource::systemRender),
            generatedProducer(capture, emit, AudioSource::microphone, test == VerticalCase::lateDevice));
        ReadinessInputs hardware;
        hardware.microphonePermissionGranted = hardware.microphoneEndpointReady =
            hardware.renderEndpointReady = hardware.formatNormalizationReady = hardware.aecReady = true;
        hardware.aacEncoderReady = true;
        assert(!hardware.storageWritable); // Peer never grants storage readiness.
        (void)NativeCaptureStorageTestPeer::startPrepared(capture, hardware);
        assert(waitFor([&] { capture.pollHealth(); return capture.indicator().state == SessionState::recording; }));
        if (privacyFlow) {
            (void)capture.pause();
            assert(waitFor([&] {
                capture.pollHealth();
                return !capture.privacyPending() && capture.indicator().state == SessionState::paused;
            }));
        }
        emit.store(true);
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(180);
        while (NativeCaptureStorageTestPeer::writtenFrames(capture) != 3000) {
            capture.pollHealth();
            assert(capture.indicator().state == (privacyFlow ? SessionState::paused : SessionState::recording));
            assert(std::chrono::steady_clock::now() < deadline);
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }
        std::fprintf(stderr, "V5_CASE=%u stage=frames_3000\n", static_cast<unsigned>(test));
        if (privacyFlow) {
            (void)capture.resume();
            assert(waitFor([&] {
                capture.pollHealth();
                return !capture.privacyPending() && capture.indicator().state == SessionState::recording;
            }));
            (void)capture.pause();
            assert(waitFor([&] {
                capture.pollHealth();
                return !capture.privacyPending() && capture.indicator().state == SessionState::paused;
            }));
            // Stop must close this second genuine durable OPEN without Resume.
        }
        if (losePoll) {
            if (test == VerticalCase::nativeStopFault)
                CaptureSessionTestPeer::lateStopFailure(NativeCaptureStorageTestPeer::controller(capture));
            {
                std::lock_guard<std::mutex> lock(cutMutex);
                cutReached = cutReleased = false;
            }
            ioCut.store(IoCut::pauseAfterFlush);
            if (test == VerticalCase::lateUi) {
                (void)capture.stop();
                assert(waitFor([&] {
                    return CaptureSessionTestPeer::completed(NativeCaptureStorageTestPeer::controller(capture));
                }));
                // No health poll: on-time native completion must not become a
                // timeout when the UI owner is destroyed after the real deadline.
                std::this_thread::sleep_for(std::chrono::milliseconds(5'200));
            }
            // The real controller destructor joins acquisition/dispatcher. Its
            // owner must hand off EOS/finalization without another UI callback.
            owned.reset();
            {
                std::unique_lock<std::mutex> lock(cutMutex);
                assert(cutWake.wait_for(lock, std::chrono::seconds(10), [] { return cutReached; }));
            }
            WindowsDesktopSession second("cannot-overtake-native-finalizer");
            assert(second.beginReadinessCheck().reason == ReasonCode::activeSessionExists);
            ioCut.store(IoCut::none);
            {
                std::lock_guard<std::mutex> lock(cutMutex);
                cutReleased = true; cutWake.notify_all();
            }
            before.reset();
            assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }, std::chrono::seconds(180)));
            std::fprintf(stderr, "V5_CASE=%u stage=abandoned_worker_released\n", static_cast<unsigned>(test));
            assert(second.beginReadinessCheck().accepted());
            assert(second.block(ReasonCode::microphonePermissionDenied).accepted());
        } else {
            (void)capture.stop();
            // Drive the real EOS/finalizer but withhold queue adoption. A completed
            // encoder is not savedLocal and cannot publish a private candidate.
            while (!NativeCaptureStorageTestPeer::resultReady(capture)) {
                capture.pollHealth();
                assert(capture.indicator().state != SessionState::savedLocal);
                assert(std::chrono::steady_clock::now() < deadline);
                std::this_thread::sleep_for(std::chrono::milliseconds(5));
            }
            assert(NativeCaptureStorageTestPeer::projection(capture) == before);
            std::fprintf(stderr, "V5_CASE=%u stage=finalized\n", static_cast<unsigned>(test));
            assert(!capture.updateWorkDrained());
            if (staleEpoch) {
                capture.setAuthSessionToken("generated-not-a-session");
                capture.setAuthSessionToken({}); // Cleared before poll: never auth/network IO.
            }
            capture.pollUploads();
            assert(waitFor([&] {
                capture.pollHealth();
                return capture.indicator().state == (staleEpoch ? SessionState::failed : SessionState::savedLocal);
            }));
            const auto ticket = NativeCaptureStorageTestPeer::ticket(capture); assert(ticket);
            assert(ticket->state == NativeCapture::QueueTicketState::committed);
            assert(ticket->baseGeneration == 1 && ticket->targetGeneration == 2);
            const auto after = NativeCaptureStorageTestPeer::projection(capture);
            assert(after && after->items().size() == 1 && std::string_view(after->items()[0].sessionId) == session);
            assert(after->items()[0].status == UploadQueueStatus::pending);
            assert(!capture.readiness().storageWritable && !capture.localQueueComplete() && !capture.uploadsBusy());
            capture.shutdown();
            assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        }
    }
    for (const auto& entry : std::filesystem::recursive_directory_iterator(fixture.root)) {
        if (!entry.is_regular_file()) continue;
        const auto name = entry.path().filename().wstring();
        assert(name != L"canonical-mix.f32" && name != L"media.wav" && name != L"playback.m4a" &&
            name != L"manifest.json" && name != L"recovery.json" && entry.path().extension() != L".tmp");
    }
    // Cold, independent semantic/hash/payload verification after worker release.
    std::fprintf(stderr, "V5_CASE=%u stage=cold_read\n", static_cast<unsigned>(test));
    auto inspection = std::async(std::launch::async, [&] {
        auto cancellation = std::make_shared<std::atomic<bool>>(false);
        auto store = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(store.ok());
        assert((*store.value)->queueGeneration() == 2);
        auto pair = (*store.value)->readPackage(session, cancellation);
        assert(pair.ok());
        if (privacyFlow) {
            const auto bytes = readGeneratedManifest(fixture.root, *pair.value, cancellation);
            const std::string_view json(reinterpret_cast<const char*>(bytes.data()), bytes.size());
            const auto count = [&](std::string_view field) {
                std::size_t matches = 0, position = 0;
                while ((position = json.find(field, position)) != std::string_view::npos) {
                    ++matches; position += field.size();
                }
                return matches;
            };
            assert(count("\"segmentId\":") == 2 && count("\"endMonotonicMs\":") == 2);
            assert(count("\"localMicTreatment\":\"silenced\"") == 2);
            std::fprintf(stderr, "PRIVACY_FLOW two_durable_segments_closed=1\n");
        }
        std::shared_ptr<const ProtectedUploadQueueValue> queueSnapshot;
        if (ownedUpload) {
            auto queue = (*store.value)->readQueueValue(cancellation); assert(queue.ok() && (*queue.value)->items().size() == 1);
            queueSnapshot = *queue.value;
            const auto& row = queueSnapshot->items()[0];
            assert(confirmed && row.status == UploadQueueStatus::pending);
        }
        store.value.reset(); // The returned pair must retain its own genuine native root/identity leases.
        assert((*pair.value)->current().phase == (degraded ? CustodyPackagePhase::sealedDegraded : CustodyPackagePhase::sealedNormal));
        std::optional<ProtectedUploadExpected> expected;
        if (ownedUpload) expected.emplace(readProtectedUploadExpected(fixture, *pair.value, cancellation));
        auto proof = LocalRecordingPackage::inspectProtected(fixture.root, *pair.value, session, cancellation);
        assert(proof.ok());
        assert((*proof.value)->evidence().integrity == (degraded ? PackageIntegrity::degraded : PackageIntegrity::valid));
        assert((*proof.value)->evidence().durationMs == 30'000);
        if (degraded) assert((*proof.value)->evidence().trustedPrefixFrames == 3000);
        else assert((*proof.value)->evidence().playback.decodedFrames > 0);
        if (ownedUpload) protectedUploadFromCold(fixture, session, *confirmed, *proof.value, *expected, cancellation, queueSnapshot->items()[0]);
    });
    inspection.get();
    std::fprintf(stderr, "V5_CASE=%u stage=cold_read_verified\n", static_cast<unsigned>(test));
    if (scheduledUpload) {
        accountCalls->store(0); // First resolver and all native owners have drained.
        auto uploadCalls = std::make_shared<std::atomic<unsigned>>(0);
        std::mutex networkMutex;
        std::condition_variable networkWake;
        bool networkReleased = !stopPrepared;
        const DesktopHttpTransport::ProtectedUploadSend uploadWire = [&](const auto& config, const auto& request) {
            assert(config.sessionToken == "generated-t116-session" && config.cancellation && !config.cancellation->load());
            assert(request.method == "GET" && request.path.find("/sync-state?") != std::string_view::npos);
            assert(uploadCalls->fetch_add(1) == 0);
            std::unique_lock<std::mutex> lock(networkMutex);
            networkWake.wait(lock, [&] { return networkReleased; });
            ioCut.store(resultCut); // Actual queue-result commit, never prepare or package inspection.
            return DesktopHttpTransport::ProtectedUploadResponse{503, "{}", false, {}, "123456"};
        };
        std::atomic<bool> activeEmit{false};
        NativeCapture scheduled(fixture.root, {std::make_shared<GeneratedAec>(), true}, accountWire, uploadWire);
        startAndAdopt(scheduled, 2);
        unsigned expiryCalls = 0;
        scheduled.setSessionExpiryHandler([&](auto deadline) { assert(deadline == 123456); ++expiryCalls; });
        scheduled.setAuthSessionToken("generated-t116-session");
        std::string activeSession;
        if (inspectionActiveStop) {
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(scheduled); return scheduled.currentAccount().has_value(); }));
            assert(NativeCaptureStorageTestPeer::requestRecording(scheduled));
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::prepared(scheduled); }));
            activeSession = scheduled.sessionId();
            assert(activeSession != session);
            CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(scheduled),
                generatedProducer(scheduled, activeEmit, AudioSource::systemRender),
                generatedProducer(scheduled, activeEmit, AudioSource::microphone));
            ReadinessInputs hardware;
            hardware.microphonePermissionGranted = hardware.microphoneEndpointReady = hardware.renderEndpointReady =
                hardware.formatNormalizationReady = hardware.aecReady = hardware.aacEncoderReady = true;
            assert(!hardware.storageWritable);
            (void)NativeCaptureStorageTestPeer::startPrepared(scheduled, hardware);
            assert(waitFor([&] { scheduled.pollHealth(); return scheduled.indicator().state == SessionState::recording; }));
            activeEmit.store(true);
            assert(waitFor([&] {
                scheduled.pollHealth();
                assert(scheduled.indicator().state == SessionState::recording);
                return NativeCaptureStorageTestPeer::writtenFrames(scheduled) == 3000;
            }, std::chrono::seconds(180)));
        }
        assert(waitFor([&] { scheduled.pollUploads(); return scheduled.currentAccount().has_value(); }));
        assert(accountCalls->load() == 2);
        assert(waitFor([&] {
            const auto ticket = NativeCaptureStorageTestPeer::workerTicket(scheduled);
            return ticket.kind == NativeCapture::QueueMutationKind::uploadPrepare && ticket.state != NativeCapture::QueueTicketState::pending;
        }));
        const auto prepare = NativeCaptureStorageTestPeer::workerTicket(scheduled);
        std::fprintf(stderr, "PROTECTED_SCHEDULER prepare_state=%u base=%llu target=%llu wire=%u\n",
            static_cast<unsigned>(prepare.state), static_cast<unsigned long long>(prepare.baseGeneration),
            static_cast<unsigned long long>(prepare.targetGeneration), uploadCalls->load());
        std::fflush(stderr);
        assert(prepare.state == NativeCapture::QueueTicketState::committed && prepare.baseGeneration == 2 &&
            prepare.targetGeneration == 3 && "protected_nonempty_prepare_requires_durable_ack");
        // No UI poll during either physical commit: network/effects must wait
        // for the exact ACK, not just the completed worker or its disk write.
        assert(NativeCaptureStorageTestPeer::generation(scheduled) == 2 && uploadCalls->load() == 0);
        assert(scheduled.uploadsBusy());
        if (inspectionPrepared || inspectionActiveStop) {
            oldPackedPath = L"\\\\?\\" + (fixture.root / session / L".custody-v1" / L"canonical" / L"content.packed-v2").native();
            { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
            pauseOldPackedRead.store(true);
        }
        scheduled.pollUploads();
        if (inspectionActiveStop) {
            assert(waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }, std::chrono::seconds(180)));
            assert(!pauseOldPackedRead.load() && uploadCalls->load() == 0);
            (void)scheduled.stop();
            const bool serviced = waitFor([&] {
                scheduled.pollHealth();
                const auto& controller = NativeCaptureStorageTestPeer::controller(scheduled);
                return CaptureSessionTestPeer::completed(controller) && CaptureSessionTestPeer::bothEndsProcessed(controller) &&
                    NativeCaptureStorageTestPeer::finalizationServiced(scheduled, activeSession);
            });
            std::fprintf(stderr, "PROTECTED_INSPECTION active_stop_cut_held=1 both_eos_finalize_serviced=%u wire=%u\n",
                serviced ? 1U : 0U, uploadCalls->load());
            std::fflush(stderr);
            // Observe service, never await full AAC/queue finalization under the old IO cut.
            { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
            cutWake.notify_all();
            const bool finalized = waitFor([&] {
                return NativeCaptureStorageTestPeer::resultReady(scheduled) &&
                    NativeCaptureStorageTestPeer::workerTicket(scheduled).kind == NativeCapture::QueueMutationKind::recording;
            }, std::chrono::seconds(180));
            const auto recordingTicket = NativeCaptureStorageTestPeer::workerTicket(scheduled);
            std::fprintf(stderr, "PROTECTED_INSPECTION active_recording_result=%u state=%u base=%llu target=%llu error=%u native=%u\n",
                finalized ? 1U : 0U, static_cast<unsigned>(recordingTicket.state),
                static_cast<unsigned long long>(recordingTicket.baseGeneration),
                static_cast<unsigned long long>(recordingTicket.targetGeneration),
                static_cast<unsigned>(recordingTicket.error), recordingTicket.nativeError);
            std::fflush(stderr);
            if (!serviced || !finalized || recordingTicket.state != NativeCapture::QueueTicketState::committed) {
                scheduled.shutdown();
                assert(waitFor([&] {
                    scheduled.pollUploads(); scheduled.pollHealth();
                    return scheduled.shutdownWorkDrained();
                }, std::chrono::seconds(180)));
                assert(serviced && "cold_inspection_must_not_block_active_stop_service");
                assert(finalized && recordingTicket.state == NativeCapture::QueueTicketState::committed &&
                    "active_stop_must_preserve_sealed_recording");
            }
            assert(recordingTicket.changed && recordingTicket.error == CustodyFileError::none &&
                recordingTicket.baseGeneration == 3 && recordingTicket.targetGeneration == 4);
            assert(NativeCaptureStorageTestPeer::generation(scheduled) == 3 &&
                NativeCaptureStorageTestPeer::projection(scheduled)->items().size() == 1 && expiryCalls == 0);
            scheduled.pollUploads(); // Recording adoption only, not upload-result adoption.
            assert(NativeCaptureStorageTestPeer::generation(scheduled) == 4);
            assert(waitFor([&] { scheduled.pollHealth(); return scheduled.indicator().state == SessionState::savedLocal; }));
            assert(waitFor([&] {
                return NativeCaptureStorageTestPeer::resultReady(scheduled) &&
                    NativeCaptureStorageTestPeer::workerTicket(scheduled).kind == NativeCapture::QueueMutationKind::uploadResult;
            }, std::chrono::seconds(180)));
            const auto uploadTicket = NativeCaptureStorageTestPeer::workerTicket(scheduled);
            assert(uploadTicket.id != recordingTicket.id && uploadTicket.state == NativeCapture::QueueTicketState::committed &&
                uploadTicket.error == CustodyFileError::none && uploadTicket.baseGeneration == 4 && uploadTicket.targetGeneration == 5);
            assert(uploadCalls->load() == 1 && expiryCalls == 0);
            scheduled.pollUploads();
            assert(NativeCaptureStorageTestPeer::generation(scheduled) == 5 && expiryCalls == 1);
            assert(waitFor([&] { scheduled.pollUploads(); return !scheduled.uploadsBusy(); }, std::chrono::seconds(180)));
            const auto verifyRows = [&](const NativeCapture& capture) {
                const auto queue = NativeCaptureStorageTestPeer::projection(capture);
                assert(queue && queue->items().size() == 2);
                for (const auto& row : queue->items()) {
                    const bool old = std::string_view(row.sessionId) == session;
                    assert(old || std::string_view(row.sessionId) == activeSession);
                    assert(row.status == (old ? UploadQueueStatus::retry : UploadQueueStatus::pending));
                    assert(row.attempts == (old ? 1U : 0U));
                    assert(confirmed && std::string_view(row.ownerUserId) == confirmed->userId &&
                        std::string_view(row.ownerWorkspaceId) == confirmed->workspaceId);
                }
                assert(!capture.localQueueComplete() && !capture.readiness().storageWritable);
            };
            verifyRows(scheduled);
            scheduled.shutdown();
            assert(waitFor([&] { scheduled.pollUploads(); return scheduled.shutdownWorkDrained(); }, std::chrono::seconds(180)));
            oldPackedPath.clear();
            auto cold = std::async(std::launch::async, [&] {
                auto cancellation = std::make_shared<std::atomic<bool>>(false);
                auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(opened.ok());
                assert((*opened.value)->queueGeneration() == 5);
                auto pair = (*opened.value)->readPackage(activeSession, cancellation); assert(pair.ok());
                opened.value.reset();
                assert((*pair.value)->current().phase == CustodyPackagePhase::sealedNormal);
                auto proof = LocalRecordingPackage::inspectProtected(fixture.root, *pair.value, activeSession, cancellation);
                assert(proof.ok() && (*proof.value)->evidence().integrity == PackageIntegrity::valid &&
                    (*proof.value)->evidence().durationMs == 30'000 && (*proof.value)->evidence().playback.decodedFrames > 0);
            });
            cold.get();
            NativeCapture durable(fixture.root, {std::make_shared<GeneratedAec>(), true});
            startAndAdopt(durable, 5);
            verifyRows(durable);
            durable.shutdown();
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(durable); }));
            assert(uploadCalls->load() == 1 && expiryCalls == 1);
            std::fputs("PROTECTED_INSPECTION active_stop_both_eos_sealed_adoption_restart5=pass\n", stderr);
            return;
        }
        if (inspectionPrepared) {
            assert(waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }, std::chrono::seconds(180)));
            assert(!pauseOldPackedRead.load() && uploadCalls->load() == 0);
            assert(NativeCaptureStorageTestPeer::requestRecording(scheduled));
            const bool actuallyPrepared = waitFor([&] { return NativeCaptureStorageTestPeer::prepared(scheduled); });
            const bool preparationQueued = NativeCaptureStorageTestPeer::preparationQueued(scheduled);
            const bool preparationInProgress = NativeCaptureStorageTestPeer::preparationInProgress(scheduled);
            if (!actuallyPrepared) NativeCaptureStorageTestPeer::diagnosePreparation(scheduled);
            std::fprintf(stderr, "PROTECTED_INSPECTION cut_held=1 actual_prepared=%u preparation_queued=%u wire=%u\n",
                actuallyPrepared ? 1U : 0U, preparationQueued ? 1U : 0U, uploadCalls->load());
            std::fflush(stderr);
            std::fprintf(stderr, "PROTECTED_INSPECTION preparation_in_progress=%u\n", preparationInProgress ? 1U : 0U);
            std::fflush(stderr);
            scheduled.shutdown(); // Cancel before any wire; do not await drain with the IO cut held.
            { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
            cutWake.notify_all();
            assert(waitFor([&] { scheduled.pollUploads(); return scheduled.shutdownWorkDrained(); }, std::chrono::seconds(180)));
            oldPackedPath.clear();
            assert(uploadCalls->load() == 0 && expiryCalls == 0);
            assert((actuallyPrepared || preparationQueued || preparationInProgress) && "inspection_test_must_not_misclassify_factory_refusal");
            assert(actuallyPrepared && "cold_inspection_must_not_block_actual_recording_preparation");
            std::fputs("PROTECTED_INSPECTION prepared_during_packed_io_cancel_zero_wire_drained=pass\n", stderr);
            return;
        }
        if (stopPrepared) {
            assert(waitFor([&] { return uploadCalls->load() == 1; }, std::chrono::seconds(180)));
            // An existing HTTP call must not occupy the storage command slot.
            assert(NativeCaptureStorageTestPeer::requestRecording(scheduled));
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::prepared(scheduled); }));
            { std::lock_guard<std::mutex> lock(networkMutex); networkReleased = true; }
            networkWake.notify_all();
        }
        assert(waitFor([&] {
            return NativeCaptureStorageTestPeer::resultReady(scheduled) &&
                NativeCaptureStorageTestPeer::workerTicket(scheduled).kind == NativeCapture::QueueMutationKind::uploadResult &&
                NativeCaptureStorageTestPeer::workerTicket(scheduled).baseGeneration == 3;
        }, std::chrono::seconds(180)));
        const auto result = NativeCaptureStorageTestPeer::workerTicket(scheduled);
        if (resultCut != IoCut::none) {
            assert(result.state == (resultCut == IoCut::ambiguousRename ?
                NativeCapture::QueueTicketState::ambiguous : NativeCapture::QueueTicketState::notCommitted));
            assert(uploadCalls->load() == 1 && expiryCalls == 0 && scheduled.uploadsBusy());
            assert(NativeCaptureStorageTestPeer::generation(scheduled) == 3);
            ioCut.store(IoCut::none);
            CustodyAllocator<char> allocator;
            if (refuseReopen) {
                { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
                pauseReopenRead.store(true);
            }
            scheduled.pollUploads(); // ACK the failed operation, not physical publication.
            if (refuseReopen) {
                assert(waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }));
                // Reserve after failed native owners have actually drained, not
                // before their teardown could free enough quota for a reopen.
                const auto reserved = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
                auto* reservation = allocator.allocate(reserved);
                { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
                cutWake.notify_all();
                assert(waitFor([&] { return NativeCaptureStorageTestPeer::reconciliationPending(scheduled); }));
                assert(NativeCaptureStorageTestPeer::storageError(scheduled) == CustodyFileError::allocationFailed);
                assert(scheduled.uploadsBusy() && !scheduled.updateWorkDrained());
                assert(NativeCaptureStorageTestPeer::generation(scheduled) == 3 && expiryCalls == 0);
                allocator.deallocate(reservation, reserved);
                scheduled.setAuthSessionToken(""); // Storage validation must not require a signed-in account.
                scheduled.recover(RecoveryTrigger::networkRecovered);
                assert(!scheduled.currentAccount());
                scheduled.pollUploads();
                assert(waitFor([&] { return NativeCaptureStorageTestPeer::physicalReadback(scheduled); }));
                assert(scheduled.uploadsBusy() && NativeCaptureStorageTestPeer::generation(scheduled) == 3);
                scheduled.setUpdateAdmissionBlocked(true); // Physical ACK during update: no effects or new HTTP.
                assert(waitFor([&] { scheduled.pollUploads(); return scheduled.updateWorkDrained(); }));
            } else {
                assert(waitFor([&] { return NativeCaptureStorageTestPeer::physicalReadback(scheduled); }));
                assert(scheduled.uploadsBusy() && NativeCaptureStorageTestPeer::generation(scheduled) == 3);
                scheduled.pollUploads(); // Physical truth only; original failed ticket stays failed.
                assert(waitFor([&] { scheduled.pollUploads(); return !scheduled.uploadsBusy(); }));
            }
            const auto generation = resultCut == IoCut::ambiguousRename ? 4U : 3U;
            assert(NativeCaptureStorageTestPeer::generation(scheduled) == generation);
            assert(expiryCalls == 0 && uploadCalls->load() == 1);
            assert(NativeCaptureStorageTestPeer::ticket(scheduled)->state == result.state);
            scheduled.shutdown();
            assert(waitFor([&] { scheduled.pollUploads(); return scheduled.shutdownWorkDrained(); }));
            NativeCapture durable(fixture.root, {std::make_shared<GeneratedAec>(), true});
            startAndAdopt(durable, generation);
            const auto& row = NativeCaptureStorageTestPeer::projection(durable)->items()[0];
            assert(row.status == (generation == 4 ? UploadQueueStatus::retry : UploadQueueStatus::pending));
            assert(row.attempts == (generation == 4 ? 1U : 0U));
            durable.shutdown();
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(durable); }));
            std::fprintf(stderr, "PROTECTED_SCHEDULER failed_result_physical_readback=pass published=%u quota_refused=%u\n",
                generation == 4 ? 1U : 0U, refuseReopen ? 1U : 0U);
            return;
        }
        assert(result.state == NativeCapture::QueueTicketState::committed && result.targetGeneration == 4);
        assert(uploadCalls->load() == 1 && expiryCalls == 0);
        assert(scheduled.uploadsBusy());
        if (stopPrepared) {
            scheduled.shutdown(); // Busy result ACK must not strand the prepared, unstarted recording.
            assert(waitFor([&] { scheduled.pollUploads(); return scheduled.shutdownWorkDrained(); }));
            assert(expiryCalls == 0 && !scheduled.uploadsBusy());
            NativeCapture durable(fixture.root, {std::make_shared<GeneratedAec>(), true});
            startAndAdopt(durable, 4);
            assert(NativeCaptureStorageTestPeer::projection(durable)->items()[0].status == UploadQueueStatus::retry);
            durable.shutdown();
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(durable); }));
            std::fputs("PROTECTED_SCHEDULER stop_prepared_while_result_busy=pass\n", stderr);
            return;
        }
        assert(NativeCaptureStorageTestPeer::generation(scheduled) == 3 &&
            NativeCaptureStorageTestPeer::projection(scheduled)->items()[0].status == UploadQueueStatus::pending);
        scheduled.pollUploads();
        assert(NativeCaptureStorageTestPeer::generation(scheduled) == 4 && expiryCalls == 1);
        const auto& row = NativeCaptureStorageTestPeer::projection(scheduled)->items()[0];
        assert(row.status == UploadQueueStatus::retry && row.attempts == 1 && row.safeReason == "transport_unavailable");
        scheduled.pollUploads();
        assert(NativeCaptureStorageTestPeer::generation(scheduled) == 4 && uploadCalls->load() == 1 && expiryCalls == 1);
        assert(!scheduled.localQueueComplete() && !scheduled.readiness().storageWritable);
        scheduled.shutdown();
        assert(waitFor([&] { scheduled.pollUploads(); return scheduled.shutdownWorkDrained(); }));
        NativeCapture durable(fixture.root, {std::make_shared<GeneratedAec>(), true});
        startAndAdopt(durable, 4);
        assert(NativeCaptureStorageTestPeer::projection(durable)->items()[0].status == UploadQueueStatus::retry);
        assert(NativeCaptureStorageTestPeer::projection(durable)->items()[0].attempts == 1);
        durable.shutdown();
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(durable); }));
        std::fputs("PROTECTED_SCHEDULER generated_recording_cold_prepare_network_result_adoption=pass\n", stderr);
        return;
    }
    NativeCapture restarted(fixture.root, {std::make_shared<GeneratedAec>(), true});
    startAndAdopt(restarted, 2);
    assert(NativeCaptureStorageTestPeer::projection(restarted)->items().size() == 1);
    assert(std::string_view(NativeCaptureStorageTestPeer::projection(restarted)->items()[0].sessionId) == session);
    assert(NativeCaptureStorageTestPeer::projection(restarted)->items()[0].status ==
        (degraded ? UploadQueueStatus::quarantined : UploadQueueStatus::pending));
    assert(!restarted.localQueueComplete());
    restarted.shutdown();
    assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(restarted); }));
    std::fprintf(stderr, "V5_CASE=%u stage=done\n", static_cast<unsigned>(test));
}
}
int main(int argc, char** argv) {
#ifdef _MSC_VER
    _set_error_mode(_OUT_TO_STDERR);
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
#endif
#if defined(_MSC_VER) && defined(_DEBUG)
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
#endif
    const auto baseline = CustodyOwnedMemory::usedBytes();
    {
        const CustodyBytes empty;
        idleOwnedBytes = CustodyOwnedMemory::usedBytes();
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
    if (argc == 2 && std::string_view(argv[1]) == "--protected-deletion-intent") {
        protectedDeletionIntent();
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-deletion-answer") {
        protectedDeletionAnswer();
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-deletion-continuation") {
        protectedDeletionContinuation();
        std::fprintf(stderr, "PROTECTED_DELETION_CONTINUATION owned=%zu baseline=%zu\n", CustodyOwnedMemory::usedBytes(), baseline);
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-deletion-application") {
        protectedDeletionApplication();
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-local-purge") {
        protectedLocalPurge();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-server-purge") {
        protectedServerPurge();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-manual-send") {
        protectedManualSend();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-local-removal") {
        protectedLocalPurge(true);
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-purge-flight") {
        protectedPurgeFlight();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-deletion-display") {
        protectedDeletionDisplayDrain();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-deletion-selection") {
        protectedDeletionSelection();
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
        return 0;
    }
    // ReadCache retains only its empty vector until process exit. Measure the
    // charged Debug iterator proxy, as in ProtectedCustodyWriteStreamTests;
    // all recording, payload and worker ownership must still drain exactly.
    std::fprintf(stderr, "NATIVE_STORAGE baseline=%zu empty_proxy=%zu\n", baseline, idleOwnedBytes - baseline);
    if (argc == 2 && std::string_view(argv[1]) == "--protected-live-metadata") {
        protectedLiveMetadataCheckpoint();
        protectedLiveMetadataCuts();
        protectedLiveMetadataFinalizeAndCorruption();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-privacy-manifest") {
        protectedPrivacyManifest();
        protectedPrivacyCheckpoints();
        protectedPrivacyCapacity();
        protectedPrivacyCloseCuts();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-privacy-flow") {
        protectedRecordingVerticalAndRestart(VerticalCase::normal, IoCut::none, false, false, false, false, true);
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-privacy-degraded") {
        protectedPrivacyDegraded();
        protectedPrivacyDegradedCuts();
        protectedPrivacyCapacity(true);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-scheduler") {
        protectedRecordingVerticalAndRestart(VerticalCase::scheduledUpload);
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-read-model") {
        birthAndRestart();
        unknownRootIsPreserved();
        recoveryCommitAndRestart();
        allocationFailurePreservesProjection();
        nativeCommitCuts();
        shutdownRecoveryAdmission();
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
        std::fputs("NATIVE_STORAGE protected_read_model=passed\n", stderr);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-account-problems") {
        protectedAccountProblems();
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
        std::fputs("NATIVE_STORAGE protected_account_problems=passed\n", stderr);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-display-owner-quota") {
        protectedDisplayOwnerQuota();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-display-timing") {
        protectedDisplayTimingAndRestart();
        std::fputs("NATIVE_STORAGE protected_display_timing=passed\n", stderr);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-birth-admission") {
        protectedPackageBirthAdmission();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-finalize-admission") {
        protectedFinalizeAdmission();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-encoder-write-failure") {
        protectedEncoderWriteFailure();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-live-born-inspection") {
        protectedLiveBornInspection();
        std::fputs("NATIVE_STORAGE protected_live_born_inspection=passed\n", stderr);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-package-revalidation") {
        protectedPackageRevalidation();
        std::fputs("NATIVE_STORAGE protected_package_revalidation=passed\n", stderr);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-playback-consumer") {
        protectedPlaybackConsumer();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-media-engine") {
        protectedMediaEngine();
        std::fputs("NATIVE_STORAGE protected_media_engine=passed\n", stderr);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-inspection-prepared") {
        protectedRecordingVerticalAndRestart(VerticalCase::scheduledUpload, IoCut::none, false, false, true);
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-inspection-active-stop") {
        protectedRecordingVerticalAndRestart(VerticalCase::scheduledUpload, IoCut::none, false, false, false, true);
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
    if (argc == 2 && (std::string_view(argv[1]) == "--protected-scheduler-ambiguous" ||
                     std::string_view(argv[1]) == "--protected-scheduler-not-committed" ||
                     std::string_view(argv[1]) == "--protected-scheduler-stop-prepared")) {
        const auto option = std::string_view(argv[1]);
        protectedRecordingVerticalAndRestart(VerticalCase::scheduledUpload,
            option == "--protected-scheduler-ambiguous" ? IoCut::ambiguousRename :
            option == "--protected-scheduler-not-committed" ? IoCut::flush : IoCut::none,
            option == "--protected-scheduler-ambiguous", option == "--protected-scheduler-stop-prepared");
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
    if (argc == 2 && (std::string_view(argv[1]) == "--protected-upload" ||
                     std::string_view(argv[1]) == "--protected-upload-control-types")) {
        enforceProtectedHttpControlTypes = std::string_view(argv[1]) == "--protected-upload";
        protectedRecordingVerticalAndRestart(VerticalCase::ownedUpload);
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
    assert(argc == 1);
    std::fputs("NATIVE_STORAGE stage=startup_recovery_faults\n", stderr);
    birthAndRestart();
    unknownRootIsPreserved();
    recoveryCommitAndRestart();
    allocationFailurePreservesProjection();
    nativeCommitCuts();
    coalescedIntentAndLostOwner();
    std::fputs("NATIVE_STORAGE stage=shutdown_recovery\n", stderr);
    shutdownRecoveryAdmission();
    std::fputs("NATIVE_STORAGE stage=blocked_recording\n", stderr);
    blockedRecordingDrains();
    protectedPackageDiscovery();
    protectedRecordingVerticalAndRestart();
    protectedRecordingVerticalAndRestart(VerticalCase::staleEpoch);
    protectedRecordingVerticalAndRestart(VerticalCase::lostPoll);
    protectedRecordingVerticalAndRestart(VerticalCase::nativeStopFault);
    protectedRecordingVerticalAndRestart(VerticalCase::lateDevice);
    protectedRecordingVerticalAndRestart(VerticalCase::lateUi);
    protectedRecordingVerticalAndRestart(VerticalCase::ownedUpload);
    assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
    std::puts("NativeCaptureStorageIntegrationTests: genuine startup/recovery commit/adoption/restart; full V5 consumers still pending");
}
