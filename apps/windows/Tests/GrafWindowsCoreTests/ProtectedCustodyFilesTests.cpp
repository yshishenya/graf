#include "../../RecApp/Storage/ProtectedCustodyFiles.h"
#ifdef _WIN32
#include "../../RecApp/Storage/ProtectedCustodyReader.h"
#include "../../RecApp/Storage/ProtectedCustodyMetadata.h"
#include "../../RecApp/Storage/ProtectedCustodyWriter.h"
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
#ifdef _MSC_VER
#include <crtdbg.h>
#include <cstdlib>
#endif

#ifdef _WIN32
// TU-local native failures compile the REAL file layer. No production fault knob.
namespace {
enum class FileFault { none, shortWrite, zeroWrite, write, flush, rename, renameCompletion, read, readFailed, hashCreate, allocation };
FileFault fileFault = FileFault::none;
unsigned flushOrdinal = 1, flushes = 0, writes = 0, reads = 0, hashCreates = 0;
unsigned opens = 0, renames = 0, searches = 0, diskChecks = 0;
bool attributeOnlyLocks = false;
std::function<void()> afterFlush, afterRename;
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
    if (attributeOnlyLocks && (flags & FILE_FLAG_BACKUP_SEMANTICS)) access &= ~FILE_LIST_DIRECTORY;
    return CreateFileW(path, access, share, security, disposition, flags, templateFile);
}
void inject(FileFault selected, unsigned ordinal = 1) {
    fileFault = selected; flushOrdinal = ordinal; flushes = writes = reads = hashCreates = 0;
    opens = renames = searches = diskChecks = 0;
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
    if (fileFault == FileFault::readFailed && reads == flushOrdinal) { SetLastError(ERROR_READ_FAULT); return FALSE; }
    return ReadFile(file, bytes, count, got, overlapped);
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
        assert(limit == (role.first == CustodyRole::manifest ? 4096U : 64 * 1024U));
        CustodyBytes over(static_cast<std::size_t>(limit) + 1, 1);
        inject(FileFault::none);
        assert(commitProtectedCustodyMetadata(fixture.root, fixture.service ? "" : "package-a", fixture.context, 0, over, cancelled).error
            == CustodyFileError::invalidInput && writes == 0);
        over.pop_back();
        auto accepted = commitProtectedCustodyMetadata(fixture.root, fixture.service ? "" : "package-a", fixture.context, 0, over, cancelled);
        assert(accepted.state == CustodyCommitState::committed && accepted.snapshot->index.logicalLength == limit);
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
        const auto loaded = reads;
        assert(clone->Read(bytes.data(), 4, &got) == S_OK && got == 4 && reads == loaded); // Same cache, own cursor.
        assert(CustodyOwnedMemory::usedBytes() == cachedCharge);
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
#else
    // Explicit manual RED control, not a production option or a default CTest.
    attributeOnlyLocks = argc == 2 && std::string(argv[1]) == "--attribute-only-negative-control";
    if (!attributeOnlyLocks) { coldCacheClose(); writerOpenBudget(); metadataMoveBudget(); protectedReader(); protectedMetadata(); protectedMediaWriter(); }
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
        const auto rejected = (*object.value)->readBlock(0, 1, 4097, 5000);
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
