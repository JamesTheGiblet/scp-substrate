"""Symbol extraction: functions, classes and imports from source files."""
import ast
import re
from pathlib import Path


def _extract_python_symbols(path):
    """Top-level functions, classes, and class methods via ast."""
    try:
        tree = ast.parse(Path(path).read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return [], []

    symbols = []
    imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            symbols.append({
                "name": node.name,
                "kind": "function",
                "line": node.lineno,
                "docstring": (ast.get_docstring(node) or "")[:200],
            })
        elif isinstance(node, ast.ClassDef):
            symbols.append({
                "name": node.name,
                "kind": "class",
                "line": node.lineno,
                "docstring": (ast.get_docstring(node) or "")[:200],
            })
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append({
                        "name": f"{node.name}.{sub.name}",
                        "kind": "method",
                        "line": sub.lineno,
                        "docstring": (ast.get_docstring(sub) or "")[:200],
                    })
    return symbols, imports


_JS_FUNC_RE = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE)


_JS_CLASS_RE = re.compile(r"^\s*(?:export\s+)?class\s+(\w+)", re.MULTILINE)


_JS_CONST_FN_RE = re.compile(r"^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(", re.MULTILINE)


_JS_IMPORT_RE = re.compile(r"^\s*import\s+(?:.*?)\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE)


def _extract_js_symbols(path):
    """Regex-based function/class/const-fn extraction for JavaScript."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], []
    symbols = []
    for m in _JS_FUNC_RE.finditer(text):
        line = text[:m.start()].count("\n") + 1
        symbols.append({"name": m.group(1), "kind": "function", "line": line, "docstring": ""})
    for m in _JS_CLASS_RE.finditer(text):
        line = text[:m.start()].count("\n") + 1
        symbols.append({"name": m.group(1), "kind": "class", "line": line, "docstring": ""})
    for m in _JS_CONST_FN_RE.finditer(text):
        line = text[:m.start()].count("\n") + 1
        symbols.append({"name": m.group(1), "kind": "function", "line": line, "docstring": ""})
    imports = [m.group(1) for m in _JS_IMPORT_RE.finditer(text)]
    return symbols, imports


def _extract_symbols_for(lang, abs_path):
    if lang == "python":
        return _extract_python_symbols(abs_path)
    if lang in ("javascript", "typescript"):
        return _extract_js_symbols(abs_path)
    return [], []
