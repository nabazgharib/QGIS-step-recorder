# -*- coding: utf-8 -*-
"""Smoke test: import every module against stub Qt/QGIS modules (catches typos,
bad imports and undefined module-level names; it does NOT exercise real Qt)."""
import ast, builtins, os, sys, types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "step_recorder")


class _Any(type):
    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _make(name)


def _make(name):
    return _Any(name, (object,), {"__init__": lambda self, *a, **k: None})


def stub(name):
    m = types.ModuleType(name)
    m.__getattr__ = lambda n: _make(n) if not n.startswith("__") else (_ for _ in ()).throw(AttributeError(n))
    sys.modules[name] = m
    return m


for n in ("qgis", "qgis.PyQt", "qgis.PyQt.QtCore", "qgis.PyQt.QtGui", "qgis.PyQt.QtWidgets",
          "qgis.PyQt.QtPrintSupport", "qgis.PyQt.Qsci", "qgis.core", "qgis.gui"):
    stub(n)

pkg = types.ModuleType("step_recorder"); pkg.__path__ = [PKG]; sys.modules["step_recorder"] = pkg
import importlib
for mod in ("i18n", "textutils", "model", "options", "exporter", "compat", "widgets",
            "capture", "recorder", "ui", "plugin"):
    importlib.import_module("step_recorder." + mod)
    print("import ok:", mod)

# static check: names used but never defined/imported in each module
builtin_names = set(dir(builtins))
bad = 0
for fn in sorted(os.listdir(PKG)):
    if not fn.endswith(".py"):
        continue
    tree = ast.parse(open(os.path.join(PKG, fn), encoding="utf-8").read())
    defined = set(builtin_names)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                defined.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            defined.add(node.name)
            if not isinstance(node, ast.ClassDef):
                for a in node.args.args + node.args.kwonlyargs + node.args.posonlyargs:
                    defined.add(a.arg)
                if node.args.vararg: defined.add(node.args.vararg.arg)
                if node.args.kwarg: defined.add(node.args.kwarg.arg)
        elif isinstance(node, ast.Lambda):
            for a in node.args.args: defined.add(a.arg)
            if node.args.vararg: defined.add(node.args.vararg.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            defined.add(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            defined.add(node.name)
        elif isinstance(node, ast.arg):
            defined.add(node.arg)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id not in defined:
            print("UNDEFINED %s:%d %s" % (fn, node.lineno, node.id)); bad += 1
print("undefined names:", bad)
sys.exit(1 if bad else 0)
