import subprocess,sys,tempfile,unittest
from pathlib import Path
import yaml

SOURCE=Path(__file__).resolve().parents[2]; GUARD=SOURCE/'scripts/agent_guard.py'
CONTRACT={'schema_version':'1.0','task_id':'T','project_mode':'EXECUTION','task_level':'B','status':'READY','objective':['local change'],'read_scope':['src/'],'write_scope':{'allow':['src/'],'deny':['data/production/**']},'autonomy':{'may_debug_test_failures':True,'may_edit_adjacent_tests':True,'may_edit_same_module_helpers':'conditional','must_not_expand_architecture':True},'stop_conditions':[],'verification':{'level_1':[],'level_2':[],'level_3':[]},'report':{'format':'compact','fields':['tests']}}
STATE={'schema_version':'1.0','project_mode':'EXECUTION','architecture_status':'confirmed','implementation_plan_status':'confirmed','repository_root':'.','adapter':'generic','high_risk_paths':[],'default_forbidden_operations':[]}
class P2AcceptanceMatrix(unittest.TestCase):
 def setup(self):
  d=tempfile.TemporaryDirectory(); root=Path(d.name); subprocess.run(['git','init','-b','main'],cwd=root,check=True,capture_output=True); subprocess.run(['git','config','user.email','test@example.invalid'],cwd=root,check=True);subprocess.run(['git','config','user.name','Test'],cwd=root,check=True);(root/'.gitignore').write_text('.agent_state/\n');subprocess.run(['git','add','.gitignore'],cwd=root,check=True);subprocess.run(['git','commit','-m','init'],cwd=root,check=True,capture_output=True); state=root/'.agent_state';state.mkdir();(state/'project_state.yaml').write_text(yaml.safe_dump(STATE));(state/'active_task.yaml').write_text(yaml.safe_dump(CONTRACT));return d,root
 def guard(self,root): return subprocess.run([sys.executable,str(GUARD),'check'],cwd=root,text=True,capture_output=True)
 def test_four_statuses(self):
  d,r=self.setup(); self.assertEqual(0,self.guard(r).returncode); (r/'tests').mkdir();(r/'tests/a.py').write_text('x');self.assertEqual(2,self.guard(r).returncode);(r/'data/production').mkdir(parents=True);(r/'data/production/a').write_text('x');self.assertEqual(3,self.guard(r).returncode);(r/'.agent_state/active_task.yaml').unlink();self.assertEqual(1,self.guard(r).returncode);d.cleanup()
 def test_missing_approval_blocks(self):
  d,r=self.setup(); c=dict(CONTRACT);c['objective']=['Call API'];c['governance']={'effect_type':'external_access','effect_scope':{}};(r/'.agent_state/active_task.yaml').write_text(yaml.safe_dump(c));self.assertEqual(3,self.guard(r).returncode);d.cleanup()
