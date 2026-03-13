# SQLite Performance Tuning and Optimization

## WAL Mode Performance

Write-Ahead Logging (WAL) is the single most impactful performance optimization for most SQLite workloads. In WAL mode, readers do not block writers and the writer does not block readers, enabling much higher concurrency than the default rollback journal mode.

### Enabling WAL Mode

```sql
PRAGMA journal_mode = WAL;
```

This command returns the new journal mode (which will be "wal" on success). WAL mode is persistent — it remains in effect until explicitly changed back with `PRAGMA journal_mode = DELETE`.

### WAL Performance Characteristics

- **Read performance**: Reads in WAL mode are slightly slower than in rollback journal mode because the reader must check both the WAL file and the database file. However, the difference is typically less than 1-2%.
- **Write performance**: Writes in WAL mode are significantly faster because they only require appending to the end of the WAL file rather than writing to two separate files (database + journal).
- **Concurrency**: The key advantage of WAL mode is that readers and the writer can operate concurrently. In rollback journal mode, a writer must wait for all readers to finish, and readers must wait for the writer to finish.

### WAL Checkpointing

The WAL file grows as writes accumulate. Periodically, the WAL file must be checkpointed — its contents transferred back to the main database file. There are four checkpoint modes:

```sql
PRAGMA wal_checkpoint(PASSIVE);    -- Checkpoint as much as possible without waiting
PRAGMA wal_checkpoint(FULL);       -- Wait for readers, then checkpoint everything
PRAGMA wal_checkpoint(RESTART);    -- Like FULL, then reset WAL to beginning
PRAGMA wal_checkpoint(TRUNCATE);   -- Like RESTART, then truncate WAL to zero size
```

By default, SQLite automatically runs a PASSIVE checkpoint when the WAL file reaches 1000 pages. This threshold is controlled by:

```sql
PRAGMA wal_autocheckpoint = 1000;  -- Default: 1000 pages
```

Or at compile time:

```c
-DSQLITE_DEFAULT_WAL_AUTOCHECKPOINT=1000
```

For high-write workloads, increasing the autocheckpoint threshold can improve throughput at the cost of larger WAL files and slower recovery times.

## Synchronous Mode

The `synchronous` pragma has a dramatic impact on write performance:

```sql
PRAGMA synchronous = OFF;     -- Fastest, but data may be lost on power failure
PRAGMA synchronous = NORMAL;  -- Good compromise for WAL mode
PRAGMA synchronous = FULL;    -- Default for DELETE mode. Safe against power loss.
PRAGMA synchronous = EXTRA;   -- Maximum safety
```

With WAL mode, `PRAGMA synchronous = NORMAL` provides adequate protection against data loss while being significantly faster than FULL. The combination of `journal_mode=WAL` with `synchronous=NORMAL` is a widely recommended configuration for good performance with reasonable durability.

Benchmarks show that WAL mode with synchronous=NORMAL can be 5-10x faster for write-heavy workloads compared to the default DELETE mode with synchronous=FULL, depending on the hardware and workload pattern.

## Page Cache Configuration

The page cache stores recently used database pages in memory. A larger cache reduces disk I/O:

```sql
-- Set cache size in pages (positive number) or KB (negative number)
PRAGMA cache_size = 10000;    -- 10,000 pages
PRAGMA cache_size = -20000;   -- 20,000 KB = ~20 MB

-- Query current cache size
PRAGMA cache_size;
```

The default cache size is -2000 (approximately 2 MB). For read-heavy workloads with databases larger than the cache, increasing the cache size can dramatically reduce disk I/O and improve query performance.

The page cache can also be configured at compile time:

```c
-DSQLITE_DEFAULT_CACHE_SIZE=-2000  /* Default: ~2MB */
```

### Cache Spill Behavior

When the cache is full and a new page needs to be loaded, SQLite must evict (spill) a page. The cache spill threshold controls how aggressively dirty pages are written back:

```sql
PRAGMA cache_spill = 100;     -- Spill when cache is 100% full (default)
PRAGMA cache_spill = OFF;     -- Never spill (hold everything until commit)
```

Disabling cache spill can speed up large transactions but uses more memory.

## Memory-Mapped I/O

SQLite can use memory-mapped I/O for reading the database file, which can be faster than traditional read() system calls because it avoids copying data from the kernel buffer to user space:

```sql
PRAGMA mmap_size = 268435456;   -- Memory-map up to 256 MB of the database
PRAGMA mmap_size = 0;           -- Disable memory-mapped I/O (default)
```

