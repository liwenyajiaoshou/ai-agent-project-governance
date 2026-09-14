"""Read-only validation for the governance runtime P0 baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import yaml
    from jsonschema import Draft202012Validator
except ModuleNotFoundError as exc:
    print("Missing validation dependency. Run: python -m pip install -r requirements-governance.txt")
    raise SystemExit(2) from exc


CORE_PATHS = (
    "docs/GOVERNANCE_RUNTIME_ARCHITECTURE.md",
    "docs/GOVERNANCE_RUNTIME_MODULE_REGISTRY.yaml",
    "docs/ADR/ADR-0001-DETERMINISTIC-GOVERNANCE-RUNTIME.md",
    "schemas/task_request.schema.json",
    "schemas/project_state.schema.json",
    "schemas/approval.schema.json",
    "schemas/task_contract.schema.json",
    "schemas/verification_result.schema.json",
    "schemas/governance_module_registry.schema.json",
    "schemas/rules_index.schema.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate governance runtime P0 baseline")
    parser.add_argument("--root", type=Path, help="Repository-root override for isolated tests")
    return parser.parse_args()


def repository_root(args: argparse.Namespace) -> Path:
    return (args.root if args.root else Path(__file__).resolve().parents[1]).resolve()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def template_fallback(path: Path) -> Path:
    return path.with_name(f"{path.stem}.template{path.suffix}")


def path_exists(root: Path, reference: str) -> bool:
    path = root / reference
    return path.exists() or template_fallback(path).exists()


def iter_references(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [item for child in value.values() for item in iter_references(child)]
    if isinstance(value, list):
        return [item for child in value for item in iter_references(child)]
    if isinstance(value, str) and value.startswith(("agent_rules/", "docs/", "schemas/")):
        return [value]
    return []


def validate_schemas(root: Path, errors: list[str]) -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    ids: set[str] = set()
    for path in sorted((root / "schemas").glob("*.schema.json")):
        try:
            schema = load_json(path)
            Draft202012Validator.check_schema(schema)
            for key in ("$schema", "$id", "title", "description", "type"):
                if key not in schema:
                    errors.append(f"Schema metadata missing: {path.relative_to(root)}: {key}")
            if schema.get("type") != "object":
                errors.append(f"Schema root must be object: {path.relative_to(root)}")
            if schema.get("$id") in ids:
                errors.append(f"Duplicate schema $id: {schema.get('$id')}")
            ids.add(schema.get("$id", ""))
            schemas[path.name] = schema
        except (OSError, ValueError) as exc:
            errors.append(f"Cannot load schema {path.relative_to(root)}: {exc}")
        except Exception as exc:
            errors.append(f"Invalid schema {path.relative_to(root)}: {exc}")
    if len(schemas) != 45:
        errors.append(f"Expected 45 schemas, found {len(schemas)}")
    return schemas


def validate_documents(root: Path, errors: list[str]) -> None:
    for relative in CORE_PATHS:
        if not (root / relative).is_file():
            errors.append(f"Required baseline file missing: {relative}")


def validate_yaml_contracts(root: Path, schemas: dict[str, dict[str, Any]], errors: list[str]) -> None:
    try:
        rules_index = load_yaml(root / "agent_rules/RULES_INDEX.yaml")
        Draft202012Validator(schemas["rules_index.schema.json"]).validate(rules_index)
        for reference in iter_references(rules_index):
            if not path_exists(root, reference):
                errors.append(f"Unresolved RULES_INDEX reference: {reference}")
    except Exception as exc:
        errors.append(f"RULES_INDEX validation failed: {exc}")
    try:
        registry = load_yaml(root / "docs/GOVERNANCE_RUNTIME_MODULE_REGISTRY.yaml")
        Draft202012Validator(schemas["governance_module_registry.schema.json"]).validate(registry)
        for module_name, module in registry["modules"].items():
            for reference in module["paths"]:
                if reference != ".agent_state/" and not (root / reference).exists():
                    errors.append(f"Unresolved module path ({module_name}): {reference}")
    except Exception as exc:
        errors.append(f"Module registry validation failed: {exc}")
    try:
        runtime = rules_index["governance_runtime"]
        architecture = (root / runtime["architecture"]).read_text(encoding="utf-8")
        if runtime["phase"] not in architecture:
            errors.append("Runtime phase is not recorded in architecture")
        workflow = root / ".github/workflows/governance-ci.yml"
        if bool(runtime.get("ci_enabled")) != workflow.is_file():
            errors.append("CI enabled flag and workflow presence differ")
        if runtime.get("phase") == "PHASE_6_MULTI_AGENT_ORCHESTRATION" and runtime.get("multi_agent_enabled") is not True:
            errors.append("P6 requires multi-agent enabled")
    except Exception as exc:
        errors.append(f"Runtime metadata validation failed: {exc}")


def main() -> int:
    root = repository_root(parse_args())
    errors: list[str] = []
    if not root.is_dir():
        print(f"Repository root not found: {root}")
        return 2
    validate_documents(root, errors)
    schemas = validate_schemas(root, errors)
    if len(schemas) == 45:
        validate_yaml_contracts(root, schemas, errors)
    if errors:
        print(f"Governance baseline validation: FAIL ({len(errors)} issue(s))")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Governance baseline validation: PASS (45 schemas, rules index, module registry, references)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
