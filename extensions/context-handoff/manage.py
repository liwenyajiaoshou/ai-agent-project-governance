#!/usr/bin/env python3
"""CLI for the optional local Context Handoff extension."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from context_handoff import disable, enable, preview, uninstall, _load_mapping

def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the optional Context Handoff extension")
    parser.add_argument("extension", choices=["context-handoff"])
    parser.add_argument("action", choices=["preview", "enable", "status", "disable", "uninstall"])
    parser.add_argument("--target", type=Path, default=Path.cwd())
    parser.add_argument("--project-id", default="LOCAL_PROJECT")
    parser.add_argument("--task-id", default="UNSPECIFIED")
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--event", default="TASK_STARTED")
    parser.add_argument("--apply", action="store_true", help="Apply the safe uninstall deletion plan")
    args = parser.parse_args()
    try:
        evidence = _load_mapping(args.evidence)
        if args.action == "preview": result = preview(args.target, args.project_id, args.task_id, evidence)
        elif args.action == "enable": result = enable(args.target, args.project_id, args.task_id, evidence, args.event)
        elif args.action == "disable": result = disable(args.target)
        elif args.action == "uninstall": result = uninstall(args.target, args.apply)
        else:
            state = args.target.resolve() / ".agent_context_handoff" / "extension_state.yaml"
            result = {"status": "NOT_INSTALLED"} if not state.exists() else {"status": "ENABLED" if "enabled: true" in state.read_text(encoding="utf-8") else "DISABLED"}
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 2 if result.get("status") == "ENABLED_WITH_WARNINGS" else (3 if result.get("status") == "OWNERSHIP_CONFLICT" else 0)
    except (OSError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr); return 3
if __name__ == "__main__": raise SystemExit(main())
