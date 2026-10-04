"""Launch the high-resolution terminal-rendered 3DEditor."""
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
command = [
    sys.executable,
    str(ROOT / 'emulator' / 'run.py'),
    str(ROOT / '3deditor' / '3deditor.asm'),
    '--terminal-size', '24x9',
    '--hide-display',
    '--terminal-renderer', str(ROOT / '3deditor-terminal' / 'renderer.py'),
    *sys.argv[1:],
]
raise SystemExit(subprocess.call(command, cwd=ROOT))
