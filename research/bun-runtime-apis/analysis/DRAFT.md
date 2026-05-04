# Bun Runtime APIs (HTTP server, file I/O, SQLite, FFI, test runner)

## Executive Summary

Bun is a JavaScript runtime that exposes a suite of native APIs covering the full application development lifecycle — from HTTP serving to database access, native library interop, and testing. This draft synthesizes 71 findings extracted from five source documents: `http-server.md`, `sqlite.md`, `ffi.md`, `test-runner.md`, and `bun-apis.md`.

The HTTP server (`Bun.serve`) is Bun's most feature-rich API surface, offering built-in routing with dynamic parameters, WebSocket support, TLS configuration, idle timeout control, server lifecycle management, and per-request metrics. Benchmarks place it at roughly 2.5x the throughput of Node.js. The file I/O surface integrates tightly with the HTTP layer through `Bun.file()` lazy-loading.

The `bun:sqlite` module is a high-performance embedded SQLite driver — 3–6x faster than `better-sqlite3` — with first-class support for transactions, WAL mode, type-safe integer handling, and ORM-style result mapping. The `bun:ffi` module enables direct calls into native shared libraries using a JIT-compiled C binding layer (via embedded TinyCC), with pointer arithmetic, typed reads, and JavaScript callback support. The `bun:test` runner is Jest-compatible and offers concurrent execution, snapshot testing, flake detection, CI integration, and an extensive CLI flag set.

Adjacent APIs span a bundler (`Bun.build`), a native package manager (`bun install`), and configuration via `bunfig.toml`. Gaps cluster around WebSocket upgrade documentation, DOM testing examples, FFI memory management, and behavioral differences between `.prepare()` and `.query()`.

---

## HTTP Server

### Routing and Request Handling

`Bun.serve` (requiring Bun v1.2.3+ for the `routes` field) supports static routes, dynamic route parameters, and per-HTTP-method handlers in a single configuration object.

> ```ts
> const server = Bun.serve({
>   // `routes` requires Bun v1.2.3+
>   routes: {
>     // Static routes
>     "/api/status": new Response("OK"),
>
>     // Dynamic routes
>     "/users/:id": req => {
>       return new Response(`Hello User ${req.params.id}!`);
>     },
>
>     // Per-HTTP method handlers
>     "/api/posts": {
>       GET: () => new Response("List posts"),
>       POST: async req => {
>         const body = await req.json();
>         return Response.json({ created: true, ...body });
>       },
>     },
>   },
> });
> ```
> — *http-server.md:8*

### HTML Imports and Full-Stack Development

HTML imports enable full-stack development with HMR in development and pre-built manifests in production.

> **Development (`bun --hot`):** Assets are bundled on-demand at runtime, enabling hot module replacement (HMR) for a fast, iterative development experience. When you change your frontend code, the browser automatically updates without a full page reload.
>
> **Production (`bun build`):** When building with `bun build --target=bun`, the `import index from "./index.html"` statement resolves to a pre-built manifest object containing all bundled client assets.
> — *http-server.md:52*

### Port Configuration

Port 0 selects a random available port. Bun also reads `BUN_PORT`, `PORT`, and `NODE_PORT` environment variables and the `--port` CLI flag.

> To randomly select an available port, set `port` to `0`.
>
> ```ts
> const server = Bun.serve({
>   port: 0, // random port
>   fetch(req) {
>     return new Response("404!");
>   },
> });
>
> // server.port is the randomly selected port
> console.log(server.port);
> ```
>
> You can view the chosen port by accessing the `port` property on the server object, or by accessing the `url` property.
>
> Bun supports several options and environment variables to configure the default port. The default port is used when the `port` option is not set.
>
> * `--port` CLI flag: `bun --port=4002 server.ts`
> * `BUN_PORT` environment variable: `BUN_PORT=4002 bun server.ts`
> * `PORT` environment variable: `PORT=4002 bun server.ts`
> * `NODE_PORT` environment variable: `NODE_PORT=4002 bun server.ts`
> — *http-server.md:84*

### Unix Domain Sockets

`Bun.serve` can listen on Unix domain sockets and Linux abstract namespace sockets (null-byte prefix). Abstract namespace sockets are automatically removed when the last reference closes.

