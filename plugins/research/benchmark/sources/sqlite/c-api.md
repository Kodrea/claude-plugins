# SQLite C/C++ API Reference

## Overview

The SQLite C API consists of over 300 functions, 30+ opaque data structures, and numerous constants. However, most applications only need a handful of core interfaces. The essential workflow for using SQLite from C is:

1. Open a database connection with `sqlite3_open_v2()`
2. Prepare a SQL statement with `sqlite3_prepare_v2()`
3. Bind parameters (if any) with `sqlite3_bind_*()` functions
4. Execute the statement by calling `sqlite3_step()` repeatedly
5. Extract column values with `sqlite3_column_*()` functions
6. Finalize the statement with `sqlite3_finalize()`
7. Close the database with `sqlite3_close_v2()`

The SQLite library is thread-safe by default when compiled with `SQLITE_THREADSAFE=1` (the default). However, a single database connection should not be used simultaneously from multiple threads without external synchronization, unless the connection was opened in serialized mode.

## Core Objects

### sqlite3 — Database Connection

The `sqlite3` object represents a single database connection. It is created by `sqlite3_open()` or `sqlite3_open_v2()` and destroyed by `sqlite3_close()` or `sqlite3_close_v2()`.

### sqlite3_stmt — Prepared Statement

The `sqlite3_stmt` object represents a single compiled SQL statement. It is created by `sqlite3_prepare_v2()` and destroyed by `sqlite3_finalize()`. A prepared statement can be reused multiple times by calling `sqlite3_reset()` between executions.

### sqlite3_value — Dynamically Typed Value

The `sqlite3_value` object represents a single value in SQLite's type system. It is used to pass values to and from application-defined SQL functions.

### sqlite3_context — Function Evaluation Context

The `sqlite3_context` object provides context for application-defined SQL functions during evaluation.

## Opening and Closing Databases

### sqlite3_open_v2()

```c
int sqlite3_open_v2(
    const char *filename,   /* Database filename (UTF-8) */
    sqlite3 **ppDb,         /* OUT: SQLite db handle */
    int flags,              /* Flags */
    const char *zVfs        /* Name of VFS module to use, or NULL */
);
```

The `flags` parameter controls how the database is opened:

| Flag | Value | Description |
|-|-|-|
| SQLITE_OPEN_READONLY | 0x00000001 | Open for reading only |
| SQLITE_OPEN_READWRITE | 0x00000002 | Open for reading and writing |
| SQLITE_OPEN_CREATE | 0x00000004 | Create the database if it does not exist |
| SQLITE_OPEN_URI | 0x00000040 | Enable URI filename interpretation |
| SQLITE_OPEN_MEMORY | 0x00000080 | Open an in-memory database |
| SQLITE_OPEN_NOMUTEX | 0x00008000 | Multi-thread mode: no mutexes on connection |
| SQLITE_OPEN_FULLMUTEX | 0x00010000 | Serialized mode: mutexes on every API call |
| SQLITE_OPEN_SHAREDCACHE | 0x00020000 | Enable shared cache mode |
| SQLITE_OPEN_PRIVATECACHE | 0x00040000 | Disable shared cache for this connection |
| SQLITE_OPEN_NOFOLLOW | 0x01000000 | Do not follow symbolic links (since 3.31.0) |

The most common combination is `SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE`, which opens the database for reading and writing and creates it if it does not exist. This is the behavior of the simpler `sqlite3_open()` function.

Simplified versions:

```c
int sqlite3_open(const char *filename, sqlite3 **ppDb);
int sqlite3_open16(const void *filename, sqlite3 **ppDb);  /* UTF-16 filename */
```

### sqlite3_close_v2()

```c
int sqlite3_close_v2(sqlite3 *db);
```

Closes a database connection. Unlike `sqlite3_close()`, the `_v2` variant is a "destructor" that will defer closing if there are unfinalized prepared statements or unfinished backups. The connection becomes a "zombie" and is automatically deallocated when the last prepared statement is finalized. This makes it safe to call `sqlite3_close_v2()` at any time.

## Preparing and Executing SQL

### sqlite3_prepare_v2()

