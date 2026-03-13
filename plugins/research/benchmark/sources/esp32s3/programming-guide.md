# ESP-IDF Programming Guide — Build System and Development Workflow

Source: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/build-system.html
Source: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/get-started/index.html

## Overview

The ESP-IDF build system is CMake-based, organizing projects into modular components that compile into static libraries and link to create applications. A project comprises one main app executable and a bootloader app, with configuration managed through the sdkconfig file.

## Getting Started

### Hardware Requirements
- ESP32-S3 development board
- USB cable (USB A / Micro-B or USB Type-C depending on board)
- Windows, Linux, or macOS computer

### Software Requirements
- **Toolchain**: Xtensa compiler for ESP32-S3
- **Build tools**: CMake and Ninja for application compilation
- **ESP-IDF**: API libraries, source code, and toolchain scripts
- **ESP-IDF version**: v5.5.3 (stable)

### Installation Options
1. **IDE Integration**: Eclipse Plugin or VSCode Extension
2. **Manual Installation**: Platform-specific guides for Windows, Linux, and macOS

## Project Structure

A typical ESP-IDF project follows this organization:

```
myProject/
├── CMakeLists.txt                 # Top-level project configuration
├── sdkconfig                       # Project configuration file
├── dependencies.lock              # Managed component versions
├── bootloader_components/
│   └── main/                       # Custom bootloader (optional)
├── components/                     # Custom project components
│   ├── component1/
│   │   ├── CMakeLists.txt
│   │   ├── Kconfig
│   │   └── src/
│   └── component2/
├── managed_components/             # IDF Component Manager packages
├── main/                           # Default main component
│   ├── CMakeLists.txt
│   ├── src/
│   └── idf_component.yml
└── build/                          # Build artifacts directory
```

## Project CMakeLists.txt

The minimal project-level CMakeLists.txt requires:

```cmake
cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(myProject)
```

### Optional Project Variables

Variables can be set between cmake_minimum_required() and include():

| Variable | Purpose |
|-|-|
| COMPONENT_DIRS | Directories to search for components |
| EXTRA_COMPONENT_DIRS | Additional component search paths |
| COMPONENTS | List of components to build (limits build scope) |
| SDKCONFIG_DEFAULTS | Default configuration file(s) |
| BOOTLOADER_IGNORE_EXTRA_COMPONENT | Conditionally exclude bootloader components |

## Component CMakeLists.txt

Each component requires a CMakeLists.txt registering itself:

```cmake
idf_component_register(SRCS "foo.c" "bar.c"
                       INCLUDE_DIRS "include"
                       REQUIRES mbedtls
                       PRIV_REQUIRES console)
```

### idf_component_register() Arguments

| Argument | Description |
|-|-|
| SRCS | Source files (*.c, *.cpp, *.cc, *.S) |
| SRC_DIRS | Directories to glob for source files |
| EXCLUDE_SRCS | Files to exclude when using SRC_DIRS |
| INCLUDE_DIRS | Public header directories |
| PRIV_INCLUDE_DIRS | Private header directories |
| REQUIRES | Public component dependencies |
| PRIV_REQUIRES | Private component dependencies |
| LDFRAGMENTS | Linker fragment files |
| REQUIRED_IDF_TARGETS | Target chips this component supports |
| EMBED_FILES | Binary files to embed in flash |
| EMBED_TXTFILES | Text files to embed as null-terminated strings |
| KCONFIG | Component configuration menu file |
| WHOLE_ARCHIVE | Include entire component library in final binary |

### Component Dependencies

**REQUIRES** lists components whose public headers are included in this component's public headers (transitive dependencies):

```cmake
idf_component_register(SRCS "car.c"
                       INCLUDE_DIRS "."
                       REQUIRES engine)
```

**PRIV_REQUIRES** lists components used internally but not exposed in public headers:

```cmake
idf_component_register(SRCS "engine.c"
                       INCLUDE_DIRS "include"
                       PRIV_REQUIRES spark_plug)
```

### Common Components (Auto-Required)

These are automatically required by every component:
cxx, newlib, freertos, esp_hw_support, heap, log, soc, hal, esp_rom, esp_common, esp_system, xtensa/riscv

### Component Search Precedence

1. Project components (highest priority)
2. EXTRA_COMPONENT_DIRS components
3. IDF Component Manager managed_components
4. ESP-IDF components (lowest priority)

## idf.py Command-Line Tool

```bash
idf.py build              # Configure and build project
idf.py clean              # Remove build artifacts
idf.py menuconfig         # Interactive configuration menu
idf.py flash              # Build and flash to device
idf.py monitor            # Open serial monitor
idf.py fullclean          # Remove entire build directory
idf.py reconfigure        # Re-run CMake configuration
idf.py set-target esp32s3 # Change target chip
```

### Environment Variables

