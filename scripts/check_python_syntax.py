"""Compile P5 runtime sources in memory without writing bytecode."""
from __future__ import annotations
import argparse
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]); root=p.parse_args().root.resolve(); errors=[]
 for folder in ("governance", "scripts", "extensions"):
  for path in (root/folder).rglob("*.py"):
   try: compile(path.read_text(encoding="utf-8"),str(path),"exec")
   except (OSError,SyntaxError) as exc: errors.append(f"{path.relative_to(root)}: {exc}")
 if errors: print(f"Python syntax: FAIL ({len(errors)} issue(s))"); print("\n".join(errors)); return 2
 print("Python syntax: PASS (in-memory compilation)"); return 0
if __name__ == "__main__": raise SystemExit(main())
