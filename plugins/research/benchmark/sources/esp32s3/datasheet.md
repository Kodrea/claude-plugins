# ESP32-S3 Datasheet — Technical Specifications

Source: https://www.espressif.com/en/products/socs/esp32-s3
Source: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/index.html

## CPU & Core Architecture

- **Processor**: Dual-core Xtensa LX7 MCU
- **Clock Speed**: Up to 240 MHz
- **Architecture**: 32-bit, Harvard architecture with separate instruction and data buses

## Memory

- **Internal SRAM**: 512 KB
- **ROM**: 384 KB
- **RTC SRAM**: 16 KB (8 KB accessible by ULP coprocessor)
- **External Memory Support**: Octal SPI interface for both flash and PSRAM
  - External Flash: Up to 1 GB via SPI/QSPI/OSPI
  - External PSRAM: Up to 32 MB via Octal SPI
  - Configurable data and instruction cache (16 KB / 32 KB / 64 KB)

## Wireless Connectivity

### Wi-Fi
- **Standard**: 2.4 GHz 802.11 b/g/n
- **Bandwidth**: 20 MHz and 40 MHz support
- **Data Rate**: Up to 150 Mbps (HT40, MCS7)
- **Security**: WPA, WPA2, WPA3, WPA2-Enterprise, WPS
- **Antenna**: Internal or external via RF switch
- **Modes**: Station, SoftAP, Station+SoftAP, Promiscuous

### Bluetooth
- **Version**: Bluetooth 5 (LE)
- **Features**: Coded PHY for long-range, 2 Mbps PHY for high throughput
- **Advertising Extension**: Multiple advertisement sets, long-range advertising
- **Protocols**: BLE Mesh, iBeacon, BluFi

## GPIO & Peripherals

- **Programmable GPIOs**: 45 total (GPIO0-GPIO21 and GPIO26-GPIO48)
- **Strapping Pins**: GPIO0, GPIO3, GPIO45, GPIO46 (determine boot mode)
- **USB-JTAG Pins**: GPIO19, GPIO20 (reserved for USB-JTAG; reconfiguring disables USB-JTAG)
- **SPI Flash/PSRAM**: GPIO26-GPIO37 reserved for flash/PSRAM operations
- **Capacitive Touch Inputs**: 14 GPIOs configurable as touch sensors for HMI

### Available Peripheral APIs (ESP-IDF v5.5.3)

**Analog & Sensor Interfaces:**
- ADC Oneshot Mode Driver — Analog to Digital Converter, single-shot sampling
- ADC Continuous Mode Driver — DMA-based continuous ADC sampling
- ADC Calibration Driver — Voltage calibration for ADC readings
- Temperature Sensor — Internal temperature measurement
- Capacitive Touch Sensor — 14-channel capacitive touch input
- Touch Element — High-level touch button/slider/matrix abstractions

**Digital Communication:**
- I2C (Inter-Integrated Circuit) — Master and slave modes
- I2S (Inter-IC Sound) — Standard, PDM, and TDM modes
- SPI Master Driver — Full-duplex, half-duplex, DMA, up to 80 MHz
- SPI Slave Driver — Full-duplex slave mode
- SPI Slave Half Duplex — Segmented transfer slave mode
- UART (Universal Asynchronous Receiver/Transmitter) — Up to 5 Mbps
- TWAI (Two-Wire Automotive Interface) — CAN 2.0 compatible

**Timing & Control:**
- GPTimer (General Purpose Timer) — Hardware timers with alarm support
- LEDC (LED Control/PWM) — 8 channels, up to 40 MHz output
- MCPWM (Motor Control Pulse Width Modulator) — 2 units, 6 channels
- RMT (Remote Control Transceiver) — IR/NEC/WS2812 encoding/decoding
- PCNT (Pulse Counter) — Hardware pulse counting with limits

**Memory & Storage:**
- SPI Flash API — Internal and external flash read/write/erase
- SDMMC Host Driver — SD card via SDMMC interface (4-bit/1-bit)
- SD SPI Host Driver — SD card via SPI interface

**Signal Processing:**
- Sigma-Delta Modulation (SDM) — Digital-to-analog via pulse density
- HMAC (Hash-Based Message Authentication Code) — Hardware HMAC acceleration
- Digital Signature (DS) — RSA digital signature with protected key

**Display & Connectivity:**
- LCD — Parallel 8080/6800, SPI, I2C, and RGB interfaces
- USB Device Stack — Full-speed USB 1.1 device, CDC, HID, MSC
- USB Host — Full-speed USB 1.1 host stack

**GPIO:**
- GPIO & RTC GPIO — Standard and RTC-domain GPIO with interrupt support
- Dedicated GPIO — Fast GPIO for bit-banging with single-cycle operations

## USB-OTG

- **Standard**: USB 1.1 Full Speed (12 Mbps)
- **Modes**: Device and Host (OTG)
- **Device Classes**: CDC-ACM, HID, MSC, vendor-specific
- **Endpoints**: Up to 6 IN + 6 OUT endpoints
- **DMA**: Internal DMA for USB transfers

## AI & Processing Acceleration

- Vector instruction extensions for neural network computing and signal processing
- Acceleration through ESP-DSP and ESP-NN optimized libraries
- Hardware support for 8-bit and 16-bit integer MAC operations
- SIMD instructions for parallel data processing
- Compatible with ESP-WHO (computer vision) and ESP-Skainet (speech recognition) SDKs
- ESP-DL framework for deploying neural network models

## Security Features

- **Flash Encryption**: AES-XTS-based flash encryption (256-bit key)
- **Secure Boot**: RSA-based secure boot (RSA-3072)
- **Digital Signature**: Hardware RSA digital signature peripheral
- **HMAC**: Hardware HMAC-SHA256 acceleration
- **World Controller**: Two fully-isolated execution environments for trusted execution or privilege separation
- **eFuse**: 4096 bits of one-time-programmable memory for key storage

## Power Management

- **Ultra-Low-Power (ULP) Coprocessors**:
  - ULP-RISC-V coprocessor (32-bit RISC-V core)
  - ULP-FSM coprocessor (Finite State Machine)
- **Sleep Modes**:
  - Active: Dual-core running, radio active — ~350 mA (typical, Wi-Fi TX)
  - Modem Sleep: CPU active, radio off — ~30-68 mA
  - Light Sleep: CPU paused, RTC memory retained — ~130 µA (ULP active)
  - Deep Sleep: Only RTC memory and ULP active — ~7 µA
  - Hibernation: Only RTC timer running — ~5 µA
- **Wake-up Sources**: Timer, GPIO, touch sensor, ULP coprocessor, UART, Wi-Fi, BLE

## Operating Conditions

- **Operating Voltage**: 3.0V to 3.6V
- **Operating Temperature**: -40°C to 105°C (depending on module)
- **Packages**: QFN56 (7×7 mm)
- **Modules Available**: ESP32-S3-WROOM-1, ESP32-S3-WROOM-2, ESP32-S3-MINI-1
  - WROOM-1: PCB antenna, 4/8/16 MB Flash, 2/8 MB PSRAM options
  - WROOM-2: PCB antenna, 16/32 MB Flash, 8 MB PSRAM
  - MINI-1: PCB antenna, smaller form factor, 4/8 MB Flash
