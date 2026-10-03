cmake_minimum_required(VERSION 3.25)
project(GrafWindowsFeature200 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(WIN32)
    add_compile_definitions(WIN32_LEAN_AND_MEAN NOMINMAX UNICODE _UNICODE _WIN32_WINNT=0x0A00)
endif()

file(GLOB_RECURSE GRAF_WINDOWS_COMMON CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/RecApp/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/Native/GrafAEC3/GrafAEC3.cpp")
list(FILTER GRAF_WINDOWS_COMMON EXCLUDE REGEX ".*/AppMain\\.cpp$")
list(REMOVE_ITEM GRAF_WINDOWS_COMMON "${CMAKE_CURRENT_SOURCE_DIR}/RecApp/Storage/Sha256.cpp")
list(REMOVE_ITEM GRAF_WINDOWS_COMMON "${CMAKE_CURRENT_SOURCE_DIR}/RecApp/Storage/ProtectedCustodyFiles.cpp")
list(REMOVE_ITEM GRAF_WINDOWS_COMMON "${CMAKE_CURRENT_SOURCE_DIR}/RecApp/Storage/ProtectedCustodyPrimitives.cpp")

set(GRAF_WINDOWS_TESTS
    "Tests/GrafWindowsCoreTests/ContractFixtures.cpp"
    "Tests/GrafWindowsCoreTests/Sha256Tests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedCustodyCodecTests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedPackedCustodyFormatTests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedPackedCustodyCodecTests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp"
    "Tests/GrafWindowsCoreTests/WindowsDesktopSessionTests.cpp"
    "Tests/GrafWindowsCoreTests/RecordingAudioTimelineTests.cpp"
    "Tests/GrafWindowsCoreTests/DesktopUploadQueueV2Tests.cpp"
    "Tests/GrafWindowsCoreTests/DesktopDeletionLedgerTests.cpp"
    "Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp"
    "Tests/GrafWindowsCoreTests/MicrophoneConsentKeyTests.cpp"
    "Tests/GrafWindowsCoreTests/CaptureReasonMappingTests.cpp"
    "Tests/GrafWindowsCoreTests/RecordingOutcomeTextTests.cpp"
    "Tests/GrafWindowsCoreTests/ShellPaletteTests.cpp"
    "Tests/GrafWindowsCoreTests/WindowsAppUpdateTests.cpp"
    "Tests/GrafWindowsCoreTests/AudioNormalizerTests.cpp"
    "Tests/GrafWindowsCoreTests/VerifiedTargetPolicyTests.cpp"
    "Tests/GrafWindowsContractTests/NativeCaptureWebFailureTests.cpp"
    "Tests/GrafWindowsContractTests/WebViewRoutePolicyTests.cpp"
    "Tests/GrafWindowsContractTests/WebViewBridgeEnvelopeTests.cpp"
    "Tests/GrafWindowsContractTests/WebView2HostLifecycleTests.cpp"
    "Tests/GrafWindowsContractTests/WindowsDiagnosticsRedactionTests.cpp"
    "Tests/GrafWindowsContractTests/DesktopUploadRecoveryTests.cpp"
    "Tests/GrafWindowsContractTests/DesktopDeletionProtocolTests.cpp"
    "Tests/GrafWindowsContractTests/RecordingDeletionBridgeTests.cpp"
    "Tests/GrafWindowsContractTests/NativeSettingsBridgeTests.cpp"
    "Tests/GrafWindowsContractTests/ProductAttributionHandoffTests.cpp"
    "Tests/GrafWindowsContractTests/AutomaticRecordingPromptTests.cpp"
    "Tests/GrafWindowsPackageTests/NativeRecordingOfflineWebViewTests.cpp"
    "Tests/GrafWindowsPackageTests/V5LocalRecordingWriterTests.cpp"
    "Tests/GrafWindowsPackageTests/ShortRecordingThresholdTests.cpp"
    "Tests/GrafWindowsPackageTests/WebViewCabinetParityTests.cpp"
    "Tests/GrafWindowsPackageTests/DesktopUploadCustodySmokeTests.cpp"
    "Tests/GrafWindowsPackageTests/WindowsHardwareEvidenceSchemaTests.cpp"
    "Tests/GrafWindowsPackageTests/AutomaticRecordingSmokeTests.cpp"
    "Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp")

enable_testing()
add_library(graf_windows_hash OBJECT "RecApp/Storage/Sha256.cpp")
add_library(graf_windows_custody_files OBJECT "RecApp/Storage/ProtectedCustodyFiles.cpp")
add_library(graf_windows_custody_primitives OBJECT "RecApp/Storage/ProtectedCustodyPrimitives.cpp")
target_compile_options(graf_windows_custody_primitives PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4;/WX;/EHsc;/utf-8>
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall;-Wextra;-Wpedantic;-Werror>)
target_compile_options(graf_windows_custody_files PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4;/WX;/EHsc;/utf-8>
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall;-Wextra;-Wpedantic;-Werror>)
target_compile_options(graf_windows_hash PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4;/WX;/EHsc;/utf-8>
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall;-Wextra;-Wpedantic;-Werror>)
if(WIN32)
    list(APPEND GRAF_WINDOWS_TESTS "Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp")
    list(APPEND GRAF_WINDOWS_TESTS "Tests/GrafWindowsCoreTests/NativeCustodyProtectionFailureTests.cpp")
endif()
add_library(graf_windows_common OBJECT ${GRAF_WINDOWS_COMMON})
target_include_directories(graf_windows_common PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/RecApp"
    "${CMAKE_CURRENT_SOURCE_DIR}/Native/GrafAEC3")
target_compile_options(graf_windows_common PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4;/WX;/EHsc;/utf-8>
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall;-Wextra;-Wpedantic;-Werror>)
foreach(test_source IN LISTS GRAF_WINDOWS_TESTS)
    get_filename_component(test_name "${test_source}" NAME_WE)
    add_executable("${test_name}" "${test_source}" $<TARGET_OBJECTS:graf_windows_common>)
    # Native fault tests compile the real SHA source with TU-local CNG wrappers.
    if(NOT WIN32 OR (NOT test_name STREQUAL "NativeHashFailureTests" AND NOT test_name STREQUAL "ProtectedCustodyFilesTests"))
        target_sources("${test_name}" PRIVATE $<TARGET_OBJECTS:graf_windows_hash>)
    endif()
    if(NOT WIN32 OR (NOT test_name STREQUAL "ProtectedCustodyFilesTests" AND NOT test_name STREQUAL "ProtectedPackedCustodyOwnerTests"))
        target_sources("${test_name}" PRIVATE $<TARGET_OBJECTS:graf_windows_custody_files>)
    endif()
    # This executable compiles the real primitive with TU-local DPAPI wrappers.
    if(NOT WIN32 OR NOT test_name STREQUAL "NativeCustodyProtectionFailureTests")
        target_sources("${test_name}" PRIVATE $<TARGET_OBJECTS:graf_windows_custody_primitives>)
    endif()
    target_include_directories("${test_name}" PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/RecApp"
        "${CMAKE_CURRENT_SOURCE_DIR}/Native/GrafAEC3")
    target_compile_options("${test_name}" PRIVATE
        $<$<CXX_COMPILER_ID:MSVC>:/W4;/WX;/EHsc;/utf-8>
        $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall;-Wextra;-Wpedantic;-Werror>)
    if(WIN32)
        target_link_libraries("${test_name}" PRIVATE mfplat mfreadwrite mfuuid ole32 avrt advapi32 shell32 winhttp wintrust bcrypt crypt32 ws2_32)
    endif()
    add_test(NAME "${test_name}" COMMAND "${test_name}")
endforeach()