| Variable | Purpose |
|-|-|
| IDF_PATH | Path to ESP-IDF directory (required) |
| ESPPORT | Serial port (/dev/ttyUSB0, COM3, etc.) |
| ESPBAUD | Flash baud rate (default 460800) |
| IDF_TARGET | Target chip name (esp32, esp32s3, etc.) |

### Direct CMake Usage

```bash
mkdir -p build
cd build
cmake .. -G Ninja
ninja
```

## Configuration System (Kconfig)

Components define configuration options via Kconfig files:

```kconfig
config FOO_ENABLE_BAR
    bool "Enable the BAR feature."
    help
        This enables the BAR feature of the FOO component.
```

Accessed in CMakeLists.txt as CONFIG_FOO_ENABLE_BAR:

```cmake
if(CONFIG_FOO_ENABLE_BAR)
    list(APPEND srcs "bar.c")
endif()
```

### sdkconfig Files

- **sdkconfig** — Project configuration (modified by menuconfig)
- **sdkconfig.defaults** — Default values for new projects
- **sdkconfig.defaults.TARGET_NAME** — Target-specific defaults (e.g., sdkconfig.defaults.esp32s3)

Files applied in order:
1. sdkconfig.defaults
2. sdkconfig.defaults.TARGET_NAME
3. Custom SDKCONFIG_DEFAULTS files

## Build Metadata

After building, the build/ directory contains:

| File | Purpose |
|-|-|
| flash_project_args | esptool.py arguments for full project flash |
| flash_app_args | Arguments for app-only flash |
| flash_bootloader_args | Arguments for bootloader-only flash |
| flasher_args.json | Project flash info in JSON format |
| component_depends.cmake | Generated component dependency graph |

Flash using saved arguments:
```bash
python esptool.py --chip esp32s3 write_flash @build/flash_project_args
```

## Embedding Binary Data

```cmake
idf_component_register(
    SRCS "foo.c"
    EMBED_FILES "server_root_cert.der"
    EMBED_TXTFILES "server_root_cert.pem"
)
```

Access via generated symbols:
```c
extern const uint8_t server_root_cert_pem_start[] asm("_binary_server_root_cert_pem_start");
extern const uint8_t server_root_cert_pem_end[] asm("_binary_server_root_cert_pem_end");
```

## Bootloader Building

Bootloader is a special subproject in /components/bootloader/subproject:
- Shares configuration and build directory with main project
- Override with bootloader_components/main/ directory
- Use BOOTLOADER_IGNORE_EXTRA_COMPONENT for conditional exclusion

## Component Manager (idf_component.yml)

Optional manifest for managed dependencies:

```yaml
version: "1.0.0"
description: "Component description"
dependencies:
  mbedtls: "^2.0"
```

Automatically generates dependencies.lock tracking component versions.

## Preset Build Variables

Available within component CMakeLists:

| Variable | Description |
|-|-|
| COMPONENT_DIR | Absolute path to component directory |
| COMPONENT_NAME | Component directory name |
| CONFIG_* | Configuration values from sdkconfig |
| ESP_PLATFORM | Set to 1 during ESP-IDF build |
| IDF_VER | Git version string |
| IDF_TARGET | Target chip (esp32s3) |

## Compiler Control

### Component-specific compile options:
```cmake
target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-unused-variable)
```

### Per-file compile options:
```cmake
set_source_files_properties(mysrc.c
    PROPERTIES COMPILE_FLAGS -Wno-unused-variable)
```

### Global build specifications:
```cmake
idf_build_set_property(COMPILE_OPTIONS "-Wno-error" APPEND)
idf_build_set_property(COMPILE_DEFINITIONS "MY_DEFINE=1" APPEND)
```

## Advanced Features

### Using External CMake Projects

```cmake
idf_component_register()
add_subdirectory(foo)
target_link_libraries(${COMPONENT_LIB} PUBLIC foo)
```

### Prebuilt Libraries

```cmake
add_prebuilt_library(target_name lib/libfoo.a
                     REQUIRES esp32
                     PRIV_REQUIRES log)
```

### Function Wrappers

```cmake
target_link_libraries(${COMPONENT_LIB} INTERFACE "-Wl,--wrap=function_to_redefine")
```

Implementation:
```c
int __wrap_function_to_redefine(int x) {
    return __real_function_to_redefine(x);
}
```

### Minimal Build Configuration

```cmake
set(COMPONENTS main esp32 freertos)
```

Or: `idf_build_set_property(MINIMAL_BUILD ON)`

## Partition Tables

ESP32-S3 flash is divided into partitions for app, data, OTA, NVS, etc. Configured via CSV file:

```csv
# Name,   Type, SubType, Offset,  Size, Flags
nvs,      data, nvs,     0x9000,  0x6000,
phy_init, data, phy,     0xf000,  0x1000,
factory,  app,  factory, 0x10000, 1M,
```

The partition table itself is flashed at offset 0x8000 (default). Maximum 95 entries.
