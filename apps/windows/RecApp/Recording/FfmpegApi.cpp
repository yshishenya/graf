#include "FfmpegApi.h"

#ifdef _WIN32
#include "../Storage/ProtectedCustodyMemory.h"
#include <graf/GrafFFmpegBuildManifest.h>
#include <bcrypt.h>
#include <tlhelp32.h>
#include <array>
#include <cstring>
#include <cwchar>
#include <string>
#include <utility>
#include <vector>

namespace graf::windows {
namespace {
namespace pins = graf::ffmpeg;
template<class T> using OwnedVector = std::vector<T, CustodyAllocator<T>>;
using Path = std::basic_string<wchar_t, std::char_traits<wchar_t>, CustodyAllocator<wchar_t>>;
using Digest = std::array<std::uint8_t, 32>;
constexpr DWORD pathCapacity = 32768;
static_assert(pins::modules.size() == 3 && pins::machine == IMAGE_FILE_MACHINE_AMD64);
static_assert(pins::modules[0].version == LIBAVUTIL_VERSION_INT);
static_assert(pins::modules[1].version == LIBAVCODEC_VERSION_INT);
static_assert(pins::modules[2].version == LIBAVFORMAT_VERSION_INT);

[[noreturn]] void reject(HRESULT error = HRESULT_FROM_WIN32(ERROR_INVALID_DATA)) { throw error; }
[[noreturn]] void rejectLastError() {
    const auto error = GetLastError();
    reject(HRESULT_FROM_WIN32(error == ERROR_SUCCESS ? ERROR_GEN_FAILURE : error));
}
void require(bool condition) { if (!condition) reject(); }

struct File {
    HANDLE value = INVALID_HANDLE_VALUE;
    explicit File(HANDLE handle = INVALID_HANDLE_VALUE) noexcept : value(handle) {}
    ~File() { if (value != INVALID_HANDLE_VALUE) CloseHandle(value); }
    File(const File&) = delete;
    File& operator=(const File&) = delete;
    File(File&& other) noexcept : value(std::exchange(other.value, INVALID_HANDLE_VALUE)) {}
    File& operator=(File&& other) noexcept {
        if (this != &other) {
            if (value != INVALID_HANDLE_VALUE) CloseHandle(value);
            value = std::exchange(other.value, INVALID_HANDLE_VALUE);
        }
        return *this;
    }
};
struct ModuleRef {
    HMODULE value = nullptr;
    ~ModuleRef() { if (value) FreeLibrary(value); }
};
struct LoadLock {
    inline static SRWLOCK mutex = SRWLOCK_INIT;
    LoadLock() { AcquireSRWLockExclusive(&mutex); }
    ~LoadLock() { ReleaseSRWLockExclusive(&mutex); }
};

Path modulePath(HMODULE module) {
    OwnedVector<wchar_t> buffer(pathCapacity);
    const auto length = GetModuleFileNameW(module, buffer.data(), pathCapacity);
    if (!length) rejectLastError();
    require(length < pathCapacity);
    return Path(buffer.data(), length);
}
Path finalPath(HANDLE file) {
    OwnedVector<wchar_t> buffer(pathCapacity);
    const auto length = GetFinalPathNameByHandleW(file, buffer.data(), pathCapacity, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (!length) rejectLastError();
    require(length < pathCapacity);
    return Path(buffer.data(), length);
}
bool samePath(const Path& left, const Path& right) noexcept {
    return CompareStringOrdinal(left.c_str(), -1, right.c_str(), -1, TRUE) == CSTR_EQUAL;
}
bool sameFile(HANDLE left, HANDLE right) {
    FILE_ID_INFO a{}, b{};
    if (!GetFileInformationByHandleEx(left, FileIdInfo, &a, sizeof(a)) ||
        !GetFileInformationByHandleEx(right, FileIdInfo, &b, sizeof(b))) rejectLastError();
    return a.VolumeSerialNumber == b.VolumeSerialNumber &&
        std::memcmp(&a.FileId, &b.FileId, sizeof(a.FileId)) == 0;
}
File openFile(const Path& path, bool directory) {
    File file(CreateFileW(path.c_str(), directory ? FILE_LIST_DIRECTORY | FILE_READ_ATTRIBUTES : GENERIC_READ,
        directory ? FILE_SHARE_READ | FILE_SHARE_WRITE : FILE_SHARE_READ, nullptr, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT | (directory ? FILE_FLAG_BACKUP_SEMANTICS : FILE_FLAG_SEQUENTIAL_SCAN), nullptr));
    if (file.value == INVALID_HANDLE_VALUE) rejectLastError();
    FILE_ATTRIBUTE_TAG_INFO attributes{};
    if (!GetFileInformationByHandleEx(file.value, FileAttributeTagInfo, &attributes, sizeof(attributes))) rejectLastError();
    require(GetFileType(file.value) == FILE_TYPE_DISK && !(attributes.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) &&
        !!(attributes.FileAttributes & FILE_ATTRIBUTE_DIRECTORY) == directory);
    return file;
}

// Hold every canonical parent against rename; the DLL leaf handles also deny
// writes/deletion. No path is accepted from cwd, an environment or a manifest.
Path lockAppDirectory(OwnedVector<File>& parents) {
    auto path = modulePath(nullptr);
    const auto slash = path.find_last_of(L"\\/");
    require(slash != Path::npos);
    path.resize(slash + 1);
    auto directory = openFile(path, true);
    path = finalPath(directory.value);
    require(path.size() >= 7 && path.compare(0, 4, L"\\\\?\\") == 0 && path[5] == L':' && path[6] == L'\\');
    parents.push_back(openFile(path.substr(0, 7), true));
    for (std::size_t start = 7; start < path.size();) {
        auto end = path.find(L'\\', start);
        if (end == Path::npos) end = path.size();
        auto prefix = path.substr(0, end);
        auto parent = openFile(prefix, true);
        require(samePath(finalPath(parent.value), prefix));
        parents.push_back(std::move(parent));
        start = end + 1;
    }
    require(sameFile(directory.value, parents.back().value));
    return path;
}

struct Hash {
    BCRYPT_ALG_HANDLE algorithm = nullptr;
    BCRYPT_HASH_HANDLE value = nullptr;
    Hash() {
        if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) < 0) reject(E_FAIL);
        if (BCryptCreateHash(algorithm, &value, nullptr, 0, nullptr, 0, 0) < 0) {
            BCryptCloseAlgorithmProvider(algorithm, 0); algorithm = nullptr; reject(E_FAIL);
        }
    }
    ~Hash() { if (value) BCryptDestroyHash(value); if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0); }
    void add(const void* data, ULONG bytes) {
        if (BCryptHashData(value, reinterpret_cast<PUCHAR>(const_cast<void*>(data)), bytes, 0) < 0) reject(E_FAIL);
    }
    Digest finish() {
        Digest result{};
        if (BCryptFinishHash(value, result.data(), static_cast<ULONG>(result.size()), 0) < 0) reject(E_FAIL);
        return result;
    }
};
void readAt(HANDLE file, std::uint64_t offset, void* data, DWORD size) {
    LARGE_INTEGER position{}; position.QuadPart = static_cast<LONGLONG>(offset);
    if (!SetFilePointerEx(file, position, nullptr, FILE_BEGIN)) rejectLastError();
    DWORD read = 0;
    if (!ReadFile(file, data, size, &read, nullptr)) rejectLastError();
    require(read == size);
}
void verifyFile(HANDLE file, const pins::ModulePin& pin) {
    LARGE_INTEGER size{};
    if (!GetFileSizeEx(file, &size)) rejectLastError();
    require(size.QuadPart > 0 && static_cast<std::uint64_t>(size.QuadPart) == pin.bytes);
    IMAGE_DOS_HEADER dos{};
    readAt(file, 0, &dos, sizeof(dos));
    require(dos.e_magic == IMAGE_DOS_SIGNATURE && dos.e_lfanew >= static_cast<LONG>(sizeof(dos)) &&
        pin.bytes >= sizeof(IMAGE_NT_HEADERS64) && static_cast<std::uint64_t>(dos.e_lfanew) <= pin.bytes - sizeof(IMAGE_NT_HEADERS64));
    IMAGE_NT_HEADERS64 pe{};
    readAt(file, static_cast<std::uint64_t>(dos.e_lfanew), &pe, sizeof(pe));
    require(pe.Signature == IMAGE_NT_SIGNATURE && pe.FileHeader.Machine == pins::machine &&
        (pe.FileHeader.Characteristics & IMAGE_FILE_DLL) && pe.OptionalHeader.Magic == IMAGE_NT_OPTIONAL_HDR64_MAGIC);
    LARGE_INTEGER zero{};
    if (!SetFilePointerEx(file, zero, nullptr, FILE_BEGIN)) rejectLastError();
    Hash hash;
    OwnedVector<unsigned char> buffer(32 * 1024);
    std::uint64_t total = 0;
    for (;;) {
        DWORD read = 0;
        if (!ReadFile(file, buffer.data(), static_cast<DWORD>(buffer.size()), &read, nullptr)) rejectLastError();
        if (!read) break;
        require(total <= pin.bytes && read <= pin.bytes - total);
        total += read;
        hash.add(buffer.data(), read);
    }
    require(total == pin.bytes && hash.finish() == pin.sha256);
}
void verifyModule(HMODULE module, HANDLE file, const Path& expectedPath) {
    auto actual = openFile(modulePath(module), false);
    require(sameFile(actual.value, file) && samePath(finalPath(actual.value), expectedPath));
}

