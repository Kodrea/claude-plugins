# ESP32-S3 Hardware Reference — GPIO and SPI Peripheral APIs

Source: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/gpio.html
Source: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/spi_master.html

## GPIO API Technical Reference

### GPIO Pin Overview

The ESP32-S3 features 45 physical GPIO pins (GPIO0-GPIO21 and GPIO26-GPIO48). Each pin supports flexible configuration through GPIO matrix, IO MUX, and RTC IO MUX, enabling peripheral signal routing to any pin.

#### Pin Categories

**Strapping Pins:** GPIO0, GPIO3, GPIO45, GPIO46 determine boot mode and must be held at specific levels during startup.

**USB-JTAG Pins:** GPIO19 and GPIO20 are reserved for USB-JTAG functionality; reconfiguring them disables USB-JTAG.

**SPI Flash/PSRAM:** GPIO26-GPIO37 reserved for flash/PSRAM operations; GPIO33-GPIO37 additionally connected to Octal interface signals.

**RTC GPIO Support:** All GPIO0-GPIO21 support RTC GPIO functionality for deep-sleep, ULP coprocessor, and analog operations.

### GPIO Configuration Modes

#### gpio_mode_t Enumeration

```c
GPIO_MODE_DISABLE        // Input and output disabled
GPIO_MODE_INPUT          // Input only
GPIO_MODE_OUTPUT         // Output only
GPIO_MODE_OUTPUT_OD      // Output with open-drain
GPIO_MODE_INPUT_OUTPUT   // Bidirectional
GPIO_MODE_INPUT_OUTPUT_OD // Bidirectional open-drain
```

#### Pull-up/Pull-down Configuration

```c
GPIO_PULLUP_DISABLE      // Disable internal pull-up
GPIO_PULLUP_ENABLE       // Enable internal pull-up
GPIO_PULLDOWN_DISABLE    // Disable internal pull-down
GPIO_PULLDOWN_ENABLE     // Enable internal pull-down
GPIO_PULLUP_ONLY         // Pull-up only
GPIO_PULLDOWN_ONLY       // Pull-down only
GPIO_PULLUP_PULLDOWN     // Both enabled
GPIO_FLOATING            // Neither enabled
```

### Interrupt Configuration

#### gpio_int_type_t Enumeration

```c
GPIO_INTR_DISABLE        // Interrupt disabled
GPIO_INTR_POSEDGE        // Rising edge trigger
GPIO_INTR_NEGEDGE        // Falling edge trigger
GPIO_INTR_ANYEDGE        // Both edges trigger
GPIO_INTR_LOW_LEVEL      // Low level trigger
GPIO_INTR_HIGH_LEVEL     // High level trigger
```

### Drive Strength Configuration

#### gpio_drive_cap_t Enumeration

```c
GPIO_DRIVE_CAP_0         // Weak drive capability
GPIO_DRIVE_CAP_1         // Stronger drive capability
GPIO_DRIVE_CAP_2         // Medium (default)
GPIO_DRIVE_CAP_3         // Strongest drive capability
GPIO_DRIVE_CAP_DEFAULT   // Medium (default)
```

### Core API Functions

#### Basic Configuration

**esp_err_t gpio_config(const gpio_config_t *pGPIOConfig)**
Configures GPIO mode, pull-up, pull-down, and interrupt type. Note: "This function always overwrite all the current IO configurations."

**esp_err_t gpio_reset_pin(gpio_num_t gpio_num)**
Resets GPIO to default state: selects GPIO function, enables pull-up, disables input/output.

#### Output Operations

**esp_err_t gpio_set_level(gpio_num_t gpio_num, uint32_t level)**
Sets GPIO output level (0 or 1). Allowed during ISR with CONFIG_GPIO_CTRL_FUNC_IN_IRAM enabled.

**esp_err_t gpio_set_drive_capability(gpio_num_t gpio_num, gpio_drive_cap_t strength)**
Configures pad drive capability for output GPIOs.

#### Input Operations

**int gpio_get_level(gpio_num_t gpio_num)**
Reads GPIO input level; returns 0 or 1. Returns 0 if pin not configured for input.

### Interrupt Management

#### Per-Pin ISR Service

