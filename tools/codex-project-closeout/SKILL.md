---
name: codex-project-closeout
description: Record a concise, safe Codex Memory Hub handoff whenever an engineering task, deployment, fix, or investigation is complete.
---

# Codex Project Closeout

Before replying after an engineering task, automatically create a `handoff` project record with the local `codex-memory-hub` command. Upload relevant small code files or archives and record their file ID and SHA-256. Add the UTC completion time and the remote device identifier when they are known.

Include only reviewable facts: project slug, completed work, service URL, host, port, deployment/config paths, artifact references, verification results, rollback or restart notes, and next actions. If no durable change was made, record a short checked/no-change handoff.

Never write passwords, API keys, tokens, private keys, cookies, session files, or connection strings. Use only a non-sensitive credential reference such as `credential:production-db` or “stored in the admin credential vault”. Do not upload hidden chain-of-thought.
