cmake_minimum_required(VERSION 3.25)
project(GrafWindowsFeature200 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

file(GLOB_RECURSE GRAF_WINDOWS_COMMON CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/RecApp/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/Native/GrafAEC3/GrafAEC3.cpp")
list(FILTER GRAF_WINDOWS_COMMON EXCLUDE REGEX ".*/AppMain\\.cpp$")

set(GRAF_WINDOWS_TESTS
    "Tests/GrafWindowsCoreTests/ContractFixtures.cpp"
    "Tests/GrafWindowsCoreTests/WindowsDesktopSessionTests.cpp"
    "Tests/GrafWindowsCoreTests/RecordingAudioTimelineTests.cpp"
    "Tests/GrafWindowsCoreTests/DesktopUploadQueueV2Tests.cpp"
    "Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp"
    "Tests/GrafWindowsCoreTests/VerifiedTargetPolicyTests.cpp"
    "Tests/GrafWindowsContractTests/NativeCaptureWebFailureTests.cpp"
    "Tests/GrafWindowsContractTests/WebViewRoutePolicyTests.cpp"
    "Tests/GrafWindowsContractTests/WebViewBridgeEnvelopeTests.cpp"
    "Tests/GrafWindowsContractTests/WindowsDiagnosticsRedactionTests.cpp"
    "Tests/GrafWindowsContractTests/DesktopUploadRecoveryTests.cpp"
    "Tests/GrafWindowsContractTests/AutomaticRecordingPromptTests.cpp"
    "Tests/GrafWindowsPackageTests/NativeRecordingOfflineWebViewTests.cpp"
    "Tests/GrafWindowsPackageTests/V5LocalRecordingWriterTests.cpp"
    "Tests/GrafWindowsPackageTests/WebViewCabinetParityTests.cpp"
    "Tests/GrafWindowsPackageTests/DesktopUploadCustodySmokeTests.cpp"
    "Tests/GrafWindowsPackageTests/WindowsHardwareEvidenceSchemaTests.cpp"
    "Tests/GrafWindowsPackageTests/AutomaticRecordingSmokeTests.cpp"
    "Tests/GrafWindowsPackageTests/AccessibilityAndBrandDistanceTests.cpp")

enable_testing()
add_library(graf_windows_common OBJECT ${GRAF_WINDOWS_COMMON})
target_include_directories(graf_windows_common PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/RecApp"
    "${CMAKE_CURRENT_SOURCE_DIR}/Native/GrafAEC3")
target_compile_options(graf_windows_common PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4;/WX>
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall;-Wextra;-Wpedantic;-Werror>)
foreach(test_source IN LISTS GRAF_WINDOWS_TESTS)
    get_filename_component(test_name "${test_source}" NAME_WE)
    add_executable("${test_name}" "${test_source}" $<TARGET_OBJECTS:graf_windows_common>)
    target_include_directories("${test_name}" PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/RecApp"
        "${CMAKE_CURRENT_SOURCE_DIR}/Native/GrafAEC3")
    target_compile_options("${test_name}" PRIVATE
        $<$<CXX_COMPILER_ID:MSVC>:/W4;/WX>
        $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall;-Wextra;-Wpedantic;-Werror>)
    if(WIN32)
        target_link_libraries("${test_name}" PRIVATE mfplat mfreadwrite mfuuid ole32 avrt)
    endif()
    add_test(NAME "${test_name}" COMMAND "${test_name}")
endforeach()