```c
esp_err_t gpio_install_isr_service(int intr_alloc_flags)
void gpio_uninstall_isr_service(void)
esp_err_t gpio_isr_handler_add(gpio_num_t gpio_num, gpio_isr_t isr_handler, void *args)
esp_err_t gpio_isr_handler_remove(gpio_num_t gpio_num)
```

#### Global ISR Registration

```c
esp_err_t gpio_isr_register(void (*fn)(void*), void *arg, int intr_alloc_flags, gpio_isr_handle_t *handle)
```

### Sleep and Hold Functions

#### Pad Hold

```c
esp_err_t gpio_hold_en(gpio_num_t gpio_num)   // Latch current pin state
esp_err_t gpio_hold_dis(gpio_num_t gpio_num)  // Release latch
void gpio_deep_sleep_hold_en(void)            // Enable for all pins during deep-sleep
void gpio_deep_sleep_hold_dis(void)           // Disable deep-sleep hold
```

### Wake-up Functions

```c
esp_err_t gpio_wakeup_enable(gpio_num_t gpio_num, gpio_int_type_t intr_type)
esp_err_t gpio_wakeup_disable(gpio_num_t gpio_num)
```

Only GPIO_INTR_LOW_LEVEL or GPIO_INTR_HIGH_LEVEL supported for wake-up.

### Configuration Structures

#### gpio_config_t

```c
typedef struct {
    uint64_t pin_bit_mask;        // GPIO pins (bit mask)
    gpio_mode_t mode;              // Input/output mode
    gpio_pullup_t pull_up_en;      // Pull-up enable
    gpio_pulldown_t pull_down_en;  // Pull-down enable
    gpio_int_type_t intr_type;     // Interrupt type
} gpio_config_t;
```

### RTC GPIO API

RTC GPIO functions operate when GPIO routed to RTC subsystem, enabling functionality during deep-sleep and with ULP coprocessors.

```c
bool rtc_gpio_is_valid_gpio(gpio_num_t gpio_num)
int rtc_io_number_get(gpio_num_t gpio_num)    // Returns index or -1
esp_err_t rtc_gpio_init(gpio_num_t gpio_num)
esp_err_t rtc_gpio_deinit(gpio_num_t gpio_num)
uint32_t rtc_gpio_get_level(gpio_num_t gpio_num)
esp_err_t rtc_gpio_set_level(gpio_num_t gpio_num, uint32_t level)
esp_err_t rtc_gpio_set_direction(gpio_num_t gpio_num, rtc_gpio_mode_t mode)
esp_err_t rtc_gpio_isolate(gpio_num_t gpio_num)
```

`rtc_gpio_isolate`: "Disables input, output, pullup, pulldown, and enables hold feature" to minimize leakage current.

#### rtc_gpio_mode_t Enumeration

```c
RTC_GPIO_MODE_INPUT_ONLY      // Input only
RTC_GPIO_MODE_OUTPUT_ONLY     // Output only
RTC_GPIO_MODE_INPUT_OUTPUT    // Bidirectional
RTC_GPIO_MODE_DISABLED        // Input/output disabled
RTC_GPIO_MODE_OUTPUT_OD       // Open-drain output
RTC_GPIO_MODE_INPUT_OUTPUT_OD // Bidirectional open-drain
```

### GPIO Glitch Filter API

Hardware filters remove unwanted glitch pulses shorter than two sample clock cycles.

```c
esp_err_t gpio_new_pin_glitch_filter(const gpio_pin_glitch_filter_config_t *config,
                                      gpio_glitch_filter_handle_t *ret_filter)
esp_err_t gpio_new_flex_glitch_filter(const gpio_flex_glitch_filter_config_t *config,
                                       gpio_glitch_filter_handle_t *ret_filter)
esp_err_t gpio_glitch_filter_enable(gpio_glitch_filter_handle_t filter)
esp_err_t gpio_glitch_filter_disable(gpio_glitch_filter_handle_t filter)
```

#### Filter Configurations