> ```ts
> Bun.serve({
>   unix: "/tmp/my-socket.sock", // path to socket
>   fetch(req) {
>     return new Response(`404!`);
>   },
> });
> ```
>
> ### Abstract namespace sockets
>
> Bun supports Linux abstract namespace sockets. To use an abstract namespace socket, prefix the `unix` path with a null byte.
>
> ```ts
> Bun.serve({
>   unix: "\0my-abstract-socket", // abstract namespace socket
>   fetch(req) {
>     return new Response(`404!`);
>   },
> });
> ```
>
> Unlike unix domain sockets, abstract namespace sockets are not bound to the filesystem and are automatically removed when the last reference to the socket is closed.
> — *http-server.md:114*

### Idle Timeout

Default idle timeout is 10 seconds, configurable up to 255 seconds. A zero value disables the timeout entirely. Timeout applies even to in-flight handlers that have not yet written any bytes.

> By default, `Bun.serve` closes connections after **10 seconds** of inactivity. A connection is considered idle when there is no data being sent or received — this includes in-flight requests where your handler is still running but hasn't written any bytes to the response yet. Browsers and `fetch()` clients will see this as a connection reset.
>
> To configure this, set the `idleTimeout` field (in seconds). The maximum value is `255`, and `0` disables the timeout entirely.
> — *http-server.md:143*

### Server Lifecycle

`server.stop()` gracefully drains in-flight connections; `stop(true)` forces immediate termination. `server.ref()` / `server.unref()` control whether the server keeps the Bun process alive.

> ```ts
> // Gracefully stop the server (waits for in-flight requests)
> await server.stop();
>
> // Force stop and close all active connections
> await server.stop(true);
> ```
>
> ### `server.ref()` and `server.unref()`
>
> Control whether the server keeps the Bun process alive:
>
> ```ts
> // Don't keep process alive if server is the only thing running
> server.unref();
>
> // Restore default behavior - keep process alive
> server.ref();
> ```
> — *http-server.md:196*

### Per-Request Controls

`server.timeout(req, seconds)` overrides the idle timeout for an individual request. `server.requestIP(req)` returns the client address and port.

> ### `server.timeout(Request, seconds)`
>
> Override the idle timeout for an individual request. Pass `0` to disable the timeout entirely for that request.
>
> ```ts
> const server = Bun.serve({
>   async fetch(req, server) {
>     // Give this request up to 60 seconds of inactivity instead of the default 10
>     server.timeout(req, 60);
>     await req.text();
>     return new Response("Done!");
>   },
> });
> ```
>
> ### `server.requestIP(Request)`
>
> Get client IP and port information:
>
> ```ts
> const server = Bun.serve({
>   fetch(req, server) {
>     const address = server.requestIP(req);
>     if (address) {
>       return new Response(`Client IP: ${address.address}, Port: ${address.port}`);
>     }
>     return new Response("Unknown client");
>   },
> });
> ```
> — *http-server.md:257*

### Metrics and Monitoring

Built-in `server.pendingRequests` and `server.pendingWebSockets` counters, plus `server.subscriberCount(topic)` for WebSocket pub/sub topics.

> ```ts
> const server = Bun.serve({
>   fetch(req, server) {
>     return new Response(
>       `Active requests: ${server.pendingRequests}\n` + `Active WebSockets: ${server.pendingWebSockets}`,
>     );
>   },
> });
> ```
>
> ### `server.subscriberCount(topic)`
>
> Get count of subscribers for a WebSocket topic:
>
> ```ts
> const server = Bun.serve({
>   fetch(req, server) {
>     const chatUsers = server.subscriberCount("chat");
>     return new Response(`${chatUsers} users in chat`);
>   },
>   websocket: {
>     message(ws) {
>       ws.subscribe("chat");
>     },
>   },
> });
> ```
> — *http-server.md:309*

### WebSocket Handler Interface

The `WebSocketHandler<T>` interface includes lifecycle methods (`open`, `message`, `close`, `ping`, `pong`, `drain`) and options for compression, backpressure, and idle timeout.

