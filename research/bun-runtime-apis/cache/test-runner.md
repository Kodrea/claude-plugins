# Bun Test Runner

> Bun's fast, built-in, Jest-compatible test runner with TypeScript support, lifecycle hooks, mocking, and watch mode

Bun ships with a fast, built-in, Jest-compatible test runner. Tests are executed with the Bun runtime, and support the following features.

* TypeScript and JSX
* Lifecycle hooks
* Snapshot testing
* UI & DOM testing
* Watch mode with `--watch`
* Script pre-loading with `--preload`

Bun aims for compatibility with Jest, but not everything is implemented.

## Run tests

```bash
bun test
```

Tests are written in JavaScript or TypeScript with a Jest-like API.

```ts
import { expect, test } from "bun:test";

test("2 + 2", () => {
  expect(2 + 2).toBe(4);
});
```

The runner recursively searches the working directory for files that match the following patterns:

* `*.test.{js|jsx|ts|tsx}`
* `*_test.{js|jsx|ts|tsx}`
* `*.spec.{js|jsx|ts|tsx}`
* `*_spec.{js|jsx|ts|tsx}`

You can filter the set of *test files* to run by passing additional positional arguments to `bun test`. Any test file with a path that matches one of the filters will run. Commonly, these filters will be file or directory names; glob patterns are not yet supported.

```bash
bun test <filter> <filter> ...
```

To filter by *test name*, use the `-t`/`--test-name-pattern` flag.

```sh
# run all tests or test suites with "addition" in the name
bun test --test-name-pattern addition
```

To run a specific file in the test runner, make sure the path starts with `./` or `/` to distinguish it from a filter name.

```bash
bun test ./test/specific-file.test.ts
```

The test runner runs all tests in a single process. It loads all `--preload` scripts, then runs all tests. If a test fails, the test runner will exit with a non-zero exit code.

## CI/CD integration

### GitHub Actions

`bun test` automatically detects if it's running inside GitHub Actions and will emit GitHub Actions annotations to the console directly. No configuration is needed, other than installing `bun` in the workflow and running `bun test`.

```yaml
jobs:
  build:
    name: build-app
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Install bun
        uses: oven-sh/setup-bun@v2
      - name: Install dependencies
        run: bun install
      - name: Run tests
        run: bun test
```

### JUnit XML reports (GitLab, etc.)

To use `bun test` with a JUnit XML reporter, you can use the `--reporter=junit` in combination with `--reporter-outfile`.

```sh
bun test --reporter=junit --reporter-outfile=./bun.xml
```

This will continue to output to stdout/stderr as usual, and also write a JUnit XML report to the given path at the very end of the test run.

## Timeouts

Use the `--timeout` flag to specify a *per-test* timeout in milliseconds. If a test times out, it will be marked as failed. The default value is `5000`.

```bash
# default value is 5000
bun test --timeout 20
```

## Concurrent test execution

By default, Bun runs all tests sequentially within each test file. You can enable concurrent execution to run async tests in parallel.

### `--concurrent` flag

Use the `--concurrent` flag to run all tests concurrently within their respective files:

```sh
bun test --concurrent
```

When this flag is enabled, all tests will run in parallel unless explicitly marked with `test.serial`.

### `--max-concurrency` flag

Control the maximum number of tests running simultaneously with the `--max-concurrency` flag:

```sh
# Limit to 4 concurrent tests
bun test --concurrent --max-concurrency 4

# Default: 20
bun test --concurrent
```

### `test.concurrent`

Mark individual tests to run concurrently, even when the `--concurrent` flag is not used:

```ts
import { test, expect } from "bun:test";

// These tests run in parallel with each other
test.concurrent("concurrent test 1", async () => {
  await fetch("/api/endpoint1");
  expect(true).toBe(true);
});

test.concurrent("concurrent test 2", async () => {
  await fetch("/api/endpoint2");
  expect(true).toBe(true);
});

// This test runs sequentially
test("sequential test", () => {
  expect(1 + 1).toBe(2);
});
```

### `test.serial`

Force tests to run sequentially, even when the `--concurrent` flag is enabled:

```ts
import { test, expect } from "bun:test";

let sharedState = 0;

test.serial("first serial test", () => {
  sharedState = 1;
  expect(sharedState).toBe(1);
});

test.serial("second serial test", () => {
  expect(sharedState).toBe(1);
  sharedState = 2;
});

test("independent test", () => {
  expect(true).toBe(true);
});

// Chaining test qualifiers
test.failing.each([1, 2, 3])("chained qualifiers %d", input => {
  expect(input).toBe(0);
});
```

## Retry failed tests

Use the `--retry` flag to automatically retry failed tests up to a given number of times. If a test fails and then passes on a subsequent attempt, it is reported as passing.

