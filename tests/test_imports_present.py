"""Static check: every module that uses a stdlib name imports it.

Catches the class of bug where a name like `os` is used only inside a method
(so py_compile and import-smoke both pass) but was never imported.
"""
import ast
import os
import pathlib

STDLIB_NAMES = ["os", "sys", "shutil", "re", "datetime", "uuid", "shlex",
                "subprocess", "yaml", "ctypes"]


def _imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # `from x import y` binds y; also record the module for `from os import path`
            for a in node.names:
                names.add(a.asname or a.name)
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def _used_attr_roots(tree: ast.AST) -> set[str]:
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            used.add(node.value.id)
    return used


def test_stdlib_imports_present():
    root = pathlib.Path(__file__).resolve().parent.parent / "qdvc"
    problems = []
    for path in root.rglob("*.py"):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
        imported = _imported_names(tree)
        used = _used_attr_roots(tree)
        for name in STDLIB_NAMES:
            if name in used and name not in imported:
                problems.append(f"{path.relative_to(root.parent)}: uses "
                                f"`{name}.` but does not import it")
    assert not problems, "Missing imports:\n" + "\n".join(problems)


if __name__ == "__main__":
    test_stdlib_imports_present()
    print("ok test_stdlib_imports_present")
