# ESP32-S3 Community Reports — Real-World Issues and Workarounds

Source: https://github.com/espressif/esp-idf/issues/12929
Source: https://github.com/espressif/esp-idf/issues/11292
Source: https://github.com/espressif/esp-idf/issues/13292

This file collects real user reports, bug discussions, and workarounds from ESP32-S3 related GitHub issues. Content is verbatim from community sources and may contain unverified claims.

---

## Issue: Kernel Panic on I2C Master Bus Initialization (#12929)

**Title:** Kernel panic on i2c_new_master_bus (IDFGH-11838)
**Author:** babagreensheep
**Status:** CLOSED (Completed)
**Date:** January 4, 2024
**Chip:** ESP32-D0WD-V3 (revision v3.1)
**IDF Version:** v5.3-dev-1196-gece73357ca

### Problem Description

User reported encountering a "Guru Meditation Error: Core 0 panic'ed (Interrupt wdt timeout on CPU0)" when calling i2c_new_master_bus(). The function previously worked but suddenly crashed after recompilation.

### Problematic Code

```cpp
static void display_bus_initialise(unsigned char SDA, unsigned char SCL) {
    if (display_bus_initialised) return;
    i2c_master_bus_config_t display_bus_config = {
        .i2c_port = -1,
        .sda_io_num = static_cast<gpio_num_t>(SDA),
        .scl_io_num = static_cast<gpio_num_t>(SCL),
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .intr_priority = 0,
        .trans_queue_depth = 2,
        .flags = 1,
    };
    ESP_ERROR_CHECK(i2c_new_master_bus(&display_bus_config, &display_bus_handle));
}
```

### Debug Backtrace

The panic occurred immediately after GPIO configuration and interrupt allocation, with the backtrace pointing to i2c_ll_enable_intr_mask at line 204 in i2c_ll.h and i2c_new_master_bus at line 857 in i2c_master.c.

### Community Discussion

**suda-morris (Espressif, Jan 5):** Flagged that ".flags = 1, looks weird" and suggested using ".flags.enable_internal_pullup=1" instead.

**babagreensheep (Jan 5):** Responded that the simplified syntax caused compilation errors and updated configuration to use .flags = {1}.

**mbratch (Mar 7):** Reported identical issue on ESP-IDF v5.2.0 with ESP32-PICO-D4, where i2c_master_bus_add_device triggered the same watchdog timeout panic. User explicitly disabled internal pull-ups believing external pull-ups were present.

**mythbuster5 (Espressif, Mar 8):** "ESP32 has a very weird behavior, it will fail in a very incomprehensible way if no any pull-ups on pins when initialize the bus"

### Root Cause and Workaround

The ESP32 I2C peripheral requires pull-ups (either internal or external) on both SDA and SCL lines during initialization. Without them, the I2C initialization sequence hangs waiting for the bus to be idle (both lines high), triggering the watchdog timer and causing a kernel panic. This is not well-documented and catches many developers.

**Fix:** Enable internal pull-ups by setting .flags.enable_internal_pullup = true in the configuration structure, or ensure external pull-ups are properly connected.

**Gotcha:** The .flags field is a bit-field struct, not an integer. Setting .flags = 1 happens to enable internal_pullup on some compilers due to struct packing but is technically undefined behavior.

---

## Issue: CRC-8 Function Output Mismatch (#11292)

**Title:** esp_crc8_le does not match the reference output? (IDFGH-10014)
**Author:** wuyuanyi135
**Status:** CLOSED (Done)
**Date:** April 28, 2023
**Board:** ESP32-S3-WROOM-1-N16R2
**IDF Version:** v5.0.1

### Problem Description

User reported that the ESP-IDF's esp_crc8_le() function produces incorrect results compared to reference CRC calculators. When processing the string "Hi", the expected CRC-8 value from an online calculator is 0xEB, but none of the tested function variations matched this output.

### Test Code

```cpp
ESP_LOGI(TAG, "CRCLE0=0x%02x", esp_crc8_le(0, (uint8_t*)"Hi", 2));
ESP_LOGI(TAG, "CRCLE1=0x%02x", ~esp_crc8_le(0, (uint8_t*)"Hi", 2));
ESP_LOGI(TAG, "CRCLE2=0x%02x", esp_crc8_le(0xff, (uint8_t*)"Hi", 2));
ESP_LOGI(TAG, "CRCLE3=0x%02x", ~esp_crc8_le(0xff, (uint8_t*)"Hi", 2));
ESP_LOGI(TAG, "CRCBE0=0x%02x", esp_crc8_be(0, (uint8_t*)"Hi", 2));
ESP_LOGI(TAG, "CRCBE1=0x%02x", ~esp_crc8_be(0, (uint8_t*)"Hi", 2));
ESP_LOGI(TAG, "CRCBE2=0x%02x", esp_crc8_be(0xff, (uint8_t*)"Hi", 2));
ESP_LOGI(TAG, "CRCBE3=0x%02x", ~esp_crc8_be(0xff, (uint8_t*)"Hi", 2));
```

