"""Risk detection from explicit input only; it never scans project files."""

from dataclasses import dataclass
from fnmatch import fnmatch

from ..models.project_state import ProjectState
from ..models.task_request import TaskRequest
from .default_rules import RISK_RULES


@dataclass(frozen=True)
class RiskSummary:
    rule_ids: tuple[str, ...]
    kinds: tuple[str, ...]


def detect_risks(task: TaskRequest, state: ProjectState, code_task: bool) -> RiskSummary:
    text, paths = task.text, task.hints["likely_paths"]
    structured = task.hints.get("risk_hints", {})
    risks: list[str] = []
    no_external = any(phrase in text for phrase in ("no network", "no real api", "do not use api", "不联网", "禁止联网", "不调用真实 api"))
    no_production = any(phrase in text for phrase in ("do not write production data", "do not write production", "不写生产数据", "不写入生产"))
    if task.hints["external_access"] or structured.get("external_access") is True or (not no_external and any(word in text for word in ("real api", "联网", "login", "scrape", "remote call"))):
        risks.append("external")
    if task.hints["production_write"] or structured.get("production_write") is True or (not no_production and any(word in text for word in ("production database", "正式数据库", "production environment", "正式证据库"))):
        risks.append("production")
    if any(word in text for word in ("delete", "overwrite", "clear", "force push", "release", "发布", "删除", "覆盖", "迁移")):
        risks.append("destructive" if "release" not in text and "发布" not in text else "release")
    if any(word in text for word in ("api key", "token", "password", "账号", "密钥")):
        risks.append("secret")
    if code_task and (not paths or all(path.strip() in {"", ".", "./"} for path in paths)):
        risks.append("scope")
    if code_task and any(fnmatch(path, pattern) for path in paths for pattern in state.high_risk_paths):
        risks.append("production")
    if task.governance_context.get("risk_status") == "unknown":
        risks.append("unknown")
    kinds = tuple(sorted(set(risks)))
    return RiskSummary(tuple(RISK_RULES[kind] for kind in kinds), kinds)
