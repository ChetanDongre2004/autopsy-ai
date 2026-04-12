# -*- coding: utf-8 -*-
"""FastAPI routes for AI test generation, explanations, and Python test syntax checks."""

import json
import re
import ast
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ai_helper import call_ai
from utils.parsers import clean_ai_json

router = APIRouter()


class TestRequest(BaseModel):
    """Request body for POST /api/test/."""
    code: str = Field(..., description="Source code to generate tests for")
    language: str = Field(default="python", description="Programming language")
    function_name: Optional[str] = Field(
        default=None,
        description="If set, focus tests on this specific function",
    )
    test_depth: str = Field(
        default="standard",
        description="'quick' (5 tests), 'standard' (10 tests), 'thorough' (15+ tests)",
    )
    include_mocks: bool = Field(
        default=True,
        description="Whether to include mock/patch examples for external dependencies",
    )
    include_fixtures: bool = Field(
        default=True,
        description="Whether to generate reusable pytest fixtures",
    )


class ExplainTestRequest(BaseModel):
    """Request body for POST /api/test/explain."""
    test_code: str = Field(..., description="The test function to explain")
    language: str = Field(default="python")


class ValidateSyntaxRequest(BaseModel):
    """Request body for POST /api/test/run-check."""
    test_code: str = Field(..., description="Test file content to validate")
    language: str = Field(default="python")


FRAMEWORK_CONFIG = {
    "python": {
        "framework": "pytest",
        "version": "pytest>=7.0",
        "install": "pip install pytest pytest-cov",
        "run_command": "pytest tests/test_generated.py -v --tb=short",
        "coverage_command": "pytest tests/test_generated.py -v --cov=. --cov-report=term-missing",
        "file_name": "test_generated.py",
        "import_style": "import pytest\nfrom unittest.mock import Mock, patch, MagicMock",
    },
    "javascript": {
        "framework": "jest",
        "version": "jest@^29",
        "install": "npm install --save-dev jest",
        "run_command": "npx jest --verbose",
        "coverage_command": "npx jest --coverage",
        "file_name": "generated.test.js",
        "import_style": "const { ... } = require('./your-module');",
    },
    "typescript": {
        "framework": "jest + ts-jest",
        "version": "jest@^29, ts-jest@^29",
        "install": "npm install --save-dev jest ts-jest @types/jest",
        "run_command": "npx jest --verbose",
        "coverage_command": "npx jest --coverage",
        "file_name": "generated.test.ts",
        "import_style": "import { ... } from './your-module';",
    },
    "java": {
        "framework": "JUnit 5",
        "version": "junit-jupiter:5.10.0",
        "install": "Add to pom.xml: <dependency>junit-jupiter 5.10.0</dependency>",
        "run_command": "mvn test",
        "coverage_command": "mvn test jacoco:report",
        "file_name": "GeneratedTest.java",
        "import_style": "import org.junit.jupiter.api.*;\nimport static org.junit.jupiter.api.Assertions.*;",
    },
}


def build_tester_system_prompt(language: str, depth: str, include_mocks: bool, include_fixtures: bool) -> str:
    """Build the system prompt for test generation."""
    fw = FRAMEWORK_CONFIG.get(language, FRAMEWORK_CONFIG["python"])

    depth_config = {
        "quick": {"count": 5, "desc": "5 essential tests covering the most important cases"},
        "standard": {"count": 10, "desc": "10 tests: happy paths, edge cases, and error scenarios"},
        "thorough": {
            "count": 15,
            "desc": "15+ tests: comprehensive coverage including security, performance edge cases, and all boundary conditions",
        },
    }
    target = depth_config.get(depth, depth_config["standard"])

    mock_instruction = ""
    if include_mocks and language == "python":
        mock_instruction = "\n- Include at least 1 test that uses unittest.mock.patch to mock an external dependency (database, API call, file I/O) if relevant"

    fixture_instruction = ""
    if include_fixtures and language == "python":
        fixture_instruction = "\n- Create a @pytest.fixture for any shared test data used by multiple tests"

    return f"""You are a Senior QA Engineer and Test Automation expert specializing in {language} with {fw['framework']}.

Your mission: generate {target['desc']} for the provided code.

══════════════════════════════
TEST CATEGORIES TO COVER
══════════════════════════════
CATEGORY 1 — HAPPY PATH (normal usage)
  → Test the expected, documented use case
  → Verify return values for typical valid inputs

CATEGORY 2 — EDGE CASES (boundary conditions)
  → Empty: "", [], {{}}, None/null
  → Single element: ["x"], "a", 1
  → Boundary values: 0, 1, -1, sys.maxsize, float("inf")
  → Whitespace: " ", "\\t\\n", "  spaces  "
  → Float precision: 0.1 + 0.2 (should not equal 0.3 exactly)

CATEGORY 3 — ERROR CASES (invalid / unexpected input)
  → Wrong type: int where str expected
  → None/null input
  → Negative numbers where only positive valid
  → Division by zero
  → Missing keys in dicts

CATEGORY 4 — SECURITY CASES (adversarial input)
  → SQL injection: "' OR '1'='1'; DROP TABLE users; --"
  → XSS payload: "<script>alert('xss')</script>"
  → Path traversal: "../../etc/passwd"
  → Very long string (10,000 chars)
  → Unicode/emoji: "\\u0000", "你好", "🔥💥"
{mock_instruction}{fixture_instruction}

══════════════════════════════
OUTPUT FORMAT — STRICT JSON
══════════════════════════════
Respond ONLY with this exact JSON structure. NO markdown. NO backticks. NO explanation. RAW JSON only.

{{
  "framework": "{fw['framework']}",
  "language": "{language}",
  "totalTests": <integer>,
  "coverage": "<estimated percentage like ~85%>",
  "testCases": [
    {{
      "name": "<test function name, snake_case, descriptive>",
      "type": "<one of: happy_path | edge_case | error_case | security>",
      "description": "<one sentence: what behavior is being verified and WHY>",
      "inputs": "<human-readable description of inputs>",
      "expectedOutput": "<human-readable description of expected result>",
      "complexity": "<simple | medium | complex>"
    }}
  ],
  "testFile": "<complete, runnable {language} test file as a single string with \\n for newlines>",
  "fixtures": [
    {{
      "name": "<fixture name>",
      "purpose": "<what shared data/state this provides>"
    }}
  ],
  "setupInstructions": "{fw['install']}\\n{fw['run_command']}",
  "coverageCommand": "{fw['coverage_command']}",
  "notes": "<any important assumptions, limitations, or things the developer should know>",
  "missingForFullCoverage": ["<what additional tests would be needed for 100% coverage>"]
}}

RULES FOR testFile:
- Must be 100% complete and immediately runnable with NO placeholders like "# your code here"
- Must import the module being tested (use a placeholder like: from your_module import function_name)
- Add a # WHY: comment on each test explaining the testing rationale
- Use AAA pattern: # Arrange / # Act / # Assert comments
- For Python: use pytest style with descriptive function names starting with test_
- Functions must have proper return type assertions (not just "no crash")

RESPOND ONLY WITH VALID JSON. The testFile must be complete and runnable."""


