"""Launch the ASM 3DEditor build with a 24x13 terminal."""
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
command = [
    sys.executable,
    str(ROOT / 'emulator' / 'run.py'),
    str(ROOT / '3deditor-terminal' / '3deditor-terminal.asm'),
    '--terminal-size', '24x13',
    '--hide-display',
    *sys.argv[1:],
]
raise SystemExit(subprocess.call(command, cwd=ROOT))
