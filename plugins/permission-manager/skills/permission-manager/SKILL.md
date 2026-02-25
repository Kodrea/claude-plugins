---
name: permission-manager
description: Configure Claude Code permission rules (allow/deny/ask) in settings.json to enable or restrict autonomous execution. Use when user requests "allow this to run autonomously", "don't ask permission for", "block access to", or when configuring tool access for Bash commands, WebFetch domains, file operations, or MCP servers. Also use when user asks to make, create, update, edit, or change "settings.json", "settings.local.json", ".claude/settings.json", or ".claude/settings.local.json". Handles permission precedence, syntax validation, and provides security guardrails.
allowed-tools: Read, Edit, Bash
---

# Claude Code Permission Manager

Manage allow/deny/ask permission rules in settings.json to control autonomous execution.

## Core Concepts

**Permission Rule Precedence:** deny > ask > allow
- **deny**: Blocks completely (highest priority)
- **ask**: Prompts user (medium priority)
- **allow**: Auto-approves (lowest priority)

**When to use each:**
- Use `allow` for trusted, repetitive operations
- Use `ask` for potentially dangerous operations that need confirmation
- Use `deny` for sensitive files/commands that should never be accessed

---

## Special Case: "Allow this to run autonomously"

When user requests autonomous execution without specifying what:

### 1. Clarify the Scope

Ask the user:
- "What specific operation should run autonomously?"
- "Is this for a command, file operation, or website access?"
- "Should this be permanent (project settings) or temporary (this session)?"

### 2. Determine Appropriate Solution

**For specific operations** (RECOMMENDED):
```
User: "Allow npm test to run autonomously"
→ Add: "Bash(npm run test:*)" to allow list
```

**For workflows** (multiple related operations):
```
User: "Allow my build process to run autonomously"
→ Add multiple rules:
  - "Bash(npm run build)"
  - "Bash(npm run lint)"
  - "Edit(/dist/**)"
```

**For session-wide** (temporary):
```
User: "Allow file edits to run autonomously for today"
→ Set: "defaultMode": "acceptEdits"
```

**For project-wide** (use cautiously):
```
User: "Allow everything to run autonomously" (CI/CD context)
→ Set: "defaultMode": "bypassPermissions"
→ WARN: Only in trusted environments
```

### 3. Security Check

Before enabling broad autonomy, verify:
- Is this a trusted environment?
- Could this expose sensitive data?
- Is the scope too broad?

**Always recommend:**
- Specific `allow` rules over `defaultMode` changes
- `acceptEdits` over `bypassPermissions`
- Adding complementary `deny` rules for sensitive areas

---

## Main Workflow

### Step 1: Identify the Permission Request

Determine from user's message:
- **Tool type**: Bash, WebFetch, Read, Edit, Write, MCP
- **Action**: allow, deny, or ask
- **Target**: Specific command, URL, file path, or pattern

**Examples:**
- "Block access to .env files" → deny, Edit, .env*
- "Allow npm commands" → allow, Bash, npm*
- "Ask before pushing to git" → ask, Bash, git push*

### Step 2: Locate Settings File

Check for settings.json in this order:
1. `.claude/settings.json` (project settings - recommended for teams)
2. `.claude/settings.local.json` (project personal - gitignored)
3. `~/.claude/settings.json` (user global settings)

**If none exist**, ask user:
- "Should I create project settings (.claude/settings.json) or user settings (~/.claude/settings.json)?"
- **Recommend**: Project settings for team-shared rules, user settings for personal preferences

### Step 3: Read Current Configuration

Read the settings.json file to:
- Check for existing `permissions` section
- Identify any conflicting rules
- Preserve all other settings (env, hooks, etc.)

**If permissions section doesn't exist**, create it:
```json
{
  "permissions": {
    "allow": [],
    "ask": [],
    "deny": []
  }
}
```

### Step 4: Build the Permission Rule

Construct the correct syntax based on tool type:

**Bash commands:**
```
"Bash(npm run test:*)"     // Wildcard at end only
"Bash(git status)"         // Exact match
"Bash(docker compose up)"  // Include arguments
```

**WebFetch (URLs):**
```
"WebFetch(https://docs.anthropic.com/*)"  // Path wildcard
"WebFetch(domain:anthropic.com)"          // Domain only
```

**File operations (Read/Edit/Write):**
```
"Edit(/src/**)"           // Relative to settings.json
"Edit(~/projects/**)"     // Home directory
"Edit(//tmp/file.txt)"    // Absolute path
"Read(.env*)"             // Current working directory
```

**MCP tools:**
```
"mcp__memory"             // All tools from server
"mcp__github__create_pr"  // Specific tool
```

**See syntax-reference.md for comprehensive examples**

### Step 5: Check for Conflicts

Before adding the rule, verify:

**Precedence conflicts:**
```
Current: "deny": ["Edit(/docs/secrets/**)"]
Adding:  "allow": ["Edit(/docs/**)"]
→ EXPLAIN: deny rule takes precedence, /docs/secrets/** will still be blocked
```

**Duplicate rules:**
```
Current: "allow": ["Bash(npm run test)"]
Adding:  "allow": ["Bash(npm run test)"]
→ INFORM: This rule already exists
```

**Pattern specificity:**
```
Current: "allow": ["Edit(/src/**)"]
Adding:  "allow": ["Edit(/src/api/**)"]
→ NOTE: More general rule already covers this
```

### Step 6: Add or Modify the Rule

Edit settings.json to add the rule to the appropriate section:

```json
{
  "permissions": {
    "allow": [
      "existing-rule-1",
      "existing-rule-2",
      "NEW-RULE-HERE"
    ],
    "ask": [...],
    "deny": [...]
  }
}
```