```c
typedef struct {
    glitch_filter_clock_source_t clk_src;
    gpio_num_t gpio_num;
} gpio_pin_glitch_filter_config_t;

typedef struct {
    glitch_filter_clock_source_t clk_src;
    gpio_num_t gpio_num;
    uint32_t window_width_ns;               // Sample window width (ns)
    uint32_t window_thres_ns;               // Threshold width (ns)
} gpio_flex_glitch_filter_config_t;
```

### Return Values

All functions return esp_err_t:
- **ESP_OK**: Success
- **ESP_ERR_INVALID_ARG**: Invalid parameter
- **ESP_ERR_NOT_FOUND**: Resource not found
- **ESP_ERR_NO_MEM**: Memory allocation failure
- **ESP_ERR_INVALID_STATE**: Invalid state
- **ESP_FAIL**: General failure

---

## SPI Master API Technical Reference

### Overview

The SPI Master driver controls ESP32-S3's General Purpose SPI (GP-SPI) peripheral when functioning as a master. The driver supports multi-threaded environments with transparent DMA handling and automatic time-division multiplexing across multiple devices.

### Bus Configuration & Initialization

#### Core Structure: spi_bus_config_t

Configures GPIO pins for the SPI bus:
- `mosi_io_num` / `data0_io_num`: Master Out, Slave In pin (-1 if unused)
- `miso_io_num` / `data1_io_num`: Master In, Slave Out pin (-1 if unused)
- `sclk_io_num`: Serial Clock pin
- `quadwp_io_num` / `data2_io_num`: Write Protect / data2 signal
- `quadhd_io_num` / `data3_io_num`: Hold / data3 signal
- `data4_io_num` through `data7_io_num`: Additional data lines for octal mode
- `max_transfer_sz`: Maximum transfer size in bytes (defaults to 4092 with DMA, SOC_SPI_MAXIMUM_BUFFER_SIZE without)
- `flags`: Bus capability flags (SPICOMMON_BUSFLAG_* constants)

#### Bus Initialization

```c
esp_err_t spi_bus_initialize(spi_host_device_t host_id,
                              const spi_bus_config_t *bus_config,
                              spi_dma_chan_t dma_chan)
```

**Parameters:**
- `host_id`: SPI peripheral (SPI2_HOST or SPI3_HOST; SPI0/1 not supported)
- `dma_chan`: SPI_DMA_DISABLED, SPI_DMA_CH_AUTO, or specific channel

### Device Configuration: spi_device_interface_config_t

- `command_bits`: Command phase width (0-16 bits)
- `address_bits`: Address phase width (0-64 bits)
- `dummy_bits`: Dummy bits between address and data phases
- `mode`: SPI mode (0-3, representing CPOL/CPHA pairs)
- `clock_speed_hz`: Desired SPI clock frequency in Hz
- `input_delay_ns`: Slave data valid time from SCLK launch edge
- `spics_io_num`: Chip Select GPIO pin (-1 if unused)
- `flags`: Device-specific flags (SPI_DEVICE_* constants)
- `queue_size`: Transaction queue depth
- `pre_cb`: Pre-transmission callback (transaction_cb_t)
- `post_cb`: Post-transmission callback

### Transaction Structure: spi_transaction_t

- `flags`: Transaction-specific flags (SPI_TRANS_* constants)
- `cmd`: Command data (length set in device config)
- `addr`: Address data (0-64 bits)
- `length`: Total data phase length in bits
- `rxlength`: Receive length in bits (0 defaults to length in full-duplex)
- `tx_buffer`: Transmit data pointer (NULL for no MOSI phase)
- `tx_data[4]`: Embedded transmit data when SPI_TRANS_USE_TXDATA set
- `rx_buffer`: Receive data pointer (NULL for no MISO phase)
- `rx_data[4]`: Embedded receive data when SPI_TRANS_USE_RXDATA set

### Data Transfer Modes

#### Interrupt Transactions

```c
esp_err_t spi_device_queue_trans(spi_device_handle_t handle,
                                  spi_transaction_t *trans_desc,
                                  TickType_t ticks_to_wait)
esp_err_t spi_device_get_trans_result(spi_device_handle_t handle,
                                       spi_transaction_t **trans_desc,
                                       TickType_t ticks_to_wait)
esp_err_t spi_device_transmit(spi_device_handle_t handle,
                               spi_transaction_t *trans_desc)
```

#### Polling Transactions