### Actual Output

```
CRCLE0=0x7d
CRCLE1=0xffffff82
CRCLE2=0x96
CRCLE3=0xffffff69
CRCBE0=0xc3
CRCBE1=0xffffff3c
CRCBE2=0x14
CRCBE3=0xffffffeb
```

None matched the expected 0xEB directly.

### Community Response

**igrr (Espressif, Apr 28):** Referenced the ESP-IDF CRC documentation and explained the function uses different parameters than the web calculator. Noted that "users can reproduce 0x7d using online tools" by configuring input/result reflection with initial value 0xFF and polynomial 0x07.

**esp-wzh (Espressif, Apr 28):** "You can also invert the result of esp_crc8_le to be consistent with CRC-8/ROHC"

### Key Takeaway

The ESP32 ROM CRC functions use different algorithm parameters than standard online CRC calculators. The function implements reflected input/output with specific polynomial and initial value settings. Users must understand the exact CRC variant implemented (not standard CRC-8) to compare results correctly.

**Common pitfall:** The ~ (bitwise NOT) operator on uint8_t return value promotes to int, producing 0xFFFFFF82 instead of 0x82. Cast to uint8_t first: (uint8_t)~esp_crc8_le(...).

---

## Issue: BLE Mesh Provisioning Data Storage Limits (#13292)

**Title:** [ble mesh] provisioning data store to sd card (IDFGH-12242)
**Author:** chegewara
**Status:** CLOSED (Completed)
**Date:** February 29, 2024
**Feature Request:** Store BLE mesh node provisioning data on SD card instead of NVS flash

### Problem Description

"If we would like to use esp32 as ble mesh provisioner then we eventually hit the nvs flash limits."

The author anticipated needing to manage 1000+ nodes, which exceeds practical NVS flash storage constraints for provisioning data on ESP32-S3 devices.

### Available APIs Identified

For exporting data:
```c
const esp_ble_mesh_node_t **esp_ble_mesh_provisioner_get_node_table_entry(void)
```

For importing data:
```c
int bt_mesh_provisioner_provision(const bt_mesh_addr_t *addr, const uint8_t uuid[16],
    uint16_t oob_info, uint16_t unicast_addr,
    uint8_t element_num, uint16_t net_idx,
    uint8_t flags, uint32_t iv_index,
    const uint8_t dev_key[16], uint16_t *index, bool nppi)
```

### Discussion

This highlights a real-world limitation when using ESP32-S3 as a BLE mesh provisioner at scale. NVS (Non-Volatile Storage) flash has limited capacity (default 24 KB partition, max ~200 key-value pairs depending on value size), making it unsuitable for storing provisioning data for large mesh networks.

The feature was addressed internally by Espressif (closed as COMPLETED on June 25, 2024), but no public documentation of the solution was provided in the issue.

### Workarounds Discussed

1. Use SDMMC or SD SPI host driver to store provisioning data on external SD card
2. Implement custom NVS backend with larger partition
3. Use external SPI flash for overflow storage
4. Export/import provisioning data via the identified APIs for backup/migration between devices

---

## Common ESP32-S3 Development Pitfalls (Aggregated from Community)

Based on recurring patterns in GitHub issues and forum discussions:

1. **I2C requires pull-ups during initialization** — Not just during communication. Missing pull-ups cause hard-to-debug kernel panics, not clean error messages.

2. **GPIO strapping pins (0, 3, 45, 46) can cause boot failures** — External connections to these pins can interfere with boot mode selection. GPIO0 pulled low enters download mode.

3. **PSRAM and flash share SPI bus GPIO26-37** — These pins cannot be used for general GPIO when PSRAM or Octal flash is enabled. This is the most common source of "why doesn't my pin work" questions.

4. **USB-JTAG on GPIO19/20 conflicts with general GPIO use** — Reconfiguring these pins disables USB-JTAG debugging permanently until reset.

5. **NVS storage limits for BLE mesh** — Default NVS partition is 24 KB, insufficient for large-scale BLE mesh deployments (1000+ nodes).

6. **CRC ROM functions use non-standard parameters** — The esp_crc8_le and esp_crc8_be functions don't match common online CRC calculators. Documentation exists but is not prominent.

7. **WiFi TX power affects memory** — Enabling WiFi with high TX power (>18 dBm) requires sufficient free heap memory. Running out of heap during WiFi operation causes silent failures or crashes.

8. **ADC2 cannot be used alongside WiFi** — ADC2 channels conflict with WiFi's use of the SAR ADC. Only ADC1 channels are safe to use when WiFi is active.

9. **Deep sleep current depends on pin state** — Floating pins during deep sleep increase leakage current significantly. Use rtc_gpio_isolate() on unused RTC GPIO pins to minimize deep sleep power consumption.

10. **SPI DMA alignment requirements** — DMA buffers must be 32-bit aligned and in DMA-capable memory. PSRAM buffers work with SPI_TRANS_DMA_USE_PSRAM flag but GPSPI bandwidth must not exceed PSRAM bandwidth.
