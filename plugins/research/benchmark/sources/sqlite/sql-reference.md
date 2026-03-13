# SQLite SQL Reference

## SQL Dialect Overview

SQLite implements most of the SQL-92 standard, with some omissions and extensions. SQLite does not support RIGHT OUTER JOIN or FULL OUTER JOIN (only LEFT OUTER JOIN and CROSS JOIN are supported). Since version 3.39.0 (2022-07-21), RIGHT and FULL OUTER JOIN are supported. SQLite also does not support the GRANT or REVOKE commands, since access control is managed at the filesystem level rather than within the database engine.

SQLite uses a dynamic type system called "type affinity" rather than the strict typing found in most other SQL databases. Any column can hold any type of value regardless of the declared type, with a few exceptions when STRICT tables are used.

## Type Affinity

Every column in an SQLite table has a type affinity. The type affinity of a column is the recommended type for data stored in that column. The five type affinities in SQLite are:

1. **TEXT** — stores values as text strings (UTF-8, UTF-16BE, or UTF-16LE)
2. **NUMERIC** — may contain values using any of the five storage classes
3. **INTEGER** — behaves like NUMERIC with an additional preference for integer storage
4. **REAL** — behaves like NUMERIC except it forces integer values into floating-point representation
5. **BLOB** — no preference for any storage class; data is stored exactly as supplied

The affinity of a column is determined by the declared type of the column, according to the following rules applied in order:

1. If the declared type contains the string "INT" (case-insensitive), the affinity is INTEGER.
2. If the declared type contains "CHAR", "CLOB", or "TEXT", the affinity is TEXT.
3. If the declared type contains "BLOB" or no type is specified, the affinity is BLOB.
4. If the declared type contains "REAL", "FLOA", or "DOUB", the affinity is REAL.
5. Otherwise, the affinity is NUMERIC.

This means that a column declared as `VARCHAR(255)` has TEXT affinity (because it contains "CHAR"), while a column declared as `BIGINT` has INTEGER affinity (because it contains "INT"). A column declared as `BOOLEAN` has NUMERIC affinity (because none of the special strings are present).

### STRICT Tables

Since SQLite version 3.37.0 (2021-11-27), tables can be declared as STRICT:

```sql
CREATE TABLE t1(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    value REAL
) STRICT;
```

In a STRICT table, the allowed column types are limited to: INT, INTEGER, REAL, TEXT, BLOB, and ANY. Type checking is enforced on insertion and update — attempting to store a text value in an INT column will raise a type mismatch error rather than silently coercing the value.

### Storage Classes

SQLite has five storage classes for values:

1. **NULL** — the value is a null value
2. **INTEGER** — a signed integer, stored in 1, 2, 3, 4, 6, or 8 bytes depending on magnitude
3. **REAL** — a floating-point value stored as an 8-byte IEEE 754 number
4. **TEXT** — a text string stored using the database encoding
5. **BLOB** — a blob of data stored exactly as it was input

The `typeof()` function can be used to determine the storage class of a value.

## PRAGMA Statements

PRAGMAs are SQLite-specific SQL extensions used to modify library behavior or query internal state. Some commonly used PRAGMAs:

### Database Configuration

```sql
-- Set/query the page size (must be set before creating tables)
PRAGMA page_size = 4096;

-- Set journal mode
PRAGMA journal_mode = WAL;

-- Enable/disable foreign key enforcement (off by default)
PRAGMA foreign_keys = ON;

-- Set the number of pages in the page cache
PRAGMA cache_size = -2000;  -- Negative means KB, so -2000 = 2MB cache

-- Query or set the database text encoding
PRAGMA encoding = 'UTF-8';

-- Set synchronous mode
PRAGMA synchronous = NORMAL;  -- Options: OFF, NORMAL, FULL, EXTRA

-- Enable/disable auto-vacuum
PRAGMA auto_vacuum = FULL;  -- Options: NONE, FULL, INCREMENTAL

-- Set the busy timeout in milliseconds
PRAGMA busy_timeout = 5000;
```

### Query and Analysis

```sql
-- Show the query plan for a statement
EXPLAIN QUERY PLAN SELECT * FROM t1 WHERE x = 5;

-- List all tables
PRAGMA table_list;

-- Show column info for a table
PRAGMA table_info(tablename);
-- Extended version with hidden columns and generated column info
PRAGMA table_xinfo(tablename);

-- List all indexes for a table
PRAGMA index_list(tablename);

-- Show columns in an index
PRAGMA index_info(indexname);

-- Database integrity check
PRAGMA integrity_check;
-- Faster partial check
PRAGMA quick_check;

-- Show compile-time options
PRAGMA compile_options;

-- Query the SQLite version
SELECT sqlite_version();  -- Returns e.g. '3.46.0'
```

### PRAGMA synchronous

The `synchronous` pragma controls how aggressively SQLite syncs data to disk. The levels are:

