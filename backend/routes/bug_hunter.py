# -*- coding: utf-8 -*-
"""Security scanner: static regex pass plus AI OWASP-style audit."""

import re
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ai_helper import call_ai
from utils.parsers import clean_ai_json

router = APIRouter()


class AuditRequest(BaseModel):
    code: str
    language: str = "python"


def run_static_scan(code: str) -> list:
    """Regex-based scan for common credential, injection, and crypto issues."""
    findings = []

    credential_patterns = [
        (r'(?i)\bapi[_-]?key\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded API Key"),
        (r'(?i)\bpassword\s*=\s*["\'][^"\']{4,}["\']', "Hardcoded Password"),
        (r'(?i)\bpasswd\s*=\s*["\'][^"\']{4,}["\']', "Hardcoded Password"),
        (r'(?i)\bsecret\s*=\s*["\'][^"\']{4,}["\']', "Hardcoded Secret"),
        (r'(?i)\btoken\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded Token"),
        (r'(?i)\bdb_pass(word)?\s*=\s*["\'][^"\']{4,}["\']', "Hardcoded DB Password"),
        (r'(?i)\bprivate_key\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded Private Key"),
        (r'sk_live_[a-zA-Z0-9]{20,}', "Stripe Live Secret Key Exposed"),
        (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID Exposed"),
        (r'(?i)bearer\s+[a-zA-Z0-9\-_\.]{20,}', "Hardcoded Bearer Token"),
    ]

    for pattern, vuln_name in credential_patterns:
        match = re.search(pattern, code)
        if match:
            evidence = match.group(0)[:60]
            findings.append({
                "category": "Hardcoded Credential",
                "subtype": vuln_name,
                "severity": "critical",
                "evidence": evidence + ("..." if len(match.group(0)) > 60 else ""),
                "line": code[:match.start()].count('\n') + 1,
                "static_detection": True,
                "owaspCategory": "A07:2021 – Identification and Authentication Failures",
                "cweId": "CWE-798",
                "remediation": "Move credentials to environment variables. Use os.getenv('API_KEY') instead.",
            })

    dangerous_fns = [
        (r'\beval\s*\(',     "eval() — executes arbitrary code as Python",   "CWE-95"),
        (r'\bexec\s*\(',     "exec() — executes arbitrary code",              "CWE-95"),
        (r'\bcompile\s*\(',  "compile() — can be used to execute code",       "CWE-95"),
        (r'\bpickle\.loads', "pickle.loads() — unsafe deserialization",       "CWE-502"),
        (r'\byaml\.load\(',  "yaml.load() — use yaml.safe_load() instead",   "CWE-502"),
        (r'\bos\.system\s*\(', "os.system() — shell injection risk",         "CWE-78"),
        (r'\bsubprocess\.call\s*\(.*shell\s*=\s*True',
                              "subprocess with shell=True — command injection","CWE-78"),
        (r'\b__import__\s*\(', "__import__() — dynamic import from user input","CWE-95"),
    ]

    for pattern, description, cwe in dangerous_fns:
        match = re.search(pattern, code)
        if match:
            findings.append({
                "category": "Dangerous Function Usage",
                "subtype": description,
                "severity": "critical",
                "line": code[:match.start()].count('\n') + 1,
                "evidence": match.group(0),
                "static_detection": True,
                "owaspCategory": "A08:2021 – Software and Data Integrity Failures",
                "cweId": cwe,
                "remediation": f"Replace {match.group(0).split('(')[0]}() with a safer alternative.",
            })

    sql_patterns = [
        r'(?i)(SELECT|INSERT|UPDATE|DELETE).*["\'].*\+\s*\w',
        r'(?i)query\s*=\s*["\'].*["\']\s*[\+%]',
        r'(?i)f["\'].*SELECT.*\{',
        r'(?i)f["\'].*WHERE.*\{',
        r'(?i)\.format\(.*\).*(?:WHERE|SELECT)',
    ]

    already_found_sql = False
    for pattern in sql_patterns:
        match = re.search(pattern, code, re.DOTALL)
        if match and not already_found_sql:
            findings.append({
                "category": "SQL Injection",
                "subtype": "String concatenation / f-string in SQL query",
                "severity": "critical",
                "line": code[:match.start()].count('\n') + 1,
                "evidence": match.group(0)[:80],
                "static_detection": True,
                "owaspCategory": "A03:2021 – Injection",
                "cweId": "CWE-89",
                "remediation": "Use parameterized queries: cursor.execute('SELECT * FROM t WHERE x=%s', (val,))",
            })
            already_found_sql = True

    weak_crypto = [
        (r'hashlib\.md5\(',  "MD5 is cryptographically broken — use sha256"),
        (r'hashlib\.sha1\(', "SHA1 is deprecated for security — use sha256"),
        (r'(?i)DES\b',       "DES encryption is broken — use AES-256"),
    ]
    for pattern, desc in weak_crypto:
        if re.search(pattern, code):
            findings.append({
                "category": "Weak Cryptography",
                "subtype": desc,
                "severity": "high",
                "static_detection": True,
                "owaspCategory": "A02:2021 – Cryptographic Failures",
                "cweId": "CWE-327",
                "remediation": "Use hashlib.sha256() or the cryptography library.",
            })

    return findings


SECURITY_SYSTEM_PROMPT = """You are a Senior Application Security Engineer (AppSec) at a cybersecurity firm.
You specialize in code security audits following the OWASP Top 10 framework.

Perform a COMPREHENSIVE security audit. For each vulnerability:
- Explain WHAT the vulnerability is
- Explain WHY it's dangerous (what can an attacker do?)
- Show the EXACT line/code that's vulnerable
- Provide a WORKING secure alternative

Check for these vulnerability classes:
1. INJECTION (SQL, Command, LDAP, XPath) — A03:2021
2. HARDCODED SECRETS (passwords, API keys, tokens in source code) — A07:2021
3. DANGEROUS FUNCTIONS (eval, exec, pickle.loads, os.system) — A08:2021
4. BROKEN AUTHENTICATION (no input validation, weak session handling) — A07:2021
5. SENSITIVE DATA EXPOSURE (logging passwords, storing plaintext) — A02:2021
6. SECURITY MISCONFIGURATION (debug=True, default credentials) — A05:2021
7. PATH TRAVERSAL (unsanitized file paths) — A01:2021
8. SSRF (unvalidated URLs in requests) — A10:2021
9. INSECURE DESERIALIZATION (pickle, yaml.load, eval on JSON) — A08:2021
10. INSUFFICIENT LOGGING (no audit trail for sensitive operations) — A09:2021

Respond ONLY in this exact JSON format:
{
  "riskLevel": "CRITICAL",
  "riskScore": 22,
  "executiveSummary": "2-3 sentence summary of the security posture of this code",
  "vulnerabilities": [
    {
      "id": "VULN-001",
      "category": "SQL Injection",
      "severity": "critical",
      "line": 24,
      "vulnerableCode": "query = 'SELECT * FROM users WHERE name = ' + user_input",
      "description": "User input is directly concatenated into a SQL query without any sanitization or parameterization.",
      "attackScenario": "Attacker sends: ' OR '1'='1'; DROP TABLE users; -- which would delete the entire users table.",
      "impact": "Complete database compromise — attacker can read, modify, or destroy all data.",
      "remediation": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE name = %s', (user_input,))",
      "secureExample": "# Safe version\\ncursor.execute('SELECT * FROM users WHERE name = %s', (user_input,))",
      "owaspCategory": "A03:2021 – Injection",
      "cweId": "CWE-89",
      "cvssScore": 9.8
    }
  ],
  "statistics": {
    "totalVulnerabilities": 4,
    "critical": 2,
    "high": 1,
    "medium": 1,
    "low": 0
  },
  "recommendations": [
    "Immediate action required: Remove all hardcoded credentials",
    "Use environment variables for all secrets (python-dotenv)"
  ]
}

riskScore: 0 (most dangerous) to 100 (most secure). Lower = worse.
riskLevel: CRITICAL (0-30), HIGH (31-55), MEDIUM (56-75), LOW (76-100)
RESPOND ONLY WITH VALID JSON."""


@router.post("/")
async def security_audit(request: AuditRequest):
    """Run static scan plus AI audit; return risk report and merged vulnerabilities."""
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="No code provided.")

    print(f"[AUDIT] Starting security audit — {len(request.code)} chars")

    static_findings = run_static_scan(request.code)
    print(f"[AUDIT] Static scan: {len(static_findings)} issues found")

    static_context = ""
    if static_findings:
        static_context = (
            f"\n\nNote: Static analysis already confirmed these issues "
            f"(include them in your vulnerabilities array):\n"
            + "\n".join(f"- {f['category']}: {f['subtype']}" for f in static_findings)
        )

    user_message = (
        f"Perform a full OWASP Top 10 security audit on this {request.language} code.\n"
        f"Be thorough — trace data flow from user inputs through the entire code.\n\n"
        f"```{request.language}\n{request.code}\n```"
        f"{static_context}"
    )

    try:
        ai_response = await call_ai(SECURITY_SYSTEM_PROMPT, user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        result = clean_ai_json(ai_response)
    except json.JSONDecodeError:
        result = {
            "riskLevel": "UNKNOWN",
            "riskScore": 50,
            "executiveSummary": ai_response[:400],
            "vulnerabilities": static_findings,
            "statistics": {
                "totalVulnerabilities": len(static_findings),
                "critical": len([f for f in static_findings if f.get("severity") == "critical"]),
                "high": 0, "medium": 0, "low": 0
            },
            "rawResponse": True,
        }

    if "vulnerabilities" in result:
        ai_categories = {v.get("category", "").lower() for v in result["vulnerabilities"]}
        for sf in static_findings:
            if sf["category"].lower() not in ai_categories:
                result["vulnerabilities"].insert(0, {
                    "id": f"STATIC-{sf['cweId']}",
                    "category": sf["category"],
                    "severity": sf["severity"],
                    "line": sf.get("line"),
                    "description": f"Static analysis detected: {sf['subtype']}",
                    "evidence": sf.get("evidence", ""),
                    "remediation": sf.get("remediation", ""),
                    "owaspCategory": sf.get("owaspCategory", ""),
                    "cweId": sf.get("cweId", ""),
                    "static_detection": True,
                })
        if "statistics" in result:
            result["statistics"]["totalVulnerabilities"] = len(result["vulnerabilities"])

    print(f"[AUDIT] Done. Risk: {result.get('riskLevel')} | Score: {result.get('riskScore')}/100")
    return result
