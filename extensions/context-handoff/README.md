# Context Handoff Extension

This optional, default-disabled extension makes small context files for resuming a task in a new Codex thread or with another agent. It creates a task-specific CURRENT_STATE view, a project DOCUMENT_INDEX, a schema-checked snapshot, and a short handoff file.

Use it when a project has several local tasks or you need a concise resume point. Do not use it if Core governance and its formal reports are already enough. It is disabled by default so Core-only users receive no new files, rules, CLI behavior, or required report fields.

The extension is a derived view only. It cannot complete a task, mark tests passed, approve a release, deploy, write external systems, or turn a local commit into a remote merge. Missing evidence is `UNKNOWN`; conflicting structured evidence is `CONFLICT_REQUIRES_REVIEW`.

## Local commands

Run commands from the Core repository, supplying a target project and unique IDs:

```bash
python3 extensions/context-handoff/manage.py context-handoff preview --target /path/to/project --project-id PROJECT_A --task-id TASK_1
python3 extensions/context-handoff/manage.py context-handoff enable --target /path/to/project --project-id PROJECT_A --task-id TASK_1 --event TASK_STARTED
python3 extensions/context-handoff/manage.py context-handoff status --target /path/to/project
python3 extensions/context-handoff/manage.py context-handoff disable --target /path/to/project
python3 extensions/context-handoff/manage.py context-handoff uninstall --target /path/to/project
python3 extensions/context-handoff/manage.py context-handoff uninstall --target /path/to/project --apply
```

`preview` makes no changes and shows planned writes, existing conflicts, owned paths, compatibility, and files it will not modify. `enable` only writes `.agent_context_handoff/` inside the target. It writes each task's state separately, then uses a project lock to rebuild a deterministic project index from every valid task snapshot. It is idempotent for unchanged derived content, and a user-modified index is preserved while `DOCUMENT_INDEX.proposed.md` is produced with `OWNERSHIP_CONFLICT`. Invalid snapshots are skipped, shown as warnings, and make the CLI return a non-zero diagnostic. `disable` stops generation but preserves history. `uninstall` first prints a deletion plan; `--apply` only removes the unmodified extension state manifest and ownership manifest. Generated snapshots, handoffs, and any user-modified file are retained.

## Evidence and isolation

Optionally pass `--evidence path/to/structured.yaml`. It may contain `task_statuses`, `verification_statuses`, blockers, authoritative file paths, and explicit remote-merge evidence. The extension does not infer a result from a plan, prose report name, or local commit.

Every generated task state is stored under `.agent_context_handoff/<project_id>/` and includes `project_id`, `task_id`, repository, branch, HEAD, and worktree status. Task-specific CURRENT_STATE, snapshot, and handoff paths prevent two tasks in one project from overwriting one another. The project index is an index only.

Views update only when the caller explicitly supplies an allowed event: `TASK_STARTED`, `HARD_BLOCKED`, `EXECUTION_COMPLETED`, `PHASE_CLOSED`, `REMOTE_MERGED`, or `RELEASE_STATUS_CHANGED`. This avoids reading full governance history during ordinary work. Limits are 100 CURRENT_STATE lines, 150 DOCUMENT_INDEX lines, and 40 snapshot lines.

This is Context Handoff `0.1.0`. It is optional and disabled by default. It does not access Obsidian, ChatGPT files, GitHub, APIs, databases, or telemetry.
