# Permission Syntax Reference

Complete syntax guide for all Claude Code permission rule types.

---

## Bash Command Permissions

**Format:** `Bash(command with args)`

### Rules
- Wildcard `*` ONLY supported at END of pattern
- Matches via prefix matching
- Include arguments in the pattern for specificity
- Case-sensitive matching

### Examples

**Exact matching:**
```json
"Bash(npm run test:unit)"      // Only matches this exact command
"Bash(git status)"              // Only "git status"
"Bash(docker compose up)"       // Exact match including args
```

**Wildcard patterns:**
```json
"Bash(npm run test:*)"          // Matches: test:unit, test:integration, test:e2e
"Bash(git *)"                   // Matches ALL git commands
"Bash(npm *)"                   // Matches ALL npm commands
"Bash(docker compose *)"        // Matches docker compose with any subcommand
```

**Specific with arguments:**
```json
"Bash(npm install lodash)"      // Only this exact install command
"Bash(git commit -m *)"         // git commit -m with any message
"Bash(echo *)"                  // All echo commands
```

### Common Patterns

**Safe development commands:**
```json
"allow": [
  "Bash(npm run test:*)",
  "Bash(npm run build)",
  "Bash(npm run dev)",
  "Bash(npm run lint)",
  "Bash(git status)",
  "Bash(git diff)",
  "Bash(git log)",
  "Bash(git branch)",
  "Bash(docker compose up)",
  "Bash(docker compose down)"
]
```

**Require confirmation for dangerous operations:**
```json
"ask": [
  "Bash(npm install *)",
  "Bash(git push *)",
  "Bash(git commit *)",
  "Bash(rm *)",
  "Bash(docker *)",
  "Bash(make clean)"
]
```

**Block destructive commands:**
```json
"deny": [
  "Bash(rm -rf *)",
  "Bash(rm -fr *)",
  "Bash(sudo *)",
  "Bash(curl *)",           // Prevent arbitrary downloads
  "Bash(wget *)",           // Prevent arbitrary downloads
  "Bash(chmod 777 *)",
  "Bash(mkfs.*)"
]
```

---

## WebFetch Permissions

**Format:** `WebFetch(URL_PATTERN)` or `WebFetch(domain:DOMAIN)`