> ```ts
> interface WebSocketHandler<T = undefined> {
>   maxPayloadLength?: number;
>   backpressureLimit?: number;
>   closeOnBackpressureLimit?: boolean;
>   drain?(ws: ServerWebSocket<T>): void | Promise<void>;
>   idleTimeout?: number;
>   perMessageDeflate?: boolean | { compress?: WebSocketCompressor | boolean; decompress?: WebSocketCompressor | boolean };
>   sendPings?: boolean;
>   publishToSelf?: boolean;
>   open?(ws: ServerWebSocket<T>): void | Promise<void>;
>   message(ws: ServerWebSocket<T>, message: string | Buffer): void | Promise<void>;
>   close?(ws: ServerWebSocket<T>, code: number, reason: string): void | Promise<void>;
>   ping?(ws: ServerWebSocket<T>, data: Buffer): void | Promise<void>;
>   pong?(ws: ServerWebSocket<T>, data: Buffer): void | Promise<void>;
> }
> ```
> — *http-server.md:375*

### TLS Configuration

TLS accepts CA, cert, and key as strings, `Buffer`s, or `BunFile` references (or arrays of these). Additional options include DH params, passphrase, secure options, server name, and a low-memory mode.

> ```ts
> interface TLSOptions {
>   ca?: string | Buffer | BunFile | Array<string | Buffer | BunFile>;
>   cert?: string | Buffer | BunFile | Array<string | Buffer | BunFile>;
>   dhParamsFile?: string;
>   key?: string | Buffer | BunFile | Array<string | Buffer | BunFile>;
>   lowMemoryMode?: boolean;
>   passphrase?: string;
>   secureOptions?: number;
>   serverName?: string;
> }
> ```
> — *http-server.md:391*

### Performance

`Bun.serve` handles approximately 160,000 requests/sec on Linux versus approximately 64,000 for Node 16 — roughly 2.5x the throughput. <!-- TEMPORAL: verify currency — benchmark comparison references Node 16 -->

> The `Bun.serve` server can handle roughly 2.5x more requests per second than Node.js on Linux.
>
> | Runtime | Requests per second |
> |-|-|
> | Node 16 | ~64,000 |
> | Bun | ~160,000 |
> — *http-server.md:343*

---

## File I/O

### BunFile Lazy Loading

`Bun.file()` returns a `BunFile` object that lazily loads file contents. It can be passed directly as a route value in `Bun.serve` or consumed with `.text()`, `.json()`, or `.arrayBuffer()`.

> ```ts
> // Serve a file by lazily loading it into memory
> "/favicon.ico": Bun.file("./favicon.ico"),
> ```
> — *http-server.md:34*

### Standard Streams

`Bun.stdin`, `Bun.stdout`, and `Bun.stderr` provide stream-based access to standard I/O.

> | File I/O | `Bun.file`, `Bun.write`, `Bun.stdin`, `Bun.stdout`, `Bun.stderr` |
> — *bun-apis.md:24*

---

## SQLite (`bun:sqlite`)

### Database Creation

Databases can be opened from a file path, `:memory:`, in readonly mode, or with the `create` flag to auto-create missing files. Import attributes (`with { type: "sqlite" }`) provide an ES module-native alternative to the constructor.

> ```ts
> import { Database } from "bun:sqlite";
> const db = new Database("mydb.sqlite");
> ```
>
> To open an in-memory database:
>
> ```ts
> const db = new Database(":memory:");
> const db = new Database();
> const db = new Database("");
> ```
>
> To open in `readonly` mode:
>
> ```ts
> const db = new Database("mydb.sqlite", { readonly: true });
> ```
>
> To create the database if the file doesn't exist:
>
> ```ts
> const db = new Database("mydb.sqlite", { create: true });
> ```
> — *sqlite.md:33*

> ```ts
> import db from "./mydb.sqlite" with { type: "sqlite" };
>
> console.log(db.query("select * from users LIMIT 1").get());
> ```
> — *sqlite.md:84*

### Strict Mode

The `strict: true` constructor option throws on missing parameters and allows binding without the `$`, `:`, or `@` prefix. Default (non-strict) mode silently ignores missing parameters.

> ```ts
> const strict = new Database(":memory:", { strict: true });
>
> // throws error because of the typo:
> const query = strict.query("SELECT $message;").all({ messag: "Hello world" });
>
> const notStrict = new Database(":memory:");
> // does not throw error:
> notStrict.query("SELECT $message;").all({ messag: "Hello world" });
> ```
> — *sqlite.md:65*

### Query Execution Methods

Statements expose `.all()` (array of objects), `.get()` (first row), `.run()` (metadata with `lastInsertRowid` and `changes`), `.as(Class)` (ORM mapping), `.iterate()`, `.values()`, and `.finalize()`.

