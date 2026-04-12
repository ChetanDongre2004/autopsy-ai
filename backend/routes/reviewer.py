# -*- coding: utf-8 -*-
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ai_helper import call_ai
from utils.parsers import clean_ai_json

router = APIRouter()

class ReviewRequest(BaseModel):
    code: str
    language: str = "python"

REVIEWER_SYSTEM_PROMPT = """You are an elite Senior Principal Software Engineer performing a SonarQube-style code review.

First, verify if the code has valid syntax. If it contains syntax errors, report them as critical issues.

Analyze the code for these SPECIFIC issues:
1. HIGH CYCLOMATIC COMPLEXITY — functions with many branches/paths
2. LONG FUNCTIONS — functions > 20 lines
3. SYNTAX ERRORS — invalid code that won't compile or run
4. UNUSED VARIABLES — declared but never used
5. CODE DUPLICATION — repeated similar code (DRY violations)
6. DEEP NESTING — >3 levels of if/for/while blocks
7. MAGIC NUMBERS — hardcoded values without named constants
8. POOR NAMING — vague or single-character variable/function names
9. MISSING ERROR HANDLING — unsafe external calls without try/catch
10. PERFORMANCE — inefficient loops (O(n²)), redundant API/DB calls
11. BEST PRACTICES — language-specific standards (PEP8, React hooks rules, etc.)

For EACH issue, you MUST provide ALL of these fields:
- what: What is wrong (the problem)
- why: Why it is wrong (the reason)
- impact: Impact on the system
- standard: Industry best practice that applies
- fix: Suggested fix with code example

Respond in this EXACT JSON format. NO markdown, NO backticks, ONLY RAW JSON:
{
  "summary": "2-3 short sentences about code quality.",
  "score": 85,
  "grade": "B",
  "issues": [
    {
      "type": "Performance",
      "severity": "critical",
      "line": 42,
      "function_name": "process_users",
      "description": "Nested loop detected causing O(n²) complexity",
      "what": "Nested loop iterating over users inside another user loop",
      "why": "Leads to O(n²) time complexity — execution time grows quadratically with input size",
      "impact": "Performance degradation under load — 1000 users = 1,000,000 iterations",
      "standard": "Use optimized data structures (hashmap/set) for O(1) lookups instead of nested iteration",
      "suggestion": "Replace inner loop with dictionary-based lookup: user_map = {u.id: u for u in users}",
      "fix": "user_map = {u.id: u for u in users}\\nresult = user_map.get(target_id)"
    }
  ],
  "positives": [
    "Clean logic structure."
  ],
  "metrics": {
    "totalIssues": 1,
    "critical": 1,
    "warnings": 0,
    "info": 0,
    "estimatedFixTime": "5 minutes",
    "cyclomaticComplexity": "moderate",
    "duplications": 0,
    "codeSmells": 1
  }
}

Grade scale: A (90-100), B (75-89), C (60-74), D (40-59), F (0-39)
Severity: "critical", "warning", "info"
DO NOT write anything else except raw JSON."""

@router.post("/")
async def review_code(request: ReviewRequest):
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="No code provided.")

    if len(request.code) > 60_000:
        raise HTTPException(status_code=400, detail="Code too large.")

    print(f"[REVIEWER] Analyzing code...")

    user_message = f"Language: {request.language}\n\nCode:\n{request.code}"

    try:
        response_text = await call_ai(REVIEWER_SYSTEM_PROMPT, user_message)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    try:
        result = clean_ai_json(response_text)
    except json.JSONDecodeError as e:
        print("[REVIEWER] JSON parse failed")
        raise HTTPException(
            status_code=500,
            detail=f"AI returned invalid JSON: {str(e)} -> Raw text starting with: {response_text[:50]}"
        )

    return result
