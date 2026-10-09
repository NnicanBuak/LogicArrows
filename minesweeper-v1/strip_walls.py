"""Use the common wall rule while retaining the module's reserved footprint."""
from snap import *
from native_rules import remove_passive_walls


def build(source='experiments/serial-80/cell',stem='releases/serial-80/cell'):
    old=read_map(BUILD/(source+'.save.txt'));meta=json.loads((BUILD/(source+'.layout.json')).read_text())
    cells=remove_passive_walls(old)
    meta.update(cells=len(cells),map_hash=map_hash(cells),passive_walls_removed=len(old)-len(cells),
                reserved_module_footprint=True)
    meta.update(write_map(BUILD,stem,cells,None));write_json(BUILD/(stem+'.layout.json'),meta)
    write_json(BUILD/(stem+'.logic.json'),json.loads((BUILD/(source+'.logic.json')).read_text()))
    print('Removed inert walls:',len(old)-len(cells),'arrows;',len(cells),'remaining',flush=True)
    return meta


if __name__=='__main__':build()