```c
esp_err_t spi_device_polling_start(spi_device_handle_t handle,
                                    spi_transaction_t *trans_desc,
                                    TickType_t ticks_to_wait)
esp_err_t spi_device_polling_end(spi_device_handle_t handle,
                                  TickType_t ticks_to_wait)
esp_err_t spi_device_polling_transmit(spi_device_handle_t handle,
                                       spi_transaction_t *trans_desc)
```

### Transaction Line Modes

| Mode | CMD Lines | ADDR Lines | DATA Lines | Flags |
|-|-|-|-|-|
| Normal SPI | 1 | 1 | 1 | 0 |
| Dual Output | 1 | 1 | 2 | SPI_TRANS_MODE_DIO |
| Quad Output | 1 | 1 | 4 | SPI_TRANS_MODE_QIO |
| Quad I/O | 1 | 4 | 4 | SPI_TRANS_MODE_QIO + SPI_TRANS_MULTILINE_ADDR |
| Octal Output | 1 | 1 | 8 | SPI_TRANS_MODE_OCT |
| OPI | 8 | 8 | 8 | SPI_TRANS_MODE_OCT + SPI_TRANS_MULTILINE_CMD + SPI_TRANS_MULTILINE_ADDR |

### Clock Configuration

**Common Frequency Constants:**
- SPI_MASTER_FREQ_8M: 8 MHz
- SPI_MASTER_FREQ_10M: 10 MHz
- SPI_MASTER_FREQ_20M: 20 MHz
- SPI_MASTER_FREQ_40M: 40 MHz
- SPI_MASTER_FREQ_80M: 80 MHz

#### GPIO Matrix vs IOMUX

"When an SPI Host is set to 40 MHz or lower frequencies, routing SPI pins via the GPIO matrix will behave the same compared to routing them via IOMUX." At higher frequencies, IOMUX pins provide ~25ns lower input delay.

#### SPI2 Native Pins

| Signal | GPIO |
|-|-|
| CS0 | 10 |
| SCLK | 12 |
| MISO | 13 |
| MOSI | 11 |
| QUADWP | 14 |
| QUADHD | 9 |

### Transfer Speed Specifications

#### Transaction Overhead (Typical at 8 MHz)

| Transaction Type | Interval (us) | 1-byte Duration | 8-byte Duration | Max Speed (KBps) |
|-|-|-|-|-|
| Interrupt via DMA | ~26 | 26 | 33 | 242 |
| Interrupt via CPU | ~24 | 24 | 32 | 250 |
| Polling via DMA | ~11 | 11 | 18 | 444 |
| Polling via CPU | ~9 | 9 | 16 | 500 |

Performance formula: Overall cost = 20 + 8n/Fspi[MHz] microseconds for n bytes.

### DMA Configuration

When DMA enabled, buffers must be:
1. Allocated in DMA-capable internal memory (MALLOC_CAP_DMA)
2. 32-bit aligned (starting at 32-bit boundary)
3. Length in multiples of 4 bytes

**PSRAM Direct Transfer:** Flag SPI_TRANS_DMA_USE_PSRAM enables direct PSRAM transfers. Limitation: "GPSPI transfer bandwidth should be less than PSRAM bandwidth, otherwise transmission data may be lost."

### Thread Safety

"The SPI Master driver allows multiple Devices to be connected on a same SPI bus... As long as each Device is accessed by only one task, the driver is thread-safe. However, if multiple tasks try to access the same SPI Device, the driver is not thread-safe."

### Data Byte Ordering

"ESP32-S3 is a little-endian chip, which means that the least significant byte of uint16_t and uint32_t variables is stored at the smallest address." SPI transmits MSB-first by default.

Endian conversion macros:
```c
SPI_SWAP_DATA_TX(DATA, LEN)  // Transform for transmission
SPI_SWAP_DATA_RX(DATA, LEN)  // Transform received data
```

### Known Restrictions

- SPI0/1 not supported for general-purpose use
- Half-duplex transactions with simultaneous read and write phases not supported
- CS0 native pin (GPIO10) only for first device; additional devices require GPIO matrix
- Interrupt transactions add overhead vs polling; optimize with bus acquisition for burst operations
