# Nexus Stream Processor — Deployment & Operations Guide

## Installation

### Requirements

- Python 3.11+ (3.12 recommended)
- Java 17+ (for Kafka connector)
- 16GB RAM minimum per worker node
- Linux x86_64 (ARM64 support is experimental, see Issue #2089)

### Install via pip

```bash
pip install nexus-stream-processor==2.8.3
```

### Docker

```bash
# Controller
docker run -d --name nsp-controller \
  -p 9090:9090 -p 9091:9091 \
  nexus/controller:2.8.3

# Worker
docker run -d --name nsp-worker-1 \
  -e NSP_CONTROLLER_HOST=ctrl-1 \
  -p 9100:9100 \
  nexus/worker:2.8.3
```

### Kubernetes (Helm)

```bash
helm repo add nexus https://charts.nexus-stream.io
helm install nsp nexus/nexus-stream-processor \
  --set controller.replicas=1 \
  --set worker.replicas=8 \
  --set worker.resources.memory=16Gi \
  --set stateBackend=rocksdb
```

## Production Configuration

### Tuning for Throughput

For maximum throughput (>1M events/sec), adjust these settings:

```yaml
# worker-config.yaml
batch:
  max_size: 4096          # up from default 1024
  max_wait_ms: 100        # up from default 50
partition_count: 64        # up from default 16
processing:
  thread_pool_size: 16     # match CPU cores
  async_io: true
```

**Note:** Increasing `MAX_BATCH_SIZE` above 4096 shows diminishing returns and increases memory pressure. Internal benchmarks showed:

| Batch Size | Throughput (events/s) | p99 Latency |
|-|-|-|
| 512 | 800,000 | 6ms |
| 1024 | 1,200,000 | 8ms |
| 2048 | 1,800,000 | 11ms |
| 4096 | 2,200,000 | 15ms |
| 8192 | 2,350,000 | 28ms |

### Tuning for Latency

For low-latency processing (<5ms p99):

```yaml
batch:
  max_size: 128
  max_wait_ms: 5
partition_count: 32
processing:
  thread_pool_size: 8
  priority_scheduling: true
```

**Trade-off:** Low-latency mode reduces maximum throughput to approximately 400,000 events/sec due to smaller batches and more frequent flushes.

### Memory Sizing

Rule of thumb for worker memory:

```
Required RAM = (state_size_per_partition * partitions_per_worker)
             + (batch_size * avg_event_size * 3)  # 3x for processing pipeline
             + 2GB  # JVM overhead for Kafka connector
             + 1GB  # OS and buffers
```

For a typical workload with 1KB events, 4 partitions per worker, and 100MB state per partition:

```
RAM = (100MB * 4) + (1024 * 1KB * 3) + 2GB + 1GB = 3.4GB + 3MB + 3GB ≈ 6.5GB
```

The recommended 16GB provides ~2.5x headroom for spikes.

## Monitoring

### Prometheus Integration

NSP exposes metrics on each worker's metrics port (default: worker_port + 100). Add to your Prometheus config:

```yaml
scrape_configs:
  - job_name: 'nexus-workers'
    static_configs:
      - targets: ['worker-1:9200', 'worker-2:9200']
    scrape_interval: 10s
```

### Key Metrics to Watch

| Metric | Alert Threshold | Meaning |
|-|-|-|
| nsp_processing_latency_ms (p99) | >50ms | Processing is backing up |
| nsp_checkpoint_duration_ms | >5000ms | State backend is slow |
| nsp_dead_letter_total (rate) | >10/min | Too many processing errors |
| nsp_state_size_bytes | >10GB per worker | State is growing unbounded |
| nsp_consumer_lag | >100000 | Pipeline can't keep up with input |

### Grafana Dashboard

Import dashboard ID `nexus-stream-18432` from the Grafana marketplace. It includes:
- Event throughput by stage
- Latency percentiles (p50, p95, p99)
- Checkpoint health
- Worker resource utilization
- Dead letter queue depth

## Disaster Recovery

### Backup Strategy

State backups are triggered via the API:

```bash
curl -X POST http://ctrl-1:9090/api/v1/backup \
  -H "Content-Type: application/json" \
  -d '{"dag_id": "dag-001", "destination": "s3://backups/nsp/"}'
```

Backups are incremental and typically complete in under 60 seconds for state sizes under 10GB.

### Restore

```bash
curl -X POST http://ctrl-1:9090/api/v1/restore \
  -H "Content-Type: application/json" \
  -d '{"dag_id": "dag-001", "source": "s3://backups/nsp/dag-001-20251115-103000.snap"}'
```

**Warning:** Restoring replaces ALL state for the DAG. Any events processed between the backup and restore will be reprocessed (at-least-once delivery during restore).

### Multi-Region

NSP does not natively support multi-region replication. For multi-region setups, use Kafka MirrorMaker 2 to replicate input topics across regions, and run independent NSP clusters in each region. State is NOT synchronized between regions.

**Contradiction note:** The marketing page claims "built-in multi-region support" but this refers only to the ability to deploy separate clusters per region, not automatic state replication. This has been flagged as misleading (Issue #2198).

## Upgrade Procedures

### Rolling Upgrade

1. Upgrade controller first: `helm upgrade nsp --set controller.image.tag=2.9.0`
2. Wait for controller health check: `curl http://ctrl-1:9090/api/v1/health`
3. Upgrade workers one at a time: partitions automatically rebalance
4. Verify: `nsp status` should show all workers on new version

**Critical:** Do NOT upgrade more than one minor version at a time. v2.7 -> v2.9 is not supported; you must go v2.7 -> v2.8 -> v2.9. The checkpoint format changed in v2.8 and again in v2.9.

### Rollback

If issues occur during upgrade:

```bash
helm rollback nsp 1  # rollback to previous revision
```

Rollback is safe as long as no checkpoints were written by the new version. If new-version checkpoints exist, you must restore from a pre-upgrade backup.
