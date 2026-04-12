# -*- coding: utf-8 -*-
"""Outdated package checker: PyPI and npm latest versions vs manifest dependencies."""

import re
import json
from typing import Dict, List, Optional, Tuple
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx

router = APIRouter()


class PackageCheckRequest(BaseModel):
    manifest_content: str = Field(..., description="Content of package.json or requirements.txt")
    manifest_type: str = Field(default="auto")


def detect_type(content: str) -> str:
    if content.strip().startswith("{"):
        return "package.json"
    return "requirements.txt"


def parse_version(v: str) -> Tuple[int, ...]:
    """Parse semver string into comparable tuple."""
    nums = re.findall(r"\d+", v)
    return tuple(int(n) for n in nums[:3]) if nums else (0,)


def version_diff(current: str, latest: str) -> str:
    """Classify update as major, minor, patch, or up-to-date."""
    c = parse_version(current)
    l = parse_version(latest)
    if len(c) < 3:
        c = c + (0,) * (3 - len(c))
    if len(l) < 3:
        l = l + (0,) * (3 - len(l))
    if l[0] > c[0]:
        return "major"
    if l[1] > c[1]:
        return "minor"
    if l[2] > c[2]:
        return "patch"
    return "up-to-date"


async def check_pypi(name: str) -> Optional[Dict]:
    """Query PyPI for latest version of a Python package."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://pypi.org/pypi/{name}/json")
            if resp.status_code != 200:
                return None
            data = resp.json()
            info = data.get("info", {})
            return {
                "latestVersion": info.get("version", ""),
                "summary": info.get("summary", ""),
                "homePage": info.get("home_page") or info.get("project_url", ""),
                "license": info.get("license", ""),
                "pythonRequires": info.get("requires_python", ""),
            }
    except Exception:
        return None


async def check_npm(name: str) -> Optional[Dict]:
    """Query npm registry for latest version."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://registry.npmjs.org/{name}")
            if resp.status_code != 200:
                return None
            data = resp.json()
            latest = data.get("dist-tags", {}).get("latest", "")
            latest_info = data.get("versions", {}).get(latest, {})
            return {
                "latestVersion": latest,
                "summary": data.get("description", ""),
                "homePage": data.get("homepage", ""),
                "license": latest_info.get("license", ""),
                "deprecated": bool(data.get("deprecated") or latest_info.get("deprecated")),
            }
    except Exception:
        return None


@router.post("/check")
async def check_outdated(request: PackageCheckRequest):
    """Check all packages for outdated versions."""
    mtype = request.manifest_type
    if mtype == "auto":
        mtype = detect_type(request.manifest_content)

    packages = []

    if mtype == "package.json":
        try:
            data = json.loads(request.manifest_content)
            for dep_type in ["dependencies", "devDependencies"]:
                for name, ver in data.get(dep_type, {}).items():
                    clean_ver = re.sub(r"[^0-9.]", "", ver)
                    packages.append({"name": name, "version": clean_ver or "0.0.0", "raw": ver, "ecosystem": "npm", "dev": dep_type == "devDependencies"})
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid package.json")
    else:
        for line in request.manifest_content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            match = re.match(r"([a-zA-Z0-9_.-]+)\s*(?:==|>=|~=|<=)?\s*(.+)?", line)
            if match:
                name = match.group(1)
                ver = (match.group(2) or "").strip().split(",")[0].strip()
                packages.append({"name": name, "version": ver or "0.0.0", "raw": line, "ecosystem": "PyPI", "dev": False})

    if not packages:
        raise HTTPException(status_code=400, detail="No packages found")

    results = []
    outdated_count = 0
    major_updates = 0
    deprecated_count = 0

    for pkg in packages:
        if pkg["ecosystem"] == "npm":
            info = await check_npm(pkg["name"])
        else:
            info = await check_pypi(pkg["name"])

        if info:
            latest = info["latestVersion"]
            diff = version_diff(pkg["version"], latest)
            is_outdated = diff != "up-to-date"
            if is_outdated:
                outdated_count += 1
            if diff == "major":
                major_updates += 1
            if info.get("deprecated"):
                deprecated_count += 1

            results.append({
                **pkg,
                "latestVersion": latest,
                "updateType": diff,
                "outdated": is_outdated,
                "deprecated": info.get("deprecated", False),
                "summary": info.get("summary", ""),
                "license": info.get("license", ""),
            })
        else:
            results.append({**pkg, "latestVersion": "unknown", "updateType": "unknown", "outdated": False})

    return {
        "manifestType": mtype,
        "totalPackages": len(results),
        "outdatedCount": outdated_count,
        "majorUpdates": major_updates,
        "deprecatedCount": deprecated_count,
        "upToDateCount": len(results) - outdated_count,
        "packages": results,
        "healthScore": max(0, 100 - outdated_count * 8 - major_updates * 5 - deprecated_count * 15),
    }