Memory-mapped I/O is disabled by default (mmap_size = 0). When enabled, SQLite memory-maps up to `mmap_size` bytes of the database file. Pages within the memory-mapped region are accessed directly through pointer dereference rather than read() system calls.

Benefits:
- Eliminates double-buffering (kernel page cache + SQLite page cache)
- Can reduce system call overhead for read-heavy workloads
- Works well on 64-bit systems with large address spaces

Limitations:
- Only applies to reads; writes still use traditional I/O
- On 32-bit systems, the address space limits the practical mmap size
- Memory-mapped I/O can cause SIGBUS signals if the database file is truncated by another process
- Not available on all platforms

The compile-time default can be set with:

```c
-DSQLITE_DEFAULT_MMAP_SIZE=0           /* Default: disabled */
-DSQLITE_MAX_MMAP_SIZE=2147483648      /* Maximum allowed: 2 GB */
```

## Query Planning and Optimization

SQLite uses a sophisticated query planner to choose efficient execution strategies. Understanding the query planner is essential for writing performant SQL.

### EXPLAIN QUERY PLAN

The `EXPLAIN QUERY PLAN` prefix shows how SQLite intends to execute a query:

```sql
EXPLAIN QUERY PLAN SELECT * FROM orders WHERE customer_id = 42;
-- Example output:
-- QUERY PLAN
-- `--SEARCH orders USING INDEX idx_customer (customer_id=?)
```

Key output indicators:
- **SCAN** — A full table scan. Generally slow for large tables.
- **SEARCH** — An indexed lookup. Much faster than SCAN.
- **USING INDEX** — The specific index being used.
- **USING COVERING INDEX** — The index contains all needed columns; the table need not be accessed at all.
- **USE TEMP B-TREE** — A temporary B-tree is created for sorting or grouping.

### The Query Planner Algorithm

SQLite uses a "next generation query planner" (NGQP) introduced in version 3.8.0 (2013-08-26). The NGQP evaluates all possible query plans using a cost-based model and selects the one with the lowest estimated cost. For queries with many tables, SQLite limits the search space to avoid exponential planning time.

The query planner considers:
1. Which indexes are available
2. The estimated number of rows produced by each scan or search
3. Whether the index can satisfy ORDER BY without a separate sort
4. Whether a covering index can be used to avoid accessing the table

### ANALYZE Command

The `ANALYZE` command gathers statistics about the distribution of values in table indexes. These statistics are stored in the `sqlite_stat1`, `sqlite_stat3`, and `sqlite_stat4` tables and are used by the query planner to make better decisions.

```sql
ANALYZE;                -- Analyze all tables and indexes
ANALYZE tablename;      -- Analyze a specific table
ANALYZE schemaname;     -- Analyze all tables in a schema
```

Running `ANALYZE` after loading data or after significant data changes can dramatically improve query performance by giving the planner accurate row count estimates. Without `ANALYZE` data, the planner uses heuristic estimates which may be significantly wrong.

The `sqlite_stat1` table stores the approximate number of rows in each index and the average number of rows with the same value for each prefix of the index columns. For example, an index on (a, b, c) would have statistics for the total rows, rows per distinct (a), rows per distinct (a,b), and rows per distinct (a,b,c).

## Indexing Strategies

### Basic Index Usage

Indexes dramatically speed up queries that filter on indexed columns:

```sql
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_name_date ON orders(customer_name, order_date);
```

### Covering Indexes

A covering index includes all columns needed by a query, eliminating the need to look up the table row:

```sql
-- Query that needs only name and email
SELECT name, email FROM users WHERE email LIKE 'a%';

-- Covering index for this query
CREATE INDEX idx_email_covering ON users(email, name);
```

With a covering index, SQLite shows "USING COVERING INDEX" in the query plan. This is faster because it avoids the extra seek to the table's B-tree to fetch the full row data.

### Partial Indexes (since 3.8.0)

Partial indexes only index rows that satisfy a WHERE clause:

```sql
-- Only index active users
CREATE INDEX idx_active_users ON users(email) WHERE active = 1;

-- Only index non-null values
CREATE INDEX idx_nonnull ON t1(x) WHERE x IS NOT NULL;
```

Partial indexes are smaller than full indexes and faster to maintain. They are used by the query planner when the query's WHERE clause implies the index's WHERE clause.

### Expression Indexes (since 3.9.0)

Indexes can be created on expressions:

```sql
CREATE INDEX idx_lower_email ON users(lower(email));
CREATE INDEX idx_year ON orders(strftime('%Y', order_date));
```

### Multi-Column Index Ordering

For multi-column indexes, the order of columns matters. The index is usable for queries that filter on a prefix of the index columns:

```sql
CREATE INDEX idx_a_b_c ON t1(a, b, c);