| Value | Name | Description |
|-|-|-|
| 0 | OFF | No syncs at all. Fastest but risk of corruption on crash. |
| 1 | NORMAL | Syncs at critical moments but not after every transaction. Reasonable compromise. |
| 2 | FULL | Syncs after every transaction. Default for DELETE journal mode. Safe against power loss. |
| 3 | EXTRA | Like FULL but also syncs the rollback journal/WAL before writing to the database. Maximum safety. |

When using WAL mode, `PRAGMA synchronous = NORMAL` is generally recommended as it provides good durability without the performance overhead of FULL synchronous in every transaction.

## Built-in Functions

### Aggregate Functions

```sql
-- Standard aggregates
SELECT count(*), sum(x), avg(x), min(x), max(x), total(x), group_concat(x, ',')
FROM t1;

-- total() returns 0.0 for empty sets (unlike sum() which returns NULL)
```

### Scalar Functions

SQLite includes numerous built-in scalar functions:

```sql
-- String functions
abs(x)            -- Absolute value
coalesce(x, y, ...)  -- First non-null argument
glob(pattern, str)   -- GLOB pattern matching
hex(x)            -- Convert to hexadecimal
ifnull(x, y)      -- If x is null, return y
iif(cond, x, y)   -- Inline if (added in 3.32.0)
instr(str, sub)   -- Position of substring
length(x)         -- String length in characters
like(pattern, str) -- LIKE pattern matching
lower(x)          -- Convert to lowercase
ltrim(x), rtrim(x), trim(x)  -- Trim whitespace
max(x, y, ...)    -- Maximum of arguments (scalar version)
min(x, y, ...)    -- Minimum of arguments (scalar version)
nullif(x, y)      -- NULL if x == y
printf(fmt, ...)  -- Formatted string (renamed to format() in 3.38.0)
quote(x)          -- SQL literal representation
random()          -- Random 64-bit integer
randomblob(n)     -- N bytes of random BLOB
replace(str, old, new)  -- String replacement
round(x, n)       -- Round to n decimal places
sign(x)           -- Returns -1, 0, or +1 (added in 3.39.0)
substr(str, start, len)  -- Substring extraction
typeof(x)         -- Returns type name as string
unicode(x)        -- Unicode code point of first character
upper(x)          -- Convert to uppercase
zeroblob(n)       -- BLOB of n zero bytes
```

### Date and Time Functions

SQLite has five date and time functions that all take a time string as the first argument and zero or more modifiers:

```sql
date(timestring, modifier, modifier, ...)       -- Returns 'YYYY-MM-DD'
time(timestring, modifier, modifier, ...)       -- Returns 'HH:MM:SS'
datetime(timestring, modifier, modifier, ...)   -- Returns 'YYYY-MM-DD HH:MM:SS'
julianday(timestring, modifier, modifier, ...)  -- Returns Julian day number
strftime(format, timestring, modifier, ...)     -- Returns formatted string
unixepoch(timestring, modifier, ...)            -- Returns Unix timestamp (added 3.38.0)
timediff(time1, time2)                          -- Returns difference (added 3.43.0)
```

Time strings can be in ISO 8601 format, Julian day numbers, Unix timestamps (with 'unixepoch' modifier), or the special string 'now' for the current time.

### JSON Functions (since 3.9.0)

SQLite has extensive JSON support through built-in functions:

```sql
-- Extract values
json_extract(json, path)    -- Extract value at path (returns SQL type)
json(json_text) -> path     -- Shorthand for json_extract (since 3.38.0)
json(json_text) ->> path    -- Extract as text (since 3.38.0)

-- Construct JSON
json_object('key1', val1, 'key2', val2)
json_array(val1, val2, val3)
json_group_array(value)     -- Aggregate: collect values into JSON array
json_group_object(key, val) -- Aggregate: collect key/value pairs into JSON object

-- Modify JSON
json_set(json, path, value)      -- Set value (create if not exists)
json_insert(json, path, value)   -- Insert only if path does not exist
json_replace(json, path, value)  -- Replace only if path exists
json_remove(json, path)          -- Remove element at path
json_patch(json1, json2)         -- RFC 7396 merge patch

-- Query JSON
json_type(json, path)      -- Returns type name at path
json_valid(json)           -- Returns 1 if valid JSON
json_each(json)            -- Table-valued function: iterate top-level
json_tree(json)            -- Table-valued function: iterate recursively
```

### Window Functions (since 3.25.0)

SQLite supports standard window functions:

```sql
SELECT
    row_number() OVER (ORDER BY x),
    rank() OVER (ORDER BY x),
    dense_rank() OVER (ORDER BY x),
    ntile(4) OVER (ORDER BY x),
    lag(x, 1) OVER (ORDER BY x),
    lead(x, 1) OVER (ORDER BY x),
    first_value(x) OVER (ORDER BY x),
    last_value(x) OVER (ORDER BY x),
    nth_value(x, 2) OVER (ORDER BY x),
    cume_dist() OVER (ORDER BY x),
    percent_rank() OVER (ORDER BY x)
FROM t1;
```

