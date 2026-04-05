"""
routes/reviewer.py
==================
WEEK 1 FEATURE: Code Quality Reviewer (Static Analysis)
"""
import json
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ai_helper import call_ai
import httpx

router = APIRouter()

class ReviewRequest(BaseModel):
    code: str
    language: str = "python"

REVIEWER_SYSTEM_PROMPT = """You are an elite Senior Principal Software Engineer at a top tech company.
You are performing a rigorous, CodeRabbit-style code review.

First, verify if the code has valid syntax. If it contains syntax errors, invalid formatting, or typos that would prevent it from running, report them as critical issues immediately.

Then, analyze the code for these SPECIFIC issues:
1. LONG FUNCTIONS — functions > 20 lines.
2. SYNTAX ERRORS — Invalid code that won't compile or run.
3. UNUSED VARIABLES — declared but never used.
4. DRY VIOLATIONS — repeated similar code.
5. DEEP NESTING — >3 levels of if/for/while blocks.
6. MAGIC NUMBERS — hardcoded values without named constants.
7. POOR NAMING — vague or single-character names.
8. MISSING ERROR HANDLING — unsafe external calls.

For each issue, pinpoint the exact line number (or range) and suggest a fix.

Respond in this EXACT JSON format, with NO markdown formatting, NO backticks, NO intro, NO outro. ONLY RAW JSON string.
{
  "summary": "2-3 short sentences about code quality.",
  "score": 85,
  "grade": "B",
  "issues": [
    {
      "type": "Magic Number",
      "severity": "critical",
      "line": 42,
      "function_name": "calculate_tax",
      "description": "Hardcoded tax rate 0.05 found.",
      "suggestion": "Extract to a constant e.g., TAX_RATE = 0.05",
      "impact": "If tax changes, you might miss updating it here."
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
    "estimatedFixTime": "5 minutes"
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
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"AI API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    try:
        # Strip potential markdown formatting that the AI might incorrectly add despite prompt
        clean = re.sub(r"```[a-zA-Z]*\n", "", response_text)
        clean = clean.replace("```", "").strip()
        result = json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"[REVIEWER] JSON parse failed. Raw: {response_text[:200]}")
        raise HTTPException(
            status_code=500, 
            detail=f"AI returned invalid JSON: {str(e)} -> Raw text starting with: {response_text[:50]}"
        )

    return result
