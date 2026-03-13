# SQLite Architecture and Storage Engine

## Overview

SQLite is a self-contained, serverless, zero-configuration, transactional SQL database engine. The entire database is stored in a single ordinary disk file. The file format is cross-platform — a database file created on one machine can be freely copied to and used on a different machine with a completely different architecture. SQLite database files are stable, cross-platform, and backwards compatible. The developers pledge to keep the file format compatible through at least the year 2050.

The SQLite library is approximately 155,000 lines of ANSI-C source code (the "amalgamation" build). It has no external dependencies beyond a few standard C library routines. The entire library compiles into a single object file of roughly 750 KB, though the exact size varies by platform and compiler optimization flags.

## Database File Format

### File Header

Every SQLite database file begins with a 100-byte header. The header contains critical metadata about the database:

| Offset | Size | Description |
|-|-|
| 0 | 16 | Header string: "SQLite format 3\000" |
| 16 | 2 | Page size in bytes (power of 2 between 512 and 65536) |
| 18 | 1 | File format write version (1 for legacy, 2 for WAL) |
| 19 | 1 | File format read version (1 for legacy, 2 for WAL) |
| 20 | 1 | Reserved space at end of each page (usually 0) |
| 21 | 1 | Max embedded payload fraction (must be 64) |
| 22 | 1 | Min embedded payload fraction (must be 32) |
| 23 | 1 | Leaf payload fraction (must be 32) |
| 24 | 4 | File change counter |
| 28 | 4 | Size of the database file in pages |
| 32 | 4 | Page number of first freelist trunk page |
| 36 | 4 | Total number of freelist pages |
| 40 | 4 | Schema cookie |
| 44 | 4 | Schema format number (1, 2, 3, or 4) |
| 48 | 4 | Default page cache size |
| 52 | 4 | Page number of largest root b-tree page (auto-vacuum/incremental-vacuum modes) |
| 56 | 4 | Database text encoding (1=UTF-8, 2=UTF-16le, 3=UTF-16be) |
| 60 | 4 | User version (set by PRAGMA user_version) |
| 64 | 4 | Incremental vacuum mode flag (non-zero = incremental) |
| 68 | 4 | Application ID (set by PRAGMA application_id) |
| 72 | 20 | Reserved for expansion (must be zero) |
| 92 | 4 | Version-valid-for number |
| 96 | 4 | SQLite version number |

The header string at offset 0 is always the 16-byte UTF-8 string "SQLite format 3\000" (including the null terminator). This string can be used to identify the file as an SQLite database.

The default page size is 4096 bytes, which has been the default since SQLite version 3.12.0 (2016-03-29). Prior to that, the default was 1024 bytes. The page size can be any power of two between 512 and 65536 inclusive. The special value 1 in the two-byte page size field at offset 16 is interpreted as a page size of 65536.

### Text Encoding

SQLite supports three text encodings for the database file: UTF-8, UTF-16le (little-endian), and UTF-16be (big-endian). The text encoding is set when the database is first created and cannot be changed afterward (except by creating a new database with the desired encoding using VACUUM INTO). UTF-8 is the most commonly used encoding and is the default. The encoding is stored as an integer at byte offset 56 of the header: 1 for UTF-8, 2 for UTF-16le, 3 for UTF-16be.

## B-Tree Structure

SQLite uses B-trees for organizing data within the database file. There are two types of B-trees used in SQLite:

1. **Table B-trees** — used for SQL tables. Each table in the database is represented by a table B-tree. Table B-trees use a 64-bit signed integer as the key (the rowid). The data is stored in the leaf pages.

2. **Index B-trees** — used for SQL indexes. Each index is represented by an index B-tree. Index B-trees store the indexed columns plus the rowid as the key. Index B-trees have no data — all information is in the key.

Both table B-trees and index B-trees are stored as separate B-tree structures within the same database file. The root page number of each B-tree is stored in the sqlite_master table (or sqlite_schema table, the alias introduced in version 3.33.0).

### Page Types

SQLite database files are divided into fixed-size pages. Every page in the database file is one of the following types:

- **B-tree interior page** — contains keys and child page pointers. Does not contain data payloads directly.
- **B-tree leaf page** — contains keys and data payloads.
- **Overflow page** — contains data that overflows from a B-tree page when a single record is too large to fit in one page.
- **Freelist page** — an unused page that has been freed by a DELETE or DROP TABLE operation.
- **Pointer map page** — used in auto-vacuum databases to track parent page relationships.
- **Lock-byte page** — page 1,073,741,824 (if it exists); used for file locking on certain platforms.

### B-Tree Page Format

Each B-tree page (both interior and leaf) has a page header at the beginning, followed by cell pointer array, unallocated space, and cell content area. The page header format is:

