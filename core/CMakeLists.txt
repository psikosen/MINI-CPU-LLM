cmake_minimum_required(VERSION 3.16)
project(voice_core VERSION 1.0.0 LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 11)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Compiler flags for optimization on ARM
if(CMAKE_SYSTEM_PROCESSOR MATCHES "arm|aarch64")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -mcpu=native -O2")
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -mcpu=native -O2")
endif()

# Find required packages
find_package(Threads REQUIRED)
find_package(PkgConfig REQUIRED)

# Find ALSA
pkg_check_modules(ALSA REQUIRED alsa)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/lib
    ${ALSA_INCLUDE_DIRS}
)

# Source files
set(SOURCES
    src/main.cpp
    src/ipc_server.cpp
    src/audio_capture.cpp
    src/audio_playback.cpp
    src/vad_detector.cpp
    src/wake_word.cpp
    src/audio_buffer.cpp
)

# Main executable
add_executable(voice_core ${SOURCES})

# Link libraries
target_link_libraries(voice_core
    Threads::Threads
    ${ALSA_LIBRARIES}
    m
    dl
    rt
)

# Installation
install(TARGETS voice_core DESTINATION /usr/local/bin)

# Optional: Build tests
option(BUILD_TESTS "Build test suite" OFF)
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()
