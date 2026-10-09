"""Game-specific binding policy; native templates belong to ArrowsHDL."""
from logic import ROOT
from native_macros import *
from native_macros import adder_groups as _adder_groups, edge_groups as _edge_groups


def adder_groups(graph, scope_prefix='count/'):
    return _adder_groups(graph, scope_prefix)


def edge_groups(graph):
    columns={n['output'] for n in graph['nodes'] if n['output'].startswith('port:display:')}
    return _edge_groups(graph, columns)
