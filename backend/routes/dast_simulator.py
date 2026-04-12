# -*- coding: utf-8 -*-
"""Simulated DAST: discover endpoints from source, generate attack scenarios, optional AI risk summary."""

import re
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ai_helper import call_ai

from utils.parsers import clean_ai_json

router = APIRouter()

ENDPOINT_PATTERNS = {
    "python": [
        (r'@(?:app|router|api)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', "decorator"),
        (r'@(?:app|router)\.route\s*\(\s*["\']([^"\']+)["\'].*methods\s*=\s*\[([^\]]+)\]', "flask_route"),
        (r'path\s*\(\s*["\']([^"\']+)["\']', "django_url"),
    ],
    "javascript": [
        (r'(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', "express"),
        (r'@(Get|Post|Put|Delete|Patch)\s*\(\s*["\']?([^"\')\s]*)["\']?\s*\)', "nestjs"),
    ],
    "typescript": [
        (r'(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', "express"),
        (r'@(Get|Post|Put|Delete|Patch)\s*\(\s*["\']?([^"\')\s]*)["\']?\s*\)', "nestjs"),
    ],
    "java": [
        (r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']', "spring"),
    ],
}

ATTACK_PAYLOADS = {
    "sql_injection": [
        "' OR '1'='1'; --",
        "'; DROP TABLE users; --",
        "' UNION SELECT * FROM information_schema.tables; --",
        "1; WAITFOR DELAY '0:0:5'; --",
    ],
    "xss": [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(document.cookie)",
        "<svg onload=alert(1)>",
    ],
    "path_traversal": [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\config\\sam",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "....//....//etc/passwd",
    ],
    "command_injection": [
        "; ls -la /",
        "| cat /etc/passwd",
        "$(whoami)",
        "`id`",
    ],
    "nosql_injection": [
        '{"$gt": ""}',
        '{"$ne": null}',
        '{"$where": "sleep(5000)"}',
    ],
    "oversized_input": [
        "A" * 10000,
        "A" * 100000,
    ],
    "special_characters": [
        "\x00\x01\x02\x03",
        "\n\r\t",
        "null",
        "undefined",
        "NaN",
        "Infinity",
    ],
}


class DASTRequest(BaseModel):
    code: str = Field(..., description="Source code to analyze for endpoints")
    language: str = Field(default="python")


class DASTRepoRequest(BaseModel):
    repo_url: str
    branch: str = Field(default="main")


def discover_endpoints(code: str, language: str) -> List[Dict]:
    """Extract API endpoint definitions from source code."""
    endpoints = []
    patterns = ENDPOINT_PATTERNS.get(language, ENDPOINT_PATTERNS.get("python", []))

    for pattern, source_type in patterns:
        for match in re.finditer(pattern, code, re.IGNORECASE):
            groups = match.groups()
            if source_type == "flask_route":
                path = groups[0]
                methods_str = groups[1]
                methods = re.findall(r"['\"](\w+)['\"]", methods_str)
            elif source_type == "decorator" or source_type == "express":
                method = groups[0].upper()
                path = groups[1]
                methods = [method]
            elif source_type == "nestjs" or source_type == "spring":
                method_map = {
                    "get": "GET", "getmapping": "GET",
                    "post": "POST", "postmapping": "POST",
                    "put": "PUT", "putmapping": "PUT",
                    "delete": "DELETE", "deletemapping": "DELETE",
                    "patch": "PATCH", "patchmapping": "PATCH",
                    "requestmapping": "GET",
                }
                method = method_map.get(groups[0].lower(), "GET")
                path = groups[1] if len(groups) > 1 else "/"
                methods = [method]
            elif source_type == "django_url":
                path = groups[0]
                methods = ["GET", "POST"]
            else:
                continue

            line_num = code[:match.start()].count("\n") + 1

            has_params = bool(re.findall(r"[{<:]\w+[}>]", path))
            has_query = "request.args" in code or "request.query" in code or "query_params" in code
            has_body = any(m in ["POST", "PUT", "PATCH"] for m in methods)

            endpoints.append({
                "path": path,
                "methods": methods,
                "line": line_num,
                "sourceType": source_type,
                "hasPathParams": has_params,
                "hasQueryParams": has_query,
                "hasBody": has_body,
            })

    return endpoints


