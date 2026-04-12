# -*- coding: utf-8 -*-
"""Branch comparison API: diff two GitHub branches and run AI analysis."""

import subprocess
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_helper import call_ai
from utils.constants import ANALYZABLE_EXTENSIONS
from utils.git_ops import parse_github_url, clone_full_repo, cleanup_clone
from utils.parsers import clean_ai_json

router = APIRouter()


class BranchCompareRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")
    base_branch: str = Field(default="main", description="Base branch (e.g., main)")
    head_branch: str = Field(..., description="Feature/PR branch to compare")


def get_diff(clone_dir: Path, base: str, head: str) -> str:
    """Return `git diff --stat` between base and head."""
    cmd = ["git", "diff", f"{base}...{head}", "--stat"]
    try:
        result = subprocess.run(cmd, cwd=clone_dir, capture_output=True, text=True, timeout=30)
        return result.stdout
    except Exception:
        return ""


def get_diff_content(clone_dir: Path, base: str, head: str) -> str:
    """Return truncated unified diff for common source extensions."""
    cmd = ["git", "diff", f"{base}...{head}", "--", "*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.java", "*.go"]
    try:
        result = subprocess.run(cmd, cwd=clone_dir, capture_output=True, text=True, timeout=30)
        return result.stdout[:50000]
    except Exception:
        return ""


def get_changed_files(clone_dir: Path, base: str, head: str) -> List[dict]:
    """List changed paths with status and whether the extension is analyzable."""
    cmd = ["git", "diff", "--name-status", f"{base}...{head}"]
    try:
        result = subprocess.run(cmd, cwd=clone_dir, capture_output=True, text=True, timeout=30)
    except Exception:
        return []

    files = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            status_code = parts[0][0]
            filepath = parts[-1]
            status_map = {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}
            ext = Path(filepath).suffix.lower()
            files.append({
                "path": filepath,
                "status": status_map.get(status_code, "modified"),
                "language": ext.lstrip("."),
                "analyzable": ext in ANALYZABLE_EXTENSIONS,
            })
    return files


def get_commit_log(clone_dir: Path, base: str, head: str) -> List[dict]:
    """Return commits reachable from head but not base (merge-base syntax)."""
    fmt = "--format=%H|||%an|||%s|||%ai"
    cmd = ["git", "log", fmt, f"{base}...{head}"]
    try:
        result = subprocess.run(cmd, cwd=clone_dir, capture_output=True, text=True, timeout=30)
    except Exception:
        return []

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|||")
        if len(parts) == 4:
            commits.append({
                "hash": parts[0][:8],
                "author": parts[1],
                "message": parts[2],
                "date": parts[3],
            })
    return commits


BRANCH_COMPARE_PROMPT = """You are a Senior Software Engineer reviewing a branch diff before merge.

Analyze the diff between the base branch and the feature branch.
Look for:
1. **Newly introduced bugs** — logic errors, null pointer risks, race conditions
2. **Security vulnerabilities** — removed input validation, hardcoded secrets, injection risks
3. **Performance regressions** — O(n²) loops, unnecessary API calls, memory leaks
4. **Removed safety checks** — deleted error handling, removed validation, weakened auth
5. **Code quality issues** — poor naming, complexity increase, broken patterns

Respond ONLY in this JSON format:
{
  "verdict": "SAFE_TO_MERGE" | "NEEDS_REVIEW" | "BLOCK_MERGE",
  "confidenceScore": 78,
  "summary": "2-3 sentence overview of the branch changes",
  "totalIssues": 3,
  "issues": [
    {
      "id": "ISSUE-001",
      "type": "bug" | "security" | "performance" | "removed_validation" | "code_quality",
      "severity": "critical" | "high" | "medium" | "low",
      "file": "path/to/file.py",
      "description": "What the issue is",
      "impact": "What could go wrong",
      "suggestion": "How to fix it",
      "lineContext": "relevant code snippet if available"
    }
  ],
  "positives": [
    "Good things about this branch"
  ],
  "riskAreas": [
    {"file": "path/to/file", "reason": "why this file is risky"}
  ],
  "testingRecommendations": [
    "Specific tests that should be written/run before merging"
  ]
}
RESPOND ONLY WITH VALID JSON."""


@router.post("/compare")
async def compare_branches(request: BranchCompareRequest):
    """Compare two branches and detect issues in the diff."""
    try:
        owner, repo = parse_github_url(request.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if request.base_branch == request.head_branch:
        raise HTTPException(status_code=400, detail="Base and head branches must be different")

    print(f"[BRANCH] Comparing {request.base_branch}...{request.head_branch} in {owner}/{repo}")

    try:
        clone_dir = clone_full_repo(request.repo_url)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        available_branches = subprocess.run(
            ["git", "branch", "-r"], cwd=clone_dir,
            capture_output=True, text=True, timeout=10
        ).stdout

        for branch in [request.base_branch, request.head_branch]:
            if f"origin/{branch}" not in available_branches:
                raise HTTPException(status_code=400, detail=f"Branch '{branch}' not found in repository")

        base_ref = f"origin/{request.base_branch}"
        head_ref = f"origin/{request.head_branch}"

        changed_files = get_changed_files(clone_dir, base_ref, head_ref)
        commits = get_commit_log(clone_dir, base_ref, head_ref)
        diff_stat = get_diff(clone_dir, base_ref, head_ref)
        diff_content = get_diff_content(clone_dir, base_ref, head_ref)

        if not changed_files and not diff_content:
            return {
                "repository": f"{owner}/{repo}",
                "baseBranch": request.base_branch,
                "headBranch": request.head_branch,
                "changedFiles": [],
                "commits": [],
                "analysis": {
                    "verdict": "SAFE_TO_MERGE",
                    "summary": "No differences found between branches.",
                    "totalIssues": 0,
                    "issues": [],
                },
            }

        user_message = (
            f"Repository: {owner}/{repo}\n"
            f"Comparing: {request.base_branch} ← {request.head_branch}\n"
            f"Changed files: {len(changed_files)}\n"
            f"Commits: {len(commits)}\n\n"
            f"Commit messages:\n" +
            "\n".join(f"- {c['message']} ({c['author']})" for c in commits[:20]) +
            f"\n\nDiff stats:\n{diff_stat}\n\n"
            f"Code diff (truncated):\n{diff_content[:30000]}"
        )

        try:
            raw = await call_ai(BRANCH_COMPARE_PROMPT, user_message)
            ai_analysis = clean_ai_json(raw)
        except Exception:
            ai_analysis = {
                "verdict": "NEEDS_REVIEW",
                "summary": "AI analysis could not be completed. Manual review recommended.",
                "totalIssues": 0,
                "issues": [],
            }

        return {
            "repository": f"{owner}/{repo}",
            "baseBranch": request.base_branch,
            "headBranch": request.head_branch,
            "changedFiles": changed_files,
            "commits": commits,
            "diffStats": diff_stat,
            "analysis": ai_analysis,
        }

    finally:
        cleanup_clone(clone_dir)
