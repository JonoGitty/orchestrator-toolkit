---
name: {{SKILL_SLUG}}
description: {{SKILL_DESCRIPTION}}
user-invocable: true
argument-hint: "[describe what you need]"
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

# {{SKILL_NAME}}

{{SKILL_DESCRIPTION}}

## When to use this skill

Use /{{SKILL_SLUG}} when the user needs help with {{SKILL_NAME}}-related tasks.

## Context

Refer to the domain knowledge in CONTEXT.md for API patterns, best practices,
and common workflows specific to this domain.

## Steps

1. Understand what the user needs
2. Apply domain-specific patterns from CONTEXT.md
3. Write code following the conventions and best practices
4. Verify the result works correctly

$ARGUMENTS
