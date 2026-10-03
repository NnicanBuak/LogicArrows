"""Compile a restricted integer Python syntax to the native ASM bytecode runtime.

The editor runs on Computer v2; Python is only used at build time.
"""
import ast

OPS = {name: i + 1 for i, name in enumerate(
    'CONST GET SET LOAD8 LOADS LOAD16 STORE8 STORE16 ADD SUB MUL DIV MOD NEG '
    'AND OR XOR SHL SHR NOT EQ LT DROP DUP JMP JZ CALL RET KEY PUTC TEXT COPY '
    'BEGIN PRESENT PIXEL LINE TRIANGLE PROJECT BLINK'.split())}
VOID = {'poke8', 'poke16', 'putc', 'text', 'copy', 'begin', 'present',
        'pixel', 'line', 'triangle', 'project', 'blink'}
INTRINSICS = dict(peek8='LOAD8', peeks8='LOADS', peek16='LOAD16',
                  poke8='STORE8', poke16='STORE16', keycode='KEY', putc='PUTC',
                  copy='COPY', begin='BEGIN', present='PRESENT', pixel='PIXEL',
                  line='LINE', triangle='TRIANGLE', project='PROJECT', blink='BLINK')


class Compiler:
    def __init__(self, source, constants, globals_base, strings_base):
        self.tree = ast.parse(source)
        self.constants = constants
        self.globals_base = globals_base
        self.strings_base = strings_base
        self.variables = {}
        self.strings = bytearray()
        self.code = bytearray()
        self.labels = {}
        self.relocations = []
        self.scope = ''
        self.shared = set()
        self.counter = 0
        self.functions = {n.name: n for n in self.tree.body if isinstance(n, ast.FunctionDef)}
        self.module_globals = {v for n in ast.walk(self.tree) if isinstance(n, ast.Global) for v in n.names}

    def variable(self, name):
        full = name if name in self.shared else self.scope + '.' + name
        if full not in self.variables:
            self.variables[full] = self.globals_base + 2 * len(self.variables)
        return self.variables[full]

    def emit(self, op, *args):
        self.code.append(OPS[op])
        self.code.extend(v & 255 for v in args)

    def word(self, op, value):
        self.emit(op, value & 255, value >> 8)

    def label(self, name):
        self.labels[name] = len(self.code)

    def tag(self):
        self.counter += 1
        return 'branch_' + str(self.counter)

    def branch(self, op, name):
        self.relocations.append((len(self.code) + 1, name))
        self.word(op, 0)

    def expr(self, n):
        if isinstance(n, ast.Constant):
            if isinstance(n.value, int):
                self.word('CONST', n.value)
            else:
                raise ValueError(ast.dump(n))
        elif isinstance(n, ast.Name):
            if n.id in self.constants:
                self.word('CONST', self.constants[n.id])
            else:
                self.word('GET', self.variable(n.id))
        elif isinstance(n, ast.BinOp):
            self.expr(n.left)
            self.expr(n.right)
            self.emit({ast.Add: 'ADD', ast.Sub: 'SUB', ast.Mult: 'MUL',
                       ast.FloorDiv: 'DIV', ast.Mod: 'MOD', ast.BitAnd: 'AND',
                       ast.BitOr: 'OR', ast.BitXor: 'XOR', ast.LShift: 'SHL',
                       ast.RShift: 'SHR'}[type(n.op)])
        elif isinstance(n, ast.UnaryOp):
            self.expr(n.operand)
            if isinstance(n.op, ast.Invert):
                self.word('CONST', -1)
                self.emit('XOR')
            else:
                self.emit({ast.USub: 'NEG', ast.Not: 'NOT'}[type(n.op)])
        elif isinstance(n, ast.BoolOp):
            end = self.tag()
            for value in n.values[:-1]:
                self.expr(value)
                self.emit('DUP')
                if isinstance(n.op, ast.Or):
                    self.emit('NOT')
                self.branch('JZ', end)
                self.emit('DROP')
            self.expr(n.values[-1])
            self.label(end)
        elif isinstance(n, ast.Compare):
            if len(n.ops) != 1:
                raise ValueError('Use explicit and instead of chained comparisons')
            op = n.ops[0]
            flip = isinstance(op, (ast.Gt, ast.LtE))
            self.expr(n.comparators[0] if flip else n.left)
            self.expr(n.left if flip else n.comparators[0])
            self.emit('EQ' if isinstance(op, (ast.Eq, ast.NotEq)) else 'LT')
            if isinstance(op, (ast.NotEq, ast.GtE, ast.LtE)):
                self.emit('NOT')
        elif isinstance(n, ast.IfExp):
            otherwise, end = self.tag(), self.tag()
            self.expr(n.test)
            self.branch('JZ', otherwise)
            self.expr(n.body)
            self.branch('JMP', end)
            self.label(otherwise)
            self.expr(n.orelse)
            self.label(end)
        elif isinstance(n, ast.Call):
            name = n.func.id
            if name == 'text':
                value = n.args[0].value.encode('ascii') + b'\0'
                address = self.strings_base + len(self.strings)
                self.strings.extend(value)
                self.word('TEXT', address)
            elif name in INTRINSICS:
                for arg in n.args:
                    self.expr(arg)
                self.emit(INTRINSICS[name])
            else:
                fn = self.functions[name]
                if len(n.args) != len(fn.args.args):
                    raise ValueError(name)
                # Evaluate all arguments before assigning parameter globals.
                for arg in n.args:
                    self.expr(arg)
                for arg in reversed(fn.args.args):
                    full = name + '.' + arg.arg
                    if full not in self.variables:
                        self.variables[full] = self.globals_base + 2 * len(self.variables)
                    self.word('SET', self.variables[full])
                self.branch('CALL', name)
        else:
            raise ValueError(ast.dump(n))

    def stmt(self, n):
        if isinstance(n, ast.Assign):
            self.expr(n.value)
            assert len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
            self.word('SET', self.variable(n.targets[0].id))
        elif isinstance(n, ast.AugAssign):
            self.expr(ast.BinOp(left=n.target, op=n.op, right=n.value))
            self.word('SET', self.variable(n.target.id))
        elif isinstance(n, ast.Expr):
            self.expr(n.value)
            if not isinstance(n.value, ast.Call) or n.value.func.id not in VOID:
                self.emit('DROP')
        elif isinstance(n, ast.If):
            otherwise, end = self.tag(), self.tag()
            self.expr(n.test)
            self.branch('JZ', otherwise)
            for child in n.body:
                self.stmt(child)
            self.branch('JMP', end)
            self.label(otherwise)
            for child in n.orelse:
                self.stmt(child)
            self.label(end)
        elif isinstance(n, ast.While):
            start, end = self.tag(), self.tag()
            self.label(start)
            self.expr(n.test)
            self.branch('JZ', end)
            for child in n.body:
                self.stmt(child)
            self.branch('JMP', start)
            self.label(end)
        elif isinstance(n, ast.Return):
            self.expr(n.value if n.value is not None else ast.Constant(value=0))
            self.emit('RET')
        elif isinstance(n, (ast.Global, ast.Pass)):
            pass
        else:
            raise ValueError(ast.dump(n))

    def compile(self, code_base):
        self.branch('JMP', 'main')
        for name, fn in self.functions.items():
            self.scope = name
            self.shared = self.module_globals
            self.label(name)
            for child in fn.body:
                self.stmt(child)
            self.word('CONST', 0)
            self.emit('RET')
        for offset, target in self.relocations:
            address = code_base + self.labels[target]
            self.code[offset:offset + 2] = address.to_bytes(2, 'little')
        assert len(self.variables) * 2 <= 1024, len(self.variables)
        assert len(self.strings) <= 2048, len(self.strings)
        return bytes(self.code)
