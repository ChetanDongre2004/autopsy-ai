# -*- coding: utf-8 -*-
"""Dependency scanning: OSV.dev CVE lookup and AI analysis of package manifests."""

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx

from ai_helper import call_ai
from utils.parsers import clean_ai_json, parse_manifest, detect_manifest_type

router = APIRouter()

OSV_API = "https://api.osv.dev/v1/query"


class DependencyRequest(BaseModel):
    manifest_content: str = Field(..., description="Content of package.json, requirements.txt, etc.")
    manifest_type: str = Field(default="auto", description="Type: package.json, requirements.txt, go.mod, pom.xml, or auto")


class RepoDependencyRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main")


async def check_osv_vulnerability(package_name: str, version: str, ecosystem: str) -> List[dict]:
    """Query OSV.dev for known vulnerabilities."""
    eco_map = {"npm": "npm", "PyPI": "PyPI", "Go": "Go", "maven": "Maven"}
    osv_ecosystem = eco_map.get(ecosystem, ecosystem)

    payload = {"package": {"name": package_name, "ecosystem": osv_ecosystem}}
    if version and version != "latest":
        payload["version"] = version

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(OSV_API, json=payload)
            if resp.status_code != 200:
                return []
            data = resp.json()
            vulns = []
            for v in data.get("vulns", []):
                severity = "medium"
                cvss = None
                for s in v.get("severity", []):
                    score_str = s.get("score", "")
                    if "CVSS" in s.get("type", ""):
                        try:
                            parts = score_str.split("/")
                            for part in parts:
                                if part.replace(".", "").isdigit():
                                    cvss = float(part)
                                    break
                        except (ValueError, IndexError):
                            pass

                if cvss:
                    if cvss >= 9.0:
                        severity = "critical"
                    elif cvss >= 7.0:
                        severity = "high"
                    elif cvss >= 4.0:
                        severity = "medium"
                    else:
                        severity = "low"

                aliases = v.get("aliases", [])
                cve_id = next((a for a in aliases if a.startswith("CVE-")), v.get("id", ""))

                fixed_version = ""
                for affected in v.get("affected", []):
                    for r in affected.get("ranges", []):
                        for event in r.get("events", []):
                            if "fixed" in event:
                                fixed_version = event["fixed"]

                vulns.append({
                    "id": v.get("id", ""),
                    "cve": cve_id,
                    "summary": v.get("summary", v.get("details", "")[:200]),
                    "severity": severity,
                    "cvss": cvss,
                    "fixedIn": fixed_version,
                    "url": f"https://osv.dev/vulnerability/{v.get('id', '')}",
                })
            return vulns
    except Exception:
        return []


DEPENDENCY_AI_PROMPT = """You are a Senior DevOps Engineer analyzing project dependencies.

Given the dependency scan results, provide:
1. Overall health assessment of the dependency tree
2. Prioritized upgrade recommendations
3. Potential version conflicts
4. Security risk summary

Respond ONLY in this JSON format:
{
  "healthScore": 75,
  "summary": "2-3 sentence overview",
  "upgradeRecommendations": [
    {"package": "name", "current": "1.0", "recommended": "2.0", "reason": "why", "priority": "high|medium|low", "breakingChanges": true}
  ],
  "conflicts": [
    {"packages": ["pkg1", "pkg2"], "issue": "description"}
  ],
  "securitySummary": "paragraph about security posture",
  "categories": {
    "critical": 0,
    "outdated": 0,
    "healthy": 0,
    "devOnly": 0
  }
}
RESPOND ONLY WITH VALID JSON."""


@router.post("/scan")
async def scan_dependencies(request: DependencyRequest):
    """Scan a manifest file for vulnerabilities and outdated packages."""
    if not request.manifest_content.strip():
        raise HTTPException(status_code=400, detail="Empty manifest content")

    manifest_type = request.manifest_type
    if manifest_type == "auto":
        manifest_type = detect_manifest_type(request.manifest_content)

    packages = parse_manifest(request.manifest_content, manifest_type)
    if not packages:
        raise HTTPException(status_code=400, detail="No packages found in manifest")

    print(f"[DEPS] Scanning {len(packages)} packages from {manifest_type}")

    results = []
    total_vulns = 0
    critical_count = 0

    for pkg in packages:
        vulns = await check_osv_vulnerability(pkg["name"], pkg["version"], pkg["ecosystem"])
        pkg_result = {
            **pkg,
            "vulnerabilities": vulns,
            "vulnerable": len(vulns) > 0,
            "vulnCount": len(vulns),
        }
        results.append(pkg_result)
        total_vulns += len(vulns)
        critical_count += sum(1 for v in vulns if v["severity"] in ("critical", "high"))

    scan_summary = "\n".join(
        f"- {r['name']}@{r['version']} ({r['ecosystem']}) — {r['vulnCount']} vulnerabilities"
        for r in results if r["vulnCount"] > 0
    )
    healthy = [r for r in results if r["vulnCount"] == 0]

    user_message = (
        f"Manifest type: {manifest_type}\n"
        f"Total packages: {len(packages)}\n"
        f"Vulnerable packages: {sum(1 for r in results if r['vulnerable'])}\n"
        f"Total vulnerabilities: {total_vulns}\n"
        f"Critical/High: {critical_count}\n\n"
        f"Vulnerable:\n{scan_summary or 'None'}\n\n"
        f"Healthy packages: {len(healthy)}\n"
        f"Full package list:\n" +
        "\n".join(f"- {r['name']}@{r['version']}" for r in results)
    )

    try:
        raw = await call_ai(DEPENDENCY_AI_PROMPT, user_message)
        ai_analysis = clean_ai_json(raw)
    except Exception:
        ai_analysis = {"healthScore": max(0, 100 - total_vulns * 15), "summary": f"Found {total_vulns} vulnerabilities across {len(packages)} packages."}

    return {
        "manifestType": manifest_type,
        "totalPackages": len(packages),
        "totalVulnerabilities": total_vulns,
        "criticalCount": critical_count,
        "packages": results,
        "analysis": ai_analysis,
    }