> ```ts
> const query = db.query(`select $message;`);
> query.all({ $message: "Hello world" });
> // [{ message: "Hello world" }]
> ```
>
> ```ts
> const query = db.query(`create table foo;`);
> query.run();
> // { lastInsertRowid: 0, changes: 0 }
> ```
> — *sqlite.md:230*

### WAL Mode

WAL (write-ahead log) mode is broadly recommended for typical applications with concurrent readers. Enable at application startup with a single pragma.

> ```ts
> db.run("PRAGMA journal_mode = WAL;");
> ```
>
> In WAL mode, writes to the database are written directly to a separate file called the "WAL file" (`-wal`). A shared-memory index file (`-shm`) is also created for read coordination.
> — *sqlite.md:176*

### Transactions

`db.transaction()` wraps query logic in atomic begin/commit/rollback blocks. Inner transaction calls become savepoints. Variants `deferred`, `immediate`, and `exclusive` are available.

> ```ts
> const insertCat = db.prepare("INSERT INTO cats (name) VALUES ($name)");
> const insertCats = db.transaction(cats => {
>   for (const cat of cats) insertCat.run(cat);
> });
> ```
>
> The driver will automatically `begin` a transaction when `insertCats` is called and `commit` it when the wrapped function returns. If an exception is thrown, the transaction will be rolled back.
>
> **Nested transactions** — Transaction functions can be called from inside other transaction functions. When doing so, the inner transaction becomes a savepoint.
> — *sqlite.md:382*

### BigInt / Safe Integers

The `safeIntegers: true` constructor option returns integers as `bigint` instead of `number`. When enabled, binding a `bigint` exceeding 64 bits throws. When disabled (default), integers beyond 53 bits are truncated.

> ```ts
> const db = new Database(":memory:", { safeIntegers: true });
> const query = db.query(`SELECT ${BigInt(Number.MAX_SAFE_INTEGER) + 102n} as max_int`);
> const result = query.get();
> console.log(result.max_int); // 9007199254741093n
> ```
> — *sqlite.md:363*

### Performance

`bun:sqlite` is roughly 3–6x faster than `better-sqlite3` and 8–9x faster than `deno.land/x/sqlite` on read queries against the Northwind Traders dataset.