```sh
bun test --retry 3
```

Per-test `{ retry: N }` overrides the global `--retry` value:

```ts
test("uses global retry", () => { /* ... */ });
test("custom retry", { retry: 1 }, () => { /* ... */ });
```

You can also set this in `bunfig.toml`:

```toml
[test]
retry = 3
```

## Rerun tests

Use the `--rerun-each` flag to run each test multiple times. This is useful for detecting flaky or non-deterministic test failures.

```sh
bun test --rerun-each 100
```

## Randomize test execution order

Use the `--randomize` flag to run tests in a random order. This helps detect tests that depend on shared state or execution order.

```sh
bun test --randomize
```

### Reproducible random order with `--seed`

Use the `--seed` flag to specify a seed for the randomization. This allows you to reproduce the same test order when debugging order-dependent failures.

```sh
bun test --seed 123456
```

The `--seed` flag implies `--randomize`, so you don't need to specify both.

## Bail out with `--bail`

Use the `--bail` flag to abort the test run early after a pre-determined number of test failures. By default Bun will run all tests and report all failures.

```sh
# bail after 1 failure
bun test --bail

# bail after 10 failures
bun test --bail=10
```

## Watch mode

Similar to `bun run`, you can pass the `--watch` flag to `bun test` to watch for changes and re-run tests.

```bash
bun test --watch
```

## Lifecycle hooks

Bun supports the following lifecycle hooks:

| Hook         | Description                 |
| ------------ | --------------------------- |
| `beforeAll`  | Runs once before all tests. |
| `beforeEach` | Runs before each test.      |
| `afterEach`  | Runs after each test.       |
| `afterAll`   | Runs once after all tests.  |

These hooks can be defined inside test files, or in a separate file that is preloaded with the `--preload` flag.

```sh
bun test --preload ./setup.ts
```

## Mocks

Create mock functions with the `mock` function.

```ts
import { test, expect, mock } from "bun:test";
const random = mock(() => Math.random());

test("random", () => {
  const val = random();
  expect(val).toBeGreaterThan(0);
  expect(random).toHaveBeenCalled();
  expect(random).toHaveBeenCalledTimes(1);
});
```

Alternatively, you can use `jest.fn()`, it behaves identically.

```ts
import { test, expect, jest } from "bun:test";
const random = jest.fn(() => Math.random());
```

## Snapshot testing

Snapshots are supported by `bun test`.

```ts
import { test, expect } from "bun:test";

test("snapshot", () => {
  expect({ a: 1 }).toMatchSnapshot();
});
```

To update snapshots, use the `--update-snapshots` flag.

```sh
bun test --update-snapshots
```

## UI & DOM testing

Bun is compatible with popular UI testing libraries:

* HappyDOM
* DOM Testing Library
* React Testing Library

## Performance

Bun's test runner is fast. It can run 266 React SSR tests faster than Jest can print its version number.

## AI Agent Integration

When using Bun's test runner with AI coding assistants, you can enable quieter output to improve readability and reduce context noise.

### Environment Variables

Set any of the following environment variables to enable AI-friendly output:

* `CLAUDECODE=1` - For Claude Code
* `REPL_ID=1` - For Replit
* `AGENT=1` - Generic AI agent flag

### Behavior

When an AI agent environment is detected:

* Only test failures are displayed in detail
* Passing, skipped, and todo test indicators are hidden
* Summary statistics remain intact

## CLI Usage

```bash
bun test <patterns>
```

### Execution Control

* `--timeout <number>` - Set per-test timeout in milliseconds (default 5000)
* `--rerun-each <number>` - Re-run each test file NUMBER times
* `--retry <number>` - Default retry count for failed tests
* `--concurrent` - Treat all tests as `test.concurrent()` tests
* `--randomize` - Run tests in random order
* `--seed <number>` - Set random seed for test randomization
* `--bail <number>` - Exit after NUMBER failures (default 1)
* `--max-concurrency <number>` - Maximum concurrent tests (default 20)

### Test Filtering

* `--todo` - Include `test.todo()` tests
* `--test-name-pattern <string>` / `-t` - Filter by test name regex

### Reporting

* `--reporter <string>` - Format: `junit` (requires --reporter-outfile), `dots`
* `--reporter-outfile <string>` - Output file for reporter
* `--dots` - Shorthand for --reporter=dots

### Coverage

* `--coverage` - Generate a coverage profile
* `--coverage-reporter <string>` - Report in `text` and/or `lcov` (default: text)
* `--coverage-dir <string>` - Directory for coverage files (default: coverage)

### Snapshots

* `--update-snapshots` / `-u` - Update snapshot files
