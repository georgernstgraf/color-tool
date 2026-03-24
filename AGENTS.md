# Color Tool

## Framework Isolation (CRITICAL)

This agent operates with ZERO knowledge of the OpenClaw framework.

**Forbidden:**
- Creating SOUL.md, USER.md, IDENTITY.md, HEARTBEAT.md, TOOLS.md, BOOTSTRAP.md
- Referencing OpenClaw concepts (gh-issue workflow, HEARTBEAT, skills, hooks, etc.)
- Using OpenClaw-specific workflows or tools

**Allowed:**
- Standard git/github operations (commit, push, PR)
- AGENTS.md for project instructions
- docs/ai/ knowledge files
- Project-specific workflows only

## Project Identity

Color tool development (WCAG contrast checking, color simulation)

## Knowledge Persistence

Uses `docs/ai/` directory:
- HANDOFF.md - Open tasks and next-session context
- CONVENTIONS.md - Coding rules and patterns
- DECISIONS.md - Architectural choices
- PITFALLS.md - Gotchas and lessons learned
- STATE.md - Current focus and progress
- DOMAIN.md - Business logic rules

## Repository

- GitHub: `georgernstgraf/color-tool`
- Local workspace: `/home/openclaw/repos/color-tool`

## Knowledge Bootstrap
Before starting any task, read the following files in order:
1. `docs/ai/HANDOFF.md` <- **read first, act on it**
2. `docs/ai/CONVENTIONS.md`
3. `docs/ai/DECISIONS.md`
4. `docs/ai/PITFALLS.md`
5. `docs/ai/STATE.md`
6. `docs/ai/DOMAIN.md` (if task involves business logic)

If `HANDOFF.md` contains open tasks, complete them before starting
any new work unless the user explicitly says otherwise.
