# -*- coding: utf-8 -*-
"""GitHub repository intelligence: clone, scan, and structured analysis."""

import json
import re
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_helper import call_ai
from utils.constants import (
    ANALYZABLE_EXTENSIONS,
    CONFIG_FILES,
    MAX_FILE_SIZE,
    MAX_FILES_TO_ANALYZE,
)
from utils.git_ops import cleanup_clone, clone_repo, parse_github_url
from utils.parsers import clean_ai_json, detect_language, should_skip_path

router = APIRouter()


class RepoRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main", description="Branch to analyze")


class RepoFileInfo(BaseModel):
    path: str
    language: str
    size: int
    role: str = ""


def classify_file_role(path: str) -> str:
    p = path.lower()
    if any(k in p for k in ["test", "spec", "__test__"]):
        return "test"
    if any(k in p for k in ["controller", "handler", "endpoint", "view"]):
        return "controller"
    if any(k in p for k in ["service", "usecase", "interactor"]):
        return "service"
    if any(k in p for k in ["model", "schema", "entity", "dto"]):
        return "model"
    if any(k in p for k in ["util", "helper", "lib", "common", "shared"]):
        return "utility"
    if any(k in p for k in ["middleware", "guard", "interceptor"]):
        return "middleware"
    if any(k in p for k in ["config", "setting"]):
        return "config"
    if any(k in p for k in ["route", "router", "url"]):
        return "routing"
    if any(k in p for k in ["migration", "seed"]):
        return "database"
    if any(k in p for k in ["component", "page", "widget"]):
        return "ui-component"
    return "source"


def scan_repo(clone_dir: Path) -> dict:
    """Walk the repo and collect file metadata and tech stack signals."""
    files: List[dict] = []
    language_counts: Dict[str, int] = {}
    total_lines = 0
    config_found = {}
    test_files = []
    source_files = []

    for fpath in sorted(clone_dir.rglob("*")):
        if not fpath.is_file():
            continue
        rel = str(fpath.relative_to(clone_dir))
        if should_skip_path(rel):
            continue

        if fpath.name in CONFIG_FILES or fpath.name in {
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
            ".eslintrc.js", ".prettierrc", "jest.config.js",
        }:
            try:
                config_found[fpath.name] = fpath.read_text(errors="ignore")[:3000]
            except Exception:
                pass

        ext = fpath.suffix.lower()
        if ext not in ANALYZABLE_EXTENSIONS:
            continue

        try:
            size = fpath.stat().st_size
            if size > MAX_FILE_SIZE:
                continue
            content = fpath.read_text(errors="ignore")
            line_count = content.count("\n") + 1
            total_lines += line_count
        except Exception:
            continue

        lang = detect_language(ext)
        language_counts[lang] = language_counts.get(lang, 0) + line_count
        role = classify_file_role(rel)

        file_info = {"path": rel, "language": lang, "size": size, "lines": line_count, "role": role}
        files.append(file_info)

        if role == "test":
            test_files.append(rel)
        else:
            source_files.append(rel)

    frameworks = detect_frameworks(config_found)
    architecture = detect_architecture(files)

    return {
        "totalFiles": len(files),
        "totalLines": total_lines,
        "languages": language_counts,
        "frameworks": frameworks,
        "architecture": architecture,
        "files": files[:MAX_FILES_TO_ANALYZE],
        "testFiles": test_files,
        "sourceFiles": source_files,
        "configFiles": list(config_found.keys()),
        "testCoverage": {
            "sourceCount": len(source_files),
            "testCount": len(test_files),
            "ratio": round(len(test_files) / max(len(source_files), 1) * 100, 1),
        },
    }


def detect_frameworks(configs: dict) -> List[dict]:
    frameworks = []

    if "package.json" in configs:
        try:
            pkg = json.loads(configs["package.json"])
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            fw_map = {
                "react": "React", "next": "Next.js", "@angular/core": "Angular",
                "vue": "Vue.js", "svelte": "Svelte", "express": "Express.js",
                "fastify": "Fastify", "nestjs": "NestJS", "jest": "Jest",
                "mocha": "Mocha", "tailwindcss": "Tailwind CSS",
                "typescript": "TypeScript", "vite": "Vite", "webpack": "Webpack",
            }
            for key, name in fw_map.items():
                if key in deps:
                    frameworks.append({"name": name, "version": deps[key], "source": "package.json"})
        except json.JSONDecodeError:
            pass

    if "requirements.txt" in configs:
        lines = configs["requirements.txt"].strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"([a-zA-Z0-9_-]+)(?:[=<>!~]+(.*))?", line)
            if match:
                name, ver = match.group(1), match.group(2) or "latest"
                fw_map = {
                    "fastapi": "FastAPI", "flask": "Flask", "django": "Django",
                    "pytest": "pytest", "sqlalchemy": "SQLAlchemy",
                    "celery": "Celery", "pydantic": "Pydantic",
                }
                if name.lower() in fw_map:
                    frameworks.append({"name": fw_map[name.lower()], "version": ver, "source": "requirements.txt"})

    if "go.mod" in configs:
        frameworks.append({"name": "Go Modules", "version": "", "source": "go.mod"})
    if "Cargo.toml" in configs:
        frameworks.append({"name": "Rust/Cargo", "version": "", "source": "Cargo.toml"})
    if "pom.xml" in configs:
        frameworks.append({"name": "Maven (Java)", "version": "", "source": "pom.xml"})
    if "Dockerfile" in configs:
        frameworks.append({"name": "Docker", "version": "", "source": "Dockerfile"})

    return frameworks


