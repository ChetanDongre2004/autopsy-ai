# -*- coding: utf-8 -*-
"""Dead code detection, import graphs, metrics, framework linting, and analysis API routes."""

import re
import ast
import hashlib
from typing import Dict, List
from collections import defaultdict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class CodeAnalysisRequest(BaseModel):
    code: str = Field(..., description="Source code to analyze")
    language: str = Field(default="python")
    filename: str = Field(default="untitled.py")


class MultiFileAnalysisRequest(BaseModel):
    files: List[Dict] = Field(..., description="List of {path, content, language} objects")


def detect_dead_code_python(code: str) -> List[Dict]:
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return [{"type": "syntax_error", "description": "Code has syntax errors, cannot analyze", "severity": "critical"}]

    imported_names = set()
    import_lines = {}
    defined_functions = {}
    called_functions = set()
    defined_vars = {}
    used_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                imported_names.add(name)
                import_lines[name] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                imported_names.add(name)
                import_lines[name] = node.lineno
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined_functions[node.name] = node.lineno
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_functions.add(node.func.id)
                used_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                used_names.add(node.func.attr)
        elif isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            used_names.add(node.attr)

    for name, line in import_lines.items():
        base_name = name.split(".")[0]
        if base_name not in used_names and name not in used_names:
            if not name.startswith("_"):
                issues.append({
                    "type": "unused_import",
                    "name": name,
                    "line": line,
                    "severity": "warning",
                    "description": f"Import '{name}' is never used",
                    "fix": f"Remove: import {name}",
                })

    for name, line in defined_functions.items():
        if name not in called_functions and not name.startswith("_") and name != "main":
            if not any(d in name for d in ["test_", "setup", "teardown", "__"]):
                issues.append({
                    "type": "potentially_unused_function",
                    "name": name,
                    "line": line,
                    "severity": "info",
                    "description": f"Function '{name}()' may be unused (not called within this file)",
                    "fix": "Verify usage in other files or remove if dead code",
                })

    lines = code.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("return ") or stripped == "return":
            for j in range(i, min(i + 5, len(lines))):
                next_line = lines[j].strip() if j < len(lines) else ""
                if next_line and not next_line.startswith("#") and not next_line.startswith("def ") and not next_line.startswith("class "):
                    indent_current = len(line) - len(line.lstrip())
                    indent_next = len(lines[j]) - len(lines[j].lstrip()) if j < len(lines) else 0
                    if indent_next >= indent_current and next_line:
                        issues.append({
                            "type": "unreachable_code",
                            "line": j + 1,
                            "severity": "warning",
                            "description": f"Code after return statement is unreachable",
                            "fix": "Remove unreachable code or restructure logic",
                        })
                    break

    return issues