-- Uses the index:
SELECT * FROM t1 WHERE a = 1;
SELECT * FROM t1 WHERE a = 1 AND b = 2;
SELECT * FROM t1 WHERE a = 1 AND b = 2 AND c = 3;

-- Does NOT use the index efficiently:
SELECT * FROM t1 WHERE b = 2;        -- Not a prefix
SELECT * FROM t1 WHERE c = 3;        -- Not a prefix
SELECT * FROM t1 WHERE a = 1 AND c = 3;  -- Gap in prefix (b is skipped)
```

The "left-most prefix" rule is fundamental: an index on (a, b, c) can be used for queries on (a), (a, b), or (a, b, c), but not for (b) or (c) alone.

## Shared Cache Mode

Shared cache mode allows multiple database connections within the same process to share a single page cache:

```sql
-- Enable at connection time
sqlite3_open_v2("test.db", &db, SQLITE_OPEN_READWRITE | SQLITE_OPEN_SHAREDCACHE, NULL);
```

Or globally:

```c
sqlite3_enable_shared_cache(1);  /* Enable for all subsequent connections */
```

In shared cache mode, table-level locking is used instead of database-level locking, providing finer-grained concurrency. However, shared cache mode is discouraged for new applications — WAL mode provides better concurrency without the complexity.

**Important**: `sqlite3_enable_shared_cache()` is deprecated as of SQLite version 3.41.0 (2023-02-21). The SQLite developers recommend using separate connections with WAL mode instead.

## Transaction Optimization

### Batch Inserts

Individual INSERT statements each run in their own transaction by default. Wrapping multiple inserts in a single transaction is dramatically faster:

```sql
-- Slow: each INSERT is a separate transaction
INSERT INTO t1 VALUES(1, 'a');
INSERT INTO t1 VALUES(2, 'b');
INSERT INTO t1 VALUES(3, 'c');

-- Fast: all inserts in one transaction
BEGIN;
INSERT INTO t1 VALUES(1, 'a');
INSERT INTO t1 VALUES(2, 'b');
INSERT INTO t1 VALUES(3, 'c');
COMMIT;
```

Batch inserting 100,000 rows in a single transaction can be 50-100x faster than inserting them individually, because each transaction requires at least one fsync() call to disk.

### Prepared Statement Reuse

Reusing prepared statements with parameter binding is significantly faster than preparing a new statement each time:

```c
sqlite3_stmt *stmt;
sqlite3_prepare_v2(db, "INSERT INTO t1 VALUES(?1, ?2)", -1, &stmt, NULL);

for (int i = 0; i < 100000; i++) {
    sqlite3_bind_int(stmt, 1, i);
    sqlite3_bind_text(stmt, 2, names[i], -1, SQLITE_STATIC);
    sqlite3_step(stmt);
    sqlite3_reset(stmt);
}

sqlite3_finalize(stmt);
```

The `sqlite3_prepare_v2()` call involves parsing and compiling SQL, which is expensive. Reusing the prepared statement avoids this overhead.

## Temporary Storage

SQLite uses temporary files for intermediate results during sorting, GROUP BY, DISTINCT, and complex queries. The location and type of temporary storage affects performance:

```sql
PRAGMA temp_store = DEFAULT;  -- Use compile-time default (usually FILE)
PRAGMA temp_store = FILE;     -- Use temporary files on disk
PRAGMA temp_store = MEMORY;   -- Use in-memory temporary storage
```

Using `temp_store = MEMORY` avoids disk I/O for temporary results but uses more RAM. For workloads with many sorting or grouping operations, this can be a significant speedup.

The location of temporary files is controlled by the `SQLITE_TMPDIR` environment variable, or the `-DSQLITE_TEMP_STORE` compile-time option (0=always file, 1=file by default, 2=memory by default, 3=always memory).

## Busy Handling

When a database is locked by another connection, SQLite returns SQLITE_BUSY. The busy handler controls what happens:

```sql
-- Wait up to 5 seconds for the lock to clear
PRAGMA busy_timeout = 5000;
```

Or programmatically:

```c
sqlite3_busy_timeout(db, 5000);  /* Wait up to 5000 milliseconds */

