# -*- coding: utf-8 -*-
"""Static checks that mirror the Bandit findings the QGIS plugin repository reports.

  B110 / B112  an `except` block whose body is only `pass` / `continue`
  B105 / B106  a string assigned to a name or dict key that looks like a credential

Run:  python3 tests/test_security_patterns.py
(Bandit itself is still the reference: `pip install bandit && bandit -r step_recorder`)
"""
import ast
import glob
import os
import re
import unittest

PKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "step_recorder")
SENSITIVE = re.compile(r"pass(word|wd)?|pwd|secret|token|api_?key", re.I)


def _trees():
    for fn in sorted(glob.glob(os.path.join(PKG, "*.py"))):
        with open(fn, encoding="utf-8") as fh:
            yield os.path.basename(fn), ast.parse(fh.read())


class SecurityPatterns(unittest.TestCase):
    def test_no_silent_except_blocks(self):
        bad = []
        for name, tree in _trees():
            for n in ast.walk(tree):
                if isinstance(n, ast.ExceptHandler) and \
                        all(isinstance(b, (ast.Pass, ast.Continue)) for b in n.body):
                    bad.append("%s:%d" % (name, n.lineno))
        self.assertEqual(bad, [], "except blocks that swallow errors: %s" % bad)

    def test_no_credential_like_names_with_string_values(self):
        bad = []
        for name, tree in _trees():
            for n in ast.walk(tree):
                if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) \
                        and isinstance(n.value.value, str):
                    for t in n.targets:
                        if isinstance(t, ast.Name) and SENSITIVE.search(t.id):
                            bad.append("%s:%d %s" % (name, n.lineno, t.id))
                elif isinstance(n, ast.Dict):
                    for k, v in zip(n.keys, n.values):
                        if isinstance(k, ast.Constant) and isinstance(k.value, str) \
                                and isinstance(v, ast.Constant) and isinstance(v.value, str) \
                                and SENSITIVE.search(k.value):
                            bad.append("%s:%d key %r" % (name, k.lineno, k.value))
        self.assertEqual(bad, [], "credential-looking names: %s" % bad)

    def test_no_broad_except_hides_errors_silently(self):
        """Every `except Exception` must do something (log, return, re-raise...)."""
        for name, tree in _trees():
            for n in ast.walk(tree):
                if isinstance(n, ast.ExceptHandler) and n.type is not None \
                        and ast.unparse(n.type) == "Exception":
                    self.assertFalse(all(isinstance(b, (ast.Pass, ast.Continue)) for b in n.body),
                                     "%s:%d" % (name, n.lineno))


if __name__ == "__main__":
    unittest.main(verbosity=2)
