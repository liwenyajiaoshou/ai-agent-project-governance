from pathlib import Path
import argparse, sys
SOURCE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(SOURCE))
from governance.state import store, layout
from governance.state.fingerprint import build, git
from governance.guards.git_status import changed_paths
from governance.guards.scope_guard import check as scope_check
from governance.guards.forbidden_operation_guard import check as forbidden_check
from governance.guards.state_guard import check as state_check
from governance.guards.approval_guard import effect_authorization
from governance.guards.result_builder import build as result_build
from governance.schema_loader import validate_mapping
from governance.serialization import dump_mapping

p=argparse.ArgumentParser();p.add_argument("command",nargs="?",default="check",choices=("check",));p.add_argument("--output-file",type=Path);x=p.parse_args();repo=Path.cwd()
try:
 state_status,reasons=state_check()
 if state_status != "OK": raise RuntimeError("state invalid")
 contract=store.active(); paths=changed_paths(repo); fingerprint=build(repo,contract["task_id"],contract)
 authorization=effect_authorization(contract,fingerprint); approval=authorization["status"]
 forbidden,why=forbidden_check(contract,paths); reasons+=why
 groups=scope_check(contract,paths)
 result=result_build(contract,repo,git(repo,["branch","--show-current"]),git(repo,["rev-parse","HEAD"]),paths,groups,approval,state_status,forbidden,reasons,authorization)
 validate_mapping(result,"guard_result.schema.json")
 store.save_p3(layout.LAST_GUARD, result, "guard_result.schema.json")
 output=dump_mapping(result,"yaml")
 if x.output_file:
  if x.output_file.exists(): raise ValueError("output exists")
  x.output_file.parent.mkdir(parents=True,exist_ok=True);x.output_file.write_text(output,encoding="utf-8")
 else: print(output,end="")
 raise SystemExit({"PASS":0,"WARN":2,"BLOCKED":3}[result["status"]])
except Exception as exc:
 print(f"Guard ERROR: {exc}",file=sys.stderr);raise SystemExit(1)
