# Nexus Stream Processor — Architecture Overview

## System Purpose

Nexus Stream Processor (NSP) is a distributed real-time data pipeline framework designed for high-throughput event processing. It handles up to 2.4 million events per second on a standard 8-node cluster, with p99 latency under 12ms for single-stage transformations.

## Core Components

### Ingestion Layer

The ingestion layer accepts data from multiple source types through **Source Connectors**. Each connector implements the `SourceAdapter` interface, which requires three methods:

- `connect(config: ConnectorConfig) -> Connection`
- `poll(timeout_ms: int) -> BatchResult`
- `acknowledge(batch_id: str) -> AckStatus`

Currently supported connectors: Kafka (v3.4+), Redis Streams, Amazon Kinesis, NATS JetStream, and raw TCP sockets. The Kafka connector is the most battle-tested, handling 89% of production traffic at current deployments.

Batching is controlled by two parameters: `MAX_BATCH_SIZE` (default: 1024 events) and `MAX_BATCH_WAIT_MS` (default: 50ms). Whichever threshold is hit first triggers a batch flush.

### Processing Engine

The processing engine uses a **directed acyclic graph (DAG)** model. Each node in the DAG is a `Processor` that implements:

```python
class Processor:
    def process(self, event: Event) -> list[Event]:
        """Transform one event into zero or more output events."""
        ...

    def on_error(self, event: Event, error: Exception) -> ErrorAction:
        """Handle processing errors. Return RETRY, SKIP, or DEAD_LETTER."""
        ...
```

Processors are grouped into **stages**. Events flow through stages sequentially, but within a stage, processors run in parallel across partitions. The default partition strategy is hash-based on event key, but round-robin and custom partitioners are also supported.

**Important limitation:** Cross-partition joins are not supported in the current version (v2.8). Events that need to be joined must share the same partition key. This is the most-requested feature in the issue tracker (see GitHub issue #1847).

### State Management

NSP uses a pluggable state backend system. Three backends are available:

1. **RocksDB** (default): Local embedded storage, fastest for single-node state. Supports incremental checkpointing every 30 seconds.
2. **Redis**: Distributed state, required for multi-node stateful processing. Adds ~3ms latency per state access.
3. **PostgreSQL**: For state that needs SQL queryability. Slowest option (~8ms per access) but useful for debugging and auditing.

State is accessed through the `StateStore` interface:

```python
state = context.get_state_store("my-state")
state.put("key", value)        # upsert
state.get("key")               # returns Optional[bytes]
state.delete("key")            # tombstone
state.range("prefix-")        # range scan by prefix
```

Checkpointing uses a **two-phase commit protocol**: first, all processors flush their local state to the backend, then the checkpoint coordinator writes a completion marker. If any processor fails to flush within `CHECKPOINT_TIMEOUT_MS` (default: 10000ms), the entire checkpoint is aborted and retried.

## Fault Tolerance

### Exactly-Once Semantics

NSP provides exactly-once processing guarantees when using the Kafka connector with RocksDB state backend. This is achieved through a combination of:

1. Kafka consumer group offset tracking
2. Idempotent state writes using event sequence numbers
3. Two-phase checkpoint commits

**Warning:** Exactly-once guarantees do NOT apply when using the Redis Streams or TCP socket connectors. These provide at-least-once semantics only. This is documented in the connector compatibility matrix but is a common source of confusion for new users.

### Recovery

On failure, NSP recovers by:
1. Loading the last successful checkpoint
2. Replaying events from the source starting at the checkpoint offset
3. Skipping events whose sequence numbers are already in the state store (idempotency)

Recovery time depends on the state backend and state size. Typical recovery times:
- RocksDB: 2-5 seconds (local restore from WAL)
- Redis: 5-15 seconds (network round-trips to restore state)
- PostgreSQL: 15-45 seconds (full state reload via SQL)

## Deployment Topology

NSP runs on a controller-worker architecture:

- **Controller** (1 per cluster): Manages DAG assignment, partition balancing, and checkpoint coordination. Runs on port 9090 (API) and 9091 (internal RPC).
- **Workers** (N per cluster): Execute processors. Each worker handles a subset of partitions. Default port range: 9100-9199.

Minimum viable cluster: 1 controller + 2 workers. Recommended production: 1 controller + 8 workers with 16GB RAM each.

The controller exposes a REST API at `/api/v1/` for management operations:
- `GET /api/v1/topology` — current cluster state
- `POST /api/v1/deploy` — deploy or update a DAG
- `GET /api/v1/metrics` — Prometheus-format metrics
- `DELETE /api/v1/dag/{id}` — undeploy a DAG
