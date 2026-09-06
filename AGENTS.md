# AGENTS.md

This file provides guidance to Codex when working in this repository.

## Project

This is Logan's primary Codex workspace — a blank-slate repo used for building projects and automations. No single framework or stack is locked in yet; this file should be updated as projects are added.

Common external systems in use: Google Workspace (Sheets, Gmail, Drive), GoHighLevel CRM, Meta Ads.

## Self-Improvement Loop

Check `lessons.md` at session start. After any correction, append a new entry:
> "When X, do Y instead."

## Tech Stack (update as projects are added)

- Runtime: TBD per project
- External APIs: GoHighLevel (v2021-07-28, base URL `https://services.leadconnectorhq.com/`), Google APIs, Meta Graph API
- Deployment: TBD per project

## Git Workflow

- Work on feature branches, never commit directly to `main`
- Use descriptive branch names (`feature/auth`, `fix/login-bug`)
- Write clear commit messages focused on the "why"
- Open a pull request to merge into `main`

## Code Style

- Prefer clarity over cleverness
- No unnecessary comments — only explain non-obvious behavior
- Keep functions small and focused
- No dead code or unused imports

## Codex Behavior

- Always read relevant files before editing
- Do not commit, push, or delete files without explicit instruction
- Do not install packages without asking first
- Summarize what changed after completing a task
- Spec before build: ask clarifying questions, write a plan, get approval, then build