def detect_dead_code_js(code: str) -> List[Dict]:
    issues = []

    imports = re.findall(r'import\s+(?:\{([^}]+)\}|(\w+))\s+from', code)
    for match in imports:
        names = match[0].split(",") if match[0] else [match[1]]
        for name in names:
            name = name.strip().split(" as ")[-1].strip()
            if name and not re.search(r'\b' + re.escape(name) + r'\b', code[code.index(name) + len(name):]):
                issues.append({
                    "type": "unused_import",
                    "name": name,
                    "severity": "warning",
                    "description": f"Import '{name}' appears unused",
                    "fix": f"Remove unused import '{name}'",
                })

    functions = re.findall(r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()', code)
    for match in functions:
        name = match[0] or match[1]
        if name and code.count(name) <= 2:
            issues.append({
                "type": "potentially_unused_function",
                "name": name,
                "severity": "info",
                "description": f"Function '{name}' may be unused (few references found)",
                "fix": "Verify usage or remove",
            })

    return issues


def build_import_graph_python(files: List[Dict]) -> Dict:
    graph = defaultdict(list)
    all_modules = {}

    for f in files:
        module_name = f["path"].replace("/", ".").replace(".py", "")
        all_modules[module_name] = f["path"]
        short = f["path"].replace(".py", "").split("/")[-1]
        all_modules[short] = f["path"]

    for f in files:
        try:
            tree = ast.parse(f.get("content", ""))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = all_modules.get(alias.name) or all_modules.get(alias.name.split(".")[-1])
                    if target and target != f["path"]:
                        graph[f["path"]].append({"target": target, "type": "import"})
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    target = all_modules.get(node.module) or all_modules.get(node.module.split(".")[-1])
                    if target and target != f["path"]:
                        graph[f["path"]].append({"target": target, "type": "from_import"})

    return dict(graph)


def build_import_graph_js(files: List[Dict]) -> Dict:
    graph = defaultdict(list)

    file_map = {}
    for f in files:
        stem = f["path"].rsplit(".", 1)[0]
        file_map[stem] = f["path"]
        file_map[stem.split("/")[-1]] = f["path"]

    for f in files:
        content = f.get("content", "")
        imports = re.findall(r"(?:import|require)\s*\(?['\"]([^'\"]+)['\"]", content)
        for imp in imports:
            if imp.startswith("."):
                from pathlib import PurePosixPath
                base_dir = str(PurePosixPath(f["path"]).parent)
                resolved = str(PurePosixPath(base_dir) / imp)
                resolved = re.sub(r'/\.\/', '/', resolved)
                target = file_map.get(resolved) or file_map.get(imp.split("/")[-1])
                if target and target != f["path"]:
                    graph[f["path"]].append({"target": target, "type": "import"})

    return dict(graph)


def detect_circular_deps(graph: Dict) -> List[List[str]]:
    cycles = []
    visited = set()

    def dfs(node, path, path_set):
        if node in path_set:
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            if sorted(cycle) not in [sorted(c) for c in cycles]:
                cycles.append(cycle)
            return
        if node in visited:
            return
        visited.add(node)
        path_set.add(node)
        path.append(node)
        for edge in graph.get(node, []):
            dfs(edge["target"], path[:], set(path_set))

    for node in graph:
        dfs(node, [], set())

    return cycles


def calculate_cyclomatic_complexity_python(code: str) -> List[Dict]:
    results = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = 1
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                    complexity += 1
                elif isinstance(child, ast.BoolOp):
                    complexity += len(child.values) - 1
                elif isinstance(child, ast.Assert):
                    complexity += 1
                elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    complexity += 1

            rating = "low" if complexity <= 5 else "moderate" if complexity <= 10 else "high" if complexity <= 20 else "very_high"
            results.append({
                "function": node.name,
                "line": node.lineno,
                "complexity": complexity,
                "rating": rating,
                "lines": node.end_lineno - node.lineno + 1 if hasattr(node, "end_lineno") and node.end_lineno else 0,
            })

    return results


def calculate_cyclomatic_complexity_js(code: str) -> List[Dict]:
    results = []
    func_pattern = r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(|(\w+)\s*\([^)]*\)\s*\{)'
    functions = list(re.finditer(func_pattern, code))

    for i, match in enumerate(functions):
        name = match.group(1) or match.group(2) or match.group(3) or f"anonymous_{i}"
        start = match.start()
        end = functions[i + 1].start() if i + 1 < len(functions) else len(code)
        body = code[start:end]

        complexity = 1
        complexity += len(re.findall(r'\bif\b|\belse\s+if\b|\bcase\b', body))
        complexity += len(re.findall(r'\bfor\b|\bwhile\b|\bdo\b', body))
        complexity += len(re.findall(r'\bcatch\b', body))
        complexity += len(re.findall(r'&&|\|\||\?\?', body))
        complexity += len(re.findall(r'\?[^?]', body))

        rating = "low" if complexity <= 5 else "moderate" if complexity <= 10 else "high" if complexity <= 20 else "very_high"
        line = code[:start].count("\n") + 1
        results.append({"function": name, "line": line, "complexity": complexity, "rating": rating})

    return results


def detect_code_duplication(code: str, min_lines: int = 4) -> List[Dict]:
    lines = code.split("\n")
    duplicates = []
    seen_blocks = {}

    for i in range(len(lines) - min_lines + 1):
        block = "\n".join(line.strip() for line in lines[i:i + min_lines] if line.strip())
        if len(block) < 20:
            continue
        block_hash = hashlib.md5(block.encode()).hexdigest()

        if block_hash in seen_blocks:
            orig_line = seen_blocks[block_hash]
            if abs(i + 1 - orig_line) > min_lines:
                already = any(d["line1"] == orig_line and d["line2"] == i + 1 for d in duplicates)
                if not already:
                    duplicates.append({
                        "line1": orig_line,
                        "line2": i + 1,
                        "lines": min_lines,
                        "snippet": block[:120],
                        "severity": "warning",
                    })
        else:
            seen_blocks[block_hash] = i + 1

    return duplicates


def calculate_file_metrics(code: str, language: str) -> Dict:
    lines = code.split("\n")
    total_lines = len(lines)
    blank_lines = sum(1 for l in lines if not l.strip())
    comment_lines = 0
    code_lines = 0

    if language == "python":
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            if '"""' in stripped or "'''" in stripped:
                comment_lines += 1
                in_docstring = not in_docstring
            elif in_docstring:
                comment_lines += 1
            elif stripped.startswith("#"):
                comment_lines += 1
            elif stripped:
                code_lines += 1
    else:
        in_block = False
        for line in lines:
            stripped = line.strip()
            if "/*" in stripped:
                in_block = True
                comment_lines += 1
            elif "*/" in stripped:
                in_block = False
                comment_lines += 1
            elif in_block:
                comment_lines += 1
            elif stripped.startswith("//"):
                comment_lines += 1
            elif stripped:
                code_lines += 1

    if language == "python":
        try:
            tree = ast.parse(code)
            func_count = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
            class_count = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
        except SyntaxError:
            func_count = len(re.findall(r"def \w+\(", code))
            class_count = len(re.findall(r"class \w+", code))
    else:
        func_count = len(re.findall(r"function\s+\w+\(|(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\(", code))
        class_count = len(re.findall(r"class\s+\w+", code))

    max_nesting = 0
    current_nesting = 0
    indent_stack = [0]
    for line in lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if indent > indent_stack[-1]:
            current_nesting += 1
            indent_stack.append(indent)
        while indent_stack and indent < indent_stack[-1]:
            indent_stack.pop()
            current_nesting = max(0, current_nesting - 1)
        max_nesting = max(max_nesting, current_nesting)

    return {
        "totalLines": total_lines,
        "codeLines": code_lines,
        "commentLines": comment_lines,
        "blankLines": blank_lines,
        "functions": func_count,
        "classes": class_count,
        "commentRatio": round(comment_lines / max(code_lines, 1) * 100, 1),
        "maxNesting": max_nesting,
    }


def lint_python_pep8(code: str) -> List[Dict]:
    issues = []
    lines = code.split("\n")

    for i, line in enumerate(lines, 1):
        if len(line) > 120:
            issues.append({"line": i, "rule": "E501", "message": f"Line too long ({len(line)} > 120 chars)", "severity": "info"})
        if line.rstrip() != line and line.strip():
            issues.append({"line": i, "rule": "W291", "message": "Trailing whitespace", "severity": "info"})
        if "\t" in line:
            issues.append({"line": i, "rule": "W191", "message": "Indentation contains tabs", "severity": "warning"})

    funcs = re.findall(r"def\s+([a-zA-Z_]\w*)\s*\(", code)
    for func in funcs:
        if func != func.lower() and not func.startswith("_"):
            if re.search(r'[A-Z]', func) and not func.startswith("test"):
                issues.append({"rule": "N802", "name": func, "message": f"Function '{func}' should be snake_case", "severity": "warning"})

    classes = re.findall(r"class\s+([a-zA-Z_]\w*)", code)
    for cls in classes:
        if cls[0].islower():
            issues.append({"rule": "N801", "name": cls, "message": f"Class '{cls}' should be CamelCase", "severity": "warning"})

    if not code.strip().endswith("\n") and code.strip():
        issues.append({"rule": "W292", "message": "No newline at end of file", "severity": "info"})

    return issues


def lint_react_hooks(code: str) -> List[Dict]:
    issues = []

    hooks = re.findall(r'\buse(State|Effect|Memo|Callback|Ref|Context)\b', code)
    if hooks:
        effects = list(re.finditer(r'useEffect\s*\(\s*(?:async\s*)?\(\s*\)\s*=>\s*\{', code))
        for match in effects:
            after = code[match.end():match.end() + 500]
            if not re.search(r'\]\s*\)', after):
                line = code[:match.start()].count("\n") + 1
                issues.append({
                    "line": line, "rule": "react-hooks/exhaustive-deps",
                    "message": "useEffect may be missing dependency array",
                    "severity": "warning",
                    "fix": "Add dependency array: useEffect(() => { ... }, [deps])",
                })

        if re.search(r'useEffect\s*\(\s*async', code):
            issues.append({
                "rule": "react-hooks/no-async-effect",
                "message": "useEffect callback should not be async directly",
                "severity": "warning",
                "fix": "Define async function inside and call it: useEffect(() => { const fn = async () => {...}; fn(); }, [])",
            })

        conditionals = re.findall(r'if\s*\(.*?\)\s*\{[^}]*\buse(?:State|Effect|Memo|Callback)\b', code, re.DOTALL)
        if conditionals:
            issues.append({
                "rule": "react-hooks/rules-of-hooks",
                "message": "Hook called inside a conditional - hooks must be called at the top level",
                "severity": "critical",
                "fix": "Move hook call outside of conditionals and loops",
            })

    return issues


def lint_angular(code: str) -> List[Dict]:
    issues = []

    if re.search(r'\.subscribe\s*\(', code):
        if not re.search(r'\.unsubscribe\s*\(|takeUntil|async\s+pipe|DestroyRef', code):
            issues.append({
                "rule": "angular/subscription-leak",
                "message": "Observable subscription without unsubscribe - potential memory leak",
                "severity": "high",
                "fix": "Use takeUntil, async pipe, or DestroyRef to manage subscriptions",
            })

    if re.search(r'constructor\s*\([^)]*\bnew\s+\w+Service', code):
        issues.append({
            "rule": "angular/no-manual-injection",
            "message": "Service instantiated manually instead of using Dependency Injection",
            "severity": "high",
            "fix": "Inject service via constructor parameter: constructor(private svc: MyService)",
        })

    if re.search(r'document\.getElementById|document\.querySelector|jQuery|\$\(', code):
        issues.append({
            "rule": "angular/no-direct-dom",
            "message": "Direct DOM manipulation detected - use Angular APIs instead",
            "severity": "warning",
            "fix": "Use @ViewChild, Renderer2, or template references",
        })

    return issues


@router.post("/dead-code")
async def analyze_dead_code(request: CodeAnalysisRequest):
    if request.language == "python":
        issues = detect_dead_code_python(request.code)
    elif request.language in ("javascript", "typescript"):
        issues = detect_dead_code_js(request.code)
    else:
        issues = []

    return {
        "totalIssues": len(issues),
        "issues": issues,
        "byType": {
            "unused_import": len([i for i in issues if i["type"] == "unused_import"]),
            "unused_function": len([i for i in issues if "unused_function" in i["type"]]),
            "unreachable": len([i for i in issues if i["type"] == "unreachable_code"]),
        },
    }


@router.post("/metrics")
async def analyze_metrics(request: CodeAnalysisRequest):
    if request.language == "python":
        complexity = calculate_cyclomatic_complexity_python(request.code)
    elif request.language in ("javascript", "typescript"):
        complexity = calculate_cyclomatic_complexity_js(request.code)
    else:
        complexity = []

    duplicates = detect_code_duplication(request.code)
    file_metrics = calculate_file_metrics(request.code, request.language)

    avg_complexity = round(sum(c["complexity"] for c in complexity) / max(len(complexity), 1), 1)
    max_complexity = max((c["complexity"] for c in complexity), default=0)
    high_complexity_count = sum(1 for c in complexity if c["rating"] in ("high", "very_high"))

    return {
        "fileMetrics": file_metrics,
        "complexity": complexity,
        "averageComplexity": avg_complexity,
        "maxComplexity": max_complexity,
        "highComplexityFunctions": high_complexity_count,
        "duplications": duplicates,
        "duplicationCount": len(duplicates),
        "healthIndicators": {
            "complexity": "good" if avg_complexity <= 5 else "moderate" if avg_complexity <= 10 else "poor",
            "duplication": "good" if len(duplicates) == 0 else "moderate" if len(duplicates) <= 3 else "poor",
            "commenting": "good" if file_metrics["commentRatio"] >= 10 else "moderate" if file_metrics["commentRatio"] >= 5 else "poor",
            "nesting": "good" if file_metrics["maxNesting"] <= 3 else "moderate" if file_metrics["maxNesting"] <= 5 else "poor",
        },
    }


@router.post("/imports")
async def analyze_imports(request: MultiFileAnalysisRequest):
    files = request.files
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    lang = files[0].get("language", "python")
    if lang == "python":
        graph = build_import_graph_python(files)
    else:
        graph = build_import_graph_js(files)

    cycles = detect_circular_deps(graph)

    edges = []
    for src, targets in graph.items():
        for t in targets:
            edges.append({"from": src, "to": t["target"], "type": t["type"]})

    return {
        "graph": graph,
        "edges": edges,
        "totalFiles": len(files),
        "totalEdges": len(edges),
        "circularDependencies": cycles,
        "hasCircularDeps": len(cycles) > 0,
    }


@router.post("/lint")
async def lint_code(request: CodeAnalysisRequest):
    issues = []

    if request.language == "python":
        issues.extend(lint_python_pep8(request.code))
    elif request.language in ("javascript", "typescript"):
        issues.extend(lint_react_hooks(request.code))
        issues.extend(lint_angular(request.code))

    dead_code = detect_dead_code_python(request.code) if request.language == "python" else detect_dead_code_js(request.code) if request.language in ("javascript", "typescript") else []

    return {
        "lintIssues": issues,
        "deadCode": dead_code,
        "totalIssues": len(issues) + len(dead_code),
        "bySeverity": {
            "critical": len([i for i in issues + dead_code if i.get("severity") == "critical"]),
            "warning": len([i for i in issues + dead_code if i.get("severity") == "warning"]),
            "info": len([i for i in issues + dead_code if i.get("severity") == "info"]),
        },
    }


@router.post("/full-analysis")
async def full_code_analysis(request: CodeAnalysisRequest):
    dead_code = detect_dead_code_python(request.code) if request.language == "python" else detect_dead_code_js(request.code) if request.language in ("javascript", "typescript") else []

    if request.language == "python":
        complexity = calculate_cyclomatic_complexity_python(request.code)
        lint_issues = lint_python_pep8(request.code)
    elif request.language in ("javascript", "typescript"):
        complexity = calculate_cyclomatic_complexity_js(request.code)
        lint_issues = lint_react_hooks(request.code) + lint_angular(request.code)
    else:
        complexity = []
        lint_issues = []

    duplicates = detect_code_duplication(request.code)
    file_metrics = calculate_file_metrics(request.code, request.language)

    avg_cx = round(sum(c["complexity"] for c in complexity) / max(len(complexity), 1), 1)
    all_issues = dead_code + lint_issues
    total = len(all_issues) + len(duplicates)

    score = 100
    score -= len([i for i in all_issues if i.get("severity") == "critical"]) * 15
    score -= len([i for i in all_issues if i.get("severity") in ("warning", "high")]) * 5
    score -= len([i for i in all_issues if i.get("severity") == "info"]) * 1
    score -= len(duplicates) * 3
    score -= sum(1 for c in complexity if c["rating"] in ("high", "very_high")) * 8
    score = max(0, min(100, score))

    return {
        "score": score,
        "grade": "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F",
        "fileMetrics": file_metrics,
        "deadCode": dead_code,
        "complexity": complexity,
        "averageComplexity": avg_cx,
        "duplications": duplicates,
        "lintIssues": lint_issues,
        "totalIssues": total,
    }
