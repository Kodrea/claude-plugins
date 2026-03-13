# ESP32-S3 AI Capabilities — ESP-DL Neural Network Framework

Source: https://github.com/espressif/esp-dl

## Overview

ESP-DL is a lightweight and efficient neural network inference framework designed specifically for ESP series chips. It enables developers to easily and quickly develop AI applications using Espressif's System on Chips (SoCs).

## Core Features

### Model Format
ESP-DL uses a proprietary ".espdl" format that uses FlatBuffers instead of Protobuf, making it more lightweight and supporting zero-copy deserialization.

### Operator Implementation
The framework efficiently implements common operators including Conv, Gemm, Add, and Mul. A complete operator support list is maintained in the repository documentation.

### Memory Management
Features a Static Memory Planner that automatically allocates different layers to the optimal memory location based on the user-specified internal RAM size.

### Multi-core Processing
Automatic dual-core scheduling allows computationally intensive operators to fully utilize the dual-core computing power. Currently, Conv2D and DepthwiseConv2D support dual-core scheduling.

### Activation Functions
All activation functions except for ReLU and PReLU are implemented using an 8-bit LUT (Look Up Table) method in ESP-DL to accelerate inference.

## Quantization & Deployment

### ESP-PPQ Tool
Serves as the quantization solution, capable of quantizing models from ONNX, PyTorch, and TensorFlow formats before exporting to ESP-DL standard format.

Installation: `pip install esp-ppq`

Recent updates (February 2026) added support for TrainedQuantizedThresholdPass quantization methods.

### Supported Quantization Types
- INT8 quantization for weights and activations
- INT16 quantization for sensitive layers
- Mixed-precision quantization (INT8/INT16)
- Per-channel and per-tensor quantization schemes

## ESP32-S3 Hardware Acceleration

### Vector Instructions
The ESP32-S3 Xtensa LX7 cores include vector instruction extensions specifically designed for neural network computing and signal processing:

- 128-bit SIMD vector operations
- Hardware support for 8-bit and 16-bit integer MAC (Multiply-Accumulate) operations
- Parallel processing of multiple data elements per clock cycle
- Optimized dot product operations for convolution and matrix multiplication

### ESP-NN Library
Low-level optimized neural network kernels that leverage the ESP32-S3 vector instructions:
- Optimized convolution (1D, 2D, depthwise)
- Optimized fully-connected layers
- Pooling operations (max pool, average pool)
- Element-wise operations
- Softmax and other activation implementations

### ESP-DSP Library
Digital Signal Processing library with optimized functions:
- FFT (Fast Fourier Transform) — radix-2, up to 4096 points
- FIR and IIR filters
- Matrix operations (multiply, transpose, inverse)
- Vector operations (add, multiply, dot product)
- Window functions (Hann, Hamming, Blackman)
- Signal processing for audio preprocessing before neural inference

## Supported Pre-built Models

The repository includes pre-built models and examples for:

### Computer Vision (ESP-WHO)
- **Face Detection**: MTCNN and custom lightweight face detector
- **Face Recognition**: MobileFaceNet-based face identification
- **Pedestrian Detection**: Person detection for surveillance and counting
- **Object Detection**: YOLO11n — real-time object detection
- **Image Classification**: MobileNetV2 — general image classification
- **Pose Estimation**: Human body pose keypoint detection
- **Gesture Recognition**: Hand gesture classification

### Audio/Speech (ESP-Skainet)
- **Wake Word Detection**: Custom wake word engine (e.g., "Hi ESP")
- **Speech Command Recognition**: Offline voice command recognition
- **Speaker Verification**: Voice identity verification
- **Acoustic Echo Cancellation**: For voice assistant applications

## Performance Characteristics

### Inference Performance on ESP32-S3 (240 MHz, dual-core)
- Face detection (320x240 input): ~30-50 ms per frame
- Image classification (96x96 input, MobileNetV2-0.35): ~15-25 ms per frame
- Wake word detection: <10 ms per audio frame
- Person detection (96x96 input): ~20-40 ms per frame

### Memory Usage
- Minimum viable model deployment: ~100 KB internal SRAM + external PSRAM
- Typical face detection + recognition: ~200 KB internal SRAM + 2-4 MB PSRAM
- Static Memory Planner reduces peak memory by reusing buffers across layers

## Model Deployment Workflow

1. **Train** model in standard framework (TensorFlow, PyTorch, or ONNX)
2. **Export** to ONNX format (if not already ONNX)
3. **Quantize** using ESP-PPQ tool:
   ```bash
   pip install esp-ppq
   python quantize_model.py --input model.onnx --output model.espdl --target esp32s3
   ```
4. **Deploy** using ESP-DL API in ESP-IDF project
5. **Optimize** memory allocation with Static Memory Planner configuration

## ESP-IDF Integration

### Requirements
- ESP-IDF release/v5.3 or above
- ESP32-S3 target chip
- Sufficient PSRAM for model weights (recommended: 8 MB PSRAM module)

### Project Setup
Add ESP-DL as a component dependency in `idf_component.yml`:
```yaml
dependencies:
  esp-dl:
    version: "*"
    git: https://github.com/espressif/esp-dl.git
```

## Comparison with Other Approaches

### ESP-DL vs TensorFlow Lite Micro
- ESP-DL: Purpose-built for ESP32-S3 vector instructions, smaller binary size, better memory efficiency
- TF Lite Micro: Broader ecosystem, portable across MCU platforms, larger binary overhead
- ESP-DL achieves 2-5x faster inference on ESP32-S3 compared to unoptimized TF Lite Micro

### Why ESP32-S3 for Edge AI
- Dual-core 240 MHz with vector extensions provides sufficient compute for many real-time AI tasks
- Low power consumption enables battery-powered AI devices
- Integrated Wi-Fi and BLE for cloud connectivity and OTA model updates
- Cost-effective compared to dedicated AI accelerator chips
- Rich peripheral set for sensor integration (camera, microphone, touch)
