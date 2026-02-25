# Common Permission Patterns

Copy-paste ready permission configurations for common scenarios. Choose a pattern that matches your use case, customize as needed, and merge into your settings.json.

---

## Pattern 1: Maximum Security

**Use case:** Regulated environments, sensitive codebases, security audits, financial systems

**Philosophy:** Deny by default, explicit allow only when necessary

```json
{
  "permissions": {
    "deny": [
      "Edit(~/.ssh/**)",
      "Edit(//etc/**)",
      "Read(~/.aws/**)",
      "Read(~/.env*)",
      "Read(.env*)",
      "Edit(/secrets/**)",
      "Edit(/credentials/**)",
      "Bash(rm *)",
      "Bash(sudo *)",
      "Bash(curl *)",
      "Bash(wget *)",
      "Bash(nc *)",
      "Bash(netcat *)",
      "WebFetch(*)"
    ],
    "ask": [
      "Bash(*)",
      "Edit(*)",
      "Write(*)"
    ],
    "defaultMode": "plan",
    "disableBypassPermissionsMode": "disable"
  }
}
```

**Key features:**
- Read-only by default (`defaultMode: "plan"`)
- Cannot bypass permissions
- Blocks all network operations
- Requires approval for ANY modification
- Ideal for: Compliance, auditing, security reviews

---

## Pattern 2: Solo Developer (Permissive)

**Use case:** Personal projects, learning, rapid prototyping, local development

**Philosophy:** Trust the developer, minimal friction, common tools allowed

```json
{
  "permissions": {
    "allow": [
      "WebFetch(https://docs.anthropic.com/*)",
      "WebFetch(https://docs.claude.com/*)",
      "WebFetch(https://github.com/*)",
      "WebFetch(https://stackoverflow.com/*)",
      "WebFetch(https://developer.mozilla.org/*)",
      "Bash(npm run *)",
      "Bash(npm *)",
      "Bash(git *)",
      "Bash(docker compose *)",
      "Bash(pytest *)",
      "Bash(cargo *)",
      "Edit(./**)",
      "Write(./**)",
      "Read(./**)"
    ],
    "deny": [
      "Edit(~/.ssh/**)",
      "Edit(~/.aws/credentials)",
      "Edit(~/.gnupg/**)"
    ],
    "defaultMode": "acceptEdits"
  }
}
```

**Key features:**
- Auto-approves file edits
- Common dev tools pre-approved
- Only protects critical system files
- Ideal for: Personal learning, side projects, experimentation

---

## Pattern 3: Team Project (Balanced)

**Use case:** Shared repository, collaborative development, professional standards

**Philosophy:** Balance productivity with safety, team-appropriate guardrails

```json
{
  "permissions": {
    "allow": [
      "WebFetch(https://docs.yourcompany.com/*)",
      "WebFetch(https://docs.anthropic.com/*)",
      "WebFetch(https://stackoverflow.com/*)",
      "Bash(npm run test:*)",
      "Bash(npm run build)",
      "Bash(npm run lint)",
      "Bash(npm run dev)",
      "Bash(git status)",
      "Bash(git diff)",
      "Bash(git log)",
      "Bash(git branch)",
      "Edit(/src/**)",
      "Edit(/tests/**)",
      "Edit(/docs/**)",
      "Read(/config/**)"
    ],
    "ask": [
      "Bash(npm install *)",
      "Bash(npm publish *)",
      "Bash(git push *)",
      "Bash(git commit *)",
      "Bash(docker *)",
      "Edit(/package.json)",
      "Edit(/config/**)",
      "Edit(/tsconfig.json)"
    ],
    "deny": [
      "Edit(~/.ssh/**)",
      "Edit(//etc/**)",
      "Edit(/.env*)",
      "Edit(/src/secrets/**)",
      "Bash(rm -rf *)"
    ],
    "additionalDirectories": ["/tmp/build-cache"],
    "defaultMode": "default"
  }
}
```

**Key features:**
- Safe commands pre-approved
- Dangerous operations require confirmation
- Protected directories enforced
- Ideal for: Team repositories, professional development, code reviews

---

## Pattern 4: CI/CD Pipeline

**Use case:** Automated builds, GitHub Actions, GitLab CI, deployment pipelines

