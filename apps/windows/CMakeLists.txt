cmake_minimum_required(VERSION 3.25)
project(GrafWindowsFeature200 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(WIN32)
    enable_language(RC)
    add_compile_definitions(WIN32_LEAN_AND_MEAN NOMINMAX UNICODE _UNICODE _WIN32_WINNT=0x0A00)
endif()

file(GLOB_RECURSE GRAF_WINDOWS_COMMON CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/RecApp/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/Native/GrafAEC3/GrafAEC3.cpp")
list(FILTER GRAF_WINDOWS_COMMON EXCLUDE REGEX ".*/AppMain\\.cpp$")
list(REMOVE_ITEM GRAF_WINDOWS_COMMON "${CMAKE_CURRENT_SOURCE_DIR}/RecApp/Storage/Sha256.cpp")
list(REMOVE_ITEM GRAF_WINDOWS_COMMON "${CMAKE_CURRENT_SOURCE_DIR}/RecApp/Storage/ProtectedCustodyFiles.cpp")
list(REMOVE_ITEM GRAF_WINDOWS_COMMON "${CMAKE_CURRENT_SOURCE_DIR}/RecApp/Storage/ProtectedCustodyPrimitives.cpp")
list(REMOVE_ITEM GRAF_WINDOWS_COMMON "${CMAKE_CURRENT_SOURCE_DIR}/RecApp/Storage/ProtectedPackedCustodyTree.cpp")
list(REMOVE_ITEM GRAF_WINDOWS_COMMON "${CMAKE_CURRENT_SOURCE_DIR}/RecApp/Upload/DesktopHttpTransport.cpp")
list(REMOVE_ITEM GRAF_WINDOWS_COMMON "${CMAKE_CURRENT_SOURCE_DIR}/RecApp/Recording/ProtectedLocalRecordingPlayback.cpp")

set(GRAF_WINDOWS_TESTS
    "Tests/GrafWindowsCoreTests/ContractFixtures.cpp"
    "Tests/GrafWindowsCoreTests/Sha256Tests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedCustodyCodecTests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedCustodyPackageTests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedPackedCustodyFormatTests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedPackedCustodyCodecTests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedCustodyWriteStreamTests.cpp"
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
    "Tests/GrafWindowsContractTests/CalendarJoinResolverTests.cpp"
    "Tests/GrafWindowsContractTests/CalendarJoinWireTests.cpp"
    "Tests/GrafWindowsContractTests/CalendarJoinHostTests.cpp"
    "Tests/GrafWindowsContractTests/CalendarJoinOperationTests.cpp"
    "Tests/GrafWindowsContractTests/CalendarMeetingUrlTests.cpp"
    "Tests/GrafWindowsContractTests/CalendarMeetingNativeTargetTests.cpp"
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
# MSVC/LTCG must agree on the inline budget counter even when another TU
# instantiates atomic<size_t> as a member before including the custody header.
add_executable(ProtectedCustodyMemoryLinkTests
    "Tests/GrafWindowsCoreTests/ProtectedCustodyMemoryLinkTests.cpp"
    "Tests/GrafWindowsCoreTests/ProtectedCustodyMemoryLinkPeer.cpp")
target_compile_options(ProtectedCustodyMemoryLinkTests PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4;/WX;/EHsc>
    $<$<AND:$<CXX_COMPILER_ID:MSVC>,$<CONFIG:Release>>:/GL>)
target_link_options(ProtectedCustodyMemoryLinkTests PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/WX>
    $<$<AND:$<CXX_COMPILER_ID:MSVC>,$<CONFIG:Release>>:/LTCG>)
add_test(NAME ProtectedCustodyMemoryLinkTests COMMAND ProtectedCustodyMemoryLinkTests)
add_library(graf_windows_hash OBJECT "RecApp/Storage/Sha256.cpp")
add_library(graf_windows_custody_files OBJECT "RecApp/Storage/ProtectedCustodyFiles.cpp")
add_library(graf_windows_custody_primitives OBJECT "RecApp/Storage/ProtectedCustodyPrimitives.cpp")
add_library(graf_windows_custody_tree OBJECT "RecApp/Storage/ProtectedPackedCustodyTree.cpp")
add_library(graf_windows_http OBJECT "RecApp/Upload/DesktopHttpTransport.cpp")
add_library(graf_windows_playback OBJECT "RecApp/Recording/ProtectedLocalRecordingPlayback.cpp")
target_compile_options(graf_windows_playback PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4;/WX;/EHsc;/utf-8>
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall;-Wextra;-Wpedantic;-Werror>)
target_compile_options(graf_windows_http PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4;/WX;/EHsc;/utf-8>
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall;-Wextra;-Wpedantic;-Werror>)
target_compile_options(graf_windows_custody_tree PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4;/WX;/EHsc;/utf-8>
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall;-Wextra;-Wpedantic;-Werror>)
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
    list(APPEND GRAF_WINDOWS_TESTS "Tests/GrafWindowsContractTests/NativeCaptureStartupTests.cpp")
    list(APPEND GRAF_WINDOWS_TESTS "Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp")
    list(APPEND GRAF_WINDOWS_TESTS "Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp")
    list(APPEND GRAF_WINDOWS_TESTS "Tests/GrafWindowsCoreTests/NativeCustodyProtectionFailureTests.cpp")
    list(APPEND GRAF_WINDOWS_TESTS "Tests/GrafWindowsContractTests/NativeCalendarJoinTransportTests.cpp")
    list(APPEND GRAF_WINDOWS_TESTS "Tests/GrafWindowsContractTests/NativeCalendarLauncherTests.cpp")
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
    if(WIN32 AND test_name STREQUAL "RecordingIndicatorTests")
        target_sources("${test_name}" PRIVATE "RecApp/GrafWindowsApp.rc")
    endif()
    # Native wire fault tests compile the production transport with local wrappers.
    if(NOT WIN32 OR NOT test_name STREQUAL "NativeCalendarJoinTransportTests")
        target_sources("${test_name}" PRIVATE $<TARGET_OBJECTS:graf_windows_http>)
    endif()
    # The integration executable holds an extra reference to the exact MF Clone.
    if(NOT WIN32 OR NOT test_name STREQUAL "NativeCaptureStorageIntegrationTests")
        target_sources("${test_name}" PRIVATE $<TARGET_OBJECTS:graf_windows_playback>)
    endif()
    # Native fault tests compile the real SHA source with TU-local CNG wrappers.
    if(NOT WIN32 OR (NOT test_name STREQUAL "NativeHashFailureTests" AND NOT test_name STREQUAL "ProtectedCustodyFilesTests"))
        target_sources("${test_name}" PRIVATE $<TARGET_OBJECTS:graf_windows_hash>)
    endif()
    if(NOT WIN32 OR (NOT test_name STREQUAL "ProtectedCustodyFilesTests" AND NOT test_name STREQUAL "ProtectedPackedCustodyOwnerTests" AND NOT test_name STREQUAL "ProtectedCustodyWriteStreamTests" AND NOT test_name STREQUAL "NativeCaptureStorageIntegrationTests"))
        target_sources("${test_name}" PRIVATE $<TARGET_OBJECTS:graf_windows_custody_files>)
    endif()
    # Owner fault tests compile the real tree with TU-local codec wrappers.
    if(NOT WIN32 OR NOT test_name STREQUAL "ProtectedPackedCustodyOwnerTests")
        target_sources("${test_name}" PRIVATE $<TARGET_OBJECTS:graf_windows_custody_tree>)
    endif()
    # This executable compiles the real primitive with TU-local DPAPI wrappers.
    if(NOT WIN32 OR NOT test_name STREQUAL "NativeCustodyProtectionFailureTests")
        target_sources("${test_name}" PRIVATE $<TARGET_OBJECTS:graf_windows_custody_primitives>)
    endif()
    target_include_directories("${test_name}" PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/RecApp"
        "${CMAKE_CURRENT_SOURCE_DIR}/Native/GrafAEC3")
    target_compile_options("${test_name}" PRIVATE
        $<$<COMPILE_LANG_AND_ID:CXX,MSVC>:/W4;/WX;/EHsc;/utf-8>
        $<$<AND:$<COMPILE_LANGUAGE:CXX>,$<NOT:$<CXX_COMPILER_ID:MSVC>>>:-Wall;-Wextra;-Wpedantic;-Werror>)
    if(WIN32)
        target_link_libraries("${test_name}" PRIVATE windowsapp mfplat mfreadwrite mfuuid ole32 oleaut32 avrt advapi32 shell32 winhttp wintrust bcrypt crypt32 ws2_32)
        if(test_name STREQUAL "NativeCaptureStorageIntegrationTests")
            target_link_libraries("${test_name}" PRIVATE dbghelp)
        endif()
    endif()
    add_test(NAME "${test_name}" COMMAND "${test_name}")
endforeach()
if(WIN32)
    add_test(NAME NativeProtectedBirthAdmission COMMAND NativeCaptureStorageIntegrationTests --protected-birth-admission)
    add_test(NAME NativeProtectedLiveMetadata COMMAND NativeCaptureStorageIntegrationTests --protected-live-metadata)
    add_test(NAME NativeProtectedPrivacyManifest COMMAND NativeCaptureStorageIntegrationTests --protected-privacy-manifest)
    add_test(NAME NativeProtectedPrivacyFlow COMMAND NativeCaptureStorageIntegrationTests --protected-privacy-flow)
    add_test(NAME NativeProtectedPrivacyDegraded COMMAND NativeCaptureStorageIntegrationTests --protected-privacy-degraded)
    add_test(NAME NativeProtectedRecordingSemantics COMMAND ProtectedCustodyFilesTests --recording-semantics)
    add_test(NAME NativeProtectedInspectionPreparation COMMAND NativeCaptureStorageIntegrationTests --protected-inspection-prepared)
    add_test(NAME NativeProtectedFinalizeAdmission COMMAND NativeCaptureStorageIntegrationTests --protected-finalize-admission)
    add_test(NAME NativeProtectedInspectionActiveStop COMMAND NativeCaptureStorageIntegrationTests --protected-inspection-active-stop)
    add_test(NAME NativeProtectedEncoderWriteFailure COMMAND NativeCaptureStorageIntegrationTests --protected-encoder-write-failure)
    add_test(NAME NativeProtectedReadModel COMMAND NativeCaptureStorageIntegrationTests --protected-read-model)
    add_test(NAME NativeProtectedDeletionIntent COMMAND NativeCaptureStorageIntegrationTests --protected-deletion-intent)
    add_test(NAME NativeProtectedDeletionAnswer COMMAND NativeCaptureStorageIntegrationTests --protected-deletion-answer)
    add_test(NAME NativeProtectedDeletionSelection COMMAND NativeCaptureStorageIntegrationTests --protected-deletion-selection)
    add_test(NAME NativeProtectedDeletionContinuation COMMAND NativeCaptureStorageIntegrationTests --protected-deletion-continuation)
    add_test(NAME NativeProtectedDeletionApplication COMMAND NativeCaptureStorageIntegrationTests --protected-deletion-application)
    add_test(NAME NativeProtectedDeletionDisplay COMMAND NativeCaptureStorageIntegrationTests --protected-deletion-display)
    add_test(NAME NativeProtectedLocalPurge COMMAND NativeCaptureStorageIntegrationTests --protected-local-purge)
    set_tests_properties(NativeProtectedLocalPurge PROPERTIES RUN_SERIAL TRUE TIMEOUT 240)
    add_test(NAME NativeProtectedLocalRemoval COMMAND NativeCaptureStorageIntegrationTests --protected-local-removal)
    set_tests_properties(NativeProtectedLocalRemoval PROPERTIES RUN_SERIAL TRUE TIMEOUT 240)
    add_test(NAME NativeProtectedServerPurge COMMAND NativeCaptureStorageIntegrationTests --protected-server-purge)
    set_tests_properties(NativeProtectedServerPurge PROPERTIES RUN_SERIAL TRUE TIMEOUT 240)
    add_test(NAME NativeProtectedPurgeFlight COMMAND NativeCaptureStorageIntegrationTests --protected-purge-flight)
    add_test(NAME NativeProtectedManualSend COMMAND NativeCaptureStorageIntegrationTests --protected-manual-send)
    set_tests_properties(NativeProtectedManualSend PROPERTIES RUN_SERIAL TRUE TIMEOUT 240)
    set_tests_properties(NativeProtectedPurgeFlight PROPERTIES RUN_SERIAL TRUE TIMEOUT 240)
    add_test(NAME NativeProtectedAccountProblems COMMAND NativeCaptureStorageIntegrationTests --protected-account-problems)
    add_test(NAME NativeProtectedDisplayTiming COMMAND NativeCaptureStorageIntegrationTests --protected-display-timing)
    add_test(NAME NativeProtectedDisplayOwnerQuota COMMAND NativeCaptureStorageIntegrationTests --protected-display-owner-quota)
    add_test(NAME NativeProtectedMetadataReadAdmission COMMAND ProtectedCustodyFilesTests --readonly-files-admission)
    add_test(NAME NativeProtectedOwnerCancellation COMMAND ProtectedCustodyFilesTests --readonly-owner-cancellation)
    add_test(NAME NativeProtectedReaderReleaseDrain COMMAND ProtectedPackedCustodyTreeTests --reader-release-drain)
    add_test(NAME NativeProtectedMediaEngine COMMAND NativeCaptureStorageIntegrationTests --protected-media-engine)
    add_test(NAME NativeProtectedPlaybackConsumer COMMAND NativeCaptureStorageIntegrationTests --protected-playback-consumer)
    add_test(NAME NativeProtectedPackageRevalidation COMMAND NativeCaptureStorageIntegrationTests --protected-package-revalidation)
    add_test(NAME NativeProtectedLiveBornInspection COMMAND NativeCaptureStorageIntegrationTests --protected-live-born-inspection)
    set_tests_properties(NativeProtectedPrivacyManifest NativeProtectedPrivacyFlow NativeProtectedPrivacyDegraded NativeProtectedRecordingSemantics NativeProtectedLiveMetadata NativeProtectedBirthAdmission NativeProtectedInspectionPreparation
        NativeProtectedFinalizeAdmission NativeProtectedInspectionActiveStop NativeProtectedEncoderWriteFailure
        NativeProtectedReadModel NativeProtectedDeletionIntent NativeProtectedDeletionAnswer NativeProtectedDeletionSelection NativeProtectedDeletionContinuation NativeProtectedDeletionDisplay NativeProtectedAccountProblems NativeProtectedDisplayTiming NativeProtectedDisplayOwnerQuota
        NativeProtectedMetadataReadAdmission NativeProtectedOwnerCancellation NativeProtectedReaderReleaseDrain
        NativeProtectedMediaEngine NativeProtectedPlaybackConsumer NativeProtectedPackageRevalidation NativeProtectedLiveBornInspection PROPERTIES RUN_SERIAL TRUE)
endif()