| Offset | Size | Description |
|-|-|
| 0 | 1 | Page type flag: 2=interior index, 5=interior table, 10=leaf index, 13=leaf table |
| 1 | 2 | Byte offset to first freeblock |
| 3 | 2 | Number of cells on this page |
| 5 | 2 | Byte offset to first byte of cell content area |
| 7 | 1 | Number of fragmented free bytes |
| 8 | 4 | Right-most child pointer (interior pages only) |

For an interior table B-tree page (type flag 5), the header is 12 bytes. For leaf pages (type flags 10 and 13), the header is 8 bytes. Page 1 of the database file is always a table B-tree leaf page that contains the schema table (sqlite_master / sqlite_schema).

### Cell Format

Cells in leaf table B-tree pages contain:
1. **Payload length** — a varint encoding the total number of bytes of payload
2. **Rowid** — a varint encoding the integer rowid for this record
3. **Payload** — the actual record data, using SQLite's record format
4. **Overflow page number** — a 4-byte big-endian integer, present only if the payload overflows

The SQLite varint encoding uses between 1 and 9 bytes. The first seven bytes of the varint each have a continuation bit in their high-order position. The eighth byte (if present) uses all 8 bits. The ninth byte (if present) also uses all 8 bits. This allows encoding of 64-bit unsigned integers.

### Overflow Pages

When a record is too large to fit entirely on a B-tree leaf page, the excess data spills onto overflow pages. The maximum payload that can be stored directly on a B-tree page is calculated as:

```
usable_size = page_size - reserved_space
max_local = usable_size - 35   (for leaf table B-tree pages)
min_local = (usable_size - 12) * 32/255 - 23
```

If the payload size exceeds `max_local`, then only `min_local` bytes are stored on the B-tree page and the rest goes to overflow pages. Each overflow page stores up to `usable_size - 4` bytes of overflow content, with the first 4 bytes being a big-endian pointer to the next overflow page (or zero for the last page in the chain).

## Journal Modes

SQLite supports two primary mechanisms for atomic commit and rollback: the rollback journal and the write-ahead log (WAL).

### Rollback Journal

The default journal mode prior to SQLite 3.7.0 was DELETE. In rollback journal mode, SQLite works as follows:

1. Before modifying any page, the original content of that page is written to a separate rollback journal file.
2. The modified pages are written directly to the database file.
3. On commit, the rollback journal file is deleted (in DELETE mode) or truncated (in TRUNCATE mode) or its header is zeroed (in PERSIST mode).
4. On rollback, the original page content is copied from the journal back to the database file.

The rollback journal file has the same name as the database file with "-journal" appended. For a database named "example.db", the journal file is "example.db-journal".

The available rollback journal modes are:

- **DELETE** — The journal file is deleted at the end of each transaction. This is the safest but slowest mode.
- **TRUNCATE** — The journal file is truncated to zero bytes. Faster than DELETE on many systems because it avoids the overhead of deleting and recreating the file.
- **PERSIST** — The journal file header is overwritten with zeros. Fastest of the journal modes because it avoids both deletion and truncation.
- **MEMORY** — The journal is stored in memory rather than on disk. This is faster but not safe against power loss or application crash.
- **OFF** — No journal is kept. Transactions are not atomic and the database can be left in a corrupt state if the application crashes.

### Write-Ahead Log (WAL)

WAL mode was introduced in SQLite version 3.7.0 (2010-07-21). In WAL mode, changes are not written directly to the database file. Instead, changes are appended to a separate WAL file (named "database.db-wal"). The original database file is not modified during a transaction.

Key characteristics of WAL mode:

- **Concurrent readers and writer**: Readers do not block the writer and the writer does not block readers. A single write transaction can proceed concurrently with multiple read transactions.
- **Checkpointing**: The WAL file must periodically be transferred back to the database file. This process is called checkpointing. By default, SQLite automatically checkpoints the WAL when it reaches 1000 pages (the SQLITE_DEFAULT_WAL_AUTOCHECKPOINT compile-time option controls this threshold).
- **WAL file structure**: The WAL file consists of a 32-byte header followed by zero or more WAL frames. Each frame contains a 24-byte frame header and a page-size worth of data.
- **Shared memory file**: WAL mode uses a shared-memory file (named "database.db-shm") to coordinate between processes. This file uses memory-mapped I/O.

WAL mode provides significantly better concurrency than rollback journal modes. However, WAL mode does not work well over a network filesystem and requires shared memory support from the operating system. WAL mode is activated using:

```sql
PRAGMA journal_mode=WAL;
```

WAL mode persists across database connections — once set, it remains in effect until explicitly changed back.

### WAL2 Mode (Experimental)

SQLite has an experimental WAL2 mode (sometimes called "wal2") that uses two WAL files instead of one. This allows one WAL file to be checkpointed while the other accepts new writes, improving write throughput for write-heavy workloads. WAL2 is not yet part of the official SQLite release as of version 3.46.0.

## Schema Storage

The database schema is stored in a special table called `sqlite_master` (aliased as `sqlite_schema` since version 3.33.0). This table exists on page 1 of every SQLite database and has the following structure:

