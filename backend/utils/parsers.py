# -*- coding: utf-8 -*-
"""
Shared parsing utilities: JSON response cleaning, manifest parsing.
"""

import re
import json
from typing import List
from pathlib import Path

from utils.constants import ANALYZABLE_EXTENSIONS, SKIP_DIRS, LANG_MAP


def clean_ai_json(raw: str) -> dict:
    """Strip markdown fences from AI response and parse JSON."""
    clean = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    return json.loads(clean)


def detect_language(ext: str) -> str:
    """Map file extension to language name."""
    return LANG_MAP.get(ext, "unknown")


def should_skip_path(rel_path: str) -> bool:
    """Check if a file path should be skipped during analysis."""
    parts = Path(rel_path).parts
    if any(part in SKIP_DIRS for part in parts):
        return True
    if any(part.startswith(".") for part in parts if part != "."):
        return True
    return False


def is_analyzable(ext: str) -> bool:
    """Check if a file extension is analyzable source code."""
    return ext.lower() in ANALYZABLE_EXTENSIONS


def parse_package_json(content: str) -> List[dict]:
    """Parse npm package.json into a list of dependency dicts."""
    packages = []
    try:
        data = json.loads(content)
        for dep_type in ["dependencies", "devDependencies"]:
            for name, version in data.get(dep_type, {}).items():
                clean_ver = re.sub(r"[^0-9.]", "", version)
                packages.append({
                    "name": name,
                    "version": clean_ver or version,
                    "raw_version": version,
                    "ecosystem": "npm",
                    "dev": dep_type == "devDependencies",
                })
    except json.JSONDecodeError:
        pass
    return packages


def parse_requirements_txt(content: str) -> List[dict]:
    """Parse Python requirements.txt into a list of dependency dicts."""
    packages = []
    for line in content.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = re.match(r"([a-zA-Z0-9_.-]+)\s*(?:[=<>!~]+\s*(.+))?", line)
        if match:
            name = match.group(1)
            version = (match.group(2) or "").strip().split(",")[0].strip()
            packages.append({
                "name": name,
                "version": version or "latest",
                "raw_version": line,
                "ecosystem": "PyPI",
                "dev": False,
            })
    return packages


def parse_go_mod(content: str) -> List[dict]:
    """Parse Go go.mod into a list of dependency dicts."""
    packages = []
    for line in content.strip().split("\n"):
        match = re.match(r"\s+(\S+)\s+(v[\d.]+)", line)
        if match:
            packages.append({
                "name": match.group(1),
                "version": match.group(2).lstrip("v"),
                "raw_version": match.group(2),
                "ecosystem": "Go",
                "dev": False,
            })
    return packages


def detect_manifest_type(content: str) -> str:
    """Auto-detect manifest file type from content."""
    content_stripped = content.strip()
    if content_stripped.startswith("{"):
        try:
            data = json.loads(content_stripped)
            if "dependencies" in data or "devDependencies" in data:
                return "package.json"
        except json.JSONDecodeError:
            pass
    if re.search(r"^[a-zA-Z0-9_-]+==[0-9]", content_stripped, re.MULTILINE):
        return "requirements.txt"
    if "module " in content_stripped and "go " in content_stripped:
        return "go.mod"
    if "<project" in content_stripped and "<dependencies>" in content_stripped:
        return "pom.xml"
    if re.search(r"^gem\s+", content_stripped, re.MULTILINE):
        return "Gemfile"
    return "requirements.txt"


def parse_manifest(content: str, manifest_type: str = "auto") -> List[dict]:
    """Parse any supported manifest into dependency list."""
    if manifest_type == "auto":
        manifest_type = detect_manifest_type(content)

    parsers = {
        "package.json": parse_package_json,
        "requirements.txt": parse_requirements_txt,
        "go.mod": parse_go_mod,
    }
    parser = parsers.get(manifest_type, parse_requirements_txt)
    return parser(content)
