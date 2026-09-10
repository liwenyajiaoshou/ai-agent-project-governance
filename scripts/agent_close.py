from pathlib import Path
import sys,yaml,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from governance.verification.closure_evaluator import close
from governance.state import store, layout
from governance.verification.report_builder import write
from governance.verification.repair_boundary import evaluate
p=argparse.ArgumentParser();p.add_argument('--repair-action', choices=('fixture','helper','mock','test_isolation','schema_fix','report_correction','network','external_api','formal_data_write','git_integration','release','scope_expansion','risk_escalation'));x=p.parse_args()
s=Path.cwd()/'.agent_state';v=yaml.safe_load((s/'verification_result.yaml').read_text(encoding='utf-8'));contract=store.active();guard=yaml.safe_load((s/'last_guard_result.yaml').read_text(encoding='utf-8'));boundary=evaluate(contract,guard,v,x.repair_action);c=close(v,repair_boundary=boundary);c['report_path']=write(Path.cwd(),v['task_id'],v,c);store.save_p3(layout.CLOSURE, c, 'closure_result.schema.json');print(yaml.safe_dump(c,sort_keys=False));raise SystemExit({'CLOSED':0,'PARTIAL':2,'BLOCKED':3,'FAILED':4}[c['status']])
