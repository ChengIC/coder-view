import os
import re
import ast
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple

IGNORED_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__"}
CODE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx"}


def _iter_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # filter ignored dirs
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for f in filenames:
            p = Path(dirpath) / f
            if p.suffix.lower() in CODE_EXTS or p.name.lower() in {"readme.md", "readme"}:
                files.append(p)
    return files


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _readability_metrics(root: Path, files: List[Path]) -> Dict[str, Any]:
    has_readme = any(f.name.lower().startswith("readme") for f in files)

    # Docstrings and comments (Python + JS/TS)
    py_docstring_count = 0
    py_func_count = 0
    py_comment_lines = 0
    py_total_lines = 0

    js_comment_lines = 0
    js_total_lines = 0
    js_jsdoc_blocks = 0

    for f in files:
        content = _read_file(f)
        if f.suffix == ".py":
            py_total_lines += len(content.splitlines())
            py_comment_lines += sum(1 for line in content.splitlines() if line.strip().startswith("#"))
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                        py_func_count += 1 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else 0
                        if ast.get_docstring(node):
                            py_docstring_count += 1
            except Exception:
                pass
        elif f.suffix in {".js", ".ts", ".tsx", ".jsx"}:
            js_total_lines += len(content.splitlines())
            js_comment_lines += sum(1 for line in content.splitlines() if line.strip().startswith("//") or line.strip().startswith("/*"))
            js_jsdoc_blocks += len(re.findall(r"/\*\*([\s\S]*?)\*/", content))

    readability = {
        "has_readme": has_readme,
        "python": {
            "docstring_count": py_docstring_count,
            "function_count": py_func_count,
            "comment_density": round(py_comment_lines / py_total_lines, 4) if py_total_lines else 0,
        },
        "javascript_typescript": {
            "jsdoc_blocks": js_jsdoc_blocks,
            "comment_density": round(js_comment_lines / js_total_lines, 4) if js_total_lines else 0,
        },
    }
    return readability


def _normalize_code(content: str) -> str:
    # strip whitespace and comments for simple duplicate detection
    lines = []
    for line in content.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#") or s.startswith("//"):
            continue
        lines.append(s)
    return "\n".join(lines)


def _reusability_metrics(files: List[Path]) -> Dict[str, Any]:
    hashes: Dict[str, List[str]] = {}
    for f in files:
        content = _read_file(f)
        norm = _normalize_code(content)
        if not norm:
            continue
        h = hashlib.sha1(norm.encode("utf-8")).hexdigest()
        hashes.setdefault(h, []).append(str(f))

    duplicates = {h: paths for h, paths in hashes.items() if len(paths) > 1}
    duplicate_groups = [paths for paths in duplicates.values()]

    return {
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_groups": duplicate_groups[:10],  # cap in report
        "recommendation": "Refactor duplicated logic into shared modules/libraries.",
    }


class _TryExceptCounter(ast.NodeVisitor):
    def __init__(self):
        self.try_count = 0
        self.func_with_annotations = 0
        self.func_total = 0

    def visit_Try(self, node):
        self.try_count += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.func_total += 1
        if node.returns or any(arg.annotation for arg in node.args.args):
            self.func_with_annotations += 1
        self.generic_visit(node)


def _robustness_metrics(files: List[Path]) -> Dict[str, Any]:
    has_tests = any("tests" in f.parts or "__tests__" in f.parts for f in files)
    py_try_count = 0
    py_func_total = 0
    py_func_annotated = 0

    for f in files:
        if f.suffix != ".py":
            continue
        content = _read_file(f)
        try:
            tree = ast.parse(content)
            c = _TryExceptCounter()
            c.visit(tree)
            py_try_count += c.try_count
            py_func_total += c.func_total
            py_func_annotated += c.func_with_annotations
        except Exception:
            pass

    return {
        "has_tests": has_tests,
        "python": {
            "try_except_count": py_try_count,
            "function_count": py_func_total,
            "typed_function_ratio": round(py_func_annotated / py_func_total, 4) if py_func_total else 0,
        }
    }


def _performance_metrics(files: List[Path]) -> Dict[str, Any]:
    sql_concat_suspects = []
    risky_calls = []

    sql_pattern = re.compile(r"SELECT[\s\S]*FROM", re.IGNORECASE)
    concat_pattern = re.compile(r"\+|%|\.format\(\)")

    for f in files:
        content = _read_file(f)
        if sql_pattern.search(content) and concat_pattern.search(content):
            sql_concat_suspects.append(str(f))

        if re.search(r"\beval\(|\bpickle\.", content):
            risky_calls.append(str(f))

    return {
        "sql_injection_risk_files": sql_concat_suspects[:20],
        "risky_calls_files": risky_calls[:20],
        "notes": "Prefer parameterized queries; avoid eval/pickle without strict controls.",
    }


def evaluate_codebase_from_contents(file_contents: Dict[str, str]) -> Dict[str, Any]:
    """Evaluate codebase directly from file contents without disk storage."""
    # Create temporary files for analysis
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    try:
        # Write files to temp directory
        file_paths = []
        for rel_path, content in file_contents.items():
            file_path = Path(temp_dir) / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                file_path.write_text(content, encoding='utf-8')
                file_paths.append(file_path)
            except Exception:
                continue
        
        # Run existing analysis on temp files
        readability = _readability_metrics(Path(temp_dir), file_paths)
        reusability = _reusability_metrics(file_paths)
        robustness = _robustness_metrics(file_paths)
        performance = _performance_metrics(file_paths)
        
        # Get code samples directly from contents
        code_samples = _get_code_samples_from_contents(file_contents)
        
        return {
            "readability": readability,
            "reusability": reusability,
            "robustness": robustness,
            "performance": performance,
            "file_count": len(file_paths),
            "code_samples": code_samples,
        }
    finally:
        # Always cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


def _get_code_samples_from_contents(file_contents: Dict[str, str], max_samples: int = 5, max_size_per_file: int = 2000) -> Dict[str, str]:
    """Extract representative code samples directly from file contents."""
    samples = {}
    
    # Filter code files
    code_files = {}
    for rel_path, content in file_contents.items():
        if any(rel_path.lower().endswith(ext) for ext in CODE_EXTS):
            code_files[rel_path] = content
    
    # Prioritize by file size and type
    python_files = {k: v for k, v in code_files.items() if k.lower().endswith('.py')}
    js_ts_files = {k: v for k, v in code_files.items() if any(k.lower().endswith(ext) for ext in {'.js', '.ts', '.tsx', '.jsx'})}
    
    def file_priority(item):
        rel_path, content = item
        size = len(content)
        # Prefer files between 500-5000 characters
        if 500 <= size <= 5000:
            return 0  # highest priority
        elif size < 500:
            return 1
        else:
            return 2
    
    selected_files = []
    
    # Add Python files
    python_sorted = sorted(python_files.items(), key=file_priority)[:max_samples//2 + 1]
    selected_files.extend(python_sorted)
    
    # Add JS/TS files
    js_sorted = sorted(js_ts_files.items(), key=file_priority)[:max_samples//2 + 1]
    selected_files.extend(js_sorted)
    
    # Limit total samples
    selected_files = selected_files[:max_samples]
    
    for rel_path, content in selected_files:
        if content.strip():
            # Truncate if too long
            if len(content) > max_size_per_file:
                content = content[:max_size_per_file] + "\n... (truncated)"
            samples[rel_path] = content
    
    return samples