def generate_attack_scenarios(endpoints: List[Dict]) -> List[Dict]:
    """Generate simulated attack scenarios for discovered endpoints."""
    scenarios = []

    for ep in endpoints:
        path = ep["path"]
        methods = ep["methods"]

        if ep["hasPathParams"] or ep["hasQueryParams"]:
            for payload_type in ["sql_injection", "xss", "path_traversal"]:
                payloads = ATTACK_PAYLOADS[payload_type]
                scenarios.append({
                    "endpoint": path,
                    "method": methods[0],
                    "attackType": payload_type.replace("_", " ").title(),
                    "vector": "path/query parameter",
                    "payloads": payloads[:2],
                    "severity": "critical" if payload_type == "sql_injection" else "high",
                    "description": f"Inject {payload_type.replace('_', ' ')} payload into parameters of {path}",
                    "expectedBehavior": "Server should reject input with 400 status, not reflect or execute payload",
                    "testScenario": f"Send {methods[0]} {path} with parameter set to: {payloads[0]}",
                })

        if ep["hasBody"]:
            for payload_type in ["sql_injection", "xss", "nosql_injection", "oversized_input"]:
                payloads = ATTACK_PAYLOADS[payload_type]
                sev = "critical" if "injection" in payload_type else "medium"
                scenarios.append({
                    "endpoint": path,
                    "method": methods[0],
                    "attackType": payload_type.replace("_", " ").title(),
                    "vector": "request body",
                    "payloads": [str(p)[:100] for p in payloads[:2]],
                    "severity": sev,
                    "description": f"Send {payload_type.replace('_', ' ')} payload in request body to {path}",
                    "expectedBehavior": "Server should validate and sanitize all input fields",
                    "testScenario": f"Send {methods[0]} {path} with body containing: {str(payloads[0])[:80]}",
                })

        scenarios.append({
            "endpoint": path,
            "method": methods[0],
            "attackType": "Rate Abuse",
            "vector": "repeated requests",
            "payloads": ["100 requests/second", "1000 requests in burst"],
            "severity": "medium",
            "description": f"Flood {path} with rapid repeated requests to test rate limiting",
            "expectedBehavior": "Server should implement rate limiting and return 429 after threshold",
            "testScenario": f"Send 100 {methods[0]} requests to {path} within 1 second",
        })

        for payload_type in ["command_injection", "special_characters"]:
            payloads = ATTACK_PAYLOADS[payload_type]
            scenarios.append({
                "endpoint": path,
                "method": methods[0],
                "attackType": payload_type.replace("_", " ").title(),
                "vector": "any input field",
                "payloads": payloads[:2],
                "severity": "critical" if payload_type == "command_injection" else "low",
                "description": f"Test {path} with {payload_type.replace('_', ' ')} to check input sanitization",
                "expectedBehavior": "Server must never execute injected commands or crash on special chars",
                "testScenario": f"Send {methods[0]} {path} with input: {payloads[0]}",
            })

    return scenarios


DAST_AI_PROMPT = """You are a Senior Penetration Tester performing a simulated DAST assessment.

Given the discovered API endpoints and attack scenarios, provide a risk assessment.

Respond ONLY in this JSON:
{
  "overallRisk": "HIGH",
  "riskScore": 35,
  "summary": "2-3 sentence assessment",
  "endpointRisks": [
    {"endpoint": "/api/users", "riskLevel": "critical", "reason": "No input validation detected", "recommendations": ["Add parameterized queries", "Implement rate limiting"]}
  ],
  "missingProtections": [
    {"protection": "Rate Limiting", "impact": "DoS vulnerability", "recommendation": "Use middleware like slowapi or express-rate-limit"}
  ],
  "prioritizedFixes": [
    {"priority": 1, "title": "Fix SQL injection", "endpoint": "/api/users", "effort": "low"}
  ]
}
RESPOND ONLY WITH VALID JSON."""


@router.post("/scan")
async def dast_scan(request: DASTRequest):
    """Discover endpoints and generate simulated DAST scenarios."""
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="No code provided")

    endpoints = discover_endpoints(request.code, request.language)
    scenarios = generate_attack_scenarios(endpoints)

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for s in scenarios:
        sev = s.get("severity", "low")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    ep_summary = "\n".join(
        f"- {e['methods']} {e['path']} (params: {e['hasPathParams']}, body: {e['hasBody']})"
        for e in endpoints
    )
    scenario_summary = "\n".join(
        f"- {s['attackType']} on {s['endpoint']} ({s['severity']})"
        for s in scenarios[:20]
    )

    try:
        msg = f"Endpoints found:\n{ep_summary}\n\nAttack scenarios:\n{scenario_summary}\n\nSource language: {request.language}"
        raw = await call_ai(DAST_AI_PROMPT, msg)
        ai_analysis = clean_ai_json(raw)
    except Exception:
        ai_analysis = {"overallRisk": "UNKNOWN", "riskScore": 50, "summary": "Analysis completed with partial results."}

    return {
        "endpoints": endpoints,
        "totalEndpoints": len(endpoints),
        "attackScenarios": scenarios,
        "totalScenarios": len(scenarios),
        "severityCounts": severity_counts,
        "analysis": ai_analysis,
    }
