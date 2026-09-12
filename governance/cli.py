"""CLI adapter for P1 Preflight; writes only an explicitly named contract output."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import GovernanceError, InputError
from .preflight.engine import run_preflight
from .schema_loader import load_mapping
from .serialization import dump_mapping, normalize_format


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a deterministic governance TaskContract")
    parser.add_argument("--task-file", required=True, type=Path)
    parser.add_argument("--project-state-file", required=True, type=Path)
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--format", choices=("yaml", "json"))
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.output_file and args.output_file.exists() and not args.force:
            raise InputError(f"Output exists; use --force to overwrite: {args.output_file}")
        if args.output_file and args.output_file.resolve() in {args.task_file.resolve(), args.project_state_file.resolve()}:
            raise InputError("Output file must not overwrite an input file")
        task_value, state_value = load_mapping(args.task_file), load_mapping(args.project_state_file)
        if "objective" in task_value and state_value.get("lifecycle_stage") in {"ACTIVATED_NOT_PREFLIGHTED", "PREFLIGHT_PASSED", "GUARDED", "TEST_PLANNED", "TEST_EXECUTED", "VERIFIED", "CLOSED"}:
            raise InputError("USE_ADOPTION_LIFECYCLE_BRIDGE: run scripts/agent_adopt.py adoption-preflight")
        result = run_preflight(task_value, state_value)
        output = dump_mapping(result.contract.to_mapping(), normalize_format(args.format, str(args.output_file) if args.output_file else None))
        if args.output_file:
            args.output_file.parent.mkdir(parents=True, exist_ok=True)
            args.output_file.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
        if not args.quiet:
            risks = ", ".join(result.risks.kinds) or "none"
            target = str(args.output_file) if args.output_file else "stdout"
            print(f"Preflight: {result.contract.status}\nTask level: {result.classification.task_level}\nProject mode: {result.contract.project_mode}\nRisks: {risks}\nRead scope: {len(result.contract.read_scope)} paths\nWrite scope: {len(result.contract.write_scope['allow'])} paths\nContract: {target}", file=sys.stderr)
        return result.exit_status
    except GovernanceError as exc:
        print(f"Preflight error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
