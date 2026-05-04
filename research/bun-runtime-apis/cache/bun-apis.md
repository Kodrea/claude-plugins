# Bun APIs

> Overview of Bun's native APIs available on the Bun global object and built-in modules

Bun implements a set of native APIs on the `Bun` global object and through a number of built-in modules. These APIs are heavily optimized and represent the canonical "Bun-native" way to implement some common functionality.

Bun strives to implement standard Web APIs wherever possible. Bun introduces new APIs primarily for server-side tasks where no standard exists, such as file I/O and starting an HTTP server. In these cases, Bun's approach still builds atop standard APIs like `Blob`, `URL`, and `Request`.

```ts
Bun.serve({
  fetch(req: Request) {
    return new Response("Success!");
  },
});
```

## API Reference Table

| Topic | APIs |
|-|-|
| HTTP Server | `Bun.serve` |
| Shell | `$` |
| Bundler | `Bun.build` |
| File I/O | `Bun.file`, `Bun.write`, `Bun.stdin`, `Bun.stdout`, `Bun.stderr` |
| Child Processes | `Bun.spawn`, `Bun.spawnSync` |
| TCP Sockets | `Bun.listen`, `Bun.connect` |
| UDP Sockets | `Bun.udpSocket` |
| WebSockets | `new WebSocket()` (client), `Bun.serve` (server) |
| Transpiler | `Bun.Transpiler` |
| Routing | `Bun.FileSystemRouter` |
| Streaming HTML | `HTMLRewriter` |
| Hashing | `Bun.password`, `Bun.hash`, `Bun.CryptoHasher`, `Bun.sha` |
| CSRF Protection | `Bun.CSRF.generate`, `Bun.CSRF.verify` |
| SQLite | `bun:sqlite` |
| PostgreSQL Client | `Bun.SQL`, `Bun.sql` |
| Redis (Valkey) Client | `Bun.RedisClient`, `Bun.redis` |
| FFI (Foreign Function Interface) | `bun:ffi` |
| DNS | `Bun.dns.lookup`, `Bun.dns.prefetch`, `Bun.dns.getCacheStats` |
| Testing | `bun:test` |
| Workers | `new Worker()` |
| Module Loaders | `Bun.plugin` |
| Glob | `Bun.Glob` |
| Cookies | `Bun.Cookie`, `Bun.CookieMap` |
| Node-API | `Node-API` |
| `import.meta` | `import.meta` |
| Utilities | `Bun.version`, `Bun.revision`, `Bun.env`, `Bun.main` |
| Sleep & Timing | `Bun.sleep()`, `Bun.sleepSync()`, `Bun.nanoseconds()` |
| Random & UUID | `Bun.randomUUIDv7()` |
| System & Environment | `Bun.which()` |
| Comparison & Inspection | `Bun.peek()`, `Bun.deepEquals()`, `Bun.deepMatch`, `Bun.inspect()` |
| String & Text Processing | `Bun.escapeHTML()`, `Bun.stringWidth()`, `Bun.indexOfLine` |
| URL & Path Utilities | `Bun.fileURLToPath()`, `Bun.pathToFileURL()` |
| Compression | `Bun.gzipSync()`, `Bun.gunzipSync()`, `Bun.deflateSync()`, `Bun.inflateSync()`, `Bun.zstdCompressSync()`, `Bun.zstdDecompressSync()`, `Bun.zstdCompress()`, `Bun.zstdDecompress()` |
| Stream Processing | `Bun.readableStreamTo*()`, `Bun.readableStreamToBytes()`, `Bun.readableStreamToBlob()`, `Bun.readableStreamToFormData()`, `Bun.readableStreamToJSON()`, `Bun.readableStreamToArray()` |
| Memory & Buffer Management | `Bun.ArrayBufferSink`, `Bun.allocUnsafe`, `Bun.concatArrayBuffers` |
| Module Resolution | `Bun.resolveSync()` |
| Parsing & Formatting | `Bun.semver`, `Bun.TOML.parse`, `Bun.markdown`, `Bun.color` |
| Low-level / Internals | `Bun.mmap`, `Bun.gc`, `Bun.generateHeapSnapshot`, `bun:jsc` |
