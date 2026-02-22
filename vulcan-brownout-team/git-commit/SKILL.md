---
name: git-commit
description: "Git commit convention for all Vulcan Brownout team members. Use this skill whenever committing code, docs, or any artifacts to the repository. Defines the commit message format, .gitignore rules, and pre-commit checklist. Every team member (Freya, FiremanDecko, Loki) must follow this convention."
---

# Git Commit Convention

All team members must follow this commit format when committing to the Vulcan Brownout repository.

## Commit Message Format

```
<one-line description under 80 characters>

# Summary of changes

## Summary

- One-liner describing change 1
- One-liner describing change 2
- One-liner describing change 3
```

### Rules

1. **First line**: Imperative mood, under 80 characters, lowercase start. Describes *what* the commit does.
2. **Blank line**: Exactly one blank line after the first line.
3. **H1 header**: `# Summary of changes` — always this exact text.
4. **H2 section**: `## Summary` — bullet list of one-liner descriptions of each change.
5. Each bullet should be a single line, starting with `- `.
6. No trailing blank lines after the last bullet.

### Examples

**Good:**
```
add Sprint 1 architecture ADRs and system design

# Summary of changes

## Summary

- Add ADR-001 integration architecture
- Add ADR-002 frontend panel technology choice
- Add ADR-003 deployment architecture with SSH flow
- Add system design doc with Mermaid component diagram
- Add API contracts for WebSocket commands
```

**Good:**
```
implement battery entity auto-discovery service

# Summary of changes

## Summary

- Add BatteryService class with entity discovery
- Register WebSocket command handler for query_devices
- Add const.py with domain constants and defaults
- Wire up event listener for state_changed events
```

**Bad:**
```
Updated stuff    <- vague, no detail

changes          <- useless

Add ADR-001 integration architecture for the Vulcan Brownout Home Assistant custom integration project
                 <- over 80 characters
```

## Post-Commit: Push to GitHub

After every commit, push to GitHub immediately:

```bash
git push
```

## Pre-Commit Checklist

Before every commit, verify:

- [ ] `.env` is NOT staged (check `git status`)
- [ ] No secrets, tokens, or credentials in any staged file
- [ ] `.gitignore` includes: `.env`, `*.env`, `.env.*`, `!.env.example`
- [ ] All Mermaid diagrams render correctly (valid syntax)
- [ ] No TODO/FIXME/HACK comments unless intentional and tracked
- [ ] Files are in the correct sprint/team directory structure

## .gitignore Baseline

Every repo must have at minimum:

```
# Secrets - NEVER commit
.env
*.env
.env.*
!.env.example

# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/

# Node/Frontend
node_modules/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

## Branch Naming (future sprints)

When branches are used:
- `sprint-N/story-description` for feature work
- `fix/short-description` for bug fixes
- `chore/short-description` for maintenance
