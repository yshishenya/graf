#ifdef NDEBUG
#undef NDEBUG
#endif
#include <atomic>
#include <cstdio>
namespace {
std::atomic<unsigned> recoveryReadyObservations{0};
std::atomic<const char*> lifecyclePhase{"entry"};
std::atomic<unsigned> lifecycleCase{0};
void observeUploadStage(unsigned, unsigned, unsigned) noexcept;
void observeStartBeforeFactory() noexcept;
}
#define GRAF_WINDOWS_TEST_RECOVERY_READY() recoveryReadyObservations.fetch_add(1, std::memory_order_release)
#define GRAF_WINDOWS_TEST_COLD_RECOVERY(stage, error, native) std::fprintf(stderr, "COLD_RECOVERY_RESULT stage=%u error=%u native=%u\n", stage, static_cast<unsigned>(error), native)
#define GRAF_WINDOWS_TEST_UPLOAD_STAGE(stage, first, second) observeUploadStage(stage, static_cast<unsigned>(first), static_cast<unsigned>(second))
#define GRAF_WINDOWS_TEST_START_BEFORE_FACTORY() observeStartBeforeFactory()
#include "../../RecApp/Recording/NativeCapture.h"
#include "../../RecApp/Audio/AudioNormalizer.h"
#undef GRAF_WINDOWS_TEST_RECOVERY_READY
#undef GRAF_WINDOWS_TEST_COLD_RECOVERY
#undef GRAF_WINDOWS_TEST_UPLOAD_STAGE
#undef GRAF_WINDOWS_TEST_START_BEFORE_FACTORY
#include "../../RecApp/Recording/LocalRecordingPackage.h"
#include "../../RecApp/Recording/ProtectedLocalRecordingPlayback.h"
#include "../../RecApp/Storage/Sha256.h"
#include "../GeneratedRecordingFixtures.h"
#include <cassert>
#include <chrono>
#include <charconv>
#include <cstddef>
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
#include <mfreadwrite.h>
#include <winternl.h>
#include <shellapi.h>
#include <aclapi.h>

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
struct UploadStageProbe {
    std::atomic<bool> armed{false};
    std::atomic<std::int64_t> originNs{0};
    std::array<std::atomic<std::int64_t>,13> reachedUs{}; // Relative microseconds + 1; zero means not reached.
    std::atomic<unsigned> inspectionError{0}, inspectionNative{0}, transportStatus{0}, transportPresent{0};
    std::array<std::atomic<std::uint64_t>,4> nativeCalls{}, nativeNs{};
} uploadStageProbe;
thread_local bool inspectionProfileActive = false;
void observeUploadStage(unsigned stage, unsigned first, unsigned second) noexcept {
    if (!uploadStageProbe.armed.load(std::memory_order_acquire)) return;
    const auto error = GetLastError();
    const auto now = std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    if (stage == 2) inspectionProfileActive = true;
    if (stage == 3 || stage == 6) inspectionProfileActive = false;
    if (stage == 3) { uploadStageProbe.inspectionError.store(first); uploadStageProbe.inspectionNative.store(second); }
    if (stage == 5) { uploadStageProbe.transportStatus.store(first); uploadStageProbe.transportPresent.store(second); }
    std::int64_t absent = 0;
    uploadStageProbe.reachedUs[stage].compare_exchange_strong(absent, (now - uploadStageProbe.originNs.load()) / 1000 + 1);
    SetLastError(error);
}
enum class IoCut { none, flush, ambiguousRename, pauseAfterFlush, pauseAfterRename };
std::atomic<IoCut> ioCut{IoCut::none};
std::atomic<unsigned> startOwnerFlushRole{0}; // 1=armed, 2=queue, 3=other; executable-only observation.
// Seven Start cuts plus eight concrete Native lifecycle cuts; each child has one exact event.
enum class StartOwnerCrashCut {
    beforeRename, afterRename, afterReadback, afterAdoption,
    packageBeforeIndex0, packageBeforeIndex1, packageAfterSemanticAck,
    afterEosBeforeSeal, beforeFinishQueue, afterFinishReadback, shortAfterRecycle, stopBeforeEos,
    shortAfterRetirementReadback, shortBeforeRecycle, normalAfterFinishAdoption
};
constexpr std::array<std::wstring_view,15> startOwnerCrashArguments{
    L"before-rename",L"after-rename",L"after-readback-before-adoption",
    L"after-adoption-before-factory",L"package-before-index0",
    L"package-between-indices-before-index1",L"package-after-semantic-ack-before-canonical",
    L"after-stop-two-eos-before-canonical-seal",L"before-finish-queue-index0",
    L"after-finish-readback-before-adoption",L"short-after-os-recycle-before-return",
    L"stop-accepted-before-two-eos",L"short-after-retirement-readback-before-adoption",
    L"short-after-positive-intent-before-os-recycle",L"normal-after-finish-adoption-before-terminal-ui"};
constexpr std::array<std::string_view,15> startOwnerCrashReceipts{
    "before_rename=1 native_calls=0 native_returns=0 native_success=0 committed=0 factory=0 devices=0 network=0 adopted=0",
    "after_rename=1 native_calls=1 native_returns=1 native_success=1 committed=0 factory=0 devices=0 network=0 adopted=0",
    "after_readback=1 native_calls=1 native_returns=1 native_success=1 committed=1 factory=0 devices=0 network=0 adopted=0",
    "after_adoption=1 native_calls=1 native_returns=1 native_success=1 committed=1 factory=0 devices=0 network=0 adopted=1",
    "package_before_index0=1 native_calls=1 native_returns=1 native_success=1 committed=1 factory=1 devices=0 network=0 adopted=1 package_calls=0,0 package_returns=0,0 semantic_ack=0 canonical=0",
    "package_before_index1=1 native_calls=1 native_returns=1 native_success=1 committed=1 factory=1 devices=0 network=0 adopted=1 package_calls=1,0 package_returns=1,0 semantic_ack=0 canonical=0",
    "package_semantic_ack=1 native_calls=1 native_returns=1 native_success=1 committed=1 factory=1 devices=0 network=0 adopted=1 package_calls=1,1 package_returns=1,1 semantic_ack=1 canonical=0",
    "after_stop_two_eos=1 frames=100 epoch_match=1 queue_calls=0 queue_returns=0 queue_committed=0 finish_adopted=0 phase=finalizing devices=2 device_audio=0 network=0 early_notice=0",
    "before_finish_index0=1 frames=100 epoch_match=1 queue_calls=0 queue_returns=0 queue_committed=0 finish_adopted=0 phase=sealed_normal devices=2 device_audio=0 network=0 early_notice=0",
    "after_finish_readback=1 frames=100 epoch_match=1 queue_calls=1 queue_returns=1 queue_committed=1 finish_adopted=0 phase=sealed_normal devices=2 device_audio=0 network=0 early_notice=0",
    "after_short_os=1 frames=100 epoch_match=1 queue_calls=1 queue_returns=1 queue_committed=1 finish_adopted=1 package_absent=1 os_attempts=1 os_effects=1 devices=2 device_audio=0 network=0 early_notice=0",
    "stop_accepted=1 dispatcher_native_hold=1 source_frames=100 written_frames=99 eos_queued=2 eos_processed=0 finalizer=0 queue_g=2 phase=capturing package_g=1 durable_frames=0 devices=2 device_audio=0 network=0 early_notice=0",
    "short_retirement_readback=1 frames=100 epoch_match=1 queue_g=3 rows=0 finish_adopted=0 phase=discard_pending package_unchanged=1 os_attempts=0 os_effects=0 devices=2 device_audio=0 network=0 early_notice=0",
    "short_before_recycle=1 frames=100 epoch_match=1 queue_g=3 rows=0 finish_adopted=1 phase=discard_pending positive_intent=1 owner_preflight=1 package_unchanged=1 os_attempts=0 os_effects=0 devices=2 device_audio=0 network=0 early_notice=0",
    "normal_after_adoption=1 frames=100 epoch_match=1 queue_g=3 rows=1 finish_adopted=1 native_terminal=1 ui_terminal=0 phase=sealed_normal package_unchanged=1 devices=2 device_audio=0 network=0 early_notice=0"};
std::atomic<bool> startOwnerCrashArmed{false};
struct StartOwnerCrashProof {
    NativeCapture* capture=nullptr;
    std::atomic<unsigned>* devices=nullptr;
    std::atomic<unsigned>* network=nullptr;
    std::ofstream* progress=nullptr;
    std::filesystem::path package;
    std::wstring queueDirectory, packageStateDirectory;
    StartOwnerCrashCut cut=StartOwnerCrashCut::afterRename;
    std::atomic<unsigned> nativeCalls{0}, nativeReturns{0};
    std::atomic<bool> nativeSucceeded{false};
    std::array<std::atomic<unsigned>,2> packageCalls{}, packageReturns{};
    std::array<std::atomic<bool>,2> packageSucceeded{};
    std::atomic<unsigned> beforeFactoryObservations{0};
    std::atomic<bool> emit{false}, stopReturned{false};
    std::atomic<unsigned> phase0Observations{0}, notices{0};
    std::atomic<DWORD> stopHoldThread{0};
    std::wstring stopCanonicalPath;
    std::string stopCanonicalHash;
    std::optional<std::map<std::wstring,std::string>> finalPackageSnapshot;
    std::uintptr_t preOsDirectory=0; // Borrowed only inside the existing recycle probe before actual service entry.
    std::shared_ptr<const ProtectedUploadQueueValue> reservation;
    std::uint64_t epoch=0, startTicket=0;
    static constexpr std::uint64_t frames=100; // Existing finalize-admission/short fixtures, not a reduced large fixture.
};
StartOwnerCrashProof* startOwnerCrash = nullptr;
void startOwnerCrashProof(const ProtectedCustodyRecordingPackage* born = nullptr);
[[noreturn]] void terminateStartOwnerCrash(const ProtectedCustodyRecordingPackage* born = nullptr);
void observeStartFinalizePhase(unsigned) noexcept;
void holdStartStopBeforeEos(HANDLE);
int protectedStartOwnerLifecycleChild(NativeCapture&, StartOwnerCrashProof&, const ReadinessInputs&);
enum class StartOwnerRenameRole { none, queue, package0, package1 };
StartOwnerRenameRole startOwnerCrashRename(HANDLE file, const void* input, ULONG length, FILE_INFORMATION_CLASS kind) {
    constexpr auto header = offsetof(FILE_RENAME_INFO, FileName);
    if (kind != static_cast<FILE_INFORMATION_CLASS>(10) || !input || length < header) return StartOwnerRenameRole::none;
    FILE_RENAME_INFO rename{};
    std::memcpy(&rename,input,header); // Read the documented ABI without aliasing the production RenameInfo.
    constexpr std::array<std::wstring_view,2> targets{L"index.0",L"index.1"};
    if (rename.ReplaceIfExists != TRUE || rename.RootDirectory || rename.FileNameLength != targets[0].size()*sizeof(wchar_t) ||
        rename.FileNameLength > length-header) return StartOwnerRenameRole::none;
    unsigned slot=0;
    if (std::memcmp(static_cast<const unsigned char*>(input)+header,targets[0].data(),rename.FileNameLength)) {
        if (std::memcmp(static_cast<const unsigned char*>(input)+header,targets[1].data(),rename.FileNameLength)) return StartOwnerRenameRole::none;
        slot=1;
    }
    wchar_t path[32768]{};
    const auto size = GetFinalPathNameByHandleW(file,path,32768,FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (!size || size >= 32768) return StartOwnerRenameRole::none;
    const std::wstring_view name(path,size);
    auto role=StartOwnerRenameRole::none;
    std::wstring_view directory;
    const unsigned queueSlot=startOwnerCrash->cut>=StartOwnerCrashCut::afterEosBeforeSeal ? 0U : 1U;
    if (slot==queueSlot && name.size()==startOwnerCrash->queueDirectory.size()+1+42 &&
        name.substr(0,startOwnerCrash->queueDirectory.size())==startOwnerCrash->queueDirectory) {
        directory=startOwnerCrash->queueDirectory; role=StartOwnerRenameRole::queue;
    } else if (startOwnerCrash->cut>=StartOwnerCrashCut::packageBeforeIndex0 &&
        startOwnerCrash->cut<=StartOwnerCrashCut::packageAfterSemanticAck &&
        name.size()==startOwnerCrash->packageStateDirectory.size()+1+42 &&
        name.substr(0,startOwnerCrash->packageStateDirectory.size())==startOwnerCrash->packageStateDirectory) {
        directory=startOwnerCrash->packageStateDirectory;
        role=slot ? StartOwnerRenameRole::package1 : StartOwnerRenameRole::package0;
    } else return StartOwnerRenameRole::none;
    if (name[directory.size()]!=L'\\') return StartOwnerRenameRole::none;
    const auto temporary=name.substr(directory.size()+1);
    return temporary.substr(0,10)==L"index.tmp-" &&
        std::all_of(temporary.begin()+10,temporary.end(),[](wchar_t c) { return (c>=L'0' && c<=L'9') || (c>=L'a' && c<=L'f'); })
        ? role : StartOwnerRenameRole::none;
}
std::atomic<bool> ambiguousRecordingQueue{false};
std::atomic<unsigned> liveMetadataRenameTarget{0}, liveMetadataRenameCount{0};
std::atomic<bool> liveMetadataRenameAfter{false};
std::atomic<bool> degradedManifestRenameCut{false};
std::mutex cutMutex;
std::condition_variable cutWake;
bool cutReached = false, cutReleased = false;
std::atomic<bool> pauseReopenRead{false};
std::atomic<bool> denyDeletionReadback{false}; // Armed only after the generated deletion's publication result.
std::atomic<bool> denyShortBootstrap{false};
std::atomic<unsigned> shortReadFailures{0};
// Opt-in diagnostic of this worker's intercepted native metadata calls only.
struct StorageProfile {
    bool active = false;
    std::array<std::uint64_t,4> calls{}, nanoseconds{};
};
thread_local StorageProfile storageProfile;
struct FinalizePhaseProfile {
    unsigned entered = 0, returned = 0, unwound = 0;
    std::chrono::steady_clock::time_point before{};
    std::uint64_t nanoseconds = 0;
    std::array<std::uint64_t,4> beforeCalls{}, beforeNative{}, calls{}, native{};
};
thread_local std::array<FinalizePhaseProfile,4> finalizeProfile;
std::atomic<bool> nativeFinalizePhaseLog{false};
enum class PlaybackCut { none, shortRead, cancel, output };
struct PlaybackProbe {
    bool armed = false, inStage = false;
    PlaybackCut cut = PlaybackCut::none;
    unsigned reads = 0, samples = 0, cutHits = 0;
    ULONG lastRead = 0;
    std::atomic<bool>* cancellation = nullptr;
};
thread_local PlaybackProbe playbackProbe;
float generatedPlaybackValue(std::uint64_t frame, std::size_t sample) {
    return static_cast<float>(static_cast<int>((frame*17+sample)%257)-128)/256.0F;
}
template<class Call> auto measuredStorageCall(std::size_t index, Call call) {
    if (!storageProfile.active && !inspectionProfileActive) return call();
    const auto incoming = GetLastError();
    const auto before = std::chrono::steady_clock::now();
    SetLastError(incoming);
    const auto result = call();
    const auto outgoing = GetLastError();
    const auto after = std::chrono::steady_clock::now();
    const auto nanoseconds = static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(after-before).count());
    if (storageProfile.active) {
        ++storageProfile.calls[index];
        storageProfile.nanoseconds[index] += nanoseconds;
    }
    if (inspectionProfileActive) {
        uploadStageProbe.nativeCalls[index].fetch_add(1, std::memory_order_relaxed);
        uploadStageProbe.nativeNs[index].fetch_add(nanoseconds, std::memory_order_relaxed);
    }
    SetLastError(outgoing);
    return result;
}
DWORD WINAPI profileFinalPath(HANDLE file, LPWSTR path, DWORD length, DWORD flags) {
    return measuredStorageCall(0, [&] { return GetFinalPathNameByHandleW(file,path,length,flags); });
}
BOOL WINAPI profileFileInfo(HANDLE file, FILE_INFO_BY_HANDLE_CLASS kind, LPVOID info, DWORD length) {
    const auto result=measuredStorageCall(1, [&] { return GetFileInformationByHandleEx(file,kind,info,length); });
    if (result && kind==FileIdInfo && startOwnerCrashArmed.load(std::memory_order_acquire) &&
        startOwnerCrash->cut==StartOwnerCrashCut::stopBeforeEos) holdStartStopBeforeEos(file);
    return result;
}
DWORD WINAPI profileSecurity(HANDLE file, SE_OBJECT_TYPE kind, SECURITY_INFORMATION requested,
    PSID* owner, PSID* group, PACL* dacl, PACL* sacl, PSECURITY_DESCRIPTOR* descriptor) {
    return measuredStorageCall(2, [&] { return GetSecurityInfo(file,kind,requested,owner,group,dacl,sacl,descriptor); });
}
HANDLE WINAPI profileFirstStream(LPCWSTR path, STREAM_INFO_LEVELS level, LPVOID data, DWORD flags) {
    return measuredStorageCall(3, [&] { return FindFirstStreamW(path,level,data,flags); });
}
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
// Last direct-upload cut only: observe real encrypted DATA reads, not a fake stream.
struct UploadReadCut {
    bool armed = false, firstComplete = false;
    unsigned dataHeaders = 0, failures = 0;
    std::uint64_t firstOffset = 0, secondOffset = 0, next = 0, end = 0;
    std::wstring path;
};
thread_local UploadReadCut uploadReadCut;
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
    if (denyShortBootstrap.load()) {
        wchar_t path[32768]{};
        const auto size = GetFinalPathNameByHandleW(file, path, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
        assert(size && size < 32768);
        if (std::wstring_view(path, size).find(L"\\bootstrap\\index.") != std::wstring_view::npos) {
            ++shortReadFailures;
            if (got) *got = 0;
            SetLastError(ERROR_READ_FAULT); return FALSE;
        }
    }
    if (denyDeletionReadback.load()) {
        ++shortReadFailures;
        if (got) *got = 0;
        SetLastError(ERROR_READ_FAULT); return FALSE;
    }
    if (pauseReopenRead.exchange(false)) pauseAtCut(); // Fresh native open after old owner/commit teardown.
    const auto result = ReadFile(file, bytes, length, got, overlapped);
    const auto error = GetLastError();
    if (result && length && got && *got == length && overlapped && uploadReadCut.armed) {
        auto& cut = uploadReadCut;
        wchar_t path[32768]{};
        const auto size = GetFinalPathNameByHandleW(file, path, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
        assert(size && size < 32768);
        const auto offset = (static_cast<std::uint64_t>(overlapped->OffsetHigh) << 32) | overlapped->Offset;
        if (std::wstring_view(path, size) == cut.path && offset >= ProtectedPackedCustodyFormat::appendOffset) {
            if (cut.dataHeaders == 1 && cut.next < cut.end && offset == cut.next) {
                assert(length <= cut.end - cut.next);
                cut.next += length; cut.firstComplete = cut.next == cut.end;
            } else {
                const auto* header = static_cast<const std::uint8_t*>(bytes);
                if (length >= 16 && std::memcmp(header, "GRFPEV2", 8) == 0 && header[8] == 2 && header[9] == 0 &&
                    header[10] == static_cast<std::uint8_t>(PackedRecordKind::data) &&
                    header[11] == static_cast<std::uint8_t>(CustodyRole::media)) {
                    std::uint32_t cipher = 0;
                    for (unsigned i = 0; i < 4; ++i) cipher |= static_cast<std::uint32_t>(header[12+i]) << (8*i);
                    assert(cipher && cipher <= ProtectedPackedCustodyFormat::blockBytes + 4096 - 16);
                    const auto envelope = std::uint64_t{16} + cipher;
                    assert(offset <= (std::numeric_limits<std::uint64_t>::max)() - envelope && length <= envelope);
                    if (++cut.dataHeaders == 1) {
                        cut.firstOffset = offset; cut.next = offset + length; cut.end = offset + envelope;
                        cut.firstComplete = cut.next == cut.end;
                    } else {
                        assert(cut.dataHeaders == 2 && cut.firstComplete && offset != cut.firstOffset);
                        cut.secondOffset = offset; cut.armed = false; ++cut.failures;
                        *got = 0; SetLastError(ERROR_READ_FAULT); return FALSE;
                    }
                }
            }
        }
    }
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
    if (result && startOwnerFlushRole.load() == 1) {
        const auto error = GetLastError();
        wchar_t path[32768]{};
        const auto size = GetFinalPathNameByHandleW(file, path, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
        assert(size && size < 32768);
        startOwnerFlushRole.store(std::wstring_view(path, size).find(L"\\queue\\") != std::wstring_view::npos ? 2U : 3U);
        SetLastError(error);
    }
    if (result && cut == IoCut::pauseAfterFlush) pauseAtCut();
    return result;
}
NTSTATUS NTAPI integrationRename(HANDLE file, PIO_STATUS_BLOCK io, PVOID info, ULONG length, FILE_INFORMATION_CLASS kind) {
    const auto incoming = GetLastError();
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
    const bool startCrashArmed = startOwnerCrashArmed.load(std::memory_order_acquire);
    const auto startRole = startCrashArmed ? startOwnerCrashRename(file,info,length,kind) : StartOwnerRenameRole::none;
    const bool startCrash = startRole==StartOwnerRenameRole::queue;
    const bool packageCrash = startRole==StartOwnerRenameRole::package0 || startRole==StartOwnerRenameRole::package1;
    const unsigned packageSlot = startRole==StartOwnerRenameRole::package1 ? 1U : 0U;
    if (startCrashArmed) SetLastError(incoming);
    if (startCrash && startOwnerCrash->cut==StartOwnerCrashCut::beforeRename) {
        assert(startOwnerCrashArmed.exchange(false));
        startOwnerCrashProof();
        std::fputs("START_OWNER_CRASH before_native_rename=1 native_calls=0 native_returns=0 destructors=0\n",stderr);
        std::fflush(stderr);
        assert(TerminateProcess(GetCurrentProcess(),88));
        std::abort(); // Never enter the actual native function for this cut.
    }
    if (startCrash && startOwnerCrash->cut==StartOwnerCrashCut::beforeFinishQueue) {
        assert(startOwnerCrashArmed.exchange(false));
        terminateStartOwnerCrash(); // Exact queue/index.0, before the actual g2->g3 native rename.
    }
    if (packageCrash && ((packageSlot==0 && startOwnerCrash->cut==StartOwnerCrashCut::packageBeforeIndex0) ||
        (packageSlot==1 && startOwnerCrash->cut==StartOwnerCrashCut::packageBeforeIndex1))) {
        assert(startOwnerCrashArmed.exchange(false));
        terminateStartOwnerCrash(); // Before the actual selected package-state rename.
    }
    if (startCrash) ++startOwnerCrash->nativeCalls;
    if (packageCrash) ++startOwnerCrash->packageCalls[packageSlot];
    const auto result = function(file, io, info, length, kind);
    const auto outgoing = startCrashArmed ? GetLastError() : ERROR_SUCCESS;
    if (startCrash) {
        ++startOwnerCrash->nativeReturns;
        startOwnerCrash->nativeSucceeded.store(result==0 && io && io->Status==0);
    }
    if (packageCrash) {
        ++startOwnerCrash->packageReturns[packageSlot];
        startOwnerCrash->packageSucceeded[packageSlot].store(result==0 && io && io->Status==0);
    }
    if (startCrash && startOwnerCrash->cut==StartOwnerCrashCut::afterRename && result == 0 && io && io->Status == 0) {
        assert(startOwnerCrashArmed.exchange(false) && startOwnerCrash);
        SetLastError(outgoing);
        startOwnerCrashProof();
        std::fputs("START_OWNER_CRASH after_native_rename=1 native_status=0 io_status=0 destructors=0\n",stderr);
        std::fflush(stderr);
        assert(TerminateProcess(GetCurrentProcess(),88));
        std::abort(); // Successful native termination never returns to publishIndex.
    }
    if (startCrashArmed) SetLastError(outgoing); // Unarmed: retain the existing GetProcAddress/native-call behavior.
    if (result == 0 && ambiguousRecordingQueue.load()) {
        wchar_t path[32768]{};
        const auto size = GetFinalPathNameByHandleW(file, path, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
        assert(size && size < 32768);
        if (std::wstring_view(path, size).find(L"\\queue\\") != std::wstring_view::npos && ambiguousRecordingQueue.exchange(false)) {
            assert(io->Status == 0);
            io->Status = static_cast<NTSTATUS>(0xC0000022UL);
            std::fputs("START_OWNER final_queue_ambiguous qualified_role=1 actual_rename=1\n", stderr);
        }
    }
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
namespace graf::windows {
bool finalizePhaseAdapterForTest(bool (*operation)());
void observeProtectedInspectionPhase(unsigned stage) noexcept {
    if (inspectionProfileActive) observeUploadStage(stage, 0, 0);
}
void beginFinalizePhase(unsigned stage) noexcept {
    observeStartFinalizePhase(stage); // Existing integration-only observer; ordinary V5 compilation is unchanged.
    playbackProbe.inStage = stage == 2;
    const bool log = nativeFinalizePhaseLog.load();
    if (!storageProfile.active && !log) return;
    const auto error = GetLastError();
    assert(stage < finalizeProfile.size());
    auto& phase = finalizeProfile[stage];
    ++phase.entered;
    phase.beforeCalls = storageProfile.calls; phase.beforeNative = storageProfile.nanoseconds;
    phase.before = std::chrono::steady_clock::now();
    if (log) {
        std::fprintf(stderr, "NATIVE_FINALIZE phase=%u enter=1\n",stage);
        std::fflush(stderr);
    }
    SetLastError(error);
}
void endFinalizePhase(unsigned stage, bool returned) noexcept {
    playbackProbe.inStage = false;
    const bool log = nativeFinalizePhaseLog.load();
    if (!storageProfile.active && !log) return;
    const auto error = GetLastError();
    const auto now = std::chrono::steady_clock::now();
    assert(stage < finalizeProfile.size());
    auto& phase = finalizeProfile[stage];
    returned ? ++phase.returned : ++phase.unwound;
    phase.nanoseconds += static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(now-phase.before).count());
    for (std::size_t i=0; i<4; ++i) {
        phase.calls[i] += storageProfile.calls[i]-phase.beforeCalls[i];
        phase.native[i] += storageProfile.nanoseconds[i]-phase.beforeNative[i];
    }
    if (log) {
        std::fprintf(stderr, "NATIVE_FINALIZE phase=%u returned=%u unwound=%u wall_us=%llu\n",
            stage,returned ? 1U : 0U,returned ? 0U : 1U,
            static_cast<unsigned long long>(std::chrono::duration_cast<std::chrono::microseconds>(now-phase.before).count()));
        std::fflush(stderr);
    }
    SetLastError(error);
}
HRESULT playbackReadForTest(IStream* stream, void* data, ULONG size, ULONG* got) {
    const auto hr = stream->Read(data,size,got); // Genuine guarded, encrypted reader.
    auto& probe = playbackProbe;
    if (probe.armed && probe.inStage) {
        ++probe.reads; probe.lastRead = size;
        if (probe.cut == PlaybackCut::shortRead && hr == S_OK && *got == size && size) {
            --*got; ++probe.cutHits;
        }
    }
    return hr;
}
HRESULT playbackSampleForTest(IMFSinkWriter* sink, DWORD index, IMFSample* sample, std::uint64_t frame) {
    auto& probe = playbackProbe;
    if (!probe.armed || !probe.inStage) return sink->WriteSample(index,sample);
    assert(frame == probe.samples);
    LONGLONG time = -1, duration = 0;
    assert(sample->GetSampleTime(&time) == S_OK && time == static_cast<LONGLONG>(frame*100000));
    assert(sample->GetSampleDuration(&duration) == S_OK && duration == 100000);
    Microsoft::WRL::ComPtr<IMFMediaBuffer> buffer;
    assert(sample->GetBufferByIndex(0,&buffer) == S_OK);
    BYTE* pcm = nullptr; DWORD maximum = 0, length = 0;
    assert(buffer->Lock(&pcm,&maximum,&length) == S_OK && length == 960 && maximum >= length);
    for (std::size_t at=0; at<480; ++at) {
        const auto expected = static_cast<std::uint16_t>(static_cast<std::int16_t>(generatedPlaybackValue(frame,at)*32767.0F));
        assert(pcm[2*at] == static_cast<BYTE>(expected) && pcm[2*at+1] == static_cast<BYTE>(expected >> 8));
    }
    assert(buffer->Unlock() == S_OK);
    const auto hr = sink->WriteSample(index,sample);
    ++probe.samples;
    if (SUCCEEDED(hr) && probe.cut == PlaybackCut::cancel) {
        probe.cancellation->store(true); ++probe.cutHits;
    }
    if (SUCCEEDED(hr) && probe.cut == PlaybackCut::output) { ++probe.cutHits; return E_ACCESSDENIED; }
    return hr;
}
}
#define FlushFileBuffers integrationFlush
#define GetProcAddress integrationProcedure
#define ReadFile integrationRead
#define WriteFile integrationWrite
#define CreateFileW integrationCreateFile
#define GetFinalPathNameByHandleW profileFinalPath
#define GetFileInformationByHandleEx profileFileInfo
#define GetSecurityInfo profileSecurity
#define FindFirstStreamW profileFirstStream
#include "../../RecApp/Storage/ProtectedCustodyFiles.cpp"
#undef FindFirstStreamW
#undef GetSecurityInfo
#undef GetFileInformationByHandleEx
#undef GetFinalPathNameByHandleW
#undef CreateFileW
#undef ReadFile
#undef WriteFile
#undef FlushFileBuffers
#undef GetProcAddress

namespace {
thread_local unsigned shortDiscardCut = 0, shortDiscardCutHits = 0;
std::atomic<bool> nativeShortCut{false};
std::atomic<unsigned> nativeShortEffects{0};
std::atomic<unsigned> nativeShortAttempts{0};
thread_local std::atomic<bool>* shortDiscardCancellation = nullptr;
}
namespace graf::windows {
// Executable-only observations immediately before the actual service call or after its OS effect.
// The production owner/validation stays real; no production fault switch.
struct ShortDiscardPurgeProbe {
    DesktopLocalPurgeService service;
    explicit ShortDiscardPurgeProbe(std::filesystem::path root) : service(std::move(root)) {}
    bool isSafePackageDirectory(const std::filesystem::path& path, bool allowMissing = false) const {
        return service.isSafePackageDirectory(path, allowMissing);
    }
    static bool recycle(const std::filesystem::path& path, std::uintptr_t owner, std::uintptr_t expected) {
        if (startOwnerCrashArmed.load(std::memory_order_acquire) && startOwnerCrash->cut==StartOwnerCrashCut::shortBeforeRecycle) {
            assert(path==startOwnerCrash->package && !owner && expected &&
                !nativeShortAttempts.load() && !nativeShortEffects.load());
            startOwnerCrash->preOsDirectory=expected;
            assert(startOwnerCrashArmed.exchange(false));
            terminateStartOwnerCrash(); // Owner intent/preflight complete; actual purge service/OS has not been called.
        }
        ++nativeShortAttempts;
        if (shortDiscardCut == 7) { ++shortDiscardCutHits; return false; } // Refusal, deliberately no OS effect.
        const auto removed = DesktopLocalPurgeService::recycle(path, owner, expected);
        if (startOwnerCrashArmed.load(std::memory_order_acquire) && startOwnerCrash->cut==StartOwnerCrashCut::shortAfterRecycle) {
            assert(path==startOwnerCrash->package && removed && !std::filesystem::exists(path));
            assert(nativeShortAttempts.load()==1);
            ++nativeShortEffects;
            assert(startOwnerCrashArmed.exchange(false));
            terminateStartOwnerCrash(); // Actual confined Shell effect/absence, before returning to the owner.
        }
        if (nativeShortCut.exchange(false)) {
            assert(removed && !std::filesystem::exists(path));
            ++nativeShortEffects;
            return false;
        }
        if (!shortDiscardCut) return removed;
        assert(removed && !std::filesystem::exists(path));
        ++shortDiscardCutHits;
        switch (shortDiscardCut) {
        case 3: return false; // Ambiguous Shell result despite a real effect.
        case 4: assert(shortDiscardCancellation); shortDiscardCancellation->store(true); break;
        case 5: throw std::bad_alloc();
        case 6: denyDeletionReadback.store(true); break;
        case 8: return false; // Actual recycle; the test then creates a distinct directory at the old path.
        case 11: denyShortBootstrap.store(true); break;
        default: assert(false);
        }
        return removed;
    }
};
}
#define DesktopLocalPurgeService ShortDiscardPurgeProbe
#include "../../RecApp/Storage/ProtectedCustodyMetadata.cpp"
#undef DesktopLocalPurgeService

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
    static bool recoveryIntentPending(const NativeCapture& capture) { return capture.pendingRecovery_.has_value(); }
    static auto activeUpload(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return capture.storageStartup_->upload; // Value/atomic observations, no native lease grant.
    }
    static std::uint64_t commandCount(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return capture.storageStartup_->nextTicket;
    }
    static void pollLifecycle(NativeCapture& capture) { capture.pollRecordingLifecycle(); }
    static bool lifecycleActive(const NativeCapture& capture) {
        return capture.lifecycleFlight_ || capture.lifecycleThread_.joinable();
    }
    static std::string lifecycleCursor(const NativeCapture& capture) {
        return std::string(capture.lifecycleCursor_.begin(), capture.lifecycleCursor_.end());
    }
    static bool lifecycleNativeExit(NativeCapture& capture) {
        return capture.lifecycleThread_.joinable() && WaitForSingleObject(capture.lifecycleThread_.native_handle(), 0) == WAIT_OBJECT_0;
    }
    static void takeFinishedLifecycleAnswer(NativeCapture& capture) {
        assert(lifecycleNativeExit(capture));
        assert(capture.lifecycleFlight_ && !capture.lifecycleFlight_->answer && !capture.lifecycleFlight_->waiting.id);
        capture.lifecycleThread_.join();
        auto answer = capture.lifecycleFuture_.get(); capture.lifecycleFuture_ = {};
        capture.lifecycleFlight_->answer = std::move(answer);
    }
    static bool lifecycleAnswerRetained(const NativeCapture& capture) {
        return capture.lifecycleFlight_ && capture.lifecycleFlight_->answer && !capture.lifecycleFlight_->waiting.id;
    }
    struct LifecycleQuotaObservation {
        std::uint64_t waiting = 0, generation = 0;
        std::size_t used = 0, operations = 0;
        unsigned posts = 0;
        bool answer = false, upload = false;
        bool resultReady = false, resultAdopted = false;
    };
    static LifecycleQuotaObservation lifecycleQuotaObservation(
        const NativeCapture& capture, unsigned posts) {
        LifecycleQuotaObservation observed{};
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        if (capture.lifecycleFlight_) {
            observed.answer = static_cast<bool>(capture.lifecycleFlight_->answer);
            observed.waiting = capture.lifecycleFlight_->waiting.id;
        }
        observed.posts = posts;
        observed.operations = capture.protectedQueueValue_->deletionOperations().size();
        observed.generation = capture.storageStartup_->generation;
        observed.upload = static_cast<bool>(capture.storageStartup_->upload);
        observed.resultReady = capture.storageStartup_->resultReady;
        observed.resultAdopted = capture.storageStartup_->resultAdopted;
        observed.used = CustodyOwnedMemory::usedBytes();
        return observed;
    }
    static bool lifecycleWaiting(const NativeCapture& capture) {
        return capture.lifecycleFlight_ && capture.lifecycleFlight_->waiting.id;
    }
    static bool lifecycleResultReady(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return capture.storageStartup_->resultReady && capture.storageStartup_->ticket.kind == NativeCapture::QueueMutationKind::lifecycleResult;
    }
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
    static bool deletionPurgeWaiting(const NativeCapture& capture) {
        return capture.deletionFlight_ && capture.deletionFlight_->phase == NativeCapture::DeletionFlight::Phase::purge;
    }
    static bool deletionNetworkExited(NativeCapture& capture) {
        return capture.deletionThread_.joinable() &&
            WaitForSingleObject(capture.deletionThread_.native_handle(), 0) == WAIT_OBJECT_0;
    }
    static bool commandReconciliationPending(const NativeCapture& capture) {
        std::lock_guard<std::mutex> lock(capture.storageStartup_->mutex);
        return capture.storageStartup_->commandReconciliation && capture.storageStartup_->reconciliationPending;
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
        if (capture.recordingWork_) {
            std::lock_guard<std::mutex> recordingLock(capture.recordingWork_->mutex);
            const auto& recording = *capture.recordingWork_;
            std::fprintf(stderr, "PREPARATION retained_terminal=%u saved=%u reason=%u epoch=%llu\n",
                recording.terminal, recording.result.savedLocal, static_cast<unsigned>(recording.result.reason),
                static_cast<unsigned long long>(recording.epoch));
        }
        std::fflush(stderr);
    }
    static void diagnoseFinalization(const NativeCapture& capture) {
        const auto work = capture.storageStartup_;
        const auto recording = capture.recordingWork_;
        bool storageObserved = false, recordingObserved = false;
        bool commandReady = false, inFlight = false, resultReady = false, queueFailed = false;
        bool prepared = false, started = false, finalizing = false, terminal = false;
        unsigned command = 0, error = 0;
        if (work) {
            std::unique_lock<std::mutex> lock(work->mutex, std::try_to_lock);
            if (lock.owns_lock()) {
                storageObserved = true;
                command = static_cast<unsigned>(work->command);
                error = static_cast<unsigned>(work->error);
                commandReady = work->commandReady; inFlight = work->inFlight;
                resultReady = work->resultReady; queueFailed = work->queueFailed;
            }
        }
        if (recording) {
            std::unique_lock<std::mutex> lock(recording->mutex, std::try_to_lock);
            if (lock.owns_lock()) {
                recordingObserved = true;
                prepared = recording->prepared; started = recording->started;
                finalizing = recording->finalizing; terminal = recording->terminal;
            }
        }
        // Missing/busy observations are not false states. Release both product
        // locks before stderr IO; this failure-only snapshot never advances work.
        std::fprintf(stderr, "FINALIZE_WAIT storage_observed=%u command=%u command_ready=%u in_flight=%u result=%u failed=%u error=%u recording_observed=%u prepared=%u started=%u finalizing=%u terminal=%u\n",
            storageObserved, command, commandReady, inFlight, resultReady, queueFailed, error,
            recordingObserved, prepared, started, finalizing, terminal);
    }
    // Enter the same private continuation as Record. Hardware prerequisites
    // may be generated; storage authority must come from the actual birth ACK.
    static bool requestRecording(NativeCapture& capture) { return capture.requestProtectedRecording(); }
    static void pollAccount(NativeCapture& capture) { capture.pollAccount(); }
    static void freezeRecordingAccount(NativeCapture& capture) {
        capture.recordingAccount_ = capture.currentAccount_;
        capture.recordingOrigin_ = DesktopHttpConfig{}.baseOrigin;
    }
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
    static auto recordingWork(const NativeCapture& capture) { return capture.recordingWork_; }
    static bool recordingTerminal(const NativeCapture& capture) {
        if (!capture.recordingWork_) return false;
        std::lock_guard<std::mutex> lock(capture.recordingWork_->mutex);
        return capture.recordingWork_->terminal;
    }
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
    static TransitionResult beginPending(NativeCapture& capture, const ReadinessInputs& hardware,
        WindowsCaptureSessionController::StartGuard guard = {}) {
        return capture.beginProtectedRecording(hardware, std::move(guard));
    }
};
struct CaptureSessionTestPeer {
    static bool stopBeforeEosHeld(WindowsCaptureSessionController& controller, DWORD heldThread) {
        std::lock_guard<std::mutex> lock(controller.dispatchMutex_);
        unsigned ends=0, mask=0;
        for (const auto& item:controller.pendingBatches_) {
            const auto* end=std::get_if<WindowsCaptureSessionController::SourceEndOfStream>(&item);
            if (end) { ++ends; mask|=end->source==AudioSource::systemRender ? 1U : 2U; }
        }
        return heldThread && GetThreadId(controller.dispatchThread_.native_handle())==heldThread &&
            controller.session_.state()==SessionState::stopping && controller.stopReason_==RecordingStopReason::interruption &&
            !controller.acceptingBatches_.load() &&
            controller.dispatchStopRequested_ && controller.sourceEndsEnqueued_ && controller.dispatchBusy_.load() &&
            !controller.dispatchFinished_.load() && !controller.sourceEndsProcessed_.load() && ends==2 && mask==3;
    }
    static void problemIndicator(WindowsCaptureSessionController& controller, bool blocked) {
        controller.indicator_.publish(blocked ? SessionState::stopping : controller.session().state(),
            blocked ? ReasonCode::finalizationFailed : ReasonCode::none);
    }
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
    static WasapiCaptureWorker& microphoneWorker(WindowsCaptureSessionController& controller) {
        return *controller.microphoneWorker_;
    }
    static void resumeGenerated(WasapiCaptureWorker& worker, std::uint64_t boundaryFrame) {
        worker.servicePrivacyResume([&] {
            return WasapiCaptureWorker::ResumeClockSample{0, boundaryFrame ? (boundaryFrame - 1) * 8 : 0,
                384'000, 48'000, 997, 1000, 1000, 10'000'000,
                std::chrono::system_clock::now(), std::chrono::steady_clock::now()};
        });
    }
    static bool generatedPacket(WasapiCaptureWorker& worker, ClockMapper& mapper, AudioNormalizer& normalizer,
        std::uint64_t frame, const float* samples, std::uint64_t clockFrame) {
        return worker.consumePacket(mapper, normalizer,
            {frame * 100'000, frame * 480, 48'000, 0, 480, clockFrame * 8, 384'000, 0},
            samples, 1, true, [](std::uint32_t count) {
                assert(count == 480); return CaptureReleaseResult{true, 0};
            }, worker.capturePrivacyEpoch());
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
        // Cleanup must use the same long-path namespace as the generated native files.
        const auto path=parent.native().substr(0,4)==L"\\\\?\\" ? parent : std::filesystem::path(L"\\\\?\\"+parent.native());
        std::error_code error; std::filesystem::remove_all(path, error); assert(!error);
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
void logQueueAdmission(const NativeCapture& capture, const char* scenario, unsigned mode) {
    const auto work = NativeCaptureStorageTestPeer::storageWork(capture); assert(work);
    std::lock_guard<std::mutex> lock(work->mutex);
    std::fprintf(stderr, "QUEUE_ADMISSION case=%s mode=%u ready=%u adopted=%u startup=%u generation=%llu error=%u failed=%u reconcile=%u command_reconcile=%u short=%u command=%u in_flight=%u result=%u result_adopted=%u stop=%u terminal=%u cancelled=%u\n",
        scenario, mode, work->ready, work->adopted, static_cast<bool>(work->startupValue),
        static_cast<unsigned long long>(work->generation), static_cast<unsigned>(work->error), work->queueFailed,
        work->reconciliationPending, work->commandReconciliation, work->shortDiscardPending, work->commandReady,
        work->inFlight, work->resultReady, work->resultAdopted, work->stop, work->terminal, work->cancellation->load());
}
using Snapshot = std::map<std::wstring, std::string>;
Snapshot snapshot(const std::filesystem::path& root) {
    Snapshot result;
    for (const auto& entry : std::filesystem::recursive_directory_iterator(root)) {
        if (!entry.is_regular_file()) continue;
        auto path=entry.path();
        // Generated local roots can exceed MAX_PATH after an interrupted index publication.
        if (path.native().size()>=MAX_PATH && path.native().substr(0,4)!=L"\\\\?\\") path=L"\\\\?\\"+path.native();
        const auto hash = sha256File(path); assert(hash.size() == 64);
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
            if (committed) assert(waitFor([&] {
                NativeCaptureStorageTestPeer::pollStorage(capture);
                return capture.localQueueComplete();
            }));
            assert(capture.readiness().storageWritable == committed && capture.localQueueComplete() == committed);
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
        if (unowned) {
            assert(!capture.requestProtectedManualSend(before, session, capture.authGeneration(), false));
            assert(!capture.requestProtectedManualSend(before, session, capture.authGeneration(), true)); // Ordinary/legacy pending is not signed-out Start.
            capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
            assert(networkCalls == 0);
            std::fputs("PROTECTED_MANUAL_SEND legacy_unowned_refused=1 network=0\n", stderr);
            continue;
        }
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
            assert(calls == (cut == IoCut::none ? 6U : 2U));
            if (committed) assert(waitFor([&] { return capture.localQueueComplete(); }));
            assert(capture.localQueueComplete() == committed && capture.readiness().storageWritable == committed);
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
std::string lifecycleOrigin(unsigned n) {
    char name[40]; std::snprintf(name, sizeof(name), "generated-life-%03u", n); return name;
}
std::string lifecycleLocal(unsigned n) {
    char name[40]; std::snprintf(name, sizeof(name), "generated-local-%03u", n); return name;
}
std::uint64_t seedLifecycleQueue(const std::filesystem::path& root, unsigned count, bool audio = false, bool needsAuth = false) {
    return std::async(std::launch::async, [root, count, audio, needsAuth] {
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        auto opened = ProtectedCustodyStoreOwner::open(root, cancel); assert(opened.ok());
        auto owner = std::move(*opened.value);
        if (audio) {
            auto writer = V5LocalRecordingWriter::open(owner, lifecycleOrigin(0), cancel); assert(writer.ok());
            CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
            for (unsigned n = 0; n != 500; ++n) { frame.ptsFrames = n * 480; assert((*writer.value)->append(frame)); }
            assert((*writer.value)->finalize().normalPackage()); writer.value.reset();
        }
        std::string json;
        DesktopUploadQueueService queue(root / L"unused.json", root,
            [&](const auto&, const auto&, std::string_view bytes) { json.assign(bytes); return true; });
        queue.setClock([] { return 1000; });
        for (unsigned n = 0; n != count; ++n) {
            UploadCustodyItem row{lifecycleLocal(n), lifecycleOrigin(n), lifecycleOrigin(n), root / lifecycleOrigin(n),
                UploadQueueStatus::uploaded, {11,22,33}, 3, "",
                "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"};
            if (needsAuth && n == 2) { row.status = UploadQueueStatus::needsAuth; row.safeReason = "auth_required"; }
            assert(queue.enqueue(std::move(row)));
        }
        assert(queue.deletionOperations().empty()); // No locally requested deletion to accept.
        CustodyBytes bytes(json.begin(), json.end());
        const auto saved = commitProtectedCustodyMetadata(owner, owner->queueContext(), owner->queueGeneration(), bytes, cancel);
        assert(saved.state == CustodyCommitState::committed);
        return saved.targetGeneration;
    }).get(); // Every seed owner/writer/lease is released before Native startup.
}
std::string lifecycleAnswer(const CustodyString& body, unsigned mode = 0) {
    const auto fields = DesktopApiClient::jsonObjectFields(body); assert(fields);
    const auto origins = DesktopApiClient::jsonArrayValues(fields->at("origins")); assert(origins && !origins->empty() && origins->size() <= 100);
    std::string answer = "[";
    for (std::size_t n = 0; n != origins->size(); ++n) {
        if (mode == 1 && n) break; // Incomplete batch; never a partial acceptance.
        if (n) answer += ',';
        const auto id = mode == 2 ? origins->front() : (*origins)[n];
        answer += "{\"target_type\":\"own_origin\",\"target_id\":"; answer += id;
        if (id == "\"generated-life-000\"") {
            answer += R"(,"state":"canceled_before_creation","receipt":{"receipt_type":"origin_cancellation","request_id":"77777777-7777-4777-8777-777777777777","phase":"accepted","local_recording_id":)";
            answer += mode == 3 ? "\"foreign-origin\"" : std::string(id); answer += "}}";
        } else answer += ",\"state\":\"allowed\"}";
    }
    answer += ']'; return answer;
}

// The server answers lifecycle while a genuine upload owns its package proof.
// Its fake sync GET remains held after cancellation so an atomic flag cannot
// stand in for executor completion, native release or queue adoption.
// Modes are concrete answers at the same existing HTTP boundary: unavailable,
// accepted external receipt, malformed JSON, foreign target, partial batch,
// late domain conflict, positive-only answer, stale account-A answer, and an
// actual cancelled-upload readback failure requiring physical reconciliation.
void protectedLifecycleUploadDrain(unsigned mode = 0) {
    const auto baseline = CustodyOwnedMemory::usedBytes();
    testing::GeneratedRecordingRoot paths;
    constexpr auto playing = "generated-drain-playing";
    constexpr auto uploading = "generated-drain-uploading";
    constexpr auto switched = "generated-drain-workspace-b";
    const bool restrictive = mode < 2 || mode == 8;
    const std::string expectedAccess = mode == 0 || mode == 8 ? "unknown" : "owner";
    const std::vector<std::string> sessions = mode == 7 ? std::vector<std::string>{playing, uploading, switched} :
        std::vector<std::string>{playing, uploading};
    std::async(std::launch::async, [&] {
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        auto opened = ProtectedCustodyStoreOwner::open(paths.root, cancel); assert(opened.ok());
        auto owner = std::move(*opened.value);
        for (const auto& session : sessions) {
            auto writer = V5LocalRecordingWriter::open(owner, session, cancel); assert(writer.ok());
            CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
            for (unsigned n = 0; n != 500; ++n) { frame.ptsFrames = n * 480; assert((*writer.value)->append(frame)); }
            assert((*writer.value)->finalize().normalPackage()); writer.value.reset();
        }
        auto read = owner->readQueueValue(cancel); assert(read.ok());
        auto value = std::allocate_shared<ProtectedUploadQueueValue>(CustodyAllocator<ProtectedUploadQueueValue>{}, **read.value);
        for (const auto& session : sessions) {
            ProtectedUploadQueueValue::Item row;
            row.localRecordingId = row.directoryId = row.sessionId = session;
            const auto path = (paths.root / session).u8string(); row.packageDirectory.assign(path.begin(), path.end());
            row.ownerUserId = "11111111-1111-4111-8111-111111111111";
            row.ownerWorkspaceId = session == switched ? "55555555-5555-4555-8555-555555555555" :
                "22222222-2222-4222-8222-222222222222";
            row.status = std::string_view(session) == playing ? UploadQueueStatus::uploaded : UploadQueueStatus::pending;
            assert(value->enqueue(std::move(row), 1000, cancel.get()));
        }
        // New enqueue cannot manufacture server truth. Apply a generated typed
        // sync result, then the existing manual-send domain transition for work.
        for (std::size_t index = 0; index != value->items().size(); ++index) {
            const auto expected = value->items()[index];
            ProtectedDesktopTransportResult synced;
            synced.status = std::string_view(expected.localRecordingId) == playing ?
                DesktopTransportStatus::uploaded : DesktopTransportStatus::retryableFailure;
            synced.serverTruth.emplace(); synced.serverTruth->localRecordingId = expected.localRecordingId;
            if (std::string_view(expected.localRecordingId) == uploading)
                synced.serverTruth->meetingId = "66666666-6666-4666-8666-666666666666";
            if (std::string_view(expected.localRecordingId) == switched)
                synced.serverTruth->meetingId = "88888888-8888-4888-8888-888888888888";
            synced.serverTruth->accessState = mode == 6 && std::string_view(expected.localRecordingId) == playing ? "unknown" : "owner";
            assert(value->applyUploadResult(expected, synced, 1500, cancel.get()));
        }
        for (std::size_t index = 0; index != value->items().size(); ++index) {
            const auto expected = value->items()[index];
            if (std::string_view(expected.localRecordingId) != playing)
                assert(value->prepareManualSend(index, expected.ownerUserId, expected.ownerWorkspaceId, false, 2000, cancel.get()));
        }
        auto bytes = value->serialize(cancel); assert(bytes.ok());
        assert(commitProtectedCustodyMetadata(owner, owner->queueContext(), owner->queueGeneration(), *bytes.value, cancel).state == CustodyCommitState::committed);
    }).get();
    const auto originalPlaying = snapshot(paths.root / playing), originalUploading = snapshot(paths.root / uploading);
    const auto originalSwitched = mode == 7 ? snapshot(paths.root / switched) : originalPlaying;
    std::atomic<bool> uploadEntered{false}, releaseUpload{false}, lifecycleEntered{false}, releaseLifecycle{false};
    std::atomic<unsigned> uploadCalls{0}, lifecycleCalls{0};
    std::atomic<bool> switchAccount{false}, switchedUploadEntered{false}, releaseSwitchedUpload{false};
    const DesktopHttpTransport::UploadSend account = [&](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(request.method == "GET");
        if (request.path == "/desktop/settings/spaces") return {200, switchAccount.load() ?
            R"({"spaces":[{"id":"55555555-5555-4555-8555-555555555555","active":true}]})" :
            R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        assert(request.path == "/api/v1/auth/me");
        return {200, switchAccount.load() ?
            R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"55555555-5555-4555-8555-555555555555","active_session_id":"33333333-3333-4333-8333-333333333333"})" :
            R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    };
    const DesktopHttpTransport::ProtectedUploadSend wire = [&](const auto& config, const auto& request) {
        DesktopHttpTransport::ProtectedUploadResponse response; response.status = 200;
        if (request.path == DesktopApiClient::notificationContextPath) {
            assert(request.method == "GET");
            response.body = switchAccount.load() ?
                R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"55555555-5555-4555-8555-555555555555","recording_deletion_protocol_version":1})" :
                R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","recording_deletion_protocol_version":1})";
        } else if (request.path == DesktopApiClient::lifecyclePath) {
            assert(request.method == "POST" && config.scopedAccount); ++lifecycleCalls;
            if (mode == 8) {
                const auto fields = DesktopApiClient::jsonObjectFields(request.body); assert(fields);
                const auto origins = DesktopApiClient::jsonArrayValues(fields->at("origins")); assert(origins && origins->size() == 2);
                assert(std::count(origins->begin(), origins->end(), "\"generated-drain-playing\"") == 1 &&
                    std::count(origins->begin(), origins->end(), "\"generated-drain-uploading\"") == 1);
            }
            lifecycleEntered.store(true); while (!releaseLifecycle.load()) Sleep(1);
            const std::string allowed = R"({"target_type":"own_origin","target_id":"generated-drain-playing","state":"allowed"})";
            const std::string unavailable = R"({"target_type":"own_origin","target_id":"generated-drain-uploading","state":"unavailable","meeting_id":"66666666-6666-4666-8666-666666666666"})";
            std::string body = "[" + allowed + "," + unavailable + "]";
            if (mode == 1) body = R"([{"target_type":"own_origin","target_id":"generated-drain-playing","state":"canceled_before_creation","receipt":{"receipt_type":"origin_cancellation","request_id":"77777777-7777-4777-8777-777777777777","phase":"accepted","local_recording_id":"generated-drain-playing"}},{"target_type":"own_origin","target_id":"generated-drain-uploading","state":"allowed"}])";
            if (mode == 2) body.pop_back();
            if (mode == 3) body.replace(body.find("generated-drain-playing"), std::strlen("generated-drain-playing"), "foreign-drain-origin");
            if (mode == 4) body = "[" + unavailable + "]";
            // Strict wire decode succeeds. The domain copy first changes upload
            // access, then refuses the other row's foreign meeting binding.
            if (mode == 5) body = "[" + unavailable + R"(,{"target_type":"own_origin","target_id":"generated-drain-playing","state":"allowed","meeting_id":"99999999-9999-4999-8999-999999999999"}])";
            if (mode == 6) body = "[" + allowed + R"(,{"target_type":"own_origin","target_id":"generated-drain-uploading","state":"allowed"}])";
            response.body.assign(body.begin(), body.end());
        } else {
            assert(request.method == "GET" && request.path.find("/sync-state?") != CustodyString::npos);
            ++uploadCalls;
            if (config.workspaceId == "55555555-5555-4555-8555-555555555555") {
                switchedUploadEntered.store(true); while (!releaseSwitchedUpload.load()) Sleep(1);
            } else { uploadEntered.store(true); while (!releaseUpload.load()) Sleep(1); }
            response.status = 503; response.body = "{}"; // A cancelled result still reaches the real ACK exchange.
        }
        return response;
    };
    bool cancelBeforeMutation = false, drainBeforeSubmit = false, noUploadResultMutation = false, adopted = false;
    std::uint64_t finalGeneration = 0;
    {
        NativeCapture capture(paths.root, {std::make_shared<GeneratedAec>(), false}, account, wire);
        startAndAdopt(capture, 2); capture.startRecordingLifecycle();
        capture.setAuthSessionToken("generated-drain-session", true);
        const bool bothHeld = waitFor([&] { capture.pollUploads(); return uploadEntered.load() && lifecycleEntered.load(); });
        // Always release either fake request if a genuine prerequisite failed.
        if (!bothHeld) { releaseUpload.store(true); releaseLifecycle.store(true); capture.shutdown();
            assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); })); }
        assert(bothHeld && "drain_fixture_requires_real_upload_and_lifecycle_http");
        auto flight = NativeCaptureStorageTestPeer::activeUpload(capture); assert(flight && capture.uploadsBusy());
        const auto before = NativeCaptureStorageTestPeer::projection(capture);
        const auto generation = NativeCaptureStorageTestPeer::generation(capture);
        const auto cursor = NativeCaptureStorageTestPeer::lifecycleCursor(capture);
        const auto commands = NativeCaptureStorageTestPeer::commandCount(capture);
        assert(before->items().back().status == UploadQueueStatus::retry && before->items().back().accessState == "owner");
        if (mode == 7) assert(before->items()[1].status == UploadQueueStatus::retry && before->items()[1].accessState == "owner");
        if (mode == 6) assert(!capture.openLocalPlayback(playing, 91, true));
        else {
            assert(capture.openLocalPlayback(playing, 91, true));
            assert(waitFor([&] { return capture.localPlaybackObservation().media.ready; }));
            assert(capture.authorizeLocalPlayback(91)); assert(capture.pauseLocalPlayback(true));
        }
        if (mode == 7) {
            // Fresh account GET cancels/drains A. The held A lifecycle thread
            // keeps B's authenticated context pending, so manual B must refuse.
            switchAccount.store(true); capture.setAuthSessionToken("generated-drain-session", true);
            releaseUpload.store(true);
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture);
                NativeCaptureStorageTestPeer::pollStorage(capture);
                return capture.currentAccount() && capture.currentAccount()->workspaceId == "55555555-5555-4555-8555-555555555555" &&
                    flight->done.load() && flight->leaseReleased.load(); }));
            capture.pollUploads(); // Retire A; the held lifecycle thread prevents a B context command.
            const auto current = NativeCaptureStorageTestPeer::projection(capture);
            assert(!capture.requestProtectedManualSend(current, switched, capture.authGeneration(), false));
            assert(uploadCalls == 1 && lifecycleCalls == 1 && !switchedUploadEntered.load() && !capture.uploadsBusy());
            const auto fresh = NativeCaptureStorageTestPeer::projection(capture);
            const auto freshGeneration = NativeCaptureStorageTestPeer::generation(capture);
            const auto freshCommands = NativeCaptureStorageTestPeer::commandCount(capture);
            const auto freshCursor = NativeCaptureStorageTestPeer::lifecycleCursor(capture);
            releaseLifecycle.store(true);
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::lifecycleNativeExit(capture); }));
            NativeCaptureStorageTestPeer::pollLifecycle(capture); // Discard stale A before publishing any B context.
            assert(NativeCaptureStorageTestPeer::projection(capture) == fresh &&
                NativeCaptureStorageTestPeer::generation(capture) == freshGeneration &&
                NativeCaptureStorageTestPeer::commandCount(capture) == freshCommands &&
                NativeCaptureStorageTestPeer::lifecycleCursor(capture) == freshCursor);
            assert(!NativeCaptureStorageTestPeer::lifecycleActive(capture) &&
                uploadCalls == 1 && lifecycleCalls == 1 && !switchedUploadEntered.load());
            assert(fresh->lastAuthenticatedContext() &&
                fresh->lastAuthenticatedContext()->workspaceId == "22222222-2222-4222-8222-222222222222");
            // Use ordinary lifecycle/storage polling: unrestricted pollUploads
            // could dispatch pending recovery B before the manual API is tested.
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollLifecycle(capture);
                return NativeCaptureStorageTestPeer::lifecycleResultReady(capture); }));
            assert(NativeCaptureStorageTestPeer::projection(capture) == fresh &&
                NativeCaptureStorageTestPeer::generation(capture) == freshGeneration &&
                NativeCaptureStorageTestPeer::commandCount(capture) == freshCommands + 1 &&
                !switchedUploadEntered.load()); // Physical context commit is not adoption.
            assert(!capture.requestProtectedManualSend(fresh, switched, capture.authGeneration(), false));
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture);
                const auto observation = capture.localObservation();
                return observation.complete && observation.value && observation.value->lastAuthenticatedContext() &&
                    observation.value->lastAuthenticatedContext()->workspaceId == "55555555-5555-4555-8555-555555555555"; }));
            assert(NativeCaptureStorageTestPeer::generation(capture) == freshGeneration + 1 && uploadCalls == 1);
            NativeCaptureStorageTestPeer::pollLifecycle(capture); // Complete the adopted context ticket; clear pending B.
            std::optional<NativeCapture::QueueMutationTicket> manual;
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture);
                const auto adopted = NativeCaptureStorageTestPeer::projection(capture);
                manual = capture.requestProtectedManualSend(adopted, switched, capture.authGeneration(), false);
                return manual.has_value(); })); // A transient display-slot refusal may need actual drain.
            assert(manual);
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture); return switchedUploadEntered.load(); }));
            flight = NativeCaptureStorageTestPeer::activeUpload(capture);
            assert(flight && !flight->cancelled->load() && capture.uploadsBusy());
            assert(!flight->cancelled->load() && !flight->done.load() && !flight->leaseReleased.load());
            assert(uploadCalls == 2); // Stale A left no restriction blocking a genuine B upload.
            releaseSwitchedUpload.store(true); capture.shutdown();
            assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        } else if (mode == 6) {
            releaseLifecycle.store(true);
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::lifecycleNativeExit(capture); }));
            NativeCaptureStorageTestPeer::pollLifecycle(capture);
            assert(!flight->cancelled->load() && !capture.openLocalPlayback(playing, 91, true));
            assert(NativeCaptureStorageTestPeer::projection(capture) == before &&
                NativeCaptureStorageTestPeer::commandCount(capture) == commands &&
                NativeCaptureStorageTestPeer::lifecycleCursor(capture) == cursor);
            releaseUpload.store(true); // Normal result, not cancellation, must commit and finish first.
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture);
                return flight->done.load() && flight->leaseReleased.load(); }));
            assert(!flight->cancelled->load() && NativeCaptureStorageTestPeer::generation(capture) == generation + 1);
            assert(NativeCaptureStorageTestPeer::projection(capture)->items().front().accessState == "unknown");
            assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::lifecycleWaiting(capture); }));
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::lifecycleResultReady(capture); }));
            assert(NativeCaptureStorageTestPeer::projection(capture)->items().front().accessState == "unknown" &&
                !capture.openLocalPlayback(playing, 91, true) && NativeCaptureStorageTestPeer::lifecycleCursor(capture) == cursor);
            NativeCaptureStorageTestPeer::pollStorage(capture);
            assert(NativeCaptureStorageTestPeer::generation(capture) == generation + 2 &&
                NativeCaptureStorageTestPeer::projection(capture)->items().front().accessState == "owner");
            assert(NativeCaptureStorageTestPeer::lifecycleCursor(capture) == cursor);
            NativeCaptureStorageTestPeer::pollLifecycle(capture);
            assert(NativeCaptureStorageTestPeer::lifecycleCursor(capture) == uploading);
            assert(waitFor([&] { return capture.openLocalPlayback(playing, 91, true); }));
            capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        } else if (!restrictive) {
            releaseLifecycle.store(true);
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::lifecycleNativeExit(capture); }));
            NativeCaptureStorageTestPeer::pollLifecycle(capture);
            assert(!flight->cancelled->load() && !flight->done.load() && !flight->leaseReleased.load() && capture.uploadsBusy());
            assert(NativeCaptureStorageTestPeer::projection(capture) == before &&
                NativeCaptureStorageTestPeer::generation(capture) == generation &&
                NativeCaptureStorageTestPeer::commandCount(capture) == commands &&
                NativeCaptureStorageTestPeer::lifecycleCursor(capture) == cursor && !NativeCaptureStorageTestPeer::lifecycleWaiting(capture));
            assert(capture.seekLocalPlayback(1)); // A late private prefix cannot revoke a consumer.
            capture.shutdown(); releaseUpload.store(true);
            assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        } else {
            releaseLifecycle.store(true);
            const bool cancelled = waitFor([&] { NativeCaptureStorageTestPeer::pollLifecycle(capture); return flight->cancelled->load(); });
            cancelBeforeMutation = cancelled && !flight->done.load() && !flight->leaseReleased.load() && capture.uploadsBusy() &&
                NativeCaptureStorageTestPeer::generation(capture) == generation && NativeCaptureStorageTestPeer::projection(capture) == before &&
                NativeCaptureStorageTestPeer::lifecycleCursor(capture) == cursor && !NativeCaptureStorageTestPeer::lifecycleWaiting(capture) &&
                !capture.seekLocalPlayback(1);
            const auto readFailuresBefore = shortReadFailures.load();
            if (mode == 8 && cancelBeforeMutation) denyDeletionReadback.store(true);
            releaseUpload.store(true);
            if (cancelBeforeMutation) {
                if (mode == 8) {
                    const bool failedReadback = waitFor([&] { return NativeCaptureStorageTestPeer::reconciliationPending(capture); });
                    denyDeletionReadback.store(false); // Release the real IO cut before any assertion/teardown.
                    assert(failedReadback && shortReadFailures.load() > readFailuresBefore &&
                        flight->done.load() && !flight->leaseReleased.load() && capture.uploadsBusy());
                    assert(NativeCaptureStorageTestPeer::generation(capture) == generation &&
                        NativeCaptureStorageTestPeer::commandCount(capture) == commands && uploadCalls == 1 &&
                        NativeCaptureStorageTestPeer::lifecycleCursor(capture) == cursor && !capture.openLocalPlayback(playing, 92, true));
                    capture.recover(RecoveryTrigger::networkRecovered);
                    NativeCaptureStorageTestPeer::pollAccount(capture);
                    assert(waitFor([&] { return NativeCaptureStorageTestPeer::accountResultReady(capture); }));
                    NativeCaptureStorageTestPeer::pollAccount(capture);
                    assert(capture.currentAccount()); // Actual fresh GET also leaves its context command pending.
                    capture.setVisibleRecordingItemIDs({playing, uploading}, capture.authGeneration());
                    capture.pollUploads(); // Actual recovery signal must reach physical retry, never a new HTTP flight.
                    const bool retried = waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture);
                        return flight->done.load() && flight->leaseReleased.load(); });
                    if (!retried) { capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); })); }
                    assert(retried && "cancelled_upload_physical_retry_must_pass_restrictive_gate");
                    assert(uploadCalls == 1 && !capture.openLocalPlayback(playing, 92, true));
                } else assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture);
                    return flight->done.load() && flight->leaseReleased.load(); }));
                const auto unchanged = NativeCaptureStorageTestPeer::projection(capture);
                noUploadResultMutation = NativeCaptureStorageTestPeer::generation(capture) == generation &&
                    unchanged->items().back().status == UploadQueueStatus::retry && unchanged->items().back().attempts == 0 &&
                    unchanged->items().back().accessState == "owner" && capture.localQueueComplete() &&
                    NativeCaptureStorageTestPeer::commandCount(capture) == commands; // No uploadResult command/apply/commit.
                assert(capture.uploadsBusy() && !NativeCaptureStorageTestPeer::lifecycleWaiting(capture)); // No retire-by-timeout.
                assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::lifecycleWaiting(capture); }));
                // Actual done+leaseReleased lets the ordinary scheduler retire.
                drainBeforeSubmit = !capture.uploadsBusy() && !NativeCaptureStorageTestPeer::activeUpload(capture) &&
                    NativeCaptureStorageTestPeer::lifecycleWaiting(capture) &&
                    NativeCaptureStorageTestPeer::commandCount(capture) == commands + 1;
                assert(waitFor([&] { return NativeCaptureStorageTestPeer::lifecycleResultReady(capture); }));
                assert(NativeCaptureStorageTestPeer::generation(capture) == generation &&
                    NativeCaptureStorageTestPeer::projection(capture)->items().back().accessState == "owner" &&
                    NativeCaptureStorageTestPeer::lifecycleCursor(capture) == cursor); // Physical commit is not positive adoption.
                NativeCaptureStorageTestPeer::pollStorage(capture);
                const auto result = NativeCaptureStorageTestPeer::projection(capture);
                adopted = NativeCaptureStorageTestPeer::generation(capture) == generation + 1 &&
                    std::string_view(*result->items().back().accessState) == expectedAccess && result->items().back().attempts == 0 &&
                    result->items().back().status == UploadQueueStatus::retry;
                assert(result->deletionOperations().size() == (mode == 1 ? 1U : 0U));
                if (mode == 1) {
                    assert(deletionPhaseIsAccepted(result->deletionOperations().front().phase));
                    assert(result->deletionBlocks(result->items().front()));
                }
                assert(NativeCaptureStorageTestPeer::lifecycleCursor(capture) == cursor);
                NativeCaptureStorageTestPeer::pollLifecycle(capture);
                // Mode8's fresh visible-priority batch does not advance the background cursor.
                if (mode == 8) assert(NativeCaptureStorageTestPeer::lifecycleCursor(capture) == cursor);
                else assert(NativeCaptureStorageTestPeer::lifecycleCursor(capture) == uploading);
                finalGeneration = NativeCaptureStorageTestPeer::generation(capture);
            }
            capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        }
    }
    assert(snapshot(paths.root / playing) == originalPlaying && snapshot(paths.root / uploading) == originalUploading);
    if (mode == 7) assert(snapshot(paths.root / switched) == originalSwitched);
    if (restrictive) {
        assert(cancelBeforeMutation && "lifecycle_restrictive_answer_must_cancel_active_upload_before_queue_change");
        if (mode == 8) assert(noUploadResultMutation && drainBeforeSubmit && adopted && uploadCalls == 1 && lifecycleCalls == 2);
        else assert(noUploadResultMutation && drainBeforeSubmit && adopted && uploadCalls == 1 && lifecycleCalls == 1);
        std::async(std::launch::async, [&] {
            auto cancel = std::make_shared<std::atomic<bool>>(false);
            auto opened = ProtectedCustodyStoreOwner::open(paths.root, cancel); assert(opened.ok());
            auto read = (*opened.value)->readQueueValue(cancel); assert(read.ok());
            if (mode == 1) {
                assert((*opened.value)->queueGeneration() == finalGeneration &&
                    std::string_view(*(*read.value)->items().back().accessState) == expectedAccess);
                assert((*read.value)->items().back().attempts == 0 && (*read.value)->deletionOperations().size() == 1);
            } else {
                assert((*opened.value)->queueGeneration() == finalGeneration && (*read.value)->items().back().accessState == "unknown");
                assert((*read.value)->items().back().attempts == 0 && (*read.value)->deletionOperations().empty());
            }
        }).get();
    }
    assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
}

void protectedLifecycleApplication() {
    for (unsigned mode = 0; mode != 9; ++mode) protectedLifecycleUploadDrain(mode);
    lifecyclePhase.store("hot_211");
    const auto baseline = CustodyOwnedMemory::usedBytes();
    const DesktopHttpTransport::UploadSend account = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(request.method == "GET");
        if (request.path == "/desktop/settings/spaces")
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        assert(request.path == "/api/v1/auth/me");
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    };
    const auto gate = R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","recording_deletion_protocol_version":1})";
    {
        Fixture fixture; const auto generation = seedLifecycleQueue(fixture.root, 211, true);
        const auto original = snapshot(fixture.root / lifecycleOrigin(0)); assert(!original.empty());
        unsigned gets = 0, deletes = 0, purgeAcks = 0;
        std::atomic<bool> exitHeld{false}, exitReleased{false}, exitTimedOut{false};
        std::vector<std::vector<std::string>> pages;
        std::mutex networkMutex;
        const DesktopHttpTransport::ProtectedUploadSend wire = [&](const auto& config, const auto& request) {
            assert(config.scopedAccount && config.scopedAccount->userId == "11111111-1111-4111-8111-111111111111" &&
                config.scopedAccount->workspaceId == "22222222-2222-4222-8222-222222222222");
            DesktopHttpTransport::ProtectedUploadResponse response; response.status = 200;
            std::lock_guard<std::mutex> lock(networkMutex);
            if (request.method == "DELETE") ++deletes;
            if (request.path.find("/ack") != CustodyString::npos) ++purgeAcks;
            if (request.method == "GET") { assert(request.path == DesktopApiClient::notificationContextPath); ++gets; response.body = gate; }
            else {
                assert(request.method == "POST" && request.path == DesktopApiClient::lifecyclePath);
                const auto fields = DesktopApiClient::jsonObjectFields(request.body); assert(fields);
                const auto ids = DesktopApiClient::jsonArrayValues(fields->at("origins")); assert(ids);
                std::vector<std::string> page;
                for (auto id : *ids) page.emplace_back(id.substr(1, id.size()-2));
                assert(page.size() <= 100);
                if (pages.empty()) {
                    struct ExitCut {
                        std::atomic<bool>* held = nullptr; std::atomic<bool>* released = nullptr; std::atomic<bool>* timedOut = nullptr;
                        ~ExitCut() {
                            if (!held) return;
                            held->store(true); const auto deadline = GetTickCount64() + 10000;
                            while (!released->load() && GetTickCount64() < deadline) Sleep(1);
                            if (!released->load()) timedOut->store(true);
                        }
                    };
                    thread_local ExitCut exit;
                    exit.held = &exitHeld; exit.released = &exitReleased; exit.timedOut = &exitTimedOut;
                }
                pages.push_back(std::move(page));
                response.body = lifecycleAnswer(request.body);
            }
            return response;
        };
        {
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, account, wire);
            startAndAdopt(capture, generation);
            capture.setAuthSessionToken("generated-lifecycle-session");
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
            capture.startRecordingLifecycle(); // Same unconditional native shell activation as AppMain.
            capture.setVisibleRecordingItemIDs({lifecycleLocal(0), lifecycleLocal(210)}, capture.authGeneration());
            assert(waitFor([&] { capture.pollUploads(); return exitHeld.load(); }));
            for (unsigned n = 0; n != 3; ++n) capture.pollUploads();
            assert(NativeCaptureStorageTestPeer::lifecycleActive(capture) && !capture.updateWorkDrained());
            assert(NativeCaptureStorageTestPeer::projection(capture)->deletionOperations().empty());
            assert(NativeCaptureStorageTestPeer::lifecycleCursor(capture).empty());
            { std::lock_guard<std::mutex> lock(networkMutex); assert(pages.size() == 1); }
            exitReleased.store(true);
            bool started = false;
            assert(waitFor([&] {
                capture.pollUploads();
                const bool active = NativeCaptureStorageTestPeer::lifecycleActive(capture); started = started || active;
                if (active) capture.setVisibleRecordingItemIDs({lifecycleLocal(0), lifecycleLocal(210)}, capture.authGeneration());
                return started && !active;
            }));
            auto adopted = NativeCaptureStorageTestPeer::projection(capture);
            assert(adopted && adopted->items().size() == 211 && adopted->deletionOperations().size() == 1);
            const auto& accepted = adopted->deletionOperations().front();
            assert(accepted.phase == DeletionOperationPhase::accepted && std::string_view(accepted.targetId) == lifecycleOrigin(0));
            assert(accepted.receiptRequestId == "77777777-7777-4777-8777-777777777777" && accepted.operationId != accepted.receiptRequestId);
            assert(accepted.attemptCount == 0 && accepted.nextAttemptAtMs == 0);
            assert(adopted->deletionBlocks(adopted->items().front()));
            assert(snapshot(fixture.root / lifecycleOrigin(0)) == original);
            assert(NativeCaptureStorageTestPeer::lifecycleCursor(capture) == lifecycleOrigin(100));
            // Clear document priority. Existing periodic/recovery triggers must
            // still advance native history without any WebView or visible IDs.
            capture.setVisibleRecordingItemIDs({}, capture.authGeneration());
            for (unsigned end : {200U, 210U, 100U}) {
                capture.recover(RecoveryTrigger::scheduled); bool cycle = false;
                assert(waitFor([&] { capture.pollUploads(); const auto active = NativeCaptureStorageTestPeer::lifecycleActive(capture);
                    cycle = cycle || active; return cycle && !active; }));
                assert(NativeCaptureStorageTestPeer::lifecycleCursor(capture) == lifecycleOrigin(end));
            }
            capture.shutdown();
            assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        }
        assert(snapshot(fixture.root / lifecycleOrigin(0)) == original && !exitTimedOut.load());
        {
            std::lock_guard<std::mutex> lock(networkMutex);
            assert(!deletes && !purgeAcks && gets == 5 && pages.size() == 5);
            assert((pages[0] == std::vector<std::string>{lifecycleOrigin(0), lifecycleOrigin(210)}));
            assert(pages[1].front() == lifecycleOrigin(1) && pages[1].back() == lifecycleOrigin(100));
            assert(pages[2].front() == lifecycleOrigin(101) && pages[2].back() == lifecycleOrigin(200));
            assert(pages[3].front() == lifecycleOrigin(201) && pages[3].back() == lifecycleOrigin(210));
            assert(pages[4] == pages[1]);
        }
        lifecyclePhase.store("cold_211");
        // FIRST fresh regular owner, after Native and every thread/value/pin
        // have gone. No candidate bytes are injected into its readback.
        std::async(std::launch::async, [&] {
            auto cancel = std::make_shared<std::atomic<bool>>(false);
            auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(opened.ok());
            auto value = (*opened.value)->readQueueValue(cancel); assert(value.ok());
            const auto snapshot = *value.value;
            assert(snapshot->items().size() == 211 && snapshot->deletionOperations().size() == 1);
            const auto& receipt = snapshot->deletionOperations().front();
            assert(receipt.phase == DeletionOperationPhase::accepted && std::string_view(receipt.targetId) == lifecycleOrigin(0) && receipt.attemptCount == 0);
            assert(receipt.actorUserId == "11111111-1111-4111-8111-111111111111" && receipt.workspaceId == "22222222-2222-4222-8222-222222222222");
            assert(std::string_view(receipt.serverOrigin) == DesktopHttpConfig{}.baseOrigin &&
                receipt.receiptRequestId == "77777777-7777-4777-8777-777777777777");
            for (unsigned n = 0; n != 211; ++n) {
                const auto& row = snapshot->items()[n];
                assert(std::string_view(row.localRecordingId) == lifecycleLocal(n) && std::string_view(row.directoryId) == lifecycleOrigin(n));
                assert(row.acceptedBytes == (std::array<std::uint64_t,3>{11,22,33}) && row.attempts == 3);
            }
            const auto before = snapshot->serialize(cancel); assert(before.ok());
            const CustodyVector<CustodyString> origins{CustodyString(lifecycleOrigin(0).c_str())};
            const auto body = CustodyString("{\"origins\":[\"generated-life-000\"]}");
            const auto entries = DesktopApiClient::decodeLifecycleEntries<CustodyString>(lifecycleAnswer(body)); assert(entries);
            for (unsigned edge = 0; edge != 7; ++edge) {
                lifecyclePhase.store("cold_edge"); lifecycleCase.store(edge);
                auto copy = std::allocate_shared<ProtectedUploadQueueValue>(CustodyAllocator<ProtectedUploadQueueValue>{}, *snapshot);
                auto answer = *entries; auto targets = origins;
                if (edge == 1) answer[0].receipt->requestId = "88888888-8888-4888-8888-888888888888";
                if (edge == 2) answer[0].targetId = "foreign-origin";
                if (edge == 3) targets.push_back(targets.front());
                if (edge == 4) answer.clear();
                if (edge >= 5) { answer[0].receipt.reset(); answer[0].state = edge == 5 ? LifecycleState::allowed : LifecycleState::unavailable; }
                bool changed = false;
                const bool valid = copy->applyLifecycleEntries(targets, answer, receipt.actorUserId, receipt.workspaceId,
                    receipt.serverOrigin, receipt.updatedAtMs + 1, changed, cancel.get());
                assert(valid == (edge == 0 || edge >= 5) && changed == (edge == 5));
                const auto after = copy->serialize(cancel); assert(after.ok());
                if (edge == 5) {
                    const auto& row = copy->items().front();
                    assert(row.accessState && *row.accessState == "owner" && row.meetingId.empty());
                    assert(copy->deletionOperations().size() == 1 && copy->deletionBlocks(row));
                    const auto& retained = copy->deletionOperations().front();
                    assert(retained.phase == receipt.phase && retained.receiptRequestId == receipt.receiptRequestId &&
                        retained.targetId == receipt.targetId && retained.attemptCount == receipt.attemptCount);
                    assert(after.value != before.value);
                } else assert(after.value == before.value);
                const auto unchanged = snapshot->serialize(cancel); assert(unchanged.ok() && unchanged.value == before.value);
            }
        }).get();
    }
    assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
    // Refuse complete malformed/stale replies before any durable effect. The
    // existing IO wrappers also prove not-committed vs ambiguous adoption.
    for (unsigned mode = 1; mode != 10; ++mode) {
        lifecyclePhase.store("negative_mode"); lifecycleCase.store(mode);
        Fixture fixture; const auto generation = seedLifecycleQueue(fixture.root, 3, false, mode == 9);
        const auto before = snapshot(fixture.root);
        std::atomic<unsigned> posts{0}; std::atomic<bool> release{false}, held{false};
        const DesktopHttpTransport::ProtectedUploadSend wire = [&](const auto& config, const auto& request) {
            DesktopHttpTransport::ProtectedUploadResponse response; response.status = 200;
            if (request.method == "GET") { assert(request.path == DesktopApiClient::notificationContextPath); response.body = gate;
                if (mode == 4) response.body = R"({"user_id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","workspace_id":"22222222-2222-4222-8222-222222222222","recording_deletion_protocol_version":1})";
            } else {
                assert(request.method == "POST" && request.path == DesktopApiClient::lifecyclePath); ++posts;
                if (mode >= 5) { held.store(true); while (!release.load() && !config.cancellation->load()) Sleep(1); }
                response.body = lifecycleAnswer(request.body, mode <= 3 ? mode : 0);
            }
            return response;
        };
        {
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, account, wire);
            startAndAdopt(capture, generation); capture.setAuthSessionToken("generated-lifecycle-negative");
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
            capture.startRecordingLifecycle(); bool active = false;
            if (mode >= 5) {
                assert(waitFor([&] { capture.pollUploads(); return held.load(); }));
                if (mode == 9) {
                    // Real auth recovery changes the queue while lifecycle HTTP
                    // is held. Its missing generated package cannot reach HTTP.
                    assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::generation(capture) > generation && capture.localQueueComplete(); }));
                    assert(NativeCaptureStorageTestPeer::projection(capture)->deletionOperations().empty());
                }
                if (mode == 5) capture.setAuthSessionToken({}, true);
                release.store(true);
                if (mode >= 6) {
                    assert(waitFor([&] { return NativeCaptureStorageTestPeer::lifecycleNativeExit(capture); }));
                    if (mode == 8) {
                        NativeCaptureStorageTestPeer::takeFinishedLifecycleAnswer(capture);
                        assert(NativeCaptureStorageTestPeer::lifecycleAnswerRetained(capture));
                        CustodyAllocator<char> allocator;
                        const auto count = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
                        auto* pressure = allocator.allocate(count);
                        assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
                        lifecyclePhase.store("quota_held");
                        const auto beforePoll = NativeCaptureStorageTestPeer::lifecycleQuotaObservation(capture, posts.load());
                        NativeCaptureStorageTestPeer::pollLifecycle(capture);
                        const auto afterPoll = NativeCaptureStorageTestPeer::lifecycleQuotaObservation(capture, posts.load());
                        lifecyclePhase.store("quota_polled");
                        const bool retained = NativeCaptureStorageTestPeer::lifecycleAnswerRetained(capture) && posts == 1 &&
                            NativeCaptureStorageTestPeer::projection(capture)->deletionOperations().empty();
                        allocator.deallocate(pressure, count);
                        lifecyclePhase.store("quota_released");
                        const auto report = [](const char* phase,
                            const NativeCaptureStorageTestPeer::LifecycleQuotaObservation& observed) {
                            std::fprintf(stderr,
                                "LIFECYCLE_QUOTA phase=%s answer=%u waiting=%llu posts=%u operations=%zu "
                                "used=%zu generation=%llu upload=%u result_ready=%u result_adopted=%u\n",
                                phase, static_cast<unsigned>(observed.answer),
                                static_cast<unsigned long long>(observed.waiting), observed.posts,
                                observed.operations, observed.used,
                                static_cast<unsigned long long>(observed.generation),
                                static_cast<unsigned>(observed.upload),
                                static_cast<unsigned>(observed.resultReady),
                                static_cast<unsigned>(observed.resultAdopted));
                        };
                        report("before_poll", beforePoll);
                        report("after_poll", afterPoll);
                        std::fflush(stderr);
                        assert(retained);
                    }
                    ioCut.store(mode == 6 ? IoCut::flush : mode == 7 ? IoCut::ambiguousRename : IoCut::none);
                    assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::lifecycleWaiting(capture); }));
                    assert(waitFor([&] { return NativeCaptureStorageTestPeer::lifecycleResultReady(capture); }));
                    if (mode == 9) {
                        const auto ticket = NativeCaptureStorageTestPeer::ticket(capture); assert(ticket && ticket->baseGeneration > generation);
                    }
                    assert(NativeCaptureStorageTestPeer::projection(capture)->deletionOperations().empty());
                    assert(NativeCaptureStorageTestPeer::lifecycleCursor(capture).empty());
                    ioCut.store(IoCut::none);
                    if (mode == 7) denyDeletionReadback.store(true);
                    NativeCaptureStorageTestPeer::pollStorage(capture);
                    if (mode == 7) {
                        assert(NativeCaptureStorageTestPeer::projection(capture)->deletionOperations().empty());
                        denyDeletionReadback.store(false); capture.recover(RecoveryTrigger::scheduled);
                        assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::projection(capture)->deletionOperations().size() == 1; }));
                    }
                }
            }
            assert(waitFor([&] { capture.pollUploads(); active = active || NativeCaptureStorageTestPeer::lifecycleActive(capture);
                return !NativeCaptureStorageTestPeer::lifecycleActive(capture) && (active || mode >= 5 || mode == 4); }));
            if (mode < 7) assert(NativeCaptureStorageTestPeer::projection(capture)->deletionOperations().empty());
            if (mode >= 8) assert(NativeCaptureStorageTestPeer::projection(capture)->deletionOperations().size() == 1);
            capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        }
        ioCut.store(IoCut::none); denyDeletionReadback.store(false);
        if (mode <= 5) assert(snapshot(fixture.root) == before);
        // Explicit recovery after ambiguous readback may coalesce one next
        // background cycle; no autonomous retry loop or destructive call exists.
        assert(mode == 7 ? posts >= 1 && posts <= 2 : posts == (mode == 4 ? 0U : 1U));
        std::async(std::launch::async, [&] {
            auto cancel = std::make_shared<std::atomic<bool>>(false);
            auto owner = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(owner.ok());
            auto read = (*owner.value)->readQueueValue(cancel); assert(read.ok());
            assert((*read.value)->deletionOperations().size() == (mode >= 7 ? 1U : 0U));
        }).get();
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
    }
    std::fprintf(stderr, "PROTECTED_LIFECYCLE generated_origins=211 external_receipt=1 devices=0 real_network=0 delete=0 purge_ack=0\n");
}

void protectedDeletionApplication() {
    protectedLifecycleApplication();
    const DesktopHttpTransport::UploadSend account = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(request.method == "GET");
        if (request.path == "/desktop/settings/spaces")
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        assert(request.path == "/api/v1/auth/me");
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    };
    for (unsigned mode = 0; mode != 18; ++mode) {
    lifecyclePhase.store("deletion_mode"); lifecycleCase.store(mode);
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
            const bool held = waitFor([&] { return NativeCaptureStorageTestPeer::commandReconciliationPending(capture); });
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
                reconciliationHeld = waitFor([&] { return NativeCaptureStorageTestPeer::commandReconciliationPending(capture); }) &&
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
    const bool complete = mode != 6 && mode != 16;
    const bool startOpen = complete && mode != 1 && mode != 2 && mode != 4 && mode != 5 && mode != 17;
    logQueueAdmission(capture, "deletion_application", mode);
    if (complete) assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture); return capture.localQueueComplete(); }));
    assert(capture.localQueueComplete() == complete && capture.readiness().storageWritable == startOpen);
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
                assert(waitFor([&] { return NativeCaptureStorageTestPeer::commandReconciliationPending(capture); }));
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
void protectedShortDiscard() {
    for (unsigned mode = 0; mode != 12; ++mode) {
        std::async(std::launch::async, [mode] {
            testing::GeneratedProtectedRecording recording("generated-short-discard");
            recording.append(100);
            const auto result = recording.writer->finalize(ReasonCode::none,
                mode == 1 ? RecordingStopReason::interruption : RecordingStopReason::userRequested);
            assert(result.ok() && result.semanticVerified && result.durationMs == 1000);
            assert(result.shortRecordingDiscarded == (mode != 1));
            const auto path = recording.paths.root / recording.session;
            recording.writer.reset(); // Real encoder, inspection and package leases retire here.
            if (mode == 2 || mode == 9) {
                const auto queue = recording.store->readQueueValue(recording.cancel); assert(queue.ok());
                auto candidate = **queue.value;
                ProtectedUploadQueueValue::Item row;
                row.localRecordingId = row.directoryId = row.sessionId = recording.session;
                const auto encoded = path.u8string(); row.packageDirectory.assign(encoded.begin(), encoded.end());
                if (mode == 9) {
                    row.localRecordingId = row.directoryId = row.sessionId = "generated-alias";
                    std::transform(row.packageDirectory.begin(), row.packageDirectory.end(), row.packageDirectory.begin(),
                        [](char c) { return c >= 'a' && c <= 'z' ? static_cast<char>(c - 'a' + 'A') : c; });
                }
                row.status = UploadQueueStatus::quarantined; row.safeReason = "capture_interrupted";
                assert(candidate.enqueue(std::move(row), 1000, recording.cancel.get()));
                const auto bytes = candidate.serialize(recording.cancel); assert(bytes.ok());
                assert(commitProtectedCustodyMetadata(recording.store, recording.store->queueContext(),
                    recording.store->queueGeneration(), *bytes.value, recording.cancel).state == CustodyCommitState::committed);
            }
            const auto before = snapshot(recording.paths.root);
            const auto generation = recording.store->queueGeneration();
            const auto attempt = [&](const CustodyContext& context, std::uint64_t stateGeneration,
                std::shared_ptr<const std::atomic<bool>> cancel) {
                return recording.store->discardShortRecording(recording.session, context, stateGeneration, std::move(cancel));
            };
            const auto refused = [&](const auto& answer) {
                assert((!answer.ok() || !*answer.value) && snapshot(recording.paths.root) == before);
            };
            auto wrong = result.packageContext; wrong.objectId[0] ^= 1;
            refused(attempt(wrong, result.packageGeneration, recording.cancel));
            refused(attempt(result.packageContext, result.packageGeneration + 1, recording.cancel));
            refused(attempt(result.packageContext, result.packageGeneration, std::make_shared<std::atomic<bool>>(true)));
            {
                std::array<CustodyNativeJob, 4> jobs;
                for (const auto& job : jobs) assert(job);
                refused(attempt(result.packageContext, result.packageGeneration, recording.cancel));
            }
            {
                CustodyBytes pressure;
                pressure.resize(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
                refused(attempt(result.packageContext, result.packageGeneration, recording.cancel));
            }
            if (mode == 1 || mode == 2 || mode == 9) {
                refused(attempt(result.packageContext, result.packageGeneration, recording.cancel));
                std::fprintf(stderr, "SHORT_DISCARD refused_mode=%u bytes_unchanged=1\n", mode);
                return;
            }
            if (mode == 7 || mode == 8 || mode == 10) {
                const auto parked = recording.paths.parent / "generated-parked";
                if (mode == 8) std::filesystem::copy(path, parked, std::filesystem::copy_options::recursive);
                shortDiscardCut = mode == 8 ? 8 : 7; shortDiscardCutHits = 0;
                const auto declined = attempt(result.packageContext, result.packageGeneration, recording.cancel);
                shortDiscardCut = 0;
                assert(!declined.ok() && declined.error == CustodyFileError::recoveryRequired && shortDiscardCutHits == 1);
                if (mode != 8) assert(snapshot(recording.paths.root) == before);
                if (mode == 8) {
                    assert(!std::filesystem::exists(path));
                    assert(std::filesystem::create_directory(path)); // Different actual FileId, never another package's authority.
                    std::filesystem::copy(parked, path, std::filesystem::copy_options::recursive);
                } else if (mode == 10) {
                    const auto member = std::find_if(std::filesystem::recursive_directory_iterator(path),
                        std::filesystem::recursive_directory_iterator{}, [](const auto& item) { return item.is_regular_file(); });
                    assert(member != std::filesystem::recursive_directory_iterator{});
                    assert(std::filesystem::remove(member->path())); // Generated partial package, no user data.
                }
                const auto disk = snapshot(recording.paths.root);
                const auto reconciled = attempt(result.packageContext, result.packageGeneration, recording.cancel);
                assert(shortDiscardCutHits == 1 && snapshot(recording.paths.root) == disk);
                if (mode == 7) {
                    assert(reconciled.ok() && !*reconciled.value);
                    const auto retried = attempt(result.packageContext, result.packageGeneration, recording.cancel);
                    assert(retried.ok() && *retried.value && !std::filesystem::exists(path));
                } else {
                    assert(!reconciled.ok() && std::filesystem::exists(path));
                    const auto birth = recording.store->createPackage("must-not-mutate-pending", recording.cancel);
                    assert(!birth.ok() && birth.error == CustodyFileError::recoveryRequired);
                }
                std::fprintf(stderr, "SHORT_DISCARD reconciliation_mode=%u readonly=1 substituted_or_partial_refused=%u audio=0\n",
                    mode, mode == 7 ? 0U : 1U);
                return;
            }
            {
                CustodyFileResult<bool> busy;
                winrt::handle held(CreateFileW(path.c_str(), FILE_READ_ATTRIBUTES | FILE_LIST_DIRECTORY,
                    FILE_SHARE_READ, nullptr, OPEN_EXISTING,
                    FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
                assert(held);
                busy = attempt(result.packageContext, result.packageGeneration, recording.cancel);
                refused(busy);
                held.close();
                if (busy.error == CustodyFileError::recoveryRequired) {
                    const auto reconciled = attempt(result.packageContext, result.packageGeneration, recording.cancel);
                    assert(reconciled.ok() && !*reconciled.value && snapshot(recording.paths.root) == before);
                }
            }
            shortDiscardCut = mode;
            shortDiscardCutHits = 0; // MSVC async may reuse a pool thread and its TLS.
            shortReadFailures.store(0);
            shortDiscardCancellation = recording.cancel.get();
            const auto removed = attempt(result.packageContext, result.packageGeneration, recording.cancel);
            shortDiscardCut = 0; shortDiscardCancellation = nullptr;
            denyDeletionReadback.store(false); denyShortBootstrap.store(false); recording.cancel->store(false);
            if (mode) {
                std::fprintf(stderr, "SHORT_DISCARD cut_mode=%u hits=%u ok=%u error=%u native=%u absent=%u\n",
                    mode, shortDiscardCutHits, removed.ok() ? 1U : 0U, static_cast<unsigned>(removed.error),
                    removed.nativeError, !std::filesystem::exists(path) ? 1U : 0U);
                assert(shortDiscardCutHits == 1 && !removed.ok() && removed.error == CustodyFileError::recoveryRequired);
                if (mode == 11) {
                    assert(shortReadFailures.load() >= 1); // Addressed bootstrap index, not the preceding inventory read.
                    std::fprintf(stderr, "SHORT_DISCARD bootstrap_index_read_faults=%u\n", shortReadFailures.load());
                }
                std::fprintf(stderr, "SHORT_DISCARD after_effect_mode=%u reconciliation_required=1 terminal_ack=0\n", mode);
            } else assert(removed.ok() && *removed.value);
            assert(!std::filesystem::exists(path));
            assert(recording.store->queueGeneration() == generation);
            auto expected = before;
            for (auto it = expected.begin(); it != expected.end();) {
                if (it->first.find(std::wstring(recording.session.begin(), recording.session.end()) + L"\\") == 0)
                    it = expected.erase(it);
                else ++it;
            }
            assert(snapshot(recording.paths.root) == expected); // No fake queue insertion/commit.
            if (mode) {
                const auto wrongPending = attempt(wrong, result.packageGeneration, recording.cancel);
                assert(!wrongPending.ok() && wrongPending.error == CustodyFileError::recoveryRequired);
                const auto newBirth = recording.store->createPackage("must-not-overtake-short", recording.cancel);
                assert(!newBirth.ok() && newBirth.error == CustodyFileError::recoveryRequired);
                if (mode == 11) {
                    const auto reads = shortReadFailures.load();
                    std::array<CustodyNativeJob, 4> jobs;
                    for (const auto& job : jobs) assert(job);
                    denyDeletionReadback.store(true);
                    const auto busy = attempt(result.packageContext, result.packageGeneration, recording.cancel);
                    denyDeletionReadback.store(false);
                    assert(!busy.ok() && busy.error == CustodyFileError::recoveryRequired &&
                        busy.nativeError == ERROR_NOT_ENOUGH_QUOTA && shortReadFailures.load() == reads);
                }
            }
            const auto repeated = attempt(result.packageContext, result.packageGeneration, recording.cancel);
            if (mode) {
                assert(repeated.ok() && *repeated.value); // Same continuously held owner reconciles its actual attempt.
                assert(shortDiscardCutHits == 1); // Read-only reconciliation, never a second Shell effect.
                const auto again = attempt(result.packageContext, result.packageGeneration, recording.cancel);
                assert(!again.ok() || !*again.value);
            } else assert(!repeated.ok() || !*repeated.value);
            recording.store.reset();
            const auto cold = ProtectedCustodyStoreOwner::open(recording.paths.root, recording.cancel); assert(cold.ok());
            const auto missing = (*cold.value)->discardShortRecording(recording.session, result.packageContext,
                result.packageGeneration, recording.cancel);
            assert(!missing.ok() || !*missing.value); // A new owner cannot manufacture the old attempt.
            const auto queue = (*cold.value)->readQueueValue(recording.cancel);
            assert(queue.ok() && (*queue.value)->items().empty() && !std::filesystem::exists(path));
            std::fputs("SHORT_DISCARD actual_recycle=1 queue_unchanged=1 cold_verified=1 audio=0\n", stderr);
        }).get();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
    }
}
void protectedLocalPurge(bool userRemoval = false) {
    // Only generated encrypted fixtures; never a device, user recording or server.
    const auto started = std::chrono::steady_clock::now();
    const auto mark = [&](unsigned mode, const char* stage) {
        std::fprintf(stderr, "PURGE_PHASE user_removal=%u mode=%u stage=%s elapsed_ms=%lld\n",
            userRemoval ? 1U : 0U, mode, stage, static_cast<long long>(
                std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - started).count()));
    };
    const DesktopHttpTransport::UploadSend account = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(request.method == "GET");
        if (request.path == "/desktop/settings/spaces")
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        assert(request.path == "/api/v1/auth/me");
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    };
    for (unsigned mode = 0; mode != 9; ++mode) {
        mark(mode, "begin"); // A subsequent begin also fences the previous fixture cleanup.
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
                mark(mode, "before_finalize");
                assert((*created.value)->finalize().normalPackage());
                mark(mode, "after_finalize");
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
        mark(mode, "prepared");
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
                    mark(mode, "recovered");
                }
            }
            const bool complete = mode != 2;
            logQueueAdmission(capture, userRemoval ? "local_removal" : "local_purge", mode);
            if (complete) assert(waitFor([&] {
                // Recovery can start another local-removal continuation. Its
                // queue ACK alone does not retire the owner-side admission fence.
                capture.pollUploads();
                return capture.localQueueComplete() && capture.readiness().storageWritable;
            }));
            assert(capture.localQueueComplete() == complete && capture.readiness().storageWritable == complete);
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
        mark(mode, "cold_shutdown");
        std::fprintf(stderr, "%s mode=%u actual_recycle=%u cold_queue=1 audio=0 real_network=0\n",
            userRemoval ? "PROTECTED_LOCAL_REMOVAL" : "PROTECTED_LOCAL_PURGE", mode, mode != 1 && mode != 4 && mode != 7);
        mark(mode, "end"); // The current fixture is still alive here.
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
            const bool complete = mode != 4;
            if (complete) assert(waitFor([&] { return capture.localQueueComplete(); }));
            assert(capture.localQueueComplete() == complete && capture.readiness().storageWritable == complete);
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
            logQueueAdmission(capture, "purge_flight", mode);
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture); return capture.localQueueComplete(); }));
            assert(capture.readiness().storageWritable == (mode != 6 && mode != 8 && mode != 9 && mode != 12));
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
void protectedDeletionDisplayDrain(bool unfinished = false, bool physicalPurge = false, bool userRemoval = false) {
    assert(!physicalPurge || unfinished);
    assert(!userRemoval || physicalPurge);
    Fixture fixture;
    const std::string session = unfinished ? "44444444-4444-4444-8444-444444444444" : "waiting";
    if (!unfinished) seedQueue(fixture.root);
    auto seed = std::async(std::launch::async, [&] {
        auto cancellation = std::make_shared<std::atomic<bool>>(false);
        auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(opened.ok());
        if (unfinished) {
            auto queue = (*opened.value)->readQueueValue(cancellation); assert(queue.ok());
            ProtectedUploadQueueValue candidate(**queue.value);
            auto prepared = (*opened.value)->prepareRecordingReservation(candidate, session,
                "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", true, 1000, cancellation);
            assert(prepared.ok() && *prepared.value);
            auto bytes = candidate.serialize(cancellation); assert(bytes.ok());
            assert(commitProtectedCustodyMetadata(*opened.value, (*opened.value)->queueContext(), 1, *bytes.value, cancellation).state == CustodyCommitState::committed);
            auto package = (*opened.value)->createPackage(session, cancellation); assert(package.ok());
            auto canonical = (*package.value)->createWriter(CustodyRole::canonical); assert(canonical.ok());
            std::array<float, 100 * 480> samples{}; samples.fill(0.25F);
            assert((*canonical.value)->writeAt(0, samples.data(), sizeof(samples)).ok());
            assert((*canonical.value)->checkpoint().state == CustodyCommitState::committed);
            return;
        }
        auto writer = V5LocalRecordingWriter::open(*opened.value, session, cancellation); assert(writer.ok());
        CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
        for (unsigned n = 0; n != 100; ++n) { frame.ptsFrames = n * 480; assert((*writer.value)->append(frame)); }
        assert((*writer.value)->finalize().normalPackage());
    });
    seed.get(); // No birth owner survives the cold startup.
    const auto packageBefore = snapshot(fixture.root / session);
    const auto holdRead = [&] {
        oldPackedPath = L"\\\\?\\" + (fixture.root / session / L".custody-v1" / L"canonical" / L"content.packed-v2").native();
        { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
        pauseOldPackedRead.store(true);
    };
    if (unfinished) holdRead(); // Recovery starts before the authenticated display.
    const DesktopHttpTransport::UploadSend wire = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(request.method == "GET");
        if (request.path == "/desktop/settings/spaces")
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        assert(request.path == "/api/v1/auth/me");
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    };
    std::atomic<unsigned> protectedHttp{0};
    {
        NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, wire,
            [&](const auto&, const auto&) { ++protectedHttp; return DesktopHttpTransport::ProtectedUploadResponse{503, "{}"}; });
        startAndAdopt(capture, 2); capture.setAuthSessionToken("generated-deletion-display-owner");
        assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
        if (!unfinished) holdRead();
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
        if (physicalPurge) {
            const auto ticket = userRemoval ? capture.requestProtectedLocalRemoval(
                NativeCaptureStorageTestPeer::projection(capture), session, capture.authGeneration()) :
                capture.beginProtectedDeletionSelection({{DeletionTarget::ownOrigin, CustodyString(session.data(), session.size())}});
            assert(ticket && waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            const auto intent = NativeCaptureStorageTestPeer::workerTicket(capture);
            assert(intent.kind == NativeCapture::QueueMutationKind::deletionIntent && intent.state == NativeCapture::QueueTicketState::committed &&
                intent.error == CustodyFileError::none && intent.changed && intent.baseGeneration == 2 && intent.targetGeneration == 3);
            NativeCaptureStorageTestPeer::pollStorage(capture);
            assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::deletionPurgeWaiting(capture); }));
            const auto value = NativeCaptureStorageTestPeer::projection(capture);
            assert(value && value->items().size() == 1 && value->items()[0].safeReason == "local_delete_pending" &&
                NativeCaptureStorageTestPeer::generation(capture) == 3);
            const auto until = std::chrono::steady_clock::now() + std::chrono::milliseconds(100);
            bool premature = false;
            while (std::chrono::steady_clock::now() < until) {
                capture.pollUploads();
                premature = premature || capture.takeProtectedDeletionCompletion(ticket->id).has_value() ||
                    NativeCaptureStorageTestPeer::workerTicket(capture).id != ticket->id || !std::filesystem::exists(fixture.root / session);
                Sleep(1);
            }
            { std::lock_guard<std::mutex> lock(cutMutex); assert(cutReached && !cutReleased); }
            assert(!premature && snapshot(fixture.root / session) == packageBefore && !protectedHttp.load());
            std::fputs("UNFINISHED_PURGE intent_commit_ack=1 actual_purge_waiting=1 held_read=1 premature_purge=0 generation=3\n", stderr);
            releaseCut();
            std::optional<NativeCapture::DeletionCompletion> completion;
            assert(waitFor([&] { capture.pollUploads(); completion = capture.takeProtectedDeletionCompletion(ticket->id); return completion.has_value(); }));
            // pollUploads can already submit an unrelated no-op uploadPrepare
            // after retiring deletion. Read the retained deletion ACK by its ID.
            const auto purgeAck = capture.protectedDeletionTicket(ticket->id + 1);
            assert(purgeAck);
            const auto& purge = *purgeAck;
            std::fprintf(stderr, "UNFINISHED_PURGE_RESULT saved=%u unknown=%u accepted=%zu pending=%zu rejected=%zu kind=%u state=%u error=%u native=%lu base=%llu target=%llu generation=%llu rows=%zu exists=%u http=%u\n",
                completion->saved, completion->unknown, completion->accepted, completion->pending, completion->rejected,
                static_cast<unsigned>(purge.kind), static_cast<unsigned>(purge.state), static_cast<unsigned>(purge.error),
                static_cast<unsigned long>(purge.nativeError), static_cast<unsigned long long>(purge.baseGeneration),
                static_cast<unsigned long long>(purge.targetGeneration), static_cast<unsigned long long>(NativeCaptureStorageTestPeer::generation(capture)),
                NativeCaptureStorageTestPeer::projection(capture)->items().size(), std::filesystem::exists(fixture.root / session), protectedHttp.load());
            assert(completion->saved && !completion->unknown && completion->accepted == 1 && !completion->pending && !completion->rejected &&
                purge.kind == NativeCapture::QueueMutationKind::deletionPurge && purge.state == NativeCapture::QueueTicketState::committed &&
                purge.baseGeneration == 3 && purge.targetGeneration == 4 && !std::filesystem::exists(fixture.root / session) &&
                NativeCaptureStorageTestPeer::projection(capture)->items().empty() && NativeCaptureStorageTestPeer::generation(capture) == 4 && !protectedHttp.load());
        } else {
            ioCut.store(IoCut::ambiguousRename);
            const auto ticket = capture.requestProtectedDeletionSelection({{DeletionTarget::ownOrigin, CustodyString(session.data(), session.size())}}, true);
            const bool intentReady = ticket && waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); });
            ioCut.store(IoCut::none);
            if (!intentReady) { releaseCut(); assert(intentReady); return; }
            NativeCaptureStorageTestPeer::pollStorage(capture);
            bool displayStillHeld = !NativeCaptureStorageTestPeer::displayFinished(capture);
            if (unfinished) {
                const auto work = NativeCaptureStorageTestPeer::storageWork(capture);
                std::lock_guard<std::mutex> lock(work->mutex);
                displayStillHeld = work->recoveryCancellation && work->recoveryCancellation->load() && !work->terminal;
            }
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
            if (unfinished) {
                const auto value = NativeCaptureStorageTestPeer::projection(capture);
                assert(value && value->items().size() == 1 && value->items()[0].safeReason == "local_delete_pending" &&
                    NativeCaptureStorageTestPeer::generation(capture) == 3 && !protectedHttp.load());
            }
        }
        capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
    }
    oldPackedPath.clear();
    if (physicalPurge) {
        std::async(std::launch::async, [&] {
            auto cancellation = std::make_shared<std::atomic<bool>>(false);
            auto owner = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(owner.ok());
            auto value = (*owner.value)->readQueueValue(cancellation); assert(value.ok());
            assert((*owner.value)->queueGeneration() == 4 && (*value.value)->items().empty() && !std::filesystem::exists(fixture.root / session));
        }).get();
        assert(!protectedHttp.load() && waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        std::fprintf(stderr, "UNFINISHED_PURGE user_removal=%u actual_retirement_before_purge=1 cold_generation=4 cold_rows=0 os_absence=1 exact_memory=1 protected_http=0 device_audio=0 real_network=0 recycle_bin_not_shredding=1\n", userRemoval);
    } else if (unfinished) {
        assert(snapshot(fixture.root / session) == packageBefore && !protectedHttp.load());
        std::async(std::launch::async, [&] {
            auto cancellation = std::make_shared<std::atomic<bool>>(false);
            auto owner = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(owner.ok());
            assert((*owner.value)->queueGeneration() == 3);
            auto value = (*owner.value)->readQueueValue(cancellation); assert(value.ok());
            assert((*value.value)->items().size() == 1 && (*value.value)->items()[0].safeReason == "local_delete_pending");
            auto pair = (*owner.value)->readPackage(session, cancellation); assert(pair.ok());
            assert((*pair.value)->current().phase == CustodyPackagePhase::capturing);
        }).get();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        std::fputs("UNFINISHED_DELETION ambiguous_intent=1 cancellation_before_release=1 premature_readback=0 premature_drain=0 cold_pending_intent=1 package_unchanged=1 protected_http=0 device_audio=0 real_network=0\n", stderr);
    } else std::fputs("PROTECTED_DELETION_DISPLAY actual_inspection=1 premature_readback=0 actual_drain=1 audio=0 network_delete=0\n", stderr);
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
            if (committed) assert(waitFor([&] { return capture.localQueueComplete(); }));
            assert(capture.localQueueComplete() == committed && capture.readiness().storageWritable == committed);
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
void protectedSameCookieProof() {
    const auto baseline = CustodyOwnedMemory::usedBytes();
    Fixture fixture; seedQueue(fixture.root);
    constexpr auto user = "11111111-1111-4111-8111-111111111111";
    constexpr auto a = "22222222-2222-4222-8222-222222222222";
    constexpr auto b = "55555555-5555-4555-8555-555555555555";
    std::atomic<bool> switched{false}, entered{false}, released{false};
    std::atomic<unsigned> active{0}, peak{0};
    const DesktopHttpTransport::UploadSend wire = [&](const auto& config, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(request.method == "GET" && config.sessionToken == "generated-same-cookie");
        const bool changed = switched.load(); const std::string workspace = changed ? b : a;
        if (request.path == "/desktop/settings/spaces") {
            assert(config.workspaceId.empty() && !config.confirmedIdentity);
            const auto concurrent = ++active; peak.store((std::max)(peak.load(), concurrent));
            if (changed) { entered.store(true); assert(waitFor([&] { return released.load(); })); }
            --active;
            return {200, "{\"spaces\":[{\"id\":\"" + workspace + "\",\"active\":true}]}"};
        }
        if (request.path == "/api/v1/auth/me")
            return {200, "{\"user_id\":\"" + std::string(user) + "\",\"workspace_id\":\"" + workspace +
                "\",\"active_session_id\":\"33333333-3333-4333-8333-333333333333\"}"};
        assert(request.path == DesktopApiClient::notificationContextPath);
        return {200, "{\"user_id\":\"" + std::string(user) + "\",\"workspace_id\":\"" + workspace + "\",\"recording_deletion_protocol_version\":1}"};
    };
    bool started = false, adopted = false, epochChanged = false;
    {
        NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, wire);
        startAndAdopt(capture, 2);
        capture.setAuthSessionToken("generated-same-cookie", true);
        assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
        assert(capture.currentAccount()->workspaceId == a);
        const auto epoch = capture.authGeneration();
        switched.store(true);
        capture.setAuthSessionToken("generated-same-cookie", true);
        capture.recover(RecoveryTrigger::activation);
        started = waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return entered.load(); });
        if (started) {
            capture.recover(RecoveryTrigger::wake); capture.recover(RecoveryTrigger::scheduled);
            NativeCaptureStorageTestPeer::pollAccount(capture);
            assert(!capture.currentAccount()); // Pending lookup cannot lend the previous network scope.
        }
        released.store(true);
        adopted = started && waitFor([&] {
            NativeCaptureStorageTestPeer::pollAccount(capture);
            return capture.currentAccount() && capture.currentAccount()->workspaceId == b;
        });
        epochChanged = capture.authGeneration() > epoch;
        capture.shutdown();
        assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
    }
    assert(started && adopted && epochChanged && peak.load() == 1 && "same_cookie_requires_fresh_native_workspace_proof");
    assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
}

void protectedAccountProblems() {
    protectedSameCookieProof();
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
        assert(capture.localQueueComplete() && capture.readiness().storageWritable);
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
    bool accountAdopted = false, timingObserved = false, sameQueue = false, storageReady = false, drained = false;
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
        storageReady = capture.localQueueComplete() && capture.readiness().storageWritable;
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
    std::fprintf(stderr, "PROTECTED_DISPLAY timing=%u account=%u same_queue=%u storage_ready=%u account_calls=%u unexpected_calls=%u upload_calls=%u drain=%u disk_unchanged=%u memory_released=%u quota_unknown=%u logout_revoked=%u native_cut=%u stale_revoked=%u\n",
        timingObserved, accountAdopted, sameQueue, storageReady, accountCalls.load(), unexpectedCalls.load(), uploadCalls.load(),
        drained, diskUnchanged, memoryReleased, quotaUnknown, logoutRevoked, cutObserved, staleRevoked);
    assert(drained && memoryReleased && "protected_display_timing_releases_workers_and_native_owners");
    assert(accountAdopted && accountCalls == 4 && "protected_display_timing_requires_actual_account_resolver");
    assert(timingObserved && "protected_display_uploaded_row_requires_genuine_package_timing");
    assert(quotaUnknown && logoutRevoked && cutObserved && staleRevoked &&
        "protected_display_timing_quota_and_stale_native_completion_remain_unknown");
    assert(sameQueue && diskUnchanged && unexpectedCalls == 0 && uploadCalls == 0 && storageReady &&
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
        assert(capture.localItems().empty() && capture.localQueueComplete() && !capture.uploadsBusy());
        assert(capture.readiness().storageWritable);
        assert(!capture.requestProtectedManualSend(before, "waiting", capture.authGeneration() + 1, false));
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
        assert(capture.localQueueComplete() && !capture.readiness().storageWritable);
        assert(capture.record().reason == ReasonCode::storageUnavailable);
        capture.shutdown();
    }
    NativeCapture restarted(fixture.root, {std::make_shared<GeneratedAec>(), false});
    startAndAdopt(restarted, 3);
    observed = observed && restarted.localObservation().value == NativeCaptureStorageTestPeer::projection(restarted) &&
        restarted.localObservation().complete;
    assert(restarted.localQueueComplete() && restarted.readiness().storageWritable);
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
            assert(capture.localQueueComplete() == (cut == IoCut::pauseAfterRename));
            assert(!capture.readiness().storageWritable && !capture.uploadsBusy());
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
// Generated legacy input only: the ordinary writer captures JSON in memory;
// neither load() nor a production protected owner is used to seed this root.
struct MigrationReadModelSeed {
    testing::GeneratedLegacyPackage package;
    std::string ledger;
};
MigrationReadModelSeed seedMigrationReadModel(const std::filesystem::path& root, bool v3) {
    return std::async(std::launch::async, [&] {
        MigrationReadModelSeed result;
        // Same explicit current-user protected DACL as FilesFixture. Inherited
        // TEMP permissions are not valid native root/package custody fixtures.
        HANDLE token = nullptr; assert(OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token));
        DWORD size = 0; GetTokenInformation(token, TokenUser, nullptr, 0, &size);
        std::vector<std::uint8_t> bytes(size);
        assert(GetTokenInformation(token, TokenUser, bytes.data(), size, &size)); assert(CloseHandle(token));
        LPWSTR sid = nullptr;
        assert(ConvertSidToStringSidW(reinterpret_cast<TOKEN_USER*>(bytes.data())->User.Sid, &sid));
        const auto sddl = std::wstring(L"D:P(A;OICI;FA;;;") + sid + L")"; LocalFree(sid);
        PSECURITY_DESCRIPTOR descriptor = nullptr;
        assert(ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl.c_str(), SDDL_REVISION_1, &descriptor, nullptr));
        SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), descriptor, FALSE};
        assert(CreateDirectoryW(root.c_str(), &security));
        assert(CreateDirectoryW((root / L"legacy-package").c_str(), &security));
        LocalFree(descriptor);
        result.package = testing::makeGeneratedLegacyPackage(root / L"legacy-package", 100);
        // Add the existing optional v5 session field before taking the source
        // snapshot; migration must copy these generated manifest bytes exactly.
        { std::ifstream in(result.package.manifestPath, std::ios::binary); assert(in);
          std::string manifest(std::istreambuf_iterator<char>(in), {}); in.close();
          assert(!manifest.empty() && manifest.front() == '{');
          manifest.insert(1, R"("sessionId":"legacy-session",)");
          std::ofstream out(result.package.manifestPath, std::ios::binary); out << manifest; assert(out); }
        std::string json;
        DesktopUploadQueueService queue(root / L"unused.json", root,
            [&](const auto&, const auto&, std::string_view bytes) { json.assign(bytes); return true; });
        queue.setClock([] { return 1000; });
        assert(queue.enqueue({"legacy-recording", "legacy-package", "legacy-session", result.package.packageDirectory,
            UploadQueueStatus::needsAuth, {11, 22, 33}, 3, "auth_required",
            "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"}));
        const auto fields = DesktopApiClient::jsonObjectFields(json); assert(fields);
        std::string items(fields->at("items"));
        const std::string access = ",\"access_state\":null";
        const auto at = items.find(access); assert(at != std::string::npos);
        items.erase(at, access.size()); assert(items.find(access) == std::string::npos);
        // Existing protectedQueueCandidate golden operation/ACK, unrelated to
        // this local-only row: migration must preserve the entire ledger.
        constexpr auto operation = R"({"operation_id":"33333333-3333-4333-8333-333333333333","target":"meeting","target_id":"44444444-4444-4444-8444-444444444444","actor_user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","server_origin":"https:\/\/example.test","phase":3,"requested_at_ms":100,"updated_at_ms":200,"attempts":3,"next_attempt_at_ms":300,"receipt_request_id":"55555555-5555-4555-8555-555555555555","safe_reason":"accepted"})";
        constexpr auto ack = R"({"task_id":"66666666-6666-4666-8666-666666666666","meeting_id":"44444444-4444-4444-8444-444444444444","acknowledged_at_ms":900})";
        result.ledger = std::string("{\"schema_version\":\"desktop-upload-queue.") + (v3 ? "v3" : "v2") + "\",\"items\":" + items;
        if (v3) result.ledger += std::string(",\"updated_at_ms\":1000,\"deletion_operations\":[") + operation +
            "],\"purge_acknowledgements\":[" + ack + "]";
        result.ledger += "}";
        { std::ofstream out(root / L"desktop-upload-queue.v2", std::ios::binary); assert(out);
          out.write(result.ledger.data(), static_cast<std::streamsize>(result.ledger.size())); assert(out); }
        assert(!std::filesystem::exists(root / L".custody-v1"));
        return result;
    }).get();
}
void nativeLegacyMigrationReadModel() {
    const auto baseline = CustodyOwnedMemory::usedBytes();
    for (const bool v3 : {true, false}) {
        Fixture fixture;
        const auto seed = seedMigrationReadModel(fixture.root, v3);
        const auto original = snapshot(fixture.root);
        const auto checkRows = [&](const auto& value, bool recovered) {
            assert(value.items().size() == 1);
            const auto& row = value.items()[0];
            assert(row.localRecordingId == "legacy-recording" && row.directoryId == "legacy-package" && row.sessionId == "legacy-session");
            assert(std::string_view(row.packageDirectory) == seed.package.packageDirectory.u8string());
            assert(row.ownerUserId == "11111111-1111-4111-8111-111111111111" && row.ownerWorkspaceId == "22222222-2222-4222-8222-222222222222");
            assert((row.acceptedBytes == std::array<std::uint64_t, 3>{11, 22, 33}) && row.attempts == 3);
            assert(row.status == (recovered ? UploadQueueStatus::retry : UploadQueueStatus::needsAuth));
            assert(row.safeReason == (recovered ? "auth_recovered" : "auth_required"));
            assert(row.meetingId.empty() && row.mediaRevisionId.empty() && row.uploadSessionId.empty());
            assert(row.serverStatus.empty() && row.processingStatus.empty() && row.mediaRevisionStatus.empty() && !row.accessState);
            if (!recovered) assert(row.updatedAtMs == 1000 && value.updatedAtMs() == (v3 ? 1000 : 0));
            assert(value.deletionOperations().size() == (v3 ? 1 : 0) && value.purgeAcknowledgements().size() == (v3 ? 1 : 0));
            if (v3) {
                const auto& op = value.deletionOperations()[0];
                assert(op.operationId == "33333333-3333-4333-8333-333333333333" && op.target == DeletionTarget::meeting);
                assert(op.targetId == "44444444-4444-4444-8444-444444444444" && op.actorUserId == row.ownerUserId && op.workspaceId == row.ownerWorkspaceId);
                assert(op.serverOrigin == "https://example.test" && static_cast<unsigned>(op.phase) == 3);
                assert(op.requestedAtMs == 100 && op.updatedAtMs == 200 && op.attemptCount == 3 && op.nextAttemptAtMs == 300);
                assert(op.receiptRequestId == "55555555-5555-4555-8555-555555555555" && op.safeReason == "accepted");
                const auto& ack = value.purgeAcknowledgements()[0];
                assert(ack.taskId == "66666666-6666-4666-8666-666666666666" && ack.meetingId == op.targetId && ack.acknowledgedAtMs == 900);
            }
        };
        const auto fixedFiles = [&] {
            auto files = snapshot(fixture.root);
            // Queue indices/blocks legitimately change after recovery. Its fixed
            // identity and all bootstrap/history/package/original files do not.
            for (auto it = files.begin(); it != files.end();) {
                if (it->first.rfind(L".custody-v1\\queue\\", 0) == 0 && std::filesystem::path(it->first).filename() != L"id.bin")
                    it = files.erase(it);
                else ++it;
            }
            return files;
        };
        std::atomic<unsigned> wireCalls{0};
        const DesktopHttpTransport::UploadSend wire = [&](const auto&, const auto&) {
            ++wireCalls; return DesktopHttpTransport::UploadResponse{503, "{}"};
        };
        const DesktopHttpTransport::ProtectedUploadSend protectedWire = [&](const auto&, const auto&) {
            ++wireCalls; return DesktopHttpTransport::ProtectedUploadResponse{503, "{}"};
        };
        CustodyContext nativeContext{};
        std::uint64_t initialGeneration = 0, recoveredGeneration = 0;
        std::string adoptedBytes;
        Snapshot fixed;
        {
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, wire, protectedWire);
            capture.startStorageValidation();
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::ready(capture); }));
            assert(NativeCaptureStorageTestPeer::opened(capture) && "native_startup_must_migrate_valid_legacy_before_ready_admission");
            assert(NativeCaptureStorageTestPeer::generation(capture) == 0 && !NativeCaptureStorageTestPeer::projection(capture));
            assert(!capture.localQueueComplete() && !capture.readiness().storageWritable);
            assert(!capture.localObservation().value && !capture.localObservation().complete && !capture.updateWorkDrained());
            assert(capture.record().reason == ReasonCode::storageUnavailable);
            capture.pollUploads(); // The real startup ACK, not an injected projection.
            initialGeneration = NativeCaptureStorageTestPeer::generation(capture); assert(initialGeneration);
            const auto before = NativeCaptureStorageTestPeer::projection(capture); assert(before && !before->lastAuthenticatedContext()); checkRows(*before, false);
            assert(capture.localQueueComplete() && capture.readiness().storageWritable && capture.localObservation().complete);
            {
                const auto work = NativeCaptureStorageTestPeer::storageWork(capture);
                std::lock_guard<std::mutex> lock(work->mutex); nativeContext = work->context;
            }
            fixed = fixedFiles();
            capture.recover(RecoveryTrigger::authRecovered);
            capture.pollUploads();
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            assert(NativeCaptureStorageTestPeer::projection(capture) == before && NativeCaptureStorageTestPeer::generation(capture) == initialGeneration);
            assert(!capture.localObservation().complete);
            capture.pollUploads(); // Physical commit/readback -> actual adoption.
            const auto ticket = NativeCaptureStorageTestPeer::ticket(capture); assert(ticket);
            assert(ticket->state == NativeCapture::QueueTicketState::committed && ticket->changed);
            assert(ticket->baseGeneration == initialGeneration && ticket->targetGeneration == initialGeneration + 1);
            recoveredGeneration = NativeCaptureStorageTestPeer::generation(capture); assert(recoveredGeneration == ticket->targetGeneration);
            const auto after = NativeCaptureStorageTestPeer::projection(capture); assert(after && after != before && !after->lastAuthenticatedContext()); checkRows(*after, true);
            assert(before->items()[0].status == UploadQueueStatus::needsAuth);
            auto cancel = std::make_shared<std::atomic<bool>>(false);
            const auto bytes = after->serialize(cancel); assert(bytes.ok());
            adoptedBytes.assign(reinterpret_cast<const char*>(bytes.value->data()), bytes.value->size());
            assert(fixedFiles() == fixed);
            capture.shutdown();
            assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
            assert(NativeCaptureStorageTestPeer::released(capture));
        }
        struct Identity {
            CustodyContext bootstrap{}, package{}, intent{};
            CustodyId transaction{};
        };
        std::optional<Identity> firstIdentity;
        const auto verifyCold = [&] {
            const auto disk = snapshot(fixture.root);
            const auto identity = std::async(std::launch::async, [&] {
                auto cancel = std::make_shared<std::atomic<bool>>(false);
                Identity observed;
                {
                    auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(opened.ok());
                    auto owner = *opened.value;
                    assert(owner->queueContext().storeId == nativeContext.storeId && owner->queueContext().objectId == nativeContext.objectId);
                    assert(owner->queueContext().role == CustodyRole::queue && owner->queueGeneration() == recoveredGeneration);
                    auto queue = owner->readQueueValue(cancel); assert(queue.ok()); checkRows(**queue.value, true);
                    auto bytes = (*queue.value)->serialize(cancel); assert(bytes.ok());
                    assert(std::string_view(reinterpret_cast<const char*>(bytes.value->data()), bytes.value->size()) == adoptedBytes);
                    auto pair = owner->readPackage("legacy-package", cancel); assert(pair.ok());
                    observed.package = (*pair.value)->current().context;
                    assert(observed.package.storeId == nativeContext.storeId && observed.package.role == CustodyRole::packageState);
                    for (const auto& slot : (*pair.value)->slots()) assert(slot.phase == CustodyPackagePhase::sealedNormal && slot.refCount == 3);
                    {
                        auto proof = LocalRecordingPackage::inspectProtected(fixture.root, *pair.value, "legacy-session", cancel); assert(proof.ok());
                        const auto& evidence = (*proof.value)->evidence();
                        assert(evidence.integrity == PackageIntegrity::valid && evidence.durationMs == seed.package.durationMs && evidence.manifestSessionMatched);
                        assert(evidence.startedAtMs == seed.package.startedAtMs && evidence.stoppedAtMs == seed.package.stoppedAtMs &&
                            evidence.displayTimezoneOffsetMinutes == seed.package.displayTimezoneOffsetMinutes && evidence.playback.decodedFrames);
                    } // Release inspection member leases before the independent reader group.
                    auto readers = openProtectedCustodyReaders(fixture.root, *pair.value, cancel); assert(readers.ok());
                    for (unsigned slot = 0; slot != 2; ++slot) {
                        const auto& state = (*pair.value)->slots()[slot];
                        for (std::size_t i = 0; i != state.refCount; ++i) {
                            const auto role = state.refs[i].role;
                            assert(role == CustodyRole::manifest || role == CustodyRole::media || role == CustodyRole::playback);
                            const auto source = role == CustodyRole::media ? L"media" : role == CustodyRole::playback ? L"playback" : L"manifest";
                            const auto path = fixture.root / L"legacy-package" / L".custody-v1" / L"legacy.originals" / source;
                            const auto longPath = path.native().substr(0, 4) == L"\\\\?\\" ? path : std::filesystem::path(L"\\\\?\\" + path.native());
                            std::ifstream originalBytes(longPath, std::ios::binary); assert(originalBytes && state.refs[i].length);
                            std::array<char, 65536> actual{}, expected{};
                            auto* stream = readers.value->at(slot).at(i).stream.Get(); assert(stream);
                            std::uint64_t done = 0;
                            while (done < *state.refs[i].length) {
                                const auto count = static_cast<ULONG>((std::min)(std::uint64_t{actual.size()}, *state.refs[i].length - done));
                                ULONG got = 0; assert(stream->Read(actual.data(), count, &got) == S_OK && got == count);
                                originalBytes.read(expected.data(), count); assert(originalBytes.gcount() == count);
                                assert(std::memcmp(actual.data(), expected.data(), count) == 0); done += count;
                            }
                            assert(originalBytes.peek() == std::char_traits<char>::eof());
                        }
                    }
                } // All ordinary owner/member leases released before discovery.
                auto bootstrap = ProtectedCustodyBootstrapPair::read(fixture.root, cancel); assert(bootstrap.ok());
                observed.bootstrap = (*bootstrap.value)->current().context;
                assert(observed.bootstrap.storeId == nativeContext.storeId && observed.bootstrap.role == CustodyRole::bootstrap);
                for (const auto& slot : (*bootstrap.value)->slots()) {
                    assert(slot.mode == CustodyBootstrapMode::protectedStore && !slot.transactionId && !slot.subject && !slot.directory);
                    assert(slot.queueObjectId == nativeContext.objectId);
                }
                auto input = ProtectedCustodyQueueInput::read(*bootstrap.value, cancel); assert(input.ok());
                assert((*input.value)->indices().indices[(*input.value)->indices().selectedSlot].generation == recoveredGeneration);
                const auto& payloads = (*input.value)->payloads();
                const auto selected = (*input.value)->indices().selectedSlot;
                assert(std::string_view(reinterpret_cast<const char*>(payloads[selected].data()), payloads[selected].size()) == adoptedBytes);
                const auto other = 1U - selected;
                assert(std::string_view(reinterpret_cast<const char*>(payloads[other].data()), payloads[other].size()) == seed.ledger);
                auto candidate = ProtectedUploadQueueCandidate::read(*input.value, cancel); assert(candidate.ok()); checkRows(**candidate.value, true);
                // No caller transaction: completed-history discovery authenticates
                // its independent immutable Birth before strict current decode.
                auto history = ProtectedCustodyMigrationPair::read(*bootstrap.value, cancel); assert(history.ok());
                const auto& current = (*history.value)->current();
                observed.intent = current.context; observed.transaction = current.transactionId;
                for (const auto& slot : (*history.value)->slots()) {
                    assert(slot.subject == CustodyMigrationSubject::queue && !slot.directory && slot.stage == CustodyMigrationStage::switched);
                    assert(!slot.authorization && slot.barrier && slot.sourceCount == 1 && slot.sources[0].kind == CustodyMigrationSourceKind::ledger);
                    assert(slot.transactionId == observed.transaction && slot.context.storeId == nativeContext.storeId && slot.context.role == CustodyRole::migrationIntent);
                    assert(slot.sources[0].destinationObjectId == nativeContext.objectId && slot.sources[0].destinationGeneration == initialGeneration);
                    assert(slot.sources[0].length == seed.ledger.size() && slot.sources[0].destinationLength == seed.ledger.size());
                    assert(slot.sources[0].destinationSha256 && slot.sources[0].sha256 == *slot.sources[0].destinationSha256);
                    assert(slot.sources[0].sha256 == sha256Digest(seed.ledger) && slot.barrier->objectId == current.context.objectId);
                }
                std::string barrierHash;
                for (const auto byte : current.barrier->sha256) {
                    barrierHash += "0123456789abcdef"[byte >> 4]; barrierHash += "0123456789abcdef"[byte & 15];
                }
                assert(disk.at(L"desktop-upload-queue.v2") == barrierHash);
                assert(current.barrier->envelopeBytes == std::filesystem::file_size(fixture.root / L"desktop-upload-queue.v2"));
                return observed;
            }).get();
            if (!firstIdentity) firstIdentity = identity;
            else {
                assert(identity.bootstrap.objectId == firstIdentity->bootstrap.objectId && identity.package.objectId == firstIdentity->package.objectId);
                assert(identity.intent.objectId == firstIdentity->intent.objectId && identity.transaction == firstIdentity->transaction);
            }
            assert(snapshot(fixture.root) == disk && fixedFiles() == fixed);
            const auto now = snapshot(fixture.root);
            assert(now.at(L".custody-v1\\legacy.originals\\ledger") == sha256(seed.ledger));
            for (const auto& names : {std::pair{L"manifest.json", L"manifest"}, std::pair{L"meeting-transcription.wav", L"media"}, std::pair{L"meeting-review.m4a", L"playback"}})
                assert(now.at(std::wstring(L"legacy-package\\.custody-v1\\legacy.originals\\") + names.second) == original.at(std::wstring(L"legacy-package\\") + names.first));
            assert(now.at(L"desktop-upload-queue.v2") == now.at(L"desktop-upload-queue.v2.quarantine") && now.at(L"desktop-upload-queue.v2") != sha256(seed.ledger));
        };
        verifyCold();
        {
            NativeCapture cold(fixture.root, {std::make_shared<GeneratedAec>(), false}, wire, protectedWire);
            startAndAdopt(cold, recoveredGeneration); checkRows(*NativeCaptureStorageTestPeer::projection(cold), true);
            assert(cold.localQueueComplete() && cold.readiness().storageWritable);
            cold.shutdown(); assert(waitFor([&] { cold.pollUploads(); return cold.shutdownWorkDrained(); }));
            assert(NativeCaptureStorageTestPeer::released(cold));
        }
        verifyCold();
        assert(!wireCalls);
        std::fprintf(stderr, "NATIVE_MIGRATION schema=%u adopted=1 recovery_committed=1 cold=1 both_history=1 originals_retained=1 generated_exact_bytes=1 real_network=0 device_audio=0\n", v3 ? 3U : 2U);
    }
    assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
}
void nativeLegacyQuarantineReadModel() {
    const auto baseline = CustodyOwnedMemory::usedBytes();
    {
        Fixture fixture;
        const auto seed = seedMigrationReadModel(fixture.root, true);
        { std::ofstream out(fixture.root / L"desktop-upload-queue.v2.quarantine", std::ios::binary);
          out << "generated unknown pre-existing quarantine"; assert(out); }
        const auto before = snapshot(fixture.root);
        assert(before.at(L"desktop-upload-queue.v2") == sha256(seed.ledger));
        for (unsigned restart = 0; restart != 2; ++restart) {
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false});
            capture.startStorageValidation();
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(capture); }));
            capture.pollUploads();
            assert(!NativeCaptureStorageTestPeer::generation(capture) && !NativeCaptureStorageTestPeer::projection(capture));
            assert(!capture.localQueueComplete() && !capture.readiness().storageWritable);
            assert(!capture.localObservation().value && !capture.localObservation().complete);
            assert(!std::filesystem::exists(fixture.root / L".custody-v1") && snapshot(fixture.root) == before);
            capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        }
    }
    assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
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
    std::fprintf(stderr, "BLOCKED_CAPTURE accepted=%u state=%u reason=%u prepared=%u frames=%llu\n",
        result.accepted(), static_cast<unsigned>(result.state), static_cast<unsigned>(result.reason),
        NativeCaptureStorageTestPeer::prepared(capture),
        static_cast<unsigned long long>(NativeCaptureStorageTestPeer::writtenFrames(capture)));
    assert(result.accepted() && result.state == SessionState::blocked);
    assert(result.reason == ReasonCode::microphonePermissionDenied && !capture.indicator().visible &&
        NativeCaptureStorageTestPeer::writtenFrames(capture) == 0);
    capture.shutdown();
    assert(!capture.shutdownWorkDrained());
    assert(waitFor([&] {
        capture.pollHealth(); capture.pollUploads();
        return capture.shutdownWorkDrained();
    }, std::chrono::seconds(180)));
    logQueueAdmission(capture, "blocked_drained", 0);
    assert(capture.localQueueComplete() && !capture.readiness().storageWritable &&
        !capture.indicator().visible && NativeCaptureStorageTestPeer::writtenFrames(capture) == 0);
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
ProtectedUploadExpected readProtectedUploadExpected(const std::filesystem::path& root,
    const std::shared_ptr<const ProtectedCustodyPackagePair>& pair,
    const std::shared_ptr<std::atomic<bool>>& cancellation) {
    auto readers = openProtectedCustodyReaders(root, pair, cancellation);
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

// Both direct transport and the scheduler use the same byte-exact fake wire.
void protectedUploadFromCold(const std::filesystem::path& root, const std::string& session,
    const DesktopAccountIdentity& account,
    const std::shared_ptr<const LocalRecordingPackage::ProtectedInspection>& proof,
    const ProtectedUploadExpected& expected,
    const std::shared_ptr<std::atomic<bool>>& cancellation, const ProtectedUploadQueueValue::Item& item,
    const DesktopHttpTransport::UploadSend& schedulerAccountWire = {}, std::size_t partSizeBytes = 64 * 1024,
    bool partialResume = false, bool lateLogout = false) {
    assert(!lateLogout || (schedulerAccountWire && !partialResume));
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
    config.partSizeBytes = schedulerAccountWire ? 4 * 1024 * 1024 : partSizeBytes;
    const auto partialPrefix = static_cast<std::uint64_t>(config.partSizeBytes);
    std::map<std::pair<std::size_t, std::uint64_t>, std::uint64_t> acknowledgedParts;
    unsigned fullMediaParts = 0, mediaTails = 0;
    unsigned sync = 0, create = 0, uploadSession = 0, ranges = 0, finalize = 0, parts = 0;
    unsigned resumePass = 0;
    std::atomic<unsigned> wireCalls{0};
    std::optional<DesktopHttpTransport::ProtectedUploadRequest> retained;
    std::weak_ptr<const CustodyBytes> retainedOwner;
    std::string retainedHash;
    std::size_t retainedLength = 0;
    const char* retainedData = nullptr;
    const auto before = snapshot(root);
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
        if (partialResume) observeUploadStage(8, 0, 0); // First real send, not a simulated dispatch.
        ++wireCalls;
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
        assert(captured.partSizeBytes == config.partSizeBytes);
        if (request.path.find("/sync-state?") != std::string::npos) {
            assert(request.method == "GET");
            ++sync;
            if (partialResume && resumePass == 1) {
                assert(sync == 2 && accepted[0] == sizes[0] && accepted[1] == partialPrefix && accepted[2] == 0);
                Response reply{200, R"({"meeting":{"meeting_id":"generated-meeting"},"upload_session":{"session_id":"generated-upload","status":"uploading","accepted_bytes_by_track":{"manifest":)"};
                number(reply.body, sizes[0]);
                reply.body += ",\"media\":"; number(reply.body, partialPrefix);
                reply.body += R"(,"playback":0}},"conflict":{"state":"none"}})";
                return reply;
            }
            assert(sync == 1);
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
            assert(request.method == "GET" && ++ranges <= (partialResume ? 3U : 2U));
            if (ranges == (partialResume ? 3U : 2U)) { assert(accepted == sizes); return {200, R"({"missing_ranges_by_track":{}})"}; }
            Response reply{200, "{\"missing_ranges_by_track\":{"};
            for (std::size_t i = 0; i < names.size(); ++i) {
                if (i) reply.body += ',';
                reply.body += '"'; reply.body += names[i]; reply.body += "\":[";
                if (accepted[i] != sizes[i]) {
                    reply.body += "{\"start\":";
                    number(reply.body, accepted[i]);
                    reply.body += ",\"end\":"; number(reply.body, sizes[i]); reply.body += '}';
                }
                reply.body += ']';
            }
            reply.body += "}}";
            return reply;
        }
        if (request.path == "/api/v1/upload-sessions/generated-upload/finalize") {
            assert(request.method == "POST" && ++finalize == 1 && ranges == (partialResume ? 3U : 2U) && accepted == sizes);
            const auto body = request.bodyView(); assert(body);
            const auto fields = DesktopApiClient::jsonObjectFields(*body); assert(fields);
            assert(fields->at("manifest_sha256") == "\"" + hashes[0] + "\"");
            const auto tracks = DesktopApiClient::jsonArrayValues(fields->at("tracks")); assert(tracks && tracks->size() == 3);
            constexpr std::array<std::string_view,3> codecs{"json", "wav-pcm-s16le", "m4a-aac-lc"};
            constexpr std::array<unsigned,3> rates{1,16000,48000};
            const auto seconds = proof ? (proof->evidence().durationMs + 999) / 1000 : (partialResume ? 140 : 30);
            const std::array<std::uint64_t,3> durations{1,seconds,seconds};
            for (std::size_t i = 0; i < names.size(); ++i) {
                const auto track = DesktopApiClient::jsonObjectFields(tracks->at(i)); assert(track);
                assert(track->at("track_role") == "\"" + std::string(names[i]) + "\"");
                assert(track->at("sha256") == "\"" + hashes[i] + "\"");
                assert(track->at("byte_length") == std::to_string(sizes[i]));
                assert(track->at("codec") == "\"" + std::string(codecs[i]) + "\"");
                assert(track->at("sample_rate_hz") == std::to_string(rates[i]));
                assert(track->at("duration_seconds") == std::to_string(durations[i]) && track->at("channel_count") == "1");
            }
            if (schedulerAccountWire) ioCut.store(IoCut::pauseAfterFlush); // Hold the real result commit, not HTTP success.
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
        if (partialResume && resumePass == 0 && track == 1 && accepted[1] == partialPrefix) {
            assert(parts == 2 && accepted[0] == sizes[0] && accepted[2] == 0 && finalize == 0);
            ioCut.store(IoCut::pauseAfterFlush); // Persist the genuine failed result before restarting.
            return {503, "{}"}; // This request is deliberately NOT acknowledged.
        }
        // The server binds (track, part number) immutably. An acknowledged
        // part must not be reused for another range or sent again in this case.
        assert(acknowledgedParts.emplace(std::make_pair(track, *request.byteOffset / config.partSizeBytes),
            *request.byteOffset).second);
        if (track == 1 && !partialResume) {
            if (got == config.partSizeBytes) ++fullMediaParts;
            else { assert(got == sizes[1] % config.partSizeBytes); ++mediaTails; }
        }
        accepted[track] += got; ++parts;
        return ack(*request.byteOffset, got);
    };
    assert(std::string_view(item.sessionId) == session && std::string_view(item.ownerUserId) == account.userId &&
        std::string_view(item.ownerWorkspaceId) == account.workspaceId);
    if (schedulerAccountWire) {
        assert(!proof && sizes[1] > 256 * 1024 &&
            (partialResume ? sizes[1] == 4'480'044 : sizes[1] < config.partSizeBytes));
        const auto packageBefore = snapshot(root / session);
        const auto finalGeneration = partialResume ? 7ULL : 5ULL;
        const auto verify = [&](const NativeCapture& capture, bool retry = false) {
            const auto queue = NativeCaptureStorageTestPeer::projection(capture);
            assert(NativeCaptureStorageTestPeer::generation(capture) == (retry ? 5 : finalGeneration) && queue && queue->items().size() == 1);
            const auto& row = queue->items()[0];
            assert(row.localRecordingId == item.localRecordingId && row.directoryId == item.directoryId &&
                row.sessionId == item.sessionId && row.packageDirectory == item.packageDirectory &&
                row.ownerUserId == item.ownerUserId && row.ownerWorkspaceId == item.ownerWorkspaceId);
            assert(row.status == (retry ? UploadQueueStatus::retry : UploadQueueStatus::uploaded));
            assert(row.attempts == (partialResume ? 1U : 0U));
            assert(row.safeReason == (partialResume ? "transport_unavailable" : ""));
            assert(row.meetingId == "generated-meeting");
            assert(row.uploadSessionId == "generated-upload");
            assert(row.acceptedBytes == (retry ? std::array<std::uint64_t,3>{sizes[0],partialPrefix,0} : sizes));
        };
        for (resumePass = 0; resumePass < (partialResume ? 2U : 1U); ++resumePass) {
            { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
            if (partialResume) {
                assert(!uploadStageProbe.armed.load()); // Prior executor must have drained before reset.
                for (auto& reached : uploadStageProbe.reachedUs) reached.store(0);
                for (auto& calls : uploadStageProbe.nativeCalls) calls.store(0);
                for (auto& elapsed : uploadStageProbe.nativeNs) elapsed.store(0);
                uploadStageProbe.inspectionError.store(0); uploadStageProbe.inspectionNative.store(0);
                uploadStageProbe.transportStatus.store(0); uploadStageProbe.transportPresent.store(0);
                uploadStageProbe.originNs.store(std::chrono::duration_cast<std::chrono::nanoseconds>(
                    std::chrono::steady_clock::now().time_since_epoch()).count());
                uploadStageProbe.armed.store(true, std::memory_order_release);
            }
            const auto baseGeneration = 3 + 2 * resumePass;
            NativeCapture scheduled(root, {std::make_shared<GeneratedAec>(), true}, schedulerAccountWire, send);
            startAndAdopt(scheduled, baseGeneration);
            if (resumePass == 1) {
                verify(scheduled, true); // Read the durable partial result before authorizing any new network.
                assert(wireCalls.load() == 7 && snapshot(root / session) == packageBefore);
            }
            scheduled.setAuthSessionToken("generated-t116-session");
            assert(waitFor([&] { scheduled.pollUploads(); return scheduled.currentAccount().has_value(); }));
            assert(waitFor([&] {
                const auto ticket = NativeCaptureStorageTestPeer::workerTicket(scheduled);
                return ticket.kind == NativeCapture::QueueMutationKind::uploadPrepare &&
                    ticket.state == NativeCapture::QueueTicketState::committed;
            }));
            const auto prepare = NativeCaptureStorageTestPeer::workerTicket(scheduled);
            assert(prepare.baseGeneration == baseGeneration && prepare.targetGeneration == baseGeneration + 1 &&
                NativeCaptureStorageTestPeer::generation(scheduled) == baseGeneration &&
                wireCalls.load() == (resumePass ? 7U : 0U) && scheduled.uploadsBusy());
            scheduled.pollUploads(); // Only this adoption releases the real network flight.
            // The 140-second fixture includes full cold member hashes before
            // HTTP. This is a functional wait, not a ten-second speed claim.
            // Keep the smaller case and the whole-case CTest deadline unchanged.
            const bool resultHeld = waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; },
                std::chrono::seconds(partialResume ? 30 : 10));
            if (!resultHeld) {
                logQueueAdmission(scheduled, "scheduler_result_wait", resumePass);
                {
                    const auto work = NativeCaptureStorageTestPeer::storageWork(scheduled);
                    std::lock_guard<std::mutex> lock(work->mutex);
                    const auto& ticket = work->ticket;
                    const auto& flight = work->upload;
                    std::fprintf(stderr, "PROTECTED_SCHEDULER_WAIT pass=%u wire=%u used=%zu idle=%zu ticket_kind=%u ticket_state=%u base=%llu target=%llu error=%u native=%u flight=%u selected=%zu cancelled=%u done=%u released=%u\n",
                        resumePass, wireCalls.load(), CustodyOwnedMemory::usedBytes(), idleOwnedBytes,
                        static_cast<unsigned>(ticket.kind), static_cast<unsigned>(ticket.state),
                        static_cast<unsigned long long>(ticket.baseGeneration), static_cast<unsigned long long>(ticket.targetGeneration),
                        static_cast<unsigned>(ticket.error), ticket.nativeError, !!flight,
                        flight ? flight->selected.size() : 0, flight && flight->cancelled->load(),
                        flight && flight->done.load(), flight && flight->leaseReleased.load());
                    std::fflush(stderr);
                }
                if (partialResume) {
                    const auto now = std::chrono::duration_cast<std::chrono::nanoseconds>(
                        std::chrono::steady_clock::now().time_since_epoch()).count();
                    for (std::size_t stage = 0; stage < uploadStageProbe.reachedUs.size(); ++stage)
                        std::fprintf(stderr, "PROTECTED_UPLOAD_STAGE stage=%zu at_us=%lld observed_us=%lld\n", stage,
                            static_cast<long long>(uploadStageProbe.reachedUs[stage].load() - 1),
                            static_cast<long long>((now - uploadStageProbe.originNs.load()) / 1000));
                    std::fprintf(stderr, "PROTECTED_UPLOAD_STAGE inspection_error=%u inspection_native=%u transport_present=%u transport_status=%u\n",
                        uploadStageProbe.inspectionError.load(), uploadStageProbe.inspectionNative.load(),
                        uploadStageProbe.transportPresent.load(), uploadStageProbe.transportStatus.load());
                    // Live sequential observations of completed calls only;
                    // not atomic count/time pairs or all inspection work.
                    for (std::size_t native = 0; native < uploadStageProbe.nativeCalls.size(); ++native)
                        std::fprintf(stderr, "PROTECTED_INSPECTION_NATIVE index=%zu completed_calls=%llu completed_us=%llu\n", native,
                            static_cast<unsigned long long>(uploadStageProbe.nativeCalls[native].load()),
                            static_cast<unsigned long long>(uploadStageProbe.nativeNs[native].load() / 1000));
                    std::fflush(stderr);
                }
            }
            assert(resultHeld);
            const auto pending = NativeCaptureStorageTestPeer::workerTicket(scheduled);
            assert(pending.kind == NativeCapture::QueueMutationKind::uploadResult && pending.state == NativeCapture::QueueTicketState::pending &&
                pending.baseGeneration == baseGeneration + 1 && pending.targetGeneration == baseGeneration + 1 && scheduled.uploadsBusy());
            const auto priorStatus = resumePass ? UploadQueueStatus::retry : UploadQueueStatus::pending;
            assert(NativeCaptureStorageTestPeer::generation(scheduled) == baseGeneration + 1 &&
                NativeCaptureStorageTestPeer::projection(scheduled)->items()[0].status == priorStatus);
            assert(create == 1 && uploadSession == 1);
            if (partialResume) {
                assert(sync == resumePass + 1 && ranges == (resumePass ? 3U : 1U) &&
                    finalize == resumePass && parts == (resumePass ? 4U : 2U) &&
                    accepted == (resumePass ? sizes : std::array<std::uint64_t,3>{sizes[0],partialPrefix,0}) &&
                    wireCalls.load() == (resumePass ? 13U : 7U));
                std::fprintf(stderr, "PROTECTED_SCHEDULER_RESUME pass=%u result_flush_pending=pass media_prefix=4194304\n", resumePass);
            } else {
                assert(sync == 1 && ranges == 2 && finalize == 1 && parts == 3 && accepted == sizes && wireCalls.load() == 9);
                std::fputs("PROTECTED_SCHEDULER_SUCCESS http_complete_result_flush_pending_projection4=pass\n", stderr);
            }
            ioCut.store(IoCut::none);
            { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
            cutWake.notify_all();
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(scheduled); }));
            const auto result = NativeCaptureStorageTestPeer::workerTicket(scheduled);
            assert(result.kind == NativeCapture::QueueMutationKind::uploadResult &&
                result.state == NativeCapture::QueueTicketState::committed && result.error == CustodyFileError::none &&
                result.baseGeneration == baseGeneration + 1 && result.targetGeneration == baseGeneration + 2 && result.id != prepare.id);
            assert(NativeCaptureStorageTestPeer::generation(scheduled) == baseGeneration + 1 && scheduled.uploadsBusy() &&
                NativeCaptureStorageTestPeer::projection(scheduled)->items()[0].status == priorStatus);
            const auto committedEpoch = scheduled.authGeneration();
            if (lateLogout) {
                // The actual result is committed, but has not been adopted.
                // Logout at the earlier flush cut could still cancel publication.
                assert(result.epoch == committedEpoch);
                const auto staleProjection = NativeCaptureStorageTestPeer::projection(scheduled);
                scheduled.setAuthSessionToken({}, true);
                assert(scheduled.authGeneration() == committedEpoch + 1 && !scheduled.currentAccount() &&
                    scheduled.authSessionToken().empty() && wireCalls.load() == 9);
                assert(NativeCaptureStorageTestPeer::generation(scheduled) == baseGeneration + 1 &&
                    NativeCaptureStorageTestPeer::projection(scheduled) == staleProjection && scheduled.uploadsBusy());
                assert(!scheduled.openLocalPlayback(std::string_view(item.localRecordingId), 1, true));
                assert(!scheduled.requestProtectedManualSend(staleProjection, std::string_view(item.localRecordingId),
                    committedEpoch, false));
            }
            scheduled.pollUploads();
            verify(scheduled, partialResume && resumePass == 0);
            assert(waitFor([&] { scheduled.pollUploads(); return !scheduled.uploadsBusy() && scheduled.localQueueComplete(); }));
            if (lateLogout) {
                assert(!scheduled.currentAccount() && scheduled.authSessionToken().empty() &&
                    scheduled.authGeneration() == committedEpoch + 1 && wireCalls.load() == 9);
                assert(!scheduled.openLocalPlayback(std::string_view(item.localRecordingId), 1, true));
                assert(!scheduled.requestProtectedManualSend(NativeCaptureStorageTestPeer::projection(scheduled),
                    std::string_view(item.localRecordingId), scheduled.authGeneration(), false));
                std::fputs("PROTECTED_SCHEDULER_LATE_LOGOUT committed4_5_before_adoption_epoch_revoked_physical5_no_authority=pass\n", stderr);
            }
            scheduled.shutdown();
            assert(waitFor([&] { scheduled.pollUploads(); return scheduled.shutdownWorkDrained(); }));
            if (partialResume) uploadStageProbe.armed.store(false, std::memory_order_release);
        }
        assert(snapshot(root / session) == packageBefore);
        const auto committed = snapshot(root);
        {
            NativeCapture cold(root, {std::make_shared<GeneratedAec>(), true}, schedulerAccountWire, send);
            startAndAdopt(cold, finalGeneration);
            verify(cold);
            cold.setAuthSessionToken("generated-t116-session");
            assert(waitFor([&] {
                cold.pollUploads();
                return cold.currentAccount().has_value() && !NativeCaptureStorageTestPeer::recoveryIntentPending(cold) &&
                    !cold.uploadsBusy() && cold.localQueueComplete();
            }));
            verify(cold);
            assert(wireCalls.load() == (partialResume ? 13U : 9U)); // Authenticated uploaded row is not sent twice.
            cold.shutdown();
            assert(waitFor([&] { cold.pollUploads(); return cold.shutdownWorkDrained(); }));
        }
        assert(snapshot(root) == committed);
        assert(retained && !retainedOwner.expired() && retained->bodyView() &&
            retained->bodyView()->data() == retainedData && retained->bodyView()->size() == retainedLength &&
            sha256(*retained->bodyView()) == retainedHash);
        retained.reset(); assert(retainedOwner.expired()); retainedOwner.reset();
        std::fputs(lateLogout
            ? "PROTECTED_SCHEDULER_LATE_LOGOUT uploaded5_cold_original_auth_no_resend_wire9_idle_owners=pass audio=0 network=0\n"
            : partialResume
            ? "PROTECTED_SCHEDULER_RESUME partial_ack_retry5_cold_suffix4194304_uploaded7_authenticated_no_resend=pass part_config=4194304 audio=0 network=0\n"
            : "PROTECTED_SCHEDULER_SUCCESS prepare3_4_result4_5_adoption_uploaded_cold_authenticated_no_resend=pass part_config=4194304 body_under4MiB=1 audio=0 network=0\n", stderr);
        return;
    }
    assert(proof);
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
    assert(result->serverTruth->uploadSessionId == "generated-upload");
    assert(result->serverTruth->acceptedBytes == sizes && sync == 1 && create == 1 && uploadSession == 1 && finalize == 1 && parts >= 3);
    assert(retained && !retainedOwner.expired() && retained->bodyView() && retained->bodyView()->data() == retainedData);
    assert(retained->bodyView()->size() == retainedLength && sha256(*retained->bodyView()) == retainedHash);
    const auto charged = CustodyOwnedMemory::usedBytes();
    retained.reset(); // Transport and all original requests have already ended.
    assert(retainedOwner.expired() && charged >= CustodyOwnedMemory::usedBytes() + retainedLength);
    retainedOwner.reset(); // Release the separately charged control block too.
    assert(snapshot(root) == before); // Transport itself never writes a plaintext copy/ledger.
    std::fputs("PROTECTED_HTTP actual_transport_bytes=pass protected_result_adoption=pending\n", stderr);
    if (partSizeBytes != 64 * 1024) {
        assert(sizes[1] == 16'800'044 && fullMediaParts == sizes[1] / partSizeBytes && mediaTails == 1);
        std::fprintf(stderr, "PROTECTED_LARGE_PARTS part_bytes=%zu media_bytes=%llu full_parts=%u tail_bytes=%llu exact_wire=pass\n",
            partSizeBytes, static_cast<unsigned long long>(sizes[1]), fullMediaParts,
            static_cast<unsigned long long>(sizes[1] % partSizeBytes));
        return; // Old 64KiB fault corpus stays separate from these larger happy paths.
    }

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
        assert(snapshot(root) == before);
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
        assert(snapshot(root) == before);
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
        assert(snapshot(root) == before);
    }

    enum class Cut { cancel, invalidRange, rangesQuota, bodyQuota, badAck, allocation, afterAckAllocation, terminalAllocation, nativeRead };
    for (const auto cut : {Cut::cancel, Cut::invalidRange, Cut::rangesQuota, Cut::bodyQuota, Cut::badAck, Cut::allocation, Cut::afterAckAllocation
#if defined(_MSC_VER) && defined(_DEBUG)
        , Cut::terminalAllocation
#endif
        , Cut::nativeRead // Sticky reader failure: no subsequent use of this proof.
    }) {
        const bool afterAck = cut == Cut::afterAckAllocation || cut == Cut::terminalAllocation;
        if (cut == Cut::nativeRead) {
            assert(sizes[1] > 256 * 1024 && sizes[1] < 4 * 1024 * 1024);
            config.partSizeBytes = 4 * 1024 * 1024; // One media body needs multiple real logical reads.
            uploadReadCut = {};
            uploadReadCut.path = L"\\\\?\\" + (root / session / L".custody-v1" / L"media" / L"content.packed-v2").wstring();
        }
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
                if (cut == Cut::bodyQuota || cut == Cut::nativeRead) {
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
                (cut == Cut::bodyQuota || cut == Cut::badAck || cut == Cut::allocation || afterAck || cut == Cut::nativeRead));
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
            if (cut == Cut::nativeRead) {
                auto reply = ack(0, body->size());
                uploadReadCut.armed = true; // Preflight hashes finished; the transport next accepts this manifest ACK.
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
        const std::array<std::uint64_t,3> acceptedBeforeFailure{afterAck || cut == Cut::bodyQuota || cut == Cut::nativeRead ? sizes[0] : 0, 0, 0};
        assert((failed->serverTruth && std::string_view(failed->serverTruth->localRecordingId) == std::string_view(item.localRecordingId) &&
            failed->serverTruth->meetingExists && failed->serverTruth->uploadSessionExists &&
            !failed->serverTruth->finalized && failed->serverTruth->acceptedBytes == acceptedBeforeFailure));
        assert(missing == (afterAck ? 2U : 1U) && put == ((cut == Cut::bodyQuota || cut == Cut::badAck || cut == Cut::allocation || afterAck || cut == Cut::nativeRead) ? 1U : 0U));
        if (cut == Cut::nativeRead) {
            assert(!uploadReadCut.armed && uploadReadCut.dataHeaders == 2 && uploadReadCut.failures == 1 &&
                uploadReadCut.firstComplete && uploadReadCut.firstOffset != uploadReadCut.secondOffset);
            assert(failed->serverTruth->meetingId == "generated-meeting" && failed->serverTruth->uploadSessionId == "generated-upload");
            uploadReadCut.path.clear();
            std::fputs("PROTECTED_HTTP native_mid_read first_envelope_complete=1 failures=1 manifest_put=1 media_put=0 playback_put=0 finalize=0 retained_manifest_ack=1\n", stderr);
        }
        assert(bodyOwner.expired());
        bodyOwner.reset(); budget.reset();
        cancellation->store(false); // Completed fixture call only; never revive a native request.
        assert(snapshot(root) == before);
    }
    // Live readers legitimately replace the retained cache block here. The
    // exact idle charge is checked by main after this worker releases the proof.
    std::fputs("PROTECTED_HTTP cancel_range_quota_ack_allocation=pass\n", stderr);
    std::fputs("PROTECTED_HTTP after_ack_allocation_retains_progress=pass\n", stderr);
#if defined(_MSC_VER) && defined(_DEBUG)
    std::fputs("PROTECTED_HTTP preowned_terminal_no_late_allocation=pass\n", stderr);
#endif
}

void protectedLargeUploadParts() {
    auto worker = std::async(std::launch::async, [] {
        const auto started = std::chrono::steady_clock::now();
        const auto elapsed = [&] { return static_cast<long long>(std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - started).count()); };
        struct PhaseLogReset {
            bool previous = nativeFinalizePhaseLog.exchange(true);
            ~PhaseLogReset() noexcept { nativeFinalizePhaseLog.store(previous); }
        } phaseLogReset;
        const auto phase = [&](const char* stage) {
            const auto error = GetLastError();
            std::fprintf(stdout, "PROTECTED_LARGE_PARTS stage=%s elapsed_ms=%lld\n", stage, elapsed());
            std::fflush(stdout);
            SetLastError(error);
        };
        {
            testing::GeneratedProtectedRecording capture("generated-large-upload");
            std::fprintf(stderr, "PROTECTED_LARGE_PARTS stage=writer_open elapsed_ms=%lld\n", elapsed());
            std::fflush(stderr);
            capture.append(52'500);
            std::fprintf(stderr, "PROTECTED_LARGE_PARTS generated_frames=52500 stage=finalize elapsed_ms=%lld\n", elapsed());
            std::fflush(stderr);
            const auto sealed = capture.writer->finalize(ReasonCode::none, RecordingStopReason::interruption);
            std::fprintf(stderr, "PROTECTED_LARGE_PARTS stage=finalize_returned elapsed_ms=%lld normal=%u error=%u storage=%u native=%u\n",
                elapsed(), sealed.normalPackage() ? 1U : 0U, static_cast<unsigned>(sealed.error),
                static_cast<unsigned>(sealed.storageError), sealed.nativeError);
            std::fflush(stderr);
            assert(sealed.normalPackage() && sealed.durationMs == 525'000);
            phase("cold_pair_enter");
            auto pair = capture.coldPair(); assert(pair.ok());
            assert((*pair.value)->current().phase == CustodyPackagePhase::sealedNormal);
            phase("cold_pair_returned");
            phase("read_expected_enter");
            const auto expected = readProtectedUploadExpected(capture.paths.root, *pair.value, capture.cancel);
            assert(expected.bytes[1].size() == 16'800'044);
            phase("read_expected_returned");
            phase("inspect_enter");
            auto proof = LocalRecordingPackage::inspectProtected(capture.paths.root, *pair.value, capture.session, capture.cancel);
            assert(proof.ok() && (*proof.value)->evidence().integrity == PackageIntegrity::valid &&
                (*proof.value)->evidence().durationMs == 525'000);
            phase("inspect_returned");
            // A synthetic transport input, not evidence of capture-owner grant or queue publication.
            const DesktopAccountIdentity account{"11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"};
            ProtectedUploadQueueValue::Item row;
            row.localRecordingId = row.directoryId = row.sessionId = capture.session;
            const auto path = (capture.paths.root / capture.session).u8string();
            row.packageDirectory.assign(path.begin(), path.end());
            row.ownerUserId = account.userId; row.ownerWorkspaceId = account.workspaceId;
            for (const std::size_t partSize : {4U * 1024 * 1024, 16U * 1024 * 1024}) {
                phase(partSize == 4U * 1024 * 1024 ? "wire_4mib_enter" : "wire_16mib_enter");
                protectedUploadFromCold(capture.paths.root, capture.session, account, *proof.value, expected, capture.cancel, row, {}, partSize);
                phase(partSize == 4U * 1024 * 1024 ? "wire_4mib_returned" : "wire_16mib_returned");
            }
            phase("cleanup_enter");
        }
        phase("cleanup_returned");
    });
    worker.get(); // Every genuine native owner and generated file drains on this worker.
}

void protectedPlaybackBatches() {
    auto worker = std::async(std::launch::async, [] {
        for (const unsigned frames : {31U,32U,33U,1000U}) {
            testing::GeneratedProtectedRecording capture("generated-playback-batch");
            CanonicalAudioFrame frame;
            for (unsigned n=0; n<frames; ++n) {
                frame.ptsFrames = static_cast<std::int64_t>(n)*480;
                for (std::size_t at=0; at<480; ++at) frame.mixed[at] = generatedPlaybackValue(n,at);
                assert(capture.writer->append(frame));
            }
            playbackProbe = {}; playbackProbe.armed = true;
            const auto sealed = capture.writer->finalize();
            playbackProbe.armed = false;
            std::fprintf(stderr,"PLAYBACK_BATCH frames=%u reads=%u samples=%u last_bytes=%lu\n",
                frames,playbackProbe.reads,playbackProbe.samples,playbackProbe.lastRead);
            std::fflush(stderr);
            assert(sealed.normalPackage() && sealed.durationMs == frames*10);
            assert(playbackProbe.samples == frames && playbackProbe.reads == (frames+31)/32 &&
                playbackProbe.lastRead == ((frames-1)%32+1)*1920);
            auto pair = capture.coldPair(); assert(pair.ok());
            auto inspected = LocalRecordingPackage::inspectProtected(capture.paths.root,*pair.value,capture.session,capture.cancel);
            assert(inspected.ok() && inspected.value.value()->evidence().playback.decodedFrames);
        }
        for (const auto cut : {PlaybackCut::shortRead,PlaybackCut::cancel,PlaybackCut::output}) {
            testing::GeneratedProtectedRecording capture("generated-playback-batch-cut");
            for (unsigned n=0; n<33; ++n) {
                CanonicalAudioFrame frame; frame.ptsFrames = static_cast<std::int64_t>(n)*480;
                for (std::size_t at=0; at<480; ++at) frame.mixed[at] = generatedPlaybackValue(n,at);
                assert(capture.writer->append(frame));
            }
            playbackProbe = {}; playbackProbe.armed = true; playbackProbe.cut = cut;
            playbackProbe.cancellation = capture.cancel.get();
            const auto result = capture.writer->finalize();
            playbackProbe.armed = false;
            const auto expected = cut == PlaybackCut::shortRead ? STG_E_READFAULT :
                cut == PlaybackCut::cancel ? HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED) : E_ACCESSDENIED;
            std::fprintf(stderr,"PLAYBACK_BATCH fault=%u reads=%u samples=%u cuts=%u error=%u native=%u verified=%u retained=%u\n",
                static_cast<unsigned>(cut),playbackProbe.reads,playbackProbe.samples,playbackProbe.cutHits,
                static_cast<unsigned>(result.error),result.nativeError,result.semanticVerified ? 1U : 0U,result.trustedPrefixRetained ? 1U : 0U);
            std::fflush(stderr);
            const bool retained = cut != PlaybackCut::cancel;
            assert(!result.normalPackage() && !result.keepablePackage() &&
                result.semanticVerified == retained && result.trustedPrefixRetained == retained &&
                playbackProbe.reads == 1 && playbackProbe.cutHits == 1 &&
                playbackProbe.samples == (cut == PlaybackCut::shortRead ? 0U : 1U) &&
                result.nativeError == static_cast<std::uint32_t>(expected) &&
                result.error == (cut == PlaybackCut::shortRead ? V5WriterError::integrityFailed : V5WriterError::encodeFailed));
            std::fprintf(stderr,"PLAYBACK_BATCH cut=%u refused=1 exact_failure=1\n",static_cast<unsigned>(cut));
        }
    });
    worker.get();
}

void protectedStorageProfile() {
    auto worker = std::async(std::launch::async, [] {
        for (const bool active : {false,true}) {
            storageProfile = {}; storageProfile.active = active;
            unsigned called = 0;
            SetLastError(ERROR_ACCESS_DENIED);
            const auto result = measuredStorageCall(0, [&] {
                assert(GetLastError() == ERROR_ACCESS_DENIED); ++called;
                SetLastError(ERROR_READ_FAULT); return 17;
            });
            assert(result == 17 && called == 1 && GetLastError() == ERROR_READ_FAULT &&
                storageProfile.calls[0] == (active ? 1U : 0U));
        }
        for (const bool nativeLog : {false,true}) for (const bool active : {false,true}) for (const bool unwind : {false,true}) {
            nativeFinalizePhaseLog.store(nativeLog);
            storageProfile = {}; storageProfile.active = active; finalizeProfile = {};
            static thread_local unsigned called;
            static thread_local bool shouldThrow;
            called = 0; shouldThrow = unwind;
            SetLastError(ERROR_ACCESS_DENIED);
            bool caught = false;
            try {
                const auto result = finalizePhaseAdapterForTest([]() -> bool {
                    assert(GetLastError() == ERROR_ACCESS_DENIED); ++called;
                    SetLastError(ERROR_READ_FAULT);
                    if (shouldThrow) throw 29;
                    return false;
                });
                assert(!result && !unwind);
            } catch (int value) { assert(value == 29 && unwind); caught = true; }
            const auto& observed = finalizeProfile[0];
            assert(called == 1 && caught == unwind && GetLastError() == ERROR_READ_FAULT &&
                observed.entered == (active || nativeLog ? 1U : 0U) &&
                observed.returned == ((active || nativeLog) && !unwind ? 1U : 0U) &&
                observed.unwound == ((active || nativeLog) && unwind ? 1U : 0U));
        }
        nativeFinalizePhaseLog.store(false);
        std::fputs("FINALIZE_PROFILE adapter_selfcheck=pass\n",stderr);
        finalizeProfile = {};
        storageProfile = {}; storageProfile.active = true;
        auto before = std::chrono::steady_clock::now();
        const auto phase = [&](const char* name) {
            const auto now = std::chrono::steady_clock::now();
            std::fprintf(stderr, "STORAGE_PROFILE phase=%s thread_local=1 frames=1000 wall_us=%lld calls=",
                name, static_cast<long long>(std::chrono::duration_cast<std::chrono::microseconds>(now-before).count()));
            for (std::size_t i=0; i<4; ++i) std::fprintf(stderr, "%s%llu", i ? "," : "",
                static_cast<unsigned long long>(storageProfile.calls[i]));
            std::fputs(" native_us=",stderr);
            for (std::size_t i=0; i<4; ++i) std::fprintf(stderr, "%s%llu", i ? "," : "",
                static_cast<unsigned long long>(storageProfile.nanoseconds[i]/1000));
            std::fputc('\n',stderr); std::fflush(stderr);
            storageProfile.calls = {}; storageProfile.nanoseconds = {};
            before = std::chrono::steady_clock::now();
        };
        {
            testing::GeneratedProtectedRecording capture("generated-storage-profile");
            phase("open");
            capture.append(1000);
            phase("append");
            const auto sealed = capture.writer->finalize(ReasonCode::none, RecordingStopReason::interruption);
            assert(sealed.normalPackage() && sealed.durationMs == 10000);
            phase("finalize");
            // Disjoint top-level spans; WAV/AAC include their internal sealing/decoding.
            constexpr std::array<const char*,4> stages{"canonical_seal","wav","aac","inspection"};
            for (std::size_t stage=0; stage<stages.size(); ++stage) {
                const auto& observed = finalizeProfile[stage];
                assert(observed.entered == 1 && observed.returned == 1 && observed.unwound == 0);
                std::fprintf(stderr,"FINALIZE_PROFILE stage=%s entered=%u returned=%u unwound=%u wall_us=%llu calls=",
                    stages[stage],observed.entered,observed.returned,observed.unwound,
                    static_cast<unsigned long long>(observed.nanoseconds/1000));
                for (std::size_t i=0; i<4; ++i) std::fprintf(stderr,"%s%llu",i ? "," : "",
                    static_cast<unsigned long long>(observed.calls[i]));
                std::fputs(" native_us=",stderr);
                for (std::size_t i=0; i<4; ++i) std::fprintf(stderr,"%s%llu",i ? "," : "",
                    static_cast<unsigned long long>(observed.native[i]/1000));
                std::fputc('\n',stderr);
            }
            std::fflush(stderr);
        }
        phase("cleanup");
        storageProfile.active = false;
    });
    worker.get();
}

void assertStartOwnerBirth(const CustodyPackageValue& birth, std::string_view session, const CustodyContext& queue) {
    assert(birth.schema==2 && birth.generation==1 && birth.phase==CustodyPackagePhase::capturing &&
        birth.reason==ReasonCode::none && !birth.shortRecordingDiscarded && birth.refCount==1 &&
        std::string_view(birth.directory.data())==session && birth.context.role==CustodyRole::packageState &&
        birth.context.storeId==queue.storeId && birth.context.objectId!=CustodyId{} &&
        birth.context.objectId!=queue.objectId && birth.context.objectId!=birth.context.storeId);
    const auto& ref=birth.refs[0];
    assert(ref.role==CustodyRole::canonical && ref.objectId!=CustodyId{} && ref.objectId!=birth.context.objectId &&
        ref.packed && !ref.sealed && ref.containerId && *ref.containerId!=CustodyId{} &&
        !ref.generation && !ref.length && !ref.sha256 && !ref.committedExtent && !ref.rootRef);
}
void adoptedStartOwnerCrashProof(const ProtectedCustodyRecordingPackage* born) {
    auto& p=*startOwnerCrash;
    const bool packageCut=p.cut>=StartOwnerCrashCut::packageBeforeIndex0;
    const bool semanticAck=p.cut==StartOwnerCrashCut::packageAfterSemanticAck;
    assert(p.nativeCalls.load()==1 && p.nativeReturns.load()==1 && p.nativeSucceeded.load() &&
        p.beforeFactoryObservations.load()==1 && bool(born)==semanticAck &&
        GetCurrentThreadId()==NativeCaptureStorageTestPeer::storageThread(*p.capture));
    const auto work=NativeCaptureStorageTestPeer::storageWork(*p.capture); assert(work);
    {
        std::lock_guard<std::mutex> lock(work->mutex);
        assert(work->ready && work->adopted && work->generation==2 && work->inFlight && work->recording &&
            !work->commandReady && work->command==decltype(work->command)::prepareRecording &&
            !work->resultReady && !work->resultAdopted && !work->resultValue && !work->stop && !work->queueFailed && !work->terminal &&
            !work->reconciliationPending && !work->commandReconciliation && !work->physicalReadback &&
            work->ticket.id && work->ticket.kind==NativeCapture::QueueMutationKind::recording &&
            work->ticket.baseGeneration==1 && work->ticket.targetGeneration==2 && work->ticket.changed &&
            work->ticket.state==NativeCapture::QueueTicketState::committed &&
            work->ticket.error==CustodyFileError::none && !work->ticket.nativeError &&
            work->ticket.context.storeId==work->context.storeId && work->ticket.context.objectId==work->context.objectId &&
            work->ticket.context.role==CustodyRole::queue);
        // pollStorageStartup publishes both projection and last ticket under this mutex.
        const auto projected=NativeCaptureStorageTestPeer::projection(*p.capture);
        const auto ticket=NativeCaptureStorageTestPeer::ticket(*p.capture);
        assert(projected && projected->items().size()==1 && ticket && ticket->id==work->ticket.id &&
            ticket->epoch==work->ticket.epoch && ticket->state==NativeCapture::QueueTicketState::committed &&
            ticket->baseGeneration==1 && ticket->targetGeneration==2);
        std::lock_guard<std::mutex> recordingLock(work->recording->mutex);
        const auto& recording=*work->recording;
        assert(recording.reservation==projected && !recording.writer && !recording.prepared && !recording.started &&
            !recording.finalizing && !recording.terminal && !recording.frames.load() && !recording.cancellation->load() &&
            recording.ownerKnown && recording.user.empty() && recording.workspace.empty() &&
            work->ticket.epoch==recording.epoch && std::string_view(recording.session)==p.package.filename().u8string());
        const auto& row=projected->items().front();
        assert(row.localRecordingId==recording.session && row.directoryId==row.localRecordingId && row.sessionId==row.localRecordingId &&
            std::string_view(row.packageDirectory)==p.package.u8string() && row.ownerUserId.empty() && row.ownerWorkspaceId.empty() &&
            row.status==UploadQueueStatus::quarantined && row.safeReason=="capture_prepared" && !hasUploadServerIdentity(row) && !row.attempts);
        if (born) {
            assert(born->directory()==std::string_view(recording.session));
            assertStartOwnerBirth(born->current(),recording.session,work->context);
        }
    }
    const unsigned first=p.cut==StartOwnerCrashCut::packageBeforeIndex1 || semanticAck ? 1U : 0U;
    const unsigned second=semanticAck ? 1U : 0U;
    assert(p.packageCalls[0].load()==first && p.packageReturns[0].load()==first && p.packageSucceeded[0].load()==bool(first) &&
        p.packageCalls[1].load()==second && p.packageReturns[1].load()==second && p.packageSucceeded[1].load()==bool(second));
    assert(!p.devices->load() && !p.network->load() && std::filesystem::exists(p.package)==packageCut);
    if (packageCut) {
        const auto state=p.package/L".custody-v1";
        assert(std::filesystem::is_regular_file(state/L"package-state"/L"id.bin") &&
            std::filesystem::is_regular_file(state/L"canonical"/L"id.bin") &&
            !std::filesystem::exists(state/L"canonical"/L"content.packed-v2") &&
            std::filesystem::exists(state/L"package-state"/L"index.0")==bool(first) &&
            std::filesystem::exists(state/L"package-state"/L"index.1")==bool(second));
    }
    *p.progress << startOwnerCrashReceipts[static_cast<unsigned>(p.cut)] << '\n';
    p.progress->flush(); assert(p.progress->good());
}
void holdStartStopBeforeEos(HANDLE file) {
    const auto incoming=GetLastError();
    auto& p=*startOwnerCrash;
    if (NativeCaptureStorageTestPeer::writtenFrames(*p.capture)==p.frames-1 && !p.stopHoldThread.load()) {
        wchar_t path[32768]{};
        const auto size=GetFinalPathNameByHandleW(file,path,32768,FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);
        assert(size && size<32768);
        DWORD absent=0;
        if (std::wstring_view(path,size)==p.stopCanonicalPath &&
            p.stopHoldThread.compare_exchange_strong(absent,GetCurrentThreadId())) {
            SetLastError(incoming);
            pauseAtCut(); // Existing hold, inside the real canonical checkWrite guard on the dispatcher.
        }
    }
    SetLastError(incoming);
}
void stopBeforeEosCrashProof() {
    auto& p=*startOwnerCrash;
    { std::lock_guard<std::mutex> lock(cutMutex); assert(cutReached && !cutReleased); }
    assert(CaptureSessionTestPeer::stopBeforeEosHeld(NativeCaptureStorageTestPeer::controller(*p.capture),p.stopHoldThread.load()));
    assert(p.capture->indicator().state==SessionState::stopping && p.capture->notificationCard().history().empty() &&
        !p.phase0Observations.load() && !p.beforeFactoryObservations.load() && !p.nativeCalls.load() &&
        !p.nativeReturns.load() && !p.nativeSucceeded.load() && p.devices->load()==2 && !p.network->load() &&
        !p.notices.load() && p.capture->authGeneration()==p.epoch);
    const auto work=NativeCaptureStorageTestPeer::storageWork(*p.capture); assert(work);
    {
        std::lock_guard<std::mutex> lock(work->mutex);
        assert(work->ready && work->adopted && work->generation==2 && work->recording && !work->inFlight &&
            !work->commandReady && !work->resultReady && !work->resultAdopted && !work->stop && !work->terminal &&
            !work->queueFailed && !work->commandReconciliation && !work->reconciliationPending && !work->physicalReadback &&
            work->ticket.id==p.startTicket && work->ticket.kind==NativeCapture::QueueMutationKind::recording &&
            work->ticket.epoch==p.epoch && work->ticket.state==NativeCapture::QueueTicketState::committed &&
            work->ticket.baseGeneration==1 && work->ticket.targetGeneration==2 && !work->ticket.nativeError &&
            work->ticket.error==CustodyFileError::none && NativeCaptureStorageTestPeer::projection(*p.capture)==p.reservation);
        std::lock_guard<std::mutex> recordingLock(work->recording->mutex);
        const auto& recording=*work->recording;
        assert(recording.reservation==p.reservation && recording.started && recording.prepared && !recording.finalizing &&
            !recording.terminal && recording.writer && recording.timeline && recording.processor && recording.activeLease &&
            recording.frames.load()==p.frames-1 && recording.writer->frameCount()==p.frames-1 &&
            recording.epoch==p.epoch && recording.ownerKnown && recording.user.empty() && recording.workspace.empty() &&
            !recording.cancellation->load() && recording.failure==ReasonCode::none && !recording.result.savedLocal &&
            !recording.result.shortRecordingDiscarded);
        const auto& row=p.reservation->items().front();
        assert(std::string_view(row.localRecordingId)==p.package.filename().u8string() && row.directoryId==row.localRecordingId &&
            row.sessionId==row.localRecordingId && std::string_view(row.packageDirectory)==p.package.u8string() &&
            row.ownerUserId.empty() && row.ownerWorkspaceId.empty() && row.status==UploadQueueStatus::quarantined &&
            row.safeReason=="capture_prepared" && !hasUploadServerIdentity(row) && !row.attempts);
        const auto package=recording.writer->package();
        assert(package && package->directory()==std::string_view(recording.session) &&
            package->current().phase==CustodyPackagePhase::capturing && package->current().generation==1);
    }
    // The hundred-frame fixture has not filled the 256KiB automatic checkpoint.
    // Dirty RAM is not a durable complete480 prefix; byte identity must survive Stop/death.
    assert(p.stopCanonicalHash.size()==64 && sha256File(p.stopCanonicalPath)==p.stopCanonicalHash);
    *p.progress << startOwnerCrashReceipts[static_cast<unsigned>(p.cut)] << '\n'
                << "canonical_sha256=" << p.stopCanonicalHash << '\n';
    p.progress->flush(); assert(p.progress->good());
}
void lifecycleStartOwnerCrashProof() {
    auto& p=*startOwnerCrash;
    const bool eos=p.cut==StartOwnerCrashCut::afterEosBeforeSeal;
    const bool shortReadback=p.cut==StartOwnerCrashCut::shortAfterRetirementReadback;
    const bool preOs=p.cut==StartOwnerCrashCut::shortBeforeRecycle;
    const bool normalAdopted=p.cut==StartOwnerCrashCut::normalAfterFinishAdoption;
    const bool readback=p.cut==StartOwnerCrashCut::afterFinishReadback || shortReadback;
    const bool removed=p.cut==StartOwnerCrashCut::shortAfterRecycle;
    const bool adopted=removed || preOs || normalAdopted;
    const bool shortStop=removed || shortReadback || preOs;
    // The child publishes this only after its one post-EOS health poll returns;
    // no UI polling races the callback's notification/indicator observations.
    assert(waitFor([&] { return p.stopReturned.load(std::memory_order_acquire); }));
    assert(p.capture->indicator().state==SessionState::finalizing && p.capture->notificationCard().history().empty());
    assert(p.phase0Observations.load()==1 && p.beforeFactoryObservations.load()==0 &&
        p.nativeCalls.load()==(readback || adopted ? 1U : 0U) &&
        p.nativeReturns.load()==(readback || adopted ? 1U : 0U) && p.nativeSucceeded.load()==(readback || adopted) &&
        p.devices->load()==2 && !p.network->load() && !p.notices.load() && p.epoch==p.capture->authGeneration());
    const auto& controller=NativeCaptureStorageTestPeer::controller(*p.capture);
    assert(CaptureSessionTestPeer::completed(controller) && CaptureSessionTestPeer::bothEndsProcessed(controller));
    const auto work=NativeCaptureStorageTestPeer::storageWork(*p.capture); assert(work);
    {
        std::lock_guard<std::mutex> lock(work->mutex);
        assert(work->ready && work->adopted && work->generation==(adopted ? 3U : 2U) && work->inFlight==!normalAdopted &&
            bool(work->recording)==!normalAdopted &&
            !work->commandReady && work->command==decltype(work->command)::finalizeRecording && !work->stop && !work->queueFailed &&
            !work->terminal && !work->commandReconciliation && !work->reconciliationPending && !work->physicalReadback &&
            work->ticket.id && work->ticket.id!=p.startTicket && work->ticket.kind==NativeCapture::QueueMutationKind::recording &&
            work->ticket.epoch==p.epoch && work->ticket.baseGeneration==2 &&
            work->ticket.context.storeId==work->context.storeId && work->ticket.context.objectId==work->context.objectId &&
            work->ticket.context.role==CustodyRole::queue && work->ticket.error==CustodyFileError::none && !work->ticket.nativeError &&
            !work->resultAdopted && work->resultReady==readback);
        const auto projected=NativeCaptureStorageTestPeer::projection(*p.capture);
        assert(p.reservation && p.reservation->items().size()==1 && projected &&
            (adopted ? projected!=p.reservation && projected->items().size()==(shortStop ? 0U : 1U) : projected==p.reservation));
        const auto& row=p.reservation->items().front();
        assert(std::string_view(row.localRecordingId)==p.package.filename().u8string() && row.directoryId==row.localRecordingId &&
            row.sessionId==row.localRecordingId && std::string_view(row.packageDirectory)==p.package.u8string() &&
            row.ownerUserId.empty() && row.ownerWorkspaceId.empty() && row.status==UploadQueueStatus::quarantined &&
            row.safeReason=="capture_prepared" && !hasUploadServerIdentity(row) && !row.attempts);
        if (readback || adopted) {
            assert(work->ticket.changed && work->ticket.state==NativeCapture::QueueTicketState::committed && work->ticket.targetGeneration==3);
            if (readback) assert(work->resultValue && work->resultValue->items().size()==(shortReadback ? 0U : 1U));
            if ((readback && !shortReadback) || normalAdopted) {
                const auto& final=(normalAdopted ? projected : work->resultValue)->items().front();
                assert(final.localRecordingId==row.localRecordingId && final.directoryId==row.directoryId && final.sessionId==row.sessionId &&
                    final.packageDirectory==row.packageDirectory && final.ownerUserId==row.ownerUserId && final.ownerWorkspaceId==row.ownerWorkspaceId &&
                    final.status==row.status && final.safeReason==row.safeReason && !hasUploadServerIdentity(final) && !final.attempts);
            }
            if (adopted) {
                assert(!work->resultValue);
                const auto adoptedTicket=NativeCaptureStorageTestPeer::ticket(*p.capture);
                assert(adoptedTicket && adoptedTicket->id==work->ticket.id && adoptedTicket->epoch==p.epoch &&
                    adoptedTicket->state==NativeCapture::QueueTicketState::committed &&
                    adoptedTicket->baseGeneration==2 && adoptedTicket->targetGeneration==3);
            }
        } else assert(!work->resultValue && work->ticket.state==NativeCapture::QueueTicketState::pending && work->ticket.targetGeneration==2);
        const auto retained=normalAdopted ? NativeCaptureStorageTestPeer::recordingWork(*p.capture) : work->recording; assert(retained);
        std::lock_guard<std::mutex> recordingLock(retained->mutex);
        const auto& recording=*retained;
        assert(recording.reservation==p.reservation && recording.started && recording.prepared && recording.finalizing && recording.terminal==normalAdopted &&
            recording.frames.load()==p.frames && recording.epoch==p.epoch && recording.ownerKnown &&
            recording.user.empty() && recording.workspace.empty() && std::string_view(recording.session)==row.sessionId &&
            !recording.cancellation->load() && recording.failure==ReasonCode::none && recording.result.savedLocal==normalAdopted &&
            !recording.result.shortRecordingDiscarded &&
            recording.stopReason==(shortStop ? RecordingStopReason::userRequested : RecordingStopReason::interruption));
        if (eos) {
            assert(recording.writer && recording.timeline && recording.processor &&
                GetCurrentThreadId()!=NativeCaptureStorageTestPeer::storageThread(*p.capture));
            const auto package=recording.writer->package();
            assert(package && package->directory()==std::string_view(recording.session) &&
                package->current().phase==CustodyPackagePhase::finalizing && package->current().generation==2);
        } else {
            assert(!recording.writer && !recording.timeline && !recording.processor && recording.processedFrames==p.frames);
            if (!readback && !normalAdopted) assert(GetCurrentThreadId()==NativeCaptureStorageTestPeer::storageThread(*p.capture));
            if (normalAdopted) assert(!recording.activeLease && recording.result.reason==ReasonCode::none &&
                GetCurrentThreadId()!=NativeCaptureStorageTestPeer::storageThread(*p.capture));
        }
    }
    assert(std::filesystem::exists(p.package)==!removed);
    if (!removed) assert(std::filesystem::is_regular_file(p.package/L".custody-v1"/L"canonical"/L"content.packed-v2"));
    if (removed) assert(nativeShortAttempts.load()==1 && nativeShortEffects.load()==1);
    if (p.cut>=StartOwnerCrashCut::shortAfterRetirementReadback) {
        assert(p.finalPackageSnapshot && !p.finalPackageSnapshot->empty() && snapshot(p.package)==*p.finalPackageSnapshot &&
            !nativeShortAttempts.load() && !nativeShortEffects.load() && !p.capture->finalization().savedLocal &&
            !p.capture->finalization().shortRecordingDiscarded);
        if (preOs) {
            assert(p.preOsDirectory);
            const auto directory=reinterpret_cast<HANDLE>(p.preOsDirectory);
            wchar_t path[32768]{};
            const auto size=GetFinalPathNameByHandleW(directory,path,32768,FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);
            FILE_ID_INFO identity{}; FILE_ATTRIBUTE_TAG_INFO attributes{};
            assert(size && size<32768 && std::wstring_view(path,size)==L"\\\\?\\"+p.package.native() &&
                GetFileInformationByHandleEx(directory,FileIdInfo,&identity,sizeof(identity)) &&
                GetFileInformationByHandleEx(directory,FileAttributeTagInfo,&attributes,sizeof(attributes)) &&
                (attributes.FileAttributes&FILE_ATTRIBUTE_DIRECTORY) && !(attributes.FileAttributes&FILE_ATTRIBUTE_REPARSE_POINT));
        }
    }
    *p.progress << startOwnerCrashReceipts[static_cast<unsigned>(p.cut)] << '\n';
    p.progress->flush(); assert(p.progress->good());
}
void startOwnerCrashProof(const ProtectedCustodyRecordingPackage* born) {
    assert(startOwnerCrash); auto& p=*startOwnerCrash;
    if (p.cut==StartOwnerCrashCut::stopBeforeEos) { assert(!born); stopBeforeEosCrashProof(); return; }
    if (p.cut>=StartOwnerCrashCut::afterEosBeforeSeal) { assert(!born); lifecycleStartOwnerCrashProof(); return; }
    if (p.cut>=StartOwnerCrashCut::afterAdoption) { adoptedStartOwnerCrashProof(born); return; }
    assert(!born);
    const bool readback=p.cut==StartOwnerCrashCut::afterReadback;
    const bool before=p.cut==StartOwnerCrashCut::beforeRename;
    assert(p.nativeCalls.load()==(before ? 0U : 1U) && p.nativeReturns.load()==(before ? 0U : 1U) &&
        p.nativeSucceeded.load()==!before);
    const auto work=NativeCaptureStorageTestPeer::storageWork(*p.capture); assert(work);
    {
        std::lock_guard<std::mutex> lock(work->mutex);
        assert(work->ready && work->adopted && work->generation==1 && work->inFlight && work->recording &&
            !work->commandReady && work->command==decltype(work->command)::prepareRecording &&
            !work->resultAdopted && !work->stop && !work->queueFailed && !work->terminal &&
            !work->reconciliationPending && !work->commandReconciliation && !work->physicalReadback &&
            work->ticket.id && work->ticket.kind==NativeCapture::QueueMutationKind::recording &&
            work->ticket.baseGeneration==1 && work->ticket.context.storeId==work->context.storeId &&
            work->ticket.context.objectId==work->context.objectId && work->ticket.context.role==CustodyRole::queue);
        std::lock_guard<std::mutex> recordingLock(work->recording->mutex);
        const auto& recording=*work->recording;
        assert(!recording.writer && !recording.prepared && !recording.started && !recording.finalizing && !recording.terminal &&
            !recording.frames.load() && !recording.cancellation->load() && recording.ownerKnown &&
            recording.user.empty() && recording.workspace.empty() && work->ticket.epoch==recording.epoch &&
            std::string_view(recording.session)==p.package.filename().u8string());
        if (readback) {
            assert(work->resultReady && work->ticket.changed && work->ticket.state==NativeCapture::QueueTicketState::committed &&
                work->ticket.targetGeneration==2 && work->ticket.error==CustodyFileError::none && !work->ticket.nativeError &&
                work->resultValue && work->resultValue->items().size()==1);
            const auto& row=work->resultValue->items().front();
            assert(row.localRecordingId==recording.session && row.directoryId==row.localRecordingId && row.sessionId==row.localRecordingId &&
                std::string_view(row.packageDirectory)==p.package.u8string() && row.ownerUserId.empty() && row.ownerWorkspaceId.empty() &&
                row.status==UploadQueueStatus::quarantined && row.safeReason=="capture_prepared" && !hasUploadServerIdentity(row) && !row.attempts);
        } else {
            assert(!work->resultReady && !work->resultValue && work->ticket.state==NativeCapture::QueueTicketState::pending &&
                work->ticket.targetGeneration==1);
        }
    }
    const auto projected=NativeCaptureStorageTestPeer::projection(*p.capture);
    assert(projected && projected->items().empty() && !p.devices->load() && !p.network->load() &&
        !std::filesystem::exists(p.package));
    *p.progress << startOwnerCrashReceipts[static_cast<unsigned>(p.cut)] << '\n';
    p.progress->flush(); assert(p.progress->good());
}
[[noreturn]] void terminateStartOwnerCrash(const ProtectedCustodyRecordingPackage* born) {
    startOwnerCrashProof(born);
    std::fprintf(stderr,"START_OWNER_CRASH cut=%ls destructors=0\n",startOwnerCrashArguments[static_cast<unsigned>(startOwnerCrash->cut)].data());
    std::fflush(stderr);
    assert(TerminateProcess(GetCurrentProcess(),88));
    std::abort();
}
void observeStartBeforeFactory() noexcept {
    const auto incoming=GetLastError();
    if (startOwnerCrashArmed.load(std::memory_order_acquire) && startOwnerCrash->cut>=StartOwnerCrashCut::afterAdoption) {
        assert(startOwnerCrash->beforeFactoryObservations.fetch_add(1)==0);
        if (startOwnerCrash->cut==StartOwnerCrashCut::afterAdoption) {
            assert(startOwnerCrashArmed.exchange(false));
            terminateStartOwnerCrash();
        }
    }
    SetLastError(incoming);
}
void observeStartFinalizePhase(unsigned stage) noexcept {
    const auto incoming=GetLastError();
    if (stage==0 && startOwnerCrashArmed.load(std::memory_order_acquire) && startOwnerCrash->cut>=StartOwnerCrashCut::afterEosBeforeSeal) {
        assert(startOwnerCrash->phase0Observations.fetch_add(1)==0);
        if (startOwnerCrash->cut==StartOwnerCrashCut::afterEosBeforeSeal) {
            assert(startOwnerCrashArmed.exchange(false));
            terminateStartOwnerCrash();
        }
    }
    SetLastError(incoming);
}
int protectedStartOwnerCrashChild(const std::filesystem::path& root, const std::filesystem::path& progressPath, StartOwnerCrashCut cut) {
    // Accept only the fresh sibling paths emitted by this executable's Fixture.
    const auto spelling=root.native();
    if (spelling.size()<3 || !((spelling[0]>=L'A' && spelling[0]<=L'Z') || (spelling[0]>=L'a' && spelling[0]<=L'z')) ||
        spelling[1]!=L':' || spelling[2]!=L'\\' || root!=root.lexically_normal()) return 89;
    const auto parent=root.parent_path();
    const auto name=parent.filename().u8string();
    constexpr std::string_view prefix="graf-storage-integration-{";
    auto id=name.size()==prefix.size()+37 ? name.substr(prefix.size(),36) : std::string{};
    std::transform(id.begin(),id.end(),id.begin(),[](char c) { return c>='A' && c<='F' ? static_cast<char>(c+'a'-'A') : c; });
    wchar_t temporary[32768]{}, actual[32768]{};
    const auto n=GetTempPathW(32768,temporary);
    if (!n || n>=32768) return 89;
    const auto actualLength=GetLongPathNameW(temporary,actual,32768);
    if (!actualLength || actualLength>=32768 ||
        name.size()!=prefix.size()+37 || name.substr(0,prefix.size())!=prefix || name.back()!='}' ||
        !DesktopApiClient::accountId(id) ||
        root != std::filesystem::path(actual)/parent.filename()/L"recordings" ||
        progressPath != parent/L"start-owner-crash-progress" || !std::filesystem::is_directory(parent) ||
        std::filesystem::exists(root) || !std::filesystem::is_regular_file(progressPath) ||
        std::filesystem::file_size(progressPath)!=19) return 89;
    const auto parentAttributes=GetFileAttributesW(parent.c_str()), progressAttributes=GetFileAttributesW(progressPath.c_str());
    if (parentAttributes==INVALID_FILE_ATTRIBUTES || progressAttributes==INVALID_FILE_ATTRIBUTES ||
        (parentAttributes & FILE_ATTRIBUTE_REPARSE_POINT) || (progressAttributes & FILE_ATTRIBUTE_REPARSE_POINT)) return 89;
    { std::ifstream input(progressPath); std::string line; if (!std::getline(input,line) || line!="START_OWNER_PARENT") return 89; }
    std::ofstream progress(progressPath,std::ios::app); assert(progress.is_open());
    std::atomic<unsigned> devices{0}, network{0};
    StartOwnerCrashProof proof; proof.cut=cut;
    // Proof/progress outlive capture even on the missing-event return path.
    NativeCapture capture(root,{std::make_shared<GeneratedAec>(),true},
        [&network](const auto&,const auto&) -> DesktopHttpTransport::UploadResponse { ++network; return {503,"{}"}; });
    startAndAdopt(capture,1);
    capture.setAuthSessionToken({},true);
    const auto session=capture.sessionId(); assert(DesktopApiClient::accountId(session));
    proof.capture=&capture; proof.devices=&devices; proof.network=&network;
    proof.progress=&progress; proof.package=root/session;
    const auto device=[&devices](const std::atomic_bool&,std::atomic_bool&,const CaptureBatchCallback&) {
        ++devices; assert(false && "start_crash_must_not_launch_devices");
    };
    CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(capture),device,device);
    const auto initial=NativeCaptureStorageTestPeer::projection(capture);
    assert(initial && initial->items().empty() && !std::filesystem::exists(proof.package));
    progress << "session=" << session << '\n'; progress.flush(); assert(progress.good());
    proof.queueDirectory=L"\\\\?\\"+(root/L".custody-v1"/L"queue").native();
    proof.packageStateDirectory=L"\\\\?\\"+(proof.package/L".custody-v1"/L"package-state").native();
    startOwnerCrash=&proof;
    ReadinessInputs hardware;
    hardware.microphonePermissionGranted=hardware.microphoneEndpointReady=hardware.renderEndpointReady=
        hardware.formatNormalizationReady=hardware.aecReady=hardware.aacEncoderReady=true;
    if (cut>=StartOwnerCrashCut::afterEosBeforeSeal) return protectedStartOwnerLifecycleChild(capture,proof,hardware);
    startOwnerCrashArmed.store(true,std::memory_order_release);
    assert(NativeCaptureStorageTestPeer::beginPending(capture,hardware).accepted());
    const bool ready=waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); },std::chrono::seconds(30));
    if (cut>=StartOwnerCrashCut::afterAdoption && ready) {
        NativeCaptureStorageTestPeer::pollStorage(capture); // One real command adoption; no subsequent UI/device polling.
        const auto work=NativeCaptureStorageTestPeer::storageWork(capture);
        (void)waitFor([&] {
            std::lock_guard<std::mutex> lock(work->mutex);
            if (work->terminal || work->queueFailed || !work->inFlight) return true;
            std::lock_guard<std::mutex> recordingLock(work->recording->mutex);
            return work->recording->prepared || work->recording->terminal;
        },std::chrono::seconds(30));
    }
    startOwnerCrashArmed.store(false);
    if (cut==StartOwnerCrashCut::afterReadback && ready) {
        // No poll/adoption/stop: the worker is waiting with the real commit retained.
        startOwnerCrashProof();
        std::fputs("START_OWNER_CRASH after_readback=1 committed=1 adopted=0 native_calls=1 native_returns=1 destructors=0\n",stderr);
        std::fflush(stderr);
        assert(TerminateProcess(GetCurrentProcess(),88));
        std::abort();
    }
    return 89; // A returned result for a native cut, or a missing event, is failure.
}
void protectedStartOwnerProcessDeath(bool lifecycleOnly=false) {
    const auto baseline=CustodyOwnedMemory::usedBytes();
    constexpr std::array<std::uint64_t,15> generations{1,2,2,2,2,2,2,2,2,3,3,2,3,3,3};
    constexpr std::array<std::size_t,15> rows{0,1,1,1,1,1,1,1,1,1,0,1,0,0,1};
    const std::size_t firstCut=lifecycleOnly ? 7U : 0U, lastCut=lifecycleOnly ? startOwnerCrashArguments.size() : 7U;
    for (std::size_t index=firstCut;index<lastCut;++index) {
        {
            Fixture fixture;
            const auto progress=fixture.parent/L"start-owner-crash-progress";
            assert(!std::filesystem::exists(progress) && !std::filesystem::exists(fixture.root));
            { std::ofstream output(progress,std::ios::binary); output << "START_OWNER_PARENT\n"; output.flush(); assert(output.good()); }
            wchar_t executable[32768]{}; const auto n=GetModuleFileNameW(nullptr,executable,32768); assert(n && n<32768);
            std::wstring command=L"\""+std::wstring(executable,n)+L"\" --protected-start-owner-crash \""+
                fixture.root.wstring()+L"\" \""+progress.wstring()+L"\" "+std::wstring(startOwnerCrashArguments[index]);
            STARTUPINFOW startup{}; startup.cb=sizeof(startup); PROCESS_INFORMATION child{};
            assert(CreateProcessW(executable,command.data(),nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,nullptr,&startup,&child));
            assert(CloseHandle(child.hThread));
            const auto wait=WaitForSingleObject(child.hProcess,60000);
            auto terminal=wait;
            if (wait!=WAIT_OBJECT_0) { TerminateProcess(child.hProcess,90); terminal=WaitForSingleObject(child.hProcess,10000); }
            DWORD exit=0; assert(GetExitCodeProcess(child.hProcess,&exit)); assert(CloseHandle(child.hProcess));
            std::fprintf(stderr,"START_OWNER_CHILD cut=%ls wait=%lu terminal=%lu exit=%lu\n",startOwnerCrashArguments[index].data(),wait,terminal,exit); std::fflush(stderr);
            assert(wait==WAIT_OBJECT_0 && terminal==WAIT_OBJECT_0 && exit==88 && "actual_start_queue_process_death_required");
            assert(std::filesystem::file_size(progress)<512);
            std::ifstream input(progress); std::string first,sessionLine,cut,extra;
            assert(std::getline(input,first) && first=="START_OWNER_PARENT" && std::getline(input,sessionLine) &&
                sessionLine.substr(0,8)=="session=" && std::getline(input,cut) &&
                cut==startOwnerCrashReceipts[index]);
            std::string canonicalHash;
            if (static_cast<StartOwnerCrashCut>(index)==StartOwnerCrashCut::stopBeforeEos) {
                assert(std::getline(input,extra) && extra.substr(0,17)=="canonical_sha256=");
                canonicalHash=extra.substr(17);
                assert(canonicalHash.size()==64 && std::all_of(canonicalHash.begin(),canonicalHash.end(),
                    [](char c) { return (c>='0' && c<='9') || (c>='a' && c<='f'); }));
            }
            assert(!std::getline(input,extra));
            const auto session=sessionLine.substr(8); assert(DesktopApiClient::accountId(session));
            const auto selected=static_cast<StartOwnerCrashCut>(index);
            const bool lifecycle=selected>=StartOwnerCrashCut::afterEosBeforeSeal;
            const bool removed=selected==StartOwnerCrashCut::shortAfterRecycle;
            const bool packageCut=selected>=StartOwnerCrashCut::packageBeforeIndex0 && !lifecycle;
            const bool packagePresent=packageCut || (lifecycle && !removed);
            const bool semanticAck=selected==StartOwnerCrashCut::packageAfterSemanticAck;
            const auto privatePackage=fixture.root/session/L".custody-v1";
            assert(std::filesystem::exists(fixture.root/session)==packagePresent);
            if (packageCut) {
                assert(std::filesystem::is_regular_file(privatePackage/L"package-state"/L"id.bin") &&
                    std::filesystem::is_regular_file(privatePackage/L"canonical"/L"id.bin") &&
                    !std::filesystem::exists(privatePackage/L"canonical"/L"content.packed-v2") &&
                    std::filesystem::exists(privatePackage/L"package-state"/L"index.0")==
                        (selected!=StartOwnerCrashCut::packageBeforeIndex0) &&
                    std::filesystem::exists(privatePackage/L"package-state"/L"index.1")==semanticAck);
            }
            const auto before=snapshot(fixture.root); assert(!before.empty());
            // Parent's first owner for this root: no child RAM proof/handle/cache is transferred.
            std::async(std::launch::async,[&] {
                auto cancel=std::make_shared<std::atomic<bool>>(false);
                auto opened=ProtectedCustodyStoreOwner::open(fixture.root,cancel); assert(opened.ok());
                const auto value=(*opened.value)->readQueueValue(cancel);
                assert(value.ok() && (*opened.value)->queueGeneration()==generations[index] && (*value.value)->items().size()==rows[index]);
                if (rows[index]) {
                    const auto& row=(*value.value)->items().front();
                    assert(std::string_view(row.localRecordingId)==session && row.directoryId==row.localRecordingId && row.sessionId==row.localRecordingId &&
                        std::string_view(row.packageDirectory)==(fixture.root/session).u8string() && row.ownerUserId.empty() && row.ownerWorkspaceId.empty() &&
                        row.status==UploadQueueStatus::quarantined && row.safeReason=="capture_prepared" && !hasUploadServerIdentity(row) && !row.attempts);
                }
                assert((*value.value)->deletionOperations().empty() && (*value.value)->purgeAcknowledgements().empty());
                if (lifecycle && !removed) {
                    auto pair=(*opened.value)->readPackage(session,cancel); assert(pair.ok());
                    if (selected==StartOwnerCrashCut::stopBeforeEos) {
                        assert((*pair.value)->current().phase==CustodyPackagePhase::capturing && (*pair.value)->current().generation==1);
                        for (const auto& birth:(*pair.value)->slots()) assertStartOwnerBirth(birth,session,(*opened.value)->queueContext());
                        const auto canonicalPath=std::filesystem::path(session)/L".custody-v1"/L"canonical"/L"content.packed-v2";
                        assert(before.at(canonicalPath.native())==canonicalHash);
                        {
                            auto readers=openProtectedCustodyReaders(fixture.root,*pair.value,cancel); assert(readers.ok());
                            for (unsigned slot=0;slot<2;++slot) {
                                std::size_t canonical=0; const auto& valueSlot=(*pair.value)->slots()[slot];
                                while (canonical<valueSlot.refCount && valueSlot.refs[canonical].role!=CustodyRole::canonical) ++canonical;
                                assert(canonical<valueSlot.refCount && valueSlot.refs[canonical].packed);
                                auto* stream=(*readers.value)[slot][canonical].stream.Get();
                                STATSTG stat{}; assert(stream->Stat(&stat,STATFLAG_NONAME)==S_OK && stat.type==STGTY_STREAM && !stat.cbSize.QuadPart);
                                BYTE byte=0xa5; ULONG got=99;
                                assert(stream->Read(&byte,1,&got)==S_FALSE && !got && byte==0xa5);
                            }
                        }
                        pair.value.reset();
                        const auto prefix=LocalRecordingPackage::inspectUnfinished(*opened.value,session,cancel);
                        assert(!prefix.ok() && prefix.error==CustodyFileError::invalidContent && !prefix.nativeError);
                    } else if (selected==StartOwnerCrashCut::afterEosBeforeSeal) {
                        assert((*pair.value)->current().phase==CustodyPackagePhase::finalizing && (*pair.value)->current().generation==2);
                        pair.value.reset(); // Release exclusive package-state before a fresh unfinished acquisition.
                        const auto prefix=LocalRecordingPackage::inspectUnfinished(*opened.value,session,cancel);
                        assert(prefix.ok() && (*prefix.value)->completeFrames()==StartOwnerCrashProof::frames);
                    } else {
                        const bool shortPending=selected==StartOwnerCrashCut::shortAfterRetirementReadback || selected==StartOwnerCrashCut::shortBeforeRecycle;
                        assert((*pair.value)->current().phase==(shortPending ? CustodyPackagePhase::discardPending : CustodyPackagePhase::sealedNormal));
                        if (selected>=StartOwnerCrashCut::shortAfterRetirementReadback) {
                            const auto& current=(*pair.value)->current();
                            assert(current.generation==3 && current.reason==ReasonCode::none && current.shortRecordingDiscarded==shortPending &&
                                current.refCount==4 && std::string_view(current.directory.data())==session &&
                                current.context.storeId==(*opened.value)->queueContext().storeId);
                            unsigned seen=0;
                            for (const auto& slot:(*pair.value)->slots()) {
                                assert(slot.context.storeId==current.context.storeId && slot.context.objectId==current.context.objectId &&
                                    slot.context.role==current.context.role && std::string_view(slot.directory.data())==session);
                                if (slot.generation==2) { assert(slot.phase==CustodyPackagePhase::finalizing && !slot.shortRecordingDiscarded); seen|=1; }
                                else { assert(slot.generation==3 && slot.phase==current.phase && slot.shortRecordingDiscarded==shortPending); seen|=2; }
                            }
                            assert(seen==3);
                            const auto canonical=std::find_if(current.refs.begin(),current.refs.begin()+current.refCount,
                                [](const auto& ref) { return ref.role==CustodyRole::canonical; });
                            assert(canonical!=current.refs.begin()+current.refCount && canonical->packed && canonical->sealed &&
                                canonical->length && *canonical->length==StartOwnerCrashProof::frames*1920 && canonical->sha256);
                        }
                        const auto inspected=LocalRecordingPackage::inspectProtected(fixture.root,*pair.value,session,cancel);
                        assert(inspected.ok() && (*inspected.value)->evidence().integrity==(shortPending ? PackageIntegrity::discardPending : PackageIntegrity::valid) &&
                            (*inspected.value)->evidence().manifestSessionMatched &&
                            (*inspected.value)->evidence().durationMs==StartOwnerCrashProof::frames*10 &&
                            (*inspected.value)->evidence().playback.decodedFrames>0);
                    }
                }
                if (packageCut) {
                    const auto pair=(*opened.value)->readPackage(session,cancel);
                    if (!semanticAck) {
                        assert(!pair.ok() && pair.error==CustodyFileError::recoveryRequired);
                    } else {
                        assert(pair.ok() && (*pair.value)->indices().indices[0].generation==1 &&
                            (*pair.value)->indices().indices[1].generation==1);
                        const auto& slots=(*pair.value)->slots();
                        for (const auto& birth:slots) assertStartOwnerBirth(birth,session,(*opened.value)->queueContext());
                        assert(slots[0].context.objectId==slots[1].context.objectId &&
                            slots[0].refs[0].objectId==slots[1].refs[0].objectId &&
                            slots[0].refs[0].containerId==slots[1].refs[0].containerId);
                    }
                }
            }).get();
            assert(snapshot(fixture.root)==before && std::filesystem::exists(fixture.root/session)==packagePresent);
            if (packageCut) assert(!std::filesystem::exists(privatePackage/L"canonical"/L"content.packed-v2"));
        }
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes()==baseline; }));
        if (static_cast<StartOwnerCrashCut>(index)==StartOwnerCrashCut::stopBeforeEos ||
            static_cast<StartOwnerCrashCut>(index)>=StartOwnerCrashCut::shortAfterRetirementReadback) {
            std::array<CustodyNativeJob,4> jobs; for (const auto& job:jobs) assert(job);
            std::array<CustodyPin,32> pins; for (const auto& pin:pins) assert(pin);
        }
        std::fprintf(stderr,"START_OWNER_PROCESS_DEATH cut=%ls cold_generation=%llu rows=%zu unchanged=1 released=1 audio=0 network=0\n",
            startOwnerCrashArguments[index].data(),static_cast<unsigned long long>(generations[index]),rows[index]);
        std::fflush(stderr);
    }
}
enum class VerticalCase { normal, staleEpoch, lostPoll, nativeStopFault, lateDevice, lateUi, ownedUpload, scheduledUpload, signedOut, successfulUpload, resumedUpload, successfulUploadLateLogout };
void protectedStartOwner() {
    protectedStartOwnerProcessDeath();
    const auto baseline = CustodyOwnedMemory::usedBytes();
    {
    Fixture fixture;
    constexpr std::string_view user = "11111111-1111-4111-8111-111111111111";
    constexpr std::string_view workspace = "22222222-2222-4222-8222-222222222222";
    std::string session;
    const auto matches = [&](const ProtectedUploadQueueValue& value) {
        if (value.items().size() != 1) return false;
        const auto& row = value.items().front();
        const auto expectedPath = (fixture.root / session).u8string();
        return std::string_view(row.localRecordingId) == session && row.directoryId == row.localRecordingId &&
            row.sessionId == row.localRecordingId && std::string_view(row.ownerUserId) == user &&
            std::string_view(row.ownerWorkspaceId) == workspace && row.status == UploadQueueStatus::quarantined &&
            row.safeReason == "capture_prepared" && !hasUploadServerIdentity(row) &&
            std::string_view(row.packageDirectory) == expectedPath;
    };
    {
        const DesktopHttpTransport::UploadSend wire = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
            assert(request.method == "GET");
            if (request.path == "/desktop/settings/spaces")
                return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
            assert(request.path == "/api/v1/auth/me");
            return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
        };
        NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), true}, wire);
        startAndAdopt(capture, 1);
        capture.setAuthSessionToken("generated-start-owner");
        assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
        session = capture.sessionId();
        std::atomic<unsigned> devices{0};
        const auto device = [&](const std::atomic_bool& running, std::atomic_bool& ready, const CaptureBatchCallback&) {
            ++devices; ready.store(true);
            while (running.load()) std::this_thread::sleep_for(std::chrono::milliseconds(1));
        };
        CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(capture), device, device);
        ReadinessInputs hardware;
        hardware.microphonePermissionGranted = hardware.microphoneEndpointReady = hardware.renderEndpointReady =
            hardware.formatNormalizationReady = hardware.aecReady = hardware.aacEncoderReady = true;
        {
            std::lock_guard<std::mutex> lock(cutMutex);
            cutReached = cutReleased = false;
            startOwnerFlushRole.store(1); ioCut.store(IoCut::pauseAfterFlush);
        }
        assert(NativeCaptureStorageTestPeer::beginPending(capture, hardware).accepted());
        bool held = false;
        {
            std::unique_lock<std::mutex> lock(cutMutex);
            held = cutWake.wait_for(lock, std::chrono::seconds(10), [] { return cutReached; });
        }
        const bool beforePrepared = !NativeCaptureStorageTestPeer::prepared(capture);
        std::error_code pathError;
        const bool beforeBirth = !std::filesystem::exists(fixture.root / session, pathError) && !pathError;
        const auto role = startOwnerFlushRole.exchange(0);
        const auto beforeDevices = devices.load();
        ioCut.store(IoCut::none);
        {
            std::lock_guard<std::mutex> lock(cutMutex);
            cutReleased = true; cutWake.notify_all();
        } // Release real IO before any assertion can terminate the test.
        std::fprintf(stderr, "START_OWNER before_ack held=%u factory_absent=%u prepared_absent=%u devices=%u queue_role=%u\n",
            held ? 1U : 0U, beforeBirth ? 1U : 0U, beforePrepared ? 1U : 0U, beforeDevices, role == 2 ? 1U : 0U);
        std::fflush(stderr);
        assert(held && beforeBirth && beforePrepared && beforeDevices == 0 && role == 2);
        // Do not adopt the result yet: a real committed metadata completion
        // must still hold factory/prepared closed until value polling ACK.
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
        const auto ticket = NativeCaptureStorageTestPeer::workerTicket(capture);
        assert(ticket.kind == NativeCapture::QueueMutationKind::recording &&
            ticket.state == NativeCapture::QueueTicketState::committed && ticket.targetGeneration > ticket.baseGeneration);
        assert(!NativeCaptureStorageTestPeer::prepared(capture) && devices == 0 &&
            !std::filesystem::exists(fixture.root / session));
        // Do not pollHealth: it launches the devices only after preparation.
        // A generated readiness flag or a test queue injection cannot satisfy this.
        assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::prepared(capture); }));
        const auto value = NativeCaptureStorageTestPeer::projection(capture);
        const bool retained = value && matches(*value);
        std::fprintf(stderr, "START_OWNER prepared=1 durable_projection=%u devices=%u frames=%llu\n",
            retained ? 1U : 0U, devices.load(), static_cast<unsigned long long>(NativeCaptureStorageTestPeer::writtenFrames(capture)));
        std::fflush(stderr);
        assert(devices == 0 && NativeCaptureStorageTestPeer::writtenFrames(capture) == 0 && retained);
        NativeCaptureStorageTestPeer::freezeRecordingAccount(capture);
        assert(capture.recordingProblems(2000).empty()); // Pending reservation is not a damaged recording.
        CaptureSessionTestPeer::problemIndicator(NativeCaptureStorageTestPeer::controller(capture), true);
        const auto problems = capture.recordingProblems(2000);
        assert(problems.size() == 1 && std::string_view(problems.front().sessionId) == session &&
            problems.front().state == LocalProblemState::problem); // A real capture blocker must not be hidden.
        CaptureSessionTestPeer::problemIndicator(NativeCaptureStorageTestPeer::controller(capture), false);
        capture.setAuthSessionToken({}); // A later account transition never rewrites Start ownership.
        (void)capture.stop();
        assert(waitFor([&] { capture.pollHealth(); capture.pollUploads(); return capture.indicator().state == SessionState::failed; }));
        capture.shutdown();
        assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
    }
    // A cold genuine owner, not only a UI projection, must read the same binding.
    std::async(std::launch::async, [&] {
        const auto cancel = std::make_shared<std::atomic<bool>>(false);
        auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(opened.ok());
        const auto value = (*opened.value)->readQueueValue(cancel);
        assert(value.ok() && matches(**value.value));
    }).get();
    std::fprintf(stderr, "START_OWNER memory live=%zu baseline=%zu idle=%zu\n",
        CustodyOwnedMemory::usedBytes(), baseline, idleOwnedBytes);
    assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
    std::fputs("START_OWNER cold_binding=pass device_audio=0 real_network=0\n", stderr);
    }
    for (unsigned mode = 0; mode != 7; ++mode) {
        Fixture fixture;
        std::string session;
        const bool signedOut = mode == 1 || mode >= 4;
        const auto matches = [&](const ProtectedUploadQueueValue& value) {
            if (value.items().size() != 1) return false;
            const auto& row = value.items().front();
            return std::string_view(row.localRecordingId) == session && row.directoryId == row.localRecordingId &&
                row.sessionId == row.localRecordingId && row.ownerUserId.empty() && row.ownerWorkspaceId.empty() &&
                row.status == UploadQueueStatus::quarantined && !hasUploadServerIdentity(row) &&
                row.safeReason == (signedOut ? "capture_prepared" : "capture_owner_unknown") &&
                std::string_view(row.packageDirectory) == (fixture.root / session).u8string();
        };
        {
            const DesktopHttpTransport::UploadSend offline = [](const auto&, const auto&) -> DesktopHttpTransport::UploadResponse {
                return {503, "{}"}; // An unresolved generated token can never call a real server.
            };
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), true}, offline);
            startAndAdopt(capture, 1);
            if (signedOut || mode == 2) capture.setAuthSessionToken({}, true);
            if (mode == 2) capture.setAuthSessionToken({}, false);
            if (mode == 3) capture.setAuthSessionToken("generated-unresolved");
            session = capture.sessionId();
            if (mode == 6) ioCut.store(IoCut::ambiguousRename);
            assert(NativeCaptureStorageTestPeer::beginPending(capture, {}).accepted());
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            const auto ticket = NativeCaptureStorageTestPeer::workerTicket(capture);
            ioCut.store(IoCut::none);
            assert(ticket.state == (mode == 6 ? NativeCapture::QueueTicketState::ambiguous : NativeCapture::QueueTicketState::committed));
            assert(!std::filesystem::exists(fixture.root / session) && !NativeCaptureStorageTestPeer::prepared(capture));
            if (mode == 4) {
                capture.setAuthSessionToken("generated-new-epoch"); capture.setAuthSessionToken({});
            } else if (mode == 5) capture.requestShutdown();
            if (mode < 4) {
                assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::prepared(capture); }));
                assert(matches(*NativeCaptureStorageTestPeer::projection(capture)));
                assert(NativeCaptureStorageTestPeer::writtenFrames(capture) == 0);
            } else if (mode == 6) {
                capture.pollUploads(); // Original ambiguous result is not an ACK of success.
                assert(waitFor([&] { return NativeCaptureStorageTestPeer::physicalReadback(capture); }));
            }
            (void)capture.stop();
            capture.setAuthSessionToken({});
            assert(waitFor([&] {
                capture.pollUploads(); capture.pollHealth();
                return capture.indicator().state == SessionState::failed;
            }));
            if (mode >= 4) assert(!std::filesystem::exists(fixture.root / session));
            capture.shutdown();
            assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        }
        std::async(std::launch::async, [&] {
            const auto cancellation = std::make_shared<std::atomic<bool>>(false);
            auto owner = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(owner.ok());
            auto value = (*owner.value)->readQueueValue(cancellation); assert(value.ok() && matches(**value.value));
        }).get();
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
        std::fprintf(stderr, "START_OWNER classification=%u marker=%s cold=1 no_saved=1 no_audio=1\n",
            mode, signedOut ? "prepared" : "unknown");
    }
}
void protectedPendingCancellation() {
    for (unsigned mode = 0; mode != 6; ++mode) {
        Fixture fixture;
        std::string session;
        {
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), true});
            startAndAdopt(capture, 1);
            const auto before = NativeCaptureStorageTestPeer::projection(capture);
            session = capture.sessionId();
            std::atomic<unsigned> deviceStarts{0};
            const auto device = [&](const std::atomic_bool& running, std::atomic_bool& ready,
                                    const CaptureBatchCallback&) {
                ++deviceStarts; ready.store(true);
                while (running.load()) std::this_thread::sleep_for(std::chrono::milliseconds(1));
            };
            std::optional<std::array<CustodyNativeJob, 4>> pressure;
            if (mode == 3) {
                pressure.emplace();
                for (const auto& job : *pressure) assert(job);
            } else {
                std::lock_guard<std::mutex> lock(cutMutex);
                cutReached = cutReleased = false;
                ioCut.store(IoCut::pauseAfterFlush);
            }
            unsigned guardCalls = 0;
            const auto pending = capture.record([&](const std::string&) {
                return [&](std::string_view) { ++guardCalls; return false; };
            });
            assert(pending.accepted() && pending.state == SessionState::starting);
            CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(capture), device, device);
            const bool duplicateRejected = !capture.record().accepted();
            bool cutSeen = true, waiting = true, reserved = true, stopped = true;
            if (mode != 3) {
                {
                    std::unique_lock<std::mutex> lock(cutMutex);
                    cutSeen = cutWake.wait_for(lock, std::chrono::seconds(10), [] { return cutReached; });
                }
                capture.pollHealth();
                waiting = deviceStarts == 0 && guardCalls == 0 && capture.indicator().stopAvailable;
                WindowsDesktopSession other("pending-start-must-reserve-session");
                const auto attempted = other.beginReadinessCheck();
                reserved = attempted.reason == ReasonCode::activeSessionExists;
                if (attempted.accepted()) (void)other.block(ReasonCode::storageUnavailable);
                if (mode == 0) {
                    const auto stopping = capture.stop();
                    stopped = stopping.accepted() && stopping.state == SessionState::finalizing;
                } else if (mode == 1) {
                    capture.setAuthSessionToken("generated-stale-pending");
                    capture.setAuthSessionToken({}); // No account/network request.
                    capture.pollHealth();
                } else if (mode == 4) capture.setUpdateAdmissionBlocked(true);
                else if (mode == 5) capture.requestShutdown();
                ioCut.store(IoCut::none);
                {
                    std::lock_guard<std::mutex> lock(cutMutex);
                    cutReleased = true; cutWake.notify_all();
                }
            }
            // No assertion can abandon a worker while the global cut is held.
            assert(pending.accepted() && pending.state == SessionState::starting && duplicateRejected);
            assert(cutSeen && waiting && reserved && stopped);
            assert(waitFor([&] {
                capture.pollHealth(); capture.pollUploads();
                return capture.indicator().state == SessionState::failed;
            }));
            pressure.reset();
            assert((mode == 2 ? deviceStarts == 2 && guardCalls == 1 : deviceStarts == 0 && guardCalls == 0));
            assert(NativeCaptureStorageTestPeer::writtenFrames(capture) == 0);
            const auto after = NativeCaptureStorageTestPeer::projection(capture);
            assert(before->items().empty() && after && after->items().size() == (mode == 2 ? 1U : 0U));
            assert(NativeCaptureStorageTestPeer::generation(capture) == (mode == 2 ? 3U : 1U));
            if (mode == 2) {
                const auto& row = after->items().front();
                assert(std::string_view(row.sessionId) == session && row.localRecordingId == row.sessionId &&
                    row.directoryId == row.sessionId && row.status == UploadQueueStatus::quarantined &&
                    row.safeReason == "capture_owner_unknown" && row.ownerUserId.empty() &&
                    row.ownerWorkspaceId.empty() && !hasUploadServerIdentity(row));
            }
            assert(!capture.indicator().visible);
            if (mode == 2) {
                assert(waitFor([&] { capture.pollUploads(); return capture.localQueueComplete(); }));
                assert(capture.readiness().storageWritable); // Start guard failed, queue publication did not.
            } else assert(!capture.localQueueComplete());
            if (mode == 4) assert(waitFor([&] { capture.pollUploads(); return capture.updateWorkDrained(); }));
            if (mode == 5) {
                capture.shutdown();
                assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
            }
            WindowsDesktopSession next("pending-start-released-after-terminal");
            assert(next.beginReadinessCheck().accepted());
            assert(next.block(ReasonCode::storageUnavailable).accepted());
            std::fprintf(stderr, "PENDING_START cancel_case=%u devices=%u guard=%u no_frames=1 no_saved=1 released=1\n",
                mode, deviceStarts.load(), guardCalls);
        }
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        std::async(std::launch::async, [&] {
            const auto cancel = std::make_shared<std::atomic<bool>>(false);
            auto owner = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(owner.ok());
            const auto queue = (*owner.value)->readQueueValue(cancel); assert(queue.ok());
            assert((*owner.value)->queueGeneration() == (mode == 2 ? 3U : 1U) &&
                (*queue.value)->items().size() == (mode == 2 ? 1U : 0U));
            assert(std::filesystem::exists(fixture.root / session) == (mode == 2));
            if (mode == 2) {
                const auto& row = (*queue.value)->items().front();
                assert(std::string_view(row.sessionId) == session && row.localRecordingId == row.sessionId &&
                    row.directoryId == row.sessionId && std::string_view(row.packageDirectory) == (fixture.root / session).u8string() &&
                    row.status == UploadQueueStatus::quarantined && row.safeReason == "capture_owner_unknown" &&
                    row.ownerUserId.empty() && row.ownerWorkspaceId.empty() && !hasUploadServerIdentity(row));
            }
        }).get();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
    }
    {
        Fixture fixture;
        NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), true});
        // No storage worker: a refused submit must not strand the visible
        // reservation or create the root synchronously on the UI thread.
        const auto refused = NativeCaptureStorageTestPeer::beginPending(capture, {});
        assert(refused.state == SessionState::failed && !capture.indicator().visible &&
            !std::filesystem::exists(fixture.root));
        WindowsDesktopSession next("failed-submit-released-reservation");
        assert(next.beginReadinessCheck().accepted());
        assert(next.block(ReasonCode::storageUnavailable).accepted());
        std::fputs("PENDING_START submit_refused=1 no_io=1 released=1\n", stderr);
    }
    assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
}
auto generatedProducer(NativeCapture& capture, std::atomic<bool>& emit, AudioSource source, bool lateDevice = false,
    std::uint64_t frameCount = 3000) {
    return [&capture, &emit, source, lateDevice, frameCount](const std::atomic_bool& running, std::atomic_bool& ready,
                                               const CaptureBatchCallback& callback) {
        ready.store(true);
        std::uint64_t frame = 0;
        for (; frame != frameCount && running.load(); ++frame) {
            // Both sources together stay below 254 data packets + two EOS.
            while (running.load() && (!emit.load() ||
                frame > NativeCaptureStorageTestPeer::writtenFrames(capture) + 32)) {
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
            if (!running.load()) return;
            AudioBatch batch{source, 48'000, 1, static_cast<std::int64_t>(frame * 480),
                1, 1, false, std::vector<float>(480), frame * 480};
            for (std::size_t sample = 0; sample != batch.samples.size(); ++sample)
                batch.samples[sample] = static_cast<float>(std::sin((frame * 480 + sample) * 0.017)) * 0.125F;
            callback(std::move(batch));
        }
        while (running.load()) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        if (lateDevice && source == AudioSource::microphone)
            std::this_thread::sleep_for(std::chrono::milliseconds(5'200));
    };
}
int protectedStartOwnerLifecycleChild(NativeCapture& capture, StartOwnerCrashProof& proof, const ReadinessInputs& hardware) {
    // Same 100-frame fixture as existing finalize-admission/Native short tests.
    // All callback state lives in proof, which outlives capture on missing-event exits.
    capture.notificationCard().setQuiet(true);
    capture.onShortRecordingPresented=[&proof] { ++proof.notices; };
    proof.epoch=capture.authGeneration();
    const auto render=generatedProducer(capture,proof.emit,AudioSource::systemRender,false,proof.frames);
    const auto microphone=generatedProducer(capture,proof.emit,AudioSource::microphone,false,proof.frames);
    CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(capture),
        [&proof,render](const std::atomic_bool& running,std::atomic_bool& ready,const CaptureBatchCallback& callback) {
            ++*proof.devices; render(running,ready,callback);
        },
        [&proof,microphone](const std::atomic_bool& running,std::atomic_bool& ready,const CaptureBatchCallback& callback) {
            ++*proof.devices; microphone(running,ready,callback);
        });
    if (!NativeCaptureStorageTestPeer::beginPending(capture,hardware).accepted()) return 89;
    if (!waitFor([&] { capture.pollUploads(); capture.pollHealth(); return capture.indicator().state==SessionState::recording; })) return 89;
    proof.reservation=NativeCaptureStorageTestPeer::projection(capture);
    const auto ticket=NativeCaptureStorageTestPeer::ticket(capture);
    assert(proof.reservation && proof.reservation->items().size()==1 && NativeCaptureStorageTestPeer::generation(capture)==2 &&
        ticket && ticket->kind==NativeCapture::QueueMutationKind::recording && ticket->state==NativeCapture::QueueTicketState::committed &&
        ticket->baseGeneration==1 && ticket->targetGeneration==2 && ticket->epoch==proof.epoch && capture.authGeneration()==proof.epoch);
    proof.startTicket=ticket->id;
    assert(capture.notificationCard().history().empty() && !proof.notices.load() && !proof.network->load());
    if (proof.cut==StartOwnerCrashCut::stopBeforeEos) {
        proof.stopCanonicalPath=L"\\\\?\\"+(proof.package/L".custody-v1"/L"canonical"/L"content.packed-v2").native();
        proof.stopCanonicalHash=sha256File(proof.stopCanonicalPath); assert(proof.stopCanonicalHash.size()==64);
        // Existing cut cleanup pattern: a missing-event/exception path must unblock the dispatcher before capture teardown.
        struct ReleaseCut {
            ~ReleaseCut() {
                startOwnerCrashArmed.store(false);
                { std::lock_guard<std::mutex> lock(cutMutex); cutReleased=true; }
                cutWake.notify_all();
            }
        } releaseOnFailure;
        { std::lock_guard<std::mutex> lock(cutMutex); cutReached=cutReleased=false; }
        startOwnerCrashArmed.store(true,std::memory_order_release);
        proof.emit.store(true);
        if (!waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; })) return 89;
        const auto stopped=capture.stop(RecordingStopReason::interruption);
        assert(stopped.accepted() && stopped.state==SessionState::stopping);
        assert(startOwnerCrashArmed.exchange(false));
        terminateStartOwnerCrash(); // Hold stays closed: actual Stop accepted, both EOS queued but neither processed.
    }
    proof.emit.store(true);
    if (!waitFor([&] { capture.pollHealth(); return NativeCaptureStorageTestPeer::writtenFrames(capture)==proof.frames; })) return 89;
    nativeShortAttempts.store(0); nativeShortEffects.store(0);
    startOwnerCrashArmed.store(true,std::memory_order_release);
    const bool shortStop=proof.cut==StartOwnerCrashCut::shortAfterRecycle ||
        proof.cut==StartOwnerCrashCut::shortAfterRetirementReadback || proof.cut==StartOwnerCrashCut::shortBeforeRecycle;
    const auto stopped=shortStop ? capture.stop() : capture.stop(RecordingStopReason::interruption);
    assert(stopped.accepted());
    if (!waitFor([&] { return CaptureSessionTestPeer::completed(NativeCaptureStorageTestPeer::controller(capture)); })) {
        startOwnerCrashArmed.store(false); return 89;
    }
    capture.pollHealth(); // One real post-EOS finalizer handoff; no further UI polling before the selected death.
    assert(CaptureSessionTestPeer::bothEndsProcessed(NativeCaptureStorageTestPeer::controller(capture)) &&
        capture.indicator().state==SessionState::finalizing && capture.notificationCard().history().empty());
    proof.stopReturned.store(true,std::memory_order_release);
    const bool ready=waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); },std::chrono::seconds(30));
    if (ready && proof.cut>=StartOwnerCrashCut::shortAfterRetirementReadback) {
        proof.finalPackageSnapshot.emplace(snapshot(proof.package)); assert(!proof.finalPackageSnapshot->empty());
    }
    if (ready && (proof.cut==StartOwnerCrashCut::afterFinishReadback || proof.cut==StartOwnerCrashCut::shortAfterRetirementReadback)) {
        assert(startOwnerCrashArmed.exchange(false));
        assert(capture.notificationCard().history().empty() && capture.indicator().state!=SessionState::savedLocal);
        terminateStartOwnerCrash(); // Committed g3/readback, no final queue adoption or release/reopen.
    }
    if (ready && proof.cut==StartOwnerCrashCut::normalAfterFinishAdoption) {
        assert(capture.notificationCard().history().empty() && NativeCaptureStorageTestPeer::projection(capture)==proof.reservation);
        NativeCaptureStorageTestPeer::pollStorage(capture); // Actual finish ACK only; never pollHealth/terminal UI here.
        const auto work=NativeCaptureStorageTestPeer::storageWork(capture);
        if (!waitFor([&] {
            std::lock_guard<std::mutex> lock(work->mutex);
            return !work->inFlight && !work->recording;
        },std::chrono::seconds(30))) { startOwnerCrashArmed.store(false); return 89; }
        assert(startOwnerCrashArmed.exchange(false));
        terminateStartOwnerCrash(); // Native terminal retained, controller still finalizing with no terminal UI delivery.
    }
    if (ready && (proof.cut==StartOwnerCrashCut::shortAfterRecycle || proof.cut==StartOwnerCrashCut::shortBeforeRecycle)) {
        assert(capture.notificationCard().history().empty() && NativeCaptureStorageTestPeer::projection(capture)==proof.reservation);
        NativeCaptureStorageTestPeer::pollStorage(capture); // Actual retirement adoption permits the single OS effect.
        const auto work=NativeCaptureStorageTestPeer::storageWork(capture);
        (void)waitFor([&] {
            std::lock_guard<std::mutex> lock(work->mutex);
            return !work->inFlight || work->shortDiscardPending || work->queueFailed || work->terminal;
        },std::chrono::seconds(30));
    }
    startOwnerCrashArmed.store(false);
    return 89; // Missing phase/rename/OS effect is never accepted as the intended death.
}
void protectedStartOwnerRecovery() {
    for (unsigned mode = 0; mode != 8; ++mode) {
        Fixture fixture;
        constexpr std::string_view session = "44444444-4444-4444-8444-444444444444";
        constexpr std::string_view user = "11111111-1111-4111-8111-111111111111";
        constexpr std::string_view workspace = "22222222-2222-4222-8222-222222222222";
        std::async(std::launch::async, [&] {
            const auto cancel = std::make_shared<std::atomic<bool>>(false);
            auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(opened.ok());
            auto owner = std::move(*opened.value);
            auto initial = owner->readQueueValue(cancel); assert(initial.ok() && owner->queueGeneration() == 1);
            auto candidate = std::allocate_shared<ProtectedUploadQueueValue>(CustodyAllocator<ProtectedUploadQueueValue>{}, **initial.value);
            const auto prepared = owner->prepareRecordingReservation(*candidate, session, user, workspace, true, 1000, cancel);
            assert(prepared.ok() && *prepared.value);
            auto bytes = candidate->serialize(cancel); assert(bytes.ok());
            const auto saved = commitProtectedCustodyMetadata(owner, owner->queueContext(), 1, *bytes.value, cancel);
            assert(saved.state == CustodyCommitState::committed && saved.targetGeneration == 2);
            auto writer = V5LocalRecordingWriter::open(owner, std::string(session), cancel); assert(writer.ok());
            CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
            for (unsigned i = 0; i != 100; ++i) {
                frame.ptsFrames = static_cast<std::int64_t>(i) * 480;
                assert((*writer.value)->append(frame));
            }
            const auto result = (*writer.value)->finalize(ReasonCode::none, RecordingStopReason::interruption);
            assert(result.normalPackage() && result.durationMs == 1000);
            // A real sealed package, but no finishRecordingReservation or queue
            // publication: emulate the crash boundary by releasing every native owner.
        }).get();
        const auto packageBefore = snapshot(fixture.root / std::string(session));
        const bool stoppingInspection = mode == 4;
        if (mode == 1 || mode == 7) ambiguousRecordingQueue.store(true);
        if (mode == 2) ioCut.store(IoCut::flush);
        if (mode >= 4 && mode <= 6) {
            oldPackedPath = L"\\\\?\\" + (fixture.root / std::string(session) / L".custody-v1" / L"canonical" / L"content.packed-v2").native();
            { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
            pauseOldPackedRead.store(true);
        }
        std::atomic<unsigned> wire{0};
        {
            const DesktopHttpTransport::UploadSend accountWire = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
                assert(request.method == "GET");
                if (request.path == "/desktop/settings/spaces")
                    return {200, R"({"spaces":[{"id":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb","active":true}]})"};
                assert(request.path == "/api/v1/auth/me");
                return {200, R"({"user_id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","workspace_id":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
            };
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), true}, accountWire,
                [&](const auto&, const auto&) { ++wire; return DesktopHttpTransport::ProtectedUploadResponse{503, "{}"}; });
            startAndAdopt(capture, 2);
            auto reservation = NativeCaptureStorageTestPeer::projection(capture);
            assert(reservation->items().size() == 1 && reservation->items()[0].safeReason == "capture_prepared");
            if (mode == 5 || mode == 6) {
                assert(waitFor([&] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }));
                if (mode == 5) {
                    std::atomic<bool> emit{false};
                    CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(capture),
                        generatedProducer(capture, emit, AudioSource::systemRender, false, 100),
                        generatedProducer(capture, emit, AudioSource::microphone, false, 100));
                    ReadinessInputs hardware;
                    hardware.microphonePermissionGranted = hardware.microphoneEndpointReady = hardware.renderEndpointReady =
                        hardware.formatNormalizationReady = hardware.aecReady = hardware.aacEncoderReady = true;
                    assert(NativeCaptureStorageTestPeer::beginPending(capture, hardware).accepted());
                    assert(waitFor([&] { capture.pollUploads(); capture.pollHealth(); return capture.indicator().state == SessionState::recording; }));
                    emit.store(true);
                    assert(waitFor([&] { capture.pollHealth(); return NativeCaptureStorageTestPeer::writtenFrames(capture) == 100; }));
                    (void)capture.stop(RecordingStopReason::interruption);
                    assert(waitFor([&] { capture.pollHealth(); return NativeCaptureStorageTestPeer::resultReady(capture); }));
                    const auto finished = NativeCaptureStorageTestPeer::workerTicket(capture);
                    assert(finished.kind == NativeCapture::QueueMutationKind::recording && finished.baseGeneration == 3 && finished.targetGeneration == 4);
                    capture.pollUploads();
                    assert(waitFor([&] { capture.pollHealth(); return capture.indicator().state == SessionState::savedLocal; }));
                    reservation = NativeCaptureStorageTestPeer::projection(capture);
                    assert(reservation->items().size() == 2 && reservation->items()[0].safeReason == "capture_prepared" &&
                        reservation->items()[1].safeReason == "capture_owner_unknown");
                } else {
                    capture.setAuthSessionToken("generated-recovery-owner-B");
                    assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
                    assert(capture.currentAccount()->userId == "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
                }
                { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
                cutWake.notify_all();
            }
            if (stoppingInspection) {
                assert(waitFor([&] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }));
                capture.shutdown();
                assert(!capture.shutdownWorkDrained());
                {
                    const auto work = NativeCaptureStorageTestPeer::storageWork(capture);
                    std::lock_guard<std::mutex> lock(work->mutex);
                    assert(work->recoveryCancellation && work->recoveryCancellation->load());
                }
                { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
                cutWake.notify_all();
            } else {
                assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
                const auto ticket = NativeCaptureStorageTestPeer::workerTicket(capture);
                assert(ticket.kind == NativeCapture::QueueMutationKind::recovery && ticket.state == ((mode == 1 || mode == 7) ?
                    NativeCapture::QueueTicketState::ambiguous : mode == 2 ? NativeCapture::QueueTicketState::notCommitted :
                    NativeCapture::QueueTicketState::committed) && ticket.baseGeneration == (mode == 5 ? 4 : 2) &&
                    (mode == 2 || ticket.targetGeneration == (mode == 5 ? 5 : 3)));
                assert(NativeCaptureStorageTestPeer::projection(capture) == reservation && !wire.load());
                ioCut.store(IoCut::none);
                if (mode == 3 || mode == 7) {
                    capture.shutdown(); // Lost polling must not discard the actual committed disk truth.
                } else {
                    NativeCaptureStorageTestPeer::pollStorage(capture);
                    if (mode == 1) {
                        assert(waitFor([&] { return NativeCaptureStorageTestPeer::physicalReadback(capture); }));
                        assert(!capture.updateWorkDrained());
                        capture.pollUploads();
                    }
                    const auto recovered = NativeCaptureStorageTestPeer::projection(capture);
                    assert(recovered->items().size() == (mode == 5 ? 2 : 1) &&
                        NativeCaptureStorageTestPeer::generation(capture) == (mode == 2 ? 2 : mode == 5 ? 5 : 3));
                    const auto& row = recovered->items()[0];
                    assert(std::string_view(row.localRecordingId) == session && row.directoryId == row.localRecordingId && row.sessionId == row.localRecordingId);
                    assert(std::string_view(row.ownerUserId) == user && std::string_view(row.ownerWorkspaceId) == workspace);
                    assert(row.status == (mode == 2 ? UploadQueueStatus::quarantined : UploadQueueStatus::pending) &&
                        row.safeReason == (mode == 2 ? "capture_prepared" : "") && !hasUploadServerIdentity(row));
                    if (mode == 0) {
                        assert(waitFor([&] { const auto work = NativeCaptureStorageTestPeer::storageWork(capture);
                            std::lock_guard<std::mutex> lock(work->mutex); return !work->inFlight && !work->recoveryCancellation; }));
                        capture.recover(RecoveryTrigger::authRecovered); capture.pollUploads();
                        assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture) &&
                            NativeCaptureStorageTestPeer::workerTicket(capture).id > ticket.id; }));
                        const auto repeat = NativeCaptureStorageTestPeer::workerTicket(capture);
                        assert(!repeat.changed && repeat.baseGeneration == 3 && repeat.targetGeneration == 3);
                        capture.pollUploads();
                        assert(NativeCaptureStorageTestPeer::generation(capture) == 3 && NativeCaptureStorageTestPeer::projection(capture)->items().size() == 1);
                    }
                    capture.shutdown();
                }
            }
            assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        }
        pauseOldPackedRead.store(false); oldPackedPath.clear();
        std::async(std::launch::async, [&] {
            const auto cancel = std::make_shared<std::atomic<bool>>(false);
            const auto owner = ProtectedCustodyStoreOwner::open(fixture.root, cancel);
            assert(owner.ok() && (*owner.value)->queueGeneration() == ((mode == 2 || mode == 4) ? 2 : mode == 5 ? 5 : 3));
            const auto value = (*owner.value)->readQueueValue(cancel);
            assert(value.ok() && (*value.value)->items().size() == (mode == 5 ? 2 : 1));
            const auto& row = (*value.value)->items()[0];
            assert(row.status == ((mode == 2 || mode == 4) ? UploadQueueStatus::quarantined : UploadQueueStatus::pending) &&
                row.safeReason == ((mode == 2 || mode == 4) ? "capture_prepared" : "") && std::string_view(row.ownerUserId) == user &&
                std::string_view(row.ownerWorkspaceId) == workspace && std::string_view(row.localRecordingId) == session);
            if (mode == 5) {
                const auto& live = (*value.value)->items()[1];
                assert(live.status == UploadQueueStatus::quarantined && live.safeReason == "capture_owner_unknown" &&
                    live.ownerUserId.empty() && live.ownerWorkspaceId.empty() && std::string_view(live.localRecordingId) != session);
            }
        }).get();
        assert(!wire.load() && snapshot(fixture.root / std::string(session)) == packageBefore);
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        std::fprintf(stderr, "START_RECOVERY mode=%u sealed_before_finish_commit=1 exact_row=1 cold=1 owner_A=1 device_audio=0 protected_http=0 real_network=0\n", mode);
    }
}
void protectedStartOwnerUnfinishedRestart(unsigned first = 0, unsigned end = 5) {
    constexpr std::string_view session = "44444444-4444-4444-8444-444444444444";
    constexpr std::string_view user = "11111111-1111-4111-8111-111111111111";
    constexpr std::string_view workspace = "22222222-2222-4222-8222-222222222222";
    for (unsigned mode = first; mode != end; ++mode) {
        Fixture fixture;
        const auto initialOwned = CustodyOwnedMemory::usedBytes();
        CustodyContext queueContext{};
        std::async(std::launch::async, [&] {
            const auto cancel = std::make_shared<std::atomic<bool>>(false);
            auto owner = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(owner.ok());
            queueContext = (*owner.value)->queueContext();
            auto queue = (*owner.value)->readQueueValue(cancel); assert(queue.ok());
            ProtectedUploadQueueValue candidate(**queue.value);
            auto prepared = (*owner.value)->prepareRecordingReservation(candidate, session, user, workspace, true, 1000, cancel);
            assert(prepared.ok() && *prepared.value);
            if (mode == 4) {
                ProtectedUploadQueueValue::Item alias;
                alias.localRecordingId = alias.directoryId = alias.sessionId = "generated-alias";
                const auto path = (fixture.root / session).u8string(); alias.packageDirectory.assign(path.begin(), path.end());
                std::transform(alias.packageDirectory.begin(), alias.packageDirectory.end(), alias.packageDirectory.begin(),
                    [](char c) { return c >= 'a' && c <= 'z' ? static_cast<char>(c - 'a' + 'A') : c; });
                alias.status = UploadQueueStatus::quarantined; alias.safeReason = "capture_interrupted";
                alias.ownerUserId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
                alias.ownerWorkspaceId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
                assert(candidate.enqueue(std::move(alias), 1000, cancel.get()));
            }
            auto bytes = candidate.serialize(cancel); assert(bytes.ok());
            assert(commitProtectedCustodyMetadata(*owner.value, (*owner.value)->queueContext(), 1, *bytes.value, cancel).state == CustodyCommitState::committed);
            auto package = (*owner.value)->createPackage(session, cancel); assert(package.ok());
            auto canonical = (*package.value)->createWriter(CustodyRole::canonical); assert(canonical.ok());
            std::array<float, 100 * 480 + 47> samples{}; samples.fill(0.25F);
            samples.back() = std::numeric_limits<float>::quiet_NaN(); // Incomplete tail is not playable audio.
            assert((*canonical.value)->writeAt(0, samples.data(), sizeof(samples)).ok());
            assert((*canonical.value)->checkpoint().state == CustodyCommitState::committed);
            if (mode == 1) {
                auto state = (*package.value)->current(); ++state.generation; state.phase = CustodyPackagePhase::finalizing;
                assert((*package.value)->commit(state).state == CustodyCommitState::committed);
            } else if (mode == 2) {
                auto started = (*package.value)->createWriter(CustodyRole::media); assert(started.ok());
                const std::uint8_t partial = 1;
                assert((*started.value)->writeAt(0, &partial, 1).ok());
                assert((*started.value)->checkpoint().state == CustodyCommitState::committed);
            }
        }).get(); // Actual cold restart, no birth owner or writer retained.
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == initialOwned; }));
        const auto canonicalBefore = snapshot(fixture.root / session / L".custody-v1" / L"canonical");
        const auto queueBefore = snapshot(fixture.root / L".custody-v1");
        const auto diskBefore = snapshot(fixture.root);
        const auto observed = recoveryReadyObservations.load(std::memory_order_acquire);
        if (mode == 3) {
            oldPackedPath = L"\\\\?\\" + (fixture.root / session / L".custody-v1" / L"canonical" / L"content.packed-v2").native();
            { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
            pauseOldPackedRead.store(true);
        }
        std::atomic<unsigned> accountCalls{0}, wire{0};
        std::atomic<bool> ownerAccount{mode == 1}; // Also prove fresh display without an account-switch refresh.
        {
            const DesktopHttpTransport::UploadSend accountWire = [&](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
                ++accountCalls; assert(request.method == "GET");
                if (request.path == "/desktop/settings/spaces") return {200, ownerAccount.load() ?
                    R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})" :
                    R"({"spaces":[{"id":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb","active":true}]})"};
                assert(request.path == "/api/v1/auth/me");
                return {200, ownerAccount.load() ?
                    R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})" :
                    R"({"user_id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","workspace_id":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
            };
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), true}, accountWire,
                [&](const auto&, const auto&) { ++wire; return DesktopHttpTransport::ProtectedUploadResponse{503, "{}"}; });
            capture.setAuthSessionToken("generated-unfinished-restart-owner-B");
            assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
            assert(accountCalls == 2 && capture.currentAccount()->userId ==
                (mode == 1 ? user : "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"));
            startAndAdopt(capture, 2);
            if (mode == 3) {
                assert(waitFor([&] {
                    NativeCaptureStorageTestPeer::pollStorage(capture); // Adopt any unrelated auth-recovery ACK, as the UI does.
                    std::lock_guard<std::mutex> lock(cutMutex); return cutReached;
                }));
                capture.shutdown();
                const auto work = NativeCaptureStorageTestPeer::storageWork(capture);
                {
                    std::lock_guard<std::mutex> lock(work->mutex);
                    assert(work->recoveryCancellation && work->recoveryCancellation->load() && !work->terminal);
                }
                assert(!capture.shutdownWorkDrained()); // Cancellation does not retire the held native read.
                { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
                cutWake.notify_all();
            }
            assert(waitFor([&] {
                NativeCaptureStorageTestPeer::pollStorage(capture);
                const auto work = NativeCaptureStorageTestPeer::storageWork(capture);
                std::lock_guard<std::mutex> lock(work->mutex);
                return recoveryReadyObservations.load(std::memory_order_acquire) == observed + 1 &&
                    !work->recoveryCancellation && !work->inFlight && !work->commandReady;
            }, std::chrono::seconds(30)));
            const auto value = NativeCaptureStorageTestPeer::projection(capture);
            assert(value && value->items().size() == (mode == 4 ? 2 : 1) && value->items()[0].safeReason == "capture_prepared" &&
                value->items()[0].status == UploadQueueStatus::quarantined && std::string_view(value->items()[0].ownerUserId) == user &&
                std::string_view(value->items()[0].ownerWorkspaceId) == workspace && !hasUploadServerIdentity(value->items()[0]));
            if (mode == 0) {
                assert(waitFor([&] {
                    capture.pollUploads();
                    const auto ticket = NativeCaptureStorageTestPeer::workerTicket(capture);
                    return ticket.id == 1 && ticket.kind == NativeCapture::QueueMutationKind::uploadPrepare &&
                        ticket.state != NativeCapture::QueueTicketState::pending;
                })); // Reach the authenticated no-eligible-row branch, not only its allowance.
            }
            const auto ticket = NativeCaptureStorageTestPeer::workerTicket(capture);
            const bool sameContext = ticket.context.storeId == queueContext.storeId &&
                ticket.context.objectId == queueContext.objectId && ticket.context.role == queueContext.role;
            // Authenticated polling may prepare an upload, but owner B has no
            // eligible row. This terminal no-change ACK is not B promotion.
            std::fprintf(stderr, "UNFINISHED_RESTART_TICKET mode=%u id=%llu kind=%u state=%u error=%u native=%lu changed=%u context_equal=%u base=%llu target=%llu\n",
                mode, static_cast<unsigned long long>(ticket.id), static_cast<unsigned>(ticket.kind),
                static_cast<unsigned>(ticket.state), static_cast<unsigned>(ticket.error),
                static_cast<unsigned long>(ticket.nativeError), ticket.changed, sameContext,
                static_cast<unsigned long long>(ticket.baseGeneration), static_cast<unsigned long long>(ticket.targetGeneration));
            assert((ticket.id == 0 || (ticket.id == 1 && ticket.kind == NativeCapture::QueueMutationKind::uploadPrepare &&
                ticket.state == NativeCapture::QueueTicketState::notCommitted && ticket.error == CustodyFileError::none &&
                ticket.nativeError == 0 && !ticket.changed && sameContext &&
                ticket.baseGeneration == 2 && ticket.targetGeneration == 2)) && !wire.load());
            if (mode != 1) assert(!capture.openLocalPlayback(session, 17, true)); // Current B never owns A.
            assert(!capture.requestProtectedManualSend(value, session, capture.authGeneration(), true));
            if (mode != 3) {
                if (!ownerAccount.exchange(true)) {
                    capture.setAuthSessionToken("generated-unfinished-original-owner-A");
                    assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
                }
                assert(capture.currentAccount()->userId == user && capture.currentAccount()->workspaceId == workspace);
                assert(waitFor([&] { capture.pollUploads(); const auto observation = capture.localObservation();
                    return observation.complete && observation.timings && observation.timings->snapshot == observation.value; }));
                if (mode < 2) {
                    const auto recoveredBefore = snapshot(fixture.root / session);
                    assert(capture.openLocalPlayback(session, 17, true) && "verified_owned_degraded_must_be_playable");
                    assert(waitFor([&] { const auto state = capture.localPlaybackObservation();
                        return state.media.ready && state.media.muted && !state.preparing && !state.terminal; }));
                    assert(!capture.authorizeLocalPlayback(16));
                    assert(capture.authorizeLocalPlayback(17));
                    assert(waitFor([&] { const auto state = capture.localPlaybackObservation();
                        return !state.media.paused && state.media.positionSeconds > 0.10; }));
                    assert(capture.pauseLocalPlayback(true));
                    assert(waitFor([&] { return capture.localPlaybackObservation().media.paused; }));
                    assert(capture.seekLocalPlayback(0));
                    assert(waitFor([&] { const auto state = capture.localPlaybackObservation();
                        return !state.media.seeking && state.media.positionSeconds <= 0.01; }));
                    assert(snapshot(fixture.root / session) == recoveredBefore &&
                        NativeCaptureStorageTestPeer::generation(capture) == 2 && !wire.load());
                    if (mode == 0) capture.setAuthSessionToken({}); // Actual auth invalidation, not a test cancellation flag.
                    else capture.closeLocalPlayback();
                    assert(waitFor([&] { return capture.localPlaybackObservation().terminal; }));
                    assert(!capture.authorizeLocalPlayback(17) && !capture.seekLocalPlayback(0));
                    std::fprintf(stderr, "OWNED_DEGRADED mode=%u actual_B=1 fresh_display=1 muted_progress=1 pause_seek=1 package_unchanged=1 queue_generation=2 protected_http=0\n", mode);
                } else assert(!capture.openLocalPlayback(session, 17, true)); // Started output/alias is not playable proof.
            }
            capture.shutdown();
            assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        }
        std::async(std::launch::async, [&] {
            const auto cancel = std::make_shared<std::atomic<bool>>(false);
            auto owner = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(owner.ok());
            assert((*owner.value)->queueGeneration() == 2);
            auto pair = (*owner.value)->readPackage(session, cancel); assert(pair.ok());
            std::fprintf(stderr, "UNFINISHED_RESTART mode=%u actual_phase=%u expected_degraded=%u\n", mode,
                static_cast<unsigned>((*pair.value)->current().phase), mode < 2); std::fflush(stderr);
            if (mode < 2) {
                assert((*pair.value)->current().phase == CustodyPackagePhase::sealedDegraded && "native_startup_must_recover_unfinished_prefix");
                auto proof = LocalRecordingPackage::inspectProtected(fixture.root, *pair.value, session, cancel);
                assert(proof.ok() && (*proof.value)->evidence().integrity == PackageIntegrity::degraded &&
                    (*proof.value)->evidence().trustedPrefixFrames == 100 && (*proof.value)->evidence().durationMs == 1000 &&
                    (*proof.value)->evidence().playback.decodedFrames);
            } else assert((*pair.value)->current().phase == CustodyPackagePhase::capturing);
        }).get();
        assert(snapshot(fixture.root / session / L".custody-v1" / L"canonical") == canonicalBefore && snapshot(fixture.root / L".custody-v1") == queueBefore);
        if (mode >= 2) assert(snapshot(fixture.root) == diskBefore);
        if (mode == 3) { pauseOldPackedRead.store(false); oldPackedPath.clear(); }
        assert(!wire.load() && waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        std::fprintf(stderr, "UNFINISHED_RESTART mode=%u cold=1 owner_A=1 initial_current_A=%u queue_unchanged=1 canonical_unchanged=1 drained=1 device_audio=0 real_network=0\n", mode, mode == 1);
    }
}
void protectedStartOwnerDegradedRestart() {
    Fixture fixture;
    constexpr std::string_view session = "44444444-4444-4444-8444-444444444444";
    constexpr std::string_view user = "11111111-1111-4111-8111-111111111111";
    constexpr std::string_view workspace = "22222222-2222-4222-8222-222222222222";
    std::async(std::launch::async, [&] {
        const auto cancel = std::make_shared<std::atomic<bool>>(false);
        auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(opened.ok());
        auto owner = std::move(*opened.value);
        auto initial = owner->readQueueValue(cancel); assert(initial.ok() && owner->queueGeneration() == 1);
        auto candidate = std::allocate_shared<ProtectedUploadQueueValue>(CustodyAllocator<ProtectedUploadQueueValue>{}, **initial.value);
        const auto prepared = owner->prepareRecordingReservation(*candidate, session, user, workspace, true, 1000, cancel);
        assert(prepared.ok() && *prepared.value);
        auto bytes = candidate->serialize(cancel); assert(bytes.ok());
        const auto saved = commitProtectedCustodyMetadata(owner, owner->queueContext(), 1, *bytes.value, cancel);
        assert(saved.state == CustodyCommitState::committed && saved.targetGeneration == 2);
        auto writer = V5LocalRecordingWriter::open(owner, session, cancel); assert(writer.ok());
        CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
        for (unsigned i = 0; i != 100; ++i) {
            frame.ptsFrames = static_cast<std::int64_t>(i) * 480;
            assert((*writer.value)->append(frame));
        }
        const auto result = (*writer.value)->finalize(ReasonCode::clockDiscontinuity, RecordingStopReason::interruption);
        assert(!result.normalPackage() && result.semanticVerified && result.trustedPrefixRetained &&
            result.packagePhase == CustodyPackagePhase::sealedDegraded && result.durationMs == 1000 &&
            result.captureFailure == ReasonCode::clockDiscontinuity);
        // Crash before finishRecordingReservation: release all native owners,
        // preserving the original Start row and the genuinely sealed prefix.
    }).get();
    const auto verifyCold = [&] {
        std::async(std::launch::async, [&] {
            const auto cancel = std::make_shared<std::atomic<bool>>(false);
            auto owner = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(owner.ok());
            assert((*owner.value)->queueGeneration() == 2);
            const auto value = (*owner.value)->readQueueValue(cancel); assert(value.ok() && (*value.value)->items().size() == 1);
            const auto& row = (*value.value)->items()[0];
            assert(row.status == UploadQueueStatus::quarantined && row.safeReason == "capture_prepared" &&
                std::string_view(row.localRecordingId) == session && row.directoryId == row.localRecordingId &&
                row.sessionId == row.localRecordingId && std::string_view(row.packageDirectory) == (fixture.root / session).u8string() &&
                std::string_view(row.ownerUserId) == user && std::string_view(row.ownerWorkspaceId) == workspace &&
                !hasUploadServerIdentity(row) && !(*value.value)->deletionBlocks(row));
            auto pair = (*owner.value)->readPackage(session, cancel); assert(pair.ok());
            assert((*pair.value)->current().phase == CustodyPackagePhase::sealedDegraded &&
                (*pair.value)->current().reason == ReasonCode::clockDiscontinuity);
            const auto proof = LocalRecordingPackage::inspectProtected(fixture.root, *pair.value, session, cancel);
            assert(proof.ok() && (*proof.value)->evidence().integrity == PackageIntegrity::degraded &&
                (*proof.value)->evidence().trustedPrefixFrames == 100 && (*proof.value)->evidence().durationMs == 1000);
        }).get();
    };
    verifyCold();
    assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
    const auto baseline = CustodyOwnedMemory::usedBytes();
    const auto diskBefore = snapshot(fixture.root); // Includes BOTH queue/bootstrap and every package file.
    const auto observations = recoveryReadyObservations.load(std::memory_order_acquire);
    std::atomic<unsigned> accountCalls{0}, wire{0};
    {
        const DesktopHttpTransport::UploadSend accountWire = [&](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
            ++accountCalls;
            assert(request.method == "GET");
            if (request.path == "/desktop/settings/spaces")
                return {200, R"({"spaces":[{"id":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb","active":true}]})"};
            assert(request.path == "/api/v1/auth/me");
            return {200, R"({"user_id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","workspace_id":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
        };
        NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), true}, accountWire,
            [&](const auto&, const auto&) { ++wire; return DesktopHttpTransport::ProtectedUploadResponse{503, "{}"}; });
        capture.setAuthSessionToken("generated-degraded-restart-owner-B");
        assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
        assert(accountCalls == 2 && capture.currentAccount()->userId == "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" &&
            capture.currentAccount()->workspaceId == "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb");
        capture.startStorageValidation();
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::ready(capture); }));
        assert(NativeCaptureStorageTestPeer::opened(capture));
        NativeCaptureStorageTestPeer::pollStorage(capture); // Real startup ACK, not an upload/scheduler command.
        assert(waitFor([&] {
            NativeCaptureStorageTestPeer::pollStorage(capture);
            if (recoveryReadyObservations.load(std::memory_order_acquire) != observations + 1) return false;
            const auto work = NativeCaptureStorageTestPeer::storageWork(capture);
            std::lock_guard<std::mutex> lock(work->mutex);
            return work->adopted && work->generation == 2 && !work->stop && !work->queueFailed &&
                work->error == CustodyFileError::none && !work->recoveryCancellation && !work->inFlight &&
                !work->recording && !work->commandReady;
        }));
        assert(NativeCaptureStorageTestPeer::generation(capture) == 2 &&
            NativeCaptureStorageTestPeer::workerTicket(capture).id == 0 && !NativeCaptureStorageTestPeer::prepared(capture) &&
            !capture.indicator().visible && !std::filesystem::exists(fixture.root / capture.sessionId()));
        const auto value = NativeCaptureStorageTestPeer::projection(capture);
        assert(value && value->items().size() == 1 && value->items()[0].status == UploadQueueStatus::quarantined &&
            value->items()[0].safeReason == "capture_prepared" && std::string_view(value->items()[0].ownerUserId) == user);
        assert(!capture.openLocalPlayback(session, 17, true));
        assert(!capture.requestProtectedManualSend(value, session, capture.authGeneration(), true));
        assert(!wire.load() && NativeCaptureStorageTestPeer::workerTicket(capture).id == 0);
        capture.shutdown();
        assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
    }
    assert(snapshot(fixture.root) == diskBefore && !wire.load());
    verifyCold();
    assert(snapshot(fixture.root) == diskBefore);
    assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
    std::fputs("START_RECOVERY_DEGRADED actual_attempt_drained=1 healthy_worker=1 generation=2 owner_A=1 current_B=1 no_mutation_ticket=1 cold_prefix_frames=100 disk_unchanged=1 exact_memory=1 device_audio=0 protected_http=0 real_network=0\n", stderr);
}
void protectedRecoveryLivePlayback(bool unfinished = false, unsigned finishMode = 0) {
    const bool stopBeforeRelease = finishMode != 0, ambiguousFinish = finishMode == 2;
    assert(finishMode <= 2 && (!stopBeforeRelease || unfinished));
    Fixture fixture;
    constexpr std::string_view old = "44444444-4444-4444-8444-444444444444";
    constexpr std::string_view neighbor = "55555555-5555-4555-8555-555555555555";
    constexpr std::string_view user = "11111111-1111-4111-8111-111111111111";
    constexpr std::string_view workspace = "22222222-2222-4222-8222-222222222222";
    std::async(std::launch::async, [&] {
        const auto cancel = std::make_shared<std::atomic<bool>>(false);
        auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(opened.ok());
        auto owner = std::move(*opened.value);
        for (const auto session : {old, neighbor}) {
            auto current = owner->readQueueValue(cancel); assert(current.ok());
            auto candidate = std::allocate_shared<ProtectedUploadQueueValue>(CustodyAllocator<ProtectedUploadQueueValue>{}, **current.value);
            const auto prepared = owner->prepareRecordingReservation(*candidate, session, user, workspace, true, 1000, cancel);
            assert(prepared.ok() && *prepared.value);
            auto bytes = candidate->serialize(cancel); assert(bytes.ok());
            auto saved = commitProtectedCustodyMetadata(owner, owner->queueContext(), owner->queueGeneration(), *bytes.value, cancel);
            assert(saved.state == CustodyCommitState::committed);
            if (unfinished && session == old) {
                auto package = owner->createPackage(session, cancel); assert(package.ok());
                auto canonical = (*package.value)->createWriter(CustodyRole::canonical); assert(canonical.ok());
                std::array<float, 100 * 480> samples{}; samples.fill(0.25F);
                assert((*canonical.value)->writeAt(0, samples.data(), sizeof(samples)).ok());
                assert((*canonical.value)->checkpoint().state == CustodyCommitState::committed);
                continue;
            }
            auto writer = V5LocalRecordingWriter::open(owner, std::string(session), cancel); assert(writer.ok());
            CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
            for (unsigned i = 0; i != 100; ++i) {
                frame.ptsFrames = static_cast<std::int64_t>(i) * 480;
                assert((*writer.value)->append(frame));
            }
            const auto result = (*writer.value)->finalize(ReasonCode::none, RecordingStopReason::interruption);
            assert(result.normalPackage() && result.durationMs == 1000);
            writer.value->reset();
            if (session == neighbor) {
                auto reservation = owner->readQueueValue(cancel); assert(reservation.ok());
                candidate = std::allocate_shared<ProtectedUploadQueueValue>(CustodyAllocator<ProtectedUploadQueueValue>{}, **reservation.value);
                const auto finished = owner->finishRecordingReservation(*candidate, **reservation.value, session, result, 2000, cancel);
                assert(finished.ok() && *finished.value);
                bytes = candidate->serialize(cancel); assert(bytes.ok());
                const auto finishedCommit = commitProtectedCustodyMetadata(owner, owner->queueContext(), owner->queueGeneration(), *bytes.value, cancel);
                assert(finishedCommit.state == CustodyCommitState::committed);
            } // Old package deliberately has no final queue publication (crash boundary).
        }
        assert(owner->queueGeneration() == 4);
    }).get();
    const auto oldBefore = snapshot(fixture.root / std::string(old));
    const auto canonicalBefore = snapshot(fixture.root / std::string(old) / L".custody-v1" / L"canonical");
    const auto neighborBefore = snapshot(fixture.root / std::string(neighbor));
    oldPackedPath = L"\\\\?\\" + (fixture.root / std::string(old) / L".custody-v1" / L"canonical" / L"content.packed-v2").native();
    { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
    pauseOldPackedRead.store(true);
    const auto observations = recoveryReadyObservations.load(std::memory_order_acquire);
    std::atomic<unsigned> wire{0};
    std::string live;
    {
        const DesktopHttpTransport::UploadSend accountWire = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
            assert(request.method == "GET");
            if (request.path == "/desktop/settings/spaces")
                return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
            assert(request.path == "/api/v1/auth/me");
            return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
        };
        NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), true}, accountWire,
            [&](const auto&, const auto&) { ++wire; return DesktopHttpTransport::ProtectedUploadResponse{503, "{}"}; });
        startAndAdopt(capture, 4);
        assert(waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }));
        capture.setAuthSessionToken("generated-recovery-live-owner-A");
        assert(waitFor([&] { NativeCaptureStorageTestPeer::pollAccount(capture); return capture.currentAccount().has_value(); }));
        assert(capture.currentAccount()->userId == user);
        std::atomic<bool> emit{false};
        CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(capture),
            generatedProducer(capture, emit, AudioSource::systemRender, false, 100),
            generatedProducer(capture, emit, AudioSource::microphone, false, 100));
        ReadinessInputs hardware;
        hardware.microphonePermissionGranted = hardware.microphoneEndpointReady = hardware.renderEndpointReady =
            hardware.formatNormalizationReady = hardware.aecReady = hardware.aacEncoderReady = true;
        live = capture.sessionId();
        assert(NativeCaptureStorageTestPeer::beginPending(capture, hardware).accepted());
        assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture); capture.pollHealth();
            return capture.indicator().state == SessionState::recording; }));
        emit.store(true);
        assert(waitFor([&] { capture.pollHealth(); return NativeCaptureStorageTestPeer::writtenFrames(capture) == 100; }));
        const auto ticket = NativeCaptureStorageTestPeer::workerTicket(capture);
        const auto reserved = NativeCaptureStorageTestPeer::projection(capture);
        assert(ticket.kind == NativeCapture::QueueMutationKind::recording && ticket.baseGeneration == 4 && ticket.targetGeneration == 5);
        const auto finishLive = [&] {
            if (ambiguousFinish) ambiguousRecordingQueue.store(true);
            (void)capture.stop(RecordingStopReason::interruption);
            assert(waitFor([&] { capture.pollHealth(); return NativeCaptureStorageTestPeer::resultReady(capture); }));
            const auto finish = NativeCaptureStorageTestPeer::workerTicket(capture);
            assert(finish.kind == NativeCapture::QueueMutationKind::recording &&
                finish.state == (ambiguousFinish ? NativeCapture::QueueTicketState::ambiguous : NativeCapture::QueueTicketState::committed) &&
                finish.baseGeneration == 5 && finish.targetGeneration == 6);
            assert(!ambiguousRecordingQueue.load() && NativeCaptureStorageTestPeer::projection(capture) == reserved);
            NativeCaptureStorageTestPeer::pollStorage(capture);
            if (ambiguousFinish) {
                assert(waitFor([&] {
                    const auto work = NativeCaptureStorageTestPeer::storageWork(capture);
                    std::lock_guard<std::mutex> lock(work->mutex);
                    return work->commandReconciliation && work->recoveryCancellation && work->recoveryCancellation->load();
                }));
                const auto until = std::chrono::steady_clock::now() + std::chrono::milliseconds(100);
                while (std::chrono::steady_clock::now() < until) {
                    capture.pollHealth();
                    assert(capture.indicator().state != SessionState::savedLocal && !NativeCaptureStorageTestPeer::physicalReadback(capture) &&
                        NativeCaptureStorageTestPeer::projection(capture) == reserved && NativeCaptureStorageTestPeer::generation(capture) == 5 &&
                        !capture.updateWorkDrained() && !wire.load());
                    Sleep(1);
                }
                return; // An ambiguous publish is not Saved, even if the candidate reached disk.
            }
            const bool saved = waitFor([&] { capture.pollHealth(); return capture.indicator().state == SessionState::savedLocal; });
            if (!saved) {
                std::fprintf(stderr, "RECOVERY_LIVE_PLAYBACK failed_save state=%u reason=%u\n",
                    static_cast<unsigned>(capture.indicator().state), static_cast<unsigned>(capture.indicator().reason));
                NativeCaptureStorageTestPeer::diagnosePreparation(capture);
            }
            assert(saved);
        };
        if (stopBeforeRelease) {
            finishLive();
            { std::lock_guard<std::mutex> lock(cutMutex); assert(cutReached && !cutReleased); }
            assert(recoveryReadyObservations.load(std::memory_order_acquire) == observations &&
                NativeCaptureStorageTestPeer::generation(capture) == (ambiguousFinish ? 5 : 6) && !wire.load());
            if (ambiguousFinish) std::fputs("UNFINISHED_FINALIZER actual_queue_ambiguous=1 held_old_read=1 premature_readback=0 saved_success=0 generation=5\n", stderr);
            else std::fputs("UNFINISHED_STOP held_old_read=1 new_eos_commit_adoption=1 generation=6 recovery_result_ready=0 protected_http=0\n", stderr);
        }
        { std::lock_guard<std::mutex> lock(cutMutex); cutReleased = true; }
        cutWake.notify_all();
        assert(waitFor([&] { return recoveryReadyObservations.load(std::memory_order_acquire) == observations + 1; }));
        if (ambiguousFinish) {
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::physicalReadback(capture); }));
            assert(NativeCaptureStorageTestPeer::generation(capture) == 5 && NativeCaptureStorageTestPeer::projection(capture) == reserved);
            NativeCaptureStorageTestPeer::pollStorage(capture);
            assert(waitFor([&] { capture.pollHealth(); return capture.indicator().state == SessionState::failed; }));
            assert(NativeCaptureStorageTestPeer::generation(capture) == 6);
        }
        if (!stopBeforeRelease) {
            assert(capture.indicator().state == SessionState::recording);
            std::fputs("RECOVERY_LIVE_PLAYBACK actual_result_ready=1 live_recording=1 generation=5\n", stderr);
            std::fflush(stderr);
            assert(!capture.openLocalPlayback(live, 17, true)); // Active reservation never becomes playback authority.
            assert(capture.openLocalPlayback(std::string(neighbor), 17, true));
            assert(waitFor([&] { const auto state = capture.localPlaybackObservation();
                return state.media.ready && state.media.muted && !state.preparing && !state.terminal; }));
            assert(capture.authorizeLocalPlayback(17));
            const bool played = waitFor([&] { const auto state = capture.localPlaybackObservation();
                return !state.media.paused && state.media.positionSeconds > 0.10; });
            if (!played) {
                const auto state = capture.localPlaybackObservation();
                std::fprintf(stderr, "RECOVERY_LIVE_PLAYBACK failed_play ready=%u paused=%u terminal=%u seeking=%u position=%f duration=%f error=%08lx\n",
                    state.media.ready, state.media.paused, state.terminal, state.media.seeking,
                    state.media.positionSeconds, state.media.durationSeconds, static_cast<unsigned long>(state.media.error));
                NativeCaptureStorageTestPeer::diagnosePreparation(capture);
            }
            assert(played);
            assert(capture.pauseLocalPlayback(true));
            assert(waitFor([&] { return capture.localPlaybackObservation().media.paused; }));
            assert(capture.seekLocalPlayback(0));
            assert(waitFor([&] { const auto state = capture.localPlaybackObservation();
                return !state.media.seeking && state.media.positionSeconds <= 0.01; }));
            assert(NativeCaptureStorageTestPeer::workerTicket(capture).id == ticket.id &&
                NativeCaptureStorageTestPeer::generation(capture) == 5 && NativeCaptureStorageTestPeer::projection(capture) == reserved &&
                capture.indicator().state == SessionState::recording && NativeCaptureStorageTestPeer::writtenFrames(capture) == 100 && !wire.load());
            capture.closeLocalPlayback();
            assert(waitFor([&] { return capture.localPlaybackObservation().terminal; }));
            std::fputs("RECOVERY_LIVE_PLAYBACK muted_play_seek=1 stale_command=0 live_unchanged=1 protected_http=0\n", stderr);
            finishLive();
        }
        if (!unfinished) {
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); }));
            const auto recovery = NativeCaptureStorageTestPeer::workerTicket(capture);
            assert(recovery.kind == NativeCapture::QueueMutationKind::recovery && recovery.state == NativeCapture::QueueTicketState::committed &&
                recovery.baseGeneration == 6 && recovery.targetGeneration == 7);
            NativeCaptureStorageTestPeer::pollStorage(capture);
        }
        assert(NativeCaptureStorageTestPeer::generation(capture) == (unfinished ? 6 : 7));
        capture.shutdown();
        assert(waitFor([&] { NativeCaptureStorageTestPeer::pollStorage(capture); return capture.shutdownWorkDrained(); }));
    }
    pauseOldPackedRead.store(false); oldPackedPath.clear();
    std::async(std::launch::async, [&] {
        const auto cancel = std::make_shared<std::atomic<bool>>(false);
        const auto owner = ProtectedCustodyStoreOwner::open(fixture.root, cancel);
        assert(owner.ok() && (*owner.value)->queueGeneration() == (unfinished ? 6 : 7));
        const auto value = (*owner.value)->readQueueValue(cancel); assert(value.ok() && (*value.value)->items().size() == 3);
        for (const auto& row : (*value.value)->items()) {
            assert((std::string_view(row.localRecordingId) == old || std::string_view(row.localRecordingId) == neighbor ||
                std::string_view(row.localRecordingId) == live) && row.directoryId == row.localRecordingId && row.sessionId == row.localRecordingId &&
                std::string_view(row.ownerUserId) == user && std::string_view(row.ownerWorkspaceId) == workspace &&
                row.status == (unfinished && std::string_view(row.localRecordingId) == old ? UploadQueueStatus::quarantined : UploadQueueStatus::pending) &&
                row.safeReason == (unfinished && std::string_view(row.localRecordingId) == old ? "capture_prepared" : "") && !hasUploadServerIdentity(row));
        }
        if (unfinished) {
            auto pair = (*owner.value)->readPackage(old, cancel); assert(pair.ok());
            if (ambiguousFinish) assert((*pair.value)->current().phase == CustodyPackagePhase::capturing);
            else {
                auto proof = LocalRecordingPackage::inspectProtected(fixture.root, *pair.value, old, cancel);
                assert(proof.ok() && (*proof.value)->evidence().integrity == PackageIntegrity::degraded &&
                    (*proof.value)->evidence().durationMs == 1000);
            }
        }
        if (stopBeforeRelease) {
            auto pair = (*owner.value)->readPackage(live, cancel); assert(pair.ok());
            auto proof = LocalRecordingPackage::inspectProtected(fixture.root, *pair.value, live, cancel);
            assert(proof.ok() && (*proof.value)->evidence().integrity == PackageIntegrity::valid &&
                (*proof.value)->evidence().durationMs == 1000 && (*proof.value)->evidence().playback.decodedFrames);
        }
    }).get();
    assert(!wire.load() && (unfinished && !ambiguousFinish ? snapshot(fixture.root / std::string(old) / L".custody-v1" / L"canonical") == canonicalBefore :
        snapshot(fixture.root / std::string(old)) == oldBefore) &&
        snapshot(fixture.root / std::string(neighbor)) == neighborBefore);
    assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
    if (!stopBeforeRelease) std::fputs("RECOVERY_LIVE_PLAYBACK eos_finish_recovery=1 cold_three_owned_rows=1 exact_memory=1 device_audio=0 real_network=0\n", stderr);
    if (unfinished && !stopBeforeRelease) std::fputs("UNFINISHED_LIVE_PLAYBACK held_old_read=1 concurrent_start_frames_stop_eos=1 old_degraded=1 old_queue_quarantined=1\n", stderr);
    if (ambiguousFinish) std::fputs("UNFINISHED_FINALIZER actual_recovery_retirement=1 readback_ack=1 cold_generation=6 cold_new_valid_decode=1 old_capturing_unchanged=1 saved_success=0 exact_memory=1 protected_http=0 device_audio=0 real_network=0\n", stderr);
    else if (stopBeforeRelease) std::fputs("UNFINISHED_STOP cold_three_owned_rows=1 new_saved_before_old_release=1 old_degraded=1 canonical_unchanged=1 exact_memory=1\n", stderr);
}
void protectedStartOwnerFinalization(bool noLoginClaim = false, unsigned claimScenario = 0) {
    const auto baseline = CustodyOwnedMemory::usedBytes();
    bool claimAdmitted = true;
    for (unsigned mode = noLoginClaim ? 3 : 0; mode != (noLoginClaim ? 4U : 3U); ++mode) {
        Fixture fixture;
        std::string session;
        {
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), true});
            startAndAdopt(capture, 1);
            if (noLoginClaim) capture.setAuthSessionToken({}, true); // Accepted signed-out observation before Start, not missing ownership.
            session = capture.sessionId();
            std::atomic<bool> emit{false};
            CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(capture),
                generatedProducer(capture, emit, AudioSource::systemRender, false, 100),
                generatedProducer(capture, emit, AudioSource::microphone, false, 100));
            ReadinessInputs hardware;
            hardware.microphonePermissionGranted = hardware.microphoneEndpointReady = hardware.renderEndpointReady =
                hardware.formatNormalizationReady = hardware.aecReady = hardware.aacEncoderReady = true;
            assert(NativeCaptureStorageTestPeer::beginPending(capture, hardware).accepted());
            assert(waitFor([&] { capture.pollUploads(); capture.pollHealth(); return capture.indicator().state == SessionState::recording; }));
            const auto reserved = NativeCaptureStorageTestPeer::projection(capture);
            assert(reserved && reserved->items().size() == 1 && reserved->items()[0].safeReason ==
                (noLoginClaim ? "capture_prepared" : "capture_owner_unknown"));
            emit.store(true);
            assert(waitFor([&] { capture.pollHealth(); return NativeCaptureStorageTestPeer::writtenFrames(capture) == 100; }));
            if (mode == 1) ambiguousRecordingQueue.store(true);
            if (mode == 2) (void)capture.stop();
            else (void)capture.stop(RecordingStopReason::interruption);
            assert(waitFor([&] { capture.pollHealth(); return NativeCaptureStorageTestPeer::resultReady(capture); }));
            const auto ticket = NativeCaptureStorageTestPeer::workerTicket(capture);
            assert(ticket.baseGeneration == 2 && ticket.targetGeneration == 3 &&
                ticket.state == (mode == 1 ? NativeCapture::QueueTicketState::ambiguous : NativeCapture::QueueTicketState::committed));
            assert(!ambiguousRecordingQueue.load() && NativeCaptureStorageTestPeer::projection(capture) == reserved);
            assert(std::filesystem::exists(fixture.root / session) && capture.indicator().state == SessionState::finalizing);
            capture.pollUploads();
            if (mode == 1) {
                assert(waitFor([&] { return NativeCaptureStorageTestPeer::physicalReadback(capture); }));
                assert(!capture.updateWorkDrained()); // Retain the operation until actual readback adoption.
                capture.pollUploads();
            }
            assert(waitFor([&] {
                capture.pollHealth();
                return capture.indicator().state == (mode == 1 ? SessionState::failed : mode == 2 ? SessionState::blocked : SessionState::savedLocal);
            }));
            assert(capture.finalization().shortRecordingDiscarded == (mode == 2));
            capture.shutdown();
            assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
        }
        std::async(std::launch::async, [&] {
            const auto cancellation = std::make_shared<std::atomic<bool>>(false);
            auto owner = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(owner.ok());
            assert((*owner.value)->queueGeneration() == 3);
            const auto value = (*owner.value)->readQueueValue(cancellation); assert(value.ok());
            if (mode == 2) assert((*value.value)->items().empty() && !std::filesystem::exists(fixture.root / session));
            else {
                assert((*value.value)->items().size() == 1);
                const auto& row = (*value.value)->items().front();
                assert(row.safeReason == (noLoginClaim ? "capture_prepared" : "capture_owner_unknown") && row.status == UploadQueueStatus::quarantined &&
                    row.ownerUserId.empty() && row.ownerWorkspaceId.empty() && !hasUploadServerIdentity(row));
                const auto pair = (*owner.value)->readPackage(session, cancellation); assert(pair.ok());
                const auto proof = LocalRecordingPackage::inspectProtected(fixture.root, *pair.value, session, cancellation);
                assert(proof.ok() && (*proof.value)->evidence().integrity == PackageIntegrity::valid);
            }
        }).get();
        if (noLoginClaim) {
            std::atomic<unsigned> networkCalls{0};
            const DesktopHttpTransport::UploadSend accountWire = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
                if (request.path == "/desktop/settings/spaces") return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
                assert(request.path == "/api/v1/auth/me");
                return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
            };
            const DesktopHttpTransport::ProtectedUploadSend wire = [&](const auto&, const auto& request) {
                assert(request.method == "GET" && request.path.find("/sync-state?") != std::string_view::npos);
                ++networkCalls;
                return DesktopHttpTransport::ProtectedUploadResponse{503, "{}"};
            };
            const auto originalPackage = snapshot(fixture.root / session);
            NativeCapture cold(fixture.root, {std::make_shared<GeneratedAec>(), true}, accountWire, wire);
            startAndAdopt(cold, 3);
            cold.setAuthSessionToken("generated-no-login-claim");
            assert(waitFor([&] {
                NativeCaptureStorageTestPeer::pollAccount(cold); cold.pollUploads();
                return cold.currentAccount().has_value() && cold.localObservation().complete && !cold.uploadsBusy() &&
                    NativeCaptureStorageTestPeer::displayFinished(cold);
            }));
            const auto before = cold.localObservation().value;
            assert(before && before->items().size() == 1 && before->items()[0].safeReason == "capture_prepared" &&
                before->items()[0].status == UploadQueueStatus::quarantined && before->items()[0].ownerUserId.empty() &&
                before->items()[0].ownerWorkspaceId.empty() && !hasUploadServerIdentity(before->items()[0]) && networkCalls == 0);
            assert(isPreparedUnownedRecording(before->items()[0]) && before->canManualSend(0,
                cold.currentAccount()->userId, cold.currentAccount()->workspaceId, true));
            assert(!cold.requestProtectedManualSend(before, session, cold.authGeneration(), false));
            const bool holdProof = claimScenario == 1 || claimScenario == 2 || claimScenario >= 4;
            if (holdProof) {
                oldPackedPath = L"\\\\?\\" + (fixture.root / session / L".custody-v1" / L"canonical" / L"content.packed-v2").native();
                { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
                pauseOldPackedRead.store(true);
            }
            const auto pending = cold.requestProtectedManualSend(before, session, cold.authGeneration(), true);
            const bool admitted = pending.has_value();
            std::fprintf(stderr, "NO_LOGIN_CLAIM genuine_start=1 reservation_ack=1 generated_frames=100 normal_finish=1 cold_inspection=1 verified_account=1 no_implicit_claim=1 admitted=%u http_before_ack=%u\n",
                admitted ? 1U : 0U, networkCalls.load());
            std::fflush(stderr);
            if (pending) {
                if (holdProof) {
                    assert(waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }));
                    assert(!NativeCaptureStorageTestPeer::resultReady(cold) && cold.localObservation().value == before && networkCalls == 0);
                    if (claimScenario == 1) cold.cancelProtectedManualSend(pending->id);
                    if (claimScenario == 2) cold.setAuthSessionToken({});
                    if (claimScenario >= 4) {
                        std::atomic<bool> emit{false};
                        CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(cold),
                            generatedProducer(cold, emit, AudioSource::systemRender, false, 100),
                            generatedProducer(cold, emit, AudioSource::microphone, false, 100));
                        ReadinessInputs hardware;
                        hardware.microphonePermissionGranted = hardware.microphoneEndpointReady = hardware.renderEndpointReady =
                            hardware.formatNormalizationReady = hardware.aecReady = hardware.aacEncoderReady = true;
                        assert(NativeCaptureStorageTestPeer::beginPending(cold, hardware).accepted());
                        assert(waitFor([&] { cold.pollUploads(); cold.pollHealth(); return cold.indicator().state == SessionState::recording; }));
                        emit.store(true);
                        assert(waitFor([&] { cold.pollHealth(); return NativeCaptureStorageTestPeer::writtenFrames(cold) == 100; }));
                        if (claimScenario == 5) ambiguousRecordingQueue.store(true);
                        assert(cold.stop(RecordingStopReason::interruption).accepted());
                        if (claimScenario == 5) {
                            assert(waitFor([&] { cold.pollHealth(); return NativeCaptureStorageTestPeer::resultReady(cold); }));
                            assert(NativeCaptureStorageTestPeer::workerTicket(cold).state == NativeCapture::QueueTicketState::ambiguous &&
                                !ambiguousRecordingQueue.load());
                            cold.pollUploads();
                            assert(waitFor([&] {
                                const auto work = NativeCaptureStorageTestPeer::storageWork(cold);
                                std::lock_guard<std::mutex> lock(work->mutex);
                                return work->commandReconciliation && work->recoveryCancellation && work->recoveryCancellation->load();
                            }));
                            assert(!NativeCaptureStorageTestPeer::physicalReadback(cold));
                        } else {
                            assert(waitFor([&] { cold.pollUploads(); cold.pollHealth(); return cold.indicator().state == SessionState::savedLocal; }));
                            assert(cold.localObservation().value->items().size() == 2);
                        }
                        assert(networkCalls == 0 &&
                            cold.protectedManualSendTicket(pending->id)->state == NativeCapture::QueueTicketState::pending);
                        std::fprintf(stderr, "NO_LOGIN_CLAIM concurrent_start_frames_stop_eos_before_proof=1 ambiguous=%u\n", claimScenario == 5 ? 1U : 0U);
                    }
                    { std::lock_guard<std::mutex> lock(cutMutex); assert(cutReached && !cutReleased); cutReleased = true; }
                    cutWake.notify_all();
                }
                const bool bound = claimScenario == 0 || claimScenario == 3 || claimScenario == 4;
                if (bound) {
                    assert(waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(cold); }));
                    assert((claimScenario == 4 || NativeCaptureStorageTestPeer::projection(cold) == before) && networkCalls == 0);
                    if (claimScenario == 3) cold.cancelProtectedManualSend(pending->id); // Actual committed bytes, before UI ACK.
                    cold.pollUploads();
                }
                const bool expectedHttp = claimScenario == 0 || claimScenario == 4;
                assert(waitFor([&] {
                    cold.pollUploads(); cold.pollHealth();
                    return networkCalls.load() == (expectedHttp ? 1U : 0U) && !cold.uploadsBusy() &&
                        cold.protectedManualSendTicket(pending->id)->state != NativeCapture::QueueTicketState::pending &&
                        (claimScenario != 5 || cold.indicator().state == SessionState::failed);
                }));
                const auto ticket = cold.protectedManualSendTicket(pending->id);
                const auto after = cold.localObservation().value;
                assert(ticket && ticket->state == (bound ? NativeCapture::QueueTicketState::committed : NativeCapture::QueueTicketState::notCommitted));
                assert(after && after->items().size() == (claimScenario >= 4 ? 2U : 1U));
                if (bound) assert(ticket->error == CustodyFileError::none && after != before &&
                    after->items()[0].ownerUserId == "11111111-1111-4111-8111-111111111111" &&
                    after->items()[0].ownerWorkspaceId == "22222222-2222-4222-8222-222222222222");
                else assert(after->items()[0].ownerUserId.empty() && after->items()[0].ownerWorkspaceId.empty());
                assert(snapshot(fixture.root / session) == originalPackage);
            }
            cold.shutdown();
            assert(waitFor([&] { cold.pollUploads(); return cold.shutdownWorkDrained(); }));
            if (admitted) std::async(std::launch::async, [&] {
                const auto cancellation = std::make_shared<std::atomic<bool>>(false);
                const auto owner = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(owner.ok());
                const auto value = (*owner.value)->readQueueValue(cancellation); assert(value.ok() && (*value.value)->items().size() == (claimScenario >= 4 ? 2U : 1U));
                const auto& row = (*value.value)->items()[0];
                assert(std::string_view(row.sessionId) == session && row.localRecordingId == row.directoryId && row.directoryId == row.sessionId &&
                    row.ownerUserId == (claimScenario == 1 || claimScenario == 2 || claimScenario == 5 ? "" : "11111111-1111-4111-8111-111111111111") &&
                    row.ownerWorkspaceId == (claimScenario == 1 || claimScenario == 2 || claimScenario == 5 ? "" : "22222222-2222-4222-8222-222222222222"));
                const auto pair = (*owner.value)->readPackage(session, cancellation); assert(pair.ok());
                const auto proof = LocalRecordingPackage::inspectProtected(fixture.root, *pair.value, session, cancellation);
                assert(proof.ok() && (*proof.value)->evidence().integrity == PackageIntegrity::valid);
            }).get();
            pauseOldPackedRead.store(false); oldPackedPath.clear();
            std::fprintf(stderr, "NO_LOGIN_CLAIM scenario=%u cold_exact_owner=1 original_package_unchanged=1 protected_http=%u\n", claimScenario, networkCalls.load());
            claimAdmitted = admitted; // Defer the target assertion until native owners and the generated fixture have drained.
        }
        // All cached plaintext, proxies and native owners must drain to the cold baseline.
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        std::fprintf(stderr, "START_OWNER finalize=%u cold=1 exact_row=1 device_audio=0 real_network=0 live=%zu entry=%zu empty_cache=%zu\n",
            mode, CustodyOwnedMemory::usedBytes(), baseline, idleOwnedBytes);
    }
    assert(claimAdmitted); // Genuine signed-out Start must accept explicit claim, never an ordinary pending surrogate.
}
void protectedNativeShortDiscard() {
    for (unsigned mode = 0; mode != 10; ++mode) {
        Fixture fixture;
        std::string session;
        {
            auto owned = std::make_unique<NativeCapture>(fixture.root,
                AecSelection{std::make_shared<GeneratedAec>(), true});
            auto& capture = *owned;
            capture.notificationCard().setQuiet(true); // History proves handoff, not a forced native presentation.
            unsigned sounds = 0;
            capture.onShortRecordingPresented = [&] { ++sounds; };
            startAndAdopt(capture, 1);
            const auto retainedStorage = NativeCaptureStorageTestPeer::storageWork(capture);
            const auto abandonAndDrain = [&] {
                owned.reset();
                assert(waitFor([&] {
                    std::lock_guard<std::mutex> lock(retainedStorage->mutex);
                    return retainedStorage->terminal;
                })); // Destructor hands off; the actual worker must release its active lease.
            };
            session = capture.sessionId();
            auto before = NativeCaptureStorageTestPeer::projection(capture);
            std::atomic<bool> emit{false};
            CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(capture),
                generatedProducer(capture, emit, AudioSource::systemRender, false, 100),
                generatedProducer(capture, emit, AudioSource::microphone, false, 100));
            ReadinessInputs hardware;
            hardware.microphonePermissionGranted = hardware.microphoneEndpointReady = hardware.renderEndpointReady =
                hardware.formatNormalizationReady = hardware.aecReady = hardware.aacEncoderReady = true;
            assert(NativeCaptureStorageTestPeer::beginPending(capture, hardware).accepted());
            assert(waitFor([&] { capture.pollUploads(); capture.pollHealth(); return capture.indicator().state == SessionState::recording; }));
            before = NativeCaptureStorageTestPeer::projection(capture);
            assert(NativeCaptureStorageTestPeer::generation(capture) == 2 && before->items().size() == 1 &&
                std::string_view(before->items().front().sessionId) == session &&
                before->items().front().status == UploadQueueStatus::quarantined &&
                before->items().front().safeReason == "capture_owner_unknown");
            emit.store(true);
            assert(waitFor([&] {
                capture.pollHealth(); return NativeCaptureStorageTestPeer::writtenFrames(capture) == 100;
            }));
            const auto path = fixture.root / session;
            winrt::handle held;
            nativeShortAttempts.store(0);
            if (mode == 2 || mode >= 7) { nativeShortEffects.store(0); nativeShortCut.store(true); }
            (void)capture.stop();
            assert(waitFor([&] {
                capture.pollHealth(); return NativeCaptureStorageTestPeer::resultReady(capture);
            }));
            const auto retirement = NativeCaptureStorageTestPeer::workerTicket(capture);
            assert(retirement.kind == NativeCapture::QueueMutationKind::recording &&
                retirement.state == NativeCapture::QueueTicketState::committed &&
                retirement.baseGeneration == 2 && retirement.targetGeneration == 3 && retirement.error == CustodyFileError::none);
            assert(NativeCaptureStorageTestPeer::projection(capture) == before && std::filesystem::exists(path) &&
                nativeShortAttempts.load() == 0 && capture.notificationCard().history().empty() && sounds == 0 &&
                capture.indicator().state == SessionState::finalizing && !capture.updateWorkDrained());
            // Hold the package only after genuine short proof/retirement commit,
            // before its adoption permits the existing physical discard.
            if (mode == 1) {
                held.attach(CreateFileW(path.c_str(), FILE_READ_ATTRIBUTES | FILE_LIST_DIRECTORY, FILE_SHARE_READ,
                    nullptr, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
                assert(held);
            }
            capture.pollUploads(); // Retirement ACK precedes every OS attempt.
            if (mode == 1 || mode == 2 || mode >= 7) {
                assert(waitFor([&] {
                    const auto work = NativeCaptureStorageTestPeer::storageWork(capture);
                    std::lock_guard<std::mutex> lock(work->mutex);
                    return work->shortDiscardPending;
                }));
                assert(capture.indicator().state == SessionState::finalizing && capture.indicator().visible);
                assert(capture.notificationCard().history().empty() && !capture.finalization().shortRecordingDiscarded);
                assert(std::filesystem::exists(path) == (mode == 1));
                held.close();
                if (mode == 7) {
                    shortReadFailures.store(0); denyDeletionReadback.store(true);
                    capture.setUpdateAdmissionBlocked(true);
                    assert(waitFor([&] { return shortReadFailures.load() > 0; }));
                    assert(!capture.updateWorkDrained() && !NativeCaptureStorageTestPeer::resultReady(capture));
                    WindowsDesktopSession second("cannot-overtake-unresolved-short");
                    assert(second.beginReadinessCheck().reason == ReasonCode::activeSessionExists);
                    denyDeletionReadback.store(false);
                    capture.recover(RecoveryTrigger::scheduled); // Readback still allowed after update admission closed.
                } else if (mode == 8) capture.shutdown();
                else if (mode == 9) abandonAndDrain();
                else capture.recover(RecoveryTrigger::scheduled);
                if (mode == 1) {
                    const auto work = NativeCaptureStorageTestPeer::storageWork(capture);
                    assert(waitFor([&] {
                        std::lock_guard<std::mutex> lock(work->mutex);
                        return work->resultReady || (work->shortDiscardPending && !work->reconcileRequested);
                    }));
                    // An attempted-but-refused Shell first needs read-only
                    // reconciliation, then a distinct explicit retry.
                    capture.recover(RecoveryTrigger::scheduled);
                }
            }
            if (owned) {
            assert(waitFor([&] {
                return NativeCaptureStorageTestPeer::recordingTerminal(capture);
            }));
            assert(!std::filesystem::exists(path));
            if (mode < 7) assert(capture.indicator().state == SessionState::finalizing && !capture.updateWorkDrained());
            assert(capture.notificationCard().history().empty() && sounds == 0);
            assert(NativeCaptureStorageTestPeer::projection(capture) != before &&
                NativeCaptureStorageTestPeer::projection(capture)->items().empty() &&
                NativeCaptureStorageTestPeer::generation(capture) == 3);
            WindowsDesktopSession second("cannot-overtake-short-adoption");
            if (mode < 7) assert(second.beginReadinessCheck().reason == ReasonCode::activeSessionExists);
            if (mode == 3) { capture.setAuthSessionToken("generated-stale"); capture.setAuthSessionToken({}); }
            if (mode == 4) capture.setUpdateAdmissionBlocked(true);
            if (mode == 5) capture.requestShutdown();
            if (mode == 6) abandonAndDrain(); // Actual lost-poll drain; no terminal UI callback.
            else {
                capture.pollUploads();
                assert(waitFor([&] {
                    capture.pollHealth();
                    return capture.indicator().state == (mode >= 3 ? SessionState::failed : SessionState::blocked);
                }));
                assert(capture.finalization().shortRecordingDiscarded == (mode < 3));
                for (unsigned i = 0; i != 3; ++i) { capture.pollHealth(); capture.pollUploads(); }
                assert(capture.notificationCard().history().size() == (mode < 3 ? 1U : 0U) && sounds == 0);
                const auto ticket = NativeCaptureStorageTestPeer::ticket(capture); assert(ticket);
                assert(ticket->state == NativeCapture::QueueTicketState::committed &&
                    ticket->baseGeneration == 2 && ticket->targetGeneration == 3 && ticket->error == CustodyFileError::none);
                assert(waitFor([&] { return capture.localQueueComplete(); }));
                assert(!capture.recordingReady() && capture.readiness().storageWritable == (mode < 4));
                capture.shutdown();
                assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
                owned.reset();
            }
            assert(second.beginReadinessCheck().accepted());
            assert(second.block(ReasonCode::microphonePermissionDenied).accepted());
            }
            if (mode == 2 || mode >= 7) assert(nativeShortEffects.load() == 1 && !nativeShortCut.load());
        }
        std::async(std::launch::async, [&] {
            auto cancel = std::make_shared<std::atomic<bool>>(false);
            auto owner = ProtectedCustodyStoreOwner::open(fixture.root, cancel); assert(owner.ok());
            auto queue = (*owner.value)->readQueueValue(cancel);
            assert(queue.ok() && (*queue.value)->items().empty() && (*owner.value)->queueGeneration() == 3);
            assert(!std::filesystem::exists(fixture.root / session));
        }).get();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        std::fprintf(stderr, "NATIVE_SHORT mode=%u absence=1 retirement_ack_before_effect=1 terminal_ui_fenced=1 cold=1 audio=0 network=0\n", mode);
    }
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
        bool pinsFull = false, pinnedAck = false;
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
                    {
                        std::array<std::optional<CustodyPin>, 32> pins;
                        for (auto& pin : pins) { pin.emplace(); if (!*pin) { pin.reset(); break; } }
                        const CustodyPin refused;
                        result.pinsFull = !refused;
                        result.pinnedAck = accepted(capture.store->revalidatePackage(*pair.value, capture.cancel));
                    } // Fresh validation of an existing lease needs no new native owner.
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
    std::fprintf(stderr, "PROTECTED_PACKAGE_REVALIDATION pins_full=%u fresh_ack_without_new_pin=%u\n", control.pinsFull, control.pinnedAck);
    assert(control.pinsFull && control.pinnedAck && "retained_revalidation_must_not_allocate_another_native_owner");
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

// A genuine V5 package, a native account/protocol proof, then a released root
// and a fresh offline owner. The cached tuple never becomes network identity.
void protectedOfflineContentContext() {
    const auto cold = CustodyOwnedMemory::usedBytes();
    testing::GeneratedRecordingRoot paths;
    constexpr auto session = "generated-offline-content";
    std::async(std::launch::async, [&] {
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        auto opened = ProtectedCustodyStoreOwner::open(paths.root, cancel); assert(opened.ok());
        auto store = std::move(*opened.value);
        auto created = V5LocalRecordingWriter::open(store, session, cancel); assert(created.ok());
        auto writer = std::move(*created.value);
        CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
        for (unsigned n = 0; n != 500; ++n) { frame.ptsFrames = n * 480; assert(writer->append(frame)); }
        const auto sealed = writer->finalize(ReasonCode::none, RecordingStopReason::interruption);
        assert(sealed.normalPackage() && sealed.semanticVerified); writer.reset();
        auto read = store->readQueueValue(cancel); assert(read.ok());
        auto value = std::allocate_shared<ProtectedUploadQueueValue>(CustodyAllocator<ProtectedUploadQueueValue>{}, **read.value);
        ProtectedUploadQueueValue::Item row;
        row.localRecordingId = row.directoryId = row.sessionId = session;
        const auto path = (paths.root / session).u8string(); row.packageDirectory.assign(path.begin(), path.end());
        row.ownerUserId = "11111111-1111-4111-8111-111111111111";
        row.ownerWorkspaceId = "22222222-2222-4222-8222-222222222222";
        row.status = UploadQueueStatus::uploaded;
        assert(value->enqueue(std::move(row), 1000, cancel.get()));
        const auto expected = value->items().back();
        ProtectedDesktopTransportResult synced; synced.status = DesktopTransportStatus::uploaded;
        synced.serverTruth.emplace(); synced.serverTruth->localRecordingId = expected.localRecordingId;
        synced.serverTruth->meetingId = "66666666-6666-4666-8666-666666666666";
        assert(value->applyUploadResult(expected, synced, 1001, cancel.get()));
        auto bytes = value->serialize(cancel); assert(bytes.ok());
        assert(commitProtectedCustodyMetadata(store, store->queueContext(), store->queueGeneration(), *bytes.value, cancel).state == CustodyCommitState::committed);
    }).get();
    const auto original = snapshot(paths.root / session);
    const auto idle = CustodyOwnedMemory::usedBytes(); assert(idle == idleOwnedBytes);
    const auto gate = R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","recording_deletion_protocol_version":1})";
    const DesktopHttpTransport::UploadSend online = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(request.method == "GET");
        if (request.path == "/desktop/settings/spaces") return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        assert(request.path == "/api/v1/auth/me");
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    };
    const DesktopHttpTransport::ProtectedUploadSend protocol = [&](const auto& config, const auto& request) {
        assert(config.scopedAccount && config.confirmedIdentity);
        DesktopHttpTransport::ProtectedUploadResponse response; response.status = 200;
        if (request.method == "GET") { assert(request.path == DesktopApiClient::notificationContextPath); response.body = gate; }
        else { assert(request.method == "POST" && request.path == DesktopApiClient::lifecyclePath); response.body = lifecycleAnswer(request.body); }
        return response; // No DELETE, purge ACK, devices or real network.
    };
    {
        NativeCapture hot(paths.root, {std::make_shared<GeneratedAec>(), false}, online, protocol);
        startAndAdopt(hot, 2); hot.startRecordingLifecycle();
        hot.setAuthSessionToken("generated-session-1", true);
        const bool committed = waitFor([&] {
            hot.pollUploads(); const auto view = hot.localObservation();
            return view.complete && view.value && view.value->lastAuthenticatedContext() &&
                view.value->items().front().accessState == "owner";
        });
        hot.shutdown(); assert(waitFor([&] { hot.pollUploads(); return hot.shutdownWorkDrained(); }));
        assert(committed && "native_proof_requires_context_commit_and_lifecycle_access_adoption");
    }
    std::uint64_t generation = 0;
    std::async(std::launch::async, [&] {
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        auto opened = ProtectedCustodyStoreOwner::open(paths.root, cancel); assert(opened.ok());
        auto store = std::move(*opened.value); auto read = store->readQueueValue(cancel); assert(read.ok());
        const auto& context = (*read.value)->lastAuthenticatedContext(); assert(context);
        assert(context->serverOrigin == "https://rec.2brain.pro" && context->actorUserId == "11111111-1111-4111-8111-111111111111" &&
            context->workspaceId == "22222222-2222-4222-8222-222222222222");
        // SHA256 of the exact no-BOM/no-newline canonical native request binding.
        assert(context->sessionFingerprint == "946fff3f96fd1088ce97880e40db203396081400100706da863ae07d8abcd0c7");
        generation = store->queueGeneration();
    }).get();
    const auto committedRoot = snapshot(paths.root);
    for (const auto status : {503U, 401U}) {
        const DesktopHttpTransport::UploadSend offline = [=](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
            assert(request.method == "GET" && request.path == "/desktop/settings/spaces"); return {status, "{}"};
        };
        const DesktopHttpTransport::ProtectedUploadSend noProtocol = [](const auto&, const auto&) {
            assert(false && "no_scoped_request_without_fresh_network_identity"); return DesktopHttpTransport::ProtectedUploadResponse{};
        };
        {
            NativeCapture coldOwner(paths.root, {std::make_shared<GeneratedAec>(), false}, offline, noProtocol);
            startAndAdopt(coldOwner, generation); coldOwner.startRecordingLifecycle();
            coldOwner.setAuthSessionToken("generated-session-1");
            assert(!coldOwner.openLocalPlayback(session, 71, true)); // Failed/unread cookie is not observation.
            coldOwner.setAuthSessionToken("generated-session-1", true);
            NativeCaptureStorageTestPeer::pollAccount(coldOwner);
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::accountResultReady(coldOwner); }));
            NativeCaptureStorageTestPeer::pollAccount(coldOwner);
            assert(!coldOwner.currentAccount());
            if (status == 503) {
            assert(waitFor([&] {
                coldOwner.pollUploads(); const auto view = coldOwner.localObservation();
                return view.complete && view.timings && view.timings->rows.size() == 1 &&
                    view.timings->rows.front() && view.timings->rows.front()->durationMs == 5000;
            }) && "offline_display_must_not_starve_behind_network_recovery");
            }
            const bool opened = coldOwner.openLocalPlayback(session, 71, true);
            assert(opened == (status == 503)); // authRequired is never offline success.
            if (opened) {
                assert(waitFor([&] { const auto s = coldOwner.localPlaybackObservation(); return s.media.ready && !s.preparing; }));
                assert(!coldOwner.authorizeLocalPlayback(70));
                assert(coldOwner.authorizeLocalPlayback(71));
                assert(coldOwner.pauseLocalPlayback(true));
                assert(waitFor([&] { return coldOwner.localPlaybackObservation().media.paused; }));
                assert(coldOwner.seekLocalPlayback(2));
                assert(waitFor([&] { const auto s = coldOwner.localPlaybackObservation(); return !s.media.seeking && s.media.positionSeconds >= 1.9; }));
                coldOwner.setAuthSessionToken("different-generated-session", true);
                assert(!coldOwner.seekLocalPlayback(1) && !coldOwner.authorizeLocalPlayback(71));
            }
            coldOwner.shutdown(); assert(waitFor([&] { coldOwner.pollUploads(); return coldOwner.shutdownWorkDrained(); }));
        }
        assert(snapshot(paths.root) == committedRoot);
    }
    assert(snapshot(paths.root / session) == original);
    assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == idle; }));
    (void)cold;
}

void protectedEmptyContextCommit() {
    for (const bool escaped : {false, true}) {
        Fixture fixture;
        const DesktopHttpTransport::UploadSend account = [](const auto&, const auto& request) -> DesktopHttpTransport::UploadResponse {
            assert(request.method == "GET");
            if (request.path == "/desktop/settings/spaces") return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
            assert(request.path == "/api/v1/auth/me");
            return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
        };
        const DesktopHttpTransport::ProtectedUploadSend protocol = [](const auto&, const auto& request) {
            assert(request.method == "GET" && request.path == DesktopApiClient::notificationContextPath);
            DesktopHttpTransport::ProtectedUploadResponse result; result.status = 200;
            result.body = R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","recording_deletion_protocol_version":1})";
            return result;
        };
        {
            NativeCapture capture(fixture.root, {std::make_shared<GeneratedAec>(), false}, account, protocol);
            startAndAdopt(capture, 1); capture.startRecordingLifecycle();
            const std::string token = escaped ? "generated-\"\\\n\t\x01\xc3\xa9" : "generated-session-1";
            capture.setAuthSessionToken(token, true);
            const bool accepted = waitFor([&] { capture.pollUploads(); const auto v = capture.localObservation();
                return v.complete && v.value && v.value->items().empty() && v.value->lastAuthenticatedContext().has_value() &&
                    v.value->lastAuthenticatedContext()->sessionFingerprint == (escaped ? "86abe19ce4b024187192bed073235adf4a205ac2d0ea7649013a128cbf43e3b6" : "946fff3f96fd1088ce97880e40db203396081400100706da863ae07d8abcd0c7"); });
            capture.shutdown(); assert(waitFor([&] { capture.pollUploads(); return capture.shutdownWorkDrained(); }));
            assert(accepted && "context_commit_does_not_require_origins");
        }
    }
}

void protectedPlaybackConsumer() {
    protectedOfflineContentContext();
    protectedEmptyContextCommit();
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
    // The genuine seed finalizer releases all cached plaintext and iterator proxies.
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
        const auto generation = NativeCaptureStorageTestPeer::generation(capture);
        const bool preparationAccepted = NativeCaptureStorageTestPeer::requestRecording(capture);
        const bool reservationReady = preparationAccepted && waitFor([&] { return NativeCaptureStorageTestPeer::resultReady(capture); });
        const auto reservation = NativeCaptureStorageTestPeer::workerTicket(capture);
        const bool reservationSaved = reservationReady && reservation.kind == NativeCapture::QueueMutationKind::recording &&
            reservation.state == NativeCapture::QueueTicketState::committed && reservation.error == CustodyFileError::none &&
            reservation.baseGeneration == generation && reservation.targetGeneration == generation + 1;
        bool sessionSaved = false;
        if (reservationSaved) {
            const auto work = NativeCaptureStorageTestPeer::storageWork(capture);
            std::lock_guard<std::mutex> lock(work->mutex);
            sessionSaved = work->resultValue && std::any_of(work->resultValue->items().begin(), work->resultValue->items().end(),
                [&](const auto& row) { return std::string_view(row.localRecordingId) == capture.sessionId() &&
                    row.directoryId == row.localRecordingId && row.sessionId == row.localRecordingId; });
        }
        const bool beforeFactory = !NativeCaptureStorageTestPeer::prepared(capture) && !std::filesystem::exists(paths.root / capture.sessionId());
        if (reservationReady) NativeCaptureStorageTestPeer::pollStorage(capture); // Real Start-owner ACK before factory.
        const bool preparedBeforeRelease = waitFor([&] { return NativeCaptureStorageTestPeer::prepared(capture); });
        held->Release(); // Always release before asserting a failed bounded observation.
        std::fprintf(stderr, "PROTECTED_PLAYBACK premature_terminal=%u replacement_refused=%u preparation_accepted=%u reservation_saved=%u session_saved=%u before_factory=%u prepared_before_clone_release=%u\n",
            prematureTerminal, replacementRefused, preparationAccepted, reservationSaved, sessionSaved, beforeFactory, preparedBeforeRelease);
        assert(!prematureTerminal && replacementRefused && preparationAccepted && reservationSaved && sessionSaved && beforeFactory && preparedBeforeRelease);
        assert(waitFor([&] { return capture.localPlaybackObservation().terminal; }));
        assert(!capture.authorizeLocalPlayback(17) && !capture.pauseLocalPlayback(false));
        assert(waitFor([&] { return capture.localQueueComplete(); }));
        assert(capture.readiness().storageWritable);
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
    bool inspectionPrepared = false, bool inspectionActiveStop = false, bool privacyFlow = false,
    bool deferredStart = false) {
    std::fprintf(stderr, "V5_CASE=%u stage=start\n", static_cast<unsigned>(test));
    const bool staleEpoch = test == VerticalCase::staleEpoch;
    const bool ownedUpload = test == VerticalCase::ownedUpload;
    const bool partialResume = test == VerticalCase::resumedUpload;
    const bool lateLogout = test == VerticalCase::successfulUploadLateLogout;
    const bool successfulUpload = test == VerticalCase::successfulUpload || partialResume || lateLogout;
    const std::uint64_t frameCount = partialResume ? 14000 : 3000;
    const bool scheduledUpload = test == VerticalCase::scheduledUpload;
    const bool ownedAccount = ownedUpload || scheduledUpload || successfulUpload;
    const bool signedOut = test == VerticalCase::signedOut;
    const bool losePoll = test != VerticalCase::normal && !staleEpoch && !ownedAccount && !signedOut;
    const bool degraded = test == VerticalCase::nativeStopFault || test == VerticalCase::lateDevice;
    Fixture fixture;
    std::string session;
    std::optional<DesktopAccountIdentity> confirmed;
    auto accountCalls = std::make_shared<std::atomic<unsigned>>(0);
    const DesktopHttpTransport::UploadSend accountWire = [accountCalls, successfulUpload, partialResume](const auto& config, const auto& request) -> DesktopHttpTransport::UploadResponse {
        assert(config.sessionToken == "generated-t116-session" && request.method == "GET");
        if (request.path == "/desktop/settings/spaces") {
            const auto call = accountCalls->fetch_add(1);
            assert(call == 0 || (successfulUpload && (call == 2 || call == 4)) || (partialResume && call == 6));
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        }
        assert(request.path == "/api/v1/auth/me");
        const auto call = accountCalls->fetch_add(1);
        assert(call == 1 || (successfulUpload && (call == 3 || call == 5)) || (partialResume && call == 7));
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    };
    {
        auto owned = ownedAccount
            ? std::make_unique<NativeCapture>(fixture.root, AecSelection{std::make_shared<GeneratedAec>(), true}, accountWire)
            : std::make_unique<NativeCapture>(fixture.root, AecSelection{std::make_shared<GeneratedAec>(), true});
        auto& capture = *owned;
        if (deferredStart) assert(!capture.record().accepted()); // No adopted storage yet.
        startAndAdopt(capture, 1);
        if (signedOut) capture.setAuthSessionToken({}, true);
        if (ownedAccount) {
            capture.setAuthSessionToken("generated-t116-session");
            assert(waitFor([&] { capture.pollUploads(); return capture.currentAccount().has_value(); }));
            confirmed = capture.currentAccount(); // Production resolver/adoption, never a private account setter.
            assert(accountCalls->load() == 2);
        }
        if (!ownedAccount) assert(capture.localQueueComplete() && capture.readiness().storageWritable);
        session = capture.sessionId();
        auto before = NativeCaptureStorageTestPeer::projection(capture);
        assert(before && before->items().empty());
        std::atomic<bool> emit{false};
        std::atomic<bool> prepareUnread{false}, unreadHeld{false}, releaseUnread{false};
        std::atomic<unsigned> renderPackets{0}, microphonePackets{0};
        const auto privacyProducer = [&](AudioSource source) {
            return [&, source](const std::atomic_bool& running, std::atomic_bool& ready,
                              const CaptureBatchCallback& callback) {
                const bool microphone = source == AudioSource::microphone;
                auto& device = CaptureSessionTestPeer::microphoneWorker(NativeCaptureStorageTestPeer::controller(capture));
                ClockMapper mapper;
                AudioNormalizer normalizer;
                std::array<std::array<float, 480>, 2> unread{};
                ready.store(true);
                for (std::uint64_t frame = 0; frame != 3000 && running.load(); ++frame) {
                    if (microphone && frame == 1) {
                        while (running.load() && !prepareUnread.load())
                            std::this_thread::sleep_for(std::chrono::milliseconds(1));
                        unread[0].fill(0.5F); unread[1].fill(0.5F);
                        unreadHeld.store(true); // Two source packets, before acquisition/epoch sampling.
                        while (running.load() && !releaseUnread.load()) {
                            CaptureSessionTestPeer::resumeGenerated(device, 1200);
                            std::this_thread::sleep_for(std::chrono::milliseconds(1));
                        }
                        // Only the suffix arrives after the genuine Resume ACK.
                        std::fill(unread[1].begin() + 240, unread[1].end(), 0.25F);
                    }
                    while (running.load() && (!emit.load() ||
                        frame > NativeCaptureStorageTestPeer::writtenFrames(capture) + 32))
                        std::this_thread::sleep_for(std::chrono::milliseconds(1));
                    if (!running.load()) return;
                    AudioBatch batch{source, 48'000, 1, static_cast<std::int64_t>(frame * 480),
                        1, 1, false, std::vector<float>(480, microphone ? (frame ? 0.25F : 0.125F) : 0.0625F), frame * 480};
                    if (microphone) {
                        const auto* samples = frame == 1 || frame == 2 ? unread[frame - 1].data() : batch.samples.data();
                        const auto clockFrame = frame ? (std::max)((frame + 1) * 480 - 1, std::uint64_t{1199}) : 479;
                        assert(CaptureSessionTestPeer::generatedPacket(device, mapper, normalizer, frame, samples, clockFrame));
                        ++microphonePackets;
                    } else { assert(callback(std::move(batch))); ++renderPackets; }
                }
                while (running.load()) std::this_thread::sleep_for(std::chrono::milliseconds(1));
            };
        };
        if (privacyFlow) CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(capture),
            privacyProducer(AudioSource::systemRender), privacyProducer(AudioSource::microphone));
        else if (!deferredStart) CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(capture),
            generatedProducer(capture, emit, AudioSource::systemRender, false, frameCount),
            generatedProducer(capture, emit, AudioSource::microphone, test == VerticalCase::lateDevice, frameCount));
        ReadinessInputs hardware;
        hardware.microphonePermissionGranted = hardware.microphoneEndpointReady =
            hardware.renderEndpointReady = hardware.formatNormalizationReady = hardware.aecReady = true;
        hardware.aacEncoderReady = true;
        assert(!hardware.storageWritable); // Peer never grants storage readiness.
        unsigned guardCalls = 0;
        if (deferredStart) {
            // Public admission and genuine metadata probes, not a private
            // continuation or a READY setter. No health poll can launch native
            // acquisition before both workers receive generated producers.
            assert(capture.localObservation().complete);
            const auto pending = capture.record([&](const std::string& id) {
                assert(id == session);
                return [&](std::string_view active) { ++guardCalls; return active == session; };
            });
            std::fprintf(stderr, "PUBLIC_RECORD accepted=%u state=%u reason=%u\n", pending.accepted(),
                static_cast<unsigned>(pending.state), static_cast<unsigned>(pending.reason));
            assert(pending.accepted() && pending.state == SessionState::starting);
            CaptureSessionTestPeer::devices(NativeCaptureStorageTestPeer::controller(capture),
                generatedProducer(capture, emit, AudioSource::systemRender),
                generatedProducer(capture, emit, AudioSource::microphone));
            assert(capture.indicator().visible && capture.indicator().stopAvailable && guardCalls == 0);
            assert(!capture.record().accepted());
        } else {
            assert(waitFor([&] { capture.pollUploads(); return NativeCaptureStorageTestPeer::requestRecording(capture); }));
            const bool prepared = waitFor([&] {
                capture.pollUploads();
                return NativeCaptureStorageTestPeer::prepared(capture);
            });
            if (!prepared) NativeCaptureStorageTestPeer::diagnosePreparation(capture);
            assert(prepared);
            (void)NativeCaptureStorageTestPeer::startPrepared(capture, hardware);
        }
        assert(waitFor([&] { capture.pollUploads(); capture.pollHealth(); return capture.indicator().state == SessionState::recording; }));
        if (deferredStart) {
            assert(waitFor([&] { capture.pollUploads(); return capture.localQueueComplete(); }));
            assert(guardCalls == 1 && capture.readiness().storageWritable);
        }
        before = NativeCaptureStorageTestPeer::projection(capture);
        assert(NativeCaptureStorageTestPeer::generation(capture) == 2 && before && before->items().size() == 1);
        const auto& reservation = before->items().front();
        assert(reservation.status == UploadQueueStatus::quarantined && !hasUploadServerIdentity(reservation) &&
            std::string_view(reservation.sessionId) == session && reservation.localRecordingId == reservation.sessionId &&
            reservation.directoryId == reservation.sessionId &&
            std::string_view(reservation.packageDirectory) == (fixture.root / session).u8string());
        assert(reservation.safeReason == (ownedAccount || signedOut ? "capture_prepared" : "capture_owner_unknown"));
        assert(std::string_view(reservation.ownerUserId) == (confirmed ? confirmed->userId : "") &&
            std::string_view(reservation.ownerWorkspaceId) == (confirmed ? confirmed->workspaceId : ""));
        emit.store(true);
        if (privacyFlow) {
            assert(waitFor([&] { capture.pollHealth(); return NativeCaptureStorageTestPeer::writtenFrames(capture) == 1; }));
            (void)capture.pause();
            assert(waitFor([&] {
                capture.pollHealth();
                return !capture.privacyPending() && capture.indicator().state == SessionState::paused;
            }));
            prepareUnread.store(true);
            assert(waitFor([&] { return unreadHeld.load(); }));
            (void)capture.resume();
            assert(waitFor([&] {
                capture.pollHealth();
                return !capture.privacyPending() && capture.indicator().state == SessionState::recording;
            }));
            releaseUnread.store(true);
        }
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(180);
        while (NativeCaptureStorageTestPeer::writtenFrames(capture) != frameCount) {
            capture.pollHealth();
            assert(capture.indicator().state == SessionState::recording);
            assert(std::chrono::steady_clock::now() < deadline);
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }
        std::fprintf(stderr, "V5_CASE=%u stage=frames_%llu elapsed_ms=%lld\n", static_cast<unsigned>(test),
            static_cast<unsigned long long>(frameCount),
            static_cast<long long>(std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now() - (deadline - std::chrono::seconds(180))).count()));
        if (privacyFlow) {
            assert(waitFor([&] { return renderPackets.load() == 3000 && microphonePackets.load() == 3000; }));
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
            const bool memoryReleased = waitFor([] {
                return CustodyOwnedMemory::usedBytes() == idleOwnedBytes;
            }, std::chrono::seconds(180));
            if (!memoryReleased) std::fprintf(stderr, "ABANDONED_MEMORY case=%u owned=%zu expected=%zu\n",
                static_cast<unsigned>(test), CustodyOwnedMemory::usedBytes(), idleOwnedBytes);
            assert(memoryReleased);
            std::fprintf(stderr, "V5_CASE=%u stage=abandoned_worker_released\n", static_cast<unsigned>(test));
            assert(second.beginReadinessCheck().accepted());
            assert(second.block(ReasonCode::microphonePermissionDenied).accepted());
        } else {
            nativeFinalizePhaseLog.store(partialResume);
            (void)capture.stop();
            // Drive the real EOS/finalizer but withhold queue adoption. A completed
            // encoder is not savedLocal and cannot publish a private candidate.
            while (!NativeCaptureStorageTestPeer::resultReady(capture)) {
                capture.pollHealth();
                assert(capture.indicator().state != SessionState::savedLocal);
                if (std::chrono::steady_clock::now() >= deadline) {
                    const auto& controller = NativeCaptureStorageTestPeer::controller(capture);
                    std::fprintf(stderr, "FINALIZE_WAIT state=%u reason=%u acquisition_dispatch_done=%u both_eos=%u frames=%llu\n",
                        static_cast<unsigned>(capture.indicator().state), static_cast<unsigned>(capture.indicator().reason),
                        CaptureSessionTestPeer::completed(controller), CaptureSessionTestPeer::bothEndsProcessed(controller),
                        static_cast<unsigned long long>(NativeCaptureStorageTestPeer::writtenFrames(capture)));
                    NativeCaptureStorageTestPeer::diagnoseFinalization(capture);
                }
                assert(std::chrono::steady_clock::now() < deadline);
                std::this_thread::sleep_for(std::chrono::milliseconds(5));
            }
            nativeFinalizePhaseLog.store(false);
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
            assert(ticket->baseGeneration == 2 && ticket->targetGeneration == 3);
            const auto after = NativeCaptureStorageTestPeer::projection(capture);
            assert(after && after->items().size() == 1 && std::string_view(after->items()[0].sessionId) == session);
            assert(after->items()[0].status == (ownedAccount ? UploadQueueStatus::pending : UploadQueueStatus::quarantined));
            assert(after->items()[0].safeReason == (ownedAccount ? "" : signedOut ? "capture_prepared" : "capture_owner_unknown"));
            assert(std::string_view(after->items()[0].ownerUserId) == (confirmed ? confirmed->userId : "") &&
                std::string_view(after->items()[0].ownerWorkspaceId) == (confirmed ? confirmed->workspaceId : ""));
            assert(!capture.uploadsBusy());
            if (deferredStart) {
                assert(waitFor([&] { capture.pollUploads(); return capture.localQueueComplete(); }));
                assert(capture.readiness().storageWritable);
                capture.setUpdateAdmissionBlocked(true);
                assert(!capture.readiness().storageWritable && !capture.record().accepted());
                assert(waitFor([&] { capture.pollUploads(); return capture.updateWorkDrained(); }));
                assert(capture.localQueueComplete()); // Clean terminal queue still permits update.
            }
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
    std::optional<ProtectedUploadExpected> scheduledExpected;
    std::shared_ptr<const ProtectedUploadQueueValue> scheduledQueue;
    auto inspection = std::async(std::launch::async, [&] {
        auto cancellation = std::make_shared<std::atomic<bool>>(false);
        auto store = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(store.ok());
        assert((*store.value)->queueGeneration() == 3);
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
            auto readers = openProtectedCustodyReaders(fixture.root, *pair.value, cancellation);
            assert(readers.ok());
            const auto& current = (*pair.value)->current();
            std::size_t ref = 0;
            while (ref != current.refCount && current.refs[ref].role != CustodyRole::canonical) ++ref;
            assert(ref != current.refCount && current.refs[ref].sealed &&
                current.refs[ref].length && *current.refs[ref].length == 3000 * 1920);
            auto& reader = readers.value->at((*pair.value)->selectedSlot()).at(ref);
            assert(reader.state == CustodySnapshotState::verified && reader.stream);
            std::array<float, 480> samples{};
            for (std::uint64_t frame = 0; frame != 3000; ++frame) {
                ULONG got = 0;
                assert(reader.stream->Read(samples.data(), sizeof(samples), &got) == S_OK && got == sizeof(samples));
                for (std::uint64_t offset = 0; offset != samples.size(); ++offset) {
                    const auto at = frame * 480 + offset;
                    const float expected = at < 480 ? 0.1875F : at < 1200 ? 0.0625F : 0.3125F;
                    assert(samples[offset] == expected && "cold_canonical_must_suppress_old_mic_and_keep_fresh_suffix");
                }
            }
            ULONG got = 1; std::uint8_t extra = 0;
            assert(reader.stream->Read(&extra, 1, &got) == S_FALSE && got == 0);
            std::fputs("PRIVACY_SAMPLES unread=2 boundary=1200 old_suppressed=1 fresh_suffix=240 canonical_samples=1440000 eof=1\n", stderr);
        }
        std::shared_ptr<const ProtectedUploadQueueValue> queueSnapshot;
        if (ownedUpload || successfulUpload) {
            auto queue = (*store.value)->readQueueValue(cancellation); assert(queue.ok() && (*queue.value)->items().size() == 1);
            queueSnapshot = *queue.value;
            const auto& row = queueSnapshot->items()[0];
            assert(confirmed && row.status == UploadQueueStatus::pending);
        }
        store.value.reset(); // The returned pair must retain its own genuine native root/identity leases.
        assert((*pair.value)->current().phase == (degraded ? CustodyPackagePhase::sealedDegraded : CustodyPackagePhase::sealedNormal));
        std::optional<ProtectedUploadExpected> expected;
        if (ownedUpload || successfulUpload) expected.emplace(readProtectedUploadExpected(fixture.root, *pair.value, cancellation));
        auto proof = LocalRecordingPackage::inspectProtected(fixture.root, *pair.value, session, cancellation);
        assert(proof.ok());
        assert((*proof.value)->evidence().integrity == (degraded ? PackageIntegrity::degraded : PackageIntegrity::valid));
        assert((*proof.value)->evidence().durationMs == frameCount * 10);
        if (degraded) assert((*proof.value)->evidence().trustedPrefixFrames == 3000);
        else assert((*proof.value)->evidence().playback.decodedFrames > 0);
        if (ownedUpload) protectedUploadFromCold(fixture.root, session, *confirmed, *proof.value, *expected, cancellation, queueSnapshot->items()[0]);
        if (successfulUpload) { scheduledExpected = std::move(expected); scheduledQueue = std::move(queueSnapshot); }
    });
    inspection.get();
    std::fprintf(stderr, "V5_CASE=%u stage=cold_read_verified\n", static_cast<unsigned>(test));
    if (successfulUpload) {
        auto cancellation = std::make_shared<std::atomic<bool>>(false);
        protectedUploadFromCold(fixture.root, session, *confirmed, {}, *scheduledExpected, cancellation, scheduledQueue->items()[0], accountWire, 64 * 1024, partialResume, lateLogout);
        assert(accountCalls->load() == (partialResume ? 8U : 6U));
        return;
    }
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
        startAndAdopt(scheduled, 3);
        unsigned expiryCalls = 0;
        scheduled.setSessionExpiryHandler([&](auto deadline) { assert(deadline == 123456); ++expiryCalls; });
        scheduled.setAuthSessionToken("generated-t116-session");
        std::string activeSession;
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
        assert(prepare.state == NativeCapture::QueueTicketState::committed && prepare.baseGeneration == 3 &&
            prepare.targetGeneration == 4 && "protected_nonempty_prepare_requires_durable_ack");
        // No UI poll during either physical commit: network/effects must wait
        // for the exact ACK, not just the completed worker or its disk write.
        assert(NativeCaptureStorageTestPeer::generation(scheduled) == 3 && uploadCalls->load() == 0);
        assert(scheduled.uploadsBusy());
        if (inspectionPrepared || inspectionActiveStop) {
            oldPackedPath = L"\\\\?\\" + (fixture.root / session / L".custody-v1" / L"canonical" / L"content.packed-v2").native();
            { std::lock_guard<std::mutex> lock(cutMutex); cutReached = cutReleased = false; }
            pauseOldPackedRead.store(true);
        }
        scheduled.pollUploads();
        const auto prepareConcurrentRecording = [&] {
            activeSession = scheduled.sessionId();
            assert(activeSession != session && NativeCaptureStorageTestPeer::requestRecording(scheduled));
            const bool prepared = waitFor([&] {
                NativeCaptureStorageTestPeer::pollStorage(scheduled); // Genuine Start ACK, never a prepared/READY setter.
                return NativeCaptureStorageTestPeer::prepared(scheduled);
            });
            if (!prepared) NativeCaptureStorageTestPeer::diagnosePreparation(scheduled);
            assert(prepared && "cold_inspection_or_http_must_not_block_actual_recording_preparation");
            const auto ticket = NativeCaptureStorageTestPeer::ticket(scheduled); assert(ticket);
            assert(ticket->kind == NativeCapture::QueueMutationKind::recording &&
                ticket->state == NativeCapture::QueueTicketState::committed && ticket->error == CustodyFileError::none &&
                ticket->baseGeneration == 4 && ticket->targetGeneration == 5);
            const auto queue = NativeCaptureStorageTestPeer::projection(scheduled);
            assert(NativeCaptureStorageTestPeer::generation(scheduled) == 5 && queue && queue->items().size() == 2);
            for (const auto& row : queue->items()) {
                const bool old = std::string_view(row.sessionId) == session;
                assert(old || std::string_view(row.sessionId) == activeSession);
                assert(row.localRecordingId == row.sessionId && row.directoryId == row.sessionId &&
                    std::string_view(row.packageDirectory) == (fixture.root / std::string(row.sessionId)).u8string());
                assert(row.status == (old ? UploadQueueStatus::pending : UploadQueueStatus::quarantined) &&
                    row.safeReason == (old ? "" : "capture_prepared") && !hasUploadServerIdentity(row));
                assert(confirmed && std::string_view(row.ownerUserId) == confirmed->userId &&
                    std::string_view(row.ownerWorkspaceId) == confirmed->workspaceId);
            }
            assert(waitFor([&] { return scheduled.localQueueComplete(); }));
            assert(scheduled.readiness().storageWritable && expiryCalls == 0);
        };
        if (inspectionActiveStop) {
            assert(waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }, std::chrono::seconds(180)));
            assert(!pauseOldPackedRead.load() && uploadCalls->load() == 0);
            prepareConcurrentRecording();
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
            assert(uploadCalls->load() == 0);
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
                recordingTicket.baseGeneration == 5 && recordingTicket.targetGeneration == 6);
            assert(NativeCaptureStorageTestPeer::generation(scheduled) == 5 &&
                NativeCaptureStorageTestPeer::projection(scheduled)->items().size() == 2 && expiryCalls == 0);
            scheduled.pollUploads(); // Recording adoption only, not upload-result adoption.
            assert(NativeCaptureStorageTestPeer::generation(scheduled) == 6);
            assert(waitFor([&] { scheduled.pollHealth(); return scheduled.indicator().state == SessionState::savedLocal; }));
            assert(waitFor([&] {
                return NativeCaptureStorageTestPeer::resultReady(scheduled) &&
                    NativeCaptureStorageTestPeer::workerTicket(scheduled).kind == NativeCapture::QueueMutationKind::uploadResult;
            }, std::chrono::seconds(180)));
            const auto uploadTicket = NativeCaptureStorageTestPeer::workerTicket(scheduled);
            assert(uploadTicket.id != recordingTicket.id && uploadTicket.state == NativeCapture::QueueTicketState::committed &&
                uploadTicket.error == CustodyFileError::none && uploadTicket.baseGeneration == 6 && uploadTicket.targetGeneration == 7);
            assert(uploadCalls->load() == 1 && expiryCalls == 0);
            scheduled.pollUploads();
            assert(NativeCaptureStorageTestPeer::generation(scheduled) == 7 && expiryCalls == 1);
            assert(waitFor([&] { scheduled.pollUploads(); return !scheduled.uploadsBusy(); }, std::chrono::seconds(180)));
            const auto verifyRows = [&](const NativeCapture& capture) {
                const auto queue = NativeCaptureStorageTestPeer::projection(capture);
                assert(queue && queue->items().size() == 2);
                for (const auto& row : queue->items()) {
                    const bool old = std::string_view(row.sessionId) == session;
                    assert(old || std::string_view(row.sessionId) == activeSession);
                    assert(row.status == (old ? UploadQueueStatus::retry : UploadQueueStatus::pending));
                    assert(row.attempts == (old ? 1U : 0U));
                    assert(row.safeReason == (old ? "transport_unavailable" : ""));
                    assert(hasUploadServerIdentity(row) == old); // This guard intentionally includes attempt history.
                    assert(row.meetingId.empty() && row.uploadSessionId.empty() && row.mediaRevisionId.empty() &&
                        row.serverStatus.empty() && row.processingStatus.empty() && row.mediaRevisionStatus.empty() &&
                        std::all_of(row.acceptedBytes.begin(), row.acceptedBytes.end(), [](auto bytes) { return bytes == 0; }));
                    assert(confirmed && std::string_view(row.ownerUserId) == confirmed->userId &&
                        std::string_view(row.ownerWorkspaceId) == confirmed->workspaceId);
                }
                assert(waitFor([&] { return capture.localQueueComplete(); }));
                assert(capture.readiness().storageWritable);
            };
            verifyRows(scheduled);
            scheduled.shutdown();
            assert(waitFor([&] { scheduled.pollUploads(); return scheduled.shutdownWorkDrained(); }, std::chrono::seconds(180)));
            oldPackedPath.clear();
            auto cold = std::async(std::launch::async, [&] {
                auto cancellation = std::make_shared<std::atomic<bool>>(false);
                auto opened = ProtectedCustodyStoreOwner::open(fixture.root, cancellation); assert(opened.ok());
                assert((*opened.value)->queueGeneration() == 7);
                auto pair = (*opened.value)->readPackage(activeSession, cancellation); assert(pair.ok());
                opened.value.reset();
                assert((*pair.value)->current().phase == CustodyPackagePhase::sealedNormal);
                auto proof = LocalRecordingPackage::inspectProtected(fixture.root, *pair.value, activeSession, cancellation);
                assert(proof.ok() && (*proof.value)->evidence().integrity == PackageIntegrity::valid &&
                    (*proof.value)->evidence().durationMs == 30'000 && (*proof.value)->evidence().playback.decodedFrames > 0);
            });
            cold.get();
            NativeCapture durable(fixture.root, {std::make_shared<GeneratedAec>(), true});
            startAndAdopt(durable, 7);
            verifyRows(durable);
            durable.shutdown();
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(durable); }));
            assert(uploadCalls->load() == 1 && expiryCalls == 1);
            std::fputs("PROTECTED_INSPECTION active_stop_both_eos_sealed_adoption_restart7=pass\n", stderr);
            return;
        }
        if (inspectionPrepared) {
            assert(waitFor([] { std::lock_guard<std::mutex> lock(cutMutex); return cutReached; }, std::chrono::seconds(180)));
            assert(!pauseOldPackedRead.load() && uploadCalls->load() == 0);
            prepareConcurrentRecording();
            const bool actuallyPrepared = NativeCaptureStorageTestPeer::prepared(scheduled);
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
            NativeCapture durable(fixture.root, {std::make_shared<GeneratedAec>(), true});
            startAndAdopt(durable, 5);
            const auto rows = NativeCaptureStorageTestPeer::projection(durable);
            assert(rows && rows->items().size() == 2);
            for (const auto& row : rows->items()) {
                const bool old = std::string_view(row.sessionId) == session;
                assert(old || std::string_view(row.sessionId) == activeSession);
                assert(row.status == (old ? UploadQueueStatus::pending : UploadQueueStatus::quarantined) &&
                    row.safeReason == (old ? "" : "capture_prepared") && row.attempts == 0 && !hasUploadServerIdentity(row));
                assert(confirmed && std::string_view(row.ownerUserId) == confirmed->userId &&
                    std::string_view(row.ownerWorkspaceId) == confirmed->workspaceId);
            }
            durable.shutdown();
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(durable); }));
            std::fputs("PROTECTED_INSPECTION prepared_during_packed_io_cancel_zero_wire_drained=pass\n", stderr);
            return;
        }
        if (stopPrepared) {
            assert(waitFor([&] { return uploadCalls->load() == 1; }, std::chrono::seconds(180)));
            // An existing HTTP call must not occupy the storage command slot.
            prepareConcurrentRecording();
            { std::lock_guard<std::mutex> lock(networkMutex); networkReleased = true; }
            networkWake.notify_all();
        }
        assert(waitFor([&] {
            return NativeCaptureStorageTestPeer::resultReady(scheduled) &&
                NativeCaptureStorageTestPeer::workerTicket(scheduled).kind == NativeCapture::QueueMutationKind::uploadResult &&
                NativeCaptureStorageTestPeer::workerTicket(scheduled).baseGeneration == (stopPrepared ? 5U : 4U);
        }, std::chrono::seconds(180)));
        const auto result = NativeCaptureStorageTestPeer::workerTicket(scheduled);
        if (resultCut != IoCut::none) {
            assert(result.state == (resultCut == IoCut::ambiguousRename ?
                NativeCapture::QueueTicketState::ambiguous : NativeCapture::QueueTicketState::notCommitted));
            assert(uploadCalls->load() == 1 && expiryCalls == 0 && scheduled.uploadsBusy());
            assert(NativeCaptureStorageTestPeer::generation(scheduled) == 4);
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
                assert(NativeCaptureStorageTestPeer::generation(scheduled) == 4 && expiryCalls == 0);
                allocator.deallocate(reservation, reserved);
                scheduled.setAuthSessionToken(""); // Storage validation must not require a signed-in account.
                scheduled.recover(RecoveryTrigger::networkRecovered);
                assert(!scheduled.currentAccount());
                scheduled.pollUploads();
                assert(waitFor([&] { return NativeCaptureStorageTestPeer::physicalReadback(scheduled); }));
                assert(scheduled.uploadsBusy() && NativeCaptureStorageTestPeer::generation(scheduled) == 4);
                scheduled.setUpdateAdmissionBlocked(true); // Physical ACK during update: no effects or new HTTP.
                assert(waitFor([&] { scheduled.pollUploads(); return scheduled.updateWorkDrained(); }));
            } else {
                assert(waitFor([&] { return NativeCaptureStorageTestPeer::physicalReadback(scheduled); }));
                assert(scheduled.uploadsBusy() && NativeCaptureStorageTestPeer::generation(scheduled) == 4);
                scheduled.pollUploads(); // Physical truth only; original failed ticket stays failed.
                assert(waitFor([&] { scheduled.pollUploads(); return !scheduled.uploadsBusy(); }));
            }
            const auto generation = resultCut == IoCut::ambiguousRename ? 5U : 4U;
            assert(NativeCaptureStorageTestPeer::generation(scheduled) == generation);
            assert(expiryCalls == 0 && uploadCalls->load() == 1);
            assert(NativeCaptureStorageTestPeer::ticket(scheduled)->state == result.state);
            scheduled.shutdown();
            assert(waitFor([&] { scheduled.pollUploads(); return scheduled.shutdownWorkDrained(); }));
            NativeCapture durable(fixture.root, {std::make_shared<GeneratedAec>(), true});
            startAndAdopt(durable, generation);
            const auto& row = NativeCaptureStorageTestPeer::projection(durable)->items()[0];
            assert(row.status == (generation == 5 ? UploadQueueStatus::retry : UploadQueueStatus::pending));
            assert(row.attempts == (generation == 5 ? 1U : 0U));
            durable.shutdown();
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(durable); }));
            std::fprintf(stderr, "PROTECTED_SCHEDULER failed_result_physical_readback=pass published=%u quota_refused=%u\n",
                generation == 5 ? 1U : 0U, refuseReopen ? 1U : 0U);
            return;
        }
        assert(result.state == NativeCapture::QueueTicketState::committed && result.error == CustodyFileError::none &&
            result.targetGeneration == (stopPrepared ? 6U : 5U));
        assert(uploadCalls->load() == 1 && expiryCalls == 0);
        assert(scheduled.uploadsBusy());
        if (stopPrepared) {
            scheduled.shutdown(); // Busy result ACK must not strand the prepared, unstarted recording.
            assert(waitFor([&] { scheduled.pollUploads(); return scheduled.shutdownWorkDrained(); }));
            assert(expiryCalls == 0 && !scheduled.uploadsBusy());
            NativeCapture durable(fixture.root, {std::make_shared<GeneratedAec>(), true});
            startAndAdopt(durable, 6);
            const auto rows = NativeCaptureStorageTestPeer::projection(durable);
            assert(rows && rows->items().size() == 2);
            for (const auto& row : rows->items()) {
                const bool old = std::string_view(row.sessionId) == session;
                assert(old || std::string_view(row.sessionId) == activeSession);
                std::fprintf(stderr, "PROTECTED_SCHEDULER cold_stop_prepared old=%u status=%u reason=%s attempts=%u server=%u\n",
                    old ? 1U : 0U, static_cast<unsigned>(row.status), row.safeReason.c_str(), row.attempts,
                    hasUploadServerIdentity(row) ? 1U : 0U);
                std::fflush(stderr);
                assert(row.status == (old ? UploadQueueStatus::retry : UploadQueueStatus::quarantined) &&
                    row.safeReason == (old ? "transport_unavailable" : "capture_prepared") &&
                    row.attempts == (old ? 1U : 0U));
                assert(hasUploadServerIdentity(row) == old);
                assert(row.meetingId.empty() && row.uploadSessionId.empty() && row.mediaRevisionId.empty() &&
                    row.serverStatus.empty() && row.processingStatus.empty() && row.mediaRevisionStatus.empty() &&
                    std::all_of(row.acceptedBytes.begin(), row.acceptedBytes.end(), [](auto bytes) { return bytes == 0; }));
                assert(confirmed && std::string_view(row.ownerUserId) == confirmed->userId &&
                    std::string_view(row.ownerWorkspaceId) == confirmed->workspaceId);
            }
            durable.shutdown();
            assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(durable); }));
            std::fputs("PROTECTED_SCHEDULER stop_prepared_while_result_busy=pass\n", stderr);
            return;
        }
        assert(NativeCaptureStorageTestPeer::generation(scheduled) == 4 &&
            NativeCaptureStorageTestPeer::projection(scheduled)->items()[0].status == UploadQueueStatus::pending);
        scheduled.pollUploads();
        assert(NativeCaptureStorageTestPeer::generation(scheduled) == 5 && expiryCalls == 1);
        const auto& row = NativeCaptureStorageTestPeer::projection(scheduled)->items()[0];
        assert(row.status == UploadQueueStatus::retry && row.attempts == 1 && row.safeReason == "transport_unavailable");
        scheduled.pollUploads();
        assert(NativeCaptureStorageTestPeer::generation(scheduled) == 5 && uploadCalls->load() == 1 && expiryCalls == 1);
        assert(waitFor([&] { return scheduled.localQueueComplete(); }));
        assert(scheduled.readiness().storageWritable);
        scheduled.shutdown();
        assert(waitFor([&] { scheduled.pollUploads(); return scheduled.shutdownWorkDrained(); }));
        NativeCapture durable(fixture.root, {std::make_shared<GeneratedAec>(), true});
        startAndAdopt(durable, 5);
        assert(NativeCaptureStorageTestPeer::projection(durable)->items()[0].status == UploadQueueStatus::retry);
        assert(NativeCaptureStorageTestPeer::projection(durable)->items()[0].attempts == 1);
        durable.shutdown();
        assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(durable); }));
        std::fputs("PROTECTED_SCHEDULER generated_recording_cold_prepare_network_result_adoption=pass\n", stderr);
        return;
    }
    NativeCapture restarted(fixture.root, {std::make_shared<GeneratedAec>(), true});
    startAndAdopt(restarted, 3);
    assert(NativeCaptureStorageTestPeer::projection(restarted)->items().size() == 1);
    assert(std::string_view(NativeCaptureStorageTestPeer::projection(restarted)->items()[0].sessionId) == session);
    assert(NativeCaptureStorageTestPeer::projection(restarted)->items()[0].status ==
        (ownedAccount && !degraded ? UploadQueueStatus::pending : UploadQueueStatus::quarantined));
    const auto& restartedRow = NativeCaptureStorageTestPeer::projection(restarted)->items().front();
    assert(restartedRow.safeReason == (ownedAccount ? "" : signedOut ? "capture_prepared" : "capture_owner_unknown"));
    assert(std::string_view(restartedRow.ownerUserId) == (confirmed ? confirmed->userId : "") &&
        std::string_view(restartedRow.ownerWorkspaceId) == (confirmed ? confirmed->workspaceId : ""));
    assert(restarted.localQueueComplete() && restarted.readiness().storageWritable);
    restarted.shutdown();
    assert(waitFor([&] { return NativeCaptureStorageTestPeer::released(restarted); }));
    std::fprintf(stderr, "V5_CASE=%u stage=done\n", static_cast<unsigned>(test));
}
}
namespace graf::windows {
void observeStartBeforeCanonical(const ProtectedCustodyRecordingPackage& born) noexcept {
    const auto incoming=GetLastError();
    if (startOwnerCrashArmed.load(std::memory_order_acquire) && startOwnerCrash->cut==StartOwnerCrashCut::packageAfterSemanticAck) {
        assert(startOwnerCrashArmed.exchange(false));
        terminateStartOwnerCrash(&born);
    }
    SetLastError(incoming);
}
}
int main(int argc, char** argv) {
    winrt::init_apartment(); // Keep WinRT alive across repeated native sessions, as AppMain does.
#ifdef _MSC_VER
    _set_error_mode(_OUT_TO_STDERR);
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
#endif
#if defined(_MSC_VER) && defined(_DEBUG)
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
#endif
    const auto baseline = CustodyOwnedMemory::usedBytes();
    idleOwnedBytes = baseline; // Empty optional cache entries retain no allocation.
    assert(CustodyOwnedMemory::usedBytes() == baseline);
    if (argc>1 && std::string_view(argv[1]).rfind("--protected-start-owner-crash",0)==0) {
        int count=0;
        struct WideArgs { LPWSTR* values; ~WideArgs() { if (values) LocalFree(values); } } args{CommandLineToArgvW(GetCommandLineW(),&count)};
        if (!args.values || count!=5 || std::wstring_view(args.values[1])!=L"--protected-start-owner-crash") return 89;
        const auto selected=std::find(startOwnerCrashArguments.begin(),startOwnerCrashArguments.end(),std::wstring_view(args.values[4]));
        if (selected==startOwnerCrashArguments.end()) return 89;
        const auto cut=static_cast<StartOwnerCrashCut>(selected-startOwnerCrashArguments.begin());
        try { return protectedStartOwnerCrashChild(std::filesystem::path(args.values[2]),std::filesystem::path(args.values[3]),cut); }
        catch (...) { return 89; }
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-no-login-claim") {
        for (unsigned scenario = 0; scenario != 6; ++scenario) protectedStartOwnerFinalization(true, scenario);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-start-owner-unfinished-shutdown") {
        protectedStartOwnerUnfinishedRestart(3, 4);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-start-owner-recovery-alias") {
        protectedStartOwnerUnfinishedRestart(4, 5);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-start-owner-unfinished-restart") {
        protectedStartOwnerUnfinishedRestart();
        protectedRecoveryLivePlayback(true);
        protectedRecoveryLivePlayback(true, 1);
        protectedRecoveryLivePlayback(true, 2);
        protectedDeletionDisplayDrain(true);
        protectedDeletionDisplayDrain(true, true);
        protectedDeletionDisplayDrain(true, true, true);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-start-owner-degraded-restart") {
        protectedStartOwnerDegradedRestart();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-recovery-live-playback") {
        protectedRecoveryLivePlayback();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-start-owner-recovery") {
        protectedStartOwnerRecovery();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-start-owner") {
        protectedStartOwner();
        protectedStartOwnerFinalization();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-recording-lifecycle") {
        for (const auto test : {VerticalCase::normal, VerticalCase::staleEpoch, VerticalCase::lostPoll,
            VerticalCase::nativeStopFault, VerticalCase::lateDevice, VerticalCase::lateUi, VerticalCase::ownedUpload})
            protectedRecordingVerticalAndRestart(test);
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
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
        const auto previousTerminate = std::set_terminate([] {
            std::fprintf(stderr, "NATIVE_LIFECYCLE_TERMINATE phase=%s case=%u owned_bytes=%zu\n",
                lifecyclePhase.load(), lifecycleCase.load(), CustodyOwnedMemory::usedBytes());
            std::fflush(stderr);
            const char* kind = "none";
            try { if (auto error = std::current_exception()) std::rethrow_exception(error); }
            catch (const std::bad_alloc&) { kind = "bad_alloc"; }
            catch (...) { kind = "other"; }
            std::fprintf(stderr, "NATIVE_LIFECYCLE_TERMINATE exception=%s\n", kind);
            std::fflush(stderr); std::abort();
        });
        protectedDeletionApplication();
        assert(waitFor([&] { return CustodyOwnedMemory::usedBytes() == baseline; }));
        std::set_terminate(previousTerminate);
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
    if (argc == 2 && std::string_view(argv[1]) == "--protected-short-discard") {
        protectedShortDiscard();
        protectedNativeShortDiscard();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-pending-start") {
        protectedRecordingVerticalAndRestart(VerticalCase::normal, IoCut::none, false, false, false, false, false, true);
        protectedRecordingVerticalAndRestart(VerticalCase::signedOut, IoCut::none, false, false, false, false, false, true);
        protectedPendingCancellation();
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
        nativeLegacyMigrationReadModel();
        nativeLegacyQuarantineReadModel();
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
        protectedStartOwnerProcessDeath(true); // Keep the eight lifecycle children outside Start's existing 240-second case.
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
    if (argc == 2 && std::string_view(argv[1]) == "--protected-playback-batches") {
        protectedPlaybackBatches();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        std::fputs("PLAYBACK_BATCH idle_memory=pass audio=0 network=0\n",stderr);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-storage-profile") {
        protectedStorageProfile();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        std::fputs("STORAGE_PROFILE idle_memory=pass audio=0 network=0\n", stderr);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--protected-large-parts") {
        protectedLargeUploadParts();
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        std::fputs("PROTECTED_LARGE_PARTS idle_memory=pass audio=0 network=0\n", stderr);
        std::fflush(stderr);
        return 0;
    }
    if (argc == 2 && (std::string_view(argv[1]) == "--protected-scheduler-success" ||
                     std::string_view(argv[1]) == "--protected-scheduler-resume" ||
                     std::string_view(argv[1]) == "--protected-scheduler-late-logout")) {
        protectedRecordingVerticalAndRestart(std::string_view(argv[1]) == "--protected-scheduler-resume"
            ? VerticalCase::resumedUpload : std::string_view(argv[1]) == "--protected-scheduler-late-logout"
                ? VerticalCase::successfulUploadLateLogout : VerticalCase::successfulUpload);
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        return 0;
    }
    if (argc == 2 && (std::string_view(argv[1]) == "--protected-upload" ||
                     std::string_view(argv[1]) == "--protected-upload-control-types")) {
        enforceProtectedHttpControlTypes = std::string_view(argv[1]) == "--protected-upload";
        protectedRecordingVerticalAndRestart(VerticalCase::ownedUpload);
        assert(waitFor([] { return CustodyOwnedMemory::usedBytes() == idleOwnedBytes; }));
        std::fputs("PROTECTED_HTTP worker_drained_idle_memory=pass\n", stderr);
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
