# -*- coding: utf-8 -*-
"""Unified code health dashboard: aggregates analysis into a single score and report."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_helper import call_ai
from utils.git_ops import parse_github_url, clone_repo, cleanup_clone
from utils.constants import ANALYZABLE_EXTENSIONS, MAX_FILE_SIZE
from utils.parsers import clean_ai_json, detect_language, should_skip_path

router = APIRouter()


class DashboardRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main")


def collect_repo_data(clone_dir: Path) -> dict:
    """Gather file stats, languages, test coverage info, and sample code."""
    files = []
    language_lines = {}
    test_files = []
    source_files = []
    total_lines = 0
    sample_code_files = []
    manifest_content = {}

    for fpath in sorted(clone_dir.rglob("*")):
        if not fpath.is_file():
            continue
        rel = str(fpath.relative_to(clone_dir))

        if should_skip_path(rel):
            continue

        if fpath.name in ("package.json", "requirements.txt", "go.mod", "Cargo.toml", "pom.xml"):
            try:
                manifest_content[fpath.name] = fpath.read_text(errors="ignore")[:5000]
            except Exception:
                pass

        ext = fpath.suffix.lower()
        if ext not in ANALYZABLE_EXTENSIONS:
            continue

        try:
            content = fpath.read_text(errors="ignore")
            lines = content.count("\n") + 1
            total_lines += lines
        except Exception:
            continue

        lang = detect_language(ext)
        language_lines[lang] = language_lines.get(lang, 0) + lines

        is_test = any(k in rel.lower() for k in ["test", "spec", "__test__"])
        if is_test:
            test_files.append(rel)
        else:
            source_files.append(rel)
            if len(sample_code_files) < 5 and len(content) < MAX_FILE_SIZE:
                sample_code_files.append({"path": rel, "content": content[:8000], "language": lang})

        files.append({"path": rel, "language": lang, "lines": lines, "isTest": is_test})

    return {
        "totalFiles": len(files),
        "totalLines": total_lines,
        "languages": language_lines,
        "testFiles": len(test_files),
        "sourceFiles": len(source_files),
        "testRatio": round(len(test_files) / max(len(source_files), 1) * 100, 1),
        "files": files,
        "sampleCode": sample_code_files,
        "manifests": manifest_content,
    }


DASHBOARD_PROMPT = """You are a Lead Engineering Manager generating a comprehensive Code Health Dashboard.

Analyze the repository data and code samples. Score each category from 0-100:

1. **Code Quality** (0-100): naming, structure, complexity, duplication, best practices
2. **Security** (0-100): hardcoded secrets, injection risks, auth issues, data exposure
3. **Test Coverage** (0-100): ratio of test to source files, edge case coverage
4. **Maintainability** (0-100): modularity, readability, documentation, separation of concerns
5. **Dependencies** (0-100): up-to-date packages, no known CVEs, minimal bloat

Also provide:
- Per-file risk assessment (top 10 riskiest files)
- Issue breakdown by category
- Specific actionable recommendations

Respond ONLY in this JSON:
{
  "overallScore": 72,
  "grade": "B",
  "scores": {
    "codeQuality": 75,
    "security": 65,
    "testCoverage": 50,
    "maintainability": 80,
    "dependencies": 70
  },
  "summary": "2-3 paragraph executive summary of the project health",
  "issueBreakdown": {
    "critical": 2,
    "high": 5,
    "medium": 8,
    "low": 3
  },
  "fileRisks": [
    {"file": "path/to/file", "score": 45, "issues": ["issue1", "issue2"], "severity": "high"}
  ],
  "categoryDetails": {
    "codeQuality": {"score": 75, "findings": ["finding1"], "recommendations": ["rec1"]},
    "security": {"score": 65, "findings": ["finding1"], "recommendations": ["rec1"]},
    "testCoverage": {"score": 50, "findings": ["finding1"], "recommendations": ["rec1"]},
    "maintainability": {"score": 80, "findings": ["finding1"], "recommendations": ["rec1"]},
    "dependencies": {"score": 70, "findings": ["finding1"], "recommendations": ["rec1"]}
  },
  "topRecommendations": [
    {"priority": 1, "title": "Fix critical security issue", "description": "detailed description", "impact": "high", "effort": "low"}
  ],
  "techDebt": {
    "level": "moderate",
    "estimatedHours": 40,
    "description": "summary of tech debt"
  }
}
RESPOND ONLY WITH VALID JSON."""


@router.post("/generate")
async def generate_dashboard(request: DashboardRequest):
    """Run the full analysis pipeline and return a unified dashboard."""
    try:
        owner, repo = parse_github_url(request.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    print(f"[DASHBOARD] Full analysis of {owner}/{repo} @ {request.branch}")

    try:
        clone_dir = clone_repo(request.repo_url, request.branch, tag="dashboard")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        repo_data = collect_repo_data(clone_dir)

        code_samples = "\n\n".join(
            f"=== {s['path']} ({s['language']}) ===\n{s['content']}"
            for s in repo_data["sampleCode"]
        )

        manifest_info = "\n\n".join(
            f"=== {name} ===\n{content}"
            for name, content in repo_data["manifests"].items()
        )

        file_list = "\n".join(
            f"- {f['path']} ({f['language']}, {f['lines']} lines, {'TEST' if f['isTest'] else 'source'})"
            for f in repo_data["files"][:60]
        )

        user_message = (
            f"Repository: {owner}/{repo}\n"
            f"Branch: {request.branch}\n"
            f"Total source files: {repo_data['sourceFiles']}\n"
            f"Total test files: {repo_data['testFiles']}\n"
            f"Test/source ratio: {repo_data['testRatio']}%\n"
            f"Total lines: {repo_data['totalLines']}\n"
            f"Languages: {json.dumps(repo_data['languages'])}\n\n"
            f"Manifests:\n{manifest_info}\n\n"
            f"File listing:\n{file_list}\n\n"
            f"Code samples:\n{code_samples}"
        )

        try:
            raw = await call_ai(DASHBOARD_PROMPT, user_message)
            dashboard = clean_ai_json(raw)
        except Exception:
            dashboard = {
                "overallScore": 50,
                "grade": "C",
                "scores": {"codeQuality": 50, "security": 50, "testCoverage": repo_data["testRatio"], "maintainability": 50, "dependencies": 50},
                "summary": "Dashboard generation encountered an issue. Partial data available.",
                "issueBreakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            }

        dashboard["repoInfo"] = {
            "name": f"{owner}/{repo}",
            "branch": request.branch,
            "totalFiles": repo_data["totalFiles"],
            "totalLines": repo_data["totalLines"],
            "languages": repo_data["languages"],
            "testFiles": repo_data["testFiles"],
            "sourceFiles": repo_data["sourceFiles"],
            "testRatio": repo_data["testRatio"],
        }

        return dashboard

    finally:
        cleanup_clone(clone_dir)