EXPLAIN_TEST_PROMPT = """You are a Senior QA Engineer explaining tests to a junior developer.
Given a test function, explain in simple terms:
1. What the test is verifying
2. WHY this specific test case matters (what bug it catches)
3. How to make the test pass (what the production code must do)

Be concrete and friendly. Use analogies. Avoid jargon.

Respond ONLY in this JSON:
{
  "testName": "<name of the function>",
  "oneLiner": "<one sentence: what this test does>",
  "whyItMatters": "<paragraph: what bug this catches and real-world impact>",
  "howToPass": "<what the production code must implement to pass this test>",
  "testType": "<happy_path | edge_case | error_case | security>",
  "difficulty": "<beginner | intermediate | advanced>"
}"""


def detect_functions_in_code(code: str, language: str) -> List[str]:
    """Return function/method names found in source for prompt context."""
    functions = []

    if language == "python":
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith("__"):
                        functions.append(node.name)
        except SyntaxError:
            pattern = r"(?:async\s+)?def\s+([a-zA-Z_]\w*)\s*\("
            functions = re.findall(pattern, code)

    elif language in ("javascript", "typescript"):
        patterns = [
            r"function\s+([a-zA-Z_$][\w$]*)\s*\(",
            r"(?:const|let|var)\s+([a-zA-Z_$][\w$]*)\s*=\s*(?:async\s*)?\(",
            r"([a-zA-Z_$][\w$]*)\s*:\s*(?:async\s*)?function",
            r"(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)",
        ]
        for pat in patterns:
            found = re.findall(pat, code)
            functions.extend(f for f in found if f not in ("if", "for", "while", "switch"))

    elif language == "java":
        pattern = r"(?:public|private|protected)(?:\s+static)?\s+\w+\s+([a-zA-Z_]\w*)\s*\("
        functions = re.findall(pattern, code)

    seen = set()
    return [f for f in functions if not (f in seen or seen.add(f))]


def build_fallback_response(raw_response: str, language: str, request: TestRequest) -> dict:
    """Return a structured payload when AI output is not valid JSON."""
    fw = FRAMEWORK_CONFIG.get(language, FRAMEWORK_CONFIG["python"])
    return {
        "framework": fw["framework"],
        "language": language,
        "totalTests": 0,
        "coverage": "N/A",
        "testCases": [],
        "testFile": raw_response,
        "fixtures": [],
        "setupInstructions": f"{fw['install']}\n{fw['run_command']}",
        "coverageCommand": fw["coverage_command"],
        "notes": "⚠️ Could not parse structured response. The testFile contains the raw AI output which may still contain valid test code.",
        "missingForFullCoverage": [],
        "rawResponse": True,
    }


