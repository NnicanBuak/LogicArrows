"""Model persistence for the shared host, GPL-3.0. Moved 2026-10-04."""
import math


def export_model(native):
    c = native.layout['constants']
    memory = native.machine.memory
    ids = [i for i in range(32) if memory[c['VLIVE'] + i]]
    indices = {v: i for i, v in enumerate(ids)}
    vertices = [[native.word(c['VERTICES'] + i * 6 + a * 2) / 16 for a in range(3)] for i in ids]
    edges = [[indices[memory[c['EDGES'] + i * 2 + a]] for a in range(2)] for i in range(64) if memory[c['ELIVE'] + i]]
    faces = [[indices[memory[c['FACES'] + i * 5 + a + 1]] for a in range(memory[c['FACES'] + i * 5])] for i in range(32) if memory[c['FACES'] + i * 5]]
    return dict(format='3DEditor-Q4', vertices=vertices, edges=edges, faces=faces)


def encode_model(model, constants):
    vertices, edges, faces = model['vertices'], model['edges'], model['faces']
    if len(vertices) > 32 or len(edges) > 64 or len(faces) > 32:
        raise ValueError('Model capacity: 32 vertices, 64 edges, 32 faces')
    values = []
    for p in vertices:
        if len(p) != 3:
            raise ValueError('Vertex needs X/Y/Z')
        for v in p:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 11 or v * 16 != round(v * 16):
                raise ValueError('Coordinates must be -11..11 on a 1/16 grid')
            values.append(round(v * 16))
    used = set()
    for e in edges:
        if len(e) != 2 or any(type(v) is not int or not 0 <= v < len(vertices) for v in e) or e[0] == e[1]:
            raise ValueError('Invalid edge')
        key = tuple(sorted(e))
        if key in used:
            raise ValueError('Duplicate edge')
        used.add(key)
    seen_faces = set()
    for f in faces:
        if len(f) not in (3, 4) or any(type(v) is not int or not 0 <= v < len(vertices) for v in f) or len(set(f)) != len(f):
            raise ValueError('Invalid face')
        if not all(tuple(sorted((a, b))) in used for a, b in zip(f, f[1:] + f[:1])):
            raise ValueError('Face boundary edges are missing')
        if tuple(sorted(f)) in seen_faces:
            raise ValueError('Duplicate face')
        seen_faces.add(tuple(sorted(f)))
    start = constants['MESH']
    buffer = bytearray(constants['MESH_BYTES'])

    def write(name, data):
        offset = constants[name] - start
        buffer[offset:offset + len(data)] = data

    write('COUNTS', bytes([len(vertices), len(edges), len(faces)]))
    write('VERTICES', b''.join((v & 65535).to_bytes(2, 'little') for v in values))
    write('VLIVE', bytes([1] * len(vertices)))
    write('EDGES', bytes(v for edge in edges for v in edge))
    write('ELIVE', bytes([1] * len(edges)))
    write('FACES', bytes(v for f in faces for v in [len(f)] + f))
    return buffer


def import_model(native, model):
    native.idle()
    c = native.layout['constants']
    encoded = encode_model(model, c)  # Validate everything before touching RAM.
    native.machine.memory[c['MESH']:c['MESH'] + c['MESH_BYTES']] = encoded
    native.machine.memory[c['SELECT']:c['SELECT'] + 128] = [0] * 128
    for field in ['tool', 'input_length', 'order_count', 'undo_valid']:
        address = native.layout['variables'][field]
        native.machine.memory[address:address + 2] = [0, 0]
    address = native.layout['variables']['cursor']
    native.machine.memory[address:address + 2] = [255, 255]
    for field, value in [('editing', 1), ('view_yaw', 4), ('view_pitch', 3), ('zoom', 10)]:
        address = native.layout['variables'][field]
        native.machine.memory[address:address + 2] = [value, 0]
    native.press(ord('1'))
