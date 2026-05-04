# Bun SQLite API

> Bun natively implements a high-performance SQLite3 driver.

Bun natively implements a high-performance [SQLite3](https://www.sqlite.org/) driver. To use it import from the built-in `bun:sqlite` module.

```ts
import { Database } from "bun:sqlite";

const db = new Database(":memory:");
const query = db.query("select 'Hello world' as message;");
query.get();
// { message: "Hello world" }
```

The API is simple, synchronous, and fast. Credit to [better-sqlite3](https://github.com/JoshuaWise/better-sqlite3) and its contributors for inspiring the API of `bun:sqlite`.

Features include:

* Transactions
* Parameters (named & positional)
* Prepared statements
* Datatype conversions (`BLOB` becomes `Uint8Array`)
* Map query results to classes without an ORM - `query.as(MyClass)`
* The fastest performance of any SQLite driver for JavaScript
* `bigint` support
* Multi-query statements (e.g. `SELECT 1; SELECT 2;`) in a single call to database.run(query)

The `bun:sqlite` module is roughly 3-6x faster than `better-sqlite3` and 8-9x faster than `deno.land/x/sqlite` for read queries. Each driver was benchmarked against the [Northwind Traders](https://github.com/jpwhite3/northwind-SQLite3/blob/46d5f8a64f396f87cd374d1600dbf521523980e8/Northwind_large.sqlite.zip) dataset.

## Database

To open or create a SQLite3 database:

```ts
import { Database } from "bun:sqlite";
const db = new Database("mydb.sqlite");
```

To open an in-memory database:

```ts
import { Database } from "bun:sqlite";

// all of these do the same thing
const db = new Database(":memory:");
const db = new Database();
const db = new Database("");
```

To open in `readonly` mode:

```ts
import { Database } from "bun:sqlite";
const db = new Database("mydb.sqlite", { readonly: true });
```

To create the database if the file doesn't exist:

```ts
import { Database } from "bun:sqlite";
const db = new Database("mydb.sqlite", { create: true });
```

### Strict mode

By default, `bun:sqlite` requires binding parameters to include the `$`, `:`, or `@` prefix, and does not throw an error if a parameter is missing.

To instead throw an error when a parameter is missing and allow binding without a prefix, set `strict: true` on the `Database` constructor:

```ts
import { Database } from "bun:sqlite";

const strict = new Database(":memory:", { strict: true });

// throws error because of the typo:
const query = strict.query("SELECT $message;").all({ messag: "Hello world" });

const notStrict = new Database(":memory:");
// does not throw error:
notStrict.query("SELECT $message;").all({ messag: "Hello world" });
```

### Load via ES module import

You can also use an import attribute to load a database.

```ts
import db from "./mydb.sqlite" with { type: "sqlite" };

console.log(db.query("select * from users LIMIT 1").get());
```

This is equivalent to the following:

```ts
import { Database } from "bun:sqlite";
const db = new Database("./mydb.sqlite");
```

### `.close(throwOnError: boolean = false)`

To close a database connection, but allow existing queries to finish, call `.close(false)`:

```ts
const db = new Database();
// ... do stuff
db.close(false);
```

To close the database and throw an error if there are any pending queries, call `.close(true)`:

```ts
const db = new Database();
// ... do stuff
db.close(true);
```

`close(false)` is called automatically when the database is garbage collected. It is safe to call multiple times but has no effect after the first.

### `using` statement

You can use the `using` statement to ensure that a database connection is closed when the `using` block is exited.

```ts
import { Database } from "bun:sqlite";

{
  using db = new Database("mydb.sqlite");
  using query = db.query("select 'Hello world' as message;");
  console.log(query.get());
}
// { message: "Hello world" }
```

### `.serialize()`

`bun:sqlite` supports SQLite's built-in mechanism for serializing and deserializing databases to and from memory.

```ts
const olddb = new Database("mydb.sqlite");
const contents = olddb.serialize(); // => Uint8Array
const newdb = Database.deserialize(contents);
```

Internally, `.serialize()` calls `sqlite3_serialize`.

### `.query()`

Use the `db.query()` method on your `Database` instance to prepare a SQL query. The result is a `Statement` instance that will be cached on the `Database` instance. The query will not be executed.

```ts
const query = db.query(`select "Hello world" as message`);
```

**What does "cached" mean?**

The caching refers to the **compiled prepared statement** (the SQL bytecode), not the query results. When you call `db.query()` with the same SQL string multiple times, Bun returns the same cached `Statement` object instead of recompiling the SQL.

It is completely safe to reuse a cached statement with different parameter values:

```ts
const query = db.query("SELECT * FROM users WHERE id = ?");
query.get(1); // Works
query.get(2); // Also works - parameters are bound fresh each time
query.get(3); // Still works
```

Use `.prepare()` instead of `.query()` when you want a fresh `Statement` instance that isn't cached, for example if you're dynamically generating SQL and don't want to fill the cache with one-off queries.

```ts
// compile the prepared statement without caching
const query = db.prepare("SELECT * FROM foo WHERE bar = ?");
```

## WAL mode

SQLite supports write-ahead log mode (WAL) which dramatically improves performance, especially in situations with many concurrent readers and a single writer. It's broadly recommended to enable WAL mode for most typical applications.

To enable WAL mode, run this pragma query at the beginning of your application:

```ts
db.run("PRAGMA journal_mode = WAL;");
```

In WAL mode, writes to the database are written directly to a separate file called the "WAL file" (`-wal`). A shared-memory index file (`-shm`) is also created for read coordination. The WAL file will be later integrated into the main database file.

### WAL sidecar file cleanup

When using WAL mode with a file-based database, SQLite creates two sidecar files alongside your database: a write-ahead log (`-wal`) and a shared-memory index (`-shm`). Whether these files are automatically removed after `.close()` depends on your platform:

* **macOS**: Bun uses the system-provided SQLite, which Apple builds with persistent WAL enabled. The `-wal` and `-shm` files **will persist** after close.
* **Linux** and **Windows**: Bun statically links its own SQLite build, which follows upstream defaults. The sidecar files are **typically removed** after close when no other connections are open.

To ensure sidecar files are cleaned up on all platforms, disable WAL persistence and run a truncating checkpoint before closing:

```ts
import { Database, constants } from "bun:sqlite";

const db = new Database("mydb.sqlite");
db.run("PRAGMA journal_mode = WAL;");

// ... use the database ...

// Disable persistent WAL (needed on macOS)
db.fileControl(constants.SQLITE_FCNTL_PERSIST_WAL, 0);
// Checkpoint and truncate the WAL file
db.run("PRAGMA wal_checkpoint(TRUNCATE);");
db.close();
// Only mydb.sqlite remains — no -wal or -shm files
```

## Statements

A `Statement` is a *prepared query*, which means it's been parsed and compiled into an efficient binary form. It can be executed multiple times in a performant way.

Create a statement with the `.query` method on your `Database` instance.

```ts
const query = db.query(`select "Hello world" as message`);
```

Queries can contain parameters. These can be numerical (`?1`) or named (`$param` or `:param` or `@param`).

```ts
const query = db.query(`SELECT ?1, ?2;`);
const query = db.query(`SELECT $param1, $param2;`);
```

### `.all()`

Use `.all()` to run a query and get back the results as an array of objects.

```ts
const query = db.query(`select $message;`);
query.all({ $message: "Hello world" });
// [{ message: "Hello world" }]
```

Internally, this calls `sqlite3_reset` and repeatedly calls `sqlite3_step` until it returns `SQLITE_DONE`.

### `.get()`

Use `.get()` to run a query and get back the first result as an object.

```ts
const query = db.query(`select $message;`);
query.get({ $message: "Hello world" });
// { $message: "Hello world" }
```

Internally, this calls `sqlite3_reset` followed by `sqlite3_step` until it no longer returns `SQLITE_ROW`. If the query returns no rows, `undefined` is returned.

### `.run()`

Use `.run()` to run a query and get back an object with execution metadata. This is useful for schema-modifying queries (e.g. `CREATE TABLE`) or bulk write operations.

```ts
const query = db.query(`create table foo;`);
query.run();
// { lastInsertRowid: 0, changes: 0 }
```

Internally, this calls `sqlite3_reset` and calls `sqlite3_step` once. The `lastInsertRowid` property returns the ID of the last row inserted into the database. The `changes` property is the number of rows affected by the query.

### `.as(Class)` - Map query results to a class

Use `.as(Class)` to run a query and get back the results as instances of a class. This lets you attach methods & getters/setters to results.

```ts
class Movie {
  title: string;
  year: number;

  get isMarvel() {
    return this.title.includes("Marvel");
  }
}

const query = db.query("SELECT title, year FROM movies").as(Movie);
const movies = query.all();
const first = query.get();

console.log(movies[0].isMarvel); // true
console.log(first.isMarvel); // true
```

As a performance optimization, the class constructor is not called, default initializers are not run, and private fields are not accessible. This is more like using `Object.create` than `new`. The class's prototype is assigned to the object, methods are attached, and getters/setters are set up, but the constructor is not called.

### `.iterate()` (`@@iterator`)

Use `.iterate()` to run a query and incrementally return results. This is useful for large result sets that you want to process one row at a time without loading all the results into memory.

```ts
const query = db.query("SELECT * FROM foo");
for (const row of query.iterate()) {
  console.log(row);
}
```

You can also use the `@@iterator` protocol:

```ts
const query = db.query("SELECT * FROM foo");
for (const row of query) {
  console.log(row);
}
```

### `.values()`

Use `values()` to run a query and get back all results as an array of arrays.

```ts
const query = db.query(`select $message;`);
query.values({ $message: "Hello world" });
query.values(2);
```

### `.finalize()`

Use `.finalize()` to destroy a `Statement` and free any resources associated with it. Once finalized, a `Statement` cannot be executed again. Typically, the garbage collector will do this for you, but explicit finalization may be useful in performance-sensitive applications.

### `.toString()`

Calling `toString()` on a `Statement` instance prints the expanded SQL query. This is useful for debugging.

```ts
const query = db.query("SELECT $param;");
console.log(query.toString()); // => "SELECT NULL"
query.run(42);
console.log(query.toString()); // => "SELECT 42"
```

Internally, this calls `sqlite3_expanded_sql`. The parameters are expanded using the most recently bound values.

## Parameters

Queries can contain parameters. These can be numerical (`?1`) or named (`$param` or `:param` or `@param`). Bind values to these parameters when executing the query:

```ts
const query = db.query("SELECT * FROM foo WHERE bar = $bar");
const results = query.all({ $bar: "bar" });
```

Numbered (positional) parameters work too:

```ts
const query = db.query("SELECT ?1, ?2");
const results = query.all("hello", "goodbye");
```

### `strict: true` lets you bind values without prefixes

By default, the `$`, `:`, and `@` prefixes are **included** when binding values to named parameters. To bind without these prefixes, use the `strict` option in the `Database` constructor.

## Integers

SQLite supports signed 64 bit integers, but JavaScript only supports signed 52 bit integers or arbitrary precision integers with `bigint`.

`bigint` input is supported everywhere, but by default `bun:sqlite` returns integers as `number` types. If you need to handle integers larger than 2^53, set `safeIntegers` option to `true` when creating a `Database` instance.

### `safeIntegers: true`

When `safeIntegers` is `true`, `bun:sqlite` will return integers as `bigint` types:

```ts
import { Database } from "bun:sqlite";

const db = new Database(":memory:", { safeIntegers: true });
const query = db.query(`SELECT ${BigInt(Number.MAX_SAFE_INTEGER) + 102n} as max_int`);
const result = query.get();
console.log(result.max_int); // 9007199254741093n
```

When `safeIntegers` is `true`, `bun:sqlite` will throw an error if a `bigint` value in a bound parameter exceeds 64 bits.

### `safeIntegers: false` (default)

When `safeIntegers` is `false`, `bun:sqlite` will return integers as `number` types and truncate any bits beyond 53.

## Transactions

Transactions are a mechanism for executing multiple queries in an *atomic* way; that is, either all of the queries succeed or none of them do. Create a transaction with the `db.transaction()` method:

```ts
const insertCat = db.prepare("INSERT INTO cats (name) VALUES ($name)");
const insertCats = db.transaction(cats => {
  for (const cat of cats) insertCat.run(cat);
});
```

The call to `db.transaction()` returns a new function (`insertCats`) that *wraps* the function that executes the queries.

The driver will automatically `begin` a transaction when `insertCats` is called and `commit` it when the wrapped function returns. If an exception is thrown, the transaction will be rolled back.

**Nested transactions** — Transaction functions can be called from inside other transaction functions. When doing so, the inner transaction becomes a savepoint.

Transactions also come with `deferred`, `immediate`, and `exclusive` versions.

```ts
insertCats(cats); // uses "BEGIN"
insertCats.deferred(cats); // uses "BEGIN DEFERRED"
insertCats.immediate(cats); // uses "BEGIN IMMEDIATE"
insertCats.exclusive(cats); // uses "BEGIN EXCLUSIVE"
```

### `.loadExtension()`

To load a SQLite extension, call `.loadExtension(name)` on your `Database` instance.

```ts
import { Database } from "bun:sqlite";
const db = new Database();
db.loadExtension("myext");
```

**MacOS users**: By default, macOS ships with Apple's proprietary build of SQLite, which doesn't support extensions. To use extensions, install a vanilla build of SQLite via Homebrew and call `Database.setCustomSQLite(path)` before creating any `Database` instances.

### `.fileControl(cmd: number, value: any)`

To use the advanced `sqlite3_file_control` API, call `.fileControl(cmd, value)` on your `Database` instance.

```ts
import { Database, constants } from "bun:sqlite";
const db = new Database();
db.fileControl(constants.SQLITE_FCNTL_PERSIST_WAL, 0);
```

`value` can be: `number`, `TypedArray`, `undefined` or `null`.

## Reference

```ts
class Database {
  constructor(filename: string, options?: number | {
    readonly?: boolean;
    create?: boolean;
    readwrite?: boolean;
    safeIntegers?: boolean;
    strict?: boolean;
  });

  query<ReturnType, ParamsType>(sql: string): Statement<ReturnType, ParamsType>;
  prepare<ReturnType, ParamsType>(sql: string): Statement<ReturnType, ParamsType>;
  run(sql: string, params?: SQLQueryBindings): { lastInsertRowid: number; changes: number };
  exec = this.run;

  transaction(insideTransaction: (...args: any) => void): CallableFunction & {
    deferred: (...args: any) => void;
    immediate: (...args: any) => void;
    exclusive: (...args: any) => void;
  };

  close(throwOnError?: boolean): void;
}

class Statement<ReturnType, ParamsType> {
  all(...params: ParamsType[]): ReturnType[];
  get(...params: ParamsType[]): ReturnType | null;
  run(...params: ParamsType[]): { lastInsertRowid: number; changes: number };
  values(...params: ParamsType[]): unknown[][];
  finalize(): void;
  toString(): string;
  columnNames: string[];
  columnTypes: string[];
  declaredTypes: (string | null)[];
  paramsCount: number;
  native: any;
  as<T>(Class: new (...args: any[]) => T): Statement<T, ParamsType>;
}

type SQLQueryBindings =
  | string
  | bigint
  | TypedArray
  | number
  | boolean
  | null
  | Record<string, string | bigint | TypedArray | number | boolean | null>;
```

### Datatypes

| JavaScript type | SQLite type            |
| --------------- | ---------------------- |
| `string`        | `TEXT`                 |
| `number`        | `INTEGER` or `DECIMAL` |
| `boolean`       | `INTEGER` (1 or 0)     |
| `Uint8Array`    | `BLOB`                 |
| `Buffer`        | `BLOB`                 |
| `bigint`        | `INTEGER`              |
| `null`          | `NULL`                 |
