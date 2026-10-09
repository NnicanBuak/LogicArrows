"""Use the shared GraphDLC engine with an explicit project resource budget."""
from logic import ROOT
from simulation import build_runner, runner_binary, simulate as _simulate


def simulate(cells, scenario, optimize_cycles=False, timeout=180):
    if not runner_binary().is_file():
        build_runner()
    return _simulate(cells, scenario, optimize_cycles, timeout,
                     limits={'nodes': 2_000_000, 'ticks': 2_000_000})
