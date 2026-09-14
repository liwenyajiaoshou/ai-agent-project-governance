"""Create and operate bounded, local existing-project adoption artifacts."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from governance.adoption import assess_rollback, build_plan, compile_runtime_bundle, export_drafts, install_approved, rollback_install, render_json, render_markdown  # noqa: E402
from governance.adoption.c0_scanner import scan_directory_for_c0
from governance.adoption.approval_candidate import approve_install_candidate, build_approval_candidate, write_approval_candidate  # noqa: E402
from governance.adoption.exporter import confirmation_candidate  # noqa: E402
from governance.adoption.io import write_bytes_exclusive, write_json_exclusive, write_text_exclusive, write_yaml_exclusive  # noqa: E402
from governance.adoption.provenance import PUBLIC_GENERATION_PATH  # noqa: E402
from governance.schema_loader import load_mapping, validate_mapping  # noqa: E402
from governance.adoption.recovery import compile_contract_recovery, recover_approved  # noqa: E402
from governance.adoption.lifecycle_context import build_lifecycle_context, run_adoption_preflight  # noqa: E402
from governance.adoption.lifecycle import transition_project_state  # noqa: E402
from governance.adoption.evidence_registry import upstream_digests  # noqa: E402
from governance.adoption.runtime_artifact_compiler import digest_bytes  # noqa: E402
from governance.adoption.installer import digest  # noqa: E402
from governance.adoption.framework_upgrade import (  # noqa: E402
    approve_pre_release_generated_template_upgrade,
    compile_framework_upgrade,
    compile_pre_release_generated_template_upgrade,
    install_framework_upgrade,
    install_pre_release_generated_template_upgrade,
    preflight_pre_release_generated_template_upgrade,
)


COMMANDS = {
    "dry-run": "Analyze an existing project without writing to the target.",
    "confirmation-candidate": "Create an external review candidate without inventing owner approval.",
    "export-drafts": "Export adoption drafts and confirmation artifacts outside the target.",
    "compile-runtime-artifacts": "Compile approved drafts into external Runtime preview artifacts.",
    "approval-candidate": "Create an unapproved exact-byte installation candidate for Owner review.",
    "approve-install-candidate": "Record an explicit Owner install decision for an unchanged candidate.",
    "install-approved": "Install exact approved Runtime artifact bytes without activation.",
    "assess-rollback": "Produce a read-only manual recovery assessment.",
    "rollback-install": "Reject automatic rollback and explain the manual-only boundary.",
    "compile-contract-recovery": "Compile an exact activated-Runtime recovery candidate.",
    "approve-contract-recovery": "Record explicit Owner approval for one unchanged recovery candidate.",
    "recover-approved": "Atomically bind an approved successor TaskContract.",
    "adoption-preflight": "Run the canonical adoption-aware preflight and lifecycle transition.",
    "compile-framework-upgrade": "Preview the bounded v1.5.1-to-v1.5.2 changed-only framework upgrade.",
    "approve-framework-upgrade": "Record explicit Owner approval for one upgrade preview.",
    "upgrade-approved": "Install one exact approved changed-only framework upgrade.",
    "compile-pre-release-template-upgrade": "Preview the exact v1.5.2 generated-template schema repair.",
    "approve-pre-release-template-upgrade": "Record explicit Owner approval for one template-repair preview.",
    "preflight-pre-release-template-upgrade": "Verify an approved template-repair writeset without writing.",
    "upgrade-pre-release-template-approved": "Install one preflighted exact generated-template repair.",
}


def _add_dry_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root", type=Path, default=argparse.SUPPRESS, help="Existing local project to inspect (required)")
    parser.add_argument("--format", choices=("markdown", "json"), default=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path, default=argparse.SUPPRESS, help="Explicit output path outside --project-root; stdout by default")
    parser.add_argument("--scope-file", type=Path, default=argparse.SUPPRESS, help="Explicit scope input configuration (JSON/YAML) for active development.")
    parser.add_argument("--scope-copy-output", type=Path, default=argparse.SUPPRESS, help="Optional external byte-identical copy of the formal scope input.")
    parser.add_argument("--provenance-output", type=Path, default=argparse.SUPPRESS, help="Optional external standalone provenance receipt.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Use bounded local Existing Project Adoption commands.",
        epilog="All commands are local-only. They do not authorize network, Git writes, production actions, or deployment.",
    )
    # Keep the original `--project-root ... dry-run` ordering compatible while
    # also showing the dry-run parameters in subcommand help.
    _add_dry_run_arguments(parser)
    subcommands = parser.add_subparsers(dest="command", required=True, title="commands")
    dry_run = subcommands.add_parser("dry-run", help=COMMANDS["dry-run"], description=COMMANDS["dry-run"])
    _add_dry_run_arguments(dry_run)

    candidate = subcommands.add_parser("confirmation-candidate", help=COMMANDS["confirmation-candidate"], description=COMMANDS["confirmation-candidate"])
    candidate.add_argument("--plan", type=Path, required=True)
    candidate.add_argument("--output", type=Path, required=True)
    candidate.add_argument("--target-project-root", type=Path, required=True)
    candidate.add_argument("--confirm-owner", action="store_true", help="Explicitly record caller-supplied Owner confirmation; never used for Preview generation.")

    export = subcommands.add_parser("export-drafts", help=COMMANDS["export-drafts"], description=COMMANDS["export-drafts"])
    export.add_argument("--plan", type=Path, required=True)
    export.add_argument("--confirmations", type=Path, required=True)
    export.add_argument("--output-dir", type=Path, required=True)
    export.add_argument("--target-project-root", type=Path, required=True, help="Used only to reject target-project output paths")

    compile_artifacts = subcommands.add_parser("compile-runtime-artifacts", help=COMMANDS["compile-runtime-artifacts"], description=COMMANDS["compile-runtime-artifacts"])
    compile_artifacts.add_argument("--plan", type=Path, required=True)
    compile_artifacts.add_argument("--confirmations", type=Path, required=True)
    compile_artifacts.add_argument("--draft-bundle", type=Path, required=True)
    compile_artifacts.add_argument("--output-dir", type=Path, required=True)
    compile_artifacts.add_argument("--target-project-root", type=Path, required=True, help="Used only to reject target-project output paths")

    approval_candidate = subcommands.add_parser("approval-candidate", help=COMMANDS["approval-candidate"], description=COMMANDS["approval-candidate"])
    approval_candidate.add_argument("--plan", type=Path, required=True)
    approval_candidate.add_argument("--confirmations", type=Path, required=True)
    approval_candidate.add_argument("--draft-bundle", type=Path, required=True)
    approval_candidate.add_argument("--runtime-artifact-bundle", type=Path, required=True)
    approval_candidate.add_argument("--target-project-root", type=Path, required=True)
    approval_candidate.add_argument("--output", type=Path, required=True)

    approve_candidate = subcommands.add_parser("approve-install-candidate", help=COMMANDS["approve-install-candidate"], description=COMMANDS["approve-install-candidate"])
    approve_candidate.add_argument("--candidate", type=Path, required=True)
    approve_candidate.add_argument("--output", type=Path, required=True)
    approve_candidate.add_argument("--target-project-root", type=Path, required=True)
    approve_candidate.add_argument("--owner-approved", action="store_true", required=True)

    install = subcommands.add_parser("install-approved", help=COMMANDS["install-approved"], description="Install exact approved Runtime artifact bytes. It does not activate state or run lifecycle steps.")
    install.add_argument("--target-project-root", type=Path, required=True)
    install.add_argument("--draft-bundle", type=Path, required=True)
    install.add_argument("--runtime-artifact-bundle", type=Path, required=True)
    install.add_argument("--final-approval", type=Path, required=True)
    install.add_argument("--receipt-output", type=Path, required=True)
    install.add_argument("--plan", type=Path, required=True)
    install.add_argument("--confirmations", type=Path, required=True)

    assessment = subcommands.add_parser("assess-rollback", help=COMMANDS["assess-rollback"], description="Produce a read-only manual recovery assessment; it never deletes target files.")
    assessment.add_argument("--target-project-root", type=Path, required=True)
    assessment.add_argument("--installation-receipt", type=Path, required=True)
    assessment.add_argument("--output", type=Path, required=True)

    rollback = subcommands.add_parser("rollback-install", help=COMMANDS["rollback-install"], description="Automatic rollback is unsupported; this command never deletes target files.")
    rollback.add_argument("--target-project-root", type=Path, required=True)
    rollback.add_argument("--installation-receipt", type=Path, required=True)
    rollback.add_argument("--rollback-approval", type=Path, required=True)

    recovery = subcommands.add_parser("compile-contract-recovery", help=COMMANDS["compile-contract-recovery"])
    recovery.add_argument("--target-project-root", type=Path, required=True)
    recovery.add_argument("--successor-task", type=Path, required=True)
    recovery.add_argument("--installation-receipt", type=Path, required=True); recovery.add_argument("--activation-receipt", type=Path, required=True)
    recovery.add_argument("--output", type=Path, required=True)
    recovery_approval = subcommands.add_parser("approve-contract-recovery", help=COMMANDS["approve-contract-recovery"])
    recovery_approval.add_argument("--candidate", type=Path, required=True)
    recovery_approval.add_argument("--output", type=Path, required=True)
    recovery_approval.add_argument("--owner-approved", action="store_true", required=True)
    recover = subcommands.add_parser("recover-approved", help=COMMANDS["recover-approved"])
    recover.add_argument("--target-project-root", type=Path, required=True)
    recover.add_argument("--manifest", type=Path, required=True); recover.add_argument("--approval", type=Path, required=True)
    recover.add_argument("--installation-receipt", type=Path, required=True); recover.add_argument("--activation-receipt", type=Path, required=True)
    recover.add_argument("--evidence-output", type=Path, required=True)
    preflight = subcommands.add_parser("adoption-preflight", help=COMMANDS["adoption-preflight"])
    for name in ("installation-receipt", "activation-receipt", "runtime-artifact-manifest", "final-install-approval", "activation-approval", "confirmation", "plan"):
        preflight.add_argument(f"--{name}", type=Path, required=True)
    preflight.add_argument("--target-project-root", type=Path, required=True)
    preflight.add_argument("--evidence-output", type=Path, required=True)
    upgrade = subcommands.add_parser("compile-framework-upgrade", help=COMMANDS["compile-framework-upgrade"])
    upgrade.add_argument("--source-root", type=Path, required=True); upgrade.add_argument("--target-project-root", type=Path, required=True); upgrade.add_argument("--output", type=Path, required=True)
    upgrade_approval = subcommands.add_parser("approve-framework-upgrade", help=COMMANDS["approve-framework-upgrade"])
    upgrade_approval.add_argument("--candidate", type=Path, required=True); upgrade_approval.add_argument("--output", type=Path, required=True); upgrade_approval.add_argument("--owner-approved", action="store_true", required=True)
    upgrade_install = subcommands.add_parser("upgrade-approved", help=COMMANDS["upgrade-approved"])
    upgrade_install.add_argument("--source-root", type=Path, required=True); upgrade_install.add_argument("--target-project-root", type=Path, required=True); upgrade_install.add_argument("--manifest", type=Path, required=True); upgrade_install.add_argument("--approval", type=Path, required=True); upgrade_install.add_argument("--receipt-output", type=Path, required=True)
    template_upgrade = subcommands.add_parser("compile-pre-release-template-upgrade", help=COMMANDS["compile-pre-release-template-upgrade"])
    template_upgrade.add_argument("--source-root", type=Path, required=True); template_upgrade.add_argument("--target-project-root", type=Path, required=True); template_upgrade.add_argument("--output", type=Path, required=True)
    template_approval = subcommands.add_parser("approve-pre-release-template-upgrade", help=COMMANDS["approve-pre-release-template-upgrade"])
    template_approval.add_argument("--candidate", type=Path, required=True); template_approval.add_argument("--output", type=Path, required=True); template_approval.add_argument("--owner-approved", action="store_true", required=True)
    template_preflight = subcommands.add_parser("preflight-pre-release-template-upgrade", help=COMMANDS["preflight-pre-release-template-upgrade"])
    template_preflight.add_argument("--target-project-root", type=Path, required=True); template_preflight.add_argument("--manifest", type=Path, required=True); template_preflight.add_argument("--approval", type=Path, required=True); template_preflight.add_argument("--output", type=Path, required=True)
    template_install = subcommands.add_parser("upgrade-pre-release-template-approved", help=COMMANDS["upgrade-pre-release-template-approved"])
    template_install.add_argument("--source-root", type=Path, required=True); template_install.add_argument("--target-project-root", type=Path, required=True); template_install.add_argument("--manifest", type=Path, required=True); template_install.add_argument("--approval", type=Path, required=True); template_install.add_argument("--preflight", type=Path, required=True); template_install.add_argument("--receipt-output", type=Path, required=True)
    return parser


def _output_path(root: Path, output: Path) -> Path:
    destination = output.expanduser().resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        return destination
    raise ValueError("--output must be outside --project-root; target-project writes are forbidden")


def _dry_run(args: argparse.Namespace, parser: argparse.ArgumentParser, provenance_source_root: Path | None = None) -> None:
    if not getattr(args, "project_root", None):
        parser.error("dry-run requires --project-root")
    root = args.project_root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"--project-root must be an existing directory: {args.project_root}")
    scope_file = getattr(args, "scope_file", None)
    if scope_file:
        scope_file = scope_file.expanduser().resolve()
        if not scope_file.is_file():
            raise ValueError(f"--scope-file must be an existing file: {scope_file}")
    plan = build_plan(root, scope_file=scope_file, generation_path=PUBLIC_GENERATION_PATH, provenance_source_root=provenance_source_root)
    rendered = render_markdown(plan) if getattr(args, "format", "markdown") == "markdown" else render_json(plan)
    if getattr(args, "output", None):
        destination = _output_path(root, args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            write_text_exclusive(destination, rendered)

            # Scan the created file for C0
            from governance.adoption.c0_scanner import scan_file_for_c0
            errors = scan_file_for_c0(destination)
            if errors:
                for err in errors:
                    print(f"HANDOFF_ERROR: {err}", file=sys.stderr)
                raise ValueError("HANDOFF_READY_FAILED_C0_SCAN")
        except FileExistsError:
            raise ValueError("--output already exists; refusing to overwrite it")
    else:
        sys.stdout.write(rendered)
    if getattr(args, "scope_copy_output", None):
        if scope_file is None:
            raise ValueError("--scope-copy-output requires --scope-file")
        write_bytes_exclusive(_output_path(root, args.scope_copy_output), scope_file.read_bytes())
    if getattr(args, "provenance_output", None):
        write_json_exclusive(_output_path(root, args.provenance_output), plan["provenance_receipt"])


def _confirmation_candidate(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    target = args.target_project_root.expanduser().resolve(strict=True)
    plan = load_mapping(args.plan)
    value = confirmation_candidate(plan, confirmed_by_user=args.confirm_owner)
    write_yaml_exclusive(_output_path(target, args.output), value)


def _export_drafts(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    export_drafts(args.plan, args.confirmations, args.output_dir, args.target_project_root)
    errors = scan_directory_for_c0(args.output_dir)
    if errors:
        for err in errors:
            print(f"HANDOFF_ERROR: {err}", file=sys.stderr)
        raise ValueError("HANDOFF_READY_FAILED_C0_SCAN")

def _compile_runtime_artifacts(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    compile_runtime_bundle(args.plan, args.confirmations, args.draft_bundle, args.output_dir, args.target_project_root)


def _approval_candidate(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    target = args.target_project_root.expanduser().resolve(strict=True)
    value = build_approval_candidate(
        plan_path=args.plan,
        confirmation_path=args.confirmations,
        draft_bundle=args.draft_bundle,
        runtime_bundle=args.runtime_artifact_bundle,
        target_root=target,
    )
    write_approval_candidate(_output_path(target, args.output), value)


def _approve_install_candidate(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    target = args.target_project_root.expanduser().resolve(strict=True)
    if not args.owner_approved:
        raise ValueError("explicit --owner-approved is required")
    write_yaml_exclusive(_output_path(target, args.output), approve_install_candidate(args.candidate))


def _install_approved(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    install_approved(args.target_project_root, args.draft_bundle, args.runtime_artifact_bundle, args.final_approval, args.receipt_output, args.plan, args.confirmations)


def _assess_rollback(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    assess_rollback(args.target_project_root, args.installation_receipt, args.output)


def _rollback_install(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    rollback_install(args.target_project_root, args.installation_receipt, args.rollback_approval)

def _compile_contract_recovery(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    compile_contract_recovery(args.target_project_root, args.successor_task, args.installation_receipt, args.activation_receipt, _output_path(args.target_project_root.resolve(strict=True), args.output))

def _approve_contract_recovery(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    manifest = load_mapping(args.candidate)
    now = datetime.now(timezone.utc)
    approval = {"schema_version":"1.0", "approved_by_user":True, "approved_action":"RECOVER_ACTIVATED_TASK_CONTRACT", "approved_at":now.isoformat(), "expires_at":(now + timedelta(hours=1)).isoformat(), "target_identity_digest":manifest["target_identity_digest"], "manifest_digest":manifest["manifest_digest"], "approved_writeset":manifest["writeset"], "approved_scope_delta":manifest["scope_delta"]}
    validate_mapping(approval, "adoption_recovery_approval.schema.json")
    write_json_exclusive(args.output, approval)

def _recover_approved(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    recover_approved(args.target_project_root, args.manifest, args.approval, args.installation_receipt, args.activation_receipt, args.evidence_output)

def _adoption_preflight(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    target = args.target_project_root.resolve(strict=True); task, state = target / "task.yaml", target / "project_state.yaml"
    context = build_lifecycle_context(target, task, state, args.installation_receipt, args.activation_receipt, runtime_artifact_manifest=args.runtime_artifact_manifest, final_install_approval=args.final_install_approval, activation_approval=args.activation_approval, confirmation=args.confirmation, plan=args.plan)
    result = run_adoption_preflight(context, task, state)
    state_value = load_mapping(state)
    evidence = {"schema_version":"1.0", "evidence_type":"PreflightEvidence", "status":"PASS", "target_identity_digest":context.target_identity_digest, "previous_state_digest":digest_bytes(state.read_bytes()), "upstream_evidence_digests":upstream_digests(state_value), "payload":result}
    write_json_exclusive(args.evidence_output, evidence)
    transition_project_state(state, expected_current_stage="ACTIVATED_NOT_PREFLIGHTED", expected_current_state_digest=digest_bytes(state.read_bytes()), evidence_path=args.evidence_output, requested_next_stage="PREFLIGHT_PASSED", target_identity_digest=context.target_identity_digest)
    print("PREFLIGHT_PASSED next_safe_action=agent_guard")

def _compile_framework_upgrade(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    compile_framework_upgrade(args.source_root, args.target_project_root, args.output)

def _approve_framework_upgrade(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    manifest = load_mapping(args.candidate)
    approval = {"schema_version":"1.0", "approved_by_user":True, "approved_action":"UPGRADE_FRAMEWORK_1_5_1_TO_1_5_2", "manifest_digest":manifest["manifest_digest"], "target_identity_digest":manifest["target_identity_digest"], "approved_writeset":manifest["writeset"]}
    validate_mapping(approval, "framework_upgrade_approval.schema.json")
    write_json_exclusive(args.output, approval)

def _upgrade_approved(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    install_framework_upgrade(args.source_root, args.target_project_root, args.manifest, args.approval, args.receipt_output)

def _compile_pre_release_template_upgrade(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    compile_pre_release_generated_template_upgrade(args.source_root, args.target_project_root, args.output)

def _approve_pre_release_template_upgrade(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    if not args.owner_approved:
        raise ValueError("explicit --owner-approved is required")
    write_json_exclusive(args.output, approve_pre_release_generated_template_upgrade(load_mapping(args.candidate)))

def _preflight_pre_release_template_upgrade(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    write_json_exclusive(args.output, preflight_pre_release_generated_template_upgrade(args.target_project_root, args.manifest, args.approval))

def _upgrade_pre_release_template_approved(args: argparse.Namespace, _: argparse.ArgumentParser) -> None:
    install_pre_release_generated_template_upgrade(args.source_root, args.target_project_root, args.manifest, args.approval, args.preflight, args.receipt_output)


HANDLERS = {
    "dry-run": _dry_run,
    "confirmation-candidate": _confirmation_candidate,
    "export-drafts": _export_drafts,
    "compile-runtime-artifacts": _compile_runtime_artifacts,
    "approval-candidate": _approval_candidate,
    "approve-install-candidate": _approve_install_candidate,
    "install-approved": _install_approved,
    "assess-rollback": _assess_rollback,
    "rollback-install": _rollback_install,
    "compile-contract-recovery": _compile_contract_recovery,
    "approve-contract-recovery": _approve_contract_recovery,
    "recover-approved": _recover_approved,
    "adoption-preflight": _adoption_preflight,
    "compile-framework-upgrade": _compile_framework_upgrade,
    "approve-framework-upgrade": _approve_framework_upgrade,
    "upgrade-approved": _upgrade_approved,
    "compile-pre-release-template-upgrade": _compile_pre_release_template_upgrade,
    "approve-pre-release-template-upgrade": _approve_pre_release_template_upgrade,
    "preflight-pre-release-template-upgrade": _preflight_pre_release_template_upgrade,
    "upgrade-pre-release-template-approved": _upgrade_pre_release_template_approved,
}


def main(argv: list[str] | None = None, *, _test_provenance_source_root: Path | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if set(COMMANDS) != set(HANDLERS):  # defensive invariant for future edits
        raise RuntimeError("parser command registry and dispatcher differ")
    try:
        if args.command == "dry-run":
            _dry_run(args, parser, _test_provenance_source_root)
        else:
            HANDLERS[args.command](args, parser)
    except (OSError, ValueError) as exc:
        print(f"[ERROR] Adoption command could not complete: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