**Philosophy:** Minimal friction for automation, workspace isolation

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run *)",
      "Bash(yarn *)",
      "Bash(docker *)",
      "Bash(git *)",
      "Bash(pytest *)",
      "Bash(cargo build)",
      "Bash(make *)",
      "Edit(/workspace/**)",
      "Edit(/github/workspace/**)",
      "Read(/workspace/**)",
      "Write(/workspace/**)"
    ],
    "deny": [
      "Edit(//etc/**)",
      "Edit(~/.ssh/**)",
      "WebFetch(*)"
    ],
    "defaultMode": "bypassPermissions"
  }
}
```

**Key features:**
- Bypass mode for automation
- Limited to workspace directories
- No external network access
- Ideal for: GitHub Actions, GitLab CI, Jenkins, automated testing

---

## Pattern 5: Research & Learning

**Use case:** Educational projects, documentation exploration, safe experimentation, students

**Philosophy:** Read-only exploration, no modifications, safe documentation access

```json
{
  "permissions": {
    "allow": [
      "WebFetch(https://docs.anthropic.com/*)",
      "WebFetch(https://docs.claude.com/*)",
      "WebFetch(https://en.wikipedia.org/*)",
      "WebFetch(https://developer.mozilla.org/*)",
      "WebFetch(https://stackoverflow.com/*)",
      "WebFetch(https://github.com/*)",
      "WebFetch(https://pypi.org/*)",
      "WebFetch(https://crates.io/*)",
      "Read(/docs/**)",
      "Read(/examples/**)",
      "Read(/src/**)"
    ],
    "deny": [
      "Edit(*)",
      "Write(*)",
      "Bash(*)"
    ],
    "defaultMode": "plan"
  }
}
```

**Key features:**
- Read-only mode enforced
- No command execution
- Wide documentation access
- Ideal for: Learning, code review, documentation research, students

---

## Pattern 6: API Development

**Use case:** REST API development, backend services, database work, microservices

**Philosophy:** Development tools + database access, careful with migrations

```json
{
  "permissions": {
    "allow": [
      "WebFetch(https://docs.anthropic.com/*)",
      "WebFetch(https://api-docs.yourcompany.com/*)",
      "Bash(npm run dev)",
      "Bash(npm run test:*)",
      "Bash(docker compose up *)",
      "Bash(docker compose logs *)",
      "Bash(prisma generate)",
      "Bash(prisma studio)",
      "Bash(curl localhost:*)",
      "Bash(curl http://localhost:*)",
      "Bash(psql *)",
      "Edit(/src/api/**)",
      "Edit(/src/models/**)",
      "Edit(/src/services/**)",
      "Edit(/tests/**)",
      "Read(/prisma/**)",
      "Read(/migrations/**)"
    ],
    "ask": [
      "Bash(npm run migrate)",
      "Bash(prisma migrate *)",
      "Bash(docker compose down)",
      "Edit(/prisma/schema.prisma)",
      "Edit(/migrations/**)",
      "Edit(/.env*)"
    ],
    "deny": [
      "Bash(rm *)",
      "Edit(/database/production/**)",
      "Bash(psql -h production*)"
    ],
    "defaultMode": "default"
  }
}
```

**Key features:**
- Local development tools allowed
- Database operations require confirmation
- Production databases protected
- Ideal for: Backend development, API services, database schema work

---

## Pattern 7: Frontend Development

**Use case:** React/Vue/Angular development, component libraries, UI work, Storybook

**Philosophy:** Fast iteration on UI code, cautious with dependencies

```json
{
  "permissions": {
    "allow": [
      "WebFetch(https://react.dev/*)",
      "WebFetch(https://vuejs.org/*)",
      "WebFetch(https://angular.io/*)",
      "WebFetch(https://developer.mozilla.org/*)",
      "WebFetch(https://tailwindcss.com/*)",
      "Bash(npm run dev)",
      "Bash(npm run test:*)",
      "Bash(npm run storybook)",
      "Bash(npm run build)",
      "Bash(npm run lint)",
      "Edit(/src/components/**)",
      "Edit(/src/pages/**)",
      "Edit(/src/styles/**)",
      "Edit(/src/hooks/**)",
      "Edit(/public/**)",
      "Edit(/tests/**)"
    ],
    "ask": [
      "Bash(npm install *)",
      "Edit(/package.json)",
      "Edit(/vite.config.*)",
      "Edit(/webpack.config.*)",
      "Edit(/tailwind.config.*)"
    ],
    "defaultMode": "acceptEdits"
  }
}
```

**Key features:**
- Component editing auto-approved
- Build tools pre-configured
- Dependency changes require confirmation
- Ideal for: React, Vue, Angular, component libraries, UI development

---

## Pattern 8: DevOps & Infrastructure

**Use case:** Infrastructure as code, Terraform, Kubernetes, deployment automation

**Philosophy:** Powerful tools with explicit safety checks

```json
{
  "permissions": {
    "allow": [
      "WebFetch(https://registry.terraform.io/*)",
      "WebFetch(https://kubernetes.io/*)",
      "Bash(terraform plan)",
      "Bash(terraform validate)",
      "Bash(kubectl get *)",
      "Bash(kubectl describe *)",
      "Bash(kubectl logs *)",
      "Bash(docker build *)",
      "Bash(docker images)",
      "Bash(docker ps)",
      "Edit(/terraform/**)",
      "Edit(/k8s/**)",
      "Edit(/helm/**)",
      "Edit(/ansible/**)",
      "Read(/scripts/**)"
    ],
    "ask": [
      "Bash(terraform apply)",
      "Bash(terraform destroy)",
      "Bash(kubectl apply *)",
      "Bash(kubectl delete *)",
      "Bash(kubectl scale *)",
      "Bash(docker push *)",
      "Bash(helm install *)",
      "Bash(helm upgrade *)"
    ],
    "deny": [
      "Bash(terraform destroy -auto-approve)",
      "Bash(kubectl delete namespace *)",
      "Bash(rm -rf /terraform/*)"
    ],
    "defaultMode": "default"
  }
}
```

**Key features:**
- Read operations allowed
- Destructive operations require confirmation
- Auto-approve explicitly blocked
- Ideal for: Terraform, Kubernetes, Docker, infrastructure automation

---

## Pattern 9: Data Science & ML

**Use case:** Jupyter notebooks, model training, data analysis, experimentation

**Philosophy:** Computation + visualization, protect trained models

```json
{
  "permissions": {
    "allow": [
      "WebFetch(https://huggingface.co/*)",
      "WebFetch(https://pytorch.org/*)",
      "WebFetch(https://tensorflow.org/*)",
      "WebFetch(https://scikit-learn.org/*)",
      "Bash(python *.py)",
      "Bash(jupyter notebook)",
      "Bash(jupyter lab)",
      "Bash(pip install *)",
      "Bash(conda install *)",
      "Edit(/notebooks/**)",
      "Edit(/src/**)",
      "Edit(/experiments/**)",
      "Write(/data/processed/**)",
      "Write(/results/**)",
      "Write(/logs/**)",
      "Read(/data/**)",
      "Read(/models/**)"
    ],
    "ask": [
      "Bash(python train_model.py)",
      "Edit(/models/**)",
      "Edit(/data/raw/**)"
    ],
    "deny": [
      "Bash(rm -rf /data/*)",
      "Bash(rm -rf /models/*)"
    ],
    "defaultMode": "acceptEdits"
  }
}
```

**Key features:**
- Python and Jupyter workflows enabled
- Model training requires confirmation
- Data and models protected from deletion
- Ideal for: Data science, ML research, Jupyter notebooks, experimentation

---

## Pattern 10: Open Source Contribution

**Use case:** Contributing to public repositories, following project guidelines

**Philosophy:** Safe exploration, careful with commits, respect project rules

```json
{
  "permissions": {
    "allow": [
      "WebFetch(https://github.com/*)",
      "WebFetch(https://docs.github.com/*)",
      "WebFetch(https://opensource.guide/*)",
      "Bash(git status)",
      "Bash(git diff)",
      "Bash(git log)",
      "Bash(git branch)",
      "Bash(git checkout *)",
      "Bash(npm run test:*)",
      "Bash(npm run lint)",
      "Edit(/src/**)",
      "Edit(/tests/**)",
      "Edit(/docs/**)",
      "Read(/CONTRIBUTING.md)",
      "Read(/CODE_OF_CONDUCT.md)"
    ],
    "ask": [
      "Bash(git commit *)",
      "Bash(git push *)",
      "Bash(npm install *)",
      "Edit(/package.json)",
      "Edit(/.github/**)"
    ],
    "deny": [
      "Bash(git push --force *)",
      "Bash(git push -f *)"
    ],
    "defaultMode": "default"
  }
}
```

**Key features:**
- Safe git operations allowed
- Commits and pushes require review
- Force push blocked
- Ideal for: Open source contributions, public repositories, collaborative projects

---

## How to Use These Patterns

### 1. Choose Your Pattern

Select the pattern that best matches your use case. You can also combine multiple patterns.

### 2. Copy to settings.json

**For project-wide settings** (shared with team):
```bash
# Create or edit project settings
nano .claude/settings.json
```

**For personal settings** (just you):
```bash
# Create or edit user settings
nano ~/.claude/settings.json
```

### 3. Customize for Your Environment

**Replace placeholders:**
- `yourcompany.com` → your actual company domain
- `/workspace/**` → your actual workspace path
- Add/remove tools based on your stack

**Adjust specificity:**
- More specific = more secure but less flexible
- More general = more flexible but less secure

### 4. Test Incrementally

1. Add the permissions configuration
2. Try common operations to verify they work
3. Adjust allow/ask/deny rules as needed
4. Document any custom rules you add

### 5. Review and Update

- Audit permissions quarterly
- Remove unused rules
- Update as your project evolves
- Share updates with team

---

## Combining Patterns

You can merge multiple patterns by combining their rules:

### Example: Frontend + API Development

```json
{
  "permissions": {
    "allow": [
      // Frontend tools
      "Bash(npm run dev)",
      "Bash(npm run build)",
      "Edit(/src/components/**)",
      "Edit(/src/pages/**)",

      // API tools
      "Bash(docker compose up *)",
      "Edit(/src/api/**)",
      "Edit(/src/models/**)"
    ],
    "ask": [
      "Bash(npm install *)",
      "Bash(docker compose down)",
      "Edit(/package.json)"
    ],
    "deny": [
      "Edit(/.env*)",
      "Edit(/secrets/**)"
    ]
  }
}
```

### Example: Team Project + Security

Take the team pattern's allow list and the security pattern's deny list:

```json
{
  "permissions": {
    "allow": [
      // Team project allows...
    ],
    "ask": [
      // Team project asks...
    ],
    "deny": [
      // Maximum security denies...
      "Edit(~/.ssh/**)",
      "Edit(//etc/**)",
      "Read(~/.aws/**)",
      // ... plus team-specific denies
    ]
  }
}
```

---

## Pattern Selection Guide

| Scenario | Recommended Pattern | Key Consideration |
|----------|-------------------|-------------------|
| Financial systems | Maximum Security | Compliance requirements |
| Personal learning | Solo Developer | Minimize friction |
| Team codebase | Team Project | Balance safety & productivity |
| GitHub Actions | CI/CD Pipeline | Automation needs |
| Code review | Research & Learning | Read-only exploration |
| Backend services | API Development | Database safety |
| Component library | Frontend Development | Fast iteration |
| Cloud infrastructure | DevOps & Infrastructure | Deployment safety |
| ML research | Data Science & ML | Experiment management |
| Public repos | Open Source Contribution | Community standards |

---

## Advanced: Combining with defaultMode

### For Development Sessions
```json
{
  "permissions": {
    "allow": [...],
    "deny": [...],
    "defaultMode": "acceptEdits"
  }
}
```
Auto-approves file edits but respects your allow/deny rules

### For Code Review
```json
{
  "permissions": {
    "allow": ["Read(**)", "WebFetch(*)"],
    "deny": ["Edit(*)", "Write(*)", "Bash(*)"],
    "defaultMode": "plan"
  }
}
```
Read-only mode regardless of other settings

### For CI/CD (Use Cautiously)
```json
{
  "permissions": {
    "allow": [...],
    "deny": [...],
    "defaultMode": "bypassPermissions",
    "disableBypassPermissionsMode": null
  }
}
```
No permission prompts (trusted environments only)

---

## Tips for Pattern Customization

1. **Start restrictive, then loosen**
   - Begin with a stricter pattern
   - Add allow rules as you discover needs
   - Easier than starting permissive and finding problems

2. **Document your changes**
   - Add comments explaining custom rules
   - Note why specific paths/commands are allowed/denied
   - Help future team members understand

3. **Version control project settings**
   - Commit `.claude/settings.json` to git
   - Add `.claude/settings.local.json` to `.gitignore`
   - Let team members customize locally

4. **Regular security audits**
   - Review allow rules quarterly
   - Check if deny rules are still relevant
   - Update as threats evolve

5. **Test with real workflows**
   - Don't just copy-paste
   - Run through your typical development tasks
   - Adjust until permissions feel natural
