# -*- coding: utf-8 -*-
"""Repo QA scanner: test coverage mapping and optional test generation."""

from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_helper import call_ai
from utils.constants import MAX_FILE_SIZE
from utils.git_ops import cleanup_clone, clone_repo, parse_github_url
from utils.parsers import clean_ai_json, should_skip_path

router = APIRouter()

TEST_PATTERNS = {
    "python": ["{name}_test.py", "test_{name}.py", "tests/test_{name}.py", "tests/{name}_test.py"],
    "javascript": ["{name}.test.js", "{name}.spec.js", "__tests__/{name}.test.js"],
    "typescript": ["{name}.test.ts", "{name}.spec.ts", "__tests__/{name}.test.ts"],
    "java": ["{name}Test.java", "test/{name}Test.java"],
}

FRAMEWORK_MAP = {
    "python": "pytest",
    "javascript": "jest",
    "typescript": "jest",
    "java": "JUnit 5",
}

LANG_EXTENSIONS = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
}


class RepoQARequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main")
    auto_generate: bool = Field(default=False, description="Auto-generate tests for uncovered files")
    max_generate: int = Field(default=5, description="Max files to auto-generate tests for")


def find_test_file(source_path: str, all_files: List[str], language: str) -> Optional[str]:
    """Return matching test path for a source file, or None."""
    stem = Path(source_path).stem
    patterns = TEST_PATTERNS.get(language, [])

    for pattern in patterns:
        expected = pattern.format(name=stem)
        for f in all_files:
            if f.endswith(expected) or Path(f).name == Path(expected).name:
                return f
    return None


def is_test_file(path: str) -> bool:
    p = path.lower()
    return any(k in p for k in ["test_", "_test.", ".test.", ".spec.", "__tests__", "/tests/", "/test/"])


def scan_test_coverage(clone_dir: Path) -> Dict:
    """Walk the clone and map source files to tests."""
    all_files = []
    for fpath in sorted(clone_dir.rglob("*")):
        if not fpath.is_file():
            continue
        rel = str(fpath.relative_to(clone_dir))
        if should_skip_path(rel):
            continue
        all_files.append(rel)

    source_files = []
    test_files = []
    coverage_map = []

    for f in all_files:
        ext = Path(f).suffix.lower()
        lang = LANG_EXTENSIONS.get(ext)
        if not lang:
            continue

        if is_test_file(f):
            fpath = clone_dir / f
            try:
                content = fpath.read_text(errors="ignore")
                line_count = content.count("\n") + 1
                is_empty = line_count < 3 or len(content.strip()) < 20
            except Exception:
                is_empty = True
                line_count = 0

            test_files.append({
                "path": f, "language": lang, "lines": line_count,
                "isEmpty": is_empty,
            })
        else:
            source_files.append({"path": f, "language": lang})

    all_rel = [str(f) for f in all_files]

    missing_tests = []
    empty_tests = []
    covered_files = []

    for src in source_files:
        test_path = find_test_file(src["path"], all_rel, src["language"])
        if test_path is None:
            missing_tests.append(src)
            coverage_map.append({**src, "testFile": None, "status": "missing"})
        else:
            test_info = next((t for t in test_files if t["path"] == test_path), None)
            if test_info and test_info["isEmpty"]:
                empty_tests.append({**src, "testFile": test_path})
                coverage_map.append({**src, "testFile": test_path, "status": "empty"})
            else:
                covered_files.append({**src, "testFile": test_path})
                coverage_map.append({**src, "testFile": test_path, "status": "covered"})

    total_source = len(source_files)
    total_covered = len(covered_files)
    coverage_pct = round(total_covered / max(total_source, 1) * 100, 1)

    return {
        "totalSourceFiles": total_source,
        "totalTestFiles": len(test_files),
        "coveredFiles": total_covered,
        "missingTests": len(missing_tests),
        "emptyTests": len(empty_tests),
        "coveragePercent": coverage_pct,
        "coverageMap": coverage_map,
        "missingTestDetails": missing_tests[:30],
        "emptyTestDetails": empty_tests[:10],
        "frameworks": list(set(FRAMEWORK_MAP.get(s["language"], "") for s in source_files if s["language"] in FRAMEWORK_MAP)),
    }


QA_GENERATE_PROMPT = """You are a Senior QA Engineer. Generate a complete, runnable test file for the source code below.

Requirements:
- Cover happy path, edge cases, error scenarios
- Use the correct framework for the language
- Include descriptive test names
- Add AAA pattern (Arrange/Act/Assert)
- Make tests immediately runnable

Respond ONLY in this JSON:
{
  "testFileName": "test_example.py",
  "framework": "pytest",
  "testCount": 8,
  "testFile": "complete runnable test code as string",
  "coverage": "~80%"
}
RESPOND ONLY WITH VALID JSON."""


@router.post("/scan")
async def scan_repo_tests(request: RepoQARequest):
    """Scan a repo for test coverage gaps."""
    try:
        owner, repo = parse_github_url(request.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    print(f"[QA] Scanning {owner}/{repo} for test coverage")

    try:
        clone_dir = clone_repo(request.repo_url, request.branch, tag="qa")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = scan_test_coverage(clone_dir)

        generated_tests = []
        if request.auto_generate and result["missingTests"] > 0:
            files_to_gen = result["missingTestDetails"][:request.max_generate]
            for src in files_to_gen:
                src_path = clone_dir / src["path"]
                try:
                    content = src_path.read_text(errors="ignore")[:MAX_FILE_SIZE]
                except Exception:
                    continue

                fw = FRAMEWORK_MAP.get(src["language"], "pytest")
                msg = f"Generate {fw} tests for this {src['language']} file ({src['path']}):\n\n```{src['language']}\n{content}\n```"

                try:
                    raw = await call_ai(QA_GENERATE_PROMPT, msg)
                    gen = clean_ai_json(raw)
                    gen["sourceFile"] = src["path"]
                    gen["language"] = src["language"]
                    generated_tests.append(gen)
                except Exception:
                    generated_tests.append({
                        "sourceFile": src["path"],
                        "language": src["language"],
                        "error": "Generation failed",
                    })

        result["generatedTests"] = generated_tests
        result["repository"] = f"{owner}/{repo}"
        result["branch"] = request.branch
        return result

    finally:
        cleanup_clone(clone_dir)