```c
int sqlite3_prepare_v2(
    sqlite3 *db,            /* Database handle */
    const char *zSql,       /* SQL statement, UTF-8 encoded */
    int nByte,              /* Maximum length of zSql in bytes (-1 for NUL-terminated) */
    sqlite3_stmt **ppStmt,  /* OUT: Statement handle */
    const char **pzTail     /* OUT: Pointer to unused portion of zSql */
);
```

This function compiles a single SQL statement into byte code. The `_v2` suffix indicates the "v2" interface which automatically re-prepares the statement if the schema changes (the older `sqlite3_prepare()` would return SQLITE_SCHEMA instead). There is also `sqlite3_prepare_v3()` which accepts an additional `prepFlags` parameter for controlling preparation behavior.

The prepared statement is a compiled bytecode program that is executed by SQLite's virtual database engine (VDBE). Each opcode in the VDBE program performs a specific operation such as opening a cursor, seeking to a key, or comparing values.

### sqlite3_step()

```c
int sqlite3_step(sqlite3_stmt *pStmt);
```

Evaluates the prepared statement one step. For statements that return data (SELECT), each call to `sqlite3_step()` returns `SQLITE_ROW` when a new row is available, and `SQLITE_DONE` when there are no more rows. For statements that do not return data (INSERT, UPDATE, DELETE), `sqlite3_step()` returns `SQLITE_DONE` immediately upon successful completion.

### sqlite3_finalize()

```c
int sqlite3_finalize(sqlite3_stmt *pStmt);
```

Destroys a prepared statement. Every prepared statement must be finalized to avoid memory leaks. Calling `sqlite3_finalize()` on a NULL pointer is harmless.

### sqlite3_reset()

```c
int sqlite3_reset(sqlite3_stmt *pStmt);
```

Resets a prepared statement back to its initial state, ready to be re-executed. This does not clear parameter bindings (use `sqlite3_clear_bindings()` for that). Resetting and re-executing a prepared statement is much faster than finalizing it and preparing a new one.

### sqlite3_exec()

```c
int sqlite3_exec(
    sqlite3 *db,                    /* Database handle */
    const char *sql,                /* SQL to be evaluated */
    int (*callback)(void*, int, char**, char**),  /* Callback function */
    void *arg,                      /* 1st argument to callback */
    char **errmsg                   /* Error msg written here */
);
```

A convenience wrapper that combines `sqlite3_prepare_v2()`, `sqlite3_step()`, and `sqlite3_finalize()` into a single call. It can execute multiple SQL statements separated by semicolons. `sqlite3_exec()` is suitable for simple cases but lacks the flexibility and performance benefits of using prepared statements directly.

## Binding Parameters

Parameters in SQL statements are denoted by `?`, `?NNN`, `:VVV`, `@VVV`, or `$VVV` placeholders. These are bound to values before execution:

```c
int sqlite3_bind_int(sqlite3_stmt*, int index, int value);
int sqlite3_bind_int64(sqlite3_stmt*, int index, sqlite3_int64 value);
int sqlite3_bind_double(sqlite3_stmt*, int index, double value);
int sqlite3_bind_text(sqlite3_stmt*, int index, const char *value, int nBytes,
                      void(*destructor)(void*));
int sqlite3_bind_blob(sqlite3_stmt*, int index, const void *value, int nBytes,
                      void(*destructor)(void*));
int sqlite3_bind_null(sqlite3_stmt*, int index);
int sqlite3_bind_zeroblob(sqlite3_stmt*, int index, int n);
int sqlite3_bind_value(sqlite3_stmt*, int index, const sqlite3_value *value);
int sqlite3_bind_pointer(sqlite3_stmt*, int index, void *ptr, const char *type,
                         void(*destructor)(void*));
```

The `index` parameter is 1-based (the first parameter is 1, not 0). The `destructor` parameter for text and blob bindings can be `SQLITE_STATIC` (the application manages the memory), `SQLITE_TRANSIENT` (SQLite makes a private copy), or a pointer to a destructor function.

The `sqlite3_bind_parameter_count()` function returns the number of parameters in a statement. The `sqlite3_bind_parameter_index()` function returns the index of a named parameter.

## Extracting Column Values

After `sqlite3_step()` returns `SQLITE_ROW`, column values can be extracted:

```c
int sqlite3_column_int(sqlite3_stmt*, int iCol);
sqlite3_int64 sqlite3_column_int64(sqlite3_stmt*, int iCol);
double sqlite3_column_double(sqlite3_stmt*, int iCol);
const unsigned char *sqlite3_column_text(sqlite3_stmt*, int iCol);
const void *sqlite3_column_text16(sqlite3_stmt*, int iCol);
const void *sqlite3_column_blob(sqlite3_stmt*, int iCol);
int sqlite3_column_bytes(sqlite3_stmt*, int iCol);
int sqlite3_column_bytes16(sqlite3_stmt*, int iCol);
int sqlite3_column_type(sqlite3_stmt*, int iCol);
sqlite3_value *sqlite3_column_value(sqlite3_stmt*, int iCol);
```

The `iCol` parameter is 0-based. The `sqlite3_column_count()` function returns the number of columns in the result set. The `sqlite3_column_name()` function returns the name of a column.

The `sqlite3_column_type()` function returns one of the fundamental datatypes:

| Constant | Value | Description |
|-|-|-|
| SQLITE_INTEGER | 1 | 64-bit signed integer |
| SQLITE_FLOAT | 2 | 64-bit IEEE 754 float |
| SQLITE_TEXT | 3 | Text string |
| SQLITE_BLOB | 4 | Binary blob |
| SQLITE_NULL | 5 | NULL value |

## Error Handling

### Result Codes

SQLite functions return integer result codes. The primary result codes are:

| Code | Value | Meaning |
|-|-|-|
| SQLITE_OK | 0 | Successful result |
| SQLITE_ERROR | 1 | Generic error |
| SQLITE_INTERNAL | 2 | Internal logic error |
| SQLITE_PERM | 3 | Access permission denied |
| SQLITE_ABORT | 4 | Callback routine requested abort |
| SQLITE_BUSY | 5 | Database is locked |
| SQLITE_LOCKED | 6 | Table in the database is locked |
| SQLITE_NOMEM | 7 | malloc() failed |
| SQLITE_READONLY | 8 | Attempt to write to a readonly database |
| SQLITE_INTERRUPT | 9 | sqlite3_interrupt() called |
| SQLITE_IOERR | 10 | Disk I/O error |
| SQLITE_CORRUPT | 11 | Database disk image is malformed |
| SQLITE_NOTFOUND | 12 | Unknown opcode in sqlite3_file_control() |
| SQLITE_FULL | 13 | Database or disk is full |
| SQLITE_CANTOPEN | 14 | Unable to open database file |
| SQLITE_PROTOCOL | 15 | Database lock protocol error |
| SQLITE_SCHEMA | 17 | Schema changed |
| SQLITE_TOOBIG | 18 | String or BLOB exceeds size limit |
| SQLITE_CONSTRAINT | 19 | Constraint violation |
| SQLITE_MISMATCH | 20 | Data type mismatch |
| SQLITE_MISUSE | 21 | Library used incorrectly |
| SQLITE_AUTH | 23 | Authorization denied |
| SQLITE_ROW | 100 | sqlite3_step() has another row ready |
| SQLITE_DONE | 101 | sqlite3_step() has finished executing |

### Extended Result Codes

Extended result codes provide more specific error information. They can be enabled with `sqlite3_extended_result_codes(db, 1)`. Examples:

- `SQLITE_IOERR_READ` (266) — Error reading from disk
- `SQLITE_IOERR_WRITE` (778) — Error writing to disk
- `SQLITE_BUSY_RECOVERY` (261) — Another process is recovering a WAL
- `SQLITE_BUSY_SNAPSHOT` (517) — Cannot promote read to write because of WAL snapshot
- `SQLITE_CONSTRAINT_UNIQUE` (2067) — UNIQUE constraint violation
- `SQLITE_CONSTRAINT_PRIMARYKEY` (1555) — PRIMARY KEY constraint violation
- `SQLITE_CONSTRAINT_FOREIGNKEY` (787) — FOREIGN KEY constraint violation

### Error Messages

```c
const char *sqlite3_errmsg(sqlite3 *db);       /* UTF-8 error message */
const void *sqlite3_errmsg16(sqlite3 *db);     /* UTF-16 error message */
int sqlite3_errcode(sqlite3 *db);              /* Most recent error code */
int sqlite3_extended_errcode(sqlite3 *db);     /* Extended error code */
const char *sqlite3_errstr(int errcode);       /* English description of result code */
```

## Threading Modes