// Snapshot paths are MAX_PATH; use its module base only, then query the actual
// full path while holding an additional reference against concurrent unload.
void verifyLoadedNames(const std::array<File, 3>& files, const std::array<Path, 3>& paths) {
    File snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, GetCurrentProcessId()));
    if (snapshot.value == INVALID_HANDLE_VALUE) rejectLastError();
    MODULEENTRY32W entry{}; entry.dwSize = sizeof(entry);
    if (!Module32FirstW(snapshot.value, &entry)) rejectLastError();
    std::array<bool, 3> seen{};
    unsigned count = 0;
    do {
        require(++count <= 4096);
        for (std::size_t i = 0; i < files.size(); ++i) {
            if (_wcsicmp(entry.szModule, pins::modules[i].filename) != 0) continue;
            require(!seen[i]); seen[i] = true;
            ModuleRef reference;
            if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,
                reinterpret_cast<LPCWSTR>(entry.modBaseAddr), &reference.value)) rejectLastError();
            verifyModule(reference.value, files[i].value, paths[i]);
        }
    } while (Module32NextW(snapshot.value, &entry));
    if (GetLastError() != ERROR_NO_MORE_FILES) rejectLastError();
}
template<class Function> Function function(HMODULE module, const char* name) {
    const auto address = GetProcAddress(module, name);
    if (!address) rejectLastError();
    // Windows represents these addresses equally; avoid MSVC C4191 from an
    // unchecked cast between FARPROC and each exact FFmpeg function signature.
    static_assert(sizeof(Function) == sizeof(address));
    Function result = nullptr;
    std::memcpy(&result, &address, sizeof(result));
    LPCWSTR location = nullptr;
    static_assert(sizeof(location) == sizeof(address));
    std::memcpy(&location, &address, sizeof(location));
    ModuleRef owner;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS, location, &owner.value)) rejectLastError();
    require(owner.value == module); // No forwarded export into another module.
    return result;
}
void verifyConfiguration(const char* configuration) {
    require(configuration && pins::configurationBytes > 0 && pins::configurationBytes <= 16384 &&
        strnlen_s(configuration, 16385) == pins::configurationBytes);
    Hash hash; hash.add(configuration, static_cast<ULONG>(pins::configurationBytes));
    require(hash.finish() == pins::configurationSha256);
    for (const auto* flag : {"--enable-shared", "--disable-static", "--disable-everything", "--disable-autodetect",
        "--disable-gpl", "--disable-nonfree", "--disable-version3", "--disable-network", "--disable-protocols",
        "--enable-encoder=aac", "--enable-muxer=ipod"}) {
        const auto* found = std::strstr(configuration, flag);
        const auto length = std::strlen(flag);
        require(found && (found == configuration || found[-1] == ' ') && (found[length] == 0 || found[length] == ' '));
    }
}
void verifyLicense(const char* license) {
    require(license && strnlen_s(license, 256) < 256 && std::strstr(license, "LGPL"));
}
} // namespace

