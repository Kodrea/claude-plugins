# Nexus Stream Processor — API Reference

## Configuration

### Environment Variables

| Variable | Default | Description |
|-|-|-|
| NSP_CONTROLLER_HOST | localhost | Controller address |
| NSP_CONTROLLER_PORT | 9090 | Controller API port |
| NSP_WORKER_PORT | 9100 | Worker base port |
| NSP_STATE_BACKEND | rocksdb | State backend: rocksdb, redis, postgresql |
| NSP_CHECKPOINT_INTERVAL_MS | 30000 | Checkpoint interval |
| NSP_MAX_BATCH_SIZE | 1024 | Max events per batch |
| NSP_MAX_BATCH_WAIT_MS | 50 | Max batch wait time |
| NSP_PARTITION_COUNT | 16 | Default partition count |
| NSP_LOG_LEVEL | INFO | Logging level |
| NSP_METRICS_ENABLED | true | Enable Prometheus metrics |

### DAG Configuration File

DAGs are defined in YAML:

```yaml
name: my-pipeline
version: "1.0"
sources:
  - type: kafka
    config:
      brokers: ["kafka-1:9092", "kafka-2:9092"]
      topic: input-events
      group_id: nsp-my-pipeline
      auto_offset_reset: earliest

stages:
  - name: parse
    processors:
      - class: com.example.JsonParser
        parallelism: 4
    partition_strategy: round_robin

  - name: enrich
    processors:
      - class: com.example.GeoEnricher
        parallelism: 8
        config:
          geoip_db: /data/GeoLite2-City.mmdb
    partition_strategy: hash
    partition_key: "$.user_id"

  - name: aggregate
    processors:
      - class: com.example.WindowAggregator
        parallelism: 4
        config:
          window_size_ms: 60000
          window_slide_ms: 10000
    state_backend: rocksdb
    partition_strategy: hash
    partition_key: "$.user_id"

sinks:
  - type: kafka
    config:
      brokers: ["kafka-1:9092"]
      topic: output-aggregates
  - type: prometheus
    config:
      port: 9200
```

### Processor Configuration

Each processor class must be annotated with `@processor` and registered in the processor registry:

```python
from nexus import processor, Event, Context

@processor(
    name="json-parser",
    version="1.2.0",
    input_schema="raw_event.avro",
    output_schema="parsed_event.avro"
)
class JsonParser:
    def setup(self, config: dict):
        """Called once when the processor starts."""
        self.strict_mode = config.get("strict", False)

    def process(self, event: Event, ctx: Context) -> list[Event]:
        try:
            parsed = json.loads(event.value)
            return [Event(key=event.key, value=parsed)]
        except json.JSONDecodeError as e:
            if self.strict_mode:
                return ctx.dead_letter(event, str(e))
            return []  # silently drop

    def teardown(self):
        """Called when the processor is stopped."""
        pass
```

## REST API

### Topology

```
GET /api/v1/topology

Response:
{
  "controller": {"host": "ctrl-1", "port": 9090, "uptime_s": 86400},
  "workers": [
    {"id": "w-001", "host": "worker-1", "port": 9100, "partitions": [0,1,2,3], "cpu_pct": 45.2, "mem_mb": 4096},
    {"id": "w-002", "host": "worker-2", "port": 9101, "partitions": [4,5,6,7], "cpu_pct": 38.7, "mem_mb": 3840}
  ],
  "dags": [
    {"id": "dag-001", "name": "my-pipeline", "status": "RUNNING", "stages": 3, "uptime_s": 3600}
  ]
}
```

### Deploy DAG

```
POST /api/v1/deploy
Content-Type: application/yaml

(DAG YAML body)

Response:
{"dag_id": "dag-002", "status": "DEPLOYING", "estimated_ready_s": 15}
```

### Metrics

```
GET /api/v1/metrics

Response (Prometheus text format):
nsp_events_processed_total{dag="my-pipeline",stage="parse"} 1547823
nsp_events_processed_total{dag="my-pipeline",stage="enrich"} 1547820
nsp_events_processed_total{dag="my-pipeline",stage="aggregate"} 1547818
nsp_processing_latency_ms{dag="my-pipeline",stage="parse",quantile="0.99"} 2.3
nsp_processing_latency_ms{dag="my-pipeline",stage="enrich",quantile="0.99"} 8.7
nsp_processing_latency_ms{dag="my-pipeline",stage="aggregate",quantile="0.99"} 11.2
nsp_checkpoint_duration_ms{dag="my-pipeline"} 1250
nsp_state_size_bytes{dag="my-pipeline",backend="rocksdb"} 524288000
nsp_dead_letter_total{dag="my-pipeline",stage="parse"} 47
```

### Error Handling

All API errors return JSON:

```json
{
  "error": "DAG_NOT_FOUND",
  "message": "No DAG with id 'dag-999' exists",
  "status": 404,
  "timestamp": "2025-11-15T10:30:00Z"
}
```

Error codes:
- `VALIDATION_ERROR` (400): Invalid DAG YAML or config
- `DAG_NOT_FOUND` (404): Referenced DAG doesn't exist
- `CONFLICT` (409): DAG with same name already deployed
- `INTERNAL_ERROR` (500): Unexpected server error
- `UNAVAILABLE` (503): Controller is starting up or shutting down

## Client SDK

### Python

```python
from nexus.client import NexusClient

client = NexusClient("ctrl-1:9090")

# Deploy a DAG
with open("pipeline.yaml") as f:
    result = client.deploy(f.read())
print(f"Deployed: {result.dag_id}")

# Check status
topo = client.topology()
for worker in topo.workers:
    print(f"Worker {worker.id}: {worker.cpu_pct}% CPU")

# Undeploy
client.undeploy("dag-001")
```

### CLI

```bash
# Deploy
nsp deploy pipeline.yaml

# Status
nsp status
nsp status dag-001

# Metrics (live tail)
nsp metrics --follow --interval 5s

# Logs
nsp logs dag-001 --stage parse --tail 100

# Scale a stage
nsp scale dag-001 enrich --parallelism 16
```

## Known Issues

- **Issue #1847**: Cross-partition joins not supported. Workaround: ensure joined events share partition keys.
- **Issue #2103**: Redis state backend leaks connections under high checkpoint frequency (<5s intervals). Fixed in v2.9-rc1.
- **Issue #2251**: The `nsp scale` CLI command does not validate that the new parallelism exceeds available partitions. Scaling beyond partition count silently creates idle processor instances.
- **Issue #1923**: Prometheus metrics endpoint returns stale data for up to 15 seconds after a DAG redeployment due to metrics registry caching.
