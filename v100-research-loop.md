# Autoresearch on V100 GPUs: Feasibility Analysis

## 1. Blocking Issue: Flash Attention 3

Autoresearch hard-depends on Flash Attention 3 kernels. The code uses `kernels-community/flash-attn3` for non-Hopper GPUs (detected via `torch.cuda.get_device_capability()`), but FA3 requires SM 8.0+ (Ampere/Ada/Hopper). V100 is SM 7.0 — FA3 will not run. You would need to replace FA3 calls with `torch.nn.functional.scaled_dot_product_attention` or Flash Attention 2 (which supports SM 7.0). This is a required code modification.

## 2. Blocking Issue: BF16

The code uses `torch.bfloat16` throughout — autocast context, embedding casting, rotary embeddings. V100 does not support BF16 natively. You must convert all BF16 usage to FP16. This means changing `autocast_ctx` to FP16 and all `.bfloat16()` casts. FP16 has narrower dynamic range, so you may need loss scaling (autocast with FP16 handles this, but the Muon optimizer's compiled kernels with explicit `.bfloat16()` casts need manual conversion).

## 3. Single-GPU VRAM at Default Depth=8

Default depth=8 gives model_dim=512, ~46M params. The README states ~45GB peak VRAM on H100 at default settings. *Inference:* much of this is activation memory and optimizer states at DEVICE_BATCH_SIZE=128 with seq_len=2048. A single 32GB V100 cannot run defaults. A 16GB V100 is far too small. You would need to reduce DEVICE_BATCH_SIZE significantly (e.g., 16-32) and rely on gradient accumulation (already built in). At batch_size=16, VRAM usage drops roughly 4-8x from the activation side, potentially fitting in 32GB. *This is an inference — actual memory depends on torch.compile behavior.*

## 4. Multi-GPU: Not Supported, Modifications Needed

The code is explicitly "single-GPU, single-file." The MuonAdamW optimizer stacks all parameters of the same shape into tensors for the fused kernel — this is incompatible with DDP without refactoring. Options:

- **Simplest:** Reduce batch size to fit on one 32GB V100. Gradient accumulation handles the rest.
- **DDP:** Would require refactoring the Muon optimizer's stacking logic and adding `DistributedDataParallel` wrapping. Moderate effort.
- **FSDP/model parallel:** Overkill for a ~46M param model. Not recommended.

The 4x NVLINK board doesn't help much here — the model fits on one GPU, you just need to shrink the batch. NVLINK would matter if you did DDP, giving ~100 GB/s inter-GPU bandwidth.

## 5. Training Speed: H100 vs V100

- H100 BF16: ~990 TFLOPS. V100 FP16: ~125 TFLOPS (with tensor cores). Roughly **8x slower**.
- Memory bandwidth: H100 3.35 TB/s vs V100-32GB 900 GB/s (~3.7x slower).
- Since autoresearch uses a fixed 5-minute time budget, V100 simply processes fewer tokens/steps. The agent optimizes for *your hardware*, so results are valid but not comparable to H100 runs. Expect ~12% MFU equivalent throughput vs H100.

## 6. Cost-Effectiveness

V100 32GB at $200-400 used is excellent value for *learning and experimentation*. For autoresearch specifically: the 5-minute budget means each experiment is self-contained. You get ~12 experiments/hour regardless of GPU speed (the time budget is fixed). The research quality depends on tokens processed per experiment, which will be ~8x fewer than H100. *Inference: this may meaningfully reduce experiment signal-to-noise, making the agent's optimization less effective.*

## 7. PyTorch Compatibility

V100 (compute capability 7.0) is fully supported in current PyTorch. `torch.compile` works but may produce less optimized kernels than for newer architectures. No compatibility blockers beyond BF16/FA3.

## Summary

| Config | Feasible? | Notes |
|-|-|-|
| 1x V100 16GB | Marginal | Needs depth=4, batch=16, seq_len reduction |
| 1x V100 32GB | Yes with mods | FA3→FA2/SDPA, BF16→FP16, batch_size=16-32 |
| 4x V100 16GB NVLINK | Same as 1x 16GB | Multi-GPU not supported without DDP refactor |
| 4x V100 32GB NVLINK | Same as 1x 32GB | Multi-GPU not supported without DDP refactor |

**Required code changes:** FA3 replacement + BF16-to-FP16 conversion + reduced DEVICE_BATCH_SIZE. A single 32GB V100 is the minimum viable config. Cost-effective for experimentation, but expect ~8x lower throughput per experiment window.
