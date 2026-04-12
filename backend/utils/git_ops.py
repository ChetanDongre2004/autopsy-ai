# -*- coding: utf-8 -*-
"""
Shared Git operations: URL parsing, repo cloning, branch operations.
Used by repo_analyzer, branch_comparator, dashboard, repo_qa_scanner.
"""

import re
import shutil
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger("autopsy.git")

CLONE_BASE = Path(__file__).resolve().parent.parent.parent / "cloned_repos"
CLONE_BASE.mkdir(exist_ok=True)


def parse_github_url(url: str) -> Tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL."""
    url = url.strip().rstrip("/").replace(".git", "")
    match = re.match(r"(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/]+)", url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return match.group(1), match.group(2)


def clone_repo(repo_url: str, branch: str = "main", tag: str = "") -> Path:
    """
    Shallow-clone a GitHub repo. Falls back to default branch if specified
    branch doesn't exist. `tag` is appended to the clone directory name
    for isolation between features.
    """
    owner, repo = parse_github_url(repo_url)
    suffix = f"__{tag}" if tag else ""
    clone_dir = CLONE_BASE / f"{owner}__{repo}__{branch}{suffix}"

    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    clean_url = f"https://github.com/{owner}/{repo}.git"
    cmd = ["git", "clone", "--depth", "1", "--branch", branch, clean_url, str(clone_dir)]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)
    except subprocess.CalledProcessError:
        cmd_fallback = ["git", "clone", "--depth", "1", clean_url, str(clone_dir)]
        try:
            subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=120, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to clone {owner}/{repo}: {e.stderr}")

    return clone_dir


def clone_full_repo(repo_url: str) -> Path:
    """Full clone (not shallow) needed for branch comparison."""
    owner, repo = parse_github_url(repo_url)
    clone_dir = CLONE_BASE / f"{owner}__{repo}__full"

    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    clean_url = f"https://github.com/{owner}/{repo}.git"
    try:
        subprocess.run(
            ["git", "clone", clean_url, str(clone_dir)],
            capture_output=True, text=True, timeout=180, check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to clone {owner}/{repo}: {e.stderr}")

    return clone_dir


def cleanup_clone(clone_dir: Path) -> None:
    """Safely remove a cloned repo directory."""
    if clone_dir and clone_dir.exists():
        shutil.rmtree(clone_dir, ignore_errors=True)