/* Or register a custom busy handler */
sqlite3_busy_handler(db, my_busy_callback, user_data);
```

Without a busy handler, any lock contention immediately returns SQLITE_BUSY to the caller. Setting an appropriate busy timeout is essential for applications with concurrent access.

## LSAP: Largest Sequence of Ascending Prefixes

SQLite's query planner uses the "LSAP" algorithm for optimizing ORDER BY clauses when an index is available. If the ORDER BY columns correspond to a prefix of an index, SQLite can avoid a separate sort step by reading the index in order.

## Performance Monitoring

### sqlite3_stmt_status()

The `sqlite3_stmt_status()` function returns performance counters for a prepared statement:

```c
int sqlite3_stmt_status(sqlite3_stmt*, int op, int resetFlg);
```

Key counters:
- `SQLITE_STMTSTATUS_FULLSCAN_STEP` — Number of full-table-scan steps
- `SQLITE_STMTSTATUS_SORT` — Number of sort operations
- `SQLITE_STMTSTATUS_AUTOINDEX` — Number of automatic indexes created
- `SQLITE_STMTSTATUS_VM_STEP` — Number of VDBE virtual machine steps
- `SQLITE_STMTSTATUS_REPREPARE` — Number of times the statement was automatically re-prepared
- `SQLITE_STMTSTATUS_RUN` — Number of times the statement was executed
- `SQLITE_STMTSTATUS_FILTER_MISS` — Number of Bloom filter misses (since 3.38.0)
- `SQLITE_STMTSTATUS_FILTER_HIT` — Number of Bloom filter hits (since 3.38.0)

### sqlite3_db_status()

The `sqlite3_db_status()` function returns information about a database connection:

```c
int sqlite3_db_status(sqlite3*, int op, int *pCur, int *pHiwtr, int resetFlg);
```

Key status parameters:
- `SQLITE_DBSTATUS_LOOKASIDE_USED` — Lookaside memory in use
- `SQLITE_DBSTATUS_CACHE_USED` — Approximate page cache memory used
- `SQLITE_DBSTATUS_SCHEMA_USED` — Memory used by schema
- `SQLITE_DBSTATUS_STMT_USED` — Memory used by prepared statements
- `SQLITE_DBSTATUS_CACHE_HIT` — Page cache hits
- `SQLITE_DBSTATUS_CACHE_MISS` — Page cache misses
- `SQLITE_DBSTATUS_CACHE_WRITE` — Pages written to cache

## The `.timer` and `.eqp` CLI Commands

The SQLite command-line shell includes built-in performance tools:

```
.timer on        -- Show wall-clock time for each statement
.eqp on          -- Show EXPLAIN QUERY PLAN before each statement
.eqp full        -- Show full EXPLAIN and EXPLAIN QUERY PLAN
.scanstats on    -- Show I/O statistics (if compiled with SQLITE_ENABLE_STMT_SCANSTATUS)
```

These tools are invaluable for identifying slow queries during development.

## Bloom Filters (since 3.38.0)

SQLite 3.38.0 introduced Bloom filter optimization for joins. When processing a join, SQLite may build a Bloom filter on the inner table and use it to quickly reject rows from the outer table that have no match. This can significantly speed up queries that join large tables with high selectivity.

The Bloom filter optimization is automatic and requires no user intervention. Its effectiveness can be monitored using the `SQLITE_STMTSTATUS_FILTER_HIT` and `SQLITE_STMTSTATUS_FILTER_MISS` counters.

## Deferred Foreign Key Checks

Foreign key checking can impact insert performance. Deferring checks to the end of the transaction is faster:

```sql
PRAGMA foreign_keys = ON;

BEGIN;
-- Create a deferred foreign key constraint
CREATE TABLE child(
    id INTEGER PRIMARY KEY,
    parent_id INTEGER REFERENCES parent(id) DEFERRABLE INITIALLY DEFERRED
);
-- Inserts are faster because FK checks happen at COMMIT, not per-row
COMMIT;
```

## Performance Summary Table

| Optimization | Typical Speedup | Tradeoff |
|-|-|-|
| WAL mode | 2-10x writes | Slightly slower reads, requires shared memory |
| synchronous=NORMAL (WAL) | 2-5x writes | Slight corruption risk on power loss |
| Batch transactions | 50-100x inserts | Must handle transaction failures |
| Prepared statement reuse | 2-5x | Code complexity |
| Covering indexes | 2-10x reads | Extra storage, slower writes |
| mmap_size > 0 | 1.2-2x reads | Platform-dependent, SIGBUS risk |
| cache_size increase | 1-5x reads | More memory usage |
| temp_store=MEMORY | 1-3x sorting | More memory usage |
| ANALYZE | Variable | Must re-run after data changes |
