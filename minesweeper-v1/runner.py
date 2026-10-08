"""Existing GraphDLC engine, with a project-local 2M node/tick CLI budget."""
import json,os,subprocess
from logic import ROOT,HERE
from pathlib import Path

def build_runner():
    # The project keeps its 2M-budget CLI source. Rebuilding must not copy
    # unrelated, possibly uncommitted changes from the shared compiler.
    subprocess.run(['cargo','build','--release','--manifest-path',str(HERE/'native/Cargo.toml')],check=True)

def simulate(cells,scenario,optimize_cycles=False,timeout=180):
    binary=HERE/'native/target/release'/('minesweeper-arrows-cli.exe' if os.name=='nt' else 'minesweeper-arrows-cli')
    if not binary.is_file():build_runner()
    request={'cells':[dict(x=x,y=y,type=c.type,rotation=c.rotation,mirrored=c.mirrored) for (x,y),c in sorted(cells.items())],
             'test':scenario,'optimize_cycles':optimize_cycles}
    graph=subprocess.run(['node',str(ROOT/'ArrowsHDL/src/compile-graph.mjs')],input=json.dumps(request),capture_output=True,text=True,encoding='utf-8',timeout=timeout)
    if graph.returncode:raise RuntimeError(graph.stderr)
    report=subprocess.run([str(binary)],input=graph.stdout,capture_output=True,text=True,encoding='utf-8',timeout=timeout)
    if report.returncode not in (0,1):raise RuntimeError(report.stderr)
    return json.loads(report.stdout)