def detect_architecture(files: List[dict]) -> dict:
    roles = [f["role"] for f in files]
    has_controllers = "controller" in roles or "routing" in roles
    has_services = "service" in roles
    has_models = "model" in roles
    has_middleware = "middleware" in roles
    has_ui = "ui-component" in roles

    if has_controllers and has_services and has_models and has_middleware:
        pattern = "Clean / Layered Architecture"
        desc = "Well-separated concerns with controllers, services, models, and middleware layers."
    elif has_controllers and has_services and has_models:
        pattern = "MVC / Three-Tier Architecture"
        desc = "Standard Model-View-Controller pattern with clear separation."
    elif has_ui and (has_services or has_controllers):
        pattern = "Full-Stack Application"
        desc = "Frontend components with backend services in a single repository."
    elif has_ui and not has_services:
        pattern = "Frontend SPA"
        desc = "Single-page application focused on UI components."
    else:
        pattern = "Monolithic / Flat Structure"
        desc = "Files organized without strong architectural patterns."

    return {"pattern": pattern, "description": desc}


REPO_ANALYSIS_PROMPT = """You are a Senior Software Architect performing a repository intelligence analysis.

Given the repository scan data below, provide a comprehensive analysis covering:

1. **Tech Stack Summary** - what technologies are used and how they fit together
2. **Architecture Assessment** - the architectural pattern, its strengths and weaknesses
3. **Code Organization** - how well the code is organized, naming conventions
4. **Test Coverage Assessment** - are tests adequate? what's missing?
5. **Key Relationships** - how do the main files/modules depend on each other?
6. **Risk Areas** - files or patterns that could cause issues
7. **Recommendations** - top 5 actionable improvements

Respond ONLY in this JSON format:
{
  "techStackSummary": "2-3 paragraph summary of the tech stack",
  "architectureAssessment": "2-3 paragraph assessment",
  "codeOrganization": "assessment of file structure and naming",
  "testCoverageAssessment": "assessment of test coverage",
  "fileRelationships": [
    {"from": "file1.py", "to": "file2.py", "relationship": "imports/calls"}
  ],
  "riskAreas": [
    {"file": "path/to/file", "risk": "description of risk", "severity": "high|medium|low"}
  ],
  "recommendations": [
    {"priority": 1, "title": "short title", "description": "what to do and why", "impact": "high|medium|low"}
  ],
  "overallScore": 72,
  "scores": {
    "codeQuality": 75,
    "architecture": 70,
    "testCoverage": 50,
    "security": 65,
    "maintainability": 80
  }
}
RESPOND ONLY WITH VALID JSON."""


@router.post("/analyze")
async def analyze_repo(request: RepoRequest):
    """Clone a GitHub repo, scan it, and return a full intelligence report."""
    try:
        owner, repo = parse_github_url(request.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    print(f"[REPO] Cloning {owner}/{repo} @ {request.branch}")

    try:
        clone_dir = clone_repo(request.repo_url, request.branch)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        scan_data = scan_repo(clone_dir)

        file_summary = "\n".join(
            f"- {f['path']} ({f['language']}, {f['lines']} lines, role: {f['role']})"
            for f in scan_data["files"][:50]
        )
        framework_summary = "\n".join(
            f"- {fw['name']} {fw['version']} (from {fw['source']})"
            for fw in scan_data["frameworks"]
        )

        user_message = (
            f"Repository: {owner}/{repo}\n"
            f"Branch: {request.branch}\n"
            f"Total Files: {scan_data['totalFiles']}\n"
            f"Total Lines: {scan_data['totalLines']}\n"
            f"Languages: {json.dumps(scan_data['languages'])}\n"
            f"Architecture detected: {scan_data['architecture']['pattern']}\n"
            f"Test files: {scan_data['testCoverage']['testCount']} / Source files: {scan_data['testCoverage']['sourceCount']}\n\n"
            f"Frameworks:\n{framework_summary}\n\n"
            f"File listing:\n{file_summary}"
        )

        try:
            raw = await call_ai(REPO_ANALYSIS_PROMPT, user_message)
            ai_analysis = clean_ai_json(raw)
        except Exception:
            ai_analysis = {}

        result = {
            "repository": f"{owner}/{repo}",
            "branch": request.branch,
            "scan": scan_data,
            "analysis": ai_analysis,
        }
        return result

    finally:
        cleanup_clone(clone_dir)


@router.post("/scan-files")
async def scan_repo_files(request: RepoRequest):
    """Return file list and structure without AI analysis."""
    try:
        owner, repo = parse_github_url(request.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        clone_dir = clone_repo(request.repo_url, request.branch)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        scan_data = scan_repo(clone_dir)
        return {"repository": f"{owner}/{repo}", "branch": request.branch, "scan": scan_data}
    finally:
        cleanup_clone(clone_dir)


@router.post("/file-content")
async def get_file_content(request: RepoRequest, file_path: str = ""):
    """Clone the repo and return content of a single file."""
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path query param required")

    try:
        clone_dir = clone_repo(request.repo_url, request.branch)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        target = clone_dir / file_path
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        content = target.read_text(errors="ignore")[:MAX_FILE_SIZE]
        ext = target.suffix.lower()
        return {"path": file_path, "language": detect_language(ext), "content": content}
    finally:
        cleanup_clone(clone_dir)
