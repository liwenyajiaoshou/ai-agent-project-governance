from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from governance.schema_loader import validate_mapping
from governance.verification.closure_evaluator import close
from governance.verification.repair_boundary import evaluate
from governance.verification.test_planner import create
from governance.verification.verification_builder import build

ROOT = Path(__file__).resolve().parents[2]

def contract():
 return {"schema_version":"1.0","task_id":"C06","project_mode":"EXECUTION","task_level":"B","status":"READY","objective":["closure"],"read_scope":[],"write_scope":{"allow":["governance/**"],"deny":[]},"autonomy":{"may_debug_test_failures":True,"may_edit_adjacent_tests":True,"may_edit_same_module_helpers":"conditional","must_not_expand_architecture":True},"stop_conditions":[],"verification":{"level_1":["python scripts/validate_governance.py"],"level_2":[],"level_3":[]},"report":{"format":"compact","fields":["tests"]}}

def result(command_id,status,required):
 return {"command_id":command_id,"level":2,"required":required,"status":status,"exit_code":0 if status=="PASS" else 1,"duration_ms":1,"sanitized_stdout_tail":"secret raw tail","sanitized_stderr_tail":"tail","stdout_digest":"a"*64,"stderr_digest":"b"*64,"redaction_count":1,"redaction_rule_version":"1.0"}

class RepairBoundaryTest(unittest.TestCase):
 def verified(self):
  c=contract(); p=create(c,{"status":"PASS"}); return c,build(c,{"status":"PASS"},p,[result("governance_validate","PASS",True),result("quality_gate","PASS",False)])
 def guard(self, **items): return {"status":"PASS","approval_status":"not_required","head_commit":"base",**items}
 def test_no_repair_and_allowed_repair_close(self):
  c,v=self.verified()
  for action in (None,"fixture","helper","mock","test_isolation","schema_fix","report_correction"):
   with self.subTest(action=action):
    b=evaluate(c,self.guard(),v,action); self.assertTrue(b["boundary_valid"]); self.assertEqual("CLOSED",close(v,repair_boundary=b)["status"]); validate_mapping(close(v,repair_boundary=b),"closure_result.schema.json")
 def test_fail_closed_matrix(self):
  c,v=self.verified()
  for action in ("network","external_api","formal_data_write","git_integration","release","scope_expansion","risk_escalation","unknown"):
   with self.subTest(action=action):
    b=evaluate(c,self.guard(),v,action); self.assertFalse(b["boundary_valid"]); self.assertNotEqual("CLOSED",close(v,repair_boundary=b)["status"])
  stale=evaluate(c,self.guard(head_commit=""),v); self.assertEqual("BLOCKED",close(v,repair_boundary=stale)["status"])
  failed=build(c,{"status":"PASS"},create(c,{"status":"PASS"}),[result("governance_validate","FAIL",True)])
  self.assertNotEqual("CLOSED",close(failed,repair_boundary=evaluate(c,self.guard(),failed))["status"])
 def test_public_close_persists_boundary_without_output(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); state=root/".agent_state"; state.mkdir(); c=contract(); p=create(c,{"status":"PASS"})
   (state/"active_task.yaml").write_text(yaml.safe_dump(c),encoding="utf-8"); (state/"last_guard_result.yaml").write_text(yaml.safe_dump(self.guard()),encoding="utf-8"); (state/"test_plan.yaml").write_text(yaml.safe_dump(p),encoding="utf-8"); (state/"test_results.yaml").write_text(yaml.safe_dump([result("governance_validate","PASS",True),result("quality_gate","PASS",False)]),encoding="utf-8")
   self.assertEqual(0,subprocess.run([sys.executable,str(ROOT/"scripts/agent_verify.py")],cwd=root,capture_output=True,text=True).returncode)
   closed=subprocess.run([sys.executable,str(ROOT/"scripts/agent_close.py"),"--repair-action","fixture"],cwd=root,capture_output=True,text=True); self.assertEqual(0,closed.returncode,closed.stderr)
   value=yaml.safe_load((state/"closure_result.yaml").read_text(encoding="utf-8")); validate_mapping(value,"closure_result.schema.json"); self.assertTrue(value["repair_boundary"]["boundary_valid"]); self.assertNotIn("sanitized_stdout_tail",json.dumps(value)); self.assertNotIn("secret raw tail",json.dumps(value))

if __name__=="__main__": unittest.main()
