"""Game policy for one global scan and column-only phase distribution.

Graph pruning, placement, routing and simulation remain in ArrowsHDL.
The row-chain has neutral inputs Req=Loss=0, Sat=1 at its beginning.
The header alone computes the game result and broadcasts defeat separately.
"""
from copy import deepcopy
from netlist_optimization import prune_outputs,forward_output_levels,fold_or_trees

H_INPUT=('MP','MC','Z','S','prefixReq','prefixLoss','prefixSat')
H_REVERSE=('MP','MC','Z','S')
V_INPUT=('M','Z','S','choose','sample','ready','stop','defeat','busy')
V_REVERSE=('M','Z','S')


def faces(side,output):
    if side in 'WE':return H_INPUT if (side=='W')!=output else H_REVERSE
    return V_INPUT if (side=='N')!=output else V_REVERSE


def graph_policy(graph):
    result=deepcopy(graph);nodes={n['output']:n for n in result['nodes']}
    request=nodes[result['_states']['request']]
    request_trigger=nodes[request['inputs'][0]]
    guard=next(nodes[net] for net in request_trigger['inputs'] if nodes.get(net,{}).get('op')=='NOT')
    guard['inputs']=['phase:busy']
    chosen=nodes[result['_states']['selected']]
    pending=list(chosen['inputs']);inverters=[];seen=set()
    while pending:
        net=pending.pop()
        if net in seen:continue
        seen.add(net);node=nodes.get(net)
        if not node:continue
        if node['op']=='NOT':inverters.append(node)
        elif node['op'] not in ('SET','TOGGLE'):pending.extend(node['inputs'])
    previous=next(n for n in inverters if n['output']!='edge_delay:choose' and n['inputs']!=['busy'])
    previous['inputs']=['W:prefixReq']
    for field in ('Req','Loss','Sat'):
        terminal=result['outputs']['E:prefix'+field][0]['net']
        prefix=nodes[nodes[terminal]['inputs'][0]]
        local=prefix['inputs'][0]
        prefix['inputs']=[local,'W:prefix'+field]
    for phase in ('choose','sample','ready','stop'):
        nodes['phase:'+phase].update(op='BUF',inputs=['N:'+phase])
    result['inputs']['N:defeat']=[dict(index=0,net='N:defeat')]
    result['nodes'] += [dict(id='phase:defeat',output='phase:defeat',op='BUF',inputs=['N:defeat'],scope='control'),
                        dict(id='port:S:defeat',output='port:S:defeat',op='BUF',inputs=['phase:defeat'],scope='links')]
    result['outputs']['S:defeat']=[dict(index=0,net='port:S:defeat')]
    result['inputs']['N:busy']=[dict(index=0,net='N:busy')]
    result['nodes'].append(dict(id='phase:busy',output='phase:busy',op='BUF',inputs=['N:busy'],scope='control'))
    nodes[result['outputs']['S:busy'][0]['net']]['inputs']=['phase:busy']
    reveal=nodes[nodes[result['outputs']['mine_indicator'][0]['net']]['inputs'][0]]
    reveal['inputs']=[result['_states']['mine'],'phase:defeat']
    result['_states']['busy']='phase:busy'
    dropped=[name for name in result['outputs'] if ':' in name and name.split(':')[0] in 'WENS'
             and name.split(':')[1] not in faces(name[0],True)]
    result=prune_outputs(result,dropped,keep_nets=result['_states'].values())
    branches=[('segment_enable:'+str(i),'segment_delay:'+str(i),'segment_pulse:'+str(i)) for i in range(7)]
    result=forward_output_levels(result,branches)
    result['nodes'].append(dict(id='port:panel_show',output='port:panel_show',op='BUF',inputs=['display_show:west'],scope='links'))
    result['outputs']['panel_show']=[dict(index=0,net='port:panel_show')]
    if result.get('_logic_decoder'):
        for i,raw in enumerate(result['_raw_level_nets']):
            net='port:panel_raw:'+str(i)
            result['nodes'].append(dict(id=net,output=net,op='BUF',inputs=[raw],scope='links'))
            result['outputs']['panel_raw:'+str(i)]=[dict(index=0,net=net)]
    result=prune_outputs(result,['display:'+str(i) for i in range(7)],keep_nets=list(result['_states'].values())+result['_count'])
    result=fold_or_trees(result,max_inputs=7,keep_nets=list(result['_states'].values())+result['_count'])
    result['_serial_control']=dict(scan_order='row-major',neutral=dict(Req=0,Loss=0,Sat=1),
                                  request_contract='header closes request capture before choose; one election',
                                  phase_contract='single permanent level per column, one generation')
    return result