### Rules
- URL format: Full URLs with path wildcards
- Domain format: Any URL on specified domain
- Protocol (https://) required in URL format
- Path wildcards supported with `*`

### URL Pattern Examples

**Full URLs with paths:**
```json
"WebFetch(https://docs.anthropic.com/*)"           // All Anthropic docs
"WebFetch(https://api.github.com/repos/*)"         // GitHub API
"WebFetch(https://registry.npmjs.org/*)"           // NPM registry
"WebFetch(https://pypi.org/pypi/*/json)"          // PyPI with pattern
```

**Specific endpoints:**
```json
"WebFetch(https://api.company.com/v1/*)"           // API v1 only
"WebFetch(https://docs.company.com/internal/*)"    // Internal docs
"WebFetch(https://status.company.com/api/*)"       // Status API
```

### Domain Pattern Examples

**Domain-wide access:**
```json
"WebFetch(domain:anthropic.com)"        // Any anthropic.com URL
"WebFetch(domain:github.com)"           // Any github.com URL
"WebFetch(domain:stackoverflow.com)"    // Any stackoverflow.com URL
```

**Subdomains:**
```json
"WebFetch(domain:docs.anthropic.com)"   // Only docs subdomain
"WebFetch(domain:api.github.com)"       // Only API subdomain
```

### Common Patterns

**Documentation sites:**
```json
"allow": [
  "WebFetch(https://docs.anthropic.com/*)",
  "WebFetch(https://docs.claude.com/*)",
  "WebFetch(https://developer.mozilla.org/*)",
  "WebFetch(https://devdocs.io/*)",
  "WebFetch(https://stackoverflow.com/*)",
  "WebFetch(domain:en.wikipedia.org)"
]
```

**Company resources:**
```json
"allow": [
  "WebFetch(https://docs.company.com/*)",
  "WebFetch(https://wiki.company.com/*)",
  "WebFetch(domain:company.internal)",
  "WebFetch(https://api.company.com/v1/*)"
]
```

**Package registries:**
```json
"allow": [
  "WebFetch(https://registry.npmjs.org/*)",
  "WebFetch(https://pypi.org/*)",
  "WebFetch(https://crates.io/*)",
  "WebFetch(https://rubygems.org/*)"
]
```

**Block external code execution:**
```json
"deny": [
  "WebFetch(domain:pastebin.com)",
  "WebFetch(domain:gist.github.com)",
  "WebFetch(domain:raw.githubusercontent.com)",
  "WebFetch(domain:cdn.jsdelivr.net)"
]
```

---

## File Operation Permissions (Read/Edit/Write)

**Path Types:**
- `//path` - Absolute filesystem path (starts from root)
- `~/path` - Home directory relative
- `/path` - Relative to settings.json location
- `path` or `./path` - Current working directory relative

**Wildcards:**
- `*` - Matches files in single directory level
- `**` - Recursive directory matching (all subdirectories)
- `*.ext` - File extension matching
- `prefix*` - Filename prefix matching

### Relative to settings.json (`/path`)

**Project structure:**
```json
"allow": [
  "Edit(/src/**)",              // All source files
  "Edit(/docs/**)",             // All documentation
  "Edit(/tests/**)",            // All test files
  "Read(/config/**)",           // Read-only config
  "Write(/dist/**)",            // Build output
  "Write(/coverage/**)"         // Test coverage reports
]
```

**Specific files:**
```json
"allow": [
  "Edit(/README.md)",
  "Edit(/package.json)",
  "Read(/tsconfig.json)"
]
```

**Nested patterns:**
```json
"allow": [
  "Edit(/src/components/**)",   // Component files
  "Edit(/src/utils/**)",        // Utility files
  "Read(/src/types/**)"         // Type definitions (read-only)
],
"deny": [
  "Edit(/src/secrets/**)",      // Block secrets directory
  "Edit(/src/api/keys/**)"      // Block API keys
]
```

### Home Directory (`~/path`)

**User configurations:**
```json
"allow": [
  "Read(~/.zshrc)",
  "Read(~/.bashrc)",
  "Read(~/.gitconfig)",
  "Edit(~/projects/**)"
]
```

**Block sensitive files:**
```json
"deny": [
  "Edit(~/.ssh/**)",
  "Read(~/.aws/credentials)",
  "Read(~/.aws/config)",
  "Edit(~/.gnupg/**)",
  "Read(~/.netrc)",
  "Edit(~/.docker/config.json)"
]
```

### Absolute Paths (`//path`)

**System files:**
```json
"ask": [
  "Edit(//etc/hosts)",
  "Read(//var/log/**)"
]
```

**Temporary files:**
```json
"allow": [
  "Write(//tmp/**)",
  "Edit(//tmp/scratch/**)"
]
```

**Block critical system files:**
```json
"deny": [
  "Edit(//etc/passwd)",
  "Edit(//etc/shadow)",
  "Edit(//etc/sudoers)",
  "Edit(//boot/**)",
  "Write(//dev/**)"
]
```

### Current Working Directory (`./path` or `path`)

**Project root files:**
```json
"allow": [
  "Edit(./**)",                 // All files in cwd
  "Edit(./README.md)",
  "Read(./package.json)"
]
```

**Block sensitive patterns:**
```json
"deny": [
  "Edit(.env*)",                // .env, .env.local, .env.production
  "Read(secrets.*)",            // secrets.json, secrets.yaml
  "Edit(credentials.*)"
]
```

### Wildcard Patterns

**Extension matching:**
```json
"allow": [
  "Edit(/src/**/*.ts)",         // Only TypeScript files
  "Edit(/docs/**/*.md)",        // Only Markdown files
  "Read(/config/**/*.json)"     // Only JSON config files
]
```

**Prefix matching:**
```json
"allow": [
  "Edit(/temp*)",               // temp, temp-file, template
  "Read(/backup*)"              // backup, backup-2024, backups
]
```

**Complex patterns:**
```json
"allow": [
  "Edit(/src/**/test-*.ts)",    // Test files in any subdirectory
  "Edit(/scripts/**/*.sh)",     // Shell scripts anywhere in scripts/
  "Read(/docs/**/api-*.md)"     // API docs in any subdirectory
]
```

---

## MCP Tool Permissions

**Format:** `mcp__servername__toolname` or `mcp__servername`

### Rules
- No wildcards supported
- Must use exact server and tool names
- Case-sensitive
- Server-wide: `mcp__servername`
- Tool-specific: `mcp__servername__toolname`

### Examples

**Server-wide access:**
```json
"allow": [
  "mcp__memory",                // All tools from memory server
  "mcp__filesystem",            // All tools from filesystem server
  "mcp__github"                 // All tools from GitHub server
]
```

**Tool-specific access:**
```json
"allow": [
  "mcp__github__get_repo",
  "mcp__github__list_issues",
  "mcp__github__create_pr",
  "mcp__memory__store",
  "mcp__memory__retrieve"
]
```

**Mixed permissions:**
```json
"allow": [
  "mcp__memory",                // All memory tools allowed
  "mcp__github__get_repo"       // Only specific GitHub tool
],
"ask": [
  "mcp__github__create_pr",     // Confirm before creating PRs
  "mcp__slack__send_message"    // Confirm before sending messages
],
"deny": [
  "mcp__exec",                  // Block execution server entirely
  "mcp__shell__run",            // Block specific shell tool
  "mcp__db__execute_sql"        // Block dangerous DB operations
]
```

### Common Patterns

**Safe read-only servers:**
```json
"allow": [
  "mcp__memory",
  "mcp__filesystem__read",
  "mcp__github__get_repo",
  "mcp__github__list_issues"
]
```

**Require confirmation for writes:**
```json
"ask": [
  "mcp__filesystem__write",
  "mcp__github__create_pr",
  "mcp__github__create_issue",
  "mcp__slack__send_message",
  "mcp__email__send"
]
```

**Block dangerous operations:**
```json
"deny": [
  "mcp__exec",
  "mcp__shell",
  "mcp__db__drop_table",
  "mcp__db__execute_sql",
  "mcp__system__reboot"
]
```

---

## Combining Multiple Rule Types

### Complete Project Configuration

```json
{
  "permissions": {
    "allow": [
      // Documentation access
      "WebFetch(https://docs.anthropic.com/*)",
      "WebFetch(https://docs.company.com/*)",

      // Safe commands
      "Bash(npm run test:*)",
      "Bash(npm run build)",
      "Bash(npm run lint)",
      "Bash(git status)",
      "Bash(git diff)",
      "Bash(git log)",

      // Project file access
      "Edit(/src/**)",
      "Edit(/tests/**)",
      "Edit(/docs/**)",
      "Read(/config/**)",
      "Write(/dist/**)",

      // MCP tools
      "mcp__memory",
      "mcp__github__get_repo"
    ],

    "ask": [
      // Confirm before installs
      "Bash(npm install *)",
      "Bash(pip install *)",

      // Confirm before pushes
      "Bash(git push *)",
      "Bash(git commit *)",

      // Confirm config edits
      "Edit(/config/**)",
      "Edit(/package.json)",
      "Edit(/tsconfig.json)",

      // Confirm MCP writes
      "mcp__github__create_pr",
      "mcp__filesystem__write"
    ],

    "deny": [
      // Block sensitive files
      "Edit(~/.ssh/**)",
      "Read(~/.aws/credentials)",
      "Edit(/.env*)",
      "Edit(/src/secrets/**)",

      // Block dangerous commands
      "Bash(rm -rf *)",
      "Bash(sudo *)",
      "Bash(curl *)",
      "Bash(wget *)",

      // Block external code
      "WebFetch(domain:pastebin.com)",

      // Block dangerous MCP
      "mcp__exec",
      "mcp__shell"
    ]
  }
}
```

---

## Pattern Precedence Examples

### Example 1: General allow with specific deny

```json
"allow": ["Edit(/docs/**)"],
"deny": ["Edit(/docs/secrets/**)"]
```

**Result:**
- ✅ `/docs/api.md` - Allowed
- ✅ `/docs/guide/intro.md` - Allowed
- ❌ `/docs/secrets/api-keys.md` - Denied (deny wins)
- ❌ `/docs/secrets/internal/passwords.txt` - Denied

### Example 2: General ask with specific allow

```json
"allow": ["Bash(git status)", "Bash(git diff)"],
"ask": ["Bash(git *)"]
```

**Result:**
- ✅ `git status` - Allowed (more specific)
- ✅ `git diff` - Allowed (more specific)
- ⚠️ `git push` - Ask (matches general pattern)
- ⚠️ `git commit` - Ask (matches general pattern)

### Example 3: Multiple deny levels

```json
"allow": ["Edit(/src/**)"],
"deny": ["Edit(/src/secrets/**)", "Edit(/src/api/keys/**)"]
```

**Result:**
- ✅ `/src/index.ts` - Allowed
- ✅ `/src/api/routes.ts` - Allowed
- ❌ `/src/secrets/config.json` - Denied
- ❌ `/src/api/keys/private.pem` - Denied

---

## Tips for Effective Patterns

1. **Be as specific as possible**
   - ❌ `"Bash(npm *)"` - Too broad
   - ✅ `"Bash(npm run test:*)"` - Specific to test commands

2. **Use deny for absolute restrictions**
   - Always deny access to: `.env*`, `~/.ssh/**`, `~/.aws/**`

3. **Use ask for dangerous operations**
   - `git push`, `npm install`, `rm *`, config file edits

4. **Layer your permissions**
   - Broad allow rules with specific deny exceptions
   - Example: Allow `/src/**` but deny `/src/secrets/**`

5. **Test your patterns**
   - Add one rule at a time
   - Verify it works as expected
   - Adjust specificity as needed

6. **Document complex patterns**
   - Add comments explaining why rules exist
   - Note any dependencies between rules

7. **Regular audits**
   - Review permissions quarterly
   - Remove unused rules
   - Update patterns as project evolves