SQLite supports three threading modes, selected at compile time and optionally changed at runtime:

1. **Single-thread** (`SQLITE_THREADSAFE=0`): All mutexes are disabled. Using SQLite from more than one thread is unsafe.

2. **Multi-thread** (`SQLITE_THREADSAFE=2`): SQLite can be safely used by multiple threads provided no single database connection is used simultaneously in two or more threads. This is also activated per-connection with `SQLITE_OPEN_NOMUTEX`.

3. **Serialized** (`SQLITE_THREADSAFE=1`, the default): SQLite can be safely used by multiple threads with no restriction. The library uses mutexes to serialize access. This can also be activated per-connection with `SQLITE_OPEN_FULLMUTEX`.

The threading mode can be queried at runtime:

```c
int sqlite3_threadsafe(void);  /* Returns 0, 1, or 2 */
```

And changed at startup (before any other SQLite calls):

```c
sqlite3_config(SQLITE_CONFIG_SINGLETHREAD);  /* mode 0 */
sqlite3_config(SQLITE_CONFIG_MULTITHREAD);   /* mode 2 */
sqlite3_config(SQLITE_CONFIG_SERIALIZED);    /* mode 1 */
```

## Application-Defined Functions

SQLite allows applications to define custom SQL functions:

```c
int sqlite3_create_function_v2(
    sqlite3 *db,
    const char *zFunctionName,
    int nArg,           /* Number of arguments (-1 for any) */
    int eTextRep,       /* SQLITE_UTF8, SQLITE_UTF16, etc. */
    void *pApp,         /* Application data pointer */
    void (*xFunc)(sqlite3_context*, int, sqlite3_value**),    /* Scalar function */
    void (*xStep)(sqlite3_context*, int, sqlite3_value**),    /* Aggregate step */
    void (*xFinal)(sqlite3_context*),                          /* Aggregate final */
    void (*xDestroy)(void*)                                    /* Destructor for pApp */
);
```

For scalar functions, only `xFunc` is provided. For aggregate functions, `xStep` and `xFinal` are provided. For window functions (since 3.25.0), there is `sqlite3_create_window_function()` which additionally takes `xValue` and `xInverse` callbacks.

Within a function implementation, use these to set the return value:

```c
void sqlite3_result_int(sqlite3_context*, int);
void sqlite3_result_int64(sqlite3_context*, sqlite3_int64);
void sqlite3_result_double(sqlite3_context*, double);
void sqlite3_result_text(sqlite3_context*, const char*, int nBytes, void(*)(void*));
void sqlite3_result_blob(sqlite3_context*, const void*, int nBytes, void(*)(void*));
void sqlite3_result_null(sqlite3_context*);
void sqlite3_result_error(sqlite3_context*, const char*, int);
void sqlite3_result_error_code(sqlite3_context*, int);
```

## Hooks and Callbacks

SQLite provides several hooks for monitoring database activity:

```c
/* Called before each UPDATE, INSERT, or DELETE */
void *sqlite3_update_hook(
    sqlite3 *db,
    void (*callback)(void*, int, const char*, const char*, sqlite3_int64),
    void *pArg
);

/* Called when a transaction is committed */
void *sqlite3_commit_hook(sqlite3 *db, int (*callback)(void*), void *pArg);

/* Called when a transaction is rolled back */
void *sqlite3_rollback_hook(sqlite3 *db, void (*callback)(void*), void *pArg);

/* Called for each SQL statement as it is being compiled (for authorization) */
int sqlite3_set_authorizer(
    sqlite3 *db,
    int (*xAuth)(void*, int, const char*, const char*, const char*, const char*),
    void *pUserData
);

/* Called to log messages */
int sqlite3_config(SQLITE_CONFIG_LOG, void(*xLog)(void*, int, const char*), void*);
```

The `sqlite3_update_hook()` callback receives the operation type (`SQLITE_INSERT`, `SQLITE_UPDATE`, or `SQLITE_DELETE`), the database name, the table name, and the rowid of the affected row.

## Memory Management

SQLite uses its own memory allocator by default. Key memory-related functions:

```c
/* Set memory limit */
sqlite3_int64 sqlite3_soft_heap_limit64(sqlite3_int64 N);  /* Soft limit */
sqlite3_int64 sqlite3_hard_heap_limit64(sqlite3_int64 N);  /* Hard limit (since 3.31.0) */

/* Query memory usage */
sqlite3_int64 sqlite3_memory_used(void);      /* Current memory in use */
sqlite3_int64 sqlite3_memory_highwater(int resetFlag);  /* Peak memory usage */

/* Release memory */
int sqlite3_release_memory(int n);  /* Try to free n bytes of memory */
int sqlite3_db_release_memory(sqlite3 *db);  /* Free unused memory for a connection */

/* Custom allocator */
sqlite3_config(SQLITE_CONFIG_MALLOC, sqlite3_mem_methods*);
```

The `sqlite3_soft_heap_limit64()` function sets a soft limit on heap memory usage. When the limit is exceeded, SQLite tries to free cached memory (like page cache entries) to get below the limit. The `sqlite3_hard_heap_limit64()` function sets an upper bound that cannot be exceeded — allocations that would exceed this limit will fail with SQLITE_NOMEM.

## VFS (Virtual File System)

The VFS layer abstracts all I/O operations, allowing SQLite to be ported to different platforms. The default VFS on Unix is "unix" and on Windows is "win32". Custom VFS implementations can be registered:

```c
int sqlite3_vfs_register(sqlite3_vfs *pVfs, int makeDflt);
int sqlite3_vfs_unregister(sqlite3_vfs *pVfs);
sqlite3_vfs *sqlite3_vfs_find(const char *zVfsName);
```

A VFS must implement these file methods (among others):

- `xOpen` — Open a file
- `xDelete` — Delete a file
- `xAccess` — Check file existence and permissions
- `xFullPathname` — Convert to full pathname
- `xRandomness` — Generate random bytes
- `xCurrentTime` — Get current time
- `xSleep` — Sleep for a number of microseconds

The file object returned by `xOpen` must implement `xRead`, `xWrite`, `xTruncate`, `xSync`, `xFileSize`, `xLock`, `xUnlock`, `xCheckReservedLock`, and `xFileControl` methods.

## Compile-Time Options

SQLite behavior can be customized through numerous compile-time options:

```c
/* Thread safety */
-DSQLITE_THREADSAFE=1        /* Default: serialized mode */

/* Performance */
-DSQLITE_DEFAULT_MEMSTATUS=0  /* Disable memory tracking (saves CPU) */
-DSQLITE_DEFAULT_WAL_SYNCHRONOUS=1  /* NORMAL sync for WAL mode */
-DSQLITE_DQS=0               /* Disable double-quoted strings as string literals */
-DSQLITE_LIKE_DOESNT_MATCH_BLOBS  /* LIKE does not match BLOB values */
-DSQLITE_OMIT_AUTOINIT       /* Require manual sqlite3_initialize() */

/* Limits */
-DSQLITE_MAX_EXPR_DEPTH=1000         /* Default expression tree depth */
-DSQLITE_MAX_COLUMN=2000             /* Default max columns */
-DSQLITE_MAX_SQL_LENGTH=1000000000   /* Default max SQL length */
-DSQLITE_MAX_ATTACHED=10             /* Default max attached databases */
-DSQLITE_MAX_PAGE_COUNT=4294967294   /* Default max pages in a database */
-DSQLITE_DEFAULT_PAGE_SIZE=4096      /* Default page size */
-DSQLITE_DEFAULT_CACHE_SIZE=-2000    /* Default page cache size in KB */

/* Feature toggles */
-DSQLITE_ENABLE_FTS5          /* Enable FTS5 full-text search */
-DSQLITE_ENABLE_RTREE         /* Enable R-Tree module */
-DSQLITE_ENABLE_JSON1         /* Enable JSON functions (built-in since 3.38.0) */
-DSQLITE_ENABLE_GEOPOLY       /* Enable Geopoly extension */
-DSQLITE_ENABLE_MATH_FUNCTIONS  /* Enable math functions (log, pow, etc.) */
```

## The Amalgamation

The SQLite amalgamation is a single C source file ("sqlite3.c") and a single header file ("sqlite3.h") that contain the entire SQLite library. The amalgamation is created by concatenating all the individual source files together. Using the amalgamation results in better compiler optimization (since the compiler can see all the code at once) and is the recommended way to embed SQLite in an application. The amalgamation is approximately 155,000 lines of code and compiles to around 750 KB of object code.
