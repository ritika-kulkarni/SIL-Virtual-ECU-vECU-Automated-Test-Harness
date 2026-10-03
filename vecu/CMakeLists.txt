cmake_minimum_required(VERSION 3.16)
project(vecu_sil C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
option(COVERAGE "Enable gcov coverage flags" ON)
option(BUILD_TESTS "Build GTest unit tests" ON)

set(VECU_LIB_SOURCES
    src/CanIf.c
    src/PduR.c
    src/Com.c
    src/J1939App.c
)

add_library(vecu_bsw STATIC ${VECU_LIB_SOURCES})
target_include_directories(vecu_bsw PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

if(COVERAGE)
    target_compile_options(vecu_bsw PUBLIC -O0 -g --coverage)
    target_link_options(vecu_bsw PUBLIC --coverage)
endif()

add_executable(vecu_sim src/main.c)
target_link_libraries(vecu_sim PRIVATE vecu_bsw)

if(BUILD_TESTS)
    include(FetchContent)
    FetchContent_Declare(
        googletest
        URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    )
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)

    enable_testing()
    add_executable(vecu_tests
        tests/gtest_canif.cpp
        tests/gtest_pdur.cpp
        tests/gtest_com.cpp
        tests/gtest_j1939.cpp
    )
    target_link_libraries(vecu_tests PRIVATE vecu_bsw GTest::gtest_main)
    include(GoogleTest)
    # gtest_discover_tests shells out in a way that breaks on paths with
    # spaces/colons, so keep registration simple.
    add_test(NAME vecu_tests COMMAND vecu_tests)
endif()
