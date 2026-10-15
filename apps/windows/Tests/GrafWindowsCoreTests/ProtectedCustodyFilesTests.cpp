#include "../../RecApp/Storage/ProtectedCustodyFiles.h"
#include "../../RecApp/Storage/ProtectedCustodyMetadata.h"
#include "../../RecApp/Upload/DesktopUploadQueueService.h"
#include "../../RecApp/Storage/ProtectedCustodyPrimitives.h"
#include "../../RecApp/Storage/Sha256.h"
#ifdef _WIN32
#include "../../RecApp/Storage/ProtectedCustodyReader.h"
#include "../../RecApp/Storage/ProtectedCustodyWriter.h"
#include "../../RecApp/Recording/LocalRecordingPackage.h"
#include <mfapi.h>
#include <mfidl.h>
#include <windows.h>
#include <sddl.h>
#include <objbase.h>
#include <aclapi.h>
#include <bcrypt.h>
#include <winternl.h>
#include <winioctl.h>
#endif
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include "../GeneratedRecordingFixtures.h"
#include <algorithm>
#include <fstream>
#include <string>
#include <cstdio>
#include <cstring>
#include <new>
#include <limits>
#include <thread>
#include <functional>
#include <array>
#include <chrono>
#include <system_error>
#include <cstdlib>
#include <clocale>
#include <type_traits>
#ifdef _MSC_VER
#include <crtdbg.h>
#endif

#ifdef _WIN32
// Executable-only allocation cuts, armed only around candidate, Birth or factory calls.
// No threads/sleeps or product hooks; ordinary std::allocator still allocates.
namespace {
struct QueueAllocationHook {
    bool active = false, hit = false;
    std::size_t calls = 0, failAt = 0, cancelAt = 0;
    std::atomic<bool>* cancellation = nullptr;
    const wchar_t* queueIdentity = nullptr;
    const wchar_t* bootstrapIdentity = nullptr;
    bool pureCodec = false; // Birth owns neither a native job nor queue identity leases.
    bool migrationFactory = false; // Includes early allocations BEFORE its own identity lease.
};
thread_local QueueAllocationHook queueAllocation;
}
void* operator new(std::size_t bytes) {
    if (queueAllocation.active) {
        const auto ordinal = ++queueAllocation.calls;
        if (ordinal == queueAllocation.failAt || ordinal == queueAllocation.cancelAt) {
            queueAllocation.hit = true;
            if (!queueAllocation.pureCodec && !queueAllocation.migrationFactory) {
                std::array<graf::windows::CustodyNativeJob, 3> remaining;
                for (const auto& job : remaining) assert(job);
                graf::windows::CustodyNativeJob overflow; assert(!overflow);
                for (const auto path : {queueAllocation.queueIdentity, queueAllocation.bootstrapIdentity}) {
                    const auto file = CreateFileW(path, GENERIC_WRITE,
                        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
                    assert(file == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
                }
            }
            if (ordinal == queueAllocation.cancelAt) queueAllocation.cancellation->store(true);
            if (ordinal == queueAllocation.failAt) { queueAllocation.failAt = 0; throw std::bad_alloc(); }
        }
    }
    if (auto* memory = std::malloc(bytes ? bytes : 1)) return memory;
    throw std::bad_alloc();
}
void operator delete(void* memory) noexcept { std::free(memory); }
void operator delete(void* memory, std::size_t) noexcept { std::free(memory); }

// TU-local native failures compile the REAL file layer. No production fault knob.
namespace {
enum class FileFault { none, shortWrite, zeroWrite, write, flush, rename, renameCompletion, read, readFailed, identityMismatch, hashCreate, allocation, readAborted };
FileFault fileFault = FileFault::none;
unsigned flushOrdinal = 1, flushes = 0, writes = 0, reads = 0, hashCreates = 0;
unsigned opens = 0, renames = 0, searches = 0, diskChecks = 0, creates = 0;
bool attributeOnlyLocks = false;
std::function<void()> afterFlush, afterRename, afterRead;
HANDLE afterReadFile = INVALID_HANDLE_VALUE; // Borrowed only during the existing afterRead callback.
bool findFailure = false, nextFailure = false, diskOverride = false;
HRESULT diskFailure = S_OK;
DISK_SPACE_INFORMATION diskInfo{};
HANDLE WINAPI fileTestFindFirst(LPCWSTR pattern, LPWIN32_FIND_DATAW data) {
    ++searches;
    if (findFailure) { SetLastError(ERROR_ACCESS_DENIED); return INVALID_HANDLE_VALUE; }
    return FindFirstFileW(pattern, data);
}
BOOL WINAPI fileTestFindNext(HANDLE search, LPWIN32_FIND_DATAW data) {
    ++searches;
    if (findFailure || nextFailure) { SetLastError(ERROR_ACCESS_DENIED); return FALSE; }
    return FindNextFileW(search, data);
}
HRESULT WINAPI fileTestDiskInfo(LPCWSTR root, DISK_SPACE_INFORMATION* info) {
    ++diskChecks;
    if (FAILED(diskFailure)) return diskFailure;
    if (diskOverride) { *info = diskInfo; return S_OK; }
    return GetDiskSpaceInformationW(root, info);
}
HANDLE WINAPI fileTestOpen(LPCWSTR path, DWORD access, DWORD share, LPSECURITY_ATTRIBUTES security,
    DWORD disposition, DWORD flags, HANDLE templateFile) {
    ++opens;
    if (disposition != OPEN_EXISTING) ++creates;
    if (attributeOnlyLocks && (flags & FILE_FLAG_BACKUP_SEMANTICS)) access &= ~FILE_LIST_DIRECTORY;
    return CreateFileW(path, access, share, security, disposition, flags, templateFile);
}
void inject(FileFault selected, unsigned ordinal = 1) {
    fileFault = selected; flushOrdinal = ordinal; flushes = writes = reads = hashCreates = 0;
    opens = renames = searches = diskChecks = creates = 0;
}
BOOL WINAPI fileTestWrite(HANDLE file, LPCVOID bytes, DWORD count, LPDWORD written, LPOVERLAPPED overlapped) {
    ++writes;
    PACL acl = nullptr; PSECURITY_DESCRIPTOR descriptor = nullptr;
    assert(GetSecurityInfo(file, SE_FILE_OBJECT, DACL_SECURITY_INFORMATION, nullptr, nullptr, &acl, nullptr, &descriptor) == ERROR_SUCCESS);
    SECURITY_DESCRIPTOR_CONTROL control{}; DWORD revision = 0;
    assert(acl && acl->AceCount == 1 && GetSecurityDescriptorControl(descriptor, &control, &revision) && (control & SE_DACL_PROTECTED));
    LocalFree(descriptor); // Proven at EACH content-write boundary, including identity creation.
    if (fileFault == FileFault::zeroWrite) { *written = 0; return TRUE; }
    if (fileFault == FileFault::write) { SetLastError(ERROR_WRITE_FAULT); return FALSE; }
    return WriteFile(file, bytes, fileFault == FileFault::shortWrite ? std::min<DWORD>(count, 7) : count, written, overlapped);
}
BOOL WINAPI fileTestFlush(HANDLE file) {
    ++flushes;
    if (fileFault == FileFault::flush && flushes == flushOrdinal) { SetLastError(ERROR_WRITE_FAULT); return FALSE; }
    const auto flushed = FlushFileBuffers(file);
    if (flushed && afterFlush) afterFlush();
    return flushed;
}
using NativeRename = NTSTATUS (NTAPI*)(HANDLE, PIO_STATUS_BLOCK, PVOID, ULONG, FILE_INFORMATION_CLASS);
NTSTATUS NTAPI fileTestRename(HANDLE file, PIO_STATUS_BLOCK io, PVOID info, ULONG size, FILE_INFORMATION_CLASS kind) {
    ++renames;
    assert(static_cast<unsigned>(kind) == 10);
    if (fileFault == FileFault::rename) { io->Status = static_cast<NTSTATUS>(0xC0000022UL); return io->Status; }
    const auto procedure = GetProcAddress(GetModuleHandleW(L"ntdll.dll"), "NtSetInformationFile"); assert(procedure);
    NativeRename real = nullptr; static_assert(sizeof(real) == sizeof(procedure));
    std::memcpy(&real, &procedure, sizeof(real));
    const auto result = real(file, io, info, size, kind);
    if (result == 0 && afterRename) afterRename();
    if (fileFault == FileFault::renameCompletion && result == 0) io->Status = static_cast<NTSTATUS>(0xC0000022UL);
    return result;
}
FARPROC WINAPI fileTestProcedure(HMODULE module, LPCSTR name) {
    if (std::strcmp(name, "NtSetInformationFile") != 0) return GetProcAddress(module, name);
    const NativeRename test = fileTestRename; FARPROC procedure = nullptr;
    static_assert(sizeof(procedure) == sizeof(test)); std::memcpy(&procedure, &test, sizeof(test)); return procedure;
}
BOOL WINAPI fileTestRead(HANDLE file, LPVOID bytes, DWORD count, LPDWORD got, LPOVERLAPPED overlapped) {
    ++reads;
    if (fileFault == FileFault::read) { *got = 0; return TRUE; }
    if ((fileFault == FileFault::readFailed || fileFault == FileFault::readAborted) && reads == flushOrdinal) {
        SetLastError(fileFault == FileFault::readAborted ? ERROR_OPERATION_ABORTED : ERROR_READ_FAULT); return FALSE;
    }
    const auto result = ReadFile(file, bytes, count, got, overlapped);
    if (result && fileFault == FileFault::identityMismatch && reads == flushOrdinal && count == 16 && *got == 16)
        static_cast<PUCHAR>(bytes)[0] ^= 1; // Different observed store IDs, without weakening native leases.
    if (result && afterRead) {
        const auto previous = afterReadFile; afterReadFile = file;
        afterRead(); afterReadFile = previous;
    }
    return result;
}
NTSTATUS WINAPI fileTestHashCreate(BCRYPT_ALG_HANDLE algorithm, BCRYPT_HASH_HANDLE* hash,
    PUCHAR object, ULONG objectBytes, PUCHAR secret, ULONG secretBytes, ULONG flags) {
    ++hashCreates;
    assert(algorithm == BCRYPT_SHA256_ALG_HANDLE);
    if (fileFault == FileFault::allocation && hashCreates == flushOrdinal) throw std::bad_alloc();
    if (fileFault == FileFault::hashCreate && hashCreates == flushOrdinal) return static_cast<NTSTATUS>(0xC0000001UL);
    return BCryptCreateHash(algorithm, hash, object, objectBytes, secret, secretBytes, flags);
}
}
#define BCryptCreateHash fileTestHashCreate
#include "../../RecApp/Storage/Sha256.cpp"
#undef BCryptCreateHash
#define WriteFile fileTestWrite
#define FlushFileBuffers fileTestFlush
#define GetProcAddress fileTestProcedure
#define CreateFileW fileTestOpen
#define ReadFile fileTestRead
#define FindFirstFileW fileTestFindFirst
#define FindNextFileW fileTestFindNext
#define GetDiskSpaceInformationW fileTestDiskInfo
#include "../../RecApp/Storage/ProtectedCustodyFiles.cpp"
#undef WriteFile
#undef FlushFileBuffers
#undef GetProcAddress
#undef CreateFileW
#undef ReadFile
#undef FindFirstFileW
#undef FindNextFileW
#undef GetDiskSpaceInformationW
#endif

using namespace graf::windows;
namespace {
#ifdef _WIN32
struct Fixture {
    std::filesystem::path root;
    PSECURITY_DESCRIPTOR descriptor = nullptr;
    SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), nullptr, FALSE};
    CustodyContext context{{}, {}, CustodyRole::queue};
    std::wstring roleDirectory;
    bool service;
    Fixture(CustodyRole role = CustodyRole::queue, std::wstring directory = L"queue")
        : roleDirectory(std::move(directory)), service(role == CustodyRole::queue || role == CustodyRole::bootstrap || role == CustodyRole::migrationIntent) {
        context.role = role;
        HANDLE token = nullptr; assert(OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token));
        DWORD size = 0; GetTokenInformation(token, TokenUser, nullptr, 0, &size);
        std::vector<std::uint8_t> bytes(size);
        assert(GetTokenInformation(token, TokenUser, bytes.data(), size, &size)); CloseHandle(token);
        LPWSTR sid = nullptr; assert(ConvertSidToStringSidW(reinterpret_cast<TOKEN_USER*>(bytes.data())->User.Sid, &sid));
        const auto sddl = std::wstring(L"D:P(A;OICI;FA;;;") + sid + L")"; LocalFree(sid);
        assert(ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl.c_str(), SDDL_REVISION_1, &descriptor, nullptr));
        security.lpSecurityDescriptor = descriptor;
        wchar_t temporary[MAX_PATH]{}; assert(GetTempPathW(MAX_PATH, temporary));
        // GetTempPath can contain 8.3 aliases; use the actual long namespace for
        // this fixture. Product IO must not waive actual-handle path comparison.
        wchar_t longTemporary[MAX_PATH]{}; assert(GetLongPathNameW(temporary, longTemporary, MAX_PATH));
        GUID id{}; assert(CoCreateGuid(&id) == S_OK); wchar_t text[40]{}; assert(StringFromGUID2(id, text, 40));
        root = std::filesystem::path(longTemporary) / (std::wstring(L"graf-custody-files-") + text);
        assert(CreateDirectoryW(root.c_str(), &security));
        assert(CreateDirectoryW((root / L".custody-v1").c_str(), &security));
        context.storeId[0] = 7; context.objectId[15] = 9;
        write(root / L".custody-v1" / L"store.id", CustodyBytes(context.storeId.begin(), context.storeId.end()));
        if (!service) assert(CreateDirectoryW((root / L"package-a").c_str(), &security));
    }
    void write(const std::filesystem::path& path, const CustodyBytes& bytes) {
        const auto file = CreateFileW(path.c_str(), GENERIC_WRITE, 0, &security, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
        assert(file != INVALID_HANDLE_VALUE); DWORD written = 0;
        assert(WriteFile(file, bytes.data(), static_cast<DWORD>(bytes.size()), &written, nullptr) && written == bytes.size());
        assert(FlushFileBuffers(file)); CloseHandle(file);
    }
    ~Fixture() {
        // Only the generated synthetic fixture, after all object handles close.
        std::error_code error; std::filesystem::remove_all(root, error); assert(!error);
        LocalFree(descriptor);
    }
    std::filesystem::path object() const { return (service ? root : root / L"package-a") / L".custody-v1" / roleDirectory; }
    auto open(CustodyFileAccess access) { return ProtectedCustodyFiles::open(root, service ? "" : "package-a", context, access); }
};
void publish(Fixture& fixture, ProtectedCustodyFiles& files, unsigned slot, const CustodyIndex& index) {
    const auto cipher = ProtectedCustodyCodec::sealIndex(fixture.context, slot, index); assert(cipher.ok());
    assert(files.publishIndex(slot, *cipher.value).state == CustodyPublishState::published);
}
auto writerIoCounts() {
    return std::array<unsigned, 8>{writes, reads, flushes, hashCreates, opens, renames, searches, diskChecks};
}
auto writerArtifacts(const Fixture& fixture) {
    std::vector<std::pair<std::filesystem::path, std::uintmax_t>> artifacts;
    for (const auto& entry : std::filesystem::directory_iterator(fixture.object()))
        artifacts.emplace_back(entry.path(), entry.file_size());
    std::sort(artifacts.begin(), artifacts.end());
    return artifacts;
}
void assertStickyWriter(ProtectedCustodyWriter& writer, const CustodyWriterCommit& failed) {
    const auto calls = writerIoCounts();
    const auto owned = CustodyOwnedMemory::usedBytes();
    const auto length = writer.size(), generation = writer.generation();
    for (unsigned attempt = 0; attempt < 2; ++attempt) {
        std::uint8_t output = 0xee;
        const std::uint8_t input = 9;
        const auto written = writer.writeAt(0, &input, 1);
        const auto resized = writer.setSize(length + 1);
        const auto read = writer.readAt(0, &output, 1);
        assert(!written.ok() && written.error == CustodyFileError::writerFailed);
        assert(!resized.ok() && resized.error == CustodyFileError::writerFailed);
        assert(!read.ok() && read.error == CustodyFileError::writerFailed && output == 0xee);
        const auto repeated = writer.checkpoint();
        assert(repeated.state == failed.state && repeated.error == CustodyFileError::writerFailed);
        assert(repeated.baseGeneration == failed.baseGeneration && repeated.targetGeneration == failed.targetGeneration);
        assert(repeated.nativeError == failed.nativeError);
        assert(writer.size() == length && writer.generation() == generation);
        assert(writerIoCounts() == calls && CustodyOwnedMemory::usedBytes() == owned);
    }
}
void protectedMediaWriterRegressions() {
    const auto before = CustodyOwnedMemory::usedBytes();
    const auto block = ProtectedCustodyCodec::blockBytes;
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    const std::uint8_t byte = 7;
    for (const auto fault : {FileFault::flush, FileFault::hashCreate, FileFault::renameCompletion}) {
        Fixture fixture(CustodyRole::media, L"media");
        auto opened = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 0, cancelled); assert(opened.ok());
        auto& writer = **opened.value;
        assert(writer.writeAt(0, &byte, 1).ok());
        inject(fault);
        const auto failed = writer.checkpoint();
        assert(failed.state == (fault == FileFault::renameCompletion ? CustodyCommitState::ambiguous : CustodyCommitState::notCommitted));
        assert(failed.error == (fault == FileFault::hashCreate ? CustodyFileError::hashFailed : CustodyFileError::ioFailed));
        assert(failed.baseGeneration == 0 && failed.targetGeneration == 1 && writer.generation() == 0);
        assert(renames == (fault == FileFault::renameCompletion ? 1U : 0U));
        if (fault == FileFault::renameCompletion) assert(std::filesystem::exists(fixture.object() / L"index.0"));
        if (fault != FileFault::hashCreate) assert(std::filesystem::exists(fixture.object() / L"block.0.1"));
        const auto artifacts = writerArtifacts(fixture);
        inject(FileFault::none);
        assertStickyWriter(writer, failed);
        assert(writerArtifacts(fixture) == artifacts);
        assert(!fixture.open(CustodyFileAccess::writeExisting).ok());
        opened.value->reset();
        assert(CustodyOwnedMemory::usedBytes() == before);
        auto released = fixture.open(CustodyFileAccess::writeExisting); assert(released.ok());
    }
    for (const unsigned ordinal : {1U, 2U}) {
        Fixture fixture(CustodyRole::media, L"media");
        auto opened = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 0, cancelled); assert(opened.ok());
        auto& writer = **opened.value;
        assert(writer.writeAt(0, &byte, 1).ok());
        inject(FileFault::none);
        afterRename = [ordinal] { inject(FileFault::readFailed, ordinal); };
        const auto failed = writer.checkpoint();
        afterRename = {};
        assert(reads == ordinal && failed.state == CustodyCommitState::ambiguous);
        assert(failed.error == CustodyFileError::ioFailed && failed.nativeError == ERROR_READ_FAULT);
        assert(failed.baseGeneration == 0 && failed.targetGeneration == 1 && writer.generation() == 0);
        assert(std::filesystem::exists(fixture.object() / L"index.0"));
        assert(std::filesystem::exists(fixture.object() / L"block.0.1"));
        const auto artifacts = writerArtifacts(fixture);
        inject(FileFault::none);
        assertStickyWriter(writer, failed);
        assert(writerArtifacts(fixture) == artifacts);
        assert(!fixture.open(CustodyFileAccess::writeExisting).ok());
        opened.value->reset();
        auto released = fixture.open(CustodyFileAccess::readExisting); assert(released.ok());
        auto recovered = (*released.value)->readValidatedSnapshot();
        assert(recovered.ok() && recovered.value->state == CustodySnapshotState::verified && recovered.value->index.generation == 1);
    }
    {
        Fixture fixture(CustodyRole::media, L"media");
        auto opened = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 0, cancelled); assert(opened.ok());
        auto& writer = **opened.value;
        assert(writer.writeAt(0, &byte, 1).ok() && writer.checkpoint().state == CustodyCommitState::committed);
        const auto previous = writerArtifacts(fixture);
        const std::uint8_t replacement = 8;
        assert(writer.writeAt(0, &replacement, 1).ok());
        inject(FileFault::none);
        afterFlush = [&] { cancelled->store(true); };
        const auto failed = writer.checkpoint();
        afterFlush = {}; cancelled->store(false);
        assert(failed.state == CustodyCommitState::notCommitted && failed.nativeError == ERROR_OPERATION_ABORTED);
        assert(failed.error == CustodyFileError::writerFailed && failed.baseGeneration == 1 && failed.targetGeneration == 2);
        assert(writer.generation() == 1 && writes == 1 && flushes == 1 && renames == 0);
        assert(!std::filesystem::exists(fixture.object() / L"index.1"));
        const auto artifacts = writerArtifacts(fixture);
        for (const auto& artifact : previous) assert(std::find(artifacts.begin(), artifacts.end(), artifact) != artifacts.end());
        assertStickyWriter(writer, failed);
        assert(writerArtifacts(fixture) == artifacts);
        assert(!fixture.open(CustodyFileAccess::writeExisting).ok());
        opened.value->reset();
        auto reader = openProtectedCustodyReader(fixture.root, "package-a", fixture.context, cancelled); assert(reader.ok());
        std::uint8_t output = 0; ULONG got = 0;
        assert(reader.value->stream->Read(&output, 1, &got) == S_OK && got == 1 && output == byte);
    }
    for (unsigned operation = 0; operation < 3; ++operation) {
        Fixture fixture(CustodyRole::media, L"media");
        auto opened = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 0, cancelled); assert(opened.ok());
        auto& writer = **opened.value;
        const auto limit = ProtectedCustodyCodec::logicalLimit(fixture.context.role);
        const std::uint8_t bytes[]{1, 2};
        inject(FileFault::none);
        const auto owned = CustodyOwnedMemory::usedBytes();
        const auto calls = writerIoCounts();
        const auto denied = operation == 0 ? writer.setSize(limit + 1)
            : writer.writeAt(operation == 1 ? limit - 1 : UINT64_MAX, bytes, sizeof(bytes));
        assert(!denied.ok() && denied.error == CustodyFileError::invalidInput);
        assert(writerIoCounts() == calls && CustodyOwnedMemory::usedBytes() == owned);
        assert(writer.size() == 0 && writer.generation() == 0);
        const auto failed = writer.checkpoint();
        assert(failed.state == CustodyCommitState::notCommitted && failed.error == CustodyFileError::writerFailed);
        assert(failed.baseGeneration == 0 && failed.targetGeneration == 0);
        assertStickyWriter(writer, failed);
    }
    for (unsigned operation = 0; operation < 3; ++operation) {
        Fixture fixture(CustodyRole::media, L"media");
        auto opened = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 0, cancelled); assert(opened.ok());
        auto& writer = **opened.value;
        assert(writer.setSize(1).ok());
        if (operation != 0) assert(writer.writeAt(0, &byte, 1).ok());
        const auto ownerBytes = CustodyOwnedMemory::usedBytes() - before;
        {
            CustodyBytes reservation;
            reservation.reserve(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
            assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
            inject(FileFault::none);
            CustodyWriterCommit failed;
            if (operation == 2) {
                failed = writer.checkpoint();
                assert(failed.state == CustodyCommitState::notCommitted && failed.error == CustodyFileError::allocationFailed);
                assert(failed.baseGeneration == 0 && failed.targetGeneration == 1);
            } else {
                const auto denied = operation == 0 ? writer.writeAt(0, &byte, 1) : writer.setSize(2ULL * block);
                assert(!denied.ok() && denied.error == CustodyFileError::allocationFailed);
                failed = writer.checkpoint();
                assert(failed.state == CustodyCommitState::notCommitted && failed.error == CustodyFileError::writerFailed);
                assert(failed.baseGeneration == 0 && failed.targetGeneration == 0);
            }
            assert(writes == 0 && flushes == 0 && renames == 0 && writer.generation() == 0 && writer.size() == 1);
            assertStickyWriter(writer, failed);
            assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
            opened.value->reset();
            assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit - ownerBytes);
        } // Release pressure and its Debug proxy before checking the baseline.
        assert(CustodyOwnedMemory::usedBytes() == before);
    }
    {
        Fixture fixture(CustodyRole::media, L"media");
        const CustodyBytes original(block + 3, 0x73);
        auto first = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 0, cancelled); assert(first.ok());
        assert((*first.value)->writeAt(0, original.data(), original.size()).ok());
        assert((*first.value)->checkpoint().state == CustodyCommitState::committed);
        auto retained = openProtectedCustodyReader(fixture.root, "package-a", fixture.context, cancelled); assert(retained.ok());
        first.value->reset();
        auto next = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 1, cancelled); assert(next.ok());
        assert((*next.value)->generation() == 1);
        const std::uint8_t header[]{1, 2, 3}, tail[]{8, 9};
        assert((*next.value)->writeAt(0, header, sizeof(header)).ok());
        assert((*next.value)->writeAt(block + 1, tail, sizeof(tail)).ok());
        const auto committed = (*next.value)->checkpoint();
        assert(committed.state == CustodyCommitState::committed && committed.baseGeneration == 1 && committed.targetGeneration == 2);
        assert((*next.value)->generation() == 2);
        CustodyBytes oldBytes(original.size()); ULONG got = 0;
        assert(retained.value->stream->Read(oldBytes.data(), static_cast<ULONG>(oldBytes.size()), &got) == S_OK);
        assert(got == oldBytes.size() && oldBytes == original);
        next.value->reset();
        inject(FileFault::none);
        const auto owned = CustodyOwnedMemory::usedBytes();
        const auto stale = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 1, cancelled);
        assert(!stale.ok() && stale.error == CustodyFileError::conflict && writes == 0 && flushes == 0 && renames == 0);
        assert(CustodyOwnedMemory::usedBytes() == owned);
        auto current = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 2, cancelled); assert(current.ok());
        CustodyBytes latest(original.size());
        auto read = (*current.value)->readAt(0, latest.data(), latest.size());
        assert(read.ok() && *read.value == latest.size());
        assert(std::equal(std::begin(header), std::end(header), latest.begin()));
        assert(latest[block] == 0x73 && latest[block + 1] == 8 && latest[block + 2] == 9);
    }
    inject(FileFault::none);
    assert(CustodyOwnedMemory::usedBytes() == before);
}
const char* writerProbeErrorName(CustodyFileError error) {
    switch (error) {
    case CustodyFileError::none: return "none";
    case CustodyFileError::unsupportedPlatform: return "unsupportedPlatform";
    case CustodyFileError::invalidInput: return "invalidInput";
    case CustodyFileError::unsafePath: return "unsafePath";
    case CustodyFileError::unsafeFile: return "unsafeFile";
    case CustodyFileError::identityMismatch: return "identityMismatch";
    case CustodyFileError::ioFailed: return "ioFailed";
    case CustodyFileError::invalidContent: return "invalidContent";
    case CustodyFileError::conflict: return "conflict";
    case CustodyFileError::writerFailed: return "writerFailed";
    case CustodyFileError::allocationFailed: return "allocationFailed";
    case CustodyFileError::hashFailed: return "hashFailed";
    case CustodyFileError::protectionFailed: return "protectionFailed";
    case CustodyFileError::recoveryRequired: return "recoveryRequired";
    }
    return "unknown";
}
int writerThroughputProbe(bool extended) {
    constexpr std::uint64_t mebibyte = 1024 * 1024;
    const std::uint64_t maximum = (extended ? 64 : 16) * mebibyte;
    constexpr auto block = ProtectedCustodyCodec::blockBytes;
    const auto before = CustodyOwnedMemory::usedBytes();
    std::array<unsigned, static_cast<std::size_t>(CustodyFileError::recoveryRequired) + 1> failures{};
    unsigned committed = 0, notCommitted = 0, ambiguous = 0;
    const auto fail = [&](const char* stage, CustodyFileError error, std::uint32_t native, std::uint64_t offset) {
        ++failures[static_cast<std::size_t>(error)];
        std::printf("writer-throughput failure stage=%s error=%s native=%u offset=%llu owned_bytes=%zu\n",
            stage, writerProbeErrorName(error), native, static_cast<unsigned long long>(offset), CustodyOwnedMemory::usedBytes());
        return 1;
    };
    const auto run = [&]() -> int {
        inject(FileFault::none);
        Fixture fixture(CustodyRole::canonical, L"canonical");
        auto cancellation = std::make_shared<std::atomic<bool>>(false);
        auto opened = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 0, cancellation);
        if (!opened.ok()) return fail("open", opened.error, opened.nativeError, 0);
        auto& writer = **opened.value;
        CustodyBytes synthetic(block);
        for (std::size_t position = 0; position < synthetic.size(); ++position)
            synthetic[position] = static_cast<std::uint8_t>((position * 37 + 0x6d) & 0xff);
        std::printf("writer-throughput synthetic_only=1 role=canonical block_bytes=%u maximum_bytes=%llu "
            "elapsed_scope=sequential_writes checkpoint_timing=writeAt_including_automatic_checkpoint owned_before_bytes=%zu\n",
            block, static_cast<unsigned long long>(maximum), before);
        const auto started = std::chrono::steady_clock::now();
        const auto initialReads = reads, initialHashes = hashCreates;
        std::uint64_t milestone = mebibyte;
        for (std::uint64_t offset = 0; offset < maximum; offset += block) {
            const auto sequence = offset / block;
            for (unsigned position = 0; position < 8; ++position)
                synthetic[position] = static_cast<std::uint8_t>(sequence >> (position * 8));
            const auto checkpointStarted = std::chrono::steady_clock::now();
            const auto written = writer.writeAt(offset, synthetic.data(), synthetic.size());
            const auto checkpointFinished = std::chrono::steady_clock::now();
            if (!written.ok()) {
                const auto terminal = writer.checkpoint();
                if (terminal.state == CustodyCommitState::ambiguous) ++ambiguous;
                else if (terminal.state == CustodyCommitState::notCommitted) ++notCommitted;
                else ++committed;
                return fail("writeAt", written.error, written.nativeError, offset);
            }
            if (*written.value != block || writer.size() != offset + block || writer.generation() != sequence + 1)
                return fail("checkpointInvariant", CustodyFileError::conflict, 0, offset);
            ++committed;
            if (offset + block == milestone) {
                const auto elapsed = std::chrono::duration<double, std::milli>(checkpointFinished - started).count();
                const auto lastCheckpoint = std::chrono::duration<double, std::milli>(checkpointFinished - checkpointStarted).count();
                std::printf("writer-throughput mib=%llu cumulative_elapsed_ms=%.3f last_write_checkpoint_ms=%.3f "
                    "generation=%llu committed=%u owned_bytes=%zu cumulative_native_reads=%u cumulative_native_hash_creates=%u\n",
                    static_cast<unsigned long long>(milestone / mebibyte), elapsed, lastCheckpoint,
                    static_cast<unsigned long long>(writer.generation()), committed, CustodyOwnedMemory::usedBytes(),
                    reads - initialReads, hashCreates - initialHashes);
                std::fflush(stdout);
                milestone *= 2;
            }
        }
        return 0;
    };
    int status = 0;
    try { status = run(); }
    catch (const std::bad_alloc&) { status = fail("allocation", CustodyFileError::allocationFailed, 0, 0); }
    catch (const std::system_error& error) {
        status = fail("filesystem", CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value()), 0);
    }
    if (CustodyOwnedMemory::usedBytes() != before) status = fail("ownerRelease", CustodyFileError::allocationFailed, 0, maximum);
    std::printf("writer-throughput summary committed=%u notCommitted=%u ambiguous=%u owned_after_release_bytes=%zu status=%d\n",
        committed, notCommitted, ambiguous, CustodyOwnedMemory::usedBytes(), status);
    for (std::size_t index = 1; index < failures.size(); ++index)
        std::printf("writer-throughput failure_count error=%s count=%u\n", writerProbeErrorName(static_cast<CustodyFileError>(index)), failures[index]);
    return status;
}
void protectedMediaWriter() {
    const auto before = CustodyOwnedMemory::usedBytes();
    protectedMediaWriterRegressions();
    const auto block = ProtectedCustodyCodec::blockBytes;
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    for (const auto role : {CustodyRole::media, CustodyRole::playback}) {
        Fixture fixture(role, role == CustodyRole::media ? L"media" : L"playback");
        auto opened = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 0, cancelled); assert(opened.ok());
        auto& writer = **opened.value;
        CustodyBytes original(block + 3, 0x73);
        assert(writer.writeAt(0, original.data(), original.size()).ok() && writer.generation() == 0);
        assert(writer.checkpoint().state == CustodyCommitState::committed && writer.generation() == 1);
        auto old = openProtectedCustodyReader(fixture.root, "package-a", fixture.context, cancelled); assert(old.ok());
        assert(writer.setSize(3ULL * block + 5).ok());
        CustodyBytes gap(block + 5, 0xff);
        auto read = writer.readAt(2ULL * block, gap.data(), gap.size());
        assert(read.ok() && *read.value == gap.size() && std::all_of(gap.begin(), gap.end(), [](auto b) { return b == 0; }));
        const std::uint8_t header[]{1, 2, 3};
        assert(writer.writeAt(0, header, 3).ok());
        assert(writer.checkpoint().state == CustodyCommitState::committed && writer.generation() == 2);
        assert(writer.setSize(block + 2).ok());
        assert(writer.checkpoint().state == CustodyCommitState::committed && writer.generation() == 3);
        CustodyBytes retained(original.size()); ULONG got = 0;
        assert(old.value->stream->Read(retained.data(), static_cast<ULONG>(retained.size()), &got) == S_OK && retained == original);
        opened.value->reset();
        auto files = fixture.open(CustodyFileAccess::readExisting); assert(files.ok());
        auto snapshot = (*files.value)->readValidatedSnapshot(); assert(snapshot.ok() && snapshot.value->index.logicalLength == block + 2);
        auto current = openProtectedCustodyReader(fixture.root, "package-a", fixture.context, cancelled); assert(current.ok());
        CustodyBytes value(block + 8, 0xff);
        assert(current.value->stream->Read(value.data(), static_cast<ULONG>(value.size()), &got) == S_FALSE && got == block + 2);
        assert(std::equal(std::begin(header), std::end(header), value.begin()) && value[block] == 0x73 && value[block + 1] == 0x73);
    }
    {
        Fixture fixture(CustodyRole::canonical, L"canonical");
        auto opened = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 0, cancelled); assert(opened.ok());
        auto& writer = **opened.value;
        CustodyBytes bytes(block + 7, 0x5a);
        assert(writer.writeAt(0, bytes.data(), bytes.size()).ok() && writer.generation() == 1 && writer.size() == bytes.size());
        auto prefix = openProtectedCustodyReader(fixture.root, "package-a", fixture.context, cancelled); assert(prefix.ok());
        STATSTG stat{}; assert(prefix.value->stream->Stat(&stat, STATFLAG_NONAME) == S_OK && stat.cbSize.QuadPart == block);
        assert(writer.checkpoint().state == CustodyCommitState::committed && writer.generation() == 2);
        assert(writer.setSize(0).ok() && writer.checkpoint().state == CustodyCommitState::committed && writer.generation() == 3);
        assert(writer.readAt(UINT64_MAX, nullptr, 0).ok());
        assert(!writer.writeAt(UINT64_MAX, bytes.data(), 1).ok());
        assert(writer.checkpoint().error == CustodyFileError::writerFailed);
    }
    for (const auto fault : {FileFault::flush, FileFault::renameCompletion, FileFault::hashCreate}) {
        Fixture fixture(CustodyRole::media, L"media");
        auto opened = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 0, cancelled); assert(opened.ok());
        const std::uint8_t byte = 7; assert((*opened.value)->writeAt(0, &byte, 1).ok());
        inject(fault);
        const auto commit = (*opened.value)->checkpoint();
        assert(commit.state != CustodyCommitState::committed && commit.error != CustodyFileError::none);
        inject(FileFault::none); const auto calls = writes;
        assert(!(*opened.value)->writeAt(0, &byte, 1).ok() && writes == calls);
        assert((*opened.value)->checkpoint().error == CustodyFileError::writerFailed && writes == calls);
        assert(!fixture.open(CustodyFileAccess::writeExisting).ok());
    }
    {
        Fixture fixture(CustodyRole::media, L"media");
        auto opened = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 0, cancelled); assert(opened.ok());
        const std::uint8_t byte = 9; assert((*opened.value)->writeAt(0, &byte, 1).ok());
        afterRename = [&] { cancelled->store(true); };
        assert((*opened.value)->checkpoint().state == CustodyCommitState::committed);
        afterRename = {}; assert(!(*opened.value)->writeAt(0, &byte, 1).ok()); cancelled->store(false);
    }
    {
        std::vector<std::unique_ptr<Fixture>> fixtures;
        std::vector<std::unique_ptr<ProtectedCustodyWriter>> writers;
        const std::uint8_t byte = 4;
        for (unsigned i = 0; i < 5; ++i) {
            fixtures.emplace_back(new Fixture(CustodyRole::media, L"media"));
            auto opened = ProtectedCustodyWriter::open(fixtures.back()->root, "package-a", fixtures.back()->context, 0, cancelled); assert(opened.ok());
            writers.push_back(std::move(*opened.value));
            const auto result = writers.back()->writeAt(0, &byte, 1);
            assert(result.ok() == (i < 4));
        }
        Fixture queue;
        const auto calls = writes;
        assert(commitProtectedCustodyMetadata(queue.root, "", queue.context, 0, CustodyBytes{1}, cancelled).error == CustodyFileError::allocationFailed);
        assert(writes == calls); // Dirty admission is shared with metadata, before IO.
        writers.clear(); fixtures.clear();
        assert(commitProtectedCustodyMetadata(queue.root, "", queue.context, 0, CustodyBytes{1}, cancelled).state == CustodyCommitState::committed);
    }
    {
        Fixture fixture(CustodyRole::media, L"media");
        auto opened = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 0, cancelled); assert(opened.ok());
        auto& writer = **opened.value;
        CustodyBytes expected;
        for (unsigned i = 0; i < 24; ++i) {
            if (i % 3 == 0) {
                const auto length = i % 6 == 0 ? 0 : (i % 4) * block + i + 1;
                assert(writer.setSize(length).ok()); expected.resize(length, 0);
            } else {
                const auto offset = (i % 3) * block + (i % 2 ? block - 3 : 11);
                const CustodyBytes part(7 + i, static_cast<std::uint8_t>(i));
                assert(writer.writeAt(offset, part.data(), part.size()).ok());
                if (offset + part.size() > expected.size()) expected.resize(offset + part.size(), 0);
                std::copy(part.begin(), part.end(), expected.begin() + offset);
            }
            CustodyBytes actual(expected.size() + 7, 0xee);
            auto read = writer.readAt(0, actual.data(), actual.size());
            assert(read.ok() && *read.value == expected.size() && std::equal(expected.begin(), expected.end(), actual.begin()));
            assert(actual.back() == 0xee);
            if (i % 4 == 3) assert(writer.checkpoint().state == CustodyCommitState::committed);
        }
        assert(writer.checkpoint().state == CustodyCommitState::committed);
        CustodyBytes output(expected.size(), 0xff);
        inject(FileFault::readFailed, 3); // First full DATA envelope takes two native reads; the next fails.
        auto read = writer.readAt(0, output.data(), output.size());
        assert(!read.ok() && read.nativeError == ERROR_READ_FAULT);
        assert(std::all_of(output.begin(), output.begin() + 2 * block, [](auto b) { return b == 0; }));
        assert(output[2 * block] == 0xff); // No partial-byte acknowledgment on failure.
        inject(FileFault::none);
        assert(writer.checkpoint().error == CustodyFileError::writerFailed);
    }
    {
        std::vector<std::unique_ptr<Fixture>> fixtures;
        std::vector<std::unique_ptr<ProtectedCustodyWriter>> writers;
        for (unsigned i = 0; i < 33; ++i) {
            fixtures.emplace_back(new Fixture(CustodyRole::media, L"media"));
            const auto calls = writes;
            auto opened = ProtectedCustodyWriter::open(fixtures.back()->root, "package-a", fixtures.back()->context, 0, cancelled);
            assert(opened.ok() == (i < 32));
            if (i < 32) writers.push_back(std::move(*opened.value));
            else assert(opened.error == CustodyFileError::allocationFailed && calls == writes);
        }
        assert(writers.front()->checkpoint().state == CustodyCommitState::committed);
        assert(openProtectedCustodyReader(fixtures.front()->root, "package-a", fixtures.front()->context, cancelled).error == CustodyFileError::allocationFailed);
        writers.clear(); fixtures.clear();
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}
void protectedMetadata() {
    const auto before = CustodyOwnedMemory::usedBytes();
    {
        Fixture fixture;
        auto cancellation = std::make_shared<std::atomic<bool>>(false);
        const CustodyBytes initial{1, 2, 3};
        std::optional<CustodyMetadataCommit> birth;
        birth.emplace(commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, initial, cancellation));
        assert(birth->state == CustodyCommitState::committed && birth->baseGeneration == 0 && birth->targetGeneration == 1);
        assert(birth->lease && birth->snapshot && birth->snapshot->index.generation == 1);
        for (unsigned slot = 0; slot < 2; ++slot) {
            auto cipher = birth->lease->readIndex(slot); assert(cipher.ok());
            auto index = ProtectedCustodyCodec::openIndex(fixture.context, slot, *cipher.value);
            assert(index.ok() && index.value->generation == 1 && index.value->logicalLength == initial.size());
        }
        auto held = fixture.open(CustodyFileAccess::writeExisting); assert(!held.ok());
        birth.reset();
        auto reader = openProtectedCustodyReader(fixture.root, "", fixture.context, cancellation); assert(reader.ok());
        CustodyBytes replacement(ProtectedCustodyCodec::blockBytes + 1, 0x71);
        std::optional<CustodyMetadataCommit> update;
        update.emplace(commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 1, replacement, cancellation));
        assert(update->state == CustodyCommitState::committed && update->targetGeneration == 2);
        assert(update->snapshot->index.entries.size() == 2);
        const auto lastVersion = update->snapshot->index.entries[0].version;
        std::array<std::uint8_t, 3> old{}; ULONG got = 0;
        assert(reader.value->stream->Read(old.data(), 3, &got) == S_OK && got == 3 && old[0] == 1 && old[2] == 3);
        update.reset();
        inject(FileFault::none);
        std::optional<CustodyMetadataCommit> stale;
        stale.emplace(commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 1, initial, cancellation));
        assert(stale->state == CustodyCommitState::notCommitted && stale->error == CustodyFileError::conflict && writes == 0);
        stale.reset();
        cancellation->store(true); inject(FileFault::none);
        auto cancelled = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 2, initial, cancellation);
        assert(cancelled.state == CustodyCommitState::notCommitted && cancelled.nativeError == ERROR_OPERATION_ABORTED && writes == 0);
        cancellation->store(false);
        auto smaller = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 2, initial, cancellation);
        assert(smaller.state == CustodyCommitState::committed && smaller.targetGeneration == 3);
        assert(smaller.snapshot->index.logicalLength == 3 && smaller.snapshot->index.entries.size() == 1);
        assert(smaller.snapshot->index.entries[0].version > lastVersion);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
    {
        Fixture fixture;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        const CustodyBytes value{1, 2, 3};
        assert(commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, value, cancelled).state == CustodyCommitState::committed);
        afterFlush = [&] { cancelled->store(true); };
        {
            auto interrupted = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 1, value, cancelled);
            assert(interrupted.state == CustodyCommitState::notCommitted && interrupted.nativeError == ERROR_OPERATION_ABORTED);
            assert(interrupted.lease && std::filesystem::exists(fixture.object() / L"block.0.2"));
        }
        afterFlush = {}; cancelled->store(false);
        auto retry = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 1, value, cancelled);
        assert(retry.state == CustodyCommitState::committed && retry.snapshot->index.entries[0].version == 3);
        assert(std::filesystem::exists(fixture.object() / L"block.0.1") && std::filesystem::exists(fixture.object() / L"block.0.2"));
    }
    {
        Fixture fixture;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        afterRename = [&] { cancelled->store(true); };
        auto birth = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, CustodyBytes{5}, cancelled);
        afterRename = {};
        assert(cancelled->load() && birth.state == CustodyCommitState::committed && birth.snapshot->index.generation == 1);
        assert(birth.lease->readIndex(0).ok() && birth.lease->readIndex(1).ok());
    }
    {
        Fixture fixture;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        unsigned published = 0;
        afterRename = [&] { if (++published == 1) inject(FileFault::hashCreate, 2); };
        {
            auto result = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, CustodyBytes{7}, cancelled);
            afterRename = {}; inject(FileFault::none);
            assert(result.state == CustodyCommitState::ambiguous && result.error == CustodyFileError::hashFailed && !result.snapshot);
            assert(result.lease && result.lease->nextBlockVersion(0).error == CustodyFileError::writerFailed);
            const auto plain = CustodyBytes{8};
            auto block = ProtectedCustodyCodec::sealBlock(fixture.context, 0, 2, plain); assert(block.ok());
            const auto writesBefore = writes;
            assert(result.lease->writeBlock(0, 2, 1, *block.value).error == CustodyFileError::writerFailed && writes == writesBefore);
            auto slot0 = result.lease->readIndex(0); assert(slot0.ok());
            auto index = ProtectedCustodyCodec::openIndex(fixture.context, 0, *slot0.value); assert(index.ok());
            index.value->generation = 2;
            auto index1 = ProtectedCustodyCodec::sealIndex(fixture.context, 1, *index.value); assert(index1.ok());
            const auto denied = result.lease->publishIndex(1, *index1.value);
            assert(denied.state == CustodyPublishState::notPublished && denied.error == CustodyFileError::writerFailed && writes == writesBefore);
            assert(!fixture.open(CustodyFileAccess::writeExisting).ok());
            assert(std::filesystem::exists(fixture.object() / L"block.0.1") && !std::filesystem::exists(fixture.object() / L"index.1"));
        }
        auto restarted = fixture.open(CustodyFileAccess::readExisting); assert(restarted.ok());
        assert(!(*restarted.value)->readValidatedSnapshot().ok());
    }
    for (unsigned failAt : {3U, 4U, 5U, 6U}) {
        Fixture fixture;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        inject(FileFault::flush, failAt); // id, block, index0-temp, index0-published, index1-temp, index1-published.
        {
            auto failed = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, CustodyBytes{7}, cancelled);
            assert(failed.state == (failAt == 3 ? CustodyCommitState::notCommitted : CustodyCommitState::ambiguous));
            assert(failed.error == CustodyFileError::ioFailed && failed.nativeError == ERROR_WRITE_FAULT && !failed.snapshot);
            assert(failed.lease && !failed.lease->nextBlockVersion(0).ok());
        }
        inject(FileFault::none);
        auto preserved = fixture.open(CustodyFileAccess::readExisting); assert(preserved.ok());
        const auto recovered = (*preserved.value)->readValidatedSnapshot();
        if (failAt < 6) assert(!recovered.ok());
        else assert(recovered.ok() && recovered.value->state == CustodySnapshotState::verified); // Physical truth != prior ACK.
    }
    for (const auto fault : {FileFault::rename, FileFault::renameCompletion, FileFault::write, FileFault::hashCreate}) {
        Fixture fixture;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        assert(commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, CustodyBytes{1}, cancelled).state == CustodyCommitState::committed);
        inject(fault);
        {
            auto result = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 1, CustodyBytes{2}, cancelled);
            assert(result.state == ((fault == FileFault::rename || fault == FileFault::renameCompletion)
                ? CustodyCommitState::ambiguous : CustodyCommitState::notCommitted));
            assert(result.error != CustodyFileError::none && !result.snapshot);
        }
        inject(FileFault::none);
    }
    {
        Fixture fixture;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        afterRename = [] { inject(FileFault::readFailed, 1); };
        auto result = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, CustodyBytes{1}, cancelled);
        afterRename = {}; inject(FileFault::none);
        assert(result.state == CustodyCommitState::ambiguous && result.nativeError == ERROR_READ_FAULT && !result.snapshot);
    }
    {
        Fixture fixture;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        unsigned published = 0;
        afterRename = [&] { if (++published == 2) inject(FileFault::readFailed, 2); };
        auto result = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, CustodyBytes{1}, cancelled);
        afterRename = {}; inject(FileFault::none);
        assert(published == 2 && result.state == CustodyCommitState::ambiguous && result.nativeError == ERROR_READ_FAULT && !result.snapshot);
    }
    {
        Fixture fixture;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        assert(commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, CustodyBytes{1}, cancelled).state == CustodyCommitState::committed);
        assert(commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 1, CustodyBytes{2}, cancelled).state == CustodyCommitState::committed);
        assert(DeleteFileW((fixture.object() / L"index.1").c_str()));
        inject(FileFault::none);
        auto lost = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 2, CustodyBytes{3}, cancelled);
        assert(lost.state == CustodyCommitState::notCommitted && lost.error == CustodyFileError::recoveryRequired && writes == 0);
        auto noHealing = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, CustodyBytes{3}, cancelled);
        assert(noHealing.state == CustodyCommitState::notCommitted && noHealing.error == CustodyFileError::conflict && writes == 0);
    }
    {
        Fixture fixture;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        assert(commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, CustodyBytes{1}, cancelled).state == CustodyCommitState::committed);
        fixture.write(fixture.object() / L"block.0.41", CustodyBytes{0}); // Orphan need not decrypt to be occupied.
        fixture.write(fixture.object() / L"block.0.0042", CustodyBytes{0}); // Unknown filename preserved, not authority.
        {
            auto next = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 1, CustodyBytes{2}, cancelled);
            assert(next.state == CustodyCommitState::committed && next.snapshot->index.entries[0].version == 42);
        }
        assert(std::filesystem::exists(fixture.object() / L"block.0.41") && std::filesystem::exists(fixture.object() / L"block.0.0042"));
        for (unsigned mode = 0; mode < 2; ++mode) {
            inject(FileFault::none); findFailure = mode == 0; nextFailure = mode == 1;
            auto fail = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 2, CustodyBytes{3}, cancelled);
            findFailure = nextFailure = false;
            assert(fail.state == CustodyCommitState::notCommitted && fail.nativeError == ERROR_ACCESS_DENIED && writes == 0);
        }
        fixture.write(fixture.object() / L"block.0.18446744073709551615", CustodyBytes{0});
        inject(FileFault::none);
        {
            auto full = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 2, CustodyBytes{3}, cancelled);
            assert(full.state == CustodyCommitState::notCommitted && full.error == CustodyFileError::invalidInput && writes == 0);
        }
        fixture.write(fixture.object() / L"block.0.18446744073709551616", CustodyBytes{0});
        auto overflow = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 2, CustodyBytes{3}, cancelled);
        assert(overflow.state == CustodyCommitState::notCommitted && overflow.error == CustodyFileError::invalidContent && writes == 0);
    }
    {
        Fixture fixture;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        const CustodyBytes value{1};
        const CustodyBytes oversize(4 * 1024 * 1024 + 1, 0);
        inject(FileFault::none);
        assert(commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, oversize, cancelled).error == CustodyFileError::invalidInput);
        assert(commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, CustodyBytes{}, cancelled).error == CustodyFileError::invalidInput);
        assert(commitProtectedCustodyMetadata(fixture.root, "", fixture.context, UINT64_MAX, value, cancelled).error == CustodyFileError::invalidInput);
        assert(commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, value, {}).error == CustodyFileError::invalidInput && writes == 0);
        {
            // Include the Debug iterator proxy before filling remaining capacity.
            CustodyBytes budget;
            budget.reserve(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
            auto denied = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, value, cancelled);
            assert(denied.state == CustodyCommitState::notCommitted && denied.error == CustodyFileError::allocationFailed && writes == 0);
        }
        CustodyBytes maximum(4 * 1024 * 1024, 0x52);
        auto accepted = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, maximum, cancelled);
        assert(accepted.state == CustodyCommitState::committed && accepted.snapshot->index.entries.size() == 16);
        auto reader = openProtectedCustodyReader(fixture.root, "", fixture.context, cancelled); assert(reader.ok());
        std::array<std::uint8_t, 7> tail{}; ULONG got = 0; LARGE_INTEGER last{}; last.QuadPart = -7;
        assert(reader.value->stream->Seek(last, STREAM_SEEK_END, nullptr) == S_OK);
        assert(reader.value->stream->Read(tail.data(), 7, &got) == S_OK && got == 7 && tail[0] == 0x52 && tail[6] == 0x52);
    }
    for (const auto& role : {std::pair{CustodyRole::manifest, L"manifest"}, std::pair{CustodyRole::recovery, L"recovery"},
        std::pair{CustodyRole::packageState, L"package-state"}, std::pair{CustodyRole::bootstrap, L"bootstrap"},
        std::pair{CustodyRole::migrationIntent, L"migration-intent"}}) {
        Fixture fixture(role.first, role.second);
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        const auto limit = ProtectedCustodyCodec::logicalLimit(role.first);
        assert(limit == 64 * 1024U);
        CustodyBytes over(static_cast<std::size_t>(limit) + 1, 1);
        inject(FileFault::none);
        assert(commitProtectedCustodyMetadata(fixture.root, fixture.service ? "" : "package-a", fixture.context, 0, over, cancelled).error
            == CustodyFileError::invalidInput && writes == 0);
        over.pop_back();
        auto accepted = commitProtectedCustodyMetadata(fixture.root, fixture.service ? "" : "package-a", fixture.context, 0, over, cancelled);
        assert(accepted.state == CustodyCommitState::committed && accepted.snapshot->index.logicalLength == limit);
        auto reader = openProtectedCustodyReader(fixture.root, fixture.service ? "" : "package-a", fixture.context, cancelled);
        assert(reader.ok());
        STATSTG stat{};
        assert(reader.value->stream->Stat(&stat, STATFLAG_NONAME) == S_OK && stat.cbSize.QuadPart == limit);
        CustodyBytes restored(static_cast<std::size_t>(limit)); ULONG got = 0;
        assert(reader.value->stream->Read(restored.data(), static_cast<ULONG>(limit), &got) == S_OK && got == limit);
        assert(restored == over);
    }
    {
        Fixture fixture, second;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        std::optional<CustodyMetadataCommit> held;
        held.emplace(commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, CustodyBytes{1}, cancelled));
        assert(held->state == CustodyCommitState::committed);
        auto reader = openProtectedCustodyReader(fixture.root, "", fixture.context, cancelled); assert(reader.ok());
        std::vector<Microsoft::WRL::ComPtr<IStream>> clones;
        for (unsigned i = 0; i < 30; ++i) {
            Microsoft::WRL::ComPtr<IStream> clone;
            assert(reader.value->stream->Clone(clone.GetAddressOf()) == S_OK); clones.push_back(std::move(clone));
        }
        Microsoft::WRL::ComPtr<IStream> refused;
        assert(reader.value->stream->Clone(refused.GetAddressOf()) == STG_E_INSUFFICIENTMEMORY);
        inject(FileFault::none);
        auto denied = commitProtectedCustodyMetadata(second.root, "", second.context, 0, CustodyBytes{1}, cancelled);
        assert(denied.error == CustodyFileError::allocationFailed && writes == 0 && !denied.lease);
        held.reset(); // Actual result release, not an independently reset public pin.
        auto afterRelease = commitProtectedCustodyMetadata(second.root, "", second.context, 0, CustodyBytes{1}, cancelled);
        assert(afterRelease.state == CustodyCommitState::committed);
    }
    {
        Fixture fixture;
        auto opened = fixture.open(CustodyFileAccess::createNew); assert(opened.ok());
        diskOverride = true;
        diskInfo = {}; diskInfo.SectorsPerAllocationUnit = 8; diskInfo.BytesPerSector = 512;
        diskInfo.ActualTotalAllocationUnits = 1'000'000;
        diskInfo.CallerTotalAllocationUnits = 1; // Must NOT become the 10% base.
        diskInfo.ActualAvailableAllocationUnits = diskInfo.CallerAvailableAllocationUnits = 100'001;
        assert((*opened.value)->checkWriteReserve(1, 1).ok()); // Exactly one 4KiB rounded file above actual 10% reserve.
        diskInfo.CallerAvailableAllocationUnits = 100'000;
        auto full = (*opened.value)->checkWriteReserve(1, 1); assert(!full.ok() && full.nativeError == ERROR_DISK_FULL);
        diskInfo.CallerAvailableAllocationUnits = 100'001;
        assert(!(*opened.value)->checkWriteReserve(UINT64_MAX, 1).ok());
        diskInfo.BytesPerSector = 0; assert(!(*opened.value)->checkWriteReserve(1, 1).ok());
        diskFailure = E_ACCESSDENIED;
        auto query = (*opened.value)->checkWriteReserve(1, 1); assert(!query.ok() && query.nativeError == static_cast<std::uint32_t>(E_ACCESSDENIED));
        diskFailure = S_OK; diskOverride = false;
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}
CustodyIndex snapshotData(Fixture&, ProtectedCustodyFiles&, std::uint64_t);
// Test-only COM destination: accepts a prefix, then runs a real synchronous
// callback. No product fault knob, file output or content retained by the sink.
class CallbackSink final : public IStream {
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
        assert(count <= ProtectedCustodyCodec::blockBytes);
        largest = std::max(largest, count);
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
void protectedReader() {
    inject(FileFault::none);
    const auto baseline = CustodyOwnedMemory::usedBytes();
    {
        Fixture fixture(CustodyRole::canonical, L"canonical");
        const auto blockBytes = ProtectedCustodyCodec::blockBytes;
        CustodyBytes full(blockBytes, 0x42), tail{1, 2, 3, 4};
        CustodyIndex index{1, 2ULL * blockBytes + tail.size(), {}};
        {
            auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
            auto cipher = ProtectedCustodyCodec::sealBlock(fixture.context, 0, 1, full); assert(cipher.ok());
            auto first = (*files.value)->writeBlock(0, 1, blockBytes, *cipher.value); assert(first.ok());
            cipher = ProtectedCustodyCodec::sealBlock(fixture.context, 2, 1, tail); assert(cipher.ok());
            auto last = (*files.value)->writeBlock(2, 1, 4, *cipher.value); assert(last.ok());
            index.entries = {{1, *first.value, 0}, {0, 0, 1}, {1, *last.value, 0}};
            publish(fixture, **files.value, 0, index);
        }
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        for (unsigned attempt = 0; attempt < 40; ++attempt) {
            const auto invalid = openProtectedCustodyReader(fixture.root, "../outside", fixture.context, cancelled);
            assert(!invalid.ok() && invalid.error == CustodyFileError::invalidInput); // Failed-open admission rolls back.
        }
        auto opened = openProtectedCustodyReader(fixture.root, "package-a", fixture.context, cancelled);
        assert(opened.ok() && opened.value->state == CustodySnapshotState::verified);
        auto& stream = opened.value->stream;
        STATSTG stat{};
        assert(stream->Stat(&stat, STATFLAG_NONAME) == S_OK && stat.cbSize.QuadPart == index.logicalLength && stat.grfMode == STGM_READ);
        assert(stream->Stat(&stat, 0xffffffff) == STG_E_INVALIDFLAG);
        LARGE_INTEGER offset{}; ULARGE_INTEGER position{}; ULONG got = 99;
        std::array<std::uint8_t, 8> bytes{};
        inject(FileFault::none);
        assert(stream->Read(bytes.data(), 4, &got) == S_OK && got == 4 && bytes[0] == 0x42 && reads > 0);
        const auto cachedCharge = CustodyOwnedMemory::usedBytes();
        Microsoft::WRL::ComPtr<IStream> clone;
        assert(stream->Clone(&clone) == S_OK);
        const auto cloneCharge = CustodyOwnedMemory::usedBytes();
        assert(cloneCharge > cachedCharge); // Fixed COM object is charged, not another plaintext cache.
        const auto loaded = reads;
        assert(clone->Read(bytes.data(), 4, &got) == S_OK && got == 4 && reads == loaded); // Same cache, own cursor.
        assert(CustodyOwnedMemory::usedBytes() == cloneCharge);
        clone.Reset();
        assert(CustodyOwnedMemory::usedBytes() == cachedCharge); // Same live source/state/cache, actual COM release.
        assert(stream->Clone(&clone) == S_OK);
        assert(clone->Read(bytes.data(), 4, &got) == S_OK && got == 4 && reads == loaded);
        assert(CustodyOwnedMemory::usedBytes() == cloneCharge);
        assert(stream->Seek(offset, STREAM_SEEK_CUR, &position) == S_OK && position.QuadPart == 4);
        offset.QuadPart = blockBytes - 2;
        assert(stream->Seek(offset, STREAM_SEEK_SET, nullptr) == S_OK);
        assert(stream->Read(bytes.data(), 6, &got) == S_OK && got == 6 && bytes[0] == 0x42 && bytes[1] == 0x42 && bytes[2] == 0 && bytes[5] == 0);
        offset.QuadPart = -2;
        assert(stream->Seek(offset, STREAM_SEEK_END, nullptr) == S_OK);
        assert(stream->Read(bytes.data(), 8, &got) == S_FALSE && got == 2 && bytes[0] == 3 && bytes[1] == 4);
        assert(stream->Read(bytes.data(), 1, &got) == S_FALSE && got == 0);
        offset.QuadPart = -1;
        assert(stream->Seek(offset, STREAM_SEEK_SET, nullptr) == STG_E_INVALIDFUNCTION);
        offset.QuadPart = (std::numeric_limits<LONGLONG>::min)();
        assert(stream->Seek(offset, STREAM_SEEK_CUR, nullptr) == STG_E_INVALIDFUNCTION);
        offset.QuadPart = (std::numeric_limits<LONGLONG>::max)();
        assert(stream->Seek(offset, STREAM_SEEK_SET, nullptr) == S_OK);
        offset.QuadPart = 1;
        assert(stream->Seek(offset, STREAM_SEEK_CUR, nullptr) == STG_E_INVALIDFUNCTION);
        assert(stream->Read(bytes.data(), 1, &got) == S_FALSE && got == 0);
        assert(stream->Write(bytes.data(), 1, &got) == STG_E_ACCESSDENIED && got == 0);
        assert(stream->SetSize({}) == STG_E_ACCESSDENIED);
        assert(stream->Commit(STGC_DEFAULT) == S_OK && stream->Commit(STGC_OVERWRITE) == STG_E_INVALIDFLAG);
        assert(stream->Revert() == STG_E_INVALIDFUNCTION && stream->LockRegion({}, {}, 0) == STG_E_INVALIDFUNCTION);
        offset.QuadPart = 0;
        assert(stream->Seek(offset, STREAM_SEEK_SET, nullptr) == S_OK);
        Microsoft::WRL::ComPtr<IStream> destination;
        assert(CreateStreamOnHGlobal(nullptr, TRUE, &destination) == S_OK);
        ULARGE_INTEGER requested{}, read{}, written{}; requested.QuadPart = index.logicalLength + 1;
        assert(stream->CopyTo(destination.Get(), requested, &read, &written) == S_FALSE && read.QuadPart == index.logicalLength && written.QuadPart == read.QuadPart);
        assert(destination->Seek(offset, STREAM_SEEK_SET, nullptr) == S_OK);
        assert(destination->Read(bytes.data(), 4, &got) == S_OK && bytes[0] == 0x42);
        assert(stream->Seek(offset, STREAM_SEEK_SET, nullptr) == S_OK);
        requested.QuadPart = 4;
        assert(stream->CopyTo(clone.Get(), requested, &read, &written) == STG_E_ACCESSDENIED && read.QuadPart == 4 && written.QuadPart == 0);
        for (bool eof : {false, true}) {
            auto signal = std::make_shared<std::atomic<bool>>(false);
            auto source = openProtectedCustodyReader(fixture.root, "package-a", fixture.context, signal); assert(source.ok());
            Microsoft::WRL::ComPtr<CallbackSink> sink; sink.Attach(new CallbackSink);
            sink->afterWrite = [signal] { signal->store(true); };
            if (eof) { offset.QuadPart = -4; assert(source.value->stream->Seek(offset, STREAM_SEEK_END, nullptr) == S_OK); }
            requested.QuadPart = eof ? 8 : 4;
            assert(source.value->stream->CopyTo(sink.Get(), requested, &read, &written) == HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED));
            assert(read.QuadPart == 4 && written.QuadPart == 4); // Accepted target prefix did not roll back.
            signal->store(false);
            assert(FAILED(source.value->stream->Read(bytes.data(), 1, &got)) && got == 0);
        }
        {
            auto source = openProtectedCustodyReader(fixture.root, "package-a", fixture.context, cancelled); assert(source.ok());
            Microsoft::WRL::ComPtr<IStream> observer; assert(source.value->stream->Clone(&observer) == S_OK);
            Microsoft::WRL::ComPtr<CallbackSink> sink; sink.Attach(new CallbackSink);
            sink->afterWrite = [&] {
                LARGE_INTEGER end{}; end.QuadPart = -4; assert(observer->Seek(end, STREAM_SEEK_END, nullptr) == S_OK);
                inject(FileFault::readFailed, 1);
                assert(FAILED(observer->Read(bytes.data(), 4, &got)) && got == 0);
                inject(FileFault::none);
            };
            requested.QuadPart = 4;
            assert(FAILED(source.value->stream->CopyTo(sink.Get(), requested, &read, &written)) && read.QuadPart == 4 && written.QuadPart == 4);
        }
        {
            auto source = openProtectedCustodyReader(fixture.root, "package-a", fixture.context, cancelled); assert(source.ok());
            Microsoft::WRL::ComPtr<CallbackSink> sink; sink.Attach(new CallbackSink);
            requested.QuadPart = 4; sink->limit = 2;
            assert(source.value->stream->CopyTo(sink.Get(), requested, &read, &written) == STG_E_MEDIUMFULL && read.QuadPart == 4 && written.QuadPart == 2);
            sink->result = STG_E_WRITEFAULT;
            assert(source.value->stream->CopyTo(sink.Get(), requested, &read, &written) == STG_E_WRITEFAULT && read.QuadPart == 4 && written.QuadPart == 2);
            sink->result = S_FALSE; sink->limit = (std::numeric_limits<ULONG>::max)();
            assert(source.value->stream->CopyTo(sink.Get(), requested, &read, &written) == S_FALSE && read.QuadPart == 4 && written.QuadPart == 4);
            sink->result = S_OK; sink->limit = (std::numeric_limits<ULONG>::max)(); offset.QuadPart = 0;
            assert(source.value->stream->Seek(offset, STREAM_SEEK_SET, nullptr) == S_OK);
            requested.QuadPart = index.logicalLength + 1;
            assert(source.value->stream->CopyTo(sink.Get(), requested, &read, &written) == S_FALSE && read.QuadPart == index.logicalLength && written.QuadPart == read.QuadPart && sink->largest == blockBytes);
        }
        {
            const auto com = CoInitializeEx(nullptr, COINIT_MULTITHREADED); assert(SUCCEEDED(com));
            assert(MFStartup(MF_VERSION, MFSTARTUP_LITE) == S_OK);
            {
                Microsoft::WRL::ComPtr<IMFByteStream> native;
                assert(MFCreateMFByteStreamOnStream(stream.Get(), &native) == S_OK);
                DWORD capabilities = 0; QWORD length = 0;
                assert(native->GetCapabilities(&capabilities) == S_OK && (capabilities & MFBYTESTREAM_IS_READABLE) && (capabilities & MFBYTESTREAM_IS_SEEKABLE) && !(capabilities & MFBYTESTREAM_IS_WRITABLE));
                assert(native->GetLength(&length) == S_OK && length == index.logicalLength);
                assert(native->SetCurrentPosition(2ULL * blockBytes) == S_OK);
                assert(native->Read(bytes.data(), 4, &got) == S_OK && got == 4 && bytes[0] == 1 && bytes[3] == 4);
            } // Byte stream releases its actual COM ownership before MF shutdown.
            assert(MFShutdown() == S_OK); CoUninitialize();
        }

        // A new current index cannot change a previously pinned generation.
        {
            auto writer = fixture.open(CustodyFileAccess::writeExisting); assert(writer.ok());
            CustodyBytes changed(blockBytes, 0x77);
            auto cipher = ProtectedCustodyCodec::sealBlock(fixture.context, 0, 2, changed); assert(cipher.ok());
            auto size = (*writer.value)->writeBlock(0, 2, blockBytes, *cipher.value); assert(size.ok());
            index.generation = 2; index.entries[0] = {2, *size.value, 0};
            publish(fixture, **writer.value, 1, index);
        }
        auto current = openProtectedCustodyReader(fixture.root, "package-a", fixture.context, cancelled); assert(current.ok());
        assert(current.value->stream->Read(bytes.data(), 1, &got) == S_OK && bytes[0] == 0x77);
        assert(stream->Seek(offset, STREAM_SEEK_SET, nullptr) == S_OK);
        assert(stream->Read(bytes.data(), 1, &got) == S_OK && bytes[0] == 0x42); // No cross-state cache reuse.
        current.value.reset();

        std::vector<Microsoft::WRL::ComPtr<IStream>> holders(30);
        for (auto& holder : holders) assert(stream->Clone(&holder) == S_OK); // Root + clone + 30 = process32.
        Microsoft::WRL::ComPtr<IStream> refused;
        assert(stream->Clone(&refused) == STG_E_INSUFFICIENTMEMORY && !refused);
        Fixture separate;
        {
            auto files = separate.open(CustodyFileAccess::createNew); assert(files.ok());
            publish(separate, **files.value, 0, CustodyIndex{1, 0, {}});
            publish(separate, **files.value, 1, CustodyIndex{1, 0, {}});
        }
        inject(FileFault::none);
        auto other = openProtectedCustodyReader(separate.root, "", separate.context, cancelled);
        assert(!other.ok() && other.error == CustodyFileError::allocationFailed && reads == 0);
        holders.pop_back();
        other = openProtectedCustodyReader(separate.root, "", separate.context, cancelled); assert(other.ok());
        other.value.reset(); holders.clear();
        stream.Reset(); // Clone retains the actual snapshot/handles, not only a counter.
        assert(clone->Seek(offset, STREAM_SEEK_SET, nullptr) == S_OK);
        assert(clone->Read(bytes.data(), 1, &got) == S_OK && bytes[0] == 0x42);

        // Concurrent Clone admission holds 31 new owners through the barrier,
        // not sequential counter-only calls that immediately release each pin.
        std::atomic<unsigned> attempted{0}, accepted{0}; std::atomic<bool> release{false};
        std::vector<std::thread> threads;
        for (unsigned i = 0; i < 40; ++i) threads.emplace_back([&] {
            Microsoft::WRL::ComPtr<IStream> holder;
            const auto result = clone->Clone(&holder);
            if (result == S_OK) ++accepted;
            else assert(result == STG_E_INSUFFICIENTMEMORY && !holder);
            ++attempted;
            while (!release.load()) std::this_thread::yield();
        });
        while (attempted.load() != 40) std::this_thread::yield();
        assert(accepted.load() == 31); release.store(true);
        for (auto& thread : threads) thread.join();
        cancelled->store(true);
        inject(FileFault::none);
        assert(clone->Read(bytes.data(), 1, &got) == HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED) && got == 0 && reads == 0);
        cancelled->store(false);
        assert(FAILED(clone->Read(bytes.data(), 1, &got)) && got == 0); // Sticky cancellation.
        clone.Reset(); opened.value.reset();

        auto failing = openProtectedCustodyReader(fixture.root, "package-a", fixture.context, cancelled); assert(failing.ok());
        Microsoft::WRL::ComPtr<IStream> failedClone; assert(failing.value->stream->Clone(&failedClone) == S_OK);
        CustodyBytes output(static_cast<std::size_t>(index.logicalLength), 0xaa);
        inject(FileFault::readFailed, 3); // First DATA copied (two native reads), then failed tail DATA.
        assert(FAILED(failing.value->stream->Read(output.data(), static_cast<ULONG>(output.size()), &got)) && got == 0);
        assert(std::all_of(output.begin(), output.begin() + blockBytes, [](auto byte) { return byte == 0; }));
        inject(FileFault::none);
        assert(FAILED(failing.value->stream->Read(bytes.data(), 1, &got)) && got == 0 && reads == 0);
        assert(FAILED(failedClone->Read(bytes.data(), 1, &got)) && got == 0 && reads == 0);
        failedClone.Reset(); failing.value.reset();
        auto exhausted = openProtectedCustodyReader(fixture.root, "package-a", fixture.context, cancelled); assert(exhausted.ok());
        {
            CustodyBytes fill; fill.reserve(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
            inject(FileFault::none);
            assert(exhausted.value->stream->Read(bytes.data(), 1, &got) == E_OUTOFMEMORY && got == 0 && reads == 0);
        }
        assert(exhausted.value->stream->Read(bytes.data(), 1, &got) == E_OUTOFMEMORY && got == 0);
        auto copyExhausted = openProtectedCustodyReader(fixture.root, "package-a", fixture.context, cancelled); assert(copyExhausted.ok());
        {
            CustodyBytes fill; fill.reserve(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
            inject(FileFault::none);
            requested.QuadPart = (std::numeric_limits<std::uint64_t>::max)();
            assert(copyExhausted.value->stream->CopyTo(destination.Get(), requested, &read, &written) == E_OUTOFMEMORY && read.QuadPart == 0 && written.QuadPart == 0 && reads == 0);
        }
        assert(copyExhausted.value->stream->Read(bytes.data(), 1, &got) == E_OUTOFMEMORY && got == 0);
    }
    {
        Fixture prefix(CustodyRole::canonical, L"canonical");
        {
            auto files = prefix.open(CustodyFileAccess::createNew); assert(files.ok());
            publish(prefix, **files.value, 0, snapshotData(prefix, **files.value, 1));
        }
        prefix.write(prefix.object() / L"index.1", CustodyBytes{1, 2, 3});
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        auto result = openProtectedCustodyReader(prefix.root, "package-a", prefix.context, cancelled);
        assert(result.ok() && result.value->state == CustodySnapshotState::trustedPrefix && result.value->recoveryError == CustodyFileError::invalidContent);
        std::array<std::uint8_t, 5> bytes{}; ULONG got = 0;
        assert(result.value->stream->Read(bytes.data(), 5, &got) == S_FALSE && got == 4 && bytes[0] == 1);
        cancelled->store(true); inject(FileFault::none);
        auto stopped = openProtectedCustodyReader(prefix.root, "package-a", prefix.context, cancelled);
        assert(!stopped.ok() && stopped.nativeError == ERROR_OPERATION_ABORTED && reads == 0);
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
    inject(FileFault::none);
}
CustodyIndex snapshotData(Fixture& fixture, ProtectedCustodyFiles& files, std::uint64_t version = 1) {
    const auto cipher = ProtectedCustodyCodec::sealBlock(fixture.context, 0, version, CustodyBytes{1, 2, 3, 4}); assert(cipher.ok());
    const auto written = files.writeBlock(0, version, 4, *cipher.value); assert(written.ok());
    return {version, 4, {{version, *written.value, 0}}};
}
void coldCacheClose() {
    // Must be the FIRST reader/cache scenario in this process. This test never
    // calls Read/Clone or reaches the private cache through a preparation path.
    inject(FileFault::none);
    const auto before = CustodyOwnedMemory::usedBytes();
    std::size_t emptyProxyCharge = 0;
    {
        const auto measured = CustodyOwnedMemory::usedBytes();
        CustodyBytes empty;
        assert(empty.empty());
        emptyProxyCharge = CustodyOwnedMemory::usedBytes() - measured;
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
    std::fprintf(stderr, "cold-cache-close empty_proxy_charge=%zu runtime=%s\n", emptyProxyCharge,
        emptyProxyCharge ? "charged-proxy-regression" : "no-charged-proxy-close-only");
    {
        Fixture fixture;
        {
            auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
            const auto index = snapshotData(fixture, **files.value);
            publish(fixture, **files.value, 0, index);
            publish(fixture, **files.value, 1, index);
        }
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        auto reader = openProtectedCustodyReader(fixture.root, "", fixture.context, cancelled);
        assert(reader.ok() && reader.value->stream && reader.value->state == CustodySnapshotState::verified);
        struct RawPressure {
            CustodyAllocator<std::uint8_t> allocator;
            std::size_t count;
            std::uint8_t* bytes;
            explicit RawPressure(std::size_t size) : count(size), bytes(allocator.allocate(size)) {}
            ~RawPressure() { allocator.deallocate(bytes, count); }
            RawPressure(const RawPressure&) = delete;
            RawPressure& operator=(const RawPressure&) = delete;
        };
        {
            const auto used = CustodyOwnedMemory::usedBytes();
            assert(used < CustodyOwnedMemory::limit);
            // No default vector here: its Debug proxy would consume headroom
            // before reservation. This synthetic raw allocation is never read.
            RawPressure pressure(CustodyOwnedMemory::limit - used);
            assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
            const auto calls = writerIoCounts();
            reader.value->stream.Reset(); // Old Debug: first cache init throws inside noexcept destruction.
            assert(!reader.value->stream);
            reader.value.reset();
            assert(writerIoCounts() == calls); // Closing never creates/reopens content.
            std::fputs("cold-cache-close stream_closed_under_pressure\n", stderr);
        }
    }
    // Fixed factory initializes the process-lifetime empty cache before state
    // creation. Its one proxy remains; snapshot/files/reader/pressure must not.
    assert(CustodyOwnedMemory::usedBytes() == before + emptyProxyCharge);
    std::fprintf(stderr, "cold-cache-close cleanup_owned=%zu expected=%zu relevance=%s\n",
        CustodyOwnedMemory::usedBytes(), before + emptyProxyCharge,
        emptyProxyCharge ? "charged-proxy-path" : "SKIP-no-proxy-allocation-fault");
}
void writerOpenBudget() {
    const auto before = CustodyOwnedMemory::usedBytes();
    std::size_t proxy = 0;
    { CustodyIndex empty; proxy = CustodyOwnedMemory::usedBytes() - before; }
    assert(CustodyOwnedMemory::usedBytes() == before);
    if (!proxy) {
        std::fputs("writer-open-budget SKIP-no-proxy-allocation-fault\n", stderr);
        return;
    }
    {
        Fixture fixture(CustodyRole::media, L"media");
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        CustodyBytes pressure;
        pressure.reserve(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
        inject(FileFault::none);
        const auto calls = writerIoCounts();
        const auto opened = ProtectedCustodyWriter::open(fixture.root, "package-a", fixture.context, 0, cancelled);
        assert(!opened.ok() && opened.error == CustodyFileError::allocationFailed);
        assert(writerIoCounts() == calls && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}
void metadataMoveBudget() {
    const auto before = CustodyOwnedMemory::usedBytes();
    std::size_t proxy = 0;
    {
        CustodyIndex empty;
        proxy = CustodyOwnedMemory::usedBytes() - before;
    }
    if (!proxy) {
        std::fputs("metadata-move-budget SKIP-no-proxy-allocation-fault\n", stderr);
        return;
    }
    {
        Fixture fixture;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        const CustodyBytes value{7};
        CustodyBytes pressure;
        pressure.reserve(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes() - proxy);
        inject(FileFault::none);
        const auto calls = writerIoCounts();
        // The candidate proxy fits exactly; reserving its first entry must fail
        // normally before native open, without retaining object admission.
        auto denied = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, value, cancelled);
        assert(denied.state == CustodyCommitState::notCommitted && denied.error == CustodyFileError::allocationFailed);
        assert(!denied.lease && !denied.snapshot && writerIoCounts() == calls);
        assert(CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit - proxy);
        std::array<std::optional<CustodyPin>, 32> pins;
        for (auto& pin : pins) { pin.emplace(); assert(*pin); }
        CustodyPin overflow; assert(!overflow);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
    {
        Fixture fixture;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        auto result = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, CustodyBytes{7}, cancelled);
        assert(result.state == CustodyCommitState::committed && result.lease && result.snapshot);
        {
            CustodyBytes pressure;
            pressure.reserve(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
            const auto calls = writerIoCounts();
            bool refused = false;
            try { CustodyMetadataCommit moved(std::move(result)); }
            catch (const std::bad_alloc&) { refused = true; }
            assert(refused && result.lease && result.snapshot && result.snapshot->index.entries.size() == 1);
            std::optional<CustodyMetadataCommit> target;
            refused = false;
            try { target.emplace(std::move(result)); }
            catch (const std::bad_alloc&) { refused = true; }
            assert(refused && !target && result.lease && result.snapshot);
            assert(result.state == CustodyCommitState::committed && result.snapshot->index.generation == 1);
            assert(writerIoCounts() == calls && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
            std::array<std::optional<CustodyPin>, 31> pins;
            for (auto& pin : pins) { pin.emplace(); assert(*pin); }
            CustodyPin overflow; assert(!overflow); // Failed moves retained result's actual admission.
            const auto write = CreateFileW((fixture.object() / L"id.bin").c_str(), GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
            assert(write == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
        }
        CustodyMetadataCommit moved(std::move(result));
        assert(moved.lease && moved.snapshot && !result.lease);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
    {
        Fixture fixture;
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        CustodyBytes pressure;
        unsigned published = 0;
        afterRename = [&] {
            if (++published == 2) pressure.reserve(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
        };
        auto failed = commitProtectedCustodyMetadata(fixture.root, "", fixture.context, 0, CustodyBytes{8}, cancelled);
        afterRename = {}; inject(FileFault::none);
        assert(published == 2 && failed.state == CustodyCommitState::ambiguous);
        assert(failed.error == CustodyFileError::allocationFailed && failed.lease && !failed.snapshot);
        assert(!fixture.open(CustodyFileAccess::writeExisting).ok()); // Return still holds the real lease.
        std::array<std::optional<CustodyPin>, 31> pins;
        for (auto& pin : pins) { pin.emplace(); assert(*pin); }
        CustodyPin overflow; assert(!overflow);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}
void junction(const std::filesystem::path&, const std::filesystem::path&, SECURITY_ATTRIBUTES&);
void linkedMigrationPairs() {
    const auto before = CustodyOwnedMemory::usedBytes();
    {
        inject(FileFault::none);
        Fixture f(CustodyRole::bootstrap, L"bootstrap");
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        auto queue = f.context; queue.role = CustodyRole::queue;
        queue.objectId = CustodyId{}; queue.objectId[0] = 31;
        // Reserve the independent fixed queue identity, without a ledger.
        assert(ProtectedCustodyFiles::open(f.root, "", queue, CustodyFileAccess::createNew).ok());
        auto own = f.context; own.role = CustodyRole::migrationIntent;
        own.objectId = CustodyId{}; own.objectId[0] = 41;
        CustodyMigrationValue intent; intent.context = own; intent.generation = 1;
        intent.transactionId[0] = 42; intent.anchor.length = 3; intent.anchor.sha256.fill(7);
        intent.sourceCount = 1; intent.sources[0].length = 3;
        intent.sources[0].sha256 = intent.anchor.sha256;
        intent.sources[0].destinationObjectId = queue.objectId;
        const auto intentBytes = writeCustodyMigration(intent, own, 1, intent.transactionId,
            CustodyMigrationSubject::queue, "");
        assert(intentBytes.ok());
        assert(commitProtectedCustodyMetadata(f.root, "", own, 0, *intentBytes.value, cancelled).state == CustodyCommitState::committed);
        CustodyBootstrapValue bootstrap; bootstrap.context = f.context; bootstrap.generation = 1;
        bootstrap.queueObjectId = queue.objectId; bootstrap.mode = CustodyBootstrapMode::migrating;
        bootstrap.transactionId = intent.transactionId; bootstrap.subject = CustodyMigrationSubject::queue;
        const auto bootstrapBytes = writeCustodyBootstrap(bootstrap, f.context, 1, queue.objectId);
        assert(bootstrapBytes.ok());
        assert(commitProtectedCustodyMetadata(f.root, "", f.context, 0, *bootstrapBytes.value, cancelled).state == CustodyCommitState::committed);
        assert(!std::filesystem::exists(f.root/L".custody-v1"/L"queue"/L"index.0"));
        assert(!std::filesystem::exists(f.root/L".custody-v1"/L"queue"/L"index.1"));
        inject(FileFault::none);
        const auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled);
        assert(parent.ok() && parent.value && *parent.value);
        const auto result = ProtectedCustodyMigrationPair::read(*parent.value, cancelled);
        // Phase 1 runtime RED: the declared Windows unsupported stub must refuse here.
        assert(result.ok() && result.value && *result.value);
        assert(result.value->get()->current().generation == 1);
        assert(result.value->get()->slots()[0].transactionId == intent.transactionId);
        assert(result.value->get()->slots()[1].transactionId == intent.transactionId);
        assert(!writes && !flushes && !renames && !searches && !diskChecks);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
    using Pair = ProtectedCustodyMigrationPair;
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    CustodyId queueId{}; queueId[0] = 31;
    const auto name = [](CustodyMigrationSubject subject) -> std::string_view {
        return subject == CustodyMigrationSubject::queue ? "" : "package-a";
    };
    const auto location = [](const Fixture& f, CustodyMigrationSubject subject) {
        return (subject == CustodyMigrationSubject::queue ? f.root : f.root/L"package-a")/L".custody-v1"/L"migration-intent";
    };
    const auto makeBirth = [&](Fixture& f, unsigned schema, CustodyMigrationSubject subject) {
        CustodyMigrationValue v; v.schema = schema; v.context = f.context;
        v.context.role = CustodyRole::migrationIntent; v.context.objectId = CustodyId{}; v.context.objectId[0] = 41;
        v.generation = 1; v.transactionId[0] = 42; v.subject = subject;
        v.anchor.length = 3; v.anchor.sha256.fill(7); v.sourceCount = 1;
        v.sources[0].length = 3; v.sources[0].sha256 = v.anchor.sha256; v.sources[0].destinationObjectId = queueId;
        if (subject == CustodyMigrationSubject::package) {
            assert(CreateDirectoryW((f.root/L"package-a").c_str(), &f.security));
            v.directory.emplace(); const std::string directory = "package-a";
            std::copy(directory.begin(), directory.end(), v.directory->begin());
            v.anchor.objectId = queueId; v.anchor.generation = 2;
            v.sources[0].kind = CustodyMigrationSourceKind::manifest; v.sources[0].destinationObjectId[0] = 8;
            v.sourceCount = 2; v.sources[1] = v.sources[0]; v.sources[1].kind = CustodyMigrationSourceKind::media;
            v.sources[1].length = 5; v.sources[1].sha256.fill(9); v.sources[1].destinationObjectId[0] = 10;
            if (schema == 2) { v.sources[1].destinationPacked = true;
                v.sources[1].destinationContainerId = CustodyId{}; v.sources[1].destinationContainerId->at(0) = 19; }
        }
        return v;
    };
    const auto encode = [&](const CustodyMigrationValue& v) {
        auto bytes = writeCustodyMigration(v, v.context, v.generation, v.transactionId, v.subject, name(v.subject));
        assert(bytes.ok()); return std::move(*bytes.value);
    };
    const auto sealBirth = [&](const CustodyMigrationValue& v, std::uint64_t version = 17) {
        auto bytes = encode(v); auto cipher = ProtectedCustodyCodec::sealBlock(v.context, 0, version, bytes);
        assert(cipher.ok()); return std::move(*cipher.value);
    };
    const auto barrier = [](const CustodyMigrationValue& birth, const CustodyBytes& cipher) {
        const auto hash = custody_detail::digest(cipher.data(), cipher.size()); assert(hash);
        return CustodyMigrationBarrier{birth.context.objectId, 1, 17, cipher.size(), *hash};
    };
    const auto authorization = [&] {
        CustodyCleanupAuthorization a; a.kind = CustodyCleanupKind::deletePurge;
        const std::string operation = "cleanup-274", actor = "user-a", workspace = "workspace-a";
        std::copy(operation.begin(), operation.end(), a.operationId.begin());
        std::copy(actor.begin(), actor.end(), a.actorUserId.begin());
        std::copy(workspace.begin(), workspace.end(), a.workspaceId.begin());
        a.queueObjectId = queueId; a.queueGeneration = 4; return a;
    };
    const auto copied = [](CustodyMigrationValue v, std::uint64_t generation, CustodyMigrationStage stage) {
        v.generation = generation; v.stage = stage;
        for (std::size_t i = 0; i < v.sourceCount; ++i) {
            auto& s = v.sources[i]; s.destinationGeneration = 5; s.destinationLength = s.length; s.destinationSha256 = s.sha256;
            if (s.destinationPacked) {
                s.destinationCommittedExtent = ProtectedPackedCustodyFormat::appendOffset + 128;
                s.destinationRootRef = ProtectedPackedCustodyFormat::encodeReference(
                    {PackedRecordKind::nodeL2, 128, ProtectedPackedCustodyFormat::appendOffset, 5, 0, {}});
                assert(s.destinationRootRef);
            }
        }
        return v;
    };
    const auto bootstrapValue = [&](const Fixture& f, const CustodyMigrationValue& intent, std::uint64_t generation) {
        CustodyBootstrapValue v; v.context = f.context; v.generation = generation; v.queueObjectId = queueId;
        v.mode = CustodyBootstrapMode::migrating; v.transactionId = intent.transactionId;
        v.subject = intent.subject; v.directory = intent.directory; return v;
    };
    const auto commitBootstrap = [&](Fixture& f, const CustodyBootstrapValue& v) {
        auto bytes = writeCustodyBootstrap(v, f.context, v.generation, queueId); assert(bytes.ok());
        assert(commitProtectedCustodyMetadata(f.root, "", f.context, v.generation - 1, *bytes.value, cancelled).state == CustodyCommitState::committed);
    };
    const auto reserve = [&](Fixture& f) {
        auto queue = f.context; queue.role = CustodyRole::queue; queue.objectId = queueId;
        assert(ProtectedCustodyFiles::open(f.root, "", queue, CustodyFileAccess::createNew).ok());
    };
    const auto replaceField = [](CustodyBytes& bytes, std::string_view field, std::string_view replacement) {
        std::string json(bytes.begin(), bytes.end()); const auto key = "\"" + std::string(field) + "\":";
        const auto found = json.find(key); assert(found != std::string::npos); const auto first = found + key.size();
        const auto end = json[first] == '"' ? json.find('"', first + 1) + 1 : json.find_first_of(",}", first);
        assert(end != std::string::npos && end > first); json.replace(first, end - first, replacement);
        bytes.assign(json.begin(), json.end());
    };
    const auto install = [&](Fixture& f, const CustodyMigrationValue& birth, const CustodyBytes& birthCipher,
        const std::array<CustodyMigrationValue, 2>& values, int malformedSlot = -1, unsigned fault = 0) {
        auto files = ProtectedCustodyFiles::open(f.root, name(birth.subject), birth.context, CustodyFileAccess::createNew); assert(files.ok());
        const auto directory = location(f, birth.subject); f.write(directory/L"block.0.17", birthCipher);
        for (unsigned slot = 0; slot < 2; ++slot) {
            auto bytes = encode(values[slot]);
            if (slot == 1 && values[slot].generation != 1 && birth.subject == CustodyMigrationSubject::package) {
                // WIRE order, not just typed array order: the production writer sorts by kind.
                std::string json(bytes.begin(), bytes.end()); const auto first = json.find("\"sources\":[") + 11;
                const auto middle = json.find("},{", first), end = json.find("],\"barrier\":", first);
                assert(middle != std::string::npos && end != std::string::npos);
                const auto a = json.substr(first, middle + 1 - first), b = json.substr(middle + 2, end - middle - 2);
                json.replace(first, end - first, b + "," + a); bytes.assign(json.begin(), json.end());
            }
            if (static_cast<int>(slot) == malformedSlot) {
                if (fault == 0) bytes[0] = '[';
                if (fault == 1) replaceField(bytes, "generation", "9");
                if (fault == 2) replaceField(bytes, "object_id", "\"00000000000000000000000000000000\"");
                if (fault == 3) replaceField(bytes, "transaction_id", "\"00000000000000000000000000000000\"");
                if (fault == 4) replaceField(bytes, "subject", birth.subject == CustodyMigrationSubject::queue ? "\"package\"" : "\"queue\"");
                if (fault == 5) replaceField(bytes, "directory_id", "\"other-package\"");
                if (fault == 6) replaceField(bytes, "store_id", "\"00000000000000000000000000000000\"");
                if (fault == 7) replaceField(bytes, "destination_generation", "null");
                if (fault == 8) replaceField(bytes, "destination_sha256", "null");
            }
            const auto version = values[slot].generation == 1 ? std::uint64_t{17} : 31 + std::uint64_t{slot};
            std::uint32_t envelopeBytes = static_cast<std::uint32_t>(birthCipher.size());
            if (version != 17) {
                auto cipher = ProtectedCustodyCodec::sealBlock(birth.context, 0, version, bytes); assert(cipher.ok());
                const auto saved = (*files.value)->writeBlock(0, version, static_cast<std::uint32_t>(bytes.size()), *cipher.value);
                assert(saved.ok()); envelopeBytes = *saved.value;
            } else {
                auto plain = ProtectedCustodyCodec::openMigrationBirthBlock(birth.context, 17, birthCipher);
                assert(plain.ok() && *plain.value == bytes);
            }
            auto index = ProtectedCustodyCodec::sealIndex(birth.context, slot,
                CustodyIndex{values[slot].generation, bytes.size(), {{version, envelopeBytes, 0}}}); assert(index.ok());
            assert((*files.value)->publishIndex(slot, *index.value).state == CustodyPublishState::published);
        }
    };
    const auto prepare = [&](Fixture& f, const CustodyMigrationValue& birth, const CustodyBytes& cipher,
        const std::array<CustodyMigrationValue, 2>& slots) {
        reserve(f); install(f, birth, cipher, slots); commitBootstrap(f, bootstrapValue(f, birth, 1));
    };
    const auto link = [&](const Fixture& f) {
        auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        return Pair::read(std::move(*parent.value), cancelled);
    };
    const auto noEffects = [] { assert(!writes && !flushes && !renames && !searches && !diskChecks && !creates); };
    const auto identities = [&](const Fixture& f, CustodyMigrationSubject subject) {
        return std::array<std::filesystem::path, 4>{f.root/L".custody-v1"/L"store.id", f.object()/L"id.bin",
            f.root/L".custody-v1"/L"queue"/L"id.bin", location(f, subject)/L"id.bin"};
    };
    const auto locks = [](const auto& paths, bool held) {
        for (const auto& path : paths) {
            const auto file = CreateFileW(path.c_str(), GENERIC_WRITE,
                FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
            if (held) { assert(file == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
                assert(!DeleteFileW(path.c_str()) && GetLastError() == ERROR_SHARING_VIOLATION); }
            else { assert(file != INVALID_HANDLE_VALUE); CloseHandle(file); }
        }
    };
    const auto check = [&](Fixture& f, const CustodyMigrationValue& birth, CustodyFileError error) {
        const auto owned = CustodyOwnedMemory::usedBytes(); const auto artifacts = writerArtifacts(f); inject(FileFault::none);
        { const auto result = link(f);
            if (error == CustodyFileError::none) assert(result.ok() && result.value && *result.value);
            else assert(!result.ok() && !result.value && result.error == error);
            noEffects(); assert(writerArtifacts(f) == artifacts); }
        assert(CustodyOwnedMemory::usedBytes() == owned); locks(identities(f, birth.subject), false);
    };
    // Gate transition table is deliberately NOT startup/queue admission.
    for (unsigned variant = 0; variant < 6; ++variant) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); auto birth = makeBirth(f, 1, CustodyMigrationSubject::queue);
        const auto cipher = sealBirth(birth); reserve(f); install(f, birth, cipher, {birth, birth});
        auto first = bootstrapValue(f, birth, 1), last = bootstrapValue(f, birth, 2);
        if (variant == 0) { first.mode = CustodyBootstrapMode::protectedStore;
            first.transactionId.reset(); first.subject.reset(); first.directory.reset(); }
        if (variant == 1) { last.mode = CustodyBootstrapMode::protectedStore;
            last.transactionId.reset(); last.subject.reset(); last.directory.reset(); }
        if (variant == 2) last.transactionId->at(0) ^= 1;
        if (variant >= 3) { last.subject = CustodyMigrationSubject::package;
            last.directory.emplace(); const std::string directory = variant == 3 ? "package-a" : "other-package";
            std::copy(directory.begin(), directory.end(), last.directory->begin()); }
        if (variant == 4) { first.subject = CustodyMigrationSubject::package; first.directory.emplace();
            const std::string directory = "package-a"; std::copy(directory.begin(), directory.end(), first.directory->begin()); }
        if (variant == 5) { last.subject = first.subject; last.directory.reset(); } // Matching migrating peers.
        commitBootstrap(f, first); commitBootstrap(f, last);
        check(f, birth, variant == 0 || variant == 5 ? CustodyFileError::none :
            variant == 1 ? CustodyFileError::invalidInput : CustodyFileError::conflict);
    }
    for (unsigned schema : {1U, 2U}) for (const auto subject : {CustodyMigrationSubject::queue, CustodyMigrationSubject::package}) {
        for (unsigned step = 1; step <= 6; ++step) {
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, schema, subject);
            const auto cipher = sealBirth(birth); const auto ref = barrier(birth, cipher);
            const auto state = [&](unsigned generation) {
                auto v = birth; v.generation = generation;
                if (generation >= 2) v.barrier = ref;
                if (generation >= 3) v = copied(v, generation, static_cast<CustodyMigrationStage>(generation - 2));
                if (generation >= 5) v.authorization = authorization();
                return v;
            };
            std::array<CustodyMigrationValue, 2> slots{birth, birth};
            if (step > 1) { slots[(step - 2) % 2] = state(step - 1); slots[(step - 1) % 2] = state(step); }
            prepare(f, birth, cipher, slots);
            const auto owned = CustodyOwnedMemory::usedBytes(); const auto paths = identities(f, subject); inject(FileFault::none);
            {
                auto callerCancel = std::make_shared<std::atomic<bool>>(false);
                auto parent = ProtectedCustodyBootstrapPair::read(f.root, callerCancel); assert(parent.ok());
                auto result = Pair::read(*parent.value, callerCancel); assert(result.ok());
                const auto& pair = **result.value;
                assert(pair.current().generation == step && pair.current().schema == schema);
                assert(pair.selectedSlot() == (step == 1 ? 0U : (step - 1) % 2));
                for (unsigned slot = 0; slot < 2; ++slot) {
                    assert(pair.slots()[slot].generation == slots[slot].generation && pair.indices().indices[slot].generation == slots[slot].generation);
                    assert(pair.slots()[slot].context.objectId == birth.context.objectId && pair.slots()[slot].context.objectId != queueId);
                    if (subject == CustodyMigrationSubject::queue) assert(pair.slots()[slot].sources[0].destinationObjectId == queueId);
                    else assert(pair.slots()[slot].anchor.objectId == queueId);
                }
                auto retained = *result.value, last = retained; result.value.reset(); parent.value.reset(); callerCancel.reset(); retained.reset();
                locks(paths, true); noEffects();
                { std::array<CustodyNativeJob, 4> jobs; for (const auto& job : jobs) assert(job); }
                { std::array<CustodyPin, 30> pins; for (const auto& pin : pins) assert(pin); CustodyPin overflow; assert(!overflow); }
                assert(last->current().generation == step); last.reset();
            }
            assert(CustodyOwnedMemory::usedBytes() == owned); locks(paths, false);
            // No queue snapshot was required or synthesized, including package linkage.
            assert(!std::filesystem::exists(f.root/L".custody-v1"/L"queue"/L"index.0"));
            assert(!std::filesystem::exists(f.root/L".custody-v1"/L"queue"/L"index.1"));
        }
        // Each decoded slot must bind the physical fixed queue, not intent ID or plausible JSON ID.
        for (unsigned changed = 0; changed < 3; ++changed) {
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, schema, subject);
            const auto cipher = sealBirth(birth); auto first = birth, last = birth; first.generation = 3; last.generation = 4;
            const auto change = [&](CustodyMigrationValue& v) {
                if (subject == CustodyMigrationSubject::queue) v.sources[0].destinationObjectId = v.context.objectId;
                else v.anchor.objectId = v.context.objectId;
            };
            if (changed != 1) change(first); if (changed != 0) change(last);
            prepare(f, birth, cipher, {first, last}); check(f, birth, CustodyFileError::invalidContent);
        }
        {
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, schema, subject);
            const auto cipher = sealBirth(birth); prepare(f, birth, cipher, {birth, birth});
            const auto queueDirectory = f.root/L".custody-v1"/L"queue";
            f.write(queueDirectory/L"index.0", CustodyBytes(32, 0)); f.write(queueDirectory/L"index.1", CustodyBytes(17, 0xff));
            const std::wstring prefix = L"\\\\?\\" + queueDirectory.wstring() + L"\\index.";
            unsigned queueReads = 0;
            afterRead = [&] { wchar_t path[1024]{}; const auto count = GetFinalPathNameByHandleW(afterReadFile, path, 1024, FILE_NAME_NORMALIZED);
                assert(count && count < 1024); if (std::wstring_view(path, count).find(prefix) == 0) ++queueReads; };
            check(f, birth, CustodyFileError::none); afterRead = {}; assert(!queueReads);
            assert(std::filesystem::file_size(queueDirectory/L"index.0") == 32 && std::filesystem::file_size(queueDirectory/L"index.1") == 17);
        }
        for (unsigned variant = 0; variant < 3; ++variant) {
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, schema, subject);
            const auto cipher = sealBirth(birth); auto first = birth; first.generation = 3; auto last = first; last.generation = 8;
            if (variant == 0) { first = copied(first, 3, CustodyMigrationStage::copiedVerified);
                last = copied(last, 8, CustodyMigrationStage::copiedVerified); }
            if (variant == 1) { last = copied(last, 8, CustodyMigrationStage::complete);
                last.barrier = barrier(birth, cipher); last.authorization = authorization(); }
            if (variant == 2) { first.barrier = last.barrier = barrier(birth, cipher);
                first.authorization = last.authorization = authorization(); }
            prepare(f, birth, cipher, {first, last}); check(f, birth, CustodyFileError::none);
        }
        // Isolate immutable correspondence from fixed-queue binding and Birth: valid prepared peers, no barrier.
        for (unsigned fault = 0; fault < 10; ++fault) {
            if (subject == CustodyMigrationSubject::queue && (fault == 4 || fault >= 6)) continue;
            if ((fault == 7 || fault == 8) && schema != 2) continue;
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, schema, subject);
            const auto cipher = sealBirth(birth); auto first = birth; first.generation = 3; auto last = first; last.generation = 4;
            auto& source = last.sources[subject == CustodyMigrationSubject::queue ? 0 : 1];
            if (fault == 0) { last.schema = schema == 1 ? 2 : 1;
                for (auto& s : last.sources) { s.destinationPacked = false; s.destinationContainerId.reset(); } }
            if (fault == 1) { ++last.anchor.length; if (subject == CustodyMigrationSubject::queue) ++source.length; }
            if (fault == 2) { last.anchor.sha256[0] ^= 1; if (subject == CustodyMigrationSubject::queue) source.sha256 = last.anchor.sha256; }
            if (fault == 3) { if (!last.anchor.objectId) last.anchor.objectId = queueId; last.anchor.generation = 9; }
            if (fault == 4) source.destinationObjectId[0] ^= 1;
            if (fault == 5) { ++source.length; if (subject == CustodyMigrationSubject::queue) last.anchor.length = source.length; }
            if (fault == 6) source.kind = CustodyMigrationSourceKind::canonical;
            if (fault == 7) { source.destinationPacked = false; source.destinationContainerId.reset(); }
            if (fault == 8) source.destinationContainerId->at(0) ^= 1;
            if (fault == 9) { last.sources[2] = last.sources[0]; last.sources[2].kind = CustodyMigrationSourceKind::recovery; last.sourceCount = 3; }
            prepare(f, birth, cipher, {first, last}); check(f, birth, CustodyFileError::conflict);
        }
        for (unsigned fault = 0; fault < 13; ++fault) {
            if ((fault == 9 || fault == 10) && (schema != 2 || subject != CustodyMigrationSubject::package)) continue;
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, schema, subject);
            const auto cipher = sealBirth(birth); auto first = copied(birth, 3, CustodyMigrationStage::copiedVerified);
            auto last = copied(birth, 4, CustodyMigrationStage::copiedVerified);
            first.barrier = last.barrier = barrier(birth, cipher); first.authorization = last.authorization = authorization();
            if (fault == 0) { last = birth; last.generation = 4; last.barrier = first.barrier; last.authorization = first.authorization; }
            if (fault == 1) last.barrier.reset();
            if (fault == 2) last.authorization.reset();
            if (fault == 3) { last.authorization->kind = CustodyCleanupKind::ownerConfirmation;
                last.authorization->operationId.fill(0); const std::string txn = "2a000000000000000000000000000000";
                std::copy(txn.begin(), txn.end(), last.authorization->operationId.begin()); }
            if (fault == 4) last.authorization->operationId[0] = 'x';
            if (fault == 5) last.authorization->actorUserId[0] = 'x';
            if (fault == 6) last.authorization->workspaceId[0] = 'x';
            if (fault == 7) last.authorization->queueObjectId[0] ^= 1;
            if (fault == 8) ++last.authorization->queueGeneration;
            if (fault == 9) { last.sources[1].destinationCommittedExtent = *last.sources[1].destinationCommittedExtent + 128; }
            if (fault == 10) { last.sources[1].destinationRootRef = ProtectedPackedCustodyFormat::encodeReference(
                {PackedRecordKind::nodeL2, 128, ProtectedPackedCustodyFormat::appendOffset, 4, 0, {}});
                assert(last.sources[1].destinationRootRef); }
            if (fault == 11) ++*last.sources[0].destinationGeneration;
            if (fault == 12) ++*last.sources[subject == CustodyMigrationSubject::queue ? 0 : 1].destinationGeneration;
            prepare(f, birth, cipher, {first, last}); check(f, birth, CustodyFileError::conflict);
        }
        {
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, schema, subject);
            const auto cipher = sealBirth(birth), other = sealBirth(birth, 18);
            auto first = birth; first.generation = 3; first.barrier = barrier(birth, cipher);
            auto last = birth; last.generation = 4; last.barrier = barrier(birth, other); last.barrier->blockVersion = 18;
            prepare(f, birth, cipher, {first, last}); f.write(location(f, subject)/L"block.0.18", other);
            assert(readCustodyMigrationBirth(cipher, birth.context, first, birth.transactionId, subject, name(subject)).ok());
            assert(readCustodyMigrationBirth(other, birth.context, last, birth.transactionId, subject, name(subject)).ok());
            check(f, birth, CustodyFileError::conflict); // Both direct envelopes valid; sticky barrier changed.
        }
        for (unsigned slot = 0; slot < 2; ++slot) for (unsigned fault = 0; fault < 9; ++fault) {
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, schema, subject);
            const auto cipher = sealBirth(birth); auto first = copied(birth, 3, CustodyMigrationStage::copiedVerified);
            auto last = copied(birth, 4, CustodyMigrationStage::copiedVerified); first.barrier = last.barrier = barrier(birth, cipher);
            reserve(f); install(f, birth, cipher, {first, last}, static_cast<int>(slot), fault);
            commitBootstrap(f, bootstrapValue(f, birth, 1)); check(f, birth, CustodyFileError::invalidContent);
        }
        for (unsigned fault = 0; fault < 8; ++fault) {
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, schema, subject);
            const auto cipher = sealBirth(birth); auto first = copied(birth, 3, CustodyMigrationStage::copiedVerified);
            auto last = copied(birth, 4, CustodyMigrationStage::copiedVerified); first.barrier = last.barrier = barrier(birth, cipher);
            prepare(f, birth, cipher, {first, last}); const auto directory = location(f, subject);
            const auto path = directory/(fault < 4 ? (fault % 2 ? L"index.1" : L"index.0") :
                (fault % 2 ? L"block.0.32" : L"block.0.31"));
            assert(DeleteFileW(path.c_str())); if (fault == 2 || fault == 3 || fault == 6 || fault == 7) f.write(path, CustodyBytes(32, 0));
            const auto owned = CustodyOwnedMemory::usedBytes(); inject(FileFault::none);
            { const auto result = link(f); assert(!result.ok() && !result.value); noEffects(); }
            assert(CustodyOwnedMemory::usedBytes() == owned); locks(identities(f, subject), false);
        }
        // Direct historical checks are required independently for BOTH slots, including the unselected lower peer.
        for (unsigned slot = 0; slot < 2; ++slot) for (unsigned fault = 0; fault < 8; ++fault) {
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, schema, subject);
            auto changed = birth; if (fault == 4) { ++changed.anchor.length;
                if (subject == CustodyMigrationSubject::queue) ++changed.sources[0].length; }
            if (fault == 5) changed.context.objectId[0] ^= 1;
            auto cipher = sealBirth(changed, fault == 7 ? 18 : 17);
            if (fault == 3) cipher.back() ^= 1;
            auto first = copied(birth, 3, CustodyMigrationStage::copiedVerified);
            auto last = copied(birth, 4, CustodyMigrationStage::copiedVerified);
            auto ref = barrier(birth, cipher);
            if (fault == 0) ref.blockVersion = 99;
            if (fault == 1) --ref.envelopeBytes;
            if (fault == 2) ref.sha256[0] ^= 1;
            (slot ? last : first).barrier = ref;
            prepare(f, birth, cipher, {first, last});
            if (fault == 6) { assert(DeleteFileW((location(f, subject)/L"block.0.17").c_str()));
                f.write((subject == CustodyMigrationSubject::queue ? f.root : f.root/L"package-a")/
                    (subject == CustodyMigrationSubject::queue ? L"desktop-upload-queue.v2.quarantine" : L"manifest.json"), cipher); }
            CustodyFileError error = CustodyFileError::invalidContent; std::uint32_t native = 0;
            if (fault == 0 || fault == 6) { error = CustodyFileError::ioFailed; native = ERROR_FILE_NOT_FOUND; }
            if (fault == 3 || fault == 5 || fault == 7) {
                const auto decoded = ProtectedCustodyCodec::openMigrationBirthBlock(birth.context, 17, cipher); assert(!decoded.ok());
                error = codecFileError(decoded.error); native = decoded.nativeError;
            }
            const auto owned = CustodyOwnedMemory::usedBytes(); inject(FileFault::none);
            { const auto result = link(f); assert(!result.ok() && !result.value && result.error == error && result.nativeError == native); noEffects(); }
            assert(CustodyOwnedMemory::usedBytes() == owned); locks(identities(f, subject), false);
        }
        // Count the real linked factory AFTER genuine bootstrap discovery; no caller-root reopening is involved.
        {
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, schema, subject);
            const auto cipher = sealBirth(birth); auto first = copied(birth, 3, CustodyMigrationStage::copiedVerified);
            auto last = copied(birth, 4, CustodyMigrationStage::switched); first.barrier = last.barrier = barrier(birth, cipher);
            prepare(f, birth, cipher, {first, last});
            const auto paths = identities(f, subject); const auto directory = location(f, subject);
            const std::wstring index0 = L"\\\\?\\" + (directory/L"index.0").wstring(), index1 = L"\\\\?\\" + (directory/L"index.1").wstring();
            const std::wstring historical = L"\\\\?\\" + (directory/L"block.0.17").wstring();
            const auto owned = CustodyOwnedMemory::usedBytes(); const auto artifacts = writerArtifacts(f);
            unsigned indexReads = 0, birthReads = 0; std::array<unsigned, 2> directOrdinals{};
            std::size_t beforeIndex = 0;
            const auto released = [&] {
                assert(CustodyOwnedMemory::usedBytes() == owned); noEffects(); locks(paths, false);
                assert(writerArtifacts(f) == artifacts);
                std::array<CustodyNativeJob, 4> jobs; for (const auto& job : jobs) assert(job);
                std::array<CustodyPin, 32> pins; for (const auto& pin : pins) assert(pin);
            };
            const auto observe = [&] {
                wchar_t text[1024]{}; const auto count = GetFinalPathNameByHandleW(afterReadFile, text, 1024, FILE_NAME_NORMALIZED);
                assert(count && count < 1024);
                const bool index = CompareStringOrdinal(text, static_cast<int>(count), index0.c_str(), -1, TRUE) == CSTR_EQUAL ||
                    CompareStringOrdinal(text, static_cast<int>(count), index1.c_str(), -1, TRUE) == CSTR_EQUAL;
                const bool direct = CompareStringOrdinal(text, static_cast<int>(count), historical.c_str(), -1, TRUE) == CSTR_EQUAL;
                if (!index && !direct) return; // Own native identity reads precede acquisition of the complete own lease.
                locks(paths, true);
                std::array<CustodyNativeJob, 3> jobs; for (const auto& job : jobs) assert(job); CustodyNativeJob overflow; assert(!overflow);
                if (index) { if (!indexReads) beforeIndex = queueAllocation.calls; ++indexReads; }
                if (direct) { assert(birthReads < directOrdinals.size()); directOrdinals[birthReads++] = reads; }
            };
            const auto invoke = [&](std::size_t failAt, std::size_t cancelAt, FileFault fault = FileFault::none, unsigned ordinal = 1) {
                afterRead = {}; inject(FileFault::none);
                auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
                indexReads = birthReads = 0; directOrdinals = {}; beforeIndex = 0;
                afterRead = observe; inject(fault, ordinal);
                queueAllocation = {}; queueAllocation.migrationFactory = true;
                queueAllocation.failAt = failAt; queueAllocation.cancelAt = cancelAt; queueAllocation.cancellation = cancelled.get();
                queueAllocation.active = true;
                auto result = Pair::read(std::move(*parent.value), cancelled);
                queueAllocation.active = false; afterRead = {}; return result;
            };
            { const auto warm = invoke(0, 0); assert(warm.ok()); } released();
            auto counted = invoke(0, 0); assert(counted.ok());
            const auto allocations = queueAllocation.calls; const auto totalReads = reads, totalHashes = hashCreates;
            const auto birthOrdinals = directOrdinals;
            assert(allocations && beforeIndex && indexReads == 2 && birthReads == 2 && birthOrdinals[1] > birthOrdinals[0]);
            counted.value.reset(); released();
            const auto retry = [&] { auto result = invoke(0, 0); assert(result.ok() && queueAllocation.calls == allocations);
                result.value.reset(); released(); };
            for (std::size_t ordinal = 1; ordinal <= allocations; ++ordinal) {
                const auto result = invoke(ordinal, 0);
                assert(queueAllocation.hit && !result.ok() && !result.value && result.error == CustodyFileError::allocationFailed);
                released(); retry();
            }
            // EVERY actual allocation cancellation ordinal, including final object/proxy/controlblock materialization.
            for (std::size_t ordinal = 1; ordinal <= allocations; ++ordinal) {
                const auto result = invoke(0, ordinal);
                assert(queueAllocation.hit && !result.ok() && !result.value && result.error == CustodyFileError::ioFailed && result.nativeError == ERROR_OPERATION_ABORTED);
                cancelled->store(false); released(); retry();
            }
            for (unsigned ordinal = 1; ordinal <= totalReads; ++ordinal) {
                const auto result = invoke(0, 0, FileFault::readFailed, ordinal);
                assert(!result.ok() && !result.value && result.error == CustodyFileError::ioFailed && result.nativeError == ERROR_READ_FAULT);
                released(); retry();
            }
            for (unsigned ordinal = 1; ordinal <= totalReads; ++ordinal) {
                inject(FileFault::none); auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
                inject(FileFault::none); afterRead = [&] { if (reads == ordinal) cancelled->store(true); };
                const auto result = Pair::read(std::move(*parent.value), cancelled); afterRead = {};
                assert(!result.ok() && !result.value && result.error == CustodyFileError::ioFailed && result.nativeError == ERROR_OPERATION_ABORTED);
                cancelled->store(false); released(); retry();
            }
            for (const auto fault : {FileFault::hashCreate, FileFault::allocation}) for (unsigned ordinal = 1; ordinal <= totalHashes; ++ordinal) {
                const auto result = invoke(0, 0, fault, ordinal);
                assert(!result.ok() && !result.value && result.error ==
                    (fault == FileFault::hashCreate ? CustodyFileError::hashFailed : CustodyFileError::allocationFailed));
                assert(result.nativeError == 0); released(); retry();
            }
            queueAllocation = {}; inject(FileFault::none);
            assert(Pair::read({}, cancelled).error == CustodyFileError::invalidInput && !opens);
            auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok()); inject(FileFault::none);
            assert(Pair::read(*parent.value, {}).error == CustodyFileError::invalidInput && !opens);
            cancelled->store(true); const auto pre = Pair::read(std::move(*parent.value), cancelled); cancelled->store(false);
            assert(!pre.ok() && !pre.value && pre.error == CustodyFileError::ioFailed && pre.nativeError == ERROR_OPERATION_ABORTED && !opens);
            released(); retry();
            {
                inject(FileFault::none); auto input = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(input.ok()); inject(FileFault::none);
                std::array<CustodyNativeJob, 4> jobs; for (const auto& job : jobs) assert(job);
                const auto denied = Pair::read(std::move(*input.value), cancelled);
                assert(!denied.ok() && !denied.value && denied.error == CustodyFileError::allocationFailed && denied.nativeError == ERROR_NOT_ENOUGH_QUOTA && !opens);
                assert(CustodyOwnedMemory::usedBytes() == owned); locks(paths, false); noEffects();
            }
            released(); retry();
            {
                inject(FileFault::none); auto input = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(input.ok()); inject(FileFault::none);
                std::array<CustodyPin, 31> pins; for (const auto& pin : pins) assert(pin); CustodyPin overflow; assert(!overflow);
                const auto denied = Pair::read(std::move(*input.value), cancelled);
                assert(!denied.ok() && !denied.value && denied.error == CustodyFileError::allocationFailed && denied.nativeError == ERROR_NOT_ENOUGH_QUOTA && !opens);
                assert(CustodyOwnedMemory::usedBytes() == owned); locks(paths, false); noEffects();
            }
            released(); retry();
            for (const auto spare : {std::size_t{0}, std::size_t{512}}) {
                inject(FileFault::none); auto input = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(input.ok());
                CustodyAllocator<std::uint8_t> allocator;
                const auto bytes = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes() - spare;
                auto* pressure = allocator.allocate(bytes); inject(FileFault::none);
                const auto denied = Pair::read(std::move(*input.value), cancelled);
                assert(!denied.ok() && !denied.value && denied.error == CustodyFileError::allocationFailed);
                assert(CustodyOwnedMemory::usedBytes() == owned + bytes); noEffects(); locks(paths, false);
                allocator.deallocate(pressure, bytes); released(); retry();
            }
            std::printf("CUSTODY_BOOTSTRAP_INTENT_CUTS schema=%u subject=%u allocations=%zu reads=%u hashes=%u direct_birth_reads=2 final_allocation_cancel=checked\n",
                schema, static_cast<unsigned>(subject), allocations, totalReads, totalHashes);
            queueAllocation = {}; afterRead = {}; inject(FileFault::none); released();
        }
    }
    {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, 1, CustodyMigrationSubject::queue);
        const auto cipher = sealBirth(birth); prepare(f, birth, cipher, {birth, birth});
        const auto owned = CustodyOwnedMemory::usedBytes();
        auto explicitOnly = ProtectedCustodyBootstrapPair::read(f.root, f.context, queueId, cancelled); assert(explicitOnly.ok());
        inject(FileFault::none); const auto denied = Pair::read(std::move(*explicitOnly.value), cancelled);
        assert(!denied.ok() && !denied.value && denied.error == CustodyFileError::invalidInput && !opens);
        assert(CustodyOwnedMemory::usedBytes() == owned); locks(identities(f, birth.subject), false); noEffects();
    }
    for (const auto subject : {CustodyMigrationSubject::queue, CustodyMigrationSubject::package}) {
        // These native identities are discovered independently of the authenticated JSON; no private getters.
        for (unsigned fault = 0; fault < 8; ++fault) {
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, 2, subject);
            const auto cipher = sealBirth(birth); prepare(f, birth, cipher, {birth, birth});
            const auto directory = location(f, subject), identity = directory/L"id.bin", alias = f.root/L"intent-id-alias";
            const auto relocated = f.root/L"relocated-intent";
            if (fault <= 3) {
                assert(DeleteFileW(identity.c_str()));
                if (fault == 1 || fault == 2) f.write(identity, CustodyBytes(fault == 1 ? 15 : 17, 0));
                if (fault == 3) { auto wrong = birth.context.objectId; wrong[0] ^= 1; f.write(identity, CustodyBytes(wrong.begin(), wrong.end())); }
            }
            if (fault == 4) assert(CreateHardLinkW(alias.c_str(), identity.c_str(), nullptr));
            BOOL present = FALSE, defaulted = FALSE; PACL dacl = nullptr;
            assert(GetSecurityDescriptorDacl(f.descriptor, &present, &dacl, &defaulted) && present && dacl);
            if (fault == 5) assert(SetNamedSecurityInfoW(identity.wstring().data(), SE_FILE_OBJECT,
                DACL_SECURITY_INFORMATION|UNPROTECTED_DACL_SECURITY_INFORMATION, nullptr, nullptr, dacl, nullptr) == ERROR_SUCCESS);
            if (fault == 6) { assert(MoveFileW(directory.c_str(), relocated.c_str())); junction(directory, relocated, f.security); }
            const auto owned = CustodyOwnedMemory::usedBytes(); inject(FileFault::none);
            auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
            inject(fault == 7 ? FileFault::identityMismatch : FileFault::none);
            const auto denied = Pair::read(std::move(*parent.value), cancelled);
            const auto error = fault == 0 ? CustodyFileError::ioFailed : fault == 3 ? CustodyFileError::protectionFailed :
                fault == 4 || fault == 5 ? CustodyFileError::unsafeFile : fault == 6 ? CustodyFileError::unsafePath : CustodyFileError::identityMismatch;
            std::fprintf(stderr, "CUSTODY_BOOTSTRAP_INTENT_NATIVE_ID schema=%u subject=%u fault=%u ok=%u has_value=%u actual_error=%u native=%u expected_error=%u\n",
                birth.schema, static_cast<unsigned>(subject), fault, static_cast<unsigned>(denied.ok()),
                static_cast<unsigned>(denied.value.has_value()), static_cast<unsigned>(denied.error),
                static_cast<unsigned>(denied.nativeError), static_cast<unsigned>(error));
            std::fflush(stderr);
            assert(!denied.ok() && !denied.value && denied.error == error);
            if (fault == 0) assert(denied.nativeError == ERROR_FILE_NOT_FOUND && !std::filesystem::exists(identity));
            if (fault == 3) assert(denied.nativeError == ERROR_INVALID_DATA);
            assert(CustodyOwnedMemory::usedBytes() == owned); noEffects();
            auto paths = identities(f, subject); locks(std::array<std::filesystem::path, 3>{paths[0], paths[1], paths[2]}, false);
            // Repair ONLY this generated negative fixture; fresh retry must use the real factory, without a fault.
            if (fault <= 3) { if (fault) assert(DeleteFileW(identity.c_str()));
                f.write(identity, CustodyBytes(birth.context.objectId.begin(), birth.context.objectId.end())); }
            if (fault == 4) assert(DeleteFileW(alias.c_str()));
            if (fault == 5) assert(SetNamedSecurityInfoW(identity.wstring().data(), SE_FILE_OBJECT,
                DACL_SECURITY_INFORMATION|PROTECTED_DACL_SECURITY_INFORMATION, nullptr, nullptr, dacl, nullptr) == ERROR_SUCCESS);
            if (fault == 6) { assert(RemoveDirectoryW(directory.c_str())); assert(MoveFileW(relocated.c_str(), directory.c_str())); }
            check(f, birth, CustodyFileError::none);
        }
        {
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto birth = makeBirth(f, 1, subject);
            reserve(f); commitBootstrap(f, bootstrapValue(f, birth, 1));
            const auto owned = CustodyOwnedMemory::usedBytes(); inject(FileFault::none);
            { const auto denied = link(f); assert(!denied.ok() && !denied.value && denied.error == CustodyFileError::ioFailed); noEffects(); }
            assert(!std::filesystem::exists(location(f, subject)) && CustodyOwnedMemory::usedBytes() == owned);
        }
        {
            // Same physical ID bytes in another generated root cannot substitute for the retained parent's root.
            Fixture a(CustodyRole::bootstrap, L"bootstrap"), b(CustodyRole::bootstrap, L"bootstrap");
            const auto birthA = makeBirth(a, 2, subject); auto birthB = makeBirth(b, 2, subject);
            birthB.anchor.length = 7; birthB.anchor.sha256.fill(23);
            if (subject == CustodyMigrationSubject::queue) { birthB.sources[0].length = 7; birthB.sources[0].sha256 = birthB.anchor.sha256; }
            const auto cipherA = sealBirth(birthA), cipherB = sealBirth(birthB);
            prepare(a, birthA, cipherA, {birthA, birthA}); prepare(b, birthB, cipherB, {birthB, birthB});
            assert(a.context.storeId == b.context.storeId && a.context.objectId == b.context.objectId && birthA.context.objectId == birthB.context.objectId);
            struct RestoreDirectory { wchar_t previous[32768]{};
                RestoreDirectory() { assert(GetCurrentDirectoryW(32768, previous)); }
                ~RestoreDirectory() { assert(SetCurrentDirectoryW(previous)); }
            } restore;
            assert(SetCurrentDirectoryW(b.root.c_str()));
            const std::wstring prefix = L"\\\\?\\" + a.root.wstring() + L"\\";
            const auto observeA = [&] { wchar_t path[1024]{}; const auto count = GetFinalPathNameByHandleW(afterReadFile, path, 1024, FILE_NAME_NORMALIZED);
                assert(count && count < 1024 && count >= prefix.size());
                assert(CompareStringOrdinal(path, static_cast<int>(prefix.size()), prefix.c_str(), static_cast<int>(prefix.size()), TRUE) == CSTR_EQUAL); };
            const auto owned = CustodyOwnedMemory::usedBytes();
            for (bool corruptB : {false, true}) {
                if (corruptB) { const auto path = location(b, subject)/L"index.1";
                    assert(DeleteFileW(path.c_str())); b.write(path, CustodyBytes(32, 0)); }
                inject(FileFault::none); afterRead = observeA;
                { const auto result = link(a); assert(result.ok() && result.value->get()->current().anchor.length == birthA.anchor.length); noEffects(); }
                afterRead = {}; assert(CustodyOwnedMemory::usedBytes() == owned);
                locks(identities(a, subject), false); locks(identities(b, subject), false);
                if (!corruptB) { inject(FileFault::none); const auto result = link(b);
                    assert(result.ok() && result.value->get()->current().anchor.length == birthB.anchor.length); noEffects(); }
            }
        }
    }
    inject(FileFault::none); assert(CustodyOwnedMemory::usedBytes() == before);
}
void protectedMigrationPairs() {
    using Pair = ProtectedCustodyMigrationPair;
    const auto before = CustodyOwnedMemory::usedBytes();
    {
        inject(FileFault::none);
        Fixture f(CustodyRole::migrationIntent, L"migration-intent");
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        CustodyMigrationValue birth;
        birth.context = f.context; birth.generation = 1; birth.transactionId[0] = 42;
        birth.anchor.length = 3; birth.anchor.sha256.fill(7); birth.sourceCount = 1;
        birth.sources[0].length = 3; birth.sources[0].sha256 = birth.anchor.sha256;
        birth.sources[0].destinationObjectId[0] = 8;
        const auto bytes = writeCustodyMigration(birth, f.context, 1, birth.transactionId, CustodyMigrationSubject::queue, "");
        assert(bytes.ok());
        assert(commitProtectedCustodyMetadata(f.root, "", f.context, 0, *bytes.value, cancelled).state == CustodyCommitState::committed);
        inject(FileFault::none);
        const auto result = ProtectedCustodyMigrationPair::read(f.root, f.context, birth.transactionId,
            CustodyMigrationSubject::queue, "", cancelled);
        // First native positive: the explicit Windows unsupported stub must fail at runtime here.
        assert(result.ok() && result.value && *result.value);
        assert(result.value->get()->selectedSlot() == 0 && result.value->get()->current().generation == 1);
        assert(result.value->get()->slots()[0].generation == 1 && result.value->get()->slots()[1].generation == 1);
        assert(result.value->get()->indices().indices[0].generation == 1 && result.value->get()->indices().indices[1].generation == 1);
        assert(!writes && !flushes && !renames);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    const auto makeBirth = [](Fixture& f, unsigned schema, CustodyMigrationSubject subject) {
        CustodyMigrationValue v; v.schema = schema; v.context = f.context; v.generation = 1;
        v.transactionId[0] = 42; v.subject = subject; v.anchor.length = 3; v.anchor.sha256.fill(7);
        v.sourceCount = 1; v.sources[0].length = 3; v.sources[0].sha256 = v.anchor.sha256;
        v.sources[0].destinationObjectId[0] = 8;
        if (subject == CustodyMigrationSubject::package) {
            f.service = false; assert(CreateDirectoryW((f.root / L"package-a").c_str(), &f.security));
            v.directory.emplace(); const std::string name = "package-a";
            std::copy(name.begin(), name.end(), v.directory->begin());
            v.anchor.objectId = CustodyId{}; v.anchor.objectId->at(0) = 13; v.anchor.generation = 2;
            v.sources[0].kind = CustodyMigrationSourceKind::manifest; v.sourceCount = 2;
            v.sources[1] = v.sources[0]; v.sources[1].kind = CustodyMigrationSourceKind::media;
            v.sources[1].length = 5; v.sources[1].sha256.fill(9); v.sources[1].destinationObjectId[0] = 10;
            if (schema == 2) { v.sources[1].destinationPacked = true;
                v.sources[1].destinationContainerId = CustodyId{}; v.sources[1].destinationContainerId->at(0) = 19; }
        }
        return v;
    };
    const auto encode = [](const CustodyMigrationValue& v) {
        auto bytes = writeCustodyMigration(v, v.context, v.generation, v.transactionId, v.subject,
            v.subject == CustodyMigrationSubject::queue ? "" : "package-a");
        assert(bytes.ok()); return std::move(*bytes.value);
    };
    const auto sealBirth = [&](const CustodyMigrationValue& v) {
        auto bytes = encode(v); auto cipher = ProtectedCustodyCodec::sealBlock(v.context, 0, 17, bytes);
        assert(cipher.ok()); return std::move(*cipher.value);
    };
    const auto barrier = [](const Fixture& f, const CustodyBytes& cipher) {
        const auto hash = custody_detail::digest(cipher.data(), cipher.size()); assert(hash);
        return CustodyMigrationBarrier{f.context.objectId, 1, 17, cipher.size(), *hash};
    };
    const auto copied = [](CustodyMigrationValue v, std::uint64_t generation, CustodyMigrationStage stage) {
        v.generation = generation; v.stage = stage;
        for (std::size_t i = 0; i < v.sourceCount; ++i) {
            auto& s = v.sources[i]; s.destinationGeneration = 5; s.destinationLength = s.length; s.destinationSha256 = s.sha256;
            if (s.destinationPacked) {
                s.destinationCommittedExtent = ProtectedPackedCustodyFormat::appendOffset + 128;
                s.destinationRootRef = ProtectedPackedCustodyFormat::encodeReference(
                    {PackedRecordKind::nodeL2, 128, ProtectedPackedCustodyFormat::appendOffset, 5, 0, {}});
                assert(s.destinationRootRef);
            }
        }
        return v;
    };
    const auto authorization = [] {
        CustodyCleanupAuthorization a; a.kind = CustodyCleanupKind::deletePurge;
        const std::string operation = "cleanup-273", actor = "user-a", workspace = "workspace-a";
        std::copy(operation.begin(), operation.end(), a.operationId.begin());
        std::copy(actor.begin(), actor.end(), a.actorUserId.begin());
        std::copy(workspace.begin(), workspace.end(), a.workspaceId.begin());
        a.queueObjectId[0] = 66; a.queueGeneration = 4; return a;
    };
    const auto replaceField = [](CustodyBytes& bytes, std::string_view field, std::string_view replacement,
        std::string_view scope = {}) {
        std::string json(bytes.begin(), bytes.end()); const auto key = "\"" + std::string(field) + "\":";
        const auto scopeAt = scope.empty() ? 0 : json.find("\"" + std::string(scope) + "\":");
        assert(scopeAt != std::string::npos);
        const auto found = json.find(key, scopeAt); assert(found != std::string::npos);
        const auto first = found + key.size();
        const auto end = json[first] == '"' ? json.find('"', first + 1) + 1 : json.find_first_of(",}", first);
        assert(end != std::string::npos && end > first);
        json.replace(first, end - first, replacement); bytes.assign(json.begin(), json.end());
    };
    const auto install = [&](Fixture& f, const CustodyBytes& birthCipher,
        const std::array<CustodyMigrationValue, 2>& values, int malformedSlot = -1, unsigned fault = 0) {
        inject(FileFault::none); auto files = f.open(CustodyFileAccess::createNew); assert(files.ok());
        f.write(f.object() / L"block.0.17", birthCipher);
        for (unsigned slot = 0; slot < 2; ++slot) {
            auto bytes = encode(values[slot]);
            if (values[slot].sourceCount == 2 && values[slot].sources[0].kind > values[slot].sources[1].kind) {
                // Writer sorts by kind; explicitly permute WIRE sources to test decoded by-kind correspondence.
                std::string json(bytes.begin(), bytes.end()); const auto first = json.find("\"sources\":[") + 11;
                const auto middle = json.find("},{", first), end = json.find("],\"barrier\":", first);
                assert(middle != std::string::npos && end != std::string::npos);
                const auto a = json.substr(first, middle + 1 - first), b = json.substr(middle + 2, end - middle - 2);
                json.replace(first, end - first, b + "," + a); bytes.assign(json.begin(), json.end());
            }
            if (static_cast<int>(slot) == malformedSlot) {
                if (fault == 0) bytes[0] = '[';
                if (fault == 1) replaceField(bytes, "generation", "9");
                if (fault == 2) replaceField(bytes, "object_id", "\"00000000000000000000000000000000\"");
                if (fault == 3) replaceField(bytes, "transaction_id", "\"00000000000000000000000000000000\"");
                if (fault == 4) replaceField(bytes, "subject", values[slot].subject == CustodyMigrationSubject::queue ? "\"package\"" : "\"queue\"");
                if (fault == 5) replaceField(bytes, "directory_id", "\"other-package\"");
                if (fault == 6) replaceField(bytes, "store_id", "\"00000000000000000000000000000000\"");
                if (fault == 7) bytes.resize(65536, ' ');
                if (fault == 8) replaceField(bytes, "object_id", "\"00000000000000000000000000000000\"", "barrier");
                if (fault == 9) replaceField(bytes, "generation", "2", "barrier");
                if (fault == 10) replaceField(bytes, "destination_generation", "null", "sources");
                if (fault == 11) replaceField(bytes, "destination_length", "4", "sources");
                if (fault == 12) replaceField(bytes, "destination_sha256", "null", "sources");
                if (fault == 13 || fault == 14) {
                    std::string json(bytes.begin(), bytes.end()); const auto first = json.find("{\"source\":\"media\"");
                    const auto end = json.find('}', first); assert(first != std::string::npos && end != std::string::npos);
                    CustodyBytes source(json.begin() + first, json.begin() + end + 1);
                    replaceField(source, fault == 13 ? "destination_committed_extent" : "destination_root_ref", "null");
                    json.replace(first, end + 1 - first, std::string(source.begin(), source.end())); bytes.assign(json.begin(), json.end());
                }
                if (fault == 15) replaceField(bytes, "destination_sha256", "\"0000000000000000000000000000000000000000000000000000000000000000\"", "sources");
            }
            const auto version = values[slot].generation == 1 ? std::uint64_t{17} : 31 + std::uint64_t{slot};
            std::uint32_t envelopeBytes = static_cast<std::uint32_t>(birthCipher.size());
            if (version != 17) {
                auto cipher = ProtectedCustodyCodec::sealBlock(f.context, 0, version, bytes); assert(cipher.ok());
                const auto saved = (*files.value)->writeBlock(0, version, static_cast<std::uint32_t>(bytes.size()), *cipher.value);
                assert(saved.ok()); envelopeBytes = *saved.value;
            } else {
                auto birthPlain = ProtectedCustodyCodec::openMigrationBirthBlock(f.context, 17, birthCipher);
                assert(birthPlain.ok() && bytes == *birthPlain.value);
            }
            publish(f, **files.value, slot, CustodyIndex{values[slot].generation, bytes.size(), {{version, envelopeBytes, 0}}});
        }
    };
    const auto read = [&](const Fixture& f, const CustodyMigrationValue& expected) {
        return Pair::read(f.root, f.context, expected.transactionId, expected.subject, f.service ? "" : "package-a", cancelled);
    };
    const auto noEffects = [] { assert(!writes && !flushes && !renames && !searches && !diskChecks); };
    const auto check = [&](Fixture& f, const CustodyMigrationValue& expected, CustodyFileError error) {
        const auto artifacts = writerArtifacts(f); const auto owned = CustodyOwnedMemory::usedBytes(); inject(FileFault::none);
        {
            const auto result = read(f, expected);
            if (error == CustodyFileError::none) assert(result.ok() && result.value && *result.value);
            else assert(!result.ok() && !result.value && result.error == error);
            noEffects(); assert(writerArtifacts(f) == artifacts);
        }
        assert(CustodyOwnedMemory::usedBytes() == owned);
        assert(f.open(CustodyFileAccess::writeExisting).ok()); // Factory failure/final release really closed its lease.
    };
    {
        Fixture f(CustodyRole::migrationIntent, L"migration-intent");
        const auto birth = makeBirth(f, 2, CustodyMigrationSubject::queue);
        const auto rootText = f.root.native(), drive = rootText.substr(0, 3);
        auto embeddedNull = rootText; embeddedNull.push_back(L'\0'); embeddedNull += L"suffix";
        const auto oversized = drive + std::wstring(29998, L'a');
        // Root grammar runs in this selector too, before any instrumented open.
        for (const auto& invalid : {std::wstring{}, drive, std::wstring(L"relative\\root"),
            drive.substr(0, 2) + L"relative", std::wstring(L"\\\\server\\share"),
            std::wstring(L"\\\\?\\") + rootText, rootText + L"/leaf", rootText + L":stream",
            rootText + L"\\.", rootText + L"\\..\\leaf", rootText + L"\\component.\\leaf",
            rootText + L"\\component \\leaf", rootText + L".", rootText + L" ",
            rootText + L"\\", embeddedNull, oversized}) {
            inject(FileFault::none);
            const auto denied = Pair::read(std::filesystem::path(invalid), f.context, birth.transactionId,
                CustodyMigrationSubject::queue, "", cancelled);
            assert(!denied.ok() && !denied.value && denied.error == CustodyFileError::unsafePath && !opens);
            noEffects();
        }
        // Private same-TU lexical/volume checks ONLY: these are not confinement or existing-root proofs.
        inject(FileFault::none);
        assert(!graf::windows::localPath(std::filesystem::path(drive))); // 3 native code units.
        assert(graf::windows::localPath(std::filesystem::path(drive + L"a"))); // 4, no directory opened.
        assert(graf::windows::localPath(std::filesystem::path(drive + std::wstring(29997, L'a')))); // 30000.
        assert(!graf::windows::localPath(std::filesystem::path(oversized))); // 30001.
        auto upper = rootText, lower = rootText;
        upper[0] = static_cast<wchar_t>(rootText[0] >= L'a' && rootText[0] <= L'z' ? rootText[0] - L'a' + L'A' : rootText[0]);
        lower[0] = static_cast<wchar_t>(rootText[0] >= L'A' && rootText[0] <= L'Z' ? rootText[0] - L'A' + L'a' : rootText[0]);
        assert(graf::windows::localPath(std::filesystem::path(upper)) && graf::windows::localPath(std::filesystem::path(lower)));
        auto repeated = rootText; const auto separator = repeated.find_last_of(L'\\'); assert(separator > 2);
        repeated.insert(separator, 1, L'\\');
        auto repeatedDrive = rootText; repeatedDrive.insert(2, 1, L'\\');
        assert(graf::windows::localPath(std::filesystem::path(repeated)));
        assert(graf::windows::localPath(std::filesystem::path(repeatedDrive)));
        assert(graf::windows::localPath(std::filesystem::path(drive + L"\u043f\u0430\u043f\u043a\u0430-\u6bb5")));
        assert(!opens); noEffects();
        auto cipher = sealBirth(birth); install(f, cipher, {birth, birth});
        const auto artifacts = writerArtifacts(f); const auto owned = CustodyOwnedMemory::usedBytes();
        for (const auto& alias : {repeated, repeatedDrive}) {
            inject(FileFault::none);
            const auto denied = Pair::read(std::filesystem::path(alias), f.context, birth.transactionId,
                CustodyMigrationSubject::queue, "", cancelled);
            // Lexical acceptance above is distinct from native root admission.
            assert(!denied.ok() && !denied.value && denied.error == CustodyFileError::unsafePath && opens > 0);
            assert(CustodyOwnedMemory::usedBytes() == owned && writerArtifacts(f) == artifacts); noEffects();
            inject(FileFault::none);
            const auto deniedCreate = ProtectedCustodyStoreOwner::open(std::filesystem::path(alias), cancelled);
            assert(!deniedCreate.ok() && !deniedCreate.value && deniedCreate.error == CustodyFileError::unsafePath);
            assert(CustodyOwnedMemory::usedBytes() == owned && writerArtifacts(f) == artifacts); noEffects();
        }
        assert(f.open(CustodyFileAccess::writeExisting).ok());
    }
    {
        Fixture f(CustodyRole::migrationIntent, L"migration-intent");
        const auto independent = f.context;
        // Rename only this generated unique root, before install/acquisition of any identity lease.
        std::filesystem::path ownUniqueRoot(f.root.native() + L"-\u043f\u0430\u043f\u043a\u0430-\u6bb5");
        assert(MoveFileW(f.root.c_str(), ownUniqueRoot.c_str())); f.root = std::move(ownUniqueRoot);
        const auto birth = makeBirth(f, 2, CustodyMigrationSubject::queue);
        auto cipher = sealBirth(birth); install(f, cipher, {birth, birth});
        const auto artifacts = writerArtifacts(f); const auto owned = CustodyOwnedMemory::usedBytes(); inject(FileFault::none);
        {
            const auto result = Pair::read(f.root, independent, birth.transactionId, CustodyMigrationSubject::queue, "", cancelled);
            assert(result.ok() && result.value && *result.value);
            const auto& pair = **result.value;
            assert(pair.selectedSlot() == 0 && pair.current().generation == 1 && pair.current().schema == 2);
            assert(pair.current().context.storeId == independent.storeId && pair.current().context.objectId == independent.objectId &&
                pair.current().context.role == independent.role && pair.current().transactionId == birth.transactionId);
            assert(pair.slots()[0].generation == 1 && pair.slots()[1].generation == 1 &&
                pair.indices().indices[0].generation == 1 && pair.indices().indices[1].generation == 1);
            assert(writerArtifacts(f) == artifacts); noEffects();
        }
        assert(CustodyOwnedMemory::usedBytes() == owned && f.open(CustodyFileAccess::writeExisting).ok());
    }
    // Direct Files package regressions: no narrow filesystem conversion in either test paths or product paths.
    const auto asciiPackage = [&](std::string_view name, bool unicodeRoot) {
        Fixture f(CustodyRole::manifest, L"manifest"); assert(!f.service);
        const auto independent = f.context; const auto owned = CustodyOwnedMemory::usedBytes();
        { const auto created = f.open(CustodyFileAccess::createNew); assert(created.ok()); }
        assert(CustodyOwnedMemory::usedBytes() == owned);
        const std::wstring wideName(name.begin(), name.end());
        const auto oldPackage = f.root / L"package-a", renamedPackage = f.root / wideName;
        assert(MoveFileW(oldPackage.c_str(), renamedPackage.c_str()));
        if (unicodeRoot) {
            std::filesystem::path ownUniqueRoot(f.root.native() + L"-\u043f\u0430\u043f\u043a\u0430-\u6bb5");
            assert(MoveFileW(f.root.c_str(), ownUniqueRoot.c_str())); f.root = std::move(ownUniqueRoot);
        }
        // Fixture::object/open and writerArtifacts still name package-a; use the actual renamed location.
        const auto identityPath = f.root / wideName / L".custody-v1" / L"manifest" / L"id.bin";
        const auto storePath = f.root / L".custody-v1" / L"store.id";
        assert(!std::filesystem::exists(f.root / L"package-a"));
        inject(FileFault::none);
        {
            const auto result = ProtectedCustodyFiles::open(f.root, name, independent, CustodyFileAccess::readExisting);
            assert(result.ok() && result.value && *result.value);
            assert(independent.role == CustodyRole::manifest);
            assert(std::filesystem::file_size(identityPath) == 16 && std::filesystem::file_size(storePath) == 16); noEffects();
        }
        assert(CustodyOwnedMemory::usedBytes() == owned);
        auto wrong = independent; wrong.storeId[0] ^= 1;
        { const auto denied = ProtectedCustodyFiles::open(f.root, name, wrong, CustodyFileAccess::readExisting);
            assert(!denied.ok() && !denied.value && denied.error == CustodyFileError::identityMismatch); }
        assert(CustodyOwnedMemory::usedBytes() == owned); noEffects();
        wrong = independent; wrong.objectId[0] ^= 1;
        { const auto denied = ProtectedCustodyFiles::open(f.root, name, wrong, CustodyFileAccess::readExisting);
            assert(!denied.ok() && !denied.value && denied.error == CustodyFileError::identityMismatch); }
        assert(CustodyOwnedMemory::usedBytes() == owned); noEffects();
        const auto id = CreateFileW(identityPath.c_str(), GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
        assert(id != INVALID_HANDLE_VALUE); CloseHandle(id);
        const auto root = CreateFileW(f.root.c_str(), DELETE,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, nullptr);
        assert(root != INVALID_HANDLE_VALUE); CloseHandle(root); // All root/object leases closed before fixture teardown.
    };
    for (const std::string_view name : {"A", "a", "0", "_", "-", "Az09_-"}) asciiPackage(name, false);
    asciiPackage("Az09_-", true); // Unicode ROOT is permitted; package identity remains strictly ASCII.
    {
        Fixture f(CustodyRole::manifest, L"manifest");
        const std::filesystem::path badRoot(L"relative-root"); const auto owned = CustodyOwnedMemory::usedBytes();
        const std::array<const std::filesystem::path*, 2> roots{&f.root, &badRoot};
        const auto rejectPackages = [&] {
            for (const auto& name : {std::string{}, std::string(301, 'a'), std::string(1, static_cast<char>(0x80)),
                std::string(1, static_cast<char>(0xe0)), std::string(1, static_cast<char>(0xff)), std::string("\xd0\xb0"),
                std::string("\xc0\xaf"), std::string("A\0B", 3), std::string("A/B"), std::string("A\\B"),
                std::string("."), std::string(".."), std::string("A:stream"), std::string("A ")}) {
                // The same invalid identity must win even over a bad root: prove guard ordering, not just no IO.
                for (const auto* root : roots) {
                    inject(FileFault::none);
                    const auto denied = ProtectedCustodyFiles::open(*root, name, f.context, CustodyFileAccess::readExisting);
                    assert(!denied.ok() && !denied.value && denied.error == CustodyFileError::invalidInput && !opens);
                    assert(CustodyOwnedMemory::usedBytes() == owned); noEffects();
                }
            }
        };
        rejectPackages(); inject(FileFault::none);
        const auto acceptedGrammar = ProtectedCustodyFiles::open(badRoot, std::string(300, 'a'), f.context, CustodyFileAccess::readExisting);
        assert(!acceptedGrammar.ok() && !acceptedGrammar.value && acceptedGrammar.error == CustodyFileError::unsafePath && !opens);
        assert(CustodyOwnedMemory::usedBytes() == owned); noEffects(); // No claim that NTFS can create a 300-character component.
        {
            const auto* previous = std::setlocale(LC_CTYPE, nullptr); assert(previous);
            struct RestoreLocale {
                std::string value;
                ~RestoreLocale() { assert(std::setlocale(LC_CTYPE, value.c_str())); }
            } restore{previous};
            if (std::setlocale(LC_CTYPE, "Russian_Russia.1251") || std::setlocale(LC_CTYPE, ".1251")) {
                const bool expanded = DesktopUploadQueueService::validIdentity(std::string(1, static_cast<char>(0xe0)));
                rejectPackages();
                std::fputs("CUSTODY_PACKAGE_ASCII_LOCALE1251 checked_nonascii_rejection=1\n", stdout);
                if (expanded) std::fputs("CUSTODY_PACKAGE_ASCII_LOCALE1251 legacy_expansion_witness=1 rejected_before_open=1\n", stdout);
                else std::fputs("CUSTODY_PACKAGE_ASCII_LOCALE1251 SKIP locale-expansion-witness unavailable\n", stdout);
            } else std::fputs("CUSTODY_PACKAGE_ASCII_LOCALE1251 SKIP locale unavailable\n", stdout);
        }
    }
    for (unsigned schema : {1U, 2U}) for (const auto subject : {CustodyMigrationSubject::queue, CustodyMigrationSubject::package}) {
        for (unsigned step = 1; step <= 6; ++step) {
            Fixture f(CustodyRole::migrationIntent, L"migration-intent"); const auto birth = makeBirth(f, schema, subject);
            auto cipher = sealBirth(birth); const auto ref = barrier(f, cipher);
            std::array<CustodyMigrationValue, 2> slots{birth, birth};
            const auto state = [&](unsigned generation) {
                auto v = birth; v.generation = generation;
                if (generation >= 2) v.barrier = ref;
                if (generation >= 3) v = copied(v, generation, static_cast<CustodyMigrationStage>(generation - 2));
                if (generation >= 5) v.authorization = authorization();
                return v;
            };
            const auto lower = step == 1 ? 1U : step - 1;
            if (step != 1) {
                slots[(lower - 1) % 2] = state(lower); slots[(step - 1) % 2] = state(step);
            }
            if (subject == CustodyMigrationSubject::package && step >= 3) std::swap(slots[1].sources[0], slots[1].sources[1]);
            install(f, cipher, slots);
            const auto owned = CustodyOwnedMemory::usedBytes(); const auto artifacts = writerArtifacts(f); inject(FileFault::none);
            auto result = read(f, birth); assert(result.ok());
            assert(result.value->get()->selectedSlot() == (step == 1 ? 0U : (step - 1) % 2));
            assert(result.value->get()->current().generation == step && result.value->get()->current().schema == schema);
            for (unsigned slot = 0; slot < 2; ++slot) {
                assert(result.value->get()->slots()[slot].generation == slots[slot].generation);
                assert(result.value->get()->indices().indices[slot].generation == slots[slot].generation);
            }
            auto retained = *result.value; result.value.reset();
            const auto id = f.object() / L"id.bin";
            const auto competing = CreateFileW(id.c_str(), GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
            assert(competing == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
            { std::array<CustodyNativeJob, 4> jobs; for (const auto& job : jobs) assert(job); }
            { std::array<CustodyPin, 31> pins; for (const auto& pin : pins) assert(pin); CustodyPin overflow; assert(!overflow); }
            assert(retained->current().generation == step); noEffects(); assert(writerArtifacts(f) == artifacts);
            assert(!std::filesystem::exists(f.root / L".custody-v1" / L"queue"));
            assert(!std::filesystem::exists(f.root / L".custody-v1" / L"bootstrap"));
            retained.reset(); assert(CustodyOwnedMemory::usedBytes() == owned);
            assert(f.open(CustodyFileAccess::writeExisting).ok());
        }
        // Same stage, a forward jump and non-adjacent generations are own-record semantics, NOT effect ACKs.
        for (unsigned variant = 0; variant < 4; ++variant) {
            Fixture f(CustodyRole::migrationIntent, L"migration-intent"); auto birth = makeBirth(f, schema, subject);
            auto cipher = sealBirth(birth); auto first = birth; first.generation = 3;
            auto last = first; last.generation = variant == 3 ? 8 : 4;
            if (variant == 0) { first = copied(first, 3, CustodyMigrationStage::copiedVerified);
                last = copied(last, 4, CustodyMigrationStage::copiedVerified); } // No new mandatory barrier at copied.
            if (variant == 1) { last = copied(last, 4, CustodyMigrationStage::complete);
                last.barrier = barrier(f, cipher); last.authorization = authorization(); }
            if (variant == 2) { last.barrier = barrier(f, cipher); last.authorization = authorization(); } // Early valid auth.
            install(f, cipher, {first, last}); check(f, birth, CustodyFileError::none);
        }
        // Independently well-formed prepared records isolate immutable Pair conflicts from Birth/native failures.
        for (unsigned fault = 0; fault < 13; ++fault) {
            if (subject == CustodyMigrationSubject::queue && (fault == 5 || fault == 6 || fault >= 10)) continue;
            if (fault >= 10 && (schema != 2 || subject != CustodyMigrationSubject::package) && fault != 12) continue;
            Fixture f(CustodyRole::migrationIntent, L"migration-intent"); auto birth = makeBirth(f, schema, subject);
            auto cipher = sealBirth(birth); auto first = birth; first.generation = 3; auto last = first; last.generation = 4;
            auto& s = last.sources[subject == CustodyMigrationSubject::queue ? 0 : 1];
            if (fault == 0) { last.schema = schema == 1 ? 2 : 1;
                for (auto& source : last.sources) { source.destinationPacked = false; source.destinationContainerId.reset(); } }
            if (fault == 1) { last.anchor.objectId = CustodyId{}; last.anchor.objectId->at(0) = 14; last.anchor.generation = 2; }
            if (fault == 2) { if (!last.anchor.objectId) last.anchor.objectId = CustodyId{}; last.anchor.generation = 3; }
            if (fault == 3) { ++last.anchor.length; if (subject == CustodyMigrationSubject::queue) ++s.length; }
            if (fault == 4) { last.anchor.sha256[0] ^= 1; if (subject == CustodyMigrationSubject::queue) s.sha256 = last.anchor.sha256; }
            if (fault == 5) { last.sources[2] = last.sources[0]; last.sources[2].kind = CustodyMigrationSourceKind::recovery; last.sourceCount = 3; }
            if (fault == 6) s.kind = CustodyMigrationSourceKind::canonical;
            if (fault == 7) { ++s.length; if (subject == CustodyMigrationSubject::queue) last.anchor.length = s.length; }
            if (fault == 8) { s.sha256[0] ^= 1; if (subject == CustodyMigrationSubject::queue) last.anchor.sha256 = s.sha256; }
            if (fault == 9) s.destinationObjectId[0] ^= 1;
            if (fault == 10) { s.destinationPacked = false; s.destinationContainerId.reset(); }
            if (fault == 11) s.destinationContainerId->at(0) ^= 1;
            if (fault == 12) last.sourceCount = 1; // Subset is not the same source set.
            install(f, cipher, {first, last}); check(f, birth, CustodyFileError::conflict);
        }
        for (unsigned fault = 0; fault < 14; ++fault) {
            if (fault >= 11 && (schema != 2 || subject != CustodyMigrationSubject::package)) continue;
            Fixture f(CustodyRole::migrationIntent, L"migration-intent"); auto birth = makeBirth(f, schema, subject);
            auto cipher = sealBirth(birth); auto first = copied(birth, 3, CustodyMigrationStage::copiedVerified);
            auto last = copied(birth, 4, CustodyMigrationStage::copiedVerified);
            first.barrier = last.barrier = barrier(f, cipher); first.authorization = last.authorization = authorization();
            if (fault == 0) { last = birth; last.generation = 4; last.barrier = first.barrier; last.authorization = first.authorization; }
            if (fault == 1) last.barrier.reset();
            if (fault == 2) last.authorization.reset();
            if (fault == 3) { last.authorization->kind = CustodyCleanupKind::ownerConfirmation;
                last.authorization->operationId.fill(0); const std::string id = "2a000000000000000000000000000000";
                std::copy(id.begin(), id.end(), last.authorization->operationId.begin()); }
            if (fault == 4) last.authorization->operationId[0] = 'x';
            if (fault == 5) last.authorization->actorUserId[0] = 'x';
            if (fault == 6) last.authorization->workspaceId[0] = 'x';
            if (fault == 7) last.authorization->queueObjectId[0] ^= 1;
            if (fault == 8) ++last.authorization->queueGeneration;
            if (fault == 9) ++*last.sources[0].destinationGeneration;
            if (fault == 10 && subject == CustodyMigrationSubject::package) {
                std::swap(last.sources[0], last.sources[1]); ++*last.sources[0].destinationGeneration;
            } else if (fault == 10) last.sources[0].destinationGeneration = 7;
            if (fault == 11) *last.sources[1].destinationCommittedExtent += 128;
            if (fault == 12) last.sources[1].destinationRootRef = ProtectedPackedCustodyFormat::encodeReference(
                {PackedRecordKind::nodeL2, 128, ProtectedPackedCustodyFormat::appendOffset, 4, 0, {}});
            if (fault == 13) { last.sources[1].destinationPacked = false; last.sources[1].destinationContainerId.reset();
                last.sources[1].destinationCommittedExtent.reset(); last.sources[1].destinationRootRef.reset();
                first.barrier.reset(); last.barrier.reset(); } // Isolate representation conflict without a foreign Birth.
            install(f, cipher, {first, last}); check(f, birth, CustodyFileError::conflict);
        }
        for (unsigned slot = 0; slot < 2; ++slot) for (unsigned fault = 0; fault < 16; ++fault) {
            if (fault == 7) continue; // Exact 64KiB is positive below, not malformed.
            if ((fault == 13 || fault == 14) && (schema != 2 || subject != CustodyMigrationSubject::package)) continue;
            Fixture f(CustodyRole::migrationIntent, L"migration-intent"); const auto birth = makeBirth(f, schema, subject);
            auto cipher = sealBirth(birth); auto first = copied(birth, 3, CustodyMigrationStage::copiedVerified);
            auto last = copied(birth, 4, CustodyMigrationStage::copiedVerified); first.barrier = last.barrier = barrier(f, cipher);
            install(f, cipher, {first, last}, static_cast<int>(slot), fault);
            check(f, birth, CustodyFileError::invalidContent); // Physical SHA/DPAPI valid, semantic own payload invalid.
        }
        // Missing/corrupt physical peer cannot be replaced by the other validated record.
        for (unsigned fault = 0; fault < 8; ++fault) {
            Fixture f(CustodyRole::migrationIntent, L"migration-intent"); const auto birth = makeBirth(f, schema, subject);
            auto cipher = sealBirth(birth); auto first = copied(birth, 3, CustodyMigrationStage::copiedVerified);
            auto last = copied(birth, 4, CustodyMigrationStage::copiedVerified); first.barrier = last.barrier = barrier(f, cipher);
            install(f, cipher, {first, last});
            if (fault <= 2) {
                assert(DeleteFileW((f.object() / L"index.0").c_str()));
                if (fault >= 1) assert(DeleteFileW((f.object() / L"index.1").c_str()));
                if (fault == 2) f.write(f.object() / L"index.0", CustodyBytes(32, 0));
            }
            if (fault == 3) { assert(DeleteFileW((f.object() / L"index.1").c_str())); f.write(f.object() / L"index.1", CustodyBytes(32, 0)); }
            if (fault == 4) assert(DeleteFileW((f.object() / L"block.0.31").c_str()));
            if (fault == 5) assert(DeleteFileW((f.object() / L"block.0.32").c_str()));
            if (fault == 6) { assert(DeleteFileW((f.object() / L"block.0.31").c_str())); f.write(f.object() / L"block.0.31", CustodyBytes(32, 0)); }
            if (fault == 7) { assert(DeleteFileW((f.object() / L"block.0.32").c_str())); f.write(f.object() / L"block.0.32", CustodyBytes(32, 0)); }
            const auto artifacts = writerArtifacts(f); const auto owned = CustodyOwnedMemory::usedBytes(); inject(FileFault::none);
            const auto denied = read(f, birth); assert(!denied.ok() && !denied.value); noEffects();
            assert(writerArtifacts(f) == artifacts && CustodyOwnedMemory::usedBytes() == owned);
        }
        for (unsigned slot = 0; slot < 2; ++slot) for (unsigned fault = 0; fault < 4; ++fault) {
            Fixture f(CustodyRole::migrationIntent, L"migration-intent"); const auto birth = makeBirth(f, schema, subject);
            auto cipher = sealBirth(birth); auto first = copied(birth, 3, CustodyMigrationStage::copiedVerified);
            auto last = copied(birth, 4, CustodyMigrationStage::copiedVerified); install(f, cipher, {first, last});
            // Independent authenticated index fixture, same v1 layout/entropy as CodecTests.
            // Oversize/multiple-entry cannot be emitted by the checked production writer.
            const auto put = [](CustodyBytes& bytes, std::size_t at, std::uint64_t value, std::size_t width) {
                for (std::size_t i = 0; i < width; ++i) bytes.at(at + i) = static_cast<std::uint8_t>(value >> (8 * i));
            };
            const unsigned count = fault == 0 ? 0U : fault == 3 ? 2U : 1U;
            CustodyBytes plain(112 + count * 16); custody_detail::WipeBytes wipe{plain};
            std::memcpy(plain.data(), "GRAFIX01", 8); put(plain, 8, 1, 2); put(plain, 10, static_cast<unsigned>(f.context.role), 2); put(plain, 12, 112, 4);
            std::copy(f.context.storeId.begin(), f.context.storeId.end(), plain.begin() + 16);
            std::copy(f.context.objectId.begin(), f.context.objectId.end(), plain.begin() + 32);
            put(plain, 48, 3 + slot, 8); put(plain, 56, fault == 0 ? 0 : fault == 1 ? 64 : fault == 2 ? 65537 : 65536, 8);
            put(plain, 64, ProtectedCustodyCodec::blockBytes, 4); put(plain, 68, count, 4);
            if (fault == 1) put(plain, 124, 1, 4); // Valid ZERO, prohibited for authority payloads.
            if (fault >= 2) { put(plain, 112, 31 + slot, 8); put(plain, 120, 64, 4); }
            const auto hash = custody_detail::digest(plain.data(), plain.size()); assert(hash);
            std::copy(hash->begin(), hash->end(), plain.begin() + 80);
            const std::string prefix = "graf.custody.v1"; CustodyBytes entropy(prefix.begin(), prefix.end());
            entropy.insert(entropy.end(), f.context.storeId.begin(), f.context.storeId.end());
            entropy.insert(entropy.end(), f.context.objectId.begin(), f.context.objectId.end());
            const auto base = entropy.size(); entropy.resize(base + 20);
            put(entropy, base, static_cast<unsigned>(f.context.role), 2); put(entropy, base + 2, 2, 2); put(entropy, base + 4, slot, 8);
            auto sealed = custody_detail::nativeTransform(entropy.data(), entropy.size(), plain.data(), plain.size(), 65536, true); assert(sealed.ok());
            CustodyBytes envelope(16); std::memcpy(envelope.data(), "GRAFDP01", 8);
            put(envelope, 8, 1, 2); put(envelope, 10, 2, 2); put(envelope, 12, sealed.value->size(), 4);
            envelope.insert(envelope.end(), sealed.value->begin(), sealed.value->end());
            const auto path = f.object() / (slot ? L"index.1" : L"index.0"); assert(DeleteFileW(path.c_str())); f.write(path, envelope);
            check(f, birth, CustodyFileError::invalidContent);
        }
        {
            Fixture f(CustodyRole::migrationIntent, L"migration-intent"); const auto birth = makeBirth(f, schema, subject);
            auto cipher = sealBirth(birth); auto first = copied(birth, 3, CustodyMigrationStage::copiedVerified);
            auto last = copied(birth, 4, CustodyMigrationStage::copiedVerified);
            install(f, cipher, {first, last}, 0, 7); check(f, birth, CustodyFileError::none); // Actual 65536-byte own JSON.
        }
        // Both references can be individually genuine yet conflict as a sticky barrier.
        for (bool padded : {false, true}) {
            Fixture f(CustodyRole::migrationIntent, L"migration-intent"); const auto birth = makeBirth(f, schema, subject);
            auto cipher = sealBirth(birth); auto first = birth; first.generation = 3; first.barrier = barrier(f, cipher);
            auto last = first; last.generation = 4;
            auto otherPlain = encode(birth); if (padded) otherPlain.resize(65536, ' ');
            auto otherCipher = ProtectedCustodyCodec::sealBlock(f.context, 0, 18, otherPlain); assert(otherCipher.ok());
            last.barrier = barrier(f, *otherCipher.value); last.barrier->blockVersion = 18;
            install(f, cipher, {first, last}); f.write(f.object() / L"block.0.18", *otherCipher.value);
            assert(readCustodyMigrationBirth(cipher, f.context, first, birth.transactionId, subject, f.service ? "" : "package-a").ok());
            assert(readCustodyMigrationBirth(*otherCipher.value, f.context, last, birth.transactionId, subject, f.service ? "" : "package-a").ok());
            check(f, birth, CustodyFileError::conflict);
        }
        for (unsigned fault = 0; fault < 8; ++fault) {
            Fixture f(CustodyRole::migrationIntent, L"migration-intent"); auto birth = makeBirth(f, schema, subject);
            auto changed = birth;
            if (fault == 4) { changed.anchor.length++; if (subject == CustodyMigrationSubject::queue) changed.sources[0].length++; }
            if (fault == 5) changed.context.objectId[0] ^= 1;
            auto cipher = sealBirth(changed);
            if (fault == 7) { const auto bytes = encode(birth); auto wrongVersion = ProtectedCustodyCodec::sealBlock(f.context, 0, 18, bytes);
                assert(wrongVersion.ok()); cipher = std::move(*wrongVersion.value); }
            auto first = copied(birth, 3, CustodyMigrationStage::copiedVerified);
            auto last = copied(birth, 4, CustodyMigrationStage::copiedVerified); auto ref = barrier(f, cipher);
            CustodyFileError error = CustodyFileError::invalidContent; std::uint32_t native = 0;
            if (fault == 0) { ref.blockVersion = 99; error = CustodyFileError::ioFailed; native = ERROR_FILE_NOT_FOUND; }
            if (fault == 6) { error = CustodyFileError::ioFailed; native = ERROR_FILE_NOT_FOUND; }
            if (fault == 1) --ref.envelopeBytes;
            if (fault == 2) ref.sha256[0] ^= 1;
            if (fault == 3) { cipher.back() ^= 1; ref = barrier(f, cipher); }
            if (fault == 3 || fault == 5 || fault == 7) {
                const auto expected = ProtectedCustodyCodec::openMigrationBirthBlock(f.context, 17, cipher);
                assert(!expected.ok()); error = codecFileError(expected.error); native = expected.nativeError;
            }
            first.barrier = last.barrier = ref; install(f, cipher, {first, last});
            if (fault == 6) {
                assert(DeleteFileW((f.object() / L"block.0.17").c_str()));
                f.write((f.service ? f.root : f.root / L"package-a") /
                    (f.service ? L"desktop-upload-queue.v2.quarantine" : L"manifest.json"), cipher);
            }
            const auto owned = CustodyOwnedMemory::usedBytes(); const auto artifacts = writerArtifacts(f); inject(FileFault::none);
            const auto result = read(f, birth);
            assert(!result.ok() && !result.value && result.error == error && result.nativeError == native);
            assert(CustodyOwnedMemory::usedBytes() == owned && writerArtifacts(f) == artifacts); noEffects();
            // Tombstone fixture is not read/verified; missing direct remains a refusal, NOT recovery proof.
        }
        // Root factory owns the entire IO operation; no outer fixture NativeJob/lease is held here.
        {
            Fixture f(CustodyRole::migrationIntent, L"migration-intent"); const auto birth = makeBirth(f, schema, subject);
            auto cipher = sealBirth(birth); auto first = copied(birth, 3, CustodyMigrationStage::copiedVerified);
            auto last = copied(birth, 4, CustodyMigrationStage::switched); first.barrier = last.barrier = barrier(f, cipher);
            if (subject == CustodyMigrationSubject::package) std::swap(last.sources[0], last.sources[1]);
            install(f, cipher, {first, last});
            const auto artifacts = writerArtifacts(f); const auto owned = CustodyOwnedMemory::usedBytes();
            const auto identityPath = f.object() / L"id.bin";
            const auto index0 = f.object() / L"index.0", index1 = f.object() / L"index.1", birthPath = f.object() / L"block.0.17";
            const std::wstring nativeIndex0 = L"\\\\?\\" + index0.wstring(), nativeIndex1 = L"\\\\?\\" + index1.wstring();
            const std::wstring nativeBirth = L"\\\\?\\" + birthPath.wstring();
            unsigned indexReads = 0, birthReads = 0; std::array<unsigned, 2> birthOrdinals{};
            std::size_t allocationsBeforeIndex = 0;
            const auto released = [&] {
                assert(CustodyOwnedMemory::usedBytes() == owned); noEffects(); assert(writerArtifacts(f) == artifacts);
                std::array<CustodyNativeJob, 4> jobs; for (const auto& job : jobs) assert(job);
                std::array<CustodyPin, 32> pins; for (const auto& pin : pins) assert(pin);
                const auto handle = CreateFileW(identityPath.c_str(), GENERIC_WRITE,
                    FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
                assert(handle != INVALID_HANDLE_VALUE); CloseHandle(handle);
            };
            const auto observe = [&] {
                wchar_t path[1024]{}; const auto count = GetFinalPathNameByHandleW(afterReadFile, path, 1024, FILE_NAME_NORMALIZED);
                assert(count && count < 1024);
                const bool index = CompareStringOrdinal(path, static_cast<int>(count), nativeIndex0.c_str(), -1, TRUE) == CSTR_EQUAL ||
                    CompareStringOrdinal(path, static_cast<int>(count), nativeIndex1.c_str(), -1, TRUE) == CSTR_EQUAL;
                const bool historical = CompareStringOrdinal(path, static_cast<int>(count), nativeBirth.c_str(), -1, TRUE) == CSTR_EQUAL;
                if (!index && !historical) return; // Fixed-ID reads can precede the own exclusive lease.
                const auto competing = CreateFileW(identityPath.c_str(), GENERIC_WRITE,
                    FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
                assert(competing == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
                std::array<CustodyNativeJob, 3> jobs; for (const auto& job : jobs) assert(job);
                CustodyNativeJob overflow; assert(!overflow);
                if (index) { if (!indexReads) allocationsBeforeIndex = queueAllocation.calls; ++indexReads; }
                if (historical) { assert(birthReads < birthOrdinals.size()); birthOrdinals[birthReads++] = reads; }
            };
            afterRead = observe; inject(FileFault::none);
            { const auto warm = read(f, birth); assert(warm.ok()); }
            assert(indexReads == 2 && birthReads == 2); released();
            const auto totalReads = reads; const auto directOrdinals = birthOrdinals;
            const auto invoke = [&](std::size_t failAt, std::size_t cancelAt) {
                indexReads = birthReads = 0; birthOrdinals = {}; inject(FileFault::none);
                queueAllocation = {}; queueAllocation.migrationFactory = true;
                queueAllocation.failAt = failAt; queueAllocation.cancelAt = cancelAt; queueAllocation.cancellation = cancelled.get();
                queueAllocation.active = true;
                auto result = read(f, birth);
                queueAllocation.active = false; return result;
            };
            auto counted = invoke(0, 0); assert(counted.ok());
            const auto allocations = queueAllocation.calls;
            assert(allocations > 0 && allocationsBeforeIndex > 0 && indexReads == 2 && birthReads == 2);
            counted.value.reset(); released();
            // EVERY actual global-new ordinal, including early path/identity allocations and Debug proxies.
            // No lease/job assertions in operator new: unlike candidate read, factory has not acquired them yet.
            for (std::size_t ordinal = 1; ordinal <= allocations; ++ordinal) {
                const auto result = invoke(ordinal, 0);
                assert(queueAllocation.hit && !result.ok() && !result.value && result.error == CustodyFileError::allocationFailed);
                released(); auto retry = invoke(0, 0); assert(retry.ok() && queueAllocation.calls == allocations); retry.value.reset(); released();
            }
            for (std::size_t ordinal = 1; ordinal <= allocations; ++ordinal) {
                const auto result = invoke(0, ordinal);
                assert(queueAllocation.hit && !result.ok() && !result.value && result.error == CustodyFileError::ioFailed &&
                    result.nativeError == ERROR_OPERATION_ABORTED);
                cancelled->store(false); released();
                auto retry = invoke(0, 0); assert(retry.ok() && queueAllocation.calls == allocations); retry.value.reset(); released();
            } // Last actual allocation includes result/controlblock publication; requires the FINAL cancellation poll.
            queueAllocation = {}; afterRead = {};
            for (unsigned ordinal = 1; ordinal <= totalReads; ++ordinal) {
                inject(FileFault::readFailed, ordinal); const auto result = read(f, birth);
                assert(!result.ok() && !result.value && result.error == CustodyFileError::ioFailed && result.nativeError == ERROR_READ_FAULT);
                released(); inject(FileFault::none); { const auto retry = read(f, birth); assert(retry.ok()); } released();
            }
            // Includes the actual UNSELECTED g3 slot's direct Birth read, not just current g4.
            assert(directOrdinals[0] && directOrdinals[1] > directOrdinals[0]);
            for (const auto ordinal : {1U, 3U, directOrdinals[0], directOrdinals[1], totalReads}) {
                inject(FileFault::none); afterRead = [&] { if (reads == ordinal) { cancelled->store(true); } };
                const auto result = read(f, birth); afterRead = {};
                assert(!result.ok() && !result.value && result.error == CustodyFileError::ioFailed && result.nativeError == ERROR_OPERATION_ABORTED);
                cancelled->store(false); released(); { const auto retry = read(f, birth); assert(retry.ok()); } released();
            }
            for (const auto fault : {FileFault::hashCreate, FileFault::allocation}) {
                inject(fault); const auto result = read(f, birth);
                assert(!result.ok() && !result.value && result.error ==
                    (fault == FileFault::hashCreate ? CustodyFileError::hashFailed : CustodyFileError::allocationFailed));
                assert(result.nativeError == 0);
                released(); inject(FileFault::none); { const auto retry = read(f, birth); assert(retry.ok()); } released();
            }
            inject(FileFault::none);
            assert(Pair::read(f.root, f.context, birth.transactionId, subject, f.service ? "" : "package-a", {}).error == CustodyFileError::invalidInput && !opens);
            cancelled->store(true); assert(read(f, birth).nativeError == ERROR_OPERATION_ABORTED && !opens); cancelled->store(false);
            auto wrong = f.context; wrong.role = CustodyRole::queue;
            assert(Pair::read(f.root, wrong, birth.transactionId, subject, f.service ? "" : "package-a", cancelled).error == CustodyFileError::invalidInput && !opens);
            assert(Pair::read(f.root, f.context, birth.transactionId, static_cast<CustodyMigrationSubject>(9), "", cancelled).error == CustodyFileError::invalidInput && !opens);
            assert(Pair::read(f.root, f.context, birth.transactionId, CustodyMigrationSubject::queue, "package-a", cancelled).error == CustodyFileError::invalidInput && !opens);
            assert(Pair::read(f.root, f.context, birth.transactionId, CustodyMigrationSubject::package, "../other", cancelled).error == CustodyFileError::invalidInput && !opens);
            assert(Pair::read(f.root, f.context, birth.transactionId, CustodyMigrationSubject::package, "", cancelled).error == CustodyFileError::invalidInput && !opens);
            { std::array<CustodyNativeJob, 4> jobs; for (const auto& job : jobs) assert(job);
                assert(read(f, birth).error == CustodyFileError::allocationFailed && !opens); }
            { std::array<CustodyPin, 32> pins; for (const auto& pin : pins) assert(pin);
                assert(read(f, birth).error == CustodyFileError::allocationFailed && !opens); }
            for (const auto spare : {std::size_t{0}, std::size_t{512}}) {
                CustodyAllocator<std::uint8_t> allocator; const auto count = CustodyOwnedMemory::limit - owned - spare;
                auto* pressure = allocator.allocate(count); inject(FileFault::none);
                const auto result = read(f, birth); assert(!result.ok() && !result.value && result.error == CustodyFileError::allocationFailed);
                assert(CustodyOwnedMemory::usedBytes() == owned + count); noEffects();
                allocator.deallocate(pressure, count); released(); { const auto retry = read(f, birth); assert(retry.ok()); } released();
            }
            wrong = f.context; wrong.storeId[0] ^= 1;
            assert(Pair::read(f.root, wrong, birth.transactionId, subject, f.service ? "" : "package-a", cancelled).error == CustodyFileError::identityMismatch);
            wrong = f.context; wrong.objectId[0] ^= 1;
            assert(Pair::read(f.root, wrong, birth.transactionId, subject, f.service ? "" : "package-a", cancelled).error == CustodyFileError::identityMismatch);
            auto transaction = birth.transactionId; transaction[0] ^= 1;
            assert(Pair::read(f.root, f.context, transaction, subject, f.service ? "" : "package-a", cancelled).error == CustodyFileError::invalidContent);
            inject(FileFault::none); released();
            // The result is independent of borrowed caller arguments/cancellation ownership.
            {
                auto callerCancel = std::make_shared<std::atomic<bool>>(false); auto context = f.context; auto txn = birth.transactionId;
                auto result = Pair::read(f.root, context, txn, subject, f.service ? "" : "package-a", callerCancel); assert(result.ok());
                auto retained = *result.value; result.value.reset(); callerCancel.reset(); context = {}; txn = {};
                assert(retained->current().transactionId == birth.transactionId && retained->slots()[0].generation == 3);
                const auto competing = CreateFileW(identityPath.c_str(), GENERIC_WRITE,
                    FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
                assert(competing == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
                retained.reset(); released();
            }
            std::printf("MIGRATION_PAIR_NATIVE schema=%u subject=%s allocations=%zu cancel_cuts=%zu direct_birth_reads=%u final_alloc_cancel=1 retry=1\n",
                schema, subject == CustodyMigrationSubject::queue ? "queue" : "package", allocations, allocations, 2U);
        }
    }
    inject(FileFault::none); assert(CustodyOwnedMemory::usedBytes() == before);
}
void migrationHistory() {
    const auto before = CustodyOwnedMemory::usedBytes();
    for (unsigned schema : {1U, 2U}) for (const auto subject : {CustodyMigrationSubject::queue, CustodyMigrationSubject::package}) {
        CustodyNativeJob job; assert(job);
        Fixture f(CustodyRole::migrationIntent, L"migration-intent");
        const std::string name = subject == CustodyMigrationSubject::queue ? "" : "package-a";
        if (!name.empty()) { f.service = false; assert(CreateDirectoryW((f.root / name).c_str(), &f.security)); }
        CustodyMigrationValue birth; birth.schema = schema; birth.context = f.context; birth.generation = 1;
        birth.subject = subject;
        if (!name.empty()) { birth.directory.emplace(); std::copy(name.begin(), name.end(), birth.directory->begin()); }
        birth.transactionId[0] = 42; birth.sourceCount = 1; birth.anchor.length = 3;
        birth.anchor.sha256.fill(7); birth.sources[0].length = 3; birth.sources[0].sha256 = birth.anchor.sha256;
        birth.sources[0].destinationObjectId[0] = 8;
        if (subject == CustodyMigrationSubject::package) {
            birth.anchor.objectId = CustodyId{}; birth.anchor.objectId->at(0) = 13; birth.anchor.generation = 2;
            birth.sourceCount = 2; birth.sources[0].kind = CustodyMigrationSourceKind::manifest;
            birth.sources[1] = birth.sources[0]; birth.sources[1].kind = CustodyMigrationSourceKind::media;
            birth.sources[1].length = 5; birth.sources[1].sha256.fill(9); birth.sources[1].destinationObjectId[0] = 10;
            if (schema == 2) {
                birth.sources[1].destinationPacked = true;
                birth.sources[1].destinationContainerId = CustodyId{}; birth.sources[1].destinationContainerId->at(0) = 19;
            }
        }
        auto bytes = writeCustodyMigration(birth, f.context, 1, birth.transactionId, subject, name); assert(bytes.ok());
        auto cipher = ProtectedCustodyCodec::sealBlock(f.context, 0, 17, *bytes.value); assert(cipher.ok());
        auto current = birth;
        const auto hash = custody_detail::digest(cipher.value->data(), cipher.value->size()); assert(hash);
        current.barrier = CustodyMigrationBarrier{f.context.objectId, 1, 17, cipher.value->size(), *hash};
        {
            auto files = f.open(CustodyFileAccess::createNew); assert(files.ok());
            const auto written = (*files.value)->writeBlock(0, 17, static_cast<std::uint32_t>(bytes.value->size()), *cipher.value); assert(written.ok());
            const CustodyIndex first{1, bytes.value->size(), {{17, *written.value, 0}}};
            publish(f, **files.value, 0, first); publish(f, **files.value, 1, first);
            for (std::uint64_t generation = 2; generation <= 4; ++generation) {
                current.generation = generation; current.stage = generation == 4 ? CustodyMigrationStage::switched : CustodyMigrationStage::copiedVerified;
                for (std::size_t i = 0; i < current.sourceCount; ++i) {
                    auto& s = current.sources[i]; s.destinationGeneration = generation;
                    s.destinationLength = s.length; s.destinationSha256 = s.sha256;
                    if (s.destinationPacked) {
                        s.destinationCommittedExtent = ProtectedPackedCustodyFormat::appendOffset+128;
                        s.destinationRootRef = ProtectedPackedCustodyFormat::encodeReference(
                            {PackedRecordKind::nodeL2, 128, ProtectedPackedCustodyFormat::appendOffset, generation, 0, {}});
                        assert(s.destinationRootRef);
                    }
                }
                const auto payload = writeCustodyMigration(current, f.context, generation, birth.transactionId, subject, name); assert(payload.ok());
                const auto envelope = ProtectedCustodyCodec::sealBlock(f.context, 0, generation+16, *payload.value); assert(envelope.ok());
                const auto saved = (*files.value)->writeBlock(0, generation+16, static_cast<std::uint32_t>(payload.value->size()), *envelope.value); assert(saved.ok());
                publish(f, **files.value, static_cast<unsigned>((generation-1)%2), CustodyIndex{generation, payload.value->size(), {{generation+16, *saved.value, 0}}});
            }
        }
        auto files = f.open(CustodyFileAccess::writeExisting); assert(files.ok()); // Exclusive identity lease, not a detached struct.
        const auto artifacts = writerArtifacts(f); inject(FileFault::none);
        const auto pair = (*files.value)->readValidatedMetadataPair(); assert(pair.ok());
        assert(pair.value->indices[0].generation == 3 && pair.value->indices[1].generation == 4);
        for (const auto& index : pair.value->indices) {
            const auto& entry = index.entries[0];
            auto envelope = (*files.value)->readBlock(0, entry.version, static_cast<std::uint32_t>(index.logicalLength), entry.envelopeBytes); assert(envelope.ok());
            auto plain = ProtectedCustodyCodec::openBlock(f.context, 0, entry.version, static_cast<std::uint32_t>(index.logicalLength), *envelope.value); assert(plain.ok());
            const auto parsed = readCustodyMigration({reinterpret_cast<const char*>(plain.value->data()), plain.value->size()}, f.context, index.generation, birth.transactionId, subject, name); assert(parsed.ok());
            auto historical = (*files.value)->readMigrationBirthEnvelope(17, static_cast<std::uint32_t>(cipher.value->size())); assert(historical.ok());
            const auto decoded = readCustodyMigrationBirth(*historical.value, f.context, *parsed.value, birth.transactionId, subject, name);
            assert(decoded.ok() && decoded.value->generation == 1 && decoded.value->stage == CustodyMigrationStage::prepared);
            assert(decoded.value->schema == schema && !decoded.value->barrier && !decoded.value->authorization);
            for (std::size_t i = 0; i < decoded.value->sourceCount; ++i) {
                const auto& source = decoded.value->sources[i];
                assert(!source.destinationGeneration && !source.destinationLength && !source.destinationSha256 &&
                    !source.destinationCommittedExtent && !source.destinationRootRef);
                assert(source.destinationPacked == birth.sources[i].destinationPacked && source.destinationContainerId == birth.sources[i].destinationContainerId);
            }
        } // Neither physical slot retains a g1 index; block version17 is not generation1.
        const auto check = [&](const CustodyMigrationValue& v, const CustodyBytes& e) {
            return readCustodyMigrationBirth(e, f.context, v, birth.transactionId, subject, name);
        };
        assert(check(current, *cipher.value).ok());
        auto reordered = current; if (reordered.sourceCount == 2) std::swap(reordered.sources[0], reordered.sources[1]);
        assert(check(reordered, *cipher.value).ok()); // Set equality, not array order or historical destination triples.
        for (unsigned fault = 0; fault < 17; ++fault) {
            auto bad = current;
            switch (fault) {
            case 0: bad.context.storeId[0] ^= 1; break;
            case 1: bad.context.objectId[0] ^= 1; break;
            case 2: bad.context.role = CustodyRole::queue; break;
            case 3: bad.transactionId[0] ^= 1; break;
            case 4: bad.subject = subject == CustodyMigrationSubject::queue ? CustodyMigrationSubject::package : CustodyMigrationSubject::queue; break;
            case 5: bad.barrier.reset(); break;
            case 6: bad.barrier->generation = 2; break;
            case 7: bad.barrier->blockVersion = 18; break;
            case 8: --bad.barrier->envelopeBytes; break;
            case 9: bad.barrier->sha256[0] ^= 1; break;
            case 10: bad.anchor.length++; break;
            case 11: bad.anchor.sha256[0] ^= 1; break;
            case 12: bad.sources[0].destinationObjectId[0] ^= 1; break;
            case 13: bad.sourceCount = 0; break;
            case 14: bad.barrier->objectId[0] ^= 1; break;
            case 15: bad.directory.emplace(); bad.directory->at(0) = 'x'; break;
            case 16: bad.generation = 1; break;
            }
            assert(!check(bad, *cipher.value).ok());
        }
        auto wrongTransaction = birth.transactionId; wrongTransaction[0] ^= 1;
        assert(!readCustodyMigrationBirth(*cipher.value, f.context, current, wrongTransaction, subject, name).ok());
        assert(!readCustodyMigrationBirth(*cipher.value, f.context, current, birth.transactionId, subject, "other").ok());
        if (subject == CustodyMigrationSubject::package) {
            for (unsigned fault = 0; fault < 8; ++fault) {
                auto bad = current;
                switch (fault) {
                case 0: bad.anchor.objectId->at(0) ^= 1; break;
                case 1: ++*bad.anchor.generation; break;
                case 2: bad.sources[0].kind = CustodyMigrationSourceKind::canonical; break;
                case 3: ++bad.sources[0].length; ++*bad.sources[0].destinationLength; break;
                case 4: bad.sources[0].sha256[0] ^= 1; bad.sources[0].destinationSha256 = bad.sources[0].sha256; break;
                case 5: bad.sourceCount = 1; break;
                case 6: bad.sources[1].kind = bad.sources[0].kind; break;
                case 7: bad.sources[2] = bad.sources[0]; bad.sources[2].kind = CustodyMigrationSourceKind::playback; bad.sourceCount = 3; break;
                }
                assert(!check(bad, *cipher.value).ok());
            }
        }
        // Re-protect semantic tampering with genuine DPAPI, refresh cipher ref,
        // and require strict birth rejection (not merely an envelope hash error).
        const std::string json(bytes.value->begin(), bytes.value->end());
        for (const auto& change : std::array<std::pair<std::string, std::string>, 12>{{
            {schema == 1 ? "migration.v1" : "migration.v2", schema == 1 ? "migration.v2" : "migration.v1"}, {"\"generation\":1", "\"generation\":2"},
            {"\"stage\":\"prepared\"", "\"stage\":\"copied_verified\""},
            {"\"barrier\":null", "\"barrier\":{}"}, {"\"cleanup_authorization\":null", "\"cleanup_authorization\":{}"},
            {"\"destination_generation\":null", "\"destination_generation\":1"},
            {"\"destination_length\":null", "\"destination_length\":3"},
            {"\"destination_sha256\":null", "\"destination_sha256\":\"bad\""},
            {"\"source_length\":3", "\"source_length\":4"},
            {"\"source_length\":3", "\"source_length\":3,\"source_length\":3"},
            {"\"source_length\":3", "\"alias_length\":3"}, {"\"schema\":", "\"unknown\":0,\"schema\":"}
        }}) {
            auto malformed = json; const auto at = malformed.find(change.first); assert(at != std::string::npos);
            malformed.replace(at, change.first.size(), change.second);
            auto protectedBad = ProtectedCustodyCodec::sealBlock(f.context, 0, 17, CustodyBytes(malformed.begin(), malformed.end())); assert(protectedBad.ok());
            auto expected = current; expected.barrier->envelopeBytes = protectedBad.value->size();
            const auto digest = custody_detail::digest(protectedBad.value->data(), protectedBad.value->size()); assert(digest); expected.barrier->sha256 = *digest;
            assert(check(expected, *protectedBad.value).error == CustodyCodecError::invalidPlaintext);
        }
        // Structurally VALID but foreign immutable birth facts: seal with genuine
        // DPAPI and refresh the exact cipher receipt, so rejection is semantic.
        const auto compareProtectedBirth = [&](const CustodyMigrationValue& changedBirth, bool expected = false) {
            const auto payload = writeCustodyMigration(changedBirth, f.context, 1, birth.transactionId, subject, name); assert(payload.ok());
            const auto envelope = ProtectedCustodyCodec::sealBlock(f.context, 0, 17, *payload.value); assert(envelope.ok());
            auto receipt = current; receipt.barrier->envelopeBytes = envelope.value->size();
            const auto hash = custody_detail::digest(envelope.value->data(), envelope.value->size()); assert(hash); receipt.barrier->sha256 = *hash;
            const auto decoded = check(receipt, *envelope.value);
            assert(decoded.ok() == expected);
            if (!expected) assert(!decoded.value && decoded.error == CustodyCodecError::invalidPlaintext);
        };
        compareProtectedBirth(birth, true);
        for (unsigned fault = 0; fault < 5; ++fault) {
            auto changed = birth;
            if (fault == 0) {
                changed.schema = schema == 1 ? 2 : 1;
                if (changed.schema == 1) for (std::size_t i = 0; i < changed.sourceCount; ++i) {
                    auto& s = changed.sources[i]; s.destinationPacked = false; s.destinationContainerId.reset();
                }
            }
            if (fault == 1) {
                ++changed.anchor.length;
                if (subject == CustodyMigrationSubject::queue) changed.sources[0].length = changed.anchor.length;
            }
            if (fault == 2) {
                changed.anchor.sha256[0] ^= 1;
                if (subject == CustodyMigrationSubject::queue) changed.sources[0].sha256 = changed.anchor.sha256;
            }
            if (fault == 3) changed.sources[0].destinationObjectId[0] ^= 1;
            if (fault == 4) {
                changed.anchor.objectId = CustodyId{}; changed.anchor.objectId->at(0) = 77; changed.anchor.generation = 7;
            }
            compareProtectedBirth(changed);
        }
        if (subject == CustodyMigrationSubject::package) {
            for (unsigned fault = 0; fault < (schema == 2 ? 8U : 6U); ++fault) {
                auto changed = birth;
                if (fault == 0) ++*changed.anchor.generation;
                if (fault == 1) ++changed.sources[1].length;
                if (fault == 2) changed.sources[1].sha256[0] ^= 1;
                if (fault == 3) changed.sources[1].kind = CustodyMigrationSourceKind::canonical;
                if (fault == 4) {
                    changed.sources[2] = changed.sources[0]; changed.sources[2].kind = CustodyMigrationSourceKind::recovery; changed.sourceCount = 3;
                }
                if (fault == 5) changed.sourceCount = 1;
                if (fault == 6) { changed.sources[1].destinationPacked = false; changed.sources[1].destinationContainerId.reset(); }
                if (fault == 7) changed.sources[1].destinationContainerId->at(0) ^= 1;
                compareProtectedBirth(changed);
            }
            if (schema == 2) {
                auto changedStamp = current; auto& s = changedStamp.sources[1];
                s.destinationGeneration = 8; s.destinationCommittedExtent = ProtectedPackedCustodyFormat::appendOffset+256;
                s.destinationRootRef = ProtectedPackedCustodyFormat::encodeReference(
                    {PackedRecordKind::nodeL2, 128, ProtectedPackedCustodyFormat::appendOffset+128, 8, 0, {}});
                assert(s.destinationRootRef && check(changedStamp, *cipher.value).ok());
                // Current sealed stamps need not equal null prepared birth stamps.
            }
        }
        auto damaged = *cipher.value; damaged.back() ^= 1;
        assert(check(current, damaged).error == CustodyCodecError::invalidEnvelope);
        auto expected = current; const auto damagedHash = custody_detail::digest(damaged.data(), damaged.size()); assert(damagedHash); expected.barrier->sha256 = *damagedHash;
        assert(check(expected, damaged).error == CustodyCodecError::nativeFailed);
        for (const auto bounds : {std::pair<std::uint64_t, std::uint32_t>{0, 17}, {17, 0}, {17, 16}, {17, 69633}}) {
            inject(FileFault::none); const auto calls = writerIoCounts();
            assert((*files.value)->readMigrationBirthEnvelope(bounds.first, bounds.second).error == CustodyFileError::invalidInput);
            assert(writerIoCounts() == calls);
        }
        inject(FileFault::none);
        assert((*files.value)->readMigrationBirthEnvelope(99, static_cast<std::uint32_t>(cipher.value->size())).error == CustodyFileError::ioFailed);
        assert((*files.value)->readMigrationBirthEnvelope(17, static_cast<std::uint32_t>(cipher.value->size()-1)).error == CustodyFileError::invalidContent);
        for (const auto selected : {FileFault::readFailed, FileFault::hashCreate, FileFault::allocation}) {
            inject(selected); const auto refused = (*files.value)->readMigrationBirthEnvelope(17, static_cast<std::uint32_t>(cipher.value->size()));
            assert(!refused.ok());
            assert(refused.error == (selected == FileFault::readFailed ? CustodyFileError::ioFailed : selected == FileFault::hashCreate ? CustodyFileError::hashFailed : CustodyFileError::allocationFailed));
            assert(selected != FileFault::readFailed || refused.nativeError == ERROR_READ_FAULT);
            assert(writerArtifacts(f) == artifacts && !writes && !flushes && !renames);
        }
        inject(FileFault::none);
        {
            CustodyBytes pressure; pressure.reserve(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
            assert((*files.value)->readMigrationBirthEnvelope(17, static_cast<std::uint32_t>(cipher.value->size())).error == CustodyFileError::allocationFailed);
            assert(check(current, *cipher.value).error == CustodyCodecError::allocationFailed);
        }
        assert(check(current, *cipher.value).ok());
        {
            inject(FileFault::none);
            const auto held = CustodyOwnedMemory::usedBytes();
            const auto identityPath = f.object() / L"id.bin";
            const auto leaseStillHeld = [&] {
                const auto competing = CreateFileW(identityPath.c_str(), GENERIC_WRITE,
                    FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
                assert(competing == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
            };
            const auto invoke = [&](std::size_t failAt) {
                queueAllocation = {true, false, 0, failAt, 0, nullptr, nullptr, nullptr, true};
                auto decoded = check(current, *cipher.value);
                queueAllocation.active = false;
                return decoded;
            };
            auto counted = invoke(0); assert(counted.ok());
            const auto allocations = queueAllocation.calls; assert(allocations > 0);
            assert(CustodyOwnedMemory::usedBytes() == held);
            for (std::size_t ordinal = 1; ordinal <= allocations; ++ordinal) {
                const auto refused = invoke(ordinal);
                assert(queueAllocation.hit && !refused.ok() && !refused.value && refused.error == CustodyCodecError::allocationFailed);
                assert(CustodyOwnedMemory::usedBytes() == held);
                leaseStillHeld(); // The FIXTURE/caller, not Birth, owns this lease.
                const auto retry = invoke(0); assert(retry.ok() && retry.value->schema == schema);
                assert(CustodyOwnedMemory::usedBytes() == held);
            }
            const auto invokeEnvelope = [&](std::size_t failAt) {
                queueAllocation = {true, false, 0, failAt, 0, nullptr, nullptr, nullptr, true};
                auto envelope = (*files.value)->readMigrationBirthEnvelope(17, static_cast<std::uint32_t>(cipher.value->size()));
                queueAllocation.active = false;
                return envelope;
            };
            auto countedEnvelope = invokeEnvelope(0); assert(countedEnvelope.ok());
            const auto envelopeAllocations = queueAllocation.calls; assert(envelopeAllocations > 0);
            countedEnvelope.value.reset(); assert(CustodyOwnedMemory::usedBytes() == held);
            for (std::size_t ordinal = 1; ordinal <= envelopeAllocations; ++ordinal) {
                const auto refused = invokeEnvelope(ordinal);
                assert(queueAllocation.hit && !refused.ok() && !refused.value && refused.error == CustodyFileError::allocationFailed);
                assert(CustodyOwnedMemory::usedBytes() == held); leaseStillHeld();
                auto retry = invokeEnvelope(0); assert(retry.ok()); retry.value.reset(); assert(CustodyOwnedMemory::usedBytes() == held);
            }
            assert(!writes && !flushes && !renames && writerArtifacts(f) == artifacts);
            inject(FileFault::hashCreate);
            const auto hashFailed = check(current, *cipher.value);
            assert(!hashFailed.ok() && !hashFailed.value && hashFailed.error == CustodyCodecError::hashFailed && hashFailed.nativeError == 0);
            assert(CustodyOwnedMemory::usedBytes() == held);
            inject(FileFault::none); assert(check(current, *cipher.value).ok());
            std::printf("MIGRATION_BIRTH_NATIVE schema=%u subject=%s current=3,4 birth=1 block_version=17 allocation_cuts=%zu envelope_cuts=%zu retry=1\n",
                schema, subject == CustodyMigrationSubject::queue ? "queue" : "package", allocations, envelopeAllocations);
        }
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        const auto workerRead = [&] {
            if (cancelled->load()) return false;
            auto envelope = (*files.value)->readMigrationBirthEnvelope(17, static_cast<std::uint32_t>(cipher.value->size()));
            if (cancelled->load() || !envelope.ok()) return false;
            return check(current, *envelope.value).ok() && !cancelled->load();
        }; // Test compound caller, NOT Birth cancellation or a production migration owner.
        afterRead = [&] {
            std::array<CustodyNativeJob, 3> remaining; for (const auto& admitted : remaining) assert(admitted);
            CustodyNativeJob overflow; assert(!overflow);
            const auto competing = CreateFileW((f.object() / L"id.bin").c_str(), GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
            assert(competing == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
            cancelled->store(true);
        };
        assert(!workerRead()); afterRead = {}; cancelled->store(false); assert(workerRead());
        cancelled->store(true); const auto calls = writerIoCounts(); assert(!workerRead() && writerIoCounts() == calls);
        assert(!writes && !flushes && !renames && writerArtifacts(f) == artifacts);
        const auto alias = f.object() / L"birth-alias";
        files.value.reset(); // Construct hostile artifacts only after the real directory lease closes.
        assert(CreateHardLinkW(alias.c_str(), (f.object() / L"block.0.17").c_str(), nullptr));
        files = f.open(CustodyFileAccess::writeExisting); assert(files.ok());
        assert((*files.value)->readMigrationBirthEnvelope(17, static_cast<std::uint32_t>(cipher.value->size())).error == CustodyFileError::unsafeFile);
        files.value.reset();
        assert(DeleteFileW(alias.c_str())); // Only the generated test hardlink.
        junction(f.object() / L"block.0.99", f.root, f.security);
        files = f.open(CustodyFileAccess::writeExisting); assert(files.ok());
        const auto reparse = (*files.value)->readMigrationBirthEnvelope(99, static_cast<std::uint32_t>(cipher.value->size()));
        assert(!reparse.ok() && (reparse.error == CustodyFileError::unsafeFile || reparse.error == CustodyFileError::ioFailed));
        inject(FileFault::none);
    }
    {
        Fixture f; auto files = f.open(CustodyFileAccess::createNew); assert(files.ok());
        inject(FileFault::none); const auto calls = writerIoCounts();
        assert((*files.value)->readMigrationBirthEnvelope(17, 17).error == CustodyFileError::invalidInput);
        assert(writerIoCounts() == calls);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}

void protectedQueueCandidate() {
    using Candidate = ProtectedUploadQueueCandidate;
    static_assert(!std::is_default_constructible_v<Candidate> && !std::is_copy_constructible_v<Candidate>);
    static_assert(std::is_same_v<decltype(std::declval<const Candidate&>().items()), const CustodyVector<Candidate::Item>&>);
    static_assert(std::is_same_v<decltype(Candidate::Item::packageDirectory), CustodyString>);
    const auto before = CustodyOwnedMemory::usedBytes();
    {
        Fixture f(CustodyRole::bootstrap, L"bootstrap");
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        auto queue = f.context; queue.role = CustodyRole::queue; queue.objectId[0] = 31;
        // Synthetic logical data; path text is NOT filesystem/effect authority.
        const std::string json = R"({"schema_version":"desktop-upload-queue.v3","items":[{"local_recording_id":"recording-a","directory_id":"directory-a","session_id":"session-a","package_directory":"C:\\synthetic\\recording-a","status":1,"accepted_bytes":[2,4,6],"attempts":3,"safe_reason":"upload_interrupted","owner_user_id":"","owner_workspace_id":""}],"updated_at_ms":17,"deletion_operations":[],"purge_acknowledgements":[]})";
        const CustodyBytes payload(json.begin(), json.end());
        assert(commitProtectedCustodyMetadata(f.root, "", queue, 0, payload, cancelled).state == CustodyCommitState::committed);
        CustodyBootstrapValue bootstrap; bootstrap.context = f.context; bootstrap.generation = 1; bootstrap.queueObjectId = queue.objectId;
        auto encoded = writeCustodyBootstrap(bootstrap, f.context, 1, queue.objectId); assert(encoded.ok());
        assert(commitProtectedCustodyMetadata(f.root, "", f.context, 0, *encoded.value, cancelled).state == CustodyCommitState::committed);
        auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        auto input = ProtectedCustodyQueueInput::read(*parent.value, cancelled); assert(input.ok());
        inject(FileFault::none);
        auto result = ProtectedUploadQueueCandidate::read(*input.value, cancelled);
        if (!result.ok()) std::fprintf(stderr, "logical-queue error=%u native=%u\n", static_cast<unsigned>(result.error), result.nativeError);
        assert(result.ok()); // RED: genuine input, not compile-only missing API.
        assert(result.value->get()->items().size() == 1);
        const auto& item = result.value->get()->items()[0];
        assert(std::string_view(item.localRecordingId) == "recording-a");
        assert(item.status == UploadQueueStatus::uploading && item.attempts == 3);
        assert((item.acceptedBytes == std::array<std::uint64_t,3>{2,4,6}));
        assert(result.value->get()->updatedAtMs() == 17 && !result.value->get()->legacy());
        assert(!writes && !reads && !opens && !flushes && !renames);
    }
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    const auto replace = [](std::string json, std::string_view from, std::string_view to) {
        const auto at = json.find(from); assert(at != std::string::npos);
        json.replace(at, from.size(), to); return json;
    };
    const auto text = [](const CustodyBytes& bytes) {
        return std::string_view(reinterpret_cast<const char*>(bytes.data()), bytes.size());
    };
    const std::string item = R"({"local_recording_id":"recording-a","directory_id":"directory-a","session_id":"session-a","package_directory":"C:\\synthetic\\\u043f\u0430\u043f\u043a\u0430-\ud83d\ude00","status":4,"accepted_bytes":[18446744073709551615,4,6],"attempts":4294967295,"safe_reason":"upload_interrupted","owner_user_id":"11111111-1111-4111-8111-111111111111","owner_workspace_id":"22222222-2222-4222-8222-222222222222","meeting_id":"meeting-a","media_revision_id":"revision-a","upload_session_id":"upload-a","server_status":"uploaded","processing_status":"processing","media_revision_status":"accepted","updated_at_ms":123})";
    const std::string operation = R"({"operation_id":"33333333-3333-4333-8333-333333333333","target":"meeting","target_id":"44444444-4444-4444-8444-444444444444","actor_user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","server_origin":"https:\/\/example.test","phase":3,"requested_at_ms":100,"updated_at_ms":200,"attempts":3,"next_attempt_at_ms":300,"receipt_request_id":"55555555-5555-4555-8555-555555555555","safe_reason":"accepted"})";
    const std::string ack = R"({"task_id":"66666666-6666-4666-8666-666666666666","meeting_id":"44444444-4444-4444-8444-444444444444","acknowledged_at_ms":900})";
    const auto ledger = [&](std::string_view rows, std::string_view operations, std::string_view acks) {
        return std::string(R"({"schema_version":"desktop-upload-queue.v3","items":[)") + std::string(rows) +
            R"(],"updated_at_ms":17,"deletion_operations":[)" + std::string(operations) +
            R"(],"purge_acknowledgements":[)" + std::string(acks) + "]}";
    };
    const auto full = ledger(item, operation, ack);
    const auto v2 = std::string(R"({"schema_version":"desktop-upload-queue.v2","items":[)") + item + "]}";
    const auto setup = [&](Fixture& f, std::initializer_list<std::string_view> documents) {
        auto queue = f.context; queue.role = CustodyRole::queue; queue.objectId[0] = 31;
        std::uint64_t generation = 0;
        for (const auto json : documents) {
            const CustodyBytes bytes(json.begin(), json.end());
            assert(commitProtectedCustodyMetadata(f.root, "", queue, generation, bytes, cancelled).state == CustodyCommitState::committed);
            ++generation;
        }
        CustodyBootstrapValue bootstrap; bootstrap.context = f.context; bootstrap.generation = 1; bootstrap.queueObjectId = queue.objectId;
        auto bytes = writeCustodyBootstrap(bootstrap, f.context, 1, queue.objectId); assert(bytes.ok());
        assert(commitProtectedCustodyMetadata(f.root, "", f.context, 0, *bytes.value, cancelled).state == CustodyCommitState::committed);
        return queue;
    };
    const auto readInput = [&](Fixture& f) {
        auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        auto input = ProtectedCustodyQueueInput::read(*parent.value, cancelled); assert(input.ok());
        return input; // Genuine parent/leases are held by input after this local reset.
    };
    const auto artifacts = [](const Fixture& f) {
        std::vector<std::pair<std::filesystem::path, std::string>> result;
        for (const auto& directory : {f.object(), f.root / L".custody-v1" / L"queue"}) {
            for (const auto& entry : std::filesystem::directory_iterator(directory)) {
                std::ifstream stream(entry.path(), std::ios::binary); assert(stream);
                const std::string bytes(std::istreambuf_iterator<char>(stream), {});
                result.emplace_back(entry.path(), sha256(bytes));
            }
        }
        std::sort(result.begin(), result.end()); return result;
    };
    const auto assertFull = [](const Candidate& value) {
        assert(value.items().size() == 1 && value.deletionOperations().size() == 1 && value.purgeAcknowledgements().size() == 1);
        const auto& row = value.items()[0];
        assert(std::string_view(row.localRecordingId) == "recording-a" && std::string_view(row.directoryId) == "directory-a");
        assert(std::string_view(row.sessionId) == "session-a" && row.status == UploadQueueStatus::uploaded);
        assert((row.acceptedBytes == std::array<std::uint64_t, 3>{std::numeric_limits<std::uint64_t>::max(), 4, 6}));
        assert(row.attempts == std::numeric_limits<std::uint32_t>::max() && row.updatedAtMs == 123);
        assert(std::string_view(row.packageDirectory) == "C:\\synthetic\\\xd0\xbf\xd0\xb0\xd0\xbf\xd0\xba\xd0\xb0-\xf0\x9f\x98\x80");
        assert(std::string_view(row.safeReason) == "upload_interrupted");
        assert(std::string_view(row.ownerUserId) == "11111111-1111-4111-8111-111111111111");
        assert(std::string_view(row.ownerWorkspaceId) == "22222222-2222-4222-8222-222222222222");
        assert(std::string_view(row.meetingId) == "meeting-a" && std::string_view(row.mediaRevisionId) == "revision-a");
        assert(std::string_view(row.uploadSessionId) == "upload-a" && std::string_view(row.serverStatus) == "uploaded");
        assert(std::string_view(row.processingStatus) == "processing" && std::string_view(row.mediaRevisionStatus) == "accepted");
        const auto& op = value.deletionOperations()[0];
        assert(std::string_view(op.operationId) == "33333333-3333-4333-8333-333333333333" && op.target == DeletionTarget::meeting);
        assert(std::string_view(op.targetId) == "44444444-4444-4444-8444-444444444444");
        assert(std::string_view(op.actorUserId) == std::string_view(row.ownerUserId) && std::string_view(op.workspaceId) == std::string_view(row.ownerWorkspaceId));
        assert(std::string_view(op.serverOrigin) == "https://example.test" && op.phase == DeletionOperationPhase::accepted);
        assert(op.requestedAtMs == 100 && op.updatedAtMs == 200 && op.attemptCount == 3 && op.nextAttemptAtMs == 300);
        assert(std::string_view(op.receiptRequestId) == "55555555-5555-4555-8555-555555555555" && std::string_view(op.safeReason) == "accepted");
        const auto& a = value.purgeAcknowledgements()[0];
        assert(std::string_view(a.taskId) == "66666666-6666-4666-8666-666666666666");
        assert(std::string_view(a.meetingId) == std::string_view(op.targetId) && a.acknowledgedAtMs == 900);
        assert(value.updatedAtMs() == 17 && !value.legacy());
    };
    const auto check = [&](std::string_view json, bool valid, std::string_view omitted = {}) {
        const auto baseline = CustodyOwnedMemory::usedBytes();
        {
            Fixture f(CustodyRole::bootstrap, L"bootstrap"); setup(f, {json});
            auto input = readInput(f); const auto held = CustodyOwnedMemory::usedBytes();
            const auto snapshot = artifacts(f); inject(FileFault::none);
            auto result = Candidate::read(*input.value, cancelled);
            assert(result.ok() == valid);
            if (!valid) assert(!result.value && result.error == CustodyFileError::invalidContent && result.nativeError != ERROR_OPERATION_ABORTED);
            else {
                assert(result.value->get()->input() == *input.value);
                const auto& row = result.value->get()->items()[0];
                if (omitted == "updated_at_ms") assert(row.updatedAtMs == 0);
                for (const auto& field : std::array<std::pair<std::string_view, const CustodyString*>, 6>{{
                    {"meeting_id", &row.meetingId}, {"media_revision_id", &row.mediaRevisionId}, {"upload_session_id", &row.uploadSessionId},
                    {"server_status", &row.serverStatus}, {"processing_status", &row.processingStatus}, {"media_revision_status", &row.mediaRevisionStatus}}})
                    if (field.first == omitted) assert(field.second->empty());
            }
            assert(writerIoCounts() == (std::array<unsigned, 8>{}));
            assert(text(input.value->get()->payloads()[0]) == json && text(input.value->get()->payloads()[1]) == json);
            result.value.reset(); assert(CustodyOwnedMemory::usedBytes() == held && artifacts(f) == snapshot);
        }
        assert(CustodyOwnedMemory::usedBytes() == baseline);
    };
    assert(Candidate::read({}, cancelled).error == CustodyFileError::invalidInput);
    const auto g1 = replace(full, "\"updated_at_ms\":17", "\"updated_at_ms\":11");
    const auto g2 = replace(full, "\"updated_at_ms\":17", "\"updated_at_ms\":22");
    const auto g3 = replace(full, "\"updated_at_ms\":17", "\"updated_at_ms\":33");
    for (const auto generation : {1U, 2U, 3U}) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap");
        const auto queue = generation == 1 ? setup(f, {g1}) : generation == 2 ? setup(f, {g1, g2}) : setup(f, {g1, g2, g3});
        auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        auto input = ProtectedCustodyQueueInput::read(*parent.value, cancelled); assert(input.ok());
        const auto* genuine = input.value->get(); const auto held = CustodyOwnedMemory::usedBytes();
        const auto snapshot = artifacts(f); inject(FileFault::none);
        auto result = Candidate::read(*input.value, cancelled); assert(result.ok());
        const auto& value = **result.value; const auto& retained = *value.input();
        assert(&retained == genuine && value.updatedAtMs() == generation * 11);
        assert(retained.context().storeId == queue.storeId && retained.context().objectId == queue.objectId && retained.context().role == CustodyRole::queue);
        assert(retained.indices().selectedSlot == (generation == 2 ? 1U : 0U));
        assert(retained.indices().indices[0].generation == (generation == 3 ? 3U : 1U));
        assert(retained.indices().indices[1].generation == (generation == 1 ? 1U : 2U));
        assert(text(retained.payloads()[0]) == (generation == 3 ? g3 : g1));
        assert(text(retained.payloads()[1]) == (generation == 1 ? g1 : g2));
        assert(writerIoCounts() == (std::array<unsigned, 8>{}));
        result.value.reset(); assert(CustodyOwnedMemory::usedBytes() == held);
        result = Candidate::read(*input.value, cancelled); assert(result.ok());
        auto last = *result.value;
        input.value.reset(); parent.value.reset(); result.value.reset();
        assert(last->input().get() == genuine && last->items().size() == 1);
        assert(!ProtectedCustodyFiles::open(f.root, "", queue, CustodyFileAccess::writeExisting).ok());
        assert(!f.open(CustodyFileAccess::writeExisting).ok());
        assert(artifacts(f) == snapshot);
        last.reset();
        assert(ProtectedCustodyFiles::open(f.root, "", queue, CustodyFileAccess::writeExisting).ok());
        assert(f.open(CustodyFileAccess::writeExisting).ok());
    }
    // Logical malformed peer, with genuine DPAPI/index/hash validation already
    // successful. Both selected slots and either bad peer must reject all data.
    for (const bool third : {false, true}) for (const bool badSelected : {false, true}) for (const bool badLegacy : {false, true}) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap");
        const auto malformed = (badLegacy ? v2 : full) + " trailing";
        const auto& previous = badSelected ? full : malformed;
        const auto& current = badSelected ? malformed : full;
        if (third) setup(f, {g1, previous, current}); else setup(f, {previous, current});
        auto input = readInput(f); const auto held = CustodyOwnedMemory::usedBytes();
        const auto snapshot = artifacts(f); inject(FileFault::none);
        const auto result = Candidate::read(*input.value, cancelled);
        assert(!result.ok() && !result.value && result.error == CustodyFileError::invalidContent);
        assert(CustodyOwnedMemory::usedBytes() == held && writerIoCounts() == (std::array<unsigned, 8>{}));
        assert(text(input.value->get()->payloads()[third ? 0 : 1]) == current);
        assert(text(input.value->get()->payloads()[third ? 1 : 0]) == previous && artifacts(f) == snapshot);
    }
    {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); setup(f, {full});
        auto input = readInput(f); auto result = Candidate::read(*input.value, cancelled); assert(result.ok()); assertFull(**result.value);
    }
    for (const bool legacySelected : {false, true}) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap");
        if (legacySelected) setup(f, {full, v2}); else setup(f, {v2, full});
        auto input = readInput(f); const auto snapshot = artifacts(f); inject(FileFault::none);
        auto result = Candidate::read(*input.value, cancelled); assert(result.ok());
        assert(result.value->get()->legacy() == legacySelected);
        assert(result.value->get()->items()[0].updatedAtMs == 123 && result.value->get()->items()[0].attempts == 4294967295U);
        if (legacySelected) assert(result.value->get()->updatedAtMs() == 0 && result.value->get()->deletionOperations().empty() && result.value->get()->purgeAcknowledgements().empty());
        else assertFull(**result.value);
        assert(writerIoCounts() == (std::array<unsigned, 8>{}) && artifacts(f) == snapshot);
    }
    for (const bool legacy : {false, true}) {
        const std::string minimal = R"({"local_recording_id":"minimal","directory_id":"directory","session_id":"session","package_directory":"../unadmitted","status":1,"accepted_bytes":[0,0,0],"attempts":0,"safe_reason":""})";
        const auto json = legacy ? std::string(R"({"schema_version":"desktop-upload-queue.v2","items":[)") + minimal + "]}" : ledger(minimal, "", "");
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); setup(f, {json});
        auto input = readInput(f); const auto snapshot = artifacts(f); inject(FileFault::none);
        auto result = Candidate::read(*input.value, cancelled); assert(result.ok());
        const auto& row = result.value->get()->items()[0];
        assert(row.status == UploadQueueStatus::uploading && row.safeReason.empty() && !row.attempts && !row.updatedAtMs);
        assert(row.ownerUserId.empty() && row.ownerWorkspaceId.empty() && row.meetingId.empty() && row.mediaRevisionId.empty() && row.uploadSessionId.empty());
        assert(row.serverStatus.empty() && row.processingStatus.empty() && row.mediaRevisionStatus.empty());
        assert(result.value->get()->legacy() == legacy && result.value->get()->deletionOperations().empty() && result.value->get()->purgeAcknowledgements().empty());
        assert(writerIoCounts() == (std::array<unsigned, 8>{}) && artifacts(f) == snapshot);
    }
    // Preserve legacy optional omission and nested extensions; this is not a
    // closed metadata schema. Escaped owner UUIDs remain raw-ASCII invalid.
    for (const auto key : {"meeting_id", "media_revision_id", "upload_session_id", "server_status", "processing_status", "media_revision_status", "updated_at_ms"}) {
        const auto begin = item.find(std::string("\"") + key + "\":"); assert(begin != std::string::npos);
        const auto end = item.find(',', begin);
        const auto token = item.substr(begin, (end == std::string::npos ? item.size()-1 : end) - begin);
        check(ledger(replace(item, token, "\"extra\":{" + token + "}"), operation, ack), true, key);
        for (const auto invalid : {"null", "{}", "-1"})
            check(ledger(replace(item, token, std::string("\"") + key + "\":" + invalid), operation, ack), false);
    }
    for (const auto& change : std::initializer_list<std::pair<std::string, std::string>>{
        {"\"status\":4", "\"status\":7"}, {"\"attempts\":4294967295", "\"attempts\":4294967296"},
        {"[18446744073709551615,4,6]", "[18446744073709551616,4,6]"}, {"[18446744073709551615,4,6]", "[1,2]"},
        {"[18446744073709551615,4,6]", "[1,2,3,4]"}, {"[18446744073709551615,4,6]", "[1,-2,3]"},
        {"\"local_recording_id\":\"recording-a\"", "\"local_recording_id\":\"recording-a\",\"local_recording_id\":\"other\""},
        {"\"owner_user_id\":\"11111111", "\"owner_user_id\":\"\\u00311111111"},
        {"\"owner_workspace_id\":\"22222222-2222-4222-8222-222222222222\"", "\"owner_workspace_id\":\"\""},
        {"\"receipt_request_id\":\"55555555-5555-4555-8555-555555555555\"", "\"receipt_request_id\":\"\""},
        {"\"next_attempt_at_ms\":300", "\"next_attempt_at_ms\":199"},
        {"\"updated_at_ms\":200", "\"updated_at_ms\":99"},
        {"\"server_origin\":\"https:\\/\\/example.test\"", "\"server_origin\":\"https://example.test/path\""},
        {"\"task_id\":\"66666666-6666-4666-8666-666666666666\"", "\"task_id\":null"},
        {"\"acknowledged_at_ms\":900", "\"acknowledged_at_ms\":1.5"},
        {"],\"updated_at_ms\":17", "],\"updated_at_ms\":-1"},
        {"],\"updated_at_ms\":17", "],\"updated_at_ms\":1e0"},
        {"],\"updated_at_ms\":17", "],\"updated_at_ms\":1234567890123456789"},
        {"],\"updated_at_ms\":17", "],\"updated_at_ms\":"}}) check(replace(full, change.first, change.second), false);
    check(full.substr(0, full.find("],\"updated_at_ms\":17") + std::string_view("],\"updated_at_ms\":17").size()), false);
    check(ledger(item + ',' + item, operation, ack), false);
    check(ledger(item, operation + ',' + operation, ack), false);
    check(ledger(item, operation, ack + ',' + ack), false);
    check(replace(full, "],\"updated_at_ms\":17", "],\"updated_at_ms\":17,\"updated_at_ms\":17"), false);
    check(replace(full, "\"purge_acknowledgements\":[", "\"deletion_operations\":[],\"purge_acknowledgements\":["), false);
    check(ledger(replace(item, "\"local_recording_id\":\"recording-a\"", R"("extra":{"local_recording_id":"recording-a"})"), operation, ack), false);
    check(ledger(replace(item, "\"local_recording_id\":\"recording-a\"", R"("local_recording_id":"\u0072ecording-a")"), operation, ack), true);
    for (const auto escaped : {R"(\n)", R"(\r)", R"(\t)", R"(\u0000)", R"(\ud800)", R"(\udc00)", R"(\q)"})
        check(ledger(replace(item, R"(\u043f\u0430\u043f\u043a\u0430-\ud83d\ude00)", escaped), operation, ack), false);
    for (const auto& path : {std::string(4097, 'a'), std::string("\xc0\xaf"), std::string("raw\nnewline")})
        check(ledger(replace(item, R"(\u043f\u0430\u043f\u043a\u0430-\ud83d\ude00)", path), operation, ack), false);
    check(ledger(replace(item, R"(C:\\synthetic\\\u043f\u0430\u043f\u043a\u0430-\ud83d\ude00)", "../outside"), operation, ack), true);
    check(replace(full, "\"updated_at_ms\":17", "\"updated_at_ms\":999999999999999999"), true);
    for (const bool legacy : {false, true}) {
        // Compare the same v2/v3 fixture with the existing std aliases. The path
        // belongs to this generated root so legacy load does not quarantine it.
        Fixture f(CustodyRole::bootstrap, L"bootstrap");
        const auto package = f.root / L"package";
        const auto parityItem = replace(item, R"(C:\\synthetic\\\u043f\u0430\u043f\u043a\u0430-\ud83d\ude00)", package.generic_u8string());
        const auto json = legacy ? std::string(R"({"schema_version":"desktop-upload-queue.v2","items":[)") + parityItem + "]}" : ledger(parityItem, operation, ack);
        setup(f, {json});
        const auto path = f.root / L"comparison.json"; f.write(path, CustodyBytes(json.begin(), json.end()));
        unsigned rewritten = 0;
        DesktopUploadQueueService standard(path, f.root, [&](const auto&, const auto&, auto) { ++rewritten; return true; });
        assert(standard.load() && rewritten == (legacy ? 1U : 0U)); // Legacy consumer alone requests a rewrite.
        auto input = readInput(f); auto result = Candidate::read(*input.value, cancelled); assert(result.ok());
        const auto& a = result.value->get()->items()[0]; const auto& b = standard.items()[0];
        assert(std::string_view(a.localRecordingId) == b.localRecordingId && std::string_view(a.directoryId) == b.directoryId && std::string_view(a.sessionId) == b.sessionId);
        assert(std::filesystem::u8path(a.packageDirectory.begin(), a.packageDirectory.end()) == b.packageDirectory);
        assert(a.status == b.status && a.acceptedBytes == b.acceptedBytes && a.attempts == b.attempts && a.updatedAtMs == b.updatedAtMs);
        assert(std::string_view(a.safeReason) == b.safeReason && std::string_view(a.ownerUserId) == b.ownerUserId && std::string_view(a.ownerWorkspaceId) == b.ownerWorkspaceId);
        assert(std::string_view(a.meetingId) == b.meetingId && std::string_view(a.mediaRevisionId) == b.mediaRevisionId && std::string_view(a.uploadSessionId) == b.uploadSessionId);
        assert(std::string_view(a.serverStatus) == b.serverStatus && std::string_view(a.processingStatus) == b.processingStatus && std::string_view(a.mediaRevisionStatus) == b.mediaRevisionStatus);
        assert(result.value->get()->deletionOperations().size() == standard.deletionOperations().size());
        assert(result.value->get()->purgeAcknowledgements().size() == standard.localPurgeAcknowledgements().size());
        if (!legacy) {
            const auto& op = result.value->get()->deletionOperations()[0]; const auto& old = standard.deletionOperations()[0];
            assert(std::string_view(op.operationId) == old.operationId && op.target == old.target && std::string_view(op.targetId) == old.targetId);
            assert(std::string_view(op.actorUserId) == old.actorUserId && std::string_view(op.workspaceId) == old.workspaceId && std::string_view(op.serverOrigin) == old.serverOrigin);
            assert(op.phase == old.phase && op.requestedAtMs == old.requestedAtMs && op.updatedAtMs == old.updatedAtMs && op.attemptCount == old.attemptCount && op.nextAttemptAtMs == old.nextAttemptAtMs);
            assert(std::string_view(op.receiptRequestId) == old.receiptRequestId && std::string_view(op.safeReason) == old.safeReason);
            const auto& purge = result.value->get()->purgeAcknowledgements()[0]; const auto& oldPurge = standard.localPurgeAcknowledgements()[0];
            assert(std::string_view(purge.taskId) == oldPurge.taskId && std::string_view(purge.meetingId) == oldPurge.meetingId && purge.acknowledgedAtMs == oldPurge.acknowledgedAtMs);
        }
    }
    {
        // Real non-SSO strings/nested key sets, parser array scratch and growth
        // of all three result vectors. Every operator-new ordinal is cut below;
        // semantic attribution of each ordinal still requires source review.
        std::string rows, operations, acks;
        for (unsigned i = 0; i < 4; ++i) {
            auto row = replace(item, "recording-a", "recording-" + std::to_string(i));
            row = replace(row, R"(C:\\synthetic\\\u043f\u0430\u043f\u043a\u0430-\ud83d\ude00)", std::string(2048, 'p'));
            row = replace(row, "directory-a", std::string(200, 'd'));
            const auto extra = std::string("\"extra\":{\"") + std::string(400, 'k') + "\":\"" + std::string(800, 'x') +
                R"(","nested":{"a":[1,2,{"b":3}],"c":{"d":4,"e":5},"f":[]}},)";
            row.insert(1, extra);
            if (i) { rows += ','; operations += ','; acks += ','; }
            rows += row;
            operations += replace(operation, "33333333", "3333333" + std::to_string(i));
            acks += replace(ack, "66666666", "6666666" + std::to_string(i));
        }
        const auto large = ledger(rows, operations, acks);
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto queue = setup(f, {full, large});
        auto input = readInput(f); const auto held = CustodyOwnedMemory::usedBytes();
        const auto snapshot = artifacts(f);
        const auto queueIdentity = f.root / L".custody-v1" / L"queue" / L"id.bin";
        const auto bootstrapIdentity = f.object() / L"id.bin";
        const auto assertLeases = [&] {
            for (const auto& path : {queueIdentity, bootstrapIdentity}) {
                const auto handle = CreateFileW(path.c_str(), GENERIC_WRITE,
                    FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
                assert(handle == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
            }
        };
        const auto assertFailure = [&](const auto& result, CustodyFileError error, std::uint32_t native = 0) {
            assert(!result.ok() && !result.value && result.error == error && result.nativeError == native);
            assert(CustodyOwnedMemory::usedBytes() == held && writerIoCounts() == (std::array<unsigned, 8>{}));
            assert(text(input.value->get()->payloads()[0]) == full && text(input.value->get()->payloads()[1]) == large);
            assertLeases();
            std::array<CustodyNativeJob, 4> jobs; for (const auto& job : jobs) assert(job); // Read really completed.
        };
        inject(FileFault::none);
        assertFailure(Candidate::read(*input.value, {}), CustodyFileError::invalidInput);
        cancelled->store(true);
        assertFailure(Candidate::read(*input.value, cancelled), CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        cancelled->store(false);
        {
            std::array<CustodyNativeJob, 4> jobs; for (const auto& job : jobs) assert(job);
            const auto refused = Candidate::read(*input.value, cancelled);
            assert(!refused.ok() && refused.error == CustodyFileError::allocationFailed && !refused.value);
            assert(CustodyOwnedMemory::usedBytes() == held && writerIoCounts() == (std::array<unsigned, 8>{}));
        }
        {
            // Reserve actual bytes, not a guessed input-size cost. Keep the BOTH
            // input alive; pressure releases to this baseline before retry.
            CustodyAllocator<std::uint8_t> allocator;
            const auto count = CustodyOwnedMemory::limit - held - 512;
            auto* pressure = allocator.allocate(count);
            const auto used = CustodyOwnedMemory::usedBytes();
            const auto failed = Candidate::read(*input.value, cancelled);
            assert(!failed.ok() && !failed.value && failed.error == CustodyFileError::allocationFailed);
            assert(CustodyOwnedMemory::usedBytes() == used && writerIoCounts() == (std::array<unsigned, 8>{}));
            assertLeases(); allocator.deallocate(pressure, count);
            assert(CustodyOwnedMemory::usedBytes() == held);
        }
        const auto invoke = [&](std::size_t failAt, std::size_t cancelAt) {
            queueAllocation = {true, false, 0, failAt, cancelAt, cancelled.get(), queueIdentity.c_str(), bootstrapIdentity.c_str()};
            auto result = Candidate::read(*input.value, cancelled);
            queueAllocation.active = false;
            return result;
        };
        auto retained = invoke(0, 0); assert(retained.ok());
        const auto allocations = queueAllocation.calls; assert(allocations > 4);
        assert(retained.value->get()->items().size() == 4 && retained.value->get()->deletionOperations().size() == 4 && retained.value->get()->purgeAcknowledgements().size() == 4);
        // A previous published snapshot remains unchanged across each refusal.
        retained.value.reset(); assert(CustodyOwnedMemory::usedBytes() == held);
        auto previous = Candidate::read(*input.value, cancelled); assert(previous.ok());
        const auto withPrevious = CustodyOwnedMemory::usedBytes();
        for (std::size_t ordinal = 1; ordinal <= allocations; ++ordinal) {
            const auto failed = invoke(ordinal, 0);
            assert(queueAllocation.hit && !failed.ok() && !failed.value && failed.error == CustodyFileError::allocationFailed);
            assert(CustodyOwnedMemory::usedBytes() == withPrevious && writerIoCounts() == (std::array<unsigned, 8>{}));
            assert(previous.value->get()->items()[0].packageDirectory.size() == 2048);
            assert(previous.value->get()->items()[0].status == UploadQueueStatus::uploaded && previous.value->get()->updatedAtMs() == 17);
            assert(previous.value->get()->input() == *input.value); assertLeases();
            {
                std::array<CustodyNativeJob, 4> jobs; for (const auto& job : jobs) assert(job);
            }
            auto retry = Candidate::read(*input.value, cancelled); assert(retry.ok());
            assert(retry.value->get()->items().size() == 4 && retry.value->get()->deletionOperations().size() == 4 && retry.value->get()->purgeAcknowledgements().size() == 4);
            retry.value.reset(); assert(CustodyOwnedMemory::usedBytes() == withPrevious);
        }
        previous.value.reset(); assert(CustodyOwnedMemory::usedBytes() == held);
        // Deterministic cancellation at first/middle/last actual allocation.
        // This does not observe allocation-free whitespace/digits/objectEnd/
        // duplicate-scan polling, or identify the exact final poll instruction.
        for (const auto ordinal : {std::size_t{1}, allocations / 2, allocations}) {
            const auto stopped = invoke(0, ordinal); assert(queueAllocation.hit);
            assertFailure(stopped, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
            cancelled->store(false);
            auto retry = Candidate::read(*input.value, cancelled); assert(retry.ok());
            retry.value.reset(); assert(CustodyOwnedMemory::usedBytes() == held);
        }
        assert(artifacts(f) == snapshot && input.value->get()->context().objectId == queue.objectId);
        queueAllocation = {};
        std::fprintf(stderr, "logical-queue actual allocation cuts=%zu; cancel cuts=first/middle/last; allocation-free polling requires source review\n", allocations);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}

void protectedQueueInput() {
    inject(FileFault::none);
    const auto before = CustodyOwnedMemory::usedBytes();
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    assert(ProtectedCustodyQueueInput::read({}, cancelled).error == CustodyFileError::invalidInput);
    {
        Fixture f(CustodyRole::bootstrap, L"bootstrap");
        auto queue = f.context; queue.role = CustodyRole::queue; queue.objectId[0] = 31;
        const CustodyBytes bytes{1, 2, 3}; // Physical input only; deliberately NOT semantic ledger proof.
        assert(commitProtectedCustodyMetadata(f.root, "", queue, 0, bytes, cancelled).state == CustodyCommitState::committed);
        CustodyBootstrapValue bootstrap; bootstrap.context = f.context; bootstrap.generation = 1;
        bootstrap.queueObjectId = queue.objectId;
        auto json = writeCustodyBootstrap(bootstrap, f.context, 1, queue.objectId); assert(json.ok());
        assert(commitProtectedCustodyMetadata(f.root, "", f.context, 0, *json.value, cancelled).state == CustodyCommitState::committed);
        auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        auto input = ProtectedCustodyQueueInput::read(*parent.value, cancelled);
        if (!input.ok()) std::fprintf(stderr, "queue-input error=%u native=%u\n", static_cast<unsigned>(input.error), input.nativeError);
        assert(input.ok());
        assert(input.value->get()->payloads()[0] == bytes && input.value->get()->payloads()[1] == bytes);
        assert(input.value->get()->context().storeId == queue.storeId && input.value->get()->context().objectId == queue.objectId);
        parent.value.reset();
        assert(!ProtectedCustodyFiles::open(f.root, "", queue, CustodyFileAccess::writeExisting).ok());
        assert(!f.open(CustodyFileAccess::writeExisting).ok());
        input.value.reset();
        assert(ProtectedCustodyFiles::open(f.root, "", queue, CustodyFileAccess::writeExisting).ok());
    }
    const auto setup = [&](Fixture& f, std::size_t length, bool next) {
        auto queue = f.context; queue.role = CustodyRole::queue; queue.objectId[0] = 31;
        const CustodyBytes bytes{1, 2, 3};
        assert(commitProtectedCustodyMetadata(f.root, "", queue, 0, bytes, cancelled).state == CustodyCommitState::committed);
        if (next) {
            const CustodyBytes replacement(length, 7);
            assert(commitProtectedCustodyMetadata(f.root, "", queue, 1, replacement, cancelled).state == CustodyCommitState::committed);
        }
        CustodyBootstrapValue bootstrap; bootstrap.context = f.context; bootstrap.generation = 1; bootstrap.queueObjectId = queue.objectId;
        auto json = writeCustodyBootstrap(bootstrap, f.context, 1, queue.objectId); assert(json.ok());
        assert(commitProtectedCustodyMetadata(f.root, "", f.context, 0, *json.value, cancelled).state == CustodyCommitState::committed);
        return queue;
    };
    for (const auto length : {std::size_t(ProtectedCustodyCodec::blockBytes + 31), std::size_t(4 * 1024 * 1024)}) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto queue = setup(f, length, true);
        auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        inject(FileFault::none);
        auto input = ProtectedCustodyQueueInput::read(*parent.value, cancelled); assert(input.ok());
        assert(input.value->get()->indices().selectedSlot == 1 && input.value->get()->indices().indices[1].generation == 2);
        assert(input.value->get()->payloads()[0] == CustodyBytes({1,2,3}));
        assert(input.value->get()->payloads()[1] == CustodyBytes(length, 7));
        assert(!writes && !flushes && !renames && !searches);
        input.value.reset(); parent.value.reset();
        const CustodyBytes oversized(4 * 1024 * 1024 + 1, 7);
        const auto refused = commitProtectedCustodyMetadata(f.root, "", queue, 2, oversized, cancelled);
        assert(refused.state == CustodyCommitState::notCommitted && refused.error == CustodyFileError::invalidInput);
    }
    {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); setup(f, 0, false);
        auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        inject(FileFault::none);
        assert(ProtectedCustodyQueueInput::read(*parent.value, {}).error == CustodyFileError::invalidInput && !reads);
        cancelled->store(true); assert(ProtectedCustodyQueueInput::read(*parent.value, cancelled).nativeError == ERROR_OPERATION_ABORTED && !reads);
        cancelled->store(false);
        { std::array<CustodyNativeJob, 4> jobs; assert(ProtectedCustodyQueueInput::read(*parent.value, cancelled).error == CustodyFileError::allocationFailed && !reads); }
        { std::array<CustodyPin, 31> pins; assert(ProtectedCustodyQueueInput::read(*parent.value, cancelled).error == CustodyFileError::allocationFailed && !reads); }
        { CustodyBytes pressure; pressure.reserve(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes());
          assert(ProtectedCustodyQueueInput::read(*parent.value, cancelled).error == CustodyFileError::allocationFailed); }
        // Budget failure in physical validation is sticky: use a fresh owner, not reset.
        parent.value.reset(); parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        inject(FileFault::none);
        auto input = ProtectedCustodyQueueInput::read(*parent.value, cancelled); assert(input.ok());
        const auto fullReads = reads; input.value.reset();
        for (const auto ordinal : {1U, fullReads}) {
            inject(FileFault::none); afterRead = [&] { if (reads == ordinal) cancelled->store(true); };
            const auto stopped = ProtectedCustodyQueueInput::read(*parent.value, cancelled);
            afterRead = {}; cancelled->store(false);
            assert(!stopped.ok() && stopped.nativeError == ERROR_OPERATION_ABORTED);
            assert(!writes && !flushes && !renames);
        }
        inject(FileFault::none);
        bool busy = false;
        afterRead = [&] {
            const auto readCount = reads;
            std::thread competing([&] {
                const auto nested = ProtectedCustodyQueueInput::read(*parent.value, cancelled);
                assert(!nested.ok() && nested.error == CustodyFileError::conflict && nested.nativeError == ERROR_BUSY);
                busy = true;
            });
            competing.join(); assert(reads == readCount);
        };
        assert(ProtectedCustodyQueueInput::read(*parent.value, cancelled).ok()); afterRead = {}; assert(busy);
        assert(ProtectedCustodyQueueInput::read(*parent.value, cancelled).ok());
    }
    for (const auto artifact : {L"index.0", L"index.1", L"block.0.1"}) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); setup(f, 0, false);
        const auto damaged = f.root / L".custody-v1" / L"queue" / artifact;
        assert(DeleteFileW(damaged.c_str()));
        auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        inject(FileFault::none);
        const auto input = ProtectedCustodyQueueInput::read(*parent.value, cancelled); assert(!input.ok());
        assert(!writes && !flushes && !renames && !std::filesystem::exists(damaged));
    }
    for (const auto artifact : {L"index.0", L"index.1", L"block.0.1", L"block.0.2"}) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); setup(f, 5, true);
        const auto damaged = f.root / L".custody-v1" / L"queue" / artifact;
        CustodyBytes bytes;
        { std::ifstream stream(damaged, std::ios::binary); assert(stream);
          bytes.assign(std::istreambuf_iterator<char>(stream), {}); }
        assert(!bytes.empty()); bytes.back() ^= 1;
        assert(DeleteFileW(damaged.c_str())); f.write(damaged, bytes);
        auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        inject(FileFault::none);
        const auto input = ProtectedCustodyQueueInput::read(*parent.value, cancelled);
        assert(!input.ok() && input.error == CustodyFileError::protectionFailed && input.nativeError != 0);
        assert(!writes && !flushes && !renames && std::filesystem::file_size(damaged) == bytes.size());
    }
    for (unsigned shape = 0; shape < 3; ++shape) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto queue = setup(f, 0, false);
        if (shape == 0) {
            for (const auto slot : {L"index.0", L"index.1"}) assert(DeleteFileW((f.root/L".custody-v1"/L"queue"/slot).c_str()));
        } else {
            CustodyIndex index{1, shape == 1 ? 0ULL : 3ULL, {}};
            if (shape == 2) index.entries.push_back({0, 0, 1}); // ZERO is not queue DATA.
            auto files = ProtectedCustodyFiles::open(f.root, "", queue, CustodyFileAccess::writeExisting); assert(files.ok());
            for (unsigned slot = 0; slot < 2; ++slot) {
                auto cipher = ProtectedCustodyCodec::sealIndex(queue, slot, index); assert(cipher.ok());
                assert((*files.value)->publishIndex(slot, *cipher.value).state == CustodyPublishState::published);
            }
        }
        auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        inject(FileFault::none);
        const auto input = ProtectedCustodyQueueInput::read(*parent.value, cancelled);
        assert(!input.ok() && input.error == (shape == 0 ? CustodyFileError::recoveryRequired : CustodyFileError::invalidContent));
        assert(!writes && !flushes && !renames && !searches);
    }
    {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); setup(f, 0, false);
        auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        inject(FileFault::none);
        auto input = ProtectedCustodyQueueInput::read(*parent.value, cancelled); assert(input.ok());
        const auto lastRead = reads; input.value.reset();
        {
            CustodyBytes pressure;
            inject(FileFault::none);
            afterRead = [&] { if (reads == lastRead) pressure.reserve(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes()); };
            const auto failed = ProtectedCustodyQueueInput::read(*parent.value, cancelled); afterRead = {};
            assert(!failed.ok() && failed.error == CustodyFileError::allocationFailed && !writes && !renames);
        }
        parent.value.reset();
        parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        assert(ProtectedCustodyQueueInput::read(*parent.value, cancelled).ok());
    }
    {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); const auto queue = setup(f, 0, false);
        auto explicitParent = ProtectedCustodyBootstrapPair::read(f.root, f.context, queue.objectId, cancelled); assert(explicitParent.ok());
        inject(FileFault::none);
        assert(ProtectedCustodyQueueInput::read(*explicitParent.value, cancelled).error == CustodyFileError::invalidInput && !reads);
    }
    for (const auto fault : {FileFault::readFailed, FileFault::hashCreate, FileFault::allocation}) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); setup(f, 0, false);
        auto parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
        inject(fault);
        const auto failed = ProtectedCustodyQueueInput::read(*parent.value, cancelled);
        assert(!failed.ok() && failed.error == (fault == FileFault::readFailed ? CustodyFileError::ioFailed :
            fault == FileFault::hashCreate ? CustodyFileError::hashFailed : CustodyFileError::allocationFailed));
        assert(!writes && !flushes && !renames); inject(FileFault::none);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}
void protectedBootstrapDiscovery() {
    inject(FileFault::none);
    const auto before = CustodyOwnedMemory::usedBytes();
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    CustodyId queue{}; queue[0] = 31;
    const auto reserveQueue = [&](Fixture& f) {
        auto context = f.context; context.role = CustodyRole::queue; context.objectId = queue;
        assert(ProtectedCustodyFiles::open(f.root, "", context, CustodyFileAccess::createNew).ok());
    };
    const auto commit = [&](Fixture& f, std::uint64_t generation, bool migrating) {
        CustodyBootstrapValue v; v.context = f.context; v.generation = generation; v.queueObjectId = queue;
        if (migrating) {
            v.mode = CustodyBootstrapMode::migrating; v.transactionId = CustodyId{};
            v.subject = CustodyMigrationSubject::queue;
        }
        auto bytes = writeCustodyBootstrap(v, f.context, generation, queue); assert(bytes.ok());
        assert(commitProtectedCustodyMetadata(f.root, "", f.context, generation-1, *bytes.value, cancelled).state == CustodyCommitState::committed);
    };
    const auto open = [&](const Fixture& f) { return ProtectedCustodyBootstrapPair::read(f.root, cancelled); };
    for (bool migrating : {false, true}) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); reserveQueue(f); commit(f, 1, migrating);
        {
            inject(FileFault::none); auto result = open(f); assert(result.ok());
            assert(result.value->get()->current().context.storeId == f.context.storeId);
            assert(result.value->get()->current().context.objectId == f.context.objectId);
            assert(result.value->get()->current().queueObjectId == queue);
            assert(result.value->get()->current().mode == (migrating ? CustodyBootstrapMode::migrating : CustodyBootstrapMode::protectedStore));
            auto held = *result.value; result.value.reset();
            for (const auto& path : {f.root/L".custody-v1"/L"store.id", f.object()/L"id.bin", f.root/L".custody-v1"/L"queue"/L"id.bin"}) {
                const auto write = CreateFileW(path.c_str(), GENERIC_WRITE, FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
                    nullptr, OPEN_EXISTING, 0, nullptr);
                assert(write == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
                assert(!DeleteFileW(path.c_str()) && GetLastError() == ERROR_SHARING_VIOLATION);
            }
            assert(!f.open(CustodyFileAccess::writeExisting).ok());
            auto context = f.context; context.role = CustodyRole::queue; context.objectId = queue;
            assert(!ProtectedCustodyFiles::open(f.root, "", context, CustodyFileAccess::writeExisting).ok());
            // A reservation with no indices is NOT an empty or authorized queue.
            assert(!std::filesystem::exists(f.root/L".custody-v1"/L"queue"/L"index.0"));
            assert(writes == 0 && flushes == 0 && renames == 0 && searches == 0);
            held.reset();
            assert(f.open(CustodyFileAccess::writeExisting).ok());
            assert(ProtectedCustodyFiles::open(f.root, "", context, CustodyFileAccess::writeExisting).ok());
            const auto write = CreateFileW((f.root/L".custody-v1"/L"store.id").c_str(), GENERIC_WRITE,
                FILE_SHARE_READ|FILE_SHARE_WRITE, nullptr, OPEN_EXISTING, 0, nullptr);
            assert(write != INVALID_HANDLE_VALUE); CloseHandle(write);
        }
        commit(f, 2, !migrating);
        assert(open(f).value->get()->current().generation == 2);
        for (unsigned ordinal = 1; ordinal <= 10; ++ordinal) {
            inject(FileFault::readFailed, ordinal); const auto denied = open(f);
            assert(!denied.ok() && denied.error == CustodyFileError::ioFailed && denied.nativeError == ERROR_READ_FAULT);
            assert(writes == 0 && flushes == 0 && renames == 0 && searches == 0);
        }
        for (unsigned ordinal : {1U, 2U, 3U, 4U, 8U, 9U, 10U}) {
            inject(FileFault::none); afterRead = [&] { if (reads == ordinal) cancelled->store(true); };
            const auto denied = open(f); afterRead = {}; cancelled->store(false);
            assert(!denied.ok() && denied.nativeError == ERROR_OPERATION_ABORTED);
            if (ordinal <= 2) assert(reads == 2);
            if (ordinal == 3 || ordinal == 4) assert(reads == 4);
            assert(writes == 0 && flushes == 0 && renames == 0);
        }
        inject(FileFault::none); cancelled->store(true);
        assert(open(f).nativeError == ERROR_OPERATION_ABORTED && opens == 0); cancelled->store(false);
        assert(ProtectedCustodyBootstrapPair::read(f.root, {}).error == CustodyFileError::invalidInput && opens == 0);
        { std::array<CustodyNativeJob, 4> jobs; assert(open(f).error == CustodyFileError::allocationFailed && opens == 0); }
        { std::array<CustodyPin, 32> pins; assert(open(f).error == CustodyFileError::allocationFailed && opens == 0); }
        for (auto fault : {FileFault::hashCreate, FileFault::allocation}) {
            inject(fault); assert(open(f).error == (fault == FileFault::allocation ? CustodyFileError::allocationFailed : CustodyFileError::hashFailed));
        }
        inject(FileFault::none);
        { CustodyBytes pressure; pressure.reserve(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes());
          assert(open(f).error == CustodyFileError::allocationFailed); }
        assert(open(f).ok());
    }
    // Each fixed identity is bounded BEFORE read and never repaired/regenerated.
    {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); reserveQueue(f); commit(f, 1, true);
        inject(FileFault::identityMismatch, 3); // Second immutable store observation.
        const auto mismatch = open(f);
        assert(!mismatch.ok() && mismatch.error == CustodyFileError::identityMismatch && reads == 4);
        assert(writes == 0 && renames == 0 && flushes == 0);
        inject(FileFault::read); assert(open(f).error == CustodyFileError::identityMismatch && reads == 1);
        inject(FileFault::none); assert(open(f).ok());
    }
    for (unsigned slot : {0U, 1U}) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); reserveQueue(f); commit(f, 1, true); commit(f, 2, false);
        assert(DeleteFileW((f.object()/(slot ? L"index.1" : L"index.0")).c_str()));
        inject(FileFault::none); const auto denied = open(f); assert(!denied.ok());
        assert(writes == 0 && renames == 0 && flushes == 0 && searches == 0);
    }
    for (unsigned identity = 0; identity < 3; ++identity) for (unsigned size : {0U, 15U, 17U}) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); reserveQueue(f); commit(f, 1, true);
        const auto path = identity == 0 ? f.root/L".custody-v1"/L"store.id"
            : identity == 1 ? f.object()/L"id.bin" : f.root/L".custody-v1"/L"queue"/L"id.bin";
        assert(DeleteFileW(path.c_str())); f.write(path, CustodyBytes(size, 0));
        inject(FileFault::none); const auto denied = open(f);
        assert(!denied.ok() && denied.error == CustodyFileError::identityMismatch);
        assert(reads == (identity == 0 ? 0U : identity == 1 ? 1U : 3U));
        assert(writes == 0 && renames == 0 && flushes == 0 && std::filesystem::file_size(path) == size);
    }
    for (unsigned identity = 0; identity < 3; ++identity) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); reserveQueue(f); commit(f, 1, true);
        const auto path = identity == 0 ? f.root/L".custody-v1"/L"store.id"
            : identity == 1 ? f.object()/L"id.bin" : f.root/L".custody-v1"/L"queue"/L"id.bin";
        assert(DeleteFileW(path.c_str())); inject(FileFault::none);
        const auto missing = open(f); assert(!missing.ok() && missing.error == CustodyFileError::ioFailed);
        assert(writes == 0 && renames == 0 && flushes == 0 && !std::filesystem::exists(path));
    }
    for (unsigned identity = 0; identity < 3; ++identity) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); reserveQueue(f); commit(f, 1, true);
        const auto path = identity == 0 ? f.root/L".custody-v1"/L"store.id"
            : identity == 1 ? f.object()/L"id.bin" : f.root/L".custody-v1"/L"queue"/L"id.bin";
        const auto alias = f.root/L"alias";
        assert(CreateHardLinkW(alias.c_str(), path.c_str(), nullptr)); inject(FileFault::none);
        assert(open(f).error == CustodyFileError::unsafeFile);
        assert(writes == 0 && renames == 0 && flushes == 0); assert(DeleteFileW(alias.c_str()));
        assert(open(f).ok());
        BOOL present = FALSE, defaulted = FALSE; PACL dacl = nullptr;
        assert(GetSecurityDescriptorDacl(f.descriptor, &present, &dacl, &defaulted) && present && dacl);
        assert(SetNamedSecurityInfoW(path.wstring().data(), SE_FILE_OBJECT,
            DACL_SECURITY_INFORMATION|UNPROTECTED_DACL_SECURITY_INFORMATION, nullptr, nullptr, dacl, nullptr) == ERROR_SUCCESS);
        assert(open(f).error == CustodyFileError::unsafeFile);
    }
    {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); commit(f, 1, true);
        inject(FileFault::none); assert(!open(f).ok());
        assert(!std::filesystem::exists(f.root/L".custody-v1"/L"queue") && writes == 0);
    }
    {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); reserveQueue(f); commit(f, 1, true);
        const auto path = f.root/L".custody-v1"/L"queue"/L"id.bin";
        assert(DeleteFileW(path.c_str())); f.write(path, CustodyBytes(16, 42));
        inject(FileFault::none); assert(open(f).error == CustodyFileError::invalidContent);
        assert(writes == 0 && renames == 0 && flushes == 0);
    }
    {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"), target;
        assert(target.open(CustodyFileAccess::createNew).ok()); commit(f, 1, true);
        junction(f.root/L".custody-v1"/L"queue", target.object(), f.security);
        inject(FileFault::none); assert(open(f).error == CustodyFileError::unsafePath);
        assert(writes == 0 && renames == 0 && flushes == 0);
        assert(RemoveDirectoryW((f.root/L".custody-v1"/L"queue").c_str()));
    }
    inject(FileFault::none); assert(CustodyOwnedMemory::usedBytes() == before);
}
void protectedBootstrapPairs() {
    inject(FileFault::none);
    const auto before = CustodyOwnedMemory::usedBytes();
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    CustodyId queue{}; queue[0] = 31;
    const auto value = [&](const Fixture& f, std::uint64_t generation, unsigned mode) {
        CustodyBootstrapValue v; v.context = f.context; v.generation = generation; v.queueObjectId = queue;
        if (mode) {
            v.mode = CustodyBootstrapMode::migrating; v.transactionId = CustodyId{}; v.transactionId->at(0) = 41;
            v.subject = mode == 1 ? CustodyMigrationSubject::queue : CustodyMigrationSubject::package;
            if (mode == 2) { v.directory = std::array<char, 301>{}; const std::string name = "package-a";
                std::copy(name.begin(), name.end(), v.directory->begin()); }
        }
        return v;
    };
    const auto commit = [&](Fixture& f, std::uint64_t generation, unsigned mode, bool padded = false) {
        auto bytes = writeCustodyBootstrap(value(f, generation, mode), f.context, generation, queue); assert(bytes.ok());
        if (padded) bytes.value->resize(65536, ' ');
        assert(commitProtectedCustodyMetadata(f.root, "", f.context, generation-1, *bytes.value, cancelled).state == CustodyCommitState::committed);
    };
    const auto open = [&](const Fixture& f) { return ProtectedCustodyBootstrapPair::read(f.root, f.context, queue, cancelled); };
    for (unsigned mode : {0U, 1U, 2U}) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap");
        commit(f, 1, mode, true);
        {
            inject(FileFault::none); auto result = open(f); assert(result.ok());
            const auto& pair = **result.value;
            assert(pair.selectedSlot() == 0 && pair.current().generation == 1);
            assert(pair.slots()[0].generation == 1 && pair.slots()[1].generation == 1);
            assert(pair.current().queueObjectId == queue && pair.indices().indices[1].logicalLength == 65536);
            assert(pair.current().mode == (mode ? CustodyBootstrapMode::migrating : CustodyBootstrapMode::protectedStore));
            assert(!f.open(CustodyFileAccess::writeExisting).ok());
            auto held = *result.value; result.value.reset();
            assert(!f.open(CustodyFileAccess::writeExisting).ok());
            // This proves only own bootstrap provenance, NOT fixed-queue/intent authority.
            assert(!std::filesystem::exists(f.root / L".custody-v1" / L"queue"));
            assert(writes == 0 && renames == 0 && flushes == 0 && searches == 0 && diskChecks == 0);
            held.reset(); assert(f.open(CustodyFileAccess::writeExisting).ok());
        }
        commit(f, 2, 1); commit(f, 3, 0);
        {
            const auto artifacts = writerArtifacts(f); inject(FileFault::none);
            auto result = open(f); assert(result.ok());
            const auto& pair = **result.value;
            assert(pair.selectedSlot() == 0 && pair.current().mode == CustodyBootstrapMode::protectedStore);
            assert(pair.slots()[0].generation == 3 && pair.slots()[1].generation == 2);
            assert(pair.slots()[1].mode == CustodyBootstrapMode::migrating);
            assert(pair.indices().indices[1].generation == 2);
            assert(writes == 0 && renames == 0 && flushes == 0 && writerArtifacts(f) == artifacts);
        }
        for (unsigned ordinal : {1U, 2U, 3U, 4U, 5U, 6U, 7U, 8U}) {
            const auto artifacts = writerArtifacts(f); inject(FileFault::readFailed, ordinal);
            const auto failed = open(f);
            assert(!failed.ok() && failed.error == CustodyFileError::ioFailed && failed.nativeError == ERROR_READ_FAULT);
            assert(writes == 0 && renames == 0 && flushes == 0 && writerArtifacts(f) == artifacts);
        }
        for (unsigned ordinal : {1U, 6U, 7U, 8U}) {
            inject(FileFault::none);
            afterRead = [&] { if (reads == ordinal) cancelled->store(true); };
            const auto denied = open(f); afterRead = {}; cancelled->store(false);
            if (ordinal == 1) assert(reads == 2); // No index/DATA read after cancelled fixed-ID open.
            assert(!denied.ok() && denied.nativeError == ERROR_OPERATION_ABORTED && writes == 0 && renames == 0);
            assert(f.open(CustodyFileAccess::writeExisting).ok());
        }
        cancelled->store(true); inject(FileFault::none);
        assert(open(f).nativeError == ERROR_OPERATION_ABORTED && opens == 0);
        cancelled->store(false);
        for (const auto fault : {FileFault::hashCreate, FileFault::allocation}) {
            inject(fault); const auto denied = open(f);
            assert(!denied.ok() && denied.error == (fault == FileFault::allocation ? CustodyFileError::allocationFailed : CustodyFileError::hashFailed));
            assert(writes == 0 && renames == 0);
        }
        inject(FileFault::none);
        {
            std::array<CustodyPin, 32> pins;
            assert(open(f).error == CustodyFileError::allocationFailed && opens == 0);
        }
        {
            std::array<CustodyNativeJob, 4> jobs;
            assert(open(f).error == CustodyFileError::allocationFailed && opens == 0);
        }
        {
            CustodyBytes pressure; pressure.reserve(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes());
            assert(open(f).error == CustodyFileError::allocationFailed && writes == 0);
        }
        assert(open(f).ok());
        auto otherQueue = queue; otherQueue[0] ^= 1;
        assert(ProtectedCustodyBootstrapPair::read(f.root, f.context, otherQueue, cancelled).error == CustodyFileError::invalidContent);
        auto wrong = f.context; wrong.objectId[0] ^= 1;
        assert(ProtectedCustodyBootstrapPair::read(f.root, wrong, queue, cancelled).error == CustodyFileError::identityMismatch);
        wrong = f.context; wrong.storeId[0] ^= 1;
        assert(ProtectedCustodyBootstrapPair::read(f.root, wrong, queue, cancelled).error == CustodyFileError::identityMismatch);
        wrong = f.context; wrong.role = CustodyRole::queue; inject(FileFault::none);
        assert(ProtectedCustodyBootstrapPair::read(f.root, wrong, queue, cancelled).error == CustodyFileError::invalidInput && opens == 0);
        assert(ProtectedCustodyBootstrapPair::read(f.root, f.context, queue, {}).error == CustodyFileError::invalidInput && opens == 0);
        commit(f, 4, 2); assert(open(f).value->get()->current().generation == 4);
    }
    // Native DPAPI-authenticated LOWER payload failure still blocks a healthy higher slot.
    for (unsigned bad : {0U, 1U, 2U, 3U, 4U, 5U, 6U}) {
        inject(FileFault::none); Fixture f(CustodyRole::bootstrap, L"bootstrap");
        auto bytes = writeCustodyBootstrap(value(f, 1, 0), f.context, 1, queue); assert(bytes.ok());
        const auto replace = [&](std::string_view from, std::string_view to) {
            const std::string text(bytes.value->begin(), bytes.value->end()); const auto at = text.find(from);
            assert(at != std::string::npos && from.size() == to.size());
            std::copy(to.begin(), to.end(), bytes.value->begin()+at);
        };
        if (bad == 0) (*bytes.value)[0] = '[';
        if (bad == 1) replace("\"generation\":1", "\"generation\":2");
        if (bad == 2) replace("bootstrap.v1", "bootstrap.v2");
        if (bad == 3) { const std::string text(bytes.value->begin(), bytes.value->end());
            const auto at = text.find("\"queue_object_id\":\""); assert(at != std::string::npos); (*bytes.value)[at+19] = '0'; }
        assert(commitProtectedCustodyMetadata(f.root, "", f.context, 0, *bytes.value, cancelled).state == CustodyCommitState::committed);
        commit(f, 2, 0);
        if (bad == 4) assert(DeleteFileW((f.object()/L"index.0").c_str()));
        if (bad == 5) assert(DeleteFileW((f.object()/L"index.1").c_str()));
        if (bad == 6) assert(DeleteFileW((f.object()/L"block.0.1").c_str()));
        const auto artifacts = writerArtifacts(f); inject(FileFault::none);
        const auto denied = open(f); assert(!denied.ok());
        assert(writes == 0 && renames == 0 && flushes == 0 && writerArtifacts(f) == artifacts);
    }
    for (std::uint64_t length : {0ULL, 64ULL}) {
        Fixture f(CustodyRole::bootstrap, L"bootstrap"); auto files = f.open(CustodyFileAccess::createNew); assert(files.ok());
        CustodyIndex zero{1, length, {}}; if (length) zero.entries.push_back({0, 0, 1});
        publish(f, **files.value, 0, zero); publish(f, **files.value, 1, zero);
        files.value.reset(); assert(open(f).error == CustodyFileError::invalidContent);
    }
    inject(FileFault::none); assert(CustodyOwnedMemory::usedBytes() == before);
}
void protectedPackagePairs() {
    const auto before = CustodyOwnedMemory::usedBytes();
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    const auto value = [](const Fixture& f, unsigned schema, std::uint64_t generation, std::uint8_t member) {
        CustodyPackageValue v;
        v.schema = schema; v.context = f.context; v.generation = generation;
        const std::string directory = "package-a";
        std::copy(directory.begin(), directory.end(), v.directory.begin());
        v.refCount = 1; v.refs[0].objectId[0] = member;
        if (schema == 2) { v.refs[0].packed = true; v.refs[0].containerId = CustodyId{}; v.refs[0].containerId->at(0) = member; }
        return v;
    };
    const auto commit = [&](Fixture& f, const CustodyPackageValue& v, bool padded = false) {
        auto bytes = writeCustodyPackage(v, f.context, v.generation, "package-a"); assert(bytes.ok());
        if (padded) bytes.value->resize(65536, ' ');
        assert(commitProtectedCustodyMetadata(f.root, "package-a", f.context, v.generation-1, *bytes.value, cancelled).state == CustodyCommitState::committed);
    };
    const auto open = [&](const Fixture& f) { return ProtectedCustodyPackagePair::read(f.root, "package-a", f.context, cancelled); };
    for (unsigned schema : {1U, 2U}) {
        Fixture f(CustodyRole::packageState, L"package-state");
        commit(f, value(f, schema, 1, 1), true);
        {
            inject(FileFault::none); auto pair = open(f); assert(pair.ok());
            assert(pair.value->get()->selectedSlot() == 0 && pair.value->get()->current().generation == 1);
            assert(pair.value->get()->slots()[0].generation == 1 && pair.value->get()->slots()[1].generation == 1);
            assert(pair.value->get()->indices().indices[0].logicalLength == 65536);
            assert(!f.open(CustodyFileAccess::writeExisting).ok());
            auto held = *pair.value; pair.value.reset(); assert(!f.open(CustodyFileAccess::writeExisting).ok());
            assert(writes == 0 && renames == 0 && flushes == 0 && searches == 0 && diskChecks == 0);
            held.reset(); assert(f.open(CustodyFileAccess::writeExisting).ok());
        }
        commit(f, value(f, schema, 2, 2)); commit(f, value(f, schema, 3, 3));
        {
            const auto artifacts = writerArtifacts(f); inject(FileFault::none);
            auto pair = open(f); assert(pair.ok() && pair.value->get()->selectedSlot() == 0);
            const auto& slots = pair.value->get()->slots();
            assert(slots[0].generation == 3 && slots[1].generation == 2);
            assert(slots[0].refs[0].objectId[0] == 3 && slots[1].refs[0].objectId[0] == 2);
            assert(pair.value->get()->indices().indices[1].generation == 2);
            assert(writes == 0 && renames == 0 && flushes == 0 && writerArtifacts(f) == artifacts);
        }
        // Two native identity reads, then paired index/DATA reads, then each
        // package payload read. Never confuse IO failure with forged identity.
        for (unsigned ordinal : {1U, 2U, 3U, 4U, 5U, 6U, 7U, 8U}) {
            const auto artifacts = writerArtifacts(f); inject(FileFault::readFailed, ordinal);
            const auto failed = open(f);
            assert(!failed.ok() && failed.error == CustodyFileError::ioFailed && failed.nativeError == ERROR_READ_FAULT);
            assert(writes == 0 && renames == 0 && flushes == 0 && writerArtifacts(f) == artifacts);
        }
        inject(FileFault::none);
        for (unsigned ordinal : {6U, 7U, 8U}) {
            afterRead = [&] { if (reads == ordinal) cancelled->store(true); };
            inject(FileFault::none); const auto denied = open(f); afterRead = {}; cancelled->store(false);
            assert(!denied.ok() && denied.nativeError == ERROR_OPERATION_ABORTED && writes == 0 && renames == 0);
        }
        cancelled->store(true); inject(FileFault::none);
        assert(open(f).nativeError == ERROR_OPERATION_ABORTED && opens == 0);
        cancelled->store(false);
        for (const auto fault : {FileFault::hashCreate, FileFault::allocation}) {
            inject(fault); const auto denied = open(f);
            assert(!denied.ok() && denied.error == (fault == FileFault::allocation ? CustodyFileError::allocationFailed : CustodyFileError::hashFailed));
            assert(writes == 0 && renames == 0);
        }
        inject(FileFault::none);
        {
            std::array<CustodyPin, 32> pins;
            assert(open(f).error == CustodyFileError::allocationFailed && opens == 0);
        }
        {
            std::array<CustodyNativeJob, 4> jobs;
            assert(open(f).error == CustodyFileError::allocationFailed && opens == 0);
        }
        {
            CustodyBytes pressure; pressure.reserve(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes());
            assert(open(f).error == CustodyFileError::allocationFailed && writes == 0);
        }
        assert(open(f).ok());
        auto wrong = f.context; wrong.objectId[0] ^= 1;
        assert(ProtectedCustodyPackagePair::read(f.root, "package-a", wrong, cancelled).error == CustodyFileError::identityMismatch);
        wrong = f.context; wrong.role = CustodyRole::canonical;
        assert(ProtectedCustodyPackagePair::read(f.root, "package-a", wrong, cancelled).error == CustodyFileError::invalidInput);
        assert(ProtectedCustodyPackagePair::read(f.root, "../outside", f.context, cancelled).error == CustodyFileError::invalidInput);
        assert(ProtectedCustodyPackagePair::read(f.root, "package-a", f.context, {}).error == CustodyFileError::invalidInput);
        commit(f, value(f, schema, 4, 4)); assert(open(f).value->get()->current().generation == 4);
    }
    for (unsigned bad : {0U, 1U, 2U, 3U}) {
        Fixture f(CustodyRole::packageState, L"package-state");
        auto bytes = writeCustodyPackage(value(f, 2, 1, 1), f.context, 1, "package-a"); assert(bytes.ok());
        if (bad == 0) (*bytes.value)[0] = '['; // Authenticated but malformed LOWER payload.
        if (bad == 1) { const std::string text(bytes.value->begin(), bytes.value->end());
            const auto at = text.find("\"generation\":1"); assert(at != std::string::npos); (*bytes.value)[at+13] = '2'; }
        assert(commitProtectedCustodyMetadata(f.root, "package-a", f.context, 0, *bytes.value, cancelled).state == CustodyCommitState::committed);
        commit(f, value(f, 2, 2, 2));
        if (bad == 2) assert(DeleteFileW((f.object()/L"index.0").c_str()));
        if (bad == 3) assert(DeleteFileW((f.object()/L"block.0.1").c_str()));
        const auto artifacts = writerArtifacts(f); inject(FileFault::none);
        const auto failed = open(f); assert(!failed.ok());
        assert(writes == 0 && renames == 0 && flushes == 0 && writerArtifacts(f) == artifacts);
    }
    {
        Fixture f(CustodyRole::packageState, L"package-state");
        auto files = f.open(CustodyFileAccess::createNew); assert(files.ok());
        CustodyIndex zero{1, 64, {{0, 0, 1}}}; publish(f, **files.value, 0, zero); publish(f, **files.value, 1, zero);
        files.value.reset(); assert(!open(f).ok());
    }
    inject(FileFault::none); assert(CustodyOwnedMemory::usedBytes() == before);
}
void sealedFlatMembers() {
    inject(FileFault::none);
    const auto before = CustodyOwnedMemory::usedBytes();
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    for (unsigned schema : {1U, 2U}) for (std::size_t count : {0U, 1U, 65536U, 65537U}) {
        Fixture f(CustodyRole::packageState, L"package-state");
        auto member = f.context; member.role = CustodyRole::media; member.objectId[0] = 42;
        CustodyBytes plain(count, 0x57);
        const auto digest = custody_detail::digest(plain.data(), plain.size()); assert(digest);
        CustodyBytes nextPlain(count, 0x58);
        const auto nextDigest = custody_detail::digest(nextPlain.data(), nextPlain.size()); assert(nextDigest);
        {
            auto files = ProtectedCustodyFiles::open(f.root, "package-a", member, CustodyFileAccess::createNew); assert(files.ok());
            for (std::uint64_t generation : {1ULL, 2ULL}) {
                CustodyIndex index{generation, count, {}};
                if (count) {
                    auto cipher = ProtectedCustodyCodec::sealBlock(member, 0, generation, generation == 1 ? plain : nextPlain); assert(cipher.ok());
                    auto written = (*files.value)->writeBlock(0, generation, static_cast<std::uint32_t>(count), *cipher.value); assert(written.ok());
                    index.entries.push_back({generation, *written.value, 0});
                }
                auto cipher = ProtectedCustodyCodec::sealIndex(member, static_cast<std::uint32_t>(generation-1), index); assert(cipher.ok());
                assert((*files.value)->publishIndex(static_cast<std::uint32_t>(generation-1), *cipher.value).state == CustodyPublishState::published);
            }
        }
        const auto commit = [&](std::uint64_t generation, std::uint64_t memberGeneration, unsigned fault = 0) {
            CustodyPackageValue v; v.schema = schema; v.context = f.context; v.generation = generation;
            const std::string directory = "package-a"; std::copy(directory.begin(), directory.end(), v.directory.begin());
            v.phase = CustodyPackagePhase::sealedDegraded; v.reason = ReasonCode::clockDiscontinuity;
            v.refCount = 1; auto& ref = v.refs[0]; ref.role = member.role; ref.objectId = member.objectId;
            ref.sealed = true; ref.generation = memberGeneration; ref.length = count; ref.sha256 = memberGeneration == 1 ? *digest : *nextDigest;
            if (fault == 1) ref.sha256->at(0) ^= 1;
            if (fault == 2) ++*ref.length;
            if (fault == 3) ref.objectId[0] ^= 1;
            auto bytes = writeCustodyPackage(v, f.context, generation, directory); assert(bytes.ok());
            assert(commitProtectedCustodyMetadata(f.root, directory, f.context, generation-1, *bytes.value, cancelled).state == CustodyCommitState::committed);
        };
        commit(1, 1); commit(2, 2);
        const auto pair = [&] { auto p = ProtectedCustodyPackagePair::read(f.root, "package-a", f.context, cancelled); assert(p.ok()); return std::move(*p.value); };
        {
            auto held = pair(); inject(FileFault::none);
            {
                auto batch = openProtectedCustodyReaders(f.root, held, cancelled); assert(batch.ok());
                for (unsigned slot : {0U, 1U}) {
                    std::uint8_t byte = 0; ULONG got = 99;
                    assert((*batch.value)[slot][0].stream->Read(&byte, 1, &got) == (count ? S_OK : S_FALSE));
                    assert(got == (count ? 1U : 0U) && (!count || byte == (slot == 0 ? 0x57 : 0x58)));
                    assert(!(*batch.value)[slot][1].stream);
                } // Both generations coexist under ONE physical role owner.
            }
            assert(openProtectedCustodyReader(f.root, held, 2, 0, cancelled).error == CustodyFileError::invalidInput);
            assert(openProtectedCustodyReader(f.root, held, 0, 1, cancelled).error == CustodyFileError::invalidInput);
            assert(openProtectedCustodyReader(f.root, std::shared_ptr<const ProtectedCustodyPackagePair>{}, 0, 0, cancelled).error == CustodyFileError::invalidInput);
            {
                std::array<CustodyNativeJob, 4> jobs;
                assert(openProtectedCustodyReader(f.root, held, 0, 0, cancelled).error == CustodyFileError::allocationFailed);
            }
            for (unsigned slot : {0U, 1U}) {
                auto opened = openProtectedCustodyReader(f.root, held, slot, 0, cancelled); assert(opened.ok());
                STATSTG stat{}; assert(opened.value->stream->Stat(&stat, STATFLAG_NONAME) == S_OK && stat.cbSize.QuadPart == count);
                std::uint8_t byte = 0; ULONG got = 99;
                assert(opened.value->stream->Read(&byte, 1, &got) == (count ? S_OK : S_FALSE));
                assert(got == (count ? 1U : 0U) && (!count || byte == (slot == 0 ? 0x57 : 0x58))); // Exact old/new bytes, rewound after full hash.
                assert(opened.value->stream->Write(&byte, 1, &got) == STG_E_ACCESSDENIED);
            }
            auto opened = openProtectedCustodyReader(f.root, held, 0, 0, cancelled); assert(opened.ok());
            Microsoft::WRL::ComPtr<IStream> clone;
            assert(opened.value->stream->Clone(&clone) == S_OK);
            held.reset(); opened.value.reset();
            assert(!f.open(CustodyFileAccess::writeExisting).ok());
            assert(!ProtectedCustodyFiles::open(f.root, "package-a", member, CustodyFileAccess::writeExisting).ok());
            clone.Reset(); assert(f.open(CustodyFileAccess::writeExisting).ok());
            assert(ProtectedCustodyFiles::open(f.root, "package-a", member, CustodyFileAccess::writeExisting).ok());
            assert(writes == 0 && renames == 0 && flushes == 0);
        }
        for (unsigned fault = 1; fault <= 3; ++fault) {
            commit(fault+2, 2, fault); auto held = pair();
            const auto failed = openProtectedCustodyReader(f.root, held, static_cast<unsigned>((fault+1)%2), 0, cancelled);
            assert(!failed.ok() && failed.error == (fault == 3 ? CustodyFileError::identityMismatch : CustodyFileError::invalidContent));
        }
        commit(6, 3); // Unavailable actual generation is not synthesized from immutable blocks.
        // Strict batch preflight now notices the preceding wrong-ID sibling
        // before member IO. Keep that rejection AND the clean unavailable-index regression.
        { auto held = pair(); assert(openProtectedCustodyReader(f.root, held, 1, 0, cancelled).error == CustodyFileError::identityMismatch); }
        commit(7, 2); commit(8, 3);
        { auto held = pair(); assert(openProtectedCustodyReader(f.root, held, 1, 0, cancelled).error == CustodyFileError::recoveryRequired); }
        commit(9, 1);
        if (count) {
            assert(DeleteFileW((f.root/L"package-a"/L".custody-v1"/L"media"/L"block.0.2").c_str()));
            auto held = pair(); const auto failed = openProtectedCustodyReader(f.root, held, 0, 0, cancelled);
            assert(!failed.ok() && failed.error == CustodyFileError::ioFailed && failed.nativeError == ERROR_FILE_NOT_FOUND);
        } // Bad other slot keeps the original cause; no healthy-member partial result.
        assert(DeleteFileW((f.root/L"package-a"/L".custody-v1"/L"media"/L"index.1").c_str()));
        { auto held = pair(); assert(openProtectedCustodyReader(f.root, held, 0, 0, cancelled).error == CustodyFileError::recoveryRequired); }
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}
void sealedPackageGroup() {
    inject(FileFault::none);
    const auto before = CustodyOwnedMemory::usedBytes();
    Fixture f(CustodyRole::packageState, L"package-state");
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    std::array<CustodyContext, 5> contexts;
    for (unsigned role = 0; role < 5; ++role) {
        contexts[role] = {f.context.storeId, f.context.objectId, static_cast<CustodyRole>(role+1)};
        contexts[role].objectId[0] = static_cast<std::uint8_t>(role+42);
        auto files = ProtectedCustodyFiles::open(f.root, "package-a", contexts[role], CustodyFileAccess::createNew); assert(files.ok());
        for (std::uint64_t generation : {1ULL, 2ULL}) {
            CustodyBytes plain{static_cast<std::uint8_t>(role+generation)};
            auto cipher = ProtectedCustodyCodec::sealBlock(contexts[role], 0, generation, plain); assert(cipher.ok());
            auto block = (*files.value)->writeBlock(0, generation, 1, *cipher.value); assert(block.ok());
            CustodyIndex index{generation, 1, {{generation, *block.value, 0}}};
            const auto publishAt = [&](unsigned slot) {
                auto encoded = ProtectedCustodyCodec::sealIndex(contexts[role], slot, index); assert(encoded.ok());
                assert((*files.value)->publishIndex(slot, *encoded.value).state == CustodyPublishState::published);
            };
            publishAt(static_cast<unsigned>(generation-1));
            if (role >= 3 && generation == 1) publishAt(1); // Manifest/recovery metadata birth BOTH.
        }
    }
    const auto commit = [&](std::uint64_t generation, unsigned fault = 0) {
        CustodyPackageValue v; v.context = f.context; v.generation = generation;
        const std::string directory = "package-a"; std::copy(directory.begin(), directory.end(), v.directory.begin());
        v.phase = CustodyPackagePhase::sealedDegraded; v.reason = ReasonCode::clockDiscontinuity; v.refCount = 5;
        for (unsigned i = 0; i < 5; ++i) {
            const unsigned role = generation == 1 ? i : 4-i; // Physical slot order is not role order.
            auto& ref = v.refs[i]; ref.role = contexts[role].role; ref.objectId = contexts[role].objectId;
            ref.sealed = true; ref.generation = generation == 1 ? 1 : 2; ref.length = 1;
            const std::uint8_t byte = static_cast<std::uint8_t>(role+*ref.generation);
            ref.sha256 = custody_detail::digest(&byte, 1); assert(ref.sha256);
        }
        if (fault == 1) v.refs[0].sha256->at(0) ^= 1; // Recovery: nonrequested sibling after canonical serialization.
        if (fault == 5) v.refs[4].sha256->at(0) ^= 1; // Canonical will exist only in the lower slot.
        if (fault == 3) v.refCount = 3; // Old slot alone retains canonical/media.
        if (fault == 4) {
            v.schema = 2;
            auto& ref = v.refs[4]; assert(ref.role == CustodyRole::canonical);
            ref.packed = true; ref.containerId = contexts[0].objectId;
            ref.generation = 1; ref.length = 0; ref.sha256 = custody_detail::digest(nullptr, 0);
            ref.committedExtent = ProtectedPackedCustodyFormat::appendOffset;
            ref.rootRef = ProtectedPackedCustodyFormat::encodeReference(PackedReference{}); assert(ref.rootRef);
        }
        if (fault == 2) {
            v.phase = CustodyPackagePhase::capturing; v.reason = ReasonCode::none; v.refCount = 1;
            v.refs[0] = {}; v.refs[0].role = CustodyRole::canonical; v.refs[0].objectId = contexts[0].objectId;
        }
        auto bytes = writeCustodyPackage(v, f.context, generation, directory); assert(bytes.ok());
        if (generation == 2) {
            // The production serializer sorts roles. Supply a valid reversed
            // wire array to test the reader's actual ordinal/role distinction.
            const std::string json(bytes.value->begin(), bytes.value->end());
            auto at = json.find("\"refs\":["); assert(at != std::string::npos); at += 8;
            std::string reversed = json.substr(0, at); std::array<std::string, 5> objects;
            for (auto& object : objects) { const auto end = json.find('}', at); assert(end != std::string::npos); object = json.substr(at, end-at+1); at = end+2; }
            for (auto i = objects.rbegin(); i != objects.rend(); ++i) { if (i != objects.rbegin()) reversed += ','; reversed += *i; }
            reversed += "]}"; bytes.value->assign(reversed.begin(), reversed.end());
        }
        assert(commitProtectedCustodyMetadata(f.root, directory, f.context, generation-1, *bytes.value, cancelled).state == CustodyCommitState::committed);
    };
    commit(1); commit(2);
    {
        auto held = ProtectedCustodyPackagePair::read(f.root, "package-a", f.context, cancelled); assert(held.ok());
        assert((*held.value)->slots()[1].refs[0].role == CustodyRole::recovery && (*held.value)->slots()[1].refs[4].role == CustodyRole::canonical);
        {
            std::array<CustodyPin, 32> pressure; inject(FileFault::none);
            assert(openProtectedCustodyReaders(f.root, *held.value, cancelled).error == CustodyFileError::allocationFailed && opens == 0 && reads == 0);
        }
        {
            std::array<CustodyNativeJob, 4> pressure; inject(FileFault::none);
            assert(openProtectedCustodyReaders(f.root, *held.value, cancelled).error == CustodyFileError::allocationFailed && opens == 0 && reads == 0);
        }
        {
            CustodyBytes pressure; pressure.reserve(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes()); inject(FileFault::none);
            assert(openProtectedCustodyReaders(f.root, *held.value, cancelled).error == CustodyFileError::allocationFailed && opens == 0 && reads == 0);
        }
        auto batch = openProtectedCustodyReaders(f.root, *held.value, cancelled); assert(batch.ok());
        for (unsigned slot : {0U, 1U}) for (unsigned i = 0; i < 5; ++i) {
            std::uint8_t byte = 0; ULONG got = 0;
            assert((*batch.value)[slot][i].stream->Read(&byte, 1, &got) == S_OK && got == 1);
            const auto& ref = held.value->get()->slots()[slot].refs[i];
            assert(byte == static_cast<unsigned>(ref.role)-1+*ref.generation);
        }
        Microsoft::WRL::ComPtr<IStream> clone;
        assert((*batch.value)[0][0].stream->Clone(&clone) == S_OK);
        LARGE_INTEGER zero{};
        assert((*batch.value)[0][0].stream->Seek(zero, STREAM_SEEK_SET, nullptr) == S_OK);
        inject(FileFault::readFailed); flushOrdinal = 1;
        std::uint8_t byte = 0; ULONG got = 99;
        const auto firstFault = HRESULT_FROM_WIN32(ERROR_READ_FAULT);
        assert((*batch.value)[0][0].stream->Read(&byte, 1, &got) == firstFault && got == 0);
        cancelled->store(true);
        assert((*batch.value)[1][1].stream->Read(&byte, 1, &got) == firstFault && got == 0);
        assert(clone->Read(&byte, 1, &got) == firstFault && got == 0); // Shared fault wins over late cancel.
        cancelled->store(false); inject(FileFault::none);
        held.value.reset(); batch.value.reset();
        assert(!f.open(CustodyFileAccess::writeExisting).ok());
        for (const auto& context : contexts)
            assert(!ProtectedCustodyFiles::open(f.root, "package-a", context, CustodyFileAccess::writeExisting).ok());
        clone.Reset(); assert(f.open(CustodyFileAccess::writeExisting).ok());
        for (const auto& context : contexts)
            assert(ProtectedCustodyFiles::open(f.root, "package-a", context, CustodyFileAccess::writeExisting).ok());
    }
    commit(3, 3);
    {
        auto held = ProtectedCustodyPackagePair::read(f.root, "package-a", f.context, cancelled); assert(held.ok());
        auto batch = openProtectedCustodyReaders(f.root, *held.value, cancelled); assert(batch.ok());
        assert(!(*batch.value)[0][3].stream && !(*batch.value)[0][4].stream && (*batch.value)[1][4].stream);
        Microsoft::WRL::ComPtr<IStream> clone; assert((*batch.value)[0][0].stream->Clone(&clone) == S_OK);
        held.value.reset(); batch.value.reset();
        for (unsigned role : {0U, 1U})
            assert(!ProtectedCustodyFiles::open(f.root, "package-a", contexts[role], CustodyFileAccess::writeExisting).ok());
        clone.Reset();
    }
    commit(4, 1);
    {
        auto held = ProtectedCustodyPackagePair::read(f.root, "package-a", f.context, cancelled); assert(held.ok());
        assert(openProtectedCustodyReaders(f.root, *held.value, cancelled).error == CustodyFileError::invalidContent);
        assert(openProtectedCustodyReader(f.root, *held.value, 1, 0, cancelled).error == CustodyFileError::invalidContent);
    }
    commit(5, 2);
    {
        auto held = ProtectedCustodyPackagePair::read(f.root, "package-a", f.context, cancelled); assert(held.ok());
        inject(FileFault::none);
        // LIVE is now supported, but the preceding slot's bad sealed SHA still
        // rejects the whole group, including the otherwise healthy target.
        assert(openProtectedCustodyReaders(f.root, *held.value, cancelled).error == CustodyFileError::invalidContent && reads > 0 && opens > 0);
        assert(openProtectedCustodyReader(f.root, *held.value, 1, 0, cancelled).error == CustodyFileError::invalidContent);
    }
    commit(6); commit(7, 4);
    {
        auto held = ProtectedCustodyPackagePair::read(f.root, "package-a", f.context, cancelled); assert(held.ok());
        inject(FileFault::none);
        const auto batch = openProtectedCustodyReaders(f.root, *held.value, cancelled);
        assert(!batch.value && batch.error == CustodyFileError::identityMismatch && reads == 0 && opens == 0);
        const auto single = openProtectedCustodyReader(f.root, *held.value, 0, 1, cancelled); // Healthy selected media.
        assert(!single.value && single.error == CustodyFileError::identityMismatch && reads == 0 && opens == 0);
    }
    commit(8, 5); commit(9, 3);
    {
        auto held = ProtectedCustodyPackagePair::read(f.root, "package-a", f.context, cancelled); assert(held.ok());
        assert((*held.value)->selectedSlot() == 0 && (*held.value)->current().refCount == 3);
        const auto batch = openProtectedCustodyReaders(f.root, *held.value, cancelled);
        assert(!batch.value && batch.error == CustodyFileError::invalidContent);
        const auto single = openProtectedCustodyReader(f.root, *held.value, 0, 0, cancelled); // Healthy selected playback.
        assert(!single.value && single.error == CustodyFileError::invalidContent);
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}
void livePackageGroup() {
    inject(FileFault::none);
    const auto before = CustodyOwnedMemory::usedBytes();
    for (unsigned fault = 0; fault < 5; ++fault) {
        Fixture f(CustodyRole::packageState, L"package-state");
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        std::array<CustodyContext, 4> contexts;
        for (unsigned role = 0; role < 4; ++role) {
            contexts[role] = {f.context.storeId, f.context.objectId, static_cast<CustodyRole>(role+1)};
            contexts[role].objectId[0] = static_cast<std::uint8_t>(role+42);
            auto files = ProtectedCustodyFiles::open(f.root, "package-a", contexts[role], CustodyFileAccess::createNew); assert(files.ok());
            for (const auto generation : {2ULL, 3ULL}) {
                const CustodyBytes plain = generation == 2 ? CustodyBytes{1, 2, 3} : CustodyBytes{8, 9, 10, 11, 12};
                auto cipher = ProtectedCustodyCodec::sealBlock(contexts[role], 0, generation, plain); assert(cipher.ok());
                auto block = (*files.value)->writeBlock(0, generation, static_cast<std::uint32_t>(plain.size()), *cipher.value); assert(block.ok());
                CustodyIndex index{generation, plain.size(), {{generation, *block.value, 0}}};
                const auto slot = static_cast<unsigned>((generation-1)%2);
                auto encoded = ProtectedCustodyCodec::sealIndex(contexts[role], slot, index); assert(encoded.ok());
                assert((*files.value)->publishIndex(slot, *encoded.value).state == CustodyPublishState::published);
            }
        }
        const auto commit = [&](std::uint64_t generation, CustodyPackagePhase phase, bool badHash = false) {
            CustodyPackageValue v; v.context = f.context; v.generation = generation; v.phase = phase;
            const std::string directory = "package-a"; std::copy(directory.begin(), directory.end(), v.directory.begin());
            const bool live = phase == CustodyPackagePhase::capturing || phase == CustodyPackagePhase::finalizing;
            const bool normal = phase == CustodyPackagePhase::sealedNormal;
            v.reason = live || normal ? ReasonCode::none : ReasonCode::clockDiscontinuity;
            v.refCount = normal ? 3 : 1;
            for (unsigned i = 0; i < v.refCount; ++i) {
                const auto role = normal ? i+1 : 0;
                auto& ref = v.refs[i]; ref.role = contexts[role].role; ref.objectId = contexts[role].objectId;
                if (!live) {
                    ref.sealed = true; ref.generation = 2; ref.length = 3;
                    const CustodyBytes bytes{1, 2, 3}; ref.sha256 = custody_detail::digest(bytes.data(), bytes.size()); assert(ref.sha256);
                    if (badHash) ref.sha256->at(0) ^= 1;
                }
                if (fault == 4 && !live && !normal) ref.objectId[0] ^= 0x40;
            }
            auto bytes = writeCustodyPackage(v, f.context, generation, directory); assert(bytes.ok());
            assert(commitProtectedCustodyMetadata(f.root, directory, f.context, generation-1, *bytes.value, cancelled).state == CustodyCommitState::committed);
        };
        commit(1, CustodyPackagePhase::capturing); // Initial BOTH metadata slots are LIVE.
        if (!fault) {
            auto held = ProtectedCustodyPackagePair::read(f.root, "package-a", f.context, cancelled); assert(held.ok());
            auto batch = openProtectedCustodyReaders(f.root, *held.value, cancelled); assert(batch.ok());
            for (unsigned slot : {0U, 1U}) {
                STATSTG stat{}; assert((*batch.value)[slot][0].stream->Stat(&stat, STATFLAG_NONAME) == S_OK && stat.cbSize.QuadPart == 5);
                std::array<std::uint8_t, 6> bytes{}; ULONG got = 0;
                assert((*batch.value)[slot][0].stream->Read(bytes.data(), 6, &got) == S_FALSE && got == 5 && bytes[0] == 8);
                assert(openProtectedCustodyReader(f.root, *held.value, slot, 0, cancelled).error == CustodyFileError::invalidInput);
            }
        }
        commit(2, CustodyPackagePhase::sealedDegraded, fault == 3);
        const auto canonical = f.root/L"package-a"/L".custody-v1"/L"canonical";
        if (fault == 1) assert(DeleteFileW((canonical/L"block.0.3").c_str())); // LIVE current DATA, healthy sealed peer.
        if (fault == 2) assert(DeleteFileW((canonical/L"index.0").c_str())); // Singleton verified is NOT BOTH authority.
        {
            auto held = ProtectedCustodyPackagePair::read(f.root, "package-a", f.context, cancelled); assert(held.ok());
            inject(FileFault::none);
            auto batch = openProtectedCustodyReaders(f.root, *held.value, cancelled);
            if (fault) {
                assert(!batch.value && batch.error == (fault == 1 ? CustodyFileError::ioFailed : fault == 2 ? CustodyFileError::recoveryRequired
                    : fault == 3 ? CustodyFileError::invalidContent : CustodyFileError::identityMismatch));
                if (fault == 1) assert(batch.nativeError == ERROR_FILE_NOT_FOUND);
                if (fault == 4) assert(opens == 0 && reads == 0); // Identity preflight still precedes IO.
                assert(writes == 0 && flushes == 0 && renames == 0);
                continue;
            }
            assert(batch.ok());
            for (unsigned slot : {0U, 1U}) {
                std::array<std::uint8_t, 6> bytes{}; ULONG got = 0;
                assert((*batch.value)[slot][0].stream->Read(bytes.data(), 6, &got) == S_FALSE);
                assert(got == (slot ? 3U : 5U) && bytes[0] == (slot ? 1 : 8)); // LIVE highest; SEALED exact older g2.
                ULARGE_INTEGER size{}; assert((*batch.value)[slot][0].stream->SetSize(size) == STG_E_ACCESSDENIED);
                assert((*batch.value)[slot][0].stream->Write(bytes.data(), 1, &got) == STG_E_ACCESSDENIED && got == 0);
            }
            batch.value.reset(); // Independent factory must not reopen an already exclusively held role.
            auto single = openProtectedCustodyReader(f.root, *held.value, 1, 0, cancelled); assert(single.ok());
            assert(writes == 0 && flushes == 0 && renames == 0);
        }
        commit(3, CustodyPackagePhase::finalizing); // Same live/sealed transition, opposite physical order.
        {
            auto held = ProtectedCustodyPackagePair::read(f.root, "package-a", f.context, cancelled); assert(held.ok());
            auto batch = openProtectedCustodyReaders(f.root, *held.value, cancelled); assert(batch.ok());
        }
        commit(4, CustodyPackagePhase::sealedNormal); // Old LIVE canonical is lower-slot-only, never erased.
        {
            auto held = ProtectedCustodyPackagePair::read(f.root, "package-a", f.context, cancelled); assert(held.ok());
            auto batch = openProtectedCustodyReaders(f.root, *held.value, cancelled); assert(batch.ok());
            assert((*held.value)->current().phase == CustodyPackagePhase::sealedNormal && !(*batch.value)[0][1].stream);
            Microsoft::WRL::ComPtr<IStream> clone; assert((*batch.value)[1][0].stream->Clone(&clone) == S_OK);
            inject(FileFault::readFailed);
            std::uint8_t byte = 0; ULONG got = 99;
            const auto firstFault = HRESULT_FROM_WIN32(ERROR_READ_FAULT);
            assert((*batch.value)[0][0].stream->Read(&byte, 1, &got) == firstFault && got == 0);
            cancelled->store(true);
            assert(clone->Read(&byte, 1, &got) == firstFault && got == 0);
            inject(FileFault::none); cancelled->store(false);
            held.value.reset(); batch.value.reset();
            assert(!f.open(CustodyFileAccess::writeExisting).ok());
            for (const auto& context : contexts)
                assert(!ProtectedCustodyFiles::open(f.root, "package-a", context, CustodyFileAccess::writeExisting).ok());
            clone.Reset(); assert(f.open(CustodyFileAccess::writeExisting).ok());
            for (const auto& context : contexts)
                assert(ProtectedCustodyFiles::open(f.root, "package-a", context, CustodyFileAccess::writeExisting).ok());
        }
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}
CustodyPackageReference protectRecordingMember(Fixture& f, CustodyRole role, const CustodyBytes& bytes,
    const std::shared_ptr<std::atomic<bool>>& cancelled) {
    CustodyPackageReference ref; ref.role = role; ref.objectId[0] = static_cast<std::uint8_t>(40+static_cast<unsigned>(role)); ref.sealed = true;
    const CustodyContext context{f.context.storeId,ref.objectId,role};
    const bool audio = static_cast<unsigned>(role) <= static_cast<unsigned>(CustodyRole::playback);
    if (audio) {
        auto writer = ProtectedCustodyWriter::open(f.root,"package-a",context,0,cancelled); assert(writer.ok());
        assert((*writer.value)->writeAt(0,bytes.data(),bytes.size()).ok());
        assert((*writer.value)->checkpoint().state == CustodyCommitState::committed);
        assert((*writer.value)->writeAt(0,bytes.data(),1).ok());
        assert((*writer.value)->checkpoint().state == CustodyCommitState::committed);
    } else assert(commitProtectedCustodyMetadata(f.root,"package-a",context,0,bytes,cancelled).state == CustodyCommitState::committed);
    ref.generation = audio ? 2 : 1; ref.length = bytes.size(); ref.sha256 = custody_detail::digest(bytes.data(),bytes.size()); assert(ref.sha256);
    return ref;
}
void protectedPlayback() {
    inject(FileFault::none);
    const auto before = CustodyOwnedMemory::usedBytes();
    for (const auto& sampleCase : std::array<std::pair<bool, unsigned>, 3>{{{false, 1000}, {true, 1000}, {false, 30'000}}}) {
        const auto damaged = sampleCase.first;
        const auto durationMs = sampleCase.second;
        Fixture f(CustodyRole::packageState, L"package-state");
        auto cancelled = std::make_shared<std::atomic<bool>>(false);
        const auto plain = f.root / L"generated-audio";
        const auto encoded = testing::makeGeneratedLegacyPackage(plain, durationMs/10);
        assert(encoded.durationMs == durationMs);
        CustodyPackageValue package; package.context = f.context; package.generation = 1;
        package.phase = CustodyPackagePhase::sealedNormal; package.refCount = 3;
        const std::string directory = "package-a";
        std::copy(directory.begin(), directory.end(), package.directory.begin());
        const std::array<const wchar_t*, 3> names{L"meeting-transcription.wav", L"meeting-review.m4a", L"manifest.json"};
        for (unsigned i = 0; i < names.size(); ++i) {
            std::ifstream input(plain / names[i], std::ios::binary); assert(input);
            const std::vector<char> fixture{std::istreambuf_iterator<char>(input), {}};
            CustodyBytes bytes(fixture.begin(), fixture.end());
            if (damaged && i == 1) {
                // Test-only MP4 mutation, preserving all header/sample tables.
                const auto big = [&](std::size_t at, unsigned count) {
                    assert(at <= bytes.size() && count <= bytes.size()-at);
                    std::uint64_t n = 0; for (unsigned j = 0; j < count; ++j) n = (n << 8) | bytes[at+j]; return n;
                };
                bool changed = false;
                for (std::size_t at = 0; at < bytes.size();) {
                    assert(bytes.size()-at >= 8);
                    auto size = big(at, 4); const auto header = size == 1 ? 16U : 8U;
                    if (size == 1) size = big(at+8, 8);
                    if (size == 0) size = bytes.size()-at;
                    assert(size >= header && size <= bytes.size()-at);
                    if (std::memcmp(bytes.data()+at+4, "mdat", 4) == 0) {
                        assert(size > header);
                        std::fill(bytes.begin()+static_cast<std::ptrdiff_t>(at+header),
                            bytes.begin()+static_cast<std::ptrdiff_t>(at+size), std::uint8_t{255}); changed = true;
                    }
                    at += static_cast<std::size_t>(size);
                }
                assert(changed);
            }
            if (damaged && i == 2) {
                // The semantic counterexample also has a correct manifest SHA.
                // A descriptor mismatch must not stand in for real AAC rejection.
                std::string json(bytes.begin(), bytes.end());
                const auto at = json.find(encoded.playbackSha256); assert(at != std::string::npos);
                std::string hash;
                for (auto byte : *package.refs[1].sha256) { hash += "0123456789abcdef"[byte >> 4]; hash += "0123456789abcdef"[byte & 15]; }
                json.replace(at, 64, hash); bytes.assign(json.begin(), json.end());
            }
            package.refs[i] = protectRecordingMember(f,static_cast<CustodyRole>(i+2),bytes,cancelled);
        }
        const auto metadata = writeCustodyPackage(package, f.context, 1, directory); assert(metadata.ok());
        assert(commitProtectedCustodyMetadata(f.root, directory, f.context, 0, *metadata.value, cancelled).state == CustodyCommitState::committed);
        auto pair = ProtectedCustodyPackagePair::read(f.root, directory, f.context, cancelled); assert(pair.ok());
        auto semantic = LocalRecordingPackage::inspectProtected(f.root, *pair.value, "synthetic-session", cancelled);
        if (damaged) assert(!semantic.ok() && semantic.error == CustodyFileError::invalidContent);
        else {
            assert(semantic.ok());
            assert((*semantic.value)->evidence().integrity == PackageIntegrity::valid);
            assert((*semantic.value)->evidence().durationMs == durationMs);
            assert(!(*semantic.value)->evidence().manifestSessionMatched); // Known no-session Windows legacy.
            assert(!ProtectedCustodyFiles::open(f.root, directory,
                {f.context.storeId, package.refs[0].objectId, CustodyRole::media}, CustodyFileAccess::writeExisting).ok());
        }
        semantic.value.reset();
        const auto result = LocalRecordingPackage::readProtectedPlayback(f.root, *pair.value, durationMs, cancelled);
        std::printf("protected-aac damaged=%u duration_ms=%u accepted=%u error=%u native=0x%08x frames=%llu\n",
            static_cast<unsigned>(damaged), durationMs, static_cast<unsigned>(result.ok()), static_cast<unsigned>(result.error),
            result.nativeError, static_cast<unsigned long long>(result.ok() ? result.value->decodedFrames : 0));
        std::fflush(stdout);
        if (damaged) assert(!result.ok() && result.error == CustodyFileError::invalidContent);
        else {
            assert(result.ok() && result.value->decodedFrames > 0 && result.value->decodedFrames <= (durationMs+100ULL)*48);
            assert(result.value->containerDuration100ns > 0);
            cancelled->store(true);
            assert(LocalRecordingPackage::readProtectedPlayback(f.root, *pair.value, durationMs, cancelled).nativeError == ERROR_OPERATION_ABORTED);
            cancelled->store(false);
            {
                std::array<CustodyNativeJob, 4> jobs;
                assert(LocalRecordingPackage::readProtectedPlayback(f.root, *pair.value, durationMs, cancelled).error == CustodyFileError::allocationFailed);
            }
            assert(LocalRecordingPackage::readProtectedPlayback(f.root, *pair.value, durationMs, cancelled).ok());
            inject(FileFault::none);
            auto batch = openProtectedCustodyReaders(f.root, *pair.value, cancelled); assert(batch.ok());
            const auto beforeDecoder = reads; batch.value.reset();
            inject(FileFault::none);
            afterRead = [&] { if (reads == beforeDecoder+1) cancelled->store(true); };
            const auto interrupted = LocalRecordingPackage::readProtectedPlayback(f.root, *pair.value, durationMs, cancelled);
            afterRead = {};
            assert(cancelled->load() && !interrupted.ok() && interrupted.nativeError != 0);
            cancelled->store(false); inject(FileFault::none);
            assert(LocalRecordingPackage::readProtectedPlayback(f.root, *pair.value, durationMs, cancelled).ok());
            inject(FileFault::readFailed);
            assert(!LocalRecordingPackage::readProtectedPlayback(f.root, *pair.value, durationMs, cancelled).ok());
            inject(FileFault::none);
            afterRead = [&] { if (reads == beforeDecoder+1) throw std::bad_alloc(); };
            const auto noMemory = LocalRecordingPackage::readProtectedPlayback(f.root, *pair.value, durationMs, cancelled);
            afterRead = {};
            assert(!noMemory.ok() && noMemory.error == CustodyFileError::allocationFailed);
            inject(FileFault::none);
            assert(LocalRecordingPackage::readProtectedPlayback(f.root, *pair.value, durationMs, cancelled).ok());
            // Corrupt a sibling's real encrypted DATA, not the AAC being decoded.
            const auto sibling = f.root/L"package-a"/L".custody-v1"/L"media"/L"block.0.2";
            std::fstream mutate(sibling, std::ios::in | std::ios::out | std::ios::binary); assert(mutate);
            char original = 0; mutate.read(&original, 1); assert(mutate.good());
            const auto wrong = static_cast<char>(original ^ 1);
            mutate.seekp(0); mutate.write(&wrong, 1); mutate.flush(); assert(mutate.good()); mutate.close();
            const auto badSibling = LocalRecordingPackage::readProtectedPlayback(f.root, *pair.value, durationMs, cancelled);
            assert(!badSibling.ok() && badSibling.error == CustodyFileError::invalidContent);
            assert(LocalRecordingPackage::inspectProtected(f.root,*pair.value,"synthetic-session",cancelled).error == CustodyFileError::invalidContent);
            mutate.open(sibling, std::ios::in | std::ios::out | std::ios::binary); assert(mutate);
            mutate.seekp(0); mutate.write(&original, 1); mutate.close();
            assert(LocalRecordingPackage::readProtectedPlayback(f.root, *pair.value, durationMs, cancelled).ok());
        }
        pair.value.reset();
        assert(f.open(CustodyFileAccess::writeExisting).ok());
    }
    assert(CustodyOwnedMemory::usedBytes() == before);
}
void protectedRecordingSemantics() {
    inject(FileFault::none); const auto before = CustodyOwnedMemory::usedBytes();
    {
        Fixture generated(CustodyRole::packageState,L"package-state");
        const auto normalResult = testing::makeGeneratedLegacyPackage(generated.root/L"normal", 100);
        const auto degradedResult = testing::makeGeneratedLegacyPackage(generated.root/L"degraded", 100, ReasonCode::clockDiscontinuity);
        testing::writeGeneratedPrefix(generated.root/L"prefix", 100, ReasonCode::clockDiscontinuity);
        assert(!std::filesystem::exists(generated.root/L"prefix"/L"manifest.json"));
        const auto read = [](const std::filesystem::path& path) { std::ifstream input(path,std::ios::binary); assert(input); return std::string(std::istreambuf_iterator<char>(input),{}); };
        const auto change = [](std::string text,std::string_view from,std::string_view to) { const auto at = text.find(from); assert(at != std::string::npos); text.replace(at,from.size(),to); return text; };
        const auto append = [](std::string text,std::string_view field) { assert(text.back() == '}'); text.pop_back(); text += ','; text += field; text += '}'; return text; };
        const auto base = read(normalResult.manifestPath);
        const auto normalArtifactsAt = base.find(",\"artifacts\":"); assert(normalArtifactsAt != std::string::npos);
        const auto normalWithoutArtifacts = base.substr(0,normalArtifactsAt)+"}";
        const std::string open = "{\"segmentId\":\"seg-a\",\"sessionId\":\"synthetic-session\",\"control\":\"pause\",\"startedAt\":\"2026-01-02T09:00:00Z\",\"startMonotonicMs\":100,\"durationMs\":0,\"localMicTreatment\":\"silenced\",\"initiator\":\"user\",\"diagnosticSafe\":true}";
        const auto closed = append(change(open,"\"durationMs\":0","\"durationMs\":150"),"\"endedAt\":\"2026-01-02T08:00:00Z\",\"endMonotonicMs\":250");
        const auto withSegment = [&](std::string segment) { return append(base,"\"privacySegments\":["+segment+"]"); };
        struct Case { const char* name; std::string json; bool accepted, sessionMatched = false; };
        std::vector<Case> cases{
            {"current_legacy",base,true},
            {"normal_without_artifacts",append(append(normalWithoutArtifacts,"\"sessionId\":\"synthetic-session\""),"\"privacySegments\":[]"),false},
            {"pre_status",change(base,"\"capture_status\":\"normal\",\"capture_reason_code\":\"none\",",""),true},
            {"escaped_schema_key",change(base,"schema_version","sch\\u0065ma_version"),true},
            {"session_present",append(base,"\"sessionId\":\"synthetic-session\""),true,true},
            {"session_mismatch",append(base,"\"sessionId\":\"other-session\""),false},
            {"privacy_open",withSegment(open),true},
            {"privacy_closed_wall_rollback",withSegment(closed),true},
            {"privacy_unicode",withSegment(change(open,"seg-a","\\u6bb5-\\ud83d\\ude00")),true},
            {"privacy_leap_date",withSegment(change(open,"2026-01-02","2024-02-29")),true},
            {"short_false",append(base,"\"short_recording_discarded\":false"),true},
            {"short_true",append(base,"\"short_recording_discarded\":true"),false},
            {"short_wrong_alias",append(base,"\"shortRecordingDiscarded\":false"),false},
            {"unknown_key",append(base,"\"unknown\":true"),false},
            {"decoded_duplicate_key",append(base,"\"duration_\\u006ds\":1000"),false},
            {"schema_null",change(base,"\"local-recording-manifest.v5\"","null"),false},
            {"duration_exponent",change(base,"\"duration_ms\":1000","\"duration_ms\":1e3"),false},
            {"duration_leading_zero",change(base,"\"duration_ms\":1000","\"duration_ms\":01000"),false},
            {"duration_overflow",change(base,"\"duration_ms\":1000","\"duration_ms\":18446744073709551616"),false},
            {"time_partial",change(base,"\"started_at_ms\":"+std::to_string(normalResult.startedAtMs)+",",""),false},
            {"time_impossible",change(base,"\"stopped_at_ms\":"+std::to_string(normalResult.stoppedAtMs),"\"stopped_at_ms\":1"),false},
            {"offset_outside",change(base,"\"display_timezone_offset_minutes\":"+std::to_string(normalResult.displayTimezoneOffsetMinutes),"\"display_timezone_offset_minutes\":841"),false},
            {"offset_minus_space",change(base,"\"display_timezone_offset_minutes\":"+std::to_string(normalResult.displayTimezoneOffsetMinutes),"\"display_timezone_offset_minutes\":- 1"),false},
            {"status_without_reason",change(base,"\"capture_reason_code\":\"none\",",""),false},
            {"media_descriptor_mismatch",change(base,"\"bytes\":"+std::to_string(normalResult.wavBytes),"\"bytes\":1"),false},
            {"privacy_wrong_session",withSegment(change(open,"synthetic-session","other-session")),false},
            {"privacy_end_null",withSegment(append(open,"\"endedAt\":null")),false},
            {"privacy_end_one_only",withSegment(append(open,"\"endMonotonicMs\":200")),false},
            {"privacy_open_duration",withSegment(change(open,"\"durationMs\":0","\"durationMs\":1")),false},
            {"privacy_negative",withSegment(change(open,"\"startMonotonicMs\":100","\"startMonotonicMs\":-1")),false},
            {"privacy_int64_overflow",withSegment(change(open,"\"startMonotonicMs\":100","\"startMonotonicMs\":9223372036854775808")),false},
            {"privacy_duration_mismatch",withSegment(change(closed,"\"durationMs\":150","\"durationMs\":149")),false},
            {"privacy_end_before_start",withSegment(change(closed,"\"endMonotonicMs\":250","\"endMonotonicMs\":99")),false},
            {"privacy_missing_initiator",withSegment(change(open,"\"initiator\":\"user\",","")),false},
            {"privacy_unknown_enum",withSegment(change(open,"\"pause\"","\"PAUSE\"")),false},
            {"privacy_invalid_date",withSegment(change(open,"2026-01-02","2026-02-30")),false},
            {"privacy_isolated_surrogate",withSegment(change(open,"seg-a","\\ud800")),false},
            {"privacy_invalid_escape",withSegment(change(open,"seg-a","\\uqqqq")),false},
            {"privacy_invalid_utf8",withSegment(change(open,"seg-a",std::string(1,static_cast<char>(255)))),false},
            {"privacy_decoded_duplicate_id",withSegment(open+","+change(open,"seg-a","seg-\\u0061")),false},
            {"privacy_duplicate_field",withSegment(append(open,"\"duration\\u004ds\":0")),false},
            {"privacy_bool_wrong_type",withSegment(change(open,"\"diagnosticSafe\":true","\"diagnosticSafe\":1")),false},
            {"manifest_bom",std::string("\xef\xbb\xbf")+base,false},
            {"manifest_trailing",base+"x",false}
        };
        std::string history;
        for (unsigned i = 0; i < 40; ++i) { if (i) history += ','; history += change(open,"seg-a","segment-"+std::to_string(i)); }
        const auto longManifest = withSegment(history); assert(longManifest.size() > 4096 && longManifest.size() < 65536);
        cases.push_back({"privacy_history_above_4096",longManifest,true});
        auto limitManifest = longManifest; limitManifest.append(65536-limitManifest.size(),' ');
        cases.push_back({"manifest_exact_65536",limitManifest,true});
        const std::array<std::string,2> audio{read(normalResult.wavPath),read(normalResult.playbackPath)};
        for (const auto& test : cases) {
            Fixture f(CustodyRole::packageState,L"package-state"); auto cancel = std::make_shared<std::atomic<bool>>(false);
            CustodyPackageValue package; package.context = f.context; package.generation = 1; package.phase = CustodyPackagePhase::sealedNormal;
            std::copy_n("package-a",9,package.directory.begin()); package.refCount = 3;
            for (unsigned i = 0; i < 3; ++i) { const auto& content = i == 2 ? test.json : audio[i];
                package.refs[i] = protectRecordingMember(f,static_cast<CustodyRole>(i+2),CustodyBytes(content.begin(),content.end()),cancel); }
            const auto value = writeCustodyPackage(package,f.context,1,"package-a"); assert(value.ok());
            assert(commitProtectedCustodyMetadata(f.root,"package-a",f.context,0,*value.value,cancel).state == CustodyCommitState::committed);
            auto pair = ProtectedCustodyPackagePair::read(f.root,"package-a",f.context,cancel); assert(pair.ok());
            auto result = LocalRecordingPackage::inspectProtected(f.root,*pair.value,"synthetic-session",cancel);
            std::printf("protected-v5 case=%s accepted=%u error=%u native=0x%08x\n",test.name,static_cast<unsigned>(result.ok()),static_cast<unsigned>(result.error),result.nativeError); std::fflush(stdout);
            assert(result.ok() == test.accepted);
            if (test.accepted) {
                assert((*result.value)->evidence().durationMs == 1000 && (*result.value)->evidence().manifestSessionMatched == test.sessionMatched);
                result.value.reset();
                cancel->store(true); assert(LocalRecordingPackage::inspectProtected(f.root,*pair.value,"synthetic-session",cancel).nativeError == ERROR_OPERATION_ABORTED); cancel->store(false);
                { std::array<CustodyNativeJob,4> jobs; assert(LocalRecordingPackage::inspectProtected(f.root,*pair.value,"synthetic-session",cancel).error == CustodyFileError::allocationFailed); }
                if (std::string_view(test.name) == "current_legacy") {
                    { CustodyBytes pressure; pressure.reserve(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes());
                      assert(LocalRecordingPackage::inspectProtected(f.root,*pair.value,"synthetic-session",cancel).error == CustodyFileError::allocationFailed); }
                    inject(FileFault::none); afterRead = [&] { if (reads == 1) cancel->store(true); };
                    assert(!LocalRecordingPackage::inspectProtected(f.root,*pair.value,"synthetic-session",cancel).ok());
                    afterRead = {}; cancel->store(false); inject(FileFault::none);
                }
                result = LocalRecordingPackage::inspectProtected(f.root,*pair.value,"synthetic-session",cancel); assert(result.ok());
            } else assert(result.error == CustodyFileError::invalidContent);
            pair.value.reset();
            if (result.ok()) assert(!f.open(CustodyFileAccess::writeExisting).ok());
            result.value.reset(); assert(f.open(CustodyFileAccess::writeExisting).ok());
            for (unsigned i = 0; i < 3; ++i) assert(ProtectedCustodyFiles::open(f.root,"package-a",
                {f.context.storeId,package.refs[i].objectId,package.refs[i].role},CustodyFileAccess::writeExisting).ok());
        }
        {
            Fixture f(CustodyRole::manifest,L"manifest"); auto cancel = std::make_shared<std::atomic<bool>>(false);
            CustodyBytes tooLarge(65537,32); inject(FileFault::none);
            const auto refused = commitProtectedCustodyMetadata(f.root,"package-a",f.context,0,tooLarge,cancel);
            assert(refused.state == CustodyCommitState::notCommitted && refused.error != CustodyFileError::none && writes == 0);
        }
        const auto canonicalBase = read(generated.root/L"prefix"/L".canonical-mix.f32.tmp");
        const auto recoveryBase = read(generated.root/L"prefix"/L"capture-recovery.json");
        const auto degradedManifest = read(degradedResult.manifestPath);
        const auto artifactsAt = degradedManifest.find(",\"artifacts\":"); assert(artifactsAt != std::string::npos);
        const auto degradedPrivacy = append(append(degradedManifest.substr(0,artifactsAt)+"}",
            "\"sessionId\":\"synthetic-session\""),"\"privacySegments\":["+open+"]");
        const std::array<std::string,2> degradedAudio{read(degradedResult.wavPath),read(degradedResult.playbackPath)};
        for (unsigned test = 0; test < 23; ++test) {
            Fixture f(CustodyRole::packageState,L"package-state"); auto cancel = std::make_shared<std::atomic<bool>>(false);
            auto canonical = canonicalBase, recovery = recoveryBase;
            if (test == 1) canonical += "xyz";
            if (test == 7) { const std::uint32_t nan = 0x7fc00000; std::memcpy(canonical.data(),&nan,4); }
            const auto digest = custody_detail::digest(reinterpret_cast<const std::uint8_t*>(canonical.data()),canonical.size()); assert(digest);
            std::string hash; for (auto byte : *digest) { hash += "0123456789abcdef"[byte >> 4]; hash += "0123456789abcdef"[byte & 15]; }
            constexpr std::string_view hashMarker = "\"canonical_sha256\":\"";
            const auto hashAt = recovery.find(hashMarker); assert(hashAt != std::string::npos);
            recovery.replace(hashAt+hashMarker.size(),64,hash);
            recovery = change(recovery,"\"canonical_bytes\":192000","\"canonical_bytes\":"+std::to_string(canonical.size()));
            if (test == 2) recovery = change(recovery,"\"trusted_prefix_frames\":100","\"trusted_prefix_frames\":99");
            if (test == 3) recovery = change(recovery,"clock_discontinuity","queue_overflow");
            if (test == 4) recovery = change(recovery,"\"trusted_prefix_frames\":100","\"trusted_prefix_frames\":101");
            if (test == 5) recovery = change(recovery,"\"trusted_prefix_frames\":100","\"trusted_prefix_frames\":0");
            if (test == 6) recovery = change(recovery,"\"canonical_bytes\":192000","\"canonical_bytes\":192001");
            if (test == 8) recovery[hashAt+hashMarker.size()] = recovery[hashAt+hashMarker.size()] == 'a' ? 'b' : 'a';
            CustodyPackageValue package; package.context = f.context; package.generation = 1; package.phase = CustodyPackagePhase::sealedDegraded; package.reason = ReasonCode::clockDiscontinuity;
            std::copy_n("package-a",9,package.directory.begin());
            package.refs[package.refCount++] = protectRecordingMember(f,CustodyRole::canonical,CustodyBytes(canonical.begin(),canonical.end()),cancel);
            package.refs[package.refCount++] = protectRecordingMember(f,CustodyRole::recovery,CustodyBytes(recovery.begin(),recovery.end()),cancel);
            if (test >= 14) {
                auto content = degradedPrivacy;
                if (test == 15) content = change(content,"\"sessionId\":\"synthetic-session\"","\"sessionId\":\"other-session\"");
                if (test == 16) content = append(content,"\"unknown\":true");
                if (test == 17) content = change(change(content,"\"capture_status\":\"degraded\"","\"capture_status\":\"normal\""),"clock_discontinuity","none");
                if (test == 18) content = change(content,"\"duration_ms\":1000","\"duration_ms\":990");
                if (test == 19) content = change(content,",\"privacySegments\":["+open+"]","");
                if (test == 20) content = change(content,",\"sessionId\":\"synthetic-session\"","");
                if (test == 22) content = change(content,"\"durationMs\":0","\"durationMs\":1");
                package.refs[package.refCount++] = protectRecordingMember(f,CustodyRole::manifest,CustodyBytes(content.begin(),content.end()),cancel);
                if (test == 21) package.refs[package.refCount++] = protectRecordingMember(f,CustodyRole::media,
                    CustodyBytes(degradedAudio[0].begin(),degradedAudio[0].end()),cancel);
            }
            for (unsigned i = 0; i < 3; ++i) if (test == 9 || ((test == 10 || test == 12) && i == 0) || ((test == 11 || test == 13) && i == 1)) {
                auto content = i == 2 ? degradedManifest : degradedAudio[i];
                if (test == 12) content[24] = 0; // Correct ref SHA, wrong WAV sample rate.
                if (test == 13) std::fill(content.begin(),content.end(),static_cast<char>(255)); // Real unreadable native final, no manifest substitute.
                package.refs[package.refCount++] = protectRecordingMember(f,static_cast<CustodyRole>(i+2),CustodyBytes(content.begin(),content.end()),cancel);
            }
            const auto value = writeCustodyPackage(package,f.context,1,"package-a"); assert(value.ok());
            assert(commitProtectedCustodyMetadata(f.root,"package-a",f.context,0,*value.value,cancel).state == CustodyCommitState::committed);
            auto pair = ProtectedCustodyPackagePair::read(f.root,"package-a",f.context,cancel); assert(pair.ok());
            auto result = LocalRecordingPackage::inspectProtected(f.root,*pair.value,"synthetic-session",cancel);
            std::printf("protected-v5 degraded_case=%u accepted=%u error=%u native=0x%08x\n",test,static_cast<unsigned>(result.ok()),static_cast<unsigned>(result.error),result.nativeError); std::fflush(stdout);
            assert(result.ok() == (test < 3 || (test >= 9 && test <= 11) || test == 14));
            if (result.ok()) { assert((*result.value)->evidence().integrity == PackageIntegrity::degraded);
                assert((*result.value)->evidence().trustedPrefixFrames == (test == 2 ? 99 : 100));
                assert((*result.value)->evidence().durationMs == (test == 2 ? 990 : 1000)); }
            else assert(result.error != CustodyFileError::none);
            pair.value.reset(); result.value.reset(); assert(f.open(CustodyFileAccess::writeExisting).ok());
        }
    }
    std::fprintf(stderr,"protected-v5 owned_before=%zu owned_after=%zu\n",before,CustodyOwnedMemory::usedBytes());
    std::fflush(stderr);
    assert(CustodyOwnedMemory::usedBytes() == before);
}
void readOnlyFilesAdmission() {
    const auto baseline = CustodyOwnedMemory::usedBytes();
    struct Result {
        CustodyFileError error = CustodyFileError::none, retry = CustodyFileError::none;
        std::uint32_t native = 0;
        bool control = false, quota = false, noWrites = false, artifactsUnchanged = false, released = false;
    };
    std::array<Result, 5> results{};
    for (unsigned test = 0; test != results.size(); ++test) {
        auto& result = results[test];
        {
            inject(FileFault::none); Fixture fixture;
            auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
            const auto index = snapshotData(fixture, **files.value);
            publish(fixture, **files.value, 0, index); publish(fixture, **files.value, 1, index);
            { const auto pair = (*files.value)->readValidatedMetadataPair(); result.control = pair.ok(); }
            if (test >= 3) assert(DeleteFileW((fixture.object() / L"index.0").c_str()));
            if (test == 4) fixture.write(fixture.object() / L"index.0", CustodyBytes(8, 0));
            const auto artifacts = writerArtifacts(fixture);
            {
                CustodyBytes pressure;
                inject(test == 1 ? FileFault::readFailed : test == 2 ? FileFault::readAborted : FileFault::none);
                if (test == 0) {
                    pressure.resize(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
                    result.quota = CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit;
                }
                if (test >= 3) afterRead = [&] {
                    wchar_t path[1024]{};
                    const auto count = GetFinalPathNameByHandleW(afterReadFile, path, 1024, FILE_NAME_NORMALIZED);
                    assert(count && count < 1024);
                    if (!result.quota && std::wstring_view(path, count).find(L"\\index.1") != std::wstring_view::npos) {
                        pressure.resize(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
                        result.quota = CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit;
                    }
                };
                const auto denied = (*files.value)->readValidatedMetadataPair();
                result.error = denied.error; result.native = denied.nativeError;
                afterRead = {};
                result.noWrites = !writes && !flushes && !renames && !creates;
            }
            inject(FileFault::none);
            { const auto pair = (*files.value)->readValidatedMetadataPair(); result.retry = pair.error; }
            result.noWrites = result.noWrites && !writes && !flushes && !renames && !creates;
            result.artifactsUnchanged = writerArtifacts(fixture) == artifacts;
        }
        result.released = CustodyOwnedMemory::usedBytes() == baseline;
        std::fprintf(stderr, "READ_ONLY_FILES case=%u control=%u quota=%u error=%u native=%u retry=%u no_writes=%u artifacts_unchanged=%u released=%u\n",
            test, result.control, result.quota, static_cast<unsigned>(result.error), result.native,
            static_cast<unsigned>(result.retry), result.noWrites, result.artifactsUnchanged, result.released);
    }
    std::fflush(stderr);
    for (const auto& result : results) {
        assert(result.control && result.released && result.noWrites && result.artifactsUnchanged &&
            "read_only_files_admission_requires_control_no_writes_and_release");
    }
    assert(results[0].quota && results[0].error == CustodyFileError::allocationFailed &&
        "read_only_files_quota_requires_exact_allocation_refusal");
    for (const unsigned test : {1U, 2U}) {
        assert(results[test].error == CustodyFileError::ioFailed &&
            results[test].native == static_cast<std::uint32_t>(test == 1 ? ERROR_READ_FAULT : ERROR_OPERATION_ABORTED) &&
            results[test].retry == CustodyFileError::writerFailed && "read_only_files_physical_fault_must_remain_sticky");
    }
    assert(results[3].quota && results[3].error == CustodyFileError::allocationFailed &&
        results[3].retry == CustodyFileError::writerFailed && "read_only_files_missing_slot_then_quota_must_remain_sticky");
    assert(results[4].quota && results[4].error == CustodyFileError::allocationFailed &&
        results[4].retry == CustodyFileError::writerFailed && "read_only_files_invalid_slot_then_quota_must_remain_sticky");
    assert(results[0].retry == CustodyFileError::none && "read_only_files_must_recover_after_transient_quota");
}

void readOnlyOwnerCancellation() {
    const auto baseline = CustodyOwnedMemory::usedBytes();
    struct Result {
        bool control = false, hit = false, actualCancellation = false, rootUncancelled = false;
        bool recovered = false, futureCreated = false, noWrites = false, released = false;
        CustodyFileError error = CustodyFileError::none, retry = CustodyFileError::none;
        std::uint32_t native = 0;
    };
    std::array<Result, 4> results{};
    for (unsigned test = 0; test != results.size(); ++test) {
        auto& result = results[test];
        const bool packageRead = test % 2 != 0, physical = test >= 2;
        {
            inject(FileFault::none); Fixture fixture;
            auto rootToken = std::make_shared<std::atomic<bool>>(false);
            auto opened = ProtectedCustodyStoreOwner::open(fixture.root / L"generated-store", rootToken); assert(opened.ok());
            auto owner = *opened.value;
            { auto package = owner->createPackage("generated-owner-cancel", rootToken); assert(package.ok()); }
            auto operationToken = std::make_shared<std::atomic<bool>>(false);
            unsigned validationRead = 0;
            const auto read = [&](const std::shared_ptr<std::atomic<bool>>& token) {
                if (packageRead) {
                    auto pair = owner->readPackage("generated-owner-cancel", token);
                    return std::pair{pair.error, pair.nativeError};
                }
                auto queue = owner->readQueueValue(token);
                return std::pair{queue.error, queue.nativeError};
            };
            {
                const auto queue = owner->readQueueValue(operationToken);
                const auto pair = owner->readPackage("generated-owner-cancel", operationToken);
                result.control = queue.ok() && pair.ok();
            }
            inject(FileFault::none);
            afterRead = [&] {
                wchar_t path[1024]{};
                const auto count = GetFinalPathNameByHandleW(afterReadFile, path, 1024, FILE_NAME_NORMALIZED);
                assert(count && count < 1024);
                if (std::wstring_view(path, count).find(L"\\bootstrap\\index.0") != std::wstring_view::npos) validationRead = reads;
            };
            const auto counted = read(operationToken); afterRead = {};
            assert(counted.first == CustodyFileError::none && validationRead);
            inject(physical ? FileFault::readAborted : FileFault::none, validationRead);
            if (!physical) afterRead = [&] {
                if (reads == validationRead) { result.hit = true; operationToken->store(true); }
            };
            const auto denied = read(operationToken); afterRead = {};
            if (physical) result.hit = reads == validationRead;
            result.actualCancellation = operationToken->load();
            result.rootUncancelled = !rootToken->load();
            result.error = denied.first; result.native = denied.second;
            result.noWrites = !writes && !flushes && !renames && !creates;
            inject(FileFault::none);
            auto freshToken = std::make_shared<std::atomic<bool>>(false);
            const auto retried = read(freshToken);
            result.retry = retried.first; result.recovered = retried.first == CustodyFileError::none;
            result.noWrites = result.noWrites && !writes && !flushes && !renames && !creates;
            { auto package = owner->createPackage("generated-after-owner-cancel", freshToken); result.futureCreated = package.ok(); }
        }
        result.released = CustodyOwnedMemory::usedBytes() == baseline;
        std::fprintf(stderr, "READ_ONLY_OWNER case=%u package=%u physical=%u control=%u hit=%u token_cancelled=%u root_uncancelled=%u error=%u native=%u retry=%u future_created=%u no_writes=%u released=%u\n",
            test, packageRead, physical, result.control, result.hit, result.actualCancellation, result.rootUncancelled,
            static_cast<unsigned>(result.error), result.native, static_cast<unsigned>(result.retry), result.futureCreated,
            result.noWrites, result.released);
    }
    std::fflush(stderr);
    for (unsigned test = 0; test != results.size(); ++test) {
        const auto& result = results[test];
        assert(result.control && result.hit && result.rootUncancelled && result.noWrites && result.released &&
            result.actualCancellation == (test < 2) && "read_only_owner_cancellation_requires_qualified_control_and_release");
        assert(result.error == CustodyFileError::ioFailed && result.native == ERROR_OPERATION_ABORTED &&
            "read_only_owner_cancellation_requires_exact_native_995");
        if (test >= 2) assert(result.retry == CustodyFileError::recoveryRequired && !result.futureCreated &&
            "read_only_owner_native_995_without_cancelled_token_must_remain_sticky");
    }
    for (unsigned test = 0; test != 2; ++test) assert(results[test].recovered && results[test].futureCreated &&
        "read_only_owner_must_recover_after_operation_token_cancellation");
}

void snapshotChecks() {
    {
        Fixture fixture;
        auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
        const auto index = snapshotData(fixture, **files.value);
        publish(fixture, **files.value, 0, index); publish(fixture, **files.value, 1, index);
        const auto cipher = ProtectedCustodyCodec::sealIndex(fixture.context, 0, index); assert(cipher.ok());
        const auto block = ProtectedCustodyCodec::sealBlock(fixture.context, 0, 2, CustodyBytes{1, 2, 3, 4}); assert(block.ok());
        {
            CustodyBytes full; full.reserve(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
            inject(FileFault::none);
            assert((*files.value)->readBlock(0, 1, 4, index.entries[0].envelopeBytes).error == CustodyFileError::allocationFailed);
            assert((*files.value)->readIndex(0).error == CustodyFileError::allocationFailed);
            assert((*files.value)->writeBlock(0, 2, 4, *block.value).error == CustodyFileError::allocationFailed);
            const auto publishResult = (*files.value)->publishIndex(0, *cipher.value);
            assert(publishResult.state == CustodyPublishState::notPublished && publishResult.error == CustodyFileError::allocationFailed);
            const auto snapshot = (*files.value)->readValidatedSnapshot();
            assert(!snapshot.ok() && snapshot.error == CustodyFileError::allocationFailed);
            assert(reads == 0 && writes == 0 && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
        } // Releasing pressure must not allocate an empty replacement proxy.
        assert((*files.value)->publishIndex(0, *cipher.value).error == CustodyFileError::writerFailed);
        assert((*files.value)->readValidatedSnapshot().error == CustodyFileError::writerFailed);
    }
    for (const auto& role : {std::pair{CustodyRole::queue, L"queue"}, {CustodyRole::bootstrap, L"bootstrap"},
         {CustodyRole::packageState, L"package-state"}, {CustodyRole::migrationIntent, L"migration-intent"},
         {CustodyRole::manifest, L"manifest"}, {CustodyRole::recovery, L"recovery"}}) {
        Fixture fixture(role.first, role.second);
        auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
        auto index = snapshotData(fixture, **files.value);
        publish(fixture, **files.value, 0, index);
        const auto singleton = (*files.value)->readValidatedSnapshot();
        assert(!singleton.ok() && singleton.error == CustodyFileError::recoveryRequired);
        assert((*files.value)->publishIndex(1, *ProtectedCustodyCodec::sealIndex(fixture.context, 1, index).value).error == CustodyFileError::writerFailed);
        assert(!std::filesystem::exists(fixture.object() / L"index.1")); // No automatic completion of interrupted birth.
        files.value->reset(); files = fixture.open(CustodyFileAccess::writeExisting); assert(files.ok());
        publish(fixture, **files.value, 1, index);
        const auto pair = (*files.value)->readValidatedSnapshot();
        assert(pair.ok() && pair.value->state == CustodySnapshotState::verified && pair.value->index.generation == 1);
        const auto both = (*files.value)->readValidatedMetadataPair();
        assert(both.ok() && both.value->selectedSlot == 0 && both.value->indices[0].generation == 1 && both.value->indices[1].generation == 1);
        index.generation = 2; index.entries[0].version = 2; // Existing, decoded index references missing DATA.
        publish(fixture, **files.value, 1, index);
        const auto missingData = (*files.value)->readValidatedSnapshot();
        assert(!missingData.ok() && missingData.nativeError == ERROR_FILE_NOT_FOUND);
        assert(std::filesystem::exists(fixture.object() / L"index.0") && std::filesystem::exists(fixture.object() / L"index.1"));
    }
    {
        Fixture fixture; auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
        fixture.write(fixture.object() / L"index.tmp-orphan", CustodyBytes(16, 0));
        assert((*files.value)->readValidatedSnapshot().error == CustodyFileError::recoveryRequired);
        assert(std::filesystem::exists(fixture.object() / L"index.tmp-orphan"));
    }
    {
        Fixture fixture; auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
        auto first = snapshotData(fixture, **files.value);
        auto other = snapshotData(fixture, **files.value, 2); other.generation = 1;
        publish(fixture, **files.value, 0, first); publish(fixture, **files.value, 1, other);
        assert((*files.value)->readValidatedSnapshot().error == CustodyFileError::conflict); // Same g1, different decoded refs.
    }
    {
        Fixture fixture; auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
        auto first = snapshotData(fixture, **files.value);
        auto next = snapshotData(fixture, **files.value, 2);
        publish(fixture, **files.value, 0, first); publish(fixture, **files.value, 1, next);
        assert(DeleteFileW((fixture.object() / L"block.0.1").c_str()));
        assert(!(*files.value)->readValidatedSnapshot().ok()); // A good newer slot does not authorize a broken metadata context.
    }
    for (const auto& role : {std::pair{CustodyRole::canonical, L"canonical"}, {CustodyRole::media, L"media"}}) {
        Fixture fixture(role.first, role.second); auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
        auto first = snapshotData(fixture, **files.value);
        publish(fixture, **files.value, 0, first);
        const auto birth = (*files.value)->readValidatedSnapshot();
        assert(birth.ok() && birth.value->state == CustodySnapshotState::verified); // Byte checkpoint, not normal-package authority.
        auto next = first; next.generation = 2; next.entries[0].version = 2;
        publish(fixture, **files.value, 1, next);
        const auto prefix = (*files.value)->readValidatedSnapshot();
        assert(prefix.ok() && prefix.value->state == CustodySnapshotState::trustedPrefix && prefix.value->index.generation == 1);
        assert(prefix.value->recoveryError == CustodyFileError::ioFailed && prefix.value->nativeError == ERROR_FILE_NOT_FOUND);
        assert((*files.value)->publishIndex(0, *ProtectedCustodyCodec::sealIndex(fixture.context, 0, first).value).error == CustodyFileError::writerFailed);
    }
    {
        Fixture fixture(CustodyRole::canonical, L"canonical"); auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
        const auto index = snapshotData(fixture, **files.value);
        publish(fixture, **files.value, 1, index);
        assert(!(*files.value)->readValidatedSnapshot().ok()); // Metadata g1 exception must not leak into canonical slot placement.
    }
    {
        Fixture fixture(CustodyRole::canonical, L"canonical"); auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
        const auto index = snapshotData(fixture, **files.value);
        publish(fixture, **files.value, 0, index); publish(fixture, **files.value, 1, index);
        assert((*files.value)->readValidatedSnapshot().error == CustodyFileError::conflict);
    }
    {
        Fixture fixture; auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
        auto index = snapshotData(fixture, **files.value);
        publish(fixture, **files.value, 1, index); index.generation = 3; publish(fixture, **files.value, 0, index);
        const auto selected = (*files.value)->readValidatedSnapshot();
        assert(selected.ok() && selected.value->index.generation == 3); // No invented generation-gap threshold.
    }
    for (const auto fault : {FileFault::hashCreate, FileFault::readFailed, FileFault::allocation}) {
        for (unsigned ordinal = 1; ordinal <= 4; ++ordinal) {
            inject(FileFault::none); Fixture fixture(CustodyRole::canonical, L"canonical");
            auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
            auto first = snapshotData(fixture, **files.value), next = snapshotData(fixture, **files.value, 2);
            publish(fixture, **files.value, 0, first); publish(fixture, **files.value, 1, next);
            inject(fault, ordinal);
            const auto result = (*files.value)->readValidatedSnapshot();
            const auto expected = fault == FileFault::hashCreate ? CustodyFileError::hashFailed
                : fault == FileFault::readFailed ? CustodyFileError::ioFailed : CustodyFileError::allocationFailed;
            assert(!result.ok() && result.error == expected);
            assert(fault != FileFault::readFailed || result.nativeError == ERROR_READ_FAULT);
            inject(FileFault::none);
            assert((*files.value)->readValidatedSnapshot().error == CustodyFileError::writerFailed); // Fault is sticky, not cleared by a healthy second slot.
        }
    }
    {
        Fixture fixture(CustodyRole::canonical, L"canonical"); auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
        auto index = snapshotData(fixture, **files.value); publish(fixture, **files.value, 0, index);
        // Intentionally store a ciphertext with the wrong slot entropy, keeping valid ACL/outer framing.
        auto wrongSlot = ProtectedCustodyCodec::sealIndex(fixture.context, 0, index); assert(wrongSlot.ok());
        fixture.write(fixture.object() / L"index.1", *wrongSlot.value);
        const auto result = (*files.value)->readValidatedSnapshot();
        assert(!result.ok() && result.error == CustodyFileError::protectionFailed && result.nativeError != 0);
    }
    {
        Fixture fixture(CustodyRole::playback, L"playback"); auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
        assert((*files.value)->readValidatedMetadataPair().error == CustodyFileError::invalidInput);
        auto index = snapshotData(fixture, **files.value); publish(fixture, **files.value, 0, index);
        assert((*files.value)->readValidatedSnapshot().ok()); // Playback is not a metadata birth pair.
        index.generation = 2; index.entries[0].version = 2; publish(fixture, **files.value, 1, index);
        assert(!(*files.value)->readValidatedSnapshot().ok()); // No canonical/media fallback permission for playback.
    }
    {
        Fixture fixture(CustodyRole::canonical, L"canonical"); auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
        auto index = snapshotData(fixture, **files.value); publish(fixture, **files.value, 0, index);
        index.generation = 2;
        auto cipher = ProtectedCustodyCodec::sealIndex(fixture.context, 1, index); assert(cipher.ok());
        (*cipher.value)[0] ^= 1; fixture.write(fixture.object() / L"index.1", *cipher.value);
        const auto result = (*files.value)->readValidatedSnapshot();
        assert(result.ok() && result.value->state == CustodySnapshotState::trustedPrefix);
        assert(result.value->index.generation == 1 && result.value->recoveryError == CustodyFileError::invalidContent);
    }
    {
        Fixture fixture(CustodyRole::canonical, L"canonical"); auto files = fixture.open(CustodyFileAccess::createNew); assert(files.ok());
        const CustodyBytes full(ProtectedCustodyCodec::blockBytes, 42), tail{1, 2, 3, 4};
        auto first = ProtectedCustodyCodec::sealBlock(fixture.context, 0, 1, full), last = ProtectedCustodyCodec::sealBlock(fixture.context, 1, 1, tail);
        assert(first.ok() && last.ok());
        const auto a = (*files.value)->writeBlock(0, 1, static_cast<std::uint32_t>(full.size()), *first.value);
        const auto b = (*files.value)->writeBlock(1, 1, 4, *last.value); assert(a.ok() && b.ok());
        CustodyIndex index{1, ProtectedCustodyCodec::blockBytes + 4ULL, {{1, *a.value, 0}, {1, *b.value, 0}}};
        publish(fixture, **files.value, 0, index);
        assert((*files.value)->readValidatedSnapshot().ok());
        index.generation = 2; index.logicalLength = std::uint64_t{ProtectedCustodyCodec::blockBytes} * 2;
        publish(fixture, **files.value, 1, index); // The old short tail is NOT a full block after extension.
        const auto result = (*files.value)->readValidatedSnapshot();
        assert(result.ok() && result.value->state == CustodySnapshotState::trustedPrefix && result.value->index.generation == 1);
        assert(result.value->recoveryError == CustodyFileError::invalidContent);
    }
    inject(FileFault::none);
}
struct WorkingDirectory {
    wchar_t previous[32768]{};
    explicit WorkingDirectory(const std::filesystem::path& path) {
        assert(GetCurrentDirectoryW(32768, previous)); assert(SetCurrentDirectoryW(path.c_str()));
    }
    ~WorkingDirectory() { assert(SetCurrentDirectoryW(previous)); }
};
void junction(const std::filesystem::path& link, const std::filesystem::path& target, SECURITY_ATTRIBUTES& security) {
    assert(CreateDirectoryW(link.c_str(), &security));
    const auto file = CreateFileW(link.c_str(), GENERIC_WRITE, 0, nullptr, OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr); assert(file != INVALID_HANDLE_VALUE);
    struct Reparse {
        DWORD tag; WORD length, reserved;
        WORD substituteOffset, substituteLength, printOffset, printLength;
        wchar_t names[1024];
    } record{};
    record.tag = IO_REPARSE_TAG_MOUNT_POINT;
    const auto substitute = std::wstring(L"\\??\\") + target.wstring(), print = target.wstring();
    const auto characters = substitute.size() + 1 + print.size() + 1; assert(characters <= 1024);
    record.substituteLength = static_cast<WORD>(substitute.size() * 2);
    record.printOffset = record.substituteLength + 2; record.printLength = static_cast<WORD>(print.size() * 2);
    record.length = static_cast<WORD>(8 + characters * 2);
    std::copy(substitute.begin(), substitute.end(), record.names);
    std::copy(print.begin(), print.end(), record.names + substitute.size() + 1);
    DWORD returned = 0;
    assert(DeviceIoControl(file, FSCTL_SET_REPARSE_POINT, &record, 8 + record.length, nullptr, 0, &returned, nullptr));
    CloseHandle(file);
}
#endif
}

int main(int argc, char** argv) {
#ifdef _MSC_VER
    // Isolated negative runs must report termination, not hang on a CRT dialog.
    _set_error_mode(_OUT_TO_STDERR);
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
#ifdef _DEBUG
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
#endif
#endif
    if (argc == 2 && std::string(argv[1]) == "--cold-cache-close") {
#ifdef _WIN32
        coldCacheClose();
#else
        std::fputs("cold-cache-close SKIP unsupportedPlatform\n", stderr);
#endif
        return 0;
    }
    if (argc == 2 && std::string(argv[1]) == "--writer-open-budget") {
#ifdef _WIN32
        writerOpenBudget();
#else
        std::fputs("writer-open-budget SKIP unsupportedPlatform\n", stderr);
#endif
        return 0;
    }
    if (argc == 2 && std::string(argv[1]) == "--metadata-move-budget") {
#ifdef _WIN32
        metadataMoveBudget();
#else
        std::fputs("metadata-move-budget SKIP unsupportedPlatform\n", stderr);
#endif
        return 0;
    }
    if (argc == 2 && (std::string(argv[1]) == "--writer-throughput-probe"
        || std::string(argv[1]) == "--writer-throughput-probe-64mib")) {
#ifdef _WIN32
        return writerThroughputProbe(std::string(argv[1]) == "--writer-throughput-probe-64mib");
#else
        std::printf("writer-throughput failure_count error=unsupportedPlatform count=1\n");
        return 1;
#endif
    }
#ifndef _WIN32
    (void)argc; (void)argv;
    const CustodyContext context{{}, {}, CustodyRole::queue};
    const auto result = ProtectedCustodyFiles::open("/tmp/not-a-custody-root", "", context, CustodyFileAccess::createNew);
    assert(!result.ok() && result.error == CustodyFileError::unsupportedPlatform);
    const CustodyContext package{{}, {}, CustodyRole::packageState};
    const CustodyContext bootstrap{{}, {}, CustodyRole::bootstrap};
    assert(ProtectedCustodyBootstrapPair::read("/tmp/not-a-custody-root", bootstrap, CustodyId{},
        std::make_shared<std::atomic<bool>>(false)).error == CustodyFileError::unsupportedPlatform);
    assert(ProtectedCustodyBootstrapPair::read("/tmp/not-a-custody-root",
        std::make_shared<std::atomic<bool>>(false)).error == CustodyFileError::unsupportedPlatform);
    assert(ProtectedCustodyPackagePair::read("/tmp/not-a-custody-root", "package-a", package,
        std::make_shared<std::atomic<bool>>(false)).error == CustodyFileError::unsupportedPlatform);
    const CustodyContext intent{{}, {}, CustodyRole::migrationIntent};
    const auto cancellation = std::make_shared<std::atomic<bool>>(false);
    assert(ProtectedCustodyMigrationPair::read("/tmp/not-a-custody-root", intent, CustodyId{},
        CustodyMigrationSubject::queue, "", cancellation).error == CustodyFileError::unsupportedPlatform);
    assert(ProtectedCustodyMigrationPair::read("/tmp/not-a-custody-root", intent, CustodyId{},
        CustodyMigrationSubject::package, "package-a", cancellation).error == CustodyFileError::unsupportedPlatform);
    assert(ProtectedCustodyMigrationPair::read("/tmp/not-a-custody-root", intent, CustodyId{},
        CustodyMigrationSubject::queue, "", {}).error == CustodyFileError::invalidInput);
    assert(ProtectedCustodyMigrationPair::read(std::shared_ptr<const ProtectedCustodyBootstrapPair>{}, cancellation).error == CustodyFileError::invalidInput);
    assert(ProtectedCustodyMigrationPair::read(std::shared_ptr<const ProtectedCustodyBootstrapPair>{}, {}).error == CustodyFileError::invalidInput);
#else
    if (argc == 2 && std::string(argv[1]) == "--recording-semantics") {
        // Measure the process-lifetime empty cache proxy, as the full suite does.
        // Both runs must then return exactly to baseline; no leak allowance.
        coldCacheClose();
        protectedRecordingSemantics();
        protectedRecordingSemantics();
        return 0;
    }
    if (argc == 2 && std::string(argv[1]) == "--readonly-files-admission") { readOnlyFilesAdmission(); return 0; }
    if (argc == 2 && std::string(argv[1]) == "--readonly-owner-cancellation") { readOnlyOwnerCancellation(); return 0; }
    if (argc == 2 && std::string(argv[1]) == "--logical-queue") { protectedQueueCandidate(); return 0; }
    if (argc == 2 && std::string(argv[1]) == "--migration-history") { migrationHistory(); return 0; }
    if (argc == 2 && std::string(argv[1]) == "--migration-pair") { linkedMigrationPairs(); protectedMigrationPairs(); return 0; }
    // Explicit manual RED control, not a production option or a default CTest.
    attributeOnlyLocks = argc == 2 && std::string(argv[1]) == "--attribute-only-negative-control";
    if (!attributeOnlyLocks) { readOnlyFilesAdmission(); readOnlyOwnerCancellation(); linkedMigrationPairs(); protectedMigrationPairs(); protectedQueueCandidate(); protectedQueueInput(); protectedBootstrapDiscovery(); protectedBootstrapPairs(); migrationHistory(); coldCacheClose(); writerOpenBudget(); metadataMoveBudget(); protectedReader(); protectedMetadata(); protectedMediaWriter(); protectedPackagePairs(); sealedFlatMembers(); livePackageGroup(); sealedPackageGroup(); protectedPlayback(); protectedRecordingSemantics(); }
    Fixture fixture;
    const auto outside = fixture.root / L"different-process-cwd";
    assert(CreateDirectoryW(outside.c_str(), &fixture.security));
    WorkingDirectory cwd(outside);
    assert(!ProtectedCustodyFiles::open(fixture.root, "../external", fixture.context, CustodyFileAccess::createNew).ok());
    assert(!ProtectedCustodyFiles::open(fixture.root.wstring() + L":stream", "", fixture.context, CustodyFileAccess::createNew).ok());
    assert(!ProtectedCustodyFiles::open(L"\\\\server\\share", "", fixture.context, CustodyFileAccess::createNew).ok());
    assert(!ProtectedCustodyFiles::open(fixture.root / L".." / fixture.root.filename(), "", fixture.context, CustodyFileAccess::createNew).ok());
    auto wrong = fixture.context; wrong.storeId[0] ^= 1;
    assert(!ProtectedCustodyFiles::open(fixture.root, "", wrong, CustodyFileAccess::createNew).ok());
    assert(!std::filesystem::exists(fixture.object()));
    auto opened = fixture.open(CustodyFileAccess::createNew);
    if (!opened.ok()) std::fprintf(stderr, "open error=%u native=%u\n", static_cast<unsigned>(opened.error), opened.nativeError);
    assert(opened.ok());
    auto files = std::move(*opened.value);
    for (const auto access : {static_cast<DWORD>(DELETE), static_cast<DWORD>(GENERIC_WRITE)}) {
        const auto attempt = CreateFileW(fixture.root.c_str(), access, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            nullptr, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, nullptr);
        assert(attempt == INVALID_HANDLE_VALUE && GetLastError() == ERROR_SHARING_VIOLATION);
    }
    assert(!fixture.open(CustodyFileAccess::writeExisting).ok()); // Single writer lease.
    assert(!fixture.open(CustodyFileAccess::createNew).ok()); // Never reset an existing directory.
    wrong = fixture.context; wrong.objectId[0] ^= 1;
    assert(!ProtectedCustodyFiles::open(fixture.root, "", wrong, CustodyFileAccess::readExisting).ok());
    const CustodyBytes payload{1, 2, 3, 4};
    auto envelope = ProtectedCustodyCodec::sealBlock(fixture.context, 0, 1, payload); assert(envelope.ok());
    auto written = files->writeBlock(0, 1, 4, *envelope.value); assert(written.ok() && *written.value == envelope.value->size());
    auto read = files->readBlock(0, 1, 4, *written.value); assert(read.ok() && *read.value == *envelope.value);
    assert(!files->readBlock(0, 1, 4, *written.value + 1).ok());
    assert(!files->readBlock(0, 2, 4, *written.value).ok()); // Missing DATA is an error, not ZERO.
    const auto renamedRoot = fixture.root.wstring() + L"-renamed";
    assert(!MoveFileExW(fixture.root.c_str(), renamedRoot.c_str(), 0));
    auto reader = fixture.open(CustodyFileAccess::readExisting); assert(reader.ok());
    assert(!(*reader.value)->writeBlock(0, 2, 4, *envelope.value).ok());
    CustodyIndex index{1, 4, {{1, *written.value, 0}}};
    auto first = ProtectedCustodyCodec::sealIndex(fixture.context, 0, index); assert(first.ok());
    const auto firstPublish = files->publishIndex(0, *first.value);
    if (firstPublish.state != CustodyPublishState::published) std::fprintf(stderr, "publish state=%u error=%u native=%u\n",
        static_cast<unsigned>(firstPublish.state), static_cast<unsigned>(firstPublish.error), firstPublish.nativeError);
    assert(firstPublish.state == CustodyPublishState::published);
    assert(!std::filesystem::exists(outside / L"index.0")); // Simple rename is source-relative, NOT process-CWD-relative.
    auto second = ProtectedCustodyCodec::sealIndex(fixture.context, 1, index); assert(second.ok());
    assert(files->publishIndex(1, *second.value).state == CustodyPublishState::published);
    auto recovered = files->readIndex(1); assert(recovered.ok());
    auto decoded = ProtectedCustodyCodec::openIndex(fixture.context, 1, *recovered.value);
    assert(decoded.ok() && decoded.value->generation == 1 && decoded.value->logicalLength == 4);
    index.generation = 2;
    auto next = ProtectedCustodyCodec::sealIndex(fixture.context, 1, index); assert(next.ok());
    assert(files->publishIndex(1, *next.value).state == CustodyPublishState::published);
    assert(!files->readIndex(2).ok());
    // Before-write semantic corruption: no physical block created.
    auto broken = *envelope.value; broken[0] ^= 1;
    assert(!files->writeBlock(0, 2, 4, broken).ok());
    assert(!std::filesystem::exists(fixture.object() / L"block.0.2"));
    // A collision poisons this writer, never overwrites orphan/ciphertext.
    const auto collision = files->writeBlock(0, 1, 4, *envelope.value);
    assert(!collision.ok() && collision.error == CustodyFileError::conflict);
    assert(files->publishIndex(1, *next.value).error == CustodyFileError::writerFailed);
    assert(std::filesystem::file_size(fixture.object() / L"block.0.1") == *written.value);
    files.reset(); reader.value->reset();
    auto reopened = fixture.open(CustodyFileAccess::writeExisting); assert(reopened.ok());
    assert((*reopened.value)->readIndex(0).ok() && (*reopened.value)->readIndex(1).ok());
    reopened.value->reset();
    // Unknown files survive opening; this layer never performs GC or inventory repair.
    fixture.write(fixture.object() / L"unknown", CustodyBytes{42});
    auto unknown = fixture.open(CustodyFileAccess::readExisting); assert(unknown.ok()); unknown.value->reset();
    assert(std::filesystem::exists(fixture.object() / L"unknown"));
    // A hard-linked content object is rejected, even if its bytes/ACL would pass.
    assert(CreateHardLinkW((fixture.object() / L"alias").c_str(), (fixture.object() / L"block.0.1").c_str(), nullptr));
    auto links = fixture.open(CustodyFileAccess::readExisting); assert(links.ok());
    assert(!(*links.value)->readBlock(0, 1, 4, *written.value).ok()); links.value->reset();
    assert(DeleteFileW((fixture.object() / L"alias").c_str()));
    // Truncated identity is blocked, not regenerated.
    assert(DeleteFileW((fixture.object() / L"id.bin").c_str())); fixture.write(fixture.object() / L"id.bin", CustodyBytes{9});
    const auto badId = fixture.open(CustodyFileAccess::readExisting);
    assert(!badId.ok() && badId.error == CustodyFileError::identityMismatch);
    assert(std::filesystem::file_size(fixture.object() / L"id.bin") == 1);

    {
        Fixture outsideObject, redirected;
        auto target = outsideObject.open(CustodyFileAccess::createNew); assert(target.ok()); target.value->reset();
        junction(redirected.object(), outsideObject.object(), redirected.security);
        const auto rejected = redirected.open(CustodyFileAccess::readExisting);
        assert(!rejected.ok() && rejected.error == CustodyFileError::unsafePath);
        assert(RemoveDirectoryW(redirected.object().c_str())); // Remove the link, never its target.
        assert(std::filesystem::file_size(outsideObject.object() / L"id.bin") == 16);
    }
    {
        Fixture bounds; bounds.context.role = CustodyRole::canonical;
        assert(CreateDirectoryW((bounds.root / L"package-a").c_str(), &bounds.security));
        auto object = ProtectedCustodyFiles::open(bounds.root, "package-a", bounds.context, CustodyFileAccess::createNew); assert(object.ok());
        const CustodyBytes full(ProtectedCustodyCodec::blockBytes, 42);
        auto cipher = ProtectedCustodyCodec::sealBlock(bounds.context, 0, 1, full); assert(cipher.ok());
        auto writtenFull = (*object.value)->writeBlock(0, 1, static_cast<std::uint32_t>(full.size()), *cipher.value); assert(writtenFull.ok());
        assert((*object.value)->readBlock(0, 1, static_cast<std::uint32_t>(full.size()), *writtenFull.value).ok());
        // Explicit ZERO extension, not a missing DATA fallback. Exercise the
        // largest physical index and bounded multi-chunk file write/read.
        CustodyIndex maximum{1, std::uint64_t{64} << 30, {}}; maximum.entries.assign(262144, {0, 0, 1});
        auto indexCipher = ProtectedCustodyCodec::sealIndex(bounds.context, 0, maximum); assert(indexCipher.ok());
        assert((*object.value)->publishIndex(0, *indexCipher.value).state == CustodyPublishState::published);
        auto readMaximum = (*object.value)->readIndex(0); assert(readMaximum.ok() && *readMaximum.value == *indexCipher.value);
        const auto verifiedMaximum = (*object.value)->readValidatedSnapshot();
        assert(verifiedMaximum.ok() && verifiedMaximum.value->index.logicalLength == maximum.logicalLength);
        assert(verifiedMaximum.value->index.entries.size() == 262144); // No DATA reads/allocation for explicit ZERO extent.
        object.value->reset();
        const auto file = CreateFileW((bounds.root / L"package-a" / L".custody-v1" / L"canonical" / L"index.0").c_str(),
            GENERIC_WRITE, 0, nullptr, OPEN_EXISTING, 0, nullptr); assert(file != INVALID_HANDLE_VALUE);
        LARGE_INTEGER oversized{}; oversized.QuadPart = static_cast<LONGLONG>(ProtectedCustodyCodec::indexEnvelopeLimit(CustodyRole::canonical) + 1);
        assert(SetFilePointerEx(file, oversized, nullptr, FILE_BEGIN) && SetEndOfFile(file)); CloseHandle(file);
        object = ProtectedCustodyFiles::open(bounds.root, "package-a", bounds.context, CustodyFileAccess::readExisting); assert(object.ok());
        reads = 0;
        assert((*object.value)->readIndex(0).error == CustodyFileError::invalidContent && reads == 0); // Size before read/allocation.
        object.value->reset();
    }
    {
        Fixture role; role.context.role = CustodyRole::manifest;
        assert(CreateDirectoryW((role.root / L"package-a").c_str(), &role.security));
        auto object = ProtectedCustodyFiles::open(role.root, "package-a", role.context, CustodyFileAccess::createNew); assert(object.ok());
        reads = 0;
        const auto rejected = (*object.value)->readBlock(0, 1, 65537, 65537 + 4096);
        assert(rejected.error == CustodyFileError::invalidInput && reads == 0); // Role cap before disk/read allocation too.
        object.value->reset();
    }
    {
        Fixture acl;
        auto object = acl.open(CustodyFileAccess::createNew); assert(object.ok()); object.value->reset();
        // An inherited ACL, even for this user, is not the required protected ACL.
        BOOL present = FALSE, defaulted = FALSE; PACL dacl = nullptr;
        assert(GetSecurityDescriptorDacl(acl.descriptor, &present, &dacl, &defaulted) && present && dacl);
        assert(SetNamedSecurityInfoW((acl.object() / L"id.bin").wstring().data(), SE_FILE_OBJECT,
            DACL_SECURITY_INFORMATION | UNPROTECTED_DACL_SECURITY_INFORMATION, nullptr, nullptr, dacl, nullptr) == ERROR_SUCCESS);
        assert(!acl.open(CustodyFileAccess::readExisting).ok());
    }

    for (const auto fault : {FileFault::shortWrite, FileFault::zeroWrite, FileFault::write, FileFault::flush}) {
        inject(FileFault::none); Fixture boundary;
        auto object = boundary.open(CustodyFileAccess::createNew); assert(object.ok());
        auto cipher = ProtectedCustodyCodec::sealBlock(boundary.context, 0, 1, payload); assert(cipher.ok());
        inject(fault);
        auto result = (*object.value)->writeBlock(0, 1, 4, *cipher.value);
        if (fault == FileFault::shortWrite) assert(result.ok() && writes > 1 && flushes == 1);
        else {
            assert(!result.ok());
            assert((*object.value)->writeBlock(0, 2, 4, *cipher.value).error == CustodyFileError::writerFailed);
            assert(std::filesystem::exists(boundary.object() / L"block.0.1")); // Retain the uncertain immutable artifact.
        }
        object.value->reset(); inject(FileFault::none);
    }
    for (const auto fault : {FileFault::flush, FileFault::rename, FileFault::renameCompletion, FileFault::read}) {
        for (unsigned ordinal = 1; ordinal <= (fault == FileFault::flush ? 2U : 1U); ++ordinal) {
            inject(FileFault::none); Fixture boundary;
            auto object = boundary.open(CustodyFileAccess::createNew); assert(object.ok());
            const auto cipher = ProtectedCustodyCodec::sealIndex(boundary.context, 0, CustodyIndex{1, 0, {}}); assert(cipher.ok());
            inject(fault, ordinal);
            const auto result = (*object.value)->publishIndex(0, *cipher.value);
            const bool prePublish = fault == FileFault::flush && ordinal == 1;
            assert(result.state == (prePublish ? CustodyPublishState::notPublished : CustodyPublishState::ambiguous));
            assert((*object.value)->publishIndex(0, *cipher.value).error == CustodyFileError::writerFailed);
            assert(std::filesystem::exists(boundary.object() / L"index.0") == (!prePublish && fault != FileFault::rename));
            bool retained = false;
            for (const auto& entry : std::filesystem::directory_iterator(boundary.object()))
                if (entry.path().filename().wstring().find(L"index.") == 0) retained = true;
            assert(retained); // Ciphertext temp or published slot is never hidden cleanup.
            object.value->reset(); inject(FileFault::none);
        }
    }
    inject(FileFault::none);
    snapshotChecks();
#endif
}
