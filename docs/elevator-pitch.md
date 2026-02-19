# Orchestrator Toolkit — Elevator Pitch

## What it is

A lean middleware layer that sits between AI coding agents (Claude Code, OpenAI
Codex, Cursor) and the machine. The agents handle reasoning and code generation;
the orchestrator handles execution, building, and coordination.

## What it does

- Takes structured plans (from any AI agent) and executes them
- Detects language stack and installs dependencies automatically
- Builds and runs projects across Python, Node.js, Go, Rust, Java, C++
- Plugin system for extending with audit trails, policy enforcement, etc.
- Ships with a Patchwork (codex-audit) integration for tamper-evident audit logs

## Why it matters

AI coding tools can generate code but can't build and run it reliably on your
machine. This is the execution layer that fills that gap — stack-aware, pluggable,
and designed to be called programmatically by AI agents or CI/CD pipelines.

## Status

v0.2 — stripped down from a larger app-builder project to focus on the middleware
use case. Plugin system is live, Patchwork integration is ready.