struct FfmpegApi::State {
    OwnedVector<File> parents;
    std::array<File, 3> files;
    std::array<HMODULE, 3> modules{};
    static void* operator new(std::size_t) { return CustodyAllocator<State>{}.allocate(1); }
    static void operator delete(void* memory) noexcept { CustodyAllocator<State>{}.deallocate(static_cast<State*>(memory), 1); }
    ~State() { for (auto i = modules.size(); i > 0; --i) if (modules[i - 1]) FreeLibrary(modules[i - 1]); }
};

void* FfmpegApi::operator new(std::size_t) { return CustodyAllocator<FfmpegApi>{}.allocate(1); }
void FfmpegApi::operator delete(void* memory) noexcept { CustodyAllocator<FfmpegApi>{}.deallocate(static_cast<FfmpegApi*>(memory), 1); }

FfmpegApi::FfmpegApi() : state_(std::make_unique<State>()) {
    LoadLock lock;
    const auto directory = lockAppDirectory(state_->parents);
    constexpr std::array<const wchar_t*, 3> names{L"avutil-59.dll", L"avcodec-61.dll", L"avformat-61.dll"};
    std::array<Path, 3> paths;
    for (std::size_t i = 0; i < paths.size(); ++i) {
        require(pins::modules[i].filename && std::wcscmp(pins::modules[i].filename, names[i]) == 0);
        paths[i] = directory + (directory.back() == L'\\' ? L"" : L"\\") + names[i];
        state_->files[i] = openFile(paths[i], false);
        require(samePath(finalPath(state_->files[i].value), paths[i]));
        verifyFile(state_->files[i].value, pins::modules[i]);
    }
    verifyLoadedNames(state_->files, paths);
    for (std::size_t i = 0; i < paths.size(); ++i) {
        state_->modules[i] = LoadLibraryExW(paths[i].c_str(), nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
        if (!state_->modules[i]) rejectLastError();
        verifyModule(state_->modules[i], state_->files[i].value, paths[i]);
    }
    verifyLoadedNames(state_->files, paths);

#define BIND(index, name) name = function<decltype(name)>(state_->modules[index], #name)
    BIND(0, av_version_info); BIND(0, avutil_version); BIND(0, avutil_configuration); BIND(0, avutil_license);
    BIND(0, av_malloc); BIND(0, av_free); BIND(0, av_freep);
    BIND(0, av_frame_alloc); BIND(0, av_frame_free);
    BIND(0, av_channel_layout_default); BIND(0, av_channel_layout_copy);
    BIND(1, avcodec_version); BIND(1, avcodec_configuration); BIND(1, avcodec_license);
    BIND(1, avcodec_find_encoder_by_name); BIND(1, avcodec_alloc_context3); BIND(1, avcodec_open2);
    BIND(1, avcodec_free_context); BIND(1, avcodec_parameters_from_context); BIND(1, avcodec_send_frame);
    BIND(1, avcodec_receive_packet); BIND(1, av_packet_alloc); BIND(1, av_packet_free);
    BIND(1, av_packet_unref); BIND(1, av_packet_rescale_ts);
    BIND(2, avformat_version); BIND(2, avformat_configuration); BIND(2, avformat_license);
    BIND(2, avformat_alloc_output_context2); BIND(2, avformat_new_stream); BIND(2, avformat_write_header);
    BIND(2, avformat_free_context); BIND(2, av_interleaved_write_frame); BIND(2, av_write_trailer);
    BIND(2, avio_alloc_context); BIND(2, avio_context_free); BIND(2, avio_flush);
#undef BIND
    require(avutil_version() == pins::modules[0].version && avcodec_version() == pins::modules[1].version &&
        avformat_version() == pins::modules[2].version);
    const auto* release = av_version_info();
    require(release && strnlen_s(release, 64) < 64 && std::strcmp(release, "7.1.5") == 0 &&
        std::strcmp(release, pins::release) == 0);
    verifyConfiguration(avutil_configuration());
    verifyConfiguration(avcodec_configuration());
    verifyConfiguration(avformat_configuration());
    verifyLicense(avutil_license()); verifyLicense(avcodec_license()); verifyLicense(avformat_license());
}

FfmpegApi::~FfmpegApi() noexcept = default;
} // namespace graf::windows
#endif