> The `bun:sqlite` module is roughly 3-6x faster than `better-sqlite3` and 8-9x faster than `deno.land/x/sqlite` for read queries. Each driver was benchmarked against the [Northwind Traders](https://github.com/jpwhite3/northwind-SQLite3/blob/46d5f8a64f396f87cd374d1600dbf521523980e8/Northwind_large.sqlite.zip) dataset.
> — *sqlite.md:29*

---

## FFI (`bun:ffi`)

### Loading Native Libraries with `dlopen`

`dlopen()` loads a shared library and declares symbol signatures using `FFIType` definitions for arguments and return types. The `suffix` export resolves to the platform-appropriate extension (`dylib`, `so`, or `dll`).

> ```ts
> import { dlopen, FFIType, suffix } from "bun:ffi";
>
> // `suffix` is either "dylib", "so", or "dll" depending on the platform
> const path = `libsqlite3.${suffix}`;
>
> const {
>   symbols: {
>     sqlite3_libversion,
>   },
> } = dlopen(
>   path, // a library name or file path
>   {
>     sqlite3_libversion: {
>       args: [],
>       returns: FFIType.cstring,
>     },
>   },
> );
>
> console.log(`SQLite 3 version: ${sqlite3_libversion()}`);
> ```
> — *ffi.md:11*

### FFIType Reference

`FFIType` covers all primitive C integer and float types, string types (`buffer`, `cstring`), pointer types (`ptr`), function pointers (`function`/`fn`/`callback`), and Node-API types (`napi_env`, `napi_value`).

> | `FFIType` | C Type | Aliases |
> |-|-|-|
> | buffer | `char*` | |
> | cstring | `char*` | |
> | function | `(void*)(*)()` | `fn`, `callback` |
> | ptr | `void*` | `pointer`, `void*`, `char*` |
> | i8 | `int8_t` | `int8_t` |
> | i16 | `int16_t` | `int16_t` |
> | i32 | `int32_t` | `int32_t`, `int` |
> | i64 | `int64_t` | `int64_t` |
> | i64_fast | `int64_t` | |
> | u8 | `uint8_t` | `uint8_t` |
> | u16 | `uint16_t` | `uint16_t` |
> | u32 | `uint32_t` | `uint32_t` |
> | u64 | `uint64_t` | `uint64_t` |
> | u64_fast | `uint64_t` | |
> | f32 | `float` | `float` |
> | f64 | `double` | `double` |
> | bool | `bool` | |
> | char | `char` | |
> | napi_env | `napi_env` | |
> | napi_value | `napi_value` | |
> — *ffi.md:95*

### CString

`CString` extends JavaScript's built-in `String` with null-terminated string support and optional `byteOffset`/`byteLength` for length-bounded conversion from a raw pointer.

> ```ts
> class CString extends String {
>   constructor(ptr: number, byteOffset?: number, byteLength?: number): string;
>   ptr: number;
>   byteOffset?: number;
>   byteLength?: number;
> }
> ```
>
> To convert from a null-terminated string pointer to a JavaScript string:
>
> ```ts
> const myString = new CString(ptr);
> ```
>
> To convert from a pointer with a known length to a JavaScript string:
>
> ```ts
> const myString = new CString(ptr, 0, byteLength);
> ```
> — *ffi.md:138*

### CFunction and `linkSymbols`

`CFunction` wraps an existing function pointer for calling from JavaScript. `linkSymbols()` declares multiple function pointers at once — useful when symbols are already loaded (e.g. via Node-API).

> ```ts
> import { CFunction } from "bun:ffi";
>
> const getVersion = new CFunction({
>   returns: "cstring",
>   args: [],
>   ptr: myNativeLibraryGetVersion,
> });
> getVersion();
> ```
> — *ffi.md:165*

### JSCallback

`JSCallback` creates JavaScript functions that can be passed as callbacks to C/FFI code. Thread-safe callbacks are supported via the experimental `threadsafe` parameter. Call `.close()` when done to free memory.

> ```ts
> const searchIterator = new JSCallback((ptr, length) => /hello/.test(new CString(ptr, length)), {
>   returns: "bool",
>   args: ["ptr", "usize"],
> });
> ```
>
> When you're done with a JSCallback, you should call `close()` to free the memory.
>
> ### Experimental thread-safe callbacks
>
> `JSCallback` has experimental support for thread-safe callbacks. This will be needed if you pass a callback function into a different thread from its instantiation context. You can enable it with the optional `threadsafe` parameter.
> — *ffi.md:212*

### Pointer Representation and Conversion

Bun represents pointers as JavaScript `number` (not `BigInt`) to avoid allocation overhead. 64-bit addressable space fits within JavaScript's 53-bit mantissa. Use `ptr()` to get a pointer from a `TypedArray`, and `toArrayBuffer()` to convert a pointer back.

> Bun represents pointers as a `number` in JavaScript.
>
> 64-bit processors support up to 52 bits of addressable space. JavaScript numbers support 53 bits of usable space, so that leaves us with about 11 bits of extra space.
>
> **Why not `BigInt`?** `BigInt` is slower. JavaScript engines allocate a separate `BigInt` which means they can't fit into a regular JavaScript value.
>
> ```ts
> import { ptr } from "bun:ffi";
> let myTypedArray = new Uint8Array(32);
> const myPtr = ptr(myTypedArray);
> ```
>
> ```ts
> // toArrayBuffer accepts a `byteOffset` and `byteLength`
> myTypedArray = new Uint8Array(toArrayBuffer(myPtr, 0, 32), 0, 32);
> ```
> — *ffi.md:265*

### `read` Functions

The `read` namespace provides fast typed reads from a pointer without creating a `DataView` or `ArrayBuffer`. Functions mirror the `FFIType` names (`read.u8`, `read.i32`, `read.f64`, `read.ptr`, etc.).

> ```ts
> import { read } from "bun:ffi";
>
> console.log(
>   read.u8(myPtr, 0),
>   read.u8(myPtr, 1),
>   read.u8(myPtr, 2),
>   read.u8(myPtr, 3),
> );
> ```
>
> The `read` function behaves similarly to `DataView`, but it's usually faster because it doesn't need to create a `DataView` or `ArrayBuffer`.
> — *ffi.md:307*

### Performance

`bun:ffi` is roughly 2–6x faster than Node.js FFI via Node-API. The performance gain comes from JIT-compiled C bindings generated using embedded TinyCC.

> According to our benchmark, `bun:ffi` is roughly 2-6x faster than Node.js FFI via `Node-API`.
>
> Bun generates & just-in-time compiles C bindings that efficiently convert values between JavaScript types and native types. To compile C, Bun embeds [TinyCC](https://github.com/TinyCC/tinycc), a small and fast C compiler.
> — *ffi.md:37*

---

## Test Runner (`bun:test`)

### Basic Usage and Feature Set

`bun test` is a built-in Jest-compatible test runner supporting TypeScript, JSX, lifecycle hooks, snapshots, UI/DOM testing, watch mode, and script preloading.

> Bun ships with a fast, built-in, Jest-compatible test runner. Tests are executed with the Bun runtime, and support the following features.
>
> * TypeScript and JSX
> * Lifecycle hooks
> * Snapshot testing
> * UI & DOM testing
> * Watch mode with `--watch`
> * Script pre-loading with `--preload`
>
> Bun aims for compatibility with Jest, but not everything is implemented.
>
> ```ts
> import { expect, test } from "bun:test";
>
> test("2 + 2", () => {
>   expect(2 + 2).toBe(4);
> });
> ```
> — *test-runner.md:3*

### Test Discovery

The runner recursively searches the working directory for files matching four pattern families.

> * `*.test.{js|jsx|ts|tsx}`
> * `*_test.{js|jsx|ts|tsx}`
> * `*.spec.{js|jsx|ts|tsx}`
> * `*_spec.{js|jsx|ts|tsx}`
> — *test-runner.md:32*

### Filtering

File-level filtering uses positional arguments; test-name filtering uses `-t` / `--test-name-pattern` with a regex. Glob patterns in positional arguments are not yet supported.

> ```bash
> bun test <filter> <filter> ...
> ```
>
> To filter by *test name*, use the `-t`/`--test-name-pattern` flag.
>
> ```sh
> # run all tests or test suites with "addition" in the name
> bun test --test-name-pattern addition
> ```
> — *test-runner.md:32*

### Lifecycle Hooks

`beforeAll`, `beforeEach`, `afterEach`, `afterAll` are supported. Hooks may live in test files or in separate files loaded via `--preload`.

> | Hook | Description |
> |-|-|
> | `beforeAll` | Runs once before all tests. |
> | `beforeEach` | Runs before each test. |
> | `afterEach` | Runs after each test. |
> | `afterAll` | Runs once after all tests. |
> — *test-runner.md:248*

### Mocking

`mock()` (from `bun:test`) and `jest.fn()` both create call-tracking mock functions. `toHaveBeenCalled` and `toHaveBeenCalledTimes` assertions are available.

> ```ts
> import { test, expect, mock } from "bun:test";
> const random = mock(() => Math.random());
>
> test("random", () => {
>   const val = random();
>   expect(val).toBeGreaterThan(0);
>   expect(random).toHaveBeenCalled();
>   expect(random).toHaveBeenCalledTimes(1);
> });
> ```
> — *test-runner.md:265*

### Snapshot Testing

`toMatchSnapshot()` captures output. Pass `--update-snapshots` to regenerate stored snapshots.

> ```ts
> test("snapshot", () => {
>   expect({ a: 1 }).toMatchSnapshot();
> });
> ```
>
> ```sh
> bun test --update-snapshots
> ```
> — *test-runner.md:288*

### Concurrent Execution

By default, tests within a file run sequentially. `--concurrent` runs all tests in parallel (default max-concurrency: 20); `--max-concurrency` caps parallelism. `test.concurrent()` and `test.serial()` override at the individual test level.

> ```sh
> bun test --concurrent
> bun test --concurrent --max-concurrency 4
> ```
> — *test-runner.md:101*

### Retry and Flake Detection

`--retry N` retries each failed test up to N times. `--rerun-each N` runs every test N times, useful for detecting non-deterministic failures. Per-test `{ retry: N }` options override the global flag. Both can be configured in `bunfig.toml`.

> ```sh
> bun test --retry 3
> bun test --rerun-each 100
> ```
>
> ```toml
> [test]
> retry = 3
> ```
> — *test-runner.md:180*

### Timeout and Bail

Default per-test timeout is 5000 ms. `--bail` exits after N failures (default 1 when the flag is present). `--randomize` runs tests in random order; `--seed` makes randomization reproducible.

> ```bash
> # default value is 5000
> bun test --timeout 20
>
> # bail after 1 failure
> bun test --bail
>
> # bail after 10 failures
> bun test --bail=10
> ```
> — *test-runner.md:92*

### CI Integration

GitHub Actions annotations are emitted automatically when `CI=true` (no configuration needed). JUnit XML output is available via `--reporter=junit --reporter-outfile`.

> `bun test` automatically detects if it's running inside GitHub Actions and will emit GitHub Actions annotations to the console directly. No configuration is needed, other than installing `bun` in the workflow and running `bun test`.
>
> ```sh
> bun test --reporter=junit --reporter-outfile=./bun.xml
> ```
> — *test-runner.md:60*

### Full CLI Flag Reference

> ### Execution Control
>
> * `--timeout <number>` - Set per-test timeout in milliseconds (default 5000)
> * `--rerun-each <number>` - Re-run each test file NUMBER times
> * `--retry <number>` - Default retry count for failed tests
> * `--concurrent` - Treat all tests as `test.concurrent()` tests
> * `--randomize` - Run tests in random order
> * `--seed <number>` - Set random seed for test randomization
> * `--bail <number>` - Exit after NUMBER failures (default 1)
> — *test-runner.md:344*

### Performance

> Bun's test runner is fast. It can run 266 React SSR tests faster than Jest can print its version number.
> — *test-runner.md:314*

---

## Cross-References

| From | To | Relationship |
|-|-|-|
| bun-apis.md | http-server.md | API reference documents `Bun.serve` HTTP functionality |
| bun-apis.md | sqlite.md | API reference lists `bun:sqlite` module |
| bun-apis.md | ffi.md | API reference lists `bun:ffi` module |
| bun-apis.md | test-runner.md | API reference lists `bun:test` module |
| http-server.md | sqlite.md | HTTP server examples can use SQLite for persistence via `bun:sqlite` |
| ffi.md | sqlite.md | FFI example calls `libsqlite3` natively; `bun:sqlite` is the higher-level abstraction |

---

## Gaps and Open Questions

The following gaps were identified from scout extraction. Items are deduplicated and grouped by type.

### Incomplete Documentation

- No detailed WebSocket API reference or `upgrade()` method documentation for server-side WebSocket implementation. <!-- TODO: verify -->
- No documentation on watch mode behavior with file changes affecting test discovery. <!-- TODO: verify -->
- AI agent integration flags (`CLAUDECODE`, `REPLIT`, `AGENT`) are mentioned but the detection mechanism is not explained. <!-- TODO: verify -->
- Database serialization/deserialization (`serialize()`, `deserialize()`) are mentioned but not explained in context of use cases. <!-- TODO: verify -->
- No documentation on `.prepare()` vs `.query()` differences for statement caching behavior. <!-- TODO: verify -->
- FFI memory management section lacks examples of `FinalizationRegistry` usage from JavaScript. <!-- TODO: verify -->
- Limited documentation on pointer alignment requirements for custom struct types in FFI. <!-- TODO: verify -->

### Missing Examples

- No examples of `export default` syntax for HTTP servers and when to use it versus `Bun.serve()`. <!-- TODO: verify -->
- No examples of `Bun.file` integration with other file I/O operations like `Bun.write` or streaming. <!-- TODO: verify -->
- Test runner DOM testing compatibility is mentioned but no usage examples are provided for HappyDOM, DOM Testing Library, or React Testing Library. <!-- TODO: verify -->

---

## Additional Notes

The following findings are low-to-medium relevance and do not fit neatly into the categories above, but are included here for auditor completeness.

- **Package management** — `bun install` is Bun's native package manager supporting dependency management and workspaces. (*bun-apis.md:1*)
- **Bundler** — `Bun.build` provides bundling and transpilation with HTML imports support. (*bun-apis.md:23*)
- **bunfig.toml** — The `[test]` section of `bunfig.toml` supports at minimum the `retry` option for test configuration. (*test-runner.md:195*)
- **Jest compatibility note** — The scout notes that `bun:test` aims for Jest compatibility but that not everything is implemented. The exact list of unimplemented features was not present in extracted sources. (*test-runner.md:14*) <!-- TODO: verify what Jest APIs are missing -->
