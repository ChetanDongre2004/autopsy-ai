"""
routes/tester.py
================
WEEK 2 FEATURE: Autonomous Test Generator (QA Automation)

WHAT THIS FILE DOES:
Automatically writes unit tests for any code the user submits.
This is like having a QA engineer who instantly writes a full test suite.

WHAT ARE UNIT TESTS?
Unit tests verify that individual functions work correctly.
They test the "units" of your code in isolation.
Example: if you have add(a, b), a unit test checks:
  - add(2, 3) == 5         ← happy path
  - add(-1, 1) == 0        ← negative numbers
  - add(0, 0) == 0         ← zeros (edge case)
  - add(None, 1) raises    ← null input (error case)

WHAT FRAMEWORKS DO WE USE?
- Python code → pytest (the most popular Python testing framework)
- JavaScript  → Jest (Facebook's testing framework)

WHAT ARE EDGE CASES?
Edge cases are the "corner" inputs that break things:
  - Empty string ""
  - Empty list []
  - Zero (0) or negative numbers
  - Very large numbers (overflow)
  - None / null / undefined
  - SQL injection strings like ' OR '1'='1
  - Unicode characters like 你好

WHY IS THIS USEFUL?
Most bugs hide in edge cases. Claude writes tests that cover them all
so developers don't have to think of them manually.
"""

import json
import re
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ai_helper import call_claude

router = APIRouter()


class TestRequest(BaseModel):
    code: str
    language: str = "python"
    function_name: Optional[str] = None  # Focus on specific function if provided


TESTER_SYSTEM_PROMPT = """You are a Senior QA Engineer and Test Automation expert.
Your job is to write comprehensive unit tests that catch bugs before they reach production.

For the provided code, generate tests that cover:

CATEGORY 1 — HAPPY PATH (normal usage)
- Test the most common, expected use case
- Verify the return value is correct for normal inputs

CATEGORY 2 — EDGE CASES (boundary conditions)
- Empty input: empty string "", empty list [], empty dict {}
- Single element: list with 1 item, string with 1 character
- Boundary values: 0, 1, -1, very large numbers, float precision issues
- Whitespace: " " (space only), "  multiple  spaces  "

CATEGORY 3 — ERROR CASES (invalid input)
- None / null input
- Wrong type: passing string where int expected
- Negative numbers where only positive makes sense
- Division by zero scenarios

CATEGORY 4 — SECURITY CASES
- SQL injection string: "' OR '1'='1'; DROP TABLE users; --"
- XSS payload: "<script>alert('xss')</script>"
- Path traversal: "../../etc/passwd"
- Very long string (10,000 characters)

Write pytest tests (for Python) or Jest tests (for JavaScript).

For Python pytest, use this style:
import pytest
def test_function_name_describes_what_it_tests():
    # Arrange — set up inputs
    # Act — call the function
    # Assert — verify the output
    assert result == expected

Respond ONLY with valid JSON in this exact format:
{
  "framework": "pytest",
  "language": "python",
  "totalTests": 9,
  "coverage": "~85%",
  "testCases": [
    {
      "name": "test_returns_correct_sum_for_two_positive_integers",
      "type": "happy_path",
      "description": "Verifies that add(2, 3) returns 5 as expected",
      "inputs": "2, 3",
      "expectedOutput": "5"
    },
    {
      "name": "test_returns_empty_list_when_input_is_empty",
      "type": "edge_case",
      "description": "Verifies function handles empty list without crashing",
      "inputs": "[]",
      "expectedOutput": "[]"
    },
    {
      "name": "test_raises_type_error_for_none_input",
      "type": "error_case",
      "description": "Verifies None input raises TypeError, not a silent failure",
      "inputs": "None",
      "expectedOutput": "raises TypeError"
    }
  ],
  "testFile": "import pytest\n\n# Full test file content here — complete, runnable code\n",
  "setupInstructions": "pip install pytest\npytest tests/test_generated.py -v",
  "notes": "Important considerations or assumptions made while writing tests"
}

RESPOND ONLY WITH VALID JSON. The testFile must be complete and immediately runnable."""


@router.post("/")
async def generate_tests(request: TestRequest):
    """
    POST /api/test
    Generates a complete unit test file for the provided code.
    Body: { "code": "...", "language": "python", "function_name": "optional" }
    Returns: JSON with test cases list + complete test file content
    """
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="No code provided.")

    print(f"[TESTER] Generating {request.language} tests — {len(request.code)} chars")

    focus = ""
    if request.function_name:
        focus = f"\n\nFocus your tests on the function named: `{request.function_name}`"

    user_message = (
        f"Write comprehensive unit tests for this {request.language} code.{focus}\n\n"
        f"```{request.language}\n{request.code}\n```\n\n"
        f"Requirements:\n"
        f"- Minimum 8 tests total\n"
        f"- At least 3 edge cases\n"
        f"- At least 2 error/exception cases\n"
        f"- At least 1 security test (try SQL injection string as input)\n"
        f"- The testFile must be 100% complete and runnable with no placeholders\n"
        f"- Add a comment on each test explaining WHY this case is being tested"
    )

    try:
        claude_response = await call_claude(TESTER_SYSTEM_PROMPT, user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        clean = re.sub(r"```(?:json)?\s*", "", claude_response).replace("```", "").strip()
        result = json.loads(clean)
    except json.JSONDecodeError:
        result = {
            "framework": "pytest" if request.language == "python" else "jest",
            "language": request.language,
            "totalTests": 0,
            "testCases": [],
            "testFile": claude_response,
            "setupInstructions": "pytest tests/test_generated.py -v",
            "rawResponse": True,
        }

    print(f"[TESTER] Done. {result.get('totalTests', 0)} tests generated.")
    return result