Window functions can also use named window definitions:

```sql
SELECT row_number() OVER win, sum(x) OVER win
FROM t1
WINDOW win AS (ORDER BY y ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING);
```

## Common Table Expressions (CTEs)

SQLite supports both ordinary and recursive CTEs:

```sql
-- Ordinary CTE
WITH regional_sales AS (
    SELECT region, sum(amount) AS total_sales
    FROM orders GROUP BY region
)
SELECT * FROM regional_sales WHERE total_sales > 1000;

-- Recursive CTE
WITH RECURSIVE cnt(x) AS (
    VALUES(1)
    UNION ALL
    SELECT x+1 FROM cnt WHERE x < 100
)
SELECT x FROM cnt;
```

Recursive CTEs are powerful for generating series, traversing hierarchies, and graph operations.

## Generated Columns (since 3.31.0)

SQLite supports computed/generated columns:

```sql
CREATE TABLE t1(
    a INTEGER,
    b INTEGER,
    c INTEGER GENERATED ALWAYS AS (a + b) STORED,
    d TEXT GENERATED ALWAYS AS (printf('%d+%d', a, b)) VIRTUAL
);
```

- **STORED** generated columns are computed when the row is inserted or updated and are stored on disk.
- **VIRTUAL** generated columns are computed on-the-fly when read and do not occupy space on disk.

## UPSERT (since 3.24.0)

SQLite supports INSERT ... ON CONFLICT (upsert):

```sql
INSERT INTO t1(id, name, count) VALUES(1, 'Alice', 1)
ON CONFLICT(id) DO UPDATE SET count = count + 1;
```

Multiple ON CONFLICT clauses can be specified to handle different unique constraints.

## Returning Clause (since 3.35.0)

The RETURNING clause can be added to INSERT, UPDATE, and DELETE statements:

```sql
INSERT INTO t1(name) VALUES('test') RETURNING id, name;
DELETE FROM t1 WHERE x > 10 RETURNING *;
UPDATE t1 SET x = x + 1 WHERE id = 5 RETURNING x;
```

## Limitations

SQLite has several hard limits defined at compile time:

| Limit | Default Value |
|-|-|
| Maximum string or BLOB length | 1,000,000,000 bytes (1 GB) |
| Maximum number of columns | 2,000 |
| Maximum SQL statement length | 1,000,000,000 bytes (1 GB) |
| Maximum number of tables in a join | 64 |
| Maximum depth of an expression tree | 1,000 |
| Maximum number of arguments to a function | 100 |
| Maximum number of terms in a compound SELECT | 500 |
| Maximum length of a LIKE or GLOB pattern | 50,000 |
| Maximum number of host parameters | 999 (SQLITE_MAX_VARIABLE_NUMBER) |
| Maximum depth of trigger recursion | 1,000 |
| Maximum number of attached databases | 10 (SQLITE_MAX_ATTACHED, can be raised to 125) |
| Maximum page count | 4,294,967,294 (2^32 - 2) |

With the default page size of 4096 bytes and the maximum page count of 4,294,967,294, the maximum database size is approximately 281 terabytes.

## ATTACH DATABASE

Multiple database files can be used simultaneously in a single connection:

```sql
ATTACH DATABASE 'other.db' AS other;
SELECT * FROM other.tablename;
DETACH DATABASE other;
```

The maximum number of attached databases is 10 by default (controlled by the SQLITE_MAX_ATTACHED compile-time option, which can be increased to 125).

## Special Column Names

SQLite has several special column names and behaviors:

- **rowid** — Every table (except WITHOUT ROWID tables) has an implicit 64-bit signed integer column called `rowid`. Aliases for `rowid` include `_rowid_` and `oid`.
- **INTEGER PRIMARY KEY** — When a column is declared as `INTEGER PRIMARY KEY` (exactly), it becomes an alias for `rowid`. This is the only case where the declared type matters for storage.
- **WITHOUT ROWID** — Tables created with `WITHOUT ROWID` do not have an implicit rowid and must have an explicit PRIMARY KEY. Without rowid tables are stored as index B-trees instead of table B-trees, which can be more efficient for tables with non-integer primary keys.

```sql
-- Regular table with rowid alias
CREATE TABLE t1(id INTEGER PRIMARY KEY, name TEXT);

-- WITHOUT ROWID table
CREATE TABLE t2(key TEXT PRIMARY KEY, value TEXT) WITHOUT ROWID;
```

## VACUUM

The `VACUUM` command rebuilds the entire database file, reclaiming unused space and defragmenting the file:

```sql
VACUUM;                        -- Rebuild the main database
VACUUM INTO 'backup.db';      -- Create a compacted copy (since 3.27.0)
```

VACUUM requires up to twice the size of the original database in free disk space, as it creates a temporary copy. VACUUM resets the database's auto-increment counters and may change the rowid of rows if the rowid was not explicitly set.