@router.post("/")
async def generate_tests(request: TestRequest):
    """Generate a test suite from submitted source code."""
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="No code provided. Please paste source code to generate tests for.")

    if len(request.code) > 60_000:
        raise HTTPException(
            status_code=400,
            detail=f"Code too large ({len(request.code):,} chars). Maximum is 60,000 characters.",
        )

    language = request.language.lower().strip()
    if language not in FRAMEWORK_CONFIG:
        supported = list(FRAMEWORK_CONFIG.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Language '{language}' not supported. Supported: {supported}",
        )

    detected_functions = detect_functions_in_code(request.code, language)

    print(f"[TESTER] Lang={language} | Depth={request.test_depth} | "
          f"Functions={detected_functions} | Size={len(request.code)} chars")

    focus_instruction = ""
    if request.function_name:
        focus_instruction = f"\n\n🎯 FOCUS: Prioritize tests for the function named `{request.function_name}` but also test helper functions it depends on."
    elif detected_functions:
        func_list = ", ".join(f"`{f}`" for f in detected_functions[:8])
        focus_instruction = f"\n\nDetected functions: {func_list}. Write tests that cover all of them."

    depth_map = {
        "quick": "Generate 5 focused tests covering only the most critical paths.",
        "standard": "Generate 10 tests: 3 happy path, 3 edge case, 2 error case, 2 security.",
        "thorough": "Generate 15+ tests: be exhaustive. Cover every branch, every edge, every security angle.",
    }
    depth_instruction = depth_map.get(request.test_depth, depth_map["standard"])

    user_message = (
        f"Generate tests for this {language} code.\n\n"
        f"```{language}\n{request.code}\n```"
        f"{focus_instruction}\n\n"
        f"DEPTH: {depth_instruction}\n\n"
        f"Remember: the testFile must be 100% complete and immediately runnable. "
        f"No TODO comments, no placeholders."
    )

    system_prompt = build_tester_system_prompt(
        language=language,
        depth=request.test_depth,
        include_mocks=request.include_mocks,
        include_fixtures=request.include_fixtures,
    )

    try:
        raw_response = await call_ai(system_prompt, user_message)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI call failed: {str(e)}")

    try:
        result = clean_ai_json(raw_response)
    except json.JSONDecodeError as e:
        print(f"[TESTER] ⚠️ JSON parse failed. Error: {e}. Raw preview: {raw_response[:300]}")
        result = build_fallback_response(raw_response, language, request)

    result["detectedFunctions"] = detected_functions
    result["requestedDepth"] = request.test_depth
    result["requestedLanguage"] = language

    print(f"[TESTER] ✅ Done. {result.get('totalTests', 0)} tests generated for {language}.")
    return result


@router.post("/explain")
async def explain_test(request: ExplainTestRequest):
    """Explain a single test function in plain language."""
    if not request.test_code or not request.test_code.strip():
        raise HTTPException(status_code=400, detail="No test code provided.")

    user_message = (
        f"Explain this {request.language} test to a junior developer:\n\n"
        f"```{request.language}\n{request.test_code}\n```"
    )

    try:
        raw = await call_ai(EXPLAIN_TEST_PROMPT, user_message)
        return clean_ai_json(raw)
    except json.JSONDecodeError:
        return {
            "testName": "Unknown",
            "oneLiner": "Could not parse explanation.",
            "whyItMatters": raw,
            "howToPass": "",
            "testType": "unknown",
            "difficulty": "unknown",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-check")
async def validate_test_syntax(request: ValidateSyntaxRequest):
    """Validate Python test syntax via ast.parse; other languages return a not-available notice."""
    if not request.test_code.strip():
        raise HTTPException(status_code=400, detail="No test code provided.")

    if request.language == "python":
        warnings = []

        try:
            tree = ast.parse(request.test_code)

            test_funcs = [
                node.name for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
            ]

            if not test_funcs:
                warnings.append(
                    "No test functions found (functions starting with 'test_'). "
                    "pytest won't discover any tests.",
                )

            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            if "pytest" not in imports:
                warnings.append(
                    "pytest is not imported. Add 'import pytest' at the top for fixture support and pytest.raises().",
                )

            return {
                "valid": True,
                "errors": [],
                "warnings": warnings,
                "testFunctions": test_funcs,
                "testCount": len(test_funcs),
                "message": f"Syntax OK. Found {len(test_funcs)} test function(s).",
            }

        except SyntaxError as e:
            return {
                "valid": False,
                "errors": [f"SyntaxError on line {e.lineno}: {e.msg}"],
                "warnings": [],
                "testFunctions": [],
                "testCount": 0,
                "message": f"Syntax error found on line {e.lineno}.",
            }
    else:
        return {
            "valid": None,
            "errors": [],
            "warnings": [
                f"Server-side syntax checking for {request.language} is not available. "
                f"Copy the test file and run it locally to verify.",
            ],
            "testFunctions": [],
            "testCount": 0,
            "message": f"Syntax checking not available for {request.language} on this server.",
        }


@router.get("/frameworks")
async def list_frameworks():
    """List supported languages and their testing framework metadata."""
    return {
        "frameworks": [
            {
                "language": lang,
                "framework": config["framework"],
                "version": config["version"],
                "install": config["install"],
                "run_command": config["run_command"],
                "file_name": config["file_name"],
            }
            for lang, config in FRAMEWORK_CONFIG.items()
        ]
    }
