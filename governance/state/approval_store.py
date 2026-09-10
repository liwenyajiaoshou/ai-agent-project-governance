from __future__ import annotations
import hashlib
import json
import yaml
from ..schema_loader import validate_mapping
from . import layout
from .atomic_writer import write

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

def load():
    if not layout.APPROVALS.exists(): return []
    values=yaml.safe_load(layout.APPROVALS.read_text(encoding="utf-8")) or []
    for value in values: validate_mapping(value,"approval.schema.json")
    return values

def save(values):
    for value in values: validate_mapping(value,"approval.schema.json")
    write(layout.APPROVALS,yaml.safe_dump(values,allow_unicode=True,sort_keys=False))

def add(value):
    validate_mapping(value,"approval.schema.json"); values=load(); values.append(value); save(values)

def expire(approval_id):
    values=load(); found=False
    for value in values:
        if value["approval_id"]==approval_id: value["status"]="expired"; found=True
    if not found: raise ValueError("approval not found")
    save(values)