```sql
CREATE TABLE sqlite_master(
    type TEXT,      -- 'table', 'index', 'view', or 'trigger'
    name TEXT,      -- Name of the object
    tbl_name TEXT,  -- Table the object is associated with
    rootpage INTEGER, -- Root page number for tables and indexes
    sql TEXT        -- SQL text that created the object
);
```

When SQLite opens a database, it reads the entire sqlite_master table to reconstruct the schema in memory. The schema cookie (at byte offset 40 in the header) is incremented each time the schema changes, which allows SQLite to detect when it needs to re-read the schema.

## Freelist Management

When rows are deleted or tables are dropped, the pages that were used become free pages. These pages are added to a freelist rather than being returned to the operating system. The freelist is organized as a linked list of trunk pages, where each trunk page can hold up to `(usable_size/4 - 2)` pointers to leaf freelist pages.

The first freelist trunk page number is stored at byte offset 32 in the database file header. The total count of freelist pages is at byte offset 36.

### Auto-Vacuum

In non-auto-vacuum mode (the default), the database file never shrinks. Freed pages are reused by subsequent INSERT operations but the file size does not decrease. To reduce the file size, the `VACUUM` command can be used.

Auto-vacuum mode causes the database file to shrink automatically when pages are freed. Auto-vacuum must be enabled before any tables are created (it cannot be turned on after the fact for an existing database). There are two sub-modes:

- **Full auto-vacuum** (`PRAGMA auto_vacuum = FULL`): Pages are moved to fill gaps immediately when data is deleted.
- **Incremental auto-vacuum** (`PRAGMA auto_vacuum = INCREMENTAL`): Pages are only reclaimed when `PRAGMA incremental_vacuum(N)` is called, where N is the number of pages to free.

Auto-vacuum mode uses pointer map pages to track the parent of every page in the database, which adds a small overhead to every write operation.

## Record Format

SQLite stores each row of a table as a record (also called a "payload"). The record format consists of a header followed by data values:

1. **Header size** — a varint giving the total size of the header (including itself)
2. **Serial type codes** — one varint per column, indicating the type and size of the value:

| Serial Type | Meaning | Size (bytes) |
|-|-|-|
| 0 | NULL | 0 |
| 1 | 8-bit signed integer | 1 |
| 2 | 16-bit big-endian signed integer | 2 |
| 3 | 24-bit big-endian signed integer | 3 |
| 4 | 32-bit big-endian signed integer | 4 |
| 5 | 48-bit big-endian signed integer | 6 |
| 6 | 64-bit big-endian signed integer | 8 |
| 7 | IEEE 754 64-bit floating point | 8 |
| 8 | Integer constant 0 (schema format >= 4) | 0 |
| 9 | Integer constant 1 (schema format >= 4) | 0 |
| 10-11 | Reserved for expansion | - |
| N >= 12, even | BLOB of (N-12)/2 bytes | (N-12)/2 |
| N >= 13, odd | TEXT of (N-13)/2 bytes | (N-13)/2 |

This encoding is very compact. A NULL value consumes zero bytes. Small integers (0 and 1) also consume zero bytes when using schema format 4. The serial type determines both the datatype and the amount of space consumed.

## Virtual Table Mechanism

SQLite supports virtual tables through a well-defined module interface. A virtual table is a table whose content is not stored in the database file but is computed on-the-fly by callback functions. Virtual tables are created using:

```sql
CREATE VIRTUAL TABLE tablename USING modulename(arguments);
```

The virtual table module must implement several callback functions, including `xCreate`, `xConnect`, `xBestIndex`, `xOpen`, `xClose`, `xFilter`, `xNext`, `xEof`, `xColumn`, and `xRowid`. The `xBestIndex` method is particularly important as it communicates with the query planner to describe which queries the virtual table can satisfy efficiently.

Built-in virtual table modules in the SQLite distribution include:
- **FTS3/FTS4/FTS5** — Full-text search
- **rtree** — R-Tree spatial indexing
- **json_each / json_tree** — JSON processing
- **csv** — Read CSV files as tables
- **dbstat** — Database file statistics

## Write Transactions

All changes to an SQLite database happen within a transaction. If no explicit transaction is started with BEGIN, each SQL statement runs in its own auto-transaction. SQLite uses a locking protocol with five lock states:

1. **UNLOCKED** — No locks held. Default state.
2. **SHARED** — Reading. Multiple processes can hold SHARED locks concurrently.
3. **RESERVED** — A process intends to write. Only one RESERVED lock at a time, but SHARED locks can coexist.
4. **PENDING** — A process is about to write. No new SHARED locks can be acquired, but existing SHARED locks are allowed to finish.
5. **EXCLUSIVE** — Writing. No other locks of any type can coexist.

In WAL mode, this locking protocol is replaced by a more concurrent mechanism using the shared-memory file.