**Important:**
- Preserve ALL existing rules
- Maintain proper JSON syntax (commas, quotes)
- Keep allow/ask/deny sections separate
- Preserve all other settings (env, model, hooks, etc.)

### Step 7: Validate Configuration

After editing, validate:

**1. JSON syntax:**
```bash
jq . .claude/settings.json
```
If this fails, the JSON is invalid - fix syntax errors

**2. Path validity (for file operations only):**
- Expand relative paths to show what they resolve to
- Verify paths make sense for the project
- Don't check existence (files may be created later)

**3. Permission logic:**
- Confirm deny rules aren't blocking unintended operations
- Verify allow rules aren't too permissive
- Check that ask rules are on appropriate operations

### Step 8: Inform User

Provide clear feedback:

**What was changed:**
```
✓ Added allow rule: "Bash(npm run test:*)"
✓ Updated: .claude/settings.json
```

**Any warnings:**
```
⚠ Note: Existing deny rule for "Bash(npm run test:e2e)" will override this allow rule
```

**Effect:**
```
✓ npm test commands will now run autonomously without permission prompts
✓ Changes take effect immediately (no restart needed)
```

### Step 9: Suggest Testing (Optional)

If user wants to verify the permission works:
```
"You can test this by running: claude 'run npm test'"
```

---

## Decision Tree for Autonomous Requests

```
User says: "Allow this to run autonomously"
│
├─ Specific operation mentioned?
│  ├─ YES → Add specific allow rule
│  │  Examples: "npm test", "editing /src/api/"
│  │  ✓ Recommended: Narrow scope, high security
│  │
│  └─ NO → Ask clarifying questions
│
├─ Workflow context (multiple operations)?
│  ├─ YES → Add multiple allow rules
│  │  Examples: "build process", "refactoring session"
│  │  ⚠ Verify each operation is necessary
│  │
│  └─ NO → Continue to next check
│
├─ Session-only (temporary)?
│  ├─ YES → Consider defaultMode: "acceptEdits"
│  │  ⚠ Explain this is temporary for current session
│  │
│  └─ NO → Continue to next check
│
└─ Project-wide (permanent)?
   ├─ YES → Use .claude/settings.json with specific rules
   │  ⚠ HIGH CAUTION: Affects entire team
   │
   └─ UNCLEAR → Ask user to clarify scope
```

---

## Common Scenarios

### Scenario 1: Development without friction
```
User: "Allow npm commands to run autonomously"
→ Add: "Bash(npm run *)" to allow list
→ Add: "Bash(npm install *)" to ask list (safety)
```

### Scenario 2: Secure sensitive files
```
User: "Block access to environment files"
→ Add: "Edit(.env*)" to deny list
→ Add: "Read(.env*)" to deny list
```

### Scenario 3: Allow documentation access
```
User: "Allow Claude to access Anthropic docs"
→ Add: "WebFetch(https://docs.anthropic.com/*)" to allow list
```

### Scenario 4: Refactoring session
```
User: "I'm refactoring /src/api - allow this to run autonomously"
→ Add: "Edit(/src/api/**)" to allow list
→ Add: "Read(/src/**)" to allow list (for context)
→ Recommend: "Edit(/src/api/secrets/**)" to deny list (protection)
```

### Scenario 5: CI/CD setup
```
User: "Allow this to run autonomously - setting up GitHub Actions"
→ Recognize CI context
→ Recommend: "defaultMode": "bypassPermissions" for CI only
→ Add deny rules for critical files as guardrails
```

---

## defaultMode Interactions

**Understanding defaultMode:**

- `"default"`: Normal - prompts for each new tool usage
- `"acceptEdits"`: Auto-approves Edit/Write, still prompts for Bash/WebFetch
- `"plan"`: Read-only mode - blocks ALL modifications regardless of allow rules
- `"bypassPermissions"`: No prompts - skips all permission checks (use cautiously)

**When defaultMode overrides allow/deny:**
- `"plan"` mode: All modification attempts blocked, even with allow rules
- `"bypassPermissions"` mode: All operations allowed, even with deny rules (unless `disableBypassPermissionsMode` is set)

**Recommendation:**
- Use specific allow/deny/ask rules over defaultMode changes
- Reserve `bypassPermissions` for CI/CD and trusted environments only

---

## Security Guardrails

When enabling autonomous execution, ALWAYS suggest complementary deny rules:

**If allowing broad file access:**
```json
"allow": ["Edit(/src/**)", "Edit(/docs/**)"],
"deny": ["Edit(/.env*)", "Edit(/secrets/**)", "Edit(~/.ssh/**)"]
```

**If allowing bash commands:**
```json
"allow": ["Bash(npm run *)", "Bash(git status)", "Bash(git diff)"],
"deny": ["Bash(rm -rf *)", "Bash(sudo *)", "Bash(curl *)"]
```

**If allowing broad WebFetch:**
```json
"allow": ["WebFetch(https://docs.*/)"],
"deny": ["WebFetch(domain:pastebin.com)"]
```

---

## Additional Resources

- **syntax-reference.md**: Comprehensive syntax examples for all tool types
- **common-patterns.md**: Pre-built permission configurations for common scenarios

---

## Tips for Success

1. **Be specific**: `"Bash(npm run test:unit)"` is better than `"Bash(npm *)"`
2. **Layer security**: Use allow for common ops, deny for sensitive areas
3. **Test incrementally**: Add rules one at a time, verify they work
4. **Document intent**: Add comments (in JSON5 format) explaining why rules exist
5. **Review regularly**: Audit permissions quarterly, remove unused rules
